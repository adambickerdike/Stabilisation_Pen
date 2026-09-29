r"""Task 5: handwriting synthesis in the writer's style (for autowrite and the clean copy).

Evidence status: CALCULATION / SIMULATION on synthetic writers (aiguide) and on public online-handwriting data
(UCI Character Trajectories and UJI Pen Characters v2, both CC BY 4.0).  Nothing was measured on a person.

Sigma-lognormal model (Plamondon 1995; O'Reilly & Plamondon 2009).  A stroke sequence is a sum of lognormal velocity
components j with
    |v_j(t)| = D_j / (sigma_j sqrt(2 pi) (t - t0_j)) exp(-(ln(t - t0_j) - mu_j)^2 / (2 sigma_j^2)),   t > t0_j
and a direction that turns from theta_s,j to theta_e,j in proportion to the lognormal's cumulative (a circular arc).
Extraction (a simplified robust procedure, not the full iDeLog): speed peaks give the initial components (t0, mu,
sigma, D from the peak time and the neighbouring speed minima; directions from the velocity at the minima), then a
bounded non-linear least-squares fit of the velocity vector refines all parameters.  Quality: SNR of the velocity
reconstruction, 10 log10(int |v|^2 / int |v - v_hat|^2) (dB).
Synthesis in the writer's style from k samples: the sample with the best fit is the prototype; new instances perturb
its parameters within the spread seen across the k samples (or a default intra-writer spread when k = 1: t0 +-5 ms,
mu +-0.05, sigma +-0.03, D +-5 %, angles +-0.05 rad; ASSUMPTION, of the order used in the kinematic-theory
signature-synthesis literature).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import argrelextrema, butter, sosfiltfilt
from scipy.special import erf

FS = 200.0
DEFAULT_SPREAD = {"t0": 0.005, "mu": 0.05, "sigma": 0.03, "D": 0.05, "th": 0.05}


def lognormal_speed(t: np.ndarray, D, t0, mu, sigma) -> np.ndarray:
    tau = np.maximum(t - t0, 1e-9)
    v = D / (sigma * math.sqrt(2 * math.pi) * tau) * np.exp(-(np.log(tau) - mu) ** 2 / (2 * sigma ** 2))
    return np.where(t > t0, v, 0.0)


def lognormal_cdf(t: np.ndarray, t0, mu, sigma) -> np.ndarray:
    tau = np.maximum(t - t0, 1e-9)
    return np.where(t > t0, 0.5 * (1 + erf((np.log(tau) - mu) / (sigma * math.sqrt(2)))), 0.0)


def velocity(t: np.ndarray, P: np.ndarray) -> np.ndarray:
    """(n, 2) velocity of a sum of lognormal components P (m, 6): D, t0, mu, sigma, theta_s, theta_e."""
    v = np.zeros((len(t), 2))
    for D, t0, mu, sg, ts, te in P:
        sp = lognormal_speed(t, D, t0, mu, sg)
        ph = ts + (te - ts) * lognormal_cdf(t, t0, mu, sg)
        v[:, 0] += sp * np.cos(ph); v[:, 1] += sp * np.sin(ph)
    return v


def trajectory(t: np.ndarray, P: np.ndarray, start: np.ndarray) -> np.ndarray:
    v = velocity(t, P)
    dt = float(t[1] - t[0])
    return start[None, :] + np.cumsum(v, axis=0) * dt


def snr_db(v: np.ndarray, v_hat: np.ndarray) -> float:
    return float(10 * np.log10(np.sum(v ** 2) / max(np.sum((v - v_hat) ** 2), 1e-30)))


def _init(t: np.ndarray, v: np.ndarray, min_rel: float = 0.08) -> np.ndarray:
    sp = np.hypot(v[:, 0], v[:, 1])
    if sp.max() <= 0:
        return np.zeros((0, 6))
    pk = argrelextrema(sp, np.greater_equal, order=3)[0]
    pk = [p for p in pk if sp[p] > min_rel * sp.max()]
    mins = argrelextrema(sp, np.less_equal, order=2)[0]
    out = []
    for p in pk:
        a = max([m for m in mins if m < p], default=0)
        b = min([m for m in mins if m > p], default=len(t) - 1)
        D = float(np.sum(sp[a:b + 1]) / FS)
        sigma = 0.3
        t_peak = t[p]
        dur = max(t[b] - t[a], 0.03)
        # the lognormal's mode is exp(mu - sigma^2) after t0; place t0 a little before the start
        t0 = t[a] - 0.25 * dur
        mu = math.log(max(t_peak - t0, 1e-3)) + sigma ** 2
        ts = math.atan2(v[min(a + 1, len(t) - 1), 1], v[min(a + 1, len(t) - 1), 0]) if sp[a + 1 if a + 1 < len(t) else a] > 0 else math.atan2(v[p, 1], v[p, 0])
        te = math.atan2(v[max(b - 1, 0), 1], v[max(b - 1, 0), 0])
        tp = math.atan2(v[p, 1], v[p, 0])
        # keep the turn consistent with the peak direction
        ts = tp + ((ts - tp + math.pi) % (2 * math.pi) - math.pi)
        te = tp + ((te - tp + math.pi) % (2 * math.pi) - math.pi)
        out.append([D, t0, mu, sigma, ts, te])
    return np.array(out, float)


def extract(t: np.ndarray, xy: np.ndarray, max_nfev: int = 400) -> Dict:
    """Sigma-lognormal parameters of one pen-down trajectory sampled at FS.  Returns P (m, 6), SNR (dB)."""
    if len(t) < 8:
        return {"P": np.zeros((0, 6)), "snr_db": float("nan")}
    sos = butter(4, 20.0, fs=FS, output="sos")
    xs = sosfiltfilt(sos, xy, axis=0) if len(xy) > 27 else xy
    v = np.gradient(xs, 1.0 / FS, axis=0)
    P0 = _init(t, v)
    if len(P0) == 0:
        return {"P": P0, "snr_db": float("nan")}
    m = len(P0)
    lo = np.tile([0.0, t[0] - 1.0, -6.0, 0.05, -4 * math.pi, -4 * math.pi], m)
    hi = np.tile([10.0, t[-1], 1.5, 1.2, 4 * math.pi, 4 * math.pi], m)
    x0 = np.clip(P0.ravel(), lo + 1e-9, hi - 1e-9)

    def res(x):
        return (velocity(t, x.reshape(m, 6)) - v).ravel()
    try:
        sol = least_squares(res, x0, bounds=(lo, hi), max_nfev=max_nfev, x_scale="jac")
        P = sol.x.reshape(m, 6)
    except Exception:
        P = P0
    return {"P": P, "snr_db": snr_db(v, velocity(t, P)), "v": v, "start": xs[0]}


def perturb(P: np.ndarray, rng: np.random.Generator, spread: Optional[Dict] = None) -> np.ndarray:
    s = dict(DEFAULT_SPREAD); s.update(spread or {})
    Q = P.copy()
    n = len(Q)
    Q[:, 0] *= 1 + rng.normal(0, s["D"], n)
    Q[:, 1] += rng.normal(0, s["t0"], n)
    Q[:, 2] += rng.normal(0, s["mu"], n)
    Q[:, 3] = np.clip(Q[:, 3] + rng.normal(0, s["sigma"], n), 0.05, 1.2)
    Q[:, 4] += rng.normal(0, s["th"], n)
    Q[:, 5] += rng.normal(0, s["th"], n)
    return Q


def spread_from(samples: List[np.ndarray]) -> Optional[Dict]:
    """Per-parameter spread across samples with the same number of components (else None: use the default)."""
    ms = [len(P) for P in samples]
    if len(samples) < 2 or len(set(ms)) != 1 or ms[0] == 0:
        return None
    A = np.stack(samples)
    rel_D = np.std(A[:, :, 0] / np.maximum(np.mean(A[:, :, 0], axis=0), 1e-12), axis=0).mean()
    return {"D": float(max(rel_D, 0.01)), "t0": float(np.std(A[:, :, 1], axis=0).mean()),
            "mu": float(np.std(A[:, :, 2], axis=0).mean()), "sigma": float(np.std(A[:, :, 3], axis=0).mean()),
            "th": float(np.std(A[:, :, 4:6], axis=0).mean())}
