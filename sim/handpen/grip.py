r"""Two-zone grip calibrated to the tip-referred HAP-26 impedance.

The pen is held by two contact zones fixed to the hand frame:
  * finger pads (thumb, index, middle) at z_f: transverse stiffness k_f, a rotational stiffness
    kappa_f (the pads' own resistance to tilting the pen) and the axial stiffness k_a;
  * the thumb-index web at z_w: transverse stiffness k_w.
Per transverse plane the grip stiffness about the nib, for pen translation u (at the nib) and
tilt psi relative to the hand, is
      K = [[k_t, S], [S, I2 + kappa_f]],   k_t = k_f + k_w,  S = k_f z_f + k_w z_w,  I2 = k_f z_f^2 + k_w z_w^2
and the nib compliance is C_uu = (I2 + kappa_f) / (k_f k_w d^2 + k_t kappa_f), d = z_w - z_f.
Calibration (CALC): C_uu = 1/575 m/N (HAP-26 k1, tip-referred) for a chosen
  r_rot = 1 - (1/k_t)/C_uu   (share of the nib compliance that comes from pen rotation in the grip)
  rho_w = k_w / k_t          (share of the translational stiffness carried at the web)
which gives k_t = k_nib/(1 - r_rot) and kappa_f = (k_nib I2 - k_f k_w d^2)/(k_t - k_nib) >= 0,
feasible for r_rot <= r_max(rho_w) = 1 - rho_w (1 - rho_w) d^2 / ((1 - rho_w) z_f^2 + rho_w z_w^2).
The axial stiffness equals k_nib so the tip-referred stiffness is 575 N/m in every direction.
Damping is stiffness-proportional (b_nib/k_nib), so the tip-referred damping is 1.3 N s/m.
The split (r_rot, rho_w) is not measured: ASSUMPTION, swept; EXP-I01 measures it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .params import Config, HAND, PAD


@dataclass
class Grip:
    k_f: float
    k_w: float
    kappa_f: float
    k_a: float
    beta: float          # damping / stiffness ratio (s)
    z_f: float
    z_w: float
    r_rot: float
    rho_w: float
    k_nib: float
    b_nib: float

    @property
    def k_t(self):
        return self.k_f + self.k_w

    @property
    def z_c(self):
        """Elastic centre for translation (a force here does not tilt the pen)."""
        return (self.k_f * self.z_f + self.k_w * self.z_w) / self.k_t

    @property
    def K_r(self):
        """Rotational stiffness about the elastic centre (N m/rad)."""
        d = self.z_w - self.z_f
        return self.k_f * self.k_w * d * d / self.k_t + self.kappa_f

    def K_plane(self):
        S = self.k_f * self.z_f + self.k_w * self.z_w
        I2 = self.k_f * self.z_f ** 2 + self.k_w * self.z_w ** 2
        return np.array([[self.k_t, S], [S, I2 + self.kappa_f]])

    def nib_compliance(self):
        return float(np.linalg.inv(self.K_plane())[0, 0])

    def static_transfer(self, z):
        """Static nib displacement per unit transverse force at z, and per unit torque (plane model)."""
        C = np.linalg.inv(self.K_plane())
        # generalised force of a transverse force F at z: (F, z F); of a torque: (0, tau)
        return {"force_at_z_m_per_N": float(C[0, 0] + z * C[0, 1]), "torque_m_per_Nm": float(C[0, 1])}

    def summary(self):
        tf = self.static_transfer
        return {"k_f_N_per_m": self.k_f, "k_w_N_per_m": self.k_w, "kappa_f_Nm_per_rad": self.kappa_f, "k_axial_N_per_m": self.k_a,
                "k_t_N_per_m": self.k_t, "z_c_mm": self.z_c * 1e3, "K_r_about_zc_Nm_per_rad": self.K_r,
                "damping_ratio_beta_s": self.beta, "r_rot": self.r_rot, "rho_w": self.rho_w,
                "nib_stiffness_check_N_per_m": 1.0 / self.nib_compliance(),
                "nib_disp_per_N_at_cap_141mm_over_per_N_at_nib": tf(0.141)["force_at_z_m_per_N"] / tf(0.0)["force_at_z_m_per_N"],
                "nib_disp_per_Nm_torque_m": tf(0.0)["torque_m_per_Nm"],
                "zone_f_vs_three_pads_skin": {"zone_f_N_per_m": self.k_f,
                                              "three_pads_skin_N_per_m_at_1N": 3 * PAD["k_power"][0] * 1.0 ** PAD["k_power"][1],
                                              "note": "skin shear stiffness of three pads (HAP-31 power law at 1 N) in series with finger joints; "
                                                      "zone stiffness below it is consistent with joint compliance dominating (CALC)"}}


def r_max(rho_w, z_f, z_w):
    d = z_w - z_f
    return 1.0 - rho_w * (1.0 - rho_w) * d * d / ((1.0 - rho_w) * z_f ** 2 + rho_w * z_w ** 2)


def calibrate(k_nib=HAND["k_nib"], b_nib=HAND["b_nib"], r_rot=0.5, rho_w=0.3, z_f=0.0275, z_w=0.075, scale=1.0,
              b_add=0.0, lock_rotation=False) -> Grip:
    """Zone parameters reproducing a tip-referred stiffness k_nib (and damping b_nib + b_add), times `scale`."""
    k_nib_s = k_nib * scale
    if lock_rotation or r_rot <= 1e-6:
        k_t = k_nib_s
        kap = 0.0               # tilt locked in the core instead (lock_rotation); translation carries all compliance
        r_eff = 0.0
    else:
        rm = r_max(rho_w, z_f, z_w)
        if r_rot > rm + 1e-9:
            raise ValueError(f"r_rot {r_rot:.3f} not reachable with rho_w {rho_w:.2f} (max {rm:.3f})")
        k_t = k_nib_s / (1.0 - r_rot)
        r_eff = r_rot
        kap = None
    k_f = (1.0 - rho_w) * k_t
    k_w = rho_w * k_t
    d = z_w - z_f
    if kap is None:
        I2 = k_f * z_f ** 2 + k_w * z_w ** 2
        kap = max((k_nib_s * I2 - k_f * k_w * d * d) / (k_t - k_nib_s), 0.0)
    beta = (b_nib * scale + b_add) / k_nib_s
    return Grip(k_f=k_f, k_w=k_w, kappa_f=kap, k_a=k_nib_s, beta=beta, z_f=z_f, z_w=z_w, r_rot=r_eff, rho_w=rho_w,
                k_nib=k_nib_s, b_nib=b_nib * scale + b_add)


def from_config(cfg: Config) -> Grip:
    return calibrate(cfg.k_nib, cfg.b_nib, cfg.r_rot, cfg.rho_w, cfg.z_f, cfg.z_w, cfg.grip_scale, cfg.grip_damp_add,
                     cfg.lock_rotation)


def hap26_compliance(f, k1=HAND["k_nib"], b1=HAND["b_nib"], M=HAND["M"], k2=HAND["k_arm"], b2=HAND["b_arm"]):
    """HAP-26 eq. (1): position/force at the stylus point, s = j 2 pi f (m/N)."""
    s = 2j * np.pi * np.asarray(f, float)
    return (M * s ** 2 + (b1 + b2) * s + k1 + k2) / (b1 * M * s ** 3 + (b1 * b2 + k1 * M) * s ** 2 + (b2 * k1 + b1 * k2) * s + k1 * k2)
