/*
 * app.h - firmware application layer: 40 kHz current ISR body and 2 kHz
 * stage task body, shared by the nRF5340 port (port/nrf5340/scheduler.c)
 * and the host system tests (tests/test_system.c).
 *
 * Stage task order (ICD s2 "Hall read -> estimator -> servo -> current
 * references"): sensors -> Hall conversion + checks -> fusion -> slow
 * channels (100 Hz: VBAT, NTC, thermal) -> fault detections -> state machine
 * -> control tick -> actuator policy -> ML window -> logging.
 * Status: PROPOSED DESIGN; host-tested with the C plant, compile-tested for
 * the nRF5340 application core. Not run on hardware.
 */
#ifndef PEN_APP_H
#define PEN_APP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "calib.h"
#include "control.h"
#include "current_loop.h"
#include "fusion.h"
#include "hall.h"
#include "log_format.h"
#include "ml_guard.h"
#include "safety.h"
#include "state_machine.h"
#include "thermal.h"

#define APP_IREF_HIST 32u   /* ticks of current-reference history (Hall fault hold) */
#define APP_HOLD_AVG 16u    /* the open-loop hold uses the mean of 16 ticks (8 ms) before the stuck run */
#define APP_SLOW_DECIM 20u  /* VBAT/NTC/thermal every 20 ticks = 100 Hz */

typedef void (*pen_log_sink_t)(const uint8_t *rec, size_t len, void *ctx);

/* sensor data gathered by the port for one stage tick */
typedef struct {
    int16_t hall_raw[3];
    bool hall_fresh;
    float opt_p[2];          /* combined optical page position, m (delayed by the sensor) */
    bool opt_valid;
    uint8_t opt_valid_bits;  /* per module, for the log */
    bool opt_surface_lost;   /* all modules report lift (pen-up source during a Hall fault) */
    float imu_a_page[2];     /* page-plane acceleration of the last IMU sample, m/s^2 */
    float imu_acc_h[3];      /* housing-frame specific force, m/s^2 */
    float imu_gyro_h[3];     /* housing-frame rate, rad/s */
    uint8_t imu_n;           /* IMU samples since the last tick (fusion integrates each) */
    float imu_dt;            /* s per IMU sample */
    float imu_a_page_seq[8][2];  /* the samples themselves (<= 8) */
} pen_sensors_t;

/* user / host requests */
typedef struct {
    bool arm, disarm, off;
    pen_mode_t assist;       /* requested assist mode */
} pen_requests_t;

typedef struct {
    /* modules */
    ctrl_t ctrl;
    curloop_t cl;
    thermal_t th;
    safety_t sf;
    sm_t sm;
    ml_guard_t mlg;
    ml_window_t mlw;
    fusion_t fu;
    cal_hall_t hall_cal;
    cal_user_t user;
    pen_requests_t req;
    bool ml_available;
    /* ISR <-> task shared data (single core: aligned 32-bit accesses are atomic;
     * the accumulators are swapped inside a short critical section) */
    volatile float iref_cmd[2];
    volatile bool cl_enable;
    volatile float vbat_f;
    float r_extra[2];
    struct {
        float i_sum[2], v_sum[2], duty_abs_max;
        uint32_t n;
        bool vsat;
    } acc;
    uint32_t isr_count;
    uint32_t isr_count_seen;
    /* stage task state */
    uint32_t tick;
    float q[2], s, f_ax;
    float ph[2];
    bool opt_valid;
    float i_mean[2];
    float th_i2_sum[2];      /* sum of i_mean^2 over the ticks since the last thermal step */
    uint32_t th_n;
    bool in_contact;
    bool pen_up;
    float t_no_contact;      /* s without contact */
    float t_lost;            /* s with the optical surface lost */
    bool offset_cal_pending;
    float iref_hist[APP_IREF_HIST][2];
    uint32_t iref_hist_n;
    float iref_hold[2];
    bool hold_captured;
    float iref_out[2];       /* what the current loop is asked to track */
    uint16_t faults_logged;
    pen_mode_t mode_logged;
    /* session clock (64-bit extension of the hardware us counter) */
    penlog_clock_t clk;
    /* capture layer: 200 Hz stroke samples plus exact pen-down / pen-up samples */
    uint32_t stroke_id;
    bool page_origin_set;
    float page_origin[2];     /* deposited-ink page position at the first pen-down */
    bool cap_prev_contact;
    bool cap_last_emitted;
    uint32_t cap_phase;
    penlog_stroke_t cap_last;
    uint32_t n_stroke_boundary;
    /* logging */
    pen_log_sink_t sink;
    void *sink_ctx;
    bool log_research;
    uint32_t log_drops;
} pen_app_t;

/* ML inference hook (ICD s5 v1.2), called at 250 Hz from the stage task when a
 * validated model is available. dp_um: 64 x (dx, dy) increments, oldest
 * first, stamped at acquisition. f_est_hz: the Kalman frequency estimate; the
 * exported v1 C model (ml/export/tcn_int8.h, tcn_predict()) still takes it as
 * a third input channel (ICD s5 artefact status, README D12); models of the
 * v1.1+ contract ignore it. Returns false if no model is linked (weak default). */
typedef struct {
    float d_um[2];       /* predicted disturbance at t_acq_newest + 6 ms, um */
    float confidence;    /* output byte / 255; 1 for a model without a confidence output */
    bool nan_or_inf;     /* kernel status */
    bool saturated;      /* int8 output saturation */
} pen_ml_out_t;
bool pen_ml_predict(const float dp_um[PEN_ML_WINDOW][2], float f_est_hz, pen_ml_out_t *out);

void pen_app_init(pen_app_t *a, pen_profile_t profile, bool reset_by_watchdog);
void pen_app_set_sink(pen_app_t *a, pen_log_sink_t sink, void *ctx, bool research_frames);
/* 40 kHz: SAADC END interrupt (centre + edge samples of this period). */
void pen_app_current_isr(pen_app_t *a, const int16_t adc_c[2], const int16_t adc_e[2]);
/* 2 kHz: stage task. */
void pen_app_stage_tick(pen_app_t *a, const pen_sensors_t *sens);
/* Apply a CAL_USER record (validated) and log event 0x0004. */
bool pen_app_apply_user_cal(pen_app_t *a, const cal_user_t *u);

#endif /* PEN_APP_H */
