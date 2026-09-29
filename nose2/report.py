r"""results/nose2/nose2.json: every number of study N with its label (CALC, SIM, LIT/MFR id, ASSUMPTION), written by
stabpen.provenance; the main tables of docs/nose_v2.md are built here.
"""
from __future__ import annotations

import math
from dataclasses import asdict, replace
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths

ensure_paths()
from stabpen import provenance  # noqa: E402

E_CALC = "CALC"
E_SIM = "SIM"
BASE_W = 0.065 + 0.012          # W, Rev H electronics base + drivers/Hall (ASSUMPTION, results/revH/tip_params.json power_model)
CELL_WH = 2.22                  # Wh usable, EEMB LIR14500 (MFR AMF-80 via results/revH/tip_params.json)


def r(x, nd=3):
    if isinstance(x, (float, np.floating)):
        return float(round(float(x), nd)) if math.isfinite(float(x)) else None
    return x


def revh_in_model(duty: Dict) -> Dict:
    """Rev H's nose with this study's inertia and duty models (CALC): z_p 45 mm, magnets at 79 mm, 3.0 x 6.5 x 2.8 mm
    blocks, 1.43 mm coils, 3 mm nominal travel, gimbal k_r 0.025 N m/rad (301 full hard 0.1 mm, b/L_f 0.75).  The force
    constant is taken two ways: as Rev H states it (0.355 N/sqrt(W) at the tip) and recalibrated by the image calculation
    with Rev H's own coil rule (designs.revh_as_designed: 0.140).  This study's constant-force rule (the coil legs stay
    over the poles over the whole stroke) cannot be met by Rev H's 3 mm poles with a 2.3-2.6 mm stroke; that is reported
    as a finding, not used here."""
    import torch
    from . import designs as DS
    from . import optimise as OP
    d = DS.Duty(**{k: v for k, v in duty.items() if k in DS.Duty.__dataclass_fields__})
    v = {"z_p": 0.045, "L_b": 0.034, "w": 3.0e-3, "l": 6.5e-3, "t_m": 2.8e-3, "t_c": 1.43e-3, "b_f": 3.0e-3, "L_f": 4.0e-3, "X": 3.0e-3}
    parts = DS.Parts(grade="N42SH", flexure="301FH", t_flex=100e-6, wire=0.10e-3, iron="1010", bore="22")
    d = replace(d, x_min=2.0e-3)
    with torch.no_grad():
        out = DS.evaluate("gimbal_radial", {k: torch.tensor(val, dtype=DS.DT) for k, val in v.items()}, parts, d)
    s = OP.summary("gimbal_radial", v, parts, out)
    o = DS.to_float(out)
    rh = DS.revh_as_designed(1.33)
    res = {"X_min_mm": s["X_min_mm"], "X_nom_mm": s["X_nom_mm"], "m_eff_tip_g": s["m_eff_tip_g"], "k_tip_N_m": s["k_tip_N_m"],
           "F_aw_rms_N": o["F_aw_rms"], "F_tr_rms_N": o["F_tr_rms"], "servo_hz_max": s["servo_hz_max"], "front_R_mm": s["front_R_mm"],
           "refill_slide_mm": s["refill_slide_mm"], "z_p_mm": 45.0, "z_a_mm": 79.0, "stroke_act_mm": s["stroke_act_mm"],
           "gap_mm": 2.77, "r_act_mm": 10.0, "mass_added_g": None,
           "constant_force_rule": {"pole_width_mm": 3.0, "stroke_at_stop_mm": s["stroke_act_mm"], "met": False}}
    for tag, Km in (("stated", 0.355), ("images", rh["Km_tip_images"])):
        res[f"Km_tip_{tag}"] = Km
        res[f"P_tremor_W_{tag}"] = 2 * (o["F_tr_rms"] / Km) ** 2
        res[f"P_autowrite_W_{tag}"] = 2 * (o["F_aw_rms"] / Km) ** 2
        res[f"F_pk_tip_N_{tag}"] = Km * math.sqrt(DS.V_BUS * DS.I_PEAK)
    res["Km_tip"] = res["Km_tip_images"]
    res["P_tremor_W"] = res["P_tremor_W_images"]
    res["P_autowrite_W"] = res["P_autowrite_W_images"]
    res["F_pk_tip_N"] = res["F_pk_tip_N_images"]
    res["dT_coil_K"] = res["P_autowrite_W"] * DS.R_TH_COIL
    res["label"] = ("CALC (Rev H geometry, this study's inertia and duties; Km as recalibrated by the image method, Rev H's coil rule; "
                    "Rev H states 0.47 N/sqrt(W) at the magnets, 0.355 at the tip)")
    return res


COLS = [("X_min_mm", "guaranteed tip travel, 35-75 deg, every direction (mm)", 2),
        ("Km_tip", "force per sqrt(W) at the tip, per axis (N/sqrt(W))", 3),
        ("m_eff_tip_g", "moving mass at the tip (g)", 2),
        ("mass_added_g", "added mass: actuator, flexure, iron (g)", 1),
        ("P_autowrite_W", "coil loss autowriting with 1 mm tremor (W)", 3),
        ("P_tremor_W", "coil loss stabilising 1 mm tremor only (W)", 3),
        ("F_aw_rms_N", "reaction on the hand while autowriting, rms per axis (N)", 3),
        ("F_pk_tip_N", "peak tip force at 3.7 V / 1.5 A (N)", 2),
        ("servo_hz_max", "servo bandwidth the first parasitic mode allows (Hz)", 0),
        ("dT_coil_K", "coil temperature rise while autowriting with tremor (K)", 1),
        ("r_act_mm", "actuator outer radius (mm)", 2),
        ("front_R_mm", "skid-ring contact radius (mm)", 2),
        ("refill_slide_mm", "refill slide over 35-75 deg and the travel (mm)", 1),
        ("stroke_act_mm", "magnet stroke at the stop (mm)", 2),
        ("gap_mm", "magnet-coil gap (mm)", 2),
        ("z_p_mm", "pivot (or virtual pivot) behind the ball (mm)", 1),
        ("z_a_mm", "actuator behind the ball (mm)", 1)]


def main_table(op: Dict, ch: Dict, revh: Dict) -> Dict:
    """Candidates at the recommended travel and handle (best feasible per candidate; if none, the largest feasible travel
    in that handle), Rev H in the same models, and the screening-only mechanisms (CALC; MFR/LIT ids in 'screening')."""
    from .choose import J, best_per_cell
    rec = ch["recommended"]
    bore = "22" if rec["handle_od"] == 22.0 else "24"
    x = rec["x_chosen_mm"]
    cells = [c for c in best_per_cell(op["best"]) if abs(c["mu_m"] - 4.0) < 1e-9 and c["bore"] == bore]
    rows = []
    kinds = ["gimbal_sphere", "gimbal_radial", "gimbal_axial", "dual_plane", "coarse_fine", "xy_wire"]
    for k in kinds:
        at = [c for c in cells if c["kind"] == k and abs(c["x_min_req_mm"] - x) < 1e-6 and c.get("feasible")]
        note = f"feasible at {x:g} mm"
        if not at:
            feas = sorted([c for c in cells if c["kind"] == k and c.get("feasible")], key=lambda c: c["x_min_req_mm"])
            if not feas:
                rows.append({"candidate": k, "note": f"no feasible design at 4-8 mm in the {bore} mm handle"})
                continue
            at = [feas[-1]]
            note = f"not feasible at {x:g} mm; largest feasible travel {feas[-1]['x_min_req_mm']:g} mm"
        c = at[0]
        row = {"candidate": k, "note": note, "recommended": c is rec["design"] or (c["kind"] == rec["design"]["kind"] and
                                                                                    abs(J(c) - rec["J"]) < 1e-9), "J": r(J(c), 4)}
        for key, _, nd in COLS:
            row[key] = r(c.get(key), nd)
        row["parts"] = c.get("parts")
        rows.append(row)
    rh = {"candidate": "revH (Rev H nose, same models)", "note": "3 mm nominal travel", "recommended": False}
    for key, _, nd in COLS:
        rh[key] = r(revh.get(key), nd)
    rows.insert(0, rh)
    return {"handle_od": rec["handle_od"], "travel_mm": x, "columns": [{"key": k, "label": lab} for k, lab, _ in COLS], "rows": rows,
            "screening": op["screening"], "label": "CALC (PROPOSED DESIGNS; nose2/designs.py; mu_m 4 W/kg runs)"}


def _agg(rows: List[Dict], keys) -> Dict:
    out = {"n": len(rows), "plan_fail": sum(1 for x in rows if not x.get("plan_ok"))}
    ok = [x for x in rows if x.get("plan_ok")]
    for k in keys:
        v = [x[k] for x in ok if x.get(k) is not None and x[k] == x[k]]
        out[k] = r(float(np.mean(v)), 4) if v else None
    if ok:
        per_w = {}
        for x in ok:
            per_w.setdefault(x["w"], []).append(x["letters_read"])
        out["letters_read_worst_writer"] = r(min(float(np.mean(v)) for v in per_w.values()), 4)
        per_w = {}
        for x in ok:
            per_w.setdefault(x["w"], []).append(x["ink_err_um"])
        out["ink_err_worst_writer_um"] = r(max(float(np.mean(v)) for v in per_w.values()), 1)
    return out


AW_KEYS = ("ink_err_um", "ink_p95_um", "letters_read", "target_letters_read", "words_read_app", "target_words_read_app",
           "letters_per_s", "v_h_mm_s", "P_coil_W", "F_rms_N", "F_p99_N", "at_travel_limit", "at_force_limit", "q_max_mm",
           "handle_dev_rms_um", "passes", "convergence_dq_um")


def autowrite_table(test: Dict, axial_W: Dict[str, float]) -> List[Dict]:
    """Per design and x-height: no tremor, and each tremor amplitude over 4/8/12 Hz (SIM, test writers and seeds).
    Total power = coil loss (SIM) + electronics 0.077 W (ASSUMPTION, Rev H) + the pen lift (CALC, designs.axial_dof)."""
    rows = test["rows"]
    out = []
    for d, h in sorted({(x["design"], x["h_mm"]) for x in rows}):
        for a in sorted({x["amp_mm"] for x in rows}):
            sub = [x for x in rows if x["design"] == d and x["h_mm"] == h and abs(x["amp_mm"] - a) < 1e-9]
            if not sub:
                continue
            g = _agg(sub, AW_KEYS)
            g.update({"design": d, "h_mm": h, "tremor_mm": a})
            if g.get("P_coil_W") is not None:
                P = g["P_coil_W"] + BASE_W + axial_W.get(d, 0.0)
                g["battery_h_autowriting"] = r(CELL_WH / P, 1)
                g["P_total_W"] = r(P, 3)
            out.append(g)
    return out


def by_frequency(test: Dict, design: str = "revJ", h: float = 2.5) -> List[Dict]:
    rows = [x for x in test["rows"] if x["design"] == design and x["h_mm"] == h]
    out = []
    for a in sorted({x["amp_mm"] for x in rows}):
        for f in sorted({x["f0"] for x in rows if x["amp_mm"] == a}):
            sub = [x for x in rows if abs(x["amp_mm"] - a) < 1e-9 and x["f0"] == f]
            g = _agg(sub, ("ink_err_um", "letters_read", "words_read_app", "P_coil_W", "at_travel_limit"))
            g.update({"tremor_mm": a, "f0_Hz": f if a > 0 else None})
            out.append(g)
            if a == 0:
                break
    return out


def headline(doc: Dict) -> Dict:
    """The numbers the answer quotes (each with its label)."""
    rec = doc["recommended"]
    d = rec["design"]
    aw = doc["autowrite"]["table"]

    def pick(design, h, a):
        for x in aw:
            if x["design"] == design and x["h_mm"] == h and abs(x["tremor_mm"] - a) < 1e-9:
                return x
        return None
    h0 = {"mechanism": d["kind"], "handle_od_mm": rec["handle_od"], "guaranteed_travel_mm": r(d["X_min_mm"], 2),
          "nominal_travel_mm": r(d["X_nom_mm"], 2), "Km_tip": r(d["Km_tip"], 3), "m_eff_tip_g": r(d["m_eff_tip_g"], 2),
          "P_autowrite_W": r(d["P_autowrite_W"], 3), "P_tremor_W": r(d["P_tremor_W"], 3), "mass_added_g": r(d["mass_added_g"], 1),
          "label": "CALC (design model)"}
    for key, design, h, a in (("aw_2p5_none", "revJ", 2.5, 0.0), ("aw_2p5_1mm", "revJ", 2.5, 1.0), ("aw_2p5_2mm", "revJ", 2.5, 2.0),
                              ("aw_3p0_none", "revJ", 3.0, 0.0), ("aw_3p0_1mm", "revJ", 3.0, 1.0),
                              ("noaxial_2p5_none", "revJ_noaxial", 2.5, 0.0), ("noaxial_2p5_1mm", "revJ_noaxial", 2.5, 1.0)):
        x = pick(design, h, a)
        if x:
            h0[key] = {k: x.get(k) for k in ("ink_err_um", "letters_read", "target_letters_read", "words_read_app", "letters_per_s",
                                             "P_coil_W", "at_travel_limit", "plan_fail", "n", "letters_read_worst_writer",
                                             "battery_h_autowriting")}
            h0[key]["label"] = "SIM (HW1; test writers 0-5, seeds 200-203; mean over 4/8/12 Hz when tremor)"
    revh = [x for x in aw if x["design"] == "revH"]
    if revh:
        h0["revH"] = {"h_mm": revh[0]["h_mm"], "none": {k: revh[0].get(k) for k in ("ink_err_um", "letters_read", "target_letters_read")},
                      "label": "SIM (Rev H at the largest x-height its plan reach fits)"}
    return h0


def build(data: Dict, quick: bool = False) -> Dict:
    tk, fe, mg, op, ch = data["tasks"], data["frontend"], data["magnetics"], data["optimise"], data["choose"]
    tu, te, li, se = data["tuning"], data["test"], data["limits"], data["sensitivity"]
    revh = revh_in_model(op["duty"])
    rec = ch["recommended"]
    doc = {"meta": provenance.metadata("CALCULATION + SIMULATION (model HW1 via nose2; synthetic writers and tremor) + PROPOSED DESIGN; "
                                       "nothing measured" + (" - QUICK RUN (tiny subsets; not for the doc)" if quick else ""),
                                       seeds={"tuning_writers": [100, 101, 102, 103], "tuning_seeds": [300, 301, 302, 303],
                                              "test_writers": [0, 1, 2, 3, 4, 5], "test_seeds": [200, 201, 202, 203]},
                                       extra={"script": "nose2/run_study.py", "doc": "docs/nose_v2.md", "quick": quick}),
           "labels": {"CALC": "calculation on a proposed design (models in nose2/)", "SIM": "executed simulation of model HW1",
                      "LIT/MFR": "published or manufacturer statement, ledger id", "ASSUMPTION": "an input nobody has measured"},
           "tasks": {"label": tk["label"], "tremor_peaks": tk["tremor"], "guidance": tk["guidance"], "autowrite_reach": tk["autowrite_reach"],
                     "delayed_ink": tk["delayed_ink"], "kinematics": tk["kinematics"], "requirements": tk["requirements"]},
           "requirement": ch["requirement"],
           "frontend": {"label": fe["label"], "rows": fe["rows"], "check_vs_original": fe["check_vs_original"],
                        "refill_follows_lift": fe.get("refill_follows_lift")},
           "magnetics": {"label": mg["label"], "image_check_max_abs_diff_T": mg["image_check"]["max_abs_diff_T"],
                         "revh": mg["revh"],
                         "surrogate": {k: {"n": mg[k]["n"], "frozen_check": mg[k]["frozen_check"], "refit": {kk: v for kk, v in mg[k]["refit"].items()
                                                                                                             if kk != "coef"}}
                                       for k in ("radial", "axial")}},
           "optimise": {"label": op["label"], "duty": op["duty"], "sweep_config": op["sweep_config"], "sweep_source": op["sweep_source"],
                        "max_reeval_dP_W": op["max_reeval_dP_W"], "grad_check_worst_rel_err": op["grad_check"]["worst_rel_err"],
                        "cells": [{k: (r(v, 4) if isinstance(v, float) else v) for k, v in c.items() if k not in ("pen_terms",)}
                                  for c in ch["cells"]],
                        "pareto_travel_power": {k: [{kk: r(vv, 4) for kk, vv in x.items() if kk in ("X_min_mm", "P_autowrite_W", "mass_added_g",
                                                                                                     "Km_tip", "m_eff_tip_g", "bore")}
                                                    for x in v["front_travel_power"]] for k, v in op["fronts"].items()},
                        "pareto_4d_size": {k: len(v["front4"]) for k, v in op["fronts"].items()},
                        "n_feasible_evaluated": {k: v["n_feasible_evaluated"] for k, v in op["fronts"].items()},
                        "screening": op["screening"]},
           "recommended": {"design": rec["design"], "handle_od": rec["handle_od"], "x_req_mm": rec["x_req_mm"],
                           "x_chosen_mm": rec["x_chosen_mm"], "shortfall_mm": rec["shortfall_mm"], "why": rec["why"], "J": rec["J"],
                           "per_kind_at_choice": rec["per_kind"], "rule": ch["rule"], "alternatives": ch.get("alternatives"),
                           "label": "CALC (PROPOSED DESIGN)"},
           "revh_in_model": revh,
           "main_table": main_table(op, ch, revh),
           "hw1_designs": ch["hw1_designs"], "axial_dof": ch.get("axial_dof"),
           "tuning": {"settings": tu["settings"], "log": tu["log"], "label": tu["label"]},
           "autowrite": {"settings": te["settings"], "sizes": te["sizes"], "revH_size_rule": te["revH_size_rule"],
                         "table": autowrite_table(te, {k: (v["axial_W"] if v.get("axial") else 0.0)
                                                       for k, v in ch["hw1_designs"].items()}),
                         "by_frequency_revJ_2p5": by_frequency(te),
                         "label": te["label"]},
           "limits": li,
           "sensitivity": {"summary": se["summary"], "label": se["label"]},
           "layout": data.get("layout"), "cad": data.get("cad"),
           "figures": {k: v for k, v in (data.get("figures") or {}).get("files", {}).items() if isinstance(v, str)},
           "example": (data.get("figures") or {}).get("files", {}).get("autowrite_example_metrics")}
    doc["headline"] = headline(doc)
    return doc


def evidence_numbers(doc: Dict) -> Dict[str, str]:
    """Strings for the derived ledger rows (evidence.py placeholders)."""
    R = {}
    m = doc["magnetics"]
    rh = m["revh"]["as_designed_Br_1.33"]
    sr, sa = m["surrogate"]["radial"]["frozen_check"], m["surrogate"]["axial"]["frozen_check"]
    R["amf150"] = (f"Rev H actuator gap flux: lumped formula (eta 0.55) {rh['B_lumped_T']:.3f} T vs images {rh['B_images_T']:.3f} T "
                   f"(eta {rh['eta_images']:.3f}); Km at the actuator {rh['Km_act_lumped']:.2f} vs {rh['Km_act_images']:.2f} N/sqrt(W), "
                   f"at the tip {rh['Km_tip_lumped']:.3f} vs {rh['Km_tip_images']:.3f} (Rev H states 0.47 and 0.355).  Surrogate vs magpylib: "
                   f"radial rel. RMS {sr['rel_rms'] * 100:.1f} % (max {sr['rel_max'] * 100:.0f} %, {sr['n']} geometries), axial "
                   f"{sa['rel_rms'] * 100:.1f} % (max {sa['rel_max'] * 100:.0f} %, {sa['n']}).")
    fr = [x for x in doc["frontend"]["rows"] if x["z_p_mm"] == 45.0]
    if fr:
        a, b = fr[0], fr[-1]
        R["amf151"] = (f"At z_p 45 mm: nominal travel {a['travel_nominal_mm']:g} -> {b['travel_nominal_mm']:g} mm needs contact radius "
                       f"{a['R_mm']:.2f} -> {b['R_mm']:.2f} mm, refill slide {a['refill_slide_mm']:.1f} -> {b['refill_slide_mm']:.1f} mm, "
                       f"guaranteed minimum travel {a['ball_travel_min_mm']:.2f} -> {b['ball_travel_min_mm']:.2f} mm; checked against "
                       f"opt/inertial/front_end.check (max abs diff {max(c['max_abs_diff'] for c in doc['frontend']['check_vs_original']):.1e}).")
    di = doc["tasks"]["delayed_ink"]
    R["amf154"] = "; ".join(f"{k}: p99 {v['synthetic_p99_mm']:.2f} mm (synthetic speed), {v['adult_speed_p99_mm']:.2f} mm (30.5 mm/s), "
                            f"{v['inked_share_lifted_before_finish'] * 100:.0f} % of inked samples laid after the stroke's pen lift"
                            for k, v in di.items())
    h = doc["headline"]
    R["act103"] = (f"Recommended: {h['mechanism']} in a {h['handle_od_mm']:g} mm handle, guaranteed travel {h['guaranteed_travel_mm']} mm "
                   f"(nominal {h['nominal_travel_mm']} mm at 50 deg), Km at the tip {h['Km_tip']} N/sqrt(W), moving mass at the tip "
                   f"{h['m_eff_tip_g']} g, coil loss {h['P_autowrite_W']} W autowriting with 1 mm tremor ({h['P_tremor_W']} W stabilising "
                   f"only), added mass {h['mass_added_g']} g.  Rev H in the same models: Km at the tip {doc['revh_in_model']['Km_tip']:.3f} "
                   f"N/sqrt(W), {doc['revh_in_model']['X_min_mm']:.2f} mm guaranteed.")
    parts = []
    for key, lab in (("aw_2p5_none", "2.5 mm letters, no tremor"), ("aw_2p5_1mm", "2.5 mm, 1 mm tremor"), ("aw_2p5_2mm", "2.5 mm, 2 mm tremor"),
                     ("aw_3p0_none", "3.0 mm, no tremor"), ("noaxial_2p5_none", "no pen lift, 2.5 mm, no tremor")):
        x = h.get(key)
        if x:
            parts.append(f"{lab}: ink error {x['ink_err_um']:.0f} um, letters read {x['letters_read'] * 100:.1f} % (ceiling "
                         f"{x['target_letters_read'] * 100:.1f} %), words (app) {x['words_read_app'] * 100:.0f} %, "
                         f"{x['letters_per_s']:.2f} letters/s, coil {x['P_coil_W']:.3f} W")
    R["act104"] = "; ".join(parts)
    # design implications (derived from the same numbers)
    fr45 = {x["travel_nominal_mm"]: x for x in doc["frontend"]["rows"] if x["z_p_mm"] == 45.0}
    if 3.0 in fr45 and 8.0 in fr45:
        dR = (fr45[8.0]["R_mm"] - fr45[3.0]["R_mm"]) / 5.0
        dS = (fr45[8.0]["refill_slide_mm"] - fr45[3.0]["refill_slide_mm"]) / 5.0
        R["amf151_impl"] = (f"Every mm of nominal travel costs about {dR:.2f} mm of skid-ring contact radius and {dS:.1f} mm of refill slide; "
                            "the guaranteed travel is about 0.88-0.92 of the nominal")
    d100 = di.get("100ms", {})
    if d100:
        R["amf154_impl"] = (f"Delayed ink of 100 ms needs {d100['synthetic_p99_mm']:.1f}-{d100['adult_speed_p99_mm']:.1f} mm; "
                            f"{d100['inked_share_lifted_before_finish'] * 100:.0f} % of its ink is laid after the hand lifts, so it needs the pen lift; "
                            "whether writers accept trailing ink is untested (OPT-50-52)")
    lay = doc.get("layout") or {}
    R["act103_impl"] = (f"Recommended {h['mechanism']} ({h['handle_od_mm']:g} mm handle): build the actuator coupon and measure Km before "
                        "the nose (EXP-N01); a flat-coil version (C1) is the fallback")
    R["act103_lim"] = (f"Lumped models; magnetic surrogate within {sr['rel_rms'] * 100:.1f} % / {sa['rel_rms'] * 100:.1f} % RMS of magpylib "
                       "(radial / axial), which itself idealises the iron; duties calibrated on HW1; no FEM")
    x = h.get("aw_2p5_1mm") or {}
    if x:
        R["act104_impl"] = (f"Autowrite works in HW1 at 2.5 mm letters with a guaranteed {h['guaranteed_travel_mm']} mm nose and a 1 kHz page "
                            f"sensor: letters read {x['letters_read'] * 100:.0f} % against a {x['target_letters_read'] * 100:.0f} % ceiling with 1 mm "
                            "tremor; test with people (EXP-N09)")
    return R
