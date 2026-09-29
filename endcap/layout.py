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
        _p(id="ec_board", label="End-cap driver board", shape="box", z0=Z1 - 4.0, z1=Z1 - 1.5, size=[16.0, 16.0, 2.5],
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
    parts.append(coil_ring(ZC - Lcoil / 2, ZC + Lcoil / 2, tc, d["parts_g"]["copper_g"]))
    return parts


def coil_ring(z0, z1, tc, copper_g) -> Dict:
    """The four drive coils as one thin ring lining the bore (as rm_coils in the Rev H layout).  The design model
    (endcap/design.lrm2) takes the coil layer as tc thick at the bore; flat 8 mm boxes at that radius would cut into the
    shell wall at their corners, so the coils are arc-shaped and the layout draws them as one tube."""
    return _p(id="ec_coils", label="Drive coils (4, arc-shaped)", shape="tube", z0=z0, z1=z1, d0=P.D_IN * 1e3, d1=P.D_IN * 1e3,
              d_in=P.D_IN * 1e3 - 2 * tc, function="Four arc-shaped coils bonded to the bore, one per side (x+, x-, y+, y-): current "
                                                    "through a coil pushes the facing slug magnet sideways. Drawn as one ring; the gaps "
                                                    "between the coils hold the flexure tabs.",
              part="self-bonding magnet wire, IEC class 155, wound on an arc former (ASSUMPTION)", ledger="AMF-29/AMF-30", mass_g=copper_g)


# Proposed compact packaging (PROPOSED DESIGN, CALC geometry): the reaction-mass end-cap sits behind the Rev H cell, in the
# slot of the Rev H rear module, with its spiral flexures nested inside the coil ring (outer rims held by four tabs between
# the coils).  The Rev H cell stays at z 101-149.5 and the USB-C side port moves forward beside the cell's rear end.
COMPACT = dict(z0=151.0, z1=175.0, zc=162.0, wall=0.8, board=2.0, usb_z=(147.0, 150.5))


def lrm_parts_compact(d: Dict) -> List[Dict]:
    x = d["x"]
    ds, Ls, tc = x["d_s"] * 1e3, x["L_s"] * 1e3, x["t_c"] * 1e3
    X = d["X"] * 1e3
    pg = d["parts_g"]
    C = COMPACT
    zc = C["zc"]
    Lmag = min(Ls, 12.0)
    Lcoil = Lmag + 2 * X
    r_coil = ds / 2 + X + 1.0 + DS.CLEAR * 1e3 + tc / 2
    r_plate = r_coil - tc / 2 - 0.3                      # nested plate: inside the coil ring
    L_shell = C["z1"] - C["z0"]
    shell_g = pg.get("shell_g", DS.SHELL_M * 1e3) * L_shell / (P.ENV["length"] * 1e3)
    wall_g = P.RHO_PEEK * math.pi / 4 * (P.D_IN * 1e3) ** 2 * C["wall"] * 1e-6       # g (RHO in g/cm3 x mm3 / 1000)
    z_board0 = zc + Lcoil / 2 + 0.2
    parts = [
        _p(id="ec_shell", label="End-cap shell", shape="tube", z0=C["z0"], z1=C["z1"], d0=P.ENV["od"] * 1e3, d1=P.ENV["od"] * 1e3,
           d_in=P.D_IN * 1e3, function=f"Closes the back of the pen and holds the reaction mass; 26 mm across, {L_shell:.0f} mm long.",
           part="PEEK tube, 1 mm wall", ledger="AMF-24", mass_g=shell_g),
        _p(id="ec_end_wall", label="End-cap rear wall", shape="cylinder", z0=C["z1"] - C["wall"], z1=C["z1"], d0=P.D_IN * 1e3, d1=P.D_IN * 1e3,
           function="Closes the rear of the end-cap.", part="PEEK disc 0.8 mm", ledger="AMF-24", mass_g=wall_g),
        _p(id="ec_board", label="End-cap driver board", shape="box", z0=z_board0, z1=z_board0 + C["board"], size=[16.0, 16.0, C["board"]],
           function="Coil drivers and the slug's position sensor; talks to the main board.", part="PCB with coil drivers (ASSUMPTION)",
           ledger="AMF-37", mass_g=pg.get("electronics_g", DS.ELEC_M * 1e3)),
        _p(id="ec_slug", label="Tungsten reaction mass", shape="cylinder", z0=zc - Ls / 2, z1=zc + Ls / 2, d0=ds, d1=ds, moves_with="inertial_mass",
           function=f"A heavy slug that the coils push sideways (up to +/-{X:.1f} mm in two axes); its reaction steadies the pen and can pulse for cues.",
           part="tungsten heavy alloy, non-magnetic grade (INERMET class)", ledger="AMF-49/AMF-125", mass_g=pg["slug_g"]),
    ]
    for name, z0_, z1_ in (("front", zc - Ls / 2 - 1.0, zc - Ls / 2 - 0.2), ("rear", zc + Ls / 2 + 0.2, zc + Ls / 2 + 1.0)):
        parts.append(_p(id=f"ec_flexure_{name}", label=f"Flexure plate ({name})", shape="tube", z0=z0_, z1=z1_, d0=2 * r_plate, d1=2 * r_plate,
                        d_in=4.0, function="Spiral spring plate nested inside the coil ring (rim held by four tabs between the coils), joined to "
                                           "the slug by a short axle: lets it move sideways, centres it at about 5 Hz, stiff along the pen.",
                        part="17-7PH or 301 spring steel, laser cut (ASSUMPTION)", ledger="AMF-20", mass_g=pg["frame_g"] / 2))
    for ax, (ox, oy) in (("x+", (1, 0)), ("x-", (-1, 0)), ("y+", (0, 1)), ("y-", (0, -1))):
        parts.append(_p(id=f"ec_magnet_{ax}", label="Slug magnet", shape="box", z0=zc - Lmag / 2, z1=zc + Lmag / 2,
                        size=[1.0 if ox else 3.0, 3.0 if ox else 1.0, Lmag], offset=[ox * (ds / 2 + 0.5), oy * (ds / 2 + 0.5)], moves_with="inertial_mass",
                        function="NdFeB tile on the slug; the facing coil pushes it sideways.", part="NdFeB N45 tile 1 mm thick", ledger="AMF-28",
                        mass_g=pg["magnets_g"] / 4))
    parts.append(coil_ring(zc - Lcoil / 2, zc + Lcoil / 2, tc, pg["copper_g"]))
    u0, u1 = C["usb_z"]
    parts.append(_p(id="ec_usb_moved", label="USB-C port and button (moved)", shape="box", z0=u0, z1=u1, size=[8.4, 2.6, u1 - u0], offset=[0.0, 9.0],
                    optional=False, function="The Rev H side port, moved 3 mm forward beside the cell's rear end (the cell is 14.1 mm across, the "
                                             "port sits at the shell wall 9 mm off the axis).", part="USB-C receptacle (mid-mount)", ledger="",
                    mass_g=0.0))
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


REVH_PEN = dict(total_g=74.95, com_mm=92.85)      # results/revH/layout.json, mass_g (standard Rev H, no optional parts)


def pen_estimate(parts: List[Dict]) -> Dict:
    """Mass and balance point of the Rev H pen with the compact end-cap (CALC): the Rev H total minus the shell segment
    behind z 151 and the rear cap (solid PEEK disc, ASSUMPTION), plus the end-cap parts."""
    rho = P.RHO_PEEK * 1e-6                                                   # kg/m3 -> g/mm3
    try:
        import json
        import os
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "revH", "layout.json")) as fh:
            mg = json.load(fh)["mass_g"]
        REVH_PEN.update(total_g=float(mg["total_g"]), com_mm=float(mg["com_mm"]))
    except (OSError, KeyError, ValueError):
        pass
    shell_cut = rho * math.pi / 4 * (22.0 ** 2 - 20.0 ** 2) * (170.0 - COMPACT["z0"])
    cap = rho * math.pi / 4 * 21.0 ** 2 * 3.0
    m = REVH_PEN["total_g"] - shell_cut - cap
    mz = REVH_PEN["total_g"] * REVH_PEN["com_mm"] - shell_cut * 0.5 * (COMPACT["z0"] + 170.0) - cap * 168.5
    for p in parts:
        mp = p.get("mass_g", 0.0)
        m += mp
        mz += mp * 0.5 * (p["z0"] + p["z1"])
    return {"label": "CALC (Rev H total 74.95 g, balance point z 92.85 mm, results/revH/layout.json; minus the Rev H shell behind "
                     "z 151 and the rear cap, taken as a solid PEEK disc (ASSUMPTION); plus the end-cap parts)",
            "removed_g": shell_cut + cap, "total_g": m, "balance_point_z_mm": mz / m,
            "was": {"total_g": REVH_PEN["total_g"], "balance_point_z_mm": REVH_PEN["com_mm"]}, "limit_g": 120.0}


def write(path, res: Dict):
    rec = res.get("recommendation", {})
    choice = rec.get("choice") or res.get("layout_choice") or "lrm"
    d = res["designs"][choice]
    compact = d["class"] == "LRM2"
    parts = lrm_parts_compact(d) if compact else cmg_parts(d)
    total = sum(p.get("mass_g", 0.0) for p in parts)
    meta = {"evidence_status": "PROPOSED DESIGN (dimensions from endcap/optimise.py; part masses CALC and ASSUMPTION); not built",
            "generated_utc": res["meta"]["generated_utc"], "git_revision": res["meta"]["git_revision"], "script": "endcap/layout.py",
            "doc": "docs/inertial_endcap.md", "design_class": d["class"], "choice": choice, "mass_total_g": total,
            "replaces": ["rear_cap", "rm_frame", "rm_mass", "rm_coils"],
            "moves": (["usb"] if compact else []),
            "conflicts": (["Proposed compact packaging: the end-cap spans z 151-175 mm behind the Rev H cell (z 101-149.5, unchanged); the Rev H "
                           "handle shell ends at z 151 and the pen grows from 170 to 175 mm (Rev J limit). The USB-C side port moves from "
                           "z 150-153.5 to z 147-150.5, beside the cell's rear end.",
                           "The study simulated the slug centre at z 152.5 mm (a 45 mm end-cap at z 130-175, which leaves the 48.5 mm "
                           "cell no room); the compact packaging puts it at z 162 mm. See 'packaging_check' for the effect."]
                          if compact else
                          ["The end-cap occupies z 130-175 mm, so the Rev H handle shell ends at z 130 and the pen grows from 170 to 175 mm (Rev J limit).",
                           "The Rev H cell (14500, 48.5 mm long, z 101-149.5) no longer fits: 31 mm remain between the board (ends z 99) and the "
                           "end-cap; a 10440 (44.5 mm, AMF-31) does not fit either. The cell, the board or the end-cap length must be rearranged "
                           "(open issue for the lead).",
                           "The USB-C port and button (z 150-153.5) must move."]),
            "axes": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away from the paper; y sideways",
            "optional_note": "every end-cap part is marked optional: the end-cap is a module that replaces the Rev H rear cap and rear "
                             "module; whether it is standard is the lead's decision (see the doc's proposed decision)",
            "moves_with_note": "'inertial_mass' = the sliding reaction mass (as rm_mass in the Rev H layout); 'rotor' = spinning; "
                               "'gimbal' = tilts on the gimbal; 'handle' = fixed to the pen body"}
    if d["class"] != "LRM2":
        meta.update({"rotor_speed_rpm": d["x"]["n"], "spin_axis": "along the pen axis (z) with the gimbals centred",
                     "angular_momentum_Nms_per_rotor": d["H"], "stored_energy_J_total": d["extras"]["E_J"]})
    else:
        meta.update({"rotor_speed_rpm": None, "spin_axis": None, "moving_mass_g": d["moving_mass_g"], "stroke_mm": d["X"] * 1e3,
                     "packaging": "compact (PROPOSED DESIGN): flexures nested inside the coil ring, end-cap z 151-175 mm, slug centre z 162 mm",
                     "packaging_check": res.get("compact_packaging"),
                     "changes_to_other_revH_parts": {
                         "shell": {"z1_mm": COMPACT["z0"], "was_z1_mm": 170.0,
                                   "note": "the Rev H handle shell (22 mm across) now ends where the 26 mm end-cap shell starts"},
                         "usb": {"z0_mm": COMPACT["usb_z"][0], "z1_mm": COMPACT["usb_z"][1], "was_mm": [150.0, 153.5],
                                 "note": "drawn here as ec_usb_moved (same part, same 9 mm offset)"},
                         "length_mm": {"now": COMPACT["z1"], "was": 170.0}},
                     "pen_estimate": pen_estimate(parts)})
    provenance.write_json(path, {"meta": meta, "units": "mm", "components": parts})
    return parts
