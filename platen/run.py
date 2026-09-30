"""Study P (the active writing surface):  python3 -m platen.run [--quick] [--stages ...]

Stages (each resumes from its caches in platen/build; one JSON per case; ONE process, one numerical thread):
  tremor       part (a): tremor on real recorded inputs, tuning split (tremor.py; reads words with study R's reader)
  accepted     part (b): the accepted references executed by moving the page (accepted.py)
  sensitivity  part (c): slip, tilt, sensing delay and noise, bandwidth, travel, friction, pen mass; accepted-mode
               sensitivities (sensitivity.py, accepted_sens in this file)
  report       results/platen/*.json with stabpen.provenance, figures with CSV twins, evidence_rows.csv (report.py)
--quick: one tuning note (PD, severe; perfect knowledge read), two accepted references and hands, two sensitivity
variants; outputs go to platen/build/quick/ and never to results/platen/.
"""
from __future__ import annotations

import argparse
import time

from . import common as CM

ALL = ("tremor", "accepted", "sensitivity", "report")


def _timings(quick: bool, stage: str, elapsed: float) -> None:
    """The first pass of each stage (from empty caches) is kept; later passes, which reuse cached cases, go under
    'reruns' (the last one)."""
    p = CM.cache_dir(quick) / "timings.json"
    d = CM.jload(p) or {"stages": {}}
    if stage in d["stages"]:
        d.setdefault("reruns", {})[stage] = round(elapsed, 1)
    else:
        d["stages"][stage] = round(elapsed, 1)
    CM.jdump(p, d)


def stage_tremor(a) -> None:
    from . import tremor as T
    for i in T.plan(a.quick)["notes"]:
        T.run_note(i, a.quick)


def stage_accepted(a) -> None:
    from . import accepted as A
    A.run_batch(a.quick)
    A.run_sensitivity(a.quick)


def stage_sensitivity(a) -> None:
    from . import sensitivity as S
    from . import tremor as T
    for i in T.plan(a.quick)["notes"]:
        S.run_note(i, a.quick)


def stage_report(a) -> None:
    from . import report as R
    R.write(a.quick)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", nargs="*", default=list(ALL), choices=list(ALL))
    a = ap.parse_args(argv)
    t00 = time.time()
    for st in a.stages:
        CM.log(f"== stage {st}{' (quick)' if a.quick else ''}")
        t0 = time.time()
        {"tremor": stage_tremor, "accepted": stage_accepted, "sensitivity": stage_sensitivity,
         "report": stage_report}[st](a)
        _timings(a.quick, st, time.time() - t0)
        CM.log(f"== stage {st} done in {time.time() - t0:.0f} s")
    CM.log(f"done in {time.time() - t00:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
