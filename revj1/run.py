r"""Rev J.1 pipeline: python3 -m revj1.run [--quick] [--no-figures] [--rerun-endcap]

Writes (results/revJ1/, or results/revJ1/_quick/ with --quick):
  layout.json         the Rev J.1 pen in the Rev J layout schema, with fit checks and the list of changes
  budgets.json        mass, centre of mass, inertia, length, power and battery per mode (x1 / x2 / x5 nose power, three
                      page-sensor options, two cells), heat, targets
  sim_params.json     MuJoCo parameters in the schema of results/revJ/sim_params.json
  gimbal.json         P1 structure: the cross-strip pivot under the pull, thrust pivots, shock
  magnetics.json      P1 magnetics (spacer, air core, ring, centring) and P6 (detent), plus Rev J's field checks re-run on
                      the Rev J.1 layout (nose Halls, outside field)
  endcap.json         P4: the end-cap family on study K's model (SIM; cached in results/revJ1/_cache/)
  visibility.json     P5: options x tilts x eye positions
  revJ1.json          headline numbers, choices, proposed decision, requirements and experiments
  evidence_rows.csv   proposed ledger rows (sources opened here)
  fig_revJ1_*.png     figures, each with a CSV twin
Every JSON carries a 'stabpen.provenance' block.  One process.  The end-cap SIM stage runs only if its cache is missing
(about 20 min on one core); --quick reuses the full cache when it exists.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import Dict

from . import CACHE_DIR, EVIDENCE_CALC, RESULTS_DIR, ensure_paths

ensure_paths()


def _prov(status: str, quick: bool, extra: Dict = None) -> Dict:
    from stabpen import provenance
    return provenance.metadata(status, extra={"script": "revj1/run.py", "doc": "docs/revJ1_design.md", "quick": quick,
                                              **(extra or {})})


def _clean(o):
    import numpy as np
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.floating):
        o = float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return "inf" if math.isinf(o) else "nan"
    return o


def _write(path: str, obj: Dict, status: str, quick: bool):
    md = _prov(status, quick)
    obj = {"meta": md, "stabpen.provenance": md, **obj}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(obj), f, indent=1)


def endcap_results(quick: bool, rerun: bool, log) -> Dict:
    from . import endcap_mass as EM
    full_ok = (CACHE_DIR / "full" / "endcap_tune.json").exists() and (CACHE_DIR / "full" / "endcap_test_j1m2.json").exists()
    use_quick = quick and not full_ok
    if rerun or not (CACHE_DIR / ("quick" if use_quick else "full") / "endcap_tune.json").exists():
        t = EM.tune_stage(use_quick, log)
        EM.test_stage(t, use_quick, log)
        EM.test_stage(t, use_quick, log, members=EM.RULE_J1_M2["members_mm"], tag="test_j1m2")
    s = EM.summary(use_quick, log, run_missing=False)
    te2 = EM._load("test_j1m2", use_quick)
    s["test_j1m2"] = {"verdicts": (te2 or {}).get("verdicts"), "summary": (te2 or {}).get("summary"),
                      "members_tested": (te2 or {}).get("members_tested"), "rule": EM.RULE_J1_M2}
    s["test"]["verdicts"] = dict((s["test"].get("verdicts") or {}), **((te2 or {}).get("verdicts") or {}))
    s["cache"] = "quick" if use_quick else "full"
    return s


def main(argv=None) -> Dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--rerun-endcap", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    out = str(RESULTS_DIR / "_quick") if a.quick else str(RESULTS_DIR)
    os.makedirs(out, exist_ok=True)
    log = lambda m: print(f"[{time.time() - t0:6.1f}s] {m}", flush=True)          # noqa: E731

    from revj import budgets as RBU
    from revj import frontend as RFR
    from revj import magnetics as RMG
    from revj import packaging as RPK
    from revj import run as RRUN
    from . import budgets as BU
    from . import endcap_mass as EM
    from . import evidence as EV
    from . import gimbal as GB
    from . import layout as LY
    from . import magnetics as MG
    from . import params as P1
    from . import simparams as SP
    from . import visibility as VI

    em = endcap_results(a.quick, a.rerun_endcap, log)
    log(f"end-cap family ({em['cache']} cache)")
    gm = GB.summary(a.quick)
    log(f"gimbal: study N buckles at {gm['buckling_N']['studyN_50um_beam']:.1f} N, 75 um at {gm['buckling_N']['chosen_75um_beam']:.1f} N")
    geo = LY.build(a.quick)
    fe = geo["_internal"]["fe"]
    log(f"layout: fit checks all pass = {geo['fit_checks']['all_pass']}; {geo['length']} / {geo['length_with_endcap']} mm")
    geo_revJ = RPK.build(fe, quick=a.quick)
    tf = RRUN.travel_factor(fe["X_nom_mm"])
    ver = (em["test"].get("verdicts") or {}).get(f"lrm_{LY.ENDCAP_LS_MM:g}", {})
    ec_sim = ver.get("P_act_W_mean_SIM", 0.03)
    ec_design = geo["endcap_member"]["P_avg_W_design"]
    bud = BU.summary(geo, tf["factor_P"], ec_sim, ec_design)
    bud["gimbal"]["buckling_N"] = gm["buckling_N"]["chosen_75um_beam"]
    log("budgets")
    mag1 = MG.summary(geo_revJ, GB.F_PULL_IMAGES, bud["gimbal"]["k_pull_Nm_rad"], a.quick)
    mag1["detent_revJ1_position"] = MG.detent(geo, a.quick)
    mag1["nose_hall_revJ1"] = RMG.nose_hall(geo)
    mag1["outside_revJ1"] = RMG.outside_field(geo, dists=(5.0, 10.0, 20.0, 30.0, 50.0) if a.quick else
                                              (5.0, 10.0, 20.0, 30.0, 50.0, 100.0))
    log("magnetics")
    mag_rj = {"axial_pull": RMG.axial_pull(n=81 if a.quick else 161), "c1s_at_motors": RMG.c1s_at_motors(geo),
              "nose_hall": mag1["nose_hall_revJ1"]}
    bud_rj = RBU.summary(geo, tf["factor_P"])
    sim = SP.build(geo, bud_rj, mag_rj, fe, geo["_internal"]["refill"], bud, mag1, ver)
    nz, h = geo["_internal"]["nz"], geo["_internal"]["h"]
    vis = VI.sweep(fe["R_mm"], nz, h, quick=a.quick)
    vis["materials"] = VI.MATERIALS
    vis["chosen"] = VI.CHOSEN
    log("visibility")

    # ---------------------------------------------------------------- write
    lay = LY.public(geo)
    md = _prov("PROPOSED DESIGN (Rev J.1 pen; dimensions CALC or ASSUMPTION; masses CALC); nothing built", a.quick,
               {"script": "revj1/layout.py via revj1/run.py"})
    md.update({"groups": list(RPK.GROUPS), "moves_with_values": list(RPK.MOVES), "base": "results/revJ/layout.json (Rev J)",
               "changes": geo["revJ1_changes"],
               "optional_note": "group 'inertial' = the detachable end-cap (optional: true); it replaces the rear cap"})
    with open(os.path.join(out, "layout.json"), "w", encoding="utf-8") as f:
        json.dump(_clean({"meta": md, "stabpen.provenance": md, **lay}), f, indent=1)
    _write(os.path.join(out, "budgets.json"), {"budgets": bud, "travel_factor": tf, "inputs": P1.all_tables()}, EVIDENCE_CALC, a.quick)
    _write(os.path.join(out, "sim_params.json"), {"sim_params": sim}, EVIDENCE_CALC + " (parameters for sim2)", a.quick)
    _write(os.path.join(out, "gimbal.json"), {"gimbal": gm}, EVIDENCE_CALC, a.quick)
    _write(os.path.join(out, "magnetics.json"), {"magnetics": mag1}, EVIDENCE_CALC + " (magpylib; ideal iron where iron appears)", a.quick)
    _write(os.path.join(out, "endcap.json"), {"endcap": em}, "SIMULATION (study K's model H1, read-only) and CALCULATION", a.quick)
    _write(os.path.join(out, "visibility.json"), {"visibility": vis}, EVIDENCE_CALC, a.quick)
    head = headline(geo, bud, gm, mag1, em, vis)
    _write(os.path.join(out, "revJ1.json"), head, EVIDENCE_CALC, a.quick)
    EV.write(os.path.join(out, "evidence_rows.csv"))
    log("json written to " + out)
    if not a.no_figures:
        from . import figures as FG
        vis_fig = dict(vis)
        FG.all_figures(out, gm, bud, em, vis_fig, mag1["detent"])
        log("figures")
    log("done")
    return head


def headline(geo, bud, gm, mag1, em, vis) -> Dict:
    mb = bud["mass"]
    nom = bud["power"]["x1_PMW3610_class"]
    ver = (em["test"].get("verdicts") or {})
    return {
        "length_mm": {"base": geo["length"], "with_endcap": geo["length_with_endcap"], "revJ": [bud["revJ"]["length_base_mm"],
                                                                                            bud["revJ"]["length_with_endcap_mm"]]},
        "mass_g": {"base": mb["base"]["mass_g"], "with_endcap": mb["with_endcap"]["mass_g"],
                   "com_base_mm": mb["base"]["com_mm"][2], "com_with_endcap_mm": mb["with_endcap"]["com_mm"][2],
                   "revJ": [bud["revJ"]["mass_base_g"], bud["revJ"]["mass_with_endcap_g"]]},
        "hours_LIR14500_x1": {k: v["h"] for k, v in nom["hours"]["LIR14500"].items()},
        "hours_LIR14500_x1_with_endcap": {k: v["h_with_endcap"] for k, v in nom["hours"]["LIR14500"].items()},
        "hours_LIR14500_x2": {k: v["h"] for k, v in bud["power"]["x2_PMW3610_class"]["hours"]["LIR14500"].items()},
        "hours_LIR14500_x5": {k: v["h"] for k, v in bud["power"]["x5_PMW3610_class"]["hours"]["LIR14500"].items()},
        "hours_ICR14650_x1": {k: v["h"] for k, v in nom["hours"]["ICR14650"].items()},
        "electronics_W": bud["electronics"]["total_W"], "page_options_W": {k: v for k, v in bud["page_options"].items() if isinstance(v, list)},
        "web_C_room30_x1": {k: v["x1"]["web_C_room30"] for k, v in bud["heat"]["web"]["rows"].items()},
        "web_C_room30_by_factor": {f: {k: v["x1"]["web_C_room30"] for k, v in t["rows"].items()} for f, t in bud["heat"]["web_by_factor"].items()},
        "spreader": {"chosen": bud["heat"]["chosen"], "R_K_W": bud["heat"]["chosen_R_K_W"], "mass_g": bud["heat"]["chosen_mass_g"],
                     "bare_R_K_W": bud["heat"]["bare_R_K_W"]},
        "gimbal": {"buckling_N": gm["buckling_N"], "chosen": gm["chosen"],
                   "k_pull_mNm_rad": bud["gimbal"]["k_pull_Nm_rad"] * 1e3, "k_unloaded_mNm_rad": bud["gimbal"]["k_unloaded_Nm_rad"] * 1e3,
                   "goodman_SF": gm["options"]["C_chosen_75um_compression"]["goodman_SF_1e8"]},
        "pull_N": {k: v["pull_N"] for k, v in mag1["pull_variants"]["D_conventions"].items()},
        "detent_mNm": {"revJ_position": mag1["detent"]["worst_torque_amp_mNm"],
                       "revJ1_position": mag1["detent_revJ1_position"]["worst_torque_amp_mNm"], "friction": 0.011},
        "endcap": {"member": geo["endcap_member"], "verdicts_test": ver},
        "visibility": {k: {"within_1mm": v["share_within_1mm"], "within_3mm": v["share_within_3mm"]} for k, v in vis["options"].items()},
        "fit_checks_all_pass": geo["fit_checks"]["all_pass"],
        "changes": geo["revJ1_changes"],
    }


if __name__ == "__main__":
    main()
