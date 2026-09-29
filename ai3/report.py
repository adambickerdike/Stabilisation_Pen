"""Report of study S: ai3.json (with stabpen.provenance), figures with CSV twins, samples.json, tables.md and the
proposed ledger rows.  Every figure is stamped with its evidence status.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import EVIDENCE_CALC, EVIDENCE_SIM, ensure_paths
from . import common as C
from . import evidence as EV
from .rules import RULES, rules_sha256

ensure_paths()
from stabpen import plotstyle as PS  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

S = PS.SERIES
INK, INK2, MUTED, GRID = PS.INK, PS.INK2, PS.MUTED, PS.GRID
MM = 1.0 / 25.4
PT_PER_MM = 72.0 / 25.4
RULE = "#9fb7d8"


def _save(fig, out: Path, name: str, status: str, header: List[str], rows: List[List], note: str = ""):
    # evidence stamp BELOW the axes (the saved image is cropped tight, so it never overlaps a label)
    txt = status.split(" (")[0].upper() + (" | " + note if note else "")
    fig.text(0.995, -0.02, txt, ha="right", va="top", fontsize=6.5, color=MUTED)
    fig.savefig(out / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    C.write_csv(out / f"{name}.csv", header, rows)


def pct(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{100 * x:.0f} %"


# ============================================================================================ figures
def fig_online(on: Dict, cal: Optional[Dict], out: Path):
    PS.apply()
    t = on["test"]
    fr = np.array(t["clean"]["fractions"]) * 100
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    series = [("New writer, clean letters", t["clean"]["top1"], S[0]),
              ("New writer, 1 mm tremor", t["tremor_0.33xh"]["top1"], S[1])]
    if cal:
        series.append(("With the writer's calibration letters", cal["test"]["clean"]["top1"], S[2]))
        series.append(("Calibrated, 1 mm tremor", cal["test"]["tremor_0.33xh"]["top1"], S[3]))
    series.append(("Other writer and tablet (Character Trajectories)", t["chartraj"]["top1"], S[6]))
    rows = []
    for lab, y, c in series:
        y = np.array(y) * 100
        ax.plot(fr, y, color=c, label=lab)
        ax.plot(fr[-1], y[-1], **PS.marker_kw(c))
        rows += [[lab, float(f), float(v)] for f, v in zip(fr, y)]
    ax.set_xlabel("Share of the letter already written (%)")
    ax.set_ylabel("Letters recognised correctly (%)")
    ax.set_ylim(0, 100); ax.set_xlim(8, 102)
    ax.legend(loc="upper left", fontsize=7.5)
    ax.set_title("Recognising a letter while it is written (20 new writers, real handwriting)", fontsize=9.5, loc="left")
    _save(fig, out, "fig_online", EVIDENCE_CALC, ["series", "share_written_pct", "recognised_pct"], rows,
          "UJI Pen Characters v2 test writers; timing ASSUMPTION")


def fig_spell_tradeoff(sp: Dict, out: Path):
    PS.apply()
    curve = sp["test"]["curve"]
    th = sorted(curve, key=float)
    x = [curve[k]["fa_per_100_correct"] for k in th]
    y = [100 * curve[k]["detection_rate"] for k in th]
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.plot(x, y, color=S[0], label="Letters known exactly (test children)")
    s = sp["test"]["score"]
    ax.plot(s["fa_per_100_correct"], 100 * s["detection_rate"], **PS.marker_kw(S[0]))
    ax.annotate(f"chosen on tuning children:\n{100 * s['detection_rate']:.0f} % caught, {s['fa_per_100_correct']:.1f} false alarms",
                (s["fa_per_100_correct"], 100 * s["detection_rate"]), xytext=(10, -28), textcoords="offset points",
                fontsize=7.5, color=INK2)
    rows = [["exact letters", float(a), float(b), float(t)] for a, b, t in zip(x, y, th)]
    k = 1
    for name, blk in (sp.get("with_recognition") or {}).items():
        sc = blk["score"]
        lab = {"writer_independent": "Letters from the recogniser (new writer)",
               "calibrated": "Letters from the recogniser (calibrated)"}.get(name, name)
        ax.plot(sc["fa_per_100_correct"], 100 * sc["detection_rate"], **PS.marker_kw(S[k]), label=lab)
        rows.append([lab, sc["fa_per_100_correct"], 100 * sc["detection_rate"], sp["test"]["theta"]])
        k += 1
    ax.set_xlabel("False alarms per 100 correctly spelled words")
    ax.set_ylabel("Misspelled words caught (%)")
    ax.set_xlim(0, max(12, max(x) * 1.05)); ax.set_ylim(0, 100)
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_title("Catching misspellings while writing: more catches cost more false alarms", fontsize=9.5, loc="left")
    _save(fig, out, "fig_spell_tradeoff", EVIDENCE_CALC, ["series", "fa_per_100_correct", "caught_pct", "theta"], rows,
          "Holbrook children's real misspellings")


def fig_spell_when(sp: Dict, out: Path):
    PS.apply()
    recs = sp["records_test"]
    theta = sp["test"]["theta"]
    from .stage_spell import flag_letter
    from .spell import first_deviation
    cats = {"on the wrong letter": 0, "1 letter later": 0, "2+ letters later": 0, "at the word's end": 0,
            "one word later (context)": 0, "not caught": 0}
    for r in recs:
        for u in r:
            if u["kind"] != "error" or len(u["tokens"]) != 1:
                continue
            t = u["tokens"][0]
            f = flag_letter(t, theta)
            fd = first_deviation(u["target"].lower(), t["written"])
            L = len(t["written"])
            if f is None:
                if t.get("p_err_late", 0) >= theta:
                    cats["one word later (context)"] += 1
                else:
                    cats["not caught"] += 1
            elif f > L:
                cats["at the word's end"] += 1
            elif f - fd <= 0:
                cats["on the wrong letter"] += 1
            elif f - fd == 1:
                cats["1 letter later"] += 1
            else:
                cats["2+ letters later"] += 1
    n = sum(cats.values())
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    labs = list(cats)
    vals = [100 * cats[k] / max(n, 1) for k in labs]
    ax.barh(range(len(labs))[::-1], vals, color=S[0], height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 1, len(labs) - 1 - i, f"{v:.0f} %", va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(labs))[::-1]); ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlabel("Share of misspelled words (%)")
    ax.set_xlim(0, max(vals) * 1.25 + 1)
    ax.set_title(f"When the pen could flag each misspelling ({n} real errors, 11 children)", fontsize=9.5, loc="left")
    _save(fig, out, "fig_spell_when", EVIDENCE_CALC, ["when", "share_pct", "count"], [[k, 100 * cats[k] / max(n, 1), cats[k]] for k in labs])
    return cats


def fig_spell_words(sp: Dict, out: Path, words: Sequence[str] = ("siter", "wach", "frount", "becos", "sometimes")):
    """Letter-by-letter probability that the word is going wrong, for a few real misspellings of the test children."""
    PS.apply()
    ex = sp["examples"]
    theta = sp["test"]["theta"]
    pick = []
    seen = set()
    for e in ex:
        if e["written"] in seen or len(e["written"]) < 4 or len(e["written"]) > 9:
            continue
        if e["flag"] is not None and e["flag"] <= len(e["written"]):
            pick.append(e); seen.add(e["written"])
        if len(pick) >= 4:
            break
    for e in ex:
        if len(pick) >= 6:
            break
        if e["written"] not in seen and e["flag"] is not None and e["flag"] > len(e["written"]) and 3 <= len(e["written"]) <= 8:
            pick.append(e); seen.add(e["written"])
    fig, axes = plt.subplots(1, len(pick), figsize=(1.9 * len(pick), 2.6), sharey=True)
    axes = np.atleast_1d(axes)
    rows = []
    for ax, e in zip(axes, pick):
        w = e["written"]
        p = list(e["p_dev"]) + [e["p_err_end"]]
        labs = list(w) + ["end"]
        cols = [S[1] if (e["flag"] is not None and i + 1 == e["flag"]) else S[0] for i in range(len(p))]
        ax.bar(range(len(p)), [100 * v for v in p], color=cols, width=0.7)
        ax.axhline(100 * theta, color=MUTED, lw=0.8)
        ax.set_xticks(range(len(p))); ax.set_xticklabels(labs, fontsize=8)
        sug = e["suggestions"][0] if e["suggestions"] else "?"
        ax.set_title(f"'{w}' for '{e['target']}'\napp suggests '{sug}'", fontsize=7.5, loc="left")
        ax.set_ylim(0, 105)
        rows += [[w, e["target"], lab, 100 * v] for lab, v in zip(labs, p)]
    axes[0].set_ylabel("P(word going wrong) (%)")
    fig.suptitle("Real misspellings: the pen's estimate after each letter (orange = where it would flag)", fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    _save(fig, out, "fig_spell_words", EVIDENCE_CALC, ["written", "target", "after_letter", "p_going_wrong_pct"], rows,
          f"threshold {theta:g} (rule S2)")


def fig_cues(cu: Dict, out: Path):
    PS.apply()
    from .cues import CUES, LABELS
    t = cu["test"]
    cues = [c for c in CUES]
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.6), sharey=True)
    metrics = [("fixed_on_paper_per_10_errors", "Mistakes fixed on paper\n(per 10 mistakes)"),
               ("false_interventions_per_100_correct", "False cues\n(per 100 correct words)"),
               ("interruptions_per_100_words", "Cues while a word is written\n(per 100 words)"),
               ("extra_time_pct", "Extra writing time (%)")]
    rows = []
    for ax, (m, lab) in zip(axes, metrics):
        v = [t["nominal"][c].get(m, float("nan")) for c in cues]
        lo = [min(t["low"][c].get(m, float("nan")), t["high"][c].get(m, float("nan"))) for c in cues]
        hi = [max(t["low"][c].get(m, float("nan")), t["high"][c].get(m, float("nan"))) for c in cues]
        y = np.arange(len(cues))[::-1]
        ax.barh(y, v, color=S[0], height=0.6)
        ax.errorbar(v, y, xerr=[np.array(v) - np.array(lo), np.array(hi) - np.array(v)], fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
        for yy, vv in zip(y, v):
            ax.text(vv, yy + 0.33, f"{vv:.1f}", fontsize=7, color=INK2, ha="left")
        ax.set_xlabel(lab, fontsize=8.5)
        rows += [[c, m, a, b, d] for c, a, b, d in zip(cues, v, lo, hi)]
    axes[0].set_yticks(np.arange(len(cues))[::-1]); axes[0].set_yticklabels([LABELS[c] for c in cues], fontsize=7.5)
    fig.suptitle("Physical cues for a misspelling (11 children's real errors; writer responses ASSUMED, bars = nominal, whiskers = low/high)",
                 fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    _save(fig, out, "fig_cues", EVIDENCE_SIM, ["cue", "metric", "nominal", "low", "high"], rows,
          "responses: ASSUMPTION anchored in HAP-130, HAP-131, HAP-133")


def fig_predict(pr: Dict, out: Path):
    PS.apply()
    t = pr["test"]
    jids = [k for k in t if k not in ("note_lines",)]
    names = ["NG0 (as used so far)", "NG1x (larger corpus)", "personalised (chosen)"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    ax = axes[0]
    xs = np.arange(3)
    rows = []
    w = 0.25
    for i, nm in enumerate(names):
        vals = [np.mean([t[j][nm][k] for j in jids]) * 100 for k in ("after0_top3", "after1_top3", "after2_top3")]
        ax.bar(xs + (i - 1) * w, vals, width=w - 0.02, color=S[i], label=nm)
        rows += [[nm, k, v] for k, v in zip(("next word", "after 1 letter", "after 2 letters"), vals)]
    ax.axhline(30, color=MUTED, lw=0.8)
    ax.text(2.45, 31, "REQ-APP-003: 30 %", fontsize=7, color=INK2, ha="right")
    ax.set_xticks(xs); ax.set_xticklabels(["next word\n(before any letter)", "after 1 letter", "after 2 letters"], fontsize=8)
    ax.set_ylabel("Right word among 3 offered (%)"); ax.set_ylim(0, 100)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.set_title("Two test journals (the user's own notes)", fontsize=9.5, loc="left")
    ax = axes[1]
    for i, j in enumerate(jids):
        cv = t[j]["history_curve"]
        hx = sorted(cv, key=int)
        ax.plot([max(int(h), 100) for h in hx], [100 * cv[h]["after1_top3"] for h in hx], color=S[i], marker="o",
                markersize=5, label=f"journal {j}: after 1 letter")
        rows += [[f"journal {j}", f"history {h} words", 100 * cv[h]["after1_top3"]] for h in hx]
    ax.set_xscale("log"); ax.set_xlabel("Words of the user's own notes seen (0 plotted at 100)")
    ax.set_ylabel("Right word among 3 (%)"); ax.set_ylim(0, 100)
    ax.legend(fontsize=7.5)
    ax.set_title("How much own text personalisation needs", fontsize=9.5, loc="left")
    fig.tight_layout()
    _save(fig, out, "fig_predict", EVIDENCE_CALC, ["model_or_journal", "position", "top3_pct"], rows,
          "Project Gutenberg journals as stand-in notes")


def _lined(ax, strokes_mm: List[np.ndarray], color=INK, lw_mm=0.35, intended=None, missing=None, xlim=None, ylim=(-4, 7),
           title="", marks=None):
    ax.set_facecolor("white")
    for yl in (0.0, 8.0, -8.0):
        if ylim[0] <= yl <= ylim[1]:
            ax.axhline(yl, color=RULE, lw=0.6, zorder=0)
    if intended is not None:
        for s in intended:
            s = np.asarray(s)
            ax.plot(s[:, 0], s[:, 1], color=MUTED, lw=0.6, ls=(0, (2, 1.5)), zorder=1)
    if missing is not None:
        for s in missing:
            s = np.asarray(s)
            ax.plot(s[:, 0], s[:, 1], color=S[1], lw=2.0, alpha=0.7, zorder=1)
    for s in strokes_mm:
        s = np.asarray(s)
        if len(s) >= 2:
            ax.plot(s[:, 0], s[:, 1], color=color, lw=lw_mm * PT_PER_MM, solid_capstyle="round", zorder=3)
    for m in marks or []:
        ax.plot(m["x"], m["y"], marker=m.get("marker", "v"), color=m.get("color", S[1]), markersize=6, zorder=4)
        if m.get("text"):
            ax.text(m["x"], m["y"] + 0.9, m["text"], fontsize=6.5, color=INK2, ha="center")
    if xlim:
        ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(False)
    if title:
        ax.set_title(title, fontsize=7.5, loc="left", pad=2)


def fig_trace(tr_examples: List[Dict], agg: Dict, out: Path):
    """Why close tracing lowers legibility: examples of guided letters with their undrawn parts."""
    PS.apply()
    n = len(tr_examples)
    fig = plt.figure(figsize=(1.9 * max(n, 1) + 3.8, 3.4))
    gs = fig.add_gridspec(1, n + 2)
    rows = []
    for i, e in enumerate(tr_examples):
        ax = fig.add_subplot(gs[0, i])
        ink = [np.asarray(s) for s in e["ink"]]
        allp = np.vstack([np.vstack(e["target"])] + ink)
        c = allp.mean(0)
        _lined(ax, [s - c for s in ink], intended=None, missing=[np.asarray(s) - c for s in e["missing"]],
               ylim=(-3.2, 3.2), xlim=(-2.6, 2.6), title=f"'{e['char']}' read as '{e['read_as']}'")
        for s in e["target"]:
            s = np.asarray(s) - c
            ax.plot(s[:, 0], s[:, 1], color=S[2], lw=2.4, alpha=0.30, zorder=0)
        rows.append([e["char"], e["read_as"], e["missing"] and 1 or 0, e.get("d_ink_um", float("nan")), e.get("missing_share", float("nan"))])
    ax = fig.add_subplot(gs[0, n:])
    conds = [("none", "no guidance"), ("wheel_path", "heel wheel"), ("nose_nogate", "nose, no gate"), ("wheel_path+nose", "wheel + nose")]
    ys = np.arange(len(conds))[::-1]
    read = [100 * agg[c]["read"] for c, _ in conds]
    stat = [100 * agg[c].get("read_static", float("nan")) for c, _ in conds]
    miss = [100 * agg[c]["missing_mean"] for c, _ in conds]
    ax.barh(ys + 0.27, read, height=0.25, color=S[0], label="read by the app (writing order)")
    ax.barh(ys, stat, height=0.25, color=S[2], label="read as a picture (order-free)")
    ax.barh(ys - 0.27, miss, height=0.25, color=S[1], label="letter left undrawn")
    for y, a, b2, b in zip(ys, read, stat, miss):
        ax.text(a + 1, y + 0.27, f"{a:.0f}", fontsize=7, va="center", color=INK2)
        if math.isfinite(b2):
            ax.text(b2 + 1, y, f"{b2:.0f}", fontsize=7, va="center", color=INK2)
        ax.text(b + 1, y - 0.27, f"{b:.0f}", fontsize=7, va="center", color=INK2)
    ax.set_yticks(ys); ax.set_yticklabels([l for _, l in conds], fontsize=8)
    ax.set_xlim(0, 110); ax.set_xlabel("% of letters", fontsize=7.5)
    ax.legend(fontsize=6.5, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    ax.set_title("Dysgraphia-like learners, 24 runs", fontsize=8.5, loc="left")
    fig.suptitle("Close tracing keeps the ink near the model letter; the app's reader (writing order) loses letters, a reader of the page "
                 "barely does\n(orange = part of the letter left undrawn; green = the model letter)", fontsize=9, x=0.01, ha="left", y=1.08)
    _save(fig, out, "fig_trace_why", EVIDENCE_SIM, ["target_letter", "read_as", "has_missing_part", "d_ink_um", "missing_share"], rows,
          "drive study HW1-D runs, test writers 0-5")


def fig_shape(samples: List[Dict], agg: Dict, out: Path):
    PS.apply()
    pick = {}
    for s in samples:
        pick.setdefault(s["cond"], s)
    order = [c for c in ("tremor_1mm_8Hz", "warp", "tremor_1mm_6Hz") if c in pick]
    fig = plt.figure(figsize=(7.2, 1.55 * 2 * len(order) + 0.6))
    rows = []
    k = 0
    titles = {"tremor_1mm_8Hz": "1 mm tremor at 8 Hz", "warp": "poorly formed letters (warp)", "tremor_1mm_6Hz": "1 mm tremor at 6 Hz"}
    for c in order:
        s = pick[c]
        allx = [p[0] for let in s["intended"] for st in let for p in st]
        x0, x1 = min(allx) - 1.5, max(allx) + 1.5
        yb = min(p[1] for let in s["intended"] for st in let for p in st)
        for j, key in enumerate(("none", "assist")):
            ax = fig.add_subplot(2 * len(order), 1, k + 1)
            strokes = [np.asarray(st) - np.array([0, yb]) for let in s[key] for st in let if len(st) >= 2]
            intended = [np.asarray(st) - np.array([0, yb]) for let in s["intended"] for st in let]
            rd = s["read_none"] if key == "none" else s["read_assist"]
            lab = "without assist" if key == "none" else "with shape assist"
            _lined(ax, strokes, intended=intended, xlim=(x0, x1), ylim=(-4.5, 8.5),
                   title=f"'{s['word']}', {titles[c]}, {lab}: letters read {sum(rd)} of {len(rd)}")
            rows.append([s["word"], c, key, sum(rd), len(rd)])
            k += 1
    fig.suptitle("Real handwriting (UJI test writer) in the pen model at true scale; grey dashes = what the writer meant",
                 fontsize=8.5, x=0.01, ha="left")
    _save(fig, out, "fig_shape_before_after", EVIDENCE_SIM, ["word", "condition", "panel", "letters_read", "letters"], rows,
          "HW1; real letters, simulated hand and tremor")
    # summary
    PS.apply()
    conds = [c for c in ("clean", "tremor_0.3mm_8Hz", "tremor_1mm_8Hz", "tremor_1mm_6Hz", "real_PD_tremor_1mm",
                         "real_ET_tremor_1mm", "warp") if c in agg]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    y = np.arange(len(conds))[::-1]
    a0 = [100 * agg[c]["read_none"] for c in conds]
    a1 = [100 * agg[c]["read_assist"] for c in conds]
    for yy, u, v in zip(y, a0, a1):
        ax.plot([u, v], [yy, yy], color=GRID, lw=2, zorder=1)
    ax.plot(a0, y, **PS.marker_kw(S[0]), label="without assist")
    ax.plot(a1, y, **PS.marker_kw(S[1]), label="with shape assist")
    ax.set_yticks(y); ax.set_yticklabels(conds, fontsize=8)
    ax.set_xlabel("Letters an independent reader recognises (%)")
    ax.legend(fontsize=7.5, loc="lower left")
    ax.set_title("Shape assist on 20 new writers' real letters", fontsize=9.5, loc="left")
    _save(fig, out, "fig_shape_summary", EVIDENCE_SIM, ["condition", "read_none_pct", "read_assist_pct"],
          [[c, u, v] for c, u, v in zip(conds, a0, a1)])


def fig_spell_sample(sample: Dict, out: Path):
    """A real child's misspelling written in real handwriting, with the cue marked and the correction."""
    PS.apply()
    panels = sample["panels"]
    fig = plt.figure(figsize=(7.2, 1.45 * len(panels) + 0.5))
    rows = []
    allx = [p[0] for pnl in panels for st in pnl["strokes"] for p in st]
    x0, x1 = min(allx) - 2, max(allx) + 2
    for i, pnl in enumerate(panels):
        ax = fig.add_subplot(len(panels), 1, i + 1)
        _lined(ax, [np.asarray(s) for s in pnl["strokes"]], xlim=(x0, x1), ylim=(-4.5, 8.5), title=pnl["title"],
               marks=pnl.get("marks"), missing=[np.asarray(s) for s in pnl.get("withheld", [])])
        for tx in pnl.get("texts", []):
            ax.text(tx["x"], tx["y"], tx["text"], fontsize=7, color=tx.get("color", INK2), ha=tx.get("ha", "left"))
        rows.append([pnl["title"], len(pnl["strokes"])])
    fig.suptitle(sample["suptitle"], fontsize=8.5, x=0.01, ha="left")
    _save(fig, out, "fig_spell_sample", EVIDENCE_SIM, ["panel", "strokes"], rows,
          "real misspelling (Holbrook) in real letters (UJI); cue timing from the checker; response ASSUMED")


# ============================================================================================ spell sample builder
def build_spell_sample(sp: Dict, quick: bool) -> Optional[Dict]:
    """Pick a real misspelling the checker flags mid-word, write it with a UJI test writer's real letters (3 mm
    x-height), and draw: as written; the tick on the suspect letter + suggestion; pen lift (withheld part); corrected."""
    from . import data as D, online as O
    from .stage_spell import flag_letter
    recs = sp["records_test"]
    theta, theta_w = sp["test"]["theta"], sp["test"]["theta_w"]
    cand = None
    for r in recs:
        for i, u in enumerate(r):
            if u["kind"] != "error" or len(u["tokens"]) != 1:
                continue
            t = u["tokens"][0]
            f = flag_letter(t, theta)
            tg = u["target"].lower()
            if (f is not None and 3 <= f <= len(t["written"]) and t["suggestions"] and t["suggestions"][0] == tg
                    and 4 <= len(t["written"]) <= 7 and tg.isalpha() and t["written"].isalpha()):
                prev = r[i - 1] if i > 0 else None
                if prev and prev["kind"] == "correct" and prev["tokens"] and prev["tokens"][0]["written"].isalpha():
                    cand = (prev["tokens"][0]["written"], t, tg, f)
                    break
        if cand:
            break
    if not cand:
        return None
    prev_w, tok, target, f = cand
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    by = {}
    for L in letters:
        if O.split_of(L.writer) == "test":
            by.setdefault(L.writer, {})[(L.char, L.rep)] = L
    need = set(prev_w + tok["written"] + target)
    w = next((w for w in sorted(by) if all((c, 1) in by[w] for c in need)), None)
    if w is None:
        return None
    f_mm = O.XH_MM / xh[w]

    def write(text, x0=0.0):
        out, x = [], x0
        spans = []
        for ch in text:
            if ch == " ":
                x += 1.6
                continue
            S_ = [np.asarray(s) * f_mm for s in by[w][(ch, 1)].strokes]
            allp = np.vstack(S_)
            dx = x - allp[:, 0].min()
            S_ = [s + np.array([dx, 0]) for s in S_]
            base = 12.7 * (1.52 if "_UPV_" in w else 1.0) / (1.52 if "_UPV_" in w else 1.0)
            S_ = [s + np.array([0, 12.7 * f_mm]) for s in S_]           # the box's baseline guide at 12.7 mm from its top
            out.append(S_)
            spans.append((ch, np.vstack(S_)[:, 0].min(), np.vstack(S_)[:, 0].max()))
            x = np.vstack(S_)[:, 0].max() + 0.35 * O.XH_MM
        return out, spans, x

    lets_prev, _, xw = write(prev_w)
    wr, spans, xe = write(tok["written"], xw + 1.6)
    # y shift so the baseline sits at 0: estimate from the x-height letters of the writer's written word
    ally = np.vstack([s for L_ in lets_prev + wr for s in L_])[:, 1]
    yb = np.percentile(ally, 20)
    shift = np.array([0.0, -yb])
    flat = lambda lets: [s + shift for L_ in lets for s in L_]
    k = f - 1                                                   # 0-based index of the flagged letter
    cx = 0.5 * (spans[k][1] + spans[k][2])
    top = np.vstack(wr[k])[:, 1].max() + shift[1]
    panels = [{"title": f"As written (a real misspelling from Holbrook's children: '{tok['written']}' for '{target}')",
               "strokes": flat(lets_prev + wr)}]
    panels.append({"title": f"LRA tick on letter {f} ('{tok['written'][k]}'), P(going wrong) = {tok['p_dev'][k]:.2f}; the app shows '{target}'",
                   "strokes": flat(lets_prev + wr[:k + 1]),
                   "marks": [{"x": cx, "y": top + 0.8, "marker": "v", "color": S[1], "text": "tick"}],
                   "texts": [{"x": spans[-1][2] + 2, "y": 1.0, "text": f"app: '{target}'?", "color": S[0]}]})
    # pen lift: the flagged letter is recognised part-way (task 1's median commit point); the rest is not inked
    frac = 0.6
    on = C.load("online_cal", quick) or C.load("online", quick) or {}
    com = (on.get("test") or {}).get("commit") or {}
    if com.get("median_fraction_at_commit"):
        frac = float(com["median_fraction_at_commit"])
    Lk = [s + shift for s in wr[k]]
    lens = [float(np.sum(np.hypot(*np.diff(s, axis=0).T))) for s in Lk]
    tot = sum(lens); keep, cut, acc = [], [], 0.0
    for s, l in zip(Lk, lens):
        if acc + l <= frac * tot:
            keep.append(s)
        elif acc >= frac * tot:
            cut.append(s)
        else:
            seg = np.r_[0.0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
            j = int(np.searchsorted(seg, frac * tot - acc))
            keep.append(s[:max(j, 2)]); cut.append(s[max(j - 1, 0):])
        acc += l
    if tok["p_dev"][k] >= theta_w:
        ttl = f"Pen lift: letter {f} is recognised at {100 * frac:.0f} % of its path and withheld (orange = not inked); the app shows '{target}'"
    else:
        ttl = (f"Pen lift (for illustration: this word's P = {tok['p_dev'][k]:.2f} is below the stricter lift threshold "
               f"{theta_w:g}, so the pen would NOT lift here)")
    panels.append({"title": ttl, "strokes": flat(lets_prev + wr[:k]) + keep, "withheld": cut})
    # after the cue: permanent ink stays; the writer crosses out the wrong letters (first wrong letter to the flagged
    # one) and writes the rest of the word right after them; the transcript reads the target
    from .spell import first_deviation
    fd = max(1, min(first_deviation(target, tok["written"]), f))
    x_end = spans[f - 1][2] + 0.35 * O.XH_MM
    rest, _, _ = write(target[fd - 1:], x_end)
    y_mid = 0.5 * O.XH_MM
    strike = np.array([[spans[fd - 1][1] - 0.3, y_mid - shift[1] - 0.2], [spans[f - 1][2] + 0.3, y_mid - shift[1] + 0.3]])
    panels.append({"title": (f"After the tick: the writer crosses out '{tok['written'][fd - 1:f]}' and writes '{target[fd - 1:]}' after it "
                             f"(response ASSUMED); the pen never changes ink; the transcript reads '{target}'"),
                   "strokes": flat(lets_prev + wr[:f] + rest) + [strike + shift]})
    return {"panels": panels, "writer": w, "written": tok["written"], "target": target, "flag_letter": f,
            "suptitle": "A misspelling caught while writing, in real handwriting at true scale (3 mm x-height, 8 mm ruled lines)"}


# ============================================================================================ tracing examples
def trace_examples(quick: bool, n: int = 4) -> List[Dict]:
    """Re-run one drive case (writer 0, seed 200, dysgraphia) to draw letters newly misread under close tracing."""
    from . import tracing_diag as TD
    from scipy.spatial import cKDTree
    res = TD.run_case(0, 200, "dysgraphia", conds=["none", "wheel_path+nose"], keep=True)
    su = res["_su"]
    r = res["_runs"]["wheel_path+nose"]
    out = []
    for k, (a, b) in enumerate(zip(res["conds"]["none"]["letters"], res["conds"]["wheel_path+nose"]["letters"])):
        if a.get("read_ok") and not b.get("read_ok") and b.get("missing", 0) > 0.1:
            L = su["wr"].letters[k]
            mw = (r.t >= L.t0 - 0.01) & (r.t <= L.t1 + 0.01)
            m = mw & (r.contact > 0.5)
            ink = r.ink[m] * 1e3
            T, sid, u, _ = TD._dense(su["tl"][k].strokes)
            d, _ = cKDTree(ink / 1e3).query(T)
            miss = T[d > 0.3e-3] * 1e3
            runs = []
            if len(miss):
                idx = np.flatnonzero(d > 0.3e-3)
                br = np.flatnonzero(np.diff(idx) > 1)
                runs = [T[idx[s0:s1 + 1]] * 1e3 for s0, s1 in zip(np.r_[0, br + 1], np.r_[br, len(idx) - 1]) if s1 > s0]
            from aiguide.metrics import split_strokes
            out.append({"char": su["targets"][k], "read_as": b["read_as"],
                        "ink": [s * 1e3 for s in split_strokes(r.ink[mw], r.contact[mw] > 0.5)],
                        "target": [np.asarray(s) * 1e3 for s in su["tl"][k].strokes], "missing": runs,
                        "d_ink_um": b["d_ink_um"], "missing_share": b["missing"]})
        if len(out) >= n:
            break
    return out


# ============================================================================================ markdown tables
def fig_words(wd: Dict, out: Path):
    """CER and WER of word recognition: new writer vs calibrated, without and with the language model."""
    PS.apply()
    b = wd["W1"]["beta_w"]
    combos = [("independent|beta=0", "new writer\nno LM"), (f"independent|beta={b:g}", "new writer\nwith LM"),
              ("calibrated|beta=0", "calibrated\nno LM"), (f"calibrated|beta={b:g}", "calibrated\nwith LM")]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.8))
    rows = []
    for ax, key, title in ((axs[0], "cer", "Letters wrong (CER)"), (axs[1], "wer", "Words wrong (WER)")):
        x = np.arange(len(combos))
        for j, (g, col, lab) in enumerate((("normal", S[0], "normal spacing"), ("tight", S[1], "tight spacing"))):
            tw = wd["test_words"].get(g, {})
            v = [100 * tw.get(k, {}).get(key, float("nan")) for k, _ in combos]
            ax.bar(x + (j - 0.5) * 0.36, v, width=0.34, color=col, label=lab)
            for xi, vi in zip(x, v):
                if math.isfinite(vi):
                    ax.text(xi + (j - 0.5) * 0.36, vi + 0.8, f"{vi:.0f}", ha="center", fontsize=6.5, color=INK2)
            rows += [[g, k, key, tw.get(k, {}).get(key)] for k, _ in combos]
        ax.set_xticks(x); ax.set_xticklabels([l for _, l in combos], fontsize=7)
        ax.set_title(title, fontsize=8.5, loc="left"); ax.set_ylabel("%", fontsize=7.5)
        top = max([r[3] for r in rows if r[2] == key and r[3] is not None] + [0.01]) * 100
        ax.set_ylim(0, top * 1.35)
    axs[1].legend(fontsize=6.5, loc="upper center", ncol=2, frameon=False)
    fig.suptitle(f"Word recognition on {wd.get('test_writers', 20)} held-out writers (real letters; calibration from their other session)",
                 fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    _save(fig, out, "fig_words", EVIDENCE_SIM, ["spacing", "recogniser", "metric", "value"], rows, "UJI test writers, Tatoeba test sentences")


def fig_calibration(wd: Dict, out: Path):
    """Reliability of P(misspelled) before and after temperature scaling (test children)."""
    PS.apply()
    panels = [("as planned (W2)", (wd.get("spelling") or {}).get("calibrated", {}), "temperature scaling"),
              ("post hoc (W5)", (wd.get("spelling_v2") or {}).get("calibrated", {}), "Platt scaling")]
    panels = [p_ for p_ in panels if p_[1].get("reliability_test")]
    if not panels:
        return
    fig, axs = plt.subplots(1, len(panels), figsize=(3.5 * len(panels), 3.3), squeeze=False)
    rows = []
    for ax, (title, blk, how) in zip(axs[0], panels):
        rel = blk["reliability_test"]
        ax.plot([0, 1], [0, 1], color=GRID, lw=1)
        for key, col, lab in (("raw", S[1], "combined score, raw"), ("calibrated", S[0], f"after {how}")):
            bins = rel[key]["bins"]
            x = [b_["mean_p"] for b_ in bins]; y = [b_["freq"] for b_ in bins]; n = [b_["n"] for b_ in bins]
            ax.plot(x, y, "-o", color=col, ms=3, lw=1.3, label=f"{lab} (ECE {rel[key]['ece']:.3f})")
            rows += [[title, key, a, c, d] for a, c, d in zip(x, y, n)]
        ax.set_xlabel("predicted P(misspelled)", fontsize=7.5); ax.set_ylabel("share actually misspelled", fontsize=7.5)
        ax.legend(fontsize=6.0, loc="upper left"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(f"{title}: {rel['n']} test words", fontsize=8.5, loc="left")
    fig.tight_layout()
    _save(fig, out, "fig_calibration", EVIDENCE_SIM, ["design", "series", "mean_predicted", "observed_share", "n"], rows,
          "calibrated recogniser; real letters of held-out writers as recognised strokes")


def fig_plan(pl: Dict, out: Path):
    """Accepted-word completion: share written in full vs the nib's reach, per hand behaviour."""
    PS.apply()
    from .complete_plan import BEHAVIOURS, RADII_MM
    T = pl["table"]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.8))
    names = {"steady": "hand advances as usual", "slow": "hand at half speed", "fast": "hand runs ahead (x1.8)",
             "pause": "hand pauses 3 s", "still": "hand held still"}
    rows = []
    for i, beh in enumerate(BEHAVIOURS):
        v = [100 * T.get(f"{beh}|{R:g}|letter_admission", {}).get("completed_share", float("nan")) for R in RADII_MM]
        axs[0].plot(RADII_MM, v, "-o", color=S[i % len(S)], ms=3, lw=1.3, label=names[beh])
        rows += [[beh, R, "letter_admission", "completed_pct", x] for R, x in zip(RADII_MM, v)]
    axs[0].set_xlabel("nib reach (+- mm)", fontsize=7.5); axs[0].set_ylabel("accepted words written in full (%)", fontsize=7.5)
    axs[0].legend(fontsize=6.2, loc="upper left"); axs[0].set_ylim(-3, 103)
    x = np.arange(len(BEHAVIOURS))
    for j, (pol, col, lab) in enumerate((("pointwise", S[1], "point by point"), ("letter_admission", S[0], "whole letter must fit"))):
        v = [T.get(f"{beh}|6|{pol}", {}).get("partial_letters_per_100", float("nan")) for beh in BEHAVIOURS]
        axs[1].bar(x + (j - 0.5) * 0.36, v, width=0.34, color=col, label=lab)
        rows += [[beh, 6, pol, "half_letters_per_100", vv] for beh, vv in zip(BEHAVIOURS, v)]
    axs[1].set_xticks(x); axs[1].set_xticklabels([b_ for b_ in BEHAVIOURS], fontsize=7)
    axs[1].set_ylabel("half-written letters per 100 words", fontsize=7.5); axs[1].legend(fontsize=6.5)
    axs[1].set_title("+-6 mm reach", fontsize=8.5, loc="left")
    fig.suptitle(f"Writing an accepted word: {pl['completions']} completions in the writers' own letters, 3 mm x-height",
                 fontsize=9, x=0.01, ha="left")
    fig.tight_layout()
    _save(fig, out, "fig_plan", EVIDENCE_SIM, ["hand", "reach_mm", "policy", "metric", "value"], rows, "kinematics only; hand advance assumed")


def _p(x, d=0):
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{100 * x:.{d}f} %"


def tables_md(res: Dict) -> str:
    """The detailed tables of docs/spelling_and_clarity.md, generated from the caches (no hand transcription)."""
    L: List[str] = []
    on, cal = res.get("online"), res.get("online_cal")
    if on:
        t = on["test"]
        fr = t["clean"]["fractions"]
        idx = [fr.index(f) for f in (0.3, 0.5, 0.7, 1.0)]
        L += ["### T1. Letters recognised while being written (20 UJI test writers, 1,040 letters; CALC)", "",
              "| Recogniser and letters | 30 % written | 50 % | 70 % | whole letter | top-3, whole letter |", "|---|---|---|---|---|---|"]
        rows = [("New writer, clean", t["clean"]), ("New writer, 0.3 mm tremor", t.get("tremor_0.1xh")),
                ("New writer, 1 mm tremor", t.get("tremor_0.33xh"))]
        if cal:
            rows += [("Calibrated (writer's own letters), clean", cal["test"]["clean"]),
                     ("Calibrated, 1 mm tremor", cal["test"]["tremor_0.33xh"])]
        rows += [("Other writer and tablet (Character Trajectories, 2,858 letters)", t["chartraj"])]
        for name, r in rows:
            if not r:
                continue
            top3 = r.get("top3", [float("nan")] * len(fr))
            L.append(f"| {name} | " + " | ".join(_p(r["top1"][i]) for i in idx) + f" | {_p(top3[-1])} |")
        c = t["commit"]
        L += ["", f"Commit rule (O2, tau {t['tau']:g}): {_p(c['committed_share'])} of letters committed before or at their end, "
              f"commits right {_p(c['commit_accuracy'], 1)}, median {_p(c['median_fraction_at_commit'])} of the letter written at commit."]
        if cal:
            cc = cal["test"]["commit"]
            L.append(f"Calibrated: {_p(cc['committed_share'])} committed, right {_p(cc['commit_accuracy'], 1)}, median "
                     f"{_p(cc['median_fraction_at_commit'])} written; committed before the letter's end: {_p(cc['committed_before_end_share'])}.")
        ctx = t.get("context", {})
        if ctx:
            b = f"{t['beta']:g}"
            L.append(f"With the text predictor's next-letter prior (beta {t['beta']:g}, rule O3), letters in Tatoeba test sentences: "
                     f"half letter {_p(ctx['0'].get('top1_0.5'))} -> {_p(ctx.get(b, {}).get('top1_0.5'))}, whole letter "
                     f"{_p(ctx['0'].get('top1_1'))} -> {_p(ctx.get(b, {}).get('top1_1'))} ({ctx['0']['n']} letters).")
        co = t["cost"]
        L.append(f"Size and speed: {co['n_params']:,} parameters ({co['kB_int8']:.0f} kB int8, {co['kB_float32']:.0f} kB float32); "
                 f"{co['macs_per_point']:,} multiply-accumulates per point; {co['ms_per_point_this_cpu']:.2f} ms per point on this "
                 f"container's CPU (one thread), {co['letter_ms_this_cpu']:.1f} ms for a median letter; "
                 f"{co['mcu_ms_per_point_int8']:.2f} ms per point on a 128 MHz Cortex-M33 (int8, CALC).")
        L.append("")
        v = t.get("variants_for_information", {})
        if v:
            L += ["Variants on the test writers, for information only (the choice was made on tuning writers, rule O1): whole-letter "
                  "top-1 clean / 1 mm tremor: " + "; ".join(f"{k} {_p(x['clean'][-1])} / {_p(x['tremor_0.33xh'][-1])}" for k, x in v.items()), ""]
    sp = res.get("spell")
    if sp:
        s = sp["test"]["score"]
        L += ["### T2. The spelling checker on 11 test children's real writing (Holbrook; CALC)", "",
              "| Measure | Value |", "|---|---|",
              f"| Misspelled words (scored) | {s['errors']} |", f"| Correctly spelled words | {s['correct_words']} |",
              f"| Caught (flag while writing or at the word's end) | {_p(s['detection_rate'])} |",
              f"| False alarms per 100 correct words | {s['fa_per_100_correct']:.1f} |",
              f"| Caught non-word errors | {s['nonword']['detected']} of {s['nonword']['n']} |",
              f"| Caught real-word errors | {s['realword']['detected']} of {s['realword']['n']} |",
              f"| Flag on the first wrong letter / one letter later / two or more later | {_p(s['flag_minus_first_wrong_letter']['same_letter'])} / {_p(s['flag_minus_first_wrong_letter']['one_later'])} / {_p(s['flag_minus_first_wrong_letter']['two_or_more_later'])} |",
              f"| Right word first / in the top 3 (caught single words) | {_p(s['suggestion_top1'])} / {_p(s['suggestion_top3'])} |"]
        r2 = sp["test"]["score_with_right_context"]
        L.append(f"| With the next word as context (one word later) | caught {_p(r2['detection_rate'])}, {r2['fa_per_100_correct']:.1f} false alarms per 100 |")
        w = sp["test"]["score_prefix_only_withhold"]
        L.append(f"| Pen-lift threshold (mid-word only, rule S3) | caught {_p(w['detection_rate'])}, {w['fa_per_100_correct']:.2f} false lifts per 100 |")
        e = sp["test"]["earliest_possible"]
        L += ["", f"Earliest letter (single-word errors, n = {e['n']}): the first wrong letter is letter {e['first_wrong_letter_median']:.0f} "
              f"(median; {_p(e['first_wrong_letter_share_of_word_median'])} of the word); {_p(e['error_at_word_end_share'])} of errors only show at "
              f"the word's end (the child wrote the start of the right word); the written letters stop being the start of ANY dictionary word "
              f"at letter {e['nonword_point_median']:.0f} (median), and {_p(e['never_nonword_share'])} never do (real-word errors).", ""]
        L += [f"Rules: alpha {sp['alpha']:.3f} (tuning children's error share); p_oov {sp['S2'].get('p_oov')}; theta {sp['test']['theta']:g}; "
              f"theta_w {sp['test']['theta_w']:g}. Lexicon {sp['lexicon_words']:,} words, covering {_p(sp['lexicon_coverage_of_intended_words'], 1)} "
              f"of the children's intended words; {sp['ms_per_letter']:.1f} ms per letter on this CPU.", ""]
        bb = sp.get("birkbeck_in_text")
        if bb:
            L.append(f"Birkbeck test misspellings placed in CC0 sentences ({bb['info']['words']} words, {_p(bb['info']['word_error_rate'])} misspelled): "
                     f"caught {_p(bb['score']['detection_rate'])}, {bb['score']['fa_per_100_correct']:.1f} false alarms per 100, right word in the top 3 "
                     f"{_p(bb['score']['suggestion_top3'])}.")
        for name, blk in (sp.get("with_recognition") or {}).items():
            sc = blk["score"]
            L.append(f"Letters read by the recogniser ({name}, {_p(blk['letter_error_rate'])} letter errors): caught {_p(sc['detection_rate'])}, "
                     f"{sc['fa_per_100_correct']:.1f} false alarms per 100 correct words ({sc['errors']} errors, {sc['correct_words']} correct words).")
        L += ["", "| Test child | Words misspelled | Caught | False alarms per 100 |", "|---|---|---|---|"]
        for ch_, v in sp["test"]["per_child"].items():
            L.append(f"| {ch_} | {_p(v['error_rate'])} | {_p(v['detection_rate'])} | {v['fa_per_100_correct']:.1f} |")
        L.append("")
    cu = res.get("cues")
    if cu:
        from .cues import CUES, LABELS
        L += ["### T3. Physical cues (11 test children's real errors; writer responses ASSUMED; SIM)", "",
              "| Cue | Mistakes caught per 10 | Fixed on paper per 10 (low - high) | False cues per 100 correct | Correct words made wrong per 100 | Extra time | Cues felt mid-word per 100 words | Suggestion lists read per 100 words | Letters drawn by the pen per 100 words | Wrong-letter fragments per 100 words |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for c in CUES:
            n_, lo_, hi_ = cu["test"]["nominal"][c], cu["test"]["low"][c], cu["test"]["high"][c]
            L.append(f"| {LABELS[c]} | {n_['caught_per_10_errors']:.1f} | {n_['fixed_on_paper_per_10_errors']:.1f} ({lo_['fixed_on_paper_per_10_errors']:.1f} - {hi_['fixed_on_paper_per_10_errors']:.1f}) | "
                     f"{n_['false_interventions_per_100_correct']:.1f} | {n_['correct_words_made_wrong_per_100_correct']:.2f} | +{n_['extra_time_pct']:.0f} % | "
                     f"{n_.get('interruptions_per_100_words', float('nan')):.1f} | {n_.get('suggestion_lists_read_per_100_words', float('nan')):.1f} | "
                     f"{n_['letters_drawn_by_pen_per_100_words']:.1f} | {n_['wrong_letter_fragments_per_100_words']:.1f} |")
        L += ["", f"Rule S4 (tuning children): recommended **{cu['S4']['recommended']}** (fragile: {cu['S4']['fragile']}); admissible: "
              f"{', '.join(cu['S4']['admissible'])}. Rule S5: theta_b {cu['S5']['theta_b']}. Recogniser commit before a letter's end: "
              f"{_p(cu['commit']['p_before_end'])}. Next letter within the nose's reach: {_p(cu['reach']['share_within_reach'])} "
              f"(median farthest point {cu['reach']['max_distance_mm_median']:.1f} mm).", ""]
        for name, blk in (cu.get("test_with_recognition") or {}).items():
            L.append(f"With letters from the recogniser ({name}), nominal responses: " + "; ".join(
                f"{c} fixed {blk[c]['fixed_on_paper_per_10_errors']:.1f}/10, false cues {blk[c]['false_interventions_per_100_correct']:.1f}/100"
                for c in ("tick_after", "tick_lift", "withhold")))
        L.append("")
    pr = res.get("predict")
    if pr:
        t = pr["test"]
        js = [k for k in t if k != "note_lines"]
        L += ["### T4. Text prediction on the user's own notes (test journals; CALC)", "",
              "| Journal | Model | Next word top-1 / top-3 | After 1 letter top-1 / top-3 | After 2 letters top-1 / top-3 | Letters saved (top-1 / top-3 list) | p95 latency |",
              "|---|---|---|---|---|---|---|"]
        for j in js:
            for nm in ("NG0 (as used so far)", "NG1x (larger corpus)", "personalised (chosen)"):
                r = t[j][nm]
                L.append(f"| {j} | {nm} | {_p(r['after0_top1'])} / {_p(r['after0_top3'])} | {_p(r['after1_top1'])} / {_p(r['after1_top3'])} | "
                         f"{_p(r['after2_top1'])} / {_p(r['after2_top3'])} | {_p(r['letters_saved_top1'])} / {_p(r['letters_saved_top3'])} | {r['latency_ms_p95']:.1f} ms |")
        L += ["", f"Rule P1 chose {pr['P1']['chosen']}; rule P2 chose p_offer {pr['P2']['p_offer']}.", ""]
        for j in js:
            nm = "personalised (chosen)"
            r = t[j][nm]
            L.append(f"Journal {j}, autowrite completion on request (offers at p >= {pr['P2']['p_offer']}): "
                     f"{r['time_autowrite_normal']['seconds_saved_per_100_letters']:+.1f} s per 100 letters for a typical writer "
                     f"({_p(r['time_autowrite_normal']['share_of_writing_time'])} of writing time), "
                     f"{r['time_autowrite_slow_writer']['seconds_saved_per_100_letters']:+.1f} s ({_p(r['time_autowrite_slow_writer']['share_of_writing_time'])}) for a slow writer.")
        L.append("")
    tr = res.get("trace")
    if tr:
        L += ["### T5. Why close tracing lowers legibility (drive study's runs, 6 test writers x 4 seeds; SIM)", "",
              "| Learners | Condition | Ink to target | Letters read by the app (writing order) | Read as a picture (order-free) | Share of each letter left undrawn (> 1 mm from any ink) | Ink running backwards along the letter | Newly misread by the app / by both readers | ...app reads them again if drawn in the letter's own order / if the missing part is added |",
              "|---|---|---|---|---|---|---|---|---|"]
        for prof, agg in tr["aggregate"].items():
            for cond, a in agg.items():
                L.append(f"| {prof} | {cond} | {a['d_ink_um_mean']:.0f} um | {_p(a['read'])} | {_p(a.get('read_static'))} | {_p(a['missing_mean'])} | "
                         f"{_p(a['backtrack_mean'])} | {a.get('newly_misread', 0)} / {a.get('newly_misread_both_readers', 0)} | "
                         f"{_p(a.get('newly_misread_covered_only_recovers'))} / {_p(a.get('newly_misread_filled_recovers'))} |")
        L.append("")
    sh = res.get("shape")
    if sh:
        ag = sh["test"]["aggregate"]
        L += ["### T6. Shape assist on 20 new writers' real letters in HW1 (SIM)", "",
              "| Writer's hand | Letters read without / with assist | Words fully read without / with | Ink moved (mean / worst word) | Device share of ink motion | Ink to intended letters without / with | Letters helped / harmed |",
              "|---|---|---|---|---|---|---|"]
        for c, a in ag.items():
            if c == "warp_close_tracing":
                continue
            L.append(f"| {c} | {_p(a['read_none'])} / {_p(a['read_assist'])} | {_p(a['words_all_letters_read_none'])} / {_p(a['words_all_letters_read_assist'])} | "
                     f"{a['moved_um_mean']:.0f} / {a['moved_um_worst_word']:.0f} um | {_p(a['device_share_mean'])} | {a['ink_err_none_um']:.0f} / {a['ink_err_assist_um']:.0f} um | "
                     f"{a['helped_letters']} / {a['harm_letters']} |")
        if "warp_close_tracing" in ag:
            a = ag["warp_close_tracing"]
            L.append(f"\nClose tracing (nearest-point, full gain, no gate) on the same poorly formed words: letters read {_p(a['read_none'])} -> {_p(a['read_trace'])}.")
        L.append(f"\nRule A1 chose {sh['test']['cfg']}. Judge (offline reader) accuracy on clean test letters: {_p(sh['judge'].get('acc_test_clean'))}.")
        oc = res.get("ocr")
        if oc:
            L.append(f"\nSpot check with study R's word reader ({oc['reader']}, literal, no lexicon; post hoc) on {len(oc['rows'])} sample words: "
                     f"read {_p(oc['all']['read_intended'])} of the writers' clean letters, {_p(oc['all']['read_none'])} without the assist, "
                     f"{_p(oc['all']['read_assist'])} with it. By condition (without / with): " +
                     "; ".join(f"{c} {_p(v['read_none'])} / {_p(v['read_assist'])} ({v['words']} words)" for c, v in oc["aggregate"].items()) + ".")
        cc = sh["test"].get("clean_copy", {})
        if cc:
            L += ["", "| Writer's hand | App clean copy: letters read raw / clean copy / clean copy v2 | Words read raw / clean copy / v2 | Letters re-drawn (synthetic) | ...of which the wrong letter |",
                  "|---|---|---|---|---|"]
            for c, v in cc.items():
                L.append(f"| {c} | {_p(v['letters_read_raw'])} / {_p(v['letters_read_cleancopy'])} / {_p(v['letters_read_cleancopy_v2'])} | "
                         f"{_p(v['words_read_raw'])} / {_p(v['words_read_cleancopy'])} / {_p(v['words_read_cleancopy_v2'])} | {_p(v['synthetic_share'])} | {v['synthetic_wrong_letters']} |")
            L.append(f"\nRule A2 (tuning writers): clean copy v2 words gain {sh['A2']['words_gain_v2']:+.3f}; adopted: {sh['A2']['adopted']}.")
    wd = res.get("words")
    if wd and wd.get("test_words"):
        b = wd["W1"]["beta_w"]
        L += ["### T7. Word recognition: character and word error rates (20 held-out UJI writers; SIM on real letters)", "",
              "| Recogniser | Spacing | CER no LM | CER with LM | WER no LM | WER with LM |", "|---|---|---|---|---|---|"]
        for g, tw in wd["test_words"].items():
            for rc, name in (("independent", "new writer (writer-disjoint)"), ("calibrated", "calibrated on the other session (session-disjoint)")):
                a0, a1 = tw.get(f"{rc}|beta=0", {}), tw.get(f"{rc}|beta={b:g}", {})
                L.append(f"| {name} | {g} | {_p(a0.get('cer'), 1)} | {_p(a1.get('cer'), 1)} | {_p(a0.get('wer'))} | {_p(a1.get('wer'))} |")
            L.append(f"| segmentation errors per letter | {g} | {_p(tw.get('segmentation_error_per_letter'), 1)} | | | |")
        L += ["", f"Rule W1 (tuning writers): language weight beta_w = {b:g}. Words: Tatoeba test sentences written with each writer's letters "
              f"from one session; spacing N(0.25, 0.12) x-height (normal) and N(0.08, 0.12) (tight), ASSUMPTION.", ""]
    if wd and wd.get("spelling"):
        L += ["### T8. Spelling help with the pen's own reading of the letters (the review's score; 11 test children; SIM)", "",
              "| Recogniser | Caught | False alarms per 100 correct | Suggestion shown / right when shown | Misread words put right / right readings changed | Unusual correct words kept | ECE raw / calibrated | Auto mode: errors fixed / correct words changed per 100 |",
              "|---|---|---|---|---|---|---|---|"]
        rows_ = [("as planned (W2, temperature)", n_, b_) for n_, b_ in wd["spelling"].items()]
        rows_ += [("post hoc (W5: + lexicon readings, Platt)", n_, b_) for n_, b_ in (wd.get("spelling_v2") or {}).items()]
        for tag, name, blk in rows_:
            if not isinstance(blk, dict) or "test" not in blk:
                continue
            t, rel = blk["test"], blk.get("reliability_test", {})
            rk = "W2" if "W2" in blk else "W5"
            cal_ = blk[rk]["T"]
            cal_s = (f"Platt a {cal_[1]:.2f}, b {cal_[2]:.2f}" if isinstance(cal_, (list, tuple)) else f"T {cal_:.2f}")
            L.append(f"| {name}, {tag} (lambda_r {blk[rk]['lambda_r']}, {cal_s}, theta_c {blk[rk]['theta_c']}, p_s {blk['W3']['p_s']}) | "
                     f"{_p(t['detection_rate'])} | {t['fa_per_100_correct']:.1f} | {_p(t['suggestion_shown_share_of_detected'])} / {_p(t['suggestion_right_when_shown'])} | "
                     f"{_p(t['recognition']['misread_fixed_share'])} / {_p(t['recognition']['right_reading_changed_share'], 1)} | "
                     f"{_p(t['unusual_correct_words']['kept_unflagged_share'])} | {rel.get('raw', {}).get('ece', float('nan')):.3f} / {rel.get('calibrated', {}).get('ece', float('nan')):.3f} | "
                     f"{t['auto_mode']['errors_fixed_per_100_errors']:.1f} / {t['auto_mode']['correct_words_changed_per_100_correct']:.2f} |")
        ex = wd["spelling"].get("exact_letters_same_units")
        if ex:
            L.append(f"| letters known exactly, same words (task 2's checker) | {_p(ex['detection_rate'])} | {ex['fa_per_100_correct']:.1f} | "
                     f"right word first {_p(ex['suggestion_top1'])} | n/a | n/a | n/a | n/a |")
        pa = wd.get("pool_letter_accuracy", {}).get("test", {})
        L += ["", f"Letters seen through real held-out letters (test pool): read right {_p(pa.get('independent'))} (new writer), "
              f"{_p(pa.get('calibrated'))} (calibrated).", ""]
    pl = res.get("plan")
    if pl and pl.get("table"):
        from .complete_plan import BEHAVIOURS, RADII_MM
        L += ["### T9. Writing an accepted word with the pen (kinematic planner, rule C1; SIM)", "",
              "| Hand | " + " | ".join(f"+-{R:g} mm" for R in RADII_MM) + " | half letters per 100 (point by point / whole letter) at +-6 mm | time vs own writing |",
              "|---|" + "---|" * len(RADII_MM) + "---|---|"]
        for beh in BEHAVIOURS:
            T = pl["table"]
            cells = [_p(T.get(f"{beh}|{R:g}|letter_admission", {}).get("completed_share")) for R in RADII_MM]
            pw, la = T.get(f"{beh}|6|pointwise", {}), T.get(f"{beh}|6|letter_admission", {})
            L.append(f"| {beh} | " + " | ".join(cells) + f" | {pw.get('partial_letters_per_100', float('nan')):.0f} / {la.get('partial_letters_per_100', float('nan')):.0f} | "
                     f"{la.get('time_ratio_median_done', float('nan')):.2f} |")
        L += ["", f"{pl['completions']} completions (the rest of words of 5+ letters after 40-60 % written); rest-of-word extent median "
              f"{pl['extent_mm_median']:.1f} mm (90th percentile {pl['extent_mm_p90']:.1f} mm); the hand's usual advance {pl['v_hand_mm_s_median']:.1f} mm/s.", ""]
    return "\n".join(L) + "\n"


# ============================================================================================ the report
def load_all(quick: bool) -> Dict:
    res = {}
    for k, name in (("online", "online"), ("online_cal", "online_cal"), ("spell", "spell_NG1x"), ("cues", "cues"),
                    ("predict", "predict"), ("trace", "trace"), ("shape", "shape"), ("lm", "lm"), ("words", "words"),
                    ("plan", "plan"), ("ocr", "ocr")):
        v = C.load(name, quick)
        if v is not None:
            res[k] = v
    return res


def run(quick: bool) -> Dict:
    out = C.out_dir(quick)
    res = load_all(quick)
    summary: Dict = {"rules_sha256": rules_sha256(), "rules": RULES}
    if "online" in res:
        fig_online(res["online"], res.get("online_cal"), out)
    if "spell" in res:
        fig_spell_tradeoff(res["spell"], out)
        summary["spell_when"] = fig_spell_when(res["spell"], out)
        fig_spell_words(res["spell"], out)
        smp = build_spell_sample(res["spell"], quick)
        if smp:
            fig_spell_sample(smp, out)
            summary["spell_sample"] = {k: v for k, v in smp.items() if k != "panels"}
    if "cues" in res:
        fig_cues(res["cues"], out)
    if "predict" in res:
        fig_predict(res["predict"], out)
    if "trace" in res:
        agg = res["trace"]["aggregate"].get("dysgraphia", {})
        try:
            ex = trace_examples(quick)
        except Exception as e:                                   # the drive study's rules file is needed
            C.log(f"[report] trace examples skipped: {e!r}")
            ex = []
        if agg:
            fig_trace(ex, agg, out)
    if "shape" in res:
        fig_shape(res["shape"].get("samples", []), res["shape"]["test"]["aggregate"], out)
    for name, fn in (("words", fig_words), ("words", fig_calibration), ("plan", fig_plan)):
        if name in res:
            try:
                fn(res[name], out)
            except Exception as e:                           # a figure must never stop the report
                C.log(f"[report] {fn.__name__}: {e!r}")
    # ai3.json: everything except bulky per-token records
    slim = {}
    for k, v in res.items():
        if isinstance(v, dict):
            slim[k] = {kk: vv for kk, vv in v.items() if not kk.startswith("records") and kk not in ("examples", "cases")}
            if k == "shape":
                slim[k]["test"] = {kk: vv for kk, vv in v["test"].items() if kk != "rows"}
                slim[k].pop("samples", None)
            if k == "trace":
                slim[k]["cases_n"] = len(v.get("cases", []))
            if k == "plan":
                slim[k].pop("rows", None)
    slim["summary"] = summary
    C.write_result("ai3.json", slim, quick, EVIDENCE_SIM + " / " + EVIDENCE_CALC)
    # samples.json (before/after ink of the shape assist and the spell sample)
    samples = {"schema": "ai3 samples: mm, lists of strokes per letter", "shape": (res.get("shape") or {}).get("samples", [])}
    if "spell_sample" in summary and "spell" in res:
        smp = build_spell_sample(res["spell"], quick)
        samples["spell"] = {"panels": [{"title": p["title"], "strokes": [np.round(np.asarray(s), 3).tolist() for s in p["strokes"]],
                                        "withheld": [np.round(np.asarray(s), 3).tolist() for s in p.get("withheld", [])]}
                                       for p in smp["panels"]]}
    (out / "samples.json").write_text(json.dumps(samples, default=C.jdefault))
    try:
        (out / "tables.md").write_text(tables_md(res))
    except Exception as e:                                   # tables are a convenience; never stop the report
        C.log(f"[report] tables.md: {e!r}")
    # ledger rows (one-line summaries for the derived rows)
    try:
        if "predict" in res:
            t = res["predict"]["test"]
            js = [k for k in t if k != "note_lines"]
            nm = "personalised (chosen)"
            b0 = "NG0 (as used so far)"
            res["predict"]["_summary"] = "; ".join(
                f"journal {j}: next word top-3 {t[j][b0]['after0_top3']:.3f} -> {t[j][nm]['after0_top3']:.3f}, after 1 letter "
                f"{t[j][b0]['after1_top3']:.3f} -> {t[j][nm]['after1_top3']:.3f}, letters saved (top-3) "
                f"{t[j][nm]['letters_saved_top3']:.3f}, p95 latency {t[j][nm]['latency_ms_p95']:.1f} ms" for j in js)
        if "cues" in res:
            tn = res["cues"]["test"]["nominal"]
            res["cues"]["_summary"] = "; ".join(
                f"{c}: fixed on paper {tn[c]['fixed_on_paper_per_10_errors']:.1f}/10, false cues "
                f"{tn[c]['false_interventions_per_100_correct']:.1f}/100 correct, time +{tn[c]['extra_time_pct']:.0f} %, "
                f"mid-word cues {tn[c].get('interruptions_per_100_words', float('nan')):.1f}/100 words, lists read "
                f"{tn[c].get('suggestion_lists_read_per_100_words', float('nan')):.1f}/100 words"
                for c in tn) + f"; recommended (rule S4, tuning children): {res['cues']['S4']['recommended']}"
    except Exception as e:                                   # a summary must never stop the report
        C.log(f"[report] summary strings: {e!r}")
    n = EV.write(out / "evidence_rows.csv", res)
    C.log(f"[report] wrote figures, ai3.json, samples.json and {n} ledger rows to {out}")
    return slim
