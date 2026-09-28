"""Optimisers for the nib-stage hardware (opt/hardware/model.py).

Problem: maximise the worst-case usable stroke under load
    U_wc = min( stroke(-20 % part tolerance, theta 35 deg, worst stroke direction, mu_wc),  q_stop - servo margin )
subject to every constraint of model.evaluate (fit with the tips at the stops, snubber webs, axial stack, leaf
design rules, resonance, fracture probability at the stops and in the drop, mass, battery life, servo stability,
driver rating) and optional epsilon constraints on power and mass (Pareto fronts).
The min() is handled in epigraph form: an extra variable s with s <= stroke and s <= q_stop - margin.

Methods (all use the exact reverse-mode gradients of the torch model):
  * batched projected Adam on the augmented Lagrangian (PHR form), one multiplier set per start, many starts;
  * scipy L-BFGS-B polish of the best starts, augmented-Lagrangian outer loop;
  * CMA-ES on an exact-penalty function as a derivative-free global check;
  * exhaustive enumeration of the discrete choices is done by the caller (run_study).
Evidence status: CALCULATION (optimisation of a calculated model).
"""
from __future__ import annotations

import math
import time

import numpy as np
import torch

from . import model as MD

DT = torch.float64
S_MAX = 0.9e-3          # upper bound of the epigraph variable (m)
LS = 1e-4               # normalisation of stroke-type constraints (0.1 mm)


class Problem:
    def __init__(self, opts: MD.Options, fixed: dict | None = None, eps: dict | None = None, cal=None,
                 objective: str = "usable_wc"):
        self.opts = opts
        self.fixed = dict(fixed or {})
        self.lo, self.hi = MD.bounds(opts, self.fixed)
        self.free = self.hi > self.lo
        self.idx = torch.nonzero(self.free).flatten()
        self.nfree = int(self.free.sum())
        self.n = self.nfree + 1
        self.cal = cal if cal is not None else MD.load_calibration()
        self.eps = dict(eps or {})
        self.objective = objective
        self.names = None

    # ----- variable maps
    def x_of(self, U):
        B = U.shape[0]
        full = self.lo.expand(B, -1).clone()
        full[:, self.idx] = self.lo[self.idx] + U[:, :self.nfree] * (self.hi - self.lo)[self.idx]
        return {n: full[:, i] for i, n in enumerate(MD.NAMES)}, U[:, -1] * S_MAX

    def u_of(self, x: dict, s=None):
        u = torch.zeros(len(MD.NAMES), dtype=DT)
        for i, nme in enumerate(MD.NAMES):
            if self.hi[i] > self.lo[i]:
                u[i] = (float(x[nme]) - self.lo[i]) / (self.hi[i] - self.lo[i])
        us = u[self.idx].clamp(0.0, 1.0)
        return torch.cat([us, torch.tensor([0.0 if s is None else s / S_MAX], dtype=DT)])

    # ----- evaluation
    def eval(self, U, full=False):
        x, s = self.x_of(U)
        out = MD.evaluate(x, self.opts, self.cal)
        cols, names = [], []
        for k, v in out["gs"].items():
            v2 = v if v.dim() == 2 else v[:, None]
            cols.append(v2)
            names += [k] if v2.shape[1] == 1 else [f"{k}[{j}]" for j in range(v2.shape[1])]
        if self.objective == "usable_wc":
            cols.append(((out["q_wc"] - s) / LS)[:, None]); names.append("epi_stroke")
            cols.append(((out["q_lim"] - s) / LS)[:, None]); names.append("epi_stop")
            f = s / LS
        elif self.objective == "usable_nom":
            cols.append(((out["q_nom"] - s) / LS)[:, None]); names.append("epi_stroke")
            cols.append(((out["q_lim"] - s) / LS)[:, None]); names.append("epi_stop")
            f = s / LS
        else:
            raise ValueError(self.objective)
        if "P_max" in self.eps:
            Pm = torch.as_tensor(self.eps["P_max"], dtype=DT)
            cols.append(((Pm - out["P_total_mean"]) / Pm)[:, None]); names.append("eps_power")
        if "M_max" in self.eps:
            Mm = torch.as_tensor(self.eps["M_max"], dtype=DT)
            cols.append(((Mm - out["mass"]["with_margin_g"]) / Mm)[:, None]); names.append("eps_mass")
        G = torch.cat(cols, -1)
        self.names = names
        if full:
            return f, G, out, x
        return f, G


def phr(G, lam, rho):
    """Powell-Hestenes-Rockafellar augmented-Lagrangian term for constraints G >= 0 (rho per row)."""
    r = rho[:, None] if rho.dim() == 1 else rho
    return (0.5 / r * (torch.clamp(lam - r * G, min=0.0) ** 2 - lam ** 2)).sum(-1)


def violation(G):
    return torch.clamp(-G, min=0.0).max(-1).values


def adam_al(prob: Problem, U0, iters=1500, lr=0.03, lr_end=0.002, al_every=100, rho0=10.0, rho_max=1e4,
            verbose=False):
    U = U0.clone().to(DT).requires_grad_(True)
    B = U.shape[0]
    with torch.no_grad():
        _f, G = prob.eval(U)
    lam = torch.zeros_like(G)
    rho = torch.full((B,), rho0, dtype=DT)
    best_v = torch.full((B,), float("inf"), dtype=DT)
    opt = torch.optim.Adam([U], lr=lr)
    for it in range(iters):
        for gparam in opt.param_groups:      # cosine decay of the step size
            gparam["lr"] = lr_end + 0.5 * (lr - lr_end) * (1 + math.cos(math.pi * it / max(iters - 1, 1)))
        f, G = prob.eval(U)
        L = -f + phr(G, lam, rho)
        bad = ~torch.isfinite(L)
        L = torch.where(bad, torch.zeros_like(L), L)
        opt.zero_grad()
        L.sum().backward()
        with torch.no_grad():
            U.grad.nan_to_num_(0.0, 0.0, 0.0)
        opt.step()
        with torch.no_grad():
            U.clamp_(0.0, 1.0)
        if (it + 1) % al_every == 0:
            with torch.no_grad():
                f, G = prob.eval(U)
                G = torch.nan_to_num(G, nan=-10.0)
                lam = torch.clamp(lam - rho[:, None] * G, min=0.0)
                v = violation(G)
                grow = v > 0.25 * best_v
                rho = torch.where(grow, torch.clamp(rho * 3.0, max=rho_max), rho)
                best_v = torch.minimum(best_v, v)
            if verbose:
                print(f"  it {it + 1}: best f {float(f[v < 1e-3].max()) if (v < 1e-3).any() else float('nan'):.3f} "
                      f"feasible {(v < 1e-3).float().mean():.2f}")
    with torch.no_grad():
        f, G = prob.eval(U)
    return U.detach(), f, G, lam


def lbfgs_al(prob: Problem, u0, outer=16, rho0=10.0, lam0=None, maxiter=400, tol=1e-4):
    from scipy.optimize import minimize
    u = np.asarray(u0, float).copy()
    with torch.no_grad():
        _f, G = prob.eval(torch.tensor(u[None], dtype=DT))
    lam = torch.zeros(G.shape[1], dtype=DT) if lam0 is None else lam0.clone()
    rho = rho0
    hist = []
    for k in range(outer):
        def fun(uu):
            U = torch.tensor(uu[None], dtype=DT, requires_grad=True)
            f, G = prob.eval(U)
            L = -f[0] + phr(G, lam[None], torch.tensor([rho], dtype=DT))[0]
            if not torch.isfinite(L):
                return 1e6, np.zeros_like(uu)
            L.backward()
            return float(L.detach()), np.nan_to_num(U.grad[0].numpy())
        res = minimize(fun, u, jac=True, method="L-BFGS-B", bounds=[(0.0, 1.0)] * len(u),
                       options=dict(maxiter=maxiter, ftol=1e-12, gtol=1e-9))
        u = res.x
        with torch.no_grad():
            f, G = prob.eval(torch.tensor(u[None], dtype=DT))
        G = torch.nan_to_num(G[0], nan=-10.0)
        v = float(torch.clamp(-G, min=0.0).max())
        lam = torch.clamp(lam - rho * G, min=0.0)
        hist.append({"outer": k, "f": float(f[0]), "viol": v, "rho": rho, "nit": int(res.nit)})
        if v < tol and k >= 2:
            break
        if v > tol:
            rho = min(rho * 4.0, 1e5)
    return u, lam, hist


def cmaes(prob: Problem, u0=None, sigma0=0.25, gens=300, popsize=None, seed=0, penalty=50.0):
    """Minimal (mu/mu_w, lambda)-CMA-ES (Hansen's tutorial defaults) on the exact penalty -f + penalty*sum(viol)."""
    rng = np.random.default_rng(seed)
    n = prob.n
    lam_ = popsize or 4 + int(3 * math.log(n))
    mu = lam_ // 2
    w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    w /= w.sum()
    mueff = 1.0 / (w ** 2).sum()
    cc = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
    cs = (mueff + 2) / (n + mueff + 5)
    c1 = 2 / ((n + 1.3) ** 2 + mueff)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0, math.sqrt((mueff - 1) / (n + 1)) - 1) + cs
    chiN = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    m = rng.random(n) if u0 is None else np.asarray(u0, float).copy()
    sigma = sigma0
    C = np.eye(n)
    pc = np.zeros(n)
    ps = np.zeros(n)
    best = (np.inf, None)
    hist = []

    def fitness(X):
        with torch.no_grad():
            f, G = prob.eval(torch.tensor(np.clip(X, 0, 1), dtype=DT))
        G = torch.nan_to_num(G, nan=-10.0)
        pen = torch.clamp(-G, min=0.0).sum(-1)
        oob = np.abs(X - np.clip(X, 0, 1)).sum(-1)
        return (-f + penalty * pen).numpy() + penalty * oob, violation(G).numpy(), f.numpy()

    for g in range(gens):
        evals, B = np.linalg.eigh(C)
        evals = np.maximum(evals, 1e-20)
        Dm = np.sqrt(evals)
        z = rng.standard_normal((lam_, n))
        y = z @ np.diag(Dm) @ B.T
        X = m + sigma * y
        F, V, fval = fitness(X)
        order = np.argsort(F)
        if F[order[0]] < best[0]:
            best = (F[order[0]], np.clip(X[order[0]], 0, 1), V[order[0]], fval[order[0]])
        yw = (w[:, None] * y[order[:mu]]).sum(0)
        m = m + sigma * yw
        Cinvsqrt = B @ np.diag(1 / Dm) @ B.T
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * (Cinvsqrt @ yw)
        hsig = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (g + 1))) / chiN < 1.4 + 2 / (n + 1)
        pc = (1 - cc) * pc + hsig * math.sqrt(cc * (2 - cc) * mueff) * yw
        artmp = y[order[:mu]]
        C = (1 - c1 - cmu) * C + c1 * (np.outer(pc, pc) + (1 - hsig) * cc * (2 - cc) * C) + \
            cmu * (artmp.T @ np.diag(w) @ artmp)
        sigma *= math.exp((cs / damps) * (np.linalg.norm(ps) / chiN - 1))
        if g % 25 == 0:
            hist.append({"gen": g, "best_penalised": float(best[0]), "sigma": sigma})
        if sigma < 1e-6:
            break
    return {"u": best[1], "penalised": float(best[0]), "viol": float(best[2]), "f": float(best[3]), "hist": hist,
            "popsize": lam_, "generations": g + 1}


def sobol_starts(n, dim, seed=0, include=None):
    from scipy.stats import qmc
    U = qmc.Sobol(dim, scramble=True, seed=seed).random(n)
    U = torch.tensor(U, dtype=DT)
    if include is not None:
        U = torch.cat([include.reshape(1, -1), U[:-1]], 0)
    return U


def solve(prob: Problem, n_starts=32, iters=1500, polish=3, seed=0, include_current=True, verbose=False):
    """Multi-start projected Adam, then L-BFGS-B polish of the best feasible starts."""
    t0 = time.time()
    inc = prob.u_of(MD.CURRENT, s=0.0) if include_current else None
    U0 = sobol_starts(n_starts, prob.n, seed=seed, include=inc)
    U, f, G, lam = adam_al(prob, U0, iters=iters, verbose=verbose)
    v = violation(torch.nan_to_num(G, nan=-10.0))
    score = torch.where(v < 1e-3, f, f - 1e3 * v)
    order = torch.argsort(score, descending=True)
    results = []
    for j in order[:polish].tolist():
        u, lamj, hist = lbfgs_al(prob, U[j].numpy(), lam0=lam[j])
        with torch.no_grad():
            fj, Gj = prob.eval(torch.tensor(u[None], dtype=DT))
        vj = float(violation(torch.nan_to_num(Gj, nan=-10.0))[0])
        results.append({"u": u, "f": float(fj[0]), "viol": vj, "lam": lamj, "hist": hist, "start": int(j)})
    feas = [r for r in results if r["viol"] < 1e-3]
    best = max(feas, key=lambda r: r["f"]) if feas else min(results, key=lambda r: r["viol"])
    return {"best": best, "polished": results, "adam_feasible_fraction": float((v < 1e-3).float().mean()),
            "adam_best": float(score.max()), "elapsed_s": time.time() - t0, "n_starts": n_starts}


def design_of(prob: Problem, u):
    with torch.no_grad():
        f, G, out, x = prob.eval(torch.tensor(np.asarray(u)[None], dtype=DT), full=True)
    return {k: float(v[0]) for k, v in x.items()}, out, G[0], f[0]


def active_constraints(prob: Problem, G, lam, tol=0.05):
    """Constraints at or near their bound, with their multipliers (shadow prices in objective units / unit g)."""
    names = prob.names
    rows = []
    for i, nme in enumerate(names):
        gi = float(G[i])
        li = float(lam[i]) if lam is not None else 0.0
        if gi < tol or li > 1e-6:
            rows.append({"constraint": nme, "g_normalised": gi, "multiplier": li})
    return sorted(rows, key=lambda r: -r["multiplier"])


def sensitivities(opts: MD.Options, x: dict, cal=None, quantities=("q_wc", "usable_wc", "q_nom", "f1", "mass_g",
                                                                  "P_total_mean", "life_h")):
    """Exact gradients (autograd = adjoint) of key outputs with respect to every design variable, in physical
    units, plus elasticities (x/y dy/dx)."""
    xt = {k: torch.tensor([float(v)], dtype=DT, requires_grad=True) for k, v in x.items()}
    out = MD.evaluate(xt, opts, cal)
    ys = {"q_wc": out["q_wc"][0], "usable_wc": out["usable_wc"][0], "q_nom": out["q_nom"][0],
          "f1": out["stage"]["f1"][0], "mass_g": out["mass"]["with_margin_g"][0]}
    if "P_total_mean" in out:
        ys["P_total_mean"] = out["P_total_mean"][0]
        ys["life_h"] = out["life_assist_h"][0]
    res = {}
    for qn in quantities:
        if qn not in ys:
            continue
        grads = torch.autograd.grad(ys[qn], list(xt.values()), retain_graph=True, allow_unused=True)
        y = float(ys[qn].detach())
        row = {}
        for (k, v), gr in zip(xt.items(), grads):
            gval = 0.0 if gr is None else float(gr[0])
            row[k] = {"d_dx": gval, "elasticity": gval * float(v[0]) / y if y != 0 else float("nan")}
        res[qn] = {"value": y, "grad": row}
    return res


def lever_derivative(opts: MD.Options, x: dict, cal=None):
    """d(stroke)/d(lever) at fixed collar position: the lever n = zg / (zg - z_cc) is varied through the gimbal
    position (chain rule through the autograd gradient w.r.t. zg)."""
    zcc = x["zc0"] + MD.FIX["collar_L"] / 2
    zg = x["zg"]
    n = zg / (zg - zcc)
    dn_dzg = -zcc / (zg - zcc) ** 2
    s = sensitivities(opts, x, cal, quantities=("q_wc", "q_nom"))
    return {k: {"n": n, "d_dn": s[k]["grad"]["zg"]["d_dx"] / dn_dzg,
                "note": "includes the change of inertia and plate-length room with the gimbal position"} for k in s}
