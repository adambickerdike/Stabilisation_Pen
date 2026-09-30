"""Figures with CSV twins for study E (results/realtrack/fig_*.png + .csv).

Style: the project's validated palette (stabpen/plotstyle.py; this order checked with the dataviz validator, light mode:
ordinary pen orange, Rev H violet, Rev J gated blue, G4 yellow, the new design green, perfect knowledge magenta: all
hard checks pass; yellow and magenta below 3:1 contrast, so every chart has direct labels and a CSV table), one fixed
colour per pen in every chart, thin bars, hairline grids, a legend for two or more series, an evidence stamp.
The results-card charts and the before/after pictures reuse study R's plotting functions (realdata/figures.py, read-only:
its colour table is extended in memory for the new pens, nothing is written to realdata/).
Pictures: CC BY inputs only (UCI Character Trajectories letters, UCI PD spiral tremor, Zenodo ET tremor); UNIPEN writing
is never drawn here (research use only).
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

SIM_TAG = "SIMULATION with real recorded inputs (model HW1)"
COL = {"none": "#eb6834", "revH_akf": "#4a3aa7", "revJ_gated": "#2a78d6", "revJ_g4": "#eda100", "revJ_new": "#008300",
       "revJ_oracle": "#e87ba4", "revJ_tcn": "#1baf7a", "revJ_held": "#898781"}
LABEL = {"none": "Ordinary pen", "revH_akf|deltapen": "Rev H tracker (R)", "revJ_gated|deltapen": "Rev J gated (R)",
         "revJ_tcn|deltapen": "Rev J + ai2 TCN (R)", "revJ_oracle": "Perfect knowledge (limit)",
         "revJ_g4|deltapen": "Rev J + G4 (sim2j)", "revJ_new|deltapen": "Rev J + best causal tracker (this study)",
         "revJ_held": "Rev J, nose held"}


def _register():
    from realdata import figures as FG
    for k, c in COL.items():
        FG.DEVICE_COLOR.setdefault(k, c)
        FG.DEVICE_COLOR.setdefault(k + "|deltapen", c)
    for k in list(FG.DEVICE_COLOR):
        base = k.split("|")[0]
        if base.startswith("revJ_info_"):
            FG.DEVICE_COLOR[k] = "#1baf7a"
    return FG


def write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence], comments: Sequence[str] = ()):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        for c in comments:
            f.write("# " + str(c).replace("\n", " ") + "\n")
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _plt():
    from stabpen import plotstyle as PS
    PS.apply()
    import matplotlib.pyplot as plt
    return plt, PS


# ------------------------------------------------------------------ results-card charts (R's functions)
def card_groups(ag: Dict, devices: Sequence[str], metric: str = "words_of_10") -> List[Dict]:
    kinds = {"PD": "Parkinson's", "ET": "Essential tremor", "all": "Both, pooled"}
    out = []
    for kind in ("all", "PD", "ET"):
        for cls in ("severe", "moderate", "mild"):
            cd = ag["real"].get(f"{kind}/{cls}")
            if not cd:
                continue
            g = {"label": f"{kinds[kind]}, {cls} ({cd['_amp_mm_mean']:.2f} mm)", "dev": {}, "bound": {}}
            for d in devices:
                v = cd.get(d, {}).get(metric if metric != "ratio" else "tip_tremor_ratio")
                if v and np.isfinite(v.get("mean", np.nan)):
                    g["dev"][d] = v
                b = cd.get(d.split("|")[0], {}).get(metric) if "|" in d else None
                if b and np.isfinite(b.get("mean", np.nan)):
                    g["bound"][d] = b["mean"]
            if metric == "words_of_10":
                c = cd.get("none", {}).get("clean_words_of_10")
                if c:
                    g["clean"] = c
            out.append(g)
    return out


def words_chart(od: Path, ag: Dict, devices: Sequence[str]) -> Path:
    FG = _register()
    groups = card_groups(ag, devices, "words_of_10")
    note = ("SIMULATION (model HW1) with real recorded inputs: 9 held-out writers (UNIPEN hpb2), held-out PD (UCI) and ET "
            "(Zenodo) patients, DeltaPen-class page sensor. Bars: mean readable words out of 10 (literal AI reader, TrOCR "
            "base); lines: 95 % interval over writers; black tick: the same notes without tremor. Groups without a bar for "
            "a pen were not read (reading budget). Not a measurement of any person.")
    return FG.words_ci_chart(od / "fig_words_read.png", groups, list(devices), LABEL,
                             "Words you can read out of 10, by tremor type and size (held-out test data)", note)


def tremor_chart(od: Path, ag: Dict, devices: Sequence[str]) -> Path:
    FG = _register()
    groups = card_groups(ag, [d for d in devices if d != "none"], "ratio")
    note = ("SIMULATION (model HW1) with real recorded inputs, test split. Tremor left at the tip: peak amplitude "
            "(sqrt(2) x RMS of the major axis) of ink minus intended, band f0 +- 2 Hz, as a share of the ordinary pen's; "
            "lines: 95 % interval over writers; power change = ratio^2 - 1 (negative = less tremor power).")
    return FG.tremor_left_chart(od / "fig_tremor_left.png", groups, [d for d in devices if d != "none"], LABEL,
                                "Tremor left at the pen tip, share of the ordinary pen's (held-out test data)", note)


# ------------------------------------------------------------------ the tuning trade-off
def tradeoff_chart(od: Path, fronts: Dict[str, List[Dict]], chosen: Optional[Dict] = None) -> Path:
    """fronts: {family label: [{'clean_um', 'severe_bb', 'severe_ratio'}]}: every tuning evaluation of each family (with
    its authority) as a faint point; each family's Pareto front as a step line with markers; the 20 um tuning limit and
    the 25 um DEC-055 line.  Two panels: the classical trackers, and the learned ones against the best classical front."""
    plt, PS = _plt()
    learned = [f for f in fronts if "TCN" in f]
    classical = [f for f in fronts if f not in learned]
    fig, axs = plt.subplots(1, 2, figsize=(12.8, 5.8), sharey=True)
    rows = []

    def front(pts):
        fx, fy, best = [], [], np.inf
        for p_ in sorted(pts, key=lambda q: q["clean_um"]):
            yi = 100 * p_["severe_ratio"]
            if yi < best:
                best = yi
                fx.append(max(p_["clean_um"], 1.05)); fy.append(yi)
        return fx, fy

    def draw(ax, fam, c, lw=2.0, ls="-", points=True, label=None):
        pts = fronts[fam]
        if points:
            ax.plot([max(p_["clean_um"], 1.05) for p_ in pts], [100 * p_["severe_ratio"] for p_ in pts],
                    **dict(PS.marker_kw(c), markersize=4.0, alpha=0.25))
        fx, fy = front(pts)
        if fx:
            xe = max(max(p_["clean_um"] for p_ in pts), fx[-1])
            ax.plot(fx + [xe], fy + [fy[-1]], color=c, linewidth=lw, linestyle=ls, drawstyle="steps-post",
                    label=label or fam)
            ax.plot(fx, fy, linestyle="none", marker="o", markersize=4.5, color=c)
    pal = [c for c in PS.SERIES if c.lower() != COL["revJ_new"].lower()]      # green is the frozen design's colour
    for i, fam in enumerate(classical):
        draw(axs[0], fam, pal[i % len(pal)])
    best_classical = "listening + soft confidence" if "listening + soft confidence" in fronts else None
    for i, fam in enumerate(learned):
        draw(axs[1], fam, ("#4a3aa7" if "real" in fam else COL["revJ_new"]))
    if best_classical:
        draw(axs[1], best_classical, PS.MUTED, lw=1.6, ls="--", points=False,
             label=f"{best_classical} (best classical, for reference)")
    for ax in axs:
        ax.axvline(25.0, color=PS.INK, linewidth=1.2)
        ax.axvline(20.0, color=PS.MUTED, linewidth=1.0, linestyle="--")
        ax.text(26.0, 111, "DEC-055: 25 um", fontsize=8.5, color=PS.INK, va="top")
        ax.text(19.0, 111, "rule T2: 20 um", fontsize=8.5, color=PS.INK2, va="top", ha="right")
        ax.axhline(100.0, color=PS.BASELINE, linewidth=1.0)
        ax.set_xscale("log")
        ax.set_xlim(1, 2000)
        ax.set_ylim(30, 113)
        ax.set_xlabel("clean real writing moved, um RMS (mean of the 10 tuning notes; log scale; 0 drawn at 1)")
        ax.legend(loc="lower left", fontsize=8.5)
    if chosen:
        axs[1].plot([chosen["clean_um"]], [100 * chosen["severe_ratio"]], marker="*", markersize=15, color=COL["revJ_new"],
                    markeredgecolor=PS.INK, linestyle="none", zorder=5)
        axs[1].annotate("frozen choice (full plant)", (chosen["clean_um"], 100 * chosen["severe_ratio"]),
                        xytext=(chosen["clean_um"] * 2.2, 100 * chosen["severe_ratio"] + 9), fontsize=8.5,
                        color=PS.INK, arrowprops=dict(arrowstyle="-", color=PS.INK2, linewidth=0.8))
    axs[0].set_ylabel("severe tremor left at the tip, % of the ordinary pen")
    axs[0].set_title("Classical trackers with their gates", loc="left")
    axs[1].set_title("Learned trackers with a soft size gate", loc="left")
    for fam in fronts:
        for p_ in fronts[fam]:
            rows.append([fam, p_["clean_um"], p_["severe_ratio"], p_["severe_bb"]])
    PS.stamp(fig, "SIMULATION (HW1 surrogate, tuning split)", "real inputs; not a measurement")
    fig.tight_layout()
    p = od / "fig_tuning_tradeoff.png"
    fig.savefig(p)
    plt.close(fig)
    write_csv(p.with_suffix(".csv"), ["family", "clean_writing_moved_um", "severe_tip_tremor_ratio",
                                      "severe_broadband_ratio_to_held"], rows,
              ["SIMULATION (model HW1 surrogate) on the tuning split, DeltaPen-class page sensor"])
    return p


# ------------------------------------------------------------------ why the gate cannot tell: detector and amplitude
def separability_chart(od: Path, dist: Dict[str, Dict[str, List[float]]]) -> Path:
    """dist: {feature label: {'clean': quantiles, 'severe': quantiles, ...}} with 'q' = the quantile levels.  ECDF-like
    step curves per level for each feature (two panels)."""
    plt, PS = _plt()
    feats = [k for k, v in dist.items() if isinstance(v, dict) and "clean" in v]
    fig, axs = plt.subplots(1, len(feats), figsize=(5.2 * len(feats), 4.4))
    axs = np.atleast_1d(axs)
    q = np.array(dist["q"])
    rows = []
    lev_col = {"clean": PS.SERIES[0], "moderate": PS.SERIES[2], "severe": PS.SERIES[1]}
    for ax, f in zip(axs, feats):
        for lev in ("clean", "moderate", "severe"):
            v = dist[f].get(lev)
            if v is None:
                continue
            vv = np.asarray(v, float)
            ok = vv > 0                                   # a ratio of 0 = the detector's window not yet full
            ax.plot(vv[ok], 100 * q[ok], color=lev_col[lev], marker="o", markersize=3,
                    label={"clean": "no tremor", "moderate": "moderate (0.24 mm)", "severe": "severe (1.72 mm)"}[lev])
            for qi, vi in zip(q, v):
                rows.append([f, lev, qi, vi])
        ax.set_title(f, loc="left", fontsize=10)
        ax.set_ylabel("% of pen-down time below")
        ax.set_xscale("log")
        ref = 1.0 if "mm" in f else 5.0
        ax.axvline(ref, color=PS.MUTED, linewidth=1.0, linestyle="--")
        ax.text(ref * 1.05, 101, f"{ref:g}{' mm' if 'mm' in f else ''}", fontsize=8, color=PS.INK2, va="bottom")
        ax.legend(loc="upper left" if "mm" in f else "lower right")
    fig.suptitle("To a tremor detector, clean real writing looks like moderate tremor; severe tremor differs mostly in "
                 "size (tuning split)", x=0.01, ha="left", fontsize=11)
    PS.stamp(fig, "SIMULATION (HW1, tuning split)", "real inputs")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    p = od / "fig_detector_separability.png"
    fig.savefig(p)
    plt.close(fig)
    write_csv(p.with_suffix(".csv"), ["feature", "level", "quantile", "value"], rows,
              ["SIMULATION (model HW1) with real inputs, tuning split, DeltaPen-class page sensor; pen-down ticks"])
    return p


# ------------------------------------------------------------------ delay
def delay_chart(od: Path, lag: Dict, decomp: Dict, sweeps: Dict[str, Dict]) -> Path:
    plt, PS = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
    rows = []
    ax = axs[0]
    levels = ["severe", "edge", "moderate", "mild"]
    names = {"severe": "severe 1.72 mm", "edge": "0.6 mm", "moderate": "moderate 0.24 mm", "mild": "mild 0.10 mm"}
    y = np.arange(len(levels))
    held = [100 * decomp["levels"][lv]["held"] for lv in levels]
    revh = [100 * decomp["levels"][lv]["revh"] for lv in levels]
    ax.barh(y - 0.18, held, height=0.34, color=COL["revJ_held"], label="Rev J, nose held (no tracker)")
    ax.barh(y + 0.18, revh, height=0.34, color=COL["revH_akf"], label="Rev J + Rev H tracker")
    for yi, a, b in zip(y, held, revh):
        ax.text(a + 0.3, yi - 0.18, f"{a:.1f} %", va="center", fontsize=8, color=PS.INK2)
        ax.text(b + 0.3, yi + 0.18, f"{b:.1f} %", va="center", fontsize=8, color=PS.INK2)
    ax.axvline(100, color=PS.INK, linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels([names[lv] for lv in levels])
    ax.invert_yaxis()
    ax.set_xlim(90, 115)
    ax.set_xlabel("tip tremor, % of the ordinary 12 g pen")
    ax.set_title("Most of 'Rev H makes it worse' is the heavier pen", loc="left", fontsize=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=2, fontsize=8, frameon=False)
    for lv, a, b in zip(levels, held, revh):
        rows.append(["decomposition", lv, "held", a])
        rows.append(["decomposition", lv, "revh", b])
    ax = axs[1]
    for i, (name, sw) in enumerate(sweeps.items()):
        off = [float(o) for o in sw["offsets_ms"]]
        v = [100 * sw["by_offset"][str(o)]["severe_ratio"] for o in sw["offsets_ms"]]
        c = COL["revH_akf"] if "Rev H" in name else COL["revJ_new"]
        lab = "frozen design (ai2's TCN + soft size gate)" if "chosen" in name else name
        ax.plot(off, v, color=c, label=lab)
        ax.plot(off, v, **PS.marker_kw(c))
        for o, vv in zip(off, v):
            rows.append(["horizon", name, o, vv])
    ax.axvline(0.0, color=PS.MUTED, linewidth=1.0, linestyle="--")
    ax.text(0.2, ax.get_ylim()[1], f"nominal = servo delay {lag['servo_group_delay_ms']:.1f} ms", fontsize=8,
            color=PS.INK2, va="top")
    ax.set_xlabel("prediction horizon minus the servo delay, ms")
    ax.set_ylabel("severe tip tremor, % of the ordinary pen")
    ax.set_title("More prediction does not remove it", loc="left", fontsize=10)
    ax.legend(loc="center right", fontsize=8)
    PS.stamp(fig, "SIMULATION (HW1, tuning split) and CALC (servo lag)", "real inputs")
    fig.tight_layout()
    p = od / "fig_delay.png"
    fig.savefig(p)
    plt.close(fig)
    write_csv(p.with_suffix(".csv"), ["panel", "series", "x", "value_pct"], rows,
              ["SIMULATION (model HW1) on the tuning split; ratios to the ordinary pen; horizon offsets in ms",
               f"servo lag (CALC): {lag['rows']}"])
    return p


# ------------------------------------------------------------------ before/after pictures (CC BY only)
def picture(od: Path, pr: Dict, new_key: str = "revJ_new|deltapen") -> Path:
    FG = _register()
    pc = pr["case"]
    n = pr["devices"]["none"]["words_total"]
    kind_txt = {"PD": "Parkinson's tremor recorded from a patient drawing on a tablet",
                "ET": "Essential tremor recorded from a patient's hand"}[pc["kind"]]
    cls_txt = f"{pc['class']} class ({pr['tremor']['amp_mm']:.2f} mm at the tip, {pr['tremor']['f0']:.1f} Hz)"
    dn, dj = pr["devices"]["none"], pr["devices"][new_key]
    panels = [
        {"title": "What the writer meant (the same note without tremor, ordinary pen)", "ink": pr["clean_path"],
         "caption": f"words you can read: {pr['clean']['words_read']} of {n}"},
        {"title": "With tremor, ordinary pen", "ink": pr["paths"]["none"],
         "caption": f"words you can read: {dn['words_read']} of {n}"},
        {"title": "With the same tremor, Rev J pen with this study's best causal tracker (realistic page sensor)",
         "ink": pr["paths"][new_key], "caption": f"words you can read: {dj['words_read']} of {n}"},
    ]
    do = pr["devices"].get("revJ_oracle")
    if do and "revJ_oracle" in pr.get("paths", {}):
        panels.append({"title": "With the same tremor, Rev J pen with perfect knowledge of the tremor (the nose's limit, "
                                "not a design)", "ink": pr["paths"]["revJ_oracle"],
                       "caption": f"words you can read: {do.get('words_read')} of {n}"})
    for p_ in panels:
        p_["baselines_mm"] = pr.get("baselines_mm") or []
    trem = (f"tremor: {'UCI Parkinson spiral tablet data (Isenkul et al. 2014, CC BY 4.0)' if pc['kind'] == 'PD' else 'Zenodo ET accelerometry (Pardo-Valencia, Ammann, Foffani 2026, CC BY 4.0)'}, "
            f"recording {pr['tremor']['rid']}, scaled to the {pc['class']} class")
    short = {"PD": "Parkinson's tremor", "ET": "Essential tremor"}[pc["kind"]]
    header = f"SIMULATION, not a measurement of a person. {short}, {cls_txt}."      # one line at the figure's width
    footer = (f"SIMULATION (model HW1) with real recorded inputs ({kind_txt}); the same writer, text and tremor in every panel; one "
              f"fixed scale (mm on the page, 10 mm bar). Writing: letters written by one real adult (UCI Character "
              f"Trajectories, Williams 2008, CC BY 4.0), placed on the line by the simulation. {trem}. Tremor left at "
              f"the tip (peak, f0 +- 2 Hz): ordinary pen {dn.get('tip_tremor_mm', float('nan')):.2f} mm, Rev J with "
              f"the tracker {dj.get('tip_tremor_mm', float('nan')):.2f} mm, perfect knowledge "
              f"{(do or {}).get('tip_tremor_mm', float('nan')):.2f} mm. Words read by an AI handwriting reader "
              f"(TrOCR, literal) standing in for a person. PROPOSED DESIGN, not built. Not an observed improvement of "
              f"any user.")
    name = f"fig_before_after_chartraj_{pc['kind'].lower()}_{pc['class']}.png"
    return FG.before_after(od / name, panels, header, footer)
