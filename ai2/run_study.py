"""One command for study L (AI and control v2): python3 -m ai2.run_study [--quick] [--workers 1] [--stages ...]

Stages (each caches its output in ai2/build/cache/ or ai2/build/quick/, git-ignored):
  d01        task 1 tuning: tremor smoother (D0) and tremor-line gate (D1), open loop, tuning writers 100-103, seed 300
  d2         task 1 tuning: lag policy per nose travel (D2), closed loop, seed 300; confirmation on seed 301
  d2b        task 1 tuning: D2 with an amplitude gate on the tremor line (added because no D2 setting passed R3/R4)
  learn_data task 2: domain-randomised training data (writers >= 1000, seeds >= 5000)
  learn      task 2: learned estimators (TCN, context TCN, hybrid Kalman-network, transformer), open-loop selection
  rl         task 3: Gymnasium environments (replay backend on HW1 sensor streams), SB3 PPO and SAC
  cl         tasks 2 + 3: closed-loop check of the learned and RL candidates on tuning writers (rules R1-R4)
  test       tasks 1-3 on the test grid: writers 0-5 x seeds 200-203 x 6/8/10 Hz x 0.3/1/2 mm + tremor-free writing
  text       task 4: next-letter and next-word prediction (corpora, n-gram, small transformer)
  synth      task 5: sigma-lognormal extraction and synthesis in the writer's style
  shared     task 6: arbitration (policy blending by confidence, assistance as needed) in HW1
  report     figures (+ CSV twins), ai2.json, samples.json, evidence_rows.csv in results/ai2/

--quick: fewer writers, seeds and conditions; outputs go to ai2/build/quick/ (never over the results).
At most 2 worker processes; each worker is limited to 1 numerical thread.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from . import TUNE_SEEDS, TUNE_WRITERS  # noqa: E402
from . import common as C  # noqa: E402

STAGES = ("d01", "d2", "d2b", "learn_data", "learn", "rl", "cl", "test", "text", "synth", "shared", "report")


def stage_d01(quick: bool, workers: int):
    from . import tuning as TU
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    d0 = TU.d0_candidates()
    jobs = [{"writer": w, "seed": TUNE_SEEDS[0], "d0": d0} for w in writers]
    outs = C.jmap(TU.d01_job, jobs, workers)
    s0 = TU.select_d0(outs, d0)
    s1 = TU.select_d1(outs, TU.d1_candidates())
    out = {"outs": [{"writer": o["writer"], "rows": [{k: v for k, v in r.items() if k not in ("ratio", "det_t")} for r in o["rows"]]}
                    for o in outs], "d0": s0, "d1": s1,
           "chosen_tremor": next(c for c in d0 if TU.key(c) == s0["chosen_key"]), "chosen_det": s1["chosen"]}
    C.save("d01", out, quick)
    C.log(f"[d01] tremor smoother {s0['chosen_key']}; gate {s1['chosen_key']}")
    return out


def stage_d2(quick: bool, workers: int, name: str = "d2"):
    from . import tuning as TU
    d01 = C.load("d01", quick)
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    cands = TU.d2_candidates() if name == "d2" else TU.d2b_candidates()
    if quick:
        cands = cands[:3]
    base = {"tremor": d01["chosen_tremor"], "det": d01["chosen_det"] or {}}
    jobs = [dict(base, writer=w, seed=TUNE_SEEDS[0], cands=cands) for w in writers]
    outs = C.jmap(TU.d2_job, jobs, workers)
    sel = TU.select_d2(outs, cands)
    # confirmation on seed 301 (the chosen settings and the causal gated tracker only)
    keep = {v for v in sel["chosen"].values() if v} | ({sel["causal_gated"]} if sel["causal_gated"] else set())
    conf_c = [c for c in cands if any(k.startswith(TU.key(c) + "_nose") for k in keep)]
    conf = None
    if not quick and conf_c:
        jobs = [dict(base, writer=w, seed=TUNE_SEEDS[1], cands=conf_c) for w in writers]
        conf_outs = C.jmap(TU.d2_job, jobs, workers)
        conf = TU.select_d2(conf_outs, conf_c)
    out = {"outs": outs, "selection": sel, "confirmation_seed_301": conf, "base": base, "candidates": cands}
    C.save(name, out, quick)
    C.log(f"[{name}] chosen {sel['chosen']} causal {sel['causal_gated']}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--stages", nargs="+", default=list(STAGES), choices=STAGES)
    a = ap.parse_args(argv)
    t_all = time.time()
    for st in a.stages:
        t = time.time()
        if st == "d01":
            stage_d01(a.quick, a.workers)
        elif st in ("d2", "d2b"):
            stage_d2(a.quick, a.workers, st)
        else:
            mod = __import__("ai2.report" if st == "report" else f"ai2.stage_{st}", fromlist=["run"])
            mod.run(a.quick, a.workers)
        C.log(f"[{st}] {time.time() - t:.0f} s")
    C.log(f"total {time.time() - t_all:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
