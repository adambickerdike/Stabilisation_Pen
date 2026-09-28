"""Hand-off of optimised designs to the rest of the project.

  * stage_spec()      -> a sim/pencil/design.register_stage() specification, so the pencil simulator P1 runs the
                         design with PencilConfig(stage_key=<key>) (the spec is written to
                         results/opt/stage_registry.json, which design.py reads);
  * cad_overlay()     -> primary CAD parameters (mm) for mechanics/cad/pencil_revP.py --overlay;
  * overlay_yaml()    -> results/opt/pencil_P0.2_proposed.yaml: the config/pencil.yaml parameters that change,
                         in the same leaf schema (value, unit, min, max, dist, status, source, note), plus the CAD
                         overlay under cad_parameters_mm.
Evidence status: PROPOSED DESIGN with CALCULATION / SIMULATION labels per value.
"""
from __future__ import annotations

import json
import math
import os

import torch

from . import OUT, ROOT
from . import catalogue as CAT
from . import model as MD
from sim.pencil import design as D  # noqa: E402
from stabpen import provenance  # noqa: E402

REGISTRY_FILE = D.STAGE_REGISTRY_FILE


def _f(v):
    return float(v[0]) if isinstance(v, torch.Tensor) and v.dim() else float(v)


def bender_numbers(x: dict, opts: MD.Options):
    """Per plate position (stacked plates summed), at the part's full rating V_full = 60 V, nominal tolerance.
    A stack is two plates clamped together with a spacer whose tips are not joined to each other: each drives the
    collar through its own half of a slit leaf, so the two bend in parallel (ASSUMPTION, EXP-Q04). A rigid joint
    between the tips would force about 9 um of relative axial slip at the stops (tip rotation x plate spacing) and
    make the pair act as a parallelogram; plates bonded along their length act as one plate of twice the thickness."""
    xb = MD.design_batch([dict(x, V=CAT.V_PART_MAX)])
    b = MD.bender(xb, opts)
    ns = float(opts.stack)
    t_eq = ns * x["t"]                       # mass-equivalent thickness of a stack (design.Bender uses rho w t L)
    num = dict(w=x["w"], t=t_eq, L_free=x["Lf"], L_total=x["Lf"] + x["Lc"], delta_f=_f(b["delta_f"]),
               F_b=_f(b["F_b"]), C_half=_f(b["C_half"]), V_full=CAT.V_PART_MAX)
    if opts.topology == "Q2L":               # fold the second-stage lever and its hinge into a collar-equivalent bender
        n2 = x["n2"]
        F_b = opts.lever_eff * num["F_b"] / n2
        k = (opts.lever_eff * num["F_b"] / num["delta_f"] + opts.hinge_frac * num["F_b"] / num["delta_f"]) / n2 ** 2
        num.update(F_b=F_b, delta_f=F_b / k, t=t_eq / n2 ** 2 * 1.0)
    mu = D.RHO_PZT * num["w"] * num["t"]
    EI = (num["F_b"] / num["delta_f"]) * num["L_free"] ** 3 / 3.0
    num["fr"] = 1.8751 ** 2 / (2 * math.pi) * math.sqrt(EI / (mu * num["L_free"] ** 4))
    return num


def cad_dict(x: dict, opts: MD.Options, mass_total_g: float, cad_summary: str | None = None):
    """Geometry for design.nib_assembly: from a rebuilt CAD summary if given, else from the model geometry."""
    if cad_summary and os.path.exists(cad_summary):
        d = json.load(open(cad_summary))
        s, P = d["summary"], d["summary"]["parameters_mm"]
        return {"z_gimbal": P["z_gimbal"], "collar_z0": P["collar_z0"], "collar_L": P["collar_L"],
                "z_plate_tip": P["z_plate_tip"], "nib_travel": P["nib_travel"], "refill_L": P["refill_L"],
                "ball_d": P["ball_d"], "plate_d": P["plate_d"],
                "parts": [[r["part"], r["group"], r["mass_g"], r["com_z_mm"]] for r in d["parts"]],
                "mass_total_g": s["mass_total_g"], "source": os.path.relpath(cad_summary, ROOT)}
    zcc = (x["zc0"] + MD.FIX["collar_L"] / 2) / MD.MM
    parts = []
    for name, (grp, mg, zc, _v) in (MD.CAD_PARTS or {}).items():
        if grp != "moving":
            continue
        z = zcc if name in MD.COLLAR_GROUP else (x["zg"] / MD.MM if name == "gimbal_hub" else zc)
        parts.append([name, grp, mg, round(z, 3)])
    return {"z_gimbal": x["zg"] / MD.MM, "collar_z0": x["zc0"] / MD.MM, "collar_L": MD.FIX["collar_L"] / MD.MM,
            "z_plate_tip": (x["zc0"] + MD.FIX["collar_L"] + x["leaf_L"]) / MD.MM, "nib_travel": x["q_stop"] / MD.MM,
            "refill_L": MD.FIX["refill_L"] / MD.MM, "ball_d": MD.FIX["ball_d"] / MD.MM, "plate_d": x["d"] / MD.MM,
            "parts": parts, "mass_total_g": mass_total_g, "source": "opt/hardware model geometry"}


def stage_spec(key: str, x: dict, opts: MD.Options, label: str, mass_total_g: float, cad_summary=None, fit_note=""):
    lm = CAT.LEAF_MATERIALS[opts.leaf_mat]
    return {"label": label, "fit": fit_note, "plates_per_axis": 2 if opts.topology in ("Q", "Q2L") else 1, "axes": 2,
            "bender": bender_numbers(x, opts),
            "leaf": {"t": x["leaf_t"], "w": x["leaf_w"], "L": x["leaf_L"], "E": lm["E"], "G": lm["G"], "Cb_over_K": 5.0},
            "k_gimbal_nib": opts.k_gimbal_nib, "cad": cad_dict(x, opts, mass_total_g, cad_summary),
            "options": {k: v for k, v in vars(opts).items() if k != "extra"}, "design_SI": dict(x),
            "status": "PROPOSED DESIGN (opt/hardware); plates scaled from AMF-11/AMF-53 (CALC, EXP-Q04 to confirm)"}


def write_registry(entries: dict, meta_extra=None):
    meta = provenance.metadata("proposed design (opt/hardware optimisation; CALCULATION)", p=D.Params().pencil,
                               extra=dict(meta_extra or {}, script="opt/hardware/run_study.py"))
    old = {}
    if os.path.exists(REGISTRY_FILE):
        try:
            old = json.load(open(REGISTRY_FILE)).get("stages", {})
        except (OSError, ValueError):
            old = {}
    old.update(entries)
    provenance.write_json(REGISTRY_FILE, {"meta": meta, "stages": old,
                                          "usage": "PencilConfig(stage_key=<key>, pen_mass=cad.mass_total_g*1.1e-3, "
                                                   "V_rail=options V); Controller(q_lim=nib_travel - 0.1 mm); "
                                                   "opt.hardware.p1_harness.pencil_config() fills pen_mass"})


def cad_overlay(x: dict, opts: MD.Options):
    """Primary CAD parameters (mm) for mechanics/cad/pencil_revP.py --overlay (variant Q or L)."""
    st = MD.stage(MD.design_batch([x]), opts)
    n = _f(st["n"])
    tr = float(opts.stack) * x["t"] + (float(opts.stack) - 1.0) * opts.k_bond_gap
    u_tip = x["q_stop"] / n / (x["n2"] if opts.topology == "Q2L" else 1.0)
    ov = {"plate_w": x["w"] / MD.MM, "plate_t": tr / MD.MM, "plate_free": x["Lf"] / MD.MM, "plate_clamp": x["Lc"] / MD.MM,
          "plate_d": x["d"] / MD.MM, "collar_z0": x["zc0"] / MD.MM,
          "z_plate_tip": (x["zc0"] + MD.FIX["collar_L"] + x["leaf_L"]) / MD.MM, "z_gimbal": x["zg"] / MD.MM,
          "leaf_t": x["leaf_t"] / MD.MM, "leaf_w": x["leaf_w"] / MD.MM,
          "tip_sweep": (u_tip + opts.sweep_margin) / MD.MM, "nib_travel": x["q_stop"] / MD.MM,
          "skid_r": x["r_ring"] / MD.MM, "batt_L": x["L_cell"] / MD.MM,
          "L_total": (MD.FIX["L_fixed_stack"] + max(x["L_cell"], 40e-3)) / MD.MM,
          "n_plates": 4 if opts.topology in ("Q", "Q2L") else 2, "hall_gap_extra": opts.hall_gap_extra / MD.MM}
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ov.items()}


def _leaf(value, unit, status, source, note="", lo=None, hi=None):
    d = {"value": value, "unit": unit}
    if lo is not None:
        d["min"], d["max"], d["dist"] = lo, hi, "fixed"
    d.update({"status": status, "source": source, "note": note})
    return d


def overlay_yaml(path, x, opts, ev, extra_notes=None, cad_ov=None, key="P02"):
    """Write the P0.2 overlay (only the parameters that change) in the config/pencil.yaml schema."""
    import yaml
    st, stw = ev["stage"], ev["stage_wc"]
    bn = bender_numbers(x, opts)
    F = lambda v: float(v[0]) if isinstance(v, torch.Tensor) else float(v)   # noqa: E731
    src = "opt/hardware (results/opt/hardware.json); plates scaled from AMF-11/AMF-53 PL128.10 (PIC252)" \
        if opts.ceramic == "PIC252" else "opt/hardware (results/opt/hardware.json); plates scaled from AMF-11/AMF-53 PL127.10 (PIC251)"
    drv = CAT.DRIVERS[opts.driver]
    hall = CAT.HALL[opts.hall]
    doc = {
        "meta": {"version": "P0.2-proposed", "base": "config/pencil.yaml P0.1.2",
                 "status": "PROPOSAL from opt/hardware; not adopted; nothing measured",
                 "stage_registry_key": key,
                 "notes": list(extra_notes or [])},
        "stage": {
            "type": _leaf(f"{(4 if opts.topology != 'L' else 2) * int(opts.stack)} custom PICMA-class multilayer benders "
                          f"{x['w'] * 1e3:.2f} x {(x['Lf'] + x['Lc']) * 1e3:.1f} x {x['t'] * 1e3:.2f} mm"
                          f"{' (%d per position, clamped together, one leaf half each)' % opts.stack if opts.stack > 1 else ''}"
                          f", ceramic {opts.ceramic}, {opts.topology} layout, {opts.leaf_mat} leaves", "-", "PROPOSED DESIGN", src),
            "bender_width": _leaf(round(x["w"], 6), "m", "PROPOSED DESIGN", src),
            "bender_thickness": _leaf(round(x["t"], 6), "m", "PROPOSED DESIGN", src,
                                      "custom layer count at the PICMA layer thickness (supplier custom part)"),
            "bender_free_length": _leaf(round(x["Lf"], 6), "m", "PROPOSED DESIGN", src),
            "bender_clamp_length": _leaf(round(x["Lc"], 6), "m", "PROPOSED DESIGN", src),
            "bender_free_stroke": _leaf(round(bn["delta_f"], 7), "m", "CALCULATION", src + "; +/-20 % (AMF-11)",
                                        "tip, unloaded, at 60 V"),
            "bender_block_force": _leaf(round(bn["F_b"], 4), "N", "CALCULATION", src + "; +/-20 % (AMF-11)",
                                        "per plate position at 60 V" + (" (both plates)" if opts.stack > 1 else "")),
            "bender_capacitance": _leaf(float(f"{bn['C_half']:.4g}"), "F", "CALCULATION", src,
                                        "per half" + (" (both plates of a position)" if opts.stack > 1 else "") +
                                        ", small signal; electrodes over the clamp " +
                                        ("included (conservative)" if opts.clamp_electroded else "excluded (inactive clamp)")),
            "bender_voltage": _leaf(round(x["V"], 2), "V", "PROPOSED DESIGN", f"{drv['label']} ({drv['ledger']})"),
            "lever": _leaf(round(F(st["n"]), 4), "-", "CALCULATION", "gimbal %.1f mm / (gimbal - collar centre %.1f mm)"
                           % (x["zg"] * 1e3, (x["zc0"] + 1.5e-3) * 1e3)),
            "travel_nib": _leaf(round(x["q_stop"] - opts.servo_margin, 6), "m", "PROPOSED DESIGN",
                                "stop travel minus the 0.10 mm servo margin (as P0.1.2)"),
            "stop_travel_nib": _leaf(round(x["q_stop"], 6), "m", "PROPOSED DESIGN", "opt/hardware"),
            "stroke_under_load": _leaf(round(F(ev["q_nom"]), 7), "m", "CALCULATION",
                                       "nominal 50 deg, mu 0.15, worst direction; worst case (-20 %%, 35 deg): %.0f um"
                                       % (F(ev["q_wc"]) * 1e6)),
            "first_resonance": _leaf(round(F(st["f1"]), 1), "Hz", "CALCULATION", "lumped (design.py reduction)"),
            "decoupling_leaf": _leaf(f"{opts.leaf_mat} leaf {x['leaf_t'] * 1e6:.0f} um thick, {x['leaf_w'] * 1e3:.2f} mm "
                                     f"wide, {x['leaf_L'] * 1e3:.2f} mm free span", "-", "PROPOSED DESIGN",
                                     "opt/hardware leaf rules (cross <= 5 % of the axis, drive >= 20x, buckling SF >= 2, "
                                     "stress <= allowable)"),
            "position_sensor": _leaf(hall["label"], "-", "PROPOSED DESIGN", f"{hall['ledger']}; {hall['note']}"),
        },
        "electronics": {
            "piezo_driver": _leaf(drv["label"], "-", "PROPOSED DESIGN", f"{drv['ledger']}; {drv['note']}"),
        },
        "cad_parameters_mm": cad_ov or cad_overlay(x, opts),
    }
    # only what changes from P0.1.2 (skid ring 1.4 mm, cell 40 mm, F_c 0.15 N)
    if abs(x["r_ring"] - 1.4e-3) > 1e-7:
        doc["skid"] = {"ring_radius": _leaf(round(x["r_ring"], 6), "m", "PROPOSED DESIGN",
                                            "opt/hardware: more room in the nose (Hall sensor, collar) and refill-cone "
                                            "clearance; lengthens the nib's axial travel between tilts (EXP-Q08)")}
    else:
        doc["meta"]["notes"].append("skid ring radius unchanged (1.4 mm)")
    if abs(x["L_cell"] - 40e-3) > 1e-7:
        doc["battery"] = {"length": _leaf(round(x["L_cell"], 5), "m", "PROPOSED DESIGN", "opt/hardware"),
                          "capacity_mAh": _leaf(round(float(MD.cell_capacity_mAh(torch.tensor(x['L_cell']))), 1), "mAh",
                                                "ASSUMPTION", "90 mAh at 40 mm scaled with the CG-series dead length (AMF-43)")}
    else:
        doc["meta"]["notes"].append("cell unchanged (40 mm, 90 mAh ASSUMPTION)")
    if abs(x["Fc"] - 0.15) > 1e-9:
        doc["nib"] = {"spring_force": _leaf(round(x["Fc"], 4), "N", "ASSUMPTION", "EXP-Q02 must confirm the ink writes at it")}
    else:
        doc["meta"]["notes"].append("nib spring force unchanged (0.15 N, ASSUMPTION, EXP-Q02)")
    doc["cad_parameters_mm"] = doc.pop("cad_parameters_mm")          # keep it last
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Rev P0.2 PROPOSED overlay of config/pencil.yaml (opt/hardware). Only the parameters that change.\n")
        f.write("# Nothing here is measured. Labels: PROPOSED DESIGN, CALCULATION, ASSUMPTION (ledger ids in sources).\n")
        f.write("# CAD: python3 mechanics/cad/pencil_revP.py --variant %s --overlay %s --tag pencil_revP%s_%s --out results/opt/cad\n"
                % ("Q" if opts.topology != "L" else "L", os.path.relpath(path, ROOT), "Q" if opts.topology != "L" else "L", key))
        yaml.safe_dump(doc, f, sort_keys=False, width=140, allow_unicode=False)
    return doc
