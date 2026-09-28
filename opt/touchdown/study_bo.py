"""Optimisation stages of the touchdown study (training seeds only): baselines, the feed-forward + margin search
(ParEGO Bayesian optimisation on P1), the travel-priority comparison, the held-out check of the pick, and the
servo search.  Every number these stages produce is a SIMULATION result on synthetic handwriting.
"""
from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import bo
from . import law as L
from . import runs
from . import servo as S

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "opt")
LOGS = os.path.join(OUT, "logs")
BO_SEEDS = tuple(range(300, 310))          # search seeds
HOLDOUT_SEEDS = tuple(range(310, 320))     # held-out training seeds for the pick (the test seeds stay unseen)
FF_SPACE = {k: L.BOUNDS[k] for k in ("margin", "gain", "kappa", "pre", "lead_s", "lp_hz", "dz", "k_load", "det_e", "hold_s", "v_td")}
FIXED = {"det_s": 20e-6, "prio": 1, "bias": 1, "handover": 1}


def objectives(agg, rms_ref_um, slow=None):
    """f_tail: touchdown and lift ink per rigid pen-down (mm): extra ink at transitions with the 0.2 mm tolerance of
    REQ-PNC-006, a quarter of it at 0.1 mm (resolution below the tolerance), missing ink beyond 0.03 mm (x2), a guard
    against in-stroke drift (0.01 mm per um of nearest-point RMS beyond rms_ref + 2 um), and half the mean peak
    contact-point deviation of slow touchdowns (1 and 10 mm/s; runs.slow_descents) in mm.
    f_ratio: oracle correction ratio at 6 Hz / 0.3 mm plus the contact time with the stage at its limit beyond 13 %."""
    f_tail = (agg["extra_tr_mm"] + 0.25 * agg["extra_tr_tight_mm"] + 2.0 * max(0.0, agg["missing_mm"] - 0.03)
              + 0.01 * max(0.0, agg["rms_nn_instroke_um"] - rms_ref_um - 2.0)
              + (0.5e-3 * slow["mean_max_dev_um"] if slow else 0.0))
    f_ratio = agg["oracle_ratio"] + max(0.0, agg.get("oracle_limit_frac_contact", 0.0) - 0.13)
    return f_tail, f_ratio


def baselines(pool, seeds=BO_SEEDS, margins=(0.1e-3, 0.2e-3, 0.3e-3, 0.4e-3)):
    out = {}
    for name, law in [("tilt_range_stop", L.tilt_range_stop())] + [(f"adaptive_{m * 1e3:.1f}mm", L.adaptive_stop(m)) for m in margins]:
        agg, rows = runs.score(law, seeds, pool=pool)
        out[name] = {"law": law.as_dict(), "agg": agg, "slow": runs.slow_descents(law)}
        print("baseline", name, {k: round(agg[k], 4) for k in ("extra_mm", "extra_tr_mm", "extra_tr_tight_mm", "missing_mm",
                                                                "rms_nn_instroke_um", "oracle_ratio", "oracle_limit_frac_contact")}, flush=True)
    return out


def ff_search(pool, rms_ref_um, n_init=24, n_iter=100, x0=None, log_name="ff_bo.jsonl", seeds=BO_SEEDS, seed=1):
    space = bo.Space(FF_SPACE, log=L.LOG_PARAMS)

    def evaluate(xd):
        law = L.TouchdownLaw(**xd, **FIXED)
        agg, _ = runs.score(law, seeds, pool=pool)
        slow = runs.slow_descents(law)
        f_tail, f_ratio = objectives(agg, rms_ref_um, slow)
        return {"f_tail": f_tail, "f_ratio": f_ratio, "slow_mean_max_dev_um": slow["mean_max_dev_um"],
                "slow_1mm_s_max_dev_um": slow["1mm_s"]["max_dev_um"], "slow_10mm_s_max_dev_um": slow["10mm_s"]["max_dev_um"],
                **{k: v for k, v in agg.items() if not k.endswith("_sd")}}
    os.makedirs(LOGS, exist_ok=True)
    rows = bo.parego(space, evaluate, ["f_tail", "f_ratio"], n_init=n_init, n_iter=n_iter, log_path=os.path.join(LOGS, log_name),
                     seed=seed, x0=x0)
    return rows


def pareto(rows, keys=("f_tail", "f_ratio")):
    F = np.array([[r["f"][k] if k in r["f"] else r["res"][k] for k in keys] for r in rows])
    m = bo.pareto_mask(F)
    return [rows[i] for i in np.flatnonzero(m)]


def pick(rows, ratio_cap):
    """Lowest f_tail among the points whose oracle ratio is within ratio_cap; ties broken by the ratio."""
    ok = [r for r in rows if r["res"]["oracle_ratio"] <= ratio_cap]
    ok = ok or rows
    return min(ok, key=lambda r: (round(r["f"]["f_tail"], 4), r["res"]["oracle_ratio"]))


def holdout(pool, candidates, rms_ref_um, seeds=HOLDOUT_SEEDS):
    """Re-score the leading candidates on the held-out training seeds (guards against a lucky pick)."""
    out = []
    for name, xd in candidates:
        law = L.TouchdownLaw(**xd, **FIXED)
        agg, _ = runs.score(law, seeds, pool=pool)
        slow = runs.slow_descents(law)
        ft, fr = objectives(agg, rms_ref_um, slow)
        out.append({"name": name, "x": xd, "f_tail": ft, "f_ratio": fr, "agg": agg, "slow": slow})
        print("holdout", name, round(ft, 4), round(fr, 4), flush=True)
    return out


def priority_check(pool, xd, rms_ref_um, seeds=BO_SEEDS):
    out = {}
    for prio in (0, 1, 2):
        law = L.TouchdownLaw(**xd, **dict(FIXED, prio=prio))
        agg, _ = runs.score(law, seeds, pool=pool, kalman=True)
        ft, fr = objectives(agg, rms_ref_um, runs.slow_descents(law))
        out[{0: "shared", 1: "feedforward_first", 2: "tremor_first"}[prio]] = {"f_tail": ft, "f_ratio": fr, "agg": agg}
        print("priority", prio, round(ft, 4), round(fr, 4), round(agg.get("kalman_ratio", float("nan")), 4), flush=True)
    return out


# ------------------------------------------------------------------ servo search
def servo_search(pool, hall_noise=1e-6, n_init=16, n_iter=40, seeds=tuple(range(300, 306)), log_name=None):
    space = bo.Space(S.SERVO_BOUNDS, log=S.SERVO_LOG)
    log_name = log_name or f"servo_bo_hall{hall_noise * 1e6:.1f}um.jsonl"

    def evaluate(xd):
        mg = S.loop_margins(**xd)
        if not mg["feasible_nominal"]:
            # infeasible: not simulated; scored by distance to the rule so the GP learns the boundary
            viol = (max(0.0, S.RULE["pm_min_deg"] - mg["pm_min_nominal_deg"]) / 10 + max(0.0, S.RULE["gm_min_db"] - mg["gm_min_nominal_db"]) / 3
                    + max(0.0, mg["peak_S_nominal"] - S.RULE["peak_s_max"]))
            return {"track_um": 40.0 + 20 * viol, "P_rail_classB_mW": 400.0 + 100 * viol, "feasible": False,
                    "pm": mg["pm_min_nominal_deg"], "gm": mg["gm_min_nominal_db"], "peak_S": mg["peak_S_nominal"]}
        agg, _ = S.score_servo(xd, seeds, pool=pool, hall_noise=hall_noise)
        return {**agg, "feasible": True, "pm": mg["pm_min_nominal_deg"], "gm": mg["gm_min_nominal_db"], "peak_S": mg["peak_S_nominal"],
                "pm_tol20": mg["pm_min_deg"]}
    os.makedirs(LOGS, exist_ok=True)
    return bo.parego(space, evaluate, ["track_um", "P_rail_classB_mW"], n_init=n_init, n_iter=n_iter,
                     log_path=os.path.join(LOGS, log_name), seed=3, x0=[dict(S.DEFAULT)], feasible=S.feasible)


def servo_pick(rows, track_cap=None, pm_tol_min=None):
    """Returns (default, lowest rail power at no worse tracking than the default (or track_cap), best tracking at no
    more rail power than the default), among designs meeting the margin rule at nominal stiffness and, when
    pm_tol_min is given, keeping at least that phase margin with the stage stiffness at +-20 % (robustness)."""
    feas = [r for r in rows if r["res"].get("feasible")]
    if pm_tol_min is not None:
        feas = [r for r in feas if r["res"].get("pm_tol20", -1e9) >= pm_tol_min - 1e-9]
    base = next(r for r in rows if r["tag"] == "x0")
    cap = track_cap if track_cap is not None else base["res"]["track_um"]
    ok = [r for r in feas if r["res"]["track_um"] <= cap] or feas
    low_power = min(ok, key=lambda r: r["res"]["P_rail_classB_mW"])
    best_track = min([r for r in feas if r["res"]["P_rail_classB_mW"] <= base["res"]["P_rail_classB_mW"]] or feas,
                     key=lambda r: r["res"]["track_um"])
    return base, low_power, best_track
