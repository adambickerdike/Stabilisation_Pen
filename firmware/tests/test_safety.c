/*
 * test_safety.c - fault detections (ICD s6) and the over-current latch clear
 * sequence against the host model of the Rev A interlock.
 */
#include <math.h>
#include <string.h>

#include "hal_host.h"
#include "params_gen.h"
#include "safety.h"
#include "tr.h"

static void noisy_raw(tr_rng_t *r, int16_t raw[3])
{
    for (int k = 0; k < 3; k++) {
        raw[k] = (int16_t)(1000 + (int)lrint(3.0 * tr_rng_normal(r)));   /* a few LSB of noise */
    }
}

void test_safety_hall_stuck(void)
{
    safety_t s;
    safety_init(&s);
    tr_rng_t rng;
    tr_rng_seed(&rng, 21u);
    const float q[2] = {0.0f, 0.0f}, i[2] = {0.0f, 0.0f};
    int16_t raw[3];
    bool fault = false;
    for (int k = 0; k < 20000; k++) {   /* 10 s of live data: no false positive */
        safety_tick_begin(&s);
        noisy_raw(&rng, raw);
        fault = fault || safety_hall_check(&s, raw, true, q, i);
    }
    CHECK(!fault);
    /* freeze: the sensor keeps returning the same frame */
    const uint32_t t_freeze = s.ticks + 1u;   /* first repeated frame arrives at this tick */
    int k_det = -1;
    for (int k = 0; k < 40; k++) {
        safety_tick_begin(&s);
        if (safety_hall_check(&s, raw, true, q, i)) {
            k_det = k;
            break;
        }
    }
    CHECK(k_det >= 0);
    const double latency_ms = (double)(s.hall_trip_tick - t_freeze + 1u) * 0.5;
    CHECK(latency_ms <= 5.0);
    CHECK((s.faults & PEN_FAULT_HALL) != 0u);
    tr_log("frozen Hall frame detected %.1f ms after the first repeated frame (budget 5 ms, ICD s6); "
           "no false trip in 10 s of live frames with ~3 LSB noise", latency_ms);
    /* stale data (no new conversion / CRC error) on two consecutive ticks */
    safety_init(&s);
    noisy_raw(&rng, raw);
    safety_tick_begin(&s);
    CHECK(!safety_hall_check(&s, raw, false, q, i));
    noisy_raw(&rng, raw);
    safety_tick_begin(&s);
    CHECK(safety_hall_check(&s, raw, false, q, i));
}

void test_safety_hall_residual_and_range(void)
{
    /* consistent motion: 0.3 mm 8 Hz with the matching coil current -> no trip */
    safety_t s;
    safety_init(&s);
    tr_rng_t rng;
    tr_rng_seed(&rng, 5u);
    int16_t raw[3];
    const double w = 2.0 * 3.141592653589793 * 8.0, A = 3e-4;
    bool fault = false;
    double resid_max = 0.0;
    for (int k = 0; k < 4000; k++) {
        const double t = k * 5e-4;
        const float q[2] = {(float)(A * sin(w * t) + 1e-6 * tr_rng_normal(&rng)), (float)(1e-6 * tr_rng_normal(&rng))};
        /* current that produces the motion (m q'' + k q = -n Kf i) */
        const double qdd = -w * w * A * sin(w * t);
        const float i[2] = {(float)(-(PEN_M_EQ * qdd + PEN_K_TIP * A * sin(w * t)) / (PEN_N_LEVER * PEN_KF20)), 0.0f};
        noisy_raw(&rng, raw);
        safety_tick_begin(&s);
        fault = fault || safety_hall_check(&s, raw, true, q, i);
    }
    resid_max = (double)s.hall_resid_max;
    CHECK(!fault);
    /* a 150 um jump (glitch) is implausible */
    const float qj[2] = {1.5e-4f, 0.0f}, i0[2] = {0.0f, 0.0f};
    safety_init(&s);
    int k_det = -1;
    for (int k = 0; k < 10; k++) {
        noisy_raw(&rng, raw);
        safety_tick_begin(&s);
        const float qz[2] = {0.0f, 0.0f};
        if (safety_hall_check(&s, raw, true, k < 4 ? qz : qj, i0)) {
            k_det = k;
            break;
        }
    }
    CHECK(k_det == 5);   /* 2 consecutive residual exceedances after the jump at k = 4 */
    /* beyond the mechanical stop */
    safety_init(&s);
    const float qo[2] = {0.0f, PEN_Q_STOP + 0.1e-3f};
    bool r1 = false;
    for (int k = 0; k < 3; k++) {
        noisy_raw(&rng, raw);
        safety_tick_begin(&s);
        r1 = safety_hall_check(&s, raw, true, qo, i0) || r1;
    }
    CHECK(r1);
    tr_log("model residual: max %.2f um over 2 s of consistent 0.3 mm 8 Hz motion (threshold %.0f um); 150 um jump "
           "detected on the 2nd residual tick; |q| beyond the stop detected", resid_max * 1e6,
           (double)PEN_HALL_JUMP_MAX * 1e6);
}

void test_safety_headroom(void)
{
    safety_t s;
    safety_init(&s);
    int k_trip = -1;
    for (int k = 0; k < 200; k++) {
        safety_tick_begin(&s);
        if (safety_headroom_check(&s, 0.96f)) {
            k_trip = k;
            break;
        }
    }
    CHECK(k_trip == 100);   /* the 101st tick: > 50 ms */
    /* interrupted runs never trip */
    safety_init(&s);
    bool f = false;
    for (int k = 0; k < 2000; k++) {
        safety_tick_begin(&s);
        f = safety_headroom_check(&s, (k % 90 == 89) ? 0.90f : 0.96f) || f;
    }
    CHECK(!f);
    tr_log("headroom: duty > 0.95 on every tick trips at %.1f ms (ICD: > 50 ms); runs of 44.5 ms never trip",
           (k_trip + 1) * 0.5);
}

void test_safety_optical(void)
{
    safety_t s;
    safety_init(&s);
    int k_trip = -1;
    for (int k = 0; k < 800; k++) {
        safety_tick_begin(&s);
        if (safety_optical_check(&s, false, true, true)) {
            k_trip = k;
            break;
        }
    }
    CHECK(k_trip == 600);   /* > 300 ms */
    safety_init(&s);
    bool f = false;
    for (int k = 0; k < 2000; k++) {
        safety_tick_begin(&s);
        f = safety_optical_check(&s, false, false, true) || f;    /* lifted: expected loss of tracking */
        f = safety_optical_check(&s, false, true, false) || f;    /* no assistance: not monitored */
    }
    CHECK(!f);
}

void test_safety_battery(void)
{
    safety_t s;
    safety_init(&s);
    bool f = false;
    for (int k = 0; k < 200; k++) {   /* 2 s at 100 Hz at 3.35 V: above v_bat_min */
        f = safety_battery_check(&s, 3.35f, 0.01f) || f;
    }
    CHECK(!f);
    CHECK(!safety_battery_ok(&s));    /* but below the recovery threshold (hysteresis) */
    int k_trip = -1;
    for (int k = 0; k < 200; k++) {
        if (safety_battery_check(&s, 3.20f, 0.01f)) {
            k_trip = k;
            break;
        }
    }
    CHECK(k_trip > 15 && k_trip < 60);
    for (int k = 0; k < 100; k++) {
        (void)safety_battery_check(&s, 3.60f, 0.01f);
    }
    CHECK(safety_battery_ok(&s));
    tr_log("low battery: 3.35 V no fault (recover >= %.2f V); step to 3.20 V trips after %d ms (LPF %.0f ms + debounce %.0f ms)",
           (double)PEN_VBAT_RECOVER, (k_trip + 1) * 10, (double)PEN_VBAT_LPF_TAU * 1e3, (double)PEN_VBAT_DEBOUNCE * 1e3);
}

void test_safety_overcurrent_latch_clear(void)
{
    hal_host_reset();
    safety_t s;
    safety_init(&s);
    hal_act_en_req(true);
    CHECK(hal_host_act_en());
    safety_tick_begin(&s);
    CHECK(!safety_overcurrent_check(&s));
    /* comparator trips: latch set, VMOT removed by hardware */
    hal_host_set_overcurrent(true);
    CHECK(!hal_host_act_en());
    safety_tick_begin(&s);
    CHECK(safety_overcurrent_check(&s));
    CHECK((s.faults & PEN_FAULT_OVERCURRENT) != 0u);
    /* fault still present: the clear sequence fails after the retries */
    oc_clr_state_t st = OC_CLR_IDLE;
    for (int k = 0; k < 20 && st != OC_CLR_FAILED && st != OC_CLR_OK; k++) {
        st = safety_oc_clear_step(&s);
        CHECK(!hal_host_act_en());
    }
    CHECK(st == OC_CLR_FAILED);
    CHECK(!safety_self_check(&s));
    /* fault removed: the sequence succeeds */
    hal_host_set_overcurrent(false);
    safety_oc_clear_reset(&s);
    for (int k = 0; k < 20 && st != OC_CLR_OK; k++) {
        st = safety_oc_clear_step(&s);
    }
    CHECK(st == OC_CLR_OK);
    CHECK(hal_fault_n());
    CHECK(g_hal.clr_while_req_high == 0u);   /* ACT_EN_REQ low before every FAULT_CLR_N pulse */
    CHECK(!g_hal.act_en_req);
    CHECK(safety_self_check(&s));
    tr_log("over-current latch: trip removes ACT_EN in hardware; clear = ACT_EN_REQ low -> FAULT_CLR_N pulse -> "
           "FAULT_N check; %u pulses, none with ACT_EN_REQ high; persistent fault -> FAILED after %.0f retries",
           (unsigned)g_hal.clr_pulses, (double)PEN_OC_CLEAR_RETRIES);
}

void test_safety_ml_trips(void)
{
    safety_t s;
    safety_init(&s);
    bool f = false;
    for (int k = 0; k < 5; k++) {
        for (int j = 0; j < 1000; j++) {
            safety_tick_begin(&s);   /* 0.5 s between trips */
        }
        f = safety_ml_trip(&s) || f;
    }
    CHECK(!f);   /* 5 trips in 2.5 s: allowed */
    for (int j = 0; j < 1000; j++) {
        safety_tick_begin(&s);
    }
    CHECK(safety_ml_trip(&s));   /* 6th within 10 s: bit 8 */
    safety_init(&s);
    f = false;
    for (int k = 0; k < 12; k++) {
        for (int j = 0; j < 5000; j++) {
            safety_tick_begin(&s);   /* 2.5 s apart: at most 4 in any 10 s */
        }
        f = safety_ml_trip(&s) || f;
    }
    CHECK(!f);
}
