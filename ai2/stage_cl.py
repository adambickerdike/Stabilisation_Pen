"""Stage cl: closed-loop check (model HW1) of the task 2 and 3 candidates on TUNING data, before the test.

Candidates (all causal, lag 0, Rev H nose +-3 mm): the model-based causal stack (stage D2b's gated tracker), the
learned estimators (stage learn; ctx uses the detector's 20 s calibration on a separate recording), the RL arbiter
and the residual RL policy (stage rl).  Tuning writers 100-103, seeds 300 and 301 (both count), the D2 conditions.
Rules (fixed before this stage ran; the D2 rules R1-R4 against the Rev H tracker on the same runs):
  R1 tremor-free false correction <= tracker + 2 um; R2 0.3 mm ink <= 1.02 x tracker per frequency;
  R3 letters read >= tracker - 0.01 per condition; R4 coverage >= tracker - 0.01 per condition.
  Also reported: REQ-ML-001's absolute line, false correction <= 25 um RMS on tremor-free writing.
Choice: among candidates passing R1-R4, the lowest mean ink error at 1-2 mm; a learned or RL candidate is adopted only
if it passes and beats the model-based stack's J by >= 2 % (else the simpler model-based stack stays).

Evidence status: SIMULATION.
"""
from __future__ import annotations

import time
from typing import Dict, List

import numpy as np

from . import AMPS, F0S, TUNE_SEEDS, TUNE_WRITERS, ensure_paths
from . import candidates as CA
from . import common as C
from . import delayed as DL
from . import stage_learn_data as SLD
from . import tuning as TU

ensure_paths()
from aiprior import core as CO  # noqa: E402
from aiprior import study as SD  # noqa: E402


def scenario_rows(sc, mp: Dict, cands: Dict, ctx) -> Dict:
    """Metrics of the tracker and every candidate on one scenario (lag 0, Rev H nose)."""
    DL.OUT_EVERY = 1
    est = DL.estimates(sc, CA.base_cfg(mp), lags=CA.LAGS_CL)
    obs = DL.observables(sc, est)
    X, tk, mb = CA.arrays(sc, mp)
    lam = np.zeros(len(sc.streams.tick_t))
    out = {}
    rt = CO.run_cmd(sc, -sc.dh)
    m = SD.metrics(sc, rt, travel=False)
    m["coverage"] = DL.coverage(sc, rt)
    if sc.amp == 0:
        m["false_correction_um"] = DL.ink_timeline_error(sc, rt, lam, sc.neutral)
    out["tracker"] = m
    for name, q in CA.commands(sc, est, mp, cands, X, tk, mb, ctx).items():
        r = DL.run(sc, q, sc.pen)
        mm = DL.evaluate_run(sc, r, sc.pen, q, lam, obs)
        if sc.amp == 0:
            mm["false_correction_um"] = DL.ink_timeline_error(sc, r, lam, sc.neutral)
        out[name] = mm
    return out


def job(j: Dict) -> Dict:
    t0 = time.time()
    mp = j["mp"]
    cands = CA.load(j["quick"])
    wr = CO.Writer(j["writer"])
    rows = []
    for seed in j["seeds"]:
        for f0, amp in TU.conditions():
            sc = TU.scenario(wr, f0, amp, seed)
            ctx = CA.calibration(wr, f0, amp, seed, mp["det"]) if "ctx" in cands["learned"] else None
            v = scenario_rows(sc, mp, cands, ctx)
            rows.append({"writer": wr.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "v": v, "ctx": ctx})
            C.log(f"[cl] writer {wr.w} seed {seed} {f0:g} Hz {amp * 1e3:g} mm: " +
                  ", ".join(f"{k} {vv['ink_err_um']:.0f}" for k, vv in v.items()))
    return {"writer": wr.w, "rows": rows, "elapsed_s": time.time() - t0}


def run(quick: bool, workers: int):
    mp = SLD.model_params(quick)
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    seeds = TUNE_SEEDS[:1] if quick else TUNE_SEEDS
    outs = C.jmap(job, [{"writer": w, "seeds": list(seeds), "mp": mp, "quick": quick} for w in writers], workers)
    sel = TU.select_d2(outs, [])
    table = sel["table"]
    names = [k for k in table]
    passing = [k for k in names if table[k]["passes"]]
    for k in names:
        table[k]["fc_le_25um"] = bool(table[k]["fc_um"] <= 25.0)
    J0 = table.get("gated", {}).get("J_ink_1_2mm_um", float("inf"))
    best = min(passing, key=lambda k: table[k]["J_ink_1_2mm_um"]) if passing else None
    adopted = best if (best == "gated" or (best and table[best]["J_ink_1_2mm_um"] <= 0.98 * J0)) else ("gated" if "gated" in passing else None)
    out = {"outs": outs, "table": table, "passing": passing, "best_passing": best, "adopted": adopted,
           "rules": "R1-R4 of D2 vs the Rev H tracker (seeds 300 and 301 pooled); adopt a learned/RL candidate only if it "
                    "passes and beats the model-based stack's J by >= 2 %", "model_params": mp, "writers": list(writers),
           "seeds": list(seeds)}
    C.save("cl", out, quick)
    for k in names:
        t = table[k]
        C.log(f"[cl] {k}: J {t['J_ink_1_2mm_um']:.0f} (tracker {t['tracker_J_ink_1_2mm_um']:.0f}) fc {t['fc_um']:.1f} "
              f"(tracker {t['tracker_fc_um']:.1f}) 0.3 mm {t['ink_0p3mm_um']:.0f} letters {t['letters_1_2mm']:.3f} "
              f"R {int(t['R1'])}{int(t['R2'])}{int(t['R3'])}{int(t['R4'])}")
    C.log(f"[cl] passing {passing}; adopted {adopted}")
    return out
