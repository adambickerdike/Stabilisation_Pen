/*
 * test_sm.c - state machine transition table (ICD s6) including every fault bit.
 */
#include <math.h>
#include <string.h>

#include "params_gen.h"
#include "state_machine.h"
#include "tr.h"

#define TS PEN_TS_STAGE

static sm_in_t base_in(void)
{
    sm_in_t in;
    memset(&in, 0, sizeof(in));
    in.dt = TS;
    in.boot_ok = true;
    in.pen_up = true;
    in.assist_req = PEN_MODE_NEUTRAL_HOLD;
    in.self_check_ok = true;
    in.power_ok = true;
    in.mode_perm = (uint8_t)SM_PERM_DEFAULT;
    return in;
}

static void step_n(sm_t *sm, const sm_in_t *in, int n)
{
    for (int k = 0; k < n; k++) {
        sm_step(sm, in);
    }
}

/* drive the machine to a given assist mode with the pen down */
static void to_mode(sm_t *sm, pen_mode_t m, bool ml)
{
    sm_init(sm);
    sm_in_t in = base_in();
    in.ml_available = ml;
    in.mode_perm = (uint8_t)(SM_PERM_DEFAULT | (ml ? SM_PERM_ML : 0u));
    step_n(sm, &in, 1);                 /* OFF -> STANDBY */
    in.arm_req = true;
    step_n(sm, &in, 1);                 /* -> NEUTRAL_HOLD */
    in.arm_req = false;
    in.pen_up = false;
    in.assist_req = m;
    step_n(sm, &in, 1);
}

void test_sm_transition_table(void)
{
    sm_t sm;
    sm_in_t in;
    /* OFF -> STANDBY on boot */
    sm_init(&sm);
    CHECK(sm.mode == PEN_MODE_OFF && sm.act == SM_ACT_OFF);
    in = base_in();
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_STANDBY && !sm.act_en_req);
    /* STANDBY -> NEUTRAL_HOLD only when armed at pen-up with power OK */
    in.arm_req = true;
    in.pen_up = false;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_STANDBY);
    in.pen_up = true;
    in.power_ok = false;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_STANDBY);
    in.power_ok = true;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_NEUTRAL_HOLD && sm.act == SM_ACT_SERVO && sm.act_en_req && sm.g_cap == 0.0f);
    in.arm_req = false;
    /* NEUTRAL_HOLD -> each assist mode; permissions and ML availability */
    const pen_mode_t modes[4] = {PEN_MODE_ASSIST_KF, PEN_MODE_ASSIST_ML, PEN_MODE_GUIDED, PEN_MODE_TRAINING_FADE};
    for (int k = 0; k < 4; k++) {
        to_mode(&sm, modes[k], false);
        if (modes[k] == PEN_MODE_ASSIST_ML) {
            CHECK(sm.mode == PEN_MODE_NEUTRAL_HOLD);    /* no validated model: refused */
            to_mode(&sm, modes[k], true);
        }
        CHECK(sm.mode == modes[k] && sm.act == SM_ACT_SERVO && sm.g_cap == 1.0f);
    }
    /* permission withdrawn by CAL_USER: refused */
    sm_init(&sm);
    in = base_in();
    in.mode_perm = (uint8_t)(SM_PERM_DEFAULT & ~SM_PERM_KF);
    step_n(&sm, &in, 1);
    in.arm_req = true;
    step_n(&sm, &in, 1);
    in.arm_req = false;
    in.assist_req = PEN_MODE_ASSIST_KF;
    step_n(&sm, &in, 5);
    CHECK(sm.mode == PEN_MODE_NEUTRAL_HOLD);
    /* ASSIST -> NEUTRAL_HOLD on request */
    to_mode(&sm, PEN_MODE_ASSIST_KF, false);
    in = base_in();
    in.pen_up = false;
    in.assist_req = PEN_MODE_NEUTRAL_HOLD;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_NEUTRAL_HOLD && sm.g_cap == 0.0f && sm.act == SM_ACT_SERVO);
    /* TRAINING_FADE: authority cap falls with pen-down time */
    to_mode(&sm, PEN_MODE_TRAINING_FADE, false);
    in = base_in();
    in.pen_up = false;
    in.assist_req = PEN_MODE_TRAINING_FADE;
    step_n(&sm, &in, (int)(30.0f / TS));
    CHECK_CLOSE(sm.g_cap, 1.0 - (1.0 - SM_TRAIN_G_END) * 0.5, 0.01, 0.0);
    /* disarm while writing: fade, stay energised until pen-up, then ramp -> STANDBY */
    to_mode(&sm, PEN_MODE_ASSIST_KF, false);
    in = base_in();
    in.pen_up = false;
    in.assist_req = PEN_MODE_ASSIST_KF;
    in.disarm_req = true;
    sm_step(&sm, &in);
    in.disarm_req = false;
    step_n(&sm, &in, 200);
    CHECK(sm.mode == PEN_MODE_NEUTRAL_HOLD && sm.act == SM_ACT_SERVO && sm.g_cap == 0.0f);
    in.pen_up = true;
    sm_step(&sm, &in);
    CHECK(sm.act == SM_ACT_RAMP);
    const int n_ramp = (int)lrintf(PEN_RAMP_DOWN_TIME / TS);
    step_n(&sm, &in, n_ramp);
    CHECK(sm.mode == PEN_MODE_STANDBY && sm.act == SM_ACT_OFF && !sm.act_en_req);
    /* STANDBY -> OFF */
    in.off_req = true;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_OFF);
    /* off request while assisting: ramp at pen-up, then OFF */
    to_mode(&sm, PEN_MODE_GUIDED, false);
    in = base_in();
    in.pen_up = true;
    in.assist_req = PEN_MODE_GUIDED;
    in.off_req = true;
    step_n(&sm, &in, n_ramp + 3);
    CHECK(sm.mode == PEN_MODE_OFF && sm.act == SM_ACT_OFF);
    tr_log("OFF->STANDBY->NEUTRAL_HOLD->{ASSIST_KF, ASSIST_ML, GUIDED, TRAINING_FADE}, permissions, disarm/off with "
           "ramp-down %.0f ms at pen-up: as specified", (double)PEN_RAMP_DOWN_TIME * 1e3);
}

typedef struct {
    uint16_t bit;
    sm_act_t policy_in_contact;
    const char *name;
} fault_case_t;

void test_sm_fault_policies(void)
{
    const fault_case_t fc[9] = {
        {PEN_FAULT_OVERCURRENT, SM_ACT_OFF, "0 over-current (hard, VMOT removed)"},
        {PEN_FAULT_HALL, SM_ACT_HOLD_OL, "1 Hall frozen (hard, hold open loop)"},
        {PEN_FAULT_OVERTEMP, SM_ACT_NEUTRAL, "2 over-temperature (fade, wait pen-up)"},
        {PEN_FAULT_LOWBAT, SM_ACT_NEUTRAL, "3 low battery (fade, wait pen-up)"},
        {PEN_FAULT_OPTICAL, SM_ACT_NEUTRAL, "4 optical invalid (fade, wait pen-up)"},
        {PEN_FAULT_WATCHDOG, SM_ACT_OFF, "5 watchdog (hard)"},
        {PEN_FAULT_HEADROOM, SM_ACT_NEUTRAL, "6 headroom (fade, wait pen-up)"},
        {PEN_FAULT_CHARGING, SM_ACT_OFF, "7 charging (VMOT removed)"},
        {PEN_FAULT_MLGUARD, SM_ACT_NEUTRAL, "8 ML guard (fade, wait pen-up)"}};
    const int n_ramp = (int)lrintf(PEN_RAMP_DOWN_TIME / TS);
    for (int k = 0; k < 9; k++) {
        sm_t sm;
        to_mode(&sm, PEN_MODE_ASSIST_KF, false);
        sm_in_t in = base_in();
        in.pen_up = false;
        in.assist_req = PEN_MODE_ASSIST_KF;
        in.faults = fc[k].bit;
        in.self_check_ok = false;
        sm_step(&sm, &in);
        CHECK(sm.mode == PEN_MODE_SAFE_PASSIVE);
        CHECK(sm.act == fc[k].policy_in_contact);
        CHECK(sm.g_cap == 0.0f);
        /* in contact the stage stays energised (except where VMOT is already gone) */
        CHECK(sm.act_en_req == (fc[k].policy_in_contact != SM_ACT_OFF));
        step_n(&sm, &in, 1000);   /* 0.5 s still in contact */
        CHECK(sm.act == fc[k].policy_in_contact);
        /* pen-up: ramp over >= 30 ms (REQ-SAF-004), then off */
        in.pen_up = true;
        sm_step(&sm, &in);
        if (fc[k].policy_in_contact != SM_ACT_OFF) {
            CHECK(sm.act == SM_ACT_RAMP);
            float prev = sm.ramp;
            bool mono = true;
            int n = 1;
            while (sm.act == SM_ACT_RAMP && n < 200) {
                sm_step(&sm, &in);
                mono = mono && sm.ramp <= prev;
                prev = sm.ramp;
                n++;
            }
            CHECK(mono);
            CHECK(n >= n_ramp && n <= n_ramp + 2);
        }
        CHECK(sm.act == SM_ACT_OFF && !sm.act_en_req);
        /* SAFE_PASSIVE -> STANDBY only with a successful self-check */
        step_n(&sm, &in, 10);
        CHECK(sm.mode == PEN_MODE_SAFE_PASSIVE);
        in.self_check_ok = true;
        sm_step(&sm, &in);
        CHECK(sm.mode == PEN_MODE_STANDBY && sm.clear_faults);
        tr_log("fault bit %s: SAFE_PASSIVE, in contact act=%d, pen-up -> ramp -> off, self-check -> STANDBY", fc[k].name,
               (int)fc[k].policy_in_contact);
    }
    /* soft fault, pen never lifted: de-energise after the 5 s timeout (ICD s6) */
    sm_t sm;
    to_mode(&sm, PEN_MODE_ASSIST_KF, false);
    sm_in_t in = base_in();
    in.pen_up = false;
    in.faults = PEN_FAULT_LOWBAT;
    in.self_check_ok = false;
    const int n_to = (int)lrintf(PEN_PENUP_TIMEOUT / TS);
    step_n(&sm, &in, n_to - 5);
    CHECK(sm.act == SM_ACT_NEUTRAL);
    step_n(&sm, &in, 10);
    CHECK(sm.act == SM_ACT_RAMP);
    step_n(&sm, &in, (int)lrintf(PEN_RAMP_DOWN_TIME / TS) + 2);
    CHECK(sm.act == SM_ACT_OFF);
    /* escalation inside SAFE_PASSIVE: neutral -> hold (Hall) -> off (over-current) */
    to_mode(&sm, PEN_MODE_ASSIST_KF, false);
    in = base_in();
    in.pen_up = false;
    in.self_check_ok = false;
    in.faults = PEN_FAULT_OVERTEMP;
    sm_step(&sm, &in);
    CHECK(sm.act == SM_ACT_NEUTRAL);
    in.faults = PEN_FAULT_OVERTEMP | PEN_FAULT_HALL;
    sm_step(&sm, &in);
    CHECK(sm.act == SM_ACT_HOLD_OL);
    in.faults = PEN_FAULT_OVERTEMP | PEN_FAULT_HALL | PEN_FAULT_OVERCURRENT;
    sm_step(&sm, &in);
    CHECK(sm.act == SM_ACT_OFF);
    /* fault while the pen is already up: immediate ramp-down */
    to_mode(&sm, PEN_MODE_ASSIST_KF, false);
    in = base_in();
    in.pen_up = true;
    in.faults = PEN_FAULT_HEADROOM;
    in.self_check_ok = false;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_SAFE_PASSIVE && sm.act == SM_ACT_RAMP);
    /* fault in STANDBY (de-energised): SAFE_PASSIVE, stays off */
    sm_init(&sm);
    in = base_in();
    sm_step(&sm, &in);
    in.faults = PEN_FAULT_WATCHDOG;
    in.self_check_ok = false;
    sm_step(&sm, &in);
    CHECK(sm.mode == PEN_MODE_SAFE_PASSIVE && sm.act == SM_ACT_OFF);
    tr_log("soft fault in contact: de-energised after the %.0f s pen-up timeout with a %.0f ms ramp; escalation "
           "NEUTRAL -> HOLD_OL -> OFF; fault at pen-up ramps immediately", (double)PEN_PENUP_TIMEOUT,
           (double)PEN_RAMP_DOWN_TIME * 1e3);
}
