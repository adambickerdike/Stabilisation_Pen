"""Shared helpers: stage caches, logging, JSON with provenance, figures with CSV twins, stable hashes."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, RESULTS_DIR, ensure_paths

ensure_paths()

_LOG_FILE: Optional[Path] = None


def set_log_file(p: Optional[Path]) -> None:
    global _LOG_FILE
    _LOG_FILE = p
    if p is not None:
        p.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if _LOG_FILE is not None:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def cache_dir(quick: bool) -> Path:
    d = BUILD_DIR / ("quick" if quick else "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(quick: bool) -> Path:
    """Final results go to results/ai3; a --quick run never overwrites them."""
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
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def save(name: str, obj, quick: bool) -> Path:
    p = cache_dir(quick) / f"{name}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, default=jdefault))
    tmp.replace(p)                                   # atomic: a crash never leaves half a cache
    return p


def load(name: str, quick: bool):
    p = cache_dir(quick) / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stable_hash(s: str, mod: int = 100) -> int:
    """Deterministic bucket of a string (sha256), for splits that never depend on Python's hash seed."""
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:12], 16) % mod


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(evidence: str, seeds=None, extra: Optional[Dict] = None) -> Dict:
    """stabpen.provenance metadata (git revision, parameter digest, command, library versions)."""
    from stabpen import provenance as P
    md = P.metadata(evidence, seeds=seeds, extra=extra)
    try:
        import torch
        md["torch"] = torch.__version__
    except Exception:
        pass
    return md


def write_result(name: str, obj: Dict, quick: bool, evidence: str, seeds=None) -> Path:
    body = dict(obj)
    body["stabpen.provenance"] = provenance(evidence, seeds=seeds, extra={"package": "ai3"})
    p = out_dir(quick) / name
    p.write_text(json.dumps(body, indent=1, default=jdefault))
    return p


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for r in rows:
            w.writerow([("%.6g" % v) if isinstance(v, float) else v for v in r])


def mean_ci(x: Sequence[float], n_boot: int = 2000, seed: int = 0, alpha: float = 0.05):
    """Mean and a percentile bootstrap CI."""
    a = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    bs = rng.choice(a, size=(n_boot, a.size), replace=True).mean(1)
    return float(a.mean()), float(np.percentile(bs, 100 * alpha / 2)), float(np.percentile(bs, 100 * (1 - alpha / 2)))


def wilson(k: int, n: int, z: float = 1.96):
    """Wilson score interval for a proportion k/n."""
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(p), float(max(0.0, c - h)), float(min(1.0, c + h))


def timer():
    t0 = time.time()
    return lambda: time.time() - t0
