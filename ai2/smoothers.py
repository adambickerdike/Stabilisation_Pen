r"""Fixed-lag estimators for delayed ink (task 1) and the handle predictor they need.

Evidence status: SIMULATION tooling (every number they produce is a SIMULATION on HW1 sensor streams).

Delayed ink.  The ink point is p_H + q (handle plus nose deflection).  If the ink may trail the hand by a lag
lambda, the nose command at tick t (acting at t + delta, the servo's group delay) is

    q(t) = s_hat(t) - p_hat_H(t + delta),    s_hat(t) = p_hat_H(s | Y_t) - g(t) d_hat(s | Y_t),   s = t + delta - lambda

* p_hat_H(t + delta): the handle position predicted over the sensor and servo delays (causal, ~5-6 ms);
* p_hat_H(s | Y_t), d_hat(s | Y_t): the handle position and the tremor at the earlier time s, SMOOTHED with every
  sample acquired up to t - 2 ms (look-ahead lambda - delta - 2 ms);
* g(t): the output gain times a soft amplitude gate on the smoothed tremor amplitude (no tremor: g = 0, so tremor-free
  writing is only delayed, never reshaped).

Estimators (all causal with respect to the output time t):
  rts      fixed-lag Rauch-Tung-Striebel smoother on the AKF's own model (fusion/estimators.py): per axis
           [p, v, a (white jerk), c1, s1 (tremor oscillator at w), c2, s2 (2nd harmonic), b (accelerometer bias)];
           measurements: the accelerometer (block-averaged pairs, 1.92 kHz, stamped at acquisition minus the 1.04 ms
           filter delay) and the page sensor (1 kHz, 3 um) at their acquisition times; the frequency is tracked from
           the fundamental's phase rate as in the AKF; after a page-sensor gap (pen lifted) the position variance is
           inflated (a process-noise impulse, so the backward pass stays consistent).  For each output tick a backward
           pass from the newest usable sample gives the smoothed state at every requested lag (mean only).
  window   windowed zero-phase smoother: at each output tick, the last W seconds of the page-sensor track are
           cleaned by the app's non-causal Wiener smoother (aiprior.cleancopy, tremor line from the window's own
           spectrum) and read at the lag (the 'clean copy' run on a sliding window).
  learned  (learned.py) a window network trained on domain-randomised writers.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from numba import njit

from . import ensure_paths

ensure_paths()
from fusion.sensors import Streams  # noqa: E402

NS = 8
TWO_PI = 2.0 * math.pi

RTS_KEYS = ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz", "harm", "acc_gd",
            "gap_reset", "gap_sd", "use_acc", "use_pos", "avail", "tau_amp")
RTS_DEFAULTS = {"qj": 0.0275, "qt": 1e-8, "qh": 3.5e-9, "qb": 2e-6, "ra": 0.075, "rp": 1.2e-9, "tau_decay": 0.3,
                "w0_hz": 6.26, "tau_w": 0.124, "wmin_hz": 3.58, "wmax_hz": 14.7, "harm": 0.88, "acc_gd": 1.04e-3,
                "gap_reset": 0.03, "gap_sd": 0.5e-3, "use_acc": 1.0, "use_pos": 1.0, "avail": 2.0e-3, "tau_amp": 0.3,
                "acc_block": 2}


def _prm(d: Dict, keys, defaults) -> np.ndarray:
    return np.array([float(d.get(k, defaults[k])) for k in keys])


# ======================================================================================== model
@njit(cache=True)
def _FQ(dt, w, tau_d, qj, qt, qh, qb, F, Q):
    for i in range(NS):
        for j in range(NS):
            F[i, j] = 0.0
            Q[i, j] = 0.0
    F[0, 0] = 1.0; F[0, 1] = dt; F[0, 2] = 0.5 * dt * dt
    F[1, 1] = 1.0; F[1, 2] = dt
    F[2, 2] = 1.0
    rd = math.exp(-dt / tau_d)
    c = math.cos(w * dt); s = math.sin(w * dt)
    F[3, 3] = rd * c; F[3, 4] = rd * s; F[4, 3] = -rd * s; F[4, 4] = rd * c
    c2 = math.cos(2 * w * dt); s2 = math.sin(2 * w * dt)
    F[5, 5] = rd * c2; F[5, 6] = rd * s2; F[6, 5] = -rd * s2; F[6, 6] = rd * c2
    F[7, 7] = 1.0
    T2 = dt * dt; T3 = T2 * dt; T4 = T3 * dt; T5 = T4 * dt
    Q[0, 0] = qj * T5 / 20.0; Q[0, 1] = qj * T4 / 8.0; Q[0, 2] = qj * T3 / 6.0
    Q[1, 0] = Q[0, 1]; Q[1, 1] = qj * T3 / 3.0; Q[1, 2] = qj * T2 / 2.0
    Q[2, 0] = Q[0, 2]; Q[2, 1] = Q[1, 2]; Q[2, 2] = qj * dt
    Q[3, 3] = qt * dt; Q[4, 4] = qt * dt
    Q[5, 5] = qh * dt; Q[6, 6] = qh * dt
    Q[7, 7] = qb * dt


@njit(cache=True)
def _matmul(A, B, C):
    n = A.shape[0]; m = B.shape[1]; k = A.shape[1]
    for i in range(n):
        for j in range(m):
            s = 0.0
            for q in range(k):
                s += A[i, q] * B[q, j]
            C[i, j] = s


@njit(cache=True)
def _inv_spd(P, out):
    """Inverse of a symmetric positive (semi-)definite matrix with diagonal scaling (states span 1e-6..1 in SI)."""
    n = P.shape[0]
    d = np.empty(n)
    for i in range(n):
        d[i] = math.sqrt(max(P[i, i], 1e-300))
    Pn = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            Pn[i, j] = P[i, j] / (d[i] * d[j])
    for i in range(n):
        Pn[i, i] += 1e-12
    Ai = np.linalg.inv(Pn)
    for i in range(n):
        for j in range(n):
            out[i, j] = Ai[i, j] / (d[i] * d[j])


@njit(cache=True)
def _forward(ev_t, ev_k, ev_y, prm, xf, xpr, Cg, ev_w, ev_amp):
    """Forward Kalman filter over the merged events (acquisition-time order).  Stores the filtered state xf, the
    predicted state xpr (before the event's update), the RTS gain Cg[k] = Pf[k] F[k+1]^T inv(Ppred[k+1]) and the
    tracked frequency per event."""
    qj = prm[0]; qt = prm[1]; qh = prm[2] * prm[11]; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    w = TWO_PI * prm[7]; tau_w = prm[8]; wmin = TWO_PI * prm[9]; wmax = TWO_PI * prm[10]; harm = prm[11]
    gap_reset = prm[13]; gap_sd = prm[14]; use_acc = prm[15] > 0.5; use_pos = prm[16] > 0.5; tau_amp = prm[18]
    n = ev_t.shape[0]
    x = np.zeros((2, NS)); P = np.zeros((NS, NS))
    F = np.zeros((NS, NS)); Q = np.zeros((NS, NS))
    FP = np.zeros((NS, NS)); Pp = np.zeros((NS, NS)); Pinv = np.zeros((NS, NS)); PfFt = np.zeros((NS, NS))
    Pf_prev = np.zeros((NS, NS))
    H = np.zeros(NS); PH = np.zeros(NS)
    # initial state: position from the first page sample
    for k in range(n):
        if ev_k[k] == 1:
            x[0, 0] = ev_y[k, 0]; x[1, 0] = ev_y[k, 1]
            break
    P[0, 0] = 1e-6; P[1, 1] = 1e-4; P[2, 2] = 1.0; P[3, 3] = 1e-7; P[4, 4] = 1e-7
    P[5, 5] = 1e-8; P[6, 6] = 1e-8; P[7, 7] = 0.05
    tf = ev_t[0]
    last_pos = -1.0
    phase_prev = 0.0; have_phase = False; tf_prev = tf; ax_prev = 0
    amp_f = 0.0
    for k in range(n):
        dt = ev_t[k] - tf
        # ---- predict
        if k > 0:
            _FQ(max(dt, 0.0), w, tau_d, qj, qt, qh, qb, F, Q)
            for a in range(2):
                for i in range(NS):
                    s = 0.0
                    for j in range(NS):
                        s += F[i, j] * x[a, j]
                    PH[i] = s
                for i in range(NS):
                    x[a, i] = PH[i]
            _matmul(F, P, FP)
            for i in range(NS):
                for j in range(NS):
                    s = 0.0
                    for q in range(NS):
                        s += FP[i, q] * F[j, q]
                    Pp[i, j] = s + Q[i, j]
            # page sample after a gap (pen lifted, page sensor invalid): process-noise impulse on position/velocity
            if ev_k[k] == 1 and use_pos and last_pos >= 0.0 and ev_t[k] - last_pos > gap_reset:
                Pp[0, 0] += gap_sd * gap_sd
                Pp[1, 1] += (gap_sd / 0.05) ** 2
            # RTS gain of the previous event: C = Pf_prev F^T inv(Pp)
            _inv_spd(Pp, Pinv)
            for i in range(NS):
                for j in range(NS):
                    s = 0.0
                    for q in range(NS):
                        s += Pf_prev[i, q] * F[j, q]
                    PfFt[i, j] = s
            for i in range(NS):
                for j in range(NS):
                    s = 0.0
                    for q in range(NS):
                        s += PfFt[i, q] * Pinv[q, j]
                    Cg[k - 1, i, j] = s
            for i in range(NS):
                for j in range(NS):
                    P[i, j] = Pp[i, j]
            tf = ev_t[k]
        for a in range(2):
            for i in range(NS):
                xpr[k, a, i] = x[a, i]
        # ---- update
        do = False
        r = 0.0
        for i in range(NS):
            H[i] = 0.0
        if ev_k[k] == 0 and use_acc:
            H[2] = 1.0; H[3] = -w * w; H[5] = -4.0 * w * w * harm; H[7] = 1.0
            r = ra; do = True
        elif ev_k[k] == 1 and use_pos:
            H[0] = 1.0; H[3] = 1.0; H[5] = harm
            r = rp; do = True
            last_pos = ev_t[k]
        if do:
            for i in range(NS):
                s = 0.0
                for j in range(NS):
                    s += P[i, j] * H[j]
                PH[i] = s
            S = r
            for i in range(NS):
                S += H[i] * PH[i]
            e0 = ev_y[k, 0]; e1 = ev_y[k, 1]
            for i in range(NS):
                e0 -= H[i] * x[0, i]
                e1 -= H[i] * x[1, i]
            for i in range(NS):
                K = PH[i] / S
                x[0, i] += K * e0
                x[1, i] += K * e1
            for i in range(NS):
                for j in range(NS):
                    P[i, j] -= PH[i] * PH[j] / S
        for a in range(2):
            for i in range(NS):
                xf[k, a, i] = x[a, i]
        for i in range(NS):
            for j in range(NS):
                Pf_prev[i, j] = P[i, j]
        # ---- frequency tracking (fundamental's phase rate, as the AKF)
        amp0 = math.hypot(x[0, 3], x[0, 4]); amp1 = math.hypot(x[1, 3], x[1, 4])
        axm = 0 if amp0 >= amp1 else 1
        ampm = max(amp0, amp1)
        phs = math.atan2(x[axm, 4], x[axm, 3])
        if have_phase and ampm > 2e-6 and tf > tf_prev + 1e-9 and axm == ax_prev:
            dph = phs - phase_prev
            while dph > math.pi:
                dph -= 2 * math.pi
            while dph < -math.pi:
                dph += 2 * math.pi
            dtp_ = tf - tf_prev
            wm = -dph / dtp_
            a_w = min(1.0, dtp_ / tau_w)
            w = w + a_w * (wm - w)
            w = min(max(w, wmin), wmax)
        if tf > tf_prev + 1e-9 or not have_phase:
            if have_phase:
                amp_f = amp_f + min(1.0, (tf - tf_prev) / tau_amp) * (math.sqrt(amp0 * amp0 + amp1 * amp1) - amp_f)
            phase_prev = phs
            tf_prev = tf
            ax_prev = axm
            have_phase = True
        ev_w[k] = w
        ev_amp[k] = amp_f


@njit(cache=True)
def _state_at(xs, t_from, t_to, w, tau_d, harm, out3):
    """Handle position, tremor and intent position of a (2, NS) state propagated from t_from to t_to (model mean)."""
    dt = t_to - t_from
    rd = math.exp(-abs(dt) / tau_d) if dt > 0 else 1.0
    c = math.cos(w * dt); s = math.sin(w * dt)
    c2 = math.cos(2 * w * dt); s2 = math.sin(2 * w * dt)
    for a in range(2):
        p = xs[a, 0] + xs[a, 1] * dt + 0.5 * xs[a, 2] * dt * dt
        d = rd * (c * xs[a, 3] + s * xs[a, 4] + harm * (c2 * xs[a, 5] + s2 * xs[a, 6]))
        out3[0, a] = p + d          # handle
        out3[1, a] = d              # tremor
        out3[2, a] = p              # intent


@njit(cache=True)
def _fixed_lag(out_t, ev_t, xf, xpr, Cg, ev_w, ev_amp, lags, delta, avail, tau_d, harm, H_out, D_out, A_out, P_now):
    """For each output time t: the handle and tremor smoothed at s = t + delta - lag (all lags), from the samples
    acquired up to t - avail; and the handle predicted to t + delta.  Mean-only backward (RTS) pass."""
    n_out = out_t.shape[0]
    nl = lags.shape[0]
    lmax = 0.0
    for i in range(nl):
        lmax = max(lmax, lags[i])
    xs = np.zeros((2, NS)); tmp = np.zeros((2, NS)); o3 = np.zeros((3, 2))
    e = -1
    ne = ev_t.shape[0]
    for m in range(n_out):
        t = out_t[m]
        while e + 1 < ne and ev_t[e + 1] <= t - avail:
            e += 1
        if e < 0:
            for i in range(nl):
                H_out[m, i, 0] = np.nan; H_out[m, i, 1] = np.nan
                D_out[m, i, 0] = 0.0; D_out[m, i, 1] = 0.0
                A_out[m, i] = 0.0
            P_now[m, 0] = np.nan; P_now[m, 1] = np.nan
            continue
        # real-time handle prediction (forward filter)
        _state_at(xf[e], ev_t[e], t + delta, ev_w[e], tau_d, harm, o3)
        P_now[m, 0] = o3[0, 0]; P_now[m, 1] = o3[0, 1]
        # backward pass
        for a in range(2):
            for j in range(NS):
                xs[a, j] = xf[e, a, j]
        k = e
        filled = np.zeros(nl, np.bool_)
        # lags whose target time is after the newest sample: forward prediction
        for i in range(nl):
            s_t = t + delta - lags[i]
            if s_t >= ev_t[e]:
                _state_at(xf[e], ev_t[e], s_t, ev_w[e], tau_d, harm, o3)
                H_out[m, i, 0] = o3[0, 0]; H_out[m, i, 1] = o3[0, 1]
                D_out[m, i, 0] = o3[1, 0]; D_out[m, i, 1] = o3[1, 1]
                A_out[m, i] = ev_amp[e]
                filled[i] = True
        t_stop = t + delta - lmax
        while k > 0 and ev_t[k] > t_stop:
            # xs(k-1) = xf(k-1) + C(k-1) (xs(k) - xpr(k))
            for a in range(2):
                for i in range(NS):
                    s = 0.0
                    for j in range(NS):
                        s += Cg[k - 1, i, j] * (xs[a, j] - xpr[k, a, j])
                    tmp[a, i] = xf[k - 1, a, i] + s
            for a in range(2):
                for i in range(NS):
                    xs[a, i] = tmp[a, i]
            k -= 1
            for i in range(nl):
                if not filled[i]:
                    s_t = t + delta - lags[i]
                    if ev_t[k] <= s_t:
                        _state_at(xs, ev_t[k], s_t, ev_w[k], tau_d, harm, o3)
                        H_out[m, i, 0] = o3[0, 0]; H_out[m, i, 1] = o3[0, 1]
                        D_out[m, i, 0] = o3[1, 0]; D_out[m, i, 1] = o3[1, 1]
                        A_out[m, i] = ev_amp[k]
                        filled[i] = True
        for i in range(nl):
            if not filled[i]:
                _state_at(xs, ev_t[k], t + delta - lags[i], ev_w[k], tau_d, harm, o3)
                H_out[m, i, 0] = o3[0, 0]; H_out[m, i, 1] = o3[0, 1]
                D_out[m, i, 0] = o3[1, 0]; D_out[m, i, 1] = o3[1, 1]
                A_out[m, i] = ev_amp[k]


def _block_average(t_acq, t_av, y, m):
    if m <= 1:
        return t_acq, t_av, y
    n = (len(t_acq) // m) * m
    return (t_acq[:n].reshape(-1, m).mean(axis=1), t_av[:n].reshape(-1, m).max(axis=1),
            y[:n].reshape(-1, m, y.shape[1]).mean(axis=1))


def events(st: Streams, acc_gd: float = 1.04e-3, acc_decim: int = 2, use_acc: bool = True, use_pos: bool = True):
    """Merged accelerometer and valid page-sensor samples in acquisition-time order: (t, kind 0/1, y (n, 2))."""
    ta, _, ya = _block_average(st.acc_t, st.acc_av, st.acc, acc_decim)
    ta = ta - acc_gd
    ok = st.pos_ok > 0.5
    tp, yp = st.pos_t[ok], st.pos[ok]
    parts_t, parts_k, parts_y = [], [], []
    if use_acc:
        parts_t.append(ta); parts_k.append(np.zeros(len(ta), np.int64)); parts_y.append(ya)
    if use_pos:
        parts_t.append(tp); parts_k.append(np.ones(len(tp), np.int64)); parts_y.append(yp)
    t = np.concatenate(parts_t); k = np.concatenate(parts_k); y = np.concatenate(parts_y)
    o = np.argsort(t, kind="stable")
    return np.ascontiguousarray(t[o]), np.ascontiguousarray(k[o]), np.ascontiguousarray(y[o])


def rts_fixed_lag(st: Streams, params: Optional[Dict], lags: Sequence[float], delta: float, out_every: int = 2):
    """Fixed-lag RTS smoother.  Returns a dict with, per output time (every `out_every` ticks):
    't' (s), 'handle' (n, L, 2) and 'tremor' (n, L, 2) smoothed at s = t + delta - lag, 'amp' (n, L) the tracked tremor
    amplitude at s, 'p_now' (n, 2) the handle predicted to t + delta, and the tracked frequency per event."""
    p = dict(RTS_DEFAULTS)
    if params:
        p.update({k: v for k, v in params.items() if k in RTS_DEFAULTS})
    ev_t, ev_k, ev_y = events(st, p["acc_gd"], int(p["acc_block"]), p["use_acc"] > 0.5, p["use_pos"] > 0.5)
    n = len(ev_t)
    xf = np.zeros((n, 2, NS)); xpr = np.zeros((n, 2, NS)); Cg = np.zeros((max(n - 1, 1), NS, NS))
    ev_w = np.zeros(n); ev_amp = np.zeros(n)
    prm = _prm(p, RTS_KEYS, RTS_DEFAULTS)
    _forward(ev_t, ev_k, ev_y, prm, xf, xpr, Cg, ev_w, ev_amp)
    out_t = np.ascontiguousarray(st.tick_t[::out_every])
    L = np.ascontiguousarray(np.asarray(lags, float))
    H = np.zeros((len(out_t), len(L), 2)); D = np.zeros((len(out_t), len(L), 2)); A = np.zeros((len(out_t), len(L)))
    Pn = np.zeros((len(out_t), 2))
    _fixed_lag(out_t, ev_t, xf, xpr, Cg, ev_w, ev_amp, L, float(delta), float(p["avail"]), float(p["tau_decay"]),
               float(p["harm"]), H, D, A, Pn)
    return {"t": out_t, "handle": H, "tremor": D, "amp": A, "p_now": Pn, "lags": L, "delta": float(delta),
            "f_ev": ev_w / TWO_PI, "t_ev": ev_t, "params": p}


# ======================================================================================== windowed zero-phase
def _ar_forecast(x: np.ndarray, n_ahead: int, order: int = 24) -> np.ndarray:
    """Least-squares AR(order) fit of each column of x and an n_ahead-sample forecast (edge extension); the forecast
    is the AR recursion's zero-input response from the last `order` samples (scipy lfilter)."""
    from scipy.signal import lfilter, lfiltic
    out = np.zeros((n_ahead, x.shape[1]))
    for j in range(x.shape[1]):
        v = x[:, j]
        if len(v) < 4 * order:
            out[:, j] = v[-1]
            continue
        X = np.column_stack([v[order - k - 1:len(v) - k - 1] for k in range(order)])
        a, *_ = np.linalg.lstsq(X, v[order:], rcond=None)
        den = np.r_[1.0, -a]
        zi = lfiltic([1.0], den, y=v[::-1][:order])
        out[:, j], _ = lfilter([1.0], den, np.zeros(n_ahead), zi=zi)
    return out


def window_smoother(st: Streams, det: Dict, lags: Sequence[float], delta: float, window: float = 2.0,
                    out_every: int = 4, beta: float = 2.0, margin: float = 2.0, half_width: float = 2.0,
                    ar_pad: bool = True) -> Dict:
    """The app's zero-phase Wiener smoother (aiprior.cleancopy.wiener_clean) run on a sliding window of the page-sensor
    track that ends at the newest usable sample (t - 2 ms), read at s = t + delta - lag.  The spectra (writing floor
    and tremor excess) are the running detector's (`detector`), so each window is filtered by
    H = S_w / (S_w + beta S_d) near f_hat and 2 f_hat, zero phase, after removing the < 1.5 Hz part.  The window's
    right edge (the future the filter cannot see) is extended by an AR(24) forecast of the fast part (ar_pad) or by
    reflection.  Returns the tremor estimate (what H removes)."""
    from scipy.signal import butter, sosfiltfilt
    fs = float(det["params"]["fs"])
    tg, yg, lat = _page_grid(st, fs)
    out_t = st.tick_t[::out_every]
    L = np.asarray(lags, float)
    D = np.zeros((len(out_t), len(L), 2))
    nw = int(round(window * fs))
    pad = int(round(1.0 * fs))
    N = nw + 2 * pad
    fgrid = np.fft.rfftfreq(N, 1.0 / fs)
    sos = butter(4, 1.5, fs=fs, output="sos")
    f = det["spec_f"]
    t_des = det["t"]
    Hcache = {}
    for m, t in enumerate(out_t):
        kd = int(np.searchsorted(t_des, t, side="right")) - 1
        if kd < 0 or det["gate"][kd] <= 0.0 or det["spec_P"][kd] is None:
            continue
        j1 = int(np.searchsorted(tg, t - lat, side="right"))
        if j1 < nw:
            continue
        if kd not in Hcache:
            P = det["spec_P"][kd]; fl = det["spec_floor"][kd]; fh = det["f_hat"][kd]
            exc = np.maximum(P - margin * fl, 0.0)
            inb = (np.abs(f - fh) <= half_width) | (np.abs(f - 2 * fh) <= half_width)
            Sd = np.where(inb, exc, 0.0)
            Sw = np.interp(fgrid, f, fl); Sdg = np.interp(fgrid, f, Sd)
            Hcache[kd] = Sw / np.maximum(Sw + beta * Sdg, 1e-300)
        H = Hcache[kd]
        seg_t = tg[j1 - nw:j1]; seg = yg[j1 - nw:j1]
        slow = sosfiltfilt(sos, seg, axis=0, padtype="odd", padlen=min(nw - 1, 3 * pad))
        fast = seg - slow
        fp = np.pad(fast, ((pad, pad), (0, 0)), mode="reflect")
        if ar_pad:                      # extend the right edge by an AR forecast instead of a mirror image
            fp[pad + nw:] = _ar_forecast(fast, pad)
        y = np.fft.irfft(np.fft.rfft(fp, axis=0) * H[:, None], n=N, axis=0)[pad:pad + nw]
        trem = fast - y
        for i, lag in enumerate(L):
            s_ = t + delta - lag
            D[m, i, 0] = np.interp(s_, seg_t, trem[:, 0]); D[m, i, 1] = np.interp(s_, seg_t, trem[:, 1])
    return {"t": out_t, "tremor": D, "lags": L, "delta": float(delta)}


# ======================================================================================== running tremor-line detector
def _page_grid(st: Streams, fs: float):
    """The valid page-sensor samples on a uniform grid (gaps bridged linearly), with each grid sample's availability
    time (acquisition + latency)."""
    ok = st.pos_ok > 0.5
    tp, yp = st.pos_t[ok], st.pos[ok]
    tg = np.arange(tp[0], tp[-1], 1.0 / fs)
    yg = np.column_stack([np.interp(tg, tp, yp[:, 0]), np.interp(tg, tp, yp[:, 1])])
    lat = float(st.pos_av[0] - st.pos_t[0])
    return tg, yg, lat


def _floor(f, P, half_window_hz=3.0):
    from scipy.ndimage import median_filter
    df = float(f[1] - f[0])
    k = max(3, 2 * int(round(half_window_hz / df)) + 1)
    return np.exp(median_filter(np.log(np.maximum(P, 1e-300)), size=k, mode="nearest"))


DET_DEFAULTS = {"win": 4.0, "seg": 2.0, "fs": 250.0, "band_lo": 4.5, "band_hi": 13.5, "hp_hz": 1.5, "every": 0.05,
                "r_lo": 2.8, "r_hi": 5.0, "min_win": 2.0, "margin": 2.0, "half_width": 1.5, "persist": 0.5,
                "f_cal": 0.0, "cal_band": 1.5, "mode": "hyst", "r_on": 5.0, "r_off": 2.5, "t_on": 0.5, "t_off": 1.0,
                "ramp": 0.2}


def detector(st: Streams, params: Optional[Dict] = None) -> Dict:
    """Causal running tremor-line detector (the app's clean-copy detector on a sliding past window).

    Every `every` s: the page-sensor track of the last `win` s that is available at that time, decimated to `fs`,
    high-passed at hp_hz (zero-phase within the past window), Welch PSD (segments of `seg` s, x + y summed); the
    writing floor is the running median of the log spectrum (+-3 Hz); the tremor line is the largest excess over the
    floor in [band_lo, band_hi].  Returns per update time: f_hat, peak ratio, the gate
    clip((ratio - r_lo) / (r_hi - r_lo), 0, 1) and the spectra (for the fixed-lag Wiener filter)."""
    from scipy.signal import butter, sosfiltfilt, welch
    p = dict(DET_DEFAULTS)
    if params:
        p.update({k: v for k, v in params.items() if k in DET_DEFAULTS})
    fs = float(p["fs"])
    tg, yg, lat = _page_grid(st, fs)
    t_up = np.arange(tg[0] + p["min_win"] + lat, st.tick_t[-1] + 1e-9, p["every"])
    nwin = int(round(p["win"] * fs)); nseg = int(round(p["seg"] * fs))
    sos = butter(2, p["hp_hz"], btype="high", fs=fs, output="sos")
    f_hat = np.zeros(len(t_up)); ratio = np.zeros(len(t_up)); amp = np.zeros(len(t_up))
    spec_f = None
    spec_P, spec_fl = [], []
    okp = st.pos_ok > 0.5
    tp_ok, tav_ok = st.pos_t[okp], st.pos_av[okp]
    for i, t in enumerate(t_up):
        # the window ends at the latest valid page sample AVAILABLE at t (grid points up to it are interpolated only
        # from samples acquired no later than it, so nothing unavailable at t enters)
        ka = int(np.searchsorted(tav_ok, t, side="right")) - 1
        j1 = int(np.searchsorted(tg, tp_ok[ka], side="right")) if ka >= 0 else 0
        j0 = max(0, j1 - nwin)
        seg = yg[j0:j1]
        if len(seg) < nseg + 8:
            spec_P.append(None); spec_fl.append(None)
            continue
        x = sosfiltfilt(sos, seg - seg.mean(0), axis=0, padlen=min(len(seg) - 1, 3 * nseg))
        f, P = welch(x, fs=fs, nperseg=nseg, noverlap=nseg // 2, axis=0, detrend="constant")
        P = P.sum(axis=1)
        fl = _floor(f, P)
        r = P / np.maximum(fl, 1e-30)
        m = (f >= p["band_lo"]) & (f <= p["band_hi"])
        if p["f_cal"] > 0:                                   # armed by the user's calibration: only near f_cal
            m &= np.abs(f - p["f_cal"]) <= p["cal_band"]
        k = int(np.flatnonzero(m)[np.argmax(r[m])])
        fh = float(f[k])
        if 0 < k < len(f) - 1:
            y0, y1, y2 = np.log(r[k - 1:k + 2])
            den = y0 - 2 * y1 + y2
            if abs(den) > 1e-12:
                fh = float(f[k] + float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) * (f[1] - f[0]))
        f_hat[i] = fh
        ratio[i] = float(r[k])
        exc = np.maximum(P - p["margin"] * fl, 0.0)
        inb = (np.abs(f - fh) <= p["half_width"]) | (np.abs(f - 2 * fh) <= p["half_width"])
        amp[i] = math.sqrt(2.0 * float(np.sum(exc[inb])) * float(f[1] - f[0]))
        spec_f = f
        spec_P.append(P); spec_fl.append(fl)
    raw = np.clip((ratio - p["r_lo"]) / max(p["r_hi"] - p["r_lo"], 1e-9), 0.0, 1.0)
    if p["mode"] == "hyst":
        # hysteresis: open once the line has stood above r_on for t_on; close once it has stayed below r_off for
        # t_off (tremor persists, a writing rhythm does not); the gate ramps over `ramp` s
        n_on = max(1, int(round(p["t_on"] / p["every"]))); n_off = max(1, int(round(p["t_off"] / p["every"])))
        stt = False; c_on = 0; c_off = 0
        state = np.zeros(len(ratio))
        for i, x in enumerate(ratio):
            if not stt:
                c_on = c_on + 1 if x > p["r_on"] else 0
                if c_on >= n_on:
                    stt = True; c_off = 0
            else:
                c_off = c_off + 1 if x < p["r_off"] else 0
                if c_off >= n_off:
                    stt = False; c_on = 0
            state[i] = 1.0 if stt else 0.0
        gate = np.zeros(len(state))
        a = min(1.0, p["every"] / max(p["ramp"], 1e-9))
        gv = 0.0
        for i, x in enumerate(state):
            gv = min(1.0, gv + a) if x > 0.5 else max(0.0, gv - a)
            gate[i] = gv
    else:
        # persistence: the gate opens only as far as the line has stood above the threshold for the last `persist` s
        npst = max(1, int(round(p["persist"] / p["every"])))
        gate = np.array([raw[max(0, i - npst + 1):i + 1].min() for i in range(len(raw))]) if len(raw) else raw
    return {"t": t_up, "gate_raw": raw, "f_hat": f_hat, "ratio": ratio, "gate": gate, "amp": amp, "spec_f": spec_f, "spec_P": spec_P,
            "spec_floor": spec_fl, "params": p}


def gate_at(det: Dict, t: np.ndarray, tau: float = 0.0) -> np.ndarray:
    """Detector gate at times t (zero-order hold of the latest update; optional first-order smoothing tau)."""
    k = np.searchsorted(det["t"], t, side="right") - 1
    g = np.where(k >= 0, det["gate"][np.clip(k, 0, len(det["gate"]) - 1)], 0.0)
    if tau > 0 and len(t) > 1:
        from scipy.signal import lfilter
        a = math.exp(-float(np.median(np.diff(t))) / tau)
        g = lfilter([1 - a], [1, -a], g)
    return g


# ======================================================================================== fixed-lag Wiener FIR
WF_DEFAULTS = {"n_past": 1.0, "fs": 250.0, "margin": 2.0, "half_width": 2.0, "beta": 1.0, "every": 0.1,
               "noise_floor": 1e-16}


def wiener_fixed_lag(st: Streams, det: Dict, lags: Sequence[float], delta: float, params: Optional[Dict] = None,
                     out_every: int = 8) -> Dict:
    """Fixed-lag Wiener smoother of the tremor from the running spectra of `detector` (the finite-lag version of the
    app's clean copy).  Model: page track y = w (writing, spectrum = the running-median floor) + d (tremor, spectrum =
    the excess above margin x floor within half_width of f_hat and 2 f_hat).  For each lag the FIR h over the last
    n_past s (up to the newest usable sample) minimises E|d(s) - sum_j h_j y(t_new - j)|^2 (normal equations,
    Levinson).  Each window is detrended by a quadratic fit first (the slow writing), so the filter sees what the
    detector's spectrum describes.  Filters are redesigned with every `every` s of spectra."""
    from scipy.linalg import solve_toeplitz
    p = dict(WF_DEFAULTS)
    if params:
        p.update({k: v for k, v in params.items() if k in WF_DEFAULTS})
    fs = float(p["fs"])
    tg, yg, lat = _page_grid(st, fs)
    N = int(round(p["n_past"] * fs))
    out_t = st.tick_t[::out_every]
    L = np.asarray(lags, float)
    D = np.zeros((len(out_t), len(L), 2))
    f = det["spec_f"]
    t_des = det["t"]
    step = max(1, int(round(p["every"] / det["params"]["every"])))
    nfft = 1 << int(math.ceil(math.log2(4 * N + 8)))
    fg = np.fft.rfftfreq(nfft, 1.0 / fs)
    design, sol = {}, {}
    u = np.arange(N, dtype=float)[::-1] / N             # time axis of the window (oldest .. newest)
    V = np.column_stack([np.ones(N), u, u * u])
    proj = V @ np.linalg.pinv(V)                        # quadratic detrend projector
    for m, t in enumerate(out_t):
        kd = int(np.searchsorted(t_des, t, side="right")) - 1
        if kd < 0 or det["gate"][kd] <= 0.0:
            continue
        kk = (kd // step) * step
        while kk > 0 and det["spec_P"][kk] is None:
            kk -= 1
        if det["spec_P"][kk] is None:
            continue
        j1 = int(np.searchsorted(tg, t - lat, side="right"))
        if j1 < N + 2:
            continue
        if kk not in design:
            P = det["spec_P"][kk]; fl = det["spec_floor"][kk]; fh = det["f_hat"][kk]
            exc = np.maximum(P - p["margin"] * fl, 0.0)
            inb = (np.abs(f - fh) <= p["half_width"]) | (np.abs(f - 2 * fh) <= p["half_width"])
            Sd = np.where(inb, exc, 0.0) * p["beta"]
            Sw = np.minimum(fl, P)
            ryy = np.fft.irfft(np.interp(fg, f, Sw + Sd) + p["noise_floor"], n=nfft)
            rdd = np.fft.irfft(np.interp(fg, f, Sd), n=nfft)
            design[kk] = (ryy[:N].copy(), rdd)
        ryy0, rdd = design[kk]
        seg = yg[j1 - N:j1][::-1]                         # y(t_new - j), j = 0..N-1
        seg = seg - proj @ seg
        for i, lag in enumerate(L):
            lsamp = int(round((tg[j1 - 1] - (t + delta - lag)) * fs))   # target, in samples before the newest
            key = (kk, lsamp)
            if key not in sol:
                idx = np.arange(N) - lsamp
                try:
                    sol[key] = solve_toeplitz(ryy0, rdd[np.abs(idx) % nfft])
                except Exception:
                    sol[key] = np.zeros(N)
            D[m, i] = sol[key] @ seg
    return {"t": out_t, "tremor": D, "lags": L, "delta": float(delta), "params": p}
