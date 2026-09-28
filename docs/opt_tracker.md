# Tremor tracker: adjoint (backpropagation) tuning, learned trackers and per-writer tuning (pencil model P1)

**Status: proposed design, tuned and checked in simulation only.** Nothing here was measured on a pen or a person. Evidence labels:
- **SIM**: pencil model P1 with the `fusion/` sensor models, on synthetic handwriting and synthetic tremor;
- **CALC**: operation counts and the MCU cycle model;
- **MFR / LITERATURE**: a manufacturer or published statement, with its ledger id;
- **ASSUMPTION**: a model input or a choice nobody has measured.

All numbers come from `results/opt/tracker.json` (provenance: git revision, source digest of `sim/pencil`, `fusion` and `config`, seeds, library versions). Proposed ledger rows: `results/opt/tracker_evidence_rows.csv` (ACT-46 to ACT-50, EML-33 to EML-35). Seed use:
- training, validation and every choice (including which tracker to ship) used tuning seeds 5000–5007, aiguide writers 100–105 and fusion's training and validation specs;
- test seeds 200–203 and aiguide test writers 0–5 were used once, for the final tables.

## 1. Short answer

**Where the simulations are.**
- Code: `opt/tracker/`. One command reruns everything: `python3 -m opt.tracker.run_study` (about 3–4 h on 2 cores once the data caches exist; §11).
- Results: `results/opt/tracker.json`; figures `results/opt/fig_tr_*.png` (each with a CSV twin); the 3-D replay `results/opt/viz_tracker.json` (seed 200, 10 Hz, 0.3 mm; `viewer/` format).

**What was done.**
- The pen's tremor tracker (the acceleration-domain Kalman filter, AKF, of DEC-025) was rewritten so that it can be differentiated exactly. The rewrite gives the same output as the existing filter to 1e-13 (SIM).
- Its exact gradient (the discrete adjoint, i.e. backpropagation through time) was then used three ways:
  - to tune all 23 settings;
  - to train small learned trackers with the right target;
  - to fit a set to each writer from the 20 s calibration.

**Ship: the same AKF with the robust settings re-optimised by the adjoint** (`rep_robust`; parameters in `results/opt/tracker_models/akf_ship.json`).
- Why: of all candidates, it gives the most tremor-band benefit while keeping sharp writers' tremor-free writing within 30 µm and not moving the ink further from the intended letters.
- The choice was made by that rule, fixed before the test data were run, on tuning data only (§3.5). The test data agree with it.
- It is the random search's own robust objective (fusion.tune), minimised by gradient instead of random search: same filter, same objective, same data, new numbers.
- One of the new numbers sits at a bound I set: the output gain went to 2.0, the upper end of its allowed range (ASSUMPTION), against 1.14 before.
  - It does not over-correct in simulation. The output stays at 13–67 % of the tremor-band disturbance's RMS (tuning seeds 5000–5003, 8–12 Hz, 0.3 mm, open loop, SIM), because the gates, the cap and the authority scale the estimate down.
  - How safe a gain of 2 is on real writing is for EXP-E01 and EXP-B09.
- It needs no new part and no new firmware code. It runs on the board IMU (LSM6DSV16X class, OPT-37) and the MCU (nRF54L15 class, AMF-44) already chosen. The change is a parameter set; the filter costs 6.2 % of the MCU (CALC, §8).

**Test results of the shipped set (SIM; P1 test grid: seeds 200–203, 4–12 Hz × 0.1/0.3/0.5 mm; aiguide test writers 0–5)**, against the previous default (the robust random-search set):

| Measure | Shipped set | Previous default | No correction |
|---|---|---|---|
| Tremor-band (3–15 Hz) ink error, ratio to no correction | **0.863** | 0.910 | 1 |
| Same, 8–12 Hz at 0.3 and 0.5 mm | **0.673** | 0.788 | 1 |
| Distortion of tremor-free writing, grid writers (µm RMS) | 7 | 5 | – |
| Distortion of tremor-free writing, sharp glyph writers (µm RMS) | **18** | 21 | – |
| Path to the intended letters, aiguide writers, writing only (µm) | 193 | 193 | 196 |
| Path to the intended letters, grid (µm) | **242** | 247 | 258 |

- The gain is modest: 5 % in the tremor band overall, 15 % at 8–12 Hz, and no more false correction on sharp writers.
- Tremor at 4–6 Hz or at 0.1 mm is barely helped: the shipped set gives 0.97–1.03 there (1.025 at 4 Hz and 0.1 mm, slightly worse than no correction). The band-target GRU gives 0.91–1.02.

**What the adjoint gained, and where it did not.**
- **Same objective, better optimum.** On both of the random search's objectives, gradient descent from its winner found lower values: 0.9910 → 0.9885 (robust), 0.9587 → 0.9572 (grid). The objective values come from fusion.tune's own numba code.
- **The trade-off is now mapped (§5.2).** Two chains of adjoint tuning, over five weights of the false-correction penalty each, trace the tremor-band benefit against distortion. They show no AKF setting that has both:
  - the tremor-band benefit of the set tuned on the grid's smooth writing (0.775);
  - a sharp writer's tremor-free ink moved by ≤ 30 µm.
  The best compromises found lie at 0.86–0.89 and 17–24 µm. The objective and the training writers decide where a set lands; the optimiser only gets it there.
- **Discontinuities.** The frequency tracker's discrete decisions make the objective (about 1.56) jump by up to 0.006 between settings 0.01 % apart (SIM, §4). Between the jumps the adjoint is exact. Iterates had to be selected on validation data.

**Learned trackers (not shipped).**
- **GRU trained on the tremor band.** It fixes the previous GRU's failure: that one made the path to the intended letters worse than no correction (282 against 258 µm), because it tracked P1's slow friction drift. The new one gives 241 µm, with a tremor-band ratio of 0.796.
  - It moves sharp writers' tremor-free ink by 57 µm.
  - It does not improve the aiguide writers' path (195 against 196 µm).
  - It would fail the REQ-ML-001 gate even in simulation. The gate asks for ≥ 0.10 lower residual than the best conventional estimator at matched false correction (≤ 25 µm). The GRU is 0.067 better than the shipped AKF, at 57 µm.
- **AKF + learned authority gate.** The gate halved its base filter's false correction on the validation writers (62 → 30 µm, open loop). On the aiguide test writers it still moves tremor-free ink by 53 µm, with a band ratio of 0.873.

**Per-writer tuning by gradient (§7).**
- Fitted to the 20 s calibration alone, the adjoint gains a lot in the tremor band: 0.638, against 0.755 for the 12-candidate choice (test seeds, 0.3 mm). But it nearly triples distortion (55 against 20 µm): the calibration task never shows the filter tremor-free writing.
- With a false-correction guard (other writers' tremor-free writing; weight chosen on tuning seeds), distortion returns to 19 µm and most of the gain goes: 0.738 against 0.755. Keep the 12-candidate choice (DEC-025). The guarded refinement is an option worth about 2 % in simulation.

**What must happen next.** Every ranking above is on synthetic writers and tremor. EXP-E01 on recorded writing decides which set ships (§10). `opt/tracker/realdata.py` is the executable path for tuning and scoring on such recordings.

## 2. Test results, all trackers (SIM)

P1 test grid: seeds 200–203 × 4/6/8/10/12 Hz × 0.1/0.3/0.5 mm, closed loop, 60 conditions. aiguide: test writers 0–5 × 4/6/8/10 Hz, 0.3 mm, 24 scenarios. Ratios are ink-error RMS against the same pen with the stage held at centre.

| Tracker | Test-grid 3-15 Hz ratio | Test-grid all-band ratio | Distortion, grid writing (µm) | Distortion, glyph writing (µm) | Path to intended letters, grid (µm) | Time-aligned intent error, grid (µm) | aiguide path RMS, writing only (µm) | aiguide recognition |
|---|---|---|---|---|---|---|---|---|
| No correction | 1.000 | 1.000 | – | – | 258 | 582 | 196 | 0.938 |
| Oracle: whole disturbance (limit, not an estimator) | 0.445 | 0.355 | – | – | 283 | 590 | 164 | 0.947 |
| Tremor-band oracle (3-15 Hz, not causal) | 0.259 | 0.765 | – | – | 225 | 539 | – | – |
| Frozen Kalman (core) | 0.847 | 0.999 | 34 | – | 240 | 554 | – | – |
| AKF, random search on the grid's writing | 0.775 | 0.930 | 21 | 146 | 235 | 545 | 196 | 0.942 |
| AKF, random search, robust | 0.910 | 0.969 | 5 | 21 | 247 | 567 | 193 | 0.934 |
| GRU, whole-disturbance target (previous) | 0.808 | 0.688 | 7 | 25 | 282 | 608 | 207 | 0.934 |
| AKF, adjoint, chain A, λ_fc 0.01 | 0.826 | 0.941 | 17 | 101 | 242 | 555 | 194 | 0.939 |
| AKF, adjoint, chain A, λ_fc 0.03 | 0.840 | 0.946 | 22 | 92 | 244 | 556 | 194 | 0.939 |
| AKF, adjoint, chain A, λ_fc 0.1 | 0.865 | 0.953 | 20 | 78 | 246 | 561 | 194 | 0.942 |
| AKF, adjoint, chain A, λ_fc 0.3 | 0.885 | 0.960 | 18 | 66 | 248 | 564 | 194 | 0.942 |
| AKF, adjoint, chain A, λ_fc 1 | 0.913 | 0.969 | 11 | 53 | 250 | 568 | 194 | 0.939 |
| AKF, adjoint, chain B, λ_fc 0.01 | 0.907 | 0.966 | 1 | 26 | 245 | 563 | 193 | 0.938 |
| AKF, adjoint, chain B, λ_fc 0.01 (validation-best iterate) | 0.853 | 0.949 | 4 | 33 | 240 | 556 | 192 | 0.934 |
| AKF, adjoint, chain B, λ_fc 0.03 | 0.880 | 0.957 | 2 | 24 | 243 | 559 | 193 | 0.938 |
| AKF, adjoint, chain B, λ_fc 0.1 | 0.888 | 0.961 | 3 | 17 | 243 | 561 | 193 | 0.936 |
| AKF, adjoint, chain B, λ_fc 0.3 | 0.913 | 0.970 | 3 | 7 | 246 | 565 | 194 | 0.934 |
| AKF, adjoint, chain B, λ_fc 1 | 0.918 | 0.971 | 1 | 6 | 247 | 565 | 194 | 0.933 |
| AKF, random search's grid objective re-optimised by the adjoint | 0.766 | 0.930 | 25 | 154 | 234 | 545 | 197 | 0.936 |
| AKF, random search's robust objective re-optimised by the adjoint (ship) | 0.863 | 0.953 | 7 | 18 | 242 | 559 | 193 | 0.938 |
| GRU, tremor-band target (this study) | 0.796 | 0.916 | 14 | 57 | 241 | 558 | 195 | 0.934 |
| AKF + learned authority gate (this study) | 0.873 | 0.947 | 5 | 53 | 246 | 560 | 196 | 0.929 |

How to read it:
- **3–15 Hz ratio**: the tracker's target. The tremor-band oracle (perfect, non-causal knowledge of the 3–15 Hz disturbance) bounds it at 0.26.
- **All-band ratio**: includes P1's slow friction drift below 3 Hz. Most of the tremor-induced disturbance in P1 is there (docs/sensor_fusion_ai.md §3.2); no tremor tracker should chase it.
- **Distortion**: closed-loop change of tremor-free ink by the tracker, in µm RMS. Grid: the test seeds' sigma-lognormal writing. Glyph: the aiguide test writers' sharp glyph writing.
- **Path to intended letters**: distance of the ink path to the intended letters (fusion.harness). The pencil's own in-stroke offset dominates it. In P1 the tremor also keeps the skid and nib sliding (friction dither, docs/sensor_fusion_ai.md §3.2), so the tremor-free pen scores 301 µm, more than the pen with tremor (258). Compare trackers with each other, not with zero.
- **Time-aligned intent error** (grid) and **aiguide recognition** are reported as asked. No tracker changes recognition by more than ±0.01, from 0.938 without correction (tremor-free 0.973).
- The shipped set puts the stage at its travel limit 2.6 % of the time (robust set 0.1 %, grid-tuned set 3.8 %). Drive power is 135 mW (robust 132, none 129; class-B rail, SIM).

Figures:
- `results/opt/fig_tr_ratio_vs_frequency.png`: tremor-band ratio against frequency per amplitude, shipped set against previous sets, learned trackers and the band oracle.
- `results/opt/fig_tr_pareto.png`: band ratio against distortion (grid and glyph) for the λ_fc sweep and every other tracker.
- `results/opt/fig_tr_training.png`: validation curves of the adjoint chains and of the learned models.
- `results/opt/fig_tr_personal.png`: per-writer tuning, 4–12 Hz at 0.3 mm.
- `results/opt/viz_tracker.json`: 3-D replay of test seed 200 at 10 Hz, 0.3 mm (`viewer/` schema). Tremor-band ratios in this one run: shipped set 0.71, robust set 0.82, grid-tuned set 0.50, band limit 0.17 (SIM).

## 3. What was done

### 3.1 The tracker written so that it can be differentiated (task 1)

- **PyTorch AKF** (`opt/tracker/torch_akf.py`). The acceleration-domain Kalman filter of `fusion/estimators.py`, with the same equations:
  - 8 states per axis: intent position, velocity and acceleration with white jerk; the tremor oscillator; its second harmonic; accelerometer bias. One covariance is shared by both axes.
  - Accelerometer updates at 1.92 kHz (two FIFO samples averaged), stamped at acquisition time minus the 1.04 ms filter delay.
  - Page-sensor updates at the page sample's acquisition time. The filter rolls back to the snapshot of the last accelerometer sample acquired no later, then predicts and updates (or re-anchors the position after a pen lift). It then re-applies the later accelerometer samples, each with the frequency it was first processed with.
  - Frequency tracking from the phase rate of the larger oscillator, clamped to [f_min, f_max].
  - Output stage: frequency gate, amplitude gate, slow-motion amplitude cap, authority smoothing, gain, and a 2nd-order output low-pass whose delay is predicted ahead.
- **Batched over recordings with their own sample clocks.** The event bookkeeping depends only on sample times: which sample each 0.5 ms tick processes, the rollback target, the re-applied samples and every prediction interval.
  - It is replayed once per recording from the numba filter's own logic (`opt/tracker/schedule.py`).
  - The tensors then only do the arithmetic, with masks where recordings differ.
- **Gates.** The deployed filter uses the exact ramps.
  - For training, the ramp keeps its exact value, and its gradient leaks by ε outside [0, 1] (straight-through; ε = 0.1, decayed linearly to 0 over the first 70 % of the iterations). A closed gate therefore still learns whether opening it would help.
  - Softplus-smoothed gates were tried first. They optimise a leakier filter than the one that ships, and validation with the exact gates got worse (build log kept).
- **The adjoint.** Backpropagation through time of this recursion is its discrete adjoint.
  - PyTorch autograd on the tensor filter works, but costs about 5 ms per tick for forward and backward (three times more with checkpointing to bound memory).
  - The sequential core (updates, rollback, frequency tracking) was therefore also written as a hand-derived reverse sweep in numba (`opt/tracker/adjoint.py`), called from PyTorch as an autograd function.
  - The output stage (prediction, cap, gates, low-pass) stays in PyTorch. It has no feedback into the filter, so it runs over all ticks at once.
  - Rollbacks make the state history a graph. A snapshot read by a later rollback receives that rollback's input adjoint. Each snapshot version's adjoint is consumed when the reverse sweep reaches the step that created it.
  - Cost (SIM tooling): 8 recordings × 1600 ticks, forward and backward, 0.22 s against 8.8 s for autograd. 64 recordings of 5 s take about 6 s on 2 threads.

### 3.2 Adjoint tuning (task 2)

**Parameters (23, log-transformed where positive):**
- noise: q_j, q_t, q_h, q_b, r_a, r_p;
- oscillator and frequency tracking: decay τ, initial frequency, smoothing τ_w, f_min, f_max;
- gates: frequency-gate centre and width, amplitude-gate centre and width, amplitude smoothing;
- output: prediction horizon, authority smoothing, gain, output low-pass, cap k, cap slow-motion speed, cap reference time.

The second harmonic (on/off) is structure and was fixed per chain. The cross-track option stayed off.

**Data (SIM).** 160 of fusion's 400 domain-randomised training pairs: P1 runs with and without tremor of the same writing.
- 96 sigma-lognormal writers and 64 aiguide glyph writers (40 % glyph).
- Randomised pen, hand, writing and tremor: 3–14 Hz, 0.05–0.6 mm, harmonic, drift, ellipticity.
- The pen-rotation parameters were redrawn per pair: ρ_t −0.5 to 1.5, ρ_w 0 to 1, phase ±90° (ASSUMPTION: ranges).
- Sensors: 1 kHz / 2 ms page sensor; LSM6DSV16X-class IMU with gyroscope compensation (fusion's models).

**Objective** (`opt/tracker/losses.py`):

J = RR_band + λ_fc · FC / 100 µm + μ · HF

- **RR_band**: the 3–15 Hz part of (true disturbance − clipped estimate), relative to the 3–15 Hz part of the true disturbance, at contact ticks after 0.5 s.
  - Energy is summed over the recordings, so large tremors, where the benefit is, dominate.
  - The mean of per-recording ratios was tried first. The many small tremors of the randomised data, where no tracker can help, turned the benefit term into a false-correction term, and the optimum was conservative for every λ_fc (build log kept).
- **FC**: RMS estimate on the tremor-free runs, glyph writers weighted 3 : 1 (ASSUMPTION).
- **HF**: RMS of the estimate above 150 Hz (causal 4th-order high-pass, as fusion.tune), with μ = 0.02 per µm, about fusion.tune's weight.

**Optimiser.**
- Full-batch Adam (gradient accumulated over 4 mini-batches), learning rate 0.03 with cosine decay, gradient norm clipped. Parameters are projected onto physical ranges after each step.
- L-BFGS was not used. Its line search assumes a smooth objective, and this one jumps (§4).
- Validation every 5 iterations with the exact gates, on three sets:
  - fusion's validation pairs;
  - tuning seeds 5004–5007 (harness scenarios);
  - aiguide tuning writers 100–105.

**Pareto sweep.** Two chains over λ_fc = 0.01, 0.03, 0.1, 0.3 and 1:
- chain A starts from the grid-tuned random-search set (second harmonic on);
- chain B starts from the robust set (second harmonic off).

Each λ starts from the previous λ's validation-best iterate. The point reported for each λ is that run's last iterate (40, 25, 15, 15 and 15 iterations). Each chain's overall validation-best iterate is kept as an extra candidate.

**The random search's own objectives, re-optimised** (`opt/tracker/replicate.py`).
- fusion.tune's two proxies (grid and robust) were written in PyTorch on exactly its streams. The objective value of the numba filter is reproduced to 1e-15.
- They were minimised by the adjoint from the random-search winners, for 30 iterations; the lowest objective along the path is kept, as fusion.tune does.
- Same objective, same data. Differences come from the optimiser and from its range: the adjoint could leave the random search's sampling box (the gain went to 2, where the random search drew 0.4–1.2).

### 3.3 Learned trackers with the right target (task 3)

- **GRU, tremor-band target** (`opt/tracker/learned.py`, `learned_train.py`).
  - Inputs are the old GRU's, at 1 kHz: IMU nib acceleration, page increments, new-sample flag, page validity, axial contact.
  - GRU(48): 8,304 MAC per step (CALC; the task allows about 10 k).
  - The output is held over the two stage ticks and passed through the same 60 Hz output low-pass. The model is trained through that low-pass, at the tick level.
  - Target: the true 3–15 Hz disturbance (zero phase, the band oracle's signal). A causal model can only predict it; the part it can predict is the causally realisable tremor.
  - Loss: error against that target at all frequencies (so slow friction drift in the output is penalised, where the old GRU was rewarded for it); plus λ_fc × false correction with λ_fc = 0.1 (glyph ×3); plus the jitter term above 150 Hz.
  - Data: all 400 training pairs (30 % glyph), randomised sensor rotation; 14 epochs, 13 min; the last epoch was also the best on validation.
- **Hybrid: AKF + learned authority gate.**
  - A small GRU(24) sees the AKF's own quantities (estimate before the low-pass, authority, tracked frequency, amplitude, intent velocity) and the 7 sensor inputs: 3,000 MAC per step.
  - It outputs a gate between 0 and 1 that multiplies the AKF's estimate before its low-pass. The gate can only remove correction, never add content the AKF did not estimate.
  - Base filter: the most aggressive adjoint-tuned AKF (chain A, λ_fc 0.01), so that there is false correction to remove. Loss: the AKF objective with λ_fc = 0.1. Trained on the AKF's 160 pairs, 14 epochs, 3.5 min; epoch 8 kept by validation (mean objective over the validation pairs and tuning seeds 5004–5007).

### 3.4 Adjoint personalisation (task 4)

- **Inputs are those of `fusion.personal`, never the test recording or the simulator's truth:**
  - the 20 s calibration task (spiral, circle, lines), in which the writer's tremor is an independent realisation (seed + 40000);
  - the pen's streams of it;
  - the phone's label: page path matched to the known shapes, cross-track, 3–15 Hz per stroke.
- `fusion.personal` picks one of 12 variants by the fit of the estimate to the label. Here the same fit is minimised by gradient over 12 parameters, starting from the 12-candidate choice.
- A quadratic prior pulls back to the start. Its weight (0.003) was chosen on tuning seeds 5000–5003 from 0.003, 0.02 and 0.1.
- The fit uses an exact PyTorch copy of fusion.personal's band_at_page: interpolation, projection, and per-stroke sosfiltfilt rebuilt from scipy's own impulse and initial-condition responses. It is unit-tested equal to scipy, and the full fit equals fusion.personal's score to 3e-15.
- **Second variant, with a false-correction term.** It adds λ_fc,p × the RMS estimate of each writer's set on 6 tremor-free recordings of other writers (fusion training specs: 3 sigma-lognormal, 3 glyph).
  - λ_fc,p was chosen on tuning seeds by a rule fixed before running: the lowest tuning band residual among the weights (0.3, 1, 3) whose open-loop false correction on the tuning seeds' own tremor-free writing is no higher than the 12-candidate choice's.

### 3.5 Selection rule (fixed before the test run) and seed plan

- **Candidates:** the 10 sweep points, chain B's validation-best iterate, the two re-optimised random-search objectives, the band-target GRU and the hybrid. Chain A's validation-best iterate is its λ = 0.01 point.
- **Closed loop on tuning data only:** P1 tuning seeds 5000–5003 × 15 conditions, and the aiguide tuning writers 100–105 (fusion.tune's scenarios).
- **Rule:** the lowest tuning-grid tremor-band ratio among the candidates that meet all three of:
  - distortion ≤ 14 µm on the tuning seeds' tremor-free writing (the frozen filter's level used by fusion.tune);
  - distortion ≤ 30 µm on the tuning glyph writers' tremor-free writing (fusion.tune's FC_AI_MAX);
  - aiguide writing-only path to the intended letters no worse than no correction.
- **Eligible:** chain B at λ_fc 0.03, 0.1, 0.3 and 1, and the re-optimised robust objective. **Chosen: `rep_robust`** (tuning band ratio 0.880; distortion 6.1 µm on grid writing, 20.5 µm on glyph writing; aiguide path 184.1 µm against 185.1 µm without correction).
- **Caveat.** The re-optimised objectives were fitted on tuning seeds 5000–5007 and writers 100–105, which include the selection data. The random-search sets they start from were fitted on the same data. The choice among them is therefore partly in-sample. The test data (not used in any choice) rank them the same way (§2).

| Data | Seeds / writers | Used for |
|---|---|---|
| fusion training specs | `fusion.learned._spec(i, 'train')`, i < 400; sensor streams 30 000 000 + 10 i | AKF training (160 pairs), GRU training (400), false-correction writing of the personal FC variant (6 tremor-free runs) |
| fusion validation specs | `_spec(j, 'val')`, j < 24; streams 35 000 000 + 10 j | validation, iterate selection, gradient checks |
| tuning seeds, open loop | 5004–5007 | validation |
| tuning seeds, closed loop | 5000–5003; aiguide writers 100–105 | selection rule; personal prior weight and λ_fc,p |
| random-search data | 5000–5007 (sensor tags 7/8); writers 100–105 | the two re-optimised objectives (as fusion.tune) |
| calibrations | seed + 40000 (fusion.personal) | personal fits (tuning seeds for choices, test seeds for the test) |
| **test** | **P1 seeds 200–203 (tremor streams 1200–1203); aiguide writers 0–5** | **final tables only** |

`opt/tracker/tests/test_tracker.py::test_seed_plan_never_uses_test_data` checks that the training, validation and tuning seeds never touch the test seeds or writers.

## 4. Checks: the differentiable tracker is the deployed tracker (SIM tooling)

| Check | Result | Note |
|---|---|---|
| PyTorch AKF against fusion's numba AKF, output relative RMS difference (6 tuning recordings per set, 5 s) | grid-tuned set 1.8e-13; robust set 3.5e-14; 120 Hz / 10 ms page sensor 4.5e-9 | requirement < 1e-2 |
| numba adjoint's forward sweep against the numba AKF | 4.6e-14; 1.2e-14; 2.0e-10 | tracked frequency within 3.8e-7 Hz |
| adjoint against PyTorch autograd through the tensor filter, all 23 parameters (8 validation recordings × 1600 ticks) | largest relative difference 2.2e-11, median 2.2e-13 | 0.22 s against 8.8 s |
| central differences against the adjoint, 7 output-stage parameters, exact gates (8 recordings, step 1e-4) | largest relative error 2.1e-5 (output low-pass); gain 2.1e-10 | |
| central differences, 5 core parameters (q_t, r_a, τ, τ_w, f_min), steps 1e-3 and 1e-4 | do not converge: q_t gives 0.435 and −23.2 against an adjoint of 0.186 | explained below |
| tiny-step central differences (step 1e-7) on single recordings, 7 parameters × 4 recordings | largest relative error 2.1e-5 (median 5.7e-7) over the 25 pairs with a non-zero gradient; 3 pairs are zero in both (f_min never reached) | |
| causality: the estimate at a tick does not change when later samples change (torch filter, adjoint path, GRU, hybrid) | unchanged to 1e-12 relative | unit tests |

**Why the larger steps disagree for the core parameters** (`stage_gradscan`, `results/opt/tracker.json` → `gradient_scan`):
- The objective was scanned along q_t, τ and the gain, ±0.2 % in steps of 0.01 %, by two paths: the adjoint implementation, and fusion's numba AKF. The two agree to 3.5e-14 at every point, so the jumps belong to the filter, not to the rewrite.
- Along q_t, 7 of 40 steps jump by more than 1e-4 beyond what the local slope explains (largest 0.0058, with the objective about 1.56). Along τ one step jumps by 5.5e-4. Along the gain none do: the largest residual, 2.9e-7, is curvature.
- The source is the frequency tracker's discrete decisions. A phase measurement is accepted only if a phase exists, the amplitude exceeds a threshold, the filter time advanced and the larger-oscillator axis is unchanged. A tiny change of a noise or decay setting flips one such decision at some tick. The tracked frequency, and with it the estimate, then differs for the rest of the recording.
- Consequence: the adjoint is the exact derivative of the smooth piece the parameters are in. Across pieces the objective is not differentiable. The optimiser therefore used Adam with a decaying step, and every iterate that was kept was chosen on validation data.
- The training gradient with leaky gates (a surrogate) differs from differences by design. It is stored in `tracker.json` but is not a check.

Unit tests (`opt/tracker/tests/test_tracker.py`, 15 tests): torch against numba (3 parameter sets), adjoint core against numba, parameter round trip, adjoint against autograd, finite differences, causality of the torch filter, the adjoint path and the learned models, the exact sosfiltfilt operator, the low-pass impulse response, the seed plan, and the recorded-data compensation.

## 5. What the adjoint gained and where it failed

### 5.1 Same objective, better optimiser (ACT-48)

| Objective (fusion.tune) | J, random search | J, adjoint | lowest J at iteration (of 30) | Test band ratio | Test distortion, grid / glyph (µm) |
|---|---|---|---|---|---|
| grid (`proxy`) | 0.9587 | 0.9572 | 3 | 0.775 → 0.766 | 21 → 25 / 146 → 154 |
| robust (`proxy_robust`) | 0.9910 | 0.9885 | 29 | 0.910 → **0.863** | 5 → 7 / 21 → **18** |

J values are computed by fusion.tune's own numba code on its own streams (SIM).

- **Robust objective.** The lowest value came at iteration 29 of 30.
  - Its terms on the tuning data: tremor-band residual on the grid 0.982 → 0.976, on the aiguide writers unchanged (0.999 → 1.000); false correction on the aiguide writers 20.9 → 19.8 µm, on the grid writing 2.4 → 3.7 µm (inside fusion.tune's 14 µm budget).
  - On test: band ratio 0.910 → 0.863, glyph distortion 21 → 18 µm, grid distortion 5 → 7 µm.
- **What changed in the robust set** (`results/opt/tracker_models/akf_ship.json`):
  - output: gain 1.14 → 2.0 (the bound); output low-pass 56 → 36 Hz; prediction horizon 0.93 → 0.07 ms;
  - frequency tracking faster: smoothing τ_w 0.30 → 0.12 s; oscillator decay τ 0.15 → 0.21 s;
  - amplitude gate narrower, 5.5–164 µm → 24–133 µm, with smoothing 1.05 → 1.73 s;
  - slow-motion cap: k 3.0 → 2.4, speed 9.8 → 15.3 mm/s, reference time 0.56 → 0.35 s;
  - noise settings by factors 0.5–2.2; the frequency gate (5.9 Hz centre, 2.1 Hz width) almost unchanged.
- **Grid objective.** The best point came after 3 iterations; later iterates were worse (jumps, §4).
  - On test: band ratio 0.775 → 0.766. Distortion rose on both: glyph 146 → 154 µm, grid 21 → 25 µm.
  - That objective does not see sharp writers. Its optimum moves their ink further.

### 5.2 The trade-off, mapped by the λ_fc sweep (ACT-47, `fig_tr_pareto.png`)

- **Chain A** (grid-tuned start, harmonic on) keeps most of the band benefit (0.83–0.91). But it cannot bring sharp writers' tremor-free distortion below 53 µm, even at λ_fc = 1.
- **Chain B** (robust start, harmonic off) spans 6–26 µm of glyph distortion at band ratios 0.88–0.92. Its grid distortion stays at 0.5–3 µm.
- **The shipped set beats chain B.** Its band ratio (0.863) is better than every chain B point. Its glyph distortion (18 µm) lies between chain B's at λ_fc 0.1 (0.888, 17 µm) and at 0.03 (0.880, 24 µm).
  - Its objective includes the aiguide tuning writers writing the study sentence, the same task as the aiguide test (other writers).
  - The chains' glyph writers wrote note lines (fusion's training specs; never the study sentence).
  - Which writers the objective sees mattered more than the optimiser.
- **Validation bounce.** Chain B's validation objective at λ_fc = 0.01 was best at iteration 20 of 40, then rose while training still fell (`fig_tr_training.png`). With 160 training pairs the objective overfits.
  - That validation-best iterate (band 0.853, grid 4 µm, glyph 33 µm on test) has the best band ratio of the AKF sets under 35 µm glyph distortion.
  - On the tuning glyph writers it was 37 µm, so the rule excluded it.

### 5.3 Where it failed or needed care

- **Discontinuous objective (§4).** The frequency tracker's discrete decisions make the objective piecewise smooth, with jumps. The adjoint follows the smooth pieces; iterates were selected on validation, never on the last step alone.
- **Energy-weighted, not per-recording, residual (§3.2).** With per-recording ratios, every λ_fc produced a conservative set.
- **Smoothed gates optimise a different filter (§3.1).** Hence the exact-value / leaky-gradient gates.
- **Local optimisation.** Two starting points; each chain has fixed structure.

## 6. Learned trackers (EML-33, EML-34)

| | GRU, whole-disturbance target (previous) | GRU, tremor-band target (this study) | AKF + learned gate (this study) | Shipped AKF |
|---|---|---|---|---|
| Test-grid 3–15 Hz ratio | 0.808 | **0.796** | 0.873 | 0.863 |
| Test-grid all-band ratio (includes the friction drift) | 0.688 | 0.916 | 0.947 | 0.953 |
| Path to intended letters, grid (µm; none 258) | 282 | **241** | 246 | 242 |
| Time-aligned intent error, grid (µm; none 582) | 608 | 558 | 560 | 559 |
| Distortion, grid / glyph (µm) | 7 / 25 | 14 / 57 | 5 / 53 | 7 / **18** |
| aiguide path, writing only (µm; none 196) | 207 | 195 | 196 | **193** |
| MAC per step (CALC) | 8,304 | 8,304 | 3,000 + AKF | AKF |

- **The target was the problem of the old GRU.**
  - Trained on the whole disturbance, it earned its all-band ratio (0.688) by tracking P1's slow friction drift. Its ink then drifted away from the intended letters: path 282 µm, against 258 without correction.
  - Trained on the tremor band, the same network no longer does this (241 µm), and it has the best causal band ratio after the grid-tuned AKFs.
- **It fails on sharp writers.** Tremor-free glyph writing moved by 57 µm, more than twice the 25 µm of AC-E01-07/09. On the aiguide writers it is no better than no correction.
  - More glyph writers in training (30 % here) or a larger false-correction weight would move it along the same trade-off as the AKF. Its validation false correction rose from 5 µm (epoch 0) to 30–47 µm while its band residual fell (`fig_tr_training.png`).
- **The gate learned what it could see.** On the validation writers (fusion's generators) it halved its base filter's false correction (open loop, 62 → 30 µm at the kept epoch 8; 13.5 → 3.3 µm on tuning seeds 5004–5007, where the band residual rose from 0.775 to 0.835).
  - On the aiguide test writers it is 53 µm, against 101 µm for its base (chain A, λ_fc 0.01) and 18 µm for the shipped set.
  - Its training writers do not cover the aiguide writers' sharp strokes. This is the synthetic version of the real risk of learned trackers.
- **Neither is shipped.** Both stay behind the ICD §5 guard until EXP-E01 (REQ-ML-001, DEC-016).
  - The GRU's margin over the shipped AKF (0.067) is below REQ-ML-001's 0.10, at higher false correction, even in simulation.

## 7. Per-writer tuning by gradient (ACT-50, `fig_tr_personal.png`)

**Test seeds 200–203 at 0.3 mm, 4–12 Hz (20 conditions, closed loop, SIM).**
- Every personal set was fitted on that condition's calibration recording only (seed + 40000: the same writer's calibration task, with an independent tremor realisation).
- Distortion: the sets from the 6 and 10 Hz calibrations, run on the same seed's tremor-free writing.
- Calibration misfit: fusion.personal's score of the fit to the phone's label (1 = no fit).

| Set | 4 Hz | 6 Hz | 8 Hz | 10 Hz | 12 Hz | mean 3–15 Hz ratio | all-band ratio | path (µm; none 235) | distortion (µm) | calibration misfit |
|---|---|---|---|---|---|---|---|---|---|---|
| population (robust AKF) | 1.001 | 0.987 | 0.901 | 0.825 | 0.770 | 0.897 | 0.969 | 228 | 5 (test grid) | – |
| 12-candidate choice (fusion.personal) | 0.998 | 0.875 | 0.705 | 0.612 | 0.583 | 0.755 | 0.925 | 222 | 20 | 0.717 |
| adjoint, calibration fit only | 1.001 | 0.690 | 0.532 | 0.479 | 0.488 | **0.638** | 0.900 | 218 | 55 | 0.539 |
| adjoint, fit + false-correction term (λ_fc,p = 1) | 1.000 | 0.857 | 0.641 | 0.598 | 0.593 | 0.738 | 0.920 | 221 | **19** | 0.654 |
| tremor-band oracle (not causal) | 0.188 | 0.151 | 0.178 | 0.194 | 0.247 | 0.192 | 0.773 | 211 | – | – |

**Choices on tuning seeds 5000–5003** (open loop, 4–12 Hz at 0.3 mm; the test seeds were not used):

| | 12-candidate | population | adjoint, prior weight 0.003 | 0.02 | 0.1 |
|---|---|---|---|---|---|
| tremor-band residual | 0.782 | 0.915 | **0.673** | 0.678 | 0.682 |

| False-correction weight λ_fc,p (prior 0.003) | 0.3 | 1 | 3 | 12-candidate |
|---|---|---|---|---|
| tremor-band residual | 0.711 | **0.765** | 0.938 | 0.782 |
| false correction on the seed's own tremor-free writing (µm, open loop) | 16.0 (above the 12-candidate's) | 8.4 | 1.0 | 9.6 |

**What it means.**
- **The calibration alone asks for more correction than writing tolerates.** Minimising the calibration misfit (0.717 → 0.539) buys tremor-band benefit (0.755 → 0.638). The calibration task always contains tremor, so nothing in it says how quiet to stay on writing. Distortion nearly triples (20 → 55 µm).
- **With the guard, most of the gain goes.** The false-correction term uses a fixed pool of other writers' tremor-free writing, so it needs no extra task from the user. Distortion is back at the 12-candidate level (19 against 20 µm), and the band ratio is 0.738 against 0.755 (−2 %), mostly at 6–10 Hz.
- **Recommendation.** Keep fusion.personal's 12-candidate choice as the calibration default (DEC-025).
  - The guarded refinement is an option worth about 2 % in simulation. It runs on the phone or a PC, not the pen: 20 calibrations took 6 min on 2 cores here.
  - The fit-only refinement should not ship.
  - Both assume the tremor during writing is the tremor of the calibration (§9); the per-user calibration experiment in §10 tests that.

## 8. MCU budget (CALC, EML-35)

nRF54L15-class MCU: Cortex-M33 at 128 MHz with FPU (AMF-44 via `fusion/budget.py`). Cycle model (ASSUMPTION, to be profiled): 2 cycles per float32 MAC; int8 CMSIS-NN at 0.5 MAC per cycle plus 300 cycles per layer call.

| Tracker | MAC per second | CPU share | Per tick, mean / worst | RAM |
|---|---|---|---|---|
| Shipped AKF (any parameter set) | 3.95 M | 6.2 % float32 | 30 / 51 µs per 0.5 ms tick | 2.3 kB |
| GRU(48), tremor-band target | 8.30 M | 13.0 % float32; 13.7 % int8 | 130 µs per 1 ms step | 33 kB float32 weights (8.3 kB int8) + 0.8 kB state |
| AKF + gate GRU(24) | 6.95 M | 10.9 % float32 (11.6 % with an int8 gate) | AKF + 47 µs per 1 ms step | 14.9 kB |
| Frozen Kalman (reference) | 1.34 M | 2.1 % | 10 µs | 0.3 kB |

- The shipped set changes only numbers. Firmware cost, timing and memory are those of the AKF of DEC-025.
- All three fit next to the servo and BLE, as far as operation counts show; the cycle model is an assumption.

## 9. Limits

Most decisive first.

1. **No person, no pen.** Everything is synthetic:
   - writing: sigma-lognormal (P1 grid) or glyph-font writers (aiguide);
   - tremor: the synthetic narrow-band model;
   - the pen: model P1 with the `fusion/` sensor models.

   Every ranking here can change on real writing (EXP-H01, EXP-E01).
2. **The objective decides the tracker.** The adjoint finds the best parameters for the stated objective and data. Several choices are ASSUMPTIONS about the users:
   - the training mix: 40 % glyph writers, tremor 0.05–0.6 mm, randomised pen rotation;
   - the weights: λ_fc, glyph × 3, μ;
   - the selection limits: 14 and 30 µm.

   With the mean of per-recording ratios instead of the energy-weighted residual, the optimum was conservative for every λ_fc (§3.2). The shipped set won because its objective contains the aiguide study task (§5.2).
3. **Training and test share generators.** Training and test use other seeds and writers, but the same sigma-lognormal and glyph generators, the same tremor model and the same P1. The margins of the learned models are in-distribution margins. The hybrid gate's collapse on the aiguide writers (§6) shows how a change of writer can erase them.
4. **Selection partly in-sample.** The re-optimised random-search objectives, like the random-search sets themselves, were fitted on the tuning seeds and writers that the selection rule also uses (§3.5). The test data, used once, agree with the choice.
5. **Friction model.** Most of P1's tremor-induced disturbance is a friction shift below 3 Hz (docs/sensor_fusion_ai.md §3.2). The trackers here target the 3–15 Hz band. The path-to-intended-letters metric rewards that; the all-band ratio does not. EXP-B01/B02 decide which view is right.
6. **Local optimisation of a piecewise-smooth objective.** Adam started from two points. Each chain had fixed structure (second harmonic on or off). The objective has jumps from the frequency tracker's decisions, clamps and gates (§4). A global optimum is not claimed.
7. **External-estimate approximation** (docs/sensor_fusion_ai.md §3.1). Estimates come from the neutral run's housing motion and are replayed into the closed loop.
8. **Open-loop hand.** The writer does not react to the correction.
9. **Personalisation assumes stationary tremor.** The calibration tremor has the test tremor's frequency and amplitude (another realisation), and there is one calibration per condition. Session-to-session change is not modelled.
10. **Budget counted, not profiled.** The cycle model is an ASSUMPTION.
11. **The simulator changed during this study.** Another study edited `sim/pencil` (touchdown feed-forward, off by default). The checks at the end:
    - `sim/pencil/tests/test_default_regression.py` passes with the final sources: default runs are bit-identical to the pre-change baseline;
    - cached neutral records equal fresh runs;
    - four test conditions × 5 trackers, re-run with the final sources, reproduce the stored results to their 6 significant digits.

    The `sim/pencil` source digest recorded by the stages therefore changes (fff7771d… before the test stage, 6dc5f22d… from it on) without changing any result.

## 10. Experiments needed

| Experiment | What to record or run | Decides | Executable here | Dependency |
|---|---|---|---|---|
| **EXP-E01** estimator bake-off on recorded writing | Recordings in the format of `opt/tracker/realdata.py`: raw 6-axis IMU samples with acquisition times (proposed record 0x07 of docs/sensor_fusion_ai.md §8, ≥ 1.9 kHz), page sensor and axial contact with acquisition and availability times, pen attitude. (a) **trace tasks** of known shapes, labelled like the 20 s calibration, without any truth; (b) **free writing** of the target groups and of healthy controls, including the fastest writers. Split by participant first (AC-E01-01). Tune with `opt.tracker.realdata.fit` on the training participants. Report on held-out participants: label misfit in 3–15 Hz and per band (4–8, 8–12 Hz); false correction on controls' free writing (AC-E01-07 and AC-E01-09, ≤ 25 µm); spikes (AC-E01-08) | which set ships (AC-E01-09): the shipped set against the robust and grid-tuned sets and a set re-tuned on the recordings; REQ-ML-001 for the learned models (AC-E01-02) | `python3 -m opt.tracker.realdata --selftest` runs the whole path on simulated recordings in that format | EXP-H01 data; ethics approval |
| **EXP-H01** tremor-at-nib census with normal-speed writing | as in docs/sensor_fusion_ai.md §11, plus the trace tasks above | the training mix (glyph share, tremor amplitudes) and λ_fc | – | ethics; instrumented pen |
| **Per-user calibration** (inside EXP-H01 / E01) | the 20 s calibration task per participant, repeated across sessions, plus a short tremor-free writing sample (or a healthy-control pool) for the false-correction term | whether adjoint personalisation transfers across sessions, and whether its false-correction guard holds on real writing | `opt.tracker.personal.refine` on the calibration recordings | EXP-H01 |
| **EXP-B09** bench cancellation | the shipped parameters on the bench with replayed tremor; log the command spectrum | closed-loop benefit with real contact; jitter above 150 Hz | firmware AKF with the new numbers (no code change) | Rev A/P prototype |
| **EXP-B01 / B02** friction under vibration | as in docs/sensor_fusion_ai.md §11 | whether the tremor-band or the all-band target is right | – | rigs |
| **MCU profiling** (firmware bring-up; no experiment id yet) | cycles of the AKF tick and of the worst rollback tick on the nRF54L15 | the cycle-model ASSUMPTION of §8 | – | board |

## 11. Reproduce, files

```
python3 -m opt.tracker.run_study                      # all stages, about 3-4 h on 2 cores (after the data caches exist)
python3 -m opt.tracker.run_study --stages report      # results/opt/tracker.json, figures, ledger rows from the stage files
python3 -m opt.tracker.report                         # the Markdown tables of this document
python3 -m opt.tracker.realdata --selftest            # the recorded-writing path (EXP-E01) on simulated recordings
python3 -m pytest -q opt/tracker/tests                # agreement, gradients, causality, seed plan (about 2 min)
```

Existing tests with the final sources: `python3 -m pytest -q sim/pencil fusion aiguide` 86 passed (57 s); `opt/tracker/tests` 15 passed (73 s).

Resources: at most 2 worker processes or 2 numba/torch threads at a time. Here the λ_fc sweep ran as two chains in parallel, one thread each (`python3 -m opt.tracker.sweep`, 1.4 h); the other stages took about 1.6 h.

**Code** (`opt/tracker/`, all new; `fusion/`, `sim/`, `aiguide/` and `ml/` are used as read-only libraries):

| File | What it holds |
|---|---|
| `run_study.py` | the entry point and every stage (check, gradscan, sweep, replicate, learned, select, personal, personal_fc, test, budget, report, viz) |
| `schedule.py`, `torch_akf.py` | the event bookkeeping per recording; the PyTorch AKF (task 1) |
| `adjoint.py` | the numba discrete adjoint of the filter core and its PyTorch autograd function |
| `losses.py`, `data.py`, `train_akf.py`, `sweep.py` | the objective; the training and validation data; Adam through the adjoint; the λ_fc chains (task 2) |
| `replicate.py` | fusion.tune's two objectives in PyTorch on its own streams |
| `gradcheck.py` | adjoint against autograd, finite differences, objective scans |
| `evaluate.py` | closed loop on the P1 grid (fusion.harness) and the aiguide writers (fusion.aieval pattern); registers the `opt_*` estimators with fusion's dispatch at run time (no `fusion/` file is edited) |
| `learned.py`, `learned_train.py` | the band-target GRU and the AKF + gate hybrid (task 3) |
| `personal.py` | adjoint personalisation on the calibration task, with the exact PyTorch sosfiltfilt (task 4) |
| `budget.py` | MCU cost (task 5) |
| `realdata.py` | recording format, IMU compensation, labels and fit for recorded pens (EXP-E01) |
| `report.py`, `figures.py`, `evidence.py`, `viz.py` | `tracker.json`, figures, ledger rows, 3-D replay |
| `tests/test_tracker.py` | 15 tests (73 s) |

**Results** (`results/opt/`):
- `tracker.json`: every stage's numbers with provenance; the shipped parameters are also in `tracker_models/akf_ship.json`;
- `fig_tr_ratio_vs_frequency`, `fig_tr_pareto`, `fig_tr_training`, `fig_tr_personal` (`.png` and `.csv`);
- `tracker_models/`: `opt_gru48_band.pt/.json`, `opt_hybrid_gate24.pt/.json` (weights, configuration, training history), `akf_ship.json`;
- `tracker_evidence_rows.csv`: proposed ledger rows in the column format of `docs/evidence.csv` (docs/evidence.csv itself is not edited);
- `viz_tracker.json`: seed 200, 10 Hz, 0.3 mm, with no correction, the physical and tremor-band limits, the previous best tracker, the previous default and the shipped set (schema of `results/fusion/viz_fusion.json`).

**Intermediate** (`opt/tracker/build/`, regenerable, git-ignored by the repository's `build/` rule): stage files `stage_*.json`, sweep runs `runs/sweep_*.json`, logs (including the discarded per-recording-ratio sweep), data caches (about 1 GB). `results/opt/tracker.json` holds every stage's numbers, so nothing reported depends on this folder.
