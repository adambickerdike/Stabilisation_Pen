"""Response surface of the finite-element drop stress, for use as a differentiable constraint.

Truth model: analysis/pencil_mechanisms.drop_sim (14-element Euler-Bernoulli plate clamped at its root, collar
share as a tip mass, unilateral tip stop at the collar-stop deflection, four snubbers at 0.2/0.4/0.6/0.8 of the
free length with gaps = operating (tip-load) shape at the stop + 30 um, transverse half-sine base pulse of a 1 m
drop with restitution 0.4 (dv 6.2 m/s), Newmark, 2 % Rayleigh damping, stop stiffness 2e5 N/m; SIMULATION with
ASSUMPTIONS as listed there).
Surrogate: Gaussian-process regression (opt/hardware/gp.py: ARD squared-exponential kernel, linear mean) of
log(peak stress) on the normalised logs of plate thickness t, free length Lf, width w, plate-tip stop deflection
u_s, tip-mass ratio mu_tip (collar share / plate free mass) and effective modulus E, trained on a scrambled-Sobol
design of experiments; a full quadratic response surface is fitted as a baseline.  Accuracy is reported on a
held-out set.  The optimiser uses the GP mean + 1 predictive sd (conservative) for the 2 ms (compliant-nose)
pulse; the recommended design is re-checked with the FE itself.
Run: python3 -m opt.hardware.drop_surrogate      (about 4-5 min)   -> results/opt/drop_surrogate.json
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import time

import numpy as np
import torch

from . import OUT, ROOT
from sim.pencil import design as D  # noqa: E402

FILE = os.path.join(OUT, "drop_surrogate.json")
INPUTS = ("t", "Lf", "w", "u_s", "mu_tip", "E")
RANGES = {"t": (0.45e-3, 1.45e-3), "Lf": (18e-3, 46e-3), "w": (1.4e-3, 4.6e-3), "u_s": (0.12e-3, 0.60e-3),
          "mu_tip": (0.05, 1.6), "E": (54e9, 70e9)}
KAPPA = 1.0          # the constraint uses mean + KAPPA x predictive sd (log space)
PULSE_T = 2e-3
DV = 4.43 * 1.4


def _pm():
    spec = importlib.util.spec_from_file_location("pencil_mechanisms", os.path.join(ROOT, "analysis", "pencil_mechanisms.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fe_drop(t, Lf, w, u_s, mu_tip, E, T=PULSE_T, pm=None, snub=True):
    """Peak plate stress (Pa) from the FE drop model for the given plate."""
    pm = pm or _pm()
    EI = E * w * t ** 3 / 12.0
    k = 3.0 * EI / Lf ** 3
    b = D.Bender("doe", w, t, Lf, Lf + 8e-3, 1.0, k, 1e-6, float("nan"))
    m_free = D.RHO_PZT * w * t * Lf
    tip = mu_tip * m_free
    sn = tuple((x, u_s * (3 * x ** 2 - x ** 3) / 2 + 30e-6) for x in (0.2, 0.4, 0.6, 0.8)) if snub else ()
    s, _tip = pm.drop_sim(b, tip, u_s, T, DV, snubbers=sn)
    return s


def _features(Z):
    """Full quadratic in the log inputs (normalised to [-1, 1]); Z: (..., 6) tensor or array."""
    lib = torch if isinstance(Z, torch.Tensor) else np
    cols = [lib.ones_like(Z[..., 0])]
    n = Z.shape[-1]
    for i in range(n):
        cols.append(Z[..., i])
    for i in range(n):
        for j in range(i, n):
            cols.append(Z[..., i] * Z[..., j])
    return lib.stack(cols, -1)


def _norm(X, lib=np):
    lo = np.array([math.log(RANGES[k][0]) for k in INPUTS])
    hi = np.array([math.log(RANGES[k][1]) for k in INPUTS])
    if lib is torch:
        lo, hi = torch.tensor(lo, dtype=torch.float64), torch.tensor(hi, dtype=torch.float64)
        return 2.0 * (torch.log(X) - lo) / (hi - lo) - 1.0
    return 2.0 * (np.log(X) - lo) / (hi - lo) - 1.0


def sobol(n, d, seed):
    from scipy.stats import qmc
    return qmc.Sobol(d, scramble=True, seed=seed).random(n)


def build(n_train=512, n_test=96, seed=7, verbose=True):
    from .gp import GP
    pm = _pm()
    t0 = time.time()

    def sample(n, s):
        U = sobol(n, len(INPUTS), s)
        X = np.empty_like(U)
        for i, k in enumerate(INPUTS):
            lo, hi = RANGES[k]
            X[:, i] = np.exp(np.log(lo) + U[:, i] * (np.log(hi) - np.log(lo)))
        y = np.array([fe_drop(*row, pm=pm) for row in X])
        return X, y

    Xtr, ytr = sample(n_train, seed)
    Xte, yte = sample(n_test, seed + 1)
    t_fe = time.time() - t0
    # baseline: full quadratic response surface
    F = _features(_norm(Xtr))
    coef = np.linalg.solve(F.T @ F + 1e-6 * np.eye(F.shape[1]), F.T @ np.log(ytr))
    rs_te = np.exp(_features(_norm(Xte)) @ coef) / yte - 1.0
    # Gaussian process on the held-out split (for the error report), then refitted on all points
    gp = GP(_norm(Xtr), np.log(ytr)).fit()
    mu, sd = gp.predict(torch.tensor(_norm(Xte)), return_std=True)
    gp_te = np.exp(mu.numpy()) / yte - 1.0
    cons_te = np.exp(mu.numpy() + KAPPA * sd.numpy()) / yte - 1.0
    gp_all = GP(_norm(np.vstack([Xtr, Xte])), np.log(np.concatenate([ytr, yte]))).fit()
    res = {"inputs": list(INPUTS), "ranges": RANGES, "pulse_s": PULSE_T, "dv_m_per_s": DV, "kappa": KAPPA,
           "coef_quadratic": coef.tolist(), "gp": gp_all.state(), "n_train": n_train, "n_test": n_test, "seed": seed,
           "test_rel_err": {
               "quadratic": {"rms": float(np.sqrt(np.mean(rs_te ** 2))), "max_abs": float(np.max(np.abs(rs_te)))},
               "gp_mean": {"rms": float(np.sqrt(np.mean(gp_te ** 2))), "max_abs": float(np.max(np.abs(gp_te))),
                           "p95_abs": float(np.percentile(np.abs(gp_te), 95))},
               "gp_mean_plus_kappa_sd": {"fraction_below_fe": float(np.mean(cons_te < 0)),
                                         "median": float(np.median(cons_te))}},
           "data": {"X": np.vstack([Xtr, Xte]).tolist(), "y_fe_Pa": np.concatenate([ytr, yte]).tolist()},
           "test_points": {"X": Xte.tolist(), "y_fe_Pa": yte.tolist(), "y_gp_Pa": np.exp(mu.numpy()).tolist()},
           "fe_elapsed_s": t_fe, "elapsed_s": time.time() - t0,
           "label": "SIMULATION-trained Gaussian-process surrogate (FE drop model analysis/pencil_mechanisms.drop_sim; "
                    "pulse, damping, stop stiffness ASSUMPTIONS as there)"}
    if verbose:
        e = res["test_rel_err"]
        print("drop surrogate (held-out %d FE runs): quadratic rms %.3f max %.3f | GP rms %.3f max %.3f p95 %.3f | "
              "GP+sd below FE %.2f; %.0f s" % (n_test, e["quadratic"]["rms"], e["quadratic"]["max_abs"],
                                               e["gp_mean"]["rms"], e["gp_mean"]["max_abs"], e["gp_mean"]["p95_abs"],
                                               e["gp_mean_plus_kappa_sd"]["fraction_below_fe"], res["elapsed_s"]))
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(FILE, "w"))
    return res


class Surrogate:
    def __init__(self, d):
        from .gp import GP
        self.d = d
        self.gp = GP.from_state(d["gp"])
        self.kappa = d.get("kappa", KAPPA)

    def predict(self, conservative=True, return_std=False, **kw):
        X = torch.stack([torch.as_tensor(kw[k], dtype=torch.float64) for k in INPUTS], -1)
        Z = _norm(X, torch)
        mu, sd = self.gp.predict(Z, return_std=True)
        val = torch.exp(mu + (self.kappa * sd if conservative else 0.0))
        return (val, sd) if return_std else val


def load(path=FILE):
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    if "gp" not in d:
        return None
    return Surrogate(d)


if __name__ == "__main__":
    build()
