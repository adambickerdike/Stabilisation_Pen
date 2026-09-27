/*
 * test_main.c - test runner entry point and case table.
 * Usage: pen_tests [vector_dir] [filter]
 *        pen_tests --golden-log <out.bin>     (writes the golden log file)
 * Test infrastructure.
 */
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "params_gen.h"
#include "tr.h"

/* ---- test cases (defined in tests/test_*.c) ---- */
#define TEST_LIST(X)                          \
    X(test_crc_known_answer)                  \
    X(test_log_header_roundtrip)              \
    X(test_log_records_roundtrip)             \
    X(test_log_unit_conversion)               \
    X(test_log_corruption_detected)           \
    X(test_log_golden_file)                   \
    X(test_biquad_vs_scipy)                   \
    X(test_jacobian_vs_frames)                \
    X(test_jacobian_properties)               \
    X(test_limiter_radial_properties)         \
    X(test_limiter_slew_properties)           \
    X(test_authority_smoothing)               \
    X(test_kf_step_golden)                    \
    X(test_kf_estimator_sequence_golden)      \
    X(test_kf_float32_covariance_health)      \
    X(test_bpf_estimator_golden)              \
    X(test_replay_sim_kf)                     \
    X(test_replay_sim_bpf)                    \
    X(test_replay_sim_ffc)                    \
    X(test_guided_tracks_template)            \
    X(test_current_loop_bridge_mapping)       \
    X(test_current_loop_step_response)        \
    X(test_current_loop_voltage_clamp)        \
    X(test_current_loop_offset_calibration)   \
    X(test_closed_loop_step_response)         \
    X(test_closed_loop_bandwidth)             \
    X(test_closed_loop_hold_no_vsat)          \
    X(test_thermal_model_steady_state)        \
    X(test_thermal_resistance_estimate)       \
    X(test_thermal_ntc_and_derating)          \
    X(test_safety_hall_stuck)                 \
    X(test_safety_hall_residual_and_range)    \
    X(test_safety_headroom)                   \
    X(test_safety_optical)                    \
    X(test_safety_battery)                    \
    X(test_safety_overcurrent_latch_clear)    \
    X(test_safety_ml_trips)                   \
    X(test_sm_transition_table)               \
    X(test_sm_fault_policies)                 \
    X(test_ml_guard_rejects)                  \
    X(test_ml_guard_fallback_within_20ms)     \
    X(test_ml_window)                         \
    X(test_calib_record_roundtrip)            \
    X(test_calib_record_corruption)           \
    X(test_calib_spectral_f0)                 \
    X(test_calib_gate_rule)                   \
    X(test_hall_conversion)                   \
    X(test_fusion_matches_sim_scheme)         \
    X(test_attitude_from_gravity)             \
    X(test_system_hall_frozen_detect)         \
    X(test_system_fault_sequences)

#define DECL(name) void name(void);
TEST_LIST(DECL)
#undef DECL

typedef struct {
    const char *name;
    tr_fn_t fn;
} tr_case_t;

#define ENTRY(name) {#name, name},
static const tr_case_t CASES[] = {TEST_LIST(ENTRY)};
#undef ENTRY

int pen_write_golden_log(const char *path);   /* test_log.c */

/* ---- runner state ---- */
static const char *s_vecdir = "tests/vectors";
static uint32_t s_checks, s_fail_case, s_fail_total;
static char s_pathbuf[512];

const char *tr_vec_path(const char *name)
{
    snprintf(s_pathbuf, sizeof(s_pathbuf), "%s/%s", s_vecdir, name);
    return s_pathbuf;
}

uint32_t tr_case_failures(void) { return s_fail_case; }

void tr_log(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fputs("    ", stdout);
    vprintf(fmt, ap);
    fputc('\n', stdout);
    va_end(ap);
}

void tr_check(bool ok, const char *expr, const char *file, int line)
{
    s_checks++;
    if (!ok) {
        s_fail_case++;
        s_fail_total++;
        if (s_fail_case <= 8u) {
            printf("    FAIL %s:%d: %s\n", file, line, expr);
        }
    }
}

void tr_check_close(double a, double b, double atol, double rtol, const char *ea, const char *eb, const char *file,
                    int line)
{
    const double tol = atol + rtol * fabs(b);
    const bool ok = isfinite(a) && isfinite(b) && fabs(a - b) <= tol;
    s_checks++;
    if (!ok) {
        s_fail_case++;
        s_fail_total++;
        if (s_fail_case <= 8u) {
            printf("    FAIL %s:%d: %s = %.9g vs %s = %.9g (|d| = %.3g > tol %.3g)\n", file, line, ea, a, eb, b,
                   fabs(a - b), tol);
        }
    }
}

void tr_rng_seed(tr_rng_t *r, uint32_t seed)
{
    r->s = seed ? seed : 0x9E3779B9u;
    r->have = false;
}

uint32_t tr_rng_u32(tr_rng_t *r)
{
    uint32_t x = r->s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    r->s = x;
    return x;
}

double tr_rng_uniform(tr_rng_t *r)
{
    return (double)(tr_rng_u32(r) >> 8) / 16777216.0;
}

double tr_rng_normal(tr_rng_t *r)
{
    if (r->have) {
        r->have = false;
        return r->spare;
    }
    double u1 = tr_rng_uniform(r);
    const double u2 = tr_rng_uniform(r);
    if (u1 < 1e-12) {
        u1 = 1e-12;
    }
    const double m = sqrt(-2.0 * log(u1));
    r->spare = m * sin(6.283185307179586 * u2);
    r->have = true;
    return m * cos(6.283185307179586 * u2);
}

int main(int argc, char **argv)
{
    if (argc >= 3 && strcmp(argv[1], "--golden-log") == 0) {
        return pen_write_golden_log(argv[2]);
    }
    if (argc >= 2) {
        s_vecdir = argv[1];
    }
    const char *filter = (argc >= 3) ? argv[2] : NULL;
    printf("pen firmware unit tests: params yaml %s [%s], model %s\n", PEN_PARAMS_YAML_VERSION, PEN_PARAMS_YAML_SHA16,
           PEN_PARAMS_MODEL_VERSION);
    uint32_t n_run = 0, n_fail = 0;
    for (size_t k = 0; k < sizeof(CASES) / sizeof(CASES[0]); k++) {
        if (filter != NULL && strstr(CASES[k].name, filter) == NULL) {
            continue;
        }
        s_fail_case = 0;
        const uint32_t c0 = s_checks;
        printf("[ RUN  ] %s\n", CASES[k].name);
        fflush(stdout);
        CASES[k].fn();
        const uint32_t nc = s_checks - c0;
        if (nc == 0u) {
            s_fail_case++;
            s_fail_total++;
            printf("    FAIL: no checks executed\n");
        }
        printf("[ %s ] %s (%u checks)\n", s_fail_case ? "FAIL" : " OK ", CASES[k].name, (unsigned)nc);
        fflush(stdout);
        n_run++;
        if (s_fail_case) {
            n_fail++;
        }
    }
    printf("SUMMARY: %u test cases, %u passed, %u failed; %u checks, %u failed checks\n", (unsigned)n_run,
           (unsigned)(n_run - n_fail), (unsigned)n_fail, (unsigned)s_checks, (unsigned)s_fail_total);
    return n_fail == 0u ? 0 : 1;
}
