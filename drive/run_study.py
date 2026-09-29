"""Study D: paper-grounded heel drive.  One command: python3 -m drive.run_study [--quick] [--stages ...] [--retune]

Stages (each writes its own JSON under results/drive/, so they can be re-run separately):
  design   CALC: heel geometry, traction capacity over the writer population, tyre mechanics, concept sizing,
           heading rates of letters, differentiable design optimisation (autograd) with its gradient check
  tune     SIM on tuning writers/seeds: gains by grid and Bayesian optimisation, then results/drive/rules.json
           (skipped when rules.json exists, unless --retune)
  test     SIM on test writers/seeds with the frozen rules: tasks (a)-(e) and the resisting-writer runs
  extra    SIM: the recommended design's passive mode on its driven wheel ('sd_path'), added after the main test
           with the same frozen rules and cases (tasks_extra.json)
  report   figures (with CSV twins), evidence rows, layout parts, proposals, tables.md, grounded_drive.json
--quick: one test writer and seed, fewer conditions, the quick tuning (about 5-8 minutes); never overwrites the full
         rules or test files (it writes *_quick.json).
Compute: one process (the study shares four cores with four other studies).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import Dict, List

import numpy as np

from . import RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, EVIDENCE_CALC, EVIDENCE_SIM, ensure_paths

ensure_paths()
from stabpen import provenance as PV  # noqa: E402

OUT = RESULTS_DIR


def _write(name: str, obj: Dict, quick: bool, evidence: str, seeds=None):
    if quick:
        name = name.replace(".json", "_quick.json")
    obj = dict(obj)
    obj["meta"] = PV.metadata(evidence, seeds=seeds, extra={"script": "drive/run_study.py", "doc": "docs/grounded_drive.md",
                                                             "quick": quick})
    obj["stabpen.provenance"] = obj["meta"]
    PV.write_json(str(OUT / name), obj)
    return OUT / name


def _load(name: str, quick: bool):
    p = OUT / (name.replace(".json", "_quick.json") if quick else name)
    return json.loads(p.read_text()) if p.exists() else None


# ============================================================================== design (CALC)
def chosen_heel(r_e: float = 1.0, delta: float = 0.35, roll_deg: float = 20.0) -> Dict:
    """The heel of the recommended design (steered and driven wheel d 2 mm with its steering ring): contact radius,
    skid radius, spring travel, roll tolerance and the front-end consequences (CALC)."""
    from . import geometry as GE
    R_d = math.ceil(GE.wheel_pod(r_e)["R_d_mm"] * 4.0) / 4.0
    R_s = R_d - delta
    tilt = GE.protrusion_vs_tilt(r_e, delta)
    s_tr = max(max(t["protrusion_mm"] for t in tilt), GE.travel_for_roll(R_s, roll_deg))
    return {"r_e_mm": r_e, "R_d_mm": R_d, "R_skid_mm": R_s, "delta_mm": delta, "spring_travel_mm": s_tr,
            "roll_tolerance_deg": GE.roll_tolerance(R_s, s_tr), "protrusion_by_tilt": tilt,
            "front_end": GE.front_end_at(R_s), "front_end_revH": GE.front_end_at(6.75)}


def stage_design(quick: bool, log=print) -> Dict:
    from . import catalog as CT, concepts as CN, contact as CO, design_opt as DO, geometry as GE, params as PA
    t0 = time.time()
    out = {"params": PA.all_tables(), "catalog": CT.as_dict()}
    out["geometry"] = {"sizes": GE.sweep_element_sizes(), "heel_1p0": GE.heel_design(1.0, 0.35, 20.0),
                       "heel_1p25": GE.heel_design(1.25, 0.35, 20.0), "heel_1p5": GE.heel_design(1.5, 0.35, 20.0),
                       "roll_tolerance": [{"R_s_mm": R, "travel_mm": s, "roll_deg": GE.roll_tolerance(R, s)}
                                          for R in (7.25, 8.0) for s in (0.25, 0.5, 0.75, 1.0, 1.5)]}
    pods = []
    for r_e in (0.75, 1.0, 1.25, 1.5, 2.0):
        wp = GE.wheel_pod(r_e)
        pods.append({"r_e_mm": r_e, "R_bare_mm": GE.required_contact_radius(r_e)["R_d_mm"],
                     "R_wheel_pod_mm": wp["R_d_mm"], "R_ball_pod_mm": GE.ball_pod(r_e)["R_d_mm"],
                     "front_end": GE.front_end_at(wp["R_d_mm"])})
    out["geometry"]["pods"] = pods
    out["geometry"]["chosen_heel"] = chosen_heel()
    log(f"  geometry [{time.time() - t0:.0f}s]")
    out["capacity"] = [CO.capacity_stats(P, mu) for P in (0.3, 0.4, 0.5, 0.55, 0.6, 0.8) for mu in (0.6, 0.9, 1.2)]
    out["tyre"] = CO.tyre_table()
    out["paper_hold"] = [dict(CO.paper_hold(F, N, Nh, mu), F_drive_N=F, N_total_N=N, N_hand_rest_N=Nh, mu_pd=mu)
                         for F in (0.3, 0.5) for N in (0.6, 1.0) for Nh in (0.0, 1.0, 3.0) for mu in (0.25, 0.5)]
    out["heading_rates"] = {"letters": CN.heading_rates((100, 101, 102)),
                            "smoothed_2mm": CN.heading_rates((100, 101, 102), smooth_mm=2.0)}
    out["concepts"] = CN.table(out["heading_rates"]["letters"])
    log(f"  concepts [{time.time() - t0:.0f}s]")
    out["design_opt"] = DO.study(quick=quick)
    log(f"  design optimisation [{time.time() - t0:.0f}s]")
    _write("design.json", out, quick, EVIDENCE_CALC)
    return out


# ============================================================================== tune (SIM, tuning writers)
def stage_tune(quick: bool, retune: bool, log=print) -> Dict:
    from . import tune as TU
    path = OUT / ("rules_quick.json" if quick else "rules.json")
    if path.exists() and not retune:
        log("  rules exist: using them (no retuning)")
        return json.loads(path.read_text())
    res = TU.tune(quick=quick, log=log)
    _write("tuning.json", res, quick, EVIDENCE_SIM, seeds={"tuning_writers": [100, 101, 102], "seed": 300})
    return TU.freeze(res, path)


# ============================================================================== test (SIM, test writers)
PRACTICE_CONDS = ["none", "nose_partial", "board_partial", "board_full", "ball_partial", "ball_full", "wheel_path",
                  "wheel_partial", "sd_full", "wheel_path+nose"]
TREMOR_CONDS = ["none", "nose_akf", "nose_oracle", "ball_damp", "ball_brake", "wheel_tremor_brake",
                "ball_damp+nose_akf", "wheel_known_text"]
AUTOWRITE_CONDS = ["writer_alone", "nose_nogate", "relaxed_nose", "board_lead+nose", "ball_lead", "ball_lead+nose",
                   "sd_lead", "sd_lead+nose"]


def case_mu(key: int) -> float:
    from .params import CONTACT
    lo, hi = CONTACT["mu_drive_range"].value
    return float(np.random.default_rng(880_000 + key).uniform(lo, hi))


def _agg(rows: List[Dict], group: str, keys: List[str]) -> Dict:
    out = {}
    for g in sorted({r[group] for r in rows}):
        sel = [r for r in rows if r[group] == g]
        cell = {"n": len(sel)}
        for k in keys:
            v = [r[k] for r in sel if isinstance(r.get(k), (int, float)) and r.get(k) is not None and not
                 (isinstance(r.get(k), float) and math.isnan(r[k]))]
            if v:
                cell[k] = float(np.mean(v))
                cell[k + "_sd"] = float(np.std(v))
        out[g] = cell
    return out


def test_practice(rules, writers, seeds, profiles, conds, log=print) -> Dict:
    from . import scenarios as S, tune as TU
    rows = []
    t0 = time.time()
    for profile in profiles:
        for w in writers:
            for seed in seeds:
                case = S.practice_case(w, seed, profile)
                mu = case_mu(1000 * w + seed)
                ev0, r0 = S.run_practice(case, "none", TU.gains_for(rules, "none"), mu)
                for cond in conds:
                    if cond == "none":
                        ev = ev0
                    else:
                        ev, _ = S.run_practice(case, cond, TU.gains_for(rules, cond), mu, ref=r0)
                    rows.append(dict({k: v for k, v in ev.items() if not isinstance(v, (list, dict))}, writer=w, seed=seed,
                                     profile=profile, mu=mu, N_mean=case["N_mean"], cond=cond))
            log(f"    practice {profile} writer {w} [{time.time() - t0:.0f}s]")
    keys = ["target_err_um", "target_p95_um", "letters_read_ok", "words_app", "words_read_ok_letters", "device_share",
            "device_disp_rms_mm", "F_rms_N", "F_p95_N", "F_max_N", "felt_rms_N", "felt_p95_N", "slide_share",
            "slip_flag_share", "slip_events", "yields", "Nd_mean_N", "cap_mean_N", "P_drive_mean_W",
            "error_letters_read_as_target"]
    agg = {}
    for profile in profiles:
        agg[profile] = _agg([r for r in rows if r["profile"] == profile], "cond", keys)
    return {"rows": rows, "aggregate": agg}


def test_resisting(rules, writers, seeds, log=print) -> Dict:
    """What a lightly resisting writer feels and gets (HAP-26 upper-CI arm), dysgraphia learners."""
    from . import scenarios as S, tune as TU
    rows = []
    for w in writers:
        for seed in seeds:
            case = S.practice_case(w, seed, "dysgraphia")
            mu = case_mu(1000 * w + seed)
            hand = S._hand("lightly_resisting")
            ev0, r0 = S.run_practice(case, "none", TU.gains_for(rules, "none"), mu, hand=hand)
            for cond in ["none", "board_full", "ball_full", "wheel_path", "sd_full"]:
                ev = ev0 if cond == "none" else S.run_practice(case, cond, TU.gains_for(rules, cond), mu, hand=hand, ref=r0)[0]
                rows.append(dict({k: v for k, v in ev.items() if not isinstance(v, (list, dict))}, writer=w, seed=seed,
                                 mu=mu, cond=cond, hand="lightly_resisting"))
    keys = ["target_err_um", "letters_read_ok", "device_share", "F_rms_N", "F_p95_N", "felt_rms_N", "felt_p95_N",
            "slide_share", "yields"]
    return {"rows": rows, "aggregate": _agg(rows, "cond", keys)}


def test_loops(rules, seeds, conds, log=print) -> Dict:
    from . import scenarios as S, tune as TU
    rows = []
    for hand in ("relaxed", "lightly_resisting"):
        for seed in seeds:
            case = S.loops_case(seed, hand=hand)
            mu = case_mu(500 + seed)
            ev0, r0 = S.run_loops(case, "none", TU.gains_for(rules, "none"), mu)
            for cond in conds:
                ev = ev0 if cond == "none" else S.run_loops(case, cond, TU.gains_for(rules, cond), mu, ref=r0)[0]
                rows.append(dict(ev, seed=seed, hand=hand, mu=mu, cond=cond))
    keys = ["loop_height_ratio_ink", "last_loop_ratio", "ink_to_template_rms_mm", "F_rms_N", "F_max_N", "felt_rms_N",
            "slide_share", "yields"]
    agg = {h: _agg([r for r in rows if r["hand"] == h], "cond", keys) for h in ("relaxed", "lightly_resisting")}
    return {"rows": rows, "aggregate": agg}


def test_reversal(rules, seeds, log=print) -> Dict:
    from . import scenarios as S, tune as TU
    rows = []
    for relaxed, conds in ((False, ["none", "board_full", "ball_full", "wheel_path", "sd_full"]),
                           (True, ["none", "board_lead", "ball_lead", "sd_lead", "wheel_path"])):
        for seed in seeds:
            case = S.reversal_case(seed, relaxed=relaxed)
            mu = case_mu(700 + seed)
            ev0, r0 = S.run_reversal(case, "none", TU.gains_for(rules, "none"), mu)
            for cond in conds:
                ev = ev0 if cond == "none" else S.run_reversal(case, cond, TU.gains_for(rules, cond), mu, ref=r0)[0]
                rows.append(dict(ev, seed=seed, mu=mu, cond=cond, writer=("relaxed (lead-through)" if relaxed else "set on b")))
    keys = ["bowl_correct_side", "bowl_coverage", "bowl_to_template_rms_mm", "F_rms_N", "F_max_N", "felt_rms_N",
            "felt_p95_N", "slide_share", "slip_events", "yields"]
    agg = {wtr: _agg([r for r in rows if r["writer"] == wtr], "cond", keys) for wtr in ("set on b", "relaxed (lead-through)")}
    return {"rows": rows, "aggregate": agg}


def test_tremor(rules, writers, seeds, f0s, amps, conds, log=print, adapt_subset=True) -> Dict:
    from . import scenarios as S, tune as TU
    from handwriting import params as PR
    trackers = {"ship": PR.akf_ship(), "revh": PR.akf_revh()}
    rows, dist = [], []
    t0 = time.time()
    for w in writers:
        etw = S.ETWriter(w)
        for seed in seeds:
            mu = case_mu(3000 * w + seed)
            for f0 in f0s:
                for amp in amps:
                    out = run_tremor_conds(S, TU, rules, etw, f0, amp, seed, conds, mu, trackers)
                    for cond, ev in out.items():
                        rows.append(dict(ev, writer=w, seed=seed, f0=f0, amp_mm=amp * 1e3, mu=mu, cond=cond,
                                         ratio=ev["ink_err_um"] / max(out["none"]["ink_err_um"], 1e-9),
                                         cell=f"{f0:g}Hz_{amp * 1e3:g}mm"))
            # tremor-free writing: what the device does to clean writing (false correction)
            out = run_tremor_conds(S, TU, rules, etw, 0.0, 0.0, seed, conds, mu, trackers)
            for cond, ev in out.items():
                dist.append(dict(ev, writer=w, seed=seed, cond=cond, adapted_writer=False))
            if adapt_subset:
                for cond in ["ball_damp", "ball_brake", "wheel_tremor_brake"]:
                    g = TU.gains_for(rules, cond)
                    ev = S.run_tremor(etw, 0.0, 0.0, seed, [cond], g, mu, trackers, adapt_writer=True)[cond]
                    dist.append(dict(ev, writer=w, seed=seed, cond=cond, adapted_writer=True))
                    ev8 = S.run_tremor(etw, 8.0, 1e-3, seed, [cond], g, mu, trackers, adapt_writer=True)[cond]
                    rows.append(dict(ev8, writer=w, seed=seed, f0=8.0, amp_mm=1.0, mu=mu, cond=cond + " (adapted writer)",
                                     cell="8Hz_1mm",
                                     ratio=ev8["ink_err_um"] / max([r for r in rows if r["writer"] == w and r["seed"] == seed and
                                                                    r["cond"] == "none" and r["cell"] == "8Hz_1mm"][0]["ink_err_um"], 1e-9)))
        log(f"    tremor writer {w} [{time.time() - t0:.0f}s]")
    keys = ["ink_err_um", "ratio", "band_err_um", "letters_read", "words_app", "F_rms_N", "F_p95_N", "felt_rms_N",
            "slide_share", "yields", "P_drive_mean_W"]
    by_cell = {}
    for cell in sorted({r["cell"] for r in rows}):
        by_cell[cell] = _agg([r for r in rows if r["cell"] == cell], "cond", keys)
    by_amp = {}
    for amp in sorted({r["amp_mm"] for r in rows}):
        by_amp[f"{amp:g}mm"] = _agg([r for r in rows if r["amp_mm"] == amp and "(adapted" not in r["cond"]], "cond", keys)
    by_f = {}
    for f0 in sorted({r["f0"] for r in rows}):
        by_f[f"{f0:g}Hz"] = _agg([r for r in rows if r["f0"] == f0 and "(adapted" not in r["cond"]], "cond", keys)
    d_agg = {"naive": _agg([d for d in dist if not d["adapted_writer"]], "cond", ["ink_err_um", "letters_read", "words_app"]),
             "adapted": _agg([d for d in dist if d["adapted_writer"]], "cond", ["ink_err_um", "letters_read", "words_app"])}
    return {"rows": rows, "by_cell": by_cell, "by_amp": by_amp, "by_f": by_f, "tremor_free": d_agg}


def run_tremor_conds(S, TU, rules, etw, f0, amp, seed, conds, mu, trackers) -> Dict:
    out = {}
    # conditions sharing gains are grouped so that the tracker's neutral run is reused
    for cond in conds:
        if cond == "wheel_known_text":
            out[cond] = run_known_text(S, TU, rules, etw, f0, amp, seed, mu)
            continue
        g = TU.gains_for(rules, cond)
        res = S.run_tremor(etw, f0, amp, seed, ["none", cond] if cond != "none" else ["none"], g, mu, trackers)
        out[cond] = res[cond]
    return out


def run_known_text(S, TU, rules, etw, f0, amp, seed, mu) -> Dict:
    """Copying known text with tremor: the steered wheel follows the template of the writer's own letters (an upper
    bound: the app knows the words and the writer's style exactly; ASSUMPTION)."""
    from handwriting import params as PR, plant as PL, writers as W
    from . import plant as DP
    from aiguide.template import build_track, LetterTemplate
    d = W.tremor_path(etw.scn0.t, f0, amp, seed, etw.w) if amp > 0 else np.zeros_like(etw.scn0.intended)
    scn = etw.scenario(d)
    st = etw.written.style
    tl = [LetterTemplate(L.char, list(L.polylines), 1.0, "own", k) for k, L in enumerate(etw.written.letters)]
    trk = build_track(tl, speed=st.speed_mm_s * 1e-3, air_speed=st.air_speed_mm_s * 1e-3, dt=5e-4)
    g = TU.gains_for(rules, "wheel_path")
    drv = S.drive_for("wheel_path", g, mu)
    r = DP.run(scn, etw.pen, etw.hand, PR.Writing(), PL.Controls(stroke_match=True), drv, Ntot=etw.Nt, hand_path=etw.hp,
               tremor=d, drive_tmpl=trk.xy, drive_tdown=trk.pen_down.astype(float), seed=90_000 + seed, rec_hz=4000.0)
    ev = S.et_metrics(etw, r, scn)
    ev.update(S.drive_metrics(r, None))
    return ev


def test_autowrite(rules, writers, seeds, conds, log=print) -> Dict:
    from . import scenarios as S, tune as TU
    rows, keep = [], {}
    t0 = time.time()
    for w in writers:
        for seed in seeds:
            case = S.autowrite_case(w, seed)
            mu = case_mu(5000 * w + seed)
            ev0, r0 = S.run_autowrite(case, "writer_alone", TU.gains_for(rules, "none"), mu)
            for cond in conds:
                if cond == "writer_alone":
                    ev, r = ev0, r0
                else:
                    ev, r = S.run_autowrite(case, cond, TU.gains_for(rules, cond), mu, ref=r0)
                rows.append(dict({k: v for k, v in ev.items() if not isinstance(v, (list, dict))}, writer=w, seed=seed,
                                 mu=mu, cond=cond))
                if w == writers[0] and seed == seeds[0]:
                    from handwriting import metrics as MT
                    keep[cond] = MT.decimate_path(r, hz=200.0).tolist()
            log(f"    autowrite writer {w} seed {seed} [{time.time() - t0:.0f}s]")
    keys = ["target_err_um", "letters_read_ok", "words_app", "words_read_ok_letters", "device_work_share",
            "pen_speed_mm_s", "F_rms_N", "F_max_N", "slide_share", "yields", "P_drive_mean_W", "n_strokes_done"]
    first = TEST_WRITERS[0]
    return {"rows": rows, "aggregate": _agg(rows, "cond", keys), "paths_first_case": keep}


def stage_test(rules: Dict, quick: bool, log=print) -> Dict:
    t0 = time.time()
    W_ = TEST_WRITERS[:1] if quick else TEST_WRITERS
    S_ = TEST_SEEDS[:1] if quick else TEST_SEEDS
    out = {"rules_sha256_16": rules.get("sha256_16"), "rules_frozen_utc": rules.get("frozen_utc"),
           "test_writers": list(W_), "test_seeds": list(S_)}
    out["practice"] = test_practice(rules, W_, S_, ("dysgraphia", "dyslexia"), PRACTICE_CONDS, log)
    log(f"  (a) practice [{time.time() - t0:.0f}s]")
    out["resisting"] = test_resisting(rules, W_, S_[:2], log)
    log(f"  resisting writer [{time.time() - t0:.0f}s]")
    out["loops"] = test_loops(rules, S_, ["none", "board_full", "ball_full", "wheel_path", "sd_full"], log)
    log(f"  (b) loops [{time.time() - t0:.0f}s]")
    out["reversal"] = test_reversal(rules, S_, log)
    log(f"  (c) reversal [{time.time() - t0:.0f}s]")
    out["autowrite"] = test_autowrite(rules, W_, S_[:2], AUTOWRITE_CONDS, log)
    log(f"  (e) autowrite [{time.time() - t0:.0f}s]")
    out["tremor"] = test_tremor(rules, W_, S_[:1], (4.0, 6.0, 8.0, 10.0) if not quick else (8.0,),
                                (1e-3, 2e-3) if not quick else (1e-3,), TREMOR_CONDS, log)
    log(f"  (d) tremor [{time.time() - t0:.0f}s]")
    out["elapsed_s"] = time.time() - t0
    _write("tasks.json", out, quick, EVIDENCE_SIM, seeds={"test_writers": list(W_), "test_seeds": list(S_)})
    return out


# ============================================================================== extra condition (after the main test)
EXTRA_CONDS = ["sd_path"]


def stage_extra(rules: Dict, quick: bool, log=print) -> Dict:
    """The recommended design's passive mode carries its drive train: 'sd_path' is the steer-only law (frozen rules,
    the same gains as 'wheel_path') on the driven wheel's hardware (reflected mass 3.8 g, back-drive 24 mN, 70 %
    friction compensation, no push).  It was defined in drive_for before the freeze and is run after the main test
    as an added condition; no gain is changed (SIM)."""
    t0 = time.time()
    W_ = TEST_WRITERS[:1] if quick else TEST_WRITERS
    S_ = TEST_SEEDS[:1] if quick else TEST_SEEDS
    out = {"rules_sha256_16": rules.get("sha256_16"), "conds": EXTRA_CONDS,
           "note": "added after the main test run; frozen rules; same cases and seeds as tasks.json"}
    out["practice"] = test_practice(rules, W_, S_, ("dysgraphia", "dyslexia"), ["none"] + EXTRA_CONDS, log)
    out["resisting"] = test_resisting_conds(rules, W_, S_[:2], ["none"] + EXTRA_CONDS)
    out["loops"] = test_loops(rules, S_, ["none"] + EXTRA_CONDS, log)
    out["elapsed_s"] = time.time() - t0
    _write("tasks_extra.json", out, quick, EVIDENCE_SIM, seeds={"test_writers": list(W_), "test_seeds": list(S_)})
    return out


def test_resisting_conds(rules, writers, seeds, conds) -> Dict:
    from . import scenarios as S, tune as TU
    rows = []
    for w in writers:
        for seed in seeds:
            case = S.practice_case(w, seed, "dysgraphia")
            mu = case_mu(1000 * w + seed)
            hand = S._hand("lightly_resisting")
            ev0, r0 = S.run_practice(case, "none", TU.gains_for(rules, "none"), mu, hand=hand)
            for cond in conds:
                ev = ev0 if cond == "none" else S.run_practice(case, cond, TU.gains_for(rules, cond), mu, hand=hand, ref=r0)[0]
                rows.append(dict({k: v for k, v in ev.items() if not isinstance(v, (list, dict))}, writer=w, seed=seed,
                                 mu=mu, cond=cond, hand="lightly_resisting"))
    keys = ["target_err_um", "letters_read_ok", "device_share", "F_rms_N", "F_p95_N", "felt_rms_N", "felt_p95_N",
            "slide_share", "yields"]
    return {"rows": rows, "aggregate": _agg(rows, "cond", keys)}


PRACTICE_KEYS_REPORT = ["target_err_um", "target_p95_um", "letters_read_ok", "words_app", "words_read_ok_letters",
                        "device_share", "F_rms_N", "F_p95_N", "F_max_N", "felt_rms_N", "felt_p95_N", "slide_share",
                        "slip_flag_share", "slip_events", "yields", "Nd_mean_N", "cap_mean_N", "mu_hat_mean",
                        "P_drive_mean_W", "error_letters_read_as_target", "coverage"]


def reaggregate(block: Dict) -> Dict:
    """Recompute a practice block's aggregates from its rows with the report's keys (adds coverage, mu_hat)."""
    if not block or "rows" not in block:
        return block
    rows = block["rows"]
    block["aggregate"] = {prof: _agg([r for r in rows if r.get("profile") == prof], "cond", PRACTICE_KEYS_REPORT)
                          for prof in sorted({r.get("profile") for r in rows})}
    return block


def merge_extra(tasks: Dict, extra: Dict) -> Dict:
    """Add the extra condition's aggregates to the main test tables (the 'none' rows are identical re-runs)."""
    if not tasks or not extra:
        return tasks
    for c in extra.get("conds", []):
        for prof, cells in extra.get("practice", {}).get("aggregate", {}).items():
            if c in cells:
                tasks["practice"]["aggregate"].setdefault(prof, {})[c] = cells[c]
        if c in extra.get("resisting", {}).get("aggregate", {}):
            tasks["resisting"]["aggregate"][c] = extra["resisting"]["aggregate"][c]
        for h, cells in extra.get("loops", {}).get("aggregate", {}).items():
            if c in cells:
                tasks["loops"]["aggregate"].setdefault(h, {})[c] = cells[c]
    return tasks


# ============================================================================== report
def stage_report(quick: bool, log=print) -> Dict:
    from . import evidence as EV, figures as FG, layout as LY
    design = _load("design.json", quick)
    tasks, extra = _load("tasks.json", quick), _load("tasks_extra.json", quick)
    if tasks:
        tasks["practice"] = reaggregate(tasks["practice"])
    if extra:
        extra["practice"] = reaggregate(extra["practice"])
    tasks = merge_extra(tasks, extra)
    rules = _load("rules.json", quick)
    figs = FG.make_all(design, tasks, rules, OUT, quick=quick)
    log(f"  figures: {len(figs)}")
    if not quick:
        from . import proposals as PP
        EV.write_rows(OUT / "evidence_rows.csv")
        LY.write_layout(OUT / "layout_parts.json", design)
        PP.write_all(OUT)
    summary = FG.summary(design, tasks, rules)
    (OUT / ("tables_quick.md" if quick else "tables.md")).write_text(
        "<!-- generated by drive/run_study.py --stages report; SIM and CALC tables of docs/grounded_drive.md -->\n"
        + FG.markdown_tables(design, tasks))
    _write("grounded_drive.json", {"summary": summary, "figures": figs}, quick, EVIDENCE_SIM + "; " + EVIDENCE_CALC)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", default="design,tune,test,extra,report")
    ap.add_argument("--retune", action="store_true")
    a = ap.parse_args()
    stages = a.stages.split(",")
    t0 = time.time()
    rules = None
    if "design" in stages:
        print("[design]")
        stage_design(a.quick)
    if "tune" in stages:
        print("[tune]")
        rules = stage_tune(a.quick, a.retune)
    if "test" in stages:
        print("[test]")
        from . import tune as TU
        rules = rules or (json.loads((OUT / "rules_quick.json").read_text()) if a.quick else TU.load_rules())
        stage_test(rules, a.quick)
    if "extra" in stages:
        print("[extra]")
        from . import tune as TU
        rules = rules or (json.loads((OUT / "rules_quick.json").read_text()) if a.quick else TU.load_rules())
        stage_extra(rules, a.quick)
    if "report" in stages:
        print("[report]")
        stage_report(a.quick)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
