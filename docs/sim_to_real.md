# Sim-to-real: calibration pipeline, bench time and prediction gap (twin experiments)

**Evidence status: SIMULATION and CALCULATION only.** No hardware exists and nothing here is a measurement. The "bench" is virtual: M1 (`sim/pensim`) or small standalone models with hidden true parameters, seen through measurement models of the instruments `validation/bench_protocols.md` names. Instrument numbers are copied from the protocols (PROTOCOL), the parameter file (CONFIG) or the design (DESIGN), or chosen inside the protocol's instrument class (ASSUMPTION); `s2r/instruments.py` labels each one.

**What twin experiments can and cannot show.** They show that the identification recovers parameters and states honest uncertainty, what an accuracy costs in bench time, how well a calibrated simulator predicts a plant whose structure it shares, and which residual tests catch which kinds of missing physics. They cannot show that M1's structure is right about the pen, or that its EXP-B09 predictions will hold. Every "gap" below is between two simulations; only the bench can close the question.

Code and run times: [`s2r/README.md`](../s2r/README.md). Bench procedure, data formats, gap thresholds and the HIL plan: [`validation/sim_to_real.md`](../validation/sim_to_real.md). Results: `results/s2r/*.json` (with provenance) and `fig_*.png` (stamped SIMULATION).

## 1. Answers in brief

All numbers are SIMULATION or CALCULATION, from twin experiments.

1. **The calibration pipeline is ready and recovers what it should.** It runs in protocol order: EXP-B03 → EXP-B05 → EXP-B01/B02. On 15 blind plants, 5 of them partly outside the declared ranges, the 95th-percentile errors at protocol settings are:
   - actuator: K_f 0.9 %, R20 0.2 %, L 0.25 %, thermal 0.2 %;
   - stage: k_tip 0.5 %, m_eq 1.4 %, ζ 0.13 %, Hall delay a few µs;
   - contact: μ_k 1.2 %, paper stiffness 1.6 %, pre-sliding length 0.4 %.
   Stated U95s cover the truth in 93–100 % of plants for every parameter except the Stribeck speed. That one is unidentifiable when the friction curve has no dip, and its U95 says so (§3.1).
2. **Bench time.** About 15 min per actuator coupon, 40 min per stage build and 33 min per ink × paper × underlay, about 1.5 h per build against 2.5 h at protocol settings, for the same M1-parameter accuracy. The floors are instrument calibration (F/T gain, LDV scale, bath temperature), not duration. K_f needs back-EMF (U95 2.3 % → 1.0 %). More chirps or grid points help only ζ, which no prediction needs, and the Stribeck speed, which needs quarter-decade speeds (§3.2).
3. **A calibrated twin predicts the oracle bound; the Kalman ratio needs more than the stage experiments.** Uncalibrated, the twin meets AC-B09-03's ±0.1 on 4–5 of 15 plants for the oracle ratio. After B03/B05/B01-B02, with the hand simulant's settings known to ±10 %, it meets it on 14 of 15. The Kalman ratio at 9 Hz reaches 9 of 15 that way, and 14 of 15 only when the sensor parameters (EXP-S01/B04) are identified too. Static hold power comes within 2.3 % and NEUTRAL ink error within 15 % (95th percentile). Intent distortion is predicted only within a factor of 2: for 12 of 15 plants, and for all 15 with the sensors identified. (§4)
4. **What dominates.** μ_eff, K_f, k_tip, the hand and the optical noise; the bench delivers each identified parameter at least 3.5× more accurately than the predictions need. The repository's Monte Carlo sensitivity ranks K_f and k_tip last for the Kalman ratio. That is an artefact of M1 handing each plant's values to the controller, and it would mislead bench priorities (§4).
5. **Model-form diagnostics work where the current criteria do not.** Every constructed defect is flagged, and the M1-structure control passes every test. Each stage defect (flexure mode, extra delay and jitter, pivot friction, backlash) is caught by a different combination of the four stage tests. Friction memory is caught by the pre-sliding drift test, and a hand resting on the paper by the NEUTRAL-error gap. The first run exposed two faults in the method itself, both since fixed. The drift test flagged the correct model on a 0.014 % change, until practical margins were added. The pilot-based chirp shaping drove a stage with pivot friction into its stops, until an amplitude ladder was added. AC-B05-01 (resonance ±10 %) passes all the stage defects, and AC-B02-01 (LuGre R² > 0.9) passes friction memory (§5).
6. **Pencil piezo.** A PI inverse identified from one 8 s decaying sweep brings open-loop tracking of a 0.2 mm nib sine to 2.8–3.1 %, against 7 % for a linear gain. It still leaves a 0.34 mm offset under a 0.1 N nib load and 17 % error when the stroke drifts −20 %. With Hall feedback it tracks to 0.5–1.6 %. Under the load the drive saturates at 30 V: a stroke budget problem, not a hysteresis one (§5.4).
7. **Domain randomisation.** The frozen Kalman set's 9 Hz ratio goes from 0.70 on the nominal plant to a median 0.88 on held-out in-range plants; 7 of 16 meet AC-B09-04. Tuning on randomised plants picks a different, more conservative set (v0.4.1's) that is better on 15 of 16 held-out plants by the tuning objective (§6).

## 2. The virtual bench

**Hidden plants** (`s2r/truth.py`). 26 M1 keys in five groups: EXP-B03 actuator (K_f, R20, L, R_th, C_th); EXP-B05 stage (k_tip, ζ, m_eq, Hall delay, k_ax, F_pre); EXP-B01/B02 contact (μ_k, μ_s/μ_k, v_s, k_p, x_pre); hand (six EXP-B06 keys); sensors (optical noise and delay, Hall noise, IMU delay; EXP-S01/B04). The last two groups are part of the truth but are not identified here. C1/C2 use 15 plants: 10 drawn with the declared distributions inside the declared ranges, 5 with about 40 % of their keys pushed 15–50 % of the range beyond a bound (for example K_f 0.40 N/A, k_tip 29 N/m, ζ 0.5, paper 8×10⁵ N/m, optical noise 28 µm). `x_pre` has no declared range; 3–30 µm is an ASSUMPTION. The batch is committed by SHA-256 before identification (`c1_identification.json`, `truth_commitment_sha256`); the identification code sees only recorded datasets.

**Instruments** (`s2r/instruments.py`; the full table with origins is `provenance_table()`):

| Instrument | Model | Origin |
|---|---|---|
| 6-axis F/T (R1, R4) | 5 kHz; 5 mN step; 2 mN RMS; per-axis gain error U(±2 %) per session; 500 Hz mount | PROTOCOL (rate, resolution, ±2 %, ≥ 500 Hz); ASSUMPTION (noise) |
| Goniometer | session angle error U(±0.1°) | PROTOCOL bound; ASSUMPTION distribution |
| Stage encoder, capacitive probe, laser triangulation | 0.1 µm; 5 nm at 10 kHz; 0.1 µm with ±1 µm non-linearity over 1 mm | PROTOCOL; ASSUMPTION (noise) |
| Current source, 4-wire ohmmeter, DMM | ±0.1 %; ±0.02 % at 20.0 ± 0.5 °C; ±0.1 % | PROTOCOL (source, bath band, DMM); ASSUMPTION (ohmmeter) |
| Scope and current probe (R7) | 10 MS/s, 12 bit, ±1 % | PROTOCOL (probe ±1 %, bandwidth); ASSUMPTION (rate, 12 bit) |
| Thermocouples | ±0.5 °C offset | PROTOCOL |
| LDV and rig DAQ (EXP-B05) | 0.1 µm/s; ±1 % scale; 10 kS/s with a shared 4.5 kHz anti-alias | PROTOCOL (resolution); ASSUMPTION (scale, rate) |
| Force probe, tip metrology, axial load cell | 1 mN; 0.5 µm; ±5 mN | PROTOCOL classes; ASSUMPTION (noise) |
| Pen Hall (research frame) | 1 µm RMS, 0.1 µm step, 2 kHz, hidden delay | CONFIG, DESIGN |
| Pen log vs rig DAQ | clock offset U(±50 µs) | PROTOCOL §0.4 |

Session systematics (gains, offsets, angle, sync) are drawn once per session and do not average down with repeats.

**Plant/controller separation** (`s2r/twin.py`). M1 packs one parameter vector, and `model.build_params` hands overridden plant values to the controller too: the servo feedforward uses the true m_eq, k_tip and c_tip, the current reference divides by the true n·K_f, the current-loop PI is built from the true L and R20, γ from the true K_n and k_ax, the horizon from the true IMU delay. Real firmware keeps the constants it was generated with. The shim rebuilds the controller-side entries from a separate "firmware knowledge" set and passes them as layout-name overrides, which `build_params` applies last; no file under `sim/` changes. At nominal it reproduces M1 exactly (tip trajectories within 1e-17 m; `grid.csv` ratios reproduced: Kalman 1.023/0.781 and oracle 0.162/0.203 at 6/9 Hz, 0.3 mm, 12 test seeds). What it cannot separate (R feed-forward in the current loop, the slide estimate s_hat, the contact threshold) is small in these runs; the reference feedforward is matched by one scale factor over 3–15 Hz (residual 0.7–2.3 % of K_p over the 15 plants).

**Experiments, as the protocols prescribe** (deviations in `validation/sim_to_real.md` §2):

- *EXP-B03*: 4-wire R20; voltage steps on the blocked coil (16 averaged scope records); blocked force at the protocol currents {±0.1, ±0.3, ±0.6} A with 2 s holds; back-EMF at 10/20/50 Hz, ±0.5 mm; a 0.2 A thermal step read by coil resistance.
- *EXP-B05* on M1 itself as the protocol's "test build": pen clamped (1e7 N/m fixture), lifted, stage sensor frozen so the position loop is open, current injected through the servo; 10 chirps of 10 s over 1–500 Hz after a pilot chirp; ±0.03 N static test in 8 directions × 3 cycles; axial 0 → 2 N → 0, 3 cycles.
- *EXP-B01/B02* on a numba tribometer that uses M1's contact and LuGre equations with the R1 rig dynamics (vertical slide with dead weight or force axis, holder mount, platen with velocity ripple): indentation 0 → 4 → 0 N at 0.2 N/s plus a hard-flat compliance check; 20 mm strokes after a 1 s dwell at N ∈ {0.2 … 4} N; velocity steps at the 10 protocol speeds × ±t1, ±t2 × N {0.5, 1, 2} × θ {45, 60}°; slow triangular sweeps 5 µm–1 mm; 32 held-out reciprocation records at 3–15 Hz.

## 3. C1: blind recovery, and what an accuracy costs in bench time

### 3.1 Recovery at protocol settings

The pipeline runs in protocol order (B03 → B05 with K_f, L and R20 from B03 → B01/B02) on the 15 committed plants, each with its own session systematics. It uses the protocol settings with the deviations of `validation/sim_to_real.md` §2 (SIMULATION + CALCULATION; `c1_identification.json`, `fig_c1_recovery.png`). Error is estimate/truth − 1. Coverage is the fraction of plants whose truth lies inside the stated U95.

| Parameter (M1 key) | Exp. | RMS error | 95th pct \|error\| | median U95 | coverage of U95 | plants beyond the range |
|---|---|---|---|---|---|---|
| K_f (`actuator.Kf`) | B03 | 0.57 % | 0.89 % | 1.04 % | 1.00 | 3 |
| R20 (`actuator.R20`) | B03 | 0.11 % | 0.20 % | 0.23 % | 1.00 | 1 |
| L (`actuator.L`) | B03 | 0.14 % | 0.25 % | 0.33 % | 1.00 | 1 |
| R_th (`actuator.Rth_coil_amb`) | B03 | 0.11 % | 0.20 % | 0.94 % | 1.00 | 1 |
| C_th (`actuator.Cth_coil`) | B03 | 0.11 % | 0.20 % | 0.94 % | 1.00 | 1 |
| k_tip (`stage.k_tip`) | B05 | 0.32 % | 0.54 % | 0.59 % | 0.93 | 2 |
| ζ (`stage.zeta_open`) | B05 | 0.07 % | 0.13 % | 0.59 % | 1.00 | 1 |
| m_eq (`stage.m_eq`) | B05 | 0.84 % | 1.35 % | 1.56 % | 0.93 | 1 |
| Hall delay (`sensing.hall_delay`) | B05 | 3.97 % (+3 µs bias) | 7.61 % | 3.36 % | 1.00 | 2 |
| k_ax (`stage.axial_k`) | B05 | 0.10 % | 0.15 % | 0.85 % | 1.00 | 2 |
| F_pre (`stage.axial_preload`) | B05 | 1.81 % | 3.68 % | 1.59 % | 0.93 | 1 |
| μ_k (`writing.mu_eff`) | B01/B02 | 0.80 % | 1.18 % | 3.47 % | 1.00 | 3 |
| μ_s/μ_k (`writing.mu_static_ratio`) | B02 | 3.03 % | 4.41 % | 1.03 % | 0.93 | 2 |
| v_s (`writing.stribeck_speed`) | B02 | 36.02 % | 88.48 % | 5.62 % | 0.87 | 1 |
| paper stiffness (`writing.paper_stiffness`) | B01 | 0.80 % | 1.63 % | 2.51 % | 1.00 | 3 |
| x_pre (`friction.x_presliding`) | B02 | 0.23 % | 0.36 % | 0.64 % | 1.00 | 2 |

Reading the table:

- **Uncertainty statements are honest.** Coverage is 0.93–1.00 for every parameter except v_s (0.87). The misses are marginal (m_eq +1.6 % against a U95 of 1.6 %; μ_s/μ_k −1.1 % against 0.9 %), except two v_s plants discussed below.
- **Out-of-range plants are recovered as well as in-range ones** (15–50 % beyond a declared bound, 3 plants per parameter at most). Nothing in the pipeline uses the declared ranges.
- **The Stribeck speed is the one weak parameter.** In two plants v_s is not identifiable: one has no Stribeck dip (μ_s/μ_k = 1.00), the other a very low μ_k (0.035, below the range). The pipeline says so (U95 > 1000 %), and the errors are +78 % and +112 %.
  - In the other 13 plants the error is ≤ 1 % in 10. A weak dip (μ_s/μ_k 1.07) gives 19 % inside a 34 % U95.
  - The two misses are v_s = 6.2 mm/s (+6.3 % against a 5.6 % U95) and v_s = 34 mm/s (+19 % against 13 %). The second is above the declared range, where the half-decade speed grid has three points through the transition.
  - The low-μ plant also carries μ_s/μ_k's RMS: −12 %, inside a 129 % U95.
- **The Hall delay carries a small bias,** +3.1 µs median (−3.1 to +4.6 µs over the 15 plants). It is the residual of correcting M1's discrete-time timing convention (−37 µs) and lies inside U95. On the bench, the R7 logic-analyser measurement of the same delay is the check.

### 3.2 Bench time for a given accuracy

Each experiment was re-run on fresh in-range plants at four durations. Instrument noise was set at the protocol class (×1) and 4× worse (16× for B03), and once with the session systematics removed (ideal calibration) (SIMULATION; `c1_bench_time.json`, `fig_c1_bench_time.png`). Bench time is the recorded time plus per-record overheads for repositioning, zeroing, cooling and settling, which are ASSUMPTIONS stated in each generator. Entries give the 95th-percentile |error| in %: at protocol noise, (at 4× noise), [with ideal calibration]. With 5–6 plants per cell, the B05 and B01/B02 percentiles are close to the worst plant and scatter by about ±50 %, so read trends rather than digits.

| EXP-B03 level (24 coupons per cell) | Bench time | K_f | L | R20 |
|---|---|---|---|---|
| 0.2 s holds, 4 step averages, 45 s thermal, no back-EMF | 8 min | 1.9 (1.7) [0.1] | 0.27 (0.55) [0.22] | 0.18 (0.18) [0.16] |
| 0.5 s holds, 16 averages, 90 s thermal, back-EMF | 15 min | 0.69 (0.71) [0.056] | 0.33 (0.32) [0.2] | 0.17 (0.17) [0.19] |
| **protocol:** 2 s holds, 16 averages, 180 s thermal, back-EMF | 16 min | 0.88 (0.71) [0.043] | 0.26 (0.4) [0.19] | 0.17 (0.19) [0.19] |
| 2 s holds x3, 64 averages, 360 s thermal, back-EMF | 27 min | 0.99 (0.95) [0.035] | 0.27 (0.3) [0.17] | 0.19 (0.17) [0.18] |

| EXP-B05 level (6 plants per cell) | Bench time | k_tip | m_eq | ζ | Hall delay |
|---|---|---|---|---|---|
| 2 chirps x 3 s | 37 min | 0.31 (0.5) [0.14] | 0.94 (0.89) [0.9] | 0.7 (7.6) [5.7] | 2.7 (13) [3.2] |
| 2 chirps x 10 s | 38 min | 0.42 (0.55) [0.089] | 1.5 (0.78) [0.61] | 0.22 (1.7) [0.62] | 2.5 (2.4) [5.3] |
| 4 chirps x 10 s | 38 min | 0.46 (0.32) [0.14] | 1.2 (1.2) [0.88] | 0.14 (0.8) [0.23] | 6.2 (6.7) [4.1] |
| **protocol:** 10 chirps x 10 s | 40 min | 0.43 (0.58) [0.15] | 1.7 (1.3) [1.1] | 0.088 (0.21) [0.11] | 4.1 (8.1) [1.9] |

| EXP-B01/B02 level (5 plants per cell) | Bench time | μ_k | μ_s/μ_k | v_s | paper stiffness | x_pre |
|---|---|---|---|---|---|---|
| reduced grid x1 (1 N, 50 deg, +-t1) | 31 min | 0.54 (0.64) [0.03] | 1.1 (0.45) [0.33] | 11 (1.1) [1.3] | 1.2 (0.86) [0.12] | 0.34 (0.9) [0.053] |
| reduced grid x3 | 54 min | 3.5 (0.48) [0.39] | 1.3 (1) [0.81] | 5.3 (54) [4.4] | 1.2 (1.1) [0.23] | 0.46 (0.32) [0.046] |
| protocol grid x1 (3 N x 2 angles x 4 directions) | 93 min | 0.94 (1.3) [0.036] | 1.3 (1.5) [0.38] | 3.3 (5.7) [1] | 1.6 (1.4) [0.12] | 0.48 (0.28) [0.054] |
| reduced grid x1, quarter-decade speeds (proposed) | 33 min | 0.78 (1.8) [0.056] | 0.67 (1.9) [0.2] | 4.4 (4.5) [0.66] | 0.87 (1.7) [0.075] | 0.49 (0.55) [0.11] |

What bench time buys:

- **EXP-B03: about 15 min per coupon.** K_f is limited by calibration, not by time.
  - From the F/T alone its U95 is 2.3 %: TUR 4.3 against AC-B03-01's ±10 %, just above the §0.5 minimum of 4.
  - Adding back-EMF (LDV route) brings U95 to 1.0 %, TUR 9.6. Longer holds, repeats and more averages add nothing (0.7–1.0 %). With ideal calibration, the random part is 0.03–0.1 %.
  - L is the only noise-limited parameter: 2.2 % at 16× noise with 4 averages, 1.1 % with the protocol's 16.
  - R20 and the thermal pair sit at 0.2 %, set by the ±0.5 °C bath band.
  - The 0.5 s-hold level (15 min) matches the protocol's accuracy without its 13 K of coil heating.
- **EXP-B05: about 40 min per build and fixture.** Nearly all of it is setup, the static test and the axial test.
  - At protocol noise, two 10 s chirps give k_tip, m_eq and ζ as well as the protocol's ten. The extra chirps take ζ to 0.1 %, which no prediction needs (C2: ζ's requirement is > 300 %).
  - At 4× noise, two 3 s chirps are not enough (ζ 7.6 %, delay 13 %); two to four 10 s chirps are.
  - Two floors do not fall with more chirps: m_eq's 1–1.7 %, which comes from K_f (B03) and the LDV and current scales, and the Hall delay's few µs of timing-convention residual (§3.1).
- **EXP-B01/B02: 31–93 min per ink × paper × underlay.**
  - μ_k, μ_s/μ_k, paper stiffness and x_pre reach 0.3–1.7 % on the reduced grid (1 N, 50°) in 31 min; the full grid does not improve them. Their floor is the F/T gain and angle systematics (0.03–0.4 % with ideal calibration).
  - The Stribeck speed is the parameter that needs the grid: 11 % on the reduced grid, 3–4 % with the proposed quarter-decade speeds (33 min) or the full protocol grid (93 min).
  - The full grid is still needed for the EXP-B01 map (AC-B01-03), which is not an M1 parameter.
- **Totals.** The M1 parameters of one build cost about 1.5 h: B03 15 min per coupon, B05 40 min, and 33 min per ink × paper × underlay on the reduced grid with quarter-decade speeds. At protocol settings they cost about 2.5 h. At protocol settings, every identified parameter has TUR ≥ 7.9 against the acceptance band it is judged by (K_f 9.6 with back-EMF, m_eq 7.9, k_tip 26, μ_k 12, v_s 21).

## 4. C2: does the calibrated twin predict the hidden plant?

Each of the 15 hidden plants runs the unchanged nominal firmware, and so does every twin. Outcomes are taken at the EXP-B09 primary cells: θ 50°, N 1 N, 0.3 mm tremor at 6 and 9 Hz, the 12 TEST seeds, the frozen Kalman set from `results/sim/estimator_selection.json`. Four twins are compared with the hidden plant (SIMULATION, `c2_twin.json`, `fig_c2_gap.png`):

- *before*: `config/parameters.yaml` v0.4.4 as it stands;
- *after (hand nominal)*: the B03, B05 and B01/B02 estimates, with hand and sensor keys nominal, as a human-writer twin would be before EXP-B06;
- *after*: those estimates plus the hand at the R2 simulant's as-set values, drawn as true ±10 % (the protocol's qualification band), with sensors nominal. This is the EXP-B09 twin that AC-B09-03 describes;
- *after + sensors*: as *after*, with the sensor keys (optical noise and delay, Hall noise, IMU delay) at their true values, standing in for EXP-S01/B04.

| Outcome (prediction − hidden plant) | before | after (hand nominal) | after | after + sensors |
|---|---|---|---|---|
| ORACLE ratio 6 Hz: RMS; worst; within ±0.1 | 0.385; 0.79; 5/15 | 0.178; 0.42; 8/15 | **0.041; 0.105; 14/15** | 0.043; 0.13; 14/15 |
| ORACLE ratio 9 Hz | 0.381; 0.76; 4/15 | 0.171; 0.36; 7/15 | **0.049; 0.124; 14/15** | 0.023; 0.057; 15/15 |
| Kalman ratio 6 Hz | 0.242; 0.72; 8/15 | 0.203; 0.62; 8/15 | 0.136; 0.42; 12/15 | **0.048; 0.16; 14/15** |
| Kalman ratio 9 Hz | 0.393; 1.17; 5/15 | 0.301; 0.88; 4/15 | 0.223; 0.71; 9/15 | **0.065; 0.24; 14/15** |
| NEUTRAL ink error 6 / 9 Hz, relative: RMS | 33 % / 42 % | 27 % / 50 % | **7.2 % / 7.0 %** | 4.4 % / 6.3 % |
| Static hold power, relative: RMS; worst | 49 %; 113 % | **1.1 %; 2.3 %** | 1.3 %; 2.3 % | 1.2 %; 1.9 % |
| Kalman M-dist: RMS; worst; within a factor of 2 | 164 µm; 520 µm; 7/15 | 139 µm; 425 µm; 9/15 | 162 µm; 410 µm; 12/15 | **85 µm; 280 µm; 15/15** |

The hidden plants span ORACLE ratios 0.16–0.87 (10th–90th percentile at 6 Hz) against a nominal prediction of 0.16, so the uncalibrated twin is wrong for most of them. After calibration **the oracle bound is predicted to AC-B09-03's ±0.1 for 14 of 15 plants, if the hand simulant's settings are known to ±10 %.** Without the hand, only half are. The **Kalman ratio needs the sensor keys as well.** With sensors nominal, 9 of 15 plants are within 0.1 at 9 Hz; with them at their true values, 14 of 15. **Static hold power** depends only on K_f and R20 and is predicted within 2.3 % once EXP-B03 is in. **Intent distortion (M-dist) is the hardest outcome.** The hidden plants span 23–297 µm (10th–90th percentile), and on one plant the gate never opens (0 µm). With the sensor keys nominal, 12 of 15 predictions fall within a factor of 2, and 13 of 15 give the right verdict against AC-B09-06's 50 µm. With the sensor keys identified, all 15 fall within a factor of 2 (rank correlation 0.95), but the RMS error is still 85 µm.

**Which parameters dominate** (`c2_sensitivity.json`, `fig_c2_sensitivity.png`; central differences of ±ln 1.25 about the nominal plant, nominal firmware, 6 test seeds, common random numbers; CALCULATION on SIMULATION). Per unit ln(parameter):

| Outcome | Largest sensitivities |
|---|---|
| ORACLE ratio 9 Hz | hand arm stiffness −0.18, μ_eff +0.17, grip stiffness −0.12, m_eq +0.075, hand mass +0.062, K_f −0.055 |
| Kalman ratio 9 Hz | μ_eff +0.40, **K_f +0.38**, **k_tip −0.26**, optical noise +0.22, hand mass −0.22, hand arm stiffness −0.07 |
| Kalman ratio 6 Hz | μ_eff +0.076, hand arm damping −0.071, optical noise +0.068, grip stiffness −0.053, k_tip −0.051 |
| Static hold power (relative) | K_f −2.1, R20 +1.0 (P ∝ R/K_f²) |

**What the bench must deliver.** This is the accuracy per parameter that keeps a ratio within ±0.05 (half the AC-B09-03 band), with the budget shared by RSS over the parameters that matter. For the Kalman ratio at 9 Hz, the tightest outcome: K_f 4.4 %, μ_eff 4.2 %, k_tip 6.5 %, R20 27 %, m_eq 36 %, x_pre 37 %, paper stiffness 41 %, v_s 43 %, μ_s/μ_k 76 %. The protocol-level identification of C1 meets all of these with a margin of 3.5× or more (K_f p95 0.9 %, μ_eff 1.2 %, k_tip 0.5 %). **The identified parameters are not what limits the prediction. The hand and the sensors are**, and neither is identified by the experiments modelled here.

**The Monte Carlo ranking in `results/sim/mc_sensitivity.json` is the wrong guide for bench priorities for the Kalman ratio.** There, K_f and k_tip rank 18th and 17th of 18 (Spearman ρ −0.001 and 0.004). Under fixed firmware they are the 2nd and 3rd most influential parameters. The cause is M1's plant/controller conflation (§2): `run_sweeps.py` passes each sample as plain overrides, so the controller is regenerated for every plant's K_f and k_tip and their errors never reach the loop. C4 measures the same effect directly: on in-range plants, the Kalman ratio from plain overrides differs from the fixed-firmware ratio by up to 0.29 (95th percentile |Δ|, 9 Hz). For the oracle the two rankings agree moderately: the rank correlation of the absolute sensitivities over the 16 shared parameters is 0.55, against 0.17 for the Kalman ratio.

**Gap attribution.** Each plant's *before* gap was split by group: the sensitivity times ln(true/nominal), summed per group. The split explains the simulated gaps poorly: correlation 0.37–0.59 with the directly simulated gap, and a residual about as large as the gap itself. The plants span the declared ranges, well outside the local linear regime. So C2 re-simulates every twin rather than propagating linearly. Read qualitatively, the contact group (μ_eff above all) is the largest term for about half the plants: 8 of 15 for the ORACLE ratio at 9 Hz and 7 of 15 for the Kalman ratio. The hand is largest for 5 and 3 of 15. The sensors are largest for 4 of the 15 Kalman cases and for none of the oracle cases.

## 5. C3: model-form gap (truths M1 cannot represent)

`c3_modelform.json`, `fig_c3_model_form.png` (SIMULATION; the effect sizes are constructed, not claimed). Each truth has one piece of physics that M1 lacks, and is identified blind with M1's structure. The diagnostics, their thresholds and the full table are in `validation/sim_to_real.md` §5.

### 5.1 Stage (EXP-B05 test build, three excitation levels)

| Truth (stage, EXP-B05 test build) | Worst band χ²/dof (band) | G1 off resonance: dB / ° | Output error: excess over sensor noise; white | Drift across levels | Hall delay − design | Flagged by |
|---|---|---|---|---|---|---|
| control (M1 structure) | 1.4 (8–20 Hz) | 0.00 / 0.0 | 0.99; yes | none (ζ significant, below margin) | +3 µs | **none** |
| flexure mode 220 Hz (10 % of the mass) | 4.4×10⁵ (160–240 Hz) | 27.94 / 90.2 | 1.29; no | none | +2426 µs | band χ², G1, OE not white, delay |
| flexure mode, refit 2–120 Hz after the flag | 1.5×10⁴ (100–160 Hz) | 0.84 / 0.8 | 1.28; no | none | −23 µs | band χ², OE not white |
| extra loop delay 150 µs + 20 µs release jitter | 0.022 (240–300 Hz) | 0.01 / 0.0 | 2.99; no | none | +180 µs | OE excess, OE not white, delay |
| pivot Coulomb friction 0.3 mN | 3.6×10³ (2–8 Hz) | 0.12 / 4.9 | 3.07; no | f_n 1.3 %, ζ 176 %, delay 59 µs | +7 µs | band χ², OE excess, OE not white, drift |
| backlash ±2 µm | 2.4×10³ (240–300 Hz) | 0.36 / 0.3 | 0.99; no | none | +6 µs | band χ², OE not white |

- **The M1-structure control passes every test at every level.** The first run did flag it: f_n changed by 0.014 % between levels at p = 0.003. That prompted the practical margins on the drift test (1 % f_n and m_eq, 5 % ζ, 5 µs delay), which sit at about a tenth of what C2 says the predictions need. The margins were set after seeing the control and are labelled as such.
- **Each defect leaves a different fingerprint.**
  - *Flexure mode at 220 Hz:* the whole fit collapses, with the mode absorbed as 2.4 ms of "delay". Refitting below the flagged band recovers f_n and ζ and passes G1 and G2, but m_eq and k_tip come out 10–11 % low. The band χ² above 100 Hz and a non-white output error still flag it.
  - *Extra delay of 150 µs:* the FRF fits perfectly, because the fitted delay absorbs it. Only the delay check (+180 µs against design) and the output error (3.0× the sensor noise) see it.
  - *Pivot friction:* the low-frequency bands fail and the output error is 3.1× the noise. ζ drifts from 0.058 at 100 µm to 0.16 at 10 µm, and the apparent delay grows by 59 µs at small amplitude.
  - *Backlash of ±2 µm:* shows only in the top band and in the whiteness of an output error that is no larger than the sensor noise; m_eq is 4–5 % low.
- **Pilot-based chirp shaping fails with friction.** In the first run, a pilot friction-dominated at 5 µm under-predicted the response, and the chirp shaped on it drove the tip to 0.65–6.8 mm, beyond the 0.6 mm stops. The two-step amplitude ladder now used (5 % and 25 % of the target, each reshaped on the previous chirp) kept every chirp within 0.39 mm (proposed as a protocol change).
- **AC-B05-01 (resonance within ±10 % of prediction) passes all of these stages except the collapsed flexure fit.** f_n stays within 1.4 % of the control's at every level.

### 5.2 Friction memory (EXP-B01/B02)

| Truth | x_pre from the 50 / 200 / 1000 µm sweeps | Held-out R² (AC-B02-01) | Small-amplitude NRMSE, mean-removed |
|---|---|---|---|
| LuGre (control) | 10.03 / 10.03 / 10.03 µm | 0.993 | 0.024 |
| Maxwell-slip (friction memory) | 9.2 / 15.7 / 16.3 µm (**drift 55 %**) | 0.987 | 0.101 |

AC-B02-01 as written (held-out R² > 0.9) passes both truths. Friction memory shows as a pre-sliding length that grows with sweep amplitude, and the drift test catches it (0.1 % against 55 %). The held-out prediction error rises only to the edge of a 0.10 threshold. Separately, with the protocol-class F/T, the correct model fails AC-B02-01 for a low-friction ink: R² 0.77 at μ_k 0.035, because of cross-axis gain errors (C1). Removing each record's mean restores R² ≥ 0.98. Proposals are in `validation/sim_to_real.md` §6.

### 5.3 Hand resting on the paper (EXP-B09)

The ratios hardly notice it. The ORACLE ratio is 0.142 against 0.162 predicted, and the Kalman ratio at 9 Hz 0.73 against 0.78; both are inside ±0.1, so G5 and G6 pass. The NEUTRAL error does notice: the twin over-predicts it by 19 % and 61 % at 6 and 9 Hz, so G7 fails. The band-resolved ratio localises the effect below 3 Hz (truth/twin 0.78 and 0.67 in 1–3 Hz; 1.0–1.2 in the other bands). The twin's Kalman M-dist is 100 µm against the truth's 56 µm. A hand resting on the page is therefore a B09 condition to control and record (R2 simulant with or without palm support), not a parameter to fit.

### 5.4 Pencil piezo stage: hysteresis, inverse feedforward and closed-loop sensing

*Plant* (`s2r/piezo.py`; SIMULATION with ASSUMED hysteresis). One bender per axis, with `config/pencil.yaml`'s per-plate figures: ±0.45 mm free stroke at ±30 V about mid, 0.23 N blocked force, lever 1.363, first resonance 123 Hz with the collar mass and leaf. Hysteresis is a Bouc–Wen truth with a 13.7 % major-loop width, inside the ASSUMED 10–15 % class of PICMA benders. Creep is 1 %/decade, also ASSUMED. The Hall read-out has the noise and delay of `sensing.hall_*`. This is a stand-in for one axis of the quad stage; it is not the pencil's mechanism model (`sim/pencil`).

*Identification* from one 8 s decaying sine sweep (±30 V → 0, nested loops, `fig_c3_piezo.png` left). A 9-operator Prandtl–Ishlinskii model (NNLS weights, analytic inverse) leaves 4.0 µm RMS over a 723 µm stroke (0.55 %; 3.9 µm without sensor noise, so the model-form floor is Bouc–Wen vs PI). A linear gain leaves 13.7 µm (1.9 %). The identified small-signal gain is 13.7 µm/V against the 19.7 µm/V of free stroke per volt from the data sheet. Feedforward built on the data-sheet gain would start 30 % off.

*Tracking* of a 0.2 mm nib sine at 4–12 Hz. Error is the 3–15 Hz band RMS relative to the reference RMS, so a static offset under load does not count here; totals are in `c3_piezo.json`.

| Scheme | Free nib | 0.1 N transverse nib load | Stroke −20 % (ageing or temperature), model not re-identified |
|---|---|---|---|
| Linear feedforward | 7.1–7.5 % | 7.1–7.5 % (plus a 0.35 mm static offset) | 21–22 % |
| PI inverse feedforward | **2.8–3.1 %** | 2.8–3.1 % (plus a 0.34 mm static offset) | 17–18 % |
| Feedback only (Hall, 40 Hz notched PI) | 9–27 % | 11–27 % | 12–33 % |
| Linear feedforward + feedback | 0.8–2.0 % | 3.0–6.8 % | 2.4–6.6 % |
| PI feedforward + feedback | **0.5–1.6 %** | 3.9–6.9 % | **1.8–5.1 %** |

Findings (SIMULATION):

- **Inverse-hysteresis feedforward alone does not hold position.** Under a 0.1 N nib load it leaves a 0.34 mm static offset, nearly all of the ±0.36 mm stroke seen in the identification sweep. With the stroke 20 % low (ageing or temperature) the error grows six-fold. Closed-loop position sensing is required.
- **With feedback**, the PI inverse still halves the error of a linear feedforward in the free case (0.5–1.6 % vs 0.8–2.0 %) and under stroke drift. Feedback alone is poor: the 123 Hz bender mode limits its crossover to about 40 Hz even with a notch, so a 12 Hz reference is tracked with 27 % error.
- **Under load, the drive runs out of voltage, not model accuracy.** Taking back the load's 0.35 mm deflection uses most of the ±30 V range. Every feedback scheme hits the 30 V limit (`u_peak_V` in `c3_piezo.json`) and clips at the peaks of the 0.2 mm sine, leaving 4–5 µm of offset and 3–7 % band error. This is a stroke-budget finding for the pencil (compare `stage_under_load` in `config/pencil.yaml`), not a hysteresis one.

What the bench (EXP-Q04/Q06 class) must add: the real hysteresis and creep (the class figures above are ASSUMED), the Hall's calibration across the stroke, and the load at the nib while writing.

## 6. C4: frozen Kalman set and oracle on held-out randomised plants

`c4_domain.json`, `fig_c4_domain.png` (SIMULATION). There are 24 held-out plants from a fresh seed: 16 drawn inside the declared ranges and 8 partly outside. Every truth key is drawn, hand and sensors included. All run the nominal firmware through the shim at the B09 primary cells, on 4 TEST seeds.

| Outcome | nominal plant | in range: median (10th–90th pct) | partly out of range | in-range plants passing |
|---|---|---|---|---|
| ORACLE ratio 6 Hz | 0.18 | 0.30 (0.19–0.62) | 0.33 (0.14–0.81) | AC-B09-02 (≤ 0.5): 13/16 |
| ORACLE ratio 9 Hz | 0.23 | 0.38 (0.18–0.69) | 0.44 (0.12–0.89) | AC-B09-02: 11/16 |
| Kalman ratio 6 Hz | 1.01 | 1.07 (0.99–1.42) | 1.00 (1.00–1.10) | AC-B09-05 (≤ 1.05): 7/16 |
| Kalman ratio 9 Hz | 0.70 | 0.88 (0.68–1.15) | 1.00 (0.59–1.14) | AC-B09-04 (≤ 0.8): 7/16 |
| Kalman M-dist, 6 Hz seeds | 84 µm | 132 µm (42–353) | 11 µm (0–355) | AC-B09-06 (≤ 50 µm): 3/16 |

The oracle bound degrades gracefully, and most in-range plants still meet AC-B09-02. **The frozen Kalman set does not hold its nominal performance across the ranges.** At 9 Hz its median ratio rises from 0.70 to 0.88, and fewer than half of the in-range plants meet AC-B09-04. Below the gate, more than half exceed the AC-B09-05 no-harm limit. On 3 of the 8 out-of-range plants the ratio is exactly 1.00 at 9 Hz: the frequency gate never opens, so the set does no harm and no good. All three have optical noise of 18–31 µm, against 0.4–10 µm on the other five.

**Tuning on randomised plants vs the nominal plant** covers six candidates from `sim/tune_estimators.py`'s grid, including the frozen v0.4.4 set and the v0.4.1 inert set. The objective is tune_estimators' J = mean(ratio + distortion/base) over 4.5–10 Hz, on TUNING seeds.

| Candidate (kf_qj, kf_qt, gate) | J nominal plant | J, 8 training plants | J, 16 held-out plants: mean (90th pct) | better than frozen on held-out plants | ratio 6 Hz / 8–10 Hz, held-out | distortion, held-out |
|---|---|---|---|---|---|---|
| 0: 0.1, 1e-8, 7.5 Hz (frozen, v0.4.4) | **1.19** | 1.49 | 1.55 (1.98) | — | 1.17 / 0.91 | 186 µm |
| 1: 10, 3e-9, 7.5 Hz (v0.4.1 inert set) | 1.25 | **1.18** | **1.14** (1.31) | 15 of 16 | 1.00 / 0.98 | 54 µm |
| 2: 1, 1e-8, 7.5 Hz | 1.56 | 1.83 | 1.77 (2.45) | 2 of 16 | 1.27 / 0.97 | 238 µm |
| 3: 0.3, 1e-8, 6.5 Hz | 1.75 | 1.92 | 1.83 (2.54) | 0 of 16 | 1.24 / 0.95 | 270 µm |
| 4: 3, 3e-9, 7.5 Hz | 1.28 | 1.24 | 1.23 (1.44) | 15 of 16 | 1.05 / 0.96 | 81 µm |
| 5: 0.1, 3e-9, 7.5 Hz | 1.29 | 1.36 | 1.35 (1.67) | 16 of 16 | 1.12 / 0.87 | 135 µm |

Nominal tuning re-selects the frozen set. Tuning on randomised plants selects the v0.4.1 inert set (kf_qj 10, kf_qt 3e-9). On the held-out plants that choice lowers J from 1.55 to 1.14 and is better on 15 of 16 plants. It does this by doing less: ratio 1.00 instead of 1.17 below the gate, and M-dist 54 µm instead of 186 µm. The price is less cancellation at 8–10 Hz (0.98 vs 0.91). The ranking between the two depends on the objective's distortion weight (λ = 1). Every candidate has J > 1 on every plant set, the nominal plant included. On this objective none beats NEUTRAL on average, in line with the expected FAILs the criteria file already records for AC-B09-05/06. On held-out plants, the frozen set ranks 4th of the 6 candidates. **The recommendation for the lead is procedural, not a new set:** choose estimator sets on randomised plants under the fixed-firmware shim, with λ fixed beforehand. The M1-internal Monte Carlo (`run_sweeps.py`) cannot show this, because it regenerates the firmware for every plant. On these same held-out plants, its Kalman ratios differ from the fixed-firmware ones by a median of +0.01/+0.04 (6/9 Hz) and up to 0.26/0.29 (95th percentile |Δ|).

## 7. Limits

- **Shared structure.** In C1, C2 and C4 the truth has M1's structure, so the recoveries and prediction gaps are best cases. C3 constructs five kinds of missing physics at assumed sizes. It shows which diagnostic sees which kind; it does not map detection thresholds, and a smaller or different effect may go unseen.
- **Instruments.** Every noise, bandwidth and latency figure the protocols do not give is an ASSUMPTION inside the protocol's instrument class (`s2r/instruments.py`, `provenance_table()`). Real instruments add effects not modelled here: F/T thermal drift, LDV dropouts, fixture compliance beyond the 1e7 N/m clamp, paper humidity. The bench-time answers scale with these assumptions.
- **Experiments not modelled:** EXP-B04 (Hall and optical calibration), EXP-B06 (human hand), EXP-S01 (optics), EXP-B07 (two-node thermal), and B09's ink metrology. C2 stands in for them by taking the hand as known to ±10 % and the sensors as nominal or true. C2's main finding, that the Kalman prediction needs the sensors, is only as good as that stand-in.
- **The shim** separates plant from controller for the entries M1 hands over (§2). Three entries still follow the plant: the current-loop R feedforward, the slide estimate and the contact threshold. It is exact at nominal and its reference-feedforward residual is 0.7–2.3 % of K_p.
- **Operating point and seeds.** Outcomes are at the B09 primary cells only (θ 50°, 1 N, 0.3 mm, 6 and 9 Hz). C2 uses 12 TEST seeds, the sensitivities 6 and C4 4 (3 for the candidate comparison). With common random numbers, the standard error of one plant's 12-seed mean gap is about 0.008 for the ORACLE ratio and 0.024 for the Kalman ratio in the median plant, and 0.06–0.17 in plants where the Kalman gate opens on some seeds and not others. A "within ±0.1" count can move by a plant or two between seed sets.
- **Ranges are not populations.** Hidden plants are drawn from the declared ranges of `config/parameters.yaml` (plus 15–50 % beyond). The C4 pass fractions are fractions of that box, not a yield forecast.
- **The piezo demo** is a single-bender stand-in with ASSUMED hysteresis and creep. The HIL section is a specification only.

## 8. Proposed changes for the lead

None of these is made here; the files named are under the checker's control.

*Protocols* (`validation/bench_protocols.md`; details and evidence in `validation/sim_to_real.md` §2):

1. EXP-B05: shape the open-loop chirp from a 5 µm pilot and an amplitude ladder instead of a flat 0.05 A chirp. The flat chirp drives the stage into its stops.
2. EXP-B05: static stiffness at ±0.03 N, or a probe force set from the pilot FRF, not ±0.2 N (2.5 mm at 80 N/m).
3. EXP-B05: log the injected current reference as float32, and estimate the FRF with the instrumental-variable estimator against the known digital excitation.
4. EXP-B03: 0.2 s holds with cooling, or per-point ΔT by resistance; the 2 s holds heat the coil by about 13 K.
5. EXP-B03: back-EMF becomes a required K_f estimate; terminal voltage recorded at ≥ 12 bit.
6. EXP-B02: add quarter-decade speeds through the Stribeck transition.
7. EXP-B01/B02: calibrate the F/T gains and cross-axis terms at the test angles.

*Acceptance criteria* (`validation/acceptance_criteria.csv`; details in `validation/sim_to_real.md` §4 and §6):

8. AC-B09-03: add EXP-B03, EXP-B04 and EXP-S01 to the re-parameterisation list; the hand is the simulant as set. Add G7 and G8. Judge M-dist agreement as a factor-of-2 band with the same verdict (G9).
9. AC-B02-01: replace R² > 0.9 with small-amplitude NRMSE, pre-sliding drift and per-record mean-removed R².
10. New EXP-B05 model-validation criterion from the §5 diagnostics. AC-B05-01's ±10 % resonance check passes every structural defect C3 tried.
11. AC-B02-02: judge v_s only when the Stribeck dip is resolved.

*Simulator and studies:*

12. `sim/pensim/core.py`: split the plant step from the controller tick, as the HIL needs (`validation/sim_to_real.md` §7). The s2r shim then becomes unnecessary.
13. `sim/run_sweeps.py` Monte Carlo and `results/sim/mc_sensitivity.json`: its Kalman-ratio sensitivities regenerate the firmware for every sample (plant/controller conflation). Either evaluate the MC under fixed firmware (as `s2r.twin.shim` does) or label the file accordingly. Under fixed firmware, K_f and k_tip are the 2nd and 3rd most influential parameters for the Kalman ratio at 9 Hz; the MC ranks them last.
14. Estimator selection: choose sets on randomised plants under fixed firmware (C4). The nominal-plant optimum (the frozen set) ranks 4th of the 6 candidates on held-out plants.
15. An HDF5 converter for `s2r-bench-1` needs h5py in `requirements.txt`.

## 9. Files

| Path | Content |
|---|---|
| `s2r/` | Package: instruments, hidden truths, plant/controller shim, virtual EXP-B03/B05/B01-B02, identification, C3 structural truths and piezo model, bench-file I/O ([`s2r/README.md`](../s2r/README.md)) |
| `s2r/tests/` | pytest: instrument labels and models, estimators and diagnostics, the shim's exact reproduction of M1, the fast harness against `sim/pensim/harness.py`, recovery of known coupons, stage and contact, the standalone stage against M1, PI inverse exactness |
| `s2r/run_all.sh` | Full chain in dependency order |
| `validation/sim_to_real.md` | Bench procedure: workflow, protocol deviations, data formats, gap metrics G1–G9 with thresholds, diagnostics, criterion proposals, HIL specification |
| `results/s2r/c1_identification.json`, `fig_c1_recovery.png` | C1 recovery on 15 committed hidden plants |
| `results/s2r/c1_bench_time.json`, `fig_c1_bench_time.png` | C1 recovery vs duration and instrument noise |
| `results/s2r/c2_twin.json`, `fig_c2_gap.png` | C2 before/after prediction gaps |
| `results/s2r/c2_sensitivity.json`, `fig_c2_sensitivity.png` | C2 local sensitivities, accuracy budget, MC ranking comparison, gap attribution |
| `results/s2r/c3_modelform.json`, `fig_c3_model_form.png` | C3 stage, friction-memory and hand-on-paper diagnostics |
| `results/s2r/c3_piezo.json`, `fig_c3_piezo.png` | C3 pencil piezo hysteresis identification and tracking |
| `results/s2r/c4_domain.json`, `fig_c4_domain.png` | C4 degradation and tuning comparison |
| `results/s2r/c5_example.json`, `results/s2r/virtual_bench_example/` | Example bench files in the `s2r-bench-1` layout, written and re-read by the pipeline |
| `results/s2r/logs/` | Run logs |

Every JSON carries `stabpen.provenance.metadata()`: git revision, parameter version and digest, seeds, command. Every figure is stamped SIMULATION.
