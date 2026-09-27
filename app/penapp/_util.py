"""Shared helpers: canonical JSON, hashing, clocks, stroke-id ranges, paths."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

APP_DIR = Path(__file__).resolve().parents[1]      # <repo>/app
REPO_ROOT = APP_DIR.parent                          # <repo>


# ------------------------------------------------------------------ hashing
def canonical_json(obj) -> bytes:
    """Deterministic JSON encoding used for every digest in the store.

    Sorted keys, no insignificant whitespace, UTF-8, NaN/Infinity rejected.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------- clocks
def utc_now() -> str:
    """Current UTC time, ISO 8601 with milliseconds and a 'Z' suffix."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class FixedClock:
    """Deterministic clock for reproducible demos and tests.

    Returns ``start`` advanced by ``step_ms`` on every call.  Values produced by
    this clock are synthetic and must be labelled as such wherever reported.
    """

    def __init__(self, start_iso: str = "2026-01-01T00:00:00.000Z", step_ms: int = 1):
        self._t = _dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        self._step = _dt.timedelta(milliseconds=step_ms)

    def __call__(self) -> str:
        v = self._t
        self._t = self._t + self._step
        return v.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def unix_ms_to_iso(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000.0, _dt.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


# ------------------------------------------------------------ stroke ranges
def ranges_from_ids(ids: Iterable[int]) -> List[List[int]]:
    """Compress stroke ids into sorted inclusive ``[first, last]`` ranges.

    Only consecutive integers are merged, so every id inside a range is one of
    the given ids (stroke ids need not be contiguous in a session).
    """
    out: List[List[int]] = []
    for i in sorted({int(v) for v in ids}):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def ids_from_ranges(ranges: Sequence[Sequence[int]]) -> List[int]:
    out = set()
    for a, b in ranges:
        if b < a:
            raise ValueError(f"invalid stroke range [{a}, {b}]")
        out.update(range(int(a), int(b) + 1))
    return sorted(out)


def merge_ranges(*range_lists) -> List[List[int]]:
    ids: set = set()
    for rl in range_lists:
        ids.update(ids_from_ranges(rl))
    return ranges_from_ids(ids)


def format_ranges(ranges: Sequence[Sequence[int]]) -> str:
    return ",".join(f"{a}" if a == b else f"{a}-{b}" for a, b in ranges)


# -------------------------------------------------------------- provenance
def ensure_stabpen_importable() -> None:
    """Make the repository root importable so ``stabpen`` can be used."""
    try:
        import stabpen  # noqa: F401
    except ImportError:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))


def git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.call(["git", "-C", str(REPO_ROOT), "diff", "--quiet", "HEAD"],
                                stderr=subprocess.DEVNULL) != 0
        return rev + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def environment_info() -> dict:
    info = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import numpy
        info["numpy"] = numpy.__version__
    except Exception:
        pass
    import sqlite3
    info["sqlite"] = sqlite3.sqlite_version
    return info


def rel_to_repo(path) -> str:
    """Repository-relative path for reports (absolute if outside the repo)."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def write_json(path, obj, *, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False, allow_nan=False, default=_json_default)
        f.write("\n")
    os.replace(tmp, path)


def _json_default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
    except Exception:
        pass
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")
