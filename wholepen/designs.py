r"""Task 3: the candidate whole-pen mechanisms sized (CALCULATION on PROPOSED DESIGN geometry; labelled inputs).

Every function returns a dict whose numbers are CALC unless a key ends in '_label'.  Inputs that no source backs are
ASSUMPTION and say so.  The ledger ids refer to docs/evidence.csv or results/wholepen/evidence_rows.csv.

  cmg_design     the severe-tremor gyroscopic tail module (scissored CMG pairs), 40-100 g: rotor, momentum, torque
                 capacity at 4-10 Hz (Bessel-limited gimbal swing), gimbal drive, spin and gimbal power, stored
                 energy, rim stress and burst margin, bearing speed margin, spin-up, tone, containment, gyroscopic
                 reaction to the writer's own pen rotation, singularity, module size and mass
  tmd_design     the tuned (resonant) reaction mass: stiffness per tuning, stroke, force capacity, bandwidth
                 (Den Hartog), semi-active retuning, mass
  collar_design  the pivot collar ('the pen pivots in the hand'): travel against pivot position, the saddle's size,
                 the static moment of the writing force, motor sizing and holding power, drag, pinch safety, the
                 largest safe tip travel
  paper_design   paper-grounded force: heel wheel (as built, anti-phase, brake), an omni heel, a hand-rest sled that
                 carries part of the hand's weight
  gating_design  the pen lift as an ink gate: cycles, energy, the ink it lays
  authority      the force or torque each device can make at the tremor frequency and what it does to the tip
                 (reduced linear model lin.py, H1 hand, three grip splits)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ROOT  # noqa: F401

RHO_W = 18000.0          # MFR AMF-49 (tungsten heavy alloy, ASTM B777 class 3: 18 g/cm^3)
UTS_W = 724e6            # MFR AMF-49 (>= 105 ksi)
RHO_AL = 2700.0          # aluminium (ASSUMPTION handbook value)
RHO_AIR = 1.2
BEARING_LIMIT_RPM = 85000.0   # MFR AMF-126 (SKF 618/4 limiting speed as listed)
TWO_PI = 2 * math.pi

LABELS = {
    "tail_od": "ASSUMPTION: the tail module sits behind the thumb-index web (z > 145 mm), so it may be up to 30 mm across (the held part stays <= 24 mm)",
    "hub_motor": "ASSUMPTION: an outrunner spin motor whose bell carries the tungsten ring (drone-class outrunners of 1.8-3.3 g exist: MFR AMF-79, AMF-127); no such CMG motor is catalogued",
    "friction": "CALC from MFR AMF-78 (Faulhaber 0620 B: C0 0.011 mN m, Cv 1.02e-6 mN m/rpm) x 1.5 for the heavier rotor's bearing load (ASSUMPTION)",
    "gimbal_motor": "MFR AMF-121 (Faulhaber 1226 B, 13 g, rated 2.13 mN m, stall 7.24 mN m) through a 16:1 gearhead (ASSUMPTION 0.8 efficiency): about 27 mN m continuous and 90 mN m peak at the pair; it must carry the gyroscopic reaction 2 h Omega of the writer's own pen rotation",
    "windage": "CALC: disc windage P = Cm 0.5 rho w^3 r^5 per face, Cm 0.01 (ASSUMPTION, enclosed disc)",
    "balance": "ASSUMPTION: balance grade G1 (1 mm/s) for the rotor",
}


# ================================================================================================ CMG tail module
def rotor(r_o: float, t: float, kappa: float = 0.5) -> Dict:
    m = RHO_W * math.pi * r_o ** 2 * (1 - kappa ** 2) * t
    J_s = 0.5 * m * r_o ** 2 * (1 + kappa ** 2)
    J_t = 0.25 * m * r_o ** 2 * (1 + kappa ** 2) + m * t * t / 12
    return {"r_o": r_o, "r_i": kappa * r_o, "t": t, "m": m, "J_s": J_s, "J_t": J_t}


def bessel_2J1(x: float) -> float:
    from scipy.special import j1
    return float(2 * j1(x))


def pair_torque(h: float, f: float, delta_max: float, rate_max: float) -> float:
    """Fundamental torque amplitude of one scissored pair (N m) for a sinusoidal gimbal swing at f, limited by the
    gimbal range and rate: tau = 2 h w 2 J1(delta0), delta0 = min(delta_max, rate_max / w) (CALC)."""
    w = TWO_PI * f
    d0 = min(delta_max, rate_max / w)
    return 2 * h * w * bessel_2J1(d0)


def module_mass_model(mode: str, n_pairs: int, r_o: float, length: float, own_cell: bool = False) -> Dict:
    """Fixed parts of the tail module (g), PROPOSED DESIGN masses (ASSUMPTION unless labelled)."""
    n_r = 2 * n_pairs
    parts = {
        "spin_motor_stators_bearings": 3.0 * n_r,               # hub outrunner stator + 2 x 618/4 bearings 0.7 g (AMF-126)
        "gimbal_frames_bearings": 2.0 * n_r,
        "gimbal_motor_gearhead_scissor_gears": 16.0 * n_pairs,  # AMF-121 1226 B 13 g + 16:1 gearhead ~2 g + gears 1 g
        "turret_motor": 2.5 if mode == "turret" else 0.0,
        "electronics": 3.0,
    }
    od = 2 * (r_o + 1.8e-3)
    wall = 0.8e-3
    shell = RHO_AL * math.pi * od * wall * length + 2 * RHO_AL * math.pi * (od / 2) ** 2 * wall
    parts["housing_containment_al"] = shell * 1e3
    if own_cell:
        parts["cell_14250"] = 10.0                              # ASSUMPTION: a 1/2 AA Li-ion cell (about 1.1 Wh)
    return {"parts_g": parts, "fixed_g": float(sum(parts.values())), "od_mm": od * 1e3}


def cmg_design(total_g: float, mode: str = "turret", rpm: float = 25000.0, delta_max: float = 1.0,
               rate_max: float = 60.0, r_o_max: float = 12.5e-3, kappa: float = 0.5, own_cell: bool = False,
               freqs: Sequence[float] = (4.0, 5.0, 6.0, 8.0, 10.0)) -> Dict:
    """Size the tail module for a total mass: the rotors take what the fixed parts leave (iterating on the module
    length, which depends on the rotor's swing slot)."""
    n_pairs = 1 if mode == "turret" else 2
    n_r = 2 * n_pairs
    L = 0.05
    for _ in range(20):
        mm = module_mass_model(mode, n_pairs, r_o_max, L, own_cell)
        m_rot = max((total_g - mm["fixed_g"]) / n_r, 0.0) * 1e-3
        r_o = r_o_max
        t = m_rot / (RHO_W * math.pi * r_o ** 2 * (1 - kappa ** 2)) if m_rot > 0 else 0.0
        if t > 0 and t < 1.0e-3:                                 # parts >= 1 mm thick (study K's rule): shrink the radius
            t = 1.0e-3
            r_o = math.sqrt(m_rot / (RHO_W * math.pi * (1 - kappa ** 2) * t))
        d = min(1.25 * delta_max, math.pi / 2)
        slot = 2 * (r_o * math.sin(d) + 0.5 * t * math.cos(d)) + 1.0e-3
        L_new = n_r * slot + 0.012
        if abs(L_new - L) < 1e-5:
            break
        L = L_new
    if m_rot <= 0:
        return {"total_g": total_g, "mode": mode, "feasible": False, "fixed_g": mm["fixed_g"]}
    ro = rotor(r_o, t, kappa)
    w_s = rpm * TWO_PI / 60
    h = ro["J_s"] * w_s
    J_g = ro["J_t"] + 3.0e-7                                     # + gimbal frame (ASSUMPTION)
    torque = {f: pair_torque(h, f, delta_max, rate_max) * n_pairs ** 0 for f in freqs}
    # gimbal drive (per pair, through the scissor gears): inertia + the gyroscopic reaction of the writer's own
    # rotation of the pen about the output axis (2 h Omega; Omega 1.5 rad/s in tremor, 3 rad/s in fast writing: ASSUMPTION)
    f_ref = 5.0
    d0 = min(delta_max, rate_max / (TWO_PI * f_ref))
    tq_inertia = 2 * J_g * d0 * (TWO_PI * f_ref) ** 2
    tq_gyro = {om: 2 * h * om for om in (1.5, 3.0)}
    # spin power per rotor: motor friction (C0 + Cv n) x 1.5 + windage (two faces)
    C0, Cv = 0.011e-3, 1.02e-9
    P_fric = 1.5 * (C0 + Cv * rpm) * w_s
    P_wind = 2 * 0.01 * 0.5 * RHO_AIR * w_s ** 3 * r_o ** 5
    P_spin = n_r * (P_fric + P_wind) / 0.8                       # driver efficiency 0.8 (ASSUMPTION)
    E = n_r * 0.5 * ro["J_s"] * w_s ** 2
    v_rim = w_s * r_o
    sigma = RHO_W * v_rim ** 2
    burst_rpm = math.sqrt(UTS_W / RHO_W) / r_o * 60 / TWO_PI
    tone = rpm / 60
    e_bal = 1.0e-3 / w_s                                        # G1: e w = 1 mm/s
    F_unbal = ro["m"] * e_bal * w_s ** 2
    spinup_s = ro["J_s"] * w_s / 1.5e-3                         # 1.5 mN m outrunner torque (ASSUMPTION)
    # a seized bearing: the rotor's momentum h leaves in ~10 ms (ASSUMPTION) -> torque pulse on the pen
    seize_Nm = h / 0.010
    out = {
        "total_g": total_g, "mode": mode, "n_pairs": n_pairs, "n_rotors": n_r, "feasible": True, "rpm": rpm,
        "fixed_g": mm["fixed_g"], "fixed_parts_g": mm["parts_g"], "od_mm": mm["od_mm"], "length_mm": L * 1e3,
        "rotor_g": ro["m"] * 1e3, "rotor_r_o_mm": r_o * 1e3, "rotor_r_i_mm": ro["r_i"] * 1e3, "rotor_t_mm": t * 1e3,
        "J_s": ro["J_s"], "J_g": J_g, "h_Nms": h, "h_total_Nms": n_r * h,
        "torque_Nm": {str(f): v for f, v in torque.items()},
        "delta_max_rad": delta_max, "rate_max_rad_s": rate_max,
        "gimbal_torque_inertia_mNm_5Hz": tq_inertia * 1e3, "gimbal_torque_gyro_mNm": {str(k): v * 1e3 for k, v in tq_gyro.items()},
        "P_spin_W": P_spin, "E_stored_J": E, "v_rim_m_s": v_rim, "hoop_stress_MPa": sigma / 1e6,
        "stress_margin": UTS_W / sigma, "burst_rpm": burst_rpm, "bearing_margin": BEARING_LIMIT_RPM / rpm,
        "tone_Hz": tone, "unbalance_force_N": F_unbal, "spinup_s": spinup_s, "seize_torque_pulse_Nm": seize_Nm,
        "labels": LABELS,
    }
    return out


def cmg_power(gt_kwargs: Dict, mech_W: float, active: bool = True) -> Dict:
    """Electrical power of a simulated tail module (CALC on SIM): spin (designs model) + gimbal (mechanical power
    from the simulation / 0.5 motor-and-gear efficiency + copper of the torque, ASSUMPTION)."""
    from .devices import CMGTail
    g = CMGTail(**gt_kwargs)
    rpm = g.rpm
    w_s = rpm * TWO_PI / 60
    n_r = g.n_rotors()
    P_fric = 1.5 * (0.011e-3 + 1.02e-9 * rpm) * w_s
    P_wind = 2 * 0.01 * 0.5 * RHO_AIR * w_s ** 3 * g.r_o ** 5
    P_spin = n_r * (P_fric + P_wind) / 0.8
    P_g = mech_W / 0.5 + (0.05 if active else 0.0)            # + driver quiescent 0.05 W (ASSUMPTION)
    return {"P_cmg_spin_W": P_spin, "P_cmg_gimbal_W": P_g}


# ================================================================================================ tuned mass
def tmd_design(m: float = 0.040, f_tune: float = 5.0, stroke: float = 5e-3, mu_eff: float = 0.12) -> Dict:
    """Tuned (resonant) reaction mass.  mu_eff: the mass ratio against the effective modal mass it works on
    (ASSUMPTION 0.1-0.15 for a 40 g mass at the tail against the pen and hand; lin.py computes the real effect)."""
    k = m * (TWO_PI * f_tune) ** 2
    zeta_opt = math.sqrt(3 * mu_eff / (8 * (1 + mu_eff) ** 3))       # Den Hartog
    f_opt_ratio = 1 / (1 + mu_eff)
    # the band in which a Den Hartog absorber keeps the response below the untreated primary's at the edges: about
    # +- sqrt(mu) around the tuning (CALC, classical result)
    bw = math.sqrt(mu_eff)
    F = {f: m * (TWO_PI * f) ** 2 * stroke for f in (4.0, 5.0, 6.0, 8.0, 10.0)}
    return {"m_g": m * 1e3, "f_tune_Hz": f_tune, "k_N_m": k, "stroke_mm": stroke * 1e3, "zeta_opt": zeta_opt,
            "f_opt_ratio": f_opt_ratio, "band_rel": bw, "band_Hz": (f_tune * (1 - bw / 2), f_tune * (1 + bw / 2)),
            "force_cap_N": {str(f): v for f, v in F.items()},
            "k_range_4_10Hz_N_m": (m * (TWO_PI * 4) ** 2, m * (TWO_PI * 10) ** 2),
            "semi_active": "retune k over 4-10 Hz (x6.25 in stiffness): a flexure whose free length a small screw motor "
                           "changes by 1.9x (k ~ 1/L^3), or a magnetic spring with an adjustable gap (PROPOSED DESIGN)",
            "fixed_g": 12.0, "power_W": 0.0, "semi_active_power_W": 0.01}


# ================================================================================================ pivot collar
def collar_design(z_p: float, travel: float, N: float = 1.0, theta_deg: float = 50.0, Km_out: float = 0.042,
                  pen_front_d: float = 12e-3, pen_d: float = 24e-3, z_f: float = 0.032, z_w: float = 0.092,
                  length: float = 0.145, tip_force_cap: float = 1.0) -> Dict:
    """The whole pen hangs in a 2-axis gimbal at z_p inside a collar (saddle) held by the fingers and the web.
    Tip travel X needs a swing phi = X / z_p; the saddle must clear the swinging pen where the hand holds it."""
    th = math.radians(theta_deg)
    phi = travel / z_p
    swing_f = abs(z_p - z_f) * phi
    swing_w = abs(z_w - z_p) * phi
    swing_tail = abs(length - z_p) * phi
    d_f = pen_front_d + 2 * swing_f + 1.6e-3                    # 0.3 mm clearance + 0.5 mm wall each side
    d_w = pen_d + 2 * swing_w + 1.6e-3
    M_static = N * z_p * math.cos(th)                           # writing force's moment about the pivot (N m)
    P_hold = (M_static / Km_out) ** 2                           # copper to hold it (one axis)
    tip_speed_5Hz = TWO_PI * 5.0 * travel
    return {"z_p_mm": z_p * 1e3, "travel_mm": travel * 1e3, "swing_rad": phi, "swing_deg": math.degrees(phi),
            "writing_angle_range_deg": (theta_deg - math.degrees(phi), theta_deg + math.degrees(phi)),
            "swing_at_fingers_mm": swing_f * 1e3, "swing_at_web_mm": swing_w * 1e3, "swing_at_tail_mm": swing_tail * 1e3,
            "collar_d_at_fingers_mm": d_f * 1e3, "saddle_d_at_web_mm": d_w * 1e3,
            "static_moment_mNm_per_N": M_static / N * 1e3, "static_moment_mNm": M_static * 1e3,
            "hold_power_W": P_hold, "Km_out_Nm_sqrtW": Km_out,
            "tip_speed_at_5Hz_m_s": tip_speed_5Hz, "tip_force_cap_N": tip_force_cap,
            "motor_torque_for_cap_mNm": tip_force_cap * z_p * 1e3,
            "Km_label": "CALC: MFR AMF-120 0824 B (kM 1.6 mN m/A, 2.91 ohm -> 0.94 mN m/sqrt(W)) x 64:1 x 0.7 (AMF-103 gearhead, efficiency ASSUMPTION)"}


def collar_power(cu_W: float, mech_W: float) -> float:
    return cu_W + mech_W / 0.7 + 0.03


# ================================================================================================ paper-grounded
def paper_design(mu: float = 0.9) -> Dict:
    """Force the paper can give (friction x load) through each element (CALC; friction ASSUMPTION 0.6-1.2)."""
    heel_P = 0.55                                                # N preload (ASSUMPTION, study D / the lead)
    out = {
        "heel_wheel": {"traction_N": (0.6 * heel_P, 1.2 * heel_P), "train_cont_N": 0.369, "train_peak_N": 0.603,
                       "note": "one wheel pushes along its heading only; across it the tyre grips (a constraint), so an "
                               "anti-phase drive needs the heading on the tremor axis, which blocks writing across it"},
        "omni_heel": {"force_cap_N": 0.37, "kP_W_N2": 4.30,
                      "note": "an idealised heel that pushes in any direction (a driven ball, study D's fallback) at the "
                              "heel train's continuous force"},
        "heel_all_load": {"traction_N": (0.6 * 1.0, 1.2 * 1.0),
                          "note": "if the heel carried the whole 1 N writing force instead of 0.55 N: x1.8"},
        "sled": {"N_rest_N": (1.0, 3.0), "mu": (0.6, 1.0), "force_N": (0.6, 3.0), "kP_W_N2": 1.0,
                 "note": "a rest under the hand's ulnar side carrying 1-3 N of the hand's weight (ASSUMPTION) onto a "
                         "braked or driven element; outside the pen (a writing mouse); the writer must slide it along the line"},
    }
    return out


def drive_power_from_F2(F2_mean: float, kind: str) -> float:
    kP = 4.30 if kind == "omni" else 1.0
    return kP * F2_mean + 0.02


# ================================================================================================ gating
def gating_design(f_tremor: float = 5.0, E_cycle: float = 0.017) -> Dict:
    """The pen lift (nose2/Rev J: drum, tendon, brake and latch; 0.5 mm, 8 ms) switching at up to 2 f_tremor."""
    return {"cycles_per_s_max": 2 * f_tremor, "E_cycle_J": E_cycle, "P_max_W": 2 * f_tremor * E_cycle,
            "switching_ms": 8.0, "stroke_mm": 0.5,
            "E_label": "CALC (nose2 axial_dof, sim2j tasks.E_LIFT)",
            "duty_note": "a 10 mm sine with 6.57 mm of nose reach is inside the reach 45 % of the time (2 asin(0.657)/pi)"}


# ================================================================================================ authority (lin.py)
def authority(freqs=(4.0, 5.0, 6.0, 8.0, 10.0), r_rots=(0.3, 0.5, 0.7)) -> Dict:
    """Tip motion per unit input for each device class (H1 hand, frictionless paper as study K; CALC)."""
    import torch
    from . import lin as L
    out = {}
    for r in r_rots:
        mdl = L.Model(hand=L.HandP(r_rot=r))
        asm = L.Assembly(mdl)
        rows = {}
        for f in freqs:
            w = TWO_PI * f
            g = lambda u: L.amp(asm.tip(asm.solve(w, u)))
            rows[str(f)] = {
                "tremor_tip_per_hand": L.amp(asm.tip(asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * 1.0)))),
                "um_per_mNm_torque_t1": g(asm.u_torque_pen(asm.t1)) * 1e3,
                "um_per_mNm_torque_t2": g(asm.u_torque_pen(asm.t2)) * 1e3,
                "mm_per_N_tail_t1": g(asm.u_force_pen(0.160, asm.t1)) * 1e3,
                "mm_per_N_tail_t2": g(asm.u_force_pen(0.160, asm.t2)) * 1e3,
                "mm_per_N_hand": g(asm.u_force_hand(np.array([0.0, 1.0, 0.0]))) * 1e3,
                "mm_per_N_tip": g(asm.u_force_pen(0.0, np.array([0.0, 1.0, 0.0]))) * 1e3,
            }
        out[str(r)] = rows
    return out
