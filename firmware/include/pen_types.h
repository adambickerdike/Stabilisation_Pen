/*
 * pen_types.h - shared enumerations of the ICD (docs/icd.md v1.3).
 *
 * Status: PROPOSED DESIGN (research prototype Rev A). Nothing here is
 * validated on hardware.
 */
#ifndef PEN_TYPES_H
#define PEN_TYPES_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* ---- Fault bits, ICD section 6 (bit positions are part of the contract) ---- */
enum {
    PEN_FAULT_OVERCURRENT = 1u << 0, /* hardware over-current latch (FAULT_N low)      - hard */
    PEN_FAULT_HALL        = 1u << 1, /* Hall frozen / implausible                     - hard */
    PEN_FAULT_OVERTEMP    = 1u << 2, /* coil over-temperature                         - soft */
    PEN_FAULT_LOWBAT      = 1u << 3, /* low battery                                   - soft */
    PEN_FAULT_OPTICAL     = 1u << 4, /* optical invalid > 300 ms                      - soft */
    PEN_FAULT_WATCHDOG    = 1u << 5, /* watchdog reset                                - hard */
    PEN_FAULT_HEADROOM    = 1u << 6, /* duty > 0.95 for > 50 ms                       - soft */
    PEN_FAULT_CHARGING    = 1u << 7, /* charging interlock (VMOT removed by hardware) - hw  */
    PEN_FAULT_MLGUARD     = 1u << 8  /* ML guard trip count exceeded                  - soft */
};
#define PEN_FAULT_ALL_MASK  (0x01FFu)
/* ICD s6: "never de-energise the stage while in contact except on hard faults (0, 1, 5)" */
#define PEN_FAULT_HARD_MASK (PEN_FAULT_OVERCURRENT | PEN_FAULT_HALL | PEN_FAULT_WATCHDOG)
/* Faults for which the hardware has already removed VMOT (nothing firmware can hold). */
#define PEN_FAULT_VMOT_LOST_MASK (PEN_FAULT_OVERCURRENT | PEN_FAULT_WATCHDOG | PEN_FAULT_CHARGING)

/* ---- Modes, ICD section 6. The numeric codes are the `mode` byte of the
 * research frame (ICD s4.2) and the event 0x0001 arg; ICD v1.3 s6 adopted
 * this numbering. ---- */
typedef enum {
    PEN_MODE_OFF = 0,
    PEN_MODE_STANDBY = 1,
    PEN_MODE_NEUTRAL_HOLD = 2,
    PEN_MODE_ASSIST_KF = 3,
    PEN_MODE_ASSIST_ML = 4,
    PEN_MODE_GUIDED = 5,
    PEN_MODE_TRAINING_FADE = 6,
    PEN_MODE_SAFE_PASSIVE = 7,
    PEN_MODE_COUNT = 8
} pen_mode_t;

/* ---- Research-frame flag bits, ICD s4.2 ---- */
enum {
    PEN_FLAG_CONTACT = 1u << 0,
    PEN_FLAG_LIFT = 1u << 1,
    PEN_FLAG_VSAT = 1u << 2,
    PEN_FLAG_STOP = 1u << 3,
    PEN_FLAG_FAULT = 1u << 4,
    PEN_FLAG_ML_ACTIVE = 1u << 5,
    PEN_FLAG_ML_REJECTED = 1u << 6,
    PEN_FLAG_THERMAL_DERATE = 1u << 7
};

/* ---- Event codes, ICD s4.4 ---- */
enum {
    PEN_EV_MODE_CHANGE = 0x0001,
    PEN_EV_FAULT_SET = 0x0002,
    PEN_EV_FAULT_CLEARED = 0x0003,
    PEN_EV_CAL_APPLIED = 0x0004,
    PEN_EV_ML_LOADED = 0x0005,
    PEN_EV_AUTHORITY_CAPPED = 0x0006,
    PEN_EV_PEN_DOWN = 0x0007,
    PEN_EV_PEN_UP = 0x0008,
    PEN_EV_TIME_WRAP = 0x0009,       /* arg = cumulative wrap count */
    /* ICD v1.2: defined for the decoder; Rev A firmware does not emit them yet
     * (no coded-paper page id, no sync input on the Rev A pin plan) */
    PEN_EV_PAGE_SET = 0x000A,        /* arg = page id */
    PEN_EV_SYNC_PULSE = 0x000B       /* arg = pulse counter (bench rigs) */
};

/* ---- Estimator used by the stage task (maps to simulator modes) ---- */
typedef enum {
    PEN_EST_NONE = 0,   /* neutral hold (sim mode 1) */
    PEN_EST_BPF = 1,    /* band-pass + extrapolation (sim mode 2) */
    PEN_EST_KF = 2,     /* Kalman intent + oscillator (sim mode 3) */
    PEN_EST_ML = 3,     /* ML predictor with KF fallback (ICD s5) */
    PEN_EST_GUIDED = 4  /* template following (sim mode 6) */
} pen_est_t;

/* ---- Parameter profiles (results/sim/estimator_selection.json) ---- */
typedef enum {
    PEN_PROFILE_BALANCED = 0,  /* "selected" (lambda_d = 1), firmware default */
    PEN_PROFILE_ASSERTIVE = 1  /* "selected_assertive" (lambda_d = 0.3) */
} pen_profile_t;

#endif /* PEN_TYPES_H */
