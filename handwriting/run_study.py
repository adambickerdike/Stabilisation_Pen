#!/usr/bin/env python3
"""One command for the handwriting-outcomes study (model HW1).  Evidence status: SIMULATION / CALCULATION.

  python3 -m handwriting.run_study            # full study (about 50 min with 2 worker processes here)
  python3 -m handwriting.run_study --quick    # reduced grid (about 4 min), same outputs, marked "quick"
  python3 -m handwriting.run_study --stages figures   # redraw figures and pages from the cached stage outputs

Stages: tuning (writers >= 100, seeds >= 300 only), et, et_sens, pd, practice, crosscheck, figures (figures, samples.json,
outcomes.json, evidence_rows.csv).  Final numbers use aiguide test writers 0-5 and seeds 200-203.
Outputs: results/handwriting/ (outcomes.json, samples.json, fig_*.png + CSV twins, evidence_rows.csv, _cache/).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from . import RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, ensure_paths

ensure_paths()
CACHE = RESULTS_DIR / "_cache"
STAGES = ("tuning", "et", "et_sens", "pd", "practice", "crosscheck", "figures")


def _limit_threads():
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(k, "1")
    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass


def _pool(fn, jobs, workers):
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=workers, initializer=_limit_threads) as ex:
        return list(ex.map(fn, jobs))


def _compact(o, sig: int = 6):
    """Round floats to `sig` significant digits (the caches are committed; paths are in mm, metrics in um)."""
    import numpy as np
    if isinstance(o, dict):
        return {k: _compact(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_compact(v, sig) for v in o]
    if isinstance(o, np.ndarray):
        return _compact(o.tolist(), sig)
    if isinstance(o, (float, np.floating)):
        x = float(o)
        return float(f"{x:.{sig}g}") if x == x and abs(x) != float("inf") else x
    return o


def _save(name, obj):
    CACHE.mkdir(parents=True, exist_ok=True)
    obj = json.loads(json.dumps(obj, default=_default))
    (CACHE / f"{name}.json").write_text(json.dumps(_compact(obj), separators=(",", ":")))


def _load(name):
    p = CACHE / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _inputs() -> dict:
    """One snapshot of the device and tracker inputs for a whole stage (other studies may rewrite these files)."""
    import hashlib
    from . import params as PR
    from . import REPO_ROOT
    files = {}
    for rel in ("results/opt/inertial_tracker_revh.json", "results/opt/tracker_models/akf_ship.json",
                "results/revH/tip_params.json", "results/board/board_params.json", "config/parameters.yaml"):
        p = REPO_ROOT / rel
        if p.exists():
            b = p.read_bytes()
            gen = None
            try:
                gen = json.loads(b).get("meta", {}).get("generated_utc")
            except Exception:
                pass
            files[rel] = {"sha256_16": hashlib.sha256(b).hexdigest()[:16], "generated_utc": gen}
    return {"files": files, "trackers": {"ship": PR.akf_ship(), "revh": PR.akf_revh()}, "revh_pen": PR.rev_h()}


def _tuned(quick: bool) -> dict:
    """Choices made on tuning data (writers >= 100, seeds >= 300) that the final stages use."""
    tu = (_load("tuning_quick") if quick else None) or _load("tuning") or {}
    out = {}
    tau = (tu.get("size_tau") or {}).get("chosen")
    if tau is not None:
        out["tau_sa"] = float(tau)
    return out


def _default(o):
    import numpy as np
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ------------------------------------------------------------------ stage jobs (module-level for multiprocessing)
def _et_job(job):
    from . import et_study as ET
    return ET.writer_job(job)


def _pd_job(job):
    from . import pd_study as PD
    return PD.writer_job(job)


def _pr_job(job):
    from . import practice as PRC
    return PRC.writer_job(job)


def _cc_job(job):
    from . import crosscheck as CC
    from . import params as PR
    return CC.scenario(job["writer"], job["seed"], job["f0"], job["amp"], PR.akf_ship())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="reduced grid for a fast check")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--stages", nargs="*", default=list(STAGES), choices=STAGES)
    args = ap.parse_args(argv)
    _limit_threads()
    from . import et_study as ET
    from . import pd_study as PD
    from . import practice as PRC
    q = args.quick
    tag = "_quick" if q else ""
    writers = TEST_WRITERS[:2] if q else TEST_WRITERS
    seeds = TEST_SEEDS[:1] if q else TEST_SEEDS
    t_all = time.time()
    log = {}
    if "tuning" in args.stages:
        from . import tuning as TU
        t0 = time.time()
        _save("tuning" + tag, TU.run(quick=q))
        log["tuning_s"] = time.time() - t0
    if "et" in args.stages:
        t0 = time.time()
        f0s = (6.0, 10.0) if q else ET.F0S
        amps = (0.3e-3, 1.0e-3, 2.0e-3)
        inp = _inputs()
        jobs = [{"writer": w, "seeds": list(seeds), "f0s": list(f0s), "amps": list(amps), "viz": w == ET.VIZ["writer"],
                 "trackers": inp["trackers"], "revh_pen_nominal": inp["revh_pen"]} for w in writers]
        outs = _pool(_et_job, jobs, args.workers)
        _save("et" + tag, {"outs": outs, "aggregate": ET.aggregate(outs), "grid": {"writers": list(writers),
                                                                                 "seeds": list(seeds), "f0s": list(f0s),
                                                                                 "amps_mm": [a * 1e3 for a in amps]},
                           "inputs": {"files": inp["files"], "trackers": inp["trackers"],
                                      "revh_pen": inp["revh_pen"].describe()}})
        log["et_s"] = time.time() - t0
    if "et_sens" in args.stages:
        t0 = time.time()
        from . import params as PR
        sw = writers[:2] if q else writers
        inp = _inputs()
        base = {"seeds": [seeds[0]], "f0s": [6.0, 10.0], "amps": [0.3e-3, 1.0e-3], "distortion": False,
                "trackers": inp["trackers"], "revh_pen_nominal": inp["revh_pen"]}
        variants = {
            "open_loop_hand": {"hand": {"writer_comp": "none"}},
            "stiff_grip_x2": {"hand": {"K_grip": 1150.0, "C_grip": 2.6}},
            "contact_gating": {"ctl": {"gating": "contact"}},
            "revH_lead_defaults": {"revh_pen": PR.rev_h_lead(), "devices": ["none", "revH_off", "revH_akf", "revH_akf_revh", "revH_oracle"]},
        }
        res = {}
        for name, v in variants.items():
            jobs = [dict(base, writer=w, **v) for w in sw]
            outs = _pool(_et_job, jobs, args.workers)
            res[name] = {"aggregate": ET.aggregate(outs), "variant": {k: (str(x) if k == "revh_pen" else x) for k, x in v.items()}}
        res["_inputs"] = {"files": inp["files"]}
        _save("et_sens" + tag, res)
        log["et_sens_s"] = time.time() - t0
    if "pd" in args.stages:
        t0 = time.time()
        tuned = _tuned(q)
        jobs = [{"writer": w, "seeds": list(seeds), "viz": w == PD.VIZ["writer"],
                 "tau_sa": tuned.get("tau_sa", PD.TAU_SA_DEFAULT)} for w in writers]
        outs = _pool(_pd_job, jobs, args.workers)
        _save("pd" + tag, {"outs": outs, "aggregate": PD.aggregate(outs), "tau_sa": jobs[0]["tau_sa"]})
        log["pd_s"] = time.time() - t0
    if "practice" in args.stages:
        t0 = time.time()
        jobs = [{"writer": w, "seeds": list(seeds), "viz": w == PRC.VIZ["writer"]} for w in writers]
        outs = _pool(_pr_job, jobs, args.workers)
        _save("practice" + tag, {"outs": outs, "aggregate": PRC.aggregate(outs), "board": outs[0].get("board")})
        log["practice_s"] = time.time() - t0
    if "crosscheck" in args.stages:
        t0 = time.time()
        cw = writers[:1] if q else writers
        jobs = [{"writer": w, "seed": seeds[0], "f0": f0, "amp": a} for w in cw for f0 in (6.0, 10.0) for a in (0.3e-3, 1.0e-3)]
        rows = _pool(_cc_job, jobs, args.workers)
        import numpy as np
        summ = {}
        for f0 in (6.0, 10.0):
            for a in (0.3e-3, 1.0e-3):
                sel = [r for r in rows if r["f0"] == f0 and abs(r["amp_mm"] - a * 1e3) < 1e-9]
                summ[f"{f0:g}Hz_{a * 1e3:g}mm"] = {m: {k: float(np.mean([r[m][k] for r in sel])) for k in ("oracle_band_ratio", "akf_band_ratio")}
                                                 for m in ("P1", "HW1", "HW1_nominal")}
        _save("crosscheck" + tag, {"rows": rows, "summary": summ})
        log["crosscheck_s"] = time.time() - t0
    if "figures" in args.stages:
        t0 = time.time()
        from . import report as RP
        RP.build(quick=q, timing=log)
        log["figures_s"] = time.time() - t0
    log["total_s"] = time.time() - t_all
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
