#!/usr/bin/env python3
"""R14 grip simulant (review gate G5): three-pad grip on a 2-DOF compliant mount (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry).  TAL221 47 x 12 x 6 mm (MFR AMF-227; the 1000 g variant for
2-8 N of squeeze); pads, skin, strips and leaves are PROPOSED; the translation stiffness range is chosen inside
the k1 range of Fu and Cavusoglu's arm-hand model (LIT HAP-26: 95 % CI 228-651 N/m in X, 679-1043 N/m in Z).

What it does: holds the pen (the same tasks with no module, the same mass locked, the module unpowered and the
module active) in three pads - index on top, thumb and middle finger at +-120 deg - with a platinum-silicone skin;
a spring screw sets the squeeze, read by the TAL221 in the index arm.  The pad block turns about the grip point on
two pairs of crossed strips (rotation about the page-frame y axis through the grip point) and translates along x
on a pair of parallel leaves; the whole mount hangs from R13's disturbance platform, so tremor enters from the
hand as it does in life.

Outputs (results/rig/cad/): rig_grip_assembly.step, drawing_rig_grip.png, rig_grip_summary.json.
Run: python3 mechanics/cad/rig_grip.py [--theta 50] [--pen pen24|slim14]
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
import rig_contact as R9  # noqa: E402
import rig_nib as R13  # noqa: E402

NAME = "rig_grip"
R = dict(
    s_grip=32.0,                                   # grip point from the ball along the axis (ASSUMPTION, tripod grip)
    pad=(5.0, 10.0, 16.0), skin_t=2.0, pad_roll=(0.0, 120.0, -120.0),
    frame_r=(7.0, 12.0), frame_w=12.0, frame_open_deg=125.0,     # C-frame radii above the pen surface, open underneath
    cell=(6.0, 12.0, 47.0),                        # TAL221 on top of the frame, along the axis
    strip=dict(L=20.0, b=10.0, t_options=(0.15, 0.20, 0.25, 0.30)), pivot_y=24.0,
    leaf=dict(L=40.0, b=10.0, t_options=(0.15, 0.20, 0.25)), z_yoke=112.0, z_mount=158.0,
    squeeze_N=(2.0, 4.0, 8.0), grip_ratio_HAP140=(4.3, 1.5),
    r_rot=(0.3, 0.5, 0.7),
)


def pad_block(pen: str):
    """Pads, skin, C-frame, arms and the squeeze cell in the local pen frame (ball at the origin, axis +Z)."""
    r = R13.R["pens"][pen]["od"] / 2
    s = R["s_grip"]
    pr, pw, pl = R["pad"]
    parts = {}
    pads = skins = arms = None
    for ang in R["pad_roll"]:
        skin = C.box(R["skin_t"], pw, pl, (r + R["skin_t"] / 2, 0, s))
        back = C.box(pr - R["skin_t"], pw, pl, (r + R["skin_t"] + (pr - R["skin_t"]) / 2, 0, s))
        arm = C.box(R["frame_r"][0] - pr + 0.5, 6.0, 8.0, (r + pr + (R["frame_r"][0] - pr + 0.5) / 2 - 0.25, 0, s))
        skin, back, arm = (C.yaw(x, ang) for x in (skin, back, arm))
        skins = skin if skins is None else skins.union(skin)
        pads = back if pads is None else pads.union(back)
        arms = arm if arms is None else arms.union(arm)
    ri, ro = r + R["frame_r"][0], r + R["frame_r"][1]
    frame = C.tube(2 * ro, 2 * ri, s - R["frame_w"] / 2, s + R["frame_w"] / 2)
    L = 3 * ro
    t = math.tan(math.radians(180.0 - R["frame_open_deg"]))
    wedge = (C.cq.Workplane("XY").workplane(offset=s - R["frame_w"])
             .polyline([(0, 0), (-L, L * t), (-L, -L * t)]).close().extrude(2 * R["frame_w"]))
    parts["pad_skins"] = skins
    parts["pad_backers"] = pads
    parts["pad_arms"] = arms
    parts["c_frame"] = frame.cut(wedge)
    cx, cy, cz = R["cell"]
    parts["squeeze_cell_TAL221"] = C.box(cx, cy, cz, (ro + cx / 2, 0, s))
    return parts


def pivot_and_mount(theta: float, pen: str):
    """Page-frame parts: crossed strips at +-y through the grip point, hubs, yoke, translation leaves, mount plate."""
    r = R13.R["pens"][pen]["od"] / 2
    lift = R9.R["ball_d"] / 2
    th = math.radians(theta)
    gx, gz = -R["s_grip"] * math.cos(th), R["s_grip"] * math.sin(th) + lift
    yp = r + R["pivot_y"]
    st = R["strip"]
    parts = {}
    strips = hubs = posts = None
    for sy in (-1, 1):
        for a in (45.0, -45.0):
            sp = C.box(st["L"], st["b"], 0.25, (0, 0, 0)).rotate((0, 0, 0), (0, 1, 0), a).translate((gx, sy * yp, gz))
            strips = sp if strips is None else strips.union(sp)
        h = st["L"] * math.sqrt(0.5) / 2
        hub = C.box(8.0, 6.0, 8.0, (gx, sy * (r + R["frame_r"][1] + 3.0 + 1.0), gz))       # moving: to the C-frame side
        hub = hub.union(C.box(8.0, st["b"], 3.0, (gx, sy * yp, gz - h - 1.5)))             # strips' lower ends
        hub = hub.union(C.box(8.0, yp - (r + R["frame_r"][1] + 2.0), 3.0,
                              (gx, sy * (r + R["frame_r"][1] + 2.0 + yp) / 2, gz - h - 1.5)))
        hubs = hub if hubs is None else hubs.union(hub)
        post = C.box(8.0, st["b"], 3.0, (gx, sy * yp, gz + h + 1.5)).union(
            C.box(8.0, 6.0, R["z_yoke"] - (gz + h), (gx, sy * (yp + st["b"] / 2 + 3.0), (R["z_yoke"] + gz + h) / 2)))
        posts = post if posts is None else posts.union(post)
    parts["cross_strips"] = strips
    parts["pivot_hubs"] = hubs
    yoke = posts.union(C.box(12.0, 2 * (yp + st["b"] / 2 + 6.0), 6.0, (gx, 0, R["z_yoke"] + 3.0)))
    parts["yoke"] = yoke
    lf = R["leaf"]
    z0 = R["z_yoke"] + 6.0
    leaves = None
    for sx in (-1, 1):
        l = C.box(0.25, lf["b"], lf["L"], (gx + 6.0 + sx * 12.0, 0, z0 + lf["L"] / 2))     # +6 mm: clears the 24 mm pen at 75 deg
        leaves = l if leaves is None else leaves.union(l)
    parts["translation_leaves"] = leaves
    parts["mount_plate"] = C.box(60.0, 40.0, 6.0, (gx + 6.0, 0, R["z_mount"] + 3.0))
    return parts


def posed(theta: float, pen: str):
    lift = R9.R["ball_d"] / 2
    out = {k: C.tilt(v, theta).translate((0, 0, lift)) for k, v in {**R13.pen_parts(pen), **pad_block(pen)}.items()}
    out.update(pivot_and_mount(theta, pen))
    return out


def checks():
    bed = R9.bed_parts()
    rows = []
    for pen in sorted(R13.R["pens"]):
        for th in (35.0, 50.0, 65.0, 75.0):
            mv = posed(th, pen)
            hits = C.pair_clearances({k: v for k, v in mv.items() if k != "ball"}, bed)
            pen_hits = []
            for k in ("pivot_hubs", "cross_strips", "yoke", "translation_leaves", "mount_plate"):
                for pk in ("pen_body", "pen_nose"):
                    v = C.overlap_mm3(mv[k], mv[pk])
                    if v > 1e-6:
                        pen_hits.append({"part": k, "against": pk, "overlap_mm3": round(v, 3)})
            low = min(C.zmin(mv[k]) for k in ("pad_skins", "pad_backers", "c_frame", "pad_arms", "squeeze_cell_TAL221", "pivot_hubs"))
            rows.append({"pen": pen, "theta": th, "interference_with_bed": hits, "mount_vs_pen": pen_hits,
                         "lowest_grip_part_mm": round(low, 2)})
    return rows


def calcs():
    lf, st = R["leaf"], R["strip"]
    d = R["s_grip"] * 1e-3
    trans = []
    for t in lf["t_options"]:
        k_t = 2 * C.leaf_k(lf["b"] * 1e-3, t * 1e-3, lf["L"] * 1e-3)
        row = {"leaf_t_mm": t, "k_trans_N_per_m": round(k_t, 0)}
        for rr in R["r_rot"]:
            # share of nib displacement from rotation for a force at the nib: (d^2/k_r) / (1/k_t + d^2/k_r) = rr
            k_r = d * d * k_t * (1 - rr) / rr
            # strips: n = 4 (two crossed pairs), E b t^3 / (12 L) each
            t_s = (k_r * 12 * st["L"] * 1e-3 / (4 * C.E_STEEL * st["b"] * 1e-3)) ** (1 / 3)
            row[f"r_rot_{rr}"] = {"k_rot_N_m_per_rad": round(k_r, 4), "strip_t_mm": round(t_s * 1e3, 3)}
        trans.append(row)
    ratio, sd = R["grip_ratio_HAP140"]
    return {"translation_and_rotation": trans,
            "translation_note": "two leaves, fixed-guided; 0.15/0.20/0.25 mm give about 211/500/977 N/m, spanning HAP-26's k1 "
                                "95 % CI (228-651 N/m X, 679-1043 N/m Z)",
            "rotation_note": "r_rot = share of the nib displacement due to rotation about the grip point for a force at the nib "
                             "(grip point 32 mm behind the ball); strips crossing at midpoints, small-angle stiffness E I / L each "
                             "(rig_common.cross_pivot_k), four strips",
            "squeeze_to_normal": {f"{sq:g} N": round(sq / ratio, 2) for sq in R["squeeze_N"]},
            "squeeze_note": f"writing force implied by grip-to-normal ratio {ratio} +- {sd} (children, LIT HAP-140); adult ratios "
                            "come from EXP-B06/I01",
            "cell": "TAL221 1000 g (9.8 N capacity, 150 % safe overload; MFR AMF-227) for 2-8 N; the 100 g SEN-14727 would overload"}


def drawing(theta, pen, path):
    import numpy as np
    from stabpen import plotstyle as ps
    fig, (ax, ax2) = C.new_figure(2, size=(13.0, 6.8), width_ratios=[1.2, 1.0])
    mv = posed(theta, pen)
    for k, v in R9.bed_parts().items():
        if k != "printer_bed_envelope":
            C.project(ax, v, "xz", color=ps.INK2, lw=0.5)
    col = {"pen_body": ps.SERIES[0], "pen_nose": ps.SERIES[0], "ball": ps.SERIES[0], "pad_skins": ps.SERIES[4],
           "squeeze_cell_TAL221": ps.SERIES[2], "cross_strips": ps.SERIES[1], "translation_leaves": ps.SERIES[1]}
    for k, v in mv.items():
        C.project(ax, v, "xz", color=col.get(k, ps.INK2), lw=0.7)
    th = math.radians(theta)
    lift = R9.R["ball_d"] / 2
    gx, gz = -R["s_grip"] * math.cos(th), R["s_grip"] * math.sin(th) + lift
    ax.plot([gx], [gz], marker="+", color=ps.INK, markersize=10)
    C.label(ax, (gx, gz), "grip point (rotation axis of the\ncrossed strips, 32 mm behind the ball)", (20, 60))
    C.label(ax, (gx + 12, R["z_yoke"] + 26), "parallel leaves (translation along x)", (25, 150))
    C.label(ax, (gx + 4, R["z_mount"] + 6), "to R13's disturbance platform", (25, 178))
    u = (-math.cos(th), math.sin(th))
    rr = R13.R["pens"][pen]["od"] / 2 + R["frame_r"][1] + 3
    C.label(ax, (u[0] * (R["s_grip"] + 20) + math.sin(th) * rr, u[1] * (R["s_grip"] + 20) + math.cos(th) * rr + lift),
            "TAL221 squeeze cell\n(spring screw sets 2/4/8 N)", (-175, 110))
    ax.set_xlim(-180, 120)
    ax.set_ylim(-30, 190)
    ax.set_xlabel("x (mm), page frame; disturbance along x")
    ax.set_ylabel("z (mm), paper top = 0")
    ax.set_title(f"R14 grip simulant, {pen}: side view", loc="left", fontsize=10)
    # section across the pen at the grip point: pads and C-frame
    blk = pad_block(pen)
    cut = C.box(200, 200, 0.5, (0, 0, R["s_grip"]))
    for k in ("pad_skins", "pad_backers", "pad_arms", "c_frame", "squeeze_cell_TAL221"):
        sec = blk[k].intersect(cut)
        C.project(ax2, sec, "xy", color=col.get(k, ps.INK2), lw=0.8)
    r = R13.R["pens"][pen]["od"] / 2
    a = np.linspace(0, 2 * np.pi, 200)
    ax2.plot(r * np.cos(a), r * np.sin(a), color=ps.SERIES[0], lw=1.0)
    ax2.annotate("", xy=(-r - 14, 0), xytext=(-r - 2, 0), arrowprops=dict(arrowstyle="->", color=ps.INK, lw=0.8))
    ax2.text(-r - 26, 2.0, "toward the\npaper", fontsize=7.5, color=ps.INK)
    ax2.text(r + R["frame_r"][1] + 8, 4, "TAL221 +\nspring screw", fontsize=7.5, color=ps.INK)
    ax2.text(-4, r + 1.5, "", fontsize=7)
    C.dim(ax2, (-r, -r - 16), (r, -r - 16), f"pen {2 * r:.0f}", off=0)
    ax2.text(-r - 12, r + 12, "index (0 deg), thumb and middle (+-120 deg);\nC-frame open underneath (+-125 deg)",
             fontsize=7.5, color=ps.INK)
    ax2.set_xlim(-r - 30, r + 40)
    ax2.set_ylim(-r - 24, r + 22)
    ax2.set_xlabel("local x (mm), +x away from the paper")
    ax2.set_ylabel("local y (mm)")
    ax2.set_title("Section at the grip point", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; skin, strips and leaves proposed; not built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=50.0)
    ap.add_argument("--pen", default="pen24", choices=sorted(R13.R["pens"]))
    a = ap.parse_args()
    parts = {**{k: v for k, v in R9.bed_parts().items() if k != "printer_bed_envelope"}, **posed(a.theta, a.pen)}
    step = C.save_assembly(NAME, parts, {"pen_body": "blue", "pad_skins": "pink", "squeeze_cell_TAL221": "green"})
    rows = checks()
    blk = pad_block(a.pen)
    m_block = sum(C.mass_g(blk[k], m) for k, m in (("pad_skins", "silicone"), ("pad_backers", "print"), ("pad_arms", "print"),
                                                   ("c_frame", "print"))) + 3.5    # TAL221 1 kg mass ASSUMPTION
    summary = {"parameters_mm": R, "theta_deg": a.theta, "pen_drawn": a.pen, "step": os.path.relpath(step, C.ROOT),
               "checks": rows, "calc": calcs(), "pad_block_mass_g": round(m_block, 1),
               "notes": ["the dummy module for the 'same mass locked' condition is printed with tungsten inserts to the "
                         "module's mass, centre of mass and inertia (weighed and swung on a bifilar pendulum)",
                         "EXP-T17 qualifies the simulant's FRF against its target within +-10 % before any G5 run"]}
    C.write_summary(NAME, "proposed design (R14 grip simulant concept geometry)", summary)
    drawing(a.theta, a.pen, os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps({"checks": rows, "calc": summary["calc"], "pad_block_mass_g": summary["pad_block_mass_g"]}, indent=1)[:5000])


if __name__ == "__main__":
    main()
