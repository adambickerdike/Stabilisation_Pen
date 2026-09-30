"""Every input of study N with its evidence label and source: V(value, unit, label, source) (revj/params.V record).

Labels: CALCULATION, SIMULATION, PROPOSED DESIGN, MANUFACTURER, LITERATURE, ASSUMPTION.  Values that another study
computed are read from its result file (read-only) where it matters; the rest are quoted with the file named.
SI units unless the key says otherwise.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict

from . import REPO_ROOT

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from revj.params import V  # noqa: E402  (the programme's labelled record)

CALC, SIM, PD, MFR, LIT, ASM = "CALCULATION", "SIMULATION", "PROPOSED DESIGN", "MANUFACTURER", "LITERATURE", "ASSUMPTION"


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


@lru_cache(maxsize=None)
def load_json(rel: str) -> Dict:
    return json.loads((REPO_ROOT / rel).read_text())


G0 = 9.80665

# ------------------------------------------------------------------------------------------------ loads (matched set)
LOADS = {
    "F_n_N": V(0.1958, "N", PD, "face force along the paper normal: N = F_n at every tilt (study B config/nib.yaml; Rev K's "
               "constant-force float, revk/params.B1 F_n_N); frozen only after gate G1 (EXP-B20)"),
    "tilts_mean_deg": V((35.0, 50.0, 60.0, 75.0), "deg", PD, "study B's four tilts for the mean over 35-75 deg "
                        "(bnib/candidates.THETAS)"),
    "tilt_worst_deg": V(35.0, "deg", LIT, "CON-02 / REQ-RVH-002 lower end of the 35-75 deg range (largest gravity and couple)"),
    "rolls_n": V(12, "-", PD, "roll sampled every 30 deg for the roll mean and the worst roll"),
    "residual_mean_mN": V(5.666, "mN", CALC, "study K face-parallelism Monte Carlo (results/revK/revK.json "
                          "face_parallelism_stack Q_mN.mean; contributors ASSUMPTION; EXP-B22 / EXP-B28)"),
    "residual_p95_mN": V(11.217, "mN", CALC, "study K face-parallelism Monte Carlo, 95th percentile"),
    "contact_share": V(0.70, "-", ASM, "study B duty: ball on the paper 70 % of the writing time (review section 4)"),
    "writing_speed_m_s": V(30.5e-3, "m/s", LIT, "CON-20 (adult phrase writing on paper), study B duty A"),
    "ink": V("oil_common", "-", LIT, "CON-13 friction of a common oil ballpoint (bnib/labels FRICTION)"),
    "slide_friction_N": V(0.010, "N", ASM, "refill-in-carrier slide friction (Rev J value, study B h_sl; REQ-BNIB-016)"),
    "face_mu": V(0.005, "-", ASM, "rolling shoe on the sapphire face (study B CounterFace.mu_face; EXP-B22)"),
    "face_guide_N": V(0.004, "N", ASM, "friction of the face's guide (study B CounterFace.h_face; K's float is a flexure)"),
    "couple_lever_mm": V(67.8, "mm", CALC, "ball to the face contact along the refill (study K nib.summary L_lever_mm = "
                         "holder z0 65.8 + stem 2.0 mm; couple M = F_n L cos(theta) = 10.87 mN m at 35 deg)"),
    "weight_trim": V(False, "-", PD, "matched baseline: the face is set parallel to the paper (study K's head), so the coils "
                     "hold the moving mass's weight in contact as well; study B's duty model trimmed the face to cancel it "
                     "in contact (bnib/balance.CounterFace comp_weight=True), which study K's budget inherited"),
}

# ------------------------------------------------------------------------------------------------ duties
DUTIES = {
    "A": V({"q_rms_mm": 0.20, "f_Hz": 8.0}, "-", ASM, "study B duty A: 0.2 mm rms per axis at 8 Hz, writing 30.5 mm/s in "
           "every direction, 70 % contact (bnib/candidates.DUTY_A)"),
    "modes_K": V({"steady_0mm": 0.0, "steady_1mm": 0.7071, "guide": 0.30, "spelling_cue": 0.0}, "mm rms per axis", ASM,
                 "study K's REQ-RVJ-I01 modes (revk/budgets.modes; 8 Hz); steady_2mm is clipped at the reach"),
    "severe": V({"f_Hz": 6.0, "bw_Hz": 0.6, "q_rms_2d_mm_by_reach": {"1.0": 0.771, "1.5": 0.930, "2.0": 0.997,
                                                                     "3.0": 1.031, "6.0": 1.036}},
                "-", SIM, "study F (results/readable/readable.json reach.rows '*|a_r2'): the nib's 2-D rms travel in contact "
                "when perfect knowledge is scaled to leave DEC-067's +2-words residual (0.65 mm), by usable reach; "
                "centre 6 Hz from study R's severe classes (PD 6.3 Hz, ET 5.7 Hz; docs/real_data.md), line width 0.6 Hz "
                "(study R's frequency SD); magnitude spread fitted to the perfect-knowledge command's p50/p90/p99 "
                "(1.21 / 2.50 / 3.81 mm, rms 1.60 mm)"),
    "screen": V({"f_Hz": (4.0, 8.0, 12.0), "n_dir": 8}, "-", CALC, "the independent pass's worst-case periodic screen "
                "(revk/improve.matched_force_duty): full-radius sinusoids at 4, 8, 12 Hz in eight directions"),
    "screen_pass_loads_mN": V((20.0, 40.0, 80.0), "mN", ASM, "the pass's constant residual loads (its sensitivity inputs)"),
}

# study F's residual left at the tip (mm) and share of contact time at the travel limit, by reach, for perfect knowledge
# (oracle) and for an estimator that itself leaves the +2 residual (a_r2)  (SIMULATION, results/readable/readable.json)
F_REACH = V({"reach_mm": (1.0, 1.5, 2.0, 3.0, 6.0),
             "oracle_tip_mm": (1.001, 0.674, 0.430, 0.153, 0.025), "oracle_at_limit": (0.638, 0.401, 0.225, 0.056, 0.001),
             "a_r2_tip_mm": (1.044, 0.818, 0.711, 0.654, 0.648), "a_r2_at_limit": (0.383, 0.149, 0.049, 0.004, 0.0)},
            "-", SIM, "study F reach check (docs/readable_target.md s8; tuning split, 20 severe cases, 5 writers, the Rev J "
            "nose with its travel cut): target DEC-067 0.55-0.65 mm")

# ------------------------------------------------------------------------------------------------ force constant
KM = {
    "derating": V(0.7, "x", ASM, "DEC-041 / study B / the pass: image-method magnetics is an upper bound; 0.7 x is the "
                  "stated derating (EXP-B23 / EXP-K22 measure K_m)"),
    "Br_tempco_per_K": V(-0.0012, "1/K", MFR, "AMF-139 (N52 reversible Br coefficient -0.12 %/degC)"),
    "grades": V({"N52": {"Br_T": 1.42, "T_max_C": 80.0}, "N48SH": {"Br_T": 1.38, "T_max_C": 150.0}}, "-", MFR,
                "AMF-139 (N52 1.42-1.48 T, 80 degC class), AMF-28 (N48SH class, 150 degC); low ends used"),
    "quad_fast": V((2, 1, 6), "-", CALC, "filaments bundle x thickness x piece for the optimiser: within 0.1 % of the "
                   "(8, 4, 32) reference on Rev K's coil (nibopt tests)"),
    "quad_fine": V((5, 3, 24), "-", CALC, "the pass's refinement quadrature (revk/improve.search_coil)"),
    "n_img_fast": V(2, "-", CALC, "image periods for the optimiser (0.04 % from 3 periods on Rev K's coil)"),
}

# ------------------------------------------------------------------------------------------------ electrical and thermal
ELEC = {
    "Cu_alpha_per_K": V(0.00393, "1/K", MFR, "AMF-29"),
    "rho_Cu_ohm_m": V(1.7241e-8, "ohm m", MFR, "AMF-29 (20 degC)"),
    "rho_C17200_ohm_m": V(1.7241e-8 / 0.22, "ohm m", MFR, "AMF-251 (C17200 AT(TF00) 22 % IACS minimum)"),
    "k_C17200_W_mK": V(105.0, "W/m K", MFR, "Materion alloy 25 (the pass's value, quoted there; ASSUMPTION for 0.1 mm wire)"),
    "V_low_V": V(3.3, "V", ASM, "low-battery bus (study B DRIVE V_low)"),
    "R_drv_ohm": V(0.24, "ohm", MFR, "AMF-37 (DRV8214 HS + LS)"),
    "I_max_A": V(1.0, "A", CALC, "study K: 3.3 V / (3.03 + 0.24) ohm with the C17200 leads"),
    "R_coil_K_ohm": V(2.5, "ohm", PD, "study B / K coil wound for 2.5 ohm per axis"),
    "wire_rise_limit_K": V(45.0, "K", ASM, "the pass's lead-heating screen (rise above the clamps, no convection)"),
    "coil_T_max_C": V(110.0, "degC", ASM, "coil insulation limit with margin (study B T_coil_max 120 degC)"),
}

THERMAL = {
    "room_C": V(30.0, "degC", PD, "rated maximum room (REQ-THM-001; study K)"),
    "skin_target_C": V(41.0, "degC", LIT, "AMF-34 (IEC 60601-1), study K's design target"),
    "h_W_m2K": V(10.0, "W/m^2 K", ASM, "natural convection + radiation (study K fin model, Rev J)"),
    "k_shell_W_mK": V(0.30, "W/m K", MFR, "AMF-24 (PEEK)"),
    "wall_mm": V(1.0, "mm", PD, "shell wall (study K)"),
    "R_int_K_W": V(15.0, "K/W", ASM, "coil to shell through the bonded stator (study K THERMAL R_int_coil_K_W)"),
}

# ------------------------------------------------------------------------------------------------ mechanics
MECH = {
    "R_carrier_mm": V(1.6, "mm", PD, "Ti carrier tube 3.2 / 2.5 mm round the D1 refill (study B/K)"),
    "refill_r_mm": V(1.175, "mm", LIT, "CON-22 (D1 refill 2.35 mm)"),
    "c_run_mm": V(0.30, "mm", ASM, "running clearance rule (Rev J / K)"),
    "c_fixed_mm": V(0.20, "mm", ASM, "fixed-part clearance rule (Rev J / K)"),
    "coil_p99_loss_mm": V(0.09, "mm", CALC, "study K tolerance Monte Carlo: the coil's 0.30 mm running clearance falls to "
                          "0.21 mm at the 99th percentile (revk/tolerance.mechanics, results/revK/revK.json tolerance)"),
    "clearance_p99_min_mm": V(0.20, "mm", PD, "brief: coil clearance >= 0.2 mm at the stop, 99th percentile"),
    "stop_margin_mm": V(0.20, "mm", PD, "hard stop 0.2 mm beyond the usable radius (study B / the pass)"),
    "goodman_min": V(1.5, "-", PD, "brief / study B FAT SF_min"),
    "servo_bw_min_Hz": V(40.0, "Hz", PD, "REQ-BNIB-006"),
    "mode_ratio": V(2.5, "x", PD, "DEC-050: lowest structural mode >= 2.5 x the servo bandwidth, ball free and stuck"),
    "cycles": V(43.2e6, "cycles", CALC, "study B FAT (8 Hz x 2 h/day x 250 days x 3 yr)"),
    "C17200": V({"E": 127.6e9, "S_f": 310e6, "S_u": 1280e6, "S_y": 1241e6, "rho": 8250.0}, "SI", MFR,
                "AMF-19 (CDA C17200 TH04: E, fatigue 310 MPa at 1e8); UTS 1280 MPa as the pass (feasibility.wire_anchor)"),
    "fatigue_knockdown": V(0.85, "x", ASM, "size/surface knock-down on thin wire (study B FAT size_surface)"),
    "Kt_worst": V(2.5, "-", ASM, "stress concentration at a soldered clamp or sleeve edge, worst corner (the pass, study B)"),
    "tol_corner": V({"d": 1.02, "L_mm": -0.05, "E": 1.04, "anchor": 1.2, "assembly_N": 0.005}, "-", ASM,
                    "the pass's worst fatigue corner (revk/improve.wire_design): diameter +2 %, length -0.05 mm, modulus "
                    "+4 %, anchor stiffness +20 %, 5 mN assembly tension"),
    "strut_misfit_um": V(2.0, "um", ASM, "axial length misfit between struts after jigged soldering (an over-constrained "
                         "plane for n > 3); EXP-NB04 measures it"),
    "hertz_C0_GPa": V(4.2, "GPa", MFR, "AMF-260 (MinebeaMitsumi: the basic static load rating is the load at which the "
                      "contact stress at the centre of the most loaded ball-race contact is 4,200 MPa, a permanent "
                      "deformation of about 0.0001 of the ball diameter; ISO 76's basis)"),
    "hertz_run_GPa": V(4.2 / 2.0 ** (1 / 3), "GPa", ASM, "sustained writing load: static safety factor s0 >= 2 for quiet "
                       "running and high accuracy (AMF-261, NES after ISO 76), i.e. 4.2 GPa / 2^(1/3) = 3.33 GPa; applying "
                       "the ball-bearing rule to 440C sphere-on-flat races is an ASSUMPTION (EXP-K20 / EXP-NB05)"),
    "hertz_static_GPa": V(4.2 / 1.5 ** (1 / 3), "GPa", ASM, "drop (the race springs' release load): s0 >= 1.5 for "
                          "pronounced shock (AMF-261), 4.2 GPa / 1.5^(1/3) = 3.67 GPa; study K used 4 GPa"),
    "mu_roll": V(0.001, "-", ASM, "rolling resistance of Si3N4 balls on lapped 440C (study K / the pass; EXP-K20)"),
    "preload_min_margin": V(1.2, "x", PD, "race preload >= 1.2 x the preload at which the Hertz solver first unloads a "
                                          "ball under the 35 deg couple (covers F_n +20 %, REQ-BNIB-008)"),
    "holder_ext_g_per_mm": V(0.025, "g/mm", ASM, "the pass's moving-mass charge for the refill-holder extension "
                             "(revk/improve.matched_force_duty: 0.025e-3 kg per mm)"),
    "Ti_rho": V(4430.0, "kg/m3", MFR, "AMF-21"),
    "Al_rho": V(2810.0, "kg/m3", ASM, "7075 handbook value"),
    "CFRP_rho": V(1550.0, "kg/m3", ASM, "pultruded carbon tube handbook value"),
    "Fe_rho": V(7870.0, "kg/m3", ASM, "1010 steel handbook value (study B)"),
    "Hiperco_rho": V(8120.0, "kg/m3", ASM, "Hiperco 50A handbook value (AMF-140 for B_sat)"),
    "B_plate_T": V({"1010": 1.5, "Hiperco50A": 2.1}, "T", ASM, "working flux density in the back plate and keeper "
                   "(1010 saturates near 1.6-1.7 T; Hiperco 50A 2.35 T, AMF-140), used to size the plate thickness"),
}

# ------------------------------------------------------------------------------------------------ the pen (study K)
PEN = {
    "length_K_mm": V(145.13, "mm", CALC, "study K layout (results/revK/layout.json length)"),
    "length_limit_mm": V(175.0, "mm", ASM, "Rev J envelope (docs/revJ_plan.md s6)"),
    "mass_K_g": V(66.4, "g", CALC, "study K base pen (results/revK/budgets.json)"),
    "actuator_z0_mm": V(21.43, "mm", CALC, "study K back-plate front face (results/revK/layout.json back_plate z0)"),
    "actuator_stack_K_mm": V(8.48, "mm", CALC, "study K back plate 1.47 + magnets 3.5 + c0 0.3 + coils 1.6 + c1 0.15 + keeper "
                             "1.47 mm"),
    "guide_stack_K_mm": V(3.70, "mm", CALC, "study K front race 0.3 + balls 0.8 + flange 1.5 + balls 0.8 + rear race 0.3 mm"),
    "wire_K_mm": V(26.80, "mm", CALC, "study K C17200 lead length (z 31.8-58.6)"),
    "shell_g_per_mm": V(0.094, "g/mm", CALC, "PEEK tube 24 / 22 mm (MANUFACTURER AMF-24 density 1.30 g/cc)"),
    "wiring_share": V(0.10, "x", ASM, "+10 % wiring and adhesive (Rev J / K convention)"),
}


def all_tables() -> Dict:
    return {"loads": table(LOADS), "duties": table(DUTIES), "F_reach": F_REACH.d(), "force_constant": table(KM),
            "electrical": table(ELEC), "thermal": table(THERMAL), "mechanics": table(MECH), "pen": table(PEN)}
