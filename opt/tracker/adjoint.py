r"""Discrete adjoint of the AKF's sequential core in numba, as a torch.autograd.Function (SIMULATION tooling).

The sequential part of the AKF (accelerometer and page updates, rollback and re-application, frequency tracking)
is run forward in numba with a tape (the input state of every filter step and the frequency tracker's
intermediate values), then swept backwards: for every step the adjoint of its output state is mapped to the
adjoint of its input state and to the parameters (q_j, q_t, q_h harm, q_b, r_a, r_p, tau_decay, w0, tau_w, wmin,
wmax).  Rollbacks make the state history a graph: a snapshot version read by a later rollback receives that
rollback's input adjoint; each snapshot version's adjoint is consumed when the reverse sweep reaches the step that
created it.  The forward arithmetic calls fusion.estimators' own numba helpers (_akf_FQ, _akf_update) and a
block-structured copy of _akf_predict that skips only exact zeros (bit-identical sums), so it is the reference
arithmetic; the per-tick schedule comes from opt.tracker.schedule.

Output of the core per tick (as opt.tracker.torch_akf.core): XO (K, 2, 5) = [v, c1, s1, c2, s2] per axis and
W (K,) the tracked frequency (rad/s).  The output stage (prediction, cap, gates, authority, low-pass) stays in
PyTorch (opt.tracker.torch_akf.output_stage), so autograd chains through it into this adjoint.

Verified against PyTorch autograd through opt.tracker.torch_akf (the same recursion written with tensors) and
against finite differences (opt/tracker/tests, opt.tracker.gradcheck).
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numba
import numpy as np
import torch
from numba import njit, prange

from fusion.estimators import _akf_FQ, _akf_update

from . import schedule as SCH
from . import torch_akf as TA

NS = 8
NP = 11          # qj, qt, qhh, qb, ra, rp, tau_d, w0, tau_w, wmin, wmax (w in rad/s)
TWO_PI = 2.0 * math.pi


# ------------------------------------------------------------------ packing of schedules (per recording arrays)
class Packed:
    """Schedules of a batch as padded arrays for the numba kernels (acc-sample indexing)."""

    def __init__(self, scheds: Sequence[SCH.Schedule]):
        B = len(scheds)
        K = scheds[0].K
        if any(s.K != K for s in scheds):
            raise ValueError("equal tick counts required")
        R = max(s.R for s in scheds)
        NA = max(s.n_acc for s in scheds)
        self.B, self.K, self.R, self.NA = B, K, R, NA
        self.acc_ev = np.zeros((B, K), np.bool_); self.acc_first = np.zeros((B, K), np.bool_)
        self.acc_dt = np.zeros((B, K)); self.acc_j = np.full((B, K), -1, np.int64)
        self.accY = np.zeros((B, NA, 2))
        self.pg_ev = np.zeros((B, K), np.bool_); self.pg_gap = np.zeros((B, K), np.bool_)
        self.pg_dt = np.zeros((B, K)); self.pg_s = np.full((B, K), -1, np.int64); self.pg_y = np.zeros((B, K, 2))
        self.pg_nre = np.zeros((B, K), np.int64); self.re_q = np.full((B, K, R), -1, np.int64)
        self.re_dt = np.zeros((B, K, R))
        self.fr_adv = np.zeros((B, K), np.bool_); self.fr_have = np.zeros((B, K), np.bool_)
        self.fr_upd = np.zeros((B, K), np.bool_); self.fr_dtp = np.zeros((B, K))
        self.n_steps = np.zeros(B, np.int64)
        for b, s in enumerate(scheds):
            j = np.cumsum(s.acc_ev) - 1
            self.acc_ev[b] = s.acc_ev; self.acc_first[b] = s.acc_first; self.acc_dt[b] = s.acc_dt
            self.acc_j[b] = np.where(s.acc_ev, j, -1)
            self.accY[b, :s.n_acc] = s.acc_y[s.acc_ev]
            self.pg_ev[b] = s.pg_ev; self.pg_gap[b] = s.pg_gap; self.pg_dt[b] = s.pg_dt; self.pg_y[b] = s.pg_y
            self.pg_s[b] = np.where(s.pg_ev, j[np.clip(s.pg_snap, 0, K - 1)], -1)
            self.pg_nre[b] = s.pg_nre
            rq = np.where(s.re_tick >= 0, j[np.clip(s.re_tick, 0, K - 1)], -1)
            self.re_q[b, :, :s.R] = rq
            self.re_dt[b, :, :s.R] = s.re_dt
            self.fr_adv[b] = s.fr_adv; self.fr_have[b] = s.fr_have; self.fr_upd[b] = s.fr_upd; self.fr_dtp[b] = s.fr_dtp
            self.n_steps[b] = int(s.acc_ev.sum() + s.pg_ev.sum() + s.pg_nre.sum())

    def args(self):
        return (self.acc_ev, self.acc_first, self.acc_dt, self.acc_j, self.accY, self.pg_ev, self.pg_gap, self.pg_dt,
                self.pg_s, self.pg_y, self.pg_nre, self.re_q, self.re_dt, self.fr_adv, self.fr_have, self.fr_upd,
                self.fr_dtp, self.n_steps)


# ------------------------------------------------------------------ forward with tape (one recording)
@njit(cache=True)
def _ha(w, harm, H):
    for i in range(NS):
        H[i] = 0.0
    H[2] = 1.0; H[3] = -w * w; H[5] = -4.0 * w * w * harm; H[7] = 1.0


@njit(cache=True)
def _fwd_one(K, NA, acc_ev, acc_first, acc_dt, acc_j, accY, pg_ev, pg_gap, pg_dt, pg_s, pg_y, pg_nre, re_q, re_dt,
             fr_adv, fr_have, fr_upd, fr_dtp, prm, harm, XO, W,
             s_kind, s_idx, s_dt, s_w, s_xin, s_Pin, s_y, t_s0, t_ns,
             f_cond, f_case, f_axm, f_phs, f_ppb, f_wb, f_wn, f_wm, f_aw, f_xc, f_xs):
    qj = prm[0]; qt = prm[1]; qhh = prm[2]; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    w = prm[7]; tau_w = prm[8]; wmin = prm[9]; wmax = prm[10]
    x = np.zeros((2, NS)); P = np.zeros((NS, NS))
    F = np.zeros((NS, NS)); Q = np.zeros((NS, NS)); tmp = np.zeros((1, NS))
    Ha = np.zeros(NS); Hp = np.zeros(NS); FPs = np.zeros((NS, NS))
    Hp[0] = 1.0; Hp[3] = 1.0; Hp[5] = harm
    snx = np.zeros((NA, 2, NS)); snP = np.zeros((NA, NS, NS)); wused = np.zeros(NA)
    phase_prev = 0.0; ax_prev = 0
    ns = 0
    for k in range(K):
        t_s0[k] = ns
        if acc_ev[k]:
            j = acc_j[k]
            if acc_first[k]:
                for i in range(NS):
                    for q in range(NS):
                        P[i, q] = 0.0
                P[0, 0] = 1e-6; P[1, 1] = 1e-4; P[2, 2] = 1.0; P[3, 3] = 1e-7; P[4, 4] = 1e-7
                P[5, 5] = 1e-8; P[6, 6] = 1e-8; P[7, 7] = 0.05
            dt = acc_dt[k]
            s_kind[ns] = 0; s_idx[ns] = j; s_dt[ns] = dt; s_w[ns] = w
            s_xin[ns] = x; s_Pin[ns] = P; s_y[ns, 0] = accY[j, 0]; s_y[ns, 1] = accY[j, 1]
            ns += 1
            if dt > 0:
                _akf_FQ(dt, w, tau_d, qj, qt, qhh, qb, F, Q)
                _pred_s(x, P, F, Q, FPs)
            _ha(w, harm, Ha)
            _akf_update(x, P, Ha, accY[j, 0], accY[j, 1], ra)
            snx[j] = x; snP[j] = P; wused[j] = w
        if pg_ev[k]:
            s = pg_s[k]
            x[:, :] = snx[s]; P[:, :] = snP[s]
            ws = wused[s]
            dt = pg_dt[k]
            s_kind[ns] = 2 if pg_gap[k] else 1; s_idx[ns] = s; s_dt[ns] = dt; s_w[ns] = ws
            s_xin[ns] = x; s_Pin[ns] = P; s_y[ns, 0] = pg_y[k, 0]; s_y[ns, 1] = pg_y[k, 1]
            ns += 1
            if dt > 0:
                _akf_FQ(dt, ws, tau_d, qj, qt, qhh, qb, F, Q)
                _pred_s(x, P, F, Q, FPs)
            if pg_gap[k]:
                for a in range(2):
                    x[a, 0] = pg_y[k, a] - x[a, 3] - harm * x[a, 5]
                for q in range(NS):
                    P[0, q] = 0.0
                    P[q, 0] = 0.0
                P[0, 0] = rp
            else:
                _akf_update(x, P, Hp, pg_y[k, 0], pg_y[k, 1], rp)
            for r in range(pg_nre[k]):
                q = re_q[k, r]
                wq = wused[q]
                dt = re_dt[k, r]
                s_kind[ns] = 3; s_idx[ns] = q; s_dt[ns] = dt; s_w[ns] = wq
                s_xin[ns] = x; s_Pin[ns] = P; s_y[ns, 0] = accY[q, 0]; s_y[ns, 1] = accY[q, 1]
                ns += 1
                if dt > 0:
                    _akf_FQ(dt, wq, tau_d, qj, qt, qhh, qb, F, Q)
                    _pred_s(x, P, F, Q, FPs)
                _ha(wq, harm, Ha)
                _akf_update(x, P, Ha, accY[q, 0], accY[q, 1], ra)
                snx[q] = x; snP[q] = P
        t_ns[k] = ns - t_s0[k]
        # frequency tracking
        a0 = math.hypot(x[0, 3], x[0, 4]); a1 = math.hypot(x[1, 3], x[1, 4])
        axm = 0 if a0 >= a1 else 1
        ampm = max(a0, a1)
        xc = x[axm, 3]; xs = x[axm, 4]
        phs = math.atan2(xs, xc)
        f_axm[k] = axm; f_phs[k] = phs; f_ppb[k] = phase_prev; f_wb[k] = w; f_xc[k] = xc; f_xs[k] = xs
        cond = fr_have[k] and ampm > 2e-6 and fr_adv[k] and axm == ax_prev
        f_cond[k] = cond
        f_case[k] = 0
        if cond:
            dph = phs - phase_prev
            while dph > math.pi:
                dph -= 2 * math.pi
            while dph < -math.pi:
                dph += 2 * math.pi
            dtp_ = fr_dtp[k]
            wm = -dph / dtp_
            a_w = min(1.0, dtp_ / tau_w)
            wn = w + a_w * (wm - w)
            f_wn[k] = wn; f_wm[k] = wm; f_aw[k] = a_w
            w1 = max(wn, wmin)
            if w1 != wn:
                f_case[k] = 1
            w2 = min(w1, wmax)
            if w2 != w1:
                f_case[k] = 2
            w = w2
        if fr_upd[k]:
            phase_prev = phs
            ax_prev = axm
        for a in range(2):
            XO[k, a, 0] = x[a, 1]; XO[k, a, 1] = x[a, 3]; XO[k, a, 2] = x[a, 4]; XO[k, a, 3] = x[a, 5]
            XO[k, a, 4] = x[a, 6]
        W[k] = w
    return ns


# block structure of F: nonzero columns of row i are LO[i] .. HI[i]-1 (intent 3x3 upper triangle, two 2x2
# oscillator rotations, bias); skipping exact zeros keeps every sum bit-identical to fusion's dense _akf_predict
LO = np.array([0, 1, 2, 3, 3, 5, 5, 7], np.int64)
HI = np.array([3, 3, 3, 5, 5, 7, 7, 8], np.int64)
# nonzero rows of column j: CLO[j] .. CHI[j]-1
CLO = np.array([0, 0, 0, 3, 3, 5, 5, 7], np.int64)
CHI = np.array([1, 2, 3, 5, 5, 7, 7, 8], np.int64)


@njit(cache=True)
def _pred_s(x, P, F, Q, FP):
    """x <- F x (both axes), P <- F P F^T + Q using the block structure of F (same sums as _akf_predict)."""
    for a in range(2):
        tt = np.empty(NS)
        for i in range(NS):
            s = 0.0
            for k in range(LO[i], HI[i]):
                s += F[i, k] * x[a, k]
            tt[i] = s
        for i in range(NS):
            x[a, i] = tt[i]
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(LO[i], HI[i]):
                s += F[i, k] * P[k, j]
            FP[i, j] = s
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(LO[j], HI[j]):
                s += FP[i, k] * F[j, k]
            P[i, j] = s + Q[i, j]


# ------------------------------------------------------------------ reverse helpers
@njit(cache=True)
def _mm(A, B, C):
    n = A.shape[0]
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += A[i, k] * B[k, j]
            C[i, j] = s


@njit(cache=True)
def _rev_update_full(xp, Pp, H, y0, y1, R, lx, lP, lH):
    PH = np.zeros(NS)
    for i in range(NS):
        s = 0.0
        for j in range(NS):
            s += Pp[i, j] * H[j]
        PH[i] = s
    S = R
    for i in range(NS):
        S += H[i] * PH[i]
    e0 = y0; e1 = y1
    for i in range(NS):
        e0 -= H[i] * xp[0, i]
        e1 -= H[i] * xp[1, i]
    # K = PH / S
    lK = np.zeros(NS)
    le0 = 0.0; le1 = 0.0
    for i in range(NS):
        lK[i] = lx[0, i] * e0 + lx[1, i] * e1
        Ki = PH[i] / S
        le0 += lx[0, i] * Ki
        le1 += lx[1, i] * Ki
    # e_a = y_a - H x_a
    for i in range(NS):
        lx[0, i] -= H[i] * le0
        lx[1, i] -= H[i] * le1
        lH[i] -= xp[0, i] * le0 + xp[1, i] * le1
    # P' = P - PH PH^T / S  and  K = PH / S
    lPH = np.zeros(NS)
    lS = 0.0
    for i in range(NS):
        s = 0.0
        for j in range(NS):
            s += (lP[i, j] + lP[j, i]) * PH[j]
        lPH[i] = -s / S + lK[i] / S
    for i in range(NS):
        for j in range(NS):
            lS += lP[i, j] * PH[i] * PH[j]
    lS = lS / (S * S)
    for i in range(NS):
        lS -= lK[i] * PH[i] / (S * S)
    # S = H . PH + R
    for i in range(NS):
        lH[i] += lS * PH[i]
        lPH[i] += lS * H[i]
    # PH = P H  (lP holds the direct adjoint of P' -> P already)
    for i in range(NS):
        for j in range(NS):
            lP[i, j] += lPH[i] * H[j]
            lH[j] += lPH[i] * Pp[i, j]
    return lS


@njit(cache=True)
def _rev_predict(xin, Pin, F, lx, lP, lF, FP, M):
    """Reverse of x' = F x, P' = F P F^T + Q (block-structured F).  lx, lP: output adjoints, replaced by the input
    adjoints.  lF is filled on the oscillator blocks only (the other entries of F do not depend on parameters).
    The caller takes lQ = lP before the call."""
    # FP = F Pin
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(LO[i], HI[i]):
                s += F[i, k] * Pin[k, j]
            FP[i, j] = s
    # lF_ij = sum_a lx_ai x_aj + sum_k (lP_ik + lP_ki) FP_kj   (P symmetric), on the blocks (3,4) and (5,6)
    for i in range(3, 7):
        j0 = 3 if i < 5 else 5
        for j in range(j0, j0 + 2):
            s = lx[0, i] * xin[0, j] + lx[1, i] * xin[1, j]
            for k in range(NS):
                s += (lP[i, k] + lP[k, i]) * FP[k, j]
            lF[i, j] = s
    # lx_in = F^T lx'
    for a in range(2):
        tt = np.empty(NS)
        for j in range(NS):
            s = 0.0
            for i in range(CLO[j], CHI[j]):
                s += F[i, j] * lx[a, i]
            tt[j] = s
        for j in range(NS):
            lx[a, j] = tt[j]
    # lP_in = F^T lP' F : M = lP' F, then F^T M
    for k in range(NS):
        for j in range(NS):
            s = 0.0
            for l in range(CLO[j], CHI[j]):
                s += lP[k, l] * F[l, j]
            M[k, j] = s
    for i in range(NS):
        for j in range(NS):
            s = 0.0
            for k in range(CLO[i], CHI[i]):
                s += F[k, i] * M[k, j]
            lP[i, j] = s


@njit(cache=True)
def _rev_FQ(dt, w, tau_d, qj, F, lF, lQ, g):
    """Parameter adjoints of F(dt, w, tau_d) and Q(dt; qj, qt, qhh, qb).  g: [.., w-slot returned]; returns lw."""
    rd = math.exp(-dt / tau_d)
    c = math.cos(w * dt); s = math.sin(w * dt)
    c2 = math.cos(2 * w * dt); s2 = math.sin(2 * w * dt)
    lw = rd * dt * (-lF[3, 3] * s + lF[3, 4] * c - lF[4, 3] * c - lF[4, 4] * s
                    + 2.0 * (-lF[5, 5] * s2 + lF[5, 6] * c2 - lF[6, 5] * c2 - lF[6, 6] * s2))
    osc = (lF[3, 3] * F[3, 3] + lF[3, 4] * F[3, 4] + lF[4, 3] * F[4, 3] + lF[4, 4] * F[4, 4]
           + lF[5, 5] * F[5, 5] + lF[5, 6] * F[5, 6] + lF[6, 5] * F[6, 5] + lF[6, 6] * F[6, 6])
    g[6] += osc * dt / (tau_d * tau_d)
    T2 = dt * dt; T3 = T2 * dt; T4 = T3 * dt; T5 = T4 * dt
    g[0] += (lQ[0, 0] * T5 / 20.0 + (lQ[0, 1] + lQ[1, 0]) * T4 / 8.0 + (lQ[0, 2] + lQ[2, 0]) * T3 / 6.0
             + lQ[1, 1] * T3 / 3.0 + (lQ[1, 2] + lQ[2, 1]) * T2 / 2.0 + lQ[2, 2] * dt)
    g[1] += dt * (lQ[3, 3] + lQ[4, 4])
    g[2] += dt * (lQ[5, 5] + lQ[6, 6])
    g[3] += dt * lQ[7, 7]
    return lw


@njit(cache=True)
def _rev_step(kind, dt, w, xin, Pin, y0, y1, prm, harm, lx, lP, g, F, Q, tmp, lF, lQ, tmp8, tmp8b, xp, Pp, Ha, lH):
    """Reverse of one filter step (predict + update / gap).  lx, lP: output adjoints -> input adjoints.
    Returns the adjoint of the step's w (acc and re-applied samples: also through H(w))."""
    qj = prm[0]; qt = prm[1]; qhh = prm[2]; qb = prm[3]; ra = prm[4]; rp = prm[5]; tau_d = prm[6]
    xp[:, :] = xin; Pp[:, :] = Pin
    pred = dt > 0
    if pred:
        _akf_FQ(dt, w, tau_d, qj, qt, qhh, qb, F, Q)
        _pred_s(xp, Pp, F, Q, tmp8)
    lw = 0.0
    if kind == 2:
        # gap: x'_a0 = y_a - x_a3 - harm x_a5 ; P' row/col 0 cleared, P00 = rp
        for a in range(2):
            l0 = lx[a, 0]
            lx[a, 3] -= l0
            lx[a, 5] -= harm * l0
            lx[a, 0] = 0.0
        g[5] += lP[0, 0]
        for q in range(NS):
            lP[0, q] = 0.0
            lP[q, 0] = 0.0
    else:
        for i in range(NS):
            lH[i] = 0.0
        if kind == 1:
            for i in range(NS):
                Ha[i] = 0.0
            Ha[0] = 1.0; Ha[3] = 1.0; Ha[5] = harm
            lR = _rev_update_full(xp, Pp, Ha, y0, y1, rp, lx, lP, lH)
            g[5] += lR
        else:
            _ha(w, harm, Ha)
            lR = _rev_update_full(xp, Pp, Ha, y0, y1, ra, lx, lP, lH)
            g[4] += lR
            lw += lH[3] * (-2.0 * w) + lH[5] * (-8.0 * w * harm)
    if pred:
        for i in range(NS):
            for j in range(NS):
                lQ[i, j] = lP[i, j]
        _rev_predict(xin, Pin, F, lx, lP, lF, tmp8, tmp8b)
        lw += _rev_FQ(dt, w, tau_d, qj, F, lF, lQ, g)
    return lw


@njit(cache=True)
def _rev_one(K, NA, acc_ev, acc_first, pg_ev, pg_nre, prm, harm, gXO, gW,
             s_kind, s_idx, s_dt, s_w, s_xin, s_Pin, s_y, t_s0, t_ns,
             f_cond, f_case, f_axm, f_phs, f_ppb, f_wb, f_wn, f_wm, f_aw, f_xc, f_xs, fr_upd, fr_dtp, g):
    tau_w = prm[8]
    lx = np.zeros((2, NS)); lP = np.zeros((NS, NS))
    lsx = np.zeros((NA, 2, NS)); lsP = np.zeros((NA, NS, NS)); lwu = np.zeros(NA)
    lw = 0.0; lpp = 0.0
    F = np.zeros((NS, NS)); Q = np.zeros((NS, NS)); tmp = np.zeros((1, NS)); lF = np.zeros((NS, NS))
    lQ = np.zeros((NS, NS)); tmp8 = np.zeros((NS, NS)); tmp8b = np.zeros((NS, NS)); xp = np.zeros((2, NS))
    Pp = np.zeros((NS, NS)); Ha = np.zeros(NS); lH = np.zeros(NS)
    for k in range(K - 1, -1, -1):
        # ---------------- output record
        for a in range(2):
            lx[a, 1] += gXO[k, a, 0]; lx[a, 3] += gXO[k, a, 1]; lx[a, 4] += gXO[k, a, 2]
            lx[a, 5] += gXO[k, a, 3]; lx[a, 6] += gXO[k, a, 4]
        lw += gW[k]
        # ---------------- frequency tracking
        lphs = 0.0
        if fr_upd[k]:
            lphs += lpp
            lpp = 0.0
        if f_cond[k]:
            lwn = 0.0
            if f_case[k] == 1:
                g[9] += lw
            elif f_case[k] == 2:
                g[10] += lw
            else:
                lwn = lw
            a_w = f_aw[k]
            dtp_ = fr_dtp[k]
            lw = lwn * (1.0 - a_w)
            lwm = lwn * a_w
            law = lwn * (f_wm[k] - f_wb[k])
            if dtp_ / tau_w < 1.0:
                g[8] += law * (-dtp_ / (tau_w * tau_w))
            ldph = -lwm / dtp_
            lphs += ldph
            lpp -= ldph
        if lphs != 0.0:
            xc = f_xc[k]; xs = f_xs[k]
            r2 = xc * xc + xs * xs
            if r2 > 0.0:
                ax = f_axm[k]
                lx[ax, 4] += lphs * xc / r2
                lx[ax, 3] -= lphs * xs / r2
        # ---------------- steps of this tick, in reverse
        s0 = t_s0[k]
        n = t_ns[k]
        if pg_ev[k]:
            ps = s0 + (1 if acc_ev[k] else 0)
            nre = n - (ps - s0) - 1
            for i in range(nre, 0, -1):
                st = ps + i
                q = s_idx[st]
                lx += lsx[q]; lP += lsP[q]
                lsx[q] = 0.0; lsP[q] = 0.0
                lwq = _rev_step(3, s_dt[st], s_w[st], s_xin[st], s_Pin[st], s_y[st, 0], s_y[st, 1], prm, harm, lx, lP,
                                g, F, Q, tmp, lF, lQ, tmp8, tmp8b, xp, Pp, Ha, lH)
                lwu[q] += lwq
            lws = _rev_step(s_kind[ps], s_dt[ps], s_w[ps], s_xin[ps], s_Pin[ps], s_y[ps, 0], s_y[ps, 1], prm, harm, lx,
                            lP, g, F, Q, tmp, lF, lQ, tmp8, tmp8b, xp, Pp, Ha, lH)
            sidx = s_idx[ps]
            lwu[sidx] += lws
            lsx[sidx] += lx; lsP[sidx] += lP
            lx[:, :] = 0.0; lP[:, :] = 0.0
        if acc_ev[k]:
            j = s_idx[s0]
            lx += lsx[j]; lP += lsP[j]
            lsx[j] = 0.0; lsP[j] = 0.0
            lwj = _rev_step(0, s_dt[s0], s_w[s0], s_xin[s0], s_Pin[s0], s_y[s0, 0], s_y[s0, 1], prm, harm, lx, lP, g,
                            F, Q, tmp, lF, lQ, tmp8, tmp8b, xp, Pp, Ha, lH)
            lwu[j] += lwj
            lw += lwu[j]
            lwu[j] = 0.0
            if acc_first[k]:
                lx[:, :] = 0.0; lP[:, :] = 0.0
    g[7] += lw


@njit(cache=True)
def _alloc_tape_nb(K, n_steps):
    return (np.zeros(n_steps, np.int8), np.zeros(n_steps, np.int64), np.zeros(n_steps), np.zeros(n_steps),
            np.zeros((n_steps, 2, NS)), np.zeros((n_steps, NS, NS)), np.zeros((n_steps, 2)), np.zeros(K, np.int64),
            np.zeros(K, np.int64))


@njit(cache=True)
def _alloc_freq_nb(K):
    return (np.zeros(K, np.bool_), np.zeros(K, np.int8), np.zeros(K, np.int64), np.zeros(K), np.zeros(K), np.zeros(K),
            np.zeros(K), np.zeros(K), np.zeros(K), np.zeros(K), np.zeros(K))


@njit(parallel=True, cache=True)
def _fwd_batch(K, NA, acc_ev, acc_first, acc_dt, acc_j, accY, pg_ev, pg_gap, pg_dt, pg_s, pg_y, pg_nre, re_q, re_dt,
               fr_adv, fr_have, fr_upd, fr_dtp, n_steps, prm, harm, XO, W):
    B = acc_ev.shape[0]
    for b in prange(B):
        tp = _alloc_tape_nb(K, n_steps[b])
        fq = _alloc_freq_nb(K)
        _fwd_one(K, NA, acc_ev[b], acc_first[b], acc_dt[b], acc_j[b], accY[b], pg_ev[b], pg_gap[b], pg_dt[b], pg_s[b],
                 pg_y[b], pg_nre[b], re_q[b], re_dt[b], fr_adv[b], fr_have[b], fr_upd[b], fr_dtp[b], prm[b], harm,
                 XO[b], W[b], tp[0], tp[1], tp[2], tp[3], tp[4], tp[5], tp[6], tp[7], tp[8],
                 fq[0], fq[1], fq[2], fq[3], fq[4], fq[5], fq[6], fq[7], fq[8], fq[9], fq[10])


@njit(parallel=True, cache=True)
def _grad_batch(K, NA, acc_ev, acc_first, acc_dt, acc_j, accY, pg_ev, pg_gap, pg_dt, pg_s, pg_y, pg_nre, re_q, re_dt,
                fr_adv, fr_have, fr_upd, fr_dtp, n_steps, prm, harm, gXO, gW, G):
    B = acc_ev.shape[0]
    for b in prange(B):
        tp = _alloc_tape_nb(K, n_steps[b])
        fq = _alloc_freq_nb(K)
        XO = np.zeros((K, 2, 5)); W = np.zeros(K)
        _fwd_one(K, NA, acc_ev[b], acc_first[b], acc_dt[b], acc_j[b], accY[b], pg_ev[b], pg_gap[b], pg_dt[b], pg_s[b],
                 pg_y[b], pg_nre[b], re_q[b], re_dt[b], fr_adv[b], fr_have[b], fr_upd[b], fr_dtp[b], prm[b], harm,
                 XO, W, tp[0], tp[1], tp[2], tp[3], tp[4], tp[5], tp[6], tp[7], tp[8],
                 fq[0], fq[1], fq[2], fq[3], fq[4], fq[5], fq[6], fq[7], fq[8], fq[9], fq[10])
        g = np.zeros(NP)
        _rev_one(K, NA, acc_ev[b], acc_first[b], pg_ev[b], pg_nre[b], prm[b], harm, gXO[b], gW[b],
                 tp[0], tp[1], tp[2], tp[3], tp[4], tp[5], tp[6], tp[7], tp[8],
                 fq[0], fq[1], fq[2], fq[3], fq[4], fq[5], fq[6], fq[7], fq[8], fq[9], fq[10], fr_upd[b], fr_dtp[b], g)
        for i in range(NP):
            G[b, i] = g[i]


class CoreFn(torch.autograd.Function):
    """(B, 11) core parameters -> XO (B, K, 2, 5), W (B, K); backward by the numba adjoint."""

    @staticmethod
    def forward(ctx, cprm, pk, harm):
        prm = np.ascontiguousarray(cprm.detach().numpy())
        XO = np.zeros((pk.B, pk.K, 2, 5)); W = np.zeros((pk.B, pk.K))
        _fwd_batch(pk.K, pk.NA, *pk.args(), prm, float(harm), XO, W)
        ctx.pk = pk; ctx.harm = float(harm)
        ctx.save_for_backward(cprm)
        return torch.from_numpy(XO), torch.from_numpy(W)

    @staticmethod
    def backward(ctx, gXO, gW):
        (cprm,) = ctx.saved_tensors
        pk = ctx.pk
        prm = np.ascontiguousarray(cprm.detach().numpy())
        gx = np.ascontiguousarray(gXO.detach().numpy()) if gXO is not None else np.zeros((pk.B, pk.K, 2, 5))
        gw = np.ascontiguousarray(gW.detach().numpy()) if gW is not None else np.zeros((pk.B, pk.K))
        G = np.zeros((pk.B, NP))
        _grad_batch(pk.K, pk.NA, *pk.args(), prm, ctx.harm, gx, gw, G)
        return torch.from_numpy(G), None, None


def core_params(prm: Dict[str, torch.Tensor], harm: float) -> torch.Tensor:
    return torch.stack([prm["qj"], prm["qt"], prm["qh"] * harm, prm["qb"], prm["ra"], prm["rp"], prm["tau_decay"],
                        TWO_PI * prm["w0_hz"], prm["tau_w"], TWO_PI * prm["wmin_hz"], TWO_PI * prm["wmax_hz"]], 1)


def forward(pk: Packed, ev: TA.EventBatch, vals: Dict, static: Dict, gate_beta=None, return_parts=False):
    """Estimate (B, K, 2): the numba core (adjoint backward) + the torch output stage."""
    prm = TA.expand(vals, pk.B)
    harm = float(static.get("harm", 1.0))
    XO, W = CoreFn.apply(core_params(prm, harm), pk, harm)
    return TA.output_stage(XO, W, ev, prm, static, gate_beta, return_parts)


def set_threads(n: int = 2):
    numba.set_num_threads(max(1, min(n, numba.config.NUMBA_NUM_THREADS)))
