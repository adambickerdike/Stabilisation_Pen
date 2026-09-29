"""Figures of the Rev J.1 study, each with a CSV twin (same name, .csv) that holds the plotted numbers.

Palette: the dataviz reference palette's first four categorical slots in fixed order (blue #2a78d6, orange #eb6834,
aqua #1baf7a, yellow #eda100; validated with scripts/validate_palette.js, light surface: all checks pass, contrast WARN
for aqua and yellow, so every series is also labelled in text and the CSV twin is the table view).  One y-scale per
panel; small multiples where measures differ.
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, List

import numpy as np

from . import ensure_paths

ensure_paths()
from revj.figures import GRID, INK, INK2, MUTED, SURF, _mpl  # noqa: E402  (read-only reuse of the plot style)

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
LIMIT = "#52514e"


def _csv(path_png: str, header: List[str], rows: List[List]):
    with open(path_png.replace(".png", ".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _style(ax, title: str, xl: str, yl: str):
    ax.set_title(title, fontsize=9, color=INK, loc="left")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# --------------------------------------------------------------------------------------------------- P1 gimbal
def gimbal_figure(path_png: str, gm: Dict):
    plt = _mpl()
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.6), dpi=150)
    series = [("studyN_50um", "study N, 50 um, crossing at mid-length", S1),
              ("tension_near_end", "50 um, tension, crossing near the end (lambda 0.06, 5 mm)", S2),
              ("chosen_75um", "Rev J.1: 75 um, compression", S3)]
    rows = []
    for key, lab, col in series:
        d = gm["curves"][key]
        F = [r["F_N"] for r in d]
        k = [r["k_mNm_rad"] for r in d]
        e = [r["strain_usable"] * 1e3 for r in d]
        axs[0].plot(F, k, color=col, lw=1.6, marker="o", ms=4, label=lab)
        axs[1].plot(F, e, color=col, lw=1.6, marker="o", ms=4, label=lab)
        for r in d:
            rows.append([key, r["F_N"], r["k_mNm_rad"], r["strain_usable"]])
    for ax in axs:
        tr = ax.get_xaxis_transform()
        for xv, txt in ((-16.5, " pull 16.5 N\n (compression)"), (16.5, " pull 16.5 N\n (tension)")):
            ax.axvline(xv, color=LIMIT, lw=0.8, ls="--")
            ax.text(xv, 0.02, txt, transform=tr, fontsize=6.5, color=INK2, va="bottom")
    axs[1].axhline(1.8, color=LIMIT, lw=0.8)
    axs[1].text(axs[1].get_xlim()[0], 1.85, " fatigue allowable (study N's rule)", fontsize=7, color=INK2)
    _style(axs[0], "Pivot stiffness under the axial pull", "axial load on the pivot (N; tension > 0)", "stiffness (mN m/rad)")
    _style(axs[1], "Peak strip strain at the usable tilt", "axial load on the pivot (N; tension > 0)", "strain (x 1e-3)")
    axs[0].legend(fontsize=6.5, frameon=False, loc="upper right")
    fig.text(0.01, 0.01, "CALC: co-rotational beam model (revj1/gimbal.py). Study N's pivot buckles at 16.4 N of compression; "
             "the 75 um pivot at 55 N.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["design", "axial_load_N", "stiffness_mNm_per_rad", "peak_strain_at_usable_tilt"], rows)


# --------------------------------------------------------------------------------------------------- P2 battery
def battery_figure(path_png: str, bud: Dict):
    plt = _mpl()
    modes = ["steady_no_tremor", "steady_0.3mm", "steady_1mm", "guide", "lead", "autowrite_no_tremor", "autowrite_1mm",
             "autowrite_2mm"]
    names = ["steady, none", "steady, 0.3 mm", "steady, 1 mm", "guide", "lead-through", "autowrite, none",
             "autowrite, 1 mm", "autowrite, 2 mm"]
    revJ = bud["revJ"]["hours"]
    variants = [("Rev J", None, S1), ("Rev J.1", "x1_PMW3610_class", S3), ("Rev J.1, nose x2", "x2_PMW3610_class", S2),
                ("Rev J.1, nose x5", "x5_PMW3610_class", S4)]
    fig, ax = plt.subplots(figsize=(9.2, 3.8), dpi=150)
    x = np.arange(len(modes))
    wbar = 0.19
    rows = []
    for i, (lab, key, col) in enumerate(variants):
        lo, hi = [], []
        for m in modes:
            if key is None:
                h = revJ[m]
            else:
                h = bud["power"][key]["hours"]["LIR14500"][m]["h"]
            lo.append(h[0]); hi.append(h[1])
            rows.append([lab, m, h[0], h[1]])
        xs = x + (i - 1.5) * wbar
        ax.bar(xs, lo, width=wbar - 0.03, color=col, label=lab, edgecolor=SURF, lw=1.0)
        ax.errorbar(xs, lo, yerr=[np.zeros(len(lo)), np.array(hi) - np.array(lo)], fmt="none", ecolor=INK2, elinewidth=0.8,
                    capsize=2.0)
    ax.axhline(8.0, color=LIMIT, lw=0.9, ls="--")
    ax.text(len(modes) - 0.5, 8.2, "8 h target", fontsize=7, color=INK2, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=7, rotation=20, ha="right")
    _style(ax, "Battery life per mode, LIR14500 (bar: pessimistic end; whisker: up to the optimistic end)", "", "hours")
    ax.legend(fontsize=7, frameon=False, ncol=4, loc="upper right")
    fig.text(0.01, 0.01, "CALC on datasheet currents and round-1 SIM/CALC loads. 'x2', 'x5': nose-coil power multiplied (sim2j "
             "reported more in some runs; unconfirmed).", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["variant", "mode", "hours_low", "hours_high"], rows)


# --------------------------------------------------------------------------------------------------- P3 heat
def heat_figure(path_png: str, bud: Dict):
    plt = _mpl()
    ht = bud["heat"]
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=150)
    P = np.linspace(0.0, 0.6, 61)
    room = ht["web"]["room_C"]
    rows = []
    for lab, R, col in (("no spreader", ht["bare_R_K_W"], S1), ("graphite 0.1 x 30 mm (chosen)", ht["chosen_R_K_W"], S3)):
        ax.plot(P * 1e3, room + P * R, color=col, lw=1.8, label=lab)
        rows += [[lab, p, room + p * R] for p in P]
    for lim, txt, dy, va in ((ht["web"]["limit_C"], "43 degC, continuously held (ECMA-287)", 0.5, "bottom"),
                             (ht["web"]["target_C"], "41 degC design target", -0.5, "top")):
        ax.axhline(lim, color=LIMIT, lw=0.8, ls="--")
        ax.text(595, lim + dy, txt, fontsize=7, color=INK2, ha="right", va=va)
    nom = bud["power"]["x1_PMW3610_class"]["rows"]
    for m, lab in (("steady_1mm", "steady 1 mm"), ("autowrite_2mm", "autowrite 2 mm")):
        p = nom[m]["nose_coil_W"]
        ax.plot([p * 1e3], [room + p * ht["chosen_R_K_W"]], "o", ms=6, color=INK)
        ax.annotate(lab, (p * 1e3, room + p * ht["chosen_R_K_W"]), xytext=(-8, 8), textcoords="offset points", fontsize=7,
                    color=INK, ha="right")
    _style(ax, f"Skin at the web over the coils, {room:.0f} degC room", "coil loss (mW)", "surface (degC)")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    fig.text(0.01, 0.01, "CALC: fin model of the PEEK shell, no heat into the hand counted.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["case", "coil_loss_W", "web_C"], rows)


# --------------------------------------------------------------------------------------------------- P4 end-cap
def endcap_figure(path_png: str, em: Dict):
    plt = _mpl()
    fam = em["family"]
    ms = sorted(fam.values(), key=lambda v: v["mass_g"])
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=150)
    rows = []
    for sp, col in (("0.3", S1), ("0.5", S2), ("0.7", S3)):
        xs = [v["mass_g"] for v in ms if sp in v["tune_further_reduction"]]
        ys = [v["tune_further_reduction"][sp] * 100 for v in ms if sp in v["tune_further_reduction"]]
        ax.plot(xs, ys, color=col, lw=1.6, marker="o", ms=4, label=f"split {sp}, tuning seeds")
        rows += [["tune", sp, x_, y_] for x_, y_ in zip(xs, ys)]
    ver = (em.get("test") or {}).get("verdicts") or {}
    ref = em["studyK_45g"]["verdict"]
    pts = [(em["studyK_45g"]["design_mass_g"], ref)] + [(v["mass_g"], v) for v in ver.values()]
    for mass, v in pts:
        for sp, col in (("0.3", S1), ("0.5", S2), ("0.7", S3)):
            y_ = v.get(f"r{sp}")
            if y_ is None:
                continue
            ax.plot([mass], [y_ * 100], marker="D", ms=6, color=col, mec=INK, mew=0.6, ls="none")
            rows.append(["test", sp, mass, y_ * 100])
    ax.axhline(10, color=LIMIT, lw=0.8, ls="--")
    ax.text(21.5, 10.4, "R-T1: 10 % at split 0.5", fontsize=7, color=INK2)
    ax.axhline(5, color=LIMIT, lw=0.8, ls=":")
    ax.text(21.5, 5.4, "R-T1: 5 % at 0.3 and 0.7", fontsize=7, color=INK2)
    _style(ax, "End-cap: further reduction on top of the nose (8-12 Hz, 1-2 mm)", "end-cap mass (g)", "further reduction (%)")
    ax.legend(fontsize=7, frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.45))
    fig.text(0.01, 0.01, "SIM: study K's model H1 (Rev H pen), lines = tuning seeds, diamonds = test seeds.", fontsize=6.5,
             color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["seeds", "split", "endcap_mass_g", "further_reduction_pct"], rows)


# --------------------------------------------------------------------------------------------------- P5 visibility
def visibility_figure(path_png: str, vis: Dict):
    plt = _mpl()
    order = [k for k in ("revJ", "open_180", "clear_sleeve_15_w120", "clear_sleeve_15_w120_ring", "no_front") if k in vis["options"]]
    labels = {"revJ": "Rev J (C 120 deg, 10 mm)", "open_180": "opened to 180 deg",
              "clear_sleeve_15_w120": "clear sleeve, 15 mm (chosen)", "clear_sleeve_15_w120_ring": "+ sapphire ring top",
              "no_front": "no ring or sleeve (bound)"}
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=150)
    y = np.arange(len(order))
    rows = []
    a = [vis["options"][k]["share_within_1mm"] * 100 for k in order]
    b = [vis["options"][k]["share_within_3mm"] * 100 for k in order]
    ax.barh(y + 0.18, a, height=0.34, color=S1, label="ink visible within 1 mm")
    ax.barh(y - 0.18, b, height=0.34, color=S2, label="within 3 mm")
    for i, k in enumerate(order):
        rows.append([k, a[i], b[i]])
        ax.text(a[i] + 1, y[i] + 0.18, f"{a[i]:.0f} %", va="center", fontsize=7, color=INK)
        ax.text(b[i] + 1, y[i] - 0.18, f"{b[i]:.0f} %", va="center", fontsize=7, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[k] for k in order], fontsize=7)
    ax.set_xlim(0, 100)
    _style(ax, "Share of tilt x eye cases with the fresh ink visible", "share of cases (%)", "")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    fig.text(0.01, 0.01, "CALC: ray casting; tilts 35-75 deg, eye elevation 40-70 deg, azimuth 0-60 deg (ASSUMPTION range).",
             fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["option", "share_within_1mm_pct", "share_within_3mm_pct"], rows)


# --------------------------------------------------------------------------------------------------- P6 detent
def detent_figure(path_png: str, det: Dict):
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=150)
    mv = det["moving_back"]
    xs = [r["moved_back_mm"] for r in mv]
    ys = [r["torque_amp_mNm"] * 1e3 for r in mv]
    ax.plot(xs, ys, color=S1, lw=1.8, marker="o", ms=5, label="motors moved back (free space)")
    fr = 0.011e3
    ax.axhline(fr, color=LIMIT, lw=0.8, ls="--")
    ax.text(max(xs), fr * 1.08, "motor static friction 0.011 mN m (MFR)", fontsize=7, color=INK2, ha="right")
    ax.axhline(det["revJ_bound_mNm"] * 1e3, color=LIMIT, lw=0.8, ls=":")
    ax.text(max(xs), det["revJ_bound_mNm"] * 1e3 * 1.08, "Rev J bound 0.080 mN m", fontsize=7, color=INK2, ha="right")
    ax.set_yscale("log")
    _style(ax, "Cap torque on a heel-motor rotor", "motors moved back (mm)", "torque amplitude (uN m)")
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    rows = [["moved_back_mm", x_, y_] for x_, y_ in zip(xs, ys)]
    fig.text(0.01, 0.01, "CALC: magpylib, free space (the coil plate's iron would lower it); vector-averaged transverse field.",
             fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path_png)
    plt.close(fig)
    _csv(path_png, ["case", "moved_back_mm", "torque_uNm"], rows)


def all_figures(out_dir: str, gm: Dict, bud: Dict, em: Dict, vis: Dict, det: Dict) -> List[str]:
    paths = []
    for name, fn, arg in (("fig_revJ1_gimbal.png", gimbal_figure, gm), ("fig_revJ1_battery.png", battery_figure, bud),
                          ("fig_revJ1_heat.png", heat_figure, bud), ("fig_revJ1_endcap.png", endcap_figure, em),
                          ("fig_revJ1_visibility.png", visibility_figure, vis), ("fig_revJ1_detent.png", detent_figure, det)):
        p = os.path.join(out_dir, name)
        fn(p, arg)
        paths.append(p)
    return paths
