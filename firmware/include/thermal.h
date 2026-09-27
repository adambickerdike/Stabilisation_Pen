/*
 * thermal.h - coil temperature observer and derating (proposed design).
 *
 * Model (per axis, as the simulator): C dT/dt = i^2 R(T) - (T - T_amb)/R_th,
 * R(T) = R20 (1 + alpha_cu (T - 20)).
 * Corrections:
 *  - resistance thermometry when the current is steady and large enough and
 *    the stage is slow (back-EMF negligible):
 *        R_coil = <duty V_M> / <i> - (r_bridge + r_shunt),
 *        T_R = 20 + (R_coil/R20 - 1)/alpha_cu,   T += k_R (T_R - T);
 *  - NTC on the coil former (one sensor for both coils): the coil cannot be
 *    colder than its former, so T = max(T, T_ntc); when both coils carry
 *    (almost) no current the estimate relaxes toward T_ntc.
 * Derating: authority cap falls linearly from 1 at T_DERATE_START to 0 at
 * T_FAULT; over-temperature condition (fault bit 2) at T_FAULT, cleared
 * below T_RECOVER. All thresholds are proposed (params_gen.h).
 * VERIFY: R_th, C_th (config says 60 K/W, 0.25 J/K; the thermal network in
 * results/thermal implies ~190 K/W for the moving coil, README D6),
 * r_bridge spread, NTC coupling (EXP-B07).
 */
#ifndef PEN_THERMAL_H
#define PEN_THERMAL_H

#include <stdbool.h>

typedef struct {
    float T[2];          /* estimated coil temperature, degC */
    float T_ntc;         /* last NTC temperature, degC */
    bool ntc_valid;
    float R_est[2];      /* last resistance estimate, ohm (0 = none yet) */
    float T_res[2];      /* temperature implied by R_est, degC */
    bool res_used[2];    /* resistance correction applied this step */
    float i_prev[2];
    float derate;        /* authority cap 0..1 */
    bool over_temp;      /* over-temperature condition (hysteresis) */
    float t_amb;         /* ambient used by the model, degC */
} thermal_t;

void thermal_init(thermal_t *t, float T0);
float thermal_r_coil(float T);
/* One observer step. i_mean, v_mean: per-axis mean current (A) and mean
 * applied bridge voltage duty*V_M (V) over dt; stage_speed: |q'| (m/s). */
void thermal_step(thermal_t *t, float dt, const float i_mean[2], const float v_mean[2], float stage_speed,
                  float ntc_degC, bool ntc_valid);
/* NTC temperature from the ratiometric reading x = V_ntc / V_supply (0..1).
 * Returns false (and leaves *T) if the reading is outside a plausible range. */
bool thermal_ntc_degC(float x, float *T);
static inline float thermal_max(const thermal_t *t) { return (t->T[0] > t->T[1]) ? t->T[0] : t->T[1]; }

#endif /* PEN_THERMAL_H */
