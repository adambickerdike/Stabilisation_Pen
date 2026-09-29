"""G2 actuator-coupon analysis (EXP-T07...T09) on rig R12.

* force/current/displacement map: at each stage position the coil current steps through
  +-I levels in reversal order; K_f is the slope of force against current (the zero-current
  intercept is the parasitic magnet force), cross-axis K_f and the motor constant
  K_m = K_f / sqrt(R(T)) follow; ripple and a smooth 2-D fit (firmware table) are reported,
  with the fraction of the map inside +-10 % of a model map (AC-B03-04 analogue);
* parasitic attraction: axial pull against gap, fitted by F = A / (g + g0)^n, its stiffness at
  the design gap, and the lateral (negative) stiffness from the zero-current map;
* Hall interference: sensor reading against coil current at fixed positions (DC and PWM),
  converted to tip micrometres, and the residual after a linear compensation;
* loaded modes: frequency response from coil current to position at several temperatures and
  axial preloads, fitted with a second-order-plus-delay model (s2r.ident);
* temperature: K_f(T) slope (magnet tempco) and R(T).
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

from s2r import ident


def kf_at_node(I: np.ndarray, F: np.ndarray) -> Dict:
    """Slope and intercept of force (n x 3) against current (n). Reversal pairs cancel drift that
    is linear in time; the least-squares fit is the same estimator with its standard error."""
    I = np.asarray(I, float)
    F = np.atleast_2d(np.asarray(F, float))
    A = np.column_stack([np.ones_like(I), I])
    coef, *_ = np.linalg.lstsq(A, F, rcond=None)
    res = F - A @ coef
    dof = max(len(I) - 2, 1)
    s2 = np.sum(res ** 2, axis=0) / dof
    cov_s = np.linalg.pinv(A.T @ A)[1, 1]
    return {"F0": coef[0], "Kf": coef[1], "se_Kf": np.sqrt(s2 * cov_s), "resid_rms": np.sqrt(s2)}


def km_map(nodes_xy: np.ndarray, I_list: Sequence[np.ndarray], F_list: Sequence[np.ndarray], R_ohm: float,
           axis: int = 0, model_Kf: np.ndarray = None, band: float = 0.10) -> Dict:
    """Map over stage nodes. F_list[k] is (n_k x 3) at node k with currents I_list[k]."""
    Kf, Kx, F0, se = [], [], [], []
    other = 1 - axis if axis in (0, 1) else 0
    for I, F in zip(I_list, F_list):
        r = kf_at_node(I, F)
        Kf.append(r["Kf"][axis])
        Kx.append(r["Kf"][other])
        F0.append(r["F0"])
        se.append(r["se_Kf"][axis])
    Kf, Kx, F0, se = map(np.asarray, (Kf, Kx, F0, se))
    xy = np.asarray(nodes_xy, float)
    Km = Kf / np.sqrt(R_ohm)
    # smooth quadratic surface for the firmware table
    x, y = xy[:, 0], xy[:, 1]
    V = np.column_stack([np.ones_like(x), x, y, x * x, x * y, y * y])
    c, *_ = np.linalg.lstsq(V, Kf, rcond=None)
    out = {"Kf": Kf, "Kf_cross": Kx, "F0": F0, "se_Kf": se, "Km": Km, "Km_min": float(Km.min()),
           "Km_centre": float(Km[np.argmin(np.hypot(x, y))]), "ripple": float((Kf.max() - Kf.min()) / Kf.mean()),
           "cross_ratio_max": float(np.max(np.abs(Kx) / np.abs(Kf))), "surface_coef": c.tolist(),
           "surface_resid_rms": float(np.sqrt(np.mean((Kf - V @ c) ** 2)))}
    if model_Kf is not None:
        ratio = Kf / np.asarray(model_Kf, float)
        out["model_ratio"] = ratio
        out["fraction_within_band"] = float(np.mean(np.abs(ratio - 1) <= band))
    return out


def attraction_fit(gap_mm: np.ndarray, Fz_N: np.ndarray, design_gap_mm: float) -> Dict:
    """F(g) = A / (g + g0)^n, fitted in log space with bounded g0 >= 0."""
    g = np.asarray(gap_mm, float)
    F = np.asarray(Fz_N, float)

    def res(p):
        A, g0, n = p
        return np.log(A) - n * np.log(g + g0) - np.log(F)

    r = ident.nls(res, [F.mean() * g.mean() ** 2, 0.2, 2.0], bounds=([1e-9, 0.0, 0.2], [1e6, 5.0, 8.0]))
    A, g0, n = r["p"]
    Fd = A / (design_gap_mm + g0) ** n
    k = n * A / (design_gap_mm + g0) ** (n + 1)          # N/mm, magnitude of dF/dg
    return {"A": float(A), "g0_mm": float(g0), "n": float(n), "F_design_N": float(Fd),
            "stiffness_N_per_mm": float(k), "resid_rms_log": float(np.sqrt(np.mean(r["resid"] ** 2)))}


def lateral_stiffness(x_mm: np.ndarray, F0x_N: np.ndarray) -> Dict:
    """Slope of the zero-current lateral force against lateral offset near the centre.
    A negative slope in the restoring sense (force grows with offset, same sign) is the
    parasitic negative stiffness the suspension must exceed."""
    x = np.asarray(x_mm, float)
    F = np.asarray(F0x_N, float)
    A = np.column_stack([np.ones_like(x), x])
    c, *_ = np.linalg.lstsq(A, F, rcond=None)
    return {"dF_dx_N_per_mm": float(c[1]), "negative_stiffness": bool(c[1] > 0), "offset_N": float(c[0])}


def hall_interference(I_A: np.ndarray, reading: np.ndarray, um_per_count: float) -> Dict:
    """Hall reading (counts or mT) against coil current at a fixed position. Returns the
    sensitivity in tip-um per A and the residual after linear compensation (um RMS), and the
    non-linearity (quadratic term) left over."""
    I = np.asarray(I_A, float)
    y = np.asarray(reading, float) * um_per_count
    A = np.column_stack([np.ones_like(I), I])
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ c
    V = np.column_stack([np.ones_like(I), I, I * I])
    c2, *_ = np.linalg.lstsq(V, y, rcond=None)
    return {"um_per_A": float(c[1]), "resid_rms_um": float(np.sqrt(np.mean(r ** 2))),
            "quadratic_um_per_A2": float(c2[2])}


def mode_fit(f: np.ndarray, H: np.ndarray, sigma: np.ndarray = None) -> Dict:
    """Second-order-plus-delay fit (s2r.ident.fit_second_order) of a current-to-position FRF."""
    sig = np.abs(H) * 0.02 if sigma is None else sigma
    r = ident.fit_second_order(f, H, sig, sign=1.0)
    a, fn, z, tau = r["p"]
    return {"fn_hz": float(fn), "zeta": float(z), "gain": float(a), "delay_s": float(tau),
            "se": [float(v) for v in r["se"]], "chi2_per_dof": r["chi2_per_dof"]}


def tempco(T_C: np.ndarray, Kf: np.ndarray) -> Dict:
    T = np.asarray(T_C, float)
    K = np.asarray(Kf, float)
    A = np.column_stack([np.ones_like(T), T - 20.0])
    c, *_ = np.linalg.lstsq(A, K, rcond=None)
    return {"Kf20": float(c[0]), "dKf_dT_pct_per_K": float(100 * c[1] / c[0])}


def copper_loss_for_holding(F_side_N: np.ndarray, lever_ratio: float, Km_N_per_sqrtW: float) -> np.ndarray:
    """Static copper loss (W) to hold a side load at the ball through a lever (tip/actuator arm):
    P = (F_side * lever / Km)^2  (review section 4)."""
    return (np.asarray(F_side_N, float) * lever_ratio / Km_N_per_sqrtW) ** 2
