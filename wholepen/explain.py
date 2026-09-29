r"""Explainer outputs: layout_parts.json (the explainer's pen-layout schema, results/drive/layout_parts.json) for the new
parts, and animation.json keyframes (time, part, position, angle) sampled from a SIMULATION run so the 3-D explainer can
show the recommended system moving.

Layout frame (the explainer's): z along the pen axis from the ball tip (z = 0) toward the back, x in the tilt plane
positive away from the paper, y lateral; mm.  The tail module replaces the Rev J rear cap (z 141.72-144.72 mm).
Animation frame: the page frame of sim2 (x, y in the page, z up; metres converted to mm), the pen's attitude as the
rotation of its axis from the writing pose (two small angles, degrees), the nose's tip deflection (mm), the CMG
turret angle and gimbal angles (degrees) and the rotor spin phase.  Evidence status: PROPOSED DESIGN (layout, CALC
masses) and SIMULATION (keyframes).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import ROOT  # noqa: F401
from . import designs as DS

Z0_TAIL = 141.72          # mm: the Rev J rear cap's front face (results/revJ/layout.json)


def layout_parts(total_g: float = 100.0, provenance: Optional[Dict] = None) -> Dict:
    d = DS.cmg_design(total_g, mode="turret")
    L = d["length_mm"]
    od = d["od_mm"]
    z0, z1 = Z0_TAIL, Z0_TAIL + L
    ro = d["rotor_r_o_mm"]
    t = d["rotor_t_mm"]
    slot = (L - 12.0) / 2
    zr = [z0 + 6.0 + slot * 0.5, z0 + 6.0 + slot * 1.5]
    fp = d["fixed_parts_g"]
    comps = [
        {"id": "gt_housing", "label": "Gyro tail housing (containment)", "group": "gyro_tail", "shape": "tube", "z0": z0, "z1": z1,
         "d0": od, "d1": od, "d_in": od - 1.6, "moves_with": "handle", "optional": True,
         "function": "Screws on in place of the rear cap. Holds the two spinning rotors and stops a loose rotor: aluminium, 0.8 mm wall.",
         "part": "custom (aluminium tube, 0.8 mm wall, end caps)", "ledger": "", "mass_g": round(fp["housing_containment_al"], 2)},
        {"id": "gt_turret", "label": "Turret (turns the pair's torque axis)", "group": "gyro_tail", "shape": "tube", "z0": z0 + 2.0,
         "z1": z1 - 2.0, "d0": od - 2.2, "d1": od - 2.2, "d_in": od - 3.2, "moves_with": "gyro_turret", "optional": True,
         "function": "Carries both gimbals and turns slowly (at most 1 rad/s) about the pen axis so the gyroscopes push along the tremor's main direction.",
         "part": "custom frame + small geared motor", "ledger": "", "mass_g": round(fp["turret_motor"], 2)},
    ]
    for j in (0, 1):
        comps.append({"id": f"gt_rotor{j}", "label": f"Tungsten rotor {j + 1} ({'clockwise' if j == 0 else 'anticlockwise'})",
                      "group": "gyro_tail", "shape": "tube", "z0": round(zr[j] - t / 2, 2), "z1": round(zr[j] + t / 2, 2),
                      "d0": round(2 * ro, 2), "d1": round(2 * ro, 2), "d_in": round(2 * d["rotor_r_i_mm"], 2),
                      "moves_with": f"gyro_gimbal_{j}", "optional": True,
                      "function": f"A {d['rotor_g']:.0f} g tungsten ring spinning at {d['rpm']:.0f} rpm; its gimbal tips it back and forth, "
                                  "which twists the pen. The two rotors spin and tip in opposite senses, so their twists add on one axis and cancel on the others.",
                      "part": "tungsten heavy alloy ring (ASTM B777, 18 g/cm3) pressed on an outrunner bell", "ledger": "AMF-49",
                      "mass_g": round(d["rotor_g"], 2)})
        comps.append({"id": f"gt_gimbal{j}", "label": f"Gimbal frame {j + 1} with spin motor", "group": "gyro_tail", "shape": "tube",
                      "z0": round(zr[j] - t / 2 - 1.0, 2), "z1": round(zr[j] + t / 2 + 1.0, 2), "d0": round(2 * ro + 1.0, 2),
                      "d1": round(2 * ro + 1.0, 2), "d_in": round(2 * ro + 0.2, 2), "moves_with": f"gyro_gimbal_{j}", "optional": True,
                      "function": "Holds the rotor's bearings and hub motor; tips about an axis across the pen.",
                      "part": "custom frame, 2 x 618/4 bearings, outrunner stator", "ledger": "AMF-126,AMF-79",
                      "mass_g": round((fp["gimbal_frames_bearings"] + fp["spin_motor_stators_bearings"]) / 2, 2)})
    comps += [
        {"id": "gt_gimbal_motor", "label": "Gimbal motor and scissor gears", "group": "gyro_tail", "shape": "cylinder",
         "z0": z1 - 6.0 - 1.0, "z1": z1 - 1.0, "d0": 12.0, "d1": 12.0, "offset": [0.0, 7.0], "moves_with": "gyro_turret",
         "optional": True, "function": "Tips the two gimbals in opposite senses at the tremor frequency (up to about 1 rad) through a pair of gears.",
         "part": "Faulhaber 1226 B + 16:1 gearhead (ASSUMPTION ratio)", "ledger": "AMF-121",
         "mass_g": round(fp["gimbal_motor_gearhead_scissor_gears"], 2)},
        {"id": "gt_board", "label": "Gyro driver board", "group": "gyro_tail", "shape": "box", "z0": z0 + 1.0, "z1": z0 + 5.0,
         "size": [14.0, 14.0, 4.0], "moves_with": "handle", "optional": True,
         "function": "Spins the rotors, drives the gimbal and turret motors, and brakes the rotors if anything goes wrong.",
         "part": "custom", "ledger": "", "mass_g": round(fp["electronics"], 2)},
    ]
    return {"meta": {"evidence_status": "PROPOSED DESIGN (study W's gyro tail module; CALC masses from volumes and catalogue parts; ASSUMPTION sizes; nothing built)",
                     "concept": "detachable gyro tail: one scissored pair of control-moment gyroscopes on a turret, behind the thumb-index web",
                     "replaces": ["rear_cap"], "added_mass_g": round(total_g - 1.06, 2),
                     "design": {k: d[k] for k in ("total_g", "rotor_g", "rotor_r_o_mm", "rotor_t_mm", "rpm", "h_Nms", "length_mm", "od_mm",
                                                  "E_stored_J", "P_spin_W")},
                     "torque_Nm": d["torque_Nm"], "source": "wholepen/explain.py; docs/whole_pen_shift.md",
                     "stabpen.provenance": provenance},
            "units": "mm",
            "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away from the paper; y transverse",
            "components": comps}


def keyframes(r, parts: Dict[str, str], t0: float, t1: float, hz: float = 50.0, label: str = "") -> List[Dict]:
    """Keyframes (list of {t, part, pos_mm, ang_deg}) from a sim2 Result between t0 and t1."""
    t = r["t"]
    tt = np.arange(t0, t1, 1.0 / hz)
    it = lambda ch: np.interp(tt, t, r[ch]) if ch in r.idx else np.zeros(len(tt))
    out = []
    tip = np.column_stack([it("tipx"), it("tipy"), it("tipz")]) * 1e3
    ink = np.column_stack([it("ballx"), it("bally"), it("ballz")]) * 1e3
    hand = np.column_stack([it("handx"), it("handy"), it("handz")]) * 1e3
    ax = np.column_stack([it("ax"), it("ay"), it("az")])
    a0 = ax[0] / np.linalg.norm(ax[0])
    ang = []
    for v in ax:
        v = v / np.linalg.norm(v)
        # two small rotation angles of the pen axis from its first pose: in the tilt plane and sideways (deg)
        ang.append([math.degrees(math.asin(np.clip(v[2] - a0[2], -1, 1))), math.degrees(math.atan2(v[1], v[0]) - math.atan2(a0[1], a0[0]))])
    ang = np.array(ang)
    q = np.column_stack([it("q1"), it("q2")]) * 1e3
    extra = {p: it(ch) for p, ch in parts.items()}
    for k, tk in enumerate(tt):
        tk_ = round(float(tk - t0), 4)
        out.append({"t": tk_, "part": "hand", "pos_mm": [round(float(x), 3) for x in hand[k] - hand[0]], "ang_deg": [0.0, 0.0]})
        out.append({"t": tk_, "part": "pen", "pos_mm": [round(float(x), 3) for x in tip[k] - tip[0]],
                    "ang_deg": [round(float(x), 3) for x in ang[k]]})
        out.append({"t": tk_, "part": "nose", "pos_mm": [round(float(q[k, 0]), 3), round(float(q[k, 1]), 3), 0.0], "ang_deg": [0.0, 0.0]})
        out.append({"t": tk_, "part": "ink", "pos_mm": [round(float(x), 3) for x in ink[k] - tip[0]], "ang_deg": [0.0, 0.0]})
        for p in parts:
            out.append({"t": tk_, "part": p, "pos_mm": [0.0, 0.0, 0.0], "ang_deg": [round(math.degrees(float(extra[p][k])), 3), 0.0]})
    return out
