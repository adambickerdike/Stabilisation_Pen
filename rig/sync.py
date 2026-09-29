"""One clock for every instrument: the coded sync pulse, clock mapping and delay estimation.

PROPOSED DESIGN, following validation/bench_protocols.md section 0.4:
- the rig DAQ emits a TTL pulse every second whose width encodes an 8-bit counter;
- any device under test (a pen prototype with its own MCU, a tablet PC, a camera PC)
  records the edges on its own clock;
- the host maps the device clock onto the DAQ clock with an affine fit
  t_daq = a + b * t_dev over all identified pulses, and reports the residuals.
  Required alignment: <= 50 us (section 0.4); the fit reports max |residual|.

Width code: w = W0 + n * DW with W0 = 1 ms and DW = 0.1 ms (n = 0..255, 1.0-26.5 ms).
Any width decoder with +-40 us error identifies n uniquely.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

PERIOD_S = 1.0
W0_S = 1.0e-3
DW_S = 0.1e-3
ALIGN_REQUIRED_S = 50e-6   # bench_protocols.md section 0.4


def width_for(n: int) -> float:
    return W0_S + (int(n) & 0xFF) * DW_S


def decode_widths(t_rise: np.ndarray, t_fall: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Pair each rising edge with the next falling edge and decode the counter.
    Returns (t_rise_paired, n). Unpairable or out-of-code pulses are dropped."""
    t_rise = np.asarray(t_rise, float)
    t_fall = np.asarray(t_fall, float)
    out_t, out_n = [], []
    j = 0
    for tr in t_rise:
        while j < len(t_fall) and t_fall[j] <= tr:
            j += 1
        if j >= len(t_fall):
            break
        w = t_fall[j] - tr
        n = (w - W0_S) / DW_S
        k = int(round(n))
        if 0 <= k <= 255 and abs(n - k) < 0.4:
            out_t.append(tr)
            out_n.append(k)
    return np.array(out_t), np.array(out_n, int)


def unwrap_counter(n: np.ndarray) -> np.ndarray:
    """8-bit counter to a monotonic pulse index."""
    n = np.asarray(n, int)
    if len(n) == 0:
        return n
    d = np.diff(n) % 256
    return np.concatenate([[n[0]], n[0] + np.cumsum(d)])


def fit_clock(t_dev_rise, n_dev, t_daq_rise, n_daq) -> Dict:
    """Map device time to DAQ time using pulses identified by their counters.

    Returns offset a (s), rate b (-), drift in ppm, residual RMS and max (s), the number of
    pulses used, and whether the 50 us requirement is met."""
    kd = unwrap_counter(n_dev)
    kq = unwrap_counter(n_daq)
    # align the unwrapped indices through the first common raw counter value
    common = np.intersect1d(np.asarray(n_dev) % 256, np.asarray(n_daq) % 256)
    if len(common) == 0:
        raise ValueError("no common sync counter between the device and the DAQ")
    c0 = common[0]
    kd = kd - kd[np.argmax(np.asarray(n_dev) % 256 == c0)]
    kq = kq - kq[np.argmax(np.asarray(n_daq) % 256 == c0)]
    pairs = {k: t for k, t in zip(kq, t_daq_rise)}
    x, y = [], []
    for k, t in zip(kd, t_dev_rise):
        if k in pairs:
            x.append(t)
            y.append(pairs[k])
    x, y = np.asarray(x), np.asarray(y)
    if len(x) < 3:
        raise ValueError("fewer than 3 matched sync pulses")
    A = np.column_stack([np.ones_like(x), x - x[0]])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ coef
    a = coef[0] - coef[1] * x[0]
    return {"offset_s": float(a), "rate": float(coef[1]), "drift_ppm": float((coef[1] - 1) * 1e6),
            "residual_rms_s": float(np.sqrt(np.mean(res ** 2))), "residual_max_s": float(np.max(np.abs(res))),
            "n_pulses": int(len(x)), "meets_50us": bool(np.max(np.abs(res)) <= ALIGN_REQUIRED_S)}


def map_time(t_dev, fit: Dict) -> np.ndarray:
    return fit["offset_s"] + fit["rate"] * np.asarray(t_dev, float)


# ------------------------------------------------------------------ delay estimation
def xcorr_delay(ref: np.ndarray, sig: np.ndarray, fs: float, max_lag_s: float = 0.05, upsample: int = 32) -> Dict:
    """Delay of sig relative to ref (positive: sig lags) from the peak of the cross-correlation,
    refined by band-limited interpolation (zero-padding the cross-spectrum by `upsample`) and a
    parabola on the interpolated peak. Both signals at the same rate fs."""
    ref = np.asarray(ref, float) - np.mean(ref)
    sig = np.asarray(sig, float) - np.mean(sig)
    n = min(len(ref), len(sig))
    ref, sig = ref[:n], sig[:n]
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    X = np.fft.rfft(sig, nfft) * np.conj(np.fft.rfft(ref, nfft))
    cc = np.fft.irfft(X, nfft)
    L = int(round(max_lag_s * fs))
    lags = np.concatenate([np.arange(0, L + 1), np.arange(-L, 0)])
    vals = np.concatenate([cc[:L + 1], cc[-L:]])
    k0 = int(lags[int(np.argmax(vals))])
    # band-limited interpolation around the integer peak: evaluate the correlation on a fine grid
    # from the cross-spectrum directly (exact trigonometric interpolation of the circular xcorr)
    f = np.arange(len(X))
    fine = k0 + np.linspace(-1.5, 1.5, 3 * upsample + 1)
    w = np.ones(len(X))
    w[1:-1] = 2.0
    vals_f = np.array([np.sum(w * np.real(X * np.exp(2j * np.pi * f * d / nfft))) for d in fine]) / nfft
    j = int(np.argmax(vals_f))
    if 0 < j < len(fine) - 1:
        ym1, y0, yp1 = vals_f[j - 1], vals_f[j], vals_f[j + 1]
        den = ym1 - 2 * y0 + yp1
        frac = 0.5 * (ym1 - yp1) / den if den != 0 else 0.0
        lag = fine[j] + frac * (fine[1] - fine[0])
    else:
        lag = fine[j]
    norm = np.sqrt(np.sum(ref ** 2) * np.sum(sig ** 2))
    return {"delay_s": float(lag / fs), "peak_corr": float(vals_f[j] / norm) if norm > 0 else 0.0}


def phase_delay(ref: np.ndarray, sig: np.ndarray, fs: float, band=(1.0, 30.0), nseg: int = 8) -> Dict:
    """Group delay from the slope of the cross-spectrum phase over a band (Welch averaging).
    Robust for band-limited motion (tremor multitones) where the correlation peak is broad."""
    from scipy import signal as sps
    nper = max(256, int(len(ref) // nseg))
    f, Pxy = sps.csd(ref, sig, fs=fs, nperseg=nper)
    _, Pxx = sps.welch(ref, fs=fs, nperseg=nper)
    m = (f >= band[0]) & (f <= band[1]) & (Pxx > 1e-6 * Pxx.max())
    ph = np.unwrap(np.angle(Pxy[m]))
    w = np.abs(Pxy[m])
    if m.sum() < 3:
        return {"delay_s": float("nan"), "n_bins": int(m.sum())}
    A = np.column_stack([np.ones(m.sum()), 2 * np.pi * f[m]])
    W = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(A * W[:, None], ph * W, rcond=None)
    return {"delay_s": float(-coef[1]), "n_bins": int(m.sum())}


def step_latency(t: np.ndarray, ref: np.ndarray, sig: np.ndarray, t_steps: np.ndarray, window_s: float = 0.05,
                 level: float = 0.5) -> np.ndarray:
    """Per-step latency: time at which sig crosses `level` of its step minus the time ref does.
    ref and sig sampled on the common time base t (interpolate first)."""
    out = []
    for ts in t_steps:
        m = (t >= ts - 0.2 * window_s) & (t <= ts + window_s)
        if m.sum() < 5:
            out.append(np.nan)
            continue
        tt = t[m]

        def cross(x):
            x = x[m]
            x0, x1 = np.median(x[:max(2, len(x) // 10)]), np.median(x[-max(2, len(x) // 10):])
            if abs(x1 - x0) < 1e-12:
                return np.nan
            y = (x - x0) / (x1 - x0)
            k = np.argmax(y >= level)
            if k == 0:
                return np.nan
            return tt[k - 1] + (level - y[k - 1]) * (tt[k] - tt[k - 1]) / (y[k] - y[k - 1])

        out.append(cross(sig) - cross(ref))
    return np.array(out)
