"""Unit calibrations for recordings whose files carry no physical units (every constant carries its label).

* UCI spiral tablet (Wacom Cintiq 12WX): X and Y are integer screen pixels (DERIVED from the value range, which spans
  the 1280 x 800 display, and from the integer steps) -> millimetres with the display's pixel pitch 0.204 mm (MFR,
  Wacom Cintiq 12WX installation guide, 'Pixel pitch 0.204 x 0.204 mm'; proposed ledger row CON-84).  The pixel grid
  quantises the pen position: a uniform +-0.102 mm error, 0.059 mm RMS per axis (CALC).
* NewHandPD BiSP pen: channels 4-6 ('tilt and acceleration') are uncalibrated.  ``gravity_fit`` finds an offset and a
  gain per axis so that the magnitude of the quasi-static samples equals 1 g (DERIVED calibration: the classic
  multi-orientation accelerometer calibration; it assumes a linear, orthogonal, same-pen sensor, which the files
  support: every file names the pen 'Pentrics Alberich1').
* UCI Character Trajectories: 0.005 mm per tablet unit, the scale used by LIT CON-25 (itself an inference).
* UJI: 100 units per millimetre (file header).  UNIPEN: per data set header.  PADS: g and rad/s (documented).
* Zenodo ET accelerometry: arbitrary units (volts after a x1000 amplifier; sensitivity not published).
"""
from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np

G0 = 9.80665                          # m/s^2, standard gravity
CINTIQ12WX_PITCH_M = 0.204e-3         # m per screen pixel (MFR, Wacom Cintiq 12WX manual; CON-84 proposed)
CINTIQ12WX_REPORT_HZ = 133.0          # maximum report rate (MFR, same manual)
CINTIQ12WX_ACCURACY_M = 0.5e-3        # +-0.5 mm average accuracy (MFR); absolute, not the pixel-to-pixel precision
CHARTRAJ_M_PER_UNIT = 0.005e-3        # LIT CON-25 inference (gives a 13.9 mm median character height)
UJI_M_PER_UNIT = 1e-5                 # file header: 100 units per millimetre

LABELS = {
    "uci_spiral": "DERIVED: screen pixels x 0.204 mm (MFR pixel pitch, Cintiq 12WX manual)",
    "newhandpd": "DERIVED: gravity sphere fit of CH4-6 (offset and gain per axis, |a| = 1 g in quasi-static samples)",
    "chartraj": "LIT CON-25 scale (0.005 mm/unit, itself inferred) then resized to a normal letter height (ASSUMPTION)",
    "uji": "documented: 100 units/mm",
    "pads": "documented: g, rad/s",
    "zenodo_et": "arbitrary units (not calibrated); shape only",
    "brush": "DERIVED per writer: mean height of 'T', 'p', 'a' set to a draw from LIT PDT-06 (ASSUMPTION)",
    "unipen": "documented per data set (.X_POINTS_PER_MM / _INCH, .POINTS_PER_SECOND)",
}


# ------------------------------------------------------------------ gravity sphere fit (NewHandPD CH4-6)
def quasi_static(v: np.ndarray, fs: float, win_s: float = 0.2, rel_tol: float = 0.01, step_s: float = 0.1) -> np.ndarray:
    """Mean of windows in which every axis is nearly constant (std below rel_tol x the recording's axis range, and at
    least below 1.5 quantisation steps of 0.0165): the samples in which the sensor measures gravity only."""
    v = np.asarray(v, float)
    n = int(round(win_s * fs))
    st = int(round(step_s * fs))
    rng = np.ptp(v, axis=0)
    tol = np.maximum(rel_tol * np.maximum(rng, 1e-9), 0.025)
    out = []
    for a in range(0, len(v) - n, st):
        w = v[a:a + n]
        if np.all(w.std(axis=0) < tol):
            out.append(w.mean(axis=0))
    return np.array(out).reshape(-1, v.shape[1])


def gravity_fit(samples: np.ndarray, g: float = G0) -> Dict:
    """Offset o and gain k per axis with |k (v - o)| = g on quasi-static samples (least squares, robust soft-L1).
    Returns the calibration, the residual (m/s^2 RMS) and how much of the sphere the samples cover."""
    from scipy.optimize import least_squares
    V = np.asarray(samples, float)
    lo, hi = np.percentile(V, 1, axis=0), np.percentile(V, 99, axis=0)
    o0 = 0.5 * (lo + hi)
    k0 = g / np.maximum(0.5 * (hi - lo), 1e-6)

    def res(p):
        o, k = p[:3], p[3:]
        return np.linalg.norm((V - o) * k, axis=1) - g
    sol = least_squares(res, np.r_[o0, k0], loss="soft_l1", f_scale=0.3)
    o, k = sol.x[:3], sol.x[3:]
    r = res(sol.x)
    u = (V - o) * k
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-12)
    cover = float(np.linalg.eigvalsh(u.T @ u / len(u)).min())      # 1/3 = uniform over the sphere, 0 = one plane
    return {"offset": o.tolist(), "gain_ms2_per_unit": k.tolist(), "residual_rms_ms2": float(np.sqrt(np.mean(r ** 2))),
            "residual_p95_ms2": float(np.percentile(np.abs(r), 95)), "n_samples": int(len(V)),
            "orientation_cover_min_eig": cover, "label": LABELS["newhandpd"]}


def apply_gravity(v: np.ndarray, cal: Dict) -> np.ndarray:
    return (np.asarray(v, float) - np.asarray(cal["offset"])) * np.asarray(cal["gain_ms2_per_unit"])


# ------------------------------------------------------------------ small helpers
def pixel_quantisation_rms_m(pitch: float = CINTIQ12WX_PITCH_M) -> float:
    """RMS error of rounding to a grid of `pitch` (uniform error): pitch / sqrt(12) (CALC)."""
    return pitch / math.sqrt(12.0)


def unit_scale(source: str) -> float:
    return {"uci_spiral": CINTIQ12WX_PITCH_M, "chartraj": CHARTRAJ_M_PER_UNIT, "uji": UJI_M_PER_UNIT}[source]


def describe() -> Dict[str, str]:
    return dict(LABELS)
