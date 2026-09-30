"""One command for study X (the re-baseline):

    python3 -m rebaseline.run                  every stage in order (hours of CPU; resumable: finished cases are cached)
    python3 -m rebaseline.run --quick          a smoke run of every stage (minutes; outputs in rebaseline/build/quick,
                                               never in results/)
    python3 -m rebaseline.run --stages impact sim2j_causal summary --jobs 2

Stages (each simulation stage runs in its own process: sim2j and bnib are configured per process at run time):
  impact              the impact register -> results/rebaseline/impact_register.{csv,json}
  sim2j_causal        task 2, causal sensing (current defaults), headline then the other ET cells
  sim2j_legacy_flags  task 2, the legacy optimistic flags on the current code
  sim2j_legacy_exact  task 2, the flags + the historical firmware contact channel (reproduction check, writers 0-1)
  bnib_revK           task 3, Rev K's nib with DEC-066's servo and corrected loads (writers 0-5)
  bnib_cand15         task 3, the 24 mm / 1.5 mm candidate (writers 0-5)
  bnib_ladder         task 3, the attribution ladder (study B now / exact / DEC-066 / Rev K linear; writers 0-1)
  reach               task 4, study F's reach cases with the balanced nib's servo and mass
  page_re             task 5, studies R and E with the version-2 page model
  page_gap            task 5, study F's gap rows and its page sensing check with the version-2 page model
  summary             results/rebaseline/*.json from the cached rows
  report              the evidence rows and the tables quoted by docs/rebaseline.md
With --quick every stage writes only under rebaseline/build/quick (the impact register and the report included).
At most two worker processes (--jobs 1 or 2); one numerical thread each.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from typing import Dict, List

from . import BUILD_DIR, REPO_ROOT
from . import common as CM

PY = sys.executable
STAGES: Dict[str, List[List[str]]] = {
    "impact": [["-m", "rebaseline.impact"]],
    "sim2j_causal": [["-m", "rebaseline.sim2j_cards", "--mode", "causal", "--phase", "headline"],
                     ["-m", "rebaseline.sim2j_cards", "--mode", "causal", "--phase", "other"]],
    "sim2j_legacy_flags": [["-m", "rebaseline.sim2j_cards", "--mode", "legacy_flags", "--phase", "headline"],
                           ["-m", "rebaseline.sim2j_cards", "--mode", "legacy_flags", "--phase", "other"]],
    "sim2j_legacy_exact": [["-m", "rebaseline.sim2j_cards", "--mode", "legacy_exact", "--phase", "headline",
                            "--writers", "0,1"]],
    "bnib_revK": [["-m", "rebaseline.bnib_rerun", "--config", "revK_corrected"]],
    "bnib_cand15": [["-m", "rebaseline.bnib_rerun", "--config", "cand15_corrected"]],
    "bnib_ladder": [["-m", "rebaseline.bnib_rerun", "--config", c, "--writers", w] for c, w in
                    (("B1_studyB_now", "0,1"), ("B1_dec066", "0,1"), ("revK_linear", "0,1"),
                     ("B1_studyB_exact", "0"))],
    "reach": [["-m", "rebaseline.reach_b1", "--run"]],
    "page_re": [["-m", "rebaseline.page_v2", "--re"]],
    "page_gap": [["-m", "rebaseline.page_v2", "--gap"], ["-m", "rebaseline.page_v2", "--sensing"]],
    "summary": [["-m", "rebaseline.sim2j_cards", "--summarise"], ["-m", "rebaseline.bnib_rerun", "--summarise"],
                ["-m", "rebaseline.reach_b1", "--summarise"], ["-m", "rebaseline.page_v2", "--summarise"]],
    "report": [["-m", "rebaseline.report"]],
}
ORDER = ("impact", "sim2j_causal", "sim2j_legacy_flags", "bnib_revK", "bnib_cand15", "reach", "page_gap", "page_re",
         "sim2j_legacy_exact", "bnib_ladder", "summary", "report")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stages", nargs="+", default=list(ORDER))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--jobs", type=int, default=1, choices=(1, 2))
    a = ap.parse_args(argv)
    bad = [s for s in a.stages if s not in STAGES]
    if bad:
        CM.log(f"unknown stages {bad}; known: {list(STAGES)}")
        return 2
    logs = BUILD_DIR / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    queue = []
    for s in a.stages:
        for k, cmd in enumerate(STAGES[s]):
            queue.append((s, k, [PY] + cmd + (["--quick"] if a.quick else [])))
    running: List = []
    failed = []
    t0 = time.time()
    serial = {"summary", "report", "impact"}
    while queue or running:
        # summary/report wait for everything before them; simulation stages fill up to --jobs workers
        while queue and len(running) < a.jobs and not (queue[0][0] in serial and running):
            s, k, cmd = queue.pop(0)
            lf = open(logs / f"run_{s}_{k}{'_quick' if a.quick else ''}.log", "a")
            CM.log(f"start {s}[{k}]: {' '.join(cmd[1:])}")
            running.append((s, k, subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=lf, stderr=subprocess.STDOUT),
                            time.time()))
            if s in serial:
                break
        for item in list(running):
            s, k, p, ts = item
            if p.poll() is not None:
                running.remove(item)
                CM.log(f"done {s}[{k}] rc {p.returncode} in {time.time() - ts:.0f} s")
                if p.returncode != 0:
                    failed.append(f"{s}[{k}]")
        time.sleep(2.0)
    CM.log(f"all stages in {time.time() - t0:.0f} s; failed: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
