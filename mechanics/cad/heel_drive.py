#!/usr/bin/env python3
"""Parametric CAD concept of study D's recommended heel drive in the Rev H pen (CadQuery 2.x).

Evidence status: PROPOSED DESIGN (dimensioned concept).  The heel geometry (contact radius, skid radius, spring travel,
roll tolerance) comes from drive/run_study.chosen_heel() and drive/geometry.py (CALC); the part list and positions from
drive/layout.parts() (the same list as results/drive/layout_parts.json); the rest of the pen from
results/revH/layout.json.  The wheel, its tyre and the steering fork are drawn tilted on the paper normal at 50 deg.
Fit checks are geometric only.  Nothing was built or measured.

Concept: a 2 mm wheel with an O-ring tyre in a slot at the bottom of a larger skid ring (contact radius 8.75 mm, ring
8.40 mm; Rev H 6.75 mm).  It is steered about the paper normal through its contact point (crown gear on the fork) and
driven about its axle (bevel 2:1); two Faulhaber 0620 B motors in the handle between the gimbal and the coils drive it
through transfer gears and two 0.8 mm shafts in a keel under the front sleeve.

Datums: origin at the ball tip, z along the pen axis toward the back, x in the tilt plane (positive away from the paper).
Outputs: results/cad/heel_drive_assembly.step, results/cad/heel_drive_summary.json, results/cad/drawing_heel_drive.png;
a copy of the drawing as results/drive/fig_cad_heel_drive.png with its CSV twin (the component table).
Run: python3 mechanics/cad/heel_drive.py [--no-step]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))

import numpy as np  # noqa: E402

from drive import geometry as DG, layout as LY  # noqa: E402
from drive.run_study import chosen_heel  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")
FIG = os.path.join(ROOT, "results", "drive")
REPLACED = ("skid_ring", "front_sleeve", "optical", "board_magnet", "board_keel")
COLORS = {"structure": (0.70, 0.72, 0.75), "grip": (0.35, 0.55, 0.85), "moving_nose": (0.95, 0.55, 0.15),
          "refill": (0.20, 0.20, 0.25), "actuator": (0.80, 0.20, 0.25), "mechanism": (0.55, 0.35, 0.75),
          "sensor": (0.15, 0.65, 0.45), "electronics": (0.20, 0.45, 0.30), "power": (0.95, 0.80, 0.20),
          "haptic": (0.50, 0.50, 0.50), "inertial": (0.30, 0.30, 0.35), "magnet": (0.80, 0.25, 0.60),
          "drive": (0.05, 0.60, 0.70)}
THETA = 50.0


def colour(c):
    """Group colour; the larger front sleeve keeps the grip colour (it is listed in group 'drive' for the explainer)."""
    return COLORS["grip"] if c["id"] == "drive_front_sleeve" else COLORS.get(c["group"], (0.6, 0.6, 0.6))


def geometry():
    """Rev H components minus the replaced ones, plus the new front sleeve and the drive parts."""
    rv = json.load(open(os.path.join(ROOT, "results", "revH", "layout.json")))
    h = chosen_heel()
    comps = [dict(c) for c in rv["components"] if c["id"] not in REPLACED]
    from opt.inertial import front_end as FE
    from opt.inertial.revh import RevH
    dm = FE.dims(h["R_skid_mm"], RevH(), FE.FrontRules())
    z_ring = h["front_end"]["ball_ahead_50_mm"]
    drive = LY.parts(h)                      # includes the larger front sleeve (drive_front_sleeve)
    for p in drive:
        p["offset"] = [float(v) for v in p.get("offset", [0.0, 0.0])]
    comps += drive
    geo = {k: v for k, v in rv.items() if k != "components"}
    geo.update({"components": comps, "heel": h, "ring_z": z_ring, "sleeve_bore_r": dm["sleeve_bore_r"],
                "skid_contact_radius": h["R_skid_mm"], "drive_contact_radius": h["R_d_mm"]})
    return geo


def _n():
    th = math.radians(THETA)
    return np.array([math.cos(th), 0.0, math.sin(th)]), np.array([math.sin(th), 0.0, -math.cos(th)])


def tilted_parts(geo):
    """The wheel (hub + O-ring tyre) and the steering fork, on the paper normal (CadQuery solids)."""
    import cadquery as cq
    h = geo["heel"]
    n, e1 = _n()
    r_e, R_d = h["r_e_mm"], h["R_d_mm"]
    contact = np.array([-R_d, 0.0, geo["ring_z"]])
    cw = contact + r_e * n
    tube = 0.3                                                   # O-ring cross-section radius (0.6 mm cord)
    hub = cq.Solid.makeCylinder(r_e - 2 * tube + 0.05, 0.8, cq.Vector(cw[0], -0.4, cw[2]), cq.Vector(0, 1, 0))
    tyre = cq.Solid.makeTorus(r_e - tube, tube, cq.Vector(*cw), cq.Vector(0, 1, 0))
    axle = cq.Solid.makeCylinder(0.15, 1.8, cq.Vector(cw[0], -0.9, cw[2]), cq.Vector(0, 1, 0))
    # fork: steering ring (crown) 2.0-3.0 mm above the contact on n, radius r_e + 0.5; two legs down to the axle
    base = contact + 2.0 * r_e * n
    ring = cq.Solid.makeCylinder(r_e + 0.5, 1.0, cq.Vector(*base), cq.Vector(*n)).cut(
        cq.Solid.makeCylinder(0.35, 1.0, cq.Vector(*base), cq.Vector(*n)))
    legs = []
    for y in (-0.65, 0.5):
        p0 = cw + 0.0 * n
        legs.append(cq.Solid.makeBox(0.6, 0.15, 1.0 * r_e + 0.1, cq.Vector(0, 0, 0)).rotate(
            cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 40.0).translate(cq.Vector(p0[0] - 0.3 * e1[0], y, p0[2] - 0.3 * e1[2])))
    fork = ring
    for l in legs:
        fork = fork.fuse(l)
    return {"drive_wheel": hub.fuse(tyre).fuse(axle), "drive_fork": fork}, contact, cw


def build_assembly(geo):
    import cadquery as cq
    from revH_pen import solid
    asm = cq.Assembly(name="heel_drive")
    tp, _, _ = tilted_parts(geo)
    for c in geo["components"]:
        col = colour(c)
        s = tp.get(c["id"])
        if s is None:
            s = solid(c)
            if c["id"] == "drive_skid_ring":
                # slot at the bottom (paper side) for the wheel: 3.2 mm wide
                h = c["z1"] - c["z0"]
                s = s.cut(cq.Workplane("XY").box(4.0, 3.2, h, centered=(True, True, False))
                          .translate((-c["d0"] / 2.0, 0.0, c["z0"])))
        asm.add(s, name=c["id"], color=cq.Color(*col))
    return asm


def drawing(geo, path_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle
    h = geo["heel"]
    n, e1 = _n()
    fig = plt.figure(figsize=(15.5, 9.4))
    ax = fig.add_axes([0.04, 0.47, 0.60, 0.45])
    axd = fig.add_axes([0.67, 0.47, 0.31, 0.45])

    def outline(a, c, alpha=0.85, lw=0.7):
        z0, z1 = c["z0"], c["z1"]
        col = colour(c)
        if c["id"] in ("drive_wheel", "drive_fork"):
            return
        if c["shape"] in ("cylinder", "cone"):
            r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
            ox = c.get("offset", [0.0, 0.0])[0]
            polys = [[(z0, ox - r0), (z1, ox - r1), (z1, ox + r1), (z0, ox + r0)]]
        elif c["shape"] == "tube":
            r0, r1, ri = c["d0"] / 2, c.get("d1", c["d0"]) / 2, c["d_in"] / 2
            polys = [[(z0, ri), (z1, ri), (z1, r1), (z0, r0)], [(z0, -ri), (z1, -ri), (z1, -r1), (z0, -r0)]]
            if c.get("open_deg"):
                polys = polys[1:]
        else:
            sx = c["size"][0]
            ox = c.get("offset", [0, 0])[0]
            polys = [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
        for pts in polys:
            a.add_patch(Polygon(pts, closed=True, facecolor=col, edgecolor="k", alpha=alpha, lw=lw))

    def tilted(a):
        r_e, R_d = h["r_e_mm"], h["R_d_mm"]
        contact = np.array([-R_d, 0.0, geo["ring_z"]])
        cw = contact + r_e * n
        a.add_patch(Circle((cw[2], cw[0]), r_e, facecolor=(0.15, 0.15, 0.15), edgecolor="k", lw=0.6, alpha=0.9))
        a.add_patch(Circle((cw[2], cw[0]), r_e - 0.6, facecolor=(0.8, 0.65, 0.3), edgecolor="k", lw=0.4))
        b0 = contact + 2.0 * r_e * n
        b1 = b0 + 1.0 * n
        w = (r_e + 0.5) * e1
        pts = [(p[2], p[0]) for p in (b0 - w, b0 + w, b1 + w, b1 - w)]
        a.add_patch(Polygon(pts, closed=True, facecolor=COLORS["drive"], edgecolor="k", lw=0.6, alpha=0.95))
        # steering axis (paper normal through the contact point)
        q0, q1 = contact - 0.5 * n, contact + 4.2 * n
        a.plot([q0[2], q1[2]], [q0[0], q1[0]], color="C3", lw=0.8, ls="-.")
        return contact

    for c in geo["components"]:
        if c["z0"] < 80.0:
            outline(ax, c, alpha=0.35 if c.get("optional") else 0.85)
            outline(axd, c, alpha=0.35 if c.get("optional") else 0.85, lw=0.5)
    for a in (ax, axd):
        contact = tilted(a)
    # nose envelope at its stop, behind the ring plane
    env = DG.envelope(h["R_skid_mm"])
    zz = geo["ring_z"] + env["s_mm"]
    m = (zz >= geo["ring_z"] - 1.0) & (zz <= geo["ring_z"] + 12.0)
    for a in (ax, axd):
        a.plot(zz[m], -env["r_mm"][m], color="C1", lw=1.0, ls="--")
        a.plot(zz[m], env["r_mm"][m], color="C1", lw=1.0, ls="--")
    axd.text(geo["ring_z"] + 7.5, -env["r_mm"][m].max() + 1.1, "nose envelope at its stop", color="C1", fontsize=7.5)
    # paper lines through the ball tip region and the drive contact at 35, 50, 75 deg
    for tdeg, ls_ in ((50.0, "-"), (35.0, ":"), (75.0, ":")):
        th = math.radians(tdeg)
        # the paper plane through the heel contact (at 35 and 75 deg drawn pivoting about it, an approximation);
        # its direction in the (z, x) drawing plane is perpendicular to n(t) = (cos t, sin t) in (x, z)
        nx, nz = math.cos(th), math.sin(th)
        dz, dx = nx, -nz
        L = np.array([-14.0, 30.0])
        for a in (ax, axd):
            a.plot(contact[2] + L * dz, contact[0] + L * dx, color="0.35", lw=0.9, ls=ls_)
    axd.text(geo["ring_z"] - 4.6, -12.2, "paper: solid 50°; dotted 35° and 75°\n(drawn pivoting about the heel contact)",
             fontsize=7, color="0.3")
    # annotations on the main view
    lbl = {"drive_motor": ("drive + steering motors (0620 B)", 60.0, -15.5), "drive_keel": ("shaft keel", 30.0, -12.6),
           "drive_transfer": ("transfer gears", 46.0, -15.5), "drive_front_sleeve": ("front sleeve (larger front)", 30.0, 12.3),
           "gimbal": ("gimbal", 45.0, 12.3), "carrier": ("moving nose", 28.0, 2.2), "coil_x+": ("coils", 77.0, 12.3),
           "drive_pod": ("heel pod + wheel", 9.0, -15.5)}
    for c in geo["components"]:
        if c["id"] in lbl:
            t, zt, xt = lbl[c["id"]]
            ax.text(zt, xt, t, ha="center", fontsize=7.5)
    for zf in geo["hand"]["finger_pads_z"]:
        ax.add_patch(Rectangle((zf - 2.5, geo["handle_od"] / 2 + 2.2), 5, 1.4, color=(0.9, 0.7, 0.6), alpha=0.9))
    ax.text(geo["hand"]["finger_pads_z"][1], geo["handle_od"] / 2 + 3.9, "finger pads", ha="center", fontsize=7.5)
    ax.set_xlim(-4, 80)
    ax.set_ylim(-geo["handle_od"] / 2 - 6, geo["handle_od"] / 2 + 5)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip (mm)")
    ax.set_ylabel("x (mm; paper side negative)")
    ax.set_title("Rev H front with the heel drive (side section in the tilt plane)", fontsize=10.5, loc="left")
    ax.grid(alpha=0.2)
    axd.set_xlim(geo["ring_z"] - 5.0, geo["ring_z"] + 13.0)
    axd.set_ylim(-12.5, -2.0)
    axd.set_aspect("equal")
    axd.set_title(f"Heel detail: wheel d {2 * h['r_e_mm']:.1f} mm, contact radius {h['R_d_mm']:.2f} mm "
                  f"(ring {h['R_skid_mm']:.2f})", fontsize=9, loc="left")
    axd.set_xlabel("z (mm)")
    axd.grid(alpha=0.2)
    axd.annotate("steering axis\n(paper normal)", xy=(contact[2] + 3.4 * n[2], contact[0] + 3.4 * n[0]),
                 xytext=(geo["ring_z"] + 3.8, -3.2), fontsize=7, color="C3",
                 arrowprops=dict(arrowstyle="-", color="C3", lw=0.6))
    # cross-sections
    secs = ((17.0, "keel, shafts, paper sensor"), (45.0, "shafts past the gimbal"), (60.0, "motors beside the rear arm"))
    for k, (zc, name) in enumerate(secs):
        axc = fig.add_axes([0.05 + 0.32 * k, 0.07, 0.25, 0.34])
        for c in geo["components"]:
            if not (c["z0"] <= zc <= c["z1"]):
                continue
            col = colour(c)
            ox, oy = c.get("offset", [0, 0])
            if c["shape"] in ("cylinder", "cone"):
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(Circle((ox, oy), r, facecolor=col, alpha=0.95, zorder=4,
                                     edgecolor="k" if c["group"] == "drive" else "none", lw=0.5))
            elif c["shape"] == "tube":
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(matplotlib.patches.Annulus((ox, oy), r, max(r - c["d_in"] / 2, 0.05), color=col, alpha=0.6))
            else:
                sx, sy = c["size"][0], c["size"][1]
                axc.add_patch(Rectangle((ox - sx / 2, oy - sy / 2), sx, sy, facecolor=col, alpha=0.55, zorder=3,
                                        edgecolor="k", lw=0.4))
        if zc > 46.5:
            rv = json.load(open(os.path.join(ROOT, "results", "revH", "layout.json")))
            sw = rv["magnet_stroke_mm"] / (rv["actuator_z"] - rv["pivot_z"]) * (zc - rv["pivot_z"])
            axc.add_patch(Circle((0, 0), 2.5 + sw, fill=False, ls="--", color="C1", lw=0.9))
            axc.text(0, 2.5 + sw + 0.4, "arm at its stop", ha="center", fontsize=6.5, color="C1")
        R = geo["handle_od"] / 2 + 1.5
        axc.set_xlim(-R, R); axc.set_ylim(-R, R); axc.set_aspect("equal")
        axc.set_title(f"section z {zc:.0f} mm ({name})", fontsize=8.5)
        axc.set_xlabel("x (mm; paper side negative)", fontsize=7)
        axc.tick_params(labelsize=7)
    handles = [Rectangle((0, 0), 1, 1, color=v) for v in COLORS.values()]
    fig.legend(handles, list(COLORS), loc="upper right", ncol=7, fontsize=7.5, frameon=False, bbox_to_anchor=(0.99, 0.995))
    fc = geo.get("fit_checks", {})
    fig.text(0.01, 0.002, "PROPOSED DESIGN (dimensioned concept; ASSUMPTION dimensions, CALC masses and clearances; nothing "
             f"built or measured).  Fit checks all pass: {fc.get('all_pass')}.  mechanics/cad/heel_drive.py", fontsize=7.5)
    fig.savefig(path_png, dpi=130, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    geo = geometry()
    h = geo["heel"]
    drive_parts = [c for c in geo["components"] if c["group"] == "drive"]
    geo["fit_checks"] = LY.fit_checks(h, drive_parts)
    os.makedirs(OUT, exist_ok=True)
    step_ok = None
    if not a.no_step:
        try:
            asm = build_assembly(geo)
            asm.save(os.path.join(OUT, "heel_drive_assembly.step"))
            step_ok = True
        except Exception as e:      # keep the drawing and summary even if a solid fails
            step_ok = f"failed: {e}"
    mass_added = sum(c.get("mass_g", 0.0) for c in drive_parts if c["id"] != "drive_front_sleeve") + \
        next(c for c in drive_parts if c["id"] == "drive_front_sleeve")["mass_g"] - LY.revh_sleeve_mass()
    summary = {"evidence_status": "PROPOSED DESIGN (dimensioned concept); masses and clearances CALC; nothing built or measured",
               "heel": h, "replaces_revH": list(REPLACED), "fit_checks": geo["fit_checks"],
               "drive_parts_mass_g": round(mass_added, 2),
               "note_mass": "new parts plus the larger front sleeve's increment over Rev H's (CALC, 1.3 g/cm3)",
               "components": geo["components"], "step_export": step_ok,
               "source": "drive/layout.py, drive/geometry.py, results/revH/layout.json"}
    with open(os.path.join(OUT, "heel_drive_summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    png = os.path.join(OUT, "drawing_heel_drive.png")
    drawing(geo, png)
    os.makedirs(FIG, exist_ok=True)
    shutil.copyfile(png, os.path.join(FIG, "fig_cad_heel_drive.png"))
    with open(os.path.join(FIG, "fig_cad_heel_drive.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm",
                    "moves_with", "optional", "part", "ledger", "mass_g"])
        for c in drive_parts:
            w.writerow([c["id"], c["label"], c["group"], c["shape"], c["z0"], c["z1"], c.get("d0", ""), c.get("d1", ""),
                        c.get("d_in", ""), c.get("size", ""), c.get("offset", ""), c["moves_with"], c["optional"], c["part"],
                        c["ledger"], c.get("mass_g", "")])
    print(json.dumps(geo["fit_checks"]), "step:", step_ok)


if __name__ == "__main__":
    main()
