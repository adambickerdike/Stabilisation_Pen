"""Every design choice of this study, on tuning data only (aiguide writers 100-103, seeds 300 (choice) and 301
(confirmation)), with its rule.  The rules below were written before any test writer (0-5) or test seed (200-203)
was run, and they are applied mechanically by `select_*`.

Stage T0 - the tracker the AI sits on (no AI).
  Candidates: the Rev H tracker (results/opt/inertial_tracker_revh.json) and the same filter with tremor-state process
  noise qt in {2e-9, 5e-9, 1e-8, 2e-8} m^2/s (harmonic qh = 0.3 qt), output gain g in {0.8, 1.0, 1.2} and oscillator
  damping time tau_decay 0.3 s; every other value as the Rev H set.
  Rule T0: the lowest mean ink error over 6/8/10 Hz x 1/2 mm, subject to
    (a) false correction on the tuning writers' tremor-free writing <= 30 um (the tracker study's glyph-writer bound),
    (b) at 0.3 mm, at every frequency: mean ink error <= 1.02 x the Rev H tracker's, and mean letters read >= the Rev H
        tracker's - 0.01.
  If no candidate passes, the Rev H tracker stays.

Stage T1 - A(i) the AI prior (fusion.context on the T0 tracker).
  Candidates: measurement form (0 intent-referenced, 1 tremor-referenced) x template noise sigma_t {100, 300} um; drop
  threshold 2000 um (60 ms), innovation gate off, template bias prior 500 um reset per letter.  (Reduced from a planned
  8-candidate list after the exploration on tuning writer 100, seed 300 showed that even the known-text template moved
  the ink error by at most 2 % on the Rev H tracker; the variant was not promising, so it was not polished further; T1 runs on tuning writers 100-101 only.)
  Rule T1: the lowest mean ink error over {ai_correct, ai_predicted} at 6/8/10 Hz x 1/2 mm, subject to
    (a) wrong letter at full confidence: total wrong letters introduced ("flips") <= 0 more than the T0 tracker's
        (flips are counted against the T0 tracker, so the rule is: no letter newly read as the wrong letter, in total),
    (b) at 0.3 mm (ai_predicted): mean ink error <= 1.02 x the T0 tracker's and letters read >= T0's - 0.01,
    (c) false correction (ai_predicted, tremor-free) <= T0's + 5 um.
  Adopt the prior only if its objective is at least 3 % below the T0 tracker's (ink error, 1-2 mm); otherwise report
  it as "no benefit" and stop tuning it.

Stage T2 - A(ii) AI guidance (guide.py on the T0 tracker).
  Amplitude gate (fixed by rule, not searched): a_lo = 1.2 x the largest per-run median of the T0 tracker's tremor
  amplitude state over the tuning runs at 0.3 mm and on tremor-free writing; a_hi = 2 a_lo.
  Candidates: g_max {0.5, 1.0} x capture {1.2, 2.0} mm (drop_d = 0.9 capture, 60 ms); dead band 0.1 mm; tau_b 0.25 s.
  Rule T2: the lowest mean ink error over {ai_correct, ai_predicted} at 6/8/10 Hz x 1/2 mm, subject to
    (a) wrong letter at full confidence: total flips <= 0 (against the T0 tracker),
    (b) mean letters read over {ai_correct, ai_predicted} at 1/2 mm >= the T0 tracker's (guidance must not make
        letters less readable),
    (c) at 0.3 mm (ai_predicted): mean ink error <= 1.02 x T0's and letters read >= T0's - 0.01,
    (d) false correction (ai_predicted, tremor-free) <= T0's + 5 um.
  Adopt only if the objective is at least 3 % below T0's; otherwise report "no benefit".

Clean copy (B): the Wiener smoother's settings (beta 2, half-width 2 Hz) were set once on tuning writer 100, seed 300
(8 Hz 1 mm, 6 Hz 2 mm, 10 Hz 2 mm), before any test run, and not searched.  The line threshold (peak-to-floor >= 3) and
the 2 x floor margin, and the running-median writing floor (in place of a power-law fit, which read a spectral knee
of writing as a line), were set, also before any test run, after a unit test showed that the first version cut writing
detail when there is no tremor line.  The T1/T2 tuning runs learnt the templates' style from the first version's clean
copy (tremor-laden tracks, where both versions apply the same kind of cleaning); the test runs use the final version.
A smoke run on test writer 0's tremor-free writing then showed the detector taking the writing's 3-4 Hz stroke rhythm
for a tremor line (a structural bug).  The fix was set on tuning writers 100-103 only (seed 300 and their tremor-free
writing): search band 4.5-13.5 Hz (tremor-free writing reads 1.0-1.5 there, 1-2 mm tremor 5-47), threshold 3 (twice the
largest tremor-free value), notch never below 3 Hz.
"""
from __future__ import annotations

import itertools
import time
from typing import Dict, List, Optional

import numpy as np

from . import F0S, TUNE_SEEDS, TUNE_WRITERS
from . import core as CO
from . import study as SD

ensure_amps = (0.3e-3, 1.0e-3, 2.0e-3)
HI_AMPS = (1.0e-3, 2.0e-3)
REL_TOL = 1.02
LETTER_TOL = 0.01
FC_BOUND_UM = 30.0
FC_EXTRA_UM = 5.0
MIN_GAIN = 0.03


def base_candidates() -> List[Optional[Dict]]:
    out: List[Optional[Dict]] = [None]
    for qt, g in itertools.product((2e-9, 5e-9, 1e-8, 2e-8), (0.8, 1.0, 1.2)):
        out.append({"qt": qt, "qh": 0.3 * qt, "g": g, "tau_decay": 0.3})
    return out


def prior_candidates() -> List[Dict]:
    return [{"tpl_mode": m, "sigma_t": s, "drop_um": d, "gate": 0.0, "tb0": 500e-6, "tb_letter": -1.0}
            for m, s, d in itertools.product((0.0, 1.0), (100e-6, 300e-6), (2000.0,))]


def guide_candidates(a_lo: float) -> List[Dict]:
    return [{"g_max": g, "capture": c, "drop_d": 0.9 * c, "drop_t": 0.06, "a_lo": a_lo, "a_hi": 2.0 * a_lo,
             "deadband": 0.1e-3, "tau_b": 0.25} for g, c in itertools.product((0.5, 1.0), (1.2e-3, 2.0e-3))]


def key(c: Optional[Dict]) -> str:
    if c is None:
        return "revh"
    return ",".join(f"{k}={v:g}" for k, v in sorted(c.items()) if isinstance(v, (int, float)))


# ------------------------------------------------------------------ jobs (one writer each)
def t0_job(job: Dict) -> Dict:
    wr = CO.Writer(job["writer"])
    cands = job["cands"]
    rows = []
    for seed in job["seeds"]:
        for f0 in F0S:
            for amp in ensure_amps:
                sc = CO.make_scenario(wr, f0, amp, seed)
                r = {"writer": wr.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "c": {}}
                for c in cands:
                    dh, info = SD.base_estimate(sc, c)
                    res = CO.run_cmd(sc, -dh)
                    m = SD.metrics(sc, res, travel=False)
                    r["c"][key(c)] = {"ink_err_um": m["ink_err_um"], "recognition": m["recognition"],
                                      "word_acc_app": m["word_acc_app"],
                                      "amp_median_um": float(np.median(info["amp"]) * 1e6)}
                rows.append(r)
    sc0 = CO.make_clean_scenario(wr)
    fc = {}
    rc = sc0.neutral
    for c in cands:
        dh, info = SD.base_estimate(sc0, c)
        res = CO.run_cmd(sc0, -dh)
        n = min(len(res.t), len(rc.t))
        m = (rc.contact[:n] > 0.5) & (res.contact[:n] > 0.5)
        fc[key(c)] = {"false_correction_um": float(np.sqrt(np.mean(np.sum((res.ink[:n] - rc.ink[:n])[m] ** 2, axis=1))) * 1e6),
                      "amp_median_um": float(np.median(info["amp"]) * 1e6)}
    return {"writer": wr.w, "rows": rows, "tremor_free": fc}


def ai_job(job: Dict) -> Dict:
    """T1 / T2: every candidate x case on the tuning scenarios of one writer, against the T0 tracker."""
    wr = CO.Writer(job["writer"])
    base = job["base"]
    stage = job["stage"]
    rows = []
    for seed in job["seeds"]:
        for f0 in F0S:
            for amp in job["amps"]:
                sc = CO.make_scenario(wr, f0, amp, seed)
                est0 = CO.calibrate_style(wr, f0, amp, seed)
                tpls = CO.templates(sc, est0)
                r = {"writer": wr.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "c": {}}
                for i, c in enumerate(job["cands"]):
                    cfg = {"base": base, "prior": c} if stage == "T1" else {"base": base, "guide": c}
                    pref = "prior_" if stage == "T1" else "guide_"
                    vs = [pref + k for k in job["cases"]]
                    ev = SD.evaluate(sc, cfg, (["tracker_rt"] if base is not None else ["tracker"]) + vs, est0=est0, tpls=tpls)
                    r["base"] = {k: ev["variants"]["tracker_rt" if base is not None else "tracker"][k]
                                 for k in ("ink_err_um", "recognition", "word_acc_app")}
                    r["c"][str(i)] = {v[len(pref):]: {k: ev["variants"][v].get(k) for k in
                                                      ("ink_err_um", "recognition", "word_acc_app", "flips", "broken", "fixed",
                                                       "ai_share", "device_share")} for v in vs}
                rows.append(r)
    fc = None
    if job.get("tremor_free"):
        fc = {}
        for i, c in enumerate(job["cands"]):
            cfg = {"base": base, "prior": c} if stage == "T1" else {"base": base, "guide": c}
            pref = "prior_" if stage == "T1" else "guide_"
            ev = SD.tremor_free(wr, cfg, [pref + "ai_predicted"])
            b = "tracker_rt" if base is not None else "tracker"
            fc[str(i)] = {"ai": ev["variants"][pref + "ai_predicted"]["false_correction_um"],
                          "base": ev["variants"][b]["false_correction_um"]}
    return {"writer": wr.w, "rows": rows, "tremor_free": fc}


# ------------------------------------------------------------------ selection rules
def _mean(rows, ck, key_, amps, sub=None):
    v = []
    for r in rows:
        if round(r["amp_mm"], 3) not in [round(a * 1e3, 3) for a in amps]:
            continue
        x = r["c"][ck]
        x = x if sub is None else x[sub]
        if x.get(key_) is not None:
            v.append(x[key_])
    return float(np.mean(v)) if v else float("nan")


def select_t0(outs: List[Dict], seeds=(300,)) -> Dict:
    rows = [r for o in outs for r in o["rows"] if r["seed"] in seeds]
    cands = list(rows[0]["c"].keys())
    ref = "revh"
    table = {}
    for ck in cands:
        J = _mean(rows, ck, "ink_err_um", HI_AMPS)
        fc = float(np.mean([o["tremor_free"][ck]["false_correction_um"] for o in outs]))
        ok_small = True
        per_f = {}
        for f0 in F0S:
            rr = [r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - 0.3) < 1e-9]
            e = float(np.mean([r["c"][ck]["ink_err_um"] for r in rr]))
            e0 = float(np.mean([r["c"][ref]["ink_err_um"] for r in rr]))
            l = float(np.mean([r["c"][ck]["recognition"] for r in rr]))
            l0 = float(np.mean([r["c"][ref]["recognition"] for r in rr]))
            per_f[f"{f0:g}Hz"] = {"ink": e, "ink_ref": e0, "letters": l, "letters_ref": l0}
            if e > REL_TOL * e0 or l < l0 - LETTER_TOL:
                ok_small = False
        table[ck] = {"J_ink_1_2mm_um": J, "false_correction_um": fc, "small_tremor_ok": ok_small, "fc_ok": fc <= FC_BOUND_UM,
                     "small_tremor": per_f, "words_1_2mm": _mean(rows, ck, "word_acc_app", HI_AMPS),
                     "letters_1_2mm": _mean(rows, ck, "recognition", HI_AMPS)}
    ok = [ck for ck in cands if table[ck]["small_tremor_ok"] and table[ck]["fc_ok"]]
    chosen = min(ok, key=lambda ck: table[ck]["J_ink_1_2mm_um"]) if ok else ref
    return {"rule": "T0", "table": table, "chosen_key": chosen, "passing": ok}


def select_ai(outs: List[Dict], stage: str, cands: List[Dict], seeds=(300,)) -> Dict:
    rows = [r for o in outs for r in o["rows"] if r["seed"] in seeds]
    hi = [r for r in rows if r["amp_mm"] > 0.5]
    lo = [r for r in rows if r["amp_mm"] < 0.5]
    base_J = float(np.mean([r["base"]["ink_err_um"] for r in hi]))
    base_L = float(np.mean([r["base"]["recognition"] for r in hi]))
    table = {}
    for i in range(len(cands)):
        ck = str(i)
        J = float(np.mean([r["c"][ck][case]["ink_err_um"] for r in hi for case in ("ai_correct", "ai_predicted")]))
        L = float(np.mean([r["c"][ck][case]["recognition"] for r in hi for case in ("ai_correct", "ai_predicted")]))
        flips = int(sum(r["c"][ck]["wrong_full"]["flips"] for r in rows))
        flips_hi = int(sum(r["c"][ck]["wrong_full"]["flips"] for r in hi))
        ok = flips <= 0
        small = {}
        if lo:
            for f0 in F0S:
                rr = [r for r in lo if r["f0"] == f0]
                e = float(np.mean([r["c"][ck]["ai_predicted"]["ink_err_um"] for r in rr]))
                e0 = float(np.mean([r["base"]["ink_err_um"] for r in rr]))
                l_ = float(np.mean([r["c"][ck]["ai_predicted"]["recognition"] for r in rr]))
                l0 = float(np.mean([r["base"]["recognition"] for r in rr]))
                small[f"{f0:g}Hz"] = {"ink": e, "ink_base": e0, "letters": l_, "letters_base": l0}
                if e > REL_TOL * e0 or l_ < l0 - LETTER_TOL:
                    ok = False
        if stage == "T2" and L < base_L:
            ok = False
        fc = None
        if outs[0].get("tremor_free"):
            fa = float(np.mean([o["tremor_free"][ck]["ai"] for o in outs]))
            fb = float(np.mean([o["tremor_free"][ck]["base"] for o in outs]))
            fc = {"ai": fa, "base": fb}
            if fa > fb + FC_EXTRA_UM:
                ok = False
        table[ck] = {"params": cands[i], "J_ink_1_2mm_um": J, "letters_1_2mm": L, "flips_wrong_full": flips,
                     "flips_wrong_full_1_2mm": flips_hi, "small_tremor": small, "false_correction": fc, "passes": ok,
                     "gain_vs_base": 1.0 - J / base_J,
                     "words_1_2mm": float(np.mean([r["c"][ck][case]["word_acc_app"] for r in hi for case in ("ai_correct", "ai_predicted")])),
                     "ai_share_1_2mm": float(np.mean([r["c"][ck][case]["ai_share"] for r in hi for case in ("ai_correct", "ai_predicted")
                                                      if r["c"][ck][case].get("ai_share") is not None]))}
    passing = [ck for ck in table if table[ck]["passes"]]
    best = min(passing, key=lambda ck: table[ck]["J_ink_1_2mm_um"]) if passing else None
    adopt = best is not None and table[best]["gain_vs_base"] >= MIN_GAIN
    return {"rule": stage, "base_J_ink_1_2mm_um": base_J, "base_letters_1_2mm": base_L, "table": table,
            "best_passing": best, "adopted": adopt, "chosen": cands[int(best)] if best is not None else None}


def amp_gate_from_t0(outs: List[Dict], base_key: str) -> float:
    """Rule for the guidance amplitude gate: 1.2 x the largest per-run median tracker amplitude at 0.3 mm and on
    tremor-free writing (tuning data)."""
    v = [r["c"][base_key]["amp_median_um"] for o in outs for r in o["rows"] if abs(r["amp_mm"] - 0.3) < 1e-9]
    v += [o["tremor_free"][base_key]["amp_median_um"] for o in outs]
    return 1.2 * max(v) * 1e-6
