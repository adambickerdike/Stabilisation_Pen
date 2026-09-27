# Model card: `tcn_s` causal disturbance predictor (int8)

> **Evidence status: SIMULATION / synthetic data.** Trained and evaluated only on synthetic handwriting and synthetic tremor, with a small realism check on the project's coupled simulator. It has never seen a human recording or a bench measurement. It is not validated for use with people, and nothing here implies clinical benefit.

## Model details

| Item | Value |
|---|---|
| Name / version | `tcn_s`; int8 parameters SHA-256 `d2d2c237…71feeb47` (low 32 bits `0x71feeb47` are the event 0x0005 argument) |
| Owner | ML workstream, research pen Rev A (`ml/`) |
| Task | Causal prediction of the housing disturbance d̂ (x, y) at t + 6 ms from the last 256 ms of page-displacement increments (`docs/icd.md` §5) |
| Architecture | Causal dilated TCN, kernel 2, dilations 1, 2, 4, 8, 16, 32 (receptive field 64 = W), ReLU; channels 8-12-16-24-32-32; head FC 32→24 (ReLU) → 2. Evaluated at the newest sample it is a 6-level stride-2 tree (`ml/models.py`). |
| Inputs | 64 × (Δp_x, Δp_y) in µm, clipped at ±400 µm per sample; f_est in Hz as a third, broadcast channel ((f − 8) × 50 µm-equivalent). All scaled by 1/100. |
| Output | d̂ in µm (float model); int16 in 0.1 µm (int8 model, C) |
| Size | 5,942 parameters; 16,688 MAC per inference; ARM `-O2` object 1,240 B code + 7,292 B rodata; RAM 640 B (int8 window + scratch) |
| Quantisation | int8 symmetric per-tensor weights; int8 activations (zero point −128 after ReLU); int32 bias; CMSIS-NN requantisation; calibration at the 99.99th percentile on 50 k training windows |
| Files | `results/ml/model/tcn_s.pt` + `.json` (float), `tcn_s_int8.npz` (int8), `ml/export/tcn_weights.h` (C) |
| Training | 240 synthetic writers (4 h at 250 Hz); weighted MSE on d(t + h) with weight 4 on no-tremor ticks (false-correction penalty); AdamW 2e-3, one-cycle cosine; 14 epochs × 1.5 M windows; seed 7; 328 s on 2 CPU threads; epoch chosen on validation |
| Licence | Same as the repository; no third-party data |

## Intended use

**Intended:**

- Bench and simulator research on the Rev A research pen, as the optional ASSIST_ML predictor behind the ML guard with Kalman fall-back.
- Firmware integration tests: C API, timing, guard behaviour.
- The reference model for the real-data bake-off (EXP-E01).

**Not intended:**

- Any use with a person.
- Any claim of tremor reduction or of clinical or functional benefit.
- Any product decision. REQ-ML-001 is not met; see the README conclusion.

## Evaluation (all synthetic; details and CIs in `ml/README.md` §c and `results/ml/eval_results.json`)

**Metric.** The residual ratio RR = RMS(d − g·d̂)/RMS(d) per nominal-f0 band, at a false correction (RMS output on no-tremor writing) matched to ≤ 25 µm on validation writers. The gain is frozen on validation. 95 % CIs from a 2000-sample writer bootstrap.

**Test writers (80, disjoint).** The 7–8 Hz column is the frequency-holdout set (30 writers whose f0 band was never in training).

| | 4–6 Hz | 6–7 Hz | 7–8 Hz | 8–10 Hz | 10–12 Hz | All bands | FC |
|---|---|---|---|---|---|---|---|
| tcn_s int8 | 0.63 [0.56, 0.72] | 0.50 [0.38, 0.79] | 0.55 [0.48, 0.64] | 0.36 [0.28, 0.46] | 0.32 [0.29, 0.40] | 0.48 [0.41, 0.55] | 16.6 µm |
| strongest baseline (AR-LS f_est-scheduled; gated KF at 7–8 Hz) | 0.97 | 0.81 | 0.83 | 0.62 | 0.53 | 0.76 | 26.5 µm |

**Under distribution shift** (all bands, same frozen gains):

| Set | tcn_s int8 | Strongest baseline | Paired difference (float TCN) |
|---|---|---|---|
| Stress: tremor outside training ranges | 0.83 | 0.87 | −0.04 [−0.10, +0.03] |
| Stress: faster writing | 0.70 | 0.98 | FC grows to 78 µm (baselines 86–155 µm) |
| Simulator realism, full band | 0.96 | 0.96 | none |
| Simulator realism, 3–15 Hz | 0.73 | 0.77 | −0.04 |

**No-tremor feature course** (canonical `feature_course`, never in training):

- Overall false-correction RMS is 17.6 µm (float 14.5 µm).
- Maxima reach 129 µm at corners and 196 µm on the spiral, as brief spikes.
- The 100 µm corner/dot limit of REQ-CTRL-005 is exceeded at corners.

**Quantisation.**

- RMS float−int8 difference: 11.9 µm.
- All-band RR 0.475 → 0.476 at FC ≤ 25 µm; 0.556 → 0.605 at FC ≤ 10 µm.

**C port.**

- Bit-exact with the Python integer reference on 20,000 test windows (host gcc, clang UBSan) and on an emulated Cortex-M33 (QEMU).
- 118 k executed instructions per inference in plain C, i.e. 0.92–1.48 ms at 128 MHz for CPI 1.0–1.6.
- An estimated 0.28 ms with CMSIS-NN at 0.5 MAC per cycle.

## Factors that change performance (known or expected)

- **Tremor waveform statistics.** Frequency and amplitude wander, harmonic content and phase, broadband content (stress set).
- **Writing speed and the in-band content of intended motion.** False-correction calibration fails on fast writers.
- **Housing dynamics.** Grip compliance, friction, stick-slip and contact transitions (simulator realism set).
- **Sensor latency, noise and scale.** Trained for 2–3 ms, 2.5–3.5 µm and ±1 %. Drop-outs and paper texture are not modelled.
- **Page-frame orientation.** Training writing always advances along +x.
- **Population.** No impaired writing (micrographia, bradykinesia) in training. No real tremor.

## Ethical considerations and risks

- **False correction** moves the ink away from what the writer intended. Confident-but-wrong assistance is the worst case in the guidance literature (HAP-23). The frozen output gain does not keep false correction bounded when writing speed changes.
- **The guard, as specified,** rejects 18 % of ticks for this model, because its Kalman reference is nearly inert at 250 Hz. A redesigned guard is required before any closed-loop use (README, proposed change 3).
- **Future training data** would be handwriting of identifiable people, which is sensitive. It needs explicit consent for model training, pseudonymous ids, data minimisation, and no use of non-commercial datasets for shipped models.
- **Claims** must stay separated by user group. Active correction addresses a subset of action tremor, not PD micrographia (COR-10).

## Caveats and recommendations

- Keep ASSIST_ML disabled. Use the conventional estimator with the frequency gate and guided modes.
- Re-train and re-evaluate on bench data with injected disturbance (EXP-B09) and EXP-H01 recordings. Apply the pre-specified REQ-ML-001 margin from the README (§d) before looking at real test data.
- Deploy with CMSIS-NN `arm_fully_connected_s8`; each tree level is one call with the parameters in `tcn_weights.h`. Measure DWT cycles on the nRF5340 with the control ISRs running.
- If f_est is kept in the contract, supply it from a tracking configuration. The ablation shows the model does not need it: 0.469 without vs 0.475 with.
