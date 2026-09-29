#!/usr/bin/env python3
"""R9 contact-and-ink rig (review gate G1): contact head for a CoreXY printer frame (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry; commercial parts as envelopes from their data sheets where the
ledger has the dimensions: K3D40 40 x 40 x 20 mm MFR AMF-224; LSB200 19.05 x 16.5 x 6.7 mm MFR AMF-225;
LVCM-013-013-03 12.7 x 12.7 mm housing, 19.0 mm overall MFR AMF-02; everything else ASSUMPTION).

What it measures: the refill's axial force F_c (in-line cell behind a leaf-guided holder) and, separately, the
force the ball applies to the paper (a 3-axis plate under the paper, page frame), while the printer head drags
the pen at a set tilt, speed and direction (docs/measurement_rig.md section 2).

Frames: page frame, paper top z = 0, the ball touching the paper at the origin when the head is at the plate
centre; the pen axis rises toward -x at altitude theta.  The tilt arc (R 70 mm) is centred on the ball centre
so changing theta leaves the contact point where it was.

Outputs (results/rig/cad/): rig_contact_assembly.step, drawing_rig_contact.png, rig_contact_summary.json.
Run: python3 mechanics/cad/rig_contact.py [--theta 50]
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

NAME = "rig_contact"
R = dict(
    # refill (D1 class, as bench_rig.py): ball, tip cone, tube
    ball_d=0.7, tip_r0=0.30, tip_z0=0.25, tip_z1=4.5, refill_d=2.35, refill_L=67.0,
    # holder and parallel-leaf guide (two leaves, spring steel)
    holder_od=8.0, holder_id=2.4, holder_z=(22.0, 50.0),
    leaf=dict(t=0.05, b=8.0, L=25.0, z=(26.0, 46.0)),
    # in-line cell (LSB200, load axis along the 19.05 mm side: ASSUMPTION, check drawing FI1455)
    cell=(16.5, 6.7, 19.05), cell_z0=50.5,
    # voice coil LVCM-013-013-03: coil envelope (ASSUMPTION) + housing 12.7 x 12.7 (19.0 overall at mid-stroke)
    coil_d=10.0, coil_L=6.3, vcm_d=12.7, vcm_L=12.7,
    # cartridge frame (aluminium)
    frame_side=(6.0, 20.0), frame_x=29.0, end_t=6.0, bracket=(16.0, 4.0),
    # Hall slide sensor (magnet on the holder, DRV5055 on a bracket)
    hall_mag_d=2.0, hall_z=36.0,
    # tilt arc on the head (fixed to the head adapter plate)
    arc_r=70.0, arc_w=12.0, arc_t=6.0, arc_y=-20.0, arc_a=(30.0, 85.0), arc_holes=(35.0, 50.0, 65.0, 75.0), hole_d=3.2,
    head_plate=(95.0, 50.0, 6.0), head_z=110.0,
    # bed side: paper, underlay, CFRP platen, K3D40, adapter, printer bed envelope
    paper=(76.0, 56.0, 0.1), underlay_t=1.0, platen=(80.0, 60.0, 1.5), k3d40=(40.0, 40.0, 20.0),
    bed_adapter=(120.0, 100.0, 6.0), bed=(250.0, 220.0, 8.0), clamp=(5.0, 60.0, 2.5), clamp_x=35.0,
    # usable writing area (ball centre), head positions checked
    area_x=(-29.0, 33.0), area_y=(-26.0, 26.0),
    theta_range=(35.0, 75.0),
)


def refill_parts():
    P = R
    ball = C.cq.Workplane("XY").sphere(P["ball_d"] / 2)
    tip = C.cone(P["tip_r0"], P["refill_d"] / 2, P["tip_z0"], P["tip_z1"])
    tube = C.cyl(P["refill_d"], P["tip_z1"], P["refill_L"])
    return {"ball": ball, "refill": tip.union(tube)}


def cartridge_parts():
    """Parts that turn with theta (local pen frame, ball centre at the origin)."""
    P = R
    parts = {}
    z0, z1 = P["holder_z"]
    parts["holder"] = C.tube(P["holder_od"], P["holder_id"], z0, z1)
    lf = P["leaf"]
    r_h = P["holder_od"] / 2
    leaves = None
    for z in lf["z"]:
        l = C.box(lf["L"], lf["b"], lf["t"], (r_h + lf["L"] / 2, 0, z))
        leaves = l if leaves is None else leaves.union(l)
    parts["guide_leaves"] = leaves
    cx, cy, cz = P["cell"]
    parts["axial_cell_LSB200"] = C.box(cx, cy, cz, (0, 0, P["cell_z0"] + cz / 2))
    zc = P["cell_z0"] + cz + 0.5
    parts["vcm_coil"] = C.cyl(P["coil_d"], zc, zc + P["coil_L"])
    zh = zc + P["coil_L"]
    parts["vcm_housing"] = C.cyl(P["vcm_d"], zh, zh + P["vcm_L"])
    ze = zh + P["vcm_L"]
    ft, fw = P["frame_side"]
    x0 = r_h + lf["L"]
    side = C.box(ft, fw, ze + P["end_t"] - z0, (x0 + ft / 2, 0, (z0 + ze + P["end_t"]) / 2))
    end = C.box(x0 + ft + 10.0, fw, P["end_t"], ((x0 + ft - 10.0) / 2, 0, ze + P["end_t"] / 2))
    parts["cartridge_frame"] = side.union(end)
    bl, bt = P["bracket"]
    zb = P["arc_r"]
    parts["arc_carriage"] = C.box(x0 + ft + 8.0, bt, bl, ((x0 + ft - 8.0) / 2, P["arc_y"] + P["arc_t"] + bt / 2, zb))
    parts["hall_magnet"] = (C.cq.Workplane("XZ").workplane(offset=-r_h).circle(P["hall_mag_d"] / 2).extrude(-1.5)
                            .translate((0, 0, P["hall_z"])))
    parts["hall_sensor_DRV5055"] = C.box(3.0, 1.1, 3.0, (0, r_h + 2.6, P["hall_z"]))
    parts["hall_bracket"] = C.box(x0 - r_h, 2.0, 6.0, (r_h + (x0 - r_h) / 2 + 1.0, r_h + 4.2, P["hall_z"]))
    return parts


def head_fixed_parts():
    """Parts fixed to the printer head (move in x, y with the head, not with theta)."""
    P = R
    ri, ro = P["arc_r"] - P["arc_w"] / 2, P["arc_r"] + P["arc_w"] / 2
    arc = C.sector_xz(ri, ro, P["arc_a"][0], P["arc_a"][1], P["arc_t"], P["arc_y"])
    for a in P["arc_holes"]:
        ar = math.radians(a)
        h = (C.cq.Workplane("XZ").workplane(offset=-P["arc_y"] + 1.0).center(-P["arc_r"] * math.cos(ar), P["arc_r"] * math.sin(ar))
             .circle(P["hole_d"] / 2).extrude(P["arc_t"] + 2.0))
        arc = arc.cut(h)
    hz = P["head_z"]
    yt = P["arc_y"] + P["arc_t"] / 2
    post_hi = C.box(10.0, P["arc_t"], hz - 66.0, (-7.0, yt, (hz + 66.0) / 2))
    a0 = math.radians(P["arc_a"][0])
    xo = -ro * math.cos(a0)
    post_lo = C.box(10.0, P["arc_t"], hz - 33.0, (xo + 3.0, yt, (hz + 33.0) / 2))
    px, py, pz = P["head_plate"]
    plate = C.box(px, py, pz, (-px / 2 + 15.0, 0, hz + pz / 2))
    frame = arc.union(post_hi).union(post_lo).union(plate)
    return {"arc_frame": frame.translate((0, 0, P["ball_d"] / 2))}


def bed_parts():
    P = R
    parts = {}
    zp = -P["paper"][2]
    parts["paper"] = C.box(*P["paper"], (0, 0, zp / 2))
    zu = zp - P["underlay_t"]
    parts["underlay"] = C.box(P["paper"][0], P["paper"][1], P["underlay_t"], (0, 0, (zp + zu) / 2))
    px, py, pz = P["platen"]
    parts["platen_cfrp"] = C.box(px, py, pz, (0, 0, zu - pz / 2))
    zk = zu - pz
    kx, ky, kz = P["k3d40"]
    parts["force_plate_K3D40"] = C.box(kx, ky, kz, (0, 0, zk - kz / 2))
    za = zk - kz
    ax_, ay, az = P["bed_adapter"]
    parts["bed_adapter"] = C.box(ax_, ay, az, (0, 0, za - az / 2))
    bx, by, bz = P["bed"]
    parts["printer_bed_envelope"] = C.box(bx, by, bz, (0, 0, za - az - bz / 2))
    cx, cy, cz = P["clamp"]
    for s, n in ((1, "clamp_px"), (-1, "clamp_nx")):
        parts[n] = C.box(cx, cy, cz, (s * (P["clamp_x"] + cx / 2), 0, cz / 2))
    return parts


def posed(theta, head_xy=(0.0, 0.0)):
    """Cartridge and refill at theta, head at head_xy (ball centre above the paper at head_xy)."""
    lift = R["ball_d"] / 2
    out = {}
    for k, v in {**refill_parts(), **cartridge_parts()}.items():
        out[k] = C.tilt(v, theta).translate((head_xy[0], head_xy[1], lift))
    for k, v in head_fixed_parts().items():
        out[k] = v.translate((head_xy[0], head_xy[1], 0))
    return out


def checks():
    bed = bed_parts()
    rows, zmins = [], []
    corners = [(x, y) for x in R["area_x"] for y in R["area_y"]] + [(0.0, 0.0)]
    for th in (35.0, 50.0, 65.0, 75.0):
        # contact-free parts against the bed at the plate centre and at the four corners of the writing area
        for hx, hy in corners:
            mv = posed(th, (hx, hy))
            moving = {k: v for k, v in mv.items() if k != "ball"}
            for r in C.pair_clearances(moving, bed):
                r.update({"theta": th, "head_xy": [hx, hy]})
                rows.append(r)
        mv = posed(th)
        z_non_refill = min(C.zmin(v) for k, v in mv.items() if k not in ("ball", "refill"))
        z_refill = C.zmin(mv["refill"])
        # cartridge against the head's own arc frame (the carriage rides on it and is excluded)
        self_hits = [{"part": k, "overlap_mm3": round(C.overlap_mm3(v, mv["arc_frame"]), 4)}
                     for k, v in mv.items() if k not in ("arc_frame", "arc_carriage")
                     and C.overlap_mm3(v, mv["arc_frame"]) > 1e-6]
        zmins.append({"theta": th, "lowest_non_refill_part_mm": round(z_non_refill, 2),
                      "lowest_refill_point_mm": round(z_refill, 3), "hits_on_arc_frame": self_hits})
    return rows, zmins


def calcs():
    P = R
    lf = P["leaf"]
    k1 = C.leaf_k(lf["b"] * 1e-3, lf["t"] * 1e-3, lf["L"] * 1e-3)
    k = 2 * k1
    s15 = C.leaf_stress(lf["t"] * 1e-3, 1.5e-3, lf["L"] * 1e-3)
    parts = cartridge_parts()
    m_holder = C.mass_g(parts["holder"], "al")
    m_refill = C.mass_g(refill_parts()["refill"], "steel") * 0.35     # ASSUMPTION: brass/steel tip + plastic tube ~ 35 % of solid steel
    m_cell_live = 19.3 / 2                                             # ASSUMPTION: half the 19.3 g cell moves (MFR AMF-225 mass)
    m_coil = 5.4                                                       # MFR AMF-02 coil mass (-013-013-03)
    m_axial = m_holder + m_refill + m_cell_live + m_coil
    bed = bed_parts()
    m_platen = C.mass_g(bed["platen_cfrp"], "cfrp")
    m_top = m_platen + C.mass_g(bed["paper"], "print") * 0.64 + C.mass_g(bed["underlay"], "glass")
    head = {k: v for k, v in {**cartridge_parts(), **head_fixed_parts()}.items()}
    mat = {"holder": "al", "guide_leaves": "steel", "cartridge_frame": "al", "arc_carriage": "al", "hall_bracket": "print",
           "arc_frame": "al", "hall_magnet": "ndfeb", "hall_sensor_DRV5055": "print", "vcm_coil": "copper", "vcm_housing": "steel",
           "axial_cell_LSB200": "al"}
    m_head = sum(C.mass_g(v, mat[k]) for k, v in head.items() if k not in ("vcm_coil", "vcm_housing", "axial_cell_LSB200"))
    m_head += 19.3 + 5.4 + 7.6                                         # MFR AMF-225 cell, AMF-02 coil and body
    return {
        "guide_k_per_leaf_N_per_m": round(k1, 2), "guide_k_total_N_per_m": round(k, 2),
        "guide_stress_at_1p5mm_MPa": round(s15 / 1e6, 1),
        "guide_force_at_1p5mm_mN": round(k * 1.5e-3 * 1e3, 1),
        "guide_note": "fixed-guided leaves, E 200 GPa ASSUMPTION; the guide force k_g (s - s_free) reaches 38 mN at 1.5 mm, a quarter "
                      "of F_c = 0.15 N, so the slide s is measured (Hall) and subtracted, and k_g, s_free are calibrated in situ "
                      "(rig.calib.fit_guide_stiffness)",
        "axial_moving_mass_g": round(m_axial, 1),
        "axial_suspension_mode_Hz": round(C.mode_hz(k, m_axial * 1e-3), 2),
        "inertial_error_mN_per_m_s2": round(m_axial, 2),
        "platen_mass_g": round(m_platen, 1), "plate_top_mass_g": round(m_top, 1),
        "plate_mode_Hz_2N_version": round(C.mode_hz(2.0 / 0.1e-3, m_top * 1e-3), 0),
        "plate_mode_Hz_10N_version": round(C.mode_hz(10.0 / 0.1e-3, m_top * 1e-3), 0),
        "plate_mode_note": "k from the rated displacement 0.1 mm at full scale (MFR AMF-224), mass of platen + underlay + paper "
                           "(glass underlay shown; a pad or elastomer is lighter); the sensor's own top half is not included, so "
                           "the real mode is lower: measure it (tap test, EXP-T01 step 0)",
        "eccentric_error_pctFS_at_area_corner": round(0.5 * math.hypot(max(abs(v) for v in R["area_x"]), max(abs(v) for v in R["area_y"])) / 100.0, 3),
        "eccentric_note": "0.5 % FS per 100 mm eccentric load (MFR AMF-224) scaled to the writing-area corner; the in-situ plate "
                          "calibration (rig.calib.fit_plate with position) removes most of it",
        "head_payload_g": round(m_head, 0),
        "head_payload_note": "cartridge + arc + adapter, aluminium/steel densities ASSUMPTION; the Core One+ page lists no payload "
                             "(MFR AMF-231): check the head's acceleration settings with this mass before the friction runs",
    }


def drawing(theta, path):
    import numpy as np
    fig, (ax, ax2) = C.new_figure(2, size=(13.0, 6.6), width_ratios=[1.45, 1.0])
    mv = posed(theta)
    bed = bed_parts()
    from stabpen import plotstyle as ps
    for k, v in bed.items():
        C.project(ax, v, "xz", color=ps.MUTED if k == "printer_bed_envelope" else ps.INK2, lw=0.6)
    for k, v in mv.items():
        col = ps.SERIES[0] if k in ("refill", "ball", "holder") else (ps.SERIES[1] if k.startswith("vcm") else
                                                                    ps.SERIES[2] if k == "axial_cell_LSB200" else ps.INK2)
        C.project(ax, v, "xz", color=col, lw=0.7 if k != "arc_frame" else 0.5)
    for th in (35.0, 75.0):
        m2 = posed(th)
        for k in ("refill", "cartridge_frame", "vcm_housing"):
            C.project(ax, m2[k], "xz", color=ps.MUTED, lw=0.4, alpha=0.6)
    lift = R["ball_d"] / 2
    th = math.radians(theta)

    def pt(s_ax, off=0.0):
        """Point on the pen axis at distance s_ax from the ball centre, offset `off` along local +x."""
        return (-s_ax * math.cos(th) + off * math.sin(th), s_ax * math.sin(th) + off * math.cos(th) + lift)

    aa = np.radians(np.linspace(R["arc_a"][0], R["arc_a"][1], 50))
    ax.plot(-R["arc_r"] * np.cos(aa), R["arc_r"] * np.sin(aa) + lift, color=ps.SERIES[3], lw=0.8, ls="--")
    C.label(ax, (-R["arc_r"] * math.cos(math.radians(70)), R["arc_r"] * math.sin(math.radians(70)) + lift),
            f"tilt arc R{R['arc_r']:.0f} about the ball centre;\nholes at 35/50/65/75 deg + slot", (-165, 118))
    C.label(ax, (25, -1.0), "paper, underlay, 1.5 mm CFRP platen\n80 x 60 mm on the K3D40 plate (40x40x20)", (65, -47))
    C.label(ax, pt(R["cell_z0"] + R["cell"][2] / 2, -R["cell"][0] / 2), "LSB200 in-line cell", (-160, 62))
    zc = R["cell_z0"] + R["cell"][2] + 0.5 + R["coil_L"] + R["vcm_L"] / 2
    C.label(ax, pt(zc, -R["vcm_d"] / 2), "LVCM-013-013-03 sets F_c\n(current mode)", (-165, 30))
    C.label(ax, pt(sum(R["leaf"]["z"]) / 2, R["holder_od"] / 2 + R["leaf"]["L"] / 2), "leaf-guided holder", (40, 70))
    C.label(ax, (0, R["head_z"] + R["head_plate"][2] + lift), "adapter to the CoreXY head (moves x, y)", (20, 130))
    zbot = -R["paper"][2] - R["underlay_t"] - R["platen"][2] - R["k3d40"][2]
    C.dim(ax, (45, 0), (45, zbot), f"{-zbot:.1f}", off=0, text_off=1.5)
    ax.text(49, zbot / 2, "paper top to\nplate base", fontsize=7, color=ps.INK2, va="center")
    ax.plot([-60, 0], [0, 0], color=ps.INK, lw=0.6, ls=":")
    rr = 28
    ax.plot(-rr * np.cos(np.linspace(0, math.radians(theta), 30)), rr * np.sin(np.linspace(0, math.radians(theta), 30)) + lift,
            color=ps.INK, lw=0.6)
    ax.text(-rr - 16, 5, f"theta {theta:.0f} deg\n(35 and 75 in grey)", fontsize=7.5, color=ps.INK)
    ax.set_xlim(-175, 130)
    ax.set_ylim(-50, 140)
    ax.set_xlabel("x (mm), page frame")
    ax.set_ylabel("z (mm), paper top = 0")
    ax.set_title("R9 contact head on the printer frame: side view", loc="left", fontsize=10)
    # detail: cartridge in its own frame (axis vertical)
    cp = {**refill_parts(), **cartridge_parts()}
    for k, v in cp.items():
        if k in ("arc_carriage",):
            continue
        col = ps.SERIES[0] if k in ("refill", "ball", "holder") else (ps.SERIES[1] if k.startswith("vcm") else
                                                                    ps.SERIES[2] if k == "axial_cell_LSB200" else ps.INK2)
        C.project(ax2, v, "xz", color=col, lw=0.7)
    lf = R["leaf"]
    x0 = R["holder_od"] / 2
    C.dim(ax2, (x0, lf["z"][0]), (x0 + lf["L"], lf["z"][0]), f"leaf {lf['L']:.0f} x {lf['b']:.0f} x {lf['t']:.2f}", off=-6.0)
    C.dim(ax2, (-9, lf["z"][0]), (-9, lf["z"][1]), f"{lf['z'][1] - lf['z'][0]:.0f}", off=0)
    zc0 = R["cell_z0"]
    C.dim(ax2, (-12, zc0), (-12, zc0 + R["cell"][2]), "19.05", off=0)
    C.dim(ax2, (-18, 0), (-18, R["holder_z"][0]), f"{R['holder_z'][0]:.0f} ball to collet", off=0)
    zt = zc0 + R["cell"][2] + 0.5 + R["coil_L"] + R["vcm_L"] + R["end_t"]
    C.dim(ax2, (46, 0), (46, zt), f"{zt:.0f} cartridge", off=0)
    ax2.text(12, 12, "D1 refill, ball down", fontsize=7.5, color=ps.INK)
    C.label(ax2, (x0 + 12, lf["z"][1]), "2 parallel leaves\n(axial guide, 26 N/m)", (18, 55))
    C.label(ax2, (6, zc0 + 9), "LSB200", (20, zc0 + 22))
    C.label(ax2, (5, zc0 + 21), "VCM coil + housing", (18, zt + 6))
    C.label(ax2, (0.0, R["hall_z"] - 1.5), "Hall slide sensor (DRV5055)", (14, 6))
    ax2.set_xlim(-30, 62)
    ax2.set_ylim(-4, zt + 14)
    ax2.set_xlabel("local x (mm)")
    ax2.set_ylabel("along the pen axis (mm)")
    ax2.set_title("Refill cartridge (local frame)", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; commercial parts as data-sheet envelopes; not built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=50.0)
    a = ap.parse_args()
    parts = {**bed_parts(), **posed(a.theta)}
    colors = {"paper": "white", "platen_cfrp": "black", "force_plate_K3D40": "gray", "refill": "blue", "ball": "blue",
              "axial_cell_LSB200": "green", "vcm_housing": "orange", "vcm_coil": "orange"}
    step = C.save_assembly(NAME, parts, colors)
    hits, zmins = checks()
    summary = {"parameters_mm": R, "theta_deg": a.theta, "step": os.path.relpath(step, C.ROOT),
               "interference_with_bed": hits, "clearance_by_theta": zmins, "calc": calcs(),
               "notes": ["only the ball may touch the paper: interference_with_bed must be empty for theta 35-75 over the "
                         "writing area (ball centre x -29..33, y -26..26 mm); the -x side keeps 6 mm from the clamp because the "
                         "pen leans that way",
                         "cartridge swaps: G2/capless refills (6 mm) take a second collet; the leaf guide and cell are unchanged",
                         "the arc is one-sided (behind the pen, y -20..-14); the carriage clamps through the indexed holes or a slot",
                         "LSB200 orientation (load axis along 19.05 mm) is an ASSUMPTION to check on drawing FI1455"]}
    C.write_summary(NAME, "proposed design (R9 contact head concept geometry)", summary)
    drawing(a.theta, os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps({"interference_with_bed": hits, "clearance_by_theta": zmins, "calc": calcs()}, indent=1))


if __name__ == "__main__":
    main()
