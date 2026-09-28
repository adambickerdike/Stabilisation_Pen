r"""Causal controllers for the H1 in-loop controller hook (sim/handpen/core.py extension).

The core's controller runs at Ts with measurements y (16), external inputs e (4: tracker estimate x, y in the page,
tracker frequency, spare), applied commands u_app (7) and outputs [u (7); eps (2)]:
    x+ = A x + B [y; e; u_app],   [u; eps] = C x + D [y; e]
(see core.py for the channel map).  This module builds (A, B, C, D) from continuous-time designs (ZOH discretisation)
and the narrow-band (AFC) inverse-plant tables.

Controllers:
  tip_servo_A      PID position servo of the Rev H architecture-A nose (Hall at the actuator), reference = -(tracker
                   estimate) mapped to the actuator displacement; bias preload in the sleeve spec.
  rm_ff            tracker-driven feed-forward for a reaction mass: device force = K(s) * estimate, K a causal
                   least-squares fit of -G_nib(jw)^-1 over 3-15 Hz (model inverse, H2-type) [task 4a].
  rm_skyhook       band-limited absolute-velocity feedback of the pen body at the device (IMU integrated) [task 4b].
  afc              adaptive narrow-band feedback (phasor LMS) at the tracked frequency with the inverse-plant table [4b].
  lqg              observer-based controller from a reduced linear model with a tremor resonator (Riccati) [4c].
Evidence status: CALCULATION (design); SIMULATION when run in H1.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

import numpy as np
from scipy.linalg import expm, solve_continuous_are

from sim.handpen import core

NY, NE, NU, NEPS = core.NY, core.NE, core.NU, core.NEPS
NI = NY + NE + NU
NO = NU + NEPS
NYE = NY + NE
# channel indices
Y_ACC_B = (0, 1); Y_GYR_B = (2, 3); Y_ACC_S = (4, 5); Y_GYR_S = (6, 7); Y_DEV = (8, 9, 10); Y_PIV = (11, 12); Y_Q = (13, 14); Y_CON = 15
E_EST = (NY + 0, NY + 1); E_FREQ = NY + 2
U_DEV = (0, 1, 2); U_PIV = (3, 4); U_STG = (5, 6)


def c2d(Ac, Bc, Ts):
    """Zero-order-hold discretisation."""
    n, m = Ac.shape[0], Bc.shape[1]
    M = np.zeros((n + m, n + m))
    M[:n, :n] = Ac
    M[:n, n:] = Bc
    E = expm(M * Ts)
    return E[:n, :n], E[:n, n:]


def embed(Ac, Bc, Cc, Dc, in_idx: Sequence[int], out_idx: Sequence[int], Ts: float, feed=None):
    """Discretise a continuous controller with inputs taken from the core input vector positions `in_idx` (indices into
    [y; e] for the output equation and into [y; e; u_app] for the state equation, same numbering for y and e) and outputs
    written to `out_idx` (indices into [u; eps]).  Returns (A, B, C, D) in the core's layout."""
    Ac = np.atleast_2d(np.asarray(Ac, float)); Bc = np.atleast_2d(np.asarray(Bc, float))
    Cc = np.atleast_2d(np.asarray(Cc, float)); Dc = np.atleast_2d(np.asarray(Dc, float))
    nx = Ac.shape[0]
    Ad, Bd = c2d(Ac, Bc, Ts) if nx > 0 else (np.zeros((0, 0)), np.zeros((0, Bc.shape[1])))
    A = Ad
    B = np.zeros((nx, NI))
    C = np.zeros((NO, nx))
    D = np.zeros((NO, NYE))
    for j, ii in enumerate(in_idx):
        B[:, ii] += Bd[:, j]
        for o, oo in enumerate(out_idx):
            D[oo, ii] += Dc[o, j]
    for o, oo in enumerate(out_idx):
        C[oo, :] += Cc[o, :]
    return A, B, C, D


def stack(*blocks):
    """Block-diagonal combination of several embedded controllers (independent states, outputs added)."""
    nxs = [b[0].shape[0] for b in blocks]
    nx = sum(nxs)
    A = np.zeros((nx, nx)); B = np.zeros((nx, NI)); C = np.zeros((NO, nx)); D = np.zeros((NO, NYE))
    i = 0
    for (a, b, c, d), n in zip(blocks, nxs):
        A[i:i + n, i:i + n] = a
        B[i:i + n, :] = b
        C[:, i:i + n] = c
        D += d
        i += n
    return A, B, C, D


def ctl_spec(blocks, Ts=5e-4, imu=None, ulim=None, nn=None, afc=None):
    A, B, C, D = stack(*blocks) if len(blocks) > 1 else blocks[0]
    spec = {"Ts": Ts, "A": A, "B": B, "C": C, "D": D, "imu": imu or {}, "ulim": list(ulim or [0.0] * NU)}
    if nn is not None:
        spec["nn"] = nn
    if afc is not None:
        spec["afc"] = afc
    return spec


# ------------------------------------------------------------------ Rev H architecture A: nose position servo
def tip_servo_A(lever: float, theta_deg: float, m_act: float, f_bw=80.0, zeta=0.7, f_i=10.0, f_d=800.0, Ts=2e-4,
                ref_gain=1.0):
    """PID on the actuator displacement d (Hall, y[11], y[12]) with the reference from the tracker estimate
    (e0, e1 = page-frame disturbance of the handle tip): the tip must move by -e in the page; along t1 the tip's page
    shift is delta_tip1 sin(theta) (no axial DOF), along t2 it is delta_tip2; the magnets move -delta_tip / lever.
    Gains for a closed-loop bandwidth f_bw on the in-air plant m_act (nose inertia about the pivot / (z_a - z_p)^2)."""
    th = math.radians(theta_deg)
    w = 2 * math.pi * f_bw
    Kp = m_act * w * w
    Kd = 2 * zeta * m_act * w
    Ki = Kp * 2 * math.pi * f_i
    wd = 2 * math.pi * f_d
    blocks = []
    for ax in range(2):
        c_ref = ref_gain / (math.sin(th) * lever) if ax == 0 else ref_gain / lever
        # states: [integral of error, low-passed d];  inputs: [d, e_ax]
        Ac = np.array([[0.0, 0.0], [0.0, -wd]])
        Bc = np.array([[-1.0, c_ref], [wd, 0.0]])
        # u = Kp (c e - d) + Ki xI - Kd wd (d - xD)
        Cc = np.array([[Ki, Kd * wd]])
        Dc = np.array([[-Kp - Kd * wd, Kp * c_ref]])
        blocks.append(embed(Ac, Bc, Cc, Dc, [Y_PIV[ax], E_EST[ax]], [U_PIV[ax]], Ts))
    return blocks, {"Kp": Kp, "Kd": Kd, "Ki": Ki, "f_bw": f_bw, "zeta": zeta, "f_i": f_i, "f_d": f_d, "Ts": Ts}


# ------------------------------------------------------------------ stage command from the tracker (external estimate)
def stage_passthrough(Ts=5e-4, gain=1.0):
    """Stage disturbance command = tracker estimate (stage_src 2): u5, u6 = e0, e1 (no states)."""
    D = np.zeros((NO, NYE))
    D[U_STG[0], E_EST[0]] = gain
    D[U_STG[1], E_EST[1]] = gain
    return np.zeros((0, 0)), np.zeros((0, NI)), np.zeros((NO, 0)), D


# ------------------------------------------------------------------ causal inverse fit (reaction-mass feed-forward)
def fit_inverse_filter(freqs, G, band=(3.0, 15.0), order=4, f_poles=(2.0, 25.0), n_poles=None, reg=1e-6):
    """Causal, stable SISO/MIMO filter K(s) ~ -G(jw)^-1 over the band, by linear least squares on a fixed set of real
    poles (a 'Kautz/orthonormal-basis' fit): K(s) = D0 + sum_k R_k / (s + p_k).  G: (nf, 2, 2) complex nib response
    per unit device input (page x, y per device axis 1, 2).  Returns state-space (Ac, Bc, Cc, Dc) with inputs e (2)
    and outputs u (2).  CALC."""
    freqs = np.asarray(freqs, float)
    sel = (freqs >= band[0]) & (freqs <= band[1])
    f = freqs[sel]
    w = 2 * np.pi * f
    Kt = np.array([-np.linalg.pinv(G[i]) for i in np.flatnonzero(sel)])     # target (nf, 2, 2)
    npol = n_poles or order
    poles = 2 * np.pi * np.geomspace(f_poles[0], f_poles[1], npol)
    # basis functions per frequency: [1, 1/(jw + p_k)]
    Phi = np.column_stack([np.ones_like(w, dtype=complex)] + [1.0 / (1j * w + p) for p in poles])
    Wt = 1.0 / np.maximum(np.abs(Kt).max(axis=(1, 2)), 1e-12)                # relative weighting
    coef = np.zeros((npol + 1, 2, 2))
    for i in range(2):
        for j in range(2):
            A_ = np.vstack([(Phi * Wt[:, None]).real, (Phi * Wt[:, None]).imag])
            b_ = np.concatenate([(Kt[:, i, j] * Wt).real, (Kt[:, i, j] * Wt).imag])
            A_ = np.vstack([A_, math.sqrt(reg) * np.eye(npol + 1)])
            b_ = np.concatenate([b_, np.zeros(npol + 1)])
            coef[:, i, j] = np.linalg.lstsq(A_, b_, rcond=None)[0]
    # state space: for each input j a chain of first-order states per pole
    nx = 2 * npol
    Ac = np.zeros((nx, nx)); Bc = np.zeros((nx, 2)); Cc = np.zeros((2, nx)); Dc = coef[0]
    for j in range(2):
        for k, p in enumerate(poles):
            s = j * npol + k
            Ac[s, s] = -p
            Bc[s, j] = 1.0
            for i in range(2):
                Cc[i, s] = coef[k + 1, i, j]
    fit = np.array([Dc + Cc @ np.linalg.solve(1j * wi * np.eye(nx) - Ac, Bc) for wi in w])
    err = float(np.linalg.norm(fit - Kt) / max(np.linalg.norm(Kt), 1e-30))
    return (Ac, Bc, Cc, Dc), {"rel_fit_error": err, "poles_hz": (poles / 2 / np.pi).tolist()}


# ------------------------------------------------------------------ narrow-band (AFC) inverse-plant table
def afc_table(freqs, G, umax=None):
    """Rows of Ginv(jw) (2x2 complex) as (re, im) x 4 = 8 floats per frequency, plus the amplitude cap at that frequency
    (0 = none), for the core's AFC block."""
    tab = []
    for i in range(len(freqs)):
        Gi = np.linalg.pinv(G[i])
        cap = 0.0 if umax is None else float(umax[i])
        tab.append([Gi[0, 0].real, Gi[0, 0].imag, Gi[0, 1].real, Gi[0, 1].imag, Gi[1, 0].real, Gi[1, 0].imag, Gi[1, 1].real,
                    Gi[1, 1].imag, cap])
    return np.array(tab)


# ------------------------------------------------------------------ skyhook (band-limited absolute velocity feedback)
def skyhook(c_sky, f_hp=2.0, f_lp=40.0, Ts=5e-4, axes=(0, 1), acc_idx=Y_ACC_B, map_page_to_dev=None):
    """Device force = -c_sky * v, v = band-limited integral of the body IMU acceleration (page x, y) at the IMU point,
    mapped to the device axes (t1 <- x sin(theta) projection given by map_page_to_dev (2x2)).  2nd-order band-pass
    integrator per axis: v = s/((s + w_h)(s/w_l + 1)) * (a/s)... implemented as a / (s + w_h) low-passed at w_l."""
    wh = 2 * np.pi * f_hp
    wl = 2 * np.pi * f_lp
    M = np.eye(2) if map_page_to_dev is None else np.asarray(map_page_to_dev, float)
    # states per axis: v (leaky integrator of a), vf (low-passed v)
    Ac = np.zeros((4, 4)); Bc = np.zeros((4, 2)); Cc = np.zeros((2, 4)); Dc = np.zeros((2, 2))
    for k in range(2):
        Ac[2 * k, 2 * k] = -wh
        Bc[2 * k, k] = 1.0
        Ac[2 * k + 1, 2 * k] = wl
        Ac[2 * k + 1, 2 * k + 1] = -wl
    for i in range(2):
        for k in range(2):
            Cc[i, 2 * k + 1] = -c_sky * M[i, k]
    return embed(Ac, Bc, Cc, Dc, [acc_idx[0], acc_idx[1]], [U_DEV[axes[0]], U_DEV[axes[1]]], Ts)
