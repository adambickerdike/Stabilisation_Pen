r"""The one-number tables, the results cards and the comparisons the review asked for, from the simulation rows
(wholepen/build/rows/*.jsonl, also in results/wholepen/test.json, grips.json, arm.json) and calc.json.

Conventions (printed with every table):
  tremor left at the tip   peak amplitude (mm) along the tremor's main axis of the ink's 2.5-20 Hz motion against the
                           tremor-free run, while the ball is on the paper (cases.tremor_amp_mm); mean of the test writers
  words readable of 10     the app's handwriting recogniser (sim2j metrics, app/penapp) reading the 5-word sentence of
                           each of the two test writers: words read correctly, summed (no language-model rescue)
  ratio                    residual amplitude / amplitude without help: 0.5 = half the amplitude = 75 % less power
                           (-6 dB); never quoted as '75 % less tremor'
Evidence status: SIMULATION on synthetic writers (two test writers, one seed each) with synthetic or recorded tremor;
CALCULATION where marked.  Nothing measured.  Two writers x one seed is a ranking, not a population estimate.
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List

import numpy as np

from . import BUILD, RESULTS
from . import run_study as RS

HEAD_DESIGNS = ["none", "nose", "nose_gate", "collar_nose", "collar_fine", "gt_nose", "nose_oracle", "collar_nose_oracle"]


def _rows(name: str) -> List[Dict]:
    return RS.Rows(name).values()


def _agg(R, cls, design, key, how="mean", hand="h1", grip=1.0):
    v = [r.get(key) for r in R if r.get("class") == cls and r.get("design") == design and r.get("hand_model", "h1") == hand
         and float(r.get("grip", 1.0)) == grip and isinstance(r.get(key), (int, float)) and math.isfinite(r.get(key))]
    if not v:
        return None
    return float(np.sum(v)) if how == "sum" else float(np.mean(v))


def headline(R, classes=None) -> Dict:
    classes = classes or [c[0] for c in RS.CLASSES]
    tip, words, cover, ink, n = {}, {}, {}, {}, {}
    all_designs = HEAD_DESIGNS + [d for d in RS.LABELS if d not in HEAD_DESIGNS]
    for c in classes:
        for d in all_designs:
            t = _agg(R, c, d, "tip_tremor_mm")
            if t is None:
                continue
            wa = [r.get("words_app") for r in R if r.get("class") == c and r.get("design") == d and r.get("hand_model", "h1") == "h1"
                  and float(r.get("grip", 1.0)) == 1.0]
            tip[(c, d)] = t
            words[(c, d)] = float(np.nansum([5.0 * x for x in wa if x is not None]))
            n[(c, d)] = len(wa)
            cover[(c, d)] = _agg(R, c, d, "coverage")
            ink[(c, d)] = _agg(R, c, d, "ink_err_um")
    rows = []
    for (c, d), t in tip.items():
        base = tip.get((c, "none"))
        rows.append({"class": c, "class_label": RS.CLASS_LABEL[c], "design": d, "design_label": RS.LABELS[d],
                     "tip_mm": round(t, 2), "words10": round(words[(c, d)], 1), "words_of": 5 * n[(c, d)], "n_writers": n[(c, d)],
                     "ratio_vs_none": round(t / base, 3) if base else None,
                     "coverage": None if cover[(c, d)] is None else round(cover[(c, d)], 3),
                     "ink_err_um": None if ink[(c, d)] is None else round(ink[(c, d)], 0)})
    return {"rows": rows, "classes": classes, "designs": HEAD_DESIGNS}


def cards(R) -> List[Dict]:
    """One results card per population and mode (review section 13)."""
    pops = {"essential tremor": ["ET_mild", "ET_moderate", "ET_severe", "ET_moderate_9Hz"],
            "Parkinson's, tremor while writing": ["PD_mild", "PD_moderate", "PD_severe", "PD_recorded_moderate"],
            "Parkinson's, re-emergent tremor in pauses": ["PD_reemergent_severe"]}
    modes = {"stabilise: Rev J nose": "nose", "stabilise: collar + nose": "collar_nose",
             "stabilise: collar + small fine nib": "collar_fine", "write only when in reach (Rev J nose)": "nose_gate"}
    out = []
    for pop, cl in pops.items():
        for mode, d in modes.items():
            rr = [r for r in R if r.get("class") in cl and r.get("design") == d and r.get("hand_model", "h1") == "h1"
                  and float(r.get("grip", 1.0)) == 1.0]
            r0 = [r for r in R if r.get("class") in cl and r.get("design") == "none" and r.get("hand_model", "h1") == "h1"
                  and float(r.get("grip", 1.0)) == 1.0]
            if not rr:
                continue
            words = float(np.nansum([5.0 * r.get("words_app", 0.0) for r in rr]))
            words0 = float(np.nansum([5.0 * r.get("words_app", 0.0) for r in r0]))
            nw = 5 * len(rr)
            T = float(np.nansum([r.get("task_time_s", float("nan")) for r in rr]))
            T_aw = float(np.nansum([r.get("autowrite_extra_s", 0.0) for r in rr])) if d == "nose_gate" else 0.0
            clean = [r for r in R if r.get("class") == "clean" and r.get("design") == d]
            out.append({
                "population": pop, "mode": mode, "design": d, "cases": len(rr),
                "readable_words": f"{words:.0f} of {nw} (no help: {words0:.0f} of {5 * len(r0)})",
                "useful_words_per_min": round(60.0 * words / T, 1) if T > 0 else None,
                "useful_words_per_min_with_completion": round(60.0 * words / (T + T_aw), 1) if d == "nose_gate" and T > 0 else None,
                "tremor_left_mm_mean": round(float(np.nanmean([r["tip_tremor_mm"] for r in rr])), 2),
                "tremor_no_help_mm_mean": round(float(np.nanmean([r["tip_tremor_mm"] for r in r0])), 2) if r0 else None,
                "clean_writing_changed_um": round(float(np.nanmean([c["moved_vs_clean_um"] for c in clean])), 0) if clean else None,
                "coverage": round(float(np.nanmean([r.get("coverage", float("nan")) for r in rr])), 3),
                "missing_stroke_rate": round(float(np.nanmean([r.get("missing_stroke_rate", float("nan")) for r in rr])), 3),
                "power_W_nose": round(float(np.nanmean([r.get("P_nose_W", float("nan")) for r in rr])), 2),
                "power_W_other_devices": round(float(np.nanmean([r.get("P_devices_W", float("nan")) for r in rr])), 2),
                "felt_grip_force_change_rms_N": round(float(np.nanmean([r.get("felt_rms_N", float("nan")) for r in rr])), 2),
            })
    return out


def gate_vs_locked(R, pairs=(("gt_nose", "gt_locked_nose"), ("collar_nose", "collar_locked_nose"), ("collar_nose", "collar_locked"),
                             ("collar_oracle", "collar_locked"), ("nose", "none"))) -> List[Dict]:
    out = []
    for act, lock in pairs:
        for c in sorted({r["class"] for r in R if r.get("design") == act}):
            for g in sorted({float(r.get("grip", 1.0)) for r in R if r.get("design") == act and r.get("class") == c}):
                a = _agg(R, c, act, "tip_tremor_mm", grip=g)
                b = _agg(R, c, lock, "tip_tremor_mm", grip=g)
                if a is None or b is None:
                    continue
                ws = sorted({int(r["w"]) for r in R if r.get("design") == act and r.get("class") == c
                             and float(r.get("grip", 1.0)) == g and "w" in r})
                out.append({"active": act, "locked": lock, "class": c, "grip": g, "writers": ws, "tip_active_mm": round(a, 3),
                            "tip_locked_mm": round(b, 3), "gain_vs_locked": round(1 - a / b, 3),
                            "passes_10pc_gate": (1 - a / b) >= 0.10})
    return out


INC_DESIGNS = ["nose", "collar_locked_nose", "collar_nose", "nose_oracle", "collar_nose_oracle"]


def collar_increment(R) -> List[Dict]:
    """What the collar adds (review: an added device must beat the same pen with it locked by >= 10 %): per class, the
    Rev J nose on its own pen, the collar pen with the collar locked and the nose working, the collar with the nose,
    and both with perfect knowledge; two test writers where both ran."""
    out = []
    for c in [c[0] for c in RS.CLASSES] + [c[0] for c in RS.CLASSES_REAL]:
        row = {"class": c, "class_label": RS.CLASS_LABEL[c]}
        for d in INC_DESIGNS:
            rr = [r for r in R if r.get("class") == c and r.get("design") == d and r.get("hand_model", "h1") == "h1"
                  and float(r.get("grip", 1.0)) == 1.0]
            if rr:
                row[d] = {"tip_mm": round(float(np.mean([r["tip_tremor_mm"] for r in rr])), 3),
                          "words": float(np.nansum([5.0 * r.get("words_app", 0.0) for r in rr])), "words_of": 5 * len(rr),
                          "coverage": round(float(np.mean([r.get("coverage", float("nan")) for r in rr])), 3),
                          "writers": sorted(int(r["w"]) for r in rr)}
        if "collar_nose" in row and "collar_locked_nose" in row:
            row["collar_gain_vs_locked"] = round(1 - row["collar_nose"]["tip_mm"] / row["collar_locked_nose"]["tip_mm"], 3)
        if "collar_nose_oracle" in row and "nose_oracle" in row:
            row["oracle_collar_gain"] = round(1 - row["collar_nose_oracle"]["tip_mm"] / row["nose_oracle"]["tip_mm"], 3)
        if len(row) > 2:
            out.append(row)
    return out


LIGHT_DESIGNS = ["none", "nose", "nose_oracle", "collar_locked", "collar_locked_nose", "collar_nose", "collar_nose_oracle",
                 "light_locked", "light_locked_nose", "light_nose", "light_fine", "light_nose_oracle"]


def compare(R, designs: List[str], classes: List[str]) -> List[Dict]:
    """Per design and class: mean tip tremor, words read (summed over writers, out of 5 per writer), ink laid, the
    writers, the felt grip-force change and the devices' power (SIM rows)."""
    out = []
    for d in designs:
        row = {"design": d, "label": RS.LABELS.get(d, d)}
        for c in classes:
            rr = [r for r in R if r.get("class") == c and r.get("design") == d and r.get("hand_model", "h1") == "h1"
                  and float(r.get("grip", 1.0)) == 1.0]
            if not rr:
                continue
            row[c] = {"tip_mm": round(float(np.mean([r["tip_tremor_mm"] for r in rr])), 3),
                      "words": float(np.nansum([5.0 * r.get("words_app", 0.0) for r in rr])), "words_of": 5 * len(rr),
                      "coverage": round(float(np.mean([r.get("coverage", float("nan")) for r in rr])), 3),
                      "writers": sorted(int(r["w"]) for r in rr),
                      "pivot_peak_rad": max([r.get("pivot_peak_rad") or 0.0 for r in rr]),
                      "P_devices_W": round(float(np.mean([r.get("P_devices_W") or 0.0 for r in rr])), 2),
                      "felt_rms_N": (round(float(np.mean([r["felt_rms_N"] for r in rr if r.get("felt_rms_N") is not None])), 3)
                                     if any(r.get("felt_rms_N") is not None for r in rr) else None)}
        out.append(row)
    return out


def tune_frozen_grip1(tune: List[Dict], rules_body: Dict) -> List[Dict]:
    """The grip-1 x rows of the grip comparison: the tuning writer's runs (writer 100, ET 3 mm, seed 300) with the
    frozen settings (the tracker, the collar variant and the gyroscope law that rules.json chose)."""
    try:
        ev = rules_body["evidence"]
        var = min(ev["tracker_and_collar"]["collar_variants_ink_um"], key=ev["tracker_and_collar"]["collar_variants_ink_um"].get)
        law = rules_body["rules"]["cmg_law"]
    except Exception:
        return []
    want = {f"h1|g1|w100|s300|ET_moderate|collar_locked": "collar_locked",
            f"cpg_{var}|h1|g1|w100|s300|ET_moderate|collar_nose": "collar_nose",
            f"h1|g1|w100|s300|ET_moderate|collar_oracle": "collar_oracle",
            f"g|h1|g1|w100|s300|ET_moderate|gt_locked_nose": "gt_locked_nose",
            f"cmgg_{law}|h1|g1|w100|s300|ET_moderate|gt_nose": "gt_nose"}
    out = []
    for r in tune:
        if r.get("key") in want:
            rr = dict(r)
            rr["design"] = want[r["key"]]
            rr["grip"] = 1.0
            out.append(rr)
    return out


def _rules_body() -> Dict:
    try:
        return json.load(open(os.path.join(RESULTS, "rules.json")))
    except Exception:
        return {}


def build() -> Dict:
    test = _rows("test")
    real = _rows("real")
    light = _rows("light")
    grips = _rows("grips")
    arm = _rows("arm")
    tune = _rows("tune")
    body = {"conventions": __doc__.split("Conventions")[1].split("Evidence status")[0].strip(),
            "headline": headline(test), "headline_real": headline(real, [c[0] for c in RS.CLASSES_REAL]), "cards": cards(test),
            "tail_and_collar_vs_locked_test": gate_vs_locked(test),
            "collar_increment": collar_increment(test + real),
            "light_compare": {"classes": ["ET_moderate", "PD_severe"],
                              "rows": compare(test + light, LIGHT_DESIGNS, ["ET_moderate", "PD_severe"])} if light else None,
            "tail_and_collar_vs_locked_grips": gate_vs_locked(grips + tune_frozen_grip1(tune, _rules_body())),
            "arm": [{k: r.get(k) for k in ("class", "design", "tip_tremor_mm", "words_app", "coverage", "ink_err_um")} for r in arm],
            "n_rows": {"test": len(test), "grips": len(grips), "arm": len(arm), "tune": len(tune)}}
    try:
        body["rules"] = json.load(open(os.path.join(RESULTS, "rules.json")))["rules"]
    except Exception:
        body["rules"] = None
    try:
        calc = json.load(open(os.path.join(RESULTS, "calc.json")))
        body["calc_tail_gate_summary"] = calc["tail_gate"]["summary"]
    except Exception:
        pass
    return body


def table_md(head: Dict, key: str = "tip_mm", fmt: str = "{:.1f}") -> str:
    """Markdown table: classes as rows, designs as columns.  A cell run on one test writer only (writer 0) is marked
    with an asterisk; its words are then out of 5, and say so."""
    ds = [d for d in head["designs"] if any(r["design"] == d for r in head["rows"])]
    lines = ["| Tremor class | " + " | ".join(RS.LABELS[d] for d in ds) + " |", "|---|" + "---|" * len(ds)]
    one = False
    for c in head["classes"]:
        cells = []
        for d in ds:
            r = next((x for x in head["rows"] if x["class"] == c and x["design"] == d), None)
            if r is None or r.get(key) is None:
                cells.append("–")
                continue
            cell = fmt.format(r[key])
            if r.get("n_writers", 2) < 2:
                one = True
                cell += f" of {r.get('words_of', 5)}*" if key == "words10" else "*"
            cells.append(cell)
        lines.append(f"| {RS.CLASS_LABEL[c]} | " + " | ".join(cells) + " |")
    if one:
        lines.append("")
        lines.append("\\* test writer 0 only (one writer, one seed); every other cell is the two test writers.")
    return "\n".join(lines)
