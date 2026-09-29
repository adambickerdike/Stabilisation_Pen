#!/usr/bin/env python3
"""Parametric CAD concept of study W's whole-pen collar (the review's option B, V2 load path), CadQuery 2.x.

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from results/wholepen/layout_parts.json
(wholepen/explain.py, from wholepen/calc.py's collar geometry and mass budget); masses are CALC or ASSUMPTION.
Nothing was built or measured.  The fit check is geometric only: the inner pen's swept envelope at the full swing
against the sleeve's bore, and the tail's swing behind the web.

Datums: origin at the ball centre, z along the pen axis toward the back, x in the tilt plane, mm.
Outputs (results/wholepen/cad/): wholepen_collar.step, drawing_wholepen_collar.png and its CSV twin (component table
with the fit checks).
Run: python3 mechanics/cad/wholepen.py [--no-step]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "results", "wholepen", "layout_parts.json")
OUT = os.path.join(ROOT, "results", "wholepen", "cad")


def fit_checks(lp):
    comp = {c["id"]: c for c in lp["components"]}
    geo = lp["meta"]["collar_geometry"]
    sleeve, barrel, piv = comp["collar_sleeve"], comp["inner_barrel"], comp["collar_pivot"]
    zp = 0.5 * (piv["z0"] + piv["z1"])
    phi = math.radians(geo["swing_deg"])
    bore = sleeve["d_in"] / 2
    rb = barrel["d0"] / 2
    out = []
    for z in (sleeve["z0"], min(sleeve["z1"], barrel["z1"])):
        # barrel surface at z, swung by phi about the pivot: its offset from the axis grows as |z - zp| sin(phi)
        off = abs(z - zp) * math.sin(phi) + rb * math.cos(phi)
        out.append({"check": f"swung inner pen inside the sleeve bore at z {z:.1f} mm", "margin_mm": round(bore - off, 3),
                    "pass": bore - off >= 0.0})
    if "collar_coil_plate" in comp:
        gap = comp["collar_coil_plate"]["z0"] - (barrel["z1"] + rb * math.sin(phi))
        out.append({"check": "end-face magnets to coil plate, axial gap at full swing", "margin_mm": round(gap, 3), "pass": gap >= 0.3})
    return out


def build_step(lp, path):
    import cadquery as cq
    asm = cq.Assembly(name="wholepen_collar")
    for c in lp["components"]:
        if c.get("group") == "gyro_tail":
            continue
        z0, z1 = c["z0"], c["z1"]
        L = max(z1 - z0, 0.2)
        off = c.get("offset", [0.0, 0.0])
        if c["shape"] == "tube":
            s = cq.Workplane("XY").circle(c["d0"] / 2).circle(c.get("d_in", 0.0) / 2 or 1e-3).extrude(L)
        elif c["shape"] == "cylinder":
            s = cq.Workplane("XY").circle(c["d0"] / 2).extrude(L)
        else:
            sx, sy, _ = c["size"]
            s = cq.Workplane("XY").rect(sx, sy).extrude(L)
        s = s.translate((off[0], off[1], z0))
        col = (0.35, 0.65, 0.45) if c["group"] == "collar" else (0.45, 0.60, 0.85)
        asm.add(s, name=c["id"], color=cq.Color(*col))
    asm.save(path)
    return path


def drawing(lp, path_png, checks):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(11, 3.2))
    comp = {c["id"]: c for c in lp["components"]}
    geo = lp["meta"]["collar_geometry"]
    piv = comp["collar_pivot"]
    zp = 0.5 * (piv["z0"] + piv["z1"])
    phi = math.radians(geo["swing_deg"])
    for c in lp["components"]:
        if c.get("group") == "gyro_tail":
            continue
        z0, z1 = c["z0"], c["z1"]
        d = c.get("d0") or (c.get("size") or [2, 2, 2])[0]
        off = (c.get("offset") or [0.0, 0.0])[0]
        col = "#1baf7a" if c["group"] == "collar" else "#2a78d6"
        ax.add_patch(Rectangle((z0, off - d / 2), z1 - z0, d, fill=False, edgecolor=col, linewidth=1.0))
        if c["shape"] == "tube" and c.get("d_in"):
            ax.add_patch(Rectangle((z0, off - c["d_in"] / 2), z1 - z0, c["d_in"], fill=False, edgecolor=col, linewidth=0.5, linestyle=":"))
    b = comp["inner_barrel"]
    for sgn in (1, -1):
        zz = [b["z0"], b["z1"]]
        ax.plot(zz, [sgn * (0) + (z - zp) * math.tan(sgn * phi) for z in zz], color="#2a78d6", linewidth=0.6, alpha=0.5)
    ax.plot([zp], [0], "ko", markersize=4)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball (mm)")
    ax.set_ylabel("x (mm)")
    ax.set_title("Whole-pen collar (PROPOSED DESIGN): green = held collar, blue = swinging inner pen; thin lines = the axis at full swing",
                 fontsize=9, loc="left")
    fig.text(0.01, -0.02, "PROPOSED DESIGN, dimensions from results/wholepen/layout_parts.json (CALC); fit: "
             + "; ".join(f"{c['check']}: {c['margin_mm']} mm" for c in checks), fontsize=6.5, color="#52514e")
    fig.tight_layout()
    fig.savefig(path_png, dpi=150, bbox_inches="tight")
    with open(path_png[:-4] + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d_in_mm", "mass_g", "part", "ledger"])
        for c in lp["components"]:
            w.writerow([c["id"], c["group"], c["shape"], c["z0"], c["z1"], c.get("d0", ""), c.get("d_in", ""), c.get("mass_g", ""),
                        c.get("part", ""), c.get("ledger", "")])
        for ch in checks:
            w.writerow([ch["check"], "fit", "", "", "", "", "", "", ch["margin_mm"], "pass" if ch["pass"] else "FAIL"])
    return path_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    lp = json.load(open(SRC))
    os.makedirs(OUT, exist_ok=True)
    checks = fit_checks(lp)
    print(drawing(lp, os.path.join(OUT, "drawing_wholepen_collar.png"), checks))
    if not a.no_step:
        print(build_step(lp, os.path.join(OUT, "wholepen_collar.step")))
    for c in checks:
        print(c)


if __name__ == "__main__":
    main()
