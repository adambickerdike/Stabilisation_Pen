r"""Causal tremor estimators for the Rev J nose on HW1 sensor streams (SIMULATION tooling; PROPOSED DESIGN laws).

Every estimator reads fusion.sensors.Streams (IMU, page sensor, contact; each sample used only once the tick time has
reached its availability time) and returns, per 2 kHz control tick, the handle-tremor estimate PREDICTED to the time
the nose will act (t + horizon), already multiplied by its authority.  The nose command is q = -d_hat (HW1's ext term).

Families (name -> function):
  g4          sim2j's guarded tracker G4 ported to HW1 (sim2j.akf_online.GuardedTracker, read-only): the Rev H AKF run tick
              by tick with the frequency-runaway guard, ai2's tremor-line detector at the stricter line (r_on 8, r_off
              4) multiplying the authority, fed with page samples taken while the ball is on the paper
              (results/sim2j/rules.json); horizon + the Rev J servo group delay
  gated       ai2's gated listening tracker (R's 'Rev J') with a re-tunable detector (band, thresholds, hysteresis
              or a soft persistence confidence) and a choice of fallback (the Rev H tracker as built, or none)
  akf         fusion's AKF with any parameter set (the 'listening' re-tunes), its own amplitude gate (a_lo, a_hi)
  wflc, bmflc fusion's WFLC and BMFLC on the page-frame acceleration (LIT ACT-08, ACT-09, ACT-10), with the pre-filter
              inverted per basis frequency and the output predicted to t + horizon
  bmflc_kf    BMFLC with Kalman-filter weights (LIT ACT-09): random-walk weights, one covariance shared by both axes
  epll        an enhanced-PLL / adaptive-oscillator tracker: one phase and frequency shared by both axes, per-axis
              in-phase and quadrature amplitudes of the fundamental and the 2nd harmonic (amplitude loops), a second-
              order phase loop (frequency integral + proportional phase correction) (LIT: EPLL equations restated by
              Abrar 2026; locking oscillators, Rosenblum et al. 2021)
  fir         a learned linear causal filter (learned.py): FIR on the accelerometer, trained on the tuning split
  net         a learned causal network (learned.py)
Authority (soft, for any raw estimate): the amplitude of the raw estimate A(t) = sqrt(2 x LP_tau(|d|^2)) maps to
g = clip((A - a_lo) / (a_hi - a_lo), 0, 1), smoothed with separate attack and release times; optionally multiplied by
a spectral confidence (the running line ratio as a continuous weight instead of a binary gate).
Delay handling: every estimator predicts its estimate to t + horizon (the IMU's anti-aliasing group delay is removed by
time-stamping; the page sensor's latency by roll-back or by using the accelerometer only); horizon defaults to the Rev J
servo's group delay (latency 0.6 ms + 2 zeta / omega_n = 3.39 ms) and is swept in delay.py.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
from numba import njit

TWO_PI = 2.0 * math.pi
ACC_GD = 1.04e-3                 # the IMU anti-aliasing filter's group delay (fusion.sensors; the recorded 400 Hz filter)


# ======================================================================================== common
def servo_delay(pen=None) -> float:
    from handwriting import params as PR
    from realdata import hw1 as H
    return PR.servo_group_delay(pen or H.revj_pen())


def acc_blocks(st, m: int = 2, acc_gd: Optional[float] = None):
    """Pairs of accelerometer samples averaged (the FIFO read of fusion's AKF): acquisition time (minus the anti-
    aliasing group delay; the module's ACC_GD unless given, read at call time so a simulator without the filter can
    set it), availability time, values."""
    from fusion import estimators as ES
    acc_gd = ACC_GD if acc_gd is None else acc_gd
    ta, tav, y = ES._block_average(st.acc_t, st.acc_av, st.acc, m)
    return np.ascontiguousarray(ta - acc_gd), np.ascontiguousarray(tav), np.ascontiguousarray(y, dtype=np.float64)


@njit(cache=True)
def _authority(d, Ts, tau_amp, a_lo, a_hi, tau_up, tau_down, gain, conf, out, out_g, out_a):
    m2 = 0.0
    g = 0.0
    au = 1.0 - math.exp(-Ts / max(tau_up, 1e-6))
    ad = 1.0 - math.exp(-Ts / max(tau_down, 1e-6))
    aa = min(1.0, Ts / max(tau_amp, 1e-6))
    for k in range(d.shape[0]):
        m2 = m2 + aa * (d[k, 0] * d[k, 0] + d[k, 1] * d[k, 1] - m2)
        A = math.sqrt(2.0 * m2)
        if a_hi > a_lo:
            tgt = min(1.0, max(0.0, (A - a_lo) / (a_hi - a_lo)))
        else:
            tgt = 1.0
        tgt *= conf[k]
        if tgt > g:
            g = g + au * (tgt - g)
        else:
            g = g + ad * (tgt - g)
        out[k, 0] = gain * g * d[k, 0]
        out[k, 1] = gain * g * d[k, 1]
        out_g[k] = g
        out_a[k] = A


AUTH_DEFAULTS = {"a_lo": 0.0, "a_hi": 0.0, "tau_amp": 0.3, "tau_up": 0.05, "tau_down": 0.2, "gain": 1.0}


def authority(d_raw: np.ndarray, Ts: float, p: Optional[Dict] = None, conf: Optional[np.ndarray] = None):
    """Soft amplitude-based authority on a raw estimate (see the module docstring).  Returns (d_hat, g, A)."""
    q = dict(AUTH_DEFAULTS)
    q.update(p or {})
    n = len(d_raw)
    out = np.zeros((n, 2)); g = np.zeros(n); A = np.zeros(n)
    c = np.ones(n) if conf is None else np.ascontiguousarray(conf[:n], dtype=np.float64)
    _authority(np.ascontiguousarray(d_raw, dtype=np.float64), Ts, q["tau_amp"], q["a_lo"], q["a_hi"], q["tau_up"],
               q["tau_down"], q["gain"], c, out, g, A)
    return out, g, A


# ======================================================================================== BMFLC with Kalman weights
@njit(cache=True)
def _biq(b, a, x, z):
    y = b[0] * x + z[0]
    z[0] = b[1] * x - a[1] * y + z[1]
    z[1] = b[2] * x - a[2] * y
    return y


@njit(cache=True)
def _bmflc_kf_run(tick_t, ta, tav, acc, w, Hm, Hp, q, r, p0, hor, bh, ah, bl, al, decim, out):
    """Kalman weights of a fixed Fourier bank on the pre-filtered acceleration (both axes, shared covariance)."""
    nb = w.shape[0]
    ns = 2 * nb
    P = np.zeros((ns, ns))
    for i in range(ns):
        P[i, i] = p0
    W = np.zeros((2, ns))
    h = np.zeros(ns)
    Ph = np.zeros(ns)
    zh = np.zeros((2, 2)); zl = np.zeros((2, 2)); u = np.zeros(2)
    n = tick_t.shape[0]
    na = ta.shape[0]
    ia = 0
    cnt = 0
    t_ref = -1.0
    t_last = 0.0
    started = False
    for k in range(n):
        t = tick_t[k]
        while ia < na and tav[ia] <= t:
            for ax in range(2):
                v = _biq(bh, ah, acc[ia, ax], zh[ax])
                u[ax] = _biq(bl, al, v, zl[ax])
            if t_ref < 0.0:
                t_ref = ta[ia]
            tt = ta[ia] - t_ref
            t_last = tt
            started = True
            cnt += 1
            if cnt % decim == 0:
                for i in range(nb):
                    h[2 * i] = math.sin(w[i] * tt)
                    h[2 * i + 1] = math.cos(w[i] * tt)
                for i in range(ns):
                    P[i, i] += q
                S = r
                for i in range(ns):
                    s = 0.0
                    for j in range(ns):
                        s += P[i, j] * h[j]
                    Ph[i] = s
                    S += h[i] * s
                for ax in range(2):
                    e = u[ax]
                    for i in range(ns):
                        e -= h[i] * W[ax, i]
                    for i in range(ns):
                        W[ax, i] += Ph[i] * e / S
                for i in range(ns):
                    for j in range(ns):
                        P[i, j] -= Ph[i] * Ph[j] / S
            ia += 1
        if not started:
            continue
        te = t_last + (t - (ta[ia - 1] if ia > 0 else t)) + hor
        for ax in range(2):
            dd = 0.0
            for i in range(nb):
                ph = w[i] * te - Hp[i]
                dd += -(W[ax, 2 * i] * math.sin(ph) + W[ax, 2 * i + 1] * math.cos(ph)) / (Hm[i] * w[i] * w[i])
            out[k, ax] = dd


BMFLC_KF_DEFAULTS = {"f_lo": 3.0, "f_hi": 12.0, "df": 0.5, "q": 1e-3, "r": 1.0, "p0": 1.0, "hp_hz": 2.0,
                     "lp_hz": 20.0, "horizon_extra": 0.0, "decim": 2}


def bmflc_kf(st, p: Optional[Dict] = None, horizon: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
    from scipy.signal import butter, freqz
    q = dict(BMFLC_KF_DEFAULTS)
    q.update(p or {})
    ta, tav, y = acc_blocks(st)
    fs = 1.0 / float(np.median(np.diff(ta)))
    bh, ah = butter(2, q["hp_hz"], btype="high", fs=fs)
    bl, al = butter(2, q["lp_hz"], btype="low", fs=fs)
    f = np.arange(q["f_lo"], q["f_hi"] + 1e-9, q["df"])
    H = freqz(bh, ah, worN=f, fs=fs)[1] * freqz(bl, al, worN=f, fs=fs)[1]
    hor = (servo_delay() if horizon is None else horizon) + q["horizon_extra"]
    out = np.zeros((st.n_ticks(), 2))
    _bmflc_kf_run(st.tick_t, ta, tav, y, TWO_PI * f, np.abs(H), np.angle(H), q["q"], q["r"], q["p0"], hor,
                  np.asarray(bh, float), np.asarray(ah, float), np.asarray(bl, float), np.asarray(al, float),
                  int(q["decim"]), out)
    return out, {"params": q, "n_basis": len(f), "horizon": hor}


# ======================================================================================== EPLL / adaptive oscillator
@njit(cache=True)
def _epll_run(tick_t, ta, tav, acc, prm, bh, ah, bl, al, out, out_f):
    """Shared phase phi and frequency w; per axis a: u_a ~ c1 cos(phi) + s1 sin(phi) + c2 cos(2 phi) + s2 sin(2 phi).
    Amplitude loops (gradient, mu_a), phase detector PD = sum_a e_a d(u_hat_a)/d(phi) / (amplitude^2), frequency loop
    w += mu_w PD dt, phase phi += (w + mu_p PD) dt; the frequency clamped to [f_lo, f_hi]."""
    mu_a = prm[0]; mu_w = prm[1]; mu_p = prm[2]; f_lo = prm[3]; f_hi = prm[4]; w0 = TWO_PI * prm[5]
    hor = prm[6]; harm_on = prm[7] > 0.5; a_eps = prm[8]
    n = tick_t.shape[0]
    na = ta.shape[0]
    zh = np.zeros((2, 2)); zl = np.zeros((2, 2)); u = np.zeros(2)
    C = np.zeros((2, 4))
    w = w0
    phi = 0.0
    t_prev = -1.0
    ia = 0
    started = False
    fs = 1.0 / (ta[1] - ta[0])
    for k in range(n):
        t = tick_t[k]
        while ia < na and tav[ia] <= t:
            for ax in range(2):
                v = _biq(bh, ah, acc[ia, ax], zh[ax])
                u[ax] = _biq(bl, al, v, zl[ax])
            dt = 1.0 / fs if t_prev < 0 else ta[ia] - t_prev
            t_prev = ta[ia]
            started = True
            cp = math.cos(phi); sp = math.sin(phi); c2 = math.cos(2 * phi); s2 = math.sin(2 * phi)
            pd = 0.0
            amp2 = a_eps
            for ax in range(2):
                uh = C[ax, 0] * cp + C[ax, 1] * sp
                if harm_on:
                    uh += C[ax, 2] * c2 + C[ax, 3] * s2
                e = u[ax] - uh
                # amplitude loops (normalised LMS step per sample)
                C[ax, 0] += mu_a * e * cp
                C[ax, 1] += mu_a * e * sp
                if harm_on:
                    C[ax, 2] += mu_a * e * c2
                    C[ax, 3] += mu_a * e * s2
                # phase detector: e x d(u_hat)/d(phi) (fundamental only)
                pd += e * (-C[ax, 0] * sp + C[ax, 1] * cp)
                amp2 += C[ax, 0] * C[ax, 0] + C[ax, 1] * C[ax, 1]
            pd /= amp2
            w += mu_w * pd * dt
            if w < TWO_PI * f_lo:
                w = TWO_PI * f_lo
            if w > TWO_PI * f_hi:
                w = TWO_PI * f_hi
            phi += (w + mu_p * pd) * dt
            if phi > 1e4:
                phi = phi - TWO_PI * math.floor(phi / TWO_PI)
            ia += 1
        if not started:
            continue
        # displacement at t + horizon: invert the pre-filter at w and 2w; divide by -(m w)^2
        dte = (t - t_prev) + hor
        for ax in range(2):
            dd = 0.0
            for m in range(2 if harm_on else 1):
                wm = (m + 1) * w
                Ts_a = 1.0 / fs
                # pre-filter response at wm (both biquads)
                hr, hi = _biq_resp(bh, ah, wm * Ts_a)
                lr, li = _biq_resp(bl, al, wm * Ts_a)
                Hr = hr * lr - hi * li; Hi = hr * li + hi * lr
                Hm = math.sqrt(Hr * Hr + Hi * Hi)
                Hph = math.atan2(Hi, Hr)
                ph = (m + 1) * (phi + w * dte) - Hph
                cc = C[ax, 2 * m]; ss = C[ax, 2 * m + 1]
                dd += -(cc * math.cos(ph) + ss * math.sin(ph)) / (Hm * wm * wm)
            out[k, ax] = dd
        out_f[k] = w / TWO_PI


@njit(cache=True)
def _biq_resp(b, a, wT):
    c1 = math.cos(wT); s1 = -math.sin(wT); c2 = math.cos(2 * wT); s2 = -math.sin(2 * wT)
    nr = b[0] + b[1] * c1 + b[2] * c2; ni = b[1] * s1 + b[2] * s2
    dr = a[0] + a[1] * c1 + a[2] * c2; di = a[1] * s1 + a[2] * s2
    den = dr * dr + di * di
    return (nr * dr + ni * di) / den, (ni * dr - nr * di) / den


EPLL_DEFAULTS = {"mu_a": 0.01, "mu_w": 2000.0, "mu_p": 30.0, "f_lo": 3.0, "f_hi": 12.0, "f0": 6.0, "harm": 1.0,
                 "a_eps": 1e-4, "hp_hz": 2.0, "lp_hz": 20.0, "horizon_extra": 0.0}


def epll(st, p: Optional[Dict] = None, horizon: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
    from scipy.signal import butter
    q = dict(EPLL_DEFAULTS)
    q.update(p or {})
    ta, tav, y = acc_blocks(st)
    fs = 1.0 / float(np.median(np.diff(ta)))
    bh, ah = butter(2, q["hp_hz"], btype="high", fs=fs)
    bl, al = butter(2, q["lp_hz"], btype="low", fs=fs)
    hor = (servo_delay() if horizon is None else horizon) + q["horizon_extra"]
    prm = np.array([q["mu_a"], q["mu_w"], q["mu_p"], q["f_lo"], q["f_hi"], q["f0"], hor, q["harm"], q["a_eps"]], float)
    out = np.zeros((st.n_ticks(), 2)); f = np.zeros(st.n_ticks())
    _epll_run(st.tick_t, ta, tav, y, prm, np.asarray(bh, float), np.asarray(ah, float), np.asarray(bl, float),
              np.asarray(al, float), out, f)
    return out, {"params": q, "f_est": f, "horizon": hor}


# ======================================================================================== wrappers of the programme's code
def akf(st, p: Optional[Dict] = None, horizon: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
    """fusion's AKF (read-only) with parameter set p; horizon = p['horizon'] + (servo delay unless given)."""
    from fusion import estimators as ES
    q = dict(p or {})
    q["horizon"] = float(q.get("horizon", 0.0)) + (servo_delay() if horizon is None else horizon)
    d, info = ES.akf(st, q)
    return d, info


def revh_params() -> Dict:
    """The Rev H tracker as built (results/opt/inertial_tracker_revh.json; R's 'Rev H' and the gated fallback)."""
    from aiprior import core as CO
    return dict(CO.tracker()["params"])


def listening_params() -> Dict:
    """ai2's listening tremor model as sim2j states it (DEC-042), output gates off, 64 Hz output low-pass."""
    from sim2j import akf_online as AO
    return AO.listening_params()


def flc(st, p: Optional[Dict] = None, mode: str = "bmflc", horizon: Optional[float] = None):
    from fusion import estimators as ES
    q = dict(p or {})
    q["horizon"] = float(q.get("horizon", 0.0)) + (servo_delay() if horizon is None else horizon)
    return ES.flc(st, q, mode=mode)


def g4(st, variant: str = "frozen", det_over: Optional[Dict] = None, guard_over: Optional[Dict] = None,
       horizon: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
    """sim2j's guarded tracker (G4, frozen in results/sim2j/rules.json) run tick by tick on HW1 streams.
    The detector sees page samples that are valid AND taken while the ball is on the paper (the latest contact sample
    available when the page sample becomes available), as sim2j's firmware passes them."""
    from dataclasses import replace
    from sim2j import akf_online as AO
    gp = AO.frozen_guard()
    dp = AO.frozen_det()
    if guard_over:
        gp = replace(gp, **guard_over)
    if det_over:
        dp = replace(dp, **det_over)
    Ts = float(st.tick_t[1] - st.tick_t[0])
    hx = servo_delay() if horizon is None else horizon
    trk = AO.GuardedTracker(revh_params(), Ts=Ts, horizon_extra=hx, guard=gp, det=dp)
    ta, tav, y = acc_blocks(st, acc_gd=0.0)                   # AKFOnline subtracts acc_gd itself (1.04 ms default)
    n = st.n_ticks()
    out = np.zeros((n, 2)); g = np.zeros(n); dg = np.zeros(n); f = np.zeros(n)
    ia = ip = 0
    na, npos = len(ta), len(st.pos_t)
    con_av, con = st.con_av, st.con
    for k in range(n):
        t = st.tick_t[k]
        while ia < na and tav[ia] <= t:
            trk.feed_acc(ta[ia], tav[ia], y[ia]); ia += 1
        while ip < npos and st.pos_av[ip] <= t:
            jc = int(np.searchsorted(con_av, st.pos_av[ip], side="right")) - 1
            on_paper = bool(jc >= 0 and con[jc] > 0.5)
            ok = st.pos_ok[ip] > 0.5
            trk.feed_pos(st.pos_t[ip], st.pos_av[ip], st.pos[ip], ok, ok_det=ok and on_paper)
            ip += 1
        out[k] = trk.step(t)
        g[k] = trk.last[3]; dg[k] = trk.det_gate; f[k] = trk.last[2]
    return out, {"authority": g, "det_gate": dg, "f_est": f, "guard_events": len(trk.events), "n_lock": trk.n_lock,
                 "guard": gp.__dict__, "det": dp.__dict__, "horizon_extra": hx}


class _Sc:
    """The duck-typed scenario ai2.delayed.estimates needs (streams, pen, Rev H tracker estimate)."""

    def __init__(self, st, dh, pen):
        self.streams = st
        self.dh = dh
        self.pen = pen


def gated(st, dh_revh: np.ndarray, det: Optional[Dict] = None, fallback: str = "revh",
          amp: Tuple[float, float] = (0.15e-3, 0.35e-3), tremor: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
    """ai2's gated listening tracker (R's Rev J row) with a re-tunable detector (ai2.smoothers.detector parameters:
    band_lo/band_hi, r_on/r_off/t_on/t_off for the hysteresis gate, or mode 'persist' with r_lo/r_hi for a soft
    confidence) and a choice of fallback ('revh' = the Rev H tracker as built, 'none')."""
    from realdata import hw1 as H
    from ai2 import delayed as DL
    M = H.ai2_models(with_tcn=False)
    S = M["S"]
    DL.OUT_EVERY = 1
    d = dict(S["det"] or {})
    d.update(det or {})
    cfg = DL.DelayCfg(tremor=tremor or S["tremor"], det=d)
    cfg.amp_lo, cfg.amp_hi = amp
    cfg.fallback = fallback
    sc = _Sc(st, dh_revh, H.revj_pen())
    est = DL.estimates(sc, cfg, lags=np.array([0.0]))
    tick_t = st.tick_t
    q = DL.command(est, np.zeros(len(tick_t)), tick_t)
    if fallback != "revh":
        est2 = dict(est)
        est2["dh"] = None
        q = DL.command(est2, np.zeros(len(tick_t)), tick_t)
    g = np.interp(tick_t, est["t"], est["g"])
    return -q, {"gate_open": float(np.mean(g > 0.5)), "g_mean": float(np.mean(g)), "det": est["det"]["params"]}


# ======================================================================================== registry
def raw_estimate(name: str, st, p: Optional[Dict] = None, horizon: Optional[float] = None, case=None, sensor="deltapen"):
    """(d (n_ticks, 2), info) of a family before any extra authority (families with their own gates keep them)."""
    p = dict(p or {})
    if name == "g4":
        return g4(st, det_over=p.get("det"), guard_over=p.get("guard"), horizon=horizon)
    if name == "gated":
        dh = case.dh_revh(sensor) if case is not None else None
        return gated(st, dh, det=p.get("det"), fallback=p.get("fallback", "revh"),
                     amp=tuple(p.get("amp", (0.15e-3, 0.35e-3))), tremor=p.get("tremor"))
    if name == "akf":
        return akf(st, p, horizon)
    if name in ("wflc", "bmflc"):
        return flc(st, p, mode=name, horizon=horizon)
    if name == "bmflc_kf":
        return bmflc_kf(st, p, horizon)
    if name == "epll":
        return epll(st, p, horizon)
    if name == "revh":
        return akf(st, revh_params(), horizon)
    if name in ("fir", "net"):
        from . import learned as LE
        return LE.estimate(name, st, p, horizon, case=case)
    if name == "gatefast":
        return gatefast(st, p, case=case, sensor=sensor, horizon=horizon)
    if name == "ai2tcn":
        return ai2_tcn(st)
    raise KeyError(name)


def ai2_tcn(st):
    """ai2's causal TCN (trained on synthetic writers; R's 'Rev J + AI' row) at lag 0: its 500 Hz outputs held and
    linearly extrapolated to the ticks (ai2.candidates.commands at lag 0, which is what R ran)."""
    from realdata import hw1 as H
    from ai2 import data as DA
    from ai2 import learned as L2
    from fusion import learned as FL
    M = H.ai2_models()
    X, tk = FL.features(st, DA.NET_HZ)
    Y = L2.predict(M["tcn"], L2.make_inputs("tcn", X))
    return np.ascontiguousarray(L2.hold_extrapolate(tk, Y[:, 0, :], st.tick_t)), {"tcn_info": "ai2 build/models tcn"}


def gatefast(st, p: Dict, case=None, sensor: str = "deltapen", horizon: Optional[float] = None):
    """The retuned binary gate exactly as tuned (search.gate_search): D = the listening AKF (or p['D']), ai2's detector
    on the page track with the chosen window and band, the hysteresis gate x the amplitude gate on the line amplitude
    (search.hyst_gate), d = gain g D + (1 - g) fb, fb = the Rev H tracker as built or nothing."""
    from ai2 import smoothers as SM
    from . import search as SR
    Dd = p.get("D") or SR.listening_design()
    D, _ = raw_estimate(Dd["family"], st, Dd.get("params"), horizon=horizon, case=case, sensor=sensor)
    g_p = p["gate"]
    dp = dict(SM.DET_DEFAULTS)
    dp.update(SR.DET_CONFIGS[g_p["det"]])
    det = SM.detector(st, dp)
    gu = SR.hyst_gate(det["t"], det["ratio"], det["amp"], g_p)
    k = np.searchsorted(det["t"], st.tick_t, side="right") - 1
    g = np.where(k >= 0, gu[np.clip(k, 0, len(gu) - 1)], 0.0)[:, None]
    d = g_p["gain"] * g * D
    if g_p["fallback"] == "revh":
        fb, _ = raw_estimate("revh", st, None, horizon=horizon)
        d = d + (1.0 - g) * fb
    elif g_p["fallback"] == "g4":                  # study W's GLG: sim2j's guarded tracker as the fallback
        fb, _ = g4(st, horizon=horizon)
        d = d + (1.0 - g) * fb
    return d, {"det_gate": g[:, 0], "gate_open": float(np.mean(g > 0.5))}


def estimate(design: Dict, st, case=None, sensor: str = "deltapen", horizon: Optional[float] = None):
    """A design = {'family', 'params', 'auth' (optional soft authority parameters)} -> (d_hat, info)."""
    d, info = raw_estimate(design["family"], st, design.get("params"), horizon=horizon, case=case, sensor=sensor)
    if design.get("auth"):
        Ts = float(st.tick_t[1] - st.tick_t[0])
        au = design["auth"]
        conf = None
        if "r_lo" in au:                  # the soft line confidence (search.conf_ratio's detector settings)
            conf = conf_from_ratio(det_ratio(st, DET_CONF_DEFAULTS)["ratio"], au["r_lo"], au["r_hi"])
        d, g, A = authority(d, Ts, au, conf)
        info = dict(info or {})
        info["auth_g"] = g
        info["auth_A"] = A
    return d, info


# ======================================================================================== spectral confidence (soft gate)
DET_CONF_DEFAULTS = {"win": 4.0, "seg": 2.0, "band_lo": 3.5, "band_hi": 12.0}


def det_ratio(st, p: Optional[Dict] = None, contact_only: bool = True) -> Dict:
    """ai2's running tremor-line detector (ai2.smoothers.detector, read-only) on the page track, every 50 ms: the line's
    peak ratio over the writing floor, its frequency and its amplitude, held to the ticks (causal: each update uses the
    page samples available at its time).  contact_only: the detector sees only samples taken with the ball on the
    paper (sim2j's firmware rule)."""
    from ai2 import smoothers as SM
    from fusion import sensors as S
    q = dict(DET_CONF_DEFAULTS)
    q.update(p or {})
    if contact_only:
        jc = np.searchsorted(st.con_av, st.pos_av, side="right") - 1
        on = np.where(jc >= 0, st.con[np.maximum(jc, 0)], 0.0) > 0.5
        st = S.Streams(tick_t=st.tick_t, acc_t=st.acc_t, acc_av=st.acc_av, acc=st.acc, pos_t=st.pos_t, pos_av=st.pos_av,
                       pos=st.pos, pos_ok=(st.pos_ok > 0.5) & on, con_t=st.con_t, con_av=st.con_av, con=st.con,
                       meta=st.meta)
        st.pos_ok = st.pos_ok.astype(np.float64)
    det = SM.detector(st, q)
    k = np.searchsorted(det["t"], st.tick_t, side="right") - 1
    ok = k >= 0
    kk = np.clip(k, 0, len(det["t"]) - 1)
    ratio = np.where(ok, det["ratio"][kk], 0.0)
    amp = np.where(ok, det["amp"][kk], 0.0)
    f = np.where(ok, det["f_hat"][kk], 0.0)
    return {"ratio": ratio, "amp": amp, "f": f, "params": det["params"]}


def conf_from_ratio(ratio: np.ndarray, r_lo: float, r_hi: float) -> np.ndarray:
    return np.clip((ratio - r_lo) / max(r_hi - r_lo, 1e-9), 0.0, 1.0)


def imu_track(st, fs: float = 1000.0, hp_hz: float = 0.5, leak_s: float = 2.0):
    """A position-like track from the accelerometer alone (causal): each 1 ms grid point takes the newest available
    acceleration pair, high-passed at hp_hz (2nd order), integrated twice with leaky integrators (time constant
    leak_s).  Its tremor band is the handle's, without the page sensor's error; its slow part is not a position."""
    from scipy.signal import butter, lfilter
    from fusion import sensors as S
    ta, tav, y = acc_blocks(st)
    tg = np.arange(float(tav[0]), float(st.tick_t[-1]), 1.0 / fs)
    j = np.searchsorted(tav, tg, side="right") - 1
    a = y[np.clip(j, 0, len(y) - 1)]
    b, aa = butter(2, hp_hz, btype="high", fs=fs)
    a = lfilter(b, aa, a, axis=0)
    lam = math.exp(-1.0 / (fs * leak_s))
    v = lfilter([1.0 / fs], [1.0, -lam], a, axis=0)
    x = lfilter([1.0 / fs], [1.0, -lam], v, axis=0)
    jc = np.searchsorted(st.con_av, tg, side="right") - 1
    ok = np.where(jc >= 0, st.con[np.maximum(jc, 0)], 0.0)
    return S.Streams(tick_t=st.tick_t, acc_t=st.acc_t, acc_av=st.acc_av, acc=st.acc, pos_t=tg, pos_av=tg.copy(),
                     pos=np.ascontiguousarray(x), pos_ok=ok.astype(np.float64), con_t=st.con_t, con_av=st.con_av,
                     con=st.con, meta=st.meta)


def det_ratio_imu(st, p: Optional[Dict] = None) -> Dict:
    """ai2's detector on the IMU track (imu_track), samples with the ball on the paper only."""
    from ai2 import smoothers as SM
    q = dict(DET_CONF_DEFAULTS)
    q.update(p or {})
    it = imu_track(st)
    det = SM.detector(it, q)
    k = np.searchsorted(det["t"], st.tick_t, side="right") - 1
    ok = k >= 0
    kk = np.clip(k, 0, len(det["t"]) - 1)
    return {"ratio": np.where(ok, det["ratio"][kk], 0.0), "amp": np.where(ok, det["amp"][kk], 0.0),
            "f": np.where(ok, det["f_hat"][kk], 0.0), "t_up": det["t"], "ratio_up": det["ratio"],
            "amp_up": det["amp"], "params": det["params"]}
