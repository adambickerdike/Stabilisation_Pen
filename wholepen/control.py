r"""Control laws of the whole-pen devices (PROPOSED DESIGN; run causally at the firmware's 2 kHz tick; SIMULATION).

Common structure: an internal-model phasor law, the one sim2j uses for the end-cap (study K's feed-forward):
  e(t) = d_hat(t) - y_u(t)            the tremor the device has not removed yet (d_hat: the guarded tracker's estimate of
                                      the handle tip's tremor; y_u: what this device's own command did to the handle
                                      tip, from the internal model G(f) at the tracked frequency, as a phasor)
  u(t) = g [Re(H) e(t) - Im(H) e(t - T/4)],  H = -G(f)^-1     (T = 1/f; two-sample phasor realisation)
The internal model G(f) is the device input -> handle-tip response of the reduced linear model (lin.py) at the
nominal grip split r_rot 0.5 (the controller does not know the writer's grip; study K's convention), with the paper's
in-plane drag of a sliding tip.  The command is scaled down as a whole when it exceeds the device's limit (so its
direction is kept), and it is zero while the tracker's tremor detector is closed ('tremor band only': the law acts
only at the tracked tremor frequency, and only while a tremor line is detected).
Devices:
  CMG pairs      u = torque about the output axes; gimbal rate = -u / (2 h cos(delta)) + centring -k_c delta
  CMG turret     one pair whose output axis the turret turns to the major axis of the estimated tremor (principal
                 axis of d_hat over the last 1.5 s; the turret moves at most 1 rad/s); the torque command is the
                 component on that axis
  collar         u = the reference angle of the collar's position servo (pen relative to the collar, about t1 and t2);
                 the servo (stepper) adds the static moment of the writing force about the pivot (N z_p cos theta, from
                 the load cell); the internal model includes the servo, the collar's mass and the grip
  sled / omni    u = force on the hand (sled) or on the pen tip (omni heel) from the paper; capped at mu N
  tuned mass     semi-active: the flexure stiffness is retuned to m (2 pi f_hat)^2 every 0.25 s while a tremor line is
                 detected (3.5-12 Hz), with a 1 s smoothing
  gating         the pen lift raises the ball while |d_hat| (the tremor the nose must cancel) exceeds the nose's reach
                 minus a margin, with 20 ms hysteresis ('write only when in reach')
Oracle variants replace d_hat by the true no-device handle-tip tremor d(t + preview) (the mechanism's limit).
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ROOT  # noqa: F401
from . import lin as L

TWO_PI = 2.0 * math.pi


@dataclass
class WPConfig:
    """Which whole-pen devices run, and their gains (every value PROPOSED DESIGN / ASSUMPTION; tuned on the tuning
    writers and seeds only, frozen before the test: results/wholepen/rules.json)."""
    cmg: str = "off"                     # off | ff (tracker) | afc (adaptive, measured tip motion) | damp (collocated
                                         # rate damping on the IMU gyro, band-limited) | oracle
    cmg_gain: float = 0.75
    cmg_center_hz: float = 0.3           # gimbal centring corner (Hz)
    cmg_frac: float = 0.9                # use at most this share of the gimbal range and torque
    collar: str = "off"                  # off (servo holds the pen centred: the collar locked) | ff | oracle
    collar_gain: float = 0.75
    collar_frac: float = 0.9             # the reference angle uses at most this share of the collar's range
    page_err: str = "measured"           # page sensor: 'measured' (OPT-02 per-window statistics as a random walk,
                                         # study W's model) | 'ideal' (sim2j's 3 um white noise: a labelled bound)
    sled: str = "off"                    # off | ff | oracle | damp (passive viscous)
    sled_gain: float = 0.75
    sled_N: float = 2.0                  # N of hand weight on the sled (ASSUMPTION)
    sled_mu: float = 0.7                 # braked/driven element on paper (ASSUMPTION)
    sled_c: float = 15.0                 # N s/m for 'damp'
    omni: str = "off"                    # off | ff | oracle : an ideal omni heel (force at the tip, any direction)
    omni_gain: float = 0.75
    omni_F: float = 0.37                 # N cap (the lead's heel train: 0.369 N continuous, 0.603 N peak)
    tmd: str = "off"                     # off | passive | semi (retune to f_hat)
    gate: bool = False                   # write only when in reach
    gate_margin: float = 0.3e-3          # m
    gate_hold: float = 0.02              # s minimum time in a state (hysteresis)
    detector_gate: bool = True           # act only while the tracker's tremor detector is open
    afc_tau: float = 0.3                 # s: adaptation time constant of the 'afc' laws
    true_f: bool = False                 # diagnostic: the device laws use the true tremor frequency (not the tracker's)
    cmg_c: float = 0.03                  # N m s/rad: 'damp' law, torque = -c x band-passed pen rotation rate (gyro)
    cmg_band: tuple = (3.0, 12.0)        # Hz band of the 'damp' law (2nd-order Butterworth band-pass, causal)
    model_r_rot: float = 0.5             # the internal model's grip split
    oracle_gain: float = 1.0             # the oracle laws' gain (perfect knowledge of the total tremor)
    preview: float = 0.0                 # s extra preview for the oracle (group delays)
    label: str = ""


# ------------------------------------------------------------------------------------------------ internal models
_GCACHE: Dict = {}


def internal_model(kind: str, pen: Dict, extra: Dict, r_rot: float = 0.5, freqs=None, out: str = "tip") -> Tuple[np.ndarray, np.ndarray]:
    """(freqs, G[f, 2, m]): handle-tip page (x, y) per unit device input (lin.py, CALC).  kind: 'cmg' (torques about
    t1, t2), 'collar' (motor torques about t1, t2), 'sled' (hand force page x, y), 'omni' (tip force x, y)."""
    freqs = np.arange(2.0, 16.01, 0.25) if freqs is None else np.asarray(freqs, float)
    key = (kind, tuple(sorted((k, str(v)) for k, v in pen.items())), tuple(sorted((k, str(v)) for k, v in extra.items())),
           r_rot, len(freqs), out)
    if key in _GCACHE:
        return _GCACHE[key]
    import torch
    mdl = L.Model(hand=L.HandP(r_rot=r_rot), pen=dict(pen), c_paper=3.0)
    if extra.get("tail_m", 0.0) > 0:
        mdl.tail = L.Tail(m=extra["tail_m"], z=extra.get("tail_z", 0.17), J_t=extra.get("tail_J", 0.0))
    if kind == "collar":
        # the collar's position servo: the flexure plus the servo's stiffness and damping between pen and collar; the
        # input is the servo's reference angle (the generalised force K_s x theta_ref)
        K_s = extra.get("K_s", 0.0)
        mdl.collar = L.Collar(z_p=extra["z_p"], K_c=extra["K_c"] + K_s, c_c=extra.get("c_c", 2e-3) + extra.get("C_s", 0.0),
                              m=extra.get("m_c", 14e-3), z_cm=extra.get("z_cm", extra["z_p"]), J=extra.get("J_c", 8e-6),
                              skid_on_collar=bool(extra.get("skid_on_collar", False)))
        if extra.get("skid_on_collar", False):
            mdl.c_paper = 1.0            # the ball's drag only (the skid's drag is on the collar)
    asm = L.Assembly(mdl)
    G = np.zeros((len(freqs), 2, 2), complex)
    for i, f in enumerate(freqs):
        w = TWO_PI * f
        for j in range(2):
            if kind == "cmg":
                u = asm.u_torque_pen(asm.t1 if j == 0 else asm.t2)
            elif kind == "collar":
                ks = extra.get("K_s", 0.0)
                u = asm.u_collar(asm.t1 if j == 0 else asm.t2) * (ks if ks > 0 else 1.0)
            elif kind == "sled":
                u = asm.u_force_hand(np.eye(3)[j])
            elif kind == "omni":
                u = asm.u_force_pen(0.0, np.eye(3)[j])
            else:
                raise KeyError(kind)
            X = asm.solve(w, u)
            G[i, :, j] = (asm.ink(X) if out == "ink" else asm.tip(X)).detach().numpy()
    _GCACHE[key] = (freqs, G)
    return freqs, G


class PhasorIMC:
    """The internal-model phasor law (module doc) for one device with m = 2 inputs.  G predicts what the device does to
    the measured point (the page sensor's handle tip); G_inv (default G) is the response of the point to be held still
    (the ink: they differ for the V2 collar).  total=True: the input is already the total tremor (the oracle's
    no-device record), so the device's own effect is not subtracted."""

    def __init__(self, freqs, G, gain: float, Ts: float = 0.5e-3, G_inv=None, total: bool = False):
        self.f = freqs
        self.G = G
        self.H = np.array([-np.linalg.pinv(g) for g in (G if G_inv is None else G_inv)])
        self.total = total
        self.gain = gain
        self.Ts = Ts
        self.uh = deque(maxlen=400)
        self.eh = deque(maxlen=400)
        self.u = np.zeros(2)

    def _interp(self, M, fq):
        re = np.array([[np.interp(fq, self.f, M[:, i, j].real) for j in range(2)] for i in range(2)])
        im = np.array([[np.interp(fq, self.f, M[:, i, j].imag) for j in range(2)] for i in range(2)])
        return re, im

    def step(self, dh: np.ndarray, f_est: float, active: bool) -> np.ndarray:
        fq = float(np.clip(f_est, self.f[0], self.f[-1]))
        kq = max(1, int(round(1.0 / (4.0 * fq * self.Ts))))
        Gr, Gi = self._interp(self.G, fq)
        Hr, Hi = self._interp(self.H, fq)
        u_q = self.uh[-kq] if len(self.uh) >= kq else np.zeros(2)
        y_u = Gr @ self.u - Gi @ u_q
        e = dh if self.total else dh - y_u
        self.eh.append(e.copy())
        e_q = self.eh[-kq] if len(self.eh) > kq else np.zeros(2)
        u = self.gain * (Hr @ e - Hi @ e_q) if active else np.zeros(2)
        return u

    def commit(self, u: np.ndarray):
        self.u = np.asarray(u, float).copy()
        self.uh.append(self.u.copy())


def cap_vec(u: np.ndarray, cap: float) -> np.ndarray:
    mag = float(np.max(np.abs(u)))
    return u * (cap / mag) if mag > cap > 0 else u


def principal_axis(buf: deque) -> float:
    """Angle (page frame) of the major axis of the recent d_hat samples."""
    if len(buf) < 20:
        return 0.0
    X = np.array(buf)
    C = X.T @ X
    w, V = np.linalg.eigh(C)
    v = V[:, -1]
    return math.atan2(v[1], v[0])


class AFC:
    """Adaptive feed-forward cancellation at the tracked tremor frequency (a closed loop on the MEASURED handle-tip
    motion: the page sensor while the pen is on the paper).  u(t) = Re{U e^{j phi}}, phi = 2 pi int f_est dt; the
    measured motion y is high-passed at 2 Hz and demodulated, and U takes a model-inverse (Newton) step toward
    cancelling its component at f_est: U <- U - a G(f)^-1 2 y e^{-j phi}, a = Ts / tau.  Writing content that is not
    at the tremor frequency averages out of the update; the law acts only while the detector sees a tremor line
    (PROPOSED DESIGN; the adaptive feed-forward canceller of the tremor literature, with the device's internal model)."""

    def __init__(self, freqs, G, tau: float = 0.3, Ts: float = 0.5e-3, hp_hz: float = 2.0, decay_tau: float = 0.3):
        from scipy.signal import butter
        self.f = freqs
        self.G = G
        self.Ginv = np.array([np.linalg.pinv(g) for g in G])
        self.a = Ts / tau
        self.Ts = Ts
        self.U = np.zeros(2, complex)
        self.phi = 0.0
        self.decay = math.exp(-Ts / decay_tau)
        self.sos = butter(2, hp_hz, btype="high", fs=1.0 / Ts, output="sos")
        self.zi = np.zeros((self.sos.shape[0], 2, 2))
        self.y_prev = None
        self.u = np.zeros(2)

    def _hp(self, y):
        from scipy.signal import sosfilt
        out, self.zi = sosfilt(self.sos, y[None, :], axis=0, zi=self.zi)
        return out[0]

    def _ginv(self, fq):
        re = np.array([[np.interp(fq, self.f, self.Ginv[:, i, j].real) for j in range(2)] for i in range(2)])
        im = np.array([[np.interp(fq, self.f, self.Ginv[:, i, j].imag) for j in range(2)] for i in range(2)])
        return re + 1j * im

    def step(self, y: np.ndarray, valid: bool, f_est: float, active: bool, cap: float) -> np.ndarray:
        fq = float(np.clip(f_est, self.f[0], self.f[-1]))
        self.phi = (self.phi + TWO_PI * fq * self.Ts) % TWO_PI
        e = np.exp(-1j * self.phi)
        if valid and y is not None:
            yh = self._hp(np.asarray(y, float))
        else:
            yh = None
        if active and yh is not None:
            self.U = self.U - self.a * (self._ginv(fq) @ (2.0 * yh * e))
        else:
            self.U = self.U * self.decay
        mag = np.abs(self.U)
        if cap > 0 and float(np.max(mag)) > cap:
            self.U = self.U * (cap / float(np.max(mag)))
        self.u = np.real(self.U * np.exp(1j * self.phi))
        return self.u


class BandPass2:
    """Causal 2nd-order Butterworth band-pass on a 2-vector at the tick rate."""

    def __init__(self, lo: float, hi: float, Ts: float = 0.5e-3):
        from scipy.signal import butter
        self.sos = butter(1, [lo, hi], btype="band", fs=1.0 / Ts, output="sos")
        self.zi = np.zeros((self.sos.shape[0], 2, 2))

    def step(self, x):
        from scipy.signal import sosfilt
        y, self.zi = sosfilt(self.sos, np.asarray(x, float)[None, :], axis=0, zi=self.zi)
        return y[0]
