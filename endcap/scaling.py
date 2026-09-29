r"""Closed-form scaling laws of every end-cap device class (CALC).

All functions accept floats, numpy arrays or torch tensors (the math is written with the operators both support) so the
same formulas serve the differentiable optimiser (endcap/optimise.py) and the tables.  Symbols: w = 2 pi f.

Force and torque that an ungrounded device can put on the pen
  linear reaction mass (LRM)      F <= min(F_act, eta m w^2 X)            grows as f^2; a stroke limit, not a force limit, at low f
  single stroke (momentum)        pen+hand shift <= m X / M_eff            centre-of-mass theorem: no net force, only relative motion
  reaction wheel (RW)             tau <= min(tau_motor, J_w w dOmega)      motor-torque limited; wheel speed must swing
  control-moment gyroscope (CMG)  tau = n H delta_dot cos(delta) <= n H min(rate_max, w delta_max)
                                  n = 2 for a scissored pair (one axis), 1 per axis for a double-gimbal rotor
  angular impulse per swing       n 2 H sin(delta_max)                     the torque is lent, not given: the gimbal must return
  passive gyroscope               tau = H x Omega_pen                      only resists rotation rate; stiffening ratio H w / K_rot
  propeller (air)                 T = (2 rho A)^(1/3) (FM eta P)^(2/3)     the only steady force; momentum theory
  weight shift (gravity)          tau = m g dx (component normal to the axis)  static, tiny
Evidence status: CALCULATION.  Inputs are MFR/LIT/ASSUMPTION as labelled in endcap/params.py.
"""
from __future__ import annotations

import math

import numpy as np

from . import params as P

TWO_PI = P.TWO_PI


def _is_t(x):
    return type(x).__module__.startswith("torch")


def _min(a, b):
    if _is_t(a) or _is_t(b):
        import torch
        a = a if _is_t(a) else torch.as_tensor(a, dtype=torch.float64)
        b = b if _is_t(b) else torch.as_tensor(b, dtype=torch.float64)
        return torch.minimum(a, b)
    return np.minimum(a, b)


def _sin(x):
    if _is_t(x):
        import torch
        return torch.sin(x)
    return np.sin(x)


def _sqrt(x):
    if _is_t(x):
        import torch
        return torch.sqrt(x)
    return np.sqrt(x)


# ------------------------------------------------------------------------------------------------ linear reaction mass
def lrm_force(m, X, f, F_act, eta=0.7):
    """Largest sinusoidal force amplitude (N) of a mass m (kg) with half-stroke X (m) at f (Hz), capped by the actuator
    force F_act (N); eta < 1 keeps the mass off its stops (0.7 as opt/inertial/addon.py)."""
    w = TWO_PI * f
    return _min(F_act, eta * m * w * w * X)


def lrm_corner(m, X, F_act, eta=0.7):
    """Frequency (Hz) above which the actuator force, not the stroke, limits a reaction mass."""
    return math.sqrt(F_act / (eta * m * X)) / TWO_PI


def com_shift_bound(m, X, M_eff):
    """Single-stroke bound (m): moving m by 2X inside the pen shifts pen + hand by at most m 2X / (M_eff + m) (no external
    force; M_eff = pen plus the hand mass that moves with it).  Returns the peak-to-peak shift."""
    return m * 2 * X / (M_eff + m)


def coil_power(F_rms, Km):
    """Copper loss (W) for an rms force with the actuator constant Km (N/sqrt(W))."""
    return (F_rms / Km) ** 2


# ------------------------------------------------------------------------------------------------ reaction wheel
def rw_torque(f, tau_motor, J_w, dOmega_max):
    """Largest sinusoidal torque amplitude (N m) of a reaction wheel: motor torque, or the wheel-speed swing
    dOmega_max (rad/s) times J_w w."""
    w = TWO_PI * f
    return _min(tau_motor, J_w * w * dOmega_max)


def rw_copper_power(tau_rms, motor):
    """I^2 R of a wheel motor delivering an rms torque (W)."""
    return (tau_rms / motor.kM) ** 2 * motor.R


# ------------------------------------------------------------------------------------------------ CMG
def rotor_mass(D, t, rho=P.RHO_WHA, d_hub=2e-3):
    return rho * math.pi / 4.0 * (D * D - d_hub * d_hub) * t


def rotor_J(m, D, d_hub=2e-3):
    """Polar moment of a disc with a hub bore."""
    return m * (D * D + d_hub * d_hub) / 8.0


def rpm2rad(n):
    return n * TWO_PI / 60.0


def cmg_torque(H, f, rate_max, delta_max, n=2):
    """Sinusoidal torque amplitude (N m) per axis: n H min(rate_max, w delta_max) (small-angle, cos(delta) ~ 1)."""
    w = TWO_PI * f
    return n * H * _min(rate_max, w * delta_max)


def cmg_corner(rate_max, delta_max):
    """Frequency (Hz) below which the gimbal angle, not its rate, limits a CMG."""
    return rate_max / (delta_max * TWO_PI)


def cmg_impulse(H, delta_max, n=2):
    """Angular impulse (N m s) of one full gimbal swing from -delta_max to +delta_max: n 2 H sin(delta_max)."""
    return n * 2.0 * H * _sin(delta_max)


def gimbal_torque(J_g, f, delta_amp, H=0.0, Omega_pen=0.0):
    """Gimbal-drive torque amplitude (N m): gimbal inertia J_g w^2 delta plus the gyroscopic load H Omega_pen from pen rotation."""
    w = TWO_PI * f
    return J_g * w * w * delta_amp + H * Omega_pen


# ------------------------------------------------------------------------------------------------ passive gyroscope
def gyro_stiffening_ratio(H, f, K_rot):
    """Gyroscopic coupling H w relative to the grip's rotational stiffness K_rot (N m/rad): the fraction by which a
    passive rotor can 'stiffen' pen tilt at f (CALC, two coupled tilt axes)."""
    return H * TWO_PI * f / K_rot


def nutation_precession(H, J_t, K_rot):
    """Nutation (fast) and precession (slow) frequencies (Hz) of a pen of transverse inertia J_t on a rotational spring K_rot
    carrying a rotor of momentum H: roots of J w^2 - H w - K = 0 ... (w_n, w_p) = (H +/- sqrt(H^2 + 4 J K)) / (2 J)."""
    s = math.sqrt(H * H + 4.0 * J_t * K_rot)
    return (H + s) / (2 * J_t) / TWO_PI, (-H + s) / (2 * J_t) / TWO_PI


# ------------------------------------------------------------------------------------------------ spin motor, energy, safety
def windage(D, t, gap, n_rpm):
    """Air drag torque (N m) of a disc in a close housing (sim/handpen/devices.windage, CALC)."""
    from sim.handpen import devices as DV
    return DV.windage(D, t, gap, n_rpm)[0]


def spin_power(motor, n_rpm, D, t, gap=0.4e-3, bearing=P.BEARING_FRICTION):
    """Electrical power (W) to hold a rotor at n_rpm: (motor friction C0 + Cv n + windage + rotor bearings) w + I^2 R, with
    I = drag / kM (CALC from MFR motor data)."""
    tau = motor.C0 + motor.Cv * n_rpm + windage(D, t, gap, n_rpm) + bearing
    w = rpm2rad(n_rpm)
    I = tau / motor.kM
    return tau * w + I * I * motor.R, tau


def spin_up_time(J, n_rpm, motor, I_lim=None, drag=0.0):
    """Time (s) to reach n_rpm at a constant motor torque min(stall, kM I_lim) minus the average drag (CALC)."""
    tq = motor.stall if I_lim is None else min(motor.stall, motor.kM * I_lim)
    net = tq - 0.5 * drag
    if net <= 0:
        return float("inf")
    return J * rpm2rad(n_rpm) / net


def stored_energy(J, n_rpm):
    return 0.5 * J * rpm2rad(n_rpm) ** 2


def hoop_stress(n_rpm, r, rho=P.RHO_WHA, nu=P.NU_WHA):
    """Peak (centre) stress of a solid spinning disc: (3 + nu)/8 rho w^2 r^2 (Pa)."""
    w = rpm2rad(n_rpm)
    return (3.0 + nu) / 8.0 * rho * w * w * r * r


def imbalance_force(m, n_rpm, G=P.BALANCE_G["nominal"]):
    """Rotating imbalance force (N) for balance grade G (m/s): m e w^2 with e w = G."""
    return m * G * rpm2rad(n_rpm)


def stop_torque(H, t_stop):
    """Average torque (N m) on the housing if a rotor of momentum H stops in t_stop (bearing seizure)."""
    return H / t_stop


# ------------------------------------------------------------------------------------------------ propeller, weight shift
def prop_thrust(D, P_elec, FM=P.PROP["FM"], eta=P.PROP["eta_motor"], rho=P.RHO_AIR):
    """Static thrust (N) of a propeller of diameter D from momentum theory: T = (2 rho A)^(1/3) (FM eta P)^(2/3)."""
    A = math.pi * D * D / 4.0
    return (2.0 * rho * A) ** (1.0 / 3.0) * (FM * eta * P_elec) ** (2.0 / 3.0)


def prop_power_for(T, D, FM=P.PROP["FM"], eta=P.PROP["eta_motor"], rho=P.RHO_AIR):
    A = math.pi * D * D / 4.0
    return T ** 1.5 / math.sqrt(2.0 * rho * A) / (FM * eta)


def weight_shift_torque(m, dx, theta_deg=50.0, axis="tilt"):
    """Static gravity torque (N m) of moving a mass m by dx normal to the pen axis: in the tilt plane (t1, vertical component
    cos(theta)) or sideways (t2, lever arm sin(theta) about the pen's lateral axis)."""
    th = math.radians(theta_deg)
    return m * P.G0 * dx * (math.cos(th) if axis == "tilt" else math.sin(th))


# ------------------------------------------------------------------------------------------------ summary table
def ceiling_table(f_list=(1, 2, 3, 5, 8, 10, 12)):
    """Force or torque available from representative end-cap-sized devices (CALC), for the doc's first table."""
    rows = []
    m_slug, X = 30e-3, 3.5e-3
    for f in f_list:
        rows.append({"f_Hz": f,
                     "LRM_30g_3.5mm_N": float(lrm_force(m_slug, X, f, 1.0)),
                     "LRM_20g_2.75mm_N": float(lrm_force(19.8e-3, 2.75e-3, f, 0.5)),
                     "CMG_pair_H1.2e-3_mNm": float(cmg_torque(1.2e-3, f, 30.0, 1.0) * 1e3),
                     "RW_0824B_rated_mNm": float(rw_torque(f, P.MOTORS["0824B"].rated, 3.8e-7, rpm2rad(10000)) * 1e3),
                     "RW_2214BXT_rated_mNm": float(rw_torque(f, P.MOTORS["2214BXT"].rated, 1.5e-6, rpm2rad(3000)) * 1e3)})
    return rows
