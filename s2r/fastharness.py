"""Faster drop-in for sim.pensim.harness.eval_case / run_cases when many plants share seeds.

sim.pensim.harness regenerates the synthetic scenario (0.6 s for 6 s of writing at 25 us)
for every plant because its caches are keyed by the plant overrides. Here the scenarios
are generated once, stored under s2r/build/scn_cache/ as .npy files and memory-mapped
read-only (the page cache is shared by the worker processes), and a persistent process
pool keeps each worker's caches and compiled code across plant evaluations. The metric
code path is harness.eval_case's, line for line; s2r/tests/test_fastharness.py checks
that the outputs are identical.

Evidence status of the outputs: SIMULATION (as the harness).
"""
from __future__ import annotations

import atexit
import functools
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import PKG_DIR
from sim.pensim import bench, evaluate, model, scenarios
from stabpen import signals as sg

SCN_DIR = os.path.join(PKG_DIR, "build", "scn_cache")
_FIELDS = ("t", "pref", "vref", "fpush", "dtrue", "intended", "opt_ok")


def _key(d):
    return tuple(sorted((k, v) for k, v in (d or {}).items()))


def _name(seed, duration, theta, N0, f0, amp, tr_key):
    tr = "none" if f0 is None else f"f{f0:g}_a{amp:g}_" + "_".join(f"{k}{v:g}" for k, v in tr_key)
    return f"hw_s{seed}_d{duration:g}_th{theta:g}_N{N0:g}_{tr}"


def scenario(seed, duration=6.0, theta=50.0, N0=1.0, f0=None, amp=None, tr_key=()):
    """Scenario identical to scenarios.handwriting(...), cached on disk and memory-mapped."""
    d = os.path.join(SCN_DIR, _name(seed, duration, theta, N0, f0, amp, tr_key))
    if not os.path.exists(os.path.join(d, "done")):
        tr = None if f0 is None else sg.TremorSpec(f0=f0, amp_pk=amp, **dict(tr_key))
        sc = scenarios.handwriting(seed=seed, duration=duration, tremor=tr, theta_deg=theta, N0=N0)
        tmp = d + f".tmp{os.getpid()}"
        os.makedirs(tmp, exist_ok=True)
        for f in _FIELDS:
            np.save(os.path.join(tmp, f + ".npy"), np.ascontiguousarray(getattr(sc, f)))
        meta = {"theta_deg": sc.theta_deg, "phi_deg": sc.phi_deg, "rho_deg": sc.rho_deg, "N0": sc.N0,
                "features": sc.meta.get("features", [])}
        with open(os.path.join(tmp, "meta.json"), "w") as fh:
            json.dump(meta, fh, default=float)
        open(os.path.join(tmp, "done"), "w").close()
        try:
            os.rename(tmp, d)
        except OSError:               # another process won the race; its copy is identical
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
    arr = {f: np.load(os.path.join(d, f + ".npy"), mmap_mode="r") for f in _FIELDS}
    with open(os.path.join(d, "meta.json")) as fh:
        meta = json.load(fh)
    return model.Scenario(t=arr["t"], pref=arr["pref"], vref=arr["vref"], fpush=arr["fpush"], dtrue=arr["dtrue"],
                          intended=arr["intended"], opt_ok=arr["opt_ok"], theta_deg=meta["theta_deg"],
                          phi_deg=meta["phi_deg"], rho_deg=meta["rho_deg"], N0=meta["N0"],
                          meta={"features": meta["features"]})


@functools.lru_cache(maxsize=48)
def _refs(seed, duration, theta, N0, ov_key):
    ov = dict(ov_key)
    sc0 = scenario(seed, duration, theta, N0)
    rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    return sc0, rs


@functools.lru_cache(maxsize=96)
def _tremor_case(seed, duration, theta, N0, f0, amp, ov_key, tr_key):
    ov = dict(ov_key)
    sc1 = scenario(seed, duration, theta, N0, f0, amp, tr_key)
    sc0, rs = _refs(seed, duration, theta, N0, ov_key)
    rn = model.run(sc1, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    return sc1, evaluate.compare(rn, rs)


def eval_case(case):
    """Same inputs, outputs and code path as sim.pensim.harness.eval_case."""
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


_POOL = {}


def _pool(workers):
    if workers not in _POOL:
        _POOL[workers] = ProcessPoolExecutor(max_workers=workers)
        atexit.register(_POOL[workers].shutdown)
    return _POOL[workers]


def prepare(seeds, f0s=(), amp=3e-4, duration=6.0, theta=50.0, N0=1.0):
    """Generate the cached scenarios up front (serially, once)."""
    for s in seeds:
        scenario(s, duration, theta, N0)
        for f in f0s:
            scenario(s, duration, theta, N0, f, amp)


def run_cases(cases, workers=2):
    """Cases sorted by (seed, f0) so consecutive cases reuse a worker's caches; results
    returned in the input order."""
    if workers <= 1:
        return [eval_case(c) for c in cases]
    order = sorted(range(len(cases)), key=lambda i: (cases[i]["seed"], cases[i].get("f0", 0.0)))
    res = list(_pool(workers).map(eval_case, [cases[i] for i in order], chunksize=4))
    out = [None] * len(cases)
    for j, i in enumerate(order):
        out[i] = res[j]
    return out
