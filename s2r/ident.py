"""Identification and model-validation tools shared by the virtual-bench experiments.

* least squares (linear, weighted) and nonlinear least squares with a Laplace
  (Gauss-Newton) covariance: cov = s^2 (J^T J)^-1, the curvature of the
  likelihood at the optimum under a flat prior;
* bootstrap over records (case resampling) for percentile intervals;
* H1 frequency-response estimation over repeated records, with coherence and
  the Bendat-Piersol random-error estimate of |H|;
* second-order-plus-delay FRF fit (complex, weighted);
* residual diagnostics: autocorrelation and Ljung-Box whiteness, cross
  correlation with the input, normalised FRF misfit per band, and a chi-square
  test of parameter constancy across excitation levels;
* GUM combination of statistical (type A) and bound-type systematic (type B,
  rectangular) uncertainty.

Evidence status of anything computed with these on virtual-bench data:
CALCULATION on SIMULATION data.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence

import numpy as np
from scipy import optimize, stats


# --------------------------------------------------------------------------- least squares
def ols(X: np.ndarray, y: np.ndarray, w: Optional[np.ndarray] = None) -> Dict:
    """Weighted linear least squares y = X b. Returns b, Laplace covariance, residuals."""
    X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != len(y):
        X = X.T
    y = np.asarray(y, float)
    sw = np.ones(len(y)) if w is None else np.sqrt(np.asarray(w, float))
    Xw, yw = X * sw[:, None], y * sw
    b, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    r = yw - Xw @ b
    dof = max(len(y) - X.shape[1], 1)
    s2 = float(r @ r / dof)
    cov = s2 * np.linalg.pinv(Xw.T @ Xw)
    return {"b": b, "cov": cov, "se": np.sqrt(np.diag(cov)), "resid": y - X @ b, "s2": s2, "dof": dof}


def nls(resid_fn: Callable[[np.ndarray], np.ndarray], p0: Sequence[float], bounds=(-np.inf, np.inf),
        x_scale="jac", loss="linear", max_nfev=2000) -> Dict:
    """Nonlinear least squares with a Laplace covariance at the optimum."""
    r = optimize.least_squares(resid_fn, np.asarray(p0, float), bounds=bounds, x_scale=x_scale, loss=loss,
                               max_nfev=max_nfev)
    J = r.jac
    n, p = J.shape
    dof = max(n - p, 1)
    s2 = float(2 * r.cost / dof)
    try:
        cov = s2 * np.linalg.inv(J.T @ J)
    except np.linalg.LinAlgError:
        cov = s2 * np.linalg.pinv(J.T @ J)
    return {"p": r.x, "cov": cov, "se": np.sqrt(np.abs(np.diag(cov))), "resid": r.fun, "s2": s2,
            "success": bool(r.success), "dof": dof, "nfev": int(r.nfev)}


def bootstrap(units: Sequence, fit: Callable[[Sequence], np.ndarray], n_boot: int, rng: np.random.Generator):
    """Case bootstrap: refit on resampled units; returns an (n_boot, p) array (NaN rows dropped)."""
    out = []
    m = len(units)
    for _ in range(n_boot):
        idx = rng.integers(0, m, m)
        try:
            out.append(np.atleast_1d(fit([units[i] for i in idx])))
        except Exception:
            continue
    a = np.array(out, float)
    return a[np.all(np.isfinite(a), axis=1)] if a.ndim == 2 else a


def ci_from_samples(a: np.ndarray, level=0.95):
    lo, hi = np.percentile(a, [50 * (1 - level), 50 * (1 + level)], axis=0)
    return lo, hi


# --------------------------------------------------------------------------- uncertainty
def combine(value: float, u_stat: float, rel_bounds: Sequence[float] = (), abs_bounds: Sequence[float] = ()):
    """GUM: combined standard uncertainty of a value with type-A u_stat and type-B bounds
    (rectangular: u = b / sqrt(3)). Returns dict(u, U95 = 2u, parts)."""
    parts = {"stat": float(u_stat)}
    u2 = u_stat ** 2
    for i, b in enumerate(rel_bounds):
        ub = abs(value) * b / np.sqrt(3)
        parts[f"rel_bound_{i}"] = float(ub)
        u2 += ub ** 2
    for i, b in enumerate(abs_bounds):
        ub = b / np.sqrt(3)
        parts[f"abs_bound_{i}"] = float(ub)
        u2 += ub ** 2
    u = float(np.sqrt(u2))
    return {"u": u, "U95": 2 * u, "parts": parts}


# --------------------------------------------------------------------------- frequency response
def frf_h1(u_recs: Sequence[np.ndarray], y_recs: Sequence[np.ndarray], fs: float, fmin=0.0, fmax=np.inf,
           window: Optional[str] = None):
    """H1 = sum(Y U*) / sum(|U|^2) over records (each record one transient chirp or one
    period of a periodic signal). Returns f, H, coherence, sigma_H (1-sigma, complex magnitude)."""
    n = min(min(len(u) for u in u_recs), min(len(y) for y in y_recs))
    win = np.ones(n) if window is None else __import__("scipy.signal", fromlist=["get_window"]).get_window(window, n)
    Suu = 0.0
    Syy = 0.0
    Syu = 0.0
    for u, y in zip(u_recs, y_recs):
        U = np.fft.rfft((u[:n] - np.mean(u[:n])) * win)
        Y = np.fft.rfft((y[:n] - np.mean(y[:n])) * win)
        Suu = Suu + np.abs(U) ** 2
        Syy = Syy + np.abs(Y) ** 2
        Syu = Syu + Y * np.conj(U)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    with np.errstate(divide="ignore", invalid="ignore"):
        H = Syu / Suu
        coh = np.abs(Syu) ** 2 / (Suu * Syy)
    nd = len(u_recs)
    coh = np.clip(np.nan_to_num(coh), 1e-12, 1.0)
    # Bendat & Piersol (9.90): normalised random error of |H| ~ sqrt(1-g2)/(|g| sqrt(2 nd))
    with np.errstate(divide="ignore", invalid="ignore"):
        eps = np.sqrt((1 - coh) / (2 * max(nd, 1) * coh))
    sigma = np.abs(H) * eps
    m = (f >= fmin) & (f <= fmax) & np.isfinite(H)
    return f[m], H[m], coh[m], sigma[m]


def so_model(f, a, fn, zeta, tau, sign=-1.0):
    """Second-order plus delay: H = sign*a*exp(-j w tau)/(wn^2 - w^2 + 2j zeta wn w)."""
    w = 2 * np.pi * np.asarray(f)
    wn = 2 * np.pi * fn
    return sign * a * np.exp(-1j * w * tau) / (wn ** 2 - w ** 2 + 2j * zeta * wn * w)


def fit_second_order(f, H, sigma, p0=None, fit_delay=True, sign=-1.0):
    """Weighted complex fit of so_model. Parameters (a, fn, zeta, tau) with Laplace covariance.
    Residuals are normalised by sigma so s^2 ~ 1 when the noise model is right."""
    f = np.asarray(f)
    sig = np.maximum(np.asarray(sigma), 1e-3 * np.abs(H) + 1e-30)
    if p0 is None:
        k = np.argmax(np.abs(H))
        fn0 = f[k]
        a0 = np.abs(H[k]) * (2 * np.pi * fn0) ** 2 * 2 * 0.05
        p0 = [a0, fn0, 0.05, 0.0]
    lo = [0.0, 0.1, 1e-4, -2e-3]
    hi = [np.inf, 5e3, 2.0, 5e-3]

    def res(p):
        tau = p[3] if fit_delay else 0.0
        e = (so_model(f, p[0], p[1], p[2], tau, sign) - H) / sig
        return np.concatenate([e.real, e.imag])

    if not fit_delay:
        lo[3], hi[3] = -1e-12, 1e-12
        p0 = list(p0)
        p0[3] = 0.0
    r = nls(res, p0, bounds=(lo, hi), x_scale=np.abs(np.asarray(p0)) + np.array([0, 0, 0, 1e-5]))
    e = (so_model(f, *r["p"], sign=sign) - H) / sig
    r["norm_resid"] = e
    r["chi2_per_dof"] = float(np.sum(np.abs(e) ** 2) / max(2 * len(f) - 4, 1))
    return r


# --------------------------------------------------------------------------- diagnostics
def acf(x: np.ndarray, nlags: int) -> np.ndarray:
    x = np.asarray(x, float) - np.mean(x)
    n = len(x)
    c0 = x @ x / n
    return np.array([1.0] + [float(x[:-k] @ x[k:] / n / c0) for k in range(1, nlags + 1)])


def ljung_box(x: np.ndarray, nlags: int = 20) -> Dict:
    """Ljung-Box whiteness test. p < 0.01 -> residuals are not white (structure left)."""
    n = len(x)
    r = acf(x, nlags)[1:]
    Q = n * (n + 2) * np.sum(r ** 2 / (n - np.arange(1, nlags + 1)))
    p = float(stats.chi2.sf(Q, nlags))
    return {"Q": float(Q), "lags": nlags, "p": p, "white_at_1pct": bool(p >= 0.01),
            "acf_max_abs": float(np.max(np.abs(r))), "band_95": float(1.96 / np.sqrt(n))}


def xcorr_test(e: np.ndarray, u: np.ndarray, maxlag: int = 20) -> Dict:
    """Cross-correlation of residual e with past input u (lags 0..maxlag). A correct model
    leaves e uncorrelated with u (Ljung, System Identification, 16.6)."""
    e = np.asarray(e, float) - np.mean(e)
    u = np.asarray(u, float) - np.mean(u)
    n = len(e)
    den = np.sqrt((e @ e) * (u @ u))
    r = np.array([float(e[k:] @ u[:n - k] / den) for k in range(maxlag + 1)])
    Q = n * np.sum(r ** 2)
    p = float(stats.chi2.sf(Q, maxlag + 1))
    return {"max_abs": float(np.max(np.abs(r))), "band_95": float(1.96 / np.sqrt(n)), "Q": float(Q), "p": p,
            "uncorrelated_at_1pct": bool(p >= 0.01)}


def band_misfit(f: np.ndarray, norm_resid: np.ndarray, bands) -> list:
    """Mean |normalised complex residual|^2 per frequency band (1 = at the noise level)."""
    out = []
    for lo, hi in bands:
        m = (f >= lo) & (f < hi)
        if m.sum() == 0:
            continue
        chi = float(np.mean(np.abs(norm_resid[m]) ** 2) / 2.0)
        out.append({"band_hz": [lo, hi], "n": int(m.sum()), "chi2_per_dof": chi,
                    "p_consistent": float(stats.chi2.sf(chi * 2 * m.sum(), 2 * m.sum()))})
    return out


def drift_test(values: np.ndarray, sigmas: np.ndarray) -> Dict:
    """Chi-square test that a parameter identified at several excitation levels is constant."""
    v = np.asarray(values, float)
    s = np.asarray(sigmas, float)
    w = 1 / s ** 2
    mean = float(np.sum(w * v) / np.sum(w))
    chi2 = float(np.sum(w * (v - mean) ** 2))
    dof = len(v) - 1
    p = float(stats.chi2.sf(chi2, dof)) if dof > 0 else 1.0
    return {"weighted_mean": mean, "chi2": chi2, "dof": dof, "p": p, "constant_at_1pct": bool(p >= 0.01),
            "spread_rel": float((v.max() - v.min()) / abs(mean)) if mean != 0 else float("nan")}


def r2(y: np.ndarray, yhat: np.ndarray) -> float:
    y = np.asarray(y, float)
    return float(1 - np.sum((y - yhat) ** 2) / np.sum((y - np.mean(y)) ** 2))
