r"""Differentiable-simulation policy learning (task 4d): a small neural controller for the rear-cap reaction mass, trained by
backpropagation through time (BPTT) through a PyTorch discrete-time model of the linearised Rev H dynamics, then run
inside the nonlinear model H1 through the core's MLP hook.

Model (CALC): LinearExt of the Rev H handle + hand + reaction mass at the nominal split r_rot 0.5, paper as a viscous
equivalent of the skid friction (c 5 N s/m, ASSUMPTION: describing function of 0.1 N Coulomb friction at 0.5 mm, 8 Hz),
state space discretised by zero-order hold at the 2 kHz controller rate.  Inputs: RM forces (policy, smooth saturation
F_max tanh) and the hand path (tremor + writing, from the scenarios).
Policy inputs (all available to the firmware): the tracker's tremor estimate e (2) and two first-order low-passed copies
of it (5 and 15 Hz: phase-shifted versions, 4 states), the tracked frequency, the tracker's authority, the RM position
(Hall, 2).  MLP 10 -> 12 (tanh) -> 2.  The tracker outputs are precomputed from H1 runs of the neutral RM pen (open
loop, as the IMC feed-forward), training seeds 300-311 only.
Training: (1) warm start by behaviour cloning of the model-based phasor feed-forward (addon.ff_phasor) along its own
linear-model response; (2) BPTT fine-tuning of the loss = (handle-tip displacement with policy / without)^2 per window
(the writing response is independent of the policy in the linear model) + force (power) + stroke-limit penalty (writing
+ tremor + policy) + the tip displacement the policy causes on tremor-free training writing (false correction); model
selection on a fixed validation set (validation seeds 316-317; the cloned policy is kept if BPTT does not improve it).
Evidence status: SIMULATION (training on the linear model; evaluation in H1).
"""
from __future__ import annotations

import math
import os
import time
from typing import Dict, List

import numpy as np
import torch

from sim.handpen import model as HM
from . import addon as AD
from . import control as CL
from . import revh as RH
from . import scen as SC
from . import tracker as TK
from .linear_ext import LinearExt

torch.set_num_threads(2)
TS = 5e-4
F_LP = (5.0, 15.0)
H = 12
N_IN = 10


def linear_model(d, rm, r_rot=0.5, c_paper=5.0):
    cfg = RH.config_B(d, r_rot=r_rot, device=rm)
    lm = LinearExt(cfg, paper="viscous", c_paper=c_paper)
    tip = np.zeros((2, lm.ndof)); tip[0, 0] = 1.0; tip[1, 1] = 1.0
    rmj = np.zeros((2, lm.ndof)); rmj[0, lm.ir] = 1.0; rmj[1, lm.ir + 1] = 1.0
    A, B, Cd, Cv = lm.state_space(["F_t1", "F_t2"], {"tip": tip, "rm": rmj}, hand=True)
    Ad, Bd = CL.c2d(A, B, TS)
    return Ad, Bd, Cd["tip"], Cd["rm"]


def lp_filters():
    """Discrete first-order low-passes of e (2 axes x 2 cut-offs): x+ = a x + (1 - a) e."""
    return np.array([math.exp(-2 * math.pi * f * TS) for f in F_LP])


def make_data(d, rm, seeds, f0s=(4.0, 6.0, 8.0, 10.0, 12.0), amps=(0.3e-3, 1.0e-3, 2.0e-3), akf_params=None, tremor_free=True):
    """Per case: tracker outputs at 2 kHz (e, f, authority), the hand tremor path and the writing path at 2 kHz."""
    cfgR = RH.config_B(d, r_rot=0.5, device=rm)
    data = []
    cases = [(s, f0, a) for s in seeds for f0 in f0s for a in amps]
    if tremor_free:
        cases += [(s, 0.0, 0.0) for s in seeds]
    for seed, f0, amp in cases:
        tr = SC.tremor(f0, amp) if amp > 0 else None
        sc = SC.get(seed, tr)
        un = HM.run(sc, cfgR, rec_hz=TK.REC_HZ)
        dh, info, _ = TK.estimate(un, sc, seed=seed + 7000, body="pen", params=akf_params)
        k = np.arange(len(dh)) * int(round(TS / HM.DT))
        k = np.clip(k, 0, len(sc.t) - 1)
        g_out = float((akf_params or TK.ship_params()).get("g", 1.0))
        data.append({"seed": seed, "f0": f0, "amp": amp, "e": dh.astype(np.float32), "f": info["f_est"].astype(np.float32),
                     "g": (info["authority"] / max(g_out, 1e-9)).astype(np.float32),
                     "d": sc.dtrue[k].astype(np.float32), "w": (sc.pref[k, 0:2] - sc.dtrue[k] - sc.pref[0, 0:2]).astype(np.float32)})
    return data


class Policy(torch.nn.Module):
    def __init__(self, F_max, stroke):
        super().__init__()
        self.l1 = torch.nn.Linear(N_IN, H)
        self.l2 = torch.nn.Linear(H, 2)
        torch.nn.init.normal_(self.l2.weight, std=1e-3)
        torch.nn.init.zeros_(self.l2.bias)
        self.F_max, self.stroke = F_max, stroke
        # input scales (folded into W1 at export)
        self.scale = torch.tensor([1 / 1e-3] * 6 + [1 / 10.0, 1.0, 1 / stroke, 1 / stroke], dtype=torch.float64)

    def forward(self, z):
        return self.F_max * torch.tanh(self.l2(torch.tanh(self.l1(z * self.scale))) / self.F_max)


def simulate(pol, Ad, Bd, Ctip, Crm, batch, burn=400):
    """BPTT rollout.  batch: dict of tensors (B, T, .): e, f, g, d (tremor), w (writing).  Returns losses."""
    Bsz, T, _ = batch["e"].shape
    n = Ad.shape[0]
    Ad_t = torch.tensor(Ad); Bu = torch.tensor(Bd[:, 0:2]); Bh = torch.tensor(Bd[:, 2:8])
    Ct = torch.tensor(Ctip); Cr = torch.tensor(Crm)
    a_lp = torch.tensor(lp_filters())
    x = torch.zeros(Bsz, n, dtype=torch.float64)          # tremor + policy
    xw = torch.zeros(Bsz, n, dtype=torch.float64)         # writing (policy-free, for the stroke)
    lp = torch.zeros(Bsz, 2, 2, dtype=torch.float64)
    x0 = torch.zeros(Bsz, n, dtype=torch.float64)         # tremor without the policy (baseline for the ratio)
    L_tip, L_F, L_str, L_0 = 0.0, 0.0, 0.0, 0.0
    d_prev = batch["d"][:, 0, :]
    w_prev = batch["w"][:, 0, :]
    for t in range(T):
        e = batch["e"][:, t, :]
        lp = a_lp[None, :, None] * lp + (1 - a_lp)[None, :, None] * e[:, None, :]
        r_tot = (x + xw) @ Cr.T
        z = torch.cat([e, lp.reshape(Bsz, 4), batch["f"][:, t, :], batch["g"][:, t, :], r_tot], dim=1)
        u = pol(z)
        d = batch["d"][:, t, :]; w = batch["w"][:, t, :]
        hd = torch.cat([d, torch.zeros(Bsz, 1, dtype=torch.float64), (d - d_prev) / TS, torch.zeros(Bsz, 1, dtype=torch.float64)], 1)
        hw = torch.cat([w, torch.zeros(Bsz, 1, dtype=torch.float64), (w - w_prev) / TS, torch.zeros(Bsz, 1, dtype=torch.float64)], 1)
        x = x @ Ad_t.T + u @ Bu.T + hd @ Bh.T
        with torch.no_grad():
            x0 = x0 @ Ad_t.T + hd @ Bh.T
        xw = xw @ Ad_t.T + hw @ Bh.T
        d_prev, w_prev = d, w
        if t >= burn:
            tip = x @ Ct.T
            L_tip = L_tip + (tip ** 2).sum(1)
            L_F = L_F + (u ** 2).sum(1)
            L_str = L_str + (torch.relu(r_tot.abs() - 0.8 * pol.stroke) ** 2).sum(1)
            L_0 = L_0 + ((x0 @ Ct.T) ** 2).sum(1)
    Tn = T - burn
    return L_tip / Tn, L_F / Tn, L_str / Tn, L_0 / Tn


def imitate(pol, data, d, rm, Ad, Bd, Crm, steps=2500, lr=1e-2, sub=4, seed=0, log=None):
    """Warm start (behaviour cloning): fit the policy to the model-based phasor feed-forward (addon.ff_phasor at the nominal
    split) on the training runs, with the policy inputs computed along the feed-forward's own linear-model response."""
    a = lp_filters()
    Z, U = [], []
    cases = [x for x in data if x["amp"] > 0] + [x for x in data if x["amp"] == 0]
    for x_ in cases:
        e = x_["e"].astype(float); n = len(e)
        u = AD.ff_phasor(e, x_["f"], d, rm, r_rot_model=0.5, Ts=TS)
        lp = np.zeros((n, 2, 2)); s_ = np.zeros((2, 2))
        for t in range(n):
            s_ = a[:, None] * s_ + (1 - a)[:, None] * e[t][None, :]
            lp[t] = s_
        dd = x_["d"].astype(float) - x_["d"][0]; ww = x_["w"].astype(float) - x_["w"][0]
        hv = dd + ww
        h = np.concatenate([hv, np.zeros((n, 1)), np.gradient(hv, TS, axis=0), np.zeros((n, 1))], axis=1)
        X = np.zeros(Ad.shape[0]); r = np.zeros((n, 2))
        for t in range(n):
            r[t] = Crm @ X
            X = Ad @ X + Bd[:, 0:2] @ u[t] + Bd[:, 2:8] @ h[t]
        z = np.concatenate([e, lp.reshape(n, 4), x_["f"][:, None], x_["g"][:, None], r], axis=1)
        Z.append(z[int(0.5 / TS)::sub]); U.append(u[int(0.5 / TS)::sub])
    Z = torch.tensor(np.concatenate(Z)); U = torch.tensor(np.concatenate(U))
    opt = torch.optim.Adam(pol.parameters(), lr=lr)
    g = torch.Generator().manual_seed(seed)
    for it in range(steps):
        idx = torch.randint(0, len(Z), (4096,), generator=g)
        loss = ((pol(Z[idx]) - U[idx]) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step()
        if log and (it % 500 == 0 or it == steps - 1):
            with torch.no_grad():
                full = float(((pol(Z) - U) ** 2).mean().sqrt()); ref = float((U ** 2).mean().sqrt())
            log(f"imitation step {it}: rms error {full:.4f} N of {ref:.4f} N rms feed-forward force")
    return {"n_samples": int(len(Z)), "rms_err_N": full, "rms_ff_N": ref}


def _windows(data, rng, n, T, tremor=True):
    pool = [x for x in data if (x["amp"] > 0) == tremor]
    idx = rng.integers(0, len(pool), n)
    b = {k: [] for k in ("e", "f", "g", "d", "w")}
    for i in idx:
        x_ = pool[i]
        s0 = int(rng.integers(int(0.5 / TS), len(x_["e"]) - T))
        for k in b:
            v = x_[k][s0:s0 + T]
            b[k].append(v if v.ndim == 2 else v[:, None])
    bt = {k: torch.tensor(np.stack(v), dtype=torch.float64) for k, v in b.items()}
    # paths relative to the window start (the linear model starts at rest; the burn-in removes the transient)
    bt["d"] = bt["d"] - bt["d"][:, :1, :]
    bt["w"] = bt["w"] - bt["w"][:, :1, :]
    if not tremor:
        bt["d"] = torch.zeros_like(bt["d"])
    return bt


def train(d=None, rm=None, seeds=range(300, 312), val_seeds=(316, 317), akf_params=None, iters=150, win=1.0, batch=12,
          lam_F=0.1, lam_s=0.02, lam_f=0.2, lr=1e-3, seed=0, warm=True, log=None):
    """Loss per window = (tip with policy / tip without)^2 averaged over the batch + lam_F F^2 [N^2] + lam_s stroke excess^2
    / (0.1 mm)^2 + lam_f (false tip motion on tremor-free writing / 10 um)^2.  Model selection on a fixed validation set
    (validation seeds, never test seeds)."""
    d = d or RH.RevH()
    rm = rm or __import__("opt.inertial.addon_eval", fromlist=["default_rm"]).default_rm()
    t0 = time.time()
    data = make_data(d, rm, list(seeds), akf_params=akf_params)
    vdata = make_data(d, rm, list(val_seeds), akf_params=akf_params)
    if log:
        log(f"data {len(data)} + {len(vdata)} runs in {time.time() - t0:.1f} s")
    Ad, Bd, Ct, Cr = linear_model(d, rm)
    pol = Policy(rm.F_max[0], rm.stroke[0]).double()
    opt = torch.optim.Adam(pol.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    T = int(win / TS)
    vr = np.random.default_rng(seed + 1)
    vb, vf = _windows(vdata, vr, 24, T, True), _windows(vdata, vr, 6, T, False)
    imit = imitate(pol, data, d, rm, Ad, Bd, Cr, log=log) if warm else None

    def val():
        with torch.no_grad():
            Lt, LF, Ls, L0 = simulate(pol, Ad, Bd, Ct, Cr, vb)
            Lf, _, _, _ = simulate(pol, Ad, Bd, Ct, Cr, vf)
        return {"ratio": float(torch.sqrt(Lt.sum() / L0.sum())), "mean_ratio": float(torch.sqrt(Lt / L0).mean()),
                "false_um": float(Lf.mean().sqrt() * 1e6), "F_rms_N": float(LF.mean().sqrt()),
                "stroke_excess_um": float(Ls.mean().sqrt() * 1e6)}

    hist = []
    best = (val(), {k: v.clone() for k, v in pol.state_dict().items()}, -1)
    hist.append({"it": -1, "val": best[0]})
    for it in range(iters):
        bt = _windows(data, rng, batch, T, True)
        Lt, LF, Ls, L0 = simulate(pol, Ad, Bd, Ct, Cr, bt)
        bf = _windows(data, rng, 3, T, False)
        Lf, _, _, _ = simulate(pol, Ad, Bd, Ct, Cr, bf)
        loss = (Lt / L0).mean() + lam_F * LF.mean() + lam_s * Ls.mean() / 1e-8 + lam_f * Lf.mean() / 1e-10
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(pol.parameters(), 1.0)
        opt.step()
        h = {"it": it, "loss": float(loss.detach()), "ratio": float(torch.sqrt(Lt / L0).mean().detach()),
             "false_um": float(Lf.mean().sqrt().detach() * 1e6), "F_rms_N": float(LF.mean().sqrt().detach())}
        if it % 10 == 9 or it == iters - 1:
            h["val"] = val()
            score = h["val"]["ratio"] + 0.02 * max(h["val"]["false_um"] - 10.0, 0.0)
            if score < best[0]["ratio"] + 0.02 * max(best[0]["false_um"] - 10.0, 0.0):
                best = (h["val"], {k: v.clone() for k, v in pol.state_dict().items()}, it)
            if log:
                log(f"it {it} loss {h['loss']:.3f} train ratio {h['ratio']:.3f} | val ratio {h['val']['ratio']:.3f} "
                    f"false {h['val']['false_um']:.1f} um F {h['val']['F_rms_N']:.3f} N")
        hist.append(h)
    pol.load_state_dict(best[1])
    return pol, hist, {"n_data": len(data), "n_val": len(vdata), "train_s": time.time() - t0, "best_it": best[2], "best_val": best[0],
                       "imitation": imit}


def export(pol: Policy):
    """Core ctl spec: LTI block = the two low-passes per axis driven by e0, e1 (no direct outputs); MLP on [x; y; e]."""
    a = lp_filters()
    nx = 4
    A = np.zeros((nx, nx)); B = np.zeros((nx, CL.NI))
    # state order: [lp5_x, lp5_y, lp15_x, lp15_y] matching lp.reshape(B, 4) in simulate (index = cutoff*2 + axis)
    for c in range(2):
        for ax in range(2):
            i = c * 2 + ax
            A[i, i] = a[c]
            B[i, CL.E_EST[ax]] = 1 - a[c]
    C = np.zeros((CL.NO, nx)); D = np.zeros((CL.NO, CL.NYE))
    W1 = pol.l1.weight.detach().numpy() * pol.scale.numpy()[None, :]
    b1 = pol.l1.bias.detach().numpy()
    nin = nx + CL.NY + CL.NE
    W1c = np.zeros((H, nin))
    # policy input order: e_x, e_y, lp(4), f, g, r1, r2
    W1c[:, nx + CL.NY + 0] = W1[:, 0]
    W1c[:, nx + CL.NY + 1] = W1[:, 1]
    W1c[:, 0:4] = W1[:, 2:6]
    W1c[:, nx + CL.NY + 2] = W1[:, 6]
    W1c[:, nx + CL.NY + 3] = W1[:, 7]
    W1c[:, nx + 8] = W1[:, 8]
    W1c[:, nx + 9] = W1[:, 9]
    # the core's MLP output is linear: approximate the smooth saturation by the device's own force limit
    W2 = np.zeros((CL.NU, H)); b2 = np.zeros(CL.NU)
    W2[0:2] = pol.l2.weight.detach().numpy()
    b2[0:2] = pol.l2.bias.detach().numpy()
    macs = nx * nx + 2 * nx + H * N_IN + H + 2 * H + 2
    return {"A": A, "B": B, "C": C, "D": D, "nn": {"W1": W1c, "b1": b1, "W2": W2, "b2": b2}}, {"macs_per_tick": macs,
                                                                                               "params": H * N_IN + H + 2 * H + 2}
