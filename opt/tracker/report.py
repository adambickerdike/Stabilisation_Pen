"""Assemble results/opt/tracker.json, the figures and the ledger rows from the stage files (SIMULATION/CALCULATION)."""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List

import numpy as np

import opt.tracker as OT
from opt.tracker import RESULTS, EVIDENCE_SIM
from opt.tracker import run_study as RS

HEAD = [("neutral", "No correction"), ("oracle", "Oracle: whole disturbance (limit, not an estimator)"),
        ("oracle_band", "Tremor-band oracle (3-15 Hz, not causal)"), ("kfosc_internal", "Frozen Kalman (core)"),
        ("akf_grid", "AKF, random search on the grid's writing"), ("akf_robust", "AKF, random search, robust"),
        ("gru_old", "GRU, whole-disturbance target (previous)")]


SHIP_SHORT = {"rep_robust": "AKF, robust objective re-optimised by the adjoint",
              "rep_grid": "AKF, grid objective re-optimised by the adjoint",
              "gru_band": "GRU, tremor-band target", "hybrid": "AKF + learned gate"}


def _g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def headline(test: Dict, labels: List[tuple]) -> List[Dict]:
    gs = test["grid"]["summary"]
    ai = test["aiguide"]["summary"]
    rows = []
    alias = {"oracle": "oracle_disturbance"}
    for lab, text in labels:
        g = gs.get(lab, {})
        a = ai.get(alias.get(lab, lab), {})
        rows.append({"label": lab, "name": text,
                     "grid_band_ratio": g.get("band_ratio_mean"), "grid_ratio": g.get("ratio_mean"),
                     "grid_path_um": g.get("path_um_mean"), "grid_intent_err_um": g.get("intent_err_um_mean"),
                     "grid_distortion_um": g.get("distortion_um_mean"),
                     "grid_residual_ratio_low": g.get("residual_ratio_low_mean"),
                     "grid_q_sat": g.get("q_sat_frac_mean"), "grid_P_rail_mW": g.get("P_rail_classB_mW_mean"),
                     "ai_path_wo_um": _g(a, "wo_path_rms_um", "mean"), "ai_path_wo_sd": _g(a, "wo_path_rms_um", "sd"),
                     "ai_recognition_wo": _g(a, "wo_recognition_accuracy", "mean"), "ai_ratio": _g(a, "ratio", "mean"),
                     "ai_band_ratio": _g(a, "band_ratio", "mean"), "ai_distortion_um": _g(a, "distortion_um", "mean"),
                     "ai_false_correction_um": _g(a, "false_correction_um", "mean")})
    # tremor-free references for the path metrics
    nt = [r for r in test["grid"]["rows"] if r["label"] == "neutral_no_tremor"]
    return rows, {"grid_path_um_no_tremor": float(np.mean([r["path_um"] for r in nt])) if nt else None,
                  "grid_intent_err_um_no_tremor": float(np.mean([r["intent_err_um"] for r in nt])) if nt else None,
                  "ai_path_wo_um_no_tremor": _g(ai, "neutral_no_tremor", "wo_path_rms_um", "mean")}


def fmt_table(rows: List[Dict]) -> str:
    def f(x, nd=3):
        return "–" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.{nd}f}"
    out = ["| Tracker | Test-grid 3-15 Hz ratio | Test-grid all-band ratio | Distortion, grid writing (µm) | "
           "Distortion, glyph writing (µm) | Path to intended letters, grid (µm) | Time-aligned intent error, grid (µm) | "
           "aiguide path RMS, writing only (µm) | aiguide recognition |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['name']} | {f(r['grid_band_ratio'])} | {f(r['grid_ratio'])} | {f(r['grid_distortion_um'], 0)} | "
                   f"{f(r['ai_distortion_um'], 0)} | {f(r['grid_path_um'], 0)} | {f(r['grid_intent_err_um'], 0)} | "
                   f"{f(r['ai_path_wo_um'], 0)} | {f(r['ai_recognition_wo'], 3)} |")
    return "\n".join(out)


def write_all(ship_label: str = None, ship_text: str = None):
    from opt.tracker import figures as FG
    stages = {n: RS.load_stage(n) for n in ("check", "gradscan", "sweep", "select", "learned", "personal", "personal_fc",
                                            "test", "budget", "replicate", "report_choice")}
    test = stages["test"]
    sel = stages["select"] or {}
    choice = stages["report_choice"] or {}
    ship = ship_label or choice.get("ship") or _g(sel, "selection", "chosen")
    labels = list(HEAD)
    pts = sorted(stages["sweep"]["points"], key=lambda p: (p["chain"], p["lam_fc"])) if stages["sweep"] else []
    for p in pts:
        labels.append((RS.point_label(p), f"AKF, adjoint, chain {p['chain']}, λ_fc {p['lam_fc']:g}" +
                       (" (validation-best iterate)" if p.get("kind") == "valbest" else "")))
    for lab, text in (("rep_grid", "AKF, random search's grid objective re-optimised by the adjoint"),
                      ("rep_robust", "AKF, random search's robust objective re-optimised by the adjoint"),
                      ("gru_band", "GRU, tremor-band target (this study)"), ("hybrid", "AKF + learned authority gate (this study)")):
        if test and lab in test["grid"]["summary"]:
            labels.append((lab, text))
    labels = [(lab, text + (" (ship)" if lab == ship else "")) for lab, text in labels]
    rows, refs = headline(test, labels) if test else ([], {})
    out = {"meta": RS.meta(EVIDENCE_SIM, {"test": list(OT.TEST_SEEDS), "aiguide_test_writers": list(OT.AIGUIDE_TEST_WRITERS),
                                          "training": "fusion.learned._spec(i, 'train'), i < 400", "validation": "fusion val specs; tuning seeds 5000-5007; aiguide writers 100-105",
                                          "sensor_streams": "30_000_000 + 10 i (training), harness seeds (test)"}),
           "summary": {"ship": ship, "ship_text": ship_text or choice.get("ship_title"), "headline": rows, "references": refs,
                       "headline_markdown": fmt_table(rows) if rows else None},
           "seed_plan": {"test_grid": list(OT.TEST_SEEDS), "test_tremor_streams": [s + 1000 for s in OT.TEST_SEEDS],
                         "aiguide_test_writers": list(OT.AIGUIDE_TEST_WRITERS),
                         "training_pairs": "fusion.learned._spec(i, 'train'), i < 400 (seeds 6000 + i sigma-lognormal, 16000 + i glyph for i % 10 in 2, 5, 8); AKF: 96 + 64 of them (40 % glyph), GRU: all 400 (30 % glyph)",
                         "validation": "fusion.learned._spec(j, 'val'), j < 24; tuning seeds 5004-5007 (open loop); aiguide tuning writers 100-105",
                         "selection_closed_loop": "tuning seeds 5000-5003 x 15 conditions; aiguide tuning writers 100-105 (fusion.tune.AI_TUNE)",
                         "replication_of_random_search": "fusion.tune data: tuning seeds 5000-5007 (sensor tags 7/8), aiguide writers 100-105",
                         "personal": "calibration = seed + 40000; prior weight chosen on tuning seeds 5000-5003; test seeds 200-203 at 0.3 mm",
                         "personal_fc": "as personal; false-correction term on 6 tremor-free training recordings (fusion.learned._spec train pairs); its weight chosen on tuning seeds 5000-5003",
                         "training_streams": "30_000_000 + 10 i (+1 tremor-free), validation 35_000_000 + 10 j"},
           "check": stages["check"], "gradient_scan": stages["gradscan"], "sweep": stages["sweep"], "selection": sel,
           "replicate": stages["replicate"], "learned": stages["learned"], "personal": stages["personal"],
           "personal_fc": stages["personal_fc"], "budget": stages["budget"],
           "test": {"grid_summary": test["grid"]["summary"], "aiguide_summary": test["aiguide"]["summary"],
                    "specs": test["specs"]} if test else None}
    from stabpen import provenance
    provenance.write_json(os.path.join(RESULTS, "tracker.json"), RS._r(out))
    # the shipped AKF parameters on their own (numba / firmware parameter names of fusion.estimators.akf)
    if test and ship:
        sp = [x for x in test["specs"] if x["label"] == ship]
        if sp:
            provenance.write_json(os.path.join(OT.MODEL_DIR, "akf_ship.json"), RS._r(
                {"meta": RS.meta(EVIDENCE_SIM, {"selection": list(OT.TUNE_SEEDS[:4]), "test": list(OT.TEST_SEEDS)}),
                 "label": ship, "estimator": sp[0]["name"], "title": choice.get("ship_title"), "note": choice.get("ship_note"),
                 "rule": choice.get("rule"), "params": sp[0]["params"],
                 "sensors": {"page": "1k", "comp": "gyro"},
                 "test_summary": next((r for r in rows if r["label"] == ship), None)}))
    # figures
    if test:
        fl = [("oracle_band", "tremor-band oracle (not causal)"), ("akf_grid", "AKF, random search, grid writing"),
              ("akf_robust", "AKF, random search, robust")]
        if ship:
            fl.append((ship, SHIP_SHORT.get(ship, "AKF, adjoint-tuned") + " (ship)"))
        for lab, text in (("hybrid", "AKF + learned gate"), ("gru_band", "GRU, tremor-band target")):
            if lab in test["grid"]["summary"]:
                fl.append((lab, text))
        FG.fig_ratio_vs_frequency(test["grid"]["summary"], fl)
        pp = []
        for p in [q for q in pts if q.get("kind", "last") == "last"]:
            lab = RS.point_label(p)
            g = test["grid"]["summary"].get(lab, {})
            a = test["aiguide"]["summary"].get(lab, {})
            pp.append({"chain": p["chain"], "lam": p["lam_fc"], "band": g.get("band_ratio_mean"),
                       "dist_grid": g.get("distortion_um_mean"), "dist_glyph": _g(a, "distortion_um", "mean")})
        others = []
        for lab, text, short, off in (("akf_grid", "AKF, random search, grid writing", "grid-tuned", (-6, 4, "right")),
                                      ("akf_robust", "AKF, random search, robust", "robust", (-6, 5, "right")),
                                      ("gru_old", "GRU, whole-disturbance target", "GRU old", (6, -9, "left")),
                                      ("gru_band", "GRU, tremor-band target", "GRU band", (6, -9, "left")),
                                      ("hybrid", "AKF + learned gate", "hybrid", (6, -9, "left")),
                                      ("rep_grid", "adjoint on the random search's grid objective", "adj. grid obj.", (6, -9, "left")),
                                      ("rep_robust", "adjoint on the random search's robust objective", "adj. robust obj.", (6, -9, "left"))):
            if lab == ship:
                text, short = text + " (ship)", short + " (ship)"
            g = test["grid"]["summary"].get(lab)
            a = test["aiguide"]["summary"].get(lab)
            if g and a:
                others.append({"label": text, "short": short, "offset": off, "band": g.get("band_ratio_mean"),
                               "dist_grid": g.get("distortion_um_mean"), "dist_glyph": _g(a, "distortion_um", "mean")})
        FG.fig_pareto(pp, others)
    if stages["sweep"]:
        sp = []
        for p in [q for q in stages["sweep"]["points"] if q.get("kind", "last") == "last"]:
            vh = [(h["iter"], h["J_val"]) for h in p["history"] if "J_val" in h]
            sp.append({"chain": p["chain"], "lam": p["lam_fc"], "iters": p["iters"], "val_hist": vh,
                       "order": p["lam_fc"]})
        FG.fig_training(sp, stages["learned"] or {})
    if stages["personal"]:
        FG.fig_personal(stages["personal"], stages["personal_fc"])
    from opt.tracker import evidence as EVD
    EVD.write()
    return out


# ------------------------------------------------------------------ Markdown tables for docs/opt_tracker.md
def md_tables() -> str:
    """All tables of the doc from results/opt/tracker.json (printed by `python3 -m opt.tracker.report`)."""
    R = json.load(open(os.path.join(RESULTS, "tracker.json")))
    out = []

    def f(x, nd=3):
        return "–" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.{nd}f}"
    S = R["summary"]
    out.append("### Headline (test data)\n\n" + (S.get("headline_markdown") or ""))
    rf = S.get("references", {})
    out.append(f"\nTremor-free references: path {f(rf.get('grid_path_um_no_tremor'), 0)} µm, time-aligned intent error "
               f"{f(rf.get('grid_intent_err_um_no_tremor'), 0)} µm (grid); aiguide path writing only {f(rf.get('ai_path_wo_um_no_tremor'), 0)} µm.")
    sel = R.get("selection") or {}
    if sel:
        g = sel["grid_summary"]; a = sel["aiguide_summary"]
        rows = ["| Point | tuning-grid 3-15 Hz ratio | tuning-grid ratio | distortion, tuning writing (µm) | distortion, tuning glyph writers (µm) | "
                "aiguide tuning path, writing only (µm) | eligible |", "|---|---|---|---|---|---|---|"]
        for lab in ["akf_grid", "akf_robust"] + [p["label"] for p in sel["points"]] + [k for k in g if k.startswith("rep_")]:
            if lab not in g:
                continue
            rows.append(f"| {lab} | {f(g[lab].get('band_ratio_mean'))} | {f(g[lab].get('ratio_mean'))} | {f(g[lab].get('distortion_um_mean'), 1)} | "
                        f"{f(_g(a, lab, 'distortion_um', 'mean'), 1)} | {f(_g(a, lab, 'wo_path_rms_um', 'mean'), 1)} | "
                        f"{'reference' if lab in ('akf_grid', 'akf_robust') else ('yes' if lab in sel['selection']['eligible'] else 'no')} |")
        rows.append(f"| no correction | 1 | 1 | – | – | {f(_g(a, 'neutral', 'wo_path_rms_um', 'mean'), 1)} | |")
        out.append("### Selection (closed loop, tuning data)\n\n" + "\n".join(rows) + f"\n\nChosen: **{sel['selection']['chosen']}**")
    rp = R.get("replicate") or {}
    if rp:
        rows = ["| Objective | random-search set: J (fusion.tune) | adjoint result: J (fusion.tune code) | iterations | terms before → after |",
                "|---|---|---|---|---|"]
        for k in ("grid", "robust"):
            if k in rp:
                a0 = rp[k]["start_reference"]; a1 = rp[k]["result_reference"]
                terms = ", ".join(f"{q} {f(a0.get(q), 4)} → {f(a1.get(q), 4)}" for q in a0 if q != "J")
                rows.append(f"| {k} | {f(a0['J'], 4)} | {f(a1['J'], 4)} | {rp[k].get('best_iter')} | {terms} |")
        out.append("### Random search's objectives, re-optimised\n\n" + "\n".join(rows))
    ps = R.get("personal") or {}
    if ps:
        tg = ps["test"]["grid_summary"]
        rows = ["| Set | 3-15 Hz ratio 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz | mean | path (µm) | distortion (µm) |", "|---|---|---|---|---|---|---|---|---|"]
        pf = R.get("personal_fc") or {}
        tg = dict(tg)
        dist = dict(ps["test"]["distortion_um"])
        if pf:
            tg.update(pf["test"]["grid_summary"])
            dist["akf_personal_adjoint_fc"] = pf["test"]["distortion_um"]
        for lab in ("akf_robust", "akf_personal", "akf_personal_adjoint", "akf_personal_adjoint_fc", "oracle_band"):
            if lab not in tg:
                continue
            by = tg.get(lab, {}).get("by_condition", {})
            cells = [f(by.get(f"{fq:g}Hz_0.3mm", {}).get("band_ratio", {}).get("mean")) for fq in (4.0, 6.0, 8.0, 10.0, 12.0)]
            rows.append(f"| {lab} | " + " | ".join(cells) + f" | {f(tg.get(lab, {}).get('band_ratio_mean'))} | {f(tg.get(lab, {}).get('path_um_mean'), 0)} | "
                        f"{f(dist.get(lab), 0) if lab in dist else '–'} |")
        out.append("### Personalisation (test seeds, 0.3 mm)\n\n" + "\n".join(rows) + f"\n\nPrior weight chosen on tuning seeds: {ps.get('rho_chosen')}; "
                   f"tuning summary: {json.dumps({k: round(v, 3) for k, v in ps['tuning']['summary'].items()})}")
        if pf:
            out.append("FC variant, tuning (band residual, open-loop false correction um): " +
                       json.dumps({k: {q: round(v, 3) for q, v in d.items()} for k, d in pf["tuning_summary"].items()}) +
                       f"; chosen lambda_fc,p = {pf['lam_chosen']}")
    gs = R.get("gradient_scan") or {}
    if gs:
        rows = ["| Parameter | adjoint slope at 0 | largest difference between the two implementations along the scan | largest step not explained by the slope | steps with a jump > 1e-4 |",
                "|---|---|---|---|---|"]
        for s in gs["scan"]:
            j = s["jumps_adjoint_path"]
            rows.append(f"| {s['param']} | {s['adjoint_slope_at_0']:.4g} | {s['max_abs_diff_paths']:.1e} | {j['max_abs_step_residual']:.1e} | "
                        f"{j['n_steps_residual_gt_1e-4']} of {j['n_steps']} |")
        ss = gs["small_step"]
        rows.append(f"\nTiny-step central differences (h = {ss['h']:g}, single recordings, {ss['n']} parameter-recording pairs): "
                    f"largest relative error {ss['max_rel_err_nonzero']:.1e} (median {ss['median_rel_err_nonzero']:.1e}) over the "
                    f"{ss['n'] - ss['n_both_zero']} pairs with a non-zero gradient; {ss['n_both_zero']} pairs are zero in both (f_min never reached).")
        out.append("### Gradient scan (core parameters)\n\n" + "\n".join(rows))
    return "\n\n".join(out)


if __name__ == "__main__":
    print(md_tables())
