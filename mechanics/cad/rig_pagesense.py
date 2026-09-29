#!/usr/bin/env python3
"""R10 page-relative sensing rig (build gate before any closed-loop claim): tilt-roll-height fixture (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry; die, lens and micrometre-stage envelopes are ASSUMPTIONS).

What it does: holds a page sensor in a mock nose (the front of the pen, printed from the candidate's CAD, carrying
the die, lens and mirror as in the pen) and turns it about the virtual ball point: tilt 35-75 deg on an arc centred
on that point, roll +-20 deg about the virtual pen axis in a ring, height by the printer's Z (coarse) and a
micrometre Z (fine).  The CoreXY head moves the fixture over paper on a glass platen with LM13 encoders as truth
(standard build); the reference build fixes the fixture on a bridge and moves the paper on two stacked Zaber
X-LDM110C stages (MFR AMF-229).  Far-field boards (PAA5100JE, 15-35 mm, MFR OPT-90) mount on a flat plate
instead of the mock nose.

Outputs (results/rig/cad/): rig_pagesense_assembly.step, drawing_rig_pagesense.png, rig_pagesense_summary.json.
Run: python3 mechanics/cad/rig_pagesense.py [--theta 50]
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

NAME = "rig_pagesense"
R = dict(
    # mock nose (pen24 class front: cone r 3 -> 12 over s 4-32, then the 24 mm sleeve to s 55; ASSUMPTION)
    nose=(3.0, 4.0, 12.0, 32.0), sleeve_to=55.0, wall=1.2,
    # sensor envelope inside the nose, at the bottom behind the tip (die + lens + mirror, ASSUMPTION)
    die=(8.0, 7.0, 3.0), die_s=16.0, lens_d=3.0, lens_h=2.0,
    # roll ring and arc (centred on the virtual ball point)
    ring=(42.0, 24.4, 10.0), ring_s=45.0, arc_r=45.0, arc_w=12.0, arc_t=5.0, arc_y=-32.0, arc_a=(30.0, 88.0),
    # mode A: bare sensor sled, optical axis through the arc centre (die, lens envelopes ASSUMPTION)
    sled=(14.0, 12.0, 3.0), h_range=(1.5, 4.5), alpha_A=(60.0, 70.0, 80.0, 88.0),
    # micrometre Z (25 mm class manual stage envelope, ASSUMPTION) and the head adapter plate
    zstage=(40.0, 40.0, 20.0), head_z=120.0, head_plate=(110.0, 60.0, 6.0),
    # bed: paper on a 200 x 150 x 5 mm float-glass platen
    paper=(190.0, 140.0, 0.1), glass=(200.0, 150.0, 5.0),
    theta_range=(35.0, 75.0), roll_range=(-20.0, 20.0), dz_range=(0.0, 3.0),
)


def nose_parts():
    """Local pen frame: virtual ball point at the origin, axis +Z."""
    r0, s0, r1, s1 = R["nose"]
    w = R["wall"]
    cone_o = C.cone(r0, r1, s0, s1)
    cone_i = C.cone(max(r0 - w, 0.5), r1 - w, s0 - 0.01, s1 + 0.01)
    sleeve = C.tube(2 * r1, 2 * (r1 - w), s1, R["sleeve_to"])
    nose = cone_o.cut(cone_i).union(sleeve)
    # the sensor sits against the bottom wall (local -x side faces the paper after tilt)
    dx, dy, dzz = R["die"]
    s = R["die_s"]
    r_at = r0 + (s - s0) * (r1 - r0) / (s1 - s0)
    die = C.box(dzz, dy, dx, (-(r_at - w - dzz / 2 - 0.3), 0, s))
    lens = (C.cq.Workplane("YZ").workplane(offset=-(r_at - w - 0.2)).center(0, s).circle(R["lens_d"] / 2)
            .extrude(-R["lens_h"] + 0.8))
    window = (C.cq.Workplane("YZ").workplane(offset=-(r_at + 1.0)).center(0, s).circle(R["lens_d"] / 2 + 0.3)
              .extrude(w + 2.0))
    nose = nose.cut(window)
    return {"mock_nose": nose, "sensor_die": die, "sensor_lens": lens}


def sled_parts(h: float):
    """Mode A (EXP-T04): bare sensor on a sled; local +Z is the optical axis, the look point at the origin and the
    lens face at distance h along the axis; the arc angle alpha sets the obliquity (90 - alpha deg)."""
    dx, dy, dzz = R["die"]
    lens = C.cyl(R["lens_d"], h, h + R["lens_h"])
    die = C.box(dx, dy, dzz, (0, 0, h + R["lens_h"] + dzz / 2))
    sx, sy, sz = R["sled"]
    z0 = h + R["lens_h"] + dzz
    sled = C.box(sx, sy, sz, (0, 0, z0 + sz / 2)).union(C.box(8.0, 8.0, R["ring_s"] - z0 - sz, (0, 0, (R["ring_s"] + z0 + sz) / 2)))
    return {"sled_lens": lens, "sled_die": die, "sled": sled}


def ring_parts():
    od, idd, wd = R["ring"]
    s = R["ring_s"]
    ring = C.tube(od, idd, s - wd / 2, s + wd / 2)
    y_face = R["arc_y"] + R["arc_t"]
    car = C.box(12.0, (-od / 2) - y_face + 2.0, 12.0, (0, (y_face - od / 2) / 2, s))
    return {"roll_ring": ring, "arc_carriage": car}


def head_parts():
    ri, ro = R["arc_r"] - R["arc_w"] / 2, R["arc_r"] + R["arc_w"] / 2
    arc = C.sector_xz(ri, ro, R["arc_a"][0], R["arc_a"][1], R["arc_t"], R["arc_y"])
    yt = R["arc_y"] + R["arc_t"] / 2
    hz = R["head_z"]
    zs = R["zstage"]
    z_bot_stage = hz - zs[2]
    a1 = math.radians(R["arc_a"][1])
    x_hi, z_hi = -R["arc_r"] * math.cos(a1), R["arc_r"] * math.sin(a1)
    hang_hi = C.box(10.0, R["arc_t"], z_bot_stage - z_hi, (x_hi, yt, (z_bot_stage + z_hi) / 2))
    a0 = math.radians(R["arc_a"][0])
    x_lo, z_lo = -ro * math.cos(a0) + 5.0, ro * math.sin(a0) - 3.0
    hang_lo = C.box(10.0, R["arc_t"], z_bot_stage - z_lo, (x_lo, yt, (z_bot_stage + z_lo) / 2))
    bar = C.box(abs(x_hi - x_lo) + 10.0, 30.0, 6.0, ((x_hi + x_lo) / 2, yt + 12.5, z_bot_stage - 3.0))
    zstage = C.box(*zs, ((x_hi + x_lo) / 2, yt + 12.5, hz - zs[2] / 2))
    px, py, pz = R["head_plate"]
    plate = C.box(px, py, pz, ((x_hi + x_lo) / 2 + 20.0, 0, hz + pz / 2))
    return {"tilt_arc": arc.union(hang_hi).union(hang_lo).union(bar), "z_micrometre_stage": zstage, "head_plate": plate}


def bed_parts():
    zp = -R["paper"][2]
    gx, gy, gz = R["glass"]
    return {"paper": C.box(*R["paper"], (0, 0, zp / 2)), "glass_platen": C.box(gx, gy, gz, (0, 0, zp - gz / 2))}


def posed(theta, roll_deg=0.0, dz=0.0):
    out = {}
    for k, v in nose_parts().items():
        out[k] = C.tilt(C.roll(v, roll_deg), theta).translate((0, 0, dz))
    for k, v in ring_parts().items():
        out[k] = C.tilt(v, theta).translate((0, 0, dz))
    for k, v in head_parts().items():
        out[k] = v.translate((0, 0, dz))
    return out


def nose_min_dz(theta):
    """CALC: lift of the virtual ball point needed for the nose cone to clear the paper (cone line from (s0, r0))."""
    r0, s0, r1, s1 = R["nose"]
    t = math.radians(theta)
    k = (r1 - r0) / (s1 - s0)
    zs = [s * math.sin(t) - (r0 + (s - s0) * k) * math.cos(t) for s in (s0, s1)]
    return max(0.0, -min(zs))


def posed_sled(alpha, h, roll_deg=0.0):
    out = {}
    for k, v in sled_parts(h).items():
        out[k] = C.tilt(C.roll(v, roll_deg), alpha)
    for k, v in ring_parts().items():
        out[k] = C.tilt(v, alpha)
    out.update(head_parts())
    return out


def checks_sled():
    bed = bed_parts()
    hits, rows = [], []
    for al in R["alpha_A"]:
        for h in R["h_range"]:
            for rl in (R["roll_range"][0], 0.0, R["roll_range"][1]):
                mv = posed_sled(al, h, rl)
                for r in C.pair_clearances(mv, bed):
                    r.update({"alpha": al, "h": h, "roll": rl})
                    hits.append(r)
            mv = posed_sled(al, h)
            rows.append({"alpha_deg": al, "obliquity_deg": round(90.0 - al, 1), "h_mm": h,
                         "lens_lowest_point_mm": round(C.zmin(mv["sled_lens"]), 2),
                         "sled_lowest_point_mm": round(min(C.zmin(mv[k]) for k in ("sled", "sled_die")), 2)})
    return hits, rows


def checks():
    bed = bed_parts()
    hits, rows = [], []
    for th in (35.0, 50.0, 65.0, 75.0):
        dz0 = round(nose_min_dz(th) + 0.3, 2)
        for dz in (dz0, R["dz_range"][1]):
            for rl in (R["roll_range"][0], 0.0, R["roll_range"][1]):
                mv = posed(th, rl, dz)
                for r in C.pair_clearances(mv, bed):
                    r.update({"theta": th, "roll": rl, "dz": dz})
                    hits.append(r)
                if rl == 0.0:
                    rows.append({"theta": th, "dz_mm": dz, "lens_lowest_point_mm": round(C.zmin(mv["sensor_lens"]), 2),
                                 "nose_lowest_point_mm": round(C.zmin(mv["mock_nose"]), 2),
                                 "fixture_lowest_other_mm": round(min(C.zmin(v) for k, v in mv.items()
                                                                      if k not in ("mock_nose", "sensor_lens", "sensor_die")), 1)})
    return hits, rows


def drawing(theta, path):
    import numpy as np
    from stabpen import plotstyle as ps
    fig, (ax, ax2) = C.new_figure(2, size=(13.0, 6.4), width_ratios=[1.25, 1.0])
    dz = nose_min_dz(theta) + 0.3
    mv = posed(theta, 0.0, dz)
    for k, v in bed_parts().items():
        C.project(ax, v, "xz", color=ps.INK2, lw=0.5)
    col = {"mock_nose": ps.SERIES[0], "sensor_die": ps.SERIES[1], "sensor_lens": ps.SERIES[1], "roll_ring": ps.SERIES[2]}
    for k, v in mv.items():
        C.project(ax, v, "xz", color=col.get(k, ps.INK2), lw=0.7)
    for th in (35.0, 75.0):
        m2 = posed(th, 0.0, nose_min_dz(th) + 0.3)
        C.project(ax, m2["mock_nose"], "xz", color=ps.MUTED, lw=0.4, alpha=0.6)
    aa = np.radians(np.linspace(R["arc_a"][0], R["arc_a"][1], 40))
    ax.plot(-R["arc_r"] * np.cos(aa), R["arc_r"] * np.sin(aa) + dz, color=ps.SERIES[3], lw=0.8, ls="--")
    th = math.radians(theta)
    C.label(ax, (-R["arc_r"] * math.cos(math.radians(70)), R["arc_r"] * math.sin(math.radians(70)) + dz),
            f"tilt arc R{R['arc_r']:.0f} about the virtual ball point", (-150, 100))
    s = R["ring_s"]
    C.label(ax, (-s * math.cos(th) - 21 * math.sin(th), s * math.sin(th) - 21 * math.cos(th)), "roll ring +-20 deg", (-150, 20))
    s = R["die_s"]
    C.label(ax, (-s * math.cos(th) - 8 * math.sin(th), s * math.sin(th) - 8 * math.cos(th) + dz),
            "die, lens and mirror in the\nmock nose (printed from the pen CAD)", (15, 45))
    C.label(ax, (0, R["head_z"] - 10), "micrometre Z (fine height)", (20, 100))
    C.label(ax, (60, -2.5), "paper on 5 mm float glass", (40, -25))
    ax.plot([-60, 0], [0, 0], color=ps.INK, lw=0.5, ls=":")
    rr = 22
    ax.plot(-rr * np.cos(np.linspace(0, th, 30)), rr * np.sin(np.linspace(0, th, 30)), color=ps.INK, lw=0.6)
    ax.text(-rr - 22, 4, f"theta {theta:.0f}\n(35, 75 grey)", fontsize=7.5, color=ps.INK)
    ax.set_xlim(-160, 110)
    ax.set_ylim(-35, 140)
    ax.set_xlabel("x (mm), page frame")
    ax.set_ylabel("z (mm), paper top = 0")
    ax.set_title("R10 page-sensor fixture on the CoreXY head: side view", loc="left", fontsize=10)
    # detail: nose in its own frame (axis vertical), with the window and die
    for k, v in nose_parts().items():
        C.project(ax2, v, "xz", color=col.get(k, ps.INK2), lw=0.7)
    for k, v in ring_parts().items():
        C.project(ax2, v, "xz", color=col.get(k, ps.INK2), lw=0.7)
    r0, s0, r1, s1 = R["nose"]
    C.dim(ax2, (-r1, s1 + 4), (r1, s1 + 4), f"{2 * r1:.0f} sleeve", off=0)
    C.dim(ax2, (16, 0), (16, R["die_s"]), f"{R['die_s']:.0f} to the window", off=0)
    C.dim(ax2, (26, 0), (26, R["ring_s"]), f"{R['ring_s']:.0f} to the ring", off=0)
    ax2.plot([-30, 30], [0, 0], color=ps.INK, lw=0.5, ls=":")
    ax2.text(-29, 1.0, "virtual ball point (arc centre)", fontsize=7, color=ps.INK2)
    ax2.set_xlim(-32, 40)
    ax2.set_ylim(-4, 62)
    ax2.set_xlabel("local x (mm), -x faces the paper")
    ax2.set_ylabel("along the virtual pen axis (mm)")
    ax2.set_title("Mock nose with the sensor window (local frame)", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; die, lens and stage envelopes assumed; not built")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=50.0)
    a = ap.parse_args()
    dz = nose_min_dz(a.theta) + 0.3
    parts = {**bed_parts(), **posed(a.theta, 0.0, dz)}
    step = C.save_assembly(NAME, parts, {"mock_nose": "blue", "sensor_die": "orange", "glass_platen": "lightblue"})
    hits, rows = checks()
    hits_a, rows_a = checks_sled()
    sled_step = C.save_assembly(NAME + "_sled", {**bed_parts(), **posed_sled(80.0, 2.4)}, {"sled_die": "orange"})
    summary = {"parameters_mm": R, "theta_deg": a.theta, "step": os.path.relpath(step, C.ROOT),
               "step_sled": os.path.relpath(sled_step, C.ROOT),
               "mode_A_sled": {"interference_with_bed": hits_a, "heights": rows_a,
                               "note": "EXP-T04 sensor physics: obliquity 2-30 deg, lens heights 1.5-4.5 mm and roll +-20 deg "
                                       "set independently"},
               "mode_B_nose": {"interference_with_bed": hits, "heights": rows,
                               "note": "EXP-J04/J10 nose-specific: the lens height follows from the nose design; with this "
                                       "generic nose (window 16 mm behind the tip) it is 3.3-15 mm over 35-75 deg, which is "
                                       "why the pen needs folded optics near the tip (docs/revJ_design.md)"},
               "min_lift_for_nose_clearance_mm": {str(t): round(nose_min_dz(t), 2) for t in (35.0, 50.0, 65.0, 75.0)},
               "calc": {"head_travel_note": "the printer's XY range (build volume 250 x 220 mm, MFR AMF-231) covers the 190 x "
                                            "140 mm paper; strokes of 100 mm at up to 100 mm/s are the EXP-T04 course",
                        "reference_build": "fixture on a bridge; paper on two stacked Zaber X-LDM110C (110 mm travel, 1 um "
                                           "unidirectional accuracy, 1 nm count, 24.5 m/s^2 max acceleration, 2.29 kg "
                                           "moving mass; USD 9,255 each; MFR AMF-229)",
                        "far_field_boards": "PAA5100JE (PIM573, 15-35 mm, 242 fps, MFR OPT-90) on a flat plate at 15-35 mm "
                                            "set by the printer Z; no clearance issue at those heights"},
               "notes": ["the virtual ball point is the arc centre; dz lifts it above the paper; the nose must clear the "
                         "paper (min lift per theta above), and the lens height follows from the nose design",
                         "roll +-20 deg is about the virtual pen axis; the Rev J window's base roll (24 deg round from the "
                         "bottom, docs/revJ_design.md) is printed into the nose insert"]}
    C.write_summary(NAME, "proposed design (R10 page-sensor fixture concept geometry)", summary)
    drawing(a.theta, os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps({"mode_B": {"hits": hits, "heights": rows}, "mode_A": {"hits": hits_a, "heights": rows_a},
                      "min_lift": summary["min_lift_for_nose_clearance_mm"]}, indent=1))


if __name__ == "__main__":
    main()
