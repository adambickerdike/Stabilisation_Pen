"""Stage shared (task 6): arbitration for guided practice (copying a known text): fixed partial / full guidance
against assistance-as-needed (AAN) gain schedules, on the handwriting study's dysgraphia-like learners (model HW1).

Evidence status: SIMULATION (passive hand, no learning).  Rule S1 (tuning learners 100-103, seeds 300-301): among the
AAN settings, the lowest mean device share whose distance to the target is within 5 % of fixed partial guidance's.
"""
from __future__ import annotations

from itertools import product
from typing import Dict, List

import numpy as np

from . import TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, ensure_paths
from . import common as C
from . import shared as SH

ensure_paths()


def _agg(outs: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    names = list(rows[0]["res"].keys()) if rows else []
    keys = ["target_err_um", "letters_read_ok", "words_app", "device_share", "device_disp_rms_mm", "nose_q_rms_mm",
            "gain_mean", "gain_on_malformed", "gain_on_wellformed", "dtw_um"]
    return {nm: {k: float(np.mean([r["res"][nm][k] for r in rows if r["res"][nm].get(k) is not None]))
                 for k in keys if any(r["res"][nm].get(k) is not None for r in rows)} | {"n": len(rows)} for nm in names}


def run(quick: bool, workers: int):
    # --- tuning: AAN grid on tuning learners
    grid = [{"kind": "aan", "f": f, "kappa": k, "e_tol": 0.10, "g_max": 1.0, "g0": 0.5} for f, k in product((0.5, 0.8), (2.0, 4.0, 8.0))]
    saved = dict(SH.POLICIES)
    SH.POLICIES.clear()
    SH.POLICIES.update({"none": None, "fixed_partial": saved["fixed_partial"]})
    for i, g in enumerate(grid):
        SH.POLICIES[f"aan_{i}"] = g
    tw = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    ts = TUNE_SEEDS[:1] if quick else TUNE_SEEDS
    tune = _agg(C.jmap(SH.job, [{"writer": w, "seeds": list(ts)} for w in tw], workers))
    ref = tune["fixed_partial"]["target_err_um"]
    ok = [i for i in range(len(grid)) if tune[f"aan_{i}"]["target_err_um"] <= 1.05 * ref]
    best = min(ok, key=lambda i: tune[f"aan_{i}"]["device_share"]) if ok else \
        min(range(len(grid)), key=lambda i: tune[f"aan_{i}"]["target_err_um"])
    chosen = grid[best]
    C.log(f"[shared] tuning: fixed partial {ref:.0f} um; chosen AAN {chosen} ({tune[f'aan_{best}']})")
    # --- test
    SH.POLICIES.clear()
    SH.POLICIES.update({"none": None, "fixed_partial": saved["fixed_partial"], "fixed_full": saved["fixed_full"],
                        "aan": chosen, "aan_fade": dict(chosen, f=max(0.3, chosen["f"] - 0.3))})
    ww = TEST_WRITERS[:2] if quick else TEST_WRITERS
    ss = TEST_SEEDS[:1] if quick else TEST_SEEDS
    outs = C.jmap(SH.job, [{"writer": w, "seeds": list(ss)} for w in ww], workers)
    test = _agg(outs)
    SH.POLICIES.clear(); SH.POLICIES.update(saved)
    out = {"tuning": tune, "grid": grid, "rule": "S1: lowest device share with target distance <= 1.05 x fixed partial",
           "chosen": chosen, "chosen_passes": bool(ok), "test": test, "writers": list(ww), "seeds": list(ss)}
    C.save("shared", out, quick)
    for k, v in test.items():
        C.log(f"[shared] {k}: target {v.get('target_err_um', float('nan')):.0f} um letters {v.get('letters_read_ok', float('nan')):.3f} "
              f"device share {v.get('device_share', float('nan')):.3f} gain {v.get('gain_mean', float('nan')):.2f}")
    return out
