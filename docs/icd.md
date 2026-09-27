# Interface control document (ICD) — research pen Rev A

**Status:** proposed design, version 1.2 (2026-09-27). §5 was revised from the ML workstream's results; §1, §2 and §4 were corrected after the app and validation reviews; §4.6 lists the v2 format changes. Nothing here is measured.
This file is the contract between electronics, firmware, simulator, ML and app.
Any change bumps the version and the `format_version` fields below.

## 1. Frames, signs and units

| Symbol | Meaning | Unit | Notes |
|---|---|---|---|
| {P} | page frame: e_x, e_y in the page, n = e_z out of the page | — | right-handed |
| {H} | housing frame: z_H = a (barrel axis, nib → cap); x_H, y_H fixed to a housing datum | — | datum = optical module 1 at 30° |
| θ, φ, ρ | altitude, azimuth of the page projection of a, roll about a | rad (logs: 0.01°) | `stabpen/frames.py` |
| q = (q1, q2) | stage displacement of the ball centre relative to the housing, along x_H, y_H (**tip-equivalent**) | m (logs: 0.1 µm) | lever angle ψ = q / L1 |
| s | axial slide of the moving assembly, > 0 toward the cap | m | Rev A: whole lever slides (κ_s = 0) |
| F_ax | axial force through the suspension, F_pre + k_ax·s | N (logs: mN) | from Hall z channel |
| p_H | housing (sensor datum) position in {P}, relative to the session page origin (the pen-down point of the first stroke) | m | optical + IMU fusion |
| d̂ | estimated disturbance (tremor) of the housing in {P} | m | estimator output |
| q_r | stage reference (correction) | m | = −J⁻¹·g·d̂ (compliance-aware J, §3) |
| i1, i2 | coil currents, positive = force along +x_H / +y_H at the tip | A (logs: mA) | force at tip = n·K_f·i |
| g | authority (0–1) | — | fades with confidence, gate, limits |

Page-plane correction to stage command: q = J⁻¹ Δ_page with
J = Rot(φ)·diag(1/J_t1, 1)·Rot(ρ) and J_t1 = sin θ + γ cos²θ / sin θ (COR-04, γ from calibration).

## 2. Rates and timing (one clock domain: the PWM timer)

| Loop / stream | Rate | Latency budget | Owner |
|---|---|---|---|
| PWM (centre-aligned, 200 levels) | 40 kHz | — | `electronics/calcs/drive_sense.py` |
| Current loop (PI per axis), SAADC sampled at period centre (+ edge, averaged) | 40 kHz | ≤ 47.5 µs loop delay | firmware ISR |
| Stage loop: Hall read → estimator → servo → current references | 2 kHz (every 20 PWM periods) | ≤ 250 µs compute; release jitter ≤ 20 µs | firmware task |
| Hall (TMAG5170, x/y/z) | 2 kHz, triggered at tick start | 14 µs SPI | firmware |
| Optical modules ×3 | 2 kHz burst | ≤ 3 ms sensor latency (EXP-S01) | firmware |
| IMU (LSM6DSV16X) | 3.84 kHz ODR (simulator value; 7.68 kHz available), FIFO read at 2 kHz | ≤ 1 ms | firmware |
| ML predictor (optional) | 250 Hz (every 8 stage ticks) | result used at the next tick | firmware + `ml/` |
| Research log frame | 2 kHz (USB CDC stream, bench) | — | §4.2 |
| Product stroke sample | 200 Hz (flash, BLE) | — | §4.3 |

## 3. Calibration records

Stored in flash, CRC-protected, versioned (`cal_version`). All fields little-endian.

| Record | Fields | Source experiment |
|---|---|---|
| `CAL_HALL` | 3×3 linear map + offset + cubic terms per axis from (Bx, By, Bz) to (q1, q2, s); current-crosstalk coefficients (T/A) | EXP-B04 |
| `CAL_ACT` | K_f(q) per axis as 5×5 grid over (q1, q2); coil R20; cross-coupling matrix | EXP-B03 |
| `CAL_ISNS` | offset (mA) per axis, gain, duty-dependent sampling correction (table vs duty, VMOT) | bring-up §7 |
| `CAL_AXIAL` | k_ax, F_pre, force-to-s map | EXP-B05 |
| `CAL_USER` | tremor f0 estimate, f_gate, f_gate_width, authority cap g_max, q_lim, mode permissions, γ | per-user calibration (firmware `calib.c`) |

## 4. Data formats

### 4.1 Common framing (binary, little-endian)

```
file/stream header (36 B, packed): magic "PENLOG\0\1" (8 B), format_version u16 (=1), device_id u64,
                                   session_id u64, start_unix_ms u64, header_crc u16 (CRC-16/CCITT-FALSE over the first 34 B)
record: type u8 | length u8 (payload bytes) | payload | crc16 (CCITT-FALSE over type..payload)
```

Record types: 0x01 research frame, 0x02 stroke sample, 0x03 event, 0x04 calibration snapshot, 0x05 annotation.

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
| t_ms | u32 | ms since session start |
| stroke_id | u32 | monotonically increasing within session |
| x, y | i32 ×2 | 1 µm, page frame (page origin = first contact of the page session) |
| force | u16 | mN (axial) |
| theta, phi | u8 ×2 | θ in 0.5° steps (0–127.5°, used 0–90°); φ in 2° steps (0–358°). v1.0 wrote "0.5°, φ/2", which cannot fit a byte; the app and firmware both implement 2° |

`x, y` are the **deposited ink** position (stage-corrected), not the hand path. The hand-path estimate is a derived layer.

### 4.4 Event record (type 0x03)

`t_us u32 | code u16 | arg i32`. Codes: 0x0001 mode change, 0x0002 fault set (arg = fault bitmask), 0x0003 fault cleared, 0x0004 calibration applied, 0x0005 ML model loaded (arg = model hash low 32 bits), 0x0006 authority capped (arg = reason), 0x0007 pen down, 0x0008 pen up, 0x0009 timestamp wrap (arg = cumulative wrap count), 0x000A page set (arg = page id from coded paper or user action), 0x000B external sync pulse (arg = pulse counter; bench rigs, EXP-S01/B09).

### 4.5 Note store (app side, JSON)

The immutable **original layer** is the list of stroke samples exactly as logged (§4.3), content-addressed by SHA-256. **Derived layers** (never overwrite the original) each carry `layer_id`, `kind` (`recognition`, `segmentation`, `hand_path_estimate`, `user_edit`, `ai_summary`), `created_by` (algorithm id + version or `user`), `inputs` (layer ids / stroke-id ranges) and `created_utc`. Every text span in a derived layer links to the stroke ids it came from. Schema: `data/schema/note_store.schema.json`.

### 4.6 Planned for format version 2 (not yet implemented)

These come from the app workstream's cross-check against the firmware golden log and its capture-fidelity analysis (`app/README.md`, `results/app/capture_fidelity.json`):

- **Boundary samples.** Emit a stroke sample at the exact pen-down and pen-up instants in addition to the 200 Hz grid. Stroke ends dominate the format error: maximum 120.6 µm, reduced to 81.5 µm with boundary samples. Bounces shorter than 50 ms otherwise get zero or one sample.
- **Timestamps.** Derive stroke `t_ms` from a 64-bit time base. The v1 firmware derived it from the wrapping 32-bit µs counter, so it restarted every 71.6 min; the reader corrects this to within 1 ms.
- **Nib offset and uncertainty.** Add the stage offset in page coordinates (i16 ×2, 1 µm) and a position uncertainty (u8, µm) to each stroke sample, so the unassisted hand path can be reconstructed and REQ-CAP-001 met. Payload grows from 20 to 25 bytes; `stroke_id` shrinks to u16 to keep 24 bytes if needed.
- **Page identity** through event 0x000A.

## 5. Firmware ↔ ML predictor contract (v1.1)

| Item | Definition |
|---|---|
| Input | window of W = 64 samples at 250 Hz (256 ms) of housing page displacement increments Δp_H (x, y) in µm, **time-stamped at sensor acquisition** (the fusion knows each sensor's latency); float32 before quantisation. The tracked frequency f_est was dropped in v1.1: removing it did not change the result (test ratio 0.469 vs 0.475, `results/ml/train_tcn_s_nofest.json`) |
| Output | struct {d̂_x, d̂_y (µm, int16); t_acq_newest (µs, u64); expiry = t_acq_newest + 8 ms; confidence (u8, 0–255)}: predicted disturbance at horizon **h = 6 ms after the acquisition time of the newest input sample**. The guard rejects expired outputs (REQ-SAF-003, REQ-ML-002). h covers the worst-case age of a 250 Hz sample (4 ms) plus stage loop and actuation (1.33 ms, `docs/architecture.md` §3). The v1 synthetic model was trained with arrival-stamped inputs, which is equivalent to 8–9 ms and therefore conservative |
| Quantisation | int8 symmetric per-tensor weights, int8 activations, scales stored with the model; C reference kernels in `ml/export/` (bit-exact with the Python int8 reference on 20 000 windows) |
| Budget | ≤ 35 k MAC per inference, ≤ 32 kB flash weights, ≤ 8 kB RAM activations, ≤ 1 ms at 128 MHz. The v1 model uses 16.7 k MAC, 7.3 kB weights and 0.64 kB RAM. It needs CMSIS-NN kernels to meet 1 ms with margin: 0.28–0.89 ms estimated; plain C is 0.92–1.48 ms by QEMU instruction count, not cycle-accurate |
| Guard (`ml_guard.c`), v1.1 | Checks and actions: (1) NaN/Inf or int8 output saturation → reject that inference; (2) clip \|d̂\| to q_lim; (3) slew-limit d̂ at 50 mm/s; (4) a-posteriori check, comparing the prediction made h ago with the realised disturbance (fused housing displacement, band-passed 3–15 Hz) → if the running RMS error over 200 ms exceeds the running RMS of the realised disturbance (worse than predicting zero), fall back to the Kalman estimate for ≥ 1 s and log event 0x0006. The v1 rule rejecting \|d̂ − d̂_KF\| > 150 µm was removed: it rejected 18 % of ticks and cancelled the predictor's benefit (`ml/README.md`) |

## 6. Modes and safety states

`OFF → STANDBY → NEUTRAL_HOLD → ASSIST_KF | ASSIST_ML | GUIDED | TRAINING_FADE`; any state → `SAFE_PASSIVE` on a fault; `SAFE_PASSIVE → STANDBY` only after pen-up and a successful self-check. Fault bits: 0 over-current latch, 1 Hall frozen/implausible, 2 over-temperature, 3 low battery, 4 optical invalid > 300 ms, 5 watchdog reset, 6 voltage headroom (duty > 0.95 for > 50 ms), 7 charging interlock, 8 ML guard trip count exceeded.

Rules carried from simulation (results/sim/sweeps/summary.json, failure cases F1–F7):
- Never de-energise the stage while in contact except on hard faults (0, 1, 5); low-battery and thermal shutdowns wait for pen-up (timeout 5 s) after fading authority, because releasing the held contact load moves the ink by up to ~0.8 mm (F3).
- A frozen stage sensor drives the stage to its stop within tens of ms (F4); detect it within 5 ms (stuck-value and model-residual tests) and hold the last current references open-loop until pen-up.
