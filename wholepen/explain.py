r"""Explainer outputs: layout_parts.json (the explainer's pen-layout schema, as results/drive/layout_parts.json) for the
recommended whole-pen collar (the review's option B, study W's V2 load path) with the gyroscopic tail as an optional,
separate group, and animation.json keyframes (time, part, position, angle) sampled from a SIMULATION run so the 3-D
explainer can show the whole pen moving.

Layout frame (the explainer's): z along the pen axis from the ball tip (z = 0) toward the back, x in the tilt plane
positive away from the paper, y lateral; mm.
Animation frame: the page frame of sim2 (x, y in the page, z up; mm relative to the first frame); angles in degrees:
'inner_pen' = the swinging pen's axis direction (tilt-plane and sideways angles from its first pose), 'collar' = the
held collar's (the inner pen's minus the pivot angles), 'pivot' = the collar's two pivot angles, 'nose' = the small nib's
tip deflection (mm), 'ink' = where the ball is.  Evidence status: PROPOSED DESIGN (layout, CALC masses) and SIMULATION
(keyframes).
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional

import numpy as np

from . import BUILD, RESULTS, provenance, write_json
from . import calc as K
from . import designs as DS

Z0_TAIL = 141.72          # mm: the Rev J rear cap's front face (results/revJ/layout.json)


def layout_parts(prov: Optional[Dict] = None, z_p: float = 50.0, travel: float = 4.0) -> Dict:
    g = K.COLLAR_V2
    mm = K.collar_masses("coil")
    geo = next(r for r in K.collar_geometry()["rows"] if r["z_p_mm"] == z_p and r["travel_mm"] == travel and r["path"] == "V2")
    od = round(geo["collar_od_mm"], 2)
    wall = g["wall"] * 1e3
    zb = g["barrel_od"] * 1e3
    z_front, z_rear, L = g["z_front_v2"] * 1e3, g["z_rear"] * 1e3, g["length"] * 1e3
    cp, mv = mm["collar_parts_g"], mm["moving_parts_g"]
    comps = [
        {"id": "collar_sleeve", "label": "Collar (what the hand holds)", "group": "collar", "shape": "tube", "z0": z_front + 1.5,
         "z1": g["z_end_wall"] * 1e3, "d0": od, "d1": od, "d_in": round(od - 2 * wall, 2), "moves_with": "collar", "optional": False,
         "function": "The fingers hold it and the thumb-index web rests on it. It does not swing: the pen inside it does.",
         "part": "custom (PA12-CF, 1.2 mm wall, or aluminium 0.8 mm)", "ledger": "", "mass_g": round(cp["sleeve_PA12CF_1.2mm"], 2)},
        {"id": "collar_skid_ring", "label": "Skid ring on the collar", "group": "collar", "shape": "tube", "z0": z_front,
         "z1": z_front + 1.5, "d0": round(od + 1.0, 2), "d1": round(od + 1.0, 2), "d_in": round(od - 2.5, 2), "moves_with": "collar",
         "optional": False, "function": "Rests on the paper and carries the writing force, so the swinging pen only carries its small refill spring.",
         "part": "custom (PTFE-coated POM ring)", "ledger": "", "mass_g": cp["skid_ring_V2"]},
        {"id": "collar_pivot", "label": "Two-axis flexure pivot", "group": "collar", "shape": "box", "z0": z_p - 1.5, "z1": z_p + 1.5,
         "size": [round(od - 2 * wall - 0.6, 2), round(od - 2 * wall - 0.6, 2), 3.0], "moves_with": "collar", "optional": False,
         "function": f"Holds the inner pen {z_p:.0f} mm behind the tip and lets it tilt ±{geo['swing_deg']:.1f}° each way: ±{travel:.0f} mm at the tip.",
         "part": "custom cross-strip flexure (titanium or spring steel)", "ledger": "", "mass_g": cp["gimbal_cross_flexure"]},
        {"id": "collar_coil_plate", "label": "Two-axis coil plate (collar's rear wall)", "group": "collar", "shape": "tube",
         "z0": 93.0, "z1": 97.0, "d0": round(od - 2 * wall, 2), "d1": round(od - 2 * wall, 2), "d_in": 2.0, "moves_with": "collar",
         "optional": False,
         "function": "Pushes on the magnets of the inner pen's end face, 42 mm behind the pivot, to swing the pen; the push-back goes into the collar and the hand (the Liftware principle). A long lever: the static load costs about 0.05 W.",
         "part": "custom flat coils on a steel back plate (Rev J C1S actuator principle)", "ledger": "", "mass_g": cp["coil_plate_2_axis"] + cp["back_iron"]},
        {"id": "collar_end_wall", "label": "Collar end wall", "group": "collar", "shape": "tube", "z0": 97.0, "z1": g["z_end_wall"] * 1e3,
         "d0": od, "d1": od, "d_in": 0.0, "moves_with": "collar", "optional": False, "function": "Closes the collar; charging contacts and the switch.",
         "part": "custom", "ledger": "", "mass_g": 0.5},
        {"id": "collar_load_cell", "label": "Skid load cell", "group": "collar", "shape": "box", "z0": z_front + 2.0, "z1": z_front + 4.0,
         "size": [2.0, 4.0, 1.0], "offset": [round(-(od / 2 - wall - 0.8), 2), 0.0], "moves_with": "collar", "optional": False,
         "function": "Measures the writing force: it tells the pen it is on the paper (the refill may then follow the paper) and the actuator how much to hold.",
         "part": "custom strain flexure", "ledger": "", "mass_g": cp["load_cell_and_wiring"]},
        {"id": "inner_barrel", "label": "Inner pen (swings)", "group": "inner_pen", "shape": "tube", "z0": 4.0, "z1": L, "d0": zb, "d1": zb,
         "d_in": zb - 1.0, "moves_with": "inner_pen", "optional": False,
         "function": "Everything that writes: refill, small fine nib, cell and board. The collar's actuator swings all of it; balanced about the pivot.",
         "part": "custom (aluminium tube 12 x 0.5 mm)", "ledger": "", "mass_g": round(mv["barrel_tube_al_0.5mm"], 2)},
        {"id": "fine_nib", "label": "Small fine nib (±1 mm)", "group": "inner_pen", "shape": "tube", "z0": 3.0, "z1": 38.0, "d0": 6.0,
         "d1": 6.0, "d_in": 2.6, "moves_with": "inner_pen", "optional": False,
         "function": "Study B's balanced nib: it trims the last millimetre quickly; the collar takes the large swings.",
         "part": "study B (bnib/), not designed here", "ledger": "", "mass_g": mv["refill_and_fine_nib_stage"]},
        {"id": "inner_board", "label": "Board and IMU", "group": "inner_pen", "shape": "box", "z0": 40.0, "z1": 56.0,
         "size": [9.0, 3.0, 16.0], "moves_with": "inner_pen", "optional": False,
         "function": "Estimates the tremor and drives the actuator and the nib.", "part": "custom", "ledger": "", "mass_g": mv["board_and_sensors"]},
        {"id": "inner_cell", "label": "Li-ion cell 10280", "group": "inner_pen", "shape": "cylinder", "z0": 58.0, "z1": 86.0, "d0": 10.0,
         "d1": 10.0, "moves_with": "inner_pen", "optional": False, "function": "Power; behind the pivot, balancing the nib in front.",
         "part": "10280 Li-ion (ASSUMPTION about 0.3 Wh)", "ledger": "", "mass_g": mv["cell_10280_Li_ion"]},
        {"id": "inner_magnets", "label": "Actuator magnets (inner pen's end face)", "group": "inner_pen", "shape": "cylinder",
         "z0": L - 3.0, "z1": L, "d0": zb, "d1": zb, "moves_with": "inner_pen", "optional": False,
         "function": "Four magnet poles facing the coil plate; they slide over it as the pen tilts.", "part": "N52 segments (ASSUMPTION)",
         "ledger": "", "mass_g": cp["magnets_on_end_face_moving"]},
    ]
    # the optional gyro tail (study W's CMG turret pair), kept as a separate optional group
    d = DS.cmg_design(100, mode="turret")
    fp = d["fixed_parts_g"]
    z0, z1 = Z0_TAIL, Z0_TAIL + d["length_mm"]
    comps.append({"id": "gt_housing", "label": "Optional gyro tail (bench experiment only)", "group": "gyro_tail", "shape": "tube",
                  "z0": z0, "z1": round(z1, 2), "d0": round(d["od_mm"], 2), "d1": round(d["od_mm"], 2), "d_in": round(d["od_mm"] - 1.6, 2),
                  "moves_with": "inner_pen", "optional": True,
                  "function": f"Two {d['rotor_g']:.0f} g tungsten rotors at {d['rpm']:.0f} rpm storing {d['E_stored_J']:.0f} J: an experiment for the review's gate G5, not part of the recommended pen.",
                  "part": "PROPOSED DESIGN (designs.cmg_design)", "ledger": "AMF-49,AMF-121,AMF-126",
                  "mass_g": round(d["total_g"], 1)})
    return {"meta": {"evidence_status": "PROPOSED DESIGN (study W's recommended whole-pen collar, the review's option B with the V2 load path; CALC masses from volumes and catalogue parts; ASSUMPTION dimensions; nothing built or measured)",
                     "concept": "the hand holds a collar that rests on the paper; the whole inner pen swings in it on a 2-axis pivot, driven by two motors that push back on the collar and hand; a small fine nib (study B) trims the rest",
                     "replaces": ["front_sleeve", "shell", "gimbal", "carrier", "magnet_cap", "coil_plate"],
                     "replaces_note": "a new architecture, not a Rev J add-on: the 24 mm shell becomes a 100 mm long, 21.7 mm collar around a 92 mm, 12 mm swinging pen; Rev J's own nose can sit in the inner pen instead of the fine nib only if the inner pen grows to 24 mm (then the collar is about 33 mm across); two geared 0824 motors (8 mm across) do not fit beside the swinging pen, so the actuator is a coil plate in the collar's rear wall",
                     "collar_geometry": geo, "masses": {"collar_g": round(mm["collar_g"], 1), "inner_pen_g": round(mm["barrel_g"], 1), "total_g": round(mm["total_g"], 1)},
                     "source": "wholepen/explain.py; wholepen/calc.py; docs/whole_pen_shift.md", "stabpen.provenance": prov},
            "units": "mm",
            "axis": "z along the pen axis from the ball tip (z = 0) toward the back; x in the tilt plane, positive away from the paper; y transverse",
            "components": comps}


def keyframes_from_trace(fn: str, t0: float, t1: float, hz: float = 50.0) -> List[Dict]:
    z = np.load(fn)
    t = z["t"]
    tt = np.arange(t0, t1, 1.0 / hz)
    it = lambda ch: np.interp(tt, t, z["ch_" + ch]) if ("ch_" + ch) in z.files else np.zeros(len(tt))
    hand = np.column_stack([it("handx"), it("handy"), it("handz")]) * 1e3
    tip = np.column_stack([it("tipx"), it("tipy"), it("tipz")]) * 1e3
    ink = np.column_stack([np.interp(tt, t, z["ink"][:, 0]), np.interp(tt, t, z["ink"][:, 1])]) * 1e3
    ax = np.column_stack([it("ax"), it("ay"), it("az")])
    a0 = ax[0] / max(np.linalg.norm(ax[0]), 1e-12)
    p1, p2 = it("w_piv1"), it("w_piv2")
    q = np.column_stack([it("q1"), it("q2")]) * 1e3
    out = []
    for k, tk in enumerate(tt):
        v = ax[k] / max(np.linalg.norm(ax[k]), 1e-12)
        tilt = math.degrees(math.asin(float(np.clip(v[2], -1, 1))) - math.asin(float(np.clip(a0[2], -1, 1))))
        side = math.degrees(math.atan2(v[1], v[0]) - math.atan2(a0[1], a0[0]))
        ts = round(float(tk - t0), 3)
        out += [{"t": ts, "part": "hand", "pos_mm": [round(float(x), 3) for x in hand[k] - hand[0]], "ang_deg": [0.0, 0.0]},
                {"t": ts, "part": "inner_pen", "pos_mm": [round(float(x), 3) for x in tip[k] - tip[0]], "ang_deg": [round(tilt, 3), round(side, 3)]},
                {"t": ts, "part": "collar", "pos_mm": [round(float(x), 3) for x in hand[k] - hand[0]],
                 "ang_deg": [round(tilt - math.degrees(float(p1[k])), 3), round(side - math.degrees(float(p2[k])), 3)]},
                {"t": ts, "part": "pivot", "pos_mm": [0.0, 0.0, 0.0], "ang_deg": [round(math.degrees(float(p1[k])), 3), round(math.degrees(float(p2[k])), 3)]},
                {"t": ts, "part": "nose", "pos_mm": [round(float(q[k, 0]), 3), round(float(q[k, 1]), 3), 0.0], "ang_deg": [0.0, 0.0]},
                {"t": ts, "part": "ink", "pos_mm": [round(float(ink[k, 0] - ink[0, 0]), 3), round(float(ink[k, 1] - ink[0, 1]), 3), 0.0],
                 "ang_deg": [0.0, 0.0]}]
    return out


def write_all() -> Dict:
    prov = provenance("PROPOSED DESIGN (layout; CALC masses)")
    lp = layout_parts(prov)
    write_json("layout_parts.json", lp)
    out = {"layout_parts": os.path.join(RESULTS, "layout_parts.json")}
    d = os.path.join(BUILD, "traces")
    anim = {"meta": {"evidence_status": "SIMULATION (sim2 + sim2j firmware; the recommended collar with the Rev J nose on test writer 0; synthetic writer and tremor; nothing measured)",
                     "frame": __doc__.split("Animation frame:")[1].split("Evidence status")[0].strip(),
                     "parts": ["hand", "collar", "pivot", "inner_pen", "nose", "ink"], "stabpen.provenance": provenance("SIMULATION")},
            "clips": []}
    for cname, lab in (("PD_severe", "Parkinson's action tremor, 8 mm at 5 Hz"), ("ET_severe", "essential tremor, 8 mm at 6 Hz")):
        for dn, dl in (("collar_nose", "collar + nose working"), ("none", "nothing moving")):
            fn = os.path.join(d, f"h1_g1_w0_s200_{cname}_{dn}.npz")
            if not os.path.exists(fn):
                continue
            z = np.load(fn)
            if not any(k.startswith("ch_") for k in z.files):
                continue
            anim["clips"].append({"name": f"{cname}_{dn}", "label": f"{lab}: {dl}", "t0_s": 6.0, "keyframes": keyframes_from_trace(fn, 6.0, 8.0)})
    write_json("animation.json", anim)
    out["animation"] = os.path.join(RESULTS, "animation.json")
    out["n_clips"] = len(anim["clips"])
    return out
