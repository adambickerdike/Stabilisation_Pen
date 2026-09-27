#!/usr/bin/env python3
"""C4: domain randomisation. How do the frozen Kalman set and the oracle bound degrade on
held-out randomised plants, and does tuning on randomised plants pick a better set?

Plants are drawn over every truth key (actuator, stage, contact, hand, sensors): 16 inside
the declared ranges and 8 partly outside, all held out from any tuning, running the
nominal firmware through s2r.twin.shim (the controller does not learn each plant, unlike
sim/run_sweeps.py's Monte Carlo, where model.build_params hands the true values to the
controller). Outcomes at 50 deg, 1 N, 0.3 mm tremor, 6 and 9 Hz, first 4 TEST seeds.

Tuning comparison (a handful of candidates from sim/tune_estimators.py's grid, including
the frozen active set and the v0.4.1 inert set): objective J = mean(ratio + lambda
distortion/base) over f0 in {4.5, 6, 8, 10} Hz, lambda = 1 (as tune_estimators), on
TUNING seeds only:
  nominal tuning      nominal plant, tuning seeds 100-102;
  randomised tuning   8 training plants drawn inside the ranges, tuning seeds 100-101.
Every candidate is then scored on the 16 held-out in-range plants with TEST seeds 200-202.

Evidence status: SIMULATION (synthetic writing and tremor, plants from declared ranges,
which are not population distributions).
Outputs: results/s2r/c4_domain.json, fig_c4_domain.png
Run: python3 -m s2r.run_c4_domain [--quick]     (about 15 min on 2 processes)
"""
from __future__ import annotations

import argparse
import time

import numpy as np

import s2r  # noqa: F401
from s2r import common, fastharness, twin
from s2r import truth as tr
from sim.pensim import harness, model

CANDIDATES = [dict(kf_qj=0.1, kf_qt=1e-8, kf_w0_hz=7.0, f_gate=7.5),     # frozen (selected, v0.4.4)
              dict(kf_qj=10.0, kf_qt=3e-9, kf_w0_hz=7.0, f_gate=7.5),    # v0.4.1 inert set
              dict(kf_qj=1.0, kf_qt=1e-8, kf_w0_hz=7.0, f_gate=7.5),
              dict(kf_qj=0.3, kf_qt=1e-8, kf_w0_hz=7.0, f_gate=6.5),
              dict(kf_qj=3.0, kf_qt=3e-9, kf_w0_hz=7.0, f_gate=7.5),
              dict(kf_qj=0.1, kf_qt=3e-9, kf_w0_hz=7.0, f_gate=7.5)]
TUNE_F0 = (4.5, 6.0, 8.0, 10.0)
LAMBDA = 1.0


def plants(seed, n_in, n_out):
    ts = tr.batch(seed, n_in, n_out)
    nom = twin.nominal_plant()
    out = []
    for t in ts:
        v = dict(nom)
        v.update(t["values"])
        out.append({"id": t["id"], "kind": t["kind"], "values": v})
    return out


def cases_for(plant_vals, seeds, f0s, mode, kf=None, distortion=False, tag=""):
    ov, kw, _ = twin.shim(plant_vals)
    ctrl = dict(kw)
    if kf:
        ctrl.update(kf)
    out = []
    for s in seeds:
        for f in f0s:
            out.append(dict(seed=s, f0=f, amp=3e-4, mode=mode, ctrl=ctrl, overrides=ov,
                            distortion=distortion and f == f0s[0], tag=tag))
    return out


def J(rows):
    """tune_estimators objective; distortion is per seed (computed once per seed)."""
    dist = {r["seed"]: r["distortion_um"] for r in rows if r["distortion_um"] > 0}
    vals = [r["ratio"] + LAMBDA * dist.get(r["seed"], 0.0) / r["base_e_rms_um"] for r in rows]
    return float(np.mean(vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    n_in, n_out, n_train = (3, 1, 2) if a.quick else (16, 8, 8)
    held = plants(4040, n_in, n_out)
    train = plants(9090, n_train, 0)
    test_seeds = harness.TEST_SEEDS[:2] if a.quick else harness.TEST_SEEDS[:4]
    eval_seeds = harness.TEST_SEEDS[:1] if a.quick else harness.TEST_SEEDS[:3]
    nominal = twin.nominal_plant()
    frozen = twin.frozen_kf()
    cands = CANDIDATES[:2] if a.quick else CANDIDATES
    # 1. degradation of the frozen set and the oracle on held-out plants (one batch)
    allp = [{"id": "nominal", "kind": "nominal", "values": nominal}] + held
    cs = []
    for p in allp:
        cs += cases_for(p["values"], test_seeds, (6.0, 9.0), "oracle", tag=f"{p['id']}|oracle")
        cs += cases_for(p["values"], test_seeds, (6.0, 9.0), "kfosc", frozen, distortion=True, tag=f"{p['id']}|kf")
    rows = fastharness.run_cases(cs, a.workers)
    deg = []
    for p in allp:
        ent = {"id": p["id"], "kind": p["kind"]}
        sub = [r for r in rows if r["tag"].startswith(p["id"] + "|")]
        for f in (6.0, 9.0):
            for tag in ("oracle", "kf"):
                ent[f"{tag}@{f:g}"] = float(np.mean([r["ratio"] for r in sub if r["tag"].endswith(tag) and r["f0"] == f]))
        ent["kf_distortion_um"] = float(np.mean([r["distortion_um"] for r in sub if r["tag"].endswith("kf")
                                                 and r["distortion_um"] > 0]))
        ent["neutral_e_um@9"] = float(np.mean([r["base_e_rms_um"] for r in sub if r["f0"] == 9.0]))
        deg.append(ent)
    print("degradation done", f"{time.time() - t0:.0f} s", flush=True)
    # 2. tuning on the nominal plant vs on randomised plants (one batch)
    cs = []
    for ci, kf in enumerate(cands):
        cs += cases_for(nominal, harness.TUNING_SEEDS[:3], TUNE_F0, "kfosc", kf, True, tag=f"nom|{ci}")
        for p in train:
            cs += cases_for(p["values"], harness.TUNING_SEEDS[:2], TUNE_F0, "kfosc", kf, True, tag=f"{p['id']}|{ci}")
    rows = fastharness.run_cases(cs, a.workers)
    tune = {"nominal": {}, "randomised": {}}
    for ci in range(len(cands)):
        tune["nominal"][ci] = J([r for r in rows if r["tag"] == f"nom|{ci}"])
        tune["randomised"][ci] = float(np.mean([J([r for r in rows if r["tag"] == f"{p['id']}|{ci}"]) for p in train]))
    print("tuning done", f"{time.time() - t0:.0f} s", tune, flush=True)
    sel_nom = min(tune["nominal"], key=tune["nominal"].get)
    sel_dr = min(tune["randomised"], key=tune["randomised"].get)
    # 3. every candidate on the held-out in-range plants, TEST seeds (one batch)
    ins_ = [h for h in held if h["kind"] == "inside"]
    cs = []
    for ci, kf in enumerate(cands):
        for p in ins_:
            cs += cases_for(p["values"], eval_seeds, TUNE_F0, "kfosc", kf, True, tag=f"{p['id']}|{ci}")
    rows = fastharness.run_cases(cs, a.workers)
    evalc = {}
    for ci, kf in enumerate(cands):
        js, r6, r9, ds = [], [], [], []
        for p in ins_:
            sub = [r for r in rows if r["tag"] == f"{p['id']}|{ci}"]
            js.append(J(sub))
            r6.append(np.mean([r["ratio"] for r in sub if r["f0"] == 6.0]))
            r9.append(np.mean([r["ratio"] for r in sub if r["f0"] in (8.0, 10.0)]))
            ds.append(np.mean([r["distortion_um"] for r in sub if r["distortion_um"] > 0]))
        evalc[ci] = {"params": kf, "J_heldout_mean": float(np.mean(js)), "J_heldout_p90": float(np.percentile(js, 90)),
                     "ratio6_mean": float(np.mean(r6)), "ratio_8_10_mean": float(np.mean(r9)),
                     "distortion_um_mean": float(np.mean(ds)), "J_per_plant": [float(x) for x in js],
                     "wins_vs_frozen": None}
    for ci in evalc:
        evalc[ci]["wins_vs_frozen"] = int(np.sum(np.array(evalc[ci]["J_per_plant"]) < np.array(evalc[0]["J_per_plant"])))
    print("eval done", f"{time.time() - t0:.0f} s", flush=True)
    base = deg[0]
    summ = {}
    for kind in ("inside", "outside"):
        sub = [d for d in deg if d["kind"] == kind]
        summ[kind] = {k: common.summarize([d[k] for d in sub]) for k in sub[0] if k not in ("id", "kind")}
    payload = {"nominal": base, "held_out": deg[1:], "degradation_summary": summ,
               "candidates": cands, "tuning_J": tune, "selected_nominal": sel_nom, "selected_randomised": sel_dr,
               "heldout_eval": evalc, "frozen_set": frozen,
               "seeds": {"test": list(test_seeds), "test_candidate_eval": list(eval_seeds),
                         "tuning_nominal": list(harness.TUNING_SEEDS[:3]),
                         "tuning_randomised": list(harness.TUNING_SEEDS[:2]), "plants_heldout": 4040, "plants_train": 9090},
               "elapsed_s": time.time() - t0}
    path = common.write_result("c4_domain", payload, "SIMULATION (randomised plants from declared ranges; synthetic signals)",
                               seeds=payload["seeds"])
    plot(deg, evalc, sel_nom, sel_dr)
    print(path, f"{time.time() - t0:.0f} s", "selected nominal", sel_nom, "selected DR", sel_dr)


def plot(deg, evalc, sel_nom, sel_dr):
    from stabpen import plotstyle
    fig, axs = common.figure(1, 2, figsize=(12.0, 4.0))
    ax = axs[0]
    for j, (k, lab) in enumerate((("oracle@9", "oracle 9 Hz"), ("kf@9", "Kalman 9 Hz"), ("kf@6", "Kalman 6 Hz"))):
        for kind, mk in (("inside", "o"), ("outside", "^")):
            ys = [d[k] for d in deg[1:] if d["kind"] == kind]
            ax.plot(np.full(len(ys), j) + (0.15 if kind == "outside" else -0.15)
                    + np.random.default_rng(j).uniform(-0.05, 0.05, len(ys)), ys, mk, ms=5,
                    color=plotstyle.SERIES[j], alpha=0.8)
        ax.plot([j - 0.35, j + 0.35], [deg[0][k]] * 2, color=plotstyle.INK, lw=2)
    ax.axhline(1.0, color=plotstyle.MUTED, lw=0.8)
    ax.set_xticks([0, 1, 2], ["oracle 9 Hz", "Kalman 9 Hz", "Kalman 6 Hz"])
    ax.set_ylabel("ink error / powered-neutral error")
    ax.set_title("Held-out plants (o in range, ^ partly outside); bar = nominal", loc="left", fontsize=10)
    ax = axs[1]
    ci = sorted(evalc)
    ax.bar(np.arange(len(ci)), [evalc[c]["J_heldout_mean"] for c in ci], color=[
        plotstyle.SERIES[1] if c == sel_dr else plotstyle.SERIES[0] if c == sel_nom else plotstyle.MUTED for c in ci])
    ax.set_xticks(np.arange(len(ci)), [f"qj {evalc[c]['params']['kf_qj']:g}\nqt {evalc[c]['params']['kf_qt']:g}\n"
                                       f"gate {evalc[c]['params']['f_gate']:g}" for c in ci], fontsize=7)
    ax.set_ylabel("held-out objective J (lower is better)")
    ax.set_title("Candidates on held-out plants (blue: nominal pick, orange: randomised pick)", loc="left", fontsize=10)
    lo = min(evalc[c]["J_heldout_mean"] for c in ci)
    ax.set_ylim(lo - 0.1, None)
    common.save_figure(fig, "fig_c4_domain", "simulation",
                       "randomised plants from declared ranges under the nominal firmware; synthetic writing and tremor")


if __name__ == "__main__":
    main()
