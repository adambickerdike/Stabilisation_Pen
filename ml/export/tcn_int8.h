/*
 * tcn_int8.h - int8 inference of the causal TCN disturbance predictor
 * (docs/icd.md section 5).  Plain C99 reference kernels.
 *
 * EVIDENCE STATUS: the model is trained on SIMULATION / synthetic data only.
 * It has never seen a human recording; see ml/model_card.md before use.
 *
 * Contract: input = the last 64 page-displacement increments dp (x, y) in um at
 * 250 Hz (oldest first) and the Kalman phase-rate estimate f_est in Hz; output
 * = predicted disturbance d_hat (x, y) at t + 6 ms, int16 in 0.1 um (the research
 * log unit of dhat_x/dhat_y, docs/icd.md s4.2).
 *
 * Structure: 6 tree levels (a causal dilated TCN, kernel 2, dilations 1..32,
 * evaluated at the newest sample), a hidden FC head and an int16 output layer.
 * Every level is one fully connected layer over contiguous (older, newer)
 * channel pairs (NHWC), so each call of tcn_fc_s8() can be replaced by
 * arm_fully_connected_s8() of CMSIS-NN with the same parameters (per-tensor
 * multiplier/shift, filter_offset 0, input_offset = -zero_point_in).
 * Requantisation is bit-identical to CMSIS-NN arm_nn_requantize().
 *
 * Build notes: compile with -ffp-contract=off so the float -> int8 input
 * quantiser rounds exactly like the Python reference (ml/quantize.py).
 * The functions are reentrant: all state lives in caller-provided buffers.
 */
#ifndef TCN_INT8_H
#define TCN_INT8_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TCN_W 64          /* samples per window (256 ms at 250 Hz) */
#define TCN_CIN 3         /* channels: dp_x, dp_y, f_est */
#define TCN_NLEVELS 6

/* One fully connected int8 layer (CMSIS-NN arm_fully_connected_s8 semantics). */
typedef struct {
    const int8_t *w;      /* [c_out][n_in], symmetric int8 (zero point 0) */
    const int32_t *bias;  /* [c_out], scale = s_in * s_w (the bias CMSIS-NN expects) */
    const int32_t *bias_folded; /* bias + in_offset * sum(w row): exact, used by the plain-C loop */
    int32_t n_in;         /* inputs per output row (2 * channels for tree levels) */
    int32_t c_out;
    int32_t in_offset;    /* = -input zero point */
    int32_t out_offset;   /* = output zero point */
    int32_t mult;         /* Q31 requantisation multiplier (per tensor) */
    int32_t shift;        /* TFLite convention: > 0 left shift, < 0 right shift */
    int32_t act_min;      /* ReLU folded in: act_min = output zero point */
    int32_t act_max;
} tcn_fc_params_t;

/* Status bits returned by tcn_predict() (inputs for the ML guard, ml_guard.c). */
#define TCN_ST_INPUT_NAN      0x01u  /* a NaN/Inf input was replaced by 0 */
#define TCN_ST_INPUT_CLIPPED  0x02u  /* |dp| > 400 um per sample (normal during fast strokes) */
#define TCN_ST_OUTPUT_SAT     0x04u  /* |d_hat| reached the int16 limit (3.2767 mm) */

/* Scratch bytes needed by tcn_run_q() (ping-pong activation buffers). */
uint32_t tcn_scratch_bytes(void);

/* Integer core: in = int8 window [64][3] (oldest first), out = int16 [2] in 0.1 um.
 * scratch must hold tcn_scratch_bytes() bytes. */
void tcn_run_q(const int8_t in[TCN_W][TCN_CIN], int16_t out_q[2], int8_t *scratch);

/* float -> int8 input quantiser (same float32 arithmetic as ml/quantize.py). */
uint32_t tcn_quantize_window(const float dp_um[TCN_W][2], float f_est_hz, int8_t q[TCN_W][TCN_CIN]);

/* Convenience: quantise, run, dequantise.  dhat_um[2] in um.  Returns status bits. */
uint32_t tcn_predict(const float dp_um[TCN_W][2], float f_est_hz, float dhat_um[2], int8_t *scratch);

/* Low 32 bits of the SHA-256 of the quantised parameters (event 0x0005 argument). */
uint32_t tcn_model_hash_low32(void);

/* Exposed for unit tests: CMSIS-NN compatible requantisation. */
int32_t tcn_requantize(int32_t val, int32_t mult, int32_t shift);

#ifdef __cplusplus
}
#endif
#endif /* TCN_INT8_H */
