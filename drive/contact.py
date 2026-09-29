"""Normal load, traction, tyre stiffness and rolling resistance of the heel drive element (CALC on ASSUMPTION inputs).

How the writing force is shared (Rev H architecture B, DEC-034):
  * the refill's constant-force spring presses the ink ball with N_ball = F_c / sin(theta) (0.20 N at 50 deg);
  * the rest of the writer's normal force goes to the heel: N_heel = N_total - N_ball;
  * the drive element is sprung with a preload P and protrudes a little beyond the skid ring, so it carries
    N_d = min(P, N_heel) and the ring carries the excess N_skid = max(0, N_heel - P).
So the traction is mu * min(P, N_heel): a writer who presses at least P + N_ball gets the full, predictable capacity
mu * P, whatever else they do; a light writer gets less; lifting the pen removes it at once.

Physical force limit that no software can exceed: mu_max * P (the spring sets the load).  With mu <= 1.2 and
P = 0.5 N that is 0.6 N.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from .params import CONTACT, WRITING, ball_normal


# ----------------------------------------------------------------------------- the writer's normal force over time
def writer_mean_force(seed: int) -> float:
    """Per-writer mean normal force (N): lognormal with CON-01's mean 1.01 N and SD 0.43 N, clipped (ASSUMPTION shape)."""
    m, s = WRITING["N_mean"].value, WRITING["N_between_sd"].value
    sig2 = math.log(1.0 + (s / m) ** 2)
    mu = math.log(m) - 0.5 * sig2
    rng = np.random.default_rng(910_000 + seed)
    x = float(rng.lognormal(mu, math.sqrt(sig2)))
    return float(np.clip(x, WRITING["N_min_writer"].value, WRITING["N_max_writer"].value))


def force_profile(t: np.ndarray, down: np.ndarray, mean_N: float, seed: int, within_sd: float = None,
                  fc_hz: float = None) -> np.ndarray:
    """Normal force N_total(t) (N): the writer's mean plus a band-limited within-word variation while the pen is down
    (CON-01 within-word SD 0.18 N; about 1.5 fluctuations/s, CON-04), zero while the pen is up."""
    from scipy.signal import butter, sosfiltfilt
    within_sd = WRITING["N_within_sd"].value if within_sd is None else within_sd
    fc_hz = WRITING["N_fluct_hz"].value if fc_hz is None else fc_hz
    dt = float(t[1] - t[0])
    rng = np.random.default_rng(920_000 + seed)
    # generate on a coarse 1 ms grid then interpolate (cheap and smooth)
    tc = np.arange(0.0, float(t[-1]) + 0.002, 1e-3)
    w = rng.standard_normal(len(tc))
    sos = butter(2, fc_hz, fs=1000.0, output="sos")
    w = sosfiltfilt(sos, w)
    w *= within_sd / max(float(np.std(w)), 1e-12)
    N = mean_N + np.interp(t, tc, w)
    N = np.maximum(N, WRITING["N_floor"].value)
    return np.where(np.asarray(down) > 0.5, N, 0.0)


def split_normal(N_total, P: float, theta_deg: float = 50.0, F_c: float = None, engaged: bool = True):
    """(N_ball, N_drive, N_skid) for an array or a scalar of total normal force."""
    F_c = WRITING["F_c_refill"].value if F_c is None else F_c
    N_total = np.asarray(N_total, float)
    Nb = np.minimum(N_total, ball_normal(theta_deg, F_c))
    Nh = np.maximum(N_total - Nb, 0.0)
    Nd = np.minimum(Nh, P) if engaged else np.zeros_like(Nh)
    return Nb, Nd, Nh - Nd


def capacity_stats(P: float, mu: float, seeds=range(1000)) -> Dict:
    """Traction capacity mu * N_d over the CON-01 writer population (CALC): mean force per writer, then the share of
    writers who get the full capacity mu * P on average."""
    means = np.array([writer_mean_force(s) for s in seeds])
    _, Nd, _ = split_normal(means, P)
    cap = mu * Nd
    return {"P_N": P, "mu": mu, "cap_mean_N": float(cap.mean()), "cap_p10_N": float(np.percentile(cap, 10)),
            "cap_p50_N": float(np.percentile(cap, 50)), "share_full": float(np.mean(Nd >= P - 1e-9)),
            "writer_mean_force_p10_p50_p90_N": [float(np.percentile(means, q)) for q in (10, 50, 90)]}


# ----------------------------------------------------------------------------- tyre mechanics
@dataclass
class Tyre:
    """A toroidal (O-ring) tyre on a hub, or an elastomer-coated ball.  r_e: outer radius of the element (m);
    rho: tube (cross-section) radius (m) for a torus (= r_e for a ball); E: Young's modulus (Pa); nu 0.5 (rubber)."""
    r_e: float = 1.5e-3
    rho: float = 0.5e-3
    E: float = CONTACT["E_tyre"].value
    nu: float = 0.5
    t_layer: float = 0.5e-3          # elastomer thickness (m)
    tan_delta: float = CONTACT["tan_delta"].value

    @property
    def G(self) -> float:
        return self.E / (2.0 * (1.0 + self.nu))

    def hertz(self, N: float) -> Dict:
        """Hertz contact of the tyre on a rigid flat (paper on a desk treated as rigid; ASSUMPTION): equivalent radius
        sqrt(R1 R2), contact radius a, mean pressure p_a (CALC)."""
        R1, R2 = self.r_e, self.rho
        Re = math.sqrt(R1 * R2)
        Es = self.E / (1.0 - self.nu ** 2)
        a = (3.0 * N * Re / (4.0 * Es)) ** (1.0 / 3.0)
        a = min(a, 0.9 * self.rho)
        pa = N / (math.pi * a * a)
        return {"R_eq_m": Re, "a_m": a, "p_mean_Pa": pa, "p_over_E": pa / self.E}

    def rolling_resistance(self, N: float) -> float:
        """Rolling friction coefficient (force / N) from Persson 2010 (AMF-112): mu_rr ~ 2.34 (p_a / E0) tan(delta)
        (sphere, low-velocity limit; Greenwood-Tabor form 9pi/64 (p_a/E0) alpha, alpha ~ 5.3 tan delta)."""
        h = self.hertz(N)
        return 2.34 * h["p_over_E"] * self.tan_delta

    def tangential_stiffness(self, N: float) -> float:
        """Tangential stiffness of the contact (N/m): Mindlin 8 a G / (2 - nu) in series with the shear of the
        elastomer layer G A / t over the contact footprint A = pi a^2 (CALC; lower bound for a thin layer)."""
        h = self.hertz(N)
        a = h["a_m"]
        k_mindlin = 8.0 * a * self.G / (2.0 - self.nu)
        A = math.pi * max(a, 1e-5) ** 2 * 4.0          # the loaded region of the layer is wider than the contact
        k_shear = self.G * A / max(self.t_layer, 1e-5)
        return 1.0 / (1.0 / k_mindlin + 1.0 / k_shear)


def tyre_table(N_list=(0.2, 0.3, 0.4, 0.5, 0.6), r_list=(1.0e-3, 1.5e-3, 2.0e-3)) -> list:
    rows = []
    for r in r_list:
        for N in N_list:
            ty = Tyre(r_e=r, rho=min(0.5e-3, 0.3 * r), t_layer=min(0.5e-3, 0.3 * r))   # O-ring cord 0.6 r (the 2 mm wheel: 0.6 mm)
            h = ty.hertz(N)
            rows.append({"r_mm": r * 1e3, "N": N, "a_mm": h["a_m"] * 1e3, "p_MPa": h["p_mean_Pa"] * 1e-6,
                         "mu_rr": ty.rolling_resistance(N), "F_rr_mN": 1e3 * ty.rolling_resistance(N) * N,
                         "k_t_N_per_mm": ty.tangential_stiffness(N) * 1e-3})
    return rows


# ----------------------------------------------------------------------------- scrub and spin at standstill
def scrub_torque(N: float, mu: float, a: float) -> float:
    """Torque (N m) to turn a loaded contact patch of radius a about its normal at standstill: (2/3) mu N a (CALC,
    uniform-pressure disc; Hertz pressure gives 3 pi / 16 = 0.59 instead of 0.67)."""
    return 2.0 / 3.0 * mu * N * a


# ----------------------------------------------------------------------------- can the paper itself hold?
def paper_hold(F_drive: float, N_total: float, N_hand_rest: float, mu_pd: float) -> Dict:
    """A loose sheet slides on the desk when the drive's reaction exceeds mu_pd (N_total + N_hand_rest) (CALC).  The
    writer's resting hand (ulnar side) and the other hand usually hold the sheet (ASSUMPTION; EXP-D03)."""
    hold = mu_pd * (N_total + N_hand_rest)
    return {"hold_N": hold, "slides": bool(F_drive > hold), "margin_N": hold - F_drive}
