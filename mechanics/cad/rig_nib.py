#!/usr/bin/env python3
"""R13 loaded-nib rig (review gates G3 and G4): disturbance stage, nib holder and truth (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry).  Commercial parts as envelopes: LVCM-032-025-02 housing
31.8 mm (MFR AMF-232; the 25.4 mm length is read from Moticont's naming convention, ASSUMPTION); LM13 readhead,
camera module and all masses are ASSUMPTIONS (densities in rig_common.RHO).

What it does: shakes the housing of a writing nib module (study B's slim core, 12-16 mm, or the 24 mm pen) with
swept sines and multitones (1-30 Hz, 0.25-2 mm peak) while it writes on paper lying on R9's force plate, with the
housing motion measured by an LM13 encoder on the stage, the nib carrier by a strobed camera and the ink by scan.
G4 stacks a second identical stage at 90 degrees.

Stage: four spring-steel leaves 0.15 x 15 x 50 mm in a parallelogram (motion along x), hanging below a base
block that is bolted to the CoreXY head (R9 frame) or to a fixed bridge; the voice coil pushes the platform.
Below the platform hangs a tilt arc (R 110 mm, centred on the ball), a roll ring (+-20 deg) and a split collar
with inserts for 12-26 mm bodies.

Outputs (results/rig/cad/): rig_nib_assembly.step, drawing_rig_nib.png, rig_nib_summary.json.
Run: python3 mechanics/cad/rig_nib.py [--theta 50] [--pen pen24|slim14]
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
import rig_contact as R9  # noqa: E402  (the paper, platen and force plate are R9's)

NAME = "rig_nib"
R = dict(
    # pens (study B grip classes, bnib/candidates.py: pen24 24 mm x 144 mm; slim 14 mm x 140 mm); nose cone ASSUMPTION
    pens={"pen24": dict(od=24.0, L=144.0, nose=(3.0, 4.0, 32.0), mass_g=90.0),
          "slim14": dict(od=14.0, L=140.0, nose=(2.5, 4.0, 22.0), mass_g=35.0)},
    ball_d=0.7,
    # stage: parallelogram of 4 leaves (x motion); platform and base (aluminium)
    leaf=dict(t=0.15, b=15.0, L=50.0), leaf_x=30.0, leaf_y=30.0,
    base=(80.0, 90.0, 12.0), platform=(80.0, 90.0, 3.0), platform_ribs=(4.0, 90.0, 8.0), platform_windows=(24.0, 60.0),
    z_platform=165.0,                       # platform underside above the paper
    # voice coil LVCM-032-025-02 (housing 31.8 mm; length ASSUMPTION 25.4 mm; coil envelope ASSUMPTION)
    vcm_d=31.8, vcm_L=25.4, coil_d=22.0, coil_L=10.0, coil_mass_g=30.0,
    vcm_ratings_N=(9.3, 29.3), vcm_stroke=12.7,
    # LM13 readhead envelope (ASSUMPTION) and scale strip on the platform
    readhead=(36.0, 14.0, 12.0), scale=(70.0, 6.0, 0.3),
    # nib holder: arc about the ball, roll ring, split collar with inserts
    arc_r=95.0, arc_w=12.0, arc_t=5.0, arc_y=-34.0, arc_a=(30.0, 82.0),
    roll_ring=(44.0, 32.0, 10.0), collar_od=30.0, collar_w=14.0, collar_s=95.0,
    inserts=(12.0, 14.0, 16.0, 20.0, 24.0, 26.0),
    # camera (OV9281 class board + lens, ASSUMPTION envelope) on the arc hanger, looking at the tip from -y
    cam_board=(38.0, 6.0, 38.0), cam_lens=(14.0, 16.0), cam_at=(-30.0, -70.0, 25.0),
    # operating envelope (review G3)
    theta_range=(35.0, 75.0), amp_mm=(0.25, 2.0), f_hz=(1.0, 30.0), stroke_limit_mm=3.0,
)


def pen_parts(pen: str):
    """Nib module housing in the local pen frame (ball centre at the origin, axis +Z)."""
    p = R["pens"][pen]
    r0, z0, z1 = p["nose"]
    ball = C.cq.Workplane("XY").sphere(R["ball_d"] / 2)
    tip = C.cone(0.35, r0, 0.2, z0)
    nose = C.cone(r0, p["od"] / 2, z0, z1)
    body = C.cyl(p["od"], z1, p["L"])
    return {"ball": ball, "pen_nose": tip.union(nose), "pen_body": body}


def holder_parts(pen: str):
    """Collar, insert and roll ring (local pen frame) + arc carriage."""
    p = R["pens"][pen]
    s = R["collar_s"]
    w = R["collar_w"]
    ins = C.tube(R["collar_od"] - 0.2, p["od"], s - w / 2, s + w / 2)
    collar = C.tube(R["roll_ring"][1], R["collar_od"], s - w / 2, s + w / 2)
    ring = C.tube(R["roll_ring"][0], R["roll_ring"][1] + 0.4, s - R["roll_ring"][2] / 2, s + R["roll_ring"][2] / 2)
    # carriage from the roll ring to the arc face (y = arc_y + arc_t), at the arc radius along the axis
    y_face = R["arc_y"] + R["arc_t"]
    y_ring = -R["roll_ring"][0] / 2
    carriage = C.box(14.0, y_ring - y_face + 2.0, 14.0, (0, (y_face + y_ring) / 2, s))
    return {"collar_insert": ins, "collar": collar, "roll_ring": ring, "arc_carriage": carriage}


def stage_parts():
    """Disturbance stage in the page frame at zero displacement."""
    P = R
    parts = {}
    zp = P["z_platform"]
    px, py, pz = P["platform"]
    plat = C.box(px, py, pz, (0, 0, zp + pz / 2))
    wx, wy = P["platform_windows"]
    for sx in (-1, 1):                          # two lightening windows between the ribs and the centre boss
        plat = plat.cut(C.box(wx, wy, pz + 2.0, (sx * (wx / 2 + 6.0), 0, zp + pz / 2)))
    rx, ry, rz = P["platform_ribs"]
    for sx in (-1, 1):
        plat = plat.union(C.box(rx, ry, rz, (sx * (P["leaf_x"] - 6.0), 0, zp + pz + rz / 2)))
    parts["platform"] = plat
    lf = P["leaf"]
    zl0 = zp + pz + rz
    leaves = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            l = C.box(lf["t"], lf["b"], lf["L"], (sx * P["leaf_x"], sy * P["leaf_y"], zl0 + lf["L"] / 2))
            leaves = l if leaves is None else leaves.union(l)
    parts["leaves"] = leaves
    # clamp blocks at both leaf ends (moving at the bottom, fixed at the top)
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts[f"clamp_lo_{'p' if sx > 0 else 'n'}{'p' if sy > 0 else 'n'}"] = C.box(
                8.0, lf["b"] + 4.0, 8.0, (sx * (P["leaf_x"] - 4.0 - 0.075), sy * P["leaf_y"], zl0 + 4.0))
    bx, by, bz = P["base"]
    zb = zl0 + lf["L"]
    # base block reaches +x over the voice coil's bracket and -y over the readhead's bracket
    base = C.box(bx + 50.0, by + 25.0, bz, (25.0, -12.5, zb + bz / 2))
    for sx in (-1, 1):
        base = base.union(C.box(8.0, by, 10.0, (sx * (P["leaf_x"] - 4.0 - 0.075), 0, zb - 5.0)))
    # drop bracket carrying the voice-coil housing and the readhead (fixed)
    xv = px / 2 + 3.0 + P["coil_L"]
    zv = zp + pz / 2 + 12.0
    base = base.union(C.box(10.0, 40.0, zb - zv + 20.0, (xv + P["vcm_L"] + 5.0, 0, (zb + zv - 20.0) / 2 + 10.0)))
    parts["stage_base_fixed"] = base
    parts["vcm_housing"] = (C.cq.Workplane("YZ").workplane(offset=xv).center(0, zv).circle(P["vcm_d"] / 2)
                            .extrude(P["vcm_L"]))
    parts["vcm_coil"] = (C.cq.Workplane("YZ").workplane(offset=px / 2 + 3.0).center(0, zv).circle(P["coil_d"] / 2)
                         .extrude(P["coil_L"]))
    parts["coil_link"] = C.box(3.0 + 1.0, 20.0, 12.0, (px / 2 + 1.5, 0, zv))
    sx_, sy_, sz_ = P["scale"]
    zs = zp + pz / 2
    parts["lm13_scale"] = C.box(sx_, sz_, sy_, (0, -py / 2 - sz_ / 2, zs))
    hx, hy, hz = P["readhead"]
    parts["lm13_readhead"] = C.box(hx, hy, hz, (0, -py / 2 - sz_ - 0.6 - hy / 2, zs))
    ztop = zs + hz / 2
    parts["readhead_bracket"] = C.box(hx, 6.0, zb - ztop + 2.0, (0, -py / 2 - sz_ - 0.6 - hy - 3.0, (zb + ztop) / 2 + 1.0))
    return parts


def arc_parts():
    """Tilt arc and its two hangers (fixed to the platform: they move with the stage)."""
    P = R
    ri, ro = P["arc_r"] - P["arc_w"] / 2, P["arc_r"] + P["arc_w"] / 2
    lift = P["ball_d"] / 2
    arc = C.sector_xz(ri, ro, P["arc_a"][0], P["arc_a"][1], P["arc_t"], P["arc_y"]).translate((0, 0, lift))
    yt = P["arc_y"] + P["arc_t"] / 2
    zp = P["z_platform"]
    a1 = math.radians(P["arc_a"][1])
    x_hi = -P["arc_r"] * math.cos(a1)
    z_hi = P["arc_r"] * math.sin(a1)
    h_hi = C.box(12.0, P["arc_t"], zp - z_hi + 4.0, (x_hi, yt, (zp + z_hi) / 2 - 2.0 + lift))
    a0 = math.radians(P["arc_a"][0])
    x_lo, z_lo = -ro * math.cos(a0) + 6.0, ro * math.sin(a0) - 4.0
    h_lo = C.box(12.0, P["arc_t"], zp - z_lo, (x_lo, yt, (zp + z_lo) / 2 + lift))
    # a cross bar ties the hangers to the platform's underside
    bar = C.box(abs(x_hi - x_lo) + 12.0, 12.0, 6.0, ((x_hi + x_lo) / 2, yt + 3.5, zp - 3.0))
    # the platform is +-40 mm in x: extend the platform footprint over the -x hanger with this bar
    cx, cy, cz = P["cam_at"]
    ztop = cz + P["cam_board"][2] / 2
    cam_arm = C.box(8.0, 8.0, zp - ztop, (cx, cy - 6.0, (zp + ztop) / 2)).union(
        C.box(8.0, -40.0 - (cy - 10.0), 6.0, (cx, (cy - 10.0 - 40.0) / 2, zp - 3.0)))
    cam = C.box(*P["cam_board"], (cx, cy, cz))
    lens = (C.cq.Workplane("XZ").workplane(offset=-cy - P["cam_board"][1] / 2).center(cx, cz)
            .circle(P["cam_lens"][0] / 2).extrude(-P["cam_lens"][1]))
    return {"tilt_arc": arc.union(h_hi).union(h_lo).union(bar), "camera_arm": cam_arm, "camera_module": cam.union(lens)}


def posed(theta: float, pen: str, dx: float = 0.0, roll_deg: float = 0.0):
    lift = R["ball_d"] / 2
    out = {}
    for k, v in {**pen_parts(pen), **holder_parts(pen)}.items():
        out[k] = C.tilt(C.roll(v, roll_deg) if k != "arc_carriage" else v, theta).translate((dx, 0, lift))
    for k, v in {**arc_parts()}.items():
        out[k] = v.translate((dx, 0, 0))
    for k, v in stage_parts().items():
        moving = not (k.startswith("stage_base") or k in ("vcm_housing", "lm13_readhead", "readhead_bracket"))
        out[k] = v.translate((dx, 0, 0)) if moving else v
    return out


MATERIAL = {"platform": "al", "leaves": "steel", "tilt_arc": "cfrp", "camera_arm": "print", "collar": "print",
            "collar_insert": "print", "roll_ring": "print", "arc_carriage": "print", "lm13_scale": "steel", "coil_link": "print"}
# tilt arc and hangers: 5 mm CFRP plate; roll ring: printed (PETG/PA-CF class) running on a PTFE strip (PROPOSED DESIGN)


def moving_mass_g(pen: str) -> dict:
    parts = {**holder_parts(pen), **arc_parts(), **stage_parts()}
    rows = {}
    for k, v in parts.items():
        if k.startswith("clamp_lo"):
            rows[k] = C.mass_g(v, "al")
        elif k in MATERIAL:
            m = C.mass_g(v, MATERIAL[k])
            rows[k] = m / 3.0 if k == "leaves" else m          # a leaf moves with a third of its mass (lumped)
    rows["camera_module"] = 15.0                               # ASSUMPTION (board + lens)
    rows["vcm_coil"] = R["coil_mass_g"]                        # ASSUMPTION (not on the Moticont page)
    rows["pen_module"] = R["pens"][pen]["mass_g"]              # ASSUMPTION (study B class masses)
    total = sum(rows.values())
    return {"parts_g": {k: round(v, 1) for k, v in rows.items()}, "total_g": round(total, 1),
            "stage_without_pen_g": round(total - rows["pen_module"], 1)}


def checks(pen: str):
    bed = R9.bed_parts()
    hits, zrows = [], []
    for th in (35.0, 50.0, 65.0, 75.0):
        for dx in (-R["stroke_limit_mm"], 0.0, R["stroke_limit_mm"]):
            for rl in ((-20.0, 0.0, 20.0) if dx == 0.0 else (0.0,)):
                mv = posed(th, pen, dx, rl)
                moving = {k: v for k, v in mv.items() if k != "ball"}
                for r in C.pair_clearances(moving, bed):
                    r.update({"theta": th, "dx_mm": dx, "roll_deg": rl})
                    hits.append(r)
        mv = posed(th, pen)
        pen_top = C.bbox(mv["pen_body"]).zmax
        low = min(C.zmin(v) for k, v in mv.items() if k not in ("ball", "pen_nose"))
        self_hits = []
        for k in ("pen_body", "pen_nose", "roll_ring", "collar"):
            for f in ("platform", "tilt_arc", "camera_arm", "camera_module", "lm13_readhead", "vcm_housing", "stage_base_fixed"):
                v = C.overlap_mm3(mv[k], mv[f])
                if v > 1e-6:
                    self_hits.append({"part": k, "against": f, "overlap_mm3": round(v, 3)})
        zrows.append({"theta": th, "pen_top_mm": round(pen_top, 1), "platform_underside_mm": R["z_platform"],
                      "lowest_part_other_than_nib_mm": round(low, 2), "self_interference": self_hits})
    return hits, zrows


def calcs(pen: str):
    lf = R["leaf"]
    t, b, L = lf["t"] * 1e-3, lf["b"] * 1e-3, lf["L"] * 1e-3
    k = 4 * C.leaf_k(b, t, L)
    mm = moving_mass_g(pen)
    m = mm["total_g"] * 1e-3
    w = 2 * math.pi * 30.0
    F_corner = abs(k - m * w * w) * 2e-3
    F_ac40 = m * 40.0 + k * 2e-3
    st = stage_parts()
    fixed_g = (C.mass_g(st["stage_base_fixed"], "al") + C.mass_g(st["readhead_bracket"], "al") + 80.0   # LM13 readhead 80 g (MFR OPT-89)
               + 0.6 * C.mass_g(st["vcm_housing"], "steel"))                                              # housing: 60 % of a solid steel envelope (ASSUMPTION)
    return {
        "head_payload_g": round(fixed_g + mm["total_g"], 0),
        "head_payload_note": "everything hung from the CoreXY head when R13 rides on it (solid 12 mm aluminium base as drawn; "
                             "a pocketed base saves a few hundred grams); the Core One+ page lists no payload (MFR AMF-231)",
        "stage_k_N_per_m": round(k, 1),
        "leaf_stress_at_3mm_MPa": round(C.leaf_stress(t, 3e-3, L) / 1e6, 1),
        "leaf_buckling_per_leaf_N": round(C.leaf_buckling(b, t, L), 2),
        "weight_carried_N": round(m * 9.81, 2),
        "buckling_note": "hanging, the leaves carry the weight in tension; mounted upright the four leaves buckle at about "
                         f"{4 * C.leaf_buckling(b, t, L):.1f} N (Euler, K = 1)",
        "parasitic_vertical_motion_um_at_2mm": round(C.leaf_shortening(2e-3, L) * 1e6, 1),
        "parasitic_note": "the platform rises 0.6 d^2 / L at twice the drive frequency: 48 um at 2 mm; through the nib's own "
                          "axial spring it modulates the ink force (measured by the force plate, not assumed away)",
        "moving_mass": mm,
        "stage_mode_Hz": round(C.mode_hz(k, m), 2),
        "F_needed_2mm_30Hz_N": round(F_corner, 2),
        "F_needed_multitone_capped_40m_s2_N": round(F_ac40, 2),
        "vcm_continuous_N": R["vcm_ratings_N"][0], "vcm_peak_N": R["vcm_ratings_N"][1],
        "corner_verdict": ("within continuous rating" if F_corner <= R["vcm_ratings_N"][0] else
                           "above continuous, within peak: short bursts only" if F_corner <= R["vcm_ratings_N"][1] else
                           "above peak rating"),
        "vcm_stroke_mm": R["vcm_stroke"], "stroke_needed_mm": 2 * R["stroke_limit_mm"],
        "alternative": "LVCM-038-038-02 (24.9 N continuous, 78.8 N peak, 0.38 in stroke; MFR AMF-232) covers the 2 mm / 30 Hz "
                       "corner continuously; its moving mass is not on the page (weigh it)",
        "collar_inserts_mm": list(R["inserts"]),
    }


def drawing(theta, pen, path):
    import numpy as np
    from stabpen import plotstyle as ps
    fig, (ax, ax2) = C.new_figure(2, size=(13.5, 7.0), width_ratios=[1.35, 1.0])
    mv = posed(theta, pen)
    for k, v in R9.bed_parts().items():
        if k == "printer_bed_envelope":
            continue
        C.project(ax, v, "xz", color=ps.INK2, lw=0.5)
    colors = {"pen_body": ps.SERIES[0], "pen_nose": ps.SERIES[0], "ball": ps.SERIES[0], "vcm_housing": ps.SERIES[1],
              "vcm_coil": ps.SERIES[1], "leaves": ps.SERIES[2], "lm13_readhead": ps.SERIES[4], "lm13_scale": ps.SERIES[4],
              "camera_module": ps.SERIES[6]}
    for k, v in mv.items():
        C.project(ax, v, "xz", color=colors.get(k, ps.INK2), lw=0.7)
    for th in (35.0, 75.0):
        m2 = posed(th, pen)
        C.project(ax, m2["pen_body"], "xz", color=ps.MUTED, lw=0.4, alpha=0.6)
    lift = R["ball_d"] / 2
    th = math.radians(theta)

    def pt(s_ax, off=0.0):
        return (-s_ax * math.cos(th) + off * math.sin(th), s_ax * math.sin(th) + off * math.cos(th) + lift)

    zp = R["z_platform"]
    lf = R["leaf"]
    z_leaf = zp + R["platform"][2] + R["platform_ribs"][2]
    C.label(ax, (R["leaf_x"], z_leaf + lf["L"] / 2), "4 leaves 0.15 x 15 x 50 mm\n(parallelogram, x motion, 324 N/m)", (60, 262))
    C.label(ax, (R["platform"][0] / 2 + 3 + R["coil_L"] + R["vcm_L"] / 2, zp + R["platform"][2] / 2 + 12 + R["vcm_d"] / 2),
            "LVCM-032-025-02 (31.8 mm)\npushes the platform", (105, 228))
    C.label(ax, (0, zp + R["platform"][2] / 2 + 2 - R["readhead"][2] / 2), "LM13 scale + readhead\n(housing truth)", (105, 135))
    C.label(ax, pt(R["collar_s"], -R["roll_ring"][0] / 2), "split collar + insert (12-26 mm)\ninside a +-20 deg roll ring",
            (-230, 150))
    a = math.radians(62)
    C.label(ax, (-R["arc_r"] * math.cos(a), R["arc_r"] * math.sin(a)), f"tilt arc R{R['arc_r']:.0f} about the ball",
            (-230, 110))
    C.label(ax, (R["cam_at"][0], R["cam_at"][2]), "strobed camera\n(nib carrier truth)", (-150, 40))
    C.label(ax, (20, 0), "paper on R9's force plate", (40, -30))
    C.dim(ax, (55, 0), (55, zp), f"{zp:.0f} paper to platform", off=0)
    ax.plot([-70, 0], [0, 0], color=ps.INK, lw=0.5, ls=":")
    rr = 30
    ax.plot(-rr * np.cos(np.linspace(0, th, 30)), rr * np.sin(np.linspace(0, th, 30)) + lift, color=ps.INK, lw=0.6)
    ax.text(-rr - 30, 4, f"theta {theta:.0f} deg\n(35, 75 grey)", fontsize=7.5, color=ps.INK)
    ax.set_xlim(-240, 200)
    ax.set_ylim(-45, 280)
    ax.set_xlabel("x (mm), page frame; stage motion along x")
    ax.set_ylabel("z (mm), paper top = 0")
    ax.set_title(f"R13 one-axis loaded-nib rig, {pen} module: side view", loc="left", fontsize=10)
    # top view of the stage
    st = stage_parts()
    for k, v in st.items():
        if k in ("stage_base_fixed",):
            continue
        C.project(ax2, v, "xy", color=colors.get(k, ps.INK2), lw=0.7)
    C.project(ax2, st["stage_base_fixed"], "xy", color=ps.MUTED, lw=0.4, alpha=0.7)
    C.dim(ax2, (-R["leaf_x"], R["leaf_y"] + 12), (R["leaf_x"], R["leaf_y"] + 12), f"{2 * R['leaf_x']:.0f} leaf pitch", off=6)
    C.dim(ax2, (-R["leaf_x"] - 12, -R["leaf_y"]), (-R["leaf_x"] - 12, R["leaf_y"]), f"{2 * R['leaf_y']:.0f}", off=0)
    C.dim(ax2, (-R["platform"][0] / 2, -R["platform"][1] / 2 - 32), (R["platform"][0] / 2, -R["platform"][1] / 2 - 32),
          f"platform {R['platform'][0]:.0f} x {R['platform'][1]:.0f}", off=0)
    ax2.annotate("", xy=(25, 0), xytext=(-25, 0), arrowprops=dict(arrowstyle="<->", color=ps.SERIES[3], lw=1.2))
    ax2.text(0, 3, "+-3 mm (stop)", fontsize=7.5, color=ps.INK, ha="center")
    ax2.text(R["platform"][0] / 2 + 8, 26, "VCM", fontsize=7.5, color=ps.INK)
    ax2.text(-18, -R["platform"][1] / 2 - 22, "LM13", fontsize=7.5, color=ps.INK)
    ax2.set_xlim(-65, 100)
    ax2.set_ylim(-95, 75)
    ax2.set_xlabel("x (mm)")
    ax2.set_ylabel("y (mm)")
    ax2.set_title("Stage, top view (G4 stacks a second stage at 90 deg)", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; envelopes and masses partly assumed; not built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=50.0)
    ap.add_argument("--pen", default="pen24", choices=sorted(R["pens"]))
    a = ap.parse_args()
    parts = {**{k: v for k, v in R9.bed_parts().items()}, **posed(a.theta, a.pen)}
    step = C.save_assembly(NAME, parts, {"pen_body": "blue", "leaves": "green", "vcm_housing": "orange"})
    out = {}
    for pen in sorted(R["pens"]):
        hits, zrows = checks(pen)
        out[pen] = {"interference_with_bed": hits, "clearance_by_theta": zrows, "calc": calcs(pen)}
    summary = {"parameters_mm": R, "theta_deg": a.theta, "pen_drawn": a.pen, "step": os.path.relpath(step, C.ROOT),
               "by_pen": out,
               "notes": ["the stage hangs from the CoreXY head (R9 frame) so the paper stays on R9's force plate; the "
                         "standard build hangs it from a fixed bridge and moves the paper on the Zaber stages instead",
                         "the voice coil's reaction shakes the head: log the head encoders and the plate; do not assume it away",
                         "moving masses are roll-ups with ASSUMED densities, coil and camera masses: weigh the parts"]}
    C.write_summary(NAME, "proposed design (R13 loaded-nib rig concept geometry)", summary)
    drawing(a.theta, a.pen, os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps({p: {"hits": o["interference_with_bed"], "clear": o["clearance_by_theta"], "calc": o["calc"]}
                      for p, o in out.items()}, indent=1)[:6000])


if __name__ == "__main__":
    main()
