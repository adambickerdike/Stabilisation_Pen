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

Extensions (opt/inertial, 2026-09-28; all off by default, and the default path is bit for bit the original: see
opt/inertial/tests/test_h1_regression.py):
  grip sleeve (slv_on): a second rigid body (the handle held by the fingers, 5 DOF, same small-angle coordinates as the
         pen).  The grip zones then act on the sleeve instead of the pen; the sleeve carries the pen through an
         actuated 2-DOF pivot: a stiff flexure pivot at z_p (translation springs, bending stiffness k_pr) and a
         2-axis actuator at z_a acting on the transverse relative displacement (act_ty 0: force actuator (voice
         coil) with a suspension spring, force limit and stops; act_ty 1: position actuator (piezo) = stiffness k_a
         towards a commanded displacement limited to the free stroke).  The push force can be routed through the
         sleeve (push_slv: applied at the sleeve's z = 0, no static couple), so the pivot carries the writing load.
  stage command source (stg_src): 0 oracle (clean reference, as before), 1 external estimate passed in `clean`,
         2 controller output.
  in-loop controller (ctl_on), run every cdec steps: measurements (body IMU acceleration at z_ib and tilt rates,
         sleeve IMU, device and pivot displacements, stage position, contact) with white noise and a latency of
         ilat ticks; external inputs from uff columns 3-6 (tracker estimate, frequency); a linear block
         x+ = A x + B [y; e; u_applied], [u; eps] = C x + D [y; e]; an optional tanh MLP on [x; y; e] added to u;
         an optional adaptive narrow-band block (phasor LMS on eps at the external frequency with a table of the
         inverse plant and a frequency-dependent amplitude cap: 9 values per frequency); commands u (device 3, pivot 2, stage 2) clipped to ul1..ul7.  uff columns 7-8 carry a
         pivot feed-forward.
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
    # ---- extensions (opt/inertial); zero = off
    "slv_on", "Si00", "Si01", "Si02", "Si03", "Si04", "Si11", "Si12", "Si13", "Si14", "Si22", "Si23", "Si24", "Si33",
    "Si34", "Si44", "zp", "kpt", "kpa", "kpr", "bpv", "za", "kas", "cas", "act_ty", "astr", "afm", "apre1", "apre2",
    "push_slv", "k_astop", "stg_src",
    "ctl_on", "cdec", "zib", "zis", "ilat", "acc_nd", "gyr_nd", "pos_nd", "iseed", "c_nx", "c_oA", "c_oB", "c_oC", "c_oD",
    "nn_h", "nn_oW1", "nn_ob1", "nn_oW2", "nn_ob2", "afc_on", "afc_mu", "afc_leak", "afc_ot", "afc_nf", "afc_f0",
    "afc_df", "afc_o1", "afc_o2", "afc_umax", "ul1", "ul2", "ul3", "ul4", "ul5", "ul6", "ul7", "iaa_hz", "afc_gate",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)
KINDS = {"none": 0, "rm": 1, "tmd": 2, "cmg": 3, "gyro": 4, "mass": 0}
# controller I/O sizes (extension): measurements, external inputs, commands, narrow-band error channels
NY = 16      # 0-1 body IMU acc (page x, y) at z_ib; 2-3 body tilt rates; 4-5 sleeve IMU acc at z_is; 6-7 sleeve tilt rates;
             # 8-10 device (reaction mass r1..r3 | CMG gimbal angles); 11-12 pivot relative displacement at z_a; 13-14 stage q; 15 contact
NE = 4       # uff columns 3-6: tracker estimate x, y (m), tracker frequency (Hz), spare
NU = 7       # 0-2 device (force t1, t2, a | CMG torque cmd 1, 2), 3-4 pivot (force or displacement), 5-6 stage (disturbance to cancel, page x, y)
NEPS = 2     # narrow-band error channels (outputs NU, NU+1 of the linear block)
REC = [
    "t", "bx", "by", "bz", "ix", "iy", "contact", "skid_contact", "Ns", "Nn", "fsx", "fsy", "fnx", "fny",
    "b1", "b2", "dMx", "dMy", "dMz", "gfx", "gfy", "gfz", "cpx", "cpy", "cpz", "hfx", "hfy", "hfz",
    "r1", "r2", "r3", "Fd1", "Fd2", "Fd3", "dl1", "dl2", "dr1", "dr2", "ddl1", "ddl2", "tq1", "tq2",
    "q1", "q2", "qr1", "qr2", "sat", "Fgx", "Fgy", "Fgz", "psi", "vbx", "vby", "Fvx", "Fvy", "cx", "cy",
    # ---- extensions (appended; zero when unused)
    "sx", "sy", "sz", "sb1", "sb2", "pd1", "pd2", "pf1", "pf2", "u1", "u2", "u3", "u4", "u5", "u6", "u7",
    "ia1", "ia2", "fp1", "fp2", "fpa", "eps1", "eps2", "afa1", "afa2",
]
NREC_ORIG = 57
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
    # ---------------- extensions (opt/inertial): grip sleeve + actuated pivot, stage command source, in-loop controller
    slv_on = P[I_slv_on] > 0.5
    Si = np.zeros((5, 5))
    Si[0, 0] = P[I_Si00]; Si[0, 1] = P[I_Si01]; Si[0, 2] = P[I_Si02]; Si[0, 3] = P[I_Si03]; Si[0, 4] = P[I_Si04]
    Si[1, 1] = P[I_Si11]; Si[1, 2] = P[I_Si12]; Si[1, 3] = P[I_Si13]; Si[1, 4] = P[I_Si14]
    Si[2, 2] = P[I_Si22]; Si[2, 3] = P[I_Si23]; Si[2, 4] = P[I_Si24]
    Si[3, 3] = P[I_Si33]; Si[3, 4] = P[I_Si34]; Si[4, 4] = P[I_Si44]
    for i in range(5):
        for j in range(i):
            Si[i, j] = Si[j, i]
    zp_ = P[I_zp]; kpt = P[I_kpt]; kpa = P[I_kpa]; kpr = P[I_kpr]; bpv = P[I_bpv]; za_ = P[I_za]; kas = P[I_kas]
    cas = P[I_cas]; act_ty = int(P[I_act_ty]); astr = P[I_astr]; afm = P[I_afm]; apre = np.array([P[I_apre1], P[I_apre2]])
    push_slv = P[I_push_slv] > 0.5; k_astop = P[I_k_astop]; stg_src = int(P[I_stg_src])
    ctl_on = P[I_ctl_on] > 0.5; cdec = max(int(P[I_cdec]), 1); zib = P[I_zib]; zis = P[I_zis]; ilat = int(P[I_ilat])
    Tc = cdec * dt
    sa_n = P[I_acc_nd] * math.sqrt(0.5 / Tc); sg_n = P[I_gyr_nd] * math.sqrt(0.5 / Tc); sp_n = P[I_pos_nd] * math.sqrt(0.5 / Tc)
    nx = int(P[I_c_nx]); oA = int(P[I_c_oA]); oB = int(P[I_c_oB]); oC = int(P[I_c_oC]); oD = int(P[I_c_oD])
    NI = NY + NE + NU
    NO = NU + NEPS
    nnh = int(P[I_nn_h]); oW1 = int(P[I_nn_oW1]); ob1 = int(P[I_nn_ob1]); oW2 = int(P[I_nn_oW2]); ob2 = int(P[I_nn_ob2])
    afc_on = P[I_afc_on] > 0.5; afc_mu = P[I_afc_mu]; afc_leak = P[I_afc_leak]; afc_ot = int(P[I_afc_ot])
    afc_nf = int(P[I_afc_nf]); afc_f0 = P[I_afc_f0]; afc_df = P[I_afc_df]; afc_o1 = int(P[I_afc_o1]); afc_o2 = int(P[I_afc_o2])
    afc_umax = P[I_afc_umax]
    ul = np.array([P[I_ul1], P[I_ul2], P[I_ul3], P[I_ul4], P[I_ul5], P[I_ul6], P[I_ul7]])
    ncol = uff.shape[1]
    ps_ = np.zeros(3); vs_ = np.zeros(3); bs_ = np.zeros(2); bds_ = np.zeros(2); Qs = np.zeros(5); accs = np.zeros(5)
    pdel = np.zeros(2); pfor = np.zeros(2); fpv = np.zeros(3)
    ucmd = np.zeros(NU); uapp = np.zeros(NU); yv = np.zeros(NY); ev = np.zeros(NE); epsv = np.zeros(NEPS)
    xc = np.zeros(max(nx, 1)); xn = np.zeros(max(nx, 1)); hbuf = np.zeros(max(nnh, 1))
    YB = 64
    ybuf = np.zeros((YB, NY))
    tick = 0
    afU = np.zeros(4)            # complex phasor gains of the two narrow-band outputs (re, im, re, im)
    afph = 0.0
    yraw = np.zeros(NY); gtab = np.zeros(9); dvec = np.zeros(3); dvel = np.zeros(3)
    nn_prev = 0.0
    # IMU anti-aliasing: 2nd-order low-pass (Butterworth damping) on the 8 inertial channels at the simulation rate
    w_aa = 2.0 * math.pi * (P[I_iaa_hz] if P[I_iaa_hz] > 0.0 else 400.0)
    aa_x = np.zeros(8); aa_v = np.zeros(8); aa_in = np.zeros(8)
    if ctl_on:
        np.random.seed(int(P[I_iseed]))
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
    if slv_on:
        for j in range(3):
            ps_[j] = p[j]
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
        # ---------------- in-loop controller tick (extension; off by default)
        if ctl_on:
            for j in range(2):
                aa_in[j] = acc[j] + zib * (acc[3] * t1[j] + acc[4] * t2[j])
                aa_in[4 + j] = accs[j] + zis * (accs[3] * t1[j] + accs[4] * t2[j])
            aa_in[2] = bd[0]; aa_in[3] = bd[1]; aa_in[6] = bds_[0]; aa_in[7] = bds_[1]
            for j in range(8):
                aa_v[j] += (w_aa * w_aa * (aa_in[j] - aa_x[j]) - 1.41421356 * w_aa * aa_v[j]) * dt
                aa_x[j] += aa_v[j] * dt
        if ctl_on and k % cdec == 0:
            for j in range(2):
                yraw[j] = aa_x[j] + sa_n * np.random.standard_normal()
            yraw[2] = aa_x[2] + sg_n * np.random.standard_normal()
            yraw[3] = aa_x[3] + sg_n * np.random.standard_normal()
            if slv_on:
                for j in range(2):
                    yraw[4 + j] = aa_x[4 + j] + sa_n * np.random.standard_normal()
                yraw[6] = aa_x[6] + sg_n * np.random.standard_normal()
                yraw[7] = aa_x[7] + sg_n * np.random.standard_normal()
                yraw[11] = pdel[0] + sp_n * np.random.standard_normal()
                yraw[12] = pdel[1] + sp_n * np.random.standard_normal()
            if kind == 1 or kind == 2:
                pxm = p[0] + z_d * (a[0] + b[0] * t1[0] + b[1] * t2[0])
                pym = p[1] + z_d * (a[1] + b[0] * t1[1] + b[1] * t2[1])
                pzm = p[2] + z_d * (a[2] + b[0] * t1[2] + b[1] * t2[2])
                for i in range(3):
                    yraw[8 + i] = ((U[0] - pxm) * E[i, 0] + (U[1] - pym) * E[i, 1] + (U[2] - pzm) * E[i, 2]
                                   + sp_n * np.random.standard_normal())
            elif kind == 3:
                yraw[8] = dl[0]
                yraw[9] = dl[1]
            yraw[13] = q[0] + sp_n * np.random.standard_normal()
            yraw[14] = q[1] + sp_n * np.random.standard_normal()
            yraw[15] = 1.0 if nn_prev > 0.0 else 0.0
            for j in range(NY):
                ybuf[tick % YB, j] = yraw[j]
            for j in range(NY):
                yv[j] = ybuf[(tick - ilat) % YB, j] if tick >= ilat else 0.0
            for j in range(NE):
                ev[j] = uff[k, 3 + j] if ncol >= 3 + NE else 0.0
            # linear block outputs
            for o in range(NO):
                s_ = 0.0
                for j in range(nx):
                    s_ += P[oC + o * nx + j] * xc[j]
                for j in range(NY):
                    s_ += P[oD + o * (NY + NE) + j] * yv[j]
                for j in range(NE):
                    s_ += P[oD + o * (NY + NE) + NY + j] * ev[j]
                if o < NU:
                    ucmd[o] = s_
                else:
                    epsv[o - NU] = s_
            # neural policy on [x; y; e]
            if nnh > 0:
                nin = nx + NY + NE
                for hh in range(nnh):
                    s_ = P[ob1 + hh]
                    for j in range(nx):
                        s_ += P[oW1 + hh * nin + j] * xc[j]
                    for j in range(NY):
                        s_ += P[oW1 + hh * nin + nx + j] * yv[j]
                    for j in range(NE):
                        s_ += P[oW1 + hh * nin + nx + NY + j] * ev[j]
                    hbuf[hh] = math.tanh(s_)
                for o in range(NU):
                    s_ = P[ob2 + o]
                    for hh in range(nnh):
                        s_ += P[oW2 + o * nnh + hh] * hbuf[hh]
                    ucmd[o] += s_
            # adaptive narrow-band block: phasor LMS at the external (tracked) frequency
            if afc_on:
                f_ = ev[2]
                fmax_ = afc_f0 + afc_df * (afc_nf - 1)
                if f_ < afc_f0:
                    f_ = afc_f0
                elif f_ > fmax_:
                    f_ = fmax_
                afph += 2.0 * math.pi * f_ * Tc
                if afph > math.pi:
                    afph -= 2.0 * math.pi
                c_ = math.cos(afph); s_ = math.sin(afph)
                E0r = 2.0 * epsv[0] * c_; E0i = -2.0 * epsv[0] * s_
                E1r = 2.0 * epsv[1] * c_; E1i = -2.0 * epsv[1] * s_
                xg = (f_ - afc_f0) / afc_df
                j0 = int(math.floor(xg))
                if j0 > afc_nf - 2:
                    j0 = afc_nf - 2
                if j0 < 0:
                    j0 = 0
                wg = xg - j0
                for i in range(9):
                    gtab[i] = (1.0 - wg) * P[afc_ot + 9 * j0 + i] + wg * P[afc_ot + 9 * (j0 + 1) + i]
                d0r = gtab[0] * E0r - gtab[1] * E0i + gtab[2] * E1r - gtab[3] * E1i
                d0i = gtab[0] * E0i + gtab[1] * E0r + gtab[2] * E1i + gtab[3] * E1r
                d1r = gtab[4] * E0r - gtab[5] * E0i + gtab[6] * E1r - gtab[7] * E1i
                d1i = gtab[4] * E0i + gtab[5] * E0r + gtab[6] * E1i + gtab[7] * E1r
                afU[0] = (1.0 - afc_leak) * afU[0] - afc_mu * d0r
                afU[1] = (1.0 - afc_leak) * afU[1] - afc_mu * d0i
                afU[2] = (1.0 - afc_leak) * afU[2] - afc_mu * d1r
                afU[3] = (1.0 - afc_leak) * afU[3] - afc_mu * d1i
                umx = min(afc_umax, gtab[8]) if gtab[8] > 0.0 else afc_umax
                for i in range(2):
                    mg = math.hypot(afU[2 * i], afU[2 * i + 1])
                    if mg > umx and mg > 0.0:
                        afU[2 * i] *= umx / mg
                        afU[2 * i + 1] *= umx / mg
                gg = 1.0
                if P[I_afc_gate] > 0.5:           # scale by the tracker's authority (external input e3, 0..1)
                    gg = min(1.0, max(0.0, ev[3]))
                ucmd[afc_o1] += gg * (afU[0] * c_ - afU[1] * s_)
                ucmd[afc_o2] += gg * (afU[2] * c_ - afU[3] * s_)
            for o in range(NU):
                if ul[o] > 0.0:
                    if ucmd[o] > ul[o]:
                        ucmd[o] = ul[o]
                    elif ucmd[o] < -ul[o]:
                        ucmd[o] = -ul[o]
                uapp[o] = ucmd[o]
            # linear block state update with the applied (clipped) commands
            for i in range(nx):
                s_ = 0.0
                for j in range(nx):
                    s_ += P[oA + i * nx + j] * xc[j]
                for j in range(NY):
                    s_ += P[oB + i * NI + j] * yv[j]
                for j in range(NE):
                    s_ += P[oB + i * NI + NY + j] * ev[j]
                for j in range(NU):
                    s_ += P[oB + i * NI + NY + NE + j] * uapp[j]
                xn[i] = s_
            for i in range(nx):
                xc[i] = xn[i]
            tick += 1
        for j in range(5):
            Q[j] = 0.0
        # grip body: the pen, or the sleeve when there is one (extension)
        if slv_on:
            gp = ps_; gv = vs_; gb = bs_; gbd = bds_; Qg = Qs
            for j in range(5):
                Qs[j] = 0.0
        else:
            gp = p; gv = v; gb = b; gbd = bd; Qg = Q
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
            dx = (gp[0] - hx) + z * (gb[0] * t1[0] + gb[1] * t2[0]) - ps * wx
            dy = (gp[1] - hy) + z * (gb[0] * t1[1] + gb[1] * t2[1]) - ps * wy
            dz = (gp[2] - hz) + z * (gb[0] * t1[2] + gb[1] * t2[2]) - ps * wz
            ex = (gv[0] - hvx) + z * (gbd[0] * t1[0] + gbd[1] * t2[0]) - psd * wx
            ey = (gv[1] - hvy) + z * (gbd[0] * t1[1] + gbd[1] * t2[1]) - psd * wy
            ez = (gv[2] - hvz) + z * (gbd[0] * t1[2] + gbd[1] * t2[2]) - psd * wz
            # K = kt (I - a a^T) + kx a a^T
            da = dx * a[0] + dy * a[1] + dz * a[2]
            ea = ex * a[0] + ey * a[1] + ez * a[2]
            fx = -(kt * (dx - da * a[0]) + kx * da * a[0]) - bg * (kt * (ex - ea * a[0]) + kx * ea * a[0])
            fy = -(kt * (dy - da * a[1]) + kx * da * a[1]) - bg * (kt * (ey - ea * a[1]) + kx * ea * a[1])
            fz = -(kt * (dz - da * a[2]) + kx * da * a[2]) - bg * (kt * (ez - ea * a[2]) + kx * ea * a[2])
            Fg[0] += fx; Fg[1] += fy; Fg[2] += fz
            Qg[0] += fx; Qg[1] += fy; Qg[2] += fz
            Qg[3] += z * (fx * t1[0] + fy * t1[1] + fz * t1[2])
            Qg[4] += z * (fx * t2[0] + fy * t2[1] + fz * t2[2])
        # tilt stiffness of the pads relative to the hand frame
        Qg[3] += -kap * (gb[0] - bh1) - bg * kap * (gbd[0] - bhd1)
        Qg[4] += -kap * (gb[1] - bh2) - bg * kap * (gbd[1] - bhd2)
        # push force at the ball centre (external, as model P1); with a sleeve it can pass through the pivot
        if slv_on and push_slv:
            Qs[2] += -fpush[k]
        else:
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
                        if ctl_on:
                            fi += ucmd[i]
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
                tcmd = uff[k, i]
                if ctl_on:
                    tcmd = tcmd + ucmd[i]
                rc = tcmd / (2.0 * H * max(cd, 0.2)) - dl[i] / tau_c
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
        # ---------------- actuated pivot between the sleeve and the pen (extension)
        if slv_on:
            dbx = b[0] - bs_[0]; dby = b[1] - bs_[1]; dbdx = bd[0] - bds_[0]; dbdy = bd[1] - bds_[1]
            for j in range(3):
                dvec[j] = (p[j] - ps_[j]) + zp_ * (dbx * t1[j] + dby * t2[j])
                dvel[j] = (v[j] - vs_[j]) + zp_ * (dbdx * t1[j] + dbdy * t2[j])
            dpa = dvec[0] * a[0] + dvec[1] * a[1] + dvec[2] * a[2]
            dva = dvel[0] * a[0] + dvel[1] * a[1] + dvel[2] * a[2]
            for j in range(3):
                fpv[j] = (-(kpt * (dvec[j] - dpa * a[j]) + kpa * dpa * a[j])
                          - bpv * (kpt * (dvel[j] - dva * a[j]) + kpa * dva * a[j]))
            fp_t1 = fpv[0] * t1[0] + fpv[1] * t1[1] + fpv[2] * t1[2]
            fp_t2 = fpv[0] * t2[0] + fpv[1] * t2[1] + fpv[2] * t2[2]
            for j in range(3):
                Q[j] += fpv[j]
                Qs[j] -= fpv[j]
            Q[3] += zp_ * fp_t1; Q[4] += zp_ * fp_t2
            Qs[3] -= zp_ * fp_t1; Qs[4] -= zp_ * fp_t2
            # bending stiffness of the pivot flexure
            tb1 = -kpr * dbx - bpv * kpr * dbdx
            tb2 = -kpr * dby - bpv * kpr * dbdy
            Q[3] += tb1; Q[4] += tb2; Qs[3] -= tb1; Qs[4] -= tb2
            # 2-axis actuator at z_a on the transverse relative displacement
            for i in range(2):
                if i == 0:
                    di = ((p[0] - ps_[0]) * t1[0] + (p[1] - ps_[1]) * t1[1] + (p[2] - ps_[2]) * t1[2]) + za_ * dbx
                    dvi = ((v[0] - vs_[0]) * t1[0] + (v[1] - vs_[1]) * t1[1] + (v[2] - vs_[2]) * t1[2]) + za_ * dbdx
                else:
                    di = ((p[0] - ps_[0]) * t2[0] + (p[1] - ps_[1]) * t2[1] + (p[2] - ps_[2]) * t2[2]) + za_ * dby
                    dvi = ((v[0] - vs_[0]) * t2[0] + (v[1] - vs_[1]) * t2[1] + (v[2] - vs_[2]) * t2[2]) + za_ * dbdy
                cmd = 0.0
                if ctl_on:
                    cmd += ucmd[3 + i]
                if ncol >= 9:
                    cmd += uff[k, 7 + i]
                if act_ty == 0:
                    if cmd > afm:
                        cmd = afm
                    elif cmd < -afm:
                        cmd = -afm
                    fa = cmd + apre[i] - kas * di - cas * dvi
                    lim = astr
                else:
                    if cmd > astr:
                        cmd = astr
                    elif cmd < -astr:
                        cmd = -astr
                    fa = kas * (cmd - di) - cas * dvi + apre[i]
                    lim = 1.5 * astr
                if di > lim:
                    fa += -k_astop * (di - lim)
                elif di < -lim:
                    fa += -k_astop * (di + lim)
                pdel[i] = di
                pfor[i] = fa
                if i == 0:
                    for j in range(3):
                        Q[j] += fa * t1[j]
                        Qs[j] -= fa * t1[j]
                    Q[3] += za_ * fa; Qs[3] -= za_ * fa
                else:
                    for j in range(3):
                        Q[j] += fa * t2[j]
                        Qs[j] -= fa * t2[j]
                    Q[4] += za_ * fa; Qs[4] -= za_ * fa
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
        if slv_on:
            for i in range(5):
                s_ = 0.0
                for j in range(5):
                    s_ += Si[i, j] * Qs[j]
                accs[i] = s_
            for j in range(3):
                vs_[j] += accs[j] * dt
                ps_[j] += vs_[j] * dt
            bds_[0] += accs[3] * dt; bds_[1] += accs[4] * dt
            bs_[0] += bds_[0] * dt; bs_[1] += bds_[1] * dt
        nn_prev = Nn
        # ---------------- nib stage (kinematic oracle as model P1: 2 kHz reference, contact-gated authority)
        if stage_on:
            if k % sdec == 0:
                in_c = 1.0 if Nn > 0.0 else 0.0
                g_eff = g_eff + alpha_a * (in_c - g_eff)
                if stg_src == 0:
                    ex_ = p[0] - clean[k, 0]; ey_ = p[1] - clean[k, 1]
                elif stg_src == 1:
                    ex_ = clean[k, 0]; ey_ = clean[k, 1]          # external disturbance estimate (extension)
                else:
                    ex_ = ucmd[5]; ey_ = ucmd[6]                  # in-loop controller output (extension)
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
            if slv_on:
                r[R_sx] = ps_[0]; r[R_sy] = ps_[1]; r[R_sz] = ps_[2]; r[R_sb1] = bs_[0]; r[R_sb2] = bs_[1]
                r[R_pd1] = pdel[0]; r[R_pd2] = pdel[1]; r[R_pf1] = pfor[0]; r[R_pf2] = pfor[1]
                r[R_fp1] = fpv[0] * t1[0] + fpv[1] * t1[1] + fpv[2] * t1[2]
                r[R_fp2] = fpv[0] * t2[0] + fpv[1] * t2[1] + fpv[2] * t2[2]
                r[R_fpa] = fpv[0] * a[0] + fpv[1] * a[1] + fpv[2] * a[2]
            if ctl_on:
                r[R_u1] = ucmd[0]; r[R_u2] = ucmd[1]; r[R_u3] = ucmd[2]; r[R_u4] = ucmd[3]; r[R_u5] = ucmd[4]
                r[R_u6] = ucmd[5]; r[R_u7] = ucmd[6]; r[R_ia1] = yv[0]; r[R_ia2] = yv[1]
                r[R_eps1] = epsv[0]; r[R_eps2] = epsv[1]
                r[R_afa1] = math.hypot(afU[0], afU[1]); r[R_afa2] = math.hypot(afU[2], afU[3])
            rec_i += 1
    return rec_i
