r"""Rev J integration pipeline: python3 -m revj.run [--quick] [--no-figures]

Writes (results/revJ/, or results/revJ/_quick/ with --quick):
  layout.json       the integrated pen in the Rev H layout schema (groups, moves_with, optional end-cap), fit checks
  budgets.json      mass / centre of mass / inertia (with and without the end-cap), length, power and battery per mode,
                    heat, cost class
  sim_params.json   parameters for the MuJoCo simulator (nose, refill, heel wheel, skid ring, end-cap, sensors)
  frontend.json     the generalised DEC-034 closure, its variants, ink visibility, the page-sensor window
  refill.json       slide, holder and tendon travel, the spiral spring, the front stop, refill replacement
  magnetics.json    axial pull on the gimbal, fields at the motors, Hall sensors, IMU, outside the pen
  revJ.json         headline numbers and the proposed decision and requirement changes
  fig_revJ_*.png    figures, each with a CSV twin (revj/figures.py)
Every JSON carries a 'stabpen.provenance' block (stabpen/provenance.py).  One process; about a minute (quick: 20 s).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import replace
from typing import Dict

from . import RESULTS_DIR, EVIDENCE_CALC, ensure_paths
from . import budgets as BU
from . import frontend as FR
from . import magnetics as MG
from . import packaging as PK
from . import params as PA
from . import refill as RF
from . import simparams as SP

ensure_paths()


def _prov(status: str, quick: bool, extra: Dict = None) -> Dict:
    from stabpen import provenance
    md = provenance.metadata(status, extra={"script": "revj/run.py", "doc": "docs/revJ_design.md", "quick": quick, **(extra or {})})
    return md


def _clean(o):
    """JSON-safe: numpy -> python, inf -> the string 'inf'."""
    import numpy as np
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        o = float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return "inf" if math.isinf(o) else "nan"
    return o


def _write(path: str, obj: Dict, status: str, quick: bool):
    obj = dict(obj)
    md = _prov(status, quick)
    obj = {"meta": md, "stabpen.provenance": md, **obj}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, indent=1)


def travel_factor(X_new: float) -> Dict:
    """Coil-loss factor of study N's design at the travel the integration needs (CALC, nose2's design model)."""
    import torch
    from nose2 import designs as DS
    rec = json.load(open(PA.REPO_ROOT / "results" / "nose2" / "nose2.json"))["recommended"]["design"]
    v = {k: torch.tensor(val, dtype=torch.float64) for k, val in rec["vars"].items()}
    parts = DS.Parts(**{k: rec["parts"][k] for k in ("grade", "flexure", "t_flex", "wire", "iron", "bore")})
    o0 = DS.to_float(DS.evaluate("gimbal_sphere", v, parts, DS.Duty()))
    v2 = dict(v)
    v2["X"] = torch.tensor(X_new * 1e-3, dtype=torch.float64)
    o1 = DS.to_float(DS.evaluate("gimbal_sphere", v2, parts, DS.Duty()))
    keys = ("X_nom", "Km_tip", "P_tremor", "P_autowrite", "dT_coil", "stroke_act", "F_pk_tip", "eps_u", "eps_s")
    return {"studyN": {k: o0[k] for k in keys}, "revJ": {k: o1[k] for k in keys},
            "factor_P": o1["P_autowrite"] / o0["P_autowrite"], "factor_P_tremor": o1["P_tremor"] / o0["P_tremor"],
            "bore_penalty_revJ": o1["pen_terms"]["bore"], "strain_allow": o1["eps_f_allow"],
            "label": "CALC (nose2/designs.py evaluated read-only at study N's variables with the new travel)"}


def main(argv=None) -> Dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help="coarse grids; writes to results/revJ/_quick/")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    out_dir = str(RESULTS_DIR / "_quick") if a.quick else str(RESULTS_DIR)
    nt, npf = (9, 24) if a.quick else (17, 72)
    log = lambda m: print(f"[{time.time() - t0:5.1f}s] {m}", flush=True)          # noqa: E731

    h = FR.Heel()
    fe = FR.close(h, n_theta=nt, n_phi=npf)
    log(f"front end: R_s {fe['R_mm']} R_d {fe['R_d_mm']} X {fe['X_nom_mm']:.3f} guaranteed {fe['ball_travel_usable_min_mm']:.3f}")
    var = FR.variants(quick=a.quick)
    log("front-end variants")
    nzj = replace(FR.c1s_nose(), X=fe["X_nom_mm"])
    vis = {"revH": FR.visibility(6.75, FR.revh_nose(), None, sleeve_step=0.75, r_grip=11.0),
           "nose2": FR.visibility(10.0, FR.c1s_nose(), None, sleeve_step=0.75, r_grip=12.0),
           "revJ": FR.visibility(fe["R_mm"], nzj, h, sleeve_step=0.0, r_grip=12.0),
           "revJ_C_sleeve_10mm": FR.visibility(fe["R_mm"], nzj, h, sleeve_step=0.0, r_grip=12.0, sleeve_open_len=10.0)}
    log("visibility")
    geo = PK.build(fe, quick=a.quick)
    log(f"layout: fit checks all pass = {geo['fit_checks']['all_pass']}")
    tf = travel_factor(fe["X_nom_mm"])
    bud = BU.summary(geo, tf["factor_P"])
    log("budgets")
    mag = MG.summary(geo)
    log("magnetics")
    rf = geo["_internal"]["refill"]
    sim = SP.build(geo, bud, mag, fe, rf)
    ps = geo["_internal"]["page_sensor"]

    # ---------------------------------------------------------------- write
    lay = PK.public(geo)
    lay_meta_extra = {
        "evidence_status": "PROPOSED DESIGN (Rev J integrated pen; dimensions CALC or ASSUMPTION; masses CALC); nothing built",
        "integrates": ["study N nose v2 (results/nose2/layout.json)", "study D heel drive (results/drive/layout_parts.json)",
                       "study K end-cap (results/endcap/layout_parts.json)", "Rev H base (results/revH/layout.json)"],
        "groups": list(PK.GROUPS), "moves_with_values": list(PK.MOVES),
        "optional_note": "group 'inertial' = the detachable reaction-mass end-cap (optional: true); it replaces the rear cap "
                         "(replaced_by_endcap: true); the LRA is optional as in Rev H",
        "moves_with_note": "nose = tilts with the nose on the gimbal; drive = the heel wheel's steering, sprung pod and shafts; "
                           "inertial_mass = the end-cap's sliding slug; handle = fixed",
        "tilted_parts_note": "drive_wheel and drive_fork lie on the 50 deg paper normal; here axis-aligned stand-ins; "
                             "mechanics/cad/revJ_pen.py draws them tilted",
        "rev_h_parts_moved": {
            "board (pcb)": "from behind the actuator (Rev H z 86.5-99, study N z 95.7-111.7) to the top of the mid-section z 50-72",
            "imu": "onto the main board at z 55-57.5 (Rev H 90-92.5, study N 99.7-102.2)",
            "hall3d": "replaced by two linear Halls on the main board's underside (z 61.5-64.5), reading a magnet on the carrier",
            "battery": "right behind the coil plate (z %.1f-%.1f), axis lifted 3 mm" % tuple(geo["_internal"]["z_cell"]),
            "lra": "under the cell behind the motors (optional)",
            "usb": "beside the cell's rear end",
            "optical / drive_paper_sensor": "folded-optics page sensor beside the heel wheel",
            "board_magnet, board_keel": "removed (the heel drive replaces the board magnet; no keel: the shafts run in the "
                                        "sleeve's and shell's bottom wall)",
            "drive motors": "from z 49.5-69.5 (study D, Rev H gimbal) to under the cell, z %.1f-%.1f" % tuple(geo["_internal"]["z_motor"]),
            "rear_cap": "base pen only; the end-cap replaces it"}}
    md = _prov(lay_meta_extra["evidence_status"], a.quick, {"script": "revj/packaging.py via revj/run.py"})
    md.update({k: v for k, v in lay_meta_extra.items() if k != "evidence_status"})
    layout_obj = {"meta": md, "stabpen.provenance": _prov(lay_meta_extra["evidence_status"], a.quick), **lay}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "layout.json"), "w", encoding="utf-8") as f:
        json.dump(_clean(layout_obj), f, indent=1)
    _write(os.path.join(out_dir, "budgets.json"), {"budgets": bud, "travel_factor": tf}, EVIDENCE_CALC, a.quick)
    _write(os.path.join(out_dir, "sim_params.json"), {"sim_params": sim}, EVIDENCE_CALC + " (parameters for sim2)", a.quick)
    _write(os.path.join(out_dir, "frontend.json"),
           {"closure": {k: v for k, v in fe.items()}, "variants": var, "visibility": vis, "eyes": FR.EYES, "page_sensor": ps,
            "heel": h.__dict__, "rules": FR.RU.__dict__}, EVIDENCE_CALC, a.quick)
    _write(os.path.join(out_dir, "refill.json"), {"refill": rf}, EVIDENCE_CALC, a.quick)
    _write(os.path.join(out_dir, "magnetics.json"), {"magnetics": mag}, EVIDENCE_CALC + " (magpylib, free space unless stated)", a.quick)
    head = headline(fe, var, vis, geo, bud, mag, rf, ps, tf)
    head["round1_conflicts"] = PK.round1_conflicts(fe)
    _write(os.path.join(out_dir, "revJ.json"), head, EVIDENCE_CALC, a.quick)
    log("json written to " + out_dir)
    if not a.no_figures:
        from . import figures as FG
        FG.all_figures(out_dir, fe, var, vis, geo, bud, mag, ps)
        log("figures")
    log("done")
    return head


def headline(fe, var, vis, geo, bud, mag, rf, ps, tf) -> Dict:
    mb = bud["mass"]
    pw = bud["power"]["modes"]
    ht = bud["heat"]
    return {
        "front_end": {"R_ring_mm": fe["R_mm"], "R_wheel_mm": fe["R_d_mm"], "R_wheel_needed_mm": fe.get("R_d_needed_continuous_mm"),
                      "sleeve_front_d_mm": fe["sleeve_front_d_mm"], "sleeve_front_d_with_revH_step_mm": var["revJ_with_revH_step"]["sleeve_front_d_mm"],
                      "X_nom_mm": fe["X_nom_mm"], "X_guaranteed_mm": fe["ball_travel_usable_min_mm"],
                      "X_guaranteed_if_studyN_angle_kept_mm": var["revJ_keep_angle"]["ball_travel_usable_min_mm"],
                      "refill_slide_mm": fe["refill_slide_range_mm"], "ball_ahead_of_ring_mm": fe["protrusion_mm"],
                      "pod_without_steering_ring_R_d_mm": var["pod_without_steering_ring_R_d_mm"],
                      "label": "CALC"},
        "length_mm": {"base": geo["length"], "with_endcap": geo["length_with_endcap"]},
        "mass_g": {"base": mb["base"]["mass_g"], "with_endcap": mb["with_endcap"]["mass_g"],
                   "com_z_base_mm": mb["base"]["com_mm"][2], "com_z_with_endcap_mm": mb["with_endcap"]["com_mm"][2]},
        "power_W_and_hours": {k: {"W": v["total_W"], "h": v["hours"], "h_with_endcap": v["hours_with_endcap"]} for k, v in pw.items()},
        "power_options": {"page_sensor_gated_hours": {k: v["hours"] for k, v in bud["power_options"]["page_sensor_gated_in_steady_modes"].items()},
                          "Wh_needed_for_8h_worst": {k: v["Wh_needed_for_8h_worst"] for k, v in bud["power_options"]["energy_needed"].items()},
                          "label": bud["power_options"]["label"]},
        "heat": {k: {"coil_rise_K": v["coil_rise_K_100KW"], "web_C": v["web_surface_C"], "web_C_spreader": v["with_spreader"]["web_surface_C"]}
                 for k, v in ht["rows"].items()},
        "magnetics": {"axial_pull_N": mag["axial_pull"]["F_axial_N_images"],
                      "motor_torque_bound_mNm": mag["c1s_at_motors"]["positions"]["stop_toward"]["torque_bound_mNm"],
                      "nose_hall_tip_noise_um": mag["nose_hall"]["tip_noise_um_rms"],
                      "outside_1mT_distance_note": mag["outside"]["by_distance_from_surface_mm"]},
        "refill": {"holder_rear_max_z_mm": rf["slide"]["holder_rear_max_z_mm"], "spring": rf["spring"]["chosen"],
                   "tendon_travel_mm": rf["slide"]["tendon_travel_mm"], "ink_tail_mm": rf["front_stop"]["ink_tail_at_lift_mm"]},
        "page_sensor": {"window": ps["window"], "height_band_mm": ps["height_band_mm"]},
        "fit_checks_all_pass": geo["fit_checks"]["all_pass"],
        "travel_factor": {"P": tf["factor_P"], "Km_tip": tf["revJ"]["Km_tip"]},
    }


if __name__ == "__main__":
    main()
