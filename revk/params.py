"""Every input of the Rev K integration with its label and source.

Every value: V(value, unit, label, source) (the record of revj/params.py).  Labels: MANUFACTURER (datasheet or
distributor page with the part number; ledger id in docs/evidence.csv, or AMF-250.. proposed in
results/revK/evidence_rows.csv for pages opened in this study), LITERATURE (ledger id), CALCULATION (a study's code,
named), SIMULATION (an executed run, file named), ASSUMPTION (unmeasured: the test that pins it is named), PROPOSED
DESIGN (a dimension or choice made here).  Values that come from another study's result file are loaded from that file
(read-only) so that Rev K follows study B if it is re-run.

Frames (as results/revJ/layout.json): z along the pen axis from the ball tip (z = 0 at 50 deg, nib centred) toward the
back; x in the tilt plane, positive AWAY from the paper (the paper side is -x); y lateral.  Units mm, g, N, W unless the
key says otherwise.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Dict

from . import REPO_ROOT, ensure_paths

ensure_paths()
from revj.params import V  # noqa: E402  (the same labelled record as Rev J and Rev J.1)

MFR, LIT, CALC, SIM, ASM, PD = "MANUFACTURER", "LITERATURE", "CALCULATION", "SIMULATION", "ASSUMPTION", "PROPOSED DESIGN"


def val(x):
    return x.value if isinstance(x, V) else x


def table(d: Dict) -> Dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, V):
            out[k] = v.d()
        elif isinstance(v, dict):
            out[k] = table(v)
        else:
            out[k] = v
    return out


def _load(rel: str) -> Dict:
    with open(REPO_ROOT / rel) as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------ study B's nib (read)
@lru_cache(maxsize=1)
def b1() -> Dict:
    """Study B's recommended nib B1 (results/bnib/bnib.json -> recommended, and the layout parts), read-only."""
    d = _load("results/bnib/bnib.json")["recommended"]
    lay = _load("results/bnib/layout_parts.json")
    comps = {c["id"]: c for c in lay["components"]}
    return {"rec": d, "x": d["x"], "comps": comps, "fit_checks": lay["meta"]["fit_checks"],
            "mass_added_g": lay["meta"]["mass_added_g"]}


def b1_design():
    """The B1 design object (bnib.optimise.build on the recorded design point), for bnib's own models."""
    from bnib import optimise as OP
    return OP.build("c_counterface", "pen24", dict(b1()["x"]))


B1 = {
    "travel_mm": V(1.0587, "mm", CALC, "study B optimiser point (results/bnib/bnib.json recommended.x.travel)"),
    "stop_mm": V(1.2587, "mm", PD, "study B: soft stops at the usable travel + 0.2 mm (config/nib.yaml travel.stop)"),
    "travel_G4_mm": V(1.0, "mm", PD, "DEC-050 / DEC-060: the two-axis nib (gate G4) at +-1.0 mm"),
    "Km_tip": V(0.40007, "N/sqrt(W)", CALC, "study B surrogate calibrated to magpylib, image method = UPPER bound (config/nib.yaml)"),
    "Km_scale_range": V((0.7, 1.0), "x", ASM, "DEC-041 / study B: image-method magnetics is an upper bound; EXP-B23 (EXP-T07) measures"),
    "k_tip_N_m": V(3.7927, "N/m", CALC, "study B, four Ti-6Al-4V wires fixed-guided (bnib/flexure.py)"),
    "m_eff_tip_g": V(3.49, "g", CALC, "study B (config/nib.yaml moving_parts.m_eff_tip)"),
    "modes_free_Hz": V((5.5, 362.3, 2444.6), "Hz", CALC, "study B loaded eigenmodes, ball free (results/bnib/bnib.json)"),
    "modes_stuck_Hz": V((109.1, 567.6, 2509.2), "Hz", CALC, "study B loaded eigenmodes, ball stuck (results/bnib/bnib.json)"),
    "servo_inner_Hz": V(100.0, "Hz", SIM, "study B frozen rule servo_fi (results/bnib/rules.json), tuned on writers 100-101"),
    "wire_circle_r_mm": V(5.5, "mm", PD, "study B layout (bnib/layout.py r_w)"),
    "F_s_N": V(0.15, "N", ASM, "study B design ink force along the pen; frozen only after gate G1 (EXP-B20 / EXP-T02)"),
    "F_n_N": V(0.1958, "N", PD, "study B: face force along the paper normal, N = F_n at every tilt (config/nib.yaml)"),
    "face_gap_mm": V(0.25, "mm", SIM, "study B frozen rule face_gap (results/bnib/rules.json)"),
    "rolling_mu": V(0.005, "-", ASM, "study B: rolling ball on a hardened face (EXP-B22)"),
    "P_cont_mW": V(7.56, "mW", CALC, "study B duty A, mean over 35-75 deg (results/bnib/bnib.json)"),
    "P_sim_correcting_mW": V(14.8, "mW", SIM, "study B sim2, 4 synthetic writers, the frozen tracker (docs/balanced_nib.md s5.3)"),
    "P_sim_clean_mW": V(11.8, "mW", SIM, "study B sim2, tremor-free writing"),
    "mass_studyB_g": V(68.76, "g", CALC, "study B's Rev K estimate (results/bnib/bnib.json recommended.mass_g)"),
    "com_studyB_mm": V(74.24, "mm", CALC, "study B (results/bnib/bnib.json recommended.eval.com_mm)"),
    "length_studyB_mm": V(148.0, "mm", CALC, "study B (144 mm base + 4 mm for the face)"),
    "battery_h_studyB": V(38.35, "h", CALC, "study B (electronics 47 mW mid + nib 7.6 / 0.85 + 2 mW positioners)"),
    "battery_h_sim": V(33.5, "h", SIM, "study B sim2 runs"),
    "T_skin_studyB_C": V(30.59, "degC", CALC, "study B two-node model, 30 degC room, 35 deg"),
}

# ------------------------------------------------------------------------------------------------ envelope and hand
ENVELOPE = {
    "handle_od_held_mm": V(24.0, "mm", ASM, "DEC-029 / docs/revJ_plan.md s6 (Rev J envelope: <= 24 mm where held)"),
    "length_mm": V(175.0, "mm", ASM, "docs/revJ_plan.md s6"),
    "mass_g": V(120.0, "g", ASM, "docs/revJ_plan.md s6 (with every module)"),
    "grip_zone_mm": V((20.0, 45.0), "mm", ASM, "Rev H hand model (results/revH/layout.json grip_zone)"),
    "finger_pads_z_mm": V((26.0, 32.0, 38.0), "mm", ASM, "Rev H hand model hand.finger_pads_z"),
    "finger_pad_half_mm": V(2.5, "mm", ASM, "Rev J drawing (pads drawn 5 mm long)"),
    "web_z_mm": V(92.0, "mm", ASM, "Rev H hand model hand.web_z"),
    "grip_full_od_from_z_mm": V(20.0, "mm", PD, "the sleeve reaches the held 24 mm at the front of the grip zone"),
    "ordinary_pen": V({"od_mm": 9.0, "pad_z_mm": 25.0}, "-", ASM, "a reference ballpoint (9 mm body held 25 mm from the tip)"),
}

# ------------------------------------------------------------------------------------------------ front end (translation nib)
FRONT = {
    "r_ball_mm": V(0.35, "mm", LIT, "CON-22 (0.7 mm ball)"),
    "refill_r_mm": V(1.175, "mm", LIT, "CON-22 (D1 refill 2.35 mm)"),
    "carrier_r_mm": V(1.6, "mm", PD, "study B carrier Ti tube 3.2/2.5 mm (bnib/actuators.py R_CARRIER)"),
    "carrier_front_z_mm": V(9.0, "mm", PD, "study B layout (bnib_carrier z0 = 9.0)"),
    "guide_station": V({"r_mm": 2.0, "len_mm": 2.0}, "mm", PD, "rolling guide station at each carrier end (three rollers in "
                       "windows, friction <= 0.01, REQ-BNIB-016): drawn as a 4 mm collar 2 mm long"),
    "ring_len_mm": V(1.5, "mm", ASM, "DEC-034 ring length"),
    "ring_wall_min_mm": V(1.0, "mm", ASM, "DEC-034 ring lip"),
    "c_run_mm": V(0.3, "mm", ASM, "running clearance (Rev J rule)"),
    "c_fixed_mm": V(0.2, "mm", ASM, "gap between fixed parts (Rev J rule)"),
    "c_paper_mm": V(0.3, "mm", ASM, "DEC-034: parts behind the ring stay 0.3 mm above the paper at 35-75 deg"),
    "R_step_mm": V(0.25, "mm", ASM, "DEC-034 sizing step"),
    "sleeve_wall_mm": V(1.0, "mm", ASM, "Rev H / J sleeve and shell wall"),
    "optics_block": V({"normal_mm": 1.5, "half_width_mm": 1.0}, "mm", ASM, "Rev J folded optics: lens + 45 deg mirror block "
                      "2 x 2 x 2 mm, 1.5 mm along the paper normal (revj/frontend.page_sensor_window)"),
    "lens_band_mm": V((2.2, 2.4, 2.6), "mm", MFR, "OPT-61 (PMW3610: lens reference plane 2.2-2.6 mm, +-0.2 mm DOF)"),
    "lift_cutoff_needed_mm": V(2.0, "mm", SIM, "REQ-BNIB-017 (study B SIM: the page kept through the lifts between strokes)"),
    "roll_design_deg": V(20.0, "deg", ASM, "REQ-RVJ-N06 / REQ-DRV-007: pen roll +-20 deg while writing"),
    "tilt_range_deg": V((35.0, 75.0), "deg", LIT, "CON-02; REQ-RVH-002"),
    "tilt_wobble_deg": V(2.5, "deg", LIT, "CON-02 (pen angle varies about 2.5 deg while writing; kinematic spectra peak 2-5 Hz)"),
    "open_deg": V(120.0, "deg", ASM, "DEC-034: the ring open 120 deg on top"),
}

# ------------------------------------------------------------------------------------------------ the nib in the pen
NIB = {
    "wire_material": V("C17200", "-", PD, "Rev K: the four suspension wires carry the two coils' currents (optical-pickup "
                       "practice); Ti-6Al-4V (study B) cannot: 170 uOhm cm (AMF-21 re-read)"),
    "rho_Ti64_ohm_m": V(1.70e-6, "ohm m", MFR, "AMF-21 re-read: AZoM / US Titanium Industry, volume electrical resistivity "
                        "'170 (67)' printed as ohm.cm (read as micro-ohm cm)"),
    "IACS_C17200_min": V(0.22, "-", MFR, "AMF-251 (IBC Advanced Alloys C17200 data sheet: AT(TF00) 22 % IACS min)"),
    "E_C17200_GPa": V(127.6, "GPa", MFR, "AMF-19 (CDA C17200: 18,500 ksi)"),
    "Sf_C17200_MPa": V(310.0, "MPa", MFR, "AMF-19 (TH04 flat products, 1e8 cycles)"),
    "coil_R_ohm": V(2.5, "ohm", PD, "study B: wound for 3.7 V / 1.5 A"),
    "coil_I_rms_duty_A": V(0.06, "A", CALC, "from study B's 35 deg card (I_hold 0.06 A) and 7.6-17.6 mW at 2.5 ohm"),
    "housing_bore_coil_mm": V(11.0, "mm", PD, "Rev K: no aluminium ring in the coil plane; the coils run inside the 22 mm "
                              "PEEK bore (study B drew a 21.6 mm aluminium ring over the whole actuator)"),
    "coil_former_margin_mm": V(0.1, "mm", ASM, "polyimide former edge around the carrier"),
    "x_pre_um": V((5.0, 10.0, 20.0), "um", ASM, "pre-sliding displacement of the stuck ball (sim2 H1 LuGre 10 um; EXP-B21 / "
                  "EXP-T01 measure the friction map, EXP-T10 the loaded modes)"),
    "refill_EI_Nm2": V((0.09, 0.385), "N m^2", ASM, "brass D1 tube (E 100 GPa, 2.35/1.9 mm) .. study B's 0.385 (Ti sleeve)"),
    "servo_bw_rule_x": V(2.5, "x", PD, "DEC-050 (lead, 2026-09-30): lowest mode >= 2.5 x the servo bandwidth, ball free and stuck"),
    "servo_bw_min_Hz": V(40.0, "Hz", PD, "REQ-BNIB-006: closed-loop bandwidth >= 40 Hz"),
    "wire_circle_options_mm": V((5.5, 7.0, 8.0), "mm", PD, "study B's 5.5 mm and two larger circles (tilt stiffness ~ r^2)"),
    "drop_height_m": V(1.0, "m", PD, "REQ-BNIB-012: 1 m onto a hard floor"),
    "lateral_stop_k_N_m": V((2e4, 1e5, 5e5, 1e6, 2e6), "N/m", ASM, "TPE ring .. PEEK .. metal lateral stops (EXP-B25)"),
    "hall_part": V("TMAG5170-A1", "-", MFR, "OPT-44 / OPT-53 (+-25/50/100 mT; 140 uT rms XY; 3.4 mA; 10 kSPS 3 axes)"),
    "hall_range_mT": V(100.0, "mT", MFR, "OPT-44 (A1 largest range)"),
    "hall_magnet": V({"size_mm": 1.0, "Br_T": 1.42}, "-", MFR, "AMF-139 (N52 1 mm cube, study B)"),
}

# ------------------------------------------------------------------------------------------------ counter-face head
HEAD = {
    "positioner": V("New Scale SQL-RV-1.8", "-", MFR, "AMF-15 / AMF-106 (2.8 x 2.8 x 6 mm, 0.16 g, 6 mm travel, stall 0.30-0.33 N "
                    "at 3.3 V, > 7 mm/s at 15 gf, < 340 mW moving, 0 mW hold; volume-only supply)"),
    "pos_travel_mm": V(6.0, "mm", MFR, "AMF-15"),
    "pos_stall_N": V(0.30, "N", MFR, "AMF-15 (0.3 N at 3.3 V; AMF-106 0.33 N)"),
    "pos_speed_15gf_mm_s": V(7.0, "mm/s", MFR, "AMF-106 (> 7 mm/s at 15 gf)"),
    "pos_power_W": V((0.34, 1.0), "W", MFR, "AMF-15: < 340 mW at 2.8 V, 7 mm/s, 15 g (Rev G); about 1 W at 3.3 V, 5 mm/s, 10 g (Rev H)"),
    "pos_mass_g": V(0.16, "g", MFR, "AMF-106"),
    "pos_life_cycles": V(1.0e6, "cycles", MFR, "AMF-15 (> 1 M cycles at 15 g, 7 mm/s)"),
    "n_positioners": V(3, "-", PD, "tilt, roll (crank, +-30 deg), axial follower"),
    "roll_range_deg": V(30.0, "deg", PD, "+-30 deg: REQ-RVJ-N06's +-20 deg of pen roll + 10 deg; the page sensor already fixes "
                        "the pen's 'down' side (roll tolerance 21 deg), so the head need not follow a full turn"),
    "roll_crank_mm": V(5.5, "mm", PD, "roll crank radius (6 mm of screw travel turns the cage 62 deg)"),
    "float_margin_mm": V(0.10, "mm", PD, "clearance kept to the float window's ends beyond the tilt wobble"),
    "refill_length_spread_mm": V(0.3, "mm", ASM, "spread of D1 refill lengths between brands (not read from ISO 12757-1 "
                                 "here); EXP-B22 measures three brands"),
    "follower_spare_mm": V(1.5, "mm", PD, "follower travel kept spare for assembly, wear and a deeper lift if EXP-S12 asks"),
    "head_bore_r_mm": V(11.0, "mm", PD, "the head runs in the 22 mm PEEK bore (24 mm shell, 1 mm wall)"),
    "lift_mm": V(0.5, "mm", PD, "DEC-050: the pen lift raises the ball about 0.5 mm (REQ-RVJ-N04: >= 0.3 mm)"),
    "puck": V({"shoe_d_mm": 4.0, "r_pb_mm": 1.0, "h_mm": 3.0, "joint_ball_d_mm": 1.2, "stem_mm": 2.0, "grip_N": (0.1, 0.2),
               "rim_clear_mm": 0.1, "mass_g": 0.08},
              "-", PD, "captive shoe and refill holder: a PEEK cup grips the refill's plain rear end; a stem carries a "
                       "1.2 mm ball snapped into an asymmetric slotted socket in a 4 mm shoe; the shoe rides on three 0.5 mm "
                       "Si3N4 balls on the sapphire, parallel to the face, under the tray's rim (0.1 mm: no force while "
                       "writing); the joint centre 1.0 mm above the face, 3.0 mm behind the refill's end"),
    "face_facing": V("sapphire 0.3 mm on a Ti-6Al-4V bracket", "-", PD, "hard, non-magnetic (AMF-160 Kyocera sapphire, AMF-21)"),
    "tilt_crank_mm": V(6.0, "mm", PD, "tilt crank radius on the hinge (the tilt SQUIGGLE runs along the pen on the roll ring)"),
    "hinge_friction_Nmm": V(0.02, "N mm", ASM, "jewel-pivot tilt hinge (EXP-B22 measures)"),
    "roll_bearing_friction_Nmm": V(0.03, "N mm", ASM, "thin roll ring on three jewel rollers (EXP-B22)"),
    "deadband_deg": V(1.5, "deg", PD, "the face is re-set only when the estimated mean tilt or roll drifts beyond this"),
    "resets_per_min": V((2.0, 6.0), "1/min", ASM, "posture changes while writing (EXP-B28 measures the tilt and roll traces)"),
    "face_sensor": V("TMAG5273-class 3-D Hall + 1 mm magnet on the float", "-", MFR, "OPT-45 (2.3 mA active; 20 kSPS)"),
    "face_sensor_W": V((0.004, 0.008), "W", ASM, "Rev J's refill-slide Hall duty-cycled at 1 kHz (revj/params POWER)"),
    "driver_ic": V("NSD-2101 x 3", "-", MFR, "AMF-15 (SQUIGGLE driver ASIC, 1.8 x 1.8 mm)"),
    "driver_sleep_W": V(0.0002, "W", ASM, "three drivers asleep between moves (not in the datasheets opened)"),
}

# ------------------------------------------------------------------------------------------------ the face-parallelism stack
FACE_STACK = {  # 1 sigma unless 'uniform' (ASSUMPTION each; EXP-B22 / EXP-B28 pin them)
    "imu_tilt_deg": V(1.0, "deg", ASM, "REQ-BNIB-015 / study B (IMU tilt while writing, 1 sigma); EXP-B28"),
    "imu_roll_deg": V(2.0, "deg", ASM, "REQ-BNIB-015 / study B (roll from gravity, 1 sigma); EXP-B28"),
    "imu_to_axis_residual_deg": V(0.2, "deg", ASM, "IMU mounting after a factory turntable calibration (0.5 deg before it)"),
    "roll_ring_axis_deg": V(0.3, "deg", ASM, "roll-ring bearing play"),
    "hinge_axis_deg": V(0.2, "deg", ASM, "tilt-hinge perpendicularity"),
    "face_perp_deg": V(0.1, "deg", ASM, "face flatness and perpendicularity to its float axis"),
    "linkage_backlash_deg": V(0.2, "deg", ASM, "tilt and roll linkages (uniform +-)"),
    "deadband_deg": V(1.5, "deg", PD, "uniform +- (HEAD deadband)"),
    "wobble_deg": V(2.5, "deg", LIT, "CON-02 amplitude, not followed by the face (a dynamic error)"),
    "slope_deg": V((0.0, 10.0), "deg", ASM, "desk slope (a use condition, study B: 17 / 34 mN at 5 / 10 deg; app setting)"),
}

# ------------------------------------------------------------------------------------------------ electronics (datasheets)
ELEC = {
    "nib_hall_mA": V(3.4, "mA", MFR, "OPT-44 / OPT-53 (TMAG5170 IACT 3.4 mA)"),
    "nib_hall_duty": V((0.2, 1.0), "-", ASM, "2 kSPS (enough for a <= 44 Hz servo, REQ-BNIB-006) .. continuous 10 kSPS"),
    "hall_supply_V": V(3.7, "V", ASM, "LDO from the cell (Rev J.1 convention for the Hall sensors)"),
    "lra_tick_mJ": V((1.5, 3.5), "mJ", ASM, "an 8 mm coin LRA at about 70 mW for 20-50 ms per tick (AMF-45 class)"),
    "idle_sleep_W": V((1.0e-4, 3.0e-4), "W", ASM, "on the desk: SoC idle 3.1 uA (OPT-60) + IMU wake-up + page sensor Rest3 7 uA "
                      "(OPT-61) + BLE advertising + fuel gauge"),
    "awake_hover_note": V("sensors on, nib servo idle, no writing", "-", PD, "the pen held but not writing"),
}

# ------------------------------------------------------------------------------------------------ modes (REQ-RVJ-I01)
MODES = {
    "tremor_rms_mm": V({"steady_0mm": 0.0, "steady_1mm": 1.0, "steady_2mm": 2.0}, "mm rms", ASM, "REQ-RVJ-I01 rows (tremor at the tip)"),
    "clip_rms_mm": V(0.75, "mm rms", CALC, "a +-1.06 mm nib passes about 0.75 mm rms of a sinusoid it clips (1.06 / sqrt 2)"),
    "spelling_lifts_per_100_words": V((0.3, 2.3), "1/100 words", SIM, "study S (pen lift alone 0.3 false / 100; tick + lift 2.3 "
                                      "false cues / 100 correct words; docs/spelling_and_clarity.md)"),
    "spelling_ticks_per_100_words": V((2.3, 7.7), "1/100 words", SIM, "study S (tick at the pause .. mid-word cues)"),
    "words_per_min": V(15.0, "1/min", ASM, "adult phrase writing (CON-20 30.5 mm/s at about 2 mm per letter-space)"),
    "guide_q_rms_mm": V(0.3, "mm rms", ASM, "guidance nudges within the nib's reach (Rev J.1 used the 0.3 mm duty as a proxy)"),
    "lead_heel_W": V(0.084 / 0.9, "W", SIM, "study D SIM 84 mW leading / 0.9 for the idler mesh (Rev J.1 row)"),
    "heel_drivers_W": V((0.010, 0.020), "W", ASM, "study D motor drivers and pod sensors"),
    "heel_steer_W": V((0.001, 0.006), "W", SIM, "study D steer-only .. steered + driven guidance"),
    "targets_h": V({"steady": 8.0, "guide": 8.0, "lead": 7.5}, "h", PD, "REQ-RVJ-I01 (as revised by DEC-045)"),
}

# ------------------------------------------------------------------------------------------------ thermal
THERMAL = {
    "room_C": V(30.0, "degC", PD, "rated maximum room (REQ-THM-001; ECMA-287 B.5, AMF-35)"),
    "skin_limit_C": V(43.0, "degC", LIT, "AMF-35 (ECMA-287 Table 5.2, continuously held)"),
    "skin_target_C": V(41.0, "degC", LIT, "AMF-34 (IEC 60601-1)"),
    "h_W_m2K": V(10.0, "W/m^2K", ASM, "natural convection + radiation (Rev J)"),
    "k_shell_W_mK": V(0.30, "W/mK", MFR, "AMF-24 (PEEK 0.29-0.32)"),
    "R_int_coil_K_W": V(15.0, "K/W", ASM, "coil to shell through the bonded stator (Rev J R_int)"),
}

# ------------------------------------------------------------------------------------------------ cost (100 / 1,000 units)
# unit prices in USD; catalogue parts from distributor pages opened 2026-09-30 (MANUFACTURER, ids proposed in
# results/revK/evidence_rows.csv); everything else ASSUMPTION ranges (quotes needed: the test is a request for quotation).
COST = [
    # item, qty per pen, (low, high) at 100, (low, high) at 1000, label, source
    ("nRF54L15-QFAA (SoC)", 1, (3.49, 3.49), (3.06, 3.06), MFR, "AMF-252 (DigiKey NRF54L15-QFAA-R, 2026-09-30: 3.49 @100, 3.06 @1000)"),
    ("DRV8214 coil drivers", 2, (2.59, 2.59), (2.24, 2.45), MFR, "AMF-253 (DigiKey DRV8214RTER: 2.59 @100, 2.45 @500, 2.24 reel)"),
    ("TMAG5170-A1 nib Hall", 1, (1.97, 1.97), (1.74, 1.74), MFR, "AMF-250 (DigiKey TMAG5170A1QDGKR: 1.97 @100, 1.74 @1000)"),
    ("LSM6DSV16X IMU", 1, (4.34, 4.34), (3.89, 3.89), MFR, "AMF-254 (DigiKey LSM6DSV16XTR: 4.34 @100, 3.89 @1000)"),
    ("page sensor die + custom lens and mirror", 1, (15.0, 40.0), (6.0, 15.0), ASM, "PMW3610-class die (no distributor price found) + custom optics"),
    ("LIR14500 cell", 1, (3.0, 6.0), (2.0, 4.0), ASM, "catalogue Li-ion 14500 (no price opened)"),
    ("charger, fuel gauge, regulators, passives", 1, (4.0, 8.0), (2.0, 4.0), ASM, "catalogue ICs"),
    ("main board (4-layer rigid-flex) and assembly", 1, (35.0, 70.0), (10.0, 20.0), ASM, "prototype vs small-batch PCBA"),
    ("face-position Hall (TMAG5273 class)", 1, (1.5, 2.5), (1.2, 2.0), ASM, "catalogue (OPT-45 class)"),
    ("SQUIGGLE SQL-RV-1.8 + NSD-2101 driver", 3, (80.0, 200.0), (25.0, 60.0), ASM, "volume-only supply (AMF-15): no public price; micro-stepper fallback"),
    ("N52 pole magnets 5.12 x 5.12 x 3.5 mm (custom size)", 4, (2.0, 5.0), (0.4, 1.0), ASM, "custom cut N52"),
    ("moving coils (two flat layers, flex or bonded wire)", 1, (40.0, 120.0), (8.0, 20.0), ASM, "custom (NRE excluded)"),
    ("1010 back plate and keeper (laser cut)", 2, (3.0, 8.0), (0.5, 1.5), ASM, "custom"),
    ("Ti-6Al-4V carrier with two rolling guide stations", 1, (60.0, 150.0), (15.0, 35.0), ASM, "micro-machined + jewel rollers"),
    ("C17200 suspension wires, clamps and PCB flange / anchor", 1, (20.0, 50.0), (5.0, 12.0), ASM, "hand soldering / laser welding"),
    ("ball thrust guide: 12 Si3N4 balls, two 440C races, wave springs, hard stops; lateral stop bush", 1, (30.0, 80.0),
     (6.0, 15.0), ASM, "catalogue grade-5 balls; lapped custom races"),
    ("counter-face head (roll ring, hinge, sapphire face, float, puck)", 1, (120.0, 300.0), (30.0, 70.0), ASM, "custom micro-mechanism"),
    ("PEEK shell, front sleeve (TPE), skid ring, rear cap", 1, (60.0, 140.0), (8.0, 18.0), ASM, "machined at 100, moulded at 1000 (tooling excluded)"),
    ("cue LRA 8 mm", 1, (2.0, 4.0), (1.0, 2.0), ASM, "AMF-45 class"),
    ("charging contacts (gold pads) and cradle share", 1, (3.0, 8.0), (1.0, 3.0), ASM, "custom"),
    ("assembly, calibration and test (hours x rate)", 1, (150.0, 300.0), (40.0, 80.0), ASM, "3-6 h at 50 USD/h (100) .. 1-1.5 h (1000)"),
]
NRE = V({"moulds_and_fixtures_usd": (25000.0, 60000.0), "coil_tooling_usd": (3000.0, 10000.0)}, "USD", ASM,
        "tooling for the 1,000-unit column (moulds for the shell, sleeve and ring; coil winding / flex tooling); not in the unit cost")
HEEL_COST = [
    ("Faulhaber 0620 B motors (heel module)", 2, (120.0, 200.0), (80.0, 140.0), ASM, "AMF-100 part; no price opened"),
    ("heel pod, wheel, fork, gears, shafts, sensors, drivers", 1, (150.0, 300.0), (40.0, 80.0), ASM, "custom module-0.1 gears, jewels"),
]


def all_tables() -> Dict:
    return {"B1": table(B1), "envelope": table(ENVELOPE), "front": table(FRONT), "nib": table(NIB), "head": table(HEAD),
            "face_stack": table(FACE_STACK), "electronics": table(ELEC), "modes": table(MODES), "thermal": table(THERMAL),
            "nre": NRE.d()}
