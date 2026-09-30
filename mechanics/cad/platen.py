"""Moving-paper platen (study P): parametric concept layout; PROPOSED DESIGN, not production CAD or an order BOM.

A5 paper plate on a two-layer XY stage under a fixed palm-rest bridge:
  coarse  cross-slide on miniature rails, belt H-bot with two NEMA 17 closed-loop steppers fixed to the base
          (+-40 mm x +-20 mm): slow page repositioning for accepted words
  fine    stacked XY on miniature guides, one Moticont LVCM-032-025-02 voice coil per axis lying beside the plate
          (+-5 mm usable, 12.7 mm stroke): tremor cancellation and the fast part of accepted writing
  plate   230 x 170 x 6 mm glass-fibre sandwich with a vacuum plenum, clip bar and edge stops, on three load cells and
          a 3 mm Z-drop (pen lift)
  palm rest  a fixed bridge 25 mm above the paper (ISO 13854 finger gap), outside the plate's swept envelope
  camera  a side post with a global-shutter camera looking at the pen tip region
Outputs (results/platen/): platen_assembly.step, drawing_platen.png (top view and front elevation with the main
dimensions) and its CSV twin drawing_platen.csv (component table), cad_summary.json (with stabpen.provenance).
Belt routing, tensioners, cable chain, encoder mounts, the vacuum plenum, the flexures of the Z-drop and every joint
are unresolved keep-outs.  Run: python3 -m mechanics.cad.platen
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "platen"

# ------------------------------------------------------------------ parameters (mm; PROPOSED DESIGN)
BASE = (380.0, 300.0, 6.0)
PLATE = (230.0, 170.0, 6.0)
PAPER = (210.0, 148.0, 0.1)
COARSE_TRAVEL = (40.0, 20.0)
FINE_TRAVEL = 5.0
Z = {"base_top": 6.0, "x_rails_top": 16.0, "x_carriage_top": 21.0, "y_rails_top": 31.0, "y_carriage_top": 36.0,
     "fine_x_top": 44.0, "fine_y_top": 52.0, "zdrop_top": 60.0, "plate_top": 66.0}
PALM_GAP = 25.0            # mm between the paper and the underside of the palm-rest bridge
PALM = {"y": -125.0, "depth": 60.0, "thick": 10.0, "post": (20.0, 30.0)}
VCA = {"d": 31.8, "len": 38.1}          # LVCM-032-025-02 housing, coil at mid-stroke (MANUFACTURER)
NEMA17 = (42.3, 42.3, 48.0)

COMPONENTS = []            # (name, role, box dims / cylinder, centre, colour, label)


def _add(name, role, shape, dims, centre, color, label="PROPOSED DESIGN"):
    COMPONENTS.append({"name": name, "role": role, "shape": shape, "dims": list(dims), "centre": list(centre),
                       "color": color, "label": label})


def layout():
    COMPONENTS.clear()
    bx, by, bz = BASE
    _add("base_plate", "grounded base, rubber feet, reaction to the desk", "box", BASE, (0, 0, bz / 2), (0.72, 0.76, 0.80))
    for sx in (-1, 1):
        for sy in (-1, 1):
            _add(f"foot_{sx}_{sy}", "rubber foot", "cyl", (20.0, 5.0), (sx * (bx / 2 - 20), sy * (by / 2 - 20), -2.5),
                 (0.2, 0.2, 0.2))
    zb = Z["base_top"]
    for sy in (-1, 1):
        _add(f"coarse_x_rail_{sy}", "coarse X miniature rail (9 mm)", "box", (330.0, 9.0, 10.0),
             (0, sy * 80.0, zb + 5.0), (0.55, 0.57, 0.6))
    _add("coarse_x_carriage", "coarse X carriage plate (moves +-40 mm)", "box", (250.0, 200.0, 5.0),
         (0, 0, Z["x_rails_top"] + 2.5), (0.62, 0.66, 0.72))
    for sx in (-1, 1):
        _add(f"coarse_y_rail_{sx}", "coarse Y miniature rail", "box", (9.0, 230.0, 10.0),
             (sx * 95.0, 0, Z["x_carriage_top"] + 5.0), (0.55, 0.57, 0.6))
    _add("coarse_y_carriage", "coarse Y carriage = fine-stage base (moves +-20 mm)", "box", (260.0, 190.0, 5.0),
         (0, 0, Z["y_rails_top"] + 2.5), (0.62, 0.66, 0.72))
    for sx in (-1, 1):
        _add(f"hbot_motor_{sx}", "NEMA 17 closed-loop stepper, fixed to the base (H-bot)", "box", NEMA17,
             (sx * (bx / 2 - 30), by / 2 - 30, zb + NEMA17[2] / 2), (0.3, 0.32, 0.36), "PROPOSED DESIGN (MANUFACTURER envelope)")
    _add("hbot_belt_keepout", "GT2 belt path of the H-bot (routing unresolved)", "box", (340.0, 6.0, 8.0),
         (0, by / 2 - 30, zb + 30), (0.1, 0.1, 0.1))
    _add("fine_x_frame", "fine X frame on miniature guides (moves +-5 mm)", "box", (240.0, 180.0, 4.0),
         (0, 0, Z["fine_x_top"] - 2.0), (0.47, 0.62, 0.8))
    _add("fine_y_carrier", "fine Y carrier on miniature guides (moves +-5 mm)", "box", (234.0, 174.0, 4.0),
         (0, 0, Z["fine_y_top"] - 2.0), (0.47, 0.62, 0.8))
    _add("vca_x", "voice coil X (LVCM-032-025-02), beside the plate", "cyl_x", (VCA["d"], VCA["len"]),
         (PLATE[0] / 2 + 24.0, 0, Z["fine_x_top"] - 2.0), (0.82, 0.60, 0.2), "MANUFACTURER envelope")
    _add("vca_y", "voice coil Y (LVCM-032-025-02), behind the plate", "cyl_y", (VCA["d"], VCA["len"]),
         (0, PLATE[1] / 2 + 24.0, Z["fine_y_top"] - 2.0), (0.82, 0.60, 0.2), "MANUFACTURER envelope")
    for i, (x, y) in enumerate([(-90.0, -60.0), (90.0, -60.0), (0.0, 65.0)]):
        _add(f"load_cell_zdrop_{i}", "load cell + Z-drop solenoid under the plate (contact force, 3 mm lift)", "cyl",
             (14.0, 8.0), (x, y, Z["fine_y_top"] + 4.0), (0.85, 0.3, 0.3))
    _add("paper_plate", "paper plate with vacuum plenum (glass-fibre sandwich, non-metallic)", "box", PLATE,
         (0, 0, Z["zdrop_top"] + PLATE[2] / 2), (0.93, 0.93, 0.88))
    _add("paper_A5", "A5 sheet (210 x 148 mm)", "box", PAPER, (0, -5.0, Z["plate_top"] + PAPER[2] / 2),
         (1.0, 1.0, 1.0))
    _add("clip_bar", "hinged clip bar with two edge stops (registration)", "box", (PLATE[0], 12.0, 4.0),
         (0, PLATE[1] / 2 - 6.0, Z["plate_top"] + 2.0), (0.25, 0.25, 0.28))
    swept = (PLATE[0] + 2 * (COARSE_TRAVEL[0] + FINE_TRAVEL), PLATE[1] + 2 * (COARSE_TRAVEL[1] + FINE_TRAVEL), 0.5)
    _add("plate_swept_envelope", "keep-out: plate swept by coarse + fine travel", "box", swept,
         (0, 0, Z["plate_top"] + 0.25), (0.15, 0.65, 0.76))
    zp = Z["plate_top"] + PALM_GAP
    for sx in (-1, 1):
        _add(f"palm_post_{sx}", "palm-rest post (fixed to the base, outside the swept envelope)", "box",
             (PALM["post"][0], PALM["post"][1], zp - zb + PALM["thick"]),
             (sx * (swept[0] / 2 + 15.0), PALM["y"], zb + (zp - zb + PALM["thick"]) / 2), (0.4, 0.42, 0.45))
    _add("palm_rest_bridge", "palm-rest bridge, padded, 25 mm above the paper (adjustable 15-35 mm)", "box",
         (swept[0] + 60.0, PALM["depth"], PALM["thick"]), (0, PALM["y"], zp + PALM["thick"] / 2), (0.55, 0.45, 0.35))
    _add("camera_post", "camera post (side arm)", "box", (16.0, 16.0, 190.0), (bx / 2 - 12.0, -20.0, zb + 95.0),
         (0.4, 0.42, 0.45))
    _add("camera", "global-shutter camera looking down at about 45 deg at the tip region", "box", (30.0, 40.0, 30.0),
         (bx / 2 - 30.0, -20.0, zb + 180.0), (0.15, 0.15, 0.17), "PROPOSED DESIGN (MANUFACTURER class: OV9281)")
    _add("electronics_box", "drivers, MCU, single-board computer, 24 V supply entry", "box", (300.0, 30.0, 34.0),
         (0, by / 2 - 70.0, zb + 17.0), (0.25, 0.3, 0.25))
    return COMPONENTS


def build(out: Path = OUT):
    import cadquery as cq
    comps = layout()
    asm = cq.Assembly(name="Moving_paper_platen_A5_concept")
    parts = []
    for c in comps:
        if c["shape"] == "box":
            obj = cq.Workplane("XY").box(*c["dims"]).translate(tuple(c["centre"]))
        elif c["shape"] == "cyl":
            d, h = c["dims"]
            obj = cq.Workplane("XY").circle(d / 2).extrude(h).translate((c["centre"][0], c["centre"][1],
                                                                         c["centre"][2] - h / 2))
        elif c["shape"] == "cyl_x":
            d, L = c["dims"]
            obj = cq.Workplane("YZ").circle(d / 2).extrude(L).translate((c["centre"][0] - L / 2, c["centre"][1],
                                                                         c["centre"][2]))
        elif c["shape"] == "cyl_y":
            d, L = c["dims"]
            obj = cq.Workplane("XZ").circle(d / 2).extrude(-L).translate((c["centre"][0], c["centre"][1] - L / 2,
                                                                          c["centre"][2]))
        else:
            raise KeyError(c["shape"])
        asm.add(obj, name=c["name"], color=cq.Color(*c["color"]))
        parts.append({"name": c["name"], "role": c["role"], "label": c["label"], "volume_mm3": obj.val().Volume()})
    out.mkdir(parents=True, exist_ok=True)
    step = out / "platen_assembly.step"
    asm.export(str(step)) if hasattr(asm, "export") else asm.save(str(step))
    return step, parts


def drawing(path_png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    comps = layout()
    SURF, INK2, MUTED = "#fcfcfb", "#52514e", "#898781"
    fig = plt.figure(figsize=(13.5, 7.2), facecolor=SURF)
    ax = fig.add_axes([0.04, 0.12, 0.52, 0.78], facecolor=SURF)
    ex = fig.add_axes([0.61, 0.40, 0.37, 0.50], facecolor=SURF)
    order = ["base_plate", "coarse", "hbot", "electronics", "fine", "vca", "load", "paper_plate", "paper_A5", "clip",
             "plate_swept", "palm", "camera"]

    def rank(c):
        for i, o in enumerate(order):
            if c["name"].startswith(o):
                return i
        return len(order)
    for c in sorted(comps, key=rank):
        col = c["color"]
        cx, cy, cz = c["centre"]
        if c["shape"] == "box":
            w, d, h = c["dims"]
        elif c["shape"] == "cyl":
            w = d = c["dims"][0]; h = c["dims"][1]
        elif c["shape"] == "cyl_x":
            w, d, h = c["dims"][1], c["dims"][0], c["dims"][0]
        else:
            w, d, h = c["dims"][0], c["dims"][1], c["dims"][0]
        swept = c["name"] == "plate_swept_envelope"
        palm = c["name"].startswith("palm_rest")
        kw = dict(fill=not swept, facecolor=col, edgecolor="#333333" if not swept else (0.15, 0.65, 0.76),
                  lw=0.6 if not swept else 1.4, alpha=(0.55 if palm else 0.9) if not swept else 1.0)
        if c["name"].startswith("foot"):
            continue
        if c["shape"] == "cyl":
            ax.add_patch(Circle((cx, cy), w / 2, **kw))
        else:
            ax.add_patch(Rectangle((cx - w / 2, cy - d / 2), w, d, **kw))
        if c["name"] in ("base_plate", "hbot_belt_keepout") or c["name"].startswith("foot"):
            pass
        ex.add_patch(Rectangle((cx - w / 2, cz - h / 2), w, h, **kw))
    bx, by, _ = BASE
    ax.set_xlim(-bx / 2 - 15, bx / 2 + 15)
    ax.set_ylim(-by / 2 - 15, by / 2 + 15)
    ax.set_aspect("equal")
    ax.set_title("Top view (mm): A5 plate at centre; cyan outline = plate swept by coarse (+-40 x +-20) + fine (+-5) "
                 "travel", fontsize=9, loc="left")
    ax.annotate("", xy=(bx / 2, -by / 2 - 8), xytext=(-bx / 2, -by / 2 - 8), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text(0, -by / 2 - 13, f"{bx:.0f}", ha="center", fontsize=8, color=INK2)
    ax.annotate("", xy=(-bx / 2 - 8, by / 2), xytext=(-bx / 2 - 8, -by / 2), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text(-bx / 2 - 13, 0, f"{by:.0f}", va="center", rotation=90, fontsize=8, color=INK2)
    ax.text(0, PALM["y"], "palm-rest bridge (fixed)", ha="center", va="center", fontsize=8, color="w")
    ax.text(0, -5, "A5 sheet on the paper plate", ha="center", fontsize=8, color=INK2)
    ax.text(PLATE[0] / 2 + 24, 22, "VCA X", ha="center", fontsize=7.5, color=INK2)
    ax.text(0, PLATE[1] / 2 + 45, "VCA Y", ha="center", fontsize=7.5, color=INK2)
    for sx in (-1, 1):
        ax.text(sx * (bx / 2 - 30), by / 2 - 20, "H-bot\nmotor", ha="center", va="center", fontsize=7, color="w",
                zorder=5)
    ax.text(bx / 2 - 30, -20 - 30, "camera\n(on a post)", ha="center", va="top", fontsize=7.5, color=INK2)
    ax.tick_params(labelsize=7)
    ex.set_xlim(-bx / 2 - 15, bx / 2 + 15)
    ex.set_ylim(-10, 215)
    ex.set_aspect("equal")
    ex.set_title("Front elevation (x-z, mm): stack heights", fontsize=9, loc="left")
    zp = Z["plate_top"]
    for zz, t in ((zp, f"paper {zp:.0f}"), (zp + PALM_GAP, f"palm-rest underside {zp + PALM_GAP:.0f} (25 mm gap)")):
        ex.axhline(zz, color=MUTED, lw=0.8)
        ex.text(-120, zz + 3, t, fontsize=7.5, color=INK2)
    ex.tick_params(labelsize=7)
    # component table (text) under the elevation
    tx = fig.add_axes([0.61, 0.05, 0.37, 0.30])
    tx.axis("off")
    lines = ["Main dimensions and budgets (PROPOSED DESIGN; CALC in platen/design.py):",
             f"  base {BASE[0]:.0f} x {BASE[1]:.0f} mm; paper surface {zp:.0f} mm above the desk",
             f"  plate {PLATE[0]:.0f} x {PLATE[1]:.0f} x {PLATE[2]:.0f} mm; A5 sheet; clip bar + 3 edge stops",
             f"  coarse travel +-{COARSE_TRAVEL[0]:.0f} x +-{COARSE_TRAVEL[1]:.0f} mm (H-bot, 2 NEMA 17, 20 N cap)",
             f"  fine travel +-{FINE_TRAVEL:.0f} mm (2 x LVCM-032-025-02, 12.7 mm stroke, 40 Hz, 20 N cap)",
             "  moving mass: fine X 0.59 kg, coarse 1.42 kg (CALC)",
             "  Z-drop 3 mm on 3 load cells (contact force, pen lift)",
             "  palm rest 25 mm above the paper, outside the swept envelope",
             "Unresolved: belts and tensioners, cable chain, encoders, plenum,",
             "  Z-drop flexures, joints, covers and skirts, ergonomics of the rest height."]
    tx.text(0, 1, "\n".join(lines), va="top", fontsize=7.8, family="monospace", color="#0b0b0b")
    fig.text(0.04, 0.03, "Moving-paper platen, A5 concept (study P). PROPOSED DESIGN: nothing built or measured. "
                         "STEP: results/platen/platen_assembly.step.", fontsize=8.5, color=INK2)
    fig.savefig(path_png, dpi=150, facecolor=SURF)
    plt.close(fig)
    with open(Path(path_png).with_suffix(".csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "role", "shape", "dims_mm", "centre_mm", "label"])
        for c in comps:
            w.writerow([c["name"], c["role"], c["shape"], " x ".join(f"{v:g}" for v in c["dims"]),
                        ", ".join(f"{v:g}" for v in c["centre"]), c["label"]])


def main():
    sys.path.insert(0, str(ROOT))
    step, parts = build(OUT)
    drawing(OUT / "drawing_platen.png")
    try:
        from stabpen import provenance as PV
        prov = PV.metadata("PROPOSED DESIGN (concept layout; keep-outs; no interference certification)",
                           extra={"package": "mechanics.cad.platen", "step": str(step.relative_to(ROOT))})
    except Exception as e:                   # provenance must not stop the export
        prov = {"error": repr(e)}
    summary = {"stabpen.provenance": prov, "status": "PROPOSED layout; nothing built or measured",
               "parameters_mm": {"base": BASE, "plate": PLATE, "paper": PAPER, "coarse_travel": COARSE_TRAVEL,
                                 "fine_travel": FINE_TRAVEL, "z": Z, "palm_gap": PALM_GAP},
               "parts": parts,
               "unresolved": ["belt routing and tensioners of the H-bot", "cable chain to the moving stages",
                              "encoder scales and read heads", "vacuum plenum and seals", "Z-drop flexures and solenoid "
                              "mounts", "guards, skirts and covers (pinch points at the plate edges)",
                              "ergonomics of the palm-rest height"]}
    (OUT / "cad_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(step)


if __name__ == "__main__":
    main()
