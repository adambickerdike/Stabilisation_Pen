/*
 * vec.c - golden vector reader (see header). Test infrastructure.
 */
#include "vec.h"

#include <stdio.h>
#include <string.h>

#include "tr.h"

#define VEC_ARENA_FLOATS (400u * 1024u)   /* 1.6 MB */
static float s_arena[VEC_ARENA_FLOATS];

static uint32_t rd_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

bool vec_load(const char *name, vec_t *v)
{
    const char *path = tr_vec_path(name);
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        tr_log("cannot open %s", path);
        return false;
    }
    uint8_t hdr[16];
    bool ok = fread(hdr, 1, sizeof(hdr), f) == sizeof(hdr) && memcmp(hdr, "PENVEC01", 8) == 0;
    if (ok) {
        v->rows = rd_u32(hdr + 8);
        v->cols = rd_u32(hdr + 12);
        ok = v->cols > 0u && v->cols <= VEC_MAX_COLS && (uint64_t)v->rows * v->cols <= VEC_ARENA_FLOATS;
    }
    for (uint32_t c = 0; ok && c < v->cols; c++) {
        ok = fread(v->names[c], 1, VEC_NAME_LEN, f) == VEC_NAME_LEN;
        v->names[c][VEC_NAME_LEN - 1] = '\0';
    }
    if (ok) {
        const size_t n = (size_t)v->rows * v->cols;
        /* the files are little-endian float32; both targets are little-endian */
        ok = fread(s_arena, sizeof(float), n, f) == n;
        v->data = s_arena;
    }
    fclose(f);
    if (!ok) {
        tr_log("bad vector file %s", path);
    }
    return ok;
}

int vec_col(const vec_t *v, const char *name)
{
    for (uint32_t c = 0; c < v->cols; c++) {
        if (strcmp(v->names[c], name) == 0) {
            return (int)c;
        }
    }
    tr_log("vector column '%s' missing", name);
    return -1;
}
