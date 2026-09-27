/*
 * current_loop.c - coil current PI and bridge mapping (see header).
 * Status: PROPOSED DESIGN; host-tested on a switched RL + stage plant
 * (tests/test_current_loop.c, tests/test_closed_loop.c). Not run on hardware.
 */
#include "current_loop.h"

#include <math.h>
#include <string.h>

#include "mathx.h"

void cl_init(curloop_t *cl)
{
    memset(cl, 0, sizeof(*cl));
    cl->vm = PEN_V_BAT_NOM;
    cl->dither_on = true;
}

float cl_adc_to_amps(int16_t code)
{
    const float volts = (float)code * (PEN_SAADC_DIFF_FS_V / (float)(1 << (PEN_SAADC_BITS - 1)));
    return volts / PEN_ISNS_V_PER_A;
}

void cl_duty_to_bridge(float duty, float duty_max, bridge_cmd_t *b, float *duty_applied)
{
    const float top = (float)PEN_PWM_COUNTERTOP;
    const float d = pen_clampf(duty, -duty_max, duty_max);
    const long n_max = (long)floorf(duty_max * top);
    long n = lrintf(pen_absf(d) * top);
    if (n > n_max) {
        n = n_max;
    }
    const uint16_t n_brake = (uint16_t)(PEN_PWM_COUNTERTOP - n);
    if (d >= 0.0f) {
        b->in1_high = (uint16_t)PEN_PWM_COUNTERTOP;
        b->in2_high = n_brake;
        *duty_applied = (float)n / top;
    } else {
        b->in1_high = n_brake;
        b->in2_high = (uint16_t)PEN_PWM_COUNTERTOP;
        *duty_applied = -(float)n / top;
    }
}

void cl_request_offset_cal(curloop_t *cl)
{
    cl->cal_state = CL_CAL_SETTLE;
    cl->cal_count = 0;
    cl->cal_acc[0] = 0.0f;
    cl->cal_acc[1] = 0.0f;
}

static void coast(curloop_t *cl, bridge_cmd_t out[2])
{
    for (int ax = 0; ax < 2; ax++) {
        out[ax].in1_high = 0;
        out[ax].in2_high = 0;
        cl->ivint[ax] = 0.0f;
        cl->v_cmd[ax] = 0.0f;
        cl->duty[ax] = 0.0f;
        cl->dither[ax] = 0.0f;
        cl->vsat[ax] = false;
    }
}

void cl_step(curloop_t *cl, const pen_ctrl_params_t *p, const float i_ref[2], const int16_t adc_c[2],
             const int16_t adc_e[2], float vbat, const float r_extra[2], bridge_cmd_t out[2])
{
    float raw[2];
    for (int ax = 0; ax < 2; ax++) {
        raw[ax] = 0.5f * (cl_adc_to_amps(adc_c[ax]) + cl_adc_to_amps(adc_e[ax]));
        cl->i_meas[ax] = raw[ax] - cl->offset[ax];
    }
    /* --- offset calibration window: bridges coast, I -> 0 --- */
    if (cl->cal_state != CL_CAL_IDLE) {
        coast(cl, out);
        cl->cal_count++;
        if (cl->cal_state == CL_CAL_SETTLE) {
            if (cl->cal_count >= CL_CAL_SETTLE_PERIODS) {
                cl->cal_state = CL_CAL_MEASURE;
                cl->cal_count = 0;
            }
        } else {
            cl->cal_acc[0] += raw[0];
            cl->cal_acc[1] += raw[1];
            if (cl->cal_count >= CL_CAL_MEASURE_PERIODS) {
                const float o0 = cl->cal_acc[0] / (float)CL_CAL_MEASURE_PERIODS;
                const float o1 = cl->cal_acc[1] / (float)CL_CAL_MEASURE_PERIODS;
                cl->cal_ok = (pen_absf(o0) <= PEN_ISNS_OFFSET_MAX_A) && (pen_absf(o1) <= PEN_ISNS_OFFSET_MAX_A);
                if (cl->cal_ok) {
                    cl->offset[0] = o0;
                    cl->offset[1] = o1;
                }
                cl->cal_state = CL_CAL_IDLE;
                cl->cal_done = true;
            }
        }
        return;
    }
    if (!cl->enabled) {
        coast(cl, out);
        return;
    }
    /* --- bridge supply estimate and voltage limit --- */
    const float vm = pen_maxf(vbat - PEN_R_LOAD_SWITCH * (pen_absf(cl->i_meas[0]) + pen_absf(cl->i_meas[1])), 0.5f);
    cl->vm = vm;
    const float vmax = p->duty_max * vm;
    for (int ax = 0; ax < 2; ax++) {
        const float e = i_ref[ax] - cl->i_meas[ax];
        const float r_ff = p->r_loop_ff + ((r_extra != NULL) ? r_extra[ax] : 0.0f);
        const float vcmd = r_ff * i_ref[ax] + p->kp_i * e + p->ki_i * cl->ivint[ax];
        const float vsat = pen_clampf(vcmd, -vmax, vmax);
        if (vsat == vcmd) {
            cl->ivint[ax] += e * PEN_TS_CURRENT;
            cl->vsat[ax] = false;
        } else {
            cl->vsat[ax] = true;
            cl->vsat_sticky = true;
        }
        cl->v_cmd[ax] = vsat;
        float d = vsat / vm;
        if (cl->dither_on) {
            d += cl->dither[ax];
        }
        float d_applied;
        cl_duty_to_bridge(d, p->duty_max, &out[ax], &d_applied);
        if (cl->dither_on) {
            /* error feedback, bounded to one LSB so clamping cannot wind it up */
            const float lsb = 1.0f / (float)PEN_PWM_COUNTERTOP;
            cl->dither[ax] = pen_clampf(d - d_applied, -lsb, lsb);
        }
        cl->duty[ax] = d_applied;
        const float ad = pen_absf(d_applied);
        if (ad > cl->duty_abs_max_sticky) {
            cl->duty_abs_max_sticky = ad;
        }
    }
}
