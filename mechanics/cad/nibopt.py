"""Parametric CAD of study N's recommended balanced nib (CadQuery), after mechanics/cad/improved_nib.py.

Run after `python3 -m nibopt.run` (it reads results/nibopt/candidates.json):

    python3 mechanics/cad/nibopt.py [--candidate balanced|reach_first|slim|k_envelope|all] [--out results/nibopt]

Writes results/nibopt/nibopt_<candidate>.step (the nib sub-assembly, PROPOSED DESIGN), drawing_nibopt_<candidate>.png
(a side section and a front view with the coils at rest and at the stop) and nibopt_cad_summary_<candidate>.json
(partial solid masses and a boolean interference check at rest and with the moving parts at the stop in eight
directions; the fixed set includes a 0.2 mm keep-out ring inside the bore, so a clean check also shows >= 0.2 mm of
nominal coil clearance at the stop).  Solid: back plate, poles, winding packs (every sublayer), keeper, races, balls,
flange, carrier tube, wires, the floating anchor coupon and the refill envelope; the counter-face head is a swept
keep-out only.  Not a manufacturing drawing: joints, solder pads, the flex lead, the Hall sensor and the head's
mechanism are unresolved.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DENS = {"iron": 7.87, "hiperco": 8.12, "ndfeb": 7.5, "copper_pack": 8.89 * 0.55 + 1.3 * 0.45, "ti": 4.43, "al": 2.81,
        "cfrp": 1.55, "si3n4": 3.2, "440c": 7.8, "becu": 8.25, "steel301": 8.0}


def ring(ro, ri, z, h):
    return cq.Workplane("XY").circle(ro).circle(ri).extrude(h).translate((0, 0, z))


def build(c: dict):
    """The assembly from one candidate record of results/nibopt/candidates.json (lengths in mm)."""
    dsg = c["design"]
    mg, co, gd, wr = dsg["magnets_mm"], dsg["coil_mm"], dsg["guide"], dsg["wires"]
    stop, bore = dsg["stop_mm"], dsg["bore_mm"]
    t_p = dsg["plate_t_mm"]
    z0 = 21.43
    e, w, t_m = mg["e"], mg["w"], mg["t_m"]
    cc = w / 2 + e
    r_hole = 1.6 + stop + 0.3
    r_plate = bore - 0.3
    solids, fixed, moving, masses = {}, [], [], []
    assy = cq.Assembly(name=f"nibopt_{c['name']}")

    def add(obj, name, color, dens=None, group=None):
        assy.add(obj, name=name, color=cq.Color(*color))
        solids[name] = obj
        if group == "fixed":
            fixed.append(name)
        elif group == "moving":
            moving.append(name)
        if dens:
            masses.append({"part": name, "solid_mass_g": obj.val().Volume() * dens * 1e-3})
    iron = "hiperco" if dsg["iron"] == "Hiperco50A" else "iron"
    add(ring(r_plate, r_hole, z0, t_p), "back_plate", (.30, .34, .38), DENS[iron], "fixed")
    zm = z0 + t_p
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
        obj = cq.Workplane("XY").box(w, w, t_m, centered=(True, True, False)).translate((sx * cc, sy * cc, zm))
        add(obj, f"pole_{i + 1}", (.70, .25, .25) if sx * sy > 0 else (.20, .35, .70), DENS["ndfeb"], "fixed")
    zc = zm + t_m + mg["c0"]
    order = co["order"]
    n = len(order)
    act = (mg["t_cu"] - (n - 1) * 0.05) / n
    for li, ax in enumerate(order):
        z = zc + li * (act + 0.05)
        for sgn in (-1, 1):
            xi, yi, b, yc = co["x_in"], co["y_in"], co["b"], co["yc"]
            obj = (cq.Workplane("XY").rect(2 * (xi + b), 2 * (yi + b)).rect(2 * xi, 2 * yi).extrude(act)
                   .translate((0, sgn * yc, z)))
            if ax == "y":
                obj = obj.rotate((0, 0, 0), (0, 0, 1), 90)
            add(obj, f"winding_{li}_{ax}_{'p' if sgn > 0 else 'n'}", (.83, .49, .16), DENS["copper_pack"], "moving")
    zk = zc + mg["t_cu"] + mg["c1"]
    if mg.get("double"):
        for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
            obj = cq.Workplane("XY").box(w, w, mg["t_m2"], centered=(True, True, False)).translate((sx * cc, sy * cc, zk))
            add(obj, f"pole2_{i + 1}", (.70, .25, .25) if sx * sy > 0 else (.20, .35, .70), DENS["ndfeb"], "fixed")
        zk += mg["t_m2"]
    add(ring(r_plate, r_hole, zk, t_p), "keeper", (.30, .34, .38), DENS[iron], "fixed")
    bc, bd, nb = gd["circle_r_mm"], gd["ball_d_mm"], gd["n_balls"]
    race_w = stop + bd + 0.4
    zr = zk + t_p
    add(ring(bc + race_w / 2, bc - race_w / 2, zr, 0.3), "front_race", (.48, .50, .54), DENS["440c"], "fixed")
    zf = zr + 0.3 + bd
    ft = c["design"].get("flange_t_mm", 1.5)
    fr = gd["flange_r_mm"]
    for i in range(nb):
        a = 2 * math.pi * i / nb
        add(cq.Workplane("XY").sphere(bd / 2).translate((bc * math.cos(a), bc * math.sin(a), zr + 0.3 + bd / 2)),
            f"front_ball_{i + 1}", (.12, .14, .16), DENS["si3n4"])
        add(cq.Workplane("XY").sphere(bd / 2).translate((bc * math.cos(a), bc * math.sin(a), zf + ft + bd / 2)),
            f"rear_ball_{i + 1}", (.12, .14, .16), DENS["si3n4"])
    fmat = DENS["al"] if c["design"].get("flange_mat", "Ti") == "Al" else DENS["ti"]
    add(ring(fr, 1.3, zf, ft), "carrier_flange", (.58, .62, .68), fmat, "moving")
    add(ring(bc + race_w / 2, bc - race_w / 2, zf + ft + bd, 0.3), "rear_race", (.48, .50, .54), DENS["440c"], "fixed")
    tmat = DENS["cfrp"] if c["design"].get("carrier_mat", "Ti") == "CFRP" else DENS["ti"]
    add(ring(1.6, 1.25, 9.0, zf + ft + 0.5 - 9.0), "carrier_tube", (.60, .62, .66), tmat, "moving")
    zw = zf + ft
    L = wr["L_mm"]
    for i in range(wr["n"]):
        a = 2 * math.pi * (i + 0.5) / wr["n"]
        add(cq.Workplane("XY").circle(wr["d_mm"] / 2).extrude(L).translate((wr["circle_mm"] * math.cos(a),
                                                                              wr["circle_mm"] * math.sin(a), zw)),
            f"C17200_lead_{i + 1}", (.75, .53, .25), DENS["becu"])
    # floating anchor coupon: four radial fixed-guided leaves carrying the anchor stiffness less the flex lead's
    # allowance (the pass's 23.4 N/m, results/improvement/mechanics/cad_summary.json)
    k_flex = 23.4
    k_beam = max(wr["anchor_N_m"] - k_flex, 0.25 * wr["anchor_N_m"])
    ri = 1.175 + stop + 0.3
    hub = max(wr["circle_mm"] + 0.35, ri + 0.5)
    Lb = max(2.0, min(6.0, r_plate - 0.3 - hub - 0.3))
    wb = 0.5
    tb = (k_beam * (Lb * 1e-3) ** 3 / (4 * 193e9 * wb * 1e-3)) ** (1 / 3) * 1e3
    dia = ring(hub, ri, 0, tb).union(ring(hub + Lb + 0.3, hub + Lb, 0, tb))
    for a in (0, 90, 180, 270):
        dia = dia.union(cq.Workplane("XY").box(Lb + 0.04, wb, tb, centered=(True, True, False))
                        .translate((hub + Lb / 2, 0, 0)).rotate((0, 0, 0), (0, 0, 1), a))
    add(dia.translate((0, 0, zw + L)), "floating_anchor_301", (.60, .67, .72), DENS["steel301"])
    ext = max(0.0, L - 26.8)
    add(cq.Workplane("XY").circle(1.175).extrude(64 + ext).translate((0, 0, 3)), "refill_envelope", (.16, .19, .24))
    head = c.get("head_fit") or {}
    shift = (dsg["stack_mm"] - 8.48) + (0.3 + bd + ft + bd + 0.3 - 3.7) + ext
    hr = head.get("od_min_head_mm", 18.0) / 2 - 1.3
    add(cq.Workplane("XY").circle(hr).extrude(85.03 - 60.67).translate((0, 0, 60.67 + shift)),
        "counterface_head_keepout_UNRESOLVED", (.12, .68, .68, .15))
    add(ring(bore, bore - 0.2, 18.0, zw + L + 3 - 18.0), "bore_keepout_0.2mm", (.65, .70, .75, .10), group="fixed")
    return assy, solids, fixed, moving, masses, {"z_actuator": (z0, zk + t_p), "z_flange": (zf, zf + ft),
                                                 "z_wires": (zw, zw + L), "anchor_leaf_t_mm": tb, "anchor_leaf_L_mm": Lb,
                                                 "anchor_leaf_w_mm": wb, "anchor_beams_N_m": k_beam,
                                                 "anchor_flex_allowance_N_m": k_flex,
                                                 "head_shift_mm": shift}


def interference(solids, fixed, moving, stop):
    """Boolean intersections > 0.001 mm^3 between moving and fixed solids at rest and at the stop (8 directions)."""
    rows = []
    for k in range(9):
        if k == 0:
            dx = dy = 0.0
            tag = "rest"
        else:
            a = (k - 1) * math.pi / 4
            dx, dy = stop * math.cos(a), stop * math.sin(a)
            tag = f"stop_{(k - 1) * 45}deg"
        for mname in moving:
            m = solids[mname].translate((dx, dy, 0))
            for fname in fixed:
                try:
                    v = m.intersect(solids[fname]).val().Volume()
                except Exception:
                    v = 0.0
                if v > 1e-3:
                    rows.append({"case": tag, "moving": mname, "fixed": fname, "volume_mm3": v})
    return rows


def drawing(c: dict, geo: dict, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    dsg = c["design"]
    mg, co, gd = dsg["magnets_mm"], dsg["coil_mm"], dsg["guide"]
    stop, bore = dsg["stop_mm"], dsg["bore_mm"]
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axs[0]
    z0, z1 = geo["z_actuator"]
    t_p = dsg["plate_t_mm"]
    r_hole = 1.6 + stop + 0.3
    for zz in (z0, z1 - t_p):
        for s in (-1, 1):
            ax.add_patch(Rectangle((zz, s * r_hole if s > 0 else -(bore - 0.3)), t_p, bore - 0.3 - r_hole, color="#5a6068"))
    cc = mg["w"] / 2 + mg["e"]
    for s in (-1, 1):
        ax.add_patch(Rectangle((z0 + t_p, s * cc - mg["w"] / 2), mg["t_m"], mg["w"], color="#b44a4a" if s > 0 else "#3a5fa8"))
    zc = z0 + t_p + mg["t_m"] + mg["c0"]
    if mg.get("double"):
        zk2 = zc + mg["t_cu"] + mg["c1"]
        for s in (-1, 1):
            ax.add_patch(Rectangle((zk2, s * cc - mg["w"] / 2), mg["t_m2"], mg["w"], color="#b44a4a" if s > 0 else "#3a5fa8",
                                   alpha=0.75))
    for s in (-1, 1):
        ax.add_patch(Rectangle((zc, s * co["yc"] - (co["y_in"] + co["b"])), mg["t_cu"], 2 * (co["y_in"] + co["b"]),
                               fill=False, ec="#d07a28", lw=1.2))
        ax.add_patch(Rectangle((zc, s * co["yc"] - (co["y_in"] + co["b"]) + stop), mg["t_cu"], 2 * (co["y_in"] + co["b"]),
                               fill=False, ec="#d07a28", lw=0.8, ls="--"))
    zf0, zf1 = geo["z_flange"]
    for s in (-1, 1):
        ax.add_patch(Rectangle((zf0, 1.3 if s > 0 else -gd["flange_r_mm"]), zf1 - zf0, gd["flange_r_mm"] - 1.3, color="#94a0ad"))
    zw0, zw1 = geo["z_wires"]
    for s in (-1, 1):
        ax.plot([zw0, zw1], [s * dsg["wires"]["circle_mm"]] * 2, color="#bf8740", lw=0.8)
    ax.add_patch(Rectangle((9.0, -1.6), zf1 + 0.5 - 9.0, 3.2, fill=False, ec="#777", lw=0.8))
    ax.add_patch(Rectangle((3.0, -1.175), 64.0, 2.35, color="#28303c", alpha=0.25))
    ax.axhline(bore, color="#999", lw=0.8, ls=":")
    ax.axhline(-bore, color="#999", lw=0.8, ls=":")
    ax.set_xlim(0, zw1 + 6)
    ax.set_ylim(-bore - 1.5, bore + 1.5)
    ax.set_aspect("equal")
    ax.set_xlabel("z from the ball tip (mm)")
    ax.set_ylabel("x (mm)")
    ax.set_title(f"side section: actuator {z1 - z0:.2f} mm ({'two arrays' if mg.get('double') else 'one array + keeper'}), "
                 f"wires {dsg['wires']['L_mm']:.1f} mm; coil at the stop dashed", fontsize=10)
    ax = axs[1]
    ax.add_patch(Circle((0, 0), bore, fill=False, ec="#999", ls=":"))
    for sx, sy in [(1, 1), (-1, 1), (-1, -1), (1, -1)]:
        ax.add_patch(Rectangle((sx * cc - mg["w"] / 2, sy * cc - mg["w"] / 2), mg["w"], mg["w"],
                               color="#b44a4a" if sx * sy > 0 else "#3a5fa8", alpha=0.6))
    xi, yi, b, yc = co["x_in"], co["y_in"], co["b"], co["yc"]
    for dx, dy, ls in ((0, 0, "-"), (stop / math.sqrt(2), stop / math.sqrt(2), "--")):
        for s in (-1, 1):
            ax.add_patch(Rectangle((dx - xi - b, dy + s * yc - yi - b), 2 * (xi + b), 2 * (yi + b), fill=False, ec="#d07a28", ls=ls))
            ax.add_patch(Rectangle((dx + s * yc - yi - b, dy - xi - b), 2 * (yi + b), 2 * (xi + b), fill=False, ec="#a35d1b", ls=ls))
    ax.add_patch(Circle((0, 0), 1.6, fill=False, ec="#777"))
    ax.add_patch(Circle((0, 0), gd["circle_r_mm"], fill=False, ec="#222", lw=0.6, ls="-."))
    ax.set_xlim(-bore - 1, bore + 1)
    ax.set_ylim(-bore - 1, bore + 1)
    ax.set_aspect("equal")
    ax.set_title(f"front view: body {dsg['od_mm']:.1f} mm, reach +-{dsg['reach_mm']:.2f} mm")
    fig.suptitle(f"nibopt '{c['name']}' (PROPOSED DESIGN; CALCULATION of fits; not a manufacturing drawing)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="balanced")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "nibopt")
    ap.add_argument("--no-interference", action="store_true")
    args = ap.parse_args(argv)
    cands = json.loads((args.out / "candidates.json").read_text())
    names = list(cands["candidates"]) if args.candidate == "all" else [args.candidate]
    for name in names:
        one(cands["candidates"][name], name, args)


def one(c: dict, name: str, args):
    import time
    t0 = time.time()
    assy, solids, fixed, moving, masses, geo = build(c)
    step = args.out / f"nibopt_{name}.step"
    assy.export(str(step))
    png = args.out / f"drawing_nibopt_{name}.png"
    drawing(c, geo, png)
    inter = [] if args.no_interference else interference(solids, fixed, moving, c["design"]["stop_mm"])
    from stabpen import provenance as PV
    import nibopt
    summ = {"stabpen.provenance": PV.metadata("PROPOSED DESIGN (CAD) with CALCULATION of fits; nothing built or measured",
                                              extra={"script": "mechanics/cad/nibopt.py", "candidate": name,
                                                     "own_sources_sha256_16": nibopt.own_digests(),
                                                     "seconds": None}),
            "candidate": name, "step": str(step.relative_to(ROOT)), "drawing": str(png.relative_to(ROOT)),
            "components": len(assy.children), "partial_solid_mass_g": sum(m["solid_mass_g"] for m in masses),
            "partial_mass_breakdown": masses, "geometry_mm": geo,
            "interference_rest_and_stop_8_directions": inter, "interference_free": len(inter) == 0,
            "not_modelled": ["wires bend and balls roll: left out of the interference check",
                             "counter-face head mechanism (a keep-out only)", "flex lead, solder pads and Hall sensor",
                             "coil former, turns and insulation build", "drop stops and dust protection"],
            "label": "PROPOSED DESIGN; interference by CadQuery boolean intersection (CALCULATION)"}
    summ["stabpen.provenance"]["seconds"] = time.time() - t0
    (args.out / f"nibopt_cad_summary_{name}.json").write_text(json.dumps(summ, indent=2, default=float) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k not in ("partial_mass_breakdown", "stabpen.provenance")},
                     indent=1, default=float))


if __name__ == "__main__":
    main()
