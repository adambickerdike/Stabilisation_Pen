r"""ai2's causal TCN tremor estimator (study L's shadow candidate, DEC-043) in sim2, run on the pen's own sensor record
and replayed as the nose command (SIMULATION; the first cross-simulator check of the learned estimator).

How: the device-off run records the firmware's sensor samples (online IMU tip acceleration, page sensor, slide contact,
with their acquisition and availability times) as fusion Streams; ai2's trained TCN (ai2/build/models/tcn.pt, trained on
HW1 streams of Rev H) runs once over them (fusion.learned.features at 500 Hz; each output uses samples available by its
step only: causal); its lag-0 output (the handle's tremor at the step + the Rev H servo delay) is held and linearly
extrapolated (ai2 hold_extrapolate) to the firmware ticks, never using an output from a step later than the tick minus
the servo delay; the nose then cancels it in a second run with the same seed (firmware 'oracle' slot fed with the TCN
table).  Replay is valid here because the nose's action does not change the handle's motion in sim2 (handle-tip
deviation within 1 % between device off, tracker and perfect-knowledge runs, tuning writer 100, 10 Hz x 1 mm), so the
record the TCN sees is the one it would see online.  Domain shift: trained on HW1 (2-D, Rev H IMU at 92 mm), used on
sim2 (3-D, Rev J IMU at 56 mm and 8.4 mm off the axis) with no retraining.
"""
from __future__ import annotations

import math
import os
from typing import Dict, Optional

import numpy as np

from . import ROOT  # noqa: F401

_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        from ai2 import stage_learn as SL
        _MODEL = SL.load_model("tcn")
    return _MODEL


def available() -> bool:
    return os.path.exists(os.path.join(ROOT, "ai2", "build", "models", "tcn.pt"))


def streams_of(r) -> "object":
    """fusion Streams from a sim2j run recorded with FWConfig(record_streams=True)."""
    from fusion.sensors import Streams
    S = r.info["streams"]
    a = np.array(S["acc"], float)
    p = np.array(S["pos"], float)
    c = np.array(S["con"], float)
    n_ticks = int(r.info["n_ticks"])
    tick = np.arange(n_ticks) * 0.5e-3
    return Streams(tick_t=tick, acc_t=a[:, 0], acc_av=a[:, 1], acc=np.ascontiguousarray(a[:, 2:4]),
                   pos_t=p[:, 0], pos_av=p[:, 1], pos=np.ascontiguousarray(p[:, 2:4]), pos_ok=p[:, 4],
                   con_t=c[:, 0], con_av=c[:, 1], con=c[:, 2])


def tcn_table(st, gd: float, n_ticks: int, Ts: float = 0.5e-3) -> np.ndarray:
    """dtab[k] = the TCN's estimate of the handle tremor at tau_k = k Ts, from the latest network step <= tau_k - gd
    (held and linearly extrapolated from the two latest steps, ai2's hold_extrapolate)."""
    from ai2 import data as DA
    from ai2 import learned as LE
    from fusion import learned as FL
    m, info = model()
    X, tk = FL.features(st, DA.NET_HZ)
    Y = LE.predict(m, LE.make_inputs("tcn", X))           # (K, n_lags, 2) m, output k targets t_k + delta_train
    y0 = Y[:, 0, :]
    tau = np.arange(n_ticks) * Ts
    src = tau - gd                                        # the step whose output targets tau (delta_train ~ gd)
    out = LE.hold_extrapolate(tk, y0, src)
    out[src < tk[0]] = 0.0
    return np.ascontiguousarray(out)


def run_case(su, f0: float, amp: float, seed: int, r_none, ref_none_metrics: Optional[Dict] = None) -> Dict:
    """The TCN-replay controller on one ET case: r_none must be the device-off run of the case recorded with
    record_streams (et.run_case(..., record=True))."""
    import time
    from dataclasses import replace
    from . import et as ET
    from . import stepper as ST
    st = streams_of(r_none)
    nz = su.pm.cfg.nose
    gd = 2 * nz.servo_zeta / (2 * math.pi * nz.servo_hz) + 0.25e-3
    dtab = tcn_table(st, gd, int(r_none.info["n_ticks"]) + 10)
    case = su.case
    tr = case.tremor(f0, amp, seed) if amp > 0 else None
    scn = case.scenario(tremor=tr)
    fw = replace(ET.controller("oracle", seed=seed * 7 + su.w))
    t0 = time.time()
    r = ST.run(su.pm, scn, fw, {"oracle_d": dtab}, mu=ET.mu_for(su.w, seed, f0, amp), seed=seed)
    m = su.metrics(r, ref_none=r_none if amp > 0 else None, clean_ref=su.clean_ref(seed) if amp <= 0 else None)
    m.update({"w": su.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "ctl": "tcn", "wall_s": time.time() - t0,
              "writer": su.version, "pen": su.pen, "tcn_rms_um": float(np.sqrt(np.mean(np.sum(dtab ** 2, 1)))) * 1e6})
    return m
