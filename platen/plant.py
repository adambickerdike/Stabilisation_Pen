r"""The moving-page plant: HW1's hand and rigid pen co-simulated with a servo-driven page stage (SIMULATION tooling).

Structure (2-D, page plane, SI units; the hand and pen are exactly model HW1's for a rigid pen, handwriting/plant.py):

  imposed hand path p_ref --[arm k_a, b_a]-- hand mass M (perturbation dM) --[grip K_g, C_g]-- pen (tip p_H)
  pen:    m_pen a_H = F_grip + F_ball + F_writer
  hand:   M dM'' = -k_a dM - b_a dM' - F_grip + F_hand_paper          (F_grip as HW1)
  ball:   LuGre friction (HW1's law and constants) on the RELATIVE velocity v_tip - v_paper while in contact
  writer: 'hw1'      F_writer = -F_ball (HW1's convention: the writer cancels whatever drag the ball meets)
          'intended' F_writer = -F_ball(v_intended) (a second bristle state driven by the intended tip velocity: the
                     writer's learnt compensation covers the drag of the voluntary motion only; tremor-band drag and
                     the drag the moving page adds act on the pen)
          'none'     F_writer = 0 (P1's open-loop hand)
  page:   a two-layer stage.  COARSE carriage (belt H-bot class): m_c, force-limited PD + feedforward on its own
          reference (the slow word motion; held at 0 in free writing).  FINE plate (voice-coil class, rides on the
          coarse carriage, carries the paper): m_f, relative travel +-q_lim (soft limit on the command, hard stop
          beyond q_stop), a HW1-style servo: command (per 2 kHz tick) -> radial soft limit -> slew limit -> latency ->
          2nd-order follower (servo_hz, zeta) -> inner loop (inverse dynamics + PD on the ABSOLUTE page position
          from the encoders, quantised; velocity from the filtered encoder difference) limited to F_peak.
          Guide friction on each layer (Coulomb, tanh-smoothed, + viscous).
  paper:  rigid on the plate (default), or a 3 g sheet held by a LuGre hold-down contact (normal force N_hold) and
          loaded by the ball and, if the hand rests on the paper, by a LuGre skin contact (N_hand) whose reaction acts on
          the hand mass: page slip under the hand.
  ink:    tip - paper displacement (page frame; the page is at 0 at t = 0).
Controller (per 2 kHz tick):
  mode 0  external page command per tick (a tremor estimate, perfect knowledge, ...), as HW1's qext
  mode 1  online: the tip is observed by a camera-class sensor (frame rate, latency, white noise, a marker offset that
          moves with the pen's rotation: kappa x the imposed hand tremor), the error e = marker - target_tip is
          predicted to t + horizon by a multi-horizon linear (AR) predictor over the latest frames, and the fine stage
          is commanded to  e_hat + page_offset(t + horizon)  (page_offset: the accepted word's page motion, known).
  Z-lift (accepted mode): the page drops away to break contact; contact follows the commanded state after
          lift_delay (both directions), as the grounded five-bar's delayed contact.  A supervisor refuses (holds the
          page, drops it) if the platen's OWN estimate of the ink error exceeds abort_err for abort_t during requested
          ink.  In free writing the contact is the writer's pen-down, as in HW1.
Integration: semi-implicit Euler at HW1's step (25 us), in HW1's order, so that with the page held still and the
'hw1' writer convention the pen reproduces handwriting.plant.run for the ordinary pen (a test checks it).
Every output is SIMULATION; every parameter carries its label in platen/design.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

import numpy as np
from numba import njit

from . import _env  # noqa: F401  (environment before numba compiles)

# ------------------------------------------------------------------ parameter vector
NAMES = [
    "dt", "n", "rec_decim", "tick_decim",
    # hand and pen (HW1)
    "Kg", "Cg", "Mh", "ka", "ba", "wc_mode", "m_pen",
    # ball-paper contact (HW1 LuGre)
    "N_ball", "mu_b", "mu_s_b", "v_s", "x_pre",
    # fine plate
    "m_f", "F_pk_f", "q_lim_f", "q_tap_f", "q_stop_f", "k_stop", "c_stop", "w_f", "z_f", "lat_f", "slew_f",
    "Kp_f", "Kd_f", "Fc_f", "c_f", "enc_f", "vfilt_f",
    # coarse carriage
    "coarse_on", "m_c", "F_pk_c", "Kp_c", "Kd_c", "Fc_c", "c_c", "q_stop_c",
    # paper
    "paper_rigid", "m_p", "N_hold", "mu_hold", "mu_s_hold", "x_pre_hold", "c_hold", "N_hand", "mu_hand", "mu_s_hand",
    # controller
    "mode", "cam_every", "cam_lat", "cam_noise", "kappa", "n_phase", "ar_order", "horizon",
    # contact / lift / supervisor
    "lift_mode", "lift_up_ticks", "lift_down_ticks", "abort_err", "abort_ticks",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)
REC = ["t", "tipx", "tipy", "inkx", "inky", "pagex", "pagey", "paperx", "papery", "cx", "cy", "fx", "fy",
       "Ffx", "Ffy", "Fcx", "Fcy", "Fbx", "Fby", "contact", "satf", "satc", "stop", "abort", "pcx", "pcy",
       "handx", "handy", "emx", "emy", "rx", "ry"]
RIDX = {n: i for i, n in enumerate(REC)}
NREC = len(REC)
RB = 512            # ring buffers (ticks / frames)


@njit(cache=True)
def _lugre(z0, z1, v0, v1, N, mu_k, mu_s, v_s, x_pre, dt):
    """HW1's vector LuGre bristle update (exact exponential step) and friction force (-N sigma0 z)."""
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
def _quant(x, q):
    if q <= 0.0:
        return x
    return q * math.floor(x / q + 0.5)


@njit(cache=True)
def simulate(P, pref, vref, vint, trem, down, cmd_ext, tgt_tick, off_tick, offv_tick, offa_tick,
             cref_tick, cvel_tick, cacc_tick, lift_cmd, ref_ink, ar_coef, seed, rec):
    np.random.seed(seed)
    dt = P[0]; n = int(P[1]); rdec = int(P[2]); tdec = int(P[3])
    Kg = P[4]; Cg = P[5]; Mh = P[6]; ka = P[7]; ba = P[8]; wcm = int(P[9]); mpen = P[10]
    Nb = P[11]; mub = P[12]; musb = P[13]; vs = P[14]; xpre = P[15]
    mf = P[16]; Fpkf = P[17]; qlim = P[18]; qtap = P[19]; qstop = P[20]; kstop = P[21]; cstop = P[22]
    wf = P[23]; zf = P[24]; latf = int(P[25]); slewf = P[26]; Kpf = P[27]; Kdf = P[28]; Fcf = P[29]; cf = P[30]
    encf = P[31]; vfilt = P[32]
    con_on = P[33] > 0.5; mc = P[34]; Fpkc = P[35]; Kpc = P[36]; Kdc = P[37]; Fcc = P[38]; cc = P[39]; qstopc = P[40]
    prig = P[41] > 0.5; mp = P[42]; Nh = P[43]; muh = P[44]; mush = P[45]; xph = P[46]; ch = P[47]
    Nhand = P[48]; muhand = P[49]; mushand = P[50]
    mode = int(P[51]); cam_every = int(P[52]); cam_lat = int(P[53]); cam_noise = P[54]; kappa = P[55]
    n_phase = int(P[56]); order = int(P[57]); horizon = P[58]
    lift_mode = int(P[59]); up_t = int(P[60]); dn_t = int(P[61]); abort_err = P[62]; abort_ticks = int(P[63])
    Ts = dt * tdec
    nt = cmd_ext.shape[0]
    # state: hand, pen
    dM0 = 0.0; dM1 = 0.0; vM0 = 0.0; vM1 = 0.0
    pH0 = pref[0, 0]; pH1 = pref[0, 1]; vH0 = 0.0; vH1 = 0.0
    # page: coarse (absolute), fine (relative to coarse), paper slip (relative to plate)
    xc0 = 0.0; xc1 = 0.0; vc0 = 0.0; vc1 = 0.0
    xf0 = 0.0; xf1 = 0.0; vf0 = 0.0; vf1 = 0.0
    xs0 = 0.0; xs1 = 0.0; vs0 = 0.0; vs1 = 0.0
    # bristles: ball-paper, writer's compensation, paper-plate, hand-paper
    zb0 = 0.0; zb1 = 0.0; zw0 = 0.0; zw1 = 0.0; zh0 = 0.0; zh1 = 0.0; zk0 = 0.0; zk1 = 0.0
    # fine follower and command path
    r0 = 0.0; r1 = 0.0; vr0 = 0.0; vr1 = 0.0; ar0 = 0.0; ar1 = 0.0
    qc0 = 0.0; qc1 = 0.0
    rb_cmd = np.zeros((RB, 2))
    # encoder velocity estimate (absolute page)
    xm_prev0 = 0.0; xm_prev1 = 0.0; ve0 = 0.0; ve1 = 0.0
    alpha_v = 1.0 - math.exp(-2.0 * math.pi * vfilt * dt) if vfilt > 0.0 else 1.0
    # camera ring buffer: frame value (error e = marker - target at acquisition), acquisition tick
    fr_e = np.zeros((RB, 2)); fr_tick = np.zeros(RB, np.int64); fr_ink = np.zeros((RB, 2)); nfr = 0
    # contact / lift / supervisor
    contact = False
    lift_state = 0 if lift_mode == 1 else 1          # 1: page up (contact possible)
    lift_target = lift_state; lift_due = -1
    aborted = False; over = 0; hold0 = 0.0; hold1 = 0.0
    pc0 = 0.0; pc1 = 0.0
    em0 = 0.0; em1 = 0.0
    satf = 0.0; satc = 0.0; stopf = 0.0
    Ff0 = 0.0; Ff1 = 0.0; Fc0 = 0.0; Fc1 = 0.0
    tick = 0; nrec = 0
    xabs0 = 0.0; xabs1 = 0.0
    for k in range(n):
        # ------------------------------------------------ controller tick
        if k % tdec == 0:
            # camera frame (mode 1): marker = tip + kappa x imposed tremor (+ noise); stored with the target
            if mode == 1 and tick % cam_every == 0:
                j = nfr % RB
                ti = tick if tick < tgt_tick.shape[0] else tgt_tick.shape[0] - 1
                mk0 = pH0 + kappa * trem[k, 0] + cam_noise * np.random.standard_normal()
                mk1 = pH1 + kappa * trem[k, 1] + cam_noise * np.random.standard_normal()
                fr_e[j, 0] = mk0 - tgt_tick[ti, 0]; fr_e[j, 1] = mk1 - tgt_tick[ti, 1]
                # the platen's own ink estimate (marker - encoder page) for the supervisor
                fr_ink[j, 0] = mk0 - (xc0 + xf0); fr_ink[j, 1] = mk1 - (xc1 + xf1)
                fr_tick[j] = tick
                nfr += 1
            # page command
            if mode == 0:
                if tick < nt:
                    pc0 = cmd_ext[tick, 0]; pc1 = cmd_ext[tick, 1]
            else:
                # newest frame available at this tick
                jl = -1
                for back in range(min(nfr, 64)):
                    jj = (nfr - 1 - back) % RB
                    if fr_tick[jj] + cam_lat <= tick:
                        jl = nfr - 1 - back
                        break
                e0 = 0.0; e1 = 0.0
                if jl >= order - 1:
                    ph = tick - fr_tick[jl % RB]
                    if ph >= n_phase:
                        ph = n_phase - 1
                    for q in range(order):
                        jj = (jl - q) % RB
                        e0 += ar_coef[ph, q] * fr_e[jj, 0]
                        e1 += ar_coef[ph, q] * fr_e[jj, 1]
                elif jl >= 0:
                    e0 = fr_e[jl % RB, 0]; e1 = fr_e[jl % RB, 1]
                em0 = e0; em1 = e1
                th = tick + int(horizon / Ts + 0.5)
                if th >= off_tick.shape[0]:
                    th = off_tick.shape[0] - 1
                pc0 = e0 + off_tick[th, 0]; pc1 = e1 + off_tick[th, 1]
                # supervisor on the platen's own ink estimate (accepted mode)
                if lift_mode == 1 and not aborted and jl >= 0:
                    tj = fr_tick[jl % RB]
                    if tj < ref_ink.shape[0] and ref_ink[tj, 2] > 0.5:
                        d0 = fr_ink[jl % RB, 0] - ref_ink[tj, 0]; d1 = fr_ink[jl % RB, 1] - ref_ink[tj, 1]
                        if math.sqrt(d0 * d0 + d1 * d1) > abort_err:
                            over += 1
                        else:
                            over = 0
                        if over > abort_ticks:
                            aborted = True
                            hold0 = xc0 + xf0; hold1 = xc1 + xf1
                    else:
                        over = 0
            if aborted:
                pc0 = hold0; pc1 = hold1
            # Z-lift: commanded page state from the plan (accepted mode); delayed contact
            if lift_mode == 1:
                want = 1 if (tick < lift_cmd.shape[0] and lift_cmd[tick] > 0.5 and not aborted) else 0
                if want != lift_target:
                    lift_target = want
                    lift_due = tick + (up_t if want == 1 else dn_t)
                if lift_due >= 0 and tick >= lift_due:
                    lift_state = lift_target
                    lift_due = -1
            # fine command: radial soft limit on the travel relative to the coarse reference, slew limit
            ic = tick if tick < cref_tick.shape[0] else cref_tick.shape[0] - 1
            crx = cref_tick[ic, 0] if con_on else 0.0
            cry = cref_tick[ic, 1] if con_on else 0.0
            u0 = pc0 - crx; u1 = pc1 - cry
            rq = math.sqrt(u0 * u0 + u1 * u1)
            knee = qlim - qtap
            if rq > knee and rq > 0.0 and qtap > 0.0:
                rnew = knee + qtap * math.tanh((rq - knee) / qtap)
                u0 *= rnew / rq; u1 *= rnew / rq
            c0 = crx + u0; c1 = cry + u1
            d0 = c0 - qc0; d1 = c1 - qc1
            dm = math.sqrt(d0 * d0 + d1 * d1)
            dmax = slewf * Ts
            if dm > dmax and dm > 0.0:
                d0 *= dmax / dm; d1 *= dmax / dm
            qc0 += d0; qc1 += d1
            rb_cmd[tick % RB, 0] = qc0; rb_cmd[tick % RB, 1] = qc1
            tick += 1
        # ------------------------------------------------ fine follower (delayed command -> 2nd-order reference)
        tk = tick - 1 - latf
        if tk >= 0:
            u0 = rb_cmd[tk % RB, 0]; u1 = rb_cmd[tk % RB, 1]
        else:
            u0 = 0.0; u1 = 0.0
        ar0 = wf * wf * (u0 - r0) - 2.0 * zf * wf * vr0
        ar1 = wf * wf * (u1 - r1) - 2.0 * zf * wf * vr1
        vr0 += ar0 * dt; vr1 += ar1 * dt
        r0 += vr0 * dt; r1 += vr1 * dt
        # ------------------------------------------------ contact
        if lift_mode == 1:
            contact = (lift_state == 1) and (down[k] > 0.5)
        else:
            contact = down[k] > 0.5
        # ------------------------------------------------ forces: hand and pen
        Fg0 = Kg * (pref[k, 0] + dM0 - pH0) + Cg * (vref[k, 0] + vM0 - vH0)
        Fg1 = Kg * (pref[k, 1] + dM1 - pH1) + Cg * (vref[k, 1] + vM1 - vH1)
        vp0 = vc0 + vf0 + vs0; vp1 = vc1 + vf1 + vs1          # paper velocity (absolute)
        Fb0 = 0.0; Fb1 = 0.0; Fw0 = 0.0; Fw1 = 0.0
        if contact:
            zb0, zb1, Fb0, Fb1 = _lugre(zb0, zb1, vH0 - vp0, vH1 - vp1, Nb, mub, musb, vs, xpre, dt)
            if wcm == 1:
                Fw0 = -Fb0; Fw1 = -Fb1
            elif wcm == 2:
                zw0, zw1, fw0, fw1 = _lugre(zw0, zw1, vint[k, 0], vint[k, 1], Nb, mub, musb, vs, xpre, dt)
                Fw0 = -fw0; Fw1 = -fw1
        else:
            zb0 = 0.0; zb1 = 0.0; zw0 = 0.0; zw1 = 0.0
        # the hand resting on the paper (no palm rest): skin friction on the hand's absolute velocity
        Fhp0 = 0.0; Fhp1 = 0.0
        if Nhand > 0.0:
            vh0 = vref[k, 0] + vM0 - vp0; vh1 = vref[k, 1] + vM1 - vp1
            zh0, zh1, Fhp0, Fhp1 = _lugre(zh0, zh1, vh0, vh1, Nhand, muhand, mushand, vs, xpre, dt)
        aM0 = (-Fg0 - ka * dM0 - ba * vM0 + Fhp0) / Mh
        aM1 = (-Fg1 - ka * dM1 - ba * vM1 + Fhp1) / Mh
        aH0 = (Fg0 + Fb0 + Fw0) / mpen
        aH1 = (Fg1 + Fb1 + Fw1) / mpen
        # ------------------------------------------------ forces on the paper and the plate
        # reactions of the ball and of the hand on the paper
        Fpe0 = -Fb0 - Fhp0; Fpe1 = -Fb1 - Fhp1
        Fk0 = 0.0; Fk1 = 0.0                              # hold-down force of the plate on the paper (slip model)
        if not prig:
            zk0, zk1, Fk0, Fk1 = _lugre(zk0, zk1, vs0, vs1, Nh, muh, mush, vs, xph, dt)
        # encoders: absolute page = coarse + fine (quantised), filtered velocity
        xm0 = _quant(xc0 + xf0, encf); xm1 = _quant(xc1 + xf1, encf)
        if k == 0:
            xm_prev0 = xm0; xm_prev1 = xm1
        ve0 += alpha_v * ((xm0 - xm_prev0) / dt - ve0); ve1 += alpha_v * ((xm1 - xm_prev1) / dt - ve1)
        xm_prev0 = xm0; xm_prev1 = xm1
        if vfilt <= 0.0:
            ve0 = vc0 + vf0; ve1 = vc1 + vf1
        # coarse actuator: PD + feedforward on its own reference (moves the fine plate too)
        Fc0 = 0.0; Fc1 = 0.0; satc = 0.0
        if con_on:
            ic = (tick - 1) if (tick - 1) < cref_tick.shape[0] else cref_tick.shape[0] - 1
            mtot = mc + mf
            Fc0 = mtot * cacc_tick[ic, 0] + Kpc * (cref_tick[ic, 0] - xc0) + Kdc * (cvel_tick[ic, 0] - vc0)
            Fc1 = mtot * cacc_tick[ic, 1] + Kpc * (cref_tick[ic, 1] - xc1) + Kdc * (cvel_tick[ic, 1] - vc1)
            fm = math.sqrt(Fc0 * Fc0 + Fc1 * Fc1)
            if fm > Fpkc:
                Fc0 *= Fpkc / fm; Fc1 *= Fpkc / fm
                satc = 1.0
        # fine actuator: inverse dynamics of the follower + PD on the absolute page position
        Ff0 = mf * ar0 + Kpf * (r0 - xm0) + Kdf * (vr0 - ve0)
        Ff1 = mf * ar1 + Kpf * (r1 - xm1) + Kdf * (vr1 - ve1)
        fm = math.sqrt(Ff0 * Ff0 + Ff1 * Ff1)
        satf = 0.0
        if fm > Fpkf:
            Ff0 *= Fpkf / fm; Ff1 *= Fpkf / fm
            satf = 1.0
        # guide friction (fine on its relative velocity; coarse on its own), hard stops
        Fgf0 = -Fcf * math.tanh(vf0 / 1e-3) - cf * vf0; Fgf1 = -Fcf * math.tanh(vf1 / 1e-3) - cf * vf1
        Fst0 = 0.0; Fst1 = 0.0
        rf = math.sqrt(xf0 * xf0 + xf1 * xf1)
        stopf = 0.0
        if rf > qstop:
            ux = xf0 / rf; uy = xf1 / rf
            vrad = vf0 * ux + vf1 * uy
            fs = kstop * (rf - qstop) + (cstop * vrad if vrad > 0 else 0.0)
            Fst0 = -fs * ux; Fst1 = -fs * uy
            stopf = 1.0
        Fgc0 = 0.0; Fgc1 = 0.0
        if con_on:
            Fgc0 = -Fcc * math.tanh(vc0 / 1e-3) - cc * vc0; Fgc1 = -Fcc * math.tanh(vc1 / 1e-3) - cc * vc1
            rc = math.sqrt(xc0 * xc0 + xc1 * xc1)
            if rc > qstopc:
                ux = xc0 / rc; uy = xc1 / rc
                vrad = vc0 * ux + vc1 * uy
                fs = kstop * (rc - qstopc) + (cstop * vrad if vrad > 0 else 0.0)
                Fgc0 -= fs * ux; Fgc1 -= fs * uy
        # plate load from the paper: rigid paper -> the external paper forces act on the plate (paper mass in m_f);
        # slipping paper -> the reaction of the hold-down (friction + damping) acts on the plate
        if prig:
            Fpl0 = Fpe0; Fpl1 = Fpe1
        else:
            Fpl0 = -Fk0 + ch * vs0; Fpl1 = -Fk1 + ch * vs1
        # absolute accelerations: fine plate (a_c + a_f) and carriage a_c
        afa0 = (Ff0 + Fgf0 + Fst0 + Fpl0) / mf
        afa1 = (Ff1 + Fgf1 + Fst1 + Fpl1) / mf
        if con_on:
            ac0 = (Fc0 - Ff0 - Fgf0 - Fst0 + Fgc0) / mc
            ac1 = (Fc1 - Ff1 - Fgf1 - Fst1 + Fgc1) / mc
        else:
            ac0 = 0.0; ac1 = 0.0
        af0 = afa0 - ac0; af1 = afa1 - ac1
        # paper slip (relative to the plate): m_p (a_plate + a_s) = external - hold-down
        as0 = 0.0; as1 = 0.0
        if not prig:
            as0 = (Fpe0 + Fk0 - ch * vs0) / mp - afa0
            as1 = (Fpe1 + Fk1 - ch * vs1) / mp - afa1
        # ------------------------------------------------ integrate (semi-implicit Euler, HW1's order)
        vM0 += aM0 * dt; vM1 += aM1 * dt; dM0 += vM0 * dt; dM1 += vM1 * dt
        vH0 += aH0 * dt; vH1 += aH1 * dt; pH0 += vH0 * dt; pH1 += vH1 * dt
        vc0 += ac0 * dt; vc1 += ac1 * dt; xc0 += vc0 * dt; xc1 += vc1 * dt
        vf0 += af0 * dt; vf1 += af1 * dt; xf0 += vf0 * dt; xf1 += vf1 * dt
        if not prig:
            vs0 += as0 * dt; vs1 += as1 * dt; xs0 += vs0 * dt; xs1 += vs1 * dt
        # ------------------------------------------------ record
        if k % rdec == 0 and nrec < rec.shape[0]:
            px0 = xc0 + xf0 + xs0; px1 = xc1 + xf1 + xs1
            rec[nrec, 0] = k * dt
            rec[nrec, 1] = pH0; rec[nrec, 2] = pH1
            rec[nrec, 3] = pH0 - px0; rec[nrec, 4] = pH1 - px1
            rec[nrec, 5] = xc0 + xf0; rec[nrec, 6] = xc1 + xf1
            rec[nrec, 7] = px0; rec[nrec, 8] = px1
            rec[nrec, 9] = xc0; rec[nrec, 10] = xc1
            rec[nrec, 11] = xf0; rec[nrec, 12] = xf1
            rec[nrec, 13] = Ff0; rec[nrec, 14] = Ff1
            rec[nrec, 15] = Fc0; rec[nrec, 16] = Fc1
            rec[nrec, 17] = Fb0; rec[nrec, 18] = Fb1
            rec[nrec, 19] = 1.0 if contact else 0.0
            rec[nrec, 20] = satf; rec[nrec, 21] = satc; rec[nrec, 22] = stopf
            rec[nrec, 23] = 1.0 if aborted else 0.0
            rec[nrec, 24] = pc0; rec[nrec, 25] = pc1
            rec[nrec, 26] = pref[k, 0] + dM0; rec[nrec, 27] = pref[k, 1] + dM1
            rec[nrec, 28] = em0; rec[nrec, 29] = em1
            rec[nrec, 30] = r0; rec[nrec, 31] = r1
            nrec += 1
    return nrec


# ------------------------------------------------------------------ Python interface
@dataclass
class Stage:
    """The page stage (defaults = the proposed design of platen/design.py; labels there)."""
    # fine plate (voice-coil class): absolute-position servo, relative travel limit
    m_f: float = 0.45              # kg moving (X axis carries the Y axis; conservative for Y)
    F_peak_f: float = 20.0         # N, radial force cap (software; below the actuator's intermittent rating)
    q_lim_f: float = 5.0e-3        # m usable travel radius (soft limit)
    q_taper_f: float = 0.5e-3      # m taper of the soft limit
    q_stop_f: float = 6.0e-3       # m hard stop (end-stop bumpers)
    servo_hz: float = 40.0         # follower bandwidth
    zeta: float = 0.7
    latency: float = 0.5e-3        # s command latency (one tick)
    slew: float = 0.5              # m/s reference slew limit
    inner_hz: float = 250.0        # inner PD loop
    Fc_f: float = 0.05             # N guide friction (Coulomb, smoothed)
    c_f: float = 0.5               # N s/m viscous
    enc_res: float = 0.25e-6       # m encoder resolution (0 = ideal)
    vel_filter_hz: float = 1500.0  # Hz first-order filter on the encoder difference (0 = true velocity)
    # coarse carriage (belt H-bot class)
    coarse_on: bool = False
    m_c: float = 0.55              # kg carriage + fine-stage stator (the fine moving mass is added in the feedforward)
    F_peak_c: float = 20.0         # N software cap
    coarse_hz: float = 8.0
    coarse_zeta: float = 0.9
    Fc_c: float = 0.3              # N
    c_c: float = 2.0               # N s/m
    q_stop_c: float = 0.080        # m

    def group_delay(self) -> float:
        """Low-frequency group delay of the fine command path (s): latency + 2 zeta / omega_n (HW1's convention)."""
        return self.latency + 2.0 * self.zeta / (2.0 * math.pi * self.servo_hz)


@dataclass
class Paper:
    rigid: bool = True             # the sheet moves with the plate (hold-down never slips)
    m_p: float = 0.003             # kg (A6-A5 sheet about 1.3-2.5 g; with margin)
    N_hold: float = 4.0            # N hold-down normal force (low vacuum x area, or a tack mat)
    mu_hold: float = 0.4           # paper on the plate
    x_pre_hold: float = 2e-5       # m pre-sliding of the hold-down
    c_hold: float = 2.0            # N s/m damping of the stuck paper
    N_hand: float = 0.0            # N of the hand resting on the paper (0: the hand is on the palm rest)
    mu_hand: float = 0.5           # skin on paper


@dataclass
class Control:
    mode: int = 0                  # 0 external command per tick; 1 online camera + predictor
    cam_hz: float = 250.0
    cam_latency: float = 6.0e-3
    cam_noise: float = 15e-6       # m RMS per axis
    kappa: float = 0.0             # marker error per unit of imposed hand tremor (pen rotation, tilt)
    ar_coef: Optional[np.ndarray] = None   # (n_phase, order)
    horizon: Optional[float] = None        # s (default: the stage's group delay)
    lift_mode: int = 0             # 0 contact = the writer's pen-down; 1 Z-lift from the plan
    lift_up: float = 0.040         # s page rise until contact
    lift_down: float = 0.040       # s page drop until contact is broken
    abort_err: float = 0.20e-3     # m (the grounded five-bar's refusal threshold)
    abort_t: float = 0.010         # s


def build_params(dt: float, n: int, hand, pen_mass: float, writing, stage: Stage, paper: Paper, ctl: Control,
                 writer: str = "hw1", rec_hz: float = 4000.0, tick_hz: float = 2000.0):
    P = np.zeros(NP)

    def s(name, v):
        P[IDX[name]] = float(v)
    tdec = max(1, int(round(1.0 / (tick_hz * dt))))
    Ts = tdec * dt
    s("dt", dt); s("n", n); s("rec_decim", max(1, int(round(1.0 / (rec_hz * dt))))); s("tick_decim", tdec)
    s("Kg", hand.K_grip); s("Cg", hand.C_grip); s("Mh", hand.M_hand); s("ka", hand.k_arm); s("ba", hand.b_arm)
    s("wc_mode", {"none": 0, "hw1": 1, "intended": 2}[writer]); s("m_pen", pen_mass)
    s("N_ball", writing.N); s("mu_b", writing.mu_ball); s("mu_s_b", writing.mu_ball * writing.ms_ratio)
    s("v_s", writing.v_s); s("x_pre", writing.x_pre)
    mf = stage.m_f if paper.rigid else max(stage.m_f - paper.m_p, 1e-3)
    s("m_f", mf); s("F_pk_f", stage.F_peak_f); s("q_lim_f", stage.q_lim_f); s("q_tap_f", stage.q_taper_f)
    s("q_stop_f", stage.q_stop_f); s("k_stop", 2.0e4); s("c_stop", 20.0)
    s("w_f", 2.0 * math.pi * stage.servo_hz); s("z_f", stage.zeta); s("lat_f", int(round(stage.latency / Ts)))
    s("slew_f", stage.slew)
    w_in = 2.0 * math.pi * stage.inner_hz
    s("Kp_f", stage.m_f * w_in ** 2); s("Kd_f", 2.0 * 0.7 * stage.m_f * w_in)
    s("Fc_f", stage.Fc_f); s("c_f", stage.c_f); s("enc_f", stage.enc_res); s("vfilt_f", stage.vel_filter_hz)
    s("coarse_on", 1.0 if stage.coarse_on else 0.0); s("m_c", stage.m_c); s("F_pk_c", stage.F_peak_c)
    mt = stage.m_c + stage.m_f
    wc = 2.0 * math.pi * stage.coarse_hz
    s("Kp_c", mt * wc ** 2); s("Kd_c", 2.0 * stage.coarse_zeta * mt * wc); s("Fc_c", stage.Fc_c); s("c_c", stage.c_c)
    s("q_stop_c", stage.q_stop_c)
    s("paper_rigid", 1.0 if paper.rigid else 0.0); s("m_p", paper.m_p); s("N_hold", paper.N_hold)
    s("mu_hold", paper.mu_hold); s("mu_s_hold", paper.mu_hold * writing.ms_ratio); s("x_pre_hold", paper.x_pre_hold)
    s("c_hold", paper.c_hold); s("N_hand", paper.N_hand); s("mu_hand", paper.mu_hand)
    s("mu_s_hand", paper.mu_hand * writing.ms_ratio)
    cam_every = max(1, int(round(1.0 / (ctl.cam_hz * Ts))))
    cam_lat = int(round(ctl.cam_latency / Ts))
    s("mode", ctl.mode); s("cam_every", cam_every); s("cam_lat", cam_lat); s("cam_noise", ctl.cam_noise)
    s("kappa", ctl.kappa)
    coef = np.zeros((cam_lat + cam_every, 1)) if ctl.ar_coef is None else np.asarray(ctl.ar_coef, float)
    s("n_phase", coef.shape[0]); s("ar_order", coef.shape[1])
    s("horizon", stage.group_delay() if ctl.horizon is None else ctl.horizon)
    s("lift_mode", ctl.lift_mode); s("lift_up_ticks", int(round(ctl.lift_up / Ts)))
    s("lift_down_ticks", int(round(ctl.lift_down / Ts)))
    s("abort_err", ctl.abort_err); s("abort_ticks", int(round(ctl.abort_t / Ts)))
    info = {"tick_decim": tdec, "Ts": Ts, "cam_every": cam_every, "cam_lat_ticks": cam_lat,
            "horizon_s": P[IDX["horizon"]], "writer": writer, "pen_mass": pen_mass}
    return P, info, np.ascontiguousarray(coef)


class PlatenResult:
    """A platen run: named columns (REC) at rec_hz."""

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
        return self.xy("inkx")

    @property
    def tip(self):
        return self.xy("tipx")

    @property
    def page(self):
        return self.xy("pagex")

    @property
    def contact(self):
        return self.rec[:, RIDX["contact"]]

    def as_hw1(self):
        """An HW1 Result whose ink is the platen's ink (tip - paper) and whose handle is the pen tip, so that study R's
        measures (realdata.hw1.measures) and reader run unchanged."""
        from handwriting import plant as PL
        r = np.zeros((len(self.rec), PL.NREC))
        r[:, PL.RIDX["t"]] = self.t
        r[:, PL.RIDX["pHx"]:PL.RIDX["pHx"] + 2] = self.tip
        r[:, PL.RIDX["tipx"]:PL.RIDX["tipx"] + 2] = self.ink
        r[:, PL.RIDX["contact"]] = self.contact
        r[:, PL.RIDX["Fbx"]:PL.RIDX["Fbx"] + 2] = self.xy("Fbx")
        return PL.Result(r, dict(self.info))


def _ticks(arr, n_ticks, fill=0.0, cols=2):
    if arr is None:
        return np.full((n_ticks, cols), fill) if cols > 1 else np.full(n_ticks, fill)
    a = np.asarray(arr, float)
    return np.ascontiguousarray(a)


def run(pref: np.ndarray, vref: np.ndarray, down: np.ndarray, dt: float, *, hand, writing, pen_mass: float = 0.012,
        stage: Optional[Stage] = None, paper: Optional[Paper] = None, ctl: Optional[Control] = None,
        writer: str = "hw1", vint: Optional[np.ndarray] = None, trem: Optional[np.ndarray] = None,
        cmd_ext: Optional[np.ndarray] = None, tgt_tick: Optional[np.ndarray] = None,
        off_tick: Optional[np.ndarray] = None, offv_tick: Optional[np.ndarray] = None,
        offa_tick: Optional[np.ndarray] = None, cref_tick: Optional[np.ndarray] = None,
        cvel_tick: Optional[np.ndarray] = None, cacc_tick: Optional[np.ndarray] = None,
        lift_cmd: Optional[np.ndarray] = None, ref_ink: Optional[np.ndarray] = None, seed: int = 1,
        rec_hz: float = 4000.0) -> PlatenResult:
    """One platen run.  pref/vref/down/vint/trem at the plant step dt; *_tick arrays per 2 kHz controller tick."""
    stage = stage or Stage()
    paper = paper or Paper()
    ctl = ctl or Control()
    n = len(pref)
    P, info, coef = build_params(dt, n, hand, pen_mass, writing, stage, paper, ctl, writer, rec_hz)
    tdec = int(P[IDX["tick_decim"]])
    nt = int(math.ceil(n / tdec)) + 1
    z2 = np.zeros((nt, 2))
    vint = np.zeros_like(pref) if vint is None else np.ascontiguousarray(vint, float)
    trem = np.zeros_like(pref) if trem is None else np.ascontiguousarray(trem, float)
    cmd = np.zeros((1, 2)) if cmd_ext is None else np.ascontiguousarray(cmd_ext, float)

    def tk(a):
        return z2 if a is None else np.ascontiguousarray(a, float)
    tgt = z2 if tgt_tick is None else np.ascontiguousarray(tgt_tick, float)
    lc = np.ones(nt) if lift_cmd is None else np.ascontiguousarray(lift_cmd, float)
    ri = np.zeros((1, 3)) if ref_ink is None else np.ascontiguousarray(ref_ink, float)
    nrec = int(math.ceil(n / P[IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC))
    m = simulate(P, np.ascontiguousarray(pref, float), np.ascontiguousarray(vref, float), vint, trem,
                 np.ascontiguousarray(down, float), cmd, tgt, tk(off_tick), tk(offv_tick), tk(offa_tick),
                 tk(cref_tick), tk(cvel_tick), tk(cacc_tick), lc, ri, coef, int(seed), rec)
    info.update({"n_ticks": nt, "rec_hz": rec_hz, "stage": asdict(stage), "paper": asdict(paper),
                 "control": {k: (v if not isinstance(v, np.ndarray) else f"array{v.shape}") for k, v in asdict(ctl).items()}})
    return PlatenResult(rec[:m], info)
