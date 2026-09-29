r"""Labelled inputs of study K (the rear end-cap).

Every constant carries a label in LABELS: (label, source).  Labels: MFR (ledger id), LIT (ledger id), CALC, SIM,
ASSUMPTION.  Ledger ids AMF-120..127, HAP-80..89, PDT-39..42, ACT-81..83 and PAT-35..39 are proposed rows in
results/endcap/evidence_rows.csv (endcap/evidence.py); other ids are in docs/evidence.csv.
Frames and positions follow sim/handpen: z along the pen axis from the ball (m), t1 in the tilt plane, t2 sideways.
Nothing here was measured.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Dict, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LABELS: Dict[str, Tuple[str, str]] = {}


def lab(name, label, source):
    LABELS[name] = (label, source)


G0 = 9.80665
TWO_PI = 2.0 * math.pi

# ------------------------------------------------------------------------------------------------ envelope (lead)
ENV = dict(od=26e-3, wall=1.0e-3, length=45e-3, mass=45e-3, p_peak=1.0, p_avg=0.3, z0=0.130, z1=0.175,
           pen_length_max=0.175, pen_mass_max=0.120, battery_h_min=8.0)
lab("env", "ASSUMPTION (lead brief, docs/revJ_plan.md s6)",
    "rear end-cap <= 26 mm across, about 45 mm long, <= 45 g, <= 1 W peak, <= 0.3 W average; pen <= 175 mm, <= 120 g, "
    ">= 8 h of writing with assistance on")
lab("env.z", "ASSUMPTION", "end-cap occupies z 130-175 mm of a 175 mm pen (the Rev H cell, 101-149.5 mm, then has no room: "
    "only 31 mm remain behind the board; packaging note for the lead)")
D_IN = ENV["od"] - 2 * ENV["wall"]          # 24 mm free bore (CALC)
Z_CAP = 0.5 * (ENV["z0"] + ENV["z1"])        # 152.5 mm: centre of the end-cap (CALC)

# ------------------------------------------------------------------------------------------------ Rev H reference pen
REVH = dict(mass=74.95e-3, com=92.85e-3, p_base=0.081, cell_Wh=2.22, cell10440_Wh=0.947)
lab("revh.mass", "CALC (results/revH/layout.json)", "Rev H pen 74.95 g, centre of mass 92.85 mm from the ball")
lab("revh.p_base", "SIM + CALC (results/opt/inertial_opt.json power_battery)", "0.081 W while writing with the nose")
lab("revh.cell", "MFR (AMF-80, AMF-31) + ASSUMPTION 80 % usable",
    "LIR14500 750 mAh -> 2.22 Wh usable; LIR10440 320 mAh -> 0.95 Wh usable")

# ------------------------------------------------------------------------------------------------ materials
RHO_WHA = 18.0e3
UTS_WHA = 724e6
NU_WHA = 0.28
RHO_PEEK = 1.30e3
RHO_AL = 2.70e3
RHO_CU = 8.89e3
RHO_NDFEB = 7.5e3
RHO_AIR, MU_AIR = 1.2, 1.8e-5
lab("rho_WHA", "MFR (AMF-49; AMF-125)", "tungsten heavy alloy 18.0 g/cm3 (ASTM B777 class 3); Plansee DENSIMET/INERMET 17.0-18.8 g/cm3, "
    "INERMET paramagnetic (non-magnetic) grades exist")
lab("uts_WHA", "MFR (AMF-49)", "ultimate tensile strength >= 724 MPa (105 ksi)")
lab("nu_WHA", "ASSUMPTION", "Poisson ratio 0.28 (typical of tungsten alloys; not from a ledger source)")
lab("rho_PEEK", "MFR (AMF-24)", "1.30 g/cm3")
lab("rho_Al", "ASSUMPTION", "6061 handbook 2.70 g/cm3")
lab("rho_Cu", "MFR (AMF-29)", "8.89 g/cm3")
lab("rho_NdFeB", "ASSUMPTION", "7.5 g/cm3 (as opt/inertial/revh.py)")


# ------------------------------------------------------------------------------------------------ motors (MFR)
@dataclass(frozen=True)
class Motor:
    name: str
    d: float            # m
    L: float            # m
    m: float            # kg
    U: float            # V
    R: float            # ohm (phase-phase)
    n0: float           # rpm no-load
    I0: float           # A no-load
    kM: float           # N m / A
    stall: float        # N m
    rated: float        # N m (continuous, thermal)
    C0: float           # N m static friction
    Cv: float           # N m per rpm
    J: float            # kg m^2 rotor
    n_max: float        # rpm
    src: str
    note: str = ""


MOTORS: Dict[str, Motor] = {
    "0308B": Motor("Faulhaber 0308 H 003 B", 3e-3, 8e-3, 0.35e-3, 3.0, 34.0, 61000, 0.027, 0.32e-3, 0.026e-3, 0.013e-3,
                   1.77e-6, 1.09e-10, 2e-11, 96000, "AMF-50", "ruby bearings"),
    "0515B": Motor("Faulhaber 0515 G 006 B", 5e-3, 15e-3, 1.6e-3, 6.0, 16.1, 43000, 0.056, 1.15e-3, 0.4e-3, 0.084e-3,
                   0.033e-3, 6.5e-10, 2e-10, 77000, "AMF-51", "sintered bearings"),
    "0620B": Motor("Faulhaber 0620 K 006 B", 6e-3, 20e-3, 2.5e-3, 6.0, 8.8, 48600, 0.056, 1.09e-3, 0.732e-3, 0.28e-3,
                   0.011e-3, 1.02e-9, 9.5e-10, 100000, "AMF-78", "ball bearings"),
    "0824B": Motor("Faulhaber 0824 K 006 B", 8e-3, 24e-3, 5.2e-3, 6.0, 2.91, 35100, 0.055, 1.6e-3, 3.28e-3, 0.89e-3,
                   0.021e-3, 1.89e-9, 2.85e-9, 90000, "AMF-120", "preloaded ball bearings; radial 1.5 N at 10 000 rpm"),
    "1226B": Motor("Faulhaber 1226 S 006 B", 12e-3, 26e-3, 13.0e-3, 6.0, 2.2, 21000, 0.07, 2.68e-3, 7.24e-3, 2.13e-3,
                   0.073e-3, 5.3e-9, 1.5e-8, 79000, "AMF-121", "preloaded ball bearings; radial 5 N at 10 000 rpm"),
    "1509B": Motor("Faulhaber 1509 T 006 B (flat)", 15e-3, 9e-3, 6.9e-3, 6.0, 22.0, 15000, 0.019, 3.56e-3, 0.953e-3, 0.45e-3,
                   0.019e-3, 3.42e-9, 6.9e-8, 40000, "AMF-78", ""),
    "2610B": Motor("Faulhaber 2610 T 006 B (flat)", 26e-3, 10e-3, 20.1e-3, 6.0, 6.97, 6400, 0.01, 8.8e-3, 7.543e-3, 2.87e-3,
                   0.035e-3, 8.85e-9, 7.9e-7, 40000, "AMF-122", "plastic housing"),
    "2214BXT": Motor("Faulhaber 2214 S 006 BXT H (flat, external rotor)", 22e-3, 14e-3, 28.9e-3, 6.0, 2.42, 5760, 0.061,
                     9.58e-3, 23.5e-3, 9.4e-3, 0.061 * 9.58e-3, 0.0, 3.3e-7, 10000, "AMF-123",
                     "C0 not published: friction taken as I0 x kM at n0 (CALC)"),
    "INT": Motor("Custom integrated outrunner in the rotor hub (0620 B electrical and friction constants)", 8e-3, 3e-3, 2.0e-3, 6.0,
                 8.8, 48600, 0.056, 1.09e-3, 0.732e-3, 0.28e-3, 0.011e-3, 1.02e-9, 9.5e-10, 60000,
                 "ASSUMPTION (concept of HAP-82: the outrunner casing is the flywheel; constants of AMF-78)",
                 "custom part: 3 mm of added stack length, 8 mm across, 2.0 g"),
}
lab("motors", "MFR (AMF-50, AMF-51, AMF-78, AMF-120..123)", "Faulhaber datasheets at 22 degC and nominal voltage; units converted "
    "(mNm -> N m, g cm2 -> kg m2)")
lab("motor.INT", "ASSUMPTION", "a custom frameless BLDC integrated in the rotor hub (as the outrunner-casing flywheels of HAP-82), taken "
    "with the 0620 B constants (AMF-78), 3 mm added length, 8 mm across, 2.0 g, 60 000 rpm cap; a supplier must confirm (EXP-K03)")

# ------------------------------------------------------------------------------------------------ bearings, balance
BEARINGS = {"618/4": dict(d=4e-3, D=9e-3, B=2.5e-3, m=0.7e-3, C=423.0, n_lim=85000, src="AMF-126"),
            "618/8": dict(d=8e-3, D=16e-3, B=4e-3, m=3.0e-3, C=819.0, n_lim=56000, src="AMF-126")}
lab("bearings", "MFR secondary (AMF-126)", "SKF 618/4 limiting 85 000 r/min, 0.7 g; 618/8 limiting 56 000 r/min, 3 g (retailer pages)")
BEARING_FRICTION = 0.01e-3      # N m per rotor bearing pair at speed
lab("bearing_friction", "ASSUMPTION", "0.01 mN m per dedicated rotor bearing pair (no ledger source; bench EXP-K03)")
BALANCE_G = dict(best=0.4e-3, nominal=2.5e-3)
lab("balance", "MFR secondary (AMF-52) + ASSUMPTION", "G0.4 (gyroscope grade) best case; G2.5 nominal (electric motors)")
N_SPIN_MAX = 40000.0
lab("n_spin_max", "ASSUMPTION (bearing limiting speeds AMF-126, motor n_max)", "rotor speed cap 40 000 rpm with 4 mm bore "
    "miniature bearings (limiting 85 000 r/min) and a 2x margin")

# ------------------------------------------------------------------------------------------------ actuator figures of merit
KM_LRM_PER_SQRT_G_CU = 0.45
lab("vcm.Km", "ASSUMPTION (scaled from opt/inertial: Km 0.9 N/sqrt(W) for 4 g of copper)",
    "moving-magnet flat-coil reaction-mass actuator: Km = 0.45 N/sqrt(W) x sqrt(copper mass in g) per axis, times the share of "
    "each turn under the magnet and a gap-flux factor (endcap/design.lrm2); stroke <= 4 mm (flexure, ASSUMPTION)")
GIMBAL_DRIVE = dict(m=3.3e-3, rate_max=30.0, eta=0.35, J_rotor_frac=0.5)
lab("gimbal_drive", "ASSUMPTION (0515 B motor 1.6 g, AMF-51, + gearhead 1.5 g + angle sensor 0.2 g)",
    "one geared micro-motor per scissored pair drives both gimbals in opposite directions through a gear pair; rate limit "
    "30 rad/s; electromechanical efficiency 35 % for the gimbal power estimate")
FRAME_PER_ROTOR = 1.5e-3
lab("frame_per_rotor", "ASSUMPTION", "gimbal frame and fasteners per rotor 1.5 g (PEEK/aluminium)")
DRIVER_Q_W = 0.005
lab("driver_q", "ASSUMPTION", "3-phase driver quiescent 5 mW per spin motor (catalog 'bldc_driver' in opt/inertial/catalog.py)")

# ------------------------------------------------------------------------------------------------ haptic actuators and cues
HAPTUATOR = dict(name="Tactile Labs Haptuator Redesign TL002-14R", d=16e-3, L=29e-3, m=11e-3, acc_1V_150Hz=24.5,
                 load=20e-3, band=(50.0, 500.0), R=6.0, V_max=3.0, I_max=0.5, src="AMF-124")
lab("haptuator", "MFR (AMF-124)", "16 x 29 mm, 11 g; 2.5 G (24.5 m/s2) at 1 V, 150 Hz with 20 g total load; 50-500 Hz; 6 ohm; "
    "3 V / 0.5 A maximum")
FORCE_REACTOR = dict(m=5e-3, dims_mm=(5, 8, 35), src="HAP-86 (Yem 2016 Table I); HAP-81 (Traxion 5.2 g)")
lab("force_reactor", "LIT (HAP-86, HAP-81)", "Alps Force Reactor about 5 g, 5 x 8 x 35 mm")
CUE_LIT = {
    "traxion_equiv_force_N": (29.8e-3 * G0, 8.5e-3 * G0, "HAP-81", "virtual force 29.8 g (s.d. 8.5 g), 10 participants, 5.2 g actuator"),
    "tanabe2024_acc_m_s2": (60.0, None, "HAP-85", "75 Hz fundamental + 150 Hz, A1 = A2 = 60 m/s2 on a 67.4 g handle"),
    "tanabe2024_dir_correct": (0.9686, 0.075, "HAP-85", "median direction discrimination 96.86 % (IQR 7.5 %), 20 healthy adults"),
    "tanabe2024_velocity_d": (0.22, None, "HAP-85", "congruent cue raised peak wrist velocity vs no stimulus, Cohen d 0.22 (p < 0.01)"),
    "tanabe2020_acc_range": ((8.0, 40.0), None, "HAP-80", "Exp II amplitudes 8-40 m/s2; threshold lowest at 40 Hz, highest at 110 Hz"),
    "tanabe2026_motor_signs_logodds": (-1.95, (-2.48, -1.62), "PDT-39", "tremor or hemiplegia on the tested side: log-odds of a correct "
                                       "direction report -1.95 (95 % CI -2.48 to -1.62); affected sides near chance (50 %)"),
    "walker2018_torque_Nm": (51.19e-3, None, "HAP-82", "CMG pulse 51.19 N mm for 150 ms, reset -14.25 N mm over 550 ms"),
    "walker2018_dir_correct": (0.993, None, "HAP-82", "99.3 % (286/288) direction identification, 12 participants"),
    "walker2018_device_g": (197.7, None, "HAP-82", "two parallel double-gimbal CMGs, 197.7 g"),
    "walker2019_dir_correct": (0.933, None, "HAP-84", "skin-stretch holdable device: 8 directions > 93.3 %"),
    "walker2019_latency_s": ((0.33, 1.56), None, "HAP-84", "delay to motion onset: fast responders 0.33 s, slow 1.56 s"),
    "yem2016_dir_correct_10Hz": (0.90, None, "HAP-86", "DC-motor rotor pseudo-torque about 90 % correct at 10 Hz sawtooth, 8 participants"),
    "winfree2009_torque_Nm": (1.2, None, "HAP-83", "iTorqU 2.0: nearly 1.2 N m per gimbal axis; 486 g gimballed gyroscope"),
}
lab("cue_lit", "LIT (HAP-80..89, PDT-39)", "psychophysics and device data used by endcap/cue.py (see CUE_LIT)")

# ------------------------------------------------------------------------------------------------ hand, writing, tremor
WRITING = dict(stroke_s=(0.09, 0.15), band_hz=5.0, letter_mm=(3.0, 5.0), speed_mm_s=30.0)
lab("writing", "LIT (CON-24) + SIM (sim/pensim lognormal writers)", "strokes 0.09-0.15 s; writing energy mostly below 5 Hz; "
    "letters 3-5 mm; the synthetic writer (seed 300) has 98 % of its > 0.3 Hz power below 3 Hz")
LETTER_RULE = dict(write_mm=2.0, nudge_mm=0.2, f_write=(1.0, 3.0))
lab("letter_rule", "ASSUMPTION (rule fixed before the test runs)",
    "'can write' = >= 2 mm peak tip displacement (half a 4 mm letter) at 1-3 Hz, repeatable stroke after stroke, with the "
    "HAP-26 hand; 'can nudge' = >= 0.2 mm; below that, a cue at most")
VOLUNTARY = dict(vc_hz=1.0, vc_delay=0.12)
lab("voluntary", "ASSUMPTION (H1 option, sim/handpen/params.py)", "writer's visual correction loop: 1 Hz crossover, 0.12 s delay")
SPLITS = (0.3, 0.5, 0.7)
lab("r_rot", "ASSUMPTION (EXP-I01)", "share of the tip grip compliance from pen rotation in the grip; unmeasured; swept 0.3/0.5/0.7")

# ------------------------------------------------------------------------------------------------ propeller (limiting case)
PROP = dict(FM=0.5, eta_motor=0.6)
lab("prop", "ASSUMPTION", "micro-propeller figure of merit 0.5 and motor efficiency 0.6 (no thrust data opened; BETAFPV page AMF-127 "
    "gives motor mass only)")

# ------------------------------------------------------------------------------------------------ seeds (as opt/inertial)
SEEDS = {"tune": (300, 301, 302, 303), "tune_more": tuple(range(300, 308)), "test": (200, 201, 202, 203)}
lab("seeds", "ASSUMPTION (plan s5)", "tuning seeds >= 300; test seeds 200-203 used only for the final tables after the rules were fixed")


def labels_table():
    return [{"name": k, "label": v[0], "source": v[1]} for k, v in sorted(LABELS.items())]
