"""Consistent, accessible static-figure style for engineering plots.

Palette: validated reference categorical order (validate_palette.js, light mode,
6 slots: all hard checks pass; slots 3-5 are below 3:1 contrast on the light
surface, so every figure ships with a legend and its data table as CSV/JSON).
Rules applied: one y-axis per panel, 2 px lines, >= 8 px markers with a surface
ring, solid hairline grid, text in ink colours (never the series colour),
categorical colours assigned in fixed order (never cycled past 8).

Every figure is also stamped with its evidence status (e.g. "ANALYTICAL
CALCULATION" or "SIMULATION") so a plot cannot be mistaken for a measurement.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "lines.markersize": 7,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "legend.labelcolor": INK2,
        "font.family": "sans-serif",
        "font.size": 9.5,
        "axes.prop_cycle": matplotlib.cycler(color=SERIES),
        "savefig.dpi": 160,
        "figure.dpi": 110,
    })


def stamp(fig, status: str, extra: str = ""):
    """Evidence-status footer on every figure."""
    txt = status.upper() + (" | " + extra if extra else "")
    fig.text(0.995, 0.005, txt, ha="right", va="bottom", fontsize=7, color=MUTED)


def marker_kw(color):
    return dict(marker="o", markersize=7, markerfacecolor=color, markeredgecolor=SURFACE,
                markeredgewidth=1.6, linestyle="none")
