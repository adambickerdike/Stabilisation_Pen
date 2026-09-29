"""A small (mu/mu_w, lambda)-CMA-ES (Hansen, 'The CMA Evolution Strategy: A Tutorial', default parameters).

Written here because the `cma` package is not installed.  Unbounded search space; callers map to their box.
Deterministic for a given seed.  Checked on the sphere and Rosenbrock functions in endcap/tests/test_cmaes.py.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List

import numpy as np


def cmaes(fun: Callable[[np.ndarray], float], x0, sigma0=0.5, max_evals=2000, popsize=None, seed=0, tol_f=None,
          verbose=False) -> Dict:
    """Minimise fun.  Stops after max_evals, when the step size collapses, or (only if tol_f is given) when the best value
    falls below tol_f.  (tol_f must stay None for objectives that can be negative, e.g. a maximised quantity.)"""
    rng = np.random.default_rng(seed)
    x0 = np.asarray(x0, float)
    n = len(x0)
    lam = popsize or 4 + int(3 * math.log(n))
    mu = lam // 2
    w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    w /= w.sum()
    mueff = 1.0 / np.sum(w ** 2)
    cc = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
    cs = (mueff + 2) / (n + mueff + 5)
    c1 = 2 / ((n + 1.3) ** 2 + mueff)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0.0, math.sqrt((mueff - 1) / (n + 1)) - 1) + cs
    chiN = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    mean = x0.copy()
    sigma = sigma0
    pc = np.zeros(n); ps = np.zeros(n)
    C = np.eye(n); B = np.eye(n); Dg = np.ones(n); invsqrtC = np.eye(n)
    evals = 0
    eigen_eval = 0
    best_x, best_f = mean.copy(), float("inf")
    hist: List[float] = []
    gen = 0
    while evals < max_evals:
        arz = rng.standard_normal((lam, n))
        ary = arz @ (B * Dg).T
        arx = mean + sigma * ary
        f = np.array([fun(x) for x in arx])
        evals += lam
        idx = np.argsort(f)
        if f[idx[0]] < best_f:
            best_f, best_x = float(f[idx[0]]), arx[idx[0]].copy()
        hist.append(best_f)
        old = mean.copy()
        mean = w @ arx[idx[:mu]]
        y = (mean - old) / sigma
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * (invsqrtC @ y)
        hsig = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * evals / lam)) / chiN < 1.4 + 2 / (n + 1)
        pc = (1 - cc) * pc + (hsig * math.sqrt(cc * (2 - cc) * mueff)) * y
        artmp = (arx[idx[:mu]] - old) / sigma
        C = ((1 - c1 - cmu) * C + c1 * (np.outer(pc, pc) + (1 - hsig) * cc * (2 - cc) * C)
             + cmu * artmp.T @ np.diag(w) @ artmp)
        sigma *= math.exp((cs / damps) * (np.linalg.norm(ps) / chiN - 1))
        if evals - eigen_eval > lam / (c1 + cmu) / n / 10:
            eigen_eval = evals
            C = np.triu(C) + np.triu(C, 1).T
            ev, B = np.linalg.eigh(C)
            Dg = np.sqrt(np.maximum(ev, 1e-30))
            invsqrtC = B @ np.diag(1 / Dg) @ B.T
        gen += 1
        if verbose and gen % 10 == 0:
            print(f"  cmaes gen {gen} evals {evals} best {best_f:.6g} sigma {sigma:.3g}")
        if (tol_f is not None and best_f < tol_f) or sigma * np.max(Dg) < 1e-12:
            break
    return {"x": best_x, "f": best_f, "evals": evals, "history": hist, "mean": mean, "sigma": sigma}
