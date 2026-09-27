#!/usr/bin/env python3
"""How fast must the page sensor be for guided mode?  (pencil capture question)

A pencil-sized pen has no room for the Rev A near-nib optical sensor
(OPT-05: 6 x 6 x 3.08 mm module); the chip-scale camera that fits runs at
30 fps (OPT-36).  In the M1 core the housing position used by guided mode is
the last page-sensor sample plus the IMU-integrated displacement since then
(sim/pensim/core.py, ph0/ph1), so the question is how rate and latency of the
page sensor limit guided mode with that fusion.

Evidence status: SIMULATION (model M1, feature course, 6 Hz / 0.3 mm tremor,
tremor seeds 0-3, parameters v0.4.4).  Latency model: one frame period plus
2 ms of exposure/decoding (ASSUMPTION).  Metric: path distance from in-contact
ink to the template (as sim/guided_eval.py), RMS over seeds.
Output: results/sim/page_sensor_rate.json.  Run: python3 sim/diag_page_sensor_rate.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import model, scenarios  # noqa: E402
from stabpen import provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim", "page_sensor_rate.json")
SEEDS = (0, 1, 2, 3)
RATES = (30.0, 60.0, 120.0, 250.0, 1000.0)


def path_rms(rates_over):
    acc = {"neutral": [], "guided": []}
    for seed in SEEDS:
        sc = scenarios.features(tremor=sg.TremorSpec(f0=6.0, amp_pk=3e-4), seed=seed)
        tree = cKDTree(sc.intended)
        for mode in acc:
            r = model.run(sc, model.Controller(mode=mode), overrides=rates_over, seed=seed + 1)
            con = r["contact"] > 0
            d, _ = tree.query(r.xy("tipx")[con])
            acc[mode].append(d)
    return {m: float(np.sqrt(np.mean(np.concatenate(v) ** 2)) * 1e6) for m, v in acc.items()}


def main():
    rows = []
    for f in RATES:
        lat = 1.0 / f + 2e-3
        m = path_rms({"sensing.opt_rate": f, "sensing.opt_delay": lat})
        rows.append({"rate_hz": f, "latency_s": round(lat, 4), "neutral_path_rms_um": round(m["neutral"], 1),
                     "guided_path_rms_um": round(m["guided"], 1), "guided_over_neutral": round(m["guided"] / m["neutral"], 3)})
        print(rows[-1])
    m = path_rms({})     # parameter defaults: 1 kHz, 2 ms
    rows.append({"rate_hz": 1000.0, "latency_s": 0.002, "neutral_path_rms_um": round(m["neutral"], 1),
                 "guided_path_rms_um": round(m["guided"], 1), "guided_over_neutral": round(m["guided"] / m["neutral"], 3),
                 "note": "parameters.yaml defaults (sensing.opt_rate, sensing.opt_delay)"})
    print(rows[-1])
    meta = provenance.metadata("simulation (M1 feature course, 6 Hz 0.3 mm tremor; latency = 1 frame + 2 ms, assumption)",
                               seeds={"tremor": list(SEEDS)})
    provenance.write_json(OUT, {"meta": meta, "rows": rows,
                                "note": ("Guided mode fuses the page sensor with the IMU between samples (core.py ph0/ph1). "
                                         "The 1 kHz case is not monotonic in latency (2 ms default vs 3 ms differ by about 10 %): "
                                         "the alignment of optical and IMU delays in the fusion matters at that level (open).")})


if __name__ == "__main__":
    main()
