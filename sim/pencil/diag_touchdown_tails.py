#!/usr/bin/env python3
"""Touchdown and lift tails of the skid pencil, and a tilt-adaptive front stop.

Finding from the AI-guidance rerun on model P1 (docs/ai_guidance.md s4): the
refill's front stop is set for the whole tilt range (ball-centre protrusion
2.06 mm, design.protrusion_budget), so at 50 deg the unloaded refill stands
1.34 mm proud of where it writes.  At touchdown the ball lands first and
slides along the page by about 1.34 mm x cos(50 deg) = 0.86 mm while the
refill retracts; the same happens in reverse at lift.

Mitigation tested here: a front stop that follows the tilt, at the protrusion
the current tilt needs plus a margin (s_min = -margin; a slow trim actuator
driven by the IMU tilt would do this in hardware, see docs/pencil_concept.md).
The margin cannot be small: the refill also slides by q cot(theta) while the
stage corrects in the tilt plane, so the correction case (oracle) is checked
for lost contact.  Tilt is constant in these runs, so the stop tracks it
perfectly: a best case for the tracking actuator.

Evidence status: SIMULATION (model P1, synthetic handwriting, test seeds
200-203, 50 deg, 1 N; oracle with 6 Hz 0.3 mm tremor).
Output: results/pencil/touchdown_tails.json.
Run: python3 -m sim.pencil.diag_touchdown_tails
"""
from __future__ import annotations

import os

import numpy as np
from scipy.spatial import cKDTree

from sim.pensim import scenarios
from sim.pencil import model as M
from stabpen import provenance
from stabpen import signals as sg

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "pencil", "touchdown_tails.json")
SEEDS = (200, 201, 202, 203)
MARGINS = (None, 0.30e-3, 0.20e-3, 0.10e-3)     # None: the tilt-range front stop of P0.1.2


def ink_stats(r, tree):
    C = np.column_stack([r["Cx"], r["Cy"]])
    nib, sk = r["contact"] > 0, r["skid_contact"] > 0
    step = np.r_[0.0, np.linalg.norm(np.diff(C, axis=0), axis=1)]
    d_all, _ = tree.query(C[nib])
    return {"ink_mm": float(step[nib].sum() * 1e3), "tail_mm": float(step[nib & ~sk].sum() * 1e3),
            "pen_downs": int(np.sum(np.diff(nib.astype(int)) == 1)),
            "path_rms_all_um": float(np.sqrt(np.mean(d_all ** 2)) * 1e6)}


def main():
    rows = []
    for seed in SEEDS:
        sc0 = scenarios.handwriting(seed=seed, duration=5.0, tremor=None, N0=1.0)
        sc1 = scenarios.handwriting(seed=seed, duration=5.0, tremor=sg.TremorSpec(f0=6.0, amp_pk=3e-4), N0=1.0)
        tree = cKDTree(sc0.intended)
        rigid = M.run(sc0, M.Controller(mode="neutral"), M.PencilConfig(locked=True), seed=seed + 1)
        n_strokes = ink_stats(rigid, tree)["pen_downs"]
        for mg in MARGINS:
            ov = {} if mg is None else {"s_min": -mg, "s_init": -mg}
            cfg = M.PencilConfig(overrides=ov)
            ref = M.run(sc0, M.Controller(mode="neutral"), cfg, seed=seed + 1)
            neu = M.run(sc1, M.Controller(mode="neutral"), cfg, seed=seed + 1)
            d_clean = M.housing_disturbance(sc1, ref)
            orc = M.run(M.with_disturbance(sc1, d_clean), M.Controller(mode="oracle"), cfg, seed=seed + 1)
            e_n = M_eval(neu, ref); e_o = M_eval(orc, ref)
            st0, sto = ink_stats(ref, tree), ink_stats(orc, tree)
            rows.append({"seed": seed, "margin_mm": None if mg is None else mg * 1e3, "strokes_rigid": n_strokes,
                         "no_tremor": st0, "oracle_6Hz_0.3mm": sto,
                         "oracle_ratio": e_o / e_n if e_n > 0 else float("nan"),
                         "oracle_lost_contact_frac": float(np.mean((ref["contact"] > 0) & (orc["contact"] <= 0)))})
            print(rows[-1]["seed"], rows[-1]["margin_mm"], st0, round(rows[-1]["oracle_ratio"], 3), round(rows[-1]["oracle_lost_contact_frac"], 4))
    summ = {}
    for mg in MARGINS:
        key = "tilt_range_stop" if mg is None else f"adaptive_{mg * 1e3:.2f}mm"
        rs = [r for r in rows if r["margin_mm"] == (None if mg is None else mg * 1e3)]
        summ[key] = {
            "tail_fraction_no_tremor": float(np.mean([r["no_tremor"]["tail_mm"] / r["no_tremor"]["ink_mm"] for r in rs])),
            "tail_mm_per_pen_down": float(np.mean([r["no_tremor"]["tail_mm"] / max(r["no_tremor"]["pen_downs"], 1) for r in rs])),
            "pen_downs_vs_rigid": float(np.mean([r["no_tremor"]["pen_downs"] / max(r["strokes_rigid"], 1) for r in rs])),
            "path_rms_all_um_no_tremor": float(np.mean([r["no_tremor"]["path_rms_all_um"] for r in rs])),
            "oracle_ratio": float(np.mean([r["oracle_ratio"] for r in rs])),
            "oracle_lost_contact_frac": float(np.mean([r["oracle_lost_contact_frac"] for r in rs])),
        }
        print(key, {k: round(v, 4) for k, v in summ[key].items()})
    meta = provenance.metadata("simulation (pencil model P1, synthetic handwriting; tilt constant, so the adaptive stop tracks it perfectly)",
                               seeds={"handwriting": list(SEEDS)})
    provenance.write_json(OUT, {"meta": meta, "summary": summ, "rows": rows,
                                "note": ("margin = front stop beyond the protrusion the tilt needs; the refill must also slide q cot(theta) "
                                         "while the stage corrects, so small margins lose contact during correction")})


def M_eval(res, ref):
    from sim.pencil import evaluate
    return evaluate.compare(res, ref)["e_rms_um"]


if __name__ == "__main__":
    main()
