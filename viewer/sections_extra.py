"""AI-guidance, sim-to-real, inertial-helper and sensor-fusion tables for viewer/index.html (rendered at build time).

Reads results/ai/*.json (aiguide, app/penapp/autocorrect.py), results/s2r/*.json (s2r),
results/pencil/inertial.json (sim/handpen) and results/fusion/*.json (fusion).  Missing inputs skip the section.
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


FUSION_ROWS = [("kfosc_internal", "Old tracker: Kalman on the page position, frozen"),
               ("akf", "Accelerometer tracker (Kalman on the IMU), tuned on smooth writing"),
               ("akf_robust", "Accelerometer tracker, robust setting (default)"),
               ("akf_personal", "Accelerometer tracker, set by a 20 s calibration"),
               ("wflc", "Adaptive oscillator on the accelerometer (WFLC)"),
               ("gru", "Learned network (GRU) trained on the simulator"),
               ("oracle_band", "Perfect knowledge of the tremor band (a limit)")]


def fusion(root):
    g = _load(root, "results/fusion/grid.json")
    c = _load(root, "results/fusion/context.json")
    if not g or "summary" not in g:
        return ""
    S, D = g["summary"], g.get("distortion_um", {})
    CS = (c or {}).get("summary", {})
    rows = []
    for key, lab in FUSION_ROWS:
        v = S.get(key)
        if not v:
            continue
        br = v.get("band_ratio", {})
        cells = []
        for f in ("8", "10", "12"):
            x = br.get(f"{f}Hz_0.3mm")
            m = x.get("mean") if isinstance(x, dict) else x
            cells.append("—" if m is None else f"{m:.2f}")
        o = v.get("overall", {})
        d_grid = D.get(key, {}).get("mean")
        d_sharp = CS.get(key, {}).get("distortion_um", {}).get("mean") if key in CS else None
        dist = "—" if d_grid is None else f"{d_grid:.0f}" + (f" / {d_sharp:.0f}" if d_sharp is not None else " / —") + " µm"
        rows.append([lab, " / ".join(cells), f"{o.get('band_ratio_mean', float('nan')):.2f}", dist,
                     f"{o.get('P_rail_classB_mW_mean', float('nan')):.0f} mW"])
    lede = ("Tremor-band ink error left, as a fraction of no correction (lower is better), on the pencil model with synthetic "
            "handwriting. The accelerometer is fast and quiet enough; what limits every tracker is that handwriting strokes "
            "share the tremor's frequencies. \"Moves tremor-free writing\" is how far each tracker shifts ink when there is no tremor: "
            "on smooth test writing / on sharper glyph writers. The learned network's gain is mostly the simulated pen's friction "
            "drift, not tremor: it moved the ink further from the intended letters.")
    t1 = _section("Telling tremor from writing: the accelerometer tracker", _tags("SIM"), lede,
                  _table(["Tracker", "Error left, 0.3 mm at 8 / 10 / 12 Hz", "Mean, 4–12 Hz and 0.1–0.5 mm",
                          "Moves tremor-free writing", "Drive power"], rows, (1, 2, 3, 4)),
                  "results/fusion/grid.json, context.json (fusion/; docs/sensor_fusion_ai.md)")
    if not CS:
        return t1
    ctx = [("neutral_no_tremor", "Writing without tremor"), ("neutral", "Tremor, no correction"),
           ("oracle_disturbance", "Tremor, perfect knowledge of the disturbance"),
           ("pull_oracle", "Pull toward the true letters (tracing, copying)"),
           ("pull_ai_correct", "Pull toward correctly predicted letters in the writer's style"),
           ("pull_wrong_letter_full", "Pull toward a wrong letter at full confidence"),
           ("ctx_ai_predicted", "Predicted letters as a hint inside the tracker"),
           ("ctx_wrong_letter_full", "A wrong letter as a hint inside the tracker")]
    flips = {"pull_wrong_letter_full": "9 of 624", "ctx_wrong_letter_full": "1 of 624"}
    rows2 = []
    for key, lab in ctx:
        v = CS.get(key)
        if not v:
            continue
        pr = v.get("wo_path_rms_um", {}).get("mean")
        rows2.append([lab, "—" if pr is None else f"{pr:.0f} µm", flips.get(key, "—")])
    lede2 = ("Distance of the ink from the letters the writer intended (writing strokes only), 6 synthetic writers, 0.3 mm tremor at "
             "4–10 Hz. The app's letter prediction helps only when the letters are known in advance; as a hint to the tracker it "
             "changes nothing, because a predicted letter in the writer's style is off by about as much as the tremor, at the same "
             "frequencies.")
    t2 = _section("AI letter prediction and the pen", _tags("SIM"), lede2,
                  _table(["Case", "Distance from the intended letters", "Letters newly misread (wrong-letter cases)"], rows2, (1, 2)),
                  "results/fusion/context.json (fusion/aieval.py; docs/sensor_fusion_ai.md §6.2)")
    return t1 + t2


# ---------------------------------------------------------------------------------------------------------------------
# Where the simulations are, and the optimisation studies (opt/)
WHERE_ROWS = [
    ("Pencil model P1", "The pencil writing on paper: hand, nose skid, spring-loaded refill, two-axis piezo stage with its Hall "
     "servo, sensors, paper contact and friction, in 25 µs steps", "sim/pencil/",
     "Replay groups: pencil model, tremor trackers, touchdown and lift"),
    ("Hand–pen model H1", "Pen tilt in a two-zone grip, with weights and gyroscopes in the cap", "sim/handpen/",
     "Replay group: weights and gyroscopes"),
    ("Sensors and trackers", "6-axis IMU and page sensor models; Kalman trackers, learned network, 20 s calibration", "fusion/, opt/tracker/",
     "Replay group: tremor trackers; gallery"),
    ("AI guidance", "Letter prediction, style templates, guided writing, autocorrect", "aiguide/", "Replay group: AI guidance; gallery"),
    ("Design models", "Loads, stroke, resonance, stress and fit of the stage; CAD of the pencil", "sim/pencil/design.py, analysis/, "
     "mechanics/cad/, opt/hardware/", "Gallery; tables below"),
    ("Twin experiments", "A virtual bench that calibrates the simulator before hardware exists", "s2r/", "Gallery"),
    ("Rev A model M1", "The earlier, larger voice-coil pen", "sim/pensim/", "docs/sim_report.md"),
]


def where(root):
    rows = [[_e(a), _e(b), f"<code>{_e(c)}</code>", _e(d)] for a, b, c, d in WHERE_ROWS]
    lede = ("Every simulation is Python in the repository and re-runs with one command (README.md, “Reproduce”). "
            "This page replays their recorded runs in 3D and shows their charts. Nothing here is a measurement.")
    return _section("Where the simulations are", _tags("SIM", "CALC"), lede,
                    _table(["Model", "What it simulates", "Code", "On this page"], rows), "README.md; CHECKPOINT.md")


def _f(v, nd=2, unit=""):
    if v is None:
        return "—"
    return f"{v:.{nd}f}" + (f" {unit}" if unit else "")


def touchdown_opt(root):
    d = _load(root, "results/opt/touchdown.json")
    sv = _load(root, "results/opt/servo.json")
    if not d or "validation_test_seeds" not in d:
        return ""
    pt = d["validation_test_seeds"]["per_theta"]
    confs = [("tilt_range_stop", "Tilt-range front stop (P0.1.2)"), ("adaptive_0.30mm", "Adaptive stop alone, 0.30 mm margin"),
             ("adaptive_ff", "Adaptive stop 0.31 mm + optimised feed-forward"),
             ("adaptive_ff_tuned_servo", "… + optimised servo")]
    rows = []
    for key, lab in confs:
        cells = [_e(lab)]
        tails = []
        for th in ("35", "50", "75"):
            v = pt.get(th, {}).get(key, {}).get("extra_tr_mm")
            tails.append("—" if v is None else f"{v:.3f}")
        v50 = pt.get("50", {}).get(key, {})
        cells += [" / ".join(tails) + " mm", _f(v50.get("extra_in_mm"), 2, "mm"), _f(v50.get("oracle_ratio"), 2),
                  _f(v50.get("oracle_P_rail_classB_mW"), 0, "mW")]
        rows.append(cells)
    lede = ("Ink the pencil draws at touchdown and lift that a rigid pen would not (within 30 ms of a transition), per stroke, on the "
            "test seeds. The feed-forward uses sensors the pen already has: it pre-positions the stage in the air, cancels the measured "
            "refill slide, switches the load bias at contact and detects contact early from the Hall sensor. Its structure was chosen with "
            "adjoint gradients of a differentiable reduced model; its 11 parameters and the stop margin by Bayesian optimisation on P1. "
            "The open risk is bounce: 1.7 contact transitions per pen-down against 1.2.")
    t1 = _section("Optimised: touchdown and lift", _tags("SIM"), lede,
                  _table(["Pen", "Tail ink per stroke, 35° / 50° / 75°", "In-stroke extra ink, 50°", "Correction left, 6 Hz 0.3 mm, 50°",
                          "Drive power, 50°"], rows, (1, 2, 3, 4)),
                  "results/opt/touchdown.json (opt/touchdown/; docs/opt_touchdown.md; DEC-026)")
    if not sv or "recommended" not in sv:
        return t1
    rec = sv["recommended"].get("hall_1.0um", {})
    base = sv.get("search", {}).get("hall_1.0um", {}).get("default", {})
    tg = sv.get("test_grid", {}).get("hall_1.0um", {})
    rows2 = []
    for lab, blk, x, tgk in (("P0.1.2 servo", base, base.get("x", {}), "default"),
                             ("Optimised servo", rec, rec.get("x", {}), "tuned")):
        r = blk.get("res", {})
        g = tg.get(tgk, {})
        rows2.append([_e(lab), f"{x.get('servo_bw', float('nan')):.0f} Hz / {x.get('servo_zeta', float('nan')):.2f} / "
                      f"{x.get('d_filt_hz', float('nan')):.0f} Hz / {x.get('ff_ref', float('nan')):.2f}",
                      _f(r.get("track_um"), 1, "µm"), _f(r.get("P_rail_classB_mW"), 0, "mW"),
                      f"{_f(r.get('pm'), 1)}° / {_f(r.get('pm_tol20'), 1)}°", _f(g.get("mean_ratio"), 3)])
    lede2 = ("The stage's position servo, tuned by Bayesian optimisation for tracking against drive power, with every candidate held to "
             "the loop-margin rule (phase margin ≥ 45°, gain margin ≥ 10 dB, and no worse than today's at ±20 % stage stiffness). "
             "Proposed only: it must be re-run on the stage once it is identified on the bench.")
    t2 = _section("Optimised: nib servo", _tags("SIM", "CALC"), lede2,
                  _table(["Servo", "Integral corner / damping / derivative filter / feed-forward", "Tracking error", "Drive power",
                          "Phase margin, nominal / ±20 %", "Correction left, test grid mean"], rows2, (2, 3, 4, 5)),
                  "results/opt/servo.json (opt/touchdown/servo.py; DEC-027)")
    return t1 + t2


def hardware_opt(root):
    h = _load(root, "results/opt/hardware.json")
    if not h or "recommended" not in h:
        return ""
    r, c = h["recommended"], h.get("model_checks", {}).get("current_design", {})
    rows = []
    for lab, k, nd, unit in (("Worst-case usable stroke (−20 % parts, 35°)", "usable_wc_um", 0, "µm"),
                             ("Loaded stroke, typical writing (50°)", "q_nom_um", 0, "µm"),
                             ("Force the stage can push with, at the nib", "F_b_nib_N", 2, "N"),
                             ("First resonance", "f1_Hz", 0, "Hz"),
                             ("Battery life with assist on (worst 0.3 mm case)", "life_assist_h", 2, "h"),
                             ("Pen mass including 10 %", "mass_with_margin_g", 1, "g")):
        a, b = c.get(k), r.get(k)
        fa = "—" if a is None else (f"{max(a, 0):.{nd}f} {unit}" + (" (raw negative)" if (k == "usable_wc_um" and a < 0) else ""))
        rows.append([_e(lab), fa, "—" if b is None else f"<b>{b:.{nd}f} {unit}</b>"])
    lede = ("The slim pencil (now the secondary option) re-optimised with a differentiable copy of its design model: exact gradients "
            "(the adjoint) through the plate, leaf, lever, load, resonance, stress and fit equations, with Bayesian optimisation and CMA-ES "
            "over real parts, and the finalists ranked in the pencil model P1. Proposed; the plates are custom and must be quoted and tested.")
    return _section("Optimised: slim pencil hardware (P0.2)", _tags("CALC", "SIM"), lede,
                    _table(["Quantity", "Current pencil (P0.1.2)", "Optimised (P0.2)"], rows, (1, 2)),
                    "results/opt/hardware.json (opt/hardware/; docs/opt_hardware.md; DEC-030)")


TRACKER_ROWS = [("oracle_band", "Limit: perfect knowledge of the 3–15 Hz tremor (not causal)"),
                ("kfosc_internal", "Old tracker: Kalman on the page position, frozen"),
                ("akf_grid", "Accelerometer tracker, random search on smooth writing"),
                ("akf_robust", "Accelerometer tracker, random search, robust (previous default)"),
                ("rep_robust", "Accelerometer tracker, robust objective optimised by backpropagation (proposed default)"),
                ("rep_grid", "Accelerometer tracker, smooth-writing objective optimised by backpropagation"),
                ("gru_old", "Learned network, whole-disturbance target (earlier)"),
                ("gru_band", "Learned network, tremor-band target"),
                ("hybrid", "Accelerometer tracker + learned authority gate")]


def tracker_opt(root):
    d = _load(root, "results/opt/tracker.json")
    if not d or "test" not in d or "grid_summary" not in d["test"]:
        return ""
    G, A = d["test"]["grid_summary"], d["test"].get("aiguide_summary", {})
    CS = (_load(root, "results/fusion/context.json") or {}).get("summary", {})   # sharp-writer shift of trackers not re-run here
    ship = (d.get("summary") or {}).get("ship")
    rows = []
    for key, lab in TRACKER_ROWS:
        v = G.get(key)
        if not v:
            continue
        bc = v.get("by_condition", {})
        hi = [bc.get(f"{f}Hz_{a}mm", {}).get("band_ratio", {}).get("mean") for f in (8, 10, 12) for a in ("0.3", "0.5")]
        hi = [x for x in hi if x is not None]
        dg = v.get("distortion_um_mean")
        ds = (A.get(key, {}).get("distortion_um") or {}).get("mean") if key in A else None
        if ds is None and key in CS:
            ds = (CS[key].get("distortion_um") or {}).get("mean")
        dist = "—" if dg is None else f"{dg:.0f} / " + ("—" if ds is None else f"{ds:.0f}") + " µm"
        name = _e(lab) if key != ship else f"<b>{_e(lab)}</b>"
        rows.append([name, _f(v.get("band_ratio_mean"), 2), "—" if not hi else f"{sum(hi) / len(hi):.2f}", dist,
                     _f(v.get("path_um_mean"), 0, "µm")])
    lede = ("The tracker decides what the stage cancels. It was rewritten so that its exact gradient (backpropagation through "
            "time, the discrete adjoint of the filter) could tune all 23 settings on simulated writing, and to train learned trackers on "
            "the right target. Tremor-band error left as a fraction of no correction on the test grid (lower is better); "
            "“moves tremor-free writing”: on smooth grid writing / on sharper glyph writers. The gain is modest; no setting found "
            "both the smooth-writing set's benefit and a small shift on sharp writers.")
    return _section("Optimised: tremor tracker", _tags("SIM"), lede,
                    _table(["Tracker", "Error left, 3–15 Hz, mean", "Error left, 8–12 Hz at 0.3–0.5 mm", "Moves tremor-free writing",
                            "Path to the intended letters"], rows, (1, 2, 3, 4)),
                    "results/opt/tracker.json (opt/tracker/; docs/opt_tracker.md)")


def optimisation(root):
    """Optimisation studies: hardware (opt/hardware), tracker (opt/tracker), touchdown and servo (opt/touchdown)."""
    parts = []
    for fn in ("hardware_opt", "tracker_opt", "touchdown_opt"):
        f = globals().get(fn)
        if f is not None:
            parts.append(f(root))
    return "".join(parts)


# ---------------------------------------------------------------------------------------------------------------------
# Simulation gallery: charts generated by the studies (copied into viewer/figures/ by viewer/build.py)
# (file under the repository root, title, one-line caption, evidence tags, source)
GALLERY = [
    ("results/cad/drawing_pencil_revPQ.png", "The pencil's layout",
     "Section through the proposed design: skid ring, four piezo plates, gimbal, board and cell. Mass 12.2 g before wiring.",
     ("CALC",), "mechanics/cad/pencil_revP.py"),
    ("results/pencil/fig_loads_vs_tilt.png", "Load the nib stage must hold",
     "Sideways load at the nib against pen tilt. The skid cuts it 3-10 times against a conventional nib.",
     ("CALC",), "analysis/pencil_mechanisms.py"),
    ("results/pencil/fig_stroke_under_load.png", "Stroke left after holding the load",
     "Nib travel left after the stage holds the paper's push. It falls below the 0.30 mm target at low tilt and at -20 % part tolerance.",
     ("CALC",), "analysis/pencil_mechanisms.py"),
    ("results/pencil/fig_sim_trace.png", "One simulated writing run",
     "Ink error with the stage held and with perfect correction (top), and the stage motion hitting its travel limit (bottom). 6 Hz, 0.3 mm tremor.",
     ("SIM",), "sim/pencil/run_study.py"),
    ("results/pencil/fig_sim_ratio_vs_frequency.png", "What the mechanism can do",
     "Ink error left against tremor frequency: the physical limit with perfect knowledge, and the old tracker.",
     ("SIM",), "sim/pencil/run_study.py"),
    ("results/fusion/fig_ratio_vs_frequency.png", "Every tremor tracker on the same writing",
     "The accelerometer trackers against the old one, the learned network and the limits.",
     ("SIM",), "fusion/run_study.py"),
    ("results/fusion/fig_leverarm.png", "Pen rotation and the IMU",
     "How much a tilting pen spoils the board IMU's view of the nib, and what the gyroscope or a nose accelerometer recovers.",
     ("SIM",), "fusion/sensors.py"),
    ("results/fusion/fig_context.png", "AI letter prediction and the pen",
     "Distance from the intended letters, recognition and distortion for every tracker and every way of using the app's templates.",
     ("SIM",), "fusion/aieval.py"),
    ("results/pencil/fig_inertial_timedomain.png", "Weights and gyroscopes in the cap",
     "Ink error with cap devices alone and with the nib stage, and how often the stage hits its travel limit.",
     ("SIM",), "sim/handpen/run_study.py"),
    ("results/ai/fig_autocorrect.png", "Autocorrect in the app",
     "Word errors before and after, correct words changed by mistake, and wrong words fixed, against the decision threshold.",
     ("CALC",), "aiguide/run_autocorrect.py"),
    ("results/s2r/fig_c2_gap.png", "Can the simulator be trusted after calibration?",
     "Twin experiments: predictions before and after calibrating the simulator from virtual bench runs, against 15 hidden plants.",
     ("SIM",), "s2r/"),
]
GALLERY_OPT = [   # optimisation studies (shown when their figures exist)
    ("results/opt/fig_hw_validation.png", "Slim pencil hardware: before and after",
     "Error left with perfect tremor knowledge, and time at the travel limit, for the current and optimised pencil stages in the pencil model. "
     "The optimised plates help most with small tremor; with larger tremor the ±0.3 mm travel limit decides.", ("SIM",), "opt/hardware/"),
    ("results/opt/fig_hw_pareto.png", "Slim pencil hardware: the trade-off",
     "Worst-case stroke against battery power and pen mass for the designs the optimiser kept.", ("CALC",), "opt/hardware/"),
    ("results/opt/fig_tr_ratio_vs_frequency.png", "Tracker optimisation: before and after",
     "Tremor-band error left against tremor frequency: the tracker settings re-optimised by adjoint gradients (proposed), the earlier sets, "
     "the retrained learned trackers and the limit with perfect knowledge.", ("SIM",), "opt/tracker/"),
    ("results/opt/fig_tr_pareto.png", "Tracker optimisation: the trade-off",
     "Tremor removed against how far each tracker moves tremor-free writing (smooth / sharp writers). The adjoint sweeps trace the front; "
     "no setting gets both the smooth-writing benefit and a small shift on sharp writing.", ("SIM",), "opt/tracker/"),
    ("results/opt/fig_td_tails.png", "Touchdown tails: before and after",
     "Extra ink at touchdown and lift, extra ink within strokes, and missing ink, with the tilt-range stop, the adaptive stop, "
     "and the stage feed-forward tuned by Bayesian optimisation.", ("SIM",), "opt/touchdown/"),
    ("results/opt/fig_td_event.png", "One touchdown, before and after",
     "The ink point, stage deflection and refill slide through a single pen-down and lift.", ("SIM",), "opt/touchdown/"),
    ("results/opt/fig_td_servo.png", "Nib servo retuned",
     "Stage tracking error against drive power for the servo settings Bayesian optimisation explored.", ("SIM", "CALC"), "opt/touchdown/servo.py"),
]


def gallery_files(root):
    """Figures of the gallery that exist: (published name, source path)."""
    import os
    out = []
    for rel, *_ in GALLERY + GALLERY_OPT:
        src = os.path.join(root, rel)
        if os.path.exists(src):
            out.append((rel.replace("/", "__"), src))
    return out


def gallery(root):
    import os
    items = []
    for rel, title, cap, tags, src in GALLERY + GALLERY_OPT:
        if not os.path.exists(os.path.join(root, rel)):
            continue
        name = "figures/" + rel.replace("/", "__")
        items.append(f'<figure class="gfig"><a href="{_e(name)}" target="_blank" rel="noopener"><img src="{_e(name)}" loading="lazy" '
                     f'alt="{_e(title)}"></a><figcaption><b>{_e(title)}</b> {_tags(*tags)}<span>{_e(cap)}</span>'
                     f'<code>{_e(src)}</code></figcaption></figure>')
    if not items:
        return ""
    lede = ("Charts produced by the simulations and calculations in the repository. Tap a chart to open it full size. "
            "Nothing here is a measurement; each chart carries its evidence label and the script that made it.")
    return (f'<section class="block"><h2>Simulation gallery</h2><p class="note">{lede}</p>'
            f'<div class="gallery">{"".join(items)}</div></section>')
