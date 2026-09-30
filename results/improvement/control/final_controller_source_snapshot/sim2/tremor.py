r"""Tremor generators: physiologically grounded torque (or displacement) sources with frequency and amplitude wander.

Structure of one tremor channel (CALC, parametric; the literature sets the ranges, the shapes are ASSUMPTION):
  f(t)   = f0 + OU(sd = f_jitter, tau = f_tau)                      frequency wander (Hz)
  A(t)   = A0 * max(0, 1 + OU(sd = am_depth, tau = am_tau)) * g(t)  amplitude wander and the rest/action gate g
  phi(t) = 2 pi int f dt
  u(t)   = A(t) [cos(phi + p_i) + h cos(2 phi + p_i + 0.7)] + broadband 3-12 Hz noise (optional)
Channels (wrist flexion-extension, wrist radial-ulnar deviation, forearm pronation-supination, elbow/arm) share the
phase and wander (a common central oscillator, ASSUMPTION) with per-channel amplitude shares and phase offsets.
Profiles:
  ET      kinetic/postural tremor present while writing; f0 4-12 Hz (typically 5-8 Hz; LIT PDT-07, PDT-31: 5.79 +- 1.32
          Hz, falling 0.06-0.08 Hz per year); distribution across DOF largest in forearm pronation-supination and wrist
          flexion-extension, intermediate in radial-ulnar deviation (LIT HAP-33), distal DOF carry 83 % of tremor for
          uniform tremorogenic input at 8 Hz (LIT, Corie & Charles 2019);
  PD_rest rest tremor 4-6 Hz, suppressed during goal-directed movement (LIT PDT-07) and re-emerging after a latency
          (re-emergent tremor latency 9.4 +- 10.7 s in posture, LIT PDT-09): gate g(t) falls to g_move while the pen
          moves and recovers with tau_re after it stops (ASSUMPTION shape);
  PD_action action tremor present while writing at 4-6 Hz (a subset of PD, LIT PDT-08);
  physio  physiological tremor 8-12 Hz, tens of micrometres (LIT PDT-07, PDT-15).
The generator returns torques (N m) per channel; tremor.calibrate() scales them so that the pen-tip displacement has
a target peak amplitude (the arm model's transfer at f0), or the caller sets torque amplitudes directly.
Every output is SIMULATION input, not data.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, Optional, Tuple

import numpy as np

CHANNELS = ("ps", "fe", "rud", "arm")


@dataclass
class TremorProfile:
    kind: str = "ET"
    f0: float = 6.0
    f_jitter: float = 0.3          # Hz rms (stabpen TremorSpec default)
    f_tau: float = 1.5             # s
    am_depth: float = 0.3          # relative rms
    am_tau: float = 0.8            # s
    harmonic: float = 0.15
    onset: float = 0.3
    broadband: float = 0.0         # relative broadband 3-12 Hz component
    share: Dict[str, float] = field(default_factory=lambda: {"ps": 0.45, "fe": 0.40, "rud": 0.25, "arm": 0.10})
    phase: Dict[str, float] = field(default_factory=lambda: {"ps": 0.0, "fe": 0.8, "rud": 1.9, "arm": 0.3})
    # rest/action gate (PD rest tremor)
    gate_move: float = 1.0         # amplitude factor while the pen moves (1: kinetic tremor)
    tau_suppress: float = 0.15     # s
    tau_reemerge: float = 3.0      # s
    v_move: float = 5e-3           # m/s pen speed threshold for "moving"
    amp_tip: float = 1.0e-3        # target pen-tip peak amplitude (m) used by calibrate()


def profile(kind: str, f0: Optional[float] = None, amp_tip: float = 1.0e-3, **kw) -> TremorProfile:
    if kind == "ET":
        p = TremorProfile(kind="ET", f0=f0 or 6.0, amp_tip=amp_tip)
    elif kind == "PD_rest":
        p = TremorProfile(kind="PD_rest", f0=f0 or 5.0, amp_tip=amp_tip, gate_move=0.15, harmonic=0.25,
                          share={"ps": 0.6, "fe": 0.3, "rud": 0.15, "arm": 0.1})
    elif kind == "PD_action":
        p = TremorProfile(kind="PD_action", f0=f0 or 5.0, amp_tip=amp_tip, harmonic=0.25,
                          share={"ps": 0.6, "fe": 0.3, "rud": 0.15, "arm": 0.1})
    elif kind == "physio":
        p = TremorProfile(kind="physio", f0=f0 or 10.0, amp_tip=amp_tip, f_jitter=0.8, am_depth=0.5, am_tau=0.3,
                          broadband=0.5, share={"ps": 0.3, "fe": 0.5, "rud": 0.4, "arm": 0.1})
    else:
        raise ValueError(kind)
    return replace(p, **kw)


def _ou(n, dt, tau, sd, rng):
    x = np.zeros(n)
    a = math.exp(-dt / tau)
    b = sd * math.sqrt(1 - a * a)
    e = rng.standard_normal(n)
    for i in range(1, n):
        x[i] = a * x[i - 1] + b * e[i]
    return x


def oscillator(t: np.ndarray, p: TremorProfile, rng: np.random.Generator):
    """Common phase and amplitude envelope (without the gate)."""
    n = len(t)
    dt = float(t[1] - t[0])
    # generate the slow processes on a coarse grid (1 kHz) and interpolate (fast and statistically identical)
    dc = max(dt, 1e-3)
    tc = np.arange(0.0, t[-1] + dc, dc)
    fc = p.f0 + _ou(len(tc), dc, p.f_tau, p.f_jitter, rng)
    ac = np.clip(1.0 + _ou(len(tc), dc, p.am_tau, p.am_depth, rng), 0.0, None)
    f = np.clip(np.interp(t, tc, fc), 0.5, None)
    amp = np.interp(t, tc, ac) * np.clip(t / max(p.onset, 1e-9), 0.0, 1.0)
    phase = 2 * np.pi * np.cumsum(f) * dt + rng.uniform(0, 2 * np.pi)
    return phase, amp, f


def gate(t: np.ndarray, speed: np.ndarray, p: TremorProfile) -> np.ndarray:
    """Rest/action gate: 1 at rest, gate_move while moving (first-order suppression and re-emergence)."""
    if p.gate_move >= 1.0:
        return np.ones(len(t))
    dt = float(t[1] - t[0])
    g = np.ones(len(t))
    x = 1.0
    for i in range(len(t)):
        tgt = p.gate_move if speed[i] > p.v_move else 1.0
        tau = p.tau_suppress if tgt < x else p.tau_reemerge
        x += (tgt - x) * dt / tau
        g[i] = x
    return g


def torques(t: np.ndarray, p: TremorProfile, A0: Dict[str, float], rng: np.random.Generator,
            speed: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
    """Torque (or force for 'arm') per channel: A0[ch] is the peak torque of the channel at unit envelope."""
    phase, amp, f = oscillator(t, p, rng)
    g = gate(t, speed, p) if speed is not None else np.ones(len(t))
    env = amp * g
    out = {}
    bb = None
    if p.broadband > 0:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [3.0, 12.0], btype="band", fs=1.0 / float(t[1] - t[0]), output="sos")
        bb = sosfiltfilt(sos, rng.standard_normal((len(t), len(CHANNELS))), axis=0)
        bb /= bb.std(axis=0) + 1e-12
    for j, ch in enumerate(CHANNELS):
        a = A0.get(ch, 0.0)
        if a == 0.0:
            out[ch] = np.zeros(len(t))
            continue
        ph = p.phase.get(ch, 0.0)
        u = np.cos(phase + ph) + p.harmonic * np.cos(2 * phase + ph + 0.7)
        if bb is not None:
            u = u + p.broadband * bb[:, j] / math.sqrt(2)
        out[ch] = a * env * u
    out["_f"] = f
    out["_gate"] = g
    return out


CH_JOINT = {"ps": "ps", "fe": "wfe", "rud": "wrud", "arm": "arm_y"}


def ellipse_major(v: np.ndarray) -> float:
    """Peak amplitude (major semi-axis) of the planar motion Re{v e^{j w t}}, v = (X, Y) complex."""
    M = np.array([[v[0].real, -v[0].imag], [v[1].real, -v[1].imag]])
    return float(np.linalg.svd(M, compute_uv=False)[0])


def calibrate(pm, p: TremorProfile, f0: Optional[float] = None) -> Dict:
    """Torque amplitudes A0 per channel (N m; N for 'arm') so that the pen tip, lifted, moves with a peak amplitude
    (major semi-axis in the page plane) of p.amp_tip at f0, with the profile's channel shares and phases (CALC on the
    linearised arm model, hand.torque_frf).  On paper, friction and the writer's feedforward change it a little
    (checked in the time domain by run_study's 'arm' stage)."""
    from . import hand as HD
    f0 = f0 or p.f0
    H = HD.torque_frf(pm, np.array([f0]), joints=tuple(CH_JOINT[c] for c in CHANNELS if p.share.get(c, 0) > 0))
    v = np.zeros(2, complex)
    for c in CHANNELS:
        sh = p.share.get(c, 0.0)
        if sh <= 0:
            continue
        v += sh * np.exp(1j * p.phase.get(c, 0.0)) * H[CH_JOINT[c]][0, :2]
    a1 = ellipse_major(v)
    S = p.amp_tip / max(a1, 1e-30)
    A0 = {c: float(S * p.share.get(c, 0.0)) for c in CHANNELS}
    per = {c: float(abs(np.linalg.norm(H[CH_JOINT[c]][0, :2]))) for c in CHANNELS if p.share.get(c, 0) > 0}
    return {"A0": A0, "f0": f0, "amp_tip": p.amp_tip, "tip_per_unit_m": per, "scale": S}


def describe(p: TremorProfile) -> Dict:
    return asdict(p)
