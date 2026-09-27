# Simulation report — model M1, parameters v0.4.2

**Evidence status: SIMULATION.** Every number below comes from executable models on synthetic signals, with parameters from literature, datasheets, CAD or assumption (`config/parameters.yaml` records which). None is a measurement of a pen or a person.

## 1. Models

| ID | Model | What it represents | Code | Verified by | Validated by (to do) |
|---|---|---|---|---|---|
| M1 | Coupled pen–hand–paper dynamics | Lever stage (tip-equivalent, pivot arc, stops), refill axial suspension (κ_s = 1), LuGre paper friction and compliant contact, two-stage hand, housing rigid body, two coils (R–L, thermal node, voltage saturation), sensors (Hall, optical, IMU, axial force: delay, noise, crosstalk, dropouts), full controller (estimators, servo, current loop), fault injection | `sim/pensim/` (numba, 25 µs step) | 12 unit tests (`sim/tests`); static load within 0.1–2.1 % of P-6 | EXP-B01/B02/B05/B06/B09 (`docs/physics.md` table) |
| M2 | Electromagnetic actuator | magpylib fields of the flat sandwich and alternatives; K_f, K_m, saturation, crosstalk | `analysis/em_actuator.py`, `em_planar.py` | Analytic cross-check (flat-coil proxy) | EXP-B03 |
| M3 | Thermal network | Coil → gap → magnets → barrel → hand/air; copper tempco | `analysis/thermal.py` | Energy bookkeeping | EXP-B07 |
| M4 | Drive stage | H-bridge, shunt, INA241, anti-alias, comparators, latch, load switch | `electronics/spice/drive_stage.cir` (ngspice) | Agreement with the analytic ripple (104 mA p-p both) | Bring-up steps 6–8 |
| M5 | Flexures and tolerances | Gimbal, diaphragm, clearance stacks | `mechanics/flexure_calc.py`, `tolerance_analysis.py` | Beam-theory limits | EXP-M02, B05 |

**Numerical method (M1).**

- Symplectic Euler at 25 µs for mechanics, with an exact exponential step for coil current.
- Controller rates as designed: current loop 40 kHz, stage 2 kHz, IMU 3.84 kHz, optics 1 kHz.
- A 6 s run takes ~0.1 s, so the complete evidence chain (`sim/run_all.sh`) re-runs in 10–25 minutes on 4 cores.

## 2. Protocol

- **Signals.**
  - Sigma-lognormal handwriting with pen lifts, from `stabpen/signals.py`. Its intended-velocity spectrum puts ~17 % of energy in 4–7 Hz, matching the literature figure (COR-28).
  - A deterministic feature course: corners, dots, 4 Hz hatching, fast stroke, circle, spiral.
  - Tremor: frequency- and amplitude-modulated (Ornstein–Uhlenbeck) elliptical oscillation with harmonics and bursts.
- **Seeds.** Estimator parameters are tuned on seeds 100–105 only (`sim/tune_estimators.py`), then frozen (`results/sim/estimator_selection.json`). All reported comparisons use test seeds 200–211.
- **Metrics.** Defined in `docs/physics.md` §8: residual ratio against the powered-neutral pen, distortion without tremor, device distortion against a rigid pen, and the oracle bound.

## 3. Results and the decisions they support

### 3.1 Load and holding power → DEC-003, DEC-008

- The static hold matches the analytic transverse load N cos θ: 0.820 / 0.639 / 0.253 N at 35° / 50° / 75° for N = 1 N.
- Copper loss is 0.81 / 0.49 / 0.08 W.
- Across the 160-sample Monte Carlo, neutral copper loss has median 0.18 W and p90 1.0 W. Rank correlation with normal force is ρ = 0.89 (`mc_sensitivity.json`).

**Normal force, not tremor, sets the heat.** This supports the lever (B) for research and the skid and bias variants (D/E) as product candidates.

### 3.2 What assistance achieves in free writing → DEC-009, DEC-016, COR-11

Grid: 12 test seeds × 9 frequencies × 3 amplitudes (0.15/0.3/0.6 mm peak). Values are the mean residual ratio against the powered-neutral pen (`results/sim/sweeps/summary.json`, `fig_ratio_vs_frequency.png`). In v0.4.2 the balanced and assertive tuning objectives select the same Kalman set, so the two profiles share one row (see "Estimator selection is fragile" below).

| Tremor frequency (Hz) | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| Oracle (mechanical bound) | 0.24 | 0.22 | 0.23 | 0.23 | 0.26 | 0.27 | 0.29 | 0.30 | 0.32 |
| Kalman (both profiles) | 1.14 | 1.10 | 1.07 | 1.07 | 1.08 | 1.03 | 0.97 | 0.90 | 0.85 |
| Band-pass | 1.49 | 1.45 | 1.32 | 1.12 | 0.86 | 0.75 | 0.87 | 1.01 | 1.10 |

The Kalman mean hides a strong amplitude dependence (`results/sim/sweeps/grid.csv`, mean over 12 seeds per cell):

| Kalman, tremor peak | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| 0.15 mm | 1.31 | 1.25 | 1.20 | 1.27 | 1.51 | 1.51 | 1.38 | 1.20 | 1.03 |
| 0.3 mm | 1.10 | 1.06 | 1.02 | 0.99 | 0.90 | 0.78 | 0.71 | 0.65 | 0.63 |
| 0.6 mm | 1.03 | 1.01 | 1.00 | 0.97 | 0.82 | 0.79 | 0.82 | 0.86 | 0.89 |

Small tremor is made worse at every frequency. At 0.15 mm the neutral pen's error is only 102–238 µm, the same order as the Kalman's false corrections of intended writing. Distortion of intended writing without tremor: Kalman 101 µm, band-pass 168 µm RMS (grid seeds). At the nominal case (0.3 mm, 4 seeds), the Kalman reaches 0.705 at 9 Hz with 55 µm distortion and the oracle 0.18–0.23 (`results/sim/nominal/metrics.json`). The distortion depends on the seeds (55 µm on 4, 101 µm on 12) because the frequency gate opens over whole segments.

**Conclusion.** The mechanism could remove 70–80 % of tremor-induced ink error. Averaged over amplitude, none of the causal estimators tested separates tremor from intended writing below ~9 Hz, where most essential tremor lies. They add error there. At 0.3 mm the Kalman breaks even at ~7 Hz; at 0.15 mm it never helps.

- The limit is **intent separation, not actuation or latency**: the prediction horizon is 1.33 ms, and delay alone would leave 0.07 at 8 Hz.
- These are synthetic-writing results. Real handwriting (EXP-H01 recordings) could be more or less separable, which is why EXP-E01 is decision-critical.
- Assistance for free writing is therefore **not** claimed. Guided tasks (§3.3) are the credible near-term use.

**Estimator selection is fragile (DEC-009).** The tuning (`sim/tune_estimators.py`, seeds 100–105) picks the Kalman set with the best balanced objective J (ratio plus a distortion penalty). The v0.4.2 plant changes (pivot stiffness 150 → 80 N/m and coil thermal resistance 60 → 130 K/W, made together) flipped that choice between two sets, both with a 7.5 Hz gate:

- the **inert** set: q_j = 10, q_t = 3×10⁻⁹;
- the **active** set: q_j = 0.1, q_t = 10⁻⁸ (the v0.4.1 assertive choice).

| Parameters | Inert set: J (ratio, distortion) | Active set: J (ratio, distortion) | Balanced choice |
|---|---|---|---|
| v0.4.1 | **1.123** (1.00, 38 µm) | 1.157 (0.89, 83 µm) | inert |
| v0.4.2 | 1.204 (1.00, 62 µm) | **1.151** (0.89, 81 µm) | active (grid row above) |

How the inert set behaves:

- Its intent model absorbs the tremor, the oscillator frequency stays at its 7 Hz prior and the gate stays closed.
- In v0.4.1 the ink trace for seed 200 at 9 Hz was byte-identical to the neutral pen's.
- Its tremor-free false correction was 4–81 µm per seed.

The flip came from the inert set's false corrections, which rose from 38 to 62 µm on the tuning seeds with the plant change; the active set's score hardly moved. About 3–5 % of the objective separates "do almost nothing" from "correct actively". The same fragility appeared earlier: filtering the contact feedforward moved the tuning-seed distortion between 5 and 45 µm. Both findings match the separability limit: on synthetic writing no setting of this estimator is both useful and harmless.

**The gate cannot tell writing from tremor.** Fraction of in-contact time with applied authority g ≥ 0.5 (the research-frame field g), seeds 200–203, θ 50°, N 1 N, 0.3 mm tremor (`sim/diag_gate.py` → `results/sim/gate_fraction.json`). AC-B09-15 asks for ≥ 0.9 with 9–10 Hz tremor and ≤ 0.05 without tremor.

| Kalman set (plant v0.4.2) | 9 Hz tremor | 10 Hz tremor | 6 Hz tremor (below gate) | No tremor: handwriting | No tremor: feature course |
|---|---|---|---|---|---|
| Selected (active) | 0.94 | 0.93 | 0.12 | 0.15 (0–0.32 per seed) | 0.52 |
| v0.4.1 inert set, for reference | 0.31 | 0.29 | 0.41 | 0.51 | 0.74 |

The active set tracks the tremor frequency (median 9.1 and 10.0 Hz) and opens its gate for it. It also opens on 15 % of tremor-free handwriting and half of the feature course, where the tracker locks onto strokes (median 8.2 Hz on the feature course). That is where the 55–101 µm distortion comes from. The inert set's gate opens more often on writing than on tremor. Two consequences follow:

- The gate should not be driven by the estimator's own tracker. The next controller revision (DEC-009 revisit) uses a separate spectral detector with hysteresis and confidence weighting.
- EXP-E01 must report whether each estimator's selection is stable across plants and writers, not only its score.

The ML workstream's frozen-controller rows labelled "assertive" (`ml/README.md`, parameters v0.4.1) used this same set, so they apply to the current controller.

### 3.3 Guided (template) mode → features

Path distance to the template, RMS, 6 Hz / 0.3 mm tremor, 4 seeds (`results/sim/guided_path_distance.json`):

| Feature | Neutral | Guided | Kalman |
|---|---|---|---|
| Circle | 443 µm | 164 µm | 437 µm |
| Spiral | 382 µm | 112 µm | 383 µm |
| Fast stroke | 115 µm | 33 µm | 111 µm |
| Dots | 153 µm | 101 µm | 127 µm |
| Corners | 228 µm | 187 µm | 225 µm |
| Hatching | 141 µm | 129 µm | 132 µm |

When the intended shape is known, the stage removes most of the tremor.

### 3.4 Axial path and Jacobian → DEC-006, COR-04

`results/sim/design_sweeps.json`, `fig_axial_sweep.png`; oracle controller, 9 Hz, 4 tuning seeds.

| k_ax (N/m) | 300 | 700 | 1000 | 2000 | 4000 | 8000 |
|---|---|---|---|---|---|---|
| Device distortion vs rigid pen (µm) | 68 | 87 | 82 | 59 | 53 | 53 |
| Normal-force modulation, oracle (mN RMS) | 91 | 95 | 107 | 128 | 138 | 140 |
| Oracle ratio | 0.27 | 0.16 | 0.13 | 0.13 | 0.15 | 0.17 |

The compliance-aware Jacobian (γ from compliances) against the textbook 1/sin θ gives oracle ratios of:

- 0.27 vs 0.48 at 35°;
- 0.13 vs 0.26 at 50°;
- 0.09 vs 0.13 at 65°.

### 3.5 Suspension placement → DEC-007 (revised)

Refill sliding in the carrier (κ_s = 1, 0.6 g) against the whole lever sliding (κ_s = 0, 1.2 g); `results/sim/kappa_compare.json`:

- device distortion 60.7 vs 61.3 µm (35°) and 59.3 vs 59.3 µm (50°);
- oracle ratio 0.27 vs 0.31 and 0.13 vs 0.13;
- Kalman 0.83 vs 0.78 and 0.73 vs 0.72.

The two layouts are equivalent in the dynamics. The tolerance stack decides the choice (`mechanics/README.md`). Reducing the tip travel from 0.65 to 0.60 mm (Rev A.1) leaves the oracle ratios unchanged (0.27 / 0.13). The oracle's time on the stops rises from 0.01 % to 0.4 % at 35° and 0.16 % at 50°.

### 3.6 Contact feedforward instability → DEC-011

- **Finding.** The Monte Carlo exposed nib bounce caused by the measured-force contact feedforward. Mechanism: `docs/physics.md` P-24. Diagnosis: `results/sim/ff_chatter.json`, `ff_options.json`.
- **Worst cases.** In six low-altitude samples with tremor, 2nd-order 60 Hz filtering still bounced (140–2539 contact transitions in 5 s). Without the feedforward there were 4–13, the same as a rigid pen with lifts.
- **Cost of removal.** Servo error 19.4 → 28.0 µm and device distortion 52 → 59 µm; the oracle ratio at 9 Hz improves, 0.18 → 0.13 (tuning seeds).
- **Partial recovery.** Doubling the servo's integral corner (0.2 → 0.4 of the position bandwidth) without the feedforward brings the servo error to 17.6 µm and device distortion to 53 µm. One worst case then rose to 35 transitions, against a rigid-pen range of 4–18, so it is not adopted before EXP-B05 measures the stage.
- **After the fix.** 0/160 Monte Carlo samples bounce; neutral contact transitions have p90 2.6/s (pen lifts).

### 3.7 Uncertainty → research priorities

Monte Carlo: 160 samples over the declared parameter ranges at 9 Hz and 0.3 mm (`monte_carlo.csv`, `mc_sensitivity.json`, `fig_mc_sensitivity.png`). Results:

- oracle ratio median 0.46 (p10 0.11, p90 1.00);
- Kalman median 0.91 (p10 0.59, p90 1.53);
- coil temperature p90 44 °C in 5 s runs (coil-to-structure 130 K/W in v0.4.2; the v0.4.3 value of 145 K/W adds 0.2–0.3 K);
- voltage saturation p90 9 % of contact time.

Strongest rank correlations:

| Outcome | Parameters (ρ) |
|---|---|
| Oracle ratio | altitude (−0.45), normal force (−0.33), friction (+0.23), arm stiffness (−0.22) |
| Kalman ratio | **friction (+0.51)**, optical noise (+0.22), grip stiffness (−0.21) |
| Copper loss | normal force (+0.89), K_f (−0.29), altitude (−0.26) |

Friction's effect on estimator performance raises the priority of EXP-B02 (friction vs speed and paper) and EXP-B01.

### 3.8 Failure cases → DEC-015

`results/sim/sweeps/summary.json`, 9 Hz tremor, Kalman; reference residual 302 µm.

| Case | Result | Firmware rule |
|---|---|---|
| F1: optical dropout 0.3 s | Authority falls to 0.002 within the dropout and recovers to 0.99 after 1 s; residual 329 µm | Confidence fade (implemented) |
| F2: low battery (3.3 / 3.0 / 2.8 V) | Voltage saturation 11 / 18 / 24 % of contact time | Derate below 3.3 V |
| F3: coil power lost in contact | **Ink jumps up to 0.79 mm within 50 ms** | Never de-energise in contact except on hard faults |
| F4: Hall sensor frozen | 0.56 mm jump; stage on its stop 99.97 % of the time; 0.55 A | Detect within 5 ms, hold open-loop |
| F5: overload (2 N at 35°) | Stops 97 % of the time; 1.55 W; coil 59 °C after 6 s. Extrapolated with the same one-node model (0.25 J/K, copper tempco), the 120 °C coil limit is reached in ≈ 18 s at 130 K/W and ≈ 17 s at the v0.4.3 value of 145 K/W (calculation) | Thermal derate |
| F6: stage blocked at 0.1 mm | Residual 412 µm; current at 0.56 A | Stop and residual detection |
| F7: optical noise ×10 (30 µm) | Residual 433 µm | Confidence (NIS) derate |

## 4. Limitations

- **Synthetic writing and tremor.** Real separability may differ in either direction.
- **Hand model.** Literature values, measured in-plane and without the hand resting on paper. γ and the normal impedance are assumed.
- **Contact model.** Paper is a lumped spring–damper with LuGre friction; there is no roughness, ink film or refill-specific drag.
- **Rigid lever.** No flexure nonlinearity or parasitic modes above the stage resonance. The actuator is a constant K_f with a map crosstalk term (the field model shows 37 % K_f variation over the stroke; to be calibrated).
- **Sensors.** Delay, white noise, simple dropout. Optical accuracy on paper at the nib is unknown (EXP-S01).
- **Evaluation.** Ink error is the error of the simulated ball path; ink deposition and line width are not modelled.
- **Found by the firmware review** (`firmware/README.md` D9, D10):
  - *Current loop.* The simulator applies R·i_ref feedforward plus PI with no sample-to-PWM delay. With the Rev A delay (47.5 µs) the same law overshoots 55 %, so the firmware uses PI only (13 % overshoot, 125 µs rise). The current loop is about 30 times faster than the stage loop, so stage-level results should change little; a re-run with the delayed PI loop would confirm it.
  - *Band-pass reference estimator.* It re-initialises on absolute page position, which gives transients of up to 10.6 mm at optical re-acquisition. The stage command is clipped at q_lim, but the band-pass figures (ratio and 168 µm distortion) may be inflated by them. The firmware's local-origin option cuts the transient to 0.27 mm. The band-pass is a reference, not a candidate controller.

## 5. Reproduce

```bash
python3 -m pytest sim/tests -q    # 12 verification tests
bash sim/run_all.sh               # full evidence chain, logs in results/sim/*.log
```

Every JSON output carries provenance: git revision, parameter-file version and digest, seeds, command, library versions.
