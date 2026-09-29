"""G3/G4 frequency-response tools (EXP-T10...T13): disturbance design, FRF estimation and the
loaded-nib metrics.

Disturbance envelope (review section 12, a PROPOSED starting envelope): 1-30 Hz, 0.25-2 mm peak.
Periodic multisines on an integer-period grid give leakage-free FRFs; Schroeder phases keep the
crest factor low. The design caps the peak acceleration and the actuator force the R13 stage can
deliver (CALC in design_disturbance), so the top-right corner of the envelope (2 mm at 30 Hz is
about 71 m/s^2) is reached only with a light payload, and the design says so.

Metrics:
  * transmissibility T(f) = X_ink / X_housing (page-frame ink motion per housing motion);
    rejection r(f) = |T(f)|, 1 for a rigid pen, 0 for perfect cancellation;
  * closed-loop tracking FRF of the nib (position / reference) and its -3 dB bandwidth;
  * ink-error reduction = 1 - RMS(on) / RMS(locked) on the same disturbance realisation
    (the review's >= 30 % G3/G4 target applies to a predeclared metric, here RMS in 3-12 Hz);
  * large-excursion limit from an amplitude ladder.
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

from s2r import ident


def tone_grid(f_lo: float, f_hi: float, n_tones: int, T: float) -> np.ndarray:
    """Log-spaced frequencies snapped to the 1/T grid (unique)."""
    df = 1.0 / T
    f = np.unique(np.round(np.geomspace(f_lo, f_hi, n_tones) / df) * df)
    return f[f > 0]


def schroeder_multisine(freqs: np.ndarray, amps: np.ndarray, fs: float, T: float) -> Dict:
    """x(t) = sum_k a_k cos(2 pi f_k t + phi_k), Schroeder phases phi_k = -pi k (k+1) / K
    (for a flat power spectrum; used as a good start for any spectrum)."""
    K = len(freqs)
    k = np.arange(1, K + 1)
    phi = -np.pi * k * (k - 1) / K
    t = np.arange(int(round(T * fs))) / fs
    x = np.sum(amps[:, None] * np.cos(2 * np.pi * freqs[:, None] * t[None, :] + phi[:, None]), axis=0)
    rms = np.sqrt(np.mean(x ** 2))
    return {"t": t, "x": x, "phases": phi, "crest": float(np.max(np.abs(x)) / rms) if rms > 0 else float("nan")}


def design_disturbance(x_peak_m: float, f_lo: float = 1.0, f_hi: float = 30.0, n_tones: int = 24, T: float = 10.0,
                       fs: float = 4000.0, a_max: float = 40.0, spectrum: str = "flat_displacement") -> Dict:
    """Multisine whose peak displacement is x_peak_m, with per-tone amplitudes reduced at high
    frequency so the waveform's peak acceleration stays <= a_max (m/s^2)."""
    f = tone_grid(f_lo, f_hi, n_tones, T)
    a = np.ones_like(f) if spectrum == "flat_displacement" else 1.0 / f
    ms = schroeder_multisine(f, a, fs, T)
    t, ph = ms["t"], ms["phases"]
    C = np.cos(2 * np.pi * f[:, None] * t[None, :] + ph[:, None])      # K x n basis
    w2 = (2 * np.pi * f) ** 2
    amps = a * x_peak_m / np.max(np.abs(ms["x"]))
    clipped = False
    amax = float(np.max(np.abs((amps * w2) @ C)))
    for _ in range(80):
        if amax <= a_max:
            break
        clipped = True
        contrib = amps * w2
        amps = np.where(contrib >= np.quantile(contrib, 0.7), amps * 0.85, amps)
        amax = float(np.max(np.abs((amps * w2) @ C)))
    x = amps @ C
    return {"f": f, "amps": amps, "phases": ph, "t": t, "x": x, "x_peak_m": float(np.max(np.abs(x))),
            "a_peak": amax, "acc_limited": clipped, "crest": float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))}


def stage_force_needed(x: np.ndarray, fs: float, m_moving: float, k_flex: float) -> Dict:
    """Peak and RMS actuator force for a disturbance waveform on the R13 flexure stage."""
    a = np.gradient(np.gradient(x, 1 / fs), 1 / fs)
    F = m_moving * a + k_flex * x
    return {"F_peak_N": float(np.max(np.abs(F))), "F_rms_N": float(np.sqrt(np.mean(F ** 2)))}


def envelope_limits(freqs: np.ndarray, x_peak_m: float, m_moving: float, k_flex: float, F_cont: float,
                    F_peak: float, stroke_half_m: float) -> Dict:
    """Sine-by-sine feasibility over the review envelope (CALC): the force a sine of amplitude x_peak
    needs at each frequency against the voice coil's continuous and peak ratings."""
    w = 2 * np.pi * np.asarray(freqs)
    F = np.abs(k_flex - m_moving * w ** 2) * x_peak_m
    return {"f": np.asarray(freqs), "F_needed_N": F, "within_continuous": F <= F_cont, "within_peak": F <= F_peak,
            "within_stroke": bool(x_peak_m <= stroke_half_m)}


def frf_periodic(u: np.ndarray, y: np.ndarray, fs: float, T: float, freqs: np.ndarray) -> Dict:
    """FRF at the excited lines of a periodic excitation, averaged over whole periods, with the
    per-line standard error from the spread between periods (noise estimate without a model)."""
    n = int(round(T * fs))
    P = len(u) // n
    if P < 1:
        raise ValueError("record shorter than one period")
    bins = np.round(np.asarray(freqs) * T).astype(int)
    Hs = []
    for p in range(P):
        U = np.fft.rfft(u[p * n:(p + 1) * n])[bins]
        Y = np.fft.rfft(y[p * n:(p + 1) * n])[bins]
        Hs.append(Y / U)
    Hs = np.array(Hs)
    H = Hs.mean(axis=0)
    se = Hs.std(axis=0, ddof=1) / np.sqrt(P) if P > 1 else np.abs(H) * np.nan
    return {"f": np.asarray(freqs), "H": H, "se": se, "periods": P}


def frf_iv(r: np.ndarray, u: np.ndarray, y: np.ndarray, fs: float, T: float, freqs: np.ndarray) -> Dict:
    """Instrumental-variable FRF H = S_ry / S_ru at the excited lines, with the known digital
    command r (logged in every SAMPLE frame as `cmd`). Unbiased for noise on u and y."""
    n = int(round(T * fs))
    P = len(u) // n
    bins = np.round(np.asarray(freqs) * T).astype(int)
    Sru = 0.0
    Sry = 0.0
    for p in range(P):
        R = np.fft.rfft(r[p * n:(p + 1) * n])[bins]
        U = np.fft.rfft(u[p * n:(p + 1) * n])[bins]
        Y = np.fft.rfft(y[p * n:(p + 1) * n])[bins]
        Sru = Sru + U * np.conj(R)
        Sry = Sry + Y * np.conj(R)
    return {"f": np.asarray(freqs), "H": Sry / Sru, "periods": P}


def bandwidth_3db(f: np.ndarray, H: np.ndarray) -> float:
    """First frequency where |H| falls below 1/sqrt(2) of its low-frequency value (interpolated)."""
    mag = np.abs(H) / np.abs(H[0])
    below = np.where(mag < 1 / np.sqrt(2))[0]
    if len(below) == 0:
        return float("nan")
    k = below[0]
    if k == 0:
        return float(f[0])
    return float(np.exp(np.interp(1 / np.sqrt(2), [mag[k], mag[k - 1]], [np.log(f[k]), np.log(f[k - 1])])))


def band_rejection(f: np.ndarray, T: np.ndarray, band=(3.0, 12.0)) -> Dict:
    m = (f >= band[0]) & (f <= band[1])
    mag = np.abs(T[m])
    return {"band_hz": list(band), "mean_ratio": float(np.mean(mag)), "max_ratio": float(np.max(mag)),
            "power_weighted_ratio": float(np.sqrt(np.mean(mag ** 2)))}


def band_rms(x: np.ndarray, fs: float, band=(3.0, 12.0)) -> float:
    from scipy import signal as sps
    sos = sps.butter(4, band, btype="band", fs=fs, output="sos")
    return float(np.sqrt(np.mean(sps.sosfiltfilt(sos, x) ** 2)))


def ink_error_reduction(err_on: Sequence[np.ndarray], err_off: Sequence[np.ndarray], fs: float, band=(3.0, 12.0),
                        n_boot: int = 500, seed: int = 0) -> Dict:
    """Paired over disturbance realisations (seeds): reduction = 1 - RMS_band(on) / RMS_band(off)."""
    on = np.array([band_rms(e, fs, band) for e in err_on])
    off = np.array([band_rms(e, fs, band) for e in err_off])
    red = 1 - on / off
    rng = np.random.default_rng(seed)
    bs = [np.mean(rng.choice(red, len(red))) for _ in range(n_boot)]
    return {"reduction_mean": float(np.mean(red)), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "per_seed": red.tolist(), "rms_on": on.tolist(), "rms_off": off.tolist()}


def excursion_limit(amplitudes: np.ndarray, residual_ratio: np.ndarray, current_peak: np.ndarray, i_limit: float,
                    ratio_limit: float = 0.7) -> Dict:
    """Largest amplitude of an amplitude ladder at which the residual ratio stays below ratio_limit
    and the peak current below the software limit."""
    ok = (np.asarray(residual_ratio) <= ratio_limit) & (np.asarray(current_peak) <= i_limit)
    amps = np.asarray(amplitudes)
    good = amps[ok]
    first_bad = amps[~ok].min() if (~ok).any() else float("nan")
    return {"largest_ok_amplitude": float(good.max()) if len(good) else float("nan"),
            "first_failing_amplitude": float(first_bad)}


def fit_loop(f: np.ndarray, H: np.ndarray, sigma: np.ndarray = None) -> Dict:
    """Second-order-plus-delay fit of a closed-loop tracking FRF (DC gain ~ 1)."""
    sig = np.abs(H) * 0.02 if sigma is None else sigma
    r = ident.fit_second_order(f, H, sig, sign=1.0)
    a, fn, z, tau = r["p"]
    return {"fn_hz": float(fn), "zeta": float(z), "delay_s": float(tau), "dc_gain": float(a / (2 * np.pi * fn) ** 2)}
