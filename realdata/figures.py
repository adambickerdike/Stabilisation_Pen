"""Figures with CSV twins (results/realdata/fig_*.png + .csv), including the before/after pictures for non-engineers.

Style (the project's dataviz rules): one fixed colour per pen in every chart, thin bars, hairline solid grids, ink
colours for text, a legend whenever two or more series are shown, selective direct labels, and a CSV twin with every
plotted number.  Handwriting pictures are black ink on white ruled paper at true proportions.  Every picture carries
'SIMULATION with real recorded inputs'.

Licences: committed pictures and their CSV twins use CC BY 4.0 inputs only (UCI Character Trajectories letters, UCI
spiral PD tremor, Zenodo ET tremor), with attribution in the CSV header.  Pictures made from UNIPEN (research use
only) or BRUSH (non-commercial research use) writing are written to realdata/build/figures_research_only/
(git-ignored).  Every before/after picture: prominent SIMULATION label, the same writer and task in every panel, one
fixed scale (mm on the page), never presented as an observed improvement of a person (review 2026-09-29 s11).
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, RESULTS_DIR

INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
       "surface": "#fcfcfb", "rule": "#9ec5f4"}
# plotting order ordinary -> Rev H -> Rev J gated -> Rev J TCN -> Rev J limit; this order passes the palette validator
# (dataviz skill: lightness band, chroma, CVD >= 6.1 with legend + direct labels, normal-vision >= 16.3)
DEVICE_COLOR = {"none": "#eb6834", "revH_akf": "#4a3aa7", "revJ_gated": "#2a78d6", "revJ_tcn": "#1baf7a",
                "revJ_oracle": "#e87ba4"}
for _k in ("revH_akf", "revJ_gated", "revJ_tcn"):
    DEVICE_COLOR[_k + "|deltapen"] = DEVICE_COLOR[_k]      # colour follows the pen; the sensor is shown by marker
RESEARCH_DIR = BUILD_DIR / "figures_research_only"
SIM_TAG = "SIMULATION with real recorded inputs"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK["axis"],
                         "axes.labelcolor": INK["secondary"], "xtick.color": INK["secondary"],
                         "ytick.color": INK["secondary"], "axes.titlecolor": INK["primary"],
                         "axes.grid": False, "figure.facecolor": "white", "axes.facecolor": "white",
                         "legend.frameon": False})
    return plt


def _grid(ax, axis="x"):
    ax.grid(True, axis=axis, color=INK["grid"], linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence], comments: Sequence[str] = ()):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        for c in comments:
            f.write(f"# {c}\n")
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([(f"{v:.6g}" if isinstance(v, float) else v) for v in r])


# ================================================================== before/after pictures
def _strokes(path_xyd: np.ndarray) -> List[np.ndarray]:
    """[[x_mm, y_mm, down], ...] -> pen-down polylines."""
    P = np.asarray(path_xyd, float)
    d = P[:, 2] > 0.5
    out, cur = [], []
    for i in range(len(P)):
        if d[i]:
            cur.append(P[i, :2])
        elif cur:
            if len(cur) > 1:
                out.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        out.append(np.array(cur))
    return out


def page(ax, paths: Sequence[np.ndarray], line_pitch_mm: float, baselines_mm: Sequence[float], x_range, title: str,
         caption: str, intended: Optional[np.ndarray] = None, ink_w: float = 1.4):
    """One page panel: ruled lines, optional faint intended letters, ink."""
    x0, x1 = x_range
    for yb in baselines_mm:
        ax.plot([x0 - 5, x1 + 5], [yb, yb], color=INK["rule"], linewidth=0.9, zorder=0)
    if intended is not None:
        for s in _strokes(intended):
            ax.plot(s[:, 0], s[:, 1], color="#c9c8c1", linewidth=ink_w * 0.9, solid_capstyle="round", zorder=1)
    for s in paths:
        ax.plot(s[:, 0], s[:, 1], color=INK["primary"], linewidth=ink_w, solid_capstyle="round",
                solid_joinstyle="round", zorder=2)
    ax.set_aspect("equal")
    ax.set_xlim(x0 - 4, x1 + 4)
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=15, color=INK["primary"], pad=6, fontweight="bold")
    ax.text(0.0, -0.02, caption, transform=ax.transAxes, ha="left", va="top", fontsize=15, color=INK["primary"])


def before_after(out_png: Path, panels: List[Dict], header: str, footer: str, research_only: bool = False) -> Path:
    """panels: [{'title', 'caption', 'ink' [[x,y,d]..] mm, 'intended' (optional)}], stacked vertically, same scale."""
    plt = _plt()
    allp = np.vstack([np.asarray(p["ink"], float)[:, :2] for p in panels])
    x0, x1 = float(np.percentile(allp[:, 0], 0.2)), float(np.percentile(allp[:, 0], 99.8))
    ys = [np.asarray(p["ink"], float)[:, 1] for p in panels]
    lo = min(float(np.percentile(y, 0.5)) for y in ys)
    hi = max(float(np.percentile(y, 99.5)) for y in ys)
    h_panel = (hi - lo) + 8
    w_in = min(16.0, max(9.0, (x1 - x0) / 9.0))
    fig_h = len(panels) * (h_panel / (x1 - x0 + 8) * w_in + 0.9) + 1.3
    fig, axs = plt.subplots(len(panels), 1, figsize=(w_in, fig_h))
    axs = np.atleast_1d(axs)
    for ax, p in zip(axs, panels):
        page(ax, _strokes(p["ink"]), p.get("line_pitch_mm", 13.0), p.get("baselines_mm", []), (x0, x1), p["title"],
             p["caption"], p.get("intended"))
        ax.set_ylim(lo - 3, hi + 3)
    fig.suptitle(header, x=0.01, ha="left", fontsize=13, color=INK["secondary"], y=0.995)
    fig.text(0.01, 0.005, footer, ha="left", va="bottom", fontsize=8.5, color=INK["secondary"], wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    rows = []
    for pi, p in enumerate(panels):
        for x, y, d in np.asarray(p["ink"], float):
            rows.append([pi, p["title"], round(x, 3), round(y, 3), int(d)])
    write_csv(out_png.with_suffix(".csv"), ["panel", "title", "x_mm", "y_mm", "pen_down"], rows,
              [SIM_TAG, footer.replace("\n", " ")] + ([p["title"] + ": " + p["caption"] for p in panels]))
    return out_png


# ================================================================== the one-number chart
def words_chart(out_png: Path, table: Dict, devices: Sequence[str], labels: Dict[str, str], title: str, note: str) -> Path:
    """table: {group label: {device: words_of_10}} -> horizontal grouped bars, one colour per pen."""
    plt = _plt()
    groups = list(table)
    nd = len(devices)
    fig, ax = plt.subplots(figsize=(9.5, 0.55 * len(groups) * nd / 2.2 + 2.2))
    bh = 0.8 / nd
    rows = []
    for gi, g in enumerate(groups):
        for di, d in enumerate(devices):
            v = table[g].get(d)
            if v is None:
                continue
            y = gi + (di - (nd - 1) / 2) * bh
            ax.barh(y, v, height=bh * 0.82, color=DEVICE_COLOR[d], zorder=2)
            if d in ("none", "revJ_gated"):
                ax.text(v + 0.12, y, f"{v:.1f}", va="center", ha="left", fontsize=9, color=INK["primary"])
            rows.append([g, labels[d], v])
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(groups, fontsize=10, color=INK["primary"])
    ax.invert_yaxis()
    ax.set_xlim(0, 10.8)
    ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel("words you can read, out of 10")
    _grid(ax, "x")
    handles = [plt.Rectangle((0, 0), 1, 1, color=DEVICE_COLOR[d]) for d in devices]
    ax.legend(handles, [labels[d] for d in devices], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=min(3, nd),
              fontsize=9)
    ax.set_title(title, loc="left", fontsize=12, pad=38)
    fig.text(0.01, 0.01, note, fontsize=8, color=INK["secondary"], ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["group", "pen", "words_of_10"], rows, [SIM_TAG, note])
    return out_png


def bridge_chart(out_png: Path, series: Dict[str, Dict[str, float]], devices: Sequence[str], labels: Dict[str, str],
                 ylabel: str, title: str, note: str) -> Path:
    """series: {input set label: {device: value}} -> one line per pen across the three input sets (same axis)."""
    plt = _plt()
    sets = list(series)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    rows = []
    for d in devices:
        ys = [series[s].get(d) for s in sets]
        if all(v is None for v in ys):
            continue
        ax.plot(range(len(sets)), ys, color=DEVICE_COLOR[d], linewidth=2, marker="o", markersize=6, zorder=3,
                label=labels[d])
        last = next((v for v in reversed(ys) if v is not None), None)
        if last is not None:
            ax.text(len(sets) - 1 + 0.06, last, f"{last:.1f}" if last < 100 else f"{last:.0f}", va="center",
                    fontsize=9, color=INK["primary"])
        for s, v in zip(sets, ys):
            rows.append([s, labels[d], v])
    ax.set_xticks(range(len(sets)))
    ax.set_xticklabels(sets, fontsize=9)
    ax.set_xlim(-0.2, len(sets) - 0.5)
    ax.set_ylabel(ylabel)
    _grid(ax, "y")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=9)
    ax.set_title(title, loc="left", fontsize=12)
    fig.text(0.01, 0.01, note, fontsize=8, color=INK["secondary"], ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["inputs", "pen", "value"], rows, [SIM_TAG, ylabel, note])
    return out_png


# ================================================================== tremor library figure
def tremor_figure(out_png: Path, lib: Dict, examples: List[Dict]) -> Path:
    """(a) PD tip amplitudes with the class boundaries; (b) real traces against the synthetic model at the same
    frequency and amplitude; (c) irregularity: envelope CV and frequency wander, real against the model's settings."""
    plt = _plt()
    cl = lib["classes"]
    amps = np.array(cl["_subject_amplitudes_mm"])
    fig = plt.figure(figsize=(12, 8.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05])
    ax = fig.add_subplot(gs[0, 0])
    rng = np.random.default_rng(0)
    ax.scatter(amps, rng.uniform(-0.25, 0.25, len(amps)), s=28, color="#2a78d6", edgecolor="white", linewidth=1.2, zorder=3)
    for k, c in (("mild", "#86b6ef"), ("moderate", "#3987e5"), ("severe", "#184f95")):
        lo, hi = cl[k]["range_mm"]
        ax.axvspan(lo, hi, color=c, alpha=0.10, zorder=0)
        ax.text(math.sqrt(lo * hi), 0.42, f"{k}\n{lo:.2f}-{hi:.2f} mm", ha="center", va="bottom", fontsize=8.5,
                color=INK["primary"])
    ax.set_xscale("log")
    ax.set_ylim(-0.5, 0.75)
    ax.set_yticks([])
    ax.set_xlabel("tremor at the pen tip, peak (mm, log scale)")
    ax.set_title("(a) Parkinson's patients drawing on a tablet: one dot per patient", loc="left", fontsize=10.5)
    _grid(ax, "x")
    pa = lib["classes"].get("_plan_assumption_mm", {})
    ax.text(0.99, 0.02, "plan's assumed classes: mild 0.3-1, moderate 2-4, severe 5-10 mm",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=INK["secondary"])
    # (b) traces
    ax2 = fig.add_subplot(gs[0, 1])
    rows = []
    off = 0.0
    for ex in examples:
        t, y = ex["t"], ex["y"]
        ax2.plot(t, y + off, color="#2a78d6" if ex["kind"] == "real" else "#eb6834", linewidth=1.5)
        ax2.text(t[-1] + 0.03, off, ex["label"], va="center", fontsize=8, color=INK["primary"])
        for a, b in zip(t, y):
            rows.append([ex["label"], ex["kind"], round(float(a), 4), round(float(b), 5)])
        off -= 2.6
    ax2.set_xlim(0, examples[0]["t"][-1] + 1.15 if examples else 1)
    ax2.set_yticks([])
    ax2.set_xlabel("time (s)")
    ax2.set_title("(b) Real tremor (blue) against the model used so far (orange),\n    each scaled to the same size and frequency",
                  loc="left", fontsize=10.5)
    _grid(ax2, "x")
    # (c) irregularity
    ax3 = fig.add_subplot(gs[1, :])
    grp = [("uci_spiral", "PD", "kinetic", "PD, tablet (tip)"), ("zenodo_et", "ET", "postural", "ET, hand (arms out)"),
           ("zenodo_et", "ET", "rest", "ET, hand (at rest)"), ("pads", "ET", "postural", "ET, wrist watch (posture)"),
           ("pads", "PD", "rest", "PD, wrist watch (rest)")]
    xs = []
    for gi, (src, g, cond, lab) in enumerate(grp):
        sel = [x for x in lib["rows"] if x["source"] == src and x["group"] == g and x["condition"] == cond and x["detected"]]
        for j, key in enumerate(("env_cv", "f_sd")):
            v = np.array([x[key] for x in sel if np.isfinite(x[key])])
            if len(v) == 0:
                continue
            xpos = gi * 3 + j
            q = np.percentile(v, [25, 50, 75])
            ax3.plot([xpos, xpos], [q[0], q[2]], color="#2a78d6" if j == 0 else "#1baf7a", linewidth=6,
                     solid_capstyle="round", alpha=0.35)
            ax3.plot([xpos], [q[1]], marker="o", markersize=8, color="#2a78d6" if j == 0 else "#1baf7a",
                     markeredgecolor="white", markeredgewidth=2)
            rows.append([lab, key, len(v), q[0], q[1], q[2]])
        xs.append((gi * 3 + 0.5, lab + f"\n(n = {len(sel)})"))
    ax3.axhline(0.3, color="#eb6834", linewidth=1.5)
    ax3.text(len(grp) * 3 - 0.6, 0.31, "model setting: 0.3 (amplitude wander) and 0.3 Hz (frequency wander)",
             ha="right", va="bottom", fontsize=8.5, color=INK["primary"])
    ax3.set_xticks([p for p, _ in xs])
    ax3.set_xticklabels([l for _, l in xs], fontsize=8.5)
    ax3.set_ylabel("median and quartiles")
    ax3.set_title("(c) Real tremor wanders about twice as much as the model: amplitude wander (envelope CV, blue) "
                  "and frequency wander (Hz, green)", loc="left", fontsize=10.5)
    _grid(ax3, "y")
    fig.text(0.01, 0.005, "DATA re-analysed (CALC): UCI PD spiral tablet (CC BY 4.0), Zenodo ET accelerometry (CC BY 4.0), "
             "PADS smartwatch (CC BY-NC-SA 4.0, statistics only). Tip amplitude: background-corrected major-axis peak.",
             fontsize=8, color=INK["secondary"], ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    for a in amps:
        rows.append(["pd_subject_tip_amplitude_mm", "", round(float(a), 5)])
    write_csv(out_png.with_suffix(".csv"), ["series", "kind_or_measure", "x_or_n", "y_or_p25", "p50", "p75"], rows,
              ["DATA re-analysis (CALC)"])
    return out_png


# ================================================================== kinematics figure
def kinematics_figure(out_png: Path, val: Dict) -> Path:
    plt = _plt()
    sets = [("syn_v1", "Synthetic writers\nused so far", "#eb6834"),
            ("syn_v2", "Synthetic writers\nrefitted (sim2j)", "#4a3aa7"),
            ("real_unipen", "Real: UNIPEN sentences\n(paper and tablets)", "#2a78d6"),
            ("real_brush", "Real: BRUSH words\n(170 writers)", "#1baf7a"),
            ("real_chartraj", "Real: one writer's letters\n(UCI)", "#e87ba4")]
    sets = [s for s in sets if s[0] in val["sets"] and "error" not in val["sets"][s[0]]]
    L = val["literature"]
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    rows = []
    # speed
    ax = axs[0, 0]
    for i, (k, lab, c) in enumerate(sets):
        v = val["sets"][k]["speed_mm_s"]["mean"]
        ax.barh(i, v, height=0.55, color=c)
        ax.text(v + 0.8, i, f"{v:.0f}", va="center", fontsize=9, color=INK["primary"])
        rows.append([k, "speed_mm_s", v])
    ax.axvspan(L["speed_mm_s"]["value"] - L["speed_mm_s"]["sd_between"], L["speed_mm_s"]["value"] + L["speed_mm_s"]["sd_between"],
               color="#86b6ef", alpha=0.18, zorder=0)
    ax.axvline(L["speed_mm_s"]["value"], color=INK["secondary"], linewidth=1)
    ax.text(L["speed_mm_s"]["value"], len(sets) - 0.4, "adults on paper\n30.5 +- 7.9 (LIT CON-20)", ha="center",
            fontsize=8, color=INK["secondary"])
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels([s[1] for s in sets], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("mean pen-down speed (mm/s)")
    ax.set_title("(a) Writing speed", loc="left", fontsize=10.5)
    _grid(ax, "x")
    # 8-12 Hz share
    ax = axs[0, 1]
    for i, (k, lab, c) in enumerate(sets):
        v = 100 * val["sets"][k]["spectrum"]["share_8_12"]
        ax.barh(i, v, height=0.55, color=c)
        ax.text(v + 0.3, i, f"{v:.1f} %", va="center", fontsize=9, color=INK["primary"])
        rows.append([k, "share_8_12_pct", v])
    ax.axvspan(100 * L["share_8_12"]["lo"], 100 * L["share_8_12"]["hi"], color="#86b6ef", alpha=0.35, zorder=0)
    ax.text(100 * L["share_8_12"]["hi"] + 0.3, len(sets) - 0.45, "one real writer: 1.3-1.7 % (LIT CON-25)", fontsize=8,
            color=INK["secondary"])
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels([s[1] for s in sets], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("share of the writing's velocity energy at 8-12 Hz (%)")
    ax.set_title("(b) Writing movement inside the tremor band", loc="left", fontsize=10.5)
    _grid(ax, "x")
    # cumulative spectrum
    ax = axs[1, 0]
    for k, lab, c in sets:
        f = np.array(val["sets"][k]["spectrum_Hz"])
        P = np.array(val["sets"][k]["spectrum_rel"])
        cum = np.cumsum(P) / np.sum(P)
        ax.plot(f, 100 * cum, color=c, linewidth=2, label=lab.replace("\n", " "))
        for a, b in zip(f[::4], cum[::4]):
            rows.append([k, "cumulative_velocity_energy_at_Hz", round(float(a), 3), round(float(b), 4)])
    for q, fq in (("50", 3.1), ("90", 4.9), ("95", 5.9), ("99", 9.3)):
        ax.plot([fq], [float(q)], marker="D", markersize=6, color=INK["primary"], zorder=5)
    ax.text(9.6, 97, "LIT CON-25", fontsize=8, color=INK["primary"])
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 101)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("velocity energy below (%)")
    ax.set_title("(c) Where the writing's movement lies in frequency", loc="left", fontsize=10.5)
    ax.legend(fontsize=7.5, loc="lower right")
    _grid(ax, "both")
    # strokes and power law
    ax = axs[1, 1]
    for i, (k, lab, c) in enumerate(sets):
        s = val["sets"][k]["stroke_ms"]["median"]
        b = val["sets"][k]["beta"]["mean"]
        ax.scatter([s], [b], s=90, color=c, edgecolor="white", linewidth=2, zorder=3)
        ax.text(s + 3, b + 0.004, lab.split("\n")[0], fontsize=8, color=INK["primary"])
        rows.append([k, "stroke_ms_median", s])
        rows.append([k, "power_law_beta", b])
    ax.axvspan(90, 150, color="#86b6ef", alpha=0.18, zorder=0)
    ax.axhline(2 / 3, color=INK["secondary"], linewidth=1)
    ax.text(92, 2 / 3 + 0.005, "2/3 law (LIT CON-27); strokes 90-150 ms (LIT CON-24)", fontsize=8, color=INK["secondary"])
    ax.set_xlabel("median stroke duration (ms)")
    ax.set_ylabel("speed-curvature exponent")
    ax.set_title("(d) Stroke timing and the two-thirds power law", loc="left", fontsize=10.5)
    _grid(ax, "both")
    fig.text(0.01, 0.005, "CALC on DATA (UNIPEN research-only, BRUSH non-commercial research, UCI CC BY 4.0) and on the "
             "synthetic writers (SIM); one measurement function for all (sim2j.writers.kinematics).", fontsize=8,
             color=INK["secondary"])
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["set", "measure", "value", "value2"], rows, ["CALC; literature as labelled"])
    return out_png


def spectra_figure(out_png: Path, grid: np.ndarray, groups: Dict[str, np.ndarray], title: str, ylabel: str, note: str) -> Path:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9, 4.8))
    cols = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]
    rows = []
    for (lab, P), c in zip(groups.items(), cols):
        med = np.median(P, axis=0)
        q1, q3 = np.percentile(P, [25, 75], axis=0)
        ax.fill_between(grid, q1, q3, color=c, alpha=0.12, linewidth=0)
        ax.plot(grid, med, color=c, linewidth=2, label=f"{lab} (n = {len(P)})")
        for f, m in zip(grid, med):
            rows.append([lab, round(float(f), 3), float(m)])
    ax.axvspan(3, 12, color="#e1e0d9", alpha=0.35, zorder=0)
    ax.text(7.5, ax.get_ylim()[1] if False else 0.0, "", fontsize=8)
    ax.set_yscale("log")
    ax.set_xlim(0.5, 20)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=9)
    ax.set_title(title, loc="left", fontsize=11)
    _grid(ax, "both")
    fig.text(0.01, 0.01, note, fontsize=8, color=INK["secondary"], ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["group", "Hz", "median_psd"], rows, [note])
    return out_png


# ================================================================== results-card charts (writer-bootstrap intervals)
def words_ci_chart(out_png: Path, groups: List[Dict], devices: Sequence[str], labels: Dict[str, str], title: str,
                   note: str, bound: Optional[Dict[str, str]] = None) -> Path:
    """groups: [{'label', 'clean': {mean, lo, hi}, 'dev': {device: {mean, lo, hi}}, 'bound': {device: mean}}].
    Horizontal bars per pen (headline page sensor) with 95 % writer-bootstrap intervals; open circles = the same pen
    with the ideal page sensor (bound); a black tick = the same notes without tremor (the reader's ceiling)."""
    plt = _plt()
    nd = len(devices)
    fig, ax = plt.subplots(figsize=(10.5, 0.62 * len(groups) * nd / 2.0 + 2.6))
    bh = 0.8 / nd
    rows = []
    for gi, g in enumerate(groups):
        for di, d in enumerate(devices):
            v = g["dev"].get(d)
            if not v or not np.isfinite(v.get("mean", np.nan)):
                continue
            y = gi + (di - (nd - 1) / 2) * bh
            ax.barh(y, v["mean"], height=bh * 0.8, color=DEVICE_COLOR[d], zorder=2)
            ax.plot([v["lo"], v["hi"]], [y, y], color=INK["primary"], linewidth=1.0, zorder=3)
            ax.text(max(v["hi"], v["mean"]) + 0.15, y, f"{v['mean']:.1f}", va="center", ha="left", fontsize=8.5,
                    color=INK["primary"])
            b = (g.get("bound") or {}).get(d)
            if b is not None and np.isfinite(b):
                ax.plot([b], [y], marker="o", markersize=6, markerfacecolor="white", markeredgecolor=INK["primary"],
                        markeredgewidth=1.2, zorder=4)
            rows.append([g["label"], labels.get(d, d), v["mean"], v["lo"], v["hi"], b if b is not None else ""])
        c = g.get("clean")
        if c and np.isfinite(c.get("mean", np.nan)):
            y0, y1 = gi - 0.45, gi + 0.45
            ax.plot([c["mean"], c["mean"]], [y0, y1], color=INK["primary"], linewidth=2.2, zorder=5)
            rows.append([g["label"], "no tremor (ceiling)", c["mean"], c.get("lo"), c.get("hi"), ""])
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([g["label"] for g in groups], fontsize=9.5, color=INK["primary"])
    ax.invert_yaxis()
    ax.set_xlim(0, 10.9)
    ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel("words you can read, out of 10 (bars: mean over writers; lines: 95 % interval)")
    _grid(ax, "x")
    handles = [plt.Rectangle((0, 0), 1, 1, color=DEVICE_COLOR[d]) for d in devices]
    names = [labels.get(d, d) for d in devices]
    handles.append(plt.Line2D([0], [0], color=INK["primary"], linewidth=2.2))
    names.append("same notes, no tremor")
    handles.append(plt.Line2D([0], [0], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=INK["primary"]))
    names.append("ideal page sensor (bound)")
    ax.legend(handles, names, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=8.5)
    ax.set_title(title, loc="left", fontsize=12, pad=52)
    fig.text(0.01, 0.01, note, fontsize=7.8, color=INK["secondary"], ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["group", "pen", "words_of_10_mean", "ci95_lo", "ci95_hi",
                                            "ideal_sensor_bound_mean"], rows, [SIM_TAG, note])
    return out_png


def tremor_left_chart(out_png: Path, groups: List[Dict], devices: Sequence[str], labels: Dict[str, str], title: str,
                      note: str) -> Path:
    """groups: [{'label', 'dev': {device: {mean, lo, hi}}}] with the amplitude ratio to the ordinary pen (1 = no
    change).  x axis in % of the ordinary pen's tip tremor; the power (squared-signal) reduction is printed."""
    plt = _plt()
    nd = len(devices)
    fig, ax = plt.subplots(figsize=(10.5, 0.6 * len(groups) * nd / 2.0 + 2.4))
    bh = 0.8 / nd
    rows = []
    xmax = 110.0
    for gi, g in enumerate(groups):
        for di, d in enumerate(devices):
            v = g["dev"].get(d)
            if not v or not np.isfinite(v.get("mean", np.nan)):
                continue
            y = gi + (di - (nd - 1) / 2) * bh
            m, lo, hi = 100 * v["mean"], 100 * v["lo"], 100 * v["hi"]
            xmax = max(xmax, hi + 25)
            ax.barh(y, m, height=bh * 0.8, color=DEVICE_COLOR[d], zorder=2)
            ax.plot([lo, hi], [y, y], color=INK["primary"], linewidth=1.0, zorder=3)
            pw = 100 * (1 - v["mean"] ** 2)
            ax.text(hi + 1.5, y, f"{m:.0f} %" + (f"  (power {'-' if pw >= 0 else '+'}{abs(pw):.0f} %)"),
                    va="center", ha="left", fontsize=8, color=INK["primary"])
            rows.append([g["label"], labels.get(d, d), v["mean"], v["lo"], v["hi"], 1 - v["mean"] ** 2])
    ax.axvline(100, color=INK["secondary"], linewidth=1.2)
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([g["label"] for g in groups], fontsize=9.5, color=INK["primary"])
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.set_xlabel("tremor left at the tip, % of the ordinary pen's (amplitude; 100 % = no change)")
    _grid(ax, "x")
    handles = [plt.Rectangle((0, 0), 1, 1, color=DEVICE_COLOR[d]) for d in devices]
    ax.legend(handles, [labels.get(d, d) for d in devices], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
              fontsize=8.5)
    ax.set_title(title, loc="left", fontsize=12, pad=36)
    fig.text(0.01, 0.01, note, fontsize=7.8, color=INK["secondary"], ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["group", "pen", "amplitude_ratio_mean", "ci95_lo", "ci95_hi",
                                            "power_reduction_share"], rows, [SIM_TAG, note])
    return out_png


def survey_figure(out_png: Path, survey: Dict, extra: Sequence[Dict] = ()) -> Path:
    """UNIPEN recording setups: 8-12 Hz share of the pen-down velocity energy against mean speed; the rule's box."""
    plt = _plt()
    R = survey["rule"]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    rows = []
    ax.add_patch(plt.Rectangle((0.1, R["speed_mm_s"][0]), 100 * R["share_8_12_max"] - 0.1,
                               R["speed_mm_s"][1] - R["speed_mm_s"][0], color="#86b6ef", alpha=0.18, zorder=0))
    ax.axvspan(1.3, 1.7, color="#e1e0d9", alpha=0.7, zorder=0)
    for r in survey["rows"]:
        if "share_8_12" not in r or not r.get("measured_lines"):
            continue
        x, y = 100 * r["share_8_12"], r["speed_mm_s"]
        sel = r["selected"]
        paper = bool(r["checks"].get("paper"))
        ax.scatter([x], [y], s=110 if sel else 45, color="#2a78d6" if sel else ("#1baf7a" if paper else "#898781"),
                   edgecolor="white", linewidth=1.5, zorder=3)
        if sel or x > 20 or r["setup"] in ("hpp/hpb3",):
            ax.text(x * 1.06, y, r["setup"] + (" (selected)" if sel else ""), fontsize=8, va="center",
                    color=INK["primary"])
        rows.append([r["setup"], r.get("device", ""), r.get("surface", ""), r["writers"], r["segments"], x, y,
                     100 * r.get("share_above_12", float("nan")), int(sel)])
    for e in extra:
        ax.scatter([e["x"]], [e["y"]], s=60, marker="s", color="#eb6834", edgecolor="white", linewidth=1.5, zorder=3)
        ax.text(e["x"] * 1.06, e["y"], e["label"], fontsize=8, va="center", color=INK["primary"])
        rows.append([e["label"], "", "", "", "", e["x"], e["y"], "", 0])
    ax.set_xscale("log")
    ax.set_xlim(0.2, 80)
    ax.set_xlabel("share of the pen-down velocity energy at 8-12 Hz (%, log scale); grey band: 1.3-1.7 % (LIT CON-25)")
    ax.set_ylabel("mean pen-down speed (mm/s)")
    ax.set_title("Which recorded writing is clean enough to test trackers on? (lower-case words, per recording setup)",
                 loc="left", fontsize=10.5)
    _grid(ax, "both")
    handles = [plt.Line2D([0], [0], marker="o", linestyle="", color=c, markersize=8) for c in ("#2a78d6", "#1baf7a", "#898781")]
    handles.append(plt.Line2D([0], [0], marker="s", linestyle="", color="#eb6834", markersize=7))
    ax.legend(handles, ["selected (passes every check)", "paper, fails a check", "screen or unknown surface",
                        "other data sets"], fontsize=8, loc="upper right")
    fig.text(0.01, 0.01, "CALC on DATA (UNIPEN train_r01_v07 category 8, research use only; BRUSH). Blue box: the "
             "selection rule (<= 2.5 % at 8-12 Hz, <= 3 % above 12 Hz, 15-60 mm/s, >= 100 samples/s, >= 15 points/mm, "
             ">= 10 writers, paper), fixed before any HW1 run.", fontsize=7.8, color=INK["secondary"], ha="left",
             va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    write_csv(out_png.with_suffix(".csv"), ["setup", "device", "surface", "writers", "lines", "share_8_12_pct",
                                            "speed_mm_s", "share_above_12_pct", "selected"], rows,
              ["CALC on DATA; rule " + str(R)])
    return out_png
