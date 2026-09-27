r"""Conventional causal disturbance predictors on the 250 Hz contract stream.

Every estimator receives exactly the information the learned model receives:
the increments dp (um) at 250 Hz (its cumulative sum is the page position up to
a constant) and, where stated, the Kalman phase-rate estimate f_est.  Each
predicts d(t_k + h) in um.  Conventional estimators extrapolate by
H = h + TAU_NOM (the nominal sensor latency is known from calibration).

  zero        d_hat = 0 (ratio 1 by construction)
  bpf         band-pass (2nd-order HP + 2nd-order LP biquads) + smoothed-derivative
              linear extrapolation: sim/pensim/core.py mode 2 at 250 Hz
  kf          intent (white jerk) + damped oscillator Kalman filter, amplitude-
              weighted phase-rate frequency adaptation, h-step oscillator prediction:
              line-by-line port of sim/pensim/core.py _kf_step and mode 3
  kf_ctrl     kf with NIS confidence, frequency gate and authority smoothing, i.e.
              the correction command the controller would apply
  bmflc       band-limited multiple Fourier linear combiner (Veluvolu & Ang), NLMS
              weights, 2nd-order high-pass pre-filter whose gain and phase are
              inverted per basis frequency in the prediction
  arls        direct h-step least-squares FIR predictor (window of increments ->
              d(t+h)), fitted on training writers with the same sample weights as
              the network; 'sched' variant has coefficients interpolated in f_est
  oracle_*    hold: true d at the newest sample's physical time (no prediction);
              osc: true oscillator state extrapolated (perfect separation bound)
Evidence status: SIMULATION / synthetic data.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit
from scipy import signal as sps

from . import common as C


# =============================================================== Kalman oscillator (port)
@njit(cache=True)
def _kf_step(x, P, y, Ts, w, rdamp, qj, qt, r):
    """Verbatim port of sim/pensim/core.py::_kf_step (5-state intent/oscillator KF).
    States: p, v, a (intended, white jerk), x1, x2 (oscillator).  Returns (innovation, S)."""
    c = math.cos(w * Ts)
    s = math.sin(w * Ts)
    F = np.zeros((5, 5))
    F[0, 0] = 1.0; F[0, 1] = Ts; F[0, 2] = 0.5 * Ts * Ts
    F[1, 1] = 1.0; F[1, 2] = Ts
    F[2, 2] = 1.0
    F[3, 3] = rdamp * c; F[3, 4] = rdamp * s
    F[4, 3] = -rdamp * s; F[4, 4] = rdamp * c
    Q = np.zeros((5, 5))
    T2 = Ts * Ts; T3 = T2 * Ts; T4 = T3 * Ts; T5 = T4 * Ts
    Q[0, 0] = qj * T5 / 20.0; Q[0, 1] = qj * T4 / 8.0; Q[0, 2] = qj * T3 / 6.0
    Q[1, 0] = Q[0, 1]; Q[1, 1] = qj * T3 / 3.0; Q[1, 2] = qj * T2 / 2.0
    Q[2, 0] = Q[0, 2]; Q[2, 1] = Q[1, 2]; Q[2, 2] = qj * Ts
    Q[3, 3] = qt * Ts; Q[4, 4] = qt * Ts
    xp = F @ x
    Pp = F @ P @ F.T + Q
    innov = y - (xp[0] + xp[3])
    S = Pp[0, 0] + Pp[0, 3] + Pp[3, 0] + Pp[3, 3] + r
    K = np.empty(5)
    for i in range(5):
        K[i] = (Pp[i, 0] + Pp[i, 3]) / S
    for i in range(5):
        x[i] = xp[i] + K[i] * innov
    for i in range(5):
        for j in range(5):
            P[i, j] = Pp[i, j] - K[i] * (Pp[0, j] + Pp[3, j])
    for i in range(5):
        for j in range(i + 1, 5):
            m = 0.5 * (P[i, j] + P[j, i])
            P[i, j] = m
            P[j, i] = m
    return innov, S


@njit(cache=True)
def _kf_loop(y, Ts, w0, rdamp, qj, qt, r, wgain, wmin, wmax, H, nis_alpha, nis_hi, fgate, fgw, alpha_a):
    """Mode-3 logic of sim/pensim/core.py at sample time Ts (optical always valid,
    no contact input: authority target = confidence x gate)."""
    n = y.shape[0]
    dhat = np.zeros((n, 2)); f_est = np.zeros(n); conf_o = np.zeros(n); geff_o = np.zeros(n)
    xk = np.zeros((2, 5)); Pk = np.zeros((2, 5, 5))
    for ax in range(2):
        xk[ax, 0] = y[0, ax]
        Pk[ax, 0, 0] = 1e-8; Pk[ax, 1, 1] = 1e-4; Pk[ax, 2, 2] = 1e-2
        Pk[ax, 3, 3] = 1e-7; Pk[ax, 4, 4] = 1e-7
    wkf = w0; kf_init = 0; phase_prev = 0.0; nis_f = 1.0; g_eff = 0.0
    rh = rdamp ** (H / Ts)
    for k in range(n):
        nis_sum = 0.0
        for ax in range(2):
            innov, S = _kf_step(xk[ax], Pk[ax], y[k, ax], Ts, wkf, rdamp, qj, qt, r)
            nis_sum += innov * innov / S
        nis_f = nis_f + nis_alpha * (0.5 * nis_sum - nis_f)
        amp0 = math.hypot(xk[0, 3], xk[0, 4]); amp1 = math.hypot(xk[1, 3], xk[1, 4])
        axm = 0 if amp0 >= amp1 else 1
        ampm = amp0 if axm == 0 else amp1
        phs = math.atan2(xk[axm, 4], xk[axm, 3])
        if kf_init == 1 and ampm > 2e-5:
            dph = phs - phase_prev
            while dph > math.pi:
                dph -= 2 * math.pi
            while dph < -math.pi:
                dph += 2 * math.pi
            wm = -dph / Ts
            wkf = wkf + wgain * (wm - wkf)
            wkf = min(max(wkf, wmin), wmax)
        phase_prev = phs
        kf_init = 1
        ch = math.cos(wkf * H); sh = math.sin(wkf * H)
        dhat[k, 0] = rh * (ch * xk[0, 3] + sh * xk[0, 4])
        dhat[k, 1] = rh * (ch * xk[1, 3] + sh * xk[1, 4])
        conf = min(1.0, max(0.0, 1.0 - (nis_f - 1.0) / max(nis_hi - 1.0, 1e-6)))
        f_tr = wkf / (2.0 * math.pi)
        if fgate > 0.0:
            gate = min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-6)))
            conf = conf * gate
        g_eff = g_eff + alpha_a * (conf - g_eff)
        f_est[k] = f_tr; conf_o[k] = conf; geff_o[k] = g_eff
    return dhat, f_est, conf_o, geff_o


def kf_run(y, Ts=C.TS, w0_hz=7.0, qj=10.0, qt=3e-9, r=2.5e-11 / 8, tau_decay=0.5, tau_w=0.3,
           wmin_hz=2.5, wmax_hz=14.0, H=C.H_S + C.TAU_NOM, nis_tau=0.0498, nis_hi=6.0,
           f_gate=0.0, f_gate_width=1.5, authority_tau=0.05):
    """y: (n,2) page position [m] (any constant offset).  Per-step constants of the
    2 kHz firmware loop are converted to time constants (rdamp, wgain, NIS and
    authority filters); r is a per-sample variance at Ts."""
    y = np.ascontiguousarray(np.asarray(y, np.float64))
    dh, fe, cf, ge = _kf_loop(y, Ts, 2 * np.pi * w0_hz, math.exp(-Ts / tau_decay), qj, qt, r, Ts / tau_w,
                              2 * np.pi * wmin_hz, 2 * np.pi * wmax_hz, H, 1.0 - math.exp(-Ts / nis_tau), nis_hi,
                              f_gate, f_gate_width, 1.0 - math.exp(-Ts / authority_tau))
    return {"dhat_um": dh * 1e6, "f_est": fe, "conf": cf, "g_eff": ge}


def frozen_kf_params(selection_path=None):
    """Controller KF configurations frozen by the simulator team
    (results/sim/estimator_selection.json: 'balanced' = selected, 'assertive' =
    selected_assertive) converted to 250 Hz.  The 2 kHz measurement variance kf_r
    is converted at equal continuous-time spectral density (r_250 = r_2k * 0.5 ms / 4 ms);
    rdamp, wgain, NIS and authority filters are expressed as time constants."""
    import json
    import os
    path = selection_path or os.path.join(C.ROOT, "results", "sim", "estimator_selection.json")
    sel = json.load(open(path))
    try:
        from sim.pensim.model import Controller   # controller defaults (read only)
        c = Controller()
        dflt = {k: getattr(c, k) for k in ("kf_qj", "kf_qt", "kf_r", "kf_w0_hz", "kf_tau_decay", "kf_tau_w",
                                           "kf_wmin_hz", "kf_wmax_hz", "conf_nis_hi", "f_gate", "f_gate_width",
                                           "authority_tau", "f_stage")}
        dsrc = "sim/pensim/model.py Controller defaults"
    except Exception as e:  # simulator is edited by others; fall back to the values read on 2026-09-27
        dflt = {"kf_qj": 3.0, "kf_qt": 2e-8, "kf_r": 2.5e-11, "kf_w0_hz": 6.0, "kf_tau_decay": 0.5, "kf_tau_w": 0.3,
                "kf_wmin_hz": 2.5, "kf_wmax_hz": 14.0, "conf_nis_hi": 6.0, "f_gate": 0.0, "f_gate_width": 1.5,
                "authority_tau": 0.05, "f_stage": 2000.0}
        dsrc = f"fallback constants ({type(e).__name__})"
    out = {}
    for key, name in (("selected", "balanced"), ("selected_assertive", "assertive")):
        s = sel["results"]["kfosc"][key]["params"]
        g = lambda k: float(s.get(k, dflt[k]))  # noqa: E731
        out[name] = {"w0_hz": g("kf_w0_hz"), "qj": g("kf_qj"), "qt": g("kf_qt"),
                     "r": g("kf_r") * (1.0 / dflt["f_stage"]) / C.TS,
                     "tau_decay": float(dflt["kf_tau_decay"]), "tau_w": float(dflt["kf_tau_w"]),
                     "wmin_hz": float(dflt["kf_wmin_hz"]), "wmax_hz": float(dflt["kf_wmax_hz"]),
                     "nis_hi": float(dflt["conf_nis_hi"]), "f_gate": g("f_gate"),
                     "f_gate_width": float(dflt["f_gate_width"]), "authority_tau": float(dflt["authority_tau"])}
    src = {"file": C.rpath(path), "generated_utc": sel["meta"].get("generated_utc"),
           "git_revision": sel["meta"].get("git_revision"),
           "selected_2kHz": sel["results"]["kfosc"]["selected"]["params"],
           "selected_assertive_2kHz": sel["results"]["kfosc"]["selected_assertive"]["params"],
           "controller_defaults_source": dsrc, "kf_r_2kHz": float(dflt["kf_r"])}
    return out, src


def feature_kf_params(frozen):
    """KF that produces the f_est input channel.  The balanced controller KF does not
    track frequency at all (its oscillator amplitude never exceeds the 20 um adaptation
    threshold, f_est stays at its 7 Hz start), so the channel uses the assertive
    configuration as the frequency tracker (see ml/README.md, proposed contract change)."""
    keep = ("w0_hz", "qj", "qt", "r", "tau_decay", "tau_w", "wmin_hz", "wmax_hz")
    return {k: frozen["assertive"][k] for k in keep}


# =============================================================== band-pass + extrapolation
def bpf_run(y, lo=6.0, hi=12.0, tune_hz=7.0, tau_d=0.00224, H=C.H_S + C.TAU_NOM):
    """sim/pensim/core.py mode 2 at 250 Hz.  The 2 kHz derivative smoother
    (0.2 per 0.5 ms step, time constant 2.24 ms) is expressed as tau_d."""
    fs = C.FS
    sos = np.vstack([sps.butter(2, lo, btype="high", fs=fs, output="sos"),
                     sps.butter(2, hi, btype="low", fs=fs, output="sos")])
    _, hh = sps.sosfreqz(sos, worN=[tune_hz], fs=fs)
    g = 1.0 / abs(hh[0])
    y = np.asarray(y, np.float64)
    yb = sps.sosfilt(sos, y - y[0], axis=0) * g
    yd = np.zeros_like(yb)
    yd[1:] = np.diff(yb, axis=0) / C.TS
    a = 1.0 - math.exp(-C.TS / tau_d) if tau_d > 0 else 1.0
    ys = sps.lfilter([a], [1.0, -(1.0 - a)], yd, axis=0)
    return (yb + H * ys) * 1e6


# =============================================================== BMFLC
@njit(cache=True)
def _bmflc_loop(s, t, freqs, mu, H, ginv, phi):
    n = s.shape[0]
    N = freqs.shape[0]
    w = np.zeros((2, 2 * N))
    out = np.zeros((n, 2))
    sn = np.empty(N); cs = np.empty(N); snp = np.empty(N); csp = np.empty(N)
    mun = mu / N
    for k in range(n):
        for i in range(N):
            a = 2.0 * math.pi * freqs[i] * t[k]
            sn[i] = math.sin(a); cs[i] = math.cos(a)
            b = 2.0 * math.pi * freqs[i] * (t[k] + H) - phi[i]
            snp[i] = ginv[i] * math.sin(b); csp[i] = ginv[i] * math.cos(b)
        for ax in range(2):
            est = 0.0
            for i in range(N):
                est += w[ax, i] * sn[i] + w[ax, N + i] * cs[i]
            e = s[k, ax] - est
            for i in range(N):
                w[ax, i] += mun * e * sn[i]
                w[ax, N + i] += mun * e * cs[i]
            p = 0.0
            for i in range(N):
                p += w[ax, i] * snp[i] + w[ax, N + i] * csp[i]
            out[k, ax] = p
    return out


def bmflc_run(y, f_lo=4.0, f_hi=13.0, df=0.5, mu=0.02, f_hp=2.0, H=C.H_S + C.TAU_NOM):
    """BMFLC on the 2nd-order-high-passed page position; prediction inverts the
    pre-filter's complex gain at each basis frequency."""
    y = np.asarray(y, np.float64)
    sos = sps.butter(2, f_hp, btype="high", fs=C.FS, output="sos")
    s = sps.sosfilt(sos, y - y[0], axis=0)
    freqs = np.arange(f_lo, f_hi + 1e-9, df)
    _, hh = sps.sosfreqz(sos, worN=freqs, fs=C.FS)
    t = np.arange(len(y)) * C.TS
    out = _bmflc_loop(np.ascontiguousarray(s), t, freqs, float(mu), float(H), 1.0 / np.abs(hh), np.angle(hh))
    return out * 1e6


# =============================================================== least-squares FIR predictors
def _windows(dp, p):
    """(n, 2p) matrix of the last p increments of x then y (zero before the start)."""
    n = len(dp)
    z = np.vstack([np.zeros((p - 1, 2), dp.dtype), dp])
    idx = np.arange(n)[:, None] + np.arange(p)[None, :]
    return np.concatenate([z[idx, 0], z[idx, 1]], axis=1)


SCHED_CENTERS = np.arange(3.0, 13.01, 1.0)


def _hat(f, centers=SCHED_CENTERS):
    f = np.clip(np.asarray(f, float), centers[0], centers[-1])
    d = centers[1] - centers[0]
    return np.clip(1.0 - np.abs(f[:, None] - centers[None, :]) / d, 0.0, 1.0)


def _design(rec, p, sched):
    X = _windows(np.asarray(rec["dp_um"], np.float64) / C.S_IN, p)
    if sched:
        Hm = _hat(rec["f_est"])
        X = (Hm[:, :, None] * X[:, None, :]).reshape(len(X), -1)
    return X


def sample_weights(rec):
    w = np.where(rec["env_tgt"] > 0, 1.0, C.LAMBDA_NT)
    w[: C.W - 1] = 0.0            # same ticks as the network (full window)
    return w


class ARLS:
    """Direct h-step least-squares predictor d(t+h) = X_k B (ridge), fitted on
    training writers.  sched=True: coefficients interpolated linearly in f_est
    between 1 Hz centres (a gain-scheduled / varying-coefficient linear model)."""

    def __init__(self, p=32, alpha=1e-3, sched=False):
        self.p, self.alpha, self.sched = int(p), float(alpha), bool(sched)
        self.B = None

    def fit(self, recs, stride=1):
        G = None
        for rec in recs:
            X = _design(rec, self.p, self.sched)[::stride]
            Y = (np.asarray(rec["d_tgt_um"], np.float64) / C.S_OUT)[::stride]
            w = sample_weights(rec)[::stride]
            Xw = X * w[:, None]
            if G is None:
                G = np.zeros((X.shape[1], X.shape[1])); Bx = np.zeros((X.shape[1], 2)); sw = 0.0
            G += Xw.T @ X
            Bx += Xw.T @ Y
            sw += w.sum()
        lam = self.alpha * np.trace(G) / G.shape[0]
        self.B = np.linalg.solve(G + lam * np.eye(G.shape[0]), Bx)
        return self

    def predict(self, rec):
        return (_design(rec, self.p, self.sched) @ self.B) * C.S_OUT

    def n_params(self):
        return int(self.B.size)


# =============================================================== registry helpers
def position(rec):
    """Page position [m] reconstructed from the increments (same information as dp)."""
    return np.cumsum(np.asarray(rec["dp_um"], np.float64), axis=0) * 1e-6


def run_method(name, rec, cfg, models=None):
    """Predict d(t_k + h) [um] for every tick of rec with method `name`."""
    if name == "zero":
        return np.zeros((len(rec["t"]), 2))
    if name == "bpf":
        return bpf_run(position(rec), **cfg)
    if name in ("kf", "kf_ctrl"):
        o = kf_run(position(rec), **cfg)
        if name == "kf":
            return o["dhat_um"]
        return o["dhat_um"] * o["g_eff"][:, None]
    if name == "bmflc":
        return bmflc_run(position(rec), **cfg)
    if name in ("arls", "arls_sched"):
        return models[name].predict(rec)
    if name == "oracle_hold":
        return np.asarray(rec["oracle_hold_um"], np.float64)
    if name == "oracle_osc":
        return np.asarray(rec["oracle_phase_um"], np.float64)
    raise KeyError(name)
