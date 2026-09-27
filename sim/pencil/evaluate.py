"""Metrics of a pencil run against a reference run of the same scenario.

Definitions follow sim/pensim/evaluate.py and docs/physics.md section 8:
the reference ink is the same pen in NEUTRAL mode on the same handwriting without
tremor; the error e(t) = ink(t) - ink_ref(t) on samples where both are in contact,
after the settle time and away from contact transitions (+/-30 ms).  The ink point is
the page projection of the ball centre.  Band-limited quantities use zero-phase
filtering of recorded signals (offline evaluation only).  Evidence status: SIMULATION.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sps

from .layout import IDX


def _mask(res, ref, t_settle=0.5, guard_s=0.03):
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
    m, fs, n = _mask(res, ref, t_settle, guard_s)
    e = res.ink()[:n] - ref.ink()[:n]
    eb = band(e, fs, 3.0, 15.0)
    dH = res.xy("pHx")[:n] - ref.xy("pHx")[:n]
    dHb = band(dH, fs, 3.0, 15.0)
    q = res.xy("q1")[:n]
    qr = res.xy("qr1")[:n]
    down = res["contact"][:n] > 0
    qlim = float(res.P[IDX["q_lim"]])
    lim = (np.linalg.norm(qr, axis=1) > 0.95 * qlim) | (res["vsat"][:n] > 0) | (res["stop"][:n] > 0)
    out = {
        "e_rms_um": rms2(e, m) * 1e6,
        "e_p95_um": float(np.percentile(np.linalg.norm(e[m], axis=1), 95) * 1e6) if m.any() else float("nan"),
        "e_band_rms_um": rms2(eb, m) * 1e6,
        "housing_dev_rms_um": rms2(dH, m) * 1e6,
        "housing_band_rms_um": rms2(dHb, m) * 1e6,
        "q_rms_um": rms2(q, m) * 1e6,
        "q_peak_um": float(np.max(np.linalg.norm(q[m], axis=1)) * 1e6) if m.any() else float("nan"),
        "q_sat_frac": float(np.mean(lim[m])) if m.any() else float("nan"),
        "frac_ref_at_limit": float(np.mean(np.linalg.norm(qr[m], axis=1) > 0.95 * qlim)) if m.any() else float("nan"),
        "frac_vsat": float(np.mean(res["vsat"][:n][down])) if down.any() else 0.0,
        "frac_stop": float(np.mean(res["stop"][:n][down])) if down.any() else 0.0,
        "P_rail_classB_mW": float(np.mean(res["PrailB"][:n]) * 1e3),
        "P_rail_recovery_mW": float(np.mean(res["PrailR"][:n]) * 1e3),
        "N_nib_mean": float(np.mean(res["Nn"][:n][m])) if m.any() else float("nan"),
        "N_nib_std": float(np.std(res["Nn"][:n][m])) if m.any() else float("nan"),
        "N_skid_mean": float(np.mean(res["Ns"][:n][m])) if m.any() else float("nan"),
        "V_rms_ac": float(np.sqrt(np.mean((res.xy("V1")[:n][m] - res.xy("V1")[:n][m].mean(axis=0)) ** 2))) if m.any() else float("nan"),
        "n_eval": int(m.sum()),
        "contact_frac": float(np.mean(down)),
    }
    return out
