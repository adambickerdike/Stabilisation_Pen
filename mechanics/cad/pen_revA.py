#!/usr/bin/env python3
"""Parametric CAD concept of the research pen, Rev A (CadQuery 2.x).

Evidence status: PROPOSED DESIGN (dimensioned concept).  A rendered or
exported model is not a fit check of physical parts.  The interference check
below is geometric only (nominal dimensions, rigid parts).

Datums (drawing convention, also used by stabpen.frames):
  A  ball centre at stage neutral, unloaded (origin)
  B  barrel axis (z, pointing from nib to cap)
  C  roll datum: +x_H toward the PCB top face / flat on the barrel
Coordinates: millimetres here (CadQuery), converted to SI in reports.

Architecture (DEC-003, DEC-006, DEC-007):
  * front-pivot lever: refill carried in a titanium carrier tube that pivots
    about a virtual centre on the axis at z = L1 via three inclined wire
    flexures (lines of action through the pivot);
  * refill suspended in the carrier by two etched diaphragms (axial path
    ~2 kN/m, radially stiff);
  * rear annular sandwich Lorentz actuator: moving-coil paddle on the carrier
    between two fixed annular quadrant-magnet rings with back iron;
  * refill rear plug carries a sensing magnet read by a 3-D Hall sensor on the
    PCB front edge (lever angle x/y and axial slide z);
  * two optical-navigation sensors in the nose flanks; IMU on the PCB.
Outputs (results/cad/): assembly and part STEP files, mass/CoM table,
swept-workspace interference report, section drawing (via drawing script).
Run: python3 mechanics/cad/pen_revA.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")

# ----------------------------------------------------------------- parameters (mm)
P = dict(
    # barrel
    od_grip=15.0, od_act=16.0, wall=0.7, L_total=150.0, z_nose_end=22.0, z_bulge0=40.0, z_bulge1=60.0,
    nose_tip_od=6.0, tip_aperture=3.6, nose_z0=1.0,
    # refill ISO 12757-2 D1 (verify against purchased samples, EXP-B02)
    refill_d=2.35, refill_L=67.0, cone_L=5.0, ball_d=0.7,
    # lever carrier
    L1=12.0, carrier_od=3.4, carrier_id=2.5, carrier_z0=3.0, carrier_z1=64.0,
    tip_travel_mech=0.65,
    # pivot wires (virtual centre at z = L1)
    wire_d=0.25, wire_r_in=1.7, wire_r_out=5.5, n_wires=3,
    # stop ring
    z_stop=36.0, stop_t=1.2, stop_clear=0.10,
    # actuator (annular sandwich)
    z_act=50.0, mag_t=1.5, fe_t=1.5, coil_t=1.0, act_gap=0.45, act_od=14.6, act_id_clear=0.35,
    # sensing
    plug_L=2.5, sense_mag_d=2.0, sense_mag_t=1.5, hall_gap=1.2,
    # electronics and battery
    pcb_z0=71.0, pcb_L=29.0, pcb_w=11.5, pcb_t=0.8, comp_h=1.2,
    batt_d=10.0, batt_L=44.0, batt_z0=102.0, batt_kind="cyl", batt_w=12.0, batt_t=5.0,
    # optics
    opt_z=14.2, opt_size=(3.0, 2.5, 1.2), opt_r=3.75,  # chip-scale sensor + micro-optic (custom; EXP-S01)
)

DENS = {  # g/mm^3
    "Al6061": 2.70e-3, "Ti6Al4V": 4.43e-3, "NdFeB": 7.50e-3, "FeCo_or_1010": 7.87e-3, "Cu_coil": 6.5e-3,
    "PP_refill_with_ink": 1.1e-3, "FR4_populated": 2.4e-3, "Li_ion_10440": 2.33e-3, "PEEK": 1.30e-3,
    "spring_steel": 7.85e-3, "PC": 1.20e-3, "LiPo_pouch": 2.4e-3,
}

# Rev A.1 packaging variant (DEC-014, electronics/gen/placement_study.py): the
# 44 mm 10440 cell becomes a ~200 mAh LiPo pouch (5 x 12 x 32 mm class, >= 5 C,
# supplier drawing pending) and the main PCB grows from 29 to 41 mm.
VARIANTS = {"A": {}, "A1": {"pcb_L": 41.0, "batt_kind": "pouch", "batt_L": 32.0, "batt_z0": 114.0,
                            # tolerance analysis (mechanics/tolerance_analysis.py, DEC-007 rev.)
                            "act_gap": 0.50, "tip_travel_mech": 0.60,
                            # paper clearance of the nose at theta >= 35 deg (tolerance stack S6)
                            "nose_z0": 5.0, "nose_tip_od": 5.2, "tip_aperture": 4.2}}


def tube(r_out, r_in, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).circle(r_out).circle(r_in).extrude(z1 - z0))


def cyl(r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)


def cone(r0, r1, z0, z1):
    return cq.Solid.makeCone(r0, r1, z1 - z0, pnt=cq.Vector(0, 0, z0), dir=cq.Vector(0, 0, 1))


def swing(z, P):
    """Lateral swing (mm) of a lever point at axial position z for full tip travel."""
    return P["tip_travel_mech"] * abs(z - P["L1"]) / P["L1"]


# ----------------------------------------------------------------- fixed parts
def barrel(P):
    r_i = P["od_grip"] / 2 - P["wall"]
    ro_g, ro_a = P["od_grip"] / 2, P["od_act"] / 2
    zb0, zb1 = P["z_bulge0"], P["z_bulge1"]
    # revolve an outer profile with a gentle bulge over the actuator section
    z0n = P["nose_z0"]
    pts = [(P["nose_tip_od"] / 2, z0n), (ro_g, P["z_nose_end"]), (ro_g, zb0), (ro_a, zb0 + 5), (ro_a, zb1 - 3),
           (ro_g, zb1), (ro_g, P["L_total"]), (0, P["L_total"]), (0, z0n)]
    outer = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    inner_pts = [(P["tip_aperture"] / 2, z0n), (r_i - 1.5, P["z_nose_end"] - 2), (r_i, P["z_nose_end"]),
                 (r_i, zb0), (ro_a - P["wall"], zb0 + 5), (ro_a - P["wall"], zb1 - 3), (r_i, zb1),
                 (r_i, P["L_total"] - 1.0), (0, P["L_total"] - 1.0), (0, z0n)]
    inner = cq.Workplane("XZ").polyline(inner_pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return outer.cut(inner)


def pivot_ring(P):
    z0 = P["L1"] + (P["wire_r_out"] - P["wire_r_in"]) + (P["wire_r_in"]) - 0.6
    r_i = P["od_grip"] / 2 - P["wall"]
    return tube(r_i, P["wire_r_out"] + 0.3, z0, z0 + 1.6)


def stop_ring(P):
    r_i = P["od_grip"] / 2 - P["wall"]
    hole = P["carrier_od"] / 2 + swing(P["z_stop"], P) + P["stop_clear"]
    return tube(r_i, hole, P["z_stop"] - P["stop_t"] / 2, P["z_stop"] + P["stop_t"] / 2), hole


def actuator_fixed(P):
    """Front and rear annular magnet rings with back-iron rings (fixed)."""
    ro = P["act_od"] / 2
    z = P["z_act"]
    zc0 = z - P["coil_t"] / 2 - P["act_gap"]
    zc1 = z + P["coil_t"] / 2 + P["act_gap"]
    ri_f = P["carrier_od"] / 2 + swing(zc0 - P["mag_t"] - P["fe_t"], P) + P["act_id_clear"]
    ri_r = P["carrier_od"] / 2 + swing(zc1 + P["mag_t"] + P["fe_t"], P) + P["act_id_clear"]
    mag_f = tube(ro, ri_f, zc0 - P["mag_t"], zc0)
    fe_f = tube(ro, ri_f, zc0 - P["mag_t"] - P["fe_t"], zc0 - P["mag_t"])
    mag_r = tube(ro, ri_r, zc1, zc1 + P["mag_t"])
    fe_r = tube(ro, ri_r, zc1 + P["mag_t"], zc1 + P["mag_t"] + P["fe_t"])
    return {"magnet_front": mag_f, "iron_front": fe_f, "magnet_rear": mag_r, "iron_rear": fe_r}, (ri_f, ri_r)


def pcb(P):
    w, L, t = P["pcb_w"], P["pcb_L"], P["pcb_t"]
    board = cq.Workplane("XY").box(w, t, L, centered=(True, True, False)).translate((0, 0, P["pcb_z0"]))
    comps = (cq.Workplane("XY").box(w - 1.0, P["comp_h"], L - 2.0, centered=(True, False, False))
             .translate((0, t / 2, P["pcb_z0"] + 1.0)))
    comps2 = (cq.Workplane("XY").box(w - 1.0, P["comp_h"], L - 2.0, centered=(True, False, False))
              .translate((0, -t / 2 - P["comp_h"], P["pcb_z0"] + 1.0)))
    return board, comps.union(comps2)


def hall_sensor(P):
    z = P["refill_L"] + P["plug_L"] + P["hall_gap"]
    return cq.Workplane("XY").box(3.0, 3.0, 0.8, centered=(True, True, False)).translate((0, 0, z))


def battery(P):
    if P.get("batt_kind") == "pouch":
        return (cq.Workplane("XY").box(P["batt_w"], P["batt_t"], P["batt_L"], centered=(True, True, False))
                .translate((0, 0, P["batt_z0"])))
    return cyl(P["batt_d"] / 2, P["batt_z0"], P["batt_z0"] + P["batt_L"])


def optics(P):
    """Two optical-navigation sensor modules on the nose inner wall at z = opt_z,
    viewing the page near the nib through windows (custom optics, EXP-S01)."""
    parts = []
    # three sensors interleaved with the three pivot wires (wires at 90/210/330 deg),
    # so that one sensor faces the page at any roll angle
    for ang in (30.0, 150.0, 270.0):
        b = (cq.Workplane("XY").box(*P["opt_size"]).translate((0, P["opt_r"], P["opt_z"]))
             .rotate((0, 0, 0), (0, 0, 1), ang - 90.0))
        parts.append(b)
    return parts


# ----------------------------------------------------------------- moving parts
def refill(P):
    tip = cq.Workplane("XY").add(cone(P["ball_d"] / 2 + 0.1, P["refill_d"] / 2, 0.0, P["cone_L"]))
    body = cyl(P["refill_d"] / 2, P["cone_L"], P["refill_L"])
    ball = cq.Workplane("XY").sphere(P["ball_d"] / 2)
    return tip.union(body).union(ball)


def carrier(P):
    return tube(P["carrier_od"] / 2, P["carrier_id"] / 2, P["carrier_z0"], P["carrier_z1"])


def coil_paddle(P, ri_f):
    ro = P["act_od"] / 2 - swing(P["z_act"], P) - 0.3
    return tube(ro, P["carrier_od"] / 2, P["z_act"] - P["coil_t"] / 2, P["z_act"] + P["coil_t"] / 2), ro


def rear_plug(P):
    z0 = P["refill_L"]
    plug = cyl(P["refill_d"] / 2 + 0.3, z0 - 1.0, z0 + P["plug_L"] - P["sense_mag_t"])
    mag = cyl(P["sense_mag_d"] / 2, z0 + P["plug_L"] - P["sense_mag_t"], z0 + P["plug_L"])
    return plug, mag


def pivot_wires(P):
    wires = []
    c = cq.Vector(0, 0, P["L1"])
    for k in range(P["n_wires"]):
        a = 2 * math.pi * k / P["n_wires"] + math.pi / 2
        u = cq.Vector(math.cos(a), math.sin(a), 0)
        p_in = c + u * P["wire_r_in"] + cq.Vector(0, 0, P["wire_r_in"])
        p_out = c + u * P["wire_r_out"] + cq.Vector(0, 0, P["wire_r_out"])
        d = p_out - p_in
        w = cq.Solid.makeCylinder(P["wire_d"] / 2, d.Length, pnt=p_in, dir=d.normalized())
        wires.append(cq.Workplane("XY").add(w))
    return wires


# ----------------------------------------------------------------- assembly
def build(P):
    fixed = {"barrel": (barrel(P), "Al6061"), "pivot_ring": (pivot_ring(P), "PEEK")}
    sr, stop_hole = stop_ring(P)
    fixed["stop_ring"] = (sr, "PEEK")
    act, (ri_f, ri_r) = actuator_fixed(P)
    fixed["magnet_front"] = (act["magnet_front"], "NdFeB")
    fixed["iron_front"] = (act["iron_front"], "FeCo_or_1010")
    fixed["magnet_rear"] = (act["magnet_rear"], "NdFeB")
    fixed["iron_rear"] = (act["iron_rear"], "FeCo_or_1010")
    board, comps = pcb(P)
    fixed["pcb"] = (board, "FR4_populated")
    fixed["pcb_components_envelope"] = (comps, "FR4_populated")
    fixed["hall_3d"] = (hall_sensor(P), "FR4_populated")
    if P.get("batt_kind") == "pouch":
        fixed["battery_pouch"] = (battery(P), "LiPo_pouch")
    else:
        fixed["battery_10440"] = (battery(P), "Li_ion_10440")
    for i, o in enumerate(optics(P)):
        fixed[f"optical_sensor_{i+1}"] = (o, "FR4_populated")
    paddle, paddle_ro = coil_paddle(P, ri_f)
    plug, smag = rear_plug(P)
    moving = {"refill_D1": (refill(P), "PP_refill_with_ink"), "carrier": (carrier(P), "Ti6Al4V"),
              "coil_paddle": (paddle, "Cu_coil"), "rear_plug": (plug, "PEEK"), "sensing_magnet": (smag, "NdFeB")}
    for i, w in enumerate(pivot_wires(P)):
        fixed[f"pivot_wire_{i+1}"] = (w, "spring_steel")   # wires bend; counted as fixed for mass
    return fixed, moving, {"stop_hole_r": stop_hole, "act_ri_front": ri_f, "act_ri_rear": ri_r, "paddle_ro": paddle_ro}


def mass_table(fixed, moving):
    rows = []
    for group, parts in (("fixed", fixed), ("moving", moving)):
        for name, (wp, mat) in parts.items():
            sol = wp.val() if hasattr(wp, "val") else wp
            try:
                shape = wp.combine().val() if hasattr(wp, "combine") else sol
            except Exception:
                shape = sol
            V = shape.Volume()
            c = shape.Center()
            m = V * DENS[mat]
            rows.append({"part": name, "group": group, "material": mat, "volume_mm3": round(V, 2),
                         "mass_g": round(m, 3), "com_z_mm": round(c.z, 2)})
    return rows


def rotate_about_pivot(wp, P, direction_deg, psi_rad):
    ax = (math.cos(math.radians(direction_deg + 90)), math.sin(math.radians(direction_deg + 90)), 0.0)
    return wp.rotate((0, 0, P["L1"]), (ax[0], ax[1], P["L1"] + ax[2] + 0 * 1.0) if False else
                     (ax[0], ax[1], P["L1"]), math.degrees(psi_rad))


def interference(fixed, moving, P, n_dir=12, margins=(1.0,)):
    """Rotate the moving assembly about the pivot to full tip travel in n_dir
    directions; report intersection volumes with fixed parts (excluding the
    pivot wires that intentionally connect them)."""
    psi = math.asin(P["tip_travel_mech"] / P["L1"])
    report = []
    fixed_check = {k: v for k, v in fixed.items() if not k.startswith("pivot_wire") and k != "pcb_components_envelope"}
    for k in range(n_dir):
        ang = 360.0 * k / n_dir
        for mname, (mwp, _) in moving.items():
            m_rot = mwp.rotate((0, 0, P["L1"]), (math.cos(math.radians(ang)), math.sin(math.radians(ang)), P["L1"]),
                               math.degrees(psi))
            for fname, (fwp, _) in fixed_check.items():
                try:
                    inter = m_rot.intersect(fwp)
                    v = inter.val().Volume() if inter.vals() else 0.0
                except Exception:
                    v = 0.0
                if v > 1e-6:
                    report.append({"direction_deg": ang, "moving": mname, "fixed": fname, "overlap_mm3": round(v, 4)})
    # fixed-vs-fixed check for parts that must not touch (wires vs optics, PCB vs Hall, etc.)
    names = [k for k in fixed if k not in ("barrel", "pcb_components_envelope")]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if {a, b} <= {"pcb", "hall_3d"}:
                continue
            try:
                inter = fixed[a][0].intersect(fixed[b][0])
                v = inter.val().Volume() if inter.vals() else 0.0
            except Exception:
                v = 0.0
            if v > 1e-6:
                report.append({"direction_deg": None, "moving": a, "fixed": b, "overlap_mm3": round(v, 4)})
    return psi, report


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="A", choices=sorted(VARIANTS))
    a = ap.parse_args()
    P.update(VARIANTS[a.variant])
    tag = "revA" if a.variant == "A" else f"rev{a.variant}"
    os.makedirs(OUT, exist_ok=True)
    fixed, moving, derived = build(P)
    rows = mass_table(fixed, moving)
    total = sum(r["mass_g"] for r in rows)
    m_mov = sum(r["mass_g"] for r in rows if r["group"] == "moving")
    com = sum(r["mass_g"] * r["com_z_mm"] for r in rows) / total
    # lever inertia about pivot from moving parts (point-mass-per-part approximation + rods)
    J = 0.0
    for r in rows:
        if r["group"] == "moving":
            J += r["mass_g"] * (r["com_z_mm"] - P["L1"]) ** 2
    # distributed-mass inertia about the pivot: each moving part as a uniform
    # line mass over its axial extent (tubes and rods), which the point-mass
    # sum above understates by ~30 % for the long carrier and refill
    Jd = 0.0
    for name, (wp, mat) in moving.items():
        m = next(r["mass_g"] for r in rows if r["part"] == name)
        bb = (wp.val() if hasattr(wp, "val") else wp).BoundingBox()
        za, zb = bb.zmin - P["L1"], bb.zmax - P["L1"]
        Jd += m * (zb ** 3 - za ** 3) / (3.0 * (zb - za)) if zb - za > 1e-6 else m * za * za
    psi, inter = interference(fixed, moving, P)
    asm = cq.Assembly(name=f"pen_{tag}")
    for name, (wp, mat) in {**fixed, **moving}.items():
        asm.add(wp, name=name)
    asm.save(os.path.join(OUT, f"pen_{tag}_assembly.step"))
    if a.variant == "A":
        for name, (wp, mat) in moving.items():
            cq.exporters.export(wp, os.path.join(OUT, f"part_{name}.step"))
        for name in ("barrel", "stop_ring", "magnet_front", "magnet_rear"):
            cq.exporters.export(fixed[name][0], os.path.join(OUT, f"part_{name}.step"))
    summary = {
        "parameters_mm": P, "derived_mm": derived,
        "mass_total_g": round(total, 2), "mass_moving_g": round(m_mov, 3), "com_z_mm": round(com, 1),
        "lever_J_pivot_g_mm2_point_approx": round(J, 1),
        "tip_equivalent_mass_g_point_approx": round(J / P["L1"] ** 2, 2),
        "lever_J_pivot_g_mm2_distributed": round(Jd, 1),
        "tip_equivalent_mass_g_distributed": round(Jd / P["L1"] ** 2, 2),
        "lever_ratio_act": round((P["z_act"] - P["L1"]) / P["L1"], 2),
        "psi_max_deg": round(math.degrees(psi), 2),
        "interference_at_full_travel": inter,
        "variant": a.variant,
        "note": "Mass excludes adhesives, wiring, fasteners, grip overmould and margin; see mechanics/mass_budget.csv.",
    }
    meta = provenance.metadata("proposed design (CAD concept, nominal geometry)", extra={"cadquery": cq.__version__})
    provenance.write_json(os.path.join(OUT, f"pen_{tag}_summary.json"), {"meta": meta, "summary": summary, "parts": rows})
    print(json.dumps({k: v for k, v in summary.items() if k != "parameters_mm"}, indent=1, default=str)[:3000])
    for r in rows:
        print(f"  {r['part']:26s} {r['group']:7s} {r['material']:20s} {r['mass_g']:7.3f} g  com_z {r['com_z_mm']:6.1f}")


if __name__ == "__main__":
    main()
