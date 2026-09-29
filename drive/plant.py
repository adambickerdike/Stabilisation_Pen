r"""Model HW1-D: the handwriting study's model HW1 with a friction-limited drive element at the heel (SIMULATION).

Reused from HW1 (handwriting/plant.py, read-only): the hand (imposed path + tremor --[arm k_a, b_a]-- hand mass M
--[grip K_g, C_g]-- handle), the Rev H nose (kinematic follower with force limit and stops), LuGre paper friction at
the ball and the skid ring, the writer's compensation of the writing drag, the page sensor, the nose's guidance law
(capture gate, drop rule, stroke matching) and HW1's parameter vector and helpers (_lugre, _nearest).  With the drive
off and a constant 1 N writing force this model reproduces HW1 (drive/tests/test_drive.py, within 2 um).

Added here (every value ASSUMPTION or CALC unless a ledger id is given; drive/params.py):
  normal load   N_total(t) from the writer (CON-01 statistics, contact.force_profile); ball N_b = F_c / sin(theta);
                heel N_h = N_total - N_b; drive element N_d = min(P, N_h) (sprung, preload P); skid N_s = N_h - N_d.
  tyre          a 2-D bristle between the pen's heel and the element's surface: stiffness k_lat, Stribeck limit
                mu(|s|) N_d, where s = v_handle - W is the slip (W = element surface velocity); rolling resistance
                c_rr N_d along the rolling direction.  Slip is real: when the demanded force exceeds mu N_d the
                element slides and the force falls to the kinetic level.
  element       holonomic (driven ball): surface velocity W (2-D) with reflected mass m_r, back-drive friction and,
                for smooth rollers, the orthogonal roller's axial scrub; steered wheel: heading psi from a steering
                servo (bandwidth, rate limit), rolling speed u with reflected mass m_r, W = u h(psi); the wheel grips
                across its heading (the cobot constraint) and rolls along it free, braked or driven.
  grounded      the desk board as a force on the handle (its law, lag, dead time, sensing noise and normal pull), for
                comparisons in this same plant.
  writer        'imposed' (HW1) or 'relaxed': while the pen is down the writer's anchor follows the hand with a time
                constant (the board study's lead-through model); while the pen is up the writer moves to the next
                stroke by themselves.
Laws (per 2 kHz tick) and the supervisor are in `_control` below; the modes are documented in DMODE.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
from numba import njit

from . import ensure_paths

ensure_paths()
from handwriting import plant as HP  # noqa: E402
from handwriting.plant import IDX as HIDX, REC as HREC, Scenario  # noqa: E402

_lugre = HP._lugre
_nearest = HP._nearest

# ------------------------------------------------------------------------------------------------ HW1 indices
H_dt = HIDX["dt"]; H_n = HIDX["n"]; H_rec = HIDX["rec_decim"]; H_tick = HIDX["tick_decim"]
H_Kg = HIDX["Kg"]; H_Cg = HIDX["Cg"]; H_Mh = HIDX["Mh"]; H_ka = HIDX["ka"]; H_ba = HIDX["ba"]; H_wc = HIDX["writer_comp"]
H_rigid = HIDX["rigid"]; H_mH = HIDX["m_H"]; H_mt = HIDX["m_t"]; H_kt = HIDX["k_t"]; H_ct = HIDX["c_t"]
H_qlim = HIDX["q_lim"]; H_qtap = HIDX["q_tap"]; H_qstop = HIDX["q_stop"]; H_kstop = HIDX["k_stop"]; H_cstop = HIDX["c_stop"]
H_wf = HIDX["w_f"]; H_zf = HIDX["z_f"]; H_lat = HIDX["lat_ticks"]; H_slew = HIDX["slew"]; H_Fpk = HIDX["F_peak"]
H_Kpi = HIDX["Kp_in"]; H_Kdi = HIDX["Kd_in"]
H_mub = HIDX["mu_b"]; H_musb = HIDX["mu_s_b"]; H_muks = HIDX["mu_k_skid"]; H_muss = HIDX["mu_s_skid"]
H_vs = HIDX["v_s"]; H_xpre = HIDX["x_pre"]; H_clat = HIDX["con_lat_ticks"]; H_tauA = HIDX["tau_auth"]
H_ext = HIDX["use_ext"]; H_gd = HIDX["use_guide"]; H_gg = HIDX["g_guide"]; H_cap = HIDX["capture"]; H_dd = HIDX["drop_d"]
H_dtm = HIDX["drop_t"]; H_pslat = HIDX["ps_lat_ticks"]; H_psn = HIDX["ps_noise"]; H_pse = HIDX["ps_every"]
H_smatch = HIDX["stroke_match"]

# ------------------------------------------------------------------------------------------------ drive parameters
DNAMES = [
    "dmode", "dtype", "dlong", "grounded", "relaxed", "tau_relax", "tau_air",
    "P", "F_c", "sin_th", "mu_d", "mu_ds", "v_sd", "k_lat", "c_rr", "m_r", "c_bd", "F_bdc", "scrub",
    "F_cap", "k_safe", "mu_hat0", "slew_d", "tau_m", "N_noise", "Flat_noise", "v_noise",
    # guidance law (holonomic / grounded)
    "sub", "Kp", "band", "Dd", "lead", "lead_v_min", "over_d", "over_t", "fade", "restore",
    # lead / autowrite
    "Kl", "F_lead", "v_lead", "Kv",
    # steering
    "w_s", "z_s", "rate_s", "acc_s", "L_a", "m_eff", "u_min", "free_in_band",
    # tremor laws
    "f_lp", "b_damp", "b_max", "v_min_head", "comp_inertia",
    # board emulation
    "b_tau", "b_dead", "b_noise", "b_pull", "wc_pull_frac",
    # slip rule
    "slip_v", "slip_t", "mu_adapt",
    # drive template search windows
    "win_fwd",
    # tremor steering law: 0 = along the low-passed pen velocity, 1 = toward the low-passed lateral push (free mode)
    "tlaw",
    # path steering law: 0 = pure pursuit (look-ahead L_a), 1 = Stanley (tangent L_t ahead + atan(k_st e / v))
    "plaw", "k_st", "L_t",
    # share of the drive train's own friction (back-drive, scrub) that the controller compensates
    "k_fc",
    # lateral release of the steered wheel (proposed after the test; default off): above the force cap, the heading
    # turns toward the writer's lateral push with apparent mass m_rel, so the constraint reaction is also capped
    "rel_on", "m_rel",
]
DIDX = {n: i for i, n in enumerate(DNAMES)}
NDP = len(DNAMES)
DMODE = {"off": 0, "guide": 1, "lead": 2, "damp": 3, "path": 4, "wheel_tremor": 5, "brake": 6}
DTYPE = {"none": 0, "holo": 1, "wheel": 2}
DLONG = {"free": 0, "brake": 1, "drive": 2, "damp": 3}

REC_X = ["psi", "u", "Wx", "Wy", "Nd", "Ftx", "Fty", "Fmx", "Fmy", "slip", "gy", "muh", "capd", "Flat", "Flong",
         "Frr", "anx", "any", "yield", "slide"]
REC_D = list(HREC) + REC_X
RIDX_D = {n: i for i, n in enumerate(REC_D)}
NREC_D = len(REC_D)
RB = 256

for _n, _i in DIDX.items():
    globals()["D_" + _n] = _i
N_HREC = len(HREC)


@njit(cache=True)
def _tyre(z0, z1, s0, s1, N, mu_k, mu_s, v_s, k, dt):
    """2-D bristle (LuGre with stiffness k per unit deflection, independent of N): the steady deflection is
    g(|s|) N / k in the slip direction; force on the pen F = -k z.  Exact exponential step as HW1's _lugre."""
    sp = math.sqrt(s0 * s0 + s1 * s1)
    g = (mu_k + (mu_s - mu_k) * math.exp(-(sp / v_s) ** 2)) * N
    if N <= 0.0 or k <= 0.0:
        return 0.0, 0.0, 0.0, 0.0
    if sp > 1e-12:
        zs0 = g * s0 / (k * sp); zs1 = g * s1 / (k * sp)
        e = math.exp(-k * sp * dt / max(g, 1e-9))
        z0 = zs0 + (z0 - zs0) * e
        z1 = zs1 + (z1 - zs1) * e
    zm = math.sqrt(z0 * z0 + z1 * z1)
    zl = mu_s * N / k
    if zm > zl:                                    # the load dropped: the bristle cannot hold more than mu_s N
        z0 *= zl / zm; z1 *= zl / zm
    return z0, z1, -k * z0, -k * z1


@njit(cache=True)
def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


@njit(cache=True)
def _near_mod_pi(target, current):
    """target or target + pi, whichever is closer to current (a wheel may roll backwards)."""
    d = _wrap(target - current)
    if d > 0.5 * math.pi:
        d -= math.pi
    elif d < -0.5 * math.pi:
        d += math.pi
    return current + d


@njit(cache=True)
def simulate(P, D, hp, trem, down, active, Ntot, qext, tmpl, tdown, tss, tse, dtm, dtd, dss, dse, dcum, seed, rec):
    np.random.seed(seed)
    dt = P[H_dt]; n = int(P[H_n]); rdec = int(P[H_rec]); tdec = int(P[H_tick])
    Kg = P[H_Kg]; Cg = P[H_Cg]; Mh = P[H_Mh]; ka = P[H_ka]; ba = P[H_ba]; wc = P[H_wc]
    rigid = P[H_rigid] > 0.5; mH = P[H_mH]; mt = P[H_mt]; kt = P[H_kt]; ct = P[H_ct]
    qlim = P[H_qlim]; qtap = P[H_qtap]; qstop = P[H_qstop]; kstop = P[H_kstop]; cstop = P[H_cstop]
    wf = P[H_wf]; zf = P[H_zf]; lat = int(P[H_lat]); slew = P[H_slew]; Fpk = P[H_Fpk]; Kpi = P[H_Kpi]; Kdi = P[H_Kdi]
    mub = P[H_mub]; musb = P[H_musb]; muks = P[H_muks]; muss = P[H_muss]
    vs = P[H_vs]; xpre = P[H_xpre]; clat = int(P[H_clat]); tauA = P[H_tauA]
    use_ext = P[H_ext] > 0.5; use_gd = P[H_gd] > 0.5; gg = P[H_gg]; cap = P[H_cap]; dd_ = P[H_dd]; dtm_ = P[H_dtm]
    pslat = int(P[H_pslat]); psn = P[H_psn]; pse = int(P[H_pse])
    smatch = P[H_smatch] > 0.5
    # drive
    dmode = int(D[D_dmode]); dtype = int(D[D_dtype]); dlong = int(D[D_dlong]); grounded = D[D_grounded] > 0.5
    relaxed = D[D_relaxed] > 0.5; tau_r = D[D_tau_relax]; tau_air = D[D_tau_air]
    Pp = D[D_P]; Fc = D[D_F_c]; sin_th = D[D_sin_th]
    mud = D[D_mu_d]; muds = D[D_mu_ds]; vsd = D[D_v_sd]; klat = D[D_k_lat]; crr = D[D_c_rr]
    m_r = D[D_m_r]; c_bd = D[D_c_bd]; F_bdc = D[D_F_bdc]; scrub = D[D_scrub]
    F_cap = D[D_F_cap]; k_safe = D[D_k_safe]; muh = D[D_mu_hat0]; slew_d = D[D_slew_d]; tau_m = D[D_tau_m]
    N_noise = D[D_N_noise]; Fl_noise = D[D_Flat_noise]; v_noise = D[D_v_noise]
    sub = int(D[D_sub]); Kp = D[D_Kp]; band = D[D_band]; Dd = D[D_Dd]; lead = D[D_lead]; lead_vmin = D[D_lead_v_min]
    over_d = D[D_over_d]; over_t = D[D_over_t]; fade = D[D_fade]; restore = D[D_restore]
    Kl = D[D_Kl]; F_lead = D[D_F_lead]; v_lead = D[D_v_lead]; Kv = D[D_Kv]
    w_s = D[D_w_s]; z_s = D[D_z_s]; rate_s = D[D_rate_s]; acc_s = D[D_acc_s]; L_a = D[D_L_a]
    m_eff = D[D_m_eff]; u_min = D[D_u_min]; free_in_band = D[D_free_in_band] > 0.5
    f_lp = D[D_f_lp]; b_damp = D[D_b_damp]; b_max = D[D_b_max]; v_min_h = D[D_v_min_head]; k_ic = D[D_comp_inertia]
    b_tau = D[D_b_tau]; b_dead = int(D[D_b_dead]); b_noise = D[D_b_noise]; b_pull = D[D_b_pull]; wcpf = D[D_wc_pull_frac]
    slip_v = D[D_slip_v]; slip_t = D[D_slip_t]; mu_adapt = D[D_mu_adapt] > 0.5
    win_fwd = int(D[D_win_fwd])
    tlaw = int(D[D_tlaw])
    plaw = int(D[D_plaw]); k_st = D[D_k_st]; L_t = D[D_L_t]
    k_fc = D[D_k_fc]
    rel_on = D[D_rel_on] > 0.5; m_rel = D[D_m_rel]
    flp = 0.0                                            # low-passed lateral force (tremor steering)
    Nb0 = Fc / sin_th
    Ts = dt * tdec
    engaged = dmode > 0 and (not grounded) and dtype > 0
    # ------------------------------------------------ state
    pH0 = hp[0, 0] + trem[0, 0]; pH1 = hp[0, 1] + trem[0, 1]; vH0 = 0.0; vH1 = 0.0; aH0 = 0.0; aH1 = 0.0
    dM0 = 0.0; dM1 = 0.0; vM0 = 0.0; vM1 = 0.0
    q0 = 0.0; q1 = 0.0; vq0 = 0.0; vq1 = 0.0
    r0 = 0.0; r1 = 0.0; vr0 = 0.0; vr1 = 0.0; ar0 = 0.0; ar1 = 0.0
    zb0 = 0.0; zb1 = 0.0; zs0 = 0.0; zs1 = 0.0; zd0 = 0.0; zd1 = 0.0
    Fa0 = 0.0; Fa1 = 0.0
    qc0 = 0.0; qc1 = 0.0
    an0 = hp[0, 0]; an1 = hp[0, 1]                      # relaxed writer's anchor
    W0 = 0.0; W1 = 0.0; u = 0.0                          # element surface velocity (holo) / rolling speed (wheel)
    psi = 0.0; psid = 0.0; psic = 0.0                    # heading, rate, command
    Fm0 = 0.0; Fm1 = 0.0; Fmc0 = 0.0; Fmc1 = 0.0         # motor force (lagged) and command (holo); wheel uses Fm0
    FB0 = 0.0; FB1 = 0.0                                 # grounded (board) force, lagged
    rb_cmd = np.zeros((RB, 2)); rb_pH = np.zeros((RB, 2)); rb_con = np.zeros(RB); rb_act = np.zeros(RB)
    rb_v = np.zeros((RB, 2)); rb_F = np.zeros((RB, 2))
    ps0 = pH0; ps1 = pH1
    px = pH0; py = pH1                                   # position used by the drive law
    vs0 = 0.0; vs1 = 0.0; vlp0 = 0.0; vlp1 = 0.0; vl20 = 0.0; vl21 = 0.0     # velocity estimate and its low-pass
    prog = 0; reacq = 1; over_tn = 0.0; dropped = 0; was_con = 0; gate = 0.0; dist = 0.0; cur_s = -1
    progd = 0; reacqd = 1; cur_sd = -1; was_cond = 0
    gy = 1.0; t_ov = 0.0; dl0 = 0.0; dl1 = 0.0; mu_h0 = muh; slipf = 0.0; yieldf = 0.0; fp0 = 0.0; fp1 = 0.0; er_prev = 0.0; erd = 0.0
    capd = 0.0; Nd_meas = 0.0; Flat_meas = 0.0; F_rr_rec = 0.0
    tick = 0; nrec = 0; g_eff = 0.0
    alpha_a = 1.0 - math.exp(-Ts / max(tauA, 1e-6))
    alpha_lp = 1.0 - math.exp(-2.0 * math.pi * max(f_lp, 0.05) * Ts)
    alpha_v = 1.0 - math.exp(-2.0 * math.pi * 100.0 * Ts)
    alpha_bd = 1.0 - math.exp(-2.0 * math.pi * 30.0 * Ts)
    alpha_b = 1.0 - math.exp(-dt / max(b_tau, 1e-9))
    alpha_m = 1.0 - math.exp(-dt / max(tau_m, 1e-9))
    nt = qext.shape[0]
    satf = 0.0; stopf = 0.0
    Nd = 0.0; Ft0 = 0.0; Ft1 = 0.0; slide = 0.0
    for k in range(n):
        con = down[k] > 0.5
        # ================================================================== controller tick
        if k % tdec == 0:
            j = tick % RB
            rb_pH[j, 0] = pH0; rb_pH[j, 1] = pH1
            rb_con[j] = 1.0 if con else 0.0
            rb_act[j] = active[k]
            rb_v[j, 0] = vH0; rb_v[j, 1] = vH1
            jc = (tick - clat) % RB if tick >= clat else 0
            con_s = rb_con[jc] > 0.5 if tick >= clat else False
            act_s = rb_act[jc] > 0.5 if tick >= clat else False
            if tick % pse == 0:
                jp = (tick - pslat) % RB if tick >= pslat else 0
                ps0 = rb_pH[jp, 0] + psn * np.random.standard_normal()
                ps1 = rb_pH[jp, 1] + psn * np.random.standard_normal()
            # optical velocity (1 tick old) + noise, 100 Hz filter; and its low-pass (intended-motion estimate)
            jv = (tick - 2) % RB if tick >= 2 else 0
            if engaged:
                nv0 = v_noise * np.random.standard_normal(); nv1 = v_noise * np.random.standard_normal()
            else:
                nv0 = 0.0; nv1 = 0.0
            vs0 += alpha_v * (rb_v[jv, 0] + nv0 - vs0)
            vs1 += alpha_v * (rb_v[jv, 1] + nv1 - vs1)
            vlp0 += alpha_lp * (vs0 - vlp0); vlp1 += alpha_lp * (vs1 - vlp1)
            vl20 += alpha_lp * (vlp0 - vl20); vl21 += alpha_lp * (vlp1 - vl21)          # 2nd-order low-pass
            target = 1.0 if act_s else 0.0
            g_eff = g_eff + alpha_a * (target - g_eff)
            # ---------------------------------------------- nose (HW1 law: external command + template guidance)
            c0 = 0.0; c1 = 0.0
            if use_ext and tick < nt:
                c0 += qext[tick, 0]; c1 += qext[tick, 1]
            if use_gd:
                if con_s:
                    if was_con == 0:
                        dropped = 0; over_tn = 0.0
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
                        over_tn += Ts
                    else:
                        over_tn = 0.0
                    if over_tn > dtm_:
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
            was_con = 1 if con_s else 0
            c0 *= g_eff; c1 *= g_eff
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
            # ---------------------------------------------- drive law
            if engaged:
                Nd_meas = Nd + N_noise * np.random.standard_normal() if Nd > 0.0 else 0.0
                Flat_meas = Fl_noise * np.random.standard_normal()
            else:
                Nd_meas = 0.0; Flat_meas = 0.0
            if dtype == 2:
                hx = math.cos(psi); hy = math.sin(psi)
                Flat_meas += -Ft0 * hy + Ft1 * hx          # tyre force across the heading (wheel-mount sensor)
            f0 = 0.0; f1 = 0.0; want_psi = psic; F_along = 0.0; has_long = False
            # the position the drive law uses: the board senses the handle itself (1 kHz, its own noise); the pen uses
            # its page sensor
            if grounded:
                if tick % pse == 0 and dmode > 0:
                    px = pH0 + b_noise * np.random.standard_normal()
                    py = pH1 + b_noise * np.random.standard_normal()
            else:
                px = ps0; py = ps1
            if dmode > 0 and con_s:
                # template progress (stroke matched), error toward the template, tangent
                if dtm.shape[0] > 1:
                    if was_cond == 0:
                        reacqd = 1
                        if smatch:
                            cur_sd += 1
                            if cur_sd < dss.shape[0]:
                                progd = dss[cur_sd]
                    blo = 0; bhi = dtm.shape[0]
                    if smatch and cur_sd < dss.shape[0]:
                        blo = dss[cur_sd]; bhi = dse[cur_sd]
                        bj, bdist = _nearest(dtm, dtd, px, py, progd, 20, win_fwd, blo, bhi)
                    elif smatch:
                        bj, bdist = progd, 1e3
                    else:
                        bj, bdist = _nearest(dtm, dtd, px, py, progd, 20, 4000 if reacqd == 1 else win_fwd)
                    reacqd = 0
                    progd = bj
                    e0 = dtm[progd, 0] - px; e1 = dtm[progd, 1] - py
                    er = math.sqrt(e0 * e0 + e1 * e1)
                    ja = progd - 1 if progd - 1 >= blo else blo
                    jb = progd + 1 if progd + 1 < bhi else bhi - 1
                    tx = dtm[jb, 0] - dtm[ja, 0]; ty = dtm[jb, 1] - dtm[ja, 1]
                    tn = math.sqrt(tx * tx + ty * ty)
                    if tn > 0.0:                                      # HW1's tangent (the board law uses it)
                        tx /= tn; ty /= tn
                    # arc-length tangent over +/-0.3 mm (defined at stroke starts, where the template dwells)
                    jf = progd
                    while jf + 1 < bhi and dcum[jf] - dcum[progd] < 0.3e-3:
                        jf += 1
                    jr = progd
                    while jr - 1 >= blo and dcum[progd] - dcum[jr] < 0.3e-3:
                        jr -= 1
                    sx = dtm[jf, 0] - dtm[jr, 0]; sy = dtm[jf, 1] - dtm[jr, 1]
                    sn = math.sqrt(sx * sx + sy * sy)
                    if sn > 0.0:
                        sx /= sn; sy /= sn
                    end_zone = dcum[bhi - 1] - dcum[progd] < 0.3e-3
                    if was_cond == 0:
                        er_prev = er; erd = 0.0
                    erd += alpha_bd * ((er - er_prev) / Ts - erd)
                    er_prev = er
                else:
                    e0 = 0.0; e1 = 0.0; er = 0.0; tx = 1.0; ty = 0.0; bdist = 0.0; blo = 0; bhi = 1
                    sx = 1.0; sy = 0.0; end_zone = False
                ux = e0 / er if er > 1e-12 else 0.0
                uy = e1 / er if er > 1e-12 else 0.0
                # supervisor: yield when the writer keeps deviating (board rule), restore near the path
                if dmode in (1, 2, 4):
                    if er > over_d:
                        t_ov += Ts
                    else:
                        t_ov = max(0.0, t_ov - Ts)
                    if t_ov > over_t:
                        if gy > 0.99:
                            yieldf += 1.0
                        gy = max(0.0, gy - Ts / fade)
                    elif er < 1e-3:
                        gy = min(1.0, gy + Ts / restore)
                # -------- holonomic / grounded impedance guidance (the board's law)
                if dmode == 1:
                    if sub == 1:                                       # partial: band, spring, damping
                        mag = er - band
                        if mag > 0.0:
                            fm_ = Kp * mag + Dd * erd
                            f0 = fm_ * ux; f1 = fm_ * uy
                    else:                                              # full: spring + damping + lead
                        f0 = Kp * e0 + Dd * erd * ux; f1 = Kp * e1 + Dd * erd * uy
                        vfw = (vH0 * tx + vH1 * ty) if grounded else (vs0 * tx + vs1 * ty)
                        if vfw > lead_vmin:
                            f0 += lead * tx; f1 += lead * ty
                    f0 *= gy; f1 *= gy
                    if bdist > 1.0:
                        f0 = 0.0; f1 = 0.0
                elif dmode == 2 and dtype == 1:                       # holonomic lead: spring + push along the path
                    v_al = vs0 * sx + vs1 * sy
                    F_along = max(0.0, F_lead + Kv * (v_lead - v_al))
                    if end_zone:
                        F_along = -Kv * v_al                           # end of the stroke: stop there
                    f0 = (Kl * e0 + F_along * sx) * gy; f1 = (Kl * e1 + F_along * sy) * gy
                elif dmode == 3:                                       # active tremor damping (high-pass velocity)
                    f0 = -b_damp * (vs0 - vl20); f1 = -b_damp * (vs1 - vl21)
                elif dmode == 6:                                       # isotropic brake (semi-active)
                    f0 = -b_damp * (vs0 - vl20); f1 = -b_damp * (vs1 - vl21)
                # -------- steered wheel: heading
                if dtype == 2:
                    if dmode == 5:                                     # tremor: follow the intended direction
                        flp += alpha_lp * (Flat_meas - flp)
                        if tlaw == 1:
                            # free mode (LIT HAP-60 eq. 2) on the low-passed push: a virtual mass m_eff across the
                            # heading; the fast, zero-mean tremor push barely turns the wheel
                            um = max(abs(u), u_min)
                            want_psi = psic + flp / (m_eff * um) * Ts
                        else:
                            vm_ = math.sqrt(vl20 * vl20 + vl21 * vl21)
                            if vm_ > v_min_h:
                                want_psi = _near_mod_pi(math.atan2(vl21, vl20), psic)
                    elif dmode in (2, 4):
                        # pure pursuit: aim at the template point L_a ahead of the projection
                        jla = progd
                        s0_ = dcum[progd]
                        while jla + 1 < bhi and dcum[jla] - s0_ < L_a:
                            jla += 1
                        ax_ = dtm[jla, 0] - ps0; ay_ = dtm[jla, 1] - ps1
                        if math.sqrt(ax_ * ax_ + ay_ * ay_) < 1e-5:
                            ax_ = sx; ay_ = sy
                        in_band = er < band
                        if (free_in_band and in_band) or gy < 0.5:
                            # free mode (LIT HAP-60 eq. 2): steer toward the writer's lateral push
                            um = max(abs(u), u_min)
                            want_psi = psic + Flat_meas / (m_eff * um) * Ts
                        elif plaw == 1:
                            # Stanley law: the template tangent L_t ahead (covers the steering lag) plus a correction
                            # toward the path that grows with the cross-track error and shrinks with speed
                            jt = progd
                            while jt + 1 < bhi and dcum[jt] - dcum[progd] < L_t:
                                jt += 1
                            jf2 = jt
                            while jf2 + 1 < bhi and dcum[jf2] - dcum[jt] < 0.3e-3:
                                jf2 += 1
                            jr2 = jt
                            while jr2 - 1 >= blo and dcum[jt] - dcum[jr2] < 0.3e-3:
                                jr2 -= 1
                            qx_ = dtm[jf2, 0] - dtm[jr2, 0]; qy_ = dtm[jf2, 1] - dtm[jr2, 1]
                            qn_ = math.sqrt(qx_ * qx_ + qy_ * qy_)
                            if qn_ > 0.0:
                                qx_ /= qn_; qy_ /= qn_
                            else:
                                qx_ = sx; qy_ = sy
                            # the travel direction along the path (the writer may go either way): follow the pen
                            if vs0 * qx_ + vs1 * qy_ < 0.0 and (vs0 * vs0 + vs1 * vs1) > 1e-6:
                                qx_ = -qx_; qy_ = -qy_
                            ecr = e0 * (-qy_) + e1 * qx_          # template to the left of the travel direction > 0
                            vm_ = math.sqrt(vs0 * vs0 + vs1 * vs1)
                            want_psi = _near_mod_pi(math.atan2(qy_, qx_) + math.atan(k_st * ecr / (vm_ + 0.005)), psic)
                        else:
                            want_psi = _near_mod_pi(math.atan2(ay_, ax_), psic)
                        if rel_on and abs(Flat_meas) > capd and capd > 0.0:
                            # lateral release: the excess of the across-heading reaction over the cap turns the
                            # wheel toward the push (free mode on the excess only)
                            um = max(abs(u), u_min)
                            exc = abs(Flat_meas) - capd
                            want_psi += math.copysign(exc, Flat_meas) / (m_rel * um) * Ts
                        # longitudinal push along the path direction (sign by the heading): lead-through /
                        # autowrite regulates the speed; path guidance adds the board's small lead while the
                        # writer moves forward
                        if dlong == 2:
                            has_long = True
                            sgn = 1.0 if (math.cos(psi) * sx + math.sin(psi) * sy) >= 0.0 else -1.0
                            v_al = vs0 * sx + vs1 * sy
                            if dmode == 2:
                                F_along = sgn * max(0.0, F_lead + Kv * (v_lead - v_al)) * gy
                                if end_zone:
                                    F_along = -sgn * Kv * v_al         # end of the stroke: stop there
                            elif v_al > lead_vmin:
                                F_along = sgn * lead * gy
                    psic = want_psi
            elif dmode > 0:
                # pen up: zero force; pre-steer the wheel to the next stroke's first direction (the app knows it)
                if dtype == 2 and dtm.shape[0] > 1 and dmode in (2, 4):
                    ns = cur_sd + 1
                    if ns < dss.shape[0]:
                        a_ = dss[ns]; b_ = a_
                        while b_ + 1 < dse[ns] and dcum[b_] - dcum[a_] < 0.5e-3:
                            b_ += 1
                        dx_ = dtm[b_, 0] - dtm[a_, 0]; dy_ = dtm[b_, 1] - dtm[a_, 1]
                        if dx_ * dx_ + dy_ * dy_ > 1e-12:
                            psic = _near_mod_pi(math.atan2(dy_, dx_), psic)
                gy = 1.0; t_ov = 0.0
            was_cond = 1 if con_s else 0
            # force cap from the traction estimate (never above mu_hat k_safe N_d), slew limit
            if grounded:
                capd = F_cap
            else:
                capd = min(F_cap, k_safe * muh * max(Nd_meas, 0.0))
            fm = math.sqrt(f0 * f0 + f1 * f1)
            if fm > capd:
                if fm > 0.0:
                    f0 *= capd / fm; f1 *= capd / fm
            if not con_s:
                f0 = 0.0; f1 = 0.0
            d0_ = f0 - fp0; d1_ = f1 - fp1
            dn_ = math.sqrt(d0_ * d0_ + d1_ * d1_)
            if dn_ > slew_d * Ts:
                f0 = fp0 + d0_ * slew_d * Ts / dn_; f1 = fp1 + d1_ * slew_d * Ts / dn_
            fp0 = f0; fp1 = f1
            # slip detection: pen velocity against the element's surface velocity
            if engaged and con_s and Nd_meas > 0.02:
                if dtype == 2:
                    wx_ = u * math.cos(psi); wy_ = u * math.sin(psi)
                else:
                    wx_ = W0; wy_ = W1
                # relative travel of the heel over the element surface, with a 50 ms leak (sensor bias); more than
                # the tyre can deflect elastically (1.5 x mu_max N_d / k_lat) means gross sliding
                rv0 = vs0 - wx_; rv1 = vs1 - wy_
                if dtype == 2 and dlong == 0:
                    # a free wheel can only slide across its heading
                    c_ = math.cos(psi); s_ = math.sin(psi)
                    lat_ = -rv0 * s_ + rv1 * c_
                    rv0 = -lat_ * s_; rv1 = lat_ * c_
                dl0 += rv0 * Ts - dl0 * Ts / slip_t; dl1 += rv1 * Ts - dl1 * Ts / slip_t
                d_th = 1.5 * 1.2 * Nd_meas / klat + slip_v * 0.004
                if math.sqrt(dl0 * dl0 + dl1 * dl1) > d_th:
                    if slipf < 0.5 and mu_adapt:
                        muh = max(0.3, 0.9 * muh)
                    slipf = 1.0
                else:
                    slipf = 0.0
                    muh += (mu_h0 - muh) * Ts / 2.0          # recover the estimate over about 2 s without slip
            else:
                slipf = 0.0; dl0 = 0.0; dl1 = 0.0
            # commands to the actuators
            if grounded:
                rb_F[j, 0] = f0; rb_F[j, 1] = f1
            elif dtype == 1:
                if dmode == 6:
                    # brake on the ball: can only oppose the ball's rolling (dissipative), up to b_max per m/s
                    wm_ = math.sqrt(W0 * W0 + W1 * W1)
                    bb = 0.0
                    if wm_ > 1e-4:
                        bb = max(0.0, -(f0 * W0 + f1 * W1)) / (wm_ * wm_)
                        bb = min(bb, b_max)
                    Fmc0 = -bb * W0; Fmc1 = -bb * W1
                else:
                    # force control with friction and (partial) inertia compensation of the element
                    wm_ = math.sqrt(W0 * W0 + W1 * W1)
                    cf0 = c_bd * W0 + (F_bdc + scrub) * (W0 / wm_ if wm_ > 1e-3 else W0 / 1e-3)
                    cf1 = c_bd * W1 + (F_bdc + scrub) * (W1 / wm_ if wm_ > 1e-3 else W1 / 1e-3)
                    Fmc0 = f0 + k_fc * cf0 + k_ic * m_r * aH0
                    Fmc1 = f1 + k_fc * cf1 + k_ic * m_r * aH1
            elif dtype == 2:
                hx = math.cos(psi); hy = math.sin(psi)
                fl = f0 * hx + f1 * hy                  # component of the force law along the heading
                if dlong == 0:
                    Fmc0 = 0.0
                elif dlong == 1:                        # axle brake: dissipative
                    if dmode == 5:
                        vh_ = (vs0 - vl20) * hx + (vs1 - vl21) * hy
                        Fd_ = -b_damp * vh_
                        Fmc0 = Fd_ if Fd_ * u < 0.0 else 0.0
                        if abs(Fmc0) > b_max * abs(u):
                            Fmc0 = -b_max * u
                    else:
                        Fmc0 = -min(b_damp, b_max) * u
                elif dlong == 3:                        # active along-path damping with the drive motor
                    vh_ = (vs0 - vl20) * hx + (vs1 - vl21) * hy
                    Fmc0 = max(-capd, min(capd, -b_damp * vh_)) + k_fc * (c_bd * u + F_bdc * math.tanh(u / 1e-3))
                else:                                   # driven: push along the heading, force-limited
                    if has_long:
                        Fmc0 = max(-capd, min(capd, F_along)) + k_fc * (c_bd * u + F_bdc * math.tanh(u / 1e-3))
                    else:
                        Fmc0 = max(-capd, min(capd, fl)) + k_fc * (c_bd * u + F_bdc * math.tanh(u / 1e-3))
                if not con_s:
                    Fmc0 = k_fc * (c_bd * u + F_bdc * math.tanh(u / 1e-3)) if dlong >= 2 else 0.0
            tick += 1
        # ================================================================== follower (nose)
        if not rigid:
            tk = tick - 1 - lat
            if tk >= 0:
                uu0 = rb_cmd[tk % RB, 0]; uu1 = rb_cmd[tk % RB, 1]
            else:
                uu0 = 0.0; uu1 = 0.0
            ar0 = wf * wf * (uu0 - r0) - 2.0 * zf * wf * vr0
            ar1 = wf * wf * (uu1 - r1) - 2.0 * zf * wf * vr1
            vr0 += ar0 * dt; vr1 += ar1 * dt
            r0 += vr0 * dt; r1 += vr1 * dt
        # ================================================================== normal loads
        if con:
            Nt = Ntot[k]
            Nb = min(Nt, Nb0)
            Nh = max(Nt - Nb, 0.0)
            Nd = min(Nh, Pp) if engaged else 0.0
            Ns = Nh - Nd
            Ns_w = Ns
            if grounded and dmode > 0:
                Ns += b_pull
        else:
            Nb = 0.0; Nd = 0.0; Ns = 0.0; Ns_w = 0.0
        # ================================================================== steering servo
        if dtype == 2:
            acc = w_s * w_s * _wrap(psic - psi) - 2.0 * z_s * w_s * psid
            acc = max(-acc_s, min(acc_s, acc))
            psid += acc * dt
            psid = max(-rate_s, min(rate_s, psid))
            psi += psid * dt
        # ================================================================== forces
        if relaxed and con:
            an0 += dM0 * dt / tau_r; an1 += dM1 * dt / tau_r
            dM0 -= dM0 * dt / tau_r; dM1 -= dM1 * dt / tau_r
            pr0 = an0 + trem[k, 0]; pr1 = an1 + trem[k, 1]
            vp0 = trem[min(k + 1, n - 1), 0] - trem[k, 0]; vp1 = trem[min(k + 1, n - 1), 1] - trem[k, 1]
            vp0 /= dt; vp1 /= dt
        elif relaxed:
            an0 += (hp[k, 0] - an0) * dt / tau_air; an1 += (hp[k, 1] - an1) * dt / tau_air
            pr0 = an0 + trem[k, 0]; pr1 = an1 + trem[k, 1]
            vp0 = (hp[k, 0] - an0) / tau_air; vp1 = (hp[k, 1] - an1) / tau_air
        else:
            pr0 = hp[k, 0] + trem[k, 0]; pr1 = hp[k, 1] + trem[k, 1]
            kk = min(k + 1, n - 1)
            vp0 = (hp[kk, 0] + trem[kk, 0] - pr0) / dt; vp1 = (hp[kk, 1] + trem[kk, 1] - pr1) / dt
        Fg0 = Kg * (pr0 + dM0 - pH0) + Cg * (vp0 + vM0 - vH0)
        Fg1 = Kg * (pr1 + dM1 - pH1) + Cg * (vp1 + vM1 - vH1)
        Fb0 = 0.0; Fb1 = 0.0; Fs0 = 0.0; Fs1 = 0.0
        if con:
            zb0, zb1, Fb0, Fb1 = _lugre(zb0, zb1, vH0 + vq0, vH1 + vq1, Nb, mub, musb, vs, xpre, dt)
            if Ns > 0.0:
                zs0, zs1, Fs0, Fs1 = _lugre(zs0, zs1, vH0, vH1, Ns, muks, muss, vs, xpre, dt)
            else:
                zs0 = 0.0; zs1 = 0.0
        else:
            zb0 = 0.0; zb1 = 0.0; zs0 = 0.0; zs1 = 0.0
        # drive element contact
        Ft0 = 0.0; Ft1 = 0.0; Frr0 = 0.0; Frr1 = 0.0; Fsc0 = 0.0; Fsc1 = 0.0
        if engaged and Nd > 0.0:
            if dtype == 2:
                hx = math.cos(psi); hy = math.sin(psi)
                Wx = u * hx; Wy = u * hy
            else:
                Wx = W0; Wy = W1
            zd0, zd1, Ft0, Ft1 = _tyre(zd0, zd1, vH0 - Wx, vH1 - Wy, Nd, mud, muds, vsd, klat, dt)
            sl_ = math.sqrt((vH0 - Wx) ** 2 + (vH1 - Wy) ** 2)
            slide = 1.0 if (math.sqrt(Ft0 * Ft0 + Ft1 * Ft1) >= 0.97 * mud * Nd and sl_ > 2e-3) else 0.0
            # rolling resistance along the rolling direction (on the pen)
            wm_ = math.sqrt(Wx * Wx + Wy * Wy)
            if wm_ > 1e-9:
                th_ = math.tanh(wm_ / 1e-3)
                Frr0 = -crr * Nd * th_ * Wx / wm_; Frr1 = -crr * Nd * th_ * Wy / wm_
        else:
            zd0 = 0.0; zd1 = 0.0; slide = 0.0
        F_rr_rec = math.sqrt(Frr0 * Frr0 + Frr1 * Frr1)
        Fw0 = 0.0; Fw1 = 0.0
        if wc > 0.5:
            fr = Ns_w / Ns if Ns > 0.0 else 1.0
            Fw0 = -(Fb0 + fr * Fs0 + Frr0); Fw1 = -(Fb1 + fr * Fs1 + Frr1)
        # grounded (board) force: dead time + first-order lag
        if grounded:
            jd = (tick - 1 - b_dead) % RB if tick - 1 >= b_dead else 0
            fc0 = rb_F[jd, 0] if tick - 1 >= b_dead else 0.0
            fc1 = rb_F[jd, 1] if tick - 1 >= b_dead else 0.0
            FB0 += alpha_b * (fc0 - FB0); FB1 += alpha_b * (fc1 - FB1)
        # element dynamics
        if engaged:
            if dtype == 1:
                Fm0 += alpha_m * (Fmc0 - Fm0); Fm1 += alpha_m * (Fmc1 - Fm1)
                wm_ = math.sqrt(W0 * W0 + W1 * W1)
                fr0 = c_bd * W0 + (F_bdc + scrub) * math.tanh(wm_ / 1e-3) * (W0 / wm_ if wm_ > 1e-9 else 0.0)
                fr1 = c_bd * W1 + (F_bdc + scrub) * math.tanh(wm_ / 1e-3) * (W1 / wm_ if wm_ > 1e-9 else 0.0)
                W0 += (Fm0 - Ft0 - fr0) / m_r * dt
                W1 += (Fm1 - Ft1 - fr1) / m_r * dt
                if not con:
                    W0 *= 0.99; W1 *= 0.99
            else:
                Fm0 += alpha_m * (Fmc0 - Fm0)
                hx = math.cos(psi); hy = math.sin(psi)
                fr_ = c_bd * u + F_bdc * math.tanh(u / 1e-3)
                u += (Fm0 - (Ft0 * hx + Ft1 * hy) - fr_) / m_r * dt
                if not con:
                    u *= 0.99
        # hand
        aM0 = (-Fg0 - ka * dM0 - ba * vM0) / Mh
        aM1 = (-Fg1 - ka * dM1 - ba * vM1) / Mh
        Fe0 = Ft0 + Frr0 + Fsc0 + FB0; Fe1 = Ft1 + Frr1 + Fsc1 + FB1   # external drive forces on the handle
        if rigid:
            aH0 = (Fg0 + Fb0 + Fs0 + Fw0 + Fe0) / (mH + mt)
            aH1 = (Fg1 + Fb1 + Fs1 + Fw1 + Fe1) / (mH + mt)
            Fa0 = 0.0; Fa1 = 0.0; satf = 0.0; stopf = 0.0; aq0 = 0.0; aq1 = 0.0
        else:
            Fsu0 = -kt * q0 - ct * vq0; Fsu1 = -kt * q1 - ct * vq1
            rq = math.sqrt(q0 * q0 + q1 * q1)
            stopf = 0.0
            if rq > qstop:
                ux_ = q0 / rq; uy_ = q1 / rq
                vrad = vq0 * ux_ + vq1 * uy_
                fs = kstop * (rq - qstop) + (cstop * vrad if vrad > 0 else 0.0)
                Fsu0 -= fs * ux_; Fsu1 -= fs * uy_
                stopf = 1.0
            Fa0 = mt * ar0 + kt * r0 + ct * vr0 + Kpi * (r0 - q0) + Kdi * (vr0 - vq0)
            Fa1 = mt * ar1 + kt * r1 + ct * vr1 + Kpi * (r1 - q1) + Kdi * (vr1 - vq1)
            fm = math.sqrt(Fa0 * Fa0 + Fa1 * Fa1)
            satf = 0.0
            if fm > Fpk:
                Fa0 *= Fpk / fm; Fa1 *= Fpk / fm
                satf = 1.0
            aH0 = (Fg0 + Fs0 + Fw0 + Fe0 - Fa0 - Fsu0) / mH
            aH1 = (Fg1 + Fs1 + Fw1 + Fe1 - Fa1 - Fsu1) / mH
            aq0 = (Fa0 + Fsu0 + Fb0) / mt - aH0
            aq1 = (Fa1 + Fsu1 + Fb1) / mt - aH1
        vM0 += aM0 * dt; vM1 += aM1 * dt; dM0 += vM0 * dt; dM1 += vM1 * dt
        vH0 += aH0 * dt; vH1 += aH1 * dt; pH0 += vH0 * dt; pH1 += vH1 * dt
        if not rigid:
            vq0 += aq0 * dt; vq1 += aq1 * dt; q0 += vq0 * dt; q1 += vq1 * dt
        # ================================================================== record
        if k % rdec == 0 and nrec < rec.shape[0]:
            rec[nrec, 0] = k * dt
            rec[nrec, 1] = pH0; rec[nrec, 2] = pH1; rec[nrec, 3] = vH0; rec[nrec, 4] = vH1
            rec[nrec, 5] = aH0; rec[nrec, 6] = aH1; rec[nrec, 7] = q0; rec[nrec, 8] = q1
            rec[nrec, 9] = r0; rec[nrec, 10] = r1; rec[nrec, 11] = qc0; rec[nrec, 12] = qc1
            rec[nrec, 13] = pH0 + q0; rec[nrec, 14] = pH1 + q1
            rec[nrec, 15] = Fa0; rec[nrec, 16] = Fa1; rec[nrec, 17] = Fb0; rec[nrec, 18] = Fb1
            rec[nrec, 19] = Fs0; rec[nrec, 20] = Fs1; rec[nrec, 21] = Fe0; rec[nrec, 22] = Fe1
            rec[nrec, 23] = Fg0; rec[nrec, 24] = Fg1
            rec[nrec, 25] = 1.0 if con else 0.0; rec[nrec, 26] = g_eff; rec[nrec, 27] = gate
            rec[nrec, 28] = satf; rec[nrec, 29] = stopf; rec[nrec, 30] = prog; rec[nrec, 31] = dist
            b = N_HREC
            rec[nrec, b + 0] = psi; rec[nrec, b + 1] = u; rec[nrec, b + 2] = W0; rec[nrec, b + 3] = W1
            rec[nrec, b + 4] = Nd; rec[nrec, b + 5] = Ft0; rec[nrec, b + 6] = Ft1
            rec[nrec, b + 7] = Fm0; rec[nrec, b + 8] = Fm1; rec[nrec, b + 9] = slipf; rec[nrec, b + 10] = gy
            rec[nrec, b + 11] = muh; rec[nrec, b + 12] = capd; rec[nrec, b + 13] = Flat_meas
            if dtype == 2:
                rec[nrec, b + 14] = Ft0 * math.cos(psi) + Ft1 * math.sin(psi)
            else:
                rec[nrec, b + 14] = 0.0
            rec[nrec, b + 15] = F_rr_rec; rec[nrec, b + 16] = an0; rec[nrec, b + 17] = an1; rec[nrec, b + 18] = yieldf
            rec[nrec, b + 19] = slide
            nrec += 1
    return nrec


# ------------------------------------------------------------------------------------------------ Python interface
@dataclass
class Drive:
    """One heel-drive configuration (defaults: the nominal steered wheel of docs/grounded_drive.md, law off)."""
    mode: str = "off"                 # DMODE key
    kind: str = "none"                # DTYPE key
    long: str = "free"                # DLONG key (wheel)
    grounded: bool = False            # the desk board (force on the handle, no traction limit)
    P: float = 0.5                    # N preload
    mu: float = 0.9                   # true tyre-paper friction
    mu_static_ratio: float = 1.1
    v_s: float = 0.002
    k_lat: float = 1500.0             # N/m tyre tangential stiffness
    c_rr: float = 0.05                # rolling resistance / N_d
    m_r: float = 0.0068               # kg reflected mass of the element (0620 B, 4:1, r 1.5 mm)
    c_bd: float = 0.0                 # N s/m back-drive viscous
    F_bdc: float = 0.033              # N back-drive Coulomb
    scrub: float = 0.0                # N ball: axial scrub of the orthogonal roller
    F_cap: float = 0.5
    k_safe: float = 0.8
    mu_hat0: Optional[float] = None   # controller's traction estimate (None: calibrated, 0.9 x mu)
    slew: float = 20.0
    tau_m: float = 0.0005
    N_noise: float = 0.01
    Flat_noise: float = 0.005
    v_noise: float = 0.002            # m/s optical-velocity noise
    sub: int = 2                      # 1 partial, 2 full (guide)
    Kp: float = 200.0
    band: float = 1.0e-3
    D: float = 2.0
    lead: float = 0.1
    lead_v_min: float = 3e-3
    over_d: float = 4e-3
    over_t: float = 0.3
    fade: float = 0.3
    restore: float = 0.5
    Kl: float = 200.0                 # N/m lead spring
    F_lead: float = 0.3               # N lead push
    v_lead: float = 0.02              # m/s lead speed (wheel velocity source)
    Kv: float = 10.0                  # N s/m speed regulation of the lead push (lead-through / autowrite)
    w_s: float = 2 * math.pi * 40.0   # steering servo natural frequency
    z_s: float = 0.8
    rate_s: float = 500.0             # rad/s
    acc_s: float = 2.0e5              # rad/s^2
    L_a: float = 1.0e-3               # m look-ahead
    m_eff: float = 0.05               # kg free-mode apparent mass
    u_min: float = 5e-3
    free_in_band: bool = False
    f_lp: float = 3.0                 # Hz intended-direction low-pass
    b_damp: float = 5.0               # N s/m
    b_max: float = 50.0
    v_min_head: float = 3e-3
    comp_inertia: float = 0.8
    b_tau: float = 0.0064             # board lag (board_params.json)
    b_dead: int = 3                   # ticks
    b_noise: float = 0.18e-3          # board sensing noise (m)
    b_pull: float = 0.98              # N normal pull while guiding
    slip_v: float = 8e-3              # m/s: adds slip_v x 4 ms to the travel threshold (sensor noise margin)
    slip_t: float = 0.05              # s leak of the relative-travel integrator
    mu_adapt: bool = True
    win_fwd: int = 400
    tlaw: int = 1
    plaw: int = 0
    k_st: float = 5.0                 # 1/s Stanley cross-track gain
    L_t: float = 0.3e-3               # m tangent look-ahead (Stanley)
    k_fc: float = 0.7                 # compensated share of the drive's own friction (ASSUMPTION)
    rel_on: bool = False              # lateral release of the steered wheel (proposed; off in the frozen test)
    m_rel: float = 0.02               # kg apparent mass of the release (ASSUMPTION)
    relaxed: bool = False
    tau_relax: float = 0.25
    tau_air: float = 0.05

    def vector(self, theta_deg: float = 50.0, F_c: float = 0.15) -> np.ndarray:
        D = np.zeros(NDP)

        def s(k, v):
            D[DIDX[k]] = float(v)
        s("dmode", DMODE[self.mode]); s("dtype", DTYPE[self.kind]); s("dlong", DLONG[self.long])
        s("grounded", self.grounded); s("relaxed", self.relaxed); s("tau_relax", self.tau_relax); s("tau_air", self.tau_air)
        s("P", self.P); s("F_c", F_c); s("sin_th", math.sin(math.radians(theta_deg)))
        s("mu_d", self.mu); s("mu_ds", self.mu * self.mu_static_ratio); s("v_sd", self.v_s); s("k_lat", self.k_lat)
        s("c_rr", self.c_rr); s("m_r", max(self.m_r, 5e-5)); s("c_bd", self.c_bd); s("F_bdc", self.F_bdc)
        s("scrub", self.scrub); s("F_cap", self.F_cap); s("k_safe", self.k_safe)
        s("mu_hat0", self.mu_hat0 if self.mu_hat0 is not None else 0.9 * self.mu); s("slew_d", self.slew)
        s("tau_m", self.tau_m); s("N_noise", self.N_noise); s("Flat_noise", self.Flat_noise); s("v_noise", self.v_noise)
        s("sub", self.sub); s("Kp", self.Kp); s("band", self.band); s("Dd", self.D); s("lead", self.lead)
        s("lead_v_min", self.lead_v_min); s("over_d", self.over_d); s("over_t", self.over_t); s("fade", self.fade)
        s("restore", self.restore); s("Kl", self.Kl); s("F_lead", self.F_lead); s("v_lead", self.v_lead); s("Kv", self.Kv)
        s("w_s", self.w_s); s("z_s", self.z_s); s("rate_s", self.rate_s); s("acc_s", self.acc_s); s("L_a", self.L_a)
        s("m_eff", self.m_eff); s("u_min", self.u_min); s("free_in_band", self.free_in_band); s("f_lp", self.f_lp)
        s("b_damp", self.b_damp); s("b_max", self.b_max); s("v_min_head", self.v_min_head)
        s("comp_inertia", self.comp_inertia); s("b_tau", self.b_tau); s("b_dead", self.b_dead)
        s("b_noise", self.b_noise); s("b_pull", self.b_pull); s("wc_pull_frac", 1.0)
        s("slip_v", self.slip_v); s("slip_t", self.slip_t); s("mu_adapt", self.mu_adapt); s("win_fwd", self.win_fwd)
        s("tlaw", self.tlaw); s("plaw", self.plaw); s("k_st", self.k_st); s("L_t", self.L_t)
        s("k_fc", self.k_fc); s("rel_on", self.rel_on); s("m_rel", self.m_rel)
        return D


class Result(HP.Result):
    def __getitem__(self, name):
        return self.rec[:, RIDX_D[name]]

    def xy(self, base):
        i = RIDX_D[base]
        return self.rec[:, i:i + 2]

    @property
    def heel_force(self):
        return self.rec[:, RIDX_D["Ftx"]:RIDX_D["Ftx"] + 2]


def _arc(tm: np.ndarray) -> np.ndarray:
    d = np.hypot(*np.diff(tm, axis=0).T) if len(tm) > 1 else np.zeros(0)
    return np.ascontiguousarray(np.r_[0.0, np.cumsum(d)])


def run(scn: Scenario, pen, hand, writing, ctl, drive: Drive, Ntot: Optional[np.ndarray] = None,
        hand_path: Optional[np.ndarray] = None, tremor: Optional[np.ndarray] = None,
        drive_tmpl: Optional[np.ndarray] = None, drive_tdown: Optional[np.ndarray] = None,
        seed: int = 1, rec_hz: float = 2000.0) -> Result:
    """One run of HW1-D.  scn, pen, hand, writing, ctl as in handwriting.plant.run (ctl drives the nose; its board
    field is ignored: use Drive(grounded=True) for the board).  hand_path/tremor split scn.pref for the relaxed writer
    (default: hand_path = scn.pref - scn.tremor)."""
    P, info = HP.build_params(scn, pen, hand, writing, HP.Controls(qext=ctl.qext, tmpl=ctl.tmpl, tmpl_down=ctl.tmpl_down,
                                                                     g_guide=ctl.g_guide, capture=ctl.capture,
                                                                     drop_d=ctl.drop_d, drop_t=ctl.drop_t,
                                                                     stroke_match=ctl.stroke_match,
                                                                     tau_auth=ctl.tau_auth, gating=ctl.gating,
                                                                     hover_max=ctl.hover_max), rec_hz=rec_hz)
    D = drive.vector(writing.theta_deg, pen.F_c if pen.skid else 0.15)
    n = len(scn.t)
    tremor = np.zeros_like(scn.pref) if tremor is None else np.asarray(tremor, float)
    if hand_path is None:
        hand_path = scn.pref - (scn.tremor if scn.tremor is not None else 0.0)
    hp = np.ascontiguousarray(hand_path, dtype=np.float64)
    trem = np.ascontiguousarray(tremor if tremor is not None else np.zeros_like(hp), dtype=np.float64)
    if Ntot is None:
        Ntot = np.full(n, writing.N)
    Ntot = np.ascontiguousarray(Ntot, dtype=np.float64)
    nrec = int(math.ceil(n / P[HIDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC_D))
    qext = np.zeros((1, 2)) if ctl.qext is None else np.ascontiguousarray(ctl.qext, dtype=np.float64)
    tm = np.zeros((1, 2)) if ctl.tmpl is None else np.ascontiguousarray(ctl.tmpl, dtype=np.float64)
    td = np.zeros(1) if ctl.tmpl_down is None else np.ascontiguousarray(ctl.tmpl_down, dtype=np.float64)
    dtm = tm if drive_tmpl is None else np.ascontiguousarray(drive_tmpl, dtype=np.float64)
    dtd = td if drive_tdown is None else np.ascontiguousarray(drive_tdown, dtype=np.float64)
    lift = scn.meta.get("lift")
    if ctl.gating == "hover" and lift is not None:
        active = np.ascontiguousarray(((scn.down > 0.5) | (np.asarray(lift) < ctl.hover_max)).astype(np.float64))
    else:
        active = np.ascontiguousarray(scn.down, dtype=np.float64)
    tss, tse = HP.stroke_ranges(td)
    dss, dse = HP.stroke_ranges(dtd)
    dcum = _arc(dtm)
    m = simulate(P, D, hp, trem, np.ascontiguousarray(scn.down, dtype=np.float64), active, Ntot, qext, tm, td, tss, tse,
                 dtm, dtd, dss, dse, dcum, seed, rec)
    info.update({"n_ticks": int(math.ceil(n / P[HIDX["tick_decim"]])) + 1, "rec_hz": rec_hz, "drive": drive.mode,
                 "kind": drive.kind, "long": drive.long, "grounded": drive.grounded})
    return Result(rec[:m], info)
