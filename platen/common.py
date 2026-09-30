"""Shared helpers: paths, logging, JSON I/O, study R's bootstrap and measures, study F's frozen curve (all read-only).

Nothing here writes outside platen/build and results/platen.  In particular the DeltaPen-class page model of
realdata (realdata.hw1.page_model, which re-fits and SAVES a cache file when its cached version is old) is never
called: the platen's position reference is an absolute desk-frame sensor, so every estimator here sees the pen's
IMU with study E's IDEAL page-sensor stream (1 kHz, 2 ms, 3 um white noise; E's labelled bound, which E found gives
the same result as the DeltaPen-class sensor for its chosen design: tip-tremor ratio 0.69 against 0.69).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, REPO_ROOT, RESULTS_DIR

CACHE = BUILD_DIR / "cache"
QUICK = BUILD_DIR / "quick"
F_CACHE = REPO_ROOT / "readable" / "build" / "cache"          # study F's per-case caches (read-only)
F_RESULTS = REPO_ROOT / "results" / "readable" / "readable.json"
F_FROZEN = REPO_ROOT / "results" / "readable" / "frozen.json"
E_FROZEN = REPO_ROOT / "results" / "realtrack" / "frozen.json"
GROUNDED_BATCH = REPO_ROOT / "results" / "improvement" / "mechanics" / "grounded_batch.json"
GROUNDED_DERIV = REPO_ROOT / "results" / "improvement" / "mechanics" / "grounded_derivative_check.json"
SE_MANIFEST = REPO_ROOT / "results" / "improvement" / "writing" / "grounded_accepted" / "manifest.json"
BOOT_SEED = 20260929          # study R's writer bootstrap seed
PEN_MASS_HW1 = 0.012 + 1e-6   # HW1's ordinary pen as the plant integrates it (12 g + the 1e-6 kg tip placeholder)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def cache_dir(quick: bool, sub: str = "") -> Path:
    d = (QUICK / "cache" if quick else CACHE) / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(quick: bool) -> Path:
    """results/platen for full runs; platen/build/quick/results for --quick (never overwrites results/platen)."""
    d = (QUICK / "results") if quick else RESULTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _jd(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def jdump(path: Path, obj, indent: Optional[int] = 1) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, default=_jd, indent=indent, allow_nan=True))
    tmp.replace(path)


def jload(path: Path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def h(*key) -> int:
    return int(hashlib.sha1(":".join(map(str, key)).encode()).hexdigest()[:8], 16)


def sha256_file(path: Path) -> Optional[str]:
    path = Path(path)
    if not path.exists():
        return None
    s = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            s.update(b)
    return s.hexdigest()


def boot(per_writer: Dict[str, float], seed: int = BOOT_SEED) -> Dict:
    """Study R's writer bootstrap (realdata.hw1._boot): mean over writers and its 95 % interval."""
    from realdata import hw1 as H
    return H._boot(per_writer, seed)


def per_writer(cases: Sequence[Dict], fn) -> Dict[str, float]:
    acc: Dict[str, List[float]] = {}
    for c in cases:
        v = fn(c)
        if v is not None and np.isfinite(v):
            acc.setdefault(c["writer"], []).append(float(v))
    return {w: float(np.mean(v)) for w, v in acc.items()}


def of10(d: Optional[Dict]) -> float:
    if not d or not d.get("words_total"):
        return float("nan")
    return 10.0 * float(d["words_read"]) / max(float(d["words_total"]), 1.0)


def fmt_ci(b: Optional[Dict], nd: int = 2, scale: float = 1.0) -> str:
    if not b or b.get("mean") is None or not np.isfinite(b.get("mean", np.nan)):
        return "-"
    return f"{b['mean'] * scale:.{nd}f} ({b['lo'] * scale:.{nd}f} to {b['hi'] * scale:.{nd}f})"


# ------------------------------------------------------------------ study F's frozen words curve (read-only)
def f_curve() -> Dict:
    fr = json.loads(F_FROZEN.read_text())
    return {"p": fr["e13"]["fit"]["p"], "r_plus2_mm": fr["e13"]["r_plus2_mm"], "r_80_mm": fr["e13"]["r_80_mm"],
            "w_ord_severe": fr["e13"]["w_ord_severe"], "w_clean": fr["e13"]["w_clean"]}


def words_via_curve(r_mm: float, p=None) -> float:
    from readable import curve as CV
    p = p if p is not None else f_curve()["p"]
    if r_mm is None or not np.isfinite(r_mm):
        return float("nan")
    return float(CV.model(r_mm, p))


# ------------------------------------------------------------------ the reader (study R's instrument, unchanged)
_READER = {"ready": False}


def reader_ready() -> str:
    """R's reader choice (realdata/build/cache/reader_choice.json, read-only): TrOCR base, literal."""
    from realdata import ocr as OC
    if not _READER["ready"]:
        rc = OC.reader_choice(log=lambda *a, **k: None)
        _READER.update({"ready": True, "chosen": rc["chosen"]})
    return _READER["chosen"]


class _W:
    def __init__(self, written):
        self.written = written


def measures(written, res, scn, f0: float, read: bool) -> Dict:
    """Study R's results-card measures (realdata.hw1.measures, unchanged) on an HW1-format result, plus E's broadband
    residual (0.5-20 Hz RMS of ink - intended in contact)."""
    from handwriting import params as PR
    from realdata import hw1 as H
    from realtrack import servo as SV
    if read:
        reader_ready()
    m = H.measures(_W(written), res, scn, PR.ordinary_pen(), ocr=read, f0=f0)
    k = np.clip(np.round(res.t / scn.dt).astype(int), 0, len(scn.t) - 1)
    dec = max(1, int(round((1.0 / float(res.t[1] - res.t[0])) / 1000.0)))
    m["bb_um"] = SV.broadband_um(res.t[::dec], res.ink[::dec], np.asarray(scn.intended)[k][::dec], res.contact[::dec],
                                 (0.5, 20.0))
    return m


def git_rev() -> str:
    from stabpen import provenance as PV
    return PV.git_revision()


def mean_finite(x: Iterable[float]) -> float:
    v = np.array([float(a) for a in x if a is not None and np.isfinite(float(a))])
    return float(v.mean()) if len(v) else float("nan")
