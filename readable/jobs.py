"""A small job runner: at most two worker processes (spawned), one job at a time each, results as JSON on disk.

Every job is a module-level function called with plain keyword arguments; it writes its own outputs into readable/build
(one JSON per case, so a stopped run resumes where it stopped) and returns a small summary.  The main process only
waits while the workers run.  Each worker uses one numerical thread (readable._env) and loads the AI reader once.
"""
from __future__ import annotations

import importlib
import time
import traceback
from typing import Dict, List, Sequence

MAX_WORKERS = 2


def _call(spec: Dict) -> Dict:
    t0 = time.time()
    try:
        import readable  # noqa: F401  (sets the environment first)
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass
        mod = importlib.import_module(spec["module"])
        res = getattr(mod, spec["func"])(**spec.get("kwargs", {}))
        return {"job": spec["name"], "ok": True, "elapsed_s": time.time() - t0, "result": res}
    except Exception:
        return {"job": spec["name"], "ok": False, "elapsed_s": time.time() - t0, "error": traceback.format_exc()}


def run(specs: Sequence[Dict], workers: int = MAX_WORKERS, log=print) -> List[Dict]:
    """Run the jobs (longest first as listed) on min(workers, 2) processes; returns their summaries."""
    workers = max(1, min(int(workers), MAX_WORKERS))
    out = []
    if not specs:
        return out
    if workers == 1 or len(specs) == 1:
        for s in specs:
            r = _call(s)
            _report(r, log)
            out.append(r)
        return out
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers, maxtasksperchild=None) as pool:
        for r in pool.imap_unordered(_call, list(specs), chunksize=1):
            _report(r, log)
            out.append(r)
    return out


def _report(r: Dict, log) -> None:
    if r["ok"]:
        log(f"[jobs] {r['job']} done in {r['elapsed_s']:.0f} s")
    else:
        log(f"[jobs] {r['job']} FAILED after {r['elapsed_s']:.0f} s:\n{r['error']}")


def job(name: str, module: str, func: str, **kwargs) -> Dict:
    return {"name": name, "module": module, "func": func, "kwargs": kwargs}
