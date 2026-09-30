"""Study N end to end: reconciliation, optimisation, candidates, levers, budgets, figures, evidence rows.

    python3 -m nibopt.run            # full study into results/nibopt/ (about 45-60 min on two processes)
    python3 -m nibopt.run --quick    # coarse diagnostic into nibopt/build/quick/ (about 1-2 min, one process)
    python3 -m nibopt.run --reuse    # reuse the optimisation archives in nibopt/build/ (minutes)
    python3 mechanics/cad/nibopt.py  # then the CAD of the balanced candidate

At most two worker processes (--procs, default 2); NUMBA_NUM_THREADS and OMP_NUM_THREADS are 1 (set in nibopt/__init__).
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import time
from dataclasses import replace
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import BUILD, DOC, EVIDENCE, RESULTS, VERSION, own_digests, read_only_digests
from . import budgets as BU
from . import candidates as CA
from . import duty as DU
from . import evaluate as E
from . import evidence as EV
from . import figures as FG
from . import levers as LV
from . import optimise as O
from . import params as P
from . import pen as PN
from . import reconcile as RC
from . import suspension as SU
from .design import reconciliation_designs


def _default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _clean(o):
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, (np.floating,)):
        return _clean(float(o))
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def provenance(args, extra=None) -> Dict:
    from stabpen import provenance as PV
    md = PV.metadata(EVIDENCE, seeds={"nsga_main": 7, "nsga_reach2": 11, "nsga_reach15": 13, "refine": 3,
                                      "severe_process": 11, "K_residual": 5},
                     extra={"package": "nibopt", "version": VERSION, "script": "nibopt/run.py",
                            "doc": str(DOC.relative_to(DOC.parents[1])), "quick": bool(args.quick),
                            "reuse": bool(args.reuse), "procs": args.procs,
                            "read_only_inputs_sha256_16": read_only_digests(), "nibopt_sources_sha256_16": own_digests(),
                            "parameters": "every input with its label and source: results/nibopt/nibopt.json -> inputs "
                                          "(nibopt/params.py)"})
    try:
        import magpylib, matplotlib, numba
        md.update({"magpylib": magpylib.__version__, "matplotlib": matplotlib.__version__, "numba": numba.__version__})
    except Exception:
        pass
    if extra:
        md.update(extra)
    return md


def write(path: Path, obj: Dict, args, extra=None):
    obj = dict(obj)
    obj = {"stabpen.provenance": provenance(args, extra), **obj}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(obj), indent=1, default=_default, allow_nan=False) + "\n")
    return str(path)


def _pool(args):
    if args.procs <= 1:
        return None
    return mp.get_context("fork").Pool(args.procs)


def run_nsga(name: str, args, pool, **kw) -> Dict:
    cache = BUILD / f"nsga_{name}.json"
    if args.reuse and cache.exists():
        print(f"[optimise] reuse {cache}", flush=True)
        return json.loads(cache.read_text())
    res = O.nsga2(pool=pool, log=lambda m: print(f"[{name}] {m}", flush=True), **kw)
    out = {"archive": res["archive"], "pop": res["pop"], "seconds": res["seconds"], "pop_size": res["pop_size"],
           "gens": res["gens"], "seed": res["seed"]}
    if not args.quick:
        cache.write_text(json.dumps(out, default=_default))
    return out


def front_record(p: Dict) -> Dict:
    g = O.decode(np.array(p["x"]))
    keep = ["reach_mm", "od_mm", "w_frac", "t_m_mm", "grade", "layout", "t_m2_frac", "iron", "t_cu_mm", "order", "fill",
            "b_mm", "R_coil", "wireset", "L_w_mm", "K_a", "preload_N", "ball_d_mm", "carrier", "flange", "flange_t_mm",
            "flange_frac", "race", "board"]
    return {"reach_mm": -p["F"][0], "screen_W": p["F"][1], "typical_W": p["F"][2], "od_mm": p["F"][3],
            "length_mm": p["F"][4], "m_move_g": p.get("m_move_g"), "sv_min_N_sqrtW": p.get("sv_min"),
            "skin_C": p.get("skin_C"), "severe_P35_W": p.get("severe_P35_W"), "goodman": p.get("goodman"),
            "genes": {k: g[k] for k in keep}, "x": p["x"]}


def _violations_by_od(arch: List[Dict]) -> Dict:
    """Which constraints fail, by body-diameter band, among the evaluated +-2 mm designs (CALC)."""
    from collections import Counter
    out = {}
    for lo, hi in ((22.0, 24.0), (24.0, 26.0), (26.0, 27.0), (27.0, 28.0), (28.0, 29.0), (29.0, 30.0), (30.0, 32.0),
                   (32.0, 34.0 + 1e-9)):
        b = [p for p in arch if p.get("ok") and lo <= p["F"][3] < hi]
        viol = Counter()
        for p in b:
            if p["V"] > 0:
                for k, v in p.get("constraints", {}).items():
                    if v < 0:
                        viol[k] += 1
        best = min(b, key=lambda p: p["V"]) if b else None
        out[f"{lo:g}-{hi:g}"] = {"n": len(b), "n_feasible": sum(1 for p in b if p["V"] <= 0),
                                 "failing": dict(viol.most_common(8)),
                                 "closest": ({k: v for k, v in best["constraints"].items() if v < 0}
                                             if best is not None and best["V"] > 0 else None),
                                 "closest_V": (best["V"] if best is not None else None)}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--figures-only", action="store_true", help="rebuild the figures from the saved JSON files")
    args = ap.parse_args(argv)
    if args.figures_only:
        return figures_only(args)
    args.procs = max(1, min(2, args.procs if not args.quick else 1))
    out = (BUILD / "quick") if args.quick else RESULTS
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    times = {}
    files = []
    PN.head_table()
    # ---------------------------------------------------------------- task 1: reconciliation
    t = time.time()
    rec = RC.run(quick=args.quick)
    times["reconcile_s"] = time.time() - t
    files.append(write(out / "reconciliation.json", rec, args))
    print(f"[reconcile] {times['reconcile_s']:.0f} s", flush=True)
    # ---------------------------------------------------------------- task 2: optimisation
    pool = _pool(args)
    t = time.time()
    try:
        if args.quick:
            main_run = run_nsga("quick", args, pool, pop_size=16, gens=3, seed=7)
            r2 = run_nsga("quick_r2", args, pool, pop_size=12, gens=2, seed=11, bounds={"reach_mm": (2.0, 2.0),
                                                                                         "od_mm": (22.0, 34.0)},
                          objectives=(3, 2))
            r15 = run_nsga("quick_r15", args, pool, pop_size=12, gens=2, seed=13, bounds={"reach_mm": (1.5, 1.5),
                                                                                           "od_mm": (20.0, 24.0)},
                           objectives=(2, 1))
            r2s = run_nsga("quick_r2s", args, pool, pop_size=12, gens=2, seed=17, bounds={"reach_mm": (2.0, 2.0),
                                                                                           "od_mm": (24.0, 29.8)},
                           objectives=(3, 2))
        else:
            main_run = run_nsga("full", args, pool, pop_size=96, gens=80, seed=7)
            r2 = run_nsga("reach2", args, pool, pop_size=48, gens=40, seed=11,
                          bounds={"reach_mm": (2.0, 2.0), "od_mm": (22.0, 34.0)}, objectives=(3, 2))
            r15 = run_nsga("reach15", args, pool, pop_size=48, gens=40, seed=13,
                           bounds={"reach_mm": (1.5, 1.5), "od_mm": (20.0, 24.0)}, objectives=(2, 1))
            # the smallest body for +-2 mm: the first 'reach2' run left 24-29.8 mm thinly sampled
            r2s = run_nsga("reach2_small", args, pool, pop_size=48, gens=30, seed=17,
                           bounds={"reach_mm": (2.0, 2.0), "od_mm": (24.0, 29.8)}, objectives=(3, 2))
        times["optimise_s"] = time.time() - t
        a2 = r2["archive"] + r2s["archive"]
        pooled = main_run["archive"] + a2 + r15["archive"]
        front = O.pareto(main_run["archive"])
        # ------------------------------------------------------------ candidates
        t = time.time()
        sel = CA.select(pooled)
        refined = {}
        for name, p in sel.items():
            if args.quick:
                refined[name] = {"best": p, "history": []}
            else:
                i = O.NAMES.index("fill")
                fix = {"fill": 0.5}
                refined[name] = CA.refine(p, iters=30, lam=6, seed=3, pool=pool, fix=fix,
                                          length_max=CA.length_cap_of(name))
        times["refine_s"] = time.time() - t
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    t = time.time()
    cand_out = {}
    designs = {}
    for name, r in refined.items():
        d, _ = O.build(np.array(r["best"]["x"]), name=name)
        designs[name] = d
        fm = E.force_map(d, fine=not args.quick, n_ang=16 if not args.quick else 8)
        ev = E.evaluate(d, fine=not args.quick, full=True, fm=fm)
        cand_out[name] = {"name": name, "design": d.summary(), "evaluation": ev,
                          "head_fit": PN.head_fit(d.reach_mm, d.od_mm), "reach_mm": d.reach_mm,
                          "typical_W": ev["dutyA"]["worst07"]["mean"], "screen_W": ev["screen"]["worst07"],
                          "refinement": r["history"], "selected_from": front_record(sel[name]),
                          "length_cap_mm": CA.length_cap_of(name),
                          "length_cap_met": bool(d.length_mm() <= CA.length_cap_of(name) + 1e-9),
                          "genes": O.decode(np.array(r["best"]["x"]))}
    times["candidates_s"] = time.time() - t
    # targeted questions
    def best_of(arch, key):
        f = CA.feasible(arch)
        return front_record(min(f, key=key)) if f else None
    inf15 = [p for p in r15["archive"] if p.get("ok") and p["V"] > 0]
    q = {"reach15_od_le_24": {"n_evaluated": len(r15["archive"]), "n_feasible": len(CA.feasible(r15["archive"])),
                              "best_typical": best_of(r15["archive"], lambda p: p["F"][2]),
                              "closest_infeasible": front_record(min(inf15, key=lambda p: p["V"])) if inf15 else None,
                              "closest_infeasible_violations": ({k: v for k, v in min(inf15, key=lambda p: p["V"])
                                                                ["constraints"].items() if v < 0} if inf15 else None)},
         "reach2": {"n_evaluated": len(a2), "n_feasible": len(CA.feasible(a2)),
                    "n_evaluated_24_29.8": len(r2s["archive"]), "n_feasible_24_29.8": len(CA.feasible(r2s["archive"])),
                    "smallest_od": best_of(a2, lambda p: (p["F"][3], p["F"][2])),
                    "lowest_typical": best_of(a2, lambda p: p["F"][2]),
                    "violations_below_smallest_od": _violations_by_od(a2),
                    "front_od_vs_typical": [front_record(p) for p in O.pareto(a2, obj=(3, 2))]},
         "reach_per_watt": CA.reach_per_watt(pooled), "max_reach_by_od": CA.max_reach_by_od(pooled)}
    par = {"n_evaluated": {"main": len(main_run["archive"]), "reach2": len(r2["archive"]),
                           "reach2_small": len(r2s["archive"]), "reach15": len(r15["archive"])},
           "n_feasible": {"main": len(CA.feasible(main_run["archive"])), "reach2": len(CA.feasible(r2["archive"])),
                          "reach2_small": len(CA.feasible(r2s["archive"])), "reach15": len(CA.feasible(r15["archive"]))},
           "settings": {"main": {"pop": main_run["pop_size"], "gens": main_run["gens"], "seed": main_run["seed"],
                                 "seconds": main_run["seconds"]},
                        "reach2": {"pop": r2["pop_size"], "gens": r2["gens"], "seed": r2["seed"], "seconds": r2["seconds"]},
                        "reach2_small": {"pop": r2s["pop_size"], "gens": r2s["gens"], "seed": r2s["seed"],
                                         "seconds": r2s["seconds"]},
                        "reach15": {"pop": r15["pop_size"], "gens": r15["gens"], "seed": r15["seed"],
                                    "seconds": r15["seconds"]}},
           "genes": [{"name": n, "lo": float(lo), "hi": float(hi), "categories": O.CAT.get(n)} for n, lo, hi in O.GENES],
           "objectives": ["-usable radius (mm)", "worst-case copper loss (W): the pass's screen, matched loads, weakest "
                          "point x 0.7, coil at its sustained temperature", "typical copper loss (W): duty A, mean 35-75 "
                          "deg, weakest point x 0.7", "body OD (mm)", "length (mm)"],
           "constraints": list(O.SCALES), "front": [front_record(p) for p in front], "targeted": q,
           "label": "CALCULATION (NSGA-II with Deb's constraint rules; every evaluated point kept; the front is the "
                    "non-dominated feasible set of the main run)"}
    files.append(write(out / "pareto.json", par, args))
    cands = {"candidates": cand_out, "selection_rules": CA.__doc__, "label": "PROPOSED DESIGN; numbers CALCULATION"}
    files.append(write(out / "candidates.json", cands, args))
    # ---------------------------------------------------------------- levers and budgets
    t = time.time()
    lev = {}
    focus = "balanced" if "balanced" in designs else next(iter(designs))
    lev[focus] = LV.study(designs[focus])
    files.append(write(out / "levers.json", {"studies": lev}, args))
    times["levers_s"] = time.time() - t
    bud = {}
    Kd = reconciliation_designs()["K_B1"]
    bud["K_B1 (matched)"] = BU.pen_budget(Kd, rec["table"]["K_B1"])
    for name, d in designs.items():
        bud[name] = BU.pen_budget(d, cand_out[name]["evaluation"])
    files.append(write(out / "budgets.json", {"budgets": bud, "K_published": rec["K_published"]}, args))
    # ---------------------------------------------------------------- figures and evidence
    figs = []
    figs += FG.reconciliation(rec["table"], out / "fig_reconciliation.png")
    figs += FG.waterfall(rec["waterfall_K"]["steps"], "P_mW", "mW", "Duty A on study K's B1: study K's number to the "
                         "matched model, one change per step (CALCULATION)", out / "fig_waterfall_K.png")
    figs += FG.waterfall(rec["waterfall_pass"]["P_150_24"]["steps"], "P_W", "W", "The pass's 1.5 mm nib, its screen: "
                         "its number to the matched loads, one change per step (CALCULATION)",
                         out / "fig_waterfall_pass.png")
    cmarks = {n: {"reach_mm": c["reach_mm"], "screen_W": c["screen_W"], "typical_W": c["typical_W"]}
              for n, c in cand_out.items()}
    figs += FG.pareto(main_run["archive"], front, cmarks, out / "fig_pareto.png")
    figs += FG.levers(lev[focus], out / "fig_levers.png")
    figs += FG.battery({n: b for n, b in bud.items()}, out / "fig_battery.png")
    ev_path = EV.write(out / "evidence_rows.csv")
    chk = EV.check(ev_path)
    times["total_s"] = time.time() - t0
    summary = {
        "answers_inputs": {
            "reach15_od_le_24": q["reach15_od_le_24"], "reach2": {k: v for k, v in q["reach2"].items()
                                                                   if k != "front_od_vs_typical"},
            "reach_per_watt": q["reach_per_watt"], "levers_ranked": lev[focus]["ranked_by_typical"],
            "max_reach_by_od": q["max_reach_by_od"]},
        "reconciliation_headline": {n: {"typical_worst07_W": t["dutyA"]["worst07"]["mean"],
                                        "typical_centre10_W": t["dutyA"]["centre10"]["mean"],
                                        "worst_typical_worst07_W": t["dutyA"]["worst07"]["worst"],
                                        "severe_P35_worst07_W": t["severe"]["worst07"]["P35_W"],
                                        "screen_worst07_W": t["screen"]["worst07"], "screen_map07_W": t["screen"]["map07"],
                                        "skin_severe_worst07_C": t["severe"]["worst07"]["skin"]["max_shell_C"],
                                        "hours_steady_1mm_conservative": t["battery"]["conservative"]["steady_1mm"]["hours"],
                                        "feasible": t["constraints"]["feasible"]} for n, t in rec["table"].items()},
        "candidates_headline": {n: {"reach_mm": c["reach_mm"], "od_mm": c["design"]["od_mm"],
                                    "length_mm": c["design"]["length_mm"], "m_move_g": c["design"]["m_move_g"],
                                    "typical_W": c["typical_W"], "screen_W": c["screen_W"],
                                    "feasible": c["evaluation"]["constraints"]["feasible"]} for n, c in cand_out.items()},
        "evidence_rows_check": chk, "figures": figs, "files": files + [str(ev_path)], "times_s": times,
        "inputs": P.all_tables(), "screen_topologies": rec["screen_topologies"],
        "label": "CALCULATION on PROPOSED DESIGNS; nothing built or measured"}
    write(out / "nibopt.json", summary, args, extra={"times_s": times})
    print(json.dumps(_clean({"times_s": times, "candidates": summary["candidates_headline"]}), indent=1, default=_default))
    return 0


def figures_only(args) -> int:
    out = (BUILD / "quick") if args.quick else RESULTS
    rec = json.loads((out / "reconciliation.json").read_text())
    par = json.loads((out / "pareto.json").read_text())
    cand = json.loads((out / "candidates.json").read_text())["candidates"]
    lev = json.loads((out / "levers.json").read_text())["studies"]
    bud = json.loads((out / "budgets.json").read_text())["budgets"]
    cache = BUILD / ("nsga_quick.json" if args.quick else "nsga_full.json")
    arch = json.loads(cache.read_text())["archive"] if cache.exists() else []
    front = O.pareto(arch) if arch else [{"F": [-p["reach_mm"], p["screen_W"], p["typical_W"], p["od_mm"], p["length_mm"]],
                                          **p} for p in par["front"]]
    figs = []
    figs += FG.reconciliation(rec["table"], out / "fig_reconciliation.png")
    figs += FG.waterfall(rec["waterfall_K"]["steps"], "P_mW", "mW", "Duty A on study K's B1: study K's number to the "
                         "matched model, one change per step (CALCULATION)", out / "fig_waterfall_K.png")
    figs += FG.waterfall(rec["waterfall_pass"]["P_150_24"]["steps"], "P_W", "W", "The pass's 1.5 mm nib, its screen: "
                         "its number to the matched loads, one change per step (CALCULATION)",
                         out / "fig_waterfall_pass.png")
    cmarks = {n: {"reach_mm": c["reach_mm"], "screen_W": c["screen_W"], "typical_W": c["typical_W"]} for n, c in cand.items()}
    figs += FG.pareto(arch, front, cmarks, out / "fig_pareto.png")
    for name, st in lev.items():
        figs += FG.levers(st, out / "fig_levers.png")
    figs += FG.battery(bud, out / "fig_battery.png")
    print("\n".join(figs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
