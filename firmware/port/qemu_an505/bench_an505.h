/*
 * bench_an505.h - instruction-count estimate of the real-time bodies on QEMU
 * mps2-an505 (see bench_an505.c). Test infrastructure.
 */
#ifndef PEN_BENCH_AN505_H
#define PEN_BENCH_AN505_H

/* Runs the closed-loop scenario, prints "BENCH ..." lines; returns 0. */
int pen_bench_run(void);

#endif /* PEN_BENCH_AN505_H */
