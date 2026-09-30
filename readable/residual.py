"""The three kinds of residual tremor of EXP-E13, built on the perfect-knowledge nose command (pure functions).

The perfect-knowledge command is R's (handwriting.tracker.oracle_command): q_o(t) = -d(t + servo group delay), d = the
true handle tremor (handle with tremor - handle without, nose held).  Each residual type changes q_o so that a known
kind of error is left at the tip:
  (a) amplitude   q = (1 - rho) q_o                 leaves rho x the tremor (an amplitude error only; rho = 1 - k)
  (b) lag         q(t) = q_o(t - tau)               the perfect estimate delayed by tau: a lag error (for a steady
                                                     sinusoid it leaves 2 sin(pi f tau) of the tremor, CALC)
  (c) noise       q = q_o + n                       perfect cancellation plus a band-limited random error n: 2-D
                                                     isotropic white Gaussian noise, zero-phase band-pass f0 +- 2 Hz
                                                     (4th order: the band of R's tip-tremor measure), a 0.3 s onset
                                                     ramp (as the tremor's), scaled so that its power amplitude
                                                     (sqrt(2) x RMS of the major axis at f0 +- 2 Hz, the class
                                                     convention) equals sigma
The noise is an INPUT of the simulation (it stands for an estimator's error), so a zero-phase filter is allowed here, as
for R's tremor extraction; no estimator ever sees it.  Every construction is deterministic given its seed.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

ONSET_S = 0.3
HALF_BAND_HZ = 2.0


def scaled(q_oracle: np.ndarray, remain: float) -> np.ndarray:
    """(a) the command that leaves `remain` (= 1 - k) of the tremor: an amplitude error only."""
    return (1.0 - float(remain)) * np.asarray(q_oracle, float)


def delayed(q_oracle: np.ndarray, tick_t: np.ndarray, tau_s: float) -> np.ndarray:
    """(b) the perfect command delayed by tau (linear interpolation between ticks; the first value held before t = tau)."""
    q = np.asarray(q_oracle, float)
    t = np.asarray(tick_t, float) - float(tau_s)
    return np.column_stack([np.interp(t, tick_t, q[:, j], left=q[0, j]) for j in range(q.shape[1])])


def band_noise(n_ticks: int, Ts: float, f0: float, sigma_m: float, seed: int, half_band: float = HALF_BAND_HZ,
               onset_s: float = ONSET_S) -> np.ndarray:
    """(c) 2-D band-limited Gaussian noise (m) at the tick rate whose power amplitude is sigma_m."""
    from scipy.signal import butter, sosfiltfilt
    from realdata import dsp as D
    rng = np.random.default_rng(int(seed) % (2 ** 32))
    fs = 1.0 / float(Ts)
    w = rng.standard_normal((int(n_ticks), 2))
    sos = butter(4, (max(1.0, f0 - half_band), f0 + half_band), btype="band", fs=fs, output="sos")
    n = sosfiltfilt(sos, w, axis=0)
    t = np.arange(int(n_ticks)) / fs
    n = n * np.clip(t / onset_s, 0.0, 1.0)[:, None]
    pa = D.power_amplitude(n, fs, f0, half_band)
    return n * (float(sigma_m) / max(pa, 1e-30))


def noisy(q_oracle: np.ndarray, Ts: float, f0: float, sigma_m: float, seed: int) -> np.ndarray:
    """(c) perfect cancellation plus the band-limited noise of power amplitude sigma."""
    q = np.asarray(q_oracle, float)
    return q + band_noise(len(q), Ts, f0, sigma_m, seed)


def delay_residual_fraction(f_hz: float, tau_s: float) -> float:
    """CALC: amplitude left by a pure delay tau on a steady sinusoid of frequency f: |1 - exp(-j 2 pi f tau)|."""
    return 2.0 * abs(math.sin(math.pi * f_hz * tau_s))


def delay_for_fraction(f_hz: float, frac: float) -> float:
    """The delay (s) that leaves `frac` of a steady sinusoid (inverse of delay_residual_fraction, first branch)."""
    x = min(max(frac / 2.0, 0.0), 1.0)
    return math.asin(x) / (math.pi * max(f_hz, 1e-9))


def variant_key(kind: str, value: float, tag: Optional[str] = None) -> str:
    """Stable result keys: E13a_0.27 (remaining share), E13b_13.4ms (delay), E13c_0.40mm (noise power amplitude)."""
    if kind == "a":
        k = f"E13a_{value:.2f}"
    elif kind == "b":
        k = f"E13b_{value:g}ms"
    elif kind == "c":
        k = f"E13c_{value:.2f}mm"
    else:
        raise KeyError(kind)
    return k if tag is None else f"{k}|{tag}"
