r"""AI-context estimator: the phone's letter template as an intent prior inside the Kalman filter (SIMULATION).

The phone predicts the next letters, synthesises them in the writer's style and sends template
segments (proposed ICD record 0x06).  The old guided mode pulled the nib toward the template, so
every template error (about 300 um for a correctly predicted letter) became ink error.  Here the
template never commands the stage.  It enters the estimator as a pseudo-measurement of the
*intended* path:

    z_T = n . T(s*)  =  n . p  -  n . b_T  +  e_T,        R_T = sigma_T^2 / c_hat

n: unit normal of the template at the point s* nearest to the predicted intent position (progress-
constrained search, re-acquired at each touchdown); p: intent position state; b_T: a slowly varying
template-bias state (offset, placement) re-initialised at each new letter; c_hat: the predictor's
calibrated confidence (letters below c_min send no template).  Only the cross-track component is
used, because the template's timing is unknown.  The filter state is otherwise the acceleration-
domain Kalman filter of fusion.estimators.akf (intent p, v, a; tremor oscillator + 2nd harmonic;
accelerometer bias) on both axes jointly (18 states: the template couples x and y).  The stage then
cancels only the estimated tremor; a wrong or badly placed template can bias the tremor estimate
only through its tremor-band content, and it is gated: an update whose normalised innovation
exceeds `gate` is skipped, and a letter's template is dropped for the rest of the letter once the
cross-track residual has stayed above `drop_um` for `drop_s` (rule T5 of docs/ai_guidance.md s7.3).

Also here: the template-error spectrum (the hypothesis that template errors are mostly low-frequency
offset, scale and slant, so their 3-15 Hz content is far below their ~300 um total) and the
closed-loop evaluation on the aiguide writers.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from numba import njit

from .estimators import AKF_DEFAULTS, _block_average, _lp2_coef, _lp2_delay, _lp2_step
from .sensors import Streams

TWO_PI = 2.0 * math.pi
NC = 18
HISTC = 256
# state index
IPX, IVX, IAX, IPY, IVY, IAY = 0, 1, 2, 3, 4, 5
IC1X, IS1X, IC1Y, IS1Y, IC2X, IS2X, IC2Y, IS2Y = 6, 7, 8, 9, 10, 11, 12, 13
IBAX, IBAY, ITBX, ITBY = 14, 15, 16, 17

CTX_KEYS = ("qj", "qt", "qh", "qb", "ra", "rp", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz", "f_gate", "f_gate_w",
            "a_lo", "a_hi", "tau_amp", "horizon", "tau_auth", "acc_gd", "gap_reset", "g", "harm",
            "sigma_t", "q_tb", "tb0", "gate", "drop_um", "drop_s", "c_min", "t_rate", "win_back", "win_fwd", "use_tpl", "win_reacq",
            "lp_hz", "tb_letter", "drop_gated_s", "tpl_mode", "xtrack", "v_xt", "cap_k", "v_slow", "tau_ref")
CTX_DEFAULTS = dict(AKF_DEFAULTS)
CTX_DEFAULTS.update({"sigma_t": 60e-6, "q_tb": (100e-6) ** 2, "tb0": 300e-6, "gate": 4.0, "drop_um": 250.0, "drop_s": 0.06,
                     "c_min": 0.5, "t_rate": 250.0, "win_back": 10.0, "win_fwd": 80.0, "use_tpl": 1.0, "win_reacq": 1500.0,
                     "tb_letter": -1.0, "drop_gated_s": 0.0, "tpl_mode": 0.0, "xtrack": 0.0, "v_xt": 5e-3,
                     "cap_k": 0.0, "v_slow": 3e-3, "tau_ref": 0.5})


# ------------------------------------------------------------------ template geometry for the pen
def template_arrays(letters, conf_by_letter: Sequence[float], step: float = 20e-6):
    """Dense template polyline in writing order: points, unit normals, stroke id, letter id, confidence."""
    pts, nrm, sid, lid, cf = [], [], [], [], []
    s_global = 0
    for li, L in enumerate(letters):
        c = float(conf_by_letter[li]) if conf_by_letter is not None else 1.0
        for s in L.strokes:
            s = np.asarray(s, float)
            seg = np.hypot(*np.diff(s, axis=0).T)
            Ls = np.r_[0.0, np.cumsum(seg)]
            if Ls[-1] <= 0:
                continue
            u = np.linspace(0.0, Ls[-1], max(2, int(Ls[-1] / step) + 1))
            P = np.column_stack([np.interp(u, Ls, s[:, 0]), np.interp(u, Ls, s[:, 1])])
            tg = np.gradient(P, axis=0)
            tn = np.linalg.norm(tg, axis=1, keepdims=True)
            tg = tg / np.maximum(tn, 1e-15)
            pts.append(P); nrm.append(np.column_stack([-tg[:, 1], tg[:, 0]]))
            sid.append(np.full(len(P), s_global)); lid.append(np.full(len(P), li)); cf.append(np.full(len(P), c))
            s_global += 1
    if not pts:
        z = np.zeros((0, 2))
        return {"xy": z, "nrm": z, "sid": np.zeros(0, np.int64), "lid": np.zeros(0, np.int64), "conf": np.zeros(0)}
    return {"xy": np.ascontiguousarray(np.vstack(pts)), "nrm": np.ascontiguousarray(np.vstack(nrm)),
            "sid": np.concatenate(sid).astype(np.int64), "lid": np.concatenate(lid).astype(np.int64),
            "conf": np.concatenate(cf)}


# ------------------------------------------------------------------ joint Kalman filter
@njit(cache=True)
def _ctx_FQ(dt, w, tau_d, qj, qt, qh, qb, qtb, F, Q):
    for i in range(NC):
        for j in range(NC):
            F[i, j] = 0.0
            Q[i, j] = 0.0
    T2 = dt * dt; T3 = T2 * dt; T4 = T3 * dt; T5 = T4 * dt
    for b in (0, 3):
        F[b, b] = 1.0; F[b, b + 1] = dt; F[b, b + 2] = 0.5 * T2
        F[b + 1, b + 1] = 1.0; F[b + 1, b + 2] = dt
        F[b + 2, b + 2] = 1.0
        Q[b, b] = qj * T5 / 20.0; Q[b, b + 1] = qj * T4 / 8.0; Q[b, b + 2] = qj * T3 / 6.0
        Q[b + 1, b] = Q[b, b + 1]; Q[b + 1, b + 1] = qj * T3 / 3.0; Q[b + 1, b + 2] = qj * T2 / 2.0
        Q[b + 2, b] = Q[b, b + 2]; Q[b + 2, b + 1] = Q[b + 1, b + 2]; Q[b + 2, b + 2] = qj * dt
    rd = math.exp(-dt / tau_d)
    c = math.cos(w * dt); s = math.sin(w * dt)
    c2 = math.cos(2 * w * dt); s2 = math.sin(2 * w * dt)
    for (i0, cc, ss, qq) in ((IC1X, c, s, qt), (IC1Y, c, s, qt), (IC2X, c2, s2, qh), (IC2Y, c2, s2, qh)):
        F[i0, i0] = rd * cc; F[i0, i0 + 1] = rd * ss; F[i0 + 1, i0] = -rd * ss; F[i0 + 1, i0 + 1] = rd * cc
        Q[i0, i0] = qq * dt; Q[i0 + 1, i0 + 1] = qq * dt
    F[IBAX, IBAX] = 1.0; F[IBAY, IBAY] = 1.0; F[ITBX, ITBX] = 1.0; F[ITBY, ITBY] = 1.0
    Q[IBAX, IBAX] = qb * dt; Q[IBAY, IBAY] = qb * dt
    Q[ITBX, ITBX] = qtb * dt; Q[ITBY, ITBY] = qtb * dt


@njit(cache=True)
def _ctx_predict(x, P, F, Q, FP, tmp):
    for i in range(NC):
        s = 0.0
        for j in range(NC):
            s += F[i, j] * x[j]
        tmp[i] = s
    for i in range(NC):
        x[i] = tmp[i]
    for i in range(NC):
        for j in range(NC):
            s = 0.0
            for k in range(NC):
                s += F[i, k] * P[k, j]
            FP[i, j] = s
    for i in range(NC):
        for j in range(i, NC):
            s = 0.0
            for k in range(NC):
                s += FP[i, k] * F[j, k]
            P[i, j] = s + Q[i, j]
            P[j, i] = P[i, j]


@njit(cache=True)
def _ctx_update(x, P, H, y, R, gate):
    """Scalar update; returns the normalised innovation; skipped (returns -nis) if it exceeds the gate."""
    PH = np.empty(NC)
    for i in range(NC):
        s = 0.0
        for j in range(NC):
            s += P[i, j] * H[j]
        PH[i] = s
    S = R
    for i in range(NC):
        S += H[i] * PH[i]
    e = y
    for i in range(NC):
        e -= H[i] * x[i]
    nis = e * e / S
    if gate > 0 and nis > gate * gate:
        return -nis
    for i in range(NC):
        x[i] += PH[i] / S * e
    for i in range(NC):
        for j in range(NC):
            P[i, j] -= PH[i] * PH[j] / S
    return nis


@njit(cache=True)
def _ctx_run(tick_t, acc_t, acc_av, acc, pos_t, pos_av, pos, pos_ok, con_av, con, txy, tnrm, tsid, tlid, tconf,
             prm, out, out_f, out_g, out_amp, out_diag):
    qj = prm[0]; qt = prm[1]; harm = prm[21]; qh = prm[2] * harm; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    w = TWO_PI * prm[7]; tau_w = prm[8]; wmin = TWO_PI * prm[9]; wmax = TWO_PI * prm[10]
    fgate = prm[11]; fgw = prm[12]; a_lo = prm[13]; a_hi = prm[14]; tau_amp = prm[15]; hor = prm[16]
    tau_auth = prm[17]; acc_gd = prm[18]; gap_reset = prm[19]; gout = prm[20]
    sig_t = prm[22]; q_tb = prm[23]; tb0 = prm[24]; gate = prm[25]; drop_m = prm[26] * 1e-6; drop_s = prm[27]
    c_min = prm[28]; t_rate = prm[29]; wb = int(prm[30]); wf = int(prm[31]); use_tpl = prm[32] > 0.5; wre = int(prm[33])
    lp_hz = prm[34]; tb_letter = prm[35]; drop_gs = prm[36]; tpl_mode = int(prm[37]); xtrack = int(prm[38]); v_xt = prm[39]
    cap_k = prm[40]; v_slow = prm[41]; tau_ref = prm[42]
    a_ref = 0.0
    n = len(tick_t)
    Ts = tick_t[1] - tick_t[0]
    lb, la = _lp2_coef(lp_hz, Ts)
    zlp = np.zeros((2, 2))
    hor = hor + _lp2_delay(lp_hz)
    na = len(acc_t); npos = len(pos_t); nc = len(con_av); ntp = txy.shape[0]
    x = np.zeros(NC); P = np.zeros((NC, NC))
    F = np.zeros((NC, NC)); Q = np.zeros((NC, NC)); FP = np.zeros((NC, NC)); tmp = np.zeros(NC)
    H = np.zeros(NC)
    h_t = np.zeros(HISTC); h_y = np.zeros((HISTC, 2)); h_x = np.zeros((HISTC, NC)); h_P = np.zeros((HISTC, NC, NC))
    h_w = np.zeros(HISTC)
    nh = 0
    ia = 0; ip = 0; ic = 0
    tf = 0.0
    started = False
    last_pos_t = -1.0
    g_eff = 0.0; amp_f = 0.0
    phase_prev = 0.0; have_phase = False; tf_prev = 0.0; ax_prev = 0
    in_con = False; was_con = False
    prog = -1; reacq = True
    cur_letter = -1
    bad_since = -1.0
    gated_since = -1.0
    dropped_letter = -2
    last_tpl_t = -1.0
    n_tpl = 0; n_gated = 0; n_drop = 0
    tpl_on = False
    for k in range(n):
        t = tick_t[k]
        while ic < nc and con_av[ic] <= t:
            in_con = con[ic] > 0.5
            ic += 1
        if in_con and not was_con:
            reacq = True
        was_con = in_con
        # ---------------- accelerometer
        while ia < na and acc_av[ia] <= t:
            ta = acc_t[ia] - acc_gd
            if not started:
                started = True
                tf = ta
                for i in range(NC):
                    P[i, i] = 1e-12
                P[IPX, IPX] = 1e-6; P[IPY, IPY] = 1e-6; P[IVX, IVX] = 1e-4; P[IVY, IVY] = 1e-4
                P[IAX, IAX] = 1.0; P[IAY, IAY] = 1.0
                for i in (IC1X, IS1X, IC1Y, IS1Y):
                    P[i, i] = 1e-7
                for i in (IC2X, IS2X, IC2Y, IS2Y):
                    P[i, i] = 1e-8
                P[IBAX, IBAX] = 0.05; P[IBAY, IBAY] = 0.05
                P[ITBX, ITBX] = tb0 * tb0; P[ITBY, ITBY] = tb0 * tb0
            dt = ta - tf
            if dt > 0:
                _ctx_FQ(dt, w, tau_d, qj, qt, qh, qb, q_tb, F, Q)
                _ctx_predict(x, P, F, Q, FP, tmp)
                tf = ta
            for axx in range(2):
                for i in range(NC):
                    H[i] = 0.0
                if axx == 0:
                    H[IAX] = 1.0; H[IC1X] = -w * w; H[IC2X] = -4.0 * w * w * harm; H[IBAX] = 1.0
                else:
                    H[IAY] = 1.0; H[IC1Y] = -w * w; H[IC2Y] = -4.0 * w * w * harm; H[IBAY] = 1.0
                _ctx_update(x, P, H, acc[ia, axx], ra, 0.0)
            j = nh % HISTC
            h_t[j] = tf; h_y[j, 0] = acc[ia, 0]; h_y[j, 1] = acc[ia, 1]; h_w[j] = w
            for i in range(NC):
                h_x[j, i] = x[i]
                for q in range(NC):
                    h_P[j, i, q] = P[i, q]
            nh += 1
            ia += 1
        # ---------------- page sensor (delayed) + template pseudo-measurement at the same instant
        while ip < npos and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5 and started and nh > 0:
                tp = pos_t[ip]
                lo = max(0, nh - HISTC)
                jj = nh - 1
                while jj >= lo and h_t[jj % HISTC] > tp:
                    jj -= 1
                if jj >= lo:
                    s = jj % HISTC
                    for i in range(NC):
                        x[i] = h_x[s, i]
                        for q in range(NC):
                            P[i, q] = h_P[s, i, q]
                    tf = h_t[s]
                    wr = h_w[s]
                    dt = tp - tf
                    if dt > 0:
                        _ctx_FQ(dt, wr, tau_d, qj, qt, qh, qb, q_tb, F, Q)
                        _ctx_predict(x, P, F, Q, FP, tmp)
                        tf = tp
                    if last_pos_t < 0 or tp - last_pos_t > gap_reset:
                        # re-anchor the intent position after a gap (pen lifted)
                        for axx in range(2):
                            ip_ = IPX if axx == 0 else IPY
                            ic_ = IC1X if axx == 0 else IC1Y
                            ic2 = IC2X if axx == 0 else IC2Y
                            pred = x[ip_] + x[ic_] + harm * x[ic2]
                            x[ip_] += pos[ip, axx] - pred
                            for q in range(NC):
                                P[ip_, q] = 0.0
                                P[q, ip_] = 0.0
                            P[ip_, ip_] = rp
                    else:
                        for axx in range(2):
                            for i in range(NC):
                                H[i] = 0.0
                            if axx == 0:
                                H[IPX] = 1.0; H[IC1X] = 1.0; H[IC2X] = harm
                            else:
                                H[IPY] = 1.0; H[IC1Y] = 1.0; H[IC2Y] = harm
                            _ctx_update(x, P, H, pos[ip, axx], rp, 0.0)
                    last_pos_t = tp
                    # ---- template (cross-track) pseudo-measurement
                    if use_tpl and ntp > 1 and in_con and (last_tpl_t < 0 or tp - last_tpl_t >= 1.0 / t_rate):
                        last_tpl_t = tp
                        px = x[IPX]; py = x[IPY]
                        if reacq or prog < 0:
                            j0 = max(0, prog); j1 = min(ntp, (prog if prog >= 0 else 0) + wre)
                        else:
                            j0 = max(0, prog - wb); j1 = min(ntp, prog + wf)
                        best = 1e30; bj = -1
                        for q in range(j0, j1):
                            dx = txy[q, 0] - px; dy = txy[q, 1] - py
                            dd = dx * dx + dy * dy
                            if dd < best:
                                best = dd; bj = q
                        if bj >= 0:
                            if reacq:
                                reacq = False
                            prog = bj
                            li = tlid[bj]
                            if li != cur_letter:
                                cur_letter = li
                                bad_since = -1.0
                                gated_since = -1.0
                                if tb_letter < 0.0:
                                    # a new letter: new placement offset (reset)
                                    for q in range(NC):
                                        P[ITBX, q] = 0.0; P[q, ITBX] = 0.0; P[ITBY, q] = 0.0; P[q, ITBY] = 0.0
                                    P[ITBX, ITBX] = tb0 * tb0; P[ITBY, ITBY] = tb0 * tb0
                                    x[ITBX] = 0.0; x[ITBY] = 0.0
                                else:
                                    # a new letter: keep the common offset, add the letter's own placement uncertainty
                                    P[ITBX, ITBX] += tb_letter * tb_letter; P[ITBY, ITBY] += tb_letter * tb_letter
                            cf = tconf[bj]
                            tpl_on = cf >= c_min and li != dropped_letter and in_con
                            if cf >= c_min and li != dropped_letter:
                                nx = tnrm[bj, 0]; ny = tnrm[bj, 1]
                                resid = nx * (px - txy[bj, 0]) + ny * (py - txy[bj, 1])
                                # rule T5: persistent cross-track mismatch drops the letter's template
                                if abs(resid - (nx * x[ITBX] + ny * x[ITBY])) > drop_m:
                                    if bad_since < 0:
                                        bad_since = tp
                                    elif tp - bad_since > drop_s:
                                        dropped_letter = li
                                        n_drop += 1
                                else:
                                    bad_since = -1.0
                                if dropped_letter != li:
                                    for i in range(NC):
                                        H[i] = 0.0
                                    if tpl_mode == 0:
                                        # intent-referenced: n.T = n.p - n.b_T
                                        H[IPX] = nx; H[IPY] = ny; H[ITBX] = -nx; H[ITBY] = -ny
                                        z = nx * txy[bj, 0] + ny * txy[bj, 1]
                                    else:
                                        # tremor-referenced: the page point's cross-track distance from the template is
                                        # tremor + template bias, n.(y_p - T) = n.c + n.b_T (the writing's own shape removed)
                                        H[IC1X] = nx; H[IC1Y] = ny; H[IC2X] = nx * harm; H[IC2Y] = ny * harm
                                        H[ITBX] = nx; H[ITBY] = ny
                                        z = nx * (pos[ip, 0] - txy[bj, 0]) + ny * (pos[ip, 1] - txy[bj, 1])
                                    r = _ctx_update(x, P, H, z, sig_t * sig_t / max(cf, 1e-3), gate)
                                    if r < 0:
                                        n_gated += 1
                                        # persistent gating also drops the letter's template (rule T5, innovation form)
                                        if gated_since < 0:
                                            gated_since = tp
                                        elif drop_gs > 0 and tp - gated_since > drop_gs:
                                            dropped_letter = li
                                            n_drop += 1
                                    else:
                                        n_tpl += 1
                                        gated_since = -1.0
                    # ---- re-apply the later accelerometer samples
                    for q in range(jj + 1, nh):
                        s2 = q % HISTC
                        wq = h_w[s2]
                        dt = h_t[s2] - tf
                        if dt > 0:
                            _ctx_FQ(dt, wq, tau_d, qj, qt, qh, qb, q_tb, F, Q)
                            _ctx_predict(x, P, F, Q, FP, tmp)
                            tf = h_t[s2]
                        for axx in range(2):
                            for i in range(NC):
                                H[i] = 0.0
                            if axx == 0:
                                H[IAX] = 1.0; H[IC1X] = -wq * wq; H[IC2X] = -4.0 * wq * wq * harm; H[IBAX] = 1.0
                            else:
                                H[IAY] = 1.0; H[IC1Y] = -wq * wq; H[IC2Y] = -4.0 * wq * wq * harm; H[IBAY] = 1.0
                            _ctx_update(x, P, H, h_y[s2, axx], ra, 0.0)
                        for i in range(NC):
                            h_x[s2, i] = x[i]
                            for r2 in range(NC):
                                h_P[s2, i, r2] = P[i, r2]
            ip += 1
        # ---------------- frequency tracking (as akf)
        amp0 = math.hypot(x[IC1X], x[IS1X]); amp1 = math.hypot(x[IC1Y], x[IS1Y])
        axm = 0 if amp0 >= amp1 else 1
        ampm = max(amp0, amp1)
        i0 = IC1X if axm == 0 else IC1Y
        phs = math.atan2(x[i0 + 1], x[i0])
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
        # ---------------- output
        d0 = 0.0; d1 = 0.0
        if started:
            dtp = t + hor - tf
            rd = math.exp(-max(dtp, 0.0) / tau_d)
            c = math.cos(w * dtp); s = math.sin(w * dtp)
            c2 = math.cos(2 * w * dtp); s2_ = math.sin(2 * w * dtp)
            d0 = rd * (c * x[IC1X] + s * x[IS1X] + harm * (c2 * x[IC2X] + s2_ * x[IS2X]))
            d1 = rd * (c * x[IC1Y] + s * x[IS1Y] + harm * (c2 * x[IC2Y] + s2_ * x[IS2Y]))
            if xtrack > 0:
                # cancel only across the stroke; the stroke direction from the active template (xtrack 2) or from
                # the intent velocity (xtrack 1, or no active template); full output when the pen is (nearly) still
                vx = x[IVX]; vy = x[IVY]
                sp = math.hypot(vx, vy)
                tx = 0.0; ty = 0.0; wgt = 0.0
                if xtrack == 2 and tpl_on and prog >= 0:
                    tx = tnrm[prog, 1]; ty = -tnrm[prog, 0]
                    wgt = min(1.0, sp / v_xt)
                elif sp > 1e-9:
                    tx = vx / sp; ty = vy / sp
                    wgt = min(1.0, sp / v_xt)
                dl = tx * d0 + ty * d1
                d0 -= wgt * dl * tx; d1 -= wgt * dl * ty
        amp = math.sqrt(amp0 * amp0 + amp1 * amp1)
        amp_f = amp_f + (Ts / tau_amp) * (amp - amp_f)
        if cap_k > 0.0 and started:
            # tremor amplitude reference learned only while the intended motion is slow (as fusion.estimators.akf)
            sp_i = math.hypot(x[IVX], x[IVY])
            wv = max(0.0, 1.0 - sp_i / v_slow)
            a_ref = a_ref + wv * (Ts / tau_ref) * (amp - a_ref)
            mag = math.hypot(d0, d1)
            lim = cap_k * a_ref
            if mag > lim:
                sc_ = lim / mag if mag > 1e-15 else 0.0
                d0 *= sc_; d1 *= sc_
        target = gout
        if fgate > 0.0:
            target *= min(1.0, max(0.0, (w / TWO_PI - (fgate - 0.5 * fgw)) / max(fgw, 1e-9)))
        if a_hi > a_lo:
            target *= min(1.0, max(0.0, (amp_f - a_lo) / (a_hi - a_lo)))
        if not started:
            target = 0.0
        g_eff = g_eff + (1.0 - math.exp(-Ts / tau_auth)) * (target - g_eff)
        out[k, 0] = _lp2_step(lb, la, g_eff * d0, zlp[0]); out[k, 1] = _lp2_step(lb, la, g_eff * d1, zlp[1])
        out_f[k] = w / TWO_PI; out_g[k] = g_eff; out_amp[k] = amp_f
    out_diag[0] = n_tpl; out_diag[1] = n_gated; out_diag[2] = n_drop


def estimate(st: Streams, params: Optional[Dict] = None, extra: Optional[Dict] = None, acc_decim: int = 2):
    """extra["template"]: output of template_arrays (or None: the same filter without template)."""
    p = dict(CTX_DEFAULTS)
    if params:
        p.update(params)
    tpl = (extra or {}).get("template")
    if tpl is None or len(tpl["xy"]) < 2:
        tpl = template_arrays([], [])
        p["use_tpl"] = 0.0
    ta, tav, y = _block_average(st.acc_t, st.acc_av, st.acc, acc_decim)
    n = st.n_ticks()
    out = np.zeros((n, 2)); f = np.zeros(n); g = np.zeros(n); amp = np.zeros(n); diag = np.zeros(3)
    prm = np.array([float(p[k]) for k in CTX_KEYS])
    _ctx_run(st.tick_t, ta, tav, np.ascontiguousarray(y), st.pos_t, st.pos_av, st.pos, st.pos_ok, st.con_av, st.con,
             np.ascontiguousarray(tpl["xy"], dtype=np.float64), np.ascontiguousarray(tpl["nrm"], dtype=np.float64),
             tpl["sid"], tpl["lid"], np.ascontiguousarray(tpl["conf"], dtype=np.float64), prm, out, f, g, amp, diag)
    return out, {"f_est": f, "authority": g, "amp": amp, "params": p,
                 "template_updates": int(diag[0]), "template_gated": int(diag[1]), "template_dropped_letters": int(diag[2])}
