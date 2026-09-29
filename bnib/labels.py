"""Labelled inputs of study B.  Every value is V(value, unit, label, source): labels CALC, SIM, LIT (ledger id),
MFR (ledger id), ASSUMPTION, PROPOSED DESIGN.  Ledger ids refer to docs/evidence.csv or to the rows this study proposes in
results/bnib/evidence_rows.csv (only for sources opened in this study).  SI units inside the code.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
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


def val(v):
    return v.value if isinstance(v, V) else v


G0 = 9.80665
D2R = math.pi / 180.0

# ------------------------------------------------------------------------------------------------ the C1S reference
@lru_cache(maxsize=1)
def c1s() -> Dict:
    """Study N's recommended C1S nose (results/nose2/nose2.json -> recommended), read-only (CALC, study N)."""
    d = json.load(open(REPO_ROOT / "results" / "nose2" / "nose2.json"))["recommended"]["design"]
    return d


C1S = {
    "F_c": V(0.15, "N", "ASSUMPTION", "Rev H/J refill force (REQ-RVJ-N05 proposed 0.15 N +-20 %); the review's input"),
    "L_t": V(76.48e-3, "m", "CALC", "study N gimbal-to-ball (results/nose2/nose2.json z_p_mm); the review's input"),
    "L_a": V(11.5e-3, "m", "CALC", "study N magnet arm (z_a - z_p); the review's input"),
    "Km_act": V(0.656, "N/sqrt(W)", "CALC", "study N image-method magnetics, an upper bound (results/nose2/nose2.json Km_act)"),
    "R_coil": V(2.47, "ohm", "ASSUMPTION", "3.7 V / 1.5 A drive (Rev H, study N); the review's input"),
    "k_r": V(0.0028, "N m/rad", "CALC", "study N cross-strip gimbal, 50 um strips (Rev J.1: 0.0094 unloaded at 75 um)"),
    "m_eff_tip": V(2.10e-3, "kg", "CALC", "study N design model (sim2j's Rev J model: 1.50 g)"),
    "contact_duty": V(0.70, "-", "ASSUMPTION", "share of writing time with the ball on the paper (review section 4; sim2j run)"),
}

# ------------------------------------------------------------------------------------------------ contact and friction
CONTACT = {
    "theta_range_deg": V((35.0, 75.0), "deg", "LIT", "CON-02 (about 50 deg mean, +-2.5 deg while writing); REQ-RVH-002 35-75 deg"),
    "theta_nominal_deg": V(50.0, "deg", "LIT", "CON-02"),
    "F_c_nominal": V(0.15, "N", "ASSUMPTION", "REQ-RVJ-N05 proposed; below every manufacturer test load found (see inkforce.py)"),
    "F_c_tol": V(0.20, "-", "ASSUMPTION", "REQ-RVJ-N05 proposed +-20 % over the slide"),
    "F_c_range": V((0.05, 0.50), "N", "ASSUMPTION", "sensitivity range until gate G1 measures the minimum reliable ink force"),
    "slide_friction": V(0.010, "N", "ASSUMPTION", "refill-in-carrier friction hysteresis (results/revJ/sim_params.json, Rev J)"),
    "r_ball": V(0.35e-3, "m", "LIT", "CON-22 (0.7 mm ball, ISO 12757 tip class F)"),
    "refill_len": V(67.0e-3, "m", "LIT", "CON-22 (ISO 12757-1 type D: 67 +0.3/0 mm, tube 2.35 mm)"),
    "refill_d": V(2.35e-3, "m", "LIT", "CON-22"),
    "refill_mass": V(0.84e-3, "kg", "ASSUMPTION", "D1 refill 0.84 g (DEC-004, study N)"),
    "refill_len_tol": V(0.3e-3, "m", "LIT", "CON-22 (+0.3/0 mm)"),
}

# friction map: kinetic coefficient of the ball on paper by ink type (CON-13, Hase 2022: 1.0-1.5 N, 15 mm/s, 90 deg,
# read from a plot), a load and speed dependence (ASSUMPTION shapes; CON-14 says mu rises with load on a tablet film),
# paper spread (ASSUMPTION) and LuGre/Stribeck static ratio (sim2 H1 values, ASSUMPTION)
FRICTION = {
    "mu_ink": {"oil_common": V(0.165, "-", "LIT", "CON-13 (Figure 9, read from plot)"),
               "oil_low_friction": V(0.105, "-", "LIT", "CON-13"),
               "gel": V(0.095, "-", "LIT", "CON-13"),
               "water_based": V(0.090, "-", "LIT", "CON-13")},
    "paper_spread": V((0.8, 1.3), "x", "ASSUMPTION", "six-paper spread to be measured in gate G1 (EXP-B21)"),
    "load_exp": V(0.10, "-", "ASSUMPTION", "mu ~ (N / 1.2 N)^0.10: CON-14 reports mu rising with load (tablet film); "
                                            "at the design's 0.1-0.4 N the extrapolation is unmeasured"),
    "speed_log": V(0.04, "-", "ASSUMPTION", "mu ~ 1 + 0.04 ln(v / 15 mm/s) (mild viscous rise of the ink film; unmeasured)"),
    "ms_ratio": V(1.3, "-", "ASSUMPTION", "static/kinetic (sim2 H1 LuGre, EXP-Q01)"),
    "v_stribeck": V(2e-3, "m/s", "ASSUMPTION", "sim2 H1"),
    "presliding": V(1e-5, "m", "ASSUMPTION", "sim2 H1"),
}

# ------------------------------------------------------------------------------------------------ materials
MAT = {
    "NdFeB_N52_Br": V(1.42, "T", "MFR", "AMF-139 (1.42-1.48 T; 80 degC class; -0.12 %/degC)"),
    "NdFeB_N48SH_Br": V(1.38, "T", "MFR", "AMF-28 (N48SH class; 150 degC)"),
    "NdFeB_rho": V(7600.0, "kg/m3", "MFR", "AMF-139"),
    "NdFeB_tc": V(-0.0012, "1/K", "MFR", "AMF-139 alpha(Br)"),
    "Hiperco_Bsat": V(2.4, "T", "MFR", "AMF-140"),
    "steel1010_Bsat": V(1.6, "T", "ASSUMPTION", "nose2 BACK_IRON"),
    "Fe_rho": V(7870.0, "kg/m3", "ASSUMPTION", "handbook"),
    "Cu_res": V(1.7241e-8, "ohm m", "MFR", "AMF-29 (20 degC)"),
    "Cu_alpha": V(0.00393, "1/K", "MFR", "AMF-29"),
    "Cu_rho": V(8890.0, "kg/m3", "MFR", "AMF-29"),
    "Ti_rho": V(4420.0, "kg/m3", "MFR", "AMF-21"),
    "Ti_E": V(114e9, "Pa", "MFR", "AMF-21"),
    "PEEK_rho": V(1300.0, "kg/m3", "MFR", "AMF-24"),
    "PEEK_k": V(0.30, "W/mK", "MFR", "AMF-24 (0.29-0.32)"),
    "Al_rho": V(2700.0, "kg/m3", "ASSUMPTION", "handbook"),
    "W_rho": V(18000.0, "kg/m3", "MFR", "AMF-49"),
    "PZT_rho": V(7800.0, "kg/m3", "ASSUMPTION", "opt/hardware DENS (PICMA class)"),
}

# flexure alloys: (E Pa, fatigue strength Pa, yield Pa, UTS Pa, density, magnetic?, ledger)
FLEX = {
    "C17200_TH04": dict(E=127.6e9, S_f=310e6, S_y=1241e6, S_u=1379e6, rho=8260.0, magnetic=False,
                        src="AMF-19 (fatigue at 1e8 cycles, flat products; E ASSUMPTION within AMF-19 context)"),
    "Ti6Al4V": dict(E=114e9, S_f=530e6, S_y=910e6, S_u=1000e6, rho=4420.0, magnetic=False,
                    src="AMF-20 (fatigue 530-630 MPa as listed, aggregated database, low provenance; low end used) / AMF-21 (E, static)"),
    "301FH": dict(E=200e9, S_f=540e6, S_y=1080e6, S_u=1460e6, rho=7800.0, magnetic=True,
                  src="AMF-20 (aggregated; full-hard 301 is partly martensitic: ferromagnetic near magnets, ASSUMPTION)"),
    "17-7PH_CH900": dict(E=200e9, S_f=520e6, S_y=1210e6, S_u=1650e6, rho=7700.0, magnetic=True,
                         src="AMF-20 (aggregated; precipitation-hardened 17-7PH is ferromagnetic, ASSUMPTION)"),
}
FAT = {
    "cycles": V(43.2e6, "cycles", "CALC", "review section 6: 8 Hz x 2 h/day x 250 days/yr x 3 yr"),
    "size_surface": V(0.85, "-", "ASSUMPTION", "extra knock-down on the listed fatigue strength for thin wire/strip surface "
                                                 "and size (drawn or etched finish; coupon tests replace it: EXP-B25)"),
    "SF_min": V(1.5, "-", "ASSUMPTION", "design safety factor on the Goodman line (study N / Rev J.1 convention)"),
    "Kt_clamp": V(1.8, "-", "ASSUMPTION", "stress concentration at a clamped/soldered wire root (1.5-2.5 typical for a "
                                           "clamp edge without a radius; a 0.1 mm radius clamp brings it near 1.2)"),
    "Kt_etched_strip": V(1.3, "-", "ASSUMPTION", "photo-etched strip root with a 0.2 mm fillet"),
}

# ------------------------------------------------------------------------------------------------ drive, electronics
DRIVE = {
    "V_bus": V(3.7, "V", "ASSUMPTION", "single Li-ion cell (Rev H drive)"),
    "V_low": V(3.3, "V", "ASSUMPTION", "low-battery bus for the headroom check"),
    "I_peak": V(1.5, "A", "ASSUMPTION", "Rev H / study N per-axis limit (DRV8214 4 A peak, 2 A rms: MFR AMF-37)"),
    "driver_Rds": V(0.24, "ohm", "MFR", "AMF-37 (DRV8214 HS+LS 240 mOhm)"),
    "electronics_W": V((0.034, 0.060), "W", "CALC", "Rev J.1 datasheet count (docs/revJ1_design.md s4.1; OPT-60, OPT-37, AMF-37)"),
    "page_sensor_W": V((0.0013, 0.0019), "W", "CALC", "Rev J.1 (PMW3610 class on in every mode, OPT-61)"),
    "cell_Wh_usable": V(2.22, "Wh", "MFR", "AMF-80 (LIR14500 750 mAh 3.7 V) x 0.8 usable (ASSUMPTION)"),
    "cell_slim_Wh_usable": V(0.89, "Wh", "ASSUMPTION", "review section 8: 300 mAh 3.7 V = 1.11 Wh nominal; 80 % usable"),
    "cell_slim_mass": V(9.0e-3, "kg", "ASSUMPTION", "a 10440-class 300-350 mAh Li-ion cell (no datasheet opened here)"),
    "cell_slim_len": V(44e-3, "m", "ASSUMPTION", "10440 class (10 x 44 mm)"),
    "driver_eff": V(0.85, "-", "ASSUMPTION", "coil copper loss -> battery (bridge and conversion losses)"),
}

# ------------------------------------------------------------------------------------------------ thermal (two nodes)
THERMAL = {
    "R_cs": V(15.0, "K/W", "ASSUMPTION", "coil to shell through the bonded coil plate (Rev J params R_int)"),
    "C_coil": V(0.5, "J/K", "ASSUMPTION", "coil node (Rev H / sim2 C_th)"),
    "h_conv": V(10.0, "W/m2K", "ASSUMPTION", "natural convection + radiation from the shell (Rev J)"),
    "hand_contact_frac": V(0.0, "-", "ASSUMPTION", "no heat into the hand counted (conservative, Rev J.1)"),
    "T_room": V(30.0, "degC", "PROPOSED DESIGN", "rated maximum room (Rev J.1 proposal; ECMA-287 B.5, AMF-35)"),
    "T_skin_max": V(43.0, "degC", "LIT", "AMF-35 (ECMA-287 Table 5.2, continuously held, all materials)"),
    "T_skin_target": V(41.0, "degC", "LIT", "AMF-34 (IEC 60601-1: no justification needed at or below 41 degC)"),
    "T_coil_max": V(120.0, "degC", "ASSUMPTION", "sim2 coil limit (class 155 wire derated); magnet N52 80 degC class: AMF-139"),
    "T_magnet_max": V(80.0, "degC", "MFR", "AMF-139 (N52 80 degC class)"),
    "cp_PEEK": V(1300.0, "J/kgK", "ASSUMPTION", "handbook (1.3 J/gK)"),
}

# ------------------------------------------------------------------------------------------------ sensors
SENSORS = {
    "hall_noise_tip": V(5e-6, "m rms", "ASSUMPTION", "sim2 default (TMAG5273 110-125 uT rms / 16 mT/mm: MFR OPT-45) at 10 kHz"),
    "hall_rate": V(10000.0, "Hz", "MFR", "OPT-44/OPT-53 (TMAG5170 20 kSPS single axis, 10 kSPS 3 axes)"),
    "page_rate": V(1000.0, "Hz", "LIT", "OPT-01 (DeltaPen: 2 x P3040 at 1 kHz)"),
    "page_latency": V(2e-3, "s", "ASSUMPTION", "not reported by DeltaPen (OPT-01: 'comparable to a tethered mouse')"),
    "page_err_window_median": V(23.6e-6, "m", "LIT", "OPT-02 (DeltaPen Sec. 4.4: translation-magnitude error per 10 ms window, "
                                                     "median 0.0236 mm; opened again in this study)"),
    "page_err_window_mean": V(68.3e-6, "m", "LIT", "OPT-02 (mean 0.0683 mm)"),
    "page_idle_drift": V(0.04375e-3, "m/s", "LIT", "OPT-02 (idle drift per axis)"),
    "page_mdape_writing": V((0.010, 0.014), "-", "LIT", "OPT-75 (DeltaPen Fig. 7, X / Y MdAPE at 2.5-5 cm/s, read from the bar chart)"),
    "page_ideal_noise": V(3e-6, "m rms", "ASSUMPTION", "the earlier studies' ideal page sensor: kept only as a labelled bound"),
    "page_lift_max": V(2e-3, "m", "MFR", "OPT-54 (PMW3360 with the LM19-LSI lens: lift cut-off 2-3 mm; the lower bound, as "
                                        "Rev J's revj/simparams.py); sim2's default 0.8 mm was used in a first run by mistake"),
    "imu": V("LSM6DSV16X class", "-", "MFR", "OPT-37 (60 ug/sqrt(Hz), 2.8 mdps/sqrt(Hz))"),
    "tilt_err_sd": V(1.0 * D2R, "rad", "ASSUMPTION", "IMU gravity-direction error while writing (tremor accelerations averaged "
                                                   "over 0.2 s); OPT-19 gives the drift scale; to measure in EXP-B28"),
    "roll_err_sd": V(2.0 * D2R, "rad", "ASSUMPTION", "roll about the pen axis from gravity: ill-conditioned near 90 deg tilt; "
                                                   "2 deg at 35-75 deg"),
}

# ------------------------------------------------------------------------------------------------ slow positioners
POSITIONER = {
    "squiggle_stall_N": V(0.30, "N", "MFR", "AMF-15 / AMF-106 (New Scale SQL-RV-1.8: 0.3-0.33 N stall at 3.3 V)"),
    "squiggle_speed": V(7e-3, "m/s", "MFR", "AMF-106 (> 7 mm/s at 15 gf)"),
    "squiggle_power_moving": V(0.34, "W", "MFR", "AMF-106 (< 340 mW moving)"),
    "squiggle_hold_W": V(0.0, "W", "MFR", "AMF-15 (off-power hold, 0 mW)"),
    "squiggle_mass": V(0.16e-3, "kg", "MFR", "AMF-106"),
    "squiggle_size": V((2.8e-3, 2.8e-3, 6e-3), "m", "MFR", "AMF-106"),
    "squiggle_travel": V(6e-3, "m", "MFR", "AMF-15"),
    "squiggle_life": V(1.0e6, "cycles", "MFR", "AMF-15 (> 1 M cycles at 15 g, 7 mm/s)"),
    "squiggle_supply": V("sold only to qualified customers with significant order quantities", "-", "MFR",
                         "AMF-15 (a supply risk for a prototype: the micro-stepper leadscrew is the fallback)"),
}

# ------------------------------------------------------------------------------------------------ piezo benders (PICMA)
PIEZO = {
    "PL128": {"free_um": V(450.0, "um", "MFR", "AMF-11 (PL128.10: +-450 um, +-0.55 N, 36 x 6.15 x 0.67 mm, 2 x 1.2 uF, 360 Hz)"),
              "F_block": V(0.55, "N", "MFR", "AMF-11"), "L": V(36e-3, "m", "MFR", "AMF-11"), "w": V(6.15e-3, "m", "MFR", "AMF-11"),
              "t": V(0.67e-3, "m", "MFR", "AMF-11"), "C_half": V(1.2e-6, "F", "MFR", "AMF-11"), "f_res": V(360.0, "Hz", "MFR", "AMF-11"),
              "V_range": V((-30.0, 30.0), "V", "MFR", "AMF-11 (0-60 V, +-30 V differential)"),
              "L_free": V(28e-3, "m", "MFR", "AMF-53 (remaining free length LF 28 mm)"), "tol": V(0.20, "-", "MFR", "AMF-11 (+-20 %)"),
              "T_max": V(150.0, "degC", "MFR", "AMF-53 (PIC252)")},
    "PL127": {"free_um": V(450.0, "um", "MFR", "AMF-11 (PL127.10: +-450 um, +-1.1 N, 31 x 9.60 x 0.67 mm, 2 x 3.4 uF, 420 Hz)"),
              "F_block": V(1.1, "N", "MFR", "AMF-11"), "L": V(31e-3, "m", "MFR", "AMF-11"), "w": V(9.6e-3, "m", "MFR", "AMF-11"),
              "t": V(0.67e-3, "m", "MFR", "AMF-11"), "C_half": V(3.4e-6, "F", "MFR", "AMF-11"), "f_res": V(420.0, "Hz", "MFR", "AMF-11"),
              "V_range": V((-30.0, 30.0), "V", "MFR", "AMF-11"), "L_free": V(27e-3, "m", "MFR", "AMF-53"),
              "tol": V(0.20, "-", "MFR", "AMF-11"), "T_max": V(85.0, "degC", "MFR", "AMF-53 (PIC251)")},
    "eta_rec": V(0.85, "-", "ASSUMPTION", "charge-recovery driver efficiency per direction (docs/opt_hardware.md A7; EXP-Q05): "
                                          "P_rail = (1/eta - eta) V_mean C_axis V_pp f per axis (opt/hardware/model.py convention)"),
    "eta_boost": V(0.80, "-", "ASSUMPTION", "60 V boost efficiency (docs/opt_hardware.md A7)"),
    "V_mean": V(30.0, "V", "MFR", "AMF-11 (0-60 V parallel drive: the middle electrode swings about 30 V)"),
    "boost_Iq_W": V(0.002, "W", "ASSUMPTION", "boost + bridge quiescent incl. leakage hold (LT8365 Burst Iq 9 uA: AMF-58)"),
}

# ------------------------------------------------------------------------------------------------ grip classes
GRIP = {
    "pen24": {"od": V(24e-3, "m", "ASSUMPTION", "DEC-029 (the user chose a bigger grip); Rev J envelope 24 mm"),
              "wall": V(1.0e-3, "m", "ASSUMPTION", "Rev H/J shell wall"), "length_max": V(175e-3, "m", "ASSUMPTION", "Rev J envelope"),
              "mass_max": V(120e-3, "kg", "ASSUMPTION", "Rev J envelope"), "base_mass": V(62e-3, "kg", "CALC",
              "Rev J.1 base pen 84.3 g minus its C1S nose parts 18.2 g plus the fixed parts it keeps (CALC in candidates.py)")},
    "slim": {"od": V((12e-3, 16e-3), "m", "ASSUMPTION", "review section 6 trade-study target (not a requirement)"),
             "wall": V(0.8e-3, "m", "ASSUMPTION", "slim barrel wall"), "length_max": V(160e-3, "m", "ASSUMPTION", "slim target"),
             "mass_target": V((25e-3, 40e-3), "kg", "ASSUMPTION", "review section 6 (25-40 g)")},
}

# ------------------------------------------------------------------------------------------------ tasks
TASKS = {
    "travel_fine": V((0.5e-3, 1.0e-3), "m", "LIT", "review section 6: initially +-0.5 to 1 mm usable correction (fine core)"),
    "tremor_classes": V({"mild": (0.3, 1.0), "moderate": (2.0, 4.0), "severe": (5.0, 10.0)}, "mm peak", "ASSUMPTION",
                        "docs/round4_plan.md section 6"),
    "tremor_freq": V((4.0, 12.0), "Hz", "ASSUMPTION", "docs/round4_plan.md section 6; review G3 1-30 Hz"),
    "tremor_duty_rms": V(1.0e-3, "m rms", "ASSUMPTION", "Rev H / study N design duty (1 mm rms per axis at 8 Hz)"),
    "writing_speed": V(30.5e-3, "m/s", "LIT", "CON-20 (adult phrase on paper, mean)"),
    "pen_up_share": V(0.30, "-", "ASSUMPTION", "review section 4 (70 % contact duty)"),
    "lifts_per_s": V(4.2, "1/s", "CALC", "study N planner (results/nose2/nose2.json axial_dof)"),
}
