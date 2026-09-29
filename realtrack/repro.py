"""Step 1: reproduce study R's baseline with R's own code (realdata.hw1.run_case, read-only), in quick form.

R's quick plan (realdata.hw1.plan(quick=True)): test note 0 (UNIPEN hpb2 test writer 'an'), PD and ET tremor of the test
split at the severe class's representative amplitude (1.72 mm), and the same note without tremor.  The cases are rebuilt
here from scratch with R's case keys and seeds and every pen of R's card is run again (ordinary pen, Rev H tracker, Rev J
gated tracker, Rev J TCN, perfect knowledge; ideal and DeltaPen-class page sensors), read by the same AI reader.  The
numbers are compared field by field with R's cached case files (realdata/build/cache/hw1/full_v2, read-only).

If every field agrees, R's cached per-case results of its 91-case full run are the SAME computation, and the test stage
(test.py) re-uses them for R's pens instead of recomputing them (it recomputes only the new designs, on the same
scenario objects and sensor draws).  Nothing is written into realdata/.  SIMULATION (model HW1, real inputs).
"""
from __future__ import annotations

import json
import time
from typing import Dict, List

import numpy as np

from . import CACHE_DIR, REPO_ROOT

R_CACHE = REPO_ROOT / "realdata" / "build" / "cache" / "hw1" / "full_v2"
OUT = CACHE_DIR / "repro"
FIELDS = ("tip_tremor_mm", "ink_err_um", "band_err_um", "words_read", "words_total", "cer", "false_correction_um",
          "coverage", "q_rms_mm")


def quick_cases() -> List[Dict]:
    return [{"file": "real_w0_PD_severe", "note": 0, "kind": "PD", "class": "severe"},
            {"file": "real_w0_ET_severe", "note": 0, "kind": "ET", "class": "severe"},
            {"file": "clean_real_w0", "note": 0, "kind": None, "class": None}]


def run(log=print, cases=None) -> Dict:
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import ocr as OC
    OUT.mkdir(parents=True, exist_ok=True)
    OC.reader_choice(log=log)                      # sets R's chosen reader (TrOCR base), from R's cached choice
    H.ai2_models()
    H.page_model(False, log)
    rows = []
    wr = None
    for c in (cases or quick_cases()):
        p = OUT / f"{c['file']}.json"
        if p.exists():
            res = json.loads(p.read_text())
        else:
            t0 = time.time()
            wr = wr or H.real_writer("test", c["note"])
            if c["kind"] is None:
                dev = H.run_case(wr, None, 0.0, 0.0, f"clean:{c['note']}")
                res = {"set": "clean_real", "writer": wr.written.real["writer"], "note": c["note"], "devices": dev}
            else:
                cls = c["class"]
                dr = RL.tremor_for(wr.written, cls, seed=c["note"], kind=c["kind"], split="test",
                                   amp_mm=RL.classes(False)[cls]["representative_mm"])
                dev = H.run_case(wr, dr.d, dr.meta["f0"], dr.meta["amp_mm"] * 1e-3,
                                 f"real:{c['note']}:{c['kind']}:{cls}", ocr_devices=H.OCR_BY_CLASS.get(cls, H.OCR_REAL))
                res = {"set": "real", "writer": wr.written.real["writer"], "note": c["note"], "kind": c["kind"],
                       "class": cls, "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")},
                       "devices": dev}
            res["_elapsed_s"] = time.time() - t0
            p.write_text(json.dumps(res, default=H._jd))
            log(f"[repro] {c['file']} in {res['_elapsed_s']:.0f} s: " + H._fmt(res["devices"]))
        rows.append(compare(c["file"], res))
    ok = all(r["identical"] for r in rows)
    summary = {"cases": rows, "all_identical": ok, "max_abs_diff": max(r["max_abs_diff"] for r in rows),
               "rule": "every field of every pen equal to R's cached case (abs difference <= 1e-9); then R's cached "
                       "per-case results are re-used for R's pens in the test stage",
               "evidence": "SIM (R's code re-run here) compared with SIM (R's cache)"}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    log(f"[repro] identical to R's cache: {ok} (max abs difference {summary['max_abs_diff']:.3g})")
    return summary


def compare(name: str, mine: Dict) -> Dict:
    r = json.loads((R_CACHE / f"{name}.json").read_text())
    diffs = []
    n = 0
    for dev, v in r["devices"].items():
        if not isinstance(v, dict) or dev.startswith("_"):
            continue
        m = mine["devices"].get(dev)
        if m is None:
            diffs.append({"device": dev, "missing": True})
            continue
        for f in FIELDS:
            if f in v:
                n += 1
                a, b = m.get(f), v.get(f)
                if a is None or b is None:
                    if a != b:
                        diffs.append({"device": dev, "field": f, "mine": a, "R": b})
                    continue
                d = abs(float(a) - float(b))
                if not (d <= 1e-9 or (np.isnan(float(a)) and np.isnan(float(b)))):
                    diffs.append({"device": dev, "field": f, "mine": a, "R": b, "abs_diff": d})
    md = max([d.get("abs_diff", 0.0) for d in diffs] + [0.0])
    return {"case": name, "fields_compared": n, "differences": diffs, "identical": not diffs, "max_abs_diff": md,
            "words": {dev: (mine["devices"][dev].get("words_read"), r["devices"][dev].get("words_read"))
                      for dev in r["devices"] if isinstance(r["devices"][dev], dict) and "words_read" in r["devices"][dev]},
            "tip_tremor_mm": {dev: (round(float(mine["devices"][dev].get("tip_tremor_mm", np.nan)), 4),
                                    round(float(r["devices"][dev].get("tip_tremor_mm", np.nan)), 4))
                              for dev in r["devices"] if isinstance(r["devices"][dev], dict) and dev in mine["devices"]}}


if __name__ == "__main__":
    run()
