#!/usr/bin/env python3
"""Parametric CAD concept of study B's recommended balanced nib (B1): a two-axis translation nib on four titanium wires,
a moving-coil axial-gap checkerboard actuator, and the contact-driven counter-face at the refill's rear end (CadQuery).

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from bnib/layout.geometry(), which takes
the optimised design (bnib/optimise.py, bnib/build/opt_cache.json; else the hand-sized default).  Fit checks are
geometric only.  Nothing was built or measured.

Datums as mechanics/cad/revH_pen.py (its solid() and colours reused read-only): origin at the ball centre, z along the
pen axis toward the back, x in the tilt plane (away from the paper), mm.
Outputs (results/bnib/): bnib_assembly.step, bnib_cad_summary.json, drawing_bnib.png and its CSV twin drawing_bnib.csv.
Run: python3 mechanics/cad/bnib.py [--no-step]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))

OUT = os.path.join(ROOT, "results", "bnib")
COLORS = {"structure": (0.70, 0.72, 0.75), "moving_nib": (0.95, 0.55, 0.15), "refill": (0.20, 0.20, 0.25),
          "actuator": (0.80, 0.20, 0.25), "magnet": (0.80, 0.25, 0.60), "mechanism": (0.55, 0.35, 0.75),
          "sensor": (0.15, 0.65, 0.45), "balance": (0.20, 0.55, 0.85), "skid": (0.60, 0.60, 0.60)}


def design():
    import bnib  # noqa: F401
    from bnib import candidates as CD
    from bnib import interface as IF
    d, x = IF.recommended_design()
    ev = CD.evaluate(d, detail=False, fast=True)
    return d, ev, x


def build_assembly(geo):
    import cadquery as cq
    import revH_pen as RC
    asm = cq.Assembly(name="bnib_B1")
    for c in geo["components"]:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        asm.add(RC.solid(c), name=c["id"], color=cq.Color(*col))
    return asm


def drawing(geo, path_png, title):
    """Side section (x-z) of the nib with its travel, and an end view of the actuator (magnets, coil hole, wires)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig = plt.figure(figsize=(14.0, 6.2))
    ax = fig.add_axes([0.04, 0.12, 0.66, 0.76])
    for c in geo["components"]:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        z0, z1 = c["z0"], c["z1"]
        ox = c.get("offset", [0.0, 0.0])[0]
        if c["shape"] in ("cylinder", "cone"):
            r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
            ax.fill([z0, z1, z1, z0], [ox - r0, ox - r1, ox + r1, ox + r0], color=col, alpha=0.75, lw=0.5, ec="k")
        elif c["shape"] == "tube":
            ro, ri = c["d0"] / 2, c["d_in"] / 2
            for sgn in (1, -1):
                ax.fill([z0, z1, z1, z0], [ox + sgn * ri, ox + sgn * ri, ox + sgn * ro, ox + sgn * ro], color=col, alpha=0.75,
                        lw=0.5, ec="k")
        elif c["shape"] == "box":
            sx = c["size"][0]
            ax.add_patch(Rectangle((z0, ox - sx / 2), z1 - z0, sx, color=col, alpha=0.8, lw=0.5, ec="k"))
    # the shell bore and the travel envelope
    ax.plot([0, 80], [11, 11], "k--", lw=0.6)
    ax.plot([0, 80], [-11, -11], "k--", lw=0.6)
    ax.text(40, 11.3, "shell bore 22 mm (24 mm grip)", fontsize=8)
    t = geo["tip_travel_mm"]
    ax.annotate("", xy=(0, t), xytext=(0, -t), arrowprops=dict(arrowstyle="<->", color="C3"))
    ax.text(-6.5, 1.6, f"±{t:.2f} mm\nusable", color="C3", fontsize=8)
    ax.set_xlim(-8, 86)
    ax.set_ylim(-14, 14)
    ax.set_aspect("equal")
    ax.set_xlabel("z along the pen from the ball (mm)")
    ax.set_ylabel("x (mm)")
    ax.set_title(title, fontsize=10)
    # end view of the actuator
    bx = fig.add_axes([0.73, 0.14, 0.25, 0.72])
    for c in geo["components"]:
        if c["id"].startswith("bnib_magnet_"):
            w = c["size"][0]
            ox, oy = c["offset"]
            bx.add_patch(Rectangle((ox - w / 2, oy - w / 2), w, w, color=COLORS["magnet"], alpha=0.8, ec="k", lw=0.5))
            bx.text(ox, oy, "N" if ox * oy > 0 else "S", ha="center", va="center", fontsize=9, color="w")
        if c["id"].startswith("bnib_wire_"):
            ox, oy = c["offset"]
            bx.add_patch(Circle((ox, oy), 0.35, color=COLORS["mechanism"]))
    bx.add_patch(Circle((0, 0), geo["r_hole"], fill=False, ls="--", ec="k"))
    bx.add_patch(Circle((0, 0), 1.6, color=COLORS["moving_nib"], alpha=0.8))
    bx.add_patch(Circle((0, 0), 1.175, color=COLORS["refill"]))
    bx.text(0, -geo["r_hole"] - 1.2, "hole clears the carrier\nat the stop", ha="center", fontsize=7)
    bx.add_patch(Circle((0, 0), 11.0, fill=False, ec="k", lw=0.8))
    bx.set_xlim(-12, 12)
    bx.set_ylim(-12, 12)
    bx.set_aspect("equal")
    bx.set_title("end view: 4 poles, central hole, carrier + refill,\n4 wires (behind the actuator)", fontsize=9)
    fig.text(0.04, 0.02, "PROPOSED DESIGN (study B). Moving coils + carrier + refill translate on four wires; magnets, plates "
                         "and keeper are fixed. The counter-face (blue) behind the refill end balances the paper's push. "
                         "Nothing built or measured.", fontsize=8)
    fig.savefig(path_png, dpi=150)
    plt.close(fig)


def component_csv(geo, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm",
                    "moves_with", "mass_g", "part", "ledger"])
        for c in geo["components"]:
            w.writerow([c["id"], c["label"], c["group"], c["shape"], round(c["z0"], 3), round(c["z1"], 3), c.get("d0", ""),
                        c.get("d1", ""), c.get("d_in", ""), c.get("size", ""), c.get("offset", ""), c["moves_with"],
                        round(c.get("mass_g", 0.0), 4), c["part"], c["ledger"]])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    from bnib import layout as LY
    d, ev, x = design()
    geo = LY.geometry(d, ev)
    os.makedirs(a.out, exist_ok=True)
    step_ok = None
    if not a.no_step:
        try:
            asm = build_assembly(geo)
            asm.save(os.path.join(a.out, "bnib_assembly.step"))
            step_ok = True
        except Exception as e:                       # keep the drawing and summary if a solid fails
            step_ok = f"failed: {e}"
    png = os.path.join(a.out, "drawing_bnib.png")
    drawing(geo, png, f"B1 (PROPOSED DESIGN): ±{geo['tip_travel_mm']:.2f} mm on four {d.wire.d * 1e3:.3f} mm Ti wires, "
                      f"moving coils, counter-face (blue); 24 mm pen")
    component_csv(geo, png.replace(".png", ".csv"))
    summary = {"evidence_status": "PROPOSED DESIGN (dimensioned concept); masses CALC or ASSUMPTION; nothing built or measured",
               "design_point": x, "geometry": {k: v for k, v in geo.items() if k != "components"}, "components": geo["components"],
               "step_export": step_ok, "script": "mechanics/cad/bnib.py"}
    with open(os.path.join(a.out, "bnib_cad_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print(json.dumps(geo["fit_checks"], default=float), "mass", round(geo["mass_g"], 2), "step:", step_ok)
    return geo


if __name__ == "__main__":
    main()
