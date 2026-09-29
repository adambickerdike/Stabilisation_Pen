"""Concept layout of the recommended nib (B1) in the explainer layout schema (results/bnib/layout_parts.json) and the
geometry the CAD script draws (mechanics/cad/bnib.py).  PROPOSED DESIGN: dimensions from the optimised design
(optimise.py) and the grip class; masses CALC from volumes and densities (labels.MAT) or ASSUMPTION; fit checks are
geometric only.  Nothing built or measured.

Axes as the Rev J.1 layout: z along the pen axis from the ball tip (z = 0) toward the back, x in the tilt plane positive
away from the paper, y sideways; mm.  The B1 nib replaces the Rev J.1 C1S nose (carrier, arm, magnet cap, coil plate,
gimbal, pen-lift drum and tendons, nose Hall) and removes the heel drive (study D's wheel is not part of the fast core);
the base pen (shell, sleeve, board, cell, LRA, page sensor, USB, spreader) is kept.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .actuators import R_CARRIER
from .labels import CONTACT, MAT, val

RC = R_CARRIER * 1e3                # mm carrier radius where it passes the magnets

REPLACES = ["carrier_nozzle", "carrier", "front_pulley", "pen_lift", "slide_sensor", "arm", "rear_pulley", "position_magnet",
            "magnet_cap", "coil_plate", "gimbal", "nose_hall", "refill_holder", "skid_ring", "drive_wheel", "drive_fork",
            "drive_pod", "drive_spring", "drive_load_sensor", "drive_steer_sensor", "drive_shaft_drive",
            "drive_shaft_steering", "drive_transfer", "drive_motor", "steer_motor"]


def geometry(d, ev: Dict) -> Dict:
    """Components of the B1 nib (mm, g) from the design d (candidates.Design) and its evaluation ev."""
    hw = ev["hw"]
    act = hw["act"]
    rho_ti, rho_fe, rho_nd, rho_cu = val(MAT["Ti_rho"]), val(MAT["Fe_rho"]), val(MAT["NdFeB_rho"]), val(MAT["Cu_rho"])
    w, t_m, t_c = d.w * 1e3, d.t_m * 1e3, d.t_c * 1e3
    G = act["G"] * 1e3
    t_bi = act["t_bi"] * 1e3
    r_out = act["r_out"] * 1e3
    z_act = d.z_act * 1e3                      # centre of the coil layers
    zc0 = z_act - t_c                          # coil layers z range
    zc1 = z_act + t_c
    zm1 = zc0 - 0.30                           # magnet faces 0.30 mm in front of the coils
    zm0 = zm1 - t_m
    zb0 = zm0 - t_bi
    zk0 = zc1 + 0.15
    zk1 = zk0 + t_bi
    e = act["c"] * 1e3 - w / 2                 # half spacing between the poles
    c = act["c"] * 1e3
    wire_L = d.wire.L * 1e3
    z_w0 = zk1 + 1.5                           # carrier's rear flange behind the keeper
    z_w1 = z_w0 + wire_L                       # wire anchor ring on the handle
    r_w = 5.5
    comps: List[Dict] = []

    def add(**k):
        k.setdefault("offset", [0.0, 0.0])
        k.setdefault("optional", False)
        comps.append(k)
    # ---- the moving nib (carrier + coils + refill + sleeve + magnet)
    add(id="ball", label="Ball tip", group="refill", shape="cone", z0=0.0, z1=3.0, d0=0.7, d1=1.6, moves_with="nib",
        function="The ink ball (0.7 mm, ISO 12757 class F).", part="D1 refill tip", ledger="CON-22", mass_g=0.0)
    add(id="refill", label="Ink refill (D1 mini)", group="refill", shape="cylinder", z0=3.0, z1=67.0, d0=2.35, d1=2.35,
        moves_with="nib", function="A standard replaceable refill; it slides along its axis in the carrier's bushings.",
        part="ISO 12757-1 type D refill", ledger="CON-22", mass_g=val(CONTACT["refill_mass"]) * 1e3)
    add(id="bnib_refill_end", label="Refill end cap with rolling ball", group="refill", shape="cylinder", z0=67.0, z1=71.0,
        d0=3.2, d1=3.2, moves_with="nib", function="Clips on the refill's end; a 3 mm hardened ball in it rolls on the "
        "counter-face.", part="PEEK cap + 3 mm Si3N4 ball (ASSUMPTION)", ledger="AMF-24", mass_g=0.5)
    L_car = z_w0 - 9.0
    add(id="bnib_carrier", label="Nib carrier (titanium tube with two bushings)", group="moving_nib", shape="tube", z0=9.0,
        z1=z_w0 + 1.0, d0=3.2, d1=3.2, d_in=2.5, moves_with="nib",
        function="Carries the refill sideways (two PTFE-lined bushings at its ends) and the moving coils; the refill "
                 "slides in it freely along the pen.", part="Ti-6Al-4V tube 4.0/2.5 mm + PTFE liners", ledger="AMF-21",
        mass_g=(0.30 + 0.35) * 1.0)
    add(id="bnib_coils", label="Moving coils (two flat layers, x and y)", group="actuator", shape="tube", z0=zc0, z1=zc1,
        d0=2 * r_out - 0.8, d1=2 * r_out - 0.8, d_in=3.3, moves_with="nib",
        function="Two racetrack pairs per layer over the four poles; current pushes the nib sideways. Moving coil: no "
                 "magnetic pull or negative stiffness on the suspension.",
        part="self-bonding 0.10 mm wire on a 0.1 mm polyimide former (or a 4-layer flex coil)", ledger="AMF-29",
        mass_g=hw["m_cu"] * 1e3 + 0.25)
    add(id="bnib_carrier_flange", label="Carrier flange (wire clamps, Hall magnet)", group="moving_nib", shape="tube",
        z0=z_w0 - 1.0, z1=z_w0 + 0.5, d0=2 * r_w + 1.6, d1=2 * r_w + 1.6, d_in=2.6, moves_with="nib",
        function="Clamps the four suspension wires (0.1 mm edge radius, Kt about 1.3-1.8) and holds the 1 mm position magnet.",
        part="Ti-6Al-4V ring, laser-welded wire ends", ledger="AMF-21", mass_g=0.25)
    add(id="bnib_hall_magnet", label="Nib position magnet", group="sensor", shape="box", z0=z_w0 + 0.5, z1=z_w0 + 1.5,
        size=[1.0, 1.0, 1.0], offset=[r_w + 1.2, 0.0], moves_with="nib", function="Read by the 3-D Hall on the stator.",
        part="N52 1 mm cube", ledger="AMF-139", mass_g=0.05)
    # ---- the stator
    add(id="bnib_back_plate", label="Magnet back plate (soft iron)", group="actuator", shape="tube", z0=zb0, z1=zm0,
        d0=2 * r_out + 0.6, d1=2 * r_out + 0.6, d_in=2 * (RC + d.travel * 1e3 + 0.5), moves_with="handle",
        function="Carries the four poles and returns their flux.", part="AISI 1010 low-carbon steel, laser-cut (B_sat 1.6 T ASSUMPTION; Hiperco 50A would thin it: AMF-140)", ledger="ASSUMPTION",
        mass_g=rho_fe * math.pi * ((r_out + 0.3) ** 2 - (RC + d.travel * 1e3 + 0.5) ** 2) * t_bi * 1e-6)
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        add(id=f"bnib_magnet_{i + 1}", label="Pole magnet (checkerboard)", group="magnet", shape="box", z0=zm0, z1=zm1,
            size=[w, w, t_m], offset=[sx * c, sy * c], moves_with="handle",
            function="Four poles in a 2 x 2 checkerboard around the refill; axially polarised, alternating.",
            part=f"N52 cuboid {w:.2f} x {w:.2f} x {t_m:.2f} mm", ledger="AMF-139", mass_g=rho_nd * w * w * t_m * 1e-6)
    add(id="bnib_keeper", label="Keeper plate (soft iron)", group="actuator", shape="tube", z0=zk0, z1=zk1,
        d0=2 * r_out + 0.6, d1=2 * r_out + 0.6, d_in=2 * (RC + d.travel * 1e3 + 0.5), moves_with="handle",
        function="Closes the magnetic circuit behind the coils; the gap stays constant as the coils translate.",
        part="AISI 1010 low-carbon steel (ASSUMPTION; Hiperco 50A alternative: AMF-140)", ledger="ASSUMPTION",
        mass_g=rho_fe * math.pi * ((r_out + 0.3) ** 2 - (RC + d.travel * 1e3 + 0.5) ** 2) * t_bi * 1e-6)
    add(id="bnib_stator_housing", label="Actuator housing and spacers", group="structure", shape="tube", z0=zb0 - 0.5,
        z1=zk1 + 0.5, d0=22.0, d1=22.0, d_in=2 * r_out + 0.8, moves_with="handle",
        function="Holds plates and magnets at the set gap; bonded into the shell (heat path to the spreader).",
        part="aluminium ring (ASSUMPTION)", ledger="-", mass_g=0.5)
    for i, ang in enumerate((45, 135, 225, 315)):
        a = math.radians(ang)
        add(id=f"bnib_wire_{i + 1}", label="Suspension wire", group="mechanism", shape="cylinder", z0=z_w0, z1=z_w1,
            d0=d.wire.d * 1e3, d1=d.wire.d * 1e3, offset=[r_w * math.cos(a), r_w * math.sin(a)], moves_with="handle",
            function="Four parallel wires (fixed-guided) let the carrier translate in x and y and hold it along the pen.",
            part=f"Ti-6Al-4V wire {d.wire.d * 1e3:.3f} mm, free length {wire_L:.1f} mm", ledger="AMF-20; AMF-21",
            mass_g=rho_ti * math.pi / 4 * (d.wire.d * 1e3) ** 2 * wire_L * 1e-6)
    add(id="bnib_anchor_ring", label="Wire anchor ring", group="structure", shape="tube", z0=z_w1, z1=z_w1 + 1.5,
        d0=2 * r_w + 2.0, d1=2 * r_w + 2.0, d_in=2 * r_w - 2.0, moves_with="handle",
        function="Fixes the wires' rear ends to the handle; axial stops (20 um) protect the wires in a drop.",
        part="Ti-6Al-4V ring", ledger="AMF-21", mass_g=0.3)
    add(id="bnib_hall", label="Nib position sensor (3-D Hall)", group="sensor", shape="box", z0=z_w0 + 2.2, z1=z_w0 + 4.2,
        size=[0.8, 3.0, 2.0], offset=[r_w + 1.2, 0.0], moves_with="handle",
        function="Measures the nib's x/y at 10 kHz; its reading is filtered by the servo's observer.",
        part="TMAG5170-A1 on a flex tail", ledger="OPT-44; OPT-53", mass_g=0.05)
    # ---- the counter-face (behind the refill end)
    zf = 71.0
    add(id="bnib_face", label="Counter-face (hardened disc on a 2-axis flexure)", group="balance", shape="cylinder", z0=zf,
        z1=zf + 1.2, d0=6.0, d1=6.0, moves_with="handle",
        function="The ink spring pushes this face against the refill's rolling end. Set parallel to the paper, it cancels "
                 "the paper's push across the pen at every tilt; it rests on its follower stop when the ball lifts.",
        part="hardened steel disc 6 mm on a cross-strip flexure (301 FH)", ledger="AMF-20", mass_g=0.3)
    add(id="bnib_face_spring", label="Face spring (constant force) and follower stop", group="balance", shape="tube",
        z0=zf + 1.2, z1=zf + 6.0, d0=6.0, d1=6.0, d_in=3.0, moves_with="handle",
        function="Constant-force spring along the face normal (the ink force); a slow stop set a gap beyond the "
                 "writing position leaves the refill when the ball lifts.",
        part="stainless constant-force strip spring; lead-screw stop", ledger="EXP-N06", mass_g=0.4)
    add(id="bnib_face_positioners", label="Face positioners (2 x tilt/roll, 1 x stop)", group="balance", shape="box",
        z0=zf + 6.0, z1=zf + 12.0, size=[2.8, 8.0, 6.0], offset=[0.0, 0.0], moves_with="handle",
        function="Three slow screw motors with zero holding power set the face orientation from the IMU and the stop from "
                 "the refill-slide sensor.",
        part="New Scale SQL-RV-1.8 x 3 (or micro-stepper lead screws)", ledger="AMF-15; AMF-106", mass_g=3 * 0.16)
    add(id="bnib_skid_ring", label="Skid ring (C-shaped heel, 7 mm contact radius)", group="skid", shape="tube", z0=9.3,
        z1=10.8, d0=15.0, d1=15.0, d_in=12.0, moves_with="handle", open_deg=120.0,
        function="Rests on the paper and carries the hand's writing force; the ball sits about 5.4 mm in front of it at 50 deg.",
        part="PTFE-coated POM", ledger="DEC-034", mass_g=0.15)
    out = {"components": comps, "z_act": z_act, "r_out": r_out, "r_hole": act["r_hole"] * 1e3, "wire_z": (z_w0, z_w1), "face_z": zf,
           "tip_travel_mm": d.travel * 1e3, "stop_mm": (d.travel + 0.2e-3) * 1e3}
    out["fit_checks"] = fit_checks(out, d)
    out["mass_g"] = sum(c.get("mass_g", 0.0) for c in comps)
    return out


def fit_checks(geo: Dict, d) -> Dict:
    bore = 11.0
    r_out = geo["r_out"]
    ch = {"actuator_in_bore_mm": bore - (r_out + 0.4),
          "wires_clear_board_mm": 7.5 - (5.5 + 0.1),
          "magnet_hole_clears_carrier_at_stop_mm": geo["r_hole"] - (RC + (d.travel + 0.2e-3) * 1e3),
          "face_behind_refill_end_mm": geo["face_z"] - 71.0 + 0.0,
          "wire_anchor_before_battery_mm": 91.9 - (geo["wire_z"][1] + 1.5)}
    ch["all_pass"] = all(v >= 0 for k, v in ch.items() if isinstance(v, (int, float)))
    return ch


def layout_parts(d, ev: Dict) -> Dict:
    geo = geometry(d, ev)
    from . import provenance
    return {
        "meta": {"evidence_status": "PROPOSED DESIGN (study B's recommended balanced nib B1; dimensions from bnib/optimise.py, "
                                    "masses CALC or ASSUMPTION; nothing built or measured)",
                 "concept": "two-axis translation nib on four wires, moving-coil axial-gap actuator, contact-driven "
                            "counter-face balance at the refill's rear end",
                 "replaces": REPLACES,
                 "replaces_note": "the Rev J.1 C1S nose, gimbal, pen lift, nose Hall and the heel drive are removed; the "
                                  "skid ring shrinks to a 7 mm contact radius (the nib moves +-1 mm, not +-6 mm)",
                 "keeps": ["front_sleeve", "shell", "rear_cap", "main_board", "imu", "page_sensor", "usb", "battery", "lra",
                           "heat_spreader"],
                 "mass_added_g": geo["mass_g"], "fit_checks": geo["fit_checks"], "source": "bnib/layout.py; docs/balanced_nib.md",
                 "cad": "mechanics/cad/bnib.py", "stabpen.provenance": provenance("PROPOSED DESIGN; CALC")},
        "units": "mm",
        "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away from the "
                "paper; y sideways",
        "moves_with_note": "'nib' = translates with the nib (carrier, coils, refill); 'handle' = fixed to the pen",
        "components": geo["components"],
    }
