"""The platen's tip predictor: a multi-horizon causal linear (AR) predictor on camera-class frames (tuning split).

The platen observes the pen tip in the desk frame with a camera-class sensor: frames at f_cam (a divisor of the
2 kHz controller tick), available cam_latency after acquisition, with white noise of RMS sigma per axis.  At each
controller tick the newest available frame is ph ticks old (cam_lat <= ph < cam_lat + cam_every); the stage acts
after its group delay g.  So for each ph a separate set of coefficients predicts e(t_frame + ph Ts + g) from the
latest `order` frames (one set shared by both page axes; ridge least squares).  e is the tip's deviation from a known
target: the clean tip path in free writing (perfect separation: the sensing limit), or the tip's starting point in
accepted writing (the user holds the pen still: every motion is unwanted, no separation is needed).

Fitted on study E's TUNING cases only (study R's tuning split: 10 notes, 5 writers, PD and ET at the severe and
moderate classes): the true tip deviation of the ordinary pen on a still page (model HW1, real inputs), plus a slow
drift (the accepted-writing hand model's drift, independent seeds) so that the predictor keeps a unit gain at low
frequency.  Order and ridge chosen by the cross-fitted RMS prediction error over E's folds (fold = note % 5: the model
scoring fold k never saw fold k's writer or patients).  CALCULATION on SIMULATION signals.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import common as CM

ORDER_GRID = (4, 8, 16, 24)
RIDGE_GRID = (1e-6, 1e-4, 1e-2)
DRIFT_RMS_M = 0.5e-3          # ASSUMPTION: slow hand drift, RMS per axis (the accepted-writing hand model)
DRIFT_HZ = 0.3                # ASSUMPTION: its corner frequency (2nd-order low-pass of white noise)


def drift(t: np.ndarray, seed: int, rms_m: float = DRIFT_RMS_M, fc: float = DRIFT_HZ) -> np.ndarray:
    """A smooth 2-D random wander (ASSUMPTION): white noise through a 2nd-order causal low-pass, scaled to rms_m per
    axis, starting at zero."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(int(seed) % (2 ** 32))
    dt = float(t[1] - t[0])
    n = len(t)
    # simulate at 1 kHz and interpolate (cheap and smooth)
    t1 = np.arange(0.0, float(t[-1]) + 0.002, 1e-3)
    w = rng.standard_normal((len(t1) + 3000, 2))
    x = sosfilt(butter(2, fc, fs=1000.0, output="sos"), w, axis=0)[3000:]
    x = x - x[0]
    s = np.sqrt(np.mean(x ** 2, axis=0))
    x = x * (rms_m / np.maximum(s, 1e-30))
    return np.column_stack([np.interp(t, t1, x[:, a]) for a in range(2)])


def frames(e_t: np.ndarray, e: np.ndarray, every: int, Ts: float, noise: float, seed: int):
    """Camera frames at the ticks k * every: times, noisy values (the frame phase is the plant's)."""
    rng = np.random.default_rng(int(seed) % (2 ** 32))
    tf = np.arange(0.0, float(e_t[-1]), every * Ts)
    y = np.column_stack([np.interp(tf, e_t, e[:, a]) for a in range(2)])
    y = y + noise * rng.standard_normal(y.shape)
    return tf, y


def design_rows(tf, y, e_t, e, order: int, ph: int, Ts: float, g: float, t_min: float = 1.0, sub: int = 2,
                weight: Optional[np.ndarray] = None):
    """Regressors (both axes stacked) and targets for phase ph: y_j..y_{j-order+1} -> e(t_j + ph Ts + g)."""
    j = np.arange(order - 1, len(tf))
    j = j[(tf[j] > t_min) & (tf[j] + ph * Ts + g < e_t[-1])][::sub]
    X = np.stack([y[j - q] for q in range(order)], axis=-1)          # (rows, 2, order)
    T = np.column_stack([np.interp(tf[j] + ph * Ts + g, e_t, e[:, a]) for a in range(2)])
    w = None if weight is None else np.interp(tf[j], e_t, weight)
    return X, T, w


def fit_phase(blocks: Sequence, ridge: float) -> np.ndarray:
    A = sum(b[0] for b in blocks)
    bb = sum(b[1] for b in blocks)
    n = A.shape[0]
    lam = ridge * float(np.trace(A)) / n
    return np.linalg.solve(A + lam * np.eye(n), bb)


def normal_blocks(X, T, w=None):
    """X'WX and X'WT with both axes pooled (isotropic coefficients)."""
    if w is None:
        w = np.ones(X.shape[0])
    A = np.zeros((X.shape[2], X.shape[2]))
    b = np.zeros(X.shape[2])
    for a in range(2):
        Xa = X[:, a, :]
        A += Xa.T @ (Xa * w[:, None])
        b += Xa.T @ (T[:, a] * w)
    return A, b


def training_signals(quick: bool = False, log=CM.log) -> List[Dict]:
    """The tip deviation signals of the tuning cases (ordinary pen, page still): tremor, and tremor + drift."""
    from handwriting import plant as PL
    from readable import common as RC
    out = []
    notes = (0, 1) if quick else tuple(range(10))
    for i in notes:
        note = RC.tuning_note(i)
        rc = PL.run(note.scenario("none", None), note.pens["none"], note.hand)
        for kind in ("PD", "ET"):
            for level in ("severe", "moderate"):
                spec = RC.tuning_spec(i, kind, level)
                dr = RC.tuning_tremor(note, spec)
                r = PL.run(note.scenario("none", dr.d), note.pens["none"], note.hand)
                n = min(len(r.t), len(rc.t))
                e = r.ink[:n] - rc.ink[:n]
                out.append({"id": spec["id"], "fold": i % 5, "level": level, "t": r.t[:n].copy(), "e": e,
                            "contact": r.contact[:n].copy(), "drift_seed": CM.h("pred-drift", spec["id"])})
        log(f"[predictor] note {i}: training signals built")
        del note
    return out


def fit(signals: Sequence[Dict], cam_hz: float = 250.0, cam_latency: float = 6e-3, noise: float = 15e-6,
        g: float = 6.07e-3, Ts: float = 5e-4, quick: bool = False, with_drift: bool = True, log=CM.log) -> Dict:
    """Choose (order, ridge) by the cross-fitted RMS prediction error (severe cases, contact samples), then fit on all
    tuning cases.  Returns the coefficient matrix (n_phase x order) and the scores."""
    t0 = time.time()
    every = max(1, int(round(1.0 / (cam_hz * Ts))))
    lat = int(round(cam_latency / Ts))
    phases = list(range(lat, lat + every))
    n_phase = lat + every
    folds = sorted({s["fold"] for s in signals})
    # frames once per signal (noise seed per case); tremor, and tremor + drift (accepted-writing variant)
    prepared = []
    for s in signals:
        variants = [("trem", s["e"])]
        if with_drift:
            variants.append(("drift", s["e"] + drift(s["t"], s["drift_seed"])))
        for tag, e in variants:
            tf, y = frames(s["t"], e, every, Ts, noise, CM.h("frames", s["id"], tag))
            prepared.append({"fold": s["fold"], "level": s["level"], "tf": tf, "y": y, "t": s["t"], "e": e,
                             "w": s["contact"], "tag": tag})
    orders = ORDER_GRID[:2] if quick else ORDER_GRID
    scores = {}
    best = None
    for order in orders:
        rows = {ph: [design_rows(p["tf"], p["y"], p["t"], p["e"], order, ph, Ts, g, weight=p["w"]) for p in prepared]
                for ph in phases}
        blocks = {ph: [normal_blocks(*r) for r in rows[ph]] for ph in phases}
        for ridge in RIDGE_GRID:
            se, cnt = 0.0, 0.0
            for k in folds:
                for ph in phases:
                    coef = fit_phase([b for b, p in zip(blocks[ph], prepared) if p["fold"] != k], ridge)
                    for r, p in zip(rows[ph], prepared):
                        if p["fold"] != k or p["level"] != "severe":
                            continue
                        X, T, w = r
                        pred = np.stack([X[:, a, :] @ coef for a in range(2)], axis=1)
                        err = np.sum((pred - T) ** 2, axis=1)
                        se += float(np.sum(err * w))
                        cnt += float(np.sum(w))
            rms = float(np.sqrt(se / max(cnt, 1.0)))
            scores[f"order{order}_ridge{ridge:g}"] = rms
            if best is None or rms < best[0] - 1e-12:
                best = (rms, order, ridge)
    order, ridge = best[1], best[2]
    coef = np.zeros((n_phase, order))
    for ph in phases:
        blocks = [normal_blocks(*design_rows(p["tf"], p["y"], p["t"], p["e"], order, ph, Ts, g, weight=p["w"]))
                  for p in prepared]
        coef[ph] = fit_phase(blocks, ridge)
    # the unpredicted baseline (hold the newest frame) on the same severe cases, for reference
    se, cnt = 0.0, 0.0
    for p in prepared:
        if p["level"] != "severe":
            continue
        for ph in phases:
            X, T, w = design_rows(p["tf"], p["y"], p["t"], p["e"], 1, ph, Ts, g, weight=p["w"])
            err = np.sum((X[:, :, 0] - T) ** 2, axis=1)
            se += float(np.sum(err * w)); cnt += float(np.sum(w))
    out = {"cam_hz": cam_hz, "cam_latency_s": cam_latency, "noise_m": noise, "horizon_s": g, "Ts": Ts,
           "cam_every": every, "cam_lat_ticks": lat, "phases": phases, "order": order, "ridge": ridge,
           "cv_rms_m": best[0], "hold_rms_m": float(np.sqrt(se / max(cnt, 1.0))), "scores": scores,
           "coef": coef.tolist(), "dc_gain_by_phase": [float(np.sum(coef[ph])) for ph in phases],
           "n_signals": len(signals), "with_drift": with_drift, "elapsed_s": time.time() - t0,
           "rule": "lowest cross-fitted RMS prediction error (E's folds; severe cases; contact-weighted), then refit on "
                   "all tuning cases; tuning split only"}
    log(f"[predictor] {cam_hz:g} Hz, {cam_latency * 1e3:g} ms, {noise * 1e6:g} um, g {g * 1e3:.2f} ms: order {order}, "
        f"ridge {ridge:g}, cv RMS {best[0] * 1e6:.1f} um (hold {out['hold_rms_m'] * 1e6:.1f} um) in {out['elapsed_s']:.0f} s")
    return out


def load_or_fit(key: str, signals_fn, quick: bool = False, **kw) -> Dict:
    p = CM.cache_dir(quick, "predictors") / f"{key}.json"
    d = CM.jload(p)
    if d is not None:
        return d
    d = fit(signals_fn(), quick=quick, **kw)
    CM.jdump(p, d, indent=None)
    return d
