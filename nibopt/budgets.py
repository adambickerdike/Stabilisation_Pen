r"""Pen-level budgets of a nib candidate in study K's structure (CALCULATION on PROPOSED DESIGNS).

  mass     study K's layout parts (results/revK/layout.json) with the nib's parts replaced by the candidate's (moving
           parts, plates, poles, races, balls, wires) and every part behind the actuator moved back by the candidate's
           shift; the shell scaled with the body diameter and length; revj/budgets.mass_properties (read-only, +10 %
           wiring and adhesive as study K)
  length   study K's 145.1 mm + the head's shift (+ a relocated board for the pad race)
  battery  study K's modes on the LIR14500 (2.22 Wh) with the matched nib power (nibopt/evaluate)
  skin     study K's fin model at the body diameter (nibopt/pen.skin)
"""
from __future__ import annotations

import copy
import math
from typing import Dict

from . import params as P
from .design import Design
from .params import val


def mass(d: Design) -> Dict:
    from revj import budgets as RBU
    lay = P.load_json("results/revK/layout.json")
    comps = copy.deepcopy(lay["components"])
    K_comps = {c["id"]: c for c in lay["components"]}
    mp = d.moving_parts_g()
    st = d.stator_parts_g()
    z0 = val(P.PEN["actuator_z0_mm"])
    t_p = d.plate_t_mm()
    g = d.mag
    zc0 = z0 + t_p + g.t_m * 1e3 + g.c0 * 1e3
    zf0, zf1 = d.flange_z()
    shift = d.rear_shift_mm()
    head = d.holder_extension_mm()
    scale_D = d.od_mm / 24.0
    out = []
    for c in comps:
        cid = c["id"]
        if cid == "back_plate":
            c.update(z0=z0, z1=z0 + t_p, mass_g=st["back_plate"], d0=2 * (d.bore_mm - 0.3))
        elif cid.startswith("pole_magnet_"):
            c.update(z0=z0 + t_p, z1=z0 + t_p + g.t_m * 1e3, mass_g=st["magnets"] / 4 * (g.t_m / (g.t_m + g.t_m2)
                                                                                           if g.double else 1.0),
                     size=[g.w * 1e3, g.w * 1e3, g.t_m * 1e3])
        elif cid == "keeper":
            zk = zc0 + g.t_cu * 1e3 + g.c1 * 1e3 + (g.t_m2 * 1e3 if g.double else 0.0)
            c.update(z0=zk, z1=zk + t_p, mass_g=st["keeper"], d0=2 * (d.bore_mm - 0.3))
        elif cid in ("coil_x", "coil_y"):
            half = g.t_cu * 0.5e3
            zz = zc0 + (0 if cid == "coil_x" else half)
            c.update(z0=zz, z1=zz + half, mass_g=mp["coils"] / 2)
        elif cid == "carrier":
            c.update(z1=zf1 + 0.5, mass_g=mp["carrier_tube"])
        elif cid == "carrier_rear_guide":
            c.update(z0=zf0 - 0.5, z1=zf1)
        elif cid == "carrier_flange":
            c.update(z0=zf0, z1=zf1, mass_g=mp["flange"] + mp["flange_inserts"], d0=2 * d.flange_radius_mm)
        elif cid == "position_magnet":
            c.update(z0=zf1, z1=zf1 + 1.0)
        elif cid in ("front_race", "rear_race"):
            ratio = (d.guide_circle_mm * (d.stop_mm + d.ball_d_mm + 0.4)) / (8.3 * (1.2587 + 0.8 + 0.4))
            if d.race_topology == "pads":
                ratio *= min(1.0, d.n_balls * math.pi * (d.stop_mm / 2 + d.ball_d_mm / 2 + 0.2) ** 2 /
                             (2 * math.pi * d.guide_circle_mm * (d.stop_mm + d.ball_d_mm + 0.4)))
            zr = (zf0 - 0.3 - d.ball_d_mm) if cid == "front_race" else (zf1 + d.ball_d_mm)
            c.update(z0=zr, z1=zr + 0.3, mass_g=K_comps[cid]["mass_g"] * ratio)
        elif cid in ("front_balls", "rear_balls"):
            zb = (zf0 - d.ball_d_mm) if cid == "front_balls" else zf1
            c.update(z0=zb, z1=zb + d.ball_d_mm, mass_g=d.n_balls * 3.2e-3 * 4 / 3 * math.pi * (d.ball_d_mm / 2) ** 3)
        elif cid.startswith("wire_"):
            c.update(z0=zf1, z1=zf1 + d.L_w_mm)
        elif cid == "refill_holder":
            c.update(z0=c["z0"] + head, z1=c["z1"] + head, mass_g=0.05 + mp["holder_extension"])
        elif cid == "shell":
            c.update(z0=c["z0"] + shift, z1=c["z1"] + head + (d.length_mm() - val(P.PEN["length_K_mm"]) - head),
                     mass_g=c["mass_g"] * scale_D * (1 + (d.length_mm() - val(P.PEN["length_K_mm"])) / (c["z1"] - c["z0"])),
                     d0=d.od_mm)
        elif cid in ("front_sleeve",):
            c.update(mass_g=c["mass_g"] * scale_D, d0=d.od_mm)
        elif cid in ("nose_hall",):
            c.update(z0=c["z0"] + shift, z1=c["z1"] + shift)
        elif cid in ("anchor_ring",):
            c.update(z0=zf1 + d.L_w_mm, z1=zf1 + d.L_w_mm + 1.5)
        elif cid in ("main_board", "board_parts", "imu"):
            if d.race_topology == "pads":
                base = K_comps["head_roll_motor"]["z1"] + head + 0.5
                c.update(z0=base + (c["z0"] - 35.5), z1=base + (c["z1"] - 35.5))
            else:
                c.update(z0=c["z0"] + shift, z1=c["z1"] + shift)
        elif c["z0"] >= 58.5:
            extra = 22.8 if d.race_topology == "pads" and c["z0"] >= 91.0 else 0.0
            c.update(z0=c["z0"] + head + extra, z1=c["z1"] + head + extra)
        out.append(c)
    # wires: n_w of them (study K drew four)
    wires = [c for c in out if c["id"].startswith("wire_")]
    for c in wires:
        c["mass_g"] = val(P.MECH["C17200"])["rho"] * math.pi / 4 * (d.d_w_mm * 1e-3) ** 2 * d.L_w_mm * 1e-3 * 1e3
    for k in range(d.n_w - len(wires)):
        cc = copy.deepcopy(wires[0])
        cc["id"] = f"wire_{len(wires) + k + 1}"
        out.append(cc)
    mpk = RBU.mass_properties(out)
    base = RBU.mass_properties(lay["components"])
    moving = d.m_move_g()
    return {"mass_g": mpk["mass_g"], "com_mm": mpk["com_mm"][2], "I_transverse_g_mm2": mpk["inertia_g_mm2"][0][0],
            "K_mass_g": base["mass_g"], "K_com_mm": base["com_mm"][2], "moving_g": moving,
            "moving_parts_g": mp, "stator_parts_g": st,
            "label": "CALCULATION (study K's layout parts, the nib's replaced; revj/budgets.mass_properties, +10 % wiring)"}


def pen_budget(d: Design, ev: Dict) -> Dict:
    m = mass(d)
    bat = ev.get("battery", {})
    nbm = ev.get("nib_by_mode", {})
    return {"mass": m, "length_mm": d.length_mm(), "od_mm": d.od_mm,
            "battery_hours": {end: {mode: r["hours"] for mode, r in rows.items()} for end, rows in bat.items()},
            "battery_rows": bat,
            "skin_by_mode": {conv: {mode: {"max_shell_C": r["skin_max_C"], "front_pad_C": r["front_pad_C"],
                                            "coil_C": r["coil_C"], "nib_35deg_W": r["P35_W"], "nib_mean_W": r["mean_W"]}
                                    for mode, r in rows.items()} for conv, rows in nbm.items()},
            "label": "CALCULATION in study K's budget structure (revk/budgets.py): mass, length, battery per mode, skin"}
