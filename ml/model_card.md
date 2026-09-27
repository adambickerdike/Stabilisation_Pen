# Model card: `tcn_s_nofest` causal disturbance predictor (int8, exported)

> **Evidence status: SIMULATION / synthetic data.** Trained and evaluated only on synthetic handwriting and synthetic tremor, with a small realism check on the project's coupled simulator. It has never seen a human recording or a bench measurement. It is not validated for use with people, and nothing here implies clinical benefit.

This is the model in `ml/export/`. It implements the firmware–ML contract `docs/icd.md` §5 v1.1 and later, whose input has no f_est. Its sibling `tcn_s` has the same architecture plus the f_est input (contract v1.0). `tcn_s` carries the full comparison in `ml/README.md` §c.1–c.6, and this card quotes it where no `tcn_s_nofest` figure exists.

## Model details

| Item | Value |
|---|---|
| Name / version | `tcn_s_nofest`; int8 parameters SHA-256 `eebeafdd…a57d81f6` (low 32 bits `0xa57d81f6` are the event 0x0005 argument; `tcn_s` was `0x71feeb47`) |
| Owner | ML workstream, research pen Rev A (`ml/`) |
| Task | Causal prediction of the housing disturbance d̂ (x, y) at t + 6 ms from the last 256 ms of page-displacement increments (`docs/icd.md` §5) |
| Why this model is exported | ICD §5 v1.1 dropped f_est from the input: it adds nothing measurable. On test the ratio is 0.469 without it and 0.475 with it; on validation 0.476 and 0.486. The export follows the contract (`ml/README.md` §c.7, §c.9) |
| Architecture | Causal dilated TCN, kernel 2, dilations 1, 2, 4, 8, 16, 32 (receptive field 64 = W), ReLU; channels 8-12-16-24-32-32; head FC 32→24 (ReLU) → 2. Evaluated at the newest sample it is a 6-level stride-2 tree (`ml/models.py`). |
| Inputs | 64 × (Δp_x, Δp_y) in µm, oldest first, clipped at ±400 µm per sample and scaled by 1/100: **2 channels, no f_est**. |
| How the 2-channel network was obtained | It was trained in the 3-channel layout of `tcn_s` with the f_est channel held at zero (`ml.train --no-fest`). `models.drop_fest` then removes the two level-1 weight columns that only ever multiplied zero. The predictions are unchanged (0.0 µm difference on five test recordings; unit-tested). |
| Output | d̂ in µm (float model); int16 in 0.1 µm (int8 model, C); status bits NaN input / input clipped / output saturated. **No confidence output.** |
| Size | 5,926 parameters; 16,176 MAC per inference; ARM `-O2` object 1,096 B code + 7,276 B read-only data; RAM 576 B (128 B int8 window + 448 B scratch; 1,088 B with a float window) |
| Quantisation | int8 symmetric per-tensor weights; int8 activations (zero point −128 after ReLU); int32 bias; CMSIS-NN requantisation; calibration at the 99.99th percentile on 50 k training windows (chosen on validation) |
| Files | `results/ml/model/tcn_s_nofest.pt` + `.json` (float, 3-channel training layout), `tcn_s_nofest_int8.npz` (int8, 2 channels), `ml/export/tcn_model.h` + `tcn_weights.h` (C, `TCN_CIN 2`) |
| C API | `ml/export/tcn_int8.h`, unchanged from v1.0: `tcn_quantize_window(dp_um, f_est_hz, q)` and `tcn_predict(dp_um, f_est_hz, dhat_um, scratch)`. With `TCN_CIN == 2`, `f_est_hz` is ignored (not read, not checked); pass 0.0f |
| Training | 240 synthetic writers (4 h at 250 Hz); weighted MSE on d(t + h) with weight 4 on no-tremor ticks (false-correction penalty); AdamW 2e-3, one-cycle cosine; 14 epochs × 1.5 M windows; seed 7; 203 s on 2 CPU threads; epoch chosen on validation (epoch 14) |
| Licence | Same as the repository; no third-party data |

## Guard parameters (ICD §5 v1.2, rule 5)

| Parameter | Value | Status |
|---|---|---|
| Confidence output | none: the model outputs d̂ and status bits only | **uncalibrated**. An adapter that fills the ICD confidence byte reports the constant 255 (`TCN_CONFIDENCE_UNCALIBRATED` in `tcn_int8.h`) |
| c_min | 0 | ICD default for an uncalibrated model |
| c_full | 1 | ICD default for an uncalibrated model |

Rule (5) uses the normalised confidence ĉ = byte / 255: it scales the ML share of authority by min(1, ĉ / c_full) and rejects ĉ < c_min.

- With c_min = 0 and c_full = 1 the rule has no effect.
- The adapter reports the constant 255 (`TCN_CONFIDENCE_UNCALIBRATED`), as ICD §5 requires for an uncalibrated model, so the rule stays neutral. A byte of 0 would remove all ML authority.
- The rule can act only after a confidence output is added and calibrated against its reliability on held-out writers (EXP-E01). The new c_min and c_full then go in this card.

## Intended use

**Intended:**

- Bench and simulator research on the Rev A research pen, as the optional ASSIST_ML predictor behind the ML guard with Kalman fall-back.
- Firmware integration tests: C API, timing, guard behaviour.
- The reference model for the real-data bake-off (EXP-E01).

**Not intended:**

- Any use with a person.
- Any claim of tremor reduction or of clinical or functional benefit.
- Any product decision. REQ-ML-001 is not met; see the README conclusion.

## Evaluation (all synthetic; details in `ml/README.md` §c)

**Metric.** The residual ratio RR = RMS(d − g·d̂)/RMS(d) per nominal-f0 band, at a false correction (RMS output on no-tremor writing) matched to ≤ 25 µm on validation writers. The gain is frozen on validation. 95 % CIs from a 2000-sample writer bootstrap.

**Test writers (80, disjoint).** The 7–8 Hz column is the frequency-holdout set (30 writers whose f0 band was never in training). Sources: `results/ml/quantization.json` (`tcn_s_nofest` int8) and `results/ml/eval_results.json` (the other rows).

| | 4–6 Hz | 6–7 Hz | 7–8 Hz | 8–10 Hz | 10–12 Hz | All bands | FC |
|---|---|---|---|---|---|---|---|
| **tcn_s_nofest int8 (exported)** | 0.63 [0.55, 0.72] | 0.49 [0.37, 0.78] | 0.54 [0.46, 0.63] | 0.35 [0.29, 0.46] | 0.32 [0.28, 0.38] | 0.47 [0.41, 0.54] | 14.1 µm |
| tcn_s_nofest float | 0.63 | 0.49 | 0.54 | 0.35 | 0.31 | 0.47 [0.40, 0.54] | 14.1 µm |
| tcn_s int8 (with f_est, v1.0) | 0.63 [0.56, 0.72] | 0.50 [0.38, 0.79] | 0.55 [0.48, 0.64] | 0.36 [0.28, 0.46] | 0.32 [0.29, 0.40] | 0.48 [0.41, 0.55] | 16.6 µm |
| strongest baseline (AR-LS f_est-scheduled; gated KF at 7–8 Hz) | 0.97 | 0.81 | 0.83 | 0.62 | 0.53 | 0.76 | 26.5 µm |

Paired differences against the baselines were computed for `tcn_s` only (README §c.2, e.g. −0.28 [−0.33, −0.24] against the scheduled AR-LS). The exported model is within 0.02 of `tcn_s` on every set in the ablation (README §c.9): better on validation, test and the simulator 3–15 Hz set, 0.016 worse on the tremor stress set.

**Under distribution shift** (all bands, same frozen gains):

| Set | tcn_s_nofest int8 | tcn_s_nofest float | Strongest baseline |
|---|---|---|---|
| Stress: tremor outside training ranges | 0.84 [0.76, 0.91] | 0.84 | 0.87 (AR-LS scheduled) |
| Stress: faster writing | 0.69 [0.59, 0.81]; FC grows to 73 µm | 0.70; FC 80 µm | 0.98; FC 86–155 µm for the baselines |
| Simulator realism, full band | 0.96 | 0.96 | 0.96 |
| Simulator realism, 3–15 Hz | not computed | 0.72 | 0.77 |

For `tcn_s` the paired difference against the scheduled AR-LS on the tremor stress set is −0.04 [−0.10, +0.03], not significant.

**No-tremor feature course** (canonical `feature_course`, never in training):

- Overall false-correction RMS at the frozen gain is 16.4 µm (float 15.5 µm).
- Per-feature maxima were computed for `tcn_s` only. They reach 129 µm at corners and 196 µm on the spiral (int8), as brief spikes, and exceed the 100 µm corner/dot limit of REQ-CTRL-005 at corners. Expect the same order for this model; it has not been checked.

**Quantisation** (test writers):

- RMS float−int8 difference: 12.0 µm.
- All-band RR 0.469 → 0.472 at FC ≤ 25 µm, a paired difference of +0.003 [+0.002, +0.006].
- Activation saturation is at most 0.006 % per layer on the test writers. The output never saturates.

**C port.**

- Bit-exact with the Python integer reference on 20,000 test windows (host gcc `-O2 -Werror`, clang UBSan) and on an emulated Cortex-M33 (QEMU, embedded vectors).
- 115 k executed instructions per inference in plain C, i.e. 0.90–1.44 ms at 128 MHz for CPI 1.0–1.6. This is a QEMU instruction count, not a cycle count.
- An estimated 0.27 ms with CMSIS-NN at 0.5 MAC per cycle, and 0.86 ms at 0.15.

## Factors that change performance (known or expected)

- **Tremor waveform statistics.** Frequency and amplitude wander, harmonic content and phase, broadband content (stress set).
- **Writing speed and the in-band content of intended motion.** False-correction calibration fails on fast writers.
- **Housing dynamics.** Grip compliance, friction, stick-slip and contact transitions (simulator realism set).
- **Sensor latency, noise and scale.** Trained for 2–3 ms, 2.5–3.5 µm and ±1 %. Drop-outs and paper texture are not modelled.
- **Page-frame orientation.** Training writing always advances along +x.
- **Population.** No impaired writing (micrographia, bradykinesia) in training. No real tremor.

## Ethical considerations and risks

- **False correction** moves the ink away from what the writer intended. Confident-but-wrong assistance is the worst case in the guidance literature (HAP-23). The frozen output gain does not keep false correction bounded when writing speed changes.
- **No calibrated confidence.** The model cannot signal when it is unsure. Until EXP-E01 calibrates a confidence, only guard rules 1–4 protect against wrong predictions.
- **The v1.0 guard** rejected 18 % of ticks for `tcn_s` and cancelled its benefit, because its Kalman reference is nearly inert at 250 Hz (README §c.6). ICD v1.1 replaced it with rules 1–4. Those rules have not been evaluated on this model in `ml/`; that is required before any closed-loop use.
- **Future training data** would be handwriting of identifiable people, which is sensitive. It needs explicit consent for model training, pseudonymous ids, data minimisation, and no use of non-commercial datasets for shipped models.
- **Claims** must stay separated by user group. Active correction addresses a subset of action tremor, not PD micrographia (COR-10).

## Caveats and recommendations

- Keep ASSIST_ML disabled. Use the conventional estimator with the frequency gate and guided modes.
- Re-train and re-evaluate on bench data with injected disturbance (EXP-B09) and EXP-H01 recordings. Apply the pre-specified REQ-ML-001 margin from the README (§d) before looking at real test data. Add and calibrate a confidence output in the same study (EXP-E01), and set c_min and c_full here from it.
- Deploy with CMSIS-NN `arm_fully_connected_s8`; each tree level is one call with the parameters in `tcn_weights.h`. Measure DWT cycles on the nRF5340 with the control ISRs running.
- f_est is not an input. Any caller of the unchanged API passes 0.0f for `f_est_hz`. The 3-channel `tcn_s` export (contract v1.0) remains reproducible with `python3 -m ml.export_c --model tcn_s` (written to `ml/runs/export_tcn_s/`).
