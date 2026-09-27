"""AI-guidance and sim-to-real tables for viewer/index.html (rendered at build time).

Reads results/ai/*.json (aiguide, app/penapp/autocorrect.py) and results/s2r/*.json
(s2r).  Missing inputs skip the section.
"""
from __future__ import annotations

from viewer.sections import _e, _load, _section, _table, _tags

SET_LABEL = {"in_domain": "Held-out sentences", "notes": "Note-like lines", "rare": "Lines with names and rare words"}


def _pct(x, nd=0):
    return f"{100 * x:.{nd}f} %"


def autocorrect(root):
    a = _load(root, "results/ai/autocorrect.json")
    if not a:
        return ""
    thr = str(a["setup"]["default_threshold"])
    rows = []
    for sname, lab in SET_LABEL.items():
        v = a["by_set"].get(sname)
        if not v:
            continue
        for mode in ("lexicon", "personal"):
            if mode not in v or (mode == "personal" and sname != "rare"):
                continue
            cells = []
            for c, x in v[mode].items():
                t = x["thresholds"][thr]
                cells.append(f"{_pct(t['wer_before'])} → <b>{_pct(t['wer_after'])}</b>")
            over = max(x["thresholds"][thr]["over_correction_rate"] for x in v[mode].values())
            rows.append([lab + (" + personal dictionary" if mode == "personal" else "")] + cells + [f"≤ {_pct(over, 1)}"])
    cers = [f"CER {100 * x['achieved_cer']:.1f} %" for x in a["by_set"]["in_domain"]["lexicon"].values()]
    demo = ", ".join(f"<code>{_e(c['from'])}</code> → <code>{_e(c['to'])}</code> ({c['posterior']:.2f})" for c in a["demo"]["changes"])
    lede = ("The app corrects the recognised text with a language model and stores the result as a derived layer that cites the "
            "strokes; the ink itself is never changed. Recognition errors are injected at the character error rates shown "
            f"(synthetic sessions, CC0 text). A word is changed only if the corrector is at least {float(thr):.0%} sure. "
            f"Example changes on a shopping-list note, with the corrector's confidence: {demo}.")
    return _section("Digital autocorrect in the app", _tags("CALC"), lede,
                    _table(["Text"] + [f"Word errors, {c}" for c in cers] + ["Correct words changed"], rows, (1, 2, 3, 4, 5)),
                    "results/ai/autocorrect.json (app/penapp/autocorrect.py; docs/ai_guidance.md §6)")


CONFIG_LABEL = {"pencil_P1": "Pencil model P1", "revA": "Rev A limits (M1)", "pencil_like": "Pencil limits (M1)",
                "pencil_0.3N": "Pencil limits, 0.3 N (M1)"}
CONDITIONS = [("neutral", "No guidance"), ("oracle", "Oracle template (the true intended path)"),
              ("ai_correct", "AI template, letter predicted correctly"), ("ai_predicted", "AI prediction, confidence-gated"),
              ("wrong_letter_full", "Wrong letter at full authority")]


def guidance(root):
    g = _load(root, "results/ai/guidance.json")
    if not g or "summary" not in g:
        return ""
    cfgs = [c for c in CONFIG_LABEL if c in g["summary"]]
    rows = []
    for key, lab in CONDITIONS:
        cells = []
        for c in cfgs:
            v = g["summary"][c].get(key, {}).get("path_rms_um", {}).get("mean")
            cells.append("—" if v is None else f"{v:.0f} µm")
        rows.append([lab] + cells)
    be = g.get("breakeven", {}).get("by_config", {})
    lede = ("Path distance from the ink to the intended letters (RMS over synthetic writers and tremor frequencies). "
            "The app predicts letters two ahead, draws them in the writer's estimated style and the pen is pulled toward that "
            "template within its travel. A correctly predicted letter in the writer's style is still about 300 µm from what "
            "they meant, which is where guidance stops paying off; wrong predictions stay bounded by the travel.")
    return _section("Physical guidance toward AI-predicted letters", _tags("SIM"), lede,
                    _table(["Condition"] + [CONFIG_LABEL[c] for c in cfgs], rows, tuple(range(1, len(cfgs) + 1))),
                    "results/ai/guidance.json (aiguide/guidance.py; docs/ai_guidance.md §4)")


def ai(root):
    return guidance(root) + autocorrect(root)


PARAMS = [("actuator.Kf", "Force constant K<sub>f</sub>", "EXP-B03"), ("actuator.R20", "Coil resistance", "EXP-B03"),
          ("actuator.L", "Coil inductance", "EXP-B03"), ("stage.k_tip", "Stage stiffness", "EXP-B05"),
          ("stage.m_eq", "Tip-equivalent mass", "EXP-B05"), ("stage.zeta_open", "Stage damping", "EXP-B05"),
          ("writing.mu_eff", "Nib friction coefficient", "EXP-B01/B02"), ("writing.paper_stiffness", "Paper contact stiffness", "EXP-B01/B02"),
          ("friction.x_presliding", "Pre-sliding length", "EXP-B02"), ("writing.stribeck_speed", "Stribeck speed", "EXP-B02")]


def s2r(root):
    c1 = _load(root, "results/s2r/c1_identification.json")
    c2 = _load(root, "results/s2r/c2_twin.json")
    if not c1 or not c2:
        return ""
    sm = c1["summary"]
    rows = [[lab, exp, f"{100 * sm[k]['rel_err']['abs_p95']:.1f} %", f"{100 * sm[k]['coverage95']:.0f} %"] for k, lab, exp in PARAMS if k in sm]
    bt = c1["bench_time_s_median"]
    lede1 = ("Twin experiments: 15 hidden plants (5 partly outside the declared ranges) are measured through models of the "
             "instruments the bench protocols name, and the identification sees only the recorded data. This shows the "
             "method works and what it costs; only the bench can show the simulator's structure is right. Median bench time "
             f"at protocol settings: EXP-B03 {bt['B03'] / 60:.0f} min per coil coupon, EXP-B05 {bt['B05'] / 60:.0f} min per "
             f"stage build, EXP-B01/B02 {bt['B01B02'] / 60:.0f} min per ink, paper and underlay (about 33 min with the reduced grid "
             "at the same accuracy).")
    t1 = _section("Calibrating the simulator from bench data", _tags("SIM", "CALC"), lede1,
                  _table(["Parameter", "Experiment", "Error, 95th percentile", "Truth inside the stated U95"], rows, (2, 3)),
                  "results/s2r/c1_identification.json (s2r/; docs/sim_to_real.md s3)")
    g = c2["gaps"]
    conds = [("before", "Uncalibrated (nominal parameters)"), ("after", "Calibrated, hand simulant known to ±10 %"),
             ("after_plus", "Calibrated, plus sensor parameters")]
    mets = [("oracle_ratio@6Hz", "Physical-limit ratio, 6 Hz"), ("oracle_ratio@9Hz", "Physical-limit ratio, 9 Hz"),
            ("kfosc_ratio@6Hz", "Estimator ratio, 6 Hz"), ("kfosc_ratio@9Hz", "Estimator ratio, 9 Hz")]
    rows2 = []
    for key, lab in mets:
        rows2.append([lab] + [f"{round(15 * g[c][key]['frac_within_0.1'])} of 15" for c, _l in conds])
    rows2.append(["Static hold power, 95th-percentile error"] + [f"{100 * g[c]['static_hold_W']['abs_p95']:.0f} %" for c, _l in conds])
    rows2.append(["Uncorrected ink error at 9 Hz, 95th-percentile error"] + [f"{100 * g[c]['neutral_e_um@9Hz']['abs_p95']:.0f} %" for c, _l in conds])
    lede2 = ("How many of the 15 hidden plants the twin predicts within ±0.1 of the true ratio (the AC-B09-03 tolerance), "
             "before and after calibrating it from the virtual bench runs above (12 test seeds per plant).")
    t2 = _section("Does the calibrated twin predict the real plant", _tags("SIM"), lede2,
                  _table(["Prediction"] + [l for _c, l in conds], rows2, (1, 2, 3)),
                  "results/s2r/c2_twin.json (docs/sim_to_real.md s4)")
    return t1 + t2
