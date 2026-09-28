r"""Candidate physical stabilisers: best plausible size in the 8.9 mm pen, sizing formulas and budgets.

Every function states its label.  Formulas (CALC) are checked against hand calculations in
tests/test_handpen.py.  Manufacturer data come from params.MOTORS (AMF-50/51) and params.RHO_WHA (AMF-49).

Candidates (task list a-i):
  a  active reaction mass in the cap (2 lateral axes, optional axial 3rd axis): the cell itself, or a tungsten slug
  b  passive tuned-mass damper in the cap (same slug), and a plainly heavier cap
  c  passive gyroscope: rotor spinning along the pen axis in the cap
  d  control-moment gyroscope: scissored pair per axis (torque 2 H delta_dot cos delta)
  e  reaction wheels (2 axes): torque = motor torque
  f  active grip sleeve (Liftware-style 2-axis gimbal between finger sleeve and pen body)
  g  passive grip: compliant / viscoelastic sleeve; 'stiction filter' (soft grip + skid friction)
  h  pivot at the paper: skid friction and a viscous nose term
  i  combinations with the nib stage (time domain)
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from .params import BALANCE_G, BUDGET, KM_CAP, MOTORS, MU_AIR, RHO_AIR, RHO_WHA, Config, Device

TWO_PI = 2 * math.pi


# ------------------------------------------------------------------ elementary formulas (CALC)
def reaction_force(m, x, f):
    """Peak force of a mass m moved sinusoidally with amplitude x at f (N): m w^2 x."""
    return m * (TWO_PI * f) ** 2 * x


def mass_stroke_needed(F, f):
    """Mass x stroke product (kg m) for a peak force F at f."""
    return F / (TWO_PI * f) ** 2


def cylinder_mass(d, L, rho=RHO_WHA, d_in=0.0):
    return rho * math.pi / 4 * (d * d - d_in * d_in) * L


def ring_inertia(m, d_out, d_in=0.0):
    """Polar moment of a ring/cylinder about its axis: m (r_o^2 + r_i^2)/2."""
    return m * ((d_out / 2) ** 2 + (d_in / 2) ** 2) / 2


def rpm_to_rad(n):
    return n * TWO_PI / 60.0


def gyro_torque(H, Omega):
    """Passive gyroscope: |tau| = H Omega for a pen rotation rate Omega perpendicular to the spin."""
    return H * Omega


def cmg_pair_torque(H, rate, delta=0.0):
    """Scissored pair: tau = 2 H delta_dot cos(delta)."""
    return 2 * H * rate * math.cos(delta)


def cmg_pair_limit(H, f, rate_max, delta_max):
    """Largest sinusoidal torque amplitude of a scissored pair at f: 2 H min(rate_max, w delta_max) (small-angle)."""
    w = TWO_PI * f
    return 2 * H * min(rate_max, w * delta_max)


def reaction_wheel_speed_swing(tau, J, f):
    """Wheel speed amplitude (rad/s) needed to give a sinusoidal torque amplitude tau at f: tau / (J w)."""
    return tau / (J * TWO_PI * f)


def imbalance_force(m, G, n_rpm):
    """Rotor imbalance force (N) at spin frequency for balance grade G (m/s): m e w^2 with e = G / w."""
    w = rpm_to_rad(n_rpm)
    return m * G * w


def spin_up_time(J, n_rpm, torque):
    return J * rpm_to_rad(n_rpm) / torque


def motor_friction_power(motor, n_rpm):
    """Bearing + iron friction power of a Faulhaber motor at speed n (datasheet C0 + Cv n) (W)."""
    M = MOTORS[motor]
    tau = M["C0"] + M["Cv"] * n_rpm
    return tau * rpm_to_rad(n_rpm), tau


def windage(d, L, gap, n_rpm, faces=2):
    """Air drag torque of a cylindrical rotor in a close housing (CALC): laminar Couette on the rim with a Taylor-vortex
    factor 2 above Ta = 1700, plus enclosed-disc torque on the faces (Daily-Nece regime I: C_m = 2 pi / ((s/r) Re))."""
    w = rpm_to_rad(n_rpm)
    r = d / 2
    nu = MU_AIR / RHO_AIR
    tau_rim = 2 * math.pi * MU_AIR * r ** 3 * L * w / gap
    Ta = w ** 2 * r * gap ** 3 / nu ** 2
    if Ta > 1700:
        tau_rim *= 2.0
    Re = w * r * r / nu
    Cm = 2 * math.pi / ((gap / r) * Re)
    tau_face = 0.5 * RHO_AIR * w ** 2 * r ** 5 * Cm * faces
    return tau_rim + tau_face, {"Taylor_number": Ta, "Re_disc": Re, "rim_Nm": tau_rim, "faces_Nm": tau_face}


def motor_power(motor, n_rpm, load_torque=0.0):
    """Electrical input to hold speed n against friction + windage load: mechanical (friction + load) x w + I^2 R."""
    M = MOTORS[motor]
    Pf, tf = motor_friction_power(motor, n_rpm)
    tau = tf + load_torque
    I = tau / M["k_M"]
    w = rpm_to_rad(n_rpm)
    return tau * w + I * I * M["R"], {"current_A": I, "friction_torque_Nm": tf}


def voice_coil_power(F_rms, Km):
    """Copper loss (W) for an rms force with a figure of merit K_m (N/sqrt(W))."""
    return (F_rms / Km) ** 2


def sleeve_holding(N=1.0, theta_deg=50.0, mu=0.12, z_p=0.040):
    """Active grip sleeve: the pen body pivots in the sleeve; the actuators hold the moment of the paper reaction about
    the pivot, z_p (N cos(theta) + mu N) worst direction, and the reaction the stage/skid architecture avoids."""
    th = math.radians(theta_deg)
    R_static = N * math.cos(th)
    R_worst = N * (math.cos(th) + mu * math.sin(th))
    return {"transverse_load_at_nib_N": R_static, "worst_direction_N": R_worst, "moment_Nm": z_p * R_worst}


def viscous_drag(c, v):
    return c * v


# ------------------------------------------------------------------ candidate devices (best plausible size)
def rm_cell(F_max=0.03):
    """a1: the 6.5 x 40 mm cell (3.45 g, CAD) suspended on flexures and driven laterally by two small moving-magnet
    coils; stroke +/-0.5 mm from the 0.7 mm radial clearance minus wiring (ASSUMPTION); +0.8 g magnets/coils/flexures
    (ASSUMPTION); K_m 0.04 N/sqrt(W) (ASSUMPTION from the project's SIM)."""
    m = BUDGET["cell_m"]
    k_c = m * (TWO_PI * 1.5) ** 2
    return Device(kind="rm", m=m, z=0.141, stroke=(0.5e-3, 0.5e-3, 0.0), F_max=(F_max, F_max, 0.0), k_c=k_c,
                  c_c=2 * 0.7 * math.sqrt(k_c * m), Km=KM_CAP["cell"], added_fixed=0.8e-3, removed_cell_frac=1.0,
                  label="Active reaction mass: the cell (3.45 g, +/-0.5 mm, 2 axes)")


def slug_geometry(d=4.5e-3, L=18e-3):
    return {"d_mm": d * 1e3, "L_mm": L * 1e3, "m_g": cylinder_mass(d, L) * 1e3,
            "stroke_lateral_mm": ((BUDGET["bore"] - d) / 2 - 0.5e-3 - 0.2e-3) * 1e3}


def rm_slug(axes=3, F_max=0.06, d=4.5e-3, L=18e-3, axial_stroke=2.0e-3):
    """a2: tungsten-alloy slug (ASTM B777 class 3, 18 g/cm3, AMF-49) 4.5 x 18 mm = 5.15 g at z 151 mm in the rear half of
    the cell space (the cell shrinks 40 -> 20 mm, about 45 mAh); lateral stroke +/-1.0 mm (bore 7.9 mm minus slug,
    0.5 mm coil wall and 0.2 mm clearance per side); optional axial stroke +/-2 mm; moving-magnet coils K_m 0.06
    N/sqrt(W) (ASSUMPTION); +0.8 g coils/magnets/flexures (ASSUMPTION)."""
    m = cylinder_mass(d, L)
    k_c = m * (TWO_PI * 1.5) ** 2
    lat = slug_geometry(d, L)["stroke_lateral_mm"] * 1e-3
    return Device(kind="rm", m=m, z=0.151, stroke=(lat, lat, axial_stroke if axes == 3 else 0.0),
                  F_max=(F_max, F_max, F_max if axes == 3 else 0.0), k_c=k_c, c_c=2 * 0.7 * math.sqrt(k_c * m),
                  Km=KM_CAP["slug"], added_fixed=0.8e-3, removed_cell_frac=0.5,
                  label=f"Active reaction mass: tungsten slug {m * 1e3:.2f} g, +/-{lat * 1e3:.1f} mm lateral" +
                        (f", +/-{axial_stroke * 1e3:.0f} mm axial" if axes == 3 else "") + f" ({axes} axes)")


def tmd_slug(f_tune=8.0, zeta=0.1, d=4.5e-3, L=18e-3):
    """b1: the same slug as a passive tuned-mass damper, tuned to f_tune with damping ratio zeta (lateral axes)."""
    m = cylinder_mass(d, L)
    k = m * (TWO_PI * f_tune) ** 2
    lat = slug_geometry(d, L)["stroke_lateral_mm"] * 1e-3
    return Device(kind="tmd", m=m, z=0.151, stroke=(lat, lat, 0.0), F_max=(0, 0, 0), k_c=k, c_c=2 * zeta * math.sqrt(k * m),
                  added_fixed=0.5e-3, removed_cell_frac=0.5, label=f"Passive TMD: slug {m * 1e3:.2f} g tuned {f_tune:g} Hz, zeta {zeta:g}")


def cap_mass(m=5.15e-3, z=0.158):
    """b2: plain added mass at the cap (tungsten), no motion."""
    return Device(kind="mass", m=m, z=z, stroke=(0, 0, 0), label=f"Heavier cap: +{m * 1e3:.1f} g tungsten at {z * 1e3:.0f} mm")


def gyro_rotor(n_rpm=30000.0, d_out=7.0e-3, d_in=2.0e-3, L=6.0e-3, motor="0515B"):
    """c: passive gyroscope - tungsten ring rotor spinning along the pen axis, driven by a 5 mm BLDC (AMF-51)."""
    m = cylinder_mass(d_out, L, d_in=d_in)
    J = ring_inertia(m, d_out, d_in)
    H = J * rpm_to_rad(n_rpm)
    return Device(kind="gyro", m=0.0, z=0.150, H=H, added_fixed=m + MOTORS[motor]["m"] + 0.4e-3, removed_cell_frac=0.6,
                  label=f"Passive gyroscope: {m * 1e3:.2f} g tungsten rotor at {n_rpm / 1000:.0f} krpm (H {H * 1e6:.0f} uN m s)")


def cmg_pair(n_rpm=60000.0, d_out=5.5e-3, d_in=1.5e-3, L=4.0e-3, axes=(1, 1), delta_max=0.6, rate_max=30.0,
             spin_motor="0308B", gimbal_motor="0515B"):
    """d: scissored-pair CMG per axis.  Rotor: tungsten ring 5.5/1.5 x 4 mm (small enough to tilt +/-0.6 rad in the bore);
    spin motor 3 mm BLDC (AMF-50) at 60 krpm; gimbal drive 5 mm BLDC class (AMF-51) with a small reduction (ASSUMPTION).
    H is per rotor; the pair gives 2 H delta_dot cos(delta)."""
    m = cylinder_mass(d_out, L, d_in=d_in)
    J = ring_inertia(m, d_out, d_in)
    H = J * rpm_to_rad(n_rpm)
    n_pairs = sum(axes)
    fixed = n_pairs * (2 * (m + MOTORS[spin_motor]["m"]) + 2 * MOTORS[gimbal_motor]["m"] + 0.5e-3)
    return Device(kind="cmg", m=0.0, z=0.146, H=H, delta_max=delta_max, rate_max=rate_max, axes=axes,
                  added_fixed=fixed, removed_cell_frac=min(1.0, 0.75 * n_pairs),
                  label=f"CMG scissored pair x{n_pairs}: rotors {m * 1e3:.2f} g at {n_rpm / 1000:.0f} krpm (H {H * 1e6:.0f} uN m s each), "
                        f"gimbal +/-{delta_max:.1f} rad, {rate_max:.0f} rad/s")


def candidate_table():
    """Best plausible devices for the frequency-domain screen and the time-domain study."""
    return {
        "rm_cell": rm_cell(),
        "rm_slug2": rm_slug(axes=2),
        "rm_slug3": rm_slug(axes=3),
        "tmd_8Hz": tmd_slug(8.0),
        "cap_5g": cap_mass(5.15e-3),
        "cap_10g": cap_mass(10.3e-3),
        "gyro_30k": gyro_rotor(30000.0),
        "cmg_lat": cmg_pair(axes=(0, 1)),
        "cmg_2ax": cmg_pair(axes=(1, 1)),
    }


# ------------------------------------------------------------------ budgets
def budget_row(cfg: Config, body_mass_kg, device_power_W=0.0, cell_frac_left=1.0):
    """Mass and battery bookkeeping (CALC): pen mass vs the 20 g target / 24 g bound; battery life with the cell
    fraction left (capacity pro rata, ASSUMPTION) and the extra power."""
    Wh = BUDGET["battery_Wh"] * cell_frac_left
    P = BUDGET["p_electronics"] + device_power_W
    return {"pen_mass_g": body_mass_kg * 1e3, "within_20g": body_mass_kg <= BUDGET["mass_target"],
            "within_24g": body_mass_kg <= BUDGET["mass_upper"], "battery_Wh": Wh,
            "life_recording_plus_device_h": Wh / P if P > 0 else float("inf")}


def gyro_budget(dev: Device, n_rpm, motor="0515B", d_out=7.0e-3, L=6.0e-3, gap=0.25e-3):
    Pm, info = motor_power(motor, n_rpm, load_torque=windage(d_out, L, gap, n_rpm)[0])
    tw, winfo = windage(d_out, L, gap, n_rpm)
    return {"spin_power_W": Pm, "windage_W": tw * rpm_to_rad(n_rpm), "windage": winfo, **info}
