r"""Autowrite settings chosen on TUNING data only (writers 100-103, seeds 300-303).  SIMULATION (HW1 via autowrite.py).

Rules (written before any test run; applied mechanically, in this order; each stage keeps the earlier choices):
  T1 observer bandwidth obs_hz in {10, 25, 50, 100} Hz: the lowest mean ink error over the tuning cases.
  T2 progress filter prog_hz in {0.4, 0.8, 1.6} Hz: the lowest mean ink error.
  T3 prediction lead_extra in {0, 1, 2} ms: the lowest mean ink error.
  T4 reach margin in {0.5, 1.0, 1.5} mm (kept free for tremor; plan reach = travel - margin): the smallest margin with
     the nose at its travel limit <= 1 % of the time in every tuning case with 1 mm tremor, and no plan failure.
  (In every rule a setting with a failed plan or a diverged run in any case is not chosen.)
  T5 sweep speed factor in {0.8, 1.0, 1.25} (x planner.line_speed): the fastest with letters read >= the clean-target
     ceiling - 0.02 on average and mean ink error <= 1.25 x that of factor 1.0.
Tuning cases: 4 writers x 2 seeds x {no tremor; 1 mm at 4, 8, 12 Hz}, x-height 2.5 mm, the recommended design.
Nothing here uses test writers 0-5 or test seeds 200-203.
"""
from __future__ import annotations

import math
import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional

import numpy as np

from . import TUNE_SEEDS, TUNE_WRITERS
from . import autowrite as AW

CONDS = [(8.0, 0.0), (4.0, 1.0e-3), (8.0, 1.0e-3), (12.0, 1.0e-3)]
GRID = {"obs_hz": (10.0, 25.0, 50.0, 100.0), "prog_hz": (0.4, 0.8, 1.6), "lead_extra": (0.0, 1e-3, 2e-3),
        "reach_margin": (0.5e-3, 1.0e-3, 1.5e-3), "speed": (0.8, 1.0, 1.25)}


def sensor_seed(w: int, seed: int, f0: float, amp: float) -> int:
    return 80_000_000 + 100_000 * (w % 1000) + 1000 * (seed % 1000) + 10 * int(round(f0)) + int(round(amp * 1e4))


def cases(design: AW.NoseDesign, st: AW.AWSettings, h_mm: float = 2.5, writers=TUNE_WRITERS, seeds=TUNE_SEEDS[:2],
          conds=CONDS, progress: Optional[Callable] = None) -> List[Dict]:
    rows = []
    for w in writers:
        for s in seeds:
            for f0, amp in conds:
                c = AW.build(w, s, h_mm, f0, amp, design, st)
                if not c.plan.ok:
                    rows.append({"plan_ok": False, "w": w, "seed": s, "f0": f0, "amp_mm": amp * 1e3})
                    continue
                m = AW.run(c, sensor_seed(w, s, f0, amp))
                rows.append(m)
                if progress:
                    progress(w, s, f0, amp, m.get("ink_err_um"))
    return rows


def _finite(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


def agg(rows: List[Dict]) -> Dict:
    """Means over the cases; a case whose plan failed or whose run diverged (no finite ink error, or > 5 mm) counts as a
    failure, and any failure makes the mean ink error infinite (the rules then reject that setting)."""
    ok = [r for r in rows if r.get("plan_ok") and _finite(r.get("ink_err_um")) and r["ink_err_um"] < 5000.0]
    diverged = sum(1 for r in rows if r.get("plan_ok")) - len(ok)
    trem = [r for r in ok if r["amp_mm"] > 0]
    return {"n": len(rows), "plan_fail": len(rows) - len(ok), "diverged": diverged,
            "ink_err_um": float(np.mean([r["ink_err_um"] for r in ok])) if ok and len(ok) == len(rows) else float("inf"),
            "letters_read": float(np.mean([r["letters_read"] for r in ok])) if ok else 0.0,
            "target_letters_read": float(np.mean([r["target_letters_read"] for r in ok])) if ok else 0.0,
            "at_limit_max": float(max([r["at_travel_limit"] for r in trem], default=0.0)),
            "P_coil_W": float(np.mean([r["P_coil_W"] for r in ok])) if ok else float("nan"),
            "letters_per_s": float(np.mean([r["letters_per_s"] for r in ok])) if ok else float("nan")}


def tune(design: AW.NoseDesign, progress: Optional[Callable] = None, quick: bool = False) -> Dict:
    st = AW.AWSettings()
    log = {}
    writers = TUNE_WRITERS[:2] if quick else TUNE_WRITERS
    seeds = TUNE_SEEDS[:1] if quick else TUNE_SEEDS[:2]
    conds = CONDS[:2] if quick else CONDS

    def evaluate(stx):
        return agg(cases(design, stx, writers=writers, seeds=seeds, conds=conds))
    # T1-T3: lowest ink error
    for key in ("obs_hz", "prog_hz", "lead_extra"):
        res = {}
        for val in GRID[key]:
            t0 = time.time()
            res[val] = evaluate(replace(st, **{key: val}))
            if progress:
                progress(key, val, res[val]["ink_err_um"], time.time() - t0)
        best = min(res, key=lambda v: (res[v]["plan_fail"], res[v]["ink_err_um"]))
        st = replace(st, **{key: best})
        log[key] = {"grid": {str(k): v for k, v in res.items()}, "chosen": best}
    # T4: smallest reach margin with <= 1 % at the limit and no plan failure
    res = {}
    for val in GRID["reach_margin"]:
        res[val] = evaluate(replace(st, reach_margin=val))
        if progress:
            progress("reach_margin", val, res[val]["at_limit_max"], 0.0)
    ok = [v for v in GRID["reach_margin"] if res[v]["plan_fail"] == 0 and res[v]["at_limit_max"] <= 0.01]
    chosen = min(ok) if ok else max(GRID["reach_margin"])
    st = replace(st, reach_margin=chosen)
    log["reach_margin"] = {"grid": {str(k): v for k, v in res.items()}, "chosen": chosen, "rule_met": bool(ok)}
    # T5: fastest sweep within the reading and ink-error rules
    res = {}
    for val in GRID["speed"]:
        res[val] = evaluate(replace(st, speed=val))
        if progress:
            progress("speed", val, res[val]["ink_err_um"], 0.0)
    base = res[1.0]["ink_err_um"]
    ok = [v for v in GRID["speed"] if res[v]["plan_fail"] == 0 and res[v]["letters_read"] >= res[v]["target_letters_read"] - 0.02
          and res[v]["ink_err_um"] <= 1.25 * base]
    chosen = max(ok) if ok else 1.0
    st = replace(st, speed=chosen)
    log["speed"] = {"grid": {str(k): v for k, v in res.items()}, "chosen": chosen}
    return {"settings": {k: getattr(st, k) for k in ("reach_margin", "obs_hz", "prog_hz", "lead_extra", "speed")},
            "log": log, "writers": list(writers), "seeds": list(seeds), "conds": [list(c) for c in conds],
            "label": "SIM (HW1 via nose2/autowrite.py; tuning writers and seeds only; rules in nose2/tuning.py)"}
