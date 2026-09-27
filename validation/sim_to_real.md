# Sim-to-real procedure: calibrating M1 from the bench and judging it against EXP-B09

**Status: PROPOSED PROCEDURE, demonstrated only in simulation.** No experiment has been executed. The pipeline below runs today on virtual-bench data (`s2r/`, results in `results/s2r/`, report in [`docs/sim_to_real.md`](../docs/sim_to_real.md)). Those twin experiments show that the method recovers parameters and predicts outcomes when the model structure is right, and that its residual tests flag several kinds of missing physics. They cannot show that M1 is right about the pen; the bench decides that.

Conventions (pre-registration, decision rules, metric definitions M-e … M-delay, rigs R1–R7) are those of [`bench_protocols.md`](bench_protocols.md) §0. Records follow [`records/README.md`](records/README.md).

## 1. What the procedure produces

1. An **identified parameter overlay** per build: `config/identified_<build>.yaml` (proposed), same leaf schema as `config/parameters.yaml`, with `value`, `U95`, `status: measured`, `source: <record id>`. Only the keys an experiment measured appear in it; everything else stays at its declared value and status.
2. **Firmware calibration records** from the same numbers (`docs/icd.md` §3): `CAL_ACT` (EXP-B03), `CAL_AXIAL` (EXP-B05), `CAL_HALL` (EXP-B04).
3. **Frozen predictions** for the EXP-B09 matrix, computed with M1 under the overlay and with the firmware constants that the tested build actually carries (`s2r.twin.shim(plant, ctrl_vals)`), before any B09 data exist (§0.2).
4. **Gap metrics** (§4) comparing B09 measurements with the frozen predictions, and **residual diagnostics** (§5) that say where the model is wrong when a gap metric fails.

## 2. Workflow, in the order of the experiments

| Step | Experiment (rig) | Identifies (M1 keys) | Analysis code | Needs | Gate before the next step |
|---|---|---|---|---|---|
| 0 | Instrument qualification and check standards (§0.5, §0.9); sync check (§0.4) | — | — | — | Check standards inside control limits; F/T cross-axis calibration at the test angles (see §6, item 3) |
| 1 | EXP-B03 actuator coupons (R4, R7) | `actuator.Kf` (blocked force and back-EMF), `actuator.R20`, `actuator.L` (voltage step, LCR cross-check), `actuator.Rth_coil_amb`, `actuator.Cth_coil` (thermal step, ratio method) | `s2r.exp_b03.identify` | — | U95(K_f) ≤ 2.5 % (TUR 4 against AC-B03-01); back-EMF and F/T estimates of K_f agree within their combined U95 |
| 2 | EXP-B04 Hall and optical calibration (R5) | `CAL_HALL`; Hall crosstalk | not modelled in s2r | — | Hall readings in µm with ≤ 1 µm residual (AC-B04) |
| 3 | EXP-B05 stage (R5 fixture, test build) | `stage.m_eq`, `stage.k_tip`, `stage.zeta_open`, loop delay → `sensing.hall_delay`, `stage.axial_k`, `stage.axial_preload` | `s2r.exp_b05.identify` (uses K_f, L, R20 from step 1); diagnostics `s2r.modelform` | steps 1, 2 | G1, G2 and the §5 diagnostics pass at three excitation levels; static and FRF k_tip agree (χ² ≤ 4) |
| 4 | EXP-B01 then EXP-B02 (R1, R3) | `writing.paper_stiffness`, `writing.mu_eff`, `writing.mu_static_ratio`, `writing.stribeck_speed`, `friction.x_presliding` | `s2r.exp_b01b02.identify` | — | Rig compliance calibrated on a hard flat; pre-sliding length constant across sweep amplitudes (§5); G4 and the held-out reciprocation criteria of §6 item 4 |
| 5 | Hand: R2 simulant qualification (B09 twin); EXP-B06 (human predictions) | `hand.*` | not modelled | ethics for B06 | Simulant FRF within ±10 % of target (R2); the twin uses the simulant's **as-set** values, not the targets |
| 6 | EXP-S01 optics; EXP-B07 thermal | `sensing.opt_*`; two-node thermal | not modelled | — | — |
| 7 | Update and freeze | overlay YAML; CAL records; frozen B09 predictions with provenance | `s2r.twin.evaluate_plant` (as `run_c2_twin`) | steps 1-6 | Prediction file committed before B09 (§0.2) |
| 8 | EXP-B09 (R2, R3, R7) | — | metrics as `sim/pensim/evaluate.py` | step 7 | Gap metrics of §4 |
| 9 | If a gap metric fails | — | §5 diagnostics on the step 1-4 data and the B09 data | — | Fix the model structure, never tune parameters to B09; re-freeze and re-test on fresh disturbance seeds |

Order matters: step 3 needs n·K_f from step 1 (the FRF mass line gives n·K_f/m_eq) and L, R20 for the known current-loop part of the loop delay; the EXP-B05 Hall-domain FRF needs `CAL_HALL` (step 2).

**Bench time** (virtual-bench estimate with ASSUMED per-record overheads; `results/s2r/c1_identification.json`, `c1_bench_time.json`): EXP-B03 about 16 min per coupon (15 min with 0.5 s holds, same accuracy), EXP-B05 about 40 min per build and fixture, EXP-B01/B02 about 93 min per ink × paper × underlay at the protocol grid, or 33 min on the reduced grid with quarter-decade speeds for the same accuracy of the M1 parameters. The accuracy each needs, and what extra time buys, are in [`docs/sim_to_real.md`](../docs/sim_to_real.md) §3.

### Deviations from `bench_protocols.md` that the pipeline assumes (proposed protocol changes, for the lead)

1. **EXP-B05 procedure 3, open-loop chirp.** A flat 0.05 A chirp from 1 Hz drives the free stage into its stops (CALCULATION: n·K_f·0.05 A / k_tip = 1.4 mm static against a 0.6 mm stop; about 10× more at the 11.8 Hz resonance). Use a pilot chirp shaped for 5 µm on the nominal plant, then chirps shaped on the pilot FRF for about 30 µm, capped at 0.05 A.
2. **EXP-B05 procedure 1, static stiffness at ±0.2 N.** At k_tip = 80 N/m, 0.2 N deflects the tip 2.5 mm, four times the stop radius. Use ±0.03 N or a probe force set from the pilot FRF so that |q| ≤ 0.8 × stop radius, and fit only points inside that radius.
3. **EXP-B05 injection log.** Log the injected current reference as float32 (test-build record or annotation), not only through the 0.1 mA research frame: the resonance-band currents of a 30 µm shaped chirp are 0.1–0.2 mA.
4. **EXP-B05 FRF estimator.** Use the instrumental-variable estimate H = S_ry/S_ru with the known digital excitation r, not H1: H1 is biased low by current-measurement noise near the resonance, and the IV ratio cancels the clock offset between the pen and the rig DAQ. Compute the loop delay inside one clock domain (pen log: command vs Hall); the §0.4 sync bound (±50 µs) is as large as the delay being measured.
5. **EXP-B03 procedure 3, 2 s holds at ±0.6 A.** The holds heat the coil by about 13 K (CALCULATION, one-node coil, median over the declared C_th range), so the protocol's own ΔT < 2 K rule fails at ±0.3 and ±0.6 A. Use 0.2 s holds with ≥ 30 s cooling, or check ΔT per point by resistance and accept that K_f is measured on a warm coil (K_f follows the magnet temperature, not the coil's).
6. **EXP-B03 back-EMF (procedure 5)** becomes a required K_f estimate, not a check. It is independent of the F/T gain. The F/T route alone gives U95 2.3 % (TUR 4.3 against AC-B03-01's ±10 %, barely above §0.5's minimum of 4); with back-EMF it is 1.0 % (TUR 9.6), and the two routes cross-check each other (G3).
7. **EXP-B03 voltage-step L.** Record the coil terminal voltage at ≥ 12 bit (an 8-bit scope misses the 8 mV source sag and biases L by about R_src/R); take L = τ·R with R from the 4-wire reading.
8. **EXP-B02 velocity steps.** Use quarter-decade speeds through the Stribeck transition: 0.56, 1.8, 3.2, 5.6, 18 and 32 mm/s, in place of 3 and 30 mm/s. The half-decade grid leaves one or two points in the transition and limits `writing.stribeck_speed`. On the reduced grid (1 N, 50°) this gives the protocol grid's accuracy for all five M1 contact parameters in 33 min instead of 93 (docs §3.2).
9. **EXP-B05 amplitude ladder.** After the pilot, run two shaped chirps at 5 % and 25 % of the target amplitude, each shaped on the FRF of the previous one, before the chirps that are analysed. With 0.3 mN of pivot friction, the 5 µm pilot under-predicts the response at the target level: a chirp shaped on it alone drove the tip to 0.65–6.8 mm, beyond the stops. With the ladder, every chirp stayed within 0.39 mm (C3). Cost: about 30 s per level.
10. **EXP-B05 excitation levels.** Repeat the shaped chirps at three levels (about 10, 30 and 100 µm at the tip in the flat part of the spectrum), with 3 estimation chirps and 1 held-out chirp each, for the drift and output-error tests of §5. Three levels of 6 chirps (ladder, estimation, held-out) take about 5 min, against 3 min for the protocol's pilot plus 10 chirps at one level. At protocol noise, two 10 s chirps per level identify k_tip, m_eq and ζ as well as ten (docs §3.2).

## 3. Data formats and which code reads which file

**Layout `s2r-bench-1`** (`s2r/io.py`), one directory per experiment and session, stored as `validation/records/<EXP-ID>/<record-id>/raw/s2r/` (written by the rig export) or `analysis/s2r/` (converted from vendor files):

```
manifest.json            {"format": "s2r-bench-1", "experiment": "EXP-B05", "evidence_status": "measured",
                          "meta": {...}, "scalars": {...}, "groups": {"<group>": {"n_records": n, ...}}}
<group>/<nnnn>.json      sidecar: scalar attributes of record nnnn and the array files it owns (names, units)
<group>/<nnnn>_<k>.npz   arrays of one sample-rate group (or .csv with header "name[unit]")
```

HDF5 (preferred by §0.4) maps one to one: one HDF5 group per record, attributes = sidecar scalars, datasets = the array names below. A converter is an open item (h5py is not in `requirements.txt`).

| Experiment | Group | Arrays (unit) | Scalars per record |
|---|---|---|---|
| EXP-B03 | `r20` | `R_ohm` (ohm, repeated 4-wire readings) | `T_nominal_C` |
| | `step` | `t_s`, `i_A`, `v_V` (scope, ≥ 10 MS/s, averaged acquisitions) | `T_coupon_C`, `n_avg` |
| | `force` | — (per-point list `points`: `I_set_A`, `F_mean_N`, `F_sd_N`, `n`, `rep`, `coil_dT_K`) | `T_magnet_C`, `hold_s` |
| | `emf` | `v_emf_V`, `vel_m_s` (10 kS/s) | `f_Hz`, `fs`; group: `T_magnet_C` |
| | `thermal` | `t_s`, `R_ohm` (10 Hz, pre-step readings first) | `I_set_A`, `t_on_s`, `T_amb_C` |
| EXP-B05 | `chirps` (one per chirp) | `daq`: `i_A`, `v_m_s`, `ref_A` (10 kS/s); `pen`: `iref_A`, `q_hall_m` (2 kHz) | `fs` per block |
| | `static` | `F_N`, `q_m`, `dir`, `cycle` | — |
| | `axial` | `F_N`, `s_m` | — |
| | top level | — | `T_c`, `n_chirps`, `T_magnet_C`, `q_peak_last_m` |
| EXP-B01/B02 | `indent` | `t`, `z_laser`, `F_a`, `F_t1`, `F_t2` (pen-frame F/T) | `surface` (`paper` or `hard_flat`), `theta`, `rep` |
| | `sliding`, `steps`, `recip` | `t`, `F_a`, `F_t1`, `F_t2` (5 kHz), `x_enc`, `y_enc` | `N_set`, `beta_deg`, `v_set`, `dwell`, `theta` (+ `f`, `A`, `drift` for `recip`) |
| | `sweeps` | as above plus `t_cap`, `x_cap` (10 kHz capacitive) | `A`, `speed`, `N_set`, `theta` |

Forces are recorded in the pen frame (a, t1, t2) as the F/T reports them; the analysis rotates them with the **set** angle. Hidden or unknown quantities (the true angle, true gains) never appear in the files.

**Code**:

```python
import numpy as np
from s2r import io, exp_b03, exp_b05, exp_b01b02
b03 = exp_b03.identify(io.load("<record>/raw/s2r/EXP-B03"), np.random.default_rng(0))
kf, L, R = (b03["estimates"][k] for k in ("actuator.Kf", "actuator.L", "actuator.R20"))
b05 = exp_b05.identify(io.load("<record>/raw/s2r/EXP-B05"), kf["value"], kf["u"], L_hat=L["value"], R20_hat=R["value"])
b12 = exp_b01b02.identify(io.load("<record>/raw/s2r/EXP-B01B02"), np.random.default_rng(0))
```

Each returns `estimates` (M1 key → `value`, `u`, `U95`), diagnostics and the bench time. An example set written and re-read by the pipeline (identical estimates) is in `results/s2r/virtual_bench_example/` (`python3 -m s2r.run_c5_example`).

## 4. Gap metrics and proposed acceptance thresholds

Two layers. **Component gaps** (G1–G4) ask whether the calibrated twin reproduces each identification experiment, including records held out of the fit; they are checked before EXP-B09 and localise a problem. **Outcome gaps** (G5–G9) compare the frozen EXP-B09 predictions with the EXP-B09 measurements; AC-B09-03 judges these. The twin for G5–G9 runs the B09 paths and disturbance realisations actually injected (§0.2), with the angle and force the rig recorded.

Every threshold is PROPOSED. Each one comes from two results: how far a parameter error moves an EXP-B09 outcome (C2 sensitivities, CALCULATION on M1), and what a twin of the right structure achieves on bench-grade data (twin experiments, SIMULATION). Neither shows what the real pen will do.

| ID | Compares | Metric | Proposed threshold | Basis (SIMULATION / CALCULATION) |
|---|---|---|---|---|
| G1 | EXP-B05 stage FRF (current → tip, IV estimate) vs M1 with the overlay | band means of H_meas/H_twin per 1/3 octave, 2–100 Hz | off resonance ≤ 1 dB and ≤ 5°; inside [f_n/1.3, 1.3·f_n] ≤ 3 dB and ≤ 20° | 1 dB is 12 %. An n·K_f or k_tip error of 12 % moves the Kalman ratio at 9 Hz by ≤ 0.05, half the AC-B09-03 band (sensitivities 0.38 and 0.26 per unit ln). A twin of the right structure matches within 0.01 dB and 0.02° (C3 control). A flexure mode inside the fit band collapses the fit (28 dB, 90°). Friction, backlash and extra delay stay under 1 dB and 5° at the mid excitation level, so G1 is a check of practical adequacy, not a detector; the χ² row is the detector. |
| G1χ | same | noise-normalised χ²/dof in seven bands, 2–300 Hz | ≤ 4 in every band | C3: right structure 1.4 at worst. Stage defects give 2.4×10³ to 4.4×10⁵ in the band where they act. Extra loop delay stays at 0.02, because a fitted delay absorbs it; G2 catches it instead. |
| G2 | EXP-B05 pen-log FRF (command → Hall) | Hall delay left after removing the known current-loop and sampling parts | design value ± 25 µs, or explained by an R7 logic-analyser measurement | C3: right structure +3 µs; 150 µs of extra delay reads +180 µs; a flexure mode absorbed as delay reads +2.4 ms. C1: +3 µs median bias (−3 to +5 µs) over 15 plants. |
| G3 | EXP-B03 | K_f from blocked force vs from back-EMF | difference within the combined U95 | the two routes share no instrument (F/T gain vs LDV scale) |
| G4 | EXP-B01/B02 held-out reciprocation, records ≤ 50 µm | RMS(F_pred − F_meas) with each record's mean removed, / (μ_k N) | ≤ 0.10 | Computed on per-record mean-removed signals, because the F/T cross-axis offset is not friction dynamics. Right structure: ≤ 0.077 on all 15 C1 plants (μ_k down to 0.035) and 0.024 in C3. Friction-memory truth: 0.101. Without mean removal the right structure reaches 0.45 at μ_k = 0.035. |
| G5 | EXP-B09 ORACLE M-ratio, primary cells | \|measured − predicted\| | ≤ 0.10 (AC-B09-03 as it stands) | 14 of 15 hidden plants within 0.1 at 6 Hz and at 9 Hz, once the B03, B05 and B01/B02 estimates and the simulant's as-set values (±10 %) are in the twin; RMS 0.041 / 0.049 |
| G6 | EXP-B09 KF-ASR / KF-BAL M-ratio | \|measured − predicted\| | ≤ 0.10, **provided** the EXP-S01/B04 sensor values are in the twin | sensor keys nominal: 12 and 9 of 15 within 0.1 at 6 and 9 Hz (worst 0.42 / 0.71); sensor keys at their true values: 14 of 15 at both (worst 0.16 / 0.24) |
| G7 | EXP-B09 NEUTRAL M-rms (the ratio denominator) | relative difference | ≤ 15 % | 95th percentile 14.5 % / 13.1 % at 6 / 9 Hz |
| G8 | Static hold copper loss, 1 N at 50° (M-Pcu) | relative difference | ≤ 5 % | worst 2.3 %; set by K_f and R20 from EXP-B03 |
| G9 | EXP-B09 M-dist (Kalman set, no disturbance) | measured/predicted M-dist, and the verdict against AC-B09-06 (50 µm) | within a factor of 2 (0.5–2), with the same verdict | With the sensor keys identified, 15 of 15 plants fall within a factor of 2 and 14 of 15 get the same verdict, with an RMS difference of 85 µm. With the sensor keys nominal, 12 and 13 of 15. An absolute band is not achievable: one plant's gate never opens (0 µm) while its twin predicts 410 µm. |

When G5–G9 fail but G1–G4 pass, the missing physics lies outside what B03/B05/B01-B02 exercise: the hand, the sensors, contact at the B09 operating point. A **failed G-metric is a model-form result.** The response is §5's diagnostics and a structural fix, then a new prediction on fresh disturbance seeds. Parameters are never tuned to EXP-B09 data.

## 5. Residual diagnostics: which test catches which missing physics

Run these on the identification data before EXP-B09, and again whenever a §4 metric fails. They use only what the analyst has: the records, the M1-structure fit and the design values. Each was tried on a constructed truth with one piece of physics M1 lacks, identified with M1's structure (C3; SIMULATION with ASSUMED effect sizes; `results/s2r/c3_modelform.json`, `fig_c3_model_form.png`).

**EXP-B05 stage.** After the pilot and the amplitude ladder (§2 item 9), shaped chirps run at three levels: 10, 30 and 100 µm at the tip in the flat part of the spectrum, with record peaks about 3.3× higher. Each level has 3 estimation chirps and 1 held-out chirp. Proposed thresholds:

- *band χ²/dof* of the noise-normalised FRF residual in 2–8, 8–20, 20–50, 50–100, 100–160, 160–240 and 240–300 Hz: ≤ 4;
- *G1* of §4;
- *output error on the held-out chirp*. The fitted model, refined for output error on the estimation chirps, predicts the Hall reading from the logged command. The residual must stay ≤ 1.3× the sensor noise measured in the record's quiet tail. Whiteness (Ljung–Box, 1 %) is reported alongside. It is very sensitive (it rejects the ±2 µm backlash, whose output error is no larger than the sensor noise), so a non-white residual prompts a look rather than failing the fit;
- *drift* of f_n, ζ, m_eq and Hall delay across the three levels: flagged when the χ² constancy test gives p < 0.01 **and** the change exceeds a practical margin of 1 % (f_n, m_eq), 5 % (ζ) or 5 µs (delay). The margins were added after the first run: without them the M1-structure control failed on a 0.014 % change in f_n (p = 0.003), which no prediction could feel;
- *Hall delay* within the design value ± 25 µs (G2).

| Truth (stage, EXP-B05 test build) | Worst band χ²/dof (band) | G1 off resonance: dB / ° | Output error: excess over sensor noise; white | Drift across levels | Hall delay − design | Flagged by |
|---|---|---|---|---|---|---|
| control (M1 structure) | 1.4 (8–20 Hz) | 0.00 / 0.0 | 0.99; yes | none (ζ significant, below margin) | +3 µs | **none** |
| flexure mode 220 Hz (10 % of the mass) | 4.4×10⁵ (160–240 Hz) | 27.94 / 90.2 | 1.29; no | none | +2426 µs | band χ², G1, OE not white, delay |
| flexure mode, refit 2–120 Hz after the flag | 1.5×10⁴ (100–160 Hz) | 0.84 / 0.8 | 1.28; no | none | −23 µs | band χ², OE not white |
| extra loop delay 150 µs + 20 µs release jitter | 0.022 (240–300 Hz) | 0.01 / 0.0 | 2.99; no | none | +180 µs | OE excess, OE not white, delay |
| pivot Coulomb friction 0.3 mN | 3.6×10³ (2–8 Hz) | 0.12 / 4.9 | 3.07; no | f_n 1.3 %, ζ 176 %, delay 59 µs | +7 µs | band χ², OE excess, OE not white, drift |
| backlash ±2 µm | 2.4×10³ (240–300 Hz) | 0.36 / 0.3 | 0.99; no | none | +6 µs | band χ², OE not white |

Reading the pattern (the mid level unless stated):

- *Flexure mode near the fit band.* The 2–300 Hz fit collapses: ζ runs to its bound, f_n to 33 Hz, and the fitted delay absorbs the mode (+2.4 ms). Every test fires. Refitting below the flagged band recovers f_n and ζ (12.18 Hz, 0.056) and passes G1 and G2. m_eq and k_tip then come out 10–11 % low, and the band χ² above 100 Hz and the non-white output error still flag the mode. A mode inside the fit band is a reason to model it, not to narrow the band.
- *Extra loop delay and jitter.* The FRF fits perfectly because the fitted delay absorbs it. Only the delay against design (+180 µs) and the output-error excess (3.0) show it. The Hall-domain delay check is what catches timing problems.
- *Pivot friction.* The low-frequency bands fail and the output error is 3× the sensor noise. ζ drifts from 0.058 at 100 µm to 0.16 at 10 µm, and the apparent Hall delay grows by 59 µs at small amplitude. G1 passes at the mid level (0.12 dB, 4.9°) but fails at 10 µm (0.9 dB and 11° off resonance, 12 dB at resonance).
- *Backlash.* Only the top band (240–300 Hz) and whiteness show it. The output error equals the sensor noise, and m_eq is 4–5 % low.
- *Control.* All tests pass at all levels. A 0.2 % change of ζ is statistically significant but below the practical margin.

**EXP-B01/B02 friction memory** (tribometer; truth a 6-element Maxwell-slip model with the same μ_k, μ_s, v_s and a comparable initial slope; identified with single-state LuGre):

| Truth | x_pre from the 50 / 200 / 1000 µm sweeps | Drift test (10 % margin) | AC-B02-01 R², pooled; mean-removed | G4: NRMSE of μ_k N, records ≤ 50 µm: raw; mean-removed |
|---|---|---|---|---|
| LuGre (control) | 10.03 / 10.03 / 10.03 µm | constant (p 0.98, spread 0.1 %) | 0.993; 1.000 | 0.074; 0.024 |
| Maxwell-slip, 6 elements (friction memory) | 9.2 / 15.7 / 16.3 µm | **drift 55 %** (p < 10⁻¹⁰) | 0.987; 0.989 | 0.122; **0.101** |

AC-B02-01 as written passes both truths. The pre-sliding drift across sweep amplitudes separates them cleanly: 0.1 % against 55 %. The mean-removed small-amplitude NRMSE separates them too (0.024 against 0.101), but only just crosses a 0.10 threshold, and a low-friction ink reaches 0.077 with the right model (C1). The drift test should lead.

**Hand resting on the paper** (EXP-B09 twin): the truth has the palm stuck to the paper, linearised as +500 N/m and +10 N s/m on the arm (ASSUMPTION); the twin keeps the free-hand values. The ratios hardly notice it. The ORACLE ratio is 0.142 against 0.162 predicted, and the Kalman ratio at 9 Hz 0.73 against 0.78; both are inside ±0.1, so G5 and G6 pass. The NEUTRAL error does notice: the twin over-predicts it by 19 % and 61 % at 6 and 9 Hz, so G7 fails. The band-resolved ratio localises the effect below 3 Hz (truth/twin 0.78 and 0.67 in 1–3 Hz; 1.0–1.2 in the other bands). The twin's Kalman M-dist is 100 µm against the truth's 56 µm. A hand resting on the page is therefore a B09 condition to control and record (R2 simulant with or without palm support), not a parameter to fit.

## 6. Proposed changes to acceptance criteria (for the lead; nothing here is edited in `acceptance_criteria.csv`)

1. **AC-B09-03, re-parameterisation list.** Today it reads "EXP-B01, B02, B05, B06". Add EXP-B03 (K_f, R20, L: the Kalman ratio at 9 Hz moves 0.38 per unit ln K_f) and EXP-S01/B04 (optical noise and delay, Hall noise). With the sensor keys left nominal, 9 of 15 hidden plants were predicted within 0.1 at 9 Hz; with them identified, 14 of 15 (G6). State that the hand in the twin is the R2 simulant **as set**, within its ±10 % qualification; with the hand left at nominal, only 7–8 of 15 oracle predictions fell within 0.1.
2. **AC-B09-03, scope.** Keep ±0.1 for ORACLE, KF-ASR and KF-BAL M-ratio. Add G7 (NEUTRAL M-rms within 15 %) and G8 (hold power within 5 %) as agreement checks. For M-dist, judge agreement as a factor-of-2 band with the same verdict against AC-B09-06 (G9), not an absolute band. Per-plant distortion depends on whether and when the Kalman gate opens, and the twin gets it within a factor of 2 only with the sensor keys identified.
3. **EXP-B01/B02, F/T calibration at the test angles.** A 6-axis F/T of the protocol class (±2 % per axis) mixes the normal force into the friction axes at θ = 45–60°. For a low-friction ink this cross-talk is a large share of the friction signal: on the 15 C1 plants, the correct model's held-out friction NRMSE reached 0.24 at μ_k 0.065 and 0.45 at μ_k 0.035, and R² fell to 0.92 and 0.77. The cross-talk is mostly a constant offset: with each record's mean removed, the same records give NRMSE ≤ 0.077 and R² ≥ 0.98. Calibrate the per-axis gains and cross-axis terms at each test angle with dead weights, to ±0.2 %. Or analyse friction from the rig's own tangential load cell, if R1 has one.
4. **AC-B02-01 (LuGre R² > 0.9 on held-out reciprocation).** As written, it misses the failures it exists to catch and flags a correct model. A Maxwell-slip (friction-memory) truth passes it with R² 0.987 (C3), while the correct model fails it for a low-friction ink (0.77 at μ_k 0.035, C1). Proposed replacement, all three together: (a) G4, mean-removed NRMSE ≤ 0.10 of μ_k N on held-out records ≤ 50 µm; (b) pre-sliding length constant across the 5 µm–1 mm sweeps (drift test with a 10 % margin, §5); (c) R² per record after removing each record's mean, > 0.9.
5. **EXP-B05 model validation (new criterion).** AC-B05-01 (resonance within ±10 % of prediction) passes a stage with backlash, extra loop delay or pivot friction. It also passes one with a flexure mode once the fit is restricted below the mode. In C3 the M1-structure f_n stayed within 1.4 % of the control's in all these cases. Add the §5 diagnostics as a pass criterion of the EXP-B05 fit, at three excitation levels:
   - band χ² ≤ 4;
   - G1;
   - output-error excess ≤ 1.3, with whiteness reported;
   - no drift beyond the practical margins;
   - loop delay within G2.
6. **AC-B02-02 (Stribeck speed 0.5–10 mm/s).** When μ_s/μ_k is within a few per cent of 1, v_s is not identifiable and does not matter; the virtual bench returns U95 > 1000 % there. Judge v_s only when μ_s/μ_k − 1 exceeds 3 × its U95, and report "not identifiable" otherwise.

## 7. Hardware-in-the-loop plan (specification only; nothing here is built)

**Goal.** Run the real firmware on the real MCU against M1 as the plant, before and alongside the Stage A/B hardware: to find timing, driver and numerical problems that the host and QEMU tests cannot see, and later to replay bench-identified plants (the calibrated twin) against the firmware build that will be tested on EXP-B09.

**What exists** (`firmware/README.md`): the control core runs on the host (ASan/UBSan) and on QEMU `mps2-an505` (not cycle-accurate) against `firmware/tests/plant.c` (switched H-bridge, coil, stage, SAADC and Hall models at PWM-clock resolution), with golden vectors and closed-loop replays generated from `sim/pensim` (60 cases, 1120 checks). The nRF5340 image links; register-level drivers are marked VERIFY.

**Levels**, each a gate for the next:

| Level | Plant | Firmware | Coupling | Real time | What it proves |
|---|---|---|---|---|---|
| H0 (exists) | `tests/plant.c` | control core, host/QEMU | function calls | no | port fidelity against the simulator, fault logic |
| H1 SIL-M1 | M1 plant step (see "M1 change" below) | control core as a host shared library (`libpencore.so`, the `make test` objects) | Python ctypes, lock-step per 25 µs | no | the firmware controller, not M1's own controller, closing the loop on M1 across the B09 matrix; M-ratio within 0.01 and M-dist within 5 % of M1's own controller on the 12 test seeds; a larger difference is a port defect |
| H2 PIL | M1 plant on the host | full image on an nRF5340 DK, test build with the SAADC END and EGU0 events raised by a host message instead of the DPPI chain | SWD/RTT or UART at ≥ 4 Mbit/s, lock-step per stage tick (20 current-loop steps per exchange) | no (≈ 2-4× slower) | numerics of FPv5-SP on silicon (bit-exact against H1 float32 within 1e-6 relative), cycle counts per ISR and per tick with DWT CYCCNT against the 64 000-cycle budget, stack high-water mark, log ring under load |
| H3 real-time HIL | electrical and sensor interfaces on an FPGA, mechanics on a real-time core | unmodified image on a Rev A board or DK with the Rev A drive stage | electrical signals | yes | end-to-end timing (47.5 µs current-loop delay, ≤ 20 µs tick release jitter), driver behaviour, fault injection EXP-F01/F02, thermal governor over minutes |

**H2 exchange per stage tick** (every 500 µs of plant time):

- host → MCU: 20 × 2 SAADC centre and edge codes (int16) for the current loop, TMAG5170 X/Y/Z raw codes with their CRC nibbles (the frame format of `sensors_nrf5340.c`), 2 IMU FIFO samples (int16 × 3), 1 optical sample every second tick (validity + counts), VBAT and NTC codes every 20th tick: about 120 B;
- MCU → host: 20 × 2 bridge commands (IN1/IN2 duty and mode, `bridge_cmd_t`), ACT_EN_REQ, DRV_SLEEP_N, the research frame (52 B): about 150 B.
At 4 Mbit/s this is ≈ 0.6 ms per tick: lock-step, 1.2× real time plus host compute.

**H3 interface and timing budget:**

| Interface | Emulation | Budget |
|---|---|---|
| Bridge gates IN1/IN2 × 2 axes (40 kHz, 200 levels) | FPGA captures edges at ≥ 100 MHz; coil R-L-EMF solved at 1 MHz with the exact exponential step (as core.py) | ≤ 1 µs from gate edge to current update (2 % of the 47.5 µs loop delay) |
| Current sense (INA241 1 V/A, anti-alias 1 k/10 nF into the SAADC) | 16-bit DAC at ≥ 1 MS/s driving the INA241 output node (or the SAADC pin through the RC) | DAC noise ≤ 0.1 mA equivalent (below the 0.55 mA SAADC noise of drive_sense.json) |
| TMAG5170 (SPI, 32-bit frames, CRC4) | FPGA SPI slave serving the plant's lever position through the inverse CAL_HALL map, with the Hall delay and noise of the identified plant | frame ready ≤ 2 µs after chip select |
| LSM6DSV16X (SPI, FIFO) | SPI slave with a FIFO fed at 3.84 kHz from the housing acceleration | FIFO timestamp error ≤ 5 µs |
| Optical modules (SPI, 1 kHz) | SPI slave, delayed page position with scale error and dropouts (EXP-S01 values) | latency as identified ± 50 µs |
| Mechanics (stage, axial slide, housing, hand, contact, LuGre) | M1 plant step at 25 µs on a real-time core (FPGA hard core or an RT-PREEMPT PC over PCIe) | deadline 25 µs, jitter ≤ 2 µs; overruns counted, run void if any |
| Faults (EXP-F01) | relay/solid-state board of rig R7 on the emulated signals: coil short, open lead, Hall supply cut, SPI freeze | as EXP-F01 |

**M1 change needed (proposal for the lead; not made here):** H1–H3 need the plant separated from M1's built-in controller. Split `sim/pensim/core.simulate` into `plant_step(state, V[2], dt)` (mechanics, contact, coil electrical and thermal, sensor ring buffers) and the existing controller tick, keeping the step order and the 25 µs integration, and add a regression test that the recombined loop reproduces today's `simulate` bit for bit. s2r's shim (`s2r/twin.py`) would then become unnecessary for plant/controller separation.

**Acceptance of the HIL itself** (before any firmware verdict is drawn from it):
1. The EXP-B05 test-build FRF measured on the HIL (current injection, s2r.exp_b05 analysis) matches M1's within G1 and G1χ of §4, and the identified loop delay is the design sum ± 5 µs.
2. The H1 replay cases (golden vectors) reproduce within the tolerances of `firmware/tests`.
3. Logic-analyser timing (R7): tick release jitter, current-loop delay, SAADC sampling instants against the PWM centre.

**Test campaign on the HIL:** EXP-F01/F02 fault sequences; the EXP-B09 matrix with injected housing disturbance (ORACLE with the plant's true disturbance, ASSIST_KF, GUIDED); the thermal governor over 30 min with the two-node thermal model (the M1 plant step needs the structure node for this; one-node M1 is valid only for runs well under 3 min); the ML guard with injected predictor outputs (ICD §5).
