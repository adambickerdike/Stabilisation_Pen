#!/usr/bin/env python3
"""Assemble the Rev J explainer page: viewer/explainer/index.html and viewer/explainer/data/*.json.

Inputs (read-only; every number on the page comes from one of these files or from a doc named next to it):

  data/layout.json   <- results/revJ/layout.json (the integrated Rev J pen; else results/revH/layout.json, labelled)
  data/pen.json      <- facts for the text and charts, each with its label and source:
                          results/revJ/{layout,budgets,revJ}.json          pen, budgets, integration problems (CALC)
                          results/ai2/ai2.json                             gated tracker, learned estimator, clean copy (SIM)
                          results/nose2/nose2.json                         autowrite (SIM)
                          results/drive/tasks.json, tasks_extra.json, fig_practice.csv, fig_loops_reversal.csv,
                          fig_traction_capacity.csv                        heel wheel (SIM, CALC)
                          results/endcap/endcap_study.json, fig_ek_ceiling.csv, fig_ek_steer.csv   first end-cap (SIM, CALC)
                          results/revJ1/{endcap,budgets,revJ1}.json        Rev J.1's lighter end-cap, the current tail (SIM)
                          results/revJ/sim_params.json + layout            the static side load on the ball (CALC, the
                                                                           independent review's formula) and the page
                                                                           sensor's assumed accuracy (ASSUMPTION)
                          docs/revJ_simulation.md §8                       simulated side-load power, heel wheel on clean
                                                                           writing (SIM); docs/evidence.csv OPT-02 (LIT)
                          results/sim2j/et.json                            whole-pen simulation (SIM), when it exists and
                                                                           is complete (no 'unfinished' writers)
  data/samples.json  <- before/after strips (handwriting samples schema, one panel per scenario):
                          results/ai2/samples.json                         tremor, gated tracker, learned estimator, clean copy
                          results/nose2/fig_nose2_autowrite_example.csv    autowrite ink paths (+ nose2.json metrics)
                          results/drive/tasks.json (paths_first_case)      the heel wheel leading a relaxed hand
                          results/sim2j/samples.json                       the whole Rev J pen in sim2, when it exists
  data/replay.json   <- results/sim2j/viz_sim2j.json (optional: the whole-pen replay that drives scenes a and b; without
                        it they replay the ai2 strips)
  data/manifest.json    which source each file came from (the page shows it)

The page itself is viewer/explainer/template.html.  build.py fills its <!--BUILD:...--> placeholders (the mechanism
sentences, the "How much better?" rows with their pictures, the component table, the results table, data status,
provenance) and its [[fact]] tokens (numbers in the text), so the text and tables read without any script.  The 2-D
cut-away, the 3-D views, the scenes and the strips load the JSON files with fetch() at run time.

The simple view is driven by two specs in this file, so that a mechanism or a result can be swapped when a study
changes: MECHANISMS (one sentence per mechanism: what moves, what pushes it, what it does to the ink) and simple_rows()
(one row per condition: a picture pair from samples.json or an illustration, ONE number from pen.json, its evidence
label and source).  KNOWN_PROBLEMS holds the "Known problems (being fixed)" panel (one plain line each, with its
evidence), drawn with the side-load figure (sideload_svg).  Results of the whole-pen simulation study (sim2j) are
picked up as soon as its files exist and its summary is complete (sim2j_row() adds a row); rebuild to add them.

Run:  python3 viewer/explainer/build.py
"""
from __future__ import annotations

import csv
import datetime as _dt
import html
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")

LAYOUT_FINAL = "results/revJ/layout.json"
LAYOUT_PROV = "results/revH/layout.json"
BUDGETS = "results/revJ/budgets.json"
REVJ = "results/revJ/revJ.json"
AI2_SAMPLES = "results/ai2/samples.json"
AI2_JSON = "results/ai2/ai2.json"
NOSE2_JSON = "results/nose2/nose2.json"
NOSE2_EXAMPLE = "results/nose2/fig_nose2_autowrite_example.csv"
DRIVE_TASKS = "results/drive/tasks.json"
DRIVE_EXTRA = "results/drive/tasks_extra.json"
DRIVE_PRACTICE = "results/drive/fig_practice.csv"
DRIVE_LOOPS = "results/drive/fig_loops_reversal.csv"
DRIVE_TRACTION = "results/drive/fig_traction_capacity.csv"
ENDCAP_JSON = "results/endcap/endcap_study.json"
ENDCAP_CEILING = "results/endcap/fig_ek_ceiling.csv"
ENDCAP_STEER = "results/endcap/fig_ek_steer.csv"
SIM2J_SAMPLES = "results/sim2j/samples.json"
SIM2J_REPLAY = "results/sim2j/viz_sim2j.json"
SIM2J_ET = "results/sim2j/et.json"
REALDATA_JSON = "results/realdata/realdata.json"         # study R: real recorded handwriting and tremor (HW1)
REALDATA_SAMPLES = "results/realdata/samples.json"
SIM_REAL = "SIMULATION (model HW1) with real recorded inputs"
AI3_JSON = "results/ai3/ai3.json"                         # study S: spelling help, prediction, clarity
WHOLEPEN_SUMMARY = "results/wholepen/summary.json"         # study W: shifting the whole pen
SIM2J_CARDS = "results/sim2j/cards.json"        # the study's results cards (one per condition), as data
SIM2J_PARTIAL: list = []      # coverage notes when the study finished with parts still to run
SIM2J_PENDING: list = []      # why whole-pen results were left out (a partial summary of a run in progress)
SIM_PARAMS = "results/revJ/sim_params.json"                 # inputs of the static nib load (refill spring, Km, coil)
REVJ1_ENDCAP = "results/revJ1/endcap.json"                  # Rev J.1's lighter end-cap (the current tail design)
REVJ1_BUDGETS = "results/revJ1/budgets.json"
REVJ1_JSON = "results/revJ1/revJ1.json"
LEDGER = "docs/evidence.csv"
SIM_DOC = "docs/revJ_simulation.md"                         # the whole-pen simulation's findings (§8)
REVIEW_RESPONSE = "docs/reviews/2026-09-29_review_response.md"
REVIEW_PDF = "docs/reviews/2026-09-29_independent_review.pdf"
STALE = ("board.json", "tip.json", "outcomes.json")          # Rev H page files that Rev J no longer uses

SIM_HW1 = "SIMULATION (model HW1)"
SIM_HW1D = "SIMULATION (model HW1-D)"
SIM_H1 = "SIMULATION (model H1)"
SIM_SIM2 = "SIMULATION (sim2, whole Rev J pen)"

WARNINGS: list[str] = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print("WARNING:", msg, file=sys.stderr)


def rel(p: str) -> str:
    return os.path.join(ROOT, p)


def load(p: str):
    with open(rel(p), encoding="utf-8") as f:
        return json.load(f)


def load_csv(p: str) -> list[dict]:
    with open(rel(p), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def exists(p: str) -> bool:
    return os.path.exists(rel(p))


def git_revision() -> str:
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                             timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True,
                               text=True, timeout=20).stdout.strip()
        return rev + ("-dirty" if dirty else "") if rev else "unknown"
    except Exception:  # noqa: BLE001  (git missing is not an error for the page)
        return "unknown"


def mtime_utc(p: str) -> str:
    return _dt.datetime.fromtimestamp(os.path.getmtime(rel(p)), _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def r3(v: float) -> float:
    return float(f"{v:.3f}")


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def pct(x, nd=0) -> str:
    return f"{100 * x:.{nd}f}"


def e(x) -> str:
    return html.escape(str(x), quote=True)


# ---------------------------------------------------------------------------------------------------------------- pen
REQUIRED_SHAPES = {"cylinder", "cone", "tube", "box"}


def check_layout(lay: dict) -> list[str]:
    """Problems that would stop the page drawing the pen (empty list = usable)."""
    probs = []
    comps = lay.get("components")
    if not isinstance(comps, list) or not comps:
        return ["no 'components' list"]
    for c in comps:
        if not isinstance(c, dict) or "z0" not in c or "z1" not in c:
            probs.append(f"component {c.get('id', '?') if isinstance(c, dict) else c!r} has no z0/z1")
        elif c.get("shape") not in REQUIRED_SHAPES:
            probs.append(f"component {c.get('id')} has unknown shape {c.get('shape')!r} (drawn as a cylinder)")
    return probs


def build_layout():
    src, status = (LAYOUT_FINAL, "final") if exists(LAYOUT_FINAL) else (LAYOUT_PROV, "provisional")
    if status != "final":
        warn(f"{LAYOUT_FINAL} is missing; the page draws the Rev H layout ({LAYOUT_PROV}) and says so")
    lay = load(src)
    probs = check_layout(lay)
    fatal = [p for p in probs if "no 'components'" in p or "no z0/z1" in p]
    if fatal:
        raise SystemExit(f"{src} is not usable: {'; '.join(fatal)}")
    for p in probs:
        warn(f"{src}: {p}")
    lay.setdefault("meta", {})["page_source"] = src
    return lay, {"file": "layout.json", "source": src, "status": status, "modified": mtime_utc(src),
                 "evidence": (lay.get("meta") or {}).get("evidence_status", "")}


# ------------------------------------------------------------------------------------------------------------- facts
def _row(rows, **kw):
    for r in rows:
        if all(str(r.get(k)) == str(v) for k, v in kw.items()):
            return r
    return None


def _f(r, k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return None


def facts_budgets(lay: dict) -> dict:
    b = load(BUDGETS)["budgets"]
    rj = load(REVJ)
    m, pw = b["mass"], b["power"]["modes"]
    out = {
        "od_mm": lay.get("handle_od"), "length_mm": b["length"]["base_mm"], "length_endcap_mm": b["length"]["with_endcap_mm"],
        "length_limit_mm": b["length"]["limit_mm"], "revH_length_mm": b["length"]["references"]["revH_mm"],
        "mass_g": m["base"]["mass_g"], "mass_endcap_g": m["with_endcap"]["mass_g"], "endcap_g": m["endcap_g"],
        "com_mm": m["base"]["com_mm"][2], "com_endcap_mm": m["with_endcap"]["com_mm"][2],
        "hours": {k: v["hours"] for k, v in pw.items()},
        "hours_endcap": {k: v["hours_with_endcap"] for k, v in pw.items()},
        "hours_gated": rj["power_options"]["page_sensor_gated_hours"],
        "base_load_mW": [1000 * (pw["steady_no_tremor"]["electronics_W"] + pw["steady_no_tremor"]["page_sensor_W"][0]),
                         1000 * (pw["steady_no_tremor"]["electronics_W"] + pw["steady_no_tremor"]["page_sensor_W"][1])],
        "heat_1mm": b["heat"]["rows"]["steady_1mm"], "heat_rows": b["heat"]["rows"],
        "fit_all_pass": bool((lay.get("fit_checks") or {}).get("all_pass")),
        "fit_n": sum(1 for k, v in (lay.get("fit_checks") or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)),
        "axial_pull_N": rj["magnetics"]["axial_pull_N"],
        "detent_torque_mNm": rj["magnetics"]["motor_torque_bound_mNm"],
        "page_sensor_band_roll0_mm": rj["page_sensor"]["height_band_mm"]["roll0"],
        "label": "CALC (results/revJ/budgets.json, revJ.json; docs/revJ_design.md)",
    }
    return out


def facts_ai2() -> dict:
    a = load(AI2_JSON)["aggregate"]
    s, tf = a["summary"], a["tremor_free"]
    g = lambda dev, k: _num((s.get(dev) or {}).get(k))
    out = {k: {"ink_um": g(k, "ink_err_um_1_2mm"), "words": g(k, "word_acc_app_1_2mm"), "letters": g(k, "recognition_1_2mm"),
               "ink_6hz_um": g(k, "ink_err_um_6Hz_1_2mm"), "ink_0p3_um": g(k, "ink_err_um_0p3mm")}
           for k in ("none", "tracker", "gated", "learned_tcn", "clean_copy", "oracle", "delayed_3mm", "lag_100_6mm", "rl_arbiter")}
    out["moved_um"] = {k: _num((tf.get(k) or {}).get("false_correction_um")) for k in ("tracker", "gated", "learned_tcn", "rl_arbiter")}
    out["paired_gated_tracker"] = (a.get("paired") or {}).get("gated-tracker:ink_err_um")
    out["gate_open_tremor_free"] = a.get("gate_open_frac_tremor_free")
    out["label"] = SIM_HW1
    out["detail"] = "test writers 0–5, seeds 200–203; the trackers drive the older Rev H inner-pen (nose) model, ±3 mm"
    out["source"] = AI2_JSON
    return out


def facts_nose2() -> dict:
    n = load(NOSE2_JSON)
    h, ex = n["headline"], n["example"]
    keep = ("ink_err_um", "letters_read", "words_read_app", "letters_per_s", "P_coil_W", "battery_h_autowriting", "plan_fail", "n")
    out = {k: {kk: h[k].get(kk) for kk in keep} for k in ("aw_2p5_none", "aw_2p5_1mm", "aw_2p5_2mm", "aw_3p0_1mm",
                                                          "noaxial_2p5_none", "noaxial_2p5_1mm") if k in h}
    out["example"] = {k: {kk: ex[k].get(kk) for kk in ("ink_err_um", "letters_read", "target_letters_read", "words_read_app",
                                                       "recognised", "letters_per_s", "v_h_mm_s", "q_max_mm", "f0", "amp_mm",
                                                       "h_mm", "w", "seed")}
                      for k in ("revJ", "revJ_noaxial") if k in ex}
    out["travel_guaranteed_mm"], out["travel_nom_mm"] = h.get("guaranteed_travel_mm"), h.get("nominal_travel_mm")
    out["label"] = SIM_HW1
    out["detail"] = "test writers 0–5, seeds 200–203"
    out["source"] = NOSE2_JSON
    return out


def facts_drive() -> dict:
    pr, lr = load_csv(DRIVE_PRACTICE), load_csv(DRIVE_LOOPS)
    tr = load_csv(DRIVE_TRACTION)
    t = load(DRIVE_TASKS)
    aw = t["autowrite"]["aggregate"]

    def pr_row(profile, cond):
        r = _row(pr, profile=profile, cond=cond)
        return {"err_um": _f(r, "target_err_um"), "letters": _f(r, "letters_read_ok"), "words": _f(r, "words_app"),
                "F_rms_N": _f(r, "F_rms_N"), "F_p95_N": _f(r, "F_p95_N")} if r else None

    def lr_val(task, writer, cond, metric):
        r = _row(lr, task=task, writer=writer, cond=cond, metric=metric)
        return _f(r, "value") if r else None

    lagg = ((t.get("loops") or {}).get("aggregate") or {}).get("relaxed") or {}
    last = {c: _num((lagg.get(c) or {}).get("last_loop_ratio")) for c in ("none", "wheel_path", "sd_full")}
    tall = {c: _num((lagg.get(c) or {}).get("loop_height_ratio_ink")) for c in ("none", "wheel_path", "sd_full")}
    ex_rows = [r for r in ((t.get("practice") or {}).get("rows") or [])
               if r.get("profile") == "dysgraphia" and r.get("writer") == 0 and r.get("seed") == 200]
    tr_ex = {r["cond"]: {"read": r.get("recognised"), "letters": _num(r.get("letters_read_ok"))} for r in ex_rows
             if r.get("cond") in ("none", "wheel_path+nose", "sd_path")}
    trac = [{"P_N": _f(r, "P_N"), "mu": _f(r, "mu"), "cap_N": _f(r, "cap_mean_N")} for r in tr]
    at055 = [x for x in trac if x["P_N"] == 0.55]
    out = {
        "tracing": {c: pr_row("dysgraphia", c) for c in ("none", "sd_path", "wheel_path", "wheel_path+nose", "board_full")},
        "tracing_dyslexia": {c: pr_row("dyslexia", c) for c in ("none", "sd_path", "wheel_path+nose")},
        "loops": {"none": lr_val("loops", "relaxed", "none", "loop_height_ratio_ink"),
                  "wheel": lr_val("loops", "relaxed", "wheel_path", "loop_height_ratio_ink"),
                  "wheel_resist": lr_val("loops", "lightly_resisting", "wheel_path", "loop_height_ratio_ink"),
                  "sd_resist": lr_val("loops", "lightly_resisting", "sd_path", "loop_height_ratio_ink"),
                  "sd_full_resist": lr_val("loops", "lightly_resisting", "sd_full", "loop_height_ratio_ink"),
                  "board": lr_val("loops", "relaxed", "board_full", "loop_height_ratio_ink")},
        "lead": {"sd": lr_val("reversal", "relaxed (lead-through)", "sd_lead", "bowl_coverage"),
                 "none": lr_val("reversal", "relaxed (lead-through)", "none", "bowl_coverage"),
                 "sd_rms_mm": lr_val("reversal", "relaxed (lead-through)", "sd_lead", "bowl_to_template_rms_mm"),
                 "sd_Fmax_N": lr_val("reversal", "relaxed (lead-through)", "sd_lead", "F_max_N")},
        "set_on_b": {c: {"moved": lr_val("reversal", "set on b", c, "bowl_correct_side"),
                         "F_max_N": lr_val("reversal", "set on b", c, "F_max_N"),
                         "felt_p95_N": lr_val("reversal", "set on b", c, "felt_p95_N")}
                     for c in ("none", "wheel_path", "sd_full", "ball_full", "board_full")},
        "gross": {k: {kk: _num((aw.get(k) or {}).get(kk)) for kk in ("letters_read_ok", "words_app", "target_err_um",
                                                                     "pen_speed_mm_s", "device_work_share", "F_rms_N", "F_max_N")}
                  for k in ("relaxed_nose", "sd_lead+nose", "ball_lead+nose", "board_lead+nose", "writer_alone")},
        "loops_last": last, "loops_tallest": tall, "tracing_example": tr_ex,
        "traction": trac, "traction_055": at055,
        "label": SIM_HW1D, "detail": "test writers 0–5, seeds 200–203; rules frozen before the test",
        "source": "results/drive/ (fig_practice.csv, fig_loops_reversal.csv, tasks.json)",
    }
    return out


def facts_endcap() -> dict:
    st = load(ENDCAP_JSON)
    s = st["tremor"]["summary"]
    band = "8-12Hz_1-2mm"

    def get(dev, key):
        return [(s.get(dev) or {}).get(sp, {}).get(band, {}).get(key) for sp in ("0.3", "0.5", "0.7")]

    ceil = [{"f_Hz": _f(r, "f_Hz"), "F_N": _f(r, "LRM_force_mN") / 1000, "need_1mm_N": _f(r, "force_for_1mm_mN") / 1000}
            for r in load_csv(ENDCAP_CEILING)]
    shift = [{"f_Hz": _f(r, "f_Hz_or_t_s"), "ink_mm": _f(r, "tip_peak_mm")} for r in load_csv(ENDCAP_STEER)
             if r["device"] == "lrm" and r["scenario"] == "write" and r["r_rot"] == "0.5"]
    return {"moving": get("lrm", "further_reduction_mean"), "fixed": get("weight_lrm", "further_reduction_mean"),
            "moving_worse": get("lrm", "frac_conditions_worse"), "fixed_worse": get("weight_lrm", "frac_conditions_worse"),
            "splits": [0.3, 0.5, 0.7], "ceiling": ceil, "write_shift_r05": shift,
            "label": SIM_H1, "detail": "on top of the Rev H nose and tracker; test seeds 200–203",
            "ceiling_label": "CALC (linear hand-pen model, relaxed hand, no paper friction: optimistic)",
            "source": ENDCAP_JSON}


def facts_sim2j() -> dict | None:
    """Headline numbers of the whole-pen simulation: the results cards (results/sim2j/cards.json, one per condition)
    and the tremor grid (results/sim2j/et.json: mean ink error, ratio to the device-off pen, words read, per controller
    and tremor size; keys follow sim2j/run_study.summarise_et).  A study that finished with parts still to run is
    shown with its coverage stated; a quick check is not shown."""
    if not exists(SIM2J_ET) and not exists(SIM2J_CARDS):
        return None
    out = {"label": SIM_SIM2, "detail": "sim2 ranks designs until it is calibrated (EXP-V01, V02, V04) and validated (EXP-V05)",
           "source": SIM2J_ET, "rows": [], "clean_moved_um": {}}
    try:
        if exists(SIM2J_ET):
            et = load(SIM2J_ET)
            if et.get("quick"):
                SIM2J_PENDING.append(f"{SIM2J_ET} is a quick check, not the study")
                warn(f"{SIM2J_ET} is a quick check; not shown")
                return None
            left = [str(x) for x in (et.get("unfinished") or [])]
            cov = et.get("coverage") or {}
            done = sum(1 for v in cov.values() if isinstance(v, dict) and v.get("complete"))
            if left:
                who = (", ".join(left[:-1]) + " and " + left[-1]) if len(left) > 1 else "".join(left)
                out["partial_note"] = f"{done} of {done + len(left)} test writers so far"
                SIM2J_PARTIAL.append(f"the tremor grid covers {done} of {done + len(left)} test writers ({who} still to run)")
            by = et.get("by_amp") or {}
            for key, v in by.items():
                parts = str(key).split("|")
                if len(parts) != 2 or not isinstance(v, dict):
                    continue
                amp, ctl = parts
                out["rows"].append({"amp_mm": _num(float(amp)) if re.match(r"^[\d.eE+-]+$", amp) else amp, "ctl": ctl,
                                    "ink_um": _num(v.get("ink_err_um")), "ratio": _num(v.get("ratio")),
                                    "words": _num(v.get("words_app")), "letters": _num(v.get("letters_read")), "n": v.get("n")})
            out["clean_moved_um"] = {k: _num((v or {}).get("moved_vs_clean_um")) for k, v in (et.get("clean") or {}).items()}

            def cell_ratio(ctl, sel):
                vs = [(v["ratio"], v.get("n") or 1) for k, v in (et.get("by_cell") or {}).items()
                      if len(k.split("|")) == 3 and k.split("|")[2] == ctl and sel(float(k.split("|")[0]), float(k.split("|")[1]))
                      and isinstance(v, dict) and _num(v.get("ratio")) is not None]
                return sum(r * n for r, n in vs) / sum(n for _, n in vs) if vs else None
            fast = lambda f0, amp: f0 >= 8 and amp >= 1.0
            slow = lambda f0, amp: f0 < 5 and amp >= 1.0
            out["ratio_fast"] = cell_ratio("nose", fast)
            out["ratio_fast_limit"] = cell_ratio("oracle", fast)
            out["ratio_slow"] = cell_ratio("nose", slow)
            out["ratio_slow_limit"] = cell_ratio("oracle", slow)
            out["ratio_fast_ec"] = cell_ratio("nose_wheel_ec", fast)
            out["ratio_fast_wheel"] = cell_ratio("nose_wheel", fast)
            out["what"] = et.get("what", "")
            out["generated_utc"] = (et.get("stabpen.provenance") or {}).get("generated_utc")
        if exists(SIM2J_CARDS):
            out["cards"] = {c["id"]: c for c in (load(SIM2J_CARDS).get("cards") or []) if isinstance(c, dict) and c.get("id")}
        return out
    except (OSError, ValueError, TypeError, AttributeError, KeyError, ZeroDivisionError) as ex:
        warn(f"{SIM2J_ET} could not be read ({ex})")
        return None


def facts_realdata() -> dict | None:
    """Study R's pooled results (results/realdata/realdata.json, hw1.aggregate.real): readable words out of 10 and the
    tip tremor, per pen, at the severe and moderate real tremor sizes (Parkinson's and essential tremor pooled; held-out
    writers, texts and patients; the DeltaPen-class page sensor)."""
    if not exists(REALDATA_JSON):
        return None
    try:
        agg = ((load(REALDATA_JSON).get("hw1") or {}).get("aggregate") or {}).get("real") or {}

        def val(x, k="mean"):
            v = x.get(k) if isinstance(x, dict) else x
            return v if isinstance(v, (int, float)) and v == v else None
        out = {"label": SIM_REAL, "source": REALDATA_JSON}
        for cls in ("severe", "moderate", "mild"):
            a = agg.get(f"all/{cls}") or {}
            pens = {}
            for key, name in (("none", "none"), ("revJ_gated|deltapen", "gated"), ("revJ_tcn|deltapen", "tcn"),
                              ("revH_akf|deltapen", "revh"), ("revJ_oracle", "oracle")):
                v = a.get(key) or {}
                pens[name] = {"words": val(v.get("words_of_10")), "words_lo": val(v.get("words_of_10"), "lo"),
                              "words_hi": val(v.get("words_of_10"), "hi"), "tip_mm": val(v.get("tip_tremor_mm")),
                              "ratio": val(v.get("tip_tremor_ratio")), "clean_moved_um": val(v.get("false_correction_um"))}
            pens["clean_words"] = val((a.get("none") or {}).get("clean_words_of_10"))
            out[cls] = pens
        return out
    except (OSError, ValueError, TypeError, AttributeError) as ex:
        warn(f"{REALDATA_JSON} could not be read ({ex})")
        return None


def facts_ai3() -> dict | None:
    """Study S's headline numbers (results/ai3/ai3.json): misspellings put right on paper per cue, the spell checker's
    catch rate with the letters known and with the pen reading them, and word completion after one letter."""
    if not exists(AI3_JSON):
        return None
    try:
        d = load(AI3_JSON)
        cues = d["cues"]["test"]["nominal"]
        sp = d["spell"]["test"]["score"]
        own = d["words"]["spelling_v2"]["independent"]["test"]
        pt = d["predict"]["test"]
        top3 = [v["personalised (chosen)"]["after1_top3"] for k, v in pt.items()          # the test journals only (the
                if str(k).isdigit() and isinstance(v, dict) and isinstance(v.get("personalised (chosen)"), dict)]   # app note lines are another test)
        return {"pause_fixed_of10": cues["pause_offer"]["fixed_on_paper_per_10_errors"],
                "lift_fixed_of10": cues["tick_lift"]["fixed_on_paper_per_10_errors"],
                "caught_known": sp["detection_rate"], "fa_known": sp["fa_per_100_correct"],
                "caught_own": own["detection_rate"], "fa_own": own["fa_per_100_correct"],
                "top3_after1": [min(top3), max(top3)] if top3 else None,
                "label": "SIMULATION and CALCULATION on real letters and real misspellings (study S)", "source": AI3_JSON}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as ex:
        warn(f"{AI3_JSON} could not be read ({ex})")
        return None


def facts_wholepen() -> dict | None:
    """Study W's collar against the same pen with the collar locked (results/wholepen/summary.json)."""
    if not exists(WHOLEPEN_SUMMARY):
        return None
    try:
        sm = load(WHOLEPEN_SUMMARY)
        rows = [r for r in (sm.get("tail_and_collar_vs_locked_test") or []) + (sm.get("tail_and_collar_vs_locked_grips") or [])
                if r.get("active") == "collar_nose" and isinstance(r.get("gain_vs_locked"), (int, float))]   # the causal collar, not its perfect-knowledge limit
        g = [r["gain_vs_locked"] for r in rows]
        return {"collar_gain": [min(g), max(g)] if g else None, "n": len(g),
                "label": "SIMULATION (study W, the collar carrying the Rev J pen)", "source": WHOLEPEN_SUMMARY}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as ex:
        warn(f"{WHOLEPEN_SUMMARY} could not be read ({ex})")
        return None


def panels_realdata() -> list:
    """Study R's committed pictures (results/realdata/samples.json; letters of UCI Character Trajectories, CC BY, with
    real recorded tremor): one panel per population and size, variants keyed none / gated / oracle / tcn / revh."""
    if not exists(REALDATA_SAMPLES):
        return []
    raw = load(REALDATA_SAMPLES)
    keymap = {"none": "none", "revJ_gated|deltapen": "gated", "revJ_oracle": "oracle", "revJ_tcn|deltapen": "tcn",
              "revH_akf|deltapen": "revh"}
    groups: dict = {}
    for p in raw.get("panels", []):
        k = keymap.get(str(p.get("device", "")))
        if k:
            groups.setdefault(str(p.get("condition", "")), []).append((k, p))
    panels = []
    for cond, items in groups.items():
        variants = []
        for k, p in items:
            pts = _pts3(p.get("ink", []))
            ink = strokes_from(pts, [q[2] for q in pts])
            if ink:
                variants.append({"key": k, "role": {"none": "before", "oracle": "limit"}.get(k, "after"), "label": p.get("title", k),
                                 "key_device": k in ("none", "gated", "oracle"), "ink": ink, "metrics": []})
        if not variants:
            continue
        first = items[0][1]
        ipts = _pts3(first.get("intended", []))
        panels.append({"id": f"real_{cond}", "condition": "real", "source": REALDATA_SAMPLES, "evidence": SIM_REAL,
                       "provisional": False, "title": str(first.get("title", cond)), "subtitle": str(first.get("caption", "")),
                       "ruling_mm": 8, "rate_hz": 50.0, "intended": strokes_from(ipts, [q[2] for q in ipts]),
                       "variants": variants})
    return panels


def _doc(p: str) -> str:
    try:
        with open(rel(p), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _find(pattern: str, text: str, what: str, src: str):
    m = re.search(pattern, text)
    if not m:
        warn(f"{src}: could not find {what}; the page shows a dash")
        return None
    return m.groups()


def facts_sideload(lay: dict) -> dict:
    """The static side load on the ball, with the independent review's formula (docs/reviews/..._independent_review.pdf
    §4, reproduced in the lead's response): N sin θ = F_c; F⊥ = N cos θ = F_c cot θ; τ = L_t F⊥; F_act = τ / L_a;
    P = (F_act / K_m)²; I = √(P / R).  Inputs from the design files: the refill spring F_c, K_m, R and the coil's
    thermal model in results/revJ/sim_params.json; L_t (pivot to ball) and L_a (pivot to magnets) in the layout."""
    sp = load(SIM_PARAMS)["sim_params"]
    fc = float(sp["refill"]["spring_force_N"]["value"])
    km = float(sp["nose"]["Km_act_N_per_sqrtW"]["value"])
    r_ohm = float(sp["nose"]["coil_R_ohm"]["value"])
    rth, cth = float(sp["nose"]["coil_Rth_K_W"]["value"]), float(sp["nose"]["coil_Cth_J_K"]["value"])
    # The arms to 0.1 mm, as the design documents and the review quote them (76.5 and 11.5 mm); the layout's extra
    # digits (76.48, 11.51) are drawing precision, and with the rounded arms the review's table reproduces exactly.
    lt = round(float(lay["pivot_z"]), 1)
    la = round(float(lay["actuator_z"]) - float(lay["pivot_z"]), 1)
    sim = _doc(SIM_DOC)
    lim = _find(r"pass its (\d+) °C limit within about (\d+) s", sim, "the coil limit", SIM_DOC)
    t_lim = float(lim[0]) if lim else 120.0
    t_amb = 25.0          # the simulator's starting coil temperature (docs/revJ_simulation.md §8.1: "25 → 61.5 °C")
    rows = {}
    for th in (35, 50, 75):
        t = math.radians(th)
        fp = fc / math.tan(t)
        fa = fp * lt / la
        p = (fa / km) ** 2
        rise = p * rth
        rows[str(th)] = {"N_N": fc / math.sin(t), "F_perp_N": fp, "torque_mNm": fp * lt, "F_act_N": fa, "P_W": p,
                         "I_A": math.sqrt(p / r_ohm),
                         "t_limit_s": (-rth * cth * math.log(1 - (t_lim - t_amb) / rise)) if rise > t_lim - t_amb else None}
    review = {"35": 4.717, "50": 1.628, "75": 0.166}          # the review's table (a check, not an input)
    for k, v in review.items():
        if abs(rows[k]["P_W"] / v - 1) > 0.02:
            warn(f"static nib load at {k}°: {rows[k]['P_W']:.3f} W here against {v} W in the review; check the inputs")
    run = _find(r"\*\*About ([\d.]+) W: the refill spring's side load", sim, "the simulated share of the load", SIM_DOC)
    return {"F_c_N": fc, "Km": km, "R_ohm": r_ohm, "Rth_K_W": rth, "Cth_J_K": cth, "L_t_mm": lt, "L_a_mm": la,
            "ratio": lt / la, "by_angle": rows, "coil_limit_C": t_lim, "start_C": t_amb,
            "sim_run_W": float(run[0]) if run else None,
            "label": "CALC (the review's formula, reproduced; inputs results/revJ/sim_params.json and layout.json)",
            "sim_label": "SIMULATION (sim2, docs/revJ_simulation.md §8.1)", "source": f"{REVIEW_RESPONSE}; {REVIEW_PDF} §4; {SIM_DOC} §8.1"}


def facts_known() -> dict:
    """The other known problems: the heel wheel on clean writing (sim2), the page sensor's assumed accuracy against
    DeltaPen's measurement (ledger OPT-02)."""
    sim = _doc(SIM_DOC)
    # "Nose + heel wheel (± end-cap) | 324–503 µm (mean 403) | ..." (the mean appeared when more test writers finished)
    heel = _find(r"Nose \+ heel wheel \(± end-cap\) \| (\d+)–(\d+) µm(?: \(mean (\d+)\))?", sim, "the heel wheel's false correction", SIM_DOC)
    who = _find(r"SIM, test writers ([\d]+[–-][\d]+)", sim[sim.find("### 8.2"):], "the writers of the false-correction check", SIM_DOC)
    sp = load(SIM_PARAMS)["sim_params"]
    noise = ((sp.get("sensors") or {}).get("page_sensor") or {}).get("value", {}).get("noise_m")
    led = ""
    try:
        led = " ".join(next((r for r in load_csv(LEDGER) if r.get("id") == "OPT-02"), {}).values())
    except OSError:
        warn(f"{LEDGER} could not be read")
    dp = _find(r"MAE ([\d.]+) mm, median ([\d.]+) mm", led, "DeltaPen's measured error (OPT-02)", LEDGER)
    return {"heel_moved_mm": [int(heel[0]) / 1000, int(heel[1]) / 1000] if heel else None,
            "heel_mean_mm": (int(heel[2]) / 1000 if heel[2] else (int(heel[0]) + int(heel[1])) / 2000) if heel else None,
            "heel_writers": who[0] if who else None,
            "heel_label": "SIMULATION (sim2, docs/revJ_simulation.md §8.2)",
            "page_assumed_um": noise * 1e6 if noise else None, "page_label": "ASSUMPTION (results/revJ/sim_params.json: page sensor 3 µm)",
            "deltapen_um": [float(dp[1]) * 1000, float(dp[0]) * 1000] if dp else None,
            "deltapen_label": "LIT OPT-02 (DeltaPen, UIST 2022: median and mean error per 10 ms window, on a tablet)",
            "source": f"{SIM_DOC} §8.2; {SIM_PARAMS}; {LEDGER} OPT-02; {REVIEW_RESPONSE}"}


def facts_endcap_j1() -> dict:
    """Rev J.1's lighter end-cap (the current tail design, docs/revJ1_design.md §6.1): the chosen member's test verdict
    and the same mass locked in place (study K's model H1, read-only; test seeds 200-203)."""
    ec = load(REVJ1_ENDCAP)["endcap"]
    member = load(REVJ1_JSON)["endcap"]["member"]
    key = f"lrm_{member['L_s_mm']:g}"
    v = ec["test_j1m2"]["verdicts"][key]
    summ = ec["test_j1m2"]["summary"][key]
    fixed = [summ["weight_lrm"][sp]["8-12Hz_1-2mm"]["further_reduction_mean"] for sp in ("0.3", "0.5", "0.7")]
    mass = load(REVJ1_BUDGETS)["budgets"]["mass"]
    return {"endcap_g": mass["endcap_g"], "pen_with_endcap_g": (mass.get("with_endcap") or {}).get("mass_g"), "slug_g": member["slug_g"],
            "length_mm": member["L_shell_mm"], "stroke_mm": member["stroke_mm"],
            "moving": [v["r0.3"], v["r0.5"], v["r0.7"]], "fixed": fixed, "splits": [0.3, 0.5, 0.7],
            "label": SIM_H1, "detail": "Rev J.1's end-cap; on top of the Rev H nose and tracker; 8–12 Hz, 1–2 mm; test seeds 200–203",
            "source": f"{REVJ1_ENDCAP}; {REVJ1_BUDGETS}; docs/revJ1_design.md §6.1"}


def build_facts(lay: dict):
    srcs, facts = [], {"meta": {"built_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}}
    for key, fn, src in (("pen", lambda: facts_budgets(lay), f"{BUDGETS}, {REVJ}"), ("ai2", facts_ai2, AI2_JSON),
                         ("nose2", facts_nose2, NOSE2_JSON), ("drive", facts_drive, "results/drive/"),
                         ("endcap", facts_endcap, ENDCAP_JSON), ("endcap_j1", facts_endcap_j1, REVJ1_ENDCAP),
                         ("sideload", lambda: facts_sideload(lay), f"{SIM_PARAMS} + layout"),
                         ("known", facts_known, f"{SIM_DOC}, {LEDGER}")):
        try:
            facts[key] = fn()
            srcs.append(src)
        except (OSError, KeyError, ValueError, TypeError, AttributeError, IndexError) as ex:
            warn(f"facts '{key}' could not be built from {src} ({ex!r})")
            facts[key] = None
    facts["tip"] = {"travel_nom_mm": lay.get("tip_travel_mm"), "travel_guaranteed_mm": lay.get("tip_travel_min_35_75_mm"),
                    "pivot_mm": lay.get("pivot_z"), "lever": lay.get("lever_tip_per_magnet"),
                    "refill_slide_mm": lay.get("refill_slide_mm"), "ball_ahead_mm": lay.get("ball_protrusion_mm"),
                    "ring_r_mm": lay.get("skid_contact_radius"), "wheel_r_mm": lay.get("heel_contact_radius"),
                    "tilt_deg": lay.get("tilt_deg"), "revH_travel_guaranteed_mm": 2.75, "revH_pivot_mm": 45.0,
                    "revH_ring_r_mm": 6.75, "label": "CALC (results/revJ/layout.json); Rev H values from docs/revJ_design.md §2-§3"}
    rd = facts_realdata()
    if rd:
        facts["realdata"] = rd
        srcs.append(REALDATA_JSON)
    a3 = facts_ai3()
    if a3:
        facts["ai3"] = a3
        srcs.append(AI3_JSON)
    wp = facts_wholepen()
    if wp:
        facts["wholepen"] = wp
        srcs.append(WHOLEPEN_SUMMARY)
    s2 = facts_sim2j()
    if s2:
        facts["sim2j"] = s2
        srcs.append(SIM2J_ET + (f" + {SIM2J_CARDS}" if s2.get("cards") else ""))
    return facts, {"file": "pen.json", "source": " + ".join(srcs), "status": "final" if all(
        facts.get(k) for k in ("pen", "ai2", "nose2", "drive", "endcap", "endcap_j1", "sideload", "known")) else "provisional",
        "modified": mtime_utc(BUDGETS) if exists(BUDGETS) else "",
        "evidence": "CALC and SIMULATION on a PROPOSED DESIGN (labelled per number); nothing measured"}


# -------------------------------------------------------------------------------------------------- handwriting data
def runs(flags):
    out, s, n = [], 0, len(flags)
    while s < n:
        while s < n and not flags[s]:
            s += 1
        e_ = s
        while e_ < n and flags[e_]:
            e_ += 1
        if e_ - s > 1:
            out.append((s, e_))
        s = e_
    return out


def strokes_from(points, flags, stride=1):
    """Pen-down runs of a point list -> list of strokes [[x, y], ...] in mm (3 decimals)."""
    out = []
    for s, e_ in runs(flags):
        idx = list(range(s, e_, stride))
        if idx[-1] != e_ - 1:
            idx.append(e_ - 1)
        out.append([[r3(points[i][0]), r3(points[i][1])] for i in idx])
    return out


def metric(name, value, unit, evidence, nd=2, note=""):
    return {"name": name, "value": None if value is None else float(f"{value:.{nd}f}"), "unit": unit,
            "evidence": evidence, "note": note}


def _txt(name, text, ev, note=""):
    return {"name": name, "value": None, "text": text, "unit": "", "evidence": ev, "note": note}


def _change(v, ref):
    ch = 100 * (v / ref - 1)
    if abs(ch) < 0.5:
        return "about the same"
    return f"{abs(ch):.0f} % " + ("less" if ch < 0 else "more")


def _pts3(a, window=None):
    out = []
    for q in a:
        if not (isinstance(q, (list, tuple)) and len(q) >= 2):
            continue
        out.append([r3(q[0]), r3(q[1]), int(q[2]) if len(q) > 2 else 1])
    return out


def _plain_shake(scen: str) -> str:
    m = re.match(r"^(\d+(?:\.\d+)?)Hz_(\d+(?:\.\d+)?)mm$", scen)
    if m:
        return f"A shake of {m.group(2)} mm, {m.group(1)} times a second"
    return scen.replace("_", " ")


AI2_LABEL = {"none": "Ordinary pen", "tracker": "Rev H tracker (as built)",
             "gated": "Gated listening tracker (the earlier default; the physics simulation replaced it with the guarded tracker)",
             "learned_tcn": "Learned estimator (shadow mode: logged, not yet steering)",
             "clean_copy": "The app's clean copy (digital, made after writing; the paper keeps the ink)",
             "oracle": "If the pen knew the shake exactly (the limit)",
             "delayed_3mm": "Delayed ink, up to 25 ms (not used: -4 %, no more words)",
             "lag_100_6mm": "Delayed ink, 100 ms (not used: stroke ends are lost)",
             "rl_arbiter": "Reinforcement-learning arbiter (not used: moves clean writing too much)"}
AI2_ORDER = ["none", "tracker", "gated", "learned_tcn", "clean_copy", "oracle", "delayed_3mm", "lag_100_6mm", "rl_arbiter"]
AI2_KEY = {"none", "tracker", "gated", "learned_tcn", "clean_copy"}
AI2_ROLE = {"none": "before", "tracker": "other", "gated": "after", "learned_tcn": "after", "clean_copy": "after",
            "oracle": "limit"}
AI2_POINTS = {"none", "tracker", "gated", "learned_tcn", "oracle"}      # kept for the animated scenes a and b


def ai2_metrics(dev, m, ref, ev):
    out = []
    if _num(m.get("ink_err_um")) is not None:
        out.append(metric("Copy off the letters (digital)" if dev == "clean_copy" else "Ink off the letters, on average",
                          m["ink_err_um"] / 1000, "mm", ev, 2))
        if ref is not None and dev != "none" and (_num(ref.get("ink_err_um")) or 0) > 0:
            out.append(_txt("Compared with the ordinary pen", _change(m["ink_err_um"], ref["ink_err_um"]), ev))
    if _num(m.get("word_acc_app")) is not None:
        out.append(metric("Words the app reads right", 100 * m["word_acc_app"], "%", ev, 0))
    if (_num(m.get("lag_mean_ms")) or 0) > 0.5:
        out.append(metric("Ink trails the hand by", m["lag_mean_ms"], "ms", ev, 0))
    if m.get("app_words"):
        out.append(_txt("The app read", f"“{m['app_words']}”", ev))
    return out


def panels_ai2() -> list:
    raw = load(AI2_SAMPLES)
    groups: dict = {}
    for p in raw.get("panels", []):
        dev = str(p.get("device", ""))
        if dev not in AI2_LABEL:
            continue
        scen = str(p.get("id", "")).replace(f"ai2_{dev}_", "", 1)
        groups.setdefault(scen, {})[dev] = p
    panels = []
    for scen, devs in groups.items():
        if "none" not in devs:
            continue
        ref = devs["none"].get("metrics") or {}
        variants = []
        for dev in AI2_ORDER:
            q = devs.get(dev)
            if not q:
                continue
            pts = _pts3(q.get("ink", []))
            ink = strokes_from(pts, [p_[2] for p_ in pts])
            if not ink:
                continue
            v = {"key": dev, "role": AI2_ROLE.get(dev, "other"), "label": AI2_LABEL[dev], "key_device": dev in AI2_KEY,
                 "ink": ink, "metrics": ai2_metrics(dev, q.get("metrics") or {}, ref, SIM_HW1)}
            if dev in AI2_POINTS:
                v["points"] = pts
            variants.append(v)
        first = devs["none"]
        ipts = _pts3(first.get("intended", []))
        panels.append({
            "id": f"ai2_{scen}", "condition": "tremor", "source": AI2_SAMPLES, "evidence": SIM_HW1, "provisional": False,
            "title": _plain_shake(scen), "scenario": scen,
            "subtitle": ("One simulated writer (writer 0, seed 200) writes “return library books by friday”. The same hand and "
                         "the same shake for every row. The trackers drive the older Rev H inner-pen model (±3 mm) in this "
                         "study; the Rev J inner pen reaches further. The tremor detector needs about 4.5 s of writing before it switches the "
                         "listening tracker on, so the first word looks the same in every tracker row."),
            "ruling_mm": 8, "rate_hz": 50.0, "intended": strokes_from(ipts, [p_[2] for p_ in ipts]), "intended_points": ipts,
            "variants": variants,
            "note": "Writer 0, one seed; the averages over 6 writers and 4 seeds are in the table above."})
    order = {"6Hz_1mm": 0, "8Hz_2mm": 1, "10Hz_1mm": 2}
    panels.sort(key=lambda p: order.get(p["scenario"], 9))
    return panels


def panel_autowrite() -> dict | None:
    """The autowrite example of study N (writer 0, seed 200, 1 mm tremor at 8 Hz, 2.5 mm letters): the hand's path
    (1 kHz in the CSV, taken at the ink's 10 ms samples) and the ink with and without the pen lift."""
    rows = load_csv(NOSE2_EXAMPLE)
    ex = (load(NOSE2_JSON).get("example") or {})
    hand = {round(float(r["t_s"]) * 1000): [float(r["x_mm"]), float(r["y_mm"])] for r in rows if r["series"] == "hand"}
    series = {}
    for key in ("revJ", "revJ_noaxial"):
        pts = [[float(r["t_s"]), float(r["x_mm"]), float(r["y_mm"]), int(float(r["pen_down"] or 0))] for r in rows
               if r["series"] == key and r["detail"] == "ink"]
        series[key] = pts
    if not series.get("revJ") or not hand:
        return None
    t_ms = [round(p[0] * 1000) for p in series["revJ"]]
    hand_pts = [[r3(hand[t][0]), r3(hand[t][1]), 1] for t in t_ms if t in hand]
    if len(hand_pts) != len(t_ms):
        warn(f"{NOSE2_EXAMPLE}: hand and ink samples do not line up; autowrite panel skipped")
        return None
    m = ex.get("revJ") or {}
    mn = ex.get("revJ_noaxial") or {}
    ev = SIM_HW1

    def mets(mm, lift):
        out = [metric("Ink off the target letters, on average", (mm.get("ink_err_um") or 0) / 1000, "mm", ev, 3)]
        if _num(mm.get("letters_read")) is not None:
            out.append(metric("Letters the app reads right", 100 * mm["letters_read"], "%", ev, 0,
                              note=f"the clean target letters: {100 * (mm.get('target_letters_read') or 0):.0f} %"))
        if _num(mm.get("words_read_app")) is not None:
            out.append(metric("Words the app reads right", 100 * mm["words_read_app"], "%", ev, 0))
        if mm.get("recognised"):
            out.append(_txt("The app read", f"“{mm['recognised']}”", ev))
        if lift and _num(mm.get("letters_per_s")):
            out.append(metric("Letters per second", mm["letters_per_s"], "", ev, 1))
        return out

    v_h = _num(m.get("v_h_mm_s"))
    variants = [
        {"key": "hand", "role": "before", "key_device": True,
         "label": (f"The hand only sweeps along the line ({v_h:.1f} mm/s) with a 1 mm shake, 8 times a second. With the inner pen "
                   f"held still, the tip would follow this path." if v_h else "The hand's path"),
         "ink": [[p_[:2] for p_ in hand_pts]], "points": hand_pts,
         "metrics": [_txt("What the hand does", "a steady sweep plus the shake; it draws no letters", ev)]},
        {"key": "autowrite", "role": "after", "key_device": True,
         "label": "Autowrite on: the Rev J inner pen draws the known text, and the pen lift raises the ball between strokes",
         "ink": strokes_from([p_[1:3] for p_ in series["revJ"]], [p_[3] for p_ in series["revJ"]]),
         "points": [[r3(p_[1]), r3(p_[2]), p_[3]] for p_ in series["revJ"]], "metrics": mets(m, True)},
    ]
    if series.get("revJ_noaxial"):
        variants.append({"key": "autowrite_nolift", "role": "other", "key_device": False,
                         "label": "Same, without the pen lift: every move between letters is inked",
                         "ink": strokes_from([p_[1:3] for p_ in series["revJ_noaxial"]], [p_[3] for p_ in series["revJ_noaxial"]]),
                         "metrics": mets(mn, False)})
    return {"id": "autowrite_example", "condition": "autowrite", "source": f"{NOSE2_EXAMPLE} + {NOSE2_JSON} (example)",
            "evidence": ev, "provisional": False, "scenario": "8Hz_1mm",
            "title": "Autowrite: the pen writes a known text while you sweep",
            "subtitle": (f"Test writer {m.get('w', 0)}, seed {m.get('seed', 200)}: the pen knows the text “return library books by "
                         f"friday” and writes it in the writer's own style with {m.get('h_mm', 2.5):g} mm letters, while the hand "
                         "sweeps with a 1 mm shake at 8 Hz. Autowrite is a mode you turn on."),
            "ruling_mm": 8, "rate_hz": 100.0, "intended": [], "variants": variants,
            "note": "The grey target letters are not stored at full resolution in the study's files, so the strip shows the ink only."}


def panel_heel_lead() -> dict | None:
    """Study D's first autowrite test case (writer 0, seed 200): the heel drive leads a relaxed hand along the practice
    sentence at gross scale, the Rev H nose adds the detail (model HW1-D)."""
    t = load(DRIVE_TASKS)
    pf = (t.get("autowrite") or {}).get("paths_first_case") or {}
    rows = (t.get("autowrite") or {}).get("rows") or []
    first = {r["cond"]: r for r in rows if r.get("writer") == 0 and r.get("seed") == 200}
    spec = [("relaxed_nose", "before", True, "A relaxed hand, inner pen only: the tip cannot move the hand along the line"),
            ("sd_lead+nose", "after", True, "Lead-through on: the heel wheel leads the hand, the inner pen adds the detail"),
            ("writer_alone", "other", False, "For comparison: the same writer writing alone, at their own speed")]
    variants = []
    ev = SIM_HW1D
    for key, role, keyd, label in spec:
        P = pf.get(key)
        if not isinstance(P, list) or len(P) < 10:
            continue
        pts = [[p_[0], p_[1], 1 if p_[2] > 0.5 else 0] for p_ in P[::10]]
        ink = strokes_from([p_[:2] for p_ in pts], [p_[2] for p_ in pts])
        m = first.get(key) or {}
        mets = []
        if _num(m.get("letters_read_ok")) is not None:
            mets.append(metric("Letters the app reads right", 100 * m["letters_read_ok"], "%", ev, 0))
        if _num(m.get("words_app")) is not None:
            mets.append(metric("Words the app reads right", 100 * m["words_app"], "%", ev, 0))
        if m.get("recognised"):
            mets.append(_txt("The app read", f"“{m['recognised']}”", ev))
        if _num(m.get("pen_speed_mm_s")) is not None:
            mets.append(metric("Pen speed", m["pen_speed_mm_s"], "mm/s", ev, 1))
        if (_num(m.get("device_work_share")) or 0) > 0.01:
            mets.append(metric("Share of the work done by the pen", 100 * m["device_work_share"], "%", ev, 0))
        variants.append({"key": key, "role": role, "key_device": keyd, "label": label, "ink": ink, "metrics": mets})
    if len(variants) < 2:
        return None
    return {"id": "heel_lead_sentence", "condition": "heel", "source": f"{DRIVE_TASKS} (autowrite.paths_first_case)",
            "evidence": ev, "provisional": False, "scenario": "relaxed",
            "title": "The heel wheel leads a relaxed hand along a sentence",
            "subtitle": ("Test writer 0, seed 200, “a big dog dug a deep pit by the pond”. The writer relaxes and holds the pen "
                         "on the paper; in lead-through, a mode you turn on, the driven heel wheel pushes the pen and the hand "
                         "along the line. This study used the older Rev H inner pen for the detail; the integrated Rev J run is in the "
                         "whole-pen simulation."),
            "ruling_mm": 8, "rate_hz": 100.0, "intended": [], "variants": variants,
            "note": "The pen did most of the work here, by design: lead-through is for people who cannot write at all, or as a first stage that fades."}


SIM2J_LABEL = {"none": "Rev J pen, inner pen and wheel off", "nose": "Rev J inner pen, chosen tracker",
               "nose_wheel": "Rev J inner pen + heel wheel", "nose_wheel_ec": "Rev J inner pen + heel wheel + end-cap",
               "oracle": "Rev J inner pen, if it knew the shake exactly (the limit)",
               "autowrite": "Autowrite: the Rev J inner pen writes the known text"}
SIM2J_ORDER = ["none", "nose", "nose_wheel", "nose_wheel_ec", "oracle", "autowrite"]
SIM2J_ROLE = {"none": "before", "nose": "after", "nose_wheel": "after", "nose_wheel_ec": "after", "oracle": "limit",
              "autowrite": "after"}


def panels_sim2j() -> list:
    """results/sim2j/samples.json (handwriting samples schema, written by sim2j/report.py): one panel per scenario."""
    if not exists(SIM2J_SAMPLES):
        return []
    try:
        raw = load(SIM2J_SAMPLES)
    except (OSError, ValueError) as ex:
        warn(f"{SIM2J_SAMPLES} could not be read ({ex})")
        return []
    groups: dict = {}
    for p in raw.get("panels", []):
        dev = str(p.get("device", ""))
        pid = str(p.get("id", ""))
        scen = pid.replace("revj_", "", 1)
        for tok in sorted(SIM2J_LABEL, key=len, reverse=True):
            if scen.startswith(tok + "_"):
                scen = scen[len(tok) + 1:]
                break
        groups.setdefault(scen, []).append((dev, p))
    ev = SIM_SIM2
    panels = []
    for scen, items in groups.items():
        items.sort(key=lambda it: SIM2J_ORDER.index(it[0]) if it[0] in SIM2J_ORDER else 99)
        ref = next((p.get("metrics") or {} for d, p in items if d == "none"), None)
        variants = []
        for dev, p in items:
            pts = _pts3(p.get("ink", []))
            ink = strokes_from(pts, [q[2] for q in pts])
            if not ink:
                continue
            m = p.get("metrics") or {}
            mets = []
            if _num(m.get("ink_err_um")) is not None:
                mets.append(metric("Ink off the letters, on average", m["ink_err_um"] / 1000, "mm", ev, 2))
                if ref and dev != "none" and (_num(ref.get("ink_err_um")) or 0) > 0 and dev != "autowrite":
                    mets.append(_txt("Compared with the pen off", _change(m["ink_err_um"], ref["ink_err_um"]), ev))
            if _num(m.get("letters_read")) is not None:
                mets.append(metric("Letters the app reads right", 100 * m["letters_read"], "%", ev, 0))
            if _num(m.get("words_app")) is not None:
                mets.append(metric("Words the app reads right", 100 * m["words_app"], "%", ev, 0))
            if m.get("recognised"):
                mets.append(_txt("The app read", f"“{m['recognised']}”", ev))
            if _num(m.get("P_total_W")) is not None:
                mets.append(metric("Pen power", m["P_total_W"], "W", ev, 2))
            v = {"key": dev, "role": SIM2J_ROLE.get(dev, "other"), "label": SIM2J_LABEL.get(dev, p.get("title", dev)),
                 "key_device": dev in ("none", "nose", "nose_wheel", "autowrite"), "ink": ink, "metrics": mets}
            if dev in ("none", "nose", "nose_wheel", "oracle"):
                v["points"] = pts
            variants.append(v)
        if not variants:
            continue
        first = items[0][1]
        ipts = _pts3(first.get("intended", []))
        title = _plain_shake(scen)
        if items and any(d == "autowrite" for d, _ in items):
            title += ": pen off, and autowrite of the same text"
        panels.append({"id": f"sim2j_{scen}", "condition": "wholepen", "source": SIM2J_SAMPLES, "evidence": ev,
                       "provisional": False, "scenario": scen, "title": title,
                       "subtitle": re.sub(r"\s*\(seed \d+\)", "", str(first.get("caption", ""))),
                       "ruling_mm": 8, "rate_hz": 50.0, "intended": strokes_from(ipts, [q[2] for q in ipts]),
                       "intended_points": ipts, "variants": variants,
                       "note": "sim2 ranks designs; its numbers become evidence only after the bench tests calibrate it and EXP-V05 validates it."})
    return panels


def build_samples():
    panels, srcs = [], []
    for fn, src in ((panels_ai2, AI2_SAMPLES), (lambda: [p for p in [panel_autowrite()] if p], NOSE2_EXAMPLE),
                    (lambda: [p for p in [panel_heel_lead()] if p], DRIVE_TASKS), (panels_sim2j, SIM2J_SAMPLES),
                    (panels_realdata, REALDATA_SAMPLES)):
        try:
            ps = fn()
        except (OSError, KeyError, ValueError, TypeError, IndexError) as ex:
            warn(f"strips from {src} skipped ({ex!r})")
            ps = []
        if ps:
            panels.extend(ps)
            srcs.append(src)
    meta = {"provisional": False, "label": "simulation on synthetic writers and synthetic tremor; nothing measured",
            "evidence_status": "SIMULATION (models HW1, HW1-D and, when present, sim2); nothing measured",
            "sources": srcs, "sim2j": exists(SIM2J_SAMPLES)}
    return {"meta": meta, "units": "mm", "panels": panels}, {
        "file": "samples.json", "source": " + ".join(srcs), "status": "final" if panels else "provisional",
        "modified": mtime_utc(AI2_SAMPLES) if exists(AI2_SAMPLES) else "", "evidence": meta["evidence_status"],
        "panels": len(panels)}


# ------------------------------------------------------------------------------------------- whole-pen replay (a, b)
REPLAY_CASES = {"none": ("off", "Rev J pen, inner pen and wheel off"), "nose": ("today", "Rev J inner pen, chosen tracker"),
                "nose_wheel": ("wheel", "Rev J inner pen + heel wheel"), "oracle": ("best", "Rev J inner pen, if it knew the shake exactly")}


def _mm2(p):
    return [round(p[0] * 1000, 3), round(p[1] * 1000, 3)]


def build_replay():
    """Scenes (a) and (b) replay the whole-pen simulation (results/sim2j/viz_sim2j.json) when it exists: per case the
    handle's tip ('nib'), the ink, the pen axis and pen up/down, in mm and rad."""
    if not exists(SIM2J_REPLAY):
        return None, None
    try:
        v = load(SIM2J_REPLAY)
        meta = v.get("meta") or {}
        scen = str(meta.get("scenario", ""))
        m = re.search(r"([\d.]+)\s*Hz\s*x\s*([\d.]+)\s*mm", scen)
        f0, amp = (float(m.group(1)), float(m.group(2))) if m else (None, None)
        cases = {}
        for c in v.get("cases") or []:
            key = c.get("key")
            if key not in REPLAY_CASES:
                continue
            role, label = REPLAY_CASES[key]
            met = c.get("metrics") or {}
            cases[role] = {"key": key, "label": label, "study_label": c.get("label", ""), "description": c.get("description", ""),
                           "nib": [_mm2(p) for p in c["nib"]], "lift": [round(max(0.0, p[2]) * 1000, 3) for p in c["nib"]],
                           "ink": [_mm2(p) for p in c["ink"]], "ref": [_mm2(p) for p in c["ref_ink"]],
                           "axis": [[round(a, 5) for a in p[:3]] for p in c["axis"]],
                           "down": [1 if d else 0 for d in c["pen_down"]], "rm": None,
                           "ink_err_mm": round(met["ink_err_rms_um"] / 1000, 3) if _num(met.get("ink_err_rms_um")) is not None else None,
                           "ratio": round(met["ratio_vs_unmodified"], 3) if _num(met.get("ratio_vs_unmodified")) is not None else None,
                           "words": met.get("words_app"), "letters": met.get("letters_read")}
        if "off" not in cases or len(cases) < 2:
            warn(f"{SIM2J_REPLAY}: the replay cases were not found; scenes (a) and (b) keep the ai2 strips")
            return None, None
        out = {"meta": {"evidence_status": meta.get("evidence_status", SIM_SIM2), "generated_utc": meta.get("generated_utc"),
                        "model_version": meta.get("model_version"), "doc": "docs/revJ_simulation.md",
                        "units": "mm, rad; page frame x along the line, y up the page; axis = unit vector of the pen axis"},
               "scenarios": [{"id": "sim2j", "source": SIM2J_REPLAY, "f0_hz": f0, "amp_mm": amp,
                              "title": (f"A shake of {amp:g} mm, {f0:g} times a second" if f0 else "Tremor"),
                              "rate_hz": meta.get("rate_Hz", 200.0), "theta_deg": 50.0, "cases": cases}]}
        return out, {"file": "replay.json", "source": SIM2J_REPLAY, "status": "final", "modified": mtime_utc(SIM2J_REPLAY),
                     "evidence": out["meta"]["evidence_status"]}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as ex:
        warn(f"{SIM2J_REPLAY} could not be read ({ex})")
        return None, None


# ------------------------------------------------------------------------------------------------------------ tables
GROUP_NAMES = {"moving_nose": "Moving nose", "refill": "Ink refill", "grip": "Finger sleeve", "structure": "Handle shell",
               "skid": "Skid ring", "mechanism": "Pivot and pen lift", "actuator": "Coils and magnets", "sensor": "Sensors",
               "electronics": "Electronics", "power": "Battery", "haptic": "Vibration motor", "drive": "Heel drive",
               "inertial": "End-cap (detachable)", "magnet": "Board magnet"}


def dims(c: dict) -> str:
    if c.get("shape") == "box" and c.get("size"):
        s = c["size"]
        return f"{s[0]:g} × {s[1]:g} × {s[2]:g} mm"
    d0, d1 = c.get("d0"), c.get("d1")
    length = c["z1"] - c["z0"]
    if d0 is None:
        return f"{length:g} mm long"
    d = f"Ø{d0:g}" if d1 in (None, d0) else f"Ø{d0:g}–{d1:g}"
    return f"{d} × {length:.3g} mm"


def component_rows(lay: dict) -> str:
    rows = []
    comps = sorted(lay.get("components", []), key=lambda c: (c.get("z0", 0), c.get("z1", 0)))
    for c in comps:
        g = "skid" if "skid" in str(c.get("id", "")).lower() else c.get("group", "other")
        pills = []
        mw = c.get("moves_with")
        if mw == "nose":
            pills.append('<span class="pill move">moves with the inner pen</span>')
        elif mw == "drive":
            pills.append('<span class="pill move">steered or sprung with the heel wheel</span>')
        elif mw == "inertial_mass":
            pills.append('<span class="pill move">moves with the end-cap weight</span>')
        if g == "inertial":
            pills.append('<span class="pill opt">detachable end-cap</span>')
        elif c.get("optional"):
            pills.append('<span class="pill opt">optional</span>')
        if c.get("replaced_by_endcap"):
            pills.append('<span class="pill opt">replaced by the end-cap</span>')
        ledger = e(c["ledger"]) if c.get("ledger") else '<span class="muted">—</span>'
        mass = f" · {c['mass_g']:.2g} g" if _num(c.get("mass_g")) and c["mass_g"] >= 0.1 else ""
        rows.append(
            f'<tr data-part="{e(c.get("id", ""))}"><td><span class="sw g-{e(g)}" aria-hidden="true"></span>'
            f'<b>{e(c.get("label", c.get("id", "")))}</b><span class="where">{e(GROUP_NAMES.get(g, g))} · '
            f'z {c["z0"]:g}–{c["z1"]:g} mm · {e(dims(c))}{mass}</span>{"".join(pills)}</td>'
            f'<td>{e(c.get("function", ""))}</td><td>{e(c.get("part", ""))}</td><td class="mono">{ledger}</td></tr>')
    return "\n".join(rows)


def tag(ev: str, title: str = "") -> str:
    """The page's evidence tag, as tagHTML() in the template draws it; `title` (for example the source file) shows on hover."""
    s = str(ev or "").strip()
    ti = f' title="{e(title)}"' if title else ""
    for pat, cls, word in ((r"^SIM(ULATION)?", "sim", "Simulation"), (r"^CALC(ULATION)?", "calc", "Calculation"),
                           (r"^LIT(ERATURE)?", "lit", "Literature"), (r"^PROP(OSED)?( DESIGN)?", "prop", "Proposed design"),
                           (r"^ILL(USTRATION)?", "ill", "Illustration"), (r"^MFR", "mfr", "Manufacturer"),
                           (r"^ASS(UMPTION)?", "asm", "Assumption")):
        m = re.match(pat, s, re.I)
        if m:
            rest = re.sub(r"^[\s·:(-]+|[)\s]+$", "", s[m.end():])
            return f'<span class="tag {cls}"{ti}><i></i>{e(word)}{" · " + e(rest) if rest else ""}</span>'
    return f'<span class="tag asm"{ti}><i></i>{e(s or "Assumption")}</span>'


def _um(x):
    return f"{x:.0f} µm" if x is not None else "—"


def results_rows(f: dict) -> str:
    """The Rev J results table (docs/revJ_concept.md §2), each number read from its results file."""
    rows = []
    a, n2, d, ec = f.get("ai2"), f.get("nose2"), f.get("drive"), f.get("endcap")

    def row(who, help_, result, block, src, cls=""):
        ev, det = (block.get("label"), block.get("detail", "")) if isinstance(block, dict) else (block, "")
        cl = f' class="{cls}"' if cls else ""
        rows.append(f'<tr{cl}><td>{who}</td><td>{help_}</td><td>{result}</td>'
                    f'<td>{tag(ev)}<span class="where">{e(det)}{"; " if det else ""}{e(src)}</span></td></tr>')

    if a:
        n, tr, g, l_, c = a["none"], a["tracker"], a["gated"], a["learned_tcn"], a["clean_copy"]
        mv = (a.get("moved_um") or {}).get("gated")
        txt = (f"Ink off the letters <b>{_um(n['ink_um'])} → {_um(g['ink_um'])}</b> (ordinary pen → Rev J); Rev H's tracker "
               f"{_um(tr['ink_um'])}. Words read <b>{pct(n['words'])} % → {pct(g['words'])} %</b> (Rev H {pct(tr['words'])} %).")
        if mv:
            txt += f" Tremor-free writing moved {mv:.0f} µm, as with Rev H."
        row("Essential tremor, 1–2 mm, 6–10 shakes a second", "Tip: the inner pen with the <b>gated tracker</b> (the new default)",
            txt, a, "docs/ai_control_v2.md · results/ai2/ai2.json")
        row("Tremor at 6 shakes a second, 1–2 mm (where Rev H did almost nothing)", "The gated tracker",
            f"<b>{_um(n['ink_6hz_um'])} → {_um(g['ink_6hz_um'])}</b> (Rev H {_um(tr['ink_6hz_um'])})", a,
            "docs/ai_control_v2.md · results/ai2/ai2.json")
        row("Same tremor, a learned estimator", "A small causal neural network, in <b>shadow mode</b> (it logs, it does not steer)",
            f"<b>{_um(l_['ink_um'])}</b> and <b>{pct(l_['words'])} %</b> of words. It may drive the inner pen only after it passes on "
            "held-out real recordings (EXP-L04).", a, "docs/ai_control_v2.md · results/ai2/ai2.json")
    j1 = f.get("endcap_j1")
    if j1 and len(j1.get("moving") or []) == 3 and len(j1.get("fixed") or []) == 3:
        mv1, fx1 = j1["moving"], j1["fixed"]
        row("Tremor, on top of the inner pen (8–12 Hz, 1–2 mm)",
            f"Tail: Rev J.1's lighter <b>end-cap</b> ({j1['endcap_g']:.1f} g, a {j1['slug_g']:.1f} g moving weight), the current design",
            f"A further <b>{' / '.join(f'{100 * x:.1f}' for x in mv1)} %</b> less ink error at grip splits 0.3 / 0.5 / 0.7. The same mass "
            f"locked in place gives {' / '.join(f'{100 * x:.1f}' for x in fx1)} %: better at split 0.3. The tail stays optional until it "
            "beats a locked weight (by at least 10 %, the review's gate G5).", j1, "docs/revJ1_design.md §6.1 · results/revJ1/endcap.json")
    if ec:
        mv, fx, mw, fw = ec["moving"], ec["fixed"], ec["moving_worse"], ec["fixed_worse"]
        if all(x is not None for x in mv + fx + mw + fw):
            first_g = (f.get("pen") or {}).get("endcap_g")
            row("The same, the first end-cap design (superseded)",
                "Tail: the first <b>tungsten end-cap</b>" + (f" ({first_g:.0f} g in Rev J)" if first_g else ""),
                f"A further <b>{pct(mv[0])} / {pct(mv[1])} / {pct(mv[2])} %</b> less ink error at grip splits 0.3 / 0.5 / 0.7. The same "
                f"mass fixed gives {pct(fx[0])} / {pct(fx[1])} / {pct(fx[2])} % (better at 0.3), but it makes {pct(min(fw[1:]))}–{pct(max(fw[1:]))} % "
                f"of the hard cases worse (the moving weight {pct(min(mw))}–{pct(max(mw))} %).", ec,
                "docs/inertial_endcap.md · results/endcap/endcap_study.json")
    if n2:
        a0, a1, a2 = n2.get("aw_2p5_none") or {}, n2.get("aw_2p5_1mm") or {}, n2.get("aw_2p5_2mm") or {}
        row("Writing for you (a known text)", "Tip: <b>autowrite</b> with the ±6 mm inner pen (a mode you turn on)",
            f"<b>{pct(a1.get('letters_read', 0), 1)} %</b> of letters and <b>{pct(a1.get('words_read_app', 0))} %</b> of words read with up "
            f"to 1 mm of tremor; {pct(a2.get('words_read_app', 0))} % of words at 2 mm; {a0.get('letters_per_s', 0):.1f} letters a second. "
            "One of six test writers needed a slower sweep.", n2, "docs/nose_v2.md · results/nose2/nose2.json")
    if d:
        lp, tr_, ld, gr = d["loops"], d["tracing"], d["lead"], d["gross"]
        if lp.get("wheel") is not None:
            rs = [x for x in (lp.get("wheel_resist"), lp.get("sd_resist"), lp.get("sd_full_resist")) if x is not None]
            ll = d.get("loops_last") or {}
            last = (f" The last loop still shrinks: <b>{ll['wheel_path']:.2f}</b> of the target ({ll['none']:.2f} with nothing on"
                    + (f"; {ll['sd_full']:.2f} when the wheel also drives" if ll.get("sd_full") is not None else "") + ")."
                    if ll.get("wheel_path") is not None and ll.get("none") is not None else "")
            row("Parkinson's: “write big” loops that shrink", "Heel: the wheel, <b>steer only</b>",
                f"Tallest loop <b>{lp['wheel']:.2f}</b> of the target height (<b>{lp['none']:.2f}</b> with nothing on"
                + (f"; {min(rs):.2f}–{max(rs):.2f} for a hand that resists a little" if rs else "") + ")." + last,
                d, "docs/grounded_drive.md · results/drive/fig_loops_reversal.csv, tasks.json")
        t0, ts, tn = tr_.get("none"), tr_.get("sd_path"), tr_.get("wheel_path+nose")
        if t0 and ts and tn:
            row("Tracing and copying (poorly formed letters)", "Heel wheel steers; with or without the inner pen",
                f"Distance to the template <b>{_um(t0['err_um'])} → {_um(ts['err_um'])}</b> (steer only) → <b>{_um(tn['err_um'])}</b> "
                f"(with the inner pen). But letters read fall from <b>{pct(t0['letters'])} %</b> to {pct(ts['letters'])} % and "
                f"<b>{pct(tn['letters'])} %</b>: closer to the template is not easier to read.",
                d, "docs/grounded_drive.md · results/drive/fig_practice.csv")
        if ld.get("sd") is not None:
            row("Leading a relaxed hand through a letter", "Heel: the wheel, <b>driven</b> (lead-through, a mode you turn on)",
                f"In the reversed-letter demo the wheel drew <b>{pct(ld['sd'])} %</b> of the ‘d’ bowl within 0.3 mm of the template "
                f"(<b>{pct(ld['none'])} %</b> with nothing on)", d, "docs/grounded_drive.md · results/drive/fig_loops_reversal.csv")
        g1 = gr.get("sd_lead+nose") or {}
        if g1.get("letters_read_ok") is not None:
            g0 = gr.get("relaxed_nose") or {}
            row("Leading a relaxed hand along a sentence", "Heel wheel leads, the inner pen adds detail (lead-through)",
                f"<b>{pct(g1['letters_read_ok'])} %</b> of letters and <b>{pct(g1.get('words_app') or 0)} %</b> of words read, at "
                f"{g1.get('pen_speed_mm_s') or 0:.1f} mm/s; the pen did {pct(g1.get('device_work_share') or 0)} % of the work"
                + (f" (a relaxed hand with the inner pen only: {pct(g0['letters_read_ok'])} % of letters)" if g0.get("letters_read_ok") is not None else "")
                + ". The older Rev H inner pen in this run.", d, "docs/grounded_drive.md · results/drive/tasks.json")
        sb = d.get("set_on_b") or {}
        moved = [v.get("moved") for v in sb.values() if v and v.get("moved") is not None]
        fmax = [v.get("F_max_N") for k, v in sb.items() if v and k != "none" and v.get("F_max_N") is not None]
        if moved:
            row("A letter the writer is set on (a reversed ‘b’ against a ‘d’ template)", "Any guidance: inner pen, wheel or board",
                f"<b>{pct(max(moved))} %</b> turned into the other letter; the push stayed at or below {max(fmax):.2f} N. "
                "The writer always wins." if fmax else f"<b>{pct(max(moved))} %</b> turned into the other letter.",
                d, "docs/grounded_drive.md · docs/handwriting_outcomes.md")
    if a:
        c = a["clean_copy"]
        row("Severe tremor, notes", "The app's <b>clean copy</b> (digital, labelled)",
            f"<b>{pct(c['words'])} %</b> of words readable at 1–2 mm (the ink: {pct(a['gated']['words'])} %). The paper keeps the pen's ink.",
            a, "docs/ai_control_v2.md · docs/ai_severe_tremor.md")
    s2 = f.get("sim2j")
    if s2 and s2.get("rows"):
        want = [r for r in s2["rows"] if r["ctl"] in ("none", "nose", "nose_wheel", "nose_wheel_ec", "oracle")]
        want.sort(key=lambda r: ((r["amp_mm"] if isinstance(r["amp_mm"], (int, float)) else 99),
                                 ["none", "nose", "nose_wheel", "nose_wheel_ec", "oracle"].index(r["ctl"])))
        parts = []
        for r in want:
            amp = r["amp_mm"]
            amp_mm = amp * 1000 if isinstance(amp, float) and amp < 0.05 else amp
            nm = {"none": "pen off", "nose": "inner pen", "nose_wheel": "inner pen + wheel", "nose_wheel_ec": "inner pen + wheel + end-cap",
                  "oracle": "perfect knowledge"}[r["ctl"]]
            parts.append(f"{nm} at {amp_mm:g} mm: {_um(r['ink_um'])}" + (f" ({pct(r['words'])} % of words)" if r.get("words") is not None else ""))
        row("Whole Rev J pen, tremor (sim2, MuJoCo)", "Inner pen, heel wheel and end-cap together", "; ".join(parts),
            s2, "docs/revJ_simulation.md · results/sim2j/et.json", cls="s2")
    return "\n".join(rows)


def status_html(manifest: dict) -> str:
    names = {"layout.json": "Pen layout", "pen.json": "Numbers in the text, tables and charts",
             "samples.json": "Handwriting strips", "replay.json": "Whole-pen replay (scenes a and b)"}
    items = []
    for m in manifest["files"]:
        st = m["status"]
        cls = "final" if st == "final" else "prov"
        word = "final" if st == "final" else "provisional"
        items.append(f'<li><span class="st {cls}">{word}</span> {e(names.get(m["file"], m["file"]))}: '
                     f'<code>{e(m["source"])}</code></li>')
    if not any(m["file"] == "replay.json" for m in manifest["files"]) or SIM2J_PENDING:
        why = f": {e('; '.join(SIM2J_PENDING))}, so its numbers are not shown yet" if SIM2J_PENDING else ""
        items.append('<li><span class="st prov">pending</span> Whole-pen simulation (sim2j): '
                     f'<code>results/sim2j/</code> is still being computed{why}. Rebuild to add its results, strips and replay.</li>')
    for note in SIM2J_PARTIAL:
        items.append(f'<li><span class="st prov">partial</span> Whole-pen simulation (sim2j): {e(note)}; rebuild when it has run.</li>')
    return "<ul class=\"status\">" + "".join(items) + "</ul>"


def provenance_html(manifest: dict, lay: dict) -> str:
    meta = lay.get("meta") or {}
    bits = [f"Built {e(manifest['built_utc'])} from git {e(manifest['git_revision'])}"]
    if meta.get("parameters_version"):
        bits.append(f"parameters v{e(meta['parameters_version'])}")
    if meta.get("generated_utc"):
        bits.append(f"layout generated {e(meta['generated_utc'])}")
    return " · ".join(bits)


# ------------------------------------------------------------------------------------------------ the simple view
# The page opens with a simple view: one sentence per mechanism, and one "How much better?" row per condition with one
# picture pair and ONE number.  Both are specs below, so that a mechanism or a result can be swapped when a new study
# lands: edit the entry (text, picture source, number, evidence) and rebuild.  {tokens} in the sentences are the numbers
# of fact_tokens() (read from the results files).  Every number shown carries its evidence label.

MECHANISMS = [
    {"key": "tip", "n": 1, "tok": "--g-nose", "name": "The inner pen", "where": "at the tip",
     "sentence": ('<b class="mv">The whole inner pen</b> (the refill, its carrier and the arm, back to a pivot {pivot}&nbsp;mm '
                  'behind the ball) swings inside the handle you hold, <b>pushed by coils</b> on the magnets at its back end, '
                  'so <b>the ball moves up to {travel_s}&nbsp;mm</b> against the shake and the ink stays on your letters.'),
     "uses": ["steadies the ink", "writes for you, if you turn it on"],
     "note": "Being redesigned: holding the ball against the paper costs this design too much power (see Known problems).",
     "evidence": [("PROPOSED DESIGN", ""), ("CALCULATION", "reach and pivot: results/revJ/layout.json")]},
    {"key": "heel", "n": 2, "tok": "--g-drive", "name": "The heel wheel", "where": "under the front ring",
     "sentence": ('<b class="mv">A 2&nbsp;mm wheel under the front ring</b> grips the paper and is <b>steered, or driven, by two '
                  'tiny motors</b>, so <b>the paper pushes the whole pen and your hand</b> along the path of the letter, gently: '
                  'at most {trac_lo}–{trac_hi}&nbsp;N, about the weight of an egg.'),
     "uses": ["big-writing practice, if you turn it on", "leads your hand, if you turn it on"],
     "note": "Retracted by default: it is lowered onto the paper only when you turn guidance on (see Known problems).",
     "evidence": [("CALCULATION", "push: results/drive/fig_traction_capacity.csv (preload 0.55 N)"),
                  ("ASSUMPTION: tyre friction 0.6–1.2", "to be measured on paper (EXP-D01)"), ("PROPOSED DESIGN", "")]},
    {"key": "tail", "n": 3, "tok": "--g-inertial", "name": "The tail weight", "where": "in the end-cap you can take off",
     "sentence": ('<b class="mv">A {ec1_slug}&nbsp;g tungsten weight in the end-cap</b> is <b>pushed from side to side by coils</b>, '
                  'and its push-back is meant to <b>steady the whole pen</b>; it is far too weak to move letters.'),
     "uses": ["tested: no gain", "not in the product"],
     "note": ("Not in the product: a simpler model gave a further {ec1_rng}&nbsp;% less shake in the ink, but the whole-pen "
              "physics simulation gave no gain, and in study W no tail weight or gyroscope robustly beat a plain weight of the "
              "same mass locked in place. It stays only as a bench comparison."),
     "evidence": [("SIMULATION (model H1)", "results/revJ1/endcap.json: Rev J.1's lighter end-cap; 8-12 Hz, 1-2 mm, grip splits 0.3/0.5/0.7"),
                  ("SIMULATION (sim2, whole Rev J pen)", "results/sim2j/et.json: 0.67 of the ordinary pen's ink error with it, 0.65 without"),
                  ("PROPOSED DESIGN", "")]},
]

# Problems found after the design was drawn (the whole-pen physics simulation, docs/revJ_simulation.md §8, and the
# independent review of 29 September 2026 with the lead's response).  One plain line each, with its evidence; the
# numbers are computed in facts_sideload() / facts_known() from the design files, the simulation doc and the ledger.
KNOWN_PROBLEMS = [
    {"key": "sideload",
     "lead": "The inner pen's coils spend most of their power just holding the ball against the paper.",
     "text": ("Because the pen is tilted, the paper pushes the ball sideways, and the magnets sit on a short arm, so they must "
              "push about {kp_ratio} times harder. That is {kp_p50}&nbsp;W at a normal 50° angle and {kp_p35}&nbsp;W at 35°. "
              "The coils would overheat within about a minute. A balanced nib is being designed, so battery and heat figures "
              "are suspended."),
     "evidence": [("CALCULATION", "the independent review's formula, reproduced by the lead; inputs results/revJ/sim_params.json and layout.json"),
                  ("SIMULATION (sim2, the same load in a writing run)", "about {kp_sim} W of the nose's power in a writing run: docs/revJ_simulation.md §8.1")]},
    {"key": "heel",
     "lead": "The heel wheel moved clean writing by about {kp_heel}&nbsp;mm in the physics simulation,",
     "text": "so it stays retracted unless the writer turns guidance on.",
     "evidence": [("SIMULATION (sim2)", "{kp_heel_um}: docs/revJ_simulation.md §8.2")]},
    {"key": "sensor",
     "lead": "The page sensor was assumed accurate to {kp_page}&nbsp;µm (thousandths of a millimetre).",
     "text": ("A published research pen (DeltaPen, 2022) measured about {kp_dp_lo}–{kp_dp_hi}&nbsp;µm, so real accuracy "
              "is unproven."),
     "evidence": [("ASSUMPTION (the page sensor)", "{kp_page} µm, results/revJ/sim_params.json (page sensor noise)"),
                  ("LITERATURE · OPT-02", "DeltaPen (UIST 2022): median and mean error per 10 ms window, on a tablet surface; docs/evidence.csv")]},
    {"key": "data",
     "lead": "All writers and shakes so far are made up.",
     "text": "Real recordings are being brought in.",
     "evidence": [("SIMULATION: synthetic writers and shakes", "study R brings in real recordings: docs/round4_plan.md")]},
]
MECH_CHIP = {"tip": ("Inner pen", "--g-nose"), "heel": ("Heel wheel", "--g-drive"), "tail": ("Tail weight", "--g-inertial"),
             "app": ("The app", "--accent")}


def mechanisms_html(toks: dict) -> str:
    out = []
    for m in MECHANISMS:
        sent = re.sub(r"\{([a-z0-9_]+)\}", lambda mm: e(toks.get(mm.group(1), "—")), m["sentence"])
        uses = "".join(f"<span>{e(u)}</span>" for u in m["uses"])
        tags = "".join(tag(x, t) for x, t in m["evidence"])
        link = '<a href="#known">see Known problems</a>'
        nt = re.sub(r"\{([a-z0-9_]+)\}", lambda mm: str(toks.get(mm.group(1), "—")), m.get("note") or "").replace("&nbsp;", "\u00a0")
        note = f'<p class="mech-note">{e(nt).replace("see Known problems", link)}</p>' if nt else ""
        out.append(f'      <article class="mech" data-mech="{e(m["key"])}" style="--c:var({m["tok"]})">'
                   f'<h3><span class="anum">{m["n"]}</span>{e(m["name"])} <small>{e(m["where"])}</small></h3>'
                   f'<p class="mech-s">{sent}</p><div class="uses">{uses}</div>{note}<div class="tags">{tags}</div></article>')
    return "\n".join(out)


def known_tokens(f: dict) -> dict:
    sl, kn = f.get("sideload") or {}, f.get("known") or {}
    by = sl.get("by_angle") or {}
    b50, b35 = by.get("50") or {}, by.get("35") or {}
    hm, dp = kn.get("heel_moved_mm"), kn.get("deltapen_um")
    return {"kp_ratio": f"{sl['ratio']:.0f}" if sl.get("ratio") else "—", "kp_ratio1": f"{sl['ratio']:.1f}" if sl.get("ratio") else "—",
            "kp_p50": f"{b50['P_W']:.1f}" if b50 else "—", "kp_p35": f"{b35['P_W']:.1f}" if b35 else "—",
            "kp_sim": f"{sl['sim_run_W']:g}" if sl.get("sim_run_W") else "—",
            "kp_heel": f"{kn['heel_mean_mm']:.1f}" if kn.get("heel_mean_mm") else "—",
            "kp_heel_um": (f"{1000 * hm[0]:.0f}–{1000 * hm[1]:.0f} µm, mean {1000 * kn['heel_mean_mm']:.0f} µm"
                           + (f", test writers {kn['heel_writers']}" if kn.get("heel_writers") else "")) if hm else "—",
            "kp_page": f"{kn['page_assumed_um']:.0f}" if kn.get("page_assumed_um") else "—",
            "kp_dp_lo": f"{dp[0]:.0f}" if dp else "—", "kp_dp_hi": f"{dp[1]:.0f}" if dp else "—"}


def _fill(s: str, toks: dict) -> str:
    return re.sub(r"\{([a-z0-9_]+)\}", lambda mm: str(toks.get(mm.group(1), "—")), s)


def sideload_svg(sl: dict) -> str:
    """The static side load, drawn simply in two stacked panels (one SVG):
      1. At the ball, magnified: the refill spring presses the ball along the pen, the paper pushes straight up, and
         that push splits into a part along the pen (it balances the spring) and a part across it (the sideways push).
         The three forces to one scale (330 units per newton), the pen at 50°.
      2. The inner pen as a lever, drawn flat and to scale (2.25 units per mm, arms from the layout): the sideways push
         on the long arm, the magnets' force on the short arm, to one force scale (90 units per newton)."""
    th = math.radians(50.0)
    u = (math.cos(th), -math.sin(th))            # along the pen, from the ball up the pen (screen: y down)
    n_out = (-math.sin(th), -math.cos(th))       # across the pen, up and away from the paper (the sideways push)
    n_in = (-n_out[0], -n_out[1])
    row = sl["by_angle"]["50"]
    lt, la, fc = sl["L_t_mm"], sl["L_a_mm"], sl["F_c_N"]

    def f2(v):
        return f"{v:.2f}"

    def poly(pts, cls):
        return f'<polygon class="{cls}" points="{" ".join(f2(x) + "," + f2(y) for x, y in pts)}"/>'

    def arrow(p0, p1, cls):
        return (f'<line class="sl-ar {cls}" x1="{f2(p0[0])}" y1="{f2(p0[1])}" x2="{f2(p1[0])}" y2="{f2(p1[1])}" '
                f'marker-end="url(#sl-{cls})"/>')

    def line(p0, p1, cls):
        return f'<line class="{cls}" x1="{f2(p0[0])}" y1="{f2(p0[1])}" x2="{f2(p1[0])}" y2="{f2(p1[1])}"/>'

    def text(p, lines, cls="", anchor="start", lh=8.6):
        t = f'<text class="sl-t {cls}" x="{f2(p[0])}" y="{f2(p[1])}" text-anchor="{anchor}">'
        for i_, ln in enumerate(lines):
            t += f'<tspan x="{f2(p[0])}" dy="{0 if i_ == 0 else lh}">{ln}</tspan>'
        return t + "</text>"

    g = []
    # ---- panel 1: at the ball, magnified -------------------------------------------------------------------------
    k1 = 330.0
    yp, bx, br = 122.0, 104.0, 3.6                # the paper line, the contact point, the ball's radius (drawing units)
    C = (bx, yp - br)                             # the ball's centre: the pen's axis passes through it

    def P(t, q=0.0, o=C):
        return (o[0] + u[0] * t + n_out[0] * q, o[1] + u[1] * t + n_out[1] * q)
    g.append(text((2, 11), ["1 · At the ball (magnified)"], "sl-h1"))
    g.append(f'<rect class="sl-desk" x="0" y="{f2(yp)}" width="230" height="10"/>'
             f'<line class="sl-paper" x1="0" x2="230" y1="{f2(yp)}" y2="{f2(yp)}"/>')
    g.append(text((226, yp + 7.6), ["paper"], "sl-m", "end"))
    g.append(poly([P(2.2, -1.5), P(15, -4.2), P(116, -4.2), P(116, 4.2), P(15, 4.2), P(2.2, 1.5)], "sl-inner"))
    g.append(f'<circle class="sl-ball" cx="{f2(C[0])}" cy="{f2(C[1])}" r="{br}"/>')
    g.append(text(P(104, 9), ["the inner pen"], "sl-m", "end"))
    B = (bx, yp)
    n_tip = (bx, yp - row["N_N"] * k1)
    s_tip = (bx + n_out[0] * row["F_perp_N"] * k1, yp + n_out[1] * row["F_perp_N"] * k1)
    sp0, sp1 = P(30 + fc * k1, -11), P(30, -11)
    g.append(line(s_tip, n_tip, "sl-comp"))
    g.append(arrow(sp0, sp1, "spring"))
    g.append(arrow(B, n_tip, "paper"))
    g.append(arrow(B, s_tip, "side"))
    g.append(text((sp1[0] + 19, sp1[1] - 10), ["the spring pushes", "the ball along", f"the pen: {fc:.2f} N"], "sl-b"))
    # the pen's angle to the paper
    ra = 15.0
    g.append(f'<path class="sl-dim" d="M{f2(bx + ra)} {f2(yp)}A{ra} {ra} 0 0 0 {f2(bx + ra * u[0])} {f2(yp + ra * u[1])}"/>')
    g.append(text((bx + 19.5, yp - 3.2), ["50°"], "sl-m"))
    g.append(text((bx - 5, n_tip[1] + 3), ["the paper pushes", f"straight up: {row['N_N']:.2f} N"], "", "end"))
    g.append(text(((s_tip[0] + n_tip[0]) / 2 - 6, (s_tip[1] + n_tip[1]) / 2 + 2), ["along the pen:", "balances the spring"], "sl-m", "end"))
    g.append(text((s_tip[0] - 4, s_tip[1] + 8), ["sideways part:", f"{row['F_perp_N']:.3f} N"], "sl-r", "end"))
    # ---- panel 2: the inner pen is a lever (drawn flat, to scale) -----------------------------------------------
    s2, k2 = 2.25, 90.0
    yb, x0 = 262.0, 14.0
    xp, xm = x0 + lt * s2, x0 + (lt + la) * s2
    g.append(f'<line class="sl-sep" x1="0" x2="230" y1="146" y2="146"/>')
    g.append(text((2, 160), ["2 · The inner pen is a lever"], "sl-h1"))
    g.append(text((2, 170), ["drawn flat, to scale"], "sl-m"))
    g.append(f'<rect class="sl-inner" x="{f2(x0)}" y="{f2(yb - 3)}" width="{f2(xm - x0)}" height="6"/>')
    g.append(f'<circle class="sl-ball" cx="{f2(x0 - 1.5)}" cy="{f2(yb)}" r="3.4"/>')
    g.append(f'<rect class="sl-mag" x="{f2(xm - 5)}" y="{f2(yb - 10)}" width="10" height="20"/>')
    g.append(poly([(xp, yb + 3), (xp - 6.5, yb + 14), (xp + 6.5, yb + 14)], "sl-pivot"))
    g.append(line((xp - 11, yb + 14.5), (xp + 11, yb + 14.5), "sl-ground"))
    g.append(text((xp - 9, yb + 12), ["pivot"], "sl-p", "end"))
    g.append(arrow((x0, yb - 4.5), (x0, yb - 4.5 - row["F_perp_N"] * k2), "side"))
    g.append(arrow((xm, yb - 11), (xm, yb - 11 - row["F_act_N"] * k2), "mag"))
    g.append(text((x0 + 6, yb - 8.5), [f"sideways part: {row['F_perp_N']:.3f} N"], "sl-r"))
    g.append(text((xm - 8, yb - 11 - row["F_act_N"] * k2 + 8), ["the magnets must push", f"{row['F_act_N']:.2f} N: {sl['ratio']:.1f} times more"], "sl-r", "end"))
    yd = yb + 25
    for xa, xb_ in ((x0, xp), (xp, xm)):
        g.append(line((xa, yd), (xb_, yd), "sl-dim"))
    for xt in (x0, xp, xm):
        g.append(line((xt, yd - 4), (xt, yd + 4), "sl-dim"))
    g.append(text(((x0 + xp) / 2 - 10, yd + 10), [f"the ball's arm: {lt:.1f} mm"], "sl-m", "middle"))
    g.append(text((xm + 5, yd + 10), ["the magnets' arm:", f"{la:.1f} mm"], "sl-m", "end", lh=8))
    defs = "".join(f'<marker id="sl-{k_}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="3.6" markerHeight="3.6" '
                   f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="sl-h {k_}"/></marker>'
                   for k_ in ("spring", "paper", "side", "mag"))
    return (f'<svg class="sideload" id="sideload" viewBox="0 0 230 {f2(yd + 22)}" role="img" aria-labelledby="sl-t sl-d">'
            f'<title id="sl-t">Why the inner pen needs so much power just to hold the ball on the paper</title>'
            f'<desc id="sl-d">At the ball: the refill spring presses the ball along the pen with {fc:.2f} N. The paper pushes back '
            f'straight up with {row["N_N"]:.2f} N; the part of that push along the pen balances the spring, and the part across the '
            f'pen is {row["F_perp_N"]:.3f} N at 50 degrees. The lever: that sideways push acts {lt:.1f} mm from the pivot, while '
            f'the magnets sit {la:.1f} mm from it on the other side, so they must push {row["F_act_N"]:.2f} N, {sl["ratio"]:.1f} '
            f'times more, all the time the ball touches the paper.</desc>'
            f'<defs>{defs}</defs>{"".join(g)}</svg>')


def known_problems_html(f: dict) -> str:
    """The 'Known problems (being fixed)' panel: four plain lines and the side-load figure."""
    toks = known_tokens(f)
    items = []
    for kp in KNOWN_PROBLEMS:
        tags = "".join(tag(_fill(x, toks), _fill(t, toks)) for x, t in kp["evidence"])
        items.append(f'<li data-kp="{e(kp["key"])}"><p><b>{_fill(kp["lead"], toks)}</b> {_fill(kp["text"], toks)}</p>'
                     f'<div class="tags">{tags}</div></li>')
    sl = f.get("sideload")
    fig = ""
    if sl and (sl.get("by_angle") or {}).get("50"):
        r50, r35 = sl["by_angle"]["50"], sl["by_angle"].get("35") or {}
        t_lim = r50.get("t_limit_s")
        cost = (f'Holding it costs {r50["P_W"]:.1f}&nbsp;W at 50° and {r35.get("P_W", 0):.1f}&nbsp;W at 35°, all the time the ball touches '
                f'the paper; a flatter pen is worse. At 50° the coil would pass its {sl["coil_limit_C"]:.0f}&nbsp;°C limit after about '
                f'{5 * round(t_lim / 5):.0f}&nbsp;s of writing.' if t_lim else "")
        fig = (f'<figure class="slfig">{sideload_svg(sl)}<figcaption><b>Why the nib must change.</b> The spring presses the ball along '
               f'the pen; the paper pushes back straight up. The part of that push across the pen (red) tries to swing the inner pen '
               f'about its pivot. It acts on a long arm and the magnets on a short one, so the magnets must push '
               f'{sl["ratio"]:.1f} times harder:'
               f'<span class="sl-eq">{r50["F_perp_N"]:.3f}&nbsp;N × {sl["L_t_mm"]:.1f}&nbsp;mm = {r50["F_act_N"]:.2f}&nbsp;N × '
               f'{sl["L_a_mm"]:.1f}&nbsp;mm</span>{cost}'
               f'<span class="tags">{tag("CALCULATION", sl["label"] + "; " + sl["source"])}'
               f'{tag("ILLUSTRATION (the lever and the forces to scale)")}</span></figcaption></figure>')
    return (f'<div class="known-grid"><ol class="known-list">{"".join(items)}</ol>{fig}</div>')


def _clip(strokes, x0, x1):
    """Strokes cut to the window x0..x1 (a stroke leaving the window is split)."""
    out = []
    for s_ in strokes or []:
        cur = []
        for p_ in s_:
            if x0 <= p_[0] <= x1:
                cur.append(p_)
            elif cur:
                if len(cur) > 1:
                    out.append(cur)
                cur = []
        if len(cur) > 1:
            out.append(cur)
    return out


def _d(strokes) -> str:
    d = []
    for s_ in strokes:
        d.append("M" + " L".join(f"{p_[0]:.1f} {-p_[1]:.1f}" for p_ in s_))
    return "".join(d)


def thumb_svg(layers, x0, x1, y0, y1, label, ruled=(0.0, 8.0), extra=""):
    """A small picture of writing in mm: layers = [(css class, strokes)], window x0..x1, y0..y1 (y up)."""
    w, h = x1 - x0, y1 - y0
    body = [f'<rect class="pp" x="{x0:.2f}" y="{-y1:.2f}" width="{w:.2f}" height="{h:.2f}"/>']
    for y in ruled:
        if y0 <= y <= y1:
            body.append(f'<line class="rl" x1="{x0:.2f}" x2="{x1:.2f}" y1="{-y:.2f}" y2="{-y:.2f}"/>')
    body.append(extra)
    for cls, strokes in layers:
        d = _d(_clip(strokes, x0, x1))
        if d:
            body.append(f'<path class="{cls}" d="{d}"/>')
    return (f'<svg class="thumb" viewBox="{x0:.2f} {-y1:.2f} {w:.2f} {h:.2f}" role="img" aria-label="{e(label)}">'
            + "".join(body) + "</svg>")


def loops_strokes(first, last, n=8, h0=10.0):
    """Cursive practice loops whose height goes in a straight line from first to last (fractions of h0): an
    illustration drawn from two numbers of the drive study (the tallest and the last loop)."""
    pts, x = [], 0.0
    for i in range(n):
        k = first + (last - first) * i / (n - 1)
        hh, w, r = h0 * k, 0.5 * h0, 0.17 * h0 * k
        for j in range(0 if i == 0 else 1, 41):
            s_ = j / 40
            px, py = x + w * s_ - r * math.sin(2 * math.pi * s_), hh * (1 - math.cos(2 * math.pi * s_)) / 2
            pts.append([round(px + 0.3 * py, 3), round(py, 3)])
        x += w
    return [pts]


def loops_from_heights(heights, h0=10.0):
    """Cursive practice loops of the given heights (mm): the heights come from the simulation, the loop shapes are
    drawn (an illustration)."""
    pts, x = [], 0.0
    for i, hh in enumerate(heights):
        w, r = 0.5 * h0, 0.17 * hh
        for j in range(0 if i == 0 else 1, 41):
            s_ = j / 40
            px, py = x + w * s_ - r * math.sin(2 * math.pi * s_), hh * (1 - math.cos(2 * math.pi * s_)) / 2
            pts.append([round(px + 0.3 * py, 3), round(py, 3)])
        x += w
    return [pts]


def _panel(samples, pid):
    return next((p for p in (samples.get("panels") or []) if p.get("id") == pid), None)


def _variant(panel, key):
    return next((v for v in (panel or {}).get("variants", []) if v.get("key") == key), None)


def pic_pair(samples, spec):
    """(before svg, after svg) for a picture spec: from a strip panel, or the loops illustration."""
    x0, x1 = spec["x"]
    y0, y1 = spec.get("y", (-3.4, 7.6))
    if spec.get("kind") == "loops_h":
        tgt = (f'<line class="tgt" x1="{x0:.2f}" x2="{x1:.2f}" y1="-10" y2="-10"/>'
               f'<text class="lbl" x="{x0 + 0.8:.2f}" y="-10.6">target height</text>')
        b = thumb_svg([("ink before", loops_from_heights(spec["before"]))], x0, x1, y0, y1, spec["cap"][0], ruled=(0.0,), extra=tgt)
        a = thumb_svg([("ink after", loops_from_heights(spec["after"]))], x0, x1, y0, y1, spec["cap"][1], ruled=(0.0,), extra=tgt)
        return b, a
    if spec.get("kind") == "loops":
        tgt = (f'<line class="tgt" x1="{x0:.2f}" x2="{x1:.2f}" y1="-10" y2="-10"/>'
               f'<text class="lbl" x="{x0 + 0.8:.2f}" y="-10.6">target height</text>')
        b = thumb_svg([("ink before", loops_strokes(*spec["before"]))], x0, x1, y0, y1, spec["cap"][0], ruled=(0.0,), extra=tgt)
        a = thumb_svg([("ink after", loops_strokes(*spec["after"]))], x0, x1, y0, y1, spec["cap"][1], ruled=(0.0,), extra=tgt)
        return b, a
    p = _panel(samples, spec["panel"])
    vb, va = _variant(p, spec["before"]), _variant(p, spec["after"])
    if not (p and vb and va):
        return None
    intended = p.get("intended") if spec.get("intended", True) else []
    cls_b = "ink hand" if spec["before"] == "hand" else "ink before"
    b = thumb_svg(([("int", intended)] if intended else []) + [(cls_b, vb["ink"])], x0, x1, y0, y1, spec["cap"][0])
    a = thumb_svg(([("int", intended)] if intended else []) + [("ink after", va["ink"])], x0, x1, y0, y1, spec["cap"][1])
    return b, a


def _pc(x):
    return None if x is None else round(100 * x)


def simple_rows_revj(f: dict) -> list:
    """The rows of "How much better?" from the whole-pen physics simulation of Rev J (results/sim2j/cards.json): one
    row per condition, one number each.  Rows the physics simulation did not cover (the app's clean copy) come from
    the earlier studies, labelled as such."""
    s2 = f.get("sim2j") or {}
    C = s2.get("cards") or {}
    a, j1 = f.get("ai2") or {}, f.get("endcap_j1") or {}
    part = s2.get("partial_note")
    src = SIM2J_CARDS
    ev_note = "Physics simulation of the whole Rev J pen, with simulated writers and simulated shakes."
    rows = []

    def pc10(x):                      # words or letters out of 10 -> per cent
        return None if x is None else round(10 * x)

    def pooled(ids, i, key="words"):
        cs = [C[k] for k in ids if k in C and C[k].get(key) and C[k][key][i] is not None]
        n = sum(c["n"] for c in cs)
        return sum(c[key][i] * c["n"] for c in cs) / n if n else None
    fast = [k for k in ("et_moderate", "et_strong") if k in C]
    if fast:
        n = sum(C[k]["n"] for k in fast)
        rf = s2.get("ratio_fast")
        rows.append({
            "id": "tremor", "mech": ["tip"], "who": "A shaky hand, simulated shake", "sub": "A fast shake of 1–2 mm, 8–12 times a second, made up by the computer",
            "help": "The inner pen tilts against the shake, so the ball stays on the letters.",
            "pic": {"panel": "sim2j_8Hz_2mm", "before": "none", "after": "nose", "x": (-1.5, 40.0),
                    "cap": ("Ordinary pen", "With the inner pen"),
                    "note": "One simulated writer writing “return library” with a 2 mm shake, 8 times a second. Grey: what the writer meant."},
            "num": {"label": "Words read correctly", "b": pc10(pooled(fast, 0)), "a": pc10(pooled(fast, 1)), "unit": "%",
                    "sub": (f"shake left at the tip: {rf:.2f} of the ordinary pen's; " if rf is not None else "")
                           + f"average of {n} simulated cases" + (f" ({part})" if part else "")},
            "verdict": "Clearly better for a simulated fast shake. Not yet for a real one (next row).",
            "ev": [SIM_SIM2], "src": src, "ev_note": ev_note})
    rd = (f.get("realdata") or {}).get("severe") or {}
    if rd.get("none", {}).get("words") is not None and rd.get("gated", {}).get("words") is not None:
        lim, cw = rd.get("oracle", {}).get("words"), rd.get("clean_words")
        rows.append({
            "id": "real", "mech": ["tip"], "who": "A shaky hand, real recorded shake", "sub": "Parkinson's and essential tremor recorded from patients: a severe shake at the pen tip (about 1.7 mm)",
            "help": "Real tremor of real patients, added to real handwriting, in the hand–pen simulation. The inner pen with today's tracker.",
            "pic": {"panel": "real_real_pd_severe", "before": "none", "after": "oracle", "x": (-1.0, 58.0), "y": (-4.0, 10.0),
                    "cap": ("Ordinary pen", "If the pen knew the shake exactly (not achieved yet)"),
                    "note": "Letters of one real writer (UCI Character Trajectories, CC BY) with a real Parkinson's tremor recording scaled to the severe size. Today's tracker looks like the left picture."},
            "num": {"label": "Words read correctly", "b": round(10 * rd["none"]["words"]), "a": round(10 * rd["gated"]["words"]), "unit": "%",
                    "sub": (f"with today's tracker; if the pen knew the shake exactly: {round(10 * lim)} %" if lim is not None else "with today's tracker")
                           + (f" (the same notes with no tremor: {round(10 * cw)} %)" if cw is not None else "") + ". 9 held-out writers"},
            "verdict": "No help yet on real tremor. The pen has the reach; it cannot yet estimate a real, irregular shake in time.",
            "ev": [SIM_REAL], "src": REALDATA_JSON,
            "ev_note": "Real handwriting and real tremor recorded by others, in the simpler hand–pen model (HW1); not a measurement of the pen or of any person."})
    if "slow_4hz" in C:
        c = C["slow_4hz"]
        lim = s2.get("ratio_slow_limit")
        rows.append({
            "id": "slow", "mech": ["tip"], "who": "A slow shake", "sub": "Parkinson's-type tremor: 1–2 mm, 4 times a second",
            "help": "The inner pen could cancel it, but the pen cannot yet tell a slow shake from the writing itself, so it stays still.",
            "pic": None, "nopic": "No picture: the ink is the same with and without the pen.",
            "num": {"label": "Words read correctly", "b": pc10(c["words"][0]), "a": pc10(c["words"][1]), "unit": "%",
                    "sub": (f"if the pen knew the shake exactly it would remove about {5 * round((100 - 100 * lim) / 5)} % of it: "
                            "telling shake from writing is the missing piece" if lim is not None else "")
                           + f"; {c['n']} simulated cases"},
            "verdict": "No help yet. This is the biggest open gap.",
            "ev": [SIM_SIM2], "src": src, "ev_note": ev_note})
    if "severe_autowrite" in C:
        c, t = C["severe_autowrite"], C.get("severe_through")
        rows.append({
            "id": "autowrite", "mech": ["tip"], "who": "Too shaky to write", "sub": "A severe shake of 3 mm: autowrite, a mode you turn on",
            "help": "You sweep the pen along the line; the inner pen writes a text you chose: typed, spoken, or a suggestion you accepted.",
            "pic": {"panel": "sim2j_5Hz_3mm", "before": "none", "after": "autowrite", "x": (-1.5, 40.0), "intended": False,
                    "cap": ("Ordinary pen", "The pen writes it"),
                    "note": "One simulated writer with a 3 mm shake, 5 times a second. The pen writes “return library” in 2.5 mm letters."},
            "num": {"label": "Words read correctly", "b": pc10(c["words"][0]), "a": pc10(c["words"][1]), "unit": "%",
                    "sub": (f"writing through the shake with the inner pen instead: {pc10(t['words'][1])} %; " if t else "")
                           + f"{c['n']} simulated cases (6 writers, 2 shake speeds)"},
            "verdict": "Readable. It writes only text you chose.",
            "status": "Suspended as a hardware claim: the current inner pen would overheat (see Known problems).",
            "ev": [SIM_SIM2], "src": src, "ev_note": ev_note})
    if "loops_relaxed" in C:
        c, r2 = C["loops_relaxed"], C.get("loops_resisting")
        hb, ha = (c.get("loop_heights_mm") or [[], []])
        rows.append({
            "id": "loops", "mech": ["heel"], "who": "Writing that gets smaller", "sub": "Parkinson's: big practice loops that shrink",
            "help": "For practice, the driven heel wheel pushes the pen along the loops.",
            "pic": ({"kind": "loops_h", "before": hb, "after": ha, "x": (-1.5, 30.0), "y": (-1.2, 13.6),
                     "cap": ("Nothing on", "Heel wheel pushing"),
                     "note": "Loop heights from the simulation (average of 2 runs, relaxed hand); the loop shapes are drawn.",
                     "ill": True} if hb and ha else None),
            "nopic": "No picture.",
            "num": {"label": "Size of the last loop, against the target", "b": round(10 * c["last_loop_mm"][0]),
                    "a": round(10 * c["last_loop_mm"][1]), "unit": "%",
                    "sub": "relaxed hand" + (f" ({round(10 * r2['last_loop_mm'][1])} % with a lightly resisting hand)" if r2 else "")
                           + f"; {c['n']} simulated runs each"},
            "verdict": "Better: the loops stay bigger. The pen pushes your hand to do it.",
            "ev": [SIM_SIM2, "ILLUSTRATION (the loop shapes)"], "src": src, "ev_note": ev_note})
    if "tracing" in C:
        c = C["tracing"]
        rows.append({
            "id": "tracing", "mech": ["tip"], "who": "Poorly formed letters", "sub": "Copying practice (dysgraphia-like writers)",
            "help": "The inner pen pulls the ink half-way toward the copybook letter.",
            "pic": None, "nopic": "No writing pictures were saved from this run.",
            "num": {"label": "Distance to the copybook letters", "b": f"{c['err_mm'][0]:.2f}", "a": f"{c['err_mm'][1]:.2f}", "unit": "mm",
                    "sub": f"words read stay at {pc10(c['words'][1])} %; {c['n']} simulated writers. Pulling harder got closer "
                           "(0.27 mm) but only 63 % of words were read"},
            "verdict": "A little closer, and just as readable.",
            "ev": [SIM_SIM2], "src": src, "ev_note": ev_note})
    a3 = f.get("ai3") or {}
    if a3.get("pause_fixed_of10") is not None:
        rows.append({
            "id": "spell", "mech": ["app", "tip"], "who": "A word you cannot spell", "sub": "Dyslexia: the app spots a misspelling, and the pen gives a small tick at the next pause",
            "help": "The app reads your letters as you write. When a word looks misspelled, the pen ticks once at the next pause and the app shows the right spelling. Your ink is never changed.",
            "pic": None, "nopic": "Try it yourself: the spelling prototype page (ai3/demo/index.html in the project files).",
            "num": {"label": "Misspellings put right on paper", "b": 0, "a": round(10 * a3["pause_fixed_of10"]), "unit": "%",
                    "sub": (f"the app spots {round(100 * a3['caught_known'])} % of real misspellings when it knows the letters, "
                            f"{round(100 * a3['caught_own'])} % when the pen reads them itself, with about {a3['fa_known']:.0f} false alarms per 100 words. "
                            "How writers respond to the tick is assumed")},
            "verdict": "A real help, from the app's spelling check. Leading the hand through the spelling helped little.",
            "ev": [a3.get("label", "SIMULATION")], "src": AI3_JSON, "ev_note": "Real children's misspellings and real letters; the writers' responses are assumptions."})
    if a3.get("top3_after1"):
        lo, hi = a3["top3_after1"]
        rows.append({
            "id": "predict", "mech": ["app"], "who": "Finding the next word", "sub": "Anyone, when writing is slow or tiring",
            "help": "After your first letter the app offers the likeliest words; if you accept one, the pen can write the rest for you.",
            "pic": None, "nopic": "No picture: suggestions appear in the app.",
            "num": {"label": "Right word among 3 suggestions after one letter", "text": f"{round(100 * lo)}–{round(100 * hi)} %",
                    "sub": "on a person's own running text, in about 3 ms"},
            "verdict": "Saves effort, not time: letting the pen finish a word takes a typical writer about 15 % longer.",
            "ev": [a3.get("label", "CALCULATION")], "src": AI3_JSON, "ev_note": ""})
    rec = s2.get("ratio_fast_ec")
    rw = s2.get("ratio_fast_wheel")
    if rec is not None and rw is not None:
        mv = j1.get("moving") or []
        h1 = f"; the simpler model had given {_pc(min(mv))}–{_pc(max(mv))} % less" if len(mv) == 3 and None not in mv else ""
        rows.append({
            "id": "tail", "mech": ["tail"], "who": "A fast shake, with the tail weight on", "sub": "The optional end-cap",
            "help": "A weight in the end-cap is pushed against the shake, on top of the inner pen and the heel wheel.",
            "pic": None, "nopic": "No writing pictures for this comparison.",
            "num": {"label": "Shake left in the ink", "text": "no better",
                    "sub": f"{rec:.2f} of the ordinary pen's with it, {rw:.2f} without, in the physics simulation{h1}"},
            "verdict": "No gain here, so the tail weight is not in the product.",
            "ev": [SIM_SIM2], "src": SIM2J_ET, "ev_note": ev_note})
    wp = f.get("wholepen") or {}
    if wp.get("collar_gain"):
        g0, g1 = wp["collar_gain"]
        rows.append({
            "id": "collar", "mech": ["tip"], "who": "Moving the whole pen", "sub": "A collar you hold; the whole inner pen swings inside it on a hinge",
            "help": "We designed the strongest compact way to shift the whole pen (±4 mm at the tip, 40 g, very little holding power) and tested it on top of the moving nose.",
            "pic": None, "nopic": "No writing pictures for this comparison.",
            "num": {"label": "Shake left, against the same pen with the collar locked", "text": "no better",
                    "sub": f"{100 * g0:+.0f} % to {100 * g1:+.0f} % in the simulation (a real gain would need at least 10 %)"},
            "verdict": "Not adopted: the moving nose already reaches far enough. Knowing the shake in time is what is missing.",
            "ev": [wp.get("label", "SIMULATION")], "src": WHOLEPEN_SUMMARY, "ev_note": ""})
    if a.get("gated") and a.get("clean_copy"):
        rows.append({
            "id": "clean", "mech": ["app"], "who": "Notes you must read later", "sub": "A strong shake",
            "help": "The app keeps a clean copy of what you wrote, clearly labelled as a copy. The paper keeps your ink.",
            "pic": {"panel": "ai2_8Hz_2mm", "before": "gated", "after": "clean_copy", "x": (25.5, 65.0),
                    "cap": ("Your ink, with the inner pen", "The app's clean copy (digital)"),
                    "note": "One simulated writer with a 2 mm shake, 8 times a second (earlier, simpler model)."},
            "num": {"label": "Words read correctly", "b": _pc(a["gated"]["words"]), "a": _pc(a["clean_copy"]["words"]), "unit": "%",
                    "sub": "the ink → the app's copy; 6 simulated writers, shakes of 1–2 mm"},
            "verdict": "Readable in the app; the paper still shows the shaky ink.",
            "ev": [a.get("label", "SIMULATION")], "src": "results/ai2/ai2.json",
            "ev_note": "From the earlier, simpler hand–pen model (HW1), not the physics simulation."})
    if "no_tremor" in C:
        c = C["no_tremor"]
        rows.append({
            "id": "normal", "mech": ["tip"], "who": "Normal writing", "sub": "No tremor",
            "help": "The pen should change nothing when there is no shake.",
            "pic": None, "nopic": "No picture: the ink is the same with and without the pen.",
            "num": {"label": "Change to the writing", "text": f"{c['moved_clean_mm']:.0f} mm",
                    "sub": f"with the inner pen ({c['n']} simulated writers). The heel wheel, switched on, changed it by "
                           f"{c['moved_clean_wheel_mm']:.2f} mm, so it stays tucked away"},
            "verdict": "Leaves normal writing alone.",
            "ev": [SIM_SIM2], "src": src, "ev_note": ev_note})
    return rows


def simple_rows(f: dict) -> list:
    """The rows of "How much better?" (condition, picture, one number, evidence).  Each number is read from pen.json's
    facts (built from the results files named in the evidence detail).  With the whole-pen physics simulation's
    results cards present, the rows come from it (simple_rows_revj)."""
    if (f.get("sim2j") or {}).get("cards"):
        return simple_rows_revj(f)
    a, n2, d, ec = f.get("ai2") or {}, f.get("nose2") or {}, f.get("drive") or {}, f.get("endcap") or {}
    rows = []
    if a.get("none") and a.get("gated"):
        rows.append({
            "id": "tremor", "mech": ["tip"], "who": "A shaky hand", "sub": "Essential tremor: a shake of 1–2 mm",
            "help": "The inner pen moves against the shake.",
            "pic": {"panel": "ai2_8Hz_2mm", "before": "none", "after": "gated", "x": (25.5, 65.0),
                    "cap": ("Ordinary pen", "With the inner pen"),
                    "note": "One simulated writer with a 2 mm shake, 8 times a second, writing “books by friday”. Grey: what the writer meant."},
            "num": {"label": "Words read correctly", "b": _pc(a["none"]["words"]), "a": _pc(a["gated"]["words"]), "unit": "%",
                    "sub": "average of 6 simulated writers, 4 shakes each (1–2 mm, 6–10 a second)"},
            "verdict": "Clearly better, not perfect.",
            "ev": [a.get("label", "SIMULATION")], "src": "results/ai2/ai2.json",
            "ev_note": "The tracker was tested on the older (Rev H) inner pen model, which reaches ±3 mm."})
    j1 = f.get("endcap_j1") or {}
    mv, fx = j1.get("moving") or [], j1.get("fixed") or []
    if len(mv) == 3 and None not in mv:
        better_locked = [i for i in range(3) if len(fx) == 3 and fx[i] is not None and fx[i] > mv[i]]
        rows.append({
            "id": "tail", "mech": ["tail"], "who": "A fast shake, with the end-cap on", "sub": "Essential tremor: 8–12 shakes a second",
            "help": (f"The tail weight pushes against the shake, on top of the inner pen. Rev J.1's lighter end-cap: "
                     f"{j1['endcap_g']:.1f} g, with a {j1['slug_g']:.1f} g weight."),
            "pic": None, "nopic": "No writing pictures: this study saved numbers only.",
            "num": {"label": "Shake left in the ink", "text": f"{_pc(min(mv))}–{_pc(max(mv))} % less",
                    "sub": "than with the inner pen alone; it depends on how you hold the pen"},
            "verdict": ("Small. A plain weight of the same mass, locked in place, did better for "
                        f"{'one of the three grips' if len(better_locked) == 1 else str(len(better_locked)) + ' of the three grips'}, "
                        "so the tail stays optional until it beats a locked weight." if better_locked else "A small extra help."),
            "ev": [j1.get("label", "SIMULATION")], "src": "results/revJ1/endcap.json (Rev J.1)", "ev_note": ""})
    a1 = n2.get("aw_2p5_1mm") or {}
    if a1.get("letters_read") is not None:
        rows.append({
            "id": "autowrite", "mech": ["tip"], "who": "Too shaky to write", "sub": "Autowrite, a mode you turn on",
            "help": "You sweep the pen along the line; the inner pen writes a text you chose, in your own style.",
            "pic": {"panel": "autowrite_example", "before": "hand", "after": "autowrite", "x": (20.0, 59.0), "y": (-2.4, 6.6),
                    "intended": False, "cap": ("What your hand does: a sweep", "What the pen writes"),
                    "note": "One simulated writer with a 1 mm shake, 8 times a second; 2.5 mm letters."},
            "num": {"label": "Letters read correctly", "a": _pc(a1["letters_read"]), "unit": "%",
                    "sub": "with a shake of up to 1 mm; average of 6 simulated writers"},
            "verdict": "Nearly every letter readable. It writes only text you chose.",
            "status": "Suspended as a hardware claim: the current inner pen would overheat (see Known problems).",
            "ev": [n2.get("label", "SIMULATION")], "src": "results/nose2/nose2.json", "ev_note": ""})
    last, tall = d.get("loops_last") or {}, d.get("loops_tallest") or {}
    if last.get("none") is not None and last.get("wheel_path") is not None and tall.get("none") and tall.get("wheel_path"):
        rows.append({
            "id": "loops", "mech": ["heel"], "who": "Writing that gets smaller", "sub": "Parkinson's: big practice loops that shrink",
            "help": "The heel wheel steers along the loops.",
            "pic": {"kind": "loops", "before": (tall["none"], last["none"]), "after": (tall["wheel_path"], last["wheel_path"]),
                    "x": (-1.5, 43.0), "y": (-1.2, 13.6), "cap": ("Nothing on", "Heel wheel steering"),
                    "note": "Drawn from two numbers of the simulation: the tallest and the last loop; the loops between are drawn in a straight line.",
                    "ill": True},
            "num": {"label": "Size of the last loop, against the target", "b": _pc(last["none"]), "a": _pc(last["wheel_path"]), "unit": "%",
                    "sub": "average of 4 runs, relaxed hand, steering only"},
            "verdict": "Better, but the loops still shrink.",
            "ev": [d.get("label", "SIMULATION"), "ILLUSTRATION (the pictures)"], "src": "results/drive/tasks.json (loops)", "ev_note": ""})
    g = d.get("gross") or {}
    r0, r1 = g.get("relaxed_nose") or {}, g.get("sd_lead+nose") or {}
    if r0.get("letters_read_ok") is not None and r1.get("letters_read_ok") is not None:
        rows.append({
            "id": "lead", "mech": ["heel", "tip"], "who": "Cannot form letters yet", "sub": "Lead-through, a mode you turn on",
            "help": "The driven heel wheel leads a relaxed hand along the line; the inner pen adds the detail.",
            "pic": {"panel": "heel_lead_sentence", "before": "relaxed_nose", "after": "sd_lead+nose", "x": (0.0, 40.0), "y": (-2.4, 6.6),
                    "intended": False, "cap": ("Relaxed hand, inner pen only", "Heel wheel leads the hand"),
                    "note": "One simulated writer, “a big dog dug a deep pit by the pond”."},
            "num": {"label": "Letters read correctly", "b": _pc(r0["letters_read_ok"]), "a": _pc(r1["letters_read_ok"]), "unit": "%",
                    "sub": "average of 6 simulated writers"},
            "verdict": "Much better, but the pen does most of the work.",
            "ev": [d.get("label", "SIMULATION")], "src": "results/drive/tasks.json (autowrite)",
            "ev_note": "This study used the older (Rev H) inner pen for the detail."})
    tr = d.get("tracing") or {}
    t0, tn = tr.get("none") or {}, tr.get("wheel_path+nose") or {}
    ex = d.get("tracing_example") or {}
    if t0.get("letters") is not None and tn.get("letters") is not None:
        rows.append({
            "id": "tracing", "mech": ["heel", "tip"], "who": "Tracing practice", "sub": "Poor handwriting (dysgraphia-like writers)",
            "help": "The heel wheel steers along the template and the inner pen corrects toward it.",
            "pic": None, "readas": [("Nothing on", (ex.get("none") or {}).get("read")),
                                    ("Heel wheel and inner pen", (ex.get("wheel_path+nose") or {}).get("read"))],
            "nopic": "No writing pictures were saved in this study. This is what the reading program read for one simulated writer copying “a big dog dug a deep pit by the pond”:",
            "num": {"label": "Letters read correctly", "b": _pc(t0["letters"]), "a": _pc(tn["letters"]), "unit": "%", "worse": True,
                    "sub": "average of 6 simulated writers"},
            "verdict": "Worse: the ink gets closer to the template, but the letters get harder to read.",
            "ev": [d.get("label", "SIMULATION")], "src": "results/drive/fig_practice.csv", "ev_note": ""})
    if a.get("gated") and a.get("clean_copy"):
        rows.append({
            "id": "clean", "mech": ["app"], "who": "Notes you must read later", "sub": "A strong shake",
            "help": "The app keeps a clean copy of what you wrote, clearly labelled as a copy. The paper keeps your ink.",
            "pic": {"panel": "ai2_8Hz_2mm", "before": "gated", "after": "clean_copy", "x": (25.5, 65.0),
                    "cap": ("Your ink, with the inner pen", "The app's clean copy (digital)"),
                    "note": "The same writer and shake as in the first row."},
            "num": {"label": "Words read correctly", "b": _pc(a["gated"]["words"]), "a": _pc(a["clean_copy"]["words"]), "unit": "%",
                    "sub": "the ink → the app's copy; same writers and shakes as the first row"},
            "verdict": "Readable in the app; the paper still shows the shaky ink.",
            "ev": [a.get("label", "SIMULATION")], "src": "results/ai2/ai2.json", "ev_note": ""})
    return rows


def sim2j_row(f: dict, samples: dict):
    """When the whole-pen simulation (results/sim2j/) has run: one more row, pen off against the full pen."""
    s2 = f.get("sim2j") or {}
    pan = [p for p in (samples.get("panels") or []) if p.get("condition") == "wholepen"]
    if not s2 and not pan:
        return None
    best = None
    for p in pan:
        keys = [v["key"] for v in p.get("variants", [])]
        after = next((k for k in ("nose_wheel_ec", "nose_wheel", "nose") if k in keys), None)
        if "none" in keys and after:
            best = (p, after)
            break
    num = None
    rows = [r for r in (s2.get("rows") or []) if r.get("words") is not None]
    if rows:
        off = [r for r in rows if r["ctl"] == "none"]
        on = [r for r in rows if r["ctl"] in ("nose_wheel_ec", "nose_wheel", "nose")]
        if off and on:
            amp = off[0]["amp_mm"]
            on_same = [r for r in on if r["amp_mm"] == amp] or on
            pick = sorted(on_same, key=lambda r: ["nose_wheel_ec", "nose_wheel", "nose"].index(r["ctl"]))[0]
            parts_ = {"nose": "inner pen", "nose_wheel": "inner pen and heel wheel",
                      "nose_wheel_ec": "inner pen, heel wheel and tail weight"}[pick["ctl"]]
            amp_mm = amp * 1000 if isinstance(amp, float) and amp < 0.05 else amp
            shake = f", a {amp_mm:g} mm shake" if isinstance(amp_mm, (int, float)) else ""
            num = {"label": "Words read correctly", "b": _pc(off[0]["words"]), "a": _pc(pick["words"]), "unit": "%",
                   "sub": f"pen off → {parts_} on, in the physics simulator{shake}"}
    if not best and not num:
        return None
    pic = None
    if best:
        p, after = best
        xs = [q[0] for s_ in (p.get("intended") or []) for q in s_] or [0, 40]
        pic = {"panel": p["id"], "before": "none", "after": after, "x": (max(min(xs), max(xs) - 39.5) - 0.5, max(xs) + 0.5),
               "cap": ("Pen off", "The whole pen on"), "note": str(p.get("title", ""))}
    return {"id": "wholepen", "mech": ["tip", "heel", "tail"], "who": "The whole pen together", "sub": "Tremor, in the physics simulator (sim2)",
            "help": "The inner pen, the heel wheel and the tail weight working at once.",
            "pic": pic, "nopic": "No writing pictures in the results yet.",
            "num": num or {"label": "Words read correctly", "text": "see Details", "sub": ""},
            "verdict": "", "ev": [SIM_SIM2], "src": "results/sim2j/", "ev_note": "sim2 ranks designs until bench tests calibrate it."}


def simple_results_html(f: dict, samples: dict) -> str:
    rows = simple_rows(f)
    r2 = None if (f.get("sim2j") or {}).get("cards") else sim2j_row(f, samples)
    if r2:
        rows.insert(1, r2)
    out = []
    for r in rows:
        chips = "".join(f'<span class="mchip" style="--c:var({MECH_CHIP[m][1]})">{e(MECH_CHIP[m][0])}</span>' for m in r["mech"])
        who = (f'<div class="bwho"><h3>{e(r["who"])}</h3><p>{e(r["sub"])}</p><p>{e(r["help"])}</p>'
               f'<div class="mchips">{chips}</div></div>')
        pic = ""
        spec = r.get("pic")
        pair = pic_pair(samples, spec) if spec else None
        if pair:
            b, a = pair
            cb = "hand" if spec.get("before") == "hand" else "shake"
            pic = (f'<div class="bpics"><figure><figcaption><span class="ln" style="--c:var(--{"muted" if cb == "hand" else "shake"})"></span>{e(spec["cap"][0])}</figcaption>{b}</figure>'
                   f'<figure><figcaption><span class="ln" style="--c:var(--accent)"></span>{e(spec["cap"][1])}</figcaption>{a}</figure>'
                   f'<p class="pnote">{e(spec.get("note", ""))} {tag("ILLUSTRATION") if spec.get("ill") else ""}</p></div>')
        elif r.get("readas"):
            ra = "".join(f'<div class="ra"><b>{e(k)}:</b><q>{e(v or "—")}</q></div>' for k, v in r["readas"])
            pic = f'<div class="readas"><p class="bnote">{e(r.get("nopic", ""))}</p>{ra}</div>'
        else:
            pic = f'<div class="readas"><p class="bnote">{e(r.get("nopic", ""))}</p></div>'
        n = r["num"]
        if n.get("text") is not None:
            val = f'<span class="b1">{e(n["text"])}</span>'
        elif n.get("b") is not None:
            val = (f'<span class="b0">{n["b"]}&nbsp;{e(n["unit"])}</span><span class="ar" aria-label="to">→</span>'
                   f'<span class="b1">{n["a"]}&nbsp;{e(n["unit"])}</span>')
        else:
            val = f'<span class="b1">{n["a"]}&nbsp;{e(n["unit"])}</span>'
        tags = "".join(tag(x, r["src"]) for x in r["ev"])
        src = (f'<span class="bnote">{e(r["ev_note"])}</span>' if r.get("ev_note") else "") + f'<span class="bnote mono">{e(r["src"])}</span>'
        num = (f'<div class="bnum"><span class="bl">{e(n["label"])}</span><span class="bv{" worse" if n.get("worse") else ""}">{val}</span>'
               f'<span class="bs">{e(n.get("sub", ""))}</span>'
               + (f'<span class="verdict">{e(r["verdict"])}</span>' if r.get("verdict") else "")
               + (f'<a class="bstat" href="#known">{e(r["status"])}</a>' if r.get("status") else "")
               + f'<div class="tags">{tags}</div>{src}</div>')
        out.append(f'      <article class="brow" data-row="{e(r["id"])}">{who}{pic}{num}</article>')
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- [[fact]] tokens
def fmt_num(v, nd=1) -> str:
    if v is None:
        return "—"
    return f"{v:.{nd}f}"


def fmt_short(v) -> str:
    """6.0 -> "6", 6.49 -> "6.5" """
    if v is None:
        return "—"
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


def fmt_range(r, nd=1) -> str:
    return f"{r[0]:.{nd}f}–{r[1]:.{nd}f}" if r else "—"


def fact_tokens(f: dict, lay: dict) -> dict:
    p, tip, n2, d, ec, a = f.get("pen") or {}, f.get("tip") or {}, f.get("nose2") or {}, f.get("drive") or {}, \
        f.get("endcap") or {}, f.get("ai2") or {}
    h, hec, hg = p.get("hours", {}), p.get("hours_endcap", {}), p.get("hours_gated", {})
    heat = p.get("heat_1mm") or {}
    t055 = sorted(d.get("traction_055") or [], key=lambda x: x["mu"])
    tok = {
        "od": fmt_num(p.get("od_mm"), 0), "len": fmt_num(p.get("length_mm")), "len_ec": fmt_num(p.get("length_endcap_mm")),
        "mass": fmt_num(p.get("mass_g")), "mass_ec": fmt_num(p.get("mass_endcap_g")), "ec_g": fmt_num(p.get("endcap_g")),
        "com": fmt_num(p.get("com_mm"), 0), "com_ec": fmt_num(p.get("com_endcap_mm"), 0),
        "travel": fmt_num(tip.get("travel_guaranteed_mm")), "travel_nom": fmt_num(tip.get("travel_nom_mm"), 2),
        "travel_s": fmt_short(tip.get("travel_guaranteed_mm")),
        "pivot": fmt_num(tip.get("pivot_mm")), "lever": fmt_num(tip.get("lever")), "slide": fmt_num(tip.get("refill_slide_mm")),
        "ring_r": fmt_num(tip.get("ring_r_mm"), 2), "wheel_r": fmt_num(tip.get("wheel_r_mm")), "ball_ahead": fmt_num(tip.get("ball_ahead_mm")),
        "h_steady1": fmt_range(h.get("steady_1mm")), "h_steady0": fmt_range(h.get("steady_no_tremor")),
        "h_steady1_gated": fmt_range(hg.get("steady_1mm")), "h_guide": fmt_range(h.get("guide")),
        "h_lead": fmt_range(h.get("lead")), "h_aw0": fmt_range(h.get("autowrite_no_tremor")),
        "h_aw1": fmt_range(h.get("autowrite_1mm")), "h_steady1_ec": fmt_range(hec.get("steady_1mm")),
        "base_mw": f"{p['base_load_mW'][0]:.0f}–{p['base_load_mW'][1]:.0f}" if p.get("base_load_mW") else "—",
        "web_23": fmt_num(heat.get("web_surface_C")), "web_30": fmt_num(heat.get("web_surface_C_hot_room")),
        "web_30_spr": fmt_num((heat.get("with_spreader") or {}).get("web_surface_C_hot_room")),
        "coil_rise": fmt_num(heat.get("coil_rise_K_100KW")),
        "pull": fmt_num(p.get("axial_pull_N")), "fit_n": str(p.get("fit_n") or "—"),
        "trac_lo": fmt_num(t055[0]["cap_N"], 1) if t055 else "—", "trac_hi": fmt_num(t055[-1]["cap_N"], 1) if t055 else "—",
        "aw_letters": fmt_num(100 * ((n2.get("aw_2p5_1mm") or {}).get("letters_read") or 0)),
        "aw_rate": fmt_num((n2.get("aw_2p5_none") or {}).get("letters_per_s")),
        "gated_um": fmt_num((a.get("gated") or {}).get("ink_um"), 0), "none_um": fmt_num((a.get("none") or {}).get("ink_um"), 0),
        "revh_um": fmt_num((a.get("tracker") or {}).get("ink_um"), 0),
        "none6_um": fmt_num((a.get("none") or {}).get("ink_6hz_um"), 0), "revh6_um": fmt_num((a.get("tracker") or {}).get("ink_6hz_um"), 0),
        "gated6_um": fmt_num((a.get("gated") or {}).get("ink_6hz_um"), 0),
        "ec_mid": fmt_num(100 * (ec.get("moving") or [0, 0, 0])[1], 0),
        "slug_g": fmt_num(sum(c.get("mass_g") or 0 for c in lay.get("components", []) if c.get("moves_with") == "inertial_mass") or None, 0),
        "ec_rng": (f"{100 * min(ec['moving']):.0f}–{100 * max(ec['moving']):.0f}" if ec.get("moving") and None not in ec["moving"] else "—"),
    }
    j1 = f.get("endcap_j1") or {}
    mv1, fx1 = j1.get("moving") or [], j1.get("fixed") or []
    ok1 = len(mv1) == 3 and None not in mv1
    tok.update({
        "ec1_g": fmt_num(j1.get("endcap_g")), "ec1_pen": fmt_num(j1.get("pen_with_endcap_g")), "ec1_slug": fmt_num(j1.get("slug_g"), 0), "ec1_slug_1": fmt_num(j1.get("slug_g")),
        "ec1_len": fmt_num(j1.get("length_mm"), 0),
        "ec1_rng": f"{100 * min(mv1):.0f}–{100 * max(mv1):.0f}" if ok1 else "—",
        "ec1_splits": " / ".join(f"{100 * x:.1f}" for x in mv1) if ok1 else "—",
        "ec1_fixed": " / ".join(f"{100 * x:.1f}" for x in fx1) if len(fx1) == 3 and None not in fx1 else "—",
    })
    last, tall = d.get("loops_last") or {}, d.get("loops_tallest") or {}
    tok.update({"loop_tall_wheel": fmt_num(tall.get("wheel_path"), 2), "loop_tall_none": fmt_num(tall.get("none"), 2),
                "loop_last_wheel": fmt_num(last.get("wheel_path"), 2), "loop_last_none": fmt_num(last.get("none"), 2)})
    tok.update(known_tokens(f))
    return tok


# -------------------------------------------------------------------------------------------------------------- main
def dump(obj, name):
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
    return os.path.getsize(p)


def main():
    os.makedirs(DATA, exist_ok=True)
    lay, m_lay = build_layout()
    facts, m_facts = build_facts(lay)
    samples, m_samp = build_samples()
    replay, m_rep = build_replay()
    files = [m_lay, m_facts, m_samp] + ([m_rep] if m_rep else [])
    manifest = {"built_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "git_revision": git_revision(), "files": files, "warnings": WARNINGS,
                "sim2j": {"samples": exists(SIM2J_SAMPLES), "replay": exists(SIM2J_REPLAY), "et": exists(SIM2J_ET),
                          "et_shown": bool(facts.get("sim2j")), "pending": SIM2J_PENDING}}
    sizes = {"layout.json": dump(lay, "layout.json"), "pen.json": dump(facts, "pen.json"),
             "samples.json": dump(samples, "samples.json")}
    rp = os.path.join(DATA, "replay.json")
    if replay is not None:
        sizes["replay.json"] = dump(replay, "replay.json")
    elif os.path.exists(rp):
        os.remove(rp)
    for name in STALE:
        if os.path.exists(os.path.join(DATA, name)):
            os.remove(os.path.join(DATA, name))
    sizes["manifest.json"] = dump(manifest, "manifest.json")
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        page = f.read()
    toks = fact_tokens(facts, lay)
    fills = {"<!--BUILD:COMPONENT_ROWS-->": component_rows(lay), "<!--BUILD:DATA_STATUS-->": status_html(manifest),
             "<!--BUILD:PROVENANCE-->": provenance_html(manifest, lay), "<!--BUILD:RESULT_ROWS-->": results_rows(facts),
             "<!--BUILD:MECHANISMS-->": mechanisms_html(toks), "<!--BUILD:SIMPLE_RESULTS-->": simple_results_html(facts, samples),
             "<!--BUILD:KNOWN_PROBLEMS-->": known_problems_html(facts)}
    for k, v in fills.items():
        if k not in page:
            warn(f"template.html has no {k} placeholder")
        page = page.replace(k, v)
    # [[fact]] tokens are filled in the markup only (the script, which starts at the first <script, is left alone)
    cut = page.find("<script")
    head, tail = (page[:cut], page[cut:]) if cut >= 0 else (page, "")
    tok_re = r"\[\[([A-Za-z][A-Za-z0-9_]*)\]\]"
    missing = sorted(set(re.findall(tok_re, head)) - set(toks))
    if missing:
        warn(f"template.html uses unknown [[tokens]]: {', '.join(missing)}")
    empty = sorted(k for k in set(re.findall(tok_re, head)) if toks.get(k) in (None, "—"))
    if empty:
        warn(f"[[tokens]] without a value (shown as a dash): {', '.join(empty)}")
    page = re.sub(tok_re, lambda m: e(toks.get(m.group(1), "—")), head) + tail
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, ROOT)} ({len(page.encode('utf-8'))} bytes)")
    for m in manifest["files"]:
        print(f"  {m['file']:<13} {m['status']:<11} <- {m['source']}")
    print("  data sizes:", ", ".join(f"{k} {v / 1024:.0f} kB" for k, v in sizes.items()))
    print(f"  sim2j: samples {exists(SIM2J_SAMPLES)}, replay {exists(SIM2J_REPLAY)}, et {exists(SIM2J_ET)}"
          f" (shown: {bool(facts.get('sim2j'))})")
    if WARNINGS:
        print(f"  {len(WARNINGS)} warning(s); see above")


if __name__ == "__main__":
    main()
