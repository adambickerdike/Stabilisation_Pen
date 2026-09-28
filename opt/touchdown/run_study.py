#!/usr/bin/env python3
"""Touchdown / lift feed-forward, stop margin and piezo servo of the pencil: the full study (model P1).

Stages (each caches its result in results/opt/logs/td_<stage>.json; --stages picks a subset):
  adjoint    reduced torch model: adjoint-gradient fit of the law and structural ablations; check against P1
  baseline   tilt-range stop and adaptive stops (0.1-0.4 mm) without feed-forward, training seeds 300-309
  bo         ParEGO Bayesian optimisation of the law jointly with the margin (training seeds 300-309, 50 deg);
             Pareto front; pick; held-out check on training seeds 310-319; travel-priority comparison
  servo      Bayesian optimisation of the inner servo (tracking error vs rail power; Hall noise 1 um and 0.3 um)
  validate   test seeds 200-203 (first use): 50 / 35 / 75 deg, tremor-free and 6 Hz / 0.3 mm (oracle, frozen Kalman);
             the published diagnostic on 5 s runs; tilt-lag proxy; servo test grid
  checks     mechanism checks quoted in the doc: 1 mm/s touchdown with the ideal law (hand-over on / off), removal of
             the stage-induced slide (kappa 1 / 0), friction dither without the dead zone (held-out training seeds)
  viz        results/opt/viz_touchdown.json (3-D replay: seed 200, 50 deg, no tremor)
  figures    results/opt/fig_td_*.png
  report     results/opt/touchdown.json, results/opt/servo.json (provenance metadata)
Run: python3 -m opt.touchdown.run_study [--stages adjoint,baseline,...] [--quick] [--workers 2]
Evidence status: CALCULATION and SIMULATION on synthetic handwriting.  Nothing here is a measurement.
"""
from __future__ import annotations

import os as _os

# one BLAS thread per process: the GP fits and the simulator workers share 2 cores with other studies, and a
# multi-threaded BLAS spin-waits under that load (a 1 s GP fit took minutes)
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import copy
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import sim.pencil  # noqa: E402,F401
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pencil import power as PW  # noqa: E402
from stabpen import provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

from opt.touchdown import law as L  # noqa: E402
from opt.touchdown import metrics as MT  # noqa: E402
from opt.touchdown import runs  # noqa: E402
from opt.touchdown import servo as S  # noqa: E402
from opt.touchdown import study_bo as SB  # noqa: E402

OUT = os.path.join(ROOT, "results", "opt")
LOGS = os.path.join(OUT, "logs")


def _pencil_params():
    from sim.pencil import design as D
    return D.Params().pencil


STAGES = ("adjoint", "baseline", "bo", "servo", "validate", "checks", "viz", "figures", "report")
Q = {"quick": False}


def _path(stage):
    return os.path.join(LOGS, f"td_{stage}{'_quick' if Q['quick'] else ''}.json")


def save(stage, obj):
    os.makedirs(LOGS, exist_ok=True)
    provenance.write_json(_path(stage), obj)


def load(stage):
    p = _path(stage)
    return json.load(open(p)) if os.path.exists(p) else None


def _tolist(o):
    if isinstance(o, dict):
        return {k: _tolist(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_tolist(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


# ------------------------------------------------------------------ stage: adjoint
def stage_adjoint(workers, precomputed=None):
    """precomputed: JSON files written earlier by reduced.adjoint_study (same code), merged instead of refitting
    (the fits take about 15 min on 2 processes); the P1 checks always run."""
    import torch
    torch.set_num_threads(1)
    from opt.touchdown import reduced as R
    t0 = time.time()
    iters = 2 if Q["quick"] else 20
    if precomputed:
        res = {}
        for p in precomputed:
            d = json.load(open(p))
            for k, v in d.items():
                res.setdefault(k, v)
        res["precomputed_from"] = [os.path.basename(p) for p in precomputed]
    else:
        res = R.adjoint_study(iters=iters, workers=workers, names=["full"] if Q["quick"] else None)
    full = res["full"]["best"]
    chk_ideal, tr_ideal = R.check_against_p1(dict(R.PARAM_INIT, lead_s=0.0), vx=(0.0,) if Q["quick"] else (0.0, 0.02))
    chk_fit, tr_fit = R.check_against_p1(full, vx=(0.0,) if Q["quick"] else (0.0, 0.02))
    chk_off, tr_off = R.check_against_p1(dict(R.PARAM_INIT), vx=(0.0,), ff_on=False)
    out = {"study": _tolist(res), "check_ideal_law": chk_ideal, "check_fitted_law": chk_fit, "check_no_feedforward": chk_off,
           "traces_ideal": _tolist({k: {kk: (vv if kk == "t" else {a: b[::4] for a, b in vv.items()}) if kk != "t" else vv[::4]
                                        for kk, vv in v.items()} for k, v in tr_ideal.items()}),
           "elapsed_s": time.time() - t0}
    save("adjoint", out)
    print("adjoint: full fit", full, "loss", res["full"]["best_loss_um"], "ideal", res["ideal_law"]["mean_rms_ink_um"],
          "no ff", res["no_feedforward"]["mean_rms_ink_um"], flush=True)
    return out


# ------------------------------------------------------------------ stage: baseline and bo
def _pool(workers):
    return ProcessPoolExecutor(workers)


def stage_baseline(workers):
    seeds = SB.BO_SEEDS[:2] if Q["quick"] else SB.BO_SEEDS
    with _pool(workers) as pool:
        out = SB.baselines(pool, seeds=seeds)
    save("baseline", out)
    return out


def stage_bo(workers):
    base = load("baseline") or stage_baseline(workers)
    adj = load("adjoint")
    rms_ref = base["adaptive_0.3mm"]["agg"]["rms_nn_instroke_um"]
    ratio_cap = base["adaptive_0.3mm"]["agg"]["oracle_ratio"] + 0.01
    x0 = [dict(margin=m, gain=1.0, kappa=1.0, pre=1.0, lead_s=1e-3, lp_hz=200.0, dz=20e-6, k_load=1.0, det_e=0.0, hold_s=2e-3, v_td=0.0)
          for m in (0.2e-3, 0.3e-3, 0.4e-3)]
    if adj:
        f = adj["study"]["full"]["best"]
        x0.append(dict(margin=0.3e-3, gain=float(np.clip(f["gain"], *L.BOUNDS["gain"])), kappa=float(np.clip(f["kappa"], *L.BOUNDS["kappa"])),
                       pre=float(np.clip(f["pre"], *L.BOUNDS["pre"])), lead_s=float(np.clip(f["lead_s"], *L.BOUNDS["lead_s"])), lp_hz=200.0,
                       dz=20e-6, k_load=float(np.clip(f["k_load"], *L.BOUNDS["k_load"])), det_e=0.0, hold_s=2e-3, v_td=0.0))
    seeds = SB.BO_SEEDS[:2] if Q["quick"] else SB.BO_SEEDS
    n_init, n_iter = (2, 2) if Q["quick"] else (24, 96)
    with _pool(workers) as pool:
        rows = SB.ff_search(pool, rms_ref, n_init=n_init, n_iter=n_iter, x0=x0[:1] if Q["quick"] else x0,
                            log_name="ff_bo_quick.jsonl" if Q["quick"] else "ff_bo.jsonl", seeds=seeds)
        front = SB.pareto(rows)
        best = SB.pick(rows, ratio_cap)
        # held-out check: the pick and its two nearest competitors under the same cap
        ok = sorted([r for r in rows if r["res"]["oracle_ratio"] <= ratio_cap], key=lambda r: r["f"]["f_tail"])[:3] or [best]
        cands = [(f"candidate_{i}", r["x"]) for i, r in enumerate(ok)]
        hold = SB.holdout(pool, cands, rms_ref, seeds=SB.HOLDOUT_SEEDS[:2] if Q["quick"] else SB.HOLDOUT_SEEDS)
        hold_ok = [h for h in hold if h["agg"]["oracle_ratio"] <= ratio_cap + 0.01] or hold
        final = min(hold_ok, key=lambda h: h["f_tail"])
        prio = SB.priority_check(pool, final["x"], rms_ref, seeds=seeds)
        # the same law without the Hall detection and without pre-positioning (what each part buys), held-out seeds
        abl = {}
        for name, mod in (("no_hall_detection", {"det_e": 0.0}), ("no_prepositioning", {"pre": 0.0}), ("no_lead", {"lead_s": 0.0}),
                          ("no_dead_zone", {"dz": 0.0}), ("no_slide_removal", {"kappa": 0.0}), ("no_handover", {}),
                          ("legacy_bias_ramp", {}), ("fast_axial_sensor", {})):
            xd = dict(final["x"], **mod)
            fixed = dict(SB.FIXED)
            extra = {}
            if name == "legacy_bias_ramp":
                fixed["bias"] = 0
            if name == "no_handover":
                fixed["handover"] = 0
            if name == "fast_axial_sensor":
                extra = {"overrides": {"ax_decim": 4, "ax_delay": 4}}
            lw = L.TouchdownLaw(**xd, **fixed, **extra)
            agg, _ = runs.score(lw, SB.HOLDOUT_SEEDS[:2] if Q["quick"] else SB.HOLDOUT_SEEDS, pool=pool)
            slow = runs.slow_descents(lw)
            ft, fr = SB.objectives(agg, rms_ref, slow)
            abl[name] = {"f_tail": ft, "f_ratio": fr, "agg": agg, "slow": slow}
            print("ablation", name, round(ft, 4), round(fr, 4), round(agg["extra_tr_mm"], 4), flush=True)
    out = {"rms_ref_um": rms_ref, "ratio_cap": ratio_cap, "n_evaluations": len(rows), "space": SB.FF_SPACE, "fixed": SB.FIXED,
           "front": [{"x": r["x"], "f": r["f"], "res": r["res"]} for r in front],
           "all": [{"x": r["x"], "f": r["f"], "tag": r["tag"],
                    "res": {k: r["res"][k] for k in ("extra_mm", "extra_tr_mm", "extra_in_mm", "extra_tr_tight_mm", "missing_mm",
                                                     "rms_nn_instroke_um", "oracle_ratio", "oracle_limit_frac_contact",
                                                     "clean_qff_peak_contact_mm", "transitions_per_pd", "tail_noskid_mm") if k in r["res"]}}
                   for r in rows],
           "search_pick": {"x": best["x"], "f": best["f"]}, "holdout": hold, "final": final, "priority": prio, "ablations": abl}
    save("bo", out)
    return out


# ------------------------------------------------------------------ stage: servo
def stage_servo(workers):
    out = {"rule": S.RULE, "default": S.DEFAULT, "default_margins": S.loop_margins(**S.DEFAULT)}
    seeds = (300, 301) if Q["quick"] else tuple(range(300, 306))
    n_init, n_iter = (2, 2) if Q["quick"] else (16, 44)
    with _pool(workers) as pool:
        for hn in (1e-6, 0.3e-6):
            rows = SB.servo_search(pool, hall_noise=hn, n_init=n_init, n_iter=n_iter, seeds=seeds,
                                   log_name=f"servo_bo_hall{hn * 1e6:.1f}um{'_quick' if Q['quick'] else ''}.jsonl")
            # picks keep the margin rule at nominal stiffness and are no less robust than the P0.1.2 servo when the stage
            # stiffness is off by +-20 % (phase margin at least the default's worst case, 44 deg); the picks under the
            # nominal rule alone are kept for reference
            pm_tol_min = out["default_margins"]["pm_min_deg"]
            base, low_power, best_track = SB.servo_pick(rows, pm_tol_min=pm_tol_min)
            _, low_power_nom, best_track_nom = SB.servo_pick(rows)
            front = SB.pareto([r for r in rows if r["res"].get("feasible")], keys=("track_um", "P_rail_classB_mW"))
            out[f"hall_{hn * 1e6:.1f}um"] = {
                "n_evaluations": len(rows), "n_feasible": sum(1 for r in rows if r["res"].get("feasible")),
                "robust_rule_pm_min_deg_at_stiffness_pm20pct": pm_tol_min,
                "default": {"x": base["x"], "res": base["res"]},
                "lowest_power_at_default_tracking": {"x": low_power["x"], "res": low_power["res"], "margins": S.loop_margins(**low_power["x"])},
                "best_tracking_at_default_power": {"x": best_track["x"], "res": best_track["res"], "margins": S.loop_margins(**best_track["x"])},
                "nominal_rule_only": {
                    "lowest_power_at_default_tracking": {"x": low_power_nom["x"], "res": low_power_nom["res"],
                                                         "margins": S.loop_margins(**low_power_nom["x"])},
                    "best_tracking_at_default_power": {"x": best_track_nom["x"], "res": best_track_nom["res"],
                                                       "margins": S.loop_margins(**best_track_nom["x"])}},
                "front": [{"x": r["x"], "res": r["res"]} for r in front],
                "all": [{"x": r["x"], "tag": r["tag"], "res": r["res"]} for r in rows]}
            print("servo", hn, "default", {k: round(base["res"][k], 3) for k in ("track_um", "P_rail_classB_mW")},
                  "low power", low_power["x"], {k: round(low_power["res"][k], 3) for k in ("track_um", "P_rail_classB_mW")},
                  "best track", best_track["x"], {k: round(best_track["res"][k], 3) for k in ("track_um", "P_rail_classB_mW")}, flush=True)
    save("servo", out)
    return out


# ------------------------------------------------------------------ stage: validate (test seeds, first use)
def _val_task(args):
    name, law, seed, theta, servo, kalman = args
    row = runs.score_seed(law, seed, theta=theta, tremor=True, kalman=kalman, servo=servo)
    # tails and missing ink under correction, against the rigid pen on the tremor-free writing
    return name, theta, seed, row


def _oracle_kalman_ink(args):
    name, law, seed, theta, servo = args
    row, rr = runs.score_seed(law, seed, theta=theta, tremor=True, kalman=True, servo=servo, keep=True)
    rig = rr["rigid"]
    out = {"seed": seed, "pen_downs_rigid": row["pen_downs_rigid"], "words_rigid": row["words_rigid"]}
    for key in ("oracle", "kalman", "neutral_tremor"):
        m = MT.ink_vs_rigid(rr[key], rig)
        out[key] = {k: m[k] for k in ("extra_mm", "extra_tr_mm", "extra_in_mm", "missing_mm", "missing_tr_mm", "transitions")}
    return name, theta, seed, row, out


def _diag_task(args):
    name, law, seed, servo = args
    sc0 = runs.writing(seed, 50.0, None, 5.0)
    rig = runs.rigid_run(seed, 50.0, 5.0)
    r = M.run(sc0, M.Controller(mode="neutral", **runs._ck(servo)), runs._cfg(law, servo), seed=seed + 1)
    d = MT.diag_metric(r, rig)
    return name, seed, d


def _servo_grid_task(args):
    name, p, seed, hn = args
    cfg = L.tilt_range_stop().pencil_config(overrides={"hall_noise": hn}, **S.servo_cfg_kw(p))
    ck = {"ff_ref": p.get("ff_ref", 1.0)}
    dur = 6.0
    from sim.pensim import scenarios
    sc0 = scenarios.handwriting(seed=seed, duration=dur)
    ref = M.run(sc0, M.Controller(mode="neutral", **ck), cfg, seed=seed)
    rows = []
    for f0 in (4.0, 6.0, 8.0, 10.0, 12.0):
        for amp in (0.1e-3, 0.3e-3, 0.5e-3):
            sc1 = scenarios.handwriting(seed=seed, duration=dur, tremor=sg.TremorSpec(f0=f0, amp_pk=amp))
            rn = M.run(sc1, M.Controller(mode="neutral", **ck), cfg, seed=seed)
            ro = M.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle", **ck), cfg, seed=seed)
            b, m = E.compare(rn, ref), E.compare(ro, ref)
            c = (ro["contact"] > 0) & (ro["t"] > 0.5)
            e = ro.xy("qr1") - ro.xy("q1")
            rows.append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "ratio": m["e_rms_um"] / b["e_rms_um"], "q_sat_frac": m["q_sat_frac"],
                         "P_rail_classB_mW": m["P_rail_classB_mW"], "P_rail_recovery_mW": m["P_rail_recovery_mW"],
                         "track_um": float(np.sqrt(np.mean(np.sum(e[c] ** 2, axis=1))) * 1e6)})
    return name, hn, rows


def _tilt_lag_margin(margin, theta_deg, dtheta_deg):
    """Effective front-stop position when the adaptive stop is set for theta + dtheta while the pen is at theta."""
    from sim.pencil import design as D
    P = D.Params()
    r_ring, r_b = P["skid.ring_radius"], P["refill.ball_radius"]
    p_true = D.protrusion(math.radians(theta_deg), r_ring, r_b)["p_centre"]
    p_set = D.protrusion(math.radians(theta_deg + dtheta_deg), r_ring, r_b)["p_centre"]
    return margin + (p_set - p_true)         # -s_min


def stage_validate(workers):
    bo_res = load("bo")
    servo_res = load("servo")
    final = bo_res["final"]["x"] if bo_res else dict(margin=0.3e-3)
    m_star = final["margin"]
    law_ff = L.TouchdownLaw(**final, **SB.FIXED)
    configs = {"tilt_range_stop": (L.tilt_range_stop(), None), "adaptive_0.30mm": (L.adaptive_stop(0.3e-3), None)}
    if abs(m_star - 0.3e-3) > 1e-6:
        configs[f"adaptive_{m_star * 1e3:.2f}mm"] = (L.adaptive_stop(m_star), None)
    configs["adaptive_ff"] = (law_ff, None)
    servo_pick = None
    if servo_res:
        servo_pick = servo_res["hall_1.0um"]["best_tracking_at_default_power"]["x"]
        kw = dict(S.servo_cfg_kw(servo_pick), ff_ref=servo_pick["ff_ref"])
        configs["adaptive_ff_tuned_servo"] = (law_ff, kw)
    configs["adaptive_ff_fast_axial_sensor"] = (L.TouchdownLaw(**final, **SB.FIXED, overrides={"ax_decim": 4, "ax_delay": 4}), None)
    seeds = runs.TEST_SEEDS[:1] if Q["quick"] else runs.TEST_SEEDS
    thetas = (50.0,) if Q["quick"] else (50.0, 35.0, 75.0)
    tasks = [(name, lw, s, th, sv) for name, (lw, sv) in configs.items() for th in thetas for s in seeds]
    out = {"configs": {k: {"law": v[0].as_dict(), "servo": v[1]} for k, v in configs.items()}, "seeds": list(seeds), "thetas": list(thetas)}
    with _pool(workers) as pool:
        res = list(pool.map(_oracle_kalman_ink, tasks))
        rows = {}
        for name, th, seed, row, ink in res:
            rows.setdefault(name, {}).setdefault(f"{th:g}", []).append({"row": row, "ink": ink})
        summ = {}
        for name, per_th in rows.items():
            for th, lst in per_th.items():
                agg = runs.aggregate([x["row"] for x in lst])
                den = max(sum(x["ink"]["pen_downs_rigid"] for x in lst), 1)
                for key in ("oracle", "kalman", "neutral_tremor"):
                    for k in ("extra_mm", "extra_tr_mm", "extra_in_mm", "missing_mm", "missing_tr_mm"):
                        agg[f"{key}_{k.replace('_mm', '')}_per_pd"] = sum(x["ink"][key][k] for x in lst) / den
                summ.setdefault(name, {})[th] = agg
        out["summary"] = summ
        out["rows"] = {n: {th: [x["row"] for x in lst] for th, lst in d.items()} for n, d in rows.items()}
        # the published diagnostic, exactly (5 s runs, 50 deg)
        dtasks = [(name, lw, s, sv) for name, (lw, sv) in configs.items() for s in seeds]
        dres = list(pool.map(_diag_task, dtasks))
        diag = {}
        for name, seed, d in dres:
            diag.setdefault(name, []).append(d)
        out["diag_published_metric"] = {n: {"extra_ink_mm_per_stroke": float(np.mean([d["extra_mm"] / d["pen_downs_rigid"] for d in v])),
                                            "missing_ink_mm_per_stroke": float(np.mean([d["missing_mm"] / d["pen_downs_rigid"] for d in v])),
                                            "rows": v} for n, v in diag.items()}
        # tilt-lag proxy: the adaptive stop set for theta + dtheta (a slow sweep that the trim actuator follows late)
        lag = {}
        for dth in ((-5.0, -2.0, 2.0, 5.0) if not Q["quick"] else (5.0,)):
            m_eff = _tilt_lag_margin(m_star, 50.0, dth)
            for name, lw in (("adaptive_alone", L.adaptive_stop(m_star)), ("adaptive_ff", law_ff)):
                lw2 = copy.deepcopy(lw)
                lw2.margin = m_eff
                agg, _ = runs.score(lw2, seeds, pool=pool)
                lag.setdefault(f"{dth:+g}deg", {})[name] = {"effective_margin_mm": m_eff * 1e3, "agg": agg}
                print("tilt lag", dth, name, round(m_eff * 1e3, 3), round(agg["extra_tr_mm"], 4), round(agg["missing_mm"], 4),
                      round(agg["oracle_ratio"], 4), flush=True)
        out["tilt_lag_proxy"] = lag
        # servo test grid (tilt-range stop, as the P1 study), default and tuned, 1 um and 0.3 um Hall noise
        if servo_res:
            gtasks = []
            for hn in (1e-6, 0.3e-6):
                key = f"hall_{hn * 1e6:.1f}um"
                picks = {"default": S.DEFAULT, "tuned": servo_res[key]["best_tracking_at_default_power"]["x"],
                         "low_power": servo_res[key]["lowest_power_at_default_tracking"]["x"]}
                for pname, p in picks.items():
                    for s in seeds:
                        gtasks.append((pname, p, s, hn))
            gres = list(pool.map(_servo_grid_task, gtasks))
            grid = {}
            for pname, hn, rws in gres:
                grid.setdefault(f"hall_{hn * 1e6:.1f}um", {}).setdefault(pname, []).extend(rws)
            gs = {}
            for hk, d in grid.items():
                for pname, rws in d.items():
                    cond = {}
                    for r in rws:
                        cond.setdefault(f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", []).append(r)
                    gs.setdefault(hk, {})[pname] = {
                        "mean_ratio": float(np.mean([r["ratio"] for r in rws])),
                        "mean_q_sat_frac": float(np.mean([r["q_sat_frac"] for r in rws])),
                        "mean_P_rail_classB_mW": float(np.mean([r["P_rail_classB_mW"] for r in rws])),
                        "mean_P_rail_recovery_mW": float(np.mean([r["P_rail_recovery_mW"] for r in rws])),
                        "mean_track_um": float(np.mean([r["track_um"] for r in rws])),
                        "by_condition": {c: {k: float(np.mean([r[k] for r in v])) for k in ("ratio", "q_sat_frac", "P_rail_classB_mW",
                                                                                              "P_rail_recovery_mW", "track_um")}
                                         for c, v in cond.items()}}
            out["servo_grid"] = gs
    save("validate", out)
    return out


# ------------------------------------------------------------------ stage: checks (mechanism checks behind the doc)
def stage_checks(workers):
    """Deterministic mechanism checks quoted in docs/opt_touchdown.md (SIM, P1):
    kinematics  ideal law in a 1 mm/s touchdown, noise and hysteresis off, with and without the load hand-over
    removal     pen held on the page while the stage cancels a synthetic 6 Hz estimate: the housing-slide estimate and
                the feed-forward command with kappa = 1 and kappa = 0
    dither      the pick without its dead zone and with 2 ms lead at 400 Hz (held-out training seeds): in-stroke drift"""
    from sim.pensim import scenarios
    bo_res = load("bo")
    final = bo_res["final"]["x"]
    out = {}
    th = math.radians(50.0)
    noise_off = {"hall_noise": 0.0, "sensing.axial_noise": 0.0}
    sc = runs.quasi_static_touchdown(50.0, v_down=1e-3, t_hold=0.2)
    kin = {}
    for name, lw in (("no_feedforward", L.adaptive_stop(0.3e-3)),
                     ("ideal_law", L.TouchdownLaw(margin=0.3e-3, dz=0.0, lead_s=0.0)),
                     ("ideal_law_without_handover", L.TouchdownLaw(margin=0.3e-3, dz=0.0, lead_s=0.0, handover=0))):
        r = M.run(sc, M.Controller(mode="neutral"), lw.pencil_config(overrides=noise_off, hysteresis=False), seed=1)
        s_ref = r.info["touchdown_ff"]["s_ref"] if lw.enabled else M.working_slide(th, 1.0, r.P[M.IDX["F_sp0"]], r.P[M.IDX["k_p"]], r.P[M.IDX["k_sk"]])
        d = runs.contact_point_drift(r, s_ref, 50.0)
        c = r["contact"] > 0
        dev = r["Cx"] - r["pHx"] - s_ref * math.cos(th)
        sliding = c & (r["s"] > -0.28e-3) & (r["s"] < s_ref - 5e-6)
        d.update({"sliding_median_um": float(np.median(np.abs(dev[sliding])) * 1e6) if sliding.any() else None,
                  "sliding_max_um": float(np.max(np.abs(dev[sliding])) * 1e6) if sliding.any() else None,
                  "final_dev_um": float(dev[-1] * 1e6)})
        kin[name] = d
    out["quasi_static_1mm_s"] = kin
    hold = scenarios.static_hold(duration=1.2, theta_deg=50.0)
    dhat = np.column_stack([1.5e-4 * np.sin(2 * np.pi * 6.0 * hold.t), np.zeros(len(hold.t))])
    rem = {}
    for kap in (1.0, 0.0):
        lw = L.TouchdownLaw(margin=0.3e-3, dz=20e-6, kappa=kap)
        r = M.run(M.with_estimate(hold, dhat), M.Controller(mode="external"), lw.pencil_config(), seed=2)
        sel = (r["t"] > 0.6) & (r["contact"] > 0)
        s_ref = r.info["touchdown_ff"]["s_ref"]
        rem[f"kappa_{kap:g}"] = {"stage_q1_pp_um": float(np.ptp(r["q1"][sel]) * 1e6), "slide_pp_um": float(np.ptp(r["s"][sel]) * 1e6),
                                 "housing_slide_estimate_max_dev_um": float(np.max(np.abs(r["td_sh"][sel] - s_ref)) * 1e6),
                                 "feedforward_max_um": float(np.max(np.abs(r["qff1"][sel])) * 1e6)}
    out["slide_removal_6Hz"] = rem
    seeds = SB.HOLDOUT_SEEDS[:2] if Q["quick"] else SB.HOLDOUT_SEEDS
    with _pool(workers) as pool:
        dith = {}
        for name, mod in (("pick", {}), ("no_dead_zone_lead_2ms_400Hz", {"dz": 0.0, "lead_s": 2e-3, "lp_hz": 400.0})):
            agg, _ = runs.score(L.TouchdownLaw(**dict(final, **mod), **SB.FIXED), seeds, pool=pool, tremor=False)
            dith[name] = {k: agg[k] for k in ("extra_in_mm", "extra_tr_mm", "missing_mm", "rms_nn_instroke_um")}
        out["dither"] = dith
        # the adjoint optimum of the reduced model, scored like the Bayesian pick (held-out seeds, full objective)
        adj = load("adjoint")
        if adj and "full" in adj["study"]:
            fa = adj["study"]["full"]["best"]
            x_adj = dict(final, **{k: float(np.clip(fa[k], *L.BOUNDS[k])) for k in ("gain", "kappa", "lead_s", "pre", "k_load")})
            h2h = {}
            for name, xd in (("bayesian_pick", final), ("adjoint_optimum_in_p1", x_adj)):
                lw = L.TouchdownLaw(**xd, **SB.FIXED)
                agg, _ = runs.score(lw, seeds, pool=pool)
                slow = runs.slow_descents(lw)
                ft, fr = SB.objectives(agg, bo_res["rms_ref_um"], slow)
                h2h[name] = {"x": xd, "f_tail": ft, "f_ratio": fr, "slow": slow,
                             "agg": {k: agg[k] for k in ("extra_tr_mm", "extra_tr_tight_mm", "missing_mm", "oracle_ratio",
                                                         "oracle_limit_frac_contact", "rms_nn_instroke_um")}}
            out["adjoint_vs_bayesian"] = h2h
    # early contact detection: time from contact to the feed-forward's contact state, Hall detection on (the pick)
    # against the slide alone (training seed 300 handwriting; slow descents at 10 and 1 mm/s); 2 kHz record
    def _state_delays(r):
        c = r["contact"] > 0
        tt = r["t"]
        st = r["td_state"] > 0.5
        on = np.flatnonzero(np.diff(c.astype(int)) == 1) + 1
        res = []
        for a in on:
            if tt[a] < 0.05:
                continue
            j = np.flatnonzero(st[a:a + 200])
            res.append(float((tt[a + j[0]] - tt[a]) * 1e3) if len(j) else None)
        return res
    det = {}
    for name, scn, sd in (("handwriting_seed300", runs.writing(300, 50.0, None, runs.DUR), 301),
                          ("slow_10mm_s", runs.quasi_static_touchdown(50.0, v_down=10e-3, t_hold=0.15), 7),
                          ("slow_1mm_s", runs.quasi_static_touchdown(50.0, v_down=1e-3, t_hold=0.15), 7)):
        for lab, mod in (("hall_and_slide", {}), ("slide_only", {"det_e": 0.0})):
            lw = L.TouchdownLaw(**dict(final, **mod), **SB.FIXED)
            r = M.run(scn, M.Controller(mode="neutral"), lw.pencil_config(), seed=sd)
            det.setdefault(name, {})[lab] = {"contact_to_state_ms": _state_delays(r),
                                             "note": "None: a contact that ended (or lasted 100 ms) before the state switched"}
    out["contact_detection_delay"] = det
    # contact events on training seeds 300-303 (bounces and re-contacts shorter than 30 ms)
    ev = {}
    pd_speed = []
    for th in (50.0, 35.0):
        for s_ in (300, 301, 302, 303):
            scn = runs.writing(s_, th, None, runs.DUR)
            rr = {"rigid": runs.rigid_run(s_, th, runs.DUR),
                  "adaptive_0.30mm": M.run(scn, M.Controller(mode="neutral"), L.adaptive_stop(0.3e-3).pencil_config(), seed=s_ + 1),
                  "adaptive_ff": M.run(scn, M.Controller(mode="neutral"), L.TouchdownLaw(**final, **SB.FIXED).pencil_config(), seed=s_ + 1)}
            if th == 50.0:
                # housing descent speed at each touchdown of the adaptive-stop pencil (the synthetic hand's pen-down)
                r = rr["adaptive_0.30mm"]
                cc = r["contact"] > 0
                ons = np.flatnonzero(np.diff(cc.astype(int)) == 1) + 1
                vz = np.gradient(r["pHz"], r["t"])
                pd_speed.extend(float(-vz[i] * 1e3) for i in ons if 0.05 < r["t"][i] <= 5.0)
            for key, r in rr.items():
                e = MT.contact_events(r)
                a = ev.setdefault(f"{th:g}deg", {}).setdefault(key, {"touchdowns": 0, "short_gaps": 0, "gap_ms": [], "peak_height_um": []})
                a["touchdowns"] += e["touchdowns"]
                a["short_gaps"] += len(e["short_gaps"])
                a["gap_ms"] += [g["gap_ms"] for g in e["short_gaps"]]
                a["peak_height_um"] += [g["peak_height_um"] for g in e["short_gaps"]]
    for th, d in ev.items():
        for key, a in d.items():
            a["gap_ms_max"] = float(max(a["gap_ms"])) if a["gap_ms"] else 0.0
            a["peak_height_um_max"] = float(max(a["peak_height_um"])) if a["peak_height_um"] else 0.0
    ev["pen_down_speed_mm_s"] = pd_speed
    ev["seeds"] = [300, 301, 302, 303]
    ev["definition"] = "touchdowns after 50 ms and up to 5 s; short gaps: lifts shorter than 30 ms before a touchdown"
    out["contact_events_training"] = ev
    save("checks", out)
    print("checks", json.dumps(_tolist(out))[:1500], flush=True)
    return out


# ------------------------------------------------------------------ stage: viz (3-D replay)
VIZ_NOTES = {
    "tilt_range_stop": "Front stop set for the whole 35-75 deg tilt range: the unloaded refill stands 1.34 mm proud at 50 deg, so "
                       "the ball lands early and slides up to 0.86 mm while the refill retracts; the same happens at lift.",
    "adaptive_stop": "Front stop 0.30 mm beyond the protrusion the current tilt needs (slow trim actuator from the IMU tilt): the slide "
                     "is 0.19 mm, and the stage, pushed by the sudden contact load before its servo reacts, adds most of the tail.",
    "adaptive_ff": "Adaptive stop plus the optimised stage feed-forward: while the refill rests on its stop the stage pre-deflects so "
                   "the ball lands where it writes, the contact-load bias switches on at contact, and the stage returns as the refill "
                   "retracts, driven by the measured slide with the stage's own contribution removed.",
}


def stage_viz(workers, seed=200, theta=50.0, dur=runs.DUR, window=None):
    bo_res = load("bo")
    final = bo_res["final"]["x"] if bo_res else dict(margin=0.3e-3)
    m_star = final["margin"]
    sc0 = runs.writing(seed, theta, None, dur)
    rig = M.run(sc0, M.Controller(mode="neutral"), M.PencilConfig(locked=True), seed=seed + 1)
    cases_def = [("tilt_range_stop", "Tilt-range front stop (P0.1.2)", L.tilt_range_stop()),
                 ("adaptive_stop", f"Adaptive stop alone ({0.30:.2f} mm margin)", L.adaptive_stop(0.3e-3)),
                 ("adaptive_ff", f"Adaptive stop ({m_star * 1e3:.2f} mm) + optimised feed-forward", L.TouchdownLaw(**final, **SB.FIXED))]
    runs_ = {k: M.run(sc0, M.Controller(mode="neutral"), lw.pencil_config(), seed=seed + 1) for k, _, lw in cases_def}
    # window: 3.0 s from 0.15 s before the rigid pen's first lift, so it holds two lifts and two touchdowns in mid-run
    # (seed 200: lifts at 1.55 and 3.96 s, touchdowns at 1.91 and 4.32 s)
    on = MT.transitions(rig)
    t_first = float(on[0]) if len(on) else 0.15
    c_r = rig["contact"] > 0
    lifts = rig["t"][np.flatnonzero(np.diff(c_r.astype(int)) == -1) + 1]
    lifts = lifts[lifts > t_first + 0.1]
    t_lift = float(lifts[0]) if len(lifts) else t_first
    t0 = max(0.0, t_lift - 0.15) if window is None else window[0]
    t1 = min(dur, t0 + 3.0) if window is None else window[1]
    ref = runs_["adaptive_stop"]
    rb = ref.info["static"]["r_b"]
    dec = int(round(0.01 / (ref["t"][1] - ref["t"][0])))

    def sig(x):
        return float(f"{x:.4g}")

    def arr(a, sl, scale=1.0):
        return [[sig(v * scale) for v in row] for row in np.asarray(a)[sl]]
    cases = []
    for key, label, lw in cases_def:
        r = runs_[key]
        n = min(len(r["t"]), len(rig["t"]))
        idx = np.flatnonzero((r["t"][:n] >= t0) & (r["t"][:n] <= t1))
        sl = idx[::dec]
        hous = np.column_stack([r.xy("pHx")[:n], r["pHz"][:n] - rb])
        nib = np.column_stack([r.ink()[:n], r["Cz"][:n] - rb])
        Fn = np.column_stack([r.xy("fnx")[:n], r["Nn"][:n]])
        Fs = np.column_stack([r.xy("fsx")[:n], r["Ns"][:n]])
        m = MT.ink_vs_rigid(r, rig)          # as the study: ink up to 5.0 s of the 5.2 s run (no end-truncation artefact)
        # viewer read-outs (same keys as viz_trace.json): time-matched ink error against the rigid pen while the pencil
        # is in contact, and the fraction of that time at the travel limit (as sim/pencil/evaluate.compare)
        cw = (r["contact"][:n] > 0) & (r["t"][:n] >= t0) & (r["t"][:n] <= t1)
        e_rig = r.ink()[:n] - rig.ink()[:n]
        lim = ((np.linalg.norm(r.xy("qr1")[:n], axis=1) > 0.95 * float(r.P[M.IDX["q_lim"]])) | (r["vsat"][:n] > 0) | (r["stop"][:n] > 0))
        cases.append({"key": key, "label": label, "note": VIZ_NOTES[key], "t": [sig(v - t0) for v in r["t"][:n][sl]],
                      "housing": arr(hous, sl, 1e3), "nib": arr(nib, sl, 1e3), "intended": arr(rig.ink()[:n], sl, 1e3),
                      "contact": [int(v > 0) for v in r["contact"][:n][sl]], "q": arr(r.xy("q1")[:n], sl, 1e3),
                      "F_nib": arr(Fn, sl), "F_skid": arr(Fs, sl), "F_act": arr(r.xy("Fa1")[:n], sl), "V": arr(r.xy("V1")[:n], sl),
                      "metrics": {"ink_err_rms_um": sig(float(np.sqrt(np.mean(np.sum(e_rig[cw] ** 2, axis=1)))) * 1e6),
                                  "q_sat_frac": sig(float(np.mean(lim[cw]))),
                                  "extra_ink_mm_per_pen_down": sig(m["extra_mm"] / max(m["pen_downs_rigid"], 1)),
                                  "tail_ink_mm_per_pen_down": sig(m["extra_tr_mm"] / max(m["pen_downs_rigid"], 1)),
                                  "missing_ink_mm_per_pen_down": sig(m["missing_mm"] / max(m["pen_downs_rigid"], 1)),
                                  "stage_ff_peak_mm": sig(float(np.max(np.hypot(r["qff1"], r["qff2"]))) * 1e3),
                                  "P_drive_mW": sig(float(np.mean(r["PrailB"])) * 1e3)}})
    meta = provenance.metadata(p=_pencil_params(), evidence_status="simulation (pencil model P1, synthetic handwriting, no tremor; nothing measured)",
                               seeds={"handwriting": seed}, extra={
                                   "model_version": M.MODEL_VERSION, "case_group": "Touchdown and lift: front stop and stage feed-forward (pencil model P1)",
                                   "scenario": f"sim.pensim.scenarios.handwriting(seed={seed}, duration={dur}, theta_deg={theta}, tremor=None)",
                                   "window_s": [t0, t1], "theta_deg": theta, "N_user_N": 1.0, "stage": "Q26 (2.6 mm quad)",
                                   "decimation": "2 kHz record decimated to 100 Hz", "law": final,
                                   "definitions": {
                                       "housing": "housing reference point: nominal ball centre fixed to the barrel, minus r_b in z (mm)",
                                       "nib": "ball contact point (ball centre minus r_b in z; z < 0 is paper indentation, z > 0 lifted), mm",
                                       "intended": "ink of a rigid conventional pen on the same writing (the reference of the tail metric)",
                                       "q": "stage deflection at the nib in housing axes x_H (tilt plane), y_H (sideways), mm",
                                       "F_nib": "paper on nib, page frame (fx, fy friction; fz normal), N",
                                       "F_skid": "paper on skid ring, page frame, N",
                                       "F_act": "net bender force referred to the nib, housing axes, N",
                                       "V": "centre-electrode drive voltage of each axis (0-60 V; 30 V = neutral)",
                                       "metrics": "ink_err_rms_um: time-matched distance between the pencil's and the rigid pen's ink "
                                                  "while the pencil is in contact, RMS over the window; q_sat_frac: fraction of that "
                                                  "time with the stage command at >= 95 % of the soft limit, the drive saturated or the "
                                                  "stage on its stop; extra / missing ink against the rigid pen (0.2 mm tolerance) per "
                                                  "rigid pen-down over the first 5 s of the run; tail = the part within 30 ms of a contact "
                                                  "transition"}})
    out = {"meta": meta, "units": {"length": "mm", "time": "s", "force": "N"},
           "frame": "paper: x,y on the page, z up; pen tilt theta_deg about the pen's azimuth phi_deg",
           "theta_deg": theta, "phi_deg": 0, "cases": cases}
    provenance.write_json(os.path.join(OUT, "viz_touchdown.json"), out)
    # 2 kHz excerpts around the rigid pen's first touchdown and first lift, for fig_td_event.png
    offs = np.flatnonzero(np.diff((rig["contact"] > 0).astype(int)) == -1) + 1
    t_on = t_first
    t_off = float(rig["t"][offs[offs > np.searchsorted(rig["t"], t_on + 0.1)][0]]) if len(offs) else t_on + 1.0
    ev = {}
    for key, _, lw in cases_def:
        r = runs_[key]
        s_ref = r.info["touchdown_ff"]["s_ref"] if lw.enabled else M.working_slide(math.radians(theta), 1.0, r.P[M.IDX["F_sp0"]],
                                                                                    r.P[M.IDX["k_p"]], r.P[M.IDX["k_sk"]])
        for name, (a, b) in (("touchdown", (t_on - 0.02, t_on + 0.05)), ("lift", (t_off - 0.03, t_off + 0.03))):
            sel = (r["t"] >= a) & (r["t"] <= b)
            ev.setdefault(name, {"t0": a})[key] = {
                "t_ms": ((r["t"][sel] - a) * 1e3).tolist(),
                "ink_minus_working_um": ((r["Cx"][sel] - r["pHx"][sel] - s_ref * math.cos(math.radians(theta))) * 1e6).tolist(),
                "contact": (r["contact"][sel] > 0).astype(int).tolist(), "q1_um": (r["q1"][sel] * 1e6).tolist(),
                "qff1_um": (r["qff1"][sel] * 1e6).tolist(), "slide_um": (r["s"][sel] * 1e6).tolist(),
                "housing_height_um": ((r["pHz"][sel] - rb) * 1e6).tolist(), "t_rigid_event_ms": ((t_on if name == "touchdown" else t_off) - a) * 1e3}
    save("viz_event", {"seed": seed, "theta_deg": theta, "events": ev})
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--quick", action="store_true", help="tiny budgets (smoke run); writes *_quick caches only")
    ap.add_argument("--adjoint-precomputed", default="", help="comma-separated reduced.adjoint_study JSON files to merge")
    a = ap.parse_args()
    Q["quick"] = a.quick
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    t0 = time.time()
    runs.warm()
    for st in stages:
        ts = time.time()
        print(f"=== stage {st}", flush=True)
        if st == "adjoint":
            stage_adjoint(a.workers, [p for p in a.adjoint_precomputed.split(",") if p] or None)
        elif st == "baseline":
            stage_baseline(a.workers)
        elif st == "bo":
            stage_bo(a.workers)
        elif st == "servo":
            stage_servo(a.workers)
        elif st == "validate":
            stage_validate(a.workers)
        elif st == "checks":
            stage_checks(a.workers)
        elif st == "viz":
            if not Q["quick"]:
                stage_viz(a.workers)
        elif st == "figures":
            if not Q["quick"]:
                from opt.touchdown import figures
                figures.make_all()
        elif st == "report":
            if not Q["quick"]:
                from opt.touchdown import report
                report.write_all()
        print(f"=== stage {st} done in {time.time() - ts:.0f} s", flush=True)
    print("total", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
