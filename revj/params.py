"""Every input of the Rev J integration with its label and source.

Labels: CALC (calculated in a round-1 study or here), SIM (an executed round-1 simulation, file named), MFR (ledger id in
docs/evidence.csv), LIT (ledger id), ASSUMPTION (chosen, to be measured).  Values that come from a round-1 result file
are loaded from that file (read-only) so the integration follows the studies if they are re-run.

Frames (as results/revH/layout.json): z along the pen axis from the ball tip (z = 0 at 50 deg with the nose centred)
toward the back; x in the tilt plane, positive AWAY from the paper (the paper side is -x); y lateral.  Units mm, g, N,
W unless stated.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Dict

from . import REPO_ROOT


@dataclass(frozen=True)
class V:
    value: object
    unit: str
    label: str
    source: str
    note: str = ""

    def d(self) -> Dict:
        out = {"value": self.value, "unit": self.unit, "label": self.label, "source": self.source}
        if self.note:
            out["note"] = self.note
        return out


def _load(rel: str) -> Dict:
    with open(REPO_ROOT / rel) as f:
        return json.load(f)


# ----------------------------------------------------------------------------------------------------------- envelope
ENVELOPE = {
    "handle_od_held_mm": V(24.0, "mm", "ASSUMPTION", "docs/revJ_plan.md s6 (lead envelope; studies may argue)"),
    "endcap_od_mm": V(26.0, "mm", "ASSUMPTION", "docs/revJ_plan.md s6"),
    "length_mm": V(175.0, "mm", "ASSUMPTION", "docs/revJ_plan.md s6"),
    "mass_g": V(120.0, "g", "ASSUMPTION", "docs/revJ_plan.md s6 ('with every module')"),
    "battery_h": V(8.0, "h", "ASSUMPTION", "docs/revJ_plan.md s6 (writing with assistance on)"),
    "coil_rise_K": V(20.0, "K", "ASSUMPTION", "nose2 design rule (DT_COIL_MAX); REQ-RVJ-N03 proposed"),
    "grip_max_C": V(41.0, "degC", "LIT", "AMF-34 (IEC 60601-1 cl. 11.1.2.2: no justification needed at or below 41 degC)"),
    "held_max_C": V(43.0, "degC", "LIT", "AMF-35 (continuously held parts, all materials: 43 degC)"),
    "grip_zone_mm": V((20.0, 45.0), "mm", "ASSUMPTION", "Rev H layout grip_zone (results/revH/layout.json)"),
    "finger_pads_z_mm": V((26.0, 32.0, 38.0), "mm", "ASSUMPTION", "Rev H layout hand.finger_pads_z"),
    "web_z_mm": V(92.0, "mm", "ASSUMPTION", "Rev H layout hand.web_z (thumb-index web rests on the top of the pen)"),
}

# ----------------------------------------------------------------------------------------------------------- nose (C1S)
@lru_cache(maxsize=1)
def nose_design() -> Dict:
    """The recommended C1S nose of study N (results/nose2/nose2.json -> recommended), lengths in mm (CALC, study N)."""
    rec = _load("results/nose2/nose2.json")["recommended"]["design"]
    v = rec["vars"]
    w, t_m, t_c = v["w"] * 1e3, v["t_m"] * 1e3, v["t_c"] * 1e3
    B, Bsat = rec["B_gap_T"], 2.3                                   # Hiperco 50A design saturation (nose2 BACK_IRON, AMF-140)
    t_bi = max(B * w / Bsat + 0.3, 0.5)                             # back iron carrying one pole's flux (nose2 act_unit)
    z_p, L_b = v["z_p"] * 1e3, v["L_b"] * 1e3
    z_a = z_p + L_b
    return {
        "kind": rec["kind"], "parts": rec["parts"], "vars_m": v,
        "z_p": z_p, "L_b": L_b, "z_a": z_a, "w": w, "t_m": t_m, "t_c": t_c, "t_bi": t_bi, "gap": rec["gap_mm"],
        "r_disc": w * math.sqrt(2.0) + 0.5, "stroke_act": rec["stroke_act_mm"],
        "X_nom": rec["X_nom_mm"], "X_min": rec["X_min_mm"],
        "Km_tip": rec["Km_tip"], "Km_act": rec["Km_act"], "B_gap_T": B, "m_eff_tip_g": rec["m_eff_tip_g"],
        "k_tip_N_m": rec["k_tip_N_m"], "P_tremor_W": rec["P_tremor_W"], "P_autowrite_W": rec["P_autowrite_W"],
        "dT_coil_K": rec["dT_coil_K"], "F_pk_tip_N": rec["F_pk_tip_N"], "f_parasitic_Hz": rec["f_parasitic_Hz"],
        "m_act_move_g": rec["m_act_move_g"], "m_act_stat_g": rec["m_act_stat_g"], "mass_added_g": rec["mass_added_g"],
        "F_grav_tip_N": rec["F_grav_tip_N"], "d_cm_mm": rec["d_cm_mm"],
        "cap_front": z_a - (t_m + t_bi), "cap_depth": t_m + t_bi,
        "label": "CALC (study N design model, results/nose2/nose2.json -> recommended)",
    }


NOSE = {
    "stop_extra_mm": V(0.5, "mm", "ASSUMPTION", "DEC-034 / nose2 frontend: stop = usable travel + 0.5 mm"),
    "servo_hz": V(80.0, "Hz", "ASSUMPTION", "Rev H tip_params (results/revH/tip_params.json); nose2 hw1_designs"),
    "servo_zeta": V(0.7, "-", "ASSUMPTION", "Rev H tip_params"),
    "slew_m_s": V(0.6, "m/s", "ASSUMPTION", "Rev H tip_params"),
    "latency_s": V(0.0006, "s", "ASSUMPTION", "nose2 hw1_designs (results/nose2/nose2.json)"),
    "coil_R_th_K_W": V(100.0, "K/W", "ASSUMPTION", "nose2 R_TH_COIL (coil to ambient through the shell)"),
    "V_bus": V(3.7, "V", "ASSUMPTION", "nose2 V_BUS (Rev H drive assumption)"),
    "I_peak_A": V(1.5, "A", "ASSUMPTION", "nose2 I_PEAK (DRV8214 4 A peak, MFR AMF-37)"),
    "mu_ball": V(0.15, "-", "ASSUMPTION", "nose2 MU_BALL (LIT CON-13 0.09-0.165)"),
    "F_refill_N": V(0.15, "N", "ASSUMPTION", "Rev H refill force (HW1 Pen.F_c); REQ-RVJ-N05 proposed 0.15 N +-20 %"),
    "tremor_a_eff": V(10.6, "m/s^2", "SIM", "nose2 Duty.tremor_a_eff (calibrated on HW1, tuning writer 100, seed 300; 1 mm 8 Hz)"),
    "aw_ink_share": V(0.6, "-", "ASSUMPTION", "nose2 Duty.aw_ink_share"),
    "pen_lift_W": V(0.0708, "W", "CALC", "nose2 axial_dof (results/nose2/nose2.json -> axial_dof.P_avg_W; 4.2 lifts/s, 17 mJ/cycle)"),
    "pen_lift_stroke_mm": V(0.5, "mm", "ASSUMPTION", "nose2 (LIT PAT-41: 0.5-0.64 mm)"),
    "pen_lift_delay_s": V(0.008, "s", "ASSUMPTION", "nose2 autowrite command-to-contact"),
}

# ----------------------------------------------------------------------------------------------------------- heel drive
HEEL = {
    "r_e_mm": V(1.0, "mm", "ASSUMPTION", "study D: 2 mm wheel, the smallest that takes a replaceable O-ring tyre"),
    "t_wall_mm": V(0.3, "mm", "ASSUMPTION", "drive/geometry.py T_WALL (housing / fork wall around the element)"),
    "c_nose_mm": V(0.3, "mm", "ASSUMPTION", "drive/geometry.py C_NOSE (pod to nose envelope at its stop)"),
    "cap_r_extra_mm": V(0.5, "mm", "ASSUMPTION", "drive/geometry.wheel_pod: steering ring radius r_e + 0.5 mm"),
    "cap_h_mm": V(1.0, "mm", "ASSUMPTION", "drive/geometry.wheel_pod: steering ring 1.0 mm tall above the wheel"),
    "delta_mm": V(0.35, "mm", "ASSUMPTION", "study D: the wheel sticks out 0.35 mm beyond the skid ring at 50 deg"),
    "roll_deg": V(20.0, "deg", "ASSUMPTION", "study D: wheel keeps contact up to +-20 deg of pen roll"),
    "theta_steer_deg": V(50.0, "deg", "ASSUMPTION", "study D: steering axis on the paper normal at 50 deg"),
    "preload_N": V(0.55, "N", "ASSUMPTION", "study D preload (T1; design optimum 0.57 N, CALC)"),
    "mu_range": V((0.6, 1.2), "-", "ASSUMPTION", "study D tyre-paper friction (EXP-D01)"),
    "k_lat_N_m": V(1500.0, "N/m", "CALC", "study D tyre tangential stiffness (drive/params.py CONTACT.k_lat)"),
    "rolling_coef": V(0.078, "-", "CALC", "study D T2 at 0.5 N (Persson, LIT AMF-112)"),
    "reflected_mass_g": V(3.8, "g", "CALC", "study D T7 (steered + driven wheel)"),
    "backdrive_N": V(0.030, "N", "CALC", "study D (0.9 per mesh; the simulation used 0.024 N)"),
    "F_cap_N": V(0.5, "N", "ASSUMPTION", "study D supervisor: min(0.5 N, 0.8 x mu_hat x wheel load)"),
    "F_cont_N": V(0.41, "N", "CALC", "study D: 0620 B at 3.7 V, 2:1, three meshes, r 1.0 mm (continuous)"),
    "F_peak_N": V(0.67, "N", "CALC", "study D (peak)"),
    "steer_bw_hz": V(40.0, "Hz", "ASSUMPTION", "study D steering servo (SIM model)"),
    "steer_rate_rad_s": V(500.0, "rad/s", "ASSUMPTION", "study D steering servo rate limit (SIM model)"),
    "mesh_eff": V(0.9, "-", "ASSUMPTION", "study D, per module-0.1 gear mesh"),
    "P_steer_only_W": V(0.001, "W", "SIM", "study D S1a (drive power while guiding, steer only)"),
    "P_guide_W": V(0.006, "W", "SIM", "study D S1a (steered + driven guidance)"),
    "P_lead_W": V(0.084, "W", "SIM", "study D S5 (wheel lead + nose)"),
    "P_drivers_W": V((0.010, 0.020), "W", "ASSUMPTION", "study D s4.5 motor drivers and Hall sensors"),
}

MOTOR = {  # Faulhaber 0620 B (MFR AMF-100; AMF-78 for the 0620 K 006 B data)
    "d_mm": V(6.0, "mm", "MFR", "AMF-100"), "l_mm": V(20.0, "mm", "MFR", "AMF-100"), "mass_g": V(2.5, "g", "MFR", "AMF-100"),
    "rated_mNm": V(0.28, "mN m", "MFR", "AMF-100"), "stall_mNm": V(0.732, "mN m", "MFR", "AMF-100 (6 V)"),
    "friction_mNm": V(0.011, "mN m", "MFR", "AMF-100 (static friction torque)"),
    "kt_mNm_A": V(1.09, "mN m/A", "MFR", "AMF-100"), "R_ohm": V(8.8, "ohm", "MFR", "AMF-100"),
    "J_gcm2": V(0.0095, "g cm^2", "MFR", "AMF-100"), "Rth_K_W": V(97.5, "K/W", "MFR", "AMF-100 (13.2 + 84.3)"),
    "rotor_magnet": V("d 2.5 x 12 mm NdFeB, diametric, Br 1.2 T", "-", "ASSUMPTION",
                      "not in the ledger extract; used only for the magnetic-torque bound (revj/magnetics.py)"),
}

# ----------------------------------------------------------------------------------------------------------- end-cap
@lru_cache(maxsize=1)
def endcap_parts() -> Dict:
    return _load("results/endcap/layout_parts.json")


ENDCAP = {
    "P_sim_W": V(0.029, "W", "SIM", "study K test runs (drivers included), docs/inertial_endcap.md s9.1"),
    "P_design_W": V(0.145, "W", "CALC", "study K design model (full cancellation at 10 Hz, 1 mm)"),
    "P_peak_W": V(1.0, "W", "CALC", "study K design model"),
    "length_mm": V(24.0, "mm", "CALC", "study K compact packaging (z 151-175 in Rev H)"),
    "flexure_hz": V(5.0, "Hz", "CALC", "study K: two spiral flexures tuned to 5 Hz"),
    "stroke_mm": V(4.0, "mm", "CALC", "study K (+-4.0 mm, both axes)"),
    "Km_N_sqrtW": V(0.735, "N/sqrt(W)", "CALC", "study K design (four arc coils)"),
    "gain": V(0.75, "-", "SIM", "study K rule (tuning seeds 300-303)"),
}

# ----------------------------------------------------------------------------------------------------------- electronics, cell
POWER = {
    "base_W": V(0.065, "W", "ASSUMPTION", "Rev H base electronics and radio (docs/opt_inertial.md s8.2)"),
    "nose_drivers_hall_W": V(0.012, "W", "ASSUMPTION", "Rev H drivers and Hall (docs/opt_inertial.md s2)"),
    "page_sensor_mA": V((16.3, 21.6), "mA", "MFR", "AMF-109 (PMW3360 run current with 1 ms polling)"),
    "page_sensor_V": V((1.9, 3.7), "V", "ASSUMPTION", "a 1.9 V buck (PMW3360 core) to the raw cell voltage (linear)"),
    "slide_sensor_W": V((0.004, 0.008), "W", "ASSUMPTION",
                        "refill-slide 3-D Hall (TMAG5273 class, 2.3 mA active, MFR OPT-45) duty-cycled at 1 kHz"),
    "cell_mAh": V(750.0, "mAh", "MFR", "AMF-80 (EEMB LIR14500)"),
    "cell_V": V(3.7, "V", "MFR", "AMF-80"),
    "usable_frac": V(0.8, "-", "ASSUMPTION", "Rev H: 2.22 Wh usable of 2.78 Wh"),
    "cell_d_mm": V(14.1, "mm", "MFR", "AMF-80 drawing 14.1 x 48.5 mm"),
    "cell_l_mm": V(48.5, "mm", "MFR", "AMF-80"),
    "cell_g": V(20.0, "g", "MFR", "AMF-80 (about 20 g)"),
}

# ----------------------------------------------------------------------------------------------------------- materials
RHO = {  # g/cm3
    "Ti": V(4.42, "g/cm3", "MFR", "AMF-21"), "PEEK": V(1.30, "g/cm3", "MFR", "AMF-24"),
    "TPE": V(1.10, "g/cm3", "ASSUMPTION", "Rev H front sleeve overmould"), "POM": V(1.41, "g/cm3", "ASSUMPTION", "handbook"),
    "steel": V(7.9, "g/cm3", "ASSUMPTION", "handbook"), "brass": V(8.5, "g/cm3", "ASSUMPTION", "handbook"),
    "Al": V(2.70, "g/cm3", "ASSUMPTION", "handbook"), "NdFeB": V(7.6, "g/cm3", "MFR", "AMF-139"),
    "Hiperco": V(8.12, "g/cm3", "ASSUMPTION", "nose2 BACK_IRON (AMF-140 for saturation)"), "FR4": V(1.9, "g/cm3", "ASSUMPTION", "handbook"),
}

SPRING = {  # the ink-force spiral spring (301 full hard strip) in the pen-lift drum
    "E_GPa": V(200.0, "GPa", "LIT", "AMF-20 (301 full hard; aggregated database, low provenance)"),
    "UTS_MPa": V(1460.0, "MPa", "LIT", "AMF-20"),
    "yield_MPa": V(1080.0, "MPa", "LIT", "AMF-20"),
    "fatigue_MPa": V(540.0, "MPa", "LIT", "AMF-20 (fatigue strength as listed; cycle count of the listing not stated)"),
    "knockdown_1e8": V(0.8, "-", "ASSUMPTION", "extra factor on the fatigue strength for 1e8 cycles, thin-strip surface and size"),
    "sigma_static_frac": V(0.55, "-", "ASSUMPTION", "peak stress <= 0.55 x UTS"),
    "force_tol": V(0.20, "-", "ASSUMPTION", "REQ-RVJ-N05 proposed: 0.15 N +-20 %"),
    "r_drum_mm": V(2.8, "mm", "ASSUMPTION", "capstan radius = the pen-lift module's outer radius (nose2 layout: d 5.6 mm)"),
    "r_hub_mm": V(1.8, "mm", "ASSUMPTION", "inner radius of the annular drum (the refill holder passes through)"),
    "drum_len_mm": V(7.0, "mm", "ASSUMPTION", "nose2 layout refill_lift length"),
    "m_drum_rotor_g": V(0.3, "g", "ASSUMPTION", "rotating part of the drum (a thin sleeve), for the reflected mass"),
}

THERMAL = {
    "h_W_m2K": V(10.0, "W/m^2K", "ASSUMPTION", "natural convection + radiation from a 24 mm cylinder near room temperature"),
    "k_shell_W_mK": V(0.30, "W/mK", "MFR", "AMF-24 (PEEK 0.29-0.32 W/mK)"),
    "shell_wall_mm": V(1.0, "mm", "ASSUMPTION", "Rev H / nose2 shell wall"),
    "R_int_K_W": V(15.0, "K/W", "ASSUMPTION", "coil layer to shell through the bonded coil plate"),
    "ambient_C": V(23.0, "degC", "ASSUMPTION", "EXP-N04 ambient"),
    "ambient_hot_C": V(30.0, "degC", "ASSUMPTION", "a warm room (sensitivity)"),
    "k_al_W_mK": V(167.0, "W/mK", "ASSUMPTION", "aluminium 6061 handbook value (heat spreader option)"),
    "spreader": V({"t_mm": 0.5, "L_mm": 20.0, "z_mm": [82.0, 102.0]}, "mm", "ASSUMPTION",
                  "proposed aluminium sleeve inside the PEEK shell over the actuator (option)"),
}


def all_tables() -> Dict:
    def t(d):
        return {k: v.d() for k, v in d.items()}
    return {"envelope": t(ENVELOPE), "nose": t(NOSE), "heel": t(HEEL), "motor": t(MOTOR), "endcap": t(ENDCAP),
            "power": t(POWER), "rho": t(RHO), "spring": t(SPRING), "thermal": t(THERMAL),
            "nose_design": {k: v for k, v in nose_design().items() if k != "vars_m"}}


def val(x):
    """The value of a V (or the object itself)."""
    return x.value if isinstance(x, V) else x
