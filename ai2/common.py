"""Shared helpers: stage caches, job mapping, JSON encoding, the scenario conventions of aiprior (read-only)."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Sequence

import numpy as np

from . import BUILD_DIR, RESULTS_DIR, ensure_paths

ensure_paths()


def cache_dir(quick: bool) -> Path:
    d = BUILD_DIR / ("quick" if quick else "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(quick: bool) -> Path:
    d = (BUILD_DIR / "quick" / "results") if quick else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def jdefault(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def save(name: str, obj, quick: bool) -> Path:
    p = cache_dir(quick) / f"{name}.json"
    p.write_text(json.dumps(obj, default=jdefault))
    return p


def load(name: str, quick: bool):
    p = cache_dir(quick) / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def jmap(fn: Callable, jobs: Sequence, workers: int = 1) -> List:
    """Map over jobs with at most 2 processes (the plan's compute rule); each worker is single-threaded."""
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(v, "1")
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, 2)) as ex:
        return list(ex.map(fn, jobs))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def mean_of(rows: List[Dict], key: str, where: Callable[[Dict], bool] = lambda r: True) -> float:
    v = [r[key] for r in rows if where(r) and r.get(key) is not None and np.isfinite(r[key])]
    return float(np.mean(v)) if v else float("nan")
