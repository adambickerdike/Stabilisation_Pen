# Interface control document (ICD) — research pen Rev A

**Status:** proposed design, version 1.3 (2026-09-27). v1.2 revised §5 from the ML workstream's results and corrected §1, §2 and §4 after the app and validation reviews. v1.3 aligns the ICD with the firmware implementation and the firmware review (`firmware/README.md` D1–D12):

- §1: the Jacobian (v1.2 printed its inverse), the sign of the actuator force, and γ(θ).
- §2: the optical rate.
- §3: the calibration container and CAL_USER v2.
- §4: the 0x04/0x05 payloads, the page origin, 64-bit stroke time and boundary samples; §4.6 lists what remains for format version 2.
- §5 v1.2: the confidence rule and the status of the exported model.
- §6: the mode codes.

Nothing here is measured.
This file is the contract between electronics, firmware, simulator, ML and app.
Any change bumps the version and the `format_version` fields below.

## 1. Frames, signs and units

| Symbol | Meaning | Unit | Notes |
|---|---|---|---|
| {P} | page frame: e_x, e_y in the page, n = e_z out of the page | — | right-handed |
| {H} | housing frame: z_H = a (barrel axis, nib → cap); x_H, y_H fixed to a housing datum | — | datum = optical module 1 at 30° |
| θ, φ, ρ | altitude, azimuth of the page projection of a, roll about a | rad (logs: 0.01°) | `stabpen/frames.py` |
| q = (q1, q2) | stage displacement of the ball centre relative to the housing, along x_H, y_H (**tip-equivalent**) | m (logs: 0.1 µm) | lever angle ψ = q / L1 |
| s | axial slide of the moving assembly, > 0 toward the cap | m | Rev A.1: the refill slides in the carrier (κ_s = 1, DEC-007 rev.); Rev A: the whole lever slides (κ_s = 0) |
| F_ax | axial force through the suspension, F_pre + k_ax·s | N (logs: mN) | from Hall z channel |
| p_H | housing (sensor datum) position in {P}, relative to the session page origin: the deposited-ink position at the first pen-down of the session | m | optical + IMU fusion; research frames log INT32_MIN until the origin exists |
| d̂ | estimated disturbance (tremor) of the housing in {P} | m | estimator output |
| q_r | stage reference (correction) | m | = −J⁻¹·g·d̂ (compliance-aware J, §3) |
| i1, i2 | coil currents, positive = force along +x_H / +y_H on the actuator paddle (behind the pivot) | A (logs: mA) | the lever reverses it: tip-equivalent force = −n·K_f·i (simulator `core.py`, firmware) |
| g | authority (0–1) | — | fades with confidence, gate, limits |

Page-plane correction to stage command: q = J⁻¹ Δ_page, where J maps stage displacement to page displacement,
J = Rot(φ)·diag(J_t1, 1)·Rot(ρ) and J_t1 = sin θ + γ(θ) cos²θ / sin θ (COR-04).
γ = 1 (rigid page, all tilt-coupled axial motion taken by the suspension) gives the textbook J_t1 = 1/sin θ of `stabpen/frames.py`; γ = 0 gives sin θ. γ depends on tilt: γ(θ) = K_n sin²θ / (K_n sin²θ + k_ax), with K_n the hand's normal stiffness and k_ax the axial path stiffness. Calibration therefore stores the ratio r_n = K_n / k_ax, not γ (§3). v1.2 wrote diag(1/J_t1, 1), which is the inverse; the simulator and firmware were always right.

## 2. Rates and timing (one clock domain: the PWM timer)

| Loop / stream | Rate | Latency budget | Owner |
|---|---|---|---|
| PWM (centre-aligned, 200 levels) | 40 kHz | — | `electronics/calcs/drive_sense.py` |
| Current loop (PI per axis), SAADC sampled at period centre (+ edge, averaged) | 40 kHz | ≤ 47.5 µs loop delay | firmware ISR |
| Stage loop: Hall read → estimator → servo → current references | 2 kHz (every 20 PWM periods) | ≤ 250 µs compute; release jitter ≤ 20 µs | firmware task |
| Hall (TMAG5170, x/y/z) | 2 kHz, triggered at tick start | 14 µs SPI | firmware |
| Optical modules ×3 | 1 kHz (simulator and `config` `sensing.opt_rate`; 2 kHz if the selected sensor allows, EXP-S01) | ≤ 3 ms sensor latency (EXP-S01) | firmware |
| IMU (LSM6DSV16X) | 3.84 kHz ODR (simulator value; 7.68 kHz available), FIFO read at 2 kHz | ≤ 1 ms | firmware |
| ML predictor (optional) | 250 Hz (every 8 stage ticks) | result used at the next tick | firmware + `ml/` |
| Research log frame | 2 kHz (USB CDC stream, bench) | — | §4.2 |
| Product stroke sample | 200 Hz (flash, BLE) | — | §4.3 |

## 3. Calibration records

Stored in flash, CRC-protected, versioned (`cal_version`). All fields little-endian. Container (as implemented in `firmware/include/calib.h`):

```
magic u32 = "PCAL" | rec_type u8 | cal_version u16 | length u16 | payload | crc16 (CCITT-FALSE over magic..payload)
rec_type: CAL_HALL 1, CAL_ACT 2, CAL_ISNS 3, CAL_AXIAL 4, CAL_USER 5
```

`CAL_USER` payload (30 B):

- cal_version 1: f0_hz f32 | f_stroke_hz f32 | f_gate_hz f32 | f_gate_width_hz f32 | g_max f32 | q_lim_m f32 | gamma f32 | mode_perm u8 | flags u8.
- **cal_version 2 (v1.3):** the same layout with `gamma` replaced by `r_n` f32 (K_n / k_ax, dimensionless, 0.02–10). The firmware computes γ(θ) at each Jacobian update. A version-1 record is read with r_n derived from its γ at the nominal 50° tilt.

Flags: bit0 tremor and writing separable in frequency, bit1 tremor found. The stroke frequency and flags record why the calibration placed or withheld the gate. mode_perm bits: 0 ASSIST_KF, 1 ASSIST_ML, 2 GUIDED, 3 TRAINING_FADE. The payload layouts of the other four records are defined when their calibration procedures are implemented.

| Record | Fields | Source experiment |
|---|---|---|
| `CAL_HALL` | 3×3 linear map + offset + cubic terms per axis from (Bx, By, Bz) to (q1, q2, s); current-crosstalk coefficients (T/A) | EXP-B04 |
| `CAL_ACT` | K_f(q) per axis as 5×5 grid over (q1, q2); coil R20; cross-coupling matrix | EXP-B03 |
| `CAL_ISNS` | offset (mA) per axis, gain, duty-dependent sampling correction (table vs duty, VMOT) | bring-up §7 |
| `CAL_AXIAL` | k_ax, F_pre, force-to-s map | EXP-B05 |
| `CAL_USER` | tremor f0 estimate, stroke frequency, f_gate, f_gate_width, authority cap g_max, q_lim, compliance ratio r_n = K_n / k_ax (γ(θ) is computed from it, §1), mode permissions, flags | per-user calibration (firmware `calib.c`); r_n from AC-B09-13-style identification |

## 4. Data formats

### 4.1 Common framing (binary, little-endian)

```
file/stream header (36 B, packed): magic "PENLOG\0\1" (8 B), format_version u16 (=1), device_id u64,
                                   session_id u64, start_unix_ms u64, header_crc u16 (CRC-16/CCITT-FALSE over the first 34 B)
record: type u8 | length u8 (payload bytes) | payload | crc16 (CCITT-FALSE over type..payload)
```

Record types:

- 0x01 research frame (§4.2);
- 0x02 stroke sample (§4.3);
- 0x03 event (§4.4);
- 0x04 calibration snapshot: `rec_type u8 | cal_version u16 | payload` (3 + n bytes), where the payload is exactly the payload of the flash container (§3). Magic, length and CRC are not repeated, because the log record carries its own. Logged when a calibration is applied (with event 0x0004);
- 0x05 annotation: `t_us u32 | UTF-8 text` (4 + n bytes, no terminator, n ≤ 251).

Readers keep unknown record types and the 0x04/0x05 bodies as raw bytes (`app/penapp/logfmt.py`).

### 4.2 Research frame (type 0x01, 2 kHz, 52-byte payload; 112 kB/s with framing, USB only)

| Field | Type | Unit / scale |
|---|---|---|
| t_us | u32 | µs since session start (wraps at 71 min; wrap counter in events) |
| q1, q2 | i16 ×2 | 0.1 µm (±3.2 mm) — measured stage |
| qr1, qr2 | i16 ×2 | 0.1 µm — commanded stage |
| i1, i2 | i16 ×2 | 0.1 mA |
| iref1, iref2 | i16 ×2 | 0.1 mA |
| f_ax | i16 | mN |
| p_Hx, p_Hy | i32 ×2 | 0.1 µm, page frame, fused housing position |
| opt_valid | u8 | bit per module |
| dhat_x, dhat_y | i16 ×2 | 0.1 µm |
| g | u8 | authority × 255 |
| f_est | u8 | tracked tremor frequency, 0.1 Hz |
| mode | u8 | §6 |
| flags | u16 | bit0 contact, bit1 lift, bit2 v_sat, bit3 stop, bit4 fault latched, bit5 ML active, bit6 ML rejected, bit7 thermal derate |
| vbat_mV | u16 | mV |
| t_coil | i16 | 0.01 °C (estimated) |
| imu_ax, imu_ay | i16 ×2 | 1 mg |
| theta, phi | i16 ×2 | 0.01° |

### 4.3 Stroke sample (type 0x02, 200 Hz, 20-byte payload) — the product capture layer

| Field | Type | Unit |
|---|---|---|
| t_ms | u32 | ms since session start, from the 64-bit session clock (wraps after 49.7 days) |
| stroke_id | u32 | monotonically increasing within session |
| x, y | i32 ×2 | 1 µm, page frame (page origin = first contact of the page session) |
| force | u16 | mN (axial) |
| theta, phi | u8 ×2 | θ in 0.5° steps (0–127.5°, used 0–90°); φ in 2° steps (0–358°). v1.0 wrote "0.5°, φ/2", which cannot fit a byte; the app and firmware both implement 2° |

`x, y` are the **deposited ink** position (stage-corrected), not the hand path. The hand-path estimate is a derived layer.

**Sampling.** Samples are taken every 10th stage tick (200 Hz) within a stroke. The phase restarts at the pen-down tick, so every stroke starts with a sample. A boundary sample is added at the last in-contact tick if the grid missed it. Stroke ends are therefore exact to the 0.5 ms stage tick (firmware `app.c`, step 12).

### 4.4 Event record (type 0x03)

`t_us u32 | code u16 | arg i32`. Codes: 0x0001 mode change, 0x0002 fault set (arg = fault bitmask), 0x0003 fault cleared, 0x0004 calibration applied, 0x0005 ML model loaded (arg = model hash low 32 bits), 0x0006 authority capped (arg = reason), 0x0007 pen down, 0x0008 pen up, 0x0009 timestamp wrap (arg = cumulative wrap count), 0x000A page set (arg = page id from coded paper or user action), 0x000B external sync pulse (arg = pulse counter; bench rigs, EXP-S01/B09).

### 4.5 Note store (app side, JSON)

The immutable **original layer** is the list of stroke samples exactly as logged (§4.3), content-addressed by SHA-256. **Derived layers** (never overwrite the original) each carry `layer_id`, `kind` (`recognition`, `segmentation`, `hand_path_estimate`, `user_edit`, `ai_summary`), `created_by` (algorithm id + version or `user`), `inputs` (layer ids / stroke-id ranges) and `created_utc`. Every text span in a derived layer links to the stroke ids it came from. Schema: `data/schema/note_store.schema.json`.

### 4.6 Format changes: done in version 1, planned for version 2

These come from the app workstream's cross-check against the firmware golden log and its capture-fidelity analysis (`app/README.md`, `results/app/capture_fidelity.json`).

Implemented without a format change (v1.3):

- **Boundary samples** (§4.3 sampling). Stroke ends dominated the format error: maximum 120.6 µm, reduced to 81.5 µm with boundary samples in the app's analysis. Bounces shorter than 50 ms previously got zero or one sample.
- **Timestamps.** Stroke `t_ms` now comes from the 64-bit session clock. Earlier firmware derived it from the wrapping 32-bit µs counter, so it restarted every 71.6 min; readers keep the correction for such logs.

Planned for format version 2:

- **Nib offset and uncertainty.** Add the stage offset in page coordinates (i16 ×2, 1 µm) and a position uncertainty (u8, µm) to each stroke sample, so the unassisted hand path can be reconstructed and REQ-CAP-001 met. Payload grows from 20 to 25 bytes; `stroke_id` shrinks to u16 to keep 24 bytes if needed.
- **Page identity.** Event 0x000A is defined, but the firmware does not yet emit it, and the page origin is set once per session. Version 2 starts a new page frame, with its own origin, at each page-set event.

## 5. Firmware ↔ ML predictor contract (v1.2)

| Item | Definition |
|---|---|
| Input | window of W = 64 samples at 250 Hz (256 ms) of housing page displacement increments Δp_H (x, y) in µm, **time-stamped at sensor acquisition** (the fusion knows each sensor's latency); float32 before quantisation. The tracked frequency f_est was dropped in v1.1: removing it did not change the result (test ratio 0.469 vs 0.475, `results/ml/train_tcn_s_nofest.json`) |
| Output | struct {d̂_x, d̂_y (µm, int16); t_acq_newest (µs, u64); expiry = t_acq_newest + 8 ms; confidence (u8, 0–255)}: predicted disturbance at horizon **h = 6 ms after the acquisition time of the newest input sample**. The guard rejects expired outputs (REQ-SAF-003, REQ-ML-002). h covers the worst-case age of a 250 Hz sample (4 ms) plus stage loop and actuation (1.33 ms, `docs/architecture.md` §3). The v1 synthetic model was trained with arrival-stamped inputs, which is equivalent to 8–9 ms and therefore conservative |
| Quantisation | int8 symmetric per-tensor weights, int8 activations, scales stored with the model; C reference kernels in `ml/export/` (bit-exact with the Python int8 reference on 20 000 windows) |
| Budget | ≤ 35 k MAC per inference, ≤ 32 kB flash weights, ≤ 8 kB RAM activations, ≤ 1 ms at 128 MHz. The v1 model uses 16.7 k MAC, 7.3 kB weights and 0.64 kB RAM. It needs CMSIS-NN kernels to meet 1 ms with margin: 0.28–0.89 ms estimated; plain C is 0.92–1.48 ms by QEMU instruction count, not cycle-accurate |
| Guard (`ml_guard.c`), v1.1 | Checks and actions: (1) NaN/Inf or int8 output saturation → reject that inference; (2) clip \|d̂\| to q_lim; (3) slew-limit d̂ at 50 mm/s; (4) a-posteriori check, comparing the prediction made h ago with the realised disturbance (fused housing displacement, band-passed 3–15 Hz) → if the running RMS error over 200 ms exceeds the running RMS of the realised disturbance (worse than predicting zero), fall back to the Kalman estimate for ≥ 1 s and log event 0x0006. The v1 rule rejecting \|d̂ − d̂_KF\| > 150 µm was removed: it rejected 18 % of ticks and cancelled the predictor's benefit (`ml/README.md`) |
| Confidence (v1.2, REQ-SAF-003) | (5) The ML share of authority is scaled by c = min(1, confidence / c_full) and slewed so that it reaches the new value within 20 ms; confidence below c_min is treated as a rejected inference. c_min and c_full are per-model values, set in the model card from the reliability of the confidence output on held-out writers (EXP-E01). Until a model is calibrated, c_min = 0 and c_full = 1, so the byte has no effect: the v1 synthetic model's confidence output is uncalibrated |
| Artefact status | The exported C model (`ml/export/tcn_int8.h`, v1) still takes f_est as a third input channel, i.e. the v1.0 contract. Its re-export without f_est is pending. Until then the firmware passes the Kalman f_est to that interface |

## 6. Modes and safety states

Mode codes (research-frame `mode` byte, event 0x0001 arg): OFF 0, STANDBY 1, NEUTRAL_HOLD 2, ASSIST_KF 3, ASSIST_ML 4, GUIDED 5, TRAINING_FADE 6, SAFE_PASSIVE 7 (firmware `pen_types.h`).

`OFF → STANDBY → NEUTRAL_HOLD → ASSIST_KF | ASSIST_ML | GUIDED | TRAINING_FADE`; any state → `SAFE_PASSIVE` on a fault; `SAFE_PASSIVE → STANDBY` only after pen-up and a successful self-check. Fault bits: 0 over-current latch, 1 Hall frozen/implausible, 2 over-temperature, 3 low battery, 4 optical invalid > 300 ms, 5 watchdog reset, 6 voltage headroom (duty > 0.95 for > 50 ms), 7 charging interlock, 8 ML guard trip count exceeded.

Rules carried from simulation (results/sim/sweeps/summary.json, failure cases F1–F7):
- Never de-energise the stage while in contact except on hard faults (0, 1, 5); low-battery and thermal shutdowns wait for pen-up (timeout 5 s) after fading authority, because releasing the held contact load moves the ink by up to ~0.8 mm (F3).
- A frozen stage sensor drives the stage to its stop within tens of ms (F4); detect it within 5 ms (stuck-value and model-residual tests) and hold the last current references open-loop until pen-up.
