"""Figures of the Rev J integration, each with a CSV twin (same name, .csv).  CALC on a PROPOSED DESIGN.

Colours: the dataviz reference palette's first three categorical slots (blue #2a78d6, orange #eb6834, aqua #1baf7a;
validated all-pairs, light surface), ink #0b0b0b / #52514e, hairline grid #e1e0d9, surface #fcfcfb.
"""
from __future__ import annotations

import csv
import math
import os
from dataclasses import replace
from typing import Dict

import numpy as np

from . import ensure_paths
from . import frontend as FR

ensure_paths()
from opt.inertial import front_end as FE  # noqa: E402
from opt.inertial.revh import RevH  # noqa: E402

S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
PART_DARK, PART_MID, PART_LIGHT = "#3a3f44", "#8a939b", "#c9ced2"


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 8.5, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": "white",
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-"})
    return plt


# --------------------------------------------------------------------------------------------------- front end
def front_end_figure(path_png: str, fe: Dict, ps: Dict):
    plt = _mpl()
    from matplotlib.patches import Circle, Polygon
    R = fe["R_mm"]
    R_d = fe["R_d_mm"]
    nz = replace(FR.c1s_nose(), X=fe["X_nom_mm"])
    h = FR.Heel()
    dm = fe["dims"]
    ru = FR.RU
    fig, axs = plt.subplots(1, 3, figsize=(13.0, 4.1), constrained_layout=True)
    rows = []
    for ax, t in zip(axs, (35.0, 50.0, 75.0)):
        th = math.radians(t)
        a2 = np.array([math.cos(th), math.sin(th)])
        n2 = np.array([math.sin(th), -math.cos(th)])
        C = np.array([0.0, R * math.cos(th)])
        s_g = nz.z_p - FE.protrusion(50.0, R)
        G = C + s_g * a2

        def H(s, r):
            return C + s * a2 + r * n2
        ax.fill_between([-22, 26], -2.0, 0.0, color="#f0efec", zorder=0)
        ax.axhline(0.0, color=MUTED, lw=0.8)
        for sgn, alp in ((+1, 1.0), (-1, 0.35)):                      # paper side solid, top side faint (C opening)
            ring = [H(0, sgn * dm["ring_bore_r"]), H(0, sgn * R), H(ru.ring_len, sgn * R), H(ru.ring_len, sgn * dm["ring_bore_r"])]
            ax.add_patch(Polygon(ring, closed=True, fc=PART_DARK, ec="none", alpha=alp, zorder=3))
            slv = [H(ru.ring_len, sgn * dm["sleeve_bore_r"]), H(ru.ring_len, sgn * R), H(3.0, sgn * 12.0), H(24.0, sgn * 12.0),
                   H(24.0, sgn * dm["sleeve_bore_r"])]
            ax.add_patch(Polygon(slv, closed=True, fc=PART_MID, ec="none", alpha=0.35 * alp, zorder=2))
        # heel: wheel (drawn resting on the paper: its spring takes the 0.35 mm protrusion), crown, pod
        n_pen = math.cos(math.radians(h.theta0)) * (-n2) + math.sin(math.radians(h.theta0)) * a2
        cpt = H(0.0, R_d)
        cpt = np.array([cpt[0], 0.0])
        wc = cpt + h.r_e * n_pen
        ax.add_patch(Circle(wc, h.r_e, fc=S3, ec="none", zorder=5))
        e1 = np.array([n_pen[1], -n_pen[0]])
        cr0, cr1 = cpt + 2 * h.r_e * n_pen, cpt + (2 * h.r_e + h.cap_h) * n_pen
        crown = [cr0 + h.cap_r * e1, cr1 + h.cap_r * e1, cr1 - h.cap_r * e1, cr0 - h.cap_r * e1]
        ax.add_patch(Polygon(crown, closed=True, fc=S3, ec="none", alpha=0.55, zorder=5))
        pod = [H(ru.ring_len, R_d - 0.3 - 2.1), H(ru.ring_len, R_d - 0.3), H(ru.ring_len + 4, R_d - 0.3), H(ru.ring_len + 4, R_d - 0.3 - 2.1)]
        ax.add_patch(Polygon(pod, closed=True, fc=S3, ec="none", alpha=0.3, zorder=4))
        # nose at rest and at the usable travel toward / away from the paper
        for alpha, col, ls, lab in ((0.0, S1, "-", "nose at rest"), (nz.alpha_u, S2, "--", "usable travel, toward the paper side"),
                                    (-nz.alpha_u, INK2, ":", "usable travel, away from it")):
            def rot(v, ang=alpha):
                c, s_ = math.cos(ang), math.sin(ang)
                return np.array([c * v[0] - s_ * v[1], s_ * v[0] + c * v[1]])

            def N(s, r):
                return G + rot((s - s_g) * a2 + r * n2)
            nzp = [N(0.0, ru.nozzle_r_front), N(ru.nozzle_len, ru.carrier_r), N(22.0, ru.carrier_r), N(22.0, -ru.carrier_r),
                   N(ru.nozzle_len, -ru.carrier_r), N(0.0, -ru.nozzle_r_front)]
            ax.add_patch(Polygon(nzp, closed=True, fc="none", ec=col, lw=1.3, ls=ls, zorder=6, label=lab if t == 35.0 else None))
            an = rot(a2)
            Lb = (G[1] - FE.R_B) / an[1]
            B = G - Lb * an
            E = N(0.0, 0.0)
            ax.plot([B[0], E[0]], [B[1], E[1]], color=col, lw=2.0, ls=ls, solid_capstyle="butt", zorder=6)
            ax.add_patch(Circle(B, FE.R_B, fc=col, ec="none", zorder=7))
        # page-sensor window (projected on the tilt plane)
        w = ps["window"]
        Pw = H(w["s_mm"], w["r_mm"] * math.cos(math.radians(w["phi_deg"])))
        ax.plot([Pw[0]], [Pw[1]], marker="s", ms=5, color=INK, zorder=8, label="page-sensor window" if t == 35.0 else None)
        ax.set_aspect("equal")
        ax.set_xlim(-20, 24)
        ax.set_ylim(-2.0, 22)
        ax.set_title(f"pen tilt {t:.0f}°", fontsize=10, color=INK)
        ax.set_xlabel("mm along the paper")
        hw = FR.window_height(R, w["s_mm"], w["r_mm"], w["phi_deg"], t)
        rows.append({"theta_deg": t, "ball_ahead_of_ring_mm": round(FE.protrusion(t, R), 3),
                     "wheel_protrusion_beyond_ring_mm": round(h.delta * math.cos(th) + h.r_e * (1 - math.cos(th - math.radians(50))), 3),
                     "page_window_height_mm": round(float(hw), 3), "ring_contact_radius_mm": R, "wheel_contact_radius_mm": R_d,
                     "usable_angle_rad": round(nz.alpha_u, 5)})
    axs[0].set_ylabel("mm above the paper")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=7.5, frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    fig.get_layout_engine().set(rect=(0, 0.07, 1, 0.93))
    fig.suptitle(f"Rev J front end (CALC on a proposed design): skid ring {R:.2f} mm, heel wheel {R_d:.2f} mm (green: wheel, "
                 f"steering crown, pod); nose ±{fe['X_nom_mm']:.2f} mm at 50°, 6.0 mm guaranteed over 35–75°\n"
                 "dark = paper side of the C ring, faint = its open top; grey = the fixed sleeve", fontsize=9, color=INK)
    fig.savefig(path_png, dpi=150)
    plt.close(fig)
    _csv(path_png, rows)


# --------------------------------------------------------------------------------------------------- budgets
def budgets_figure(path_png: str, bud: Dict):
    plt = _mpl()
    mb = bud["mass"]
    grp = dict(sorted(mb["by_group_base_g"].items(), key=lambda kv: kv[1]))
    grp["end-cap (detachable)"] = mb["endcap_g"]
    pw = bud["power"]["modes"]
    names = list(pw.keys())
    fig, axs = plt.subplots(1, 3, figsize=(14.0, 4.8), constrained_layout=True)
    ax = axs[0]
    y = np.arange(len(grp))
    ax.barh(y, list(grp.values()), height=0.55, color=S1, zorder=3)
    for yi, v in zip(y, grp.values()):
        ax.text(v + 0.4, yi, f"{v:.1f}", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(y, [k.replace("_", " ") for k in grp.keys()])
    ax.set_xlabel("g")
    ax.set_title(f"Mass by group: base pen {mb['base']['mass_g']:.1f} g, with the end-cap {mb['with_endcap']['mass_g']:.1f} g "
                 f"(limit {mb['limit_g']:.0f} g)", fontsize=8.5, color=INK, loc="left")
    ax = axs[1]
    y = np.arange(len(names))
    lo = [pw[k]["total_W"][0] for k in names]
    hi = [pw[k]["total_W"][1] for k in names]
    ax.barh(y, [h_ - l_ for l_, h_ in zip(lo, hi)], left=lo, height=0.55, color=S1, zorder=3)
    for yi, h_ in zip(y, hi):
        ax.text(h_ + 0.008, yi, f"{h_:.2f}", va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(y, [k.replace("_", " ") for k in names])
    ax.set_xlim(0, max(hi) * 1.18)
    ax.set_xlabel("W (range: low and high electronics, page-sensor supply)")
    ax.set_title("Mean electrical power per mode (base pen)", fontsize=8.5, color=INK, loc="left")
    ax = axs[2]
    hb = [pw[k]["hours"][0] for k in names]
    he = [pw[k]["hours_with_endcap"][0] for k in names]
    ax.barh(y + 0.16, hb, height=0.3, color=S1, zorder=3, label="base pen")
    ax.barh(y - 0.16, he, height=0.3, color=S2, zorder=3, label="with the end-cap active")
    ax.axvline(bud["power"]["target_h"], color=INK2, lw=1.0, zorder=4)
    ax.text(bud["power"]["target_h"] + 0.15, -0.75, "8 h target", fontsize=7.5, color=INK2)
    ax.set_yticks(y, [k.replace("_", " ") for k in names])
    ax.set_ylim(-1.0, len(names) - 0.4)
    ax.set_xlabel("hours on the LIR14500 (conservative end of the range)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=7.5, frameon=False)
    ax.set_title("Battery life per mode", fontsize=8.5, color=INK, loc="left")
    fig.suptitle("Rev J budgets (CALC; nose coil from study N's duty model or SIM rows; heel drive from study D SIM; "
                 "end-cap from study K)", fontsize=9, color=INK)
    fig.savefig(path_png, dpi=150)
    plt.close(fig)
    rows = [{"item": f"mass_{k}", "value": round(v, 3), "unit": "g"} for k, v in grp.items()]
    for k in names:
        rows.append({"item": f"power_{k}_low", "value": round(pw[k]["total_W"][0], 4), "unit": "W"})
        rows.append({"item": f"power_{k}_high", "value": round(pw[k]["total_W"][1], 4), "unit": "W"})
        rows.append({"item": f"hours_{k}_base_low", "value": round(pw[k]["hours"][0], 2), "unit": "h"})
        rows.append({"item": f"hours_{k}_endcap_low", "value": round(pw[k]["hours_with_endcap"][0], 2), "unit": "h"})
    _csv(path_png, rows)


# --------------------------------------------------------------------------------------------------- page sensor
def page_sensor_figure(path_png: str, fe: Dict, ps: Dict):
    plt = _mpl()
    w = ps["window"]
    th = np.linspace(35.0, 75.0, 81)
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    ax.axhspan(2.2, 2.6, color="#f0efec", zorder=0)
    ax.text(36.0, 2.62, "lens reference band 2.2–2.6 mm (MFR OPT-54)", fontsize=7.5, color=INK2, va="bottom")
    rows = []
    for roll, col, lab in ((0.0, S1, "no roll"), (5.0, S2, "±5° roll"), (20.0, S3, "±20° roll")):
        for sgn in ((1,) if roll == 0 else (1, -1)):
            hh = FR.window_height(fe["R_mm"], w["s_mm"], w["r_mm"], w["phi_deg"], th, sgn * roll)
            ax.plot(th, hh, color=col, lw=2.0, label=lab if sgn == 1 else None, zorder=3)
            for t, v in zip(th[::10], hh[::10]):
                rows.append({"roll_deg": sgn * roll, "theta_deg": round(float(t), 1), "window_height_mm": round(float(v), 4)})
    ax.set_xlabel("pen tilt (°)")
    ax.set_ylabel("lens-to-paper distance (mm)")
    ax.set_xlim(35, 75)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False, bbox_to_anchor=(0.0, 0.93))
    ax.set_title(f"Page-sensor window beside the heel wheel (azimuth {w['phi_deg']:.0f}°, {w['s_mm']:.2f} mm behind the ring "
                 f"plane): CALC", fontsize=8.5, color=INK, loc="left")
    fig.savefig(path_png, dpi=150)
    plt.close(fig)
    _csv(path_png, rows)


def _csv(path_png: str, rows):
    with open(path_png.replace(".png", ".csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        for r in rows:
            wr.writerow(r)


def all_figures(out_dir: str, fe, var, vis, geo, bud, mag, ps):
    os.makedirs(out_dir, exist_ok=True)
    front_end_figure(os.path.join(out_dir, "fig_revJ_front_end.png"), fe, ps)
    budgets_figure(os.path.join(out_dir, "fig_revJ_budgets.png"), bud)
    page_sensor_figure(os.path.join(out_dir, "fig_revJ_page_sensor.png"), fe, ps)
