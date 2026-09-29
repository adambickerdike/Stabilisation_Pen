"""Camera ground truth (the low-cost option of R10, R13, R14): strobed global-shutter frames of a
high-contrast dot, a sub-pixel centroid, and a dot-grid calibration with radial distortion.

PROPOSED DESIGN: an OV9281-class global-shutter camera triggered by the rig DAQ (up to 100 fps
in external-trigger mode, trigger pulse >= 2 us, MFR OPT-88), an LED strobe of 20-50 us fired by
the DAQ inside the exposure so the image time is the strobe time on the DAQ clock, and a printed
or chrome dot grid for scale and distortion. Its accuracy is an ASSUMPTION until the static-target
and moving-target checks of docs/measurement_rig.md section R10 are done.

Frame capture from a UVC camera needs OpenCV (optional dependency, exact pin in the doc:
opencv-python-headless==4.14.0.94); everything else works on numpy arrays.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from scipy import optimize


def centroid(img: np.ndarray, rc0: Tuple[float, float], half: int = 12, dark_dot: bool = True) -> Tuple[float, float]:
    """Intensity-weighted centroid in a square window around rc0 (row, col), background removed
    with the window's border median, weights clipped at zero."""
    r0, c0 = int(round(rc0[0])), int(round(rc0[1]))
    a = np.asarray(img, float)[max(r0 - half, 0):r0 + half + 1, max(c0 - half, 0):c0 + half + 1]
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    w = (np.median(border) - a) if dark_dot else (a - np.median(border))
    w = np.clip(w, 0, None)
    w = np.where(w > 0.2 * w.max(), w, 0.0)
    if w.sum() <= 0:
        return float("nan"), float("nan")
    rr, cc = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    return (max(r0 - half, 0) + float((w * rr).sum() / w.sum()), max(c0 - half, 0) + float((w * cc).sum() / w.sum()))


def track(frames, rc_start, half: int = 12, dark_dot: bool = True) -> np.ndarray:
    out = []
    rc = rc_start
    for fr in frames:
        rc = centroid(fr, rc, half, dark_dot)
        out.append(rc)
    return np.array(out)


def _distort(params, px):
    """pixel -> mm: affine after radial undistortion about centre (cr, cc) with k1."""
    a, b, c, d, e, f, k1, cr, ccol = params
    r = px[:, 0] - cr
    q = px[:, 1] - ccol
    rho2 = (r * r + q * q) * 1e-6
    ru = cr + r * (1 + k1 * rho2)
    qu = ccol + q * (1 + k1 * rho2)
    return np.column_stack([a * ru + b * qu + c, d * ru + e * qu + f])


def calibrate_grid(px: np.ndarray, mm: np.ndarray, centre=None) -> Dict:
    """Fit the pixel -> mm map from grid dots (px as (row, col), mm as (x, y))."""
    px = np.asarray(px, float)
    mm = np.asarray(mm, float)
    P = np.column_stack([px, np.ones(len(px))])
    X, *_ = np.linalg.lstsq(P, mm, rcond=None)
    cr, ccol = (px.mean(axis=0) if centre is None else centre)
    p0 = [X[0, 0], X[1, 0], X[2, 0], X[0, 1], X[1, 1], X[2, 1], 0.0, cr, ccol]

    def res(p):
        return (_distort(p, px) - mm).ravel()

    r = optimize.least_squares(res, p0, x_scale="jac")
    e = res(r.x).reshape(-1, 2)
    return {"params": r.x.tolist(), "resid_rms_um": float(np.sqrt(np.mean(np.sum(e ** 2, axis=1))) * 1e3),
            "mm_per_px": float(np.sqrt(abs(r.x[0] * r.x[4] - r.x[1] * r.x[3])))}


def px_to_mm(cal: Dict, px: np.ndarray) -> np.ndarray:
    return _distort(np.asarray(cal["params"]), np.atleast_2d(np.asarray(px, float)))


def render_dot(shape, rc, sigma_px=2.5, depth=180.0, bg=220.0, noise=2.0, rng=None, blur_vec=(0.0, 0.0)):
    """Synthetic frame: a Gaussian dark dot (optionally smeared along blur_vec, px) on a flat
    background with Gaussian noise. Used by the self-test."""
    rng = rng or np.random.default_rng(0)
    rr, cc = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    img = np.zeros(shape)
    nsub = 5 if any(blur_vec) else 1
    for k in range(nsub):
        fr = (k / max(nsub - 1, 1) - 0.5) if nsub > 1 else 0.0
        r0 = rc[0] + fr * blur_vec[0]
        c0 = rc[1] + fr * blur_vec[1]
        img += np.exp(-((rr - r0) ** 2 + (cc - c0) ** 2) / (2 * sigma_px ** 2)) / nsub
    return bg - depth * img + noise * rng.standard_normal(shape)
