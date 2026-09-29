#!/usr/bin/env python3
"""Parametric CAD concept of the Rev J rear end-cap (study K), CadQuery 2.x.

Evidence status: PROPOSED DESIGN (dimensioned concept).  Dimensions come from endcap/layout.py, which takes them from the
optimised design in results/endcap/endcap_study.json (endcap/optimise.py); part masses are CALC or ASSUMPTION.  The drawing
places the end-cap on the Rev H pen outline (results/revH/layout.json, read-only).  Fit checks are geometric only.
Nothing was built or measured.

Datums: origin at the ball centre, z along the pen axis toward the back, x in the tilt plane, mm.
Outputs (results/endcap/): endcap_<design>.step, drawing_endcap_<design>.png and its CSV twin (component table),
and drawing_endcap.png for the recommended design.
Run: python3 mechanics/cad/endcap.py [--design recommended|lrm|cmg] [--no-step]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
# This file shares its name with the study package endcap/: keep the repository root first on the path so that
# "import endcap" finds the package, and put this folder (for revH_pen.solid) last.
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != HERE]
sys.path.insert(0, ROOT)
sys.path.append(HERE)

OUT = os.path.join(ROOT, "results", "endcap")
COLORS = {"shell": (0.72, 0.74, 0.77), "slug": (0.30, 0.30, 0.35), "rotor": (0.30, 0.30, 0.35), "coil": (0.80, 0.45, 0.20),
          "magnet": (0.80, 0.25, 0.60), "gimbal": (0.55, 0.35, 0.75), "motor": (0.20, 0.45, 0.70), "flexure": (0.45, 0.60, 0.45),
          "board": (0.20, 0.45, 0.30), "bearing": (0.60, 0.60, 0.60), "drive": (0.15, 0.55, 0.60)}


def kind(c):
    i = c["id"]
    for k, key in (("slug", "slug"), ("rotor", "rotor"), ("coil", "coil"), ("magnet", "magnet"), ("gimbal_drive", "drive"),
                   ("gimbal", "gimbal"), ("spin_motor", "motor"), ("flexure", "flexure"), ("board", "board"), ("bearing", "bearing"),
                   ("shell", "shell")):
        if k in i:
            return key
    return "shell"


def parts_for(design):
    """Components of one design ('lrm' or 'cmg') from the study JSON (endcap/layout.py)."""
    from endcap import layout as LY
    res = json.load(open(os.path.join(OUT, "endcap_study.json")))
    rec = (res.get("recommendation") or {}).get("choice") or "lrm"
    name = rec if design == "recommended" else design
    d = res["designs"][name]
    parts = LY.lrm_parts(d) if d["class"] == "LRM2" else LY.cmg_parts(d)
    return name, d, parts


def build_step(parts, path):
    import cadquery as cq
    from revH_pen import solid
    asm = cq.Assembly(name="endcap")
    for c in parts:
        asm.add(solid(c), name=c["id"], color=cq.Color(*COLORS[kind(c)]))
    asm.save(path)


def _rotor_centre(parts, c):
    """z of the rotor centre that part c tilts about (the rotor with the same suffix)."""
    sfx = c["id"].split("_")[-1] if c["id"][-1].isdigit() else ""
    for r in parts:
        if r.get("moves_with") == "rotor" and (r["id"].endswith(sfx) if sfx else True):
            return 0.5 * (r["z0"] + r["z1"])
    return 0.5 * (c["z0"] + c["z1"])


def drawing(name, d, parts, path_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle, Circle, Annulus
    geo = json.load(open(os.path.join(ROOT, "results", "revH", "layout.json")))
    fig = plt.figure(figsize=(14.5, 8.0))
    ax = fig.add_axes([0.05, 0.44, 0.90, 0.48])
    # Rev H outline (handle parts, light) up to z 130 mm, the end-cap in colour
    for c in geo["components"]:
        if c.get("moves_with") in ("handle", "nose") and c["shape"] in ("tube", "cylinder") and c["z1"] <= 130.0 and not c.get("optional"):
            r = c.get("d0", 2) / 2
            ax.add_patch(Rectangle((c["z0"], -r), c["z1"] - c["z0"], 2 * r, facecolor=(0.93, 0.93, 0.93), edgecolor=(0.8, 0.8, 0.8), lw=0.5))
    ax.add_patch(Rectangle((101.0, -7.05), 29.0, 14.1, facecolor=(0.98, 0.9, 0.6), edgecolor=(0.8, 0.7, 0.3), lw=0.6, alpha=0.7))
    ax.text(115.5, 0.0, "Rev H cell (z 101-149.5):\nno room with the end-cap\n(open packaging issue)", fontsize=7, ha="center", va="center", color="0.3")

    def poly(c, dx=0.0, rot=0.0, fill=True, ls="-", zc=None):
        z0, z1 = c["z0"], c["z1"]
        col = COLORS[kind(c)]
        ox = c.get("offset", [0.0, 0.0])[0] + dx
        if c["shape"] in ("cylinder", "cone"):
            r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
            pts = [(z0, ox - r0), (z1, ox - r1), (z1, ox + r1), (z0, ox + r0)]
            polys = [pts]
        elif c["shape"] == "tube":
            r0, r1, ri = c["d0"] / 2, c.get("d1", c["d0"]) / 2, c["d_in"] / 2
            polys = [[(z0, ri), (z1, ri), (z1, r1), (z0, r0)], [(z0, -ri), (z1, -ri), (z1, -r1), (z0, -r0)]]
        else:
            sx = c["size"][0]
            polys = [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
        for pts in polys:
            if rot:
                zr = zc if zc is not None else 0.5 * (z0 + z1)
                pts = [(zr + (z - zr) * math.cos(rot) - x * math.sin(rot), (z - zr) * math.sin(rot) + x * math.cos(rot)) for z, x in pts]
            ax.add_patch(Polygon(pts, closed=True, facecolor=col if fill else "none", edgecolor="k" if fill else col, lw=0.7 if fill else 1.0,
                                 alpha=0.85 if fill else 0.9, ls=ls))

    # side view = section through the tilt plane (y = 0): parts that sit off that plane (the y-axis coils and magnets)
    # appear only in the cross-sections below
    def in_plane(c):
        return abs(c.get("offset", [0.0, 0.0])[1]) < 1e-9

    for c in parts:
        if in_plane(c):
            poly(c)
    if d["class"] == "LRM2":
        X = d["X"] * 1e3
        for c in parts:
            if c.get("moves_with") == "inertial_mass" and in_plane(c):
                for s in (X, -X):
                    poly(c, dx=s, fill=False, ls="--")
        ax.text(152.5, 13.8, f"slug moves +/-{X:.1f} mm (dashed)", ha="center", fontsize=8)
    else:
        dl = d["x"]["delta"]
        for c in parts:
            if c.get("moves_with") == "rotor" or "spin_motor" in c["id"] or "bearings" in c["id"]:
                for s in (dl, -dl):
                    poly(c, rot=s, fill=False, ls="--", zc=_rotor_centre(parts, c))
        ax.text(152.5, 13.8, f"rotor tilts +/-{math.degrees(dl):.0f} deg on its gimbals (dashed); gimbal rings drawn centred, they turn with it",
                ha="center", fontsize=8)
    ax.set_xlim(95, 180); ax.set_ylim(-16, 16); ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip (mm)"); ax.set_ylabel("x (mm)")
    ttl = {"LRM2": "End-cap: 2-axis tungsten reaction mass on flexures (tremor damping, cues)",
           "DG1": "End-cap: single-rotor double-gimbal CMG (torque pulses and nudges)"}.get(d["class"], f"End-cap: {d['class']} CMG")
    ax.set_title(ttl + f" - {d['mass_g']:.1f} g (CALC)", fontsize=11)
    ax.grid(alpha=0.2)
    # cross-sections: through the moving mass or rotor, and through the flexure plate or the gimbal drives
    moving = [c for c in parts if c.get("moves_with") in ("inertial_mass", "rotor")]
    z_a = 0.5 * (moving[0]["z0"] + moving[0]["z1"]) if moving else 152.5
    second = [c for c in parts if "flexure_rear" in c["id"] or "gimbal_drive" in c["id"]]
    z_b = 0.5 * (second[0]["z0"] + second[0]["z1"]) if second else 170.0
    zs = (z_a, z_b)
    for k, zc in enumerate(zs):
        axc = fig.add_axes([0.10 + 0.32 * k, 0.03, 0.26, 0.30])
        for c in parts:
            if not (c["z0"] <= zc <= c["z1"]):
                continue
            col = COLORS[kind(c)]
            ox, oy = c.get("offset", [0, 0])
            if c["shape"] in ("cylinder", "cone"):
                axc.add_patch(Circle((ox, oy), c["d0"] / 2, color=col, alpha=0.85))
            elif c["shape"] == "tube":
                axc.add_patch(Annulus((ox, oy), c["d0"] / 2, max(c["d0"] / 2 - c["d_in"] / 2, 0.05), color=col, alpha=0.85))
            else:
                sx, sy = c["size"][0], c["size"][1]
                axc.add_patch(Rectangle((ox - sx / 2, oy - sy / 2), sx, sy, color=col, alpha=0.9))
        axc.set_xlim(-14, 14); axc.set_ylim(-14, 14); axc.set_aspect("equal")
        axc.set_title(f"section z {zc:.1f} mm", fontsize=8); axc.tick_params(labelsize=7)
    kinds = [k for k in COLORS if any(kind(c) == k for c in parts)]
    handles = [Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in kinds]
    fig.legend(handles, kinds, loc="lower right", ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.97, 0.06), title="parts")
    fig.text(0.01, 0.985, "PROPOSED DESIGN (dimensioned concept; dimensions from endcap/optimise.py, part masses CALC/ASSUMPTION). Not built. "
             "Side view: section through the tilt plane (y = 0).", fontsize=7.5, va="top")
    fig.savefig(path_png, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="all", help="recommended | lrm | cmg | all")
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    todo = ("recommended", "lrm", "cmg") if a.design == "all" else (a.design,)
    for des in todo:
        name, d, parts = parts_for(des)
        tag = "" if des == "recommended" else f"_{name}"
        png = os.path.join(OUT, f"drawing_endcap{tag}.png")
        drawing(name, d, parts, png)
        with open(png.replace(".png", ".csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "label", "shape", "z0_mm", "z1_mm", "d0_mm", "d_in_mm", "size_mm", "offset_mm", "moves_with", "mass_g", "part", "ledger"])
            for c in parts:
                w.writerow([c["id"], c["label"], c["shape"], round(c["z0"], 2), round(c["z1"], 2), c.get("d0", ""), c.get("d_in", ""),
                            c.get("size", ""), c.get("offset", ""), c["moves_with"], round(c.get("mass_g", 0.0), 2), c["part"], c["ledger"]])
        if not a.no_step and des != "recommended":
            build_step(parts, os.path.join(OUT, f"endcap_{name}.step"))
        print(f"{des}: {name} {d['class']} {sum(c.get('mass_g', 0) for c in parts):.1f} g -> {png}")


if __name__ == "__main__":
    main()
