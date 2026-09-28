"""P1 runs that score a touchdown law (SIMULATION on synthetic handwriting; nothing measured).

Per seed and tilt:
  rigid   conventional pen (stage and slide locked, no skid) on the tremor-free writing: the ink reference
  clean   the pencil with the law, NEUTRAL (no tremor correction) on the tremor-free writing: tails and missing ink
  ratio   harness convention of sim/pencil/run_study.py with the law on in every run: reference = `clean`,
          ratio = e_rms(controller, tremor) / e_rms(neutral, tremor) for tremor 6 Hz / 0.3 mm; the oracle gets the
          clean housing path as its disturbance reference; the Kalman is the frozen M1 set (M.kalman_controller()).
Seeds: tuning on training seeds (300-319); the test seeds 200-203 are only used by run_study's final validation.
"""
from __future__ import annotations

import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Iterable, Optional

import numpy as np

import sim.pencil  # noqa: F401  (NUMBA_CACHE_DIR outside sim/pensim)
from sim.pencil import evaluate as E
from sim.pencil import model as M
from sim.pensim import scenarios
from stabpen import signals as sg

from . import metrics as MT
from .law import TouchdownLaw

TRAIN_SEEDS = tuple(range(300, 320))
TEST_SEEDS = (200, 201, 202, 203)
DUR = 5.2
TREMOR = sg.TremorSpec(f0=6.0, amp_pk=0.3e-3)
WORKERS = int(os.environ.get("TD_WORKERS", "2"))

_rigid_cache: Dict = {}


def writing(seed, theta=50.0, tremor=None, duration=DUR):
    return scenarios.handwriting(seed=seed, duration=duration, tremor=tremor, theta_deg=theta, N0=1.0)


def rigid_run(seed, theta=50.0, duration=DUR):
    key = (seed, theta, duration)
    if key not in _rigid_cache:
        _rigid_cache[key] = M.run(writing(seed, theta, None, duration), M.Controller(mode="neutral"),
                                  M.PencilConfig(locked=True), seed=seed + 1)
    return _rigid_cache[key]


CTRL_KEYS = ("ff_ref",)          # servo settings that live on the Controller, not on PencilConfig


def _cfg(law: TouchdownLaw, servo: Optional[dict]):
    return law.pencil_config(**{k: v for k, v in (servo or {}).items() if k not in CTRL_KEYS})


def _ck(servo: Optional[dict]):
    return {k: v for k, v in (servo or {}).items() if k in CTRL_KEYS}


def score_seed(law: TouchdownLaw, seed: int, theta=50.0, tremor=True, kalman=False, servo=None, duration=DUR,
               keep=False):
    """All metrics of one seed; keep=True also returns the Result objects."""
    cfg = _cfg(law, servo)
    ck = _ck(servo)
    sc0 = writing(seed, theta, None, duration)
    rig = rigid_run(seed, theta, duration)
    clean = M.run(sc0, M.Controller(mode="neutral", **ck), cfg, seed=seed + 1)
    row = {"seed": seed, "theta": theta}
    row.update(MT.ink_vs_rigid(clean, rig))
    row.update({"clean_" + k: v for k, v in MT.travel_stats(clean).items()})
    runs = {"rigid": rig, "clean": clean}
    if tremor:
        sc1 = writing(seed, theta, TREMOR, duration)
        rn = M.run(sc1, M.Controller(mode="neutral", **ck), cfg, seed=seed + 1)
        base = E.compare(rn, clean)
        ro = M.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, clean)), M.Controller(mode="oracle", **ck), cfg, seed=seed + 1)
        mo = E.compare(ro, clean)
        row.update({"oracle_ratio": mo["e_rms_um"] / base["e_rms_um"], "neutral_e_rms_um": base["e_rms_um"],
                    "oracle_q_sat_frac": mo["q_sat_frac"], "oracle_frac_vsat": mo["frac_vsat"],
                    "oracle_P_rail_classB_mW": mo["P_rail_classB_mW"], "oracle_P_rail_recovery_mW": mo["P_rail_recovery_mW"],
                    "oracle_lost_contact_frac": float(np.mean((clean["contact"][:len(ro["t"])] > 0) & (ro["contact"][:len(clean["t"])] <= 0))),
                    "oracle_tail_extra_mm": MT.ink_vs_rigid(ro, rig)["extra_tr_mm"]})
        row.update({"oracle_" + k: v for k, v in MT.travel_stats(ro).items()})
        runs.update({"neutral_tremor": rn, "oracle": ro})
        if kalman:
            rk = M.run(sc1, M.kalman_controller(**ck), cfg, seed=seed + 1)
            mk = E.compare(rk, clean)
            row.update({"kalman_ratio": mk["e_rms_um"] / base["e_rms_um"], "kalman_q_sat_frac": mk["q_sat_frac"],
                        "kalman_P_rail_classB_mW": mk["P_rail_classB_mW"], "kalman_tail_extra_mm": MT.ink_vs_rigid(rk, rig)["extra_tr_mm"]})
            runs["kalman"] = rk
    if keep:
        return row, runs
    return row


def _score_task(args):
    law, seed, kw = args
    return score_seed(law, seed, **kw)


def score(law: TouchdownLaw, seeds: Iterable[int], workers: int = WORKERS, pool=None, **kw):
    """Rows for all seeds, and the aggregate: per-stroke ink metrics plus seed means of the ratios."""
    tasks = [(law, s, kw) for s in seeds]
    if pool is not None:
        rows = list(pool.map(_score_task, tasks))
    elif workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            rows = list(ex.map(_score_task, tasks))
    else:
        rows = [_score_task(t) for t in tasks]
    return aggregate(rows), rows


def aggregate(rows):
    agg = MT.per_stroke(rows)
    agg.update({"words_" + k: v for k, v in MT.per_stroke(rows, norm="words_rigid").items() if k in MT.PER_PD})
    for k in ("oracle_ratio", "kalman_ratio", "oracle_q_sat_frac", "oracle_frac_vsat", "oracle_P_rail_classB_mW",
              "oracle_P_rail_recovery_mW", "oracle_lost_contact_frac", "oracle_limit_frac_contact", "clean_limit_frac_contact",
              "kalman_q_sat_frac", "kalman_P_rail_classB_mW", "neutral_e_rms_um"):
        v = [r[k] for r in rows if k in r and np.isfinite(r[k])]
        if v:
            agg[k] = float(np.mean(v))
            agg[k + "_sd"] = float(np.std(v))
    for k in ("oracle_tail_extra_mm", "kalman_tail_extra_mm"):
        if all(k in r for r in rows):
            agg[k.replace("_mm", "_per_pd")] = float(sum(r[k] for r in rows) / max(sum(r["pen_downs_rigid"] for r in rows), 1))
    agg["clean_qff_peak_contact_mm"] = float(max(r.get("clean_qff_peak_contact_mm", 0.0) for r in rows))
    agg["n_seeds"] = len(rows)
    return agg


def warm():
    """Compile the numba core in this process."""
    t0 = time.time()
    M.run(scenarios.handwriting(seed=1, duration=0.3), M.Controller(mode="neutral"),
          TouchdownLaw().pencil_config())
    return time.time() - t0


def quasi_static_touchdown(theta=50.0, v_down=1e-3, h0=0.6e-3, t_air=0.15, t_hold=0.25, dt=25e-6, N0=1.0):
    """Hand holding the pen h0 above writing height for t_air (the stage settles on its pre-position), then lowering it
    slowly (v_down) onto the page and holding it; no lateral motion, no tremor: the kinematic check of the law."""
    from stabpen import signals as sg
    T = t_air + h0 / v_down + t_hold
    n = int(round(T / dt))
    t = np.arange(n) * dt
    z = np.clip(h0 - v_down * np.clip(t - t_air, 0.0, None), 0.0, None)
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=z <= 0, lift=z, features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)), N0, theta)
    return sc


def contact_point_drift(r, s_ref, theta_deg):
    """Deviation of the ink point from its working position under the housing (C - p_H - s_ref cos(th) along the
    azimuth, and sideways) while the ball is on the page; also the drift of the page contact point after first contact."""
    th = math.radians(theta_deg)
    c = r["contact"] > 0
    if not c.any():
        return {"contact": False}
    i0 = int(np.argmax(c))
    dev_x = (r["Cx"] - r["pHx"] - s_ref * math.cos(th))[c]
    dev_y = (r["Cy"] - r["pHy"])[c]
    Cx0, Cy0 = r["Cx"][i0], r["Cy"][i0]
    drift = np.hypot(r["Cx"][c] - Cx0, r["Cy"][c] - Cy0)
    return {"contact": True, "t_first_contact_s": float(r["t"][i0]), "max_abs_dev_um": float(np.max(np.hypot(dev_x, dev_y)) * 1e6),
            "rms_dev_um": float(np.sqrt(np.mean(dev_x ** 2 + dev_y ** 2)) * 1e6), "max_drift_um": float(np.max(drift) * 1e6),
            "slide_range_um": float(np.ptp(r["s"][c]) * 1e6)}


def slow_descents(law: TouchdownLaw, theta=50.0, speeds=(1e-3, 10e-3), servo=None):
    """Contact-point deviation of slow touchdowns (the hand lowering the pen at 1 and 10 mm/s; sensor noise and
    hysteresis on).  Handwriting only exercises fast (~50-60 mm/s) touchdowns; this keeps the law honest for slow ones."""
    out = {}
    for v in speeds:
        sc = quasi_static_touchdown(theta, v_down=v, t_hold=0.15)
        r = M.run(sc, M.Controller(mode="neutral", **_ck(servo)), _cfg(law, servo), seed=7)
        if law.enabled:
            s_ref = r.info["touchdown_ff"]["s_ref"]
        else:
            s_ref = M.working_slide(math.radians(theta), 1.0, r.P[M.IDX["F_sp0"]], r.P[M.IDX["k_p"]], r.P[M.IDX["k_sk"]])
        d = contact_point_drift(r, s_ref, theta)
        out[f"{v * 1e3:g}mm_s"] = {"max_dev_um": d["max_abs_dev_um"], "rms_dev_um": d["rms_dev_um"], "drift_um": d["max_drift_um"],
                                   "transitions": int(len(MT.transitions(r)))}
    out["mean_max_dev_um"] = float(np.mean([out[k]["max_dev_um"] for k in out if k.endswith("mm_s")]))
    return out
