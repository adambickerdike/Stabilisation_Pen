#!/usr/bin/env python3
r"""Study N (Rev J "nose v2"): the full pipeline, stage by stage.

Stages (each caches its JSON in nose2/build/cache/<stage>.json, or <stage>_quick.json with --quick):
  tasks        travel each task needs: tremor, guided shaping, autowrite reach, delayed ink; autowrite kinematics (CALC)
  frontend     the DEC-034 front-end closure at +-3-8 mm and pivots 35-65 mm; check against opt/inertial/front_end (CALC)
  magnetics    magpylib gap-flux grid, the surrogate fit and its check; Rev H recalibration; image convention (CALC)
  optimise     CMA-ES + adjoint L-BFGS over every candidate, travel, mass weight and handle; Pareto fronts;
               gradient check; screening of galvo, piezo, SMA and planar stages (CALC)
  choose       the fixed selection rule (choose.py) -> recommended design; HW1 pens for it and for Rev H (CALC)
  tuning       autowrite settings on tuning writers 100-103 and seeds 300-303 (SIM)
  test         the test grid: writers 0-5, seeds 200-203, no tremor and 0.3/1/2 mm at 4/8/12 Hz (SIM)
  limits       largest letter size and fastest sweep per reach (CALC, planner; test writers)
  sensitivity  one factor at a time on the recommended design (SIM, test writers, seed 200)
  layout       results/nose2/layout.json in the Rev H schema (PROPOSED DESIGN)
  cad          mechanics/cad/nose2.py: STEP, drawing and front-end views (PROPOSED DESIGN)
  figures      results/nose2/fig_*.png with CSV twins
  report       results/nose2/nose2.json (stabpen.provenance)
  evidence     results/nose2/evidence_rows.csv (proposed ledger rows)
Run: python3 nose2/run_study.py [--quick] [--stages a,b] [--sweep-cache FILE]
--quick runs every stage on a tiny subset and writes to nose2/build/quick/ (never to results/nose2/).
One process; about 2-3 h for the full run on one core (the optimisation sweep is about 40 min of it).
Evidence status: CALCULATION and SIMULATION on synthetic writers and synthetic tremor.  Nothing here is a measurement.
"""
from __future__ import annotations

import os as _os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, replace

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nose2 import BUILD_DIR, RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, ensure_paths  # noqa: E402

ensure_paths()
from stabpen import provenance  # noqa: E402

STAGES = ("tasks", "frontend", "magnetics", "optimise", "choose", "tuning", "test", "limits", "sensitivity", "layout", "cad",
          "figures", "report", "evidence")
Q = {"quick": False}


def cache_dir():
    d = BUILD_DIR / ("quick" if Q["quick"] else "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir():
    d = (BUILD_DIR / "quick" / "results") if Q["quick"] else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(stage):
    return cache_dir() / f"{stage}{'_quick' if Q['quick'] else ''}.json"


def save(stage, obj):
    provenance.write_json(str(_path(stage)), tolist(obj))


def load(stage):
    p = _path(stage)
    if not p.exists():
        raise SystemExit(f"stage '{stage}' has no cached result ({p}); run it first")
    with open(p) as f:
        return json.load(f)


def tolist(o):
    if isinstance(o, dict):
        return {str(k): tolist(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tolist(v) for v in o]
    if isinstance(o, np.ndarray):
        return tolist(o.tolist())
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------ tasks
def stage_tasks():
    from nose2 import tasks as T
    t0 = time.time()
    q = Q["quick"]
    tr = T.tremor_peaks(f0s=(4.0, 8.0, 12.0) if q else (4.0, 6.0, 8.0, 10.0, 12.0), seeds=TUNE_SEEDS[:1] if q else TUNE_SEEDS,
                        T=4.0 if q else 12.0)
    log("tremor peaks", tr)
    gd = T.guidance_error(writers=TUNE_WRITERS[:1] if q else TUNE_WRITERS, seeds=TUNE_SEEDS[:1] if q else TUNE_SEEDS)
    log("guidance", gd)
    aw = T.autowrite_reach(writers=TUNE_WRITERS[:2] if q else TUNE_WRITERS, xh=(2.5, 3.0) if q else T.XHEIGHTS_MM,
                           speeds=(1.0,) if q else T.SPEED_FACTORS)
    log("autowrite reach rows", len(aw))
    di = T.delayed_ink(writers=TUNE_WRITERS[:1] if q else TUNE_WRITERS, seeds=TUNE_SEEDS[:1] if q else TUNE_SEEDS[:2],
                       taus=(0.10, 0.20) if q else T.TAUS_S)
    log("delayed ink", {k: v["synthetic_p99_mm"] for k, v in di.items()})
    kin = T.autowrite_kinematics(writers=TUNE_WRITERS[:2] if q else TUNE_WRITERS)
    log("kinematics", kin)
    req = T.requirement_table(tr, gd, aw, di)
    save("tasks", {"tremor": tr, "guidance": gd, "autowrite_reach": aw, "delayed_ink": di, "kinematics": kin, "requirements": req,
                   "label": "CALC on synthetic writers (aiguide) and the project's tremor model; tuning writers 100-103, seeds 300-303",
                   "elapsed_s": time.time() - t0})


# ------------------------------------------------------------------ front end
def stage_frontend():
    from nose2 import frontend as FEN
    t0 = time.time()
    q = Q["quick"]
    rows = FEN.sweep(X_list=(3.0, 6.0) if q else (3.0, 4.0, 5.0, 6.0, 7.0, 8.0), zp_list=(45.0,) if q else (35.0, 45.0, 55.0, 65.0))
    log("frontend rows", len(rows))
    # the vectorised closure against the original (opt/inertial/front_end.check) at the Rev H point and at 6 mm
    from opt.inertial import front_end as FE
    from opt.inertial.revh import RevH
    chk = []
    for X, zp, R in ((3.0, 45.0, 6.75), (6.0, 45.0, 9.0)) if not q else ((3.0, 45.0, 6.75),):
        a = FEN.check(R, FEN.Nose(z_p=zp, travel=X))
        d = replace(RevH(), travel=X * 1e-3, z_p=zp * 1e-3)
        ru = replace(FE.FrontRules(), stop=X + 0.5)
        b = FE.check(R, d, ru, n_theta=9, n_phi=24)
        keys = [k for k in a if k in b and isinstance(a[k], (int, float)) and isinstance(b[k], (int, float))]
        chk.append({"X_mm": X, "z_p_mm": zp, "R_mm": R, "max_abs_diff": max(abs(float(a[k]) - float(b[k])) for k in keys),
                    "compared_keys": keys})
    log("frontend check", [(c["X_mm"], c["max_abs_diff"]) for c in chk])
    lift = {"revH": FEN.refill_follow_lift(6.75)}
    save("frontend", {"rows": rows, "check_vs_original": chk, "refill_follows_lift": lift,
                      "label": "CALC (DEC-034 closure rules, generalised; nose2/frontend.py)", "elapsed_s": time.time() - t0})


# ------------------------------------------------------------------ magnetics
def stage_magnetics():
    from nose2 import designs as DS
    from nose2 import magnetics as MG
    t0 = time.time()
    every = 12 if Q["quick"] else 1
    out = {"image_check": MG.image_check(), "revh": {"as_designed_Br_1.33": DS.revh_as_designed(1.33),
                                                      "as_designed_Br_1.42": DS.revh_as_designed(1.42)}}
    for kind, coef in (("radial", DS.ETA_RADIAL), ("axial", DS.ETA_AXIAL)):
        rows = MG.surrogate_rows(kind, every=every)
        fit = MG.fit_surrogate(kind, rows)
        chk = MG.check_surrogate(kind, rows, coef)
        out[kind] = {"n": int(len(rows)), "refit": fit, "frozen_check": {k: v for k, v in chk.items() if k not in ("eta", "eta_pred")},
                     "parity": {"eta": chk["eta"], "eta_pred": chk["eta_pred"]}, "grid": MG.SURR_GRID[kind]}
        log("magnetics", kind, len(rows), "frozen rel rms", round(chk["rel_rms"], 4), "max", round(chk["rel_max"], 3))
    out["label"] = "CALC (magpylib analytic cuboids, soft iron as mu = inf planes by images; upper bound: no saturation, no finite iron)"
    out["elapsed_s"] = time.time() - t0
    save("magnetics", out)


# ------------------------------------------------------------------ optimise
SWEEP = {"full": {"kinds_seeds": ((("gimbal_sphere", "gimbal_radial", "gimbal_axial", "dual_plane"), (0, 1, 2)),
                                  (("coarse_fine", "xy_wire"), (0,))),
                  "x_mins": (4e-3, 5e-3, 6e-3, 7e-3, 8e-3), "mus": (1.0, 4.0), "bores": ("22", "24"), "iters": 150, "popsize": 16},
         "quick": {"kinds_seeds": ((("gimbal_sphere", "gimbal_radial"), (0,)),), "x_mins": (5e-3, 6e-3), "mus": (4.0,),
                   "bores": ("24",), "iters": 25, "popsize": 8}}


def duty_from_tasks(tk):
    from nose2 import designs as DS
    k = tk["kinematics"]
    return DS.Duty(aw_q_rms=round(k["q_rms_axis_mm"], 2) * 1e-3, aw_a_pk=round(k["a_p999_m_s2"], 1), aw_q_pk=round(k["q_p999_mm"], 1) * 1e-3,
                   aw_ink_share=round(k["ink_share"], 2))


def reevaluate(row, duty):
    """Recompute a sweep row's summary with the current model (fills fields added after a cached sweep)."""
    import torch
    from nose2 import designs as DS
    from nose2 import optimise as OP
    parts = DS.Parts(**row["parts"])
    d = replace(duty, x_min=row.get("x_min_req_mm", row["X_min_mm"]) * 1e-3)
    v = {k: torch.tensor(val, dtype=DS.DT) for k, val in row["vars"].items()}
    with torch.no_grad():
        out = DS.evaluate(row["kind"], v, parts, d)
    s = OP.summary(row["kind"], row["vars"], parts, out)
    s["pen_terms"] = {k: float(t) for k, t in out["pen_terms"].items()}
    for k in ("feasible", "mu_m", "x_min_req_mm", "bore", "seed", "J"):
        if k in row:
            s[k] = row[k]
    s["feasible_reeval"] = float(out["pen"]) < 1e-6
    s["reeval_dP_W"] = s["P_autowrite_W"] - row["P_autowrite_W"]
    return s


def stage_optimise(sweep_cache=None):
    from nose2 import designs as DS
    from nose2 import optimise as OP
    t0 = time.time()
    tk = load("tasks")
    duty = duty_from_tasks(tk)
    cfg = SWEEP["quick" if Q["quick"] else "full"]
    log("duty", asdict(duty))
    if sweep_cache:
        with open(sweep_cache) as f:
            raw = json.load(f)
        src = {"file": os.path.relpath(sweep_cache, ROOT), "duty_used": raw.get("duty"), "note": raw.get("note", "")}
        log("sweep from cache", sweep_cache, len(raw["best"]), "best rows,", len(raw["archive"]), "archive rows")
    else:
        raw = {"best": [], "archive": []}
        for kinds, seeds in cfg["kinds_seeds"]:
            r = OP.sweep(duty, x_mins=cfg["x_mins"], mus=cfg["mus"], bores=cfg["bores"], kinds=kinds, seeds=seeds,
                         iters=cfg["iters"], popsize=cfg["popsize"], progress=lambda *a: log("opt", *a))
            raw["best"] += r["best"]
            raw["archive"] += r["archive"][::2]          # every second feasible evaluation (memory)
        src = {"file": None, "duty_used": asdict(duty)}
    best = [reevaluate(r, duty) for r in raw["best"]]
    dP = max(abs(r["reeval_dP_W"]) for r in best)
    log("re-evaluated best rows; max |dP|", dP)
    # Pareto fronts: per candidate and overall, on (guaranteed travel, Km_tip, added mass, autowrite power)
    fronts = {}
    for kind in sorted({r["kind"] for r in raw["archive"]}):
        rows = [r for r in raw["archive"] if r["kind"] == kind]
        f = OP.pareto(rows)
        f2 = OP.pareto(rows, keys=(("X_min_mm", 1), ("P_autowrite_W", -1)))
        fronts[kind] = {"n_feasible_evaluated": len(rows), "front4": f, "front_travel_power": sorted(f2, key=lambda r: r["X_min_mm"])}
        log("pareto", kind, len(rows), len(f), len(f2))
    allrows = [r for k in fronts for r in fronts[k]["front4"]]
    overall = OP.pareto(allrows)
    raw = None
    gc = OP.grad_check("gimbal_sphere")
    gc_r = OP.grad_check("gimbal_radial")
    worst = max(abs(a - b) / max(abs(b), 1e-12) for a, b in list(gc.values()) + list(gc_r.values()))
    log("grad check worst rel", worst)
    save("optimise", {"duty": asdict(duty), "sweep_config": {k: (v if k != "kinds_seeds" else [[list(a), list(b)] for a, b in v])
                                                              for k, v in cfg.items()},
                      "sweep_source": src, "best": best, "max_reeval_dP_W": dP, "fronts": fronts, "overall_front": overall,
                      "grad_check": {"gimbal_sphere": gc, "gimbal_radial": gc_r, "worst_rel_err": worst},
                      "screening": DS.screening(duty), "label": "CALC (nose2/designs.py models; CMA-ES + L-BFGS adjoint polish)",
                      "elapsed_s": time.time() - t0})


# ------------------------------------------------------------------ choose
def hw1_designs(rec, axial_W):
    """The HW1 pens: the recommended nose with and without its axial DOF, and Rev H (as built into HW1)."""
    from nose2 import autowrite as AW
    des = rec["design"]
    od = rec["handle_od"]
    d1 = AW.from_summary(des, od, key="revJ", axial=True, axial_W=axial_W)
    d0 = AW.from_summary(des, od, key="revJ_noaxial", axial=False)
    return {"revJ": d1, "revJ_noaxial": d0, "revH": AW.revh_design()}


def design_to_dict(d):
    x = asdict(d)
    return x


def design_from_dict(x):
    from nose2 import autowrite as AW
    return AW.NoseDesign(**x)


def stage_choose():
    from nose2 import choose as CH
    t0 = time.time()
    tk = load("tasks")
    op = load("optimise")
    req = CH.required_travel(tk["autowrite_reach"])
    log("required travel", req)
    rec = CH.choose(op["best"], req["x_req_mm"])
    if rec["design"] is None:
        raise SystemExit("no feasible design at any travel: see the search log")
    log("chosen", rec["design"]["kind"], rec["x_chosen_mm"], rec["handle_od"], rec["why"])
    from nose2 import designs as DS
    ax = DS.axial_dof(lifts_per_s=tk["kinematics"]["pen_lifts_per_s"])
    ds = hw1_designs(rec, ax["P_avg_W"])
    cells = CH.best_per_cell(op["best"])
    alt = CH.alternatives(op["best"], req["x_req_mm"])
    log("alternatives", alt)
    save("choose", {"requirement": req, "recommended": rec, "alternatives": alt, "axial_dof": ax,
                    "hw1_designs": {k: design_to_dict(v) for k, v in ds.items()},
                    "cells": cells, "rule": CH.__doc__, "elapsed_s": time.time() - t0})


def designs_from_choose(ch):
    return {k: design_from_dict(v) for k, v in ch["hw1_designs"].items()}


# ------------------------------------------------------------------ tuning
def stage_tuning():
    from nose2 import tuning as TU
    t0 = time.time()
    ds = designs_from_choose(load("choose"))
    res = TU.tune(ds["revJ"], progress=lambda *a: log("tune", *a), quick=Q["quick"])
    res["elapsed_s"] = time.time() - t0
    log("tuned", res["settings"])
    save("tuning", res)


def settings_from_tuning():
    from nose2 import autowrite as AW
    tu = load("tuning")
    return replace(AW.AWSettings(), **tu["settings"])


# ------------------------------------------------------------------ test
def stage_test():
    from nose2 import evaluate as EV
    t0 = time.time()
    ch = load("choose")
    ds = designs_from_choose(ch)
    st = settings_from_tuning()
    lim = limits_quick_revh(ds, st)
    if Q["quick"]:
        designs = {"revJ": ds["revJ"]}
        sizes = {"revJ": [2.5]}
        rows = EV.grid(designs, st, sizes, writers=TEST_WRITERS[:2], seeds=TEST_SEEDS[:1], conds=[(8.0, 0.0), (8.0, 1.0e-3)],
                       progress=lambda *a: log("test", *a))
    else:
        designs = ds
        sizes = {"revJ": [2.5, 3.0], "revJ_noaxial": [2.5], "revH": [lim["revH_h_mm"]]}
        rows = EV.grid(designs, st, sizes, progress=lambda *a: log("test", *a))
    summ = EV.summarise(rows)
    save("test", {"settings": {k: getattr(st, k) for k in ("reach_margin", "obs_hz", "prog_hz", "lead_extra", "speed")},
                  "sizes": sizes, "revH_size_rule": lim, "rows": rows, "summary": summ,
                  "label": "SIM (HW1 via nose2/autowrite.py; test writers 0-5, seeds 200-203; settings frozen by tuning)",
                  "elapsed_s": time.time() - t0})


def limits_quick_revh(ds, st):
    """Rev H's x-height for the test grid: the largest size its plan reach fits for every test writer (CALC)."""
    from nose2 import evaluate as EV
    R = (ds["revH"].q_lim - st.reach_margin) * 1e3
    lim = EV.size_speed_limits({"revH": R}, writers=TEST_WRITERS[:2] if Q["quick"] else TEST_WRITERS,
                               h_grid=(0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5), speed_grid=(1.0,), pp=st.plan)
    h = lim["revH"]["largest_x_height_mm"]
    return {"revH_plan_reach_mm": R, "revH_h_mm": h if h > 0 else 0.75, "limits": lim}


# ------------------------------------------------------------------ limits
def stage_limits():
    from nose2 import evaluate as EV
    t0 = time.time()
    ch = load("choose")
    ds = designs_from_choose(ch)
    st = settings_from_tuning()
    reach = {k: (d.q_lim - st.reach_margin) * 1e3 for k, d in ds.items() if k != "revJ_noaxial"}
    curve = {f"reach_{r:.1f}mm": r for r in ((2.0, 3.0, 4.0, 5.0, 6.0, 7.0) if not Q["quick"] else (2.0, 4.0))}
    writers = TEST_WRITERS[:2] if Q["quick"] else TEST_WRITERS
    h_grid = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
    out = EV.size_speed_limits({**reach, **curve}, writers=writers, h_grid=h_grid, pp=st.plan)
    log("limits", {k: (v["largest_x_height_mm"], v["fastest_speed_factor_at_2.5mm"]) for k, v in out.items()})
    save("limits", {"by_design": {k: out[k] for k in reach}, "curve": {k: out[k] for k in curve}, "writers": list(writers),
                    "label": "CALC (planner feasibility; test writers, seed 200)", "elapsed_s": time.time() - t0})


# ------------------------------------------------------------------ sensitivity
def stage_sensitivity():
    from nose2 import evaluate as EV
    t0 = time.time()
    ds = designs_from_choose(load("choose"))
    st = settings_from_tuning()
    if Q["quick"]:
        rows = EV.sensitivity(ds["revJ"], st, writers=TEST_WRITERS[:1], conds=((8.0, 1.0e-3),))
    else:
        rows = EV.sensitivity(ds["revJ"], st)
    agg = {}
    for r in rows:
        a = agg.setdefault(r["variant"], {"n": 0, "plan_fail": 0, "ink_err_um": [], "letters_read": [], "P_coil_W": [],
                                          "at_travel_limit": [], "words_read_app": []})
        a["n"] += 1
        if not r.get("plan_ok"):
            a["plan_fail"] += 1
            continue
        for k in ("ink_err_um", "letters_read", "P_coil_W", "at_travel_limit", "words_read_app"):
            if r.get(k) is not None:
                a[k].append(r[k])
    for a in agg.values():
        for k in ("ink_err_um", "letters_read", "P_coil_W", "at_travel_limit", "words_read_app"):
            a[k] = float(np.mean(a[k])) if a[k] else None
    log("sensitivity", {k: (v["ink_err_um"], v["letters_read"]) for k, v in agg.items()})
    save("sensitivity", {"rows": rows, "summary": agg, "label": "SIM (HW1; test writers, seed 200; one factor at a time)",
                         "elapsed_s": time.time() - t0})


# ------------------------------------------------------------------ layout and CAD
def stage_layout():
    from nose2 import layout as LY
    ch = load("choose")
    rec = ch["recommended"]
    geo = LY.layout(rec["design"], handle_od=rec["handle_od"], axial=True)
    geo = {"meta": provenance.metadata("PROPOSED DESIGN (dimensioned concept; CALC masses; ASSUMPTION dimensions) - Rev J nose v2 "
                                       f"({rec['design']['kind']}), study N",
                                       extra={"script": "nose2/layout.py (also mechanics/cad/nose2.py)", "doc": "docs/nose_v2.md"}),
           **geo}
    provenance.write_json(str(out_dir() / "layout.json"), tolist(geo))
    log("layout", geo["fit_checks"], geo["mass_g"])
    save("layout", {"fit_checks": geo["fit_checks"], "mass_g": geo["mass_g"], "file": str(out_dir() / "layout.json")})


def stage_cad():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nose2_cad", os.path.join(ROOT, "mechanics", "cad", "nose2.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ImportError as e:                 # CadQuery missing: the drawing needs it too
        log("CAD skipped:", e)
        save("cad", {"skipped": str(e)})
        return
    design_json = out_dir() / "_design_for_cad.json"
    ch = load("choose")
    with open(design_json, "w") as f:
        json.dump({"recommended": {"design": ch["recommended"]["design"], "handle_od": ch["recommended"]["handle_od"]}}, f)
    args = ["--design", str(design_json), "--out", str(out_dir())] + (["--no-step"] if Q["quick"] else [])
    geo = mod.main(args)
    os.remove(design_json)
    save("cad", {"fit_checks": geo["fit_checks"], "mass_g": geo["mass_g"]})


# ------------------------------------------------------------------ figures, report, evidence
def stage_figures():
    from nose2 import figures as FG
    data = {s: load(s) for s in ("tasks", "magnetics", "optimise", "choose", "tuning", "test", "limits")}
    files = FG.all_figures(data, out_dir(), quick=Q["quick"])
    log("figures", files)
    save("figures", {"files": files})


def stage_report():
    from nose2 import report as RP
    data = {s: load(s) for s in ("tasks", "frontend", "magnetics", "optimise", "choose", "tuning", "test", "limits", "sensitivity")}
    for s in ("layout", "cad", "figures"):
        try:
            data[s] = load(s)
        except SystemExit:
            data[s] = None
    doc = RP.build(data, quick=Q["quick"])
    provenance.write_json(str(out_dir() / "nose2.json"), tolist(doc))
    log("report written", out_dir() / "nose2.json")


def stage_evidence():
    from nose2 import evidence as EVD
    from nose2 import report as RP
    with open(out_dir() / "nose2.json") as f:
        doc = json.load(f)
    n = EVD.write(str(out_dir() / "evidence_rows.csv"), RP.evidence_numbers(doc))
    log("evidence rows", n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--sweep-cache", default=None, help="JSON of an optimise.sweep run with the same settings (best + archive)")
    a = ap.parse_args(argv)
    Q["quick"] = a.quick
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    for s in stages:
        if s not in STAGES:
            raise SystemExit(f"unknown stage {s}; stages: {', '.join(STAGES)}")
    for s in STAGES:
        if s not in stages:
            continue
        t0 = time.time()
        log(f"== stage {s}{' (quick)' if Q['quick'] else ''}")
        if s == "optimise":
            stage_optimise(a.sweep_cache)
        else:
            globals()[f"stage_{s}"]()
        log(f"== stage {s} done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
