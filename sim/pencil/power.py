r"""Piezo drive power, driver topologies and battery life for the pencil (shared by
analysis/pencil_mechanisms.py and sim/pencil/run_study.py).

Charge bookkeeping for a capacitive actuator driven on one node (the bender centre
electrode; the outer electrodes sit at 0 V and V_rail):
  * switch-to-rail or class-B linear stage: the rail supplies V_rail * i whenever the
    capacitor charges (i > 0) and nothing is returned when it discharges, so
    P_rail = V_rail * <max(i, 0)>  (a sinusoid gives f * C * V_pp * V_rail);
  * charge-recovery (bidirectional buck/boost, CapDrive class): the rail supplies
    p/eta_c when p = V i > 0 and receives eta_c * |p| when p < 0.
The battery supplies the rail through a boost converter of efficiency eta_boost, plus
the quiescent power of the driver chips.
Evidence status: CALCULATION; driver numbers are MANUFACTURER STATEMENTS (AMF-16;
proposed AMF-46, AMF-47) or ASSUMPTIONS as labelled in DRIVERS.
"""
from __future__ import annotations

import math

import numpy as np

V_BAT = 3.7                       # V, Li-ion nominal (config/pencil.yaml battery.v_nom)

# DRV2700 quiescent current vs boost voltage (AMF-16): 5 mA @30 V, 9 mA @55 V, 13 mA @80 V, 24 mA @105 V
_DRV2700_IQ = ((30.0, 5e-3), (55.0, 9e-3), (80.0, 13e-3), (105.0, 24e-3))


def drv2700_iq(v_boost):
    v = [a for a, _ in _DRV2700_IQ]
    i = [b for _, b in _DRV2700_IQ]
    return float(np.interp(v_boost, v, i))


DRIVERS = {
    "drv2700": {
        "label": "2 x TI DRV2700 (integrated boost + linear amplifier), boost at the rail voltage",
        "V_rail": 60.0, "channels": 2, "recovery": False,
        "P_quiescent_W": 2 * drv2700_iq(60.0) * V_BAT,
        "P_shutdown_W": 2 * 13e-6 * V_BAT,
        "eta_boost": 0.75,
        "labels": {"Iq": "MANUFACTURER STATEMENT (AMF-16: 9 mA at 55 V, 13 mA at 80 V; 9.8 mA at 60 V by interpolation)",
                   "shutdown": "MANUFACTURER STATEMENT (AMF-16: 13 uA)",
                   "eta_boost": "ASSUMPTION (integrated boost at 10-100 mW; EXP-Q05 measures)"},
        "availability": "off the shelf (EVM available); prototype driver",
    },
    "recovery": {
        "label": "shared low-Iq 60 V boost (LT8330 class) + 2 discrete charge-recovery half-bridge stages (MCU-controlled)",
        "V_rail": 55.0, "channels": 2, "recovery": True,
        "P_quiescent_W": 6e-6 * V_BAT + 2 * 0.5e-3,
        "P_shutdown_W": 0.9e-6 * V_BAT,
        "eta_boost": 0.80, "eta_c": 0.85,
        "labels": {"Iq": "MANUFACTURER STATEMENT (proposed AMF-47: LT8330 Iq 6 uA Burst Mode, 60 V switch, 3-40 V in) + "
                         "ASSUMPTION 0.5 mW per half-bridge stage (gate drive and control at 20-50 kHz burst)",
                   "V_rail": "CALCULATION: 55 V keeps 5 V below the LT8330 60 V switch rating; stroke and force x 55/60",
                   "eta_boost": "ASSUMPTION (EXP-Q05)", "eta_c": "ASSUMPTION per transfer direction (EXP-Q05)"},
        "availability": "custom power stage from catalogue parts (make)",
    },
    "capdrive": {
        "label": "2 x Boreas BOS1931-class CapDrive (integrated boost, energy recovery)",
        "V_rail": 60.0, "channels": 2, "recovery": True,
        "P_quiescent_W": 2 * 3.7e-3 * 3.6,
        "P_shutdown_W": 2 * 0.6e-6 * 3.6,
        "eta_boost": 0.80, "eta_c": 0.85,
        "labels": {"Iq": "MANUFACTURER STATEMENT (proposed AMF-46: 3.7 mA average at DC output, 95 V on 100 nF; IDLE 530 uA; SLEEP 0.6 uA)",
                   "limit": "MANUFACTURER STATEMENT (proposed AMF-46): load <= 820 nF at 100 Vpp/130 Hz; our 2.0-2.6 uF per axis is outside the rating",
                   "eta": "ASSUMPTION"},
        "availability": "catalogue part, but the bender capacitance exceeds its rated load (needs vendor qualification)",
    },
}


def rail_flow(V, i, dt, V_rail, recovery=False, eta_c=0.85):
    """Mean power drawn from the rail (W) for voltage and current samples of one channel."""
    V = np.asarray(V, float)
    i = np.asarray(i, float)
    if not recovery:
        return float(V_rail * np.mean(np.maximum(i, 0.0)))
    p = V * i
    flow = np.where(p > 0, p / eta_c, eta_c * p)
    return float(max(np.mean(flow), 0.0))


def sine_drive(C, V_a, f, V_rail, recovery=False, eta_c=0.85, V_mid=None, n=2000):
    """Per-channel powers for V = V_mid + V_a sin(wt) on capacitance C.
    Returns reactive VA, rail power (W)."""
    V_mid = V_rail / 2.0 if V_mid is None else V_mid
    w = 2 * math.pi * f
    t = np.linspace(0.0, 1.0 / f, n, endpoint=False)
    V = V_mid + V_a * np.sin(w * t)
    i = C * V_a * w * np.cos(w * t)
    return {"reactive_VA": 0.5 * C * w * V_a ** 2, "i_peak_A": C * V_a * w,
            "P_rail_W": rail_flow(V, i, t[1] - t[0], V_rail, recovery, eta_c)}


def battery_power(driver_key, P_rail_total, active=True):
    d = DRIVERS[driver_key]
    if not active:
        return d["P_shutdown_W"]
    return d["P_quiescent_W"] + P_rail_total / d["eta_boost"]


def battery_life_h(P_total, capacity_mAh=90.0, v_nom=V_BAT, usable=0.8):
    return capacity_mAh * 1e-3 * v_nom * usable / max(P_total, 1e-12)
