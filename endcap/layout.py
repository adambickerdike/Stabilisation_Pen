"""The recommended end-cap as parts in the Rev H layout schema (results/revH/layout.json "components"), for the 3-D explainer.

Each part: id, label, group ("endcap"), shape (cylinder | cone | tube | box), z0, z1 (mm along the pen axis from the ball
tip), d0, d1, d_in, size, offset ([x, y] mm; x in the tilt plane, positive away from the paper), moves_with ("handle", "rotor"
for a spinning part, "gimbal" for a gimbal frame, "inertial_mass" for a sliding reaction mass as in the Rev H layout),
optional, function, part, ledger, mass_g.  "meta" carries the evidence status, the rotor speed and spin axis, the Rev H
parts it replaces and the packaging conflicts.
Evidence status: PROPOSED DESIGN (dimensions from the optimiser, part masses CALC/ASSUMPTION).
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List

from stabpen import provenance
from . import design as DS
from . import params as P

Z0, Z1 = P.ENV["z0"] * 1e3, P.ENV["z1"] * 1e3
ZC = P.Z_CAP * 1e3


def _p(**kw):
    base = {"group": "endcap", "optional": True, "moves_with": "handle", "offset": [0.0, 0.0]}
    base.update(kw)
    return base


def shell_parts(d: Dict = None) -> List[Dict]:
    pg = (d or {}).get("parts_g", {})
    return [
        _p(id="ec_shell", label="End-cap shell", shape="tube", z0=Z0, z1=Z1, d0=P.ENV["od"] * 1e3, d1=P.ENV["od"] * 1e3, d_in=P.D_IN * 1e3,
           function="Closes the back of the pen and holds the end-cap parts; 26 mm across, 45 mm long.", part="PEEK tube, 1 mm wall",
           ledger="AMF-24", mass_g=pg.get("shell_g", DS.SHELL_M * 1e3)),
        _p(id="ec_board", label="End-cap driver board", shape="box", z0=Z1 - 4.0, z1=Z1 - 1.5, size=[18.0, 18.0, 2.5],
           function="Drivers for the end-cap actuators; talks to the main board.", part="PCB with coil or motor drivers (ASSUMPTION)",
           ledger="AMF-37", mass_g=pg.get("electronics_g", DS.ELEC_M * 1e3)),
    ]


def lrm_parts(d: Dict) -> List[Dict]:
    x = d["x"]
    ds, Ls, tc = x["d_s"] * 1e3, x["L_s"] * 1e3, x["t_c"] * 1e3
    X = d["X"] * 1e3
    z0, z1 = ZC - Ls / 2, ZC + Ls / 2
    Lmag = min(Ls, 12.0)
    Lcoil = Lmag + 2 * X
    r_coil = ds / 2 + X + 1.0 + DS.CLEAR * 1e3 + tc / 2
    parts = shell_parts(d)
    # the spring plates sit beyond the coil ends (no radial clash with the coils) and hold the slug by short axles
    half = max(Ls, Lcoil) / 2
    parts += [
        _p(id="ec_slug", label="Tungsten reaction mass", shape="cylinder", z0=z0, z1=z1, d0=ds, d1=ds, moves_with="inertial_mass",
           function=f"A heavy slug that the coils push sideways (up to +/-{X:.1f} mm in two axes); its reaction steadies the pen and can pulse for cues.",
           part="tungsten heavy alloy, non-magnetic grade (INERMET class)", ledger="AMF-49/AMF-125", mass_g=d["parts_g"]["slug_g"]),
        _p(id="ec_flexure_front", label="Flexure plate (front)", shape="tube", z0=ZC - half - 3.5, z1=ZC - half - 0.5, d0=P.D_IN * 1e3 - 0.5,
           d1=P.D_IN * 1e3 - 0.5, d_in=4.0,
           function="Spiral spring plate joined to the slug by a short axle: lets the slug move sideways, centres it at about 5 Hz, stiff along the pen.",
           part="17-7PH or 301 spring steel, laser cut (ASSUMPTION)", ledger="AMF-20", mass_g=d["parts_g"]["frame_g"] / 2),
        _p(id="ec_flexure_rear", label="Flexure plate (rear)", shape="tube", z0=ZC + half + 0.5, z1=ZC + half + 3.5, d0=P.D_IN * 1e3 - 0.5,
           d1=P.D_IN * 1e3 - 0.5, d_in=4.0, function="Second spring plate at the rear of the slug.",
           part="17-7PH or 301 spring steel, laser cut (ASSUMPTION)", ledger="AMF-20", mass_g=d["parts_g"]["frame_g"] / 2),
    ]
    for ax, (ox, oy) in (("x+", (1, 0)), ("x-", (-1, 0)), ("y+", (0, 1)), ("y-", (0, -1))):
        parts.append(_p(id=f"ec_magnet_{ax}", label="Slug magnet", shape="box", z0=ZC - Lmag / 2, z1=ZC + Lmag / 2,
                        size=[1.0 if ox else 3.0, 3.0 if ox else 1.0, Lmag], offset=[ox * (ds / 2 + 0.5), oy * (ds / 2 + 0.5)], moves_with="inertial_mass",
                        function="NdFeB tile on the slug; the facing coil pushes it sideways.", part="NdFeB N45 tile 1 mm thick", ledger="AMF-28",
                        mass_g=d["parts_g"]["magnets_g"] / 4))
        parts.append(_p(id=f"ec_coil_{ax}", label="Flat coil", shape="box", z0=ZC - Lcoil / 2, z1=ZC + Lcoil / 2,
                        size=[tc if ox else 8.0, 8.0 if ox else tc, Lcoil], offset=[ox * r_coil, oy * r_coil],
                        function="Fixed flat coil with a back iron: current through it pushes the facing magnet.",
                        part="self-bonding magnet wire, IEC class 155", ledger="AMF-29/AMF-30", mass_g=d["parts_g"]["copper_g"] / 4))
    return parts


def cmg_parts(d: Dict) -> List[Dict]:
    x = d["x"]
    D, t, dl = x["D"] * 1e3, x["t"] * 1e3, x["delta"]
    mot = P.MOTORS[d["choice"][1]]
    Lm, dm = mot.L * 1e3, mot.d * 1e3
    n_rot = {"SP2": 4, "SP1": 2, "DG1": 1, "DG2": 2, "PL2": 2}[d["class"]]
    parts = shell_parts(d)
    pitch = (Z1 - Z0 - 6.0) / n_rot
    for i in range(n_rot):
        zc = Z0 + 1.0 + pitch * (i + 0.5)
        sfx = "" if n_rot == 1 else f"_{i + 1}"
        spin = "counter-spinning " if (n_rot > 1 and i % 2) else ""
        parts += [
            _p(id=f"ec_rotor{sfx}", label=f"Tungsten rotor{sfx.replace('_', ' ')}", shape="cylinder", z0=zc - t / 2, z1=zc + t / 2, d0=D, d1=D,
               moves_with="rotor", function=f"Spinning {spin}disc ({x['n']:.0f} rpm): its angular momentum is tipped by the gimbals to twist the pen.",
               part="tungsten heavy alloy, non-magnetic grade (INERMET class), balanced to G0.4-G2.5", ledger="AMF-49/AMF-125/AMF-52",
               mass_g=d["parts_g"]["rotors_g"] / n_rot),
            _p(id=f"ec_spin_motor{sfx}", label="Spin motor", shape="cylinder", z0=zc + t / 2, z1=zc + t / 2 + Lm, d0=dm, d1=dm, moves_with="gimbal",
               function="Keeps the rotor at speed (about 0.1-0.2 W).", part=mot.name, ledger=mot.src, mass_g=mot.m * 1e3),
            _p(id=f"ec_bearings{sfx}", label="Rotor bearings", shape="tube", z0=zc - t / 2 - 2.5, z1=zc - t / 2, d0=9.0, d1=9.0, d_in=4.0,
               moves_with="gimbal", function="Carry the gyroscopic moment (tens of mN m) so the small motor's bearings do not.",
               part="2 x SKF 618/4 class, 4 x 9 x 2.5 mm", ledger="AMF-126", mass_g=d["parts_g"]["bearings_g"] / n_rot),
            _p(id=f"ec_gimbal_inner{sfx}", label="Inner gimbal ring", shape="tube", z0=zc - 3.0, z1=zc + 3.0, d0=D + 3.0, d1=D + 3.0, d_in=D + 1.0,
               moves_with="gimbal", function=f"Tilts the rotor about one cross axis (+/-{math.degrees(dl):.0f} deg).",
               part="aluminium ring with pivots (ASSUMPTION)", ledger="", mass_g=d["parts_g"]["frames_g"] / n_rot / (2 if d["class"] in ("DG1", "DG2") else 1)),
        ]
        if d["class"] in ("DG1", "DG2"):
            parts.append(_p(id=f"ec_gimbal_outer{sfx}", label="Outer gimbal ring", shape="tube", z0=zc - 3.5, z1=zc + 3.5, d0=min(D + 6.0, P.D_IN * 1e3),
                            d1=min(D + 6.0, P.D_IN * 1e3), d_in=D + 3.5, moves_with="gimbal",
                            function="Tilts the inner ring about the other cross axis: torque in any direction across the pen.",
                            part="aluminium ring with pivots (ASSUMPTION)", ledger="", mass_g=d["parts_g"]["frames_g"] / n_rot / 2))
    n_gd = {"SP2": 2, "SP1": 1, "DG1": 2, "DG2": 2, "PL2": 2}[d["class"]]
    for j in range(n_gd):
        parts.append(_p(id=f"ec_gimbal_drive_{j + 1}", label="Gimbal drive", shape="box", z0=Z1 - 13.0, z1=Z1 - 5.0, size=[5.0, 5.0, 8.0],
                        offset=[(-1) ** j * 7.0, 0.0], moves_with="handle",
                        function="Geared micro-motor with an angle sensor that swings a gimbal (up to 30 rad/s).",
                        part="Faulhaber 0515 B + gearhead + angle sensor (ASSUMPTION)", ledger="AMF-51", mass_g=d["parts_g"]["gimbal_drives_g"] / n_gd))
    return parts


def write(path, res: Dict):
    rec = res.get("recommendation", {})
    choice = rec.get("choice") or res.get("layout_choice") or "lrm"
    d = res["designs"][choice]
    parts = lrm_parts(d) if d["class"] == "LRM2" else cmg_parts(d)
    total = sum(p.get("mass_g", 0.0) for p in parts)
    meta = {"evidence_status": "PROPOSED DESIGN (dimensions from endcap/optimise.py; part masses CALC and ASSUMPTION); not built",
            "generated_utc": res["meta"]["generated_utc"], "git_revision": res["meta"]["git_revision"], "script": "endcap/layout.py",
            "doc": "docs/inertial_endcap.md", "design_class": d["class"], "choice": choice, "mass_total_g": total,
            "replaces": ["rear_cap", "rm_frame", "rm_mass", "rm_coils"],
            "conflicts": ["The end-cap occupies z 130-175 mm, so the Rev H handle shell ends at z 130 and the pen grows from 170 to 175 mm (Rev J limit).",
                          "The Rev H cell (14500, 48.5 mm long, z 101-149.5) no longer fits: 31 mm remain between the board (ends z 99) and the "
                          "end-cap; a 10440 (44.5 mm, AMF-31) does not fit either. The cell, the board or the end-cap length must be rearranged "
                          "(open issue for the lead).",
                          "The USB-C port and button (z 150-153.5) must move."],
            "axes": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away from the paper; y sideways",
            "optional_note": "every end-cap part is marked optional: the end-cap is a module that replaces the Rev H rear cap and rear "
                             "module; whether it is standard is the lead's decision (see the doc's proposed decision)",
            "moves_with_note": "'inertial_mass' = the sliding reaction mass (as rm_mass in the Rev H layout); 'rotor' = spinning; "
                               "'gimbal' = tilts on the gimbal; 'handle' = fixed to the pen body"}
    if d["class"] != "LRM2":
        meta.update({"rotor_speed_rpm": d["x"]["n"], "spin_axis": "along the pen axis (z) with the gimbals centred",
                     "angular_momentum_Nms_per_rotor": d["H"], "stored_energy_J_total": d["extras"]["E_J"]})
    else:
        meta.update({"rotor_speed_rpm": None, "spin_axis": None, "moving_mass_g": d["moving_mass_g"], "stroke_mm": d["X"] * 1e3})
    provenance.write_json(path, {"meta": meta, "units": "mm", "components": parts})
    return parts
