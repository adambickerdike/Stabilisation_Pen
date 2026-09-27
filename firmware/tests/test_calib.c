/*
 * test_calib.c - calibration records (CRC, versioning, ranges) and the
 * tremor-frequency calibration on synthetic housing motion.
 */
#include <math.h>
#include <string.h>

#include "calib.h"
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
    u.gamma = 0.3f;
    u.flags = CAL_FLAG_SEPARABLE | CAL_FLAG_TREMOR_FOUND;
    uint8_t buf[64];
    const size_t n = cal_user_encode(&u, buf, sizeof(buf));
    CHECK(n == CAL_USER_LEN + CAL_REC_OVERHEAD);
    CHECK(le_get_u32(buf) == CAL_MAGIC && buf[0] == 'P' && buf[1] == 'C' && buf[2] == 'A' && buf[3] == 'L');
    CHECK(buf[4] == CAL_USER && le_get_u16(buf + 5) == CAL_USER_VERSION && le_get_u16(buf + 7) == CAL_USER_LEN);
    CHECK(cal_user_decode(buf, n, &d) == CAL_OK);
    CHECK(d.f0_hz == u.f0_hz && d.f_stroke_hz == u.f_stroke_hz && d.f_gate_hz == u.f_gate_hz &&
          d.f_gate_width_hz == u.f_gate_width_hz && d.g_max == u.g_max && d.q_lim_m == u.q_lim_m &&
          d.gamma == u.gamma && d.mode_perm == u.mode_perm && d.flags == u.flags);
    /* invalid values are never written */
    cal_user_t bad = u;
    bad.g_max = 1.5f;
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad = u;
    bad.q_lim_m = 0.7e-3f;   /* beyond the design soft limit */
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
    bad = u;
    bad.gamma = NAN;
    CHECK(cal_user_encode(&bad, buf, sizeof(buf)) == 0u);
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
    size_t m = cal_record_encode(CAL_USER, 2u, p, CAL_USER_LEN, other, sizeof(other));
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
