"""Catalogue parts for the heel drive: motors, gearheads, piezo drives, sensors, wheels, fluids (MFR, with ledger ids).

Every number is a manufacturer statement (MFR) with the proposed ledger id of results/drive/evidence_rows.csv, or an
ASSUMPTION where the datasheet was not opened (said so in `note`).  Battery voltage for the pen: 3.0-4.2 V
(Li-ion, AMF-80); motor data at other voltages are scaled linearly in speed (CALC).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

G_CM2 = 1e-7          # kg m^2 per g cm^2
MNM = 1e-3            # N m per mN m


@dataclass(frozen=True)
class Motor:
    key: str
    label: str
    kind: str                 # "dc" (brushed coreless), "bldc", "stepper"
    d_mm: float
    l_mm: float
    mass_g: float
    V_nom: float
    n0_rpm: float             # no-load speed at V_nom
    tau_cont_mNm: float       # rated / nominal (max continuous) torque
    tau_stall_mNm: float      # stall torque at V_nom
    kt_mNm_A: float
    R_ohm: float
    J_gcm2: float
    tau_fric_mNm: float       # static friction torque (ASSUMPTION where not given)
    Rth_K_W: float            # winding to ambient (sum of the two stages)
    T_max_C: float
    ledger: str
    label_ev: str = "MFR"
    note: str = ""

    def J(self) -> float:
        return self.J_gcm2 * G_CM2

    def n0_at(self, V: float) -> float:
        """No-load speed (rpm) at voltage V (CALC: proportional to V)."""
        return self.n0_rpm * V / self.V_nom

    def stall_at(self, V: float) -> float:
        """Stall torque (N m) at V, voltage-limited (CALC: kt V / R)."""
        return self.kt_mNm_A * MNM * V / self.R_ohm


@dataclass(frozen=True)
class Gearhead:
    key: str
    label: str
    d_mm: float
    ratio: float
    eta: float
    tau_cont_mNm: float
    tau_int_mNm: float
    l_mm: float
    mass_g: float
    backlash_deg: float
    ledger: str
    label_ev: str = "MFR"
    note: str = ""


MOTORS: Dict[str, Motor] = {m.key: m for m in [
    Motor("fh0620B", "Faulhaber 0620 B (6 V) brushless", "bldc", 6.0, 20.0, 2.5, 6.0, 48600, 0.28, 0.732, 1.09, 8.8,
          0.0095, 0.011, 13.2 + 84.3, 125.0, "AMF-100",
          note="eshop.faulhaber.com series 0620 B, variant 0620K006B; static friction torque 0.011 mNm (MFR)"),
    Motor("mxDCX6M", "maxon DCX 6 M (3 V) coreless DC", "dc", 6.0, 15.7, 2.4, 3.0, 17500, 0.332, 0.524, 1.56, 9.0,
          0.0183, 0.01, 105.0 + 20.0, 100.0, "AMF-101",
          note="maxon catalogue 2020/21 p.75; length 15.7 mm and friction torque ASSUMPTION (not in the extract read)"),
    Motor("mxDCX8M", "maxon DCX 8 M (4.2 V) coreless DC", "dc", 8.0, 16.7, 4.3, 4.2, 11700, 0.649, 1.14, 3.36, 12.0,
          0.0379, 0.015, 101.0 + 16.9, 100.0, "AMF-101",
          note="maxon catalogue 2020/21 p.76; length and mass ASSUMPTION (not in the extract read)"),
    Motor("orbBMN04", "Orbray (Namiki) BMN04-08 4 mm brushless", "bldc", 4.0, 8.0, 0.7, 3.0, 37600, 0.01, 0.04, 0.52,
          30.5, 0.0006, 0.002, 150.0, 100.0, "AMF-104",
          note="orbray.com BMN04-08; length 8 mm, rotor inertia, friction, thermal resistance and T_max ASSUMPTION"),
    Motor("fhAM0820", "Faulhaber AM0820 stepper (20 steps/rev)", "stepper", 8.0, 12.0, 3.3, 3.0, 15000, 0.65, 1.0,
          2.0, 18.0, 0.0275, 0.13, 4.1 + 65.3, 130.0, "AMF-105",
          note="EN_AM0820_FPS (2026): holding 0.65 mNm nominal, 1 mNm boosted; residual torque 0.13 mNm; kt and n0 "
               "stand-ins for the torque-speed curve (ASSUMPTION: 0.6 mNm up to about 6000 rpm on the 2.5x-voltage "
               "curve)"),
]}

GEARHEADS: Dict[str, Gearhead] = {g.key: g for g in [
    Gearhead("GP6A_3.9", "maxon GP 6 A 3.9:1", 6.0, 3.9, 0.88, 2.0, 5.0, 5.3, 1.7, 1.8, "AMF-102"),
    Gearhead("GP6A_15", "maxon GP 6 A 15:1", 6.0, 15.0, 0.77, 5.0, 10.0, 7.8, 2.1, 2.0, "AMF-102"),
    Gearhead("GP6A_57", "maxon GP 6 A 57:1", 6.0, 57.0, 0.68, 10.0, 20.0, 10.4, 2.5, 2.2, "AMF-102"),
    Gearhead("FH06_4", "Faulhaber 06/1 4:1", 6.0, 4.0, 0.90, 25.0, 35.0, 9.2, 2.0, 2.0, "AMF-103",
             note="efficiency, length and mass of the 1-stage version ASSUMPTION (series: 25 mNm cont., L 9.2-22.7 mm)"),
    Gearhead("FH06_16", "Faulhaber 06/1 16:1", 6.0, 16.0, 0.81, 25.0, 35.0, 11.9, 2.5, 2.2, "AMF-103",
             note="efficiency, length and mass ASSUMPTION (0.9 per stage)"),
    Gearhead("FH06_64", "Faulhaber 06/1 64:1", 6.0, 64.0, 0.73, 25.0, 35.0, 14.6, 3.0, 2.4, "AMF-103",
             note="efficiency, length and mass ASSUMPTION (0.9 per stage)"),
    Gearhead("SPG04_100", "Orbray SPG04 about 100:1", 4.0, 100.0, 0.60, 3.0, 5.0, 10.0, 0.8, 3.0, "AMF-104",
             note="SPG04 data not opened: every value ASSUMPTION"),
]}

# custom watch-scale transmissions of the recommended layout (drive/layout.py): module 0.1 gears, 0.9 per mesh
# (ASSUMPTION), torque limits ASSUMPTION; length 0 because they sit at the heel or beside the motor
PATHS: Dict[str, Gearhead] = {g.key: g for g in [
    Gearhead("WHEEL_PATH", "transfer spur 1:1 + 40 deg bevel 1:1 + axle bevel 2:1", 3.0, 2.0, 0.9 ** 3, 2.0, 4.0, 0.0,
             0.15, 1.5, "", label_ev="ASSUMPTION", note="three meshes at 0.9 each"),
    Gearhead("STEER_PATH", "transfer spur 1:1 + crown 2:1 on the fork", 3.0, 2.0, 0.9 ** 2, 2.0, 4.0, 0.0, 0.1, 1.0, "",
             label_ev="ASSUMPTION", note="two meshes at 0.9 each; steering angle read at the fork"),
    Gearhead("BALL_PATH", "transfer spur 1:1 + roller bevel 1:1", 3.0, 1.0, 0.9 ** 2, 2.0, 4.0, 0.0, 0.1, 1.5, "",
             label_ev="ASSUMPTION", note="two meshes at 0.9 each, per roller"),
]}


@dataclass(frozen=True)
class Part:
    key: str
    label: str
    values: Dict[str, float]
    ledger: str
    label_ev: str = "MFR"
    note: str = ""


PARTS: Dict[str, Part] = {p.key: p for p in [
    Part("squiggle", "New Scale SQL-RV-1.8 SQUIGGLE piezo linear motor",
         {"size_mm": 2.8, "length_mm": 6.0, "mass_g": 0.16, "stall_N": 0.33, "speed_mm_s_at_0.15N": 7.0,
          "power_W_moving": 0.34, "hold_power_W": 0.0, "travel_mm": 6.0}, "AMF-106"),
    Part("twusm4", "Micro travelling-wave ultrasonic motor, 4.12 mm PZT stator (research device)",
         {"d_mm": 4.12, "n_max_rpm": 30.0, "stall_mNm": 0.501, "preload_N": 0.323}, "AMF-107", "LIT"),
    Part("mrf132dg", "LORD MRF-132DG magnetorheological fluid",
         {"viscosity_Pa_s_40C": 0.112, "density_g_cm3": 3.05, "yield_kPa_max_plot": 50.0}, "AMF-108",
         note="yield stress read from the datasheet plot (approximate)"),
    Part("pmw3360", "PixArt PMW3360 optical navigation sensor (paper velocity, slip detection)",
         {"speed_ips_typ": 250.0, "accel_g": 50.0, "cpi_max": 12000.0, "fps_max": 12000.0, "run_mA": 16.3,
          "report_Hz": 1000.0}, "AMF-109"),
    Part("vinci_omni", "Vinci micro omni wheel (smallest commercial omni-wheel found)",
         {"d_mm": 11.5, "width_mm": 7.5, "n_rollers": 6.0}, "AMF-110", note="pre-launch product page"),
]}


def ratio_options(family: str) -> List[Gearhead]:
    return [g for g in GEARHEADS.values() if g.key.startswith(family)]


def as_dict() -> Dict:
    return {"motors": {k: asdict(v) for k, v in MOTORS.items()},
            "gearheads": {k: asdict(v) for k, v in GEARHEADS.items()},
            "paths": {k: asdict(v) for k, v in PATHS.items()},
            "parts": {k: asdict(v) for k, v in PARTS.items()}}
