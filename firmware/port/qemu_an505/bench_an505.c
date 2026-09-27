/*
 * bench_an505.c - INSTRUCTION-COUNT ESTIMATE of the two real-time bodies,
 * pen_app_current_isr() (40 kHz) and pen_app_stage_tick() (2 kHz), compiled
 * for Cortex-M33 (-O2, FPv5-SP hard float, the flags of the nRF5340 build)
 * and executed on QEMU mps2-an505.
 *
 * Evidence status: QEMU EXECUTION. QEMU is not cycle-accurate. Run with
 * `-icount shift=N`, the virtual clock advances 2^N ns per executed guest
 * instruction, so the SysTick (processor clock) counts instructions, not
 * cycles. The ratio SysTick-ticks per instruction is calibrated here with a
 * loop of known length (subs + bne = 2 instructions per iteration). The
 * numbers exclude interrupt entry/exit, FP lazy stacking, flash wait
 * states, pipeline and bus stalls and the nRF5340 port code (SAADC/EGU
 * handlers, SPI sensor reads); host HAL stubs replace the register HAL.
 *
 * Scenario (closed loop on the C plant of tests/plant.c, switched bridge,
 * 3.7 V, 25 degC): 100 ticks pen-up in STANDBY, arm, ASSIST_KF, pen-down
 * with 0.5 N transverse load, 9 Hz housing tremor (0.3 / 0.2 mm) on a
 * 20 mm/s stroke seen by the optics (2 ms delay) and the IMU (1.92 samples
 * per tick), 1000 ticks, then pen-up and 200 more ticks (debounce, ramp,
 * ISNS offset calibration). ML window export runs (ml_available); no model
 * is linked, so the inference itself is not included. Every log record is
 * copied into an 8 kB ring as in port/nrf5340/sensors_nrf5340.c.
 */
#include "bench_an505.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "app.h"
#include "crc16.h"
#include "hal_host.h"
#include "params_gen.h"
#include "plant.h"

#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
#define SYST_MASK 0x00FFFFFFu

#define N_PENUP0 100u
#define N_ARM 10u
#define N_DOWN 1000u
#define N_SETTLE 300u          /* first 300 ticks after pen-down excluded from the steady-state set */
#define N_PENUP1 200u
#define N_TICKS (N_PENUP0 + N_ARM + N_DOWN + N_PENUP1)
#define N_ISR (N_TICKS * (uint32_t)PEN_PWM_PER_STAGE)

#define LOG_RING 8192u
/* nRF5340 application core at 128 MHz: 3200 cycles per 25 us PWM period,
 * 64000 cycles per 500 us stage tick (the budgets of the firmware brief) */
#define BENCH_F_CPU_HZ 128.0e6f

typedef struct {
    pen_app_t app;
    plant_t pl;
    pen_sensors_t sens;
    uint8_t ring[LOG_RING];
    uint32_t head, tail, drops, bytes;
} bench_t;

static bench_t g_b;
/* snapshot of the last steady-state tick for the per-part breakdown */
static pen_app_t s_app_snap, s_app_work;
static pen_sensors_t s_sens_snap;
static hal_host_state_t s_hal_snap;
static bool s_have_snap;
static uint32_t s_stage_ticks[N_TICKS];
static uint8_t s_stage_cls[N_TICKS];    /* bit0 steady contact, bit1 100 Hz slow tick, bit2 ML push tick */
static uint16_t s_isr_ticks[N_ISR];

static inline uint32_t st_now(void)
{
    return SYST_CVR;
}

static inline uint32_t st_elapsed(uint32_t t0, uint32_t t1)
{
    return (t0 - t1) & SYST_MASK;   /* counts down */
}

static void __attribute__((noinline)) spin(uint32_t n)
{
    __asm__ volatile("1: subs %0, %0, #1\n\tbne 1b\n" : "+r"(n) : : "cc");
}

/* same copy loop as board_log_sink() of the nRF5340 port */
static void sink(const uint8_t *rec, size_t len, void *ctx)
{
    bench_t *b = (bench_t *)ctx;
    const uint32_t used = b->head - b->tail;
    if (used + len > LOG_RING) {
        b->drops++;
        return;
    }
    for (size_t k = 0; k < len; k++) {
        b->ring[(b->head + (uint32_t)k) % LOG_RING] = rec[k];
    }
    b->head += (uint32_t)len;
}

static int cmp_u32(const void *pa, const void *pb)
{
    const uint32_t a = *(const uint32_t *)pa, b = *(const uint32_t *)pb;
    return (a > b) - (a < b);
}

typedef struct {
    uint32_t n;
    float mean, p50, p99, max;
} stats_t;

static stats_t stats(uint32_t *v, uint32_t n, float over, float tpi)
{
    stats_t s = {n, 0.0f, 0.0f, 0.0f, 0.0f};
    if (n == 0u) {
        return s;
    }
    qsort(v, n, sizeof(v[0]), cmp_u32);
    double sum = 0.0;
    for (uint32_t k = 0; k < n; k++) {
        sum += (double)v[k];
    }
    const float mean_t = (float)(sum / (double)n);
    s.mean = (mean_t - over) / tpi;
    s.p50 = ((float)v[n / 2u] - over) / tpi;
    s.p99 = ((float)v[(uint32_t)((float)(n - 1u) * 0.99f)] - over) / tpi;
    s.max = ((float)v[n - 1u] - over) / tpi;
    return s;
}

static void print_stats(const char *name, stats_t s, float budget)
{
    printf("BENCH %s n=%u mean=%.0f p50=%.0f p99=%.0f max=%.0f instructions (budget %.0f cycles: max = %.1f %%)\n",
           name, (unsigned)s.n, (double)s.mean, (double)s.p50, (double)s.p99, (double)s.max, (double)budget,
           100.0 * (double)s.max / (double)budget);
}

int pen_bench_run(void)
{
    bench_t *b = &g_b;
    SYST_RVR = SYST_MASK;
    SYST_CVR = 0u;
    SYST_CSR = 0x5u;   /* enable, processor clock, no interrupt */

    /* ---- calibration: SysTick ticks per executed instruction ---- */
    uint32_t t0 = st_now();
    spin(50000u);
    uint32_t t1 = st_now();
    const uint32_t c1 = st_elapsed(t0, t1);
    t0 = st_now();
    spin(150000u);
    t1 = st_now();
    const uint32_t c2 = st_elapsed(t0, t1);
    t0 = st_now();
    spin(250000u);
    t1 = st_now();
    const uint32_t c3 = st_elapsed(t0, t1);
    if (c2 <= c1 || c3 <= c2) {
        printf("BENCH unavailable: SysTick does not advance with execution (run QEMU with -icount shift=N)\n");
        return 0;
    }
    const float tpi = (float)(c2 - c1) / 200000.0f;          /* ticks per instruction */
    const float tpi_chk = (float)(c3 - c2) / 200000.0f;
    float over = 1e9f;                                        /* empty measured region */
    for (int k = 0; k < 16; k++) {
        t0 = st_now();
        __asm__ volatile("" ::: "memory");
        t1 = st_now();
        const float e = (float)st_elapsed(t0, t1);
        over = (e < over) ? e : over;
    }
    printf("BENCH calib ticks_per_instruction=%.5f check=%.5f overhead_ticks=%.1f (spin 100k/300k/500k iterations: "
           "%u/%u/%u ticks)\n",
           (double)tpi, (double)tpi_chk, (double)over, (unsigned)c1, (unsigned)c2, (unsigned)c3);

    /* ---- closed-loop scenario ---- */
    memset(b, 0, sizeof(*b));
    hal_host_reset();
    plant_init(&b->pl, 3.7, 25.0);
    pen_app_init(&b->app, PEN_PROFILE_BALANCED, false);
    pen_app_set_sink(&b->app, sink, b, true);
    b->app.ml_available = true;   /* window export runs; no model is linked */
    const float th = 50.0f * 3.14159265f / 180.0f;
    b->sens.imu_acc_h[0] = -9.80665f * cosf(th);
    b->sens.imu_acc_h[2] = 9.80665f * sinf(th);
    b->sens.imu_dt = 1.0f / PEN_IMU_RATE_HZ;

    const float w = 2.0f * 3.14159265f * 9.0f;
    const float amp[2] = {0.3e-3f, 0.2e-3f};
    const float phs[2] = {0.0f, 1.0f};
    const float v_int = 0.02f;
    uint32_t n_isr = 0;
    uint32_t n_down_ticks = 0;
    float g_sum = 0.0f, g_min = 1.0f;
    uint32_t t_down0 = 0;
    for (uint32_t k = 0; k < N_TICKS; k++) {
        const bool down = (k >= N_PENUP0 + N_ARM) && (k < N_PENUP0 + N_ARM + N_DOWN);
        if (k == N_PENUP0) {
            b->app.req.arm = true;
        }
        if (k == N_PENUP0 + N_ARM) {
            b->app.req.assist = PEN_MODE_ASSIST_KF;
            t_down0 = k;
        }
        g_hal.time_us += 500u;
        const float t = (float)k * 5e-4f;
        const float td = (float)(k - t_down0) * 5e-4f;
        /* plant contact state */
        b->pl.f_ax = down ? 1.0 : (double)PEN_F_PRE;
        b->pl.f_ext[0] = down ? 0.5 : 0.0;
        plant_hall(&b->pl, b->sens.hall_raw);
        b->sens.hall_fresh = true;
        /* optics (delayed page position of the housing) and IMU */
        const float t_opt = t - PEN_OPT_DELAY;
        for (int ax = 0; ax < 2; ax++) {
            const float intent = (ax == 0 && down) ? v_int * td : 0.0f;
            b->sens.opt_p[ax] = intent + amp[ax] * sinf(w * t_opt + phs[ax]);
        }
        b->sens.opt_valid = down;
        b->sens.opt_valid_bits = down ? 0x07u : 0x00u;
        b->sens.opt_surface_lost = !down;
        b->sens.imu_n = (k % 12u == 0u) ? 1u : 2u;
        for (uint32_t m = 0; m < b->sens.imu_n; m++) {
            const float ti = t - (float)(b->sens.imu_n - 1u - m) * b->sens.imu_dt;
            for (int ax = 0; ax < 2; ax++) {
                b->sens.imu_a_page_seq[m][ax] = -amp[ax] * w * w * sinf(w * ti + phs[ax]);
            }
        }
        b->sens.imu_a_page[0] = b->sens.imu_a_page_seq[b->sens.imu_n - 1u][0];
        b->sens.imu_a_page[1] = b->sens.imu_a_page_seq[b->sens.imu_n - 1u][1];

        const uint32_t app_tick = b->app.tick;
        if (k == N_PENUP0 + N_ARM + N_DOWN - 1u && b->app.sm.mode == PEN_MODE_ASSIST_KF && b->app.in_contact) {
            s_app_snap = b->app;
            s_sens_snap = b->sens;
            s_hal_snap = g_hal;
            s_have_snap = true;
        }
        t0 = st_now();
        pen_app_stage_tick(&b->app, &b->sens);
        t1 = st_now();
        s_stage_ticks[k] = st_elapsed(t0, t1);
        uint8_t cls = 0u;
        if (down && (k - t_down0) >= N_SETTLE && b->app.sm.mode == PEN_MODE_ASSIST_KF && b->app.in_contact) {
            cls |= 1u;
            n_down_ticks++;
            g_sum += b->app.ctrl.g_eff;
            g_min = (b->app.ctrl.g_eff < g_min) ? b->app.ctrl.g_eff : g_min;
        }
        if ((app_tick % APP_SLOW_DECIM) == 0u) {
            cls |= 2u;
        }
        if (b->app.opt_valid && (app_tick % (uint32_t)PEN_ML_DECIM) == 0u) {
            cls |= 4u;
        }
        s_stage_cls[k] = cls;

        for (int p = 0; p < PEN_PWM_PER_STAGE; p++) {
            const bool powered = hal_host_act_en() && g_hal.drv_sleep_n;
            b->pl.vm = powered ? 3.7 : 0.0;
            bridge_cmd_t cmd[2] = {g_hal.bridge[0], g_hal.bridge[1]};
            if (!powered) {
                memset(cmd, 0, sizeof(cmd));
            }
            int16_t ae[2], ac[2];
            plant_period(&b->pl, cmd, ae, ac);
            t0 = st_now();
            pen_app_current_isr(&b->app, ac, ae);
            t1 = st_now();
            s_isr_ticks[n_isr++] = (uint16_t)((st_elapsed(t0, t1) > 0xFFFFu) ? 0xFFFFu : st_elapsed(t0, t1));
        }
        b->bytes += b->head - b->tail;
        b->tail = b->head;   /* drained by the (not measured) background loop */
    }

    /* ---- statistics ---- */
    static uint32_t v[N_ISR];
    uint32_t n = 0;
    for (uint32_t k = 0; k < n_isr; k++) {
        v[n++] = s_isr_ticks[k];
    }
    const stats_t s_isr = stats(v, n, over, tpi);
    const float isr_budget = BENCH_F_CPU_HZ / PEN_F_PWM_HZ;
    const float stage_budget = BENCH_F_CPU_HZ / PEN_F_STAGE_HZ;

    n = 0;
    for (uint32_t k = 0; k < N_TICKS; k++) {
        v[n++] = s_stage_ticks[k];
    }
    const stats_t s_all = stats(v, n, over, tpi);
    n = 0;
    for (uint32_t k = 0; k < N_TICKS; k++) {
        if ((s_stage_cls[k] & 1u) != 0u) {
            v[n++] = s_stage_ticks[k];
        }
    }
    const stats_t s_ss = stats(v, n, over, tpi);
    n = 0;
    for (uint32_t k = 0; k < N_TICKS; k++) {
        if ((s_stage_cls[k] & 3u) == 3u) {
            v[n++] = s_stage_ticks[k];
        }
    }
    const stats_t s_slow = stats(v, n, over, tpi);
    n = 0;
    for (uint32_t k = 0; k < N_TICKS; k++) {
        if ((s_stage_cls[k] & 7u) == 5u) {
            v[n++] = s_stage_ticks[k];
        }
    }
    const stats_t s_ml = stats(v, n, over, tpi);

    printf("BENCH scenario ticks=%u isr_calls=%u steady_contact_ticks=%u (authority g_eff mean %.3f min %.3f) "
           "final_mode=%u faults=0x%04x log_bytes=%u log_drops=%u\n",
           (unsigned)N_TICKS, (unsigned)n_isr, (unsigned)n_down_ticks,
           (double)(n_down_ticks ? g_sum / (float)n_down_ticks : 0.0f), (double)g_min, (unsigned)b->app.sm.mode,
           (unsigned)b->app.sf.faults, (unsigned)b->bytes, (unsigned)b->drops);
    print_stats("isr_current_loop", s_isr, isr_budget);
    print_stats("stage_all_ticks", s_all, stage_budget);
    print_stats("stage_assist_steady", s_ss, stage_budget);
    print_stats("stage_assist_slow_100Hz", s_slow, stage_budget);
    print_stats("stage_assist_ml_push", s_ml, stage_budget);
    /* docs/icd.md s2 (v1.2): stage loop <= 250 us compute = 32000 cycles at 128 MHz */
    const float icd_stage = BENCH_F_CPU_HZ * 250e-6f;
    printf("BENCH icd_stage_budget %.0f cycles (250 us): all-ticks max = %.1f %%, steady max = %.1f %%, steady mean = "
           "%.1f %% (instructions / cycles)\n",
           (double)icd_stage, 100.0 * (double)s_all.max / (double)icd_stage, 100.0 * (double)s_ss.max / (double)icd_stage,
           100.0 * (double)s_ss.mean / (double)icd_stage);
    const float load = (s_isr.mean * (float)PEN_PWM_PER_STAGE + s_ss.mean) / stage_budget;
    printf("BENCH cpu_load_estimate_assist=%.1f %% (mean ISR x 20 + mean steady stage tick, per 2 kHz period, at 1 "
           "instruction per cycle; a lower bound)\n",
           100.0 * (double)load);

    /* ---- breakdown on the snapshot of the last steady tick (same inputs) ---- */
    if (s_have_snap) {
        float part[4];
        for (int m = 0; m < 2; m++) {   /* 0: as run, 1: research frame logging off */
            s_app_work = s_app_snap;
            g_hal = s_hal_snap;
            s_app_work.log_research = (m == 0) ? s_app_snap.log_research : false;
            b->head = b->tail = 0u;
            t0 = st_now();
            pen_app_stage_tick(&s_app_work, &s_sens_snap);
            t1 = st_now();
            part[m] = ((float)st_elapsed(t0, t1) - over) / tpi;
        }
        s_app_work = s_app_snap;
        t0 = st_now();
        kf_est_tick(&s_app_work.ctrl.kf, &s_app_work.ctrl.prm, s_app_work.ph, true);
        t1 = st_now();
        part[2] = ((float)st_elapsed(t0, t1) - over) / tpi;
        static uint8_t frame[PENLOG_RESEARCH_LEN];
        memset(frame, 0x5A, sizeof(frame));
        t0 = st_now();
        const uint16_t crc = crc16_ccitt(frame, sizeof(frame));
        t1 = st_now();
        part[3] = ((float)st_elapsed(t0, t1) - over) / tpi;
        printf("BENCH breakdown (last steady tick, replayed on a copy of the state): stage tick %.0f; without the "
               "research frame %.0f (frame pack + CRC + ring copy = %.0f); Kalman estimator, both axes %.0f; "
               "table CRC-16 of the %u-byte research payload %.0f (crc 0x%04x) instructions\n",
               (double)part[0], (double)part[1], (double)(part[0] - part[1]), (double)part[2],
               (unsigned)sizeof(frame), (double)part[3], (unsigned)crc);
    }
    return 0;
}
