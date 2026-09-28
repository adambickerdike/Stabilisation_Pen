r"""Compiled time-domain core of the hand-pen-paper model H1 (rigid pen with rotation).

State (page frame {P}, stabpen/frames.py conventions; small tilts, exact translation):
  pen: ball centre p (3) and velocity; tilt beta = (beta1, beta2), a pen point z along the axis moves
       z (beta1 t1 + beta2 t2), rotation vector phi = -beta2 t1 + beta1 t2 (roll ignored, axisymmetric pen);
       constant 5x5 mass matrix (CAD mass, CoM, transverse inertia) inverted outside the core;
  hand mass perturbation dM (3) with the arm spring/damper to the imposed hand path (HAP-26, P1 convention);
  imposed hand-frame rotation Psi(t) about axis n_w through pivot P (wrist tremor component);
  grip: finger-pad zone (transverse k_f, axial k_a, tilt kappa_f) and web zone (transverse k_w) between pen
        points and hand-frame points, stiffness-proportional damping (grip.py calibration);
  paper: skid-ring point (penalty normal + LuGre friction normalised by N, as model P1) and the ball
         (constant spring force F_c/sin(theta) inside a 0.3 mm protrusion margin, LuGre friction);
         optional viscous nose drag c_visc (idealised damped roller);
  device (kind): 1 active reaction mass (absolute position of the moving mass; actuator force limited,
         centring loop, stroke stops; axes with zero stroke are locked by a stiff spring), 2 passive tuned
         mass (spring/damper, stops), 3 scissored-pair control-moment gyroscopes (gimbal angle, rate and servo
         lag limits; torque 2 H cos(delta) delta_dot), 4 passive rotor spinning along the axis (gyroscopic
         coupling -H (beta1_dot t1 + beta2_dot t2));
  nib stage (optional): kinematic oracle stage as model P1's limits (0.30 mm soft limit with taper, 0.40 mm
         stop, 2 kHz reference with slew limit and contact-gated authority, second-order follower).
Integration: semi-implicit Euler at dt (25 us).  Every output is a SIMULATION result.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit

NAMES = [
    "dt", "n_steps", "rec_decim",
    "ax", "ay", "az", "t1x", "t1y", "t1z", "t2x", "t2y", "t2z", "sin_th", "cos_th",
    "Mi00", "Mi01", "Mi02", "Mi03", "Mi04", "Mi11", "Mi12", "Mi13", "Mi14", "Mi22", "Mi23", "Mi24", "Mi33", "Mi34", "Mi44",
    "zf", "zw", "kf", "kw", "ka", "kap", "beta_g",
    "Mh", "karm", "barm", "z0",
    "nwx", "nwy", "nwz", "Px", "Py", "Pz",
    "skid_on", "k_sk", "c_sk", "p_nom", "r_ring", "r_b", "mu_sk", "mus_sk", "vs", "sg0_sk",
    "N_nib0", "mu_n", "mus_n", "sg0_n", "margin_b", "ramp_b", "c_visc",
    "kind", "m_r", "z_d", "st1", "st2", "st3", "Fm1", "Fm2", "Fm3", "kc", "cc", "k_stop", "c_stop", "k_lock", "c_lock",
    "H", "dmax", "ratemax", "cmg1", "cmg2", "tau_g", "tau_c",
    "stage_on", "qlim", "qtap", "qstop", "ws", "zs", "sdec", "slew", "atau", "lock_rot", "m_pen",
    "vc_on", "vc_ki", "vc_delay",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)
KINDS = {"none": 0, "rm": 1, "tmd": 2, "cmg": 3, "gyro": 4, "mass": 0}
REC = [
    "t", "bx", "by", "bz", "ix", "iy", "contact", "skid_contact", "Ns", "Nn", "fsx", "fsy", "fnx", "fny",
    "b1", "b2", "dMx", "dMy", "dMz", "gfx", "gfy", "gfz", "cpx", "cpy", "cpz", "hfx", "hfy", "hfz",
    "r1", "r2", "r3", "Fd1", "Fd2", "Fd3", "dl1", "dl2", "dr1", "dr2", "ddl1", "ddl2", "tq1", "tq2",
    "q1", "q2", "qr1", "qr2", "sat", "Fgx", "Fgy", "Fgz", "psi", "vbx", "vby", "Fvx", "Fvy", "cx", "cy",
]
RIDX = {n: i for i, n in enumerate(REC)}
NREC = len(REC)

for _n, _i in IDX.items():
    globals()["I_" + _n] = _i
for _n, _i in RIDX.items():
    globals()["R_" + _n] = _i


@njit(cache=True)
def _lugre(zb, vx, vy, N, mu_k, mu_s, v_s, sg0, dt):
    """LuGre friction normalised by N (P-9), implicit bristle update (copy of sim/pencil/core.py::_lugre, sg1 = sg2 = 0)."""
    vn = math.hypot(vx, vy)
    gv = mu_k + (mu_s - mu_k) * math.exp(-(vn / v_s) ** 2)
    den = 1.0 + dt * sg0 * vn / gv
    z0n = (zb[0] + dt * vx) / den
    z1n = (zb[1] + dt * vy) / den
    zb[0] = z0n
    zb[1] = z1n
    return -N * sg0 * z0n, -N * sg0 * z1n


@njit(cache=True)
def simulate(P, pref, vref, fpush, psi, psid, uff, clean, intended, rec):
    dt = P[I_dt]
    n = int(P[I_n_steps])
    rdec = int(P[I_rec_decim])
    a = np.array([P[I_ax], P[I_ay], P[I_az]])
    t1 = np.array([P[I_t1x], P[I_t1y], P[I_t1z]])
    t2 = np.array([P[I_t2x], P[I_t2y], P[I_t2z]])
    sth = P[I_sin_th]
    Mi = np.zeros((5, 5))
    Mi[0, 0] = P[I_Mi00]; Mi[0, 1] = P[I_Mi01]; Mi[0, 2] = P[I_Mi02]; Mi[0, 3] = P[I_Mi03]; Mi[0, 4] = P[I_Mi04]
    Mi[1, 1] = P[I_Mi11]; Mi[1, 2] = P[I_Mi12]; Mi[1, 3] = P[I_Mi13]; Mi[1, 4] = P[I_Mi14]
    Mi[2, 2] = P[I_Mi22]; Mi[2, 3] = P[I_Mi23]; Mi[2, 4] = P[I_Mi24]
    Mi[3, 3] = P[I_Mi33]; Mi[3, 4] = P[I_Mi34]; Mi[4, 4] = P[I_Mi44]
    for i in range(5):
        for j in range(i):
            Mi[i, j] = Mi[j, i]
    zf = P[I_zf]; zw = P[I_zw]; kf = P[I_kf]; kw = P[I_kw]; ka = P[I_ka]; kap = P[I_kap]; bg = P[I_beta_g]
    Mh = P[I_Mh]; karm = P[I_karm]; barm = P[I_barm]; z0 = P[I_z0]
    nw = np.array([P[I_nwx], P[I_nwy], P[I_nwz]])
    Pv = np.array([P[I_Px], P[I_Py], P[I_Pz]])
    skid_on = P[I_skid_on] > 0.5; k_sk = P[I_k_sk]; c_sk = P[I_c_sk]; p_nom = P[I_p_nom]; r_ring = P[I_r_ring]
    r_b = P[I_r_b]; mu_sk = P[I_mu_sk]; mus_sk = P[I_mus_sk]; vs = P[I_vs]; sg0_sk = P[I_sg0_sk]
    N_nib0 = P[I_N_nib0]; mu_n = P[I_mu_n]; mus_n = P[I_mus_n]; sg0_n = P[I_sg0_n]; mb = P[I_margin_b]; rb_ramp = P[I_ramp_b]
    c_visc = P[I_c_visc]
    kind = int(P[I_kind]); m_r = P[I_m_r]; z_d = P[I_z_d]
    st = np.array([P[I_st1], P[I_st2], P[I_st3]]); Fm = np.array([P[I_Fm1], P[I_Fm2], P[I_Fm3]])
    kc = P[I_kc]; cc = P[I_cc]; k_stop = P[I_k_stop]; c_stop = P[I_c_stop]; k_lock = P[I_k_lock]; c_lock = P[I_c_lock]
    H = P[I_H]; dmax = P[I_dmax]; ratemax = P[I_ratemax]; cmg_on = np.array([P[I_cmg1], P[I_cmg2]])
    tau_g = P[I_tau_g]; tau_c = P[I_tau_c]
    stage_on = P[I_stage_on] > 0.5; qlim = P[I_qlim]; qtap = P[I_qtap]; qstop = P[I_qstop]; ws = P[I_ws]; zs_ = P[I_zs]
    sdec = int(P[I_sdec]); slew = P[I_slew]; atau = P[I_atau]
    lock_rot = P[I_lock_rot] > 0.5; m_pen = P[I_m_pen]
    vc_on = P[I_vc_on] > 0.5; vc_ki = P[I_vc_ki]; vc_dl = int(P[I_vc_delay])
    VB = 16384
    vbuf = np.zeros((VB, 2))
    corr = np.zeros(2); corr_d = np.zeros(2)
    Ts = sdec * dt
    alpha_a = 1.0 - math.exp(-Ts / max(atau, 1e-6))
    # skid point offset and its tilt Jacobian (phi x s for s = p_nom a + r_ring t1)
    # zone basis
    E = np.zeros((3, 3))
    for j in range(3):
        E[0, j] = t1[j]; E[1, j] = t2[j]; E[2, j] = a[j]
    # ---------------- state
    p = np.array([pref[0, 0], pref[0, 1], z0 + pref[0, 2]])
    v = np.zeros(3)
    b = np.zeros(2); bd = np.zeros(2)
    dM = np.zeros(3); vM = np.zeros(3)
    zsk = np.zeros(2); znb = np.zeros(2)
    U = np.zeros(3); W = np.zeros(3)
    for j in range(3):
        U[j] = p[j] + z_d * a[j]
    dl = np.zeros(2); dld = np.zeros(2); ddl = np.zeros(2)
    q = np.zeros(2); qd = np.zeros(2); qr = np.zeros(2); g_eff = 0.0
    rec_i = 0
    nrec = rec.shape[0]
    Q = np.zeros(5)
    acc = np.zeros(5)
    Fd = np.zeros(3)
    tq = np.zeros(2)
    satf = 0.0
    for k in range(n):
        # ---------------- kinematic helpers
        # hand reference (imposed) + perturbation; imposed rotation Psi about nw through Pv
        hx = pref[k, 0] + corr[0] + dM[0]; hy = pref[k, 1] + corr[1] + dM[1]; hz = z0 + pref[k, 2] + dM[2]
        hvx = vref[k, 0] + corr_d[0] + vM[0]; hvy = vref[k, 1] + corr_d[1] + vM[1]; hvz = vref[k, 2] + vM[2]
        ps = psi[k]; psd = psid[k]
        # hand tilt coordinates
        bh1 = ps * (nw[0] * t2[0] + nw[1] * t2[1] + nw[2] * t2[2])
        bh2 = -ps * (nw[0] * t1[0] + nw[1] * t1[1] + nw[2] * t1[2])
        bhd1 = psd * (nw[0] * t2[0] + nw[1] * t2[1] + nw[2] * t2[2])
        bhd2 = -psd * (nw[0] * t1[0] + nw[1] * t1[1] + nw[2] * t1[2])
        for j in range(5):
            Q[j] = 0.0
        Fg = np.zeros(3)
        # ---------------- grip zones
        for zone in range(2):
            z = zf if zone == 0 else zw
            kt = kf if zone == 0 else kw
            kx = ka if zone == 0 else 0.0
            # relative displacement pen point - hand point
            s0 = z * a[0]; s1 = z * a[1]; s2 = z * a[2]
            rx = s0 - Pv[0]; ry = s1 - Pv[1]; rz = s2 - Pv[2]
            wx = nw[1] * rz - nw[2] * ry; wy = nw[2] * rx - nw[0] * rz; wz = nw[0] * ry - nw[1] * rx   # nw x (s - P)
            dx = (p[0] - hx) + z * (b[0] * t1[0] + b[1] * t2[0]) - ps * wx
            dy = (p[1] - hy) + z * (b[0] * t1[1] + b[1] * t2[1]) - ps * wy
            dz = (p[2] - hz) + z * (b[0] * t1[2] + b[1] * t2[2]) - ps * wz
            ex = (v[0] - hvx) + z * (bd[0] * t1[0] + bd[1] * t2[0]) - psd * wx
            ey = (v[1] - hvy) + z * (bd[0] * t1[1] + bd[1] * t2[1]) - psd * wy
            ez = (v[2] - hvz) + z * (bd[0] * t1[2] + bd[1] * t2[2]) - psd * wz
            # K = kt (I - a a^T) + kx a a^T
            da = dx * a[0] + dy * a[1] + dz * a[2]
            ea = ex * a[0] + ey * a[1] + ez * a[2]
            fx = -(kt * (dx - da * a[0]) + kx * da * a[0]) - bg * (kt * (ex - ea * a[0]) + kx * ea * a[0])
            fy = -(kt * (dy - da * a[1]) + kx * da * a[1]) - bg * (kt * (ey - ea * a[1]) + kx * ea * a[1])
            fz = -(kt * (dz - da * a[2]) + kx * da * a[2]) - bg * (kt * (ez - ea * a[2]) + kx * ea * a[2])
            Fg[0] += fx; Fg[1] += fy; Fg[2] += fz
            Q[0] += fx; Q[1] += fy; Q[2] += fz
            Q[3] += z * (fx * t1[0] + fy * t1[1] + fz * t1[2])
            Q[4] += z * (fx * t2[0] + fy * t2[1] + fz * t2[2])
        # tilt stiffness of the pads relative to the hand frame
        Q[3] += -kap * (b[0] - bh1) - bg * kap * (bd[0] - bhd1)
        Q[4] += -kap * (b[1] - bh2) - bg * kap * (bd[1] - bhd2)
        # push force at the ball centre (external, as model P1)
        Q[2] += -fpush[k]
        # ---------------- paper: skid ring point s = p_nom a + r_ring t1; phi x s = p_nom (b1 t1 + b2 t2) - r_ring b1 a
        Ns = 0.0; fsx = 0.0; fsy = 0.0
        sz = p[2] - r_b + p_nom * (b[0] * t1[2] + b[1] * t2[2]) - r_ring * b[0] * a[2]
        svz = v[2] + p_nom * (bd[0] * t1[2] + bd[1] * t2[2]) - r_ring * bd[0] * a[2]
        svx = v[0] + p_nom * (bd[0] * t1[0] + bd[1] * t2[0]) - r_ring * bd[0] * a[0]
        svy = v[1] + p_nom * (bd[0] * t1[1] + bd[1] * t2[1]) - r_ring * bd[0] * a[1]
        if skid_on and sz < 0.0:
            Ns = k_sk * (-sz) - c_sk * svz
            if Ns < 0.0:
                Ns = 0.0
        if Ns > 0.0:
            fsx, fsy = _lugre(zsk, svx, svy, Ns, mu_sk, mus_sk, vs, sg0_sk, dt)
        else:
            zsk[0] = 0.0; zsk[1] = 0.0
        # ---------------- ball: constant spring force inside the protrusion margin, LuGre friction
        hb = p[2] - r_b
        Nn = 0.0
        if hb < mb:
            Nn = N_nib0 * min(1.0, (mb - hb) / rb_ramp)
        # stage velocity in the page (ink moves by q1/sin(th) h + q2 t2; h = (t1 + cot a)... use J with phi = 0 frame)
        qvx = qd[0] / sth * (t1[0] * sth + a[0] * P[I_cos_th]) + qd[1] * t2[0]
        qvy = qd[0] / sth * (t1[1] * sth + a[1] * P[I_cos_th]) + qd[1] * t2[1]
        fnx = 0.0; fny = 0.0
        if Nn > 0.0:
            fnx, fny = _lugre(znb, v[0] + qvx, v[1] + qvy, Nn, mu_n, mus_n, vs, sg0_n, dt)
        else:
            znb[0] = 0.0; znb[1] = 0.0
        # viscous nose drag (idealised damped roller), acting while the nose is on the paper
        Fvx = 0.0; Fvy = 0.0
        if c_visc > 0.0 and (Ns > 0.0 or Nn > 0.0):
            Fvx = -c_visc * svx; Fvy = -c_visc * svy
        # generalised forces of the skid (point s) and ball (s = 0)
        Fsx = fsx + Fvx; Fsy = fsy + Fvy; Fsz = Ns
        Q[0] += Fsx + fnx; Q[1] += Fsy + fny; Q[2] += Fsz + Nn
        Fdt1 = Fsx * t1[0] + Fsy * t1[1] + Fsz * t1[2]
        Fdt2 = Fsx * t2[0] + Fsy * t2[1] + Fsz * t2[2]
        Fda = Fsx * a[0] + Fsy * a[1] + Fsz * a[2]
        Q[3] += p_nom * Fdt1 - r_ring * Fda
        Q[4] += p_nom * Fdt2
        # ---------------- device
        for j in range(3):
            Fd[j] = 0.0
        if kind == 1 or kind == 2:
            # relative displacement of the moving mass in the pen frame
            px_ = p[0] + z_d * (a[0] + b[0] * t1[0] + b[1] * t2[0])
            py_ = p[1] + z_d * (a[1] + b[0] * t1[1] + b[1] * t2[1])
            pz_ = p[2] + z_d * (a[2] + b[0] * t1[2] + b[1] * t2[2])
            vx_ = v[0] + z_d * (bd[0] * t1[0] + bd[1] * t2[0])
            vy_ = v[1] + z_d * (bd[0] * t1[1] + bd[1] * t2[1])
            vz_ = v[2] + z_d * (bd[0] * t1[2] + bd[1] * t2[2])
            rx = U[0] - px_; ry = U[1] - py_; rz = U[2] - pz_
            ux = W[0] - vx_; uy = W[1] - vy_; uz = W[2] - vz_
            Fint = np.zeros(3)
            for i in range(3):
                ri = rx * E[i, 0] + ry * E[i, 1] + rz * E[i, 2]
                ui = ux * E[i, 0] + uy * E[i, 1] + uz * E[i, 2]
                if st[i] <= 0.0:
                    fi = -k_lock * ri - c_lock * ui
                else:
                    if kind == 1:
                        fi = uff[k, i] - kc * ri - cc * ui
                        if fi > Fm[i]:
                            fi = Fm[i]
                        elif fi < -Fm[i]:
                            fi = -Fm[i]
                    else:
                        fi = -kc * ri - cc * ui
                    Fd[i] = fi
                    if ri > st[i]:
                        fi += -k_stop * (ri - st[i]) - (c_stop * ui if ui > 0 else 0.0)
                    elif ri < -st[i]:
                        fi += -k_stop * (ri + st[i]) - (c_stop * ui if ui < 0 else 0.0)
                for j in range(3):
                    Fint[j] += fi * E[i, j]
            # the mass
            for j in range(3):
                W[j] += Fint[j] / m_r * dt
                U[j] += W[j] * dt
            # reaction on the pen at z_d
            Q[0] -= Fint[0]; Q[1] -= Fint[1]; Q[2] -= Fint[2]
            Q[3] -= z_d * (Fint[0] * t1[0] + Fint[1] * t1[1] + Fint[2] * t1[2])
            Q[4] -= z_d * (Fint[0] * t2[0] + Fint[1] * t2[1] + Fint[2] * t2[2])
        elif kind == 3:
            for i in range(2):
                if cmg_on[i] < 0.5:
                    tq[i] = 0.0
                    continue
                cd = math.cos(dl[i])
                rc = uff[k, i] / (2.0 * H * max(cd, 0.2)) - dl[i] / tau_c
                if rc > ratemax:
                    rc = ratemax
                elif rc < -ratemax:
                    rc = -ratemax
                if (dl[i] >= dmax and rc > 0.0) or (dl[i] <= -dmax and rc < 0.0):
                    rc = 0.0
                ddl[i] = (rc - dld[i]) / tau_g
                dld[i] += ddl[i] * dt
                dl[i] += dld[i] * dt
                if dl[i] > dmax * 1.05:
                    dl[i] = dmax * 1.05; dld[i] = 0.0
                elif dl[i] < -dmax * 1.05:
                    dl[i] = -dmax * 1.05; dld[i] = 0.0
                tq[i] = 2.0 * H * math.cos(dl[i]) * dld[i]
            Q[3] += tq[0]        # torque about t2 -> beta1
            Q[4] += -tq[1]       # torque about t1 -> beta2
        elif kind == 4:
            Q[3] += -H * bd[1]
            Q[4] += H * bd[0]
        # ---------------- pen and hand accelerations
        if lock_rot:
            for i in range(3):
                acc[i] = Q[i] / m_pen
            acc[3] = 0.0
            acc[4] = 0.0
        else:
            for i in range(5):
                s_ = 0.0
                for j in range(5):
                    s_ += Mi[i, j] * Q[j]
                acc[i] = s_
        aMx = (-Fg[0] - karm * dM[0] - barm * vM[0]) / Mh
        aMy = (-Fg[1] - karm * dM[1] - barm * vM[1]) / Mh
        aMz = (-Fg[2] - karm * dM[2] - barm * vM[2]) / Mh
        for j in range(3):
            v[j] += acc[j] * dt
            p[j] += v[j] * dt
        bd[0] += acc[3] * dt; bd[1] += acc[4] * dt
        b[0] += bd[0] * dt; b[1] += bd[1] * dt
        vM[0] += aMx * dt; vM[1] += aMy * dt; vM[2] += aMz * dt
        dM[0] += vM[0] * dt; dM[1] += vM[1] * dt; dM[2] += vM[2] * dt
        # ---------------- nib stage (kinematic oracle as model P1: 2 kHz reference, contact-gated authority)
        if stage_on:
            if k % sdec == 0:
                in_c = 1.0 if Nn > 0.0 else 0.0
                g_eff = g_eff + alpha_a * (in_c - g_eff)
                ex_ = p[0] - clean[k, 0]; ey_ = p[1] - clean[k, 1]
                # inverse Jacobian for azimuth frame (h, t2): q1 = sin(th) e.h, q2 = e.t2
                hxv = a[0] * P[I_cos_th] + t1[0] * sth; hyv = a[1] * P[I_cos_th] + t1[1] * sth
                eh = ex_ * hxv + ey_ * hyv
                e2 = ex_ * t2[0] + ey_ * t2[1]
                qn0 = -g_eff * sth * eh
                qn1 = -g_eff * e2
                rq = math.hypot(qn0, qn1)
                knee = qlim - qtap
                if rq > knee and rq > 0:
                    rnew = knee + qtap * math.tanh((rq - knee) / qtap)
                    qn0 *= rnew / rq; qn1 *= rnew / rq
                # as model P1 (sim/pencil/evaluate.py): tapered reference at >= 95 % of the soft limit
                satf = 1.0 if math.hypot(qn0, qn1) > 0.95 * qlim else 0.0
                dq0 = qn0 - qr[0]; dq1 = qn1 - qr[1]
                dmx = slew * Ts
                dm_ = math.hypot(dq0, dq1)
                if dm_ > dmx:
                    dq0 *= dmx / dm_; dq1 *= dmx / dm_
                qr[0] += dq0; qr[1] += dq1
            for i in range(2):
                qdd = ws * ws * (qr[i] - q[i]) - 2.0 * zs_ * ws * qd[i]
                qd[i] += qdd * dt
                q[i] += qd[i] * dt
            rq = math.hypot(q[0], q[1])
            if rq > qstop:
                q[0] *= qstop / rq; q[1] *= qstop / rq
                satf = 1.0
        # ---------------- voluntary (visual) correction of slow ink errors: integral with delay (optional)
        if vc_on:
            hxv_ = a[0] * P[I_cos_th] + t1[0] * sth; hyv_ = a[1] * P[I_cos_th] + t1[1] * sth
            ixn = p[0] + q[0] / sth * hxv_ + q[1] * t2[0]
            iyn = p[1] + q[0] / sth * hyv_ + q[1] * t2[1]
            kb = k % VB
            if Nn > 0.0:
                vbuf[kb, 0] = intended[k, 0] - ixn; vbuf[kb, 1] = intended[k, 1] - iyn
            else:
                vbuf[kb, 0] = 0.0; vbuf[kb, 1] = 0.0
            if k >= vc_dl:
                kd = (k - vc_dl) % VB
                corr_d[0] = vc_ki * vbuf[kd, 0]; corr_d[1] = vc_ki * vbuf[kd, 1]
                corr[0] += corr_d[0] * dt; corr[1] += corr_d[1] * dt
        # ---------------- record
        if k % rdec == 0 and rec_i < nrec:
            r = rec[rec_i]
            r[R_t] = k * dt
            r[R_bx] = p[0]; r[R_by] = p[1]; r[R_bz] = p[2]
            hxv = a[0] * P[I_cos_th] + t1[0] * sth; hyv = a[1] * P[I_cos_th] + t1[1] * sth
            r[R_ix] = p[0] + q[0] / sth * hxv + q[1] * t2[0]
            r[R_iy] = p[1] + q[0] / sth * hyv + q[1] * t2[1]
            r[R_contact] = 1.0 if Nn > 0.0 else 0.0
            r[R_skid_contact] = 1.0 if Ns > 0.0 else 0.0
            r[R_Ns] = Ns; r[R_Nn] = Nn; r[R_fsx] = fsx; r[R_fsy] = fsy; r[R_fnx] = fnx; r[R_fny] = fny
            r[R_b1] = b[0]; r[R_b2] = b[1]
            r[R_dMx] = dM[0]; r[R_dMy] = dM[1]; r[R_dMz] = dM[2]
            for j in range(3):
                r[R_gfx + j] = p[j] + zf * (a[j] + b[0] * t1[j] + b[1] * t2[j])
                r[R_cpx + j] = p[j] + z_d * (a[j] + b[0] * t1[j] + b[1] * t2[j])
            r[R_hfx] = pref[k, 0] + dM[0]; r[R_hfy] = pref[k, 1] + dM[1]; r[R_hfz] = z0 + pref[k, 2] + dM[2]
            if kind == 1 or kind == 2:
                px_ = p[0] + z_d * (a[0] + b[0] * t1[0] + b[1] * t2[0])
                py_ = p[1] + z_d * (a[1] + b[0] * t1[1] + b[1] * t2[1])
                pz_ = p[2] + z_d * (a[2] + b[0] * t1[2] + b[1] * t2[2])
                rx = U[0] - px_; ry = U[1] - py_; rz = U[2] - pz_
                r[R_r1] = rx * t1[0] + ry * t1[1] + rz * t1[2]
                r[R_r2] = rx * t2[0] + ry * t2[1] + rz * t2[2]
                r[R_r3] = rx * a[0] + ry * a[1] + rz * a[2]
            r[R_Fd1] = Fd[0]; r[R_Fd2] = Fd[1]; r[R_Fd3] = Fd[2]
            r[R_dl1] = dl[0]; r[R_dl2] = dl[1]; r[R_dr1] = dld[0]; r[R_dr2] = dld[1]; r[R_ddl1] = ddl[0]; r[R_ddl2] = ddl[1]
            r[R_tq1] = tq[0]; r[R_tq2] = tq[1]
            r[R_q1] = q[0]; r[R_q2] = q[1]; r[R_qr1] = qr[0]; r[R_qr2] = qr[1]; r[R_sat] = satf
            r[R_Fgx] = Fg[0]; r[R_Fgy] = Fg[1]; r[R_Fgz] = Fg[2]
            r[R_psi] = ps; r[R_vbx] = v[0]; r[R_vby] = v[1]; r[R_Fvx] = Fvx; r[R_Fvy] = Fvy
            r[R_cx] = corr[0]; r[R_cy] = corr[1]
            rec_i += 1
    return rec_i
