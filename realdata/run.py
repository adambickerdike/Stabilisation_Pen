"""One command for study R:  python3 -m realdata.run [--quick] [--stages fetch tremor writing kinematics hw1 figures report]

Stages (each resumes from its cache in realdata/build/cache; the container may restart):
  fetch       download any missing dataset (sources.py), never overwriting present files
  tremor      the tremor library (tremorlib.build): parameters, thresholds, classes, splits, waveforms
  writing     the BRUSH writer statistics (writer sizes, lower-case recordings, splits) and a check of the reader
  kinematics  validation of real and synthetic writers against the literature (kinematics.validate)
  hw1         the headline comparison on real inputs and the bridge sets (hw1.run; one case per cache file)
  figures     figures with CSV twins, the before/after pictures (committed: CC BY inputs only)
  report      results/realdata/realdata.json, samples.json, evidence_rows.csv
--quick writes to realdata/build/quick/ (results) and uses fewer writers and cases; it never overwrites the published
results.  One process, one numerical thread (REALDATA_THREADS=1 by default).
"""
from __future__ import annotations

import argparse
import json
import time

from . import BUILD_DIR, CACHE_DIR, RESULTS_DIR

ALL = ("fetch", "tremor", "writing", "kinematics", "hw1", "figures", "report")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def out_dir(quick: bool):
    d = (BUILD_DIR / "quick" / "results") if quick else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def stage_fetch(quick: bool):
    from . import sources as SO
    for k in SO.SOURCES:
        if not SO.present(k):
            log(f"[fetch] {k}")
            try:
                SO.fetch(k)
            except Exception as e:                  # a refused site is recorded, the study continues
                log(f"[fetch] {k} failed: {e!r}")
    if not (BUILD_DIR / "raw" / "pads" / "preprocessed" / "movement").exists():
        log("[fetch] PADS movement files: run realdata/build/raw/pads/dl_pads.py (selection and checksums)")


def stage_tremor(quick: bool):
    from . import tremorlib as TL
    p = CACHE_DIR / ("tremorlib_quick.json" if quick else "tremorlib.json")
    if p.exists():
        log(f"[tremor] cached {p.name}")
        return
    TL.build(quick=quick, log=log)


def stage_writing(quick: bool):
    from . import writinglib as WL
    st = WL.brush_writer_stats(log=log)
    log(f"[writing] BRUSH: {len(st['writers'])} writers; tuning {len(WL.brush_writers('tuning', st))}, "
        f"test {len(WL.brush_writers('test', st))} (>= 6 lower-case word recordings)")


def stage_kinematics(quick: bool):
    from . import kinematics as KI
    p = CACHE_DIR / ("kinematics_quick.json" if quick else "kinematics.json")
    if p.exists():
        log(f"[kinematics] cached {p.name}")
        return
    val = KI.validate(quick=quick, log=log)
    p.write_text(json.dumps(val, default=str))


def stage_hw1(quick: bool):
    from . import hw1 as H
    out = H.run(quick=quick, log=log)
    log(f"[hw1] {len(out['cases'])} cases")


def stage_figures(quick: bool):
    from . import report as RP
    RP.figures(quick, out_dir(quick), log=log)


def stage_report(quick: bool):
    from . import report as RP
    RP.write(quick, out_dir(quick), log=log)


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
