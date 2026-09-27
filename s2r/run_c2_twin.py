#!/usr/bin/env python3
"""C2: how well does a calibrated twin predict the hidden plant's performance?

For each hidden plant of C1 (results/s2r/c1_identification.json):
  truth          M1 with every true parameter (actuator, stage, contact, hand, sensors),
                 running the unchanged nominal firmware (s2r.twin.shim). On the EXP-B09 rig
                 the "hand" is the R2 simulant;
  before         the nominal twin (config/parameters.yaml v0.4.4), i.e. no calibration;
  after_nohand   the twin updated with the EXP-B03/B05/B01/B02 estimates, hand and sensor
                 keys nominal (a twin of a human writer before EXP-B06);
  after          the same with the simulant's set values: the true hand keys, each off by
                 U(+-10 %) (PROTOCOL R2: simulant FRF within +-10 % of target); sensors nominal
                 (EXP-S01/B04 not modelled here). This is the B09 prediction the protocol freezes;
  after_plus     after, with the true sensor keys (as if EXP-S01/B04 were done perfectly).
Outcomes on the TEST seeds 200-211 at the EXP-B09 primary cells (theta 50 deg,
N 1 N, 0.3 mm tremor at 6 and 9 Hz): oracle ratio, Kalman ratio (frozen set),
Kalman distortion without tremor, neutral-pen ink error, static hold copper loss
(50 deg, 1 N), and device distortion (neutral vs rigid; first 4 test seeds).

Evidence status: SIMULATION (twin experiment). It shows how the method behaves
when the model structure is right; it says nothing about whether M1 is right.
Outputs: results/s2r/c2_twin.json, fig_c2_gap.png
Run: python3 -m s2r.run_c2_twin --part 1; --part 2; --merge   (about 4 min per part on 2 processes;
     no --part runs all 15 plants in one call, about 8 min)
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

import s2r  # noqa: F401
from s2r import common, pipeline, twin
from s2r import truth as tr
from sim.pensim import harness

OUTCOMES = ["oracle_ratio@6Hz", "oracle_ratio@9Hz", "kfosc_ratio@6Hz", "kfosc_ratio@9Hz", "kf_distortion_um",
            "neutral_e_um@6Hz", "neutral_e_um@9Hz", "static_hold_W", "device_distortion_um"]
RATIOS = OUTCOMES[:4]
ABSOLUTE = RATIOS + ["kf_distortion_um", "device_distortion_um"]     # gaps in ratio units or um


def evaluate(plant, seeds, workers):
    out = twin.evaluate_plant(plant, seeds=seeds, workers=workers, device=False)
    out["device_distortion_um"] = twin.device_distortion(twin.shim(plant)[0], seeds[:4])
    return out


def conditions(nominal, tv, idv, rng):
    hand = tr.GROUPS["B06_hand"]
    sens = tr.GROUPS["S01B04_sensors"]
    after_nohand = dict(nominal)
    after_nohand.update(idv)
    after = dict(after_nohand)
    for k in hand:
        after[k] = tv[k] * (1 + rng.uniform(-0.1, 0.1))
    plus = dict(after)
    for k in sens:
        plus[k] = tv[k]
    return {"after_nohand": after_nohand, "after": after, "after_plus": plus}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--part", type=int, default=0, help="0 = all plants; 1 = plants 0-7; 2 = plants 8-")
    ap.add_argument("--merge", action="store_true", help="merge c2_twin_part1/2.json into c2_twin.json")
    a = ap.parse_args()
    if a.merge:
        return merge()
    c1 = json.load(open(os.path.join(s2r.RESULTS, "c1_identification.json")))
    rows_in = c1["per_truth"]
    truths = {t["id"]: t for t in c1["truths_revealed"]}
    seeds = harness.TEST_SEEDS[:2] if a.quick else harness.TEST_SEEDS
    if a.quick:
        rows_in = rows_in[:2]
    elif a.part == 1:
        rows_in = rows_in[:8]
    elif a.part == 2:
        rows_in = rows_in[8:]
    t0 = time.time()
    nominal = twin.nominal_plant()
    nom = evaluate(nominal, seeds, a.workers) if a.part in (0, 1) else None
    per = []
    for r in rows_in:
        tv = dict(nominal)
        tv.update(truths[r["id"]]["values"])
        idv = pipeline.identified_values(r["estimates"])
        rng = np.random.default_rng(int(r["id"][1:]) + 555)
        ent = {"id": r["id"], "kind": r["kind"], "outside": r["outside"], "truth": evaluate(tv, seeds, a.workers)}
        for lab, pv in conditions(nominal, tv, idv, rng).items():
            ent[lab] = evaluate(pv, seeds, a.workers)
        per.append(ent)
        print(r["id"], f"{time.time() - t0:.0f} s", {k: round(ent["truth"][k], 3) for k in RATIOS}, flush=True)
    part = {"nominal": None if nom is None else {k: nom[k] for k in OUTCOMES},
            "per_plant": [{kk: ({k: e[k] for k in OUTCOMES + ["_per_seed", "_shim"]} if isinstance(e, dict)
                                and kk in LABELS + ("truth",) else e) for kk, e in ent.items()} for ent in per],
            "seeds": list(seeds), "elapsed_s": time.time() - t0}
    if a.part in (1, 2):
        common.write_result(f"c2_twin_part{a.part}", part, "SIMULATION (twin experiment, partial)",
                            seeds={"test": list(seeds)})
        print("part written", f"{time.time() - t0:.0f} s")
        return
    finish(part, seeds, t0)


LABELS = ("after_nohand", "after", "after_plus")


def merge():
    p1 = json.load(open(os.path.join(s2r.RESULTS, "c2_twin_part1.json")))
    p2 = json.load(open(os.path.join(s2r.RESULTS, "c2_twin_part2.json")))
    part = {"nominal": p1["nominal"], "per_plant": p1["per_plant"] + p2["per_plant"], "seeds": p1["seeds"]}
    finish(part, p1["seeds"], time.time() - p1["elapsed_s"] - p2["elapsed_s"])
    for k in (1, 2):
        os.remove(os.path.join(s2r.RESULTS, f"c2_twin_part{k}.json"))


def finish(part, seeds, t0):
    nom = part["nominal"]
    per = part["per_plant"]
    gaps = {}
    for label in ("before",) + LABELS:
        g = {}
        for k in OUTCOMES:
            vals = []
            for ent in per:
                pred = nom[k] if label == "before" else ent[label][k]
                tru = ent["truth"][k]
                if k in ABSOLUTE:
                    vals.append(pred - tru)
                elif abs(tru) > 1e-12:
                    vals.append((pred - tru) / tru)
            v = np.array(vals)
            g[k] = {"kind": "absolute" if k in ABSOLUTE else "relative", **common.summarize(v),
                    "abs_max": float(np.max(np.abs(v)))}
            if k in RATIOS:
                g[k]["frac_within_0.1"] = float(np.mean(np.abs(v) <= 0.1))
                g[k]["frac_within_0.05"] = float(np.mean(np.abs(v) <= 0.05))
        gaps[label] = g
    spread = {k: common.summarize([ent["truth"][k] for ent in per]) for k in OUTCOMES}
    payload = {"nominal": nom, "gaps": gaps, "truth_spread": spread,
               "per_plant": [{kk: ({k: e[k] for k in OUTCOMES} if isinstance(e, dict) and kk in LABELS + ("truth",)
                                   else e) for kk, e in ent.items()} for ent in per],
               "per_seed_truth_after": [{"id": ent["id"], "truth": ent["truth"]["_per_seed"],
                                         "after": ent["after"]["_per_seed"]} for ent in per],
               "shim": {ent["id"]: ent["truth"]["_shim"] for ent in per},
               "seeds": list(seeds), "cells": {"theta_deg": 50, "N0": 1.0, "amp_m": 3e-4, "f0_hz": [6, 9]},
               "conditions": {"after_nohand": "B03/B05/B01-B02 estimates; hand and sensors nominal",
                              "after": "estimates + simulant hand (true +-10 %); sensors nominal",
                              "after_plus": "estimates + simulant hand + true sensors"},
               "elapsed_s": time.time() - t0}
    path = common.write_result("c2_twin", payload, "SIMULATION (twin experiment: M1 truth vs M1 twins)",
                               seeds={"test": list(seeds)}, extra={"frozen_kf": twin.frozen_kf()})
    plot(per, nom)
    print(path)
    for label, g in gaps.items():
        print(label, {k: (round(v["abs_max"], 3), round(v.get("frac_within_0.1", float("nan")), 2)) for k, v in g.items()})


def plot(per, nom):
    from stabpen import plotstyle
    fig, axs = common.figure(1, 4, figsize=(14.0, 3.8))
    for ax, k in zip(axs, RATIOS):
        tru = np.array([e["truth"][k] for e in per])
        aft = np.array([e["after"][k] for e in per])
        out = np.array([bool(e["outside"]) for e in per])
        lo, hi = min(tru.min(), aft.min(), nom[k]) - 0.05, max(tru.max(), aft.max(), nom[k]) + 0.05
        ax.fill_between([lo, hi], [lo - 0.1, hi - 0.1], [lo + 0.1, hi + 0.1], color=plotstyle.GRID, alpha=0.6, lw=0,
                        label="+-0.1 (AC-B09-03)")
        ax.plot([lo, hi], [lo, hi], color=plotstyle.MUTED, lw=0.8)
        ax.plot(tru, np.full_like(tru, nom[k]), "s", ms=5, color=plotstyle.SERIES[1], label="before (nominal twin)")
        ax.plot(tru[~out], aft[~out], "o", ms=5, color=plotstyle.SERIES[0], label="after calibration, plant in range")
        ax.plot(tru[out], aft[out], "^", ms=6, color=plotstyle.SERIES[2],
                label="after calibration, plant partly out of range")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel(f"hidden plant: {k}")
        ax.set_title(k.replace("_", " "), loc="left", fontsize=9.5)
    axs[0].set_ylabel("twin prediction")
    axs[0].legend(fontsize=7)
    common.save_figure(fig, "fig_c2_gap", "simulation",
                       "twin experiment on M1, 12 test seeds; after = B03/B05/B01-B02 estimates + simulant hand "
                       "(true +-10 %), sensor keys nominal")


if __name__ == "__main__":
    main()
