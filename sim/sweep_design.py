#!/usr/bin/env python3
"""Design sweeps behind DEC-006 (stiff axial path) and COR-04 (compliance-aware Jacobian).

Evidence status: SIMULATION (model M1, synthetic handwriting, tuning seeds).

1. Axial-path stiffness k_ax: device distortion of the powered-neutral pen
   against a rigid pen (no tremor), and, with 9 Hz / 0.3 mm tremor under the
   oracle controller, the residual ratio, normal-force modulation in the
   3-15 Hz band and contact transitions.  A soft suspension lets writing-force
   changes move the ink (the ball slides s cos(theta) along the tilt
   direction); a stiff one converts tilt-coupled stage motion into normal-force
   modulation.
2. Jacobian: oracle residual with the textbook paper-plane Jacobian
   (gamma = 1, J_t1 = 1/sin theta) against the compliance-aware one
   (gamma from the suspension/hand compliance ratio), at 35/50/65 deg.

Outputs results/sim/design_sweeps.json and fig_axial_sweep.png.
Run: python3 sim/sweep_design.py
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import bench, evaluate, harness, model, scenarios  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

KAX = (300.0, 700.0, 1000.0, 2000.0, 4000.0, 8000.0)
SEEDS = harness.TUNING_SEEDS[:4]
TR = sg.TremorSpec(f0=9.0, amp_pk=3e-4)


def _trans(r):
    c = (r["contact"] > 0).astype(int)
    return int(np.sum(np.diff(c) != 0))


def axial_case(args):
    kax, seed = args
    ov = {"stage.axial_k": kax}
    sc0 = scenarios.handwriting(seed=seed, duration=6.0)
    sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=TR)
    rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    rr = model.run(sc0, model.Controller(mode="rigid"), overrides=ov, seed=seed)
    dd = bench.device_distortion(rs, rr)
    d, rn = bench.housing_disturbance(sc1, rs, overrides=ov, seed=seed)
    base = evaluate.compare(rn, rs)
    ro = model.run(bench.with_disturbance(sc1, d), model.Controller(mode="oracle"), overrides=ov, seed=seed)
    m = evaluate.compare(ro, rs)
    return {"k_ax": kax, "seed": seed, "device_distortion_um": dd.get("detrended_rms_um", float("nan")),
            "oracle_ratio": m["e_rms_um"] / base["e_rms_um"], "oracle_Nmod_N": m["N_mod_rms"],
            "neutral_Nmod_N": base["N_mod_rms"], "oracle_transitions": _trans(ro), "neutral_transitions": _trans(rn),
            "oracle_ink_gap_frac": m["ink_gap_frac"]}


def jac_case(args):
    theta, seed, gamma = args
    sc0 = scenarios.handwriting(seed=seed, duration=6.0, theta_deg=theta)
    sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=TR, theta_deg=theta)
    rs = model.run(sc0, model.Controller(mode="neutral"), seed=seed)
    d, rn = bench.housing_disturbance(sc1, rs, seed=seed)
    base = evaluate.compare(rn, rs)["e_rms_um"]
    ro = model.run(bench.with_disturbance(sc1, d), model.Controller(mode="oracle", gamma_acc=gamma), seed=seed)
    return {"theta": theta, "seed": seed, "gamma": "computed" if gamma is None else gamma,
            "oracle_ratio": evaluate.compare(ro, rs)["e_rms_um"] / base}


def main():
    with ProcessPoolExecutor(3) as ex:
        ax = list(ex.map(axial_case, [(k, s) for k in KAX for s in SEEDS]))
        jac = list(ex.map(jac_case, [(th, s, g) for th in (35.0, 50.0, 65.0) for s in SEEDS for g in (1.0, None)]))
    summ_ax = []
    for k in KAX:
        rows = [r for r in ax if r["k_ax"] == k]
        summ_ax.append({key: float(np.mean([r[key] for r in rows])) for key in rows[0] if key not in ("seed",)})
    summ_j = {}
    for th in (35.0, 50.0, 65.0):
        for g in (1.0, "computed"):
            v = [r["oracle_ratio"] for r in jac if r["theta"] == th and r["gamma"] == g]
            summ_j[f"theta{th:g}_gamma_{g}"] = float(np.mean(v))
    meta = provenance.metadata("simulation (synthetic handwriting; tuning seeds)", seeds={"tuning": list(SEEDS)})
    provenance.write_json(os.path.join(ROOT, "results", "sim", "design_sweeps.json"),
                          {"meta": meta, "axial_sweep": summ_ax, "jacobian": summ_j, "axial_rows": ax, "jacobian_rows": jac})
    for r in summ_ax:
        print({k: round(v, 3) for k, v in r.items()})
    print(summ_j)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.6))
    ks = [r["k_ax"] for r in summ_ax]
    axs[0].plot(ks, [r["device_distortion_um"] for r in summ_ax], color=plotstyle.SERIES[0])
    axs[0].plot(ks, [r["device_distortion_um"] for r in summ_ax], **plotstyle.marker_kw(plotstyle.SERIES[0]))
    axs[0].set_xscale("log"); axs[0].set_xlabel("Axial-path stiffness k_ax (N/m)")
    axs[0].set_ylabel("Device distortion vs rigid pen (um RMS)")
    axs[0].set_title("Writing-force changes move the ink when soft", loc="left", fontsize=10)
    axs[1].plot(ks, [r["oracle_Nmod_N"] * 1e3 for r in summ_ax], color=plotstyle.SERIES[1])
    axs[1].plot(ks, [r["oracle_Nmod_N"] * 1e3 for r in summ_ax], **plotstyle.marker_kw(plotstyle.SERIES[1]))
    axs[1].set_xscale("log"); axs[1].set_xlabel("Axial-path stiffness k_ax (N/m)")
    axs[1].set_ylabel("Normal-force modulation 3-15 Hz (mN RMS)")
    axs[1].set_title("...and correction modulates the force when stiff", loc="left", fontsize=10)
    plotstyle.stamp(fig, "simulation", "oracle controller, 9 Hz 0.3 mm tremor, theta 50 deg, N 1 N; mean of 4 tuning seeds")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "results", "sim", "fig_axial_sweep.png"))


if __name__ == "__main__":
    main()
