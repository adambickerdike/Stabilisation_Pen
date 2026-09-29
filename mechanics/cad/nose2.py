#!/usr/bin/env python3
"""Parametric CAD concept of the Rev J nose ("nose v2", study N): the recommended short-arm 2-axis flexure gimbal and its
actuator (from results/nose2/nose2.json), a +-6 mm class tip travel, the generalised C-shaped skid ring, the pen lift
(pen-up/down), the refill channel and the paper sensor (CadQuery 2.x).

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from nose2/layout.layout(), which takes the
optimised design (results/nose2/nose2.json -> "recommended") and the front-end closure (nose2/frontend.py).  Fit checks
are geometric only.  Nothing was built or measured.

Datums and conventions as mechanics/cad/revH_pen.py (reused read-only): origin at the ball centre, z along the pen axis
from the tip toward the back, x in the tilt plane, mm.
Outputs (results/nose2/): nose2_assembly.step, nose2_cad_summary.json, drawing_nose2.png and its CSV twin
(drawing_nose2.csv, the component table), fig_nose2_front_end.png (+ .csv): side views at 35/50/75 deg.
Run: python3 mechanics/cad/nose2.py [--no-step] [--design results/nose2/nose2.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))

import revH_pen as RC  # noqa: E402  (read-only reuse: solid, build_assembly, drawing, COLORS)
from nose2 import layout as LY  # noqa: E402

OUT = os.path.join(ROOT, "results", "nose2")


def load_design(path):
    with open(path) as f:
        d = json.load(f)
    rec = d.get("recommended") or d
    return rec["design"], rec.get("handle_od", 24.0)


def component_csv(geo, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm", "moves_with",
                    "optional", "mass_g", "part", "ledger"])
        for c in geo["components"]:
            w.writerow([c["id"], c["label"], c["group"], c["shape"], c["z0"], c["z1"], c.get("d0", ""), c.get("d1", ""), c.get("d_in", ""),
                        c.get("size", ""), c.get("offset", ""), c["moves_with"], c["optional"], c.get("mass_g", ""), c["part"], c["ledger"]])


def front_end_figure(geo, path_png):
    """Side views at 35/50/75 deg with the nose at rest and at +-travel (opt/inertial/front_end.figure, read-only)."""
    from opt.inertial import front_end as FE
    from opt.inertial.revh import RevH
    import matplotlib.figure as mfig
    d = replace(RevH(), travel=geo["tip_travel_mm"] * 1e-3, z_p=geo["pivot_z"] * 1e-3)
    ru = replace(FE.FrontRules(), stop=geo["tip_travel_mm"] + 0.5)
    orig = mfig.Figure.suptitle

    def retitled(self, t, *a, **k):                     # the read-only function titles its figure "Rev H front end"
        return orig(self, t.replace("Rev H front end", f"Rev J nose v2 front end (nominal travel {geo['tip_travel_mm']:.2f} mm, "
                                                     f"pivot {geo['pivot_z']:.1f} mm)"), *a, **k)
    mfig.Figure.suptitle = retitled
    try:
        FE.figure(geo["skid_contact_radius"], d, ru, path_png)
    finally:
        mfig.Figure.suptitle = orig
    chk = FE.check(geo["skid_contact_radius"], d, ru, n_theta=9, n_phi=24)
    with open(path_png.replace(".png", ".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(chk["by_tilt"][0].keys()))
        w.writeheader()
        for r in chk["by_tilt"]:
            w.writerow({k: round(v, 4) for k, v in r.items()})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--design", default=os.path.join(OUT, "nose2.json"))
    ap.add_argument("--out", default=OUT, help="output folder (results/nose2 by default)")
    a = ap.parse_args(argv)
    des, od = load_design(a.design)
    geo = LY.layout(des, handle_od=od)
    out = a.out
    os.makedirs(out, exist_ok=True)
    step_ok = None
    if not a.no_step:
        try:
            asm = RC.build_assembly(geo)
            asm.save(os.path.join(out, "nose2_assembly.step"))
            step_ok = True
        except Exception as e:           # keep the drawing and the summary even if a solid fails
            step_ok = f"failed: {e}"
    png = os.path.join(out, "drawing_nose2.png")
    act = {"gimbal_sphere": "spherical-gap checkerboard actuator", "gimbal_radial": "pole-pair magnets in a radial gap",
           "gimbal_axial": "flat axial-gap checkerboard actuator", "coarse_fine": "coarse-fine stages"}.get(des["kind"], des["kind"])
    RC.drawing(geo, png, title=f"Rev J nose v2 (PROPOSED DESIGN): short-arm gimbal, \u00b1{geo['tip_travel_min_35_75_mm']:.1f} mm "
                              f"guaranteed over 35-75 deg, {act}, pen lift, Ø{geo['handle_od']:.0f} mm handle")
    component_csv(geo, png.replace(".png", ".csv"))
    front_end_figure(geo, os.path.join(out, "fig_nose2_front_end.png"))
    summary = {"evidence_status": "PROPOSED DESIGN (dimensioned concept); masses CALC; nothing built or measured",
               "geometry": {k: v for k, v in geo.items() if k != "components"}, "components": geo["components"], "step_export": step_ok}
    with open(os.path.join(out, "nose2_cad_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(geo["fit_checks"]), "mass", geo["mass_g"], "step:", step_ok)
    return geo


if __name__ == "__main__":
    main()
