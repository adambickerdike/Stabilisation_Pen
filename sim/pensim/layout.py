"""Index layout of the packed parameter vector passed to the compiled core.

Keeping names in one list avoids silent index errors between Python and numba.
All quantities SI.  'tip-equivalent' quantities are referred to the ball centre.
"""
NAMES = [
    # integration
    "dt", "n_steps", "rec_decim",
    # orientation (constant within a run)
    "theta", "phi", "rho",
    # stage (tip-equivalent)
    "m_eq", "k_tip", "c_tip", "m_couple", "m_mov", "cm_factor", "L1",
    "q_stop", "k_stop", "c_stop",
    # axial suspension
    "m_ax", "k_ax", "c_ax", "F_pre", "s_max",
    # housing + hand (two-stage: barrel -(grip k1,b1)- hand mass M -(arm k2,b2)- imposed path)
    "m_H", "K_hxy", "C_hxy", "K_hz", "C_hz", "z0", "M_hand", "k_arm", "b_arm",
    # paper contact and friction (LuGre, normalised by N)
    "k_p", "c_p", "r_b", "mu_k", "mu_s", "v_s", "sigma0", "sigma1", "sigma2",
    # actuator / electrical (per axis, values at actuator; n = lever ratio)
    "n_lever", "Kf", "R20", "Lc", "V_bus", "r_bridge", "r_shunt", "i_max", "alpha_cu", "alpha_B",
    "Rth", "Cth", "T_amb",
    # current loop
    "cur_decim", "Kp_i", "Ki_i",
    # sensors
    "hall_noise", "hall_delay", "hall_ict", "hall_ict_comp",
    "opt_decim", "opt_delay", "opt_noise", "opt_scale", "opt_lift_max",
    "imu_decim", "imu_delay", "imu_noise", "imu_bias_x", "imu_bias_y",
    "force_decim", "force_delay", "force_noise",
    # controller common
    "mode", "stage_decim", "Kp", "Kd", "Ki", "d_filt",
    "ff_contact", "ff_accel", "ff_ref", "mu_hat",
    "g_assist", "q_lim", "q_taper", "slew", "authority_tau",
    # estimator: band-pass (two biquads, coefficients b0 b1 b2 a1 a2 each)
    "bp1_b0", "bp1_b1", "bp1_b2", "bp1_a1", "bp1_a2",
    "bp2_b0", "bp2_b1", "bp2_b2", "bp2_a1", "bp2_a2",
    "bp_gain_comp", "horizon",
    # estimator: Kalman intent + oscillator
    "kf_qj", "kf_qt", "kf_r", "kf_w0", "kf_rdamp", "kf_wgain", "kf_wmin", "kf_wmax",
    "conf_nis_hi",
    # oracle preview
    "oracle_h",
    # verification hooks
    "q_init", "require_contact",
    # axial-slide compensation (ink shift s*cos(theta) along h)
    "axial_comp", "axial_comp_tau",
    # compliance-aware Jacobian: fraction of tilt-coupled axial accommodation in the suspension
    "gamma_acc",
    # frequency-gated authority (per-user calibration): cancel only when tracked f >= f_gate
    "f_gate", "f_gate_width",
    # axial suspension location: 1 = refill slides in carrier (lever arm L1 - s), 0 = whole lever slides (Rev A)
    "kappa_s",
    # fault injection: type 0 none, 1 actuator power loss (coils open), 3 stage sensor frozen; time in s
    "fail_type", "fail_time",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)

MODES = {"rigid": 0, "neutral": 1, "bpf": 2, "kfosc": 3, "oracle": 4, "unpowered": 5, "guided": 6}

# recorded channels (columns of the output array)
REC = [
    "t", "pHx", "pHy", "pHz", "q1", "q2", "qr1", "qr2", "s", "N", "fx", "fy",
    "tipx", "tipy", "i1", "i2", "V1", "V2", "contact", "dhx", "dhy", "T1", "T2",
    "Pcu", "Pbr", "Fhx", "Fhy", "Fhz", "conf", "sat_v", "stop", "west", "iref1", "iref2",
    "Fax_meas",
]
RIDX = {n: i for i, n in enumerate(REC)}
NREC = len(REC)
