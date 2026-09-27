# Product features: what each does, for whom, and what may be claimed

**Status:** feature definitions for the research pen. Every "evidence" entry is calculation, simulation or literature; no feature has been tested on people. **Immediate assistance** (performance while the device acts) and **lasting improvement** (unassisted performance after practice) are separate claims with separate studies (`validation/human_study_plan.md`).

| Feature | Mode (ICD §6) | Intended users | Mechanism | Evidence now | May claim now | Needed to claim more |
|---|---|---|---|---|---|---|
| Ordinary writing | `NEUTRAL_HOLD` / off | everyone | Stage held at neutral; the pen writes like a pen | Device distortion vs a rigid pen ≈ 59 µm RMS (sim) | nothing beyond "writes" | EXP-H02 writing feel; H05 perception threshold |
| Tremor cancellation, free writing | `ASSIST_KF` | action/essential tremor ≤ 1 mm p-p at the nib and tracked frequency ≥ gate (DEC-002, DEC-009) | Page-referenced Kalman estimate; stage moves the nib against the predicted disturbance | Oracle bound 0.22–0.32 of neutral error (sim). Causal estimators ≈ no benefit below 9 Hz; assertive Kalman 0.84 at 12 Hz; band-pass harms below 8 Hz (sim, synthetic writing) | **no efficacy claim** | EXP-E01 on recorded writing; B09 bench; immediate-assistance crossover study |
| Guided tracing and drawing | `GUIDED` | tremor, rehabilitation, art | The correction pulls toward a known template (letters, shapes) instead of guessing intent | Path distance to the template (RMS, 6 Hz / 0.3 mm tremor, 4 seeds): circle 442 → 165 µm, spiral 382 → 111 µm, fast stroke 115 → 34 µm, dots 153 → 101 µm, corners 228 → 187 µm, hatching 141 → 130 µm (sim, `results/sim/guided_path_distance.json`) | none | Template library; H-study with tracing tasks |
| Micrographia support (Parkinson's) | app cues + `TRAINING_FADE` | PD with micrographia | Letter-size monitoring from capture; haptic (ERM) or visual cue when size decays; external cueing | Literature: cueing improves size; ±0.5 mm stage cannot enlarge letters (COR-10) | none | H04-style training study with retention/transfer |
| Practice for lasting improvement | `TRAINING_FADE` | tremor and PD users who want unassisted gains | Fading guidance or error amplification; unassisted probes | Literature: error-removing guidance can impair retention (HAP-09) | none | H04 randomised practice study, delayed retention |
| Faithful stroke capture | always (logging) | everyone | Deposited-ink position (optical + IMU + stage), 200 Hz, 1 µm LSB, immutable original layer | Format resampling error measured on simulated traces (app capture-fidelity analysis) | none | S02/C02 against a reference digitiser |
| Handwriting recognition | app | everyone | Off-the-shelf on-device recogniser behind an interface (DEC-013) | Vendor claims only | none | C01 writer-disjoint evaluation, incl. tremor-affected writing |
| Searchable notes | app | everyone | Full-text index over recognised text with stroke-level links | Implemented on synthetic data (app/) | none | C01 retrieval evaluation |
| Source-grounded AI assistance | app | everyone | Retrieval over the user's own notes; every generated sentence cites stroke ranges; refusal without support; stored as a separate layer | Enforced by tests on synthetic data (app/) | none | A01 grounding audit |
| Personal calibration | `calib` | assisted users | Per-user tremor frequency, gate, authority cap, γ; per-refill force re-zero | Design (firmware `calib.c`); refill-length tolerance makes re-zero mandatory (tolerance S5) | — | EXP-H01 data; B04/B06 |
| Safety behaviours | always | everyone | Hardware interlock; no de-energising in contact; frozen-sensor detection; derating before pen-up | Simulation of failures F1–F7; ngspice trip 8.8 µs | — | F01/F02 fault injection |

## Modes the product does **not** have

- **Diagnosis or severity scoring.** Captured handwriting is never used to infer a medical condition. Any clinical use would need its own regulatory path.
- **Silent correction.** Assistance is always user-visible (LED or app), and the unassisted ink can always be reproduced from the logs (original layer + stage record).
- **Enlarging strokes mechanically.** Letter size cannot be changed by a ±0.55 mm stage.
