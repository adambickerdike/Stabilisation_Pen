"""One command for study E:  python3 -m realtrack.run [--quick] [--stages repro cases search learn freeze test report]

Stages (each resumes from realtrack/build; the container may restart; ONE process, one numerical thread):
  repro    re-run study R's quick cases with R's code and compare with R's cache (bit-identical -> R's cached per-case
           results are re-used for R's pens in the test)
  cases    the tuning selection set (cases.py): 10 tuning notes x PD/ET x 4 amplitudes + the clean notes
  search   stage 1 (raw estimators), stage 2 (soft authority), the retuned binary gate, the soft line confidence, the
           joint AKF search (search.py; the rules are in tune.py)
  learn    the FIR (linear) and the TCN trained on real tuning inputs, cross-fitted by fold (learned.py, netmodel.py),
           the soft authority on the learned outputs (and on ai2's TCN), then study W's GLG (chain_after.py)
  freeze   the finalists re-run in the full HW1 plant on the tuning cases; the choice by tune.py's rules; writes
           results/realtrack/frozen.json (test.py refuses to run without it); then the analyses (post.py)
  test     the one test run on R's test split (test.py) and the CC BY before/after picture runs
  sim2     one confirmation in sim2 (sim2j's ET grid, one writer) if time allows (sim2check.py)
  report   results/realtrack/*.json with stabpen.provenance, figures with CSV twins, evidence_rows.csv
--quick: the first test note only, severe class only (a smoke run; writes realtrack/build/quick/, never the results).
"""
from __future__ import annotations

import argparse
import time

ALL = ("repro", "cases", "search", "learn", "freeze", "test", "sim2", "report")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def stage_repro(quick: bool):
    from . import repro
    repro.run(log=log)


def stage_cases(quick: bool):
    from . import cases as C
    C.build_tuning_set(log=log)


def stage_search(quick: bool):
    from . import search as SR
    SR.stage1(log=log)
    SR.stage2(log=log)
    SR.stage2b(log=log)


def stage_learn(quick: bool):
    from . import chain_after
    chain_after.main()


def stage_freeze(quick: bool):
    from . import post
    post.main()


def stage_test(quick: bool):
    from . import test as T
    T.run(log=log, quick=quick)
    if not quick:
        T.picture_runs(log=log)


def stage_sim2(quick: bool):
    from . import sim2check as S2
    S2.run(log=log, quick=quick)


def stage_report(quick: bool):
    from . import report as RP
    RP.write(quick=quick, log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", nargs="*", default=list(ALL), choices=ALL)
    a = ap.parse_args(argv)
    t0 = time.time()
    for s in ALL:
        if s in a.stages:
            log(f"== stage {s}{' (quick)' if a.quick else ''}")
            globals()[f"stage_{s}"](a.quick)
    log(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
