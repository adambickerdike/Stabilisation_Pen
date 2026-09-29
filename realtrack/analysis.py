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


def learned(log=print) -> Dict:
    """The learned estimators on the tuning cases (cross-fitted where trained here): raw and with the soft authority."""
    from . import evaluate as EV
    from . import netmodel as NM
    from . import tune as TU
    p = BUILD_DIR / "learned.json"
    if p.exists():
        return json.loads(p.read_text())
    out = {}
    rows = EV.eval_batch([{"name": "fir", "family": "fir", "params": {"tag": "fir_main", "fold": "auto"}}],
                         C.tuning_specs(), "deltapen", log=log)
    out["fir_raw"] = EV.summarize(rows)["fir"]
    for tag, key in (("auth_net_main", "net"), ("auth_ai2tcn", "ai2_tcn")):
        v = json.loads((TU.TUNE_DIR / f"{tag}.json").read_text()) if (TU.TUNE_DIR / f"{tag}.json").exists() else None
        if v:
            out[f"{key}_raw"] = v["history"][0]["summary"]
            out[f"{key}_gated"] = {"params": v["best"]["params"], "summary": v["best"]["summary"],
                                   "passes": TU.passes(v["best"]["summary"])}
    cf = NM.MODEL_DIR / "net_main_crossfit.json"
    if cf.exists():
        c = json.loads(cf.read_text())
        out["net_training"] = {k: c.get(k) for k in ("n_cases", "epochs", "fold0_val_loss", "params", "cfg",
                                                    "macs_per_step", "elapsed_s")}
        try:
            data = NM.load_arrays(sorted(str(x) for x in (NM.TRAIN_DIR / "selection").glob("tune_n*_severe.npz")))
            out["int8"] = NM.int8_check("net_main", data)
        except Exception as e:                     # the int8 check is informative only
            out["int8"] = {"error": repr(e)}

    def fmt(s):
        return (f"severe tip {s.get('severe_ratio', float('nan')):.2f} x, clean {s.get('clean_um_mean', float('nan')):.0f} um"
                if s else "n/a")
    out["summary"] = "; ".join(f"{k}: {fmt(out.get(k) if 'gated' not in k else (out.get(k) or {}).get('summary'))}"
                               for k in ("fir_raw", "net_raw", "net_gated", "ai2_tcn_raw", "ai2_tcn_gated") if k in out)
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] learned: {out['summary']}")
    return out
