"""Benchmark helpers: references, housing-level oracle disturbance and a
standard multi-controller comparison.  Evidence status: SIMULATION."""
from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np

from . import evaluate, model

DEFAULT_MODES = ("rigid", "neutral", "bpf", "kfosc", "oracle")


def references(scn_clean, geom=None, overrides=None, seed=1):
    ref_same = model.run(scn_clean, model.Controller(mode="neutral"), geom, overrides, seed=seed)
    ref_rigid = model.run(scn_clean, model.Controller(mode="rigid"), geom, overrides, seed=seed)
    return ref_same, ref_rigid


def housing_disturbance(scn_tremor, ref_same, geom=None, overrides=None, seed=1):
    """Clean housing path (powered-neutral, no disturbance) upsampled to the
    simulation rate.  The oracle controller uses d = p_H(now) - clean_path(now),
    i.e. the instantaneous true housing disturbance with zero sensing delay."""
    r = model.run(scn_tremor, model.Controller(mode="neutral"), geom, overrides, seed=seed)
    t_rec = ref_same["t"]
    clean = ref_same.xy("pHx")
    t = scn_tremor.t
    d = np.column_stack([np.interp(t, t_rec, clean[:, 0]), np.interp(t, t_rec, clean[:, 1])])
    return d, r


def with_disturbance(scn, d):
    s2 = copy.copy(scn)
    s2.dtrue = d
    return s2


def compare_modes(scn_clean, scn_tremor, modes=DEFAULT_MODES, ctrl_kw=None, geom=None, overrides=None,
                  seed=1, oracle_h=0.0):
    """Run all modes on the tremor scenario; metrics vs same-pen clean reference.
    Also runs each estimator on the clean scenario to measure intended-path
    distortion (no disturbance present)."""
    ctrl_kw = ctrl_kw or {}
    ref_same, ref_rigid = references(scn_clean, geom, overrides, seed)
    d_h, neutral_tr = housing_disturbance(scn_tremor, ref_same, geom, overrides, seed)
    scn_o = with_disturbance(scn_tremor, d_h)
    out = {"device_vs_rigid": device_distortion(ref_same, ref_rigid)}
    runs = {}
    for mode in modes:
        kw = dict(ctrl_kw.get(mode, {}))
        if mode == "oracle":
            kw.setdefault("oracle_h", oracle_h)
        ctrl = model.Controller(mode=mode, **kw)
        s_use = scn_o if mode == "oracle" else scn_tremor
        r = neutral_tr if (mode == "neutral" and not kw) else model.run(s_use, ctrl, geom, overrides, seed=seed)
        ref = ref_rigid if mode == "rigid" else ref_same
        m = evaluate.compare(r, ref)
        if mode not in ("rigid", "neutral", "oracle"):
            rc = model.run(scn_clean, ctrl, geom, overrides, seed=seed)
            m["distortion_clean_rms_um"] = evaluate.compare(rc, ref_same)["e_rms_um"]
            feats = scn_clean.meta.get("features") or []
        out[mode] = m
        runs[mode] = r
    base = out["neutral"]["e_rms_um"]
    for mode in modes:
        out[mode]["ratio_vs_neutral"] = out[mode]["e_rms_um"] / base if base > 0 else float("nan")
    return out, runs, (ref_same, ref_rigid)


def device_distortion(ref_same, ref_rigid):
    """Ink difference between the suspended active pen held at neutral and an
    ordinary rigid pen, same hand motion, no disturbance.  Mean offset removed
    (a constant offset is invisible to the writer)."""
    n = min(len(ref_same["t"]), len(ref_rigid["t"]))
    m = (ref_same["contact"][:n] > 0) & (ref_rigid["contact"][:n] > 0) & (ref_same["t"][:n] > 0.5)
    e = ref_same.xy("tipx")[:n] - ref_rigid.xy("tipx")[:n]
    if not m.any():
        return {}
    off = e[m].mean(axis=0)
    ed = e[m] - off
    return {"mean_offset_um": (off * 1e6).tolist(),
            "detrended_rms_um": float(np.sqrt(np.mean(np.sum(ed ** 2, axis=1))) * 1e6),
            "detrended_p95_um": float(np.percentile(np.linalg.norm(ed, axis=1), 95) * 1e6)}
