"""Sanity of the adjoint gradients (SIMULATION tooling).

Three checks, reported in results/opt/tracker.json `gradient_check`:
  1. numba discrete adjoint (opt.tracker.adjoint) against PyTorch autograd through the tensor implementation of the
     same filter (opt.tracker.torch_akf.core), on the full objective of a few short recordings, all 23 parameters;
  2. central finite differences of the full objective (numba forward, smooth gates) against the adjoint gradient
     for a set of parameters, at two step sizes (a kink of the piecewise-smooth filter between the two evaluation
     points shows up as a disagreement between the step sizes);
  3. the same with the exact (hard) gates for the parameters that do not sit on a gate saturation.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Sequence

import numpy as np
import torch

from . import data as DA
from . import losses as LS
from . import torch_akf as TA

FD_KEYS = ("qt", "ra", "tau_decay", "tau_w", "wmin_hz", "f_gate", "a_c", "horizon", "lp_hz", "cap_k", "g", "tau_auth")


def objective(rs: DA.RecSet, theta: torch.Tensor, static: Dict, beta, lcfg: LS.LossCfg, grad: bool):
    J, info, _, _ = DA.evaluate(rs, TA.from_theta(theta), static, beta, lcfg, grad=grad)
    return J


def adjoint_vs_autograd(rs_full: DA.RecSet, start: Dict, static: Dict, beta=8.0, n_ticks: int = 1600,
                        lcfg: LS.LossCfg = LS.LossCfg()) -> Dict:
    """Both gradients of the objective on the first n_ticks of the recordings of rs_full (rebuilt short)."""
    import copy
    items = []
    for it in rs_full.items:
        st = copy.copy(it["st"])
        st.tick_t = st.tick_t[:n_ticks]
        items.append(dict(it, st=st, d=it["d"][:n_ticks], m=it["m"][:n_ticks]))
    rs = DA.build_set(items, full_events=True)
    th1 = TA.to_theta(start).requires_grad_(True)
    t0 = time.time()
    J1 = objective(rs, th1, static, beta, lcfg, grad=True)
    J1.backward()
    t_adj = time.time() - t0
    th2 = TA.to_theta(start).requires_grad_(True)
    t0 = time.time()
    with torch.enable_grad():
        dh = TA.forward(rs.ev, TA.from_theta(th2), static, gate_beta=beta, chunk=None)
        t = LS.terms(dh, rs.d, rs.db, rs.m, rs.clean, 1.0 / rs.ev.Ts)
        J2, _ = LS.objective(t, rs.clean, rs.glyph, lcfg)
    J2.backward()
    t_ag = time.time() - t0
    g1 = th1.grad.numpy(); g2 = th2.grad.numpy()
    rel = np.abs(g1 - g2) / np.maximum(np.abs(g2), 1e-12 * np.max(np.abs(g2)))
    return {"n_recordings": rs.B, "n_ticks": n_ticks, "J_adjoint": float(J1.detach()), "J_autograd": float(J2.detach()),
            "keys": list(TA.TRAIN_KEYS), "grad_adjoint": g1.tolist(), "grad_autograd": g2.tolist(),
            "max_rel_diff": float(np.max(rel)), "median_rel_diff": float(np.median(rel)),
            "time_adjoint_s": t_adj, "time_autograd_s": t_ag, "gate_beta": beta}


def finite_differences(rs: DA.RecSet, start: Dict, static: Dict, keys: Sequence[str] = FD_KEYS, beta=8.0,
                       steps=(1e-3, 1e-4), lcfg: LS.LossCfg = LS.LossCfg()) -> Dict:
    th = TA.to_theta(start).requires_grad_(True)
    J = objective(rs, th, static, beta, lcfg, grad=True)
    J.backward()
    g = th.grad.numpy().copy()
    rows = []
    for k in keys:
        i = TA.TRAIN_KEYS.index(k)
        fds = []
        for h in steps:
            tp = th.detach().clone(); tp[i] += h
            tm = th.detach().clone(); tm[i] -= h
            Jp = float(objective(rs, tp, static, beta, lcfg, grad=False))
            Jm = float(objective(rs, tm, static, beta, lcfg, grad=False))
            fds.append((Jp - Jm) / (2 * h))
        rel = [abs(f - g[i]) / max(abs(g[i]), 1e-12) for f in fds]
        rows.append({"param": k, "adjoint": float(g[i]), "fd": [float(f) for f in fds], "steps": list(steps),
                     "rel_err": [float(r) for r in rel]})
    return {"gate_beta": beta, "J": float(J.detach()), "rows": rows, "n_recordings": rs.B,
            "max_rel_err_smallest_step": float(max(r["rel_err"][-1] for r in rows)),
            "median_rel_err_smallest_step": float(np.median([r["rel_err"][-1] for r in rows]))}


CORE_KEYS = ("qt", "ra", "tau_decay", "tau_w", "wmin_hz")


def reference_objective(items, params, lcfg: LS.LossCfg) -> float:
    """The same objective with fusion.estimators.akf (numba) producing the estimate: shows that a jump of the
    objective belongs to the reference filter, not to the torch/adjoint implementation."""
    from fusion import estimators as ES
    dh = np.stack([ES.akf(it["st"], params)[0] for it in items])
    d = torch.as_tensor(np.stack([it["d"] for it in items]), dtype=TA.DT)
    m = torch.as_tensor(np.stack([it["m"] for it in items]).astype(float), dtype=TA.DT)
    db = LS.zero_phase(d, "band", 2000.0)
    clean = torch.tensor([it["clean"] for it in items]); glyph = torch.tensor([it["glyph"] for it in items])
    t = LS.terms(torch.as_tensor(dh), d, db, m, clean)
    J, _ = LS.objective(t, clean, glyph, lcfg)
    return float(J)


def scan(items, start: Dict, static: Dict, key: str, deltas, lcfg: LS.LossCfg = LS.LossCfg()) -> Dict:
    """J(theta_key + delta) on a grid, by the adjoint path and by fusion's numba AKF; the adjoint slope at 0."""
    rs = DA.build_set(items)
    i = TA.TRAIN_KEYS.index(key)
    th0 = TA.to_theta(start)
    Js, Jr = [], []
    for dlt in deltas:
        th = th0.clone(); th[i] += dlt
        Js.append(float(objective(rs, th, static, None, lcfg, grad=False)))
        p = TA.to_numba({k: float(v) for k, v in TA.from_theta(th).items()}, static)
        Jr.append(reference_objective(items, p, lcfg))
    thg = th0.clone().requires_grad_(True)
    objective(rs, thg, static, None, lcfg, grad=True).backward()
    return {"param": key, "deltas": list(map(float, deltas)), "J_adjoint_path": Js, "J_numba_reference": Jr,
            "max_abs_diff_paths": float(np.max(np.abs(np.array(Js) - np.array(Jr)))), "adjoint_slope_at_0": float(thg.grad[i])}


def small_step(items, start: Dict, static: Dict, keys=CORE_KEYS, h: float = 1e-7, lcfg: LS.LossCfg = LS.LossCfg()) -> List[Dict]:
    """Central differences with a tiny step on single recordings (inside a smooth piece unless a discrete event of
    the frequency tracker sits within +-h), against the adjoint."""
    out = []
    for n, it in enumerate(items):
        rs = DA.build_set([it])
        th = TA.to_theta(start).requires_grad_(True)
        objective(rs, th, static, None, lcfg, grad=True).backward()
        for k in keys:
            i = TA.TRAIN_KEYS.index(k)
            tp = th.detach().clone(); tp[i] += h
            tm = th.detach().clone(); tm[i] -= h
            fd = (float(objective(rs, tp, static, None, lcfg, grad=False)) - float(objective(rs, tm, static, None, lcfg, grad=False))) / (2 * h)
            g = float(th.grad[i])
            out.append({"recording": n, "param": k, "adjoint": g, "fd": fd, "rel_err": abs(fd - g) / max(abs(g), 1e-12)})
    return out
