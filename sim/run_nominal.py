#!/usr/bin/env python3
"""Nominal benchmark of the coupled pen simulator (model M1) on TEST seeds.

Scenario: synthetic handwriting (sigma-lognormal), altitude 50 deg, N = 1 N,
tremor 0.3 mm peak at 6 and 9 Hz, literature two-stage hand impedance.
Controllers (estimator parameters frozen from results/sim/estimator_selection.json,
selected on TUNING seeds only):
  rigid      ordinary pen (no stage, no suspension)
  neutral    same pen, powered, stage held at neutral (matched comparator)
  bpf        band-pass disturbance estimate (selected band)
  kf_bal     Kalman intent+oscillator, balanced selection (lambda = 1)
  kf_asr     Kalman intent+oscillator, assertive selection (lambda = 0.3)
  oracle     instantaneous true housing disturbance (mechanical/servo bound)
Also: intended-feature distortion on the feature course (no tremor), guided
mode (known path) on the feature course with tremor, and a static load check.
Evidence status: SIMULATION on synthetic signals; not human or bench data.
Outputs: results/sim/nominal/{metrics.json, metrics.csv, traces_*.npz, fig_*.png}
Run: python3 sim/run_nominal.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import bench, evaluate, harness, model, scenarios  # noqa: E402
from stabpen import contact, plotstyle, provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim", "nominal")
SEEDS = harness.TEST_SEEDS[:4]
F0S = (6.0, 9.0)
AMP = 3e-4


def frozen():
    sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
    return {"bpf": sel["bpf"]["selected"]["params"], "kf_bal": sel["kfosc"]["selected"]["params"],
            "kf_asr": sel["kfosc"]["selected_assertive"]["params"]}


def controllers(fz):
    return {"rigid": ("rigid", {}), "neutral": ("neutral", {}), "bpf": ("bpf", fz["bpf"]),
            "kf_bal": ("kfosc", fz["kf_bal"]), "kf_asr": ("kfosc", fz["kf_asr"]), "oracle": ("oracle", {})}


def main():
    os.makedirs(OUT, exist_ok=True)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    t0 = time.time()
    fz = frozen()
    ctrls = controllers(fz)
    rows = []
    keep = {}
    for seed in SEEDS:
        sc0 = scenarios.handwriting(seed=seed, duration=6.0)
        ref_same, ref_rigid = bench.references(sc0)
        dev = bench.device_distortion(ref_same, ref_rigid)
        for f0 in F0S:
            tr = sg.TremorSpec(f0=f0, amp_pk=AMP)
            sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=tr)
            d_clean, r_neu = bench.housing_disturbance(sc1, ref_same)
            base = evaluate.compare(r_neu, ref_same)
            for name, (mode, kw) in ctrls.items():
                ctrl = model.Controller(mode=mode, **kw)
                if name == "neutral":
                    r = r_neu
                elif name == "oracle":
                    r = model.run(bench.with_disturbance(sc1, d_clean), ctrl)
                else:
                    r = model.run(sc1, ctrl)
                ref = ref_rigid if name == "rigid" else ref_same
                m = evaluate.compare(r, ref)
                m["ratio_vs_neutral"] = m["e_rms_um"] / base["e_rms_um"]
                if name in ("bpf", "kf_bal", "kf_asr"):
                    m["distortion_um"] = evaluate.compare(model.run(sc0, ctrl), ref_same)["e_rms_um"]
                rows.append({"seed": seed, "f0": f0, "controller": name, **m,
                             "device_detrended_rms_um": dev.get("detrended_rms_um")})
                if seed == SEEDS[0] and f0 == 9.0:
                    keep[name] = r
                    keep["ref_same"] = ref_same
    # feature course: distortion per feature (no tremor) and guided mode with tremor
    feat_rows = []
    fc0 = scenarios.features()
    fref = model.run(fc0, model.Controller(mode="neutral"))
    for name in ("bpf", "kf_bal", "kf_asr"):
        mode, kw = ctrls[name]
        r = model.run(fc0, model.Controller(mode=mode, **kw))
        fe = evaluate.feature_errors(r, fref, fc0.meta["features"])
        for feat, v in fe.items():
            feat_rows.append({"controller": name, "tremor": "none", "feature": feat, **v})
    fc1 = scenarios.features(tremor=sg.TremorSpec(f0=6.0, amp_pk=AMP))
    for name, mode in (("neutral", "neutral"), ("guided", "guided"), ("kf_asr", "kfosc")):
        kw = fz["kf_asr"] if name == "kf_asr" else {}
        r = model.run(fc1, model.Controller(mode=mode, **kw))
        fe = evaluate.feature_errors(r, fref, fc1.meta["features"])
        for feat, v in fe.items():
            feat_rows.append({"controller": name, "tremor": "6Hz 0.3mm", "feature": feat, **v})
        m = evaluate.compare(r, fref)
        feat_rows.append({"controller": name, "tremor": "6Hz 0.3mm", "feature": "ALL", "rms_um": m["e_rms_um"],
                          "max_um": m["e_p95_um"], "n": m["n_eval"]})
    # static load check (design angle range)
    stat = []
    for th in (35.0, 50.0, 75.0):
        r = model.run(scenarios.static_hold(duration=1.2, theta_deg=th, N0=1.0), model.Controller(mode="neutral"))
        sel = r["t"] > 0.9
        n = r.info["reduction"]["n_lever"]
        Kf = r.P[model.IDX["Kf"]]
        F_tip = float(np.linalg.norm(-n * Kf * r.xy("i1")[sel].mean(axis=0)))
        R = contact.reaction_components(r["N"][sel].mean(), 0.0, 0.0, math.radians(th))
        stat.append({"theta_deg": th, "N_mean": float(r["N"][sel].mean()), "F_actuator_tip_N": F_tip,
                     "analytic_Rperp_N": float(abs(R["R_perp"])), "P_cu_W": float(r["Pcu"][sel].mean())})
    # aggregate
    agg = {}
    for name in ctrls:
        for f0 in F0S:
            sub = [r for r in rows if r["controller"] == name and r["f0"] == f0]
            k = f"{name}@{f0:g}Hz"
            agg[k] = {m: float(np.mean([s[m] for s in sub])) for m in
                      ("e_rms_um", "ratio_vs_neutral", "e_band_rms_um", "q_rms_um", "frac_near_limit", "i_rms_A",
                       "P_cu_mean_W", "N_mod_rms", "F_hand_band_rms")}
            agg[k]["ratio_sd"] = float(np.std([s["ratio_vs_neutral"] for s in sub], ddof=1))
            if "distortion_um" in sub[0]:
                agg[k]["distortion_um"] = float(np.mean([s["distortion_um"] for s in sub]))
    meta = provenance.metadata("simulation (synthetic signals, TEST seeds; not human or bench data)",
                               seeds={"test": list(SEEDS)}, extra={"frozen_estimators": fz, "f0_hz": F0S, "amp_m": AMP,
                                                                    "elapsed_s": time.time() - t0})
    provenance.write_json(os.path.join(OUT, "metrics.json"), {"meta": meta, "aggregate": agg, "static": stat,
                                                              "features": feat_rows, "per_run": rows})
    with open(os.path.join(OUT, "metrics.csv"), "w", newline="") as f:
        keys = list(rows[0].keys())
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    # traces for one representative run (decimated to 1 kHz, float32)
    for name, r in keep.items():
        np.savez_compressed(os.path.join(OUT, f"traces_{name}.npz"),
                            t=r["t"][::2].astype(np.float32), tip=r.xy("tipx")[::2].astype(np.float32),
                            housing=r.xy("pHx")[::2].astype(np.float32), q=r.xy("q1")[::2].astype(np.float32),
                            i=r.xy("i1")[::2].astype(np.float32), N=r["N"][::2].astype(np.float32),
                            contact=r["contact"][::2].astype(np.int8))
    # figures ------------------------------------------------------------
    ref = keep["ref_same"]
    t = ref["t"]
    win = (t > 1.0) & (t < 3.2)
    same_kf = fz["kf_bal"] == fz["kf_asr"]  # tuning may select one set for both objectives
    kf_title = "Kalman (both profiles: same set)" if same_kf else "Kalman (assertive)"
    fig, axs = plt.subplots(1, 3, figsize=(13, 2.9), sharex=True, sharey=True)
    for ax, (name, title) in zip(axs, (("neutral", "powered neutral"), ("kf_asr", kf_title), ("oracle", "oracle bound"))):
        r = keep[name]
        cm = win & (r["contact"] > 0) & (ref["contact"] > 0)
        ax.plot(ref.xy("tipx")[win, 0] * 1e3, ref.xy("tipx")[win, 1] * 1e3, color=plotstyle.MUTED, lw=1.0, label="intended ink (no tremor)")
        tip = r.xy("tipx").copy()
        tip[~cm] = np.nan
        ax.plot(tip[win, 0] * 1e3, tip[win, 1] * 1e3, color=plotstyle.SERIES[0], lw=1.0, label="ink with tremor")
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlabel("page x (mm)")
    axs[0].set_ylabel("page y (mm)")
    handles, labs = axs[0].get_legend_handles_labels()
    fig.legend(handles, labs, loc="upper right", ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.995, 0.995))
    fig.suptitle("Ink with 9 Hz, 0.3 mm tremor (test seed %d), 50°, 1 N" % SEEDS[0], x=0.01, ha="left", fontsize=11)
    plotstyle.stamp(fig, "simulation", "synthetic handwriting and tremor; model M1")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_ink_traces.png"))
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    names = ["neutral", "bpf", "kf_bal", "kf_asr", "oracle"]
    x = np.arange(len(names))
    for j, f0 in enumerate(F0S):
        vals = [agg[f"{n}@{f0:g}Hz"]["ratio_vs_neutral"] for n in names]
        sds = [agg[f"{n}@{f0:g}Hz"]["ratio_sd"] for n in names]
        ax.bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=plotstyle.SERIES[j], label=f"tremor {f0:g} Hz",
               yerr=sds, error_kw=dict(ecolor=plotstyle.INK2, lw=0.8, capsize=2))
    ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
    ax.set_xticks(x, ["powered\nneutral", "band-pass", "Kalman\nbalanced", "Kalman\nassertive", "oracle\nbound"])
    ax.set_ylabel("Ink error / powered-neutral error")
    ax.set_title("Residual ink error by controller (mean ± SD over test seeds)", loc="left")
    ax.legend()
    plotstyle.stamp(fig, "simulation", "lower is better; >1 means assistance made ink worse"
                    + ("; both Kalman profiles are the same selected set" if same_kf else ""))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_ratio_by_controller.png"))
    plt.close(fig)
    for k, v in agg.items():
        print(k, {kk: round(vv, 3) for kk, vv in v.items()})
    print("static", stat)
    print("features", [(r["controller"], r["tremor"], r["feature"], round(r.get("rms_um", 0), 1)) for r in feat_rows])


if __name__ == "__main__":
    main()
