#!/usr/bin/env python3
"""PCB area and height feasibility study for the Rev A research electronics.

Evidence status: CALCULATION from KiCad library footprint courtyards (F.CrtYd)
and the CAD envelope (mechanics/cad/pen_revA.py: main PCB 29 x 11.5 mm,
1.2 mm component height per side).  Not a layout: a shelf-packing of courtyard
rectangles shows whether the parts can fit at all and how dense the board is.

Boards: main (in the barrel, z 71-100 mm), tail (USB-C at the cap end),
hall_flex (sensor at the lever tail), bench (DNP force option on an adapter).
Run: python3 electronics/gen/placement_study.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

FPDIR = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
BOARD = {**{r: "tail" for r in ("J1", "U1", "R1", "R2")},
         **{r: "hall_flex" for r in ("U10", "C31", "R15", "U11", "U12", "C32", "C33")},
         **{r: "bench" for r in ("U9", "C28", "C29", "C30", "J8")}}
MAIN_W, MAIN_L = 11.5, 29.0
ANT_KEEPOUT_L = 5.0          # mm of board length kept clear around the chip antenna (both sides)
EDGE = 0.25                  # mm edge clearance
# typical seated heights (mm); VERIFY against datasheets / 3D models before layout
HEIGHT = {"Nordic_AQFN": 0.85, "WSON-8-1EP_6x5": 0.8, "WSON-8-1EP_2x2": 0.8, "WSON-6": 0.8, "SOT-23-8": 1.1,
          "SOT-23-5": 1.45, "SOT-23-6": 1.45, "SOT-23": 1.12, "X2SON": 0.4, "USON": 0.55, "SOT-883": 0.5, "Molex_54548": 1.2, "SOT-666": 0.6, "SOT-723": 0.55, "SOT-353": 1.1, "SOT-363": 1.1, "VSSOP-8_2.3x2": 0.9,
          "VSSOP-8_3x3": 1.1, "LGA-14": 0.86, "Crystal_SMD_2016": 0.55, "Crystal_SMD_2012": 0.6,
          "Johanson_2450AT18": 1.0, "TE_0-1734839": 1.2, "Tag-Connect": 0.0, "SolderWirePad": 0.05,
          "SW_Push_1P1T_NO_CK_KMR2": 1.9, "TestPoint": 0.05, "USB_C": 3.3, "_0402_": 0.55, "_0603_": 0.9,
          "TSSOP-16": 1.2, "JST_SH": 2.95, "SOD-523": 0.7}


def board_of(ref):
    return BOARD.get(ref, "main")


def courtyard(fp):
    lib, name = fp.split(":", 1)
    path = os.path.join(FPDIR, f"{lib}.pretty", f"{name}.kicad_mod")
    txt = open(path, encoding="utf-8").read()
    xs, ys = [], []
    # every (start|end|xy|center) coordinate inside an element on F.CrtYd
    for m in re.finditer(r"\((fp_line|fp_rect|fp_poly|fp_circle)(.*?)\(layer \"?F\.CrtYd\"?\)", txt, re.S):
        for x, y in re.findall(r"\((?:start|end|xy|center)\s+(-?[\d.]+)\s+(-?[\d.]+)\)", m.group(2)):
            xs.append(float(x)); ys.append(float(y))
    if not xs:   # fall back to pad extents + 0.25 mm
        for x, y, sx, sy in re.findall(r"\(pad .*?\(at (-?[\d.]+) (-?[\d.]+).*?\(size ([\d.]+) ([\d.]+)\)", txt, re.S):
            xs += [float(x) - float(sx) / 2 - 0.25, float(x) + float(sx) / 2 + 0.25]
            ys += [float(y) - float(sy) / 2 - 0.25, float(y) + float(sy) / 2 + 0.25]
    return max(xs) - min(xs), max(ys) - min(ys)


def height(fp):
    for k, h in HEIGHT.items():
        if k in fp:
            return h
    return None


def shelf_pack(rects, W, L):
    """First-fit decreasing-height shelf packing along the board length.
    rects: list of (ref, w, h); a part may rotate 90 deg to fit the width.
    Returns placements and the used length."""
    items = []
    for ref, w, h in rects:
        a, b = max(w, h), min(w, h)
        if a <= W:                     # long side across the board: shorter shelves
            items.append((ref, a, b))
        else:
            items.append((ref, b, a))
    items.sort(key=lambda r: -r[2])
    shelves = []                        # [y0, height, x_used]
    placed = []
    y = 0.0
    for ref, w, h in items:
        for s in shelves:
            if s[2] + w <= W and h <= s[1]:
                placed.append((ref, s[2], s[0], w, h)); s[2] += w
                break
        else:
            shelves.append([y, h, w]); placed.append((ref, 0.0, y, w, h)); y += h
    return placed, y


# Rev A.1 package plan ("min"): substitutions evaluated for area only.  Changing a
# footprint needs the matching symbol/pin map, so the schematic keeps the
# verified library symbols until each substitution is confirmed (VERIFY/SELECT).
MIN_FP = {"J4": "Connector_FFC-FPC:Molex_54548-1071_1x10-1MP_P0.5mm_Horizontal",   # one nose flex for 3 modules
          "U15": "Package_SON:Texas_X2SON-5_0.8x0.8mm_P0.48mm", "U16": "Package_SON:Texas_X2SON-5_0.8x0.8mm_P0.48mm",
          "U19": "Package_SON:Texas_X2SON-5_0.8x0.8mm_P0.48mm", "U20": "Package_SON:Texas_X2SON-5_0.8x0.8mm_P0.48mm",
          "U4": "Package_SON:Texas_X2SON-4_1x1mm_P0.65mm",
          "U21": "Package_SON:Winbond_USON-8-2EP_3x4mm_P0.8mm_EP0.2x0.8mm",
          "Q3": "Package_TO_SOT_SMD:SOT-883", "Q4": "Package_TO_SOT_SMD:SOT-883"}
MIN_REMOVE = {"J5", "J6"}                               # merged into the single nose-flex connector
MIN_SIZE = {"Q1": (2.0, 2.0), "Q2": (0.0, 0.0)}         # dual common-drain NMOS, 1.5 mm WLCSP class (SELECT)
MIN_TAIL = {"U2", "R3", "C1", "R5", "R6"}               # charger and VBUS divider move to the USB tail board
MIN_NOTES = ["comparators: TLV7021-class open-drain in X2SON-5 (VERIFY)", "LDO: TLV755 in X2SON-4 (VERIFY)",
             "flash: 64-128 Mbit in USON 3x4 (VERIFY)", "0402 -> 0201 for all R/C below 1 uF",
             "optical modules on one 10-pin nose flex", "charger on the tail board"]


def variant_rows(rows, parts_by_ref, variant):
    out = []
    for r in rows:
        r = dict(r)
        if variant == "min":
            ref = r["ref"]
            if ref in MIN_REMOVE:
                continue
            if ref in MIN_TAIL:
                r["board"] = "tail"
            fp = MIN_FP.get(ref)
            p = parts_by_ref[ref]
            if fp is None and p.lib_id in ("Device:R", "Device:C") and "0402" in p.footprint and p.value not in ("1u", "4u7", "10u"):
                fp = p.footprint.replace("0402_1005Metric", "0201_0603Metric")
            if fp:
                r["footprint"] = fp
                r["w"], r["h"] = courtyard(fp)
                r["height_mm"] = height(fp)
            if ref in MIN_SIZE:
                r["w"], r["h"] = MIN_SIZE[ref]
            r["area"] = r["w"] * r["h"]
        out.append(r)
    return out


def evaluate(rows, board_len):
    W = MAIN_W - 2 * EDGE
    L_side = board_len - ANT_KEEPOUT_L - 2 * EDGE
    # the chip antenna sits inside its own keep-out zone at the board end
    main = sorted([r for r in rows if r["board"] == "main" and r["ref"] != "AE1"], key=lambda r: -r["area"])
    sides = {"A": [], "B": []}
    area = {"A": 0.0, "B": 0.0}
    for r in main:
        s = "A" if (r["ref"] in ("U7", "Y1", "Y2", "L1") or area["A"] <= area["B"]) else "B"
        sides[s].append(r); area[s] += r["area"]
    packs = {}
    for name, side in sides.items():
        pl, used = shelf_pack([(r["ref"], r["w"], r["h"]) for r in side], W, L_side)
        packs[name] = {"used_length_mm": used, "available_length_mm": L_side, "fits": used <= L_side,
                       "courtyard_area_mm2": area[name], "placements": pl}
    avail = 2 * W * L_side
    tot = sum(r["area"] for r in main)
    return {"board_length_mm": board_len, "available_area_mm2_two_sides": avail, "courtyard_area_mm2": tot,
            "density": tot / avail, "fits_shelf_pack": all(p["fits"] for p in packs.values()),
            "parts_over_1p2mm": [(r["ref"], r["height_mm"]) for r in main if (r["height_mm"] or 0) > 1.2]}, packs


def main():
    from design_revA import build
    from stabpen import plotstyle, provenance
    parts = [p for s in build() for p in s.parts]
    rows = []
    for p in parts:
        w, h = courtyard(p.footprint)
        rows.append({"ref": p.ref, "footprint": p.footprint, "board": board_of(p.ref), "w": w, "h": h,
                     "area": w * h, "height_mm": height(p.footprint), "dnp": p.dnp})
    parts_by_ref = {p.ref: p for p in parts}
    out = {"boards": {}, "cases": {}}
    for b in ("main", "tail", "hall_flex", "bench"):
        rs = [r for r in rows if r["board"] == b]
        out["boards"][b] = {"n_parts": len(rs), "courtyard_area_mm2": sum(r["area"] for r in rs),
                            "tallest": max(((r["height_mm"] or 0), r["ref"]) for r in rs) if rs else None}
    best = None
    for variant in ("as_drawn", "min"):
        vr = variant_rows(rows, parts_by_ref, variant)
        for L in (MAIN_L, MAIN_L + 12.0):
            res, packs = evaluate(vr, L)
            out["cases"][f"{variant}_{L:g}mm"] = res
            if variant == "min" and L == MAIN_L + 12.0:
                best = (variant, L, packs)
    out.update({"parts": rows, "min_variant_notes": MIN_NOTES,
                "notes": ["courtyard area excludes routing: keep density below ~0.6 for a 6-8 layer HDI board with an aQFN94",
                          "board length +12 mm assumes the 44 mm 10440 bay is replaced by a ~32 mm pouch cell (CAD update pending)",
                          "SOT-23-5/6 (DBV) parts are 1.45 mm tall and exceed the 1.2 mm envelope; the min variant replaces most of them"]})
    meta = provenance.metadata("calculation (library courtyards; CAD envelope); not a PCB layout")
    os.makedirs(os.path.join(ROOT, "results", "electronics"), exist_ok=True)
    provenance.write_json(os.path.join(ROOT, "results", "electronics", "placement_study.json"), {"meta": meta, **out})
    variant, L_best, packs = best
    L_side = L_best - ANT_KEEPOUT_L - 2 * EDGE
    plotstyle.apply()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axs = plt.subplots(2, 1, figsize=(11.5, 4.6))
    for ax, name in zip(axs, ("A", "B")):
        ax.add_patch(Rectangle((0, 0), L_best, MAIN_W, fill=False, ec=plotstyle.INK2, lw=1.2))
        ax.add_patch(Rectangle((L_best - ANT_KEEPOUT_L, 0), ANT_KEEPOUT_L, MAIN_W, fc=plotstyle.GRID, ec="none"))
        ax.text(L_best - ANT_KEEPOUT_L / 2, MAIN_W / 2 + (2.2 if name == "A" else 0), "antenna\nkeep-out", ha="center", va="center", fontsize=7, color=plotstyle.INK2)
        if name == "A":
            aw, ah = courtyard("RF_Antenna:Johanson_2450AT18x100")
            ax.add_patch(Rectangle((L_best - ANT_KEEPOUT_L / 2 - aw / 2, 1.0), aw, ah, fc=plotstyle.SERIES[3], ec=plotstyle.SURFACE, lw=1.0))
            ax.text(L_best - ANT_KEEPOUT_L / 2, 1.0 + ah / 2, "AE1", ha="center", va="center", fontsize=6, color=plotstyle.INK)
        for ref, x, y, w, h in packs[name]["placements"]:
            # packing runs along the board length: y -> board x
            col = plotstyle.SERIES[0] if ref.startswith("U") else plotstyle.SERIES[2] if ref.startswith(("C", "R", "L", "FB")) else plotstyle.SERIES[3]
            ax.add_patch(Rectangle((EDGE + y, EDGE + x), h, w, fc=col, ec=plotstyle.SURFACE, lw=1.0, alpha=0.85))
            if w * h > 3:
                ax.text(EDGE + y + h / 2, EDGE + x + w / 2, ref, ha="center", va="center", fontsize=6, color=plotstyle.INK)
        ax.set_xlim(-0.5, L_best + 0.5); ax.set_ylim(-0.5, MAIN_W + 0.5); ax.set_aspect("equal")
        ax.set_ylabel("width (mm)")
        ax.set_title(f"Side {name}: courtyards shelf-packed, {packs[name]['used_length_mm']:.1f} of {L_side:.1f} mm used", loc="left", fontsize=10)
    axs[1].set_xlabel("board length (mm), nib side at 0")
    fig.suptitle(f"Rev A.1 package plan on a {L_best:g} mm board (courtyards only; routing not included)", x=0.01, ha="left", fontsize=11)
    plotstyle.stamp(fig, "calculation", "area feasibility only, not a layout; blue ICs, green passives, amber other")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "results", "electronics", "fig_placement_study.png"))
    print(json.dumps(out["cases"], indent=1, default=str))


if __name__ == "__main__":
    main()
