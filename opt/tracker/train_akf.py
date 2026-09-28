r"""Tuning every AKF parameter by backpropagation through time (the discrete adjoint of the filter), SIMULATION.

theta: the 23 parameters of opt.tracker.torch_akf.TRAIN_KEYS (positive ones log-transformed; the frequency
bounds, the frequency-gate centre, the amplitude-gate centre and the horizon linear): process and measurement
noises, oscillator decay, initial frequency, frequency smoothing and window, frequency gate (centre, width),
amplitude gate (centre, width), amplitude smoothing, prediction horizon, authority smoothing, gain, output
low-pass, amplitude cap (k, slow-motion speed, reference time).  Structure kept fixed per run: the second
harmonic (harm 0/1), the cross-track option (off).

Loop: full-batch Adam on the training set (opt.tracker.data train: 96 sigma-lognormal + 64 glyph-writer pairs,
40 % glyph; the gradient is accumulated over four mini-batches), objective opt.tracker.losses (tremor-band
residual + lambda_fc x false correction (glyph writers weighted 3:1) + mu x estimate RMS above 150 Hz).  The gates
always take their exact (numba) values; during the first 70 % of the iterations their gradient leaks outside the
ramp (straight-through, 0.1 decaying to 0) so that closed gates still get a first-order signal.  (Softplus-smoothed
gates were tried first: they optimise a leakier function than the deployed one and the hard-gate validation got
worse; see build logs.)  Parameters are clamped to physical ranges after each step.  Every
`val_every` iterations the objective is evaluated with the exact (hard) gates on the validation sets (val pairs,
tuning seeds 5004-5007, aiguide tuning writers 100-105); the iterate with the lowest validation objective is kept.
Never the test seeds 200-203 or the aiguide test writers 0-5.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import torch

from . import data as DA
from . import losses as LS
from . import torch_akf as TA

KEYS = TA.TRAIN_KEYS

# physical ranges (value units as the numba dict; a_c in m, horizon in s)
BOUNDS = {"qj": (1e-5, 1e4), "qt": (1e-14, 1e-4), "qh": (1e-16, 1e-4), "qb": (1e-12, 1e-1), "ra": (1e-7, 10.0),
          "rp": (1e-14, 1e-7), "tau_decay": (0.02, 10.0), "w0_hz": (2.0, 15.0), "tau_w": (0.005, 5.0),
          "wmin_hz": (1.5, 8.0), "wmax_hz": (8.0, 20.0), "f_gate": (0.5, 12.0), "f_gate_w": (0.1, 10.0),
          "a_c": (-100e-6, 600e-6), "a_w": (1e-7, 1e-3), "tau_amp": (0.002, 5.0), "horizon": (-3e-3, 8e-3),
          "tau_auth": (0.002, 2.0), "g": (0.2, 2.0), "lp_hz": (5.0, 400.0), "cap_k": (0.3, 100.0),
          "v_slow": (1e-4, 0.2), "tau_ref": (0.01, 10.0)}


def _bounds_theta(keys=KEYS):
    lo, hi = [], []
    for k in keys:
        kind, sc = TA.PARAM_DEFS[k]
        a, b = BOUNDS[k]
        if kind == "log":
            lo.append(math.log(a / sc)); hi.append(math.log(b / sc))
        else:
            lo.append(a / sc); hi.append(b / sc)
    return torch.tensor(lo, dtype=TA.DT), torch.tensor(hi, dtype=TA.DT)


def project(theta: torch.Tensor, keys=KEYS):
    lo, hi = _bounds_theta(keys)
    with torch.no_grad():
        theta.copy_(torch.maximum(torch.minimum(theta, hi), lo))
        # wmax at least 1 Hz above wmin
        iw, ix = keys.index("wmin_hz"), keys.index("wmax_hz")
        theta[..., ix] = torch.maximum(theta[..., ix], theta[..., iw] + 1.0)
    return theta


@dataclass
class TrainCfg:
    lam_fc: float = 0.2
    mu_hf: float = 0.02
    w_glyph_fc: float = 3.0
    iters: int = 60
    lr: float = 0.03
    leak0: float = 0.1               # straight-through gradient outside the gate ramps, annealed to 0
    smooth_frac: float = 0.7          # after this fraction of the iterations: exact gradients (leak 0)
    val_every: int = 5
    grad_clip: float = 5.0
    harm: float = 1.0
    rr_mode: str = "aggregate"
    lr_min_frac: float = 0.1          # cosine decay of the learning rate to this fraction over the iterations

    def loss_cfg(self) -> LS.LossCfg:
        return LS.LossCfg(lam_fc=self.lam_fc, mu_hf=self.mu_hf, w_glyph_fc=self.w_glyph_fc, rr_mode=self.rr_mode)


def beta_at(it: int, cfg: TrainCfg):
    """Gate mode at iteration it: exact ramp values always; leaky straight-through gradient decaying to 0."""
    n = max(1, int(cfg.smooth_frac * cfg.iters))
    if it >= n or cfg.leak0 <= 0:
        return None
    return ("leaky", float(cfg.leak0 * (1.0 - it / n)))


def static_for(harm: float) -> Dict:
    return {"harm": float(harm), "xtrack": 0.0, "v_xt": 5e-3, "acc_gd": 1.04e-3, "gap_reset": 0.03, "use_pos": 1.0,
            "use_acc": 1.0}


def validate(val_sets: Dict[str, DA.RecSet], vals: Dict, static: Dict, lcfg: LS.LossCfg) -> Dict:
    out = {}
    Js = []
    for name, rs in val_sets.items():
        J, info, _, _ = DA.evaluate(rs, vals, static, None, lcfg)
        out[name] = info
        Js.append(info["J"])
    out["J_mean"] = float(np.mean(Js))
    return out


def minibatches(items: List[Dict], n_batches: int, seed: int = 0) -> List[DA.RecSet]:
    """Fixed partition of the training pairs (tremor + tremor-free run stay together) into n_batches RecSets,
    stratified by writer type."""
    pairs = {}
    for it in items:
        key = (it["meta"]["set"], it["meta"]["i"])
        pairs.setdefault(key, []).append(it)
    keys = sorted(pairs)
    rng = np.random.default_rng(seed)
    gl = [k for k in keys if pairs[k][0]["glyph"]]
    lg = [k for k in keys if not pairs[k][0]["glyph"]]
    rng.shuffle(gl); rng.shuffle(lg)
    parts = [[] for _ in range(n_batches)]
    for j, k in enumerate(lg + gl):
        parts[j % n_batches].append(k)
    return [DA.build_set([it for k in sorted(p) for it in pairs[k]]) for p in parts]


def train(tr, val_sets: Dict[str, DA.RecSet], start: Dict, cfg: TrainCfg, log: Callable = print,
          tag: str = "") -> Dict:
    """tr: a RecSet or a list of mini-batch RecSets (cycled in a random order per epoch); start: values of KEYS.
    Returns the best iterate by validation objective (hard gates)."""
    batches = tr if isinstance(tr, (list, tuple)) else [tr]
    order_rng = np.random.default_rng(1)
    order: List[int] = []
    static = static_for(cfg.harm)
    lcfg = cfg.loss_cfg()
    theta = project(TA.to_theta(start).clone()).requires_grad_(True)
    optim = torch.optim.Adam([theta], lr=cfg.lr)
    sched = torch.optim.lr_scheduler.LambdaLR(
        optim, lambda i: cfg.lr_min_frac + (1.0 - cfg.lr_min_frac) * 0.5 * (1.0 + math.cos(math.pi * min(i, cfg.iters) / max(1, cfg.iters))))
    hist: List[Dict] = []
    best = None
    t0 = time.time()
    for it in range(cfg.iters + 1):
        beta = beta_at(it, cfg)
        do_val = (it % cfg.val_every == 0) or it == cfg.iters
        if do_val:
            with torch.no_grad():
                vals_now = {k: float(v) for k, v in TA.from_theta(theta.detach()).items()}
            v = validate(val_sets, vals_now, static, lcfg)
            rec = {"iter": it, "val": v, "elapsed_s": time.time() - t0}
            if best is None or v["J_mean"] < best["val"]["J_mean"]:
                best = {"iter": it, "val": v, "theta": theta.detach().clone(), "vals": vals_now}
            hist.append(rec)
            log(f"[{tag}] it {it:3d} VAL J {v['J_mean']:.4f} | " + " | ".join(
                f"{n}: rr {v[n].get('rr_band', float('nan')):.3f} (mean {v[n].get('rr_band_all', float('nan')):.3f}) fc {v[n].get('fc_w_um', float('nan')):.1f} hf {v[n].get('hf_um', float('nan')):.2f}"
                for n in val_sets) + f" ({time.time() - t0:.0f} s)")
        if it == cfg.iters:
            break
        # full-batch gradient: the objective is the mean of the mini-batch objectives
        optim.zero_grad()
        infos = []
        for rs in batches:
            J, info, _, _ = DA.evaluate(rs, TA.from_theta(theta), static, beta, lcfg, grad=True)
            (J / len(batches)).backward()
            infos.append(info)
        info = {k: float(np.mean([x[k] for x in infos])) for k in ("J", "rr_band", "fc_w_um", "hf_um", "rr_band_all")}
        g = theta.grad
        bad = ~torch.isfinite(g)
        if bool(bad.any()):
            log(f"[{tag}] it {it}: non-finite gradient in {[KEYS[i] for i in np.flatnonzero(bad.numpy())]}; zeroed")
            g[bad] = 0.0
        gn = float(g.norm())
        if gn > cfg.grad_clip:
            g.mul_(cfg.grad_clip / gn)
        optim.step()
        sched.step()
        project(theta)
        hist.append({"iter": it, "train": info, "beta": beta, "grad_norm": gn, "lr": float(optim.param_groups[0]["lr"])})
        if True:
            log(f"[{tag}] it {it:3d} train J {info['J']:.4f} rr {info['rr_band']:.3f} fc {info['fc_w_um']:.1f} "
                f"hf {info['hf_um']:.2f} |g| {gn:.3f} beta {beta} ({time.time() - t0:.0f} s)")
    return {"best": {"iter": best["iter"], "val": best["val"], "vals": best["vals"],
                     "numba_params": TA.to_numba(best["vals"], static), "theta": best["theta"].tolist()},
            "last_vals": {k: float(v) for k, v in TA.from_theta(theta.detach()).items()},
            "history": hist, "cfg": asdict(cfg), "elapsed_s": time.time() - t0, "static": static}
