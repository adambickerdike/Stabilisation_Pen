"""Figures (each with a CSV twin), aiprior.json (with provenance), samples.json and the proposed ledger rows.

Evidence status: SIMULATION / CALCULATION on synthetic data (model HW1); nothing measured.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import BUILD_DIR, EVIDENCE_SIM, RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, __version__, ensure_paths

ensure_paths()
from handwriting import figures as FG  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402

C = plotstyle.SERIES
STATUS = "SIMULATION (model HW1)"
LABELS = {
    "none": "Ordinary pen (12 g)", "revH_off": "Rev H, nose held",
    "tracker": "Rev H + tracker (as in the handwriting study)",
    "tracker_rt": "Rev H + tracker re-tuned here for severe tremor (no AI)",
    "tracker_sev": "Rev H + severe-tremor tracker setting (rejected by the rules; information)",
    "prior_ai_correct": "+ AI prior, correct letters", "prior_ai_predicted": "+ AI prior, predicted letters (gated)",
    "prior_wrong_full": "+ AI prior, wrong letter at full confidence", "prior_oracle": "+ prior from the known text (limit)",
    "guide_ai_correct": "+ AI guidance, correct letters", "guide_ai_predicted": "+ AI guidance, predicted letters (gated)",
    "guide_wrong_full": "+ AI guidance, wrong letter at full confidence", "guide_oracle": "+ guidance to the known text (limit)",
    "oracle": "Rev H, perfect knowledge (limit)",
    "clean_tracker": "Digital clean copy of the tracker's ink", "clean_tracker_rt": "Digital clean copy of the re-tuned tracker's ink",
    "clean_revH_off": "Digital clean copy, nose held", "clean_bs_tracker": "Digital clean copy (band-stop) of the tracker's ink",
}
COL = {"none": plotstyle.MUTED, "tracker": C[1], "tracker_rt": C[0], "tracker_sev": C[4], "prior_ai_predicted": C[6], "guide_ai_predicted": C[3],
       "clean_tracker": C[0], "clean_tracker_rt": C[0], "oracle": C[2], "prior_ai_correct": C[6], "guide_ai_correct": C[3],
       "prior_wrong_full": C[7], "guide_wrong_full": C[7], "clean_revH_off": C[4], "guide_oracle": C[3], "prior_oracle": C[6]}
KEYS = ("ink_err_um", "recognition", "word_acc_app", "device_share", "ai_share", "at_travel_limit", "q_rms_mm",
        "ink_err_ratio")
SUMS = ("flips", "flips_removed", "mispred_flips", "broken", "fixed", "read_as_wrong", "n_letters")


def _load(name: str, quick: bool):
    p = BUILD_DIR / ("quick" if quick else "cache") / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def outdir(quick: bool) -> Path:
    d = (BUILD_DIR / "quick" / "results") if quick else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_csv(path: Path, header: List[str], rows: List[List]) -> None:
    FG.write_csv(path, header, rows)


# ------------------------------------------------------------------ aggregation
def aggregate(test: Dict) -> Dict:
    rows = [r for o in test["outs"] for r in o["rows"]]
    variants = sorted({v for r in rows for v in r["variants"]})
    f0s = sorted({r["f0"] for r in rows})
    amps = sorted({r["amp_mm"] for r in rows})
    by = {}
    for v in variants:
        cells = {}
        for f0 in f0s:
            for a in amps:
                sel = [r["variants"][v] for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - a) < 1e-9 and v in r["variants"]]
                if not sel:
                    continue
                c = {"n": len(sel)}
                for k in KEYS:
                    x = [s[k] for s in sel if s.get(k) is not None]
                    if x:
                        c[k] = float(np.mean(x))
                        c[k + "_sd"] = float(np.std(x))
                for k in SUMS:
                    x = [s[k] for s in sel if s.get(k) is not None]
                    if x:
                        c[k] = int(np.sum(x))
                cells[f"{f0:g}Hz_{a:g}mm"] = c
        by[v] = cells

    def mean_over(v, k, fs, am):
        x = [by[v].get(f"{f:g}Hz_{a:g}mm", {}).get(k) for f in fs for a in am]
        x = [y for y in x if y is not None]
        return float(np.mean(x)) if x else None

    def sum_over(v, k, fs, am):
        x = [by[v].get(f"{f:g}Hz_{a:g}mm", {}).get(k) for f in fs for a in am]
        x = [y for y in x if y is not None]
        return int(np.sum(x)) if x else None
    groups = {"8_10Hz_1_2mm": ((8.0, 10.0), (1.0, 2.0)), "6Hz_1_2mm": ((6.0,), (1.0, 2.0)),
              "6_10Hz_1_2mm": ((6.0, 8.0, 10.0), (1.0, 2.0)), "0.3mm": ((6.0, 8.0, 10.0), (0.3,)),
              "1mm": ((6.0, 8.0, 10.0), (1.0,)), "2mm": ((6.0, 8.0, 10.0), (2.0,))}
    head = {}
    for g, (fs, am) in groups.items():
        head[g] = {}
        for v in variants:
            d = {k: mean_over(v, k, fs, am) for k in KEYS}
            d.update({k: sum_over(v, k, fs, am) for k in SUMS})
            head[g][v] = d
        # share of the gap between the tracker and perfect knowledge that each variant closes (ink error)
        for ref in ("tracker", "tracker_rt"):
            if ref in head[g] and "oracle" in head[g] and head[g][ref]["ink_err_um"] is not None:
                e0, eo = head[g][ref]["ink_err_um"], head[g]["oracle"]["ink_err_um"]
                for v in variants:
                    e = head[g][v]["ink_err_um"]
                    if e is not None and e0 - eo > 1e-9:
                        head[g][v][f"gap_closed_vs_{ref}"] = (e0 - e) / (e0 - eo)
    free = {}
    for o in test["outs"]:
        for v, m in o["tremor_free"]["variants"].items():
            free.setdefault(v, []).append(m)
    free_agg = {v: {k: float(np.mean([x[k] for x in ms if x.get(k) is not None])) for k in
                    ("false_correction_um", "ink_err_um", "recognition", "word_acc_app") if any(x.get(k) is not None for x in ms)}
                for v, ms in free.items()}
    terr = {}
    for case in ("ai_correct", "ai_predicted", "wrong_full"):
        for a in amps:
            x = [r["template_error"][case] for r in rows if abs(r["amp_mm"] - a) < 1e-9 and r.get("template_error")]
            if x:
                terr.setdefault(case, {})[f"{a:g}mm"] = {k: float(np.nanmean([y[k] for y in x])) for k in x[0]}
    return {"by_condition": by, "headlines": head, "tremor_free": free_agg, "template_error": terr,
            "n_scenarios": len(rows), "writers": sorted({r["writer"] for r in rows}), "seeds": sorted({r["seed"] for r in rows}),
            "f0s": f0s, "amps_mm": amps,
            "prediction": _prediction_stats()}


def _prediction_stats() -> Dict:
    from . import core as CO
    p = CO.predictions()
    n = len(p)
    guided = [q for q in p if q["conf"] >= CO.C_MIN]
    return {"n_letters": n, "top1_correct": float(np.mean([q["correct"] for q in p])),
            "letters_guided": len(guided) / n, "correct_when_guided": float(np.mean([q["correct"] for q in guided])) if guided else None,
            "mean_authority": float(np.mean([CO.gated_conf(q["conf"]) for q in p]))}


# ------------------------------------------------------------------ figures
def _fmt_um(v):
    return "n/a" if v is None else (f"{v / 1000:.2f} mm" if v >= 100 else f"{v:.0f} µm")


def base_key(test) -> str:
    return "tracker_rt" if test["cfg"].get("base") else "tracker"


def fig_before_after(test: Dict, od: Path) -> Optional[Dict]:
    viz, rows, writer = None, None, None
    for o in test["outs"]:
        if o.get("viz"):
            viz, rows, writer = o["viz"], o["rows"], o["writer"]
    if viz is None:
        return None
    bk = base_key(test)
    keys = ["intended", "none", "tracker"] + (["tracker_rt"] if bk == "tracker_rt" else []) + \
           ["prior_ai_predicted", "guide_ai_predicted", "clean_" + bk, "oracle"]
    labels = {"intended": "Intended", "none": "Ordinary pen", "tracker": "Rev H + tracker\n(handwriting study)",
              "tracker_rt": "Rev H + tracker\nre-tuned (no AI)",
              "prior_ai_predicted": f"Rev H + tracker\n+ AI prior", "guide_ai_predicted": "Rev H + tracker\n+ AI guidance",
              "clean_" + bk: "Digital clean copy\n(app only, not ink)", "oracle": "Rev H, perfect\nknowledge (limit)"}
    cols = []
    for case in [k for k in viz if "Hz_" in k]:
        f0 = float(case.split("Hz")[0])
        amp = float(case.split("_")[1].rstrip("mm"))
        r = next((r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
        metrics = {}
        for dv in keys:
            if r is None or dv not in r["variants"]:
                continue
            m = r["variants"][dv]
            nw = len(m["recognised_words"].split())
            txt = (f"ink error {_fmt_um(m['ink_err_um'])}  ·  letters read {m['recognition']:.0%}\n"
                   f"words read by the app {round(m['word_acc_app'] * nw)}/{nw}")
            if dv.startswith(("prior_", "guide_")):
                txt += f"  ·  AI share {m.get('ai_share', 0):.0%}  ·  wrong letters {m.get('mispred_flips', 0)}"
            metrics[dv] = txt
        paths = {k: viz[case][k] for k in keys if k in viz[case]}
        paths["intended"] = viz["intended"]
        metrics["intended"] = "what the writer meant to write\n(the same hand without tremor)"
        cols.append({"title": f"hand tremor {amp:g} mm peak at {f0:g} Hz (writer {writer}, seed 200)", "paths": paths,
                     "intended": viz["intended"], "metrics": metrics, "x_height": viz.get("x_height_mm", 2.5)})
    out = od / "fig_before_after.png"
    FG.before_after(out, cols, keys, labels, STATUS,
                    "Grey dashes: intended letters. AI = the app's predicted letters (top-1, two letters ahead, confidence-gated). "
                    "The clean copy is digital: the paper keeps the causal pen's ink. Synthetic writer and tremor; nothing measured.",
                    suptitle="Severe tremor: the same sentence, hand and tremor, with each kind of help")
    return {"keys": keys}


def fig_summary(agg: Dict, test: Dict, od: Path) -> None:
    bc = agg["by_condition"]
    bk = base_key(test)
    f0s = agg["f0s"]
    series_keys = ["none", "tracker"] + (["tracker_rt"] if bk == "tracker_rt" else []) + \
                  ["prior_ai_predicted", "guide_ai_predicted", "tracker_sev", "clean_" + bk, "oracle"]
    panels = []
    for key, lab, ylab, scale in (("ink_err_um", "Ink error", "mm RMS from the intended letters", 1e-3),
                                  ("word_acc_app", "Words read by the app", "share of words", 1.0)):
        for a in agg["amps_mm"]:
            series = []
            for dv in series_keys:
                if dv not in bc:
                    continue
                y = [bc[dv].get(f"{f:g}Hz_{a:g}mm", {}).get(key) for f in f0s]
                if any(v is None for v in y):
                    continue
                series.append({"label": LABELS[dv], "y": [v * scale for v in y], "color": COL.get(dv, C[0]),
                               "ls": "--" if dv in ("oracle",) or dv.startswith("clean") else (":" if dv == "tracker_sev" else "-")})
            panels.append({"title": f"{lab}, tremor {a:g} mm at the hand", "x": f0s, "xlabel": "tremor frequency (Hz)",
                           "ylabel": ylab, "series": series, "xticks": f0s,
                           "ylim": (0, 1.05) if key == "word_acc_app" else None})
    FG.lines_chart(od / "fig_summary.png", panels, STATUS,
                   f"writers {min(agg['writers'])}-{max(agg['writers'])}, seeds {min(agg['seeds'])}-{max(agg['seeds'])}; "
                   f"mean of {agg['n_scenarios'] // max(len(f0s) * len(agg['amps_mm']), 1)} runs per point",
                   ncols=3, size=(13.0, 4.3))


def fig_safety(agg: Dict, test: Dict, od: Path) -> None:
    h = agg["headlines"]
    hi, lo = h["6_10Hz_1_2mm"], h["0.3mm"]
    vs = [v for v in ("prior_ai_correct", "prior_ai_predicted", "prior_wrong_full", "guide_ai_correct", "guide_ai_predicted",
                      "guide_wrong_full") if v in hi]
    lab = [LABELS[v].replace("+ ", "") for v in vs]

    def per1000(d, k):
        return None if d.get(k) is None or not d.get("n_letters") else 1000.0 * d[k] / d["n_letters"]
    free = agg["tremor_free"]
    bk = base_key(test)
    panels = [
        {"title": "Wrong letters introduced, 1-2 mm (per 1000 letters)", "labels": lab,
         "values": [per1000(hi[v], "flips") for v in vs], "colors": [COL.get(v) for v in vs], "fmt": "{:.1f}",
         "xlabel": "letters newly read as the wrong predicted letter, vs the tracker underneath"},
        {"title": "Letters broken, 1-2 mm (per 1000 letters)", "labels": lab,
         "values": [per1000(hi[v], "broken") for v in vs], "colors": [COL.get(v) for v in vs], "fmt": "{:.1f}",
         "xlabel": "read correctly with the tracker alone, not with the AI"},
        {"title": "AI share of the ink path, 1-2 mm", "labels": lab,
         "values": [hi[v].get("ai_share") for v in vs], "colors": [COL.get(v) for v in vs], "fmt": "{:.0%}",
         "xlabel": "moved by the AI, vs the tracker alone"},
        {"title": "Ink error at 0.3 mm (µm)", "labels": [LABELS[bk].split(" (")[0]] + lab,
         "values": [lo[bk]["ink_err_um"]] + [lo[v]["ink_err_um"] for v in vs], "colors": [COL.get(bk)] + [COL.get(v) for v in vs],
         "fmt": "{:.0f}", "ref": lo[bk]["ink_err_um"], "xlabel": "dashed = the tracker underneath"},
        {"title": "False correction on tremor-free writing (µm)",
         "labels": [LABELS[v].replace("+ ", "") for v in ("tracker", bk) + tuple(vs) if v in free][:len(vs) + 2],
         "values": [free[v]["false_correction_um"] for v in ("tracker", bk) + tuple(vs) if v in free][:len(vs) + 2],
         "colors": [COL.get(v) for v in ("tracker", bk) + tuple(vs) if v in free][:len(vs) + 2], "fmt": "{:.0f}", "ref": 25.0,
         "xlabel": "RMS ink displacement vs the nose held; dashed = 25 µm (AC-E01-09)"},
    ]
    if bk == "tracker":
        panels[-1]["labels"] = [LABELS[v].replace("+ ", "") for v in ("tracker",) + tuple(vs) if v in free]
        panels[-1]["values"] = [free[v]["false_correction_um"] for v in ("tracker",) + tuple(vs) if v in free]
        panels[-1]["colors"] = [COL.get(v) for v in ("tracker",) + tuple(vs) if v in free]
    FG.bars_chart(od / "fig_safety.png", panels, STATUS,
                  f"test writers 0-5, seeds 200-203, 6/8/10 Hz; {agg['n_scenarios']} scenarios", ncols=3, size=(15.5, 3.8),
                  share_labels=False)


def fig_tuning(t0: Dict, t1: Optional[Dict], t2: Optional[Dict], od: Path) -> None:
    sel = t0["selection"]
    tab = sel["table"]
    ks = list(tab.keys())
    short = []
    for k in ks:
        if k == "revh":
            short.append("Rev H set")
        else:
            d = dict(x.split("=") for x in k.split(","))
            short.append(f"qt {float(d['qt']):.0e}, g {float(d['g']):g}")
    colors = [C[2] if k == sel["chosen_key"] else (C[0] if (tab[k]["fc_ok"] and tab[k]["small_tremor_ok"]) else plotstyle.MUTED) for k in ks]
    panels = [{"title": "T0: ink error at 1-2 mm (µm), tuning data", "labels": short, "values": [tab[k]["J_ink_1_2mm_um"] for k in ks],
               "colors": colors, "fmt": "{:.0f}", "xlabel": "green = chosen; grey = fails a rule"},
              {"title": "T0: false correction, tremor-free (µm)", "labels": short, "values": [tab[k]["false_correction_um"] for k in ks],
               "colors": colors, "fmt": "{:.0f}", "ref": 30.0, "xlabel": "dashed = 30 µm rule"}]
    for t, name in ((t1, "T1 prior"), (t2, "T2 guidance")):
        if not t:
            continue
        s = t["selection"]
        tk = list(s["table"].keys())
        lab = []
        for k in tk:
            p = s["table"][k]["params"]
            lab.append(f"form {p['tpl_mode']:.0f}, σ {p['sigma_t'] * 1e6:.0f} µm, drop {p['drop_um']:.0f}" if name.startswith("T1")
                       else f"g {p['g_max']:g}, capture {p['capture'] * 1e3:.1f} mm")
        cl = [C[2] if (k == s["best_passing"] and s["adopted"]) else (C[0] if s["table"][k]["passes"] else plotstyle.MUTED) for k in tk]
        panels.append({"title": f"{name}: gain vs the tracker, 1-2 mm", "labels": lab,
                       "values": [s["table"][k]["gain_vs_base"] for k in tk], "colors": cl, "fmt": "{:+.0%}",
                       "ref": 0.03, "xlabel": "dashed = 3 % adoption rule; grey = fails a safety rule"})
    FG.bars_chart(od / "fig_tuning.png", panels, "SIMULATION (model HW1), tuning writers 100-103, seed 300",
                  "choices made on tuning data only, rules fixed before the test (aiprior/tuning.py)", ncols=2,
                  size=(12.5, 4.4), share_labels=False)


# ------------------------------------------------------------------ samples.json
def _dec(path, hz_in: float = 250.0, hz_out: float = 50.0, nd: int = 2, max_pts: int = 3000):
    p = np.asarray(path, float)
    step = max(1, int(round(hz_in / hz_out)))
    q = p[::step]
    if len(q) > max_pts:
        q = q[:: int(math.ceil(len(q) / max_pts))]
    return [[round(float(a), nd), round(float(b), nd), int(c > 0.5)] for a, b, c in q]


def samples(test: Dict, od: Path) -> Dict:
    panels = []
    bk = base_key(test)
    keys = ["none", "tracker"] + (["tracker_rt"] if bk == "tracker_rt" else []) + \
           ["prior_ai_predicted", "guide_ai_predicted", "guide_wrong_full", "clean_" + bk, "oracle"]
    for o in test["outs"]:
        if not o.get("viz"):
            continue
        v = o["viz"]
        for case in [k for k in v if "Hz_" in k]:
            f0 = float(case.split("Hz")[0])
            amp = float(case.split("_")[1].rstrip("mm"))
            r = next((r for r in o["rows"] if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
            for dv in keys:
                if dv not in v[case]:
                    continue
                m = r["variants"][dv] if r else {}
                digital = dv.startswith("clean")
                panels.append({"id": f"aiprior_{dv}_{case}".replace(".", "p"), "title": f"{LABELS[dv]} - tremor {amp:g} mm at {f0:g} Hz",
                               "condition": "et_severe_tremor_ai", "device": dv,
                               "caption": (f"Writer {o['writer']}, 'return library books by friday', hand tremor {amp:g} mm peak at {f0:g} Hz "
                                           "(seed 200). The same hand and tremor for every row. "
                                           + ("DIGITAL copy made by the app after writing (non-causal); the paper keeps the pen's ink."
                                              if digital else "Ink on the paper (causal pen).")),
                               "evidence": "SIM", "intended": _dec(v["intended"]), "ink": _dec(v[case][dv]),
                               "metrics": {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k)) for k in
                                           ("ink_err_um", "recognition", "word_acc_app", "recognised_words", "app_words", "at_travel_limit",
                                            "q_rms_mm", "device_share", "ai_share", "flips", "mispred_flips", "broken", "fixed")
                                           if k in m}})
    doc = {"meta": provenance.metadata("SIMULATION (model HW1; synthetic writers; nothing measured)",
                                       seeds={"writers": list(TEST_WRITERS), "seeds": [200]},
                                       extra={"script": "aiprior/report.py", "version": __version__,
                                              "schema": "panels[{id, title, condition, device, caption, evidence, intended [[x_mm, y_mm, pen_down]], ink [[...]], metrics}]; paths at 50 Hz, 0.01 mm",
                                              "units": "mm; page frame, x along the line, y up; pen_down 0/1"}),
           "panels": panels}
    (od / "samples.json").write_text(json.dumps(doc, separators=(",", ":")))
    return doc


# ------------------------------------------------------------------ build
def build(quick: bool = False) -> Dict:
    from . import evidence as EV
    test = _load("test", quick)
    t0, t1, t2 = _load("t0", quick), _load("t1", quick), _load("t2", quick)
    od = outdir(quick)
    agg = aggregate(test) if test else None
    if t0:
        fig_tuning(t0, t1, t2, od)
    if test:
        fig_before_after(test, od)
        fig_summary(agg, test, od)
        fig_safety(agg, test, od)
        samples(test, od)
    doc = {"meta": provenance.metadata(EVIDENCE_SIM,
                                       seeds={"test_writers": list(TEST_WRITERS), "test_seeds": list(TEST_SEEDS),
                                              "tune_writers": list(TUNE_WRITERS), "tune_seeds": list(TUNE_SEEDS)},
                                       extra={"script": "aiprior/run_study.py", "version": __version__, "quick": quick,
                                              "inputs": _inputs()}),
           "config": test["cfg"] if test else None,
           "labels": LABELS,
           "tuning": {"t0": {"selection": t0["selection"], "confirmation_seed_301": t0.get("confirmation_seed_301"),
                             "chosen": t0["chosen"], "amp_gate_a_lo_m": t0["amp_gate_a_lo"]} if t0 else None,
                      "t1": {"selection": t1["selection"]} if t1 else None,
                      "t2": {"selection": t2["selection"]} if t2 else None},
           "aggregate": agg}
    provenance.write_json(str(od / "aiprior.json"), doc)
    EV.write_rows(od / "evidence_rows.csv", doc)
    return doc


def _inputs() -> Dict:
    import hashlib
    from . import REPO_ROOT
    out = {}
    for rel in ("results/revH/tip_params.json", "results/opt/inertial_tracker_revh.json", "config/parameters.yaml"):
        p = REPO_ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out
