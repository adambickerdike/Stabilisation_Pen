/*
 * test_thermal.c - coil temperature observer and derating (synthetic data).
 */
#include <math.h>
#include <string.h>

#include "params_gen.h"
#include "thermal.h"
#include "tr.h"

#define DT_SLOW 0.01f   /* 100 Hz observer */

void test_thermal_model_steady_state(void)
{
    thermal_t t;
    thermal_init(&t, PEN_T_AMB);
    const float i[2] = {0.30f, 0.0f}, v[2] = {0.0f, 0.0f};   /* v = 0: resistance thermometry rejected */
    float t_63 = -1.0f;
    /* analytic steady state of C dT/dt = i^2 R20 (1 + a (T - 20)) - (T - Tamb)/Rth */
    const double a = PEN_ALPHA_CU, R20 = PEN_R20, Rth = PEN_RTH_COIL, I2 = 0.09;
    const double Tss = (PEN_T_AMB + Rth * I2 * R20 * (1.0 - 20.0 * a)) / (1.0 - Rth * I2 * R20 * a);
    for (int k = 0; k < 30000; k++) {   /* 300 s */
        thermal_step(&t, DT_SLOW, i, v, 0.0f, 0.0f, false);
        if (t_63 < 0.0f && (double)t.T[0] >= PEN_T_AMB + 0.632 * (Tss - PEN_T_AMB)) {
            t_63 = (float)k * DT_SLOW;
        }
    }
    CHECK_CLOSE(t.T[0], Tss, 0.3, 0.0);
    CHECK_CLOSE(t.T[1], PEN_T_AMB, 1e-3, 0.0);
    CHECK(!t.res_used[0]);
    tr_log("0.30 A on coil x (model only): steady %.2f degC (analytic %.2f), 63 %% rise at %.1f s "
           "(R_th C_th = %.0f s); R_th = %.0f K/W from config (README D6)", (double)t.T[0], Tss, (double)t_63,
           (double)(PEN_RTH_COIL * PEN_CTH_COIL), (double)PEN_RTH_COIL);
}

void test_thermal_resistance_estimate(void)
{
    /* true coil at 70 degC carrying 0.30 A; the observer starts at 25 degC */
    const float T_true = 70.0f;
    const float R_true = PEN_R20 * (1.0f + PEN_ALPHA_CU * (T_true - 20.0f));
    const float i[2] = {0.30f, -0.25f};
    const float v[2] = {i[0] * (R_true + PEN_R_BRIDGE + PEN_R_SHUNT), i[1] * (R_true + PEN_R_BRIDGE + PEN_R_SHUNT)};
    thermal_t t;
    thermal_init(&t, 25.0f);
    int k_conv = -1;
    for (int k = 0; k < 1000; k++) {   /* 10 s */
        thermal_step(&t, DT_SLOW, i, v, 0.0f, 0.0f, false);
        if (k_conv < 0 && fabsf(t.T[0] - T_true) < 2.0f) {
            k_conv = k;
        }
    }
    CHECK(t.res_used[0] && t.res_used[1]);
    CHECK_CLOSE(t.T_res[0], T_true, 0.05, 0.0);
    CHECK_CLOSE(t.T_res[1], T_true, 0.05, 0.0);
    CHECK(k_conv >= 0 && k_conv < 200);
    /* moving stage (back-EMF) or unsteady current: no resistance update */
    thermal_t t2;
    thermal_init(&t2, 25.0f);
    thermal_step(&t2, DT_SLOW, i, v, 0.02f, 0.0f, false);
    CHECK(!t2.res_used[0]);
    tr_log("resistance thermometry (V/I - r_bridge - r_shunt): T_R = %.2f degC for a 70 degC coil; estimate within "
           "2 degC after %.2f s; systematic error from r_bridge spread 0.28-0.60 ohm: +/-%.1f degC (VERIFY EXP-B07)",
           (double)t.T_res[0], (double)k_conv * 0.01, 0.16 / (6.0 * 0.00393));
}

void test_thermal_ntc_and_derating(void)
{
    /* NTC conversion at 50 degC (10k B3435 with 10k pull-up) */
    const double r50 = 10000.0 * exp(3435.0 * (1.0 / 323.15 - 1.0 / 298.15));
    const float x50 = (float)(r50 / (r50 + 10000.0));
    float T;
    CHECK(thermal_ntc_degC(x50, &T));
    CHECK_CLOSE(T, 50.0, 0.05, 0.0);
    CHECK(thermal_ntc_degC(0.5f, &T));
    CHECK_CLOSE(T, 25.0, 0.02, 0.0);
    CHECK(!thermal_ntc_degC(0.995f, &T));   /* open */
    CHECK(!thermal_ntc_degC(0.005f, &T));   /* short */
    /* lower bound: coil cannot be colder than its former */
    thermal_t t;
    thermal_init(&t, 25.0f);
    const float i0[2] = {0.0f, 0.0f}, v0[2] = {0.0f, 0.0f};
    thermal_step(&t, DT_SLOW, i0, v0, 0.0f, 50.0f, true);
    CHECK(t.T[0] >= 50.0f && t.T[1] >= 50.0f);
    /* idle relaxation toward the NTC */
    thermal_init(&t, 90.0f);
    for (int k = 0; k < 500; k++) {
        thermal_step(&t, DT_SLOW, i0, v0, 0.0f, 40.0f, true);
    }
    CHECK(fabsf(t.T[0] - 40.0f) < 1.0f);
    /* derating and the over-temperature condition with hysteresis */
    thermal_init(&t, 25.0f);
    t.T[0] = 107.5f;
    thermal_step(&t, 1e-6f, i0, v0, 0.0f, 0.0f, false);
    CHECK_CLOSE(t.derate, 0.5, 0.01, 0.0);
    CHECK(!t.over_temp);
    t.T[0] = 116.0f;
    thermal_step(&t, 1e-6f, i0, v0, 0.0f, 0.0f, false);
    CHECK(t.over_temp && t.derate == 0.0f);
    t.T[0] = 95.0f;
    thermal_step(&t, 1e-6f, i0, v0, 0.0f, 0.0f, false);
    CHECK(t.over_temp);                      /* hysteresis: clears below 90 degC */
    t.T[0] = 89.0f;
    thermal_step(&t, 1e-6f, i0, v0, 0.0f, 0.0f, false);
    CHECK(!t.over_temp && t.derate == 1.0f);
    tr_log("NTC 50 degC -> %.2f degC; derate 1 at <= %.0f degC -> 0 at %.0f degC (fault), clears < %.0f degC",
           (double)T, (double)PEN_T_DERATE_START, (double)PEN_T_FAULT, (double)PEN_T_RECOVER);
}
