r"""Inertial add-on modules for the Rev H handle (rear cap) and the passive weighted-handle comparator.

  rm_rear    active reaction mass: tungsten slug (WHA, AMF-49) on flexures in the rear cap, moved on 2 lateral axes (option:
             3rd axial axis) by moving-magnet voice coils (Km ASSUMPTION scaled from AMF-02/AMF-73), centring loop; the
             stroke is set by the cap bore.
  cmg_rear   scissored-pair control-moment gyroscope (one pair per axis) with tungsten discs on Faulhaber 0620 B spin
             motors (AMF-78) and a geared gimbal drive; torque 2 H delta_dot cos(delta).
  weight     the same mass fixed in the rear cap (passive comparator; weighted utensils ACT-18/19/32).
Budget guide from the lead: <= 30 g and <= 0.5 W for the add-on.  Masses are CALC from assumed parts (ASSUMPTION).
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from sim.handpen.params import Device
from . import catalog as CT
from .linear_ext import LinearExt, ls_bound, tremor_direction
from . import revh as RH


def rm_rear(m_slug=22e-3, d_slug=12e-3, bore=19.0e-3, z=0.160, axes=2, F_max=0.6, Km=0.9, f_c=1.5, coil_mass=4e-3,
            frame_mass=3e-3):
    """Reaction mass in the rear cap.  Lateral stroke = (bore - slug - 2 x 1.5 mm magnets/coils - 2 x 0.25 mm clearance)/2."""
    L = m_slug / (CT.RHO_WHA * math.pi / 4 * d_slug ** 2)
    lat = max((bore - d_slug - 2 * 1.5e-3 - 0.5e-3) / 2, 0.2e-3)
    k_c = m_slug * (2 * math.pi * f_c) ** 2
    return Device(kind="rm", m=m_slug, z=z, stroke=(lat, lat, 2e-3 if axes == 3 else 0.0),
                  F_max=(F_max, F_max, F_max if axes == 3 else 0.0), k_c=k_c, c_c=2 * 0.7 * math.sqrt(k_c * m_slug), Km=Km,
                  added_fixed=coil_mass + frame_mass, removed_cell_frac=0.0,
                  label=f"Rear-cap reaction mass: WHA {m_slug * 1e3:.1f} g (d {d_slug * 1e3:.0f} x {L * 1e3:.1f} mm), +/-{lat * 1e3:.1f} mm, "
                        f"{axes} axes, Km {Km} N/sqrt(W)")


def cmg_rear(d_rot=16e-3, L_rot=4e-3, rpm=20000.0, axes=(1, 1), delta_max=0.6, rate_max=20.0, z=0.160):
    m = CT.cylinder_mass(d_rot, L_rot, d_in=1e-3)
    J = CT.ring_inertia(m, d_rot, 1e-3)
    H = J * rpm * 2 * math.pi / 60
    n_pairs = sum(axes)
    mot = CT.MOTORS["0620B"]
    fixed = n_pairs * (2 * (m + mot.m) + 2 * mot.m + 1.5e-3)       # rotors, spin motors, gimbal motors, frames
    return Device(kind="cmg", m=0.0, z=z, H=H, delta_max=delta_max, rate_max=rate_max, axes=axes, added_fixed=fixed,
                  removed_cell_frac=0.0,
                  label=f"Rear-cap CMG x{n_pairs}: WHA discs {m * 1e3:.1f} g d{d_rot * 1e3:.0f} at {rpm / 1000:.0f} krpm (H {H * 1e6:.0f} uN m s)")


def cmg_power(dev: Device, rpm=20000.0, d_rot=16e-3, L_rot=4e-3, gap=0.3e-3, gimbal_W=0.03):
    """Spin power per rotor (0620 B friction C0 + Cv n, AMF-78, plus windage, CALC) x rotors + gimbal drives (ASSUMPTION)."""
    from sim.handpen import devices as DV
    mot = CT.MOTORS["0620B"]
    tau_f = mot.C0 + mot.Cv * rpm
    tau_w, _ = DV.windage(d_rot, L_rot, gap, rpm)
    w = rpm * 2 * math.pi / 60
    I = (tau_f + tau_w) / mot.kM
    P_rot = (tau_f + tau_w) * w + I * I * mot.R
    n_rot = 2 * sum(dev.axes)
    return {"P_spin_per_rotor_W": P_rot, "P_total_W": n_rot * P_rot + sum(dev.axes) * gimbal_W, "friction_torque_mNm": tau_f * 1e3,
            "windage_mNm": tau_w * 1e3}


def linear_bounds(d: RH.RevH, dev: Device, r_rot=0.5, rho_w=0.3, f0s=(4, 6, 8, 10, 12), A=0.3e-3, extra_weight=0.0):
    """Frictionless linear bound (CALC): handle-tip tremor with and without the device's best phased input, limited by
    force/stroke (RM) or gimbal rate/angle (CMG); the passive weight is a model change.  Returns ratio per frequency."""
    base = RH.config_B(d, r_rot=r_rot, rho_w=rho_w)
    lm0 = LinearExt(base)
    out = {}
    for f in f0s:
        w = 2 * np.pi * f
        umaj, umin = tremor_direction(0.6)
        x0 = lm0.solve(w, lm0.exc_translation(umaj, w) * A + lm0.exc_translation(umin, w) * (-0.4j * A))[0:2]
        if dev.kind == "rm" or dev.kind == "cmg":
            cfg = RH.config_B(d, r_rot=r_rot, rho_w=rho_w, device=dev)
            lm = LinearExt(cfg)
            x1 = lm.solve(w, lm.exc_translation(umaj, w) * A + lm.exc_translation(umin, w) * (-0.4j * A))[0:2]
            gains, lims = [], []
            if dev.kind == "rm":
                for i, nm in enumerate(("F_t1", "F_t2")):
                    X = lm.solve(w, lm.input_vector(nm).astype(complex))
                    gains.append(X[0:2])
                    lims.append(min(dev.F_max[i], dev.stroke[i] / max(abs(X[lm.ir + i]), 1e-12)))
            else:
                for nm in ("tau_t2", "tau_t1"):
                    X = lm.solve(w, lm.input_vector(nm).astype(complex))
                    gains.append(X[0:2])
                    lims.append(2 * dev.H * min(dev.rate_max, w * dev.delta_max))
            res, u = ls_bound(x1, gains, lims)
            out[f"{f:g}Hz"] = float(np.linalg.norm(res) / np.linalg.norm(np.abs(x0)))
        else:
            dd = RH.RevH(**{**d.__dict__, "extra_mass": extra_weight})
            lm = LinearExt(RH.config_B(dd, r_rot=r_rot, rho_w=rho_w))
            x1 = lm.solve(w, lm.exc_translation(umaj, w) * A + lm.exc_translation(umin, w) * (-0.4j * A))[0:2]
            out[f"{f:g}Hz"] = float(np.linalg.norm(np.abs(x1)) / np.linalg.norm(np.abs(x0)))
    return out


# ------------------------------------------------------------------ causal controllers for the rear-cap reaction mass
def plant_tables(d: RH.RevH, dev: Device, r_rot=0.5, rho_w=0.3, f=np.arange(2.0, 16.01, 0.25), z_imu=0.100):
    """Linear model responses (CALC) per unit RM force on t1, t2: handle tip displacement (page x, y) and the tip
    acceleration seen by the IMU-based estimate.  Returns freqs, G_tip (nf, 2, 2), G_acc (nf, 2, 2)."""
    lm = LinearExt(RH.config_B(d, r_rot=r_rot, rho_w=rho_w, device=dev))
    Gt = np.zeros((len(f), 2, 2), complex)
    for i, fi in enumerate(f):
        w = 2 * np.pi * fi
        for j, nm in enumerate(("F_t1", "F_t2")):
            X = lm.solve(w, lm.input_vector(nm).astype(complex))
            Gt[i, :, j] = X[0:2]
    Ga = -(2 * np.pi * f[:, None, None]) ** 2 * Gt
    return f, Gt, Ga


def afc_rm(d: RH.RevH, dev: Device, r_rot_model=0.5, mu=0.004, leak=2e-4, Ts=5e-4, z_imu=0.100, theta_deg=50.0, f_dd=150.0):
    """Adaptive narrow-band feedback (phasor LMS) of the rear-cap reaction mass at the tracked frequency (e2 = AKF
    frequency).  Error = tip acceleration estimate (page x, y) = IMU acceleration - z_imu * (gyro rate derivative)
    projected on the page; the table is the inverse of G_acc from the linear model at the MODEL split r_rot_model (the
    true split may differ: robustness is tested at 0.3 / 0.5 / 0.7).  Returns the core ctl blocks and the afc dict."""
    from sim.handpen.params import geometry_vectors
    from . import control as CL
    a, t1, t2, n, h = geometry_vectors(theta_deg)
    f, Gt, Ga = plant_tables(d, dev, r_rot=r_rot_model, z_imu=z_imu)
    wd = 2 * np.pi * f_dd
    # states: filtered gyro rates x1, x2 (for the derivative); inputs: acc x, acc y, gyro 1, gyro 2
    Ac = -wd * np.eye(2)
    Bc = np.zeros((2, 4)); Bc[0, 2] = wd; Bc[1, 3] = wd
    # beta_dd ~ wd (gyro - x); eps_j = acc_j - z_imu * (bdd1 t1_j + bdd2 t2_j)
    Cc = np.zeros((2, 2)); Dc = np.zeros((2, 4))
    for j in range(2):
        Dc[j, j] = 1.0
        Dc[j, 2] = -z_imu * wd * t1[j]
        Dc[j, 3] = -z_imu * wd * t2[j]
        Cc[j, 0] = z_imu * wd * t1[j]
        Cc[j, 1] = z_imu * wd * t2[j]
    blk = CL.embed(Ac, Bc, Cc, Dc, [CL.Y_ACC_B[0], CL.Y_ACC_B[1], CL.Y_GYR_B[0], CL.Y_GYR_B[1]], [CL.NU, CL.NU + 1], Ts)
    afc = {"table": CL.afc_table(f, Ga), "f0": float(f[0]), "df": float(f[1] - f[0]), "mu": mu, "leak": leak,
           "out": (CL.U_DEV[0], CL.U_DEV[1]), "umax": float(dev.F_max[0])}
    return [blk], afc


def ff_rm(d: RH.RevH, dev: Device, r_rot_model=0.5, Ts=5e-4, order=5):
    """Tracker-driven feed-forward: RM force = K(s) e_hat, K a causal least-squares fit of -G_tip(jw)^-1 over 3-15 Hz
    (e_hat = AKF estimate of the handle-tip disturbance, e0/e1).  Returns ([block], fit info)."""
    from . import control as CL
    f, Gt, Ga = plant_tables(d, dev, r_rot=r_rot_model)
    (Ac, Bc, Cc, Dc), info = CL.fit_inverse_filter(f, Gt, band=(3.0, 15.0), order=order, f_poles=(2.0, 30.0))
    blk = CL.embed(Ac, Bc, Cc, Dc, [CL.E_EST[0], CL.E_EST[1]], [CL.U_DEV[0], CL.U_DEV[1]], Ts)
    return [blk], info
