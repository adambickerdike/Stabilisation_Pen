/*
 * hall.c - Hall conversion (see header).
 * Status: PROPOSED DESIGN; placeholder calibration (VERIFY, EXP-B04).
 */
#include "hall.h"

#include <string.h>

#include "params_gen.h"

#define HALL_RANGE_T 0.025f        /* TMAG5170A1 +/-25 mT range setting (VERIFY) */
#define HALL_GRADIENT_T_PER_M 40.0f /* assumed field gradient at the sensor (VERIFY, EXP-B04) */

void cal_hall_default(cal_hall_t *c)
{
    memset(c, 0, sizeof(*c));
    c->lsb_T = HALL_RANGE_T / 32768.0f;
    c->m[0][0] = 1.0f / HALL_GRADIENT_T_PER_M;
    c->m[1][1] = 1.0f / HALL_GRADIENT_T_PER_M;
    c->m[2][2] = 1.0f / HALL_GRADIENT_T_PER_M;
    c->k_ax = PEN_K_AX;
    c->f_pre = PEN_F_PRE;
}

void hall_convert(const cal_hall_t *c, const int16_t raw[3], const float i_meas[2], float q[2], float *s, float *f_ax)
{
    float B[3];
    for (int k = 0; k < 3; k++) {
        B[k] = c->lsb_T * (float)raw[k] - (c->ict[k][0] * i_meas[0] + c->ict[k][1] * i_meas[1]) - c->b0[k];
    }
    float y[3];
    for (int j = 0; j < 3; j++) {
        const float v = c->m[j][0] * B[0] + c->m[j][1] * B[1] + c->m[j][2] * B[2];
        y[j] = v + c->c3[j] * v * v * v;
    }
    q[0] = y[0];
    q[1] = y[1];
    /* the axial suspension rests on its front stop without contact: s >= 0 */
    const float sv = (y[2] > 0.0f) ? y[2] : 0.0f;
    *s = sv;
    *f_ax = c->f_pre + c->k_ax * sv;
}
