r"""Design optimisation of the candidate mechanisms (CALC): CMA-ES over real part choices and continuous variables, an
adjoint (reverse-mode autograd) L-BFGS polish of the continuous variables, and Pareto fronts.

Encoding.  Continuous variables (designs.VAR_BOUNDS) are mapped to [0, 1]; discrete part choices (magnet grade,
flexure alloy and stock thickness, magnet wire, back-iron alloy) are encoded as continuous coordinates in [0, n) and
floored when a design is evaluated.  CMA-ES (Hansen's (mu/mu_w, lambda) with rank-mu and rank-one updates; own
numpy implementation, no external package) searches the whole vector; the best design's continuous variables are then
polished by L-BFGS on the differentiable model (gradients by autograd; checked against central differences in
tests/test_designs.py).

Objective.  J = P_autowrite (copper loss while autowriting with 1 mm rms tremor on top) + mu_m * added mass + 10 * penalties,
swept over mu_m (W/kg) and the required guaranteed travel x_min, per candidate.  Feasible designs (penalty < 1e-6) from
every CMA-ES population and every polish enter the Pareto fronts: maximise travel and Km_tip, minimise mass and power.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

from . import designs as DS

GRADES = list(DS.MAGNET_GRADES)
FLEXES = list(DS.FLEXURES)
WIRES = list(DS.WIRES)
IRONS = list(DS.BACK_IRON)
DISCRETE = [("grade", GRADES), ("flexure", FLEXES), ("t_flex", list(DS.STOCK_T)), ("wire", WIRES), ("iron", IRONS)]


# ------------------------------------------------------------------ CMA-ES
def cmaes(f: Callable[[np.ndarray], float], x0: np.ndarray, sigma0: float, iters: int = 120, popsize: Optional[int] = None,
          seed: int = 0, lo: float = 0.0, hi: float = 1.0, log: Optional[List] = None) -> Tuple[np.ndarray, float]:
    """Minimise f over the box [lo, hi]^n (repair by clipping; f sees the clipped point)."""
    rng = np.random.default_rng(seed)
    n = len(x0)
    lam = popsize or 4 + int(3 * math.log(n))
    mu = lam // 2
    wts = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    wts /= wts.sum()
    mueff = 1.0 / np.sum(wts ** 2)
    cc = (4 + mueff / n) / (n + 4 + 2 * mueff / n)
    cs = (mueff + 2) / (n + mueff + 5)
    c1 = 2 / ((n + 1.3) ** 2 + mueff)
    cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff))
    damps = 1 + 2 * max(0.0, math.sqrt((mueff - 1) / (n + 1)) - 1) + cs
    chiN = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    m = np.array(x0, float)
    sigma = sigma0
    pc = np.zeros(n); ps = np.zeros(n)
    C = np.eye(n); B = np.eye(n); D = np.ones(n); invsqrtC = np.eye(n)
    best_x, best_f = m.copy(), f(np.clip(m, lo, hi))
    eigeneval = 0
    for g in range(iters):
        z = rng.standard_normal((lam, n))
        y = z @ (B * D).T
        X = m + sigma * y
        Xc = np.clip(X, lo, hi)
        fit = np.array([f(xc) + 1e3 * np.sum((x - xc) ** 2) for x, xc in zip(X, Xc)])
        idx = np.argsort(fit)
        if fit[idx[0]] < best_f:
            best_f, best_x = float(fit[idx[0]]), Xc[idx[0]].copy()
        if log is not None:
            log.append((g, float(fit[idx[0]]), float(np.median(fit))))
        old = m.copy()
        m = np.sum(wts[:, None] * X[idx[:mu]], axis=0)
        ymean = (m - old) / sigma
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * mueff) * invsqrtC @ ymean
        hsig = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (g + 1))) / chiN < 1.4 + 2 / (n + 1)
        pc = (1 - cc) * pc + hsig * math.sqrt(cc * (2 - cc) * mueff) * ymean
        artmp = (X[idx[:mu]] - old) / sigma
        C = ((1 - c1 - cmu) * C + c1 * (np.outer(pc, pc) + (1 - hsig) * cc * (2 - cc) * C)
             + cmu * (artmp.T * wts) @ artmp)
        sigma *= math.exp((cs / damps) * (np.linalg.norm(ps) / chiN - 1))
        sigma = min(sigma, 1.0)
        if g - eigeneval > lam / (c1 + cmu) / n / 10:
            eigeneval = g
            C = np.triu(C) + np.triu(C, 1).T
            Dv, B = np.linalg.eigh(C)
            D = np.sqrt(np.maximum(Dv, 1e-20))
            invsqrtC = B @ np.diag(1 / D) @ B.T
        if sigma * np.max(D) < 1e-7:
            break
    return best_x, best_f


# ------------------------------------------------------------------ encoding
class Problem:
    def __init__(self, kind: str, duty: DS.Duty, mu_m: float, bore: str = "22", servo_hz: float = 80.0, fixed: Optional[Dict] = None):
        self.kind = kind
        self.duty = duty
        self.mu_m = mu_m
        self.bore = bore
        self.servo_hz = servo_hz
        self.bounds = DS.VAR_BOUNDS[kind]
        self.cont = list(self.bounds)
        self.fixed = fixed or {}
        self.n = len(self.cont) + len(DISCRETE)
        self.archive: List[Dict] = []

    def decode(self, x: np.ndarray) -> Tuple[Dict[str, float], DS.Parts]:
        v = {}
        for i, k in enumerate(self.cont):
            lo, hi = self.bounds[k]
            v[k] = lo + (hi - lo) * float(x[i])
        v.update(self.fixed)
        ch = {}
        for j, (name, opts) in enumerate(DISCRETE):
            u = float(x[len(self.cont) + j])
            ch[name] = opts[min(len(opts) - 1, int(u * len(opts)))]
        parts = DS.Parts(grade=ch["grade"], flexure=ch["flexure"], t_flex=ch["t_flex"], wire=ch["wire"], iron=ch["iron"],
                         bore=self.bore)
        return v, parts

    def evaluate(self, v: Dict[str, float], parts: DS.Parts) -> Dict:
        vt = {k: torch.tensor(val, dtype=DS.DT) for k, val in v.items()}
        return DS.evaluate(self.kind, vt, parts, self.duty, self.servo_hz)

    def objective(self, out: Dict) -> torch.Tensor:
        return out["P_autowrite"] + self.mu_m * out["mass_added"] + 10.0 * out["pen"]

    def f(self, x: np.ndarray) -> float:
        v, parts = self.decode(x)
        with torch.no_grad():
            out = self.evaluate(v, parts)
            J = float(self.objective(out))
        if not math.isfinite(J):
            return 1e9
        if float(out["pen"]) < 1e-6:
            self.archive.append(summary(self.kind, v, parts, out))
        return J


def summary(kind, v, parts, out) -> Dict:
    o = DS.to_float(out)
    return {"kind": kind, "vars": dict(v), "parts": dict(parts.__dict__), "X_min_mm": o["X_min"] * 1e3, "X_nom_mm": o["X_nom"] * 1e3,
            "Km_tip": o["Km_tip"], "Km_act": o["Km_act"], "B_gap_T": o["B_gap"], "m_eff_tip_g": o["m_eff_tip"] * 1e3,
            "k_tip_N_m": o["k_tip"], "mass_added_g": o["mass_added"] * 1e3, "m_act_move_g": o["m_act_move"] * 1e3,
            "m_act_stat_g": o["m_act_stat"] * 1e3, "P_tremor_only_W": o["P_tremor"], "F_aw_rms_N": o["F_aw_rms"], "P_autowrite_W": o["P_autowrite"], "P_tremor_W": o["P_tremor"],
            "F_pk_tip_N": o["F_pk_tip"], "F_pk_need_N": o["F_pk_tip_need"], "f_parasitic_Hz": o["f_parasitic"],
            "servo_hz_max": o["servo_hz_max"], "r_act_mm": o["r_act"] * 1e3, "front_R_mm": o["front_R"] * 1e3,
            "refill_slide_mm": o["refill_slide"] * 1e3, "stroke_act_mm": o["stroke_act"] * 1e3, "gap_mm": o["gap"] * 1e3,
            "eps_u": o["eps_u"], "eps_allow": o["eps_f_allow"], "dT_coil_K": o["dT_coil"], "z_p_mm": o["z_p"] * 1e3,
            "z_a_mm": o["z_a"] * 1e3, "d_cm_mm": o["d_cm"] * 1e3, "F_grav_tip_N": o["F_grav_tip"], "pen": o["pen"]}


def polish(prob: Problem, v0: Dict[str, float], parts: DS.Parts, iters: int = 60) -> Tuple[Dict[str, float], Dict]:
    """Adjoint polish: L-BFGS on the continuous variables (sigmoid-bounded), discrete parts fixed."""
    keys = [k for k in prob.cont if k not in prob.fixed]
    raw = {}
    for k in keys:
        lo, hi = prob.bounds[k]
        u = min(max((v0[k] - lo) / (hi - lo), 1e-4), 1 - 1e-4)
        raw[k] = torch.tensor(math.log(u / (1 - u)), dtype=DS.DT, requires_grad=True)
    opt = torch.optim.LBFGS(list(raw.values()), max_iter=iters, line_search_fn="strong_wolfe")

    def vars_():
        v = {}
        for k in keys:
            lo, hi = prob.bounds[k]
            v[k] = lo + (hi - lo) * torch.sigmoid(raw[k])
        for k, val in prob.fixed.items():
            v[k] = torch.tensor(val, dtype=DS.DT)
        return v

    def closure():
        opt.zero_grad()
        out = DS.evaluate(prob.kind, vars_(), parts, prob.duty, prob.servo_hz)
        J = prob.objective(out)
        J.backward()
        return J
    try:
        opt.step(closure)
    except Exception:
        pass
    with torch.no_grad():
        v = {k: float(x) for k, x in vars_().items()}
        out = prob.evaluate(v, parts)
    return v, out


def run(kind: str, duty: DS.Duty, mu_m: float, seed: int = 0, iters: int = 120, popsize: int = 20, bore: str = "22",
        fixed: Optional[Dict] = None) -> Dict:
    prob = Problem(kind, duty, mu_m, bore=bore, fixed=fixed)
    rng = np.random.default_rng(seed)
    x0 = rng.uniform(0.3, 0.7, prob.n)
    log: List = []
    x, fbest = cmaes(prob.f, x0, 0.3, iters=iters, popsize=popsize, seed=seed, log=log)
    v, parts = prob.decode(x)
    vp, outp = polish(prob, v, parts)
    Jp = float(prob.objective(outp))
    s = summary(kind, vp, parts, outp)
    if float(outp["pen"]) < 1e-6:
        prob.archive.append(s)
    return {"kind": kind, "mu_m": mu_m, "x_min_mm": duty.x_min * 1e3, "J_cma": fbest, "J_polished": Jp, "best": s,
            "feasible": float(outp["pen"]) < 1e-6, "log": log, "archive": prob.archive}


def pareto(rows: List[Dict], keys=(("X_min_mm", 1), ("Km_tip", 1), ("mass_added_g", -1), ("P_autowrite_W", -1))) -> List[Dict]:
    """Non-dominated designs (maximise +1 keys, minimise -1 keys).  Sort-filter-skyline: after sorting by the sum of the
    normalised objectives (descending), a point can only be dominated by an earlier one, and checking it against the
    current front suffices (dominance is transitive)."""
    if not rows:
        return []
    A = np.array([[r[k] * s for k, s in keys] for r in rows], float)
    Z = (A - A.min(axis=0)) / np.maximum(A.max(axis=0) - A.min(axis=0), 1e-300)
    order = np.argsort(-Z.sum(axis=1), kind="stable")
    front = np.empty((0, A.shape[1]))
    keep = []
    for i in order:
        a = A[i]
        if len(front) and np.any(np.all(front >= a, axis=1) & np.any(front > a, axis=1)):
            continue
        front = np.vstack([front, a])
        keep.append(rows[i])
    return keep


def grad_check(kind: str = "gimbal_axial", eps: float = 1e-7, seed: int = 1) -> Dict[str, Tuple[float, float]]:
    """Autograd against central differences on the smooth objective P_autowrite + mass (CALC; test)."""
    duty = DS.Duty()
    parts = DS.Parts()
    rng = np.random.default_rng(seed)
    b = DS.VAR_BOUNDS[kind]
    v0 = {k: lo + (hi - lo) * rng.uniform(0.35, 0.65) for k, (lo, hi) in b.items()}
    x = {k: torch.tensor(val, dtype=DS.DT, requires_grad=True) for k, val in v0.items()}
    out = DS.evaluate(kind, x, parts, duty)
    J = out["P_autowrite"] + 2.0 * out["mass_added"]
    J.backward()
    res = {}
    for k in v0:
        h = eps * max(abs(v0[k]), 1e-3)
        vp = dict(v0); vm = dict(v0)
        vp[k] += h; vm[k] -= h
        fp = DS.evaluate(kind, {kk: torch.tensor(vv, dtype=DS.DT) for kk, vv in vp.items()}, parts, duty)
        fm = DS.evaluate(kind, {kk: torch.tensor(vv, dtype=DS.DT) for kk, vv in vm.items()}, parts, duty)
        fd = float((fp["P_autowrite"] + 2.0 * fp["mass_added"]) - (fm["P_autowrite"] + 2.0 * fm["mass_added"])) / (2 * h)
        g = x[k].grad
        res[k] = (0.0 if g is None else float(g), fd)
    return res


KINDS = ("gimbal_radial", "gimbal_axial", "gimbal_sphere", "dual_plane", "coarse_fine", "xy_wire")


def sweep(duty_base: DS.Duty, x_mins=(4e-3, 5e-3, 6e-3, 7e-3, 8e-3), mus=(1.0, 4.0), bores=("22", "24"), kinds=KINDS,
          seeds=(0,), iters: int = 150, popsize: int = 16, progress=None) -> Dict:
    """Every candidate at every required travel, mass weight and bore (CALC).  Returns the best design per cell and the
    archive of feasible designs for the Pareto fronts."""
    best, archive = [], []
    for kind in kinds:
        for bore in bores:
            for xm in x_mins:
                for mu in mus:
                    for sd in seeds:
                        duty = replace(duty_base, x_min=xm)
                        r = run(kind, duty, mu, seed=sd, iters=iters, popsize=popsize, bore=bore)
                        b = dict(r["best"])
                        b.update({"feasible": r["feasible"], "mu_m": mu, "x_min_req_mm": xm * 1e3, "bore": bore, "seed": sd,
                                  "J": r["J_polished"]})
                        best.append(b)
                        for a in r["archive"]:
                            a = dict(a); a.update({"mu_m": mu, "x_min_req_mm": xm * 1e3, "bore": bore})
                            archive.append(a)
                        if progress:
                            progress(kind, bore, xm, mu, sd, r["feasible"], b["P_autowrite_W"], b["mass_added_g"])
    return {"best": best, "archive": archive}
