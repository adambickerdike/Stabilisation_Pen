"""Closed-loop evaluation of the trackers (SIMULATION).

P1 grid     fusion.harness.case (harness convention: scenarios.handwriting(seed, 5 s, TremorSpec(f0, amp)),
            PencilConfig() defaults, q_lim 0.30 mm; the estimate from sensor streams of the NEUTRAL tremor run is
            injected through M.with_estimate into Controller(mode="external")) and fusion.harness.distortion (the
            same estimator on the tremor-free writing).  Rows carry the ratio, band ratio, path_um (nearest-point
            distance of the ink to the intended path) and intent_err_um (time-aligned, offset removed).
aiguide     the aiguide writers (fusion.aieval.setup: glyph writer, "return library books by friday", 0.3 mm tremor,
            P1 with q_lim 0.30 mm) with the external-estimator block of fusion.aieval.scenario copied exactly
            (stream seeds 500000 + 1000 w + f0 and 510000 + ..., aieval._metrics): path RMS to the intended letters
            on all ink and on the writing only, recognition, ink ratio, distortion on the tremor-free writing.
The learned estimators of this package are made available to fusion's dispatch at run time (a wrapper around
fusion.estimators.run_estimator for names starting with "opt_"; no file of fusion/ is edited).
Test data (seeds 200-203, aiguide writers 0-5) are only used by run_study's final stage.
"""
from __future__ import annotations

import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from fusion import estimators as ES
from fusion import harness as H
from fusion import sensors as S


def register():
    """Route estimator names 'opt_*' to opt.tracker.learned (idempotent, per process)."""
    if getattr(ES.run_estimator, "_opt_tracker", False):
        return
    orig = ES.run_estimator

    def run_estimator(name, st, params=None, extra=None):
        if isinstance(name, str) and name.startswith("opt_"):
            from . import learned as LN
            return LN.estimate(name, st, params, extra)
        return orig(name, st, params, extra)
    run_estimator._opt_tracker = True
    ES.run_estimator = run_estimator


def _worker_init():
    import torch
    torch.set_num_threads(1)
    register()


# ------------------------------------------------------------------ P1 grid
def _case(args):
    seed, f0, amp, specs, per_cond = args
    register()
    sp = []
    for s in specs:
        if per_cond and s.label in per_cond:
            s = H.Spec(s.label, s.name, per_cond[s.label][(seed, f0, round(amp * 1e6))], s.sensors, s.extra)
        sp.append(s)
    return H.case(seed, f0, amp, sp, with_internal_kfosc=True, with_band_oracle=True)


def _dist(args):
    seed, specs = args
    register()
    return H.distortion(seed, specs)


def _dist_personal(args):
    seed, label, params, f0 = args
    register()
    rows = H.distortion(seed, [H.Spec(label, "akf", params, {"page": "1k", "comp": "gyro"})])
    r = [x for x in rows if x["label"] == label][0]
    r["calib_f0"] = f0
    return r


def grid(specs: Sequence[H.Spec], seeds: Sequence[int], f0s=H.F0S, amps=H.AMPS, workers: int = 2,
         per_cond: Optional[Dict] = None, dist: bool = True, log: Callable = print) -> Dict:
    """Rows of fusion.harness.case for every condition, distortion rows per seed.  per_cond: {label: {(seed, f0,
    amp_um): params}} for per-condition parameter sets (personalisation)."""
    t0 = time.time()
    conds = [(s, f0, a, list(specs), per_cond) for s in seeds for f0 in f0s for a in amps]
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as ex:
        rows = [r for rr in ex.map(_case, conds) for r in rr]
        drows = []
        if dist:
            sp = [s for s in specs if not (per_cond and s.label in per_cond)]
            drows = [r for rr in ex.map(_dist, [(s, sp) for s in seeds]) for r in rr]
    log(f"[grid] {len(conds)} conditions x {len(specs)} specs in {time.time() - t0:.0f} s")
    return {"rows": rows, "distortion_rows": drows, "summary": summarise(rows, drows), "elapsed_s": time.time() - t0}


def personal_distortion(items: Sequence[Tuple[int, str, Dict, float]], workers: int = 2) -> List[Dict]:
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as ex:
        return list(ex.map(_dist_personal, items))


def summarise(rows: List[Dict], drows: List[Dict]) -> Dict:
    labels = []
    for r in rows:
        if r["label"] not in labels:
            labels.append(r["label"])
    out = {}
    keys = ("ratio", "band_ratio", "path_um", "intent_err_um", "residual_ratio", "residual_ratio_band",
            "residual_ratio_low", "q_sat_frac", "P_rail_classB_mW", "housing_vs_neutral_rms_um", "authority_mean",
            "f_est_median_hz")
    for lab in labels:
        R = [r for r in rows if r["label"] == lab]
        o = {"n": len(R)}
        for k in keys:
            v = [r[k] for r in R if k in r and r[k] is not None and np.isfinite(r[k])]
            if v:
                o[k + "_mean"] = float(np.mean(v))
        by = {}
        for r in R:
            if "ratio" not in r:
                continue
            key = f"{r['f0']:g}Hz_{r['amp_mm']:g}mm"
            by.setdefault(key, {"ratio": [], "band_ratio": [], "path_um": [], "intent_err_um": []})
            for k in by[key]:
                if k in r:
                    by[key][k].append(r[k])
        o["by_condition"] = {c: {k: {"mean": float(np.mean(v)), "sd": float(np.std(v))} for k, v in d.items() if v}
                             for c, d in by.items()}
        out[lab] = o
    for lab in {d["label"] for d in drows}:
        D = [d["distortion_um"] for d in drows if d["label"] == lab]
        F = [d.get("false_correction_rms_um") for d in drows if d["label"] == lab and d.get("false_correction_rms_um") is not None]
        out.setdefault(lab, {})["distortion_um_mean"] = float(np.mean(D))
        out[lab]["distortion_um_sd"] = float(np.std(D))
        if F:
            out[lab]["false_correction_um_mean"] = float(np.mean(F))
    return out


# ------------------------------------------------------------------ aiguide writers
def _ai_scenario(args):
    """Neutral, tremor-free and every external spec on one (writer, f0) aiguide scenario (fusion.aieval pattern)."""
    w, f0, specs, with_oracle = args
    register()
    from fusion import aieval as AE
    from aiguide import guidance as G
    from sim.pencil import evaluate as E
    from sim.pencil import model as M
    t0 = time.time()
    su = AE.setup(w, f0)
    scn, S_ = su["scn"], su["S"]
    neutral = su["neutral"]
    na = G.arrays(neutral)
    rows = {"neutral": AE._metrics(su, neutral), "neutral_no_tremor": AE._metrics(su, su["clean"])}
    if with_oracle:
        rows["oracle_disturbance"] = AE._metrics(su, AE.prun(M.with_disturbance(scn, M.housing_disturbance(scn, su["clean"])),
                                                             "oracle", S_), na)
    rec1 = S.record_from_result(neutral, scn)
    rec0 = S.record_from_result(su["clean"], su["scn0"])
    for label, (name, params, skw) in specs.items():
        st = S.make_streams(rec1, S.config(**skw), 500_000 + 1000 * w + int(f0))
        dh, info = ES.run_estimator(name, st, params, None)
        res = M.run(M.with_estimate(scn, S.expand_to_steps(dh, len(scn.t), rec1.sdec)),
                    M.Controller(mode="external", **AE.CFG["ctrl"]), M.PencilConfig(), seed=S_, rec_hz=AE.REC_HZ)
        r = AE._metrics(su, res, na)
        st0 = S.make_streams(rec0, S.config(**skw), 510_000 + 1000 * w + int(f0))
        dh0, _ = ES.run_estimator(name, st0, params, None)
        res0 = M.run(M.with_estimate(su["scn0"], S.expand_to_steps(dh0, len(su["scn0"].t), rec0.sdec)),
                     M.Controller(mode="external", **AE.CFG["ctrl"]), M.PencilConfig(), seed=S_, rec_hz=AE.REC_HZ)
        con0 = np.interp(st0.tick_t, rec0.t, rec0.contact) > 0.5
        r["distortion_um"] = E.compare(res0, su["clean"])["e_rms_um"]
        r["false_correction_um"] = float(np.sqrt(np.mean(np.sum(dh0[con0] ** 2, axis=1))) * 1e6) if con0.any() else float("nan")
        rows[label] = r
    for lab in rows:
        rows[lab].pop("_letters", None)
        rows[lab].pop("_letters_wo", None)
    return {"writer": w, "f0": f0, "rows": rows, "writing_band_um": AE.writing_band_um(su["wr"].intended),
            "elapsed_s": time.time() - t0}


def aiguide(specs: Dict[str, Tuple[str, Dict, Dict]], writers: Sequence[int], f0s: Sequence[float], workers: int = 2,
            with_oracle: bool = True, log: Callable = print) -> Dict:
    t0 = time.time()
    jobs = [(w, f0, specs, with_oracle) for w in writers for f0 in f0s]
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as ex:
        outs = list(ex.map(_ai_scenario, jobs))
    labels = list(outs[0]["rows"].keys())
    summ = {}
    for lab in labels:
        for k in outs[0]["rows"][lab]:
            vals = [o["rows"][lab][k] for o in outs if isinstance(o["rows"][lab].get(k), (int, float))
                    and o["rows"][lab].get(k) is not None and np.isfinite(o["rows"][lab].get(k))]
            if vals:
                summ.setdefault(lab, {})[k] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals)), "n": len(vals)}
    log(f"[aiguide] {len(jobs)} scenarios x {len(specs)} specs in {time.time() - t0:.0f} s")
    return {"summary": summ, "scenarios": outs, "writers": list(writers), "f0": list(f0s), "elapsed_s": time.time() - t0}
