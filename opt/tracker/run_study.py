#!/usr/bin/env python3
"""Tremor-tracker optimisation study: python3 -m opt.tracker.run_study [--stages ...] [--workers 2].

Stages (each stores its result in opt/tracker/build/stage_<name>.json; `report` assembles results/opt/tracker.json):
  check     torch AKF vs numba AKF agreement; numba adjoint vs PyTorch autograd; finite differences
  gradscan  the objective along core parameters by both implementations (jumps of the frequency tracker), tiny-step
            finite differences on single recordings
  sweep     the lambda_fc chains (python3 -m opt.tracker.sweep; skipped when the runs exist)
  replicate the random search's own objectives (fusion.tune.proxy / proxy_robust) re-optimised by the adjoint
  learned   the GRU with the tremor-band target and the AKF + learned authority gate (trained if missing)
  select    closed-loop validation of every candidate (sweep points, replications, learned models) on tuning seeds
            5000-5003 (P1 grid, 60 conditions) and the aiguide tuning writers 100-105; the pre-declared rule picks the
            tracker to ship
  personal  adjoint personalisation: prior weight chosen on tuning seeds, then test seeds 200-203 at 0.3 mm
  personal_fc  the same with a false-correction term on other writers' tremor-free training writing
  test      the P1 test grid (seeds 200-203, 4-12 Hz x 0.1/0.3/0.5 mm) and the aiguide test writers 0-5 x 4-10 Hz
  budget    MCU cost (CALCULATION)
  viz       results/opt/viz_tracker.json (seed 200, 10 Hz, 0.3 mm)
  report    results/opt/tracker.json, figures results/opt/fig_tr_*.png, ledger rows
Evidence status: SIMULATION (and CALCULATION for the budget); nothing measured.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import time
from typing import Dict, List

import numpy as np

import opt.tracker as OT
from opt.tracker import BUILD, RESULTS, MODEL_DIR, EVIDENCE_SIM, EVIDENCE_CALC

from fusion import harness as H
from fusion import run_study as FRS

SK_1K = {"page": "1k", "comp": "gyro"}
RUNS = os.path.join(BUILD, "runs")


# ------------------------------------------------------------------ helpers
def _r(x):
    if isinstance(x, float):
        if not math.isfinite(x):
            return None
        return float(f"{x:.6g}") if x != 0.0 else 0.0
    if isinstance(x, dict):
        return {str(k): _r(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r(v) for v in x]
    if isinstance(x, np.floating):
        return _r(float(x))
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return _r(x.tolist())
    return x


def stage_path(name):
    return os.path.join(BUILD, f"stage_{name}.json")


def save_stage(name, obj):
    os.makedirs(BUILD, exist_ok=True)
    with open(stage_path(name) + ".tmp", "w") as f:
        json.dump(_r(obj), f, indent=1)
    os.replace(stage_path(name) + ".tmp", stage_path(name))


def load_stage(name):
    p = stage_path(name)
    return json.load(open(p)) if os.path.exists(p) else None


def sim_digest() -> Dict:
    """Digest of the simulator and fusion sources the numbers depend on (another study edits sim/pencil)."""
    out = {}
    for pat in ("sim/pencil/*.py", "fusion/*.py", "config/*.yaml"):
        h = hashlib.sha256()
        for p in sorted(glob.glob(os.path.join(OT.ROOT, pat))):
            h.update(open(p, "rb").read())
        out[pat] = h.hexdigest()[:16]
    return out


def meta(status, seeds, extra=None):
    m = FRS._meta(status, seeds, dict({"script": "opt/tracker/run_study.py", "source_digest": sim_digest()}, **(extra or {})))
    return m


def previous_sets() -> Dict[str, Dict]:
    T = FRS.tuned()
    return {"akf_grid": T["akf_1k"]["params"], "akf_robust": T["akf_robust_1k"]["params"]}


# ------------------------------------------------------------------ check
def stage_check(workers: int):
    import torch
    from opt.tracker import adjoint as AD, data as DA, gradcheck as GC, schedule as SCH, torch_akf as TA
    from fusion import data as FD, estimators as ES, sensors as S
    torch.set_num_threads(1)
    AD.set_threads(2)
    prev = previous_sets()
    T = FRS.tuned()
    out = {"agreement": {}, "gradient_check": {}}
    # 1) agreement on the tuning conditions (seeds 5000-5001, 3 frequencies, 0.3 mm), both implementations
    for key, p, page in (("akf_grid", prev["akf_grid"], "1k"), ("akf_robust", prev["akf_robust"], "1k"),
                         ("akf_120", T["akf_120"]["params"], "120")):
        sts, refs = [], []
        for s in (5000, 5001):
            for f0 in (4.0, 8.0, 12.0):
                r1, _ = FD.test_pair_records(s, f0, 0.3e-3)
                st = S.make_streams(r1, S.config(page=page, comp="gyro"), H.sensor_seed(s, f0, 0.3e-3, 3))
                sts.append(st)
                refs.append(ES.akf(st, p))
        t0 = time.time()
        out_t, parts = TA.run_numba_equivalent(sts, p)
        t_torch = time.time() - t0
        sch = [SCH.build(st) for st in sts]
        t0 = time.time()
        with torch.no_grad():
            out_a = AD.forward(AD.Packed(sch), DA.light_events(sch), TA.numba_to_values(p), TA.static_of(p))
        t_adj = time.time() - t0
        rel_t = [float(np.sqrt(np.mean((out_t[b].numpy() - refs[b][0]) ** 2)) / np.sqrt(np.mean(refs[b][0] ** 2))) for b in range(len(sts))]
        rel_a = [float(np.sqrt(np.mean((out_a[b].numpy() - refs[b][0]) ** 2)) / np.sqrt(np.mean(refs[b][0] ** 2))) for b in range(len(sts))]
        out["agreement"][key] = {"page": page, "n_recordings": len(sts), "torch_rel_rms_max": max(rel_t),
                                 "adjoint_core_rel_rms_max": max(rel_a),
                                 "f_est_max_abs_diff_hz": float(max(np.max(np.abs(parts["f_est"][b].numpy() - refs[b][1]["f_est"])) for b in range(len(sts)))),
                                 "torch_time_s": t_torch, "adjoint_time_s": t_adj,
                                 "conditions": "seeds 5000-5001 x 4/8/12 Hz x 0.3 mm (tuning seeds), 5 s each"}
    # 2) gradients: adjoint vs autograd (all 23 parameters) and finite differences
    items = DA.val_items()[:8]
    rs = DA.build_set(items, keep_streams=True)
    p = prev["akf_grid"]
    static = TA.static_of(p)
    start = TA.trainable_start(p)
    out["gradient_check"]["adjoint_vs_autograd"] = GC.adjoint_vs_autograd(rs, start, static, beta=("leaky", 0.1), n_ticks=1600)
    rs2 = DA.build_set(items)
    out["gradient_check"]["finite_differences_leaky_gates"] = GC.finite_differences(rs2, start, static, beta=("leaky", 0.1))
    out["gradient_check"]["finite_differences_exact_gates"] = GC.finite_differences(rs2, start, static, beta=None)
    out["meta"] = meta(EVIDENCE_SIM, {"agreement": "tuning seeds 5000-5001", "gradients": "validation pairs 9000-9003 (fusion val specs)"})
    save_stage("check", out)
    return out


def _jumps(deltas, J, slope):
    """Steps of a scanned objective that a smooth piece with the local slope does not explain."""
    d = np.diff(np.asarray(deltas)); dj = np.diff(np.asarray(J))
    resid = dj - slope * d
    return {"max_abs_step_residual": float(np.max(np.abs(resid))), "n_steps_residual_gt_1e-4": int(np.sum(np.abs(resid) > 1e-4)),
            "n_steps": int(len(d))}


def small_step_summary(ss: List[Dict], h: float) -> Dict:
    """Relative errors of tiny-step differences; pairs where both the adjoint and the difference are below 1e-10
    (a parameter with no effect on that recording, e.g. f_min never reached) are counted apart."""
    rel = [r["rel_err"] for r in ss]
    nz = [r["rel_err"] for r in ss if max(abs(r["adjoint"]), abs(r["fd"])) > 1e-10]
    return {"h": h, "rows": ss, "median_rel_err": float(np.median(rel)), "max_rel_err": float(np.max(rel)),
            "n_rel_err_gt_1e-3": int(np.sum(np.array(rel) > 1e-3)), "n": len(rel),
            "n_both_zero": len(rel) - len(nz), "max_rel_err_nonzero": float(np.max(nz)) if nz else None,
            "median_rel_err_nonzero": float(np.median(nz)) if nz else None}


def stage_gradscan(workers: int):
    """Why central finite differences of the core parameters (q_t, r_a, tau, tau_w, f_min) disagree with the adjoint
    in stage check: the objective along one parameter by both implementations (opt.tracker.adjoint + torch output
    stage, and fusion.estimators.akf), on the same 8 validation recordings and start point as stage check; and
    tiny-step (1e-7) central differences on single recordings, which stay inside one smooth piece unless a discrete
    event of the frequency tracker sits within the step."""
    import torch
    from opt.tracker import adjoint as AD, data as DA, gradcheck as GC, torch_akf as TA
    torch.set_num_threads(1)
    AD.set_threads(2)
    p = previous_sets()["akf_grid"]
    static = TA.static_of(p)
    start = TA.trainable_start(p)
    items = DA.val_items()[:8]
    deltas = np.round(np.linspace(-2e-3, 2e-3, 41), 12)
    out = {"start": "akf_grid (random-search grid-tuned set), exact gates", "recordings": "fusion val specs 0-7 (as stage check)",
           "scan": [], "note": "theta = log of the parameter (or its linear value for signed ones), as in training"}
    t0 = time.time()
    for key in ("qt", "tau_decay", "g"):
        s = GC.scan(items, start, static, key, deltas)
        s["jumps_adjoint_path"] = _jumps(deltas, s["J_adjoint_path"], s["adjoint_slope_at_0"])
        out["scan"].append(s)
        print(f"[gradscan] {key}: paths differ by {s['max_abs_diff_paths']:.2e}, largest unexplained step "
              f"{s['jumps_adjoint_path']['max_abs_step_residual']:.2e} ({time.time() - t0:.0f} s)", flush=True)
    ss = GC.small_step(items[:4], start, static, keys=GC.CORE_KEYS + ("g", "lp_hz"), h=1e-7)
    out["small_step"] = small_step_summary(ss, 1e-7)
    print(f"[gradscan] small step: median rel err {out['small_step']['median_rel_err']:.2e}, max {out['small_step']['max_rel_err']:.2e} "
          f"({time.time() - t0:.0f} s)", flush=True)
    out["meta"] = meta(EVIDENCE_SIM, {"gradients": "fusion val specs 0-7"})
    save_stage("gradscan", out)
    return out


# ------------------------------------------------------------------ sweep
def sweep_points() -> List[Dict]:
    """Pareto points: the LAST iterate of each (chain, lambda_fc) run, i.e. the lambda objective's optimum within the
    iteration budget (each run starts from the previous point's validation-best iterate), plus each chain's overall
    validation-best iterate (kind "valbest").  The closed-loop stage on tuning data chooses among all of them."""
    from opt.tracker import torch_akf as TA
    pts, best = [], {}
    for p in sorted(glob.glob(os.path.join(RUNS, "sweep_*.json"))):
        r = json.load(open(p))
        last_val = [h["val"] for h in r["history"] if "val" in h and h["iter"] == r["cfg"]["iters"]]
        hist = [{"iter": h["iter"], "J_train": h["train"]["J"]} if "train" in h else {"iter": h["iter"], "J_val": h["val"]["J_mean"]}
                for h in r["history"]]
        pts.append({"file": os.path.basename(p), "chain": r["chain"], "lam_fc": r["lam_fc"], "kind": "last",
                    "harm": r["static"]["harm"], "iters": r["cfg"]["iters"], "val": last_val[0] if last_val else None,
                    "params": TA.to_numba(r["last_vals"], r["static"]), "elapsed_s": r["elapsed_s"], "history": hist,
                    "best_iter": r["best"]["iter"]})
        c = r["chain"]
        if c not in best or r["best"]["val"]["J_mean"] < best[c]["val"]["J_mean"]:
            best[c] = {"file": os.path.basename(p), "chain": c, "lam_fc": r["lam_fc"], "kind": "valbest", "harm": r["static"]["harm"],
                       "iters": r["cfg"]["iters"], "val": r["best"]["val"], "params": r["best"]["numba_params"],
                       "best_iter": r["best"]["iter"], "history": []}
    extra = []
    for c in sorted(best):
        same = any(q["chain"] == c and all(abs(q["params"][k] - best[c]["params"][k]) <= 1e-12 * max(1.0, abs(q["params"][k]))
                                           for k in q["params"]) for q in pts)
        if not same:
            extra.append(best[c])
    return sorted(pts, key=lambda q: (q["chain"], q["lam_fc"])) + extra


def stage_sweep(workers: int, chains=None):
    from opt.tracker import sweep as SW
    prev = previous_sets()
    chains = chains or [("A", "akf_grid", 1.0, [0.01, 0.03, 0.1, 0.3, 1.0], 40, 25),
                        ("B", "akf_robust", 0.0, [0.01, 0.03, 0.1, 0.3, 1.0], 40, 25)]
    for name, key, harm, lams, it1, it2 in chains:
        missing = [l for l in lams if not os.path.exists(os.path.join(RUNS, f"sweep_{name}_l{l:g}.json"))]
        if missing:
            SW.run_chain(name, prev[key], harm, lams, it1, it2, log=lambda s: print(s, flush=True))
    pts = sweep_points()
    save_stage("sweep", {"points": pts, "meta": meta(EVIDENCE_SIM, {"train": "fusion.learned._spec(i, 'train'), 96 sigma-lognormal + 64 glyph pairs",
                                                                     "validation": "fusion val specs (24 pairs), tuning seeds 5004-5007, aiguide writers 100-105"})})
    return pts


def point_label(p):
    if p.get("kind") == "valbest":
        return f"adj_{p['chain']}_valbest"
    return f"adj_{p['chain']}_l{p['lam_fc']:g}"


# ------------------------------------------------------------------ replicate (the random search's own objectives)
def stage_replicate(workers: int, iters: int = 30):
    from opt.tracker import replicate as RP
    prev = previous_sets()
    out = {}
    for kind, key in (("grid", "akf_grid"), ("robust", "akf_robust")):
        r = RP.run(kind, prev[key], iters=iters, log=lambda s: print(s, flush=True), workers=workers)
        out[kind] = {k: r[k] for k in ("kind", "start_reference", "start_torch", "params", "result_reference", "elapsed_s", "objective")}
        out[kind]["best_iter"] = r["best"]["iter"]
        out[kind]["history"] = r["history"]
    out["meta"] = meta(EVIDENCE_SIM, {"data": "fusion.tune: tuning seeds 5000-5007 (sensor tags 7/8), aiguide writers 100-105"})
    save_stage("replicate", out)
    return out


def replicate_specs() -> List:
    rp = load_stage("replicate") or {}
    return [H.Spec(f"rep_{k}", "akf", rp[k]["params"], SK_1K) for k in ("grid", "robust") if k in rp]


# ------------------------------------------------------------------ select (closed loop on tuning data)
AI_TUNE = ((100, 5.0), (101, 7.0), (102, 9.0), (103, 6.0), (104, 8.0), (105, 4.5))   # fusion.tune.AI_TUNE


def select_rule(res: Dict, candidates: List[str]) -> Dict:
    """Pre-declared: lowest tuning-grid band ratio among the points whose closed-loop distortion is <= 14 um on the
    tuning seeds' writing and <= 30 um on the tuning glyph writers' tremor-free writing, and whose aiguide
    writing-only path RMS is not worse than no correction."""
    g = res["grid"]["summary"]
    a = res["aiguide"]["summary"]
    ok = []
    for lab in candidates:
        d_grid = g[lab].get("distortion_um_mean", 1e9)
        d_ai = a[lab]["distortion_um"]["mean"]
        path = a[lab]["wo_path_rms_um"]["mean"]
        path0 = a["neutral"]["wo_path_rms_um"]["mean"]
        if d_grid <= 14.0 and d_ai <= 30.0 and path <= path0:
            ok.append((g[lab]["band_ratio_mean"], lab))
    ok.sort()
    return {"rule": select_rule.__doc__, "eligible": [x[1] for x in ok], "chosen": ok[0][1] if ok else None}


def stage_select(workers: int):
    from opt.tracker import evaluate as EV
    pts = sweep_points()
    prev = previous_sets()
    specs = [H.Spec("akf_grid", "akf", prev["akf_grid"], SK_1K), H.Spec("akf_robust", "akf", prev["akf_robust"], SK_1K)]
    for p in pts:
        specs.append(H.Spec(point_label(p), "akf", p["params"], SK_1K))
    specs += replicate_specs()
    specs += learned_specs()
    grid = EV.grid(specs, seeds=OT.TUNE_SEEDS[:4], workers=workers)
    ai = _ai_tune(specs, workers)
    res = {"grid": {"summary": grid["summary"]}, "aiguide": {"summary": ai["summary"]}}
    cands = [point_label(p) for p in pts] + [s.label for s in replicate_specs()] + [s.label for s in learned_specs()]
    sel = select_rule(res, cands)
    out = {"grid_summary": grid["summary"], "aiguide_summary": ai["summary"], "selection": sel,
           "points": [{"label": point_label(p), "chain": p["chain"], "lam_fc": p["lam_fc"], "params": p["params"]} for p in pts],
           "meta": meta(EVIDENCE_SIM, {"closed_loop": list(OT.TUNE_SEEDS[:4]), "aiguide_tuning_writers": [list(x) for x in AI_TUNE]})}
    save_stage("select", out)
    write_choice(sel)
    return out


CHOICE_TEXT = {
    "gru_band": ("GRU with the tremor-band target (this study)",
                 "A small recurrent network trained on the 3-15 Hz part of the disturbance only."),
    "hybrid": ("Accelerometer Kalman filter + learned authority gate (this study)",
               "The adjoint-tuned Kalman filter estimates the tremor; a small learned gate lowers its authority when the pen is "
               "writing rather than trembling."),
    "rep_robust": ("Accelerometer Kalman filter, robust settings re-optimised by backpropagation (this study)",
                   "The same Kalman filter as the robust set, with the random search's own robust objective (tuning writing plus "
                   "sharp glyph writers) minimised by gradient through the filter (its adjoint) instead of by random search."),
    "rep_grid": ("Accelerometer Kalman filter, grid settings re-optimised by backpropagation (this study)",
                 "The same Kalman filter with the random search's grid objective minimised by gradient through the filter."),
}
DEFAULT_CHOICE_TEXT = ("Accelerometer Kalman filter tuned by backpropagation (this study)",
                       "The same Kalman filter as before, with all 23 settings tuned by gradient (the adjoint of the filter) on "
                       "domain-randomised writers, 40 % of them sharp glyph writers.")


def write_choice(sel: Dict) -> Dict:
    ch = sel["chosen"]
    t, n = CHOICE_TEXT.get(ch, DEFAULT_CHOICE_TEXT)
    rec = {"ship": ch, "ship_title": t, "ship_note": n, "rule": sel["rule"]}
    save_stage("report_choice", rec)
    return rec


def _ai_tune(specs, workers):
    from opt.tracker import evaluate as EV
    from concurrent.futures import ProcessPoolExecutor
    sp = {s.label: (s.name, s.params, SK_1K) for s in specs}
    jobs = [(w, f0, sp, False) for w, f0 in AI_TUNE]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=EV._worker_init) as ex:
        outs = list(ex.map(EV._ai_scenario, jobs))
    labels = list(outs[0]["rows"].keys())
    summ = {}
    for lab in labels:
        for k in outs[0]["rows"][lab]:
            vals = [o["rows"][lab][k] for o in outs if isinstance(o["rows"][lab].get(k), (int, float))
                    and o["rows"][lab].get(k) is not None and np.isfinite(o["rows"][lab].get(k))]
            if vals:
                summ.setdefault(lab, {})[k] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals)), "n": len(vals)}
    return {"summary": summ, "scenarios": outs, "elapsed_s": time.time() - t0}


def ship_params() -> Dict:
    sel = load_stage("select")
    lab = sel["selection"]["chosen"]
    return lab, [p for p in sel["points"] if p["label"] == lab][0]["params"]


# ------------------------------------------------------------------ learned
LEARNED_LAM = 0.1          # lambda_fc of both learned models (they are compared with the AKF front by position)
HYBRID_BASE = ("A", 0.01)  # the aggressive adjoint-tuned AKF: the gate has false correction to remove


def stage_learned(workers: int, retrain: bool = False, minutes: float = 45.0):
    import torch
    from opt.tracker import data as DA, learned_train as LT
    torch.set_num_threads(2)
    pts = {(p["chain"], p["lam_fc"]): p for p in sweep_points() if p["kind"] == "last"}
    base = pts[HYBRID_BASE]["params"]
    out = {"lam_fc": LEARNED_LAM, "hybrid_base": f"adj_{HYBRID_BASE[0]}_l{HYBRID_BASE[1]:g}"}
    names = {"gru": "opt_gru48_band", "hybrid": "opt_hybrid_gate24"}
    tg_items = DA.tune_grid_items()
    if retrain or not os.path.exists(os.path.join(MODEL_DIR, names["gru"] + ".json")):
        A = LT.gru_data(list(range(400)), "train", "all400")
        V = LT.gru_data(list(range(24)), "val", "val24")
        TG = LT.arrays(tg_items)
        LT.train(A, {"val": V, "tune_grid": TG}, LT.LCfg(kind="gru", hidden=48, lam_fc=LEARNED_LAM, max_minutes=minutes),
                 names["gru"], log=lambda s: print(s, flush=True))
    if retrain or not os.path.exists(os.path.join(MODEL_DIR, names["hybrid"] + ".json")):
        Ah = LT.arrays(DA.train_items(96, 64), base)
        Vh = LT.arrays(DA.val_items(), base)
        TGh = LT.arrays(tg_items, base)
        LT.train(Ah, {"val": Vh, "tune_grid": TGh}, LT.LCfg(kind="hybrid", hidden=24, lam_fc=LEARNED_LAM, max_minutes=minutes),
                 names["hybrid"], akf_params=base, log=lambda s: print(s, flush=True))
    for k, n in names.items():
        m = json.load(open(os.path.join(MODEL_DIR, n + ".json")))
        out[k] = {kk: m[kk] for kk in ("name", "kind", "n_in", "hidden", "n_out", "lp_hz", "best_epoch", "macs_per_step",
                                       "params", "train_recordings", "total_s", "cfg", "start_val")}
        out[k]["history"] = [{"epoch": h["epoch"], "train_J": h["train_J"], "score": h["score"],
                              "val": {v: {q: h["val"][v].get(q) for q in ("J", "rr_band", "fc_w_um", "hf_um")} for v in h["val"]}}
                             for h in m["history"]]
    out["meta"] = meta(EVIDENCE_SIM, {"train": "fusion.learned._spec(i, 'train'): GRU all 400 pairs (30 % glyph), hybrid 160 pairs (40 % glyph)",
                                      "validation": "fusion val specs (24 pairs), tuning seeds 5004-5007"})
    save_stage("learned", out)
    return out


def learned_specs() -> List:
    out = []
    for lab, name in (("gru_band", "opt_gru48_band"), ("hybrid", "opt_hybrid_gate24")):
        if os.path.exists(os.path.join(MODEL_DIR, name + ".json")):
            out.append(H.Spec(lab, name, {"model": name}, SK_1K))
    return out


# ------------------------------------------------------------------ personal
PERS_RHOS = (0.003, 0.02, 0.1)


def _calib_job(args):
    seed, f0, amp = args
    from opt.tracker import personal as PE
    from fusion import personal as PS
    pop = FRS.population(FRS.tuned())
    r = PS.personalise(seed, f0, amp, pop, SK_1K)
    return {"seed": seed, "f0": f0, "amp": amp, "choice": r["params"], "calibration": r["calibration"],
            "calib_band_rr": r["calib_band_rr"], "calib_band_rr_population": r["calib_band_rr_population"]}


def stage_personal(workers: int, iters: int = 30):
    import torch
    from concurrent.futures import ProcessPoolExecutor
    from opt.tracker import adjoint as AD, evaluate as EV, personal as PE, data as DA, torch_akf as TA, losses as LS
    from fusion import data as FD, sensors as S, estimators as ES
    torch.set_num_threads(1)
    AD.set_threads(2)
    pop = FRS.population(FRS.tuned())
    out = {"population": "fusion robust AKF (fusion.run_study.population)", "keys": list(PE.PERSONAL_KEYS)}
    # ---- 1) prior weight on tuning seeds 5000-5003 (0.3 mm, 4-12 Hz): open-loop band residual on each seed's
    # 0.3 mm grid condition (other noise draws) with the parameters fitted on that condition's calibration task
    tune_conds = [(s, f0, 0.3e-3) for s in OT.TUNE_SEEDS[:4] for f0 in H.F0S]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        choices = list(ex.map(_calib_job, tune_conds))
    calibs = [PE.Calib(s, f0, a) for (s, f0, a) in tune_conds]
    items = []
    for (s, f0, a) in tune_conds:
        r1, r0 = FD.test_pair_records(s, f0, a)
        st = S.make_streams(r1, S.config(**SK_1K), H.sensor_seed(s, f0, a, 23))
        m = (np.interp(st.tick_t, r1.t, r1.contact) > 0.5) & (st.tick_t > 0.5)
        items.append({"st": st, "d": S.truth_at(st.tick_t, r1, r0), "m": m, "clean": False, "glyph": False, "meta": {}})

    tune = {"conditions": [list(c) for c in tune_conds],
            "choice_band_rr": [_rr_band(ES.akf(it["st"], c["choice"])[0], it) for it, c in zip(items, choices)],
            "population_band_rr": [_rr_band(ES.akf(it["st"], pop)[0], it) for it in items]}
    fits = {}
    for rho in PERS_RHOS:
        res, hist = PE.refine(calibs, [c["choice"] for c in choices], rho=rho, iters=iters, log=lambda s: print(s, flush=True),
                              tag=f" tune rho {rho:g}")
        tune[f"rho_{rho:g}"] = {"band_rr": [_rr_band(ES.akf(it["st"], r["params"])[0], it) for it, r in zip(items, res)],
                                "calib_fit": [r["fit_best"] for r in res], "history": hist}
        fits[rho] = res
    tune["summary"] = {k: float(np.mean(v["band_rr"] if isinstance(v, dict) else v)) for k, v in tune.items()
                       if k.startswith("rho_") or k in ("choice_band_rr", "population_band_rr")}
    rho_best = min(PERS_RHOS, key=lambda r: tune["summary"][f"rho_{r:g}"])
    out["tuning"] = tune
    out["rho_chosen"] = rho_best
    # ---- 2) test seeds 200-203 at 0.3 mm, 4-12 Hz (closed loop) and distortion (calibrations at 6 and 10 Hz)
    test_conds = [(s, f0, 0.3e-3) for s in OT.TEST_SEEDS for f0 in H.F0S]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        tchoices = list(ex.map(_calib_job, test_conds))
    tcalibs = [PE.Calib(s, f0, a) for (s, f0, a) in test_conds]
    tres, thist = PE.refine(tcalibs, [c["choice"] for c in tchoices], rho=rho_best, iters=iters,
                            log=lambda s: print(s, flush=True), tag=" test")
    per_choice = {(s, f0, round(a * 1e6)): c["choice"] for (s, f0, a), c in zip(test_conds, tchoices)}
    per_adj = {(s, f0, round(a * 1e6)): r["params"] for (s, f0, a), r in zip(test_conds, tres)}
    specs = [H.Spec("akf_robust", "akf", pop, SK_1K), H.Spec("akf_personal", "akf", pop, SK_1K),
             H.Spec("akf_personal_adjoint", "akf", pop, SK_1K)]
    grid = EV.grid(specs, seeds=OT.TEST_SEEDS, f0s=H.F0S, amps=(0.3e-3,), workers=workers, dist=False,
                   per_cond={"akf_personal": per_choice, "akf_personal_adjoint": per_adj})
    dist_items = []
    for (s, f0, a), c, r in zip(test_conds, tchoices, tres):
        if f0 in (6.0, 10.0):
            dist_items.append((s, "akf_personal", c["choice"], f0))
            dist_items.append((s, "akf_personal_adjoint", r["params"], f0))
    drows = EV.personal_distortion(dist_items, workers=workers)
    out["test"] = {"grid_summary": grid["summary"], "rows": [r for r in grid["rows"] if r["label"] in
                                                               ("akf_robust", "akf_personal", "akf_personal_adjoint", "oracle_band", "neutral")],
                   "distortion_rows": drows,
                   "distortion_um": {lab: float(np.mean([d["distortion_um"] for d in drows if d["label"] == lab]))
                                     for lab in ("akf_personal", "akf_personal_adjoint")},
                   "calib_fit_choice": [c["calib_band_rr"] for c in tchoices], "calib_fit_adjoint": [r["fit_best"] for r in tres],
                   "calibration_estimates": [c["calibration"] for c in tchoices], "conditions": [list(c) for c in test_conds],
                   "adjoint_params": [r["params"] for r in tres], "history": thist}
    out["meta"] = meta(EVIDENCE_SIM, {"calibration": "seed + 40000 (fusion.personal)", "rho_choice": list(OT.TUNE_SEEDS[:4]),
                                      "test": list(OT.TEST_SEEDS)})
    save_stage("personal", out)
    return out


def _rr_band(dh, it):
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, (3.0, 15.0), btype="band", fs=2000.0, output="sos")
    m = it["m"]
    e = sosfiltfilt(sos, it["d"] - dh, axis=0)
    db = sosfiltfilt(sos, it["d"], axis=0)
    return float(np.sqrt(np.sum(e[m] ** 2) / max(np.sum(db[m] ** 2), 1e-30)))


PERS_FC_LAMS = (0.3, 1.0, 3.0)


def _fc_open_loop(params_list, seeds_f0) -> List[float]:
    """Open-loop false correction (um RMS in contact) of each personal set on its own seed's tremor-free writing."""
    from fusion import data as FD, sensors as S, estimators as ES
    out = []
    for p, (s, f0) in zip(params_list, seeds_f0):
        _, r0 = FD.test_pair_records(s, 4.0, 0.1e-3)
        st = S.make_streams(r0, S.config(**SK_1K), H.sensor_seed(s, 0.0, 0.0, 29))
        m = (np.interp(st.tick_t, r0.t, r0.contact) > 0.5) & (st.tick_t > 0.5)
        dh, _ = ES.akf(st, p)
        out.append(float(np.sqrt(np.mean(np.sum(dh[m] ** 2, axis=1))) * 1e6))
    return out


def stage_personal_fc(workers: int, iters: int = 30):
    """Adjoint personalisation with a false-correction term on OTHER writers' tremor-free training writing.
    Pre-declared choice of lambda_fc,p on tuning seeds 5000-5003: the lowest tuning band residual among the weights
    whose open-loop false correction on the tuning seeds' own tremor-free writing is no higher than the 12-candidate
    choice's (the prior weight stays at the value chosen by stage personal)."""
    import torch
    from concurrent.futures import ProcessPoolExecutor
    from opt.tracker import adjoint as AD, evaluate as EV, personal as PE, data as DA
    from fusion import data as FD, sensors as S, estimators as ES
    torch.set_num_threads(1)
    AD.set_threads(2)
    prev = load_stage("personal")
    rho = prev["rho_chosen"]
    tr = DA.train_items(96, 64)
    fc_items = [it for it in tr if it["clean"] and not it["glyph"]][:3] + [it for it in tr if it["clean"] and it["glyph"]][:3]
    del tr
    out = {"rho": rho, "fc_items": [it["meta"] for it in fc_items], "rule": stage_personal_fc.__doc__}
    tune_conds = [(s, f0, 0.3e-3) for s in OT.TUNE_SEEDS[:4] for f0 in H.F0S]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        choices = list(ex.map(_calib_job, tune_conds))
    calibs = [PE.Calib(*c) for c in tune_conds]
    items = []
    for (s, f0, a) in tune_conds:
        r1, r0 = FD.test_pair_records(s, f0, a)
        st = S.make_streams(r1, S.config(**SK_1K), H.sensor_seed(s, f0, a, 23))
        m = (np.interp(st.tick_t, r1.t, r1.contact) > 0.5) & (st.tick_t > 0.5)
        items.append({"st": st, "d": S.truth_at(st.tick_t, r1, r0), "m": m})
    sf = [(s, f0) for (s, f0, a) in tune_conds]
    tune = {"choice": {"band_rr": [_rr_band(ES.akf(it["st"], c["choice"])[0], it) for it, c in zip(items, choices)],
                       "fc_um": _fc_open_loop([c["choice"] for c in choices], sf)}}
    for lam in PERS_FC_LAMS:
        res, hist = PE.refine(calibs, [c["choice"] for c in choices], rho=rho, iters=iters, log=lambda q: print(q, flush=True),
                              tag=f" fc tune lambda {lam:g}", fc_items=fc_items, lam_fc=lam)
        tune[f"lam_{lam:g}"] = {"band_rr": [_rr_band(ES.akf(it["st"], r["params"])[0], it) for it, r in zip(items, res)],
                                "fc_um": _fc_open_loop([r["params"] for r in res], sf), "calib_fit": [r["fit_best"] for r in res]}
    summ = {k: {"band_rr": float(np.mean(v["band_rr"])), "fc_um": float(np.mean(v["fc_um"]))} for k, v in tune.items()}
    ok = [(summ[f"lam_{l:g}"]["band_rr"], l) for l in PERS_FC_LAMS if summ[f"lam_{l:g}"]["fc_um"] <= summ["choice"]["fc_um"]]
    lam_best = min(ok)[1] if ok else max(PERS_FC_LAMS)
    out.update({"tuning": tune, "tuning_summary": summ, "lam_chosen": lam_best})
    # test
    test_conds = [(s, f0, 0.3e-3) for s in OT.TEST_SEEDS for f0 in H.F0S]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        tchoices = list(ex.map(_calib_job, test_conds))
    tcalibs = [PE.Calib(*c) for c in test_conds]
    tres, thist = PE.refine(tcalibs, [c["choice"] for c in tchoices], rho=rho, iters=iters, log=lambda q: print(q, flush=True),
                            tag=" fc test", fc_items=fc_items, lam_fc=lam_best)
    per_adj = {(s, f0, round(a * 1e6)): r["params"] for (s, f0, a), r in zip(test_conds, tres)}
    pop = FRS.population(FRS.tuned())
    grid = EV.grid([H.Spec("akf_personal_adjoint_fc", "akf", pop, SK_1K)], seeds=OT.TEST_SEEDS, f0s=H.F0S, amps=(0.3e-3,),
                   workers=workers, dist=False, per_cond={"akf_personal_adjoint_fc": per_adj})
    dist_items = [(s, "akf_personal_adjoint_fc", r["params"], f0) for (s, f0, a), r in zip(test_conds, tres) if f0 in (6.0, 10.0)]
    drows = EV.personal_distortion(dist_items, workers=workers)
    out["test"] = {"grid_summary": grid["summary"], "rows": [r for r in grid["rows"] if r["label"] == "akf_personal_adjoint_fc"],
                   "distortion_rows": drows, "distortion_um": float(np.mean([d["distortion_um"] for d in drows])),
                   "calib_fit_adjoint_fc": [r["fit_best"] for r in tres], "adjoint_params": [r["params"] for r in tres],
                   "history": thist}
    out["meta"] = meta(EVIDENCE_SIM, {"calibration": "seed + 40000", "fc_writing": "fusion training specs (tremor-free runs)",
                                      "choice": list(OT.TUNE_SEEDS[:4]), "test": list(OT.TEST_SEEDS)})
    save_stage("personal_fc", out)
    return out


# ------------------------------------------------------------------ test
F0S_AI = (4.0, 6.0, 8.0, 10.0)


def test_specs(include_sweep: bool = True) -> List:
    prev = previous_sets()
    sp = [H.Spec("akf_grid", "akf", prev["akf_grid"], SK_1K), H.Spec("akf_robust", "akf", prev["akf_robust"], SK_1K),
          H.Spec("gru_old", "learned", {"model": "gru48_1k", "lp_hz": 60.0}, SK_1K)]
    if include_sweep:
        for p in sweep_points():
            sp.append(H.Spec(point_label(p), "akf", p["params"], SK_1K))
    sp += replicate_specs()
    sp += learned_specs()
    return sp


def stage_test(workers: int):
    from opt.tracker import evaluate as EV
    sp = test_specs()
    grid = EV.grid(sp, seeds=OT.TEST_SEEDS, workers=workers)
    ai = EV.aiguide({s.label: (s.name, s.params, s.sensors) for s in sp}, writers=OT.AIGUIDE_TEST_WRITERS, f0s=F0S_AI,
                    workers=workers)
    out = {"grid": {"summary": grid["summary"], "rows": grid["rows"], "distortion_rows": grid["distortion_rows"],
                    "elapsed_s": grid["elapsed_s"]},
           "aiguide": {"summary": ai["summary"], "scenarios": ai["scenarios"], "elapsed_s": ai["elapsed_s"]},
           "specs": [{"label": s.label, "name": s.name, "params": s.params} for s in sp],
           "meta": meta(EVIDENCE_SIM, {"test": list(OT.TEST_SEEDS), "sensor_noise": "10_000_000 + 1000 seed + 10 f0 + amp[0.1 mm]",
                                       "aiguide_test_writers": list(OT.AIGUIDE_TEST_WRITERS), "aiguide_f0": list(F0S_AI)})}
    save_stage("test", out)
    return out


# ------------------------------------------------------------------ budget / viz / report
def stage_budget():
    from opt.tracker import budget as BU
    L = load_stage("learned") or {}
    out = BU.costs(gru_hidden=(L.get("gru") or {}).get("hidden", 48), gate_hidden=(L.get("hybrid") or {}).get("hidden", 24))
    out["meta"] = meta(EVIDENCE_CALC, None)
    save_stage("budget", out)
    return out


def stage_viz(best_label: str = None):
    from opt.tracker import viz as VZ
    prev = previous_sets()
    rep = load_stage("report_choice") or {}
    lab = best_label or rep.get("ship")
    sp = {s.label: s for s in test_specs()}[lab]
    note = rep.get("ship_note", "The tracker this study recommends.")
    vz = VZ.traces((lab, sp.name, sp.params, rep.get("ship_title", "Recommended tracker (this study)"), note),
                   {"akf_prev_best": prev["akf_grid"], "akf_robust": prev["akf_robust"]})
    VZ.write(vz)
    return {c["key"]: c["metrics"] for c in vz["cases"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stages", nargs="*", default=["check", "gradscan", "sweep", "replicate", "learned", "select", "personal",
                                                    "personal_fc", "test", "budget", "report", "viz"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--retrain", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    for st in a.stages:
        print(f"== stage {st} ({time.time() - t0:.0f} s)", flush=True)
        if st == "check":
            stage_check(a.workers)
        elif st == "gradscan":
            stage_gradscan(a.workers)
        elif st == "sweep":
            stage_sweep(a.workers)
        elif st == "replicate":
            stage_replicate(a.workers)
        elif st == "select":
            stage_select(a.workers)
        elif st == "learned":
            stage_learned(a.workers, a.retrain)
        elif st == "personal":
            stage_personal(a.workers)
        elif st == "personal_fc":
            stage_personal_fc(a.workers)
        elif st == "test":
            stage_test(a.workers)
        elif st == "budget":
            stage_budget()
        elif st == "report":
            from opt.tracker import report as RP
            RP.write_all()
        elif st == "viz":
            print(stage_viz())
    print(f"all done {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
