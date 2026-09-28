"""Proposed evidence-ledger rows (results/opt/tracker_evidence_rows.csv) in the exact column format of docs/evidence.csv.

Ids (and only these): ACT-46 ... ACT-55 and EML-33 ... EML-39.  Every number is read from results/opt/tracker.json
(the stage files), so the ledger and the results cannot disagree.  docs/evidence.csv itself is not edited.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Dict, List

from . import RESULTS, ROOT

RETRIEVED = "2026-09-28"
ALLOWED = {f"ACT-{i}" for i in range(46, 56)} | {f"EML-{i}" for i in range(33, 40)}


def header() -> List[str]:
    with open(os.path.join(ROOT, "docs", "evidence.csv"), encoding="utf-8") as f:
        return next(csv.reader(f))


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def _e(x):
    return "n/a" if x is None else f"{x:.1e}"


def _row(**kw):
    base = {"year": "2026", "source_type": "derived simulation", "evidence_class": "numerical simulation",
            "access_level": "full text", "participants_or_bench": "none (simulation)", "retrieved": RETRIEVED,
            "search_query": "n/a (derived)", "lead_verification": "", "transferability": "low",
            "transferability_reason": "Simulation on synthetic handwriting and tremor (pencil model P1, fusion/ sensor models)"}
    base.update(kw)
    return base


def rows() -> List[Dict]:
    p = os.path.join(RESULTS, "tracker.json")
    if not os.path.exists(p):
        return []
    R = json.load(open(p))
    S = R["summary"]
    H = {r["label"]: r for r in S["headline"]}
    ship = S.get("ship")
    out = []

    def h(lab, key, nd=3):
        return _f((H.get(lab) or {}).get(key), nd)

    chk = R.get("check") or {}
    ag = chk.get("agreement", {})
    gc = chk.get("gradient_check", {})
    core = ("qt", "ra", "tau_decay", "tau_w", "wmin_hz")
    fd_out = [r["rel_err"][-1] for r in (gc.get("finite_differences_exact_gates") or {}).get("rows", []) if r["param"] not in core]
    gs = R.get("gradient_scan") or {}
    ss = gs.get("small_step") or {}
    scan_txt = ""
    if gs:
        jm = max(s["jumps_adjoint_path"]["max_abs_step_residual"] for s in gs["scan"] if s["param"] != "g")
        dp = max(s["max_abs_diff_paths"] for s in gs["scan"])
        scan_txt = (f"; core parameters (q_t, r_a, tau, tau_w, f_min): the objective has jumps of up to {_e(jm)} from the frequency tracker's discrete "
                    f"decisions, identical in fusion's numba AKF (largest difference between the implementations along the scans {_e(dp)}), so step-1e-3/1e-4 "
                    f"differences do not converge; tiny-step (1e-7) central differences on single recordings (7 parameters x 4 recordings): largest relative "
                    f"error {_e(ss.get('max_rel_err_nonzero'))}, median {_e(ss.get('median_rel_err_nonzero'))} over the {ss.get('n', 0) - ss.get('n_both_zero', 0)} pairs with a "
                    f"non-zero gradient ({ss.get('n_both_zero')} pairs zero in both)")
    out.append(_row(
        id="ACT-46", topic="Differentiable AKF (PyTorch) and its discrete adjoint (numba): agreement with the numba AKF and gradient checks (this study)",
        citation="This ledger's calculation: opt/tracker/torch_akf.py, opt/tracker/adjoint.py, opt/tracker/gradcheck.py; results/opt/tracker.json check",
        doi_or_url="results/opt/tracker.json; docs/opt_tracker.md", source_type="derived calculation", evidence_class="numerical calculation",
        task_or_setup="The acceleration-domain Kalman filter of fusion/estimators.py re-implemented in PyTorch (batched over recordings with their own sample clocks, exact rollback of delayed page samples, frequency tracking, gates, cap, output low-pass) and its sequential core differentiated by a hand-written reverse sweep in numba; compared on tuning-seed streams (5000-5001, 4/8/12 Hz, 0.3 mm)",
        comparator="fusion.estimators.akf (numba); PyTorch autograd; central finite differences",
        key_quantitative_findings=(f"Output relative RMS difference to the numba AKF (6 tuning recordings each): grid-tuned set {_e(ag.get('akf_grid', {}).get('torch_rel_rms_max'))}, "
                                   f"robust set {_e(ag.get('akf_robust', {}).get('torch_rel_rms_max'))}, 120 Hz / 10 ms page sensor {_e(ag.get('akf_120', {}).get('torch_rel_rms_max'))} "
                                   f"(requirement < 1e-2); numba adjoint core {_e(ag.get('akf_grid', {}).get('adjoint_core_rel_rms_max'))}; adjoint vs PyTorch autograd, largest relative gradient difference "
                                   f"{_e((gc.get('adjoint_vs_autograd') or {}).get('max_rel_diff'))} over 23 parameters; central finite differences (step 1e-4, 8 recordings, exact gates) vs adjoint "
                                   f"for the {len(fd_out)} output-stage parameters: largest relative error {_e(max(fd_out) if fd_out else None)}"
                                   + scan_txt),
        units_and_conditions="relative RMS of the estimate over 5 s recordings; relative gradient differences", locator="results/opt/tracker.json check",
        limitations="Agreement is between two implementations of the same model; it says nothing about the model's fidelity to a real pen",
        relevance_to_design="Makes every AKF parameter tunable by gradient on any differentiable objective, and per writer",
        transferability="high", transferability_reason="Numerical property of the implementation",
        design_implication="Use opt.tracker.adjoint for tuning and personalisation; the firmware keeps the numba/C filter structure unchanged",
        stream="ACT"))
    sw = R.get("sweep") or {}
    pts = sw.get("points") or []
    txt = "; ".join(f"chain {p['chain']} lambda {p['lam_fc']:g}: test band {h('adj_' + p['chain'] + '_l' + format(p['lam_fc'], 'g'), 'grid_band_ratio')}, "
                    f"distortion grid {h('adj_' + p['chain'] + '_l' + format(p['lam_fc'], 'g'), 'grid_distortion_um', 0)} um / glyph {h('adj_' + p['chain'] + '_l' + format(p['lam_fc'], 'g'), 'ai_distortion_um', 0)} um"
                    for p in sorted(pts, key=lambda p: (p["chain"], p["lam_fc"])))
    out.append(_row(
        id="ACT-47", topic="AKF tuned by backpropagation through time on domain-randomised writers: the tremor-band / false-correction Pareto front (this study)",
        citation="This ledger's simulation: opt/tracker/train_akf.py, opt/tracker/sweep.py, opt/tracker/evaluate.py; results/opt/tracker.json sweep, test",
        doi_or_url="results/opt/tracker.json; results/opt/fig_tr_pareto.png",
        task_or_setup=("23 AKF parameters (log-transformed) tuned with full-batch Adam through the adjoint on 160 domain-randomised P1 pairs (40 % glyph writers), "
                       "objective = energy-weighted 3-15 Hz residual + lambda_fc x false correction (glyph writers x3) + 0.02/um x RMS above 150 Hz; two chains "
                       "(from the grid-tuned and from the robust random-search sets) swept over lambda_fc; closed loop on the P1 test grid (seeds 200-203) and the aiguide test writers 0-5"),
        comparator="random-search AKF sets (grid-tuned, robust); frozen Kalman; tremor-band oracle",
        key_quantitative_findings=(f"Test grid 3-15 Hz ratio / distortion grid / glyph: grid-tuned {h('akf_grid', 'grid_band_ratio')} / {h('akf_grid', 'grid_distortion_um', 0)} / {h('akf_grid', 'ai_distortion_um', 0)} um, "
                                   f"robust {h('akf_robust', 'grid_band_ratio')} / {h('akf_robust', 'grid_distortion_um', 0)} / {h('akf_robust', 'ai_distortion_um', 0)} um; adjoint points: " + txt),
        units_and_conditions="ratios of ink-error RMS against the tremor-free neutral pen (mean of 60 conditions); distortion um RMS",
        locator="results/opt/tracker.json summary.headline, sweep", limitations="Synthetic writers and tremor; P1 friction model; open-loop hand; one training distribution",
        relevance_to_design="Which AKF parameter set ships", design_implication=f"Ship the selected set ({ship}) as the default tracker parameters; re-tune on EXP-E01 recordings",
        stream="ACT"))
    rep = R.get("replicate") or {}
    if rep:
        g = rep.get("grid", {}); r_ = rep.get("robust", {})
        out.append(_row(
            id="ACT-48", topic="The random search's own objectives re-optimised by the adjoint on the same data (this study)",
            citation="This ledger's simulation: opt/tracker/replicate.py; results/opt/tracker.json replicate",
            doi_or_url="results/opt/tracker.json",
            task_or_setup="fusion.tune.proxy (grid) and fusion.tune.proxy_robust written in PyTorch on exactly fusion.tune's streams (tuning seeds 5000-5007, aiguide writers 100-105), Adam through the adjoint from the random-search winners",
            comparator="fusion.tune random search + local refinement (220-380 candidates)",
            key_quantitative_findings=(f"grid objective J: random search {_f((g.get('start_reference') or {}).get('J'), 4)} -> adjoint {_f((g.get('result_reference') or {}).get('J'), 4)}; "
                                       f"robust objective J: {_f((r_.get('start_reference') or {}).get('J'), 4)} -> {_f((r_.get('result_reference') or {}).get('J'), 4)} "
                                       f"(values from fusion.tune's own numba code); test-grid band ratio {h('rep_grid', 'grid_band_ratio')} (random search {h('akf_grid', 'grid_band_ratio')}), "
                                       f"{h('rep_robust', 'grid_band_ratio')} (robust {h('akf_robust', 'grid_band_ratio')})"),
            units_and_conditions="open-loop objective values; closed-loop ratios as ACT-47", locator="results/opt/tracker.json replicate",
            limitations="Local optimisation from the random-search optimum; the objectives are fusion.tune's proxies",
            relevance_to_design="Separates the optimiser's gain from the objective's", design_implication="Gradient tuning should replace random search for the AKF",
            stream="ACT"))
    out.append(_row(
        id="ACT-49", topic="Adjoint-tuned AKF on the aiguide glyph writers: path to the intended letters, recognition, distortion (this study)",
        citation="This ledger's simulation: opt/tracker/evaluate.py (fusion.aieval pattern); results/opt/tracker.json test.aiguide_summary",
        doi_or_url="results/opt/tracker.json",
        task_or_setup="aiguide test writers 0-5 writing 'return library books by friday' with 0.3 mm tremor at 4-10 Hz on P1 (q_lim 0.30 mm); external estimate from the gyroscope-compensated IMU + 1 kHz page sensor",
        comparator="no correction; random-search AKF sets; previous GRU",
        key_quantitative_findings=(f"Path RMS to the intended letters, writing only: no correction {h('neutral', 'ai_path_wo_um', 0)} um, grid-tuned AKF {h('akf_grid', 'ai_path_wo_um', 0)}, "
                                   f"robust {h('akf_robust', 'ai_path_wo_um', 0)}, previous GRU {h('gru_old', 'ai_path_wo_um', 0)}, ship {h(ship, 'ai_path_wo_um', 0)}, "
                                   f"GRU band target {h('gru_band', 'ai_path_wo_um', 0)}, hybrid {h('hybrid', 'ai_path_wo_um', 0)}; recognition {h('neutral', 'ai_recognition_wo')} -> ship {h(ship, 'ai_recognition_wo')}; "
                                   f"distortion on tremor-free glyph writing: ship {h(ship, 'ai_distortion_um', 0)} um, robust {h('akf_robust', 'ai_distortion_um', 0)} um, grid-tuned {h('akf_grid', 'ai_distortion_um', 0)} um"),
        units_and_conditions="um RMS, mean of 24 scenarios", locator="results/opt/tracker.json test.aiguide_summary",
        limitations="Glyph-font writers; one sentence; open-loop hand", relevance_to_design="Whether sharp writers are harmed",
        design_implication="Judge trackers by the path to the intended letters and distortion on sharp writing, not only by the grid ratio",
        stream="ACT"))
    ps = R.get("personal") or {}
    pf = R.get("personal_fc") or {}
    if ps:
        tg = (ps.get("test") or {}).get("grid_summary", {})
        du = (ps.get("test") or {}).get("distortion_um", {})
        fc_txt = ""
        if pf:
            tf = (pf.get("test") or {}).get("grid_summary", {}).get("akf_personal_adjoint_fc", {})
            fc_txt = (f"; with a false-correction term on other writers' tremor-free training writing (weight {pf.get('lam_chosen')} chosen on tuning seeds): "
                      f"band ratio {_f(tf.get('band_ratio_mean'))}, distortion {_f((pf.get('test') or {}).get('distortion_um'), 0)} um")
        out.append(_row(
            id="ACT-50", topic="Per-writer AKF parameters by gradient descent on the 20 s calibration recording vs the 12-candidate choice (this study)",
            citation="This ledger's simulation: opt/tracker/personal.py; results/opt/tracker.json personal",
            doi_or_url="results/opt/tracker.json",
            task_or_setup=("fusion.personal's calibration labels (page path matched to the known shapes, cross-track 3-15 Hz per stroke; no simulator truth); "
                           f"12 parameters refined from the 12-candidate choice by Adam through the adjoint with a quadratic prior (weight {ps.get('rho_chosen')} chosen on tuning seeds 5000-5003); "
                           "test seeds 200-203 at 0.3 mm, 4-12 Hz; distortion from the 6 and 10 Hz calibrations on tremor-free writing"),
            comparator="population (robust) set; fusion.personal 12-candidate choice",
            key_quantitative_findings=(f"Test band ratio (mean of 20 conditions): population {_f((tg.get('akf_robust') or {}).get('band_ratio_mean'))}, "
                                       f"12-candidate {_f((tg.get('akf_personal') or {}).get('band_ratio_mean'))}, adjoint {_f((tg.get('akf_personal_adjoint') or {}).get('band_ratio_mean'))}; "
                                       f"distortion 12-candidate {_f(du.get('akf_personal'), 0)} um, adjoint {_f(du.get('akf_personal_adjoint'), 0)} um" + fc_txt),
            units_and_conditions="ratios as ACT-47", locator="results/opt/tracker.json personal",
            limitations="Stationary synthetic tremor (the calibration tremor has the test tremor's frequency and amplitude); one calibration per condition",
            relevance_to_design="CAL_USER content", design_implication="See docs/opt_tracker.md s6", stream="ACT"))
    L = R.get("learned") or {}
    for rid, lab, key, name in (("EML-33", "gru_band", "gru", "GRU with the tremor-band target"),
                                ("EML-34", "hybrid", "hybrid", "AKF + learned authority gate")):
        m = L.get(key) or {}
        out.append(_row(
            id=rid, topic=f"{name}: trained on the 3-15 Hz disturbance with a false-correction and jitter penalty (this study)",
            citation="This ledger's simulation: opt/tracker/learned.py, opt/tracker/learned_train.py; results/opt/tracker.json learned, test",
            doi_or_url="results/opt/tracker.json; results/opt/tracker_models/",
            task_or_setup=(f"{m.get('kind')} model, {m.get('n_in')} inputs, hidden {m.get('hidden')}, {m.get('macs_per_step')} MAC per 1 ms step, "
                           f"{m.get('train_recordings')} training recordings (fusion training specs, randomised sensor rotation), trained at the tick level through the output low-pass; "
                           "loss: error against the zero-phase 3-15 Hz disturbance (GRU) or the AKF objective (gate), lambda_fc x false correction (glyph x3), jitter"),
            comparator="previous GRU (whole-disturbance target); adjoint-tuned AKF; no correction",
            key_quantitative_findings=(f"Test grid band ratio {h(lab, 'grid_band_ratio')}, all-band {h(lab, 'grid_ratio')}, distortion {h(lab, 'grid_distortion_um', 0)} um; "
                                       f"path to intended letters {h(lab, 'grid_path_um', 0)} um (no correction {h('neutral', 'grid_path_um', 0)}, previous GRU {h('gru_old', 'grid_path_um', 0)}); "
                                       f"aiguide path writing only {h(lab, 'ai_path_wo_um', 0)} um (no correction {h('neutral', 'ai_path_wo_um', 0)}); glyph distortion {h(lab, 'ai_distortion_um', 0)} um"),
            units_and_conditions="as ACT-47", locator="results/opt/tracker.json learned, summary.headline",
            limitations="Trained and tested on the same generators (other seeds and writers); no real data", relevance_to_design="Whether a learned model should ship",
            design_implication="Keep behind the ICD s5 guard until EXP-E01", stream="EML"))
    B = R.get("budget") or {}
    if B:
        a = B.get("akf_adjoint_tuned", {}); g = B.get("gru_band", {}); hy = B.get("hybrid_akf_gate", {})
        out.append(_row(
            id="EML-35", topic="MCU cost of the adjoint-tuned AKF, the band-target GRU and the AKF + gate hybrid on an nRF54L15-class Cortex-M33 (this study)",
            citation="This ledger's calculation: opt/tracker/budget.py (fusion/budget.py conventions); results/opt/tracker.json budget",
            doi_or_url="results/opt/tracker.json", source_type="derived calculation", evidence_class="calculation",
            task_or_setup="MAC counts, float32 at 2 cycles per MAC and int8 CMSIS-NN at 0.5 MAC per cycle + 300 cycles per layer call (ASSUMPTION), 128 MHz",
            comparator="frozen Kalman; previous GRU",
            key_quantitative_findings=(f"AKF {_f(100 * (a.get('cpu_fraction_f32_total') or 0), 1)} % CPU float32 ({_f((a.get('mac_per_s_total') or 0) / 1e6, 2)} M MAC/s); "
                                       f"GRU {g.get('mac_per_step')} MAC per step ({_f(100 * (g.get('cpu_fraction_f32') or 0), 1)} % float32, {_f(100 * (g.get('cpu_fraction_int8_cmsis') or 0), 1)} % int8); "
                                       f"hybrid {_f(100 * (hy.get('cpu_fraction_f32_total') or 0), 1)} % float32 total, gate {hy.get('gate', {}).get('mac_per_step')} MAC per step"),
            units_and_conditions="1 kHz page sensor; accelerometer 1.92 kHz; network 1 kHz", locator="results/opt/tracker.json budget",
            limitations="Cycle model assumed; not profiled", relevance_to_design="Fits next to the servo and BLE",
            transferability="medium", transferability_reason="Instruction-level costs to be measured on the target",
            design_implication="All three fit; the AKF alone is the cheapest", stream="EML"))
    return [r for r in out if r["id"] in ALLOWED]


def write(path: str = None) -> str:
    path = path or os.path.join(RESULTS, "tracker_evidence_rows.csv")
    head = header()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        for r in rows():
            w.writerow([r.get(k, "") for k in head])
    return path
