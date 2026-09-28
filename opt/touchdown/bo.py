"""Gaussian-process Bayesian optimisation (numpy / scipy) and CMA-ES, written for noisy simulator objectives.

GP: Matern-5/2 kernel with one length scale per input (ARD), constant mean, Gaussian noise; hyperparameters by
maximum marginal likelihood (L-BFGS-B, several restarts).  Inputs live in [0, 1]^d; outputs are standardised.
Acquisition: expected improvement over the best posterior mean at the evaluated points (robust to noise),
maximised by random search plus L-BFGS-B polishing.
Multi-objective search: ParEGO (Knowles 2006) - each iteration scalarises the normalised objectives with a random
weight vector, lam, by the augmented Chebyshev function max_i(lam_i f_i) + 0.05 sum_i lam_i f_i, and runs one EI step.
The log (JSON lines) makes a search resumable: evaluated points are read back and not repeated.
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


# ------------------------------------------------------------------ Gaussian process
def _matern52(X1, X2, ls):
    d = np.sqrt(np.maximum(((X1[:, None, :] - X2[None, :, :]) / ls) ** 2, 0.0).sum(-1))
    s5 = math.sqrt(5.0) * d
    return (1.0 + s5 + 5.0 / 3.0 * d * d) * np.exp(-s5)


class GP:
    def __init__(self, X, y, noise_min=1e-4, restarts=3, rng=None, theta0=None):
        self.X = np.asarray(X, float)
        y = np.asarray(y, float)
        self.ym, self.ys = float(np.mean(y)), float(np.std(y) + 1e-12)
        self.y = (y - self.ym) / self.ys
        self.noise_min = noise_min
        self._fit(restarts, rng or np.random.default_rng(0), theta0)

    def _nll(self, th):
        """Negative log marginal likelihood (weak log-normal priors on the length scales and the noise) and its analytic
        gradient with respect to th = (log length scales, log signal variance, log noise)."""
        d = self.X.shape[1]
        ls = np.exp(th[:d]); sf2 = np.exp(th[d]); sn_raw = np.exp(th[d + 1]); sn2 = sn_raw + self.noise_min
        D2 = ((self.X[:, None, :] - self.X[None, :, :]) / ls) ** 2
        r = np.sqrt(np.maximum(D2.sum(-1), 0.0))
        s5 = math.sqrt(5.0) * r
        e = np.exp(-s5)
        Kf = sf2 * (1.0 + s5 + 5.0 / 3.0 * r * r) * e
        K = Kf + sn2 * np.eye(len(self.X))
        try:
            L = np.linalg.cholesky(K)
        except np.linalg.LinAlgError:
            return 1e10, np.zeros_like(th)
        a = np.linalg.solve(L.T, np.linalg.solve(L, self.y))
        mu_l, sd_l, mu_n, sd_n = math.log(0.4), 1.5, math.log(0.05), 2.0
        prior = 0.5 * np.sum((th[:d] - mu_l) ** 2) / sd_l ** 2 + 0.5 * (th[d + 1] - mu_n) ** 2 / sd_n ** 2
        nll = 0.5 * self.y @ a + np.log(np.diag(L)).sum() + prior
        Linv = np.linalg.solve(L, np.eye(len(self.X)))
        W = Linv.T @ Linv - np.outer(a, a)
        dK_common = (5.0 / 3.0) * sf2 * (1.0 + s5) * e          # dK/dlog(l_d) = dK_common * D2_d
        g = np.empty_like(th)
        g[:d] = 0.5 * np.einsum("ij,ijd->d", W * dK_common, D2) + (th[:d] - mu_l) / sd_l ** 2
        g[d] = 0.5 * np.sum(W * Kf)
        g[d + 1] = 0.5 * np.trace(W) * sn_raw + (th[d + 1] - mu_n) / sd_n ** 2
        return nll, g

    def _fit(self, restarts, rng, theta0=None):
        d = self.X.shape[1]
        bnds = [(math.log(0.02), math.log(5.0))] * d + [(math.log(0.05), math.log(20.0)), (math.log(1e-5), math.log(2.0))]
        starts = [np.asarray(theta0, float)] if theta0 is not None and len(theta0) == d + 2 else []
        while len(starts) < restarts:
            starts.append(np.r_[np.log(rng.uniform(0.15, 0.8, d)), 0.0, np.log(rng.uniform(0.01, 0.3))])
        best = None
        for th0 in starts:
            th0 = np.clip(th0, [b[0] for b in bnds], [b[1] for b in bnds])
            r = minimize(self._nll, th0, jac=True, method="L-BFGS-B", bounds=bnds, options={"maxiter": 200})
            if best is None or r.fun < best.fun:
                best = r
        th = best.x
        self.theta = th
        self.ls = np.exp(th[:d]); self.sf2 = float(np.exp(th[d])); self.sn2 = float(np.exp(th[d + 1]) + self.noise_min)
        K = self.sf2 * _matern52(self.X, self.X, self.ls) + self.sn2 * np.eye(len(self.X))
        self.L = np.linalg.cholesky(K)
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, self.y))

    def predict(self, Xs, std=True):
        Xs = np.atleast_2d(Xs)
        Ks = self.sf2 * _matern52(Xs, self.X, self.ls)
        mu = Ks @ self.alpha
        if not std:
            return mu * self.ys + self.ym
        v = np.linalg.solve(self.L, Ks.T)
        var = np.maximum(self.sf2 - (v * v).sum(0), 1e-12)
        return mu * self.ys + self.ym, np.sqrt(var) * self.ys


def expected_improvement(gp: GP, Xs, best):
    mu, sd = gp.predict(Xs)
    z = (best - mu) / sd
    return (best - mu) * norm.cdf(z) + sd * norm.pdf(z)


def propose(gp: GP, d, rng, n_rand=4000, n_polish=4, feasible=None):
    """Maximise EI over [0, 1]^d; the incumbent is the lowest posterior mean at the data (noise-robust).
    feasible(u) -> bool restricts the search to a known-feasible region (cheap analytic constraints): candidates are
    filtered before EI, and a polished point that leaves the region falls back to the best feasible candidate."""
    best = float(np.min(gp.predict(gp.X, std=False)))
    if feasible is not None:
        n_rand = min(n_rand, 1500)
    C = rng.uniform(0, 1, (n_rand, d))
    # also sample around the incumbents
    mu_d = gp.predict(gp.X, std=False)
    top = gp.X[np.argsort(mu_d)[:5]]
    C = np.vstack([C, np.clip(top[rng.integers(0, len(top), 500 if feasible else 1000)] + rng.normal(0, 0.06, (500 if feasible else 1000, d)), 0, 1)])
    if feasible is not None:
        C = C[np.array([bool(feasible(u)) for u in C])]
        if len(C) == 0:
            return gp.X[np.argmin(mu_d)], 0.0
    ei = expected_improvement(gp, C, best)
    starts = C[np.argsort(-ei)[:n_polish]]
    bx, bv = starts[0], -ei.max()
    for x0 in starts:
        r = minimize(lambda x: -expected_improvement(gp, x[None, :], best)[0], x0, method="L-BFGS-B", bounds=[(0, 1)] * d,
                     options={"maxiter": 100})
        if r.fun < bv and (feasible is None or feasible(np.clip(r.x, 0, 1))):
            bx, bv = r.x, r.fun
    return np.clip(bx, 0, 1), float(-bv)


# ------------------------------------------------------------------ search space
class Space:
    """Box bounds in natural units; names in LOG are searched on a log scale."""

    def __init__(self, bounds: Dict[str, Sequence[float]], log=()):
        self.names = list(bounds)
        self.lo = np.array([bounds[n][0] for n in self.names], float)
        self.hi = np.array([bounds[n][1] for n in self.names], float)
        self.log = np.array([n in log for n in self.names])

    @property
    def d(self):
        return len(self.names)

    def to_unit(self, x):
        x = np.asarray(x, float)
        lo, hi = self.lo.copy(), self.hi.copy()
        xx = x.copy()
        xx[self.log] = np.log(x[self.log]); lo[self.log] = np.log(lo[self.log]); hi[self.log] = np.log(hi[self.log])
        return (xx - lo) / (hi - lo)

    def from_unit(self, u):
        u = np.clip(np.asarray(u, float), 0, 1)
        lo, hi = self.lo.copy(), self.hi.copy()
        lo[self.log] = np.log(lo[self.log]); hi[self.log] = np.log(hi[self.log])
        x = lo + u * (hi - lo)
        x[self.log] = np.exp(x[self.log])
        return x

    def as_dict(self, x):
        return {n: float(v) for n, v in zip(self.names, x)}


def sobol(n, d, seed=0):
    from scipy.stats import qmc
    return qmc.Sobol(d, scramble=True, seed=seed).random(n)


# ------------------------------------------------------------------ ParEGO loop
def chebyshev(F, lam, rho=0.05):
    return np.max(F * lam, axis=1) + rho * np.sum(F * lam, axis=1)


def pareto_mask(F):
    """Non-dominated rows of F (minimisation)."""
    F = np.asarray(F, float)
    keep = np.ones(len(F), bool)
    for i in range(len(F)):
        if not keep[i]:
            continue
        dom = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        if dom.any():
            keep[i] = False
    return keep


def read_log(path):
    rows = []
    if path and os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def parego(space: Space, evaluate: Callable[[Dict[str, float]], Dict], objectives: List[str], n_init=24, n_iter=80,
           log_path=None, seed=0, weights: Optional[np.ndarray] = None, scales: Optional[Dict[str, float]] = None,
           x0: Optional[List[Dict[str, float]]] = None, verbose=True, feasible: Optional[Callable[[Dict[str, float]], bool]] = None):
    """Minimise the listed objective keys of evaluate(x) (a dict) with ParEGO.  Returns the evaluated rows.
    weights: fixed weight vectors to cycle through (default: random on the simplex each iteration).
    feasible: known, cheap constraint on x (natural units); the initial design and every proposal stay inside it."""
    rng = np.random.default_rng(seed)
    rows = read_log(log_path)

    def run(xd, tag):
        t0 = time.time()
        res = evaluate(xd)
        row = {"x": xd, "tag": tag, "f": {k: float(res[k]) for k in objectives}, "res": res, "t_s": round(time.time() - t0, 2)}
        rows.append(row)
        if log_path:
            with open(log_path, "a") as f:
                f.write(json.dumps(row, default=float) + "\n")
        if verbose:
            print(f"[{len(rows):3d}] {tag:5s} " + " ".join(f"{k}={row['f'][k]:.4g}" for k in objectives) +
                  "  x=" + ", ".join(f"{k}={v:.3g}" for k, v in xd.items()) + f"  ({row['t_s']} s)", flush=True)
        return row

    # initial design: the given starting points, then a scrambled Sobol set (deterministic, so a resumed search
    # continues exactly where the log ends)
    if feasible is None:
        init_pts = [space.as_dict(space.from_unit(u)) for u in sobol(n_init, space.d, seed)]
    else:
        init_pts = []
        for u in sobol(max(8 * n_init, 64), space.d, seed):
            xd = space.as_dict(space.from_unit(u))
            if feasible(xd):
                init_pts.append(xd)
            if len(init_pts) >= n_init:
                break
    init_list = [(dict(xd), "x0") for xd in (x0 or [])] + [(xd, "init") for xd in init_pts]
    n_done = sum(1 for r in rows if r["tag"] in ("init", "x0"))
    for xd, tag in init_list[n_done:]:
        run(xd, tag)
    n_bo = sum(1 for r in rows if r["tag"] == "bo")
    theta_prev = None
    for it in range(n_bo, n_iter):
        U = np.array([space.to_unit([r["x"][n] for n in space.names]) for r in rows])
        F = np.array([[r["f"][k] for k in objectives] for r in rows])
        if scales:
            Fn = F / np.array([scales[k] for k in objectives])
        else:
            lo, hi = F.min(0), F.max(0)
            Fn = (F - lo) / np.maximum(hi - lo, 1e-12)
        if weights is not None:
            lam = np.asarray(weights[it % len(weights)], float)
        else:
            lam = rng.dirichlet(np.ones(len(objectives)))
        y = chebyshev(Fn, lam)
        gp = GP(U, y, rng=rng, theta0=theta_prev)
        theta_prev = gp.theta
        fu = (lambda uu: feasible(space.as_dict(space.from_unit(uu)))) if feasible is not None else None
        u, ei = propose(gp, space.d, rng, feasible=fu)
        run(space.as_dict(space.from_unit(u)), "bo")
    return rows


# ------------------------------------------------------------------ CMA-ES (for comparison / local refinement)
def cmaes(f: Callable[[np.ndarray], float], x0, sigma0=0.2, popsize=None, iters=30, seed=0, lo=0.0, hi=1.0, verbose=False):
    """Minimal (mu/mu_w, lambda)-CMA-ES in [lo, hi]^d (Hansen 2016 defaults); returns (best_x, best_f, history)."""
    rng = np.random.default_rng(seed)
    x0 = np.asarray(x0, float); d = len(x0)
    lam = popsize or 4 + int(3 * math.log(d))
    mu = lam // 2
    w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1)); w /= w.sum()
    mueff = 1.0 / np.sum(w ** 2)
    cc = (4 + mueff / d) / (d + 4 + 2 * mueff / d); cs = (mueff + 2) / (d + mueff + 5)
    c1 = 2 / ((d + 1.3) ** 2 + mueff); cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((d + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0, math.sqrt((mueff - 1) / (d + 1)) - 1) + cs
    chiN = math.sqrt(d) * (1 - 1 / (4 * d) + 1 / (21 * d * d))
    m, sigma = x0.copy(), sigma0
    C = np.eye(d); pc = np.zeros(d); ps = np.zeros(d)
    best = (None, np.inf); hist = []
    for g in range(iters):
        Dg, B = np.linalg.eigh(C); Dg = np.sqrt(np.maximum(Dg, 1e-20))
        Z = rng.standard_normal((lam, d)); Y = Z @ (B * Dg).T
        X = np.clip(m + sigma * Y, lo, hi)
        fx = np.array([f(x) for x in X])
        idx = np.argsort(fx)
        if fx[idx[0]] < best[1]:
            best = (X[idx[0]].copy(), float(fx[idx[0]]))
        hist.append({"gen": g, "best": best[1], "median": float(np.median(fx)), "sigma": sigma})
        if verbose:
            print("cma gen", g, round(best[1], 5), round(float(np.median(fx)), 5), round(sigma, 4), flush=True)
        yw = (Y[idx[:mu]] * w[:, None]).sum(0)
        m = np.clip(m + sigma * yw, lo, hi)
        Cm12 = B @ np.diag(1 / Dg) @ B.T
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * Cm12 @ yw
        hs = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (g + 1))) < (1.4 + 2 / (d + 1)) * chiN
        pc = (1 - cc) * pc + hs * math.sqrt(cc * (2 - cc) * mueff) * yw
        C = (1 - c1 - cmu) * C + c1 * (np.outer(pc, pc) + (1 - hs) * cc * (2 - cc) * C) + cmu * (Y[idx[:mu]].T * w) @ Y[idx[:mu]]
        sigma *= math.exp((cs / damps) * (np.linalg.norm(ps) / chiN - 1))
    return best[0], best[1], hist
