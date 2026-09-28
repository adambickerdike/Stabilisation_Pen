r"""A(ii): partial guidance of the nose toward the AI's predicted letter template, on top of the tremor tracker.

CAUSAL: every quantity at tick k uses only sensor samples available by then (page sensor 1 kHz with its 2 ms
latency and noise, the axial contact sensor, the tracker's own outputs up to tick k).  Unit-tested by perturbing the
future (tests/test_aiprior.py).

Per 2 kHz tick:
  u      = y_p - d_hat(t_p)              the tracker-corrected handle position at the page sample's acquisition time
  s*     = nearest template point to u   (dense template, forward-constrained progress; re-acquired at each touchdown)
  dev    = T(s*) - u
  b      <- slow per-letter placement offset, first-order average of dev (tau_b), reset at each new letter
  e      = dev - b                        the fast deviation from the template's shape (residual tremor + shape error)
  e_db   = e with a radial dead band (the writer's own letter-to-letter variability is not corrected)
  g      = g_max x conf_gate(c_hat) x amp_gate(A_hat) x capture_gate(|e|) x (letter not dropped), slewed (tau_g)
  cmd    = -d_hat + g e_db                (then the plant's soft travel limit, slew limit and servo)

conf_gate   rule 5 on the calibrated confidence (0 below c_min, min(1, c/c_full)); the template carries it per letter
amp_gate    ramps from 0 at a_lo to 1 at a_hi of the tracker's tremor-amplitude estimate (AKF amp state): no guidance
            on small or no tremor
capture     full inside `capture`, fading to 0 at 1.5 capture
drop (T5)   |e| > drop_d for longer than drop_t drops the letter's template until the next letter
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
from numba import njit

GUIDE_DEFAULTS = {"g_max": 0.6, "a_lo": 60e-6, "a_hi": 200e-6, "capture": 1.2e-3, "drop_d": 1.0e-3, "drop_t": 0.06,
                  "tau_b": 0.25, "deadband": 0.1e-3, "tau_g": 0.02, "win_back": 10, "win_fwd": 60, "win_reacq": 400,
                  "c_min": 0.5}
KEYS = tuple(GUIDE_DEFAULTS)


@njit(cache=True)
def _guide_run(tick_t, pos_t, pos_av, pos, pos_ok, con_av, con, dh, amp, lag_ticks, txy, tlid, tconf, prm, out, out_g, diag):
    g_max = prm[0]; a_lo = prm[1]; a_hi = prm[2]; cap = prm[3]; drop_d = prm[4]; drop_t = prm[5]
    tau_b = prm[6]; db = prm[7]; tau_g = prm[8]; wb = int(prm[9]); wf = int(prm[10]); wre = int(prm[11]); c_min = prm[12]
    n = len(tick_t)
    Ts = tick_t[1] - tick_t[0]
    npos = len(pos_t); ncon = len(con_av); ntp = txy.shape[0]
    ip = 0; ic = 0
    have = False
    y0 = 0.0; y1 = 0.0; yt = 0.0
    in_con = False; was_con = False
    prog = 0; reacq = True
    cur_letter = -1
    b0 = 0.0; b1 = 0.0; nb = 0
    over = 0.0; dropped = -2
    g = 0.0
    a_b = Ts / max(tau_b, 1e-6)
    a_g = 1.0 - math.exp(-Ts / max(tau_g, 1e-6))
    n_on = 0; n_drop = 0
    for k in range(n):
        t = tick_t[k]
        while ip < npos and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5:
                y0 = pos[ip, 0]; y1 = pos[ip, 1]; yt = pos_t[ip]; have = True
            ip += 1
        while ic < ncon and con_av[ic] <= t:
            in_con = con[ic] > 0.5
            ic += 1
        if in_con and not was_con:
            reacq = True
        was_con = in_con
        c0 = -dh[k, 0]; c1 = -dh[k, 1]
        target = 0.0
        e0 = 0.0; e1 = 0.0
        if in_con and have and ntp > 1:
            # tracker estimate for the page sample's acquisition time (it was predicted lag_ticks ahead)
            kk = int(math.floor(yt / Ts + 1e-9)) - lag_ticks
            if kk < 0:
                kk = 0
            if kk > k:
                kk = k
            u0 = y0 - dh[kk, 0]; u1 = y1 - dh[kk, 1]
            if reacq:
                j0 = prog; j1 = min(ntp, prog + wre)
            else:
                j0 = max(0, prog - wb); j1 = min(ntp, prog + wf)
            best = 1e30; bj = -1
            for q in range(j0, j1):
                dx = txy[q, 0] - u0; dy = txy[q, 1] - u1
                dd = dx * dx + dy * dy
                if dd < best:
                    best = dd; bj = q
            if bj >= 0:
                reacq = False
                prog = bj
                li = tlid[bj]
                if li != cur_letter:
                    cur_letter = li
                    nb = 0; b0 = 0.0; b1 = 0.0; over = 0.0
                d0 = txy[bj, 0] - u0; d1 = txy[bj, 1] - u1
                if nb == 0:
                    b0 = 0.0; b1 = 0.0
                b0 += a_b * (d0 - b0); b1 += a_b * (d1 - b1)
                nb += 1
                e0 = d0 - b0; e1 = d1 - b1
                r = math.sqrt(e0 * e0 + e1 * e1)
                if r > drop_d:
                    over += Ts
                else:
                    over = 0.0
                if over > drop_t and dropped != li:
                    dropped = li
                    n_drop += 1
                cf = tconf[bj]
                if cf >= c_min and dropped != li:
                    ga = 1.0 if a_hi <= a_lo else min(1.0, max(0.0, (amp[k] - a_lo) / (a_hi - a_lo)))
                    if r <= cap:
                        gc = 1.0
                    elif r < 1.5 * cap:
                        gc = (1.5 * cap - r) / (0.5 * cap)
                    else:
                        gc = 0.0
                    target = g_max * min(1.0, cf) * ga * gc
                # radial dead band
                if r > db and r > 0.0:
                    s = (r - db) / r
                    e0 *= s; e1 *= s
                else:
                    e0 = 0.0; e1 = 0.0
        g += a_g * (target - g)
        if target > 0.0:
            n_on += 1
        out[k, 0] = c0 + g * e0
        out[k, 1] = c1 + g * e1
        out_g[k] = g
    diag[0] = n_on; diag[1] = n_drop


def command(st, dh: np.ndarray, amp: np.ndarray, tpl: Dict, params: Optional[Dict] = None, lag_s: float = 0.0):
    """Per-tick nose command (m) = -d_hat + guidance.  tpl: fusion.context.template_arrays output (xy, lid, conf).
    lag_s: how far ahead the tracker predicts (its horizon incl. the output low-pass delay)."""
    p = dict(GUIDE_DEFAULTS)
    if params:
        p.update(params)
    n = len(st.tick_t)
    out = np.zeros((n, 2)); g = np.zeros(n); diag = np.zeros(2)
    Ts = float(st.tick_t[1] - st.tick_t[0])
    prm = np.array([float(p[k]) for k in KEYS])
    xy = np.ascontiguousarray(tpl["xy"], dtype=np.float64) if len(tpl["xy"]) else np.zeros((1, 2))
    lid = np.ascontiguousarray(tpl["lid"], dtype=np.int64) if len(tpl["xy"]) else np.zeros(1, np.int64)
    cf = np.ascontiguousarray(tpl["conf"], dtype=np.float64) if len(tpl["xy"]) else np.zeros(1)
    _guide_run(st.tick_t, st.pos_t, st.pos_av, np.ascontiguousarray(st.pos), st.pos_ok, st.con_av, st.con,
               np.ascontiguousarray(dh, dtype=np.float64), np.ascontiguousarray(amp, dtype=np.float64),
               int(round(lag_s / Ts)), xy, lid, cf, prm, out, g, diag)
    return out, {"g": g, "ticks_on": int(diag[0]), "letters_dropped": int(diag[1]), "params": p,
                 "mean_g_in_use": float(g[g > 1e-3].mean()) if np.any(g > 1e-3) else 0.0}
