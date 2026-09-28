"""One command for the whole study: python3 -m aiprior.run_study [--quick] [--workers 2] [--stages ...]

Stages (each caches its output in aiprior/build/cache/, git-ignored):
  t0       tuning, stage T0: the tracker the AI sits on (tuning writers 100-103, seed 300; confirmation seed 301)
  t1       tuning, stage T1: the AI prior settings (rule in tuning.py)
  t2       tuning, stage T2: the AI guidance settings
  test     every variant on the test grid: writers 0-5 x seeds 200-203 x 6/8/10 Hz x 0.3/1/2 mm, plus tremor-free writing
  report   figures, aiprior.json, samples.json, evidence_rows.csv (results/aiprior/)

--quick: 2 test writers, 1 seed, and 2 tuning writers; outputs go to aiprior/build/quick/ (never over the results).
At most 2 worker processes; each worker is limited to 1 numerical thread.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from . import AMPS, BUILD_DIR, F0S, RESULTS_DIR, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS  # noqa: E402

STAGES = ("t0", "t1", "t2", "test", "report")
TEST_VARIANTS = ["none", "revH_off", "tracker", "tracker_rt", "tracker_sev", "oracle",
                 "prior_ai_correct", "prior_ai_predicted", "prior_wrong_full", "prior_oracle",
                 "guide_ai_correct", "guide_ai_predicted", "guide_wrong_full", "guide_oracle",
                 "clean_tracker", "clean_tracker_rt", "clean_revH_off", "clean_bs_tracker"]
FREE_VARIANTS = ["tracker", "tracker_rt", "tracker_sev", "prior_ai_correct", "prior_ai_predicted", "prior_wrong_full",
                 "guide_ai_correct", "guide_ai_predicted", "guide_wrong_full", "clean_tracker", "clean_tracker_rt"]


def cache_dir(quick: bool) -> Path:
    d = BUILD_DIR / ("quick" if quick else "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(name: str, obj, quick: bool) -> Path:
    p = cache_dir(quick) / f"{name}.json"
    p.write_text(json.dumps(obj, default=_default))
    return p


def load(name: str, quick: bool):
    p = cache_dir(quick) / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _default(o):
    import numpy as np
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


def _map(fn, jobs, workers):
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, 2)) as ex:
        return list(ex.map(fn, jobs))


def stage_t0(quick, workers):
    from . import tuning as TU
    writers = TUNE_WRITERS[:2] if quick else TUNE_WRITERS
    seeds = TUNE_SEEDS[:1] if quick else TUNE_SEEDS
    cands = TU.base_candidates()
    jobs = [{"writer": w, "seeds": seeds, "cands": cands} for w in writers]
    outs = _map(TU.t0_job, jobs, workers)
    sel = TU.select_t0(outs, seeds=(TUNE_SEEDS[0],))
    conf = TU.select_t0(outs, seeds=(TUNE_SEEDS[1],)) if len(seeds) > 1 else None
    cmap = {TU.key(c): c for c in cands}
    out = {"outs": outs, "selection": sel, "confirmation_seed_301": conf, "chosen": cmap[sel["chosen_key"]],
           "candidates": {TU.key(c): c for c in cands}}
    out["amp_gate_a_lo"] = TU.amp_gate_from_t0(outs, sel["chosen_key"])
    save("t0", out, quick)
    return out


def stage_ai(stage, quick, workers):
    from . import tuning as TU
    t0 = load("t0", quick)
    base = t0["chosen"]
    # T1 runs on two tuning writers only: the exploration on tuning writer 100 showed the prior was not promising, so
    # it was documented under its rule and not polished (tuning.py)
    writers = TUNE_WRITERS[:2] if (quick or stage == "T1") else TUNE_WRITERS
    seeds = TUNE_SEEDS[:1]
    cands = TU.prior_candidates() if stage == "T1" else TU.guide_candidates(t0["amp_gate_a_lo"])
    cases = ["ai_correct", "ai_predicted", "wrong_full"]
    jobs = [{"writer": w, "seeds": seeds, "cands": cands, "base": base, "stage": stage, "cases": cases,
             "amps": AMPS, "tremor_free": True} for w in writers]
    outs = _map(TU.ai_job, jobs, workers)
    sel = TU.select_ai(outs, stage, cands, seeds=seeds)
    out = {"outs": outs, "selection": sel, "candidates": cands, "base": base}
    save(stage.lower(), out, quick)
    return out


def test_job(job):
    from . import core as CO
    from . import study as SD
    t0 = time.time()
    wr = CO.Writer(job["writer"])
    rows, viz = [], {}
    for seed in job["seeds"]:
        for f0 in job["f0s"]:
            for amp in job["amps"]:
                sc = CO.make_scenario(wr, f0, amp, seed)
                keep = job.get("viz") and seed == job["viz"]["seed"] and [f0, amp * 1e3] in job["viz"]["cases"]
                ev = SD.evaluate(sc, job["cfg"], job["variants"], keep=bool(keep))
                if keep:
                    from handwriting import metrics as MT
                    runs = ev.pop("_runs")
                    viz[f"{f0:g}Hz_{amp * 1e3:g}mm"] = {k: MT.decimate_path(r, hz=250.0).tolist() for k, r in runs.items()}
                rows.append(ev)
    free = SD.tremor_free(wr, job["cfg"], job["free_variants"])
    out = {"writer": wr.w, "rows": rows, "tremor_free": free, "elapsed_s": time.time() - t0}
    if viz:
        from handwriting import metrics as MT
        viz["intended"] = MT.intended_path(wr.scn0, hz=250.0).tolist()
        viz["x_height_mm"] = wr.written.style.x_height_mm
        out["viz"] = viz
    return out


def info_setting(t: dict) -> dict:
    """The setting shown on the test grid: the rule's choice if a candidate passed; otherwise (not adopted), for
    information, the candidate with the fewest wrong letters at full confidence (ties: lowest ink error)."""
    s = t["selection"]
    if s["best_passing"] is not None:
        return t["candidates"][int(s["best_passing"])]
    k = min(s["table"], key=lambda c: (s["table"][c]["flips_wrong_full"], s["table"][c]["J_ink_1_2mm_um"]))
    return t["candidates"][int(k)]


def stage_test(quick, workers):
    t0 = load("t0", quick)
    t1 = load("t1", quick)
    t2 = load("t2", quick)
    sev = None
    if t0:
        tab = t0["selection"]["table"]
        k_sev = min((k for k in tab if k != "revh"), key=lambda k: tab[k]["J_ink_1_2mm_um"])
        sev = t0["candidates"][k_sev]
    cfg = {"base": t0["chosen"] if t0 else None, "sev": sev,
           "prior": info_setting(t1) if t1 else {}, "guide": info_setting(t2) if t2 else {},
           "adopted": {"prior": bool(t1 and t1["selection"]["adopted"]), "guide": bool(t2 and t2["selection"]["adopted"])}}
    writers = TEST_WRITERS[:2] if quick else TEST_WRITERS
    seeds = TEST_SEEDS[:1] if quick else TEST_SEEDS
    viz = {"writer": 0, "seed": 200, "cases": [[6.0, 1.0], [8.0, 2.0], [10.0, 1.0]]}
    jobs = [{"writer": w, "seeds": seeds, "f0s": F0S, "amps": AMPS, "cfg": cfg, "variants": TEST_VARIANTS,
             "free_variants": FREE_VARIANTS, "viz": viz if w == viz["writer"] else None} for w in writers]
    # longest job first (writer 0 keeps the figure runs)
    outs = _map(test_job, jobs, workers)
    out = {"outs": outs, "cfg": cfg, "writers": list(writers), "seeds": list(seeds)}
    save("test", out, quick)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--stages", nargs="+", default=list(STAGES), choices=STAGES)
    a = ap.parse_args(argv)
    t_all = time.time()
    for st in a.stages:
        t = time.time()
        if st == "t0":
            r = stage_t0(a.quick, a.workers)
            print(f"[t0] chosen {r['selection']['chosen_key']} ({time.time() - t:.0f} s)", flush=True)
        elif st in ("t1", "t2"):
            r = stage_ai(st.upper(), a.quick, a.workers)
            s = r["selection"]
            print(f"[{st}] best passing {s['best_passing']} adopted {s['adopted']} ({time.time() - t:.0f} s)", flush=True)
        elif st == "test":
            stage_test(a.quick, a.workers)
            print(f"[test] done ({time.time() - t:.0f} s)", flush=True)
        elif st == "report":
            from . import report as RP
            RP.build(quick=a.quick)
            print(f"[report] done ({time.time() - t:.0f} s)", flush=True)
    print(f"total {time.time() - t_all:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
