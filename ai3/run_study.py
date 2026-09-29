"""One command for study S: python3 -m ai3.run_study [--quick] [--stages ...]

Stages (each caches its result in ai3/build/cache (or ai3/build/quick) and resumes from it):
  online   task 1: train and test the online letter recogniser on real handwriting (UJI; Character Trajectories)
  calib    task 1: the writer-calibrated recogniser (rule O4)
  lm       the NG1x language model (ai2's NG1 recipe), for tasks 2 and 3
  spell    task 2: the spelling checker on real misspellings (Birkbeck, Holbrook)
  cues     task 2: physical feedback simulation (assumed writer responses)
  words    word recognition CER/WER (writer- and session-disjoint, with/without LM); recognition-aware spelling
  plan     physical completion of an accepted word: reach-limited planner with the hand's advance
  predict  task 3: personalised text prediction on public-domain journals
  trace    task 4a: why close tracing lowers legibility (drive study's HW1-D runs)
  shape    task 4b: shape assist and clean copy on real handwriting in HW1
  ocr      spot check of task 4b's sample words with study R's word reader (TrOCR)
  report   figures with CSV twins, ai3.json, samples.json, evidence_rows.csv
  demo     the prototype page ai3/demo/index.html (inlined model, lexicon, error model and tuned settings); its
           smoke test: NODE_PATH=$(npm root -g) node ai3/demo/smoke_test.js
--quick runs every stage small and writes to ai3/build/quick/ only (never to results/ai3).
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from . import BUILD_DIR
from . import common as C

ALL = ["online", "calib", "lm", "spell", "cues", "words", "plan", "predict", "trace", "shape", "ocr", "report", "demo"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", nargs="*", default=ALL)
    ap.add_argument("--force", action="store_true", help="recompute stages even if cached")
    a = ap.parse_args(argv)
    C.set_log_file(BUILD_DIR / "logs" / ("run_quick.log" if a.quick else "run.log"))
    t0 = time.time()
    failed = []
    for st in a.stages:
        t1 = time.time()
        cached = C.load({"spell": "spell_NG1x", "calib": "online_cal"}.get(st, st), a.quick)
        if cached is not None and not a.force and st not in ("report", "demo"):
            C.log(f"[run] {st}: cached")
            continue
        C.log(f"[run] stage {st} ...")
        try:
            _run_stage(st, a.quick)
        except Exception:                                    # log and go on: later stages may not depend on it
            import traceback
            C.log(f"[run] stage {st} FAILED:\n{traceback.format_exc()}")
            failed.append(st)
            continue
        C.log(f"[run] {st} done in {(time.time() - t1) / 60:.1f} min")
    C.log(f"[run] all done in {(time.time() - t0) / 60:.1f} min" + (f"; FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


def _run_stage(st: str, quick: bool) -> None:
    class _A:
        pass
    a = _A()
    a.quick = quick
    if True:
        if st == "online":
            from . import stage_online
            stage_online.run(a.quick)
        elif st == "calib":
            from . import stage_online
            stage_online.run_calibrated(a.quick)
        elif st == "lm":
            from . import lmx
            _, info = lmx.ng1x(a.quick)
            C.save("lm", info, a.quick)
        elif st == "spell":
            from . import lmx, stage_spell
            import numpy as np
            pred, _ = lmx.ng1x(a.quick)
            on = C.load("online", a.quick) or {}
            cal = C.load("online_cal", a.quick) or {}
            confs = {}
            if on.get("test", {}).get("confusion_full_letter"):
                M = np.asarray(on["test"]["confusion_full_letter"], float)
                confs["writer_independent"] = M / np.maximum(M.sum(1, keepdims=True), 1)
            if cal.get("test", {}).get("confusion_full_letter"):
                M = np.asarray(cal["test"]["confusion_full_letter"], float)
                confs["calibrated"] = M / np.maximum(M.sum(1, keepdims=True), 1)
            stage_spell.run(a.quick, pred=pred, lm_name="NG1x", rec_conf=confs)
        elif st == "cues":
            from . import stage_cues
            stage_cues.run(a.quick)
        elif st == "words":
            from . import stage_words
            stage_words.run(a.quick)
        elif st == "plan":
            from . import complete_plan
            complete_plan.run(a.quick)
        elif st == "predict":
            from . import stage_predict
            stage_predict.run(a.quick)
        elif st == "trace":
            from . import tracing_diag
            C.save("trace", tracing_diag.run(a.quick), a.quick)
        elif st == "shape":
            from . import stage_shape
            stage_shape.run(a.quick)
        elif st == "ocr":
            from . import ocr_check
            ocr_check.run(a.quick)
        elif st == "report":
            from . import report
            report.run(a.quick)
        elif st == "demo":
            from .demo import build
            build.main(["--quick"] if a.quick else [])
        else:
            raise KeyError(f"unknown stage {st!r} (stages: {ALL})")


if __name__ == "__main__":
    raise SystemExit(main())
