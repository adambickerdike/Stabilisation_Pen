"""Assemble results/opt/touchdown.json, results/opt/servo.json and results/opt/touchdown_evidence_rows.csv from the
stage caches of opt/touchdown/run_study.py (results/opt/logs/td_*.json).  Labels: SIM (simulation, pencil model P1
or the reduced model), CALC (kinematics, loop margins, magnet field), MFR (manufacturer statement, ledger id),
ASSUMPTION.  Nothing here is a measurement."""
from __future__ import annotations

import csv
import json
import math
import os

import numpy as np

from stabpen import provenance

from . import law as L

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "opt")
LOGS = os.path.join(OUT, "logs")
EVIDENCE_HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level", "task_or_setup",
                   "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions", "locator", "limitations",
                   "relevance_to_design", "transferability", "transferability_reason", "design_implication", "retrieved", "search_query",
                   "stream", "lead_verification"]
RETRIEVED = "2026-09-28"


def _pencil_params():
    from sim.pencil import design as D
    return D.Params().pencil


def _load(stage):
    p = os.path.join(LOGS, f"td_{stage}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def r3(x):
    if isinstance(x, float):
        return float(f"{x:.4g}") if math.isfinite(x) and x != 0.0 else x
    if isinstance(x, dict):
        return {str(k): r3(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r3(v) for v in x]
    return x


def _cfg_table(val, th):
    S = val["summary"]
    keys = ("extra_mm", "extra_tr_mm", "extra_in_mm", "missing_mm", "extra_tr_tight_mm", "rms_nn_instroke_um", "oracle_ratio",
            "kalman_ratio", "oracle_q_sat_frac", "oracle_limit_frac_contact", "oracle_P_rail_classB_mW", "oracle_P_rail_recovery_mW",
            "oracle_lost_contact_frac", "oracle_extra_tr_per_pd", "oracle_missing_per_pd", "oracle_extra_per_pd",
            "kalman_extra_tr_per_pd", "kalman_missing_per_pd", "kalman_extra_per_pd", "transitions_per_pd", "clean_qff_peak_contact_mm",
            "words_extra_tr_mm")
    return {name: {k: d[th][k] for k in keys if k in d[th]} for name, d in S.items() if th in d}


def _pareto_tail_ratio(bo_res, base):
    """Non-dominated laws in (oracle ratio, tail ink per stroke) over all evaluated points (search seeds), with their
    margins, and the front stop alone at each margin for reference."""
    from .bo import pareto_mask
    rows = bo_res["all"]
    # the full evaluation records (slow touchdowns) are in the search log
    full = {}
    log = os.path.join(LOGS, "ff_bo.jsonl")
    if os.path.exists(log):
        for line in open(log):
            rr = json.loads(line)
            full[json.dumps(rr["x"], sort_keys=True)] = rr["res"]
    F = np.array([[r["res"]["oracle_ratio"], r["res"]["extra_tr_mm"]] for r in rows])
    keep = np.flatnonzero(pareto_mask(F))

    def entry(r):
        fr = full.get(json.dumps(r["x"], sort_keys=True), {})
        return {"margin_mm": r["x"]["margin"] * 1e3, "oracle_ratio": r["res"]["oracle_ratio"],
                "extra_tr_mm_per_stroke": r["res"]["extra_tr_mm"], "missing_mm_per_stroke": r["res"]["missing_mm"],
                "extra_tr_tight_mm_per_stroke": r["res"]["extra_tr_tight_mm"],
                "oracle_limit_frac_contact": r["res"].get("oracle_limit_frac_contact"),
                "slow_touchdown_peak_um_1mm_s": fr.get("slow_1mm_s_max_dev_um"), "slow_touchdown_peak_um_10mm_s": fr.get("slow_10mm_s_max_dev_um"),
                "x": r["x"]}
    front = sorted([entry(rows[i]) for i in keep], key=lambda d: d["oracle_ratio"])
    ref = {k: {"oracle_ratio": v["agg"]["oracle_ratio"], "extra_tr_mm_per_stroke": v["agg"]["extra_tr_mm"],
               "missing_mm_per_stroke": v["agg"]["missing_mm"], "oracle_limit_frac_contact": v["agg"].get("oracle_limit_frac_contact"),
               "slow_touchdown_peak_um_1mm_s": (v.get("slow") or {}).get("1mm_s", {}).get("max_dev_um"),
               "slow_touchdown_peak_um_10mm_s": (v.get("slow") or {}).get("10mm_s", {}).get("max_dev_um")} for k, v in (base or {}).items()}
    pick_x = bo_res["final"]["x"]
    pick = next((entry(r) for r in rows if r["x"] == pick_x), None)
    return {"front_with_feedforward": front, "front_stop_alone": ref, "pick_on_search_seeds": pick,
            "label": "SIM (P1, training seeds 300-309, 50 deg; tail = extra ink within 30 ms of a contact transition, 0.2 mm tolerance)"}


def magnet_field_calc(Br=1.32, R=0.5e-3, Lm=1.0e-3, z=1.5e-3):
    """On-axis field and gradient of an axially magnetised cylinder (CALC): B = Br/2 [(z+L)/sqrt((z+L)^2+R^2) - z/sqrt(z^2+R^2)]."""
    f = lambda z: Br / 2 * ((z + Lm) / math.hypot(z + Lm, R) - z / math.hypot(z, R))   # noqa: E731
    h = 1e-6
    return {"B_mT": f(z) * 1e3, "gradient_mT_per_mm": (f(z + h) - f(z - h)) / (2 * h) * 1e3 * 1e-3, "z_mm": z * 1e3, "Br_T": Br}


def write_all():
    adj, base, bo_res, sv, val = _load("adjoint"), _load("baseline"), _load("bo"), _load("servo"), _load("validate")
    final = bo_res["final"]
    law = final["x"]
    m = law["margin"]
    th50 = math.radians(50)
    kin = {"q_pre_mm_at_margin": {f"{t:g}deg": L.q_pre(m, math.radians(t)) * 1e3 for t in (35, 50, 75)},
           "contact_height_with_prepositioning_mm": {f"{t:g}deg": L.contact_height(m, math.radians(t), pre=law["pre"]) * 1e3 for t in (35, 50, 75)},
           "contact_height_without_mm": {f"{t:g}deg": L.contact_height(m, math.radians(t), pre=0.0) * 1e3 for t in (35, 50, 75)},
           "slide_tail_without_feedforward_mm": {f"{t:g}deg": L.slide_tail(m, math.radians(t)) * 1e3 for t in (35, 50, 75)},
           "travel_table": L.travel_table(), "brief_estimate_check": {
               "brief_q_pre_mm_at_0.30mm_50deg": math.sin(th50) * math.cos(th50) * 0.3,
               "calc_q_pre_mm_at_0.30mm_50deg": L.q_pre(0.3e-3, th50) * 1e3,
               "reason": "sin cos x margin is the law's gain on the housing-induced slide; with the refill on its stop the "
                         "pre-deflected ball lands higher up the descent, and the fixed point is margin x cot(theta)"},
           "loop_gain_without_removal": {f"{t:g}deg": L.contact_loop_gain_without_removal(math.radians(t)) for t in (35, 50, 75)},
           "air_iteration_gain": {f"{t:g}deg": L.air_loop_gain(math.radians(t)) for t in (35, 50, 75)},
           "label": "CALC (rigid kinematics, ball on the page, roll 0)"}
    val50 = _cfg_table(val, "50") if val else {}
    td = {
        "meta": provenance.metadata(p=_pencil_params(), evidence_status="simulation (pencil model P1 and a reduced torch model, synthetic handwriting; kinematics and "
                                    "loop margins by calculation; nothing measured)",
                                    seeds={"search": list(range(300, 310)), "held_out_training": list(range(310, 320)),
                                           "servo_search": list(range(300, 306)), "test": [200, 201, 202, 203]},
                                    extra={"model_version": "P1.0 + touchdown feed-forward (td_* parameters, default off)",
                                           "script": "opt/touchdown/run_study.py", "stage_caches": "results/opt/logs/td_*.json",
                                           "bo_logs": "results/opt/logs/ff_bo.jsonl, servo_bo_hall*.jsonl",
                                           "pipeline": "python3 -m opt.touchdown.run_study runs the stages adjoint, baseline, bo, servo, "
                                                       "validate, checks, viz, figures, report in order (--stages selects some; the "
                                                       "Bayesian searches resume from their logs); 'command' is the last invocation, "
                                                       "the stages were run in several invocations"}),
        "recommended": {"margin_mm": m * 1e3, "law": law, "fixed": bo_res["fixed"], "label": "PROPOSED DESIGN (tuned in SIM on training seeds)"},
        "kinematics": kin,
        "adjoint_reduced_model": adj and {
            "fits": {k: {"best": v.get("best"), "best_loss_um": v.get("best_loss_um"), "per_event_um": v.get("per_event_um")}
                     for k, v in adj["study"].items() if isinstance(v, dict) and "best" in v},
            "ideal_law_um": adj["study"]["ideal_law"]["mean_rms_ink_um"], "no_feedforward_um": adj["study"]["no_feedforward"]["mean_rms_ink_um"],
            "check_against_p1": {"ideal_law": adj["check_ideal_law"], "fitted_law": adj["check_fitted_law"],
                                 "no_feedforward": adj["check_no_feedforward"]},
            "label": "SIM (reduced torch model, down-up events at 0 and 20 mm/s, margin 0.30 mm; loss = RMS ink deviation in contact)"},
        "baseline_training": base and {k: {"agg": v["agg"], "slow": v.get("slow")} for k, v in base.items()},
        "pareto_tail_vs_ratio_vs_margin": _pareto_tail_ratio(bo_res, base),
        "search": {"n_evaluations": bo_res["n_evaluations"], "space": bo_res["space"], "ratio_cap": bo_res["ratio_cap"],
                   "rms_ref_um": bo_res["rms_ref_um"], "pareto_front": bo_res["front"], "search_pick": bo_res["search_pick"],
                   "holdout": bo_res["holdout"], "final": final, "priority": bo_res["priority"], "ablations": bo_res["ablations"],
                   "label": "SIM (P1, training seeds 300-309 search, 310-319 held out; 50 deg)"},
        "validation_test_seeds": val and {"per_theta": {th: _cfg_table(val, th) for th in val["summary"][next(iter(val["summary"]))]},
                                          "diag_published_metric_50deg": val["diag_published_metric"],
                                          "tilt_lag_proxy": val.get("tilt_lag_proxy"), "configs": val["configs"],
                                          "label": "SIM (P1, test seeds 200-203, first use)"},
        "mechanism_checks": _load("checks") and {k: v for k, v in _load("checks").items() if k != "meta"},
        "slide_sensor_option": {"p1_model": "P1 default: axial (slide) sensor sampled at 1 kHz with 1 ms delay, 2 um noise; the option "
                                            "case: 10 kHz with 0.1 ms delay (ax_decim 4, ax_delay 4), noise kept at 2 um",
                                "magnet_field_calc": magnet_field_calc(), "candidates": ["AMF-70 (TI DRV5055)", "AMF-71 (MDT TMR2615x-AAC)",
                                                                                          "AMF-72 (supermagnete S-01-01-N, 1 x 1 mm N45)"]},
        "definitions": {
            "extra_mm": "pencil ink more than 0.2 mm from anything the rigid pen drew on the same writing, per rigid pen-down",
            "extra_tr_mm": "the part within 30 ms of a contact transition of either pen (touchdown and lift tails; REQ-PNC-006)",
            "extra_in_mm": "the rest (in-stroke): the skid's device distortion, about 0.14 mm RMS from the rigid pen's letters",
            "missing_mm": "rigid-pen ink more than 0.2 mm from anything the pencil drew, per rigid pen-down",
            "extra_tr_tight_mm": "transition extra ink at a 0.1 mm tolerance",
            "per stroke": "per rigid pen-down, as sim/pencil/diag_touchdown_tails.py (the rigid pen's touchdown bounce counts; about 2 per word); "
                          "words_* divide by words instead",
            "oracle_ratio": "harness convention: e_rms(oracle, 6 Hz / 0.3 mm) / e_rms(neutral, same tremor), both against the same pencil "
                            "(with the same law) on the tremor-free writing",
            "limit_frac_contact": "fraction of contact time with the command at >= 95 % of the 0.30 mm soft limit, the drive saturated or the stage on its stop",
            "slow descents": "hand lowering the pen at 1 and 10 mm/s; peak and RMS deviation of the ink point from its working position under the housing"},
    }
    provenance.write_json(os.path.join(OUT, "touchdown.json"), r3(td))
    if sv:
        servo = {"meta": provenance.metadata(p=_pencil_params(), evidence_status="simulation (pencil model P1, synthetic handwriting and tremor; loop margins by calculation; nothing measured)",
                                             seeds={"search": list(range(300, 306)), "test": [200, 201, 202, 203]},
                                             extra={"script": "opt/touchdown/run_study.py (stage servo)", "front_stop": "tilt-range stop (P0.1.2), no feed-forward"}),
                 "rule": dict(sv["rule"], robustness="picks also keep a phase margin of at least the P0.1.2 servo's own worst case "
                                                     f"({sv['default_margins']['pm_min_deg']:.1f} deg) with the stage stiffness at +-20 % "
                                                     "and open-loop damping 0.02-0.1"),
                 "recommended": {"hall_1.0um": sv["hall_1.0um"]["best_tracking_at_default_power"],
                                 "label": "PROPOSED DESIGN (tuned in SIM on training seeds 300-305; margins by CALC)"},
                 "default": {"params": sv["default"], "margins": sv["default_margins"]},
                 "search": {k: {kk: vv for kk, vv in v.items() if kk != "all"} for k, v in sv.items() if k.startswith("hall_")},
                 "test_grid": val.get("servo_grid") if val else None,
                 "nominal_rule_pick_test_results": _load("validate_nominal_servo_pick"),
                 "with_touchdown_feedforward_test_seeds_50deg": {k: val50[k] for k in ("adaptive_ff", "adaptive_ff_tuned_servo") if k in val50},
                 "definitions": {"track_um": "mean of the RMS stage tracking error (q_r - q) in contact in the oracle run (6 Hz / 0.3 mm) and in "
                                             "the tremor-free NEUTRAL run (holding zero against the writing loads)",
                                 "P_rail_classB_mW": "mean drive-rail power, both axes, class-B / switch-to-rail stage (sim/pencil/power.py)"}}
        provenance.write_json(os.path.join(OUT, "servo.json"), r3(servo))
    write_evidence_rows(td, sv, val)
    return td


def write_evidence_rows(td, sv, val):
    rows = []
    fin = td["search"]["final"]
    law = fin["x"]
    v = td["validation_test_seeds"]["per_theta"] if td.get("validation_test_seeds") else {}
    v50 = v.get("50", {})
    base = td["baseline_training"] or {}

    def g(cfg, k, th="50", nd=3):
        try:
            return f"{v[th][cfg][k]:.{nd}f}"
        except Exception:
            return "n/a"
    common = {"year": "2026", "source_type": "derived simulation", "evidence_class": "numerical simulation", "access_level": "full text",
              "participants_or_bench": "none (simulation)", "retrieved": RETRIEVED, "search_query": "n/a (derived)", "stream": "ACT",
              "lead_verification": ""}
    diag = td["validation_test_seeds"]["diag_published_metric_50deg"] if td.get("validation_test_seeds") else {}
    rows.append(dict(common, **{
        "id": "ACT-56", "topic": "Touchdown and lift tails of the skid pencil removed by a stage feed-forward of the refill slide (this study)",
        "citation": "This ledger's simulation: opt/touchdown (law, runs, run_study), results/opt/touchdown.json",
        "doi_or_url": "results/opt/touchdown.json; docs/opt_touchdown.md",
        "task_or_setup": ("P1 on synthetic handwriting, test seeds 200-203 (first use), tilt 50/35/75 deg, 1 N; tremor-free and 6 Hz / 0.3 mm "
                          "(oracle, frozen Kalman); feed-forward q_ff = sin cos (s_ref - s_h) from the 1 kHz / 1 ms axial sensor with the "
                          "stage-induced slide removed, pre-positioning on the stop, contact-load bias switched at contact with integrator hand-over"),
        "comparator": "tilt-range front stop (P0.1.2); tilt-adaptive stop alone (DEC-022)",
        "key_quantitative_findings": (
            f"Extra ink at touchdown and lift per stroke (50 deg, 0.2 mm tolerance): tilt-range stop {g('tilt_range_stop', 'extra_tr_mm')}, "
            f"adaptive 0.30 mm {g('adaptive_0.30mm', 'extra_tr_mm')}, adaptive {law['margin'] * 1e3:.2f} mm + feed-forward {g('adaptive_ff', 'extra_tr_mm')} mm; "
            f"all extra ink (incl. in-stroke device distortion) {g('tilt_range_stop', 'extra_mm')} / {g('adaptive_0.30mm', 'extra_mm')} / {g('adaptive_ff', 'extra_mm')}; "
            f"missing {g('tilt_range_stop', 'missing_mm')} / {g('adaptive_0.30mm', 'missing_mm')} / {g('adaptive_ff', 'missing_mm')}; "
            f"oracle ratio {g('tilt_range_stop', 'oracle_ratio')} / {g('adaptive_0.30mm', 'oracle_ratio')} / {g('adaptive_ff', 'oracle_ratio')}; "
            f"published diagnostic (5 s runs): {diag.get('tilt_range_stop', {}).get('extra_ink_mm_per_stroke', float('nan')):.2f} / "
            f"{diag.get('adaptive_0.30mm', {}).get('extra_ink_mm_per_stroke', float('nan')):.2f} / {diag.get('adaptive_ff', {}).get('extra_ink_mm_per_stroke', float('nan')):.2f} mm per stroke. "
            f"Tails at 35 / 75 deg: {g('tilt_range_stop', 'extra_tr_mm', '35')} / {g('tilt_range_stop', 'extra_tr_mm', '75')}, "
            f"{g('adaptive_0.30mm', 'extra_tr_mm', '35')} / {g('adaptive_0.30mm', 'extra_tr_mm', '75')}, "
            f"{g('adaptive_ff', 'extra_tr_mm', '35')} / {g('adaptive_ff', 'extra_tr_mm', '75')} mm; oracle ratio at 35 deg "
            f"{g('tilt_range_stop', 'oracle_ratio', '35')} / {g('adaptive_0.30mm', 'oracle_ratio', '35')} / {g('adaptive_ff', 'oracle_ratio', '35')}. "
            f"Under 6 Hz / 0.3 mm tremor, tails with the oracle {g('tilt_range_stop', 'oracle_extra_tr_per_pd')} / "
            f"{g('adaptive_0.30mm', 'oracle_extra_tr_per_pd')} / {g('adaptive_ff', 'oracle_extra_tr_per_pd')} mm, with the frozen Kalman "
            f"(ratio about 1.0 here) {g('tilt_range_stop', 'kalman_extra_tr_per_pd')} / {g('adaptive_0.30mm', 'kalman_extra_tr_per_pd')} / "
            f"{g('adaptive_ff', 'kalman_extra_tr_per_pd')} mm"),
        "units_and_conditions": "mm of ink per rigid pen-down; ratio of ink-error RMS",
        "locator": "results/opt/touchdown.json validation_test_seeds", "limitations": (
            "Synthetic handwriting with a 60 ms pen-down ramp (touchdown at 50-60 mm/s); tilt constant within a run (the adaptive stop tracks "
            "it perfectly); friction, stage damping, sensor rates and hysteresis are assumptions; the in-stroke part of the metric sits at the "
            "skid's 0.14 mm device distortion, near the 0.2 mm tolerance"),
        "relevance_to_design": "Decides whether REQ-PNC-006 can be met by firmware on the adaptive-stop pencil",
        "transferability": "low", "transferability_reason": "Simulation only; contact and servo dynamics at touchdown are unmeasured (EXP-Q08)",
        "design_implication": "Adopt the adaptive stop with the feed-forward in firmware (touchdown state machine, 2 kHz law); verify on the Q06 rig (EXP-Q08)"}))
    pf = td["search"]
    rows.append(dict(common, **{
        "id": "ACT-57", "topic": "Front-stop margin against touchdown tails and correction with and without the feed-forward (this study)",
        "citation": "This ledger's simulation: opt/touchdown/study_bo.py (ParEGO Bayesian optimisation), results/opt/touchdown.json search",
        "doi_or_url": "results/opt/touchdown.json; results/opt/fig_td_pareto.png",
        "task_or_setup": f"P1, training seeds 300-309, 50 deg; {pf['n_evaluations']} evaluated laws x margins 0.10-0.40 mm (11 parameters); pick checked on seeds 310-319",
        "comparator": "adaptive stop alone at 0.1/0.2/0.3/0.4 mm",
        "key_quantitative_findings": (
            "Without feed-forward the margin trades tails against correction (training seeds: " +
            "; ".join(f"{k.replace('adaptive_', '')}: tail {vv['agg']['extra_tr_mm']:.3f} mm, ratio {vv['agg']['oracle_ratio']:.2f}"
                      for k, vv in base.items() if k.startswith("adaptive")) +
            f"). With the feed-forward the tails stay near {fin['agg']['extra_tr_mm']:.3f} mm per stroke while the margin is chosen for "
            f"correction: pick {law['margin'] * 1e3:.2f} mm, ratio {fin['agg']['oracle_ratio']:.2f} (held-out seeds)"),
        "units_and_conditions": "mm per rigid pen-down; oracle ratio at 6 Hz / 0.3 mm",
        "locator": "results/opt/touchdown.json search.pareto_front, search.final",
        "limitations": "One tilt in the search; tremor-free and one tremor condition; the objective weights are choices",
        "relevance_to_design": "Sets the stop margin (DEC-022) and shows the travel cost of pre-positioning",
        "transferability": "low", "transferability_reason": "Simulation only",
        "design_implication": (f"Set the adaptive stop margin to about {law['margin'] * 1e3:.2f} mm with the feed-forward (0.35-0.40 mm if "
                               f"correction matters more than slow touchdowns); the pre-positioning uses {law['pre']:.2f} x margin x cot(theta) "
                               f"of travel ({law['pre'] * L.q_pre(law['margin'], math.radians(50)) * 1e3:.2f} mm at 50 deg) only while the "
                               "refill rests on its stop")}))
    ab = pf["ablations"]
    rows.append(dict(common, **{
        "id": "ACT-58", "topic": "Stage compliance at touchdown: contact-load bias timing, integrator hand-over and early contact detection (this study)",
        "citation": "This ledger's simulation: sim/pencil/core.py td_* path, opt/touchdown/runs.py slow_descents, results/opt/touchdown.json ablations",
        "doi_or_url": "results/opt/touchdown.json",
        "task_or_setup": f"P1, held-out training seeds 310-319 (handwriting) and slow touchdowns at 1 and 10 mm/s, 50 deg, {law['margin'] * 1e3:.2f} mm stop",
        "comparator": "the picked law with one element removed at a time",
        "key_quantitative_findings": (
            "The contact load arrives as a step (0.13 N transverse at 1 N and 50 deg, 0.22 mm of static deflection of the 575 N/m stage); "
            "the servo integral (25 Hz corner) and the 1 kHz / 1 ms slide signal are too slow for it, so without a switched load bias the stage "
            "yields about 0.2 mm at each touchdown (seed 200). Tails per stroke at 0.2 / 0.1 mm tolerance and peak ink-point deviation "
            "in slow touchdowns at 1 / 10 mm/s: the picked law " +
            f"{fin['agg']['extra_tr_mm']:.3f} / {fin['agg']['extra_tr_tight_mm']:.3f} mm, {fin['slow']['1mm_s']['max_dev_um']:.0f} / "
            f"{fin['slow']['10mm_s']['max_dev_um']:.0f} um; with one element removed: " +
            "; ".join(f"{k.replace('_', ' ')} {vv['agg']['extra_tr_mm']:.3f} / {vv['agg']['extra_tr_tight_mm']:.3f} mm, "
                      f"{vv['slow']['1mm_s']['max_dev_um']:.0f} / {vv['slow']['10mm_s']['max_dev_um']:.0f} um" for k, vv in ab.items()) +
            f" (oracle ratio {fin['agg']['oracle_ratio']:.3f}; without the slide removal {ab.get('no_slide_removal', {}).get('agg', {}).get('oracle_ratio', float('nan')):.3f})"),
        "units_and_conditions": "mm per rigid pen-down; um peak deviation of the ink point from its working position",
        "locator": "results/opt/touchdown.json search.ablations",
        "limitations": "Contact stiffness, stop preload and bushing friction are assumptions; P1 has no stage-contact impact model beyond penalty contact",
        "relevance_to_design": "Shows what each firmware element buys and where a faster slide sensor helps",
        "transferability": "medium", "transferability_reason": "The mechanism (compliant stage, delayed contact signal) follows from the stage stiffness and sensor latency",
        "design_implication": "Switch the contact-load bias at contact with integrator hand-over and detect contact from the stage Hall error; "
                              "a 10 kHz slide sensor (AMF-70/71) adds little in P1 and is a fallback only"}))
    if sv:
        h1 = sv["hall_1.0um"]
        d0, bt, lp = h1["default"], h1["best_tracking_at_default_power"], h1["lowest_power_at_default_tracking"]
        grid = val.get("servo_grid", {}).get("hall_1.0um", {}) if val else {}
        rows.append(dict(common, **{
            "id": "ACT-59", "topic": "Inner piezo servo of the pencil stage tuned for tracking against rail power (this study)",
            "citation": "This ledger's simulation: opt/touchdown/servo.py, study_bo.servo_search, results/opt/servo.json",
            "doi_or_url": "results/opt/servo.json; results/opt/fig_td_servo.png",
            "task_or_setup": ("P1, servo 10 kHz; Bayesian optimisation over integral corner, damping, derivative filter, feedforward gain and a "
                              "proportional term under 1 um and 0.3 um Hall noise, training seeds 300-305; loop margins (ZOH, 0.1 ms, 2 kHz driver pole) "
                              "PM >= 45 deg, GM >= 10 dB, |S| <= 2 at open-loop damping 0.02-0.1, and PM no lower than the default's at "
                              "stiffness +-20 %; test grid 4-12 Hz x 0.1/0.3/0.5 mm x seeds 200-203"),
            "comparator": "P0.1.2 servo (25 Hz, zeta 0.4, 600 Hz filter)",
            "key_quantitative_findings": (
                f"Hall 1 um: default track {d0['res']['track_um']:.1f} um at {d0['res']['P_rail_classB_mW']:.0f} mW; best tracking at no more power "
                f"{bt['res']['track_um']:.1f} um at {bt['res']['P_rail_classB_mW']:.0f} mW ({', '.join(f'{k} {v:.3g}' for k, v in bt['x'].items())}; "
                f"phase margin {bt['margins']['pm_min_nominal_deg']:.1f} deg nominal and {bt['margins']['pm_min_deg']:.1f} deg at stiffness +-20 %, "
                f"gain margin {bt['margins']['gm_min_db']:.1f} dB, peak |S| {bt['margins']['peak_S_max']:.2f}; default "
                f"{sv['default_margins']['pm_min_nominal_deg']:.1f} / {sv['default_margins']['pm_min_deg']:.1f} deg, "
                f"{sv['default_margins']['gm_min_db']:.1f} dB, {sv['default_margins']['peak_S_max']:.2f}); "
                f"lowest power at default tracking {lp['res']['P_rail_classB_mW']:.0f} mW. Test grid mean oracle ratio "
                + ", ".join(f"{k} {vv['mean_ratio']:.3f} ({vv['mean_P_rail_classB_mW']:.0f} mW, limit {vv['mean_q_sat_frac']:.3f})" for k, vv in grid.items())
                + "; the gain is at 0.1 mm tremor (stage off its limit), none where the stage sits at its travel limit. With the adaptive stop "
                f"and the feed-forward (test seeds, 50 deg) the tuned servo halves the in-stroke extra ink ({g('adaptive_ff', 'extra_in_mm')} -> "
                f"{g('adaptive_ff_tuned_servo', 'extra_in_mm')} mm per stroke) and lowers the 35 deg oracle ratio "
                f"({g('adaptive_ff', 'oracle_ratio', '35')} -> {g('adaptive_ff_tuned_servo', 'oracle_ratio', '35')})"),
            "units_and_conditions": "um RMS stage tracking error in contact; mW class-B rail power; oracle ratio",
            "locator": "results/opt/servo.json", "limitations": "Stage damping, hysteresis and Hall noise are assumptions; the loop model has no contact stiffness",
            "relevance_to_design": "Servo settings for the firmware and the drive-power budget",
            "transferability": "medium", "transferability_reason": "Loop margins by calculation transfer once the stage is identified (EXP-Q04/Q07)",
            "design_implication": "Re-identify the stage on the bench, then retune with the same objective; keep the margins rule"}))
    adj = td.get("adjoint_reduced_model") or {}
    if adj:
        fits = adj["fits"]
        chk = adj["check_against_p1"]["ideal_law"].get("vx0", {})
        rows.append(dict(common, **{
            "id": "ACT-60", "topic": "Differentiable reduced touchdown model and adjoint gradients for the feed-forward law (this study)",
            "citation": "This ledger's simulation: opt/touchdown/reduced.py (torch, backpropagation through time)",
            "doi_or_url": "results/opt/touchdown.json adjoint_reduced_model; results/opt/fig_td_adjoint.png",
            "task_or_setup": ("Planar reduced model with P1 parameters (hand impedance, skid, refill slide, ball contact with tanh friction, stage "
                              "second-order, discrete sensors and servo); down-up events at 0 and 20 mm/s; Adam on adjoint gradients (checked "
                              "against central finite differences within 0.2 % at a 0.001 step; the loss is rough at a 2 % step)"),
            "comparator": "P1 on the same event; law structures with one element removed",
            "key_quantitative_findings": (
                f"RMS ink deviation in contact: no feed-forward {adj['no_feedforward_um']:.0f} um, ideal law {adj['ideal_law_um']:.0f} um, " +
                ", ".join(f"{k} {vv['best_loss_um']:.0f} um" for k, vv in fits.items() if vv.get('best_loss_um') is not None) +
                f". Agreement with P1 (ideal law, 0 mm/s): touchdown at {chk.get('touchdown_ms', {}).get('p1', float('nan')):.1f} ms (P1) and "
                f"{chk.get('touchdown_ms', {}).get('reduced', float('nan')):.1f} ms (reduced), slide RMS difference "
                f"{chk.get('slide_um', {}).get('rms_diff', float('nan')):.0f} um of a {chk.get('slide_um', {}).get('p1_range', float('nan')):.0f} um range. "
                "The reduced model's optimum, moved into P1, cut the slow-touchdown peak but raised the tail and the oracle ratio, so the "
                "Bayesian search on P1 sets the law"),
            "units_and_conditions": "um RMS; ms",
            "locator": "results/opt/touchdown.json adjoint_reduced_model",
            "limitations": "Reduced model: planar, no hysteresis or noise, regularised friction (raised for a stable adjoint); its optimum only seeds the P1 search",
            "relevance_to_design": "Identifies the elements of the law that matter (pre-positioning first, then the hand-over) before the P1 search",
            "transferability": "low", "transferability_reason": "Model-to-model; structure-level conclusions only",
            "design_implication": "Keep pre-positioning; the load bias must not over-compensate (integrator hand-over). The lead the reduced "
                                  "model liked (about 0.75 ms) did not pay in P1, where the 2 um slide noise dominates"}))
    mf = {"year": "2026", "source_type": "datasheet", "evidence_class": "manufacturer statement", "access_level": "full text",
          "participants_or_bench": "not applicable (manufacturer data; test method not published)", "retrieved": RETRIEVED, "stream": "AMF",
          "lead_verification": ""}
    mag = td["slide_sensor_option"]["magnet_field_calc"]
    rows.append(dict(mf, **{
        "id": "AMF-70", "topic": "Fast refill-slide sensor: ratiometric linear Hall sensor (TI DRV5055)",
        "citation": "Texas Instruments. DRV5055 Ratiometric Linear Hall-Effect Sensor, data sheet SBAS640C (January 2018, revised June 2026).",
        "doi_or_url": "https://www.ti.com/lit/gpn/DRV5055", "task_or_setup": "Electrical characteristics, 5.5; features p. 1",
        "comparator": "the 1 kHz / 1 ms / 2 um axial contact sensor assumed in P1",
        "key_quantitative_findings": ("Supply 3-3.63 V or 4.5-5.5 V; ICC 2 mA typ (4 max) at 3.3 V, 3 mA at 5 V; sensing bandwidth 20 kHz; propagation "
                                      "delay 10 us; input-referred noise density 215 nT/sqrt(Hz) at 3.3 V (130 at 5 V), 0.2 mT pk-pk over 20 kHz; sensitivity "
                                      "A1 60 mV/mT at 3.3 V (100 at 5 V, +-21 mT) down to A4; SOT-23 2.92 x 2.37 mm or TO-92. "
                                      f"MY CALC with AMF-72 at 1.5 mm: {mag['B_mT']:.0f} mT, gradient {abs(mag['gradient_mT_per_mm']):.0f} mT/mm, so 215 nT/sqrt(Hz) "
                                      f"over 5 kHz is about {215e-9 * math.sqrt(5000) / (abs(mag['gradient_mT_per_mm']) * 1e-3 / 1e-3) * 1e6:.2f} um RMS of slide"),
        "units_and_conditions": "typical values, TA 25 degC unless stated", "locator": "Section 5.5 Electrical Characteristics (p. 5); Features (p. 1)",
        "limitations": "2 mA at 3.3 V is 6.6 mW continuous; magnet and stage-Hall crosstalk; offset drift over temperature",
        "relevance_to_design": "Enables a 10 kHz slide measurement with about 0.1 ms latency for the touchdown feed-forward",
        "transferability": "high", "transferability_reason": "Catalogue part; the application (magnet on the refill) is conventional position sensing",
        "design_implication": "Candidate for a 10 kHz slide sensor on the refill collar; power it only while the pen is in use",
        "search_query": "TI DRV5055 ratiometric linear Hall effect sensor datasheet bandwidth 20 kHz noise"}))
    rows.append(dict(mf, **{
        "id": "AMF-71", "topic": "Fast refill-slide sensor, low power: TMR linear magnetic sensor (MultiDimension TMR2615x-AAC)",
        "citation": "MultiDimension Technology. TMR2615x-AAC Low Power Large Range TMR Linear Magnetic Sensor, datasheet version 1.3.4.",
        "doi_or_url": "https://www.dowaytech.com/en/res/202408/21/3fc42854d4f23bec.pdf ; https://tmr-sensors.com/products/tmr2615-low-power-large-range-tmr-linear-magnetic-sensor",
        "task_or_setup": "Electrical specifications, section 5", "comparator": "DRV5055 (AMF-70)",
        "key_quantitative_findings": ("VDD 1.71-5 V; ICC 240 uA typ at 3.3 V (200 at 1.8 V); bandwidth 30 kHz (-3 dB); linear range +-500 Gs (+-50 mT), "
                                      "sensitivity programmable 0.5-7 mV/V/Gs; nonlinearity 2 %FS, hysteresis 2 %FS typ; noise <= 10 mV pk-pk at 3.3 V over 5 kHz; "
                                      "power-on time 100 us max; DFN3L 1.6 x 1.6 x 0.5 mm or 2 x 2 x 0.55 mm; -40 to 85 degC"),
        "units_and_conditions": "TA 25 degC, VDD 1.71-5 V", "locator": "Section 5 Electrical Specifications (datasheet v1.3.4)",
        "limitations": ("2 %FS hysteresis: MY CALC up to about 60 um of slide if it applies to the full +-50 mT range at the 32 mT/mm "
                        "gradient of AMF-72, about 20 um if it scales with a +-0.5 mm span; sensitivity and offset are set to order; "
                        "distributor page lists no noise density"),
        "relevance_to_design": "Same speed as AMF-70 at about a tenth of the current and a smaller package",
        "transferability": "medium", "transferability_reason": "Catalogue part, but ordered to a programmed sensitivity; hysteresis needs a bench check",
        "design_implication": "Preferred slide sensor if its hysteresis is below about 10 um on the bench (the law needs changes, not absolute position)",
        "search_query": "MultiDimension TMR linear magnetic sensor datasheet low power TMR2615"}))
    rows.append(dict(mf, **{
        "id": "AMF-72", "topic": "Target magnet for the refill-slide sensor: 1 x 1 mm NdFeB N45 disc (supermagnete S-01-01-N)",
        "citation": "Webcraft AG (supermagnete). Data sheet article S-01-01-N, technical data and application safety.",
        "doi_or_url": "https://www.supermagnete.ch/eng/data_sheet_S-01-01-N.pdf", "source_type": "manufacturer",
        "task_or_setup": "Technical information, section 1", "comparator": "none",
        "key_quantitative_findings": (f"Diameter 1 mm, height 1 mm (+-0.1 mm), axial magnetisation, N45, Br 1.32-1.37 T, bHc 860-995 kA/m, iHc >= 955 kA/m, "
                                      f"(BH)max 342-358 kJ/m3, 0.006 g, max working temperature 80 degC, Ni-Cu-Ni coating. MY CALC (on-axis cylinder formula, "
                                      f"Br 1.32 T): {mag['B_mT']:.1f} mT and {abs(mag['gradient_mT_per_mm']):.1f} mT/mm at 1.5 mm"),
        "units_and_conditions": "manufacturer data", "locator": "Data sheet page 1, section 1",
        "limitations": "80 degC limit; field at the stage Hall sensors must be checked (crosstalk); holding force irrelevant here",
        "relevance_to_design": "Gives the field gradient the slide-sensor resolution estimate uses",
        "transferability": "high", "transferability_reason": "Catalogue magnet",
        "design_implication": "Glue to the refill collar about 1.5 mm from the slide sensor; keep it away from the stage Hall sensors",
        "search_query": "supermagnete S-01-01-N cylinder magnet 1 mm x 1 mm N45 remanence data sheet"}))
    path = os.path.join(OUT, "touchdown_evidence_rows.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EVIDENCE_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in EVIDENCE_HEADER})
    return path
