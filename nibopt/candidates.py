r"""Recommended candidates from the pooled feasible points, local refinement, and the targeted questions (CALCULATION).

Selection (feasible points of every run, fill fixed at study B / K's 0.55 for the recommendations so that no
recommended design rests on the higher fills, which are an ASSUMPTION):
  reach_first  the largest usable radius in a body of 24 mm or less; ties (within 0.03 mm) by the worst-case loss
  balanced     usable radius >= 1.5 mm (DEC-050's option, study F's perfect-knowledge line) in <= 24 mm with the lowest
               typical-duty loss; if none is feasible, the design with the most reach per typical watt
  slim         the smallest body diameter that keeps +-1.0 mm (DEC-060) with every constraint met; ties by typical loss
Refinement: the categorical genes, reach and body diameter fixed, a (1 + lambda) evolution strategy with Deb's rules on
the continuous genes minimises the typical-duty loss (the worst-case loss as the tie-break).
Targeted runs: 'reach2' fixes the usable radius at 2.0 mm and lets the body grow to 34 mm (objectives: diameter and
typical loss); 'reach15' fixes 1.5 mm in <= 24 mm (objectives: typical and worst-case loss).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import optimise as O


def feasible(points: List[Dict], fill055: bool = False) -> List[Dict]:
    out = [p for p in points if p.get("ok") and p["V"] <= 0]
    if fill055:
        i = O.NAMES.index("fill")
        out = [p for p in out if O._cat("fill", p["x"][i]) == 0.55]
    return out


def select(points: List[Dict]) -> Dict[str, Dict]:
    fz = feasible(points, fill055=True)
    sel = {}
    f24 = [p for p in fz if p["F"][3] <= 24.0 + 1e-9]
    if f24:
        rmax = max(-p["F"][0] for p in f24)
        pool = [p for p in f24 if -p["F"][0] >= rmax - 0.03]
        sel["reach_first"] = min(pool, key=lambda p: p["F"][1])
        b = [p for p in f24 if -p["F"][0] >= 1.5 - 1e-9 and p["F"][4] <= 160.0]
        if b:
            sel["balanced"] = min(b, key=lambda p: p["F"][2])
        else:
            sel["balanced"] = max(f24, key=lambda p: -p["F"][0] / p["F"][2])
    s = [p for p in fz if -p["F"][0] >= 1.0 - 1e-9]
    if s:
        odmin = min(p["F"][3] for p in s)
        pool = [p for p in s if p["F"][3] <= odmin + 0.25]
        sel["slim"] = min(pool, key=lambda p: p["F"][2])
    return sel


CONT = ["w_frac", "t_m_mm", "t_m2_frac", "t_cu_mm", "b_mm", "yc_frac", "leg_frac", "R_coil_log", "L_w_mm", "K_a_log",
        "preload_N", "ball_d_mm", "flange_t_mm", "flange_frac"]


def refine(p: Dict, iters: int = 30, lam: int = 6, seed: int = 3, pool=None, fix: Optional[Dict[str, float]] = None) -> Dict:
    """(1 + lambda)-ES on the continuous genes with Deb's rules; objective typical loss, tie-break worst-case loss."""
    rng = np.random.default_rng(seed)
    x0 = np.array(p["x"], float)
    if fix:
        for k, v in fix.items():
            x0[O.NAMES.index(k)] = v
    best = O.score(x0)
    idx = [O.NAMES.index(n) for n in CONT]
    span = np.array([O.HI[i] - O.LO[i] for i in idx])
    sigma = 0.08
    hist = [{"it": 0, "typical_W": best["F"][2], "V": best["V"]}]

    def better(a, b):
        if a["V"] <= 0 < b["V"]:
            return True
        if a["V"] > 0 and b["V"] > 0:
            return a["V"] < b["V"]
        if a["V"] > 0:
            return False
        return (a["F"][2], a["F"][1]) < (b["F"][2], b["F"][1])
    for it in range(1, iters + 1):
        xs = []
        for _ in range(lam):
            x = np.array(best["x"], float)
            x[idx] = np.clip(x[idx] + rng.normal(0, sigma, len(idx)) * span, [O.LO[i] for i in idx],
                             [O.HI[i] - 1e-12 for i in idx])
            xs.append(x)
        res = pool.map(O.score, xs) if pool is not None else [O.score(x) for x in xs]
        cand = best
        for r in res:
            if r.get("ok") and better(r, cand):
                cand = r
        if cand is not best:
            best = cand
            sigma = min(0.2, sigma * 1.3)
        else:
            sigma = max(0.005, sigma * 0.7)
        hist.append({"it": it, "typical_W": best["F"][2], "V": best["V"], "sigma": sigma})
    return {"best": best, "history": hist}


def reach_per_watt(points: List[Dict]) -> Dict:
    fz = feasible(points)
    if not fz:
        return {}
    best = max(fz, key=lambda p: -p["F"][0] / p["F"][2])
    by_bin = {}
    for lo in np.arange(1.0, 2.0, 0.1):
        b = [p for p in fz if lo <= -p["F"][0] < lo + 0.1 and p["F"][3] <= 24.0 + 1e-9]
        if b:
            q = min(b, key=lambda p: p["F"][2])
            by_bin[f"{lo:.1f}-{lo + 0.1:.1f}"] = {"reach_mm": -q["F"][0], "typical_W": q["F"][2], "screen_W": q["F"][1],
                                                  "od_mm": q["F"][3], "length_mm": q["F"][4],
                                                  "reach_per_W_mm": -q["F"][0] / q["F"][2]}
    return {"best": {"reach_mm": -best["F"][0], "typical_W": best["F"][2], "od_mm": best["F"][3],
                     "reach_per_W_mm": -best["F"][0] / best["F"][2]}, "best_by_reach_bin_od_le_24": by_bin,
            "label": "CALCULATION (typical-duty loss, weakest point x 0.7)"}


def max_reach_by_od(points: List[Dict]) -> Dict:
    fz = feasible(points)
    out = {}
    for od in (20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0):
        b = [p for p in fz if p["F"][3] <= od + 1e-9]
        if b:
            q = max(b, key=lambda p: (-p["F"][0], -p["F"][2]))
            out[f"{od:g}"] = {"reach_mm": -q["F"][0], "typical_W": q["F"][2], "screen_W": q["F"][1], "od_mm": q["F"][3],
                              "length_mm": q["F"][4]}
    return out
