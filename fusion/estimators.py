r"""Causal disturbance estimators run outside the P1 core (numba), for Controller(mode="external").

Every estimator reads fusion.sensors.Streams and returns, per stage tick t_n (2 kHz), the
housing-disturbance estimate the stage should cancel, already multiplied by the estimator's own
authority (0..1).  A sample is used only once t_n >= its availability time.

kfosc   port of the frozen Kalman oscillator of sim/pencil/core.py mode 3 (5 states per axis:
        intent position/velocity/acceleration with jerk noise + one damped oscillator; frequency
        tracked from the oscillator phase rate; NIS confidence; frequency gate), fed with the same
        optical + IMU-increment fusion as the core (the optical sample plus the IMU-integrated motion
        since then).  Parameters: the frozen M1 set (results/sim/estimator_selection.json) and the
        Controller defaults.
akf     acceleration-domain Kalman filter, 8 states per axis
            x = [p, v, a (intent: white jerk q_j),  c1, s1 (tremor oscillator at w: q_t),
                 c2, s2 (2nd harmonic at 2w: q_h),  b (accelerometer bias: random walk q_b)]
        measurements: the accelerometer directly, y_a = a - w^2 c1 - 4 w^2 c2 + b (+ noise), stamped
        at its acquisition time minus the known filter group delay; the page sensor
        y_p = p + c1 + c2 (+ noise), applied at its acquisition time by rolling the filter back through
        a history of snapshots and re-applying the later accelerometer samples (exact handling of a
        2 ms or 10 ms latency).  Both axes share w and the covariance (identical F, Q, H, R).
        Frequency: phase rate of the larger oscillator, smoothed (tau_w) and clamped.
        Output: tremor (c1 + c2) predicted to t_n + h; authority = soft frequency gate x soft
        amplitude gate, smoothed.
wflc    weighted-frequency Fourier linear combiner (Riviere et al. 1998, ACT-08) on the page-frame
        acceleration, fundamental + 2nd harmonic, adaptive frequency; displacement = -component / (m w)^2
bmflc   band-limited multiple Fourier linear combiner (Veluvolu & Ang 2010/2011, ACT-09/10) on the
        acceleration: fixed bank f_lo..f_hi, LMS weights; each component's displacement is -1/w_k^2 of
        its acceleration; the pre-filter's gain and phase are inverted per basis frequency.
All outputs are SIMULATION quantities; parameters are tuned on fusion.TUNE_SEEDS only.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from numba import njit

from .sensors import Streams

TWO_PI = 2.0 * math.pi


# ======================================================================================== helpers
def _block_average(t_acq, t_av, y, m):
    """Average m consecutive accelerometer samples (FIFO read): mean acquisition time, last availability."""
    if m <= 1:
        return t_acq, t_av, y
    n = (len(t_acq) // m) * m
    return (t_acq[:n].reshape(-1, m).mean(axis=1), t_av[:n].reshape(-1, m).max(axis=1),
            y[:n].reshape(-1, m, y.shape[1]).mean(axis=1))


def _prm(d: Dict, keys, defaults):
    return np.array([float(d.get(k, defaults[k])) for k in keys])


# ======================================================================================== kfosc port
KFOSC_KEYS = ("qj", "qt", "r", "w0_hz", "tau_decay", "tau_w", "wmin_hz", "wmax_hz", "nis_hi", "f_gate", "f_gate_w",
              "horizon", "lag_s", "tau_auth", "leak_tau", "g", "lp_hz")
KFOSC_DEFAULTS = {"qj": 3.0, "qt": 2e-8, "r": 2.5e-11, "w0_hz": 6.0, "tau_decay": 0.5, "tau_w": 0.3, "wmin_hz": 2.5,
                  "wmax_hz": 14.0, "nis_hi": 6.0, "f_gate": 0.0, "f_gate_w": 1.5, "horizon": 1.3296e-3, "lag_s": 0.6e-3,
                  "tau_auth": 0.05, "leak_tau": 0.5, "g": 1.0, "lp_hz": 0.0}


def frozen_kfosc_params() -> Dict:
    """The frozen M1 set (sim.pencil.model.frozen_kf) over the Controller defaults, as the core uses it."""
    from sim.pencil import model as M
    kf = M.frozen_kf()
    c = M.Controller()
    return {"qj": kf.get("kf_qj", c.kf_qj), "qt": kf.get("kf_qt", c.kf_qt), "r": kf.get("kf_r", c.kf_r),
            "w0_hz": kf.get("kf_w0_hz", c.kf_w0_hz), "tau_decay": kf.get("kf_tau_decay", c.kf_tau_decay),
            "tau_w": kf.get("kf_tau_w", c.kf_tau_w), "wmin_hz": kf.get("kf_wmin_hz", c.kf_wmin_hz),
            "wmax_hz": kf.get("kf_wmax_hz", c.kf_wmax_hz), "nis_hi": kf.get("conf_nis_hi", c.conf_nis_hi),
            "f_gate": kf.get("f_gate", c.f_gate), "f_gate_w": kf.get("f_gate_width", c.f_gate_width),
            "horizon": 1e-3 + 0.25e-3 + 1.0 / (2 * math.pi * 2000.0), "tau_auth": c.authority_tau}


@njit(cache=True)
def _kf_step(x, P, y, Ts, w, rdamp, qj, qt, r):
    """Copy of sim/pencil/core.py::_kf_step (itself a copy of sim/pensim/core.py)."""
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
def _kfosc_run(tick_t, acc_t, acc_av, acc, pos_t, pos_av, pos, pos_ok, prm, out, out_f, out_g):
    qj = prm[0]; qt = prm[1]; kr = prm[2]; wkf = TWO_PI * prm[3]
    Ts = tick_t[1] - tick_t[0]
    rdamp = math.exp(-Ts / prm[4]); wg = Ts / prm[5]
    wmin = TWO_PI * prm[6]; wmax = TWO_PI * prm[7]; nishi = prm[8]; fgate = prm[9]; fgw = prm[10]
    hor = prm[11]; lag_t = int(round(prm[12] / Ts)); alpha_a = 1.0 - math.exp(-Ts / prm[13]); leak = prm[14]; gout = prm[15]
    lp_hz = prm[16]
    lb, la = _lp2_coef(lp_hz, Ts)
    zlp = np.zeros((2, 2))
    hor = hor + _lp2_delay(lp_hz)
    n = len(tick_t)
    ia = 0; ip = 0
    na = len(acc_t); npos = len(pos_t)
    vimu = np.zeros(2); pimu = np.zeros(2)
    rb = np.zeros((1024, 2))
    o_meas = np.zeros(2); o_valid = 0.0
    xk = np.zeros((2, 5)); Pk = np.zeros((2, 5, 5))
    for axx in range(2):
        for i in range(5):
            Pk[axx, i, i] = 1e-6
    kf_init = 0; phase_prev = 0.0; nis_f = 1.0; need_reinit = 1
    g_eff = 0.0
    t_last_a = 0.0
    for k in range(n):
        t = tick_t[k]
        # IMU samples available by now: leaky velocity integration as the core
        while ia < na and acc_av[ia] <= t:
            dti = acc_t[ia] - t_last_a if ia > 0 else 1.0 / 4000.0
            t_last_a = acc_t[ia]
            for j in range(2):
                vimu[j] = (vimu[j] + acc[ia, j] * dti) * (1.0 - dti / leak)
                pimu[j] += vimu[j] * dti
            ia += 1
        while ip < npos and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5:
                o_meas[0] = pos[ip, 0]; o_meas[1] = pos[ip, 1]
                if o_valid < 0.5:
                    need_reinit = 1
                o_valid = 1.0
            else:
                o_valid = 0.0
            ip += 1
        rb[k % 1024, 0] = pimu[0]; rb[k % 1024, 1] = pimu[1]
        jl = (k - lag_t) % 1024
        ph0 = o_meas[0] + (pimu[0] - rb[jl, 0])
        ph1 = o_meas[1] + (pimu[1] - rb[jl, 1])
        target = 0.0
        d0 = 0.0; d1 = 0.0
        if o_valid > 0.5 and ip > 0:
            if need_reinit == 1:
                for axx in range(2):
                    for i in range(5):
                        xk[axx, i] = 0.0
                        for j in range(5):
                            Pk[axx, i, j] = 0.0
                    xk[axx, 0] = ph0 if axx == 0 else ph1
                    Pk[axx, 0, 0] = 1e-8; Pk[axx, 1, 1] = 1e-4; Pk[axx, 2, 2] = 1e-2
                    Pk[axx, 3, 3] = 1e-7; Pk[axx, 4, 4] = 1e-7
                need_reinit = 0
            nis_sum = 0.0
            for axx in range(2):
                yv = ph0 if axx == 0 else ph1
                innov, S = _kf_step(xk[axx], Pk[axx], yv, Ts, wkf, rdamp, qj, qt, kr)
                nis_sum += innov * innov / S
            nis_f = nis_f + 0.01 * (0.5 * nis_sum - nis_f)
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
                wkf = wkf + wg * (wm - wkf)
                wkf = min(max(wkf, wmin), wmax)
            phase_prev = phs
            kf_init = 1
            ch = math.cos(wkf * hor); sh = math.sin(wkf * hor)
            rh = rdamp ** (hor / Ts)
            d0 = rh * (ch * xk[0, 3] + sh * xk[0, 4])
            d1 = rh * (ch * xk[1, 3] + sh * xk[1, 4])
            conf = min(1.0, max(0.0, 1.0 - (nis_f - 1.0) / max(nishi - 1.0, 1e-6)))
            f_tr = wkf / TWO_PI
            if fgate > 0.0:
                gate = min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-6)))
                conf = conf * gate
            target = gout * conf
        else:
            need_reinit = 1
        g_eff = g_eff + alpha_a * (target - g_eff)
        out[k, 0] = _lp2_step(lb, la, g_eff * d0, zlp[0]); out[k, 1] = _lp2_step(lb, la, g_eff * d1, zlp[1])
        out_f[k] = wkf / TWO_PI; out_g[k] = g_eff


def kfosc(st: Streams, params: Dict = None) -> Tuple[np.ndarray, Dict]:
    p = dict(KFOSC_DEFAULTS)
    p.update(frozen_kfosc_params())
    if params:
        p.update(params)
    if "lag_s" not in (params or {}):
        # the optical sample is older than the IMU-integrated motion by (page latency - IMU latency), as the core's lag_t
        p["lag_s"] = max(0.0, st.meta.get("page_latency", 2e-3) - (1.04e-3 + st.meta.get("imu_extra_latency", 0.0)))
    n = st.n_ticks()
    out = np.zeros((n, 2)); f = np.zeros(n); g = np.zeros(n)
    _kfosc_run(st.tick_t, st.acc_t, st.acc_av, st.acc, st.pos_t, st.pos_av, st.pos, st.pos_ok,
               _prm(p, KFOSC_KEYS, KFOSC_DEFAULTS), out, f, g)
    return out, {"f_est": f, "authority": g, "params": p}


# ======================================================================================== AKF
AKF_KEYS = ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz",
            "f_gate", "f_gate_w", "a_lo", "a_hi", "tau_amp", "horizon", "tau_auth", "acc_gd", "gap_reset", "g", "use_pos",
            "use_acc", "harm", "lp_hz", "xtrack", "v_xt")
AKF_DEFAULTS = {"qj": 30.0, "qt": 1e-6, "qh": 2e-7, "qb": 1e-6, "ra": 1e-3, "rp": 1e-11, "tau_decay": 0.6,
                "w0_hz": 7.0, "tau_w": 0.25, "wmin_hz": 3.0, "wmax_hz": 14.0, "f_gate": 0.0, "f_gate_w": 1.5,
                "a_lo": 0.0, "a_hi": 0.0, "tau_amp": 0.2, "horizon": 1.5e-3, "tau_auth": 0.05, "acc_gd": 1.04e-3,
                "gap_reset": 0.03, "g": 1.0, "use_pos": 1.0, "use_acc": 1.0, "harm": 1.0, "lp_hz": 60.0,
                "xtrack": 0.0, "v_xt": 5e-3}
NS = 8
HIST = 512


@njit(cache=True)
def _lp2_coef(fc, Ts):
    """2nd-order Butterworth low-pass (bilinear, prewarped) as a biquad; fc <= 0: pass-through."""
    b = np.zeros(3); a = np.zeros(3)
    if fc <= 0.0:
        b[0] = 1.0; a[0] = 1.0
        return b, a
    K = math.tan(math.pi * fc * Ts)
    norm = 1.0 / (1.0 + math.sqrt(2.0) * K + K * K)
    b[0] = K * K * norm; b[1] = 2.0 * b[0]; b[2] = b[0]
    a[0] = 1.0; a[1] = 2.0 * (K * K - 1.0) * norm; a[2] = (1.0 - math.sqrt(2.0) * K + K * K) * norm
    return b, a


@njit(cache=True)
def _lp2_step(b, a, x, z):
    y = b[0] * x + z[0]
    z[0] = b[1] * x - a[1] * y + z[1]
    z[1] = b[2] * x - a[2] * y
    return y


@njit(cache=True)
def _lp2_delay(fc):
    """Low-frequency group delay of the 2nd-order Butterworth low-pass: sqrt(2) / (2 pi fc)."""
    return 0.0 if fc <= 0.0 else math.sqrt(2.0) / (2.0 * math.pi * fc)


@njit(cache=True)
def _akf_FQ(dt, w, tau_d, qj, qt, qh, qb, F, Q):
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
def _akf_predict(x, P, F, Q, tmp):
    # x[a] <- F x[a] (both axes); P <- F P F' + Q
    for a in range(2):
        for i in range(NS):
            s = 0.0
            for j in range(NS):
                s += F[i, j] * x[a, j]
            tmp[0, i] = s
        for i in range(NS):
            x[a, i] = tmp[0, i]
    FP = np.empty((NS, NS))
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(NS):
                s += F[i, k] * P[k, j]
            FP[i, j] = s
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(NS):
                s += FP[i, k] * F[j, k]
            P[i, j] = s + Q[i, j]


@njit(cache=True)
def _akf_update(x, P, H, y0, y1, R):
    PH = np.empty(NS)
    for i in range(NS):
        s = 0.0
        for j in range(NS):
            s += P[i, j] * H[j]
        PH[i] = s
    S = R
    for i in range(NS):
        S += H[i] * PH[i]
    e0 = y0; e1 = y1
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
    return (e0 * e0 + e1 * e1) / S


@njit(cache=True)
def _akf_run(tick_t, acc_t, acc_av, acc, pos_t, pos_av, pos, pos_ok, prm, out, out_f, out_g, out_amp):
    qj = prm[0]; qt = prm[1]; qh = prm[2] * prm[23]; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    w = TWO_PI * prm[7]; tau_w = prm[8]; wmin = TWO_PI * prm[9]; wmax = TWO_PI * prm[10]
    fgate = prm[11]; fgw = prm[12]; a_lo = prm[13]; a_hi = prm[14]; tau_amp = prm[15]; hor = prm[16]
    tau_auth = prm[17]; acc_gd = prm[18]; gap_reset = prm[19]; gout = prm[20]; use_pos = prm[21] > 0.5
    use_acc = prm[22] > 0.5; harm = prm[23]; lp_hz = prm[24]; xtrack = prm[25] > 0.5; v_xt = prm[26]
    n = len(tick_t)
    Ts = tick_t[1] - tick_t[0]
    lb, la = _lp2_coef(lp_hz, Ts)
    zlp = np.zeros((2, 2))
    hor = hor + _lp2_delay(lp_hz)       # the output low-pass's group delay is predicted ahead (narrow-band tremor)
    na = len(acc_t); npos = len(pos_t)
    x = np.zeros((2, NS)); P = np.zeros((NS, NS))
    F = np.zeros((NS, NS)); Q = np.zeros((NS, NS)); tmp = np.zeros((1, NS))
    Ha = np.zeros(NS); Hp = np.zeros(NS)
    Hp[0] = 1.0; Hp[3] = 1.0; Hp[5] = harm
    # history of snapshots after each accelerometer update
    h_t = np.zeros(HIST); h_y = np.zeros((HIST, 2)); h_x = np.zeros((HIST, 2, NS)); h_P = np.zeros((HIST, NS, NS))
    h_w = np.zeros(HIST)
    nh = 0                 # total snapshots written
    ia = 0; ip = 0
    tf = 0.0               # filter time (acquisition time of the last processed sample)
    started = False
    last_pos_t = -1.0
    g_eff = 0.0
    amp_f = 0.0
    phase_prev = 0.0; have_phase = False; tf_prev = 0.0; ax_prev = 0
    for k in range(n):
        t = tick_t[k]
        # ---------------- accelerometer samples available by now
        while ia < na and acc_av[ia] <= t:
            ta = acc_t[ia] - acc_gd
            if not started:
                if ip < npos:
                    pass
                started = True
                tf = ta
                for i in range(NS):
                    P[i, i] = 1e-12
                P[0, 0] = 1e-6; P[1, 1] = 1e-4; P[2, 2] = 1.0; P[3, 3] = 1e-7; P[4, 4] = 1e-7
                P[5, 5] = 1e-8; P[6, 6] = 1e-8; P[7, 7] = 0.05
            dt = ta - tf
            if dt > 0:
                _akf_FQ(dt, w, tau_d, qj, qt, qh, qb, F, Q)
                _akf_predict(x, P, F, Q, tmp)
                tf = ta
            if use_acc:
                Ha[2] = 1.0; Ha[3] = -w * w; Ha[5] = -4.0 * w * w * harm; Ha[7] = 1.0
                _akf_update(x, P, Ha, acc[ia, 0], acc[ia, 1], ra)
            j = nh % HIST
            h_t[j] = tf; h_y[j, 0] = acc[ia, 0]; h_y[j, 1] = acc[ia, 1]; h_w[j] = w
            for a in range(2):
                for i in range(NS):
                    h_x[j, a, i] = x[a, i]
            for i in range(NS):
                for jj in range(NS):
                    h_P[j, i, jj] = P[i, jj]
            nh += 1
            ia += 1
        # ---------------- page-sensor samples available by now (delayed: roll back and re-propagate)
        while ip < npos and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5 and use_pos and started and nh > 0:
                tp = pos_t[ip]
                # find the last snapshot with time <= tp
                lo = max(0, nh - HIST)
                jj = nh - 1
                while jj >= lo and h_t[jj % HIST] > tp:
                    jj -= 1
                if jj >= lo:
                    s = jj % HIST
                    for a in range(2):
                        for i in range(NS):
                            x[a, i] = h_x[s, a, i]
                    for i in range(NS):
                        for q in range(NS):
                            P[i, q] = h_P[s, i, q]
                    tf = h_t[s]
                    wr = h_w[s]
                    # position re-anchoring after a gap (pen lifted: page sensor invalid)
                    if last_pos_t < 0 or tp - last_pos_t > gap_reset:
                        dt = tp - tf
                        if dt > 0:
                            _akf_FQ(dt, wr, tau_d, qj, qt, qh, qb, F, Q)
                            _akf_predict(x, P, F, Q, tmp)
                            tf = tp
                        pred = x[0, 0] + x[0, 3] + harm * x[0, 5]
                        pred1 = x[1, 0] + x[1, 3] + harm * x[1, 5]
                        x[0, 0] += pos[ip, 0] - pred
                        x[1, 0] += pos[ip, 1] - pred1
                        for q in range(NS):
                            P[0, q] = 0.0
                            P[q, 0] = 0.0
                        P[0, 0] = rp
                    else:
                        dt = tp - tf
                        if dt > 0:
                            _akf_FQ(dt, wr, tau_d, qj, qt, qh, qb, F, Q)
                            _akf_predict(x, P, F, Q, tmp)
                            tf = tp
                        _akf_update(x, P, Hp, pos[ip, 0], pos[ip, 1], rp)
                    last_pos_t = tp
                    # re-apply the later accelerometer samples, overwriting their snapshots
                    for q in range(jj + 1, nh):
                        s2 = q % HIST
                        wq = h_w[s2]
                        dt = h_t[s2] - tf
                        if dt > 0:
                            _akf_FQ(dt, wq, tau_d, qj, qt, qh, qb, F, Q)
                            _akf_predict(x, P, F, Q, tmp)
                            tf = h_t[s2]
                        if use_acc:
                            Ha[2] = 1.0; Ha[3] = -wq * wq; Ha[5] = -4.0 * wq * wq * harm; Ha[7] = 1.0
                            _akf_update(x, P, Ha, h_y[s2, 0], h_y[s2, 1], ra)
                        for a in range(2):
                            for i in range(NS):
                                h_x[s2, a, i] = x[a, i]
                        for i in range(NS):
                            for r2 in range(NS):
                                h_P[s2, i, r2] = P[i, r2]
            ip += 1
        # ---------------- frequency tracking from the fundamental's phase rate, measured over the advance of
        # the filter time (samples do not arrive exactly once per tick); smoothing time constant tau_w
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
            phase_prev = phs
            tf_prev = tf
            ax_prev = axm
            have_phase = True
        # ---------------- output: tremor predicted to t + horizon
        d0 = 0.0; d1 = 0.0
        if started:
            dtp = t + hor - tf
            rd = math.exp(-max(dtp, 0.0) / tau_d)
            c = math.cos(w * dtp); s = math.sin(w * dtp)
            c2 = math.cos(2 * w * dtp); s2_ = math.sin(2 * w * dtp)
            d0 = rd * (c * x[0, 3] + s * x[0, 4] + harm * (c2 * x[0, 5] + s2_ * x[0, 6]))
            d1 = rd * (c * x[1, 3] + s * x[1, 4] + harm * (c2 * x[1, 5] + s2_ * x[1, 6]))
            if xtrack:
                # cancel only across the stroke: remove the component along the intent velocity (the writing's
                # own speed changes live there); full output when the pen is (nearly) still
                vx = x[0, 1]; vy = x[1, 1]
                sp = math.hypot(vx, vy)
                if sp > 1e-9:
                    tx = vx / sp; ty = vy / sp
                    wgt = min(1.0, sp / v_xt)
                    dl = tx * d0 + ty * d1
                    d0 -= wgt * dl * tx; d1 -= wgt * dl * ty
        amp = math.sqrt(amp0 * amp0 + amp1 * amp1)
        amp_f = amp_f + (Ts / tau_amp) * (amp - amp_f)
        target = gout
        if fgate > 0.0:
            f_tr = w / TWO_PI
            target *= min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-9)))
        if a_hi > a_lo:
            target *= min(1.0, max(0.0, (amp_f - a_lo) / (a_hi - a_lo)))
        if not started:
            target = 0.0
        g_eff = g_eff + (1.0 - math.exp(-Ts / tau_auth)) * (target - g_eff)
        out[k, 0] = _lp2_step(lb, la, g_eff * d0, zlp[0]); out[k, 1] = _lp2_step(lb, la, g_eff * d1, zlp[1])
        out_f[k] = w / TWO_PI; out_g[k] = g_eff; out_amp[k] = amp_f


def akf(st: Streams, params: Dict = None, acc_decim: int = 2) -> Tuple[np.ndarray, Dict]:
    p = dict(AKF_DEFAULTS)
    if params:
        p.update(params)
    ta, tav, y = _block_average(st.acc_t, st.acc_av, st.acc, acc_decim)
    n = st.n_ticks()
    out = np.zeros((n, 2)); f = np.zeros(n); g = np.zeros(n); amp = np.zeros(n)
    _akf_run(st.tick_t, ta, tav, np.ascontiguousarray(y), st.pos_t, st.pos_av, st.pos, st.pos_ok,
             _prm(p, AKF_KEYS, AKF_DEFAULTS), out, f, g, amp)
    return out, {"f_est": f, "authority": g, "amp": amp, "params": p, "acc_decim": acc_decim}


# ======================================================================================== WFLC / BMFLC
FLC_KEYS = ("mu", "mu0", "f_lo", "f_hi", "df", "hp_hz", "lp_hz", "horizon", "g", "a_lo", "a_hi", "tau_amp",
            "tau_auth", "w0_hz", "acc_gd", "harm", "f_gate", "f_gate_w", "out_lp_hz")
FLC_DEFAULTS = {"mu": 0.002, "mu0": 0.02, "f_lo": 3.0, "f_hi": 14.0, "df": 0.5, "hp_hz": 2.5, "lp_hz": 20.0,
                "horizon": 1.5e-3, "g": 1.0, "a_lo": 0.0, "a_hi": 0.0, "tau_amp": 0.2, "tau_auth": 0.05,
                "w0_hz": 7.0, "acc_gd": 1.04e-3, "harm": 1.0, "f_gate": 0.0, "f_gate_w": 1.5, "out_lp_hz": 60.0}
NB_MAX = 64


@njit(cache=True)
def _biquad(b, a, x, z):
    y = b[0] * x + z[0]
    z[0] = b[1] * x - a[1] * y + z[1]
    z[1] = b[2] * x - a[2] * y
    return y


@njit(cache=True)
def _flc_run(mode, tick_t, acc_t, acc_av, acc, prm, bh, ah, bl, al, Hre, Him, out, out_f, out_g):
    """mode 0 = BMFLC (fixed bank), 1 = WFLC (adaptive fundamental + 2nd harmonic, shared by both axes)."""
    mu = prm[0]; mu0 = prm[1]; f_lo = prm[2]; f_hi = prm[3]; df = prm[4]
    hor = prm[7]; gout = prm[8]; a_lo = prm[9]; a_hi = prm[10]; tau_amp = prm[11]; tau_auth = prm[12]
    w0 = TWO_PI * prm[13]; acc_gd = prm[14]; harm = prm[15]; fgate = prm[16]; fgw = prm[17]; olp = prm[18]
    nb = Hre.shape[0]
    Ts = tick_t[1] - tick_t[0]
    Ta = acc_t[1] - acc_t[0]
    lb, la = _lp2_coef(olp, Ts)
    zlp = np.zeros((2, 2))
    hor = hor + _lp2_delay(olp)
    n = len(tick_t)
    na = len(acc_t)
    zh = np.zeros((2, 2)); zl = np.zeros((2, 2))
    W = np.zeros((2, 2 * NB_MAX))
    u = np.zeros(2); e = np.zeros(2)
    ia = 0
    g_eff = 0.0; amp_f = 0.0
    phi = 0.0            # WFLC phase (integral of w0)
    t_prev = -1.0
    for k in range(n):
        t = tick_t[k]
        while ia < na and acc_av[ia] <= t:
            ta = acc_t[ia] - acc_gd
            if t_prev < 0:
                t_prev = ta
            dt = ta - t_prev
            t_prev = ta
            for ax in range(2):
                v = _biquad(bh, ah, acc[ia, ax], zh[ax])
                u[ax] = _biquad(bl, al, v, zl[ax])
            if mode == 0:
                for ax in range(2):
                    yh = 0.0
                    for i in range(nb):
                        wi = TWO_PI * (f_lo + i * df)
                        yh += W[ax, 2 * i] * math.sin(wi * ta) + W[ax, 2 * i + 1] * math.cos(wi * ta)
                    e[ax] = u[ax] - yh
                for i in range(nb):
                    wi = TWO_PI * (f_lo + i * df)
                    sn = math.sin(wi * ta); cs = math.cos(wi * ta)
                    for ax in range(2):
                        W[ax, 2 * i] += 2 * mu * e[ax] * sn / nb
                        W[ax, 2 * i + 1] += 2 * mu * e[ax] * cs / nb
            else:
                phi += w0 * dt
                gsum = 0.0
                for ax in range(2):
                    yh = 0.0
                    for m in range(2):
                        yh += W[ax, 2 * m] * math.sin((m + 1) * phi) + W[ax, 2 * m + 1] * math.cos((m + 1) * phi)
                    e[ax] = u[ax] - yh
                    # frequency gradient from the fundamental only: with the harmonic in the gradient the
                    # combiner locks onto half the tremor frequency (tested on a pure sinusoid)
                    gsum += e[ax] * (W[ax, 0] * math.cos(phi) - W[ax, 1] * math.sin(phi))
                for ax in range(2):
                    for m in range(2):
                        sc = 1.0 if m == 0 else harm
                        W[ax, 2 * m] += 2 * mu * sc * e[ax] * math.sin((m + 1) * phi)
                        W[ax, 2 * m + 1] += 2 * mu * sc * e[ax] * math.cos((m + 1) * phi)
                # normalised frequency update (Riviere): gradient sum over both axes, scaled by the signal power
                pw = 1e-9
                for ax in range(2):
                    pw += W[ax, 0] * W[ax, 0] + W[ax, 1] * W[ax, 1]
                w0 += 2 * mu0 * gsum / pw
                w0 = min(max(w0, TWO_PI * f_lo), TWO_PI * f_hi)
            ia += 1
        # displacement estimate at t + horizon: invert the pre-filter gain/phase and divide by -w^2 per component
        d0 = 0.0; d1 = 0.0
        te = t + hor
        amp = 0.0
        for ax in range(2):
            dd = 0.0
            if mode == 0:
                for i in range(nb):
                    wi = TWO_PI * (f_lo + i * df)
                    a_s = W[ax, 2 * i]; a_c = W[ax, 2 * i + 1]
                    hr = Hre[i]; hi = Him[i]; h2 = hr * hr + hi * hi
                    zr = (a_c * hr - a_s * hi) / h2
                    zi = (-a_s * hr - a_c * hi) / h2
                    dd += -(zr * math.cos(wi * te) - zi * math.sin(wi * te)) / (wi * wi)
                    amp += (zr * zr + zi * zi) / (wi ** 4)
            else:
                ph_e = phi + w0 * (te - t_prev)
                for m in range(2):
                    wm = (m + 1) * w0
                    a_s = W[ax, 2 * m]; a_c = W[ax, 2 * m + 1]
                    hr, hi = _biquad_resp(bh, ah, wm * Ta)
                    lr, li = _biquad_resp(bl, al, wm * Ta)
                    Hr = hr * lr - hi * li; Hi = hr * li + hi * lr
                    h2 = Hr * Hr + Hi * Hi
                    zr = (a_c * Hr - a_s * Hi) / h2
                    zi = (-a_s * Hr - a_c * Hi) / h2
                    dd += -(zr * math.cos((m + 1) * ph_e) - zi * math.sin((m + 1) * ph_e)) / (wm * wm)
                    amp += (zr * zr + zi * zi) / (wm ** 4)
            if ax == 0:
                d0 = dd
            else:
                d1 = dd
        amp = math.sqrt(amp)
        amp_f = amp_f + (Ts / tau_amp) * (amp - amp_f)
        target = gout
        if a_hi > a_lo:
            target *= min(1.0, max(0.0, (amp_f - a_lo) / (a_hi - a_lo)))
        if mode == 1 and fgate > 0.0:
            target *= min(1.0, max(0.0, (w0 / TWO_PI - (fgate - 0.5 * fgw)) / max(fgw, 1e-9)))
        if t_prev < 0:
            target = 0.0
        g_eff = g_eff + (1.0 - math.exp(-Ts / tau_auth)) * (target - g_eff)
        out[k, 0] = _lp2_step(lb, la, g_eff * d0, zlp[0]); out[k, 1] = _lp2_step(lb, la, g_eff * d1, zlp[1])
        out_f[k] = w0 / TWO_PI; out_g[k] = g_eff


@njit(cache=True)
def _biquad_resp(b, a, wT):
    # H(e^{j wT}) of a biquad (numerator b, denominator a)
    c1 = math.cos(wT); s1 = -math.sin(wT); c2 = math.cos(2 * wT); s2 = -math.sin(2 * wT)
    nr = b[0] + b[1] * c1 + b[2] * c2; ni = b[1] * s1 + b[2] * s2
    dr = a[0] + a[1] * c1 + a[2] * c2; di = a[1] * s1 + a[2] * s2
    den = dr * dr + di * di
    return (nr * dr + ni * di) / den, (ni * dr - nr * di) / den


def _prefilter(fs, hp_hz, lp_hz):
    from scipy.signal import butter
    bh, ah = butter(2, hp_hz, btype="high", fs=fs)
    bl, al = butter(2, lp_hz, btype="low", fs=fs)
    return bh, ah, bl, al


def flc(st: Streams, params: Dict = None, mode: str = "bmflc", acc_decim: int = 2) -> Tuple[np.ndarray, Dict]:
    p = dict(FLC_DEFAULTS)
    if params:
        p.update(params)
    ta, tav, y = _block_average(st.acc_t, st.acc_av, st.acc, acc_decim)
    fs = 1.0 / float(ta[1] - ta[0])
    bh, ah, bl, al = _prefilter(fs, p["hp_hz"], p["lp_hz"])
    freqs = np.arange(p["f_lo"], p["f_hi"] + 1e-9, p["df"])[:NB_MAX]
    from scipy.signal import freqz
    H = np.ones(len(freqs), complex)
    for b, a in ((bh, ah), (bl, al)):
        H *= freqz(b, a, worN=freqs, fs=fs)[1]
    n = st.n_ticks()
    out = np.zeros((n, 2)); f = np.zeros(n); g = np.zeros(n)
    _flc_run(0 if mode == "bmflc" else 1, st.tick_t, ta, tav, np.ascontiguousarray(y), _prm(p, FLC_KEYS, FLC_DEFAULTS),
             np.asarray(bh, float), np.asarray(ah, float), np.asarray(bl, float), np.asarray(al, float),
             np.ascontiguousarray(H.real), np.ascontiguousarray(H.imag), out, f, g)
    return out, {"f_est": f, "authority": g, "params": p, "n_basis": len(freqs)}


# ======================================================================================== registry
def run_estimator(name: str, st: Streams, params: Dict = None, extra: Dict = None) -> Tuple[np.ndarray, Dict]:
    """Dispatch by name; `extra` carries inputs other than the streams (templates, calibration)."""
    if name == "kfosc":
        return kfosc(st, params)
    if name == "akf":
        return akf(st, params)
    if name in ("bmflc", "wflc"):
        return flc(st, params, mode=name)
    if name == "zero":
        return np.zeros((st.n_ticks(), 2)), {}
    if name == "learned":
        from . import learned
        return learned.estimate(st, params, extra)
    if name == "context":
        from . import context
        return context.estimate(st, params, extra)
    raise KeyError(name)
