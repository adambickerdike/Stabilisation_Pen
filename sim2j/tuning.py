r"""Rules fixed on tuning writers (100-103) and tuning seeds (300+) before any test run (SIMULATION).

Guard rule (tune_guard): the frequency-runaway guard variants of akf_online.GuardParams are compared on tuning
writers 100-103, seed 300, ET at 6/8/10 Hz x 0.3/1/2 mm (v2 writers, "return library", Rev J pen, H1 hand), with
the rules written here before the runs:
  R1  false correction on tremor-free writing (ink moved against the device-off pen run with the same seed, i.e. the
      same sensor and Hall noise) <= 25 um (project rule, AC-E01-09 / docs/revJ_plan.md);
  R2  no worse than the device-off pen at 0.3 mm (mean ink-error ratio <= 1.02);
  choose the variant with the lowest mean ink-error ratio at 1-2 mm among those that pass R1 and R2; if none
  passes, the variant with the smallest false correction.
Variants: G0 no guard (the Rev H re-tuned AKF alone), G3 re-seed + frequency lock + ai2's detector gate on the
authority (G1 re-seed only and G2 re-seed + lock were run on the round-1 assembly: both moved tremor-free writing by
about 0.2 mm), G4 as G3 with a stricter line (r_on 8, r_off 4), G5 as G4 with 1 s to open.  The detector sees the page
samples taken while the ball is on the paper (firmware).
The chosen variant is written to results/sim2j/rules.json with the time of the freeze.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, replace
from typing import Dict, List

import numpy as np

from . import RESULTS, TUNE_WRITERS
from . import et as ET
from .akf_online import DetParams, GuardParams

GUARD_VARIANTS = {
    "G0_no_guard": GuardParams(on=False, use_det_gate=False, lock_hz=0.0),
    "G1_reseed": GuardParams(on=True, use_det_gate=False, lock_hz=0.0),
    "G2_reseed_lock": GuardParams(on=True, use_det_gate=False, lock_hz=1.0),
    "G3_reseed_lock_gate": GuardParams(on=True, use_det_gate=True, lock_hz=1.0),
    "G4_gate_r8": GuardParams(on=True, use_det_gate=True, lock_hz=1.0),
    "G5_gate_r8_t1": GuardParams(on=True, use_det_gate=True, lock_hz=1.0),
}
# the detector with each variant: ai2's defaults (r_on 5, r_off 2.5, t_on 0.5 s), or a stricter line (r_on 8, r_off 4;
# G5 also 1 s to open) - added after a tuning run in which ai2's detector opened on tremor-free v2 writing (the clean
# writing's own peak ratios reach 4-6 on the v2 and up to 14 on the v1 writers' intended paths: the r_on = 5 margin is thin)
DET_VARIANTS = {
    "G4_gate_r8": DetParams(r_on=8.0, r_off=4.0),
    "G5_gate_r8_t1": DetParams(r_on=8.0, r_off=4.0, t_on=1.0),
}
TUNE_SET = ("G0_no_guard", "G3_reseed_lock_gate", "G4_gate_r8", "G5_gate_r8_t1")


def det_for(v: str) -> DetParams:
    return DET_VARIANTS.get(v, DetParams())


def tune_guard(writers=TUNE_WRITERS, seeds=(300,), f0s=(6.0, 8.0, 10.0), amps=(0.3e-3, 1.0e-3, 2.0e-3), log=print,
               cache_path=None, variants=TUNE_SET) -> Dict:
    pens = ET.PenModels()
    rows: List[Dict] = []
    t0 = time.time()
    for w in writers:
        su = ET.WriterSetup(w, pens, log=log)
        for vname in variants:
            g = GUARD_VARIANTS[vname]
            m = ET.run_case(su, "nose", 0.0, 0.0, 300, ref_none=su.clean, guard=g, det=det_for(vname))
            m["variant"] = vname
            m["kind"] = "clean"
            m["moved_um"] = m["moved_vs_clean_um"]
            rows.append(m)
            log(f"[guard] w{w} {vname} clean moved {m['moved_um']:.1f} um")
        for seed in seeds:
            for f0 in f0s:
                for amp in amps:
                    rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
                    r_none = rn.pop("_r")
                    rn["variant"] = "none"
                    rn["kind"] = "tremor"
                    rows.append(rn)
                    for vname in variants:
                        g = GUARD_VARIANTS[vname]
                        m = ET.run_case(su, "nose", f0, amp, seed, ref_none=r_none, guard=g, det=det_for(vname))
                        m["variant"] = vname
                        m["kind"] = "tremor"
                        m["ratio"] = m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)
                        rows.append(m)
                    log(f"[guard] w{w} s{seed} {f0:g} Hz {amp * 1e3:g} mm: none {rn['ink_err_um']:.0f} um; " +
                        ", ".join(f"{r['variant']} {r['ratio']:.3f}" for r in rows[-len(variants):]))
        if cache_path:
            json.dump(rows, open(cache_path, "w"), default=float)
    summ = {}
    for vname in variants:
        cl = [r["moved_um"] for r in rows if r.get("variant") == vname and r["kind"] == "clean"]
        r03 = [r["ratio"] for r in rows if r.get("variant") == vname and r["kind"] == "tremor" and abs(r["amp_mm"] - 0.3) < 1e-6]
        r12 = [r["ratio"] for r in rows if r.get("variant") == vname and r["kind"] == "tremor" and r["amp_mm"] > 0.5]
        summ[vname] = {"false_correction_um_mean": float(np.mean(cl)), "false_correction_um_max": float(np.max(cl)),
                       "ratio_0p3": float(np.mean(r03)), "ratio_1_2mm": float(np.mean(r12)),
                       "R1": bool(np.mean(cl) <= 25.0), "R2": bool(np.mean(r03) <= 1.02)}
    passing = [v for v in summ if summ[v]["R1"] and summ[v]["R2"]]
    if passing:
        chosen = min(passing, key=lambda v: summ[v]["ratio_1_2mm"])
    else:
        chosen = min(summ, key=lambda v: summ[v]["false_correction_um_mean"])
    return {"rows": rows, "summary": summ, "chosen": chosen, "chosen_params": asdict(GUARD_VARIANTS[chosen]),
            "chosen_det_params": asdict(det_for(chosen)),
            "rules": __doc__, "elapsed_s": time.time() - t0}


RL_SELECTION_RULE = """RL checkpoint selection (fixed before any test run): each saved PPO checkpoint is run deterministically on the
tuning writers 100-103 with seeds 300-303 (ET 6/8/10 Hz x 0.3/1/2 mm, one seed per writer and cell, and the tremor-free
writing of every writer); a checkpoint passes when (S1) its false correction on tremor-free writing is <= 25 um (mean
and every case <= 50 um) and (S2) its mean ink-error ratio to the model-based tracker at 0.3 mm is <= 1.00; among the
passing checkpoints the one with the lowest mean ink error at 1-2 mm is taken to the test; if none passes, the RL policy
is not adopted and is reported as such (the model-based tracker stays)."""

TEST_PROTOCOL = """Test (after the freeze): writers 0-5 (v2), seeds 200-203 (two per writer and cell, rotating), ET 4/8/12 Hz x
0.3/1/2 mm, controllers none, nose, nose_wheel, nose_wheel_ec, oracle, rl; nose_noguard at 1 mm; tremor-free writing of every
writer with every controller (false correction against the device-off run with the same seed)."""


def freeze(result: Dict, path: str = None, extra: Dict = None) -> Dict:
    """Write the chosen guard and the selection rules to results/sim2j/rules.json with the time of the freeze."""
    from stabpen import provenance as PV
    from . import revj as RJ
    path = path or os.path.join(RESULTS, "rules.json")
    summ = result["summary"]
    out = {
        "stabpen.provenance": PV.metadata("SIMULATION (rules fixed on the tuning writers 100-103 and seed 300 before any "
                                          "test run; sim2 ranks concepts, COU-1)", seeds=[300],
                                          extra={"pen_source": RJ.lead()["meta"] if RJ.lead_available() else "round1"}),
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "guard": {"variant": result["chosen"], "params": result["chosen_params"],
                  "det_params": result.get("chosen_det_params", asdict(DetParams())), "summary": summ,
                  "rule_text": __doc__, "elapsed_s": result.get("elapsed_s")},
        "rl_selection_rule": RL_SELECTION_RULE,
        "test_protocol": TEST_PROTOCOL,
    }
    if extra:
        out.update(extra)
    PV.write_json(path, out)
    return out
