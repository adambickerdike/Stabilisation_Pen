#!/usr/bin/env python3
"""Uncertainty and coverage sweeps of the coupled simulator (model M1), TEST seeds.

1. Tremor frequency x amplitude grid (4-12 Hz x 0.15/0.3/0.6 mm peak) for
   powered neutral, Kalman (balanced, assertive; frequency-gated), band-pass
   and oracle, over TEST seeds.  Estimator parameters are frozen
   (results/sim/estimator_selection.json).
2. Monte Carlo over declared parameter ranges (config/parameters.yaml: hand
   impedance, friction, normal force, altitude, paper stiffness, axial
   stiffness, actuator constants, sensor delays and noise) at 9 Hz, 0.3 mm.
   Ranges are exploratory declarations, not population distributions.
3. Failure cases: optical dropout, low battery, actuator power loss in
   contact, frozen stage sensor, overload (2 N at 35 deg), blocked stage,
   degraded optical noise.
Evidence status: SIMULATION on synthetic signals.
Outputs: results/sim/sweeps/*.json|csv|png.  Run: python3 sim/run_sweeps.py [--quick]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import bench, evaluate, harness, model, scenarios  # noqa: E402
from stabpen import params as sp_params  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim", "sweeps")
F0S = (4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0)
AMPS = (1.5e-4, 3.0e-4, 6.0e-4)
MC_KEYS = ["hand.grip_stiffness", "hand.grip_damping", "hand.mass", "hand.arm_stiffness", "hand.arm_damping",
           "hand.normal_stiffness", "writing.mu_eff", "writing.normal_force", "writing.tilt_deg",
           "writing.paper_stiffness", "stage.axial_k", "stage.k_tip", "actuator.Kf", "actuator.R20",
           "sensing.opt_delay", "sensing.opt_noise", "sensing.imu_delay", "sensing.hall_noise_tip"]


def frozen():
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
    return {"kf_bal": ("kfosc", sel["kfosc"]["selected"]["params"]),
            "kf_asr": ("kfosc", sel["kfosc"]["selected_assertive"]["params"]),
            "bpf": ("bpf", sel["bpf"]["selected"]["params"]), "oracle": ("oracle", {})}


def grid(seeds, workers):
    fz = frozen()
    cases = []
    for s in seeds:
        for f in F0S:
            for a in AMPS:
                for name, (mode, kw) in fz.items():
                    cases.append(dict(seed=s, f0=f, amp=a, mode=mode, ctrl=kw, tag=name, distortion=False))
    rows = harness.run_cases(cases, workers)
    # intended-path distortion depends only on (seed, controller)
    dcases = [dict(seed=s, f0=6.0, amp=3e-4, mode=mode, ctrl=kw, tag=name, distortion=True)
              for s in seeds for name, (mode, kw) in fz.items() if name != "oracle"]
    drows = harness.run_cases(dcases, workers)
    dist = {}
    for r in drows:
        dist.setdefault(r["tag"], []).append(r["distortion_um"])
    return rows, {k: float(np.mean(v)) for k, v in dist.items()}


def _mc_one(args):
    i, sample, seed = args
    ov = dict(sample)
    th = ov.pop("writing.tilt_deg")
    N0 = ov.pop("writing.normal_force")
    fz = frozen()
    out = {"i": i, "theta": th, "N0": N0, **{k: v for k, v in sample.items()}}
    tr = sg.TremorSpec(f0=9.0, amp_pk=3e-4)
    sc0 = scenarios.handwriting(seed=seed, duration=5.0, theta_deg=th, N0=N0)
    sc1 = scenarios.handwriting(seed=seed, duration=5.0, tremor=tr, theta_deg=th, N0=N0)
    rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=seed)
    d, rn = bench.housing_disturbance(sc1, rs, overrides=ov, seed=seed)
    base = evaluate.compare(rn, rs)
    out["neutral_e_um"] = base["e_rms_um"]
    out["P_cu_neutral_W"] = base["P_cu_mean_W"]
    out["T_coil_max_C"] = base["T_coil_max_C"]
    out["frac_vsat_neutral"] = base["frac_vsat"]
    for name in ("kf_asr", "oracle"):
        mode, kw = fz[name]
        scn = bench.with_disturbance(sc1, d) if name == "oracle" else sc1
        r = model.run(scn, model.Controller(mode=mode, **kw), overrides=ov, seed=seed)
        m = evaluate.compare(r, rs)
        out[f"{name}_ratio"] = m["e_rms_um"] / base["e_rms_um"]
        out[f"{name}_Nmod"] = m["N_mod_rms"]
        out[f"{name}_near_limit"] = m["frac_near_limit"]
        out[f"{name}_stop"] = m["frac_stop"]
    return out


def monte_carlo(n, workers, seed0=7):
    p = sp_params.load()
    rng = np.random.default_rng(seed0)
    jobs = []
    for i in range(n):
        s = p.sample(MC_KEYS, rng)
        jobs.append((i, s, harness.TEST_SEEDS[i % len(harness.TEST_SEEDS)]))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_mc_one, jobs, chunksize=2))


def failure_cases():
    fz = frozen()
    mode, kw = fz["kf_asr"]
    tr = sg.TremorSpec(f0=9.0, amp_pk=3e-4)
    seed = harness.TEST_SEEDS[0]
    sc0 = scenarios.handwriting(seed=seed, duration=6.0)
    sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=tr)
    rs = model.run(sc0, model.Controller(mode="neutral"))
    out = {}

    def jump_at(r, t_fail, win=0.05):
        t = r["t"]
        i0 = np.searchsorted(t, t_fail)
        i1 = np.searchsorted(t, t_fail + win)
        tip = r.xy("tipx")
        con = r["contact"] > 0
        seg = tip[i0:i1][con[i0:i1]]
        if len(seg) < 2:
            return float("nan")
        return float(np.max(np.linalg.norm(seg - seg[0], axis=1)) * 1e6)

    base = evaluate.compare(model.run(sc1, model.Controller(mode=mode, **kw)), rs)
    out["reference_kf_asr"] = {"e_rms_um": base["e_rms_um"]}
    # F1 optical dropout 0.3 s
    ok = np.ones(len(sc1.t), np.uint8)
    ok[(sc1.t > 2.5) & (sc1.t < 2.8)] = 0
    s_drop = scenarios.handwriting(seed=seed, duration=6.0, tremor=tr, opt_ok=ok)
    r = model.run(s_drop, model.Controller(mode=mode, **kw))
    m = evaluate.compare(r, rs)
    g = r["conf"]
    t = r["t"]
    out["F1_optical_dropout_0p3s"] = {"e_rms_um": m["e_rms_um"], "authority_min_during": float(g[(t > 2.55) & (t < 2.8)].min()),
                                      "authority_after_1s": float(g[(t > 3.8) & (t < 3.9)].mean())}
    # F2 low battery
    for vb in (3.3, 3.0, 2.8):
        r = model.run(sc1, model.Controller(mode=mode, **kw), overrides={"electrical.v_bat_nom": vb})
        m = evaluate.compare(r, rs)
        out[f"F2_vbat_{vb}"] = {"e_rms_um": m["e_rms_um"], "frac_vsat": m["frac_vsat"]}
    # F3 actuator power loss in contact at t = 3.0 s (coils open)
    r = model.run(sc1, model.Controller(mode=mode, **kw), overrides={"fail_type": 1, "fail_time": 3.0})
    out["F3_power_loss_in_contact"] = {"ink_jump_max_um_50ms": jump_at(r, 3.0), "frac_stop_after": float(np.mean(r["stop"][r["t"] > 3.05]))}
    # F4 frozen stage sensor at t = 3.0 s
    r = model.run(sc1, model.Controller(mode=mode, **kw), overrides={"fail_type": 3, "fail_time": 3.0})
    out["F4_stage_sensor_frozen"] = {"ink_jump_max_um_50ms": jump_at(r, 3.0),
                                     "frac_stop_after": float(np.mean(r["stop"][r["t"] > 3.05])),
                                     "i_peak_after_A": float(np.max(np.abs(r.xy("i1")[r["t"] > 3.0])))}
    # F5 overload 2 N at 35 deg
    s_hi = scenarios.handwriting(seed=seed, duration=6.0, tremor=tr, theta_deg=35.0, N0=2.0)
    rs_hi = model.run(scenarios.handwriting(seed=seed, duration=6.0, theta_deg=35.0, N0=2.0), model.Controller(mode="neutral"))
    r = model.run(s_hi, model.Controller(mode=mode, **kw))
    m = evaluate.compare(r, rs_hi)
    out["F5_overload_2N_35deg"] = {"e_rms_um": m["e_rms_um"], "i_peak_A": m["i_peak_A"], "P_cu_mean_W": m["P_cu_mean_W"],
                                   "T_coil_max_C": m["T_coil_max_C"], "frac_stop": m["frac_stop"]}
    # F6 blocked stage (stop at 0.1 mm)
    r = model.run(sc1, model.Controller(mode=mode, **kw), overrides={"stage.travel_tip_mech": 1.0e-4})
    m = evaluate.compare(r, rs)
    out["F6_blocked_stage_0p1mm"] = {"e_rms_um": m["e_rms_um"], "frac_stop": m["frac_stop"], "i_peak_A": m["i_peak_A"]}
    # F7 degraded optical noise x10
    r = model.run(sc1, model.Controller(mode=mode, **kw), overrides={"sensing.opt_noise": 3.0e-5})
    m = evaluate.compare(r, rs)
    out["F7_optical_noise_30um"] = {"e_rms_um": m["e_rms_um"]}
    return out


def plots(rows, dist, mc):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 3.8), sharey=True)
    names = [("kf_bal", "Kalman balanced"), ("kf_asr", "Kalman assertive"), ("bpf", "band-pass"), ("oracle", "oracle bound")]
    for ax, amp in zip(axs, AMPS):
        for j, (tag, lab) in enumerate(names):
            mean, lo, hi = [], [], []
            for f in F0S:
                v = np.array([r["ratio"] for r in rows if r["tag"] == tag and r["f0"] == f and r["amp"] == amp])
                mean.append(v.mean()); lo.append(np.percentile(v, 10)); hi.append(np.percentile(v, 90))
            c = plotstyle.SERIES[j]
            ax.fill_between(F0S, lo, hi, color=c, alpha=0.12, lw=0)
            ax.plot(F0S, mean, color=c, label=lab)
        ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
        ax.set_title(f"tremor amplitude {amp*1e3:.2f} mm peak", loc="left", fontsize=10)
        ax.set_xlabel("Tremor frequency (Hz)")
    axs[0].set_ylabel("Ink error / powered-neutral error")
    axs[0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Where assistance helps: residual vs tremor frequency (mean, 10-90% band over test seeds)", x=0.01, ha="left", fontsize=11)
    plotstyle.stamp(fig, "simulation", "synthetic handwriting; distortion (um): " + ", ".join(f"{k} {v:.0f}" for k, v in dist.items()))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_ratio_vs_frequency.png"))
    plt.close(fig)
    if mc:
        fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
        th = np.array([r["theta"] for r in mc]); N = np.array([r["N0"] for r in mc])
        P = np.array([r["P_cu_neutral_W"] for r in mc])
        sc = axs[0].scatter(th, P, c=N, cmap="Blues", s=22, edgecolors=plotstyle.SURFACE, linewidths=0.8, vmin=0, vmax=2)
        axs[0].set_xlabel("Altitude θ (deg)"); axs[0].set_ylabel("Mean copper loss while writing (W)")
        axs[0].set_title("Holding power across the declared envelope", loc="left", fontsize=10)
        fig.colorbar(sc, ax=axs[0], label="normal force N (N)")
        for j, key in enumerate(("oracle_ratio", "kf_asr_ratio")):
            axs[1].hist([r[key] for r in mc], bins=25, color=plotstyle.SERIES[j], alpha=0.7, label=key.replace("_ratio", ""))
        axs[1].axvline(1.0, color=plotstyle.MUTED, lw=1.0)
        axs[1].set_xlabel("Ink error / powered-neutral error (9 Hz, 0.3 mm)"); axs[1].set_ylabel("Monte Carlo samples")
        axs[1].set_title("Sensitivity of benefit to uncertain parameters", loc="left", fontsize=10)
        axs[1].legend()
        plotstyle.stamp(fig, "simulation", "exploratory parameter ranges from config/parameters.yaml; not population data")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "fig_monte_carlo.png"))
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    seeds = harness.TEST_SEEDS[:3] if a.quick else harness.TEST_SEEDS
    rows, dist = grid(seeds, a.workers)
    mc = monte_carlo(24 if a.quick else 160, a.workers)
    fails = failure_cases()
    with open(os.path.join(OUT, "grid.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, "monte_carlo.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mc[0].keys()))
        w.writeheader(); w.writerows(mc)
    summ = {}
    for tag in ("kf_bal", "kf_asr", "bpf", "oracle"):
        for f in F0S:
            v = [r["ratio"] for r in rows if r["tag"] == tag and r["f0"] == f]
            summ[f"{tag}@{f:g}"] = {"mean": float(np.mean(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))}
    mc_summ = {k: {"median": float(np.median([r[k] for r in mc])), "p10": float(np.percentile([r[k] for r in mc], 10)),
                   "p90": float(np.percentile([r[k] for r in mc], 90))}
               for k in ("oracle_ratio", "kf_asr_ratio", "P_cu_neutral_W", "T_coil_max_C", "oracle_Nmod", "oracle_near_limit", "frac_vsat_neutral")}
    meta = provenance.metadata("simulation (synthetic signals; exploratory parameter ranges)",
                               seeds={"test": list(seeds), "mc_seed": 7},
                               extra={"elapsed_s": time.time() - t0, "mc_keys": MC_KEYS, "quick": a.quick})
    provenance.write_json(os.path.join(OUT, "summary.json"), {"meta": meta, "grid_summary": summ, "distortion_um": dist,
                                                              "monte_carlo_summary": mc_summ, "failure_cases": fails})
    plots(rows, dist, mc)
    print(json.dumps({"distortion_um": dist, "mc": mc_summ, "failures": fails}, indent=1, default=str)[:6000])
    for k, v in summ.items():
        print(k, {kk: round(vv, 3) for kk, vv in v.items()})


if __name__ == "__main__":
    main()
