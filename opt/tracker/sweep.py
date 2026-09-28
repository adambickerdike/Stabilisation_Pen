"""The lambda_fc sweep (Pareto front of tremor-band residual against false correction), SIMULATION.

A chain trains the AKF at increasing (or decreasing) lambda_fc, each point warm-started from the previous one's
best validation iterate: python3 -m opt.tracker.sweep <name> <start set> <harm> <lambda,lambda,...> [iters first]
[iters next].  Each point is saved to opt/tracker/build/runs/sweep_<name>_l<lambda>.json.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import torch

from . import BUILD
from . import adjoint as AD
from . import data as DA
from . import torch_akf as TA
from . import train_akf as TR

RUNS = os.path.join(BUILD, "runs")


def run_chain(name: str, start_params: dict, harm: float, lams, iters_first: int = 50, iters_next: int = 35,
              log=print, threads: int = 2):
    torch.set_num_threads(1)
    AD.set_threads(threads)
    t0 = time.time()
    batches = TR.minibatches(DA.train_items(96, 64), 4)
    vals = {"val": DA.build_set(DA.val_items()), "tune_grid": DA.build_set(DA.tune_grid_items()),
            "tune_ai": DA.build_set(DA.tune_ai_items())}
    log(f"[{name}] data {time.time() - t0:.0f} s; batches {[b.B for b in batches]}")
    start = TA.trainable_start(start_params)
    os.makedirs(RUNS, exist_ok=True)
    out = []
    for j, lam in enumerate(lams):
        fp = os.path.join(RUNS, f"sweep_{name}_l{lam:g}.json")
        if os.path.exists(fp):                        # resume: this point exists, continue from its best iterate
            res = json.load(open(fp))
            start = res["best"]["vals"]
            out.append(res)
            log(f"[{name}] lambda {lam:g}: loaded {os.path.basename(fp)} (best iter {res['best']['iter']})")
            continue
        cfg = TR.TrainCfg(lam_fc=float(lam), iters=iters_first if j == 0 else iters_next, harm=harm,
                          lr=0.03 if j == 0 else 0.02)
        res = TR.train(batches, vals, start, cfg, log=log, tag=f"{name} l{lam:g}")
        res["chain"] = name
        res["lam_fc"] = float(lam)
        res["start_from"] = "previous point" if j else "given set"
        json.dump(res, open(os.path.join(RUNS, f"sweep_{name}_l{lam:g}.json"), "w"), indent=1, default=float)
        start = res["best"]["vals"]
        out.append(res)
        log(f"[{name}] lambda {lam:g} done: best iter {res['best']['iter']} val J {res['best']['val']['J_mean']:.4f} "
            f"({time.time() - t0:.0f} s)")
    return out


if __name__ == "__main__":
    from fusion import run_study as RS
    name, start_key, harm = sys.argv[1], sys.argv[2], float(sys.argv[3])
    lams = [float(x) for x in sys.argv[4].split(",")]
    it1 = int(sys.argv[5]) if len(sys.argv) > 5 else 50
    it2 = int(sys.argv[6]) if len(sys.argv) > 6 else 35
    thr = int(sys.argv[7]) if len(sys.argv) > 7 else 2
    T = RS.tuned()
    run_chain(name, T[start_key]["params"], harm, lams, it1, it2, log=lambda s: print(s, flush=True), threads=thr)
