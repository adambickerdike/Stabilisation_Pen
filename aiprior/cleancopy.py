"""B: the app's digital clean copy of a recorded tip path (NON-CAUSAL; digital only).

The pen records its tip path: the page sensor gives the handle position and the nose Hall sensor the nose deflection
(or IMU + page sensor).  The app has the whole note, so it can look ahead and remove the tremor band with zero phase
before it displays and recognises the note.  The ink on the paper is whatever the causal pen wrote; the clean copy is a
derived digital layer that cites the original strokes (DEC-020 conventions), never a replacement of the ink.

Methods (all zero-phase; the tremor frequency is estimated from the recording itself, no simulator truth):
  bandstop   Butterworth band-stop around the tremor peak f_hat (and 2 f_hat), filtfilt
  wiener     non-causal Wiener smoother: the writing's spectrum is the running median (+-3 Hz) of the recording's
             own log spectrum, which follows the writing's slope but not narrow lines; the tremor's spectrum is the excess above twice that floor near
             f_hat and 2 f_hat; gain H = S_w / (S_w + beta S_d) applied by FFT to the recording minus its < 1.5 Hz
             part; nothing is changed unless the recording shows a clear line (peak-to-floor >= 3).
             With a stationary model this equals the steady-state forward-backward (RTS) Kalman smoother of an
             intent + tremor-oscillator model, without having to choose its noise levels.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

F_BAND = (4.5, 13.5)          # where the app looks for a tremor line (Hz).  Tuning writers 100-103: the glyph writers'
                              # stroke rhythm makes a 3-4 Hz bump (peak-to-floor 3.3-5.2) that a 3.5 Hz edge mistook
                              # for tremor; above 4.5 Hz tremor-free writing reads 1.0-1.5 and 1-2 mm tremor 5-47.
                              # A 4 Hz tremor (not in this study's grid) would need another cue (e.g. the IMU at rest).
F_NOTCH_MIN = 3.0             # the notch never reaches into the writing's core band below this (Hz)
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


def writing_floor(f: np.ndarray, P: np.ndarray, excl=(), half_window_hz: float = 3.0) -> np.ndarray:
    """The writing's smooth spectrum: running median of log P over +-half_window_hz.  A running median follows any
    monotonic slope or knee of the writing's spectrum exactly, but removes narrow lines (tremor, its harmonic).
    `excl` is kept for the interface: excluded bands are filled by the median of their surroundings anyway."""
    from scipy.ndimage import median_filter
    df = float(f[1] - f[0])
    k = max(3, 2 * int(round(half_window_hz / df)) + 1)
    lp = np.log(np.maximum(P, 1e-300))
    return np.exp(median_filter(lp, size=k, mode="nearest"))


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
            fh = float(f[i] + float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) * (f[1] - f[0]))
    return {"f_hat": fh, "peak_ratio": float(r[i])}


def bandstop_clean(t: np.ndarray, xy: np.ndarray, down: np.ndarray, f_hat: Optional[float] = None, half_width: float = 1.5,
                   order: int = 2, harmonic: bool = True) -> Tuple[np.ndarray, Dict]:
    """Zero-phase band-stop around f_hat (estimated from the recording if None) and its 2nd harmonic."""
    fs = _fs(t)
    info = tremor_peak(t, xy) if f_hat is None else {"f_hat": float(f_hat), "peak_ratio": float("nan")}
    fh = info["f_hat"]
    y = xy.copy()
    for k in ((1, 2) if harmonic else (1,)):
        lo, hi = max(k * fh - half_width, F_NOTCH_MIN), k * fh + half_width
        if hi >= 0.45 * fs or lo <= 0.5:
            continue
        sos = butter(order, [lo, hi], btype="bandstop", fs=fs, output="sos")
        y = sosfiltfilt(sos, y, axis=0)
    return y, info


def wiener_clean(t: np.ndarray, xy: np.ndarray, down: np.ndarray, f_hat: Optional[float] = None, beta: float = 2.0,
                 half_width: float = 2.0, h_min: float = 0.0, min_ratio: float = 3.0, margin: float = 2.0) -> Tuple[np.ndarray, Dict]:
    """Non-causal Wiener smoother (see the module docstring).  No correction if the recording shows no clear tremor
    line (peak-to-floor ratio below min_ratio; clean glyph writing reads 1.6-2.2 on the scorer's definition): clean
    writing is returned unchanged.  Only the excess above `margin` x the writing floor counts as tremor, so the writing's
    own spectral bumps are kept."""
    fs = _fs(t)
    f, P = spectrum(t, xy)
    info = tremor_peak(t, xy) if f_hat is None else {"f_hat": float(f_hat), "peak_ratio": float("nan")}
    fh = info["f_hat"]
    bands = [(max(fh - half_width, F_NOTCH_MIN), fh + half_width), (2 * fh - half_width, 2 * fh + half_width)]
    floor = writing_floor(f, P, excl=bands)
    ratio = info["peak_ratio"] if f_hat is None else float(np.max(P / np.maximum(floor, 1e-30)))
    info["applied"] = bool(ratio >= min_ratio)
    if not info["applied"]:
        return xy.copy(), info
    excess = np.maximum(P - margin * floor, 0.0)
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
