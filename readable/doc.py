"""The tables quoted by docs/readable_target.md, generated from readable.json (no number is copied by hand).

python3 -m readable.doc [--quick]  ->  readable/build/doc_tables.md (quick: readable/build/quick/doc_tables.md)
"""
from __future__ import annotations

import argparse
from typing import Dict, List, Optional

import numpy as np

from . import BUILD_DIR
from . import common as CM


def f(x, nd: int = 2, pct: bool = False) -> str:
    if x is None:
        return "-"
    try:
        x = float(x)
    except Exception:
        return str(x)
    if not np.isfinite(x):
        return "-"
    return f"{x:.{nd}f}"


def ci(b: Optional[Dict], nd: int = 2) -> str:
    if not b:
        return "-"
    m, lo, hi = b.get("mean"), b.get("lo"), b.get("hi")
    if m is None or not np.isfinite(float(m)):
        return "-"
    if lo is None or hi is None or not (np.isfinite(float(lo)) and np.isfinite(float(hi))):
        return f(m, nd)
    return f"{f(m, nd)} ({f(lo, nd)} to {f(hi, nd)})"


def ci_thr(v, c: Optional[Dict], nd: int = 2) -> str:
    if v is None or not np.isfinite(float(v)):
        return "not reached"
    s = f(v, nd)
    if c and np.isfinite(c.get("lo", np.nan)) and np.isfinite(c.get("hi", np.nan)):
        s += f" ({f(c['lo'], nd)} to {f(c['hi'], nd)})"
        if c.get("n_unreachable"):
            s += f"; not reached in {c['n_unreachable']} of {c['n']} resamples"
    return s


def table(header: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def dev_label(dev: str, row: Dict) -> str:
    p = row.get("param") or {}
    if dev == "none":
        return "Ordinary pen"
    if dev in ("revJ_oracle", "E13a_0.00"):
        return "Rev J, perfect knowledge"
    if dev == "E13a_1.00":
        return "Rev J, nose held (a: 100 % left)"
    t = p.get("type")
    if t == "a":
        return f"(a) {100 * p['remain']:.0f} % of the tremor left" + (f" [aimed at {p['target_mm']:.2f} mm]"
                                                                        if "target_mm" in p else "")
    if t == "b":
        return f"(b) perfect estimate {p['delay_ms']:.1f} ms late" + (f" [aimed at {p['target_mm']:.2f} mm]"
                                                                        if "target_mm" in p else "")
    if t == "c":
        return f"(c) perfect + noise {p['noise_mm']:.2f} mm" + (f" [aimed at {p['target_mm']:.2f} mm]"
                                                                 if "target_mm" in p else "")
    return dev


# ------------------------------------------------------------------ E13
CURVE_AT = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0, 1.12, 1.4, 1.64)


def curve_table(e: Dict) -> List[str]:
    """Words of 10 read off the fitted curves at chosen residuals (CALC on the SIM points)."""
    from . import curve as CV
    fits = {s: ((e.get(s) or {}).get("fits") or {}).get("pooled") for s in ("tuning", "test")}
    if not fits["tuning"]:
        return []
    rows = []
    for r in CURVE_AT:
        row = [f"{r:.2f}" + {0.0: " (no tremor left)", 1.12: " (study E's best causal tracker, test)",
                             1.64: " (ordinary pen, severe, test)"}.get(r, "")]
        for s in ("tuning", "test"):
            f_ = fits[s]
            row.append(f(float(CV.model(r, f_["fit"]["p"])), 1) if f_ else "-")
        rows.append(row)
    return ["**Words read out of 10 against the tremor left at the tip, read off the fitted curves** (CALC on SIM "
            "points; PD and ET, severe and moderate pooled)\n",
            table(["Tremor left at the tip, mm", "Words of 10, tuning curve", "Words of 10, test curve"], rows), ""]


def e13_tables(e: Dict) -> List[str]:
    out = curve_table(e)
    n_curve = len(out)
    for split in ("tuning", "test"):
        blk = e.get(split) or {}
        for key in ("all/severe", "PD/severe", "ET/severe", "all/moderate", "PD/moderate", "ET/moderate"):
            t = blk.get("tables", {}).get(key)
            if not t:
                continue
            cw = t[0].get("clean_words_of_10")
            rows = []
            for r in t[1:]:
                rows.append([dev_label(r["device"], r), ci(r["tip_tremor_mm"]), ci(r["words_of_10"], 1),
                             ci(r["gain_vs_ordinary"], 1) if r.get("gain_vs_ordinary") else "-", str(r["n_cases"])])
            kind, cls = key.split("/")
            kn = {"all": "PD and ET pooled", "PD": "Parkinson's", "ET": "Essential tremor"}[kind]
            out.append(f"**E13, {split} split, {kn}, {cls} class** (SIM; mean over writers, 95 % writer-bootstrap "
                       f"interval; same notes without tremor: {ci(cw, 1)} words of 10)\n")
            out.append(table(["Residual at the tip", "Tremor left at the tip, mm", "Words of 10",
                              "Gain over the ordinary pen", "Cases"], rows))
            out.append("")
        fits = blk.get("fits") or {}
        if fits:
            rows = []
            for k in ("pooled", "severe_only", "kind_PD", "kind_ET", "type_a", "type_b", "type_c", "pooled_broadband",
                      "type_a_broadband", "type_b_broadband", "type_c_broadband"):
                x = fits.get(k)
                if not x:
                    continue
                pr = x["fit"].get("params") or {}
                c = x.get("ci95") or {}
                rows.append([{"pooled": "all points (PD + ET, severe + moderate, all types)",
                              "severe_only": "severe class only", "kind_PD": "Parkinson's only",
                              "kind_ET": "essential tremor only", "type_a": "(a) amplitude + anchors",
                              "type_b": "(b) lag + anchors", "type_c": "(c) noise + anchors",
                              "pooled_broadband": "check: all points, broadband residual (0.5-20 Hz RMS) as x",
                              "type_a_broadband": "check: (a) + anchors, broadband x",
                              "type_b_broadband": "check: (b) + anchors, broadband x",
                              "type_c_broadband": "check: (c) + anchors, broadband x"}[k],
                             ci_thr(x.get("r_plus2_mm"), c.get("r_plus2_mm")), ci_thr(x.get("r_80_mm"), c.get("r_80_mm")),
                             ci_thr(x.get("r_within1_mm"), c.get("r_within1_mm")),
                             f(pr.get("w_hi"), 1), f(pr.get("r50_mm")), f(pr.get("steepness"), 1), f(pr.get("w_lo"), 1),
                             f(x["fit"].get("rmse_words"), 2), str(x.get("n_points"))])
            out.append(f"**E13 curve, {split} split** (CALC on SIM points; 95 % writer-bootstrap intervals; the anchors "
                       f"are the ordinary pen, perfect knowledge, the nose held and the clean notes)\n")
            out.append(table(["Points fitted", "Residual for +2 words (DEC-055), mm", "Residual for 80 % of the "
                              "tremor-free words, mm", "Residual for words within 1 of the clean notes, mm", "w_hi",
                              "r50, mm", "steepness", "w_lo", "RMSE, words", "points"], rows))
            mf = blk.get("model_free_type_a")
            if mf:
                out.append(f"\nModel-free check (type (a) per-level means, piecewise linear): +2 words at "
                           f"{f(mf.get('r_plus2_mm'))} mm, 80 % at {f(mf.get('r_80_mm'))} mm, within 1 word at "
                           f"{f(mf.get('r_within1_mm'))} mm.")
            p = fits.get("pooled", {})
            out.append(f"\nOrdinary pen at the severe class: {f(p.get('w_ord_severe'), 2)} words of 10 (target "
                       f"{f((p.get('w_ord_severe') or np.nan) + 2, 2)}); the same notes without tremor: "
                       f"{f(p.get('w_clean'), 2)} (80 %: {f(0.8 * (p.get('w_clean') or np.nan), 2)}).\n")
    te = e.get("test") or {}
    if te.get("prediction_check"):
        pc = te["prediction_check"]
        rows = [[k, f(v["r_mm_mean"]), f(v["words_mean"], 2), f(v["predicted_mean"], 2), str(v["n"])]
                for k, v in pc["by_device"].items()]
        out.append("**E13 test split against the frozen tuning curve** (words read vs the curve's words at the measured "
                   f"residual; mean error {f(pc['mean_error_words'], 2)} words, mean absolute error "
                   f"{f(pc['mae_words'], 2)} per run)\n")
        out.append(table(["Run", "Tip tremor, mm", "Words read", "Tuning curve predicts", "Runs"], rows))
        out.append("")
    g = te.get("gain_at_r_plus2")
    if g:
        out.append(f"At the level aimed at the tuning r_plus2 ({g['device']}): tip tremor {ci(g['tip_tremor_mm'])} mm, "
                   f"words {ci(g['words_of_10'], 1)}, gain over the ordinary pen {ci(g['gain'], 2)}; DEC-055's words "
                   f"line {'met' if g['meets_dec055_words_line'] else 'not met'}.\n")
    return out


# ------------------------------------------------------------------ E11
def e11_tables(e: Dict) -> List[str]:
    out = []
    tu = e.get("tuning")
    if tu:
        rows = []
        for k, ch in tu["choice"].items():
            fz = ch["frozen_gate_on_tuning"]
            rows.append([k, ch["rule"], "yes" if ch["passes"] else "no (smallest worst note)", f(ch["severe_ratio"]),
                         f(ch["clean_um_mean"], 1), f(ch["clean_um_note_max"], 1), f(ch["moderate_rheld"], 3),
                         f(ch["mild_rheld"], 3), f(fz["severe_ratio"]), f(fz["clean_um_mean"], 1),
                         f(fz["clean_um_note_max"], 1)])
        out.append("**E11 rule chosen on the tuning split** (SIM, E's surrogate of the command path; each tuning note "
                   "calibrated on its writer's other note; severe tip tremor as a share of the ordinary pen's)\n")
        out.append(table(["Design", "Rule chosen", "Passes", "Severe tip tremor, x ordinary", "Clean moved, um: mean",
                          "worst note", "Moderate, x held", "Mild, x held", "Frozen gate: severe", "clean mean",
                          "worst note"], rows))
        out.append("")
    te = e.get("test")
    if te:
        rows = []
        for r in te["per_writer"]:
            rows.append([str(r["note"]), r["writer"].split("/")[-1].replace(".dat", ""),
                         f(r.get("D1_frozen_um"), 1), f(r.get("D1_cal_um"), 1), f(r.get("D1_a_lo_mm"), 2),
                         f(r.get("D2_frozen_um"), 1), f(r.get("D2_cal_um"), 1), f(r.get("D2_a_lo_mm"), 2),
                         f(r.get("D3_frozen_um"), 1), f(r.get("D3_cal_um"), 1)])
        out.append("**E11 on the test split, per writer: clean writing moved, um** (SIM, full HW1 plant; INFORMATION "
                   "ONLY; a_lo = the calibrated opening threshold of the gate, mm)\n")
        out.append(table(["Test note", "Writer", "D1 frozen gate", "D1 calibrated", "D1 a_lo", "D2 frozen gate",
                          "D2 calibrated", "D2 a_lo", "D3 frozen gate", "D3 calibrated"], rows))
        out.append("")
        rows = []
        for key, s in te["summary"].items():
            d5 = s.get("dec055") or {}
            rows.append([key, ci(s.get("clean_um"), 1), f(s.get("clean_um_worst_writer"), 1),
                         str(s.get("writers_over_50um")), ci(s.get("severe_words_of_10"), 1),
                         ci(s.get("severe_words_gain"), 2), ci(s.get("severe_ratio_to_ordinary")),
                         f(s.get("moderate_ratio_to_held_worst_writer"), 3), f(s.get("mild_ratio_to_held_worst_writer"), 3),
                         {True: "passed", False: "not passed", None: "words not read"}[d5.get("passes")]])
        out.append("**E11 on the test split, summary** (SIM; 9 test writers; words gain over the ordinary pen at the "
                   "severe class, PD and ET pooled; 'frozen' D1 words are study E's reading of the same cases)\n")
        out.append(table(["Design and gate", "Clean moved, um: mean (95 %)", "worst writer", "writers > 50 um",
                          "Severe words of 10", "gain over ordinary", "Severe tip tremor, x ordinary",
                          "Moderate, worst writer x held", "Mild, worst writer x held", "DEC-055"], rows))
        out.append("")
    return out


# ------------------------------------------------------------------ gap
def gap_tables(g: Dict) -> List[str]:
    out = []
    pr = g.get("predictor") or {}
    if pr.get("choice"):
        out.append(f"AR predictor chosen on the tuning split: Delta {pr['choice']['dtau_ms']} ms x {pr['choice']['order']} "
                   f"lags (cross-fitted in-band residual {f(pr['choice']['cv_residual_mm'] * 1e3, 1)} um; no prediction: "
                   f"{f(pr.get('hold_cv_residual_mm', np.nan) * 1e3, 1)} um).\n")
    for split in ("tuning", "test"):
        blk = g.get(split)
        if not blk:
            continue
        rows = []
        tcurve = split == "test"
        for name, ch in blk["chains"].items():
            for s in ch["steps"]:
                rows.append([ch["label"], s["step"], s["config"], ci(s.get("tip_tremor_mm")),
                             ci(s.get("signal_residual_mm")), ci(s.get("words_via_curve"), 1)]
                            + ([ci(s.get("words_via_test_curve"), 1)] if tcurve else [])
                            + [ci(s.get("words_read"), 1) if s.get("words_read") else "-"])
            pad = ["-"] if tcurve else []
            rows.append([ch["label"], "separation part alone (e_sep)", "-", "-", ci(ch.get("separation_part_mm")), "-"]
                        + pad + ["-"])
            if ch.get("clean_change_um"):
                cc = ch["clean_change_um"]
                rows.append([ch["label"], f"clean writing moved, um ({split} notes)", "-", ci(cc, 1) + f"; worst "
                             f"note {f(cc.get('worst_note'), 1)}", "-", "-"] + pad + ["-"])
        out.append(f"**Gap decomposition, {split} split, severe class** (SIM, full HW1 plant; words via the frozen E13 "
                   f"tuning curve = CALC; {blk['n_writers']} writers, {blk['n_cases']} cases)\n")
        out.append(table(["Estimator", "Step", "Configuration", "Tremor left at the tip, mm",
                          "Error signal alone, mm (R's measure)", "Words of 10 via the tuning curve"]
                         + (["Words of 10 via the test curve"] if tcurve else []) + ["Words read directly"], rows))
        out.append("")
        cf = blk["configs"]
        rows = [[k, ci(v.get("tip_tremor_mm")), ci(v.get("signal_residual_mm")), ci(v.get("words_via_curve"), 1)]
                + ([ci(v.get("words_via_test_curve"), 1)] if tcurve else [])
                + [ci(v.get("words_read"), 1) if v.get("words_read") else "-"] for k, v in sorted(cf.items())]
        out.append(f"**Every configuration, {split} split** (SIM)\n")
        out.append(table(["Configuration", "Tremor left at the tip, mm", "Error signal alone, mm",
                          "Words via the tuning curve"] + (["Words via the test curve"] if tcurve else [])
                         + ["Words read directly"], rows))
        out.append("")
    bb = pr.get("broadband") or g.get("broadband")
    return out


def broadband_table(ar: Optional[Dict]) -> List[str]:
    if not ar or not ar.get("broadband"):
        return []
    b = ar["broadband"]
    rows = []
    for h, v in b["by_horizon"].items():
        rows.append([h, f(v["horizon_ms"], 1), f(100 * v["narrow"]["ar_inband_share_mean"], 2),
                     f(100 * v["broad"]["ar_inband_share_mean"], 2), f(100 * v["broad"]["ar_rms_share_mean"], 2),
                     f(100 * v["broad"]["hold_inband_share_mean"], 1), f(v["broad"]["ar_at_1p72mm_mm"] * 1e3, 1)])
    return ["**Prediction on broadband tremor** (CALC on DATA: " + f"{b['n_records']} tuning ET recordings, "
            f"{b['n_subjects']} subjects; AR structure as chosen, refitted per band, cross-fitted by subject)\n",
            table(["Horizon", "ms", "AR residual, library bands, % (in band)", "AR residual, broad band, % (in band)",
                   "AR residual, broad band, % (RMS, 1.5-20 Hz)", "no prediction, broad band, % (in band)",
                   "AR residual at 1.72 mm, um (broad)"], rows), ""]


def fir_table(ar: Optional[Dict]) -> List[str]:
    if not ar or not ar.get("imu_fir"):
        return []
    fi = ar["imu_fir"]
    rows = [[k, f(v * 1e3, 0)] for k, v in fi.get("scores_mm", {}).items()]
    return [f"**Linear IMU filter trained on the tremor alone** (CALC on SIM; cross-fitted in-band residual on the "
            f"severe tuning cases; chosen: {fi['L']} taps at {fi['fs_in']:g} Hz, ridge {fi['ridge']:g})\n",
            table(["Taps and ridge", "Residual, um"], rows), ""]


def _card_rows(cd: Dict, cols: List[str]) -> List[List[str]]:
    def g(dev, key, nd=2):
        return ci((cd.get(dev) or {}).get(key), nd)
    rows = [["Readable words out of 10"] + [g(c, "words_of_10", 1) for c in cols],
            ["... gain over the ordinary pen"] + ["-" if c == "none" else g(c, "words_of_10_gain", 1) for c in cols],
            ["Tremor left at the tip, mm"] + [g(c, "tip_tremor_mm") for c in cols],
            ["... share of the ordinary pen's (amplitude)"] + ["1 (reference)" if c == "none" else
                                                              g(c, "tip_tremor_ratio") for c in cols],
            ["Clean writing moved, um (notes without tremor)"] + [
                "0 (reference)" if c == "none" else (g(c, "false_correction_um", 1)
                                                     if (cd.get(c) or {}).get("false_correction_um", {}).get("n_writers")
                                                     else "0 by construction" if c.startswith("E13") or c == "revJ_oracle"
                                                     else "-") for c in cols],
            ["Readable words without tremor"] + [g(c, "clean_words_of_10", 1) if
                                                 (cd.get(c) or {}).get("clean_words_of_10", {}).get("n_writers") else "-"
                                                 for c in cols]]
    return rows


def results_cards(out: Dict) -> List[str]:
    """R's and E's results card (writer-bootstrap 95 % intervals) for the key rows of the test split, severe class,
    PD and ET pooled."""
    res = []
    cd = (((out.get("e13") or {}).get("test") or {}).get("cards") or {}).get("all/severe")
    if cd:
        cols = [c for c in ("none", "E13a_r80", "E13a_mid", "E13a_r2", "E13b_r2", "E13c_r2", "E13a_r2x1.3", "revJ_oracle")
                if c in cd]
        head = {"none": "Ordinary pen", "E13a_r80": "(a) aimed at the 80 % level", "E13a_mid": "(a) midway",
                "E13a_r2": "(a) aimed at +2 words", "E13b_r2": "(b) lag, aimed at +2", "E13c_r2": "(c) noise, aimed at +2",
                "E13a_r2x1.3": "(a) 1.3 x the +2 level", "revJ_oracle": "Perfect knowledge (R)"}
        res += ["**Results card: EXP-E13 on the test split, severe class, PD and ET pooled** (SIM; 9 test writers, 18 "
                "cases; 95 % writer-bootstrap intervals; E13 rows are perfect knowledge made imperfect on purpose, so "
                "they move no clean writing by construction)\n",
                table([""] + [head[c] for c in cols], _card_rows(cd, cols)), ""]
    cd = (((out.get("e11") or {}).get("test") or {}).get("cards") or {}).get("severe")
    if cd:
        cols = [c for c in ("none", "D1|frozen_E", "D1|cal", "D2|frozen", "D2|cal", "D3|frozen", "D3|cal") if c in cd]
        head = {"none": "Ordinary pen", "D1|frozen_E": "D1 frozen gate (E's reading)", "D1|cal": "D1 calibrated",
                "D2|frozen": "D2 frozen gate", "D2|cal": "D2 calibrated", "D3|frozen": "D3 frozen gate",
                "D3|cal": "D3 calibrated"}
        rows = _card_rows(cd, cols)
        s11 = ((out.get("e11") or {}).get("test") or {}).get("summary") or {}
        rows[4] = ["Clean writing moved, um (notes without tremor)"] + [
            "0 (reference)" if c == "none" else ci((s11.get(c.replace("_E", "")) or {}).get("clean_um"), 1)
            for c in cols]
        rows.append(["... worst writer, um"] + ["-" if c == "none" else
                                                 f((s11.get(c.replace("_E", "")) or {}).get("clean_um_worst_writer"), 1)
                                                 for c in cols])
        res += ["**Results card: EXP-E11 on the test split, severe class, PD and ET pooled** (SIM; INFORMATION ONLY; 9 "
                "test writers; D1 = ai2's TCN + size gate, D2 = the real-data TCN + size gate, D3 = the listening AKF + "
                "confidence gate; D3 not read)\n", table([""] + [head[c] for c in cols], rows), ""]
    return res


def sections(out: Dict, quick: bool) -> Dict[str, List[str]]:
    from . import stages as SG
    ar = CM.jload(SG.predictor_path(quick))
    return {"curve": curve_table(out.get("e13") or {}), "e13": e13_tables(out.get("e13") or {})[
        len(curve_table(out.get("e13") or {})):], "e11": e11_tables(out.get("e11") or {}), "fir": fir_table(ar),
        "broadband": broadband_table(ar), "gap": gap_tables(out.get("gap") or {}), "cards": results_cards(out),
        "sensing": sensing_table(out.get("gap") or {})}


def sensing_table(g: Dict) -> List[str]:
    sc = g.get("sensing_check") or {}
    if not sc:
        return []
    rows = []
    lab = {("imu", "pen"): "the pen's IMU (noise, bias, drift, scale, misalignment, pen rotation): linear filter",
           ("imu", "perfect"): "a perfect accelerometer (none of those errors, no rotation): the same filter",
           ("page", "ideal"): "ideal page sensor (3 um, 2 ms): linear estimator on the high-passed position",
           ("page", "deltapen"): "DeltaPen-class page sensor (R's headline): the same estimator"}
    for kind in ("imu", "page"):
        for v, x in (sc.get(kind) or {}).get("variants", {}).items():
            rows.append([lab.get((kind, v), f"{kind} {v}"), f(x.get("signal_residual_mm"), 3), f(x.get("tip_tremor_mm"), 3),
                         str(x.get("n"))])
    return ["**What the sensors allow with the tremor alone** (CALC on SIM streams, tuning split, severe class, "
            "cross-fitted by fold; the tip column is the full plant on the full case, SIM)\n",
            table(["Sensor and estimator (tremor alone)", "Error in the tremor band, mm (R's measure)",
                   "Tremor left at the tip, mm", "Cases"], rows), ""]


def write_tables(out: Dict, quick: bool) -> str:
    sec = sections(out, quick)
    parts = ["# Generated tables for docs/readable_target.md", ""]
    for k in ("curve", "cards", "e13", "e11", "fir", "sensing", "broadband", "gap"):
        parts += sec[k]
    txt = "\n".join(parts) + "\n"
    p = (CM.QUICK_DIR if quick else BUILD_DIR) / "doc_tables.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)
    CM.log(f"[doc] {p}")
    return txt


# ------------------------------------------------------------------ the document: a template filled from readable.json
def _get(d, path: str):
    for k in path.split("."):
        if d is None:
            return None
        d = d.get(k) if isinstance(d, dict) else None
    return d


def values(out: Dict) -> Dict[str, str]:
    """Key numbers for the document's text, each formatted from readable.json ({{KEY}} in the template)."""
    from . import curve as CV
    v: Dict[str, str] = {}
    e = out.get("e13") or {}
    for split, tag in (("tuning", "T"), ("test", "S")):
        fp = _get(e, f"{split}.fits.pooled") or {}
        c = fp.get("ci95") or {}
        for key, name in (("r_plus2_mm", "R2"), ("r_80_mm", "R80"), ("r_within1_mm", "RW1")):
            v[f"{tag}_{name}"] = f(fp.get(key))
            v[f"{tag}_{name}_LO"] = f((c.get(key) or {}).get("lo"))
            v[f"{tag}_{name}_HI"] = f((c.get(key) or {}).get("hi"))
        v[f"{tag}_WORD"] = f(fp.get("w_ord_severe"), 1)
        v[f"{tag}_WCLEAN"] = f(fp.get("w_clean"), 1)
        v[f"{tag}_TARGET2"] = f((fp.get("w_ord_severe") or np.nan) + 2, 1)
        v[f"{tag}_TARGET80"] = f(0.8 * (fp.get("w_clean") or np.nan), 1)
        p = _get(fp, "fit.p")
        for r in (0.1, 0.2, 0.24, 0.3, 0.5, 0.75, 1.0, 1.12, 1.64):
            v[f"{tag}_W@{r:g}"] = f(float(CV.model(r, p)), 1) if p and np.all(np.isfinite(p)) else "-"
        for ty in ("a", "b", "c"):
            ft = _get(e, f"{split}.fits.type_{ty}") or {}
            v[f"{tag}_R2_{ty}"] = f(ft.get("r_plus2_mm"))
            fb = _get(e, f"{split}.fits.type_{ty}_broadband") or {}
            v[f"{tag}_R2BB_{ty}"] = f(fb.get("r_plus2_mm"))
        for kd in ("PD", "ET"):
            fk = _get(e, f"{split}.fits.kind_{kd}") or {}
            v[f"{tag}_R2_{kd}"] = f(fk.get("r_plus2_mm"))
            v[f"{tag}_R80_{kd}"] = f(fk.get("r_80_mm"))
        mf = _get(e, f"{split}.model_free_type_a") or {}
        v[f"{tag}_MF_R2"] = f(mf.get("r_plus2_mm"))
        v[f"{tag}_MF_R80"] = f(mf.get("r_80_mm"))
        v[f"{tag}_MF_RW1"] = f(mf.get("r_within1_mm"))
        v[f"{tag}_RMSE"] = f(_get(fp, "fit.rmse_words"), 2)
        v[f"{tag}_RMSE_BB"] = f(_get(e, f"{split}.fits.pooled_broadband.fit.rmse_words"), 2)
    g = _get(e, "test.gain_at_r_plus2") or {}
    v["S_GAIN_AT_R2"] = ci(g.get("gain"), 1)
    v["S_TIP_AT_R2"] = ci(g.get("tip_tremor_mm"))
    v["S_WORDS_AT_R2"] = ci(g.get("words_of_10"), 1)
    pc = _get(e, "test.prediction_check") or {}
    v["S_PRED_ERR"] = f(pc.get("mean_error_words"), 2)
    v["S_PRED_MAE"] = f(pc.get("mae_words"), 2)
    try:
        r2 = float(_get(e, "tuning.fits.pooled.r_plus2_mm"))
        v["E_OVER_R2"] = f(1.12 / r2, 1)
        v["E_POWER_OVER_R2"] = f((1.12 / r2) ** 2, 1)
    except Exception:
        v["E_OVER_R2"] = v["E_POWER_OVER_R2"] = "-"
    try:
        v["S_E_OVER_R2"] = f(1.12 / float(_get(e, "test.fits.pooled.r_plus2_mm")), 1)
    except Exception:
        v["S_E_OVER_R2"] = "-"
    for row in (_get(e, "test.tables") or {}).get("all/severe", [])[1:]:
        if row.get("gain_vs_ordinary"):
            v[f"S_GAIN_{row['device']}"] = f(row["gain_vs_ordinary"].get("mean"), 1)
            v[f"S_TIP_{row['device']}"] = f(row["tip_tremor_mm"].get("mean"))
    for row in (_get(out, "e11.test.per_writer") or []):
        v[f"E11_W{row['note']}_D1_ALO"] = f(row.get("D1_a_lo_mm"))
    try:
        v["E11_D1_FROZEN_ALO"] = f(float(_get(out, "frozen.e11.choice.D1.frozen_gate_on_tuning") and
                                         CM.frozen_e()["chosen"]["auth"]["a_lo"]) * 1e3)
    except Exception:
        v["E11_D1_FROZEN_ALO"] = "-"
    s11 = _get(out, "e11.test.summary") or {}
    for k, x in s11.items():
        t = k.replace("|", "_")
        v[f"{t}_CLEAN"] = ci(x.get("clean_um"), 1)
        v[f"{t}_WORST"] = f(x.get("clean_um_worst_writer"), 1)
        v[f"{t}_WORSTW"] = str(x.get("worst_writer") or "-").replace(".dat", "")
        v[f"{t}_N50"] = str(x.get("writers_over_50um"))
        v[f"{t}_GAIN"] = ci(x.get("severe_words_gain"), 2)
        v[f"{t}_WORDS"] = ci(x.get("severe_words_of_10"), 1)
        v[f"{t}_RATIO"] = ci(x.get("severe_ratio_to_ordinary"))
        v[f"{t}_MODW"] = f(x.get("moderate_ratio_to_held_worst_writer"), 3)
        v[f"{t}_MILDW"] = f(x.get("mild_ratio_to_held_worst_writer"), 3)
    ch11 = _get(out, "e11.tuning.choice") or {}
    for k, x in ch11.items():
        v[f"{k}_RULE"] = str(x.get("rule"))
    gp = out.get("gap") or {}
    for split, tag in (("tuning", "T"), ("test", "S")):
        cf = _get(gp, f"{split}.configs") or {}
        for k, x in cf.items():
            v[f"G{tag}_{k}_MM"] = ci(x.get("tip_tremor_mm"))
            v[f"G{tag}_{k}_M"] = f(_get(x, "tip_tremor_mm.mean"))
            v[f"G{tag}_{k}_W"] = f(_get(x, "words_via_curve.mean"), 1)
            v[f"G{tag}_{k}_WR"] = f(_get(x, "words_read.mean"), 1)
            v[f"G{tag}_{k}_WT"] = f(_get(x, "words_via_test_curve.mean"), 1)
            v[f"G{tag}_{k}_SIG"] = f(_get(x, "signal_residual_mm.mean"), 3)
        for name, ch in (_get(gp, f"{split}.chains") or {}).items():
            v[f"G{tag}_{name}_SEP"] = f(_get(ch, "separation_part_mm.mean"))
            v[f"G{tag}_{name}_CLEAN"] = f(_get(ch, "clean_change_um.mean"), 0)
            v[f"G{tag}_{name}_CLEANW"] = f(_get(ch, "clean_change_um.worst_note"), 0)
    pr = gp.get("predictor") or {}
    v["AR_CV_UM"] = f(_get(pr, "choice.cv_residual_mm") * 1e3 if _get(pr, "choice.cv_residual_mm") is not None else None, 1)
    v["HOLD_CV_UM"] = f(pr.get("hold_cv_residual_mm") * 1e3 if pr.get("hold_cv_residual_mm") is not None else None, 0)
    v["AR_ORDER"] = str(_get(pr, "choice.order"))
    v["AR_DTAU"] = str(_get(pr, "choice.dtau_ms"))
    bb = _get(pr, "broadband.by_horizon.imu") or {}
    v["BB_NARROW_PCT"] = f(100 * (_get(bb, "narrow.ar_inband_share_mean") or np.nan), 2)
    v["BB_BROAD_PCT"] = f(100 * (_get(bb, "broad.ar_inband_share_mean") or np.nan), 2)
    v["BB_BROAD_RMS_PCT"] = f(100 * (_get(bb, "broad.ar_rms_share_mean") or np.nan), 2)
    v["BB_HOLD_PCT"] = f(100 * (_get(bb, "broad.hold_inband_share_mean") or np.nan), 1)
    v["BB_NREC"] = str(_get(pr, "broadband.n_records"))
    v["BB_NSUBJ"] = str(_get(pr, "broadband.n_subjects"))
    for kind, vs in (("imu", ("pen", "perfect")), ("page", ("ideal", "deltapen"))):
        for v_ in vs:
            x = _get(gp, f"sensing_check.{kind}.variants.{v_}") or {}
            v[f"SC_{kind}_{v_}_SIG"] = f(x.get("signal_residual_mm"))
            v[f"SC_{kind}_{v_}_TIP"] = f(x.get("tip_tremor_mm"))
    fi = pr.get("imu_fir") or {}
    v["FIR_L"] = str(fi.get("L"))
    v["FIR_RIDGE"] = f"{fi.get('ridge'):g}" if fi.get("ridge") is not None else "-"
    comp = out.get("compute") or {}
    for k, x in (comp.get("stages") or {}).items():
        v[f"T_{k}"] = f(x / 60.0, 1)
    return v


def fill(template: str, out: Dict, quick: bool) -> str:
    import re
    vals = values(out)
    sec = sections(out, quick)

    def rep(m):
        key = m.group(1)
        if key.startswith("TABLE:"):
            return "\n".join(sec.get(key[6:], [f"(no table {key[6:]})"]))
        return vals.get(key, f"[[missing {key}]]")
    return re.sub(r"\{\{([^}]+)\}\}", rep, template)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--fill", help="a template to fill from readable.json")
    ap.add_argument("--out", help="where to write the filled document")
    ap.add_argument("--keys", action="store_true", help="print the value keys")
    a = ap.parse_args(argv)
    from . import stages as SG
    out = CM.jload(SG.results_dir(a.quick) / "readable.json")
    write_tables(out, a.quick)
    if a.keys:
        for k, x in sorted(values(out).items()):
            print(f"{k} = {x}")
    if a.fill:
        from pathlib import Path
        txt = fill(Path(a.fill).read_text(), out, a.quick)
        miss = sorted(set(__import__("re").findall(r"\[\[missing ([^\]]+)\]\]", txt)))
        if miss:
            print("missing keys:", miss)
        Path(a.out).write_text(txt)
        CM.log(f"[doc] {a.out}")


if __name__ == "__main__":
    main()
