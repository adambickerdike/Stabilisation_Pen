#!/usr/bin/env python3
"""Dimensioned longitudinal section and cross-sections of pen Rev A, generated
from the same parameter set as the CAD (mechanics/cad/pen_revA.py).

Evidence status: PROPOSED DESIGN drawing (nominal dimensions, mm).  Datums:
A ball centre at neutral, B barrel axis, C roll datum (+x toward PCB top).
Outputs results/cad/drawing_revA_section.png (+ .svg) and cross_sections.png.
"""
from __future__ import annotations

import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle, Wedge, Polygon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))
from stabpen import plotstyle  # noqa: E402
import pen_revA as cad  # noqa: E402

P = cad.P
OUT = os.path.join(ROOT, "results", "cad")
INK, INK2, MUTED = plotstyle.INK, plotstyle.INK2, plotstyle.MUTED
C_FIX, C_MOV, C_MAG, C_PCB, C_BAT = "#c3c2b7", plotstyle.SERIES[0], plotstyle.SERIES[1], plotstyle.SERIES[2], plotstyle.SERIES[3]


def dim_h(ax, x0, x1, y, text, above=True):
    ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=0.7, color=INK2))
    ax.text((x0 + x1) / 2, y + (0.45 if above else -0.9), text, ha="center", fontsize=6.5, color=INK)


def dim_v(ax, x, y0, y1, text):
    ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", lw=0.7, color=INK2))
    ax.text(x + 0.6, (y0 + y1) / 2, text, va="center", fontsize=6.5, color=INK, rotation=90)


def section():
    plotstyle.apply()
    fig, ax = plt.subplots(figsize=(14, 4.6))
    ax.set_aspect("equal")
    ax.grid(False)
    ri = P["od_grip"] / 2 - P["wall"]
    # barrel outline (upper and lower walls), nose cone
    zs = [1.0, P["z_nose_end"], P["z_bulge0"], P["z_bulge0"] + 5, P["z_bulge1"] - 3, P["z_bulge1"], P["L_total"]]
    ro = [P["nose_tip_od"] / 2, P["od_grip"] / 2, P["od_grip"] / 2, P["od_act"] / 2, P["od_act"] / 2, P["od_grip"] / 2, P["od_grip"] / 2]
    for sgn in (1, -1):
        ax.plot(zs, [sgn * r for r in ro], color=INK2, lw=1.2)
        rin = [P["tip_aperture"] / 2, ri, ri, P["od_act"] / 2 - P["wall"], P["od_act"] / 2 - P["wall"], ri, ri]
        ax.fill_between(zs, [sgn * r for r in ro], [sgn * r for r in rin], color=C_FIX, alpha=0.5, lw=0)
    # refill + ball
    ax.add_patch(Polygon([(0, 0.45), (P["cone_L"], P["refill_d"] / 2), (P["refill_L"], P["refill_d"] / 2),
                          (P["refill_L"], -P["refill_d"] / 2), (P["cone_L"], -P["refill_d"] / 2), (0, -0.45)],
                         closed=True, fc=C_MOV, alpha=0.25, ec=C_MOV, lw=0.8))
    ax.add_patch(Circle((0, 0), P["ball_d"] / 2, fc=INK, ec=INK))
    # carrier
    for sgn in (1, -1):
        ax.add_patch(Rectangle((P["carrier_z0"], sgn * P["carrier_id"] / 2 if sgn > 0 else -P["carrier_od"] / 2),
                               P["carrier_z1"] - P["carrier_z0"], (P["carrier_od"] - P["carrier_id"]) / 2,
                               fc=C_MOV, alpha=0.6, lw=0))
    # pivot wires and ring
    L1 = P["L1"]
    for sgn in (1, -1):
        ax.plot([L1 + P["wire_r_in"], L1 + P["wire_r_out"]], [sgn * P["wire_r_in"], sgn * P["wire_r_out"]], color=INK, lw=1.0)
        ax.plot([L1, L1 + P["wire_r_in"]], [0, sgn * P["wire_r_in"]], color=MUTED, lw=0.6, ls=(0, (2, 2)))
    ax.plot(L1, 0, marker="+", color=INK, ms=10, mew=1.2)
    # stop ring
    sr_hole = P["carrier_od"] / 2 + cad.swing(P["z_stop"], P) + P["stop_clear"]
    for sgn in (1, -1):
        ax.add_patch(Rectangle((P["z_stop"] - P["stop_t"] / 2, sgn * sr_hole if sgn > 0 else -ri), P["stop_t"], ri - sr_hole, fc="#898781", lw=0))
    # actuator
    z = P["z_act"]
    zc0 = z - P["coil_t"] / 2 - P["act_gap"]
    zc1 = z + P["coil_t"] / 2 + P["act_gap"]
    ri_f = P["carrier_od"] / 2 + cad.swing(zc0 - P["mag_t"] - P["fe_t"], P) + P["act_id_clear"]
    ri_r = P["carrier_od"] / 2 + cad.swing(zc1 + P["mag_t"] + P["fe_t"], P) + P["act_id_clear"]
    for sgn in (1, -1):
        y0f, y0r = (ri_f, ri_r) if sgn > 0 else (-P["act_od"] / 2, -P["act_od"] / 2)
        hf, hr = P["act_od"] / 2 - ri_f, P["act_od"] / 2 - ri_r
        ax.add_patch(Rectangle((zc0 - P["mag_t"] - P["fe_t"], y0f), P["fe_t"], hf, fc="#52514e", lw=0))
        ax.add_patch(Rectangle((zc0 - P["mag_t"], y0f), P["mag_t"], hf, fc=C_MAG, lw=0))
        ax.add_patch(Rectangle((zc1, y0r), P["mag_t"], hr, fc=C_MAG, lw=0))
        ax.add_patch(Rectangle((zc1 + P["mag_t"], y0r), P["fe_t"], hr, fc="#52514e", lw=0))
        ro_p = P["act_od"] / 2 - cad.swing(z, P) - 0.3
        ax.add_patch(Rectangle((z - P["coil_t"] / 2, P["carrier_od"] / 2 if sgn > 0 else -ro_p), P["coil_t"],
                               ro_p - P["carrier_od"] / 2, fc=C_MOV, alpha=0.9, lw=0))
    # sensing magnet + hall
    zp = P["refill_L"] + P["plug_L"]
    ax.add_patch(Rectangle((zp - P["sense_mag_t"], -P["sense_mag_d"] / 2), P["sense_mag_t"], P["sense_mag_d"], fc=C_MAG, lw=0))
    ax.add_patch(Rectangle((zp + P["hall_gap"], -1.5), 0.8, 3.0, fc=C_PCB, lw=0))
    # pcb, battery
    ax.add_patch(Rectangle((P["pcb_z0"], -P["pcb_t"] / 2), P["pcb_L"], P["pcb_t"], fc=C_PCB, lw=0))
    for sgn in (1, -1):
        ax.add_patch(Rectangle((P["pcb_z0"] + 1, sgn * P["pcb_t"] / 2 if sgn > 0 else -P["pcb_t"] / 2 - P["comp_h"]),
                               P["pcb_L"] - 2, P["comp_h"], fc=C_PCB, alpha=0.35, lw=0))
    ax.add_patch(Rectangle((P["batt_z0"], -P["batt_d"] / 2), P["batt_L"], P["batt_d"], fc=C_BAT, alpha=0.6, lw=0))
    # optics (three at 30/150/270 deg; the 270 deg sensor lies in this section plane)
    ax.add_patch(Rectangle((P["opt_z"] - P["opt_size"][0] / 2, -P["opt_r"] - P["opt_size"][2] / 2),
                           P["opt_size"][0], P["opt_size"][2], fc="#4a3aa7", lw=0))
    # datums
    ax.text(-2.2, 0.0, "A", fontsize=8, color=INK, ha="center", va="center", bbox=dict(boxstyle="square,pad=0.15", fc="white", ec=INK, lw=0.6))
    ax.plot([-1, P["L_total"] + 2], [0, 0], color=MUTED, lw=0.5, ls=(0, (6, 2, 1, 2)))
    ax.text(P["L_total"] + 3.5, 0.0, "B", fontsize=8, color=INK, ha="center", va="center", bbox=dict(boxstyle="square,pad=0.15", fc="white", ec=INK, lw=0.6))
    # dimensions
    y = -10.5
    dim_h(ax, 0, P["L_total"], y - 2.2, f"{P['L_total']:.0f} overall (A to cap end)", above=False)
    dim_h(ax, 0, L1, y, f"L1 = {L1:.0f} (pivot)", above=False)
    dim_h(ax, L1, z, y + 2.4, f"L2 = {z - L1:.0f}  (n = {(z - L1) / L1:.2f})", above=False)
    dim_h(ax, 0, P["z_stop"], 9.8, f"stop {P['z_stop']:.0f}")
    dim_h(ax, 0, P["refill_L"], 12.0, f"refill D1 {P['refill_L']:.0f}")
    dim_h(ax, P["pcb_z0"], P["pcb_z0"] + P["pcb_L"], 9.8, f"PCB {P['pcb_L']:.0f} x {P['pcb_w']}")
    dim_h(ax, P["batt_z0"], P["batt_z0"] + P["batt_L"], 9.8, f"cell 10440 (Ø{P['batt_d']:.0f})")
    dim_v(ax, P["L_total"] - 6, -P["od_grip"] / 2, P["od_grip"] / 2, f"Ø{P['od_grip']:.0f}")
    dim_v(ax, (P["z_bulge0"] + P["z_bulge1"]) / 2 + 3, -P["od_act"] / 2, P["od_act"] / 2, f"Ø{P['od_act']:.0f}")
    ax.text(z, P["od_act"] / 2 + 1.6, f"actuator: coil paddle between annular\nquadrant magnets, gap {P['act_gap']} mm", ha="center", fontsize=6.5, color=INK2)
    ax.text(L1 + 3, 5.8, "pivot: 3 wires, lines through\nvirtual centre on axis", fontsize=6.5, color=INK2)
    ax.text(P["opt_z"], -7.2, "optics (x3, 120 deg)", ha="center", fontsize=6.5, color=INK2)
    ax.text(zp + 2.2, 2.2, "3-D Hall", fontsize=6.5, color=INK2)
    ax.set_xlim(-5, P["L_total"] + 6)
    ax.set_ylim(-14.5, 14.5)
    ax.set_xlabel("z from ball centre (mm)")
    ax.set_title("Pen Rev A: longitudinal section (proposed design, nominal dimensions in mm)", loc="left")
    plotstyle.stamp(fig, "proposed design", "not a fit check; generated from mechanics/cad/pen_revA.py parameters")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "drawing_revA_section.png"), dpi=200)
    fig.savefig(os.path.join(OUT, "drawing_revA_section.svg"))
    plt.close(fig)


def cross_sections():
    plotstyle.apply()
    stations = [("z = 12 pivot plane", 12.0), ("z = 36 stop ring", P["z_stop"]), ("z = 50 actuator", P["z_act"]),
                ("z = 85 PCB", 85.0), ("z = 124 cell", 124.0)]
    fig, axs = plt.subplots(1, len(stations), figsize=(14, 3.2))
    ri = P["od_grip"] / 2 - P["wall"]
    for ax, (name, z) in zip(axs, stations):
        ax.set_aspect("equal"); ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
        od = P["od_act"] if P["z_bulge0"] + 5 <= z <= P["z_bulge1"] - 3 else P["od_grip"]
        if z < P["z_nose_end"]:
            od = P["nose_tip_od"] + (P["od_grip"] - P["nose_tip_od"]) * (z - 1) / (P["z_nose_end"] - 1)
        r_in = od / 2 - P["wall"]
        ax.add_patch(Circle((0, 0), od / 2, fc=C_FIX, ec=INK2, lw=0.8))
        ax.add_patch(Circle((0, 0), r_in, fc="white", ec=INK2, lw=0.5))
        area_bore = math.pi * r_in ** 2
        occ = 0.0
        sw = cad.swing(z, P) if z <= P["carrier_z1"] else 0
        if z <= P["refill_L"]:
            ax.add_patch(Circle((0, 0), P["carrier_od"] / 2 + sw, fc="none", ec=C_MOV, lw=0.8, ls=(0, (2, 1.5))))
            if z >= P["carrier_z0"] and z <= P["carrier_z1"]:
                ax.add_patch(Circle((0, 0), P["carrier_od"] / 2, fc=C_MOV, alpha=0.6, lw=0))
            ax.add_patch(Circle((0, 0), P["refill_d"] / 2, fc=C_MOV, alpha=0.9, lw=0))
            occ += math.pi * (P["carrier_od"] / 2 + sw) ** 2
        if abs(z - P["z_act"]) < 1:
            ax.add_patch(Wedge((0, 0), P["act_od"] / 2, 0, 360, width=P["act_od"] / 2 - 3.9, fc=C_MAG, alpha=0.8, lw=0))
            occ += math.pi * ((P["act_od"] / 2) ** 2 - 3.9 ** 2)
        if abs(z - P["z_stop"]) < 1:
            ax.add_patch(Wedge((0, 0), r_in, 0, 360, width=r_in - 3.1, fc="#898781", lw=0))
        if P["pcb_z0"] <= z <= P["pcb_z0"] + P["pcb_L"]:
            ax.add_patch(Rectangle((-P["pcb_w"] / 2, -P["pcb_t"] / 2), P["pcb_w"], P["pcb_t"], fc=C_PCB, lw=0))
            ax.add_patch(Rectangle((-P["pcb_w"] / 2 + 0.5, P["pcb_t"] / 2), P["pcb_w"] - 1, P["comp_h"], fc=C_PCB, alpha=0.35, lw=0))
            ax.add_patch(Rectangle((-P["pcb_w"] / 2 + 0.5, -P["pcb_t"] / 2 - P["comp_h"]), P["pcb_w"] - 1, P["comp_h"], fc=C_PCB, alpha=0.35, lw=0))
            occ += P["pcb_w"] * (P["pcb_t"] + 2 * P["comp_h"])
        if P["batt_z0"] <= z <= P["batt_z0"] + P["batt_L"]:
            ax.add_patch(Circle((0, 0), P["batt_d"] / 2, fc=C_BAT, alpha=0.6, lw=0))
            occ += math.pi * (P["batt_d"] / 2) ** 2
        if abs(z - P["opt_z"]) < 2:
            for sgn in (1, -1):
                ax.add_patch(Rectangle((-P["opt_size"][0] / 2, sgn * P["opt_r"] - P["opt_size"][2] / 2), P["opt_size"][0], P["opt_size"][2], fc="#4a3aa7", lw=0))
        ax.set_xlim(-9, 9); ax.set_ylim(-9, 9)
        ax.set_title(f"{name}\nbore Ø{2*r_in:.1f}, swept/used {min(occ/area_bore,1)*100:.0f}%", fontsize=8, loc="center")
    plotstyle.stamp(fig, "proposed design", "dashed circle = swept envelope of lever at full tip travel")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "drawing_revA_cross_sections.png"), dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    section()
    cross_sections()
    print("drawings written to", OUT)
