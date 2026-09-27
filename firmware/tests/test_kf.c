/*
 * test_kf.c - estimators against golden vectors from the numba reference,
 * and replays of the real simulator's closed-loop runs through the firmware
 * stage tick.
 */
#include <math.h>
#include <string.h>

#include "control.h"
#include "estimator_bpf.h"
#include "estimator_kf.h"
#include "guided.h"
#include "tr.h"
#include "vec.h"

/* Q entries in double precision from (qj, qt, Ts), as the generator does */
static void make_q(double qj, double qt, double Ts, float q[KFQ_N])
{
    const double T2 = Ts * Ts, T3 = T2 * Ts, T4 = T3 * Ts, T5 = T4 * Ts;
    q[KFQ_00] = (float)(qj * T5 / 20.0);
    q[KFQ_01] = (float)(qj * T4 / 8.0);
    q[KFQ_02] = (float)(qj * T3 / 6.0);
    q[KFQ_11] = (float)(qj * T3 / 3.0);
    q[KFQ_12] = (float)(qj * T2 / 2.0);
    q[KFQ_22] = (float)(qj * Ts);
    q[KFQ_OSC] = (float)(qt * Ts);
}

void test_kf_step_golden(void)
{
    vec_t v;
    CHECK(vec_load("kf_step.vec", &v));
    if (v.rows == 0u) {
        return;
    }
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    float q[KFQ_N];
    make_q(PEN_BAL_KF_QJ, PEN_BAL_KF_QT, 5e-4, q);
    const int cx = vec_col(&v, "x0"), cP = vec_col(&v, "P00"), cy = vec_col(&v, "y"), cw = vec_col(&v, "w");
    const int cxo = vec_col(&v, "xo0"), cPo = vec_col(&v, "Po00"), ci = vec_col(&v, "innov"), cS = vec_col(&v, "S");
    double ex = 0.0, eP = 0.0, ei = 0.0, eS = 0.0;
    for (uint32_t r = 0; r < v.rows; r++) {
        float x[KF_NX], P[KF_NX][KF_NX];
        for (int i = 0; i < KF_NX; i++) {
            x[i] = vec_at(&v, r, cx + i);
            for (int j = 0; j < KF_NX; j++) {
                P[i][j] = vec_at(&v, r, cP + KF_NX * i + j);
            }
        }
        float innov, S;
        kf_step5(x, P, vec_at(&v, r, cy), PEN_TS_STAGE, vec_at(&v, r, cw), p.kf_rdamp, q, p.kf_r, &innov, &S);
        /* errors normalised by the posterior standard deviations (float32-appropriate) */
        for (int i = 0; i < KF_NX; i++) {
            const double sdi = sqrt(fabs((double)vec_at(&v, r, cPo + KF_NX * i + i)));
            const double e = fabs((double)x[i] - (double)vec_at(&v, r, cxo + i)) / sdi;
            ex = e > ex ? e : ex;
            for (int j = 0; j < KF_NX; j++) {
                const double sdj = sqrt(fabs((double)vec_at(&v, r, cPo + KF_NX * j + j)));
                const double ep = fabs((double)P[i][j] - (double)vec_at(&v, r, cPo + KF_NX * i + j)) / (sdi * sdj);
                eP = ep > eP ? ep : eP;
            }
        }
        const double Sref = (double)vec_at(&v, r, cS);
        const double e_i = fabs((double)innov - (double)vec_at(&v, r, ci)) / sqrt(Sref);
        const double e_s = fabs((double)S - Sref) / Sref;
        ei = e_i > ei ? e_i : ei;
        eS = e_s > eS ? e_s : eS;
    }
    CHECK(ex < 1e-3);
    CHECK(eP < 1e-4);
    CHECK(ei < 1e-3);
    CHECK(eS < 1e-4);
    tr_log("_kf_step golden (%u realistic states): max |dx|/sd %.2g, |dP|/(sd sd) %.2g, |d innov|/sqrt(S) %.2g, "
           "|dS|/S %.2g", (unsigned)v.rows, ex, eP, ei, eS);
}

typedef struct {
    double dhat, w, conf, nis;
} kf_err_t;

static bool run_kf_seq(const char *file, pen_profile_t prof, kf_err_t *err, kf_est_t *final_state)
{
    vec_t v;
    if (!vec_load(file, &v)) {
        return false;
    }
    pen_ctrl_params_t p;
    pen_params_default(&p, prof);
    kf_est_t e;
    kf_est_init(&e, &p);
    const int c0 = vec_col(&v, "ph0"), c1 = vec_col(&v, "ph1"), cv = vec_col(&v, "valid");
    const int cd0 = vec_col(&v, "dhat0"), cd1 = vec_col(&v, "dhat1"), cw = vec_col(&v, "w");
    const int cc = vec_col(&v, "conf"), cn = vec_col(&v, "nis_f");
    memset(err, 0, sizeof(*err));
    bool vprev = false;
    for (uint32_t r = 0; r < v.rows; r++) {
        const float ph[2] = {vec_at(&v, r, c0), vec_at(&v, r, c1)};
        const bool valid = vec_at(&v, r, cv) > 0.5f;
        if (valid && !vprev) {
            e.need_reinit = true;
        }
        vprev = valid;
        kf_est_tick(&e, &p, ph, valid);
        const double d0 = fabs((double)e.dhat[0] - (double)vec_at(&v, r, cd0));
        const double d1 = fabs((double)e.dhat[1] - (double)vec_at(&v, r, cd1));
        const double dw = fabs((double)e.w - (double)vec_at(&v, r, cw)) / (double)vec_at(&v, r, cw);
        const double dc = fabs((double)e.conf - (double)vec_at(&v, r, cc));
        const double dn = fabs((double)e.nis_f - (double)vec_at(&v, r, cn)) / fabs((double)vec_at(&v, r, cn));
        err->dhat = fmax(err->dhat, fmax(d0, d1));
        err->w = fmax(err->w, dw);
        err->conf = fmax(err->conf, dc);
        err->nis = fmax(err->nis, dn);
    }
    if (final_state != NULL) {
        *final_state = e;
    }
    return true;
}

void test_kf_estimator_sequence_golden(void)
{
    kf_err_t e;
    CHECK(run_kf_seq("kf_seq_bal.vec", PEN_PROFILE_BALANCED, &e, NULL));
    CHECK(e.dhat < 0.1e-6);    /* 0.1 um: 1/30 of the optical noise */
    CHECK(e.w < 1e-4);
    CHECK(e.conf < 2e-3);
    CHECK(e.nis < 2e-3);
    tr_log("balanced: 6000 ticks (tremor 8->10 Hz, dropout): max |d dhat| %.3g m, rel |d w| %.2g, |d conf| %.2g, "
           "rel |d nis| %.2g", e.dhat, e.w, e.conf, e.nis);
    CHECK(run_kf_seq("kf_seq_asr.vec", PEN_PROFILE_ASSERTIVE, &e, NULL));
    CHECK(e.dhat < 0.1e-6);
    CHECK(e.w < 1e-4);
    CHECK(e.conf < 2e-3);
    CHECK(e.nis < 2e-3);
    tr_log("assertive: max |d dhat| %.3g m, rel |d w| %.2g, |d conf| %.2g, rel |d nis| %.2g", e.dhat, e.w, e.conf,
           e.nis);
}

void test_kf_float32_covariance_health(void)
{
    /* after the long run the float32 covariance must stay symmetric positive
     * definite (the reference omits the Joseph form) */
    kf_err_t e;
    kf_est_t st;
    CHECK(run_kf_seq("kf_seq_bal.vec", PEN_PROFILE_BALANCED, &e, &st));
    bool ok = true;
    for (int ax = 0; ax < 2; ax++) {
        /* Cholesky in double of the float32 matrix */
        double L[KF_NX][KF_NX];
        memset(L, 0, sizeof(L));
        for (int i = 0; i < KF_NX; i++) {
            for (int j = 0; j <= i; j++) {
                double s = (double)st.P[ax][i][j];
                for (int k = 0; k < j; k++) {
                    s -= L[i][k] * L[j][k];
                }
                if (i == j) {
                    if (!(s > 0.0)) {
                        ok = false;
                        s = 1e-300;
                    }
                    L[i][i] = sqrt(s);
                } else {
                    L[i][j] = s / L[j][j];
                }
            }
            for (int j = 0; j < KF_NX; j++) {
                if (st.P[ax][i][j] != st.P[ax][j][i]) {
                    ok = false;
                }
            }
        }
    }
    CHECK(ok);
    tr_log("float32 P after 6000 ticks: symmetric and positive definite (Cholesky) on both axes: %s", ok ? "yes" : "NO");
}

void test_bpf_estimator_golden(void)
{
    vec_t v;
    CHECK(vec_load("bpf_seq.vec", &v));
    if (v.rows == 0u) {
        return;
    }
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    bpf_est_t e;
    bpf_est_init(&e);
    const int c0 = vec_col(&v, "ph0"), c1 = vec_col(&v, "ph1"), cv = vec_col(&v, "valid");
    const int cd0 = vec_col(&v, "dhat0"), cd1 = vec_col(&v, "dhat1");
    double err = 0.0;
    bool vprev = false;
    for (uint32_t r = 0; r < v.rows; r++) {
        const float ph[2] = {vec_at(&v, r, c0), vec_at(&v, r, c1)};
        const bool valid = vec_at(&v, r, cv) > 0.5f;
        if (valid && !vprev) {
            e.need_reinit = true;
        }
        vprev = valid;
        bpf_est_tick(&e, &p, ph, valid);
        err = fmax(err, fmax(fabs((double)e.dhat[0] - (double)vec_at(&v, r, cd0)),
                             fabs((double)e.dhat[1] - (double)vec_at(&v, r, cd1))));
    }
    /* the high-pass runs on absolute page position (mm scale) in float32: the
     * DF2T states carry the full input amplitude, so the error scales with
     * |p| x eps / (1 - pole radius); 0.5 um is 1/6 of the optical noise */
    CHECK(err < 0.5e-6);
    tr_log("band-pass estimator vs mode==2 transcription: max |d dhat| %.3g m over %u ticks", err, (unsigned)v.rows);
}

/* ------------------------------------------------------------------ replay of the simulator */
typedef struct {
    double dhat, west, g, qr, iref;
    uint32_t n_iref_big;
} replay_err_t;

static bool replay(const char *file, replay_err_t *er, uint32_t *rows, bool local_origin)
{
    vec_t v;
    if (!vec_load(file, &v)) {
        return false;
    }
    ctrl_t c;
    ctrl_init(&c, PEN_PROFILE_BALANCED);
    c.local_origin = local_origin;
    const int cth = vec_col(&v, "theta"), cph = vec_col(&v, "phi"), crh = vec_col(&v, "rho"), cg = vec_col(&v, "gamma");
    const int cfa = vec_col(&v, "ff_accel"), cfc = vec_col(&v, "ff_contact"), ce = vec_col(&v, "est");
    const int chz = vec_col(&v, "horizon");
    c.prm.gamma = vec_at(&v, 0, cg);
    c.prm.ff_accel = vec_at(&v, 0, cfa);
    c.prm.ff_contact = vec_at(&v, 0, cfc);
    CHECK_CLOSE(vec_at(&v, 0, chz), c.prm.horizon, 1e-9, 1e-6);
    const pen_est_t est = (pen_est_t)(int)vec_at(&v, 0, ce);
    const int cq0 = vec_col(&v, "qm0"), cq1 = vec_col(&v, "qm1"), cf = vec_col(&v, "fa");
    const int cp0 = vec_col(&v, "ph0"), cp1 = vec_col(&v, "ph1"), cv = vec_col(&v, "valid");
    const int cd0 = vec_col(&v, "dhat0"), cd1 = vec_col(&v, "dhat1"), cw = vec_col(&v, "west"), cge = vec_col(&v, "g_eff");
    const int cr0 = vec_col(&v, "qr0"), cr1 = vec_col(&v, "qr1"), ci0 = vec_col(&v, "iref0"), ci1 = vec_col(&v, "iref1");
    memset(er, 0, sizeof(*er));
    for (uint32_t r = 0; r < v.rows; r++) {
        ctrl_in_t in;
        memset(&in, 0, sizeof(in));
        in.qm[0] = vec_at(&v, r, cq0);
        in.qm[1] = vec_at(&v, r, cq1);
        in.fa = vec_at(&v, r, cf);
        in.ph[0] = vec_at(&v, r, cp0);
        in.ph[1] = vec_at(&v, r, cp1);
        in.opt_valid = vec_at(&v, r, cv) > 0.5f;
        in.theta = vec_at(&v, r, cth);
        in.phi = vec_at(&v, r, cph);
        in.rho = vec_at(&v, r, crh);
        in.g_cap = 1.0f;
        in.i_max = PEN_I_MAX;
        in.est = est;
        in.servo_on = true;
        ctrl_tick(&c, &in);
        const float *dh = (est == PEN_EST_BPF) ? c.bpf.dhat : c.kf.dhat;
        er->dhat = fmax(er->dhat, fmax(fabs((double)dh[0] - (double)vec_at(&v, r, cd0)),
                                       fabs((double)dh[1] - (double)vec_at(&v, r, cd1))));
        if (est == PEN_EST_KF) {
            er->west = fmax(er->west, fabs((double)kf_est_freq_hz(&c.kf) - (double)vec_at(&v, r, cw)));
        }
        er->g = fmax(er->g, fabs((double)c.g_eff - (double)vec_at(&v, r, cge)));
        er->qr = fmax(er->qr, fmax(fabs((double)c.servo.qr[0] - (double)vec_at(&v, r, cr0)),
                                   fabs((double)c.servo.qr[1] - (double)vec_at(&v, r, cr1))));
        const double di = fmax(fabs((double)c.servo.iref[0] - (double)vec_at(&v, r, ci0)),
                               fabs((double)c.servo.iref[1] - (double)vec_at(&v, r, ci1)));
        er->iref = fmax(er->iref, di);
        if (di > 1e-4) {
            er->n_iref_big++;
        }
    }
    *rows = v.rows;
    return true;
}

/* Tolerances. Kalman path: float32 vs float64 differences stay far below the
 * sensing noise (optical 3 um, current 0.55 mA rms). Band-pass path: the
 * 6 Hz high-pass runs on page position in float32; its DF2T states carry the
 * full input, so rounding of order eps |p| / (1 - pole radius) reaches
 * ~0.3 um and the servo's derivative (Kd/Ts) turns that into ~1 mA; the
 * standalone band-pass test shows the same magnitude against its float64
 * transcription, so the servo itself is not the source. */
static void check_replay(const char *file, const char *label, bool local_origin, double tol_d, double tol_i)
{
    replay_err_t e;
    uint32_t rows = 0;
    CHECK(replay(file, &e, &rows, local_origin));
    CHECK(e.dhat < tol_d);        /* m */
    CHECK(e.west < 1e-3);         /* Hz */
    CHECK(e.g < 1e-4);
    CHECK(e.qr < tol_d);          /* m */
    CHECK(e.iref < tol_i);        /* A */
    tr_log("%s: %u ticks vs core.simulate(): max |d dhat| %.3g m, |d f_est| %.3g Hz, |d g| %.3g, |d q_r| %.3g m, "
           "|d i_ref| %.3g A", label, (unsigned)rows, e.dhat, e.west, e.g, e.qr, e.iref);
}

void test_replay_sim_kf(void)
{
    check_replay("replay_kf.vec", "Kalman (balanced), local origin on (shift invariance)", true, 0.2e-6, 1e-4);
    check_replay("replay_kf.vec", "Kalman (balanced), local origin off", false, 0.2e-6, 1e-4);
}
void test_replay_sim_bpf(void) { check_replay("replay_bpf.vec", "band-pass, local origin off (as simulator)", false, 1e-6, 5e-3); }
void test_replay_sim_ffc(void)
{
    check_replay("replay_ffc.vec", "Kalman + contact FF (bench option)", true, 0.2e-6, 1e-4);
}

void test_bpf_reacquisition_transient(void)
{
    /* pen re-acquired 20 mm from the page origin with a 0.3 mm 8 Hz tremor:
     * the simulator's band-pass (zeroed states, absolute input) produces a
     * step transient of the full coordinate; with the local origin it does not */
    double peak[2] = {0.0, 0.0};
    for (int mode = 0; mode < 2; mode++) {
        ctrl_t c;
        ctrl_init(&c, PEN_PROFILE_BALANCED);
        c.local_origin = (mode == 1);
        for (int k = 0; k < 2000; k++) {
            const double t = (double)k * 5e-4;
            ctrl_in_t in;
            memset(&in, 0, sizeof(in));
            in.qm[0] = 0.0f;
            in.fa = 1.0f;
            in.ph[0] = (float)(0.020 + 3e-4 * sin(2.0 * 3.141592653589793 * 8.0 * t));
            in.ph[1] = (float)(0.005);
            in.opt_valid = k >= 200;
            in.theta = 0.8726646f;
            in.g_cap = 1.0f;
            in.i_max = PEN_I_MAX;
            in.est = PEN_EST_BPF;
            in.servo_on = true;
            ctrl_tick(&c, &in);
            if (k >= 200 && k < 400) {
                const double d = hypot((double)c.bpf.dhat[0], (double)c.bpf.dhat[1]);
                peak[mode] = d > peak[mode] ? d : peak[mode];
            }
        }
    }
    CHECK(peak[0] > 5e-3);     /* simulator behaviour: ~20 mm-scale false estimate */
    CHECK(peak[1] < 0.6e-3);   /* local origin: only the tremor (0.3 mm, gain-compensated) */
    tr_log("band-pass after re-acquisition at 20 mm: peak |dhat| %.2f mm (simulator scheme) vs %.3f mm (local origin)",
           peak[0] * 1e3, peak[1] * 1e3);
}

void test_guided_tracks_template(void)
{
    static float tmpl[500][2];
    for (int k = 0; k < 500; k++) {
        tmpl[k][0] = 1e-5f * (float)k;   /* 5 mm straight line at 2 kHz */
        tmpl[k][1] = 0.0f;
    }
    guided_t gd;
    guided_init(&gd, (const float (*)[2])tmpl, 500u);
    /* pen 0.2 mm off the line, moving along it */
    for (int k = 0; k < 300; k++) {
        const float ph[2] = {1e-5f * (float)k + 2e-6f, 2e-4f};
        guided_tick(&gd, ph, true, true, PEN_Q_LIM);
    }
    CHECK(gd.active);
    CHECK(gd.prog >= 298u && gd.prog <= 300u);
    CHECK_CLOSE(gd.corr[1], -2e-4, 1e-9, 0.0);
    CHECK(gd.conf == 1.0f);
    /* outside the capture radius (2 q_lim) authority is released */
    const float far[2] = {3.0e-3f, 2.0e-3f};
    guided_tick(&gd, far, true, true, PEN_Q_LIM);
    CHECK(gd.conf == 0.0f);
    /* lift: re-acquisition window */
    guided_tick(&gd, far, true, false, PEN_Q_LIM);
    CHECK(gd.reacq);
}
