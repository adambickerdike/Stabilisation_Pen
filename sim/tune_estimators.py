#!/usr/bin/env python3
"""Select conventional estimator parameters on TUNING seeds only.

Objective (lower is better), averaged over tuning cases:
    J = ratio_vs_neutral + lambda_d * distortion_um / base_e_rms_um
where distortion is the ink error the controller introduces on the same
handwriting WITHOUT disturbance.  lambda_d = 1 treats one micrometre of
distortion as costly as one micrometre of residual disturbance.
The selected parameters are frozen in results/sim/estimator_selection.json
and used unchanged by run_nominal.py and run_sweeps.py on TEST seeds.
Evidence status: SIMULATION on synthetic signals (not human data).
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.pensim import harness  # noqa: E402
from stabpen import provenance  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sim")
LAMBDA_D = 1.0          # balanced operating point
LAMBDA_ASSERTIVE = 0.3  # assertive operating point (accepts more distortion)
TUNE_F0 = (4.5, 6.0, 8.0, 10.0)
TUNE_AMP = 3e-4


def objective(rows, lam=LAMBDA_D):
    import numpy as np
    return float(np.mean([r["ratio"] + lam * r["distortion_um"] / r["base_e_rms_um"] for r in rows]))


def main():
    t0 = time.time()
    grids = {
        "kfosc": [dict(kf_qj=qj, kf_qt=qt, kf_w0_hz=7.0, f_gate=fg) for qj, qt, fg in
                  itertools.product((0.1, 0.3, 1.0, 3.0, 10.0), (3e-9, 1e-8), (0.0, 6.5, 7.5))],
        "bpf": [dict(bp_lo=lo, bp_hi=hi, bp_tune_hz=7.0) for lo, hi in ((6.0, 16.0), (4.5, 16.0), (6.0, 12.0))],
    }
    results = {}
    for mode, grid in grids.items():
        scored = []
        for kw in grid:
            cases = [dict(seed=s, f0=f, amp=TUNE_AMP, mode=mode, ctrl=kw) for s in harness.TUNING_SEEDS for f in TUNE_F0]
            rows = harness.run_cases(cases)
            J = objective(rows)
            scored.append({"params": kw, "J": J, "J_assertive": objective(rows, LAMBDA_ASSERTIVE),
                           "per_f0": {str(f): {"ratio": float(sum(r["ratio"] for r in rows if r["f0"] == f) / sum(1 for r in rows if r["f0"] == f)),
                                                "distortion_um": float(sum(r["distortion_um"] for r in rows if r["f0"] == f) / sum(1 for r in rows if r["f0"] == f))}
                                      for f in TUNE_F0},
                           "mean_ratio": sum(r["ratio"] for r in rows) / len(rows),
                           "mean_distortion_um": sum(r["distortion_um"] for r in rows) / len(rows)})
            print(f"{mode} {kw} J={J:.3f} ratio={scored[-1]['mean_ratio']:.3f} dist={scored[-1]['mean_distortion_um']:.1f}", flush=True)
        scored.sort(key=lambda d: d["J"])
        assertive = min(scored, key=lambda d: d["J_assertive"])
        results[mode] = {"selected": scored[0], "selected_assertive": assertive, "all": scored}
    meta = provenance.metadata("simulation (synthetic signals, tuning seeds only)",
                               seeds={"tuning": list(harness.TUNING_SEEDS)},
                               extra={"objective": "mean(ratio + lambda_d*distortion/base)", "lambda_d": LAMBDA_D,
                                      "tune_f0_hz": TUNE_F0, "tune_amp_m": TUNE_AMP, "elapsed_s": time.time() - t0})
    provenance.write_json(os.path.join(OUT, "estimator_selection.json"), {"meta": meta, "results": results})
    for mode in results:
        print("SELECTED", mode, results[mode]["selected"])


if __name__ == "__main__":
    main()
