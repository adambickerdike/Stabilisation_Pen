#!/usr/bin/env python3
"""Axial-suspension placement: whole lever slides (kappa_s = 0) vs refill slides in the
carrier (kappa_s = 1, lever-arm change compensated from the measured slide).

Evidence status: SIMULATION (model M1, tuning seeds 100-103, theta 35/50 deg).
Companion to mechanics/tolerance_analysis.py, which shows kappa_s = 0 closes the
actuator gap (DEC-007 revision).  Output results/sim/kappa_compare.json.
Run: python3 sim/diag_kappa.py
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from concurrent.futures import ProcessPoolExecutor
from sim.pensim import bench, evaluate, harness, model, scenarios
from stabpen import signals as sg
sel = json.load(open(os.path.join(ROOT, 'results', 'sim', 'estimator_selection.json')))["results"]
KB = sel["kfosc"]["selected"]["params"]; KA = sel["kfosc"]["selected_assertive"]["params"]
CASES = {"kappa0_m1.2g": {"stage.kappa_s": 0.0, "stage.axial_mass": 1.2e-3, "stage.travel_tip_mech": 0.65e-3},
         "kappa1_m0.6g": {"stage.kappa_s": 1.0, "stage.axial_mass": 0.6e-3, "stage.travel_tip_mech": 0.65e-3},
         "kappa1_m0.6g_travel0.60": {"stage.kappa_s": 1.0, "stage.axial_mass": 0.6e-3, "stage.travel_tip_mech": 0.60e-3}}
def run(args):
    name, seed, theta = args
    ov = CASES[name]
    TR = sg.TremorSpec(f0=9.0, amp_pk=3e-4)
    sc0 = scenarios.handwriting(seed=seed, duration=6.0, theta_deg=theta)
    sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=TR, theta_deg=theta)
    rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    rr = model.run(sc0, model.Controller(mode="rigid"), overrides=ov, seed=seed)
    dd = bench.device_distortion(rs, rr)["detrended_rms_um"]
    d, rn = bench.housing_disturbance(sc1, rs, overrides=ov, seed=seed)
    base = evaluate.compare(rn, rs)["e_rms_um"]
    ro = evaluate.compare(model.run(bench.with_disturbance(sc1, d), model.Controller(mode="oracle"), overrides=ov, seed=seed), rs)
    ka = evaluate.compare(model.run(sc1, model.Controller(mode="kfosc", **KA), overrides=ov, seed=seed), rs)["e_rms_um"] / base
    kd = evaluate.compare(model.run(sc0, model.Controller(mode="kfosc", **KB), overrides=ov, seed=seed), rs)["e_rms_um"]
    return name, theta, {"device_distortion_um": dd, "oracle_ratio": ro["e_rms_um"] / base, "oracle_frac_stop": ro["frac_stop"],
                         "kf_asr_ratio": ka, "kf_bal_distortion_um": kd}
if __name__ == "__main__":
    jobs = [(c, s, th) for c in CASES for s in harness.TUNING_SEEDS[:4] for th in (35.0, 50.0)]
    agg = {}
    with ProcessPoolExecutor(3) as ex:
        for name, th, r in ex.map(run, jobs):
            agg.setdefault((name, th), []).append(r)
    summ = {f"{name}_theta{th:g}": {k: float(np.mean([r[k] for r in rows])) for k in rows[0]} for (name, th), rows in sorted(agg.items())}
    from stabpen import provenance
    meta = provenance.metadata("simulation", seeds={"tuning": list(harness.TUNING_SEEDS[:4])})
    provenance.write_json(os.path.join(ROOT, "results", "sim", "kappa_compare.json"), {"meta": meta, "cases": CASES, "results": summ})
    for k, v in summ.items():
        print(k, {kk: round(vv, 3) for kk, vv in v.items()})
