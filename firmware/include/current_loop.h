/*
 * current_loop.h - 40 kHz per-axis coil current PI (port of the simulator's
 * current loop) with the Rev A bridge mapping.
 *
 *   v = R_ff i_ref + Kp_i e + Ki_i int(e),  e = i_ref - i_meas
 *   |v| <= duty_max * V_M,  V_M = VBAT - R_ls (|i_x| + |i_y|)     (duty <= 0.97)
 *   anti-windup: conditional integration (no integration while clamped),
 *   exactly as sim/pensim/core.py.
 *   duty = v / V_M, quantised to 1/200 (centre-aligned PWM, 200 levels) with
 *   first-order error feedback (sub-LSB dither, proposed).
 *
 * Bridge mapping (DRV8212P IN/IN, drive/brake slow decay; truth table VERIFY:
 * 00 coast, 10 forward OUT1=H, 01 reverse OUT2=H, 11 brake low-side):
 *   duty > 0 : IN1 = 1 for the whole period, IN2 = 1 during the brake phase
 *   duty < 0 : IN2 = 1 for the whole period, IN1 = 1 during the brake phase
 *   brake phase = (1 - |duty|) of the period, centred on the period edge, so
 *   the drive phase is centred on the period centre where the SAADC samples
 *   (the second sample at the period edge is the middle of the brake phase).
 *   coast    : IN1 = IN2 = 0 (offset calibration at pen-up, faults).
 * NOTE: electronics/gen/design_revA.py (actuator sheet note) and the SPICE
 * deck describe "PWM on one input, other low" as drive/brake; with the
 * DRV8212P truth table above that is drive/COAST (README discrepancy D3).
 *
 * Positive current = OUT1 -> shunt -> coil -> OUT2 (ISNS above VREF; VERIFY
 * INA241 pin polarity in the schematic).
 */
#ifndef PEN_CURRENT_LOOP_H
#define PEN_CURRENT_LOOP_H

#include <stdbool.h>
#include <stdint.h>

#include "params.h"

typedef struct {
    uint16_t in1_high;   /* PWM counts (0..PEN_PWM_COUNTERTOP) IN1 is high, centred on the period edge */
    uint16_t in2_high;   /* idem IN2 */
} bridge_cmd_t;

typedef enum { CL_CAL_IDLE = 0, CL_CAL_SETTLE = 1, CL_CAL_MEASURE = 2 } cl_cal_state_t;

typedef struct {
    float ivint[2];          /* PI integrator, A s */
    float i_meas[2];         /* A, offset-corrected mean of centre and edge samples */
    float v_cmd[2];          /* V after clamp */
    float duty[2];           /* signed duty applied (quantised) */
    float dither[2];         /* error-feedback state */
    float vm;                /* estimated bridge supply, V */
    bool vsat[2];
    bool vsat_sticky;        /* any clamp since the stage task last read it */
    float duty_abs_max_sticky;
    float offset[2];         /* current-sense offset, A */
    /* offset calibration sequencer (bridge coast at pen-up) */
    cl_cal_state_t cal_state;
    uint16_t cal_count;
    float cal_acc[2];
    bool cal_done;           /* set when a calibration finished (read & clear by caller) */
    bool cal_ok;             /* result of the last calibration */
    bool enabled;            /* false: coast, integrators reset */
    bool dither_on;
} curloop_t;

#define CL_CAL_SETTLE_PERIODS 10u   /* 250 us >> L/R = 29 us (proposed) */
#define CL_CAL_MEASURE_PERIODS 16u  /* 16 periods x (centre + edge) = 32 samples */

void cl_init(curloop_t *cl);
/* SAADC differential code (signed 12-bit) -> amps before offset removal. */
float cl_adc_to_amps(int16_t code);
/* Signed duty -> IN1/IN2 high times (duty clamped to +/- duty_max, quantised). */
void cl_duty_to_bridge(float duty, float duty_max, bridge_cmd_t *b, float *duty_applied);
/* Request a current-sense offset calibration (caller guarantees pen-up). */
void cl_request_offset_cal(curloop_t *cl);
/* One PWM period. adc_c/adc_e: centre/edge codes per axis, vbat: volts,
 * r_extra: optional per-axis resistance added to the R feedforward (e.g. the
 * thermal rise R20 alpha (T - 20)); may be NULL. */
void cl_step(curloop_t *cl, const pen_ctrl_params_t *p, const float i_ref[2], const int16_t adc_c[2],
             const int16_t adc_e[2], float vbat, const float r_extra[2], bridge_cmd_t out[2]);

#endif /* PEN_CURRENT_LOOP_H */
