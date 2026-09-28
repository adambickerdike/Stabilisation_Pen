"""Recorded sensor streams for training and validation of the tracker (SIMULATION).

Sets (never the test seeds 200-203 or the aiguide test writers 0-5):
  train      pairs of fusion.learned._spec(i, "train"): P1 runs with and without tremor of the same writing,
             domain-randomised pen, hand, writing and tremor (fusion.data.draw_spec); i % 10 in (2, 5, 8) are
             aiguide glyph writers (seeds 16000 + i), the others sigma-lognormal (seeds 6000 + i).  The sensor
             model is the P1 default page sensor (1 kHz, 2 ms) and the gyroscope-compensated LSM6DSV16X-class IMU,
             with the pen-rotation parameters re-drawn per pair (rho_t in [-0.5, 1.5], rho_w in [0, 1], phase in
             +-90 deg, as fusion.learned).  Stream noise seeds 30_000_000 + 10 i (+1 for the tremor-free run).
  val        fusion.learned._spec(j, "val"), j < 24 (seeds 9000-9011, 9101-9111, glyph 19000 + j), same sensors.
  tune_grid  the harness-convention scenarios of tuning seeds 5000-5007 (4-12 Hz x 0.1/0.3/0.5 mm) and their
             tremor-free writing, nominal sensors (rho 0.5): fusion.tune's proxy data, other noise seeds.
  tune_ai    aiguide tuning writers 100-105 (20 s sentence, 0.3 mm at 4.5-9 Hz) and their tremor-free writing
             (fusion.tune.aiguide_items).
Everything is cached in opt/tracker/build/cache (git-ignored).
"""
from __future__ import annotations

import math
import os
import pickle
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch

from . import CACHE, STREAM_SEED_BASE, TUNE_SEEDS
from . import adjoint as AD
from . import losses as LS
from . import schedule as SCH
from . import torch_akf as TA

from fusion import data as FD  # noqa: E402
from fusion import harness as H  # noqa: E402
from fusion import learned as FL  # noqa: E402
from fusion import sensors as S  # noqa: E402

DT = torch.float64


# ------------------------------------------------------------------ one recording
def _contact_mask(st: S.Streams, rec: S.Record) -> np.ndarray:
    con = np.interp(st.tick_t, rec.t, rec.contact) > 0.5
    return con & (st.tick_t > 0.5)


def _item(st: S.Streams, d: np.ndarray, m: np.ndarray, clean: bool, glyph: bool, meta: Dict) -> Dict:
    return {"st": st, "d": np.asarray(d, float), "m": m.astype(bool), "clean": bool(clean), "glyph": bool(glyph),
            "meta": meta}


def random_sensor_cfg(rng) -> S.SensorConfig:
    return S.config(page="1k", comp="gyro", rho_t=float(rng.uniform(-0.5, 1.5)), rho_w=float(rng.uniform(0.0, 1.0)),
                    psi_t=float(rng.uniform(-math.pi / 2, math.pi / 2)))


def _pair_job(args):
    i, kind = args
    spec = FL._spec(i, kind)
    r1, r0 = FD.pair_records(spec)
    base = STREAM_SEED_BASE + (0 if kind == "train" else 5_000_000) + 10 * i
    rng = np.random.default_rng(base + 2)
    cfg = random_sensor_cfg(rng)
    st1 = S.make_streams(r1, cfg, base)
    st0 = S.make_streams(r0, cfg, base + 1)
    glyph = spec.writer == "glyph"
    meta = {"set": kind, "i": i, "seed": spec.seed, "writer": spec.writer, "f0": spec.f0, "amp_mm": spec.amp * 1e3,
            "rho_t": cfg.rot.rho_t, "rho_w": cfg.rot.rho_w, "psi_t": cfg.rot.psi_t}
    return [_item(st1, S.truth_at(st1.tick_t, r1, r0), _contact_mask(st1, r1), False, glyph, dict(meta, clean=False)),
            _item(st0, np.zeros((len(st0.tick_t), 2)), _contact_mask(st0, r0), True, glyph, dict(meta, clean=True))]


def _grid_job(args):
    s, f0, a = args
    r1, r0 = FD.test_pair_records(s, f0, a)
    cfg = S.config(page="1k", comp="gyro")
    st1 = S.make_streams(r1, cfg, H.sensor_seed(s, f0, a, 17))
    out = [_item(st1, S.truth_at(st1.tick_t, r1, r0), _contact_mask(st1, r1), False, False,
                 {"set": "tune_grid", "seed": s, "f0": f0, "amp_mm": a * 1e3, "clean": False})]
    if f0 == 4.0 and abs(a - 0.1e-3) < 1e-12:
        st0 = S.make_streams(r0, cfg, H.sensor_seed(s, 0.0, 0.0, 18))
        out.append(_item(st0, np.zeros((len(st0.tick_t), 2)), _contact_mask(st0, r0), True, False,
                         {"set": "tune_grid", "seed": s, "f0": 0.0, "amp_mm": 0.0, "clean": True}))
    return out


def _map(fn, jobs, workers):
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return [x for r in ex.map(fn, jobs) for x in r]
    return [x for j in jobs for x in fn(j)]


def _cached(name: str, make):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name + ".pkl")
    if os.path.exists(p):
        with open(p, "rb") as f:
            return pickle.load(f)
    items = make()
    with open(p + ".tmp", "wb") as f:
        pickle.dump(items, f, protocol=5)
    os.replace(p + ".tmp", p)
    return items


def train_indices(n_lognormal: int, n_glyph: int) -> List[int]:
    """The first n_lognormal sigma-lognormal and the first n_glyph glyph-writer pairs of the 400 training specs."""
    lg = [i for i in range(400) if (i % 10) not in FL.GLYPH_EVERY][:n_lognormal]
    gl = [i for i in range(400) if (i % 10) in FL.GLYPH_EVERY][:n_glyph]
    return sorted(lg + gl)


def train_items(n_lognormal: int = 96, n_glyph: int = 64, workers: int = 2) -> List[Dict]:
    idx = train_indices(n_lognormal, n_glyph)
    return _cached(f"train_{n_lognormal}_{n_glyph}", lambda: _map(_pair_job, [(i, "train") for i in idx], workers))


def train_items_range(idx: Sequence[int], tag: str, workers: int = 2) -> List[Dict]:
    return _cached(f"train_{tag}", lambda: _map(_pair_job, [(i, "train") for i in idx], workers))


def val_items(workers: int = 2) -> List[Dict]:
    return _cached("val24", lambda: _map(_pair_job, [(j, "val") for j in range(24)], workers))


def tune_grid_items(seeds: Sequence[int] = TUNE_SEEDS[4:], workers: int = 2) -> List[Dict]:
    jobs = [(s, f0, a) for s in seeds for f0 in H.F0S for a in H.AMPS]
    return _cached("tune_grid_" + "_".join(map(str, seeds)), lambda: _map(_grid_job, jobs, workers))


def tune_ai_items() -> List[Dict]:
    def make():
        from fusion import tune as TU
        out = []
        for it in TU.aiguide_items({"page": "1k", "comp": "gyro"}):
            meta = {"set": "tune_ai", "writer": it["writer"], "f0": it["f0"], "amp_mm": 0.3}
            out.append(_item(it["st"], it["d"], it["m"], False, True, dict(meta, clean=False)))
            out.append(_item(it["st0"], np.zeros((len(it["st0"].tick_t), 2)), it["m0"], True, True, dict(meta, clean=True)))
        return out
    return _cached("tune_ai", make)


# ------------------------------------------------------------------ batched set
@dataclass
class RecSet:
    items: List[Dict]
    scheds: List[SCH.Schedule]
    ev: TA.EventBatch
    pk: AD.Packed
    d: torch.Tensor
    db: torch.Tensor
    m: torch.Tensor
    clean: torch.Tensor
    glyph: torch.Tensor

    @property
    def B(self) -> int:
        return len(self.items)

    def meta(self) -> List[Dict]:
        return [it["meta"] for it in self.items]


def pad_item(it: Dict, K: int) -> Dict:
    """Extend a recording to K ticks: later ticks carry no sensor sample and are masked out of every loss term."""
    import copy
    k0 = len(it["st"].tick_t)
    if k0 == K:
        return it
    st = copy.copy(it["st"])
    Ts = float(st.tick_t[1] - st.tick_t[0])
    st.tick_t = np.arange(K) * Ts
    d = np.zeros((K, 2)); d[:k0] = it["d"]
    m = np.zeros(K, bool); m[:k0] = it["m"]
    return dict(it, st=st, d=d, m=m, meta=dict(it["meta"], padded_from=k0))


def build_set(items: List[Dict], full_events: bool = False, keep_streams: bool = False) -> RecSet:
    K = max(len(it["st"].tick_t) for it in items)
    items = [pad_item(it, K) for it in items]
    scheds = [SCH.build(it["st"]) for it in items]
    ev = TA.EventBatch.from_schedules(scheds) if full_events else light_events(scheds)
    pk = AD.Packed(scheds)
    d = torch.as_tensor(np.stack([it["d"] for it in items]), dtype=DT)
    m = torch.as_tensor(np.stack([it["m"] for it in items]).astype(float), dtype=DT)
    db = LS.zero_phase(d, "band", 1.0 / scheds[0].Ts)
    if not keep_streams:
        items = [{k: v for k, v in it.items() if k not in ("st", "d", "m")} for it in items]
    return RecSet(items=items, scheds=scheds, ev=ev, pk=pk, d=d, db=db, m=m,
                  clean=torch.tensor([it["clean"] for it in items]), glyph=torch.tensor([it["glyph"] for it in items]))


def light_events(scheds: Sequence[SCH.Schedule]) -> TA.EventBatch:
    """An EventBatch with only what the output stage reads (tick times, filter time, started)."""
    K = scheds[0].K
    z = None
    return TA.EventBatch(B=len(scheds), K=K, Ts=scheds[0].Ts, tick_t=torch.as_tensor(scheds[0].tick_t, dtype=DT), D=0, R=0,
                         acc_ev=z, acc_first=z, acc_dt=z, acc_fc=z, acc_qc=z, acc_y=z, pg_ev=z, pg_off=z, pg_dt=z,
                         pg_fc=z, pg_qc=z, pg_gap=z, pg_y=z, re_off=z, re_dt=z, re_fc=z, re_qc=z, re_y=z, fr_adv=z,
                         fr_have=z, fr_upd=z, fr_dtp=z,
                         tf=torch.as_tensor(np.stack([s.tf for s in scheds]), dtype=DT),
                         started=torch.as_tensor(np.stack([s.started for s in scheds]).astype(float), dtype=DT),
                         any_acc=z, all_acc=z, any_pg=z, d_tick=z, r_tick=z)


def evaluate(rs: RecSet, vals: Dict, static: Dict, gate_beta=None, cfg: Optional[LS.LossCfg] = None, grad: bool = False):
    """Objective and per-recording terms of parameter values on a set (numba core, torch output stage)."""
    cfg = cfg or LS.LossCfg()
    ctx = torch.enable_grad() if grad else torch.no_grad()
    with ctx:
        dh = AD.forward(rs.pk, rs.ev, vals, static, gate_beta=gate_beta)
        t = LS.terms(dh, rs.d, rs.db, rs.m, rs.clean, 1.0 / rs.ev.Ts)
        J, info = LS.objective(t, rs.clean, rs.glyph, cfg)
    info.update(LS.summary(t, rs.clean, rs.glyph))
    return J, info, t, dh
