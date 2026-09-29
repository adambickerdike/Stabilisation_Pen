"""The Rev J command path as a fast surrogate (for tuning searches), the servo lag, and the fast results-card measures.

Surrogate (CALC on the HW1 plant's own equations, handwriting/plant.py, read-only): the per-tick command q_c passes the
plant's contact authority g_eff (ramp tau_auth 50 ms toward 'active' = in contact or within 2 mm of the page, sensed
with the 1 ms contact latency), the radial soft limit (tanh taper to q_lim), the slew limit, the command latency
(lat_ticks) and the 2nd-order follower (servo_hz, zeta), integrated with the plant's own semi-implicit Euler at the
plant step.  The tip is taken to follow the follower exactly (the stiff inner loop), and the handle is taken from the
nose-held run (the nose's reaction on the handle is neglected: 2 g of moving tip against the 81 g handle on the grip).
So ink ~= handle(nose held) + follower(command).  Every tuning search uses this surrogate; every finalist is re-run in
the full HW1 plant (the check is reported: surrogate against plant).

The tip-tremor measure is R's (realdata.hw1.tip_tremor_mm), reimplemented on the 1 kHz samples it uses (identical by
construction; tested): power amplitude (sqrt(2) x RMS of the major axis) of ink - intended in contact segments of at
least 0.5 s, band f0 +- 2 Hz (4th-order zero-phase: a measurement, never a controller input).
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
from numba import njit

TAU_AUTH = 0.05
CON_LAT_S = 1e-3


def pen_params(pen=None) -> Dict:
    from realdata import hw1 as H
    pen = pen or H.revj_pen()
    return {"q_lim": pen.q_lim, "q_tap": pen.q_taper, "slew": pen.slew, "latency": pen.latency,
            "servo_hz": pen.servo_hz, "zeta": pen.servo_zeta}


@njit(cache=True)
def _follow(qext, active_ticks, Ts, tdec, qlim, qtap, slew, lat, wf, zf, tau_auth, clat, out_ticks):
    """Follower output r at every tick start (the plant's tick-rate command pipeline, integrated at dt = Ts / tdec)."""
    n = qext.shape[0]
    dt = Ts / tdec
    alpha = 1.0 - math.exp(-Ts / max(tau_auth, 1e-6))
    g = 0.0
    qc0 = 0.0; qc1 = 0.0
    r0 = 0.0; r1 = 0.0; v0 = 0.0; v1 = 0.0
    RB = 256
    rb = np.zeros((RB, 2))
    knee = qlim - qtap
    for k in range(n):
        out_ticks[k, 0] = r0; out_ticks[k, 1] = r1
        act = 0.0
        if k >= clat:
            act = active_ticks[k - clat]
        g = g + alpha * (act - g)
        c0 = qext[k, 0] * g; c1 = qext[k, 1] * g
        rq = math.sqrt(c0 * c0 + c1 * c1)
        if rq > knee and rq > 0.0 and qtap > 0.0:
            rn = knee + qtap * math.tanh((rq - knee) / qtap)
            c0 *= rn / rq; c1 *= rn / rq
        d0 = c0 - qc0; d1 = c1 - qc1
        dm = math.sqrt(d0 * d0 + d1 * d1)
        dmax = slew * Ts
        if dm > dmax and dm > 0.0:
            d0 *= dmax / dm; d1 *= dmax / dm
        qc0 += d0; qc1 += d1
        rb[k % RB, 0] = qc0; rb[k % RB, 1] = qc1
        # the plant reads the command of tick (k - lat) during the steps of tick k (after the tick's own update)
        tk = k - lat
        u0 = 0.0; u1 = 0.0
        if tk >= 0:
            u0 = rb[tk % RB, 0]; u1 = rb[tk % RB, 1]
        for s in range(tdec):
            a0 = wf * wf * (u0 - r0) - 2.0 * zf * wf * v0
            a1 = wf * wf * (u1 - r1) - 2.0 * zf * wf * v1
            v0 += a0 * dt; v1 += a1 * dt
            r0 += v0 * dt; r1 += v1 * dt


def tip_offset(qext: np.ndarray, case, pp: Optional[Dict] = None) -> np.ndarray:
    """Surrogate tip deflection (m) at the case's 1 kHz sample times for a per-tick command qext (n_ticks, 2)."""
    pp = pp or pen_params()
    Ts = float(case.meta["Ts"])
    tdec = int(case.meta["tick_decim"])
    act = case.arrays["active_ticks"]
    n = min(len(qext), len(act))
    out = np.zeros((n, 2))
    lat = int(round(pp["latency"] / Ts))
    _follow(np.ascontiguousarray(qext[:n], dtype=np.float64), np.ascontiguousarray(act[:n], dtype=np.float64), Ts,
            tdec, pp["q_lim"], pp["q_tap"], pp["slew"], lat, 2.0 * math.pi * pp["servo_hz"], pp["zeta"], TAU_AUTH,
            int(round(CON_LAT_S / Ts)), out)
    t1 = case.arrays["t1k"]
    kt = np.clip(np.floor(t1 / Ts + 1e-9).astype(int), 0, n - 1)
    # the record at a step inside tick k shows the follower advanced by the steps since the tick start: use the
    # follower value at the tick start (sub-tick detail is below the measure's resolution: 1 kHz samples = tick starts)
    return out[kt]


# ------------------------------------------------------------------ measures (R's definitions)
def tip_tremor_mm(t1k, ink1k, intended1k, contact1k, f0: float, min_seg_s: float = 0.5) -> float:
    """realdata.hw1.tip_tremor_mm on the 1 kHz samples (identical arithmetic)."""
    from scipy.signal import butter, sosfiltfilt
    if not f0 or f0 <= 0:
        return float("nan")
    e = ink1k - intended1k
    con = contact1k > 0.5
    fs = 1.0 / float(t1k[1] - t1k[0])
    sos = butter(4, (max(1.0, f0 - 2.0), f0 + 2.0), btype="band", fs=fs, output="sos")
    idx = np.flatnonzero(con)
    if len(idx) < int(min_seg_s * fs):
        return float("nan")
    parts = []
    for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        if len(r) < int(min_seg_s * fs):
            continue
        eb = sosfiltfilt(sos, e[r], axis=0)
        trim = int(0.1 * fs)
        if len(eb) > 2 * trim + 10:
            parts.append(eb[trim:len(eb) - trim])
    if not parts:
        return float("nan")
    X = np.vstack(parts)
    X = X - X.mean(0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    major = X @ vt[0]
    return float(np.sqrt(2.0) * np.sqrt(np.mean(major ** 2)) * 1e3)


BB_BAND = (0.5, 20.0)


def broadband_um(t1k, ink1k, intended1k, contact1k, band=BB_BAND) -> float:
    """RMS of ink - intended in contact (after 0.5 s), band 0.5-20 Hz (zero-phase measurement filter, whole record as
    handwriting.metrics.band_error_um does): the tremor left in every band plus anything the correction adds."""
    from scipy.signal import butter, sosfiltfilt
    fs = 1.0 / float(t1k[1] - t1k[0])
    e = sosfiltfilt(butter(4, band, btype="band", fs=fs, output="sos"), ink1k - intended1k, axis=0)
    m = (contact1k > 0.5) & (t1k > 0.5)
    return float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6) if m.any() else float("nan")


_HELD: Dict[str, float] = {}


def fast_measures(case, qext: np.ndarray, pp: Optional[Dict] = None) -> Dict:
    """Surrogate results-card measures for a per-tick command: tip tremor (mm, and ratio to the ordinary pen) and the
    broadband residual (um, and ratio to the nose-held pen's) for tremor cases; clean-writing change (RMS tip
    deflection over contact, um) for clean cases."""
    A = case.arrays
    off = tip_offset(qext, case, pp)
    ink = A["handle1k"] + off
    con = A["contact1k"] > 0.5
    out = {}
    tr = case.meta.get("tremor")
    if tr:
        f0 = float(tr["f0"])
        tt = tip_tremor_mm(A["t1k"], ink, A["intended1k"], A["contact1k"], f0)
        out["tip_tremor_mm"] = tt
        ref = case.meta["ref"]["none_tip_tremor_mm"]
        out["ratio"] = tt / ref if ref and ref > 0 else float("nan")
        out["none_tip_tremor_mm"] = ref
        key = case.spec["id"]
        if key not in _HELD:
            _HELD[key] = broadband_um(A["t1k"], A["handle1k"], A["intended1k"], A["contact1k"])
        bb = broadband_um(A["t1k"], ink, A["intended1k"], A["contact1k"])
        out["bb_um"] = bb
        out["bb_ratio_held"] = bb / _HELD[key]
        held_tt = case.meta["ref"].get("held_tip_tremor_mm")
        out["ratio_held"] = tt / held_tt if held_tt else float("nan")
    else:
        out["clean_change_um"] = float(np.sqrt(np.mean(np.sum(off[con] ** 2, axis=1))) * 1e6) if con.any() else float("nan")
        out["clean_change_p99_um"] = float(np.percentile(np.hypot(*off[con].T), 99) * 1e6) if con.any() else float("nan")
    return out
