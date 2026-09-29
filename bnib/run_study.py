"""Study B, the balanced two-axis nib: one command.

    python3 -m bnib.run_study [--quick] [--stages loads,candidates,optimise,sim,interface,layout,report]

Stages (each caches its output in bnib/build/stage_<name>.json and resumes from it; the sim stage also resumes case by
case from bnib/build/sim_rows.json; ONE process, one BLAS thread):
  calib       fit the voice-coil surrogate to magpylib force maps (bnib/build/vc_calibration.json; skipped if present)
  loads       the review's check, the C1S load reconciliation, the balance mechanisms' quality (Monte Carlo), ink force
  candidates  candidates (a)-(h) for the 24 mm pen and the 14 mm slim core at duties A and B (30-min thermal runs)
  optimise    CMA-ES on epsilon-constraint problems + exact-gradient polish; Pareto fronts
  sim         the best nibs in sim2: tuning (frozen rules), test grid, ideal-sensor bound, thermal run (hours)
  interface   config/nib.yaml
  layout      results/bnib/layout_parts.json and the CAD (mechanics/cad/bnib.py)
  report      results/bnib/bnib.json (+ figures with CSV twins, evidence rows) and docs/balanced_nib.md
--quick: small versions of every stage (a minute or two), written to bnib/build/quick/, never over the results.
Every output is CALC or SIM on PROPOSED DESIGNS; nothing was built or measured.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, List

from . import BUILD, RESULTS, cache_path

ALL = ("calib", "loads", "candidates", "optimise", "sim", "interface", "layout", "report")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _stage_path(name: str, quick: bool):
    d = BUILD / ("quick" if quick else "")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"stage_{name}.json"


def save_stage(name: str, obj: Dict, quick: bool) -> None:
    p = _stage_path(name, quick)
    tmp = str(p) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, default=_default)
    os.replace(tmp, p)


def load_stage(name: str, quick: bool):
    p = _stage_path(name, quick)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def _default(o):
    import numpy as np
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    if hasattr(o, "__dict__"):
        return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
    return str(o)


# ------------------------------------------------------------------------------------------------ stages
def stage_calib(quick: bool) -> Dict:
    from . import actuators as A
    if A.CAL_PATH.exists() and not quick:
        c = A.calibration()
        return {k: c.get(k) for k in ("kappa", "nu", "rel_rms_fit", "rel_rms_holdout", "rel_max_holdout", "n_fit", "n_holdout")}
    r = A.fit_calibration(quick=quick)
    return {k: r.get(k) for k in ("kappa", "nu", "rel_rms_fit", "rel_rms_holdout", "rel_max_holdout", "n_fit", "n_holdout")}


def stage_loads(quick: bool) -> Dict:
    from . import balance as BL
    from . import candidates as CD
    from . import contact as C
    from . import inkforce as IK
    from . import loads as LD
    from . import thermal as TH
    out = {"review_check": {"static_power_W": {f"{t:g}": C.review_static_power(t) for t in (35.0, 50.0, 60.0, 75.0)},
                            "time_to_120C_s": TH.review_check(),
                            "label": "CALC (the review's section 4 statics and single-node screen, reproduced)"},
           "reconciliation": LD.reconcile_c1s(), "catalogue": LD.load_catalogue(),
           "friction_map": C.mu_map_table()}
    d = CD.make("c_counterface", CD.pen24())
    hw = CD.translation_hw(d)
    nib = CD._nib_model(d, hw)
    n = 300 if quick else 3000
    mechs = {"none": BL.NoBalance(), "b_bias (ungated)": BL.BiasSpring(gated="none"), "b_bias (EPM gated)": BL.BiasSpring(gated="epm"),
             "c_counterface imu2": BL.CounterFace(driver="imu2"), "c_counterface slidecam": BL.CounterFace(driver="slidecam"),
             "c_counterface keyed": BL.CounterFace(driver="keyed")}
    out["balance_quality"] = {k: BL.balance_quality(m, nib, n=n) for k, m in mechs.items()}
    out["balance_quality_note"] = ("Translation nib (24 mm default hardware); tilt 35-75 deg, roll uniform, inks oil/gel, "
                                   "papers 0.8-1.3, F_s +-20 %, IMU tilt/roll errors 1/2 deg (1 sigma), keyed grip 15 deg")
    out["inkforce"] = IK.summary()
    out["inkforce"]["sensitivity"] = IK.sensitivity(forces=(0.05, 0.15, 0.69) if quick else (0.05, 0.10, 0.15, 0.30, 0.50, 0.69, 1.00))
    # gimbal counter-face variant (the tilted face for a gimbal nib): its tilt at 50 deg
    cf = BL.CounterFace(nib_kind="gimbal", b_over_L=1.0)
    import math
    nr = cf.face_normal(50 * math.pi / 180, 0.0)
    fr = C.frame(50 * math.pi / 180, 0.0)
    out["gimbal_face_tilt_deg_at_50"] = math.degrees(math.acos(abs(nr @ fr["a"])))
    return out


def stage_candidates(quick: bool) -> Dict:
    from . import candidates as CD
    out = {}
    for gname, grip in (("pen24", CD.pen24()), ("slim14", CD.slim(14e-3))):
        for key in (CD.CANDIDATES if not quick else ("c_counterface", "f_translation", "h_piezo")):
            d = CD.make(key, grip)
            rA = CD.evaluate(d, CD.DUTY_A, detail=not quick)
            rB = CD.evaluate(d, CD.DUTY_B, detail=False, fast=True) if d.family != "piezo" else None
            rA["P_cont_duty_B_W"] = rB["P_cont_W"] if rB else None
            rA["P_35_duty_B_W"] = rB["P_mean_W_by_theta"][35.0] if rB else None
            rA["duty_B_feasible"] = bool(rB and d.travel >= 0.75e-3 and rB["travel_under_load_mm"] >= 0.7)
            if d.family == "translation":
                from . import flexure as FX
                rA["tolerance_mc"] = FX.tolerance_mc(d.wire, d.travel, d.travel + 0.2e-3, rA["hw"]["m_move"],
                                                     n=200 if quick else 2000)
            out[f"{gname}|{key}"] = rA
            log(f"[candidates] {gname} {key}: P_cont {rA['P_cont_W'] * 1e3:.2f} mW (35 deg "
                f"{rA['P_mean_W_by_theta'][35.0] * 1e3:.1f}), travel {rA['travel_under_load_mm']:.2f} mm, mass {rA['mass_g']:.1f} g")
    out["collar"] = CD.collar_numbers()
    return out


def stage_optimise(quick: bool) -> Dict:
    from . import optimise as OP
    r = OP.run(quick=quick, log=log)
    r.pop("method", None)
    # keep the file small: pooled points go to the Pareto figure's CSV; here the runs and fronts
    slim = {"fronts": r["fronts"], "problems": {}, "piezo": {}}
    for pid, pr in r["problems"].items():
        slim["problems"][pid] = {k: v for k, v in pr.items() if k != "points"}
        slim["problems"][pid]["n_points"] = len(pr["points"])
        slim["problems"][pid]["points"] = pr["points"]
    slim["piezo"] = r["piezo"]
    return slim


def stage_sim(quick: bool) -> Dict:
    from . import sim as SM
    return SM.run_all(quick=quick, log=log)


def stage_interface(quick: bool, sim: Dict = None) -> Dict:
    from . import interface as IF
    doc = IF.build_interface(sim_cards=(sim or {}).get("cards"))
    if not quick:
        path = IF.write(doc)
    else:
        path = IF.write(doc, BUILD / "quick" / "nib.yaml")
    return {"path": str(path), "missing_status": IF.leaves_missing_status(doc)}


def stage_layout(quick: bool) -> Dict:
    from . import candidates as CD
    from . import interface as IF
    from . import layout as LY
    from . import write_json
    d, x = IF.recommended_design()
    ev = CD.evaluate(d, detail=False, fast=True)
    lp = LY.layout_parts(d, ev)
    if not quick:
        write_json("layout_parts.json", lp)
    cad = {"skipped": quick}
    if not quick:
        sys.path.insert(0, str(RESULTS.parent.parent / "mechanics" / "cad"))
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("bnib_cad", str(RESULTS.parent.parent / "mechanics" / "cad" / "bnib.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            geo = mod.main([])
            cad = {"ok": True, "fit_checks": geo["fit_checks"], "mass_g": geo["mass_g"]}
        except Exception as ex:
            cad = {"ok": False, "error": repr(ex)}
    return {"fit_checks": lp["meta"]["fit_checks"], "mass_added_g": lp["meta"]["mass_added_g"], "cad": cad,
            "n_components": len(lp["components"])}


def stage_report(quick: bool, S: Dict) -> Dict:
    from . import report as RP
    return RP.write_all(S, quick=quick, log=log)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", default=",".join(ALL))
    ap.add_argument("--force", default="", help="comma-separated stages to recompute even if cached")
    a = ap.parse_args(argv)
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    force = {s.strip() for s in a.force.split(",") if s.strip()}
    q = a.quick
    t0 = time.time()
    S: Dict = {}
    fns = {"calib": stage_calib, "loads": stage_loads, "candidates": stage_candidates, "optimise": stage_optimise,
           "sim": stage_sim}
    for name in ALL:
        cached = load_stage(name, q) if name not in force else None
        if name in ("interface", "layout", "report"):
            continue
        if name in stages and cached is None:
            log(f"stage {name} ...")
            S[name] = fns[name](q)
            save_stage(name, S[name], q)
            log(f"stage {name} done ({time.time() - t0:.0f} s)")
        elif cached is not None:
            S[name] = cached
    if "interface" in stages:
        S["interface"] = stage_interface(q, S.get("sim"))
        save_stage("interface", S["interface"], q)
    if "layout" in stages:
        S["layout"] = stage_layout(q)
        save_stage("layout", S["layout"], q)
    else:
        S["layout"] = load_stage("layout", q)
    if "report" in stages:
        S["report"] = stage_report(q, S)
    log(f"done in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
