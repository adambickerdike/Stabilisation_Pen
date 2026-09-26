"""Parallel evaluation harness: one 'case' = (scenario seed, disturbance,
controller) evaluated against the same-pen clean reference, plus the same
controller on the clean scenario (intended-path distortion).

Seeds are partitioned into disjoint TUNING and TEST sets so estimator
parameters are selected on tuning seeds only and frozen before testing.
All outputs are SIMULATION results on synthetic signals.
"""
from __future__ import annotations

import functools
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from stabpen import signals as sg
from . import bench, evaluate, model, scenarios

TUNING_SEEDS = tuple(range(100, 106))
TEST_SEEDS = tuple(range(200, 212))


def _key(d):
    return tuple(sorted((k, v) for k, v in (d or {}).items()))


@functools.lru_cache(maxsize=64)
def _refs(seed, duration, theta, N0, ov_key):
    ov = dict(ov_key)
    sc0 = scenarios.handwriting(seed=seed, duration=duration, tremor=None, theta_deg=theta, N0=N0)
    rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    return sc0, rs


@functools.lru_cache(maxsize=64)
def _tremor_case(seed, duration, theta, N0, f0, amp, ov_key, tr_key):
    ov = dict(ov_key)
    tr = sg.TremorSpec(f0=f0, amp_pk=amp, **dict(tr_key))
    sc1 = scenarios.handwriting(seed=seed, duration=duration, tremor=tr, theta_deg=theta, N0=N0)
    sc0, rs = _refs(seed, duration, theta, N0, ov_key)
    rn = model.run(sc1, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    base = evaluate.compare(rn, rs)
    return sc1, base


def eval_case(case):
    """case: dict(seed, f0, amp, mode, ctrl, overrides, theta, N0, duration, tremor_kw, distortion)"""
    seed = case["seed"]; dur = case.get("duration", 6.0)
    th = case.get("theta", 50.0); N0 = case.get("N0", 1.0)
    ov = case.get("overrides") or {}
    ovk = _key(ov)
    trk = _key(case.get("tremor_kw"))
    sc0, rs = _refs(seed, dur, th, N0, ovk)
    sc1, base = _tremor_case(seed, dur, th, N0, case["f0"], case["amp"], ovk, trk)
    ctrl = model.Controller(mode=case["mode"], **(case.get("ctrl") or {}))
    scn = sc1
    if case["mode"] == "oracle":
        d, _ = bench.housing_disturbance(sc1, rs, overrides=ov, seed=seed)
        scn = bench.with_disturbance(sc1, d)
    r = model.run(scn, ctrl, overrides=ov, seed=seed)
    m = evaluate.compare(r, rs)
    m["ratio"] = m["e_rms_um"] / base["e_rms_um"]
    m["band_ratio"] = m["e_band_rms_um"] / base["e_band_rms_um"]
    m["base_e_rms_um"] = base["e_rms_um"]
    m["base_band_um"] = base["e_band_rms_um"]
    m["w_final_hz"] = float(r["west"][-1])
    if case.get("distortion", True) and case["mode"] not in ("neutral", "oracle", "rigid"):
        rc = model.run(sc0, ctrl, overrides=ov, seed=seed)
        m["distortion_um"] = evaluate.compare(rc, rs)["e_rms_um"]
    else:
        m["distortion_um"] = 0.0
    out = {k: case[k] for k in ("seed", "f0", "amp", "mode") if k in case}
    out.update({"theta": th, "N0": N0, "tag": case.get("tag", "")})
    out.update(m)
    return out


def run_cases(cases, workers=None):
    workers = workers or min(4, os.cpu_count() or 1)
    if workers <= 1:
        return [eval_case(c) for c in cases]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(eval_case, cases, chunksize=2))
