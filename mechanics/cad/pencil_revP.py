#!/usr/bin/env python3
"""Parametric CAD concept of the pencil-class pen, Rev P0 (CadQuery 2.x).

Evidence status: PROPOSED DESIGN (dimensioned concept).  Nominal dimensions,
rigid parts; the fit checks are geometric only.  Envelope, skid, nib and
bender values come from config/pencil.yaml; the rest are packaging choices
made here and listed in P.

Datums as Rev A (mechanics/cad/pen_revA.py): origin at the ball centre with
the nib in contact at the design tilt (50 deg), z along the barrel axis from
the nib toward the cap, x toward the flat (roll datum).  Millimetres.

Architecture (docs/pencil_concept.md):
  * skid ring on the nose carries the user's writing force; the refill is
    pressed onto the paper by a soft spring behind it and slides axially;
  * the refill pivots in a flexure gimbal at z_gimbal and is moved at a
    front collar by piezo benders beside it, each through a leaf flexure
    that is stiff in the bender's drive direction and compliant across it;
  * variant "L": two 3.5 mm wide plates (x and y) in an L; variant "Q": four
    2.6 mm plates, a push-pull pair per axis;
  * 3-D Hall sensor in the nose reads a magnet on the collar (stage position);
    a second Hall on the board front reads the refill's rear magnet (axial
    slide: pen-down and protrusion);
  * rigid-flex board, 6.5 mm cylindrical cell, plastic rear cap (antenna).
Outputs (results/cad/): pencil_revP{L,Q}_assembly.step, _summary.json (mass,
centre of mass, fit checks) and _viewer.json (primitives for the 3-D page).
Run: python3 mechanics/cad/pencil_revP.py [--variant L|Q]
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
from stabpen import params as sp_params  # noqa: E402
from stabpen import provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")
PENCIL = os.path.join(ROOT, "config", "pencil.yaml")


def parameters(variant: str) -> dict:
    pc = sp_params.load(PENCIL)
    mm = 1e3
    P = dict(
        od=pc["envelope.od"] * mm, L_total=pc["envelope.length"] * mm, wall=pc["envelope.wall"] * mm,
        nose_L=pc["envelope.nose_length"] * mm,
        # skid: contact ring radius r_s; the nib must protrude p >= r_s cot(theta) (theta 35-75 deg)
        skid_r=pc["skid.ring_radius"] * mm, skid_w=0.4, theta_design=50.0, theta_min=pc["skid.theta_min"],
        # refill: ISO 12757-2 D1 format (verify against purchased samples)
        refill_d=2.35, refill_L=67.0, cone_L=5.0, ball_d=0.7, socket_d=1.0,
        # stage (bender thickness and free length from config/pencil.yaml; widths per variant)
        plate_t=pc["stage.bender_thickness"] * mm, plate_free=pc["stage.bender_free_length"] * mm, plate_clamp=8.0,
        plate_d=2.15,            # plate mid-plane distance from the axis
        tip_sweep=0.40,          # bender tip travel to the stops (+/-)
        nib_travel=0.40,         # nib travel to the stops (+/-); usable correction 0.30 (stage.travel_nib)
        collar_z0=15.0, collar_L=3.0, collar_od=4.0,
        z_plate_tip=19.0, z_gimbal=60.0,
        spring_L=10.0, spring_od=2.4,
        pcb_L=42.0, pcb_w=pc["electronics.board_width"] * mm, pcb_t=0.6, comp_h=1.0,
        batt_d=pc["battery.diameter"] * mm, batt_L=pc["battery.length"] * mm,
        cap_L=5.0, clear_min=0.10,
    )
    P["plate_w"], P["n_plates"] = {"L": (3.5, 2), "Q": (2.6, 4)}[variant]
    P["r_bore"] = P["od"] / 2 - P["wall"]
    P["z_skid"] = P["skid_r"] / math.tan(math.radians(P["theta_design"]))     # ring plane above the ball, in contact
    P["plate_L"] = P["plate_free"] + P["plate_clamp"]
    P["z_clamp0"] = P["z_plate_tip"] + P["plate_free"]
    P["z_clamp1"] = P["z_plate_tip"] + P["plate_L"]
    P["z_spring0"] = P["refill_L"]
    P["z_bulkhead"] = P["refill_L"] + P["spring_L"]
    P["z_pcb0"] = P["z_bulkhead"] + 1.0
    P["z_batt0"] = P["z_pcb0"] + P["pcb_L"] + 1.0
    P["z_cap0"] = P["L_total"] - P["cap_L"]
    P["lever"] = P["z_gimbal"] / (P["z_gimbal"] - (P["collar_z0"] + P["collar_L"] / 2))
    return P


DENS = {  # g/mm^3
    "PA_GF30": 1.36e-3, "POM_PTFE": 1.50e-3, "Ti6Al4V": 4.43e-3, "PZT_multilayer": 7.80e-3,
    "stainless": 8.00e-3, "brass_refill_with_ink": 3.0e-3, "NdFeB": 7.50e-3, "FR4_populated": 2.4e-3,
    "Li_ion_cyl": 2.6e-3, "PC": 1.20e-3, "spring_steel": 7.85e-3, "sensor_pkg": 2.4e-3,
}


# ------------------------------------------------------------------ helpers
def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def tube(r_out, r_in, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(r_out).circle(r_in).extrude(z1 - z0)


def box(sx, sy, sz, cx, cy, cz):
    return cq.Workplane("XY").box(sx, sy, sz).translate((cx, cy, cz))


def revolve(pts):
    """Solid of revolution about z from an (r, z) polygon."""
    return cq.Workplane("XZ").polyline(pts).close().revolve(360.0, (0, 0, 0), (0, 1, 0))


# ------------------------------------------------------------------ parts
def barrel(P):
    ro, ri, zs = P["od"] / 2, P["r_bore"], P["z_skid"] + P["skid_w"]
    r_tip_o, r_tip_i = P["skid_r"] + 0.35, P["skid_r"] - 0.05
    z_nose1 = zs + P["nose_L"]
    outer = [(r_tip_o, zs), (ro, z_nose1), (ro, P["z_cap0"]), (0.0, P["z_cap0"]), (0.0, zs)]
    inner = [(r_tip_i, zs - 0.01), (ri, z_nose1 - 0.5), (ri, P["z_cap0"] + 0.01), (0.0, P["z_cap0"] + 0.01),
             (0.0, zs - 0.01)]
    return revolve(outer).cut(revolve(inner))


def nose_inner_r(P, z):
    zs = P["z_skid"] + P["skid_w"]
    r0, r1, z1 = P["skid_r"] - 0.05, P["r_bore"], zs + P["nose_L"] - 0.5
    return r0 + (r1 - r0) * min(max((z - zs) / (z1 - zs), 0.0), 1.0)


def skid_ring(P):
    return tube(P["skid_r"] + 0.35, P["skid_r"] - 0.15, P["z_skid"], P["z_skid"] + P["skid_w"])


def rear_cap(P):
    ro = P["od"] / 2
    return revolve([(ro, P["z_cap0"]), (ro, P["L_total"] - 1.0), (ro - 1.0, P["L_total"]), (0.0, P["L_total"]),
                    (0.0, P["z_cap0"])]).cut(cyl(ro - 0.6, P["z_cap0"], P["L_total"] - 0.8))


def refill(P):
    r = P["refill_d"] / 2
    ball = cq.Workplane("XY").sphere(P["ball_d"] / 2)
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(P["socket_d"] / 2, r, P["cone_L"] - 0.3,
                                                   pnt=cq.Vector(0, 0, 0.3), dir=cq.Vector(0, 0, 1)))
    return ball.union(cone).union(cyl(r, P["cone_L"], P["refill_L"]))


def collar(P):
    z0, z1 = P["collar_z0"], P["collar_z0"] + P["collar_L"]
    c = tube(P["collar_od"] / 2, P["refill_d"] / 2 + 0.05, z0, z1)
    # flat on +x for the stage-sensing magnet
    return c.cut(box(1.0, 5.0, P["collar_L"] + 0.2, P["collar_od"] / 2 + 0.5 - 0.3, 0, (z0 + z1) / 2))


def collar_magnet(P):
    zc = P["collar_z0"] + P["collar_L"] / 2
    return box(0.6, 1.0, 1.0, P["collar_od"] / 2 - 0.3 + 0.3, 0.0, zc)


def plates(P):
    """Bender plates: (name, solid, drive axis unit vector, material)."""
    d, t, w = P["plate_d"], P["plate_t"], P["plate_w"]
    z0, z1 = P["z_plate_tip"], P["z_clamp1"]
    zc, L = (z0 + z1) / 2, z1 - z0
    out = []
    if P["n_plates"] == 2:
        off = 0.5 * w - 1.2         # lateral offset of each plate's centre away from the L corner
        out.append(("bender_x", box(t, w, L, -d, off, zc), (1, 0, 0)))
        out.append(("bender_y", box(w, t, L, off, -d, zc), (0, 1, 0)))
    else:
        out.append(("bender_x_neg", box(t, w, L, -d, 0.0, zc), (1, 0, 0)))
        out.append(("bender_x_pos", box(t, w, L, d, 0.0, zc), (1, 0, 0)))
        out.append(("bender_y_neg", box(w, t, L, 0.0, -d, zc), (0, 1, 0)))
        out.append(("bender_y_pos", box(w, t, L, 0.0, d, zc), (0, 1, 0)))
    return out


def leaves(P, plate_list):
    """Decoupling leaf flexures from each bender tip to the collar (25 um stainless, drawn 0.1 mm)."""
    z0, z1 = P["collar_z0"] + P["collar_L"] - 1.0, P["z_plate_tip"] + 0.5
    out = []
    for name, sol, ax in plate_list:
        bb = sol.val().BoundingBox()
        cx, cy = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
        # leaf plane contains the drive axis and z; thin across the other in-plane axis
        if ax[0]:
            out.append((name.replace("bender", "leaf"), box(abs(cx) - P["collar_od"] / 2 + 0.3, 0.1, z1 - z0,
                                                             math.copysign((abs(cx) + P["collar_od"] / 2 - 0.3) / 2, cx),
                                                             0.0, (z0 + z1) / 2)))
        else:
            out.append((name.replace("bender", "leaf"), box(0.1, abs(cy) - P["collar_od"] / 2 + 0.3, z1 - z0,
                                                             0.0, math.copysign((abs(cy) + P["collar_od"] / 2 - 0.3) / 2, cy),
                                                             (z0 + z1) / 2)))
    return out


def clamp_block(P):
    blk = tube(P["r_bore"] - 0.05, P["refill_d"] / 2 + 0.45, P["z_clamp0"], P["z_clamp1"])
    return blk


def gimbal(P):
    z = P["z_gimbal"]
    disc = tube(P["r_bore"] - 0.05, 1.9, z - 0.05, z + 0.05)            # etched cross-strip flexure (envelope)
    hub = tube(1.9, P["refill_d"] / 2 + 0.02, z - 1.0, z + 1.0)         # PTFE-lined slide bushing
    return disc, hub


def nib_spring(P):
    return tube(P["spring_od"] / 2, P["spring_od"] / 2 - 0.15, P["z_spring0"] + 1.0, P["z_bulkhead"])


def rear_plug(P):
    return cyl(P["refill_d"] / 2, P["refill_L"], P["refill_L"] + 1.0), cyl(0.5, P["refill_L"] + 0.2, P["refill_L"] + 0.9)


def bulkhead(P):
    return tube(P["r_bore"] - 0.05, 0.0 + 1e-3, P["z_bulkhead"], P["z_bulkhead"] + 0.8)


def pcb(P):
    z0, z1 = P["z_pcb0"], P["z_pcb0"] + P["pcb_L"]
    board = box(P["pcb_w"], P["pcb_t"], z1 - z0, 0, 0, (z0 + z1) / 2)
    comps = box(P["pcb_w"] - 0.4, 2 * P["comp_h"] + P["pcb_t"], z1 - z0 - 1.0, 0, 0, (z0 + z1) / 2).cut(board)
    return board, comps


def hall_nose(P):
    zc = P["collar_z0"] + P["collar_L"] / 2
    sweep = P["nib_travel"] / P["lever"]                          # collar travel at the nib stops
    x0 = P["collar_od"] / 2 + 0.3 + sweep + 0.15                  # sensor face beyond the magnet's swept position
    return box(0.6, 1.5, 1.5, x0 + 0.3, 0.0, zc), x0


def optics(P):
    z = P["collar_z0"] - 2.0
    r_in = nose_inner_r(P, z)
    return box(1.6, 0.7, 1.6, 0.0, -(r_in - 0.35), z)


def battery(P):
    return cyl(P["batt_d"] / 2, P["z_batt0"], P["z_batt0"] + P["batt_L"])


def build(P):
    fixed = {"barrel": (barrel(P), "PA_GF30"), "skid_ring": (skid_ring(P), "POM_PTFE"),
             "rear_cap": (rear_cap(P), "PC"), "clamp_block": (clamp_block(P), "Ti6Al4V"),
             "bulkhead": (bulkhead(P), "PC"), "battery": (battery(P), "Li_ion_cyl")}
    disc, hub = gimbal(P)
    fixed["gimbal_flexure"] = (disc, "stainless")
    board, comps = pcb(P)
    fixed["pcb"] = (board, "FR4_populated")
    fixed["pcb_components_envelope"] = (comps, "FR4_populated")
    hall, _ = hall_nose(P)
    fixed["hall_3d_nose"] = (hall, "sensor_pkg")
    fixed["optical_sensor"] = (optics(P), "sensor_pkg")
    pl = plates(P)
    benders = {n: (s, "PZT_multilayer") for n, s, _ax in pl}
    lvs = {n: (s, "stainless") for n, s in leaves(P, pl)}
    plug, smag = rear_plug(P)
    moving = {"refill_D1": (refill(P), "brass_refill_with_ink"), "collar": (collar(P), "Ti6Al4V"),
              "collar_magnet": (collar_magnet(P), "NdFeB"), "gimbal_hub": (hub, "PC"),
              "rear_plug": (plug, "PC"), "axial_magnet": (smag, "NdFeB"), "nib_spring": (nib_spring(P), "spring_steel")}
    return fixed, benders, lvs, moving, pl


def solid(wp):
    try:
        return wp.combine().val() if hasattr(wp, "combine") else wp
    except Exception:
        return wp.val()


def mass_table(groups):
    rows = []
    for gname, parts in groups.items():
        for name, (wp, mat) in parts.items():
            s = solid(wp)
            V, c = s.Volume(), s.Center()
            rows.append({"part": name, "group": gname, "material": mat, "volume_mm3": round(V, 2),
                         "mass_g": round(V * DENS[mat], 3), "com_z_mm": round(c.z, 2)})
    return rows


# ------------------------------------------------------------------ fit checks
def section_checks(P, pl):
    """2-D clearances (mm) at the bender station with the tips swept to the stops,
    and at the nose sensor station.  Positive = clearance."""
    rb = P["r_bore"]
    out = {}
    # bender plates: tip sweeps +/- tip_sweep along the drive axis
    rects = []
    for name, sol, ax in pl:
        bb = sol.val().BoundingBox()
        for s in (-1.0, 1.0):
            dx, dy = s * P["tip_sweep"] * ax[0], s * P["tip_sweep"] * ax[1]
            rects.append((name, s, bb.xmin + dx, bb.xmax + dx, bb.ymin + dy, bb.ymax + dy))
    # (a) plate corners to the bore wall
    worst = min(rb - math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) for _n, _s, x0, x1, y0, y1 in rects)
    out["plate_to_bore_mm"] = round(worst, 3)
    # (b) plate to plate (all sweep combinations)
    def gap(a, b):
        gx = max(a[2] - b[3], b[2] - a[3])
        gy = max(a[4] - b[5], b[4] - a[5])
        return max(gx, gy)
    pg = [gap(a, b) for i, a in enumerate(rects) for b in rects[i + 1:] if a[0] != b[0]]
    out["plate_to_plate_mm"] = round(min(pg), 3)
    # (c) plate to refill: relative sweep only along the plate's own drive axis is shared with the
    # refill (the plate drives it); across it the refill moves while the plate does not
    zt = P["z_plate_tip"]
    u_ref = P["nib_travel"] / P["lever"] * (P["z_gimbal"] - zt) / (P["z_gimbal"] - (P["collar_z0"] + P["collar_L"] / 2))
    rr = P["refill_d"] / 2
    worst_r = 1e9
    for name, sol, ax in pl:
        bb = sol.val().BoundingBox()
        inner = min(abs(bb.xmin), abs(bb.xmax)) if ax[0] else min(abs(bb.ymin), abs(bb.ymax))
        rel = P["tip_sweep"] - u_ref                # tip and refill move together along the drive axis
        worst_r = min(worst_r, inner - rel - (rr + 0.0))
    out["plate_to_refill_mm"] = round(worst_r, 3)
    out["refill_sweep_at_plate_tip_mm"] = round(u_ref, 3)
    # (d) nose: collar magnet to Hall face; collar to nose wall; refill cone to skid aperture at theta_min
    _h, x_face = hall_nose(P)
    zc = P["collar_z0"] + P["collar_L"] / 2
    mag_outer = P["collar_od"] / 2 + 0.3
    out["collar_magnet_to_hall_mm"] = round(x_face - (mag_outer + P["nib_travel"] / P["lever"]), 3)
    out["hall_outer_to_nose_wall_mm"] = round(nose_inner_r(P, zc) - (x_face + 0.6 + 0.75 * 0), 3)
    out["collar_to_nose_wall_mm"] = round(nose_inner_r(P, P["collar_z0"]) - (P["collar_od"] / 2 + P["nib_travel"] / P["lever"]), 3)
    p_max = P["skid_r"] / math.tan(math.radians(P["theta_min"]))
    zc_ap = p_max                                     # skid plane height above the ball at theta_min
    r_cone = P["socket_d"] / 2 + (P["refill_d"] / 2 - P["socket_d"] / 2) * min(max((zc_ap - 0.3) / (P["cone_L"] - 0.3), 0), 1)
    out["refill_cone_to_skid_aperture_at_theta_min_mm"] = round((P["skid_r"] - 0.15) - (r_cone + P["nib_travel"]), 3)
    # smallest ring radius that keeps clear_min at theta_min (the aperture is 0.15 mm inside the contact radius)
    r_req = P["skid_r"]
    for _ in range(200):
        pm = r_req / math.tan(math.radians(P["theta_min"]))
        rc = P["socket_d"] / 2 + (P["refill_d"] / 2 - P["socket_d"] / 2) * min(max((pm - 0.3) / (P["cone_L"] - 0.3), 0), 1)
        if (r_req - 0.15) - (rc + P["nib_travel"]) >= P["clear_min"]:
            break
        r_req += 0.01
    out["skid_ring_radius_required"] = round(r_req, 2)
    out["nib_protrusion_range_mm"] = [round(P["skid_r"] / math.tan(math.radians(75.0)), 3), round(p_max, 3)]
    # (e) board and cell in the bore
    out["pcb_diagonal_to_bore_mm"] = round(rb - math.hypot(P["pcb_w"] / 2, P["pcb_t"] / 2 + P["comp_h"]), 3)
    out["battery_to_bore_mm"] = round(rb - P["batt_d"] / 2, 3)
    out["optical_sensor_to_refill_mm"] = round(nose_inner_r(P, P["collar_z0"] - 2.0) - 0.7 - (rr + P["nib_travel"]), 3)
    out["min_required_mm"] = P["clear_min"]
    out["all_ok"] = all(v >= P["clear_min"] for k, v in out.items() if k.endswith("_mm") and isinstance(v, float)
                        and k not in ("refill_sweep_at_plate_tip_mm",))
    return out


def moving_interference(fixed, moving, P, n_dir=8):
    """Tilt the nib assembly about the gimbal centre so the ball moves nib_travel in
    n_dir directions; intersect with fixed parts (benders and leaves excluded:
    they connect to the collar)."""
    psi = math.degrees(math.atan(P["nib_travel"] / P["z_gimbal"]))
    rep = []
    check = {k: v for k, v in fixed.items() if k not in ("pcb_components_envelope",)}
    for k in range(n_dir):
        a = 2 * math.pi * k / n_dir
        axis = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2), 0.0)
        for mn, (mwp, _m) in moving.items():
            if mn in ("gimbal_hub",):
                continue
            mr = mwp.rotate((0, 0, P["z_gimbal"]), (axis[0], axis[1], P["z_gimbal"]), psi)
            for fn, (fwp, _f) in check.items():
                if (fn == "gimbal_flexure" and mn in ("refill_D1",)) or (fn == "bulkhead" and mn == "nib_spring"):
                    continue   # connected parts: the refill passes through the gimbal hub; the spring bears on the bulkhead
                try:
                    inter = mr.intersect(fwp)
                    v = inter.val().Volume() if inter.vals() else 0.0
                except Exception:
                    v = 0.0
                if v > 1e-5:
                    rep.append({"direction_deg": round(math.degrees(a), 1), "moving": mn, "fixed": fn, "overlap_mm3": round(v, 4)})
    return rep


# ------------------------------------------------------------------ viewer primitives
def viewer_primitives(P, pl):
    """Simple primitives for the three.js page, in the same frame (mm)."""
    ro, zs = P["od"] / 2, P["z_skid"] + P["skid_w"]
    prims = [
        {"name": "barrel", "group": "housing", "type": "lathe", "color": "barrel", "opacity": 0.28,
         "profile": [[P["skid_r"] + 0.35, zs], [ro, zs + P["nose_L"]], [ro, P["z_cap0"]]]},
        {"name": "rear_cap", "group": "housing", "type": "lathe", "color": "cap", "opacity": 0.9,
         "profile": [[ro, P["z_cap0"]], [ro, P["L_total"] - 1.0], [ro - 1.0, P["L_total"]], [0.01, P["L_total"]]]},
        {"name": "skid_ring", "group": "housing", "type": "tube", "color": "skid", "r_out": P["skid_r"] + 0.35,
         "r_in": P["skid_r"] - 0.15, "z0": P["z_skid"], "z1": P["z_skid"] + P["skid_w"]},
        {"name": "clamp_block", "group": "housing", "type": "tube", "color": "metal", "r_out": P["r_bore"] - 0.05,
         "r_in": P["refill_d"] / 2 + 0.45, "z0": P["z_clamp0"], "z1": P["z_clamp1"]},
        {"name": "gimbal_flexure", "group": "housing", "type": "tube", "color": "metal", "r_out": P["r_bore"] - 0.05,
         "r_in": 1.9, "z0": P["z_gimbal"] - 0.1, "z1": P["z_gimbal"] + 0.1},
        {"name": "bulkhead", "group": "housing", "type": "tube", "color": "cap", "r_out": P["r_bore"] - 0.05, "r_in": 0.01,
         "z0": P["z_bulkhead"], "z1": P["z_bulkhead"] + 0.8},
        {"name": "pcb", "group": "housing", "type": "box", "color": "pcb", "size": [P["pcb_w"], P["pcb_t"], P["pcb_L"]],
         "center": [0, 0, P["z_pcb0"] + P["pcb_L"] / 2]},
        {"name": "pcb_components", "group": "housing", "type": "box", "color": "chip",
         "size": [P["pcb_w"] - 0.6, 2 * P["comp_h"] + P["pcb_t"], P["pcb_L"] - 6.0], "center": [0, 0, P["z_pcb0"] + P["pcb_L"] / 2]},
        {"name": "battery", "group": "housing", "type": "cylinder", "color": "battery", "r": P["batt_d"] / 2,
         "z0": P["z_batt0"], "z1": P["z_batt0"] + P["batt_L"]},
        {"name": "hall_3d_nose", "group": "housing", "type": "box", "color": "chip", "size": [0.6, 1.5, 1.5],
         "center": [hall_nose(P)[1] + 0.3, 0, P["collar_z0"] + P["collar_L"] / 2]},
        {"name": "refill_D1", "group": "nib", "type": "refill", "color": "refill", "r": P["refill_d"] / 2,
         "L": P["refill_L"], "cone_L": P["cone_L"], "ball_r": P["ball_d"] / 2, "socket_r": P["socket_d"] / 2},
        {"name": "collar", "group": "nib", "type": "tube", "color": "metal", "r_out": P["collar_od"] / 2,
         "r_in": P["refill_d"] / 2 + 0.05, "z0": P["collar_z0"], "z1": P["collar_z0"] + P["collar_L"]},
        {"name": "collar_magnet", "group": "nib", "type": "box", "color": "magnet", "size": [0.6, 1.0, 1.0],
         "center": [P["collar_od"] / 2, 0, P["collar_z0"] + P["collar_L"] / 2]},
        {"name": "nib_spring", "group": "housing", "type": "spring", "color": "metal", "r": P["spring_od"] / 2,
         "z0": P["z_spring0"] + 1.0, "z1": P["z_bulkhead"], "turns": 12},
    ]
    for name, sol, ax in pl:
        bb = sol.val().BoundingBox()
        prims.append({"name": name, "group": "bender", "type": "plate", "color": "piezo",
                      "size": [bb.xlen, bb.ylen, P["plate_L"]], "root_z": P["z_clamp1"], "tip_z": P["z_plate_tip"],
                      "clamp_z": P["z_clamp0"], "center_xy": [(bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2],
                      "drive_axis": list(ax)})
    return prims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="L", choices=("L", "Q"))
    ap.add_argument("--no-step", action="store_true")
    a = ap.parse_args()
    P = parameters(a.variant)
    tag = f"pencil_revP{a.variant}"
    os.makedirs(OUT, exist_ok=True)
    fixed, benders, lvs, moving, pl = build(P)
    rows = mass_table({"fixed": fixed, "bender": benders, "leaf": lvs, "moving": moving})
    total = sum(r["mass_g"] for r in rows)
    com = sum(r["mass_g"] * r["com_z_mm"] for r in rows) / total
    m_mov = sum(r["mass_g"] for r in rows if r["group"] == "moving" and r["part"] not in ("nib_spring",))
    checks = section_checks(P, pl)
    inter = moving_interference(fixed, moving, P)
    if not a.no_step:
        asm = cq.Assembly(name=tag)
        for grp in (fixed, benders, lvs, moving):
            for name, (wp, _m) in grp.items():
                asm.add(wp, name=name)
        asm.save(os.path.join(OUT, f"{tag}_assembly.step"))
    summary = {
        "variant": a.variant, "parameters_mm": P,
        "mass_total_g": round(total, 2), "mass_nib_assembly_g": round(m_mov, 3), "com_z_mm": round(com, 1),
        "com_from_nib_fraction": round(com / P["L_total"], 3),
        "lever_nib_per_collar": round(P["lever"], 3),
        "section_checks": checks, "nib_assembly_interference": inter,
        "note": ("Mass excludes adhesives, wiring, flex tails and margin (add about 10 %). Bender blocking force "
                 "scales with plate width: 3.5 mm (L) or 2 x 2.6 mm per axis (Q) against PL128.10's 6.15 mm "
                 "(AMF-11). Fit checks use nominal dimensions and rigid parts."),
    }
    meta = provenance.metadata("proposed design (CAD concept, nominal geometry)",
                               extra={"cadquery": cq.__version__, "pencil_params": sp_params.load(PENCIL).version()})
    provenance.write_json(os.path.join(OUT, f"{tag}_summary.json"), {"meta": meta, "summary": summary, "parts": rows})
    provenance.write_json(os.path.join(OUT, f"{tag}_viewer.json"),
                          {"meta": meta, "units": "mm", "frame": "origin at the ball centre in contact at 50 deg tilt; z along the barrel toward the cap",
                           "gimbal_z": P["z_gimbal"], "lever": P["lever"], "primitives": viewer_primitives(P, pl)})
    print(json.dumps({k: v for k, v in summary.items() if k not in ("parameters_mm",)}, indent=1, default=str))
    for r in rows:
        print(f"  {r['part']:26s} {r['group']:7s} {r['material']:22s} {r['mass_g']:7.3f} g  com_z {r['com_z_mm']:6.1f}")


if __name__ == "__main__":
    main()
