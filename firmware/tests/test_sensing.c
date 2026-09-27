/*
 * test_sensing.c - Hall conversion, housing-position fusion (simulator
 * scheme), attitude from gravity.
 */
#include <math.h>
#include <string.h>

#include "fusion.h"
#include "hall.h"
#include "params_gen.h"
#include "tr.h"

void test_hall_conversion(void)
{
    cal_hall_t c;
    cal_hall_default(&c);
    const float i0[2] = {0.0f, 0.0f};
    /* inverse of the diagonal default map */
    const double qx = 123e-6, qy = -45e-6, s = 0.1e-3;
    int16_t raw[3] = {(int16_t)lrint(qx / (double)c.m[0][0] / (double)c.lsb_T),
                      (int16_t)lrint(qy / (double)c.m[1][1] / (double)c.lsb_T),
                      (int16_t)lrint(s / (double)c.m[2][2] / (double)c.lsb_T)};
    float q[2], sv, fa;
    hall_convert(&c, raw, i0, q, &sv, &fa);
    const double lsb_m = (double)c.lsb_T * (double)c.m[0][0];
    CHECK_CLOSE(q[0], qx, lsb_m, 0.0);
    CHECK_CLOSE(q[1], qy, lsb_m, 0.0);
    CHECK_CLOSE(sv, s, lsb_m, 0.0);
    CHECK_CLOSE(fa, PEN_F_PRE + PEN_K_AX * s, 1e-4, 0.0);
    /* axial slide never negative (front stop) */
    raw[2] = -500;
    hall_convert(&c, raw, i0, q, &sv, &fa);
    CHECK(sv == 0.0f && fa == PEN_F_PRE);
    /* current crosstalk (T/A) is removed */
    cal_hall_t cx = c;
    cx.ict[0][0] = 2e-4f;   /* 0.2 mT per A on Bx */
    const float i1[2] = {0.5f, 0.0f};
    int16_t raw2[3] = {(int16_t)lrint((qx / (double)c.m[0][0] + 2e-4 * 0.5) / (double)c.lsb_T), raw[1], 0};
    hall_convert(&cx, raw2, i1, q, &sv, &fa);
    CHECK_CLOSE(q[0], qx, 2.0 * lsb_m, 0.0);
    /* cubic term */
    cx = c;
    cx.c3[1] = 1e6f;   /* y + 1e6 y^3 */
    raw[2] = 0;
    hall_convert(&cx, raw, i0, q, &sv, &fa);
    CHECK_CLOSE(q[1], qy + 1e6 * qy * qy * qy, 2.0 * lsb_m, 1e-4);
    tr_log("Hall: default (UNCALIBRATED placeholder) LSB = %.1f nm at the tip; crosstalk and cubic terms applied",
           lsb_m * 1e9);
}

void test_fusion_matches_sim_scheme(void)
{
    /* housing oscillates 0.3 mm at 8 Hz; optical delayed 2 ms (1 kHz sample
     * and hold), IMU delayed 1 ms (exact acceleration). The fused estimate
     * refers to t - imu_delay; both errors are taken against truth(t - 1 ms) */
    fusion_t f;
    fusion_init(&f, (uint16_t)PEN_FUSION_LAG_TICKS);
    const double w = 2.0 * 3.141592653589793 * 8.0, A = 3e-4, v0 = 0.0;
    const double dt_sim = 25e-6;
    double v_ref[2] = {0.0, 0.0}, p_ref[2] = {0.0, 0.0};   /* double-precision reference of the same scheme */
    double ring[64][2];
    memset(ring, 0, sizeof(ring));
    double e_fw = 0.0, e_ref = 0.0, e_opt = 0.0;
    uint32_t tick = 0;
    double o_last[2] = {0.0, 0.0};
    const int n = (int)(1.0 / dt_sim);
    for (int k = 0; k < n; k++) {
        const double t = k * dt_sim;
        if (k % 20 == 0) {
            /* stage tick: fused position vs truth at t - IMU delay */
            float ph[2];
            bool valid;
            fusion_tick(&f, ph, &valid);
            const uint32_t kk = tick % 64u, jj = (tick + 64u - (uint32_t)PEN_FUSION_LAG_TICKS) % 64u;
            ring[kk][0] = p_ref[0];
            ring[kk][1] = p_ref[1];
            const double pr = o_last[0] + (p_ref[0] - ring[jj][0]);
            tick++;
            if (t > 0.5) {
                const double td = t - 1e-3;
                const double truth = A * sin(w * td) + v0 * td;
                e_fw = fmax(e_fw, fabs((double)ph[0] - pr));
                e_ref = fmax(e_ref, fabs(pr - truth));
                e_opt = fmax(e_opt, fabs(o_last[0] - truth));
            }
        }
        if (k % 40 == 0) {
            const double to = t - 2e-3;
            const float po[2] = {(float)(A * sin(w * to) + v0 * to), 0.0f};
            fusion_optical_sample(&f, po, true);
            o_last[0] = (double)po[0];
        }
        if (k % 10 == 0 && k > 0) {   /* ~3840 Hz (4 kHz grid here) */
            const double ti = t - 1e-3;
            const float a[2] = {(float)(-w * w * A * sin(w * ti)), 0.0f};
            const double dti = 10 * dt_sim;
            fusion_imu_sample(&f, a, (float)dti);
            v_ref[0] = (v_ref[0] + (double)a[0] * dti) * (1.0 - dti / 0.5);
            p_ref[0] += v_ref[0] * dti;
        }
    }
    CHECK(e_fw < 5e-9);          /* float32 port = double reference of the scheme */
    CHECK(e_ref < 0.75 * e_opt); /* bridging the optical latency with the IMU helps */
    tr_log("fusion (simulator scheme): float32 vs double reference %.2g m; max error vs truth(t - 1 ms) %.1f um "
           "(optical sample-and-hold staleness remains) vs raw delayed optics %.1f um", e_fw, e_ref * 1e6, e_opt * 1e6);
}

void test_attitude_from_gravity(void)
{
    const double th = 50.0 * 3.141592653589793 / 180.0, ro = 30.0 * 3.141592653589793 / 180.0;
    /* specific force at rest: +g n in housing coordinates */
    const float acc[3] = {(float)(-9.80665 * cos(th) * cos(ro)), (float)(9.80665 * cos(th) * sin(ro)),
                          (float)(9.80665 * sin(th))};
    fusion_t f;
    fusion_init(&f, 2u);
    const float gyro0[3] = {0.0f, 0.0f, 0.0f};
    for (int k = 0; k < 200; k++) {
        fusion_attitude(&f, acc, gyro0, 5e-4f, 0.02f);
    }
    CHECK_CLOSE(f.theta, th, 1e-4, 0.0);
    CHECK_CLOSE(f.rho, ro, 1e-4, 0.0);
    /* rotation about the page normal at 0.5 rad/s for 1 s -> phi = 0.5 rad */
    const double gn = 9.80665;
    const float gyro[3] = {(float)(0.5 * acc[0] / gn), (float)(0.5 * acc[1] / gn), (float)(0.5 * acc[2] / gn)};
    fusion_phi_reset(&f);
    for (int k = 0; k < 2000; k++) {
        fusion_attitude(&f, acc, gyro, 5e-4f, 0.02f);
    }
    CHECK_CLOSE(f.phi, 0.5, 1e-3, 0.0);
    tr_log("attitude from gravity: theta %.3f deg (50), rho %.3f deg (30); yaw about n integrates to phi %.4f rad (0.5)",
           (double)f.theta * 57.29578, (double)f.rho * 57.29578, (double)f.phi);
}
