"""Words read out of 10 against the tremor left at the tip: the model, its fit, its inversion, the writer bootstrap.

Model (fixed before any reading; CALC on SIM points): a log-logistic fall from the tremor-free level to a floor,
    w(r) = w_lo + (w_hi - w_lo) / (1 + (r / r50)^s),        r = tremor left at the tip, mm (R's measure)
with w_hi the words read with no tremor left, w_lo the floor at large tremor, r50 the residual at the midpoint and s the
steepness.  Fitted by least squares on the per-case points (every run of every case: its measured tip tremor and its
words out of 10), with bounds w_lo in [0, 3], w_hi in [0.5, 10], r50 in [0.01, 5] mm, s in [0.5, 15], from a small
fixed grid of starts (the lowest cost wins).  Clean notes enter at r = 0.

Read off the curve (DEC-055 and the target of any estimator):
  r_plus2  the residual at which w(r) = w_ord + 2, w_ord = the ordinary pen's mean words at the severe class of the
           same split (DEC-055: at least 2 more readable words out of 10 than the ordinary pen)
  r_80     the residual at which w(r) = 0.8 x w_clean, w_clean = the mean words on the same notes without tremor
Uncertainty: 2000 bootstrap resamples of WRITERS (the participant level, as R's cards), each refitted, with w_ord and
w_clean recomputed on the resample; 95 % percentile intervals.  An unreachable target gives NaN (counted).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

BOUNDS = (np.array([0.0, 0.5, 0.01, 0.5]), np.array([3.0, 10.0, 5.0, 15.0]))
STARTS = [(r50, s) for r50 in (0.25, 0.5, 1.0) for s in (1.5, 3.0, 6.0)]
N_BOOT = 2000
BOOT_SEED = 20260930


def model(r, p) -> np.ndarray:
    w_lo, w_hi, r50, s = p
    r = np.maximum(np.asarray(r, float), 0.0)
    return w_lo + (w_hi - w_lo) / (1.0 + (r / r50) ** s)


def invert(p, w_target: float) -> float:
    """The residual (mm) at which the curve equals w_target (NaN if the curve never reaches it)."""
    w_lo, w_hi, r50, s = p
    lo, hi = min(w_lo, w_hi), max(w_lo, w_hi)
    if not (np.isfinite(w_target) and lo < w_target < hi):
        return float("nan")
    return float(r50 * ((w_hi - w_lo) / (w_target - w_lo) - 1.0) ** (1.0 / s))


def fit(r: Sequence[float], w: Sequence[float], p_init: Optional[Sequence[float]] = None, warm_only: bool = False) -> Dict:
    """Least-squares fit of the model to points (r mm, words of 10); warm_only: start from p_init alone (bootstrap)."""
    from scipy.optimize import least_squares
    r = np.asarray(r, float)
    w = np.asarray(w, float)
    ok = np.isfinite(r) & np.isfinite(w)
    r, w = r[ok], w[ok]
    if len(r) < 4:
        return {"p": [float("nan")] * 4, "cost": float("nan"), "n": int(len(r)), "ok": False}
    hi0 = float(np.clip(np.mean(w[r <= np.percentile(r, 20)]) if len(r) > 4 else w.max(), 0.6, 9.9))
    lo0 = float(np.clip(np.mean(w[r >= np.percentile(r, 80)]) if len(r) > 4 else 0.0, 0.0, 2.9))
    starts = [tuple(p_init)] if p_init is not None and np.all(np.isfinite(p_init)) else []
    if not (warm_only and starts):
        starts += [(lo0, hi0, r50, s) for r50, s in STARTS]
    best = None
    for p0 in starts:
        p0 = np.clip(np.asarray(p0, float), BOUNDS[0] + 1e-9, BOUNDS[1] - 1e-9)
        try:
            res = least_squares(lambda p: model(r, p) - w, p0, bounds=BOUNDS, method="trf")
        except Exception:
            continue
        if best is None or res.cost < best.cost:
            best = res
    if best is None:
        return {"p": [float("nan")] * 4, "cost": float("nan"), "n": int(len(r)), "ok": False}
    resid = model(r, best.x) - w
    return {"p": [float(x) for x in best.x], "cost": float(best.cost), "n": int(len(r)), "ok": bool(best.success),
            "rmse_words": float(np.sqrt(np.mean(resid ** 2))),
            "params": dict(zip(("w_lo", "w_hi", "r50_mm", "steepness"), [float(x) for x in best.x]))}


def thresholds(p, w_ord: float, w_clean: float) -> Dict[str, float]:
    return {"r_plus2_mm": invert(p, w_ord + 2.0), "r_80_mm": invert(p, 0.8 * w_clean),
            "w_target_plus2": w_ord + 2.0, "w_target_80": 0.8 * w_clean}


def _stack(points: Dict[str, List[Tuple[float, float]]], writers: Sequence[str]):
    r, w = [], []
    for wr in writers:
        for a, b in points.get(wr, []):
            r.append(a)
            w.append(b)
    return np.array(r, float), np.array(w, float)


def fit_with_ci(points: Dict[str, List[Tuple[float, float]]], ord_by_writer: Dict[str, float],
                clean_by_writer: Dict[str, float], n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> Dict:
    """Fit on all writers' points, thresholds, and the writer-bootstrap intervals of the thresholds and parameters.
    points: {writer: [(r_mm, words_of_10), ...]}; ord_by_writer / clean_by_writer: per-writer means."""
    writers = sorted(points)
    r, w = _stack(points, writers)
    f = fit(r, w)
    w_ord = float(np.mean([ord_by_writer[x] for x in writers if x in ord_by_writer])) if ord_by_writer else float("nan")
    w_clean = float(np.mean([clean_by_writer[x] for x in writers if x in clean_by_writer])) if clean_by_writer else float("nan")
    th = thresholds(f["p"], w_ord, w_clean) if f["ok"] or np.all(np.isfinite(f["p"])) else \
        {"r_plus2_mm": float("nan"), "r_80_mm": float("nan")}
    out = {"fit": f, "w_ord_severe": w_ord, "w_clean": w_clean, **th, "n_writers": len(writers), "n_points": int(len(r))}
    if n_boot and len(writers) > 1 and np.all(np.isfinite(f["p"])):
        rng = np.random.default_rng(seed)
        bs = {"r_plus2_mm": [], "r_80_mm": [], "w_lo": [], "w_hi": [], "r50_mm": [], "steepness": []}
        for _ in range(n_boot):
            pick = [writers[j] for j in rng.integers(0, len(writers), len(writers))]
            rb, wb = _stack(points, pick)
            fb = fit(rb, wb, p_init=f["p"], warm_only=True)
            if not np.all(np.isfinite(fb["p"])):
                continue
            wo = float(np.mean([ord_by_writer[x] for x in pick if x in ord_by_writer])) if ord_by_writer else float("nan")
            wc = float(np.mean([clean_by_writer[x] for x in pick if x in clean_by_writer])) if clean_by_writer else float("nan")
            tb = thresholds(fb["p"], wo, wc)
            bs["r_plus2_mm"].append(tb["r_plus2_mm"])
            bs["r_80_mm"].append(tb["r_80_mm"])
            for k, v in zip(("w_lo", "w_hi", "r50_mm", "steepness"), fb["p"]):
                bs[k].append(v)
        ci = {}
        for k, v in bs.items():
            a = np.array(v, float)
            fin = a[np.isfinite(a)]
            ci[k] = {"lo": float(np.percentile(fin, 2.5)) if len(fin) else float("nan"),
                     "hi": float(np.percentile(fin, 97.5)) if len(fin) else float("nan"),
                     "n": int(len(a)), "n_unreachable": int(np.sum(~np.isfinite(a)))}
        out["ci95"] = ci
        out["bootstrap"] = {"n": n_boot, "seed": seed, "unit": "writer"}
    return out


def curve_points(p, r_max: float = 2.0, n: int = 200) -> List[Tuple[float, float]]:
    rr = np.concatenate([[0.0], np.geomspace(0.005, r_max, n)])
    return [(float(a), float(b)) for a, b in zip(rr, model(rr, p))]


def band(points: Dict[str, List[Tuple[float, float]]], p_full, rr: np.ndarray, n_boot: int = 400,
         seed: int = BOOT_SEED + 1) -> Tuple[np.ndarray, np.ndarray]:
    """Pointwise 95 % writer-bootstrap band of the fitted curve at the residuals rr (for the figure)."""
    writers = sorted(points)
    rng = np.random.default_rng(seed)
    W = []
    for _ in range(n_boot):
        pick = [writers[j] for j in rng.integers(0, len(writers), len(writers))]
        rb, wb = _stack(points, pick)
        fb = fit(rb, wb, p_init=p_full, warm_only=True)
        if np.all(np.isfinite(fb["p"])):
            W.append(model(rr, fb["p"]))
    if not W:
        return np.full(len(rr), np.nan), np.full(len(rr), np.nan)
    W = np.array(W)
    return np.percentile(W, 2.5, axis=0), np.percentile(W, 97.5, axis=0)
