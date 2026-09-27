r"""Synthetic training data for the causal disturbance predictor (SIMULATION).

Wraps the project generators in stabpen.signals without modifying them:
  * intended motion: sigma-lognormal handwriting (lognormal_handwriting) with a
    per-writer size, slant, advance and speed (time scaling), interleaved with
    randomised deliberate-feature primitives built with stabpen.signals.PathBuilder
    (sharp corners, dots, hatching at 2.5-6 Hz, loops, fast strokes);
  * disturbance: stabpen.signals tremor model (OU frequency wander, AM, ellipse,
    2nd harmonic, bursts, optional broadband part), switched on and off in
    segments with 0.3 s raised-cosine envelopes so every recording mixes tremor
    and no-tremor writing.  `tremor_with_state` re-implements
    stabpen.signals.tremor line by line (same random-number order, verified
    equal in ml/tests) and also returns the oscillator state that the
    oscillator-state oracle needs.
Kinematic housing model: the housing follows the hand, p_H = intended + d.
(The coupled hand-pen-paper dynamics are exercised only by the simulator
realism set in ml/datasets.py.)
Sensor model (optical page displacement, docs/icd.md s2/s5): per-recording
latency 2-3 ms, white position noise 2.5-3.5 um RMS per axis per sample,
scale error +-1 %, sampled at 250 Hz; the predictor sees increments.
Time-stamp convention: tick k is stamped t_k = k/250 s when it becomes
available; it measures the housing at t_k - delay.  Target d(t_k + h), h = 6 ms.
Nothing here is a recording of a person.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field
from typing import List, Optional

import numpy as np

from . import common as C
from stabpen import signals as sg

GEN_VERSION = "ml.synth 1.0"


# ---------------------------------------------------------------- tremor with oscillator state
def tremor_with_state(t, spec: sg.TremorSpec, rng, harm_phase=0.7):
    """Identical to stabpen.signals.tremor (same statements, same RNG call order)
    for harm_phase = 0.7 rad (the fixed value in stabpen), but also returns the
    oscillator state: instantaneous frequency f (Hz), phase (rad), amplitude
    envelope amp (m, incl. AM and onset ramp) and the non-oscillatory part (bursts
    + broadband) separately.  harm_phase != 0.7 is used only by the stress set."""
    n = len(t)
    dt = t[1] - t[0]
    f = spec.f0 + sg._ou(n, dt, spec.f_tau, spec.f_jitter, rng)
    f = np.clip(f, 0.5, None)
    phase = 2 * np.pi * np.cumsum(f) * dt + rng.uniform(0, 2 * np.pi)
    amp = spec.amp_pk * np.clip(1 + sg._ou(n, dt, spec.am_tau, spec.am_depth, rng), 0.0, None)
    ramp = np.clip(t / max(spec.onset, 1e-9), 0, 1)
    amp = amp * ramp
    d = _oscillator(amp, phase, spec, harm_phase)
    extra = np.zeros_like(d)
    if spec.broadband_rms > 0:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [3.0, 12.0], btype="band", fs=1 / dt, output="sos")
        wn = rng.standard_normal((n, 2))
        bb = sosfiltfilt(sos, wn, axis=0)   # offline generation only (not a causal feature)
        bb *= spec.broadband_rms / (bb.std(axis=0) + 1e-12)
        extra += bb
    if spec.burst_rate > 0:
        nb = rng.poisson(spec.burst_rate * t[-1])
        for tb in rng.uniform(0, t[-1], nb):
            w = np.exp(-0.5 * ((t - tb) / 0.03) ** 2)
            ang = rng.uniform(0, 2 * np.pi)
            extra += spec.burst_amp * w[:, None] * np.array([np.cos(ang), np.sin(ang)])[None, :]
    return d + extra, {"f": f, "phase": phase, "amp": amp, "extra": extra}


def _oscillator(amp, phase, spec, harm_phase=0.7):
    maj = amp * (np.cos(phase) + spec.harmonic * np.cos(2 * phase + harm_phase))
    mnr = amp * spec.ellipticity * (np.sin(phase) + spec.harmonic * np.sin(2 * phase + harm_phase))
    c, s = np.cos(spec.orientation), np.sin(spec.orientation)
    return np.column_stack([c * maj - s * mnr, s * maj + c * mnr])


# ---------------------------------------------------------------- writer profiles
@dataclass
class SensorSpec:
    delay_s: float
    noise_um: float
    scale_err: float
    fs_hz: float = C.FS


@dataclass
class WriterProfile:
    writer_id: str
    split: str
    letter_height_m: float
    slant_deg: float
    advance_ratio: float
    speed: float                   # time-scale factor of the lognormal generator (>1 = faster)
    strokes_per_word: tuple
    word_gap_s: float
    feature_frac: float            # fraction of chunks that are deliberate-feature primitives
    tremor: Optional[dict]         # writer-level TremorSpec fields (None = never tremor)
    tremor_duty: float
    sensor: SensorSpec
    seed: dict = field(default_factory=dict)

    def to_json(self):
        d = asdict(self)
        d["strokes_per_word"] = list(self.strokes_per_word)
        return d


def _draw_f0(rng, rule):
    """rule: 'main' = [4, 12] Hz excluding the holdout band; 'holdout' = inside it."""
    lo, hi = C.HOLDOUT_BAND
    if rule == "holdout":
        return float(rng.uniform(lo, hi))
    while True:
        f = float(rng.uniform(4.0, 12.0))
        if not (lo <= f < hi):
            return f


REGIMES = {
    # training distribution
    "main": {},
    # tremor outside the training ranges (faster FM/AM wander, stronger random-phase harmonic,
    # broadband part in every writer); writing as in training
    "stress_tremor": {"f_jitter": (0.6, 1.0), "f_tau": (0.3, 0.8), "am_depth": (0.5, 0.8), "am_tau": (0.2, 0.5),
                      "harmonic": (0.3, 0.5), "harm_phase": (0.0, 2 * np.pi), "broadband_rms": (2e-5, 5e-5)},
    # writing outside the training ranges (faster, larger, more deliberate hatching); tremor as in training
    "stress_writing": {"speed": (2.1, 2.6), "letter_height": (5e-3, 8e-3), "feature_frac": (0.5, 0.5)},
}


def draw_writer(rng, writer_id, split, f0_rule="main", p_no_tremor=0.15, regime="main"):
    """Writer-level parameters.  The same random draws are made in every regime; a
    regime then overrides selected ranges (a fresh RNG stream per override)."""
    speed = float(np.exp(rng.uniform(np.log(1.0), np.log(2.1))))
    h = float(rng.uniform(2.5e-3, 7.0e-3))
    tremor = None
    if rng.random() >= p_no_tremor:
        bursts = rng.random() < 0.3
        broadband = rng.random() < 0.2
        tremor = {
            "f0": _draw_f0(rng, f0_rule),
            "amp_pk": float(np.exp(rng.uniform(np.log(1.0e-4), np.log(8.0e-4)))),
            "f_jitter": float(rng.uniform(0.1, 0.5)),
            "f_tau": float(rng.uniform(0.8, 3.0)),
            "am_depth": float(rng.uniform(0.1, 0.5)),
            "am_tau": float(rng.uniform(0.4, 1.5)),
            "harmonic": float(rng.uniform(0.0, 0.3)),
            "ellipticity": float(rng.uniform(0.1, 0.9)),
            "orientation": float(rng.uniform(0.0, np.pi)),
            "onset": 1e-6,
            "burst_rate": float(rng.uniform(0.05, 0.3)) if bursts else 0.0,
            "burst_amp": float(rng.uniform(1.0e-4, 4.0e-4)),
            "broadband_rms": float(rng.uniform(5e-6, 2e-5)) if broadband else 0.0,
        }
    sensor = SensorSpec(delay_s=float(rng.uniform(0.002, 0.003)), noise_um=float(rng.uniform(2.5, 3.5)),
                        scale_err=float(rng.uniform(-0.01, 0.01)))
    prof = WriterProfile(writer_id=writer_id, split=split, letter_height_m=h,
                         slant_deg=float(rng.uniform(60.0, 90.0)), advance_ratio=float(rng.uniform(0.4, 0.7)),
                         speed=speed, strokes_per_word=(int(rng.integers(4, 7)), int(rng.integers(8, 12))),
                         word_gap_s=float(rng.uniform(0.15, 0.4)), feature_frac=float(rng.uniform(0.1, 0.35)),
                         tremor=tremor, tremor_duty=float(rng.uniform(0.45, 0.75)), sensor=sensor)
    ov = REGIMES[regime]
    if ov:
        r2 = np.random.default_rng(rng.integers(2 ** 63))
        for k, (lo, hi) in ov.items():
            v = float(r2.uniform(lo, hi))
            if k == "speed":
                prof.speed = v
            elif k == "letter_height":
                prof.letter_height_m = v
            elif k == "feature_frac":
                prof.feature_frac = v
            elif prof.tremor is not None:
                prof.tremor[k] = v
    return prof


# ---------------------------------------------------------------- intended motion
def _handwriting_chunk(rng, prof: WriterProfile, dur, dt):
    s = prof.speed
    it = sg.lognormal_handwriting(dt * s, dur * s, rng, letter_height=prof.letter_height_m,
                                  slant_deg=prof.slant_deg, advance=prof.advance_ratio * prof.letter_height_m,
                                  strokes_per_word=prof.strokes_per_word, word_gap=prof.word_gap_s)
    feats = [(nm, t0 / s, t1 / s, m) for nm, t0, t1, m in it.features]
    return it.xy, it.pen_down, feats


def _feature_chunk(rng, prof: WriterProfile, dur, dt):
    """Randomised deliberate features (intended motion inside the tremor band)."""
    sc = prof.letter_height_m / 4e-3
    sp = prof.speed
    pb = sg.PathBuilder(dt, start=(0.0, 0.0))
    pb.dwell(0.15).pen(True)
    while pb._t < dur - 1.6:
        kind = rng.choice(["corners", "hatch", "dots", "loop", "line"])
        if kind == "corners":
            p0 = pb.pos.copy()
            for _ in range(int(rng.integers(3, 6))):
                ang = rng.uniform(0, 2 * np.pi)
                L = rng.uniform(2e-3, 6e-3) * sc
                pb.move(pb.pos + L * np.array([np.cos(ang), np.sin(ang)]), rng.uniform(0.2, 0.5) / sp, name="corner_edge")
                pb.dwell(rng.uniform(0.02, 0.06))
            pb.move(p0 + np.array([1e-3 * sc, 0.0]), 0.3 / sp)
        elif kind == "hatch":
            fh = rng.uniform(2.5, 6.0)            # deliberate oscillation frequency (Hz)
            amp = rng.uniform(1.5e-3, 4e-3) * sc
            ang = rng.uniform(np.pi / 3, 2 * np.pi / 3)
            u = np.array([np.cos(ang), np.sin(ang)])
            base = pb.pos.copy()
            for i in range(int(rng.integers(4, 11))):
                off = amp if i % 2 == 0 else 0.0
                pb.move(base + off * u + np.array([0.4e-3 * sc * (i + 1), 0.0]), 1.0 / (2 * fh), name="hatch")
        elif kind == "dots":
            pb.pen(False, 0.06)
            for _ in range(int(rng.integers(2, 6))):
                pb.move(pb.pos + np.array([rng.uniform(1.5e-3, 3e-3) * sc, rng.uniform(-1e-3, 1e-3) * sc]), 0.12 / sp)
                pb.pen(True, 0.05).dwell(rng.uniform(0.03, 0.08)).pen(False, 0.05)
            pb.pen(True, 0.06)
        elif kind == "loop":
            r = rng.uniform(1.5e-3, 4e-3) * sc
            c = pb.pos + np.array([0.0, r])
            turns = int(rng.integers(1, 3))
            pb.curve(lambda uu, c=c, r=r, turns=turns: c + r * np.array([np.sin(2 * np.pi * turns * uu),
                                                                          -np.cos(2 * np.pi * turns * uu)]),
                     rng.uniform(0.6, 1.5) * turns / sp, name="loop")
        else:  # fast straight stroke
            L = rng.uniform(6e-3, 15e-3) * sc
            ang = rng.uniform(-0.4, 0.4)
            pb.move(pb.pos + L * np.array([np.cos(ang), np.sin(ang)]), rng.uniform(0.1, 0.2) / sp, name="fast_stroke")
        pb.pen(False, 0.06).move(pb.pos + np.array([rng.uniform(2e-3, 5e-3) * sc, rng.uniform(-1e-3, 1e-3)]), 0.2 / sp)
        pb.pen(True, 0.06)
    pb.pen(False)
    it = pb.build()
    n = int(round(dur / dt))
    xy, down = it.xy, it.pen_down
    if len(xy) < n:
        pad = n - len(xy)
        xy = np.vstack([xy, np.repeat(xy[-1:], pad, 0)])
        down = np.concatenate([down, np.zeros(pad, bool)])
    return xy[:n], down[:n], [f for f in it.features if f[1] < dur]


def intended_path(rng, prof: WriterProfile, duration, dt):
    n = int(round(duration / dt))
    xs, ds, feats = [], [], []
    t_acc = 0.0
    end = np.zeros(2)
    while t_acc * (1 / dt) < n:
        dur = float(rng.uniform(6.0, 12.0))
        if rng.random() < prof.feature_frac:
            xy, down, fe = _feature_chunk(rng, prof, dur, dt)
        else:
            xy, down, fe = _handwriting_chunk(rng, prof, dur, dt)
        xy = xy - xy[0] + end
        end = xy[-1].copy()
        xs.append(xy)
        ds.append(down)
        feats += [(nm, t0 + t_acc, t1 + t_acc, m) for nm, t0, t1, m in fe]
        t_acc += len(xy) * dt
    return np.vstack(xs)[:n], np.concatenate(ds)[:n], feats


# ---------------------------------------------------------------- disturbance mixture
def _envelope(n, dt, ramp_s=0.3):
    e = np.ones(n)
    m = min(int(round(ramp_s / dt)), n // 2)
    if m > 0:
        r = 0.5 * (1 - np.cos(np.pi * np.arange(m) / m))
        e[:m] = r
        e[-m:] = r[::-1]
    return e


def tremor_mixture(rng, prof: WriterProfile, duration, dt, f0_rule="main"):
    """Alternating tremor-on / tremor-off segments.  Returns d (n,2) m and the
    per-sample state used for labels and the oracle."""
    n = int(round(duration / dt))
    d = np.zeros((n, 2))
    st = {"env": np.zeros(n), "f0": np.zeros(n), "amp": np.zeros(n), "phase": np.zeros(n), "f": np.zeros(n),
          "harm": np.zeros(n), "ell": np.zeros(n), "ori": np.zeros(n), "hph": np.full(n, 0.7)}
    segs = []
    if prof.tremor is None:
        return d, st, segs
    base = prof.tremor
    t = float(rng.uniform(0.0, 3.0))
    on = bool(rng.random() < 0.5)
    duty = prof.tremor_duty
    while t < duration:
        if on:
            L = float(rng.uniform(4.0, 12.0))
            i0 = int(round(t / dt))
            i1 = min(n, int(round((t + L) / dt)))
            if i1 - i0 > int(1.0 / dt):
                spec_d = dict(base)
                hph = float(spec_d.pop("harm_phase", 0.7))
                f0 = base["f0"] + float(rng.normal(0.0, 0.15))
                lo, hi = C.HOLDOUT_BAND
                if f0_rule == "holdout":
                    f0 = float(np.clip(f0, lo + 1e-3, hi - 1e-3))
                elif lo <= f0 < hi:                   # keep the nominal f0 outside the holdout band
                    f0 = lo - 1e-3 if base["f0"] < lo else hi + 1e-3
                spec_d["f0"] = float(np.clip(f0, 4.0, 12.0))
                spec_d["amp_pk"] = base["amp_pk"] * float(rng.uniform(0.7, 1.3))
                spec = sg.TremorSpec(**spec_d)
                tl = np.arange(i1 - i0) * dt
                ds, s = tremor_with_state(tl, spec, rng, hph)
                env = _envelope(i1 - i0, dt)
                d[i0:i1] += env[:, None] * ds
                st["env"][i0:i1] = env
                st["f0"][i0:i1] = spec.f0
                st["amp"][i0:i1] = s["amp"]
                st["phase"][i0:i1] = s["phase"]
                st["f"][i0:i1] = s["f"]
                st["harm"][i0:i1] = spec.harmonic
                st["ell"][i0:i1] = spec.ellipticity
                st["ori"][i0:i1] = spec.orientation
                st["hph"][i0:i1] = hph
                segs.append({"t0": i0 * dt, "t1": i1 * dt, "spec": {k: float(v) for k, v in vars(spec).items()} |
                             {"harm_phase": hph}})
            t += L
        else:
            t += float(rng.uniform(2.0, 7.0)) * (1.0 - duty) / 0.4
        on = not on
    return d, st, segs


def oscillator_oracle(st, H):
    """Prediction H ahead from the true oscillator state (perfect separation, known
    model, constant frequency and amplitude over the horizon; bursts and the
    broadband part are not predictable and are not included)."""
    ph = st["phase"] + 2 * np.pi * st["f"] * H
    amp = st["amp"] * st["env"]
    maj = amp * (np.cos(ph) + st["harm"] * np.cos(2 * ph + st["hph"]))
    mnr = amp * st["ell"] * (np.sin(ph) + st["harm"] * np.sin(2 * ph + st["hph"]))
    c, s = np.cos(st["ori"]), np.sin(st["ori"])
    return np.column_stack([c * maj - s * mnr, s * maj + c * mnr])


# ---------------------------------------------------------------- sensor + 250 Hz sampling
def sample_record(t_fine, p_h, d, pen, st, sensor: SensorSpec, rng, kf_params, oracle_phase_fine=None):
    """Apply the sensor model and build one recording at 250 Hz.

    t_fine (n,), p_h (n,2) housing position [m], d (n,2) true housing disturbance [m],
    pen (n,) contact, st: dict with 'env', 'f0', 'f' arrays (n,).  Returns dict of arrays."""
    from . import baselines
    dt = t_fine[1] - t_fine[0]
    dec = int(round(C.TS / dt))
    hk = int(round(C.H_S / dt))
    n = len(t_fine)
    K = (n - 1 - hk) // dec + 1
    tk = np.arange(K) * C.TS
    tp = np.clip(tk - sensor.delay_s, 0.0, None)
    y = np.column_stack([np.interp(tp, t_fine, p_h[:, 0]), np.interp(tp, t_fine, p_h[:, 1])])
    y = (1.0 + sensor.scale_err) * y + sensor.noise_um * 1e-6 * rng.standard_normal((K, 2))
    dp = np.zeros((K, 2))
    dp[1:] = np.diff(y, axis=0)
    it = np.arange(K) * dec + hk
    kfo = baselines.kf_run(np.cumsum(dp, axis=0), **kf_params)
    rec = {
        "t": tk,
        "dp_um": (dp * 1e6).astype(np.float32),
        "f_est": kfo["f_est"].astype(np.float32),
        "d_tgt_um": (d[it] * 1e6).astype(np.float32),
        "env_tgt": st["env"][it].astype(np.float32),
        "pen_tgt": pen[it].astype(bool),
        "f0_tgt": np.where(st["env"][it] > 0, st["f0"][it], 0.0).astype(np.float32),
        "finst_tgt": np.where(st["env"][it] > 0, st["f"][it], 0.0).astype(np.float32),
        "oracle_hold_um": (np.column_stack([np.interp(tp, t_fine, d[:, 0]), np.interp(tp, t_fine, d[:, 1])]) * 1e6
                           ).astype(np.float32),
    }
    if oracle_phase_fine is not None:
        rec["oracle_phase_um"] = (np.column_stack([np.interp(tp, t_fine, oracle_phase_fine[:, 0]),
                                                   np.interp(tp, t_fine, oracle_phase_fine[:, 1])]) * 1e6
                                  ).astype(np.float32)
    else:
        rec["oracle_phase_um"] = np.full((K, 2), np.nan, np.float32)
    return rec


def content_hash(arr):
    return hashlib.sha256(np.ascontiguousarray(arr, dtype=np.float64).tobytes()).hexdigest()[:16]


def make_recording(prof: WriterProfile, duration, seed_seq: np.random.SeedSequence, kf_params, f0_rule="main"):
    """One writer recording: intended writing + tremor mixture + sensor model."""
    r_path, r_trem, r_sens = [np.random.default_rng(s) for s in seed_seq.spawn(3)]
    dt = 1.0 / C.FS_FINE
    xy, pen, feats = intended_path(r_path, prof, duration, dt)
    d, st, segs = tremor_mixture(r_trem, prof, duration, dt, f0_rule)
    n = len(xy)
    t = np.arange(n) * dt
    H_true = C.H_S + prof.sensor.delay_s
    orc = oscillator_oracle(st, H_true)
    rec = sample_record(t, xy + d, d, pen, st, prof.sensor, r_sens, kf_params, orc)
    rec["meta"] = {"writer": prof.to_json(), "segments": segs, "duration_s": duration,
                   "content_hash": content_hash(xy), "n_features": len(feats),
                   "intended_spectrum": intended_band_fractions(xy, pen, dt),
                   "seed": {"entropy": int(seed_seq.entropy), "spawn_key": [int(k) for k in seed_seq.spawn_key]}}
    return rec


def intended_band_fractions(xy, pen, dt):
    """Share of intended velocity energy (pen-down) in 4-7 Hz and 8-12 Hz (Welch).
    Reported next to CON-25 (one public writer: ~0.17 and ~0.013-0.017)."""
    from scipy.signal import welch
    v = np.gradient(xy, dt, axis=0) * pen[:, None]
    f, p = welch(v, fs=1 / dt, nperseg=4096, axis=0)
    p = p.sum(axis=1)
    m = (f > 0.1) & (f < 25.0)
    tot = p[m].sum()
    band = lambda lo, hi: float(p[(f >= lo) & (f < hi)].sum() / tot) if tot > 0 else float("nan")  # noqa: E731
    return {"v_4_7Hz": band(4.0, 7.0), "v_8_12Hz": band(8.0, 12.0), "v_0_3Hz": band(0.1, 3.0),
            "speed_mean_down_mm_s": float(np.mean(np.linalg.norm(np.gradient(xy, dt, axis=0)[pen], axis=1)) * 1e3)
            if pen.any() else float("nan")}


def feature_course_record(scale, speed, sensor: SensorSpec, rng, kf_params, lead_s=1.0, tail_s=0.5):
    """Canonical stabpen.signals.feature_course (never used for training), time-scaled,
    no tremor, preceded by a stationary lead-in for estimator warm-up."""
    dt = 1.0 / C.FS_FINE
    it = sg.feature_course(dt * speed, scale=scale)
    nl, nt = int(lead_s / dt), int(tail_s / dt)
    xy = np.vstack([np.repeat(it.xy[:1], nl, 0), it.xy, np.repeat(it.xy[-1:], nt, 0)])
    pen = np.concatenate([np.zeros(nl, bool), it.pen_down, np.zeros(nt, bool)])
    n = len(xy)
    t = np.arange(n) * dt
    st = {"env": np.zeros(n), "f0": np.zeros(n), "f": np.zeros(n)}
    rec = sample_record(t, xy, np.zeros((n, 2)), pen, st, sensor, rng, kf_params, np.zeros((n, 2)))
    feats = [(nm, lead_s + t0 / speed, lead_s + t1 / speed) for nm, t0, t1, _ in it.features]
    rec["meta"] = {"course": {"scale": scale, "speed": speed}, "sensor": asdict(sensor),
                   "features": [{"name": nm, "t0": a, "t1": b} for nm, a, b in feats],
                   "content_hash": content_hash(xy)}
    return rec
