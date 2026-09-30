r"""results/revK/sim_params.json in the schema of results/revJ/sim_params.json, so that the whole-pen simulator (sim2 /
sim2j) can run Rev K later (CALCULATION from the Rev K layout and study B; labels on every value).

What differs from Rev J's file:
  nose       a translation nib has no gimbal.  The block keeps Rev J's keys with a VIRTUAL PIVOT 10 m behind the tip
             (every carrier point then moves within 0.7 % of the ball's motion; stiffness, inertia and angles are mapped by
             z_p^2 and z_p), so sim2j's two-hinge nose can run it unchanged; the native two-prismatic-joint values are in
             'nib'.  The servo bandwidth obeys DEC-050's 2.5 x rule (the lowest structural mode, ball free and stuck).
  refill     the refill slides in rolling guides; its rear end rests on the counter-face head's puck (the ink force F_n
             along the paper normal, a float gap each side, the pen lift by the follower); no pen-lift drum.
  heel_wheel present only in the heel-module variant ('fitted': false in the base pen); its values are study D's.
  endcap     absent (DEC-051).
An adapter note lists what sim2j/revj.py must change to load this file (it reads 'refill_holder' and 'ec_shell' from the
layout, and the layout's 'pivot_z').
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from . import ensure_paths
from . import params as PR
from .params import val

ensure_paths()
from revj import budgets as RBU  # noqa: E402

Z_P_VIRTUAL = 10.0          # m


def L(value, unit, label, source, note=None):
    d = {"value": value, "unit": unit, "label": label, "source": source}
    if note:
        d["note"] = note
    return d


def build(lay: Dict, nibsum: Dict, hd: Dict, fc: Dict, fc_h: Dict, bud: Dict) -> Dict:
    comps = lay["components"]
    c = {x["id"]: x for x in comps}
    moving_ids = {x["id"] for x in comps if x.get("moves_with") == "nib"}
    handle = [x for x in comps if x["id"] not in moving_ids]
    mh = RBU.mass_properties(handle)
    mh_heel = RBU.mass_properties(handle + lay["heel_variant"]["components"])
    mv = RBU.mass_properties([x for x in comps if x["id"] in moving_ids])
    zp = Z_P_VIRTUAL
    m_eff = nibsum["m_move_g"] * 1e-3 * (1 + RBU.WIRING)
    ld = nibsum["leads"]["options"]["revK_C17200_0.100"]
    k_tip = ld["wire_stage"]["k_lat_N_m"]
    Km = nibsum["Km_tip_revK"]
    R_c = val(PR.NIB["coil_R_ohm"])
    md = nibsum["modes"]["by_restraint"]["revK_ball_guide"]
    bw_allowed = md["servo_bw_max_worst_Hz"]
    servo = min(max(val(PR.NIB["servo_bw_min_Hz"]), 40.0), bw_allowed)
    travel = val(PR.B1["travel_mm"]) * 1e-3
    stop = val(PR.B1["stop_mm"]) * 1e-3
    z_coil = 0.5 * (c["coil_x"]["z0"] + c["coil_y"]["z1"]) * 1e-3
    w = fc["window"]
    pw = bud["power"]["rows"]
    th_rise = bud["heat"]["rows"]["steady_1mm"]
    sp = {
        "frames": {"pen": "z from the ball tip at 50 deg (nib centred) toward the back; x in the tilt plane away from the "
                          "paper; y lateral; metres",
                   "gimbal_z": zp, "gimbal_note": "virtual pivot for a translation nib (see 'nose' and 'nib')"},
        "handle": {
            "mass_base_kg": L(mh["mass_g"] * 1e-3, "kg", "CALC", "revk/layout + revj/budgets.mass_properties (+10 % wiring)",
                              "handle = every part except the moving nib (carrier, coils, flange, position magnet, refill, "
                              "puck)"),
            "com_base_m": L([v * 1e-3 for v in mh["com_mm"]], "m", "CALC", "revk/layout"),
            "inertia_base_kg_m2": L((np.array(mh["inertia_g_mm2"]) * 1e-9).tolist(), "kg m^2", "CALC", "revk/layout"),
            "mass_with_heel_kg": L(mh_heel["mass_g"] * 1e-3, "kg", "CALC", "revk/layout heel-module variant"),
            "com_with_heel_m": L([v * 1e-3 for v in mh_heel["com_mm"]], "m", "CALC", "revk/layout"),
            "inertia_with_heel_kg_m2": L((np.array(mh_heel["inertia_g_mm2"]) * 1e-9).tolist(), "kg m^2", "CALC", "revk/layout"),
            "finger_pads_z_m": L([z * 1e-3 for z in val(PR.ENVELOPE["finger_pads_z_mm"])], "m", "ASSUMPTION",
                                 "Rev H hand model (unchanged)"),
            "web_z_m": L(val(PR.ENVELOPE["web_z_mm"]) * 1e-3, "m", "ASSUMPTION", "Rev H hand model"),
        },
        "skid_ring": {
            "contact_radius_m": L(fc["R_s_mm"] * 1e-3, "m", "CALC", "revk/frontend.front_close (page sensor at the bottom)"),
            "ring_plane_z_m": L(fc["z_ring_mm"] * 1e-3, "m", "CALC", "p(50 deg) = (R cos 50 - r_b) / sin 50"),
            "open_deg_top": L(val(PR.FRONT["open_deg"]), "deg", "ASSUMPTION", "DEC-034"),
            "tube_radius_m": L(0.0006, "m", "ASSUMPTION", "sim2 native C ring (31 capsules)"),
            "mu": L(0.12, "-", "ASSUMPTION", "sim2 / HW1 skid friction (EXP-Q01)"),
        },
        "nose": {
            "joint": L("two hinges (x, y) about a virtual pivot 10 m behind the tip: a translation nib", "-",
                       "PROPOSED DESIGN", "revk/simparams (maps B1's two prismatic joints within 0.7 %)"),
            "mass_kg": L(mv["mass_g"] * 1e-3, "kg", "CALC", "revk/layout moving parts (+10 %)"),
            "com_z_m": L(mv["com_mm"][2] * 1e-3, "m", "CALC", "revk/layout"),
            "inertia_about_pivot_kg_m2": L(m_eff * zp ** 2, "kg m^2", "CALC", "m_eff x z_p^2 (virtual pivot)"),
            "m_eff_tip_kg_layout": L(m_eff, "kg", "CALC", "revk/nib.summary (moving parts +10 %)"),
            "m_eff_tip_kg_studyB": L(val(PR.B1["m_eff_tip_g"]) * 1e-3, "kg", "CALC", "config/nib.yaml"),
            "flexure_k_Nm_per_rad": L(k_tip * zp ** 2, "N m/rad", "CALC", "k_tip x z_p^2; k_tip of four 0.10 mm C17200 wires "
                                      f"({k_tip:.3f} N/m, bnib/flexure.wire_stage)"),
            "magnetic_negative_k_Nm_per_rad": L([0.0, 0.0], "N m/rad", "CALC", "moving coil between fixed magnets: no pull "
                                                 "on the moving part (study B)"),
            "axial_magnetic_pull_N": L(0.0, "N", "CALC", "the keeper's pull stays inside the stator (handle)"),
            "damping_ratio": L(0.02, "-", "ASSUMPTION", "sim2 structural damping (the ball guide's rolling friction is "
                               "added as Coulomb friction in 'nib')"),
            "usable_angle_rad": L(travel / zp, "rad", "CALC", "travel / z_p"),
            "stop_angle_rad": L(stop / zp, "rad", "CALC", "stop / z_p"),
            "actuator_z_m": L(z_coil, "m", "CALC", "the coils' plane (in front of the virtual pivot; lever ratio "
                              f"{(zp - z_coil) / zp:.4f})"),
            "Km_act_N_per_sqrtW": L(Km["x"], "N/sqrt(W)", "CALC", "Rev K buildable coil, x layer (image method: upper bound)"),
            "Km_tip_N_per_sqrtW": L(Km["x"], "N/sqrt(W)", "CALC", "translation: tip = actuator; y layer "
                                    f"{Km['y']:.3f}, min over the stroke {Km['x_min_over_stroke']:.3f}"),
            "coil_R_ohm": L(R_c + 2 * ld["R_wire_ohm"], "ohm", "CALC", "2.5 ohm coil + two C17200 wire leads"),
            "K_f_N_per_A": L(Km["x"] * math.sqrt(R_c), "N/A", "CALC", "Km sqrt(R_coil)"),
            "coil_L_H": L(1e-4, "H", "ASSUMPTION", "sim2 value"),
            "coil_Rth_K_W": L(val(PR.THERMAL["R_int_coil_K_W"]) + 69.0, "K/W", "CALC",
                              "R_int 15 K/W + the shell fin over the 8.5 mm stator (revk/budgets.fin_R)"),
            "coil_Cth_J_K": L(0.5, "J/K", "ASSUMPTION", "sim2 value"),
            "I_max_A": L(ld["I_max_3V3_A"], "A", "CALC", "3.3 V over the coil, leads and the DRV8214's 0.24 ohm"),
            "V_bus_V": L(3.3, "V", "ASSUMPTION", "regulated drive rail"),
            "servo_hz": L(servo, "Hz", "PROPOSED DESIGN",
                          f"DEC-050 2.5 x rule: the lowest mode (ball stuck, worst case) allows {bw_allowed:.1f} Hz, nominal "
                          f"{md['servo_bw_max_nominal_Hz']:.1f} Hz; REQ-BNIB-006 asks >= 40 Hz",
                          "study B's SIM ran an 80 Hz position loop with a 100 Hz inner loop; on the tuning writers "
                          "40 / 100 Hz changed the ink error by +0.5 % and 40 / 46 Hz by +7 % (results/revK/"
                          "servo_bandwidth_sim.json, SIM); the test writers remain (EXP-K25, proposed)"),
            "inner_hz": L(round(min(46.0, bw_allowed), 1), "Hz", "PROPOSED DESIGN",
                          "the inner loop also inside the 2.5 x rule (the conservative reading; setting C of "
                          "results/revK/servo_bandwidth_sim.json: +7 % ink error, -29 % nib power on the tuning cells, SIM)"),
            "servo_zeta": L(0.7, "-", "ASSUMPTION", "Rev H"),
            "slew_m_s": L(0.6, "m/s", "ASSUMPTION", "Rev H"),
            "latency_s": L(0.0006, "s", "ASSUMPTION", "study N"),
            "first_parasitic_mode_hz": L(md["lowest_stuck_worst_Hz"], "Hz", "CALC",
                                         "bnib/flexure.loaded_modes, ball stuck, worst of tilt x refill EI x pre-sliding "
                                         f"(ball free: first structural {md['first_free_nominal_Hz']:.0f} Hz)"),
        },
        "nib": {
            "joint": L("two prismatic joints (x, y) across the pen; axial and tilt fixed by the ball thrust guide", "-",
                       "PROPOSED DESIGN", "revk/layout"),
            "moving_mass_kg": L(m_eff, "kg", "CALC", "carrier, coils, flange, magnet, refill, puck (+10 %)"),
            "k_N_per_m": L(k_tip, "N/m", "CALC", "four 0.10 mm C17200 wires (bnib/flexure.wire_stage)"),
            "travel_m": L(travel, "m", "CALC", "study B"),
            "stop_m": L(stop, "m", "PROPOSED DESIGN", "study B soft stops; Rev K lateral stop bush (1e6 N/m, ASSUMPTION)"),
            "Km_x_y_N_per_sqrtW": L([Km["x"], Km["y"]], "N/sqrt(W)", "CALC", "revk/nib.buildable_coil (upper bound)"),
            "Km_scale_range": L(list(val(PR.B1["Km_scale_range"])), "-", "ASSUMPTION", "DEC-041 (EXP-B23 measures)"),
            "Km_variation_over_stroke": L(nibsum["buildable_coil"]["variation"], "-", "CALC", "force map over +-stop"),
            "coulomb_friction_N": L(nibsum["couple"]["worst"]["ball_guide_friction_mN"] * 1e-3, "N", "CALC",
                                    "ball guide: rolling resistance 0.001 (ASSUMPTION) x the couple's ball load at 35 deg"),
            "modes_Hz": L({"free_first_structural_nominal": md["first_free_nominal_Hz"],
                           "stuck_lowest_nominal": md["lowest_stuck_nominal_Hz"], "stuck_lowest_worst": md["lowest_stuck_worst_Hz"]},
                          "Hz", "CALC", "revk/nib.modes_grid"),
            "servo_bw_allowed_Hz": L({"nominal": md["servo_bw_max_nominal_Hz"], "worst": md["servo_bw_max_worst_Hz"]}, "Hz",
                                     "CALC", "DEC-050 2.5 x rule"),
        },
        "refill": {
            "joint": L("slide along the carrier axis (rolling guides)", "-", "PROPOSED DESIGN", "study B"),
            "moving_mass_kg": L((0.84 + val(PR.HEAD["puck"])["mass_g"]) * 1e-3, "kg", "CALC", "refill 0.84 g + puck 0.06 g"),
            "slide_range_m": L([-(fc["protrusion_mm"]["35"] - fc["z_ring_mm"]) * 1e-3 - 0.0015,
                                (fc["z_ring_mm"] - fc["protrusion_mm"]["75"]) * 1e-3 + 0.0015], "m", "CALC",
                               "revk/frontend (35-75 deg) +- the nib correction's 1.5 mm at 35 deg"),
            "spring_force_N": L(val(PR.B1["F_s_N"]), "N", "ASSUMPTION", "study B design ink force (frozen after G1)"),
            "face_force_normal_N": L(val(PR.B1["F_n_N"]), "N", "PROPOSED DESIGN", "the float's constant-force spring along the "
                                     "paper normal (study B: N = F_n at every tilt)"),
            "spring_force_range_N": L([0.8 * val(PR.B1["F_n_N"]), 1.2 * val(PR.B1["F_n_N"])], "N", "ASSUMPTION",
                                      "+-20 % (study B's Monte Carlo)"),
            "spring_gradient_N_per_m": L(0.0, "N/m", "PROPOSED DESIGN", "constant-force strip spring"),
            "friction_hysteresis_N": L(0.005, "N", "ASSUMPTION", "rolling guides (REQ-BNIB-016)"),
            "front_stop": L({"type": "counter-face float's front stop (follower stop)", "margin_m": hd["gap_mm"] * 1e-3,
                             "brake_engage_s": None, "detect": "face-position Hall"}, "-", "PROPOSED DESIGN",
                            "revk/counterface (float gap sized to the +-2.5 deg tilt wobble)"),
            "counter_face": L({"L_O_m": hd["L_O_mm"] * 1e-3, "x_h_m": hd["x_h_mm"] * 1e-3, "float_gap_m": hd["gap_mm"] * 1e-3,
                               "face_parallel_residual_mean_N": None, "reset_deadband_deg": val(PR.HEAD["deadband_deg"])},
                              "-", "PROPOSED DESIGN", "revk/counterface.design"),
            "hard_stop_extension_m": L(((fc["z_ring_mm"] - fc["protrusion_mm"]["75"]) + 1.5 + hd["gap_mm"] + 0.3) * 1e-3, "m",
                                       "CALC", "largest extension + float gap + 0.3 mm"),
            "pen_lift": L({"stroke_m": val(PR.HEAD["lift_mm"]) * 1e-3, "switch_s": hd["lift"]["worst_time_up_s"],
                           "command_to_contact_s": hd["lift"]["rows"][0]["ink_stops_after_s"], "holding_power_W": 0.0,
                           "energy_per_cycle_J": hd["lift"]["energy_per_lift_J"][1]}, "-", "CALC",
                          "revk/counterface.pen_lift (follower SQUIGGLE; speed-force line ASSUMPTION)"),
            "slide_sensor": L({"rate_hz": 1000.0, "noise_m": 2e-6, "delay_s": 0.001}, "-", "ASSUMPTION",
                              "face-position Hall (TMAG5273 class), as Rev J's slide sensor"),
        },
        "heel_wheel": {
            "fitted": False,
            "note": "base Rev K has no heel; the values are the heel-module variant's (study D's, at Rev K's radius)",
            "contact_point_m": L([-fc_h["R_d_mm"] * 1e-3, 0.0, fc_h["z_ring_mm"] * 1e-3], "m", "CALC",
                                 "revk/frontend.front_close(heel=True)"),
            "radius_m": L(0.001, "m", "ASSUMPTION", "study D"),
            "protrusion_beyond_ring_m": L(0.00035, "m", "ASSUMPTION", "study D"),
            "preload_N": L(0.55, "N", "ASSUMPTION", "study D"),
            "retracted_by_default": L(True, "-", "PROPOSED DESIGN", "DEC-048 (latch lifts the wheel 0.5 mm)"),
            "mu_range": L([0.6, 1.2], "-", "ASSUMPTION", "study D (EXP-D01)"),
            "shaft_length_m": L((lay["heel_variant"]["motor_z"][0] - lay["heel_variant"]["shafts"]["gearbox_z_mm"]) * 1e-3, "m",
                                "CALC", "revk/layout heel variant (outer shafts)"),
        },
        "endcap": {"optional": False, "fitted": False, "note": "no tail (DEC-051)"},
        "sensors": {
            "imu_position_m": L([v * 1e-3 for v in (c["imu"]["offset"][0], c["imu"]["offset"][1],
                                                   0.5 * (c["imu"]["z0"] + c["imu"]["z1"]))], "m", "CALC", "revk/layout"),
            "imu_model": L("LSM6DSV16X", "-", "MFR", "OPT-37"),
            "nose_position_noise_m": L([nibsum["hall"]["tip_noise_um_rms_1kHz"] * 1e-6] * 2, "m rms at the tip", "CALC",
                                       "revk/nib.hall_fields (TMAG5170 140 uT rms at 20 kSPS, MFR OPT-44; 1 kHz band)"),
            "nose_position_delay_s": L(1e-4, "s", "ASSUMPTION", "TMAG5170 conversion at 10 kSPS"),
            "page_sensor": L({"window_m": [w["r_mm"] * 1e-3, w["phi_deg"], (fc["z_ring_mm"] + w["s_mm"]) * 1e-3],
                              "window_note": "[radius m, azimuth deg from the bottom, z m]", "rate_hz": 1000.0,
                              "latency_s": 0.002, "noise_m": 1e-5, "lift_cutoff_m": [0.0002, 0.0002],
                              "lens_band_m": [2.2e-3, 2.6e-3]}, "-", "ASSUMPTION",
                             "PMW3610 class (MFR OPT-61 lens band +-0.2 mm); rate and noise as Rev J's assumption (EXP-J10)"),
        },
        "domain_randomisation_added": {
            "refill_face_force_N": [0.8 * val(PR.B1["F_n_N"]), 1.2 * val(PR.B1["F_n_N"])],
            "Km_scale": list(val(PR.B1["Km_scale_range"])),
            "x_pre_um": list(val(PR.NIB["x_pre_um"])),
            "face_parallel_error_deg": [0.0, 3.3],
            "pen_roll_deg": [-20.0, 20.0],
            "note": "ranges ASSUMPTION; face error up to the 95th percentile of revk/counterface.face_stack",
        },
        "adapter_for_sim2j": [
            "sim2j/revj.lead() reads results/revJ/*; point it at results/revK/ (layout.json, sim_params.json)",
            "geometry(): the layout's 'pivot_z' is the virtual 10 m pivot (layout.json carries it); comp['ec_shell'] does not "
            "exist (no end-cap): skip it when endcap is False",
            "_lead_part(): the refill holder is 'refill_holder' (the captive puck); there is no pen-lift drum",
            "nose(): use servo_hz and inner_hz from this file (both inside the 2.5 x rule; sim2j's loader fixes inner_hz at "
            "400 Hz) and add the ball guide's Coulomb friction (nib.coulomb_friction_N)",
            "the counter-face: the ink force acts along the paper normal at the puck (study B's sim2 model, bnib/sim.py)",
        ],
    }
    return {"sim_params": sp, "label": "CALCULATION from the Rev K layout and study B; labels on each value"}
