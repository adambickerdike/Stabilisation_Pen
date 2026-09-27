/*
 * test_thermal.c - two-node coil temperature estimator and derating
 * (synthetic data; closed-form references in double precision).
 */
#include <math.h>
#include <string.h>

#include "params_gen.h"
#include "thermal.h"
#include "tr.h"

#define DT_SLOW 0.01f   /* 100 Hz estimator in the application */

/* eigen time constants of the coupled coil/structure network (s), fast and slow */
static void network_taus(double *tau_fast, double *tau_slow)
{
    const double a1 = 1.0 / (PEN_RTH_COIL * PEN_CTH_COIL), a2 = 1.0 / (PEN_RTH_COIL * PEN_CTH_STRUCT);
    const double a3 = 1.0 / (PEN_RTH_STRUCT * PEN_CTH_STRUCT);
    const double tr = -(a1 + a2 + a3), det = a1 * a3;
    const double disc = sqrt(tr * tr - 4.0 * det);
    *tau_fast = -2.0 / (tr - disc);
    *tau_slow = -2.0 / (tr + disc);
}

static thermal_in_t no_input(void)
{
    thermal_in_t in;
    memset(&in, 0, sizeof(in));
    return in;
}

void test_thermal_model_steady_state(void)
{
    const double Tref = (double)PEN_T_AMB + (double)PEN_T_STRUCT_RISE_IDLE;
    const double Rcs = PEN_RTH_COIL, Rsa = PEN_RTH_STRUCT;
    /* (a) constant loss P: T_c = T_ref + P (R_cs + R_sa), T_s = T_ref + P R_sa */
    thermal_t t;
    thermal_init(&t, PEN_T_AMB);
    const float P = 0.20f;
    for (int k = 0; k < 40000; k++) {   /* 4000 s = 21 slow time constants, 0.1 s steps */
        thermal_network_step(&t, 0.1f, P);
    }
    const double Tc_ss = Tref + (double)P * (Rcs + Rsa), Ts_ss = Tref + (double)P * Rsa;
    CHECK_CLOSE(t.T_coil, Tc_ss, 0.05, 0.0);
    CHECK_CLOSE(t.T_struct, Ts_ss, 0.05, 0.0);
    const double sim_c = t.T_coil, sim_s = t.T_struct;
    /* (b) constant current with the copper tempco (full estimator step, 100 Hz, NTC absent):
     *     T_c = [T_ref + I2 R20 (1 - 20 a) R_tot] / (1 - I2 R20 a R_tot) */
    thermal_init(&t, PEN_T_AMB);
    thermal_in_t in = no_input();
    in.i2_mean[0] = 0.15f * 0.15f;
    for (int k = 0; k < 400000; k++) {   /* 4000 s */
        thermal_step(&t, DT_SLOW, &in);
    }
    const double a = PEN_ALPHA_CU, R20 = PEN_R20, I2 = 0.15 * 0.15, Rt = Rcs + Rsa;
    const double Tc_i = (Tref + I2 * R20 * (1.0 - 20.0 * a) * Rt) / (1.0 - I2 * R20 * a * Rt);
    CHECK_CLOSE(t.T_coil, Tc_i, 0.02, 0.0);
    CHECK(t.source == THERMAL_SRC_MODEL && !t.res_used[0]);
    const double sim_i = t.T_coil;
    /* (c) no coil loss: both nodes settle at T_amb + T_struct_rise_idle */
    thermal_init(&t, PEN_T_AMB);
    for (int k = 0; k < 40000; k++) {
        thermal_network_step(&t, 0.1f, 0.0f);
    }
    CHECK_CLOSE(t.T_coil, Tref, 0.05, 0.0);
    CHECK_CLOSE(t.T_struct, Tref, 0.05, 0.0);
    tr_log("two-node steady state: 0.20 W -> coil %.3f degC (closed form %.3f), structure %.3f (%.3f); 0.15 A on one "
           "coil with copper tempco -> %.3f degC (closed form %.3f); no loss -> coil %.3f degC (T_amb + %.1f K = %.3f); "
           "R_coil-struct %.0f K/W + R_struct-amb %.1f K/W = %.1f K/W (README D6)",
           sim_c, Tc_ss, sim_s, Ts_ss, sim_i, Tc_i, (double)t.T_coil, (double)PEN_T_STRUCT_RISE_IDLE, Tref, Rcs, Rsa,
           Rcs + Rsa);
}

void test_thermal_two_time_constants(void)
{
    double tf, ts;
    network_taus(&tf, &ts);
    const double Tref = (double)PEN_T_AMB + (double)PEN_T_STRUCT_RISE_IDLE;
    const float P = 0.30f;
    const double Tss = Tref + (double)P * ((double)PEN_RTH_COIL + (double)PEN_RTH_STRUCT);
    /* analytic step response of the coil node from equilibrium (x = T - T_ref) */
    const double a1 = 1.0 / (PEN_RTH_COIL * PEN_CTH_COIL);
    const double l1 = -1.0 / tf, l2 = -1.0 / ts;
    /* eigenvectors v = (a1, a1 + lambda); x(0) = 0 = x_ss + c1 v1 + c2 v2 */
    const double xs0 = (double)P * ((double)PEN_RTH_COIL + (double)PEN_RTH_STRUCT), xs1 = (double)P * PEN_RTH_STRUCT;
    const double v10 = a1, v11 = a1 + l1, v20 = a1, v21 = a1 + l2;
    const double det = v10 * v21 - v20 * v11;
    const double c1 = (-xs0 * v21 + xs1 * v20) / det, c2 = (-xs1 * v10 + xs0 * v11) / det;
    thermal_t t;
    thermal_init(&t, PEN_T_AMB);
    t.T_coil = (float)Tref;
    t.T_struct = (float)Tref;
    const float h = 0.1f;
    double y[4] = {0, 0, 0, 0}, emax = 0.0;
    const int k_at[4] = {100, 400, 6000, 9000};   /* t = 10, 40, 600, 900 s */
    for (int k = 1; k <= 9000; k++) {
        thermal_network_step(&t, h, P);
        const double tt = k * (double)h;
        const double an = Tref + xs0 + c1 * v10 * exp(l1 * tt) + c2 * v20 * exp(l2 * tt);
        emax = fmax(emax, fabs((double)t.T_coil - an));
        for (int m = 0; m < 4; m++) {
            if (k == k_at[m]) {
                y[m] = Tss - (double)t.T_coil;
            }
        }
    }
    /* slow: late-time log slope; fast: log slope of the residual after removing the slow mode */
    const double ts_fit = (900.0 - 600.0) / log(y[2] / y[3]);
    const double B = y[2] * exp(600.0 / ts_fit);
    const double z1 = y[0] - B * exp(-10.0 / ts_fit), z2 = y[1] - B * exp(-40.0 / ts_fit);
    const double tf_fit = (40.0 - 10.0) / log(z1 / z2);
    CHECK_CLOSE(ts_fit, ts, 0.0, 0.01);
    CHECK_CLOSE(tf_fit, tf, 0.0, 0.01);
    CHECK(emax < 0.05);
    CHECK(tf > 30.0 && tf < 40.0 && ts > 170.0 && ts < 210.0);
    tr_log("0.30 W step: time constants from the response %.1f s and %.1f s (network eigenvalues %.1f s and %.1f s; "
           "uncoupled R C products %.2f s and %.2f s); max |T - analytic| %.3f K over 900 s", tf_fit, ts_fit, tf, ts,
           (double)(PEN_RTH_COIL * PEN_CTH_COIL), (double)(PEN_RTH_STRUCT * PEN_CTH_STRUCT), emax);
}

void test_thermal_resistance_estimate(void)
{
    /* true coil at 70 degC carrying 0.30 A; the estimator starts at 25 degC; NTC absent */
    const float T_true = 70.0f;
    const float R_true = PEN_R20 * (1.0f + PEN_ALPHA_CU * (T_true - 20.0f));
    thermal_in_t in = no_input();
    in.i_mean[0] = 0.30f;
    in.i_mean[1] = -0.25f;
    in.i2_mean[0] = 0.09f;
    in.i2_mean[1] = 0.0625f;
    for (int ax = 0; ax < 2; ax++) {
        in.v_mean[ax] = in.i_mean[ax] * (R_true + PEN_R_BRIDGE + PEN_R_SHUNT);
    }
    thermal_t t;
    thermal_init(&t, 25.0f);
    int k_conv = -1;
    for (int k = 0; k < 1000; k++) {   /* 10 s */
        thermal_step(&t, DT_SLOW, &in);
        if (k_conv < 0 && fabsf(t.T_coil - T_true) < 2.0f) {
            k_conv = k;
        }
    }
    CHECK(t.res_used[0] && t.res_used[1] && t.source == THERMAL_SRC_RES);
    CHECK_CLOSE(t.T_res[0], T_true, 0.05, 0.0);
    CHECK_CLOSE(t.T_res[1], T_true, 0.05, 0.0);
    CHECK(k_conv >= 0 && k_conv < 200);
    /* moving stage (back-EMF) or unsteady current: no resistance update */
    thermal_t t2;
    thermal_init(&t2, 25.0f);
    thermal_in_t mv = in;
    mv.stage_speed = 0.02f;
    thermal_step(&t2, DT_SLOW, &mv);
    CHECK(!t2.res_used[0]);
    tr_log("resistance thermometry (NTC invalid; V/I - r_bridge - r_shunt): T_R = %.2f degC for a 70 degC coil; "
           "estimate within 2 degC after %.2f s; systematic error from r_bridge spread 0.28-0.60 ohm: +/-%.1f degC "
           "(VERIFY EXP-B07)", (double)t.T_res[0], (double)k_conv * 0.01, 0.16 / (6.0 * 0.00393));
}

void test_thermal_ntc_and_derating(void)
{
    /* NTC conversion at 50 degC (10k B3435 with 10k pull-up) */
    const double r50 = 10000.0 * exp(3435.0 * (1.0 / 323.15 - 1.0 / 298.15));
    const float x50 = (float)(r50 / (r50 + 10000.0));
    float T, T50 = 0.0f;
    CHECK(thermal_ntc_degC(x50, &T50));
    CHECK_CLOSE(T50, 50.0, 0.05, 0.0);
    CHECK(thermal_ntc_degC(0.5f, &T));
    CHECK_CLOSE(T, 25.0, 0.02, 0.0);
    CHECK(!thermal_ntc_degC(0.995f, &T));   /* open */
    CHECK(!thermal_ntc_degC(0.005f, &T));   /* short */
    /* the first valid reading initialises both nodes (warm boot) */
    thermal_t t;
    thermal_init(&t, 25.0f);
    thermal_in_t in = no_input();
    in.ntc_valid = true;
    in.ntc_degC = 50.0f;
    thermal_step(&t, DT_SLOW, &in);
    CHECK(t.ntc_seen && t.T_coil >= 50.0f && fabsf(t.T_struct - 50.0f) < 0.01f && t.source == THERMAL_SRC_NTC);
    /* NTC preferred: a model that says 90 degC is pulled to a valid 40 degC reading within 0.5 s */
    thermal_init(&t, 25.0f);
    t.ntc_seen = true;
    t.T_coil = 90.0f;
    in.ntc_degC = 40.0f;
    int k40 = -1;
    for (int k = 0; k < 100; k++) {
        thermal_step(&t, DT_SLOW, &in);
        if (k40 < 0 && fabsf(t.T_coil - 40.0f) < 0.5f) {
            k40 = k;
        }
    }
    CHECK(k40 >= 0 && (k40 + 1) * 0.01 <= 0.5);
    /* ... and resistance thermometry is not applied while the NTC is valid */
    in.i_mean[0] = 0.30f;
    in.i2_mean[0] = 0.09f;
    in.v_mean[0] = 0.30f * (thermal_r_coil(70.0f) + PEN_R_BRIDGE + PEN_R_SHUNT);
    thermal_step(&t, DT_SLOW, &in);
    thermal_step(&t, DT_SLOW, &in);
    CHECK(!t.res_used[0] && t.R_est[0] > 0.0f && t.source == THERMAL_SRC_NTC);
    /* derating and the over-temperature condition with hysteresis (thresholds unchanged) */
    const thermal_in_t off = no_input();
    thermal_init(&t, 25.0f);
    t.T_coil = 107.5f;
    thermal_step(&t, 1e-6f, &off);
    CHECK_CLOSE(t.derate, 0.5, 0.01, 0.0);
    CHECK(!t.over_temp);
    t.T_coil = 116.0f;
    thermal_step(&t, 1e-6f, &off);
    CHECK(t.over_temp && t.derate == 0.0f);
    t.T_coil = 95.0f;
    thermal_step(&t, 1e-6f, &off);
    CHECK(t.over_temp);                      /* hysteresis: clears below 90 degC */
    t.T_coil = 89.0f;
    thermal_step(&t, 1e-6f, &off);
    CHECK(!t.over_temp && t.derate == 1.0f);
    CHECK(PEN_T_DERATE_START == 100.0f && PEN_T_FAULT == 115.0f && PEN_T_RECOVER == 90.0f);
    tr_log("NTC 50 degC -> %.2f degC; the coil-former NTC is preferred when valid (90 -> 40 degC within %.2f s; "
           "resistance thermometry only without it); derate 1 at <= %.0f degC -> 0 at %.0f degC (fault), clears < %.0f "
           "degC (unchanged)", (double)T50, (k40 + 1) * 0.01, (double)PEN_T_DERATE_START, (double)PEN_T_FAULT,
           (double)PEN_T_RECOVER);
}
