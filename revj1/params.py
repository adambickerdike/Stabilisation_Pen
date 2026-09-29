"""Inputs of Rev J.1 that are new or changed against Rev J (revj/params.py stays the source of everything else).

Every value: V(value, unit, label, source).  Labels: MFR / LIT (ledger id; the ids AMF-155.., OPT-60.., HAP-110..,
CON-70.. are proposed in results/revJ1/evidence_rows.csv for sources opened in this study), CALC (this package),
SIM (an executed simulation, file named), ASSUMPTION, PROPOSED DESIGN.
"""
from __future__ import annotations

from typing import Dict

from . import ensure_paths

ensure_paths()
from revj.params import V  # noqa: E402  (same record type as Rev J)

# ----------------------------------------------------------------------------------------------- electronics (MFR figures)
NRF = {   # Nordic nRF54L15 Preliminary Datasheet v0.10 (4503_018), s11.1.2, VDD 3.0 V, DC/DC, 25 degC
    "cpu_coremark_128MHz_mA": V(2.6, "mA", "MFR", "OPT-60 (IAPPCPU0: CoreMark at 128 MHz from NVM, cache enabled)"),
    "radio_tx_0dBm_mA": V(4.8, "mA", "MFR", "OPT-60 (IRADIO_TX0)"),
    "radio_rx_2M_mA": V(3.6, "mA", "MFR", "OPT-60 (IRADIO_RX1, 2 Mbps)"),
    "timer_128MHz_uA": V(450.0, "uA", "MFR", "OPT-60 (ITIMER0, TIMER00 at 128 MHz)"),
    "saadc_2Msps_mA": V(1.4, "mA", "MFR", "OPT-60 (ISAADC0)"),
    "idle_uA": V(3.1, "uA", "MFR", "OPT-60 (ION_IDLE8, System ON, GRTC, LFXO, 256 KB retained)"),
    "vdd_V": V(3.0, "V", "MFR", "OPT-60 (common conditions of the current tables)"),
}
DUTY = {  # duty cycles of the SoC while writing (ASSUMPTION; the TCN alone is 28 % of the core at 500 Hz, DEC-042 CALC)
    "cpu": V((0.5, 0.8), "-", "ASSUMPTION", "2 kHz control loop, lag-0 Kalman, detector every 50 ms, TCN in shadow (28 %, "
                                            "docs/ai_control_v2.md s5), servo and heel loops"),
    "radio": V((0.03, 0.10), "-", "ASSUMPTION", "BLE link to the phone for the ink log (a few kB/s on the 2 Mbps PHY)"),
    "periph_mA": V((0.8, 1.5), "mA", "ASSUMPTION", "HFXO, TIMER00 (0.45 mA, MFR OPT-60), SAADC at low duty, SPI/TWIM"),
    "reg_eff": V(0.85, "-", "ASSUMPTION", "cell to the SoC's 3.0 V rail"),
}
SENSORS = {
    "imu_mA": V(0.65, "mA", "MFR", "OPT-37 (LSM6DSV16X accelerometer + gyroscope, high-performance) at 1.8 V"),
    "nose_hall_mA_each": V((2.0, 4.0), "mA", "MFR", "OPT-46 (DRV5055 ICC 2 mA typ, 4 max at 3.3 V; revised June 2026 sheet re-read)"),
    "coil_driver_mA_each": V((1.3, 1.9), "mA", "MFR", "AMF-37 re-read: DRV8214 IVM active 1.3 typ / 1.9 max mA (SLVSH04, VM > VCC)"),
    "misc_W": V((0.0005, 0.001), "W", "ASSUMPTION", "charger, fuel gauge and regulator quiescent currents"),
    "slide_hall_W": V((0.004, 0.008), "W", "ASSUMPTION", "Rev J value: TMAG5273 class (2.3 mA active, MFR OPT-45) duty-cycled"),
}
PAGE = {
    "pmw3610_run_mA": V(0.60, "mA", "MFR", "OPT-61 (PMW3610DM-SUDU IDD_RUN typ, VDD 1.8 V, incl. laser)"),
    "pmw3610_V": V(1.8, "V", "MFR", "OPT-61"),
    "pmw3610_cpi": V(3200, "cpi", "MFR", "OPT-61 (up to 3200 cpi in 200 cpi steps)"),
    "pmw3610_speed_ips": V((24, 30), "in/s", "MFR", "OPT-61 (typ / max with certain surfaces)"),
    "pmw3610_accel_g": V(10, "g", "MFR", "OPT-61"),
    "pmw3610_z_mm": V((2.2, 2.4, 2.6), "mm", "MFR", "OPT-61 (lens reference plane to surface, +-0.2 mm DOF)"),
    "pmw3360_mA": V((16.3, 21.6), "mA", "MFR", "AMF-109 (run current with 1 ms polling)"),
    "pmw3360_V": V((1.9, 3.7), "V", "ASSUMPTION", "Rev J: a 1.9 V buck (90 %) to the raw cell voltage (linear)"),
}
CELLS = {
    "LIR14500": {"mAh": V(750.0, "mAh", "MFR", "AMF-80"), "d_mm": V(14.1, "mm", "MFR", "AMF-80"),
                 "l_mm": V(48.5, "mm", "MFR", "AMF-80"), "g": V(20.0, "g", "MFR", "AMF-80 (about 20 g)")},
    "ICR14650": {"mAh": V(1100.0, "mAh", "MFR", "AMF-156 (KeepPower 14650: 1100 mAh minimum, 1130 typical)"),
                 "d_mm": V(14.5, "mm", "MFR", "AMF-156 (14.5 -0.7 mm)"), "l_mm": V(65.3, "mm", "MFR", "AMF-156 (65.3 -0.6 mm)"),
                 "g": V(27.0, "g", "MFR", "AMF-156 (about 27 g)")},
    "pouch_LP503562": {"mAh": V(1200.0, "mAh", "MFR", "AMF-157 (LP503562, 5.2 x 35.5 x 62.2 mm): energy density reference only"),
                       "vol_cm3": V(11.48, "cm3", "CALC", "AMF-157 dimensions"), "g": V(24.0, "g", "MFR", "AMF-157 (about 24 g)")},
    "V_nom": V(3.7, "V", "MFR", "AMF-80 / AMF-156"),
    "usable": V(0.8, "-", "ASSUMPTION", "Rev J: 80 % of the rated energy usable"),
}

# ----------------------------------------------------------------------------------------------- heat
SKIN = {
    "held_max_C": V(43.0, "degC", "LIT", "AMF-35 re-read: ECMA-287 Table 5.2, continuously held, all materials, 43 degC (from EN "
                                          "563; continuous holding assumed below 8 h)"),
    "design_target_C": V(41.0, "degC", "LIT", "AMF-34 (IEC 60601-1: no justification needed at or below 41 degC)"),
    "rated_room_C": V(30.0, "degC", "PROPOSED DESIGN", "the rated maximum room temperature (ECMA-287 B.5 lets the maker set "
                                                       "T_mra; the check is T - T_amb <= T_max - T_mra)"),
}
SPREADERS = {   # in-plane conductivity, density, thickness choices
    "Al_6061": {"k": V(167.0, "W/mK", "ASSUMPTION", "handbook (Rev J value)"), "rho": V(2.70, "g/cm3", "ASSUMPTION", "handbook"),
                "t_mm": (0.2, 0.3, 0.5)},
    "Cu_C110": {"k": V(390.0, "W/mK", "ASSUMPTION", "handbook"), "rho": V(8.9, "g/cm3", "MFR", "AMF-29 (8.89)"), "t_mm": (0.1, 0.2)},
    "PGS_graphite": {"k": V(600.0, "W/mK", "MFR", "AMF-158 (a-b plane 600-800 W/mK; lower end used)"),
                     "rho": V(1.0, "g/cm3", "MFR", "AMF-158 (about 1 g/cm3)"), "t_mm": (0.05, 0.10)},
}
CU_ALPHA = V(0.00393, "1/K", "ASSUMPTION", "copper resistance temperature coefficient (handbook)")

# ----------------------------------------------------------------------------------------------- gimbal (P1 choice)
GIMBAL = {
    "t_um": V(75.0, "um", "PROPOSED DESIGN", "301 full-hard strip, one stock step up from study N's 50 um (revj1/gimbal.py)"),
    "b_mm": V(2.55, "mm", "CALC", "study N"), "L_mm": V(3.80, "mm", "CALC", "study N"), "alpha_deg": V(45.0, "deg", "CALC", "study N"),
    "crossing": V(0.5, "-", "CALC", "study N (crossing at mid-length kept)"),
    "load_path": V("compression (study N's arrangement kept)", "-", "PROPOSED DESIGN", "revj1/gimbal.py: tension fails fatigue"),
}

# ----------------------------------------------------------------------------------------------- nose-coil sensitivity
NOSE_POWER_FACTORS = V((1.0, 2.0, 5.0), "-", "ASSUMPTION",
                       "sensitivity of the nose-coil power: x1 = study N's duty model (CALC) and SIM autowrite values; x2 and x5 "
                       "bracket the unconfirmed sim2j closed-loop report of 1.3-2.4 W in some tremor runs (lead note, 2026-09-29)")


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


def all_tables() -> Dict:
    return {"nrf54l15": table(NRF), "duty": table(DUTY), "sensors": table(SENSORS), "page_sensor": table(PAGE),
            "cells": table(CELLS), "skin": table(SKIN), "spreaders": table(SPREADERS), "cu_alpha": CU_ALPHA.d(),
            "gimbal": table(GIMBAL), "nose_power_factors": NOSE_POWER_FACTORS.d()}
