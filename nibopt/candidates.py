r"""Recommended candidates from the pooled feasible points, local refinement, and the targeted questions (CALCULATION).

Selection (feasible points of every run, fill fixed at study B / K's 0.55 for the recommendations so that no
recommended design rests on the higher fills, which are an ASSUMPTION; length <= 160 mm for the first three, an
ASSUMPTION: at most 10 mm over REQ-RVK-001's 150 mm, well inside the Rev J envelope's 175 mm):
  reach_first  the largest usable radius in a body of 24 mm or less; ties (within 0.03 mm) by the worst-case loss
  balanced     usable radius >= 1.5 mm (DEC-050's option, study F's perfect-knowledge line) in <= 24 mm with the lowest
               typical-duty loss; if none is feasible, the design with the most reach per typical watt
  slim         the smallest body diameter that keeps +-1.0 mm (DEC-060) with every constraint met; ties (within
               0.25 mm of diameter) by typical loss
  k_envelope   the largest usable radius inside Rev K's envelope as REQ-RVK-001 states it (<= 24 mm across,
               <= 150 mm long); ties (within 0.03 mm) by the worst-case loss
Refinement: the categorical genes, reach and body diameter fixed, a (1 + lambda) evolution strategy with Deb's rules on
the continuous genes minimises the typical-duty loss (the worst-case loss as the tie-break), the candidate's length
cap added as a constraint.
Targeted runs: 'reach2' fixes the usable radius at 2.0 mm and lets the body grow to 34 mm (objectives: diameter and
typical loss); 'reach2_small' repeats it between 24 and 29.8 mm to find the smallest body that works; 'reach15' fixes
1.5 mm in <= 24 mm (objectives: typical and worst-case loss).
"""
from __future__ import annotations

import functools
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


LENGTH_CAP_MM = 160.0          # ASSUMPTION (see the module note)
K_ENVELOPE = (24.0, 150.0)     # REQ-RVK-001: <= 24 mm across, <= 150 mm long


def select(points: List[Dict], length_cap: float = LENGTH_CAP_MM) -> Dict[str, Dict]:
    fz = feasible(points, fill055=True)
    fzc = [p for p in fz if p["F"][4] <= length_cap + 1e-9]
    sel = {}
    f24 = [p for p in fzc if p["F"][3] <= 24.0 + 1e-9]
    if f24:
        rmax = max(-p["F"][0] for p in f24)
        pool = [p for p in f24 if -p["F"][0] >= rmax - 0.03]
        sel["reach_first"] = min(pool, key=lambda p: p["F"][1])
        b = [p for p in f24 if -p["F"][0] >= 1.5 - 1e-9]
        if b:
            sel["balanced"] = min(b, key=lambda p: p["F"][2])
        else:
            sel["balanced"] = max(f24, key=lambda p: -p["F"][0] / p["F"][2])
    s = [p for p in fzc if -p["F"][0] >= 1.0 - 1e-9]
    if s:
        odmin = min(p["F"][3] for p in s)
        pool = [p for p in s if p["F"][3] <= odmin + 0.25]
        sel["slim"] = min(pool, key=lambda p: p["F"][2])
    k = [p for p in fz if p["F"][3] <= K_ENVELOPE[0] + 1e-9 and p["F"][4] <= K_ENVELOPE[1] + 1e-9]
    if k:
        rmax = max(-p["F"][0] for p in k)
        pool = [p for p in k if -p["F"][0] >= rmax - 0.03]
        sel["k_envelope"] = min(pool, key=lambda p: p["F"][1])
    return sel


def length_cap_of(name: str) -> float:
    return K_ENVELOPE[1] if name == "k_envelope" else LENGTH_CAP_MM


def score_capped(x, length_max: Optional[float] = None) -> Dict:
    """optimise.score with a length cap added to the violation (the same scale as the 175 mm limit)."""
    r = O.score(x)
    if length_max is not None and r.get("ok"):
        over = max(0.0, r["F"][4] - length_max)
        if over > 0:
            r["V"] = r["V"] + over / O.SCALES["length"]
            r["feasible"] = False
        r.setdefault("constraints", {})["length_cap"] = float(length_max - r["F"][4])
    return r


CONT = ["w_frac", "t_m_mm", "t_m2_frac", "t_cu_mm", "b_mm", "yc_frac", "leg_frac", "R_coil_log", "L_w_mm", "K_a_log",
        "preload_N", "ball_d_mm", "flange_t_mm", "flange_frac"]


def refine(p: Dict, iters: int = 30, lam: int = 6, seed: int = 3, pool=None, fix: Optional[Dict[str, float]] = None,
           length_max: Optional[float] = None) -> Dict:
    """(1 + lambda)-ES on the continuous genes with Deb's rules; objective typical loss, tie-break worst-case loss;
    length_max adds a length cap to the constraints."""
    rng = np.random.default_rng(seed)
    x0 = np.array(p["x"], float)
    if fix:
        for k, v in fix.items():
            x0[O.NAMES.index(k)] = v
    fn = functools.partial(score_capped, length_max=length_max)
    best = fn(x0)
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
        res = pool.map(fn, xs) if pool is not None else [fn(x) for x in xs]
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


def reach_per_watt(points: List[Dict], fill055: bool = False, length_cap: Optional[float] = None) -> Dict:
    fz = feasible(points, fill055=fill055)
    if length_cap is not None:
        fz = [p for p in fz if p["F"][4] <= length_cap + 1e-9]
    if not fz:
        return {}
    best = max(fz, key=lambda p: -p["F"][0] / p["F"][2])
    by_bin = {}
    for lo in np.arange(1.0, 2.0, 0.1):
        b = [p for p in fz if lo - 1e-9 <= -p["F"][0] < lo + 0.1 - 1e-9 and p["F"][3] <= 24.0 + 1e-9]
        if b:
            q = min(b, key=lambda p: p["F"][2])
            by_bin[f"{lo:.1f}-{lo + 0.1:.1f}"] = {"reach_mm": -q["F"][0], "typical_W": q["F"][2], "screen_W": q["F"][1],
                                                  "od_mm": q["F"][3], "length_mm": q["F"][4],
                                                  "reach_per_W_mm": -q["F"][0] / q["F"][2]}
    return {"best": {"reach_mm": -best["F"][0], "typical_W": best["F"][2], "od_mm": best["F"][3],
                     "reach_per_W_mm": -best["F"][0] / best["F"][2]}, "best_by_reach_bin_od_le_24": by_bin,
            "fill_0.55_only": fill055, "length_cap_mm": length_cap,
            "label": "CALCULATION (typical-duty loss, weakest point x 0.7)"}


def max_reach_by_od(points: List[Dict], fill055: bool = False, length_cap: Optional[float] = None) -> Dict:
    fz = feasible(points, fill055=fill055)
    if length_cap is not None:
        fz = [p for p in fz if p["F"][4] <= length_cap + 1e-9]
    out = {}
    for od in (20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 28.0, 30.0, 32.0, 34.0):
        b = [p for p in fz if p["F"][3] <= od + 1e-9]
        if b:
            q = max(b, key=lambda p: (round(-p["F"][0], 4), -p["F"][2]))
            out[f"{od:g}"] = {"reach_mm": -q["F"][0], "typical_W": q["F"][2], "screen_W": q["F"][1], "od_mm": q["F"][3],
                              "length_mm": q["F"][4]}
    return out


def length_limits(points: List[Dict]) -> Dict:
    """What the pen's length buys in a body of 24 mm or less (fill 0.55): the shortest pen for each reach, the largest
    reach and the lowest typical loss at each length cap (CALC)."""
    fz = [p for p in feasible(points, fill055=True) if p["F"][3] <= 24.0 + 1e-9]
    out = {"shortest_for_reach": {}, "at_length_cap": {}}
    for r in (1.0, 1.25, 1.5):
        b = [p for p in fz if -p["F"][0] >= r - 1e-9]
        if b:
            q = min(b, key=lambda p: p["F"][4])
            out["shortest_for_reach"][f"{r:g}"] = {"length_mm": q["F"][4], "typical_W": q["F"][2], "screen_W": q["F"][1],
                                                   "od_mm": q["F"][3], "reach_mm": -q["F"][0]}
    for cap in (145.2, 148.0, 150.0, 152.0, 155.0, 160.0):
        b = [p for p in fz if p["F"][4] <= cap + 1e-9]
        if not b:
            continue
        q = max(b, key=lambda p: (round(-p["F"][0], 4), -p["F"][2]))
        row = {"max_reach_mm": -q["F"][0], "its_typical_W": q["F"][2], "its_screen_W": q["F"][1]}
        for r in (1.0, 1.25, 1.5):
            c = [p for p in b if -p["F"][0] >= r - 1e-9]
            if c:
                qq = min(c, key=lambda p: p["F"][2])
                row[f"reach_{r:g}_min_typical_W"] = qq["F"][2]
                row[f"reach_{r:g}_its_screen_W"] = qq["F"][1]
        out["at_length_cap"][f"{cap:g}"] = row
    out["label"] = "CALCULATION (pooled feasible points, fill 0.55, body <= 24 mm)"
    return out
