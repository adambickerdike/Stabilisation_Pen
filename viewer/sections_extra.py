"""AI-guidance, sim-to-real and inertial-helper tables for viewer/index.html (rendered at build time).

Reads results/ai/*.json (aiguide, app/penapp/autocorrect.py), results/s2r/*.json (s2r) and
results/pencil/inertial.json (sim/handpen).  Missing inputs skip the section.
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


def _rng(v, nd=2):
    return f"{v[0]:.{nd}f}–{v[1]:.{nd}f}"


def _pct_rng(v):
    return f"{100 * v[0]:.0f}–{100 * v[1]:.0f} %"


def _drag0(d):
    try:
        v = d["time_domain"]["passive"]["unmodified"]["drag_N"]
        vals = [x["mean"] for x in v.values()] if isinstance(v, dict) else [v]
        return f"{sum(vals) / len(vals):.2f} N"
    except (KeyError, TypeError, ZeroDivisionError):
        return "—"


def inertial(root):
    d = _load(root, "results/pencil/inertial.json")
    if not d or "headline" not in d:
        return ""
    h, b = d["headline"], d["budgets"]
    orc, sat = h["ink_error_ratio_oracle"], h["stage_time_at_limit"]
    a = "0.3mm"
    rows = [
        ["Piezo nib stage (current design)", _rng(orc["stage"][a]), "—", _pct_rng(sat["stage"][a]), "in the CAD"],
        ["Tungsten slug in the cap, pushed on 3 axes (5.15 g)", _rng(orc["rm_slug3"][a]), _rng(orc["stage+rm_slug3"][a]),
         _pct_rng(sat["stage+rm_slug3"][a]),
         f"pen {b['rm_slug3']['pen_mass_g']:.1f} g; takes {100 * (1 - b['rm_slug3']['cell_capacity_left']):.0f} % of the cell"],
        ["Two pairs of gyroscopes on motorised gimbals", _rng(orc["cmg_2ax"][a]), _rng(orc["stage+cmg_2ax"][a]),
         _pct_rng(sat["stage+cmg_2ax"][a]),
         f"pen {b['cmg_2ax']['pen_mass_g']:.1f} g; no room left for the cell"],
    ]
    lede1 = ("Can a moving weight or a gyroscope in the cap steady the pen? Ink error left at 0.3 mm tremor, 4–12 Hz, as a fraction of "
             "no correction, with perfect knowledge of the tremor (an upper bound). The hand pushes the pen around with about "
             "0.17 N through the grip; a few grams moving ±1 mm in the cap push back with only 2–30 mN, and a gyroscope only resists "
             "the pen's rotation, which is tiny. Helpers matter only where the stage runs out of travel.")
    t1 = _section("Weights and gyroscopes in the cap", _tags("SIM", "CALC"), lede1,
                  _table(["Helper", "Ink error left, alone", "With the nib stage", "Stage time at its limit", "Cost"], rows, (1, 2, 3)),
                  "results/pencil/inertial.json (sim/handpen/, hand-pen model H1; docs/inertial_stabilisation.md)")
    ps = h["passive_0.3mm"]
    lab = [("skid_mu_0.25", "Skid friction 0.25 (now 0.12)"), ("skid_mu_0.40", "Skid friction 0.40"),
           ("viscous_10", "Damped roller at the nose, 10 N s/m"), ("grip_soft_x0.5", "Soft grip sleeve, half the grip stiffness"),
           ("grip_soft_x0.25", "Soft grip sleeve, a quarter"), ("cap_10g", "10 g heavier cap"), ("tmd_8Hz", "Tuned mass damper, 8 Hz"),
           ("gyro_30k", "Spinning gyroscope, 30 000 rpm")]
    rows2 = [["Pencil as designed (skid friction 0.12, normal grip)", "1", "1", "100 %", _drag0(d)]]
    for k, l in lab:
        v = ps.get(k)
        if not v:
            continue
        rows2.append([l, _rng(v["in_band_tremor"]), _rng(v["net_in_band_vs_intended"]),
                      f"{100 * v['letters_vs_unmodified']:.0f} %", f"{v['drag_N']:.2f} N"])
    lede2 = ("Passive ways to steady the pen at the paper or in the grip, relative to the pencil as designed (0.3 mm tremor, "
             "4–12 Hz). Tremor and handwriting strokes share frequencies, so whatever filters the tremor also shrinks and "
             "delays the letters: against what the writer meant, the net change is close to nothing.")
    t2 = _section("Pivots at the paper and in the grip", _tags("SIM"), lede2,
                  _table(["Option", "Tremor in the ink", "Net error against the intended writing", "Letter size", "Drag felt"],
                         rows2, (1, 2, 3, 4)),
                  "results/pencil/inertial.json passive (docs/inertial_stabilisation.md §5.6)")
    return t1 + t2
