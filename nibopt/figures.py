"""Figures of study N (PNG with a CSV twin each: the table view).  Palette: the validated reference categorical order
(blue, orange, aqua, yellow; first three all-pairs safe for scatter), blue <-> red for signed changes, text in ink
tokens, hairline grid.  CALCULATION labels are in the titles."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import numpy as np

SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
NEG, POS = "#2a78d6", "#e34948"


def _style(ax):
    ax.set_facecolor(SURF)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=8)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)


def _csv(path: Path, header: List[str], rows: List[List]):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _fig(w=10, h=4.6, n=1):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, n, figsize=(w, h))
    fig.patch.set_facecolor(SURF)
    return plt, fig, (axs if n > 1 else [axs])


def pareto(points: List[Dict], front: List[Dict], cands: Dict[str, Dict], out: Path) -> List[str]:
    """Reach against the worst-case and the typical copper loss, feasible points, three body-diameter classes."""
    plt, fig, axs = _fig(11, 4.8, 2)
    classes = [("OD <= 22 mm", lambda od: od <= 22.0 + 1e-6, S1), ("22-24 mm", lambda od: 22.0 < od <= 24.0 + 1e-6, S2),
               ("24-26 mm", lambda od: od > 24.0 + 1e-6, S3)]
    rows = []
    for k, (ax, obj, lab) in enumerate(zip(axs, (1, 2), ("worst-case copper loss, W (screen, matched loads)",
                                                         "typical copper loss, W (duty A, mean 35-75 deg)"))):
        _style(ax)
        for name, sel, col in classes:
            pts = [p for p in front if sel(p["F"][3])]
            if pts:
                ax.scatter([-p["F"][0] for p in pts], [p["F"][obj] for p in pts], s=16, color=col,
                           edgecolors=SURF, linewidths=0.8, label=name, zorder=3)
        for cn, c in cands.items():
            ax.scatter([c["reach_mm"]], [c["screen_W"] if obj == 1 else c["typical_W"]], s=90, marker="D",
                       color=INK, edgecolors=SURF, linewidths=1.5, zorder=4)
            ax.annotate(cn, (c["reach_mm"], c["screen_W"] if obj == 1 else c["typical_W"]), textcoords="offset points",
                        xytext=(6, 6), fontsize=8, color=INK)
        if obj == 1:
            ax.axhline(0.15, color=MUTED, lw=1.0)
            ax.annotate("0.15 W (the pass's allocation)", (1.0, 0.15), textcoords="offset points", xytext=(2, 3),
                        fontsize=7, color=INK2)
        ax.set_yscale("log")
        ax.set_xlabel("usable radius (mm)")
        ax.set_ylabel(lab)
        if k == 0:
            ax.legend(frameon=False, fontsize=8, labelcolor=INK2, title="non-dominated, feasible", title_fontsize=8)
    fig.suptitle("Pareto front of the balanced nib (CALCULATION; weakest force constant over the disk x 0.7)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURF)
    plt.close(fig)
    for p in front:
        rows.append([f"{-p['F'][0]:.3f}", f"{p['F'][1]:.5f}", f"{p['F'][2]:.5f}", f"{p['F'][3]:.2f}", f"{p['F'][4]:.2f}",
                     f"{p.get('m_move_g', float('nan')):.3f}", f"{p.get('sv_min', float('nan')):.4f}",
                     f"{p.get('skin_C', float('nan')):.2f}"])
    _csv(out.with_suffix(".csv"), ["reach_mm", "screen_W", "typical_W", "od_mm", "length_mm", "m_move_g",
                                   "sv_min_N_sqrtW", "skin_C"], rows)
    return [str(out), str(out.with_suffix(".csv"))]


def waterfall(steps: List[Dict], key: str, unit: str, title: str, out: Path, scale: float = 1.0) -> List[str]:
    plt, fig, axs = _fig(10, 0.36 * len(steps) + 1.4)
    ax = axs[0]
    _style(ax)
    ax.grid(True, axis="x", color=GRID, lw=0.8)
    ax.grid(False, axis="y")
    vals = [s[key] * scale for s in steps]
    names = [s["name"] for s in steps]
    y = np.arange(len(steps))[::-1]
    for i, (yy, v) in enumerate(zip(y, vals)):
        if i == 0 or i == len(steps) - 1:
            ax.barh(yy, v, height=0.55, color=MUTED, zorder=3)
        else:
            prev = vals[i - 1]
            ax.barh(yy, v - prev, left=prev, height=0.55, color=POS if v >= prev else NEG, zorder=3)
        ax.annotate(f"{v:.3g}", (v, yy), textcoords="offset points", xytext=(4, -3), fontsize=7, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8, color=INK2)
    ax.set_xlabel(unit)
    ax.set_title(title, fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURF)
    plt.close(fig)
    _csv(out.with_suffix(".csv"), ["step", "name", unit], [[s["step"], s["name"], f"{s[key] * scale:.6g}"] for s in steps])
    return [str(out), str(out.with_suffix(".csv"))]


def levers(study: Dict, out: Path) -> List[str]:
    rows = sorted(study["rows"], key=lambda r: abs(r["d_typical_pct"]))
    plt, fig, axs = _fig(9, 0.34 * len(rows) + 1.4)
    ax = axs[0]
    _style(ax)
    ax.grid(False, axis="y")
    y = np.arange(len(rows))
    v = [r["d_typical_pct"] for r in rows]
    ax.barh(y, v, height=0.55, color=[NEG if x < 0 else POS for x in v], zorder=3)
    for yy, x in zip(y, v):
        ax.annotate(f"{x:+.0f} %", (x, yy), textcoords="offset points", xytext=(4 if x >= 0 else -30, -3), fontsize=7,
                    color=INK)
    ax.axvline(0, color="#c3c2b7", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([r["lever"] for r in rows], fontsize=8, color=INK2)
    ax.set_xlabel("change in typical copper loss (duty A), %")
    ax.set_title(f"Levers, one at a time, around '{study['design']}' (CALCULATION)", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURF)
    plt.close(fig)
    _csv(out.with_suffix(".csv"), ["lever", "typical_W", "severe35_W", "skin_C", "screen_W", "d_typical_pct", "d_screen_pct"],
         [[r["lever"], f"{r['typical_W']:.5f}", f"{r['severe35_W']:.5f}", f"{r['skin_C']:.2f}", f"{r['screen_W']:.5f}",
           f"{r['d_typical_pct']:.1f}", f"{r['d_screen_pct']:.1f}"] for r in study["rows"]])
    return [str(out), str(out.with_suffix(".csv"))]


def reconciliation(table: Dict[str, Dict], out: Path) -> List[str]:
    """Typical and worst-case copper loss of the four designs under the matched assumptions, two conventions."""
    names = list(table)
    plt, fig, axs = _fig(11, 4.4, 2)
    series = [("weakest point x 0.7", "worst07", S1), ("centre x 1.0 (study K's low end)", "centre10", S2)]
    x = np.arange(len(names))
    rows = []
    for ax, (key, lab) in zip(axs, (("dutyA", "typical (duty A), mean 35-75 deg, W"), ("screen", "worst-case screen, W"))):
        _style(ax)
        ax.grid(False, axis="x")
        for j, (sname, conv, col) in enumerate(series):
            vals = [(table[n][key][conv]["mean"] if key == "dutyA" else table[n][key][conv]) for n in names]
            ax.bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=col, label=sname, zorder=3)
            for xx, vv in zip(x + (j - 0.5) * 0.36, vals):
                ax.annotate(f"{vv:.3f}", (xx, vv), textcoords="offset points", xytext=(-10, 2), fontsize=7, color=INK)
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=8, color=INK2)
        ax.set_ylabel(lab)
    axs[0].legend(frameon=False, fontsize=8, labelcolor=INK2)
    fig.suptitle("The four designs under one load model (CALCULATION; nothing measured)", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURF)
    plt.close(fig)
    for n in names:
        t = table[n]
        rows.append([n, f"{t['dutyA']['worst07']['mean']:.5f}", f"{t['dutyA']['centre10']['mean']:.5f}",
                     f"{t['screen']['worst07']:.5f}", f"{t['screen']['centre10']:.5f}"])
    _csv(out.with_suffix(".csv"), ["design", "typical_worst07_W", "typical_centre10_W", "screen_worst07_W",
                                   "screen_centre10_W"], rows)
    return [str(out), str(out.with_suffix(".csv"))]


def battery(budgets: Dict[str, Dict], out: Path) -> List[str]:
    """Hours per mode at the conservative end (weakest point x 0.7, electronics high) for study K's B1 and candidates."""
    names = list(budgets)
    modes = ["steady_0mm", "steady_1mm", "steady_2mm", "guide", "spelling_cue", "severe"]
    cols = [MUTED, S1, S2, S3, S4]
    plt, fig, axs = _fig(11, 4.2)
    ax = axs[0]
    _style(ax)
    ax.grid(False, axis="x")
    x = np.arange(len(modes))
    wbar = 0.8 / len(names)
    rows = []
    for j, n in enumerate(names):
        h = [budgets[n]["battery_hours"]["conservative"][m] for m in modes]
        ax.bar(x + (j - (len(names) - 1) / 2) * wbar, h, width=wbar * 0.92, color=cols[j % len(cols)], label=n, zorder=3)
        rows.append([n] + [f"{v:.2f}" for v in h])
    ax.axhline(8.0, color=MUTED, lw=1)
    ax.annotate("REQ-RVJ-I01 8 h", (x[-1] + 0.3, 8.0), textcoords="offset points", xytext=(0, 3), fontsize=7, color=INK2)
    ax.set_xticks(x)
    ax.set_xticklabels(modes, fontsize=8, color=INK2)
    ax.set_ylabel("hours on 2.22 Wh (conservative end)")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, ncol=len(names))
    ax.set_title("Battery per mode in study K's structure (CALCULATION)", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURF)
    plt.close(fig)
    _csv(out.with_suffix(".csv"), ["design"] + modes, rows)
    return [str(out), str(out.with_suffix(".csv"))]
