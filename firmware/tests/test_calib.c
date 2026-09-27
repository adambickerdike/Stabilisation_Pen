/*
 * test_calib.c - calibration records (CRC, versioning, ranges) and the
 * tremor-frequency calibration on synthetic housing motion.
 */
#include <math.h>
#include <string.h>

#include "calib.h"
#include "control.h"
#include "jacobian.h"
#include "log_format.h"
#include "params_gen.h"
#include "state_machine.h"
#include "tr.h"

void test_calib_record_roundtrip(void)
{
    cal_user_t u, d;
    cal_user_default(&u);
    u.f0_hz = 8.2f;
    u.f_stroke_hz = 4.4f;
    u.f_gate_hz = 6.3f;
    u.g_max = 0.8f;
    u.q_lim_m = 0.5e-3f;
    u.r_n = 0.7f;
    u.flags = CAL_FLAG_SEPARABLE | CAL_FLAG_TREMOR_FOUND;
    uint8_t buf[64];
    const size_t n = cal_user_encode(&u, buf, sizeof(buf));
    CHECK(n == CAL_USER_LEN + CAL_REC_OVERHEAD);
    CHECK(le_get_u32(buf) == CAL_MAGIC && buf[0] == 'P' && buf[1] == 'C' && buf[2] == 'A' && buf[3] == 'L');
    CHECK(buf[4] == CAL_USER && le_get_u16(buf + 5) == CAL_USER_VERSION && le_get_u16(buf + 7) == CAL_USER_LEN);
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK);
    CHECK(d.f0_hz == u.f0_hz && d.f_stroke_hz == u.f_stroke_hz && d.f_gate_hz == u.f_gate_hz &&
          d.f_gate_width_hz == u.f_gate_width_hz && d.g_max == u.g_max && d.q_lim_m == u.q_lim_m &&
          d.r_n == u.r_n && d.mode_perm == u.mode_perm && d.flags == u.flags && !d.from_v1_clamped);
    /* the log snapshot body (record 0x04) is exactly the container payload */
    uint8_t pl[CAL_USER_LEN];
    CHECK(cal_user_payload(&u, pl) == CAL_USER_LEN && memcmp(pl, buf + CAL_HDR_LEN, CAL_USER_LEN) == 0);
    CHECK(cal_user_from_payload(CAL_USER_VERSION, pl, CAL_USER_LEN, &d) == CAL_OK && d.r_n == u.r_n);
    /* invalid values are never written */
    cal_user_t bad = u;
    bad.g_max = 1.5f;
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad = u;
    bad.q_lim_m = 0.7e-3f;   /* beyond the design soft limit */
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad = u;
    bad.r_n = NAN;
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad.r_n = 0.01f;   /* below the ICD range 0.02-10 */
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad.r_n = 10.5f;
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    tr_log("CAL_USER v2 (r_n = K_n/k_ax) flash record and log payload round-trip bit-exactly; r_n outside 0.02-10 "
           "and other out-of-range fields are never written");
}

/* a version-1 record (gamma at 50 deg) as written by earlier firmware */
static size_t v1_record(float gamma, uint8_t *out, size_t cap)
{
    cal_user_t u;
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 8.3f, 4.6f);
    uint8_t p[CAL_USER_LEN];
    (void)cal_user_payload(&u, p);
    le_put_f32(p + 24, gamma);
    return cal_record_encode(CAL_USER, CAL_USER_VERSION_V1, p, CAL_USER_LEN, out, cap);
}

void test_calib_user_v1_conversion(void)
{
    const double th = PEN_THETA_NOM, s2 = sin(th) * sin(th);
    uint8_t buf[64];
    cal_user_t d;
    double worst = 0.0;
    const float g1[4] = {0.05f, 0.1901f, 0.3f, 0.8f};
    for (int k = 0; k < 4; k++) {
        const size_t n = v1_record(g1[k], buf, sizeof(buf));
        CHECK(cal_user_decode(buf, n, &d) == CAL_OK && !d.from_v1_clamped);
        const double rn = (double)g1[k] / ((1.0 - (double)g1[k]) * s2);
        CHECK_CLOSE(d.r_n, rn, 0.0, 2e-6);
        /* gamma recomputed at 50 deg reproduces the stored v1 gamma */
        const double back = (double)jac_gamma(d.r_n, PEN_THETA_NOM);
        CHECK_CLOSE(back, g1[k], 1e-6, 0.0);
        worst = fmax(worst, fabs(back - (double)g1[k]));
        CHECK(d.f0_hz == 8.3f && d.mode_perm == (uint8_t)SM_PERM_DEFAULT);
    }
    /* v1 gamma outside the representable range: clamped to 0.02 / 10 and reported */
    size_t n = v1_record(0.0f, buf, sizeof(buf));
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK && d.from_v1_clamped && d.r_n == PEN_R_N_MIN);
    n = v1_record(0.95f, buf, sizeof(buf));
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK && d.from_v1_clamped && d.r_n == PEN_R_N_MAX);
    n = v1_record(1.0f, buf, sizeof(buf));
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK && d.from_v1_clamped && d.r_n == PEN_R_N_MAX);
    n = v1_record(1.5f, buf, sizeof(buf));
    CHECK(cal_user_decode(buf, n, &d) == CAL_E_RANGE);
    /* re-encoding writes version 2 */
    d.from_v1_clamped = false;
    n = v1_record(0.3f, buf, sizeof(buf));
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK);
    const size_t m = cal_user_encode(&d, buf, sizeof(buf));
    CHECK(m > 0u && le_get_u16(buf + 5) == CAL_USER_VERSION && cal_user_decode(buf, m, &d) == CAL_OK);
    tr_log("CAL_USER v1 -> v2: r_n = gamma / ((1 - gamma) sin^2 50 deg); gamma(50 deg) recomputed from r_n within "
           "%.1e for gamma 0.05-0.8; v1 gamma outside %.4f-%.3f is clamped to r_n 0.02 / 10 (flagged); re-encoded "
           "as version 2", worst, (double)jac_gamma(PEN_R_N_MIN, PEN_THETA_NOM),
           (double)jac_gamma(PEN_R_N_MAX, PEN_THETA_NOM));
}

void test_jacobian_gamma_of_theta(void)
{
    /* simulator formula (sim/pensim/model.py): gamma = Kn sin^2 / (Kn sin^2 + k_ax); J_t1 = s + gamma c^2 / s */
    const double Kn = PEN_K_HAND_NORMAL, kax = PEN_K_AX;
    CHECK_CLOSE(PEN_R_N_NOM, Kn / kax, 1e-7, 0.0);
    CHECK_CLOSE(jac_gamma(PEN_R_N_NOM, PEN_THETA_NOM), PEN_GAMMA_NOM, 1e-6, 0.0);
    const double deg[3] = {35.0, 50.0, 75.0};
    double eg = 0.0, ej = 0.0;
    for (int k = 0; k < 3; k++) {
        const double th = deg[k] * 3.141592653589793 / 180.0;
        const double s = sin(th), c = cos(th);
        const double gam = Kn * s * s / (Kn * s * s + kax);
        const double jt1 = s + gam * c * c / s;
        /* through the control tick: gamma(theta) evaluated at the Jacobian update */
        ctrl_t ct;
        ctrl_init(&ct, PEN_PROFILE_BALANCED);
        ctrl_in_t in;
        memset(&in, 0, sizeof(in));
        in.theta = (float)th;
        in.fa = PEN_F_PRE;
        in.g_cap = 1.0f;
        in.i_max = PEN_I_MAX;
        in.est = PEN_EST_KF;
        in.servo_on = true;
        ctrl_tick(&ct, &in);
        CHECK_CLOSE(jac_gamma(PEN_R_N_NOM, (float)th), gam, 1e-6, 0.0);
        CHECK_CLOSE(ct.gamma, gam, 1e-6, 0.0);
        CHECK_CLOSE(ct.jac.jt1, jt1, 0.0, 1e-6);
        eg = fmax(eg, fabs((double)ct.gamma - gam));
        ej = fmax(ej, fabs((double)ct.jac.jt1 - jt1) / jt1);
        tr_log("theta %.0f deg: gamma %.5f (simulator formula %.5f), J_t1 %.5f (%.5f)", deg[k], (double)ct.gamma, gam,
               (double)ct.jac.jt1, jt1);
    }
    tr_log("gamma(theta) and J_t1 vs the simulator formula at 35/50/75 deg: max |d gamma| %.1e, rel |d J_t1| %.1e "
           "(r_n = K_n/k_ax = %.3f)", eg, ej, (double)PEN_R_N_NOM);
}

void test_calib_record_corruption(void)
{
    cal_user_t u, d;
    cal_user_default(&u);
    uint8_t buf[64];
    const size_t n = cal_user_encode(&u, buf, sizeof(buf));
    uint32_t detected = 0, total = 0;
    for (size_t b = 0; b < n; b++) {
        for (int bit = 0; bit < 8; bit++) {
            buf[b] ^= (uint8_t)(1u << bit);
            if (cal_user_decode(buf, n, &d) != CAL_OK) {
                detected++;
            }
            total++;
            buf[b] ^= (uint8_t)(1u << bit);
        }
    }
    CHECK(detected == total);
    CHECK(cal_user_decode(buf, n - 1u, &d) != CAL_OK);
    /* a well-formed record of another version or type is refused */
    uint8_t p[CAL_USER_LEN];
    memcpy(p, buf + CAL_HDR_LEN, CAL_USER_LEN);
    uint8_t other[64];
    size_t m = cal_record_encode(CAL_USER, 3u, p, CAL_USER_LEN, other, sizeof(other));
    CHECK(cal_user_decode(other, m, &d) == CAL_E_VERSION);
    m = cal_record_encode(CAL_HALL, CAL_USER_VERSION, p, CAL_USER_LEN, other, sizeof(other));
    CHECK(cal_user_decode(other, m, &d) == CAL_E_TYPE);
    /* valid CRC but out-of-range content (e.g. written by a buggy tool) */
    le_put_f32(p + 16, 2.0f);   /* g_max */
    m = cal_record_encode(CAL_USER, CAL_USER_VERSION, p, CAL_USER_LEN, other, sizeof(other));
    CHECK(cal_user_decode(other, m, &d) == CAL_E_RANGE);
    tr_log("CAL_USER record: %u/%u single-bit corruptions rejected; wrong version/type/range rejected", (unsigned)detected,
           (unsigned)total);
}

static float run_spec(double f_trem, double a_trem, double f_stroke, double a_stroke, uint32_t seed, double f_lo,
                      double f_hi)
{
    static cal_spec_t c;
    cal_spec_init(&c, 1024u);
    tr_rng_t r;
    tr_rng_seed(&r, seed);
    const double dt = 1.0 / 250.0;
    bool done = false;
    for (int k = 0; !done; k++) {
        const double t = k * dt;
        const double x = a_stroke * sin(2.0 * 3.141592653589793 * f_stroke * t) +
                         a_trem * sin(2.0 * 3.141592653589793 * f_trem * t + 0.3) + 2e-3 * t +   /* drift */
                         3e-6 * tr_rng_normal(&r);
        const double y = 0.6 * a_stroke * cos(2.0 * 3.141592653589793 * f_stroke * t) +
                         0.4 * a_trem * sin(2.0 * 3.141592653589793 * f_trem * t + 1.1) + 3e-6 * tr_rng_normal(&r);
        const float p[2] = {(float)(0.05 + x), (float)(0.02 + y)};   /* absolute page coordinates */
        done = cal_spec_push(&c, p);
    }
    return cal_spec_peak(&c, (float)f_lo, (float)f_hi);
}

void test_calib_spectral_f0(void)
{
    /* HOLD window: tremor only */
    const double f0s[3] = {5.3, 8.3, 11.7};
    double emax = 0.0;
    for (int k = 0; k < 3; k++) {
        const float f = run_spec(f0s[k], 2e-4, 3.0, 0.0, 30u + (uint32_t)k, 2.0, 14.0);
        CHECK_CLOSE(f, f0s[k], 0.1, 0.0);
        emax = fmax(emax, fabs((double)f - f0s[k]));
    }
    /* WRITE window: strokes 1.5 mm at 4.6 Hz plus the tremor */
    const float fs = run_spec(8.3, 2e-4, 4.6, 1.5e-3, 40u, 2.0, 8.3 - 1.0);
    CHECK_CLOSE(fs, 4.6, 0.15, 0.0);
    /* no tremor: no peak accepted */
    const float fn = run_spec(8.0, 0.0, 3.0, 0.0, 41u, 2.0, 14.0);
    CHECK(fn == 0.0f);
    tr_log("Goertzel bank 2-14 Hz (0.1 Hz bins, Hann, 4.1 s at 250 Hz): tremor peak error <= %.3f Hz for 5.3/8.3/11.7 Hz; "
           "stroke peak %.2f Hz (true 4.6); noise-only window -> no peak", emax, (double)fs);
}

void test_calib_gate_rule(void)
{
    cal_user_t u;
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 8.3f, 4.6f);
    CHECK((u.flags & CAL_FLAG_SEPARABLE) != 0u && (u.mode_perm & SM_PERM_KF) != 0u);
    CHECK_CLOSE(u.f_gate_hz, 0.5 * (8.3 + 4.6), 1e-5, 0.0);
    CHECK(u.f_gate_hz + 0.5f * u.f_gate_width_hz <= 8.3f + 1e-5f);   /* gate fully open at f0 */
    CHECK(cal_user_validate(&u) == CAL_OK);
    /* close to the handwriting band: not separable -> ASSIST_KF withdrawn, tuned gate kept */
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 5.0f, 4.5f);
    CHECK((u.flags & CAL_FLAG_SEPARABLE) == 0u && (u.mode_perm & SM_PERM_KF) == 0u);
    CHECK(u.f_gate_hz == PEN_BAL_F_GATE);
    /* high tremor frequency: gate limited so that it is fully open at f0 */
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 7.0f, 4.0f);
    CHECK_CLOSE(u.f_gate_hz, 5.5, 1e-5, 0.0);
    /* no clear peak: defaults unchanged */
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 0.0f, 4.5f);
    CHECK(u.f_gate_hz == PEN_BAL_F_GATE && (u.mode_perm & SM_PERM_KF) != 0u);
    tr_log("gate rule: f0 8.3 / stroke 4.6 Hz -> f_gate 6.45 Hz; f0 5.0 / 4.5 Hz -> not separable, ASSIST_KF withdrawn");
}
