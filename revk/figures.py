"""Figures of study K (PNG + CSV twin each, results/revK/): the layout side view, the mass budget, the power budget per mode
and the battery hours per mode against REQ-RVJ-I01.  Every number drawn is in revK.json / budgets.json (CALCULATION)."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import ensure_paths

ensure_paths()

COLORS = {"structure": (0.70, 0.72, 0.75), "grip": (0.35, 0.55, 0.85), "moving_nib": (0.95, 0.55, 0.15),
          "refill": (0.20, 0.20, 0.25), "actuator": (0.80, 0.20, 0.25), "mechanism": (0.55, 0.35, 0.75),
          "sensor": (0.15, 0.65, 0.45), "electronics": (0.20, 0.45, 0.30), "power": (0.95, 0.80, 0.20),
          "haptic": (0.50, 0.50, 0.50), "magnet": (0.80, 0.25, 0.60), "skid": (0.15, 0.17, 0.20),
          "balance": (0.10, 0.55, 0.75), "drive": (0.05, 0.60, 0.45)}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _write_csv(path: Path, header: List[str], rows: List[List]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _outline(c: Dict):
    """Side-section outline (z, x) of a component (x up = away from the paper)."""
    z0, z1 = c["z0"], c["z1"]
    ox = c.get("offset", [0.0, 0.0])[0]
    if c["shape"] == "box":
        sx = c["size"][0]
        return [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
    r0, r1 = c.get("d0", 0.0) / 2, c.get("d1", c.get("d0", 0.0)) / 2
    if c["shape"] == "tube":
        ri = c.get("d_in", 0.0) / 2
        top = [(z0, ox + ri), (z1, ox + ri), (z1, ox + r1), (z0, ox + r0)]
        bot = [(z0, ox - r0), (z1, ox - r1), (z1, ox - ri), (z0, ox - ri)]
        if c.get("open_deg"):
            return [bot]
        return [top, bot]
    return [[(z0, ox - r0), (z1, ox - r1), (z1, ox + r1), (z0, ox + r0)]]


def layout_side(lay: Dict, out: Path, hd: Dict) -> List[str]:
    plt = _plt()
    from matplotlib.patches import Polygon, Rectangle
    fig, ax = plt.subplots(figsize=(17, 4.6))
    rows = []
    for c in lay["components"]:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        if c["id"] == "head_face":
            pts = np.array(c["plate_corners_50deg"])
            # the plate's section in the tilt plane (y = +-w/2 collapse): corners at v = -w/2, back 0 and 1.2
            poly = [(p[2], p[0]) for p in pts[[0, 4, 5, 1]]]
            ax.add_patch(Polygon(poly, closed=True, facecolor=col, edgecolor="k", lw=0.5, alpha=0.9))
        else:
            for poly in _outline(c):
                ax.add_patch(Polygon(poly, closed=True, facecolor=col, edgecolor="k", lw=0.4, alpha=0.85))
        rows.append([c["id"], c["label"], c["group"], c["shape"], round(c["z0"], 3), round(c["z1"], 3), c.get("d0", ""),
                     c.get("d1", ""), c.get("d_in", ""), c.get("size", ""), c.get("offset", ""), c["moves_with"],
                     c.get("optional", False), c.get("mass_g", "")])
    for c in lay["heel_variant"]["components"]:
        for poly in _outline(c):
            ax.add_patch(Polygon(poly, closed=True, facecolor="none", edgecolor=COLORS["drive"], lw=0.8, ls="--"))
        rows.append([c["id"], c["label"] + " (heel variant)", c["group"], c["shape"], round(c["z0"], 3), round(c["z1"], 3),
                     c.get("d0", ""), c.get("d1", ""), c.get("d_in", ""), c.get("size", ""), c.get("offset", ""),
                     c["moves_with"], True, c.get("mass_g", "")])
    R = lay["skid_contact_radius"]
    zr = lay["ball_protrusion_mm"]
    for tdeg, ls in ((35.0, ":"), (50.0, "-"), (75.0, "--")):
        th = math.radians(tdeg)
        zz = np.array([-10.0, 150.0])
        ax.plot(zz, [-R - (z - zr) * math.tan(th) for z in zz], color="0.35", lw=0.8, ls=ls)
        ax.text(zz[0] + 1, -R - (zz[0] + 1 - zr) * math.tan(th) + 0.6, f"paper {tdeg:.0f}°", fontsize=7, color="0.3")
    D = lay["handle_od"]
    for zf in lay["hand"]["finger_pads_z"]:
        ax.add_patch(Rectangle((zf - 2.5, D / 2 + 1.5), 5, 2.0, color=(0.9, 0.7, 0.6), alpha=0.9))
    ax.add_patch(Rectangle((lay["hand"]["web_z"] - 6, D / 2 + 1.5), 12, 2.0, color=(0.85, 0.6, 0.5), alpha=0.9))
    ax.text(lay["hand"]["web_z"], D / 2 + 4.3, "web", ha="center", fontsize=7)
    ax.text(32, D / 2 + 4.3, "finger pads", ha="center", fontsize=7)
    fs = lay["fit_summary"]
    ax.set_title(f"Rev K (PROPOSED DESIGN): {lay['length']:.1f} mm, B1 nib ±{lay['tip_travel_mm']:.2f} mm, counter-face head "
                 f"(L_O {hd['L_O_mm']:g} mm, hinge x {hd['x_h_mm']:g} mm), heel module dashed; fit checks: {fs['pass']} pass, "
                 f"{fs['marginal']} marginal, {fs['fail']} fail (CALC)", fontsize=9)
    ax.set_xlim(-12, lay["length"] + 4)
    ax.set_ylim(-20, 18)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip at 50° (mm)")
    ax.set_ylabel("x (mm, + away from the paper)")
    handles = [Rectangle((0, 0), 1, 1, color=COLORS[g]) for g in ("refill", "moving_nib", "actuator", "magnet", "mechanism",
                                                                     "sensor", "electronics", "balance", "power", "grip",
                                                                     "structure", "skid")]
    ax.legend(handles, ["refill", "moving nib", "coils / iron", "magnets", "ball guide / wires", "sensors", "electronics",
                        "counter-face head", "cell", "grip / window", "structure", "skid ring"], fontsize=7, ncol=6,
              loc="lower right")
    fig.tight_layout()
    p = out / "layout_side_revK.png"
    fig.savefig(p, dpi=130, facecolor="white")
    plt.close(fig)
    q = out / "layout_side_revK.csv"
    _write_csv(q, ["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm",
                   "moves_with", "optional", "mass_g"], rows)
    return [str(p), str(q)]


def mass_fig(bud: Dict, out: Path) -> List[str]:
    plt = _plt()
    m = bud["mass"]
    g = m["by_group_base_g"]
    keys = sorted(g, key=lambda k: -g[k])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [2.2, 1]})
    ax.bar(keys, [g[k] for k in keys], color=[COLORS.get(k, (0.6, 0.6, 0.6)) for k in keys])
    ax.set_ylabel("g (incl. +10 % wiring)")
    ax.set_title(f"Rev K base pen by group: {m['base']['mass_g']:.1f} g (CALC)", fontsize=9)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    names = ["Rev K base", "Rev K + heel", "study B's Rev K", "Rev J.1 base"]
    vals = [m["base"]["mass_g"], m["with_heel_module"]["mass_g"], m["compare"]["studyB_revK_estimate"]["mass_g"],
            m["compare"]["revJ1_base"]["mass_g"]]
    com = [m["base"]["com_mm"][2], m["with_heel_module"]["com_mm"][2], m["compare"]["studyB_revK_estimate"]["com_z_mm"],
           m["compare"]["revJ1_base"]["com_z_mm"]]
    bx.bar(names, vals, color=["C0", "C2", "C1", "C7"])
    for i, (v, c) in enumerate(zip(vals, com)):
        bx.text(i, v + 1, f"{v:.1f} g\nCoM {c:.1f} mm", ha="center", fontsize=7)
    bx.axhline(m["limit_g"], color="r", ls="--", lw=0.8)
    bx.text(3.4, m["limit_g"] - 6, "120 g limit", color="r", fontsize=7, ha="right")
    bx.set_ylim(0, 130)
    bx.tick_params(axis="x", rotation=20, labelsize=8)
    bx.set_title("mass and balance point (CALC)", fontsize=9)
    fig.tight_layout()
    p = out / "mass_budget_revK.png"
    fig.savefig(p, dpi=130, facecolor="white")
    plt.close(fig)
    q = out / "mass_budget_revK.csv"
    rows = [["group", k, round(g[k], 3), ""] for k in keys] + [["pen", n, round(v, 2), round(c, 2)] for n, v, c in
                                                                zip(names, vals, com)]
    _write_csv(q, ["kind", "name", "mass_g", "com_z_mm"], rows)
    return [str(p), str(q)]


def power_fig(bud: Dict, out: Path) -> List[str]:
    plt = _plt()
    pw = bud["power"]["rows"]
    modes = [k for k in pw if "nib_W" in k or "nib_W" in pw[k]]
    parts = [("electronics_W", "electronics"), ("page_W", "page sensor"), ("face_sensor_W", "face sensor"),
             ("positioners_W", "head positioners"), ("nib_W", "nib coils"), ("mode_extra_W", "mode extras (lifts, cues)")]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4), sharey=True)
    rows = []
    for j, (idx, name) in enumerate(((0, "low end"), (1, "high end"))):
        bottom = np.zeros(len(modes))
        for i, (k, lab) in enumerate(parts):
            v = np.array([pw[m][k][idx] * 1e3 for m in modes])
            ax[j].bar(modes, v, bottom=bottom, label=lab, color=f"C{i}")
            bottom += v
            for m, x in zip(modes, v):
                rows.append([name, m, lab, round(float(x), 3)])
        ax[j].set_title(f"mean power per mode, {name} (mW, CALC)", fontsize=9)
        ax[j].set_ylim(0, 120)
        ax[j].tick_params(axis="x", rotation=25, labelsize=8)
    ax[0].set_ylabel("mW")
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    p = out / "power_budget_revK.png"
    fig.savefig(p, dpi=130, facecolor="white")
    plt.close(fig)
    q = out / "power_budget_revK.csv"
    _write_csv(q, ["end", "mode", "part", "mW"], rows)
    return [str(p), str(q)]


def hours_fig(bud: Dict, out: Path) -> List[str]:
    plt = _plt()
    pw = bud["power"]["rows"]
    ph = bud["power_heel_variant"]["rows"]
    cmp = bud["power_compare"]["revJ1"]
    modes = ["steady_0mm", "steady_1mm", "steady_2mm", "guide", "spelling_cue", "lead_through"]
    tg = {"steady_0mm": 8.0, "steady_1mm": 8.0, "guide": 8.0, "lead_through": 7.5}
    j1 = {"steady_0mm": cmp["steady_no_tremor_h"], "steady_1mm": cmp["steady_1mm_h"], "guide": cmp["guide_h"],
          "lead_through": cmp["lead_h"]}
    fig, ax = plt.subplots(figsize=(10, 4.4))
    rows = []
    for i, m in enumerate(modes):
        r = pw.get(m) or ph.get(m)
        src = "base" if m in pw else "heel variant"
        lo, hi = r["hours"]
        ax.bar(i, hi - lo, bottom=lo, color="C0" if src == "base" else "C2", width=0.6)
        ax.text(i, hi + 1, f"{lo:.0f}-{hi:.0f} h", ha="center", fontsize=8)
        if m in tg:
            ax.plot([i - 0.35, i + 0.35], [tg[m]] * 2, color="r", lw=1.5)
        if m in j1:
            ax.plot([i, i], j1[m], color="k", lw=3, alpha=0.5)
        rows.append([m, src, round(lo, 2), round(hi, 2), tg.get(m, ""), j1.get(m, ["", ""])[0], j1.get(m, ["", ""])[1]])
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels([m.replace("_", " ") + (" (heel module)" if m == "lead_through" else "") for m in modes], fontsize=8)
    ax.set_ylim(0, max(r[3] for r in rows) + 6)
    ax.set_ylabel("hours on the LIR14500 (2.22 Wh usable)")
    ax.set_title("Rev K battery hours per mode (bars low-high, CALC); red: REQ-RVJ-I01 targets; grey: Rev J.1 (suspended)",
                 fontsize=9)
    fig.tight_layout()
    p = out / "battery_hours_revK.png"
    fig.savefig(p, dpi=130, facecolor="white")
    plt.close(fig)
    q = out / "battery_hours_revK.csv"
    _write_csv(q, ["mode", "pen", "hours_low", "hours_high", "REQ_RVJ_I01_target_h", "revJ1_low_h", "revJ1_high_h"], rows)
    return [str(p), str(q)]


def all_figures(lay: Dict, bud: Dict, hd: Dict, out: Path) -> List[str]:
    files = []
    files += layout_side(lay, out, hd)
    files += mass_fig(bud, out)
    files += power_fig(bud, out)
    files += hours_fig(bud, out)
    return files
