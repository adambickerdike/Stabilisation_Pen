"""Thermal analysis (EXP-T15; also the coupon steps of EXP-T08): coil temperature by resistance,
one- and two-node fits, time to a limit, and a check of the firmware governor.

Coil temperature from resistance: T = 20 + (R/R20 - 1) / alpha, alpha_cu = 0.00393 /K
(LIT AMF-29, as bench_protocols.md EXP-B03). Resistance is measured by the rig's 4-wire channels
during short zero-force current pulses or from V/I with the drive's own current.

One node:   C dT/dt = P - (T - Ta)/R
Two nodes:  C1 dT1/dt = P - (T1 - T2)/R12 ;  C2 dT2/dt = (T1 - T2)/R12 - (T2 - Ta)/R2a
(node 1 the coil, node 2 the housing/grip surface where the web thermocouple sits).
The review (section 8) screens with R_th 100 K/W and C_th 0.5 J/K (ASSUMPTION of the repository);
these fits replace them with measured values.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from scipy import optimize

ALPHA_CU = 0.00393


def coil_temperature(R_ohm, R20_ohm, alpha=ALPHA_CU):
    return 20.0 + (np.asarray(R_ohm, float) / R20_ohm - 1.0) / alpha


def simulate_1node(t, P, Ta, Rth, Cth, T0):
    t = np.asarray(t, float)
    P = np.broadcast_to(np.asarray(P, float), t.shape)
    Ta = np.broadcast_to(np.asarray(Ta, float), t.shape)
    T = np.empty_like(t)
    T[0] = T0
    tau = Rth * Cth
    for k in range(1, len(t)):
        dt = t[k] - t[k - 1]
        Tinf = Ta[k - 1] + P[k - 1] * Rth
        T[k] = Tinf + (T[k - 1] - Tinf) * np.exp(-dt / tau)
    return T


def simulate_2node(t, P, Ta, C1, C2, R12, R2a, T10, T20, substeps=None):
    """Exact discretisation for piecewise-constant power and ambient (zero-order hold), so the
    fit stays stable for any positive parameters."""
    from scipy.linalg import expm
    t = np.asarray(t, float)
    P = np.broadcast_to(np.asarray(P, float), t.shape)
    Ta = np.broadcast_to(np.asarray(Ta, float), t.shape)
    A = np.array([[-1 / (R12 * C1), 1 / (R12 * C1)],
                  [1 / (R12 * C2), -1 / (R12 * C2) - 1 / (R2a * C2)]])
    B = np.array([[1 / C1, 0.0], [0.0, 1 / (R2a * C2)]])      # inputs: P, Ta
    Ainv = np.linalg.inv(A)
    cache = {}
    X = np.empty((len(t), 2))
    X[0] = (T10, T20)
    for k in range(1, len(t)):
        dt = round(t[k] - t[k - 1], 9)
        if dt not in cache:
            Ad = expm(A * dt)
            cache[dt] = (Ad, Ainv @ (Ad - np.eye(2)) @ B)
        Ad, Bd = cache[dt]
        X[k] = Ad @ X[k - 1] + Bd @ np.array([P[k - 1], Ta[k - 1]])
    return X[:, 0], X[:, 1]


def fit_1node(t, P, T, Ta) -> Dict:
    t = np.asarray(t, float)
    T = np.asarray(T, float)

    def res(p):
        return simulate_1node(t, P, Ta, np.exp(p[0]), np.exp(p[1]), T[0]) - T

    r = optimize.least_squares(res, [np.log(50.0), np.log(1.0)])
    J = r.jac
    s2 = 2 * r.cost / max(len(t) - 2, 1)
    cov = np.linalg.pinv(J.T @ J) * s2
    Rth, Cth = np.exp(r.x)
    return {"Rth_K_per_W": float(Rth), "Cth_J_per_K": float(Cth), "tau_s": float(Rth * Cth),
            "rel_se": np.sqrt(np.diag(cov)).tolist(), "resid_rms_K": float(np.sqrt(np.mean(r.fun ** 2)))}


def fit_2node(t, P, T1, T2, Ta) -> Dict:
    t = np.asarray(t, float)
    T1 = np.asarray(T1, float)
    T2 = np.asarray(T2, float)

    def res(p):
        C1, C2, R12, R2a = np.exp(p)
        a, b = simulate_2node(t, P, Ta, C1, C2, R12, R2a, T1[0], T2[0])
        return np.concatenate([a - T1, b - T2])

    p0 = np.log([0.5, 5.0, 30.0, 60.0])
    r = optimize.least_squares(res, p0, x_scale=1.0, max_nfev=200)
    J = r.jac
    s2 = 2 * r.cost / max(2 * len(t) - 4, 1)
    cov = np.linalg.pinv(J.T @ J) * s2
    C1, C2, R12, R2a = np.exp(r.x)
    return {"C1_J_per_K": float(C1), "C2_J_per_K": float(C2), "R12_K_per_W": float(R12), "R2a_K_per_W": float(R2a),
            "rel_se": np.sqrt(np.diag(cov)).tolist(), "resid_rms_K": float(np.sqrt(np.mean(r.fun ** 2)))}


def time_to_limit(P_W, Rth, Cth, T_limit, T0=25.0, Ta=25.0) -> float:
    """Seconds for a one-node coil at constant power to reach T_limit (inf if it never does)."""
    Tinf = Ta + P_W * Rth
    if Tinf <= T_limit:
        return float("inf")
    return float(-Rth * Cth * np.log((Tinf - T_limit) / (Tinf - T0)))


def governor_check(t, T_coil, T_limit=120.0, T_web=None, web_limit=43.0) -> Dict:
    T_coil = np.asarray(T_coil, float)
    out = {"coil_max_C": float(T_coil.max()), "coil_margin_K": float(T_limit - T_coil.max()),
           "time_above_s": float(np.sum(np.diff(t)[T_coil[1:] > T_limit]))}
    if T_web is not None:
        Tw = np.asarray(T_web, float)
        out.update({"web_max_C": float(Tw.max()), "web_margin_K": float(web_limit - Tw.max())})
    return out
