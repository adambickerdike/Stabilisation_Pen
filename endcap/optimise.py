r"""Design optimisation of the end-cap device classes (CALC, linear model).

Objectives (for each class and each mass cap 15/25/35/45 g):
  tremor  minimise the mean, over the grip splits r_rot 0.3/0.5/0.7 and f = 4, 6, 8, 10, 12 Hz, of the residual ratio of the
          handle-tip tremor (1 mm hand-path tremor, default ellipse) with the device's scaled model inverse, relative to the
          Rev H pen without the end-cap (so a device is charged for the mass it adds: a heavier handle changes the tremor
          that reaches the tip, sometimes for the worse)
  steer   maximise the mean over splits of the tip displacement the device can make in its weakest direction at 3 Hz
          (writing frequencies), at its force/torque limit, in the relaxed-hand model (HAP-26)
Constraints (quadratic penalties): mass <= cap; fit in the 26 x 45 mm end-cap; spin speed <= 40 000 rpm; spin-up <= 10 s;
stored rotor energy <= 3 J; average power <= 0.3 W (spin + tremor-mode actuation at 10 Hz, 1 mm); peak <= 1 W.
Methods
  gradient  autograd through the torch model (endcap/linear_torch.py) and the design models (endcap/design.py); box
            variables through a sigmoid; Adam with a rising penalty weight; several seeded starts.  Chosen because the
            objective is smooth in the continuous sizes once the hard minima are softened, and it is cheap to differentiate.
  CMA-ES    derivative-free (endcap/cmaes.py) on the exact (hard-minimum) objective, including the discrete choices (motor,
            CMG arrangement) as rounded coordinates.  Chosen to check the gradient optima, to handle the non-smooth limits
            and the catalogue choices, and because the problem is small (3-5 variables).
Bayesian optimisation was not used: each evaluation costs milliseconds, so sample efficiency does not matter here.
Evidence status: CALCULATION.  Absolute ratios are single-frequency linear bounds (optimistic; the time domain realises a
fraction of them: study I1 found a quarter to a half).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch

from . import design as DS
from . import linear_torch as LT
from . import params as P
from .cmaes import cmaes

F_TREMOR = (4.0, 6.0, 8.0, 10.0, 12.0)
A_TREMOR = 1e-3
F_STEER = 3.0
F_STEER_ALL = (1.0, 2.0, 3.0, 5.0)
MASS_CAPS = (15e-3, 25e-3, 35e-3, 45e-3)

_MODELS: Dict = {}


def model(r_rot, hand_scale=1.0):
    k = (r_rot, hand_scale)
    if k not in _MODELS:
        _MODELS[k] = LT.EndcapLinear(r_rot, hand_scale=hand_scale)
    return _MODELS[k]


# ------------------------------------------------------------------------------------------------ class definitions
@dataclass
class Space:
    names: Sequence[str]
    lo: Sequence[float]
    hi: Sequence[float]

    def to_x(self, z):
        s = torch.sigmoid(z) if torch.is_tensor(z) else 1 / (1 + np.exp(-np.asarray(z)))
        return {n: l + (h - l) * s[i] for i, (n, l, h) in enumerate(zip(self.names, self.lo, self.hi))}


SPACES = {
    "LRM2": Space(("d_s", "L_s", "t_c"), (6e-3, 5e-3, 0.6e-3), (18e-3, 36e-3, 3.0e-3)),
    "CMG": Space(("D", "t", "n", "delta"), (8e-3, 1.0e-3, 5000.0, 0.2), (22e-3, 8e-3, 40000.0, 1.2)),
    "RW2": Space(("D", "t", "nb"), (10e-3, 1.0e-3, 1000.0), (22e-3, 6e-3, 20000.0)),
    "PG": Space(("D", "t", "n"), (8e-3, 1.0e-3, 5000.0), (22e-3, 8e-3, 40000.0)),
}
CMG_ARRS = ("SP2", "SP1", "DG1", "DG2", "PL2")
CMG_MOTORS = ("0308B", "0515B", "0620B", "0824B", "INT")
RW_MOTORS = ("0824B", "1226B", "1509B", "2610B", "2214BXT")
PG_MOTORS = ("0515B", "0620B", "0824B", "INT")


def build(cls, x, choice):
    if cls == "LRM2":
        return DS.lrm2(x)
    if cls == "CMG":
        return DS.cmg(x, arr=choice[0], motor=choice[1])
    if cls == "RW2":
        return DS.rw2(x, motor=choice[0])
    if cls == "PG":
        return DS.pg(x, motor=choice[0])
    raise KeyError(cls)


def dev_dict(d):
    """Linear-model parameters of a design."""
    if d["cls"] == "LRM2":
        return dict(m_fix=d["m_fix"], z_fix=d["z_fix"], m_r=d["m_r"], z_r=d["z_r"], k_c=d["k_c"], c_c=d["c_c"]), ("F_t1", "F_t2")
    if d["cls"] == "PG":
        return dict(m_fix=d["m_fix"], z_fix=d["z_fix"], H_gyro=d["H_gyro"]), ()
    return dict(m_fix=d["m_fix"], z_fix=d["z_fix"]), ("tau_t2", "tau_t1")


def limits(d, f):
    if d["cls"] == "LRM2":
        return DS.lrm_limit(d, f)
    if d["cls"] == "RW2":
        return DS.rw_limit(d, f)
    if d["cls"] in CMG_ARRS:
        return DS.cmg_limit(d, f)
    return None


def _scaled(x0, G, L, x_ref, sharp=40.0, hard=False):
    """Scaled least-squares inverse on the inputs whose limit is > 0 (see linear_torch.scaled_inverse_ratio)."""
    act = [i for i in range(G.shape[1]) if float(L[i]) > 0.0]
    if not act:
        return torch.linalg.norm(torch.abs(x0)) / torch.linalg.norm(torch.abs(x_ref)), torch.zeros(2, dtype=torch.complex128)
    Ga = G[:, act]
    La = L[act]
    Gh = Ga.conj().T
    u = -torch.linalg.solve(Gh @ Ga, Gh @ x0)
    mag = torch.abs(u) + 1e-30
    q = torch.cat([torch.ones(1, dtype=torch.float64), La / mag])
    if hard:
        s = torch.clamp(torch.min(q), 0.0, 1.0)
    else:
        s = torch.clamp(-torch.logsumexp(-sharp * q, dim=0) / sharp, 0.0, 1.0)
    res = x0 + s * (Ga @ u)
    uf = torch.zeros(G.shape[1], dtype=torch.complex128)
    for j, i in enumerate(act):
        uf[i] = s * u[j]
    return torch.linalg.norm(torch.abs(res)) / torch.linalg.norm(torch.abs(x_ref)), uf


def metrics(d, splits=P.SPLITS, f_tremor=F_TREMOR, A=A_TREMOR, f_steer=F_STEER_ALL, hard=False, hand_scale=1.0):
    """Tremor ratios, steering capacity and power of one design (torch tensors where differentiable)."""
    dv, ins = dev_dict(d)
    out = {"tremor": {}, "steer_mm": {}, "steer_axis_mm": {}}
    P_act = []
    for rr in splits:
        el = model(rr, hand_scale)
        for f in f_tremor:
            xref = el.x0_nodev(f, A)
            x0, G = el.responses(dv, f, A, inputs=ins)
            if G is None:
                r = torch.linalg.norm(torch.abs(x0)) / torch.linalg.norm(torch.abs(xref))
                u = None
            else:
                r, u = _scaled(x0, G, limits(d, f), xref, hard=hard)
            out["tremor"][(rr, f)] = r
            if u is not None and f == 10.0:
                P_act.append(actuation_power(d, f, torch.abs(u)))
        for f in f_steer:
            if not ins:
                out["steer_mm"][(rr, f)] = torch.zeros(())
                out["steer_axis_mm"][(rr, f)] = torch.zeros(2)
                continue
            x0, G = el.responses(dv, f, A, inputs=ins)
            L = limits(d, f)
            per, worst = LT.tip_capacity(G, L)
            out["steer_mm"][(rr, f)] = worst * 1e3
            out["steer_axis_mm"][(rr, f)] = per * 1e3
    out["tremor_mean"] = torch.stack(list(out["tremor"].values())).mean()
    out["steer_3Hz_mm"] = torch.stack([out["steer_mm"][(rr, F_STEER)] for rr in splits]).mean() if F_STEER in f_steer else None
    out["P_act_10Hz_1mm"] = torch.stack(P_act).max() if P_act else torch.zeros(())
    out["P_avg"] = d["P_spin"] + out["P_act_10Hz_1mm"]
    out["P_peak"] = peak_power(d)
    return out


def actuation_power(d, f, u_amp):
    """Average actuation power (W) for sinusoidal input amplitudes u_amp (2,)."""
    if d["cls"] == "LRM2":
        return torch.sum((u_amp / math.sqrt(2) / d["Km"]) ** 2)
    if d["cls"] == "RW2":
        m = d["mot"]
        return torch.sum((u_amp / math.sqrt(2) / m.kM) ** 2 * m.R)
    if d["cls"] in CMG_ARRS:
        return DS.cmg_gimbal_power(d, f, u_amp)
    return torch.zeros(())


def peak_power(d):
    if d["cls"] == "LRM2":
        return torch.tensor(1.0)                      # 0.5 W per axis by construction
    if d["cls"] == "RW2":
        m = d["mot"]
        return d["P_spin"] + 2 * (d["tau_pk"] / m.kM) ** 2 * m.R
    if d["cls"] in CMG_ARRS:
        # gimbal drives at full rate against full-range oscillation at 12 Hz, plus spin
        f = 12.0
        tau = DS.cmg_limit(d, f)
        return d["P_spin"] + DS.cmg_gimbal_power(d, f, tau)
    return d["P_spin"]


def penalty(d, m, cap):
    v = DS.violation(d)
    v = v + DS.relu(d["m_total"] - cap) / 1e-3
    v = v + DS.relu(m["P_avg"] - P.ENV["p_avg"]) / 0.01 + DS.relu(m["P_peak"] - P.ENV["p_peak"]) / 0.01
    return v


def objective(m, which, d=None):
    if which == "H":                                   # passive gyroscope: the largest momentum that fits
        return -d["H"] * 1e3
    return m["tremor_mean"] if which == "tremor" else -m["steer_3Hz_mm"]


# ------------------------------------------------------------------------------------------------ gradient
def grad_opt(cls, choice, cap, which="tremor", starts=4, iters=160, seed=0, lr=0.08, f_tremor=F_TREMOR, z0=None, check_every=10):
    """Adam on the sigmoid-mapped box variables with a rising quadratic penalty; start 0 from z0 (e.g. the CMA-ES optimum,
    with a smaller step) when given, the others from seeded random points.  Every `check_every` iterations the exact
    (hard-minimum) objective is evaluated and the best feasible iterate is kept, so a warm start can only improve."""
    sp = SPACES[cls]
    rng = np.random.default_rng(seed)
    best = None

    def exact(z):
        with torch.no_grad():
            x = sp.to_x(z)
            d = build(cls, x, choice)
            m = metrics(d, hard=True, f_tremor=f_tremor, f_steer=(F_STEER,))
            return float(objective(m, which, d)), float(penalty(d, m, cap)), {k: float(v) for k, v in x.items()}

    for s in range(starts):
        warm = z0 is not None and s == 0
        zi = np.asarray(z0, float) if warm else rng.normal(0, 1.2, len(sp.names))
        z = torch.tensor(zi, requires_grad=True)
        opt = torch.optim.Adam([z], lr=lr * (0.25 if warm else 1.0))
        cand = None
        for it in range(iters + 1):
            if it % check_every == 0 or it == iters:
                val, pen, xx = exact(z.detach())
                c = dict(z=z.detach().numpy().copy(), x=xx, f=val, pen=pen, start=s, it=it)
                if cand is None or (c["pen"] < 1e-3 and (cand["pen"] >= 1e-3 or c["f"] < cand["f"])) or \
                        (cand["pen"] >= 1e-3 and c["pen"] < cand["pen"]):
                    cand = c
            if it == iters:
                break
            mu = 10.0 * (100.0 ** (it / max(1, iters - 1)))
            opt.zero_grad()
            x = sp.to_x(z)
            d = build(cls, x, choice)
            m = metrics(d, f_tremor=f_tremor, f_steer=(F_STEER,))
            J = objective(m, which, d) + mu * penalty(d, m, cap) ** 2 * 1e-2
            J.backward()
            opt.step()
        if best is None or (cand["pen"] < 1e-3 and (best["pen"] >= 1e-3 or cand["f"] < best["f"])) or \
                (best["pen"] >= 1e-3 and cand["pen"] < best["pen"]):
            best = cand
    return best


# ------------------------------------------------------------------------------------------------ CMA-ES
def cma_opt(cls, cap, which="tremor", choices=None, max_evals=900, seed=0, f_tremor=F_TREMOR, restarts=1):
    """CMA-ES over the continuous variables plus one coordinate per discrete choice (rounded); `restarts` independent runs
    (seeds seed, seed + 1, ...), the best feasible kept."""
    best = None
    for k in range(restarts):
        r = _cma_once(cls, cap, which, choices, max_evals, seed + k, f_tremor)
        if best is None or (r["pen"] < 1e-3 and (best["pen"] >= 1e-3 or r["f"] < best["f"])) or \
                (best["pen"] >= 1e-3 and r["pen"] < best["pen"]):
            best = r
    return best


def _cma_once(cls, cap, which, choices, max_evals, seed, f_tremor):
    sp = SPACES[cls]
    nd = len(choices) if choices else 0

    def decode(v):
        v = np.asarray(v, float)
        x = sp.to_x(v[:len(sp.names)])
        ch = []
        for j, opts in enumerate(choices or []):
            s = 1 / (1 + math.exp(-v[len(sp.names) + j]))
            ch.append(opts[min(len(opts) - 1, int(s * len(opts)))])
        return x, tuple(ch)

    def fun(v):
        x, ch = decode(v)
        with torch.no_grad():
            d = build(cls, {k: torch.tensor(float(vv)) for k, vv in x.items()}, ch)
            m = metrics(d, hard=True, f_tremor=f_tremor, f_steer=(F_STEER,))
            pen = float(penalty(d, m, cap))
            return float(objective(m, which, d)) + 10.0 * pen + (1e3 if pen > 0.5 else 0.0)

    r = cmaes(fun, np.zeros(len(sp.names) + nd), sigma0=1.0, max_evals=max_evals, seed=seed)
    x, ch = decode(r["x"])
    with torch.no_grad():
        d = build(cls, {k: torch.tensor(float(vv)) for k, vv in x.items()}, ch)
        m = metrics(d, hard=True, f_tremor=f_tremor, f_steer=(F_STEER,))
        pen = float(penalty(d, m, cap))
    return dict(x={k: float(v) for k, v in x.items()}, choice=ch, f=float(objective(m, which, d)), pen=pen, evals=r["evals"],
                history=[float(h) for h in r["history"]], z=np.asarray(r["x"], float)[:len(sp.names)].tolist())


# ------------------------------------------------------------------------------------------------ reporting helpers
def summarize(cls, x, choice, splits=P.SPLITS):
    """Full metrics (hard minima, all frequencies) of a design, as floats for JSON."""
    with torch.no_grad():
        d = build(cls, {k: torch.tensor(float(v)) for k, v in x.items()}, choice)
        m = metrics(d, splits=splits, hard=True)
    out = {"class": d["cls"], "choice": list(choice), "x": x, "mass_g": float(d["m_total"]) * 1e3,
           "moving_mass_g": float(d["m_r"]) * 1e3, "P_spin_W": float(d["P_spin"]), "P_avg_W": float(m["P_avg"]),
           "P_peak_W": float(m["P_peak"]), "violation": float(DS.violation(d)),
           "tremor_ratio": {f"r{rr}_{f:g}Hz": float(v) for (rr, f), v in m["tremor"].items()},
           "tremor_mean": float(m["tremor_mean"]),
           "steer_worst_mm": {f"r{rr}_{f:g}Hz": float(v) for (rr, f), v in m["steer_mm"].items()},
           "steer_axis_mm": {f"r{rr}_{f:g}Hz": [float(a) for a in v] for (rr, f), v in m["steer_axis_mm"].items()},
           "steer_3Hz_mm": float(m["steer_3Hz_mm"]) if m["steer_3Hz_mm"] is not None else None,
           "parts_g": {k: float(v) for k, v in d.get("parts", {}).items()}}
    for k in ("H", "X", "Km", "F_act", "L_ax", "H_net", "tau_pk", "J", "dW"):
        if k in d:
            out[k] = float(d[k])
    if "extras" in d:
        out["extras"] = {k: float(v) for k, v in d["extras"].items()}
    cell = P.REVH["cell_Wh"]
    out["battery_h_14500"] = cell / (P.REVH["p_base"] + out["P_avg_W"])
    out["battery_h_10440"] = P.REVH["cell10440_Wh"] / (P.REVH["p_base"] + out["P_avg_W"])
    return out


def passive_weight_ratio(m_add, splits=P.SPLITS, f_tremor=F_TREMOR, A=A_TREMOR):
    """Ratio for the same mass fixed in the end-cap with no control (comparator)."""
    out = {}
    with torch.no_grad():
        for rr in splits:
            el = model(rr)
            for f in f_tremor:
                x0 = el.responses(dict(m_fix=m_add, z_fix=P.Z_CAP), f, A, inputs=())[0]
                out[f"r{rr}_{f:g}Hz"] = float(torch.linalg.norm(torch.abs(x0)) / torch.linalg.norm(torch.abs(el.x0_nodev(f, A))))
    return out


def tmd_ratio(m, f_tune, zeta=0.1, splits=P.SPLITS, f_tremor=F_TREMOR, A=A_TREMOR, m_fix=8e-3):
    out = {}
    k = m * (2 * math.pi * f_tune) ** 2
    c = 2 * zeta * math.sqrt(k * m)
    with torch.no_grad():
        for rr in splits:
            el = model(rr)
            for f in f_tremor:
                x0 = el.responses(dict(m_fix=m_fix, z_fix=P.Z_CAP, m_r=m, z_r=P.Z_CAP, k_c=k, c_c=c), f, A, inputs=())[0]
                out[f"r{rr}_{f:g}Hz"] = float(torch.linalg.norm(torch.abs(x0)) / torch.linalg.norm(torch.abs(el.x0_nodev(f, A))))
    return out
