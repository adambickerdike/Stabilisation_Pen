"""Page-relative sensing qualification (EXP-T04, T05) on rig R10: error statistics of an optical
page sensor against encoder or camera ground truth, in DeltaPen's metric and per sample.

DeltaPen (Luethi, Fender, Holz, UIST 2022; LIT OPT-02, metric wording OPT-85) compared the
pen's translation with the differences of the Wacom tablet's absolute positions "at every
10 ms": mean absolute error of the translation magnitude 0.0683 mm, median 0.0236 mm. The paper
separately rotated the sensor values to get X and Y errors, so the magnitude metric is read here
as rotation-invariant: e_mag = | |ds| - |dg| | per 10 ms window. The protocol EXP-S01 (analysis
step 3) instead writes the norm of the vector difference |ds - dg|. Both are computed:
e_mag is the like-for-like comparison with DeltaPen; e_vec (>= e_mag) is what the controller needs.

Also reported: per-sample noise after a linear detrend per 100 ms (AC-S01-02, REQ-SNS-001), the
RMS position error over a stroke after scale calibration (REQ-RVJ-N06's 10 um RMS), the latency
(cross-correlation and phase slope), dropouts, and the fitted 2x2 scale-rotation matrix.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from . import sync

DELTAPEN_MAE_UM = 68.3       # LIT OPT-02 / OPT-85, per 10 ms window, Wacom Intuos 4 surface
DELTAPEN_MEDIAN_UM = 23.6


def integrate(t: np.ndarray, dx: np.ndarray, dy: np.ndarray, um_per_count: float) -> Dict:
    """Sensor increments (counts per report) to a position track (um), starting at zero."""
    x = np.cumsum(np.asarray(dx, float)) * um_per_count
    y = np.cumsum(np.asarray(dy, float)) * um_per_count
    return {"t": np.asarray(t, float), "xy": np.column_stack([x, y])}


def fit_matrix(sens_xy: np.ndarray, truth_xy: np.ndarray, stride: int = 50) -> Dict:
    """2x2 matrix A with truth increments ~= A @ sensor increments (scale, rotation, shear).
    Increments are taken over `stride` samples (50 ms at 1 kHz) so that position noise, which does
    not grow with the interval, does not bias A toward zero (errors in the regressor)."""
    ds = np.diff(sens_xy[::stride], axis=0)
    dg = np.diff(truth_xy[::stride], axis=0)
    A, *_ = np.linalg.lstsq(ds, dg, rcond=None)
    A = A.T
    u, s, vt = np.linalg.svd(A)
    rot = u @ vt
    ang = float(np.degrees(np.arctan2(rot[1, 0], rot[0, 0])))
    return {"A": A.tolist(), "scale_x": float(np.linalg.norm(A[:, 0])), "scale_y": float(np.linalg.norm(A[:, 1])),
            "rotation_deg": ang, "anisotropy": float(s[0] / s[1] - 1)}


def apply_matrix(A, sens_xy):
    return np.asarray(sens_xy) @ np.asarray(A).T


def window_errors(t_truth, g_xy, t_sens, s_xy, window_s=0.010, delay_s=0.0, valid=None) -> Dict:
    """Errors per non-overlapping window. The sensor track is shifted by delay_s (its latency,
    estimated separately) before comparison, so the metric scores accuracy, not lag; the lag is
    reported by latency(). Windows with any invalid sensor sample are excluded and counted."""
    t0 = max(t_truth[0], t_sens[0] - delay_s)
    t1 = min(t_truth[-1], t_sens[-1] - delay_s)
    edges = np.arange(t0, t1, window_s)
    g = np.column_stack([np.interp(edges, t_truth, g_xy[:, k]) for k in range(2)])
    s = np.column_stack([np.interp(edges + delay_s, t_sens, s_xy[:, k]) for k in range(2)])
    dg = np.diff(g, axis=0)
    ds = np.diff(s, axis=0)
    keep = np.ones(len(dg), bool)
    if valid is not None:
        bad_t = np.asarray(t_sens)[~np.asarray(valid, bool)] - delay_s
        idx = np.searchsorted(edges, bad_t) - 1
        idx = idx[(idx >= 0) & (idx < len(keep))]
        keep[idx] = False
    e_mag = np.abs(np.linalg.norm(ds, axis=1) - np.linalg.norm(dg, axis=1))[keep]
    e_vec = np.linalg.norm(ds - dg, axis=1)[keep]
    return {"n_windows": int(keep.sum()), "excluded_windows": int((~keep).sum()),
            "mag_mae_um": float(np.mean(e_mag)), "mag_median_um": float(np.median(e_mag)),
            "vec_mae_um": float(np.mean(e_vec)), "vec_median_um": float(np.median(e_vec)),
            "vec_p95_um": float(np.percentile(e_vec, 95)),
            "vs_deltapen_mae": float(np.mean(e_mag) / DELTAPEN_MAE_UM),
            "vs_deltapen_median": float(np.median(e_mag) / DELTAPEN_MEDIAN_UM)}


def per_sample_noise(t_truth, g_xy, t_sens, s_xy, delay_s=0.0, seg_s=0.1, valid=None) -> Dict:
    """RMS of (sensor - truth) after removing a straight line per 100 ms segment (AC-S01-02).
    Segments that contain an invalid sensor sample are skipped (a dropout loses counts, which is
    reported by dropouts() and stroke_error(), not as noise)."""
    g = np.column_stack([np.interp(t_sens - delay_s, t_truth, g_xy[:, k]) for k in range(2)])
    e = s_xy - g
    t = t_sens
    v = np.ones(len(t), bool) if valid is None else np.asarray(valid, bool)
    out = []
    k0 = 0
    while k0 < len(t):
        k1 = np.searchsorted(t, t[k0] + seg_s)
        if k1 - k0 >= 5 and v[k0:k1].all():
            tt = t[k0:k1] - t[k0]
            A = np.column_stack([np.ones_like(tt), tt])
            for c in range(2):
                coef, *_ = np.linalg.lstsq(A, e[k0:k1, c], rcond=None)
                out.append(e[k0:k1, c] - A @ coef)
        k0 = k1
    r = np.concatenate(out) if out else np.array([np.nan])
    return {"rms_um_per_axis": float(np.sqrt(np.mean(r ** 2)))}


def stroke_error(t_truth, g_xy, t_sens, s_xy, delay_s=0.0, valid=None) -> Dict:
    """RMS position error over the longest dropout-free run after removing its start offset
    (REQ-RVJ-N06 style), and the end-point drift per mm travelled."""
    v = np.ones(len(t_sens), bool) if valid is None else np.asarray(valid, bool)
    best, k, a0, a1 = 0, 0, 0, len(v)
    while k < len(v):
        if v[k]:
            j = k
            while j < len(v) and v[j]:
                j += 1
            if j - k > best:
                best, a0, a1 = j - k, k, j
            k = j
        else:
            k += 1
    t_sens, s_xy = np.asarray(t_sens)[a0:a1], np.asarray(s_xy)[a0:a1]
    g = np.column_stack([np.interp(t_sens - delay_s, t_truth, g_xy[:, k]) for k in range(2)])
    e = (s_xy - s_xy[0]) - (g - g[0])
    L = np.sum(np.linalg.norm(np.diff(g, axis=0), axis=1))
    return {"run_s": float(t_sens[-1] - t_sens[0]), "rms_um": float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))),
            "end_drift_um": float(np.linalg.norm(e[-1])),
            "drift_um_per_mm": float(np.linalg.norm(e[-1]) / max(L / 1000.0, 1e-9)), "path_mm": float(L / 1000.0)}


def latency(t_truth, g_xy, t_sens, s_xy, fs=1000.0, max_lag_s=0.02) -> Dict:
    """Sensor latency from velocity cross-correlation on a common grid, and from the phase slope."""
    t0, t1 = max(t_truth[0], t_sens[0]), min(t_truth[-1], t_sens[-1])
    tt = np.arange(t0, t1, 1 / fs)
    res = {}
    for k, name in ((0, "x"), (1, "y")):
        gv = np.gradient(np.interp(tt, t_truth, g_xy[:, k]), 1 / fs)
        sv = np.gradient(np.interp(tt, t_sens, s_xy[:, k]), 1 / fs)
        res[name] = sync.xcorr_delay(gv, sv, fs, max_lag_s)["delay_s"]
        res[name + "_phase"] = sync.phase_delay(gv, sv, fs, band=(1.0, 40.0))["delay_s"]
    res["delay_s"] = float(np.nanmean([res["x"], res["y"]]))
    return res


def dropouts(t_sens, valid) -> Dict:
    v = np.asarray(valid, bool)
    t = np.asarray(t_sens, float)
    bad = ~v
    longest = 0.0
    count = 0
    k = 0
    while k < len(v):
        if bad[k]:
            j = k
            while j < len(v) and bad[j]:
                j += 1
            count += 1
            longest = max(longest, t[min(j, len(t) - 1)] - t[k])
            k = j
        else:
            k += 1
    dur = t[-1] - t[0]
    return {"invalid_fraction": float(bad.mean()), "dropouts": count, "longest_s": float(longest),
            "per_minute": float(count / max(dur / 60.0, 1e-9))}


def report_rate(t_sens) -> Dict:
    dt = np.diff(np.asarray(t_sens, float))
    return {"rate_hz": float(1 / np.median(dt)), "dt_p99_ms": float(np.percentile(dt, 99) * 1e3),
            "dt_max_ms": float(dt.max() * 1e3)}


def qualify(t_truth, g_xy, t_sens, dx, dy, um_per_count, valid=None, cal_fraction=0.3) -> Dict:
    """Full qualification of one run: the first cal_fraction of the run fits the 2x2 matrix and the
    latency; the rest is scored (held out)."""
    tr = integrate(t_sens, dx, dy, um_per_count)
    n = len(t_sens)
    kc = int(cal_fraction * n)
    # latency and matrix are coupled (a rotated sensor mixes the quadrature axes of elliptical
    # tremor, which shifts the apparent phase): alternate the two fits twice
    s_xy = tr["xy"]
    M = {"A": np.eye(2).tolist()}
    for _ in range(3):
        lat = latency(t_truth, g_xy, t_sens[:kc], apply_matrix(M["A"], s_xy[:kc]))
        d = lat["delay_s"]
        gi = np.column_stack([np.interp(t_sens[:kc] - d, t_truth, g_xy[:, k]) for k in range(2)])
        M = fit_matrix(s_xy[:kc], gi)
    s_cal = apply_matrix(M["A"], tr["xy"])
    ts, ss = t_sens[kc:], s_cal[kc:]
    vv = None if valid is None else np.asarray(valid)[kc:]
    return {"report": report_rate(t_sens), "latency": lat, "matrix": M,
            "window_10ms": window_errors(t_truth, g_xy, ts, ss, 0.010, d, vv),
            "per_sample": per_sample_noise(t_truth, g_xy, ts, ss, d, valid=vv),
            "stroke": stroke_error(t_truth, g_xy, ts, ss, d, valid=vv),
            "dropouts": dropouts(t_sens, valid if valid is not None else np.ones(n, bool))}
