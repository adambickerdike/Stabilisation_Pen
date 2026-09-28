"""Personalisation: per-writer tuning from a short calibration task against frozen population parameters (SIMULATION).

Calibration task (about 20 s, known templates): an Archimedean spiral (3 turns to 5 mm radius), a
slow circle and back-and-forth lines, drawn by the writer with his or her tremor (a different
random realisation of the same tremor process; seeds test_seed + fusion.CALIB_SEED_OFFSET).  The pen
records its sensor streams as in use; the phone (offline) knows the shapes but not the writer's timing
along them, so it matches each page-sensor sample to the shape (progress-constrained nearest point),
smooths the progress (the shapes are drawn slowly) and takes the residual, page path minus shape,
band-passed 3-15 Hz: the tremor as the page sensor sees it (`page_label`).  No simulator truth is used.
From it the phone estimates the tremor frequency (spectral peak), its amplitude and its 2nd-harmonic
share, then chooses, among a small family of AKF parameter sets built around the population set,
the one whose tremor-band output best matches that label on the calibration recording itself.  The family: frequency window f_hat +- {1.5, 3} Hz (the tracker cannot wander into the
writing band), initial frequency f_hat, amplitude gate scaled to the measured amplitude, oscillator
process noise scaled x{0.5, 1, 2}, frequency gate off (tremor is known to be present).
The chosen set goes to the pen (proposed CAL_USER record fields; docs/icd.md s3 is not edited).
Only the calibration recording and population parameters are used: never the test recording.
"""
from __future__ import annotations

import itertools
import math
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch
from scipy.spatial import cKDTree

from . import CALIB_SEED_OFFSET
from . import data as FD
from . import estimators as ES
from . import sensors as S

import sim.pencil  # noqa: F401,E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

CAL_DURATION = 20.0


def calibration_path(dt: float = FD.DT) -> sg.Intended:
    """Spiral, circle and lines with pen lifts between them (about 20 s)."""
    pb = sg.PathBuilder(dt, start=(0.0, 0.0))
    pb.dwell(0.3).pen(True)
    c = pb.pos.copy()
    pb.curve(lambda u: c + 5e-3 * u * np.array([np.cos(6 * np.pi * u), np.sin(6 * np.pi * u)]), 6.0, name="spiral")
    pb.pen(False).move((14e-3, 0.0), 0.4).pen(True)
    c2 = pb.pos + np.array([0.0, 3e-3])
    pb.curve(lambda u: c2 + 3e-3 * np.array([np.sin(2 * np.pi * u), -np.cos(2 * np.pi * u)]), 3.0, name="circle")
    pb.pen(False).move((22e-3, -2e-3), 0.4).pen(True)
    for i in range(8):
        tgt = (pb.pos[0] + (6e-3 if i % 2 == 0 else -6e-3), pb.pos[1] + 0.8e-3)
        pb.move(tgt, 0.9, name="line")
        pb.dwell(0.05)
    pb.pen(False).dwell(0.3)
    it = pb.build()
    n = int(round(CAL_DURATION / dt))
    if len(it.t) < n:        # pad with a pen-up dwell to the fixed duration
        k = n - len(it.t)
        it = sg.Intended(np.arange(n) * dt, np.vstack([it.xy, np.repeat(it.xy[-1:], k, 0)]),
                         np.r_[it.pen_down, np.zeros(k, bool)], np.r_[it.lift, np.full(k, it.lift[-1])], it.features)
    return it


def calibration_records(seed: int, f0: float, amp: float, cfg=None, clean: bool = True):
    """(tremor record, clean record or None) of the calibration task (the clean run is for checks only)."""
    import copy
    it = calibration_path()
    d = sg.tremor(it.t, sg.TremorSpec(f0=f0, amp_pk=amp), np.random.default_rng(seed + CALIB_SEED_OFFSET))
    sc1 = scenarios._assemble(it, d, 1.0, 50.0, meta={"kind": "calibration"})
    sc0 = scenarios._assemble(it, np.zeros_like(d), 1.0, 50.0, meta={"kind": "calibration_clean"})
    r1 = S.record_from_result(FD.run(sc1, cfg=cfg, seed=seed + CALIB_SEED_OFFSET), sc1)
    r0 = S.record_from_result(FD.run(sc0, cfg=cfg, seed=seed + CALIB_SEED_OFFSET), sc0) if clean else None
    return r1, r0


def _segments(mask: np.ndarray, min_len: int):
    """Contiguous runs of True of at least min_len samples: list of (start, stop)."""
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return [(i, j) for i, j in zip(a, b) if j - i >= min_len]


def page_label(st: S.Streams, shape: np.ndarray, fs_prog: float = 1.5) -> Dict:
    """Tremor seen by the page sensor during the calibration task, computed as the phone would (offline).

    shape: the known calibration shapes (dense polyline in drawing order, page frame, registered only up to an
    offset).  Each valid in-contact page sample is matched to the shape by a nearest-point search constrained to
    move forward (re-acquired globally at each touchdown); the matched progress is smoothed with a zero-phase
    `fs_prog` low-pass (the shapes take 0.9-6 s each); the residual page - shape(progress) minus its segment mean
    is band-passed 3-15 Hz per contact segment.  Returns the sample indices used, the label (m) and the segments."""
    fs = float(st.meta.get("page_rate", 1.0 / np.median(np.diff(st.pos_t))))
    con = np.interp(st.pos_t, st.con_t, st.con) > 0.5
    ok = (st.pos_ok > 0.5) & con
    segs = _segments(ok, int(0.6 * fs))
    sos = butter(4, [3.0, 15.0], btype="band", fs=fs, output="sos")
    sos_p = butter(2, fs_prog, fs=fs, output="sos")
    lab = np.full((len(st.pos_t), 2), np.nan)
    tree = cKDTree(shape)
    for a, b in segs:
        P = st.pos[a:b]
        _, j0 = tree.query(P)
        P = P - np.median(P - shape[j0], axis=0)          # registration offset (the phone knows the shape, not its place)
        k = np.empty(b - a)
        _, k0 = tree.query(P[0])
        kp = int(k0)
        for j in range(b - a):
            lo, hi = max(0, kp - 20), min(len(shape), kp + 400)
            kk = lo + int(np.argmin(np.sum((shape[lo:hi] - P[j]) ** 2, axis=1)))
            k[j] = kk
            kp = kk
        ks = sosfiltfilt(sos_p, k, padlen=min(3 * 6, len(k) - 1))
        ks = np.clip(ks, 0, len(shape) - 1)
        i = np.floor(ks).astype(int)
        f = (ks - i)[:, None]
        i2 = np.minimum(i + 1, len(shape) - 1)
        T = shape[i] * (1 - f) + shape[i2] * f
        r = P - T
        r = r - r.mean(axis=0)
        lab[a:b] = sosfiltfilt(sos, r, axis=0)
    use = np.zeros(len(st.pos_t), bool)
    edge = int(0.15 * fs)
    for a, b in segs:
        use[a + edge:b - edge] = True
    use &= st.pos_t > 1.0
    return {"label": lab, "use": use, "segments": segs, "fs": fs, "sos": sos}


def band_at_page(dh: np.ndarray, st: S.Streams, pl: Dict) -> np.ndarray:
    """The estimator output at the page-sample times, band-passed per contact segment like the label."""
    out = np.full((len(st.pos_t), 2), np.nan)
    x = np.column_stack([np.interp(st.pos_t, st.tick_t, dh[:, 0]), np.interp(st.pos_t, st.tick_t, dh[:, 1])])
    for a, b in pl["segments"]:
        out[a:b] = sosfiltfilt(pl["sos"], x[a:b] - x[a:b].mean(axis=0), axis=0)
    return out


def tremor_from_calibration(pl: Dict) -> Dict:
    """Frequency, amplitude and harmonic share of the page-sensor tremor label (phone, offline)."""
    m = pl["use"]
    rb = pl["label"][m]
    fs = pl["fs"]
    f, P = welch(rb, fs=fs, nperseg=min(4096, len(rb)), axis=0)
    Ps = P.sum(axis=1)
    band = (f >= 3.0) & (f <= 14.5)
    f_hat = float(f[band][np.argmax(Ps[band])])
    amp_rms = float(np.sqrt(np.mean(np.sum(rb ** 2, axis=1))))
    h = (f > 1.8 * f_hat) & (f < 2.2 * f_hat)
    f1 = (f > 0.8 * f_hat) & (f < 1.2 * f_hat)
    harm = float(np.sqrt(Ps[h].sum() / max(Ps[f1].sum(), 1e-30))) if h.any() else 0.0
    return {"f_hat_hz": f_hat, "amp_rms_um": amp_rms * 1e6, "harmonic_ratio": harm}


def candidates(pop: Dict, est: Dict):
    """The personal parameter family around the population set."""
    f = est["f_hat_hz"]
    A = est["amp_rms_um"] * 1e-6
    out = []
    for half, qs, gate_scale in itertools.product((1.5, 3.0), (0.5, 1.0, 2.0), (0.15, 0.35)):
        p = dict(pop)
        p.update({"w0_hz": f, "wmin_hz": max(2.5, f - half), "wmax_hz": min(15.0, f + half), "f_gate": 0.0,
                  "qt": pop.get("qt", 1e-9) * qs, "a_lo": gate_scale * A * 0.5, "a_hi": gate_scale * A * 1.5})
        out.append(p)
    return out


def personalise(seed: int, f0: float, amp: float, pop: Dict, sensor_kw: Dict) -> Dict:
    """Calibration -> chosen personal parameters for the AKF.  Uses only the calibration recording and the known
    shapes (never the test recording, never the simulator's true disturbance)."""
    r1, _ = calibration_records(seed, f0, amp, clean=False)
    cfg = S.config(**sensor_kw)
    st = S.make_streams(r1, cfg, seed + CALIB_SEED_OFFSET + 1)
    it = calibration_path(dt=1e-3)
    pl = page_label(st, it.xy[it.pen_down])
    est = tremor_from_calibration(pl)
    m = pl["use"]
    lab = pl["label"][m]
    den = max(float(np.sum(lab ** 2)), 1e-30)
    best, best_s, table = None, 1e9, []
    for p in candidates(pop, est):
        dh, _ = ES.akf(st, p)
        e = band_at_page(dh, st, pl)[m] - lab
        s = float(np.sqrt(np.sum(e ** 2) / den))
        table.append(s)
        if s < best_s:
            best, best_s = p, s
    dh, _ = ES.akf(st, pop)
    s_pop = float(np.sqrt(np.sum((band_at_page(dh, st, pl)[m] - lab) ** 2) / den))
    return {"params": best, "calibration": est, "calib_band_rr": best_s, "n_candidates": len(table),
            "calib_band_rr_population": s_pop}
