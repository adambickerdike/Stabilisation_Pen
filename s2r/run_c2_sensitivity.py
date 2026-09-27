#!/usr/bin/env python3
"""C2 part B: local sensitivity of the B09-cell outcomes to every hidden-plant parameter,
and the parameter accuracy a twin needs.

Central differences in ln(parameter) (x1.25 and /1.25) about the nominal plant, under
the unchanged nominal firmware (s2r.twin.shim), common random numbers (same seeds and
noise for every run). S = d outcome / d ln(theta). From S:
  * required accuracy of each parameter alone for a ratio prediction within +-0.05
    (half the AC-B09-03 band) or +-5 % for distortion, neutral error and hold power;
  * a linear attribution of each C2 plant's calibration gap to parameter groups
    (checked against the directly simulated gap in c2_twin.json when present);
  * a comparison of the ranking with results/sim/mc_sensitivity.json (Spearman
    rank correlations over the 160-sample Monte Carlo, which varied use conditions too).

Evidence status: SIMULATION + CALCULATION (finite differences of simulation outputs).
Outputs: results/s2r/c2_sensitivity.json, fig_c2_sensitivity.png
Run: python3 -m s2r.run_c2_sensitivity [--quick]     (about 3 min on 2 processes)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time

import numpy as np

import s2r  # noqa: F401
from s2r import common, twin
from s2r import truth as tr
from sim.pensim import harness

OUT = ["oracle_ratio@6Hz", "oracle_ratio@9Hz", "kfosc_ratio@6Hz", "kfosc_ratio@9Hz", "kf_distortion_um",
       "neutral_e_um@6Hz", "neutral_e_um@9Hz", "static_hold_W"]
TOL = {k: ("abs", 0.05) for k in OUT[:4]}
TOL.update({k: ("rel", 0.05) for k in OUT[4:]})
STEP = math.log(1.25)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    seeds = harness.TEST_SEEDS[:2] if a.quick else harness.TEST_SEEDS[:6]
    keys = [k for g in tr.GROUPS.values() for k in g]
    if a.quick:
        keys = ["writing.mu_eff", "actuator.Kf"]
    nominal = twin.nominal_plant()
    t0 = time.time()
    base = twin.evaluate_plant(nominal, seeds=seeds, workers=a.workers, device=False)
    S = {}
    for k in keys:
        res = {}
        for sgn in (+1, -1):
            pv = dict(nominal)
            pv[k] = nominal[k] * math.exp(sgn * STEP)
            res[sgn] = twin.evaluate_plant(pv, seeds=seeds, workers=a.workers, device=False)
        S[k] = {o: (res[1][o] - res[-1][o]) / (2 * STEP) for o in OUT}
        S[k]["_curvature"] = {o: (res[1][o] - 2 * base[o] + res[-1][o]) / STEP ** 2 for o in OUT}
        print(k, f"{time.time() - t0:.0f} s", {o: round(S[k][o], 3) for o in OUT[:4]}, flush=True)
    req = {}
    for k in keys:
        req[k] = {}
        for o in OUT:
            kind, tol = TOL[o]
            s = abs(S[k][o]) if kind == "abs" else abs(S[k][o]) / max(abs(base[o]), 1e-12)
            req[k][o] = float(tol / s) if s > 1e-9 else None      # relative parameter accuracy
    group_of = {k: g for g, ks in tr.GROUPS.items() for k in ks}
    # RSS budget: the tolerance shared equally among the identified parameters that matter
    ident_keys = [k for k in keys if group_of[k] in tr.IDENTIFIED_GROUPS]
    budget = {}
    for o in OUT:
        kind, tol = TOL[o]
        sens = {k: (abs(S[k][o]) if kind == "abs" else abs(S[k][o]) / max(abs(base[o]), 1e-12)) for k in ident_keys}
        act = [k for k, v in sens.items() if v * 0.05 > 0.02 * tol]     # matters at a 5 % parameter error
        if act:
            share = tol / math.sqrt(len(act))
            budget[o] = {k: float(share / sens[k]) for k in act}
    # comparison with the Monte Carlo ranking
    mc = json.load(open(os.path.join(s2r.ROOT, "results", "sim", "mc_sensitivity.json")))["outcomes"]
    comp = {}
    for o_mc, o in (("oracle_ratio", "oracle_ratio@9Hz"), ("kf_asr_ratio", "kfosc_ratio@9Hz")):
        rows = []
        for p, v in mc[o_mc]["by_parameter"].items():
            if p in S:
                rows.append((p, v["rho"], S[p][o]))
        if len(rows) > 2:
            from scipy import stats
            comp[o] = {"n": len(rows), "spearman_abs": float(stats.spearmanr([abs(r[1]) for r in rows],
                                                                              [abs(r[2]) for r in rows]).statistic),
                       "rows": [{"param": r[0], "mc_rho": r[1], "local_S": r[2]} for r in rows]}
    # linear attribution of the C2 gaps (if c2_twin.json exists)
    attrib = None
    c2p = os.path.join(s2r.RESULTS, "c2_twin.json")
    c1p = os.path.join(s2r.RESULTS, "c1_identification.json")
    if os.path.exists(c2p) and os.path.exists(c1p) and not a.quick:
        c2 = json.load(open(c2p))
        c1 = json.load(open(c1p))
        truths = {t["id"]: t["values"] for t in c1["truths_revealed"]}
        attrib = []
        for ent in c2["per_plant"]:
            tv = truths[ent["id"]]
            row = {"id": ent["id"], "groups": {}}
            for o in OUT[:4]:
                by_g = {}
                for k in keys:
                    d = math.log(tv[k] / nominal[k]) if tv.get(k, 0) > 0 else 0.0
                    by_g[group_of[k]] = by_g.get(group_of[k], 0.0) + S[k][o] * d
                row["groups"][o] = {"linear_truth_minus_nominal": by_g,
                                    "linear_sum": float(sum(by_g.values())),
                                    "simulated_truth_minus_nominal": float(ent["truth"][o] - c2["nominal"][o])}
            attrib.append(row)
    payload = {"step_ln": STEP, "seeds": list(seeds), "base": {o: base[o] for o in OUT}, "S": S,
               "required_rel_accuracy_single": req, "rss_budget_identified": budget, "tolerances": TOL,
               "mc_rank_comparison": comp, "gap_attribution": attrib, "elapsed_s": time.time() - t0}
    path = common.write_result("c2_sensitivity", payload,
                               "SIMULATION + CALCULATION (central differences in ln parameter, common random numbers)",
                               seeds={"test": list(seeds)})
    plot(S, keys, group_of)
    print(path, f"{time.time() - t0:.0f} s")


def plot(S, keys, group_of):
    from stabpen import plotstyle
    outs = ["oracle_ratio@9Hz", "kfosc_ratio@9Hz", "kfosc_ratio@6Hz"]
    order = sorted(keys, key=lambda k: -max(abs(S[k][o]) for o in outs))
    fig, axs = common.figure(1, 3, figsize=(13.5, 6.0), sharey=True)
    gcol = {g: plotstyle.SERIES[i] for i, g in enumerate(tr.GROUPS)}
    y = np.arange(len(order))
    for ax, o in zip(axs, outs):
        v = [S[k][o] for k in order]
        ax.barh(y, v, color=[gcol[group_of[k]] for k in order], height=0.65)
        ax.axvline(0, color=plotstyle.INK2, lw=0.8)
        for x in (-0.05 / STEP * STEP, 0.05):
            pass
        ax.set_title(f"d({o}) / d ln(parameter)", loc="left", fontsize=9.5)
        ax.set_xlabel("change in ratio per unit ln(parameter)")
    axs[0].set_yticks(y, order, fontsize=7.5)
    axs[0].invert_yaxis()
    from matplotlib.patches import Patch
    axs[-1].legend(handles=[Patch(color=c, label=g) for g, c in gcol.items()], fontsize=7.5, loc="lower right")
    common.save_figure(fig, "fig_c2_sensitivity", "simulation",
                       "central differences x1.25 about the nominal plant, nominal firmware, 6 test seeds, B09 primary cells")


if __name__ == "__main__":
    main()
