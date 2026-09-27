/*
 * test_filters.c - biquad vs scipy, Jacobian vs stabpen/frames.py, limiter
 * and authority-smoothing properties.
 */
#include <math.h>
#include <string.h>

#include "biquad.h"
#include "jacobian.h"
#include "limiter.h"
#include "params.h"
#include "tr.h"
#include "vec.h"

static double run_biquad(const vec_t *v, const biquad_coef_t *c, int cx, int cy, double *max_ref)
{
    biquad_state_t st = {0.0f, 0.0f};
    double emax = 0.0, rmax = 0.0;
    for (uint32_t r = 0; r < v->rows; r++) {
        const float y = biquad_step(c, &st, vec_at(v, r, cx));
        const double e = fabs((double)y - (double)vec_at(v, r, cy));
        if (e > emax) {
            emax = e;
        }
        if (fabs((double)vec_at(v, r, cy)) > rmax) {
            rmax = fabs((double)vec_at(v, r, cy));
        }
    }
    *max_ref = rmax;
    return emax;
}

void test_biquad_vs_scipy(void)
{
    vec_t v;
    CHECK(vec_load("biquad.vec", &v));
    if (v.rows == 0u) {
        return;
    }
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    const int cx = vec_col(&v, "x");
    double rm;
    /* contact-feedforward force filter (DEC-011): 2nd-order Butterworth 60 Hz */
    double e = run_biquad(&v, &p.ffc, cx, vec_col(&v, "y_ffc"), &rm);
    CHECK(e < 2e-6 * (1.0 + rm));
    tr_log("ffc 60 Hz biquad vs scipy sosfilt: max |err| %.3g (signal max %.3g)", e, rm);
    e = run_biquad(&v, &p.ffc, cx, vec_col(&v, "y_butter60"), &rm);
    CHECK(e < 2e-6 * (1.0 + rm));   /* coefficients equal scipy.signal.butter(2, 60, fs=2000) */
    e = run_biquad(&v, &p.bp1, cx, vec_col(&v, "y_bp1"), &rm);
    CHECK(e < 2e-5 * (1.0 + rm));
    tr_log("bp1 high-pass biquad vs scipy: max |err| %.3g (poles near z = 1: float32 DF2T)", e);
    e = run_biquad(&v, &p.bp2, cx, vec_col(&v, "y_bp2"), &rm);
    CHECK(e < 2e-5 * (1.0 + rm));
    tr_log("bp2 low-pass biquad vs scipy: max |err| %.3g", e);
    /* DC gain of the low-pass is 1 */
    const float dc = (p.ffc.b0 + p.ffc.b1 + p.ffc.b2) / (1.0f + p.ffc.a1 + p.ffc.a2);
    CHECK_CLOSE(dc, 1.0, 1e-5, 0.0);
}

void test_jacobian_vs_frames(void)
{
    vec_t v;
    CHECK(vec_load("jacobian.vec", &v));
    if (v.rows == 0u) {
        return;
    }
    const int ct = vec_col(&v, "theta"), cp = vec_col(&v, "phi"), cr = vec_col(&v, "rho"), cg = vec_col(&v, "gamma");
    const int cj = vec_col(&v, "J00"), ci = vec_col(&v, "Ji00");
    double ej = 0.0, ei = 0.0;
    for (uint32_t r = 0; r < v.rows; r++) {
        jac_t J;
        jac_update(&J, vec_at(&v, r, ct), vec_at(&v, r, cp), vec_at(&v, r, cr), vec_at(&v, r, cg));
        for (int i = 0; i < 2; i++) {
            for (int j = 0; j < 2; j++) {
                const double dj = fabs((double)J.j[i][j] - (double)vec_at(&v, r, cj + 2 * i + j));
                const double di = fabs((double)J.ji[i][j] - (double)vec_at(&v, r, ci + 2 * i + j));
                ej = dj > ej ? dj : ej;
                ei = di > ei ? di : ei;
            }
        }
    }
    CHECK(ej < 2e-6);
    CHECK(ei < 2e-6);
    tr_log("J and J^-1 vs stabpen/frames.py (gamma = 1) and numeric 3-D construction (0 <= gamma <= 1), %u poses:"
           " max |err| J %.2g, J^-1 %.2g", (unsigned)v.rows, ej, ei);
}

void test_jacobian_properties(void)
{
    tr_rng_t rng;
    tr_rng_seed(&rng, 7u);
    double worst = 0.0;
    for (int k = 0; k < 500; k++) {
        const float th = (float)(0.4 + 1.1 * tr_rng_uniform(&rng));
        const float ph = (float)(6.2 * tr_rng_uniform(&rng) - 3.1);
        const float ro = (float)(6.2 * tr_rng_uniform(&rng) - 3.1);
        const float g = (float)tr_rng_uniform(&rng);
        jac_t J;
        jac_update(&J, th, ph, ro, g);
        for (int i = 0; i < 2; i++) {
            for (int j = 0; j < 2; j++) {
                const double s = (double)J.j[i][0] * J.ji[0][j] + (double)J.j[i][1] * J.ji[1][j];
                const double e = fabs(s - (i == j ? 1.0 : 0.0));
                worst = e > worst ? e : worst;
            }
        }
        const double det = (double)J.j[0][0] * J.j[1][1] - (double)J.j[0][1] * J.j[1][0];
        const double jt1 = sin((double)th) + (double)g * cos((double)th) * cos((double)th) / sin((double)th);
        CHECK_CLOSE(det, jt1, 1e-5, 1e-5);
    }
    CHECK(worst < 1e-5);
    /* limits: gamma = 1 -> J_t1 = 1/sin(theta) (rigid page), gamma = 0 -> sin(theta) */
    jac_t J;
    jac_update(&J, 0.8726646f, 0.0f, 0.0f, 1.0f);
    CHECK_CLOSE(J.jt1, 1.0 / sin(0.8726646), 1e-6, 0.0);
    jac_update(&J, 0.8726646f, 0.0f, 0.0f, 0.0f);
    CHECK_CLOSE(J.jt1, sin(0.8726646), 1e-6, 0.0);
    /* phi = rho = 0: page x maps to stage x scaled by 1/J_t1; page y to stage y */
    float d[2] = {1e-4f, 0.0f}, q[2];
    jac_update(&J, 0.8726646f, 0.0f, 0.0f, PEN_GAMMA_NOM);
    jac_page_to_stage(&J, d, q);
    CHECK_CLOSE(q[0], 1e-4 / J.jt1, 1e-10, 1e-5);
    CHECK_CLOSE(q[1], 0.0, 1e-12, 0.0);
    tr_log("J J^-1 = I within %.2g over 500 random poses; det J = J_t1", worst);
}

void test_limiter_radial_properties(void)
{
    const float qlim = PEN_Q_LIM, qt = PEN_Q_TAPER, knee = qlim - qt;
    tr_rng_t rng;
    tr_rng_seed(&rng, 11u);
    float prev_r = -1.0f, prev_out = -1.0f;
    uint32_t bad_bound = 0, bad_dir = 0, bad_inner = 0, bad_mono = 0;
    for (int k = 0; k < 4000; k++) {
        const float r = 5e-3f * (float)k / 4000.0f;    /* 0 .. 5 mm radius, monotonic */
        const float a = (float)(6.283185 * tr_rng_uniform(&rng));
        float q[2] = {r * cosf(a), r * sinf(a)};
        lim_radial_taper(q, qlim, qt);
        const float ro = hypotf(q[0], q[1]);
        if (!(ro <= qlim)) {   /* float32 tanh saturates to exactly 1 far out */
            bad_bound++;
        }
        if (r > 0.0f && fabsf(atan2f(q[1], q[0]) - atan2f(sinf(a), cosf(a))) > 1e-4f) {
            bad_dir++;
        }
        if (r <= knee && fabsf(ro - r) > 1e-9f) {
            bad_inner++;
        }
        if (r > prev_r && ro + 1e-9f < prev_out) {
            bad_mono++;
        }
        prev_r = r;
        prev_out = ro;
    }
    CHECK(bad_bound == 0u && bad_dir == 0u && bad_inner == 0u && bad_mono == 0u);
    /* C1 continuity at the knee: slope 1 on both sides */
    float q1[2] = {knee + 1e-7f, 0.0f}, q2[2] = {knee + 2e-7f, 0.0f};
    lim_radial_taper(q1, qlim, qt);
    lim_radial_taper(q2, qlim, qt);
    CHECK_CLOSE((q2[0] - q1[0]) / 1e-7f, 1.0, 0.05, 0.0);
    /* far beyond the limit the radius approaches q_lim */
    float q3[2] = {1.0f, 0.0f};
    lim_radial_taper(q3, qlim, qt);
    CHECK_CLOSE(q3[0], qlim, 1e-9, 1e-6);
    tr_log("radial taper: |q| <= q_lim = %.3g m for 4000 radii up to 5 mm, identity inside the knee, monotonic, C1",
           (double)qlim);
}

void test_limiter_slew_properties(void)
{
    const float dmax = PEN_SLEW * PEN_TS_STAGE;
    tr_rng_t rng;
    tr_rng_seed(&rng, 13u);
    uint32_t bad = 0;
    for (int k = 0; k < 2000; k++) {
        float qr[2] = {(float)(1e-3 * (tr_rng_uniform(&rng) - 0.5)), (float)(1e-3 * (tr_rng_uniform(&rng) - 0.5))};
        const float qn[2] = {(float)(1e-3 * (tr_rng_uniform(&rng) - 0.5)), (float)(1e-3 * (tr_rng_uniform(&rng) - 0.5))};
        const float q0[2] = {qr[0], qr[1]};
        lim_slew(qr, qn, dmax);
        const float step = hypotf(qr[0] - q0[0], qr[1] - q0[1]);
        const float dist0 = hypotf(qn[0] - q0[0], qn[1] - q0[1]);
        if (step > dmax * (1.0f + 1e-5f)) {
            bad++;
        }
        if (dist0 <= dmax && (fabsf(qr[0] - qn[0]) > 1e-9f || fabsf(qr[1] - qn[1]) > 1e-9f)) {
            bad++;
        }
        /* moves along the line toward the target */
        const float cross = (qr[0] - q0[0]) * (qn[1] - q0[1]) - (qr[1] - q0[1]) * (qn[0] - q0[0]);
        if (fabsf(cross) > 1e-12f) {
            bad++;
        }
    }
    CHECK(bad == 0u);
    tr_log("slew: step <= %.3g m per tick (%.3g m/s) in 2000 random cases", (double)dmax, (double)PEN_SLEW);
}

void test_authority_smoothing(void)
{
    float g = 0.0f;
    const int n_tau = (int)lrintf(PEN_AUTHORITY_TAU / PEN_TS_STAGE);
    for (int k = 0; k < n_tau; k++) {
        g = lim_authority_step(g, 1.0f, PEN_ALPHA_A);
    }
    CHECK_CLOSE(g, 1.0 - exp(-1.0), 1e-4, 0.0);   /* first order, tau = authority_tau */
    for (int k = 0; k < 20 * n_tau; k++) {
        g = lim_authority_step(g, 0.3f, PEN_ALPHA_A);
    }
    CHECK_CLOSE(g, 0.3, 1e-5, 0.0);
}
