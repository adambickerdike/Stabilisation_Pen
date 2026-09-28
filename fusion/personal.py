"""Personalisation: per-writer tuning from a short calibration task against frozen population parameters (SIMULATION).

Calibration task (about 20 s, known templates): an Archimedean spiral (3 turns to 5 mm radius), a
slow circle and back-and-forth lines, drawn by the writer with his or her tremor (a different
random realisation of the same tremor process; seeds test_seed + fusion.CALIB_SEED_OFFSET).  The pen
records its sensor streams as in use; the phone (offline) knows the template, so it can see the
tremor directly: the page-sensor path minus the template, band-passed 3-15 Hz.
From it the phone estimates the tremor frequency (spectral peak), its amplitude and its 2nd-harmonic
share, then chooses, among a small family of AKF parameter sets built around the population set,
the one with the lowest tremor-band residual on the calibration recording itself (the known template
is the label).  The family: frequency window f_hat +- {1.5, 3} Hz (the tracker cannot wander into the
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


def calibration_records(seed: int, f0: float, amp: float, cfg=None):
    """(tremor record, clean record, intended path at the record times) of the calibration task."""
    import copy
    it = calibration_path()
    d = sg.tremor(it.t, sg.TremorSpec(f0=f0, amp_pk=amp), np.random.default_rng(seed + CALIB_SEED_OFFSET))
    sc1 = scenarios._assemble(it, d, 1.0, 50.0, meta={"kind": "calibration"})
    sc0 = scenarios._assemble(it, np.zeros_like(d), 1.0, 50.0, meta={"kind": "calibration_clean"})
    r1 = S.record_from_result(FD.run(sc1, cfg=cfg, seed=seed + CALIB_SEED_OFFSET), sc1)
    r0 = S.record_from_result(FD.run(sc0, cfg=cfg, seed=seed + CALIB_SEED_OFFSET), sc0)
    return r1, r0


def tremor_from_calibration(st: S.Streams, rec: S.Record) -> Dict:
    """Frequency, amplitude and harmonic share from the page-sensor path minus the known template (phone, offline)."""
    tp = st.pos_t
    ok = st.pos_ok > 0.5
    tmpl = np.column_stack([np.interp(tp, rec.t, rec.intended[:, 0]), np.interp(tp, rec.t, rec.intended[:, 1])])
    con = np.interp(tp, st.con_t, st.con) > 0.5
    r = st.pos - tmpl
    fs = st.meta.get("page_rate", 1000.0)
    sos = butter(4, [3.0, 15.0], btype="band", fs=fs, output="sos")
    rb = sosfiltfilt(sos, r, axis=0)
    m = ok & con & (tp > 1.0)
    f, P = welch(rb[m], fs=fs, nperseg=min(4096, int(m.sum())), axis=0)
    Ps = P.sum(axis=1)
    band = (f >= 3.0) & (f <= 14.5)
    f_hat = float(f[band][np.argmax(Ps[band])])
    amp_rms = float(np.sqrt(np.mean(np.sum(rb[m] ** 2, axis=1))))
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
    """Calibration -> chosen personal parameters for AKF.  Uses only the calibration recording."""
    r1, r0 = calibration_records(seed, f0, amp)
    cfg = S.config(**sensor_kw)
    st = S.make_streams(r1, cfg, seed + CALIB_SEED_OFFSET + 1)
    est = tremor_from_calibration(st, r1)
    # label for the choice: the page-sensor-visible tremor, band-passed, at the ticks (known template)
    d = S.truth_at(st.tick_t, r1, r0)
    fs = 1.0 / float(st.tick_t[1] - st.tick_t[0])
    sos = butter(4, [3.0, 15.0], btype="band", fs=fs, output="sos")
    db = sosfiltfilt(sos, d, axis=0)
    con = np.interp(st.tick_t, r1.t, r1.contact) > 0.5
    m = con & (st.tick_t > 1.0)
    best, best_s, table = None, 1e9, []
    for p in candidates(pop, est):
        dh, _ = ES.akf(st, p)
        e = sosfiltfilt(sos, dh, axis=0) - db
        s = float(np.sqrt(np.sum(e[m] ** 2) / max(np.sum(db[m] ** 2), 1e-30)))
        table.append(s)
        if s < best_s:
            best, best_s = p, s
    return {"params": best, "calibration": est, "calib_band_rr": best_s, "n_candidates": len(table),
            "calib_band_rr_population": _pop_score(st, pop, db, m, sos)}


def _pop_score(st, pop, db, m, sos):
    dh, _ = ES.akf(st, pop)
    e = sosfiltfilt(sos, dh, axis=0) - db
    return float(np.sqrt(np.sum(e[m] ** 2) / max(np.sum(db[m] ** 2), 1e-30)))
