"""A page-sensor error model of DeltaPen class for the HW1 runs, applied on top of the fusion page stream.

Why: the fusion page sensor (fusion/sensors.py, used by every tracker of the programme) is an optical relative-position
sensor at 1 kHz with 2 ms latency and 3 um white noise: an ASSUMPTION ('ideal').  The independent review of 2026-09-29
(s7, s11, R14) and the lead's response (row 8) ask for results with a measured-error model, the ideal sensor only as a
labelled bound.

What is measured (LIT OPT-02, DeltaPen, 10 participants writing and drawing on a Wacom Intuos 4 tablet, not paper):
the translation error per 10 ms window has a median of 23.6 um and a mean absolute value of 68.3 um; the relative
error falls with speed; idle drift is 0.044 mm/s per axis; about 0.05 % of raw flow samples are outliers (OPT-01).
Not measured: latency, paper, pen tilt.  That per-window metric is neither per-sample Gaussian noise nor absolute path
accuracy, and part of it is the Wacom reference's own error.

The model ('deltapen'; every item labelled):
  window error  each 10 ms window of page motion gets an error vector of random direction and size
                c (d / 100 um)^gamma exp(sigma z), z ~ N(0, 1), d = the window's true translation: larger for faster
                windows but relatively smaller (gamma = 0.5: ASSUMPTION for 'relative error falls with speed').
                c and sigma are FITTED (CALC) so that the window errors on the TUNING writers' clean notes have
                OPT-02's median and mean.  The error is spread evenly over the window and ACCUMULATES, as it does in a
                relative (optical-flow) sensor.  All of DeltaPen's measured error is attributed to the sensor although
                part of it belongs to the reference: a PESSIMISTIC model.
  idle drift    constant velocity per axis, 43.75 um/s, random sign (OPT-02)
  scale error   per session and axis, N(0, 3 %) (ASSUMPTION: DeltaPen reports tilt and height sensitivity, not a value)
  quantisation  4.23 um counts (6000 dpi nominal; OPT-01, derived)
  outliers      0.05 % of samples rejected, i.e. marked invalid (OPT-01)
  dropouts      loss-of-tracking episodes, Poisson 0.2 per second of valid sensing, 20-150 ms each (ASSUMPTION)
  latency       2 ms + uniform jitter 0-1 ms (ASSUMPTION: DeltaPen did not measure latency); availability kept
                monotone; acquisition and availability times stay separate, as in fusion/sensors.py
  saturation    measured speed limited to 1 m/s (ASSUMPTION; handwriting never reaches it).  Actuator saturation
                (travel, force, slew) is already in the HW1 pens.
The IMU model of fusion/sensors.py already has bias, Gauss-Markov drift, scale error, misalignment, quantisation and
range; it is unchanged.  The trackers are used as built (tuned for the ideal sensor): no re-tuning here.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import CACHE_DIR, ensure_paths

ensure_paths()

OPT02_MEDIAN_M = 23.6e-6          # LIT OPT-02
OPT02_MAE_M = 68.3e-6             # LIT OPT-02
OPT02_IDLE_DRIFT_M_S = 43.75e-6   # LIT OPT-02 (per axis)
OPT01_COUNT_M = 25.4e-3 / 6000.0  # LIT OPT-01 (6000 dpi nominal; derived)
OPT01_OUTLIER_P = 5e-4            # LIT OPT-01
PAGE_MODEL_JSON = CACHE_DIR / "page_model.json"


@dataclass
class PageModel:
    name: str = "deltapen"
    window_s: float = 0.010
    d_ref: float = 100e-6
    gamma: float = 0.5
    c: float = 20e-6                # fitted (fit_window_error)
    sigma: float = 1.0              # fitted
    drift_m_s: float = OPT02_IDLE_DRIFT_M_S
    scale_sd: float = 0.03
    quant_m: float = OPT01_COUNT_M
    outlier_p: float = OPT01_OUTLIER_P
    drop_rate_hz: float = 0.2
    drop_ms: tuple = (20.0, 150.0)
    latency_s: float = 2e-3
    jitter_s: float = 1e-3
    vmax_m_s: float = 1.0
    fitted: Dict = field(default_factory=dict)
    labels: Dict = field(default_factory=lambda: {
        "window error": "LIT OPT-02 median and mean; shape (gamma, log-normal, random direction) ASSUMPTION; c, sigma CALC",
        "idle drift": "LIT OPT-02", "scale error": "ASSUMPTION", "quantisation": "LIT OPT-01 (derived)",
        "outliers": "LIT OPT-01", "dropouts": "ASSUMPTION", "latency": "ASSUMPTION (fusion default 2 ms + jitter)",
        "saturation": "ASSUMPTION"})


def _window_translations(t: np.ndarray, xy: np.ndarray, valid: np.ndarray, window_s: float) -> np.ndarray:
    """True translation of every complete valid window (m)."""
    fs = 1.0 / float(np.median(np.diff(t)))
    W = max(1, int(round(window_s * fs)))
    n = (len(t) // W) * W
    X = xy[:n].reshape(-1, W, 2)
    V = valid[:n].reshape(-1, W).all(axis=1)
    d = np.hypot(*(X[:, -1] - X[:, 0]).T)
    return d[V]


def fit_window_error(notes: Sequence, model: Optional[PageModel] = None, n_mc: int = 200_000, seed: int = 7) -> PageModel:
    """Fit c and sigma so that the window error on these clean notes has OPT-02's median and mean (CALC).
    notes: aiguide Written objects (tuning writers); their pen-down samples stand in for DeltaPen's writing tasks."""
    model = copy.deepcopy(model or PageModel())
    d = []
    for w in notes:
        it = w.intended
        step = max(1, int(round(1e-3 / float(it.t[1] - it.t[0]))))
        t, xy, dn = it.t[::step], it.xy[::step], it.pen_down[::step]
        d.append(_window_translations(t, xy, dn, model.window_s))
    d = np.concatenate(d)
    u = (d / model.d_ref) ** model.gamma
    rng = np.random.default_rng(seed)
    us = rng.choice(u, n_mc)
    z = rng.standard_normal(n_mc)
    target = OPT02_MAE_M / OPT02_MEDIAN_M

    def ratio(sig):
        r = us * np.exp(sig * z)
        return float(np.mean(r) / np.median(r))

    lo, hi = 0.0, 4.0
    if ratio(lo) >= target:
        sig = 0.0
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if ratio(mid) < target:
                lo = mid
            else:
                hi = mid
        sig = 0.5 * (lo + hi)
    r = us * np.exp(sig * z)
    c = OPT02_MEDIAN_M / float(np.median(r))
    model.c, model.sigma = float(c), float(sig)
    rr = c * r
    model.fitted = {"n_windows": int(len(d)), "n_notes": len(notes), "median_um": float(np.median(rr) * 1e6),
                    "mean_um": float(np.mean(rr) * 1e6), "p99_um": float(np.percentile(rr, 99) * 1e6),
                    "window_translation_median_um": float(np.median(d) * 1e6),
                    "window_translation_mean_um": float(np.mean(d) * 1e6),
                    "target": {"median_um": OPT02_MEDIAN_M * 1e6, "mean_um": OPT02_MAE_M * 1e6, "ledger": "OPT-02"},
                    "label": "CALC: fitted on the TUNING writers' clean notes (pen-down samples)"}
    return model


def save_model(model: PageModel) -> None:
    PAGE_MODEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    PAGE_MODEL_JSON.write_text(json.dumps(asdict(model)))


def load_model() -> Optional[PageModel]:
    if not PAGE_MODEL_JSON.exists():
        return None
    d = json.loads(PAGE_MODEL_JSON.read_text())
    d["drop_ms"] = tuple(d["drop_ms"])
    return PageModel(**d)


def degrade_page(st, model: PageModel, seed: int):
    """A copy of fusion Streams `st` whose page stream carries the model's errors (the IMU and contact streams are
    unchanged).  st.pos is taken as the true page position (its 3 um noise is negligible here)."""
    from fusion import sensors as FS
    rng = np.random.default_rng(seed)
    t = np.asarray(st.pos_t, float)
    P = np.asarray(st.pos, float)
    ok = np.asarray(st.pos_ok, float).copy()
    n = len(t)
    if n < 4:
        return st
    fs = 1.0 / float(np.median(np.diff(t)))
    dP = np.diff(P, axis=0, prepend=P[:1])
    # scale error (per session and axis) and saturation of the measured speed
    s = rng.normal(0.0, model.scale_sd, 2)
    dM = dP * (1.0 + s)
    sp = np.hypot(*dM.T) * fs
    lim = sp > model.vmax_m_s
    if lim.any():
        dM[lim] *= (model.vmax_m_s / sp[lim])[:, None]
    # window errors, spread evenly over each window's samples, only while the sensor is valid
    W = max(1, int(round(model.window_s * fs)))
    nw = int(math.ceil(n / W))
    i0 = np.arange(nw) * W
    i1 = np.minimum(i0 + W, n - 1)
    d = np.hypot(*(P[i1] - P[i0]).T)
    r = model.c * (d / model.d_ref) ** model.gamma * np.exp(model.sigma * rng.standard_normal(nw))
    a = rng.uniform(0.0, 2.0 * math.pi, nw)
    ew = np.column_stack([r * np.cos(a), r * np.sin(a)]) / W
    e = np.repeat(ew, W, axis=0)[:n]
    e[ok < 0.5] = 0.0
    # idle drift (constant velocity, random sign per axis)
    e += (model.drift_m_s * rng.choice([-1.0, 1.0], 2)) / fs
    M = P[0] + np.cumsum(dM + e, axis=0) - (dM + e)[0]
    M = np.round(M / model.quant_m) * model.quant_m
    # outliers and dropout episodes (samples marked invalid)
    ok[rng.random(n) < model.outlier_p] = 0.0
    valid_s = float(np.sum(ok > 0.5)) / fs
    n_drop = rng.poisson(model.drop_rate_hz * valid_s)
    vidx = np.flatnonzero(ok > 0.5)
    drops = []
    for _ in range(int(n_drop)):
        if not len(vidx):
            break
        k0 = int(vidx[rng.integers(0, len(vidx))])
        dur = rng.uniform(*model.drop_ms) * 1e-3
        k1 = min(n, k0 + int(round(dur * fs)))
        ok[k0:k1] = 0.0
        drops.append([float(t[k0]), float(dur)])
    # latency with jitter; availability monotone; acquisition time unchanged
    av = np.maximum.accumulate(t + model.latency_s + rng.uniform(0.0, model.jitter_s, n))
    meta = dict(st.meta)
    meta.update({"page_model": model.name, "page_seed": int(seed), "page_scale_err": [float(v) for v in s],
                 "page_dropouts": len(drops), "page_latency": model.latency_s, "page_jitter": model.jitter_s})
    out = FS.Streams(tick_t=st.tick_t, acc_t=st.acc_t, acc_av=st.acc_av, acc=st.acc, pos_t=t, pos_av=av,
                     pos=np.ascontiguousarray(M), pos_ok=ok, con_t=st.con_t, con_av=st.con_av, con=st.con, meta=meta)
    return out


def window_error_check(st_true, st_meas, window_s: float = 0.010) -> Dict:
    """Per-window translation error of a degraded stream against the true one (valid windows): median and mean (um),
    to compare with OPT-02 (a check of the construction on the simulated run)."""
    t = st_true.pos_t
    fs = 1.0 / float(np.median(np.diff(t)))
    W = max(1, int(round(window_s * fs)))
    n = (len(t) // W) * W
    ok = (st_meas.pos_ok[:n] > 0.5).reshape(-1, W).all(axis=1)
    A = st_true.pos[:n].reshape(-1, W, 2)
    B = st_meas.pos[:n].reshape(-1, W, 2)
    err = np.hypot(*((B[:, -1] - B[:, 0]) - (A[:, -1] - A[:, 0])).T)[ok]
    moving = np.hypot(*(A[:, -1] - A[:, 0]).T)[ok] > 20e-6
    err = err[moving]
    return {"median_um": float(np.median(err) * 1e6) if len(err) else float("nan"),
            "mean_um": float(np.mean(err) * 1e6) if len(err) else float("nan"), "n": int(len(err))}
