"""Heel-drive parts of the recommended concept in the Rev H layout schema (PROPOSED DESIGN; CALC masses; ASSUMPTION
dimensions).  Written to results/drive/layout_parts.json for the 3-D explainer and used by mechanics/cad/heel_drive.py.

Recommended concept: a steered and driven wheel at the heel ("powered cobot").  A 2 mm wheel with an O-ring tyre sits
in a slot at the bottom of a larger skid ring; it is steered about the paper normal through its contact point and
driven about its axle.  Two brushless 6 mm motors sit in the handle between the gimbal and the coils; two thin shafts
in a keel under the front sleeve carry their motion to the heel pod.

Schema (as results/revH/layout.json "components"): id, label, group, shape (cylinder | cone | tube | box), z0, z1 (mm
along the pen axis from the ball tip), d0, d1, d_in, size ([x, y, z] mm for a box), offset ([x, y] mm; x in the tilt
plane, positive away from the paper), moves_with, optional, function, part, ledger, mass_g.  Parts that the layout
schema cannot tilt (the wheel, its fork and steering ring lie on the paper normal, 50 deg to the pen axis) are given
as axis-aligned stand-ins of the same size at the right place; mechanics/cad/heel_drive.py draws them tilted.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import REPO_ROOT as REPO, ensure_paths

ensure_paths()

THETA = 50.0
RHO = {"steel": 7.9e-3, "brass": 8.5e-3, "peek": 1.32e-3, "pom": 1.41e-3, "nbr": 1.0e-3, "fr4": 1.9e-3}   # g/mm^3 (ASSUMPTION)


def heel() -> Dict:
    from .run_study import chosen_heel
    return chosen_heel()


def _cyl_mass(d, L, rho, d_in=0.0):
    return math.pi / 4.0 * (d * d - d_in * d_in) * L * rho


def parts(h: Dict = None) -> List[Dict]:
    h = h or heel()
    th = math.radians(THETA)
    n = np.array([math.cos(th), 0.0, math.sin(th)])           # paper normal in the pen frame (x, y, z)
    r_e, R_d, R_s = h["r_e_mm"], h["R_d_mm"], h["R_skid_mm"]
    z_ring = h["front_end"]["ball_ahead_50_mm"]                   # ring plane = contact plane at 50 deg (front_end.py)
    contact = np.array([-R_d, 0.0, z_ring])
    wheel_c = contact + r_e * n
    ring_c = contact + (2.0 * r_e + 0.5) * n                     # steering ring (crown) 2.0-3.0 mm above the contact
    sleeve_front_d = h["front_end"]["sleeve_front_d_mm"]
    lip = 1.16                                                   # ring lip as Rev H (13.5 - 11.18) / 2
    P = []

    def add(**k):
        P.append(k)

    add(id="drive_skid_ring", label="Skid ring with wheel slot", group="drive", shape="tube",
        z0=round(z_ring, 2), z1=round(z_ring + 1.5, 2), d0=round(2 * R_s, 2), d1=round(2 * R_s, 2),
        d_in=round(2 * (R_s - lip), 2), moves_with="handle", optional=False,
        function="Rests on the paper like the Rev H ring, but larger, with a slot at the bottom through which the "
                 "drive wheel reaches the paper.",
        part="custom (PTFE-coated POM, contact radius %.2f mm, open 120 deg on top)" % R_s, ledger="",
        mass_g=round(_cyl_mass(2 * R_s, 1.5, RHO["pom"], 2 * (R_s - lip)) * (240.0 / 360.0), 3), open_deg=120.0)
    add(id="drive_wheel", label="Drive wheel with O-ring tyre", group="drive", shape="cylinder",
        z0=round(wheel_c[2] - 0.5, 2), z1=round(wheel_c[2] + 0.5, 2), d0=2.0 * r_e, d1=2.0 * r_e,
        offset=[round(wheel_c[0], 2), 0.0], moves_with="drive", optional=False,
        function="A 2 mm wheel that rolls on the paper: steered, it lets the pen move only along the letter; "
                 "driven, it pushes the pen along it.",
        part="custom brass hub d 0.8 mm + NBR O-ring 0.8 x 0.6 mm (tyre); axle d 0.3 mm in jewel bearings",
        ledger="AMF-111,AMF-112", mass_g=round(_cyl_mass(0.8, 1.0, RHO["brass"]) + _cyl_mass(2.0, 0.6, RHO["nbr"], 0.8), 3))
    add(id="drive_fork", label="Steering fork and crown", group="drive", shape="cylinder",
        z0=round(ring_c[2] - 0.5, 2), z1=round(ring_c[2] + 0.5, 2), d0=2.0 * r_e + 1.0, d1=2.0 * r_e + 1.0,
        offset=[round(ring_c[0], 2), 0.0], moves_with="drive", optional=False,
        function="Holds the wheel and turns it about the paper normal through its contact point; carries the "
                 "crown gear, the axle bevel and a tiny magnet for the steering-angle sensor.",
        part="custom (hardened steel fork, brass crown gear module 0.1, bevel 2:1 to the axle)", ledger="",
        mass_g=round(_cyl_mass(3.0, 1.0, RHO["brass"], 1.2) + 0.03, 3))
    # pod: outside the sleeve bore (6.23 mm at the carrier front) and the nose envelope (<= 6.1 mm, CALC
    # geometry.envelope(8.4)), inside the front sleeve and keel on the paper side
    bore = 6.23
    pod_x0, pod_x1 = -(bore + 0.27), -9.0
    add(id="drive_pod", label="Heel pod (sprung)", group="drive", shape="box",
        z0=round(z_ring + 1.5, 2), z1=round(z_ring + 5.5, 2), size=[round(pod_x0 - pod_x1, 2), 4.0, 4.0],
        offset=[round((pod_x0 + pod_x1) / 2.0, 2), 0.0], moves_with="drive", optional=False,
        function="Bearing block for the fork, the two bevel pinions and the sensors; it hangs on a flexure so a "
                 "0.55 N preload presses the wheel onto the paper.",
        part="custom (PEEK housing, two jewel bearings)", ledger="",
        mass_g=round(2.4 * 4.0 * 4.0 * 0.5 * RHO["peek"] + 0.05, 3))
    add(id="drive_spring", label="Preload flexure", group="drive", shape="box",
        z0=round(z_ring + 5.5, 2), z1=round(z_ring + 10.5, 2), size=[0.3, 3.0, 5.0],
        offset=[-8.6, 0.0], moves_with="handle", optional=False,
        function="Leaf spring that lets the pod move %.2f mm toward the paper and presses it with about 0.55 N; the "
                 "ring takes any extra writing force." % h["spring_travel_mm"],
        part="custom (17-7PH leaf 0.1 mm, laser-cut)", ledger="", mass_g=round(0.1 * 3.0 * 5.0 * RHO["steel"], 3))
    add(id="drive_load_sensor", label="Wheel-load sensor", group="drive", shape="box",
        z0=round(z_ring + 9.0, 2), z1=round(z_ring + 10.0, 2), size=[0.8, 1.5, 1.0],
        offset=[-9.2, 0.0], moves_with="handle", optional=False,
        function="Hall sensor that reads the flexure's bend: the wheel's load, which sets how much force can be "
                 "used before the wheel slips.",
        part="linear Hall IC (DRV5055 class) + 1 mm magnet", ledger="OPT-46", mass_g=0.02)
    add(id="drive_steer_sensor", label="Steering-angle sensor", group="drive", shape="box",
        z0=round(z_ring + 2.2, 2), z1=round(z_ring + 3.2, 2), size=[0.8, 1.5, 1.0],
        offset=[-8.4, -1.3], moves_with="drive", optional=False,
        function="Reads the wheel's heading from a magnet on the fork, right at the wheel (so shaft twist does not "
                 "matter).",
        part="3-D Hall IC (TMAG5273 class) + diametric magnet d 1 mm", ledger="OPT-45", mass_g=0.02)
    # keel and shafts under the front sleeve (paper side), beside the paper sensor
    z_k0, z_k1 = round(z_ring + 3.6, 2), 47.2      # keel starts where it clears the paper at 35 deg
    for i, (y, what) in enumerate(((2.9, "drive"), (-2.9, "steering"))):
        add(id=f"drive_shaft_{what}", label=f"{what.capitalize()} shaft", group="drive", shape="cylinder",
            z0=z_k0, z1=49.2, d0=0.8, d1=0.8, offset=[-9.1, y], moves_with="drive", optional=False,
            function=f"Thin steel shaft in a PTFE liner that carries the {what} motor's turning to the heel pod.",
            part="custom (stainless shaft d 0.8 mm, PTFE liner d 1.2 mm; 40 deg bevel pinion at the pod)", ledger="",
            mass_g=round(_cyl_mass(0.8, 49.2 - z_k0, RHO["steel"]), 3))
    add(id="drive_keel", label="Shaft keel", group="drive", shape="box", z0=z_k0, z1=z_k1, size=[2.6, 8.4, z_k1 - z_k0],
        offset=[-9.4, 0.0], moves_with="handle", optional=False,
        function="Ridge under the front sleeve (toward the paper) that houses the two shafts either side of the "
                 "paper sensor.",
        part="PEEK / TPE, part of the sleeve moulding", ledger="AMF-24",
        mass_g=round(2.6 * 8.4 * (z_k1 - z_k0) * 0.35 * RHO["peek"], 3))
    add(id="drive_paper_sensor", label="Paper sensor (needed by the drive)", group="drive", shape="box", z0=14.0, z1=20.0,
        size=[4.0, 5.0, 6.0], offset=[-8.6, 0.0], moves_with="handle", optional=False,
        function="Optical sensor that sees the paper: it detects wheel slip (pen motion that the wheel did not make) "
                 "and gives the page position.",
        part="optical flow sensor, to select (mouse-class performance as PMW3360: 1 kHz reports, 12 000 frames/s; "
             "its own package is too large)", ledger="AMF-109", mass_g=0.3)
    add(id="drive_transfer", label="Transfer gears", group="drive", shape="box", z0=47.2, z1=49.2, size=[4.6, 12.0, 2.0],
        offset=[-7.8, 0.0], moves_with="handle", optional=False,
        function="Two small spur-gear pairs that move each motor's output out to its shaft, around the gimbal.",
        part="module 0.1 spur gears (33 teeth, 1:1, centre distance 3.3 mm), brass", ledger="", mass_g=0.12)
    az = math.radians(35.0)
    rm = 7.4                          # sits 0.4 mm into the 1 mm shell wall (local pocket; ASSUMPTION acceptable)
    for name, sgn, lab_, fn in (("drive_motor", 1, "Wheel drive motor",
                                 "Turns the wheel so the pen is pushed along the letter (up to about 0.5 N at the wheel)."),
                                ("steer_motor", -1, "Steering motor",
                                 "Turns the wheel's heading to follow the letter.")):
        add(id=name, label=lab_, group="drive", shape="cylinder", z0=49.5, z1=69.5, d0=6.0, d1=6.0,
            offset=[round(-rm * math.cos(az), 2), round(sgn * rm * math.sin(az), 2)], moves_with="handle", optional=False,
            function=fn, part="Faulhaber 0620 B brushless DC, 6 x 20 mm (drive: bevel 2:1 at the wheel; steering: "
                              "crown 2:1)", ledger="AMF-100", mass_g=2.5)
    add(id="drive_drivers", label="Motor drivers", group="drive", shape="box", z0=99.5, z1=103.0, size=[1.0, 10.0, 3.5],
        offset=[0.0, 0.0], moves_with="handle", optional=False,
        function="Two three-phase drivers with current sensing that set each motor's torque 2000 times a second.",
        part="3-phase micro BLDC driver x2 (to select; DRV8311 class)", ledger="", mass_g=0.15)
    return P


def fit_checks(h: Dict, P: List[Dict]) -> Dict:
    """Simple clearance checks of the concept layout against Rev H parts (CALC)."""
    from . import geometry as GE
    rv = json.loads((REPO / "results" / "revH" / "layout.json").read_text())
    comp = {c["id"]: c for c in rv["components"]}
    swing = rv["magnet_stroke_mm"] / (rv["actuator_z"] - rv["pivot_z"])       # rad, arm swing at its stop
    arm_r = comp["arm"]["d0"] / 2.0
    shell_in = comp["shell"]["d_in"] / 2.0
    out = {}
    for m in ("drive_motor", "steer_motor"):
        c = next(p for p in P if p["id"] == m)
        rc = math.hypot(*c["offset"])
        arm_out = arm_r + swing * (c["z1"] - rv["pivot_z"])
        out[f"{m}_to_arm_at_stop_mm"] = round(rc - 3.0 - arm_out, 3)
        out[f"{m}_shell_pocket_depth_mm"] = round(max(0.0, (rc + 3.0) - shell_in), 3)
        out[f"{m}_shell_wall_left_mm"] = round((comp["shell"]["d0"] - comp["shell"]["d_in"]) / 2.0 - max(0.0, (rc + 3.0) - shell_in), 3)
        out[f"{m}_to_back_ring_z_mm"] = round(comp["back_ring"]["z0"] - c["z1"], 3)
        out[f"{m}_to_gimbal_z_mm"] = round(c["z0"] - comp["gimbal"]["z1"], 3)
    sh = next(p for p in P if p["id"] == "drive_shaft_drive")
    rsh = math.hypot(*sh["offset"])
    out["shaft_outside_gimbal_mm"] = round(rsh - 0.6 - comp["gimbal"]["d0"] / 2.0, 3)
    wp = GE.wheel_pod(h["r_e_mm"])
    out["wheel_pod_contact_radius_needed_mm"] = round(wp["R_d_mm"], 3)
    out["wheel_pod_contact_radius_used_mm"] = h["R_d_mm"]
    # the keel's lowest edge against the paper at the lowest tilt (35 deg): paper_wedge
    keel = next(p for p in P if p["id"] == "drive_keel")
    s_mid = np.array([keel["z0"], keel["z1"]]) - h["front_end"]["ball_ahead_50_mm"]
    allowed = GE.paper_wedge(h["R_d_mm"], s_mid)
    low = -keel["offset"][0] + keel["size"][0] / 2.0
    out["keel_to_paper_at_35deg_front_mm"] = round(float(allowed[0] - low), 3)
    env = GE.envelope(h["R_skid_mm"])
    for pid in ("drive_pod", "drive_paper_sensor"):
        c = next(p for p in P if p["id"] == pid)
        inner = -c["offset"][0] - c["size"][0] / 2.0
        s = np.linspace(c["z0"], c["z1"], 21) - h["front_end"]["ball_ahead_50_mm"]
        out[f"{pid}_to_nose_envelope_mm"] = round(float(inner - np.max(np.interp(s, env["s_mm"], env["r_mm"]))), 3)
    out["all_pass"] = bool(all(v > 0 for k, v in out.items() if k.endswith("_mm") and "radius" not in k
                               and "pocket" not in k))
    return out


def write_layout(path: Path, design: Dict = None) -> Dict:
    from stabpen import provenance as PV
    h = heel()
    P = parts(h)
    for p in P:
        for k in ("z0", "z1"):
            p[k] = round(float(p[k]), 2)
        if "offset" in p:
            p["offset"] = [round(float(v), 2) for v in p["offset"]]
        if "size" in p:
            p["size"] = [round(float(v), 2) for v in p["size"]]
    fc = fit_checks(h, P)
    mass = round(sum(p.get("mass_g", 0.0) for p in P), 2)
    doc = {
        "meta": {
            "evidence_status": "PROPOSED DESIGN (concept layout of study D's recommended heel drive; CALC masses from "
                               "volumes and catalogue; ASSUMPTION dimensions; nothing built or measured)",
            "concept": "steered and driven wheel at the heel (powered cobot); modes: steer only (passive guidance, "
                       "tremor constraint), steer + brake, steer + drive (lead-through, autowrite)",
            "replaces": ["skid_ring", "front_sleeve", "optical", "board_magnet", "board_keel"],
            "replaces_note": "skid_ring -> drive_skid_ring (contact radius %.2f mm instead of 6.75 mm, slotted); "
                             "front_sleeve grows at the front from 15.0 to %.1f mm (same 22 mm at z 50); optical -> "
                             "drive_paper_sensor (no longer optional: slip detection); the board magnet and its keel "
                             "give way to the shaft keel (the heel drive does the board's job without a board)"
                             % (h["R_skid_mm"], h["front_end"]["sleeve_front_d_mm"]),
            "changes_to_other_revH_parts": {
                "front_sleeve": {"d0_mm": h["front_end"]["sleeve_front_d_mm"], "z0_mm": round(h["front_end"]["ball_ahead_50_mm"] + 1.5, 2),
                                 "d1_mm": 22.0, "z1_mm": 50.0},
                "refill_spring": "the refill slides %.1f mm over 35-75 deg instead of %.1f mm"
                                 % (h["front_end"]["refill_slide_range_mm"], h["front_end_revH"]["refill_slide_range_mm"]),
                "ball_ahead_of_heel_at_50deg_mm": [round(h["front_end_revH"]["ball_ahead_50_mm"], 2),
                                                   round(h["front_end"]["ball_ahead_50_mm"], 2)]},
            "heel": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items()
                     if k in ("r_e_mm", "R_d_mm", "R_skid_mm", "delta_mm", "spring_travel_mm", "roll_tolerance_deg")},
            "added_mass_g": mass,
            "added_mass_note": "parts listed here; the larger front sleeve adds about 2.5 g more (CALC, PEEK/TPE 1.3 g/cm3)",
            "tilted_parts_note": "drive_wheel, drive_fork and drive_pod lie on the paper normal (50 deg to the pen "
                                 "axis); here they are axis-aligned stand-ins; mechanics/cad/heel_drive.py draws them tilted",
            "fit_checks": fc,
            "source": "drive/layout.py; docs/grounded_drive.md",
        },
        "units": "mm",
        "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away "
                "from the paper; y transverse",
        "components": P,
    }
    doc["meta"].update({"stabpen.provenance": PV.metadata("PROPOSED DESIGN; CALC",
                                                           extra={"script": "drive/layout.py"})})
    Path(path).write_text(json.dumps(doc, indent=1))
    return doc
