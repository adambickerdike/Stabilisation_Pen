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
           evidence: str = "PROPOSED DESIGN (sizes CALC: wholepen/calc.py collar_geometry, collar_masses); an illustration, not a drawing for manufacture"):
    """A labelled side view of the recommended pen (the V2 collar): what the hand holds, what moves, what pushes."""
    plt = _mpl()
    from matplotlib.patches import FancyArrowPatch, Polygon, Circle, Ellipse
    fig, ax = plt.subplots(figsize=(11, 4.6))
    th = math.radians(50)
    a = np.array([math.cos(th), math.sin(th)])
    n = np.array([-math.sin(th), math.cos(th)])

    def P(z, r=0.0):
        return a * z + n * r

    zp = d["z_p_mm"]
    rb = d["barrel_od_mm"] / 2
    rc = d["collar_od_mm"] / 2
    zf, zr = d["z_front_mm"], d.get("z_end_mm", d["z_rear_mm"])
    L = d["length_mm"]
    phi = math.radians(d["swing_deg"])
    ax.plot([-40, 200], [0, 0], color=GREY, linewidth=1.5)
    ax.text(-38, -7, "paper", fontsize=8, color=INK2)
    # the inner barrel in three poses (centre and the two ends of its swing about the pivot)
    for ang, al in ((0.0, 1.0), (phi, 0.28), (-phi, 0.28)):
        R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
        piv = P(zp)
        pts = [P(3, -1.2), P(12, -rb), P(L, -rb), P(L, rb), P(12, rb), P(3, 1.2)]
        pts = [piv + R @ (p - piv) for p in pts]
        ax.add_patch(Polygon(pts, closed=True, facecolor="#e9f1fb" if ang == 0 else "none", edgecolor=SLOT[0], linewidth=1.2,
                             alpha=al))
    # the collar (sleeve) held by the fingers and resting in the web, with its skid ring on the paper
    col = [P(zf, -rc), P(zr, -rc), P(zr, rc), P(zf, rc)]
    ax.add_patch(Polygon(col, closed=True, facecolor="none", edgecolor=SLOT[2], linewidth=2.0))
    ax.add_patch(Polygon([P(zf - 0.5, -rc), P(9.5, -11.6), P(9.5, 11.6), P(zf - 0.5, rc)], closed=True, facecolor="none",
                         edgecolor=SLOT[2], linewidth=1.2, linestyle="--"))
    ax.add_patch(Circle(P(zp), 1.8, color=INK))
    for z, lab, dxy in ((32, "finger pads\nhold the collar", (-30, 6)), (92, "thumb-index web\nrests on the collar", (-34, 8))):
        c = P(z, rc + 4)
        ax.add_patch(Ellipse(c, 14, 6, angle=math.degrees(th), facecolor="#f3e3d3", edgecolor=GREY, linewidth=0.8))
        ax.text(c[0] + dxy[0], c[1] + dxy[1], lab, fontsize=7, color=INK2)

    def label(xy, txt, xyt):
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=8, color=INK, arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))
    label((0, 0.3), f"ink point: the whole inner pen swings it\n±{d['travel_mm']:.0f} mm (×1.3 across the page in the\ntilt plane)", (-95, 22))
    label(P(zp), f"2-axis flexure pivot,\n{zp:.0f} mm from the tip", (40, 20))
    label(P(zf + 1, -rc), f"skid ring on the collar carries\nthe writing force", (25, -9))
    label(P(75, -rc), f"collar {d['collar_od_mm']:.1f} mm across,\n{zr:.0f} mm long", (80, 38))
    label(P(60, 0), f"inner pen {d['barrel_od_mm']:.0f} mm across, {L:.0f} mm long:\nrefill, small fine nib, cell and board\nswing together", (-100, 75))
    label(P(95, 0), "coil plate in the collar's rear wall pushes on magnets\non the pen's end face: it swings the pen and pushes\nback on the collar and hand (Liftware principle)", (75, 95))
    ax.add_patch(Polygon([P(93, -rc + 0.8), P(97, -rc + 0.8), P(97, rc - 0.8), P(93, rc - 0.8)], closed=True, facecolor="#dff2ea",
                         edgecolor=SLOT[2], linewidth=1.0))
    ax.set_xlim(-100, 175)
    ax.set_ylim(-14, 118)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("The recommended pen: the whole inner pen swings inside a collar the hand holds", loc="left")
    _evidence(fig, evidence)
    fig.tight_layout()
    return save(fig, name, ["item", "value"], [[k, v] for k, v in d.items()])


# ------------------------------------------------------------------------------------------------ all figures
DESIGN_COLORS = {"none": "#8a8985", "nose": SLOT[0], "nose_gate": SLOT[3], "collar_nose": SLOT[2], "collar_fine": SLOT[5],
                 "gt_nose": SLOT[1], "gt_locked_nose": "#f4b99b", "nose_oracle": SLOT[6], "collar_nose_oracle": SLOT[4],
                 "collar_oracle": SLOT[7], "collar_locked": "#b9b8b3", "gt_locked": "#d9c7bd"}


def _load(n):
    import json
    p = os.path.join(RESULTS, n)
    return json.load(open(p)) if os.path.exists(p) else None


def fig_headline():
    """The four designs every class ran on both test writers, at the assumed classes and at study R's real classes."""
    from . import run_study as RS
    s = _load("summary.json")
    if not s:
        return None
    ds = ["none", "nose", "collar_nose", "collar_nose_oracle"]
    rr = [r for r in s["headline"]["rows"] + (s.get("headline_real") or {}).get("rows", [])
          if r["design"] in ds and r.get("n_writers", 2) >= 2]
    order = [c[0] for c in RS.CLASSES] + [c[0] for c in RS.CLASSES_REAL]
    rr.sort(key=lambda r: order.index(r["class"]))
    rows = [{"class": RS.CLASS_LABEL[r["class"]], "design": RS.LABELS[r["design"]], "tip_mm": r["tip_mm"], "words10": r["words10"]}
            for r in rr]
    colors = {RS.LABELS[d]: DESIGN_COLORS[d] for d in ds}
    return headline(rows, [RS.LABELS[d] for d in ds], colors,
                    evidence="SIMULATION (sim2, H1 hand, two synthetic test writers; synthetic tremor, a recorded NewHandPD waveform, and "
                             "study R's recorded PD tremor for the two 'Real PD' rows); nothing measured; the perfect-knowledge bars are a limit, not a result")


def fig_writing():
    """Before/after pictures from the saved traces (test writer 0)."""
    from . import BUILD
    from . import run_study as RS
    d = os.path.join(BUILD, "traces")
    if not os.path.isdir(d):
        return None
    samples = []
    cls_rows = ["ET_moderate", "ET_severe", "PD_severe"]
    des = ["none", "nose", "collar_nose", "collar_nose_oracle"]
    for i, c in enumerate(cls_rows):
        for j, dn in enumerate(des):
            fn = os.path.join(d, f"h1_g1_w0_s200_{c}_{dn}.npz")
            if not os.path.exists(fn):
                continue
            z = np.load(fn)
            t0, t1 = 4.3, 7.6                                     # the first two words ("return library")
            m = (z["t"] > t0) & (z["t"] < t1)
            mi = (z["it_t"] > t0) & (z["it_t"] < t1)
            ink = np.column_stack([z["ink"][m] * 1e3, z["contact"][m]])
            it = np.column_stack([z["it_xy"][mi] * 1e3, z["it_down"][mi]])
            samples.append({"row": i, "col": j, "title": f"{RS.CLASS_LABEL[c]} - {RS.LABELS[dn]}", "intended": it.tolist(),
                            "ink": ink.tolist(), "caption": ""})
    if not samples:
        return None
    return writing(samples)


def fig_collar_control():
    c = _load("calc.json")
    if not c:
        return None
    out = []
    for key, pen in (("collar_control_revJ", "Rev J inner pen"), ("collar_control_compact", "compact 12 mm barrel")):
        rows = c[key]["rows"]
        series = {}
        for web in (True, False):
            for g in (0.5, 1.0, 2.0):
                rr = sorted([r for r in rows if r["web_on_collar"] == web and r["grip_scale"] == g and r["r_rot"] == 0.5], key=lambda r: r["f"])
                lab = f"grip {g:g} x, web on {'collar' if web else 'barrel'}"
                series[lab] = {"x": [r["f"] for r in rr], "y": [r["transmission_min"] for r in rr]}
        cols = {f"grip {g:g} x, web on {'collar' if w else 'barrel'}": SLOT[k] for k, (w, g) in
                enumerate([(True, 0.5), (True, 1.0), (True, 2.0), (False, 0.5), (False, 1.0), (False, 2.0)])}
        out.append(lines(series, "tremor frequency (Hz)", "ink motion / (pivot-to-tip x angle), weakest axis",
                         f"Does the collar still move the ink? ({pen})", f"fig_w_collar_transmission_{'revj' if 'revJ' in key else 'compact'}",
                         "CALC (lin.py, V2 collar, split 0.5); 1 = the ideal lever; below 1 the grip or the web takes part of the motion",
                         colors=cols, hlines=[(1.0, "ideal")]))
    return out


def fig_tail_gate():
    c = _load("calc.json")
    if not c:
        return None
    rows = c["tail_gate"]["rows"]
    series = {}
    for mod in sorted({r["module"] for r in rows}):
        rr = [r for r in rows if r["module"] == mod and r["r_rot"] == 0.5 and r["f"] == 6.0 and r["A_mm"] == 3.0]
        rr = sorted(rr, key=lambda r: r["grip_scale"])
        series[mod] = {"x": [r["grip_scale"] for r in rr], "y": [100 * r["gain_vs_locked"] for r in rr]}
    return lines(series, "grip stiffness (x the nominal 575 N/m)", "improvement over the same mass locked (%)",
                 "Tail modules against the same mass locked (6 Hz, 3 mm)", "fig_w_tail_gate",
                 "CALC (lin.py, perfect knowledge of the tremor: an upper bound); dashed: the review's 10 % gate", hlines=[(10.0, "gate 10 %")])


def fig_cmg_energy():
    c = _load("calc.json")
    if not c:
        return None
    rows = c["cmg_sizing"]["rows"]
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    out = []
    for i, r in enumerate(rows):
        x, y = r["E_J_total"], r["tip_tremor_cancellable_5Hz_mm"]
        ax.plot([x], [y], "o", color=SLOT[i % len(SLOT)], markersize=7)
        ax.text(x * 1.05, y, "  " + r["name"].split(",")[0].replace("study W turret pair", "W pair"), fontsize=7, color=INK2, va="center")
        out.append([r["name"], x, y, r["h_Nms"]])
    ax.set_xscale("log")
    ax.set_xlabel("energy stored in the spinning rotors (J)")
    ax.set_ylabel("largest tip tremor it could cancel at 5 Hz (mm)")
    ax.set_title("Gyroscopes: what they could do against what they store")
    _grid(ax)
    _evidence(fig, "CALC (designs.py, calc.py; perfect knowledge, ±1 rad gimbals; a 100 g pen dropped from 1 m carries about 1 J)")
    fig.tight_layout()
    return save(fig, "fig_w_cmg_energy", ["design", "E_stored_J", "cancellable_5Hz_mm", "h_Nms"], out)


def fig_grips():
    from . import run_study as RS
    s = _load("summary.json")
    if not s:
        return None
    rr = s.get("tail_and_collar_vs_locked_grips", [])
    series = {}
    for act in ("collar_nose", "collar_oracle", "gt_nose"):
        v = sorted([r for r in rr if r["active"] == act], key=lambda r: r["grip"])
        if v:
            series[RS.LABELS[act]] = {"x": [r["grip"] for r in v], "y": [100 * r["gain_vs_locked"] for r in v]}
    if not series:
        return None
    return lines(series, "grip stiffness (x nominal)", "improvement over the same pen locked (%)",
                 "In the simulator: collar and gyro tail against the same mass locked", "fig_w_grips_sim",
                 "SIMULATION (tuning writer 100, ET 6 Hz 3 mm, seed 300)", hlines=[(10.0, "gate 10 %")],
                 colors={RS.LABELS[k]: DESIGN_COLORS[k] for k in ("collar_nose", "collar_oracle", "gt_nose")})


def fig_gate():
    from . import run_study as RS
    s = _load("summary.json")
    if not s:
        return None
    rows = [r for r in s["headline"]["rows"] if r["design"] in ("nose", "nose_gate")]
    plt = _mpl()
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    out = []
    cls = [c for c in s["headline"]["classes"] if any(r["class"] == c for r in rows)]
    for j, dn in enumerate(("nose", "nose_gate")):
        rr = [next((r for r in rows if r["class"] == c and r["design"] == dn), None) for c in cls]
        ys = np.arange(len(cls)) + (j - 0.5) * 0.4
        axs[0].barh(ys, [r["ink_err_um"] if r else 0 for r in rr], height=0.38, color=DESIGN_COLORS[dn], label=RS.LABELS[dn])
        axs[1].barh(ys, [100 * (r["coverage"] or 0) if r else 0 for r in rr], height=0.38, color=DESIGN_COLORS[dn])
        out += [[c, dn, r["ink_err_um"] if r else None, r["coverage"] if r else None] for c, r in zip(cls, rr)]
    for ax in axs:
        ax.set_yticks(range(len(cls)))
        ax.set_yticklabels([RS.CLASS_LABEL[c] for c in cls], fontsize=7)
        ax.invert_yaxis()
        _grid(ax, "x")
    axs[0].set_xlabel("ink error while inking (um)")
    axs[1].set_xlabel("share of the letters' ink laid (%)")
    axs[0].set_title("Writing only when in reach: the error drops...")
    axs[1].set_title("...because ink goes missing")
    axs[0].legend(fontsize=7, loc="lower right")
    _evidence(fig, "SIMULATION (test writers 0-1); coverage = share of the tremor-free run's inked samples also inked")
    fig.tight_layout()
    return save(fig, "fig_w_gate", ["class", "design", "ink_err_um", "coverage"], out)


def all_figures() -> Dict:
    from . import calc as K
    out = {}
    for nm, fn in (("headline", fig_headline), ("writing", fig_writing), ("collar_control", fig_collar_control),
                   ("tail_gate", fig_tail_gate), ("cmg_energy", fig_cmg_energy), ("grips", fig_grips), ("gate", fig_gate)):
        try:
            out[nm] = fn()
        except Exception as e:                                   # a missing input skips that figure only
            out[nm] = f"skipped: {type(e).__name__}: {e}"
    g = K.COLLAR_V2
    mm = K.collar_masses("coil")
    d = {"z_p_mm": 50.0, "barrel_od_mm": g["barrel_od"] * 1e3, "collar_od_mm": 21.7, "z_front_mm": g["z_front_v2"] * 1e3,
         "z_rear_mm": g["z_rear"] * 1e3, "z_end_mm": g["z_end_wall"] * 1e3, "length_mm": g["length"] * 1e3, "travel_mm": 4.0,
         "swing_deg": math.degrees(4.0 / 50.0), "total_g": round(mm["total_g"], 1)}
    out["system"] = system(d)
    return out
