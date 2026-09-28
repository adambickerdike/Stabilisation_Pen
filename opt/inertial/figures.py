"""Figures of the Rev H study (results/opt/fig_in_*.png), each with a CSV twin holding the plotted numbers.

Style: one measure per chart (no dual axes), small multiples for a second factor, categorical colours in the fixed order
of the validated palette (blue, orange, aqua, yellow; checked with the dataviz validator, light mode), a legend for two
or more series plus direct labels where there is room, recessive grid.  Aqua and yellow have low contrast on white,
so every series is also labelled and the CSV twin carries the values.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Sequence

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "results", "opt")
PAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#1f2328"
MUTED = "#59636e"
GRID = "#d8dee4"


def _style():
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.titlesize": 9, "axes.titleweight": "bold", "legend.frameon": False,
                         "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})


def _grid(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def _save(fig, name, header: Sequence[str], rows: List[Sequence]):
    os.makedirs(OUT, exist_ok=True)
    png = os.path.join(OUT, name + ".png")
    fig.savefig(png, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([f"{v:.6g}" if isinstance(v, (float, np.floating)) else v for v in r])
    return png


def _label_end(ax, x, y, text, color):
    ax.annotate(text, (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=INK)


def lines_panels(name, title, panels: Dict[str, Dict[str, tuple]], xlabel, ylabel, ylim=None, note=None, direct=True,
                 hline=None, width=3.3):
    """panels: {panel title: {series label: (x, y)}}; series share colours by label order across panels."""
    _style()
    labels = []
    for p in panels.values():
        for k in p:
            if k not in labels:
                labels.append(k)
    col = {k: PAL[i] for i, k in enumerate(labels)}
    fig, axs = plt.subplots(1, len(panels), figsize=(width * len(panels) + 0.6, 3.0), sharey=True, squeeze=False)
    rows = []
    for ax, (pt, series) in zip(axs[0], panels.items()):
        _grid(ax)
        for k, (x, y) in series.items():
            ax.plot(x, y, "-o", color=col[k], lw=2, ms=4, label=k, markeredgecolor="white", markeredgewidth=0.8)
            for xi, yi in zip(x, y):
                rows.append([pt, k, xi, yi])
        if hline is not None:
            ax.axhline(hline, color=MUTED, lw=0.8, ls="--")
        ax.set_title(pt, loc="left")
        ax.set_xlabel(xlabel)
        if ylim:
            ax.set_ylim(*ylim)
    axs[0][0].set_ylabel(ylabel)
    h, lab = axs[0][0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=min(4, len(lab)), bbox_to_anchor=(0.5, -0.08 - 0.05 * ((len(lab) - 1) // 4)),
               fontsize=7.5)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    if note:
        fig.text(0.01, -0.2 - 0.05 * ((len(lab) - 1) // 4), note, fontsize=6.8, color=MUTED, ha="left", wrap=True)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    return _save(fig, name, ["panel", "series", xlabel, ylabel], rows)


def dots_panels(name, title, panels: Dict[str, Dict[str, Dict[str, float]]], xlabel, note=None, xlim=(0, 1.3), ref_line=1.0):
    """Dot plot: panels {title: {series: {category: value}}}; categories on y, value on x."""
    _style()
    series = []
    cats = []
    for p in panels.values():
        for s, d in p.items():
            if s not in series:
                series.append(s)
            for c in d:
                if c not in cats:
                    cats.append(c)
    col = {s: PAL[i] for i, s in enumerate(series)}
    fig, axs = plt.subplots(1, len(panels), figsize=(3.0 * len(panels) + 1.6, 0.36 * len(cats) + 1.5), sharey=True,
                            squeeze=False)
    rows = []
    ypos = {c: len(cats) - 1 - i for i, c in enumerate(cats)}
    for ax, (pt, sd) in zip(axs[0], panels.items()):
        _grid(ax)
        off = np.linspace(-0.14, 0.14, len(series)) if len(series) > 1 else [0.0]
        for j, s in enumerate(series):
            d = sd.get(s, {})
            xs = [d[c] for c in cats if c in d]
            ys = [ypos[c] + off[j] for c in cats if c in d]
            ax.scatter(xs, ys, s=34, color=col[s], label=s, edgecolor="white", linewidth=0.8, zorder=3)
            for c in cats:
                if c in d:
                    rows.append([pt, s, c, d[c]])
                    ax.annotate(f"{d[c]:.2f}", (d[c], ypos[c] + off[j]), xytext=(5, 0), textcoords="offset points", va="center",
                                fontsize=6.5, color=MUTED)
        if ref_line is not None:
            ax.axvline(ref_line, color=MUTED, lw=0.8, ls="--")
        ax.set_title(pt, loc="left")
        ax.set_xlim(*xlim)
        ax.set_xlabel(xlabel)
    axs[0][0].set_yticks([ypos[c] for c in cats])
    axs[0][0].set_yticklabels(cats)
    if len(series) > 1:
        h, lab = axs[0][0].get_legend_handles_labels()
        fig.legend(h, lab, loc="lower center", ncol=len(lab), bbox_to_anchor=(0.5, -0.06), fontsize=7.5)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    if note:
        fig.text(0.01, -0.12, note, fontsize=6.8, color=MUTED, ha="left", wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    return _save(fig, name, ["panel", "series", "category", xlabel], rows)


def scatter_front(name, title, pts, highlight: Dict[str, tuple], xlabel, ylabel, note=None, muted_label="evaluations"):
    """pts: list of (x, y) evaluations (muted); highlight: {label: (x, y)} in palette order with direct labels."""
    _style()
    fig, ax = plt.subplots(figsize=(4.6, 3.3))
    _grid(ax)
    pts = np.asarray(pts)
    ax.scatter(pts[:, 0], pts[:, 1], s=16, color="#9aa4ae", label=muted_label, zorder=2)
    rows = [[muted_label, x, y] for x, y in pts]
    for i, (k, (x, y)) in enumerate(highlight.items()):
        ax.scatter([x], [y], s=60, color=PAL[i], label=k, edgecolor="white", linewidth=1.0, zorder=4)
        ax.annotate(k, (x, y), xytext=(6, 4), textcoords="offset points", fontsize=7.5, color=INK)
        rows.append([k, x, y])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=7.5, loc="best")
    ax.set_title(title, loc="left", fontsize=10)
    if note:
        fig.text(0.01, -0.06, note, fontsize=6.8, color=MUTED, ha="left", wrap=True)
    fig.tight_layout()
    return _save(fig, name, ["point", xlabel, ylabel], rows)


def time_series(name, title, t, series: Dict[str, np.ndarray], ylabel, note=None):
    _style()
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    _grid(ax)
    rows = []
    for i, (k, y) in enumerate(series.items()):
        ax.plot(t, y, color=PAL[i], lw=1.4 if i else 1.2, label=k)
    for j in range(len(t)):
        rows.append([t[j]] + [series[k][j] for k in series])
    ax.set_xlabel("time (s)")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=7.5, ncol=len(series), loc="upper left", bbox_to_anchor=(0, 1.16))
    ax.set_title(title, loc="left", fontsize=10, pad=24)
    if note:
        fig.text(0.01, -0.06, note, fontsize=6.8, color=MUTED, ha="left", wrap=True)
    fig.tight_layout()
    return _save(fig, name, ["t_s"] + list(series.keys()), rows)
