r"""Compiled time-domain core of the pencil simulator (model P1).

Degrees of freedom (page frame {P}, conventions of stabpen/frames.py):
  housing reference point p_H (3) = nominal ball centre fixed to the barrel; passive hand
  mass perturbation (3); stage deflection at the nib q (2, housing axes x_H, y_H); axial
  slide of the spring-loaded refill s (1, + toward the cap); LuGre bristles of nib and skid
  (2 + 2); piezo driver outputs V (2) and Bouc-Wen states (2).
Ball centre:  C = p_H + q1 x_H + q2 y_H + (s + |q|^2 / (2 L_piv)) a
Skid contact point (lowest point of the ring, fixed to the housing):
              S = p_H + p_nom a + r_ring t1,  S_z = 0 when p_Hz = r_b (nominal)
Stage (per axis j, nib-referred; bender = force source k_b*delta_free(V) in parallel with k_b):
  m_eq q_j'' = k_b delta_free,j - (k_b + k_par) q_j - c q_j' + F_nib.e_j + F_stop,j - m_cpl a_H.e_j
Axial:  m_ax s'' = F_nib.a - (F_sp0 + k_sp s) - c_ax s' - mu_b*bear*|F_perp|*tanh(s'/v_b) + F_axstop - m_ax a_H.a
Housing: M_t a_H = F_hand + F_nib + F_skid - m_cpl (q1'' x_H + q2'' y_H) - m_ax s'' a
Hand: two-stage impedance exactly as sim/pensim/core.py (HAP-26 parameters).
Contacts: penalty normal force with damping; LuGre friction normalised by N (P-9) for the
nib (ball) and for the skid.
Driver: V follows the command through a first-order lag with a slew limit, clamped to
[0, V_rail]; charge i = C dV/dt; rail power for a class-B / switch-to-rail stage and for a
charge-recovery stage (sim/pencil/power.py conventions).
Hysteresis: Bouc-Wen on the normalised drive (optional).
Control: outer loop (estimator, page-to-stage reference) at the stage rate as in model M1;
mode 7 (external) cancels a disturbance estimate the harness computes outside the core and
passes per simulation step in place of dtrue (the estimator must be causal; see model.py);
inner piezo servo (feedforward + integral + damping) at servo_decim.
Touchdown / lift feed-forward (td_* parameters, default off; opt/touchdown/law.py): a stage command from the
measured axial slide with the stage-induced slide removed (predicted ahead by an alpha-beta tracker), pre-positioning
while the refill rests on its stop, and the contact-load bias switched at once by its contact state.
Estimators _kf_step and the fusion/gate/guided logic are copied from sim/pensim/core.py
(model M1) so both simulators run the same estimator.
Integration: semi-implicit (symplectic) Euler at dt (default 25 us).
Every output is a SIMULATION result.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit

from .layout import IDX, RIDX

RB = 8192

# module-level integer constants (numba treats globals as compile-time constants)
for _n, _i in IDX.items():
    globals()["I_" + _n] = _i
for _n, _i in RIDX.items():
    globals()["R_" + _n] = _i


@njit(cache=True)
def _kf_step(x, P, y, Ts, w, rdamp, qj, qt, r):
    """Copy of sim/pensim/core.py::_kf_step (5-state intent + oscillator Kalman filter)."""
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
def _lugre(zb, vx, vy, N, mu_k, mu_s, v_s, sg0, sg1, sg2, dt):
    """LuGre friction normalised by N (P-9), implicit bristle update as sim/pensim/core.py."""
    vn = math.hypot(vx, vy)
    gv = mu_k + (mu_s - mu_k) * math.exp(-(vn / v_s) ** 2)
    den = 1.0 + dt * sg0 * vn / gv
    z0n = (zb[0] + dt * vx) / den
    z1n = (zb[1] + dt * vy) / den
    zd0 = (z0n - zb[0]) / dt
    zd1 = (z1n - zb[1]) / dt
    zb[0] = z0n
    zb[1] = z1n
    fx = -N * (sg0 * z0n + sg1 * zd0) - sg2 * vx
    fy = -N * (sg0 * z1n + sg1 * zd1) - sg2 * vy
    return fx, fy


@njit(cache=True)
def _taper(x0, x1, lim, qtap):
    """Radial soft limit of a stage command at radius lim (the tanh taper of the tremor path, width qtap)."""
    r = math.hypot(x0, x1)
    if lim <= 0.0:
        return 0.0, 0.0
    if r <= 0.0:
        return x0, x1
    w = min(qtap, lim)
    knee = lim - w
    if r > knee:
        rn = knee + w * math.tanh((r - knee) / w)
        return x0 * rn / r, x1 * rn / r
    return x0, x1


@njit(cache=True)
def simulate(P, pref, vref, fpush, dtrue, tmpl, opt_ok, seed, rec):
    np.random.seed(seed)
    dt = P[I_dt]
    n = int(P[I_n_steps])
    rdec = int(P[I_rec_decim])
    mode = int(P[I_mode])
    th = P[I_theta]; ph = P[I_phi]; ro = P[I_rho]
    ct = math.cos(th); st_ = math.sin(th)
    hx = math.cos(ph); hy = math.sin(ph)
    ax_ = ct * hx; ay_ = ct * hy; az_ = st_
    t1x = st_ * hx; t1y = st_ * hy; t1z = -ct
    t2x = -hy; t2y = hx; t2z = 0.0
    cr = math.cos(ro); sr = math.sin(ro)
    xHx = cr * t1x + sr * t2x; xHy = cr * t1y + sr * t2y; xHz = cr * t1z + sr * t2z
    yHx = -sr * t1x + cr * t2x; yHy = -sr * t1y + cr * t2y; yHz = -sr * t1z + cr * t2z
    gam = P[I_gamma_acc]
    Jt1 = st_ + gam * ct * ct / st_
    a00 = hx / Jt1; a01 = hy / Jt1
    a10 = -hy; a11 = hx
    Ji00 = cr * a00 + sr * a10; Ji01 = cr * a01 + sr * a11
    Ji10 = -sr * a00 + cr * a10; Ji11 = -sr * a01 + cr * a11

    m_eq = P[I_m_eq]; k_b = P[I_k_b]; k_par = P[I_k_par]; c_st = P[I_c_st]; m_cpl = P[I_m_cpl]
    g_V = P[I_g_V]; V_rail = P[I_V_rail]; L_piv = P[I_L_piv]
    q_stop = P[I_q_stop]; k_stop = P[I_k_stop]; c_stop = P[I_c_stop]; lock_st = P[I_lock_stage] > 0.5
    bw_on = P[I_bw_on] > 0.5; bw_a = P[I_bw_alpha]; bw_b = P[I_bw_beta]; bw_g = P[I_bw_gamma]; bw_hs = P[I_bw_hsat]
    drv_tau = P[I_drv_tau]; drv_slew = P[I_drv_slew]; C_ax = P[I_C_axis]; eta_c = P[I_eta_c]
    m_ax = P[I_m_ax]; k_sp = P[I_k_sp]; F_sp0 = P[I_F_sp0]; c_ax = P[I_c_ax]
    s_min = P[I_s_min]; s_max = P[I_s_max]; mu_b = P[I_mu_b]; bear = P[I_bear_fac]; v_b = P[I_v_b]
    lock_ax = P[I_lock_axial] > 0.5
    M_t = P[I_M_t]; Khxy = P[I_K_hxy]; Chxy = P[I_C_hxy]; Khz = P[I_K_hz]; Chz = P[I_C_hz]; z0 = P[I_z0]
    Mh = P[I_M_hand]; ka = P[I_k_arm]; ba = P[I_b_arm]
    k_p = P[I_k_p]; c_p = P[I_c_p]; r_b = P[I_r_b]; mu_k = P[I_mu_k]; mu_s = P[I_mu_s]; v_s = P[I_v_s]
    sg0 = P[I_sigma0]; sg1 = P[I_sigma1]; sg2 = P[I_sigma2]
    skid_on = P[I_skid_on] > 0.5; k_sk = P[I_k_sk]; c_sk = P[I_c_sk]; mu_sk = P[I_mu_sk]; mus_sk = P[I_mus_sk]
    vs_sk = P[I_vs_sk]; sg0_sk = P[I_sigma0_sk]; p_nom = P[I_p_nom]; r_ring = P[I_r_ring]
    hn = P[I_hall_noise]; hd = int(P[I_hall_delay])
    odec = int(P[I_opt_decim]); od = int(P[I_opt_delay]); on_ = P[I_opt_noise]; olift = P[I_opt_lift_max]
    idec = int(P[I_imu_decim]); idl = int(P[I_imu_delay]); inz = P[I_imu_noise]; ibx = P[I_imu_bias_x]; iby = P[I_imu_bias_y]
    adec = int(P[I_ax_decim]); adl = int(P[I_ax_delay]); anz = P[I_ax_noise]; cthr = P[I_contact_thr]
    w_aa = 2.0 * math.pi * max(P[I_acc_aa_hz], 1.0); imu_aa = P[I_imu_aa] > 0.5
    aa_q1 = 0.5411961001461969; aa_q2 = 1.3065629648763766   # Butterworth order 4: two biquads
    sdec = int(P[I_stage_decim]); vdec = int(P[I_servo_decim])
    Ki = P[I_Ki]; Kp = P[I_Kp]; Kd = P[I_Kd]; dfilt = P[I_d_filt]; ffr = P[I_ff_ref]; ffb = P[I_ff_bias]
    Fb0 = P[I_F_bias0]; Fb1 = P[I_F_bias1]
    g_as = P[I_g_assist]; qlim = P[I_q_lim]; qtap = P[I_q_taper]; slew = P[I_slew]; atau = P[I_authority_tau]
    hor = P[I_horizon]
    qj = P[I_kf_qj]; qt = P[I_kf_qt]; kr = P[I_kf_r]; wkf = P[I_kf_w0]; rdamp = P[I_kf_rdamp]
    wg = P[I_kf_wgain]; wmin = P[I_kf_wmin]; wmax = P[I_kf_wmax]; nishi = P[I_conf_nis_hi]
    fgate = P[I_f_gate]; fgw = P[I_f_gate_width]
    Ft0 = P[I_F_test0]; Ft1 = P[I_F_test1]; Vfix = P[I_V_fixed]; reqc = P[I_require_contact] > 0.5
    # touchdown / lift feed-forward (all zero = off; see layout.py and opt/touchdown/law.py)
    td_on = P[I_td_on] > 0.5
    tdK = P[I_td_gain]; tdkap = P[I_td_kappa]; tdsref = P[I_td_sref]; tdlead = P[I_td_lead]; tdlp = P[I_td_lp]
    tdpre = P[I_td_pre]; tddz = P[I_td_dz]; tdprio = int(P[I_td_prio]); tdbias = int(P[I_td_bias]); tdkl = P[I_td_kl]
    tddets = P[I_td_det_s]; tddete = P[I_td_det_e]; tdhold = P[I_td_hold]; tdvtd = P[I_td_vtd]; tdho = P[I_td_handover] > 0.5
    Ts = dt * sdec
    Tv = dt * vdec
    V_mid = 0.5 * V_rail
    dfree_max = g_V * V_mid
    Fv = k_b * g_V                     # nib force per volt of centre-electrode offset (blocked)
    k_tot = k_b + k_par
    bw_norm = 1.0 / (1.0 - bw_hs) if bw_on else 1.0

    # ---------------- state
    pH = np.zeros(3); vH = np.zeros(3); aH = np.zeros(3)
    pH[0] = pref[0, 0]; pH[1] = pref[0, 1]; pH[2] = z0 + pref[0, 2]
    dM = np.zeros(3); vM = np.zeros(3)
    q = np.zeros(2); qd = np.zeros(2); qdd = np.zeros(2)
    if not lock_st:
        q[0] = P[I_q_init]
    s = 0.0 if lock_ax else P[I_s_init]
    sd = 0.0; sdd = 0.0
    zn = np.zeros(2); zs = np.zeros(2)
    Vo = np.full(2, V_mid); Vc = np.full(2, V_mid)
    hB = np.zeros(2); u_prev = np.zeros(2)
    rb_q = np.zeros((RB, 2)); rb_pH = np.zeros((RB, 3)); rb_aH = np.zeros((RB, 2)); rb_s = np.zeros(RB); rb_ok = np.zeros(RB)
    o_meas = np.zeros(2); o_valid = 0.0
    a_meas = np.zeros(2)
    s_meas = s
    pimu = np.zeros(2); vimu = np.zeros(2)
    aa1 = np.zeros(3); aa1d = np.zeros(3); aa2 = np.zeros(3); aa2d = np.zeros(3)   # anti-aliasing filter states
    rb_pimu = np.zeros((1024, 2)); tick = 0
    xk = np.zeros((2, 5)); Pk = np.zeros((2, 5, 5))
    for axx in range(2):
        for i in range(5):
            Pk[axx, i, i] = 1e-6
    kf_init = 0; phase_prev = 0.0; nis_f = 1.0; need_reinit = 1
    qr = np.zeros(2); qr_prev = np.zeros(2); qr_prev2 = np.zeros(2); qddr = np.zeros(2); qdr = np.zeros(2)
    eint = np.zeros(2); qm_prev = np.zeros(2); ed_f = np.zeros(2)
    g_eff = 0.0; conf = 0.0
    dhat = np.zeros(2)
    prog = 0; reacq = 1
    vsat = 0.0
    in_contact = False
    alpha_d = 1.0 - math.exp(-2.0 * math.pi * dfilt * Tv)
    alpha_a = 1.0 - math.exp(-Ts / max(atau, 1e-6))
    ex_drv = 1.0 - math.exp(-dt / max(drv_tau, 1e-9))
    rec_i = 0
    nrec = rec.shape[0]
    PB = 0.0; PR = 0.0
    EB = 0.0; ER = 0.0; nacc = 0
    bias_g = 0.0
    cur = np.zeros(2)
    # touchdown / lift feed-forward state
    cot_ = ct / st_
    sc_ = st_ * ct
    uf0 = cr; uf1 = -sr                  # stage direction that moves the ink along the azimuth at constant housing height
    Fbn = math.hypot(Fb0, Fb1)
    ub0 = Fb0 / Fbn if Fbn > 0 else 1.0  # direction in which the actuator holds the paper's normal load
    ub1 = Fb1 / Fbn if Fbn > 0 else 0.0
    q_pre = (tdsref - s_min) * cot_      # stage deflection that lands the ball where it writes (refill on its stop)
    rb_qm = np.zeros((RB, 2)); qm_last = np.zeros(2)
    Ta = dt * adec
    r_ab = math.exp(-2.0 * math.pi * max(tdlp, 1e-3) * Ta)
    a_ab = 1.0 - r_ab * r_ab; b_ab = (1.0 - r_ab) ** 2          # critically damped alpha-beta tracker
    td_x = 0.0; td_v = 0.0; td_init = 0; k_samp = 0; td_stop = 1
    td_c = 0; td_c_prev = 0; k_tdsw = -(1 << 30); k_quiet = -1; k_exc = -1; td_armed = 0; td_left = 0
    qf0 = 0.0; qf1 = 0.0

    for k in range(n):
        # ======================= outer tick: sensors -> estimator -> stage reference
        if k % sdec == 0 and mode != 0 and mode != 5:
            pim_now0 = pimu[0]; pim_now1 = pimu[1]
            rb_pimu[tick % 1024, 0] = pim_now0; rb_pimu[tick % 1024, 1] = pim_now1
            lag_t = max(0, (od - idl) // sdec)
            jl = (tick - lag_t) % 1024
            ph0 = o_meas[0] + (pim_now0 - rb_pimu[jl, 0])
            ph1 = o_meas[1] + (pim_now1 - rb_pimu[jl, 1])
            valid = o_valid > 0.5
            in_contact = (s_meas > s_min + cthr) or (not reqc)
            corr0 = 0.0; corr1 = 0.0
            target_g = 0.0
            if mode == 3:
                if valid:
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
                    dhat[0] = rh * (ch * xk[0, 3] + sh * xk[0, 4])
                    dhat[1] = rh * (ch * xk[1, 3] + sh * xk[1, 4])
                    conf = min(1.0, max(0.0, 1.0 - (nis_f - 1.0) / max(nishi - 1.0, 1e-6)))
                    f_tr = wkf / (2.0 * math.pi)
                    if fgate > 0.0:
                        gate = min(1.0, max(0.0, (f_tr - (fgate - 0.5 * fgw)) / max(fgw, 1e-6)))
                        conf = conf * gate
                    corr0 = -dhat[0]; corr1 = -dhat[1]
                    target_g = g_as * conf if in_contact else 0.0
                else:
                    need_reinit = 1
                    target_g = 0.0
            elif mode == 4:   # oracle: true housing deviation from its clean (tremor-free) path
                dhat[0] = pH[0] - dtrue[k, 0]; dhat[1] = pH[1] - dtrue[k, 1]
                corr0 = -dhat[0]; corr1 = -dhat[1]
                target_g = g_as if in_contact else 0.0
                conf = 1.0
            elif mode == 7:   # external: the harness supplies a causal disturbance estimate per step in dtrue
                dhat[0] = dtrue[k, 0]; dhat[1] = dtrue[k, 1]
                corr0 = -dhat[0]; corr1 = -dhat[1]
                target_g = g_as if in_contact else 0.0
                conf = 1.0
            elif mode == 6:   # guided: user-paced progress along the template (as M1 mode 6)
                if valid and in_contact:
                    m_t = tmpl.shape[0]
                    best = 1e9; bj = prog
                    j0 = max(0, prog - 20); j1 = min(m_t, prog + (4000 if reacq == 1 else 200))
                    reacq = 0
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
                    reacq = 1
            g_eff = g_eff + alpha_a * (target_g - g_eff)
            bias_g = bias_g + alpha_a * ((1.0 if in_contact else 0.0) - bias_g)
            qn0 = g_eff * (Ji00 * corr0 + Ji01 * corr1)
            qn1 = g_eff * (Ji10 * corr0 + Ji11 * corr1)
            if td_on:
                # touchdown / lift feed-forward: acts at once (not through the authority ramp)
                if td_c == 0 and td_stop == 1:
                    qfm = tdpre * q_pre                   # in the air: pre-position so the ball lands where it writes
                else:
                    shp = td_x + td_v * ((k - k_samp) * dt + tdlead)
                    dev = tdsref - shp
                    if dev > tddz:
                        dev -= tddz
                    elif dev < -tddz:
                        dev += tddz
                    else:
                        dev = 0.0
                    qfm = tdK * sc_ * dev
                qf0 = qfm * uf0; qf1 = qfm * uf1
                if tdprio == 0:                           # shared: the sum is tapered
                    qn0, qn1 = _taper(qn0 + qf0, qn1 + qf1, qlim, qtap)
                elif tdprio == 1:                         # feed-forward first, the tremor command gets what is left
                    a0, a1 = _taper(qf0, qf1, qlim, qtap)
                    b0, b1 = _taper(qn0, qn1, qlim - math.hypot(a0, a1), qtap)
                    qn0 = a0 + b0; qn1 = a1 + b1
                else:                                     # tremor first
                    b0, b1 = _taper(qn0, qn1, qlim, qtap)
                    a0, a1 = _taper(qf0, qf1, qlim - math.hypot(b0, b1), qtap)
                    qn0 = a0 + b0; qn1 = a1 + b1
            else:
                rq = math.hypot(qn0, qn1)
                knee = qlim - qtap
                if rq > knee and rq > 0:
                    rnew = knee + qtap * math.tanh((rq - knee) / qtap)
                    qn0 *= rnew / rq; qn1 *= rnew / rq
            dq0 = qn0 - qr[0]; dq1 = qn1 - qr[1]
            dmax = slew * Ts
            dm = math.hypot(dq0, dq1)
            if dm > dmax:
                dq0 *= dmax / dm; dq1 *= dmax / dm
            qr_prev2[0] = qr_prev[0]; qr_prev2[1] = qr_prev[1]
            qr_prev[0] = qr[0]; qr_prev[1] = qr[1]
            qr[0] += dq0; qr[1] += dq1
            qddr[0] = (qr[0] - 2 * qr_prev[0] + qr_prev2[0]) / (Ts * Ts)
            qddr[1] = (qr[1] - 2 * qr_prev[1] + qr_prev2[1]) / (Ts * Ts)
            qdr[0] = (qr[0] - qr_prev[0]) / Ts
            qdr[1] = (qr[1] - qr_prev[1]) / Ts
            tick += 1
        elif k % sdec == 0:
            tick += 1

        # ======================= inner piezo servo
        if k % vdec == 0 and mode != 0:
            if mode == 5:
                Vc[0] = min(max(Vfix, 0.0), V_rail); Vc[1] = V_mid
            else:
                kh = (k - hd) % RB
                vsat = 0.0
                bg = bias_g
                if td_on:
                    for axx in range(2):
                        qm_last[axx] = rb_q[kh, axx] + hn * np.random.standard_normal()
                    # contact state of the feed-forward.  Touchdown: the refill leaves its stop (axial sensor), or the
                    # Hall sees the stage pushed back along the load direction by more than td_det_e within 1 ms of
                    # leaving a quiet band (|e| < td_det_e/2) held for td_hold: a load step, which neither a free-stage
                    # oscillation nor a slowly growing contact load (slow touchdown) produces.  Lift: the refill is back
                    # on its stop after having left it, or 10 ms after a Hall-detected touchdown it never left.
                    eb = (qr[0] - qm_last[0]) * ub0 + (qr[1] - qm_last[1]) * ub1
                    off_stop = s_meas > s_min + tddets
                    if off_stop:
                        td_left = 1
                    if tddete > 0.0:
                        if abs(eb) < 0.5 * tddete:
                            if k_quiet < 0:
                                k_quiet = k
                            td_armed = 1 if (k - k_quiet) * dt >= tdhold else 0
                            k_exc = -1
                        else:
                            k_quiet = -1
                            if k_exc < 0:
                                k_exc = k
                    if (k - k_tdsw) * dt >= tdhold:
                        if td_c == 0:
                            hall_td = tddete > 0.0 and eb > tddete and td_armed == 1 and (k - k_exc) * dt <= 1e-3
                            if off_stop or hall_td:
                                td_c = 1
                                k_tdsw = k
                                td_armed = 0
                                td_left = 1 if off_stop else 0
                                if hall_td and not off_stop and tdvtd > 0.0:
                                    td_v = tdvtd / st_          # assumed descent speed until the slide is measured
                                    k_samp = k
                        elif not off_stop and (td_left == 1 or (k - k_tdsw) * dt > 0.01):
                            td_c = 0
                            k_tdsw = k
                            td_armed = 0
                    if tdbias == 1:
                        bg = tdkl * td_c
                        if tdho and td_c != td_c_prev and Ki > 0.0:
                            # load hand-over: at switch-on the integrator gives up the load share it already carries along
                            # the load direction (a slow touchdown), at switch-off it drops a negative share (a slow lift)
                            carried = Ki * (eint[0] * ub0 + eint[1] * ub1)
                            if td_c == 1:
                                tr_ = min(max(carried, 0.0), tdkl * Fbn)
                            else:
                                tr_ = -min(max(-carried, 0.0), tdkl * Fbn)
                            eint[0] -= tr_ * ub0 / Ki; eint[1] -= tr_ * ub1 / Ki
                    td_c_prev = td_c
                for axx in range(2):
                    if td_on:
                        qm = qm_last[axx]
                    else:
                        qm = rb_q[kh, axx] + hn * np.random.standard_normal()
                    e = qr[axx] - qm
                    # damping on the measurement only (no derivative kick from the 2 kHz reference steps)
                    vmeas = (qm - qm_prev[axx]) / Tv
                    qm_prev[axx] = qm
                    ed_f[axx] += alpha_d * (-vmeas - ed_f[axx])
                    Fb = Fb0 if axx == 0 else Fb1
                    F = (ffr * (k_tot * qr[axx] + (c_st + Kd) * qdr[axx] + m_eq * qddr[axx]) + ffb * bg * Fb
                         + Kp * e + Ki * eint[axx] + Kd * ed_f[axx])
                    Vcmd = V_mid + F / Fv
                    Vs = min(max(Vcmd, 0.0), V_rail)
                    if Vs == Vcmd or (Vcmd > V_rail and e < 0) or (Vcmd < 0.0 and e > 0):
                        eint[axx] += e * Tv
                    if Vs != Vcmd:
                        vsat = 1.0
                    Vc[axx] = Vs

        # ======================= driver and piezo (every step)
        PB = 0.0; PR = 0.0
        for axx in range(2):
            if mode == 0:
                cur[axx] = 0.0
                continue
            dV = (Vc[axx] - Vo[axx]) * ex_drv
            dvm = drv_slew * dt
            if dV > dvm:
                dV = dvm
            elif dV < -dvm:
                dV = -dvm
            Vn = min(max(Vo[axx] + dV, 0.0), V_rail)
            dV = Vn - Vo[axx]
            i_c = C_ax * dV / dt
            Vavg = 0.5 * (Vn + Vo[axx])
            Vo[axx] = Vn
            cur[axx] = i_c
            if i_c > 0.0:
                PB += V_rail * i_c
            p_c = Vavg * i_c
            if p_c > 0.0:
                PR += p_c / eta_c
            else:
                PR += eta_c * p_c
            u = (Vn - V_mid) / V_mid
            du = u - u_prev[axx]
            u_prev[axx] = u
            if bw_on:
                hB[axx] += bw_a * du - bw_b * abs(du) * hB[axx] - bw_g * du * abs(hB[axx])

        EB += PB * dt; ER += PR * dt; nacc += 1
        # ======================= mechanics
        qq = q[0] * q[0] + q[1] * q[1]
        ax_off = s + qq / (2.0 * L_piv)
        Cx = pH[0] + q[0] * xHx + q[1] * yHx + ax_off * ax_
        Cy = pH[1] + q[0] * xHy + q[1] * yHy + ax_off * ay_
        Cz = pH[2] + q[0] * xHz + q[1] * yHz + ax_off * az_
        qdq = (q[0] * qd[0] + q[1] * qd[1]) / L_piv
        vax = sd + qdq
        vCx = vH[0] + qd[0] * xHx + qd[1] * yHx + vax * ax_
        vCy = vH[1] + qd[0] * xHy + qd[1] * yHy + vax * ay_
        vCz = vH[2] + qd[0] * xHz + qd[1] * yHz + vax * az_
        delta = r_b - Cz
        Nf = 0.0; fx = 0.0; fy = 0.0
        if delta > 0.0:
            Nf = k_p * delta - c_p * vCz
            if Nf < 0.0:
                Nf = 0.0
        if Nf > 0.0:
            fx, fy = _lugre(zn, vCx, vCy, Nf, mu_k, mu_s, v_s, sg0, sg1, sg2, dt)
        else:
            zn[0] = 0.0; zn[1] = 0.0
        Ns = 0.0; fsx = 0.0; fsy = 0.0
        if skid_on:
            Sz = pH[2] + p_nom * st_ - r_ring * ct
            dS = -Sz
            if dS > 0.0:
                Ns = k_sk * dS - c_sk * vH[2]
                if Ns < 0.0:
                    Ns = 0.0
            if Ns > 0.0:
                fsx, fsy = _lugre(zs, vH[0], vH[1], Ns, mu_sk, mus_sk, vs_sk, sg0_sk, 0.0, 0.0, dt)
            else:
                zs[0] = 0.0; zs[1] = 0.0
        # generalised contact forces on the stage and the axial slide
        Q0 = fx * xHx + fy * xHy + Nf * xHz
        Q1 = fx * yHx + fy * yHy + Nf * yHz
        Qs = fx * ax_ + fy * ay_ + Nf * az_
        # hand (two-stage impedance, as model M1)
        Fhx = Khxy * (pref[k, 0] + dM[0] - pH[0]) + Chxy * (vref[k, 0] + vM[0] - vH[0])
        Fhy = Khxy * (pref[k, 1] + dM[1] - pH[1]) + Chxy * (vref[k, 1] + vM[1] - vH[1])
        Fhz = Khz * (z0 + pref[k, 2] + dM[2] - pH[2]) + Chz * (vref[k, 2] + vM[2] - vH[2]) - fpush[k]
        if Mh > 0.0:
            aMx = (-(Fhx) - ka * dM[0] - ba * vM[0]) / Mh
            aMy = (-(Fhy) - ka * dM[1] - ba * vM[1]) / Mh
            aMz = (-(Fhz + fpush[k]) - ka * dM[2] - ba * vM[2]) / Mh
            vM[0] += aMx * dt; vM[1] += aMy * dt; vM[2] += aMz * dt
            dM[0] += vM[0] * dt; dM[1] += vM[1] * dt; dM[2] += vM[2] * dt
        # stage
        stopf = 0.0
        Fa0 = 0.0; Fa1 = 0.0
        if lock_st:
            qdd[0] = 0.0; qdd[1] = 0.0
        else:
            df0 = dfree_max * (u_prev[0] - (hB[0] if bw_on else 0.0)) * bw_norm
            df1 = dfree_max * (u_prev[1] - (hB[1] if bw_on else 0.0)) * bw_norm
            Fa0 = k_b * (df0 - q[0])
            Fa1 = k_b * (df1 - q[1])
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
            qdd[0] = (Fa0 - k_par * q[0] - c_st * qd[0] + Q0 + Fs0 - m_cpl * aHp0 + Ft0) / m_eq
            qdd[1] = (Fa1 - k_par * q[1] - c_st * qd[1] + Q1 + Fs1 - m_cpl * aHp1 + Ft1) / m_eq
        # axial slide
        if lock_ax:
            sdd = 0.0
        else:
            Fsp = F_sp0 + k_sp * s
            Fperp = math.hypot(Q0, Q1)
            Fbush = -mu_b * bear * Fperp * math.tanh(sd / v_b)
            Fst = 0.0
            if s < s_min:
                Fst = k_stop * (s_min - s) - (c_stop * sd if sd < 0 else 0.0)
            elif s > s_max:
                Fst = -k_stop * (s - s_max) - (c_stop * sd if sd > 0 else 0.0)
            aHa = aH[0] * ax_ + aH[1] * ay_ + aH[2] * az_
            sdd = (Qs - Fsp - c_ax * sd + Fbush + Fst - m_ax * aHa) / m_ax
        # housing (total momentum; coupling through the previous step's relative accelerations)
        cx_ = m_cpl * (qdd[0] * xHx + qdd[1] * yHx) + m_ax * sdd * ax_
        cy_ = m_cpl * (qdd[0] * xHy + qdd[1] * yHy) + m_ax * sdd * ay_
        cz_ = m_cpl * (qdd[0] * xHz + qdd[1] * yHz) + m_ax * sdd * az_
        aH[0] = (Fhx + fx + fsx - cx_) / M_t
        aH[1] = (Fhy + fy + fsy - cy_) / M_t
        aH[2] = (Fhz + Nf + Ns - cz_) / M_t
        for j in range(3):
            vH[j] += aH[j] * dt
            pH[j] += vH[j] * dt
        if not lock_st:
            for j in range(2):
                qd[j] += qdd[j] * dt
                q[j] += qd[j] * dt
        if not lock_ax:
            sd += sdd * dt
            s += sd * dt
        # anti-aliasing low-pass on the housing acceleration (two state-variable biquads, semi-implicit)
        for j in range(3):
            aa1d[j] += (w_aa * w_aa * (aH[j] - aa1[j]) - (w_aa / aa_q1) * aa1d[j]) * dt
            aa1[j] += aa1d[j] * dt
            aa2d[j] += (w_aa * w_aa * (aa1[j] - aa2[j]) - (w_aa / aa_q2) * aa2d[j]) * dt
            aa2[j] += aa2d[j] * dt
        # ring buffers
        kk = k % RB
        rb_q[kk, 0] = q[0]; rb_q[kk, 1] = q[1]
        rb_pH[kk, 0] = pH[0]; rb_pH[kk, 1] = pH[1]; rb_pH[kk, 2] = pH[2]
        if imu_aa:
            rb_aH[kk, 0] = aa2[0]; rb_aH[kk, 1] = aa2[1]
        else:
            rb_aH[kk, 0] = aH[0]; rb_aH[kk, 1] = aH[1]
        rb_s[kk] = s
        rb_ok[kk] = opt_ok[k]
        if td_on:
            rb_qm[kk, 0] = qm_last[0]; rb_qm[kk, 1] = qm_last[1]
        # sensors
        if k % odec == 0:
            ko = (k - od) % RB
            hz = rb_pH[ko, 2] - z0
            ok = (rb_ok[ko] > 0.5) and (hz < olift) and (k >= od)
            if ok:
                o_meas[0] = rb_pH[ko, 0] + on_ * np.random.standard_normal()
                o_meas[1] = rb_pH[ko, 1] + on_ * np.random.standard_normal()
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
        if k % adec == 0:
            ks = (k - adl) % RB
            s_meas = rb_s[ks] + anz * np.random.standard_normal() if k >= adl else s
            if td_on and k >= adl:
                # housing-induced slide: measured slide minus the stage's own contribution cot(th) (u_ff . q), with the
                # Hall reading taken at the axial sample's acquisition time; alpha-beta tracker for the lead
                jq = (k - adl + hd) % RB
                sh_raw = s_meas - tdkap * cot_ * (uf0 * rb_qm[jq, 0] + uf1 * rb_qm[jq, 1])
                on_stop = s_meas <= s_min + tddets
                if td_init == 0 or (on_stop and td_c == 0):
                    td_x = sh_raw; td_v = 0.0; td_init = 1
                else:
                    pred = td_x + td_v * (k - k_samp) * dt
                    res_ = sh_raw - pred
                    td_x = pred + a_ab * res_
                    td_v = td_v + b_ab / Ta * res_
                k_samp = k
                td_stop = 1 if on_stop else 0
        # record
        if k % rdec == 0 and rec_i < nrec:
            r = rec[rec_i]
            r[R_t] = k * dt
            r[R_pHx] = pH[0]; r[R_pHy] = pH[1]; r[R_pHz] = pH[2]
            r[R_q1] = q[0]; r[R_q2] = q[1]; r[R_qr1] = qr[0]; r[R_qr2] = qr[1]; r[R_s] = s
            r[R_Nn] = Nf; r[R_fnx] = fx; r[R_fny] = fy
            r[R_Ns] = Ns; r[R_fsx] = fsx; r[R_fsy] = fsy
            qq = q[0] * q[0] + q[1] * q[1]
            ao = s + qq / (2.0 * L_piv)
            r[R_Cx] = pH[0] + q[0] * xHx + q[1] * yHx + ao * ax_
            r[R_Cy] = pH[1] + q[0] * xHy + q[1] * yHy + ao * ay_
            r[R_Cz] = pH[2] + q[0] * xHz + q[1] * yHz + ao * az_
            r[R_V1] = Vo[0]; r[R_V2] = Vo[1]; r[R_Fa1] = Fa0; r[R_Fa2] = Fa1
            r[R_contact] = 1.0 if Nf > 0.0 else 0.0
            r[R_skid_contact] = 1.0 if Ns > 0.0 else 0.0
            r[R_dhx] = dhat[0]; r[R_dhy] = dhat[1]
            r[R_conf] = g_eff; r[R_vsat] = vsat; r[R_stop] = stopf
            r[R_PrailB] = EB / max(nacc * dt, 1e-12); r[R_PrailR] = ER / max(nacc * dt, 1e-12)
            EB = 0.0; ER = 0.0; nacc = 0
            r[R_Fhx] = Fhx; r[R_Fhy] = Fhy; r[R_Fhz] = Fhz
            r[R_west] = wkf / (2 * math.pi)
            r[R_i1] = cur[0]; r[R_i2] = cur[1]
            r[R_incontact] = 1.0 if in_contact else 0.0
            r[R_aHx] = aa2[0]; r[R_aHy] = aa2[1]; r[R_aHz] = aa2[2]
            if td_on:
                r[R_qff1] = qf0; r[R_qff2] = qf1; r[R_td_sh] = td_x; r[R_td_state] = td_c
            rec_i += 1
    return rec_i
