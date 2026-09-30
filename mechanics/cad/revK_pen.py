#!/usr/bin/env python3
"""Parametric CAD concept of the Rev K pen (CadQuery 2.x): study B's balanced translation nib B1 in the Rev J body, with
Rev K's ball thrust guide, C17200 wire leads, the counter-face head (roll cage, carriage, tilted face, captive shoe, three
SQUIGGLE positioners), the LIR14500 and the cue LRA; the heel module as an optional variant.

Evidence status: PROPOSED DESIGN (dimensioned concept).  Every dimension comes from results/revK/layout.json (written by
python3 -m revk.run; rebuilt here if missing).  The fit checks here are on solids (pairwise boolean intersections at rest
and with the nib moved to its stop in eight directions); the layout's own 57 checks are in layout.json.  Nothing was built
or measured.

Datums: origin at the ball tip (50 deg, nib centred), z along the pen axis toward the back, x in the tilt plane (positive
away from the paper), y lateral, mm.  The counter-face, its shoe and the refill holder's joint are drawn at 50 deg, roll 0.
Outputs (results/revK/):
  revK_pen_assembly.step              the base pen
  revK_pen_assembly_heel.step         the heel-module variant (--heel)
  drawing_revK_pen.png + .csv         side section with the nib at +-stop dashed, hand zones, paper lines, six sections;
                                      the CSV twin is the component table
  revK_cad_summary.json               geometry, solid fit checks, STEP status (stabpen.provenance)
Run: python3 mechanics/cad/revK_pen.py [--heel] [--no-step] [--layout results/revK/layout.json]
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mechanics", "cad"))

import numpy as np  # noqa: E402

import revH_pen as RC  # noqa: E402  (read-only reuse: solid())

OUT = os.path.join(ROOT, "results", "revK")
COLORS = dict(RC.COLORS)
COLORS.update({"skid": (0.15, 0.17, 0.20), "drive": (0.05, 0.60, 0.45), "moving_nib": (0.95, 0.55, 0.15),
               "balance": (0.10, 0.55, 0.75)})
TILT = 50.0

# intended contacts (not interferences): clamped wire ends, balls between races and flange, the cup on the refill,
# the stop bush at the stop, parts carried on the board or on the cage
INTENDED = {frozenset(p) for p in [
    ("wire_1", "carrier_flange"), ("wire_2", "carrier_flange"), ("wire_3", "carrier_flange"), ("wire_4", "carrier_flange"),
    ("wire_1", "anchor_ring"), ("wire_2", "anchor_ring"), ("wire_3", "anchor_ring"), ("wire_4", "anchor_ring"),
    ("front_balls", "front_race"), ("front_balls", "carrier_flange"), ("rear_balls", "carrier_flange"),
    ("rear_balls", "rear_race"), ("refill", "refill_holder"), ("carrier", "carrier_front_guide"),
    ("carrier", "carrier_rear_guide"), ("carrier_rear_guide", "carrier_flange"), ("carrier", "carrier_flange"),
    ("coil_x", "coil_y"), ("main_board", "board_parts"), ("main_board", "imu"), ("head_cage", "head_carriage"),
    ("head_face", "head_float"), ("head_cage", "head_tilt_motor"), ("head_cage", "head_balance_spring"),
    ("head_tilt_motor", "head_balance_spring"), ("head_shoe", "head_face"), ("refill_holder", "head_shoe"),
    ("battery", "lra"), ("shell", "rear_cap"), ("rear_cap", "charging_pads"), ("front_sleeve", "shell"),
    ("front_cone_1", "front_cone_2"), ("front_cone_2", "front_cone_3"), ("front_cone_3", "front_sleeve"),
    ("skid_ring", "front_cone_1"), ("keeper", "front_race"), ("back_plate", "pole_magnet_1"), ("back_plate", "pole_magnet_2"),
    ("back_plate", "pole_magnet_3"), ("back_plate", "pole_magnet_4"), ("head_roll_motor", "bulkhead"),
    ("head_follower_motor", "bulkhead"), ("head_flex", "bulkhead"), ("coil_x", "carrier"), ("coil_y", "carrier"),
    ("position_magnet", "carrier_flange"), ("drive_front_transfer", "drive_inner_shaft_drive"),
    ("drive_front_transfer", "drive_inner_shaft_steering"), ("drive_front_transfer", "drive_shaft_drive"),
    ("drive_front_transfer", "drive_shaft_steering"), ("drive_transfer", "drive_shaft_drive"),
    ("drive_transfer", "drive_shaft_steering"), ("drive_transfer", "drive_motor"), ("drive_transfer", "steer_motor"),
    ("drive_pod", "drive_fork"), ("drive_pod", "drive_sensors"), ("drive_fork", "drive_wheel"),
    ("drive_pod", "drive_inner_shaft_drive"), ("drive_pod", "drive_inner_shaft_steering"),
]}


def load_layout(path: str) -> dict:
    if not os.path.exists(path):
        from revk import run as RR
        RR.main(["--no-figures"])
    with open(path) as f:
        return json.load(f)


def _n50():
    th = math.radians(TILT)
    return np.array([math.cos(th), 0.0, math.sin(th)])


def part_solid(c: dict, geo: dict):
    import cadquery as cq
    cid = c["id"]
    if cid == "head_face":
        P = np.array(c["plate_corners_50deg"])
        o = P[0]
        eu = P[4] - P[0]
        ev = P[2] - P[0]
        en = P[1] - P[0]
        Lu, W, T = np.linalg.norm(eu), np.linalg.norm(ev), np.linalg.norm(en)
        pl = cq.Plane(origin=tuple(o), xDir=tuple(eu / Lu), normal=tuple(en / T))
        return cq.Workplane(pl).rect(Lu, W, centered=False).extrude(T)
    if c.get("cad") == "tilted_shoe":
        n = _n50()
        hold = next(x for x in geo["components"] if x["id"] == "refill_holder")
        C = np.array([0.0, 0.0, hold["joint_z"]])
        base = C + (c["r_pb"] - 0.7) * n
        disc = cq.Solid.makeCylinder(c["shoe_d"] / 2, 0.6, cq.Vector(*base), cq.Vector(*n))
        hole = cq.Solid.makeCylinder(0.65, 0.6, cq.Vector(*base), cq.Vector(*n))
        return cq.Workplane("XY").add(disc.cut(hole))
    if c.get("cad") == "cup_stem_ball":
        zr = c["z0"] + 1.2
        cup = cq.Solid.makeCylinder(1.6, 1.2, cq.Vector(0, 0, c["z0"])).cut(cq.Solid.makeCylinder(1.175, 1.2, cq.Vector(0, 0, c["z0"])))
        disc = cq.Solid.makeCylinder(1.6, 0.6, cq.Vector(0, 0, zr))
        rb = c["joint_ball_d"] / 2
        stem = cq.Solid.makeCylinder(0.3, max(c["joint_z"] - rb - (zr + 0.6), 0.05) + 0.1, cq.Vector(0, 0, zr + 0.6))
        ball = cq.Solid.makeSphere(rb, cq.Vector(0, 0, c["joint_z"]))
        return cq.Workplane("XY").add(cup.fuse(disc).fuse(stem).fuse(ball))
    s = RC.solid(c)
    if c["shape"] == "box" and c.get("d_in"):
        h = c["z1"] - c["z0"]
        ox, oy = c.get("offset", [0.0, 0.0])
        s = s.cut(cq.Workplane("XY").circle(c["d_in"] / 2).extrude(h).translate((ox, oy, c["z0"])))
    return s


def solids(geo: dict, comps: list) -> dict:
    out, failed = {}, []
    for c in comps:
        try:
            out[c["id"]] = part_solid(c, geo)
        except Exception as e:                    # keep going; report the part
            failed.append(f"{c['id']}: {e}")
    return out, failed


def _shape(w):
    return w.val() if hasattr(w, "val") else w


def _bbox_overlap(a, b, tol=0.0):
    A, B = a.BoundingBox(), b.BoundingBox()
    return not (A.xmax < B.xmin - tol or B.xmax < A.xmin - tol or A.ymax < B.ymin - tol or B.ymax < A.ymin - tol
                or A.zmax < B.zmin - tol or B.zmax < A.zmin - tol)


def interferences(sol: dict, pairs=None, vol_tol=1e-3) -> list:
    shp = {k: _shape(v) for k, v in sol.items()}
    keys = list(shp)
    hits = []
    it = pairs if pairs is not None else itertools.combinations(keys, 2)
    for a, b in it:
        if frozenset((a, b)) in INTENDED:
            continue
        sa, sb = shp[a], shp[b]
        if not _bbox_overlap(sa, sb):
            continue
        try:
            v = sa.intersect(sb).Volume()
        except Exception:
            continue
        if v > vol_tol:
            hits.append({"a": a, "b": b, "volume_mm3": v})
    return hits


def at_stop_checks(geo: dict, sol: dict, stop: float) -> list:
    """The moving nib (refill, carrier, coils, flange, magnet, refill holder, shoe) translated to its stop in eight
    directions (the refill, its holder and the shoe also slide along the pen so that the ball stays on the paper at 50 deg)
    against every fixed part except the wires (they bend), the balls (they roll) and the lateral stop (touches)."""
    moving = [c["id"] for c in geo["components"] if c.get("moves_with") == "nib" and c["id"] in sol] + ["head_shoe"]
    sliding = {"ball", "refill", "refill_holder", "head_shoe"}     # these also slide along the axis: the ball stays on the paper
    skip = {"wire_1", "wire_2", "wire_3", "wire_4", "front_balls", "rear_balls", "lateral_stop"}
    fixed = [k for k in sol if k not in moving and k not in skip]
    rows = []
    th = math.radians(TILT)
    for k in range(8):
        a = 2 * math.pi * k / 8
        dx, dy = stop * math.cos(a), stop * math.sin(a)
        dz = -math.cos(th) * dx / math.sin(th)
        mv = {m: _shape(sol[m]).translate((dx, dy, dz if m in sliding else 0.0)) for m in moving}
        for m, f in itertools.product(moving, fixed):
            if frozenset((m, f)) in INTENDED:
                continue
            sm, sf = mv[m], _shape(sol[f])
            if not _bbox_overlap(sm, sf):
                continue
            try:
                v = sm.intersect(sf).Volume()
            except Exception:
                continue
            if v > 1e-3:
                rows.append({"direction_deg": 45 * k, "moving": m, "fixed": f, "volume_mm3": v})
    return rows


def build_assembly(sol: dict, geo: dict, comps: list, name: str):
    import cadquery as cq
    asm = cq.Assembly(name=name)
    for c in comps:
        if c["id"] in sol:
            asm.add(sol[c["id"]], name=c["id"], color=cq.Color(*COLORS.get(c["group"], (0.6, 0.6, 0.6))))
    return asm


# --------------------------------------------------------------------------------------------------- drawing
def _outline(c, dx=0.0):
    z0, z1 = c["z0"], c["z1"]
    ox = c.get("offset", [0.0, 0.0])[0] + dx
    if c["shape"] == "box":
        sx = c["size"][0]
        return [[(z0, ox - sx / 2), (z1, ox - sx / 2), (z1, ox + sx / 2), (z0, ox + sx / 2)]]
    r0, r1 = c.get("d0", 0.0) / 2, c.get("d1", c.get("d0", 0.0)) / 2
    if c["shape"] == "tube":
        ri = c.get("d_in", 0.0) / 2
        top = [(z0, ox + ri), (z1, ox + ri), (z1, ox + r1), (z0, ox + r0)]
        bot = [(z0, ox - r0), (z1, ox - r1), (z1, ox - ri), (z0, ox - ri)]
        return [bot] if c.get("open_deg") else [top, bot]
    return [[(z0, ox - r0), (z1, ox - r1), (z1, ox + r1), (z0, ox + r0)]]


def drawing(geo: dict, comps: list, path_png: str, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Annulus, Circle, Polygon, Rectangle
    fig = plt.figure(figsize=(18, 9.5))
    ax = fig.add_axes([0.04, 0.42, 0.93, 0.52])
    stop = geo["stop_mm"]
    for c in comps:
        col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
        if c["id"] == "head_face":
            P = np.array(c["plate_corners_50deg"])
            ax.add_patch(Polygon([(p[2], p[0]) for p in P[[0, 4, 5, 1]]], closed=True, facecolor=col, edgecolor="k", lw=0.5))
            continue
        ls = "--" if c.get("optional") else "-"
        for poly in _outline(c):
            ax.add_patch(Polygon(poly, closed=True, facecolor=col if not c.get("optional") else "none",
                                 edgecolor="k" if not c.get("optional") else col, lw=0.4, ls=ls, alpha=0.85))
        if c.get("moves_with") == "nib" and c["id"] not in ("ball", "refill"):
            for d in (-stop, stop):
                for poly in _outline(c, d):
                    ax.add_patch(Polygon(poly, closed=True, fill=False, edgecolor=col, lw=0.5, ls=":"))
    R = geo["skid_contact_radius"]
    zr = geo["ball_protrusion_mm"]
    for tdeg, lsty in ((35.0, ":"), (50.0, "-"), (75.0, "--")):
        th = math.radians(tdeg)
        zz = np.array([-8.0, 150.0])
        ax.plot(zz, [-R - (z - zr) * math.tan(th) for z in zz], color="0.35", lw=0.8, ls=lsty)
        ax.text(-7.5, -R - (-7.5 - zr) * math.tan(th) + 0.5, f"paper {tdeg:.0f}°", fontsize=7, color="0.3")
    D = geo["handle_od"]
    for zf in geo["hand"]["finger_pads_z"]:
        ax.add_patch(Rectangle((zf - 2.5, D / 2 + 1.5), 5, 2.0, color=(0.9, 0.7, 0.6), alpha=0.9))
    ax.add_patch(Rectangle((geo["hand"]["web_z"] - 6, D / 2 + 1.5), 12, 2.0, color=(0.85, 0.6, 0.5), alpha=0.9))
    ax.set_xlim(-10, geo["length"] + 3)
    ax.set_ylim(-17, 17)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("z from the ball tip at 50° (mm)")
    ax.set_ylabel("x (mm)")
    cuts = [("coils", 27.5), ("flange", 32.0), ("board", 45.0), ("head", 70.0), ("head motors", 88.0), ("cell", 115.0)]
    for i, (nm, zc) in enumerate(cuts):
        axc = fig.add_axes([0.04 + i * 0.16, 0.03, 0.14, 0.33])
        for c in comps:
            if not (c["z0"] <= zc <= c["z1"]) or c["id"] == "head_face":
                continue
            col = COLORS.get(c["group"], (0.6, 0.6, 0.6))
            ox, oy = c.get("offset", [0.0, 0.0])
            if c["shape"] == "box":
                sx, sy = c["size"][0], c["size"][1]
                axc.add_patch(Rectangle((oy - sy / 2, ox - sx / 2), sy, sx, color=col, alpha=0.8,
                                        fill=not c.get("optional"), ls="--" if c.get("optional") else "-"))
            else:
                t = (zc - c["z0"]) / max(c["z1"] - c["z0"], 1e-6)
                r = 0.5 * (c["d0"] + t * (c.get("d1", c["d0"]) - c["d0"]))
                if c["shape"] == "tube" and c.get("d_in"):
                    axc.add_patch(Annulus((oy, ox), r, max(r - c["d_in"] / 2, 0.05), color=col, alpha=0.8))
                else:
                    axc.add_patch(Circle((oy, ox), r, color=col, alpha=0.85, fill=not c.get("optional")))
        axc.set_xlim(-13, 13)
        axc.set_ylim(-13, 13)
        axc.set_aspect("equal")
        axc.set_title(f"{nm}, z {zc:g}", fontsize=8)
        axc.tick_params(labelsize=6)
    fig.text(0.01, 0.005, "PROPOSED DESIGN (dimensioned concept; dimensions CALC or ASSUMPTION). Dotted: moving nib at its ±stop "
                          "in x. Dashed: heel-module variant. Sections look from the back (horizontal y, vertical x; x < 0 is "
                          "the paper side). The face is drawn at 50°.", fontsize=7.5)
    fig.savefig(path_png, dpi=120, facecolor="white")
    plt.close(fig)


def component_csv(comps: list, path: str):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "group", "shape", "z0_mm", "z1_mm", "d0_mm", "d1_mm", "d_in_mm", "size_mm", "offset_mm",
                    "moves_with", "optional", "mass_g", "part", "ledger"])
        for c in comps:
            w.writerow([c["id"], c["label"], c["group"], c["shape"], round(c["z0"], 3), round(c["z1"], 3), c.get("d0", ""),
                        c.get("d1", ""), c.get("d_in", ""), c.get("size", ""), c.get("offset", ""), c["moves_with"],
                        c.get("optional", False), c.get("mass_g", ""), c.get("part", ""), c.get("ledger", "")])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--heel", action="store_true", help="also build the heel-module variant")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--layout", default=os.path.join(OUT, "layout.json"))
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    t0 = time.time()
    geo = load_layout(a.layout)
    base = list(geo["components"])
    heel = list(geo["heel_variant"]["components"])
    os.makedirs(a.out, exist_ok=True)
    sol, failed = solids(geo, base)
    hits = interferences(sol)
    stop_hits = at_stop_checks(geo, sol, geo["stop_mm"])
    res = {"base": {"n_solids": len(sol), "failed": failed, "interferences_at_rest": hits, "interferences_at_stop": stop_hits}}
    step = {}
    if not a.no_step:
        try:
            asm = build_assembly(sol, geo, base, "revK_pen")
            asm.save(os.path.join(a.out, "revK_pen_assembly.step"))
            step["base"] = True
        except Exception as e:
            step["base"] = f"failed: {e}"
    if a.heel:
        solh, failh = solids(geo, heel)
        allsol = dict(sol)
        allsol.update(solh)
        pairs = [(h, b) for h in solh for b in allsol if b != h and b not in solh] + list(itertools.combinations(solh, 2))
        res["heel"] = {"n_solids": len(solh), "failed": failh, "interferences_at_rest": interferences(allsol, pairs)}
        if not a.no_step:
            try:
                asm = build_assembly(allsol, geo, base + heel, "revK_pen_heel")
                asm.save(os.path.join(a.out, "revK_pen_assembly_heel.step"))
                step["heel"] = True
            except Exception as e:
                step["heel"] = f"failed: {e}"
    png = os.path.join(a.out, "drawing_revK_pen.png")
    drawing(geo, base + heel, png, f"Rev K pen (PROPOSED DESIGN): B1 translation nib, ball thrust guide, counter-face head, "
                                   f"no heel (dashed: heel-module variant); Ø{geo['handle_od']:.0f} × {geo['length']:.1f} mm")
    component_csv(base + heel, png.replace(".png", ".csv"))
    from revk import write_json
    summ = {"variant": "base pen" + (" + heel-module variant" if a.heel else ""), "step": step, "solid_checks": res,
            "geometry": {k: v for k, v in geo.items() if k not in ("components", "meta", "stabpen.provenance", "heel_variant",
                                                                  "fit_checks", "tables")},
            "layout_fit_summary": geo.get("fit_summary"), "n_components": len(base), "n_heel_components": len(heel),
            "intended_contacts": sorted(sorted(p) for p in INTENDED), "runtime_s": time.time() - t0,
            "note": "solid checks: boolean intersections > 0.001 mm3 between parts that should not touch, at rest and with the "
                    "moving nib translated to its stop in eight directions (the wires bend and the balls roll: skipped)"}
    write_json(os.path.join(a.out, "revK_cad_summary.json"), summ,
               "PROPOSED DESIGN (dimensioned concept); CALC (solid checks); nothing built or measured",
               extra={"script": "mechanics/cad/revK_pen.py", "command": "python3 mechanics/cad/revK_pen.py" +
                      (" --heel" if a.heel else "")})
    print("step:", step, "| at rest:", len(hits), "| at stop:", len(stop_hits), "| failed:", failed,
          f"| {time.time() - t0:.1f} s")
    for h in hits:
        print("  rest", h)
    for h in stop_hits[:40]:
        print("  stop", h)
    return summ


if __name__ == "__main__":
    main()
