r"""Figures of study W, each with a CSV twin (same name, .csv) holding the plotted numbers.

Palette (dataviz skill reference instance, light mode; categorical slots in fixed order, never cycled): designs are
coloured by identity with the same colour on every figure; text stays in ink colours; one y-axis per panel; a legend
for two or more series plus selective direct labels.  Evidence labels are printed on every figure.
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import RESULTS

SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8985"
GRID = "#e4e3df"
SURF = "#fcfcfb"
GREY = "#b9b8b3"


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": GREY, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.titlecolor": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
                         "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                         "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})
    return plt


def _grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def write_csv(path: str, header: Sequence[str], rows: Sequence[Sequence]):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def save(fig, name: str, header, rows, outdir: str = RESULTS):
    os.makedirs(outdir, exist_ok=True)
    png = os.path.join(outdir, name + ".png")
    fig.savefig(png, dpi=150, bbox_inches="tight")
    write_csv(os.path.join(outdir, name + ".csv"), header, rows)
    return png


def _evidence(fig, text: str):
    fig.text(0.01, -0.02, text, fontsize=7, color=MUTED, ha="left", va="top")


# ------------------------------------------------------------------------------------------------ headline
def headline(table: List[Dict], designs: List[str], colors: Dict[str, str], name: str = "fig_w_headline",
             evidence: str = "SIMULATION (sim2, H1 hand, synthetic writers; recorded PD waveform where marked); nothing measured"):
    """table rows: {class, design, tip_mm, words10}; two panels: tip tremor (mm) and words readable (of 10)."""
    plt = _mpl()
    classes = []
    for r in table:
        if r["class"] not in classes:
            classes.append(r["class"])
    nC, nD = len(classes), len(designs)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 0.55 * nC * nD / 2 + 1.6), sharey=True)
    h = 0.8 / nD
    rows = []
    for j, dz in enumerate(designs):
        ys, tips, words = [], [], []
        for i, c in enumerate(classes):
            rr = [r for r in table if r["class"] == c and r["design"] == dz]
            if not rr:
                continue
            y = i + (j - (nD - 1) / 2) * h
            ys.append(y)
            tips.append(rr[0]["tip_mm"])
            words.append(rr[0]["words10"])
            rows.append([c, dz, rr[0]["tip_mm"], rr[0]["words10"]])
        axs[0].barh(ys, tips, height=h * 0.9, color=colors[dz], label=dz, edgecolor=SURF, linewidth=1.0)
        axs[1].barh(ys, words, height=h * 0.9, color=colors[dz], edgecolor=SURF, linewidth=1.0)
        for y, v in zip(ys, tips):
            axs[0].text(v + 0.05, y, f"{v:.1f}", va="center", fontsize=7, color=INK2)
        for y, v in zip(ys, words):
            axs[1].text(v + 0.1, y, f"{v:.0f}", va="center", fontsize=7, color=INK2)
    axs[0].set_yticks(range(nC))
    axs[0].set_yticklabels(classes)
    axs[0].invert_yaxis()
    axs[0].set_xlabel("tremor at the pen tip (mm, peak)")
    axs[1].set_xlabel("words readable (out of 10)")
    axs[1].set_xlim(0, 10.8)
    axs[0].set_title("How much the ink still shakes")
    axs[1].set_title("How many words the app can read")
    for ax in axs:
        _grid(ax, "x")
    axs[0].legend(loc="lower right", fontsize=8)
    _evidence(fig, evidence)
    fig.tight_layout()
    return save(fig, name, ["class", "design", "tip_tremor_mm", "words_readable_of_10"], rows)


# ------------------------------------------------------------------------------------------------ writing pictures
def writing(samples: List[Dict], name: str = "fig_w_writing",
            evidence: str = "SIMULATION: the same synthetic writer, sentence and tremor with each pen; grey = the letters the writer meant; true scale, 8 mm lines"):
    """samples: {row, col, title, intended [[x, y, down]], ink [[x, y, down]], caption}; rows = tremor classes, cols =
    designs.  Strokes drawn at true scale (mm) on ruled lines."""
    plt = _mpl()
    rows_ = sorted({s["row"] for s in samples})
    cols_ = sorted({s["col"] for s in samples})
    fig, axs = plt.subplots(len(rows_), len(cols_), figsize=(4.3 * len(cols_), 1.25 * len(rows_) + 0.4), squeeze=False)
    out = []
    for s in samples:
        ax = axs[rows_.index(s["row"]), cols_.index(s["col"])]
        it = np.asarray(s["intended"], float)
        ink = np.asarray(s["ink"], float)
        x0 = np.nanmin(it[:, 0])
        y0 = np.nanmedian(it[it[:, 2] > 0.5, 1]) if np.any(it[:, 2] > 0.5) else 0.0
        for arr, col, lw in ((it, "#c9c8c3", 2.2), (ink, INK, 0.7)):
            pen = arr[:, 2] > 0.5
            segs = np.split(np.arange(len(arr)), np.flatnonzero(np.diff(pen.astype(int)) != 0) + 1)
            for sg in segs:
                if len(sg) > 1 and pen[sg[0]]:
                    ax.plot(arr[sg, 0] - x0, arr[sg, 1] - y0, color=col, linewidth=lw, solid_capstyle="round")
        for yl in (-2.0, 6.0):
            ax.axhline(yl, color="#9ec5f4", linewidth=0.6)
        ax.set_aspect("equal")
        ax.set_xlim(-3, max(np.nanmax(it[:, 0]) - x0 + 3, 20))
        ax.set_ylim(-9, 12)
        ax.axis("off")
        ax.set_title(s["title"], fontsize=8, loc="left", color=INK)
        ax.text(0, -8.5, s.get("caption", ""), fontsize=7, color=INK2)
        out.append([s["row"], s["col"], s["title"], s.get("caption", "")])
    _evidence(fig, evidence)
    fig.tight_layout()
    return save(fig, name, ["row", "col", "title", "caption"], out)


# ------------------------------------------------------------------------------------------------ design curves
def lines(series: Dict[str, Dict], xlabel: str, ylabel: str, title: str, name: str, evidence: str, logy: bool = False,
          hlines: Optional[List] = None, colors: Optional[Dict[str, str]] = None, ylim=None):
    """series: {label: {"x": [...], "y": [...]}}."""
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    rows = []
    for i, (lab, v) in enumerate(series.items()):
        c = (colors or {}).get(lab, SLOT[i % len(SLOT)])
        ax.plot(v["x"], v["y"], color=c, linewidth=2.0, marker="o", markersize=4, label=lab)
        ax.text(v["x"][-1], v["y"][-1], "  " + lab, fontsize=7, color=INK2, va="center")
        rows += [[lab, x, y] for x, y in zip(v["x"], v["y"])]
    for hl in (hlines or []):
        ax.axhline(hl[0], color=MUTED, linewidth=1.0, linestyle="--")
        ax.text(ax.get_xlim()[0], hl[0], " " + hl[1], fontsize=7, color=MUTED, va="bottom")
    if logy:
        ax.set_yscale("log")
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    _grid(ax)
    ax.legend(fontsize=7, loc="best")
    _evidence(fig, evidence)
    fig.tight_layout()
    return save(fig, name, ["series", "x", "y"], rows)


# ------------------------------------------------------------------------------------------------ the system picture
def system(d: Dict, name: str = "fig_w_system",
           evidence: str = "PROPOSED DESIGN (sizes CALC from designs.py); an illustration, not a drawing for manufacture"):
    """A labelled side view of the recommended pen: what moves, what pushes, what it does to the ink."""
    plt = _mpl()
    from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle, Circle, Ellipse
    fig, ax = plt.subplots(figsize=(11, 4.4))
    th = math.radians(50)
    a = np.array([math.cos(th), math.sin(th)])
    n = np.array([-math.sin(th), math.cos(th)])

    def P(z, r=0.0):
        return a * z + n * r

    # paper
    ax.plot([-40, 230], [0, 0], color=GREY, linewidth=1.5)
    ax.text(-38, -6, "paper", fontsize=8, color=INK2)
    # pen body (0-145) and tail module
    L = 144.7
    Lt = d["length_mm"]
    od = d["od_mm"]
    body = [P(10, -11.65), P(50, -12), P(L, -12), P(L, 12), P(50, 12), P(10, 11.65)]
    ax.add_patch(Polygon(body, closed=True, facecolor="#e9f1fb", edgecolor=SLOT[0], linewidth=1.2))
    tail = [P(L, -od / 2), P(L + Lt, -od / 2), P(L + Lt, od / 2), P(L, od / 2)]
    ax.add_patch(Polygon(tail, closed=True, facecolor="#fdeee6", edgecolor=SLOT[1], linewidth=1.2))
    # nose inside: from the gimbal (76.5) to the ball (0), deflected
    for q, alpha in ((0.0, 1.0), (6.6, 0.35), (-6.6, 0.35)):
        tip = np.array([0.0, 0.0]) + np.array([1, 0]) * q
        ax.plot([tip[0], P(76.5)[0]], [tip[1] + 0.5, P(76.5)[1]], color=INK, linewidth=1.2, alpha=alpha)
    ax.add_patch(Circle(P(76.5), 1.6, color=INK))
    # rotors (two discs seen edge-on, tilted +- delta)
    for j, zc in enumerate((L + Lt * 0.33, L + Lt * 0.67)):
        c = P(zc)
        for dd, al in ((0.0, 1.0), (0.6, 0.3), (-0.6, 0.3)):
            ang = th + math.pi / 2 + (dd if j == 0 else -dd)
            v = np.array([math.cos(ang), math.sin(ang)]) * d["rotor_r_o_mm"]
            ax.plot([c[0] - v[0], c[0] + v[0]], [c[1] - v[1], c[1] + v[1]], color=SLOT[1], linewidth=3.0, alpha=al,
                    solid_capstyle="round")
    # hand contact zones
    for z, lab in ((32, "finger pads"), (92, "thumb-index web")):
        c = P(z, 16)
        ax.add_patch(Ellipse(c, 16, 7, angle=math.degrees(th), facecolor="#f3e3d3", edgecolor=GREY, linewidth=0.8))
        ax.text(c[0] - 10, c[1] + 6, lab, fontsize=7, color=INK2)
    # arrows and labels
    def label(xy, txt, xyt, color=INK):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=8, color=color, arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))
    label((0, 0.5), "ink tip: moves up to 6.6 mm each way\nto cancel what is left of the tremor", (-40, 40))
    label(P(76.5), "nose pivot (Rev J)", (5, 95))
    label(P(L + Lt * 0.33), f"two tungsten rotors, {d['rotor_g']:.0f} g each, spinning\n{d['rpm']:.0f} rpm in opposite senses; tipping them\ntwists the whole pen and hand against the tremor", (150, 150))
    label(P(L + Lt, 0), f"gyro tail: {d['total_g']:.0f} g, {Lt:.0f} mm long, {od:.0f} mm across;\nit screws on in place of the rear cap", (210, 60))
    ax.add_patch(FancyArrowPatch(P(L + Lt + 8, -14), P(L + Lt + 8, 14), connectionstyle="arc3,rad=0.5",
                                 arrowstyle="<->", mutation_scale=10, color=SLOT[1], linewidth=1.2))
    ax.set_xlim(-45, 280)
    ax.set_ylim(-12, 190)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("The recommended pen: Rev J's moving nose + a detachable gyro tail", loc="left")
    _evidence(fig, evidence)
    fig.tight_layout()
    return save(fig, name, ["item", "value"], [["tail_mass_g", d["total_g"]], ["rotor_g", d["rotor_g"]], ["rpm", d["rpm"]],
                                                ["tail_length_mm", Lt], ["tail_od_mm", od]])
