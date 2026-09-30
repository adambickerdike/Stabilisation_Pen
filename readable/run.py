"""Study F:  python3 -m readable.run [--quick] [--stages ...] [--workers 2]

Stages (each resumes from its caches in readable/build; one JSON per case):
  predictor  the causal linear (AR) predictor of the clean tremor signal, chosen on E's tuning cases (main process)
  tuning     E13 tuning notes (every run read by the AI reader), the E11 rule choice (surrogate), the gap on the tuning
             cases: jobs on at most two worker processes
  freeze     the E13 curve, thresholds and test levels, the E11 rules, the predictor -> frozen.json (once)
  test       R's test notes, once: E13 confirmation, E11 calibration, the gap (two workers)
  extras     the sensing check on the tuning split (the IMU filter with a perfect accelerometer; a linear estimator on
             the page position) and the clean-writing change of every full estimator on R's clean test notes
  report     readable.json with stabpen.provenance, the figures with CSV twins, the doc tables, the ledger rows
--quick: one tuning note (PD, severe: the ordinary pen and 2 residual levels, read), one test note (not read), a
reduced E11 grid, no sensing check; outputs go to readable/build/quick/ and never overwrite results/readable/.
"""
from __future__ import annotations

import argparse
import time

from . import common as CM

ALL = ("predictor", "tuning", "freeze", "test", "extras", "report")


def _timings(quick: bool, stage: str, elapsed: float, jobs=None) -> None:
    p = CM.cache_dir(quick) / "timings.json"
    d = CM.jload(p) or {"stages": {}, "jobs": {}}
    d["stages"][stage] = round(elapsed, 1)
    for j in jobs or []:
        d["jobs"][j["job"]] = {"ok": j["ok"], "elapsed_s": round(j["elapsed_s"], 1)}
    CM.jdump(p, d)


def stage_predictor(a) -> None:
    from . import gap
    from . import stages as SG
    p = SG.predictor_path(a.quick)
    if p.exists():
        CM.log(f"[predictor] cached {p}")
        return
    CM.jdump(p, gap.fit_predictors(quick=a.quick))


def stage_tuning(a):
    from . import e13
    from . import jobs as JB
    P = e13.plan(a.quick)
    specs = [JB.job(f"e13_tune_n{i}", "readable.stages", "job_e13_tune", i=i, quick=a.quick) for i in P["tuning"]["notes"]]
    specs.append(JB.job("e11_tune", "readable.stages", "job_e11_tune", quick=a.quick))
    specs += [JB.job(f"gap_tune_n{i}", "readable.stages", "job_gap_tune", i=i, quick=a.quick) for i in P["tuning"]["notes"]]
    return JB.run(specs, a.workers, CM.log)


def stage_freeze(a) -> None:
    from . import stages as SG
    SG.freeze(a.quick, force=a.refreeze)


def stage_test(a):
    from . import e13
    from . import jobs as JB
    P = e13.plan(a.quick)
    specs = [JB.job(f"test_w{i}", "readable.stages", "job_test", i=i, quick=a.quick) for i in P["test"]["notes"]]
    return JB.run(specs, a.workers, CM.log)


def stage_extras(a):
    from . import e13
    from . import jobs as JB
    P = e13.plan(a.quick)
    specs = [] if a.quick else [JB.job(f"sensing_{k}", "readable.stages", "job_sensing", kind=k, quick=a.quick)
                                for k in ("imu", "page")]          # (full runs only: about 2 minutes each)
    specs += [JB.job(f"gap_test_clean_w{i}", "readable.stages", "job_gap_test_clean", i=i, quick=a.quick)
              for i in P["test"]["notes"]]
    from . import reach
    specs += [JB.job(f"reach_n{i}", "readable.stages", "job_reach", i=i, quick=a.quick)
              for i in reach.plan(a.quick)["notes"]]          # tuning split only; after the freeze
    return JB.run(specs, a.workers, CM.log)


def stage_report(a) -> None:
    from . import doc, evidence, figures, report
    from . import stages as SG
    out = report.write(a.quick)
    d = SG.results_dir(a.quick)
    figures.all_figures(out, d)
    n = evidence.write(out, d / "evidence_rows.csv")
    CM.log(f"[report] {n} proposed ledger rows -> {d / 'evidence_rows.csv'}")
    doc.write_tables(out, a.quick)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", nargs="*", default=list(ALL), choices=ALL)
    ap.add_argument("--workers", type=int, default=2, help="worker processes (at most 2)")
    ap.add_argument("--refreeze", action="store_true", help="rewrite frozen.json (only before the test stage has run)")
    a = ap.parse_args(argv)
    t0 = time.time()
    for s in ALL:
        if s in a.stages:
            CM.log(f"== stage {s}{' (quick)' if a.quick else ''}")
            t1 = time.time()
            jobs = globals()[f"stage_{s}"](a)
            _timings(a.quick, s, time.time() - t1, jobs if isinstance(jobs, list) else None)
            bad = [j for j in (jobs or []) if isinstance(jobs, list) and not j["ok"]]
            if bad:
                CM.log(f"== stage {s}: {len(bad)} job(s) failed; stopping")
                raise SystemExit(1)
    _timings(a.quick, "total_this_call", time.time() - t0)
    CM.log(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
