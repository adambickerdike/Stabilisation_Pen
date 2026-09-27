/*
 * thermal.c - two-node coil temperature estimator (see header).
 * Status: PROPOSED DESIGN, host unit tests on synthetic data only.
 */
#include "thermal.h"

#include <math.h>
#include <string.h>

#include "mathx.h"
#include "params_gen.h"

#define THERMAL_STAGE_SPEED_MAX 0.005f  /* m/s: back-EMF n Kf v < 12 mV (proposed) */
#define THERMAL_DT_MAX 0.1f             /* s: sub-step the explicit integration beyond this */

void thermal_init(thermal_t *t, float T0)
{
    memset(t, 0, sizeof(*t));
    t->T_coil = T0;
    t->T_struct = T0;
    t->T_ntc = T0;
    t->T_ref = PEN_T_AMB + PEN_T_STRUCT_RISE_IDLE;
    t->derate = 1.0f;
}

float thermal_r_coil(float T)
{
    return PEN_R20 * (1.0f + PEN_ALPHA_CU * (T - 20.0f));
}

bool thermal_ntc_degC(float x, float *T)
{
    if (!(x > 0.02f && x < 0.98f)) {
        return false;  /* open or shorted NTC */
    }
    const float r = PEN_NTC_R_PULLUP * x / (1.0f - x);
    const float inv = 1.0f / 298.15f + logf(r / PEN_NTC_R25) / PEN_NTC_BETA;
    *T = 1.0f / inv - 273.15f;
    return true;
}

/* compensated (Kahan) accumulation: at 100 Hz the per-step increments near
 * equilibrium are below a float32 ulp of the temperature and would be lost */
static void kahan_add(float *sum, float *comp, float inc)
{
    const float y = inc - *comp;
    const float s = *sum + y;
    *comp = (s - *sum) - y;
    *sum = s;
}

void thermal_network_step(thermal_t *t, float dt, float P)
{
    /* explicit Euler; dt / 35 s << 1 at the 100 Hz application rate */
    float left = dt;
    while (left > 0.0f) {
        const float h = (left > THERMAL_DT_MAX) ? THERMAL_DT_MAX : left;
        const float q_cs = (t->T_coil - t->T_struct) / PEN_RTH_COIL;     /* coil -> structure, W */
        const float q_sa = (t->T_struct - t->T_ref) / PEN_RTH_STRUCT;    /* structure -> ambient/hand, W */
        kahan_add(&t->T_coil, &t->c_coil, h / PEN_CTH_COIL * (P - q_cs));
        kahan_add(&t->T_struct, &t->c_struct, h / PEN_CTH_STRUCT * (q_cs - q_sa));
        left -= h;
    }
}

void thermal_step(thermal_t *t, float dt, const thermal_in_t *in)
{
    const float r_ext = PEN_R_BRIDGE + PEN_R_SHUNT;
    t->ntc_valid = in->ntc_valid;
    if (in->ntc_valid) {
        t->T_ntc = in->ntc_degC;
        if (!t->ntc_seen) {
            t->T_coil = in->ntc_degC;   /* first measurement: both nodes start from it */
            t->T_struct = in->ntc_degC;
            t->ntc_seen = true;
        }
    }
    /* model prediction: copper loss at the current coil temperature */
    const float r_c = thermal_r_coil(t->T_coil);
    t->P = (in->i2_mean[0] + in->i2_mean[1]) * r_c;
    thermal_network_step(t, dt, t->P);
    t->source = THERMAL_SRC_MODEL;
    /* resistance thermometry (diagnostic always; correction only without a valid NTC) */
    for (int ax = 0; ax < 2; ax++) {
        t->res_used[ax] = false;
        const float ia = pen_absf(in->i_mean[ax]);
        const bool steady = pen_absf(in->i_mean[ax] - t->i_prev[ax]) < PEN_R_EST_DI_MAX;
        if (ia > PEN_R_EST_I_MIN && steady && in->stage_speed < THERMAL_STAGE_SPEED_MAX) {
            const float r_coil = in->v_mean[ax] / in->i_mean[ax] - r_ext;
            if (r_coil > 0.5f * PEN_R20 && r_coil < 2.0f * PEN_R20) {   /* plausibility (-107..+274 degC) */
                t->R_est[ax] = r_coil;
                t->T_res[ax] = 20.0f + (r_coil / PEN_R20 - 1.0f) / PEN_ALPHA_CU;
                if (!in->ntc_valid) {
                    t->T_coil += PEN_T_RES_GAIN * (t->T_res[ax] - t->T_coil);
                    t->res_used[ax] = true;
                    t->source = THERMAL_SRC_RES;
                }
            }
        }
        t->i_prev[ax] = in->i_mean[ax];
    }
    /* the coil-former NTC is preferred when valid */
    if (in->ntc_valid) {
        t->T_coil += PEN_T_NTC_GAIN * (t->T_ntc - t->T_coil);
        if (t->T_coil < t->T_ntc) {
            t->T_coil = t->T_ntc;   /* the winding is not colder than its former */
        }
        t->source = THERMAL_SRC_NTC;
    }
    t->derate = pen_clampf((PEN_T_FAULT - t->T_coil) / (PEN_T_FAULT - PEN_T_DERATE_START), 0.0f, 1.0f);
    if (t->T_coil >= PEN_T_FAULT) {
        t->over_temp = true;
    } else if (t->T_coil < PEN_T_RECOVER) {
        t->over_temp = false;
    }
}
