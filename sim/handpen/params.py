r"""Labelled inputs of the hand-pen-paper model H1.

Frames follow stabpen/frames.py: page frame {P} with x, y in the page and z = n out of
the page; pen axis a (nib -> cap) at altitude theta and azimuth phi; t1 = sin(th) h - cos(th) n
(tilt plane, pointing down-forward); t2 = (-sin phi, cos phi, 0) (sideways).  Positions
along the pen are z (m) from the ball centre toward the cap.

Evidence labels used in this package:
  CALC        calculation from labelled inputs
  SIM         simulation (this package or model P1)
  MFR (id)    manufacturer statement, evidence-ledger id (docs/evidence.csv or the new rows
              in results/pencil/inertial_evidence_rows.csv)
  LIT (id)    literature, evidence-ledger id
  CAD         proposed design (mechanics/cad/pencil_revP.py, results/cad/*_summary.json)
  ASSUMPTION  value chosen here; the experiment that would measure it is named
Nothing in this package has been measured on hardware.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

D2R = math.pi / 180.0
CAD_Q = os.path.join(ROOT, "results", "cad", "pencil_revPQ_summary.json")

# ------------------------------------------------------------------------------------------------
# Labelled constants
# ------------------------------------------------------------------------------------------------
LABELS: Dict[str, Tuple[str, str]] = {}


def lab(name, label, source):
    LABELS[name] = (label, source)


# Hand impedance, tip-referred, in-plane (config/parameters.yaml `hand`, HAP-26 Fu & Cavusoglu 2012)
HAND = dict(k_nib=575.0, b_nib=1.3, M=0.21, k_arm=170.0, b_arm=11.0)
lab("hand.k_nib", "LIT (HAP-26)", "config/parameters.yaml hand.grip_stiffness 575 N/m (230-1040): tip-referred in-plane grasp stiffness k1")
lab("hand.b_nib", "LIT (HAP-26)", "hand.grip_damping 1.3 N s/m (0.3-4.6)")
lab("hand.M", "LIT (HAP-26)", "hand.mass 0.21 kg (0.05-0.57)")
lab("hand.k_arm", "LIT (HAP-26)", "hand.arm_stiffness 170 N/m (63-533)")
lab("hand.b_arm", "LIT (HAP-26)", "hand.arm_damping 11 N s/m (3.7-27.6)")
lab("hand.measurement_point", "LIT (HAP-26)",
    "Fu & Cavusoglu 2012 Sec. II-B: force applied and position recorded at the stylus gimbal centre; grip-force sensor 4 cm "
    "from it -> the lumped model is a driving-point impedance about 4 cm ahead of the fingers, taken here as the nib")
lab("hand.normal", "ASSUMPTION",
    "the grip is made isotropic at the nib (575 N/m, 1.3 N s/m in x, y and z); parameters.yaml assumes 800 N/m, 3 N s/m normal "
    "(range 200-3000); the P1 comparison is run with the same normal values")

# Grip geometry (tripod grasp): ASSUMPTION (task definition; no measured pen-grip contact map found)
GRIP = dict(z_f=0.0275, z_f_range=(0.020, 0.035), z_w=0.075, z_w_range=(0.060, 0.090))
lab("grip.z_f", "ASSUMPTION", "finger pads (thumb, index, middle) centred 27.5 mm from the nib (20-35 mm)")
lab("grip.z_w", "ASSUMPTION", "thumb-index web contact centred 75 mm from the nib (60-90 mm)")
# Split of the tip-referred compliance: unmeasured -> ASSUMPTION with sweep (grip.py)
SPLIT = dict(r_rot=0.5, rho_w=0.3)
lab("grip.r_rot", "ASSUMPTION",
    "fraction of the nib's static grip compliance that comes from pen rotation relative to the hand (0 = the pen cannot tilt "
    "in the grip, 1 = pure pivot); nominal 0.5, swept 0.1-0.8; measure with EXP-I01 (two-point compliance)")
lab("grip.rho_w", "ASSUMPTION", "share of the translational grip stiffness carried at the web (0.3; swept 0.1-0.6); EXP-I01")
# Fingertip pad literature (plausibility bound of the zone stiffness): Wiertlewski & Hayward 2012 (new row HAP-31)
PAD = dict(k_lo=600.0, k_hi=2000.0, b_lo=0.75, b_hi=2.38, n_ref=0.5, k_power=(1.48e3, 0.35), b_power=(1.78, 0.35))
lab("pad.k", "LIT (HAP-31)", "index fingertip tangential stiffness 0.6-2.0 kN/m, damping 0.75-2.38 N s/m at 0.5 N normal force "
    "(7 participants); k = 1.48 n^0.35 N/mm, b = 1.78 n^0.35 N s/m with n the normal force in N (author's copy, Table 1-2)")

# Paper contact and friction (model P1 values; config/pencil.yaml)
CONTACT = dict(mu_skid=0.12, mu_nib=0.15, ms_ratio=1.3, v_s=0.002, k_sk=1.0e5, c_sk=10.0, F_c=0.15, r_ring=1.4e-3,
               r_b=0.35e-3, presliding=1e-5)
lab("contact.mu_skid", "ASSUMPTION", "skid.mu 0.12 (0.05-0.25), EXP-Q01")
lab("contact.mu_nib", "ASSUMPTION", "nib.mu_nib 0.15 (0.05-0.35)")
lab("contact.k_sk", "ASSUMPTION", "skid-paper contact 1e5 N/m, 10 N s/m (model P1 values, EXP-Q01)")
lab("contact.F_c", "ASSUMPTION", "nib spring 0.15 N axial -> ball normal force F_c/sin(theta) = 0.196 N at 50 deg (EXP-Q02)")

# Envelope, mass and power budgets (config/pencil.yaml)
BUDGET = dict(od=8.9e-3, bore=7.9e-3, length=0.166, length_max=0.170, mass_target=0.020, mass_upper=0.024,
              battery_Wh=0.266, p_electronics=0.065, cell_z=(0.121, 0.161), cell_d=6.5e-3, cell_m=3.451e-3)
lab("budget", "CAD / inherited target", "config/pencil.yaml envelope, battery (90 mAh, 0.266 Wh usable), electronics 65 mW")

# Materials and parts
RHO_WHA = 18.0e3          # MFR (AMF-49): ASTM B777 class 3 tungsten heavy alloy, 18 g/cm3, non-magnetic grade exists
RHO_AIR, MU_AIR = 1.2, 1.8e-5
lab("rho_WHA", "MFR (AMF-49)", "Elmet ASTM B777 class 3 (95 % W): 18 g/cm3; ET95NM non-magnetic (permeability <= 1.05)")
# Micro BLDC motors (Faulhaber datasheets, downloaded 2026-09-28): new rows AMF-50 (0308 B) and AMF-51 (0515 B)
MOTORS = {
    "0308B": dict(d=3e-3, L=8e-3, m=0.35e-3, U=3.0, R=34.0, n0=61000.0, I0=0.027, k_M=0.32e-3, M_stall=0.026e-3,
                  M_rated=0.013e-3, C0=1.77e-6, Cv=1.09e-10, n_max=96000.0, eta_max=0.20, J=0.0002e-7, bearings="ruby",
                  src="AMF-50"),
    "0515B": dict(d=5e-3, L=15e-3, m=1.6e-3, U=6.0, R=16.1, n0=43000.0, I0=0.056, k_M=1.15e-3, M_stall=0.4e-3,
                  M_rated=0.084e-3, C0=0.033e-3, Cv=6.5e-10, n_max=77000.0, eta_max=0.39, J=0.002e-7, bearings="sintered",
                  src="AMF-51"),
}
# units: k_M N m/A; torques N m; C0 N m; Cv N m per rpm; J kg m^2 (datasheet g cm^2 x 1e-7)
lab("motor.0308B", "MFR (AMF-50)", "Faulhaber 0308 H 003 B: 3 x 8 mm, 0.35 g, 61 000 rpm no-load at 3 V, I0 27 mA, stall 0.026 mNm, "
    "rated 0.013 mNm, friction 1.77e-3 mNm + 1.09e-7 mNm/rpm, 96 000 rpm max, ruby bearings, eta 20 %")
lab("motor.0515B", "MFR (AMF-51)", "Faulhaber 0515 G 006 B: 5 x 15 mm, 1.6 g, 43 000 rpm no-load at 6 V, I0 56 mA, stall 0.4 mNm, "
    "rated 0.084 mNm, k_M 1.15 mNm/A, R 16.1 ohm, friction 0.033 mNm + 6.5e-7 mNm/rpm, 77 000 rpm max, sintered bearings")
# Balance quality (ISO 21940-11 grade G = e*omega): standard not read -> ASSUMPTION bracket
BALANCE_G = dict(nominal=2.5e-3, best=0.4e-3, worst=6.3e-3)   # m/s
lab("balance", "ASSUMPTION", "rotor balance grade G2.5 (G0.4-G6.3); secondary summaries of ISO 21940-11 list G0.4 for gyroscopes; "
    "not verified against the standard")
# Wrist (for the hand-rotation hand calculation only)
WRIST = dict(k_passive=1.3, k_range=(0.55, 3.0), J_hand=3.0e-3, J_range=(2.0e-3, 4.5e-3))
lab("wrist.k", "LIT (HAP-32)", "passive wrist stiffness matrix mean [1.28 -0.18; -0.18 1.74] N m/rad (FE, RUD), flexion 0.55, "
    "extension 1.02 N m/rad (Formica et al. 2012, 10 subjects, relaxed)")
lab("wrist.J", "ASSUMPTION", "hand inertia about the wrist 2-4.5e-3 kg m^2 (0.4-0.5 kg hand, CoM 60-80 mm from the wrist)")
# Voice-coil figure of merit for a cap reaction mass: ASSUMPTION scaled from the project's SIM of a planar
# moving-magnet coil in the 7.9 mm bore (config/pencil.yaml stage_vcm.Km 0.080 N/sqrt(W))
KM_CAP = dict(cell=0.04, slug=0.06)
lab("vcm.Km", "ASSUMPTION (from SIM)", "reaction-mass voice coil K_m 0.06 N/sqrt(W) for a tungsten slug with a moving magnet, "
    "0.04 N/sqrt(W) for coils around the moving cell; scaled from stage_vcm.Km 0.080 N/sqrt(W) (magpylib, pencil.yaml)")


# ------------------------------------------------------------------------------------------------
# Pen mass properties from the CAD (+10 % wiring and adhesives, distributed pro rata)
# ------------------------------------------------------------------------------------------------
# own extent of each CAD part: (length along the axis, r^2 term for the transverse inertia of a cylinder: r^2/4,
# tube: (ro^2 + ri^2)/4); unlisted parts are point masses.  Lengths from results/cad parameters_mm.
_SHAPES = {
    "barrel": (0.166, (4.45e-3 ** 2 + 3.95e-3 ** 2) / 4), "rear_cap": (0.005, 4.45e-3 ** 2 / 4),
    "clamp_block": (0.008, 3.95e-3 ** 2 / 4), "battery": (0.040, 3.25e-3 ** 2 / 4), "pcb": (0.042, 2.75e-3 ** 2 / 3),
    "pcb_components_envelope": (0.042, 2.75e-3 ** 2 / 3), "refill_D1": (0.067, 1.175e-3 ** 2 / 4),
    "nib_spring": (0.010, 1.2e-3 ** 2 / 2), "bender_x_neg": (0.036, 0), "bender_x_pos": (0.036, 0),
    "bender_y_neg": (0.036, 0), "bender_y_pos": (0.036, 0),
}
_FALLBACK_PARTS = [("barrel", 2.723, 84.97), ("battery", 3.451, 141.0), ("clamp_block", 1.399, 55.0),
                   ("pcb", 0.333, 99.0), ("pcb_components_envelope", 1.004, 99.0), ("refill_D1", 0.84, 34.7),
                   ("bender_x_neg", 0.489, 41.0), ("bender_x_pos", 0.489, 41.0), ("bender_y_neg", 0.489, 41.0),
                   ("bender_y_pos", 0.489, 41.0), ("rear_cap", 0.123, 163.99), ("other", 0.922, 40.0)]


def cad_parts():
    """[(name, mass kg, z m, length m, r^2 term m^2)] from the CAD summary (fallback: rounded constants)."""
    if os.path.exists(CAD_Q):
        d = json.load(open(CAD_Q))
        rows = [(p["part"], p["mass_g"] * 1e-3, p["com_z_mm"] * 1e-3) for p in d["parts"]]
        src = os.path.relpath(CAD_Q, ROOT)
    else:
        rows = [(n, m * 1e-3, z * 1e-3) for n, m, z in _FALLBACK_PARTS]
        src = "fallback constants"
    out = []
    for n, m, z in rows:
        L, r2 = _SHAPES.get(n, (0.0, 0.0))
        out.append((n, m, z, L, r2))
    return out, src


def mass_properties(parts):
    m = sum(p[1] for p in parts)
    zg = sum(p[1] * p[2] for p in parts) / m
    J = sum(p[1] * ((p[2] - zg) ** 2 + p[3] ** 2 / 12.0 + p[4]) for p in parts)
    return m, zg, J


@dataclass
class PenBody:
    """Rigid pen body: mass m (kg), CoM z_g (m from the ball), transverse inertia J_g about the CoM (kg m^2)."""
    m: float
    z_g: float
    J_g: float
    parts: list = field(default_factory=list, repr=False)
    note: str = ""

    @property
    def J_nib(self):
        return self.J_g + self.m * self.z_g ** 2

    def add(self, name, m, z, L=0.0, r2=0.0):
        return make_body(self.parts + [(name, m, z, L, r2)], note=self.note + f"; +{name} {m * 1e3:.2f} g at {z * 1e3:.0f} mm")

    def remove(self, name, frac=1.0, new_len=None, new_z=None):
        parts = []
        for p in self.parts:
            if p[0] == name:
                if frac < 1.0:
                    parts.append((p[0], p[1] * frac, new_z if new_z is not None else p[2],
                                  new_len if new_len is not None else p[3], p[4]))
                continue
            parts.append(p)
        return make_body(parts, note=self.note + f"; {name} x{frac:.2f}")

    def summary(self):
        return {"mass_g": self.m * 1e3, "com_mm": self.z_g * 1e3, "J_cm_kgm2": self.J_g, "J_nib_kgm2": self.J_nib,
                "radius_of_gyration_mm": math.sqrt(self.J_g / self.m) * 1e3, "note": self.note}


def make_body(parts, note=""):
    m, zg, J = mass_properties(parts)
    return PenBody(m, zg, J, parts, note)


def pen_body(wiring=0.10):
    """CAD (Q) pen with all parts scaled by 1 + wiring (config convention of model P1)."""
    parts, src = cad_parts()
    parts = [(n, m * (1 + wiring), z, L, r2) for n, m, z, L, r2 in parts]
    return make_body(parts, note=f"CAD {src} x{1 + wiring:.2f} (wiring and adhesives, ASSUMPTION pro rata)")


lab("pen.body", "CAD + ASSUMPTION", "results/cad/pencil_revPQ_summary.json parts (12.2 g, CoM 88 mm) x1.10 for wiring/adhesive "
    "(model P1 convention); own-length inertia of barrel, cell, board, plates and refill as uniform rods")


# ------------------------------------------------------------------------------------------------
# Configuration of one hand-pen-paper case
# ------------------------------------------------------------------------------------------------
@dataclass
class Device:
    """Cap / grip device.  kind: none | rm (active reaction mass) | tmd (passive tuned mass) | mass (fixed cap mass)
    | cmg (scissored-pair control-moment gyroscope, one pair per axis) | gyro (passive rotor along the axis)."""
    kind: str = "none"
    m: float = 0.0                 # moving mass (rm, tmd) or added fixed mass (mass), kg
    z: float = 0.141               # position along the pen, m
    stroke: Tuple[float, float, float] = (0.5e-3, 0.5e-3, 0.0)   # t1, t2, axial half-stroke (m); 0 = axis locked
    F_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)          # actuator force limit per axis (N)
    k_c: float = 0.0               # centring spring (rm) or tuning spring (tmd), N/m
    c_c: float = 0.0               # centring / tuning damper, N s/m
    H: float = 0.0                 # rotor angular momentum (one rotor), N m s (gyro, cmg)
    delta_max: float = 0.6         # cmg gimbal angle limit (rad)
    rate_max: float = 30.0         # cmg gimbal rate limit (rad/s)
    axes: Tuple[int, int] = (1, 1) # cmg pairs active: (torque about t2 [tilt plane], torque about t1 [lateral])
    Km: float = 0.06               # voice-coil figure of merit (N/sqrt(W)) for power bookkeeping
    added_fixed: float = 0.0       # fixed mass the device adds to the pen body (motors, coils, frames), kg
    removed_cell_frac: float = 0.0 # fraction of the cell mass removed to make room
    label: str = ""


@dataclass
class Sleeve:
    """Grip sleeve (handle) held by the fingers, carrying the pen body through an actuated 2-DOF pivot (extension added by
    opt/inertial; PROPOSED DESIGN, all values set by the caller).  The pen body keeps the paper contacts, the nib stage
    and any cap device; the grip zones act on the sleeve.  Pivot: flexure at z_p (translational stiffness k_pt, axial
    k_pa, bending k_pr; stiffness-proportional damping beta_p).  Actuator at z_a acting on the transverse relative
    displacement: act 'vcm' (force = command + preload - k_a d - c_a d', |command| <= F_max, stops at +/-stroke) or
    'piezo' (force = k_a (command - d) - c_a d' + preload, |command| <= stroke = free stroke, crash stop at 1.5 stroke).
    push_on_sleeve routes the writing push through the sleeve (applied at the sleeve's z = 0: the pivot carries the
    paper's transverse reaction; no static couple on the hand)."""
    m: float = 8.0e-3
    z_g: float = 0.050
    J_g: float = 6.0e-6
    z_p: float = 0.015
    k_pt: float = 5.0e4
    k_pa: float = 1.0e5
    k_pr: float = 0.02
    beta_p: float = 1.0e-4
    z_a: float = 0.075
    act: str = "piezo"
    k_a: float = 1000.0
    c_a: float = 0.05
    stroke: float = 1.0e-3
    F_max: float = 1.0
    preload: Tuple[float, float] = (0.0, 0.0)
    push_on_sleeve: bool = True
    k_stop: float = 2.0e4
    label: str = ""

    @property
    def J_nib(self):
        return self.J_g + self.m * self.z_g ** 2


@dataclass
class Config:
    theta_deg: float = 50.0
    phi_deg: float = 0.0
    N0: float = 1.0
    # grip
    k_nib: float = HAND["k_nib"]
    b_nib: float = HAND["b_nib"]
    grip_scale: float = 1.0          # passive compliant sleeve: multiplies every grip stiffness (series compliance)
    grip_damp_add: float = 0.0       # extra tip-referred grip damping from a viscoelastic sleeve (N s/m)
    r_rot: float = SPLIT["r_rot"]
    rho_w: float = SPLIT["rho_w"]
    z_f: float = GRIP["z_f"]
    z_w: float = GRIP["z_w"]
    # hand
    M_hand: float = HAND["M"]
    k_arm: float = HAND["k_arm"]
    b_arm: float = HAND["b_arm"]
    # contact
    mu_skid: float = CONTACT["mu_skid"]
    mu_nib: float = CONTACT["mu_nib"]
    ms_ratio: float = CONTACT["ms_ratio"]
    v_s: float = CONTACT["v_s"]
    c_visc: float = 0.0              # viscous drag at the nose (idealised damped roller), N s/m
    k_sk: float = CONTACT["k_sk"]
    c_sk: float = CONTACT["c_sk"]
    F_c: float = CONTACT["F_c"]
    skid: bool = True
    # pen
    wiring: float = 0.10
    lock_rotation: bool = False      # rigid rotation (for the check against model P1)
    # nib stage (kinematic oracle stage, P1 limits)
    stage: bool = False
    q_lim: float = 0.30e-3
    q_taper: float = 0.05e-3
    q_stop: float = 0.40e-3
    stage_hz: float = 150.0
    stage_zeta: float = 0.7
    stage_rate: float = 2000.0
    device: Device = field(default_factory=Device)
    # writer's voluntary correction of slow ink errors (visual loop): off by default (model P1 convention)
    voluntary: bool = False
    vc_hz: float = 1.0               # ASSUMPTION: loop crossover ~ integral gain 2 pi f (eye-hand loop 0.5-2 Hz, ACT-02)
    vc_delay: float = 0.12           # ASSUMPTION: visual-motor delay (s)
    label: str = ""
    # ---- extensions (opt/inertial); defaults leave the model exactly as before
    sleeve: Optional[Sleeve] = None  # grip sleeve with an actuated pivot
    stage_src: int = 0               # stage command: 0 oracle (clean reference), 1 external estimate (run(clean=...)), 2 controller
    ctl: Optional[dict] = None       # in-loop controller spec (opt/inertial/control.py builds it)
    body_mod: Optional[dict] = None  # envelope tiers: {"remove": [part names], "add": [(name, m, z, L, r2)]} applied to the CAD pen
    skid_geom: Optional[Tuple[float, float]] = None   # (p_nom, r_ring) override of the skid contact point (m); (0, 0) puts it at the ball
    stage_slew: float = 0.08         # stage reference slew limit (m/s); 0.08 is the P1 value (large-travel stages need more)

    def replace(self, **kw):
        return replace(self, **kw)


def geometry_vectors(theta_deg, phi_deg=0.0):
    th, ph = theta_deg * D2R, phi_deg * D2R
    h = np.array([math.cos(ph), math.sin(ph), 0.0])
    n = np.array([0.0, 0.0, 1.0])
    a = math.cos(th) * h + math.sin(th) * n
    t1 = math.sin(th) * h - math.cos(th) * n
    t2 = np.array([-math.sin(ph), math.cos(ph), 0.0])
    return a, t1, t2, n, h


def protrusion_centre(theta_deg, r_ring=CONTACT["r_ring"], r_b=CONTACT["r_b"]):
    """Ball-centre protrusion beyond the skid-ring plane with both on the paper (sim/pencil/design.protrusion)."""
    th = theta_deg * D2R
    return (r_ring * math.cos(th) - r_b) / math.sin(th)


def pen_with_device(cfg: Config) -> PenBody:
    """Pen body carrying the device's fixed parts (the moving mass of rm/tmd is a separate body)."""
    body = pen_body(cfg.wiring)
    bm = getattr(cfg, "body_mod", None)
    if bm:
        for name, m_, z_, L_, r2_ in bm.get("add", ()):
            body = body.add(name, m_, z_, L_, r2_)
        for name in bm.get("remove", ()):
            body = body.remove(name)
    dv = cfg.device
    if dv.removed_cell_frac > 0:
        f = 1.0 - dv.removed_cell_frac
        z0, z1 = BUDGET["cell_z"]
        L = (z1 - z0) * f
        m_cell = next(p_[1] for p_ in body.parts if p_[0] == "battery")
        body = body.remove("battery", frac=f, new_len=L, new_z=z0 + L / 2) if f > 0 else body.remove("battery")
        # keep the removed part's pro-rata wiring share (the x(1 + wiring) scaling is not part of the cell)
        body = body.add("cell_wiring_share", m_cell * dv.removed_cell_frac * cfg.wiring / (1 + cfg.wiring), (z0 + z1) / 2)
    if dv.added_fixed > 0:
        body = body.add(f"{dv.kind}_fixed", dv.added_fixed, dv.z, 0.01, 3e-3 ** 2 / 4)
    if dv.kind == "mass" and dv.m > 0:
        body = body.add("cap_mass", dv.m, dv.z, 0.015, 2.25e-3 ** 2 / 4)
    return body
