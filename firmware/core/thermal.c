/*
 * thermal.c - coil temperature observer (see header).
 * Status: PROPOSED DESIGN, host unit tests on synthetic data only.
 */
#include "thermal.h"

#include <math.h>
#include <string.h>

#include "mathx.h"
#include "params_gen.h"

#define THERMAL_STAGE_SPEED_MAX 0.005f  /* m/s: back-EMF n Kf v < 12 mV (proposed) */
#define THERMAL_IDLE_I 0.05f            /* A: both coils "idle" for NTC relaxation (proposed) */

void thermal_init(thermal_t *t, float T0)
{
    memset(t, 0, sizeof(*t));
    t->T[0] = T0;
    t->T[1] = T0;
    t->T_ntc = T0;
    t->derate = 1.0f;
    t->t_amb = PEN_T_AMB;
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

void thermal_step(thermal_t *t, float dt, const float i_mean[2], const float v_mean[2], float stage_speed,
                  float ntc_degC, bool ntc_valid)
{
    const float r_ext = PEN_R_BRIDGE + PEN_R_SHUNT;
    t->ntc_valid = ntc_valid;
    if (ntc_valid) {
        t->T_ntc = ntc_degC;
    }
    const bool idle = (pen_absf(i_mean[0]) < THERMAL_IDLE_I) && (pen_absf(i_mean[1]) < THERMAL_IDLE_I);
    for (int ax = 0; ax < 2; ax++) {
        /* model prediction (explicit Euler; dt/(R_th C_th) << 1) */
        const float P = i_mean[ax] * i_mean[ax] * thermal_r_coil(t->T[ax]);
        t->T[ax] += dt / PEN_CTH_COIL * (P - (t->T[ax] - t->t_amb) / PEN_RTH_COIL);
        /* resistance thermometry */
        t->res_used[ax] = false;
        const float ia = pen_absf(i_mean[ax]);
        const bool steady = pen_absf(i_mean[ax] - t->i_prev[ax]) < PEN_R_EST_DI_MAX;
        if (ia > PEN_R_EST_I_MIN && steady && stage_speed < THERMAL_STAGE_SPEED_MAX) {
            const float r_coil = v_mean[ax] / i_mean[ax] - r_ext;
            if (r_coil > 0.5f * PEN_R20 && r_coil < 2.0f * PEN_R20) {   /* plausibility (-107..+274 degC) */
                t->R_est[ax] = r_coil;
                t->T_res[ax] = 20.0f + (r_coil / PEN_R20 - 1.0f) / PEN_ALPHA_CU;
                t->T[ax] += PEN_T_RES_GAIN * (t->T_res[ax] - t->T[ax]);
                t->res_used[ax] = true;
            }
        }
        t->i_prev[ax] = i_mean[ax];
        /* NTC fusion: lower bound always; relaxation when idle */
        if (ntc_valid) {
            if (t->T[ax] < t->T_ntc) {
                t->T[ax] = t->T_ntc;
            } else if (idle) {
                t->T[ax] += PEN_T_NTC_GAIN * (t->T_ntc - t->T[ax]);
            }
        }
    }
    const float tmax = thermal_max(t);
    t->derate = pen_clampf((PEN_T_FAULT - tmax) / (PEN_T_FAULT - PEN_T_DERATE_START), 0.0f, 1.0f);
    if (tmax >= PEN_T_FAULT) {
        t->over_temp = true;
    } else if (tmax < PEN_T_RECOVER) {
        t->over_temp = false;
    }
}
