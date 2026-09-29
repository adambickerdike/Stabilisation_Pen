r"""config/nib.yaml: the ONE versioned definition of the nib's physical interface (writer, loader, checks).

What crosses the interface (every leaf is {value, unit, status, source}; status is one of CALC, SIM, LIT, MFR,
ASSUMPTION, PROPOSED DESIGN, UNKNOWN): the ink spring and the paper-normal force, the tilt range, the friction map, the
contact Jacobian, the static side load, the effective actuator arm, Km over the stroke (magpylib map), the moving mass
and suspension, the travel and stops, the sensors (nib Hall, DeltaPen-calibrated page sensor, IMU), the two-node thermal
parameters and the governor, the counter-face, the drive, and the C1S reference values the review checked.
The file is generated from this package's labelled inputs and the recommended design (run_study stage 'interface'),
and tests check that the code and the file agree (bnib/tests), so they cannot drift apart silently.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
from typing import Dict, Optional

import numpy as np

from . import CONFIG_NIB, VERSION
from . import candidates as CD
from . import contact as C
from . import thermal as TH
from .labels import C1S, CONTACT, DRIVE, FRICTION, MAT, SENSORS, THERMAL, val

D2R = math.pi / 180.0
SCHEMA = "bnib-nib-interface/1"


def L(value, unit: str, status: str, source: str, note: str = "") -> Dict:
    v = value
    if isinstance(v, (np.floating, np.integer)):
        v = v.item()
    if isinstance(v, float):
        v = float(f"{v:.6g}")
    if isinstance(v, (list, tuple)):
        v = [float(f"{x:.6g}") if isinstance(x, float) else x for x in v]
    out = {"value": v, "unit": unit, "status": status, "source": source}
    if note:
        out["note"] = note
    return out


def recommended_design():
    """The recommended nib (B1): the optimiser's counter-face translation nib at travel >= 1 mm (24 mm pen), else the
    hand-sized default (PROPOSED DESIGN)."""
    from . import optimise as OP
    from .sim import _opt_point
    x = _opt_point("pen24_c", 1.0)
    if x:
        return OP.build("c_counterface", "pen24", x), x
    return CD.make("c_counterface", CD.pen24()), None


def km_table(d, n: int = 5) -> Dict:
    """Km over the stroke for the design's coil geometry (magpylib full-coil map, iron images: an upper bound)."""
    from . import magnetics as MG
    s = d.travel + 0.2e-3
    from .actuators import R_CARRIER
    e = (R_CARRIER + s + 0.3e-3) / math.sqrt(2)
    g = MG.ChkGeom(w=d.w, e=e, t_m=d.t_m, t_x=d.t_c, t_y=d.t_c, s=s)
    mx = MG.km_map(g, n=n, axis="x", nb=3, nt=2, nl=10)
    return mx


def build_interface(d=None, x=None, ev: Optional[Dict] = None, km: Optional[Dict] = None, sim_cards: Optional[Dict] = None) -> Dict:
    if d is None:
        d, x = recommended_design()
    ev = ev or CD.evaluate(d, detail=False)
    hw = ev["hw"]
    km = km or km_table(d)
    thetas = (35.0, 50.0, 60.0, 75.0)
    F_s = d.F_s
    tn = TH.model_for(d.grip.od, max(hw["L_src"], 5e-3), hw["m_cu"], spreader=TH.GRAPHITE_30, wall=d.grip.wall)
    cal = None
    try:
        from .sim import deltapen_calibration
        cal = deltapen_calibration()
    except Exception:
        cal = None
    jac = {}
    for th in thetas:
        J = C.contact_jacobian(th * D2R, 0.0)
        jac[f"{th:g}"] = {"J_ink_per_nib": np.round(J["J_ink_per_nib"], 5).tolist(),
                          "slide_per_nib": np.round(J["slide_per_nib"], 5).tolist()}
    side = {f"{th:g}": {"static_N": C.static_side_load(th * D2R, F_s),
                        "friction_band_N": list(C.side_load_friction_band(th * D2R, F_s, C.mu_kinetic("oil_common", 30e-3, F_s / math.sin(th * D2R))))}
            for th in thetas}
    normal = {f"{th:g}": {"spring_along_pen_N": F_s / math.sin(th * D2R), "counterface_N": F_s / math.sin(50 * D2R)} for th in thetas}
    mu_rows = C.mu_map_table()["rows"]
    doc = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "PROPOSED DESIGN (study B, balanced two-axis nib). Nothing here was built or measured.",
        "design": {"id": "B1", "title": "two-axis translation nib with the contact-driven counter-face (24 mm pen)",
                   "candidate": d.key, "grip": d.grip.name,
                   "optimiser_point": ({k: L(v * 1e3, "mm", "PROPOSED DESIGN", "bnib/optimise.py (CMA-ES + gradient polish)")
                                        for k, v in x.items()} if x else None),
                   "doc": "docs/balanced_nib.md", "results": "results/bnib/bnib.json"},
        "frames": {"value": "page frame x, y in the paper, n out of it; pen axis a = cos(th) h + sin(th) n; nib axes u1 "
                            "(tilt plane, toward the paper side at roll 0) and u2 (lateral)", "unit": "-", "status": "CALC",
                   "source": "bnib/contact.py (as sim2/params.py and H1)"},
        "refill": {
            "type": L("ISO 12757-1 type D (D1 mini)", "-", "LIT", "CON-22"),
            "ball_diameter": L(2 * val(CONTACT["r_ball"]) * 1e3, "mm", "LIT", "CON-22 (tip class F)"),
            "length": L(val(CONTACT["refill_len"]) * 1e3, "mm", "LIT", "CON-22 (+0.3/0 mm)"),
            "mass": L(val(CONTACT["refill_mass"]) * 1e3, "g", "ASSUMPTION", "DEC-004"),
            "replacement": L("F_s +-20 %, length +0.3 mm, another ink's friction", "-", "ASSUMPTION", "labels.CONTACT"),
        },
        "ink_force": {
            "spring_force_along_pen_F_s": L(F_s, "N", "ASSUMPTION", "REQ-RVJ-N05 proposed; unverified until gate G1 (EXP-B20)"),
            "tolerance": L(val(CONTACT["F_c_tol"]), "-", "ASSUMPTION", "REQ-RVJ-N05"),
            "lowest_manufacturer_test_load_found": L(0.686, "N (normal)", "LIT", "CON-97 (Pilot US 11,993,099 B2: 70 gf, 70 deg)"),
            "iso_ballpoint_test_load": L(1.5, "N (normal)", "LIT", "CON-21 (ISO 12757-1: 1.5 +- 0.1 N at 75 deg)"),
            "minimum_reliable_force": L(None, "N", "UNKNOWN", "no source opened states one (bnib/inkforce.py); EXP-B20 measures it"),
            "counterface_face_force_F_n": L(F_s / math.sin(50 * D2R), "N", "PROPOSED DESIGN",
                                            "the face spring along the paper normal: N = F_n at every tilt (set for 0.15 N at 50 deg)"),
        },
        "paper_normal_force": {"formula": "spring along the pen: N = F_s' / (sin th - mu (v_hat . a)), F_s' = F_s -+ h_sl; "
                                          "counter-face: N = F_n (+ the friction's share)", "values_N": normal,
                               "status": "CALC", "source": "bnib/contact.py contact_force, balance.CounterFace"},
        "tilt": {"range": L(list(val(CONTACT["theta_range_deg"])), "deg", "LIT", "CON-02; REQ-RVH-002"),
                 "nominal": L(50.0, "deg", "LIT", "CON-02")},
        "friction_map": {
            "base_mu_by_ink": {k: L(val(v), "-", "LIT", "CON-13 (read from plot)") for k, v in FRICTION["mu_ink"].items()},
            "load_exponent": L(val(FRICTION["load_exp"]), "-", "ASSUMPTION", FRICTION["load_exp"].source),
            "speed_log_slope": L(val(FRICTION["speed_log"]), "-", "ASSUMPTION", FRICTION["speed_log"].source),
            "paper_factor": L(list(val(FRICTION["paper_spread"])), "x", "ASSUMPTION", "six papers in EXP-B21"),
            "static_to_kinetic": L(val(FRICTION["ms_ratio"]), "-", "ASSUMPTION", "sim2 H1 LuGre; EXP-Q01"),
            "stribeck_speed": L(val(FRICTION["v_stribeck"]) * 1e3, "mm/s", "ASSUMPTION", "sim2 H1"),
            "presliding": L(val(FRICTION["presliding"]) * 1e6, "um", "ASSUMPTION", "sim2 H1"),
            "formula": "mu = mu_ink (N / 1.2 N)^0.10 (1 + 0.04 ln(v / 15 mm/s)) x paper",
            "table": mu_rows,
        },
        "slide_friction": L(val(CONTACT["slide_friction"]), "N", "ASSUMPTION", "Rev J sim_params (refill in its bushings)"),
        "contact_jacobian": {"formula": "dx_ink = (I - n n^T)(dq - ds a), ds = (n . dq) / (n . a): at roll 0 "
                                        "dx_ink = dq1 / sin(th) h + dq2 t2, refill slide ds = cot(th) dq1",
                             "by_tilt_deg": jac, "status": "CALC", "source": "bnib/contact.py contact_jacobian"},
        "static_side_load": {"formula": "F_s cot(th) (frictionless); sliding band F_s cot(th -+ phi_f), tan phi_f = mu",
                             "by_tilt_deg": side, "status": "CALC", "source": "bnib/contact.py"},
        "effective_actuator_arm": {
            "B1_translation": L(1.0, "tip force / coil force", "CALC", "moving-coil translation: no lever"),
            "C1S_reference": L(val(C1S["L_t"]) / val(C1S["L_a"]), "coil force / tip force", "CALC",
                               "review: L_t / L_a = 76.48 / 11.5 = 6.65"),
        },
        "actuator": {
            "topology": L("moving-coil annular axial-gap 2x2 checkerboard, four N52 poles on a 1010 plate, 1010 keeper",
                          "-", "PROPOSED DESIGN", "bnib/magnetics.py"),
            "pole_side_w": L(d.w * 1e3, "mm", "PROPOSED DESIGN", "optimise.py"),
            "magnet_thickness": L(d.t_m * 1e3, "mm", "PROPOSED DESIGN", "optimise.py"),
            "coil_layer_thickness": L(d.t_c * 1e3, "mm", "PROPOSED DESIGN", "optimise.py"),
            "Km_tip_centre": L(ev["Km_tip"], "N/sqrt(W) per axis", "CALC",
                               "surrogate calibrated to magpylib (0.65 % rms holdout); image method = upper bound"),
            "Km_tip_worst_corner": L(ev["Km_tip_min"], "N/sqrt(W)", "CALC", "at the stop corner"),
            "Km_uncertainty": L([0.7, 1.0], "x", "ASSUMPTION", "DEC-041: image-method upper bound; coupons EXP-N01 / EXP-B23"),
            "Km_map_magpylib": {"stroke_grid_mm": km["xs_mm"], "Km_grid": np.round(np.array(km["Km_grid"]), 4).tolist(),
                                "Km0": km["Km0"], "variation": km["variation"], "cross_coupling_max": km["cross_max"],
                                "status": "CALC", "source": "bnib/magnetics.km_map (magpylib cuboids + iron images)"},
            "magnetic_negative_stiffness": L(0.0, "N/m", "CALC", "moving coil: the gap does not change with the stroke"),
            "parasitic_pull_on_moving_part": L(0.0, "N", "CALC", "the magnets and keeper are both on the handle"),
            "R_per_axis": L(2.5, "ohm", "PROPOSED DESIGN", "wound for a 3.7 V / 1.5 A drive"),
            "I_peak": L(val(DRIVE["I_peak"]), "A", "ASSUMPTION", DRIVE["I_peak"].source),
            "F_peak_hot_low_battery": L(ev["F_peak_hot_lowV_N"], "N", "CALC", "worst corner, coil +90 K, 3.3 V, at the "
                                        "upper-bound Km (optimise.py checks the travel at Km x 0.70)"),
        },
        "moving_parts": {
            "m_eff_tip": L(ev["m_eff_tip_g"], "g", "CALC", "coils + former + carrier + refill + holder + Ti sleeve + magnet + 1/3 wires"),
            "suspension_k_tip": L(ev["k_tip_N_m"], "N/m", "CALC", "four Ti-6Al-4V wires, fixed-guided (flexure.py)"),
            "wire_diameter": L(d.wire.d * 1e3, "mm", "PROPOSED DESIGN", "optimise.py"),
            "wire_free_length": L(d.wire.L * 1e3, "mm", "PROPOSED DESIGN", "optimise.py"),
            "goodman_SF_full_travel": L(ev["fatigue"]["goodman_SF_full_travel"], "-", "CALC", "43.2 M cycles, Kt 1.8, AMF-20 low end x 0.85"),
            "modes_Hz": {k: (np.round(v, 1).tolist() if isinstance(v, (list, tuple)) else round(float(v), 1)) for k, v in ev["modes"].items()},
            "bandwidth": L(ev["bandwidth_Hz"], "Hz", "CALC", "first parasitic mode / 3"),
        },
        "travel": {"usable": L(d.travel * 1e3, "mm (radius)", "PROPOSED DESIGN", "optimise.py eps_T"),
                   "stop": L((d.travel + 0.2e-3) * 1e3, "mm", "PROPOSED DESIGN", "soft stops"),
                   "under_load_worst": L(ev["travel_under_load_mm"], "mm", "CALC", "35 deg, 12 Hz, hot coil, 3.3 V")},
        "sensors": {
            "nib_hall": {"part": L("TMAG5170-A1 3-D Hall over a 1 mm N52 magnet on the carrier", "-", "MFR", "OPT-44/OPT-53"),
                         "noise_tip_20kSPS": L(ev["sensing"]["nib_hall_noise_um_20kSPS"], "um rms", "CALC", "140 uT rms / field gradient"),
                         "noise_tip_1kHz": L(ev["sensing"]["nib_hall_noise_um_1kHz"], "um rms", "CALC", ""),
                         "rate": L(val(SENSORS["hall_rate"]), "Hz", "MFR", SENSORS["hall_rate"].source),
                         "delay": L(50.0, "us", "ASSUMPTION", "sim2")},
            "page_sensor": {
                "model": L("DeltaPen-calibrated: held error redrawn every 10 ms (window differences median 23.6 um, mean "
                           "68.3 um), idle drift, per-run scale error", "-", "LIT + CALC", "OPT-02, OPT-75; bnib/sim.py"),
                "window_error_median": L(val(SENSORS["page_err_window_median"]) * 1e6, "um", "LIT", "OPT-02"),
                "window_error_mean": L(val(SENSORS["page_err_window_mean"]) * 1e6, "um", "LIT", "OPT-02"),
                "idle_drift": L(val(SENSORS["page_idle_drift"]) * 1e3, "mm/s per axis", "LIT", "OPT-02 (2.6 mm/min)"),
                "scale_error_median": L(list(val(SENSORS["page_mdape_writing"])), "-", "LIT", "OPT-75 (Fig. 7, X/Y at 2.5-5 cm/s)"),
                "held_error_lognormal": ({"median_um": cal["median_m"] * 1e6, "log_sd": cal["sigma"], "status": "CALC",
                                          "source": "Monte Carlo fit (bnib/sim.deltapen_calibration)"} if cal else None),
                "rate": L(val(SENSORS["page_rate"]), "Hz", "LIT", "OPT-01"),
                "latency": L(val(SENSORS["page_latency"]) * 1e3, "ms", "ASSUMPTION", SENSORS["page_latency"].source),
                "ideal_bound_noise": L(val(SENSORS["page_ideal_noise"]) * 1e6, "um rms", "ASSUMPTION", "a labelled bound only"),
            },
            "imu": {"part": L("LSM6DSV16X class", "-", "MFR", "OPT-37"),
                    "tilt_error_sd": L(val(SENSORS["tilt_err_sd"]) / D2R, "deg", "ASSUMPTION", "EXP-B28"),
                    "roll_error_sd": L(val(SENSORS["roll_err_sd"]) / D2R, "deg", "ASSUMPTION", "EXP-B28")},
        },
        "thermal_two_node": {
            "C_coil": L(tn.C_c, "J/K", "CALC", "copper mass x 385 J/kgK x 1.5 (bond, former: ASSUMPTION)"),
            "R_coil_shell": L(tn.R_cs, "K/W", "ASSUMPTION", THERMAL["R_cs"].source),
            "C_shell": L(tn.C_s, "J/K", "ASSUMPTION", "6 J/K at 24 mm, scaled with the diameter"),
            "R_shell_ambient": L(tn.R_sa, "K/W", "CALC", "fin model of the PEEK shell with a 30 mm graphite spreader (AMF-158)"),
            "T_room_max": L(tn.T_room, "degC", "PROPOSED DESIGN", THERMAL["T_room"].source),
            "T_skin_target": L(tn.T_s_target, "degC", "LIT", "AMF-34 (IEC 60601-1, 41 degC)"),
            "T_skin_limit": L(val(THERMAL["T_skin_max"]), "degC", "LIT", "AMF-35 (ECMA-287)"),
            "T_coil_max": L(tn.T_c_max, "degC", "ASSUMPTION", THERMAL["T_coil_max"].source),
            "governor": L("current x g, g = min(1, sqrt(clip((T_c,max - 10 K - T_c)/10 K)), sqrt(clip((T_skin,target - T_s)/1.5 K)))",
                          "-", "PROPOSED DESIGN", "bnib/thermal.py; in the sim servo loop"),
        },
        "counter_face": {
            "principle": L("the ink spring pushes a face on the handle against the refill's rear end; the face is set "
                           "parallel to the paper and spring-loaded along its normal; a follower stop leaves the refill "
                           "when the ball lifts", "-", "PROPOSED DESIGN", "bnib/balance.py CounterFace"),
            "orientation_driver": L("two slow positioners from the IMU (imu2); fallbacks: slide cam + one roll positioner, "
                                    "or slide cam + keyed grip", "-", "PROPOSED DESIGN", "balance.py"),
            "follower_gap": L(_rules().get("face_gap_mm", 0.15), "mm along the face normal", "PROPOSED DESIGN",
                              "tuned in bnib/sim.py on tuning writers (results/bnib/rules.json)" if _rules() else
                              "default before tuning (bnib/sim.py)"),
            "servo_inner_bandwidth": L(_rules().get("servo_fi", 150.0), "Hz", "PROPOSED DESIGN",
                                       "filtered servo, tuned (results/bnib/rules.json)" if _rules() else "default before tuning"),
            "follower_time_constant": L(0.3, "s", "PROPOSED DESIGN", "bnib/sim.py"),
            "rolling_contact_mu": L(0.005, "-", "ASSUMPTION", "3 mm ball on a hardened face"),
            "guide_friction": L(0.004, "N", "ASSUMPTION", "flexure-guided face"),
            "residual_contact_mean": L(None, "N", "CALC", "see results/bnib/bnib.json balance_quality"),
        },
        "drive": {"V_bus": L(val(DRIVE["V_bus"]), "V", "ASSUMPTION", DRIVE["V_bus"].source),
                  "V_low": L(val(DRIVE["V_low"]), "V", "ASSUMPTION", DRIVE["V_low"].source),
                  "driver_efficiency": L(val(DRIVE["driver_eff"]), "-", "ASSUMPTION", DRIVE["driver_eff"].source),
                  "electronics": L(list(val(DRIVE["electronics_W"])), "W", "CALC", DRIVE["electronics_W"].source),
                  "cell_usable": L(val(DRIVE["cell_Wh_usable"]), "Wh", "MFR", DRIVE["cell_Wh_usable"].source)},
        "power_calc": {"P_cont_duty_A": L(ev["P_cont_W"], "W", "CALC", "mean over 35/50/60/75 deg, 0.2 mm rms at 8 Hz, 70 % contact"),
                       "P_35deg_duty_A": L(ev["P_mean_W_by_theta"][35.0], "W", "CALC", ""),
                       "battery_h": L(ev["battery_h"], "h", "CALC", "electronics-dominated")},
        "failure_state": ev["failure_state"],
        "c1s_reference": {
            "F_c": L(val(C1S["F_c"]), "N", "ASSUMPTION", C1S["F_c"].source),
            "L_t": L(val(C1S["L_t"]) * 1e3, "mm", "CALC", C1S["L_t"].source),
            "L_a": L(val(C1S["L_a"]) * 1e3, "mm", "CALC", C1S["L_a"].source),
            "Km_act": L(val(C1S["Km_act"]), "N/sqrt(W)", "CALC", C1S["Km_act"].source),
            "static_power_35_50_75": L([C.review_static_power(t)["P_W"] for t in (35.0, 50.0, 75.0)], "W", "CALC",
                                       "the review's section 4, reproduced (bnib/contact.review_static_power)"),
        },
    }
    if sim_cards and sim_cards.get("B1"):
        b1 = sim_cards["B1"]
        src = "bnib/sim.py -> results/bnib/bnib.json (sim.cards.B1; the full cards and every case are there)"
        doc["simulated"] = {
            "note": "headline SIMULATION numbers for this nib (sim2, synthetic writers and tremor, DeltaPen-calibrated page "
                    "sensor, the frozen tracker); results, not interface parameters",
            "tremor_left_ratio_tracker": L(b1.get("tremor_left_ratio_mean"), "1", "SIM", src, "mean over the ET/PD cells"),
            "tremor_left_ratio_perfect_knowledge": L(b1.get("tremor_left_ratio_oracle_mean"), "1", "SIM", src,
                                                     "the mechanism's limit"),
            "nib_power_while_correcting": L(b1.get("P_nib_mW_tremor_mean"), "mW", "SIM", src),
            "nib_power_tremor_free": L(b1.get("P_nib_mW_clean_mean"), "mW", "SIM", src),
            "clean_writing_moved": L(b1.get("clean_moved_um_mean"), "um", "SIM", src, "false correction"),
            "n_writers": L(b1.get("n_writers"), "1", "SIM", src),
        }
    return doc


def _rules() -> Dict:
    from . import RESULTS
    p = RESULTS / "rules.json"
    if p.exists():
        try:
            return json.load(open(p))["chosen"]
        except Exception:
            return {}
    return {}


def write(doc: Dict, path=CONFIG_NIB) -> str:
    import yaml
    head = ("# config/nib.yaml - the nib's physical interface (ONE versioned file; study B, round 4)\n"
            "# Generated by `python3 -m bnib.run_study` (bnib/interface.py) from the labelled inputs and the recommended\n"
            "# design.  Every leaf: value, unit, status (CALC | SIM | LIT | MFR | ASSUMPTION | PROPOSED DESIGN | UNKNOWN),\n"
            "# source (ledger id or file).  Nothing here was built or measured.  Do not edit by hand: change the inputs\n"
            "# in bnib/labels.py or the design, re-run, and bump the version.\n")
    txt = yaml.safe_dump(json.loads(json.dumps(doc, default=float)), sort_keys=False, width=120, allow_unicode=False)
    with open(path, "w") as f:
        f.write(head + txt)
    return str(path)


def load(path=CONFIG_NIB) -> Dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)


def leaves_missing_status(doc: Dict, prefix: str = "") -> list:
    """Leaves that are dicts with a value but no unit or status (the check the tests run)."""
    bad = []
    if isinstance(doc, dict):
        if "value" in doc and ("unit" not in doc or "status" not in doc):
            bad.append(prefix)
        for k, v in doc.items():
            if isinstance(v, dict):
                bad += leaves_missing_status(v, f"{prefix}/{k}")
    return bad
