r"""Differentiable models of the candidate tip mechanisms (CALC on PROPOSED DESIGNS; PyTorch float64).

Every candidate is described by continuous variables (lengths in metres) and discrete part choices (magnet grade,
flexure material and stock thickness, magnet wire, back-iron alloy).  ``evaluate(kind, v, parts)`` returns the
metrics used by the optimiser and the report: tip travel (nominal and guaranteed over 35-75 deg), force constant at the
tip Km_tip (N/sqrt(W)), tip-equivalent moving mass, suspension stiffness at the tip, first parasitic mode, the
bandwidth the structure allows, copper loss for the design duties, peak force, added mass, radial build (envelope),
flexure strain, reaction force on the hand and constraint penalties.

Candidates
  gimbal_radial   C1: the Rev H topology scaled: 2-axis flexure gimbal at z_p, four magnets on a soft-iron hub at
                  z_a = z_p + L_b facing four flat coils (radial gap); the gap must clear the other axis's stroke.
  gimbal_axial    C1+ (new): the same gimbal, but the magnets face the coils ACROSS the pen axis (axial gap): four
                  magnet-pair units on a disc at the arm's end over four flat racetrack coils; lateral motion slides the
                  magnets parallel to the coils, so the gap does not grow with the stroke; a flat coil plate sees the
                  disc tilt (gap + r alpha at the rim).
  gimbal_sphere   C1S: gimbal_axial with the coil and magnet faces on spheres centred on the gimbal: constant gap
                  (custom curved parts, ASSUMPTION manufacturable).
  dual_plane      C2: two actuation planes (front coil set in the grip zone at z_1, rear set at z_2) driving a carrier
                  on two flexure planes; tilt and translation independent; the optimal force split between the planes.
  coarse_fine     C3: the C1S gimbal as the coarse stage (it no longer carries the tremor duty) plus a +-1 mm fine
                  stage at the carrier front for tremor.
  xy_wire         C4a: translating carrier on four superelastic NiTi wires, axial-gap actuator at the rear, no lever.
Screening only (not differentiable; datasheet numbers):  galvo pair (C4b, MFR AMF-137), ultrasonic piezo (C4c,
MFR AMF-138), SMA (C4d, MFR AMF-77), planar flexure stage at Awtar scale (LIT AMF-135).

Physics (lumped; every coefficient is an ASSUMPTION unless a ledger id is given):
  gap flux      B_g = B_r t_m / (t_m + g + t_c) * eta(topology, geometry), eta from the magpylib fit (magnetics.py)
  force const.  per axis, two units in push-pull:  Km_act = sqrt(2) * phi * B_g * sqrt(k_fill * V_leg / rho_Cu)
                (V_leg: coil-leg volume over the poles; phi: the share of the winding's length that is active,
                end turns and stroke overhang removed)
  tip           F_tip = F_act * lambda (lambda = actuator displacement per tip displacement); Km_tip = Km_act * lambda
  inertia       point and bar masses about the pivot; m_eff = I / z_p^2 at the tip
  flexure       cross-strip gimbal, per axis k_r = E b t^3 / (6 L_f); strain eps = t alpha / L_f (S-bending, factor 2)
  duties        tremor: 1.0 mm rms at 8 Hz per axis (Rev H design duty) with the effective acceleration calibrated on
                HW1 (Duty.tremor_a_eff) + ball drag mu_b N_b while inking (Rev H's 0.03 N rms residual is replaced by
                the explicit drag); autowrite: the planner's nose kinematics (tasks.autowrite_kinematics) + the same drag
                + the tremor duty on top; gravity from the nose's centre-of-mass offset
  power         P = sum over axes (F_act,rms / Km_act)^2  (copper loss; the driver and electronics are added in the
                report)
  drive         peak force within the 3.7 V bus at 1.5 A per axis (Rev H assumption): F_pk <= Km_act sqrt(V I)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np
import torch

torch.set_num_threads(1)
DT = torch.float64

# ------------------------------------------------------------------ constants with sources
RHO_CU = 8.89e3          # MFR AMF-29
RES_CU = 1.7241e-8       # MFR AMF-29 (20 degC)
RHO_MAG = 7.6e3          # MFR AMF-139 (Arnold N52 7.6 g/cm3)
RHO_FE = 7.87e3          # ASSUMPTION (1010 steel handbook)
RHO_TI = 4.42e3          # MFR AMF-21
RHO_AL = 2.70e3          # ASSUMPTION (6061)
E_TI = 114e9             # MFR AMF-21
E_AL = 69e9              # ASSUMPTION
G0 = 9.80665
G_CLEAR = 0.5e-3         # mechanical clearance magnet-coil (Rev H g0, ASSUMPTION)
V_BUS, I_PEAK = 3.7, 1.5 # drive limits per axis (Rev H assumption; DRV8214 4 A peak, MFR AMF-37)
MU_BALL = 0.15           # ball friction (ASSUMPTION; LIT CON-13 0.09-0.165)
F_REFILL = 0.15          # N, refill spring (ASSUMPTION, Rev H); ball normal = F / sin(theta)
THETA = math.radians(50.0)
N_BALL = F_REFILL / math.sin(THETA)
BORE_R = {"22": 10.0e-3, "24": 11.0e-3}      # handle bore radius for a 1 mm wall at OD 22 / 24 mm (ASSUMPTION)
R_TH_COIL = 100.0        # K/W coil to ambient through a 22 mm shell (ASSUMPTION; Rev A's 157 K/W, CHECKPOINT 2, is the bound)
DT_COIL_MAX = 20.0       # K coil temperature rise allowed while autowriting with tremor (ASSUMPTION: about 0.2 W at 100 K/W;
                         # keeps the shell near skin temperature).  Battery hours are reported, not constrained: autowrite is
                         # a mode for short texts; 8 h applies to writing with the stabiliser (docs/revJ_plan.md section 6)
Z_ACT_MAX = 0.100        # m, actuator centre + half length (a 16 mm board and the 48.5 mm cell behind it within 175 mm)

MAGNET_GRADES = {        # name -> (B_r low end T, max working temperature degC, ledger)
    "N42SH": (1.30, 150.0, "AMF-28"), "N48SH": (1.38, 150.0, "AMF-28 (N48SH class, ASSUMPTION within the K&J table)"),
    "N52": (1.42, 80.0, "AMF-139")}
FLEXURES = {             # name -> (E Pa, fatigue strain allowable, static strain allowable, density, ledger)
    "301FH": (200e9, 540e6 / 200e9, 1080e6 / 200e9, 7.8e3, "AMF-20"),
    "17-7PH_CH900": (200e9, 520e6 / 200e9, 1210e6 / 200e9, 7.7e3, "AMF-20"),
    "Ti6Al4V": (114e9, 530e6 / 114e9, 910e6 / 114e9, 4.42e3, "AMF-20/AMF-21"),
    "C17200_TH04": (127.6e9, 310e6 / 127.6e9, 1241e6 / 127.6e9, 8.26e3, "AMF-19"),
    "NiTi_superelastic": (45e9, 0.004, 0.03, 6.45e3, "AMF-141/AMF-142 (E and density ASSUMPTION)")}
STOCK_T = (50e-6, 75e-6, 100e-6, 127e-6, 150e-6, 200e-6)               # shim stock (ASSUMPTION typical series); >= 50 um so the
                                                                        # laser-cut strips survive handling (ASSUMPTION)
BUCKLE_SF = 3.0          # the gimbal's compressed strip must carry 3 x the refill force without buckling (ASSUMPTION)
WIRES = {                # bare copper diameter -> fill factor of a bonded flat coil (ASSUMPTION: grade-2 enamel + bond)
    0.08e-3: 0.50, 0.10e-3: 0.55, 0.125e-3: 0.58, 0.15e-3: 0.60, 0.20e-3: 0.63}
BACK_IRON = {"1010": (1.6, RHO_FE, "ASSUMPTION"), "Hiperco50A": (2.3, 8.12e3, "AMF-140 (2.4 T saturation; density ASSUMPTION)")}
FAT_SF = 1.5             # safety factor on the fatigue strain (ASSUMPTION)


@dataclass
class Parts:
    grade: str = "N48SH"
    flexure: str = "301FH"
    t_flex: float = 100e-6
    wire: float = 0.10e-3
    iron: str = "1010"
    bore: str = "22"

    @property
    def B_r(self):
        return MAGNET_GRADES[self.grade][0]

    @property
    def k_fill(self):
        return WIRES[self.wire]


@dataclass
class Duty:
    """Design duties at the tip (per axis rms unless noted); filled from tasks.autowrite_kinematics."""
    tremor_x_rms: float = 1.0e-3          # m (Rev H duty)
    tremor_f: float = 8.0                 # Hz
    tremor_resid: float = 0.0             # N rms (Rev H's duty had 0.03 N; here the ball drag is modelled explicitly)
    tremor_a_eff: float = 10.6            # m/s^2 rms per axis: the force per unit moving mass the nose spends while
                                          # cancelling 1 mm, 8 Hz tremor (SIM-calibrated on HW1 autowrite runs, tuning writer
                                          # 100, seed 300, prototype nose: mostly 30-2000 Hz, from ball-friction reversals
                                          # and HW1's stiff inner servo loop, whose gains scale with the moving mass)
    aw_q_rms: float = 1.5e-3              # m rms per axis of the nose excursion while autowriting (placeholder)
    aw_a_rms: float = 4.5                 # m/s^2 rms per axis, effective (SIM-calibrated as tremor_a_eff; the plan alone
                                          # has 1.3-1.4 m/s^2, tasks.autowrite_kinematics)
    aw_q_pk: float = 5.0e-3
    aw_a_pk: float = 12.0
    aw_ink_share: float = 0.6             # share of the time the ball is inking
    x_min: float = 6.0e-3                 # guaranteed travel over 35-75 deg (m)


def _t(x):
    return x if torch.is_tensor(x) else torch.tensor(float(x), dtype=DT)


# ------------------------------------------------------------------ front end (smooth fits of frontend.sweep, CALC)
# fitted on frontend.size over z_p 30-80 mm, X 3-9 mm (max errors: R 0.15 mm, ratio 0.002, bore 0.08 mm, slide 2.1 mm)
FE_R = [4.88239, 0.7411, -0.00507, 0.00209, -0.42053, -5.51044]
FE_RATIO = [0.99591, -0.00345, 5e-05, 1e-05, -2.3803, -0.31751]
FE_BORE = [4.23399, 0.91094, -0.00107, 0.00045, 10.56802, -12.48206]
FE_SLIDE = [15.75968, -0.13184, -0.08045, 0.02167, -481.03213, 132.63973]
FE_BACK = [2.68409, 0.71302, -0.00241, 0.00082, 14.31574, -10.26169]     # backward slide of the refill (mm), max err 0.15 mm

# the refill and its channel (ASSUMPTION unless noted): the D1 refill (67 mm, DEC-004) reaches back to its end plus its
# backward slide (FE_BACK) plus a 6 mm holder; the moving nose must carry it there.  Behind the actuator it runs in a
# thin titanium channel tube (4.0 / 3.4 mm) that swings with the nose; through an axial-gap actuator it needs a central
# hole (the pole units move outward by the hole).  The pen lift (brake + latch, 2 g) sits just behind the gimbal and
# the refill spring and holder (0.5 g) at the refill's rear end.
REFILL_L = 0.067
HOLDER_L = 0.006
R_CH = 2.0e-3
LIN_CH = RHO_TI * math.pi / 4 * (0.0040 ** 2 - 0.0034 ** 2)          # kg/m
M_REAR = 0.5e-3
M_LIFT = 2.0e-3
Z_LIFT = 0.005                                                        # behind the gimbal


def _fe(c, X_mm, zp_mm):
    return c[0] + c[1] * X_mm + c[2] * zp_mm + c[3] * X_mm * zp_mm + c[4] / zp_mm + c[5] * X_mm / zp_mm


def front_end(X, z_p) -> Dict[str, torch.Tensor]:
    Xm, zm = X * 1e3, z_p * 1e3
    return {"R": _fe(FE_R, Xm, zm) * 1e-3, "ratio_min": _fe(FE_RATIO, Xm, zm), "sleeve_bore_r": _fe(FE_BORE, Xm, zm) * 1e-3,
            "slide": _fe(FE_SLIDE, Xm, zm) * 1e-3,
            "z_end": REFILL_L + _fe(FE_BACK, Xm, zm) * 1e-3 + HOLDER_L}


# ------------------------------------------------------------------ magnetics (surrogates of magnetics.py, CALC)
ETA_RADIAL = [-1.7353, -0.96439, -0.24714, 0.45927, -0.22936, -0.02979, -0.01594, 0.20621, -0.02946, -0.43524, -0.16894]
ETA_AXIAL = [-3.00529, -2.24347, -0.49465, 1.68934, -0.33866, -0.02079, -0.16821, 1.25248, 0.01892]


def eta_radial(w, l, t_m, G, t_c):
    x = torch.log(G / w); y = torch.log(t_m / w); z = torch.log(w / l); u = t_c / G
    c = ETA_RADIAL
    return torch.exp(c[0] + c[1] * x + c[2] * y + c[3] * u + c[4] * x * x + c[5] * y * y + c[6] * x * y + c[7] * x * u
                     + c[8] * y * u + c[9] * z + c[10] * x * z)


def eta_axial(a, t_m, G, t_c):
    x = torch.log(G / a); y = torch.log(t_m / a); u = t_c / G
    c = ETA_AXIAL
    return torch.exp(c[0] + c[1] * x + c[2] * y + c[3] * u + c[4] * x * x + c[5] * y * y + c[6] * x * y + c[7] * x * u
                     + c[8] * y * u)


def gap_flux(kind, B_r, t_m, g, t_c, w, l):
    G = g + t_c
    ideal = B_r * t_m / (t_m + G)
    if kind == "radial":
        return ideal * eta_radial(w, l, t_m, G, t_c)
    return ideal * eta_axial(w, t_m, G, t_c)


# ------------------------------------------------------------------ building blocks
def flexure(parts: Parts, b, L_f, alpha_u, alpha_s):
    """Cross-strip 2-axis gimbal: rotational stiffness per axis, strains at the usable travel and at the stop."""
    E, eps_f, eps_y, rho, _ = FLEXURES[parts.flexure]
    t = parts.t_flex
    k_r = E * b * t ** 3 / (6.0 * L_f)
    eps_u = t * alpha_u / L_f
    eps_s = t * alpha_s / L_f
    # the axial refill force (0.15 N) reaches the handle through the gimbal; in a cross-strip pivot one strip of a pair is
    # in compression: Euler buckling with both ends clamped (effective length L_f / 2)
    P_cr = math.pi ** 2 * E * b * t ** 3 / 12.0 / (0.5 * L_f) ** 2
    return {"k_r": k_r, "eps_u": eps_u, "eps_s": eps_s, "eps_f_allow": eps_f / FAT_SF, "eps_s_allow": eps_y / 1.2,
            "P_cr": P_cr, "mass": 4 * rho * b * t * L_f * 2.0 + 0.8e-3}       # four strips + a 0.8 g frame (ASSUMPTION)


def nose_inertia(z_p, L_b, m_act, r_act_extra=0.0, z_end=None):
    """Moving nose about the pivot (kg m^2) and its centre-of-mass offset (m, + behind the pivot).  Carrier tube,
    refill, nozzle, arm, actuator; the pen lift behind the gimbal; the refill channel from the actuator to the refill's
    rearmost end (z_end) when that lies behind the actuator, and the refill spring and holder there."""
    L_t = z_p - 0.004
    m_tube = RHO_TI * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * L_t
    m_arm = RHO_AL * math.pi / 4 * 0.005 ** 2 * L_b
    items = [(m_tube, -(z_p - L_t / 2), L_t), (0.84e-3, 0.0345 - z_p, 0.067), (0.4e-3, 0.004 - z_p, 0.0),
             (m_arm, L_b / 2, L_b), (m_act, L_b, 0.0), (M_LIFT, Z_LIFT, 0.0)]
    if z_end is not None:
        L_ch = torch.clamp(z_end - z_p - L_b, min=0.0)
        items += [(LIN_CH * L_ch, L_b + L_ch / 2, L_ch), (M_REAR, torch.maximum(z_end - z_p, L_b + 0.0 * L_ch), 0.0)]
    I = sum(m * (r * r + (Lr * Lr / 12.0 if (torch.is_tensor(Lr) or Lr) else 0.0)) for m, r, Lr in items) + m_act * r_act_extra ** 2
    m = sum(m for m, _, _ in items)
    d_cm = sum(m_ * r for m_, r, _ in items) / m
    return I, m, d_cm, m_tube + 0.84e-3 + 0.4e-3


def arm_mode(L_b, m_act, d_arm=0.005):
    """First bending mode of the rear arm carrying the magnets (cantilever from the gimbal, CALC)."""
    I_a = math.pi / 64 * d_arm ** 4
    m_arm = RHO_AL * math.pi / 4 * d_arm ** 2 * L_b
    k = 3 * E_AL * I_a / L_b ** 3
    return torch.sqrt(k / (m_act + 0.24 * m_arm)) / (2 * math.pi)


def carrier_mode(z_p):
    I_a = math.pi / 64 * (0.007 ** 4 - 0.006 ** 4)
    L = z_p - 0.005
    m_tube = RHO_TI * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * L
    k = 3 * E_TI * I_a / L ** 3
    return torch.sqrt(k / (1.3e-3 + 0.24 * m_tube)) / (2 * math.pi)


def duty_forces(m_eff, k_tip, F_grav, duty: Duty, add_tremor=True):
    """Per-axis rms and peak tip force.
    tremor duty (writing with the stabiliser on): the nose moves duty.tremor_x_rms at duty.tremor_f and drags the ball
      while inking (Coulomb drag mu_b N_b in a rotating direction: per-axis rms mu_b N_b / sqrt(2), inking share);
    autowrite duty: the planner's nose kinematics (inertia, suspension spring), the same ball drag, gravity from the
      nose's centre-of-mass offset, and the tremor inertia on top (writing with 1 mm rms of hand tremor)."""
    w = 2 * math.pi * duty.tremor_f
    drag2 = duty.aw_ink_share * (MU_BALL * N_BALL) ** 2 / 2.0
    Ftr = torch.sqrt((m_eff * duty.tremor_a_eff) ** 2 + (k_tip * duty.tremor_x_rms) ** 2 + drag2 + F_grav ** 2)
    Faw = torch.sqrt((m_eff * duty.aw_a_rms) ** 2 + (k_tip * duty.aw_q_rms) ** 2 + drag2 + F_grav ** 2
                     + ((m_eff * duty.tremor_a_eff) ** 2 if add_tremor else 0.0))
    Fpk = m_eff * (duty.aw_a_pk + w * w * 2.0e-3) + k_tip * duty.x_min + MU_BALL * N_BALL + F_grav
    return Ftr, Faw, Fpk


# ------------------------------------------------------------------ actuators
def act_unit(parts: Parts, topology: str, w, l, t_m, t_c, s, r_u=None, g_extra=None, s_far=None, r_hole=None):
    """Two topologies, both with two coil sets per axis in push-pull (CALC).

    radial   four pole pairs on the faces of a square soft-iron hub (poles N | S of width w side by side across the
             force direction, length l along the pen), each facing a flat racetrack coil (one leg over each pole) backed
             by the soft-iron shell.  Own-axis motion slides the poles across the legs: leg width b = w - 2 s.
             Other-axis motion moves the pole toward its coil: the gap clears the stroke at the magnet's far end
             (s_far = alpha (L_b + l / 2)), so g = clearance + s_far.
    axial    a checkerboard of four square poles (side w) on a soft-iron disc across the pen axis, facing two stacked coil
             layers (x and y) on a soft-iron plate.  Each layer has two racetrack coils with one leg over each pole of a
             row (x) or a column (y).  Motion along either axis slides the poles parallel to the coils, so the gap does
             not grow; each active leg is (w - 2 s) square (stays over its pole in both directions).  The mean gap of
             the two layers is clearance + t_c / 2 (+ g_extra: tilt of a flat plate at the disc rim).
    Km per axis = sqrt(2) B sqrt(k_fill V_leg phi / rho_Cu), phi = active share of the winding length.  CALC."""
    s_far = s if s_far is None else s_far
    b = torch.clamp(w - 2 * s, min=0.4e-3)
    if topology == "radial":
        g = G_CLEAR + s_far
        phi = 0.8
        B = gap_flux("radial", parts.B_r, t_m, g, t_c, w, l)
        V_leg = 2 * b * l * t_c                                          # two legs per coil, one coil per face
        m_mag = 4 * 2 * RHO_MAG * w * l * t_m
        m_cu = RHO_CU * parts.k_fill * 4 * 2 * (b + 0.3e-3) * (l + 2 * w) * t_c
        tl = t_c
    else:
        g = G_CLEAR + 0.5 * t_c + (g_extra if g_extra is not None else 0.0)
        la = torch.clamp(w - 2 * s, min=0.4e-3)                         # active leg length (other axis slides along it)
        phi = 0.8 * la / w
        B = gap_flux("axial", parts.B_r, t_m, g, t_c, w, w)
        V_leg = 2 * b * la * t_c                                         # two legs per coil, two coils per axis
        m_mag = 4 * RHO_MAG * w * w * t_m
        m_cu = RHO_CU * parts.k_fill * 4 * 2 * (b + 0.3e-3) * (2 * w) * t_c
        tl = 2 * t_c
    Km = math.sqrt(2.0) * B * torch.sqrt(parts.k_fill * V_leg * phi / RES_CU)
    Bsat, rho_bi, _ = BACK_IRON[parts.iron]
    t_bi = torch.clamp(B * w / Bsat + 0.3e-3, min=0.5e-3)               # carries one pole's flux sideways
    if topology == "radial":
        hub = torch.clamp(2 * w, min=2 * R_CH + 1.5e-3)                  # square hub, one pole pair per face; the refill
                                                                        # channel passes through it
        m_move = m_mag + RHO_FE * hub * hub * l * 0.6 + 0.4e-3
        r_out = hub / 2 + t_m + g + t_c + t_bi
        length = l + 3e-3
        m_bi = rho_bi * 2 * math.pi * (r_out - t_bi / 2) * t_bi * length
        r_extra = hub / 2 + t_m / 2
        geom = torch.zeros((), dtype=DT)
    else:
        # 2w x 2w checkerboard in a disc; with a central hole for the refill channel the four pole units move outward
        # by the hole's radius (ASSUMPTION: same flux per unit)
        rh = r_hole if r_hole is not None else torch.zeros((), dtype=DT)
        r_disc = w * math.sqrt(2.0) + 0.5e-3 + rh
        m_move = m_mag + rho_bi * math.pi * (r_disc ** 2 - rh ** 2) * t_bi + 0.3e-3
        r_out = r_disc + s + 0.5e-3                                     # the disc swings by s over the coil plate
        length = t_bi + t_m + (G_CLEAR + (g_extra if g_extra is not None else 0.0)) + tl + t_bi
        m_bi = rho_bi * math.pi * r_out ** 2 * t_bi
        r_extra = r_disc * 0.5
        geom = torch.zeros((), dtype=DT)
    geom = geom + torch.relu(0.6e-3 - (w - 2 * s)) / 1e-4                # an active leg must remain
    return {"Km": Km, "B": B, "g": g, "b_leg": b, "m_move": m_move, "m_stat": m_cu + m_bi, "r_out": r_out, "len": length,
            "r_act_extra": r_extra, "geom": geom, "phi": phi, "cap_depth": t_m + t_bi}


def act_radial(parts, w, l, t_m, t_c, s, s_far=None):
    return act_unit(parts, "radial", w, l, t_m, t_c, s, s_far=s_far)


def act_axial(parts, w, l, t_m, t_c, s, r_u, g_extra, r_hole=None):
    return act_unit(parts, "axial", w, l, t_m, t_c, s, r_u, g_extra, r_hole=r_hole)


def revh_as_designed(B_r: float = 1.33) -> Dict[str, float]:
    """The Rev H actuator (3.0 x 6.5 x 2.8 mm magnets, 1.43 mm coils, 2.27 mm stroke) with its own lumped formula, and
    with the gap flux replaced by the magpylib image calculation (CALC).  The Rev H formula takes eta_leak 0.55."""
    w, l, t_m, t_c, s = 3.0e-3, 6.5e-3, 2.8e-3, 1.43e-3, 2.27e-3
    G = G_CLEAR + s + t_c
    B_lumped = 0.55 * B_r * t_m / (t_m + G)
    eta = float(eta_radial(_t(w), _t(l), _t(t_m), _t(G), _t(t_c)))
    B_img = B_r * t_m / (t_m + G) * eta
    V = 2 * w * l * t_c
    Km_l = math.sqrt(2) * 0.8 * B_lumped * math.sqrt(0.6 * V / RES_CU)
    Km_i = math.sqrt(2) * 0.8 * B_img * math.sqrt(0.6 * V / RES_CU)
    return {"B_lumped_T": B_lumped, "B_images_T": B_img, "eta_images": eta, "Km_act_lumped": Km_l, "Km_act_images": Km_i,
            "Km_tip_lumped": Km_l / 1.324, "Km_tip_images": Km_i / 1.324}


# ------------------------------------------------------------------ candidates
VAR_BOUNDS = {
    "gimbal_radial": {"z_p": (0.030, 0.080), "L_b": (0.004, 0.050), "w": (1.5e-3, 8e-3), "l": (3e-3, 16e-3),
                      "t_m": (1.0e-3, 5e-3), "t_c": (0.6e-3, 3.0e-3), "b_f": (1.0e-3, 5e-3), "L_f": (2e-3, 12e-3)},
    "gimbal_axial": {"z_p": (0.030, 0.080), "L_b": (0.006, 0.050), "w": (2e-3, 7e-3), "l": (2e-3, 9e-3),
                     "t_m": (1.0e-3, 4e-3), "t_c": (0.4e-3, 2.0e-3), "b_f": (1.0e-3, 5e-3), "L_f": (2e-3, 12e-3)},
    "dual_plane": {"z_1": (0.022, 0.040), "z_2": (0.060, 0.100), "z_v": (0.030, 0.30), "w": (1.5e-3, 6e-3),
                   "l": (3e-3, 10e-3), "t_m": (1.0e-3, 3e-3), "t_c": (0.6e-3, 2.0e-3), "b_f": (1.0e-3, 5e-3), "L_f": (2e-3, 12e-3)},
    "xy_wire": {"L_w": (0.015, 0.060), "d_w": (0.05e-3, 0.30e-3), "w": (2e-3, 7e-3), "l": (2e-3, 9e-3),
                "t_m": (1.0e-3, 4e-3), "t_c": (0.4e-3, 2.0e-3)},
}
VAR_BOUNDS["gimbal_sphere"] = dict(VAR_BOUNDS["gimbal_axial"])
VAR_BOUNDS["coarse_fine"] = dict(VAR_BOUNDS["gimbal_axial"])


def evaluate(kind: str, v: Dict[str, torch.Tensor], parts: Parts, duty: Duty, servo_hz: float = 80.0) -> Dict[str, torch.Tensor]:
    """All metrics of one design (tensors).  Penalties (>= 0) in out['pen'] are zero for a feasible design."""
    if kind in ("gimbal_radial", "gimbal_axial", "gimbal_sphere", "coarse_fine"):
        return _gimbal(kind, v, parts, duty, servo_hz)
    if kind == "dual_plane":
        return _dual(v, parts, duty, servo_hz)
    if kind == "xy_wire":
        return _xy(v, parts, duty, servo_hz)
    raise ValueError(kind)


def _common_out(out, parts, duty, servo_hz, bore_need, f_modes):
    """Constraint penalties shared by the candidates."""
    R_bore = BORE_R[parts.bore]
    pen = {
        "travel": torch.relu(duty.x_min - out["X_min"]) / 1e-4,
        "bore": torch.relu(bore_need - R_bore) / 1e-4,
        "modes": torch.relu(3.0 * servo_hz - f_modes) / 10.0,
        "peak": torch.relu(out["F_pk_tip_need"] - out["F_pk_tip"]) / 0.01,
        "fatigue": torch.relu(out["eps_u"] - out["eps_f_allow"]) / 1e-4 + torch.relu(out["eps_s"] - out["eps_s_allow"]) / 1e-4,
        "buckling": torch.relu(BUCKLE_SF * F_REFILL - out["P_cr"]) / 0.01 if "P_cr" in out else torch.zeros((), dtype=DT),
        "heat": torch.relu(out["dT_coil"] - DT_COIL_MAX) / 1.0,
        "length": torch.relu(out["z_a"] + out["len_act"] / 2 - Z_ACT_MAX) / 1e-4 if torch.isfinite(out["z_a"]) else torch.zeros((), dtype=DT),
        "geom": out.get("geom_pen", torch.zeros((), dtype=DT)),
    }
    out["pen_terms"] = pen
    out["pen"] = sum(p ** 2 for p in pen.values())
    out["servo_hz_max"] = f_modes / 3.0
    return out


def nominal_travel(x_min, z_p):
    """Nominal travel (at 50 deg) whose minimum over 35-75 deg and all directions equals x_min (two fixed-point steps
    on the front-end fit)."""
    X = x_min / 0.9
    for _ in range(3):
        X = x_min / front_end(X, z_p)["ratio_min"]
    return X


def _gimbal(kind, v, parts, duty, servo_hz):
    z_p, L_b = v["z_p"], v["L_b"]
    X = nominal_travel(torch.as_tensor(duty.x_min, dtype=DT), z_p) if "X" not in v else v["X"]
    alpha_u = X / z_p
    alpha_s = (X + 0.5e-3) / z_p
    s = alpha_s * L_b                                                   # actuator stroke at the stop
    fe = front_end(X, z_p)
    z_end = fe["z_end"]
    if kind == "gimbal_radial":
        A = act_radial(parts, v["w"], v["l"], v["t_m"], v["t_c"], s, s_far=alpha_s * (L_b + v["l"] / 2))
        # the magnets start behind the gimbal (1.5 mm half-length + 1.5 mm clearance)
        geom_pen = A["geom"] + torch.relu(3.0e-3 - (L_b - v["l"] / 2)) / 1e-4
        z_act_back = z_p + L_b - v["l"] / 2                             # the hub's front face (the channel runs through it)
    else:
        # flat coil plate (C1+): the disc's tilt opens the gap at its rim; spherical faces (C1S, and C3's coarse stage)
        # keep it constant
        g_extra = torch.zeros((), dtype=DT) if kind in ("gimbal_sphere", "coarse_fine") else (v["w"] * math.sqrt(2.0)) * alpha_s
        # the refill channel passes through the cap and the coil plate when the refill's holder reaches within 0.5 mm of
        # the cap's front face (magnet face at z_a, back iron in front of it); the plate's hole also clears the channel's
        # swing there (the stroke s).  The cap depth is taken from a first evaluation without the hole.
        A0 = act_axial(parts, v["w"], v["l"], v["t_m"], v["t_c"], s, None, g_extra)
        cap_front = z_p + L_b - A0["cap_depth"]
        through = torch.sigmoid((z_end + 0.5e-3 - cap_front) / 0.3e-3)
        r_hole = through * (R_CH + s + 0.3e-3)
        A = act_axial(parts, v["w"], v["l"], v["t_m"], v["t_c"], s, None, g_extra, r_hole=r_hole)
        geom_pen = A["geom"] + torch.relu(3.0e-3 + 0.5 * A["len"] - L_b) / 1e-4
        z_act_back = cap_front
    fl = flexure(parts, v["b_f"], v["L_f"], alpha_u, alpha_s)
    I, m_nose, d_cm, m_front = nose_inertia(z_p, L_b, A["m_move"], A["r_act_extra"], z_end=z_end)
    m_eff = I / z_p ** 2
    k_tip = fl["k_r"] / z_p ** 2
    lam = L_b / z_p                                                     # actuator motion per tip motion
    Km_tip = A["Km"] * lam
    F_grav = (m_nose * G0 * torch.abs(d_cm) * math.cos(THETA)) / z_p     # gravity torque across the axis, tip-referred
    Ftr, Faw, Fpk_need = duty_forces(m_eff, k_tip, F_grav, duty)
    P_tr = 2 * (Ftr / Km_tip) ** 2
    P_aw = 2 * (Faw / Km_tip) ** 2
    F_pk_tip = A["Km"] * math.sqrt(V_BUS * I_PEAK) * lam
    f_modes = torch.minimum(arm_mode(L_b, A["m_move"]), carrier_mode(z_p))
    out = {"X_nom": X, "X_min": X * fe["ratio_min"], "z_p": z_p, "z_a": z_p + L_b, "stroke_act": s, "B_gap": A["B"], "gap": A["g"],
           "Km_act": A["Km"], "Km_tip": Km_tip, "lever_tip_per_act": 1.0 / lam, "m_eff_tip": m_eff, "k_tip": k_tip,
           "m_nose": m_nose, "d_cm": d_cm, "F_grav_tip": F_grav, "F_tr_rms": Ftr, "F_aw_rms": Faw, "P_tremor": P_tr, "P_autowrite": P_aw,
           "F_pk_tip": F_pk_tip, "F_pk_tip_need": Fpk_need, "f_parasitic": f_modes,
           "mass_added": A["m_move"] + A["m_stat"] + fl["mass"], "m_act_move": A["m_move"], "m_act_stat": A["m_stat"],
           "r_act": A["r_out"], "len_act": A["len"], "eps_u": fl["eps_u"], "eps_s": fl["eps_s"], "eps_f_allow": fl["eps_f_allow"],
           "eps_s_allow": fl["eps_s_allow"], "k_r": fl["k_r"], "P_cr": fl["P_cr"], "front_R": fe["R"], "front_bore_r": fe["sleeve_bore_r"],
           "refill_slide": fe["slide"], "dT_coil": P_aw * R_TH_COIL, "reaction_rms": torch.sqrt(Faw ** 2)}
    # envelope: the actuator's radial build (+ its swing for the axial disc), the carrier's swing at the gimbal, and the
    # refill channel's swing behind the actuator
    swing_rear = alpha_s * torch.clamp(z_end - z_p, min=0.0) + R_CH + 0.3e-3
    bore_need = torch.maximum(torch.maximum(A["r_out"], fe["sleeve_bore_r"] + 1e-3), swing_rear)
    out["z_end"] = z_end
    out["refill_through_actuator"] = (z_end > z_act_back).to(DT) if torch.is_tensor(z_end) else torch.tensor(float(z_end > z_act_back))
    out["swing_rear"] = swing_rear
    if kind == "coarse_fine":
        out = _add_fine(out, parts, duty)
    out["geom_pen"] = geom_pen
    return _common_out(out, parts, duty, servo_hz, bore_need, f_modes)


def _add_fine(out, parts, duty):
    """Fine stage (C3): a +-1 mm moving-magnet stage at the carrier front moving the refill's front guide; the coarse
    gimbal no longer carries the tremor duty.  Fine stage (ASSUMPTION, order-of-magnitude values for a 2 x 2 x 1 mm
    magnet in a 0.5 mm gap): 0.25 g moving at the tip, Km 0.05 N/sqrt(W) at the tip, +1.0 mm on the carrier radius at
    the front (the front end grows: front_R + 1 mm), 1.5 g added."""
    Km_f = 0.05
    m_f = 0.25e-3
    # the coarse stage no longer sees the tremor inertia in autowrite (the fine stage takes it); the fine stage drags the
    # ball while cancelling tremor, the coarse stage while drawing: count the drag once, on the coarse stage
    Faw_nt = torch.sqrt(torch.clamp(out["F_aw_rms"] ** 2 - (out["m_eff_tip"] * duty.tremor_a_eff) ** 2, min=1e-12))
    P_f = 2 * ((m_f * duty.tremor_a_eff) / Km_f) ** 2
    out["P_autowrite"] = 2 * (Faw_nt / out["Km_tip"]) ** 2 + P_f
    out["P_tremor"] = torch.tensor(P_f, dtype=DT)
    out["dT_coil"] = out["P_autowrite"] * R_TH_COIL                    # both stages' copper in the same shell (conservative)
    out["front_R"] = out["front_R"] + 1.0e-3
    out["mass_added"] = out["mass_added"] + 1.5e-3
    out["fine_travel"] = torch.tensor(1.0e-3, dtype=DT)
    return out


def _dual(v, parts, duty, servo_hz):
    """Two actuation planes (radial-gap units around the carrier at z_1 and around the rear arm at z_2), the carrier on
    two flexure planes; virtual pivot at z_v (tip motion = rotation about z_v).  Minimum-power force split:
    Km_tip^2 = sum lambda_i^2 Km_i^2 with lambda_i = |z_v - z_i| / z_v."""
    z1, z2, zv = v["z_1"], v["z_2"], v["z_v"]
    X = nominal_travel(torch.as_tensor(duty.x_min, dtype=DT), torch.clamp(zv, max=0.08)) if "X" not in v else v["X"]
    lam1 = torch.abs(zv - z1) / zv
    lam2 = torch.abs(zv - z2) / zv
    alpha_s = (X + 0.5e-3) / zv
    s1 = lam1 * (X + 0.5e-3)
    s2 = lam2 * (X + 0.5e-3)
    A1 = act_radial(parts, v["w"], v["l"], v["t_m"], v["t_c"], s1, s_far=s1 + alpha_s * v["l"] / 2)
    A2 = act_radial(parts, v["w"], v["l"], v["t_m"], v["t_c"], s2, s_far=s2 + alpha_s * v["l"] / 2)
    # the front units sit around the 7 mm carrier: their hub is the carrier (radius 3.5 mm) instead of a 5 mm hub
    r1 = 3.5e-3 + v["t_m"] + A1["g"] + v["t_c"] + 0.8e-3
    Km_tip = torch.sqrt(lam1 ** 2 * A1["Km"] ** 2 + lam2 ** 2 * A2["Km"] ** 2)
    # inertia: carrier + refill + nozzle between 0 and z1.., arm to z2 with the rear magnets, front magnets at z1
    L_t = z2 - 0.004
    m_tube = RHO_TI * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * L_t
    fe0 = front_end(X, torch.clamp(zv, max=0.08))
    z_end = fe0["z_end"]
    L_ch = torch.clamp(z_end - z2, min=0.0)
    items = [(m_tube, 0.004 + L_t / 2, L_t), (0.84e-3, 0.0345, 0.067), (0.4e-3, 0.004, 0.0), (A1["m_move"], z1, 0.0),
             (A2["m_move"], z2, 0.0), (M_LIFT, z1 + Z_LIFT, 0.0), (LIN_CH * L_ch, z2 + L_ch / 2, L_ch),
             (M_REAR, torch.maximum(z_end, z2), 0.0)]
    I_v = sum(m * ((z - zv) ** 2 + (Lr * Lr / 12.0 if (torch.is_tensor(Lr) or Lr) else 0.0)) for m, z, Lr in items)
    m_nose = sum(m for m, _, _ in items)
    m_eff = I_v / zv ** 2
    fl = flexure(parts, v["b_f"], v["L_f"], X / zv, alpha_s)
    k_tip = 2 * fl["k_r"] / zv ** 2 + 2 * 50.0 * lam1 ** 2       # two flexure planes; + lateral spring (ASSUMPTION 50 N/m)
    d_cm = sum(m * z for m, z, _ in items) / m_nose - zv
    F_grav = m_nose * G0 * torch.abs(d_cm) * math.cos(THETA) / zv
    Ftr, Faw, Fpk_need = duty_forces(m_eff, k_tip, F_grav, duty)
    fe = front_end(X, torch.clamp(zv, max=0.08))
    P_tr = 2 * (Ftr / Km_tip) ** 2
    P_aw = 2 * (Faw / Km_tip) ** 2
    F_pk_tip = math.sqrt(V_BUS * I_PEAK) * Km_tip
    f_modes = torch.minimum(carrier_mode(z1 + 0.01), torch.tensor(600.0, dtype=DT))
    out = {"X_nom": X, "X_min": X * fe["ratio_min"], "z_p": zv, "z_a": z2, "stroke_act": torch.maximum(s1, s2), "B_gap": A2["B"],
           "gap": A2["g"], "Km_act": A2["Km"], "Km_tip": Km_tip, "lever_tip_per_act": 1.0 / lam2, "m_eff_tip": m_eff, "k_tip": k_tip,
           "m_nose": m_nose, "d_cm": d_cm, "F_grav_tip": F_grav, "F_tr_rms": Ftr, "F_aw_rms": Faw, "P_tremor": P_tr,
           "P_autowrite": P_aw, "F_pk_tip": F_pk_tip, "F_pk_tip_need": Fpk_need, "f_parasitic": f_modes,
           "mass_added": A1["m_move"] + A1["m_stat"] + A2["m_move"] + A2["m_stat"] + 2 * fl["mass"],
           "m_act_move": A1["m_move"] + A2["m_move"], "m_act_stat": A1["m_stat"] + A2["m_stat"], "r_act": torch.maximum(r1, A2["r_out"]),
           "r_act_front": r1, "len_act": A1["len"] + A2["len"], "eps_u": fl["eps_u"], "eps_s": fl["eps_s"],
           "eps_f_allow": fl["eps_f_allow"], "eps_s_allow": fl["eps_s_allow"], "k_r": fl["k_r"], "P_cr": fl["P_cr"], "front_R": fe["R"],
           "front_bore_r": fe["sleeve_bore_r"], "refill_slide": fe["slide"], "dT_coil": P_aw * R_TH_COIL,
           "reaction_rms": Faw, "lam1": lam1, "lam2": lam2}
    swing_rear = alpha_s * torch.abs(z_end - zv) + R_CH + 0.3e-3
    bore_need = torch.maximum(torch.maximum(torch.maximum(r1 + s1, A2["r_out"]), fe["sleeve_bore_r"] + 1e-3), swing_rear)
    out["z_end"] = z_end
    out["swing_rear"] = swing_rear
    out["geom_pen"] = A1["geom"] + A2["geom"] + torch.relu(z1 + 0.012 - z2) / 1e-4
    return _common_out(out, parts, duty, servo_hz, bore_need, f_modes)


def _xy(v, parts, duty, servo_hz):
    """Translating carrier on four NiTi wires (fixed-guided), axial-gap actuator at the rear, no lever."""
    Lw, dw = v["L_w"], v["d_w"]
    X = torch.as_tensor(duty.x_min, dtype=DT) if "X" not in v else v["X"]
    Xs = X + 0.5e-3
    A = act_axial(parts, v["w"], v["l"], v["t_m"], v["t_c"], Xs, None, torch.zeros((), dtype=DT))
    E = FLEXURES["NiTi_superelastic"][0]
    Iw = math.pi * dw ** 4 / 64
    k_tip = 4 * 12 * E * Iw / Lw ** 3
    eps_u = 3 * dw * X / Lw ** 2
    eps_s = 3 * dw * Xs / Lw ** 2
    L_t = 0.080
    m_tube = RHO_TI * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * L_t
    m_nose = m_tube + 0.84e-3 + 0.4e-3 + A["m_move"] + 1.0e-3
    m_eff = m_nose                                                  # pure translation: all of it at the tip
    Ftr, Faw, Fpk_need = duty_forces(m_eff, k_tip, torch.zeros((), dtype=DT), duty)
    Km_tip = A["Km"]
    P_tr = 2 * (Ftr / Km_tip) ** 2
    P_aw = 2 * (Faw / Km_tip) ** 2
    fe = front_end(X, torch.tensor(0.08, dtype=DT))
    # a translating carrier needs the travel as clearance along its whole length (ball travel = X at every tilt)
    R_front = fe["R"] + 1.25e-3
    f_wire = torch.sqrt(k_tip / m_nose) / (2 * math.pi)
    f_modes = torch.tensor(400.0, dtype=DT) + 0 * f_wire            # suspension mode is controlled; parasitic ~ tube bending
    out = {"X_nom": X, "X_min": X * 1.0, "z_p": torch.tensor(float("inf"), dtype=DT), "z_a": torch.tensor(0.09, dtype=DT),
           "stroke_act": Xs, "B_gap": A["B"], "gap": A["g"], "Km_act": A["Km"], "Km_tip": Km_tip,
           "lever_tip_per_act": torch.ones((), dtype=DT), "m_eff_tip": m_eff, "k_tip": k_tip, "m_nose": m_nose,
           "d_cm": torch.zeros((), dtype=DT), "F_grav_tip": torch.zeros((), dtype=DT), "F_tr_rms": Ftr, "F_aw_rms": Faw,
           "P_tremor": P_tr, "P_autowrite": P_aw, "F_pk_tip": A["Km"] * math.sqrt(V_BUS * I_PEAK), "F_pk_tip_need": Fpk_need,
           "f_parasitic": f_modes, "f_suspension": f_wire, "mass_added": A["m_move"] + A["m_stat"] + 4 * 6.45e3 * math.pi / 4 * dw ** 2 * Lw,
           "m_act_move": A["m_move"], "m_act_stat": A["m_stat"], "r_act": A["r_out"], "len_act": A["len"], "eps_u": eps_u, "eps_s": eps_s,
           "eps_f_allow": torch.tensor(FLEXURES["NiTi_superelastic"][1] / FAT_SF, dtype=DT),
           "eps_s_allow": torch.tensor(FLEXURES["NiTi_superelastic"][2] / 1.2, dtype=DT), "k_r": k_tip,
           "front_R": R_front, "front_bore_r": 3.5e-3 + X + 0.5e-3, "refill_slide": fe["slide"], "dT_coil": P_aw * R_TH_COIL,
           "reaction_rms": Faw, "L_w": Lw}
    bore_need = torch.maximum(A["r_out"], 3.5e-3 + Xs + 0.5e-3 + 0.5e-3)     # carrier + travel + wire attachment
    out["geom_pen"] = A["geom"]
    return _common_out(out, parts, duty, servo_hz, bore_need, f_modes)


# ------------------------------------------------------------------ screening-only candidates (datasheet numbers)
def screening(duty: Duty) -> Dict[str, Dict]:
    """Galvo pair, ultrasonic piezo, SMA, Awtar-scale flexure stage: the numbers that exclude them (MFR/LIT + CALC)."""
    z_p = 0.045
    # Cambridge Technology 6210H (MFR AMF-137): torque constant 2.79e4 dyne cm/A, 3.7 ohm, 18 g, 100 us small step
    Kt = 2.79e4 * 1e-7
    Km_rot = Kt / math.sqrt(3.7)
    Km_tip = Km_rot / z_p
    F = 0.06
    galvo = {"Km_tip_N_per_sqrtW": Km_tip, "P_autowrite_W_at_0.06N": 2 * (F / Km_tip) ** 2, "mass_g": 2 * 18.0,
             "body": "Ø12.7 mm class each (62xxH drawings); two do not fit side by side in a 20 mm bore",
             "verdict": "rejected: 10x lower force per sqrt(W) at the tip than the flat-coil gimbal, 36 g", "ledger": "AMF-137"}
    # PI P-661 PILine (MFR AMF-138): 14 x 35 x 6 mm, 10 g, 2 N, 500 mm/s, 120 Vpp motor, 12 V / 5 W driver electronics
    piezo = {"mass_g": 2 * 10.0, "driver_power_W": 2 * 5.0, "speed_mm_s": 500.0, "force_N": 2.0, "backdrivable": False,
             "verdict": "rejected: 5 W per axis of driver power (the whole Rev H pen uses 0.08 W), 120 Vpp in a handheld pen, "
                        "and a self-locking friction drive cannot yield to the writer", "ledger": "AMF-138"}
    # Flexinol 0.025 mm (MFR AMF-77): cooling 0.15-0.18 s
    sma = {"cooling_s": 0.15, "bandwidth_Hz_est": 1.0 / (2 * 0.15), "verdict": "reference only: about 3 Hz, below the 4-12 Hz tremor band "
           "and the 3-7 Hz stroke rate of writing", "ledger": "AMF-77"}
    # Awtar & Parmar 2013 (LIT AMF-135): 10 x 10 mm range needs 47.5 mm beams, a 255 mm bearing, first mode 18 Hz
    awtar = {"range_mm": 10.0, "bearing_mm": 255.0, "beam_len_mm": 47.5, "first_mode_Hz": 18.0,
             "verdict": "a planar double-parallelogram XY stage at this range does not fit a pen; wire flexures (xy_wire) are the "
                        "only planar option evaluated in detail", "ledger": "AMF-135"}
    return {"galvo_pair": galvo, "ultrasonic_piezo": piezo, "sma": sma, "planar_flexure_stage": awtar}


def to_float(out: Dict) -> Dict:
    r = {}
    for k, v in out.items():
        if isinstance(v, dict):
            r[k] = to_float(v)
        elif torch.is_tensor(v):
            r[k] = float(v.detach())
        else:
            r[k] = v
    return r


# ------------------------------------------------------------------ the axial DOF (pen-up / pen-down)
MU0 = 4e-7 * math.pi


def axial_dof(lifts_per_s: float = 4.0, m_move: float = 1.2e-3, stroke: float = 0.5e-3, t_switch: float = 5e-3,
              F_spring: float = F_REFILL, d_pole: float = 3.0e-3, g_res: float = 0.1e-3, win_r: float = 1.5e-3,
              win_l: float = 4.0e-3, k_fill: float = 0.55, E_brake: float = 3e-3) -> Dict[str, float]:
    """Refill lift of the Rev J nose (CALC; every input ASSUMPTION unless noted).  While writing, a spring keeps the ball
    on the paper as in Rev H.  For a pen-up an electro-permanent brake locks the refill holder to the carrier and a
    bistable reluctance latch (soft-iron plunger, permanent-magnet detent: no holding power) lifts the refill by the
    stroke (0.5 mm: CalComp's plotter lift 0.5-0.64 mm, LIT PAT-41); for a pen-down both are released.
      force to lift      F = F_spring + m 4 s / t^2 (bang-bang over the stroke)
      pole flux density  B = sqrt(2 mu0 F / A_pole) at the largest gap s + g_res
      ampere-turns       NI = B (s + g_res) / mu0 (iron neglected)
      coil loss          P = NI^2 rho_Cu MLT / (k_fill A_window)
      energy per cycle   P t (lift) + 0.5 P t (release; detent near balance) + 2 E_brake (lock, unlock; E_brake ASSUMPTION)
    Average power = pen lifts per second x energy per cycle."""
    F = F_spring + m_move * 4.0 * stroke / t_switch ** 2
    A = math.pi * d_pole ** 2 / 4.0
    B = math.sqrt(2.0 * MU0 * F / A)
    NI = B * (stroke + g_res) / MU0
    MLT = math.pi * (d_pole + win_r)
    P = NI ** 2 * RES_CU * MLT / (k_fill * win_r * win_l)
    E = 1.5 * P * t_switch + 2.0 * E_brake
    return {"F_lift_N": F, "B_pole_T": B, "NI_At": NI, "P_pulse_W": P, "E_cycle_J": E, "lifts_per_s": lifts_per_s,
            "P_avg_W": E * lifts_per_s, "stroke_mm": stroke * 1e3, "t_switch_ms": t_switch * 1e3,
            "label": "CALC (reluctance latch + electro-permanent brake; inputs ASSUMPTION; stroke from LIT PAT-41)"}
