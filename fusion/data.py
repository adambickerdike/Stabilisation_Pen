"""Scenarios and P1 runs for the fusion study.

Test grid (harness convention, sim/pencil/run_study.py): scenarios.handwriting(seed, duration=5.0,
tremor=TremorSpec(f0, amp_pk), N0=1.0), PencilConfig() defaults, seeds 200-203 only for testing.

Tuning and training use other seeds (fusion.TUNE_SEEDS, TRAIN_SEEDS_BASE + i, VAL_SEEDS) and, for
the learned model, a domain-randomised copy of the same generators:
  * handwriting: `fast_lognormal_handwriting`, the sigma-lognormal generator of stabpen.signals with
    each stroke evaluated only on its support (identical draws; the truncation changes the path by
    < 1 nm, unit-tested), with randomised letter height, slant, stroke speed and advance;
  * tremor: stabpen.signals.tremor with randomised frequency 3-14 Hz, amplitude 0.05-0.6 mm,
    harmonic, amplitude and frequency drift, ellipticity, orientation, onset;
  * pen and hand: tilt 35-75 deg, user force 0.5-2 N, the hand impedance ranges of
    config/parameters.yaml `hand` (log-uniform, PencilConfig overrides), skid friction 0.06-0.2.
All of it is synthetic (SIMULATION); none of it is a person.
"""
from __future__ import annotations

import copy
import hashlib
import math
import os
from dataclasses import asdict, dataclass, field
from math import sqrt
from typing import Dict, Optional, Tuple

import numpy as np
from scipy.special import erf as _verf

from . import CACHE
from . import sensors as S

import sim.pencil  # noqa: F401,E402  (package init; NUMBA_CACHE_DIR already set by fusion)
from sim.pencil import model as M  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

DT = 25e-6
REC_HZ = 4000.0
DURATION = 5.0


# ------------------------------------------------------------------ test scenarios (harness convention)
_CLEAN: Dict = {}


def clean_scenario(seed: int, duration: float = DURATION):
    """scenarios.handwriting(seed, duration) without tremor, cached per process (the handwriting is the slow part)."""
    key = (seed, duration)
    if key not in _CLEAN:
        if len(_CLEAN) > 8:
            _CLEAN.clear()
        _CLEAN[key] = scenarios.handwriting(seed=seed, duration=duration, tremor=None, N0=1.0)
    return _CLEAN[key]


def test_scenario(seed: int, f0: float = 0.0, amp: float = 0.0, duration: float = DURATION):
    """Exactly scenarios.handwriting(seed, duration, tremor=TremorSpec(f0, amp), N0=1.0) (unit-tested): the
    tremor scenario is the clean one with the tremor added to the hand reference as _assemble does."""
    sc0 = clean_scenario(seed, duration)
    if amp <= 0:
        return sc0
    d = sg.tremor(sc0.t, sg.TremorSpec(f0=f0, amp_pk=amp), np.random.default_rng(seed + 1000))
    s1 = copy.copy(sc0)
    pref = sc0.pref.copy()
    pref[:, :2] = sc0.intended + d
    s1.pref = pref
    s1.vref = np.gradient(pref, sc0.t[1] - sc0.t[0], axis=0)
    s1.dtrue = d
    s1.meta = dict(sc0.meta, tremor=vars(sg.TremorSpec(f0=f0, amp_pk=amp)))
    return s1


def run(scn, ctrl=None, cfg=None, seed: int = 1):
    return M.run(scn, ctrl or M.Controller(mode="neutral"), cfg or M.PencilConfig(), seed=seed, rec_hz=REC_HZ)


# ------------------------------------------------------------------ fast sigma-lognormal handwriting
def _sl_vel_window(t, i0, i1, D, t0, mu, sigma, th_s, th_e, v):
    tau = t[i0:i1] - t0
    m = tau > 0
    lt = np.log(tau[m])
    speed = D / (sigma * sqrt(2 * np.pi) * tau[m]) * np.exp(-(lt - mu) ** 2 / (2 * sigma ** 2))
    phi = th_s + (th_e - th_s) * 0.5 * (1 + _verf((lt - mu) / (sigma * sqrt(2))))
    idx = np.flatnonzero(m) + i0
    v[idx, 0] += speed * np.cos(phi)
    v[idx, 1] += speed * np.sin(phi)


def fast_lognormal_handwriting(dt, duration, rng, letter_height=4e-3, slant_deg=75.0, advance=2.2e-3,
                               strokes_per_word=(6, 10), word_gap=0.25, mu_shift=0.0, support_s=3.0):
    """stabpen.signals.lognormal_handwriting with each stroke evaluated on [t0, t0 + support_s] only.

    Same random draws in the same order, so with mu_shift = 0 the path equals the reference up to the
    truncated lognormal tails (exp(-(ln 3 + 1.85)^2 / (2 * 0.34^2)) ~ 1e-38 of the peak).  mu_shift
    shifts every stroke's log-time (negative = faster strokes).
    """
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    v = np.zeros((n, 2))
    down = np.zeros(n, bool)
    lift = np.full(n, 1.5e-3)
    feats = []
    tc = 0.15
    slant = np.deg2rad(slant_deg)
    w = int(round(support_s / dt))

    def add(D, t0, mu, sig, th_s, th_e):
        i0 = max(0, int(t0 / dt))
        _sl_vel_window(t, i0, min(n, i0 + w), D, t0, mu, sig, th_s, th_e, v)

    while tc < duration - 0.8:
        k = rng.integers(strokes_per_word[0], strokes_per_word[1] + 1)
        w_start = tc
        up = True
        for j in range(k):
            D = letter_height * rng.uniform(0.6, 1.15)
            mu = rng.uniform(-1.85, -1.45) + mu_shift
            sig = rng.uniform(0.22, 0.34)
            base = slant if up else slant + np.pi
            curv = rng.uniform(-0.9, 0.9)
            add(D, tc, mu, sig, base - curv / 2, base + curv / 2)
            add(advance * rng.uniform(0.7, 1.3) / 2, tc, mu, sig, 0.0, 0.0)
            tc += np.exp(mu) * rng.uniform(0.95, 1.25)
            up = not up
        w_end = tc + 0.2
        i0, i1 = int(w_start / dt), min(int(w_end / dt), n)
        down[i0:i1] = True
        lift[i0:i1] = 0.0
        feats.append(("word", w_start, w_end, {"strokes": int(k)}))
        add(3.0e-3, w_end, -1.5 + mu_shift, 0.3, 0.0, 0.0)
        tc = w_end + word_gap + advance * 2 / 0.04
    xy = np.cumsum(v, axis=0) * dt
    kw = int(0.06 / dt)
    lift = np.convolve(lift, np.ones(kw) / kw, mode="same")
    return sg.Intended(t, xy, down, lift, feats)


# ------------------------------------------------------------------ domain randomisation
HAND_KEYS = ("grip_stiffness", "grip_damping", "mass", "arm_stiffness", "arm_damping", "normal_stiffness", "normal_damping")


@dataclass
class RandSpec:
    seed: int
    tremor: bool = True
    duration: float = DURATION
    f0: float = 6.0
    amp: float = 3e-4
    harmonic: float = 0.15
    am_depth: float = 0.3
    f_jitter: float = 0.3
    ellipticity: float = 0.4
    orientation: float = 0.6
    onset: float = 0.3
    theta_deg: float = 50.0
    N0: float = 1.0
    letter_height: float = 4e-3
    slant_deg: float = 75.0
    mu_shift: float = 0.0
    advance: float = 2.2e-3
    mu_skid: Optional[float] = None
    hand: Dict[str, float] = field(default_factory=dict)

    def key(self) -> str:
        return hashlib.sha1(repr(asdict(self)).encode()).hexdigest()[:16]


def draw_spec(seed: int, tremor: bool = True, duration: float = DURATION) -> RandSpec:
    """Domain-randomised scenario specification (training / validation of the learned model)."""
    from stabpen import params as sp
    rng = np.random.default_rng(seed)
    P = sp.load()
    hand = {}
    for k in HAND_KEYS:
        lo, hi = P.rng_range(f"hand.{k}")
        hand[f"hand.{k}"] = float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
    return RandSpec(seed=seed, tremor=tremor, duration=duration,
                    f0=float(rng.uniform(3.0, 14.0)), amp=float(math.exp(rng.uniform(math.log(0.05e-3), math.log(0.6e-3)))),
                    harmonic=float(rng.uniform(0.0, 0.4)), am_depth=float(rng.uniform(0.0, 0.6)),
                    f_jitter=float(rng.uniform(0.0, 1.0)), ellipticity=float(rng.uniform(0.0, 1.0)),
                    orientation=float(rng.uniform(0.0, math.pi)), onset=float(rng.uniform(0.05, 0.6)),
                    theta_deg=float(rng.uniform(35.0, 75.0)), N0=float(math.exp(rng.uniform(math.log(0.5), math.log(2.0)))),
                    letter_height=float(rng.uniform(2.5e-3, 6e-3)), slant_deg=float(rng.uniform(60.0, 90.0)),
                    mu_shift=float(rng.uniform(-0.3, 0.3)), advance=float(rng.uniform(1.6e-3, 2.8e-3)),
                    mu_skid=float(rng.uniform(0.06, 0.2)), hand=hand)


def nominal_spec(seed: int, f0: float, amp: float, duration: float = DURATION) -> RandSpec:
    """Nominal pen and hand (PencilConfig defaults), handwriting from the fast generator."""
    return RandSpec(seed=seed, tremor=amp > 0, duration=duration, f0=f0, amp=amp)


def build(spec: RandSpec):
    """(tremor scenario, clean scenario, PencilConfig) of one spec; both scenarios share the handwriting."""
    rng = np.random.default_rng(spec.seed)
    it = fast_lognormal_handwriting(DT, spec.duration, rng, letter_height=spec.letter_height, slant_deg=spec.slant_deg,
                                    advance=spec.advance, mu_shift=spec.mu_shift)
    if spec.tremor and spec.amp > 0:
        tr = sg.TremorSpec(f0=spec.f0, amp_pk=spec.amp, f_jitter=spec.f_jitter, am_depth=spec.am_depth,
                           harmonic=spec.harmonic, ellipticity=spec.ellipticity, orientation=spec.orientation,
                           onset=spec.onset)
        d = sg.tremor(it.t, tr, np.random.default_rng(spec.seed + 1000))
    else:
        d = np.zeros_like(it.xy)
    sc1 = scenarios._assemble(it, d, spec.N0, spec.theta_deg, meta={"kind": "fusion_random", "spec": asdict(spec)})
    sc0 = scenarios._assemble(it, np.zeros_like(it.xy), spec.N0, spec.theta_deg, meta={"kind": "fusion_random_clean"})
    cfg = M.PencilConfig(mu_skid=spec.mu_skid, overrides=dict(spec.hand))
    return sc1, sc0, cfg


# ------------------------------------------------------------------ cached neutral runs (records only)
def _rec_to_npz(path, rec: S.Record, extra: Dict):
    np.savez_compressed(path, t=rec.t.astype(np.float64), pH=rec.pH.astype(np.float64), aH=rec.aH.astype(np.float32),
                        s=rec.s.astype(np.float64), contact=rec.contact.astype(np.int8),
                        hand_tremor=rec.hand_tremor.astype(np.float32), intended=rec.intended.astype(np.float64),
                        scal=np.array([rec.theta, rec.phi, rec.rho, rec.z0, rec.s_min, rec.n_steps, rec.dt, rec.sdec]),
                        **{k: np.asarray(v) for k, v in extra.items()})


def _npz_to_rec(z) -> S.Record:
    sc = z["scal"]
    return S.Record(t=z["t"], pH=z["pH"], aH=z["aH"].astype(np.float64), s=z["s"], contact=z["contact"].astype(np.float64),
                    hand_tremor=z["hand_tremor"].astype(np.float64), intended=z["intended"], theta=float(sc[0]),
                    phi=float(sc[1]), rho=float(sc[2]), z0=float(sc[3]), s_min=float(sc[4]), n_steps=int(sc[5]),
                    dt=float(sc[6]), sdec=int(sc[7]))


def pair_records(spec: RandSpec, use_cache: bool = True) -> Tuple[S.Record, S.Record]:
    """(tremor record, clean record) of the neutral pen for one spec, cached in fusion/build/cache."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"pair_{spec.key()}.npz")
    if use_cache and os.path.exists(path):
        try:
            with np.load(path) as z:
                r1 = _npz_to_rec({k[2:]: z[k] for k in z.files if k.startswith("1_")})
                r0 = _npz_to_rec({k[2:]: z[k] for k in z.files if k.startswith("0_")})
            return r1, r0
        except Exception:
            pass
    sc1, sc0, cfg = build(spec)
    r1 = S.record_from_result(run(sc1, cfg=cfg, seed=spec.seed), sc1)
    r0 = S.record_from_result(run(sc0, cfg=cfg, seed=spec.seed), sc0)
    if use_cache:
        tmp = path + ".tmp.npz"
        arrs = {}
        for tag, r in (("1_", r1), ("0_", r0)):
            for k, v in (("t", r.t), ("pH", r.pH), ("aH", r.aH.astype(np.float32)), ("s", r.s),
                         ("contact", r.contact.astype(np.int8)), ("hand_tremor", r.hand_tremor.astype(np.float32)),
                         ("intended", r.intended),
                         ("scal", np.array([r.theta, r.phi, r.rho, r.z0, r.s_min, r.n_steps, r.dt, r.sdec]))):
                arrs[tag + k] = v
        np.savez_compressed(tmp, **arrs)
        os.replace(tmp, path)
    return r1, r0


def test_pair_records(seed: int, f0: float, amp: float, duration: float = DURATION, use_cache: bool = True):
    """(tremor record, clean record) of the neutral pen on a harness-convention scenario (cached)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"test_{seed}_{f0:g}_{amp * 1e6:.0f}_{duration:g}.npz")
    if use_cache and os.path.exists(path):
        with np.load(path) as z:
            return (_npz_to_rec({k[2:]: z[k] for k in z.files if k.startswith("1_")}),
                    _npz_to_rec({k[2:]: z[k] for k in z.files if k.startswith("0_")}))
    sc0 = test_scenario(seed, duration=duration)
    sc1 = test_scenario(seed, f0, amp, duration)
    r0 = S.record_from_result(run(sc0, seed=seed), sc0)
    r1 = S.record_from_result(run(sc1, seed=seed), sc1)
    if use_cache:
        arrs = {}
        for tag, r in (("1_", r1), ("0_", r0)):
            for k, v in (("t", r.t), ("pH", r.pH), ("aH", r.aH.astype(np.float32)), ("s", r.s),
                         ("contact", r.contact.astype(np.int8)), ("hand_tremor", r.hand_tremor.astype(np.float32)),
                         ("intended", r.intended),
                         ("scal", np.array([r.theta, r.phi, r.rho, r.z0, r.s_min, r.n_steps, r.dt, r.sdec]))):
                arrs[tag + k] = v
        tmp = path + ".tmp.npz"
        np.savez_compressed(tmp, **arrs)
        os.replace(tmp, path)
    return r1, r0
