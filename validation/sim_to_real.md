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
| 3 | EXP-B05 stage (R5 fixture, test build) | `stage.m_eq`, `stage.k_tip`, `stage.zeta_open`, loop delay → `sensing.hall_delay`, `stage.axial_k`, `stage.axial_preload` | `s2r.exp_b05.identify` (uses K_f, L, R20 from step 1) | steps 1, 2 | Residual diagnostics of §5 pass at three excitation levels; static and FRF k_tip agree (χ² ≤ 4) |
| 4 | EXP-B01 then EXP-B02 (R1, R3) | `writing.paper_stiffness`, `writing.mu_eff`, `writing.mu_static_ratio`, `writing.stribeck_speed`, `friction.x_presliding` | `s2r.exp_b01b02.identify` | — | Rig compliance calibrated on a hard flat; pre-sliding length constant across sweep amplitudes (§5); held-out reciprocation criteria of §6 item 4 |
| 5 | Hand: R2 simulant qualification (B09 twin); EXP-B06 (human predictions) | `hand.*` | not modelled | ethics for B06 | Simulant FRF within ±10 % of target (R2); the twin uses the simulant's **as-set** values, not the targets |
| 6 | EXP-S01 optics; EXP-B07 thermal | `sensing.opt_*`; two-node thermal | not modelled | — | — |
| 7 | Update and freeze | overlay YAML; CAL records; frozen B09 predictions with provenance | `s2r.twin.evaluate_plant` (as `run_c2_twin`) | steps 1-6 | Prediction file committed before B09 (§0.2) |
| 8 | EXP-B09 (R2, R3, R7) | — | metrics as `sim/pensim/evaluate.py` | step 7 | Gap metrics of §4 |
| 9 | If a gap metric fails | — | §5 diagnostics on the step 1-4 data and the B09 data | — | Fix the model structure, never tune parameters to B09; re-freeze and re-test on fresh disturbance seeds |

Order matters: step 3 needs n·K_f from step 1 (the FRF mass line gives n·K_f/m_eq) and L, R20 for the known current-loop part of the loop delay; the EXP-B05 Hall-domain FRF needs `CAL_HALL` (step 2).

**Bench time** (virtual-bench estimate with ASSUMED per-record overheads; `results/s2r/c1_identification.json`, `c1_bench_time.json`): EXP-B03 about 16 min per coupon, EXP-B05 about 40 min per build and fixture, EXP-B01/B02 at the protocol grid about 95 min per ink × paper × underlay. The accuracy each needs, and what extra time buys, are in [`docs/sim_to_real.md`](../docs/sim_to_real.md) §3.

### Deviations from `bench_protocols.md` that the pipeline assumes (proposed protocol changes, for the lead)

1. **EXP-B05 procedure 3, open-loop chirp.** A flat 0.05 A chirp from 1 Hz drives the free stage into its stops (CALCULATION: n·K_f·0.05 A / k_tip = 1.4 mm static against a 0.6 mm stop; about 10× more at the 11.8 Hz resonance). Use a pilot chirp shaped for 5 µm on the nominal plant, then chirps shaped on the pilot FRF for about 30 µm, capped at 0.05 A.
2. **EXP-B05 procedure 1, static stiffness at ±0.2 N.** At k_tip = 80 N/m, 0.2 N deflects the tip 2.5 mm, four times the stop radius. Use ±0.03 N or a probe force set from the pilot FRF so that |q| ≤ 0.8 × stop radius, and fit only points inside that radius.
3. **EXP-B05 injection log.** Log the injected current reference as float32 (test-build record or annotation), not only through the 0.1 mA research frame: the resonance-band currents of a 30 µm shaped chirp are 0.1–0.2 mA.
4. **EXP-B05 FRF estimator.** Use the instrumental-variable estimate H = S_ry/S_ru with the known digital excitation r, not H1: H1 is biased low by current-measurement noise near the resonance, and the IV ratio cancels the clock offset between the pen and the rig DAQ. Compute the loop delay inside one clock domain (pen log: command vs Hall); the §0.4 sync bound (±50 µs) is as large as the delay being measured.
5. **EXP-B03 procedure 3, 2 s holds at ±0.6 A.** The holds heat the coil by about 13 K (CALCULATION, one-node coil, median over the declared C_th range), so the protocol's own ΔT < 2 K rule fails at ±0.3 and ±0.6 A. Use 0.2 s holds with ≥ 30 s cooling, or check ΔT per point by resistance and accept that K_f is measured on a warm coil (K_f follows the magnet temperature, not the coil's).
6. **EXP-B03 back-EMF (procedure 5)** becomes a required K_f estimate, not a check: it is independent of the F/T gain, and the F/T's ±2 % calibration alone gives TUR ≈ 3 against AC-B03-01's ±10 %.
7. **EXP-B03 voltage-step L.** Record the coil terminal voltage at ≥ 12 bit (an 8-bit scope misses the 8 mV source sag and biases L by about R_src/R); take L = τ·R with R from the 4-wire reading.
8. **EXP-B02 velocity steps.** Add quarter-decade speeds through the Stribeck transition (0.56, 1.8, 5.6, 18 mm/s); the half-decade grid leaves one or two points in the transition and limits `writing.stribeck_speed`.

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

GAP_TABLE_PLACEHOLDER

## 5. Residual diagnostics: which test catches which missing physics

DIAG_TABLE_PLACEHOLDER

HIL_PLACEHOLDER
