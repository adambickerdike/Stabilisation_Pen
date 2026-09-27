/*
 * tr.h - minimal self-contained test runner (host and QEMU/semihosting).
 * Test infrastructure; may use double precision for reference arithmetic.
 */
#ifndef PEN_TR_H
#define PEN_TR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef void (*tr_fn_t)(void);

void tr_check(bool ok, const char *expr, const char *file, int line);
void tr_check_close(double a, double b, double atol, double rtol, const char *ea, const char *eb, const char *file,
                    int line);
void tr_log(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
/* path of a vector file: <vector dir>/<name> */
const char *tr_vec_path(const char *name);
uint32_t tr_case_failures(void);

#define CHECK(cond) tr_check((cond), #cond, __FILE__, __LINE__)
#define CHECK_CLOSE(a, b, atol, rtol) tr_check_close((double)(a), (double)(b), (atol), (rtol), #a, #b, __FILE__, __LINE__)

/* deterministic PRNG for tests (xorshift32 + Box-Muller) */
typedef struct {
    uint32_t s;
    bool have;
    double spare;
} tr_rng_t;
void tr_rng_seed(tr_rng_t *r, uint32_t seed);
uint32_t tr_rng_u32(tr_rng_t *r);
double tr_rng_uniform(tr_rng_t *r);   /* [0, 1) */
double tr_rng_normal(tr_rng_t *r);

#include "test_list.h"

#endif /* PEN_TR_H */
