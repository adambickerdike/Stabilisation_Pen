"""Calibration fits for the rig sensors (in-situ, at the test angle, as bench_protocols.md R1 asks).

- bridge load cells: polynomial fit of applied load against reading, with residual statistics
  and a hysteresis estimate from loading/unloading pairs;
- 3-axis force plate: an affine 3x3 matrix (with offsets) from dead weights and pulled
  horizontal loads applied at several positions, plus a linear position (eccentricity)
  correction of the normal channel;
- flexure-guided axial cartridge: guide stiffness from force against slide with the
  refill free of the paper.

All functions take numpy arrays and return plain dicts (JSON-ready).
"""
from __future__ import annotations

from typing import Dict

import numpy as np


def fit_bridge(load_N: np.ndarray, reading: np.ndarray, order: int = 2, direction: np.ndarray = None) -> Dict:
    """load = sum_k c_k reading^k. Returns coefficients (lowest order first), residual RMS and max,
    and the loading/unloading hysteresis (max |mean residual up - mean residual down| per load)."""
    x = np.asarray(reading, float)
    y = np.asarray(load_N, float)
    V = np.vander(x, order + 1, increasing=True)
    c, *_ = np.linalg.lstsq(V, y, rcond=None)
    r = y - V @ c
    out = {"coef": c.tolist(), "order": order, "resid_rms_N": float(np.sqrt(np.mean(r ** 2))),
           "resid_max_N": float(np.max(np.abs(r))), "n": int(len(y))}
    if direction is not None:
        d = np.asarray(direction)
        h = []
        for L in np.unique(np.round(y, 6)):
            m = np.isclose(y, L)
            up, dn = r[m & (d > 0)], r[m & (d < 0)]
            if len(up) and len(dn):
                h.append(abs(up.mean() - dn.mean()))
        out["hysteresis_max_N"] = float(max(h)) if h else float("nan")
    return out


def apply_bridge(cal: Dict, reading) -> np.ndarray:
    c = np.asarray(cal["coef"])
    x = np.asarray(reading, float)
    return sum(ck * x ** k for k, ck in enumerate(c))


def fit_plate(F_applied: np.ndarray, raw: np.ndarray, pos_xy: np.ndarray = None) -> Dict:
    """Force-plate calibration. F_applied (n x 3) are the known loads in the page frame (N),
    raw (n x 3) the bridge readings, pos_xy (n x 2) the load positions on the platen (mm).
    Model: F = M raw + b, then F_z corrected by (1 + e_x x + e_y y) for eccentric loads."""
    F = np.asarray(F_applied, float)
    R = np.asarray(raw, float)
    A = np.column_stack([R, np.ones(len(R))])
    X, *_ = np.linalg.lstsq(A, F, rcond=None)
    M, b = X[:3].T, X[3]
    pred = R @ M.T + b
    out = {"M": M.tolist(), "b": b.tolist()}
    e = [0.0, 0.0]
    if pos_xy is not None:
        P = np.asarray(pos_xy, float)
        m = np.abs(F[:, 2]) > 1e-6
        if m.sum() >= 3:
            # F_z,true = pred_z * (1 + ex x + ey y)  ->  F_z/pred_z - 1 = ex x + ey y
            y = F[m, 2] / pred[m, 2] - 1.0
            e, *_ = np.linalg.lstsq(P[m], y, rcond=None)
            pred[:, 2] = pred[:, 2] * (1 + P @ e)
    out["ecc"] = [float(e[0]), float(e[1])]
    res = F - pred
    out["resid_rms_N"] = np.sqrt(np.mean(res ** 2, axis=0)).tolist()
    out["resid_max_N"] = np.max(np.abs(res), axis=0).tolist()
    offdiag = M - np.diag(np.diag(M))
    out["cross_axis_rel"] = (np.abs(offdiag) / np.abs(np.diag(M))[:, None]).max(axis=1).tolist()
    return out


def apply_plate(cal: Dict, raw: np.ndarray, pos_xy: np.ndarray = None) -> np.ndarray:
    R = np.atleast_2d(np.asarray(raw, float))
    F = R @ np.asarray(cal["M"]).T + np.asarray(cal["b"])
    if pos_xy is not None:
        P = np.atleast_2d(np.asarray(pos_xy, float))
        F[:, 2] = F[:, 2] * (1 + P @ np.asarray(cal["ecc"]))
    return F


def fit_guide_stiffness(slide_m: np.ndarray, force_N: np.ndarray) -> Dict:
    """Axial flexure guide: force read by the in-line cell against slide, refill off the paper.
    The slope is the guide stiffness k_g that the analysis subtracts (F_c = F_cell - k_g (s - s0))."""
    s = np.asarray(slide_m, float)
    f = np.asarray(force_N, float)
    A = np.column_stack([np.ones_like(s), s])
    c, *_ = np.linalg.lstsq(A, f, rcond=None)
    r = f - A @ c
    cov = np.linalg.inv(A.T @ A) * np.sum(r ** 2) / max(len(s) - 2, 1)
    return {"k_g_N_per_m": float(c[1]), "u_k_g": float(np.sqrt(cov[1, 1])), "f0_N": float(c[0]),
            "s0_m": float(-c[0] / c[1]) if c[1] != 0 else float("nan"), "resid_rms_N": float(np.sqrt(np.mean(r ** 2)))}
