"""Figures of the handwriting-outcomes study: handwriting on ruled paper at true scale, before and after.

True scale: the handwriting panels are placed in millimetres on the figure, so the PNG printed at 100 % (or the PDF
page) shows the ink at its real size; on screen the 300 dpi image is simply large.  Every figure carries its evidence
status and a CSV twin with the numbers it shows.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths

ensure_paths()
from stabpen import plotstyle  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

C = plotstyle.SERIES
INK, INK2, MUTED, GRID = plotstyle.INK, plotstyle.INK2, plotstyle.MUTED, plotstyle.GRID
MM = 1.0 / 25.4
PT_PER_MM = 72.0 / 25.4
RULE = "#9fb7d8"


def write_csv(path: Path, header: List[str], rows: List[List]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def strokes(xy: np.ndarray, down: np.ndarray) -> List[np.ndarray]:
    d = np.diff(np.r_[0, np.asarray(down, bool).astype(np.int8), 0])
    return [xy[a:b] for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= 2]


def lined_panel(ax, ink_mm: np.ndarray, down: np.ndarray, x_height: float, title: str = "", spacing: float = 8.0,
                color: str = INK, width_mm: float = 0.35, xlim=None, ylim=(-6.0, 10.0), intended=None, target=None,
                baseline: float = 0.0):
    """Ink on ruled paper; ink_mm (n, 2) in mm, down (n,) pen-down flags; axes in mm with equal aspect."""
    ax.set_facecolor("white")
    x0 = np.nanmin(ink_mm[:, 0]) - 3 if xlim is None else xlim[0]
    x1 = np.nanmax(ink_mm[:, 0]) + 3 if xlim is None else xlim[1]
    for k in range(-3, 4):
        yl = baseline + k * spacing
        if ylim[0] <= yl <= ylim[1]:
            ax.axhline(yl, color=RULE, lw=0.6, zorder=0)
    if target is not None:
        for s in target:
            s = np.asarray(s)
            ax.plot(s[:, 0], s[:, 1], color=C[2], lw=2.2, alpha=0.35, solid_capstyle="round", zorder=1)
    if intended is not None:
        for s in strokes(intended[:, :2], intended[:, 2] > 0.5):
            ax.plot(s[:, 0], s[:, 1], color=MUTED, lw=0.6, ls=(0, (2, 1.5)), zorder=2)
    lw = width_mm * PT_PER_MM
    for s in strokes(ink_mm, down):
        ax.plot(s[:, 0], s[:, 1], color=color, lw=lw, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    ax.set_xlim(x0, x1)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(False)
    if title:
        ax.set_title(title, fontsize=7.5, loc="left", color=INK, pad=2)


def mm_axes(fig, x_mm, y_mm, w_mm, h_mm, W_mm, H_mm):
    """Axes placed in millimetres from the top-left corner of a W x H mm figure."""
    return fig.add_axes([x_mm / W_mm, 1.0 - (y_mm + h_mm) / H_mm, w_mm / W_mm, h_mm / H_mm])


def before_after(out: Path, columns: List[Dict], row_keys: List[str], row_labels: Dict[str, str], status: str, note: str,
                 panel_h: float = 16.0, text_h: float = 8.5, col_gap: float = 8.0, suptitle: str = "",
                 ylim=(-6.0, 10.0), spacing: float = 8.0):
    """columns: [{"title", "paths": {key: [[x, y, d], ...]}, "intended": [[x, y, d]...], "metrics": {key: str},
    "x_height": float, "target": optional strokes}].  One row per key; metrics printed under each panel."""
    widths = []
    for col in columns:
        xs = np.concatenate([np.asarray(p)[:, 0] for p in col["paths"].values() if len(p)])
        widths.append((float(np.nanmin(xs)) - 3.0, float(np.nanmax(xs)) + 3.0))
    col_w = [b - a for a, b in widths]
    left = 38.0
    W_mm = left + sum(col_w) + col_gap * (len(columns) - 1) + 6.0
    row_h = panel_h + text_h + 4.0
    top = 20.0
    H_mm = top + row_h * len(row_keys) + 8.0
    fig = plt.figure(figsize=(W_mm * MM, H_mm * MM))
    fig.patch.set_facecolor(plotstyle.SURFACE)
    if suptitle:
        fig.text(2.0 / W_mm, 1 - 3.0 / H_mm, suptitle, fontsize=9, color=INK, va="top", fontweight="bold")
    fig.text(2.0 / W_mm, 1 - 8.5 / H_mm, note, fontsize=6.2, color=MUTED, va="top")
    x = left
    csv_rows = []
    for ci, col in enumerate(columns):
        fig.text((x + 1) / W_mm, 1 - 14.5 / H_mm, col["title"], fontsize=7.5, color=INK, va="top")
        for ri, key in enumerate(row_keys):
            y = top + ri * row_h
            if key not in col["paths"]:
                continue
            p = np.asarray(col["paths"][key])
            ax = mm_axes(fig, x, y + 4.0, col_w[ci], panel_h, W_mm, H_mm)
            intended = np.asarray(col["intended"]) if (key != "intended" and col.get("show_intended", True)) else None
            lined_panel(ax, p[:, :2], p[:, 2] > 0.5, col.get("x_height", 2.5), xlim=widths[ci], ylim=ylim, spacing=spacing,
                        intended=intended, target=col.get("target"),
                        color=INK if key != "intended" else INK2)
            txt = col.get("metrics", {}).get(key, "")
            fig.text((x + 0.5) / W_mm, 1 - (y + 4.0 + panel_h + 0.8) / H_mm, txt, fontsize=6.2, color=INK2, va="top",
                     linespacing=1.25)
            csv_rows.append([col["title"], key, row_labels.get(key, key), txt])
            if ci == 0:
                fig.text(2.0 / W_mm, 1 - (y + 4.0 + panel_h * 0.45) / H_mm, row_labels.get(key, key), fontsize=7.2,
                         color=INK, va="center", wrap=True)
        x += col_w[ci] + col_gap
    # scale bar
    ax = mm_axes(fig, W_mm - 20.0, H_mm - 7.0, 10.0, 2.0, W_mm, H_mm)
    ax.plot([0, 10], [0, 0], color=INK, lw=1.5)
    ax.set_xlim(0, 10)
    ax.axis("off")
    fig.text((W_mm - 21.0) / W_mm, 5.0 / H_mm, "10 mm", fontsize=6.5, color=INK2, ha="right")
    plotstyle.stamp(fig, status, "true scale when printed at 100 %")
    fig.savefig(out, dpi=300)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["column", "row_key", "row", "metrics"], csv_rows)


def lines_chart(out: Path, panels: List[Dict], status: str, note: str = "", ncols: int = 3, size=(12.5, 4.2)):
    """panels: [{"title", "x", "xlabel", "ylabel", "series": [{"label", "y", "color", "ls"}], "ylim"}]."""
    plotstyle.apply()
    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(size[0], size[1] * nrows), squeeze=False)
    rows = []
    for ax, p in zip(axes.flat, panels):
        for s in p["series"]:
            ax.plot(p["x"], s["y"], color=s["color"], ls=s.get("ls", "-"), label=s["label"])
            ax.plot(p["x"], s["y"], **plotstyle.marker_kw(s["color"]))
            for xv, yv in zip(p["x"], s["y"]):
                rows.append([p["title"], s["label"], xv, yv])
        ax.set_title(p["title"], fontsize=9.5, loc="left")
        ax.set_xlabel(p.get("xlabel", ""))
        ax.set_ylabel(p.get("ylabel", ""))
        if p.get("ylim"):
            ax.set_ylim(*p["ylim"])
        if p.get("xticks") is not None:
            ax.set_xticks(p["xticks"])
    for ax in list(axes.flat)[len(panels):]:
        ax.axis("off")
    h, lab = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=min(4, len(lab)), fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.10 if nrows == 1 else 0.06, 1, 1))
    plotstyle.stamp(fig, status, note)
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["panel", "series", "x", "y"], rows)


def bars_chart(out: Path, panels: List[Dict], status: str, note: str = "", ncols: int = 3, size=(12.5, 4.2),
               share_labels: bool = True):
    """panels: [{"title", "labels", "values", "colors", "xlabel", "fmt", "ref"}]; horizontal bars.  Bar labels are
    printed only in the first column when a row of panels shares them."""
    plotstyle.apply()
    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(size[0], size[1] * nrows), squeeze=False)
    rows = []
    for i, (ax, p) in enumerate(zip(axes.flat, panels)):
        n = len(p["values"])
        yy = np.arange(n)[::-1]
        vals = [0.0 if v is None else v for v in p["values"]]
        ax.barh(yy, vals, color=p.get("colors") or [C[0]] * n)
        ax.set_yticks(yy)
        first = panels[i - i % ncols]
        if share_labels and i % ncols > 0 and list(p["labels"]) == list(first["labels"]):
            ax.set_yticklabels([])
        else:
            ax.set_yticklabels(p["labels"], fontsize=8)
        fin = [v for v in vals if np.isfinite(v)]
        if fin and not p.get("xlim") and min(fin) >= 0:
            hi = max(max(fin), p.get("ref") or 0.0)
            ax.set_xlim(0, hi * 1.3 if hi > 0 else 1.0)
        fmt = p.get("fmt", "{:.2f}")
        for yv, v in zip(yy, p["values"]):
            if v is not None and np.isfinite(v):
                ax.text(v, yv, " " + fmt.format(v), va="center", fontsize=7.5, color=INK2)
        if p.get("ref") is not None:
            ax.axvline(p["ref"], color=MUTED, lw=1, ls="--")
        ax.set_title(p["title"], fontsize=9.5, loc="left")
        ax.set_xlabel(p.get("xlabel", ""))
        if p.get("xlim"):
            ax.set_xlim(*p["xlim"])
        ax.grid(axis="y", visible=False)
        for lab, v in zip(p["labels"], p["values"]):
            rows.append([p["title"], lab, v])
    for ax in list(axes.flat)[len(panels):]:
        ax.axis("off")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    plotstyle.stamp(fig, status, note)
    fig.savefig(out)
    plt.close(fig)
    write_csv(out.with_suffix(".csv"), ["panel", "label", "value"], rows)
