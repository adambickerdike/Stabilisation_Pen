#!/usr/bin/env python3
"""R11 recording pen for EXP-H01: a passive, instrumented pen in two grip classes (CadQuery).

Evidence status: PROPOSED DESIGN (concept geometry).  LSB200 19.05 x 16.5 x 6.7 mm, 19.3 g (MFR AMF-225; load axis
along the 19.05 mm side is an ASSUMPTION to check on drawing FI1455); LLB130 9.5 x 3.3 mm, 8.5 g (MFR AMF-226);
IMU breakout envelope, bushes, slugs and densities are ASSUMPTIONS.

What it does: the refill slides in two PTFE bushes and bears through a pin on an axial load cell, so the pen
measures the axial ink force F_c while the paper lies on R9's force plate (the paper-normal force measured apart,
Schomaker and Plamondon's two-transducer method, LIT CON-101); an LSM6DSV16X in the tail records pen motion at
1.92 kHz; a 1.5 m, 12-core cable runs to DAQ-1.  Tungsten slugs in the front and tail match the candidate's mass
and centre of mass (Rev J.1's base pen: 84.3 g, centre of mass 86.0 mm from the tip, CALC in docs/revJ1_design.md).

Outputs (results/rig/cad/): rig_recpen_assembly.step, drawing_rig_recpen.png, rig_recpen_summary.json.
Run: python3 mechanics/cad/rig_recpen.py
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.dont_write_bytecode = True          # no bytecode caches from this study's helpers in mechanics/cad/__pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_common as C  # noqa: E402

NAME = "rig_recpen"
R = dict(
    ball_d=0.7, refill_d=2.35, refill_L=67.0, tip=(0.30, 0.25, 4.5),
    pens={
        "pen24": dict(od=24.0, wall=1.0, L=144.0, nose=(3.0, 4.0, 12.0, 32.0), cell="LSB200", cell_mass_g=19.3,
                      cell_dims=(16.5, 6.7, 19.05), target=(84.3, 86.0), target_src="Rev J.1 base pen, CALC (docs/revJ1_design.md)"),
        "slim14": dict(od=14.0, wall=0.8, L=140.0, nose=(2.5, 4.0, 7.0, 22.0), cell="LLB130", cell_mass_g=8.5,
                       cell_dims=(9.5, 3.3), target=(35.0, 70.0), target_src="ASSUMPTION inside the review's 25-40 g slim class"),
    },
    bush=(6.0, 2.45, 8.0), bush_s=(10.0, 52.0), pin=(2.0, 3.0), bulkhead_t=3.0,
    imu=(12.0, 10.0, 1.6), imu_s=118.0, cable_d=4.0,
    slug_front=(12.0, 36.0, 46.0), slug_rear_L=12.0,
)


def pen_parts(pen: str):
    p = R["pens"][pen]
    r0, s0, r1, s1 = p["nose"]
    w = p["wall"]
    parts = {}
    parts["ball"] = C.cq.Workplane("XY").sphere(R["ball_d"] / 2)
    t0, tz0, tz1 = R["tip"]
    parts["refill"] = C.cone(t0, R["refill_d"] / 2, tz0, tz1).union(C.cyl(R["refill_d"], tz1, R["refill_L"]))
    nose_o = C.cone(r0, r1, s0 + 1.5, s1)
    nose_i = C.cone(max(r0 - w, R["refill_d"] / 2 + 0.2), r1 - w, s0 + 1.49, s1 + 0.01)
    parts["nose"] = nose_o.cut(nose_i)
    parts["body"] = C.tube(p["od"], p["od"] - 2 * w, s1, p["L"])
    bore = p["od"] - 2 * w
    bd, bid, bl = R["bush"]
    bushes = None
    ri0, ri1, zi0, zi1 = max(r0 - w, R["refill_d"] / 2 + 0.2), r1 - w, s0 + 1.49, s1 + 0.01

    def r_inner(z):
        return ri0 + (z - zi0) * (ri1 - ri0) / (zi1 - zi0) if z < s1 else bore / 2

    for s in R["bush_s"]:
        od = min(bd if s < s1 else bore - 0.2, 2 * r_inner(s) - 0.2)      # the bush's front end is the narrowest point
        b = C.tube(od, bid, s, s + bl)
        bushes = b if bushes is None else bushes.union(b)
    parts["ptfe_bushes"] = bushes
    pd, pl = R["pin"]
    parts["force_pin"] = C.cyl(pd, R["refill_L"] + 0.1, R["refill_L"] + 0.1 + pl)
    zc = R["refill_L"] + 0.1 + pl
    if p["cell"] == "LSB200":
        cx, cy, cz = p["cell_dims"]
        parts["axial_cell"] = C.box(cx, cy, cz, (0, 0, zc + cz / 2))
        zb = zc + cz
    else:
        d, h = p["cell_dims"]
        parts["axial_cell"] = C.cyl(d, zc, zc + h)
        zb = zc + h
    parts["bulkhead"] = C.cyl(bore - 0.1, zb, zb + R["bulkhead_t"])
    ix, iy, iz = R["imu"]
    parts["imu_board"] = C.box(ix, iy, iz, (0, 0, R["imu_s"])).rotate((0, 0, R["imu_s"]), (0, 1, R["imu_s"]), 90)
    parts["cap"] = C.cyl(bore - 0.1, p["L"] - 3.0, p["L"]).cut(C.cyl(R["cable_d"] + 0.4, p["L"] - 4.0, p["L"] + 1.0))
    parts["cable"] = C.cyl(R["cable_d"], p["L"] - 10.0, p["L"] + 25.0)
    sd, sa, sb = R["slug_front"]
    sd = min(sd, 2 * (r0 + (sa - s0) * (r1 - r0) / (s1 - s0) - w) - 0.4) if sa < s1 else min(sd, bore - 0.4)
    parts["slug_front"] = C.tube(sd, R["refill_d"] + 0.6, sa, sb)
    parts["slug_rear"] = C.cyl(bore - 0.4, p["L"] - 3.0 - R["slug_rear_L"], p["L"] - 3.0).cut(
        C.cyl(R["cable_d"] + 0.6, p["L"] - 20.0, p["L"] + 1.0))
    return parts, zb


MAT = {"refill": ("steel", 0.35), "nose": ("print", 1.0), "body": ("al", 1.0), "ptfe_bushes": ("print", 1.7),
       "force_pin": ("steel", 1.0), "bulkhead": ("al", 1.0), "imu_board": ("pcb", 1.0), "cap": ("print", 1.0),
       "slug_front": ("tungsten", 1.0), "slug_rear": ("tungsten", 1.0)}


def mass_properties(pen: str):
    """Mass and centre of mass (CALC; densities ASSUMPTION; PTFE as 1.7 x printed polymer = 2.1 g/cm^3)."""
    parts, _ = pen_parts(pen)
    p = R["pens"][pen]
    rows = {}
    for k, v in parts.items():
        if k in ("ball", "cable"):
            continue
        if k == "axial_cell":
            m = p["cell_mass_g"]
        else:
            mat, f = MAT[k]
            m = C.mass_g(v, mat) * f
        bb = C.bbox(v)
        rows[k] = (m, 0.5 * (bb.zmin + bb.zmax))
    rows["cable_strain_relief_and_wires"] = (3.0, p["L"] - 5.0)       # ASSUMPTION (the hanging cable is not counted)
    base = {k: v for k, v in rows.items() if not k.startswith("slug")}
    M0 = sum(m for m, _ in base.values())
    S0 = sum(m * s for m, s in base.values()) / M0
    mf, sf = rows["slug_front"]
    mr, sr = rows["slug_rear"]
    tgt_m, tgt_s = p["target"]
    # solve for the fractions a (front) and b (rear) of the full slugs: M0 + a mf + b mr = M, S0 M0 + a mf sf + b mr sr = S M
    import numpy as np
    A = np.array([[mf, mr], [mf * sf, mr * sr]])
    rhs = np.array([tgt_m - M0, tgt_s * tgt_m - S0 * M0])
    try:
        a, b = np.linalg.solve(A, rhs)
    except np.linalg.LinAlgError:
        a, b = float("nan"), float("nan")
    feasible = bool(-0.05 <= a <= 1.05 and -0.05 <= b <= 1.05)      # +-5 % of a slug: trimmed at assembly
    at_limit = feasible and not (0 <= a <= 1 and 0 <= b <= 1)
    return {"target_at_limit": at_limit, "parts_g_and_centre_mm": {k: [round(m, 2), round(s, 1)] for k, (m, s) in rows.items()},
            "without_slugs": {"mass_g": round(M0, 1), "com_mm": round(S0, 1)},
            "full_slugs_g": {"front": round(mf, 1), "rear": round(mr, 1)},
            "target": {"mass_g": tgt_m, "com_mm": tgt_s, "source": p["target_src"]},
            "slug_fill_fraction": {"front": round(float(a), 3), "rear": round(float(b), 3)}, "target_reachable": feasible}


def checks(pen: str):
    parts, zb = pen_parts(pen)
    p = R["pens"][pen]
    bore = p["od"] - 2 * p["wall"]
    out = {"bore_mm": bore}
    if p["cell"] == "LSB200":
        cx, cy, cz = p["cell_dims"]
        out["cell_section_diagonal_mm"] = round(math.hypot(cx, cy), 2)
        out["cell_section_diagonal_if_rotated_mm"] = round(math.hypot(cz, cy), 2)
    else:
        out["cell_diameter_mm"] = p["cell_dims"][0]
    out["cell_fits"] = all(v < bore for k, v in out.items() if k.startswith("cell_") and isinstance(v, float))
    # nothing may reach outside the shell (nose + body) except the refill tip, ball and cable
    shell = parts["nose"].union(parts["body"])
    env = C.cone(p["nose"][0], p["nose"][2], p["nose"][1] + 1.5, p["nose"][3]).union(C.cyl(p["od"], p["nose"][3], p["L"]))
    outside = []
    for k, v in parts.items():
        if k in ("ball", "refill", "cable", "nose", "body"):
            continue
        vol = C.volume_mm3(v)
        inside = C.volume_mm3(v.intersect(env)) if vol > 0 else 0.0
        if vol - inside > 1e-3:
            outside.append({"part": k, "outside_mm3": round(vol - inside, 3)})
    out["parts_outside_shell"] = outside
    # the refill must be free to move 0.3 mm axially (cell deflection 0.2 mm at full scale for LSB200 100/250 g)
    ref = parts["refill"].translate((0, 0, 0.3))
    hits = [k for k in ("nose", "ptfe_bushes", "slug_front", "bulkhead") if C.overlap_mm3(ref, parts[k]) > 1e-6]
    out["refill_free_0p3mm"] = not hits
    out["refill_hits"] = hits
    del shell
    return out


def drawing(path):
    from stabpen import plotstyle as ps
    fig, axs = C.new_figure(2, size=(13.0, 6.0))
    for ax, pen in zip(axs, sorted(R["pens"])):
        parts, zb = pen_parts(pen)
        col = {"refill": ps.SERIES[0], "ball": ps.SERIES[0], "axial_cell": ps.SERIES[2], "imu_board": ps.SERIES[4],
               "slug_front": ps.SERIES[3], "slug_rear": ps.SERIES[3], "ptfe_bushes": ps.SERIES[1]}
        for k, v in parts.items():
            C.project(ax, v.rotate((0, 0, 0), (0, 1, 0), 90), "xz", color=col.get(k, ps.INK2), lw=0.7)
        p = R["pens"][pen]
        mp = mass_properties(pen)
        r = p["od"] / 2
        C.dim(ax, (0, r + 6), (p["L"], r + 6), f"{p['L']:.0f}", off=0)
        C.dim(ax, (p["L"] + 8, -r), (p["L"] + 8, r), f"{p['od']:.0f}", off=0)
        cz = R["refill_L"] + 0.1 + R["pin"][1]
        C.label(ax, (cz + 4, -2), f"{p['cell']} axial cell", (70, -r - 14))
        C.label(ax, (R["imu_s"], 0), "LSM6DSV16X", (100, r + 14))
        C.label(ax, (41, 0), "tungsten slugs (front, tail)", (10, r + 16))
        C.label(ax, (14, 0), "PTFE bushes", (-8, -r - 14))
        wo = mp["without_slugs"]
        tg = mp["target"]
        fr = mp["slug_fill_fraction"]
        ax.text(0, -r - 30, f"without slugs {wo['mass_g']} g, CoM {wo['com_mm']} mm from the tip; target {tg['mass_g']} g at "
                            f"{tg['com_mm']} mm:\nslug fill front {fr['front']}, rear {fr['rear']} "
                            f"({('reachable, at the limit' if mp['target_at_limit'] else 'reachable') if mp['target_reachable'] else 'NOT reachable with these slugs'})",
                fontsize=7.5, color=ps.INK)
        ax.set_xlim(-8, p["L"] + 40)
        ax.set_ylim(-r - 36, r + 22)
        ax.set_xlabel("along the pen axis from the ball (mm)")
        ax.set_ylabel("mm")
        ax.set_title(f"Recording pen, {pen} ({p['cell']})", loc="left", fontsize=10)
    C.finish(fig, path, "concept geometry drawn from the CAD solids; densities and envelopes assumed; not built")


def main():
    os.makedirs(C.OUT, exist_ok=True)
    parts = {}
    for i, pen in enumerate(sorted(R["pens"])):
        pp, _ = pen_parts(pen)
        for k, v in pp.items():
            parts[f"{pen}_{k}"] = v.translate((0, 40.0 * i, 0))
    step = C.save_assembly(NAME, parts, {f"{p}_axial_cell": "green" for p in R["pens"]})
    res = {pen: {"checks": checks(pen), "mass": mass_properties(pen)} for pen in sorted(R["pens"])}
    summary = {"parameters_mm": R, "step": os.path.relpath(step, C.ROOT), "by_pen": res,
               "notes": ["a light preload spring (about 20 mN, ASSUMPTION) keeps the refill on the pin when the pen is lifted; "
                         "the cell reads it as an offset that is re-zeroed at every pen lift",
                         "PTFE bush friction adds to the cell reading during axial motion: EXP-T06 measures it on R9 "
                         "(recording pen on the plate, plate force vs cell force)",
                         "the IMU is the only electronics in the pen; the bridge and IMU lines run in the 12-core cable to DAQ-1"]}
    C.write_summary(NAME, "proposed design (R11 recording pen concept geometry)", summary)
    drawing(os.path.join(C.OUT, f"drawing_{NAME}.png"))
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    main()
