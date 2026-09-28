r"""Small-angle 3-D linear model of hand, pen and paper (frequency domain).

Degrees of freedom (page frame for translations):
  0-2  p      ball-centre displacement of the pen (x, y, z)
  3-4  beta   pen tilt: a point z along the axis moves z (beta1 t1 + beta2 t2); rotation vector
              phi = -beta2 t1 + beta1 t2 (roll about the axis is irrelevant for an axisymmetric pen)
  5-7  dM     hand-mass perturbation (HAP-26 convention of models M1/P1: the imposed hand path is the
              reference of the arm spring; the hand mass responds only to grip and arm forces)
  8-10 r      reaction-mass or tuned-mass displacement relative to the pen along t1, t2, a (device kinds rm, tmd)
Point kinematics: the displacement of a pen-fixed point at offset s is  p + beta1 (t2 x s) - beta2 (t1 x s).
Grip zones (grip.py) act between pen points and the hand frame; the hand frame moves with the imposed
tremor (translation D and rotation Psi about a pivot) plus dM.  Paper: stiff normal contact at the skid
point; in-plane either frictionless ('free'), viscous ('viscous', c) or pinned ('pinned').
Nib (ink) = page projection of the ball centre = p_x, p_y.
Evidence status: CALCULATION (linear model); used for the oracle bounds and sizing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import grip as G
from .params import Config, geometry_vectors, pen_with_device, protrusion_centre, CONTACT


def cross_mat(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0.0]])


class LinearModel:
    def __init__(self, cfg: Config, paper: str = "free", c_paper: float = 0.0, k_pin: float = 1e6,
                 hand_fixed: bool = False, massless_pen: bool = False, contact: bool = True):
        self.cfg = cfg
        a, t1, t2, n, h = geometry_vectors(cfg.theta_deg, cfg.phi_deg)
        self.a, self.t1, self.t2, self.n, self.h = a, t1, t2, n, h
        self.grip = G.from_config(cfg)
        self.body = pen_with_device(cfg)
        dv = cfg.device
        self.has_r = dv.kind in ("rm", "tmd")
        self.ndof = 11 if self.has_r else 8
        nd = self.ndof
        M = np.zeros((nd, nd)); D = np.zeros((nd, nd)); K = np.zeros((nd, nd))
        # ---- pen mass matrix
        b = self.body
        if not massless_pen:
            m, zg, Jn = b.m, b.z_g, b.J_nib
            M[0:3, 0:3] += m * np.eye(3)
            M[0:3, 3] += m * zg * t1
            M[0:3, 4] += m * zg * t2
            M[3, 0:3] += m * zg * t1
            M[4, 0:3] += m * zg * t2
            M[3, 3] += Jn
            M[4, 4] += Jn
        else:
            M[0:5, 0:5] += 1e-9 * np.eye(5)
        # ---- hand mass and arm
        if hand_fixed:
            K[5:8, 5:8] += 1e9 * np.eye(3)
            M[5:8, 5:8] += 1e-9 * np.eye(3)
        else:
            M[5:8, 5:8] += cfg.M_hand * np.eye(3)
            K[5:8, 5:8] += cfg.k_arm * np.eye(3)
            D[5:8, 5:8] += cfg.b_arm * np.eye(3)
        gp = self.grip
        beta = gp.beta
        # ---- grip zones: finger pads (transverse k_f + axial k_a) and web (transverse k_w)
        self.zones = []
        P_tr = np.eye(3) - np.outer(a, a)
        for name, z, Kz in (("f", gp.z_f, gp.k_f * P_tr + gp.k_a * np.outer(a, a)), ("w", gp.z_w, gp.k_w * P_tr)):
            s = z * a
            J = np.zeros((3, nd))
            J[:, 0:5] = self.point_jac(s)
            J[:, 5:8] = -np.eye(3)
            K += J.T @ Kz @ J
            D += beta * (J.T @ Kz @ J)
            self.zones.append((name, s, Kz, J))
        # rotational stiffness of the pads, relative to the hand frame's tilt
        kap = gp.kappa_f
        K[3:5, 3:5] += kap * np.eye(2)
        D[3:5, 3:5] += beta * kap * np.eye(2)
        # ---- paper contact at the skid point
        self.s_skid = protrusion_centre(cfg.theta_deg) * a + CONTACT["r_ring"] * t1
        Js = np.zeros((3, nd)); Js[:, 0:5] = self.point_jac(self.s_skid)
        self.J_skid = Js
        if contact:
            nz = Js[2]
            K += cfg.k_sk * np.outer(nz, nz)
            D += cfg.c_sk * np.outer(nz, nz)
            Jxy = Js[0:2]
            if paper == "viscous" and c_paper > 0:
                D += c_paper * Jxy.T @ Jxy
            elif paper == "pinned":
                K += k_pin * Jxy.T @ Jxy
        # ---- device
        if self.has_r:
            T = np.column_stack([t1, t2, a])
            sd = dv.z * a
            Jd = np.zeros((3, nd))
            Jd[:, 0:5] = self.point_jac(sd)
            Jd[:, 8:11] = T
            M += dv.m * Jd.T @ Jd
            kc = np.array([dv.k_c if s_ > 0 else 2e4 for s_ in dv.stroke])
            cc = np.array([dv.c_c if s_ > 0 else 2 * 0.7 * math.sqrt(2e4 * max(dv.m, 1e-6)) for s_ in dv.stroke])
            K[8:11, 8:11] += np.diag(kc)
            D[8:11, 8:11] += np.diag(cc)
        if dv.kind == "gyro" and dv.H != 0:
            D[3, 4] += dv.H
            D[4, 3] -= dv.H
        self.M, self.D, self.K = M, D, K

    # -------------------------------------------------------------- kinematics
    def point_jac(self, s):
        """3x5 Jacobian of the displacement of a pen-fixed point at offset s w.r.t. (p, beta1, beta2)."""
        J = np.zeros((3, 5))
        J[:, 0:3] = np.eye(3)
        J[:, 3] = np.cross(self.t2, s)
        J[:, 4] = -np.cross(self.t1, s)
        return J

    def hand_beta(self, axis):
        """Hand-frame tilt coordinates (beta1, beta2) for a unit rotation about `axis`."""
        axis = np.asarray(axis, float)
        return np.array([axis @ self.t2, -(axis @ self.t1)])

    # -------------------------------------------------------------- excitation vectors
    def exc_translation(self, d_page, w):
        """Generalised force (complex) for a unit imposed hand translation along d_page at angular frequency w."""
        F = np.zeros(self.ndof, complex)
        d = np.asarray(d_page, float)
        for name, s, Kz, J in self.zones:
            F += J.T @ ((Kz + 1j * w * self.grip.beta * Kz) @ d)
        return F

    def exc_rotation(self, axis, pivot, w):
        """Generalised force for a unit imposed rotation of the hand frame about `axis` through `pivot`."""
        axis = np.asarray(axis, float)
        pivot = np.asarray(pivot, float)
        F = np.zeros(self.ndof, complex)
        for name, s, Kz, J in self.zones:
            dh = np.cross(axis, s - pivot)
            F += J.T @ ((Kz + 1j * w * self.grip.beta * Kz) @ dh)
        bh = self.hand_beta(axis)
        kap = self.grip.kappa_f
        F[3:5] += kap * (1 + 1j * w * self.grip.beta) * bh
        return F

    def input_vector(self, which):
        """Unit generalised input: F_t1/F_t2/F_a on the moving mass (reaction on the pen), tau_t2/tau_t1 torque on
        the pen, F_x/F_y/F_z force at the nib, Fcap_t1/Fcap_t2 force on the pen at the device position."""
        u = np.zeros(self.ndof)
        a, t1, t2 = self.a, self.t1, self.t2
        if which in ("F_t1", "F_t2", "F_a"):
            if not self.has_r:
                raise ValueError("no moving mass in this configuration")
            u[8 + ("F_t1", "F_t2", "F_a").index(which)] = 1.0
        elif which == "tau_t2":
            u[3] = 1.0
        elif which == "tau_t1":
            u[4] = -1.0
        elif which in ("F_x", "F_y", "F_z"):
            u[("F_x", "F_y", "F_z").index(which)] = 1.0
        elif which in ("Fcap_t1", "Fcap_t2", "Fcap_a"):
            d = {"Fcap_t1": t1, "Fcap_t2": t2, "Fcap_a": a}[which]
            u[0:5] = self.point_jac(self.cfg.device.z * a).T @ d
        else:
            raise KeyError(which)
        return u

    # -------------------------------------------------------------- solves
    def solve(self, w, F):
        A = -w * w * self.M + 1j * w * self.D + self.K
        return np.linalg.solve(A, F)

    def frf(self, f, F_fun):
        """Response vectors for each frequency: F_fun(w) -> generalised force."""
        out = []
        for fi in np.atleast_1d(f):
            w = 2 * np.pi * fi
            out.append(self.solve(w, F_fun(w)))
        return np.array(out)

    @staticmethod
    def nib(X):
        return X[..., 0:2]

    def stroke(self, X):
        return X[..., 8:11] if self.has_r else None


def tremor_direction(orientation=0.6):
    """Major axis of the synthetic tremor ellipse in the page (stabpen.signals.TremorSpec default 0.6 rad)."""
    return np.array([math.cos(orientation), math.sin(orientation), 0.0]), np.array([-math.sin(orientation), math.cos(orientation), 0.0])


def pivot_point(cfg: Config, L_p: float, height: float = 0.0):
    """Wrist pivot: L_p behind the grip's elastic centre along the pen azimuth h (page plane), at `height`."""
    a, t1, t2, n, h = geometry_vectors(cfg.theta_deg, cfg.phi_deg)
    g = G.from_config(cfg)
    zc_proj = g.z_c * math.cos(cfg.theta_deg * math.pi / 180)
    return (zc_proj + L_p) * h + height * n


def oracle_bound(nib0, gains, limits):
    """Best residual nib amplitude per page component when each input i (complex nib response gains[i] per unit
    input, 2-vector) is bounded by |u_i| <= limits[i] and phased optimally (CALC, single frequency).
    Inputs acting on the same page component add in magnitude (a bound, reached when their phases align)."""
    nib0 = np.asarray(nib0, complex)
    res = np.abs(nib0).astype(float)
    auth = np.zeros(2)
    for g, L in zip(gains, limits):
        g = np.asarray(g, complex)
        auth += np.abs(g) * L
    res = np.maximum(res - auth, 0.0)
    return res, auth
