#!/usr/bin/env python3
"""Frequency-gate behaviour of the Kalman profiles: prediction for AC-B09-15.

For the frozen Kalman set (results/sim/estimator_selection.json) and, for
reference, the v0.4.1 balanced ("inert") set, report on TEST seeds 200-203:
  (a) the fraction of in-contact samples with applied authority g >= 0.5
      (recorded channel "conf" = NIS confidence x frequency gate, after the
      authority time constant; the research-frame field g, docs/icd.md s4.2)
      with 9 and 10 Hz, 0.3 mm tremor on handwriting, and with 6 Hz tremor
      (below the 7.5 Hz gate, where the gate should stay closed);
  (b) the same fraction on tremor-free handwriting and on the feature course;
  plus the median tracked tremor frequency while in contact.
Evidence status: SIMULATION (synthetic writing and tremor, theta 50 deg, N 1 N).
Output: results/sim/gate_fraction.json.  Run: python3 sim/diag_gate.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import harness, model, scenarios  # noqa: E402
from stabpen import provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim", "gate_fraction.json")
SEEDS = harness.TEST_SEEDS[:4]
AMP = 3e-4
G_OPEN = 0.5
# v0.4.1 balanced selection (results/sim/estimator_selection.json at commit 2477142), kept for reference
INERT_V041 = {"kf_qj": 10.0, "kf_qt": 3e-09, "kf_w0_hz": 7.0, "f_gate": 7.5}


def gate_stats(r):
    con = r["contact"] > 0
    g = r["conf"][con]
    f = r["west"][con]  # recorded in Hz (sim/pensim/core.py)
    return {"frac_g_open": float(np.mean(g >= G_OPEN)), "g_mean": float(np.mean(g)),
            "f_track_median_hz": float(np.median(f)), "n": int(con.sum())}


def main():
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]["kfosc"]
    sets = {"kf_selected": sel["selected"]["params"], "kf_inert_v041": INERT_V041}
    out = {}
    for name, kw in sets.items():
        ctrl = model.Controller(mode="kfosc", **kw)
        cases = {}
        for seed in SEEDS:
            for f0 in (6.0, 9.0, 10.0):
                sc = scenarios.handwriting(seed=seed, duration=6.0, tremor=sg.TremorSpec(f0=f0, amp_pk=AMP))
                cases.setdefault(f"tremor_{f0:g}Hz", []).append(gate_stats(model.run(sc, ctrl)))
            cases.setdefault("no_tremor_handwriting", []).append(
                gate_stats(model.run(scenarios.handwriting(seed=seed, duration=6.0), ctrl)))
        cases["no_tremor_feature_course"] = [gate_stats(model.run(scenarios.features(), ctrl))]
        out[name] = {"params": kw, "cases": {
            k: {"frac_g_open_mean": float(np.mean([v["frac_g_open"] for v in vs])),
                "frac_g_open_per_seed": [round(v["frac_g_open"], 4) for v in vs],
                "g_mean": float(np.mean([v["g_mean"] for v in vs])),
                "f_track_median_hz": float(np.median([v["f_track_median_hz"] for v in vs]))}
            for k, vs in cases.items()}}
        for k, v in out[name]["cases"].items():
            print(f"{name:18s} {k:26s} g>=0.5: {v['frac_g_open_mean']:.3f}  per seed {v['frac_g_open_per_seed']}"
                  f"  f_track {v['f_track_median_hz']:.2f} Hz")
    meta = provenance.metadata("simulation (synthetic writing and tremor, TEST seeds; not bench data)",
                               seeds={"test": list(SEEDS)},
                               extra={"amp_m": AMP, "g_open_threshold": G_OPEN,
                                      "criterion": "AC-B09-15: (a) >= 0.9 with 9-10 Hz tremor; (b) <= 0.05 without tremor"})
    provenance.write_json(OUT, {"meta": meta, "results": out})


if __name__ == "__main__":
    main()
