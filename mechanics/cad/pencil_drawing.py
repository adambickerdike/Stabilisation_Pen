#!/usr/bin/env python3
"""Section drawing of the pencil concept Rev P0 from its CAD primitives.

Evidence status: PROPOSED DESIGN (drawing of the nominal CAD concept).
Reads results/cad/pencil_revP{L,Q}_viewer.json and _summary.json (written by
mechanics/cad/pencil_revP.py) and draws a longitudinal section with station
labels, plus cross-sections at the bender, nose, board and cell stations with
the bender tips shown at both stops.
Output: results/cad/drawing_pencil_revP{L,Q}.png
Run: python3 mechanics/cad/pencil_drawing.py [--variant L|Q]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from stabpen import plotstyle  # noqa: E402

COL = {"barrel": "#d9dcd8", "cap": "#c7cbc6", "skid": "#2d3338", "metal": "#8f989f", "pcb": "#1f6a45",
       "chip": "#23282e", "battery": "#345f88", "refill": "#b9c1c8", "magnet": "#b2493a", "piezo": "#c2a45e"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="L", choices=("L", "Q"))
    a = ap.parse_args()
    base = os.path.join(ROOT, "results", "cad", f"pencil_revP{a.variant}")
    g = json.load(open(base + "_viewer.json"))
    s = json.load(open(base + "_summary.json"))["summary"]
    P = s["parameters_mm"]
    prims = {p["name"]: p for p in g["primitives"]}
    plotstyle.apply()
    fig = plt.figure(figsize=(11.0, 5.9))
    ax = fig.add_axes([0.05, 0.50, 0.92, 0.42])
    # ---- longitudinal section (z horizontal, x vertical), half-plane rendering of solids of revolution
    ro, ri = P["od"] / 2, P["r_bore"]
    zs = P["z_skid"] + P["skid_w"]
    outer = [(zs, P["skid_r"] + 0.35), (zs + P["nose_L"], ro), (P["z_cap0"], ro)]
    for sgn in (1, -1):
        pts = [(z, sgn * r) for z, r in outer] + [(z, sgn * (r - P["wall"])) for z, r in reversed(outer)]
        ax.add_patch(Polygon(pts, closed=True, fc=COL["barrel"], ec="#7d847f", lw=0.6))
    ax.add_patch(Rectangle((P["z_cap0"], -ro), P["L_total"] - P["z_cap0"], 2 * ro, fc=COL["cap"], ec="#7d847f", lw=0.6))
    ax.add_patch(Rectangle((P["z_skid"], P["skid_r"] - 0.15), P["skid_w"], 0.5, fc=COL["skid"]))
    ax.add_patch(Rectangle((P["z_skid"], -P["skid_r"] - 0.35), P["skid_w"], 0.5, fc=COL["skid"]))
    rf = prims["refill_D1"]
    ax.add_patch(Polygon([(0.3, rf["socket_r"]), (rf["cone_L"], rf["r"]), (rf["L"], rf["r"]), (rf["L"], -rf["r"]),
                          (rf["cone_L"], -rf["r"]), (0.3, -rf["socket_r"])], closed=True, fc=COL["refill"], ec="#6d757c", lw=0.5))
    ax.add_patch(Circle((0, 0), rf["ball_r"], fc="#6d757c"))
    for n in ("collar", "clamp_block", "gimbal_flexure", "bulkhead"):
        p = prims[n]
        for sgn in (1, -1):
            y0 = p["r_in"] if sgn > 0 else -p["r_out"]
            ax.add_patch(Rectangle((p["z0"], y0), p["z1"] - p["z0"], p["r_out"] - p["r_in"], fc=COL[p["color"]], ec="none"))
    for n, p in prims.items():
        if p["type"] == "plate":
            cx, cy = p["center_xy"]
            if p["drive_axis"][0]:          # x-plate: its thickness shows in this x-z section
                ax.add_patch(Rectangle((p["tip_z"], cx - p["size"][0] / 2), p["root_z"] - p["tip_z"], p["size"][0], fc=COL["piezo"], ec="#8a7440", lw=0.5))
            else:                           # y-plate: seen edge-on across its width
                ax.add_patch(Rectangle((p["tip_z"], cx - p["size"][0] / 2), p["root_z"] - p["tip_z"], p["size"][0], fc=COL["piezo"], ec="#8a7440", lw=0.5, alpha=0.45))
    pc = prims["pcb"]; pz0 = pc["center"][2] - pc["size"][2] / 2
    ax.add_patch(Rectangle((pz0, -pc["size"][1] / 2), pc["size"][2], pc["size"][1], fc=COL["pcb"]))
    cm = prims["pcb_components"]
    ax.add_patch(Rectangle((cm["center"][2] - cm["size"][2] / 2, -cm["size"][1] / 2), cm["size"][2], cm["size"][1], fc="none", ec=COL["chip"], lw=0.6, ls="--"))
    bt = prims["battery"]
    ax.add_patch(Rectangle((bt["z0"], -bt["r"]), bt["z1"] - bt["z0"], 2 * bt["r"], fc=COL["battery"]))
    sp = prims["nib_spring"]
    zz = [sp["z0"] + (sp["z1"] - sp["z0"]) * k / 60 for k in range(61)]
    ax.plot(zz, [sp["r"] * math.sin(2 * math.pi * sp["turns"] * k / 60) for k in range(61)], color=COL["metal"], lw=0.8)
    hl = prims["hall_3d_nose"]
    ax.add_patch(Rectangle((hl["center"][2] - 0.75, hl["center"][0] - 0.3), 1.5, 0.6, fc=COL["chip"]))
    mg = prims["collar_magnet"]
    ax.add_patch(Rectangle((mg["center"][2] - 0.5, mg["center"][0] - 0.3), 1.0, 0.6, fc=COL["magnet"]))
    # station labels
    stations = [(0, "ball (datum A)", 0), (P["z_skid"], "skid ring", 2), (P["collar_z0"] + P["collar_L"] / 2, "collar + Hall", 0),
                (P["z_plate_tip"], "bender tips", 2), (P["z_clamp0"], "clamp", 0), (P["z_gimbal"], "gimbal", 0),
                ((P["z_spring0"] + P["z_bulkhead"]) / 2, "nib spring", 2), (P["z_pcb0"], "board", 0), (P["z_batt0"], "cell", 0),
                (P["z_cap0"], "cap", 0)]
    for z, lab, lev in stations:
        y = ro + 1.0 + lev * 1.6
        ax.plot([z, z], [ro + 0.2, y - 0.2], color="#898781", lw=0.6)
        ax.text(z, y, f"{lab}\nz {z:.1f}", fontsize=7, ha="center", va="bottom")
    ax.set_xlim(-4, P["L_total"] + 2); ax.set_ylim(-ro - 1.5, ro + 7.4)
    ax.set_aspect("equal"); ax.set_xlabel("z along the barrel from the ball (mm)"); ax.set_yticks([-4, 0, 4])
    ax.set_title(f"Pencil Rev P0{a.variant}: section through the barrel axis (x-z plane), nominal, stage centred", loc="left", fontsize=10)
    # ---- cross-sections
    cuts = [("bender station z 30: tips at both stops", 30.0), ("nose z 16.5: collar, magnet, Hall", 16.5),
            ("board z 99", 99.0), ("cell z 140", 140.0)]
    for k, (title, z) in enumerate(cuts):
        cx = fig.add_axes([0.05 + k * 0.235, 0.03, 0.2, 0.28])
        cx.add_patch(Circle((0, 0), ro, fc=COL["barrel"], ec="#7d847f", lw=0.6))
        r_in = ri if z > zs + P["nose_L"] else (P["skid_r"] - 0.05) + (ri - P["skid_r"] + 0.05) * (z - zs) / (P["nose_L"] - 0.5)
        cx.add_patch(Circle((0, 0), min(r_in, ri), fc="white", ec="none"))
        if z < rf["L"]:
            cx.add_patch(Circle((0, 0), rf["r"], fc=COL["refill"], ec="#6d757c", lw=0.5))
        if abs(z - 16.5) < 2:
            col = prims["collar"]
            cx.add_patch(Circle((0, 0), col["r_out"], fc=COL["metal"], ec="none"))
            cx.add_patch(Circle((0, 0), rf["r"], fc=COL["refill"], ec="#6d757c", lw=0.5))
            cx.add_patch(Rectangle((mg["center"][0] - 0.3, -0.5), 0.6, 1.0, fc=COL["magnet"]))
            cx.add_patch(Rectangle((hl["center"][0] - 0.3, -0.75), 0.6, 1.5, fc=COL["chip"]))
            sw = P["nib_travel"] / P["lever"]
            cx.add_patch(Circle((0, 0), col["r_out"] + sw, fc="none", ec="#cf4a2c", lw=0.6, ls=":"))
        if 19 <= z <= 55:
            for n, p in prims.items():
                if p["type"] != "plate":
                    continue
                w_, h_ = p["size"][0], p["size"][1]
                x0, y0 = p["center_xy"][0] - w_ / 2, p["center_xy"][1] - h_ / 2
                cx.add_patch(Rectangle((x0, y0), w_, h_, fc=COL["piezo"], ec="#8a7440", lw=0.5))
                sweep = P["tip_sweep"] * max(0.0, (P["z_clamp0"] - z) / (P["z_clamp0"] - P["z_plate_tip"])) ** 2
                for sgn in (-1, 1):
                    dx, dy = (sgn * sweep, 0) if p["drive_axis"][0] else (0, sgn * sweep)
                    cx.add_patch(Rectangle((x0 + dx, y0 + dy), w_, h_, fc="none", ec="#cf4a2c", lw=0.5, ls=":"))
        if 78 <= z <= 120:
            cx.add_patch(Rectangle((-pc["size"][0] / 2, -pc["size"][1] / 2), pc["size"][0], pc["size"][1], fc=COL["pcb"]))
            cx.add_patch(Rectangle((-cm["size"][0] / 2, -cm["size"][1] / 2), cm["size"][0], cm["size"][1], fc="none", ec=COL["chip"], lw=0.6, ls="--"))
        if 121 <= z <= 161:
            cx.add_patch(Circle((0, 0), bt["r"], fc=COL["battery"]))
        cx.set_xlim(-ro - 0.4, ro + 0.4); cx.set_ylim(-ro - 0.4, ro + 0.4); cx.set_aspect("equal")
        cx.set_xticks([-4, 0, 4]); cx.set_yticks([-4, 0, 4]); cx.tick_params(labelsize=7)
        cx.set_title(title, fontsize=8, loc="left")
    ck = s["section_checks"]
    import textwrap
    fig.text(0.05, 0.395, textwrap.fill("Translucent gold in the section: the y-axis plate behind the section plane. Dotted red: bender tips at the ±0.40 mm stops (z 30 shows the swept position there) and the collar's swept radius. "
             f"Worst clearances: plates-bore {ck['plate_to_bore_mm']} mm, plate-plate {ck['plate_to_plate_mm']} mm, "
             f"magnet-Hall {ck['collar_magnet_to_hall_mm']} mm, refill cone-skid aperture at 35 deg {ck['refill_cone_to_skid_aperture_at_theta_min_mm']} mm "
             f"(ring radius needed {ck['skid_ring_radius_required']} mm). Mass {s['mass_total_g']} g before wiring and margin.", 200), fontsize=7.5, va="top")
    plotstyle.stamp(fig, "PROPOSED DESIGN (CAD concept, nominal)")
    out = os.path.join(ROOT, "results", "cad", f"drawing_pencil_revP{a.variant}.png")
    fig.savefig(out, dpi=170)
    print("wrote", out)


if __name__ == "__main__":
    main()
