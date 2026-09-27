#!/usr/bin/env python3
"""Loaded bench mechanism, prototype stage A: dimensioned concept (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry; commercial parts shown as
envelopes of their catalogue class; nothing built).

Purpose: test the pen-scale nib mechanics against real paper and ink before a
miniature actuator exists (EXP-B01, B05, B06, B08, B09).  The nib, refill,
carrier (L1 = 12 mm to the gimbal) and lever ratio (n = 3.17) are the pen's;
the annular actuator is replaced by two orthogonal 12.7 mm moving-coil VCMs
(Moticont LVCM-013 class, AMF-02) pushing the lever end through wire struts.

Stack (page frame: x along the writing stage, z up, paper surface z = 0):
  base plate -> motorised XY stage (writing motion) -> 6-axis F/T sensor
  (Nano17 class) -> paper platen;
  vertical column with a low-friction carriage; dead weight sets the normal
  force; a goniometer arc centred on the ball sets the altitude theta;
  a 2-axis flexure "hand simulant" stage driven by two larger VCMs injects
  housing disturbance; the pen module rides on it.
Outputs results/cad/bench_rig_assembly.step, bench_rig_summary.json and
drawing_bench_rig.png (dimensioned side view).
Run: python3 mechanics/cad/bench_rig.py [--theta 50]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")

R = dict(
    # pen-scale mechanism (same as Rev A.1)
    L1=12.0, L2=38.0, ball_d=0.7, refill_d=2.35, refill_L=67.0, carrier_od=3.4, carrier_z0=3.0, carrier_z1=64.0,
    tip_travel=0.60,
    # stage-A actuators: 12.7 mm OD VCM class, strut length
    vcm_d=12.7, vcm_L=13.0, strut_L=6.0,
    # module frame (square tube around the axis)
    frame_w=50.0, frame_wall=5.0, frame_z0=40.0, frame_z1=80.0,
    # slim nose (clears the paper down to theta = 35 deg): cone r 3 -> 8 over z 1-22, tube r 10 to z 40
    nose_r0=2.6, nose_r1=8.0, nose_z0=5.0, nose_z1=22.0, neck_r=10.0,
    # hand-simulant stage: flexure block + 2 shaker VCMs (25 mm class)
    hs_L=22.0, shaker_d=25.0, shaker_L=25.0,
    # goniometer arc centred on the ball
    gon_r_in=150.0, gon_r_out=185.0, gon_t=10.0, gon_a0=30.0, gon_a1=80.0,
    # paper stack
    platen=(100.0, 100.0, 4.0), ft_d=17.0, ft_h=14.5, xy=(160.0, 160.0, 45.0), xy_travel=100.0,
    base=(420.0, 300.0, 15.0),
    # column, carriage and dead weight
    col=(60.0, 40.0, 330.0), col_x=-230.0, carriage=(70.0, 30.0, 60.0), weight_d=40.0, weight_h=30.0,
    # operating envelope
    theta_range=(35.0, 75.0), N_range=(0.2, 2.0), speed_range_mm_s=(1.0, 100.0), disturbance=(3.0, 15.0, 1.0),
)


def along_axis(wp, theta_deg):
    """Local build frame: ball at origin, pen axis +Z.  Rotate into the page frame
    so the axis points up and toward -x at altitude theta."""
    return wp.rotate((0, 0, 0), (0, 1, 0), theta_deg - 90.0)


def cyl_z(d, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(d / 2).extrude(z1 - z0)


def pen_module(theta):
    P = R
    parts = {}
    parts["refill"] = cyl_z(P["refill_d"], 0.8, P["refill_L"]).union(cq.Workplane("XY").sphere(P["ball_d"] / 2))
    parts["carrier"] = cyl_z(P["carrier_od"], P["carrier_z0"], P["carrier_z1"]).cut(cyl_z(2.5, P["carrier_z0"] - 1, P["carrier_z1"] + 1))
    parts["gimbal_block"] = (cq.Workplane("XY").box(14, 14, 3).translate((0, 0, P["L1"]))
                             .cut(cyl_z(P["carrier_od"] + 0.6, P["L1"] - 3, P["L1"] + 3)))
    zv = P["L1"] + P["L2"]
    x0 = P["carrier_od"] / 2 + P["strut_L"]
    parts["vcm_x"] = (cq.Workplane("YZ").workplane(offset=x0).circle(P["vcm_d"] / 2).extrude(P["vcm_L"])
                      .translate((0, 0, zv)))
    parts["vcm_y"] = (cq.Workplane("XZ").workplane(offset=-x0).circle(P["vcm_d"] / 2).extrude(-P["vcm_L"])
                      .translate((0, 0, zv)))
    parts["strut_x"] = (cq.Workplane("YZ").workplane(offset=P["carrier_od"] / 2).circle(0.15).extrude(P["strut_L"])
                        .translate((0, 0, zv)))
    parts["strut_y"] = (cq.Workplane("XZ").workplane(offset=-P["carrier_od"] / 2).circle(0.15).extrude(-P["strut_L"])
                        .translate((0, 0, zv)))
    w, t = P["frame_w"], P["frame_wall"]
    frame = (cq.Workplane("XY").rect(w, w).extrude(P["frame_z1"] - P["frame_z0"]).translate((0, 0, P["frame_z0"]))
             .cut(cq.Workplane("XY").rect(w - 2 * t, w - 2 * t).extrude(P["frame_z1"] - P["frame_z0"] + 2)
                  .translate((0, 0, P["frame_z0"] - 1))))
    nose = cq.Workplane("XY").add(cq.Solid.makeCone(P["nose_r0"], P["nose_r1"], P["nose_z1"] - P["nose_z0"],
                                                     pnt=cq.Vector(0, 0, P["nose_z0"]), dir=cq.Vector(0, 0, 1)))
    neck = cyl_z(2 * P["neck_r"], P["nose_z1"], P["frame_z0"])
    bore = cyl_z(2 * (P["carrier_od"] / 2 + R["tip_travel"] * (P["frame_z0"] - P["L1"]) / P["L1"] + 0.5), 0.0, P["frame_z0"] + 1)
    parts["module_nose"] = nose.union(neck).cut(bore).cut(cyl_z(2 * 1.2, -1, P["nose_z0"] + 2))
    parts["module_frame"] = frame
    hs = cq.Workplane("XY").rect(w, w).extrude(P["hs_L"]).translate((0, 0, P["frame_z1"]))
    parts["hand_simulant_flexure"] = hs
    zs = P["frame_z1"] + P["hs_L"] / 2
    parts["shaker_x"] = (cq.Workplane("YZ").workplane(offset=w / 2).circle(P["shaker_d"] / 2).extrude(P["shaker_L"])
                         .translate((0, 0, zs)))
    parts["shaker_y"] = (cq.Workplane("XZ").workplane(offset=-w / 2).circle(P["shaker_d"] / 2).extrude(-P["shaker_L"])
                         .translate((0, 0, zs)))
    return {k: along_axis(v, theta) for k, v in parts.items()}


def fixed_parts(theta):
    P = R
    parts = {}
    px, py, pz = P["platen"]
    parts["platen"] = cq.Workplane("XY").box(px, py, pz).translate((0, 0, -pz / 2))
    parts["ft_sensor"] = cyl_z(P["ft_d"], -pz - P["ft_h"], -pz)
    xx, xy_, xz = P["xy"]
    ztop = -pz - P["ft_h"]
    parts["xy_stage"] = cq.Workplane("XY").box(xx, xy_, xz).translate((0, 0, ztop - xz / 2))
    bx, by, bz = P["base"]
    zb = ztop - xz
    parts["base_plate"] = cq.Workplane("XY").box(bx, by, bz).translate((-60, 0, zb - bz / 2))
    cx, cy, cz = P["col"]
    parts["column"] = cq.Workplane("XY").box(cx, cy, cz).translate((P["col_x"], -60, zb + cz / 2))
    # goniometer sector in the x-z plane behind the module (y = -40)
    ang = [math.radians(a) for a in (P["gon_a0"], P["gon_a1"])]
    pts_out = [(-P["gon_r_out"] * math.cos(a), P["gon_r_out"] * math.sin(a)) for a in ang]
    pts_in = [(-P["gon_r_in"] * math.cos(a), P["gon_r_in"] * math.sin(a)) for a in ang]
    mid = math.radians(0.5 * (P["gon_a0"] + P["gon_a1"]))
    sector = (cq.Workplane("XZ").moveTo(*pts_in[0]).lineTo(*pts_out[0])
              .threePointArc((-P["gon_r_out"] * math.cos(mid), P["gon_r_out"] * math.sin(mid)), pts_out[1])
              .lineTo(*pts_in[1])
              .threePointArc((-P["gon_r_in"] * math.cos(mid), P["gon_r_in"] * math.sin(mid)), pts_in[0]).close()
              .extrude(P["gon_t"]).translate((0, -40 + P["gon_t"], 0)))
    parts["goniometer_arc"] = sector
    kx, ky, kz = P["carriage"]
    parts["carriage"] = cq.Workplane("XY").box(kx, ky, kz).translate((P["col_x"] + cx / 2 + kx / 2, -60, 170))
    parts["dead_weight"] = cyl_z(P["weight_d"], 205, 205 + P["weight_h"]).translate((P["col_x"] + cx / 2 + kx / 2, -60, 0))
    return parts


def drawing(theta, path):
    """Dimensioned side view (x-z) from the parameters (schematic, to scale)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from stabpen import plotstyle
    plotstyle.apply()
    P = R
    th = math.radians(theta)
    u = (-math.cos(th), math.sin(th))          # pen axis, ball -> cap
    nrm = (math.sin(th), math.cos(th))         # perpendicular in the drawing plane

    def pt(s, o=0.0):
        return (u[0] * s + nrm[0] * o, u[1] * s + nrm[1] * o)

    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    ink, grey = plotstyle.INK2, plotstyle.MUTED

    def box_along(s0, s1, half, **kw):
        c = [pt(s0, -half), pt(s1, -half), pt(s1, half), pt(s0, half), pt(s0, -half)]
        ax.plot([p[0] for p in c], [p[1] for p in c], **kw)

    box_along(0.8, P["refill_L"], P["refill_d"] / 2, color=plotstyle.SERIES[0], lw=1.5)
    box_along(P["carrier_z0"], P["carrier_z1"], P["carrier_od"] / 2, color=plotstyle.SERIES[0], lw=1.0)
    box_along(P["frame_z0"], P["frame_z1"], P["frame_w"] / 2, color=ink, lw=1.2)
    nose_pts = [pt(P["nose_z0"], -P["nose_r0"]), pt(P["nose_z1"], -P["nose_r1"]), pt(P["nose_z1"], -P["neck_r"]),
                pt(P["frame_z0"], -P["neck_r"]), pt(P["frame_z0"], P["neck_r"]), pt(P["nose_z1"], P["neck_r"]),
                pt(P["nose_z1"], P["nose_r1"]), pt(P["nose_z0"], P["nose_r0"]), pt(P["nose_z0"], -P["nose_r0"])]
    ax.plot([p[0] for p in nose_pts], [p[1] for p in nose_pts], color=ink, lw=1.2)
    box_along(P["frame_z1"], P["frame_z1"] + P["hs_L"], P["frame_w"] / 2, color=plotstyle.SERIES[2], lw=1.2)
    zv = P["L1"] + P["L2"]
    box_along(zv - P["vcm_L"] / 2, zv + P["vcm_L"] / 2, P["carrier_od"] / 2 + P["strut_L"] + P["vcm_L"],
              color=plotstyle.SERIES[1], lw=1.2)
    gx, gz = pt(P["L1"])
    ax.plot(gx, gz, marker="o", markersize=7, color=plotstyle.SERIES[3])
    ax.annotate("gimbal (virtual pivot)", xy=(gx, gz), xytext=(60, 12), fontsize=8, color=ink,
                arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))
    ax.annotate("2 x VCM 12.7 mm (x_H, y_H)\nvia wire struts", xy=pt(zv, -12), xytext=(-175, 60), fontsize=8, color=ink,
                arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))
    ax.annotate("hand-simulant flexure\n+ 2 shakers (3-15 Hz)", xy=pt(P["frame_z1"] + P["hs_L"] / 2, -20), xytext=(-190, 105),
                fontsize=8, color=ink, arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))
    px, _, pz = P["platen"]
    ax.add_patch(plt.Rectangle((-px / 2, -pz), px, pz, fc=plotstyle.GRID, ec=ink, lw=1.0))
    ax.add_patch(plt.Rectangle((-P["ft_d"] / 2, -pz - P["ft_h"]), P["ft_d"], P["ft_h"], fc="none", ec=ink, lw=1.0))
    xx, _, xz = P["xy"]
    ax.add_patch(plt.Rectangle((-xx / 2, -pz - P["ft_h"] - xz), xx, xz, fc="none", ec=ink, lw=1.0))
    ax.text(px / 2 + 4, -pz / 2, "paper platen", fontsize=8, color=ink, va="center")
    ax.text(P["ft_d"] / 2 + 4, -pz - P["ft_h"] / 2, "6-axis F/T sensor (Nano17 class)", fontsize=8, color=ink, va="center")
    ax.text(xx / 2 + 4, -pz - P["ft_h"] - xz / 2, f"XY stage, {P['xy_travel']:.0f} mm travel, 1-100 mm/s", fontsize=8, color=ink, va="center")
    a0, a1 = math.radians(P["gon_a0"]), math.radians(P["gon_a1"])
    import numpy as np
    aa = np.linspace(a0, a1, 60)
    for r in (P["gon_r_in"], P["gon_r_out"]):
        ax.plot(-r * np.cos(aa), r * np.sin(aa), color=grey, lw=1.0)
    ax.text(-P["gon_r_out"] * math.cos(a1) - 10, P["gon_r_out"] * math.sin(a1) + 6,
            f"goniometer arc R{P['gon_r_in']:.0f}, centred on the ball: theta {P['theta_range'][0]:.0f}-{P['theta_range'][1]:.0f} deg",
            fontsize=8, color=ink)

    def dim(s0, s1, off, label):
        p0, p1 = pt(s0, off), pt(s1, off)
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="<->", color=ink, lw=0.8))
        m = pt(0.5 * (s0 + s1), off + 3)
        ax.text(m[0], m[1], label, fontsize=8, color=ink, rotation=-theta, rotation_mode="anchor", ha="center", va="bottom")

    dim(0, P["L1"], P["frame_w"] / 2 + 8, f"L1 {P['L1']:.0f}")
    dim(P["L1"], P["L1"] + P["L2"], P["frame_w"] / 2 + 22, f"L2 = {P['L2']:.0f} (n = {P['L2']/P['L1']:.2f})")
    dim(0, P["refill_L"], P["frame_w"] / 2 + 36, f"D1 refill {P['refill_L']:.0f}")
    r_arc = 40
    ax.plot(-r_arc * np.cos(np.linspace(0, th, 30)), r_arc * np.sin(np.linspace(0, th, 30)), color=ink, lw=0.8)
    ax.plot([-60, 0], [0, 0], color=ink, lw=0.8, ls="--")
    ax.text(-r_arc - 14, 8, f"theta = {theta:.0f} deg", fontsize=8.5, color=ink)
    ax.text(-225, 172, "dead weight on a low-friction vertical carriage\n(column behind, x = -230) sets N = 0.2-2 N", fontsize=8, color=ink)
    ax.set_aspect("equal")
    ax.set_xlim(-235, 210); ax.set_ylim(-80, 200)
    ax.set_xlabel("x (mm), writing-stage direction"); ax.set_ylabel("z (mm)")
    ax.set_title("Stage-A loaded bench mechanism: side view (pen-scale nib, lever and gimbal; commercial actuators)", loc="left", fontsize=10.5)
    plotstyle.stamp(fig, "proposed design", "concept geometry to scale; commercial parts as envelopes of their class; not built")
    fig.tight_layout()
    fig.savefig(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=50.0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mod = pen_module(a.theta)
    fix = fixed_parts(a.theta)
    asm = cq.Assembly(name="bench_rig_stageA")
    for k, v in {**fix, **mod}.items():
        asm.add(v, name=k)
    asm.save(os.path.join(OUT, "bench_rig_assembly.step"))
    # clearance checks: pen module vs platen at theta limits (ball touches, nothing else)
    report = []
    for th in (R["theta_range"][0], a.theta, R["theta_range"][1]):
        m = pen_module(th)
        for k, v in m.items():
            if k in ("refill",):
                continue
            inter = v.intersect(fix["platen"])
            vol = inter.val().Volume() if inter.vals() else 0.0
            if vol > 1e-6:
                report.append({"theta": th, "part": k, "overlap_mm3": round(vol, 3)})
    summary = {"parameters_mm": R, "theta_deg": a.theta, "interference_with_platen": report,
               "tip_travel_at_vcm_mm": R["tip_travel"] * R["L2"] / R["L1"],
               "vcm_force_needed_at_design_N": 0.76 / (R["L2"] / R["L1"]),
               "notes": ["VCM stroke needed at the lever end = n x tip travel = 1.9 mm (LVCM-013 class stroke +/-3.2 mm, AMF-02/03)",
                         "force at the VCM for the design-point transverse load 0.76 N (theta 50, N 1 N) = 0.24 N; LVCM-013 class continuous force >> 0.24 N",
                         "wire struts decouple the two VCMs; strut buckling and bending stiffness to be sized with flexure_calc (EXP-B05)"]}
    meta = provenance.metadata("proposed design (bench concept geometry)", extra={"cadquery": cq.__version__})
    provenance.write_json(os.path.join(OUT, "bench_rig_summary.json"), {"meta": meta, "summary": summary})
    drawing(a.theta, os.path.join(OUT, "drawing_bench_rig.png"))
    print(json.dumps({k: v for k, v in summary.items() if k != "parameters_mm"}, indent=1))


if __name__ == "__main__":
    main()
