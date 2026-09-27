"""Metrics comparing a run with a reference run of the same scenario.

Reference ink = the same intended hand path, no disturbance, ordinary rigid pen
(mode 'rigid').  Error e(t) = ink(t) - ink_ref(t) on samples where BOTH are in
contact and away from contact transitions.  Band-limited errors use zero-phase
filtering of the recorded error (offline evaluation only; never a controller
feature).  All values are SIMULATION outputs.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sps


def _mask(res, ref, t_settle, guard_s):
    t = res["t"]
    fs = 1.0 / (t[1] - t[0])
    c = (res["contact"] > 0) & (ref["contact"] > 0) & (t > t_settle)
    g = int(round(guard_s * fs))
    if g > 0:
        edges = np.flatnonzero(np.diff(c.astype(int)) != 0)
        for e in edges:
            c[max(0, e - g):e + g + 1] = False
    return c, fs


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


def compare(res, ref, t_settle=0.5, guard_s=0.03, band_lo=3.0, band_hi=15.0, low_hi=2.5):
    m, fs = _mask(res, ref, t_settle, guard_s)
    n = min(len(res["t"]), len(ref["t"]))
    tip = res.xy("tipx")[:n]
    tipr = ref.xy("tipx")[:n]
    e = tip - tipr
    m = m[:n]
    e_band = band(e, fs, band_lo, band_hi)
    e_low = band(e, fs, None, low_hi)
    q = res.xy("q1")[:n]
    qr = res.xy("qr1")[:n]
    i = res.xy("i1")[:n]
    N = res["N"][:n]
    Nb = band(N, fs, band_lo, band_hi)
    Fh = res.rec[:n, [res_idx(res, "Fhx"), res_idx(res, "Fhy")]]
    Fhb = band(Fh, fs, band_lo, band_hi)
    qlim = res.ctrl.q_lim
    down = res["contact"][:n] > 0
    out = {
        "e_rms_um": rms2(e, m) * 1e6,
        "e_p95_um": float(np.percentile(np.linalg.norm(e[m], axis=1), 95) * 1e6) if m.any() else float("nan"),
        "e_band_rms_um": rms2(e_band, m) * 1e6,
        "e_low_rms_um": rms2(e_low, m) * 1e6,
        "q_rms_um": rms2(q, m) * 1e6,
        "q_peak_um": float(np.max(np.linalg.norm(q[m], axis=1)) * 1e6) if m.any() else float("nan"),
        "frac_near_limit": float(np.mean(np.linalg.norm(qr[m], axis=1) > 0.95 * qlim)) if m.any() else float("nan"),
        "frac_stop": float(np.mean(res["stop"][:n][down])) if down.any() else 0.0,
        "frac_vsat": float(np.mean(res["sat_v"][:n][down])) if down.any() else 0.0,
        "i_rms_A": float(np.sqrt(np.mean(np.sum(i[down] ** 2, axis=1)))) if down.any() else 0.0,
        "i_peak_A": float(np.max(np.abs(i))) if len(i) else 0.0,
        "P_cu_mean_W": float(np.mean(res["Pcu"][:n])),
        "P_bridge_mean_W": float(np.mean(res["Pbr"][:n])),
        "T_coil_max_C": float(np.max(res.rec[:n, [res_idx(res, "T1"), res_idx(res, "T2")]])),
        "N_mean": float(np.mean(N[m])) if m.any() else float("nan"),
        "N_mod_rms": float(np.sqrt(np.mean(Nb[m] ** 2))) if m.any() else float("nan"),
        "ink_gap_frac": float(np.mean((ref["contact"][:n] > 0) & (res["contact"][:n] <= 0))),
        "F_hand_band_rms": rms2(Fhb, m),
        "n_eval": int(m.sum()),
        "contact_transitions_per_s": float(np.sum(np.diff((res["contact"][:n] > 0).astype(int)) != 0) / max(res["t"][n - 1] - res["t"][0], 1e-9)),
    }
    return out


def res_idx(res, name):
    from .layout import RIDX
    return RIDX[name]


def feature_errors(res, ref, features, fs=None):
    """Max and RMS ink error inside each named feature window (e.g. corner_edge,
    dot, hatch, fast_stroke, circle, spiral)."""
    t = res["t"]
    n = min(len(t), len(ref["t"]))
    e = res.xy("tipx")[:n] - ref.xy("tipx")[:n]
    both = (res["contact"][:n] > 0) & (ref["contact"][:n] > 0)
    out = {}
    for name, t0, t1, meta in features:
        m = (t[:n] >= t0) & (t[:n] <= t1) & both
        if not m.any():
            continue
        en = np.linalg.norm(e[m], axis=1)
        d = out.setdefault(name, {"max_um": 0.0, "sum2": 0.0, "n": 0})
        d["max_um"] = max(d["max_um"], float(en.max() * 1e6))
        d["sum2"] += float(np.sum(en ** 2))
        d["n"] += int(m.sum())
    for k, d in out.items():
        d["rms_um"] = float(np.sqrt(d["sum2"] / max(d["n"], 1)) * 1e6)
        del d["sum2"]
    return out
