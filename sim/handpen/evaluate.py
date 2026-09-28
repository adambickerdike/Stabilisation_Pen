"""Ink-error metrics of an H1 run against a reference run of the same scenario.

Definitions follow sim/pencil/evaluate.py (and docs/physics.md section 8): the error is the time-aligned
ink difference on samples where both runs are in contact, after 0.5 s and away from contact transitions
(+/-30 ms); band-limited values use zero-phase 4th-order Butterworth filtering (offline only).
Additional quantities for the stabiliser study: tilt, grip-point motion, device stroke/force/torque,
drag felt at the grip.  Evidence status: SIMULATION.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sps


def mask(res, ref, t_settle=0.5, guard_s=0.03):
    t = res["t"]
    n = min(len(t), len(ref["t"]))
    fs = 1.0 / (t[1] - t[0])
    c = (res["contact"][:n] > 0) & (ref["contact"][:n] > 0) & (t[:n] > t_settle)
    g = int(round(guard_s * fs))
    if g > 0:
        edges = np.flatnonzero(np.diff(c.astype(int)) != 0)
        for e in edges:
            c[max(0, e - g):e + g + 1] = False
    return c, fs, n


def band(x, fs, lo=None, hi=None):
    if lo and hi:
        sos = sps.butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    elif lo:
        sos = sps.butter(4, lo, btype="high", fs=fs, output="sos")
    else:
        sos = sps.butter(4, hi, btype="low", fs=fs, output="sos")
    return sps.sosfiltfilt(sos, x, axis=0)


def rms2(e, m):
    if m.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))))


def compare(res, ref, t_settle=0.5, guard_s=0.03):
    m, fs, n = mask(res, ref, t_settle, guard_s)
    e = res.ink()[:n] - ref.ink()[:n]
    eb = band(e, fs, 3.0, 15.0)
    dH = res.ball()[:n] - ref.ball()[:n]
    dHb = band(dH, fs, 3.0, 15.0)
    down = res["contact"][:n] > 0
    q = res.xy("q1")[:n]
    sat = res["sat"][:n] > 0
    Fd = np.column_stack([res["Fd1"][:n], res["Fd2"][:n], res["Fd3"][:n]])
    r = np.column_stack([res["r1"][:n], res["r2"][:n], res["r3"][:n]])
    tq = np.column_stack([res["tq1"][:n], res["tq2"][:n]])
    dl = np.column_stack([res["dl1"][:n], res["dl2"][:n]])
    dr = np.column_stack([res["dr1"][:n], res["dr2"][:n]])
    tilt = np.column_stack([res["b1"][:n], res["b2"][:n]])
    tiltb = band(tilt, fs, 3.0, 15.0)
    fric = np.column_stack([res["fsx"][:n] + res["fnx"][:n] + res["Fvx"][:n], res["fsy"][:n] + res["fny"][:n] + res["Fvy"][:n]])
    out = {
        "e_rms_um": rms2(e, m) * 1e6,
        "e_band_rms_um": rms2(eb, m) * 1e6,
        "e_p95_um": float(np.percentile(np.linalg.norm(e[m], axis=1), 95) * 1e6) if m.any() else float("nan"),
        "ball_dev_rms_um": rms2(dH, m) * 1e6,
        "ball_band_rms_um": rms2(dHb, m) * 1e6,
        "tilt_band_rms_mrad": rms2(tiltb, m) * 1e3,
        "q_rms_um": rms2(q, m) * 1e6,
        "q_sat_frac": float(np.mean(sat[m])) if m.any() else float("nan"),
        "dev_force_rms_N": [float(np.sqrt(np.mean(Fd[m, i] ** 2))) if m.any() else float("nan") for i in range(3)],
        "dev_force_peak_N": [float(np.max(np.abs(Fd[m, i]))) if m.any() else float("nan") for i in range(3)],
        "dev_stroke_peak_mm": [float(np.max(np.abs(r[m, i]))) * 1e3 if m.any() else float("nan") for i in range(3)],
        "dev_stroke_rms_mm": [float(np.sqrt(np.mean(r[m, i] ** 2))) * 1e3 if m.any() else float("nan") for i in range(3)],
        "cmg_torque_rms_mNm": [float(np.sqrt(np.mean(tq[m, i] ** 2))) * 1e3 if m.any() else float("nan") for i in range(2)],
        "cmg_gimbal_peak_rad": [float(np.max(np.abs(dl[m, i]))) if m.any() else float("nan") for i in range(2)],
        "cmg_rate_rms_rad_s": [float(np.sqrt(np.mean(dr[m, i] ** 2))) if m.any() else float("nan") for i in range(2)],
        "drag_mean_N": float(np.mean(np.linalg.norm(fric[m], axis=1))) if m.any() else float("nan"),
        "N_skid_mean": float(np.mean(res["Ns"][:n][m])) if m.any() else float("nan"),
        "n_eval": int(m.sum()),
        "contact_frac": float(np.mean(down)),
    }
    return out


def vs_intended(res, scn, t_settle=0.5, guard_s=0.03):
    """Ink against the writer's intended path (scenario.intended): RMS with the mean offset removed, the 3-15 Hz band
    RMS (tremor that gets through plus writing detail that is filtered away; slow lag, which a writer can compensate,
    is excluded), and the 0.5-8 Hz amplitude ratio (letter size)."""
    t = res["t"]
    fs = 1.0 / (t[1] - t[0])
    it = np.column_stack([np.interp(t, scn.t, scn.intended[:, 0]), np.interp(t, scn.t, scn.intended[:, 1])])
    c = (res["contact"] > 0) & (t > t_settle)
    g = int(round(guard_s * fs))
    edges = np.flatnonzero(np.diff(c.astype(int)) != 0)
    for e_ in edges:
        c[max(0, e_ - g):e_ + g + 1] = False
    if not c.any():
        return {"e_int_um": float("nan"), "e_int_band_um": float("nan"), "amp_ratio_int": float("nan")}
    e = res.ink() - it
    off = e[c].mean(axis=0)
    eb = band(e, fs, 3.0, 15.0)
    a = band(res.ink(), fs, 0.5, 8.0)[c]
    b = band(it, fs, 0.5, 8.0)[c]
    return {"e_int_um": float(np.sqrt(np.mean(np.sum((e[c] - off) ** 2, axis=1)))) * 1e6,
            "e_int_band_um": rms2(eb, c) * 1e6,
            "amp_ratio_int": float(np.sqrt(np.sum(a ** 2) / max(np.sum(b ** 2), 1e-30)))}


def distortion(res, ref, t_settle=0.5, guard_s=0.03):
    """Writing distortion of a configuration against another on tremor-free writing: RMS difference after removing
    the mean offset, lag (s) from cross-correlation of the ink velocity, and the amplitude ratio of the ink motion."""
    m, fs, n = mask(res, ref, t_settle, guard_s)
    a = res.ink()[:n]
    b = ref.ink()[:n]
    e = a - b
    if not m.any():
        return {"detrended_rms_um": float("nan"), "lag_ms": float("nan"), "amplitude_ratio": float("nan")}
    off = e[m].mean(axis=0)
    ed = e[m] - off
    # lag: cross-correlate velocities (x and y summed) within +/- 50 ms
    va = np.gradient(a, axis=0) * fs
    vb = np.gradient(b, axis=0) * fs
    va[~m] = 0.0
    vb[~m] = 0.0
    L = int(0.05 * fs)
    best, bl = -np.inf, 0
    for lag in range(-L, L + 1):
        if lag >= 0:
            c = np.sum(va[lag:] * vb[:n - lag])
        else:
            c = np.sum(va[:lag] * vb[-lag:])
        if c > best:
            best, bl = c, lag
    # amplitude ratio of the in-band (0.5-8 Hz) writing motion
    ab = band(a, fs, 0.5, 8.0)[m]
    bb = band(b, fs, 0.5, 8.0)[m]
    amp = float(np.sqrt(np.sum(ab ** 2) / max(np.sum(bb ** 2), 1e-30)))
    return {"mean_offset_um": (off * 1e6).tolist(), "detrended_rms_um": float(np.sqrt(np.mean(np.sum(ed ** 2, axis=1)))) * 1e6,
            "lag_ms": bl / fs * 1e3, "amplitude_ratio": amp}
