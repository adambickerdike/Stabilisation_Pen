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
    """Per case cached (realtrack/build/sep_cache/<case>.npz, pen-down ticks, every 10th): restart-proof."""
    p = BUILD_DIR / "separability.json"
    if p.exists():
        return json.loads(p.read_text())
    from . import search as SR
    t0 = time.time()
    L = SR.listening_design()
    cdir = BUILD_DIR / "sep_cache"
    cdir.mkdir(parents=True, exist_ok=True)
    feats = ("line ratio, page track 4 s (ai2's detector)", "line ratio, accelerometer track 2 s",
             "amplitude of the listening estimate, mm (1 s)")
    acc: Dict = {}
    for s in C.tuning_specs():
        if s["level"] not in ("clean", "moderate", "severe"):
            continue
        f = cdir / f"{s['id']}.npz"
        if not f.exists():
            c = C.load_case(s)
            st = c.streams("deltapen")
            down = c.arrays["down_ticks"] > 0.5
            r1 = E.det_ratio(st, {"win": 4.0, "seg": 2.0, "band_lo": 4.5, "band_hi": 13.5}, contact_only=False)["ratio"]
            r2 = E.det_ratio_imu(st, {"win": 2.0, "seg": 1.0, "band_lo": 3.5, "band_hi": 12.0})["ratio"]
            d, _ = E.raw_estimate("akf", st, L["params"])
            _, _, A = E.authority(d, float(c.meta["Ts"]), {"tau_amp": 1.0})
            np.savez(f, r1=r1[down][::10], r2=r2[down][::10], A=A[down][::10] * 1e3)
            del c, st
        with np.load(f) as z:
            for feat, key in zip(feats, ("r1", "r2", "A")):
                acc.setdefault((feat, s["level"]), []).append(z[key])
    out = {"q": Q}
    for (feat, lev), v in acc.items():
        x = np.concatenate(v)
        out.setdefault(feat, {})[lev] = [float(np.quantile(x, q)) for q in Q]
        out[feat].setdefault("_share_above", {})
        if "ratio" in feat:
            out[feat]["_share_above"][lev] = {str(t): float(np.mean(x > t)) for t in (3, 5, 8)}
        else:
            out[feat]["_share_above"][lev] = {str(t): float(np.mean(x > t)) for t in (0.5, 1.0, 1.5)}
    out["label"] = ("SIMULATION (HW1) with real inputs, tuning split, DeltaPen-class page sensor; pen-down ticks (every "
                    "10th)")
    out["elapsed_s_last_run"] = time.time() - t0
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] separability ({out['elapsed_s_last_run']:.0f} s)")
    return out


def delay(chosen: Dict, log=print) -> Dict:
    """Restart-proof: every horizon point and every lag estimate is cached (realtrack/build/delay_cache)."""
    from . import delay as DY
    from . import evaluate as EV
    p = BUILD_DIR / "delay.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    cdir = BUILD_DIR / "delay_cache"
    cdir.mkdir(parents=True, exist_ok=True)
    gd = E.servo_delay()
    offsets = (-3, -1.5, 0, 1.5, 3, 5, 7.5, 10)
    specs = [s for s in C.tuning_specs() if s["level"] in ("severe", "moderate", "mild")]
    horizon = {}
    for label, dz in (("Rev H tracker (as built)", {"family": "revh"}), ("chosen design", chosen)):
        key = "revh" if dz.get("family") == "revh" else "chosen"
        by = {}
        for o in offsets:
            f = cdir / f"{key}_{o:+g}.json"
            if not f.exists():
                d = dict(dz)
                d["name"] = "x"
                d["horizon"] = gd + o * 1e-3
                sm = EV.summarize(EV.eval_batch([d], specs, "deltapen", log=lambda *a: None))["x"]
                f.write_text(json.dumps({k: sm.get(k) for k in ("severe_ratio", "severe_bb", "moderate_ratio",
                                                                 "moderate_rheld", "mild_ratio", "mild_rheld")}))
            by[str(o)] = json.loads(f.read_text())
        horizon[label] = {"offsets_ms": list(offsets), "nominal_ms": gd * 1e3, "by_offset": by}
        log(f"[analysis] horizon sweep {label} ({time.time() - t0:.0f} s)")
    lags = {"revh": [], "chosen": []}
    for s in C.tuning_specs():
        if s["level"] != "severe":
            continue
        f = cdir / f"xcorr_{s['id']}.json"
        if not f.exists():
            c = C.load_case(s)
            st = c.streams("deltapen")
            r = {}
            for nm, dz in (("revh", {"family": "revh"}), ("chosen", chosen)):
                d, _ = E.estimate(dz, st, case=c)
                r[nm] = DY.xcorr_lag(d, c)
            f.write_text(json.dumps(r))
            del c, st
        r = json.loads(f.read_text())
        for nm in lags:
            lags[nm].append(r[nm])
    out = {"servo_lag": DY.servo_lag(), "budget": DY.budget(), "decompose": DY.decompose(), "horizon": horizon,
           "xcorr": {k: {"lag_ms_median": float(np.median([x["lag_ms"] for x in v])),
                         "gain_median": float(np.median([x["gain"] for x in v])), "cases": v} for k, v in lags.items()},
           "elapsed_s_last_run": time.time() - t0}
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] delay ({out['elapsed_s_last_run']:.0f} s)")
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


def int8_ai2tcn(log=print) -> Dict:
    """Per-channel symmetric int8 quantisation of ai2's TCN weights (activations float): the change of its lag-0 output
    on the severe tuning cases (RMS, um) against the output's RMS (CALC)."""
    p = BUILD_DIR / "int8_ai2tcn.json"
    if p.exists():
        return json.loads(p.read_text())
    import copy
    import torch
    from realdata import hw1 as H
    from ai2 import data as DA
    from ai2 import learned as L2
    from fusion import learned as FL
    torch.set_num_threads(1)
    m = H.ai2_models()["tcn"]
    q = copy.deepcopy(m)
    with torch.no_grad():
        for name, w in q.named_parameters():
            if w.dim() >= 2:
                s = w.abs().amax(dim=tuple(range(1, w.dim())), keepdim=True).clamp(min=1e-12) / 127.0
                w.copy_(torch.round(w / s).clamp(-127, 127) * s)
    num = den = 0.0
    n = 0
    for s in C.tuning_specs():
        if s["level"] != "severe":
            continue
        c = C.load_case(s)
        X, tk = FL.features(c.streams("deltapen"), DA.NET_HZ)
        Z = L2.make_inputs("tcn", X)
        a = L2.predict(m, Z)[:, 0, :]
        b = L2.predict(q, Z)[:, 0, :]
        num += float(np.sum((a - b) ** 2)); den += float(np.sum(a ** 2)); n += a.size
        del c
    out = {"rms_diff_um": float(np.sqrt(num / n) * 1e6), "rms_out_um": float(np.sqrt(den / n) * 1e6),
           "label": "CALC: ai2's TCN, weights per-channel int8, activations float; severe tuning cases"}
    p.write_text(json.dumps(out))
    log(f"[analysis] int8 ai2 TCN: {out['rms_diff_um']:.1f} um RMS change on {out['rms_out_um']:.0f} um output")
    return out


def raw_clean(log=print) -> Dict:
    """The capture-only (stage-1) setting of every classical family, no gate, on the clean and the mild tuning cases:
    how much it moves clean writing and what it does to small tremor (explains why a gate is needed; not a choice)."""
    from . import evaluate as EV
    from . import search as SR
    p = BUILD_DIR / "raw_clean.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    designs = [SR.best_design(fam) for fam in ("akf", "wflc", "bmflc", "bmflc_kf", "epll")]
    specs = [s for s in C.tuning_specs() if s["level"] in ("clean", "mild")]
    sm = EV.summarize(EV.eval_batch(designs, specs, "deltapen", log=log))
    out = {d["name"].replace("_s1", ""): {k: sm[d["name"]].get(k) for k in ("clean_um_mean", "clean_um_max", "mild_ratio",
                                                                             "mild_rheld")} for d in designs}
    out["label"] = "SIM (surrogate of the HW1 command path), tuning split: 10 clean notes and 20 mild cases"
    out["elapsed_s"] = time.time() - t0
    p.write_text(json.dumps(out, default=float))
    log(f"[analysis] raw clean: {out}")
    return out
