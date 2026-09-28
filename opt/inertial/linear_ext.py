r"""Small-angle linear model of hand, pen, optional grip sleeve and devices (frequency domain and state space).

Extends sim/handpen/linear.py (read-only there) with the grip sleeve and the actuated pivot of the H1 extension, and
exports state-space models for controller design and for the differentiable (torch) models.

Degrees of freedom (page frame for translations; same small-angle pen coordinates as H1):
  0-2   p       pen ball-centre displacement
  3-4   beta    pen tilt (a pen point z moves z (beta1 t1 + beta2 t2))
  5-7   dM      hand-mass perturbation (HAP-26 convention)
  [r]   3       reaction-mass displacement relative to the pen along t1, t2, a (device kinds rm, tmd)
  [s]   5       sleeve (handle) displacement and tilt, when a sleeve is present
Grip zones act between the hand frame and the sleeve (or the pen when there is no sleeve).  Pivot: translational
springs at z_p and bending stiffness k_pr between pen and sleeve; actuator at z_a: suspension/piezo stiffness k_a
(transverse) plus the command input.  Paper: stiff normal contact at the skid point; in-plane 'free', 'viscous' (c) or
'pinned' (k_pin).  Nib (ink without stage) = p_x, p_y.
Inputs (unit generalised force vectors): F_t1, F_t2, F_a (reaction-mass actuator), tau_t2, tau_t1 (torque on the pen,
CMG), P_t1, P_t2 (pivot actuator: for 'vcm' a force pair at z_a; for 'piezo' the same force pair per unit force,
i.e. k_a times the commanded displacement), F_x, F_y (force at the nib).
Evidence status: CALCULATION (linear model).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

from sim.handpen import grip as G
from sim.handpen.params import CONTACT, Config, geometry_vectors, pen_with_device, protrusion_centre


class LinearExt:
    def __init__(self, cfg: Config, paper: str = "free", c_paper: float = 0.0, k_pin: float = 1e6, contact: bool = True):
        self.cfg = cfg
        a, t1, t2, n, h = geometry_vectors(cfg.theta_deg, cfg.phi_deg)
        self.a, self.t1, self.t2, self.n, self.h = a, t1, t2, n, h
        self.grip = G.from_config(cfg)
        self.body = pen_with_device(cfg)
        dv = cfg.device
        self.has_r = dv.kind in ("rm", "tmd")
        self.sl = getattr(cfg, "sleeve", None)
        nd = 8
        self.ir = None
        if self.has_r:
            self.ir = nd
            nd += 3
        self.isl = None
        if self.sl is not None:
            self.isl = nd
            nd += 5
        self.ndof = nd
        M = np.zeros((nd, nd)); D = np.zeros((nd, nd)); K = np.zeros((nd, nd))
        b = self.body
        m, zg, Jn = b.m, b.z_g, b.J_nib
        M[0:3, 0:3] += m * np.eye(3)
        M[0:3, 3] += m * zg * t1; M[0:3, 4] += m * zg * t2
        M[3, 0:3] += m * zg * t1; M[4, 0:3] += m * zg * t2
        M[3, 3] += Jn; M[4, 4] += Jn
        M[5:8, 5:8] += cfg.M_hand * np.eye(3)
        K[5:8, 5:8] += cfg.k_arm * np.eye(3)
        D[5:8, 5:8] += cfg.b_arm * np.eye(3)
        if self.sl is not None:
            s0 = self.isl
            sl = self.sl
            M[s0:s0 + 3, s0:s0 + 3] += sl.m * np.eye(3)
            M[s0:s0 + 3, s0 + 3] += sl.m * sl.z_g * t1; M[s0:s0 + 3, s0 + 4] += sl.m * sl.z_g * t2
            M[s0 + 3, s0:s0 + 3] += sl.m * sl.z_g * t1; M[s0 + 4, s0:s0 + 3] += sl.m * sl.z_g * t2
            M[s0 + 3, s0 + 3] += sl.J_nib; M[s0 + 4, s0 + 4] += sl.J_nib
        gp = self.grip
        beta = gp.beta
        P_tr = np.eye(3) - np.outer(a, a)
        self.zones = []
        gb = 0 if self.sl is None else self.isl       # grip body offset
        for name, z, Kz in (("f", gp.z_f, gp.k_f * P_tr + gp.k_a * np.outer(a, a)), ("w", gp.z_w, gp.k_w * P_tr)):
            J = np.zeros((3, nd))
            J[:, gb:gb + 5] = self.point_jac(z * a)
            J[:, 5:8] = -np.eye(3)
            K += J.T @ Kz @ J
            D += beta * (J.T @ Kz @ J)
            self.zones.append((name, z * a, Kz, J))
        kap = gp.kappa_f
        K[gb + 3:gb + 5, gb + 3:gb + 5] += kap * np.eye(2)
        D[gb + 3:gb + 5, gb + 3:gb + 5] += beta * kap * np.eye(2)
        self.gb = gb
        # paper at the skid point of the pen
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
        # reaction mass
        if self.has_r:
            T = np.column_stack([t1, t2, a])
            Jd = np.zeros((3, nd))
            Jd[:, 0:5] = self.point_jac(dv.z * a)
            Jd[:, self.ir:self.ir + 3] = T
            M += dv.m * Jd.T @ Jd
            kc = np.array([dv.k_c if s_ > 0 else 2e4 for s_ in dv.stroke])
            cc = np.array([dv.c_c if s_ > 0 else 2 * 0.7 * math.sqrt(2e4 * max(dv.m, 1e-6)) for s_ in dv.stroke])
            K[self.ir:self.ir + 3, self.ir:self.ir + 3] += np.diag(kc)
            D[self.ir:self.ir + 3, self.ir:self.ir + 3] += np.diag(cc)
        if dv.kind == "gyro" and dv.H != 0:
            D[3, 4] += dv.H
            D[4, 3] -= dv.H
        # pivot and actuator
        if self.sl is not None:
            sl = self.sl
            s0 = self.isl
            Kp = sl.k_pt * P_tr + sl.k_pa * np.outer(a, a)
            Jp = np.zeros((3, nd))
            Jp[:, 0:5] = self.point_jac(sl.z_p * a)
            Jp[:, s0:s0 + 5] = -self.point_jac(sl.z_p * a)
            K += Jp.T @ Kp @ Jp
            D += sl.beta_p * (Jp.T @ Kp @ Jp)
            Jr = np.zeros((2, nd)); Jr[0, 3] = 1; Jr[1, 4] = 1; Jr[0, s0 + 3] = -1; Jr[1, s0 + 4] = -1
            K += sl.k_pr * Jr.T @ Jr
            D += sl.beta_p * sl.k_pr * Jr.T @ Jr
            Ja = self.pivot_jac(sl.z_a)            # 2 x nd: transverse relative displacement at z_a
            self.J_act = Ja
            K += sl.k_a * Ja.T @ Ja
            D += sl.c_a * Ja.T @ Ja
        self.M, self.D, self.K = M, D, K

    # ------------------------------------------------------------------ kinematics
    def point_jac(self, s):
        J = np.zeros((3, 5))
        J[:, 0:3] = np.eye(3)
        J[:, 3] = np.cross(self.t2, s)
        J[:, 4] = -np.cross(self.t1, s)
        return J

    def pivot_jac(self, z):
        """Transverse (t1, t2) relative displacement pen - sleeve at z along the axis (2 x ndof)."""
        J = np.zeros((2, self.ndof))
        s0 = self.isl
        for i, t in enumerate((self.t1, self.t2)):
            J[i, 0:3] = t
            J[i, s0:s0 + 3] = -t
            J[i, 3 + i] = z
            J[i, s0 + 3 + i] = -z
        return J

    def imu_jac(self, z, body="pen"):
        """Page x, y displacement of a body point at z (2 x ndof); IMU acceleration = -w^2 times this in the frequency domain."""
        off = 0 if body == "pen" else self.isl
        J = np.zeros((2, self.ndof))
        J[:, off:off + 5] = self.point_jac(z * self.a)[0:2]
        return J

    # ------------------------------------------------------------------ excitations and inputs
    def exc_translation(self, d_page, w):
        F = np.zeros(self.ndof, complex)
        d = np.asarray(d_page, float)
        for name, s, Kz, J in self.zones:
            F += J.T @ ((Kz + 1j * w * self.grip.beta * Kz) @ d)
        return F

    def exc_rotation(self, axis, pivot, w):
        axis = np.asarray(axis, float); pivot = np.asarray(pivot, float)
        F = np.zeros(self.ndof, complex)
        for name, s, Kz, J in self.zones:
            dh = np.cross(axis, s - pivot)
            F += J.T @ ((Kz + 1j * w * self.grip.beta * Kz) @ dh)
        bh = np.array([axis @ self.t2, -(axis @ self.t1)])
        kap = self.grip.kappa_f
        F[self.gb + 3:self.gb + 5] += kap * (1 + 1j * w * self.grip.beta) * bh
        return F

    def input_vector(self, which):
        u = np.zeros(self.ndof)
        a, t1, t2 = self.a, self.t1, self.t2
        if which in ("F_t1", "F_t2", "F_a"):
            if not self.has_r:
                raise ValueError("no moving mass")
            u[self.ir + ("F_t1", "F_t2", "F_a").index(which)] = 1.0
        elif which == "tau_t2":
            u[3] = 1.0
        elif which == "tau_t1":
            u[4] = -1.0
        elif which in ("P_t1", "P_t2"):
            if self.sl is None:
                raise ValueError("no sleeve")
            u = self.J_act[("P_t1", "P_t2").index(which)].copy()
        elif which in ("F_x", "F_y", "F_z"):
            u[("F_x", "F_y", "F_z").index(which)] = 1.0
        else:
            raise KeyError(which)
        return u

    # ------------------------------------------------------------------ solves
    def dyn(self, w):
        return -w * w * self.M + 1j * w * self.D + self.K

    def solve(self, w, F):
        return np.linalg.solve(self.dyn(w), F)

    def frf(self, f, F_fun):
        return np.array([self.solve(2 * np.pi * fi, F_fun(2 * np.pi * fi)) for fi in np.atleast_1d(f)])

    # ------------------------------------------------------------------ state space
    def state_space(self, inputs, outputs: Dict[str, np.ndarray], hand=True):
        """Continuous state space x = [q; qdot].  Inputs: the named unit input vectors, then (hand=True) the hand
        translation d (3) and its rate (3) through the grip springs and dampers.  outputs: name -> (k x ndof)
        displacement map; for each name the model returns displacement rows and velocity rows (use
        'acc' post-processing for accelerations).  Returns (A, B, Cd, Cv, names)."""
        n = self.ndof
        Minv = np.linalg.inv(self.M)
        A = np.zeros((2 * n, 2 * n))
        A[0:n, n:] = np.eye(n)
        A[n:, 0:n] = -Minv @ self.K
        A[n:, n:] = -Minv @ self.D
        cols = [self.input_vector(nm) for nm in inputs]
        if hand:
            Kh = np.zeros((n, 3)); Dh = np.zeros((n, 3))
            for name, s, Kz, J in self.zones:
                Kh += J.T @ Kz
                Dh += self.grip.beta * (J.T @ Kz)
            cols += [Kh[:, j] for j in range(3)] + [Dh[:, j] for j in range(3)]
        Bf = np.column_stack(cols) if cols else np.zeros((n, 0))
        B = np.zeros((2 * n, Bf.shape[1]))
        B[n:, :] = Minv @ Bf
        Cd = {k: np.hstack([v, np.zeros_like(v)]) for k, v in outputs.items()}
        Cv = {k: np.hstack([np.zeros_like(v), v]) for k, v in outputs.items()}
        return A, B, Cd, Cv


def tremor_direction(orientation=0.6):
    return np.array([math.cos(orientation), math.sin(orientation), 0.0]), np.array([-math.sin(orientation), math.cos(orientation), 0.0])


def x0_trans(lm: LinearExt, f, A=0.3e-3, orientation=0.6, ell=0.4):
    """Response to the default elliptical hand-path tremor (major axis 0.6 rad, ellipticity 0.4) at f."""
    w = 2 * np.pi * f
    umaj, umin = tremor_direction(orientation)
    F = lm.exc_translation(umaj, w) * A + lm.exc_translation(umin, w) * (-1j * ell * A)
    return lm.solve(w, F)


def oracle_bound(nib0, gains, limits):
    """Best residual nib amplitude per page component (as sim/handpen/linear.oracle_bound)."""
    nib0 = np.asarray(nib0, complex)
    res = np.abs(nib0).astype(float)
    auth = np.zeros(2)
    for g, L in zip(gains, limits):
        auth += np.abs(np.asarray(g, complex)) * L
    return np.maximum(res - auth, 0.0), auth


def ls_bound(nib0, gains, limits, n_iter=60):
    """Least-squares optimal cancellation with box limits on each (complex) input amplitude: minimise
    |nib0 + sum_i g_i u_i|^2 subject to |u_i| <= L_i (projected gradient on the complex amplitudes).  Tighter and
    more honest than oracle_bound (which adds authorities in magnitude per component).  Returns (residual 2-vector
    magnitude, u)."""
    G_ = np.column_stack([np.asarray(g, complex) for g in gains]) if gains else np.zeros((2, 0), complex)
    nib0 = np.asarray(nib0, complex)
    if G_.shape[1] == 0:
        return np.abs(nib0), np.zeros(0, complex)
    u, *_ = np.linalg.lstsq(G_, -nib0, rcond=None)
    Lv = np.asarray(limits, float)

    def proj(x):
        mag = np.abs(x)
        s = np.where(mag > Lv, Lv / np.maximum(mag, 1e-30), 1.0)
        return x * s

    u = proj(u)
    step = 1.0 / max(np.linalg.norm(G_, 2) ** 2, 1e-30)
    for _ in range(n_iter):
        r = nib0 + G_ @ u
        u = proj(u - step * (G_.conj().T @ r))
    return np.abs(nib0 + G_ @ u), u
