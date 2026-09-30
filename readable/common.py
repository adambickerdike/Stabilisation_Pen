"""Shared helpers: study R's and study E's objects (read-only), the measures, R-format results cards, JSON I/O.

Everything that builds a scenario reuses R's and E's own code and seeds, so that a case here is the same case as there:
  tuning  E's selection set (realtrack.cases): note i of R's tuning split (writer i % 5), PD and ET tremor of tuning
          patients of the note's fold, the nose-held Rev J run, E's sensor seeds; the ordinary pen on the same hand,
          writing and tremor.  Rebuilt exactly as realtrack.cases.build_case does (checked against E's cache).
  test    R's test cases (realdata.hw1): test note i (writer i), R's tremor draw (seed i) at the class representative,
          R's case keys for the sensor seeds (realdata.hw1.make_scen).  R's cached per-case results (ordinary pen,
          perfect knowledge, clean notes) are merged in, as study E did.
Measures are R's (realdata.hw1.measures: words read by TrOCR base, literal; tip tremor = sqrt(2) x RMS of the major axis
of ink - intended in contact, f0 +- 2 Hz; ink error; band error; coverage) plus E's broadband residual (0.5-20 Hz).
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, REPO_ROOT

CACHE = BUILD_DIR / "cache"
QUICK_DIR = BUILD_DIR / "quick"
R_CACHE = REPO_ROOT / "realdata" / "build" / "cache" / "hw1" / "full_v2"
E_TEST_CACHE = REPO_ROOT / "realtrack" / "build" / "cache" / "test"
E_FROZEN = REPO_ROOT / "results" / "realtrack" / "frozen.json"
KINDS = ("PD", "ET")
BOOT_SEED = 20260929          # R's writer bootstrap seed (hw1._boot)
N_BOOT = 2000


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def cache_dir(quick: bool) -> Path:
    d = (QUICK_DIR / "cache") if quick else CACHE
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


def jdump(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, default=_jd, indent=1))
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


def frozen_e() -> Dict:
    """Study E's frozen designs (results/realtrack/frozen.json, read-only)."""
    return json.loads(E_FROZEN.read_text())


def page_model_version() -> int:
    """The version of the page model (realdata.hw1.page_model) that this process's DeltaPen-class streams use: recorded
    in every case file whose rows read that sensor."""
    from realdata import hw1 as H
    return H.page_model().version


def one_page_model_version(files: Sequence[Dict], what: str) -> Optional[int]:
    """Case files aggregated together must share one page-model version (realdata.hw1.one_page_model_version)."""
    from realdata import hw1 as H
    return H.one_page_model_version(files, what)


# ------------------------------------------------------------------ the reader (R's instrument, unchanged)
_READER = {"ready": False}


def reader_ready(log_=None) -> str:
    """R's reader choice (realdata/build/cache/reader_choice.json, read-only): sets realdata.ocr.MODEL to TrOCR base."""
    from realdata import ocr as OC
    if not _READER["ready"]:
        rc = OC.reader_choice(log=log_ or (lambda *a, **k: None))
        _READER.update({"ready": True, "chosen": rc["chosen"]})
    return _READER["chosen"]


class _W:
    """What realdata.hw1.measures needs from a writer: .written."""

    def __init__(self, written):
        self.written = written


def broadband_um(res, scn, band=(0.5, 20.0)) -> float:
    """E's T1 residual (realtrack.servo.broadband_um) on a full-plant run: RMS of ink - intended in contact (after 0.5 s),
    0.5-20 Hz, zero-phase measurement filter, on the 1 kHz samples R's tip-tremor measure uses."""
    from realtrack import servo as SV
    k = np.clip(np.round(res.t / scn.dt).astype(int), 0, len(scn.t) - 1)
    dec = max(1, int(round((1.0 / float(res.t[1] - res.t[0])) / 1000.0)))
    return SV.broadband_um(res.t[::dec], res.ink[::dec], np.asarray(scn.intended)[k][::dec], res.contact[::dec], band)


def measures(written, res, scn, pen, f0: float, read: bool) -> Dict:
    """R's results-card measures (realdata.hw1.measures, unchanged) + E's broadband residual."""
    from realdata import hw1 as H
    if read:
        reader_ready()
    m = H.measures(_W(written), res, scn, pen, ocr=read, f0=f0)
    m["bb_um"] = broadband_um(res, scn)
    return m


def false_correction_um(sJ, res) -> float:
    """ai2's false correction (realdata's 'clean writing moved'): RMS over contact of ink against the nose-held ink."""
    from ai2 import delayed as DL
    return DL.ink_timeline_error(sJ, res, np.zeros(sJ.n_ticks), sJ.neutral)


# ------------------------------------------------------------------ tuning cases (E's selection set)
def tuning_spec(note: int, kind: Optional[str], level: str) -> Dict:
    from realtrack import cases as C
    sid = f"tune_n{note}_clean" if kind is None else f"tune_n{note}_{kind}_{level}"
    for s in C.tuning_specs():
        if s["id"] == sid:
            return s
    raise KeyError(sid)


def tuning_note(i: int):
    from realtrack import cases as C
    return C.tuning_note(i)


def tuning_tremor(note, spec: Dict):
    """The spec's tremor draw exactly as realtrack.cases.build_case makes it."""
    from realdata import library as RL
    return RL.tremor(spec["level"] if spec["level"] in ("severe", "moderate", "mild") else "severe",
                     seed=int(spec["tseed"]), kind=spec["kind"], split=spec["split"], t=note.written.intended.t,
                     amp_mm=float(spec["amp_mm"]), rid=spec["rid"])


class TuneCase:
    """One tuning case rebuilt in the full plant: the Rev J scenario and nose-held run, the ordinary pen's scenario,
    the perfect-knowledge command (R's handwriting.tracker.oracle_command), and (on request) E's sensor streams."""

    def __init__(self, note, spec: Dict, streams: bool = False):
        from handwriting import plant as PL
        from handwriting import tracker as TR
        from realtrack import cases as C
        self.note, self.spec = note, spec
        self.written = note.written
        dr = tuning_tremor(note, spec)
        self.dr = dr
        self.f0 = float(dr.meta["f0"])
        self.pen = note.pens["revJ"]
        self.scn = note.scenario("revJ", dr.d)
        self.neutral = PL.run(self.scn, self.pen, note.hand, ctl=PL.Controls())
        self.clean = note.clean["revJ"]
        self.scn_clean = note.scenario("revJ", None)
        self.Ts = float(self.neutral.info["Ts"])
        self.n_ticks = int(self.neutral.info["n_ticks"])
        self.tick_t = np.arange(self.n_ticks) * self.Ts
        self.q_oracle = TR.oracle_command(self.neutral, self.clean, self.pen, self.n_ticks, self.Ts)
        self.s_seed = C._h(spec["id"], "revJ") % (2 ** 31)
        self.streams_i = self.streams_d = None
        if streams:
            self.make_streams()

    def make_streams(self):
        from aiprior import core as CO
        from realdata import hw1 as H
        from realdata import sensors as RS
        self.streams_i = CO.streams_for(self.neutral, self.scn, self.pen, self.note.trk, self.s_seed)
        self.streams_d = RS.degrade_page(self.streams_i, H.page_model(), self.s_seed + 17)
        return self.streams_d

    def run(self, q: Optional[np.ndarray]):
        from handwriting import plant as PL
        if q is None:
            return self.neutral
        return PL.run(self.scn, self.pen, self.note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))

    def ordinary(self):
        from handwriting import plant as PL
        scn_n = self.note.scenario("none", self.dr.d)
        return PL.run(scn_n, self.note.pens["none"], self.note.hand), scn_n

    def tremor_meta(self) -> Dict:
        return {k: self.dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "source", "looped", "kind")}


# ------------------------------------------------------------------ test cases (R's)
def test_writer(i: int):
    from realdata import hw1 as H
    return H.real_writer("test", i)


class TestCase:
    """R's test case (note i, kind, class) rebuilt with R's code and seeds: the Rev J scenario and nose-held run with the
    DeltaPen-class streams (R's headline sensor), the oracle command, R's cached per-case results."""

    def __init__(self, wr, i: int, kind: Optional[str], cls: Optional[str], sensor: str = "deltapen"):
        from handwriting import tracker as TR
        from realdata import hw1 as H
        from realdata import library as RL
        self.wr, self.i, self.kind, self.cls = wr, i, kind, cls
        self.written = wr.written
        pm = H.page_model()
        if kind is None:
            self.dr, tremor, f0, amp = None, None, 0.0, 0.0
            key = f"clean:{i}"
        else:
            self.dr = RL.tremor_for(wr.written, cls, seed=i, kind=kind, split="test",
                                    amp_mm=RL.classes(False)[cls]["representative_mm"])
            tremor, f0, amp = self.dr.d, float(self.dr.meta["f0"]), self.dr.meta["amp_mm"] * 1e-3
            key = f"real:{i}:{kind}:{cls}"
        self.f0 = f0
        self.key = key
        self.sJ = H.make_scen(wr, "revJ", tremor, f0, amp, 0, H._seed(key, "revJ"),
                              page=None if sensor == "ideal" else pm)
        self.pen = self.sJ.pen
        self.scn = self.sJ.scn
        self.neutral = self.sJ.neutral
        self.clean = wr.su.clean["revJ"]
        self.scn_clean = wr.su.scenario("revJ", None)
        self.Ts = float(self.sJ.Ts)
        self.n_ticks = int(self.sJ.n_ticks)
        self.tick_t = np.arange(self.n_ticks) * self.Ts
        self.q_oracle = None if kind is None else TR.oracle_command(self.neutral, self.clean, self.pen,
                                                                     self.n_ticks, self.Ts)
        self.s_seed = H._seed(key, "revJ")

    @property
    def streams_d(self):
        return self.sJ.streams

    @property
    def dh_revh(self):
        return self.sJ.dh

    def run(self, q: Optional[np.ndarray]):
        from handwriting import plant as PL
        if q is None:
            return self.neutral
        return PL.run(self.scn, self.pen, self.wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))

    def ordinary(self):
        from handwriting import plant as PL
        scn_n = self.wr.su.scenario("none", None if self.dr is None else self.dr.d)
        return PL.run(scn_n, self.wr.pens["none"], self.wr.hand), scn_n

    def r_name(self) -> str:
        return f"clean_real_w{self.i}" if self.kind is None else f"real_w{self.i}_{self.kind}_{self.cls}"

    def r_cached(self) -> Optional[Dict]:
        return jload(R_CACHE / f"{self.r_name()}.json")

    def e_cached(self) -> Optional[Dict]:
        return jload(E_TEST_CACHE / f"{self.r_name()}.json")

    def tremor_meta(self) -> Dict:
        return {} if self.dr is None else {k: self.dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")}


class CaseLike:
    """What realtrack.estimators.estimate needs from a case: .spec (split and fold, for the learned models' fold choice)
    and .dh_revh(sensor) (the Rev H tracker's estimate, used only by the 'gated' family)."""

    def __init__(self, spec: Dict, dh=None):
        self.spec = spec
        self._dh = dh

    def dh_revh(self, sensor):
        return self._dh


# ------------------------------------------------------------------ R-format results cards
def card(sel: List[Dict], devices: Sequence[str], clean: Optional[List[Dict]] = None) -> Dict:
    """realdata.hw1.card (R's results card, writer bootstrap) on R-format cases."""
    from realdata import hw1 as H
    return H.card(sel, devices, clean)


def boot(per_writer: Dict[str, float], seed: int = BOOT_SEED) -> Dict:
    from realdata import hw1 as H
    return H._boot(per_writer, seed)


def per_writer(sel: List[Dict], dev: str, metric: str = "", ref: Optional[str] = None, fn=None) -> Dict[str, float]:
    from realdata import hw1 as H
    return H._per_writer(sel, dev, metric, ref, fn)


def of10(d, r=None) -> float:
    return 10.0 * float(d["words_read"]) / max(float(d["words_total"]), 1.0) if d.get("words_total") else float("nan")


def signal_residual_mm(err_ticks: np.ndarray, tick_t: np.ndarray, t1k: np.ndarray, contact1k: np.ndarray,
                       f0: float) -> float:
    """R's tip-tremor measure applied to an error SIGNAL (m, per tick) instead of ink - intended: the residual one part
    of an estimator's error would leave at the tip if the servo passed it with gain 1 (it does at 3-14 Hz: E's delay
    analysis).  Same band (f0 +- 2 Hz), segments (contact >= 0.5 s), trim and convention (sqrt(2) x RMS, major axis)."""
    from realtrack import servo as SV
    e = np.column_stack([np.interp(t1k, tick_t, err_ticks[:, 0]), np.interp(t1k, tick_t, err_ticks[:, 1])])
    return SV.tip_tremor_mm(t1k, e, np.zeros_like(e), contact1k, f0)


def grid_1k(res, scn) -> Dict[str, np.ndarray]:
    """The 1 kHz samples of a run that R's measure uses (every 4th record sample)."""
    dec = max(1, int(round((1.0 / float(res.t[1] - res.t[0])) / 1000.0)))
    return {"t1k": res.t[::dec].copy(), "contact1k": res.contact[::dec].copy()}


def git_short() -> str:
    from stabpen import provenance as PV
    return PV.git_revision()


def mean_finite(x: Iterable[float]) -> float:
    v = np.array([float(a) for a in x if a is not None and np.isfinite(float(a))])
    return float(v.mean()) if len(v) else float("nan")
