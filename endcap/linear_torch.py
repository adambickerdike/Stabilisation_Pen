r"""Differentiable (PyTorch) small-angle model of the Rev H pen, the hand and an end-cap device (CALC).

The base matrices (pen 5 DOF, hand mass 3 DOF, two-zone grip calibrated to HAP-26 at a grip split r_rot, stiff paper
normal contact at the skid, frictionless in-plane: the linear model of opt/inertial/linear_ext.py, read-only) are
computed once with numpy.  The end-cap enters with differentiable parameters:
  m_fix, z_fix   mass rigidly added at z_fix (coils, frames, rotors, motors)            -> M += m J_z^T J_z
  m_r, z_r       a reaction mass on a centring spring (2 lateral DOF r1, r2 along t1, t2), actuator force between pen and mass
  k_c, c_c       its centring stiffness and damping
  H_gyro         a passive rotor spinning along the pen axis: gyroscopic coupling D[3,4] += H, D[4,3] -= H
Inputs: F_t1, F_t2 (reaction-mass actuator), tau_t2, tau_t1 (torque on the pen; CMG, reaction wheel), hand-path tremor.
Outputs: the ink (tip) displacement (page x, y) = the ball-centre displacement p_x, p_y (the nose is not modelled here: this
model gives what the end-cap does to the handle tip; the nose then corrects what is left, see endcap/sim.py).

Bound used by the optimiser (CALC, one frequency): the device applies the scaled model inverse u = -s G^-1 x0 with
s = min(1, limits / |G^-1 x0|): a feasible input, so 1 - s is an upper bound on the best residual ratio (the true
constrained optimum can only be lower).  It is the same capping rule as the feed-forward law used in the time domain.
Evidence status: CALCULATION (linear model).
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict, Optional, Sequence

import numpy as np
import torch

from opt.inertial import revh as RH
from opt.inertial.linear_ext import LinearExt, tremor_direction

torch.set_default_dtype(torch.float64)


@lru_cache(maxsize=16)
def base(r_rot=0.5, rho_w=0.3, theta_deg=50.0):
    """Numpy base model of the Rev H pen (no device): M, D, K (8x8), the pen point Jacobian helper and the tremor
    excitation vectors (unit translation along the ellipse axes, per frequency on demand)."""
    lm = LinearExt(RH.config_B(RH.RevH(), r_rot=r_rot, rho_w=rho_w, theta_deg=theta_deg))
    return lm


def point_jac8(lm, z):
    J = np.zeros((3, 8))
    J[:, 0:5] = lm.point_jac(z * lm.a)
    return J


class EndcapLinear:
    """Differentiable frequency responses for one grip split."""

    def __init__(self, r_rot=0.5, rho_w=0.3, theta_deg=50.0, hand_scale=1.0):
        lm = base(r_rot, rho_w, theta_deg)
        self.lm = lm
        self.r_rot = r_rot
        M, D, K = lm.M.copy(), lm.D.copy(), lm.K.copy()
        if hand_scale != 1.0:          # stiffer (or softer) hand: scale the grip and arm stiffness and damping (sensitivity)
            Kh = np.zeros_like(K); Dh = np.zeros_like(D)
            for name, s, Kz, J in lm.zones:
                Kh += J.T @ Kz @ J
                Dh += lm.grip.beta * (J.T @ Kz @ J)
            kap = lm.grip.kappa_f
            Kh[3:5, 3:5] += kap * np.eye(2); Dh[3:5, 3:5] += lm.grip.beta * kap * np.eye(2)
            Kh[5:8, 5:8] += lm.cfg.k_arm * np.eye(3); Dh[5:8, 5:8] += lm.cfg.b_arm * np.eye(3)
            K = K + (hand_scale - 1.0) * Kh
            D = D + (hand_scale - 1.0) * Dh
        self.hand_scale = hand_scale
        self.M0 = torch.tensor(M); self.D0 = torch.tensor(D); self.K0 = torch.tensor(K)
        self.t1 = lm.t1; self.t2 = lm.t2; self.a = lm.a
        self._exc = {}

    # -------------------------------------------------------------------------------------------- excitation
    def exc(self, f, A=1e-3, orientation=0.6, ell=0.4):
        """Generalised force (8, complex) of the default elliptical hand-path tremor of peak A (P1 convention)."""
        key = (round(f, 6), orientation, ell)
        if key not in self._exc:
            w = 2 * math.pi * f
            umaj, umin = tremor_direction(orientation)
            F = self.lm.exc_translation(umaj, w) + self.lm.exc_translation(umin, w) * (-1j * ell)
            self._exc[key] = torch.tensor(F[0:8], dtype=torch.complex128)
        return self._exc[key] * A

    # -------------------------------------------------------------------------------------------- assembly
    def matrices(self, dev: Dict):
        """(M, D, K, n) with the device's differentiable parameters (torch scalars or floats)."""
        m_fix = torch.as_tensor(dev.get("m_fix", 0.0)); z_fix = float(dev.get("z_fix", 0.1525))
        Jf = torch.tensor(point_jac8(self.lm, z_fix))
        M = self.M0 + m_fix * (Jf.T @ Jf)
        D = self.D0.clone(); K = self.K0.clone()
        Hg = dev.get("H_gyro", 0.0)
        if torch.is_tensor(Hg) or Hg != 0.0:
            Hg = torch.as_tensor(Hg)
            E = torch.zeros(8, 8); E[3, 4] = 1.0; E[4, 3] = -1.0
            D = D + Hg * E
        m_r = dev.get("m_r", 0.0)
        if torch.is_tensor(m_r) or m_r > 0.0:
            m_r = torch.as_tensor(m_r)
            z_r = float(dev.get("z_r", 0.1525))
            Jd = np.zeros((3, 10))
            Jd[:, 0:8] = point_jac8(self.lm, z_r)
            Jd[:, 8] = self.t1; Jd[:, 9] = self.t2
            Jd = torch.tensor(Jd)
            Mz = torch.zeros(10, 10); Mz[0:8, 0:8] = M
            Dz = torch.zeros(10, 10); Dz[0:8, 0:8] = D
            Kz = torch.zeros(10, 10); Kz[0:8, 0:8] = K
            M = Mz + m_r * (Jd.T @ Jd)
            k_c = torch.as_tensor(dev.get("k_c", 0.0)); c_c = torch.as_tensor(dev.get("c_c", 0.0))
            I2 = torch.zeros(10, 10); I2[8, 8] = 1.0; I2[9, 9] = 1.0
            K = Kz + k_c * I2
            D = Dz + c_c * I2
            return M, D, K, 10
        return M, D, K, 8

    @staticmethod
    def solve(M, D, K, w, F):
        A = (-w * w) * M.to(torch.complex128) + (1j * w) * D.to(torch.complex128) + K.to(torch.complex128)
        return torch.linalg.solve(A, F)

    # -------------------------------------------------------------------------------------------- responses
    def responses(self, dev: Dict, f, A=1e-3, inputs=("tau_t2", "tau_t1")):
        """Tip response to the tremor (x0, 2 complex) and the 2x2 matrix G (tip per unit input) at f."""
        M, D, K, n = self.matrices(dev)
        w = 2 * math.pi * f
        F = torch.zeros(n, dtype=torch.complex128)
        F[0:8] = self.exc(f, A)
        x0 = self.solve(M, D, K, w, F)[0:2]
        cols = []
        for nm in inputs:
            u = torch.zeros(n, dtype=torch.complex128)
            if nm == "tau_t2":
                u[3] = 1.0
            elif nm == "tau_t1":
                u[4] = -1.0
            elif nm == "F_t1":
                u[8] = 1.0
            elif nm == "F_t2":
                u[9] = 1.0
            elif nm in ("Fcap_t1", "Fcap_t2"):         # a force on the pen at the end-cap centre (e.g. a propeller)
                J = torch.tensor(point_jac8(self.lm, float(dev.get("z_fix", 0.1525))))
                d = torch.tensor(self.t1 if nm == "Fcap_t1" else self.t2)
                u[0:8] = (J.T @ d).to(torch.complex128)
            else:
                raise KeyError(nm)
            cols.append(self.solve(M, D, K, w, u)[0:2])
        G = torch.stack(cols, dim=1) if cols else None
        return x0, G

    def x0_nodev(self, f, A=1e-3):
        """Tip response of the Rev H pen without any end-cap device (the reference of every ratio)."""
        M, D, K, n = self.matrices({})
        F = self.exc(f, A)
        return self.solve(M, D, K, 2 * math.pi * f, F)[0:2]


def scaled_inverse_ratio(x0, G, limits, x_ref=None, sharp=40.0):
    """Residual ratio of the scaled model inverse (see module doc): r = (1 - s) |x0| / |x_ref|, s = softmin(1, L_i / |u*_i|).
    limits: tensor (2,) of input amplitude limits.  sharp sets the smoothness of the soft minimum (LogSumExp)."""
    u = torch.linalg.solve(G, -x0)
    mag = torch.abs(u) + 1e-30
    q = torch.stack([torch.ones((), dtype=torch.float64), *(limits / mag)])
    s = -torch.logsumexp(-sharp * q, dim=0) / sharp          # smooth min, <= true min
    s = torch.clamp(s, 0.0, 1.0)
    xn = torch.linalg.norm(torch.abs(x0))
    ref = xn if x_ref is None else torch.linalg.norm(torch.abs(x_ref))
    return (1.0 - s) * xn / ref


def exact_ratio(x0, G, limits, x_ref=None):
    """Same bound with the hard minimum (for tables)."""
    u = torch.linalg.solve(G, -x0)
    s = min(1.0, float(torch.min(limits / (torch.abs(u) + 1e-30))))
    xn = float(torch.linalg.norm(torch.abs(x0)))
    ref = xn if x_ref is None else float(torch.linalg.norm(torch.abs(x_ref)))
    return (1.0 - s) * xn / ref


def tip_capacity(G, limits):
    """Tip amplitude (m) each input can produce alone at its limit, per input (2,), and the worst direction (smallest
    singular value of G diag(L)): the displacement the device can make in every direction."""
    per = torch.linalg.norm(torch.abs(G), dim=0) * limits
    sv = torch.linalg.svdvals(G * limits.to(torch.complex128)[None, :])
    return per, sv[-1]
