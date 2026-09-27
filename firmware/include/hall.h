/*
 * hall.h - TMAG5170 3-axis Hall -> stage position (q1, q2), axial slide s
 * and axial force F_ax = F_pre + k_ax s (electronics/gen/design_revA.py
 * sheet_stage_position; ICD s3 CAL_HALL / CAL_AXIAL).
 *
 *   B   = lsb_T * raw - ict * i          (current crosstalk, T/A)
 *   y   = M (B - b0)                     (3x3 linear map, m/T)
 *   out = y + c3 .* y^3                  (odd cubic correction per axis)
 *   (q1, q2, s) = out
 * The default map is an UNCALIBRATED placeholder (assumed 40 mT/mm field
 * gradient, +/-25 mT range) until EXP-B04; every value is VERIFY.
 */
#ifndef PEN_HALL_H
#define PEN_HALL_H

#include <stdint.h>

typedef struct {
    float lsb_T;      /* tesla per LSB */
    float b0[3];      /* T */
    float m[3][3];    /* m/T */
    float c3[3];      /* 1/m^2 */
    float ict[3][2];  /* T/A */
    float k_ax;       /* N/m (CAL_AXIAL) */
    float f_pre;      /* N   (CAL_AXIAL) */
} cal_hall_t;

void cal_hall_default(cal_hall_t *c);
void hall_convert(const cal_hall_t *c, const int16_t raw[3], const float i_meas[2], float q[2], float *s, float *f_ax);

#endif /* PEN_HALL_H */
