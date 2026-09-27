/*
 * state_machine.h - operating modes and safety states, ICD section 6.
 *
 *   OFF -> STANDBY -> NEUTRAL_HOLD -> ASSIST_KF | ASSIST_ML | GUIDED | TRAINING_FADE
 *   any state (except OFF) -> SAFE_PASSIVE on a fault
 *   SAFE_PASSIVE -> STANDBY only after pen-up and a successful self-check
 *
 * Actuator policy while a fault is latched (ICD s6 rules from sim F1-F7):
 *   faults 0 (over-current), 5 (watchdog), 7 (charging): VMOT is already
 *       removed by hardware -> coast immediately (SM_ACT_OFF).
 *   fault 1 (Hall frozen/implausible): hold the last good current references
 *       open loop (SM_ACT_HOLD_OL) until pen-up, then ramp down (>= 30 ms,
 *       REQ-SAF-004). Pen-up cannot come from F_ax here (same TMAG5170), so
 *       the caller supplies an optical-lift based pen-up; timeout 5 s.
 *   soft faults 2, 3, 4, 6, 8: fade authority to zero and keep the closed-loop
 *       neutral hold (SM_ACT_NEUTRAL) until pen-up or the 5 s timeout, then
 *       ramp down and coast.
 * Transition table: README section "State machine" and tests/test_state_machine.c.
 */
#ifndef PEN_STATE_MACHINE_H
#define PEN_STATE_MACHINE_H

#include <stdbool.h>
#include <stdint.h>

#include "pen_types.h"

typedef enum {
    SM_ACT_OFF = 0,      /* bridges coast, ACT_EN_REQ low */
    SM_ACT_SERVO,        /* closed-loop servo, authority per mode */
    SM_ACT_NEUTRAL,      /* closed-loop servo, authority forced to 0 (fault fade) */
    SM_ACT_HOLD_OL,      /* frozen current references (Hall fault) */
    SM_ACT_RAMP          /* current references scaled 1 -> 0 over RAMP_DOWN_TIME */
} sm_act_t;

/* CAL_USER mode-permission bits */
enum {
    SM_PERM_KF = 1u << 0,
    SM_PERM_ML = 1u << 1,
    SM_PERM_GUIDED = 1u << 2,
    SM_PERM_TRAINING = 1u << 3
};
#define SM_PERM_DEFAULT (SM_PERM_KF | SM_PERM_GUIDED | SM_PERM_TRAINING)

typedef struct {
    float dt;
    bool boot_ok;
    bool pen_up;            /* debounced pen-up (caller chooses the source) */
    bool arm_req;           /* STANDBY -> NEUTRAL_HOLD */
    bool disarm_req;        /* -> STANDBY (at pen-up) */
    bool off_req;           /* -> OFF (at pen-up) */
    pen_mode_t assist_req;  /* NEUTRAL_HOLD / ASSIST_KF / ASSIST_ML / GUIDED / TRAINING_FADE; others ignored */
    uint16_t faults;        /* latched fault bits (safety_t.faults) */
    bool self_check_ok;     /* safety_self_check() */
    bool power_ok;          /* battery OK and not charging (arming precondition) */
    uint8_t mode_perm;      /* SM_PERM_* from CAL_USER */
    bool ml_available;      /* validated model loaded */
} sm_in_t;

typedef struct {
    pen_mode_t mode;
    pen_mode_t prev_mode;
    sm_act_t act;
    bool act_en_req;        /* request actuator power */
    float g_cap;            /* authority cap from the state machine (0..1) */
    float ramp;             /* current-reference scale in SM_ACT_RAMP */
    bool mode_changed;      /* this tick */
    bool clear_faults;      /* this tick: caller must call safety_clear() */
    uint16_t faults_handled;/* fault bits already acted upon */
    float t_wait;           /* s waiting for pen-up in SAFE_PASSIVE */
    float t_mode;           /* s in the current mode */
    pen_mode_t pending;     /* STANDBY/OFF after a ramp-down, else PEN_MODE_COUNT */
    bool disarm_pending;
    float train_t;          /* s of pen-down time in TRAINING_FADE */
} sm_t;

/* TRAINING_FADE schedule (proposed; ICD does not define it): authority cap
 * falls linearly from 1 to SM_TRAIN_G_END over SM_TRAIN_T of assisted time. */
#define SM_TRAIN_G_END 0.2f
#define SM_TRAIN_T 60.0f

void sm_init(sm_t *sm);
void sm_step(sm_t *sm, const sm_in_t *in);
bool sm_mode_permitted(pen_mode_t m, uint8_t perm, bool ml_available);
const char *sm_mode_name(pen_mode_t m);

#endif /* PEN_STATE_MACHINE_H */
