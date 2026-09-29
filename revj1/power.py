r"""P2: battery life with assistance on, per mode (CALC on datasheet figures and the round-1 SIM/CALC loads).

What changes against Rev J (revj/budgets.power_modes, whose loads are reused where nothing changed):
  electronics  rebuilt bottom-up from datasheets instead of Rev H's 77 mW ASSUMPTION: the nRF54L15's CPU, radio and
               peripheral currents (MFR OPT-60) with duty cycles (ASSUMPTION), the IMU (OPT-37), the two DRV5055 nose Hall
               sensors (OPT-46: 2 mA typ, 4 mA max each), the two DRV8214 coil drivers (AMF-37 re-read: 1.3 / 1.9 mA
               active), the charger and regulators (ASSUMPTION)
  page sensor  per mode, with three options: PMW3360 always on at 1 kHz (Rev J), PMW3360 gated by an IMU pre-detector,
               or a low-power PMW3610-class die (MFR OPT-61: 0.60 mA run at 1.8 V) always on.  DEC-042's tremor-line
               detector runs on the page sensor, so the steady mode may NOT simply switch it off (Rev J's assumption).
  heel         steady mode: the wheel free-follows with its drivers asleep (ASSUMPTION); other modes as Rev J
  nose coils   study N's duty model (revj.budgets) with the Rev J.1 gimbal stiffness (revj1.gimbal) and the copper's
               temperature (the spreader of revj1.thermal lowers it), times a SENSITIVITY factor 1 / 2 / 5 (the sim2j
               closed loop reported 1.3-2.4 W in some tremor runs; unconfirmed)
  end-cap      the Rev J.1 member (revj1.endcap_mass): SIM actuation power on the test runs (drivers included) to the
               design model's average; only while a tremor line is detected (DEC-038 proposal)
  cells        LIR14500 (AMF-80), a 14650 (AMF-156), 16 mm cells and a custom D-shaped pouch (geometry CALC)
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

from . import ensure_paths
from . import params as P1

ensure_paths()
from revj import params as PA  # noqa: E402
from revj import budgets as RBU  # noqa: E402


def _lohi(v):
    return v.value if isinstance(v.value, (tuple, list)) else (v.value, v.value)


# --------------------------------------------------------------------------------------------------- electronics
def electronics() -> Dict:
    """Base electronics while writing (W, low / high), bottom-up (CALC on MFR figures, duty cycles ASSUMPTION)."""
    n = P1.NRF
    cpu = [d * n["cpu_coremark_128MHz_mA"].value for d in _lohi(P1.DUTY["cpu"])]
    rad = [d * 0.5 * (n["radio_tx_0dBm_mA"].value + n["radio_rx_2M_mA"].value) for d in _lohi(P1.DUTY["radio"])]
    per = list(_lohi(P1.DUTY["periph_mA"]))
    eff = P1.DUTY["reg_eff"].value
    vdd = n["vdd_V"].value
    soc = [(cpu[i] + rad[i] + per[i]) * 1e-3 * vdd / eff for i in (0, 1)]
    imu = P1.SENSORS["imu_mA"].value * 1e-3 * 1.8 / eff
    hall = [2 * i * 1e-3 * PA.POWER["cell_V"].value for i in _lohi(P1.SENSORS["nose_hall_mA_each"])]    # LDO from the cell
    drv = [2 * i * 1e-3 * PA.POWER["cell_V"].value for i in _lohi(P1.SENSORS["coil_driver_mA_each"])]  # VM = cell
    misc = list(_lohi(P1.SENSORS["misc_W"]))
    tot = [soc[i] + imu + hall[i] + drv[i] + misc[i] for i in (0, 1)]
    return {"soc_W": soc, "imu_W": imu, "nose_halls_W": hall, "coil_drivers_W": drv, "misc_W": misc, "total_W": tot,
            "revJ_W": PA.POWER["base_W"].value + PA.POWER["nose_drivers_hall_W"].value,
            "label": "CALC (nRF54L15 MFR OPT-60, LSM6DSV16X OPT-37, DRV5055 OPT-46, DRV8214 AMF-37; duty cycles and "
                     "regulator efficiency ASSUMPTION)"}


# --------------------------------------------------------------------------------------------------- page sensor
def page_options() -> Dict:
    """Page-sensor power (W, low / high) for the three options (CALC on MFR figures)."""
    eff = P1.DUTY["reg_eff"].value
    lo360 = P1.PAGE["pmw3360_mA"].value[0] * 1e-3 * 1.9 / 0.9
    hi360 = P1.PAGE["pmw3360_mA"].value[1] * 1e-3 * 3.7
    p3610 = P1.PAGE["pmw3610_run_mA"].value * 1e-3 * P1.PAGE["pmw3610_V"].value / eff
    return {"PMW3360_1kHz": [lo360, hi360],
            "PMW3360_gated": [0.1 * lo360, 0.3 * hi360],
            "PMW3610_class": [p3610, p3610 * 1.5],
            "notes": {"PMW3360_gated": "steady mode: on only while an IMU pre-detector sees a candidate tremor line, for the 20 s "
                                       "calibration and for confirmation windows (duty 10-30 %, ASSUMPTION); needs EXP-L01 to "
                                       "show the IMU pre-detector misses no tremor line the page detector finds",
                      "PMW3610_class": "0.60 mA typ at 1.8 V (MFR OPT-61), x1.5 for its polling and the regulator (ASSUMPTION); "
                                       "3200 cpi (7.9 um counts), 24-30 in/s, 10 g: enough for the detector, slip and capture; "
                                       "whether it gives autowrite's 1 kHz / 2 ms / 10 um on paper is unknown (EXP-J10)"},
            "label": "CALC (MFR AMF-109, OPT-61; gating duty ASSUMPTION)"}


NEEDS = {   # what each mode needs from the page sensor (sources: DEC-042, docs/ai_control_v2.md, docs/nose_v2.md, study D)
    "steady": "tremor-line detector (Welch spectrum of the last 4 s every 50 ms on a 250 Hz grid, 4.5-13.5 Hz band, amplitude "
              "gate 0.15-0.35 mm); the listening smoother (the IMU carries the estimate: 421 vs 412 um with the page sensor, SIM "
              "ai2 s4.7); the ink log for the app",
    "guide": "handle position on the page for the template (>= 120 Hz, <= 10 ms: CHECKPOINT s7), heel slip",
    "lead": "position and heel slip (study D), >= 120 Hz",
    "autowrite": "1 kHz, <= 2 ms, <= 10 um (DEC-036, REQ-RVJ-N06; 120 Hz doubles the ink error, SIM study N)",
}


# --------------------------------------------------------------------------------------------------- nose coils
def nose_coil_W(tremor_mm: float, k_tip_N_m: float, travel_factor: float, F_grav_tip_N: float, T_coil_C: float = 20.0) -> float:
    """Study N's duty model (revj.budgets.nose_coil_power) with a different suspension stiffness and the copper at
    T_coil (CALC).  The model's Km uses copper at 20 degC."""
    nd = PA.nose_design()
    base = RBU.nose_coil_power(tremor_mm, travel_factor, F_grav_tip_N)
    x = tremor_mm * 1e-3
    dF2 = (k_tip_N_m ** 2 - nd["k_tip_N_m"] ** 2) * x * x
    P = base["P_W"] + 2.0 * dF2 / nd["Km_tip"] ** 2 * travel_factor
    return P * (1.0 + P1.CU_ALPHA.value * (T_coil_C - 20.0))


def autowrite_coil_W(sim_W: float, k_tip_N_m: float, T_coil_C: float = 20.0) -> float:
    """Study N's SIM autowrite coil loss plus the stiffer gimbal on the planner's 1.5 mm rms excursion (CALC)."""
    nd = PA.nose_design()
    q = 1.5e-3                                              # nose2 Duty.aw_q_rms (per axis)
    dP = 2.0 * (k_tip_N_m ** 2 - nd["k_tip_N_m"] ** 2) * q * q / nd["Km_tip"] ** 2
    return (sim_W + dP) * (1.0 + P1.CU_ALPHA.value * (T_coil_C - 20.0))


# --------------------------------------------------------------------------------------------------- modes
def modes(k_tip_N_m: float, travel_factor: float, F_grav_tip_N: float, T_coil: Dict[str, float],
          page_choice: str = "PMW3610_class", endcap_W: Sequence[float] = (0.0, 0.0), factor: float = 1.0) -> Dict:
    """Mean power per mode (W, low / high) for the Rev J.1 pen (CALC).  T_coil: coil temperature per mode (degC)."""
    el = electronics()["total_W"]
    pg = page_options()
    page = pg[page_choice]
    page_full = pg["PMW3610_class"] if page_choice == "PMW3610_class" else pg["PMW3360_1kHz"]
    slide = list(_lohi(P1.SENSORS["slide_hall_W"]))
    drv = list(_lohi(PA.HEEL["P_drivers_W"]))
    brake = 0.006 * 2.0                                     # Rev J ASSUMPTION: 6 mJ per lift, 2 lifts/s
    lift_aw = PA.NOSE["pen_lift_W"].value
    lead = PA.HEEL["P_lead_W"].value / PA.HEEL["mesh_eff"].value
    rows = {}

    def coil(t, key):
        return factor * nose_coil_W(t, k_tip_N_m, travel_factor, F_grav_tip_N, T_coil.get(key, 20.0))

    def aw(sim, key):
        return factor * autowrite_coil_W(sim, k_tip_N_m, T_coil.get(key, 20.0))
    spec = {
        "steady_no_tremor": (coil(0.0, "steady_no_tremor"), (0.0, 0.002), brake, page),
        "steady_0.3mm": (coil(0.3, "steady_0.3mm"), (0.0, 0.002), brake, page),
        "steady_1mm": (coil(1.0, "steady_1mm"), (0.0, 0.002), brake, page),
        "guide": (coil(0.3, "guide"), (PA.HEEL["P_steer_only_W"].value + drv[0], PA.HEEL["P_guide_W"].value + drv[1]), brake, page_full),
        "lead": (aw(0.089, "lead"), (lead + drv[0], lead + drv[1]), brake, page_full),
        "autowrite_no_tremor": (aw(0.089, "autowrite_no_tremor"), (0.001 + drv[0], 0.001 + drv[1]), lift_aw, page_full),
        "autowrite_1mm": (aw(0.166, "autowrite_1mm"), (0.001 + drv[0], 0.001 + drv[1]), lift_aw, page_full),
        "autowrite_2mm": (aw(0.376, "autowrite_2mm"), (0.001 + drv[0], 0.001 + drv[1]), lift_aw, page_full),
    }
    for k, (Pc, heel, lift, pgw) in spec.items():
        lo = el[0] + pgw[0] + slide[0] + Pc + heel[0] + lift
        hi = el[1] + pgw[1] + slide[1] + Pc + heel[1] + lift
        ec = (endcap_W[0], endcap_W[1]) if k.startswith("steady") and k != "steady_no_tremor" else (0.0, 0.0)
        rows[k] = {"nose_coil_W": Pc, "heel_W": list(heel), "pen_lift_W": lift, "electronics_W": list(el), "page_W": list(pgw),
                   "slide_hall_W": slide, "total_W": [lo, hi], "endcap_W_if_fitted": list(ec),
                   "total_with_endcap_W": [lo + ec[0], hi + ec[1]]}
    return rows


def hours(rows: Dict, E_Wh: float) -> Dict:
    return {k: {"h": [E_Wh / r["total_W"][1], E_Wh / r["total_W"][0]],
                "h_with_endcap": [E_Wh / r["total_with_endcap_W"][1], E_Wh / r["total_with_endcap_W"][0]]} for k, r in rows.items()}


def cells() -> Dict:
    """Cell options in the Rev J handle (CALC on MFR data; bore 22 mm, two 6 mm motors under the cell)."""
    V = P1.CELLS["V_nom"].value
    u = P1.CELLS["usable"].value
    out = {}
    for name in ("LIR14500", "ICR14650"):
        c = P1.CELLS[name]
        E = c["mAh"].value * 1e-3 * V * u
        out[name] = {"E_usable_Wh": E, "d_mm": c["d_mm"].value, "l_mm": c["l_mm"].value, "mass_g": c["g"].value,
                     "extra_length_mm": c["l_mm"].value - P1.CELLS["LIR14500"]["l_mm"].value,
                     "extra_mass_g": c["g"].value - P1.CELLS["LIR14500"]["g"].value,
                     "Wh_per_L": c["mAh"].value * 1e-3 * V / (math.pi / 4 * c["d_mm"].value ** 2 * c["l_mm"].value * 1e-6)}
    # a 16 mm cell beside two 6 mm motors in the 22 mm bore: the motors' centres at (x_m, +-3.5) need
    # |c_m| + 3 <= 11 and |c_m - c_cell| >= 8 + 3 with the cell touching the bore top (centre 3 mm up): infeasible
    y = 3.5
    x_bore = -math.sqrt(max((11 - 3) ** 2 - y ** 2, 0.0))                  # lowest motor centre inside the bore
    x_cell = 3.0 - math.sqrt((8 + 3) ** 2 - y ** 2)                        # highest motor centre clear of the cell
    out["16mm_beside_motors"] = {"feasible": x_cell >= x_bore, "motor_centre_must_be_below_mm": x_cell,
                                 "bore_allows_down_to_mm": x_bore, "label": "CALC (geometry)"}
    out["16mm_motors_behind"] = {"pen_length_base_mm": 92.7 + 65.0 + 0.5 + 20.2 + 3.0,
                                 "note": "a 16 x 65 mm cell with the motors behind it: the base pen exceeds 175 mm (CALC, "
                                         "Rev J stack: actuator to z 92.2 + 0.5 mm, cell, motors 20 mm, rear cap 3 mm)"}
    lp = P1.CELLS["pouch_LP503562"]
    wh_l = lp["mAh"].value * 1e-3 * 3.75 / (lp["vol_cm3"].value * 1e-3)
    seg = 284.0                                                             # mm^2 of the 22 mm bore above the motors (CALC)
    usable_area = 0.75 * seg                                                # pouch margins and radii (ASSUMPTION)
    out["custom_D_pouch"] = {"energy_density_Wh_per_L_ref": wh_l, "section_mm2": usable_area,
                             "E_usable_Wh_same_length_48mm": wh_l * usable_area * 48.5e-6 * u,
                             "note": "a custom D-shaped pouch over the motors: about 1.4 x the round cell's section; energy "
                                     "density from a catalogue pouch (MFR AMF-157), no catalogue part in this shape"}
    return out


def targets_proposal() -> Dict:
    return {"REQ-RVJ-I01 (revised)": "Battery, continuous writing on the LIR14500 at 23 degC: >= 8 h in the steady modes up to "
                                     "1 mm rms tremor and in guide; with the end-cap fitted and active while tremor is detected, "
                                     ">= 8 h at the end-cap's measured duty and >= 6 h at its design power; >= 7.5 h in "
                                     "lead-through; >= 6 h in autowrite up to 1 mm tremor; autowrite with 2 mm tremor is for "
                                     "short texts (>= 3.5 h). The page sensor stays on in every mode (DEC-042's detector). "
                                     "As adopted in DEC-045 and docs/revJ1_design.md s4.7.",
            "REQ-DRV-009": "keep the heel drive's own <= 0.15 W; the pen-level hours move to REQ-RVJ-I01",
            "REQ-EC-008": "fold into REQ-RVJ-I01's end-cap clause (>= 8 h at the end-cap's measured duty, >= 6 h at its "
                          "design power)",
            "label": "PROPOSED (reconciles REQ-DRV-009, REQ-EC-008 and REQ-RVJ-I01; the lead edits requirements.csv)"}
