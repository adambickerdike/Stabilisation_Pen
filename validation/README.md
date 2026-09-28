# Validation plan

**Status (2026-09-27): PROPOSED. No experiment or study has been executed, no participant enrolled, no bench record exists.** Everything in this directory is one of three things:

- a proposed procedure;
- a prediction copied from `results/` with its source;
- an acceptance criterion whose number states its origin: a requirement id, a literature evidence id, a simulation or calculation file, or "engineering judgement".

Executed results will live only in [`records/`](records/README.md).

## 1. Files

| File | Content |
|---|---|
| [`bench_protocols.md`](bench_protocols.md) | 34 bench and offline protocols: EXP-B01…B10, S01–S02, F01–F02, M02–M03, P01–P02, E01–E02, C01–C02, A01, A03, the pencil-class Q01–Q08, and I01 and I04 from the inertial study (§35–§36) (§0.11 holds the pencil conventions; the A03 and Q sections are compact: purpose and gates, set-up, procedure, measurands with uncertainty, criteria, decision rule). Each of the others gives purpose and gated decisions, hypotheses with predictions, equipment classes and required accuracy, setup, procedure, sample size, data format, analysis and metric definitions, acceptance criteria, what result changes which decision, and risks. §0 holds the shared conventions: pre-registration, synchronisation, metrology and decision rules, randomisation and blinding, sample-size rules, the metric definitions that mirror `docs/physics.md` §8 and `sim/pensim/evaluate.py`, and the shared rigs R1–R8. |
| [`human_study_plan.md`](human_study_plan.md) | EXP-H01…H06: tremor-at-nib census, form factor, skid feel, training with retention and transfer, perception thresholds, and the immediate-assistance crossover. §12: EXP-A02, guidance acceptance with people (pencil concept). §13–§14: EXP-I02 (rotational share of writing tremor) and EXP-I03 (passive nose and grip options). The **immediate assistance vs lasting improvement** separation is central (§1). Also covers populations, randomisation, blinding, outcomes, step-by-step sample sizes, analysis plans, adverse events and stopping rules, and ethics, regulatory and data-protection notes. |
| [`acceptance_criteria.csv`](acceptance_criteria.csv) | **Source of truth** for all criteria: 272 rows, 43 experiments. Columns: `id, requirement_id, experiment_id, metric, threshold, direction, basis, status, decision_gated`. |
| [`prototype_stages.md`](prototype_stages.md) | Stages A (bench rig with commercial actuators), B (tethered Rev A pen), C (untethered pen), D (product-form candidates, DEC-008). Gates G-A, G-B, G-S (safety before any participant), G-C, G-D and the claim gates C-IA, C-LI, C-CAP, each defined by criterion ids. Also: what each stage may and may not claim, a mermaid dependency graph, and the mapping to the phases of `docs/plan.md`. |
| [`records/README.md`](records/README.md) | How executed records are stored: layout, naming, mandatory `record.yaml` metadata, write-once raw data with SHA-256 manifests, verdict files, retention, human-data rules. |
| [`check_criteria.py`](check_criteria.py) | Checks the CSV (unique ids, requirement ids exist in `docs/requirements.csv`, status and direction vocabulary, coverage) and regenerates the criteria tables embedded in the two protocol documents. Edit the CSV, then run `python3 validation/check_criteria.py`; add `--check` to only check. |

## 2. Conventions

- **Experiment ids:**
  - EXP-Bnn: bench physics;
  - EXP-Snn: sensing and capture;
  - EXP-Fnn: faults;
  - EXP-Mnn: mechanics. M01 is unused, because the brief's list starts at M02;
  - EXP-Pnn: power;
  - EXP-Enn: estimation;
  - EXP-Cnn: capture and recognition;
  - EXP-Ann: AI;
  - EXP-Qnn: pencil-class concept (Rev P0) components and stages;
  - EXP-Hnn: human studies.

  The ids used in `docs/` for B01–B10, S01, S02, M02, M03, E01, E02, H01–H05 are kept. EXP-H06 is the immediate-assistance crossover that `docs/features.md` calls "immediate-assistance crossover study".
- **Criterion ids:** `AC-<exp>-<nn>`, for example AC-B09-02.
- **`status`:**

  | Status | Meaning | Rows |
  |---|---|---|
  | `requirement` | The threshold is copied from `docs/requirements.csv`; `requirement_id` is set | 86 |
  | `derived` | The threshold is computed from a requirement, literature value, simulation result or design rule (ICD, decision log), or chosen to protect another criterion (metrology qualification). The derivation is in `basis` | 40 |
  | `hypothesis` | A prediction or proposed pass line about the device or the world, often engineering judgement, that the experiment tests. Thresholds taken from twin experiments (`sim_to_real.md`) say in `basis` that they are proposed design values, not measurements | 146 |

- **`direction`:** `<=`, `>=`, `<`, `>`, `=`, `within` (inclusive interval) or `pass/fail` (a conformity check described in `metric`).
- **Decision rules:** simple acceptance when TUR ≥ 4, otherwise guarded acceptance. Safety criteria always use guarded acceptance (`bench_protocols.md` §0.5).
- **Predictions are indicative until frozen.** Result files carry mixed parameter versions (EM 0.2.0; mechanics, CAD and ML 0.4.1; simulation, trade, thermal and drive calculations 0.4.4). Before each experiment the predictions are regenerated with the as-built parameters and frozen (`bench_protocols.md` §0.2).

## 3. Coverage

- **Experiments:** 43 (34 bench or offline, 9 human-participant).
- **Criteria:** 272.
- **Requirements:** all 61 requirements in `docs/requirements.csv` have at least one criterion, including REQ-PNC-001…008.
- **Model validation:** the physics.md model-validation table is covered for every model:
  - P-1…P-4: AC-B04-05, AC-B06-03;
  - P-5…P-9: AC-B01-03, AC-B02-01, AC-B02-04, AC-B02-05;
  - P-10…P-12: AC-B05-01, AC-B05-03, AC-B05-15;
  - P-13: AC-B06-01;
  - P-14…P-16: AC-B03-01, AC-B03-04;
  - P-18: AC-B07-04, AC-B07-05;
  - P-19…P-24: AC-B09-03, with AC-B09-16…18.
- **Decision revisit triggers:** every trigger in `docs/decisions.md` that names an experiment has a protocol:
  - DEC-003: B01, B03;
  - DEC-004: B08;
  - DEC-005: S01;
  - DEC-006: B06, B08;
  - DEC-007: M02, B03;
  - DEC-008: H03;
  - DEC-009: E01;
  - DEC-010: F02;
  - DEC-011: B05 (chatter on paper stacks);
  - DEC-012: B03;
  - DEC-013: C01;
  - DEC-015: F01, F02;
  - DEC-016: E01, E02;
  - DEC-018: H02 (visibility of the writing point);
  - DEC-019: Q02, Q04, Q06, Q07, H03;
  - DEC-020: A02, A03;
  - DEC-021: S01 (AC-S01-08);
  - DEC-022: Q08;
  - DEC-023: B03, B05, B01/B02 through `s2r`, judged in B09 (AC-B09-03, -16…18).

## 4. The three most decision-critical experiments

1. **EXP-H01 tremor-at-nib census, with its analysis EXP-E01.**
   - It decides whether free-writing tremor cancellation helps a meaningful population at all. It measures amplitude against the ±0.5 mm stage (REQ-USR-002) and frequency against the 7.5 Hz gate (DEC-009) at the nib.
   - E01 then tests causal separability on real writing.
   - Today's evidence: about 30 % of ET within 1 mm p-p (PDT-12, spirals); ET frequency 5.8 ± 1.3 Hz (about 10 % above the gate); no causal separation below about 9 Hz in simulation. Together these suggest only a few percent of ET patients may be addressable by free-writing cancellation.
   - It needs no active hardware and has the longest lead time (ethics).
2. **EXP-B01 refill drag and reaction map.**
   - The transverse load enters holding power squared. It decides configuration B vs D/E (DEC-003, DEC-008) and REQ-ACT-001, and fixes the friction parameters that dominate simulated estimator performance (`results/sim/mc_sensitivity.json`, ρ = 0.52).
   - It is cheap and early, and every later bench prediction depends on it.
3. **EXP-B09 bench cancellation with injected disturbance and µm ink metrology.**
   - It is the first physical test of loaded cancellation at practical force. There is no published precedent for an actuated nib in contact (ACT notes).
   - It validates the control and contact models that all simulation-based decisions rest on.
   - It gates the Rev A build (G-B), and in its guided-mode part the credible near-term use.

## 5. Criteria predicted to fail by calculation

Stating these in advance keeps the plan honest. Each will be measured, not assumed.

| Criterion | Why it is expected to fail |
|---|---|
| AC-B03-03 (K_m ≥ 0.37 N/√W for REQ-ACT-002) | Predicted K_m 0.293 N/√W |
| AC-P01-02 (REQ-ACT-002 ≤ 0.25 W) | Predicted 0.33 W average copper loss (configuration B, 65 % pen-down) |
| AC-B03-10 (REQ-ACT-001: 0.75 N continuous) | Needs 0.65 W referenced to 20 °C (0.85 W at the 96.6 °C design coil) against 0.412 W allowable |
| AC-B03-11 (REQ-ACT-001: 1.4 N for 2 s) | Needs 0.62 A per axis against a 0.45 A or 0.60 A clamp |
| AC-B04-04 (REQ-MECH-001) | Page disc of 0.5 mm unreachable in the tilt direction below θ ≈ 56° with q_lim 0.55 mm and K_n 800 N/m |
| AC-B05-02 (REQ-MECH-003) | m_eq 13.7 g against ≤ 12 g |
| AC-P01-01 (REQ-PWR-001) | About 53 min with the cell that fits the Rev A.1 bay, against ≥ 60 min (81 min with a 200 mAh cell) |
| AC-M03-02 (REQ-FORM-004) | CoM 76–81 mm against ≤ 70 mm |
| AC-B09-05 (REQ-CTRL-007) | Kalman 1.10 / 1.06 of neutral error at 4 / 5 Hz against ≤ 1.05 (grid at 0.3 mm, v0.4.4) |
| AC-B09-06 (REQ-CTRL-005) | 55–100 µm distortion predicted against 50 µm (v0.4.4; was marginal at 57–62 µm with the v0.4.1 inert set) |
| AC-B09-07 (REQ-CTRL-005) | Corner error 208 µm max against 100 µm |
| AC-B09-15 (b) | Gate open on 14 % of tremor-free handwriting and 68 % of the feature course against ≤ 5 % (`results/sim/gate_fraction.json`). In v0.4.1 part (a) was the predicted failure (inert set); `docs/sim_report.md` §3.2 |
| AC-C02-08, AC-S02-06 | The ICD lacks the uncertainty and nib-offset fields |
| AC-E01-08 (REQ-ML-001: no spikes > 100 µm) | The synthetic TCN shows 125 µm corner spikes (REQ-CTRL-005 current estimate) |
| AC-B04-03, AC-B05-12, AC-F01-03/04, AC-F02-05 (class 5) | Requirement text conflicts with the design (§6). AC-F02-01 is also flagged, but 40 kHz meets "≥ 20 kHz" |
| AC-Q07-01 (REQ-PNC-003, pencil) | Loaded stroke ±277 µm at 50°, ±162 µm at −20 % part tolerance and ±48 µm at 35°, against ±0.30 mm. The ±0.30 mm needs F_c ≤ 0.14 N at 50°, below the 0.15 N design value (EXP-Q02) |
| AC-Q08-01 (REQ-PNC-006) without the feed-forward | Tail ink 0.11 mm per stroke at 50° and 0.14 mm at 35° with the adaptive stop alone, against 0.1 mm. With the touchdown feed-forward (DEC-026) it is predicted to pass (0.005–0.008 mm; SIM, `results/opt/touchdown.json`) |
| AC-Q08-06 and AC-Q08-07 at 35° (feed-forward) | 21 touchdowns against the rigid pen's 18 (re-contacts after lift-off); the oracle ratio rises by 0.03 with the P0.1.2 servo (0.354 with the DEC-027 servo) (SIM) |
| AC-Q05-01 and AC-P01-05 with 2 × DRV2700 | 255 mW of drive power against a 68 mW budget; 0.83 h of assist against 2 h. A charge-recovery driver is predicted to pass (32 mW, 2.7 h) |
| AC-A02-02 (tremor groups), AC-A02-03 | A personal template lies about 300 µm from intent, beyond the 265 µm break-even; AI templates gave no net legibility gain (SIM, synthetic writers) |
| AC-A02-04 | Template error in the tremor band 165 µm for correctly predicted letters in the writer's style, against ≤ 50 µm (SIM, `results/fusion/context.json`) |
| AC-I03-01 | No modelled passive nose or grip option improved the net error against the intended writing (0.93–1.25 of the unmodified pencil; SIM, `results/pencil/inertial.json`); hand resting is not modelled |

## 6. Issues found in existing documents (for the project lead)

This list was checked against the repository on 2026-09-27, while other workstreams were still editing. Nothing outside `validation/` was changed. File:field references are given so each item can be fixed directly.

### 6.1 Requirement text conflicts with the design or with other requirements

1. **REQ-SAF-002.** The text says a 0.45 A software limit and a 0.6 A hardware trip. The design uses 0.60 A and ±0.80 A: `config/parameters.yaml` `actuator.i_max`/`i_trip`, `electronics/README.md`, `electronics/gen/design_revA.py`, and the requirement's own `current_estimate`.
2. **REQ-ACT-001 vs REQ-SAF-002 and the thermal limit.**
   - "≥ 1.4 N for 2 s" needs 1.4 / (3.17 × 0.717) = **0.62 A** on one axis, above both current clamps.
   - "0.75 N continuously" needs about **0.65 W (20 °C) to 0.82 W (85 °C)** of copper loss at K_m 0.293 N/√W. The moving-coil allowable is 0.455 W (`results/thermal/thermal.json`) and REQ-ACT-002 allows 0.25 W. *(v0.4.3: 0.412 W allowable with the 0.50 mm gaps; see the resolution log.)* By the repository's own numbers REQ-ACT-001 is infeasible for configuration B, not merely "at risk".
3. **REQ-MECH-002.** The text says "hard stops at 0.65 mm". The design is 0.60 mm (`config` `stage.travel_tip_mech` v0.4.1, DEC-007 rev.); the requirement's own `current_estimate` also says 0.60 mm.
4. **REQ-MECH-001.** "0.5 mm at every altitude 35–75°" is not reachable with q_lim = 0.55 mm.
   - By P-4 with K_n 800 N/m and k_ax 2 kN/m, the tilt-plane stage needs 0.705 / 0.606 / 0.576 / 0.553 mm at 35 / 45 / 50 / 55°.
   - The requirement's own estimate (0.57–0.62 mm) already exceeds q_lim.
   - COR-26 restricts the product envelope to θ ≥ 45°. Restate the altitude range, or change the travel.
5. **REQ-SNS-004** asks for ≥ 4 kHz lever-angle sampling; `docs/icd.md` §2 samples the TMAG5170 at 2 kHz.
6. **REQ-CTRL-001** says "Current regulation 20 kHz"; DEC-012, `docs/icd.md` §2 and `config` `control.f_current` use 40 kHz.
7. **REQ-SAF-003 and REQ-ML-002 vs ICD §5 v1.1.**
   - REQ-SAF-003 requires authority reduction within 20 ms for low-confidence outputs. The v1.1 guard's a-posteriori check uses a 200 ms running RMS.
   - REQ-ML-002 requires an output "with timestamp/expiry/confidence"; the v1.1 output is d̂ (x, y) only.
8. **REQ-CAP-001** requires the measured nib offset and uncertainty in the stroke record; `docs/icd.md` §4.3 (20-byte stroke sample) has neither field. Its `current_estimate` points to `data/schema/stroke_record.schema.json`, which does not exist.
9. **REQ-MECH-004** rationale says "< 30 µm RMS device distortion", but simulation gives 59–75 µm at k_ax 2 kN/m (`results/sim/nominal/metrics.json` per seed; `results/sim/design_sweeps.json` 59.2 µm). COR-05's "64 → 22 µm" is not reproduced by `design_sweeps.json` v0.4.1, which gives 68.7 µm at 300 N/m and 53.0 µm at 8 kN/m.
10. **REQ-CTRL-005** bounds RMS distortion and corner/dot error, but not deliberate high-frequency features. In simulation the balanced Kalman distorts hatching by 93 µm and fast strokes by 122 µm RMS, and the learned TCN has 125 µm corner spikes (REQ-CTRL-005's own estimate). A feature-specific limit is proposed from EXP-H05 (AC-B09-08).

### 6.2 Experiment ids that point to the wrong experiment

Fix these to match the definitions used here and in `docs/physics.md`.

11. **`docs/requirements.csv` `verification`:**

    | Requirement | Current text | Should be |
    |---|---|---|
    | REQ-MECH-002 | "drop test EXP-M03" | EXP-B10 (M03 is mass and CoM) |
    | REQ-MECH-008 | "EXP-B02 refill metrology" | EXP-B01 Part 0 and EXP-B10 (B02 is friction/LuGre, as in physics.md) |
    | REQ-CTRL-005 | "EXP-B10" | EXP-B09, E02, H05 |
    | REQ-PWR-001 | "EXP-P02 measured duty cycle" | EXP-P01 |
    | REQ-PWR-002 | "cell qualification EXP-P01" | EXP-P02 |
    | REQ-CAP-001 | "capture tests EXP-C01" | EXP-C02, S02 |
    | REQ-APP-001 | "recognition evaluation EXP-A01" | EXP-C01 |
    | REQ-APP-002 | no id | EXP-A01 |
    | REQ-SAF-004 | EXP-F02 only | EXP-F01 (power loss in contact) and F02 (brown-out) |
    | REQ-SNS-004 | EXP-B03 only | B03 (crosstalk) and B04 (noise, rate) |
    | REQ-SNS-005 | "bench calibration" | EXP-B05 |
    | REQ-CTRL-002 | "sim/analysis/margins" (does not exist) | EXP-B05 |
    | REQ-ML-002 | "MCU benchmark EXP-E02" | On-target timing is part of EXP-E02 and F02; rename |

12. **`docs/corrections.csv`:**
    - COR-11 `affected_items` "validation EXP-B10" → EXP-B09/E01;
    - COR-14 "cell qualification EXP-P01" → EXP-P02;
    - COR-21 "MCU benchmark EXP-E02" and "ml/deploy" (does not exist).
13. **`config/parameters.yaml`:**
    - `writing.tilt_deg` note "(EXP-B05)" → EXP-H01 (task distribution);
    - `refill.length` and `refill.mass` notes "(EXP-B02)" → EXP-B01 Part 0. The same stale "EXP-B02" appears in comments at `sim/pensim/model.py:39` and `mechanics/cad/pen_revA.py:49`.
14. **`config/parameters.yaml` sources "REQ-ENV-001/002/003"** (`writing.tilt_deg`, `writing.normal_force`, `disturbance.tremor_*`) do not exist in `docs/requirements.csv`.

### 6.3 Correction numbers and equation references

15. **"COR-18" is cited for the 10440 cell's 1C limit** in `config/parameters.yaml` (changelog 0.4.0; `battery.capacity_mAh` source) and in REQ-PWR-002 `current_estimate`. It should be **COR-14**; COR-18 is flexures.
16. **`docs/physics.md` P-23 cites "COR-05"** for the servo-delay residual. In `docs/corrections.csv` that is **COR-07**; COR-05 is the axial suspension. The root cause is that `analysis/audit_recalc.py` and `results/audit/audit_corrections.json` number corrections differently from `docs/corrections.csv`:

    | Key in `audit_corrections.json` | Content | Id in `corrections.csv` |
    |---|---|---|
    | COR-04 | pressure modulation | COR-05 |
    | COR-05 | delay | COR-07 |
    | COR-07 | IMU | COR-08 |
    | COR-08 | runtime | COR-02 |

17. **COR-04 `evidence`** cites "docs/physics.md eq. P-12" for the compliance-aware Jacobian. It is **P-4**; P-12 is flexures.

### 6.4 Numbers stated inconsistently

18. **Oracle (mechanical) bound.** Each quote should carry its conditions (frequency, amplitude, seeds, parameter version).

    | Source | Value |
    |---|---|
    | `docs/audit.md` | about 0.13–0.20 |
    | `docs/research_questions.md` rank 4 | 0.21–0.27 |
    | `docs/research_synthesis.md` §7 | 0.2–0.27 |
    | Nominal simulation, v0.4.1 | 0.18 (6 Hz) / 0.23 (9 Hz) |
    | Grid simulation, v0.4.1 (`docs/sim_report.md`, `docs/features.md`) | means 0.22–0.32 over 4–12 Hz |
    | Design sweep | 0.13 (50°, 9 Hz) |
    | Monte Carlo | median 0.45, p90 1.00 |

19. **Runtime and electronics power.**
    - COR-02 and `results/trade/config_trade.json` give ≈ 96 min with 60 mW of electronics. That is `config` `electrical.p_electronics_active`, whose source "docs/budgets" does not exist.
    - `electronics/README.md` and REQ-PWR-001 give ≈ 55 min with 115 mW (`results/electronics/drive_sense.json`).
    - COR-02's "0.37 W writing average" copper loss includes the 0.06 W of electronics (0.65 × 0.477 + 0.06).
20. **Configuration power figures mix definitions:** DEC-008 "D 0.07 W / E 0.02 W" (in-contact copper); REQ-ACT-002 "D 0.05 W / E 0.01 W" (average copper); `config_trade.json` `avg_power_writing_W` (includes electronics).
21. **`config` `stage.k_tip` = 150 N/m** ("flexure concept"), but the selected gimbal is **75.8 N/m** (`results/mechanics/flexure_calc.json`). COR-06's "19 Hz at 150 N/m" uses the old value; with 75.8 N/m and 13.7 g the open-loop mode is about 11.8 Hz.
22. **`config` `stage.m_eq` = 10.3 g** (point mass) vs **13.7 g** in REQ-MECH-003 and `mechanics/README.md`.
23. **`config` `actuator.Rth_coil_amb` = 60 K/W** (range 30–120 K/W) vs **130 K/W** for the Rev A moving coil (`config_trade.json`; `mechanics/README.md` M-5). The simulator's coil-temperature range excludes the design value.
24. **IMU rate:** `docs/icd.md` §2 gives a 7.68 kHz ODR; `config` `sensing.imu_rate` and `docs/sim_report.md` give 3.84 kHz.
25. **K_m target:** `docs/research_questions.md` rank 9 says ≥ 0.3 N/√W; `docs/plan.md` §3 says ≥ 0.29 N/√W at the 0.50 mm gap. The prediction is 0.293. This plan uses 0.29 (AC-B03-02).

### 6.5 Interface control document (for the ICD owner)

26. **§4.3 φ encoding.** "u8, 0.5°, φ 0–360° as φ/2" cannot be represented: 0–360° at 0.5° needs 720 codes, and φ/2 at 0.5° needs 360. `app/penapp/logfmt.py` chose a 2° LSB. State the encoding explicitly.
27. **Bench records need** an event code for rig synchronisation pulses, and defined payloads for 0x04 (calibration snapshot) and 0x05 (annotation). Until then, bench logs use annotation text `SYNC <n>` (`bench_protocols.md` §0.4).
28. **Stroke record fields** for REQ-CAP-001 (uncertainty, measured nib offset), and **ML output expiry and confidence** for REQ-ML-002 and REQ-SAF-003: items 7 and 8 above.

### 6.6 Referenced files that do not exist

29. The following are cited but absent:

    | Missing file | Cited by |
    |---|---|
    | `docs/budgets.md` | COR-02; `config` `p_electronics_active` |
    | `mechanics/bench_rig` | COR-15. The rig is now `mechanics/cad/bench_rig.py` and `mechanics/README.md` |
    | `data/splits.py` | REQ-DATA-001: "Implemented in data/splits.py". The synthetic writer-disjoint splits are built in `ml/datasets.py` |
    | `data/schema/stroke_record.schema.json` | REQ-CAP-001 |
    | `firmware/src/limiter.c`, `ml_guard.c`, `log_format.c` | REQ-CTRL-004, REQ-SAF-003, REQ-CAP-002. The files exist under `firmware/core/` |
    | `sim/analysis/margins` | REQ-CTRL-002 |
    | `mechanics/mass_model` | `config` `stage.m_couple` |
    | `results/sim/axial_sweep` | `config` `stage.axial_k`. The sweep is in `results/sim/design_sweeps.json` |
    | `ml/model_cards` | COR-11. The model card is `ml/model_card.md` |
    | `ml/deploy` | COR-21. The int8 export and host test are in `ml/export/` |

### 6.7 Planning numbers and naming

30. **`docs/research_questions.md`: "n ≈ 12" for EXP-H03** gives only **56 % power** under this plan's non-inferiority assumptions (σ_D 1.5 points, margin 1.0). n = 20 is needed (`human_study_plan.md` §6).
31. **"n ≈ 20 per group" for EXP-H01** gives a 95 % CI of 18–50 % for the ET fraction ≤ 1 mm p-p, no narrower than the literature range. An adaptive extension to 40 ET is proposed.
32. **Phases vs stages.**
    - `docs/plan.md` phases A–G (brief §18) and this plan's hardware stages A–D use the same letters for different things.
    - "Phase B → C gate" (`docs/research_questions.md`) and "Phase B gate" (`docs/plan.md`) are the same event as G-B here.
    - COR-23's "Gate G-B" was otherwise undefined. The mapping is in `prototype_stages.md` §2.1.
33. **Scope risk (not a document error).**
    - DEC-009's 7.5 Hz gate against the ET tremor frequency of 5.79 ± 1.32 Hz means about 10 % of ET are above the gate. The frequency figure comes from Elble 2000, **screened but not in `docs/evidence.csv`**; it should be ledgered, since it now carries decision weight.
    - Combined with the amplitude limit, free-writing cancellation may address about 5 % of ET patients. The free-writing variant of EXP-H06 would need about 860 screened to enrol 42.
    - This plan therefore pre-specifies a guided-task variant (H06-G) and makes EXP-H01 and EXP-E01 decide.

### 6.8 Resolution log (project lead, 2026-09-27)

Status of each item above after the consistency pass. Parameters moved to v0.4.2 and the simulation chain was re-run on them.

| Items | Resolution |
|---|---|
| 1, 3, 6 | Fixed. REQ-SAF-002 now reads 0.60 A / ±0.80 A; REQ-MECH-002 reads 0.60 mm; REQ-CTRL-001 reads 40 kHz. |
| 2, 4 | Recorded as **violated** with the limiting numbers. REQ-ACT-001 is infeasible for configuration B; REQ-MECH-001 holds only for θ ≥ 55°. Resolution depends on DEC-008 and a travel/q_lim decision. |
| 5 | Changed: REQ-SNS-004 is now "synchronous with the 2 kHz loop, ≥ 4 kHz preferred". The simulator meets its results with 2 kHz sampling. |
| 7 | Fixed. ICD §5 output carries timestamp, expiry and confidence; expired, NaN or saturated outputs are rejected at the next 2 kHz tick. |
| 8, 28 | Partly fixed. REQ-CAP-001 trace corrected. Nib offset and uncertainty fields, boundary samples, 64-bit time and page id are specified for ICD format v2 (§4.6), not yet implemented. |
| 9, 10 | Fixed. REQ-MECH-004 rationale and COR-05 carry the current sweep numbers; REQ-CTRL-005 has a provisional ≤ 150 µm limit for deliberate fast features. |
| 11–13 | Fixed. Verification ids, COR affected items, and parameter/code comments corrected. |
| 14 | Fixed: REQ-ENV-001–003 added, with criteria AC-H01-20, AC-B01-20 and AC-H01-21. |
| 15–17 | Fixed. COR-18 → COR-14 where the cell is meant; P-23 cites COR-07. `analysis/audit_recalc.py` now numbers corrections like the register, and `results/audit/` was regenerated. COR-04 cites P-4. |
| 18 | Fixed in `docs/audit.md`, `research_questions.md` and `research_synthesis.md` (oracle 0.22–0.32 over the grid, 0.18–0.23 nominal). |
| 19, 20 | Fixed. Electronics 115 mW is used everywhere, read from the config. Runtime: 81 min writing at 65 % duty, 54 min continuous contact. DEC-008 and REQ-ACT-002 separate "in contact" from "average while writing". |
| 21–23 | Fixed in `config/parameters.yaml` v0.4.2 (k_tip 80 N/m, m_eq 13.7 g, Rth 130 K/W); simulations re-run. |
| 24–26 | Fixed. ICD IMU rate is 3.84 kHz; K_m target is 0.29 N/√W; φ uses 2° steps. |
| 27 | Partly fixed: events 0x000A (page) and 0x000B (sync pulse) defined. Calibration and annotation payloads will follow the firmware implementation. |
| 29 | Fixed: all references now point to existing files. |
| 30, 32, 33 | Fixed. H03 n = 20; phase/stage naming note in `docs/plan.md`; Elble 2000 ledgered as PDT-31 (abstract only). |
| 31 | Noted; the adaptive extension to 40 ET stays in the plan. |
| New | The Rev A.1 battery bay (32 mm) cannot hold the 200 mAh the budgets assumed. At the ledgered cell's energy density it holds ~130 mAh. Recorded in DEC-014 as a coupled packaging option set. |
| New (v0.4.4, firmware review round 2) | The simulator applied the magnets' Br tempco at the coil temperature (now at the magnet temperature, `actuator.alpha_B` in the parameter file). The drive calculation now evaluates the current loop as implemented (2 kHz, 55.8° phase margin). The thermal network takes its coil capacity from the parameter file. The simulation chain was re-run on v0.4.4, and the predictions quoted here were refreshed from it. The firmware's loop-margin test shows 35.3° against REQ-CTRL-002's 40° (open; EXP-B05). |
| New (v0.4.3, firmware review) | The thermal network used the old 0.45 mm air gap and 60 mW of electronics. At 0.50 mm and 115 mW: coil-to-structure 145 K/W, 157 K/W steady to ambient, allowable average copper loss 0.412 W (was 0.455 W; now set by the 120 °C coil limit), Rev A coil 96.6 °C at the design load. AC-B03-08 now measures the coil-to-structure resistance directly (coil by resistance, magnets by thermocouple), because the coupon's fixture made "coil to ambient" ill-defined. AC-B03-10, AC-B07-06, the EXP-B03/B07 predictions and the DC test steps follow. The 6 Ω winding binds at 3.3 V in the hot high-force corner (DEC-012 revisited; EXP-B03 winds 4 Ω and 6 Ω). |
| New (v0.4.2 re-run) | The balanced Kalman selection flipped from the inert set to the active one, so KF-BAL = KF-ASR (`docs/sim_report.md` §3.2). Updated to match: the EXP-B09 predictions; the bases of AC-B09-02/04/05/06/07/08/15; §5. `sim/diag_gate.py` → `results/sim/gate_fraction.json` now predicts AC-B09-15. |

## 7. Open items in this plan

- **The bias-actuator (configuration E) feasibility test** needed for G-D is not yet specified. It covers zero-hold slew, force and life (AMF-15).
- **Designs still to be written:** the EXP-H01 instrumented passive pen, and the stage lock (or mass-matched rigid replica) for the OFF condition of EXP-H06.
- **Assumed variances are placeholders.** Every sample size in `human_study_plan.md` §11 and `bench_protocols.md` §0.7 is replaced by pilot or internal-pilot estimates under pre-registered rules.
- **Engineering-judgement thresholds** (labelled so in `basis`) should be reviewed by the project lead before pre-registration. Those tied to perception (EXP-B08 margins, feature distortion) are replaced by EXP-H05 results when available.
- **Sim-to-real proposals not applied here** (`docs/sim_to_real.md` §8; items 1–11 are applied):
  - 12. Split `sim/pensim/core.py` into a plant step and a controller tick, as the hardware-in-the-loop plan needs ([`sim_to_real.md`](sim_to_real.md) §7). The `s2r` shim then becomes unnecessary.
  - 13. The `sim/run_sweeps.py` Monte Carlo and `results/sim/mc_sensitivity.json` regenerate the firmware for every sample. Evaluate them under fixed firmware, or label the file: under fixed firmware K_f and k_tip rank 2nd and 3rd for the Kalman ratio at 9 Hz, where the Monte Carlo ranks them last.
  - 14. Choose estimator sets on randomised plants under fixed firmware (DEC-009, DEC-023).
  - 15. An HDF5 converter for the `s2r-bench-1` layout needs h5py in `requirements.txt`.
- **Gate lists in `prototype_stages.md`** (not edited here) do not yet name the new criteria. Candidates: AC-B02-04/05 and AC-B05-15 for G-B's model rows (next to AC-B02-01); AC-B09-16…18 for G-B and G-C (next to AC-B09-03); AC-Q07-01…03 and AC-Q04-03 for a Rev P1 gate.
- **Sensing and inertial studies (2026-09-28), protocol text still to write:** superimposed 4–12 Hz vibration in the EXP-B01/B02 friction identification (in the pencil model most of the tremor-induced ink error is a friction drift; `docs/sensor_fusion_ai.md` §3.2); raw IMU logging (proposed ICD record 0x07) and the nose accelerometer in the EXP-H01 passive pen; the EXP-B09 jitter test on the Rev A rig (AC-Q06-05 covers the pencil rig).
- **Pencil builds have no stage gates.** `prototype_stages.md` defines G-S, G-B and G-C for Rev A builds only. A pencil safety gate equivalent to G-S is needed before EXP-A02-G, together with a pencil fault-injection set (the Rev A EXP-F01 current and coil criteria do not apply to a piezo stage).

## 8. Changelog

- **2026-09-28 (touchdown study).** `docs/opt_touchdown.md`: touchdown and lift feed-forward (DEC-026) and servo retune (DEC-027). AC-Q08-01 now measures tail ink only (within 30 ms of a touchdown or lift) and is predicted to pass with the feed-forward; the all-extra-ink metric it replaced was dominated by in-stroke distortion. New AC-Q08-04 (in-stroke ink, retuned servo), AC-Q08-05 (slow pen-downs), AC-Q08-06 (contact events) and AC-Q08-07 (correction cost). EXP-Q08 (§33) gains a latency-identification step 0, slow pen-downs, the feed-forward on/off conditions and the matching measurands and decision rules. The status table's counts were stale (256 of 268 rows) and are corrected. 268 → 272 criteria.
- **2026-09-28 (later).** Inertial and sensing studies (`docs/inertial_stabilisation.md`, `docs/sensor_fusion_ai.md`). New experiments: EXP-I01 (grip compliance split, inside EXP-B06; `bench_protocols.md` §35), EXP-I04 (conditional bench, §36), EXP-I02 (rotational share of writing tremor, inside EXP-H01; `human_study_plan.md` §13) and EXP-I03 (passive nose and grip options, §14); 8 criteria. New criteria in existing experiments: AC-S01-09 (IMU latency, with a procedure step), AC-E01-09 (false correction for the fastest writers; EXP-E01 adds the AKF sets, the calibration, the GRU and the template prior), AC-A02-04 (template error in the tremor band, analysis of A02-P) and AC-Q06-05 (command jitter, with a procedure step). 256 → 268 criteria, 39 → 43 experiments.
- **2026-09-28.** Pencil and AI experiments: compact protocols EXP-Q01…Q08 and A03 (`bench_protocols.md` §0.11, §25–§33) and EXP-A02 (`human_study_plan.md` §12); 29 criteria, which cover REQ-PNC-001…008 (AC-M03-07, AC-S01-08 and AC-P01-05 sit in existing experiments). Sim-to-real items 1–11 of `docs/sim_to_real.md` §8 applied: EXP-B05 shaped chirps with an amplitude ladder, static stiffness at ±0.03 N, float32 logging and the IV estimator; EXP-B03 0.2 s holds and back-EMF as a required K_f route; EXP-B02 quarter-decade speeds; F/T calibration at the test angles (B01, B02, R1); AC-B09-03 rewritten (re-parameterisation list, simulant as set) with G7–G9 as AC-B09-16…18; AC-B02-01 replaced by mean-removed R² with AC-B02-04 (G4) and AC-B02-05 (pre-sliding drift); AC-B02-02 judged only when the Stribeck dip is resolved; new AC-B05-15 (model-form diagnostics); AC-B03-01 and AC-B05-03 metrics follow the protocol changes (and the stale v0.4.1 config notes of EXP-B05 now read v0.4.2). Items 12–15 are listed as open (§7). `docs/requirements.csv`: REQ-PNC-002 and REQ-PNC-005 verification now also name EXP-Q06 and EXP-Q03. 221 → 256 criteria, 29 → 39 experiments.
