"""Shared helpers: provenance, JSON I/O, a resumable row cache, bootstrap intervals and logging.

Provenance (the block every results JSON carries under "stabpen.provenance"): the git revision (with a dirty flag: other
agents work in the same clone), SHA-256 of every input file named by the stage (source files and data), the seeds, the
parameters, the command, and the python / numpy / scipy / mujoco versions.  The git revision alone would not pin the
code (the tree may be dirty), so the source hashes are the operative record.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, REPO_ROOT, RESULTS_DIR, __version__


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------ JSON
def _jd(o):
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def clean(x):
    """Replace non-finite floats by None (strict JSON) recursively."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, np.generic):
        return clean(x.item())
    return x


def jdump(path, obj, indent: Optional[int] = 1) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(clean(obj), default=_jd, indent=indent, allow_nan=False) + "\n")
    tmp.replace(path)
    return path


def jload(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


# ------------------------------------------------------------------ provenance
def sha256_file(path) -> Optional[str]:
    path = Path(path)
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_revision() -> Dict:
    def git(*a):
        try:
            return subprocess.check_output(["git", "-C", str(REPO_ROOT), *a], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return None
    head = git("rev-parse", "HEAD")
    dirty = None
    try:
        dirty = subprocess.call(["git", "-C", str(REPO_ROOT), "diff", "--quiet", "HEAD"], stderr=subprocess.DEVNULL) != 0
    except Exception:
        pass
    return {"head": head, "short": head[:7] if head else None, "dirty_tree": dirty,
            "note": "other agents work in this clone at the same time; the source hashes below pin the code that ran"}


def input_hashes(paths: Iterable) -> Dict[str, Optional[str]]:
    out = {}
    for p in paths:
        p = Path(p)
        if not p.is_absolute():
            p = REPO_ROOT / p
        try:
            key = str(p.relative_to(REPO_ROOT))
        except ValueError:
            key = str(p)
        out[key] = sha256_file(p)
    return out


def versions() -> Dict[str, Optional[str]]:
    v = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "scipy", "mujoco", "numba", "torch"):
        try:
            m = __import__(mod)
            v[mod] = getattr(m, "__version__", None)
        except Exception:
            v[mod] = None
    return v


def provenance(evidence: str, inputs: Sequence = (), seeds=None, parameters: Optional[Dict] = None,
               extra: Optional[Dict] = None) -> Dict:
    md = {"evidence_status": evidence, "package": f"rebaseline {__version__}",
          "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
          "git": git_revision(), "command": " ".join([os.path.basename(sys.argv[0])] + sys.argv[1:]),
          "cwd": os.getcwd(), "seeds": seeds, "parameters": parameters or {}, "input_sha256": input_hashes(inputs),
          "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS")}}
    md.update(versions())
    if extra:
        md.update(extra)
    return md


def write_result(name: str, body: Dict, evidence: str, inputs: Sequence = (), seeds=None,
                 parameters: Optional[Dict] = None, extra: Optional[Dict] = None, quick: bool = False) -> Path:
    """results/rebaseline/<name>.json (quick runs: rebaseline/build/quick/<name>.json, never a result)."""
    out = {"stabpen.provenance": provenance(evidence, inputs, seeds, parameters, extra)}
    out.update(body)
    base = (BUILD_DIR / "quick") if quick else RESULTS_DIR
    return jdump(base / f"{name}.json", out)


# ------------------------------------------------------------------ resumable rows
class Rows:
    """Rows cached in rebaseline/build/<name>_rows.json, keyed; a stopped stage resumes where it stopped."""

    def __init__(self, name: str, quick: bool = False):
        d = BUILD_DIR / ("quick" if quick else "rows")
        d.mkdir(parents=True, exist_ok=True)
        self.path = d / f"{name}_rows.json"
        self.rows: Dict[str, Dict] = {}
        if self.path.exists():
            try:
                self.rows = json.loads(self.path.read_text())
            except Exception:
                self.rows = {}
        self._t = time.time()

    def has(self, k: str) -> bool:
        return k in self.rows

    def get(self, k: str) -> Optional[Dict]:
        return self.rows.get(k)

    def put(self, k: str, row: Dict, save: bool = False) -> None:
        self.rows[k] = clean({kk: v for kk, v in row.items() if not str(kk).startswith("_")})
        if save or time.time() - self._t > 15.0:
            self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.rows, default=_jd))
        tmp.replace(self.path)
        self._t = time.time()

    def values(self) -> List[Dict]:
        return list(self.rows.values())


# ------------------------------------------------------------------ statistics (descriptive; small synthetic samples)
def boot_mean(values: Sequence[float], n_boot: int = 5000, seed: int = 20260930) -> Dict:
    """Mean and 95 % percentile bootstrap interval over the given units (cases or writers).  A description of this
    sample's spread, not a population or patient interval."""
    v = np.array([float(x) for x in values if x is not None and np.isfinite(float(x))])
    if len(v) == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    if len(v) == 1:
        return {"mean": float(v[0]), "lo": float(v[0]), "hi": float(v[0]), "n": 1}
    rng = np.random.default_rng(seed)
    bs = v[rng.integers(0, len(v), (n_boot, len(v)))].mean(axis=1)
    return {"mean": float(v.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "n": int(len(v))}


def cluster_boot_mean(values: Sequence[float], clusters: Sequence, n_boot: int = 5000, seed: int = 20260930) -> Dict:
    """Mean over cases with a 95 % bootstrap interval that resamples CLUSTERS (writers): cases of one writer are not
    independent."""
    v = np.array([float(x) for x in values], dtype=float)
    c = np.array([str(x) for x in clusters])
    ok = np.isfinite(v)
    v, c = v[ok], c[ok]
    if len(v) == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0, "n_clusters": 0}
    ids = sorted(set(c))
    groups = [v[c == i] for i in ids]
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        bs.append(float(np.concatenate([groups[j] for j in pick]).mean()))
    return {"mean": float(v.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "n": int(len(v)), "n_clusters": len(ids)}


def mean_or_none(values: Iterable) -> Optional[float]:
    v = [float(x) for x in values if x is not None and np.isfinite(float(x))]
    return float(np.mean(v)) if v else None
