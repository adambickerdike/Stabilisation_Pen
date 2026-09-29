r"""The steered and driven heel wheel (DEC-037) in sim2: tyre, pod, steering servo and rolling degree of freedom,
advanced every physics step by a numba kernel that adds the wheel's wrench to the handle (after sim2's contact law).

Model (every value ASSUMPTION or CALC from study D, drive/plant.py HW1-D and docs/grounded_drive.md, unless labelled):
  pod        the wheel sits at the bottom of the skid ring (on the side toward the paper), protruding h_w = 0.35 mm
             beyond the ring along the paper normal of the nominal pose (PROPOSED DESIGN, drive T3); it is carried by a
             preloaded leaf spring: the pod does not move until the load exceeds the preload P = 0.55 N, then it yields
             with k_s (0.55 N over 0.54 mm of travel: about 100 N/m, ASSUMPTION), with a stop at the end of the travel.
             The tyre on paper is a stiff penalty contact (k_t 1e5 N/m, c_t 5 N s/m; the paper penalty of sim2's H1
             law).  So a light writer rides on the wheel and the ball, the ring lifted; a heavier writer loads the ring
             with the rest (drive: N_d = min(P, heel load)), but here the split comes from the geometry.
  tyre       2-D bristle between the handle's material point at the wheel and the wheel's surface velocity
             W = u h(psi): stiffness k_lat 1.5 N/mm, friction limit mu(|s|) N_d with a static/kinetic ratio and a
             Stribeck speed (exact exponential update, drive/plant._tyre); rolling resistance c_rr N_d along the
             heading.  Slip is real: above mu N_d the tyre slides and the force falls to the kinetic level.
  steering   heading psi (page frame) follows the command through a 40 Hz, zeta 0.8 servo with rate (500 rad/s) and
             acceleration (6e4 rad/s^2) limits (drive Hardware; CALC from the 0620 B + 4:1).
  rolling    speed u with the reflected mass m_r of the drive train (3.8 g driven; 0.1 g free), back-drive friction
             (Coulomb F_bdc, viscous c_bd) and the motor force F_m (first-order lag tau_m 0.5 ms) along the heading.
Output per step (kernel `out`): N_d, F_x, F_y (tyre + rolling drag on the pen), slip speed, slide flag, u, psi,
psi rate, rolling drag, pod compression.  Every result is a SIMULATION.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Dict

import numpy as np
from numba import njit

from . import ROOT  # noqa: F401


@dataclass
class WheelParams:
    h_w: float = 0.35e-3            # protrusion beyond the ring at nominal (m) - PROPOSED DESIGN (drive T3: 0.35 mm)
    P: float = 0.55                 # N preload (drive Hardware.P)
    travel: float = 0.54e-3         # pod travel (m) (drive T3)
    k_s: float = 100.0              # N/m pod spring beyond the preload (ASSUMPTION: 0.55 N over 0.54 mm)
    k_t: float = 1.0e5              # N/m tyre + paper penalty (sim2 H1 law k_sk)
    c_t: float = 5.0                # N s/m (ASSUMPTION)
    k_stop: float = 2.0e4           # N/m pod end stop
    mu: float = 0.9                 # true tyre-paper kinetic friction (drawn 0.6-1.2 per case in the test, drive)
    ms_ratio: float = 1.1           # static / kinetic (drive Drive.mu_static_ratio)
    v_s: float = 0.002              # Stribeck speed (m/s) (drive)
    k_lat: float = 1500.0           # N/m tyre tangential stiffness (drive Hardware.k_lat)
    c_rr: float = 0.066             # rolling resistance / N_d (drive Hardware.c_rr_wheel)
    m_r: float = 0.0038             # kg reflected mass, driven wheel (drive Hardware.m_r_wheel_driven)
    F_bdc: float = 0.024            # N back-drive Coulomb, driven wheel (drive Hardware.F_bd_wheel_driven)
    c_bd: float = 0.0               # N s/m
    tau_m: float = 0.0005           # s motor force lag
    w_s: float = 2 * math.pi * 40.0 # steering servo natural frequency (rad/s)
    z_s: float = 0.8
    rate_s: float = 500.0           # rad/s
    acc_s: float = 6.0e4            # rad/s^2
    radius: float = 1.0e-3          # wheel radius (m) (2 mm wheel)
    R_w: float = 0.0                # radial position of the wheel's contact in the ring plane (m); 0: at the ring's
                                    # contact radius with the protrusion h_w along the paper normal (study D)
    kP_copper: float = 3.48         # W/N^2 copper loss of the drive train (drive concepts.train, CALC)
    eta_mech: float = 0.8           # mechanical efficiency for the positive-work power estimate (drive)
    label: str = ("PROPOSED DESIGN / ASSUMPTION / CALC after study D (docs/grounded_drive.md T3, T6, T7; "
                  "drive/scenarios.Hardware; results/drive/rules.json)")

    def describe(self) -> Dict:
        return asdict(self)


# kernel parameter vector
WNAMES = ["h_w", "P", "travel", "k_s", "k_t", "c_t", "k_stop", "mu", "mus", "v_s", "k_lat", "c_rr", "m_r", "F_bdc",
          "c_bd", "tau_m", "w_s", "z_s", "rate_s", "acc_s", "px", "py", "pz", "nx", "ny", "nz", "on"]
WI = {n: i for i, n in enumerate(WNAMES)}
# state vector: bristle z0, z1; u; psi; psid; Fm; psi_cmd; Fm_cmd
SNAMES = ["z0", "z1", "u", "psi", "psid", "Fm", "psi_cmd", "Fm_cmd"]
SI = {n: i for i, n in enumerate(SNAMES)}
# outputs
ONAMES = ["N", "Fx", "Fy", "slip", "slide", "u", "psi", "psid", "Frr", "comp", "vx", "vy", "Flat", "Flong"]
OI = {n: i for i, n in enumerate(ONAMES)}


def param_vector(wp: WheelParams, p_loc: np.ndarray, n_loc: np.ndarray, on: bool = True) -> np.ndarray:
    v = np.zeros(len(WNAMES))
    for k in ("h_w", "P", "travel", "k_s", "k_t", "c_t", "k_stop", "mu", "v_s", "k_lat", "c_rr", "m_r", "F_bdc",
              "c_bd", "tau_m", "w_s", "z_s", "rate_s", "acc_s"):
        v[WI[k]] = float(getattr(wp, k))
    v[WI["mus"]] = wp.mu * wp.ms_ratio
    v[WI["px"]], v[WI["py"]], v[WI["pz"]] = p_loc
    v[WI["nx"]], v[WI["ny"]], v[WI["nz"]] = n_loc
    v[WI["on"]] = 1.0 if on else 0.0
    return v


@njit(cache=True)
def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


@njit(cache=True)
def wheel_step(xpos, xmat, cvel, subtree_com, xipos, xfrc, bh, root, prm, st, out, dt):
    """One physics step of the heel wheel: pod normal force, tyre bristle, rolling drag, wheel rolling and steering
    dynamics; adds the wrench on the handle (body bh) to xfrc."""
    for i in range(out.shape[0]):
        out[i] = 0.0
    if prm[26] < 0.5:
        return
    # ---- the wheel's free contact point in the world (handle-fixed point minus the protrusion along the pod axis)
    px_l = prm[20]; py_l = prm[21]; pz_l = prm[22]
    nx_l = prm[23]; ny_l = prm[24]; nz_l = prm[25]
    h_w = prm[0]
    qx = px_l - h_w * nx_l; qy = py_l - h_w * ny_l; qz = pz_l - h_w * nz_l
    R00 = xmat[bh, 0]; R01 = xmat[bh, 1]; R02 = xmat[bh, 2]
    R10 = xmat[bh, 3]; R11 = xmat[bh, 4]; R12 = xmat[bh, 5]
    R20 = xmat[bh, 6]; R21 = xmat[bh, 7]; R22 = xmat[bh, 8]
    wx_ = xpos[bh, 0] + R00 * qx + R01 * qy + R02 * qz
    wy_ = xpos[bh, 1] + R10 * qx + R11 * qy + R12 * qz
    wz_ = xpos[bh, 2] + R20 * qx + R21 * qy + R22 * qz
    # velocity of the handle's material point there
    ox = cvel[bh, 0]; oy = cvel[bh, 1]; oz = cvel[bh, 2]
    rx = wx_ - subtree_com[root, 0]; ry = wy_ - subtree_com[root, 1]; rz = wz_ - subtree_com[root, 2]
    vx = cvel[bh, 3] + oy * rz - oz * ry
    vy = cvel[bh, 4] + oz * rx - ox * rz
    vz = cvel[bh, 5] + ox * ry - oy * rx
    # ---- pod: preloaded spring in series with the tyre penalty
    P = prm[1]; trav = prm[2]; ks = prm[3]; kt = prm[4]; ct = prm[5]; kstop = prm[6]
    c = -wz_
    N = 0.0
    if c > 0.0:
        c0 = P / kt
        if c <= c0:
            N = kt * c
        else:
            N = P + ks * (c - c0) / (1.0 + ks / kt)
            if c - c0 > trav:
                N += kstop * (c - c0 - trav)
        N -= ct * vz
        if N < 0.0:
            N = 0.0
    # ---- steering servo (always runs)
    psi = st[3]; psid = st[4]
    ws = prm[16]; zs = prm[17]; rate = prm[18]; accm = prm[19]
    acc = ws * ws * _wrap(st[6] - psi) - 2.0 * zs * ws * psid
    if acc > accm:
        acc = accm
    elif acc < -accm:
        acc = -accm
    psid += acc * dt
    if psid > rate:
        psid = rate
    elif psid < -rate:
        psid = -rate
    psi += psid * dt
    st[3] = psi; st[4] = psid
    hx = math.cos(psi); hy = math.sin(psi)
    # ---- motor force lag
    taum = prm[15]
    st[5] += (1.0 - math.exp(-dt / max(taum, 1e-9))) * (st[7] - st[5])
    u = st[2]
    Fx = 0.0; Fy = 0.0; Frr = 0.0; slide = 0.0; sp = 0.0
    if N > 0.0:
        Wx = u * hx; Wy = u * hy
        s0 = vx - Wx; s1 = vy - Wy
        sp = math.sqrt(s0 * s0 + s1 * s1)
        mu = prm[7]; mus = prm[8]; vs = prm[9]; kl = prm[10]
        g = (mu + (mus - mu) * math.exp(-(sp / vs) ** 2)) * N
        z0 = st[0]; z1 = st[1]
        if sp > 1e-12:
            zs0 = g * s0 / (kl * sp); zs1 = g * s1 / (kl * sp)
            e = math.exp(-kl * sp * dt / max(g, 1e-9))
            z0 = zs0 + (z0 - zs0) * e
            z1 = zs1 + (z1 - zs1) * e
        zm = math.sqrt(z0 * z0 + z1 * z1)
        zl = mus * N / kl
        if zm > zl:
            z0 *= zl / zm; z1 *= zl / zm
        st[0] = z0; st[1] = z1
        Ft0 = -kl * z0; Ft1 = -kl * z1
        slide = 1.0 if (math.sqrt(Ft0 * Ft0 + Ft1 * Ft1) >= 0.97 * mu * N and sp > 2e-3) else 0.0
        # rolling resistance along the heading, opposing the rolling
        th = math.tanh(u / 1e-3)
        Frr = prm[11] * N * th
        Fx = Ft0 - Frr * hx
        Fy = Ft1 - Frr * hy
        # rolling degree of freedom: motor, tyre reaction along the heading, back-drive friction
        mr = prm[12]
        fr = prm[14] * u + prm[13] * math.tanh(u / 1e-3)
        u += (st[5] - (Ft0 * hx + Ft1 * hy) - fr) / mr * dt
        # ---- wrench on the handle at the wheel point (normal along +z, friction in the page plane)
        cx = xipos[bh, 0]; cy = xipos[bh, 1]; cz = xipos[bh, 2]
        ax_ = wx_ - cx; ay_ = wy_ - cy; az_ = wz_ - cz
        xfrc[bh, 0] += Fx; xfrc[bh, 1] += Fy; xfrc[bh, 2] += N
        xfrc[bh, 3] += ay_ * N - az_ * Fy
        xfrc[bh, 4] += az_ * Fx - ax_ * N
        xfrc[bh, 5] += ax_ * Fy - ay_ * Fx
    else:
        st[0] = 0.0; st[1] = 0.0
        mr = prm[12]
        fr = prm[14] * u + prm[13] * math.tanh(u / 1e-3)
        u += (st[5] - fr) / mr * dt
        u *= 0.999                                   # a lifted wheel spins down (bearing drag)
    st[2] = u
    out[0] = N; out[1] = Fx; out[2] = Fy; out[3] = sp; out[4] = slide; out[5] = u; out[6] = psi; out[7] = psid
    out[8] = Frr; out[9] = max(c, 0.0); out[10] = vx; out[11] = vy
    out[12] = -Fx * hy + Fy * hx                     # across the heading (the wheel-mount lateral force sensor)
    out[13] = Fx * hx + Fy * hy                      # along the heading


class Wheel:
    """Holds the kernel's parameter and state vectors for one PenModel; the stepper calls step() every physics step and
    the firmware sets the heading and motor-force commands (set_command)."""

    def __init__(self, pm, wp: WheelParams, on: bool = True):
        import mujoco  # noqa: F401
        self.pm = pm
        self.wp = wp
        g = pm.cfg.geom
        th = math.radians(g.theta_deg)
        # wheel point in the pen frame (x = t1 toward the paper side): the lowest point of the ring at nominal tilt
        # (the C ring's contact point p_nom a + R t1 in sim2's geometry), and the pod axis = the paper normal
        # expressed in the pen frame at the nominal pose: n = sin(th) a - cos(th) t1
        self.p_loc = np.array([wp.R_w if wp.R_w > 0 else g.skid_R, 0.0, g.p_nom()])
        self.n_loc = np.array([-math.cos(th), 0.0, math.sin(th)])
        self.prm = param_vector(wp, self.p_loc, self.n_loc, on)
        self.st = np.zeros(len(SNAMES))
        self.out = np.zeros(len(ONAMES))
        self.bh = int(pm.ids["body:handle"])
        self.root = int(pm.m.body_rootid[self.bh])
        self.dt = float(pm.m.opt.timestep)
        self.energy_pos = 0.0          # positive mechanical work of the motor on the wheel (J)

    def reset(self, psi0: float = 0.0):
        self.st[:] = 0.0
        self.st[3] = psi0
        self.st[6] = psi0
        self.out[:] = 0.0
        self.energy_pos = 0.0

    def set_command(self, psi_cmd: float, Fm_cmd: float):
        self.st[6] = psi_cmd
        self.st[7] = Fm_cmd

    def step(self, d):
        wheel_step(d.xpos, d.xmat, d.cvel, d.subtree_com, d.xipos, d.xfrc_applied, self.bh, self.root, self.prm, self.st,
                   self.out, self.dt)
        p = self.st[5] * self.st[2]
        if p > 0:
            self.energy_pos += p * self.dt

    def set_mu(self, mu: float):
        self.prm[WI["mu"]] = mu
        self.prm[WI["mus"]] = mu * self.wp.ms_ratio

    def set_free(self, free: bool):
        """A bare free wheel (steer-only hardware without the drive train): tiny reflected mass and drag."""
        if free:
            self.prm[WI["m_r"]] = 1.0e-4
            self.prm[WI["F_bdc"]] = 0.002
        else:
            self.prm[WI["m_r"]] = self.wp.m_r
            self.prm[WI["F_bdc"]] = self.wp.F_bdc
