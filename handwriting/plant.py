r"""Model HW1: hand, pen handle, active tip (nose or nib stage), paper friction and guidance, in the page plane.

Evidence status of every output: SIMULATION.  Structure (2-D, page plane, SI units):

  imposed hand path p_ref = intended + tremor --[arm k_a, b_a]-- hand mass M (perturbation dM, M1 convention)
      --[grip K_g, C_g]-- handle (tip reference point p_H) --[tip actuator F_a + suspension k_t, stops]-- tip (p_H + q)

  handle:  m_H a_H = F_grip + F_skid + F_writer - F_a - F_sus
  tip:     m_t (a_H + a_q) = F_a + F_sus + F_ball + F_board                     (rigid pens: q = 0)
  hand:    M dM'' = -k_a dM - b_a dM' - F_grip,    F_grip = K_g (p_ref + dM - p_H) + C_g (v_ref + dM' - v_H)

Paper: LuGre friction normalised by the normal force (as M1/P1: sigma_0 = mu_s / x_pre, sigma_1 = sigma_2 = 0,
Stribeck), on the ball (tip velocity) and on the skid ring (handle velocity) for skid designs.
Writer (ASSUMPTION): writer_comp = 1 cancels the paper drag at the handle (a writer's learnt compensation, so the
tremor-free ink follows the intended letters); 0 = open-loop hand (P1/H1 convention).  In both cases the ball drag
still loads the tip actuator.

Tip servo (kinematic follower with force limit): the controller's command (2 kHz ticks) is soft-limited (tanh taper
to q_lim), slew-limited, delayed by the command latency, filtered by a 2nd-order follower (servo_hz, zeta) and tracked
by a stiff inner loop (inverse dynamics + PD at inner_hz) whose force is limited to F_peak at the tip.  Mechanical
stops at q_stop (2e4 N/m).

Controller terms (summed, times the contact authority g_eff that ramps with tau_auth after sensed contact):
  ext    an external command per tick (tracker: -d_hat; oracle: -d(t + preview); neutral: 0)
  guide  pull toward a template track: nearest pen-down template point in a forward window around the progress index,
         from the page-sensor handle position (1 kHz, 2 ms, 3 um); correction clipped by the soft limit; capture gate
         (full inside capture, fading to 0 at 1.5 capture) and a drop rule (distance > drop_d for > drop_t: off until the
         next touchdown); gain g_guide
  size   band-limited size assist: (G - 1) (p_hat - LP_tau(p_hat)) per axis (x gain, y gain)
Board (optional): F = sat_cap(K (T_near - x_tip_hat)) from the board's own pen sensing (1 kHz, noise, dead time) through a
first-order lag, applied to the tip (the pen magnet sits on the nose).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
from numba import njit

from . import ensure_paths
from .params import Board, Hand, Pen, Writing

ensure_paths()

NAMES = [
    "dt", "n", "rec_decim", "tick_decim",
    # hand
    "Kg", "Cg", "Mh", "ka", "ba", "writer_comp",
    # pen
    "rigid", "m_H", "m_t", "k_t", "c_t", "q_lim", "q_tap", "q_stop", "k_stop", "c_stop",
    "w_f", "z_f", "lat_ticks", "slew", "F_peak", "Kp_in", "Kd_in",
    # contact
    "N_ball", "N_skid", "mu_b", "mu_s_b", "mu_k_skid", "mu_s_skid", "v_s", "x_pre", "con_lat_ticks",
    # authority
    "tau_auth",
    # controller switches and gains
    "use_ext", "use_guide", "g_guide", "capture", "drop_d", "drop_t", "use_size", "G_x", "G_y", "tau_sa",
    "sa_adapt", "sa_tau_amp", "sa_t_cal",
    "ps_lat_ticks", "ps_noise", "ps_every",
    # board
    "use_board", "Kb", "Db", "F_cap", "b_tau", "b_dead_ticks", "b_noise", "b_every", "b_bias_x", "b_bias_y",
    "stroke_match",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)
REC = ["t", "pHx", "pHy", "vHx", "vHy", "aHx", "aHy", "qx", "qy", "qrx", "qry", "qcx", "qcy", "tipx", "tipy",
       "Fax", "Fay", "Fbx", "Fby", "Fsx", "Fsy", "FBx", "FBy", "Fgx", "Fgy", "contact", "g", "gate", "sat", "stop",
       "prog", "dist"]
RIDX = {n: i for i, n in enumerate(REC)}
NREC = len(REC)
RB = 256          # ring buffer length (ticks)

I_dt = IDX["dt"]; I_n = IDX["n"]; I_rec = IDX["rec_decim"]; I_tick = IDX["tick_decim"]
I_Kg = IDX["Kg"]; I_Cg = IDX["Cg"]; I_Mh = IDX["Mh"]; I_ka = IDX["ka"]; I_ba = IDX["ba"]; I_wc = IDX["writer_comp"]
I_rigid = IDX["rigid"]; I_mH = IDX["m_H"]; I_mt = IDX["m_t"]; I_kt = IDX["k_t"]; I_ct = IDX["c_t"]
I_qlim = IDX["q_lim"]; I_qtap = IDX["q_tap"]; I_qstop = IDX["q_stop"]; I_kstop = IDX["k_stop"]; I_cstop = IDX["c_stop"]
I_wf = IDX["w_f"]; I_zf = IDX["z_f"]; I_lat = IDX["lat_ticks"]; I_slew = IDX["slew"]; I_Fpk = IDX["F_peak"]
I_Kpi = IDX["Kp_in"]; I_Kdi = IDX["Kd_in"]
I_Nb = IDX["N_ball"]; I_Ns = IDX["N_skid"]; I_mub = IDX["mu_b"]; I_musb = IDX["mu_s_b"]; I_muks = IDX["mu_k_skid"]
I_muss = IDX["mu_s_skid"]; I_vs = IDX["v_s"]; I_xpre = IDX["x_pre"]; I_clat = IDX["con_lat_ticks"]
I_tauA = IDX["tau_auth"]
I_ext = IDX["use_ext"]; I_gd = IDX["use_guide"]; I_gg = IDX["g_guide"]; I_cap = IDX["capture"]; I_dd = IDX["drop_d"]
I_dtm = IDX["drop_t"]; I_sa = IDX["use_size"]; I_Gx = IDX["G_x"]; I_Gy = IDX["G_y"]; I_tsa = IDX["tau_sa"]
I_sad = IDX["sa_adapt"]; I_satau = IDX["sa_tau_amp"]; I_satcal = IDX["sa_t_cal"]
I_pslat = IDX["ps_lat_ticks"]; I_psn = IDX["ps_noise"]; I_pse = IDX["ps_every"]
I_bd = IDX["use_board"]; I_Kb = IDX["Kb"]; I_Db = IDX["Db"]; I_Fcap = IDX["F_cap"]; I_btau = IDX["b_tau"]
I_bdead = IDX["b_dead_ticks"]; I_bn = IDX["b_noise"]; I_bev = IDX["b_every"]; I_bbx = IDX["b_bias_x"]; I_bby = IDX["b_bias_y"]
I_smatch = IDX["stroke_match"]


@njit(cache=True)
def _lugre(z0, z1, v0, v1, N, mu_k, mu_s, v_s, x_pre, dt):
    """Vector LuGre bristle update (exact exponential step) and friction force (-N sigma0 z)."""
    sp = math.sqrt(v0 * v0 + v1 * v1)
    sig0 = mu_s / x_pre
    g = mu_k + (mu_s - mu_k) * math.exp(-(sp / v_s) ** 2)
    if sp > 1e-12:
        zs0 = g * v0 / (sig0 * sp); zs1 = g * v1 / (sig0 * sp)
        e = math.exp(-sig0 * sp * dt / g)
        z0 = zs0 + (z0 - zs0) * e
        z1 = zs1 + (z1 - zs1) * e
    return z0, z1, -N * sig0 * z0, -N * sig0 * z1


@njit(cache=True)
def _nearest(tm, tdown, px, py, prog, win_back, win_fwd, lo=0, hi=-1):
    m = tm.shape[0] if hi < 0 else hi
    best = 1e30; bj = prog
    j0 = max(lo, prog - win_back); j1 = min(m, prog + win_fwd)
    if j0 >= j1:
        j0 = lo; j1 = min(m, lo + win_fwd)
    for j in range(j0, j1):
        if tdown[j] < 0.5:
            continue
        dx = tm[j, 0] - px; dy = tm[j, 1] - py
        dd = dx * dx + dy * dy
        if dd < best:
            best = dd; bj = j
    return bj, math.sqrt(best)


@njit(cache=True)
def simulate(P, pref, vref, down, active, qext, gsa, tmpl, tdown, tss, tse, btmpl, btdown, btss, btse, seed, rec):
    np.random.seed(seed)
    dt = P[I_dt]; n = int(P[I_n]); rdec = int(P[I_rec]); tdec = int(P[I_tick])
    Kg = P[I_Kg]; Cg = P[I_Cg]; Mh = P[I_Mh]; ka = P[I_ka]; ba = P[I_ba]; wc = P[I_wc]
    rigid = P[I_rigid] > 0.5; mH = P[I_mH]; mt = P[I_mt]; kt = P[I_kt]; ct = P[I_ct]
    qlim = P[I_qlim]; qtap = P[I_qtap]; qstop = P[I_qstop]; kstop = P[I_kstop]; cstop = P[I_cstop]
    wf = P[I_wf]; zf = P[I_zf]; lat = int(P[I_lat]); slew = P[I_slew]; Fpk = P[I_Fpk]; Kpi = P[I_Kpi]; Kdi = P[I_Kdi]
    Nb = P[I_Nb]; Ns = P[I_Ns]; mub = P[I_mub]; musb = P[I_musb]; muks = P[I_muks]; muss = P[I_muss]
    vs = P[I_vs]; xpre = P[I_xpre]; clat = int(P[I_clat]); tauA = P[I_tauA]
    use_ext = P[I_ext] > 0.5; use_gd = P[I_gd] > 0.5; gg = P[I_gg]; cap = P[I_cap]; dd_ = P[I_dd]; dtm = P[I_dtm]
    use_sa = P[I_sa] > 0.5; Gx = P[I_Gx]; Gy = P[I_Gy]; tsa = P[I_tsa]
    sa_ad = P[I_sad] > 0.5; sa_ta = P[I_satau]; sa_tc = P[I_satcal]
    pslat = int(P[I_pslat]); psn = P[I_psn]; pse = int(P[I_pse])
    use_bd = P[I_bd] > 0.5; Kb = P[I_Kb]; Db = P[I_Db]; Fcap = P[I_Fcap]; btau = P[I_btau]
    bdead = int(P[I_bdead]); bn = P[I_bn]; bev = int(P[I_bev]); bbx = P[I_bbx]; bby = P[I_bby]
    smatch = P[I_smatch] > 0.5
    cur_s = -1; cur_sb = -1; was_con_b = 0
    be0 = 0.0; be1 = 0.0; bed0 = 0.0; bed1 = 0.0           # board error and its filtered rate
    alpha_bd = 1.0 - math.exp(-2.0 * math.pi * 30.0 * dt * tdec)
    Ts = dt * tdec
    # state
    pH0 = pref[0, 0]; pH1 = pref[0, 1]; vH0 = 0.0; vH1 = 0.0; aH0 = 0.0; aH1 = 0.0
    dM0 = 0.0; dM1 = 0.0; vM0 = 0.0; vM1 = 0.0
    q0 = 0.0; q1 = 0.0; vq0 = 0.0; vq1 = 0.0
    r0 = 0.0; r1 = 0.0; vr0 = 0.0; vr1 = 0.0          # follower output
    zb0 = 0.0; zb1 = 0.0; zs0 = 0.0; zs1 = 0.0          # bristles
    Fa0 = 0.0; Fa1 = 0.0
    ar0 = 0.0; ar1 = 0.0
    FB0 = 0.0; FB1 = 0.0                                 # board force (lagged)
    Fbc0 = 0.0; Fbc1 = 0.0                               # board command (before the lag)
    g_eff = 0.0
    qc0 = 0.0; qc1 = 0.0                                 # slew-limited command
    rb_cmd = np.zeros((RB, 2)); rb_pH = np.zeros((RB, 2)); rb_tip = np.zeros((RB, 2)); rb_con = np.zeros(RB)
    rb_bF = np.zeros((RB, 2)); rb_act = np.zeros(RB)
    ps0 = pH0; ps1 = pH1                                 # page-sensor sample (held)
    bs0 = pH0; bs1 = pH1                                 # board sensing sample (held)
    an0 = pH0; an1 = pH1                                 # size-assist anchor
    g_sa = 1.0                                           # size-assist gain (per-tick schedule when sa_adapt)
    prog = 0; progb = 0; reacq = 1; reacqb = 1
    over_t = 0.0; dropped = 0; was_con = 0
    gate = 0.0; dist = 0.0
    tick = 0; nrec = 0
    alpha_a = 1.0 - math.exp(-Ts / max(tauA, 1e-6))
    alpha_sa = Ts / max(tsa, 1e-6)
    alpha_b = 1.0 - math.exp(-dt / max(btau, 1e-9))
    nt = qext.shape[0]
    satf = 0.0; stopf = 0.0
    for k in range(n):
        con = down[k] > 0.5
        # ------------------------------------------------ controller tick
        if k % tdec == 0:
            j = tick % RB
            rb_pH[j, 0] = pH0; rb_pH[j, 1] = pH1
            rb_tip[j, 0] = pH0 + q0; rb_tip[j, 1] = pH1 + q1
            rb_con[j] = 1.0 if con else 0.0
            rb_act[j] = active[k]
            jc = (tick - clat) % RB if tick >= clat else 0
            con_s = rb_con[jc] > 0.5 if tick >= clat else False
            act_s = rb_act[jc] > 0.5 if tick >= clat else False
            # page sensor (handle), 1 kHz with latency and noise
            if tick % pse == 0:
                jp = (tick - pslat) % RB if tick >= pslat else 0
                ps0 = rb_pH[jp, 0] + psn * np.random.standard_normal()
                ps1 = rb_pH[jp, 1] + psn * np.random.standard_normal()
            target = 1.0 if act_s else 0.0
            g_eff = g_eff + alpha_a * (target - g_eff)
            c0 = 0.0; c1 = 0.0
            if use_ext and tick < nt:
                c0 += qext[tick, 0]; c1 += qext[tick, 1]
            if use_gd:
                if con_s:
                    if was_con == 0:
                        dropped = 0; over_t = 0.0
                        if smatch:
                            cur_s += 1
                            if cur_s < tss.shape[0]:
                                prog = tss[cur_s]
                    if smatch:
                        if cur_s < tss.shape[0]:
                            bj, dist = _nearest(tmpl, tdown, ps0, ps1, prog, 20, 400, tss[cur_s], tse[cur_s])
                        else:
                            bj, dist = prog, 1e3
                    else:
                        bj, dist = _nearest(tmpl, tdown, ps0, ps1, prog, 20, 4000 if reacq == 1 else 200)
                    reacq = 0
                    prog = bj
                    if dist > dd_:
                        over_t += Ts
                    else:
                        over_t = 0.0
                    if over_t > dtm:
                        dropped = 1
                    if dist <= cap:
                        gate = 1.0
                    elif dist < 1.5 * cap:
                        gate = (1.5 * cap - dist) / (0.5 * cap)
                    else:
                        gate = 0.0
                    if dropped == 1:
                        gate = 0.0
                    c0 += gg * gate * (tmpl[prog, 0] - ps0); c1 += gg * gate * (tmpl[prog, 1] - ps1)
                else:
                    reacq = 1
            if use_sa:
                an0 += alpha_sa * (ps0 - an0); an1 += alpha_sa * (ps1 - an1)
                if con_s:
                    if sa_ad:
                        # per-letter gain from the app (letter sizes measured on the unassisted hand path), per tick
                        g_sa = gsa[tick] if tick < gsa.shape[0] else gsa[gsa.shape[0] - 1]
                        c0 += (g_sa - 1.0) * (ps0 - an0) * (Gx > 1.0); c1 += (g_sa - 1.0) * (ps1 - an1)
                    else:
                        c0 += (Gx - 1.0) * (ps0 - an0); c1 += (Gy - 1.0) * (ps1 - an1)
            was_con = 1 if con_s else 0
            c0 *= g_eff; c1 *= g_eff
            # soft limit (radial tanh taper), slew limit
            rq = math.sqrt(c0 * c0 + c1 * c1)
            knee = qlim - qtap
            if rq > knee and rq > 0.0 and qtap > 0.0:
                rnew = knee + qtap * math.tanh((rq - knee) / qtap)
                c0 *= rnew / rq; c1 *= rnew / rq
            d0 = c0 - qc0; d1 = c1 - qc1
            dm = math.sqrt(d0 * d0 + d1 * d1)
            dmax = slew * Ts
            if dm > dmax and dm > 0.0:
                d0 *= dmax / dm; d1 *= dmax / dm
            qc0 += d0; qc1 += d1
            rb_cmd[j, 0] = qc0; rb_cmd[j, 1] = qc1
            # board
            if use_bd:
                if tick % bev == 0:
                    bs0 = pH0 + q0 + bbx + bn * np.random.standard_normal()
                    bs1 = pH1 + q1 + bby + bn * np.random.standard_normal()
                f0 = 0.0; f1 = 0.0
                if con_s:
                    if smatch and was_con_b == 0:
                        cur_sb += 1
                        if cur_sb < btss.shape[0]:
                            progb = btss[cur_sb]
                    if smatch:
                        if cur_sb < btss.shape[0]:
                            bj, bdist = _nearest(btmpl, btdown, bs0, bs1, progb, 20, 400, btss[cur_sb], btse[cur_sb])
                        else:
                            bj, bdist = progb, 1e3
                    else:
                        bj, bdist = _nearest(btmpl, btdown, bs0, bs1, progb, 20, 4000 if reacqb == 1 else 200)
                    reacqb = 0
                    progb = bj
                    e0 = btmpl[progb, 0] - bs0; e1 = btmpl[progb, 1] - bs1
                    if was_con_b == 0:
                        be0 = e0; be1 = e1; bed0 = 0.0; bed1 = 0.0
                    bed0 += alpha_bd * ((e0 - be0) / Ts - bed0); bed1 += alpha_bd * ((e1 - be1) / Ts - bed1)
                    be0 = e0; be1 = e1
                    f0 = Kb * e0 + Db * bed0; f1 = Kb * e1 + Db * bed1
                    if bdist > 1.0:
                        f0 = 0.0; f1 = 0.0
                    fm = math.sqrt(f0 * f0 + f1 * f1)
                    if fm > Fcap:
                        f0 *= Fcap / fm; f1 *= Fcap / fm
                else:
                    reacqb = 1
                was_con_b = 1 if con_s else 0
                rb_bF[j, 0] = f0; rb_bF[j, 1] = f1
                jb = (tick - bdead) % RB if tick >= bdead else 0
                Fbc0 = rb_bF[jb, 0] if tick >= bdead else 0.0
                Fbc1 = rb_bF[jb, 1] if tick >= bdead else 0.0
            tick += 1
        # ------------------------------------------------ follower (delayed command -> 2nd-order reference)
        if not rigid:
            tk = tick - 1 - lat
            if tk >= 0:
                u0 = rb_cmd[tk % RB, 0]; u1 = rb_cmd[tk % RB, 1]
            else:
                u0 = 0.0; u1 = 0.0
            ar0 = wf * wf * (u0 - r0) - 2.0 * zf * wf * vr0
            ar1 = wf * wf * (u1 - r1) - 2.0 * zf * wf * vr1
            vr0 += ar0 * dt; vr1 += ar1 * dt
            r0 += vr0 * dt; r1 += vr1 * dt
        # ------------------------------------------------ forces
        Fg0 = Kg * (pref[k, 0] + dM0 - pH0) + Cg * (vref[k, 0] + vM0 - vH0)
        Fg1 = Kg * (pref[k, 1] + dM1 - pH1) + Cg * (vref[k, 1] + vM1 - vH1)
        Fb0 = 0.0; Fb1 = 0.0; Fs0 = 0.0; Fs1 = 0.0
        if con:
            zb0, zb1, Fb0, Fb1 = _lugre(zb0, zb1, vH0 + vq0, vH1 + vq1, Nb, mub, musb, vs, xpre, dt)
            if Ns > 0.0:
                zs0, zs1, Fs0, Fs1 = _lugre(zs0, zs1, vH0, vH1, Ns, muks, muss, vs, xpre, dt)
        else:
            zb0 = 0.0; zb1 = 0.0; zs0 = 0.0; zs1 = 0.0
        Fw0 = 0.0; Fw1 = 0.0
        if wc > 0.5:
            Fw0 = -(Fb0 + Fs0); Fw1 = -(Fb1 + Fs1)
        if use_bd:
            FB0 += alpha_b * (Fbc0 - FB0); FB1 += alpha_b * (Fbc1 - FB1)
        aM0 = (-Fg0 - ka * dM0 - ba * vM0) / Mh
        aM1 = (-Fg1 - ka * dM1 - ba * vM1) / Mh
        if rigid:
            mt_ = mH + mt
            aH0 = (Fg0 + Fb0 + Fs0 + Fw0 + FB0) / mt_
            aH1 = (Fg1 + Fb1 + Fs1 + Fw1 + FB1) / mt_
            aq0 = 0.0; aq1 = 0.0
            Fa0 = 0.0; Fa1 = 0.0; satf = 0.0; stopf = 0.0
        else:
            # suspension and stops
            Fsu0 = -kt * q0 - ct * vq0; Fsu1 = -kt * q1 - ct * vq1
            rq = math.sqrt(q0 * q0 + q1 * q1)
            stopf = 0.0
            if rq > qstop:
                ux = q0 / rq; uy = q1 / rq
                vrad = vq0 * ux + vq1 * uy
                fs = kstop * (rq - qstop) + (cstop * vrad if vrad > 0 else 0.0)
                Fsu0 -= fs * ux; Fsu1 -= fs * uy
                stopf = 1.0
            # actuator: inverse dynamics of the follower + stiff PD, limited to F_peak
            Fa0 = mt * ar0 + kt * r0 + ct * vr0 + Kpi * (r0 - q0) + Kdi * (vr0 - vq0)
            Fa1 = mt * ar1 + kt * r1 + ct * vr1 + Kpi * (r1 - q1) + Kdi * (vr1 - vq1)
            fm = math.sqrt(Fa0 * Fa0 + Fa1 * Fa1)
            satf = 0.0
            if fm > Fpk:
                Fa0 *= Fpk / fm; Fa1 *= Fpk / fm
                satf = 1.0
            aH0 = (Fg0 + Fs0 + Fw0 - Fa0 - Fsu0) / mH
            aH1 = (Fg1 + Fs1 + Fw1 - Fa1 - Fsu1) / mH
            aq0 = (Fa0 + Fsu0 + Fb0 + FB0) / mt - aH0
            aq1 = (Fa1 + Fsu1 + Fb1 + FB1) / mt - aH1
        # ------------------------------------------------ integrate (semi-implicit Euler)
        vM0 += aM0 * dt; vM1 += aM1 * dt; dM0 += vM0 * dt; dM1 += vM1 * dt
        vH0 += aH0 * dt; vH1 += aH1 * dt; pH0 += vH0 * dt; pH1 += vH1 * dt
        if not rigid:
            vq0 += aq0 * dt; vq1 += aq1 * dt; q0 += vq0 * dt; q1 += vq1 * dt
        # ------------------------------------------------ record
        if k % rdec == 0 and nrec < rec.shape[0]:
            rec[nrec, 0] = k * dt
            rec[nrec, 1] = pH0; rec[nrec, 2] = pH1; rec[nrec, 3] = vH0; rec[nrec, 4] = vH1
            rec[nrec, 5] = aH0; rec[nrec, 6] = aH1; rec[nrec, 7] = q0; rec[nrec, 8] = q1
            rec[nrec, 9] = r0; rec[nrec, 10] = r1; rec[nrec, 11] = qc0; rec[nrec, 12] = qc1
            rec[nrec, 13] = pH0 + q0; rec[nrec, 14] = pH1 + q1
            rec[nrec, 15] = Fa0; rec[nrec, 16] = Fa1; rec[nrec, 17] = Fb0; rec[nrec, 18] = Fb1
            rec[nrec, 19] = Fs0; rec[nrec, 20] = Fs1; rec[nrec, 21] = FB0; rec[nrec, 22] = FB1
            rec[nrec, 23] = Fg0; rec[nrec, 24] = Fg1
            rec[nrec, 25] = 1.0 if con else 0.0; rec[nrec, 26] = g_eff; rec[nrec, 27] = gate
            rec[nrec, 28] = satf; rec[nrec, 29] = stopf; rec[nrec, 30] = prog; rec[nrec, 31] = dist if use_gd else g_sa
            nrec += 1
    return nrec


# ------------------------------------------------------------------ Python interface
@dataclass
class Controls:
    """What drives the tip (and the board) in one run."""
    qext: Optional[np.ndarray] = None       # (n_ticks, 2) external command (m), e.g. -d_hat
    tmpl: Optional[np.ndarray] = None       # (m, 2) template track at the tick rate (page frame, m)
    tmpl_down: Optional[np.ndarray] = None  # (m,) 1 = pen-down template sample
    g_guide: float = 0.0
    capture: float = 2.0e-3
    drop_d: float = 2.5e-3
    drop_t: float = 0.06
    size_gain: tuple = (1.0, 1.0)           # (G_x, G_y); 1 = off
    tau_sa: float = 0.4
    size_gain_track: Optional[np.ndarray] = None   # (n_ticks,) time-varying gain (adaptive size assist); x gain applied
                                                   # only if size_gain[0] > 1
    board: Optional[Board] = None
    board_gain: float = 1.0                 # multiplies Board.K
    board_tmpl: Optional[np.ndarray] = None
    board_tmpl_down: Optional[np.ndarray] = None
    stroke_match: bool = False              # search only the template stroke matching the writer's current stroke
    tau_auth: float = 0.05
    gating: str = "hover"                   # authority on while the pen is in contact ("contact", P1 convention) or
    hover_max: float = 2.0e-3               # within hover_max of the paper ("hover": T7 of docs/ai_guidance.md 7.3)


@dataclass
class Scenario:
    t: np.ndarray
    pref: np.ndarray        # (n, 2) imposed hand path = intended + tremor
    vref: np.ndarray
    down: np.ndarray        # (n,) 1.0 in contact
    intended: np.ndarray    # (n, 2)
    tremor: np.ndarray      # (n, 2) the tremor part of pref
    dt: float
    meta: Dict = field(default_factory=dict)


def scenario_from_written(written, tremor: Optional[np.ndarray] = None, meta: Optional[Dict] = None) -> Scenario:
    it = written.intended
    t = it.t
    dt = float(t[1] - t[0])
    d = np.zeros_like(it.xy) if tremor is None else np.asarray(tremor, float)
    pref = it.xy + d
    vref = np.gradient(pref, dt, axis=0)
    return Scenario(t=t, pref=np.ascontiguousarray(pref), vref=np.ascontiguousarray(vref),
                    down=np.ascontiguousarray(it.pen_down.astype(np.float64)), intended=it.xy, tremor=d, dt=dt,
                    meta=dict(meta or {}, lift=it.lift))


def adapted_path(intended: np.ndarray, dt: float, pen: Pen, hand: Hand, band_hz: Optional[float] = None) -> np.ndarray:
    """The writer's learnt hand path for this pen (ASSUMPTION: an adapted writer whose internal model compensates the
    pen's inertia on the compliant grip; the paper drag is compensated separately, writer_comp).

    Exact inverse of the linear hand-grip-pen chain for the tremor-free writing: F_grip = m_pen x'' and
        p_ref = x + F_grip * [1 / (C_g s + K_g) + 1 / (M s^2 + b_a s + k_a)],
    discretised with the bilinear transform at dt.  band_hz (optional) limits the correction to the writer's internal-
    model bandwidth (zero-phase low-pass of p_ref - x)."""
    from scipy.signal import bilinear, butter, lfilter, sosfiltfilt
    x = np.asarray(intended, float)
    acc = np.gradient(np.gradient(x, dt, axis=0), dt, axis=0)
    F = pen.mass * acc
    fs = 1.0 / dt
    b1, a1 = bilinear([1.0], [hand.C_grip, hand.K_grip], fs)
    b2, a2 = bilinear([1.0], [hand.M_hand, hand.b_arm, hand.k_arm], fs)
    corr = lfilter(b1, a1, F, axis=0) + lfilter(b2, a2, F, axis=0)
    if band_hz is not None:
        corr = sosfiltfilt(butter(4, band_hz, fs=fs, output="sos"), corr, axis=0)
    return x + corr


def with_hand_path(scn: Scenario, hand_path: np.ndarray, tremor: Optional[np.ndarray] = None) -> Scenario:
    """Scenario whose imposed hand path is hand_path (+ tremor); intended letters unchanged."""
    d = np.zeros_like(hand_path) if tremor is None else np.asarray(tremor, float)
    pref = np.ascontiguousarray(hand_path + d)
    return Scenario(t=scn.t, pref=pref, vref=np.ascontiguousarray(np.gradient(pref, scn.dt, axis=0)), down=scn.down,
                    intended=scn.intended, tremor=d, dt=scn.dt, meta=dict(scn.meta))


class Result:
    def __init__(self, rec: np.ndarray, info: Dict):
        self.rec = rec
        self.info = info

    def __getitem__(self, name):
        return self.rec[:, RIDX[name]]

    def xy(self, base):
        i = RIDX[base]
        return self.rec[:, i:i + 2]

    @property
    def t(self):
        return self.rec[:, 0]

    @property
    def ink(self):
        return self.rec[:, RIDX["tipx"]:RIDX["tipx"] + 2]

    @property
    def handle(self):
        return self.rec[:, RIDX["pHx"]:RIDX["pHx"] + 2]

    @property
    def contact(self):
        return self.rec[:, RIDX["contact"]]


def stroke_ranges(tdown: np.ndarray):
    """Start (inclusive) and end (exclusive) sample of every pen-down run of a template track."""
    d = np.diff(np.r_[0, (np.asarray(tdown) > 0.5).astype(np.int8), 0])
    a = np.flatnonzero(d == 1).astype(np.int64)
    b = np.flatnonzero(d == -1).astype(np.int64)
    if len(a) == 0:
        return np.zeros(1, np.int64), np.zeros(1, np.int64)
    return np.ascontiguousarray(a), np.ascontiguousarray(b)


def build_params(scn: Scenario, pen: Pen, hand: Hand, writing: Writing, ctl: Controls, rec_hz: float = 4000.0,
                 inner_hz: Optional[float] = None, page_sensor=(1000.0, 2e-3, 3e-6), contact_latency: float = 1e-3):
    dt = scn.dt
    P = np.zeros(NP)

    def s(name, v):
        P[IDX[name]] = float(v)
    n = len(scn.t)
    tick_decim = max(1, int(round(1.0 / (pen.tick_hz * dt))))
    Ts = tick_decim * dt
    s("dt", dt); s("n", n); s("rec_decim", max(1, int(round(1.0 / (rec_hz * dt))))); s("tick_decim", tick_decim)
    s("Kg", hand.K_grip); s("Cg", hand.C_grip); s("Mh", hand.M_hand); s("ka", hand.k_arm); s("ba", hand.b_arm)
    s("writer_comp", 1.0 if hand.writer_comp == "drag" else 0.0)
    s("rigid", 1.0 if pen.rigid else 0.0)
    m_t = pen.m_tip if not pen.rigid else 0.0
    s("m_H", pen.mass - m_t); s("m_t", m_t if m_t > 0 else 1e-6)
    s("k_t", pen.k_tip); s("c_t", 2.0 * pen.zeta_tip * math.sqrt(max(pen.k_tip, 1e-9) * max(m_t, 1e-6)))
    s("q_lim", pen.q_lim); s("q_tap", pen.q_taper); s("q_stop", pen.q_stop if pen.q_stop > 0 else 1.0)
    s("k_stop", 2.0e4); s("c_stop", 20.0)
    s("w_f", 2.0 * math.pi * max(pen.servo_hz, 1e-3)); s("z_f", pen.servo_zeta)
    s("lat_ticks", int(round(pen.latency / Ts))); s("slew", pen.slew if pen.slew > 0 else 1e3)
    s("F_peak", pen.F_peak if pen.F_peak > 0 else 1e3)
    f_in = inner_hz if inner_hz is not None else max(400.0, 5.0 * max(pen.servo_hz, 1.0))
    w_in = 2.0 * math.pi * f_in
    s("Kp_in", max(m_t, 1e-6) * w_in ** 2); s("Kd_in", 2.0 * 0.7 * max(m_t, 1e-6) * w_in)
    Nb = pen.ball_normal(writing)
    s("N_ball", Nb); s("N_skid", max(writing.N - Nb, 0.0) if pen.skid else 0.0)
    s("mu_b", writing.mu_ball); s("mu_s_b", writing.mu_ball * writing.ms_ratio)
    s("mu_k_skid", writing.mu_skid); s("mu_s_skid", writing.mu_skid * writing.ms_ratio)
    s("v_s", writing.v_s); s("x_pre", writing.x_pre)
    s("con_lat_ticks", int(round(contact_latency / Ts)))
    s("tau_auth", ctl.tau_auth)
    s("use_ext", 1.0 if ctl.qext is not None else 0.0)
    s("use_guide", 1.0 if (ctl.tmpl is not None and ctl.g_guide > 0) else 0.0)
    s("g_guide", ctl.g_guide); s("capture", ctl.capture); s("drop_d", ctl.drop_d); s("drop_t", ctl.drop_t)
    s("use_size", 1.0 if (ctl.size_gain[0] != 1.0 or ctl.size_gain[1] != 1.0) else 0.0)
    s("G_x", ctl.size_gain[0]); s("G_y", ctl.size_gain[1]); s("tau_sa", ctl.tau_sa)
    s("sa_adapt", 1.0 if ctl.size_gain_track is not None else 0.0); s("sa_tau_amp", 0.0); s("sa_t_cal", 0.0)
    if ctl.size_gain_track is not None:
        s("use_size", 1.0)
    rate, lat, noise = page_sensor
    s("ps_lat_ticks", int(round(lat / Ts))); s("ps_noise", noise); s("ps_every", max(1, int(round(1.0 / (rate * Ts)))))
    b = ctl.board
    if b is not None:
        s("use_board", 1.0); s("Kb", b.K * ctl.board_gain); s("Db", b.D * ctl.board_gain); s("F_cap", b.F_cap); s("b_tau", b.tau)
        s("b_dead_ticks", int(round(b.dead / Ts))); s("b_noise", b.noise); s("b_every", max(1, int(round(1.0 / (1000.0 * Ts)))))
        s("b_bias_x", b.bias); s("b_bias_y", 0.0)
    s("stroke_match", 1.0 if ctl.stroke_match else 0.0)
    info = {"tick_decim": tick_decim, "Ts": Ts, "N_ball": Nb, "N_skid": P[IDX["N_skid"]], "inner_hz": f_in,
            "pen": pen.key, "writer_comp": hand.writer_comp}
    return P, info


def run(scn: Scenario, pen: Pen, hand: Optional[Hand] = None, writing: Optional[Writing] = None,
        ctl: Optional[Controls] = None, seed: int = 1, rec_hz: float = 4000.0, **kw) -> Result:
    hand = hand or Hand.from_config()
    writing = writing or Writing()
    ctl = ctl or Controls()
    P, info = build_params(scn, pen, hand, writing, ctl, rec_hz=rec_hz, **kw)
    n = len(scn.t)
    nrec = int(math.ceil(n / P[IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC))
    nt = int(math.ceil(n / P[IDX["tick_decim"]])) + 1
    qext = np.zeros((1, 2)) if ctl.qext is None else np.ascontiguousarray(ctl.qext, dtype=np.float64)
    tm = np.zeros((1, 2)) if ctl.tmpl is None else np.ascontiguousarray(ctl.tmpl, dtype=np.float64)
    td = np.zeros(1) if ctl.tmpl_down is None else np.ascontiguousarray(ctl.tmpl_down, dtype=np.float64)
    bt = tm if ctl.board_tmpl is None else np.ascontiguousarray(ctl.board_tmpl, dtype=np.float64)
    btd = td if ctl.board_tmpl_down is None else np.ascontiguousarray(ctl.board_tmpl_down, dtype=np.float64)
    lift = scn.meta.get("lift")
    if ctl.gating == "hover" and lift is not None:
        active = np.ascontiguousarray(((scn.down > 0.5) | (np.asarray(lift) < ctl.hover_max)).astype(np.float64))
    else:
        active = scn.down
    gsa = np.ones(1) if ctl.size_gain_track is None else np.ascontiguousarray(ctl.size_gain_track, dtype=np.float64)
    tss, tse = stroke_ranges(td)
    btss, btse = stroke_ranges(btd)
    m = simulate(P, scn.pref, scn.vref, scn.down, active, qext, gsa, tm, td, tss, tse, bt, btd, btss, btse, seed, rec)
    info.update({"n_ticks": nt, "rec_hz": rec_hz})
    return Result(rec[:m], info)
