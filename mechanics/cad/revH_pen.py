#!/usr/bin/env python3
"""Parametric CAD concept of the Rev H pen: Ø22 mm handle, active nose on a 2-axis flexure gimbal, optional rear-cap
inertial module (CadQuery 2.x).

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from opt/inertial/geometry.layout(), which
derives it from the design variables of opt/inertial/revh.RevH (the adjoint-optimised actuator, the tracker-driven travel)
and catalogue parts with ledger ids.  Fit checks are geometric only.  Nothing was built or measured.

Datums: origin at the ball centre, z along the pen axis from the tip toward the back, x in the tilt plane, mm.
Outputs (results/cad/): revH_pen_assembly.step (nominal nose), revH_pen_summary.json (components, masses, fit checks),
drawing_revH_pen.png (side section with the nose at +/- full travel, hand zones, cross-sections at the gimbal and the coils).
Also written: results/opt/fig_in_cad.png and its CSV twin (the component table).
Run: python3 mechanics/cad/revH_pen.py [--addon] [--no-step]
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

from opt.inertial import geometry as GE  # noqa: E402
from opt.inertial import revh as RH  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")
FIG = os.path.join(ROOT, "results", "opt")
COLORS = {"structure": (0.70, 0.72, 0.75), "grip": (0.35, 0.55, 0.85), "moving_nose": (0.95, 0.55, 0.15),
          "refill": (0.20, 0.20, 0.25), "actuator": (0.80, 0.20, 0.25), "mechanism": (0.55, 0.35, 0.75),
          "sensor": (0.15, 0.65, 0.45), "electronics": (0.20, 0.45, 0.30), "power": (0.95, 0.80, 0.20),
          "haptic": (0.50, 0.50, 0.50), "inertial": (0.30, 0.30, 0.35)}


def default_addon():
    """The rear-cap reaction-mass module of the recommendation (opt/inertial/addon.rm_rear with the chosen size)."""
    return {"z0": 151.0, "z1": 169.0, "frame_d": 20.0, "mz0": 153.0, "mz1": 167.0, "mass_d": 10.0, "stroke": 2.5, "m_g": 19.8}


def solid(c):
    import cadquery as cq
    z0, z1 = c["z0"], c["z1"]
    h = max(z1 - z0, 0.05)
    sh = c["shape"]
    if sh == "cylinder":
        r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
        if abs(r0 - r1) < 1e-6:
            s = cq.Workplane("XY").circle(r0).extrude(h)
        else:
            s = cq.Workplane("XY").add(cq.Solid.makeCone(r0, r1, h))
    elif sh == "cone":
        s = cq.Workplane("XY").add(cq.Solid.makeCone(c["d0"] / 2, c.get("d1", c["d0"]) / 2, h))
    elif sh == "tube":
        ro0, ro1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
        ri = c["d_in"] / 2
        outer = cq.Solid.makeCone(ro0, ro1, h) if abs(ro0 - ro1) > 1e-6 else cq.Solid.makeCylinder(ro0, h)
        inner = cq.Solid.makeCylinder(ri, h)
        s = cq.Workplane("XY").add(outer.cut(inner))
    elif sh == "box":
        sx, sy, sz = c["size"]
        s = cq.Workplane("XY").box(sx, sy, h, centered=(True, True, False))
    else:
        raise ValueError(sh)
    ox, oy = c.get("offset", [0.0, 0.0])
    return s.translate((ox, oy, z0))


def build_assembly(geo):
    import cadquery as cq
    asm = cq.Assembly(name="revH_pen")
    for c in geo["components"]:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        asm.add(solid(c), name=c["id"], color=cq.Color(*col))
    return asm


def drawing(geo, path_png, title="Rev H pen: active nose (architecture B) with optional rear-cap inertial module"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    fig = plt.figure(figsize=(15.5, 7.2))
    ax = fig.add_axes([0.04, 0.34, 0.93, 0.56])
    X = geo["tip_travel_mm"]
    zp = geo["pivot_z"]

    def outline(c, dx=0.0, alpha=0.85, ls="-", lw=0.8, fill=True):
        z0, z1 = c["z0"], c["z1"]
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        if c["shape"] in ("cylinder", "cone"):
            r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
            pts = [(z0, -r0), (z1, -r1), (z1, r1), (z0, r0)]
            polys = [pts]
        elif c["shape"] == "tube":
            r0, r1, ri = c["d0"] / 2, c.get("d1", c["d0"]) / 2, c["d_in"] / 2
            polys = [[(z0, ri), (z1, ri), (z1, r1), (z0, r0)], [(z0, -ri), (z1, -ri), (z1, -r1), (z0, -r0)]]
        else:
            sx = c["size"][0]
            ox = c.get("offset", [0, 0])[0]
            polys = [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
        for pts in polys:
            if dx != 0.0 and c.get("moves_with") == "nose":
                # rotate about the gimbal by the angle that moves the tip by dx (small angle): x += (z - zp) * (-dx / zp)
                pts = [(z, x + (zp - z) * dx / zp) for z, x in pts]
            ax.add_patch(Polygon(pts, closed=True, facecolor=col if fill else "none", edgecolor="k" if fill else col,
                                 alpha=alpha, lw=lw, ls=ls))

    for c in geo["components"]:
        outline(c, alpha=0.35 if c.get("optional") else 0.85)
    for dx in (X, -X):
        for c in geo["components"]:
            if c.get("moves_with") == "nose":
                outline(c, dx=dx, fill=False, ls="--", lw=0.9)
    # paper line at the tilt through the ball and the skid contact
    th = math.radians(geo["tilt_deg"])
    ax.plot([-6, 20], [math.tan(th) * 6 * 0 - 0.35, -0.35], color="none")
    # hand zones
    for zf in geo["hand"]["finger_pads_z"]:
        ax.add_patch(Rectangle((zf - 2.5, geo["handle_od"] / 2 + 0.5), 5, 2.0, color=(0.9, 0.7, 0.6), alpha=0.9))
    ax.add_patch(Rectangle((geo["hand"]["web_z"] - 6, geo["handle_od"] / 2 + 0.5), 12, 2.0, color=(0.85, 0.6, 0.5), alpha=0.9))
    ax.text(geo["hand"]["finger_pads_z"][1], geo["handle_od"] / 2 + 3.4, "finger pads", ha="center", fontsize=8)
    ax.text(geo["hand"]["web_z"], geo["handle_od"] / 2 + 3.4, "thumb-index web", ha="center", fontsize=8)
    ax.annotate("", xy=(0, X), xytext=(0, -X), arrowprops=dict(arrowstyle="<->", color="C1"))
    ax.text(1.5, X + 0.6, f"tip travel ±{X:.1f} mm", color="C1", fontsize=8)
    ax.axvline(zp, color="C4", lw=0.6, ls=":")
    ax.text(zp, -geo["handle_od"] / 2 - 3.5, f"gimbal z {zp:.0f}", color="C4", ha="center", fontsize=8)
    ax.axvline(geo["actuator_z"], color="C3", lw=0.6, ls=":")
    ax.text(geo["actuator_z"], -geo["handle_od"] / 2 - 3.5, f"magnets/coils z {geo['actuator_z']:.0f}", color="C3", ha="center", fontsize=8)
    labels = {"skid_ring": "skid ring", "front_sleeve": "fixed front sleeve (grip)", "carrier": "moving nose", "gimbal": "gimbal",
              "arm": "rear arm", "coil_x+": "coils", "pcb": "board + IMU", "battery": "Li-ion cell", "rm_mass": "tungsten reaction mass"}
    for c in geo["components"]:
        if c["id"] in labels:
            zc = 0.5 * (c["z0"] + c["z1"])
            ax.text(zc, -geo["handle_od"] / 2 - 7.0 if c["id"] not in ("carrier", "arm") else 5.5, labels[c["id"]], ha="center",
                    fontsize=7.5, rotation=0)
    ax.set_xlim(-8, geo["length"] + 4)
    ax.set_ylim(-geo["handle_od"] / 2 - 9, geo["handle_od"] / 2 + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip (mm)")
    ax.set_ylabel("x (mm)")
    ax.set_title(title, fontsize=11)
    ax.grid(alpha=0.2)
    # cross-sections
    for k, (zc, name) in enumerate(((zp, "at the gimbal"), (geo["actuator_z"], "at the magnets and coils"), (125.0, "at the cell"))):
        axc = fig.add_axes([0.08 + 0.3 * k, 0.03, 0.22, 0.26])
        for c in geo["components"]:
            if not (c["z0"] <= zc <= c["z1"]):
                continue
            col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
            ox, oy = c.get("offset", [0, 0])
            if c["shape"] in ("cylinder", "cone"):
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(matplotlib.patches.Circle((ox, oy), r, color=col, alpha=0.85))
            elif c["shape"] == "tube":
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(matplotlib.patches.Annulus((ox, oy), r, r - c["d_in"] / 2 if False else max(r - c["d_in"] / 2, 0.05),
                                                         color=col, alpha=0.85))
            else:
                sx, sy = c["size"][0], c["size"][1]
                axc.add_patch(Rectangle((ox - sx / 2, oy - sy / 2), sx, sy, color=col, alpha=0.9))
        R = geo["handle_od"] / 2 + 1
        axc.set_xlim(-R, R); axc.set_ylim(-R, R); axc.set_aspect("equal")
        axc.set_title(f"section z {zc:.0f} mm ({name})", fontsize=8)
        axc.tick_params(labelsize=7)
    handles = [Rectangle((0, 0), 1, 1, color=v) for v in COLORS.values()]
    fig.legend(handles, list(COLORS), loc="upper right", ncol=6, fontsize=7.5, frameon=False, bbox_to_anchor=(0.98, 0.99))
    fig.text(0.01, 0.005, "PROPOSED DESIGN (dimensioned concept; ASSUMPTION dimensions, CALC masses). Dashed: moving nose at ±full travel.",
             fontsize=7.5)
    fig.savefig(path_png, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addon", action="store_true", help="include the rear-cap reaction-mass module")
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    d = RH.RevH()
    addon = default_addon() if a.addon else None
    geo = GE.layout(d, addon=addon)
    os.makedirs(OUT, exist_ok=True)
    tag = "revH_pen" + ("_addon" if a.addon else "")
    summary = {"evidence_status": "PROPOSED DESIGN (dimensioned concept); masses CALC; nothing built or measured",
               "design": RH.describe(d), "geometry": {k: v for k, v in geo.items() if k != "components"},
               "components": geo["components"]}
    step_ok = None
    if not a.no_step:
        try:
            asm = build_assembly(geo)
            asm.save(os.path.join(OUT, f"{tag}_assembly.step"))
            step_ok = True
        except Exception as e:     # keep the drawing and summary even if a solid fails
            step_ok = f"failed: {e}"
    summary["step_export"] = step_ok
    with open(os.path.join(OUT, f"{tag}_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    png = os.path.join(OUT, f"drawing_{tag}.png")
    drawing(geo, png)
    if not a.addon or True:
        import shutil
        figp = os.path.join(FIG, "fig_in_cad" + ("_addon" if a.addon else "") + ".png")
        shutil.copyfile(png, figp)
        with open(figp.replace(".png", ".csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm", "moves_with",
                        "optional", "part", "ledger"])
            for c in geo["components"]:
                w.writerow([c["id"], c["label"], c["group"], c["shape"], c["z0"], c["z1"], c.get("d0", ""), c.get("d1", ""),
                            c.get("d_in", ""), c.get("size", ""), c.get("offset", ""), c["moves_with"], c["optional"], c["part"], c["ledger"]])
    print(json.dumps(geo["fit_checks"]), "step:", step_ok)


if __name__ == "__main__":
    main()
