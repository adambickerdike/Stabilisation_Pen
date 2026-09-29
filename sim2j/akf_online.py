r"""The project's AKF tremor tracker, tick by tick, with a frequency-runaway guard and a running tremor-line detector.

AKF (fusion/estimators.py, read-only): an 8-state-per-axis Kalman filter on the accelerometer (intent p, v, a with white
jerk; tremor oscillator at w and its 2nd harmonic; accelerometer bias) and the delayed page sensor (roll-back through a
history of snapshots); the frequency follows the phase rate of the larger oscillator, clamped to [wmin, wmax]; output =
tremor predicted to t + horizon x authority (frequency and amplitude gates), 2nd-order output low-pass.  fusion runs it
over whole recorded streams; `AKFOnline.tick` runs exactly the same arithmetic one 2 kHz tick at a time on the samples
that became available since the previous tick, so it can close the loop inside sim2 (and serve an RL policy).  The
equivalence is tested bit for bit against fusion.estimators.akf (tests/test_akf_online.py).

Frequency-runaway guard (new here; sim2 found the Rev H AKF's frequency estimate running away to its 14.7 Hz bound on
nearly identical inputs, docs/sim_v2.md 5.1).  Rules (ASSUMPTION values; tuned on tuning writers/seeds only):
  * runaway: the frequency estimate sits within `edge_hz` of either bound for `t_edge` s, or it disagrees with the
    tremor-line detector's line by more than `df_max` for `t_df` s while the detector's gate is open;
  * action: re-seed the frequency at the detector's line when the detector is confident (gate open), else at w0;
    reset the oscillator states' covariance to their start values; hold the tracker's output at zero authority for
    `t_hold` s and let it recover through the tracker's own authority filter.
Tremor-line detector (ai2/smoothers.detector, the algorithm and its tuned parameters DET_DEFAULTS, re-implemented
online): every 50 ms, the last 4 s of the page-sensor track that is available at that time, 250 Hz, 1.5 Hz high-pass,
Welch (2 s segments), writing floor = running median of the log spectrum; line = largest excess over the floor in
4.5-13.5 Hz; hysteresis gate (open after the ratio stayed above 5 for 0.5 s, closed after it stayed below 2.5 for 1 s,
0.2 s ramp).  Optionally the gate multiplies the tracker's authority (ai2 stage D1: never opened on tuning writers'
tremor-free writing).  Every output is a SIMULATION quantity.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
from numba import njit

from . import ROOT  # noqa: F401
from fusion import estimators as ES  # noqa: E402

NS = ES.NS
HIST = ES.HIST
TWO_PI = 2.0 * math.pi
_akf_FQ = ES._akf_FQ
_akf_predict = ES._akf_predict
_akf_update = ES._akf_update
_lp2_coef = ES._lp2_coef
_lp2_step = ES._lp2_step
_lp2_delay = ES._lp2_delay

# scalar state indices
S_W, S_TF, S_STARTED, S_LASTPOS, S_GEFF, S_AMPF, S_PHPREV, S_HAVEPH, S_TFPREV, S_AXPREV, S_AREF, S_NH, S_HOR = range(13)
NSC = 13


@njit(cache=True)
def _tick(t, Ts, acc_t, acc_av, acc, na, pos_t, pos_av, pos, pos_ok, npos, prm, x, P, F, Q, tmp, Ha, Hp, h_t, h_y, h_x,
          h_P, h_w, S, zlp, lb, la, out, guard_gain):
    """One tick of fusion.estimators._akf_run (same statements, same order) on the samples that became available."""
    qj = prm[0]; qt = prm[1]; qh = prm[2] * prm[23]; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    tau_w = prm[8]; wmin = TWO_PI * prm[9]; wmax = TWO_PI * prm[10]
    fgate = prm[11]; fgw = prm[12]; a_lo = prm[13]; a_hi = prm[14]; tau_amp = prm[15]
    tau_auth = prm[17]; acc_gd = prm[18]; gap_reset = prm[19]; gout = prm[20]; use_pos = prm[21] > 0.5
    use_acc = prm[22] > 0.5; harm = prm[23]; xtrack = prm[25] > 0.5; v_xt = prm[26]
    cap_k = prm[27]; v_slow = prm[28]; tau_ref = prm[29]
    w = S[S_W]; tf = S[S_TF]; started = S[S_STARTED] > 0.5; last_pos_t = S[S_LASTPOS]; g_eff = S[S_GEFF]
    amp_f = S[S_AMPF]; phase_prev = S[S_PHPREV]; have_phase = S[S_HAVEPH] > 0.5; tf_prev = S[S_TFPREV]
    ax_prev = int(S[S_AXPREV]); a_ref = S[S_AREF]; nh = int(S[S_NH]); hor = S[S_HOR]
    # ---------------- accelerometer samples available by now
    for ia in range(na):
        ta = acc_t[ia] - acc_gd
        if not started:
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
    # ---------------- page-sensor samples available by now (delayed: roll back and re-propagate)
    for ip in range(npos):
        if pos_ok[ip] > 0.5 and use_pos and started and nh > 0:
            tp = pos_t[ip]
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
    # ---------------- frequency tracking
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
            vx = x[0, 1]; vy = x[1, 1]
            sp = math.hypot(vx, vy)
            if sp > 1e-9:
                tx = vx / sp; ty = vy / sp
                wgt = min(1.0, sp / v_xt)
                dl = tx * d0 + ty * d1
                d0 -= wgt * dl * tx; d1 -= wgt * dl * ty
    amp = math.sqrt(amp0 * amp0 + amp1 * amp1)
    amp_f = amp_f + (Ts / tau_amp) * (amp - amp_f)
    if cap_k > 0.0 and started:
        sp_i = math.hypot(x[0, 1], x[1, 1])
        wv = max(0.0, 1.0 - sp_i / v_slow)
        a_ref = a_ref + wv * (Ts / tau_ref) * (amp - a_ref)
        mag = math.hypot(d0, d1)
        lim = cap_k * a_ref
        if mag > lim:
            sc_ = lim / mag if mag > 1e-15 else 0.0
            d0 *= sc_; d1 *= sc_
    target = gout
    if fgate > 0.0:
        f_tr = w / TWO_PI
        target *= min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-9)))
    if a_hi > a_lo:
        target *= min(1.0, max(0.0, (amp_f - a_lo) / (a_hi - a_lo)))
    if not started:
        target = 0.0
    target *= guard_gain
    g_eff = g_eff + (1.0 - math.exp(-Ts / tau_auth)) * (target - g_eff)
    out[0] = _lp2_step(lb, la, g_eff * d0, zlp[0]); out[1] = _lp2_step(lb, la, g_eff * d1, zlp[1])
    out[2] = w / TWO_PI; out[3] = g_eff; out[4] = amp_f; out[5] = d0; out[6] = d1
    S[S_W] = w; S[S_TF] = tf; S[S_STARTED] = 1.0 if started else 0.0; S[S_LASTPOS] = last_pos_t; S[S_GEFF] = g_eff
    S[S_AMPF] = amp_f; S[S_PHPREV] = phase_prev; S[S_HAVEPH] = 1.0 if have_phase else 0.0; S[S_TFPREV] = tf_prev
    S[S_AXPREV] = ax_prev; S[S_AREF] = a_ref; S[S_NH] = nh


class AKFOnline:
    """fusion's AKF, one tick at a time.  feed(): accelerometer samples (acquisition time, availability time, 2 values)
    and page-sensor samples (acquisition time, availability time, 2 values, valid flag) in arrival order; tick(t) runs
    the filter on every sample available by t and returns (d_hat (2,), f_est, authority, amplitude)."""

    def __init__(self, params: Dict, Ts: float = 0.5e-3, horizon_extra: float = 0.0):
        p = dict(ES.AKF_DEFAULTS)
        p.update(params or {})
        p["horizon"] = float(p.get("horizon", 0.0)) + horizon_extra
        self.p = p
        self.prm = ES._prm(p, ES.AKF_KEYS, ES.AKF_DEFAULTS)
        self.Ts = Ts
        self.lb, self.la = _lp2_coef(float(p["lp_hz"]), Ts)
        self.reset()

    def reset(self):
        p = self.p
        self.x = np.zeros((2, NS)); self.P = np.zeros((NS, NS))
        self.F = np.zeros((NS, NS)); self.Q = np.zeros((NS, NS)); self.tmp = np.zeros((1, NS))
        self.Ha = np.zeros(NS); self.Hp = np.zeros(NS)
        self.Hp[0] = 1.0; self.Hp[3] = 1.0; self.Hp[5] = float(p["harm"])
        self.h_t = np.zeros(HIST); self.h_y = np.zeros((HIST, 2)); self.h_x = np.zeros((HIST, 2, NS))
        self.h_P = np.zeros((HIST, NS, NS)); self.h_w = np.zeros(HIST)
        self.S = np.zeros(NSC)
        self.S[S_W] = TWO_PI * float(p["w0_hz"])
        self.S[S_LASTPOS] = -1.0
        self.S[S_HOR] = float(p["horizon"]) + _lp2_delay(float(p["lp_hz"]))
        self.zlp = np.zeros((2, 2))
        self.out = np.zeros(7)
        self.acc_q = []                  # pending (t_acq, t_av, y0, y1)
        self.pos_q = []                  # pending (t_acq, t_av, y0, y1, ok)

    def feed_acc(self, t_acq: float, t_av: float, y):
        self.acc_q.append((t_acq, t_av, float(y[0]), float(y[1])))

    def feed_pos(self, t_acq: float, t_av: float, y, ok: bool):
        self.pos_q.append((t_acq, t_av, float(y[0]), float(y[1]), 1.0 if ok else 0.0))

    def _take(self, q, t, ncol):
        k = 0
        while k < len(q) and q[k][1] <= t:
            k += 1
        if k == 0:
            return np.zeros(0), np.zeros(0), np.zeros((0, 2)), np.zeros(0), 0
        a = np.array(q[:k])
        del q[:k]
        return (np.ascontiguousarray(a[:, 0]), np.ascontiguousarray(a[:, 1]), np.ascontiguousarray(a[:, 2:4]),
                np.ascontiguousarray(a[:, 4]) if ncol == 5 else np.zeros(k), k)

    def tick(self, t: float, guard_gain: float = 1.0):
        at, aav, ay, _, na = self._take(self.acc_q, t, 4)
        pt, pav, py, pok, npos = self._take(self.pos_q, t, 5)
        _tick(t, self.Ts, at, aav, ay, na, pt, pav, py, pok, npos, self.prm, self.x, self.P, self.F, self.Q, self.tmp,
              self.Ha, self.Hp, self.h_t, self.h_y, self.h_x, self.h_P, self.h_w, self.S, self.zlp, self.lb, self.la,
              self.out, float(guard_gain))
        return self.out

    # ---- guard hooks
    @property
    def f_est(self) -> float:
        return self.S[S_W] / TWO_PI

    def reseed(self, f_hz: float):
        """Re-seed the frequency and reset the oscillator states' covariance to their start values (guard action)."""
        self.S[S_W] = TWO_PI * float(f_hz)
        P = self.P
        for i in (3, 4, 5, 6):
            for j in range(NS):
                P[i, j] = 0.0
                P[j, i] = 0.0
        P[3, 3] = 1e-7; P[4, 4] = 1e-7; P[5, 5] = 1e-8; P[6, 6] = 1e-8
        self.x[:, 3:7] = 0.0
        self.S[S_HAVEPH] = 0.0


def run_batch_equivalent(st, params: Dict, acc_decim: int = 2):
    """Run AKFOnline over fusion Streams exactly as fusion.estimators.akf does (for the bit-exact test)."""
    ta, tav, y = ES._block_average(st.acc_t, st.acc_av, st.acc, acc_decim)
    n = st.n_ticks()
    Ts = float(st.tick_t[1] - st.tick_t[0])
    ak = AKFOnline(params, Ts=Ts)
    out = np.zeros((n, 2)); f = np.zeros(n); g = np.zeros(n); amp = np.zeros(n)
    ia = 0; ip = 0
    for k in range(n):
        t = st.tick_t[k]
        while ia < len(ta) and tav[ia] <= t:
            ak.feed_acc(ta[ia], tav[ia], y[ia]); ia += 1
        while ip < len(st.pos_t) and st.pos_av[ip] <= t:
            ak.feed_pos(st.pos_t[ip], st.pos_av[ip], st.pos[ip], st.pos_ok[ip] > 0.5); ip += 1
        o = ak.tick(t)
        out[k] = o[0:2]; f[k] = o[2]; g[k] = o[3]; amp[k] = o[4]
    return out, {"f_est": f, "authority": g, "amp": amp}


# ================================================================================================ tremor-line detector
@dataclass
class DetParams:
    win: float = 4.0
    seg: float = 2.0
    fs: float = 250.0
    band_lo: float = 4.5
    band_hi: float = 13.5
    hp_hz: float = 1.5
    every: float = 0.05
    min_win: float = 2.0
    r_on: float = 5.0
    r_off: float = 2.5
    t_on: float = 0.5
    t_off: float = 1.0
    ramp: float = 0.2
    margin: float = 2.0             # line amplitude: excess over margin x floor within half_width of f and 2f (ai2)
    half_width: float = 1.5
    label: str = "ai2/smoothers.DET_DEFAULTS (tuned by study L on tuning writers; algorithm re-implemented online)"


class LineDetector:
    """ai2's running tremor-line detector, online: push page samples as they become available; update() every `every`
    seconds returns (gate, f_line, ratio)."""

    def __init__(self, prm: Optional[DetParams] = None):
        from scipy.signal import butter
        self.p = prm or DetParams()
        self.sos = butter(2, self.p.hp_hz, btype="high", fs=self.p.fs, output="sos")
        self.buf = deque()
        self.t_next = None
        self.state = False
        self.c_on = 0
        self.c_off = 0
        self.gate = 0.0
        self.f_line = 0.0
        self.ratio = 0.0
        self.amp = 0.0
        self.t_first = None
        self.n_on = max(1, int(round(self.p.t_on / self.p.every)))
        self.n_off = max(1, int(round(self.p.t_off / self.p.every)))

    def push(self, t_acq: float, y, ok: bool):
        if not ok:
            return
        if self.t_first is None:
            self.t_first = t_acq
        self.buf.append((t_acq, float(y[0]), float(y[1])))
        while self.buf and self.buf[0][0] < t_acq - self.p.win - 0.1:
            self.buf.popleft()

    def update(self, t: float):
        from scipy.signal import sosfiltfilt, welch
        from ai2.smoothers import _floor
        p = self.p
        if self.t_first is None or t - self.t_first < p.min_win or len(self.buf) < 16:
            return self.gate, self.f_line, self.ratio
        if self.t_next is not None and t < self.t_next:
            return self.gate, self.f_line, self.ratio
        self.t_next = t + p.every
        a = np.array(self.buf)
        tp, yp = a[:, 0], a[:, 1:]
        t1 = tp[-1]
        tg = np.arange(max(tp[0], t1 - p.win), t1, 1.0 / p.fs)
        nseg = int(round(p.seg * p.fs))
        if len(tg) < nseg + 8:
            return self.gate, self.f_line, self.ratio
        yg = np.column_stack([np.interp(tg, tp, yp[:, 0]), np.interp(tg, tp, yp[:, 1])])
        x = sosfiltfilt(self.sos, yg - yg.mean(0), axis=0, padlen=min(len(yg) - 1, 3 * nseg))
        f, Pw = welch(x, fs=p.fs, nperseg=nseg, noverlap=nseg // 2, axis=0, detrend="constant")
        Pw = Pw.sum(axis=1)
        fl = _floor(f, Pw)
        r = Pw / np.maximum(fl, 1e-30)
        m = (f >= p.band_lo) & (f <= p.band_hi)
        k = int(np.flatnonzero(m)[np.argmax(r[m])])
        fh = float(f[k])
        if 0 < k < len(f) - 1:
            y0, y1, y2 = np.log(r[k - 1:k + 2])
            den = y0 - 2 * y1 + y2
            if abs(den) > 1e-12:
                fh = float(f[k] + float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) * (f[1] - f[0]))
        self.f_line = fh
        self.ratio = float(r[k])
        exc = np.maximum(Pw - p.margin * fl, 0.0)
        inb = (np.abs(f - fh) <= p.half_width) | (np.abs(f - 2 * fh) <= p.half_width)
        self.amp = math.sqrt(2.0 * float(np.sum(exc[inb])) * float(f[1] - f[0]))
        if not self.state:
            self.c_on = self.c_on + 1 if self.ratio > p.r_on else 0
            if self.c_on >= self.n_on:
                self.state = True
                self.c_off = 0
        else:
            self.c_off = self.c_off + 1 if self.ratio < p.r_off else 0
            if self.c_off >= self.n_off:
                self.state = False
                self.c_on = 0
        a_ = min(1.0, p.every / max(p.ramp, 1e-9))
        self.gate = min(1.0, self.gate + a_) if self.state else max(0.0, self.gate - a_)
        return self.gate, self.f_line, self.ratio


# ================================================================================================ runaway guard
@dataclass
class GuardParams:
    on: bool = True
    edge_hz: float = 0.8            # "at the bound": within this of wmin or wmax
    t_edge: float = 0.25            # s at the bound before acting
    df_max: float = 2.0             # Hz disagreement with the detector's line (gate open)
    t_df: float = 0.5               # s of disagreement before acting
    t_hold: float = 0.2             # s of zero authority after a re-seed
    lock_hz: float = 1.0            # while the detector's gate is open, the AKF frequency is kept within +-lock_hz of
                                    # the detector's line (0: no lock)
    use_det_gate: bool = True       # multiply the authority by the detector gate (ai2 stage D1: the gate never opened
                                    # on the tuning writers' tremor-free writing)
    label: str = "ASSUMPTION (rules of this study; values fixed on tuning writers/seeds before the test)"


class GuardedTracker:
    """AKFOnline + LineDetector + the runaway guard.  step(t) returns the disturbance estimate (2,), and keeps the
    diagnostics (frequency, authority, detector gate and line, guard events)."""

    def __init__(self, akf_params: Dict, Ts: float = 0.5e-3, horizon_extra: float = 0.0,
                 guard: Optional[GuardParams] = None, det: Optional[DetParams] = None):
        self.akf = AKFOnline(akf_params, Ts=Ts, horizon_extra=horizon_extra)
        self.det = LineDetector(det)
        self.g = guard or GuardParams()
        self.Ts = Ts
        self.t_edge = 0.0
        self.t_df = 0.0
        self.hold_until = -1.0
        self.events = []
        self.wmin = float(self.akf.p["wmin_hz"])
        self.wmax = float(self.akf.p["wmax_hz"])
        self.w0 = float(self.akf.p["w0_hz"])
        self.last = np.zeros(7)
        self.det_gate = 0.0
        self.n_lock = 0

    def feed_acc(self, t_acq, t_av, y):
        self.akf.feed_acc(t_acq, t_av, y)

    def feed_pos(self, t_acq, t_av, y, ok, ok_det=None):
        """ok: the page sensor's validity (the AKF uses every valid sample); ok_det: the detector's input gate (the
        firmware passes 'valid and the ball on the paper': the detector sees the writing trace, as ai2 designed it on
        page samples cut off at 0.8 mm lift; the Rev J sensor stays valid to 2 mm, and the air moves it then sees
        tripped the detector on tremor-free writing in a tuning run)."""
        self.akf.feed_pos(t_acq, t_av, y, ok)
        self.det.push(t_acq, y, ok if ok_det is None else ok_det)

    def step(self, t: float) -> np.ndarray:
        g = self.g
        det_gate, f_line, ratio = self.det.update(t)
        self.det_gate = det_gate
        gain = 1.0
        if g.on:
            f = self.akf.f_est
            at_edge = (f >= self.wmax - g.edge_hz) or (f <= self.wmin + g.edge_hz)
            self.t_edge = self.t_edge + self.Ts if at_edge else 0.0
            disagree = det_gate > 0.5 and abs(f - f_line) > g.df_max
            self.t_df = self.t_df + self.Ts if disagree else 0.0
            if self.t_edge >= g.t_edge or self.t_df >= g.t_df:
                f_new = f_line if det_gate > 0.5 else self.w0
                self.akf.reseed(f_new)
                self.events.append((t, f, f_new, "edge" if self.t_edge >= g.t_edge else "disagree"))
                self.t_edge = 0.0
                self.t_df = 0.0
                self.hold_until = t + g.t_hold
            if t < self.hold_until:
                gain = 0.0
        if g.use_det_gate:
            gain *= det_gate
        self.last = self.akf.tick(t, gain)
        if g.on and g.lock_hz > 0 and det_gate > 0.5 and f_line > 0:
            w = self.akf.S[S_W]
            lo, hi = TWO_PI * (f_line - g.lock_hz), TWO_PI * (f_line + g.lock_hz)
            if w < lo or w > hi:
                self.akf.S[S_W] = min(max(w, lo), hi)
                self.n_lock += 1
        return self.last[0:2]


def frozen_guard() -> GuardParams:
    """The guard frozen in results/sim2j/rules.json (chosen on the tuning writers and seeds before any test run), else
    the default GuardParams()."""
    import json
    import os
    from . import RESULTS
    try:
        d = json.load(open(os.path.join(RESULTS, "rules.json")))
        return GuardParams(**d["guard"]["params"])
    except Exception:
        return GuardParams()


def frozen_det() -> DetParams:
    """The tremor-line detector parameters frozen with the guard in results/sim2j/rules.json, else ai2's defaults."""
    import json
    import os
    from . import RESULTS
    try:
        d = json.load(open(os.path.join(RESULTS, "rules.json")))
        return DetParams(**d["guard"]["det_params"])
    except Exception:
        return DetParams()


# ================================================================================================ ai2's gated listening
def listening_params() -> Dict:
    """ai2's listening tremor model (DEC-042; ai2/delayed.TREMOR_DEFAULTS updated with results/ai2/ai2.json
    test_settings.tremor) in fusion's AKF parameter format, with the AKF's own output gates off (the detector and the
    amplitude gate decide) and a negligible output low-pass (the forward filter's prediction is used directly)."""
    import json
    import os
    from ai2 import delayed as DL
    p = dict(DL.TREMOR_DEFAULTS)
    try:
        from . import ROOT as _R
        d = json.load(open(os.path.join(_R, "results", "ai2", "ai2.json")))
        p.update(d["test_settings"]["tremor"])
    except Exception:
        pass
    out = {k: float(p[k]) for k in ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz",
                                    "wmax_hz", "harm", "gap_reset")}
    out.update({"f_gate": 0.0, "a_lo": 0.0, "a_hi": 0.0, "g": 1.0, "cap_k": 0.0, "xtrack": 0.0, "horizon": 0.0,
                "lp_hz": 1000.0, "tau_auth": 0.05, "tau_amp": 0.3})
    return out


def listening_det() -> DetParams:
    """ai2's detector for the gated tracker (ai2/delayed.DET_DEFAULTS + test_settings.det: 4 s before the first update)."""
    from ai2 import delayed as DL
    d = DL.DET_DEFAULTS
    return DetParams(win=d["win"], seg=d["seg"], every=d["every"], min_win=d["min_win"], r_on=d["r_on"],
                     r_off=d["r_off"], t_on=d["t_on"], t_off=d["t_off"], ramp=d["ramp"])


class GatedListening:
    """ai2's gated listening tracker (DEC-042), online in the firmware: the tremor-line detector's hysteresis gate x an
    amplitude gate on the detector's line amplitude (fades in between amp_lo 0.15 mm and amp_hi 0.35 mm) weights the
    listening estimate (a second AKF instance with ai2's listening tremor model, its prediction to t + the servo delay);
    the complement goes to the fallback tracker: the Rev H tracker as built (ai2's definition) or the guarded tracker.
    Same interface as GuardedTracker (feed_acc, feed_pos, step, last, det, det_gate, events, n_lock)."""

    def __init__(self, revh_params: Dict, Ts: float = 0.5e-3, horizon_extra: float = 0.0,
                 fallback_guard: Optional[GuardParams] = None, fallback_det: Optional[DetParams] = None,
                 det: Optional[DetParams] = None, amp_lo: float = 0.15e-3, amp_hi: float = 0.35e-3,
                 listen: Optional[Dict] = None):
        g = fallback_guard or GuardParams(on=False, use_det_gate=False, lock_hz=0.0)
        self.fb = GuardedTracker(revh_params, Ts=Ts, horizon_extra=horizon_extra, guard=g, det=fallback_det or det)
        lp = dict(listen or listening_params())
        lp["acc_gd"] = float(revh_params.get("acc_gd", lp.get("acc_gd", 1.04e-3)))
        self.listen = AKFOnline(lp, Ts=Ts, horizon_extra=horizon_extra)
        self.det = LineDetector(det or listening_det())
        self.amp_lo, self.amp_hi = amp_lo, amp_hi
        self.Ts = Ts
        self.last = np.zeros(7)
        self.det_gate = 0.0
        self.g_listen = 0.0
        self.events = self.fb.events

    @property
    def n_lock(self):
        return self.fb.n_lock

    @property
    def akf(self):
        return self.fb.akf

    def feed_acc(self, t_acq, t_av, y):
        self.fb.feed_acc(t_acq, t_av, y)
        self.listen.feed_acc(t_acq, t_av, y)

    def feed_pos(self, t_acq, t_av, y, ok, ok_det=None):
        self.fb.feed_pos(t_acq, t_av, y, ok, ok_det=ok_det)
        self.listen.feed_pos(t_acq, t_av, y, ok)
        self.det.push(t_acq, y, ok if ok_det is None else ok_det)

    def weight(self) -> float:
        g = self.det.gate
        if self.amp_hi > self.amp_lo:
            g *= min(1.0, max(0.0, (self.det.amp - self.amp_lo) / (self.amp_hi - self.amp_lo)))
        return g

    def step(self, t: float) -> np.ndarray:
        d_fb = self.fb.step(t)
        self.det.update(t)
        self.det_gate = self.det.gate
        ol = self.listen.tick(t)
        g = self.weight()
        self.g_listen = g
        o = self.last
        fo = self.fb.last
        o[0] = g * ol[5] + (1.0 - g) * d_fb[0]
        o[1] = g * ol[6] + (1.0 - g) * d_fb[1]
        o[2] = ol[2] if g > 0.5 else fo[2]
        o[3] = g + (1.0 - g) * fo[3]
        o[4] = ol[4] if g > 0.5 else fo[4]
        o[5] = ol[5]; o[6] = ol[6]                     # ungated listening estimate (for an arbiter)
        self.d_fb = d_fb
        return o[0:2]


def frozen_tracker() -> str:
    """The tracker family frozen in results/sim2j/rules.json ('guarded' | 'gl' | 'glg'), else 'guarded'."""
    import json
    import os
    from . import RESULTS
    try:
        d = json.load(open(os.path.join(RESULTS, "rules.json")))
        return str(d["guard"].get("tracker", "guarded"))
    except Exception:
        return "guarded"
