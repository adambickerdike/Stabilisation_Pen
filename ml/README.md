# ml/: causal disturbance predictor (training, comparison, edge deployment)

> **Evidence status: SIMULATION / synthetic data.**
> - The data is synthetic handwriting (sigma-lognormal, `stabpen.signals`) plus synthetic tremor, with 60 runs of the coupled simulator (`sim/pensim`) as a realism check.
> - No human recording, bench measurement or nRF5340 hardware measurement exists behind any number here.
> - Nothing here implies clinical benefit.
> - Timing numbers are calculations plus an executed-instruction count on an emulated Cortex-M33. QEMU is not cycle accurate.

## Summary

**Contract implemented as written** (`docs/icd.md` §5):

- Input: 64 increments Δp_H (x, y, µm) at 250 Hz, plus f_est.
- Output: d̂ (x, y, µm) at h = 6 ms.
- Quantisation: int8.
- Budget: ≤ 35 k MAC, ≤ 32 kB, ≤ 8 kB, ≤ 1 ms at 128 MHz.

**Model.** `tcn_s` is a causal dilated TCN (kernel 2, dilations 1–32, receptive field = W = 64). It is evaluated only at the newest sample, so it reduces to 6 stride-2 "pair" layers plus a 2-layer head. It has 5,942 parameters and 16,688 MAC per inference.

**In-distribution result (80 test writers).** At matched false correction (gain frozen on validation for FC ≤ 25 µm RMS on no-tremor writing), the residual ratio (all bands) is:

| Method | Residual ratio (all bands) |
|---|---|
| TCN | 0.48 [0.41, 0.55] |
| f_est-scheduled least-squares FIR | 0.76 |
| Kalman oscillator + frequency gate, tuned | 0.80 |
| Kalman oscillator, tuned | 0.81 |
| Band-pass + extrapolation | 0.95 |
| BMFLC | 0.96 |

- The TCN leads in every band, including 4–7 Hz, where every conventional estimator stays at 0.97–1.01.
- Paired writer-bootstrap difference against the strongest baseline: −0.28 [−0.33, −0.24].
- The unseen 7–8 Hz band behaves the same: 0.55 vs 0.83.

**The advantage does not survive plausible model mismatch:**

- **Tremor outside the training ranges:** the TCN reaches 0.83. The f_est-scheduled linear baseline reaches 0.87 (difference −0.04 [−0.10, +0.03], not significant).
- **Simulator realism (coupled hand–pen–paper housing):** 0.96 for every method on the full band. On the 3–15 Hz band the TCN reaches 0.73 against 0.77 for the linear baseline and 0.79 for the gated Kalman. At 9–11 Hz the TCN and the conventional estimators are within 0.03.
- **Fast writing:** false correction rises from about 25 µm to 73–155 µm for every method, the TCN included.

**Deployment:**

- int8 costs almost nothing: 0.475 → 0.476, with an RMS prediction difference of 11.9 µm.
- The C reference is bit-exact with the Python integer reference on 20,000 test windows, on host GCC, on clang with UBSan, and on an emulated Cortex-M33.
- ARM `-O2` object: 1.2 kB code + 7.3 kB weights. RAM: 640 B.
- Time at 128 MHz: 0.28 ms estimated with CMSIS-NN (0.89 ms pessimistic). The plain-C reference executes 118 k instructions (QEMU count), i.e. 0.92–1.48 ms for CPI 1.0–1.6, at the limit. Energy about 6.5 µJ per inference.

**The contract's guard, as written, suppresses the predictor.** Its "|d̂ − d̂_KF| > 150 µm for > 20 ms" rule uses the frozen controller KF as reference, and that KF barely moves at 250 Hz. It rejects 18 % of ticks and returns the TCN to 0.94.

**Verdict:** a learned predictor is **not justified for deployment or for any claim at this stage**. It is justified as the lead candidate for the real-data bake-off (EXP-E01, REQ-ML-001), and the edge path is ready.

## Contents

- (a) [Which product features need custom training](#a-which-product-features-need-custom-training)
- (b) [Pipeline](#b-pipeline)
- (c) [Results](#c-results)
- (d) [Limitations and real-data plan](#d-limitations-and-real-data-plan)
- [Proposed contract changes](#proposed-changes-to-the-contract-docsicdmd-5)
- [Conclusion](#conclusion-is-a-learned-predictor-justified-now)
- [File map](#file-map)

---

## (a) Which product features need custom training

| Product feature | Custom training? | Approach now | Data and labels | Licences | Main risks |
|---|---|---|---|---|---|
| **Disturbance (tremor) predictor** (this directory) | **Yes, if a learned model is used at all.** The conventional path needs tuning only (KF with per-user gate). | Conventional KF with frequency gate in firmware. Learned TCN behind the ML guard, disabled until REQ-ML-001 is met on real data. | Synthetic and simulator now; see (d) for EXP-H01, bench and self-supervision. No public dataset records nib or housing motion during writing with tremor (research synthesis, gap 1). | Own data only; participant consent must cover model training. | Distribution shift (§c.4); false correction of intended strokes; confident-but-wrong assistance, the worst case in HAP-23; the guard design. |
| **Pen-state / contact classification** (down, up, hover, touchdown and lift events) | **No learned model at first.** | Hysteretic thresholds on the axial force (Hall z → F_ax, `CAL_AXIAL`) plus optical validity and lift height; debounce. A tiny tree (emlearn, MIT, EML-29) only if thresholds fail on bench data. | Self-labelled from the force channel on the bench (EXP-B05); human edge cases (light writers, stick-slip) from EXP-H01. | Own data. | Light-pressure writers near F_pre; pressure modulation from correction (~0.1 N) chattering the threshold; lift during tremor bursts. |
| **Handwriting recognition** | **No, initially.** | Off-the-shelf on-device recogniser: ML Kit Digital Ink (free, on device, 300+ languages, no published accuracy; OPT-20). MyScript for maths and diagrams only under a commercial licence (OPT-21/22). Feed reconstructed trajectories (optical), not raw IMU (OPT-16/18). | Evaluate CER on our own pen recordings of target users (REQ-APP-001, EXP-A01): ink from the stroke layer (`docs/icd.md` §4.3), transcripts by participants. Fine-tuning would need our own consented data. | IAM-OnDB terms unverified; DeepWriting non-commercial; MathWriting CC BY-NC-SA 4.0; CASIA unverified; OnHW licence unstated (OPT-15, 28–31). Use these for benchmarking only, never for shipped training. | Relative-position drift and scale error of pen-on-paper trajectories; tremor-affected ink and micrographia outside the recognisers' training data; vendor terms can change. |
| **Personalisation** | **No training; per-user calibration.** | `CAL_USER` record: tremor f0, f_gate and width, authority cap g_max, q_lim, γ, from a 30–60 s calibration task (spiral + writing), estimated with the KF / spectral method. If the learned predictor is ever enabled, its per-user part is the output-gain / false-correction operating point chosen the way this pipeline chooses it (§c.3), not on-device gradient training. | Calibration recordings per user; re-calibration on demand. | Own data. | Day-to-day and medication-state variability; a calibration taken without tremor; users gaming the authority cap. |
| **Note search and summary** | **No training.** | Retrieval-grounded: search over the recognised-text layer, whose spans link to stroke ids (`docs/icd.md` §4.5); summaries cite note spans. Evaluate with AIS-style attribution plus citation recall and precision, and faithfulness against recognition error (OPT-32–35). | None to train. Evaluation needs human-rated summaries of consented notes. | LLM or service terms, privacy consent for any server-side step. | Recognition errors propagating into confident summaries; privacy of personal notes. |

**Conclusion of (a).** Only the disturbance predictor is a custom-training problem. Its training labels cannot come from free human writing alone (§d). Everything else is thresholds, calibration or off-the-shelf components that need *evaluation* on our data, not training.

---

## (b) Pipeline

`ml/run_all.sh` reproduces every number (about 30–35 min on 4 shared cores; about 12 min of it is training). It writes only to `ml/` (`ml/runs/` is git-ignored), `data/` and `results/ml/`. It never writes byte-code or numba caches into `stabpen/` or `sim/`.

| Step | Module | What it does |
|---|---|---|
| 1 | `ml/synth.py` | Generator: writer profiles, intended motion (lognormal handwriting + randomised deliberate features via `PathBuilder`), tremor segments (a line-by-line re-implementation of `stabpen.signals.tremor` that also exposes the oscillator state; equality is unit-tested), kinematic housing, and the sensor model (latency 2–3 ms, 2.5–3.5 µm RMS noise, ±1 % scale, 250 Hz). See `data/dataset_card.md`. |
| 2 | `ml/datasets.py` | Splits by writer id: 240 train / 40 val / 80 test / 30 frequency-holdout writers, a no-tremor feature course, two stress sets, and a simulator realism set of 60 runs. Leakage checks, manifest, schema examples. |
| 3 | `ml/baselines.py`, `ml/tune_baselines.py` | Zero; band-pass + extrapolation (`core.py` mode 2 at 250 Hz); Kalman oscillator (verbatim `_kf_step` port + phase-rate adaptation, equality tested against `sim.pensim.core._kf_step.py_func`); KF with NIS confidence, frequency gate and authority smoothing; BMFLC (NLMS, pre-filter gain and phase inverted per basis frequency); least-squares direct h-step FIR predictor (AR-LS), global and f_est-scheduled; two oracles. All hyperparameters are chosen on **validation** with the network's criterion; grids were widened until every optimum was interior or the criterion was flat (§c.8). |
| 4 | `ml/models.py`, `ml/train.py` | TCN tree (see the Summary). Loss: weighted MSE on d(t + h), weight 1 on tremor ticks and 4 on no-tremor ticks (penalty on false correction). AdamW, one-cycle cosine schedule, seed 7, 2 threads, 14 epochs of 1.5 M windows. Epoch selected on validation. |
| 5 | `ml/quantize.py` | int8 post-training quantisation: per-tensor symmetric int8 weights, int8 activations (zero point −128 after ReLU), int32 bias, CMSIS-NN requantisation, int16 output in 0.1 µm. Calibration: 50 k training windows, 99.99th percentile, chosen on validation over max and the 99.9th percentile. Includes the integer reference `run_int8`. |
| 6 | `ml/export_c.py` + `ml/export/` | Generates `tcn_weights.h` and `test_vectors.h`. Builds and runs `test_host.c` with gcc `-O2 -Werror` and clang UBSan (trap mode). Cross-compiles `tcn_int8.c` for Cortex-M33 and reports section sizes. Runs the same test on QEMU `mps2-an505` (Cortex-M33) and counts executed instructions. |
| 7 | `ml/budget.py` | MACs, parameter and activation memory, cycles (plain C: QEMU instructions × CPI 1.0/1.3/1.6; CMSIS-NN: 0.5 or 0.15 MAC/cycle + 300 cycles per call), time at 64 and 128 MHz, energy (183 / 155 pJ per cycle, EML-02), and the streaming alternative. |
| 8 | `ml/evaluate.py`, `ml/metrics.py` | Residual ratio per band, false correction, matched-FC gains frozen on validation (10 / 25 / 50 µm and unit gain), 2000-sample writer bootstrap with paired differences, feature-course distortion, the ICD guard, figures with CSV data twins. |
| 9 | `ml/tests/test_ml.py` | 15 tests: KF port = simulator; tremor wrapper = `stabpen`; oscillator oracle; causality and window-only dependence; tree = streaming dilated TCN; requantisation vs an independent scalar implementation; metrics; leakage; schema; int8 vs float; C host bit-exactness. Run: `python3 -m pytest -p no:cacheprovider ml/tests -q`. |

**Definitions** (`ml/metrics.py`):

- **Scored ticks:** t ≥ 1 s and pen down at t_k + h.
- **Residual ratio:** RR_b(g) = √(Σ|d − g·d̂|² / Σ|d|²) over tremor ticks of band b (band = nominal f0 of the segment), pooled over writers. RR = 1 means no benefit.
- **False correction:** FC(g) = g · RMS|d̂| over no-tremor ticks (µm).
- **Matched false correction:** g = min(g_opt, F / FC_val(1), 2) is chosen on validation writers, then frozen for all test sets.

**Time stamps.** A sample is stamped when it becomes available and describes the housing 2–3 ms earlier. The *physical* horizon is therefore 8–9 ms. Conventional estimators extrapolate by h + 2.5 ms (latency known from calibration); the network learns it. See proposed change 1.

**Why the tree formulation.** A kernel-2 dilated causal stack with dilations 1…32 has receptive field 64 = W. Its value at the newest sample depends only on the binary tree of positions T − 2^l·j. That makes each layer a fully-connected layer over contiguous (older, newer) channel pairs, which is one `arm_fully_connected_s8` call in CMSIS-NN with no dilated kernel. By comparison:

- Recomputing the dilated convolution at all 64 positions would cost 319 k MAC, 9× over budget.
- The streaming alternative with cached layer states costs 5.8 k MAC per step, plus 1.6 kB of state.

The equivalence of the tree and streaming forms is unit-tested.

**Not built.** The optional GRU:

- A GRU re-run over the 64-sample window costs ≥ 58 k MAC even at 16 hidden units, over budget.
- As a streaming GRU it has unbounded memory, which breaks the window semantics of the contract.

---

## (c) Results

All results are SIMULATION on synthetic data. The CI is a 95 % writer-bootstrap interval (2000 resamples, gains frozen, gain-selection uncertainty not included). Each network was trained with one seed; the three TCN variants (§c.9) land within 0.03 of each other, far less than the gap to the baselines.

### c.1 Headline: residual ratio per band at matched false correction (FC ≤ 25 µm)

Test writers; the 7–8 Hz column comes from the frequency-holdout writers; "all bands" is over the test writers. Source: `results/ml/eval_results.json` (`sets.*.matched.25`); figure `fig_residual_by_band.png`.

| Method | 4–6 Hz | 6–7 Hz | 7–8 Hz (unseen f0) | 8–10 Hz | 10–12 Hz | All bands | FC on test (µm) | Frozen gain g |
|---|---|---|---|---|---|---|---|---|
| zero | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 0 |
| band-pass + extrapolation | 1.01 [1.00, 1.01] | 0.98 [0.98, 0.99] | 0.96 [0.95, 0.97] | 0.91 [0.91, 0.92] | 0.90 [0.89, 0.90] | 0.95 [0.93, 0.97] | 27.7 | 0.06 |
| Kalman oscillator (tuned) | 0.99 [0.98, 1.00] | 0.88 [0.84, 0.99] | 0.85 [0.79, 0.91] | 0.65 [0.58, 0.75] | 0.64 [0.46, 0.85] | 0.81 [0.72, 0.88] | 25.9 | 1.11 |
| Kalman + frequency gate (tuned) | 1.00 [0.99, 1.00] | 0.86 [0.83, 0.99] | 0.83 [0.77, 0.90] | 0.62 [0.55, 0.73] | 0.62 [0.43, 0.84] | 0.80 [0.71, 0.88] | 24.7 | 1.25 |
| Kalman controller, frozen balanced (250 Hz port) | 1.00 [1.00, 1.00] | 0.99 [0.99, 1.00] | 0.99 [0.97, 1.00] | 0.95 [0.91, 0.97] | 0.95 [0.87, 0.99] | 0.97 [0.96, 0.98] | 20.4 | 2.00 (cap) |
| BMFLC | 1.02 [1.02, 1.02] | 1.01 [1.00, 1.02] | 0.99 [0.98, 1.00] | 0.91 [0.90, 0.93] | 0.90 [0.89, 0.91] | 0.96 [0.94, 0.98] | 28.2 | 0.16 |
| AR-LS global (64 taps/axis) | 0.98 [0.97, 0.98] | 0.95 [0.95, 0.97] | 0.94 [0.93, 0.96] | 0.84 [0.81, 0.87] | 0.72 [0.70, 0.74] | 0.88 [0.84, 0.91] | 28.4 | 0.60 |
| AR-LS f_est-scheduled | 0.97 [0.96, 0.98] | 0.81 [0.76, 0.96] | 0.84 [0.80, 0.89] | 0.62 [0.53, 0.73] | 0.53 [0.43, 0.66] | 0.76 [0.67, 0.83] | 26.5 | 0.81 |
| **TCN (float)** | **0.63 [0.56, 0.72]** | **0.50 [0.38, 0.79]** | **0.55 [0.48, 0.64]** | **0.36 [0.28, 0.46]** | **0.32 [0.28, 0.40]** | **0.48 [0.41, 0.55]** | 14.1 | 1.01 |
| **TCN (int8, deployed)** | 0.63 [0.56, 0.72] | 0.50 [0.38, 0.79] | 0.55 [0.48, 0.64] | 0.36 [0.28, 0.46] | 0.32 [0.29, 0.40] | 0.48 [0.41, 0.55] | 16.6 | 1.00 |
| oracle: true d at the newest sample, no prediction | 0.28 | 0.36 | 0.41 | 0.50 | 0.55 | 0.44 | 0 | 0.90 |
| oracle: true oscillator state, extrapolated | 0.06 | 0.04 | 0.07 | 0.06 | 0.06 | 0.06 | 0 | 1.00 |

How to read it:

- **Conventional estimators do not work below about 7 Hz.** This reproduces COR-11 on independent data.
  - Every band-limited estimator (band-pass, BMFLC) selects a 10–12 Hz band. At matched FC it is scaled almost to zero, because intended writing leaks through at 150–470 µm RMS at unit gain.
  - The Kalman estimators help only at 8–12 Hz (0.62–0.65).
- **The TCN is below 0.65 in every band.** It is the only method that beats the no-prediction ("hold") oracle at 8–12 Hz (0.36 and 0.32 against 0.50 and 0.55), i.e. it predicts the phase ahead.
  - At 4–6 Hz it stays far above that oracle (0.63 against 0.28). There, separation from intent, not prediction, limits it.
- **The TCN's frozen gain reaches its optimum at 14 µm FC**, below the 25 µm allowed. The comparison therefore gives the baselines more false-correction room than the TCN uses.
- **The frozen controller KF is not a verdict on the controller.** Its parameters were selected at 2 kHz with a 1.3 ms horizon inside the coupled simulator. At 250 Hz with an 8.5 ms physical horizon it is nearly inert.

### c.2 Paired differences (TCN − baseline, same bootstrap resamples; test writers)

The strongest baseline in every test band, chosen on test (which favours the baselines), is the f_est-scheduled AR-LS; on the holdout writers it is the gated KF.

| TCN minus | 4–6 Hz | 6–7 Hz | 8–10 Hz | 10–12 Hz | All bands |
|---|---|---|---|---|---|
| AR-LS f_est-scheduled | −0.33 [−0.41, −0.25] | −0.29 [−0.39, −0.16] | −0.26 [−0.32, −0.21] | −0.21 [−0.29, −0.14] | −0.28 [−0.33, −0.24] |
| Kalman + gate (tuned) | −0.36 [−0.44, −0.28] | −0.34 [−0.46, −0.19] | −0.27 [−0.34, −0.19] | −0.30 [−0.47, −0.13] | −0.32 [−0.38, −0.26] |

On the frequency-holdout writers (7–8 Hz): TCN − gated KF = −0.28 [−0.35, −0.22]; TCN − scheduled AR-LS = −0.29 [−0.34, −0.24].

### c.3 Other operating points (test, all bands; figure `fig_operating_curves.png`)

| FC target on validation | Kalman + gate | AR-LS scheduled | TCN float | TCN int8 |
|---|---|---|---|---|
| ≤ 10 µm | 0.90 | 0.88 | 0.56 | 0.61 |
| ≤ 25 µm | 0.80 | 0.76 | 0.48 | 0.48 |
| ≤ 50 µm | 0.78 | 0.72 | 0.48 | 0.48 |
| unit gain (as designed / trained) | 0.82 (FC 20 µm) | 0.73 (FC 33 µm) | 0.48 (FC 14 µm) | 0.48 (FC 17 µm) |

int8 matters only at the tightest point (≤ 10 µm). Its no-tremor output floor is about 2.5 µm higher, so the gain must drop further.

### c.4 Robustness to distribution shift (all bands, gains frozen for FC ≤ 25 µm; figure `fig_distribution_shift.png`)

Each cell gives RR with the FC reached on that set in parentheses (µm).

| Set (writers) | Kalman + gate | AR-LS scheduled | BMFLC | TCN | TCN int8 | TCN − AR-LS sched. | TCN − KF+gate | Hold oracle |
|---|---|---|---|---|---|---|---|---|
| test (80) | 0.80 (25) | 0.76 (27) | 0.96 (28) | 0.48 (14) | 0.48 (17) | −0.28 [−0.33, −0.24] | −0.32 [−0.38, −0.26] | 0.44 |
| frequency holdout 7–8 Hz (30) | 0.83 (28) | 0.84 (31) | 0.99 (32) | 0.55 (17) | 0.55 (20) | −0.29 [−0.34, −0.24] | −0.28 [−0.35, −0.22] | 0.41 |
| stress: tremor model (30) | 0.97 (25) | 0.87 (30) | 0.98 (33) | **0.83** (14) | 0.83 (16) | **−0.04 [−0.10, +0.03]** | −0.14 [−0.22, −0.08] | 0.44 |
| stress: fast writing (30) | 0.99 (86) | 0.98 (155) | 0.99 (87) | 0.70 (**73**) | 0.70 (78) | −0.28 [−0.33, −0.24] | −0.28 [−0.39, −0.19] | 0.43 |
| simulator realism, full band (12 seeds) | 0.97 (12) | 0.96 (14) | 1.00 (7) | 0.96 (14) | 0.96 (15) | −0.00 [−0.00, 0.00] | −0.01 [−0.01, −0.00] | 0.23 |
| simulator realism, 3–15 Hz (12 seeds) | 0.79 (11) | 0.77 (8) | 0.96 (6) | **0.73** (10) | 0.73 (10) | **−0.04 [−0.05, −0.03]** | −0.06 [−0.07, −0.06] | 0.41 |

Realism per band (3–15 Hz scoring; RR):

| f0 | Kalman + gate | AR-LS sched. | TCN | TCN int8 | Hold oracle |
|---|---|---|---|---|---|
| 4.5 Hz | 1.00 | 0.98 | 0.92 | 0.91 | 0.27 |
| 6 Hz | 0.97 | 0.91 | 0.84 | 0.83 | 0.33 |
| 9 Hz | 0.67 | 0.68 | 0.65 | 0.65 | 0.43 |
| 11 Hz | 0.59 | 0.58 | 0.57 | 0.57 | 0.52 |

How to read it:

- **Tremor model:** when the tremor has faster frequency and amplitude wander, a stronger harmonic at random phase and a broadband part, the TCN keeps only a non-significant edge over the scheduled linear model.
- **Fast writing:** writing faster than any training writer (50 % of intended velocity energy in 4–7 Hz) breaks the *false-correction* calibration of every method. Gains frozen for 25 µm give 73–155 µm. The TCN still has the lowest residual.
- **Simulator realism:** the coupled simulator's housing disturbance holds 40–68 % of its power below 3 Hz. This is a slow path divergence that tremor causes through contact and hand dynamics, and no causal estimator predicts it; hence 0.96 for all methods on the full band.
  - On the 3–15 Hz part, scored as `sim/pensim/evaluate.py` scores its band error, the TCN's lead shrinks to 0.04–0.06.
  - At 9–11 Hz that lead is at most 0.03, and the TCN only exceeds the linear or KF estimators meaningfully at 4.5–6 Hz.
  - The realism CIs are narrow because the 12 seeds share one tremor specification per f0. They measure seed variation only.

### c.5 No-tremor distortion on the canonical feature course (never in training; figure `fig_feature_course.png`)

Values are RMS / maximum of |g·d̂| in µm, pen down, gains frozen for FC ≤ 25 µm, over 18 runs (3 scales × 3 speeds × 2 sensor draws).

| Method | Overall RMS | Corners | Dots | Hatching (4 Hz) | Fast stroke | Circle | Spiral |
|---|---|---|---|---|---|---|---|
| Kalman + gate | 16.4 | 3 / 15 | 36 / 162 | 25 / 144 | 44 / 164 | 13 / 77 | 4 / 57 |
| BMFLC | 20.8 | 7 / 22 | 11 / 78 | 29 / 86 | 90 / 283 | 8 / 33 | 10 / 64 |
| AR-LS scheduled | 23.0 | 13 / 75 | 15 / 56 | 30 / 188 | 128 / 406 | 9 / 32 | 9 / 37 |
| TCN float | 14.5 | 12 / 125 | 7 / 54 | 7 / 167 | 7 / 49 | 7 / 65 | 21 / 157 |
| TCN int8 | 17.6 | 13 / 129 | 7 / 54 | 8 / 189 | 10 / 57 | 11 / 88 | 25 / 196 |

- On RMS, every method stays below the 50 µm REQ-CTRL-005 limit, which applies to the whole controller.
- Against the 100 µm corner/dot limit:
  - the TCN exceeds it at corners (maximum 125 µm; int8 129 µm);
  - the Kalman variants exceed it at dots (143–162 µm), and the band-pass does too (118 µm);
  - BMFLC and the scheduled AR-LS stay within it at corners and dots, but reach 283–406 µm on the fast stroke.
- The TCN's maxima are brief spikes (corners 125 µm, hatching 167 µm, spiral 157 µm); its RMS on the fast stroke (7 µm) and on hatching (7 µm) is the lowest of all methods.
- These are estimator outputs at frozen gains. Ink error additionally depends on the servo and the stage limits.
- A time-domain view is in `fig_example_trace.png`: the TCN tracks a 5.7 Hz, 0.69 mm tremor while BMFLC runs out of phase, and on no-tremor writing BMFLC produces ±150 µm of false correction.

### c.6 The ICD §5 guard applied to the int8 TCN (test writers)

With the frozen controller KF (balanced or assertive) as reference and fallback, the guard rejects **18.3 % of scored ticks**. Nearly all rejections come from the |d̂ − d̂_KF| > 150 µm for > 20 ms rule; the q_lim and 50 mm/s rules add fewer. The TCN's residual ratio goes from 0.48 to **0.94**. The KF reference is nearly inert at 250 Hz, so any correction of a tremor larger than about 0.2 mm is "rejected". See proposed change 3.

### c.7 Quantisation, C port, size, time and energy

**int8 vs float (`results/ml/quantization.json`, `fig_quantization.png`).**

- RMS prediction difference: 11.9 µm (test), 12.8 µm (holdout), 6.2 µm (feature course), 8.2 µm (realism).
- All-band RR: 0.4752 → 0.4764 (test), 0.552 → 0.554 (holdout).
- FC at unit gain: 13.9 → 16.6 µm.
- Activation saturation is below 0.012 % per layer; the output never saturates.
- Model hash: SHA-256 `…71feeb47` (low 32 bits for event 0x0005).

**C vs Python integer reference: bit-exact (0 LSB) everywhere.** Checked on:

- 20,000 test windows (40,000 outputs), plus 64 embedded integer windows, 32 float-API windows and 104 requantisation edge cases;
- with gcc 13.3 `-O2 -std=c99 -ffp-contract=off -Wall -Wextra -Wpedantic -Werror`;
- with clang UBSan (trap mode: no undefined behaviour);
- on an **emulated Cortex-M33** (QEMU 8.2.2 `mps2-an505`, built with arm-none-eabi-gcc 13.2.1 `-O2`, hard float).

**ARM build** (`-mcpu=cortex-m33 -mfpu=fpv5-sp-d16 -mfloat-abi=hard -mthumb -O2`):

- `tcn_int8.o`: 1,240 B code + 7,292 B read-only data (int8 weights, int32 biases, parameter structs); no `.data` or `.bss`. With `-Os`: 862 B code.
- RAM: 448 B scratch + 192 B int8 window, all caller-provided; 1,152 B if the caller keeps a float window.

**Budget** (`results/ml/budget.json`; ICD limits in the last column):

| Quantity | tcn_s (deployed) | tcn_m (alternative) | ICD budget |
|---|---|---|---|
| MAC per inference (tree) | 16,688 | 31,296 | ≤ 35,000 |
| Parameters | 5,942 | 10,966 | |
| Flash: weights + biases (×2) + structs | 7,376 B | 12,792 B | ≤ 32 kB |
| Activation RAM (int8 / with float window) | 640 B / 1,152 B | 832 B / 1,344 B | ≤ 8 kB |
| Plain C, QEMU executed instructions | 118,359 (7.1 per MAC) | ≈ 222,000 (scaled by MAC) | |
| Plain C time at 128 MHz, CPI 1.0 / 1.3 / 1.6 | 0.92 / 1.20 / 1.48 ms | ≈ 2.3 ms | ≤ 1 ms |
| CMSIS-NN time at 128 MHz, 0.5 / 0.15 MAC per cycle | 0.28 / 0.89 ms | 0.51 / 1.65 ms | ≤ 1 ms |
| Energy per inference, CMSIS central / plain C at CPI 1.3 | 6.5 µJ / 28 µJ | 11.9 µJ | |
| Power at 250 Hz, CMSIS central | 1.6 mW (CPU load 7 %) | 3.0 mW | |
| Streaming alternative: MAC per step / state | 5,792 / 1,603 B | 10,760 / 2,075 B | |

Assumptions and caveats:

- **Plain C:** instructions come from QEMU `-icount`, calibrated with a 2-instruction loop. QEMU is not cycle accurate, so cycles = instructions × assumed CPI, with the 8 kB flash cache assumed warm.
- **Where plain C spends its time:** about 37 % of instructions are per-output requantisation (794 outputs, 256 of them in level 1 with only 6 MACs each).
- **CMSIS-NN:** 0.5 MAC per cycle for optimised int8 on Cortex-M33 (EML-23), 0.15 for small dilated layers on M4 (EML-24), plus 300 cycles per kernel call.
- **Energy:** 183 pJ per cycle is a CoreMark whole-SoC figure (EML-02), not an NN measurement.
- **Consequence:** the plain-C reference meets 1 ms only if CPI ≤ 1.08. **CMSIS-NN (or equivalent SIMD kernels) is required for margin, and nRF5340 DWT cycle measurements are still missing** (EML "must be benchmarked" 1–5).

### c.8 Baseline tuning and fairness (`results/ml/baselines_tuning.json`)

- 69 band-pass, 197 Kalman, 788 gated-Kalman, 79 BMFLC and 10 + 6 AR-LS configurations were evaluated on validation writers.
- A second pass widened every grid whose optimum was on an edge. The Kalman optimum is now interior in all of qj = 30, qt = 3e-8 and r = 1e-8 m². The gated KF adds f_gate = 5.5 Hz; the ungated KF, gate 0, brackets it.
- The band-limited families converge to 10–12 Hz bands, where their criterion is flat: the best four band-pass points lie within 0.0004 (0.957), the best four BMFLC points within 0.0014 (0.966–0.968).
- AR-LS uses the maximum order the contract window allows (64 taps per axis). The scheduled variant uses 11 f_est centres, 1,408 coefficients per output.

### c.9 Ablations

| Variant | Val | Test | Stress tremor | Realism 3–15 Hz | MAC |
|---|---|---|---|---|---|
| tcn_s with f_est (deployed) | 0.486 | 0.475 | 0.828 | 0.728 | 16,688 |
| tcn_s **without f_est** | 0.476 | 0.469 | 0.844 | 0.724 | 16,688 |
| tcn_m (larger) | 0.449 | 0.449 | 0.815 | 0.715 | 31,296 |

- **f_est adds nothing measurable.** Its source is also fragile: the balanced controller KF's f_est never leaves about 7.5 Hz, which is why the channel uses the assertive configuration.
- **tcn_m is better by 0.03 but does not fit.** It fails 1 ms in plain C (≈ 2.3 ms) and in the pessimistic CMSIS case (1.65 ms).
- **Choice of tcn_s** was made on validation for deployment margin, not on test.

### c.10 Figures (each stamped "SIMULATION", with a `.csv` data twin)

`results/ml/`:

- `fig_residual_by_band.png`
- `fig_operating_curves.png`
- `fig_distribution_shift.png`
- `fig_feature_course.png`
- `fig_quantization.png`
- `fig_example_trace.png`

---

## (d) Limitations and real-data plan

### Limitations (most decisive first)

1. **The network and the test data come from one generator.** The shift results (§c.4) show that most of the in-distribution advantage is generator-specific. We do not know where real tremor and real handwriting fall between "test" and "stress".
   - Candidate cues the TCN may exploit are strictly sinusoidal tremor with a fixed-phase harmonic, and lognormal stroke shapes with pen lifts and a rightward page advance.
2. **Kinematic housing.** Grip compliance, friction, stick-slip and contact transitions appear only in the 60-run realism set. There, the TCN's lead drops to 0.04–0.06 (3–15 Hz).
3. **No impaired writing.** The data has no micrographia, bradykinesia or pathological stroke shapes. The intended-motion spectrum is matched to a single literature writer (CON-25).
4. **The output-gain / FC calibration does not transfer across writing speed.** Every method's FC tripled or worse on fast writers. A per-user calibration of the operating point is needed (§a, personalisation).
5. **Idealised sensing.** Optical data is always valid, noise is white, and f_est comes from our 250 Hz port of the KF, not the firmware's 2 kHz estimator.
6. **Metric scope.** RR and FC are signal-level metrics of d(t + h). They are not ink metrics. Servo lag, stage limits and the actuator are excluded (the simulator covers those).
7. **Statistics.** Each network was trained with one seed. The bootstrap ignores gain-selection uncertainty. The realism set has 12 seeds with identical tremor specifications.
8. **Timing.** No nRF5340 measurement exists. The QEMU instruction count is not a cycle count, and the CMSIS-NN numbers are literature assumptions.

### What real data is needed and how to get labels without ground-truth tremor

In free human writing the "true tremor" is not observable: intended and involuntary motion share one pen. Labels therefore come from four complementary routes:

1. **Bench recordings with injected disturbance (supervised labels; EXP-B09).**
   - The pen is driven by a bench rig along replayed human intended trajectories (from EXP-H01 writers without tremor, or template tracing).
   - A *known* housing disturbance is injected from the tremor model and from recorded tremor segments.
   - Real paper, ink, friction and optical sensing are present, and d is known exactly.
   - This is the primary supervised training and test source. The "stress" axes of §c.4 become measured conditions.
2. **Instrumented passive-pen recordings (EXP-H01, ethics approval).**
   - Design: n ≈ 20 per group (ET, PD, older adults, controls), about 10 min of writing each, plus spirals, line and letter tracing on coded paper.
   - Streams: optical 1–2 kHz, IMU 2–4 kHz, axial force, and a µm-class coded-paper reference; the same schema as `data/schema/ml_sample.schema.json` with pseudonymous writer ids.
   - Labels come from:
     - **Template tasks:** d ≈ housing path − registered template. Template-tracking error remains as label noise; quantify it on controls.
     - **Self-supervised future-displacement prediction:** Δp(t → t + h) is fully observed, so a model can be pre-trained to predict the predictable part of the total motion. A band-limited target (3–15 Hz, zero-phase filtered offline, which is legitimate as a label for a causal predictor) is then fine-tuned. It encodes the "tremor = in-band motion" assumption; its bias is measured on controls, whose in-band motion is intent.
     - **Writer-level splits and a pre-registered test** (EXP-E01): matched distortion, per band, bootstrap over participants.
3. **Closed-loop evaluation in the simulator.**
   - The simulator needs a hook for an externally supplied d̂ at 250 Hz. It has none today (`sim/pensim/core.py` modes 2/3/4), so the simulator team must add one.
   - With it, ink error vs the powered-neutral pen can be measured together with servo lag, q_lim and the guard, on synthetic and on replayed EXP-H01 inputs.
4. **Pre-training and fine-tuning.** Synthetic plus simulator data pre-train; bench-labelled data fine-tune; held-out human writers test. The realism gap in §c.4 is the reason not to trust synthetic-only training.

**Pre-specified gate for REQ-ML-001.** This margin is proposed here, after seeing the synthetic results; it must be fixed before any real-data test. On held-out participants, the learned predictor must reduce the all-band residual ratio at matched distortion by ≥ 0.10 against the strongest conventional estimator, with the paired 95 % CI below 0 in each band where it is enabled, with no REQ-CTRL-005 violation on the feature course, and within timing.

On synthetic data this gate:

- is met in distribution (−0.28 against the scheduled AR-LS; −0.32 against the gated KF);
- fails on the tremor-model shift (−0.04, CI includes 0);
- fails on the simulator realism set (−0.04 to −0.06);
- would fail the corner-maximum part of REQ-CTRL-005 (125 µm, estimator output at the frozen gain).

---

## Proposed changes to the contract (`docs/icd.md` §5)

The contract is implemented as written. These are proposals only.

1. **Time stamp and horizon.** State whether h is measured from the sample's physical time or its arrival.
   - We assumed arrival, which gives an 8–9 ms physical horizon with a 2–3 ms optical latency.
   - Better: supply the latency-compensated, IMU-bridged fused position (about 1 ms old). That shortens the physical horizon to about 7 ms; the "hold" oracle shows prediction error grows about linearly with horizon × frequency.
2. **Drop f_est from the input, or specify its source.**
   - It adds nothing measurable (§c.9).
   - The balanced controller KF's f_est is constant (7.5–7.7 Hz): its oscillator never exceeds the 20 µm adaptation threshold.
   - The input couples the ML model to KF tuning.
3. **Redesign the guard.**
   - The "|d̂ − d̂_KF| > 150 µm for > 20 ms" rule rejects 18 % of ticks and erases the benefit (0.48 → 0.94), because the reference KF is nearly inert.
   - Replace it with a causal consistency check against the *realised* displacement: compare d̂(t − h) with the band-passed Δp observed h later, and reject when that residual exceeds its own recent quantile.
   - **Clip at q_lim instead of rejecting.**
   - **Apply the 50 mm/s limit as a slew limit, not a reject.** A 0.8 mm peak tremor at 12 Hz has a peak rate of 60 mm/s.
4. **Output.** Output an int16 in 0.1 µm (implemented; matches `dhat_x/dhat_y` of the research frame) plus a validity or confidence and a validity time, as REQ-ML-002 already requires.
5. **Allow the streaming form.**
   - Cost: 5.8 k MAC per step (−65 %) and 1.6 kB of state.
   - Semantics: an explicit reset on any gap, re-initialisation or optical invalidity, and exact equivalence to the window form (unit-tested) when f_est is constant or removed.
6. **State the kernel assumption in the budget.**
   - The plain-C reference is at the 1 ms limit.
   - Require CMSIS-NN (`arm_fully_connected_s8`), a DWT cycle measurement on the nRF5340 with the current and position ISRs active, and a worst-case (cache-miss) figure.
   - The tree layers need no dilated kernels, so ST Edge AI's dilation restriction (EML-26) does not apply.
7. **Evaluation protocol as part of the contract.** Matched false correction with gains frozen on validation; residual ratio per nominal-f0 band; participant-level bootstrap; the pre-specified REQ-ML-001 margin above.

---

## Conclusion: is a learned predictor justified now?

**Not for deployment and not as a claim.** The evidence is synthetic, and the TCN's large in-distribution advantage mostly disappears under plausible mismatches:

- tremor statistics outside the training ranges;
- the coupled simulator's housing dynamics, where at 9–11 Hz it matches the tuned Kalman filter within 0.03;
- calibration of the false-correction operating point, which fails on fast writers for every method.

On this evidence REQ-ML-001 is not met. The firmware should keep the conventional estimator with the frequency gate and the guided modes. ASSIST_ML stays off.

**Worth taking to real data, and cheap to carry.** It is the only method in this study that reduced 4–7 Hz residuals at matched false correction at all:

- in distribution, 0.63 against at best 0.97;
- in the simulator realism set, 0.92 and 0.84 at 4.5 and 6 Hz, against ≥ 0.98 and ≥ 0.91 for every other method.

It also fits the edge budget with margin via CMSIS-NN: 16.7 k MAC, 8.5 kB flash, 640 B RAM, about 0.3 ms and 6.5 µJ.

**Next step:** EXP-B09 bench labels and EXP-H01 recordings, then the pre-registered EXP-E01 bake-off. Guard (change 3) and f_est (change 2) should be fixed first.

---

## File map

| Path | Content |
|---|---|
| `ml/common.py` | Contract constants, paths, environment guards, provenance |
| `ml/synth.py` | Synthetic generator and sensor model |
| `ml/datasets.py` | Splits, cache, simulator realism set, leakage checks, schema examples |
| `ml/baselines.py`, `ml/tune_baselines.py` | Conventional estimators and their validation tuning |
| `ml/models.py`, `ml/train.py` | TCN tree (+ streaming reference) and training |
| `ml/metrics.py`, `ml/evaluate.py` | Metrics, gains, bootstrap, figures |
| `ml/quantize.py` | int8 PTQ and the integer reference |
| `ml/export_c.py`, `ml/export/` | C inference (`tcn_int8.[ch]`), generated `tcn_weights.h` and `test_vectors.h`, `test_host.c`, QEMU Cortex-M33 harness (`qemu/`) |
| `ml/budget.py` | Compute, memory, time and energy budget |
| `ml/model_card.md`, `data/dataset_card.md`, `data/schema/ml_sample.schema.json` | Cards and schema |
| `results/ml/` | `dataset_manifest.json`, `baselines_tuning.json`, `train_*.json`, `quantization.json`, `export_c.json`, `budget.json`, `eval_results.json`, `headline_table.md`, `budget_table.md`, figures + CSV twins, `model/` (float `.pt` + `.json`, int8 `.npz`, AR-LS coefficients; all < 100 kB) |
