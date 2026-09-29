"""Delay: the Rev J command path's lag, the sensor latencies, and whether prediction removes "Rev H makes it worse".

  servo_lag     CALC on the HW1 plant's own command path (servo.py surrogate; the full plant checked at 6 Hz): a
                sinusoidal nose command at 3-14 Hz, the tip's gain and phase, the equivalent delay -phase / (2 pi f)
  budget        the latency chain (ASSUMPTION values of fusion.sensors and the Rev J pen, results/nose2/nose2.json)
  decompose     SIM on the tuning cases: ordinary pen -> Rev J with the nose held (the heavier pen's own effect) ->
                Rev J + Rev H tracker (the tracker's effect), as tip-tremor ratios per level
  horizon       SIM on the tuning cases: the tip-tremor ratio of a tracker against its prediction horizon (the nominal
                horizon = the servo group delay; offsets -3 ... +10 ms) at the severe, moderate and mild levels
  xcorr_lag     the lag that best aligns an estimate with the truth at the action time (tremor band), per case
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import cases as C
from . import estimators as E
from . import evaluate as EV
from . import servo as SV


def servo_lag(freqs=(3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 14.0), amp: float = 1e-3) -> Dict:
    """Gain, phase and equivalent delay of command -> tip for the Rev J pen (the surrogate's follower, authority on)."""
    pp = SV.pen_params()
    Ts = 0.5e-3
    tdec = 20
    T = 6.0
    n = int(T / Ts)
    t = np.arange(n) * Ts
    rows = []
    for f in freqs:
        q = np.column_stack([amp * np.sin(2 * math.pi * f * t), np.zeros(n)])
        out = np.zeros((n, 2))
        SV._follow(q, np.ones(n), Ts, tdec, pp["q_lim"], pp["q_tap"], pp["slew"], int(round(pp["latency"] / Ts)),
                   2 * math.pi * pp["servo_hz"], pp["zeta"], 1e-6, 0, out)
        m = t > 2.0
        # the follower value at a tick start is the state after the previous tick: evaluate at the tick start
        z = np.exp(-2j * math.pi * f * t[m])
        H = (2 * np.mean(out[m, 0] * z)) / (2 * np.mean(q[m, 0] * z))
        ph = float(np.angle(H))
        rows.append({"f_hz": f, "gain": float(abs(H)), "phase_deg": math.degrees(ph),
                     "delay_ms": -ph / (2 * math.pi * f) * 1e3})
    gd = E.servo_delay()
    return {"rows": rows, "servo_group_delay_ms": gd * 1e3, "pen": pp,
            "label": "CALC: the HW1 plant's command path (tick hold, command latency, 2nd-order follower) for the Rev J "
                     "pen (results/nose2/nose2.json: 80 Hz, zeta 0.7, 0.6 ms)"}


def budget() -> Dict:
    from fusion import sensors as S
    acc = S.AccelModel()
    pg = S.PageSensor()
    gd = E.servo_delay()
    items = [
        {"item": "IMU anti-aliasing filter group delay (400 Hz, 4th order)", "ms": 1.04, "label": "ASSUMPTION (fusion.sensors)"},
        {"item": "IMU FIFO read and SPI", "ms": acc.extra_latency * 1e3, "label": "ASSUMPTION (fusion.sensors)"},
        {"item": "IMU pair averaging (FIFO read of 2 samples at 3.84 kHz)", "ms": 0.5 / acc.odr * 1e3, "label": "CALC"},
        {"item": "control tick hold (2 kHz), mean", "ms": 0.25, "label": "CALC"},
        {"item": "command latency (Rev J)", "ms": 0.6, "label": "CALC (results/nose2/nose2.json)"},
        {"item": "servo follower group delay (80 Hz, zeta 0.7): 2 zeta / omega_n", "ms": (gd - 0.6e-3) * 1e3,
         "label": "CALC"},
        {"item": "page sensor latency (not in the accelerometer path)", "ms": pg.latency * 1e3,
         "label": "ASSUMPTION (fusion default; DeltaPen-class model adds 0-1 ms jitter)"},
    ]
    imu_path = sum(x["ms"] for x in items[:6])
    return {"items": items, "imu_to_tip_ms": imu_path,
            "phase_at_6hz_deg": 360.0 * 6.0 * imu_path * 1e-3,
            "uncorrected_residual_at_6hz": 2.0 * math.sin(math.pi * 6.0 * imu_path * 1e-3),
            "note": "an estimate that were exact but not predicted would leave 2 sin(pi f tau) of the tremor (amplitude)"}


def decompose(log=print) -> Dict:
    """Tip-tremor ratios to the ordinary pen per level: nose held, and the Rev H tracker (DeltaPen-class sensor)."""
    rows = []
    for s in C.tuning_specs():
        if not s.get("kind"):
            continue
        c = C.load_case(s)
        r = c.meta["ref"]
        rows.append({"level": s["level"], "kind": s["kind"], "held": r["held_tip_tremor_mm"] / r["none_tip_tremor_mm"],
                     "revh": r["revh_tip_tremor_mm_deltapen"] / r["none_tip_tremor_mm"],
                     "revh_vs_held": r["revh_tip_tremor_mm_deltapen"] / r["held_tip_tremor_mm"]})
    out = {}
    for lev in ("severe", "edge", "moderate", "mild"):
        sel = [x for x in rows if x["level"] == lev]
        out[lev] = {k: float(np.mean([x[k] for x in sel])) for k in ("held", "revh", "revh_vs_held")}
        out[lev]["revh_worse_share"] = float(np.mean([x["revh"] > 1.05 for x in sel]))
        out[lev]["held_worse_share"] = float(np.mean([x["held"] > 1.05 for x in sel]))
    return {"levels": out, "label": "SIM (tuning cases, DeltaPen-class page sensor; full HW1 plant)"}


def horizon_sweep(design: Dict, offsets_ms=(-3, -1.5, 0, 1.5, 3, 5, 7.5, 10), levels=("severe", "moderate", "mild"),
                  log=print) -> Dict:
    """The design's horizon = servo group delay + offset; surrogate tip-tremor ratios per level (tuning cases)."""
    specs = [s for s in C.tuning_specs() if s["level"] in levels]
    gd = E.servo_delay()
    designs = []
    for o in offsets_ms:
        d = dict(design)
        d["name"] = f"h{o:+g}ms"
        d["horizon"] = gd + o * 1e-3
        designs.append(d)
    rows = EV.eval_batch(designs, specs, "deltapen", log=log)
    sm = EV.summarize(rows)
    out = {"offsets_ms": list(offsets_ms), "nominal_ms": gd * 1e3, "by_offset": {}}
    for o, d in zip(offsets_ms, designs):
        s = sm[d["name"]]
        out["by_offset"][str(o)] = {k: s.get(k) for k in ("severe_ratio", "severe_bb", "moderate_ratio",
                                                           "moderate_rheld", "mild_ratio", "mild_rheld")}
    return out


def xcorr_lag(est: np.ndarray, case, band=(3.0, 12.0), max_lag_ms: float = 40.0) -> Dict:
    """Lag (ms, positive = the estimate is late) and gain that best align the estimate with the truth at the action
    time, in the tremor band, over pen-down ticks."""
    from scipy.signal import butter, sosfiltfilt
    tick_t = case.tick_t
    gd = float(case.meta["servo_group_delay_s"])
    d = case.truth
    tgt = np.column_stack([np.interp(tick_t + gd, tick_t, d[:, 0]), np.interp(tick_t + gd, tick_t, d[:, 1])])
    fs = 1.0 / float(tick_t[1] - tick_t[0])
    sos = butter(2, band, btype="band", fs=fs, output="sos")
    a = sosfiltfilt(sos, tgt, axis=0)
    b = sosfiltfilt(sos, est, axis=0)
    m = case.arrays["down_ticks"] > 0.5
    best = (0.0, -np.inf)
    L = int(max_lag_ms * 1e-3 * fs)
    for k in range(-L, L + 1, 2):
        if k >= 0:
            x, y, mm = a[:len(a) - k], b[k:], m[:len(m) - k]
        else:
            x, y, mm = a[-k:], b[:len(b) + k], m[-k:]
        c = float(np.sum(x[mm] * y[mm]))
        if c > best[1]:
            best = (k / fs * 1e3, c)
    g = float(np.sum(a[m] * b[m]) / max(np.sum(a[m] * a[m]), 1e-30))
    return {"lag_ms": best[0], "gain": g}
