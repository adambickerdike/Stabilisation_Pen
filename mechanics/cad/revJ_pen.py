#!/usr/bin/env python3
"""Parametric CAD concept of the integrated Rev J pen (CadQuery 2.x): the C1S nose (study N), the steered and driven heel
wheel (study D) repacked, the detachable reaction-mass end-cap (study K), and the Rev J packaging (revj/packaging.py).

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from results/revJ/layout.json (written by
python3 -m revj.run; rebuilt here if missing), which derives it from the round-1 designs and the integration's closure
(CALC) or ASSUMPTION values.  Fit checks are geometric only.  Nothing was built or measured.

Datums: origin at the ball tip (50 deg, nose centred), z along the pen axis toward the back, x in the tilt plane (positive
away from the paper), y lateral, mm.  The heel wheel and its steering crown are drawn tilted on the 50 deg paper normal.
Outputs (results/revJ/):
  revJ_pen_assembly.step             the pen with the end-cap (the rear cap removed)
  revJ_pen_assembly_no_endcap.step   the base pen (--no-endcap)
  drawing_revJ_pen.png + drawing_revJ_pen.csv   side section with the nose at +-travel, hand zones, paper lines, six
                                     cross-sections; the CSV twin is the component table
  revJ_cad_summary.json              geometry, fit checks, STEP status (stabpen.provenance)
Run: python3 mechanics/cad/revJ_pen.py [--no-endcap] [--no-step] [--layout results/revJ/layout.json]
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

import numpy as np  # noqa: E402

import revH_pen as RC  # noqa: E402  (read-only reuse: solid())

OUT = os.path.join(ROOT, "results", "revJ")
COLORS = dict(RC.COLORS)
COLORS.update({"skid": (0.15, 0.17, 0.20), "drive": (0.05, 0.60, 0.45), "inertial": (0.30, 0.30, 0.35)})
TILT = 50.0


def load_layout(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    from revj import packaging as PK
    return PK.public(PK.build())


def select(geo: dict, endcap: bool) -> list:
    out = []
    for c in geo["components"]:
        if endcap and c.get("replaced_by_endcap"):
            continue
        if not endcap and c.get("group") == "inertial":
            continue
        out.append(c)
    return out


# --------------------------------------------------------------------------------------------------- solids
def _normal():
    th = math.radians(TILT)
    return np.array([math.cos(th), 0.0, math.sin(th)])


def tilted_heel(geo: dict):
    """The wheel (hub + O-ring tyre + axle) and the steering fork (crown ring on the paper normal + two legs)."""
    import cadquery as cq
    n = _normal()
    R_d = geo["heel_contact_radius"]
    z_ring = geo["ball_protrusion_mm"]
    contact = np.array([-R_d, 0.0, z_ring])
    r_e, tube = 1.0, 0.3
    cw = contact + r_e * n
    hub = cq.Solid.makeCylinder(r_e - 2 * tube + 0.05, 0.8, cq.Vector(cw[0], -0.4, cw[2]), cq.Vector(0, 1, 0))
    tyre = cq.Solid.makeTorus(r_e - tube, tube, cq.Vector(*cw), cq.Vector(0, 1, 0))
    axle = cq.Solid.makeCylinder(0.15, 1.8, cq.Vector(cw[0], -0.9, cw[2]), cq.Vector(0, 1, 0))
    base = contact + 2.0 * r_e * n
    ring = cq.Solid.makeCylinder(r_e + 0.5, 1.0, cq.Vector(*base), cq.Vector(*n)).cut(
        cq.Solid.makeCylinder(0.35, 1.0, cq.Vector(*base), cq.Vector(*n)))
    fork = ring
    for y in (-0.72, 0.57):
        leg = cq.Solid.makeBox(0.5, 0.15, 1.1, cq.Vector(cw[0] - 0.25, y, cw[2] - 0.2))
        fork = fork.fuse(leg)
    return {"drive_wheel": cq.Workplane("XY").add(hub.fuse(tyre).fuse(axle)), "drive_fork": cq.Workplane("XY").add(fork)}


def part_solid(c: dict, geo: dict, heel: dict):
    import cadquery as cq
    if c["id"] in heel:
        return heel[c["id"]]
    s = RC.solid(c)
    cid = c["id"]
    if cid == "skid_ring":                                   # wheel slot at the bottom (paper side)
        h = c["z1"] - c["z0"]
        s = s.cut(cq.Workplane("XY").box(5.0, c.get("notch", {}).get("wheel_slot_width_mm", 3.2), h, centered=(True, True, False))
                  .translate((-c["d0"] / 2.0, 0.0, c["z0"])))
    if cid == "front_sleeve" and c.get("open_deg_front"):     # the ring's C opening continued into the sleeve
        L = c["open_deg_front"]["length_mm"]
        half = math.radians(c["open_deg_front"]["deg"]) / 2
        Rw = c["d1"]
        pts = [(0.0, 0.0)] + [(Rw * math.cos(-half + 2 * half * k / 8), Rw * math.sin(-half + 2 * half * k / 8)) for k in range(9)]
        s = s.cut(cq.Workplane("XY").polyline(pts).close().extrude(L).translate((0, 0, c["z0"])))
    if cid == "magnet_cap":                                   # flat at the bottom for the shafts
        r_f = c["notch"]["flat_at_bottom_radius_mm"]
        s = s.cut(cq.Workplane("XY").box(10.0, 30.0, c["z1"] - c["z0"], centered=(False, True, False))
                  .translate((-r_f - 10.0, 0.0, c["z0"])))
    if cid in ("coil_plate", "gimbal"):                       # notch at the bottom rim for the shafts
        r_n = c["notch"]["bottom_rim_radius_mm"]
        s = s.cut(cq.Workplane("XY").box(3.0, 4.2, c["z1"] - c["z0"], centered=(False, True, False))
                  .translate((-r_n - 3.0, 0.0, c["z0"])))
    if cid in ("front_sleeve", "shell"):                      # grooves for the two shafts (PTFE liners d 1.0)
        for sh in [x for x in geo["components"] if x["id"].startswith("drive_shaft")]:
            z0, z1 = max(c["z0"], sh["z0"]), min(c["z1"], sh["z1"])
            if z1 > z0:
                s = s.cut(cq.Workplane("XY").circle(0.5).extrude(z1 - z0).translate((sh["offset"][0], sh["offset"][1], z0)))
    return s


def build_assembly(geo: dict, comps: list, name: str):
    import cadquery as cq
    asm = cq.Assembly(name=name)
    heel = tilted_heel(geo)
    failed = []
    for c in comps:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        try:
            asm.add(part_solid(c, geo, heel), name=c["id"], color=cq.Color(*col))
        except Exception as e:                                # keep going; report the part
            failed.append(f"{c['id']}: {e}")
    return asm, failed


# --------------------------------------------------------------------------------------------------- drawing
def drawing(geo: dict, comps: list, path_png: str, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Annulus, Circle, Polygon, Rectangle
    fig = plt.figure(figsize=(16.5, 9.2))
    ax = fig.add_axes([0.035, 0.42, 0.95, 0.5])
    X = geo["tip_travel_mm"]
    zp = geo["pivot_z"]

    def outline(c, dx=0.0, alpha=0.85, ls="-", lw=0.7, fill=True):
        z0, z1 = c["z0"], c["z1"]
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        ox = c.get("offset", [0.0, 0.0])[0]
        if c["shape"] in ("cylinder", "cone"):
            r0, r1 = c["d0"] / 2, c.get("d1", c["d0"]) / 2
            polys = [[(z0, ox - r0), (z1, ox - r1), (z1, ox + r1), (z0, ox + r0)]]
        elif c["shape"] == "tube":
            r0, r1, ri = c["d0"] / 2, c.get("d1", c["d0"]) / 2, c["d_in"] / 2
            polys = [[(z0, ri), (z1, ri), (z1, r1), (z0, r0)], [(z0, -ri), (z1, -ri), (z1, -r1), (z0, -r0)]]
            if c.get("open_deg"):
                polys = polys[1:]
        else:
            sx = c["size"][0]
            polys = [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
        for pts in polys:
            if dx != 0.0 and c.get("moves_with") == "nose":
                pts = [(z, x + (zp - z) * dx / zp) for z, x in pts]
            ax.add_patch(Polygon(pts, closed=True, facecolor=col if fill else "none", edgecolor="k" if fill else col,
                                 alpha=alpha, lw=lw, ls=ls))

    for c in comps:
        outline(c, alpha=0.35 if c.get("optional") else 0.85)
    for dx in (X, -X):
        for c in comps:
            if c.get("moves_with") == "nose" and c["id"] not in ("refill", "ball"):
                outline(c, dx=dx, fill=False, ls="--", lw=0.8)
    zr, rr = geo["ball_protrusion_mm"], geo["skid_contact_radius"]
    for tdeg, lsty in ((50.0, "-"), (35.0, ":")):
        th = math.radians(tdeg)
        zz = [zr - 2.0, zr + 6.0]
        ax.plot(zz, [-rr - (z - zr) * math.tan(th) for z in zz], color="0.35", lw=0.9, ls=lsty)
        ax.text(zz[1] + 0.5, -rr - (zz[1] - zr) * math.tan(th), f"paper at {tdeg:.0f}°", fontsize=7, color="0.3", va="center",
                ha="left")
    D = geo["handle_od"]
    for zf in geo["hand"]["finger_pads_z"]:
        ax.add_patch(Rectangle((zf - 2.5, D / 2 + 1.5), 5, 2.0, color=(0.9, 0.7, 0.6), alpha=0.9))
    ax.add_patch(Rectangle((geo["hand"]["web_z"] - 6, D / 2 + 1.5), 12, 2.0, color=(0.85, 0.6, 0.5), alpha=0.9))
    ax.text(geo["hand"]["finger_pads_z"][1], D / 2 + 4.4, "finger pads", ha="center", fontsize=8)
    ax.text(geo["hand"]["web_z"], D / 2 + 4.4, "thumb-index web", ha="center", fontsize=8)
    ax.annotate("", xy=(0, X), xytext=(0, -X), arrowprops=dict(arrowstyle="<->", color="C1"))
    ax.text(1.0, X + 0.8, f"ball ±{X:.2f} mm at 50° (6.0 mm guaranteed 35–75°)", color="C1", fontsize=8)
    ax.axvline(zp, color="C4", lw=0.6, ls=":")
    ax.text(zp, -D / 2 - 5.5, f"gimbal z {zp:.1f}", color="C4", ha="center", fontsize=8)
    labels = {"skid_ring": ("C ring + heel wheel", -D / 2 - 10.2), "front_sleeve": ("fixed front sleeve (grip)", -D / 2 - 10.2),
              "main_board": ("main board (top)", D / 2 - 3.2), "carrier": ("moving nose", 1.0),
              "magnet_cap": ("magnet cap / coil plate", -D / 2 - 10.2), "battery": ("Li-ion cell (lifted 3 mm)", D / 2 - 3.2),
              "drive_motor": ("heel motors (under the cell)", -D / 2 - 10.2), "ec_slug": ("end-cap slug (detachable)", -D / 2 - 10.2)}
    for c in comps:
        if c["id"] in labels:
            t, yy = labels[c["id"]]
            ax.text(0.5 * (c["z0"] + c["z1"]), yy, t, ha="center", fontsize=7.5)
    Lmax = max(c["z1"] for c in comps)
    ax.set_xlim(-6, Lmax + 6)
    ax.set_ylim(-D / 2 - 12, D / 2 + 7)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip (mm)")
    ax.set_ylabel("x (mm; paper side negative)")
    ax.set_title(title, fontsize=11)
    ax.grid(alpha=0.2)
    zc_list = [(geo["ball_protrusion_mm"] + 3.5, "heel pod, page sensor"), (40.0, "grip: carrier, shafts"),
               (63.0, "main board, nose Hall"), (geo["pivot_z"], "gimbal (notched)"), (90.0, "coil plate"),
               (104.9, "cell (lifted) + motors")]
    if any(c["group"] == "inertial" for c in comps):
        zc_list[-1] = (104.9, "cell (lifted) + motors")
        zc_list.append((152.0, "end-cap"))
    for k, (zc, name) in enumerate(zc_list):
        axc = fig.add_axes([0.02 + 0.14 * k, 0.03, 0.12, 0.3])
        for c in comps:
            if not (c["z0"] <= zc <= c["z1"]):
                continue
            col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
            ox, oy = c.get("offset", [0, 0])
            if c["shape"] in ("cylinder", "cone"):
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(Circle((ox, oy), r, color=col, alpha=0.85))
            elif c["shape"] == "tube":
                r = c["d0"] / 2 + (c.get("d1", c["d0"]) - c["d0"]) / 2 * (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-9)
                axc.add_patch(Annulus((ox, oy), r, max(r - c["d_in"] / 2, 0.05), color=col, alpha=0.85))
            else:
                sx, sy = c["size"][0], c["size"][1]
                axc.add_patch(Rectangle((ox - sx / 2, oy - sy / 2), sx, sy, color=col, alpha=0.9))
        R = 13.5
        axc.set_xlim(-R, R)
        axc.set_ylim(-R, R)
        axc.set_aspect("equal")
        axc.set_title(f"z {zc:.0f} mm: {name}", fontsize=7.5)
        axc.set_xlabel("x", fontsize=7)
        axc.tick_params(labelsize=6.5)
    handles = [Rectangle((0, 0), 1, 1, color=COLORS[g]) for g in ("moving_nose", "refill", "skid", "grip", "mechanism", "actuator",
                                                                   "sensor", "electronics", "power", "haptic", "drive", "inertial", "structure")]
    fig.legend(handles, ["moving nose", "refill", "skid", "grip", "mechanism", "actuator", "sensor", "electronics", "power",
                         "haptic", "drive", "inertial", "structure"], loc="upper right", ncol=7, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.99, 0.995))
    fig.text(0.01, 0.005, "PROPOSED DESIGN (dimensioned concept; CALC or ASSUMPTION dimensions, CALC masses). Dashed: moving nose "
                          "at ± its usable travel. Cross-sections look from the back; x < 0 is the paper side.", fontsize=7.5)
    fig.savefig(path_png, dpi=130, facecolor="white")
    plt.close(fig)


def component_csv(comps: list, path: str):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm", "moves_with",
                    "optional", "mass_g", "part", "ledger"])
        for c in comps:
            w.writerow([c["id"], c["label"], c["group"], c["shape"], c["z0"], c["z1"], c.get("d0", ""), c.get("d1", ""), c.get("d_in", ""),
                        c.get("size", ""), c.get("offset", ""), c["moves_with"], c.get("optional", False), c.get("mass_g", ""),
                        c.get("part", ""), c.get("ledger", "")])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-endcap", action="store_true", help="the base pen (rear cap, no end-cap)")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--layout", default=os.path.join(OUT, "layout.json"))
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    geo = load_layout(a.layout)
    endcap = not a.no_endcap
    comps = select(geo, endcap)
    os.makedirs(a.out, exist_ok=True)
    tag = "revJ_pen_assembly" + ("" if endcap else "_no_endcap")
    step_ok, failed = None, []
    if not a.no_step:
        try:
            asm, failed = build_assembly(geo, comps, tag)
            asm.save(os.path.join(a.out, f"{tag}.step"))
            step_ok = True
        except Exception as e:
            step_ok = f"failed: {e}"
    png = os.path.join(a.out, "drawing_revJ_pen.png" if endcap else "drawing_revJ_pen_no_endcap.png")
    L = geo["length_with_endcap"] if endcap else geo["length"]
    drawing(geo, comps, png, f"Rev J integrated pen (PROPOSED DESIGN): C1S nose, heel wheel, pen lift, "
                             f"{'detachable end-cap fitted' if endcap else 'base pen'}; Ø{geo['handle_od']:.0f} × {L:.1f} mm")
    component_csv(comps, png.replace(".png", ".csv"))
    from stabpen import provenance
    summ = {"meta": provenance.metadata("PROPOSED DESIGN (dimensioned concept); masses CALC; nothing built or measured",
                                        extra={"script": "mechanics/cad/revJ_pen.py", "doc": "docs/revJ_design.md"}),
            "variant": "with end-cap" if endcap else "base pen", "step": step_ok, "step_parts_failed": failed,
            "geometry": {k: v for k, v in geo.items() if k not in ("components", "meta", "stabpen.provenance")},
            "n_components": len(comps)}
    summ["stabpen.provenance"] = summ["meta"]
    with open(os.path.join(a.out, "revJ_cad_summary.json" if endcap else "revJ_cad_summary_no_endcap.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(geo.get("fit_checks", {}).get("all_pass")), "step:", step_ok, "failed parts:", failed)
    return summ


if __name__ == "__main__":
    main()
