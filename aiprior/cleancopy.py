"""B: the app's digital clean copy of a recorded tip path (NON-CAUSAL; digital only).

The pen records its tip path: the page sensor gives the handle position and the nose Hall sensor the nose deflection
(or IMU + page sensor).  The app has the whole note, so it can look ahead and remove the tremor band with zero phase
before it displays and recognises the note.  The ink on the paper is whatever the causal pen wrote; the clean copy is a
derived digital layer that cites the original strokes (DEC-020 conventions), never a replacement of the ink.

Methods (all zero-phase; the tremor frequency is estimated from the recording itself, no simulator truth):
  bandstop   Butterworth band-stop around the tremor peak f_hat (and 2 f_hat), filtfilt
  wiener     non-causal Wiener smoother: the writing's spectrum is a robust power-law floor fitted to the recording's
             own spectrum outside the tremor band; the tremor's spectrum is the excess above that floor near f_hat
             and 2 f_hat; gain H = S_w / (S_w + beta S_d) applied by FFT to the recording minus its < 1.5 Hz part.
             With a stationary model this equals the steady-state forward-backward (RTS) Kalman smoother of an
             intent + tremor-oscillator model, without having to choose its noise levels.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

F_BAND = (3.5, 13.5)          # where the app looks for a tremor peak (Hz)
LOW_HZ = 1.5                  # the slow part (along the line) is kept untouched


def _fs(t: np.ndarray) -> float:
    return 1.0 / float(np.median(np.diff(t)))


def _split_slow(xy: np.ndarray, fs: float, fc: float = LOW_HZ) -> Tuple[np.ndarray, np.ndarray]:
    sos = butter(4, fc, fs=fs, output="sos")
    slow = sosfiltfilt(sos, xy, axis=0, padtype="odd", padlen=min(len(xy) - 1, int(3 * fs / fc)))
    return slow, xy - slow


def spectrum(t: np.ndarray, xy: np.ndarray, nperseg_s: float = 2.0) -> Tuple[np.ndarray, np.ndarray]:
    """Welch PSD of the fast part of the track, summed over x and y (m^2/Hz)."""
    fs = _fs(t)
    _, fast = _split_slow(xy, fs)
    n = int(min(len(xy), round(nperseg_s * fs)))
    f, P = welch(fast, fs=fs, nperseg=n, axis=0, detrend="constant")
    return f, P.sum(axis=1)


def writing_floor(f: np.ndarray, P: np.ndarray, excl=(), fit=(2.0, 30.0), iters: int = 4) -> np.ndarray:
    """Robust power-law fit log P = a + b log f over `fit`, excluding the `excl` bands and positive outliers."""
    m = (f >= fit[0]) & (f <= fit[1]) & (P > 0)
    for lo, hi in excl:
        m &= ~((f >= lo) & (f <= hi))
    lf, lp = np.log(f[m]), np.log(P[m])
    keep = np.ones(len(lf), bool)
    a = b = 0.0
    for _ in range(iters):
        if keep.sum() < 4:
            break
        b, a = np.polyfit(lf[keep], lp[keep], 1)
        r = lp - (a + b * lf)
        keep = r < 0.5                                   # peaks (tremor, writing rhythm) do not pull the floor up
    ff = np.maximum(f, 1e-3)
    return np.exp(a + b * np.log(ff))


def tremor_peak(t: np.ndarray, xy: np.ndarray, band=F_BAND) -> Dict[str, float]:
    """The tremor line the app sees: frequency of the largest excess over the writing floor in `band`, and the
    peak-to-floor ratio (as handwriting/score_recording.py; no simulator truth)."""
    f, P = spectrum(t, xy)
    floor = writing_floor(f, P)
    r = P / np.maximum(floor, 1e-30)
    m = (f >= band[0]) & (f <= band[1])
    i = int(np.flatnonzero(m)[np.argmax(r[m])])
    # parabolic refinement on log ratio
    fh = float(f[i])
    if 0 < i < len(f) - 1:
        y0, y1, y2 = np.log(r[i - 1:i + 2])
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-12:
            fh = float(f[i] + 0.5 * (y0 - y2) / den * (f[1] - f[0]))
    return {"f_hat": fh, "peak_ratio": float(r[i])}


def bandstop_clean(t: np.ndarray, xy: np.ndarray, down: np.ndarray, f_hat: Optional[float] = None, half_width: float = 1.5,
                   order: int = 2, harmonic: bool = True) -> Tuple[np.ndarray, Dict]:
    """Zero-phase band-stop around f_hat (estimated from the recording if None) and its 2nd harmonic."""
    fs = _fs(t)
    info = tremor_peak(t, xy) if f_hat is None else {"f_hat": float(f_hat), "peak_ratio": float("nan")}
    fh = info["f_hat"]
    y = xy.copy()
    for k in ((1, 2) if harmonic else (1,)):
        lo, hi = k * fh - half_width, k * fh + half_width
        if hi >= 0.45 * fs or lo <= 0.5:
            continue
        sos = butter(order, [lo, hi], btype="bandstop", fs=fs, output="sos")
        y = sosfiltfilt(sos, y, axis=0)
    return y, info


def wiener_clean(t: np.ndarray, xy: np.ndarray, down: np.ndarray, f_hat: Optional[float] = None, beta: float = 2.0,
                 half_width: float = 2.0, h_min: float = 0.0, min_ratio: float = 1.5) -> Tuple[np.ndarray, Dict]:
    """Non-causal Wiener smoother (see the module docstring).  No correction if the recording shows no tremor line
    (peak-to-floor ratio below min_ratio): clean writing is returned unchanged."""
    fs = _fs(t)
    f, P = spectrum(t, xy)
    info = tremor_peak(t, xy) if f_hat is None else {"f_hat": float(f_hat), "peak_ratio": float("nan")}
    fh = info["f_hat"]
    bands = [(fh - half_width, fh + half_width), (2 * fh - half_width, 2 * fh + half_width)]
    floor = writing_floor(f, P, excl=bands)
    ratio = info["peak_ratio"] if f_hat is None else float(np.max(P / np.maximum(floor, 1e-30)))
    info["applied"] = bool(ratio >= min_ratio)
    if not info["applied"]:
        return xy.copy(), info
    excess = np.maximum(P - floor, 0.0)
    inb = np.zeros_like(f, bool)
    for lo, hi in bands:
        inb |= (f >= lo) & (f <= hi)
    Sd = np.where(inb, excess, 0.0)
    slow, fast = _split_slow(xy, fs)
    n = len(fast)
    pad = int(min(n - 1, round(1.0 * fs)))
    fp = np.pad(fast, ((pad, pad), (0, 0)), mode="reflect")
    N = len(fp)
    F = np.fft.rfft(fp, axis=0)
    fg = np.fft.rfftfreq(N, 1.0 / fs)
    Sw_g = np.interp(fg, f, floor)
    Sd_g = np.interp(fg, f, Sd)
    H = Sw_g / np.maximum(Sw_g + beta * Sd_g, 1e-300)
    H = np.maximum(H, h_min)
    y = np.fft.irfft(F * H[:, None], n=N, axis=0)[pad:pad + n]
    info["gain_min"] = float(H[(fg > 2.0) & (fg < 20.0)].min())
    return slow + y, info


def clean_track(t, xy, down, method: str = "wiener", **kw) -> Tuple[np.ndarray, Dict]:
    if method == "wiener":
        return wiener_clean(t, xy, down, **kw)
    if method == "bandstop":
        return bandstop_clean(t, xy, down, **kw)
    if method == "none":
        return xy.copy(), {}
    raise KeyError(method)
