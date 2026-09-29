r"""Parameters a MuJoCo simulator (sim2, DEC-040) needs to model the integrated Rev J pen: the nose, the refill with its
spring, pen lift and front stop, the heel wheel, the skid ring, the end-cap, the sensors, and the handle's mass
properties with and without the end-cap.  Every value carries a label and a source; values are SI unless the key says
otherwise.  Frames: pen frame as results/revH/layout.json (z from the ball tip at 50 deg toward the back, x in the tilt
plane away from the paper, y lateral), metres in this file.
"""
from __future__ import annotations

import math
from typing import Dict

from . import params as PA


def _v(value, unit, label, source, note=""):
    d = {"value": value, "unit": unit, "label": label, "source": source}
    if note:
        d["note"] = note
    return d


def build(geo: Dict, bud: Dict, mag: Dict, fe: Dict, rf: Dict) -> Dict:
    nd = PA.nose_design()
    c = {x["id"]: x for x in geo["components"]}
    mm = 1e-3
    zp = nd["z_p"]
    ms = bud["mass"]
    nose = ms["nose"]
    hb, he = ms["handle_only_base"], ms["handle_only_with_endcap"]
    R_coil = PA.NOSE["V_bus"].value / PA.NOSE["I_peak_A"].value
    Kf = nd["Km_act"] * math.sqrt(R_coil)
    sp = rf["spring"]
    sl = rf["slide"]
    ap = mag["axial_pull"]
    nh = mag["nose_hall"]
    ec_slug = sum(x["mass_g"] for x in geo["components"] if x.get("moves_with") == "inertial_mass")
    ec_z = [0.5 * (x["z0"] + x["z1"]) for x in geo["components"] if x["id"] == "ec_slug"][0]
    k_ec = ec_slug * 1e-3 * (2 * math.pi * PA.ENDCAP["flexure_hz"].value) ** 2
    th = math.radians(50.0)
    ring_z = protrusion50 = geo["ball_protrusion_mm"]
    out = {
        "frames": {"pen": "z from the ball tip at 50 deg (nose centred) toward the back; x in the tilt plane away from the "
                          "paper; y lateral; metres", "gimbal_z": zp * mm},
        "handle": {
            "mass_base_kg": _v(hb["mass_g"] * 1e-3, "kg", "CALC", "revj/budgets.py (layout parts, +10 % wiring)",
                               "handle = every part except the moving nose (and the end-cap slug)"),
            "com_base_m": _v([v * mm for v in hb["com_mm"]], "m", "CALC", "revj/budgets.py"),
            "inertia_base_kg_m2": _v([[v * 1e-9 for v in row] for row in hb["inertia_g_mm2"]], "kg m^2", "CALC",
                                     "revj/budgets.py (about the handle's centre of mass)"),
            "mass_with_endcap_kg": _v(he["mass_g"] * 1e-3, "kg", "CALC", "revj/budgets.py (end-cap fitted, its slug excluded)"),
            "com_with_endcap_m": _v([v * mm for v in he["com_mm"]], "m", "CALC", "revj/budgets.py"),
            "inertia_with_endcap_kg_m2": _v([[v * 1e-9 for v in row] for row in he["inertia_g_mm2"]], "kg m^2", "CALC", "revj/budgets.py"),
            "finger_pads_z_m": _v([26 * mm, 32 * mm, 38 * mm], "m", "ASSUMPTION", "Rev H hand model (unchanged)"),
            "web_z_m": _v(92 * mm, "m", "ASSUMPTION", "Rev H hand model"),
        },
        "skid_ring": {
            "contact_radius_m": _v(fe["R_mm"] * mm, "m", "CALC", "revj/frontend.close (heel pod + C1S nose)"),
            "ring_plane_z_m": _v(ring_z * mm, "m", "CALC", "p(50 deg) = (R cos 50 - r_b) / sin 50"),
            "open_deg_top": _v(120.0, "deg", "ASSUMPTION", "DEC-034"),
            "tube_radius_m": _v(0.6 * mm, "m", "ASSUMPTION", "sim2 native C ring (31 capsules)"),
            "mu": _v(0.12, "-", "ASSUMPTION", "sim2 / HW1 skid friction (EXP-Q01)"),
        },
        "nose": {
            "joint": _v("two hinges (x, y) at the gimbal, axes perpendicular to the pen axis", "-", "PROPOSED DESIGN", "study N C1S"),
            "mass_kg": _v(nose["mass_g"] * 1e-3, "kg", "CALC", "revj/budgets.nose_about_pivot (layout parts, +10 %)"),
            "com_z_m": _v(nose["com_z_mm"] * mm, "m", "CALC", "revj/budgets.nose_about_pivot"),
            "inertia_about_pivot_kg_m2": _v(nose["I_pivot_g_mm2"] * 1e-9, "kg m^2", "CALC", "revj/budgets.nose_about_pivot",
                                            "study N's design model gives 2.10 g at the tip (its carrier ran from 4 mm); the "
                                            "layout gives %.2f g" % nose["m_eff_tip_g"]),
            "m_eff_tip_kg_layout": _v(nose["m_eff_tip_g"] * 1e-3, "kg", "CALC", "I / z_p^2 (layout)"),
            "m_eff_tip_kg_studyN": _v(nd["m_eff_tip_g"] * 1e-3, "kg", "CALC", "results/nose2/nose2.json (conservative; used for power)"),
            "flexure_k_Nm_per_rad": _v(nd["k_tip_N_m"] * (zp * mm) ** 2, "N m/rad", "CALC", "study N (0.478 N/m at the tip)"),
            "magnetic_negative_k_Nm_per_rad": _v([0.0, ap["negative_stiffness_Nm_per_rad_per_0.1mm"]], "N m/rad", "CALC",
                                                 "revj/magnetics.axial_pull: F x e, e 0-0.1 mm (sphere-centre offset, ASSUMPTION)",
                                                 "randomise over this range; the servo holds it"),
            "axial_magnetic_pull_N": _v(ap["F_axial_N_images"], "N", "CALC", "revj/magnetics.axial_pull (image method, upper bound)"),
            "damping_ratio": _v(0.02, "-", "ASSUMPTION", "sim2 nose structural damping"),
            "usable_angle_rad": _v(fe["alpha_u_rad"], "rad", "CALC", "revj/frontend.close (6.0 mm guaranteed over 35-75 deg)"),
            "stop_angle_rad": _v(fe["alpha_s_rad"], "rad", "CALC", "usable + 0.5 mm at the ball"),
            "actuator_z_m": _v(nd["z_a"] * mm, "m", "CALC", "study N (magnet face)"),
            "Km_act_N_per_sqrtW": _v(nd["Km_act"], "N/sqrt(W)", "CALC", "study N (image-method magnetics: upper bound; EXP-N01)"),
            "Km_tip_N_per_sqrtW": _v(nd["Km_tip"], "N/sqrt(W)", "CALC", "study N"),
            "coil_R_ohm": _v(R_coil, "ohm", "ASSUMPTION", "3.7 V / 1.5 A drive (study N V_BUS, I_PEAK)"),
            "K_f_N_per_A": _v(Kf, "N/A", "CALC", "Km sqrt(R) at the magnets"),
            "coil_L_H": _v(100e-6, "H", "ASSUMPTION", "sim2 value"),
            "coil_Rth_K_W": _v(PA.NOSE["coil_R_th_K_W"].value, "K/W", "ASSUMPTION", "study N; the fin model gives 94 K/W to the surface"),
            "coil_Cth_J_K": _v(0.5, "J/K", "ASSUMPTION", "sim2 value"),
            "I_max_A": _v(PA.NOSE["I_peak_A"].value, "A", "ASSUMPTION", "study N"),
            "V_bus_V": _v(PA.NOSE["V_bus"].value, "V", "ASSUMPTION", "study N"),
            "servo_hz": _v(PA.NOSE["servo_hz"].value, "Hz", "ASSUMPTION", "Rev H / study N"),
            "servo_zeta": _v(PA.NOSE["servo_zeta"].value, "-", "ASSUMPTION", "Rev H"),
            "slew_m_s": _v(PA.NOSE["slew_m_s"].value, "m/s", "ASSUMPTION", "Rev H"),
            "latency_s": _v(PA.NOSE["latency_s"].value, "s", "ASSUMPTION", "study N"),
            "first_parasitic_mode_hz": _v(nd["f_parasitic_Hz"], "Hz", "CALC", "study N (carrier bending)"),
        },
        "refill": {
            "joint": _v("slide along the nose axis", "-", "PROPOSED DESIGN", "architecture B"),
            "moving_mass_kg": _v(rf["moving_mass"]["total_g"] * 1e-3, "kg", "CALC",
                                 "refill 0.84 g + holder 0.5 g + drum rotor reflected 0.3 g + spring 0.1 g (ASSUMPTION masses)"),
            "slide_range_m": _v([v * mm for v in sl["slide_mm"]], "m", "CALC", "revj/frontend.close (relative to the 50 deg rest)"),
            "spring_force_N": _v(0.15, "N", "ASSUMPTION", "REQ-RVJ-N05 proposed"),
            "spring_force_range_N": _v(sp["force_range_N"], "N", "CALC", "spiral spring +-20 % over the tendon travel"),
            "spring_gradient_N_per_m": _v(-(sp["force_range_N"][1] - sp["force_range_N"][0]) / (sl["tendon_travel_mm"] * mm), "N/m",
                                          "CALC", "force falls as the refill extends (lowest at 35 deg)"),
            "friction_hysteresis_N": _v(0.01, "N", "ASSUMPTION", "tendon over two pulleys and the capstan (EXP-N06)"),
            "front_stop": _v({"type": "follows the nose (software brake)", "margin_m": 0.3 * mm, "brake_engage_s": 0.003,
                              "detect": "slide exceeds the contact position by the margin", "release": "pen-down detected"},
                             "-", "ASSUMPTION", "revj/refill.front_stop; sim2 s5.8 margin 0.3 mm"),
            "hard_stop_extension_m": _v((sl["slide_mm"][1] + 0.3) * mm, "m", "CALC", "largest geometric extension + 0.3 mm"),
            "pen_lift": _v({"stroke_m": PA.NOSE["pen_lift_stroke_mm"].value * mm, "switch_s": 0.005,
                            "command_to_contact_s": PA.NOSE["pen_lift_delay_s"].value, "holding_power_W": 0.0,
                            "energy_per_cycle_J": 0.017}, "-", "CALC/ASSUMPTION", "study N axial_dof"),
            "slide_sensor": _v({"rate_hz": 1000.0, "noise_m": 2e-6, "delay_s": 0.001}, "-", "ASSUMPTION", "sim2 refill-slide Hall"),
        },
        "heel_wheel": {
            "contact_point_m": _v([-fe["R_d_mm"] * mm, 0.0, ring_z * mm], "m", "CALC", "revj/frontend.close (ring plane, bottom)"),
            "radius_m": _v(PA.HEEL["r_e_mm"].value * mm, "m", "ASSUMPTION", "study D"),
            "steer_axis": _v([math.cos(th), 0.0, math.sin(th)], "-", "ASSUMPTION", "paper normal at 50 deg through the contact (study D)"),
            "protrusion_beyond_ring_m": _v(PA.HEEL["delta_mm"].value * mm, "m", "ASSUMPTION", "study D"),
            "preload_N": _v(PA.HEEL["preload_N"].value, "N", "ASSUMPTION", "study D"),
            "spring_travel_m": _v(fe["spring_travel_mm"] * mm, "m", "CALC", "revj/frontend.check (tilt and +-20 deg roll)"),
            "spring_rate_N_per_m": _v(200.0, "N/m", "ASSUMPTION", "a soft preloaded leaf (+-10 % load over the travel)"),
            "mu_range": _v(list(PA.HEEL["mu_range"].value), "-", "ASSUMPTION", "study D (EXP-D01)"),
            "k_lat_N_per_m": _v(PA.HEEL["k_lat_N_m"].value, "N/m", "CALC", "study D"),
            "rolling_coef": _v(PA.HEEL["rolling_coef"].value, "-", "CALC", "study D (Persson, LIT AMF-112)"),
            "reflected_mass_kg": _v(PA.HEEL["reflected_mass_g"].value * 1e-3, "kg", "CALC", "study D"),
            "backdrive_N": _v(PA.HEEL["backdrive_N"].value, "N", "CALC", "study D"),
            "F_cap_N": _v(PA.HEEL["F_cap_N"].value, "N", "ASSUMPTION", "study D supervisor (and 0.8 mu_hat N)"),
            "F_cont_N": _v(PA.HEEL["F_cont_N"].value * PA.HEEL["mesh_eff"].value, "N", "CALC",
                           "study D 0.41 N x 0.9 for the Rev J idler mesh (motors under the cell)"),
            "F_peak_N": _v(PA.HEEL["F_peak_N"].value * PA.HEEL["mesh_eff"].value, "N", "CALC",
                           "study D 0.67 N x 0.9 for the Rev J idler mesh"),
            "steer_servo": _v({"bandwidth_hz": PA.HEEL["steer_bw_hz"].value, "rate_rad_s": PA.HEEL["steer_rate_rad_s"].value},
                              "-", "ASSUMPTION", "study D"),
            "motor": _v({k: v.value for k, v in PA.MOTOR.items() if k != "rotor_magnet"}, "-", "MFR", "AMF-100"),
            "drive_ratio": _v(2.0, "-", "ASSUMPTION", "study D (spur 1:1 via idler, 40 deg bevel 1:1, axle bevel 2:1)"),
            "drive_efficiency": _v(0.9 ** 4, "-", "ASSUMPTION", "0.9 per mesh; Rev J adds the idler mesh (study D: 3 meshes)"),
            "steer_ratio": _v(2.0, "-", "ASSUMPTION", "study D (crown 2:1)"),
            "shaft_length_m": _v((c["drive_transfer"]["z0"] - c["drive_shaft_drive"]["z0"]) * mm, "m", "CALC", "layout"),
            "shaft_torsion_Nm_per_rad": _v(80e9 * math.pi * (0.8e-3) ** 4 / 32 / ((c["drive_transfer"]["z0"] - c["drive_shaft_drive"]["z0"]) * mm),
                                           "N m/rad", "CALC", "G 80 GPa steel (ASSUMPTION), d 0.8 mm"),
            "magnetic_detent_torque_bound_Nm": _v(mag["c1s_at_motors"]["positions"]["stop_toward"]["torque_bound_mNm"] * 1e-3, "N m",
                                                  "CALC", "revj/magnetics (free-space upper bound; randomise 0 .. this)"),
        },
        "endcap": {
            "optional": True,
            "slug_mass_kg": _v(ec_slug * 1e-3, "kg", "CALC", "study K (28.7 g tungsten + 4 tiles)"),
            "slug_centre_z_m": _v(ec_z * mm, "m", "CALC", "revj layout (study K's end-cap moved to the Rev J cell end)"),
            "stroke_m": _v(PA.ENDCAP["stroke_mm"].value * mm, "m", "CALC", "study K"),
            "flexure_k_N_per_m": _v(k_ec, "N/m", "CALC", "m (2 pi 5 Hz)^2 per axis"),
            "damping_ratio": _v(0.05, "-", "ASSUMPTION", "spiral flexures in air"),
            "Km_N_per_sqrtW": _v(PA.ENDCAP["Km_N_sqrtW"].value, "N/sqrt(W)", "CALC", "study K"),
            "P_peak_W": _v(PA.ENDCAP["P_peak_W"].value, "W", "CALC", "study K"),
            "feedforward_gain": _v(PA.ENDCAP["gain"].value, "-", "SIM", "study K rule (tuning seeds)"),
        },
        "sensors": {
            "imu_position_m": _v([c["imu"]["offset"][0] * mm, 0.0, 0.5 * (c["imu"]["z0"] + c["imu"]["z1"]) * mm], "m", "CALC",
                                 "layout (on the main board; Rev H r_imu 92-93.5 mm)"),
            "imu_model": _v("LSM6DSV16X", "-", "MFR", "OPT-37 (sim2 sensor model unchanged)"),
            "nose_position_noise_m": _v([nh["tip_noise_um_rms"]["DRV5055_A4_pair"]["x"] * 1e-6,
                                         nh["tip_noise_um_rms"]["DRV5055_A4_pair"]["y"] * 1e-6], "m rms at the tip", "CALC",
                                        "revj/magnetics.nose_hall (two DRV5055-A4 on the board; OPT-46)"),
            "nose_position_delay_s": _v(50e-6, "s", "ASSUMPTION", "sim2"),
            "page_sensor": _v({"window_m": [c["page_sensor"]["window"]["r_mm"] * mm, c["page_sensor"]["window"]["phi_deg"],
                                            c["page_sensor"]["window"]["z_mm"] * mm],
                               "window_note": "[radius m, azimuth deg from the bottom, z m]",
                               "rate_hz": 1000.0, "latency_s": 0.002, "noise_m": 3e-6,
                               "valid_height_m": [2.2e-3, 2.6e-3], "lift_cutoff_m": [2e-3, 3e-3]},
                              "-", "ASSUMPTION / MFR", "study N (1 kHz, 2 ms, 3 um); OPT-54 (lens plane 2.2-2.6 mm, lift cut-off 2-3 mm)"),
        },
        "domain_randomisation_added": {
            "tyre_mu": [0.6, 1.2], "wheel_preload_N": [0.5, 0.6], "refill_spring_N": [0.12, 0.18],
            "nose_negative_k_Nm_per_rad": [0.0, ap["negative_stiffness_Nm_per_rad_per_0.1mm"]],
            "Km_scale": [0.7, 1.0], "motor_detent_Nm": [0.0, mag["c1s_at_motors"]["positions"]["stop_toward"]["torque_bound_mNm"] * 1e-3],
            "pen_roll_deg": [-20.0, 20.0], "note": "ranges ASSUMPTION; Km_scale 0.7-1.0 because the image-method magnetics is an upper bound"},
    }
    return out
