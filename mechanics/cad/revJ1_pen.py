#!/usr/bin/env python3
"""Parametric CAD concept of the Rev J.1 pen (CadQuery 2.x), built with Rev J's CAD code (mechanics/cad/revJ_pen.py,
imported, not copied) from results/revJ1/layout.json (written by python3 -m revj1.run).

Evidence status: PROPOSED DESIGN (dimensioned concept); masses CALC; nothing built or measured.  What differs from the
Rev J drawing comes from the layout: the thinner coil-plate back iron (parts behind it 0.87 mm forward), the heel motors
and gears 10 mm further back with the cue LRA in front of them, the graphite spreader in the shell wall, the shorter
end-cap with the 9 mm slug, and the clear front-sleeve window (recorded in the layout; drawn as part of the sleeve).
Outputs (results/revJ1/): revJ1_pen_assembly.step (end-cap fitted), revJ1_pen_assembly_no_endcap.step (--no-endcap),
drawing_revJ1_pen.png + .csv (component table), drawing_revJ1_pen_no_endcap.png + .csv, revJ1_cad_summary*.json.
Run: python3 mechanics/cad/revJ1_pen.py [--no-endcap] [--no-step]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))

import revJ_pen as RJ  # noqa: E402  (read-only reuse: select, build_assembly, drawing, component_csv)

OUT = os.path.join(ROOT, "results", "revJ1")


def load_layout(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    from revj1 import layout as LY
    return LY.public(LY.build())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-endcap", action="store_true")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--layout", default=os.path.join(OUT, "layout.json"))
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    geo = load_layout(a.layout)
    endcap = not a.no_endcap
    comps = RJ.select(geo, endcap)
    os.makedirs(a.out, exist_ok=True)
    tag = "revJ1_pen_assembly" + ("" if endcap else "_no_endcap")
    step_ok, failed = None, []
    if not a.no_step:
        try:
            asm, failed = RJ.build_assembly(geo, comps, tag)
            asm.save(os.path.join(a.out, f"{tag}.step"))
            step_ok = True
        except Exception as e:                                   # report, do not hide
            step_ok = f"failed: {e}"
    png = os.path.join(a.out, "drawing_revJ1_pen.png" if endcap else "drawing_revJ1_pen_no_endcap.png")
    L = geo["length_with_endcap"] if endcap else geo["length"]
    RJ.drawing(geo, comps, png, f"Rev J.1 pen (PROPOSED DESIGN): 75 um gimbal, thinner plate iron, graphite spreader, motors "
                                f"10 mm back, {'9 mm-slug end-cap fitted' if endcap else 'base pen'}; Ø{geo['handle_od']:.0f} × {L:.1f} mm")
    RJ.component_csv(comps, png.replace(".png", ".csv"))
    from stabpen import provenance
    summ = {"meta": provenance.metadata("PROPOSED DESIGN (dimensioned concept); masses CALC; nothing built or measured",
                                        extra={"script": "mechanics/cad/revJ1_pen.py", "doc": "docs/revJ1_design.md"}),
            "variant": "with end-cap" if endcap else "base pen", "step": step_ok, "step_parts_failed": failed,
            "geometry": {k: v for k, v in geo.items() if k not in ("components", "meta", "stabpen.provenance")},
            "n_components": len(comps)}
    summ["stabpen.provenance"] = summ["meta"]
    with open(os.path.join(a.out, "revJ1_cad_summary.json" if endcap else "revJ1_cad_summary_no_endcap.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(geo.get("fit_checks", {}).get("all_pass")), "step:", step_ok, "failed parts:", failed)
    return summ


if __name__ == "__main__":
    main()
