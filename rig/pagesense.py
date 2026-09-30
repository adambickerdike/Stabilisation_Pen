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
        # Include interpolation brackets and both shared window endpoints. A bad
        # sample exactly on a boundary invalidates each window that uses it.
        ts = np.asarray(t_sens)
        vv = np.asarray(valid, bool)
        lo = np.maximum(0, np.searchsorted(ts, edges[:-1] + delay_s, side="right") - 1)
        hi = np.minimum(len(ts) - 1, np.searchsorted(ts, edges[1:] + delay_s, side="left"))
        bad_prefix = np.concatenate(([0], np.cumsum(~vv)))
        keep &= (bad_prefix[hi + 1] - bad_prefix[lo]) == 0
    e_mag = np.abs(np.linalg.norm(ds, axis=1) - np.linalg.norm(dg, axis=1))[keep]
    e_vec = np.linalg.norm(ds - dg, axis=1)[keep]
    if not len(e_mag):
        return {"valid": False, "reason": "no complete valid windows", "n_windows": 0,
                "excluded_windows": int((~keep).sum()),
                **{key: float("nan") for key in ("mag_mae_um", "mag_median_um", "vec_mae_um", "vec_median_um",
                                                "vec_p95_um", "vs_deltapen_mae", "vs_deltapen_median")}}
    return {"valid": True, "n_windows": int(keep.sum()), "excluded_windows": int((~keep).sum()),
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
    best, k, a0, a1 = 0, 0, 0, 0
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
    if best < 2:
        return {"valid": False, "reason": "no valid run of at least two samples", "run_s": 0., "path_mm": 0.,
                "rms_um": float("nan"), "end_drift_um": float("nan"), "drift_um_per_mm": float("nan")}
    t_sens, s_xy = np.asarray(t_sens)[a0:a1], np.asarray(s_xy)[a0:a1]
    g = np.column_stack([np.interp(t_sens - delay_s, t_truth, g_xy[:, k]) for k in range(2)])
    e = (s_xy - s_xy[0]) - (g - g[0])
    L = np.sum(np.linalg.norm(np.diff(g, axis=0), axis=1))
    return {"valid": True, "run_s": float(t_sens[-1] - t_sens[0]), "rms_um": float(np.sqrt(np.mean(np.sum(e ** 2, axis=1)))),
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


# ------------------------------------------------------------------------------------------ sim2j page-noise model (EXP-J10 addition)
# sim2j/sensing.py (read-only here) models the page sensor as white noise per 1 kHz sample (page_noise), a latency
# (page_latency), and optionally a DeltaPen-like error drawn every 10 ms: a 2-D vector with lognormal magnitude
# (DP_MEDIAN, DP_SIGMA = sqrt(2 ln(mean/median))) and uniform direction, either HELD for its window (errors do not
# add up: 'deltapen_held') or ADDED to the previous ones ('deltapen_walk'). The functions below measure those
# quantities on paper and say which mode the data support, from the correlation of the 10 ms window errors:
#   P_k = position error at window k = h_k (held part) + W_k (walk part, W_k = W_{k-1} + w_k)
#   e_k = P_k - P_{k-1}:   E|e|^2 = 2 E|h|^2 + E|w|^2,   E[e_k . e_{k-1}] = -E|h|^2
# so the lag-1 covariance of the window errors separates the held and the walking parts.

def position_error_runs(t_truth, g_xy, t_sens, s_xy, delay_s=0.0, valid=None, window_s=0.010, min_run_s=0.5):
    """Position error P = (s - s0) - (g - g0) (um) every window_s along each dropout-free run of >= min_run_s."""
    t_sens = np.asarray(t_sens, float)
    v = np.ones(len(t_sens), bool) if valid is None else np.asarray(valid, bool)
    runs = []
    k = 0
    while k < len(v):
        if not v[k]:
            k += 1
            continue
        j = k
        while j < len(v) and v[j]:
            j += 1
        ta, tb = t_sens[k], t_sens[j - 1]
        if tb - ta >= min_run_s:
            tw = np.arange(ta, tb, window_s)
            s = np.column_stack([np.interp(tw, t_sens[k:j], np.asarray(s_xy)[k:j, c]) for c in range(2)])
            g = np.column_stack([np.interp(tw - delay_s, t_truth, np.asarray(g_xy)[:, c]) for c in range(2)])
            runs.append((s - s[0]) - (g - g[0]))
        k = j
    return runs


def _held_lognormal_for_window_stats(median_e, mean_e, n=200_000, seed=7):
    """(median, sigma) of a held lognormal-magnitude error h whose window difference |h_k - h_{k-1}| has the given
    median and mean (Monte Carlo inversion, fixed seed)."""
    rng = np.random.default_rng(seed)
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    a1, a2 = rng.uniform(0, 2 * np.pi, n), rng.uniform(0, 2 * np.pi, n)

    def stats(sig):
        m1, m2 = np.exp(sig * z1), np.exp(sig * z2)
        d = np.hypot(m1 * np.cos(a1) - m2 * np.cos(a2), m1 * np.sin(a1) - m2 * np.sin(a2))
        return np.median(d), np.mean(d)

    target = mean_e / median_e
    lo, hi = 1e-3, 3.0
    r_lo = stats(lo)[1] / stats(lo)[0]
    if target <= r_lo:
        sig = lo
    else:
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            md, mn = stats(mid)
            if mn / md < target:
                lo = mid
            else:
                hi = mid
        sig = 0.5 * (lo + hi)
    md, _ = stats(sig)
    return float(median_e / md), float(sig)


def page_error_model_from_runs(runs, window_s=0.010, drift_s=2.0, max_lag=20) -> Dict:
    """Held/walk split, sim2j parameters, drift over drift_s and the correlation of window errors.

    The split is fitted on the structure function V(L) = E|P_{k+L} - P_k|^2 = 2 E|h|^2 + L E|w|^2 over lags of 10 ms
    to drift_s (intercept: held part; slope: walk step), which is far better conditioned than the lag-1 covariance
    alone (also reported). The mode sim2j should use is the one that dominates V at drift_s."""
    es = [np.diff(P, axis=0) for P in runs if len(P) > 2]
    e = np.concatenate(es)
    v = float(np.mean(np.sum(e ** 2, axis=1)))
    c1 = float(np.sum([np.sum(x[1:] * x[:-1]) for x in es]) / max(sum(len(x) - 1 for x in es), 1))
    mag = np.linalg.norm(e, axis=1)
    med, mean = float(np.median(mag)), float(np.mean(mag))
    acf = []
    for L in range(1, max_lag + 1):
        num = np.sum([np.sum(x[L:] * x[:-L]) for x in es if len(x) > L])
        den = sum(len(x) - L for x in es if len(x) > L)
        acf.append(float(num / max(den, 1) / v) if v > 0 else float("nan"))
    Lmax = int(round(drift_s / window_s))
    lags = np.unique(np.round(np.geomspace(1, Lmax, 14)).astype(int))
    sf, Ls, Vs = [], [], []
    for L in lags:
        d = [np.sum((P[L:] - P[:-L]) ** 2, axis=1) for P in runs if len(P) > L]
        if not d:
            continue
        d = np.concatenate(d)
        Ls.append(L)
        Vs.append(float(np.mean(d)))
        sf.append({"lag_s": float(L * window_s), "rms_um": float(np.sqrt(np.mean(d))), "p95_um": float(np.sqrt(np.percentile(d, 95))),
                   "n": int(len(d))})
    Ls, Vs = np.array(Ls, float), np.array(Vs, float)
    W = 1.0 / np.maximum(Vs, 1e-12)                       # relative-error weighting across lags
    A = np.column_stack([np.full_like(Ls, 2.0), Ls]) * W[:, None]
    coef, *_ = np.linalg.lstsq(A, Vs * W, rcond=None)
    var_h, var_w = max(0.0, float(coef[0])), max(0.0, float(coef[1]))
    V_end = 2 * var_h + Lmax * var_w
    walk_share = float(Lmax * var_w / V_end) if V_end > 0 else float("nan")
    mode = "deltapen_held" if walk_share < 1 / 3 else ("deltapen_walk" if walk_share > 2 / 3 else "mixed")
    dd = [np.linalg.norm(P[Lmax:] - P[:-Lmax], axis=1) for P in runs if len(P) > Lmax]
    dd = np.concatenate(dd) if dd else np.array([np.nan])
    held_med, held_sig = _held_lognormal_for_window_stats(med, mean) if med > 0 else (float("nan"), float("nan"))
    return {
        "window_s": window_s, "n_windows": int(len(e)), "n_runs": len(runs),
        "window_error_um": {"vec_median": med, "vec_mean": mean, "vec_p95": float(np.percentile(mag, 95))},
        "held_rms_um": float(np.sqrt(var_h)), "walk_step_rms_um": float(np.sqrt(var_w)),
        "walk_share_at_drift_s": walk_share,
        "lag1_correlation": float(c1 / v) if v > 0 else float("nan"),
        "lag1_estimate": {"held_rms_um": float(np.sqrt(max(0.0, -c1))), "walk_step_rms_um": float(np.sqrt(max(0.0, v + 2 * c1)))},
        "acf": acf, "mode_supported": mode,
        "sim2j": {
            "page_error": mode if mode != "mixed" else "deltapen_held (lower bound) and deltapen_walk (upper bound)",
            "DP_MEDIAN_walk_m": med * 1e-6, "DP_SIGMA_walk": float(np.sqrt(2 * np.log(max(mean / med, 1.0)))),
            "DP_MEDIAN_held_m": held_med * 1e-6, "DP_SIGMA_held": held_sig,
            "note": "walk: the window error itself is the sim2j draw; held: the draw is a position error, so its "
                    "(median, sigma) are inverted to reproduce the measured window-error median and mean"},
        "drift": {"over_s": drift_s, "walk_rms_um": float(np.sqrt(Lmax * var_w)),
                  "raw_rms_um": float(np.sqrt(np.nanmean(dd ** 2))), "raw_p95_um": float(np.nanpercentile(dd, 95)),
                  "raw_max_um": float(np.nanmax(dd)), "n": int(np.sum(np.isfinite(dd))),
                  "note": "raw = |P(t + drift_s) - P(t)|, which contains the held error at both ends (a pure held error "
                          "of DeltaPen's size already gives a raw p95 near or above 0.1 mm); walk = the accumulated part "
                          "sqrt(L var_w) fitted from the structure function: the quantity REQ-RVJ-C05's drift means"},
        "structure_function": sf,
    }


def sim2j_page_model(t_truth, g_xy, t_sens, s_xy, delay_s=0.0, valid=None, per_sample_rms_um=None, window_s=0.010,
                     drift_s=2.0) -> Dict:
    """The measured page-noise model in sim2j/sensing.py's terms (EXP-J10 addition). Adds the per-sample white noise
    (page_noise) and the latency (page_latency) when given, and the proposed REQ-RVJ-C05 verdict inputs."""
    runs = position_error_runs(t_truth, g_xy, t_sens, s_xy, delay_s, valid, window_s)
    m = page_error_model_from_runs(runs, window_s, drift_s)
    m["sim2j"]["page_latency_s"] = float(delay_s)
    if per_sample_rms_um is not None:
        m["sim2j"]["page_noise_m"] = float(per_sample_rms_um) * 1e-6
    w = window_errors(t_truth, g_xy, t_sens, s_xy, window_s, delay_s, valid)
    m["deltapen_metric"] = {"mag_median_um": w["mag_median_um"], "mag_mean_um": w["mag_mae_um"]}
    m["req_rvj_c05"] = {"drift_walk_um": m["drift"]["walk_rms_um"], "drift_raw_p95_um": m["drift"]["raw_p95_um"],
                        "drift_line_um": 100.0,
                        "window_median_um": w["mag_median_um"], "window_mean_um": w["mag_mae_um"],
                        "deltapen_median_um": DELTAPEN_MEDIAN_UM, "deltapen_mean_um": DELTAPEN_MAE_UM}
    return m


class patch_sim2j:
    """Context manager that loads a measured model into sim2j's page-sensor code for one run, without editing sim2j:
        with patch_sim2j(model, sensing_module, run_study_module): run_study_module.stage_page_noise()
    It sets sensing.DP_MEDIAN / DP_SIGMA to the measured values for the supported mode and restricts
    run_study.PAGE_MODELS to ('white', mode). Where results are written is sim2j's business (its owner runs it)."""

    def __init__(self, model: Dict, sensing, run_study=None, mode: str = None):
        self.m, self.s, self.r = model, sensing, run_study
        sup = model["mode_supported"]
        self.mode = mode or ("deltapen_walk" if sup == "deltapen_walk" else "deltapen_held")
        self.saved = {}

    def __enter__(self):
        key = "walk" if self.mode == "deltapen_walk" else "held"
        self.saved = {"DP_MEDIAN": self.s.DP_MEDIAN, "DP_SIGMA": self.s.DP_SIGMA}
        self.s.DP_MEDIAN = self.m["sim2j"][f"DP_MEDIAN_{key}_m"]
        self.s.DP_SIGMA = self.m["sim2j"][f"DP_SIGMA_{key}"]
        if self.r is not None:
            self.saved["PAGE_MODELS"] = self.r.PAGE_MODELS
            self.r.PAGE_MODELS = ("white", self.mode)
        return self

    def __exit__(self, *exc):
        self.s.DP_MEDIAN, self.s.DP_SIGMA = self.saved["DP_MEDIAN"], self.saved["DP_SIGMA"]
        if self.r is not None:
            self.r.PAGE_MODELS = self.saved["PAGE_MODELS"]
        return False
