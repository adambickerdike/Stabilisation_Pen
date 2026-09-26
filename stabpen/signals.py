r"""Synthetic intended-motion and disturbance generators.

These signals exercise the pipeline and controllers.  They are NOT recordings
of any person and must never be reported as human data.

Intended motion
  * sigma-lognormal strokes (Plamondon's kinematic theory) for handwriting-like
    kinematics: each stroke j contributes a speed profile
        |v_j|(t) = D_j / (sigma_j sqrt(2 pi) (t - t0_j)) exp(-(ln(t - t0_j) - mu_j)^2 / (2 sigma_j^2))
    along a direction that rotates from theta_s to theta_e with the lognormal CDF.
    Used as a candidate prior, not a definition of correct handwriting.
  * minimum-jerk via-point segments (Flash & Hogan) for controlled features:
    sharp corners (stop at via point), dots (touch/lift), deliberate hatching,
    fast straight strokes, spirals.
Disturbance
  * narrowband tremor with Ornstein-Uhlenbeck frequency wander and amplitude
    modulation, elliptical polarisation, 2nd harmonic, optional onset and
    transient bursts.
Arrays are sampled at dt; positions in metres, page frame (x, y).  A pen-down
mask and a hand z-reference (lift schedule) accompany every intended path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

import numpy as np
from scipy.special import erf as _verf


@dataclass
class Intended:
    t: np.ndarray                 # (n,) s
    xy: np.ndarray                # (n,2) m, intended hand path in page frame
    pen_down: np.ndarray          # (n,) bool, intended contact
    lift: np.ndarray              # (n,) m, hand lift height above contact reference
    features: list = field(default_factory=list)  # (name, t_start, t_end, meta)


# ---------------------------------------------------------------- helpers
def min_jerk_profile(s):
    s = np.clip(s, 0.0, 1.0)
    return 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5


def _smooth_step(n):
    return min_jerk_profile(np.linspace(0, 1, n))


class PathBuilder:
    """Build piecewise minimum-jerk paths with pen-down/lift schedule."""

    def __init__(self, dt, start=(0.0, 0.0), lift_height=1.5e-3):
        self.dt = dt
        self.xy = [np.array(start, float)[None, :]]
        self.down = [np.array([False])]
        self.lift = [np.array([lift_height])]
        self.features = []
        self.lift_height = lift_height
        self._t = 0.0

    @property
    def pos(self):
        return self.xy[-1][-1]

    @property
    def is_down(self):
        return bool(self.down[-1][-1])

    def _append(self, xy, down, lift):
        self.xy.append(xy)
        self.down.append(down)
        self.lift.append(lift)
        self._t += len(xy) * self.dt

    def move(self, target, T, down=None, name=None):
        n = max(int(round(T / self.dt)), 2)
        s = _smooth_step(n)[:, None]
        p0 = self.pos
        xy = p0 + (np.asarray(target, float) - p0) * s
        d = self.is_down if down is None else down
        t0 = self._t
        self._append(xy, np.full(n, d), np.full(n, 0.0 if d else self.lift_height))
        if name:
            self.features.append((name, t0, self._t, {"from": p0.tolist(), "to": list(target)}))
        return self

    def dwell(self, T):
        n = max(int(round(T / self.dt)), 1)
        d = self.is_down
        self._append(np.repeat(self.pos[None, :], n, 0), np.full(n, d),
                     np.full(n, 0.0 if d else self.lift_height))
        return self

    def pen(self, down, T=0.08):
        """Touch down or lift with a smooth z transition (hand lift height)."""
        n = max(int(round(T / self.dt)), 2)
        s = _smooth_step(n)
        z = self.lift_height * (1 - s) if down else self.lift_height * s
        # contact flag switches mid-transition
        dflag = (s > 0.5) if down else (s < 0.5)
        self._append(np.repeat(self.pos[None, :], n, 0), dflag, z)
        return self

    def curve(self, fn, T, name=None):
        """Follow fn(u) for u in [0,1] (u advanced by min-jerk timing)."""
        n = max(int(round(T / self.dt)), 2)
        u = _smooth_step(n)
        pts = np.array([fn(ui) for ui in u])
        t0 = self._t
        d = self.is_down
        self._append(pts, np.full(n, d), np.full(n, 0.0 if d else self.lift_height))
        if name:
            self.features.append((name, t0, self._t, {}))
        return self

    def build(self):
        xy = np.vstack(self.xy)
        down = np.concatenate(self.down)
        lift = np.concatenate(self.lift)
        t = np.arange(len(xy)) * self.dt
        return Intended(t, xy, down, lift, self.features)


# ------------------------------------------------------ sigma-lognormal
def sigma_lognormal_velocity(t, D, t0, mu, sigma, th_s, th_e):
    """Velocity (n,2) of one sigma-lognormal stroke."""
    v = np.zeros((len(t), 2))
    tau = t - t0
    m = tau > 0
    lt = np.log(tau[m])
    speed = D / (sigma * sqrt(2 * np.pi) * tau[m]) * np.exp(-(lt - mu) ** 2 / (2 * sigma ** 2))
    phi = th_s + (th_e - th_s) * 0.5 * (1 + _verf((lt - mu) / (sigma * sqrt(2))))
    v[m, 0] = speed * np.cos(phi)
    v[m, 1] = speed * np.sin(phi)
    return v


def lognormal_handwriting(dt, duration, rng, letter_height=4e-3, slant_deg=75.0,
                          advance=2.2e-3, strokes_per_word=(6, 10), word_gap=0.25):
    """Handwriting-like scribble: alternating up/down lognormal strokes with a
    rightward advance, grouped into 'words' separated by pen lifts.  Returns
    Intended.  Intended stroke speed and spectrum follow from the drawn
    parameters (report them from the returned path, do not assume them)."""
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    v = np.zeros((n, 2))
    down = np.zeros(n, bool)
    lift = np.full(n, 1.5e-3)
    feats = []
    tc = 0.15
    slant = np.deg2rad(slant_deg)
    while tc < duration - 0.8:
        k = rng.integers(strokes_per_word[0], strokes_per_word[1] + 1)
        w_start = tc
        up = True
        for j in range(k):
            D = letter_height * rng.uniform(0.6, 1.15)
            mu = rng.uniform(-1.85, -1.45)        # peak time exp(mu - sigma^2) ~ 0.14-0.22 s
            sig = rng.uniform(0.22, 0.34)
            base = slant if up else slant + np.pi
            curv = rng.uniform(-0.9, 0.9)
            th_s = base - curv / 2
            th_e = base + curv / 2
            v += sigma_lognormal_velocity(t, D, tc, mu, sig, th_s, th_e)
            # rightward advance as a small overlapping stroke
            v += sigma_lognormal_velocity(t, advance * rng.uniform(0.7, 1.3) / 2, tc, mu, sig, 0.0, 0.0)
            tc += np.exp(mu) * rng.uniform(0.95, 1.25)
            up = not up
        w_end = tc + 0.2
        i0, i1 = int(w_start / dt), min(int(w_end / dt), n)
        down[i0:i1] = True
        lift[i0:i1] = 0.0
        feats.append(("word", w_start, w_end, {"strokes": int(k)}))
        # pen-up move to the next word (rightward lognormal stroke while lifted)
        v += sigma_lognormal_velocity(t, 3.0e-3, w_end, -1.5, 0.3, 0.0, 0.0)
        tc = w_end + word_gap + advance * 2 / 0.04
    xy = np.cumsum(v, axis=0) * dt
    # smooth the lift transitions (hand z) with 60 ms ramps
    ker = np.ones(int(0.06 / dt)) / int(0.06 / dt)
    lift = np.convolve(lift, ker, mode="same")
    return Intended(t, xy, down, lift, feats)


def feature_course(dt, rng=None, scale=1.0):
    """Deterministic course of intent-preservation features (no disturbance
    content): sharp corners, dots, deliberate hatching at 4 Hz, a fast straight
    stroke, a slow circle and a spiral.  Used to measure intended-feature
    distortion by the controller."""
    pb = PathBuilder(dt, start=(0.0, 0.0))
    s = scale
    pb.dwell(0.15).pen(True)
    # square with sharp corners (stop at each corner)
    for tgt in ((6e-3 * s, 0), (6e-3 * s, 6e-3 * s), (0, 6e-3 * s), (0, 0)):
        pb.move(tgt, 0.35, name="corner_edge")
        pb.dwell(0.03)
    pb.pen(False).move((10e-3 * s, 3e-3 * s), 0.2)
    # dots
    for i in range(4):
        pb.pen(True, 0.05).dwell(0.06).pen(False, 0.05)
        pb.features.append(("dot", pb._t - 0.16, pb._t, {"xy": pb.pos.tolist()}))
        pb.move((pb.pos[0] + 2.0e-3 * s, pb.pos[1]), 0.12)
    # deliberate hatching: 8 strokes of 3 mm at 4 Hz stroke rate (in tremor band!)
    pb.move((20e-3 * s, 0), 0.25).pen(True)
    for i in range(8):
        dy = 3e-3 * s if i % 2 == 0 else 0.0
        pb.move((pb.pos[0] + 0.5e-3 * s, dy), 0.125, name="hatch")
    pb.pen(False).move((26e-3 * s, 0), 0.2).pen(True)
    # fast straight stroke 12 mm in 0.12 s (peak ~190 mm/s)
    pb.move((38e-3 * s, 2e-3 * s), 0.12, name="fast_stroke")
    pb.pen(False).move((46e-3 * s, 3e-3 * s), 0.25).pen(True)
    # slow circle r = 3 mm in 1.2 s
    c = pb.pos + np.array([0.0, 3e-3 * s])
    pb.curve(lambda u: c + 3e-3 * s * np.array([np.sin(2 * np.pi * u), -np.cos(2 * np.pi * u)]), 1.2, name="circle")
    pb.pen(False).move((56e-3 * s, 3e-3 * s), 0.25).pen(True)
    # Archimedean spiral (standard tremor task) 3 turns, r to 5 mm, 3 s
    c2 = pb.pos.copy()
    pb.curve(lambda u: c2 + 5e-3 * s * u * np.array([np.cos(6 * np.pi * u), np.sin(6 * np.pi * u)]), 3.0, name="spiral")
    pb.pen(False).dwell(0.2)
    return pb.build()


# ------------------------------------------------------------- tremor
@dataclass
class TremorSpec:
    f0: float = 6.0             # Hz
    amp_pk: float = 3e-4        # m, peak of major axis
    f_jitter: float = 0.3       # Hz RMS wander
    f_tau: float = 1.5          # s, correlation time of wander
    am_depth: float = 0.3       # relative RMS amplitude modulation
    am_tau: float = 0.8         # s
    harmonic: float = 0.15      # relative 2nd harmonic amplitude
    ellipticity: float = 0.4    # minor/major
    orientation: float = 0.6    # rad, major-axis angle in page
    onset: float = 0.3          # s ramp
    burst_rate: float = 0.0     # transient bursts per second
    burst_amp: float = 5e-4     # m
    broadband_rms: float = 0.0  # m, band-limited 3-12 Hz noise component


def _ou(n, dt, tau, sd, rng):
    x = np.zeros(n)
    a = np.exp(-dt / tau)
    b = sd * np.sqrt(1 - a * a)
    e = rng.standard_normal(n)
    for i in range(1, n):
        x[i] = a * x[i - 1] + b * e[i]
    return x


def tremor(t, spec: TremorSpec, rng):
    """(n,2) tremor displacement of the hand reference in the page frame."""
    n = len(t)
    dt = t[1] - t[0]
    f = spec.f0 + _ou(n, dt, spec.f_tau, spec.f_jitter, rng)
    f = np.clip(f, 0.5, None)
    phase = 2 * np.pi * np.cumsum(f) * dt + rng.uniform(0, 2 * np.pi)
    amp = spec.amp_pk * np.clip(1 + _ou(n, dt, spec.am_tau, spec.am_depth, rng), 0.0, None)
    ramp = np.clip(t / max(spec.onset, 1e-9), 0, 1)
    amp = amp * ramp
    maj = amp * (np.cos(phase) + spec.harmonic * np.cos(2 * phase + 0.7))
    mnr = amp * spec.ellipticity * (np.sin(phase) + spec.harmonic * np.sin(2 * phase + 0.7))
    c, s = np.cos(spec.orientation), np.sin(spec.orientation)
    d = np.column_stack([c * maj - s * mnr, s * maj + c * mnr])
    if spec.broadband_rms > 0:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [3.0, 12.0], btype="band", fs=1 / dt, output="sos")
        wn = rng.standard_normal((n, 2))
        bb = sosfiltfilt(sos, wn, axis=0)   # offline generation only (not a causal feature)
        bb *= spec.broadband_rms / (bb.std(axis=0) + 1e-12)
        d += bb
    if spec.burst_rate > 0:
        nb = rng.poisson(spec.burst_rate * t[-1])
        for tb in rng.uniform(0, t[-1], nb):
            w = np.exp(-0.5 * ((t - tb) / 0.03) ** 2)
            ang = rng.uniform(0, 2 * np.pi)
            d += spec.burst_amp * w[:, None] * np.array([np.cos(ang), np.sin(ang)])[None, :]
    return d


def derivative(x, dt):
    return np.gradient(x, dt, axis=0)
