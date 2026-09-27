/*
 * vec.h - reader for golden vector files written by tools/gen_vectors.py.
 * Format "PENVEC01": magic[8] | n_rows u32 | n_cols u32 | n_cols x 32-byte
 * column names | n_rows x n_cols float32 little-endian (row major).
 * Test infrastructure (static arena, no malloc).
 */
#ifndef PEN_VEC_H
#define PEN_VEC_H

#include <stdbool.h>
#include <stdint.h>

#define VEC_MAX_COLS 96
#define VEC_NAME_LEN 32

typedef struct {
    uint32_t rows, cols;
    char names[VEC_MAX_COLS][VEC_NAME_LEN];
    const float *data;
} vec_t;

/* Loads into a shared static arena (one file at a time). */
bool vec_load(const char *name, vec_t *v);
int vec_col(const vec_t *v, const char *name);          /* -1 if absent */
static inline float vec_at(const vec_t *v, uint32_t row, int col)
{
    return v->data[(uint64_t)row * v->cols + (uint32_t)col];
}

#endif /* PEN_VEC_H */
