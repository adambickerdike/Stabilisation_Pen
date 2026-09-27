/*
 * thermal.h - two-node coil temperature estimator and derating (proposed design).
 *
 * Network (config/parameters.yaml 0.4.3 actuator.*, derived in
 * results/thermal/thermal.json two_node_governor_model):
 *   coil node (both windings on the moving paddle, one former):
 *       C_c dT_c/dt = P - (T_c - T_s) / R_cs
 *   structure node (iron, magnets, barrel):
 *       C_s dT_s/dt = (T_c - T_s) / R_cs - (T_s - T_ref) / R_sa
 *   P = sum over both axes of <i^2> R20 (1 + alpha_cu (T_c - 20))   (copper tempco)
 *   T_ref = T_amb + T_struct_rise_idle: electronics dissipation and the hand
 *           warm the structure by 5.9 K with no coil loss.
 *   R_cs = actuator.Rth_coil_amb (145 K/W, coil to structure; the key name is
 *   historical), C_c = Cth_coil, R_sa = Rth_struct_amb, C_s = Cth_struct.
 *   Steady state at constant loss: T_c = T_ref + P (R_cs + R_sa), T_s = T_ref + P R_sa.
 *   Time constants (eigenvalues of the coupled network): about 35.5 s and
 *   190 s with the 0.4.3 values; the uncoupled products R_cs C_c and R_sa C_s
 *   are 36 s and 186 s.
 * Measurements, in order of preference:
 *   1. the NTC bonded to the coil former (AIN3, converted by the port at
 *      100 Hz; port/nrf5340 reads it, the host HAL models it): when the
 *      reading is valid the coil node is pulled toward it (T_NTC_GAIN per
 *      update, time constant 0.1 s) and never kept below it. The gradient
 *      from the winding to its former is not modelled (VERIFY EXP-B07).
 *   2. resistance thermometry, only while the NTC is invalid: when the current
 *      is steady and large enough and the stage slow (back-EMF negligible),
 *        R_coil = <duty V_M> / <i> - (r_bridge + r_shunt),
 *        T_R = 20 + (R_coil/R20 - 1)/alpha_cu,   T_c += k_R (T_R - T_c);
 *   3. otherwise the model runs open loop from T_amb (config thermal.t_ambient,
 *      not measured by the pen).
 * The first valid NTC reading initialises both nodes (a warm boot then
 * over-estimates the structure: conservative).
 * Derating (unchanged): authority cap falls linearly from 1 at T_DERATE_START
 * to 0 at T_FAULT; over-temperature condition (fault bit 2) at T_FAULT,
 * cleared below T_RECOVER. All thresholds are proposed (params_gen.h).
 * VERIFY: R/C values, r_bridge spread, NTC coupling (EXP-B07).
 */
#ifndef PEN_THERMAL_H
#define PEN_THERMAL_H

#include <stdbool.h>
#include <stdint.h>

enum { THERMAL_SRC_MODEL = 0, THERMAL_SRC_NTC = 1, THERMAL_SRC_RES = 2 };

typedef struct {
    float T_coil;        /* coil node, degC */
    float T_struct;      /* structure node, degC */
    float T_ref;         /* structure reference T_amb + T_struct_rise_idle, degC */
    float c_coil, c_struct;  /* compensated-summation terms of the integration (float32) */
    float P;             /* copper loss of the last step, W */
    float T_ntc;         /* last valid NTC temperature, degC */
    bool ntc_valid;
    bool ntc_seen;       /* nodes initialised from the NTC */
    float R_est[2];      /* last resistance estimate, ohm (0 = none yet) */
    float T_res[2];      /* temperature implied by R_est, degC */
    bool res_used[2];    /* resistance correction applied this step */
    float i_prev[2];
    uint8_t source;      /* THERMAL_SRC_* that corrected the coil node in the last step */
    float derate;        /* authority cap 0..1 */
    bool over_temp;      /* over-temperature condition (hysteresis) */
} thermal_t;

typedef struct {
    float i2_mean[2];    /* mean of i^2 over the step, A^2 (copper loss) */
    float i_mean[2];     /* mean current of the last stage tick, A (resistance thermometry) */
    float v_mean[2];     /* mean applied bridge voltage duty*V_M of the last stage tick, V */
    float stage_speed;   /* |q'|, m/s */
    float ntc_degC;
    bool ntc_valid;
} thermal_in_t;

/* Both nodes start at T0; T_ref = PEN_T_AMB + PEN_T_STRUCT_RISE_IDLE. */
void thermal_init(thermal_t *t, float T0);
float thermal_r_coil(float T);
/* One estimator step (100 Hz in the application). */
void thermal_step(thermal_t *t, float dt, const thermal_in_t *in);
/* Network integration only, for a given copper loss P (W); used by thermal_step and the tests. */
void thermal_network_step(thermal_t *t, float dt, float P);
/* NTC temperature from the ratiometric reading x = V_ntc / V_supply (0..1).
 * Returns false (and leaves *T) if the reading is outside a plausible range. */
bool thermal_ntc_degC(float x, float *T);

#endif /* PEN_THERMAL_H */
