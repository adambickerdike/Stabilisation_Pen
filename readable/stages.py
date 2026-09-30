"""The job functions the workers run (module level, plain keyword arguments) and the freeze.

Order (run.py): predictor (main process) -> tuning jobs (E13 notes, E11 choice, gap notes; two workers) -> freeze (main
process: the E13 curve, thresholds and test levels, the E11 rules, the predictor; written to frozen.json with its time
BEFORE any test case is built) -> test jobs (one per test note: E13 confirmation, E11 calibration, gap; two workers) ->
report.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Dict, Optional

from . import RESULTS_DIR
from . import common as CM


def results_dir(quick: bool) -> Path:
    d = (CM.QUICK_DIR / "results") if quick else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def frozen_path(quick: bool) -> Path:
    return results_dir(quick) / "frozen.json"


def predictor_path(quick: bool) -> Path:
    return CM.cache_dir(quick) / "gap" / "predictor.json"


def load_predictor(quick: bool) -> Dict:
    ar = CM.jload(predictor_path(quick))
    if ar is None:
        raise RuntimeError("the AR predictor has not been fitted (stage 'predictor')")
    return ar


# ------------------------------------------------------------------ jobs
def job_e13_tune(i: int, quick: bool = False) -> Dict:
    from . import e13
    return e13.tune_note(i, quick)


def job_gap_tune(i: int, quick: bool = False) -> Dict:
    from . import gap
    return gap.tune_note(i, load_predictor(quick), quick)


def job_e11_tune(quick: bool = False) -> Dict:
    from . import e11
    r = e11.tune(quick)
    return {"job": "e11_tune", "choice": {k: v["choice"]["rule"] for k, v in r["designs"].items()}}


def job_test(i: int, quick: bool = False) -> Dict:
    """Everything of test note i, after the freeze: E13 confirmation, E11 calibration, the gap decomposition."""
    from . import e11, e13, gap
    fr = CM.jload(frozen_path(quick))
    if fr is None:
        raise RuntimeError("frozen.json is missing: the test runs only after the freeze")
    t0 = time.time()
    wr = CM.test_writer(i)
    files = []
    files += e13.test_note(wr, i, fr, quick)
    files += e11.test_note(wr, i, fr, quick)
    files += gap.test_note(wr, i, load_predictor(quick), quick)
    return {"job": f"test_w{i}", "files": files, "elapsed_s": time.time() - t0}


def job_gap_test_clean(i: int, quick: bool = False) -> Dict:
    """After the test stage: the clean-writing change of every full estimator on R's clean test note i."""
    from . import gap
    t0 = time.time()
    wr = CM.test_writer(i)
    files = gap.test_clean(wr, i, load_predictor(quick), quick)
    return {"job": f"gap_test_clean_w{i}", "files": files, "elapsed_s": time.time() - t0}


def job_sensing(kind: str, quick: bool = False) -> Dict:
    """After the test stage: what the pen's sensors allow with the tremor alone (tuning split only)."""
    from . import gap
    p = CM.cache_dir(quick) / "gap" / f"sensing_{kind}.json"
    if not p.exists():
        CM.jdump(p, gap.sensing_check(kind, quick))
    return {"job": f"sensing_{kind}", "files": [p.name]}


# ------------------------------------------------------------------ the freeze
def freeze(quick: bool, log=CM.log, force: bool = False) -> Dict:
    """Fit the E13 curve on the tuning cases, read off the thresholds, set the test levels; take the E11 rules and the
    predictor; write frozen.json (once: an existing freeze is kept unless force)."""
    from . import e11, e13
    from . import report as RP
    p = frozen_path(quick)
    old = CM.jload(p)
    if old is not None and not force:
        log(f"[freeze] kept the existing freeze of {old.get('frozen_utc')}")
        return old
    real, clean = e13.load_cases(quick, "tuning")
    if not real:
        raise RuntimeError("no E13 tuning cases: run the tuning stage first")
    f = e13.fits(real, clean)
    pooled = f["pooled"]
    lv = e13.freeze_levels(pooled)
    tu = e11.tune(quick)
    ar = load_predictor(quick)
    fr = {"stabpen.provenance": RP.provenance(quick, "SIMULATION (tuning split only); frozen before the test run"),
          "frozen_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "e13": {"fit": pooled["fit"], "r_plus2_mm": pooled.get("r_plus2_mm"), "r_80_mm": pooled.get("r_80_mm"),
                  "r_within1_mm": pooled.get("r_within1_mm"),
                  "ci95": pooled.get("ci95"), "w_ord_severe": pooled.get("w_ord_severe"),
                  "w_clean": pooled.get("w_clean"), "test_levels": lv, "n_cases": len(real), "n_clean": len(clean)},
          "e11": {"choice": {k: v["choice"] for k, v in tu["designs"].items()}, "grid": tu["rules"],
                  "rule_text": e11.__doc__.split("CALIBRATION RULE")[1].split("TEST (once")[0].strip()},
          "gap": {"predictor": {"choice": ar["choice"], "delta_s": ar["delta_s"], "lead_s": ar["lead_s"]}},
          "note": "Written after the tuning runs and before any test case was built; the test runs once."}
    CM.jdump(p, fr)
    log(f"[freeze] E13 tuning: r_plus2 {pooled.get('r_plus2_mm')}, r_80 {pooled.get('r_80_mm')}; E11 "
        + ", ".join(f"{k} {v['choice']['rule']}" for k, v in tu["designs"].items()) + f" -> {p}")
    return fr
