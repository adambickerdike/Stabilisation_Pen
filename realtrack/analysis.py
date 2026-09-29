"""Analyses that explain the results (tuning split only; SIMULATION with real inputs, CALC for the servo lag).

  separability   why the gates fail on real inputs: the tremor-line detector's peak ratio (ai2's detector on the page
                 track, and on an accelerometer-only track) and the amplitude of the raw listening estimate, per level
                 (no tremor, moderate, severe), pen-down time, DeltaPen-class page sensor
  delay          the servo lag (CALC), the latency chain, the decomposition ordinary pen -> nose held -> Rev H tracker,
                 and horizon sweeps of the Rev H tracker and of the chosen design
  learned        the linear FIR bound, the TCN trained on real tuning inputs (cross-fitted) and ai2's TCN (trained on
                 synthetic writers), raw and with the soft authority, on the same tuning cases
Each writes realtrack/build/<name>.json (read by report.py).
"""
from __future__ import annotations

import json
import time
from typing import Dict

import numpy as np

from . import BUILD_DIR
from . import cases as C
from . import estimators as E

Q = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 0.999]


def separability(log=print) -> Dict:
    p = BUILD_DIR / "separability.json"
    if p.exists():
        return json.loads(p.read_text())
    from . import search as SR
    t0 = time.time()
    L = SR.listening_design()
    acc: Dict = {}
    for s in C.tuning_specs():
        if s["level"] not in ("clean", "moderate", "severe"):
            continue
        c = C.load_case(s)
        st = c.streams("deltapen")
        down = c.arrays["down_ticks"] > 0.5
        lev = s["level"]
        acc.setdefault(("line ratio, page track 4 s (ai2's detector)", lev), []).append(
            E.det_ratio(st, {"win": 4.0, "seg": 2.0, "band_lo": 4.5, "band_hi": 13.5}, contact_only=False)["ratio"][down])
        acc.setdefault(("line ratio, accelerometer track 2 s", lev), []).append(
            E.det_ratio_imu(st, {"win": 2.0, "seg": 1.0, "band_lo": 3.5, "band_hi": 12.0})["ratio"][down])
        d, _ = E.raw_estimate("akf", st, L["params"])
        _, _, A = E.authority(d, float(c.meta["Ts"]), {"tau_amp": 1.0})
        acc.setdefault(("amplitude of the listening estimate, mm (1 s)", lev), []).append(A[down] * 1e3)
        del c, st
    out = {"q": Q}
    for (feat, lev), v in acc.items():
        x = np.concatenate(v)
        out.setdefault(feat, {})[lev] = [float(np.quantile(x, q)) for q in Q]
        out[feat].setdefault("_share_above", {})
        if "ratio" in feat:
            out[feat]["_share_above"][lev] = {str(t): float(np.mean(x > t)) for t in (3, 5, 8)}
    out["label"] = "SIMULATION (HW1) with real inputs, tuning split, DeltaPen-class page sensor; pen-down ticks"
    out["elapsed_s"] = time.time() - t0
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] separability in {out['elapsed_s']:.0f} s")
    return out


def delay(chosen: Dict, log=print) -> Dict:
    from . import delay as DY
    p = BUILD_DIR / "delay.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    out = {"servo_lag": DY.servo_lag(), "budget": DY.budget(), "decompose": DY.decompose(),
           "horizon": {"Rev H tracker (as built)": DY.horizon_sweep({"family": "revh", "name": "revh"}, log=log),
                       "chosen design": DY.horizon_sweep(chosen, log=log)}}
    # the effective lag of the Rev H tracker and of the chosen design against the truth (severe cases)
    lags = {"revh": [], "chosen": []}
    for s in C.tuning_specs():
        if s["level"] != "severe":
            continue
        c = C.load_case(s)
        st = c.streams("deltapen")
        for nm, dz in (("revh", {"family": "revh"}), ("chosen", chosen)):
            d, _ = E.estimate(dz, st, case=c)
            lags[nm].append(DY.xcorr_lag(d, c))
        del c, st
    out["xcorr"] = {k: {"lag_ms_median": float(np.median([x["lag_ms"] for x in v])),
                        "gain_median": float(np.median([x["gain"] for x in v])), "cases": v} for k, v in lags.items()}
    out["elapsed_s"] = time.time() - t0
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] delay in {out['elapsed_s']:.0f} s")
    return out
