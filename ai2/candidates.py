"""The closed-loop variants of tasks 2 and 3 on one scenario (model HW1): the model-based causal stack, the learned
estimators, the RL arbiter and the residual RL policy, all causal (lag 0), built from the same sensor streams.

Evidence status: SIMULATION tooling.  Commands are per control tick; every estimate at a tick uses sensor data
available by that tick (fixed-lag RTS outputs every tick; learned outputs every 2 ms held and extrapolated causally;
policy weights held for their 20 ms decision period; residual actions held for 2 ms).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from . import ensure_paths
from . import common as C
from . import data as DA
from . import delayed as DL
from . import learned as LE
from . import rl_env as RE
from . import smoothers as SM

ensure_paths()
from aiprior import core as CO  # noqa: E402
from fusion import learned as FL  # noqa: E402

LAGS_CL = np.round(np.arange(0.0, 0.1001, 0.005), 6)     # estimator lags for closed-loop runs (0-100 ms)
CAL_SEED_OFFSET = 5000                                    # the calibration recording's seed offset
CAL_CLEAN = (8.0, 1.0e-3)                                 # tremor-free test: the user's tremor at calibration


def load(quick: bool, modes=None) -> Dict:
    """The trained learned models and the chosen RL policies (None where a stage has not run)."""
    from . import stage_learn as SL
    from . import stage_rl as SR
    out = {"learned": {}, "arbiter": None, "residual": None, "info": {}}
    learn = C.load("learn", quick)
    if learn:
        for mode in (modes or learn["models"].keys()):
            try:
                out["learned"][mode] = SL.load_model(mode, quick)[0]
            except FileNotFoundError:
                pass
    rl = C.load("rl", quick)
    if rl:
        # the residual policy is shown even when no residual run passed its rule (information): the chosen one, else
        # the FC-weighted run, else the plain run
        res_key = rl.get("chosen_residual") or next((k for k in ("residual_ppo_fc", "residual_ppo") if k in rl["policies"]), None)
        for kind, key in (("arbiter", rl.get("chosen_arbiter")), ("residual", res_key)):
            pol = rl["policies"].get(key) if key else None
            if pol:
                out[kind] = SR.load_policy(pol["best"]["path"])
                out["info"][kind] = {"policy": key, "steps": pol["best"]["steps"], "passes_rule": pol["passes_rule"]}
    return out


def calibration(wr, f0: float, amp: float, seed: int, det_params: Dict) -> Tuple[float, float]:
    """The 20 s calibration: the tremor-line detector on a separate recording of the same writer and tremor (another
    seed); the median line frequency and amplitude while the gate is open; (0, 0) if it never opens."""
    if amp <= 0:
        f0, amp = CAL_CLEAN
    sc = CO.make_scenario(wr, f0, amp, seed + CAL_SEED_OFFSET)
    det = SM.detector(sc.streams, det_params)
    m = np.asarray(det["gate"]) > 0.5
    if not m.any():
        return 0.0, 0.0
    return float(np.median(np.asarray(det["f_hat"])[m])), float(np.median(np.asarray(det["amp"])[m]))


def arrays(sc, mp: Dict):
    X, tk = FL.features(sc.streams, DA.NET_HZ)
    mb = DA.model_based(sc.streams, sc.pen, tk, mp["tremor"], mp["det"])
    return X, tk, mb


def commands(sc, est: Dict, mp: Dict, cands: Dict, X, tk, mb, ctx: Optional[Tuple[float, float]] = None,
             keep_est: Optional[Dict] = None) -> Dict:
    """q per tick for each available variant (lag 0).  keep_est (a dict) receives each learned model's estimate
    structure (for the delayed-ink variants of the test stage)."""
    tick_t = sc.streams.tick_t
    zeros = np.zeros(len(tick_t))
    out = {"gated": DL.command(est, zeros, tick_t)}
    ones = np.ones(len(est["t"]))
    for mode, model in cands["learned"].items():
        if mode == "ctx" and ctx is None:
            continue
        Y = LE.predict(model, LE.make_inputs(mode, X, mb, ctx if mode == "ctx" else None, mp["amp_gate"]))
        D = LE.hold_extrapolate(tk, LE.on_lag_grid(Y, DA.LAGS, est["lags"]), est["t"])
        e = dict(est, D=D, g=ones)
        if keep_est is not None:
            keep_est[mode] = e
        out[f"learned_{mode}"] = DL.command(e, zeros, tick_t)
    ep = dict(mb, X=X, Y=np.zeros((len(tk), len(DA.LAGS), 2), np.float32), mask=np.zeros(len(tk), np.float32), spec={})
    if cands.get("arbiter") is not None:
        w = RE.policy_weights(cands["arbiter"], ep)
        k = np.clip(np.searchsorted(tk, est["t"] + 1e-9, side="right") - 1, 0, len(tk) - 1)
        out["rl_arbiter"] = DL.command(dict(est, g=w[k]), zeros, tick_t)
    if cands.get("residual") is not None:
        a = RE.residual_actions(cands["residual"], ep, mp["amp_gate"])
        k = np.clip(np.searchsorted(tk, tick_t + 1e-9, side="right") - 1, 0, len(tk) - 1)
        out["rl_residual"] = np.ascontiguousarray(out["gated"] - RE.RES_SCALE * a[k])
    return out


def base_cfg(mp: Dict) -> DL.DelayCfg:
    cfg = DL.DelayCfg(tremor=mp["tremor"], det=mp["det"])
    cfg.amp_lo, cfg.amp_hi = mp["amp_gate"]
    cfg.lam_max, cfg.alpha, cfg.beta = 0.0, 1.0, 6.0
    return cfg
