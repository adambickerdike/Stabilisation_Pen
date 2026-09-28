#!/usr/bin/env python3
"""Desk guidance board (A4): dimensioned concept in CadQuery.

Evidence status: PROPOSED DESIGN (concept geometry; catalogue parts shown as
envelopes of the cited parts; nothing built).  Geometry comes from
board/layout.py, the same source as results/board/layout.json.

Outputs
  results/cad/guidance_board_assembly.step   STEP assembly (head at the page centre)
  results/cad/guidance_board_summary.json    dimensions, mass estimate, interference checks
  results/cad/drawing_guidance_board.png     top view, section through the head, pen-magnet detail
  results/board/fig_cad_drawing.png/.csv     the same drawing and its dimension table (CSV twin)
Run: python3 mechanics/cad/guidance_board.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402
from board import layout as L  # noqa: E402
from board import params as P  # noqa: E402

OUT = os.path.join(ROOT, "results", "cad")
OUT_B = os.path.join(ROOT, "results", "board")

DENSITY = {"aluminium": 2.70, "glass": 2.50, "steel": 7.85, "PA12": 1.01, "FR4": 1.90, "paper": 0.80, "foam": 0.10}
KNOWN_MASS_G = {"motor_A": 400.0, "motor_B": 400.0, "head_magnet": 12.07, "zservo": 18.0,
                "yblock_0": 54.0, "yblock_1": 54.0, "xblock": 26.0}   # MFR AMF-92, 90, 96, 94
MATERIAL = {"base_plate": "aluminium", "wall_left": "aluminium", "wall_right": "aluminium", "wall_front": "aluminium",
            "glass": "glass", "paper": "paper", "paper_stop": "PA12", "housing": "PA12", "beam": "aluminium",
            "carriage_plate": "aluminium", "head_cup": "aluminium", "hall_ring": "FR4", "main_pcb": "FR4",
            "arm_rest": "foam", "idler_0": "aluminium", "idler_1": "aluminium", "stop_button": "PA12", "dc_jack": "PA12",
            "belt_left": "PA12", "belt_right": "PA12"}


def solid(c):
    if c["shape"] == "box":
        sx, sy, sz = c["size"]
        s = cq.Workplane("XY").box(sx, sy, sz, centered=False).translate((c["x0"], c["y0"], c["z0"]))
        if "hole" in c:
            hx, hy = c["hole"]["center"]
            s = s.cut(cq.Workplane("XY").circle(c["hole"]["d"] / 2).extrude(sz + 2).translate((hx, hy, c["z0"] - 1)))
        return s
    cx, cy, cz = c["center"]
    h = c["h"]
    wp = cq.Workplane("XY").circle(c["d"] / 2)
    if c["shape"] == "tube":
        wp = wp.circle(c["d_in"] / 2)
    return wp.extrude(h).translate((cx, cy, cz - h / 2))


def shell_volume_mm3(c):
    """Volume used for the mass estimate (housing and walls treated as thin shells)."""
    if c["id"] == "housing":
        sx, sy, sz = c["size"]
        return 2.0 * (sx * sy + 2 * sx * sz + 2 * sy * sz)   # 2 mm shell
    if c["id"] == "arm_rest":
        sx, sy, sz = c["size"]
        return 0.5 * sx * sy * sz                            # wedge
    if c["shape"] == "box":
        sx, sy, sz = c["size"]
        return sx * sy * sz
    v = math.pi / 4 * c["d"] ** 2 * c["h"]
    if c["shape"] == "tube":
        v -= math.pi / 4 * c["d_in"] ** 2 * c["h"]
    return v


def mass_estimate(comps):
    rows, total = [], 0.0
    for c in comps:
        if c["id"] in KNOWN_MASS_G:
            m, src = KNOWN_MASS_G[c["id"]], "MFR"
        elif c["id"].startswith(("yrail", "xrail")):
            length = max(c["size"][:2]) / 1000.0
            m, src = (0.65 if c["id"].startswith("yrail") else 0.38) * length * 1000.0, "MFR AMF-94 (kg/m) x CALC length"
        elif c["id"] in MATERIAL:
            m, src = shell_volume_mm3(c) * 1e-3 * DENSITY[MATERIAL[c["id"]]], f"CALC volume x {MATERIAL[c['id']]} density (ASSUMPTION)"
        else:
            continue
        rows.append({"id": c["id"], "mass_g": round(m, 1), "source": src})
        total += m
    return rows, total


def interference(pairs, comps_by_id):
    out = []
    for a, b in pairs:
        sa, sb = solid(comps_by_id[a]), solid(comps_by_id[b])
        inter = sa.intersect(sb)
        vol = inter.val().Volume() if inter.vals() else 0.0
        out.append({"a": a, "b": b, "overlap_mm3": round(vol, 3)})
    return out


def drawing(path, comps, comps_low):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    from stabpen import plotstyle as ps
    ps.apply()
    G = L.G
    fig = plt.figure(figsize=(15.5, 8.6))
    ax = fig.add_axes([0.03, 0.07, 0.42, 0.86])
    ink, grey = ps.INK2, ps.MUTED
    byid = {c["id"]: c for c in comps}
    # ---- top view
    colors = {"structure": ps.GRID, "mechanism": ps.SEQ_BLUE[1], "actuator": ps.SERIES[1], "magnet": ps.SERIES[4],
              "sensor": ps.SERIES[2], "electronics": ps.SERIES[3], "power": ps.SERIES[3]}
    for c in comps:
        if c["id"] in ("glass", "arm_rest", "housing"):
            continue
        col = colors.get(c["group"], ps.GRID)
        if c["shape"] == "box":
            ax.add_patch(Rectangle((c["x0"], c["y0"]), c["size"][0], c["size"][1], fc=col, ec=ink, lw=0.6,
                                   alpha=0.35 if c["id"] == "paper" else 0.8))
        else:
            ax.add_patch(Circle((c["center"][0], c["center"][1]), c["d"] / 2, fc=col, ec=ink, lw=0.6, alpha=0.85))
    bx, by = G["board"]
    ax.add_patch(Rectangle((0, 0), bx, by, fc="none", ec=ps.INK, lw=1.4))
    ax.plot([0, bx], [G["glass_y"], G["glass_y"]], color=ink, lw=1.0, ls="--")
    tr = L.travel()
    ax.add_patch(Rectangle((tr["x"][0], tr["y"][0]), tr["x"][1] - tr["x"][0], tr["y"][1] - tr["y"][0], fc="none",
                           ec=ps.SERIES[0], lw=1.2, ls="-."))
    x0, y0, w, h = G["paper"]
    ax.text(x0 + 6, y0 + h - 22, "A4 paper 210 x 297", fontsize=8, color=ink)
    ax.text(tr["x"][0] + 3, tr["y"][0] + 4, f"head travel {tr['x'][1]-tr['x'][0]:.0f} x {tr['y'][1]-tr['y'][0]:.0f}", fontsize=8, color=ps.SERIES[0])
    ax.text(60, G["glass_y"] - 12, "back housing above: 2 x NEMA 17, main board, stop button", fontsize=8, color=ink)
    hm = byid["head_magnet"]
    ax.annotate("head magnet D88-N52\n+ Hall ring (8 x TMAG5170)\n+ Z-lift servo XL330", xy=(hm["center"][0], hm["center"][1]),
                xytext=(hm["center"][0] + 40, hm["center"][1] - 90), fontsize=8, color=ink,
                arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))
    ax.annotate("gantry beam + MGN9 rail", xy=(150, byid["beam"]["y0"] + 10), xytext=(170, byid["beam"]["y0"] + 60),
                fontsize=8, color=ink, arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))
    ax.annotate("MGN12 Y rail", xy=(G["yrail_x"][0], 250), xytext=(20, 290), fontsize=8, color=ink,
                arrowprops=dict(arrowstyle="-", color=grey, lw=0.8))

    def dim_h(x1, x2, y, label):
        ax.annotate("", xy=(x2, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", color=ink, lw=0.8))
        ax.text((x1 + x2) / 2, y + 3, label, ha="center", fontsize=8, color=ink)

    def dim_v(y1, y2, x, label):
        ax.annotate("", xy=(x, y2), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", color=ink, lw=0.8))
        ax.text(x - 3, (y1 + y2) / 2, label, rotation=90, ha="right", va="center", fontsize=8, color=ink)

    dim_h(0, bx, -14, f"{bx:.0f}")
    dim_v(0, by, -12, f"{by:.0f}")
    ax.set_xlim(-30, bx + 12)
    ax.set_ylim(-30, by + 12)
    ax.set_aspect("equal")
    ax.set_title("Top view (glass removed); board frame x right, y away from the writer", loc="left", fontsize=10)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.grid(False)
    # ---- section through the head (y-z at the head x)
    ax2 = fig.add_axes([0.51, 0.40, 0.47, 0.53])
    hx, hy = hm["center"][0], hm["center"][1]
    Z = L.z_levels()
    ymin, ymax = hy - 45, hy + 55
    ax2.add_patch(Rectangle((ymin, -G["glass_t"]), ymax - ymin, G["glass_t"], fc=ps.SEQ_BLUE[0], ec=ink, lw=0.8))
    ax2.add_patch(Rectangle((ymin, 0), ymax - ymin, P.STACK["paper_mm"].value, fc=ps.GRID, ec=ink, lw=0.6))
    ax2.add_patch(Rectangle((ymin, L.base_z0()), ymax - ymin, G["base_t"], fc=ps.GRID, ec=ink, lw=0.8))
    for cid in ("carriage_plate", "beam", "xrail", "xblock"):
        c = byid[cid]
        y_0, dy = c["y0"], c["size"][1]
        ax2.add_patch(Rectangle((max(y_0, ymin), c["z0"]), min(y_0 + dy, ymax) - max(y_0, ymin), c["size"][2],
                                fc=colors.get(c["group"], ps.GRID), ec=ink, lw=0.6, alpha=0.8))
    c = byid["zservo"]   # beside the section plane (x + 9 mm): outline only
    ax2.add_patch(Rectangle((c["y0"], c["z0"]), c["size"][1], c["size"][2], fc="none", ec=ps.SERIES[1], lw=1.0, ls="--"))
    for comp_set, alpha, lab in ((comps, 0.95, "working"), (comps_low, 0.35, "retracted")):
        c = {k["id"]: k for k in comp_set}["head_magnet"]
        cz, d, hh = c["center"][2], c["d"], c["h"]
        ax2.add_patch(Rectangle((hy - d / 2, cz - hh / 2), d, hh, fc=ps.SERIES[4], ec=ink, lw=0.8, alpha=alpha))
    ring = byid["hall_ring"]
    for sgn in (-1, 1):
        ax2.add_patch(Rectangle((hy + sgn * ring["d_in"] / 2 if sgn > 0 else hy - ring["d"] / 2, ring["center"][2] - ring["h"] / 2),
                                (ring["d"] - ring["d_in"]) / 2, ring["h"], fc=ps.SERIES[2], ec=ink, lw=0.6))
    ax2.text(ymin + 2, 0.6, "paper", fontsize=7.5, color=ink)
    ax2.text(ymin + 2, -G["glass_t"] + 0.6, f"glass {G['glass_t']:.1f}", fontsize=7.5, color=ink)
    ax2.text(hy + 8, byid["head_magnet"]["center"][2], "head magnet (working)", fontsize=7.5, color=ink)
    ax2.text(hy + 8, byid["head_magnet"]["center"][2] - G["zlift"], f"retracted (-{G['zlift']:.0f} mm)", fontsize=7.5, color=ink)
    ax2.text(hy - 44, ring["center"][2] - 3.6, "Hall ring PCB", fontsize=7.5, color=ink)
    ax2.text(byid["beam"]["y0"] + 1, byid["beam"]["z0"] + 3, "beam", fontsize=7.5, color=ink)
    ax2.text(byid["zservo"]["y0"] - 17, byid["zservo"]["z0"] + 2, "servo\n(beside, x+9)", fontsize=7.5, color=ink)
    gap = P.design_gap_mm()
    ax2.annotate("", xy=(hy - 12, -gap + P.STACK["paper_mm"].value), xytext=(hy - 12, P.STACK["paper_mm"].value),
                 arrowprops=dict(arrowstyle="<->", color=ink, lw=0.8))
    ax2.text(hy - 13.5, -gap / 2, f"gap {gap:.1f}", rotation=90, ha="right", va="center", fontsize=7.5, color=ink)
    ax2.annotate("", xy=(ymax - 5, L.base_z0()), xytext=(ymax - 5, P.STACK["paper_mm"].value),
                 arrowprops=dict(arrowstyle="<->", color=ink, lw=0.8))
    ax2.text(ymax - 6.5, (L.base_z0()) / 2, f"{-L.base_z0():.0f} to the desk", rotation=90, ha="right", va="center", fontsize=7.5, color=ink)
    ax2.set_xlim(ymin, ymax)
    ax2.set_ylim(L.base_z0() - 3, 6)
    ax2.set_aspect("equal")
    ax2.set_title("Section through the head (y-z); z = 0 on the glass", loc="left", fontsize=10)
    ax2.set_xlabel("y (mm)")
    ax2.set_ylabel("z (mm)")
    ax2.grid(False)
    # ---- pen-magnet detail (side view in the pen's vertical plane, 50 deg)
    ax3 = fig.add_axes([0.53, 0.06, 0.44, 0.27])
    a = math.radians(50.0)
    u = (math.cos(a), math.sin(a))
    n = (math.sin(a), -math.cos(a))
    L_axis = 60.0
    ax3.plot([0, L_axis * u[0]], [0, L_axis * u[1]], color=grey, lw=0.8, ls="--")
    for r in (6.47, -6.47):
        ax3.plot([4.66 * u[0] + r * n[0], L_axis * u[0] + r * n[0]], [4.66 * u[1] + r * n[1], L_axis * u[1] + r * n[1]], color=ink, lw=0.8)
    s_m, r_m = P.PEN["pen_magnet_axial_mm"].value, P.PEN["pen_magnet_radial_mm"].value
    cx, cy = s_m * u[0] + r_m * n[0], s_m * u[1] + r_m * n[1]
    dd, hh = P.PEN["pen_magnet_d_mm"].value, P.PEN["pen_magnet_h_mm"].value
    pts = []
    for sa, sr in ((-hh / 2, -dd / 2), (hh / 2, -dd / 2), (hh / 2, dd / 2), (-hh / 2, dd / 2), (-hh / 2, -dd / 2)):
        pts.append((cx + sa * u[0] + sr * n[0], cy + sa * u[1] + sr * n[1]))
    ax3.fill([p[0] for p in pts], [p[1] for p in pts], color=ps.SERIES[4], alpha=0.9)
    ax3.plot([-25, 60], [0, 0], color=ink, lw=1.0)
    ax3.plot([0], [0], marker="o", color=ps.SERIES[0], ms=5)
    ax3.text(0.8, -3.5, "ball", fontsize=7.5, color=ink)
    ax3.text(cx + 6, cy - 2, f"D42-N52 (0.75 g), centre {P.PEN['pen_magnet_height_mm'].value:.1f} mm up,\n"
                            f"{P.PEN['pen_magnet_behind_ball_mm'].value:.1f} mm behind the ball, in a keel\nunder the FIXED front sleeve",
             fontsize=7.5, color=ink)
    ax3.text(28, 30, "pen axis (50 deg)", fontsize=7.5, color=grey)
    ax3.text(10, 22, "nose bore r 6.47 (Rev H)", fontsize=7.5, color=ink)
    ax3.set_xlim(-8, 62)
    ax3.set_ylim(-5, 40)
    ax3.set_aspect("equal")
    ax3.set_title("Pen add-on (side view, the pen's rear to the right)", loc="left", fontsize=10)
    ax3.set_xlabel("mm")
    ax3.grid(False)
    ps.stamp(fig, "proposed design", "concept geometry to scale; catalogue parts as envelopes; nothing built")
    fig.savefig(path)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(OUT_B, exist_ok=True)
    comps = L.components()
    comps_low = L.components(zlift_mm=L.G["zlift"])
    asm = cq.Assembly(name="guidance_board_A4")
    for c in comps:
        asm.add(solid(c), name=c["id"])
    asm.save(os.path.join(OUT, "guidance_board_assembly.step"))
    byid = {c["id"]: c for c in comps}
    byid_low = {c["id"]: c for c in comps_low}
    checks = {"working": interference([("head_magnet", "glass"), ("head_magnet", "carriage_plate"), ("head_magnet", "beam"),
                                        ("zservo", "beam"), ("hall_ring", "glass"), ("carriage_plate", "glass")], byid),
              "retracted": interference([("head_magnet", "beam"), ("head_cup", "base_plate"), ("head_magnet", "zservo")], byid_low)}
    # travel extremes: carriage parts vs walls, motors and rails
    corners = []
    tr = L.travel()
    for hx in tr["x"]:
        for hy in tr["y"]:
            cc = {c["id"]: c for c in L.components(head_xy=(hx, hy))}
            for mv in ("head_magnet", "zservo", "carriage_plate", "hall_ring"):
                for fx in ("wall_left", "wall_right", "wall_front", "motor_A", "motor_B", "yrail_0", "yrail_1", "housing"):
                    r = interference([(mv, fx)], cc)[0]
                    if r["overlap_mm3"] > 1e-3:
                        corners.append({"head_xy": [hx, hy], **r})
    masses, total = mass_estimate(comps)
    min_clear = byid["head_magnet"]["center"][2] + byid["head_magnet"]["h"] / 2
    summary = {
        "board_outer_mm": [*L.G["board"], L.G["housing_top"] - L.base_z0()],
        "writing_surface_above_desk_mm": -L.base_z0(),
        "glass_mm": L.G["glass_t"], "design_gap_mm": P.design_gap_mm(),
        "head_top_below_glass_top_mm": -min_clear,
        "carriage_travel": tr, "paper": L.G["paper"],
        "interference_checks": checks, "travel_corner_interferences": corners,
        "mass_estimate_g": {"total": round(total, 0), "parts": masses,
                            "label": "CALC: MFR masses where known (AMF-90/92/94/96), otherwise volume x density (ASSUMPTION); excludes the external 24 V adaptor, screws and cables"},
        "notes": ["the head magnet hangs beside the gantry beam on a 25 mm cantilever so it can drop 12 mm without hitting the beam",
                  "keep >= 20 mm between the head magnet and the steel MGN9 rail (about 0.8 N upper-bound pull, image-dipole CALC)",
                  "the pen magnet sits in the Rev H front sleeve; its keel geometry is for the Rev H team to confirm"],
    }
    meta = provenance.metadata("proposed design (concept geometry)", extra={"cadquery": cq.__version__, "script": "mechanics/cad/guidance_board.py"})
    provenance.write_json(os.path.join(OUT, "guidance_board_summary.json"), {"meta": meta, "summary": summary})
    png = os.path.join(OUT, "drawing_guidance_board.png")
    drawing(png, comps, comps_low)
    shutil.copyfile(png, os.path.join(OUT_B, "fig_cad_drawing.png"))
    with open(os.path.join(OUT_B, "fig_cad_drawing.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "x0_or_cx_mm", "y0_or_cy_mm", "z0_or_cz_mm", "size_x_or_d_mm",
                    "size_y_or_d_in_mm", "size_z_or_h_mm", "moves_with", "part", "ledger"])
        for c in comps:
            if c["shape"] == "box":
                w.writerow([c["id"], c["label"], c["group"], c["shape"], c["x0"], c["y0"], c["z0"], *c["size"],
                            c["moves_with"], c["part"], c["ledger"]])
            else:
                w.writerow([c["id"], c["label"], c["group"], c["shape"], *c["center"], c["d"], c.get("d_in", ""), c["h"],
                            c["moves_with"], c["part"], c["ledger"]])
    print(json.dumps({k: v for k, v in summary.items() if k not in ("mass_estimate_g",)}, indent=1))
    print("mass estimate (g):", round(total))


if __name__ == "__main__":
    main()
