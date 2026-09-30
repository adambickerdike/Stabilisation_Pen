"""Tuning and test cases on REAL inputs (study R's library, read-only) in model HW1, and their compact on-disk cache.

A case = one real note (UNIPEN hpb2, ballpoint on paper) + one real tremor recording (UCI PD tip tremor or Zenodo ET
hand tremor, scaled to a tip amplitude) + the Rev J nose held centred (the "neutral" run whose sensor streams every
tracker sees, R's and ai2's convention) + the pen's sensor streams with the ideal page sensor (3 um white noise, a
labelled bound) and with the DeltaPen-class page sensor (R's headline sensor) + the true handle tremor
d = handle(tremor, nose held) - handle(no tremor, nose held) (the perfect-knowledge target, never shown to a tracker).

TUNING SET (rules fixed here before any tracker ran on it; realtrack only ever reads R's TUNING split for choices):
  notes      tuning note seeds 0-9 of realdata.library.writing('tuning', seed): note i is written by tuning writer
             i % 5 (5 tuning writers, 2 notes each, tuning texts only)
  tremor     per note, PD and ET, at four tip amplitudes: the severe class's representative 1.72 mm (the DEC-055
             condition), 0.6 mm (the severe class's lower part), the moderate representative 0.24 mm and the mild
             representative 0.098 mm; each waveform is a TUNING-split recording of a subject in the note's fold
  folds      fold k = tuning writer k + the tuning subjects of rank k mod 5 (sorted per kind: PD 11 subjects -> fold
             sizes 3/2/2/2/2, ET 9 -> 2/2/2/2/1); a learned estimator selected on fold k's cases is trained without
             fold k's writer and subjects (cross-fitting), so every tuning score is out of sample for writers and
             patients
  clean      the same 10 notes without tremor (clean-writing change)
TEST SET: exactly study R's (realdata.hw1.plan): 9 test notes (one per test writer), PD and ET at the three class
representatives, and the 9 clean notes; built with R's own Writer / make_scen and R's seeds (test.py).
Evidence: SIM (model HW1) with DATA inputs (recordings by others).
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import CACHE_DIR

CASE_DIR = CACHE_DIR / "cases"
N_TUNE_NOTES = 10
N_FOLDS = 5
TUNE_LEVELS = ("severe", "edge", "moderate", "mild")        # 'edge' = 0.6 mm (inside the severe class, near its start)
EDGE_MM = 0.6
REC_1K = 4                                                   # 4 kHz plant record -> 1 kHz (every 4th sample)


def _h(*key) -> int:
    return int(hashlib.sha1(":".join(map(str, key)).encode()).hexdigest()[:8], 16)


def level_amp_mm(level: str) -> float:
    from realdata import library as RL
    cl = RL.classes(False)
    return {"severe": cl["severe"]["representative_mm"], "edge": EDGE_MM,
            "moderate": cl["moderate"]["representative_mm"], "mild": cl["mild"]["representative_mm"]}[level]


# ------------------------------------------------------------------ folds (writers and subjects)
def subject_folds(split: str = "tuning") -> Dict[str, Dict[str, int]]:
    """{kind: {subject: fold}}: the split's generator subjects of each kind, sorted, fold = rank mod 5."""
    from realdata import library as RL
    out = {}
    for kind in ("PD", "ET"):
        subs = sorted({x["subject"] for x in RL.candidates(kind, split)})
        out[kind] = {s: i % N_FOLDS for i, s in enumerate(subs)}
    return out


def fold_rids(kind: str, fold: int, split: str = "tuning") -> List[str]:
    from realdata import library as RL
    sf = subject_folds(split)[kind]
    return sorted(x["rid"] for x in RL.candidates(kind, split) if sf.get(x["subject"]) == fold)


def tuning_specs() -> List[Dict]:
    """The tuning selection set (fixed rule, see the module docstring)."""
    specs = []
    for i in range(N_TUNE_NOTES):
        fold = i % N_FOLDS
        specs.append({"id": f"tune_n{i}_clean", "split": "tuning", "note": i, "fold": fold, "kind": None,
                      "level": "clean", "amp_mm": 0.0})
        for kind in ("PD", "ET"):
            rids = fold_rids(kind, fold)
            start = _h("tune", i, kind) % len(rids)
            for j, lev in enumerate(TUNE_LEVELS):
                specs.append({"id": f"tune_n{i}_{kind}_{lev}", "split": "tuning", "note": i, "fold": fold,
                              "kind": kind, "level": lev, "amp_mm": level_amp_mm(lev),
                              "rid": rids[(start + j + i // N_FOLDS) % len(rids)], "tseed": 1000 * j + i})
    return specs


# ------------------------------------------------------------------ a real note set up for the Rev J pen
class Note:
    """What realdata.hw1.Writer offers for the ordinary pen and Rev J only (same adapted paths and tremor-free run):
    the scenario without tremor, the writer's adapted hand path per pen, and Rev J's tremor-free (nose held) run."""

    def __init__(self, written, pens=("none", "revJ")):
        from realdata import hw1 as H
        from handwriting import params as PR
        from handwriting import plant as PL
        from aiprior import core as CO
        self.written = written
        self.hand = PR.Hand.from_config()
        allp = H.pens()
        self.pens = {k: allp[k] for k in pens}
        self.scn0 = PL.scenario_from_written(written, None)
        self.hp = {k: PL.adapted_path(self.scn0.intended, self.scn0.dt, p, self.hand) for k, p in self.pens.items()}
        self.clean = {k: PL.run(PL.with_hand_path(self.scn0, self.hp[k]), p, self.hand) for k, p in self.pens.items()
                      if k != "none"}
        self.trk = CO.tracker()

    def scenario(self, key: str, tremor):
        from handwriting import plant as PL
        return PL.with_hand_path(self.scn0, self.hp[key], tremor)


def tuning_note(i: int) -> Note:
    from realdata import library as RL
    return Note(RL.writing("tuning", seed=i, source="unipen"))


# ------------------------------------------------------------------ streams <-> arrays
STREAM_KEYS = ("tick_t", "acc_t", "acc_av", "acc", "pos_t", "pos_av", "pos", "pos_ok", "con_t", "con_av", "con")


def streams_to_arrays(st, prefix: str) -> Dict[str, np.ndarray]:
    return {f"{prefix}{k}": np.asarray(getattr(st, k)) for k in STREAM_KEYS}


def arrays_to_streams(d: Dict[str, np.ndarray], prefix: str, meta: Optional[Dict] = None):
    from fusion import sensors as S
    # the DeltaPen-class streams store only their page arrays; the IMU and contact streams are the ideal case's
    kw = {k: np.ascontiguousarray(d[f"{prefix}{k}"] if f"{prefix}{k}" in d else d[f"i_{k}"]) for k in STREAM_KEYS}
    return S.Streams(meta=dict(meta or {}), **kw)


def truth_at_ticks(neutral, clean, tick_t: np.ndarray) -> np.ndarray:
    """d = handle(tremor, nose held) - handle(clean, nose held) at the tick times (the oracle's definition)."""
    n = min(len(neutral.t), len(clean.t))
    t = neutral.t[:n]
    d = neutral.handle[:n] - clean.handle[:n]
    return np.column_stack([np.interp(tick_t, t, d[:, 0]), np.interp(tick_t, t, d[:, 1])])


@dataclass
class Case:
    """Everything a causal estimator and the fast evaluation need for one case (no scenario arrays)."""
    spec: Dict
    meta: Dict
    arrays: Dict[str, np.ndarray] = field(default_factory=dict)

    def streams(self, sensor: str = "deltapen"):
        return arrays_to_streams(self.arrays, "i_" if sensor == "ideal" else "d_", self.meta)

    @property
    def tick_t(self):
        return self.arrays["i_tick_t"]

    @property
    def truth(self):
        return self.arrays["truth"]

    def dh_revh(self, sensor: str = "deltapen"):
        return self.arrays["i_dh" if sensor == "ideal" else "d_dh"]


def build_case(note: Note, spec: Dict, log=print) -> Case:
    """Neutral Rev J run, the ordinary pen's run (reference), the sensor streams and the truth for one spec."""
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import sensors as RS
    from handwriting import plant as PL
    from aiprior import core as CO
    from fusion import estimators as ES
    t0 = time.time()
    written = note.written
    dr = None
    tremor = None
    if spec.get("kind"):
        dr = RL.tremor(spec["level"] if spec["level"] in ("severe", "moderate", "mild") else "severe",
                       seed=int(spec["tseed"]), kind=spec["kind"], split=spec["split"], t=written.intended.t,
                       amp_mm=float(spec["amp_mm"]), rid=spec["rid"])
        tremor = dr.d
    pen = note.pens["revJ"]
    scn = note.scenario("revJ", tremor)
    neutral = note.clean["revJ"] if tremor is None else PL.run(scn, pen, note.hand, ctl=PL.Controls())
    s_seed = _h(spec["id"], "revJ") % (2 ** 31)
    st = CO.streams_for(neutral, scn, pen, note.trk, s_seed)
    pm = H.page_model()
    std = RS.degrade_page(st, pm, s_seed + 17)
    tp = CO.tracker_params(pen, note.trk)
    dh_i, _ = ES.akf(st, tp)
    dh_d, _ = ES.akf(std, tp)
    arr = {}
    arr.update(streams_to_arrays(st, "i_"))
    for k in ("pos_t", "pos_av", "pos", "pos_ok"):
        arr[f"d_{k}"] = np.asarray(getattr(std, k))
    arr["i_dh"] = dh_i
    arr["d_dh"] = dh_d
    arr["truth"] = truth_at_ticks(neutral, note.clean["revJ"], st.tick_t)
    # the fast evaluation's inputs at 1 kHz (every 4th record sample: the samples R's tip-tremor measure uses)
    rec = neutral.rec[::REC_1K]
    t1 = rec[:, 0]
    k = np.clip(np.round(t1 / scn.dt).astype(int), 0, len(scn.t) - 1)
    arr["t1k"] = t1
    arr["handle1k"] = neutral.handle[::REC_1K]
    arr["intended1k"] = np.asarray(scn.intended)[k]
    arr["contact1k"] = neutral.contact[::REC_1K]
    lift = np.asarray(scn.meta.get("lift"))
    tick_decim = neutral.info["tick_decim"]
    kt = np.clip(np.arange(len(st.tick_t)) * tick_decim, 0, len(scn.t) - 1)
    arr["active_ticks"] = (((scn.down > 0.5) | (lift < 2.0e-3))[kt]).astype(np.float64)
    arr["down_ticks"] = (scn.down[kt] > 0.5).astype(np.float64)
    meta = {"spec": spec, "writer": written.real.get("writer"), "text": written.text,
            "duration_s": float(written.intended.t[-1]), "Ts": float(neutral.info["Ts"]),
            "tick_decim": int(tick_decim), "dt": float(scn.dt), "s_seed": int(s_seed),
            "servo_group_delay_s": float(_gd(pen)), "page_model_version": pm.version}
    ref = {}
    if dr is not None:
        meta["tremor"] = {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "source", "looped", "kind")}
        f0 = float(dr.meta["f0"])
        # the ordinary pen with the same hand, writing and tremor (the card's reference)
        scn_n = note.scenario("none", tremor)
        rn = PL.run(scn_n, note.pens["none"], note.hand)
        ref["none_tip_tremor_mm"] = H.tip_tremor_mm(rn, scn_n, f0)
        ref["held_tip_tremor_mm"] = H.tip_tremor_mm(neutral, scn, f0)
        ref["revh_tip_tremor_mm_deltapen"] = H.tip_tremor_mm(
            PL.run(scn, pen, note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(-dh_d))), scn, f0)
        del rn, scn_n
    meta["ref"] = ref
    meta["build_s"] = time.time() - t0
    return Case(spec=spec, meta=meta, arrays=arr)


def _gd(pen) -> float:
    from handwriting import params as PR
    return PR.servo_group_delay(pen)


def case_path(spec: Dict):
    return CASE_DIR / f"{spec['id']}.npz"


def save_case(c: Case) -> None:
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    p = case_path(c.spec)
    np.savez_compressed(p, _meta=np.frombuffer(json.dumps(c.meta, default=float).encode(), dtype=np.uint8),
                        **{k: v for k, v in c.arrays.items()})


def load_case(spec_or_id) -> Case:
    sid = spec_or_id if isinstance(spec_or_id, str) else spec_or_id["id"]
    with np.load(CASE_DIR / f"{sid}.npz") as z:
        meta = json.loads(bytes(z["_meta"]).decode())
        arrays = {k: z[k] for k in z.files if k != "_meta"}
    return Case(spec=meta["spec"], meta=meta, arrays=arrays)


def build_tuning_set(log=print, specs: Optional[List[Dict]] = None) -> List[Dict]:
    """Build (or resume) every tuning case, one note at a time (memory: one note's arrays at a time)."""
    specs = specs or tuning_specs()
    by_note: Dict[int, List[Dict]] = {}
    for s in specs:
        by_note.setdefault(s["note"], []).append(s)
    done = []
    for i, ss in sorted(by_note.items()):
        todo = [s for s in ss if not case_path(s).exists()]
        if todo:
            t0 = time.time()
            note = tuning_note(i)
            for s in todo:
                c = build_case(note, s, log)
                save_case(c)
                r = c.meta.get("ref", {})
                log(f"[cases] {s['id']}: {c.meta['duration_s']:.0f} s note, built in {c.meta['build_s']:.1f} s; "
                    f"ordinary pen {r.get('none_tip_tremor_mm', float('nan')):.3f} mm, "
                    f"Rev H tracker {r.get('revh_tip_tremor_mm_deltapen', float('nan')):.3f} mm")
            log(f"[cases] note {i} ({note.written.real.get('writer')}): {len(todo)} cases in {time.time() - t0:.0f} s")
            del note
        done += ss
    return done
