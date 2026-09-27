/*
 * state_machine.c - modes and safety states (see header).
 * Status: PROPOSED DESIGN; transition table host-tested
 * (tests/test_state_machine.c). Not validated on hardware.
 */
#include "state_machine.h"

#include <string.h>

#include "mathx.h"
#include "params_gen.h"

void sm_init(sm_t *sm)
{
    memset(sm, 0, sizeof(*sm));
    sm->mode = PEN_MODE_OFF;
    sm->prev_mode = PEN_MODE_OFF;
    sm->act = SM_ACT_OFF;
    sm->ramp = 1.0f;
    sm->pending = PEN_MODE_COUNT;
}

const char *sm_mode_name(pen_mode_t m)
{
    switch (m) {
    case PEN_MODE_OFF: return "OFF";
    case PEN_MODE_STANDBY: return "STANDBY";
    case PEN_MODE_NEUTRAL_HOLD: return "NEUTRAL_HOLD";
    case PEN_MODE_ASSIST_KF: return "ASSIST_KF";
    case PEN_MODE_ASSIST_ML: return "ASSIST_ML";
    case PEN_MODE_GUIDED: return "GUIDED";
    case PEN_MODE_TRAINING_FADE: return "TRAINING_FADE";
    case PEN_MODE_SAFE_PASSIVE: return "SAFE_PASSIVE";
    case PEN_MODE_COUNT:
    default: return "?";
    }
}

static bool is_assist(pen_mode_t m)
{
    return m == PEN_MODE_ASSIST_KF || m == PEN_MODE_ASSIST_ML || m == PEN_MODE_GUIDED || m == PEN_MODE_TRAINING_FADE;
}

bool sm_mode_permitted(pen_mode_t m, uint8_t perm, bool ml_available)
{
    switch (m) {
    case PEN_MODE_NEUTRAL_HOLD: return true;
    case PEN_MODE_ASSIST_KF: return (perm & SM_PERM_KF) != 0u;
    case PEN_MODE_ASSIST_ML: return ((perm & SM_PERM_ML) != 0u) && ml_available;
    case PEN_MODE_GUIDED: return (perm & SM_PERM_GUIDED) != 0u;
    case PEN_MODE_TRAINING_FADE: return (perm & SM_PERM_TRAINING) != 0u;
    default: return false;
    }
}

static void set_mode(sm_t *sm, pen_mode_t m)
{
    if (m != sm->mode) {
        sm->prev_mode = sm->mode;
        sm->mode = m;
        sm->mode_changed = true;
        sm->t_mode = 0.0f;
    }
}

/* Policy for a set of latched faults, strongest first. */
static sm_act_t fault_policy(uint16_t f)
{
    if ((f & PEN_FAULT_VMOT_LOST_MASK) != 0u) {
        return SM_ACT_OFF;
    }
    if ((f & PEN_FAULT_HALL) != 0u) {
        return SM_ACT_HOLD_OL;
    }
    return SM_ACT_NEUTRAL;
}

static void start_ramp(sm_t *sm)
{
    sm->act = SM_ACT_RAMP;
    sm->ramp = 1.0f;
}

static bool ramp_step(sm_t *sm, float dt)
{
    sm->ramp -= dt / PEN_RAMP_DOWN_TIME;
    if (sm->ramp <= 0.0f) {
        sm->ramp = 0.0f;
        sm->act = SM_ACT_OFF;
        return true;
    }
    return false;
}

void sm_step(sm_t *sm, const sm_in_t *in)
{
    sm->mode_changed = false;
    sm->clear_faults = false;
    sm->t_mode += in->dt;
    const uint16_t f = in->faults;

    /* ---- any state except OFF -> SAFE_PASSIVE on a fault ---- */
    if (f != 0u && sm->mode != PEN_MODE_OFF) {
        if (sm->mode != PEN_MODE_SAFE_PASSIVE) {
            set_mode(sm, PEN_MODE_SAFE_PASSIVE);
            sm->t_wait = 0.0f;
            sm->pending = PEN_MODE_COUNT;
            sm->disarm_pending = false;
            if (sm->act != SM_ACT_OFF) {
                const sm_act_t pol = fault_policy(f);
                if (pol == SM_ACT_OFF) {
                    sm->act = SM_ACT_OFF;
                } else if (in->pen_up) {
                    /* not loaded by the page: de-energise now, with the ramp */
                    sm->act = pol;
                    start_ramp(sm);
                } else {
                    sm->act = pol;
                }
            }
        } else {
            const uint16_t newf = (uint16_t)(f & (uint16_t)~sm->faults_handled);
            if (newf != 0u) {
                const sm_act_t pol = fault_policy(f);
                if (pol == SM_ACT_OFF) {
                    sm->act = SM_ACT_OFF;               /* escalate: VMOT is gone */
                } else if (pol == SM_ACT_HOLD_OL && sm->act == SM_ACT_NEUTRAL) {
                    sm->act = SM_ACT_HOLD_OL;           /* cannot servo without the sensor */
                }
            }
        }
        sm->faults_handled = f;
    }

    switch (sm->mode) {
    case PEN_MODE_OFF:
        sm->act = SM_ACT_OFF;
        if (in->boot_ok) {
            set_mode(sm, PEN_MODE_STANDBY);
        }
        break;

    case PEN_MODE_STANDBY:
        sm->act = SM_ACT_OFF;
        if (in->off_req) {
            set_mode(sm, PEN_MODE_OFF);
        } else if (in->arm_req && in->pen_up && in->power_ok && f == 0u) {
            /* energise only at pen-up: pulling a loaded stage to neutral moves the ink */
            set_mode(sm, PEN_MODE_NEUTRAL_HOLD);
            sm->act = SM_ACT_SERVO;
            sm->ramp = 1.0f;
        }
        break;

    case PEN_MODE_NEUTRAL_HOLD:
    case PEN_MODE_ASSIST_KF:
    case PEN_MODE_ASSIST_ML:
    case PEN_MODE_GUIDED:
    case PEN_MODE_TRAINING_FADE:
        if (in->disarm_req || in->off_req) {
            sm->disarm_pending = true;
            sm->pending = in->off_req ? PEN_MODE_OFF : PEN_MODE_STANDBY;
        }
        if (sm->disarm_pending) {
            set_mode(sm, PEN_MODE_NEUTRAL_HOLD);   /* fade authority, wait for pen-up */
            if (sm->act == SM_ACT_SERVO && in->pen_up) {
                start_ramp(sm);
            }
        } else if (in->assist_req != sm->mode &&
                   (in->assist_req == PEN_MODE_NEUTRAL_HOLD || is_assist(in->assist_req)) &&
                   sm_mode_permitted(in->assist_req, in->mode_perm, in->ml_available)) {
            set_mode(sm, in->assist_req);
            if (in->assist_req == PEN_MODE_TRAINING_FADE) {
                sm->train_t = 0.0f;
            }
        }
        if (sm->act == SM_ACT_RAMP && ramp_step(sm, in->dt)) {
            set_mode(sm, (sm->pending == PEN_MODE_OFF) ? PEN_MODE_OFF : PEN_MODE_STANDBY);
            sm->pending = PEN_MODE_COUNT;
            sm->disarm_pending = false;
        }
        if (sm->mode == PEN_MODE_TRAINING_FADE && !in->pen_up) {
            sm->train_t += in->dt;
        }
        break;

    case PEN_MODE_SAFE_PASSIVE:
        if (sm->act == SM_ACT_NEUTRAL || sm->act == SM_ACT_HOLD_OL) {
            sm->t_wait += in->dt;
            if (in->pen_up || sm->t_wait >= PEN_PENUP_TIMEOUT) {
                start_ramp(sm);
            }
        }
        if (sm->act == SM_ACT_RAMP) {
            (void)ramp_step(sm, in->dt);
        }
        if (sm->act == SM_ACT_OFF) {
            if (in->off_req) {
                sm->clear_faults = false;
                set_mode(sm, PEN_MODE_OFF);
            } else if (in->pen_up && in->self_check_ok) {
                sm->clear_faults = true;
                sm->faults_handled = 0;
                set_mode(sm, PEN_MODE_STANDBY);
            }
        }
        break;

    case PEN_MODE_COUNT:
    default:
        set_mode(sm, PEN_MODE_SAFE_PASSIVE);
        sm->act = SM_ACT_OFF;
        break;
    }

    /* ---- outputs ---- */
    if (is_assist(sm->mode) && !sm->disarm_pending && sm->act == SM_ACT_SERVO) {
        if (sm->mode == PEN_MODE_TRAINING_FADE) {
            sm->g_cap = 1.0f - (1.0f - SM_TRAIN_G_END) * pen_minf(sm->train_t / SM_TRAIN_T, 1.0f);
        } else {
            sm->g_cap = 1.0f;
        }
    } else {
        sm->g_cap = 0.0f;
    }
    sm->act_en_req = (sm->act != SM_ACT_OFF);
}
