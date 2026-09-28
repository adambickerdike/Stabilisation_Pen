"""Interface files (results/revH/), the assembled results JSON, figures with CSV twins, the replay and the evidence rows.

Stages callable from run_study: report (everything below), interfaces (tip_params.json + layout.json only).
Evidence labels: SIM (model H1 runs), CALC (formulas, design models), MFR (ledger id), LITERATURE (ledger id), ASSUMPTION.
"""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from stabpen import provenance
from . import catalog as CT
from . import geometry as GE
from . import revh as RH

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVH_DIR = os.path.join(ROOT, "results", "revH")
OPT = os.path.join(ROOT, "results", "opt")
CACHE = os.path.join(OPT, "_cache")


def _stage(name):
    p = os.path.join(CACHE, f"inertial_stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _mean(rows, f):
    v = [f(r) for r in rows]
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def grid_summary(grid: Dict) -> Dict:
    """Mean over test seeds per (tracker, r_rot, tremor kind, amplitude, frequency)."""
    out = {}
    for tag, rows in grid["rows"].items():
        for r in rows:
            k = (tag, r["r_rot"], r["kind"], r["amp_mm"], r["f0"])
            out.setdefault(k, []).append(r)
    summ = []
    for (tag, rr, kind, amp, f0), rows in sorted(out.items()):
        row = {"tracker": tag, "r_rot": rr, "kind": kind, "amp_mm": amp, "f0": f0, "n": len(rows),
               "unmod_e_rms_um": _mean(rows, lambda r: r["unmod_e_rms_um"]),
               "akf_ratio": _mean(rows, lambda r: r["akf"]["ratio"]), "akf_band_ratio": _mean(rows, lambda r: r["akf"]["band_ratio"]),
               "akf_q_sat": _mean(rows, lambda r: r["akf"]["q_sat_frac"]),
               "akf_F_tip_rms_N": [_mean(rows, lambda r: r["akf"]["F_tip_rms_N"][0]), _mean(rows, lambda r: r["akf"]["F_tip_rms_N"][1])]}
        if "oracle" in rows[0]:
            row["oracle_ratio"] = _mean(rows, lambda r: r["oracle"]["ratio"])
            row["oracle_q_sat"] = _mean(rows, lambda r: r["oracle"]["q_sat_frac"])
        summ.append(row)
    return summ


def power_final(F_rms_axes, d: Optional[RH.RevH] = None):
    """Recompute the tip copper loss for the final design constant Km_tip (CALC)."""
    d = d or RH.RevH()
    Pcu = float(sum(f * f for f in F_rms_axes) / d.Km_tip ** 2)
    return {"P_cu_W": Pcu, "P_total_W": CT.ELECTRONICS["base_W"] + 0.012 + Pcu}


# ------------------------------------------------------------------ interface files for the other agents
def write_tip_params(final=True, addon_decision: Optional[Dict] = None):
    d = RH.RevH()
    ms = RH.masses(d)
    geo = GE.layout(d)
    grid = _stage("grid")
    th = math.radians(50.0)
    Fpk_act = d.Km_act * math.sqrt(3.7 * 1.5)
    Fc_act = d.Km_act * math.sqrt(0.35)
    res = {}
    if grid:
        sm = grid_summary(grid)
        B_or = [r["oracle_ratio"] for r in sm if r["tracker"] == "ship" and r["kind"] == "trans"]
        rv = [r for r in sm if r["tracker"] == "revh" and r["kind"] == "trans" and r["r_rot"] == 0.5]
        Fr = [r["akf_F_tip_rms_N"] for r in sm if r["tracker"] == "revh"]
        pw = power_final(np.mean(Fr, axis=0).tolist(), d)
        A = grid["A"]["rows"]
        res = {"B_oracle_ratio_range": [min(B_or), max(B_or)],
               "B_revh_tracker_ratio_8_12Hz_1_2mm": [min(r["akf_ratio"] for r in rv if r["f0"] >= 8 and r["amp_mm"] >= 1),
                                                    max(r["akf_ratio"] for r in rv if r["f0"] >= 8 and r["amp_mm"] >= 1)],
               "A_oracle_ratio_range": [min(r["oracle"]["ratio"] for r in A), max(r["oracle"]["ratio"] for r in A)],
               "A_P_cu_with_bias_W": float(np.mean([r["akf"]["P_cu_W"] for r in A])),
               "A_P_cu_without_bias_W": float(np.mean([r["akf"]["P_cu_no_bias_W"] for r in A])),
               "A_writing_force_std_N": float(np.mean([r["akf"]["N_std_N"] for r in A])),
               "B_tip_force_rms_N": np.mean(Fr, axis=0).tolist(), "B_power_W": pw,
               "label": "SIM (model H1, test seeds 200-203, first use; see results/opt/inertial_opt.json)"}
    cell = CT.CELLS[d.cell]
    out = {
        "meta": provenance.metadata("SIMULATION + CALCULATION (Rev H active nose, model H1; nothing measured)" if final else
                                    "PROVISIONAL", seeds={"test": [200, 201, 202, 203], "train": [300, 301]},
                                    extra={"script": "opt/inertial/report.py", "doc": "docs/opt_inertial.md"}),
        "architecture": "B",
        "architecture_note": ("B = a skid ring on the FIXED front sleeve carries the writing force; the refill carrier (the moving nose) "
                              "tilts on a 2-axis flexure gimbal so the ball moves up to +/-3 mm; the refill slides axially on a soft "
                              "constant-force spring so the ball stays on the paper. Chosen over A (rigid nose carrying the load) by "
                              "simulation: A's ceiling with perfect knowledge is 0.15-0.77 of the ink error against 0.08-0.24 for B, A "
                              "needs 0.41 W of copper loss with a bias spring (1.9 W without) against about 0.004 W for B, and a rigid "
                              "nose must press the tip into the paper for tilt-plane corrections (0.38 N rms writing-force change)."),
        "results_summary": res,
        "tip_travel_mm": {"usable_radius": d.travel * 1e3, "mechanical_stop_radius": (d.travel + 0.5e-3) * 1e3,
                          "label": "PROPOSED; SIM: never at its limit with perfect knowledge of 2 mm tremor except peaks at 10-12 Hz (see sweep)"},
        "refill_axial_slide_mm": {"value": 8.0, "note": "delta cot(theta) for the tilt-plane correction (2.5 mm at 3 mm, 50 deg) plus the tilt-dependent ball protrusion 1.1-7.3 mm at 75-35 deg (skid contact radius 5.5 mm); constant-force spring 0.15 N (P0 value, ASSUMPTION)",
                                  "label": "CALC"},
        "moving_mass_at_tip_g": {"value": round(ms["moving_mass_at_tip_g"], 3), "total_moving_g": round(ms["nose_g"], 3),
                                 "inertia_about_pivot_g_mm2": round(ms["nose_inertia_about_pivot_g_mm2"], 1),
                                 "label": "CALC (parts in opt/inertial/revh.nose_parts: Ti carrier, D1 refill, Al arm, 4 NdFeB magnets)"},
        "suspension_stiffness_N_per_m": {"value": round(d.k_r / d.z_p ** 2, 2), "gimbal_bending_Nm_per_rad": d.k_r,
                                         "label": "ASSUMPTION (laser-cut cross-strip gimbal, 301 full-hard / 17-7PH, AMF-20)"},
        "actuator": {"type": "2-axis moving-magnet flat voice coils: 4 NdFeB magnets on the nose's rear arm, 4 flat coils with a soft-iron "
                             "back ring in the handle; each magnet moves parallel to its coil (shear) for its own axis",
                     "Km_actuator_N_per_sqrtW_per_axis": round(d.Km_act, 3), "Km_at_tip_N_per_sqrtW_per_axis": round(d.Km_tip, 3),
                     "lever_tip_per_magnet": round(d.lever, 3),
                     "magnet_mm": [d.mag_w * 1e3, d.mag_l * 1e3, d.mag_t * 1e3], "coil_thickness_mm": d.coil_t * 1e3,
                     "magnet_stroke_mm": round(d.travel / d.lever * 1e3, 3),
                     "force_limit_at_tip_N": {"peak": round(Fpk_act / d.lever, 3), "continuous": round(Fc_act / d.lever, 3)},
                     "drivers": "2 x TI DRV8214 H-bridge with current mirror (AMF-37), 3.7 V cell",
                     "label": "CALC (adjoint design model opt/inertial/adjoint.py; magnet and copper data MFR AMF-28/AMF-29; leakage, fill and end-turn factors ASSUMPTION); peak = Km sqrt(3.7 V x 1.5 A), continuous = Km sqrt(0.35 W) per axis (ASSUMPTION thermal)"},
        "static_tip_load_N": {"refill_spring_transverse": round(0.15 / math.sin(th) * math.cos(th), 4),
                              "ball_friction": round(0.15 * 0.15 / math.sin(th), 4),
                              "bias": "a fixed spring or magnet offset cancels the 0.126 N refill-spring component (constant in the handle frame when the grip sleeve fixes the roll)",
                              "label": "CALC (F_c 0.15 N, mu_ball 0.15, 50 deg; ASSUMPTION values from config/pencil.yaml)"},
        "servo": {"type": "PID position loop on the 3-D Hall reading of the arm magnet; reference = -(tracker estimate) mapped to the tip",
                  "bandwidth_Hz": d.servo_hz, "damping": d.servo_zeta, "inner_rate_Hz": 10000.0,
                  "tip_reference_slew_m_s": d.slew,
                  "label": "ASSUMPTION (modelled in H1 as the stage's 2nd-order follower); sensitivity in the sweep"},
        "latency_ms": {"imu_to_estimate": 1.4, "controller_tick": 0.5, "servo_group_delay_at_12Hz": round(1e3 * 2 * d.servo_zeta / (2 * math.pi * d.servo_hz), 2),
                       "label": "ASSUMPTION built on MFR OPT-37 (fusion) and CALC for the 2nd-order servo"},
        "power_model": {"formula": "P_total = 0.065 + 0.012 + (F_tip_rms_t1^2 + F_tip_rms_t2^2) / Km_tip^2   [W]; F_tip = m_eff q'' + k_s q + ball loads - bias",
                        "Km_tip_N_per_sqrtW": round(d.Km_tip, 4), "typical_W": res.get("B_power_W", {}).get("P_total_W"),
                        "battery": {"part": cell.name, "ledger": cell.src, "usable_Wh": round(cell.Wh, 3),
                                    "life_h_writing_continuously": round(cell.Wh / res["B_power_W"]["P_total_W"], 1) if res else None},
                        "label": "CALC on SIM forces; 0.065 W base electronics and 0.012 W drivers/Hall ASSUMPTION"},
        "geometry_mm": {"pivot_z": geo["pivot_z"], "actuator_z": geo["actuator_z"], "front_opening_d": geo["front_opening_d"],
                        "skid_ring": {"contact_radius": geo["skid_contact_radius"], "od": round(geo["front_opening_d"] + 3.0, 2),
                                      "ball_protrusion_at_50deg": geo["ball_protrusion_mm"],
                                      "note": "C-shaped heel skid (open at the front for visibility) - feel and visibility ASSUMPTION, to test (EXP-H03 extension)"},
                        "grip_zone_z": [geo["grip_zone"]["z0"], geo["grip_zone"]["z1"]], "finger_pads_z": geo["hand"]["finger_pads_z"],
                        "web_z": geo["hand"]["web_z"], "handle_od": geo["handle_od"], "length": geo["length"], "pen_tilt_deg": 50.0,
                        "tilt_range_deg": [35.0, 75.0], "label": "PROPOSED DESIGN (opt/inertial/geometry.py, mechanics/cad/revH_pen.py)"},
        "mass_g": {"pen_without_inertial_module": round(ms["total_g"], 2), "handle": round(ms["handle_g"], 2), "moving_nose": round(ms["nose_g"], 2),
                   "com_mm_from_tip": round(ms["com_mm"], 1), "label": "CALC from assumed parts +10 % wiring"},
        "inertial_addon": addon_decision or {"status": "evaluated in docs/opt_inertial.md; see layout.json 'optional' components"},
        "tracker": {"default": "results/opt/tracker_models/akf_ship.json (shipped)", "rev_h_setting": "results/opt/inertial_tracker_revh.json",
                    "note": "the Rev H setting opens the frequency gate and the amplitude cap for the larger travel; chosen on training seeds by a pre-declared false-correction rule"},
    }
    os.makedirs(REVH_DIR, exist_ok=True)
    path = os.path.join(REVH_DIR, "tip_params.json" if final else "tip_params_provisional.json")
    provenance.write_json(path, out)
    return out


def write_layout(addon: Optional[Dict] = None, addon_recommended: bool = False):
    d = RH.RevH()
    geo = GE.layout(d, addon=addon)
    meta = provenance.metadata("PROPOSED DESIGN (dimensioned concept; CALC masses; ASSUMPTION dimensions) - Rev H active-nose pen, architecture B",
                               extra={"script": "opt/inertial/geometry.py (also mechanics/cad/revH_pen.py)", "doc": "docs/opt_inertial.md",
                                      "inertial_addon_recommended": addon_recommended})
    out = {"meta": meta, **{k: v for k, v in geo.items()}}
    os.makedirs(REVH_DIR, exist_ok=True)
    provenance.write_json(os.path.join(REVH_DIR, "layout.json"), out)
    return out


def stage_interfaces(quick=False):
    write_tip_params(final=True)
    write_layout(addon=None)
