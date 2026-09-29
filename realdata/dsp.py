"""Signal processing for recorded tremor and writing (CALC).

Every filter here that is marked ZERO-PHASE uses future samples.  That is allowed ONLY because the outputs are
simulation INPUTS (the tremor a simulated hand makes) or offline statistics.  No tracker or controller may use them:
in the simulations the trackers see only the simulated sensor streams.

Definitions used for every recording (the same for tablet displacement, pen acceleration and wrist acceleration):
  f0             peak of the Welch spectrum (4 s windows, 50 % overlap) inside 3-12 Hz, summed over axes
  peak_to_floor  spectral power in f0 +- 0.5 Hz divided by the median power density in 2-20 Hz outside f0 +- 1 Hz and
                 2 f0 +- 1 Hz, times the band width (so white noise gives about 1)
  line_fraction  share of the 2-20 Hz power inside f0 +- 1 Hz
  harmonic       amplitude ratio of the second harmonic: sqrt(P(2 f0 +- 0.75 Hz) / P(f0 +- 0.75 Hz))
  amplitude      the recording's tremor is band-limited to f0 +- 2 Hz (zero-phase), its principal (major) axis is
                 taken (PCA), and the Hilbert envelope gives the instantaneous peak amplitude; 'amp_median' is its
                 median (for a steady sinusoid: the sinusoid's amplitude, the definition of TremorSpec.amp_pk),
                 'amp_p90' its 90th percentile
  env_cv         SD / mean of that envelope (the project's tremor model calls this 'am_depth')
  f_sd           SD of the instantaneous frequency (Hilbert phase, 0.25 s median filter): the frequency wander
  ellipticity    RMS of the minor axis / RMS of the major axis of the f0 +- 2 Hz motion (2-D and 3-D data)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.signal import butter, hilbert, medfilt, sosfiltfilt, welch


# ------------------------------------------------------------------ resampling
def segments(t: np.ndarray, max_gap: float) -> List[Tuple[int, int]]:
    """Index ranges [a, b) of runs without a time gap longer than max_gap."""
    t = np.asarray(t, float)
    dt = np.diff(t)
    cut = np.flatnonzero((dt > max_gap) | (dt < 0)) + 1
    edges = np.r_[0, cut, len(t)]
    return [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b - a >= 2]


def uniform(t: np.ndarray, x: np.ndarray, fs: float, kind: str = "cubic") -> Tuple[np.ndarray, np.ndarray]:
    """Resample (t, x) (strictly increasing t after removing repeats) onto a uniform grid at fs."""
    from scipy.interpolate import CubicSpline
    t = np.asarray(t, float)
    x = np.asarray(x, float)
    keep = np.r_[True, t[1:] > np.maximum.accumulate(t)[:-1]]
    t, x = t[keep], x[keep]
    tu = np.arange(t[0], t[-1], 1.0 / fs)
    if kind == "cubic" and len(t) >= 4:
        xu = CubicSpline(t, x, axis=0)(tu)
    else:
        xu = np.column_stack([np.interp(tu, t, x[:, j]) for j in range(x.shape[1])]) if x.ndim == 2 else np.interp(tu, t, x)
    return tu - tu[0], xu


# ------------------------------------------------------------------ zero-phase band limits (NON-CAUSAL: inputs only)
def bandpass(x: np.ndarray, fs: float, lo: float, hi: float, order: int = 4) -> np.ndarray:
    """ZERO-PHASE Butterworth band-pass (sosfiltfilt). NON-CAUSAL: simulation inputs and statistics only."""
    hi = min(hi, 0.45 * fs)
    sos = butter(order, [lo, hi], btype="band", fs=fs, output="sos")
    return sosfiltfilt(sos, np.asarray(x, float), axis=0)


def lowpass(x: np.ndarray, fs: float, fc: float, order: int = 4) -> np.ndarray:
    """ZERO-PHASE Butterworth low-pass. NON-CAUSAL."""
    sos = butter(order, min(fc, 0.45 * fs), btype="low", fs=fs, output="sos")
    return sosfiltfilt(sos, np.asarray(x, float), axis=0)


def acc_to_disp(a: np.ndarray, fs: float, lo: float, hi: float, taper: float = 0.5) -> np.ndarray:
    """Displacement from acceleration inside [lo, hi] Hz by division with -(2 pi f)^2 in the frequency domain, with
    raised-cosine edges of width `taper` Hz; zero outside.  NON-CAUSAL (whole-record FFT): inputs and statistics only."""
    a = np.asarray(a, float)
    one = a.ndim == 1
    A = a[:, None] if one else a
    n = len(A)
    nfft = 1 << int(math.ceil(math.log2(n + int(2 * fs))))       # zero padding (>= 2 s) against wrap-around
    X = np.fft.rfft(A - A.mean(axis=0), n=nfft, axis=0)
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    w = np.zeros_like(f)
    m = (f >= lo) & (f <= hi)
    w[m] = 1.0
    e1 = (f > lo - taper) & (f < lo)
    w[e1] = 0.5 * (1 - np.cos(np.pi * (f[e1] - (lo - taper)) / taper))
    e2 = (f > hi) & (f < hi + taper)
    w[e2] = 0.5 * (1 + np.cos(np.pi * (f[e2] - hi) / taper))
    H = np.zeros_like(f)
    nz = f > 0
    H[nz] = -w[nz] / (2 * np.pi * f[nz]) ** 2
    d = np.fft.irfft(X * H[:, None], n=nfft, axis=0)[:n]
    return d[:, 0] if one else d


# ------------------------------------------------------------------ spectra and parameters
def psd(x: np.ndarray, fs: float, seg_s: float = 4.0) -> Tuple[np.ndarray, np.ndarray]:
    """Welch PSD summed over axes (x: (n,) or (n, k)); linear detrend per segment."""
    X = np.asarray(x, float)
    X = X[:, None] if X.ndim == 1 else X
    nper = int(min(len(X), round(seg_s * fs)))
    f, P = welch(X, fs=fs, nperseg=nper, noverlap=nper // 2, detrend="linear", axis=0)
    return f, P.sum(axis=1)


def _band_power(f, P, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.trapezoid(P[m], f[m])) if m.sum() > 1 else float(P[m].sum() * (f[1] - f[0]))


def principal_axes(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eigen-decomposition of the covariance (descending): values, vectors (columns) and the projected signal."""
    C = np.cov(X.T)
    lam, V = np.linalg.eigh(np.atleast_2d(C))
    o = np.argsort(lam)[::-1]
    lam, V = lam[o], V[:, o]
    return lam, V, X @ V


def envelope_stats(m: np.ndarray, fs: float, trim_s: float = 0.5) -> Dict:
    """Hilbert envelope and instantaneous frequency of a narrow-band 1-D signal."""
    z = hilbert(m)
    env = np.abs(z)
    ph = np.unwrap(np.angle(z))
    fi = np.gradient(ph) * fs / (2 * np.pi)
    k = max(3, int(0.25 * fs) | 1)
    k = min(k, (len(fi) // 2) * 2 - 1) if len(fi) > 5 else 3
    fi = medfilt(fi, k)
    tr = int(trim_s * fs)
    sl = slice(tr, len(m) - tr) if len(m) > 4 * tr else slice(None)
    e, f = env[sl], fi[sl]
    return {"amp_median": float(np.median(e)), "amp_p90": float(np.percentile(e, 90)), "amp_p99": float(np.percentile(e, 99)),
            "env_cv": float(np.std(e) / max(np.mean(e), 1e-30)), "f_inst_mean": float(np.mean(f)),
            "f_sd": float(np.std(f)), "env": env, "f_inst": fi}


def background(f: np.ndarray, P: np.ndarray, lo: float = 1.5, hi: float = 25.0, iters: int = 4,
               clip: float = 0.25) -> np.ndarray:
    """Smooth broadband background of a PSD: a quadratic in log10 P against log10 f over [lo, hi] Hz, refitted with
    the bins more than `clip` decades above the fit masked (spectral lines), evaluated on every bin (CALC).  The
    slow drawing or writing and the sensor noise make this background; tremor is a line above it."""
    m = (f >= lo) & (f <= hi) & (P > 0)
    x = np.log10(f[m])
    y = np.log10(P[m])
    use = np.ones(len(x), bool)
    c = np.polyfit(x, y, 2)
    for _ in range(iters):
        r = y - np.polyval(c, x)
        use = r < clip
        if use.sum() < 6:
            break
        c = np.polyfit(x[use], y[use], 2)
    B = np.full_like(P, np.nan)
    ok = f > 0
    B[ok] = 10 ** np.polyval(c, np.log10(np.clip(f[ok], lo, hi)))
    return B


def tremor_params(x: np.ndarray, fs: float, band=(3.0, 12.0), floor_band=(2.0, 20.0), half_width: float = 2.0,
                  keep_signals: bool = False) -> Dict:
    """The parameters defined in the module docstring, for a (n,) or (n, k) signal (displacement or acceleration).
    The tremor line is found against the fitted broadband background (``background``): f0 maximises the ratio of
    the spectrum to its background inside `band` (3-bin smoothed).  ZERO-PHASE band limits: statistics only."""
    X = np.asarray(x, float)
    X = X[:, None] if X.ndim == 1 else X
    X = X - X.mean(axis=0)
    f, P = psd(X, fs)
    df = f[1] - f[0]
    B = background(f, P)
    R = np.convolve(P / np.where(B > 0, B, np.inf), np.ones(3) / 3, mode="same")
    mb = (f >= band[0]) & (f <= band[1])
    i0 = int(np.flatnonzero(mb)[np.argmax(R[mb])])
    f0 = float(f[i0])
    mw = np.abs(f - f0) <= 0.5
    ex = np.clip(P - B, 0.0, None)
    if ex[mw].sum() > 0:
        f0 = float(np.sum(f[mw] * ex[mw]) / np.sum(ex[mw]))
    ratio = float(R[i0])
    fl = (f >= floor_band[0]) & (f <= floor_band[1]) & (np.abs(f - f0) > 1.0) & (np.abs(f - 2 * f0) > 1.0)
    floor = float(np.median(P[fl])) if fl.any() else float("nan")
    ptf = _band_power(f, P, f0 - 0.5, f0 + 0.5) / max(floor, 1e-300)
    tot = _band_power(f, P, *floor_band)
    line_frac = _band_power(f, P, f0 - 1.0, f0 + 1.0) / max(tot, 1e-300)
    p1 = _band_power(f, P, f0 - 0.75, f0 + 0.75)
    p2 = _band_power(f, P, 2 * f0 - 0.75, 2 * f0 + 0.75) if 2 * f0 + 0.75 < fs / 2 else float("nan")
    harm = math.sqrt(p2 / p1) if p1 > 0 and np.isfinite(p2) else float("nan")
    e1 = _band_power(f, ex, f0 - 0.75, f0 + 0.75)
    e2 = _band_power(f, ex, 2 * f0 - 0.75, 2 * f0 + 0.75) if 2 * f0 + 0.75 < fs / 2 else float("nan")
    harm_ex = math.sqrt(e2 / e1) if e1 > 0 and np.isfinite(e2) else float("nan")
    lo = max(1.0, f0 - half_width)
    nb = bandpass(X, fs, lo, f0 + half_width)
    lam, V, Y = principal_axes(nb) if X.shape[1] > 1 else (np.array([np.var(nb)]), np.eye(1), nb)
    major = Y[:, 0]
    es = envelope_stats(major, fs)
    ell = float(math.sqrt(max(lam[1], 0.0) / max(lam[0], 1e-300))) if len(lam) > 1 else 0.0
    ori = float(math.degrees(math.atan2(V[1, 0], V[0, 0]))) if V.shape[0] > 1 else float("nan")
    # excess power over the background in f0 +- 1.5 Hz -> amplitude of the major axis of an ellipse with the measured
    # ellipticity (power of a sinusoid of amplitude A is A^2 / 2)
    pex = _band_power(f, ex, f0 - 1.5, f0 + 1.5)
    amp_ex = math.sqrt(2.0 * pex / (1.0 + ell ** 2))
    bg_share = 1.0 - pex / max(_band_power(f, P, f0 - 1.5, f0 + 1.5), 1e-300)
    b312 = bandpass(X, fs, band[0], band[1])
    out = {"f0": f0, "line_ratio": ratio, "peak_to_floor": float(ptf), "line_fraction": float(line_frac),
           "harmonic": harm, "harmonic_excess": harm_ex, "amp_excess": amp_ex, "background_share": float(bg_share),
           "amp_median": es["amp_median"], "amp_p90": es["amp_p90"], "amp_p99": es["amp_p99"], "env_cv": es["env_cv"],
           "f_sd": es["f_sd"], "f_inst_mean": es["f_inst_mean"], "ellipticity": ell, "orientation_deg": ori,
           "band_rms": float(np.sqrt(np.mean(np.sum(b312 ** 2, axis=1)))), "duration_s": float(len(X) / fs),
           "psd_df": float(df)}
    if keep_signals:
        out["_f"], out["_P"], out["_B"] = f, P, B
        out["_major"], out["_env"] = major, es["env"]
    return out


def spectrum_on_grid(x: np.ndarray, fs: float, grid: np.ndarray) -> np.ndarray:
    """Welch PSD (summed over axes) interpolated onto a common frequency grid (for averaged spectra)."""
    f, P = psd(x, fs)
    return np.interp(grid, f, P)


def tremor_band_for(f0: float) -> Tuple[float, float]:
    """The band kept in a tremor-only waveform: the fundamental and the second harmonic, and nothing of the slow
    drawing or writing: [max(2, 0.6 f0), min(2.6 f0, 25)] Hz (ASSUMPTION, fixed before the test split was used)."""
    return max(2.0, 0.6 * f0), min(2.6 * f0, 25.0)
