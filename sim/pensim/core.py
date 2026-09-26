r"""Compiled time-domain core of the coupled pen simulator (model version M1).

Degrees of freedom (page frame {P}; see docs/physics.md):
  housing translation p_H (3), lever/stage coordinate q (2, tip-equivalent, in
  housing axes x_H, y_H), refill axial slide s (1), coil currents i (2),
  LuGre friction bristle state z (2), coil temperatures T (2).
Ball centre kinematics (front-pivot lever, suspension inside the carrier):
  C = p_H + (1 - kappa s/L1)(q1 x_H + q2 y_H) + (s + |q|^2/(2 L1)) a
  (kappa = 1 for Rev A; translational carriage: L1 -> inf)
Generalised forces follow from virtual work of the contact force F_c at C.
Stage:   m_eq q'' = -n Kf(T) i + Q_q - k q - c q' + F_stop + m_couple a_H,perp
Axial:   m_ax s'' = Q_s - (F_pre + k_ax s) - c_ax s' + F_axstop - m_ax a_H.a
Housing: (m_H + m_mov + m_ax) a_H = F_hand + F_c - m_mov cf q''_vec - m_ax s'' a
Current: L di/dt = V - (R(T) + r_bridge + r_shunt) i - e,  e = -n Kf q'
         (exact exponential step; V from a PI loop saturated at +/-V_bus)
Contact: N = max(0, k_p delta + c_p delta'), delta = r_b - C_z
Friction (LuGre, normalised): z' = v - sigma0 |v| z / g(v),
         g(v) = mu_k + (mu_s - mu_k) exp(-(v/v_s)^2),
         f = -N (sigma0 z + sigma1 z') - sigma2 v
Integration: semi-implicit (symplectic) Euler at dt (default 25 us).
Sensors, estimator and controller run at their own rates with ring-buffer
delays.  All outputs are SIMULATION results.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit

from .layout import IDX, NREC, RIDX

RB = 8192  # ring buffer length (steps); must exceed the largest sensor delay


def _mk(name):
    return IDX[name]


# unpack indices as module constants (numba treats them as compile-time ints)
I_dt = _mk("dt"); I_n = _mk("n_steps"); I_rec = _mk("rec_decim")
I_th = _mk("theta"); I_phi = _mk("phi"); I_rho = _mk("rho")
I_meq = _mk("m_eq"); I_ktip = _mk("k_tip"); I_ctip = _mk("c_tip"); I_mcpl = _mk("m_couple")
I_mmov = _mk("m_mov"); I_cf = _mk("cm_factor"); I_L1 = _mk("L1")
I_qstop = _mk("q_stop"); I_kstop = _mk("k_stop"); I_cstop = _mk("c_stop")
I_max = _mk("m_ax"); I_kax = _mk("k_ax"); I_cax = _mk("c_ax"); I_Fpre = _mk("F_pre"); I_smax = _mk("s_max")
I_mH = _mk("m_H"); I_Khxy = _mk("K_hxy"); I_Chxy = _mk("C_hxy"); I_Khz = _mk("K_hz"); I_Chz = _mk("C_hz"); I_z0 = _mk("z0")
I_kp = _mk("k_p"); I_cp = _mk("c_p"); I_rb = _mk("r_b"); I_muk = _mk("mu_k"); I_mus = _mk("mu_s"); I_vs = _mk("v_s")
I_s0 = _mk("sigma0"); I_s1 = _mk("sigma1"); I_s2 = _mk("sigma2")
I_nlev = _mk("n_lever"); I_Kf = _mk("Kf"); I_R20 = _mk("R20"); I_Lc = _mk("Lc"); I_Vbus = _mk("V_bus")
I_rbr = _mk("r_bridge"); I_rsh = _mk("r_shunt"); I_imax = _mk("i_max"); I_acu = _mk("alpha_cu"); I_aB = _mk("alpha_B")
I_Rth = _mk("Rth"); I_Cth = _mk("Cth"); I_Tamb = _mk("T_amb")
I_cdec = _mk("cur_decim"); I_Kpi = _mk("Kp_i"); I_Kii = _mk("Ki_i")
I_hn = _mk("hall_noise"); I_hd = _mk("hall_delay"); I_hict = _mk("hall_ict"); I_hictc = _mk("hall_ict_comp")
I_odec = _mk("opt_decim"); I_od = _mk("opt_delay"); I_on = _mk("opt_noise"); I_osc = _mk("opt_scale"); I_olift = _mk("opt_lift_max")
I_idec = _mk("imu_decim"); I_id = _mk("imu_delay"); I_in = _mk("imu_noise"); I_ibx = _mk("imu_bias_x"); I_iby = _mk("imu_bias_y")
I_fdec = _mk("force_decim"); I_fd = _mk("force_delay"); I_fn = _mk("force_noise")
I_mode = _mk("mode"); I_sdec = _mk("stage_decim"); I_Kp = _mk("Kp"); I_Kd = _mk("Kd"); I_Ki = _mk("Ki"); I_dfilt = _mk("d_filt")
I_ffc = _mk("ff_contact"); I_ffa = _mk("ff_accel"); I_ffr = _mk("ff_ref"); I_muh = _mk("mu_hat")
I_g = _mk("g_assist"); I_qlim = _mk("q_lim"); I_qtap = _mk("q_taper"); I_slew = _mk("slew"); I_atau = _mk("authority_tau")
I_b1 = _mk("bp1_b0"); I_b2 = _mk("bp2_b0"); I_bpg = _mk("bp_gain_comp"); I_hor = _mk("horizon")
I_qj = _mk("kf_qj"); I_qt = _mk("kf_qt"); I_kr = _mk("kf_r"); I_w0 = _mk("kf_w0"); I_rd = _mk("kf_rdamp")
I_wg = _mk("kf_wgain"); I_wmin = _mk("kf_wmin"); I_wmax = _mk("kf_wmax"); I_nis = _mk("conf_nis_hi")
I_oh = _mk("oracle_h")
I_qinit = _mk("q_init"); I_reqc = _mk("require_contact")
I_axc = _mk("axial_comp"); I_axct = _mk("axial_comp_tau"); I_gam = _mk("gamma_acc")

R_t = RIDX["t"]; R_pHx = RIDX["pHx"]; R_q1 = RIDX["q1"]; R_qr1 = RIDX["qr1"]; R_s = RIDX["s"]; R_N = RIDX["N"]
R_fx = RIDX["fx"]; R_tipx = RIDX["tipx"]; R_i1 = RIDX["i1"]; R_V1 = RIDX["V1"]; R_con = RIDX["contact"]
R_dhx = RIDX["dhx"]; R_T1 = RIDX["T1"]; R_Pcu = RIDX["Pcu"]; R_Pbr = RIDX["Pbr"]; R_Fhx = RIDX["Fhx"]
R_conf = RIDX["conf"]; R_satv = RIDX["sat_v"]; R_stop = RIDX["stop"]; R_west = RIDX["west"]; R_ir1 = RIDX["iref1"]
R_fax = RIDX["Fax_meas"]


@njit(cache=True)
def _biquad(b0, b1, b2, a1, a2, x, st):
    """Direct form II transposed; st = [s1, s2] updated in place."""
    y = b0 * x + st[0]
    st[0] = b1 * x - a1 * y + st[1]
    st[1] = b2 * x - a2 * y
    return y


@njit(cache=True)
def _kf_step(x, P, y, Ts, w, rdamp, qj, qt, r):
    """One predict+update of the 5-state intent/oscillator Kalman filter.
    States: p, v, a (intended, white jerk), x1, x2 (oscillator).  Returns
    (innovation, S)."""
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
    # measurement y = p + x1 + noise
    innov = y - (xp[0] + xp[3])
    S = Pp[0, 0] + Pp[0, 3] + Pp[3, 0] + Pp[3, 3] + r
    K = np.empty(5)
    for i in range(5):
        K[i] = (Pp[i, 0] + Pp[i, 3]) / S
    for i in range(5):
        x[i] = xp[i] + K[i] * innov
    # P = (I - K H) Pp (Joseph form omitted; symmetrise instead)
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
def simulate(P, pref, vref, fpush, dtrue, tmpl, opt_ok, seed, rec):
    np.random.seed(seed)
    dt = P[I_dt]
    n = int(P[I_n])
    rdec = int(P[I_rec])
    mode = int(P[I_mode])
    th = P[I_th]; ph = P[I_phi]; ro = P[I_rho]
    ct = math.cos(th); st_ = math.sin(th)
    # basis vectors in page frame
    hx = math.cos(ph); hy = math.sin(ph)
    ax_ = ct * hx; ay_ = ct * hy; az_ = st_
    t1x = st_ * hx; t1y = st_ * hy; t1z = -ct
    t2x = -hy; t2y = hx; t2z = 0.0
    cr = math.cos(ro); sr = math.sin(ro)
    xHx = cr * t1x + sr * t2x; xHy = cr * t1y + sr * t2y; xHz = cr * t1z + sr * t2z
    yHx = -sr * t1x + cr * t2x; yHy = -sr * t1y + cr * t2y; yHz = -sr * t1z + cr * t2z
    # inverse of the compliance-aware page Jacobian (page -> stage):
    # J = Rot(phi) diag(J_t1, 1) Rot(rho),  J_t1 = sin th + gamma cos^2 th / sin th
    # gamma = 1: all tilt-coupled axial motion taken by the suspension (rigid-page
    # textbook case, J_t1 = 1/sin th); gamma = 0: taken by the hand (J_t1 = sin th)
    gam = P[I_gam]
    Jt1 = st_ + gam * ct * ct / st_
    a00 = hx / Jt1; a01 = hy / Jt1        # diag(1/J_t1, 1) Rot(-phi): rows
    a10 = -hy; a11 = hx
    Ji00 = cr * a00 + sr * a10; Ji01 = cr * a01 + sr * a11
    Ji10 = -sr * a00 + cr * a10; Ji11 = -sr * a01 + cr * a11

    m_eq = P[I_meq]; k_tip = P[I_ktip]; c_tip = P[I_ctip]; m_cpl = P[I_mcpl]
    m_mov = P[I_mmov]; cf = P[I_cf]; L1 = P[I_L1]
    q_stop = P[I_qstop]; k_stop = P[I_kstop]; c_stop = P[I_cstop]
    m_ax = P[I_max]; k_ax = P[I_kax]; c_ax = P[I_cax]; F_pre = P[I_Fpre]; s_max = P[I_smax]
    m_H = P[I_mH]; Khxy = P[I_Khxy]; Chxy = P[I_Chxy]; Khz = P[I_Khz]; Chz = P[I_Chz]; z0 = P[I_z0]
    k_p = P[I_kp]; c_p = P[I_cp]; r_b = P[I_rb]; mu_k = P[I_muk]; mu_s = P[I_mus]; v_s = P[I_vs]
    sg0 = P[I_s0]; sg1 = P[I_s1]; sg2 = P[I_s2]
    nlev = P[I_nlev]; Kf20 = P[I_Kf]; R20 = P[I_R20]; Lc = P[I_Lc]; Vbus = P[I_Vbus]
    rbr = P[I_rbr]; rsh = P[I_rsh]; imax = P[I_imax]; acu = P[I_acu]; aB = P[I_aB]
    Rth = P[I_Rth]; Cth = P[I_Cth]; Tamb = P[I_Tamb]
    cdec = int(P[I_cdec]); Kpi = P[I_Kpi]; Kii = P[I_Kii]
    hn = P[I_hn]; hd = int(P[I_hd]); hict = P[I_hict]; hictc = P[I_hictc]
    odec = int(P[I_odec]); od = int(P[I_od]); on_ = P[I_on]; osc = P[I_osc]; olift = P[I_olift]
    idec = int(P[I_idec]); idl = int(P[I_id]); inz = P[I_in]; ibx = P[I_ibx]; iby = P[I_iby]
    fdec = int(P[I_fdec]); fdl = int(P[I_fd]); fnz = P[I_fn]
    sdec = int(P[I_sdec]); Kp = P[I_Kp]; Kd = P[I_Kd]; Ki = P[I_Ki]; dfilt = P[I_dfilt]
    ffc = P[I_ffc]; ffa = P[I_ffa]; ffr = P[I_ffr]; muh = P[I_muh]
    g_as = P[I_g]; qlim = P[I_qlim]; qtap = P[I_qtap]; slew = P[I_slew]; atau = P[I_atau]
    bp1 = P[I_b1:I_b1 + 5]; bp2 = P[I_b2:I_b2 + 5]; bpg = P[I_bpg]; hor = P[I_hor]
    qj = P[I_qj]; qt = P[I_qt]; kr = P[I_kr]; wkf = P[I_w0]; rdamp = P[I_rd]
    wg = P[I_wg]; wmin = P[I_wmin]; wmax = P[I_wmax]; nishi = P[I_nis]
    oh = int(P[I_oh])
    Ts = dt * sdec

    # ---------------- state
    pH = np.zeros(3); vH = np.zeros(3); aH = np.zeros(3)
    pH[0] = pref[0, 0]; pH[1] = pref[0, 1]; pH[2] = z0 + pref[0, 2]
    q = np.zeros(2); qd = np.zeros(2); qdd = np.zeros(2)
    q[0] = P[I_qinit]
    reqc = P[I_reqc] > 0.5
    s = 0.0; sd = 0.0; sdd = 0.0
    cur = np.zeros(2); V = np.zeros(2); Tc = np.array([Tamb, Tamb])
    zb = np.zeros(2)
    # ring buffers of true signals
    rb_q = np.zeros((RB, 2)); rb_i = np.zeros((RB, 2)); rb_pH = np.zeros((RB, 3)); rb_aH = np.zeros((RB, 2))
    rb_s = np.zeros(RB); rb_ok = np.zeros(RB)
    # sensor holds
    o_meas = np.zeros(2); o_valid = 0.0; o_age = 0
    a_meas = np.zeros(2); fa_meas = F_pre
    # estimator state
    pimu = np.zeros(2); vimu = np.zeros(2)
    rb_pimu = np.zeros((1024, 2)); tick = 0
    bst = np.zeros((2, 4))           # biquad states per axis (2 biquads x 2)
    ybp_prev = np.zeros(2); ybpd = np.zeros(2)
    xk = np.zeros((2, 5)); Pk = np.zeros((2, 5, 5))
    for ax in range(2):
        for i in range(5):
            Pk[ax, i, i] = 1e-6
    kf_init = 0; phase_prev = 0.0; nis_f = 1.0
    need_reinit = 1
    # servo state
    qr = np.zeros(2); qr_prev = np.zeros(2); qr_prev2 = np.zeros(2)
    eint = np.zeros(2); eprev = np.zeros(2); ed_f = np.zeros(2)
    iref = np.zeros(2); ivint = np.zeros(2)
    g_eff = 0.0; conf = 0.0
    axc = P[I_axc]; axct = max(P[I_axct], 1e-3); s_lp = 0.0; was_contact = False
    dhat = np.zeros(2)
    prog = 0
    sat_v_flag = 0.0
    alpha_d = 1.0 - math.exp(-2.0 * math.pi * dfilt * Ts)
    alpha_a = 1.0 - math.exp(-Ts / max(atau, 1e-6))
    rec_i = 0
    nrec = rec.shape[0]

    for k in range(n):
        # ======================= control tick (sensors -> estimator -> servo)
        if k % sdec == 0 and mode != 0:
            kk = k % RB
            # --- Hall stage sensor (delayed, noisy, current crosstalk)
            kh = (k - hd) % RB
            qm0 = rb_q[kh, 0] + hn * np.random.standard_normal() + hict * rb_i[kh, 0] - hictc * cur[0]
            qm1 = rb_q[kh, 1] + hn * np.random.standard_normal() + hict * rb_i[kh, 1] - hictc * cur[1]
            # --- fused housing page position: optical (delayed) + IMU over the gap
            pim_now0 = pimu[0]; pim_now1 = pimu[1]
            rb_pimu[tick % 1024, 0] = pim_now0; rb_pimu[tick % 1024, 1] = pim_now1
            lag_t = max(0, (od - idl) // sdec)
            jl = (tick - lag_t) % 1024
            ph0 = o_meas[0] + (pim_now0 - rb_pimu[jl, 0])
            ph1 = o_meas[1] + (pim_now1 - rb_pimu[jl, 1])
            valid = o_valid > 0.5
            in_contact = (fa_meas > F_pre + 0.02) or (not reqc)
            # --- disturbance estimate and page correction
            corr0 = 0.0; corr1 = 0.0
            target_g = 0.0
            if mode == 2:  # band-pass + linear extrapolation
                if need_reinit == 1 and valid:
                    for ax in range(2):
                        for j in range(4):
                            bst[ax, j] = 0.0
                    need_reinit = 0
                yb = np.zeros(2)
                pv = (ph0, ph1)
                for ax in range(2):
                    s1 = bst[ax, 0:2]
                    s2 = bst[ax, 2:4]
                    y1 = _biquad(bp1[0], bp1[1], bp1[2], bp1[3], bp1[4], pv[ax], s1)
                    y2 = _biquad(bp2[0], bp2[1], bp2[2], bp2[3], bp2[4], y1, s2)
                    bst[ax, 0] = s1[0]; bst[ax, 1] = s1[1]; bst[ax, 2] = s2[0]; bst[ax, 3] = s2[1]
                    y2 = y2 * bpg
                    yd = (y2 - ybp_prev[ax]) / Ts
                    ybpd[ax] = ybpd[ax] + 0.2 * (yd - ybpd[ax])
                    ybp_prev[ax] = y2
                    yb[ax] = y2 + hor * ybpd[ax]
                dhat[0] = yb[0]; dhat[1] = yb[1]
                corr0 = -dhat[0]; corr1 = -dhat[1]
                target_g = g_as if (valid and in_contact) else 0.0
                conf = 1.0
            elif mode == 3:  # Kalman intent + oscillator with prediction
                if valid:
                    if need_reinit == 1:
                        for ax in range(2):
                            for i in range(5):
                                xk[ax, i] = 0.0
                                for j in range(5):
                                    Pk[ax, i, j] = 0.0
                            xk[ax, 0] = ph0 if ax == 0 else ph1
                            Pk[ax, 0, 0] = 1e-8; Pk[ax, 1, 1] = 1e-4; Pk[ax, 2, 2] = 1e-2
                            Pk[ax, 3, 3] = 1e-7; Pk[ax, 4, 4] = 1e-7
                        need_reinit = 0
                    nis_sum = 0.0
                    for ax in range(2):
                        yv = ph0 if ax == 0 else ph1
                        innov, S = _kf_step(xk[ax], Pk[ax], yv, Ts, wkf, rdamp, qj, qt, kr)
                        nis_sum += innov * innov / S
                    nis_f = nis_f + 0.01 * (0.5 * nis_sum - nis_f)
                    # frequency adaptation from oscillator phase rate (amplitude weighted)
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
                    # prediction of the oscillator component h ahead
                    ch = math.cos(wkf * hor); sh = math.sin(wkf * hor)
                    rh = rdamp ** (hor / Ts)
                    dhat[0] = rh * (ch * xk[0, 3] + sh * xk[0, 4])
                    dhat[1] = rh * (ch * xk[1, 3] + sh * xk[1, 4])
                    conf = min(1.0, max(0.0, 1.0 - (nis_f - 1.0) / max(nishi - 1.0, 1e-6)))
                    corr0 = -dhat[0]; corr1 = -dhat[1]
                    target_g = g_as * conf if in_contact else 0.0
                else:
                    need_reinit = 1
                    target_g = 0.0
            elif mode == 4:  # oracle: instantaneous true housing disturbance (dtrue = clean housing path)
                kd = min(k + oh, n - 1)
                dhat[0] = pH[0] - dtrue[kd, 0]; dhat[1] = pH[1] - dtrue[kd, 1]
                corr0 = -dhat[0]; corr1 = -dhat[1]
                target_g = g_as if in_contact else 0.0
                conf = 1.0
            elif mode == 6:  # guided: user-paced progress along registered template
                if valid:
                    m_t = tmpl.shape[0]
                    best = 1e9; bj = prog
                    j0 = max(0, prog - 20); j1 = min(m_t, prog + 200)
                    for j in range(j0, j1):
                        dx = tmpl[j, 0] - ph0; dy = tmpl[j, 1] - ph1
                        dd = dx * dx + dy * dy
                        if dd < best:
                            best = dd; bj = j
                    prog = bj
                    corr0 = tmpl[prog, 0] - ph0; corr1 = tmpl[prog, 1] - ph1
                    dhat[0] = -corr0; dhat[1] = -corr1
                    dist = math.sqrt(best)
                    conf = 1.0 if dist < 2.0 * qlim else 0.0
                    target_g = g_as * conf if in_contact else 0.0
                else:
                    target_g = 0.0
            # mode 1 (neutral), 5 (unpowered): no correction
            g_eff = g_eff + alpha_a * (target_g - g_eff)
            # axial-slide compensation: the ball moves s*cos(theta) along h when
            # the suspension deflects; cancel its variation about a slow mean
            s_meas = max(0.0, (fa_meas - F_pre) / k_ax)
            if in_contact and was_contact:
                s_lp += (Ts / axct) * (s_meas - s_lp)      # slow leak toward current slide
            elif in_contact and not was_contact:
                s_lp = 0.0                                  # reference = slide at touchdown
            was_contact = in_contact
            if axc > 0.5 and mode != 5 and in_contact:
                ds = s_meas - s_lp
                ax_c0 = -ds * ct * hx; ax_c1 = -ds * ct * hy
                am = math.hypot(ax_c0, ax_c1)
                if am > 0.3e-3:
                    ax_c0 *= 0.3e-3 / am; ax_c1 *= 0.3e-3 / am
            else:
                ax_c0 = 0.0; ax_c1 = 0.0
            # page correction -> stage (lever) coordinates; compensate the lever-arm
            # shortening lam = 1 - s/L1 using the axial deflection implied by the
            # measured suspension force
            s_hat = max(0.0, (fa_meas - F_pre) / k_ax)
            lam_hat = max(0.5, 1.0 - s_hat / L1)
            qn0 = (g_eff * (Ji00 * corr0 + Ji01 * corr1) + (Ji00 * ax_c0 + Ji01 * ax_c1)) / lam_hat
            qn1 = (g_eff * (Ji10 * corr0 + Ji11 * corr1) + (Ji10 * ax_c0 + Ji11 * ax_c1)) / lam_hat
            # radial soft limit with smooth taper
            rq = math.hypot(qn0, qn1)
            knee = qlim - qtap
            if rq > knee and rq > 0:
                rnew = knee + qtap * math.tanh((rq - knee) / qtap)
                qn0 *= rnew / rq; qn1 *= rnew / rq
            # slew limit
            dq0 = qn0 - qr[0]; dq1 = qn1 - qr[1]
            dmax = slew * Ts
            dm = math.hypot(dq0, dq1)
            if dm > dmax:
                dq0 *= dmax / dm; dq1 *= dmax / dm
            qr_prev2[0] = qr_prev[0]; qr_prev2[1] = qr_prev[1]
            qr_prev[0] = qr[0]; qr_prev[1] = qr[1]
            qr[0] += dq0; qr[1] += dq1
            # ---------------- position servo (tip-equivalent force)
            if mode == 5:
                iref[0] = 0.0; iref[1] = 0.0
            else:
                em0 = qr[0] - qm0; em1 = qr[1] - qm1
                ed0 = (em0 - eprev[0]) / Ts; ed1 = (em1 - eprev[1]) / Ts
                ed_f[0] += alpha_d * (ed0 - ed_f[0]); ed_f[1] += alpha_d * (ed1 - ed_f[1])
                eprev[0] = em0; eprev[1] = em1
                F0 = Kp * em0 + Kd * ed_f[0] + Ki * eint[0]
                F1 = Kp * em1 + Kd * ed_f[1] + Ki * eint[1]
                if ffr > 0:
                    qdd0 = (qr[0] - 2 * qr_prev[0] + qr_prev2[0]) / (Ts * Ts)
                    qdd1 = (qr[1] - 2 * qr_prev[1] + qr_prev2[1]) / (Ts * Ts)
                    F0 += ffr * (m_eq * qdd0 + k_tip * qr[0] + c_tip * (qr[0] - qr_prev[0]) / Ts)
                    F1 += ffr * (m_eq * qdd1 + k_tip * qr[1] + c_tip * (qr[1] - qr_prev[1]) / Ts)
                if ffc > 0 and in_contact:
                    Nh = fa_meas / st_
                    # normal-reaction direction in housing axes: n.xH, n.yH;
                    # generalised stage force is lam * (transverse contact force)
                    F0 += ffc * lam_hat * (Nh * ct * cr)      # -(N n.xH) = N cos th cos rho
                    F1 += ffc * lam_hat * (-Nh * ct * sr)     # -(N n.yH) = -N cos th sin rho
                if ffa > 0:
                    F0 += -ffa * m_cpl * (a_meas[0] * xHx + a_meas[1] * xHy)
                    F1 += -ffa * m_cpl * (a_meas[0] * yHx + a_meas[1] * yHy)
                Kf_hat = Kf20
                i0 = -F0 / (nlev * Kf_hat); i1 = -F1 / (nlev * Kf_hat)
                sat0 = abs(i0) > imax; sat1 = abs(i1) > imax
                iref[0] = min(max(i0, -imax), imax); iref[1] = min(max(i1, -imax), imax)
                if not sat0 and sat_v_flag < 0.5:
                    eint[0] += em0 * Ts
                if not sat1 and sat_v_flag < 0.5:
                    eint[1] += em1 * Ts
            tick += 1
        elif k % sdec == 0 and mode == 0:
            tick += 1

        # ======================= current loop (PI, saturating), every cdec steps
        if k % cdec == 0:
            sat_v_flag = 0.0
            for ax in range(2):
                if mode == 0 or mode == 5:
                    V[ax] = 0.0
                    continue
                Rhat = R20 + rbr + rsh
                e_i = iref[ax] - cur[ax]
                vcmd = Rhat * iref[ax] + Kpi * e_i + Kii * ivint[ax]
                vsat = min(max(vcmd, -Vbus), Vbus)
                if vsat == vcmd:
                    ivint[ax] += e_i * dt * cdec
                else:
                    sat_v_flag = 1.0
                V[ax] = vsat

        # ======================= mechanics
        # kinematics of the ball centre
        lam = 1.0 - s / L1
        qq = q[0] * q[0] + q[1] * q[1]
        ax_off = s + qq / (2.0 * L1)
        Cx = pH[0] + lam * (q[0] * xHx + q[1] * yHx) + ax_off * ax_
        Cy = pH[1] + lam * (q[0] * xHy + q[1] * yHy) + ax_off * ay_
        Cz = pH[2] + lam * (q[0] * xHz + q[1] * yHz) + ax_off * az_
        qdot_dot = (q[0] * qd[0] + q[1] * qd[1]) / L1
        vtr0 = lam * qd[0] - sd / L1 * q[0]
        vtr1 = lam * qd[1] - sd / L1 * q[1]
        vax = sd + qdot_dot
        vCx = vH[0] + vtr0 * xHx + vtr1 * yHx + vax * ax_
        vCy = vH[1] + vtr0 * xHy + vtr1 * yHy + vax * ay_
        vCz = vH[2] + vtr0 * xHz + vtr1 * yHz + vax * az_
        if mode == 0:
            Cx = pH[0]; Cy = pH[1]; Cz = pH[2]
            vCx = vH[0]; vCy = vH[1]; vCz = vH[2]
        delta = r_b - Cz
        Nf = 0.0; fx = 0.0; fy = 0.0
        if delta > 0.0:
            Nf = k_p * delta - c_p * vCz
            if Nf < 0.0:
                Nf = 0.0
        if Nf > 0.0:
            vn = math.hypot(vCx, vCy)
            gv = mu_k + (mu_s - mu_k) * math.exp(-(vn / v_s) ** 2)
            den = 1.0 + dt * sg0 * vn / gv
            z0n = (zb[0] + dt * vCx) / den
            z1n = (zb[1] + dt * vCy) / den
            zd0 = (z0n - zb[0]) / dt; zd1 = (z1n - zb[1]) / dt
            zb[0] = z0n; zb[1] = z1n
            fx = -Nf * (sg0 * z0n + sg1 * zd0) - sg2 * vCx
            fy = -Nf * (sg0 * z1n + sg1 * zd1) - sg2 * vCy
        else:
            zb[0] = 0.0; zb[1] = 0.0
        # contact force on ball, generalised forces
        Fc1 = fx * xHx + fy * xHy + Nf * xHz
        Fc2 = fx * yHx + fy * yHy + Nf * yHz
        Fca = fx * ax_ + fy * ay_ + Nf * az_
        Qq0 = lam * Fc1 + Fca * q[0] / L1
        Qq1 = lam * Fc2 + Fca * q[1] / L1
        Qs = -(q[0] * Fc1 + q[1] * Fc2) / L1 + Fca
        # hand force on housing
        Fhx = Khxy * (pref[k, 0] - pH[0]) + Chxy * (vref[k, 0] - vH[0])
        Fhy = Khxy * (pref[k, 1] - pH[1]) + Chxy * (vref[k, 1] - vH[1])
        Fhz = Khz * (z0 + pref[k, 2] - pH[2]) + Chz * (vref[k, 2] - vH[2]) - fpush[k]
        # stage dynamics
        stopf = 0.0
        if mode == 0:
            qdd[0] = 0.0; qdd[1] = 0.0; sdd = 0.0
        else:
            Kf_T0 = Kf20 * (1.0 + aB * (Tc[0] - 20.0))
            Kf_T1 = Kf20 * (1.0 + aB * (Tc[1] - 20.0))
            Fa0 = -nlev * Kf_T0 * cur[0]
            Fa1 = -nlev * Kf_T1 * cur[1]
            rq = math.hypot(q[0], q[1])
            Fs0 = 0.0; Fs1 = 0.0
            if rq > q_stop:
                ux = q[0] / rq; uy = q[1] / rq
                vr = qd[0] * ux + qd[1] * uy
                fm = k_stop * (rq - q_stop) + (c_stop * vr if vr > 0 else 0.0)
                Fs0 = -fm * ux; Fs1 = -fm * uy
                stopf = 1.0
            aHp0 = aH[0] * xHx + aH[1] * xHy + aH[2] * xHz
            aHp1 = aH[0] * yHx + aH[1] * yHy + aH[2] * yHz
            qdd[0] = (Fa0 + Qq0 - k_tip * q[0] - c_tip * qd[0] + Fs0 + m_cpl * aHp0) / m_eq
            qdd[1] = (Fa1 + Qq1 - k_tip * q[1] - c_tip * qd[1] + Fs1 + m_cpl * aHp1) / m_eq
            # axial
            Fsp = F_pre + k_ax * s
            Fst = 0.0
            if s < 0.0:
                Fst = -k_stop * s - (c_stop * sd if sd < 0 else 0.0)
            elif s > s_max:
                Fst = -k_stop * (s - s_max) - (c_stop * sd if sd > 0 else 0.0)
            aHa = aH[0] * ax_ + aH[1] * ay_ + aH[2] * az_
            sdd = (Qs - Fsp - c_ax * sd + Fst - m_ax * aHa) / m_ax
        # housing (total momentum, explicit coupling through previous accelerations)
        Mt = m_H + m_mov + m_ax
        cx_ = m_mov * cf * (qdd[0] * xHx + qdd[1] * yHx) + m_ax * sdd * ax_
        cy_ = m_mov * cf * (qdd[0] * xHy + qdd[1] * yHy) + m_ax * sdd * ay_
        cz_ = m_mov * cf * (qdd[0] * xHz + qdd[1] * yHz) + m_ax * sdd * az_
        if mode == 0:
            cx_ = 0.0; cy_ = 0.0; cz_ = 0.0
        aH[0] = (Fhx + fx - cx_) / Mt
        aH[1] = (Fhy + fy - cy_) / Mt
        aH[2] = (Fhz + Nf - cz_) / Mt
        # integrate (symplectic Euler)
        for j in range(3):
            vH[j] += aH[j] * dt
            pH[j] += vH[j] * dt
        if mode != 0:
            for j in range(2):
                qd[j] += qdd[j] * dt
                q[j] += qd[j] * dt
            sd += sdd * dt
            s += sd * dt
        # electrical (exact exponential step per axis) and thermal
        Pcu = 0.0
        for ax in range(2):
            Rc = R20 * (1.0 + acu * (Tc[ax] - 20.0))
            if mode == 0 or mode == 5:
                cur[ax] = 0.0
            else:
                Rt = Rc + rbr + rsh
                Kf_T = Kf20 * (1.0 + aB * (Tc[ax] - 20.0))
                emf = -nlev * Kf_T * qd[ax]
                ex = math.exp(-dt * Rt / Lc)
                cur[ax] = cur[ax] * ex + (V[ax] - emf) / Rt * (1.0 - ex)
            pc = cur[ax] * cur[ax] * Rc
            Pcu += pc
            Tc[ax] += dt / Cth * (pc - (Tc[ax] - Tamb) / Rth)
        # ring buffers (true signals)
        kk = k % RB
        rb_q[kk, 0] = q[0]; rb_q[kk, 1] = q[1]
        rb_i[kk, 0] = cur[0]; rb_i[kk, 1] = cur[1]
        rb_pH[kk, 0] = pH[0]; rb_pH[kk, 1] = pH[1]; rb_pH[kk, 2] = pH[2]
        rb_aH[kk, 0] = aH[0]; rb_aH[kk, 1] = aH[1]
        rb_s[kk] = s
        rb_ok[kk] = opt_ok[k]
        # ----- sensor sampling
        if k % odec == 0:
            ko = (k - od) % RB
            hz = rb_pH[ko, 2] - z0
            ok = (rb_ok[ko] > 0.5) and (hz < olift) and (k >= od)
            if ok:
                o_meas[0] = (1.0 + osc) * rb_pH[ko, 0] + on_ * np.random.standard_normal()
                o_meas[1] = (1.0 + osc) * rb_pH[ko, 1] + on_ * np.random.standard_normal()
                if o_valid < 0.5:
                    need_reinit = 1
                o_valid = 1.0
            else:
                o_valid = 0.0
        if k % idec == 0:
            ki = (k - idl) % RB
            a_meas[0] = rb_aH[ki, 0] + ibx + inz * np.random.standard_normal()
            a_meas[1] = rb_aH[ki, 1] + iby + inz * np.random.standard_normal()
            dti = dt * idec
            vimu[0] = (vimu[0] + a_meas[0] * dti) * (1.0 - dti / 0.5)
            vimu[1] = (vimu[1] + a_meas[1] * dti) * (1.0 - dti / 0.5)
            pimu[0] += vimu[0] * dti
            pimu[1] += vimu[1] * dti
        if k % fdec == 0:
            kf_ = (k - fdl) % RB
            fa_meas = F_pre + k_ax * rb_s[kf_] + fnz * np.random.standard_normal()
        # ----- record (all states at end of step)
        if k % rdec == 0 and rec_i < nrec:
            if mode == 0:
                Cx = pH[0]; Cy = pH[1]
            else:
                lam_r = 1.0 - s / L1
                ao_r = s + (q[0] * q[0] + q[1] * q[1]) / (2.0 * L1)
                Cx = pH[0] + lam_r * (q[0] * xHx + q[1] * yHx) + ao_r * ax_
                Cy = pH[1] + lam_r * (q[0] * xHy + q[1] * yHy) + ao_r * ay_
            r = rec[rec_i]
            r[R_t] = k * dt
            r[R_pHx] = pH[0]; r[R_pHx + 1] = pH[1]; r[R_pHx + 2] = pH[2]
            r[R_q1] = q[0]; r[R_q1 + 1] = q[1]
            r[R_qr1] = qr[0]; r[R_qr1 + 1] = qr[1]
            r[R_s] = s; r[R_N] = Nf; r[R_fx] = fx; r[R_fx + 1] = fy
            r[R_tipx] = Cx; r[R_tipx + 1] = Cy
            r[R_i1] = cur[0]; r[R_i1 + 1] = cur[1]
            r[R_V1] = V[0]; r[R_V1 + 1] = V[1]
            r[R_con] = 1.0 if Nf > 0.0 else 0.0
            r[R_dhx] = dhat[0]; r[R_dhx + 1] = dhat[1]
            r[R_T1] = Tc[0]; r[R_T1 + 1] = Tc[1]
            r[R_Pcu] = Pcu; r[R_Pbr] = (cur[0] ** 2 + cur[1] ** 2) * (rbr + rsh)
            r[R_Fhx] = Fhx; r[R_Fhx + 1] = Fhy; r[R_Fhx + 2] = Fhz
            r[R_conf] = g_eff; r[R_satv] = sat_v_flag; r[R_stop] = stopf
            r[R_west] = wkf / (2 * math.pi)
            r[R_ir1] = iref[0]; r[R_ir1 + 1] = iref[1]
            r[R_fax] = fa_meas
            rec_i += 1
    return rec_i
