"""Pencil-concept piezo stage: hysteresis truth, Prandtl-Ishlinskii identification, inverse feedforward.

Plant per axis (config/pencil.yaml stage.* with its status; everything else ASSUMPTION):
  drive           u in [-30, +30] V about the 30 V midpoint (0-60 V differential, AMF-11),
                  amplifier as a 5 kHz first-order lag (ASSUMPTION, DRV2700-class, AMF-16)
  hysteresis      free bender-tip stroke d = d_p u - h, Bouc-Wen (Low & Guo form)
                  dh = alpha d_p du - beta |du| h - gamma du |h|  (rate independent),
                  tuned to a 12 % major-loop width (ASSUMPTION: PZT benders 10-15 % open loop;
                  AMF-11 gives no figure)
  creep           +1 % of the stroke per decade of time (three first-order lags, ASSUMPTION)
  mechanics       collar mass m (bender tip + refill reflected through the rear gimbal,
                  ASSUMPTION 0.9 g) on the bender stiffness k_b = F_block / free stroke (pencil.yaml),
                  a wire/gimbal flexure k_s (ASSUMPTION 20 N/m) and light damping (zeta 0.05)
  nib             y = lever x (pencil.yaml stage.lever 1.2)
  sensor          Hall on the collar, 1 um RMS nib-referred noise, 100 us delay, 2 kHz
                  (config sensing.hall_*, the Rev A sensing lineage named in pencil.yaml)
Identification model: Prandtl-Ishlinskii (linear gain + n play operators, weights by
non-negative least squares), structurally different from the Bouc-Wen truth.
Inverse: the analytic PI inverse (Kuhnen 2003): w0' = 1/w0,
  w_i' = -w_i / ((w0 + sum_{j<=i} w_j)(w0 + sum_{j<i} w_j)), r_i' = w0 r_i + sum_{j<=i} w_j (r_i - r_j).

Evidence status: SIMULATION (plant and tracking) and CALCULATION (fits, inverse).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
from numba import njit
from scipy.optimize import nnls

from stabpen import params as sp_params

PENCIL = sp_params.load(os.path.join(sp_params.REPO_ROOT, "config", "pencil.yaml"))
BASE = sp_params.load()
DT = 25e-6
U_MAX = 0.5 * float(PENCIL["stage.bender_voltage"])        # +-30 V about the midpoint


@dataclass
class PiezoPlant:
    free_stroke: float = float(PENCIL["stage.bender_free_stroke"])   # m at +-U_MAX (per side)
    block_force: float = float(PENCIL["stage.bender_block_force"])   # N
    lever: float = float(PENCIL["stage.lever"])
    alpha: float = 0.35
    beta: float = 0.020
    gamma: float = 0.005
    creep_gain: float = 0.01          # per decade (three lags 0.05, 0.5, 5 s)
    m: float = 0.9e-3                 # kg at the collar (ASSUMPTION)
    k_s: float = 20.0                 # N/m flexure (ASSUMPTION)
    zeta: float = 0.05                # (ASSUMPTION)
    amp_bw: float = 5000.0            # Hz (ASSUMPTION)
    hall_noise: float = float(BASE["sensing.hall_noise_tip"])
    hall_delay: float = float(BASE["sensing.hall_delay"])
    load_nib: float = 0.0             # N constant transverse load at the nib (writing: see pencil.yaml)

    @property
    def d_p(self):
        return self.free_stroke / U_MAX

    @property
    def k_b(self):
        return self.block_force / self.free_stroke

    def nib_gain(self):
        """Static nominal nib displacement per volt (linear datasheet model)."""
        return self.lever * self.d_p * self.k_b / (self.k_b + self.k_s)


@njit(cache=True)
def _plant(u_cmd, dt, d_p, alpha, beta, gamma, cg, tau_c, k_b, k_s, m, c, lever, amp_a, F_load, out):
    """out: 0 applied voltage, 1 free stroke (hysteretic + creep), 2 collar x, 3 nib y."""
    n = len(u_cmd)
    u = 0.0; h = 0.0; x = 0.0; v = 0.0
    cr = np.zeros(3)
    for k in range(n):
        u_new = u + amp_a * (u_cmd[k] - u)
        du = u_new - u
        h += alpha * d_p * du - beta * abs(du) * h - gamma * du * abs(h)
        u = u_new
        d0 = d_p * u - h
        dcr = 0.0
        for i in range(3):
            cr[i] += dt / tau_c[i] * (d0 - cr[i])
            dcr += cg * cr[i]
        d = d0 + dcr
        a = (k_b * (d - x) - k_s * x - c * v + F_load) / m
        v += a * dt
        x += v * dt
        out[k, 0] = u; out[k, 1] = d; out[k, 2] = x; out[k, 3] = lever * x
    return out


def simulate_open(p: PiezoPlant, u_cmd: np.ndarray):
    out = np.zeros((len(u_cmd), 4))
    c = 2 * p.zeta * math.sqrt((p.k_b + p.k_s) * p.m)
    amp_a = 1 - math.exp(-2 * math.pi * p.amp_bw * DT)
    _plant(np.ascontiguousarray(np.clip(u_cmd, -U_MAX, U_MAX)), DT, p.d_p, p.alpha, p.beta, p.gamma, p.creep_gain,
           np.array([0.05, 0.5, 5.0]), p.k_b, p.k_s, p.m, c, p.lever, amp_a, p.load_nib * p.lever, out)
    return out


# --------------------------------------------------------------------------- Prandtl-Ishlinskii
def play(u, r, y0=0.0):
    """Play (backlash) operator with threshold r on a sampled input."""
    y = np.empty_like(u)
    yp = y0
    for k in range(len(u)):
        yp = max(u[k] - r, min(u[k] + r, yp))
        y[k] = yp
    return y


@njit(cache=True)
def _pi_eval(u, r, w, w0):
    n = len(u)
    m = len(r)
    st = np.zeros(m)
    y = np.empty(n)
    for k in range(n):
        acc = w0 * u[k]
        for i in range(m):
            st[i] = max(u[k] - r[i], min(u[k] + r[i], st[i]))
            acc += w[i] * st[i]
        y[k] = acc
    return y


@dataclass
class PIModel:
    w0: float
    r: np.ndarray
    w: np.ndarray
    offset: float = 0.0
    info: Dict = field(default_factory=dict)

    def __call__(self, u):
        return _pi_eval(np.ascontiguousarray(u, float), self.r, self.w, self.w0) + self.offset

    def inverse(self) -> "PIModel":
        w0, w, r = self.w0, self.w, self.r
        cum = w0 + np.cumsum(w)
        prev = np.concatenate([[w0], cum[:-1]])
        wi = -w / (cum * prev)
        ri = np.array([w0 * r[i] + np.sum(w[:i + 1] * (r[i] - r[:i + 1])) for i in range(len(r))])
        return PIModel(1.0 / w0, ri, wi, 0.0, {"inverse_of": "PI", "offset_in": self.offset})

    def inverse_call(self, y):
        inv = self.inverse()
        return inv(np.asarray(y, float) - self.offset)


def fit_pi(u, y, n_ops=10, u_max=None):
    """Non-negative least squares fit of y = w0 u + sum w_i play_ri(u) + c (thresholds uniform on [0, u_max))."""
    u_max = u_max or float(np.max(np.abs(u)))
    r = np.linspace(0, u_max, n_ops + 1)[1:-1] if n_ops > 1 else np.array([])
    r = np.concatenate([[0.0], r])[1:]                     # thresholds r_1..r_{n-1} (> 0)
    cols = [u] + [play(u, ri) for ri in r]
    A = np.column_stack(cols)
    # offset (free sign) via two non-negative columns
    A2 = np.column_stack([A, np.ones_like(u), -np.ones_like(u)])
    x, res = nnls(A2, y)
    w0, w, c = x[0], x[1:1 + len(r)], x[-2] - x[-1]
    model = PIModel(float(w0), np.asarray(r, float), np.asarray(w, float), float(c))
    yhat = model(u)
    model.info = {"n_ops": n_ops, "resid_rms": float(np.sqrt(np.mean((y - yhat) ** 2))),
                  "stroke": float(np.ptp(y))}
    return model


def fit_linear(u, y):
    A = np.column_stack([u, np.ones_like(u)])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return b


# --------------------------------------------------------------------------- experiments
def decaying_sweep(T=8.0, f0=1.0, f1=8.0, decay=0.35, fs=1.0 / DT):
    """Decaying-amplitude sine with a slowly rising frequency: nested minor loops in one record."""
    t = np.arange(int(T * fs)) / fs
    k = math.log(f1 / f0) / T
    ph = 2 * math.pi * f0 * (np.exp(k * t) - 1) / k
    env = np.exp(-t / (decay * T)) * np.clip(t / 0.1, 0, 1)
    return t, U_MAX * env * np.sin(ph)


def hall(p: PiezoPlant, t, y, rng, fs=2000.0):
    tk = np.arange(0, t[-1] - p.hall_delay, 1 / fs)
    return tk, np.interp(tk - p.hall_delay, t, y) + p.hall_noise * rng.standard_normal(len(tk))


def identify(p: PiezoPlant, rng, n_ops=10, T=8.0):
    t, u = decaying_sweep(T)
    out = simulate_open(p, u)
    tk, yk = hall(p, t, out[:, 3], rng)
    uk = np.interp(tk, t, out[:, 0])          # the driver's monitored output voltage
    model = fit_pi(uk, yk, n_ops)
    lin = fit_linear(uk, yk)
    ylin = lin[0] * uk + lin[1]
    # true major-loop hysteresis width (noise free) at full swing, % of stroke
    return {"model": model, "linear_gain": float(lin[0]),
            "resid_rms_pi_um": model.info["resid_rms"] * 1e6,
            "resid_rms_linear_um": float(np.sqrt(np.mean((yk - ylin) ** 2)) * 1e6),
            "stroke_um": model.info["stroke"] * 1e6, "record_s": T}


def hysteresis_width(p: PiezoPlant, f=1.0, cycles=3):
    t = np.arange(int(cycles / f / DT)) * DT
    u = U_MAX * np.sin(2 * np.pi * f * t)
    y = simulate_open(p, u)[:, 3]
    last = t > (cycles - 1) / f
    uu, yy = u[last], y[last]
    up = np.gradient(uu) > 0
    # width at u = 0 crossing between branches, relative to peak-to-peak
    i_up = np.argmin(np.abs(uu[up]))
    i_dn = np.argmin(np.abs(uu[~up]))
    return float(abs(yy[up][i_up] - yy[~up][i_dn]) / np.ptp(yy))


def resonance_hz(p: PiezoPlant) -> float:
    return math.sqrt((p.k_b + p.k_s) / p.m) / (2 * math.pi)


def track(p: PiezoPlant, ref_t, ref_y, scheme: str, pim: Optional[PIModel], rng, fs=2000.0, lin_gain=None,
          fb_hz=40.0, preview=None, notch_hz=None):
    """Nib tracking of ref_y. scheme: 'linear_ff', 'pi_ff', 'fb', 'linear_ff+fb', 'pi_ff+fb'.

    Feedforward sees the reference `preview` s ahead (the ZOH half-period plus amplifier lag;
    a tremor predictor or a guided-mode template supplies this); 'linear_ff' uses the gain
    identified from the same decaying sweep, 'pi_ff' the analytic PI inverse.
    Feedback: integral + proportional on the Hall error (volt-equivalents), crossover fb_hz,
    with a notch (Q 2, 2 kHz biquad) at the bender resonance identified as in EXP-B05, so the
    lightly damped mode does not set the bandwidth."""
    from scipy.signal import iirnotch
    n = len(ref_t)
    sdec = int(round(1.0 / (fs * DT)))
    g_lin = lin_gain or p.nib_gain()
    Ts = sdec * DT
    ki = 2 * math.pi * fb_hz
    kp = 0.3
    preview = Ts / 2 + 1.0 / (2 * math.pi * p.amp_bw) if preview is None else preview
    tk = ref_t[::sdec]
    rk = ref_y[::sdec]
    rff = np.interp(tk + preview, ref_t, ref_y)
    if scheme.startswith("pi_ff"):
        ffk = pim.inverse_call(rff)
    elif scheme.startswith("linear_ff"):
        ffk = rff / g_lin
    else:
        ffk = np.zeros_like(rk)
    use_fb = scheme.endswith("fb")
    b, a = iirnotch(notch_hz or resonance_hz(p), 2.0, fs=fs)
    z = np.zeros(2)
    u_cmd = np.zeros(n)
    integ = 0.0
    hd = int(round(p.hall_delay / DT))
    c = 2 * p.zeta * math.sqrt((p.k_b + p.k_s) * p.m)
    amp_a = 1 - math.exp(-2 * math.pi * p.amp_bw * DT)
    out = np.zeros((n, 4))
    st = _State()
    for j in range(len(tk)):
        k0 = j * sdec
        k1 = min(n, k0 + sdec)
        fb = 0.0
        if use_fb:
            kh = max(0, k0 - 1 - hd)
            y_meas = (out[kh, 3] if k0 > 0 else 0.0) + p.hall_noise * rng.standard_normal()
            e = (rk[j] - y_meas) / g_lin
            integ += e * Ts
            x = kp * e + ki * integ
            fb = b[0] * x + z[0]                       # notch, direct form II transposed
            z[0] = b[1] * x - a[1] * fb + z[1]
            z[1] = b[2] * x - a[2] * fb
            if abs(ffk[j] + fb) > U_MAX:
                integ -= e * Ts                        # conditional integration (anti-windup)
        u_cmd[k0:k1] = float(np.clip(ffk[j] + fb, -U_MAX, U_MAX))
        _step_chunk(st, u_cmd[k0:k1], p, c, amp_a, out[k0:k1])
    return out, u_cmd


class _State:
    def __init__(self):
        self.x = np.zeros(8)   # u, h, cr0, cr1, cr2, x, v, unused


@njit(cache=True)
def _chunk(s, u_cmd, dt, d_p, alpha, beta, gamma, cg, k_b, k_s, m, c, lever, amp_a, F_load, out):
    u = s[0]; h = s[1]; x = s[5]; v = s[6]
    tau = (0.05, 0.5, 5.0)
    for k in range(len(u_cmd)):
        u_new = u + amp_a * (u_cmd[k] - u)
        du = u_new - u
        h += alpha * d_p * du - beta * abs(du) * h - gamma * du * abs(h)
        u = u_new
        d0 = d_p * u - h
        dcr = 0.0
        for i in range(3):
            s[2 + i] += dt / tau[i] * (d0 - s[2 + i])
            dcr += cg * s[2 + i]
        d = d0 + dcr
        a = (k_b * (d - x) - k_s * x - c * v + F_load) / m
        v += a * dt
        x += v * dt
        out[k, 0] = u; out[k, 1] = d; out[k, 2] = x; out[k, 3] = lever * x
    s[0] = u; s[1] = h; s[5] = x; s[6] = v


def _step_chunk(st, u_cmd, p, c, amp_a, out):
    _chunk(st.x, np.ascontiguousarray(u_cmd), DT, p.d_p, p.alpha, p.beta, p.gamma, p.creep_gain, p.k_b, p.k_s, p.m,
           c, p.lever, amp_a, p.load_nib * p.lever, out)


def tracking_error(ref_t, ref_y, y, t_settle=1.0):
    m = ref_t >= t_settle
    e = y[m] - ref_y[m]
    return float(np.sqrt(np.mean(e ** 2))), float(np.sqrt(np.mean(ref_y[m] ** 2)))
