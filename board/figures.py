"""Figures for the guidance-board study; every PNG has a CSV twin with the plotted data."""
from __future__ import annotations

import csv
import os

import numpy as np

from stabpen import plotstyle as ps

ps.apply()
import matplotlib.pyplot as plt  # noqa: E402


def _csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def force_vs_gap(out_dir, rows, diam_rows, zlift_rows, design_gaps=(("A4", 3.7), ("A5", 2.7)), zlift=(3.7, 15.7),
                 status="CALC (magpylib 5.2; nothing measured)"):
    allr = sorted(rows + zlift_rows, key=lambda r: r["gap_mm"])
    g = np.array([r["gap_mm"] for r in allr])
    iso = np.array([r["lateral_isotropic_N"] for r in allr])
    best = np.array([r["lateral_best_direction_N"] for r in allr])
    fz0 = np.array([-r["normal_at_zero_lateral_N"] for r in allr])
    dg = np.array([r["gap_mm"] for r in diam_rows])
    dacross = np.array([r["across_azimuth_lateral_N"] for r in diam_rows])
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
    for ax in axs:
        ax.axvspan(0.5, 3.0, color=ps.GRID, alpha=0.6, lw=0)
        ax.axvspan(zlift[0], zlift[1], ymin=0.0, ymax=0.04, color=ps.SEQ_BLUE[2], lw=0)
        for name, dgap in design_gaps:
            ax.axvline(dgap, color=ps.INK2, lw=1, ls=":")
    ax = axs[0]
    ax.plot(g, best, color=ps.SERIES[0], lw=2, label="axial head, best direction")
    ax.plot(g, iso, color=ps.SERIES[0], lw=2, ls="--", label="axial head, weakest direction")
    ax.plot(dg, dacross, color=ps.SERIES[1], lw=2, label="diametric head (variant)")
    ax.plot(g, iso, **ps.marker_kw(ps.SERIES[0]))
    ax.axhline(0.40, color=ps.MUTED, lw=1, ls="-.")
    ax.set_ylim(0, max(best.max(), dacross.max() if len(dacross) else 0) * 1.08)
    ax.set_xlim(0, g.max() + 0.5)
    top = ax.get_ylim()[1]
    ax.text(g.max() * 0.55, 0.45, "software cap 0.40 N", fontsize=8, color=ps.INK2)
    ax.text(0.55, top * 0.03 + 0.05, "range asked:\n0.5-3 mm", fontsize=7.5, color=ps.INK2)
    for name, dgap in design_gaps:
        ax.text(dgap + 0.15, top * 0.55, f"{name} design gap {dgap:g} mm", fontsize=7.5, color=ps.INK2, rotation=90, va="center")
    ax.text(zlift[0] + 0.3, top * 0.07, "Z-lift range (guidance level)", fontsize=7.5, color=ps.INK2)
    ax.set_xlabel("gap: paper top to head-magnet top (mm)")
    ax.set_ylabel("lateral force available at the pen (N)")
    ax.set_title("Lateral force vs gap (pen at 50 deg)", loc="left")
    ax.legend(loc="upper right")
    ax = axs[1]
    ax.plot(g, fz0, color=ps.SERIES[2], lw=2, label="axial head under the zero-force point")
    ax.plot(g, fz0, **ps.marker_kw(ps.SERIES[2]))
    ax.axhline(1.0, color=ps.MUTED, lw=1, ls="-.")
    ax.set_ylim(0, fz0.max() * 1.08)
    ax.set_xlim(0, g.max() + 0.5)
    ax.text(g.max() * 0.5, 1.12, "writer's own normal force ~1 N", fontsize=8, color=ps.INK2)
    ax.set_xlabel("gap (mm)")
    ax.set_ylabel("extra normal pull on the pen (N)")
    ax.set_title("The price: the head also pulls the pen down", loc="left")
    ax.legend(loc="upper right")
    ps.stamp(fig, status, "head K&J D88-N52 (AMF-90); pen magnet K&J D42-N52 (AMF-91), 3.8 mm above the paper")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(out_dir, "fig_force_vs_gap.png")
    fig.savefig(p)
    plt.close(fig)
    rows_csv = []
    for r in allr:
        rows_csv.append([r["gap_mm"], r["lateral_isotropic_N"], r["lateral_best_direction_N"], -r["normal_at_zero_lateral_N"],
                         r["max_normal_pull_N"], r["slope_at_zero_N_per_mm"], "", ""])
    for r in diam_rows:
        rows_csv.append([r["gap_mm"], "", "", "", "", "", r["across_azimuth_lateral_N"], r["along_azimuth_normal_N"]])
    _csv(os.path.join(out_dir, "fig_force_vs_gap.csv"),
         ["gap_mm", "axial_lateral_isotropic_N", "axial_lateral_best_direction_N", "axial_normal_pull_at_zero_lateral_N",
          "axial_max_normal_pull_N", "axial_slope_at_zero_N_per_mm", "diametric_lateral_across_azimuth_N",
          "diametric_normal_along_azimuth_N"], rows_csv)
    return p


def force_vs_position(out_dir, X, Y, F_margin, F_nomargin, paper, travel, status="CALC (magpylib; plate theory)"):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 6.2), sharey=True)
    vmax = float(np.nanmax(F_margin))
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("seq", ps.SEQ_BLUE)
    for ax, F, title in ((axs[0], F_margin, "Head travel = page + 12 mm (design)"),
                         (axs[1], F_nomargin, "Head travel = page only")):
        im = ax.pcolormesh(X, Y, F, cmap=cmap, vmin=0.0, vmax=vmax, shading="auto")
        x0, y0, w, h = paper
        ax.plot([x0, x0 + w, x0 + w, x0, x0], [y0, y0, y0 + h, y0 + h, y0], color=ps.INK, lw=1.2)
        ax.set_aspect("equal")
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_xlabel("x (mm), board frame")
        ax.grid(False)
    axs[0].set_ylabel("y (mm), away from the writer")
    cb = fig.colorbar(im, ax=axs, fraction=0.03, pad=0.02)
    cb.set_label("lateral force available in every direction (N)")
    fig.suptitle("Force available over an A4 page (pen at 50 deg, 10 N hand load at the pen)", x=0.02, ha="left", fontsize=11)
    ps.stamp(fig, status, "gap 2.7 mm minus glass sag; weakest direction")
    p = os.path.join(out_dir, "fig_force_vs_position.png")
    fig.savefig(p)
    plt.close(fig)
    rows = [[float(x), float(y), float(a), float(b)] for x, y, a, b in zip(X.ravel(), Y.ravel(), F_margin.ravel(), F_nomargin.ravel())]
    _csv(os.path.join(out_dir, "fig_force_vs_position.csv"),
         ["x_mm", "y_mm", "lateral_isotropic_N_travel_page_plus_12mm", "lateral_isotropic_N_travel_page_only"], rows)
    return p


def force_cuts(out_dir, cut_x, cut_y, status="CALC (magpylib)"):
    """cut_x/cut_y: (offsets, F (n,3)) for head offsets across / along the pen azimuth."""
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.2))
    ox, Fx = cut_x
    oy, Fy = cut_y
    axs[0].plot(ox, Fx[:, 0], color=ps.SERIES[0], label="offset across the pen azimuth (x)")
    axs[0].plot(oy, Fy[:, 1], color=ps.SERIES[1], label="offset along the pen azimuth (y)")
    axs[0].axhline(0, color=ps.BASELINE, lw=1)
    axs[0].set_xlabel("head offset from the pen magnet (mm)")
    axs[0].set_ylabel("lateral force on the pen along the offset (N)")
    axs[0].set_title("Pull toward the head", loc="left")
    axs[0].legend(loc="upper left")
    axs[1].plot(ox, -Fx[:, 2], color=ps.SERIES[0], label="offset across the azimuth")
    axs[1].plot(oy, -Fy[:, 2], color=ps.SERIES[1], label="offset along the azimuth")
    axs[1].axhline(0, color=ps.BASELINE, lw=1)
    axs[1].set_xlabel("head offset from the pen magnet (mm)")
    axs[1].set_ylabel("normal pull on the pen, down positive (N)")
    axs[1].set_title("Normal pull", loc="left")
    axs[1].legend(loc="upper right")
    ps.stamp(fig, status, "design gap 2.7 mm; pen at 50 deg, rear toward the writer (-y)")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(out_dir, "fig_force_cuts.png")
    fig.savefig(p)
    plt.close(fig)
    rows = [["across", float(o), *map(float, f)] for o, f in zip(ox, Fx)] + [["along", float(o), *map(float, f)] for o, f in zip(oy, Fy)]
    _csv(os.path.join(out_dir, "fig_force_cuts.csv"), ["cut", "offset_mm", "Fx_N", "Fy_N", "Fz_N"], rows)
    return p


def hand_deflection(out_dir, freqs, curves, status="CALC (HAP-26 hand model)"):
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labels = {"relaxed": "relaxed (HAP-26 nominal)", "relaxed_compliant": "relaxed, soft (HAP-26 lower CI)",
              "lightly_resisting": "lightly resisting (stiff arm)", "hand_held_still": "hand held still (grip only)"}
    for k, (name, y) in enumerate(curves.items()):
        ax.plot(freqs, y, color=ps.SERIES[k], label=labels.get(name, name))
    ax.set_xlabel("frequency of the guidance force (Hz)")
    ax.set_ylabel("pen deflection per 0.1 N (mm)")
    ax.set_title("How far 0.1 N moves the pen in the hand", loc="left")
    ax.legend(loc="upper right")
    ax.set_xlim(0, max(freqs))
    ax.set_ylim(0, None)
    ps.stamp(fig, status, "passive writer; paper friction not included")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(out_dir, "fig_hand_deflection.png")
    fig.savefig(p)
    plt.close(fig)
    rows = [[float(f)] + [float(curves[n][i]) for n in curves] for i, f in enumerate(freqs)]
    _csv(os.path.join(out_dir, "fig_hand_deflection.csv"), ["f_Hz"] + [f"{n}_mm_per_0.1N" for n in curves], rows)
    return p


def guidance_examples(out_dir, panels, status="SIMULATION (synthetic paths, HAP-26 hand model; nothing measured)"):
    """panels: list of (title, list of (label, style_key, xy array))."""
    style = {"template": dict(color=ps.MUTED, lw=1.5, ls="--"),
             "intended": dict(color=ps.SERIES[3], lw=1.5),
             "ink_off": dict(color=ps.SERIES[1], lw=1.8),
             "ink_guided": dict(color=ps.SERIES[0], lw=1.8),
             "ink_lead": dict(color=ps.SERIES[2], lw=1.8)}
    fig, axs = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 5.6))
    rows = []
    for ax, (title, series) in zip(np.atleast_1d(axs), panels):
        seen = set()
        for label, key, xy in series:
            kw = dict(style[key])
            ax.plot(xy[:, 0], xy[:, 1], label=None if label in seen else label, **kw)
            seen.add(label)
            for x, y in xy[::5]:
                rows.append([title, label, float(x), float(y)])
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_xlabel("x (mm)")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=7.5)
    np.atleast_1d(axs)[0].set_ylabel("y (mm)")
    ps.stamp(fig, status)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(out_dir, "fig_guidance_sim.png")
    fig.savefig(p)
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_guidance_sim.csv"), ["panel", "series", "x_mm", "y_mm"], rows)
    return p
