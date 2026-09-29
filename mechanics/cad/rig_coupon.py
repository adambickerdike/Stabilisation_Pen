#!/usr/bin/env python3
"""R12 actuator-coupon bench (review gate G2): 2-D force/current/position map, magnetic pull, Hall errors (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry).  K3D40 40 x 40 x 20 mm (MFR AMF-224, variants +-2/10/20/50 N);
the micrometre XYZ stage, the goniometer pair (common centre 30 mm below its face) and the coupon itself are
ENVELOPES (ASSUMPTION): the coupon shown is a generic spherical-gap pair (coil-plate bowl of radius 20 mm, magnet
cap at 20 - g), standing in for Rev J.1's C1S or study B's chosen actuator.

What it does: the stator sits on a 3-axis force plate; the moving part hangs from an overhead bridge on a 3-axis
micrometre stage and a 2-axis goniometer whose common centre is set on the coupon's pivot, so a spherical-gap
coupon tilts about its real pivot (the gap stays constant) and a translation coupon translates.  The force plate
reads force against coil current at every node; the zero-current map gives the pull and the negative stiffness.

Outputs (results/rig/cad/): rig_coupon_assembly.step, drawing_rig_coupon.png, rig_coupon_summary.json.
Run: python3 mechanics/cad/rig_coupon.py [--gap 1.0]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.dont_write_bytecode = True          # no bytecode caches from this study's helpers in mechanics/cad/__pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_common as C  # noqa: E402

NAME = "rig_coupon"
R = dict(
    base=(240.0, 160.0, 12.0), k3d40=(40.0, 40.0, 20.0), stator_plate=(60.0, 60.0, 5.0),
    # generic spherical-gap coupon (ASSUMPTION): bowl radius Rs, bowl wall, footprint radii
    Rs=20.0, bowl_t=3.0, bowl_r=11.0, cap_t=2.5, cap_r=9.0, arm_d=5.0, gap_range=(0.5, 1.5),
    # goniometer pair (common centre c below the lower face) and XYZ stage (envelopes, ASSUMPTION)
    gon=(40.0, 40.0, 22.0), gon_c=30.0, xyz=(60.0, 60.0, 60.0),
    # bridge
    post=(20.0, 30.0), post_x=100.0, beam=(220.0, 30.0, 15.0),
    # Hall board on a printed fixture beside the stator (envelope)
    hall=(16.0, 8.0, 1.6), hall_at=(18.0, 0.0, 30.0),
    tilt_deg=10.0, centring_errors_mm=(0.0, 0.05, 0.1, 0.2),
)


def stator_parts():
    P = R
    parts = {}
    bx, by, bz = P["base"]
    parts["base_plate"] = C.box(bx, by, bz, (0, 0, -bz / 2))
    kx, ky, kz = P["k3d40"]
    parts["force_plate_K3D40"] = C.box(kx, ky, kz, (0, 0, kz / 2))
    sx, sy, sz = P["stator_plate"]
    parts["stator_plate"] = C.box(sx, sy, sz, (0, 0, kz + sz / 2))
    z_bottom = kz + sz
    zc = z_bottom + P["bowl_t"] + P["Rs"]          # pivot height: the bowl's outer bottom sits on the plate
    sph_o = C.cq.Workplane("XY").sphere(P["Rs"] + P["bowl_t"]).translate((0, 0, zc))
    sph_i = C.cq.Workplane("XY").sphere(P["Rs"]).translate((0, 0, zc))
    footprint = C.cyl(2 * P["bowl_r"], z_bottom - 1.0, zc - 8.0)
    parts["coupon_stator_bowl"] = sph_o.cut(sph_i).intersect(footprint)
    hx, hy, hz = P["hall"]
    parts["hall_board"] = C.box(hx, hy, hz, (P["hall_at"][0] + hx / 2, P["hall_at"][1], zc - P["Rs"] * 0.55))
    parts["hall_fixture"] = C.box(hx, hy + 6.0, zc - P["Rs"] * 0.55 - z_bottom - hz / 2,
                                  (P["hall_at"][0] + hx / 2, 0, (zc - P["Rs"] * 0.55 - hz / 2 + z_bottom) / 2))
    return parts, zc


def moving_parts(zc: float, gap: float):
    """Magnet cap and arm, built about the pivot (0, 0, zc)."""
    P = R
    r_out = P["Rs"] - gap
    sph_o = C.cq.Workplane("XY").sphere(r_out).translate((0, 0, zc))
    sph_i = C.cq.Workplane("XY").sphere(r_out - P["cap_t"]).translate((0, 0, zc))
    footprint = C.cyl(2 * P["cap_r"], zc - r_out - 1.0, zc - 10.0)
    cap = sph_o.cut(sph_i).intersect(footprint)
    arm = C.cyl(P["arm_d"], zc - r_out + P["cap_t"] - 0.5, zc + P["gon_c"])
    return {"coupon_magnet_cap": cap, "coupon_arm": arm}


def overhead_parts(zc: float):
    P = R
    parts = {}
    gx, gy, gz = P["gon"]
    z0 = zc + P["gon_c"]
    parts["goniometer_lower"] = C.box(gx, gy, gz, (0, 0, z0 + gz / 2))
    parts["goniometer_upper"] = C.box(gx, gy, gz, (0, 0, z0 + 1.5 * gz))
    xx, xy_, xz = P["xyz"]
    z1 = z0 + 2 * gz
    parts["xyz_micrometre_stage"] = C.box(xx, xy_, xz, (0, 0, z1 + xz / 2))
    z2 = z1 + xz
    pw, pd = P["post"]
    bx, by, bz = P["beam"]
    parts["bridge"] = (C.box(bx, by, bz, (0, 0, z2 + bz / 2))
                       .union(C.box(pw, pd, z2, (P["post_x"], 0, z2 / 2)))
                       .union(C.box(pw, pd, z2, (-P["post_x"], 0, z2 / 2))))
    return parts


def rotate_about(wp, centre, axis, deg):
    return wp.rotate(centre, (centre[0] + axis[0], centre[1] + axis[1], centre[2] + axis[2]), deg)


def gap_checks(zc: float):
    """Min distance cap-bowl over tilts about the goniometer centre, which is off the sphere centre by e."""
    stat, _ = stator_parts()
    bowl = stat["coupon_stator_bowl"].val()
    rows = []
    for g in R["gap_range"]:
        mv = moving_parts(zc, g)
        for e in R["centring_errors_mm"]:
            worst = None
            for axis in ((1, 0, 0), (0, 1, 0)):
                for t in (-R["tilt_deg"], R["tilt_deg"]):
                    # goniometer centre displaced laterally by e (x) and axially by e (z): the worst common case
                    c = (e, 0.0, zc + e)
                    cap = rotate_about(mv["coupon_magnet_cap"], c, axis, t).val()
                    d = cap.distance(bowl)
                    worst = d if worst is None else min(worst, d)
            rows.append({"gap_mm": g, "centring_error_mm": e, "min_gap_at_10deg_mm": round(worst, 3),
                         "gap_change_mm": round(worst - g, 3)})
    return rows


def drawing(gap, path):
    from stabpen import plotstyle as ps
    fig, (ax, ax2) = C.new_figure(2, size=(12.5, 6.8), width_ratios=[1.2, 1.0])
    stat, zc = stator_parts()
    mv = moving_parts(zc, gap)
    ov = overhead_parts(zc)
    col = {"coupon_stator_bowl": ps.SERIES[1], "coupon_magnet_cap": ps.SERIES[0], "coupon_arm": ps.SERIES[0],
           "force_plate_K3D40": ps.SERIES[2], "hall_board": ps.SERIES[4]}
    for d in (stat, mv, ov):
        for k, v in d.items():
            C.project(ax, v, "xz", color=col.get(k, ps.INK2), lw=0.7)
    C.label(ax, (20, 10), "K3D40 3-axis plate (+-10 N map, +-50 N pull)", (35, -40))
    C.label(ax, (0, zc + R["gon_c"] + R["gon"][2]), "2-axis goniometer pair,\ncommon centre on the pivot", (60, 120))
    C.label(ax, (30, zc + R["gon_c"] + 2 * R["gon"][2] + 30), "3-axis micrometre stage", (60, 185))
    C.label(ax, (R["hall_at"][0] + 8, zc - R["Rs"] * 0.55), "Hall board at its design place", (60, 40))
    ax.plot([0], [zc], marker="+", color=ps.INK, markersize=10)
    ax.text(3, zc + 2, "pivot", fontsize=7.5, color=ps.INK)
    ax.set_xlim(-130, 170)
    ax.set_ylim(-60, 260)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("z (mm), base top = 0")
    ax.set_title("R12 coupon bench: front view", loc="left", fontsize=10)
    # detail: coupon section with the gap, tilted 10 deg
    import numpy as np
    for k in ("coupon_stator_bowl",):
        C.project(ax2, stat[k], "xz", color=col[k], lw=0.9)
    C.project(ax2, rotate_about(mv["coupon_magnet_cap"], (0, 0, zc), (0, 1, 0), R["tilt_deg"]), "xz", color=col["coupon_magnet_cap"], lw=0.9)
    C.project(ax2, mv["coupon_magnet_cap"], "xz", color=ps.MUTED, lw=0.5, alpha=0.6)
    aa = np.radians(np.linspace(-60, 60, 80))
    for r in (R["Rs"], R["Rs"] - gap):
        ax2.plot(r * np.sin(aa), zc - r * np.cos(aa), color=ps.MUTED, lw=0.4, ls=":")
    ax2.plot([0], [zc], marker="+", color=ps.INK, markersize=10)
    C.dim(ax2, (0, zc), (0, zc - R["Rs"]), f"Rs {R['Rs']:.0f}", off=-3)
    ax2.text(-16, zc - R["Rs"] - 6, f"gap {gap:.1f} mm, constant while the cap turns about the pivot\n(grey: untilted; colour: 10 deg)",
             fontsize=7.5, color=ps.INK)
    ax2.set_xlim(-25, 25)
    ax2.set_ylim(zc - R["Rs"] - 10, zc + 6)
    ax2.set_xlabel("x (mm)")
    ax2.set_ylabel("z (mm)")
    ax2.set_title("Generic spherical-gap coupon (envelope)", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; stage and coupon envelopes assumed; not built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=1.0)
    a = ap.parse_args()
    stat, zc = stator_parts()
    parts = {**stat, **moving_parts(zc, a.gap), **overhead_parts(zc)}
    step = C.save_assembly(NAME, parts, {"coupon_stator_bowl": "orange", "coupon_magnet_cap": "blue", "force_plate_K3D40": "gray"})
    gaps = gap_checks(zc)
    clash = C.pair_clearances(moving_parts(zc, a.gap), {k: v for k, v in stat.items() if k != "base_plate"})
    summary = {"parameters_mm": R, "gap_mm": a.gap, "pivot_height_mm": zc, "step": os.path.relpath(step, C.ROOT),
               "gap_vs_centring": gaps, "interference_at_rest": clash,
               "calc": {"plate_choice": "K3D40 +-10 N for the force map (up to about 4 N of coil force), +-50 N for the "
                                        "pull (12.4-22.2 N for Rev J.1's cap, 36 N by the cruder estimate; operating force "
                                        "200 % FS; MFR AMF-224)",
                        "centring_rule": "the goniometer centre must sit on the sphere centre within a fraction of the gap: "
                                         "see gap_vs_centring (a 0.2 mm error at 10 deg changes a 0.5 mm gap noticeably); "
                                         "set it with the zero-current pull map (the pull is symmetric only when centred)",
                        "thermal": "the coupon fits the printer chamber of R9's frame (active control to 55 C, MFR AMF-231) "
                                   "or a small heated box for the 23/35/50 C runs"},
               "notes": ["coupon geometry is generic (ASSUMPTION): replace with study B's chosen actuator coupon",
                         "translation coupons: lock the goniometers and use the XYZ stage; the map runs 7 x 7 or 11 x 11 nodes"]}
    C.write_summary(NAME, "proposed design (R12 coupon bench concept geometry)", summary)
    drawing(a.gap, os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps({"pivot": zc, "gaps": gaps, "clash": clash}, indent=1))


if __name__ == "__main__":
    main()
