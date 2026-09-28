#!/usr/bin/env python3
"""Sensing + AI study on the pencil model P1: python3 -m fusion.run_study [--stages ...] [--workers 2].

Stages (each writes its own file in results/fusion/ with provenance metadata):
  sensors   datasheet catalogue and tremor-band SNR (CALC); pen-rotation / lever-arm error of the nib
            acceleration estimate per compensation (SIM, open loop); closed-loop AKF per compensation and
            rotation; the internal IMU anti-aliasing check (imu_aa) with a 120 Hz page sensor
  tune      tuned parameters (fusion/tune.py on seeds 5000-5007; `--retune` re-runs the searches) and their
            closed-loop verification on the tuning seeds
  learned   trains the GRU if it is missing (`--retrain` forces it)
  grid      the P1 test grid 4-12 Hz x 0.1/0.3/0.5 mm x seeds 200-203 for every estimator, distortion on the
            tremor-free writing, one re-estimation iteration on a subset
  context   template-error spectrum and the closed loop on the aiguide writers (AI + physical)
  budget    MCU cost per estimator (CALC)
  figures   figures from the JSON files
Evidence status: SIMULATION and CALCULATION on synthetic signals; nothing measured.
Runtime here (2 processes): about 25 min for the GRU training, 40-50 min for the rest (see results/fusion/*.json), plus about 45 min for `--retune`.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import numpy as np

import fusion
from fusion import RESULTS, TEST_SEEDS, TUNE_SEEDS, EVIDENCE_SIM, EVIDENCE_CALC
from fusion import data as FD
from fusion import harness as H
from fusion import parts as PT
from fusion import sensors as S

TUNE_DIR = os.path.join(fusion.BUILD, "tune")
SK_1K = {"page": "1k", "comp": "gyro"}
SK_120 = {"page": "120", "comp": "gyro"}


def _meta(status, seeds, extra=None):
    from stabpen import provenance
    from sim.pencil import design as D, model as M
    ex = {"model_version": M.MODEL_VERSION, "script": "fusion/run_study.py"}
    try:
        import torch
        import numba
        ex["torch"] = torch.__version__
        ex["numba"] = numba.__version__
    except Exception:  # pragma: no cover
        pass
    ex.update(extra or {})
    return provenance.metadata(status, seeds=seeds, p=D.Params().pencil, extra=ex)


def _write(name, obj):
    from stabpen import provenance
    os.makedirs(RESULTS, exist_ok=True)
    provenance.write_json(os.path.join(RESULTS, name), _r4(obj))


def _r4(x):
    if isinstance(x, float):
        if not math.isfinite(x):
            return None                      # strict JSON: NaN / inf become null
        return float(f"{x:.5g}") if x != 0.0 else x
    if isinstance(x, dict):
        return {str(k): _r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r4(v) for v in x]
    if isinstance(x, (np.floating,)):
        return _r4(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def _load(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p)) if os.path.exists(p) else None


# ================================================================== tuned parameters
SEARCHES = (("akf", "1k", 220, 120), ("akf", "120", 220, 120), ("bmflc", "1k", 160, 80), ("wflc", "1k", 160, 80), ("kfosc", "1k", 120, 60),
            ("kfosclp", "1k", 60, 40))
# robust variants: the same estimators tuned on the grid tuning seeds AND the aiguide tuning writers 100-105 (tune.search_robust)
ROBUST = (("akfx", "akf_robust_1k", 160, 80), ("akfc", "akf_robust_1k", 140, 80), ("wflcx", "wflc_robust_1k", 120, 60))


def run_searches(workers: int = 2):
    """Re-run every parameter search on the tuning seeds (about 40 min on 2 processes)."""
    from fusion import tune as TU
    os.makedirs(TUNE_DIR, exist_ok=True)
    TU.prepare(workers=workers)
    for name, page, nr, nl in SEARCHES:
        start = [{}] if name.startswith("kfosc") else []
        r = TU.search(name, {"page": page, "comp": "gyro"}, n_random=nr, n_local=nl, workers=workers, fc_max=14e-6, start=start, seed=21)
        json.dump(r, open(os.path.join(TUNE_DIR, f"v2_{name}_{page}.json"), "w"), indent=1, default=float)
    for name, _, nr, nl in ROBUST:
        r = TU.search_robust(name, {"page": "1k", "comp": "gyro"}, n_random=nr, n_local=nl, workers=workers, fc_max=14e-6, seed=31)
        json.dump(r, open(os.path.join(TUNE_DIR, f"v2_{name}_robust_1k.json"), "w"), indent=1, default=float)


def tuned() -> Dict:
    """Best parameters of each search (fusion/build/tune/v2_*.json, else results/fusion/tuning.json)."""
    out = {}
    committed = (_load("tuning.json") or {}).get("searches", {})
    for name, page, _, _ in SEARCHES:
        p = os.path.join(TUNE_DIR, f"v2_{name}_{page}.json")
        if not os.path.exists(p) and f"{name}_{page}" in committed:
            out[f"{name}_{page}"] = committed[f"{name}_{page}"]
            continue
        if os.path.exists(p):
            r = json.load(open(p))
            out[f"{name}_{page}"] = {"params": r["best"]["params"], "proxy": {k: r["best"].get(k) for k in ("J", "rr_mean", "hf_rel_mean", "fc_um")},
                                     "n_evaluated": r["n_evaluated"], "objective": r["objective"], "fc_max_um": r.get("fc_max_um")}
    for name, key, _, _ in ROBUST:
        # several searches may feed one key (the AKF without and with the amplitude cap): the lowest objective wins
        p = os.path.join(TUNE_DIR, f"v2_{name}_robust_1k.json")
        if not os.path.exists(p) and key in committed and key not in out:
            out[key] = committed[key]
        elif os.path.exists(p):
            r = json.load(open(p))
            if key in out and out[key].get("proxy", {}).get("J", 1e9) <= r["best"]["J"]:
                continue
            out[key] = {"params": r["best"]["params"], "search": name,
                        "proxy": {k: r["best"].get(k) for k in ("J", "rr_mean", "rr_ai_mean", "fc_ai_rel_mean", "fc_ai_um", "hf_rel_mean", "fc_um")},
                        "n_evaluated": r["n_evaluated"], "objective": r["objective"], "fc_max_um": r.get("fc_max_um"),
                        "aiguide_tuning": r.get("aiguide_tuning")}
    p = os.path.join(TUNE_DIR, "context.json")
    if os.path.exists(p):
        out["context"] = json.load(open(p))
    elif "context" in committed:
        out["context"] = committed["context"]
    elif (_load("context.json") or {}).get("context_tuning"):
        ct = _load("context.json")
        out["context"] = dict(ct["context_tuning"], all=ct.get("context_tuning_all"))
    return out


def specs(T: Dict, with_learned=True, with_personal=True) -> List[H.Spec]:
    from fusion import estimators as ES
    # the frozen filter through the external path: with the core's own IMU settings (agreement check: ideal translation-only
    # IMU at 4 kHz, 70 ug/sqrt(Hz), no read latency beyond the 1.04 ms filter) and with this study's sensor models
    sp = [H.Spec("kfosc_port_matched", "kfosc", {}, {"page": "1k", "comp": "ideal", "odr": 4000.0, "extra_latency": 0.0, "nd_ug": 70.0}),
          H.Spec("kfosc_port", "kfosc", {}, SK_1K), H.Spec("kfosc_port_120", "kfosc", {}, SK_120)]
    if "kfosc_1k" in T:
        sp.append(H.Spec("kfosc_p1", "kfosc", T["kfosc_1k"]["params"], SK_1K))
    if "kfosclp_1k" in T:
        sp.append(H.Spec("kfosc_p1_lp", "kfosc", T["kfosclp_1k"]["params"], SK_1K))
    if "akf_1k" in T:
        sp.append(H.Spec("akf", "akf", T["akf_1k"]["params"], SK_1K))
    if "akf_120" in T:
        sp.append(H.Spec("akf_120", "akf", T["akf_120"]["params"], SK_120))
    if "akf_robust_1k" in T:
        sp.append(H.Spec("akf_robust", "akf", T["akf_robust_1k"]["params"], SK_1K))
    for n in ("bmflc", "wflc"):
        if f"{n}_1k" in T:
            sp.append(H.Spec(n, n, T[f"{n}_1k"]["params"], SK_1K))
    if "wflc_robust_1k" in T:
        sp.append(H.Spec("wflc_robust", "wflc", T["wflc_robust_1k"]["params"], SK_1K))
    if with_learned:
        from fusion import learned as L
        for name, sk, lab in (("gru48_1k", SK_1K, "gru"), ("gru48_mix", SK_120, "gru_120")):
            if os.path.exists(os.path.join(L.MODEL_DIR, name + ".pt")):
                sp.append(H.Spec(lab, "learned", {"model": name, "lp_hz": 60.0}, sk))
    if with_personal and "akf_1k" in T:
        sp.append(H.Spec("akf_personal", "akf", population(T), SK_1K))
    return sp


def population(T: Dict) -> Dict:
    """The population parameter set the personal calibration starts from (the robust AKF when it exists)."""
    return dict(T["akf_robust_1k"]["params"] if "akf_robust_1k" in T else T["akf_1k"]["params"])


def stage_tune(workers: int):
    """Record the tuned parameters and check them in closed loop on tuning seeds 5000-5003 (never the test seeds)."""
    from fusion import tune as TU
    T = tuned()
    t0 = time.time()
    sp = [s for s in specs(T, with_learned=False, with_personal=False)
          if s.label in ("kfosc_port", "kfosc_p1", "kfosc_p1_lp", "akf", "akf_120", "akf_robust", "bmflc", "wflc", "wflc_robust")]
    cl = TU.closed_loop_check(sp, seeds=TUNE_SEEDS[:4], workers=workers)
    out = {"meta": _meta(EVIDENCE_SIM, {"tuning": list(TUNE_SEEDS), "closed_loop_check": list(TUNE_SEEDS[:4])},
                         {"elapsed_s": round(time.time() - t0, 1)}),
           "method": TU.__doc__, "searches": T, "closed_loop_on_tuning_seeds": cl, "robust_searches": {}}
    for name, key, _, _ in ROBUST:
        p = os.path.join(TUNE_DIR, f"v2_{name}_robust_1k.json")
        if os.path.exists(p):
            b = json.load(open(p))["best"]
            out["robust_searches"][name] = {"feeds": key, "chosen": T.get(key, {}).get("search") == name,
                                            **{k: b.get(k) for k in ("J", "rr_mean", "rr_ai_mean", "fc_ai_um", "fc_um", "rr_ai")}}
    _write("tuning.json", out)
    return out


# ================================================================== grid
_T: Dict = {}


def _grid_case(args):
    seed, f0, amp, T = args
    sp = specs(T)
    pers = {}
    for s in sp:
        if s.label == "akf_personal":
            from fusion import personal as PS
            r = PS.personalise(seed, f0, amp, population(T), SK_1K)
            s.params = r["params"]
            pers = {k: r[k] for k in ("calibration", "calib_band_rr", "calib_band_rr_population")}
    it = ("akf", "akf_robust", "gru") if (seed == TEST_SEEDS[0] and abs(amp - 0.3e-3) < 1e-9) else ()
    rows = H.case(seed, f0, amp, sp, iterate=it)
    for r in rows:
        if r["label"] == "akf_personal":
            r["personal"] = pers
    return rows


def _grid_dist(args):
    seed, T = args
    sp = [s for s in specs(T) if s.label != "akf_personal"]
    return H.distortion(seed, sp)


def _personal_dist(args):
    """Distortion of the personal set: calibrated on each tremor condition's calibration task, applied to clean writing."""
    seed, f0, amp, T = args
    from fusion import personal as PS
    r = PS.personalise(seed, f0, amp, population(T), SK_1K)
    sp = H.Spec("akf_personal", "akf", r["params"], SK_1K)
    d = [x for x in H.distortion(seed, [sp]) if x["label"] == "akf_personal"][0]
    d.update({"f0": f0, "amp_mm": amp * 1e3})
    return d


def _writing_band(seed: int) -> float:
    """3-15 Hz RMS of the intended pen-down motion of a grid scenario (compare aieval.writing_band_um)."""
    from scipy.signal import butter, sosfiltfilt
    sc = FD.clean_scenario(seed)
    fs = 1.0 / float(sc.t[1] - sc.t[0])
    x = sosfiltfilt(butter(4, (3.0, 15.0), btype="band", fs=fs, output="sos"), np.asarray(sc.intended), axis=0)
    fp = np.asarray(sc.fpush, float).reshape(len(sc.t))
    pd = fp > 0.5 * fp.max()                     # pen down (scenarios._assemble: fpush = N0 x down fraction)
    return float(np.sqrt(np.mean(np.sum(x[pd] ** 2, axis=1))) * 1e6)


def stage_grid(workers: int, seeds=TEST_SEEDS, f0s=H.F0S, amps=H.AMPS):
    T = tuned()
    t0 = time.time()
    conds = [(s, f0, a, T) for s in seeds for f0 in f0s for a in amps]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = [r for rr in ex.map(_grid_case, conds) for r in rr]
        dist = [r for rr in ex.map(_grid_dist, [(s, T) for s in seeds]) for r in rr]
        pdist = list(ex.map(_personal_dist, [(s, f0, 0.3e-3, T) for s in seeds for f0 in (6.0, 10.0)]))
    labels = []
    for r in rows:
        if r["label"] not in labels:
            labels.append(r["label"])
    summ = {}
    for lab in labels:
        for key in ("ratio", "band_ratio", "q_sat_frac", "P_rail_classB_mW", "P_rail_recovery_mW", "e_rms_um", "path_um",
                    "intent_err_um", "residual_ratio", "residual_ratio_band", "residual_ratio_low", "housing_vs_neutral_rms_um"):
            a = H.aggregate([r for r in rows if r["label"] == lab], ("f0", "amp_mm"), (key,))
            if a:
                summ.setdefault(lab, {})[key] = {f"{f:g}Hz_{amp:g}mm": v[key] for (f, amp), v in sorted(a.items()) if key in v}
        R = [r for r in rows if r["label"] == lab and "ratio" in r]
        if R:
            summ[lab]["overall"] = {"ratio_mean": float(np.mean([r["ratio"] for r in R])),
                                    "band_ratio_mean": float(np.mean([r["band_ratio"] for r in R])),
                                    "intent_err_um_mean": float(np.mean([r.get("intent_err_um", np.nan) for r in R])),
                                    "path_um_mean": float(np.mean([r.get("path_um", np.nan) for r in R])),
                                    "q_sat_mean": float(np.mean([r["q_sat_frac"] for r in R])),
                                    "residual_ratio_band_mean": float(np.mean([r.get("residual_ratio_band", np.nan) for r in R])),
                                    "residual_ratio_low_mean": float(np.mean([r.get("residual_ratio_low", np.nan) for r in R])),
                                    "P_rail_classB_mW_mean": float(np.mean([r["P_rail_classB_mW"] for r in R])),
                                    "n": len(R)}
    dsum = {}
    for lab in {d["label"] for d in dist}:
        D = [d["distortion_um"] for d in dist if d["label"] == lab]
        dsum[lab] = {"mean": float(np.mean(D)), "sd": float(np.std(D)), "n": len(D)}
    if pdist:
        D = [d["distortion_um"] for d in pdist]
        dsum["akf_personal"] = {"mean": float(np.mean(D)), "sd": float(np.std(D)), "n": len(D),
                                "note": "personal set calibrated on each writer's 6 and 10 Hz / 0.3 mm calibration task, then run on that seed's tremor-free writing"}
    it_rows = [r for r in rows if "ratio_iter1" in r]
    iteration = {lab: {"ratio_iter0": [r["ratio"] for r in it_rows if r["label"] == lab],
                       "ratio_iter1": [r["ratio_iter1"] for r in it_rows if r["label"] == lab],
                       "dhat_change_rms_um": [r["dhat_change_rms_um"] for r in it_rows if r["label"] == lab],
                       "f0": [r["f0"] for r in it_rows if r["label"] == lab]} for lab in {r["label"] for r in it_rows}}
    out = {"meta": _meta(EVIDENCE_SIM, {"test": list(seeds), "tuning": list(TUNE_SEEDS),
                                        "sensor_noise": "10_000_000 + 1000 seed + 10 f0 + amp[0.1 mm] (+100000 tremor-free)",
                                        "calibration": "test seed + 40000"},
                         {"elapsed_s": round(time.time() - t0, 1), "workers": workers, "duration_s": FD.DURATION, "record_Hz": FD.REC_HZ}),
           "protocol": {"reference": "same pen, NEUTRAL, same handwriting without tremor (harness convention)",
                        "ratio": "e_rms(controller)/e_rms(NEUTRAL with tremor), both against the reference",
                        "band_ratio": "same with the 3-15 Hz band of the ink error (sim/pencil/evaluate.py)",
                        "oracle": "M.housing_disturbance / M.with_disturbance (true disturbance, core mode 4)",
                        "oracle_band": "true disturbance band-passed 3-15 Hz zero-phase, injected as an external estimate (NOT causal): the best any tremor-band estimator can do",
                        "external": "causal estimate from sensor streams generated on the NEUTRAL run's recorded housing motion, injected with M.with_estimate, Controller(mode='external')",
                        "housing_vs_neutral_rms_um": "RMS difference between the controlled run's housing path and the neutral run's (the approximation of the external pattern)",
                        "distortion": "the estimator on the tremor-free writing against the reference",
                        "grid": "scenarios.handwriting(seed, duration=5.0, tremor=TremorSpec(f0, amp_pk), N0=1.0), PencilConfig() defaults, q_lim 0.30 mm",
                        "sensors": "page sensor 1 kHz / 2 ms / 3 um (P1 default) or 120 Hz / 10 ms / 3 um (proposed requirement); LSM6DSV16X-class IMU 60 ug/sqrt(Hz) at 3.84 kHz, 0.35 ms after the recorded 1.04 ms filter, gyroscope-compensated; pen rotation rho_t = rho_w = 0.5 (ASSUMPTION)",
                        "residual_ratio": "open-loop RMS(d - d_hat)/RMS(d) at the ticks in contact (signal level)",
                        "intent_err_um": "time-aligned RMS distance of the ink from the intended hand path (scenario.intended), static offset removed; not a harness metric",
                        "path_um": "nearest-point (timing-free) RMS distance of the ink from the intended hand path"},
           "writing_band_um": {str(sd): _writing_band(sd) for sd in seeds},
           "summary": summ, "distortion_um": dsum, "iteration": iteration, "rows": rows, "distortion_rows": dist + pdist,
           "tuned_params": {k: v.get("params") for k, v in T.items() if isinstance(v, dict) and "params" in v}}
    _write("grid.json", out)
    return out


# ================================================================== sensors
def _lever_closed(args):
    seed, f0, T, comp, rho, page = args
    key = "akf_1k" if page == "1k" else "akf_120"
    sp = H.Spec(f"akf_{comp}_{rho:g}_{page}", "akf", T[key]["params"], {"page": page, "comp": comp, "rho_t": rho, "rho_w": rho})
    rows = H.case(seed, f0, 0.3e-3, [sp], with_internal_kfosc=False, with_band_oracle=False)
    return [dict(r, comp=comp, rho=rho, page=page) for r in rows if r["label"] == sp.label]


def _friction_control(args):
    """Low-frequency vs tremor-band parts of the oracle's disturbance with nominal and near-frictionless skid and nib."""
    seed, f0, label = args
    from scipy.signal import butter, sosfiltfilt
    from sim.pencil import model as M, evaluate as E
    cfg = M.PencilConfig() if label == "nominal" else M.PencilConfig(mu_skid=0.0, mu_nib=0.02)
    sc0 = FD.test_scenario(seed)
    sc1 = FD.test_scenario(seed, f0, 0.3e-3)
    ref = FD.run(sc0, cfg=cfg, seed=seed)
    rn = FD.run(sc1, cfg=cfg, seed=seed)
    rec0 = S.record_from_result(ref, sc0)
    rec1 = S.record_from_result(rn, sc1)
    d = rn.xy("pHx") - ref.xy("pHx")
    fs = FD.REC_HZ
    lo = sosfiltfilt(butter(4, 3.0, fs=fs, output="sos"), d, axis=0)
    bd = sosfiltfilt(butter(4, [3.0, 15.0], btype="band", fs=fs, output="sos"), d, axis=0)
    m = (rn["contact"] > 0) & (rn["t"] > 0.5)
    base = E.compare(rn, ref)["e_rms_um"]
    ro = FD.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle"), cfg, seed=seed)
    rb = FD.run(M.with_estimate(sc1, H.band_oracle_steps(rec1, rec0, sc1.t)), M.Controller(mode="external"), cfg, seed=seed)
    return {"seed": seed, "f0": f0, "config": label, "d_below_3Hz_um": E.rms2(lo, m) * 1e6, "d_3_15Hz_um": E.rms2(bd, m) * 1e6,
            "oracle_ratio": E.compare(ro, ref)["e_rms_um"] / base, "oracle_band_ratio": E.compare(rb, ref)["e_rms_um"] / base}


def _noise_closed(args):
    seed, f0, T, part, page = args
    key = "akf_1k" if page == "1k" else "akf_120"
    sp = H.Spec(f"akf_{part}_{page}", "akf", T[key]["params"], {"page": page, "comp": "gyro", "acc_part": part})
    rows = H.case(seed, f0, 0.3e-3, [sp], with_internal_kfosc=False, with_band_oracle=False)
    return [dict(r, part=part, page=page) for r in rows if r["label"] == sp.label]


def _imu_aa(args):
    seed, f0, aa, page = args
    from sim.pencil import model as M, evaluate as E
    ov = {"imu_aa": aa}
    if page == "120":
        ov.update({"sensing.opt_rate": 120.0, "sensing.opt_delay": 10e-3})
    cfg = M.PencilConfig(overrides=ov)
    sc0 = FD.test_scenario(seed)
    sc1 = FD.test_scenario(seed, f0, 0.3e-3)
    ref = FD.run(sc0, cfg=cfg, seed=seed)
    rn = FD.run(sc1, cfg=cfg, seed=seed)
    rk = FD.run(sc1, M.kalman_controller(), cfg, seed=seed)
    return {"seed": seed, "f0": f0, "imu_aa": aa, "page": page, "ratio": E.compare(rk, ref)["e_rms_um"] / E.compare(rn, ref)["e_rms_um"]}


def _jitter(args):
    """Tremor-band oracle plus band-limited random jitter: what estimate noise does to the pen (not an estimator)."""
    seed, label, band, rms = args
    from scipy.signal import butter, sosfiltfilt
    from sim.pencil import model as M, evaluate as E
    sc0 = FD.test_scenario(seed)
    sc1 = FD.test_scenario(seed, 8.0, 0.3e-3)
    ref = FD.run(sc0, seed=seed)
    rn = FD.run(sc1, seed=seed)
    rec0 = S.record_from_result(ref, sc0)
    rec1 = S.record_from_result(rn, sc1)
    t = np.arange(0.0, len(sc1.t) * rec1.dt, rec1.sdec * rec1.dt)[: int(math.ceil(len(sc1.t) / rec1.sdec))]
    dv = H.band_oracle_steps(rec1, rec0, t)
    if band is not None:
        rng = np.random.default_rng(seed + 17)
        nz = sosfiltfilt(butter(4, band, btype="band", fs=2000.0, output="sos"), rng.standard_normal(dv.shape), axis=0)
        dv = dv + nz / nz.std() * rms / math.sqrt(2.0)
    rx = FD.run(M.with_estimate(sc1, S.expand_to_steps(dv, len(sc1.t), rec1.sdec)), M.Controller(mode="external"), seed=seed)
    c = E.compare(rx, ref)
    m, _, n = E._mask(rx, rn)
    return {"seed": seed, "label": label, "ratio": c["e_rms_um"] / E.compare(rn, ref)["e_rms_um"],
            "P_rail_classB_mW": c["P_rail_classB_mW"], "housing_vs_neutral_um": E.rms2(rx.xy("pHx")[:n] - rn.xy("pHx")[:n], m) * 1e6}


def stage_sensors(workers: int):
    t0 = time.time()
    out = {"catalog": PT.catalog(), "snr": PT.snr_table(), "writing_vs_tremor": {
        "letter_2mm_3Hz_vs_tremor_0.1mm_6Hz": PT.writing_vs_tremor_acceleration(2e-3, 3.0, (0.1e-3, 6.0)),
        "letter_2mm_3Hz_vs_tremor_0.3mm_10Hz": PT.writing_vs_tremor_acceleration(2e-3, 3.0, (0.3e-3, 10.0))}}
    # open-loop: band error of the nib-acceleration estimate per compensation, rotation and tremor frequency (tuning seeds)
    from scipy.signal import butter, sosfiltfilt
    ol = []
    for f0 in (4.0, 6.0, 8.0, 10.0, 12.0):
        r1, _ = FD.test_pair_records(TUNE_SEEDS[0], f0, 0.3e-3)
        for comp in ("ideal", "none", "nose", "gyro", "dual"):
            for rho in (-0.5, 0.0, 0.5, 1.0):
                cfg = S.config(comp=comp, rho_t=rho, rho_w=rho)
                t_a = np.arange(0.0, r1.t[-1], 1.0 / cfg.acc.odr)
                est, tru = S.nib_acceleration(r1, cfg, np.random.default_rng(5), t_a, return_truth=True)
                sos = butter(4, [3.0, 15.0], btype="band", fs=cfg.acc.odr, output="sos")
                e = sosfiltfilt(sos, est[:, :2] - tru[:, :2], axis=0)
                tb = sosfiltfilt(sos, tru[:, :2], axis=0)
                m = t_a > 0.5
                ol.append({"f0": f0, "comp": comp, "rho": rho,
                           "band_error_rel": float(np.sqrt(np.mean(e[m] ** 2)) / np.sqrt(np.mean(tb[m] ** 2)))})
    # rotation phase (psi_t, relative to the hand tremor) and board distance (78-120 mm), rho = 0.5, 8 Hz
    olp = []
    r1, _ = FD.test_pair_records(TUNE_SEEDS[0], 8.0, 0.3e-3)
    for comp in ("none", "nose", "gyro", "dual"):
        for psi in (-90.0, 0.0, 90.0, 180.0):
            for rb in (0.078, 0.100, 0.120):
                cfg = S.config(comp=comp, rho_t=0.5, rho_w=0.5, psi_t=math.radians(psi))
                cfg.r_board = rb
                t_a = np.arange(0.0, r1.t[-1], 1.0 / cfg.acc.odr)
                est, tru = S.nib_acceleration(r1, cfg, np.random.default_rng(5), t_a, return_truth=True)
                sos = butter(4, [3.0, 15.0], btype="band", fs=cfg.acc.odr, output="sos")
                e = sosfiltfilt(sos, est[:, :2] - tru[:, :2], axis=0)
                tb = sosfiltfilt(sos, tru[:, :2], axis=0)
                m = t_a > 0.5
                olp.append({"comp": comp, "psi_deg": psi, "r_board_m": rb,
                            "band_error_rel": float(np.sqrt(np.mean(e[m] ** 2)) / np.sqrt(np.mean(tb[m] ** 2)))})
    out["leverarm_open_loop"] = {"rows": ol, "definition": "RMS of (estimate - true nib acceleration) / RMS(true), both band-passed 3-15 Hz; "
                                 "seed 5000 (tuning), 0.3 mm tremor; rho_t = rho_w = rho",
                                 "geometry": {"r_board_m": 0.100, "r_nose_m": 0.017, "r_ref_m": 0.100, "theta_deg": 50.0},
                                 "phase_and_distance": {"rows": olp, "setup": "rho 0.5, 8 Hz 0.3 mm, seed 5000; rotation phase psi_t relative to the hand tremor; board IMU at 78/100/120 mm"}}
    T = tuned()
    # design studies (compensation, IMU noise, estimate jitter) on tuning seeds, so no design choice is made on the test seeds
    DS = TUNE_SEEDS[:2]
    jobs = [(s, f0, T, comp, rho, page) for page in ("1k", "120") for s in DS for f0 in (4.0, 8.0, 12.0)
            for comp in ("ideal", "none", "nose", "gyro", "dual") for rho in (0.0, 0.5, 1.0) if f"akf_{page}" in T]
    aa_jobs = [(s, f0, aa, pg) for s in TEST_SEEDS for f0 in H.F0S for aa in (0.0, 1.0) for pg in ("1k", "120")]
    jit_cases = [("tremor-band oracle", None, 0.0), ("+ 10 um jitter 20-200 Hz", (20.0, 200.0), 10e-6),
                 ("+ 5 um jitter 200-900 Hz", (200.0, 900.0), 5e-6), ("+ 10 um jitter 200-900 Hz", (200.0, 900.0), 10e-6),
                 ("+ 20 um drift 0.2-3 Hz", (0.2, 3.0), 20e-6)]
    jit_jobs = [(s, lab, b, r) for s in DS for lab, b, r in jit_cases]
    nz_jobs = [(s, f0, T, part, page) for page in ("1k", "120") for s in DS for f0 in (4.0, 8.0, 12.0)
               for part in ("LSM6DSV16X", "BMI323") if f"akf_{page}" in T]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        cl = [r for rr in ex.map(_lever_closed, jobs) for r in rr]
        aa = list(ex.map(_imu_aa, aa_jobs))
        jit = list(ex.map(_jitter, jit_jobs))
        nz = [r for rr in ex.map(_noise_closed, nz_jobs) for r in rr]
        fc = list(ex.map(_friction_control, [(s, f0, lab) for s in TUNE_SEEDS[:2] for f0 in (6.0, 10.0) for lab in ("nominal", "frictionless")]))
    out["friction_control"] = {"rows": fc, "summary": {lab: {k: float(np.mean([r[k] for r in fc if r["config"] == lab]))
                                                             for k in ("d_below_3Hz_um", "d_3_15Hz_um", "oracle_ratio", "oracle_band_ratio")}
                                                       for lab in ("nominal", "frictionless")},
                               "setup": "tuning seeds 5000-5001, 6 and 10 Hz, 0.3 mm; frictionless = PencilConfig(mu_skid=0, mu_nib=0.02)"}
    out["imu_noise_closed_loop"] = {"summary": {f"{page}_{part}": {"ratio_mean": float(np.mean([r["ratio"] for r in nz if r["page"] == page and r["part"] == part])),
                                                                  "band_ratio_mean": float(np.mean([r["band_ratio"] for r in nz if r["page"] == page and r["part"] == part]))}
                                                for page in ("1k", "120") for part in ("LSM6DSV16X", "BMI323")
                                                if any(r["page"] == page and r["part"] == part for r in nz)},
                                    "rows": nz, "setup": "AKF (gyro-compensated, rho 0.5) with the LSM6DSV16X (60 ug/sqrt(Hz)) or BMI323 (180 ug/sqrt(Hz)) noise; tuning seeds 5000-5001, 4/8/12 Hz, 0.3 mm"}
    out["jitter_check"] = {"rows": jit, "summary": {lab: {"ratio_mean": float(np.mean([r["ratio"] for r in jit if r["label"] == lab])),
                                                         "P_rail_classB_mW_mean": float(np.mean([r["P_rail_classB_mW"] for r in jit if r["label"] == lab])),
                                                         "housing_vs_neutral_um_mean": float(np.mean([r["housing_vs_neutral_um"] for r in jit if r["label"] == lab]))}
                                                   for lab, _, _ in jit_cases},
                           "setup": "tremor-band oracle (true disturbance 3-15 Hz, zero-phase) plus band-limited Gaussian jitter of the stated RMS, "
                                    "tuning seeds 5000-5001, 8 Hz 0.3 mm; the stage's first resonance is 192 Hz (config/pencil.yaml)"}
    cls = {}
    for page in ("1k", "120"):
        for comp in ("ideal", "none", "nose", "gyro", "dual"):
            for rho in (0.0, 0.5, 1.0):
                R = [r["ratio"] for r in cl if r["page"] == page and r["comp"] == comp and r["rho"] == rho]
                B = [r["band_ratio"] for r in cl if r["page"] == page and r["comp"] == comp and r["rho"] == rho]
                if R:
                    cls[f"{page}_{comp}_rho{rho:g}"] = {"ratio_mean": float(np.mean(R)), "ratio_sd": float(np.std(R)),
                                                        "band_ratio_mean": float(np.mean(B)), "n": len(R)}
    out["leverarm_closed_loop"] = {"summary": cls, "rows": cl,
                                   "setup": "AKF tuned with the gyroscope-compensated IMU, run with each compensation; tuning seeds 5000-5001, 4/8/12 Hz, 0.3 mm"}
    aas = {}
    for pg in ("1k", "120"):
        for a_ in (0.0, 1.0):
            R = [r["ratio"] for r in aa if r["page"] == pg and r["imu_aa"] == a_]
            aas[f"{pg}_imu_aa{int(a_)}"] = {"kfosc_internal_ratio_mean": float(np.mean(R)), "n": len(R)}
    out["imu_aa_check"] = {"summary": aas, "rows": aa, "setup": "internal kfosc (core mode 3), seeds 200-203, 4-12 Hz, 0.3 mm; "
                           "page sensor 1 kHz / 2 ms or 120 Hz / 10 ms (sensing.opt_rate / opt_delay overrides)"}
    out["meta"] = _meta(EVIDENCE_CALC + "; " + EVIDENCE_SIM, {"open_loop": TUNE_SEEDS[0], "design_studies_closed_loop": list(DS),
                                                              "friction_control": list(TUNE_SEEDS[:2]), "imu_aa_check": list(TEST_SEEDS)},
                        {"elapsed_s": round(time.time() - t0, 1)})
    _write("sensors.json", out)
    return out


# ================================================================== context (aiguide writers)
def _ctx_tune_setup(job):
    from fusion import aieval as AE
    return AE.tune_setup(job)


def stage_context(workers: int, writers=None, f0s=None):
    from fusion import aieval as AE
    T = tuned()
    t0 = time.time()
    base = population(T)
    ctx = T.get("context")
    if ctx is None:
        # tune the template parameters on writers 100-105 (open loop), then store them
        jobs = [{"writer": w, "f0": f0, "sensors": SK_1K} for w in fusion.AIGUIDE_TUNE_WRITERS[:3] for f0 in (5.0, 8.0)]
        cands = AE.tune_candidates()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            items = list(ex.map(_ctx_tune_setup, jobs))
            chunks = [cands[i::workers] for i in range(workers)]
            parts = list(ex.map(AE.tune_score_chunk, [(items, base, ch) for ch in chunks]))
        by = {}
        for ch, sc in zip(chunks, parts):
            for c, s_ in zip(ch, sc):
                by[json.dumps(c, sort_keys=True)] = s_
        scores = [by[json.dumps(c, sort_keys=True)] for c in cands]
        k = int(np.argmin([s["J"] for s in scores]))
        ctx = {"params": dict(base, **cands[k]), "template_params": cands[k], "score": scores[k],
               "all": [dict(c, **s) for c, s in zip(cands, scores)], "writers": list(fusion.AIGUIDE_TUNE_WRITERS[:3]), "f0": [5.0, 8.0],
               "base": "akf_robust" if "akf_robust_1k" in T else "akf",
               "objective": "open loop on writers 100-102 at 5 and 8 Hz: mean over the AI-correct and AI-predicted templates of "
                            "(residual ratio + 0.5 false correction on the tremor-free writing / RMS disturbance) "
                            "+ 0.5 max(0, the same for the full-confidence wrong-letter template - no template)"}
        os.makedirs(TUNE_DIR, exist_ok=True)
        json.dump(ctx, open(os.path.join(TUNE_DIR, "context.json"), "w"), indent=1, default=float)
    cp = ctx["params"]
    sp = {"akf": ("akf", dict(T["akf_1k"]["params"]), SK_1K, None), "ctx_none": ("context", cp, SK_1K, None),
          "ctx_oracle": ("context", cp, SK_1K, "oracle"), "ctx_ai_correct": ("context", cp, SK_1K, "ai_correct"),
          "ctx_ai_predicted": ("context", cp, SK_1K, "ai_predicted"),
          "ctx_wrong_letter_gated": ("context", cp, SK_1K, "wrong_letter_gated"),
          "ctx_wrong_letter_full": ("context", cp, SK_1K, "wrong_letter_full")}
    if "akf_robust_1k" in T:
        sp["akf_robust"] = ("akf", dict(T["akf_robust_1k"]["params"]), SK_1K, None)
    if "wflc_1k" in T:
        sp["wflc"] = ("wflc", dict(T["wflc_1k"]["params"]), SK_1K, None)
    if "wflc_robust_1k" in T:
        sp["wflc_robust"] = ("wflc", dict(T["wflc_robust_1k"]["params"]), SK_1K, None)
    from fusion import learned as L
    if os.path.exists(os.path.join(L.MODEL_DIR, "gru48_1k.pt")):
        sp["gru"] = ("learned", {"model": "gru48_1k", "lp_hz": 60.0}, SK_1K, None)
    writers = writers or AE.TEST_WRITERS
    f0s = f0s or AE.F0S
    jobs = [{"writer": w, "f0": f0, "specs": sp} for w in writers for f0 in f0s]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        outs = list(ex.map(AE.scenario, jobs))
    labels = list(outs[0]["rows"].keys())
    summ = {}
    for lab in labels:
        for k in outs[0]["rows"][lab]:
            vals = [o["rows"][lab][k] for o in outs if isinstance(o["rows"][lab].get(k), (int, float)) and o["rows"][lab].get(k) is not None]
            if vals:
                summ.setdefault(lab, {})[k] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals)), "n": len(vals)}
        fl = [o["rows"][lab]["flips"]["newly_read_as_wrong_letter"] for o in outs if "flips" in o["rows"][lab]]
        if fl:
            summ[lab]["flips_newly_read_as_wrong_letter_total"] = int(np.sum(fl))
            summ[lab]["flips_n_letters_total"] = int(np.sum([o["rows"][lab]["flips"]["n"] for o in outs]))
    te = {}
    for c in ("oracle", "ai_correct", "ai_predicted", "wrong_letter"):
        for k in outs[0]["template_error"][c]:
            v = [o["template_error"][c][k] for o in outs]
            te.setdefault(c, {})[k] = {"mean": float(np.mean(v)), "sd": float(np.std(v))}
    by_f0 = {}
    for lab in labels:
        for f0 in f0s:
            v = [o["rows"][lab]["path_rms_um"] for o in outs if o["f0"] == f0]
            by_f0.setdefault(lab, {})[f"{f0:g}"] = float(np.mean(v))
    # spectra for the figure (writer 0, 6 Hz or first)
    su = AE.setup(writers[0], 6.0 if 6.0 in f0s else f0s[0])
    spec = {}
    for c in ("ai_correct", "ai_predicted", "wrong_letter", "oracle"):
        f, p = AE.template_spectrum(su, c)
        spec[c] = {"f_hz": f.tolist(), "psd_um2_per_hz": p.tolist()}
    out = {"meta": _meta(EVIDENCE_SIM + "; aiguide writers (glyph font), Tatoeba-CC0 n-gram predictor",
                         {"test_writers": list(writers), "tuning_writers": ctx.get("writers"), "f0_hz": list(f0s),
                          "tremor": "3000+10w+f0", "sensor_noise_sim": "11+w", "sensor_streams": "500000+1000w+f0"},
                         {"elapsed_s": round(time.time() - t0, 1)}),
           "setup": {"sentence": "return library books by friday", "tremor_mm": 0.3, "config": "pencil_P1 (q_lim 0.30 mm, user force 1.0 N)",
                     "sensors": SK_1K, "context_params": cp, "template_params": ctx.get("template_params"),
                     "c_min": AE.C_MIN, "c_full": AE.C_FULL},
           "template_error": te, "template_error_spectrum_writer0": spec, "summary": summ, "path_by_f0": by_f0,
           "prediction_accuracy_mean": float(np.mean([o["prediction_accuracy"] for o in outs])),
           "writing_band_um_mean": float(np.mean([o["writing_band_um"] for o in outs])),
           "writing_band_um_by_writer": {str(w): float(np.mean([o["writing_band_um"] for o in outs if o["writer"] == w])) for w in writers},
           "scenarios": [{"writer": o["writer"], "f0": o["f0"], "rows": o["rows"], "template_error": o["template_error"]} for o in outs],
           "context_tuning": {k: v for k, v in ctx.items() if k != "all"}, "context_tuning_all": ctx.get("all")}
    _write("context.json", out)
    return out


# ================================================================== learned
def stage_learned(retrain: bool, workers: int, minutes: float):
    from fusion import learned as L
    info = {}
    for name, kw in (("gru48_1k", dict(page="1k", tag="")),):
        p = os.path.join(L.MODEL_DIR, name + ".json")
        if retrain or not os.path.exists(p):
            L.train(n_train=kw.get("n_train", 400), n_val=24, hidden=48, epochs=12, page=kw["page"], tag=kw["tag"],
                    workers=workers, max_minutes=minutes)
        info[name] = json.load(open(p))
    out = {"meta": _meta(EVIDENCE_SIM, {"train": f"{fusion.TRAIN_SEEDS_BASE}+i sigma-lognormal, 16000+i glyph writers (i % 10 in 2, 5, 8); "
                                                 "tremor stream seed + 1000",
                                        "val": "9000-9011 and 9100-9111 sigma-lognormal, 19000+j glyph writers"}),
           "models": info}
    _write("learned.json", out)
    return out


# ================================================================== budget
def stage_budget():
    from fusion import budget as B
    ctx = tuned().get("context") or {}
    tr = float((ctx.get("params") or {}).get("t_rate", 500.0))
    out = {"meta": _meta(EVIDENCE_CALC, None),
           "p1_default_page_1kHz": B.estimator_costs(page_rate=1000.0, rollback_samples=4.0, tpl_rate=tr),
           "page_120Hz_10ms": B.estimator_costs(page_rate=120.0, rollback_samples=19.0, tpl_rate=tr)}
    _write("budget.json", out)
    return out


# ================================================================== main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", nargs="*", default=["tune", "sensors", "learned", "grid", "context", "budget", "figures", "evidence"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--retrain", action="store_true")
    ap.add_argument("--retune", action="store_true", help="re-run the parameter searches on the tuning seeds first")
    ap.add_argument("--train-minutes", type=float, default=40.0)
    ap.add_argument("--quick", action="store_true", help="grid on seed 200 at 6 and 10 Hz only (smoke run)")
    a = ap.parse_args(argv)
    t0 = time.time()
    # warm the numba caches in this process before forking
    r1, _ = FD.test_pair_records(TUNE_SEEDS[0], 6.0, 0.3e-3)
    from fusion import estimators as ES
    st = S.make_streams(r1, S.config(), 1)
    for n in ("kfosc", "akf", "bmflc", "wflc"):
        ES.run_estimator(n, st, {})
    if a.retune or not tuned():
        run_searches(a.workers)
    if "tune" in a.stages:
        stage_tune(a.workers)
        print(f"tune done {time.time() - t0:.0f} s", flush=True)
    if "sensors" in a.stages:
        stage_sensors(a.workers)
        print(f"sensors done {time.time() - t0:.0f} s", flush=True)
    if "learned" in a.stages:
        stage_learned(a.retrain, a.workers, a.train_minutes)
        print(f"learned done {time.time() - t0:.0f} s", flush=True)
    if "grid" in a.stages:
        if a.quick:
            stage_grid(a.workers, seeds=TEST_SEEDS[:1], f0s=(6.0, 10.0))
        else:
            stage_grid(a.workers)
        print(f"grid done {time.time() - t0:.0f} s", flush=True)
    if "context" in a.stages:
        stage_context(a.workers)
        print(f"context done {time.time() - t0:.0f} s", flush=True)
    if "budget" in a.stages:
        stage_budget()
    if "figures" in a.stages:
        from fusion import figures
        figures.make_all()
    if "evidence" in a.stages:
        from fusion import evidence
        evidence.write()
    print(f"all done {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
