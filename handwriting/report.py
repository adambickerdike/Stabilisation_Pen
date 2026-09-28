"""Assemble figures, samples.json, outcomes.json and the proposed ledger rows from the cached stage outputs.

Evidence status: everything is SIMULATION / CALCULATION on synthetic data (model HW1), plus LITERATURE rows.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, __version__, ensure_paths
from . import evidence as EV
from . import figures as FG
from . import params as PR

ensure_paths()
from stabpen import plotstyle, provenance  # noqa: E402

C = plotstyle.SERIES
CACHE = RESULTS_DIR / "_cache"
DEV_COL = {"none": plotstyle.MUTED, "weighted": C[3], "pencil_akf": C[4], "pencil_oracle": C[4], "revH_off": C[6],
           "revH_akf": C[1], "revH_akf_revh": C[0], "revH_oracle": C[2]}
DEV_LS = {"pencil_oracle": "--", "revH_oracle": "--"}


def _load(name: str, quick: bool) -> Optional[Dict]:
    for n in ([name + "_quick", name] if quick else [name]):
        p = CACHE / f"{n}.json"
        if p.exists():
            return json.loads(p.read_text())
    return None


def _fmt_um(v):
    return "n/a" if v is None else (f"{v / 1000:.2f} mm" if v >= 100 else f"{v:.0f} µm")


# ------------------------------------------------------------------ ET
def et_headlines(agg: Dict) -> Dict:
    ba = agg["by_amplitude"]
    bc = agg["by_condition"]

    def cell(dv, key, f, a):
        return bc.get(dv, {}).get(f"{f:g}Hz_{a:g}mm", {}).get(key)

    out = {}
    lines = []
    for a in (0.3, 1.0, 2.0):
        k = f"{a:g}mm"
        row = {dv: ba[dv][k] for dv in ba if k in ba[dv]}
        out[k] = {dv: {m: row[dv].get(m) for m in ("ink_err_um", "recognition", "word_acc_app", "at_travel_limit", "ink_err_ratio")}
                  for dv in row}
    for f in (4.0, 6.0, 8.0, 10.0):
        for a in (1.0, 2.0):
            n = cell("none", "ink_err_um", f, a)
            h = cell("revH_akf_revh", "ink_err_um", f, a) or cell("revH_akf", "ink_err_um", f, a)
            o = cell("revH_oracle", "ink_err_um", f, a)
            if n and h and o:
                lines.append(f"{f:g} Hz {a:g} mm: none {n:.0f} um, Rev H tracker {h:.0f} ({h / n - 1:+.0%}), oracle {o:.0f} ({o / n - 1:+.0%})")
    out["by_frequency_text"] = lines
    tf = agg.get("tremor_free", {})
    out["tremor_free_distortion_um"] = {k: v.get("distortion_um") for k, v in tf.items() if v.get("distortion_um") is not None}

    def mean_over(dv, key, fs, amps):
        v = [cell(dv, key, f, a) for f in fs for a in amps]
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else None
    hi = {dv: {"ink": mean_over(dv, "ink_err_um", (8.0, 10.0), (1.0, 2.0)), "words": mean_over(dv, "word_acc_app", (8.0, 10.0), (1.0, 2.0)),
               "letters": mean_over(dv, "recognition", (8.0, 10.0), (1.0, 2.0))} for dv in bc}
    lo = {dv: {"ink": mean_over(dv, "ink_err_um", (4.0, 6.0), (1.0, 2.0)), "words": mean_over(dv, "word_acc_app", (4.0, 6.0), (1.0, 2.0)),
               "letters": mean_over(dv, "recognition", (4.0, 6.0), (1.0, 2.0))} for dv in bc}
    out["high_f_1_2mm"] = hi
    out["low_f_1_2mm"] = lo
    return out


def fig_et(et: Dict, outdir: Path) -> List[Dict]:
    agg = et["aggregate"]
    bc = agg["by_condition"]
    f0s = sorted({float(k.split("Hz")[0]) for dv in bc.values() for k in dv})
    amps = sorted({float(k.split("_")[1].rstrip("mm")) for dv in bc.values() for k in dv})
    panels = []
    for key, lab, ylab, scale in (("ink_err_um", "Ink error", "mm (RMS) from the intended letters", 1e-3),
                                  ("word_acc_app", "Words read by the app", "share of words", 1.0)):
        for a in amps:
            series = []
            for dv in ("none", "weighted", "pencil_akf", "revH_akf", "revH_akf_revh", "revH_oracle"):
                if dv not in bc:
                    continue
                y = [bc[dv].get(f"{f:g}Hz_{a:g}mm", {}).get(key) for f in f0s]
                if any(v is None for v in y):
                    continue
                series.append({"label": _et_label(dv), "y": [v * scale for v in y], "color": DEV_COL[dv], "ls": DEV_LS.get(dv, "-")})
            panels.append({"title": f"{lab}, tremor {a:g} mm at the hand", "x": f0s, "xlabel": "tremor frequency (Hz)",
                           "ylabel": ylab, "series": series, "xticks": f0s,
                           "ylim": (0, 1.05) if key == "word_acc_app" else None})
    grid = et.get("grid") or {}
    sd = grid.get("seeds", [200, 201, 202, 203])
    FG.lines_chart(outdir / "fig_et_summary.png", panels, "SIMULATION (model HW1)",
                   f"aiguide test writers {min(agg['writers'])}-{max(agg['writers'])}, seeds {min(sd)}-{max(sd)}; "
                   f"each point = mean of {agg['n_scenarios'] // max(len(f0s) * len(amps), 1)} runs",
                   ncols=3, size=(13.0, 3.9))
    return panels


PD_SHORT = {"pen_none": "Ordinary pen", "revH_off": "Rev H, off", "cue": "Vibration cue", "lines": "Lines >= 1 cm",
            "size_assist_1.2": "Size x1.2", "size_assist_1.35": "Size x1.35", "size_assist_1.5": "Size x1.5",
            "size_assist_y1.35": "Size x1.35, vertical", "size_adapt_y1.5": "Adaptive, vertical",
            "cue_size_1.35": "Cue + size x1.35"}
PD_ROW = {"pen_none": "No device\n(ordinary pen)", "cue": "Vibration cue\n'write bigger'", "lines": "Lines >= 1 cm",
          "size_assist_1.35": "Size assist x1.35", "size_assist_y1.35": "Size assist x1.35,\nvertical only",
          "size_adapt_y1.5": "Adaptive size\nassist, vertical"}
PR_SHORT = {"none": "No guidance", "cue": "Cue on error", "nose_partial": "Nose, partial", "nose_full": "Nose, full",
            "nose_nogate": "Nose, no gate", "board_partial": "Board, partial", "board_full": "Board, full"}
PR_ROW = {"none": "No guidance", "nose_partial": "Nose guidance,\npartial (0.5)", "nose_full": "Nose guidance,\nfull",
          "board_partial": "Board, partial\n(1 mm band)", "board_full": "Board, full\n(0.20 N/mm + lead)",
          "nose_nogate": "Nose, no gate\n(the pen writes)"}


def _et_label(dv):
    from .et_study import LABELS
    return LABELS.get(dv, dv)


def fig_et_before_after(et: Dict, outdir: Path) -> None:
    viz = None
    for o in et["outs"]:
        if o.get("viz"):
            viz = o["viz"]
            writer = o["writer"]
            rows = o["rows"]
    if viz is None:
        return
    cols = []
    for case in [k for k in viz if "Hz_" in k]:
        f0 = float(case.split("Hz")[0])
        amp = float(case.split("_")[1].rstrip("mm"))
        r = next((r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
        metrics = {}
        if r:
            for dv, m in r["devices"].items():
                nw = len(m["recognised_words"].split())
                metrics[dv] = (f"ink error {_fmt_um(m['ink_err_um'])}  ·  letters read {m['recognition']:.0%}\n"
                               f"words read by the app {round(m['word_acc_app'] * nw)}/{nw}" +
                               (f"  ·  at travel limit {m['at_travel_limit']:.0%}" if dv.startswith(("pencil", "revH")) and dv != "revH_off" else ""))
        paths = {k: v for k, v in viz[case].items()}
        paths["intended"] = viz["intended"]
        metrics["intended"] = "what the writer meant to write\n(the same hand without tremor)"
        cols.append({"title": f"hand tremor {amp:g} mm peak at {f0:g} Hz (writer {writer}, seed 200)", "paths": paths,
                     "intended": viz["intended"], "metrics": metrics, "x_height": viz.get("x_height_mm", 2.5)})
    keys = ["intended", "none", "weighted", "pencil_akf", "revH_akf", "revH_akf_revh", "revH_oracle"]
    labels = {"intended": "Intended", "none": "No device\n(ordinary pen)", "weighted": "Weighted pen\n(+60 g)",
              "pencil_akf": "Pencil Rev P0\n+ tracker", "revH_akf": "Rev H + tracker\nas shipped",
              "revH_akf_revh": "Rev H + tracker\nre-tuned for Rev H", "revH_oracle": "Rev H, perfect\nknowledge (limit)"}
    FG.before_after(outdir / "fig_et_before_after.png", cols, keys, labels, "SIMULATION (model HW1)",
                    "Grey dashes: intended letters. Tracker = accelerometer + page-sensor Kalman filter (fusion AKF). "
                    "Synthetic writer and tremor; nothing measured.",
                    suptitle="Essential tremor: the same sentence, the same hand and tremor, with each pen")


SENS_NAME = {"nominal": "This study", "open_loop_hand": "Drag not compensated", "stiff_grip_x2": "Grip twice as stiff",
             "contact_gating": "Nose acts only in contact", "revH_lead_defaults": "Lead's first Rev H values"}
DEV_SHORT = {"weighted": "weighted pen", "revH_off": "Rev H, nose held", "pencil_akf": "pencil + tracker",
             "revH_akf_revh": "Rev H + re-tuned tracker", "revH_oracle": "Rev H, perfect knowledge"}


def fig_et_sensitivity(sens: Dict, outdir: Path, et: Optional[Dict] = None) -> Dict:
    if not sens:
        return {}
    panels = []
    summary = {}
    variants = [(k, v) for k, v in sens.items() if not k.startswith("_")]
    if et:                                   # the nominal case: the same writers with seed 200 from the main grid
        rows = [r for o in et["outs"] if o["writer"] in (0, 1, 2, 3, 4, 5) for r in o["rows"] if r["seed"] == 200]
        nominal = {}
        for case in ("10Hz_1mm", "6Hz_1mm"):
            f0, amp = float(case.split("Hz")[0]), float(case.split("_")[1].rstrip("mm"))
            sel = [r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9]
            for dv in DEV_SHORT:
                v = [r["devices"][dv]["ink_err_um"] / r["devices"]["none"]["ink_err_um"] for r in sel if dv in r["devices"]]
                if v:
                    nominal.setdefault(dv, {})[case] = {"ink_err_ratio": float(np.mean(v))}
        variants = [("nominal", {"aggregate": {"by_condition": nominal}})] + variants
    for case in ("10Hz_1mm", "6Hz_1mm"):
        labels, vals, cols = [], [], []
        for vname, v in variants:
            bc = v["aggregate"]["by_condition"]
            for dv in DEV_SHORT:
                c = bc.get(dv, {}).get(case)
                if c is None:
                    continue
                labels.append(f"{SENS_NAME.get(vname, vname)}: {DEV_SHORT[dv]}")
                vals.append(c["ink_err_ratio"])
                cols.append(DEV_COL[dv])
                summary.setdefault(case, {}).setdefault(vname, {})[dv] = c["ink_err_ratio"]
        panels.append({"title": f"Ink error relative to the ordinary pen, {case.replace('Hz_', ' Hz, ').replace('mm', ' mm')}",
                       "labels": labels, "values": vals, "colors": cols, "xlabel": "ratio (1 = ordinary pen)", "ref": 1.0,
                       "fmt": "{:.2f}"})
    FG.bars_chart(outdir / "fig_et_sensitivity.png", panels, "SIMULATION (model HW1): sensitivity",
                  "writers 0-5, seed 200. Drag not compensated and contact-only nose = P1 conventions; grip twice as stiff = 2x HAP-26",
                  ncols=2, size=(13.0, 8.0))
    return summary


# ------------------------------------------------------------------ PD
def pd_headlines(agg: Dict) -> Dict:
    bc = agg["by_condition"]
    keys = ("xh_start_mm", "xh_end_mm", "xh_drift", "recognition", "word_acc_app", "norm_jerk_median", "speed_peaks_per_stroke",
            "mean_speed_mm_s", "tremor_in_ink_um", "tremor_at_hand_um", "writing_time_s", "touching_frac", "n_cues")
    return {c: {k: bc[c].get(k) for k in keys} for c in bc}


def fig_pd(pd: Dict, outdir: Path) -> None:
    from .pd_study import LABELS
    agg = pd["aggregate"]["by_condition"]
    order = [c for c in ("revH_off", "cue", "lines", "size_assist_1.2", "size_assist_1.35", "size_assist_1.5",
                         "size_assist_y1.35", "size_adapt_y1.5", "cue_size_1.35") if c in agg]
    pal = list(C) + [plotstyle.MUTED, plotstyle.INK2]
    colours = {c: pal[i % len(pal)] for i, c in enumerate(order)}
    # size profile along the sentence (x1.35 in both axes and vertical only give the same letter height)
    lab = dict(LABELS)
    lab["size_assist_1.35"] = "Size assist x1.35 (both axes or vertical only: same letter height)"
    series = [{"label": lab[c], "y": agg[c]["xh_profile_mm"], "color": colours[c], "ls": "-" if "size" not in c else "--"}
              for c in order if c in ("revH_off", "cue", "lines", "size_assist_1.35", "size_adapt_y1.5")]
    n = len(series[0]["y"])
    FG.lines_chart(outdir / "fig_pd_size_profile.png",
                   [{"title": "Letter size (x-height) along the pangram, mean of writers 0-5 x seeds 200-203", "x": list(range(1, n + 1)),
                     "xlabel": "letter number", "ylabel": "x-height of the ink (mm)", "series": series}],
                   "SIMULATION (model HW1; writer responses = ASSUMPTION ranges)", "start 5.0 mm; progressive loss 20-30 %",
                   ncols=1, size=(12.0, 4.6))
    panels = []
    for key, title, fmt in (("xh_end_mm", "Letter size at the end (mm)", "{:.2f}"),
                            ("recognition", "Letters read correctly", "{:.0%}"),
                            ("norm_jerk_median", "Normalised jerk per stroke (lower = smoother)", "{:.0f}"),
                            ("tremor_in_ink_um", "Tremor in the ink, 3-15 Hz (µm)", "{:.0f}"),
                            ("touching_frac", "Neighbouring letters touching", "{:.0%}"),
                            ("writing_time_s", "Writing time (s)", "{:.1f}")):
        panels.append({"title": title, "labels": [PD_SHORT[c] for c in order], "values": [agg[c].get(key) for c in order],
                       "colors": [colours[c] for c in order], "fmt": fmt})
    FG.bars_chart(outdir / "fig_pd_summary.png", panels, "SIMULATION (model HW1; writer responses = ASSUMPTION ranges)",
                  "writers 0-5 x seeds 200-203; PD-like writers (5 mm start, 20-30 % loss, slow, 4-6 Hz tremor 0.05-0.25 mm)",
                  ncols=3, size=(13.0, 4.2))


def fig_pd_before_after(pd: Dict, outdir: Path) -> None:
    from .pd_study import LABELS
    viz, rows, writer = None, None, None
    for o in pd["outs"]:
        if o.get("viz"):
            viz, rows, writer = o["viz"], o["rows"], o["writer"]
    if not viz:
        return
    keys = [c for c in ("pen_none", "cue", "lines", "size_assist_1.35", "size_assist_y1.35", "size_adapt_y1.5") if c in viz]
    metrics = {}
    for c in keys:
        r = next((r for r in rows if r["cond"] == c and r["seed"] == 200), None)
        if r:
            metrics[c] = (f"x-height {r['xh_start_mm']:.1f} → {r['xh_end_mm']:.1f} mm  ·  letters read {r['recognition']:.0%}\n"
                          f"jerk {r['norm_jerk_median']:.0f}  ·  tremor in ink {r['tremor_in_ink_um']:.0f} µm" +
                          (f"  ·  cues {r['n_cues']}" if r['n_cues'] else ""))
    # two halves of the long pangram line: show the whole line
    col = {"title": f"PD-like writer {writer}, seed 200: 'the quick brown fox jumps over the lazy dog'",
           "paths": {c: viz[c]["ink"] for c in keys}, "intended": viz[keys[0]]["intended"], "metrics": metrics,
           "x_height": 5.0, "show_intended": False}
    FG.before_after(outdir / "fig_pd_before_after.png", [col], keys, {c: PD_ROW.get(c, LABELS[c]) for c in keys},
                    "SIMULATION (model HW1)", "Ruled lines 10 mm apart. Cue and lines change the writer (ASSUMPTION response); size assist moves the ink.",
                    suptitle="Parkinson's micrographia: letters shrink along the line; what each help does",
                    panel_h=22.0, ylim=(-8.0, 14.0), spacing=10.0)


# ------------------------------------------------------------------ practice
def practice_headlines(agg: Dict) -> Dict:
    out = {}
    for prof in ("dysgraphia", "dyslexia"):
        if prof not in agg:
            continue
        out[prof] = {c: {k: v.get(k) for k in ("target_err_um", "letters_read_ok", "words_app", "device_share",
                                                 "device_disp_max_mm", "error_letters_read_as_target",
                                                 "flag_rate_on_errors", "flag_rate_on_correct")}
                     for c, v in agg[prof].items() if isinstance(v, dict) and "n" in v}
    return out


def fig_practice(pr: Dict, outdir: Path) -> None:
    from .practice import LABELS
    viz, rows, writer = None, None, None
    for o in pr["outs"]:
        if o.get("viz"):
            viz, rows, writer = o["viz"], o["rows"], o["writer"]
    if not viz:
        return
    cols = []
    keys = ["none", "nose_partial", "nose_full", "board_partial", "board_full", "nose_nogate"]
    for prof in ("dysgraphia", "dyslexia"):
        if prof not in viz:
            continue
        v = viz[prof]
        vs = v.get("seed", 200)
        r = next((r for r in rows if r["profile"] == prof and r["seed"] == vs), None)
        metrics = {}
        for c in keys:
            if r and c in r["conds"]:
                m = r["conds"][c]
                metrics[c] = (f"ink vs target {_fmt_um(m['target_err_um'])}  ·  letters read {m['letters_read_ok']:.0%}\n"
                              f"device share of the ink motion {m['device_share']:.0%}")
        cols.append({"title": f"{prof}-like learner (writer {writer}, seed {vs}); green = target letters",
                     "paths": {c: v[c] for c in keys if c in v}, "intended": v["intended"], "metrics": metrics,
                     "x_height": v.get("x_height_mm", 2.5), "target": [np.asarray(s) * 1e3 for letter in v["target"] for s in letter],
                     "show_intended": False})
    FG.before_after(outdir / "fig_practice_before_after.png", cols, keys, {c: PR_ROW.get(c, LABELS[c]) for c in keys},
                    "SIMULATION (model HW1)", "Passive hand (neither follows nor resists); copybook target anchored at each letter's first touchdown.",
                    suptitle="Guided practice: 'a big dog dug a deep pit by the pond' copied with each kind of guidance")


def fig_practice_summary(pr: Dict, outdir: Path) -> None:
    from .practice import LABELS
    agg = pr["aggregate"]
    panels = []
    order = ["none", "nose_partial", "nose_full", "board_partial", "board_full", "nose_nogate"]
    for prof in ("dysgraphia", "dyslexia"):
        if prof not in agg:
            continue
        a = agg[prof]
        cs = [c for c in order if c in a]
        for key, title, fmt in (("target_err_um", f"{prof}: ink vs target (µm RMS)", "{:.0f}"),
                                ("letters_read_ok", f"{prof}: letters read as the target", "{:.0%}"),
                                ("device_share", f"{prof}: device share of the ink motion", "{:.0%}")):
            panels.append({"title": title, "labels": [PR_SHORT[c] for c in cs], "values": [a[c].get(key) for c in cs],
                           "colors": [C[i] for i in range(len(cs))], "fmt": fmt})
    FG.bars_chart(outdir / "fig_practice_summary.png", panels, "SIMULATION (model HW1)",
                  "writers 0-5 x seeds 200-203; passive hand; stroke-matched guidance; board = final board file + the board study's law",
                  ncols=3, size=(13.0, 3.6))


def fig_spelling(pr: Dict, outdir: Path) -> Dict:
    import matplotlib.pyplot as plt
    viz, rows = None, None
    for o in pr["outs"]:
        if o.get("viz"):
            viz, rows = o["viz"], o["rows"]
    if not viz or "dyslexia" not in viz:
        return {}
    vs = viz["dyslexia"].get("seed", 200)
    r = next((r for r in rows if r["profile"] == "dyslexia" and r["seed"] == vs), None)
    sp = r["spelling"]
    ink = np.asarray(viz["dyslexia"]["none"])
    plotstyle.apply()
    fig = plt.figure(figsize=(12.5, 5.6))
    ax = fig.add_axes([0.02, 0.50, 0.96, 0.40])
    FG.lined_panel(ax, ink[:, :2], ink[:, 2] > 0.5, viz["dyslexia"].get("x_height_mm", 2.5))
    ax.set_title("1. The ink stays exactly as written (the pen does not write for the user)", fontsize=10, loc="left")
    ax2 = fig.add_axes([0.02, 0.09, 0.96, 0.38])
    ax2.axis("off")
    lines = [("2. The app reads the words:", "  ".join(sp["recognised"].split()), plotstyle.INK2),
             ("3. It knows the target (copying or dictation) and flags:", ", ".join(sp["flagged_words_known_target"]) or "nothing", C[7]),
             ("   A gentle buzz and the right spelling shown and read aloud:", sp["target"], C[2]),
             ("4. A corrected digital copy is kept with the original ink:", sp["target"], plotstyle.INK),
             ("   Without the target (free writing), lexicon correction gives:", sp["app_corrected_free_writing"], C[3])]
    y = 0.95
    for a, b, col in lines:
        ax2.text(0.0, y, a, fontsize=10, color=plotstyle.INK, va="top")
        ax2.text(0.46, y, b, fontsize=11, color=col, va="top", family="monospace")
        y -= 0.2
    fig.text(0.02, 0.965, "Dyslexia-like learner: letters written  '" + sp["written_letters"] + "'", fontsize=10, color=plotstyle.INK2)
    from .practice import spelling_stats
    st = spelling_stats([r for o in pr["outs"] for r in o["rows"] if r["profile"] == "dyslexia"])
    fig.text(0.02, 0.035, (f"All dyslexia-like runs (writers 0-5 x seeds 200-203): {st['misspelled_words']} misspelled words. With the known "
                           f"target the app flagged {st['flagged_with_target']} ({st['flag_rate']:.0%}) and wrongly flagged "
                           f"{st['correct_words_flagged']} of {st['correct_words']} correct words ({st['false_flag_rate']:.0%}, reader errors). "
                           f"In free writing the lexicon correction repaired {st['fixed_by_free_writing_lexicon']} ({st['free_fix_rate']:.0%})."),
             fontsize=8.5, color=plotstyle.INK, wrap=True)
    sp = dict(sp)
    sp["stats_all_runs"] = st
    plotstyle.stamp(fig, "SIMULATION + CALCULATION (synthetic writer; app reader and lexicon correction)",
                    "real-word errors (dig, bog) need the known target; HAP-47/48/50")
    fig.savefig(outdir / "fig_spelling.png")
    plt.close(fig)
    FG.write_csv((outdir / "fig_spelling.csv"), ["step", "text"], [[a.strip(), b] for a, b, _ in lines])
    return sp


def fig_crosscheck(cc: Dict, outdir: Path) -> Dict:
    if not cc:
        return {}
    s = cc["summary"]
    labels, vals, cols = [], [], []
    names = {"P1": "P1 (pencil model)", "HW1": "HW1, P1's conventions", "HW1_nominal": "HW1, this study"}
    for case, d in s.items():
        for model, col in (("P1", C[4]), ("HW1", C[0]), ("HW1_nominal", C[2])):
            for k, kl in (("oracle_band_ratio", "perfect knowledge"), ("akf_band_ratio", "tracker")):
                labels.append(f"{case.replace('Hz_', ' Hz, ').replace('mm', ' mm')} | {names[model]} | {kl}")
                vals.append(d[model][k])
                cols.append(col)
    FG.bars_chart(outdir / "fig_crosscheck.png", [{"title": "Pencil Rev P0: 3-15 Hz ink error relative to its own neutral run, P1 against HW1",
                                                   "labels": labels, "values": vals, "colors": cols, "ref": 1.0, "fmt": "{:.2f}",
                                                   "xlabel": "ratio (1 = no correction)"}],
                  "SIMULATION (P1 unmodified vs HW1)", "writers 0-5, seed 200; HW1 with P1's conventions = drag not compensated, nose only in contact",
                  ncols=1, size=(11.0, 7.5))
    return s


# ------------------------------------------------------------------ samples.json
def _dec(path, hz_in: float = 250.0, hz_out: float = 50.0, nd: int = 2, max_pts: int = 3000):
    p = np.asarray(path, float)
    step = max(1, int(round(hz_in / hz_out)))
    q = p[::step]
    if len(q) > max_pts:
        q = q[:: int(math.ceil(len(q) / max_pts))]
    return [[round(float(a), nd), round(float(b), nd), int(c > 0.5)] for a, b, c in q]


def _target_path(strokes_by_letter):
    out = []
    for letter in strokes_by_letter:
        for s in letter:
            s = np.asarray(s) * 1e3
            if out:
                out.append([round(float(s[0, 0]), 2), round(float(s[0, 1]), 2), 0])
            out += [[round(float(x), 2), round(float(y), 2), 1] for x, y in s[:: max(1, len(s) // 40)]]
    return out


def samples(et, pd, pr, outdir: Path) -> Dict:
    panels = []
    if et:
        for o in et["outs"]:
            if not o.get("viz"):
                continue
            v = o["viz"]
            for case in [k for k in v if "Hz_" in k]:
                f0 = float(case.split("Hz")[0])
                amp = float(case.split("_")[1].rstrip("mm"))
                r = next((r for r in o["rows"] if r["f0"] == f0 and abs(r["amp_mm"] - amp) < 1e-9 and r["seed"] == 200), None)
                for dv in ("none", "weighted", "pencil_akf", "revH_akf", "revH_akf_revh", "revH_oracle"):
                    if dv not in v[case]:
                        continue
                    m = r["devices"][dv] if r else {}
                    panels.append({"id": f"et_{dv}_{case}".replace(".", "p"), "title": f"{_et_label(dv)} - tremor {amp:g} mm at {f0:g} Hz",
                                   "condition": "et_tremor", "device": dv,
                                   "caption": f"Writer {o['writer']}, 'return library books by friday', hand tremor {amp:g} mm peak at {f0:g} Hz (seed 200). "
                                              "The same hand and tremor for every pen. Ink error = distance of the ink to the intended letters.",
                                   "evidence": "SIM", "intended": _dec(v["intended"]), "ink": _dec(v[case][dv]),
                                   "metrics": {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k)) for k in
                                               ("ink_err_um", "band_err_um", "recognition", "word_acc_app", "recognised_words", "app_words",
                                                "at_travel_limit", "q_rms_mm")}})
    if pd:
        from .pd_study import LABELS as PL_
        for o in pd["outs"]:
            if not o.get("viz"):
                continue
            for c, v in o["viz"].items():
                r = next((r for r in o["rows"] if r["cond"] == c and r["seed"] == 200), None)
                panels.append({"id": f"pd_{c}".replace(".", "p"), "title": PL_[c], "condition": "pd_micrographia", "device": c,
                               "caption": f"PD-like writer {o['writer']} (start x-height 5 mm, progressive size loss, slow, small tremor), pangram. "
                                          "'intended' = the writer's own shrinking plan; cue and lines change the plan (ASSUMPTION response), size assist moves the ink.",
                               "evidence": "SIM", "intended": _dec(v["intended"], hz_out=30.0), "ink": _dec(v["ink"], hz_out=30.0),
                               "metrics": {k: (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k)) for k in
                                           ("xh_start_mm", "xh_end_mm", "recognition", "word_acc_app", "norm_jerk_median",
                                            "tremor_in_ink_um", "touching_frac", "n_cues", "writing_time_s")} if r else {}})
    if pr:
        from .practice import LABELS as PRL
        for o in pr["outs"]:
            if not o.get("viz"):
                continue
            for prof, v in o["viz"].items():
                vs = v.get("seed", 200)
                r = next((r for r in o["rows"] if r["profile"] == prof and r["seed"] == vs), None)
                tgt = _target_path(v["target"])
                for c in ("none", "cue", "nose_partial", "nose_full", "board_partial", "board_full", "nose_nogate"):
                    if c not in v:
                        continue
                    m = r["conds"][c] if r else {}
                    panels.append({"id": f"practice_{prof}_{c}", "title": f"{prof}: {PRL[c]}",
                                   "condition": "guided_practice", "device": c,
                                   "caption": f"{prof}-like learner (writer {o['writer']}, seed {vs}) copying 'a big dog dug a deep pit by the pond'. "
                                              "'intended' = the target copybook letters; 'hand_plan' = what the learner's hand does.",
                                   "evidence": "SIM", "intended": tgt, "hand_plan": _dec(v["intended"]), "ink": _dec(v[c]),
                                   "metrics": {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k)) for k in
                                               ("target_err_um", "letters_read_ok", "words_app", "device_share", "device_disp_max_mm",
                                                "recognised", "flag_rate_on_errors")}})
                if prof == "dyslexia" and r and r.get("spelling"):
                    sp = r["spelling"]
                    panels.append({"id": "spelling_dyslexia", "title": "Spelling help: the app flags, shows and keeps a corrected copy",
                                   "condition": "spelling", "device": "app_ai",
                                   "caption": "The ink is never changed. The app reads the words, compares them with the known target, buzzes gently, shows and reads the right spelling, and keeps a corrected digital copy.",
                                   "evidence": "SIM", "intended": tgt, "ink": _dec(v["none"]),
                                   "metrics": {"written_letters": sp["written_letters"], "recognised": sp["recognised"],
                                               "flagged_words": sp["flagged_words_known_target"], "corrected_copy": sp["target"],
                                               "free_writing_correction": sp["app_corrected_free_writing"]}})
    doc = {"meta": provenance.metadata("SIMULATION (model HW1; synthetic writers; nothing measured)",
                                       seeds={"writers": list(TEST_WRITERS), "seeds": [200]},
                                       extra={"script": "handwriting/report.py", "version": __version__,
                                              "schema": "panels[{id, title, condition, device, caption, evidence, intended [[x_mm, y_mm, pen_down]], ink [[...]], metrics}]; paths at 50 Hz (PD 30 Hz), 0.01 mm",
                                              "units": "mm; page frame, x along the line, y up; pen_down 0/1"}),
           "panels": panels}
    p = outdir / "samples.json"
    p.write_text(json.dumps(doc, separators=(",", ":")))
    return {"n_panels": len(panels), "bytes": p.stat().st_size}


# ------------------------------------------------------------------ outcomes.json and evidence rows
def build(quick: bool = False, timing: Optional[Dict] = None, outdir: Path = RESULTS_DIR) -> Dict:
    outdir.mkdir(parents=True, exist_ok=True)
    et = _load("et", quick)
    sens = _load("et_sens", quick)
    pd = _load("pd", quick)
    pr = _load("practice", quick)
    cc = _load("crosscheck", quick)
    tu = _load("tuning", quick)
    from . import primer
    prim = primer.build(outdir)
    out = {"meta": provenance.metadata("SIMULATION + CALCULATION (model HW1, synthetic writers and tremor) + LITERATURE rows; nothing measured",
                                       seeds={"test_writers": list(TEST_WRITERS), "test_seeds": list(TEST_SEEDS),
                                              "tune_writers": list(TUNE_WRITERS), "tune_seeds": list(TUNE_SEEDS)},
                                       extra={"script": "handwriting/run_study.py", "version": __version__, "quick": quick,
                                              "timing_s": timing or {}}),
           "devices": {"none": PR.ordinary_pen().describe(), "weighted": PR.weighted_pen().describe(),
                       "pencil": PR.pencil_p0().describe(), "revH": PR.rev_h().describe(), "revH_lead": PR.rev_h_lead().describe()},
           "hand": vars(PR.Hand.from_config()), "writing": vars(PR.Writing()),
           "board": {k: v for k, v in vars(PR.board()).items()},
           "trackers": {"ship": {k: v for k, v in PR.akf_ship().items() if k != "params"}, "revh": ({k: v for k, v in PR.akf_revh().items() if k != "params"} if PR.akf_revh() else None)},
           "primer": prim, "tuning": tu}
    if et:
        fig_et_before_after(et, outdir)
        fig_et(et, outdir)
        out["et"] = {"aggregate": et["aggregate"], "grid": et.get("grid"), "headlines": et_headlines(et["aggregate"]),
                     "inputs": et.get("inputs")}          # the tracker and Rev H values these results used
    if sens:
        out["et_sensitivity"] = {"summary": fig_et_sensitivity(sens, outdir, et),
                                 "aggregates": {k: v["aggregate"] for k, v in sens.items() if not k.startswith("_")},
                                 "inputs": sens.get("_inputs")}
    if pd:
        fig_pd_before_after(pd, outdir)
        fig_pd(pd, outdir)
        out["pd"] = {"aggregate": pd["aggregate"], "headlines": pd_headlines(pd["aggregate"])}
    if pr:
        fig_practice(pr, outdir)
        fig_practice_summary(pr, outdir)
        out["practice"] = {"aggregate": pr["aggregate"], "headlines": practice_headlines(pr["aggregate"]),
                           "spelling_example": fig_spelling(pr, outdir)}
    if cc:
        out["crosscheck"] = {"summary": fig_crosscheck(cc, outdir)}
    out["samples"] = samples(et, pd, pr, outdir)
    out["text"] = headline_text(out)
    provenance.write_json(str(outdir / "outcomes.json"), out)
    rows = EV.LITERATURE + EV.sim_rows({k: out["text"].get(k, {}) for k in ("et", "pd", "practice", "crosscheck")})
    EV.check_ids(rows)
    assert EV.ledger_header() == EV.HEADER
    EV.write_csv(outdir / "evidence_rows.csv", rows)
    return out


def headline_text(o: Dict) -> Dict:
    t = {}
    et = o.get("et", {}).get("headlines")
    if et:
        hi, lo = et["high_f_1_2mm"], et["low_f_1_2mm"]
        def g(d, dv, k):
            return d.get(dv, {}).get(k)
        best = "revH_akf_revh" if "revH_akf_revh" in hi else "revH_akf"
        t["et"] = {"headline": (
            f"Mean over 8-10 Hz and 1-2 mm tremor: ink error none {g(hi, 'none', 'ink'):.0f} um, weighted {g(hi, 'weighted', 'ink'):.0f}, "
            f"pencil+AKF {g(hi, 'pencil_akf', 'ink'):.0f}, Rev H+AKF as shipped {g(hi, 'revH_akf', 'ink'):.0f}, Rev H+AKF re-tuned {g(hi, best, 'ink'):.0f}, "
            f"Rev H oracle {g(hi, 'revH_oracle', 'ink'):.0f}; words read by the app {g(hi, 'none', 'words'):.2f} / {g(hi, best, 'words'):.2f} / "
            f"{g(hi, 'revH_oracle', 'words'):.2f} (none / Rev H re-tuned / oracle). At 4-6 Hz: none {g(lo, 'none', 'ink'):.0f}, "
            f"Rev H re-tuned {g(lo, best, 'ink'):.0f}, oracle {g(lo, 'revH_oracle', 'ink'):.0f} um."),
            "implication": "The +-3 mm nose has the reach for 1-2 mm tremor; the tremor tracker, not the mechanism, limits the benefit, and it barely acts below about 6 Hz"}
        hi_w = g(hi, "weighted", "ink") / max(g(hi, "none", "ink"), 1e-9)
        lo_w = g(lo, "weighted", "ink") / max(g(lo, "none", "ink"), 1e-9)
        t["et"]["weighted_headline"] = (f"+60 g: ink error x{hi_w:.2f} at 8-10 Hz and x{lo_w:.2f} at 4-6 Hz vs the 12 g pen (1-2 mm); "
                                        "see et_sensitivity for the stiff-grip case")
    pdh = o.get("pd", {}).get("headlines")
    if pdh:
        def p(c, k):
            return pdh.get(c, {}).get(k)
        t["pd"] = {"headline": (
            f"x-height end of line (start 5.0 mm): off {p('revH_off', 'xh_end_mm'):.2f}, cue {p('cue', 'xh_end_mm'):.2f}, lines {p('lines', 'xh_end_mm'):.2f}, "
            f"size assist x1.35 {p('size_assist_1.35', 'xh_end_mm'):.2f}, vertical adaptive {p('size_adapt_y1.5', 'xh_end_mm'):.2f} mm; "
            f"tremor in ink off {p('revH_off', 'tremor_in_ink_um'):.0f} vs x1.35 {p('size_assist_1.35', 'tremor_in_ink_um'):.0f} um; "
            f"jerk off {p('revH_off', 'norm_jerk_median'):.0f} vs x1.35 {p('size_assist_1.35', 'norm_jerk_median'):.0f}; letters touching "
            f"{p('revH_off', 'touching_frac'):.0%} vs {p('size_assist_1.35', 'touching_frac'):.0%}"),
            "implication": ("If people respond to a cue as assumed (PDT-19), a vibration cue keeps letters at their start size for "
                            "about 11 % more writing time; lines >= 1 cm halve the shrinkage; a fixed size gain only rescales the "
                            "shrinking letters and enlarges tremor, jerk and (horizontally) crowding; an adaptive vertical gain "
                            "restores the size with little ink cost but hides the deficit from the writer: test it against lines "
                            "and the cue for agency, after-effects and fluency (EXP-HW3)")}
    prh = o.get("practice", {}).get("headlines")
    if prh:
        def q(prof, c, k):
            return prh.get(prof, {}).get(c, {}).get(k)
        t["practice"] = {"headline": (
            f"Dysgraphia-like: ink vs target none {q('dysgraphia', 'none', 'target_err_um'):.0f} um, nose full {q('dysgraphia', 'nose_full', 'target_err_um'):.0f}, "
            f"board full {q('dysgraphia', 'board_full', 'target_err_um'):.0f}; letters read {q('dysgraphia', 'none', 'letters_read_ok'):.2f} / "
            f"{q('dysgraphia', 'nose_full', 'letters_read_ok'):.2f} / {q('dysgraphia', 'board_full', 'letters_read_ok'):.2f}; device share "
            f"{q('dysgraphia', 'nose_full', 'device_share'):.0%} (nose) and {q('dysgraphia', 'board_full', 'device_share'):.0%} (board). "
            f"Dyslexia-like: reversed or wrong letters read as the target: none {q('dyslexia', 'none', 'error_letters_read_as_target'):.2f}, "
            f"nose full {q('dyslexia', 'nose_full', 'error_letters_read_as_target'):.2f}; cue flags {q('dyslexia', 'cue', 'flag_rate_on_errors'):.0%} of errors"),
            "implication": ("Guidance brings the ink closer to the copybook target during guidance, but the device then authors "
                            "20-40 % of the ink motion; full guidance leaves hybrid letters that are read less well, partial nose "
                            "guidance keeps them readable; no guidance turns a reversed or wrong letter into the right one, so for "
                            "dyslexia the app's flagging against a known target carries the benefit. Only unassisted retention "
                            "tests can show learning (HAP-41..44; EXP-HW4)")}
    ccs = o.get("crosscheck", {}).get("summary")
    if ccs:
        parts = []
        for case, d in ccs.items():
            parts.append(f"{case}: oracle P1 {d['P1']['oracle_band_ratio']:.2f} vs HW1 {d['HW1']['oracle_band_ratio']:.2f}; AKF P1 {d['P1']['akf_band_ratio']:.2f} vs HW1 {d['HW1']['akf_band_ratio']:.2f}")
        t["crosscheck"] = {"headline": "; ".join(parts)}
    return t
