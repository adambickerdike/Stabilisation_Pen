#!/usr/bin/env python3
"""Guided (template-following) mode vs free assistance on the feature course.

Evidence status: SIMULATION (model M1, deterministic feature course with 6 Hz /
0.3 mm tremor, seeds 0-3 for the tremor realisation).

Metric: path distance = distance from each in-contact ink sample to the
nearest point of the intended path (template), per feature, RMS and 95th
percentile.  Unlike the time-aligned ink error, this rewards drawing the right
shape even if slightly early or late, which is the point of guided tracing.
Outputs results/sim/guided_path_distance.json.  Run: python3 sim/guided_eval.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import model, scenarios  # noqa: E402
from stabpen import provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

SEEDS = (0, 1, 2, 3)


def main():
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
    ka = sel["kfosc"]["selected_assertive"]["params"]
    ctrls = {"neutral": ("neutral", {}), "guided": ("guided", {}), "kf_asr": ("kfosc", ka)}
    acc = {}
    for seed in SEEDS:
        sc = scenarios.features(tremor=sg.TremorSpec(f0=6.0, amp_pk=3e-4), seed=seed)
        tree = cKDTree(sc.intended)
        for name, (mode, kw) in ctrls.items():
            r = model.run(sc, model.Controller(mode=mode, **kw), seed=seed + 1)
            t = r["t"]
            ink = r.xy("tipx")
            con = r["contact"] > 0
            for feat, t0, t1, _meta in sc.meta.get("features", []) or []:
                m = (t >= t0) & (t <= t1) & con
                if m.sum() < 10:
                    continue
                d, _ = tree.query(ink[m])
                a = acc.setdefault((name, feat), [])
                a.append(d)
    out = {}
    for (name, feat), ds in acc.items():
        d = np.concatenate(ds) * 1e6
        out.setdefault(feat, {})[name] = {"rms_um": float(np.sqrt(np.mean(d ** 2))), "p95_um": float(np.percentile(d, 95)), "n": int(d.size)}
    meta = provenance.metadata("simulation (feature course, 6 Hz 0.3 mm tremor)", seeds={"tremor": list(SEEDS)})
    provenance.write_json(os.path.join(ROOT, "results", "sim", "guided_path_distance.json"), {"meta": meta, "path_distance": out})
    for feat, v in out.items():
        print(feat, {k: round(x["rms_um"], 1) for k, x in v.items()})


if __name__ == "__main__":
    main()
