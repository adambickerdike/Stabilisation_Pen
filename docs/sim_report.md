# Simulation report — model M1, parameters v0.4.1

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

Grid: 12 test seeds × 9 frequencies × 3 amplitudes (0.15/0.3/0.6 mm peak). Values are the mean residual ratio against the powered-neutral pen (`results/sim/sweeps/summary.json`, `fig_ratio_vs_frequency.png`).

| Tremor frequency (Hz) | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| Oracle (mechanical bound) | 0.24 | 0.22 | 0.23 | 0.23 | 0.26 | 0.27 | 0.29 | 0.30 | 0.32 |
| Kalman, balanced | 1.07 | 1.05 | 1.05 | 1.01 | 1.02 | 0.99 | 0.96 | 0.97 | 0.99 |
| Kalman, assertive | 1.15 | 1.10 | 1.06 | 1.09 | 1.08 | 1.04 | 0.96 | 0.91 | 0.85 |
| Band-pass | 1.49 | 1.45 | 1.32 | 1.12 | 0.86 | 0.76 | 0.87 | 1.01 | 1.10 |

Distortion of intended writing without tremor: Kalman balanced 62 µm, assertive 97 µm, band-pass 168 µm RMS. At the nominal case (0.3 mm, 4 seeds), the assertive Kalman reaches 0.72 at 9 Hz and the oracle 0.18–0.23 (`results/sim/nominal/metrics.json`).

**Conclusion.** The mechanism could remove 70–80 % of tremor-induced ink error. None of the causal estimators tested separates tremor from intended writing below ~9 Hz, where most essential tremor lies. They add error there.

- The limit is **intent separation, not actuation or latency**: the prediction horizon is 1.33 ms, and delay alone would leave 0.07 at 8 Hz.
- These are synthetic-writing results. Real handwriting (EXP-H01 recordings) could be more or less separable, which is why EXP-E01 is decision-critical.
- Assistance for free writing is therefore **not** claimed. Guided tasks (§3.3) are the credible near-term use.

**Frequency-gate fragility.** Small plant changes (for example, filtering the contact feedforward) moved balanced-Kalman distortion between 5 and 45 µm on the same tuning seeds, because the gate opens or closes over whole segments. A hysteretic, confidence-weighted gate is future work.

**The "balanced" Kalman profile is effectively inert against tremor.** The mechanism, found by the app and ML workstreams and confirmed here:

1. Its intent model (q_j = 10) absorbs the tremor as intended motion.
2. The oscillator's frequency estimate therefore stays near its 7 Hz prior.
3. The 7.5 Hz gate stays closed with tremor present. For seed 200 at 9 Hz, the ink trace is byte-identical to the neutral pen (`results/sim/nominal/traces_kf_bal.npz` = `traces_neutral.npz`).
4. On tremor-free writing, the tracker occasionally crosses the gate, giving 4–81 µm of false correction.

The tuning objective selected "do almost nothing" as the best balance on synthetic writing, which is itself evidence for the separability limit. The gate should not be driven by the estimator's own tracker: a separate spectral detector with hysteresis is the next controller revision (DEC-009 revisit).

### 3.3 Guided (template) mode → features

Path distance to the template, RMS, 6 Hz / 0.3 mm tremor, 4 seeds (`results/sim/guided_path_distance.json`):

| Feature | Neutral | Guided | Kalman assertive |
|---|---|---|---|
| Circle | 442 µm | 165 µm | 438 µm |
| Spiral | 382 µm | 111 µm | 383 µm |
| Fast stroke | 115 µm | 34 µm | 111 µm |
| Dots | 153 µm | 101 µm | 127 µm |
| Corners | 228 µm | 187 µm | 225 µm |
| Hatching | 141 µm | 130 µm | 132 µm |

When the intended shape is known, the stage removes most of the tremor.

### 3.4 Axial path and Jacobian → DEC-006, COR-04

`results/sim/design_sweeps.json`, `fig_axial_sweep.png`; oracle controller, 9 Hz, 4 tuning seeds.

| k_ax (N/m) | 300 | 700 | 1000 | 2000 | 4000 | 8000 |
|---|---|---|---|---|---|---|
| Device distortion vs rigid pen (µm) | 69 | 87 | 83 | 59 | 53 | 53 |
| Normal-force modulation, oracle (mN RMS) | 91 | 95 | 107 | 127 | 137 | 138 |
| Oracle ratio | 0.27 | 0.16 | 0.13 | 0.13 | 0.15 | 0.17 |

The compliance-aware Jacobian (γ from compliances) against the textbook 1/sin θ gives oracle ratios of:

- 0.27 vs 0.48 at 35°;
- 0.13 vs 0.26 at 50°;
- 0.09 vs 0.13 at 65°.

### 3.5 Suspension placement → DEC-007 (revised)

Refill sliding in the carrier (κ_s = 1, 0.6 g) against the whole lever sliding (κ_s = 0, 1.2 g); `results/sim/kappa_compare.json`:

- device distortion 60.6 vs 61.0 µm (35°) and 59.2 vs 59.3 µm (50°);
- oracle ratio 0.27 vs 0.31 and 0.13 vs 0.13;
- assertive Kalman 0.83 vs 0.78 and 0.74 vs 0.73.

The two layouts are equivalent in the dynamics. The tolerance stack decides the choice (`mechanics/README.md`).

### 3.6 Contact feedforward instability → DEC-011

- **Finding.** The Monte Carlo exposed nib bounce caused by the measured-force contact feedforward. Mechanism: `docs/physics.md` P-24. Diagnosis: `results/sim/ff_chatter.json`, `ff_options.json`.
- **Worst cases.** In six low-altitude samples with tremor, 2nd-order 60 Hz filtering still bounced (138–2539 contact transitions in 5 s). Without the feedforward there were 4–13, the same as a rigid pen with lifts.
- **Cost of removal.** Servo error 19.7 → 28.7 µm, device distortion 51 → 59 µm, oracle ratio 0.18 → 0.13 at 9 Hz (tuning seeds).
- **After the fix.** 0/160 Monte Carlo samples bounce; neutral contact transitions have p90 2.6/s (pen lifts).

### 3.7 Uncertainty → research priorities

Monte Carlo: 160 samples over the declared parameter ranges at 9 Hz and 0.3 mm (`monte_carlo.csv`, `mc_sensitivity.json`, `fig_mc_sensitivity.png`). Results:

- oracle ratio median 0.45 (p10 0.11, p90 1.00);
- assertive Kalman median 0.91 (p10 0.59, p90 1.52);
- coil temperature p90 42 °C in 5 s runs;
- voltage saturation p90 7 % of contact time.

Strongest rank correlations:

| Outcome | Parameters (ρ) |
|---|---|
| Oracle ratio | altitude (−0.44), normal force (−0.34), friction (+0.24), arm stiffness (−0.22) |
| Kalman ratio | **friction (+0.52)**, grip stiffness (−0.22), optical noise (+0.22) |
| Copper loss | normal force (+0.89), K_f (−0.29), altitude (−0.26) |

Friction's effect on estimator performance raises the priority of EXP-B02 (friction vs speed and paper) and EXP-B01.

### 3.8 Failure cases → DEC-015

`results/sim/sweeps/summary.json`, 9 Hz tremor, assertive Kalman; reference residual 302 µm.

| Case | Result | Firmware rule |
|---|---|---|
| F1: optical dropout 0.3 s | Authority falls to 0.002 within the dropout and recovers to 0.99 after 1 s; residual 330 µm | Confidence fade (implemented) |
| F2: low battery (3.3 / 3.0 / 2.8 V) | Voltage saturation 11 / 18 / 25 % of contact time | Derate below 3.3 V |
| F3: coil power lost in contact | **Ink jumps up to 0.78 mm within 50 ms** | Never de-energise in contact except on hard faults |
| F4: Hall sensor frozen | 0.56 mm jump; stage on its stop 99.9 % of the time; 0.56 A | Detect within 5 ms, hold open-loop |
| F5: overload (2 N at 35°) | Stops 96 % of the time; 1.56 W; coil 55 °C after 6 s | Thermal derate |
| F6: stage blocked at 0.1 mm | Residual 414 µm; current at 0.55 A | Stop and residual detection |
| F7: optical noise ×10 (30 µm) | Residual 433 µm | Confidence (NIS) derate |

## 4. Limitations

- **Synthetic writing and tremor.** Real separability may differ in either direction.
- **Hand model.** Literature values, measured in-plane and without the hand resting on paper. γ and the normal impedance are assumed.
- **Contact model.** Paper is a lumped spring–damper with LuGre friction; there is no roughness, ink film or refill-specific drag.
- **Rigid lever.** No flexure nonlinearity or parasitic modes above the stage resonance. The actuator is a constant K_f with a map crosstalk term (the field model shows 37 % K_f variation over the stroke; to be calibrated).
- **Sensors.** Delay, white noise, simple dropout. Optical accuracy on paper at the nib is unknown (EXP-S01).
- **Evaluation.** Ink error is the error of the simulated ball path; ink deposition and line width are not modelled.

## 5. Reproduce

```bash
python3 -m pytest sim/tests -q    # 12 verification tests
bash sim/run_all.sh               # full evidence chain, logs in results/sim/*.log
```

Every JSON output carries provenance: git revision, parameter-file version and digest, seeds, command, library versions.
