"""Stage learn: train the learned estimators on the domain-randomised samples and score them on the tuning set
(writers 100-103, seed 300) against the model-based estimators on the same metric.

Evidence status: SIMULATION.  Weights: ai2/build/models/ (git-ignored); scores: the stage cache.
Selection (open loop, tuning data, rule L1 fixed before the run): J = mean time-aligned residual over 1-2 mm, 6-10 Hz,
lags 0/25/50 ms, plus 2 x (the mean tremor-free output above 25 um) as a false-correction guard.  The closed-loop
check of the learned estimators against the Rev H tracker (rules R1-R4 of stage D2) is stage cl.
"""
from __future__ import annotations

import json
import math
import time
from typing import Dict, List

import numpy as np

from . import BUILD_DIR, ensure_paths
from . import common as C
from . import data as DA
from . import learned as LE
from . import stage_learn_data as SLD

ensure_paths()

MODEL_DIR = BUILD_DIR / "models"


def model_dir(quick: bool):
    return BUILD_DIR / ("models_quick" if quick else "models")
MODES = ("tcn", "ctx", "hybrid", "transformer")
ARCH = {"tcn": {"ch": 32, "k": 3}, "ctx": {"ch": 32, "k": 3}, "hybrid": {"ch": 32, "k": 3},
        "transformer": {"d": 32, "heads": 4, "layers": 2, "window": 192, "ff": 64}}
BATCH = {"transformer": (16, 512)}                  # (batch, sequence); default (24, 1500)
LR = {"transformer": 1e-3}                          # default 2e-3


def z_train(s: Dict, mode: str, mp: Dict, rng=None) -> np.ndarray:
    """Training inputs; for ctx the calibration context is the true tremor with calibration error (ASSUMPTION:
    frequency +-0.3 Hz SD, amplitude 20 % SD) and, for half the tremor-free samples, a tremor user's calibration
    (the user has tremor but writes without it at the moment)."""
    ctx = None
    if mode == "ctx":
        sp = s["spec"]
        f0, amp = sp.get("f0", 0.0), sp.get("amp", 0.0)
        if rng is not None:
            if amp <= 0 and rng.random() < 0.5:
                f0, amp = float(rng.uniform(4, 12)), float(math.exp(rng.uniform(math.log(0.3e-3), math.log(2e-3))))
            if amp > 0:
                f0 = f0 + float(rng.normal(0, 0.3)); amp = amp * float(math.exp(rng.normal(0, 0.2)))
        ctx = (f0, amp)
    return LE.make_inputs(mode, s["X"], s, ctx, mp["amp_gate"])


def residuals(D_est: np.ndarray, s: Dict, lags_idx=(0, 1, 2)) -> List[float]:
    m = s["mask"] > 0.5
    return [float(np.sqrt(np.mean(np.sum((s["Y"][m, i] - D_est[m, i]) ** 2, axis=1))) * 1e6) if m.any() else float("nan")
            for i in lags_idx]


def score(tune: List[Dict], est_fn) -> Dict:
    rows = []
    for s in tune:
        D = est_fn(s)
        r = residuals(D, s)
        m = s["mask"] > 0.5
        out_rms = float(np.sqrt(np.mean(np.sum(D[m, 0] ** 2, axis=1))) * 1e6) if m.any() else 0.0
        rows.append({"f0": s["spec"]["f0"], "amp_mm": s["spec"]["amp"] * 1e3, "writer": s["spec"]["writer"], "res": r,
                     "out_rms_um": out_rms})
    big = [np.mean(r["res"]) for r in rows if r["amp_mm"] >= 1.0]
    leak = [r["out_rms_um"] for r in rows if r["amp_mm"] == 0]
    small = [np.mean(r["res"]) for r in rows if 0 < r["amp_mm"] < 0.5]
    J = float(np.mean(big)) + 2.0 * max(0.0, float(np.mean(leak)) - 25.0)
    by_f = {f"{f:g}": float(np.mean([np.mean(r["res"]) for r in rows if r["amp_mm"] >= 1.0 and r["f0"] == f])) for f in (6.0, 8.0, 10.0)}
    return {"J": J, "res_1_2mm_um": float(np.mean(big)), "res_0p3mm_um": float(np.mean(small)),
            "leak_um": float(np.mean(leak)), "by_lag_1_2mm_um": [float(np.mean([r["res"][i] for r in rows if r["amp_mm"] >= 1.0])) for i in range(3)],
            "by_f0_1_2mm_um": by_f, "rows": rows}


def references(tune: List[Dict], mp: Dict) -> Dict:
    L = tune[0]["D"].shape[1]
    return {
        "rts_ungated": score(tune, lambda s: s["D"].astype(float)),
        "model_based_stack": score(tune, lambda s: LE.base_estimate(s, *mp["amp_gate"])[0]),
        # the Rev H tracker at each lag: its causal estimate dh(t - lag) (the fallback of delayed.estimates)
        "revh_tracker": score(tune, lambda s: LE.base_estimate(dict(s, gate=np.zeros_like(s["gate"])))[0]),
    }


def run(quick: bool, workers: int):
    DA.set_quick(quick)
    n = SLD.N_TRAIN_QUICK if quick else SLD.N_TRAIN
    mp = SLD.model_params(quick)
    train_raw = DA.load_set("train", n)
    tune = SLD.load_tuning()
    C.log(f"[learn] {len(train_raw)} training samples, {len(tune)} tuning scenarios; amp gate {mp['amp_gate']}")
    md = model_dir(quick)
    md.mkdir(parents=True, exist_ok=True)
    out = {"n_train": len(train_raw), "n_tune": len(tune), "models": {}, "model_params": mp,
           "rule": "L1: lowest J = mean residual 1-2 mm (lags 0/25/50 ms) + 2 x (tremor-free output - 25 um)+"}
    out["reference"] = references(tune, mp)
    for k, v in out["reference"].items():
        C.log(f"[learn] reference {k}: J {v['J']:.1f} residual 1-2 mm {v['res_1_2mm_um']:.1f} (lags {[round(x) for x in v['by_lag_1_2mm_um']]}) "
              f"0.3 mm {v['res_0p3mm_um']:.1f} leak {v['leak_um']:.1f}")
    minutes = 1.0 if quick else 13.0
    for mode in MODES:
        t0 = time.time()
        rng = np.random.default_rng(7)
        tr = [{"Z": z_train(s, mode, mp, rng), "Y": s["Y"], "mask": s["mask"], "spec": s["spec"]} for s in train_raw]
        tz = [dict(s, Z=z_train(s, mode, mp, None) if mode != "ctx" else
                   LE.make_inputs("ctx", s["X"], s, (s["spec"]["f0"], s["spec"]["amp"]), mp["amp_gate"])) for s in tune]

        def val_fn(model, tz=tz):
            return score(tz, lambda s: LE.predict(model, s["Z"]))["J"]
        b, sq = BATCH.get(mode, (24, 1500))
        model, info = LE.train(tr, val_fn, ARCH[mode], minutes=minutes, mode=mode, log=C.log, lambda_fc=4.0, batch=b, seq=sq,
                               lr=LR.get(mode, 2e-3))
        sc = score(tz, lambda s: LE.predict(model, s["Z"]))
        import torch
        torch.save(model.state_dict(), md / f"{mode}.pt")
        info["tuning_score"] = sc
        info["note_ctx"] = "tuning score with the true tremor as calibration context" if mode == "ctx" else ""
        (md / f"{mode}.json").write_text(json.dumps({k: v for k, v in info.items() if k != "tuning_score"}, default=C.jdefault))
        info["wall_min"] = (time.time() - t0) / 60.0
        out["models"][mode] = info
        C.log(f"[learn] {mode}: J {sc['J']:.1f} residual 1-2 mm {sc['res_1_2mm_um']:.1f} (lags {[round(x) for x in sc['by_lag_1_2mm_um']]}) "
              f"0.3 mm {sc['res_0p3mm_um']:.1f} leak {sc['leak_um']:.1f}; {info['n_params']} parameters, {info['macs_per_step']} MAC/step, "
              f"{info['steps']} steps")
    ranked = sorted(out["models"], key=lambda m: out["models"][m]["tuning_score"]["J"])
    out["ranked"] = ranked
    out["best_learned"] = ranked[0]
    C.save("learn", out, quick)
    C.log(f"[learn] ranked {ranked}")
    return out


def load_model(mode: str, quick: bool = False):
    import torch
    md = model_dir(quick)
    info = json.loads((md / f"{mode}.json").read_text())
    m = LE.build_model(info["cfg"])
    m.load_state_dict(torch.load(md / f"{mode}.pt"))
    m.eval()
    return m, info
