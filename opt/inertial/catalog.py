"""Parts catalogue (verified datasheet values with ledger ids) and envelope tiers for the inertial / pen-movement study.

Every entry carries `src` (ledger id in docs/evidence.csv, or a new row proposed in
results/opt/inertial_evidence_rows.csv) and `label`: MFR (manufacturer statement), LITERATURE, CALC or ASSUMPTION.
Values were read from the documents named in the ledger rows on 2026-09-28; nothing here was measured.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

G0 = 9.80665
RHO_WHA = 18.0e3      # MFR AMF-49 (ASTM B777 class 3, ET95NM non-magnetic grade available)
RHO_BRASS = 8.5e3     # ASSUMPTION (CuZn39Pb3 free-cutting brass, typical handbook value; not ledgered)
RHO_BECU = 8.36e3     # MFR AMF-18 (C17200 aged)
E_BECU = 131e9        # MFR AMF-18
FATIGUE_BECU = 276e6  # MFR AMF-19 (TH01, 1e8 cycles)
E_SS301 = 200e9       # MFR AMF-20 (301 full hard)
FATIGUE_SS301 = 540e6  # MFR AMF-20
RHO_PEEK = 1.30e3     # MFR AMF-24
RHO_AL = 2.70e3       # ASSUMPTION (6061 handbook)
RHO_CU = 8.89e3       # MFR AMF-29
RES_CU = 1.7241e-8    # MFR AMF-29 (20 degC)
BR_N45 = 1.33         # MFR AMF-28 (N45 13.3-13.7 kG, low end)


# ============================================================================== voice-coil actuators (linear, axial)
@dataclass
class VCA:
    name: str
    od: float           # housing outer diameter (m)
    L_body: float       # housing length (m)
    L_mid: float        # overall length at mid-stroke (m)
    stroke: float       # total stroke (m)
    Kf: float           # force constant (N/A)
    R: float            # coil resistance (ohm)
    L_ind: float        # inductance (H)
    F_cont: float       # continuous force (N)
    F_peak: float       # 10 % duty force (N)
    P_cont: float       # max continuous power (W)
    m_coil: float       # coil assembly (kg)
    m_body: float       # body / magnet assembly (kg)
    src: str
    label: str = "MFR"

    @property
    def Km(self):
        return self.Kf / math.sqrt(self.R)


VCAS: Dict[str, VCA] = {
    "LVCM-010-013-01": VCA("Moticont LVCM-010-013-01", 9.5e-3, 12.7e-3, 20.7e-3, 6.4e-3, 0.29, 1.9, 0.2e-3, 0.28, 0.88, 1.8,
                           2.5e-3, 3.8e-3, "AMF-01"),
    "LVCM-013-013-03": VCA("Moticont LVCM-013-013-03", 12.7e-3, 12.7e-3, 19.0e-3, 3.2e-3, 1.14, 1.9, 0.13e-3, 1.42, 4.48, 3.0,
                           5.4e-3, 7.6e-3, "AMF-02"),
    "LVCM-013-013-01": VCA("Moticont LVCM-013-013-01", 12.7e-3, 12.7e-3, 19.8e-3, 5.0e-3, 0.61, 1.7, 0.28e-3, 0.74, 2.35, 2.5,
                           6.0e-3, 7.0e-3, "AMF-73"),
    "LVCM-016-010-01": VCA("Moticont LVCM-016-010-01 (Rev 1)", 15.9e-3, 9.5e-3, 15.9e-3, 3.2e-3, 1.1, 1.8, 0.2e-3, 1.6, 5.2, 4.0,
                           5.0e-3, 7.0e-3, "AMF-73"),
    "LVCM-016-013-01": VCA("Moticont LVCM-016-013-01", 15.9e-3, 12.7e-3, 20.7e-3, 6.4e-3, 1.4, 2.7, 0.4e-3, 1.8, 5.6, 4.2,
                           7.0e-3, 12.0e-3, "AMF-02/AMF-73"),
    "AVM12-6.4": VCA("Akribis AVM 12-6.4", 12.7e-3, 12.7e-3, 20.4e-3, 6.4e-3, 0.57, 1.13, 0.09e-3, 0.91, 3.53, 2.89,
                     5.0e-3, 7.3e-3, "AMF-03"),
    "NCM01-04-001-2IB": VCA("H2W NCM01-04-001-2IB (moving magnet)", 10.2e-3, 18.7e-3, 18.7e-3, 2.5e-3, 0.56, 2.8, 0.10e-3, 0.45, 1.34,
                            2.0, 1.0e-3, 4.6e-3, "AMF-04"),
}


# ============================================================================== wideband haptic actuators (checked, rejected)
HAPTIC = {
    "Actronika HFBA121238 (Tactile Labs file 'Mark II-D')": dict(dims_mm=(11.5, 12.0, 37.7), m_total=8.7e-3, m_moving=4.4e-3,
                                                                  R=4.5, f_res_loaded=65.0, load=0.100, src="AMF-74", label="MFR"),
    "Alps Alpine AFT14A903A": dict(dims_mm=(9.0, 10.0, 22.6), m_total=5.5e-3, R=8.0, f_res=(160.0, 320.0), src="AMF-75", label="MFR"),
    "Titan Haptics TacHammer Carlton": dict(dims_mm=(14.0, 14.0, 34.0), band_hz=(10.0, 300.0), src="AMF-76", label="MFR (secondary)"),
}


def below_resonance_transmission(f, f_n):
    """Share of the coil force that reaches the housing through a spring-suspended internal mass driven below its
    suspension resonance: (f/f_n)^2 / |1 - (f/f_n)^2| (undamped), CALC."""
    r = (f / f_n) ** 2
    return r / abs(1.0 - r)


# ============================================================================== piezo actuators
@dataclass
class Bender:
    name: str
    L: float; W: float; T: float
    free_len: float
    stroke: float        # free displacement amplitude +/- (m) at full voltage
    F_block: float       # blocking force +/- (N)
    C: float             # capacitance per half (F); bimorph 2 x C
    f_res: float
    V: float             # full differential voltage span (0-60 V)
    src: str
    label: str = "MFR"

    @property
    def k(self):
        return self.F_block / self.stroke

    @property
    def mass(self):
        return 7.8e3 * self.L * self.W * self.T      # PZT ~7.8 g/cm3 (ASSUMPTION)


BENDERS: Dict[str, Bender] = {
    "PL127.10": Bender("PI PICMA PL127.10", 31e-3, 9.6e-3, 0.67e-3, 27e-3, 450e-6, 1.1, 3.4e-6, 420.0, 60.0, "AMF-11"),
    "PL128.10": Bender("PI PICMA PL128.10", 36e-3, 6.15e-3, 0.67e-3, 28e-3, 450e-6, 0.55, 1.2e-6, 360.0, 60.0, "AMF-11"),
    "PL140.10": Bender("PI PICMA PL140.10", 45e-3, 11.0e-3, 0.55e-3, 40e-3, 1000e-6, 0.5, 4.1e-6, 160.0, 60.0, "AMF-11"),
    "PL122.10": Bender("PI PICMA PL122.10", 25e-3, 9.6e-3, 0.67e-3, 22e-3, 310e-6, 1.25, 2.5e-6, 600.0, 60.0, "AMF-11"),
}
APA = {"APA60S": dict(stroke=75e-6, F_block=130.0, dims_mm=(15, 29, 9), m=8.5e-3, src="AMF-14"),
       "APA120S": dict(stroke=140e-6, F_block=46.0, dims_mm=(13, 29, 9), m=7.2e-3, src="AMF-14")}
SQUIGGLE = dict(name="New Scale SQL-RV-1.8", stall_N=0.3, speed_mm_s=7.0, travel=6e-3, hold_power=0.0, dims_mm=(2.8, 2.8, 6.0),
                src="AMF-15", label="MFR")
SMA = dict(name="Dynalloy Flexinol 0.025 mm (F1140 Rev M)", pull_N=8.9e-3 * G0, cool_s_LT=0.18, cool_s_HT=0.15, strain=0.04,
           src="AMF-77", label="MFR")


# ============================================================================== motors (CMG spin and gimbal)
@dataclass
class Motor:
    name: str
    d: float; L: float; m: float
    U: float; R: float; n0: float; I0: float
    kM: float            # N m/A
    M_stall: float; M_rated: float
    C0: float            # N m (static friction)
    Cv: float            # N m per rpm
    J: float             # kg m^2
    n_max: float
    src: str
    label: str = "MFR"


MOTORS: Dict[str, Motor] = {
    "0308B": Motor("Faulhaber 0308 H 003 B", 3e-3, 8e-3, 0.35e-3, 3.0, 34.0, 61000.0, 0.027, 0.32e-3, 0.026e-3, 0.013e-3,
                   1.77e-6, 1.09e-10, 0.0002e-7, 96000.0, "AMF-50"),
    "0515B": Motor("Faulhaber 0515 G 006 B", 5e-3, 15e-3, 1.6e-3, 6.0, 16.1, 43000.0, 0.056, 1.15e-3, 0.4e-3, 0.084e-3,
                   0.033e-3, 6.5e-10, 0.002e-7, 77000.0, "AMF-51"),
    "0620B": Motor("Faulhaber 0620 K 006 B", 6e-3, 20e-3, 2.5e-3, 6.0, 8.8, 48600.0, 0.056, 1.09e-3, 0.732e-3, 0.28e-3,
                   0.011e-3, 1.02e-9, 0.0095e-7, 100000.0, "AMF-78"),
    "1509B": Motor("Faulhaber 1509 T 006 B (flat)", 15e-3, 9e-3, 6.9e-3, 6.0, 22.0, 15000.0, 0.019, 3.56e-3, 0.953e-3, 0.45e-3,
                   0.019e-3, 3.42e-9, 0.69e-7, 40000.0, "AMF-78"),
}
DRONE_1103 = dict(name="BETAFPV 1103 11000KV outrunner", dims_mm=(13.5, 13.5, 16.0), m=3.25e-3, kv=11000.0, supply="2S (7.4 V)",
                  friction="not published", inertia="not published", src="AMF-79", label="MFR (retailer page)")


# ============================================================================== cells
@dataclass
class Cell:
    name: str
    d: float; L: float; m: float
    mAh: float
    v_nom: float
    i_max: float         # continuous discharge (A)
    src: str
    label: str = "MFR"
    usable: float = 0.8  # ASSUMPTION (config battery.usable_fraction)

    @property
    def Wh(self):
        return self.mAh * 1e-3 * self.v_nom * self.usable

    @property
    def P_max(self):
        return self.i_max * self.v_nom


CELLS: Dict[str, Cell] = {
    "custom_6.5x40": Cell("custom 6.5 x 40 mm Li-ion (pencil P0)", 6.5e-3, 40e-3, 3.451e-3, 90.0, 3.7, 0.18, "config/pencil.yaml (ASSUMPTION)",
                          "ASSUMPTION"),
    "LIR10440": Cell("EEMB LIR10440", 10.3e-3, 44.5e-3, 9.0e-3, 320.0, 3.7, 0.32, "AMF-31"),
    "LIR14500": Cell("EEMB LIR14500", 14.1e-3, 48.5e-3, 20.0e-3, 750.0, 3.7, 1.5, "AMF-80"),
    "GRP5811047": Cell("Grepow GRP5811047 narrow pouch", 11.0e-3, 47e-3, 5.0e-3, 200.0, 3.7, 4.0, "AMF-33",
                       "MFR (mass ASSUMPTION)"),
}


# ============================================================================== drivers and electronics
ELECTRONICS = {
    "base_W": 0.065,          # recording, BLE, MCU (config/pencil.yaml; ASSUMPTION)
    "stage_W": 0.135,         # nib-stage drive with the shipped tracker (SIM, docs/opt_tracker.md: 135 mW class-B rail)
    "vcm_driver": dict(part="TI DRV8214 (per axis)", q_W=0.003, eta=0.85, src="AMF-37",
                       note="current mirror IPROPI for the current loop; 4 A peak; WQFN 3 x 3 mm; quiescent ASSUMPTION"),
    "piezo_driver": dict(part="LT8365 boost + charge-recovery half bridges (as the stage), or DRV8662 for < 1 uF", recovery=0.7,
                         q_W=0.010, src="AMF-58/AMF-57 (hardware study rows); AMF-47, AMF-16", label="ASSUMPTION for recovery 70 %"),
    "bldc_driver": dict(part="3-phase sensorless driver (DRV10974 class, not verified)", eta=0.8, q_W=0.005, label="ASSUMPTION"),
    "imu2": dict(part="second LSM6DSV16X on the sleeve", W=0.0012, src="OPT-37", label="MFR (0.65 mA high-performance, 1.8 V)"),
}


# ============================================================================== envelope tiers (design choices = ASSUMPTION)
@dataclass
class Tier:
    key: str
    title: str
    od_body: float          # barrel OD (m)
    length: float
    mass_max: float         # total pen mass bound (kg)
    cell: str
    zones: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)   # name -> (z0, z1, max OD) in m
    note: str = ""
    label: str = "ASSUMPTION (design choice)"


TIERS: Dict[str, Tier] = {
    "T0": Tier("T0", "Pencil (Rev P0 envelope)", 8.9e-3, 0.166, 0.020, "custom_6.5x40",
               {"cap": (0.141, 0.162, 8.9e-3)},
               "As the current concept: bore 7.9 mm, cell 6.5 x 40 mm at z 121-161 mm; a cap device takes cell space"),
    "T1": Tier("T1", "Slim pen", 11.0e-3, 0.166, 0.025, "custom_6.5x40",
               {"cap": (0.128, 0.162, 11.0e-3)},
               "Bore 10.4 mm; same electronics and cell as T0; 5 g more mass allowed; cap zone 34 mm"),
    "T2c": Tier("T2c", "Pen with a cap bulb", 11.0e-3, 0.166, 0.040, "LIR10440",
                {"cap": (0.116, 0.166, 16.0e-3)},
                "Barrel 11 mm with a 10440 cell; top 50 mm up to 16 mm OD for the inertial module"),
    "T2g": Tier("T2g", "Pen with a grip bulb", 11.0e-3, 0.166, 0.040, "LIR10440",
                {"grip": (0.012, 0.095, 16.0e-3)},
                "Barrel 11 mm with a 10440 cell; grip section z 12-95 mm up to 16 mm OD (fingers and web on the bulb)"),
    "T3": Tier("T3", "Assistive-handle pen", 11.0e-3, 0.170, 0.080, "LIR14500",
               {"grip": (0.010, 0.110, 22.0e-3), "cap": (0.110, 0.170, 16.0e-3)},
               "Handle up to 22 mm OD over z 10-110 mm (thick assistive-pen class); 14500 cell in the handle"),
}


def cylinder_mass(d, L, rho=RHO_WHA, d_in=0.0):
    return rho * math.pi / 4 * (d * d - d_in * d_in) * L


def ring_inertia(m, d_out, d_in=0.0):
    return m * ((d_out / 2) ** 2 + (d_in / 2) ** 2) / 2
