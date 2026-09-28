"""Index layout of the pencil simulator's packed parameter vector and recorded channels.
All quantities SI; stage quantities are tip-equivalent (referred to the ball centre)."""
NAMES = [
    # integration
    "dt", "n_steps", "rec_decim",
    # orientation
    "theta", "phi", "rho",
    # stage per axis (nib-referred): inertia, bender stiffness, parasitic stiffness, damping, housing coupling
    "m_eq", "k_b", "k_par", "c_st", "m_cpl", "g_V", "V_rail", "L_piv",
    "q_stop", "k_stop", "c_stop", "lock_stage",
    # hysteresis (Bouc-Wen on the normalised drive u = (V - V_rail/2)/(V_rail/2))
    "bw_on", "bw_alpha", "bw_beta", "bw_gamma", "bw_hsat",
    # piezo driver: first-order lag, slew limit, driven capacitance per axis, charge recovery
    "drv_tau", "drv_slew", "C_axis", "eta_c",
    # axial (spring-loaded refill): mass, spring rate, spring force at s = 0, damping, stops, bushing friction
    "m_ax", "k_sp", "F_sp0", "c_ax", "s_min", "s_max", "mu_b", "bear_fac", "v_b", "lock_axial", "s_init",
    # housing + two-stage hand
    "M_t", "K_hxy", "C_hxy", "K_hz", "C_hz", "z0", "M_hand", "k_arm", "b_arm",
    # nib-paper contact + LuGre (normalised by N)
    "k_p", "c_p", "r_b", "mu_k", "mu_s", "v_s", "sigma0", "sigma1", "sigma2",
    # skid-paper contact + LuGre; ring geometry
    "skid_on", "k_sk", "c_sk", "mu_sk", "mus_sk", "vs_sk", "sigma0_sk", "p_nom", "r_ring",
    # sensors
    "hall_noise", "hall_delay", "opt_decim", "opt_delay", "opt_noise", "opt_lift_max",
    "imu_decim", "imu_delay", "imu_noise", "imu_bias_x", "imu_bias_y",
    "ax_decim", "ax_delay", "ax_noise", "contact_thr",
    # anti-aliasing low-pass on the housing acceleration (4th-order Butterworth): the recorded aH channels
    # always pass through it; the internal IMU uses it only if imu_aa > 0.5 (legacy P1.0: raw samples)
    "acc_aa_hz", "imu_aa",
    # controller: outer (estimator) and inner (piezo servo) rates, gains, limits
    "mode", "stage_decim", "servo_decim", "Ki", "Kp", "Kd", "d_filt", "ff_ref", "ff_bias", "F_bias0", "F_bias1",
    "g_assist", "q_lim", "q_taper", "slew", "authority_tau", "horizon",
    # Kalman intent + oscillator (same as sim/pensim/core.py mode kfosc)
    "kf_qj", "kf_qt", "kf_r", "kf_w0", "kf_rdamp", "kf_wgain", "kf_wmin", "kf_wmax", "conf_nis_hi",
    "f_gate", "f_gate_width", "gamma_acc",
    # verification hooks
    "q_init", "F_test0", "F_test1", "V_fixed", "require_contact",
    # touchdown / lift feed-forward (opt/touchdown; appended, every entry 0 = off, so default runs are unchanged):
    # kinematic law q_ff = td_gain sin(th) cos(th) (td_sref - s_h) (cos rho, -sin rho), s_h = s_meas - td_kappa cot(th) q_meas,
    # predicted td_lead ahead through a td_lp low-pass; td_pre pre-positions the stage while the refill rests on its stop;
    # td_dz dead zone; td_prio travel priority (0 shared, 1 feed-forward first, 2 tremor first); td_bias 1 switches the
    # static contact-load bias at once on the feed-forward's contact state (td_kl its gain), detected from the slide
    # (td_det_s above the stop) and from the Hall error along the load direction (td_det_e); td_hold debounce time;
    # td_vtd assumed descent speed that bridges the axial sensor's latency after a Hall-detected touchdown (0: none);
    # td_handover 1: when the bias switches, the servo integrator hands over the load share it already carries
    "td_on", "td_gain", "td_kappa", "td_sref", "td_lead", "td_lp", "td_pre", "td_dz", "td_prio",
    "td_bias", "td_kl", "td_det_s", "td_det_e", "td_hold", "td_vtd", "td_handover",
]
IDX = {n: i for i, n in enumerate(NAMES)}
NP = len(NAMES)

MODES = {"locked": 0, "neutral": 1, "kfosc": 3, "oracle": 4, "open": 5, "guided": 6, "external": 7}

REC = [
    "t", "pHx", "pHy", "pHz", "q1", "q2", "qr1", "qr2", "s",
    "Nn", "fnx", "fny", "Ns", "fsx", "fsy", "Cx", "Cy", "Cz",
    "V1", "V2", "Fa1", "Fa2", "contact", "skid_contact", "dhx", "dhy", "conf", "vsat", "stop",
    "PrailB", "PrailR", "Fhx", "Fhy", "Fhz", "west", "i1", "i2", "incontact",
    "aHx", "aHy", "aHz",   # true housing acceleration (page frame) after the acc_aa_hz anti-aliasing low-pass
    # touchdown / lift feed-forward (appended; zero when td_on = 0): stage command of the feed-forward (housing axes),
    # its estimate of the housing-induced slide, and its contact state (0 air, 1 contact)
    "qff1", "qff2", "td_sh", "td_state",
]
RIDX = {n: i for i, n in enumerate(REC)}
NREC = len(REC)
