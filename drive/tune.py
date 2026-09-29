"""Tuning of the heel-drive control gains on tuning writers only, then the frozen rules (SIMULATION).

Why Bayesian optimisation here: every evaluation is a closed-loop HW1-D simulation with friction, slip, stroke
matching and the recogniser; the objective is noisy and not differentiable, and each call costs seconds.  A Gaussian
process (Matern 5/2, maximum-likelihood length scales on a grid) with expected improvement finds good gains in 20-30
calls.  The hardware sizing, whose model is smooth and analytic, uses autograd instead (design_opt.py).

Objectives (declared here, before any test run; tuning writers 100-102 and seed 300 unless noted):
  guidance   J = mean(target error / target error without guidance) + 2 x max(0, letters read without - with)
             (dysgraphia-like learners, practice sentence);
  tremor     J = mean(ink error / ink error of Rev H with nothing on) over 5 and 8 Hz at 1 mm, + 0.01 x
             max(0, tremor-free distortion - 100 um) (the device must not bend clean writing by more than 100 um on
             average; ASSUMPTION threshold, about 3 % of a 3 mm x-height);
  lead       J = (1 - letters read) + target error / 1000 um in autowrite (relaxed writer, nose on).
The chosen gains, the objectives, the seeds and a hash go to results/drive/rules.json; the test stage refuses to run
without that file.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import replace
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np

from . import RESULTS_DIR
from . import scenarios as S

MU_TUNE = 0.9          # nominal tyre friction during tuning (the test draws mu per case)


# ----------------------------------------------------------------------------- a small GP-EI optimiser
def _matern52(A, B, ls):
    d = np.sqrt(np.sum(((A[:, None, :] - B[None, :, :]) / ls) ** 2, axis=-1))
    s5 = math.sqrt(5.0) * d
    return (1.0 + s5 + s5 * s5 / 3.0) * np.exp(-s5)


def _gp_fit(X, y, noise=1e-3):
    ym, ys = float(np.mean(y)), float(np.std(y) + 1e-9)
    z = (y - ym) / ys
    best = None
    for l in (0.1, 0.2, 0.35, 0.6, 1.0):
        ls = np.full(X.shape[1], l)
        K = _matern52(X, X, ls) + noise * np.eye(len(X))
        try:
            L = np.linalg.cholesky(K)
        except np.linalg.LinAlgError:
            continue
        a = np.linalg.solve(L.T, np.linalg.solve(L, z))
        ll = -0.5 * z @ a - np.sum(np.log(np.diag(L)))
        if best is None or ll > best[0]:
            best = (ll, ls, L, a)
    _, ls, L, a = best
    return {"ls": ls, "L": L, "a": a, "X": X, "ym": ym, "ys": ys}


def _gp_pred(gp, Xs):
    Ks = _matern52(Xs, gp["X"], gp["ls"])
    mu = Ks @ gp["a"]
    v = np.linalg.solve(gp["L"], Ks.T)
    var = np.maximum(1.0 - np.sum(v * v, axis=0), 1e-12)
    return gp["ym"] + gp["ys"] * mu, gp["ys"] * np.sqrt(var)


def _ei(mu, sd, best):
    from scipy.stats import norm
    z = (best - mu) / sd
    return (best - mu) * norm.cdf(z) + sd * norm.pdf(z)


def bayes_opt(f: Callable[[np.ndarray], float], bounds: Sequence[Tuple[float, float]], log: Sequence[bool],
              n_init: int = 6, n_iter: int = 14, seed: int = 0) -> Dict:
    """Minimise f over a box (log-scaled where asked).  Returns the history and the best point."""
    rng = np.random.default_rng(seed)
    d = len(bounds)
    lo = np.array([math.log(b[0]) if lg else b[0] for b, lg in zip(bounds, log)])
    hi = np.array([math.log(b[1]) if lg else b[1] for b, lg in zip(bounds, log)])

    def to_x(u):
        v = lo + u * (hi - lo)
        return np.array([math.exp(vi) if lg else vi for vi, lg in zip(v, log)])
    # Latin hypercube start
    U = (np.argsort(rng.random((n_init, d)), axis=0) + rng.random((n_init, d))) / n_init
    hist = []
    for u in U:
        hist.append((u, f(to_x(u))))
    for _ in range(n_iter):
        X = np.array([h[0] for h in hist]); y = np.array([h[1] for h in hist])
        gp = _gp_fit(X, y)
        cand = rng.random((3000, d))
        b = X[np.argmin(y)]
        cand = np.vstack([cand, np.clip(b + 0.05 * rng.standard_normal((500, d)), 0, 1)])
        mu, sd = _gp_pred(gp, cand)
        u = cand[int(np.argmax(_ei(mu, sd, float(np.min(y)))))]
        hist.append((u, f(to_x(u))))
    ys = [h[1] for h in hist]
    k = int(np.argmin(ys))
    return {"best_x": to_x(hist[k][0]).tolist(), "best_J": float(ys[k]),
            "history": [{"x": to_x(u).tolist(), "J": float(J)} for u, J in hist]}


# ----------------------------------------------------------------------------- objectives
class GuidanceObjective:
    def __init__(self, writers=(100, 101, 102), seeds=(300,), profile="dysgraphia"):
        self.cases = [S.practice_case(w, s, profile) for w in writers for s in seeds]
        self.ref = []
        for c in self.cases:
            ev, r = S.run_practice(c, "none", S.Gains(), MU_TUNE)
            self.ref.append((ev, r))

    def __call__(self, cond: str, g: S.Gains) -> float:
        J = []
        for c, (ev0, r0) in zip(self.cases, self.ref):
            ev, _ = S.run_practice(c, cond, g, MU_TUNE, ref=r0)
            J.append(ev["target_err_um"] / ev0["target_err_um"] + 2.0 * max(0.0, ev0["letters_read_ok"] - ev["letters_read_ok"]))
        return float(np.mean(J))


class TremorObjective:
    def __init__(self, writers=(100, 101), seed=300, cases=((5.0, 1e-3), (8.0, 1e-3))):
        self.w = [S.ETWriter(w) for w in writers]
        self.seed = seed
        self.cases = cases
        self.base = {}
        for etw in self.w:
            for f0, a in cases:
                self.base[(etw.w, f0)] = S.run_tremor(etw, f0, a, seed, ["none"], S.Gains(), MU_TUNE)["none"]["ink_err_um"]

    def __call__(self, cond: str, g: S.Gains) -> float:
        J, dist = [], []
        for etw in self.w:
            for f0, a in self.cases:
                ev = S.run_tremor(etw, f0, a, self.seed, [cond], g, MU_TUNE)[cond]
                J.append(ev["ink_err_um"] / self.base[(etw.w, f0)])
            ev0 = S.run_tremor(etw, 0.0, 0.0, self.seed, [cond], g, MU_TUNE)[cond]
            dist.append(ev0["ink_err_um"])
        return float(np.mean(J) + 0.01 * max(0.0, float(np.mean(dist)) - 100.0))


class LeadObjective:
    def __init__(self, writers=(100, 101), seed=300):
        self.cases = [S.autowrite_case(w, seed) for w in writers]

    def __call__(self, cond: str, g: S.Gains) -> float:
        J = []
        for c in self.cases:
            ev, _ = S.run_autowrite(c, cond, g, MU_TUNE)
            J.append((1.0 - (ev.get("letters_read_ok") or 0.0)) + (ev.get("target_err_um") or 1000.0) / 1000.0)
        return float(np.mean(J))


# ----------------------------------------------------------------------------- the tuning run
def tune(quick: bool = False, log=print) -> Dict:
    t0 = time.time()
    g = S.Gains()
    out = {"objectives": __doc__.split("Objectives")[1].split("The chosen")[0].strip(), "mu_tune": MU_TUNE,
           "tuning_writers": {"guidance": [100, 101, 102], "tremor": [100, 101], "lead": [100, 101]},
           "tuning_seed": 300, "steps": {}}
    n_init, n_iter = (4, 4) if quick else (6, 14)
    # --- guidance: the steered wheel's look-ahead (grid) and the holonomic law (BO)
    GO = GuidanceObjective(writers=(100,) if quick else (100, 101, 102))
    grid = [0.5e-3, 0.8e-3, 1.2e-3, 2.0e-3] if quick else [0.3e-3, 0.5e-3, 0.8e-3, 1.2e-3, 2.0e-3, 3.0e-3]
    rows = [{"L_a_mm": La * 1e3, "J": GO("wheel_path", replace(g, L_a=La))} for La in grid]
    best = min(rows, key=lambda r: r["J"])
    g = replace(g, L_a=best["L_a_mm"] * 1e-3)
    out["steps"]["wheel_L_a_grid"] = {"rows": rows, "chosen_mm": best["L_a_mm"]}
    log(f"  wheel pure pursuit: look-ahead {best['L_a_mm']} mm (J {best['J']:.3f})  [{time.time() - t0:.0f}s]")

    def f_st(x):
        return GO("wheel_path", replace(g, plaw=1, k_st=x[0], L_t=x[1]))
    bo_st = bayes_opt(f_st, [(1.0, 40.0), (0.05e-3, 1.5e-3)], [True, False], n_init, n_iter, seed=6)
    out["steps"]["wheel_stanley_bo"] = bo_st
    law = "stanley" if bo_st["best_J"] < best["J"] else "pursuit"
    if law == "stanley":
        g = replace(g, plaw=1, k_st=bo_st["best_x"][0], L_t=bo_st["best_x"][1])
    out["steps"]["wheel_law_chosen"] = {"law": law, "J_pursuit": best["J"], "J_stanley": bo_st["best_J"]}
    log(f"  wheel Stanley k {bo_st['best_x'][0]:.1f} 1/s L_t {bo_st['best_x'][1] * 1e3:.2f} mm (J {bo_st['best_J']:.3f}); "
        f"chosen: {law}  [{time.time() - t0:.0f}s]")
    rows = [{"band_mm": b * 1e3, "J": GO("wheel_partial", replace(g, band=b))} for b in ([0.5e-3, 1.0e-3] if quick else [0.3e-3, 0.5e-3, 1.0e-3, 1.5e-3])]
    bb = min(rows, key=lambda r: r["J"])
    out["steps"]["wheel_band_grid"] = {"rows": rows, "chosen_mm": bb["band_mm"]}
    g_band_wheel = bb["band_mm"] * 1e-3

    def f_ball(x):
        return GO("ball_full", replace(g, K_full=x[0], D=x[1], lead=x[2]))
    bo = bayes_opt(f_ball, [(80.0, 800.0), (0.0, 6.0), (0.0, 0.25)], [True, False, False], n_init, n_iter, seed=1)
    g = replace(g, K_full=bo["best_x"][0], D=bo["best_x"][1], lead=bo["best_x"][2])
    out["steps"]["ball_full_bo"] = bo
    log(f"  ball full law K {bo['best_x'][0]:.0f} N/m D {bo['best_x'][1]:.2f} lead {bo['best_x'][2]:.3f} (J {bo['best_J']:.3f})  [{time.time() - t0:.0f}s]")
    # --- tremor laws
    TO = TremorObjective(writers=(100,) if quick else (100, 101))

    def f_ball_d(x):
        return TO("ball_damp", replace(g, b_ball=x[0], f_lp=x[1]))
    bo = bayes_opt(f_ball_d, [(1.0, 25.0), (2.0, 10.0)], [True, False], n_init, n_iter, seed=2)
    g_ball_damp = {"b_ball": bo["best_x"][0], "f_lp": bo["best_x"][1]}
    out["steps"]["ball_damp_bo"] = bo
    log(f"  ball damper b {bo['best_x'][0]:.1f} N s/m f_lp {bo['best_x'][1]:.1f} Hz (J {bo['best_J']:.3f})  [{time.time() - t0:.0f}s]")

    def f_wb(x):
        return TO("wheel_tremor_brake", replace(g, b_wheel=x[0], m_eff=x[1], f_lp=x[2]))
    bo = bayes_opt(f_wb, [(1.0, 25.0), (0.05, 2.0), (2.0, 10.0)], [True, True, False], n_init, n_iter, seed=3)
    g_wheel_trem = {"b_wheel": bo["best_x"][0], "m_eff": bo["best_x"][1], "f_lp_wheel": bo["best_x"][2]}
    out["steps"]["wheel_tremor_brake_bo"] = bo
    log(f"  wheel tremor b {bo['best_x'][0]:.1f} m_eff {bo['best_x'][1]:.2f} f_lp {bo['best_x'][2]:.1f} (J {bo['best_J']:.3f})  [{time.time() - t0:.0f}s]")
    # --- lead-through / autowrite
    LO = LeadObjective(writers=(100,) if quick else (100, 101))

    def f_lead(x, cond):
        return LO(cond, replace(g, F_lead=x[0], Kv=x[1]))
    bo_sd = bayes_opt(lambda x: f_lead(x, "sd_lead+nose"), [(0.1, 0.45), (0.0, 30.0)], [False, False], n_init, n_iter, seed=4)
    bo_ball = bayes_opt(lambda x: f_lead(x, "ball_lead+nose"), [(0.1, 0.45), (0.0, 30.0)], [False, False], n_init, n_iter, seed=5)
    out["steps"]["sd_lead_bo"] = bo_sd
    out["steps"]["ball_lead_bo"] = bo_ball
    log(f"  lead: wheel F {bo_sd['best_x'][0]:.2f} Kv {bo_sd['best_x'][1]:.1f} (J {bo_sd['best_J']:.3f}); ball F "
        f"{bo_ball['best_x'][0]:.2f} Kv {bo_ball['best_x'][1]:.1f} (J {bo_ball['best_J']:.3f})  [{time.time() - t0:.0f}s]")
    out["gains"] = {"common": g.as_dict(), "wheel_partial_band": g_band_wheel, "ball_damp": g_ball_damp,
                    "wheel_tremor": g_wheel_trem,
                    "sd_lead": {"F_lead": bo_sd["best_x"][0], "Kv": bo_sd["best_x"][1]},
                    "ball_lead": {"F_lead": bo_ball["best_x"][0], "Kv": bo_ball["best_x"][1]}}
    out["elapsed_s"] = time.time() - t0
    out["quick"] = quick
    return out


def gains_for(rules: Dict, cond: str) -> S.Gains:
    """The frozen gains for a condition (the test stage uses only this)."""
    G = rules["gains"]
    g = S.Gains(**G["common"])
    c = cond.replace("+nose_akf", "").replace("+nose", "")
    c = c.replace("ballsmooth", "ball")          # the smooth-roller ball uses the ball's gains (hardware differs only)
    if c == "wheel_partial":
        g = replace(g, band=G["wheel_partial_band"])
    if c in ("ball_damp", "ball_brake"):
        g = replace(g, b_ball=G["ball_damp"]["b_ball"], f_lp=G["ball_damp"]["f_lp"])
    if c.startswith("wheel_tremor"):
        w = G["wheel_tremor"]
        g = replace(g, b_wheel=w["b_wheel"], m_eff=w["m_eff"], f_lp=w["f_lp_wheel"])
    if c == "sd_lead":
        g = replace(g, F_lead=G["sd_lead"]["F_lead"], Kv=G["sd_lead"]["Kv"])
    if c == "ball_lead":
        g = replace(g, F_lead=G["ball_lead"]["F_lead"], Kv=G["ball_lead"]["Kv"])
    return g


def freeze(result: Dict, path=None) -> Dict:
    path = path or (RESULTS_DIR / "rules.json")
    body = {k: v for k, v in result.items() if k != "steps"}
    body["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body["test_plan"] = {"writers": [0, 1, 2, 3, 4, 5], "seeds": [200, 201, 202, 203],
                         "mu": "per case uniform 0.6-1.2 (params CONTACT mu_drive_range), seeded by case",
                         "rule": "no gain or rule is changed after this file is written; the test tables use it as is"}
    s = json.dumps(body, sort_keys=True, default=float)
    body["sha256_16"] = hashlib.sha256(s.encode()).hexdigest()[:16]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1, default=float))
    return body


def load_rules(path=None) -> Dict:
    path = path or (RESULTS_DIR / "rules.json")
    if not path.exists():
        raise FileNotFoundError("results/drive/rules.json is missing: run the tuning stage first (no test before rules)")
    return json.loads(path.read_text())
