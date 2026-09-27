# Firmware baseline: stabilisation pen, research prototype Rev A

**Status: proposed design.**
- Host-tested: x86-64 with ASan and UBSan, against golden vectors from the simulator.
- Compiled and linked for the nRF5340 application core. It has **not run on hardware**.
- Executed as unit tests on QEMU `mps2-an505`, a Cortex-M33 emulator that is not cycle-accurate.

Nothing in this directory is a hardware measurement. Every number below carries its evidence label: *host test*, *QEMU execution*, *build artefact* or *proposed*. Register-level code that could not be checked against the nRF5340 or TMAG5170 documentation is marked `VERIFY`.

Contract documents:
- `docs/icd.md` v1.2 (the ML guard implements the §5 v1.1 rules plus the v1.2 output expiry);
- `config/parameters.yaml` v0.4.2;
- `results/sim/estimator_selection.json`;
- `electronics/gen/design_revA.py` (pin plan and fault logic);
- `electronics/calcs/drive_sense.py` (current-loop design).

## 1. Directory map

| Path | Content |
|---|---|
| `include/`, `core/` | Portable control core, C11. No dynamic allocation; float32 only in control code. Builds with `-Wall -Wextra -Werror -Wdouble-promotion -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wcast-align -Wformat=2 -Wvla`. |
| `include/params_gen.h`, `.json` | 202 constants generated from the YAML, the simulator and the estimator selection by `tools/gen_params.py`. Do not edit. |
| `include/hal.h` | Hardware interface. The control core never touches registers. |
| `port/host/` | Host HAL, including a behavioural model of the Rev A over-current latch and the ACT_EN AND gate. |
| `port/nrf5340/` | Application-core port: start-up, linker script, register definitions, PWM→DPPI→SAADC scheduler, GPIO/WDT/time-base HAL, sensor front ends and log ring. **Compile-tested only; VERIFY throughout.** |
| `port/qemu_an505/` | Start-up and linker script for running the unit tests under semihosting on QEMU `mps2-an505`, plus the instruction-count bench (`bench_an505.c`). |
| `tests/` | Test runner and 56 cases. Also contains `plant.c`, a switched-bridge coil and stage plant at PWM-clock resolution, and `vec.c`, the golden-vector reader. |
| `tests/vectors/` | Golden vectors (`PENVEC01` float32 files with JSON sidecars). Also `golden_log_v1.bin` and `golden_log_v1.json`. |
| `tools/` | Scripts: `gen_params.py`, `gen_vectors.py`, `check_inputs.py` (freshness), `pen_log.py` (independent ICD §4 decoder and encoder), `size_report.py`, `run_qemu.py`. |
| `../results/firmware/` | `test_report.txt` (host), `size_report.txt` (ARM), `qemu_report.txt` (QEMU). |

## 2. Architecture

```
 port (nRF5340)                 core/app.c (application layer)            core modules
 ─────────────────              ───────────────────────────────           ─────────────────────────────
 SAADC END IRQ (40 kHz) ──────► pen_app_current_isr()  ─────────────────► current_loop.c (PI, bridge map)
 EGU0 IRQ (2 kHz)        ─┐                                               hall.c, fusion.c
 sensors_read() ──────────┴───► pen_app_stage_tick()  ──┬───────────────► safety.c, thermal.c
                                                        ├───────────────► state_machine.c
                                                        ├───────────────► control.c ─► estimator_kf.c / estimator_bpf.c /
                                                        │                               guided.c, jacobian.c, limiter.c, servo.c
                                                        ├───────────────► ml_guard.c (window, guard)
 board_log_sink() ◄── ring ◄────────────────────────────┴───────────────► log_format.c, crc16.c (capture layer)
 main loop: WFI, drain the ring to USB CDC (transport not implemented)    calib.c (records, f0 calibration)
```

The control core (`core/control.c`, `ctrl_tick()`) is a line-by-line port of the control tick of `sim/pensim/core.py` `simulate()`. It runs these steps in order:
1. estimator (Kalman oscillator, band-pass, guided, or ML via the guard);
2. authority smoothing;
3. axial compensation;
4. compliance-aware inverse Jacobian with γ;
5. `lam_hat` (κ_s = 1);
6. radial tanh taper;
7. slew limit;
8. PID servo with reference, acceleration and contact feedforwards (contact feedforward gain 0, DEC-011);
9. `i_ref = −F/(n·K_f)`.

The replay tests prove the port against the numba simulator (section 7). Firmware-only additions are opt-in or documented:
- the estimator local origin (D9);
- the current-loop feedforward default (D10);
- the authority cap from the state machine and the thermal derating;
- the ML cross-fade.

## 3. Timing: interrupts and the stage task (proposed design, `port/nrf5340/scheduler.c`, VERIFY)

There is one clock domain: the PWM timer (ICD §2).

| Event | Time in the 25 µs PWM period | Mechanism |
|---|---|---|
| PWM0 period | 0–25 µs | 16 MHz, up/down counter, COUNTERTOP 200, 4 channels (IN1/IN2 × x, y); the drive phase is centred on 12.5 µs |
| TIMER1 CLEAR | 0 | DPPI ch0 from PWM0 PWMPERIODEND |
| Centre scan (ISNS_X, ISNS_Y) | TIMER1 CC0 = 7.0 µs → conversions straddle 12.5 µs | DPPI ch1 → SAADC SAMPLE (TACQ 3 µs + 2 µs per channel) |
| Edge scan | CC1 = 19.5 µs → conversions straddle the period boundary (middle of the brake phase) | DPPI ch1 → SAADC SAMPLE |
| SAADC END (4 results) | ≈ 4.5 µs into the next period | DPPI ch3 → SAADC START (re-arm); END IRQ, priority 1 → **current loop** |
| New duty | written by the ISR, fetched by the PWM EasyDMA at the start of period n+2 | sample-to-update 37.5 µs; with the 10 µs anti-alias filter this is the 47.5 µs loop delay of the ICD |
| Stage tick | every 20th period (2 kHz) | TIMER2 counts PWMPERIODEND, CC0 = 20 with the clear short → DPPI ch2 → EGU0 TRIGGER0 → EGU0 IRQ, priority 3 → **stage task**. Release jitter is interrupt latency only. |
| Slow channels (VBAT, NTC) | every 20th stage tick (100 Hz) | the stage task enables 2 more channels for one scan (MAXCNT 6); the ISR stores them and restores MAXCNT 4. The ≈ 10 µs longer scan needs VERIFY with a logic analyser. |

Aggregate SAADC rate is 160 kS/s + 200 S/s, against the 200 kS/s limit (DEC-010, VERIFY).

**Current ISR** (`pen_app_current_isr`, 40 kHz):
- centre and edge samples → per-axis PI with a voltage clamp at `duty_max·V_M`, where `V_M = VBAT − R_ls·Σ|i|`, and conditional-integration anti-windup;
- duty quantised to 1/200 with error-feedback dither → DRV8212P IN/IN drive/brake mapping (D3);
- accumulators for the stage task.

**Stage task** (`pen_app_stage_tick`, 2 kHz), in order:
1. 64-bit session clock (wrap event);
2. swap of the ISR accumulators inside a short critical section;
3. Hall conversion and Hall checks;
4. fusion (optics + IMU, simulator scheme) and attitude;
5. contact and pen-up; during a Hall fault, pen-up comes from optical lift, because F_ax comes from the same sensor;
6. at 100 Hz: battery, NTC, thermal observer and derating;
7. remaining fault detections;
8. ML: realised-disturbance band-pass, window push and inference at 250 Hz, guard;
9. over-current clear sequence;
10. state machine and events;
11. `ctrl_tick`;
12. actuator policy (servo, neutral, hold open-loop, ramp 30 ms, off), then ACT_EN_REQ and DRV_SLEEP_N;
13. watchdog kick, only while the ISR is alive;
14. research frame;
15. capture layer (stroke samples).

**Instruction counts** (*QEMU execution*: `results/firmware/qemu_report.txt`, `port/qemu_an505/bench_an505.c`). Method: `-icount` makes the SysTick count executed instructions, calibrated with a loop of known length. The scenario is the closed-loop C plant in ASSIST_KF with 9 Hz tremor, authority engaged and research logging on. These are **instructions, not cycles**, measured on a non-cycle-accurate emulator. Real cycles are higher: loads, VDIV/VSQRT (14 cycles), branches, flash wait states, exception entry and exit, and the port code are not included.

| Body | Mean | Max | Budget (128 MHz) | Max / budget at CPI 1 |
|---|---|---|---|---|
| Current ISR | 422 | 446 | 3200 cycles per 25 µs | 14.0 % |
| Stage tick, steady assist | 11390 | 12893 | 64000 cycles per 500 µs (brief); 32000 = the ≤ 250 µs compute of ICD §2 | 20.1 % / 40.3 % |
| Stage tick, all ticks (incl. pen-down/up, events, 100 Hz ticks) | 9599 | 12893 | same | 20.1 % / 40.3 % |

Breakdown of one steady tick:
- 11244 instructions in total: Kalman estimator (both axes) 6866; research frame (pack + CRC + ring copy) 1631, of which the table CRC over the 52-byte payload is 425; everything else (Hall, fusion, safety, state machine, servo, Jacobian, limiter, ML window and guard, capture) about 2747

CRC history:
- the bitwise CRC-16 cost ≈ 3600 instructions per research frame;
- `crc16.c` is now table-driven (512 B of flash).

Mean load in assist is about 31 % of the 128 MHz core at CPI 1 (20 ISR calls + one stage tick per 500 µs). This is a lower bound. The ML inference itself is not included: no model is linked, and ICD §5 allows ≤ 1 ms per 4 ms.

The unit tests on QEMU run all 56 cases (1053 checks) on the Cortex-M33 code: FPv5-SP, newlib libm. All pass with the host tolerances. Values agree with the host to the printed precision; the Jacobian vs frames.py error is 2.7e-7 on target vs 2.4e-7 on host, a libm difference. The run takes about 24 min of host time, because the test plant is soft double.

## 4. Module map to the ICD

| Module | ICD / requirement | Simulator reference | Tests |
|---|---|---|---|
| `current_loop.c` | §2 current loop (40 kHz, centre + edge sampling, ≤ 47.5 µs); §1 current sign | `core.py` current loop; `drive_sense.py` (PI design) | `test_current.c`, `test_closed_loop.c` |
| `servo.c` | §1 signs (D2); §2 stage loop; DEC-011 | `core.py` position servo | replays, `test_closed_loop.c` |
| `estimator_kf.c` | §1 d̂; §2 | `core._kf_step`, mode 3 | `test_kf.c` (step, sequences, replays) |
| `estimator_bpf.c`, `guided.c` | §1 d̂ | mode 2, mode 6 | `test_kf.c` |
| `jacobian.c` | §1 J (D1); §3 γ from CAL_USER | `core.py` Ji00..Ji11; `stabpen/frames.py` | `test_filters.c` (frames vectors) |
| `limiter.c` | REQ-CTRL-004 (taper, slew) | `core.py` taper and slew | `test_filters.c` |
| `control.c` | §2 stage-loop order | `simulate()` control tick | replays |
| `fusion.c` | §1 p_H; §2 optics and IMU rates (D8) | `core.py` fusion | `test_sensing.c` |
| `hall.c` | §3 CAL_HALL (default map is an **uncalibrated placeholder**) | none | `test_sensing.c` |
| `thermal.c` | §6 bit 2; D6 | none (firmware observer) | `test_thermal.c` |
| `safety.c` | §6 fault bits 0–8; REQ-SAF-001/002 | failure cases F1–F7 | `test_safety.c`, `test_system.c` |
| `state_machine.c` | §6 modes and policies; REQ-SAF-004; REQ-PWR-003 | none | `test_sm.c`, `test_system.c` |
| `ml_guard.c` | §5 v1.1 guard rules, v1.2 expiry; REQ-SAF-003 | none | `test_ml.c` |
| `log_format.c`, `crc16.c` | §4.1–4.4 (0x04 and 0x05 payloads proposed, D4) | none | `test_log.c`, `tools/pen_log.py` |
| `calib.c` | §3 container and CAL_USER; REQ-CTRL-007 (f0 calibration and f_gate rule) | none | `test_calib.c` |
| `app.c` | §2 order; §4 capture layer; §6 actuator policies | failure cases F1–F7 | `test_system.c` |
| `port/nrf5340/*` | §2 scheduler; Rev A pin plan (`design_revA.py sheet_mcu`) | none | compile and link only |

## 5. Parameters

`tools/gen_params.py` (run with `make params`) reads four sources:
- `config/parameters.yaml` through `stabpen.params`;
- `sim/pensim/model.py` `build_params()` and `Controller` (balanced and assertive profiles);
- `results/sim/estimator_selection.json`;
- `results/electronics/drive_sense.json`, the output of `electronics/calcs/drive_sense.py`: sense chain, PWM, duty limit and design hold current.

It writes `include/params_gen.h` (202 `#define`s, each with its source and status) and `params_gen.json`. The output is deterministic: no timestamps; the digests of every input are recorded. `tools/check_inputs.py` compares those digests with the current files. `make test` records the result in the report and **fails if the generated header or any vector is stale**. The upstream files changed several times during this work, so check this before trusting a report.

Current inputs:

| Input | Version / digest |
|---|---|
| YAML | 0.4.2 [62292f1efdb00e0f] |
| estimator selection | [ecd777b4a7ae9117]: balanced KF q_j 0.1, q_t 1e-8, w0 7 Hz, f_gate 7.5 Hz (the same values as the assertive profile) |
| `model.py` | [2bcbc83194379333] |
| `core.py` | [c46570f25d1439cb] |

Notable values:

| Parameter | Value |
|---|---|
| K_f20 | 0.717 N/A |
| R20 | 6 Ω |
| L | 175 µH |
| r_bridge + r_shunt | 0.42 + 0.10 Ω |
| i_max / i_trip | 0.60 / 0.80 A |
| Kp_i / Ki_i | 2.20 V/A / 81.9 kV/(A·s) (ω_c = 2π·2 kHz) |
| m_eq | 13.69 g (simulator geometry; YAML now documents 13.7 g) |
| k_tip | 80 N/m (v0.4.2) |
| Kp / Kd / Ki | 1866 N/m / 7.23 N·s/m / 1.41e5 N/(m·s) |
| q_lim | 0.55 mm |
| slew | 0.08 m/s |
| horizon | 1.33 ms |
| R_th | 130 K/W |
| **ff_contact** | **0.0 (DEC-011)** |

The contact feedforward path (N̂ = F_ax/sin θ through a 60 Hz, 2nd-order biquad) is kept behind that gain; the FFC replay proves it at gain 1.

## 6. Build and test

Prerequisites (versions used):
- gcc 13.3;
- arm-none-eabi-gcc 13.2.1 with newlib and newlib-nano;
- qemu-system-arm 8.2.2;
- Python 3 with numpy, scipy and numba, for the generators only. The generators import `sim/` and `stabpen/` read-only. They set `NUMBA_CACHE_DIR=firmware/build/numba_cache` and never write bytecode outside `firmware/`.

```
make params     # regenerate include/params_gen.h from the YAML (after upstream changes)
make vectors    # regenerate golden vectors, golden_log_v1.bin/.json, and verify the JSON with pen_log.py
make test       # host unit tests (ASan + UBSan) + input freshness -> results/firmware/test_report.txt
make arm        # nRF5340 image + results/firmware/size_report.txt
make qemu       # unit tests + instruction-count bench on qemu-system-arm -M mps2-an505
                # -> results/firmware/qemu_report.txt (takes tens of minutes: the plant is soft double)
make all        # test + arm + qemu      (use at most make -j2 on shared machines)
```

Useful direct invocations:
- `build/host/pen_tests tests/vectors <filter>` runs a subset of the cases.
- `tools/gen_vectors.py --only replay_kf_auth` regenerates one vector group.
- `tools/pen_log.py decode <bin> --json <out>` decodes a log to JSON.
- `tools/pen_log.py verify <bin> <json>` checks a log against its JSON.

**Size** (*build artefact*, `results/firmware/size_report.txt`, `-O2`, newlib-nano, `--gc-sections`):

| Item | Size |
|---|---|
| Flash | 31.6 kB (3.0 % of 1 MB) |
| RAM | 29.4 kB (5.6 % of 512 kB), including the 16 kB stack and the 8 kB log ring |
| Control core | 20.0 kB text |
| libm | 7.5 kB |

## 7. Verification status

Evidence labels: **H** = host test (float32 code on x86-64), **Q** = QEMU execution (Cortex-M33 code, emulator), **B** = build artefact, **P** = proposed / not verified. All host cases also run on QEMU (section 3 and `qemu_report.txt`).

| Item (brief / requirement) | Method | Status | Result |
|---|---|---|---|
| CRC-16/CCITT-FALSE | KAT "123456789", 64 vectors vs `binascii.crc_hqx`, 448 single-bit corruptions | H, Q | 0x29B1; 0 mismatches; 448/448 detected |
| Log round-trip | header and all record types packed and unpacked; unit conversions; corruption | H, Q | pass |
| Golden log | `golden_log_v1.bin` (502 B) + `golden_log_v1.json`; the firmware writer reproduces the file byte for byte, and the independent Python decoder re-encodes it byte-identically | H, Q (C side) | pass |
| Log fixes (1)–(5) from the project lead | 64-bit t_ms, wrap-count arg, 2° φ, pen-down/up boundary samples, page-origin p_H | H | all done (section 8) |
| Jacobian vs `stabpen/frames.py` | 240 poses, γ = 1 closed form and 0 ≤ γ ≤ 1 numeric construction | H, Q | max error J 2.4e-7, J⁻¹ 2.1e-7 |
| Biquads vs scipy | 60 Hz feedforward filter, BP1, BP2 (`sosfilt`) | H, Q | 3.9e-6 / 3.3e-5 / 3.9e-5 |
| Limiter and slew properties | 4000 radii, 2000 random slews | H, Q | \|q\| ≤ q_lim + 4 ulp (0.5 nm); step ≤ 40 µm per tick |
| KF step vs `core._kf_step` | 114 realistic states, covariance-normalised | H, Q | dx/σ 2.6e-5, dP 9.4e-6 |
| KF sequences (balanced, assertive) | 6000 ticks, 8→10 Hz, dropout | H, Q | d̂ 9.0e-9 m, relative ω 1.4e-6; float32 P stays SPD |
| Replay of `core.simulate()` (Kalman) | inputs reconstructed from the numba closed-loop run, 2 s | H, Q | d̂ 5.5e-9 m, f 4.8e-5 Hz, g 5.1e-6, q_r 3.4e-9 m, i_ref 25 µA; authority on in 92 % of ticks |
| Replay, Kalman 4 s / 9 Hz (new) | same, long run | H, Q | d̂ 1.7e-8 m, q_r 5.8e-9 m, i_ref 33 µA; authority on in 96 % |
| Replay, band-pass | same | H, Q | d̂ 1.6e-7 m, q_r 1.6e-7 m, i_ref 1.65 mA. Float32 DF2T on page position; tolerance 1 µm / 5 mA; standalone BPF 1.0e-7 m |
| Replay, contact feedforward (gain 1) | same | H, Q | q_r 6.0e-9 m, i_ref 18 µA |
| Current loop | switched-bridge plant, 0→0.30 A step, 3.7 V | H, Q | rise 125 µs, overshoot 13.2 %, error −0.53 mA; simulator R·i_ref form 54.7 % (D10) |
| Voltage clamp and anti-windup | 3.0 V, 85 °C, 0.6 A request | H, Q | duty 0.970, 0.361 A; recovers to 0.20 A ±5 mA in 400 µs |
| ISNS offset calibration at pen-up | +8 / −5 mA injected | H, Q | estimated 8.06 / −5.04 mA |
| Servo + current loop closed loop ("~60 Hz") | C plant: stage, coil, bridge, ADC, delayed Hall | H, Q | 50 µm step: rise 1.5 ms, overshoot 45.8 %, 2 % settling 23 ms; −3 dB at 193 Hz, peak +4.4 dB at 80 Hz. "60 Hz" is the PID natural frequency |
| Loop margins (REQ-CTRL-002) | force injection, unloaded plant | H, Q | crossover 98 Hz, **PM 35.3° (< 40°, not met)**, GM 10.9 dB |
| No voltage saturation at the design hold current | 0.76 N hold (0.335 A) + 0.3 mm 8 Hz correction | H, Q | 3.7 V / 25 °C: max duty 0.66, no clamp. 3.3 V / 85 °C: DC 0.894, peaks 0.955 (above the 0.95 threshold for 0.5 ms; no clamp; no headroom fault) |
| Hall frozen detection < 5 ms | unit test + system test on the plant | H, Q | 4.0 ms; no false trip in 10 s. Open-loop hold drifts 33 µm in 200 ms (release would move 600 µm) |
| Fault detections | residual, range, headroom, optical, battery | H, Q | headroom 50.5 ms; optical 300.5 ms; battery 230 ms (LPF 50 ms + debounce 200 ms) |
| Over-current latch clear | host latch model (PRE/CLR/Q, AND gate) | H, Q | clears only with ACT_EN_REQ low; FAILED after 3 retries |
| State-machine table, every fault | 18 transitions; 9 fault bits × (in contact, pen-up, timeout, self-check) | H, Q | as ICD §6 (policy per bit in section 10) |
| System fault sequences (a)–(e) | app + plant + host HAL | H, Q | pass. Watchdog kicked only while the ISR runs |
| ML guard (§5 v1.1 + v1.2 expiry) | injected good, bad, NaN, saturated and stale predictors | H, Q | rules 1–3; bad predictor → fallback 38.5 ms, Kalman fully in use 20 ms later; re-admission ≥ 1 s; expiry at t_acq + 8 ms (8.5 ms at tick granularity) |
| Calibration records and f0 | 328 corruptions; Goertzel bank; gate rule | H, Q | 328/328 rejected; peak error < 0.001 Hz |
| Fusion, attitude | vs double transcription of the simulator scheme | H, Q | 1.1e-9 m; θ, ρ, φ exact |
| Capture layer | 501.5 ms stroke across a hardware counter wrap | H, Q | 102 samples incl. pen-down and pen-up; t_ms monotonic |
| ARM build | `make arm` | B | links; sizes above |
| Target timing | QEMU icount bench | Q (instructions) | section 3; cycles **not measured** |
| Register code, DPPI chain, SAADC timing, TMAG5170 frames | none possible without hardware | P | VERIFY (section 12) |

## 8. Log format notes (ICD §4)

- Encoding is explicitly little-endian (no struct overlay). Every record is `type | len | payload | CRC-16` over type..payload. The header CRC covers the first 34 B.
- Research frame: 52 B at 2 kHz; with framing this is 56 B, 112 kB/s. p_H is an i32 in 0.1 µm. `INT32_MIN` is reserved for "undefined" (before the first pen-down). `sat_i32` clamps to `INT32_MIN + 1`.
- The project lead's fixes are **all done**, within the v1 layout (format_version stays 1):
  1. stroke `t_ms` comes from a 64-bit session time base (`penlog_clock_t`), so it no longer wraps every 71.6 min;
  2. event 0x0009 arg is the cumulative wrap count;
  3. φ is a u8 in 2° steps (0–358°) and θ is in 0.5° steps; ICD v1.2 now says the same (D5 resolved);
  4. a stroke sample is emitted at the exact pen-down tick (phase reset) and at the pen-up boundary (the last in-contact tick, unless already on the 200 Hz grid);
  5. research p_H is relative to the session page origin (the ink position at the first pen-down), the same origin as stroke x/y. ICD v1.2 §1 adopted this.
- ICD §4.6 (format v2) lists boundary samples and the 64-bit t_ms as future work. Both are already implemented without a layout change. Nib offset and uncertainty in the stroke sample, and emission of event 0x000A (page set), are **not** implemented. The codes 0x000A and 0x000B are defined and decoded, but Rev A never emits them.
- 0x04 calibration snapshot: `cal_type u8 | cal_version u16 | record bytes`. 0x05 annotation: `t_us u32 | UTF-8`. Both are **proposed** (D4).

## 9. ML guard (ICD §5)

`ml_guard.c` implements the **v1.1 rule set**:
1. NaN/Inf or int8 saturation rejects that inference;
2. |d̂| is clipped to q_lim;
3. d̂ is slew-limited at 50 mm/s, over acquisition-time intervals;
4. a-posteriori check: the prediction made h = 6 ms earlier is compared with the realised disturbance (fused p_H band-passed 3–15 Hz, 2nd-order Butterworth). If the 200 ms running RMS error exceeds the running RMS of the realised disturbance, the guard falls back to the Kalman estimate for ≥ 1 s and logs event 0x0006 with a reason bit;
5. the v1 rule "|d̂ − d̂_KF| > 150 µm" is **not** present.

The input window holds 64 × (dx, dy) µm increments, oldest first. Samples are stamped at acquisition (tick time − IMU delay). f_est is not an input.

Additions:
- **v1.2 expiry**: an output expires at t_acq_newest + 8 ms (REQ-SAF-003, REQ-ML-002);
- every fallback and re-admission is a 20 ms cross-fade;
- more than 5 trips in 10 s set fault bit 8.

The kernel's confidence byte (ICD v1.2 output struct) is not consumed: no v1.1 rule uses it (open issue O8).

## 10. State machine (ICD §6)

`OFF → STANDBY → NEUTRAL_HOLD → {ASSIST_KF, ASSIST_ML, GUIDED, TRAINING_FADE}`. Any state goes to `SAFE_PASSIVE` on a fault. `SAFE_PASSIVE → STANDBY` only after pen-up and a successful self-check. Arming needs the battery to be OK and the pen not to be charging. Mode permissions come from CAL_USER. Disarm and off take effect at pen-up, with the 30 ms ramp.

| Fault bit | Class | In contact | After pen-up (or the 5 s timeout) |
|---|---|---|---|
| 0 over-current, 5 watchdog, 7 charging | VMOT removed by hardware | coast immediately | latch clear sequence (bit 0) and self-check |
| 1 Hall frozen / implausible | hard | hold the mean of the 8 ms of current references before the stuck run, open loop | ramp 30 ms → off (pen-up from optical lift) |
| 2 thermal, 3 battery, 4 optical, 6 headroom, 8 ML | soft | fade authority, closed-loop neutral hold | ramp 30 ms → off |

The numeric mode codes (0–7) in the research frame are **proposed** (O3).

## 11. Discrepancies found (simulator ↔ ICD ↔ circuit)

| # | Discrepancy | Firmware choice |
|---|---|---|
| D1 | ICD §1 gives J = Rot(φ)·diag(**1/J_t1**, 1)·Rot(ρ); `core.py` and `frames.py` use diag(**J_t1**, 1) (still so in ICD v1.2) | follows the simulator and frames.py (verified to 2e-7) |
| D2 | ICD §1: force at tip = **+**n·K_f·i; simulator: stage force = **−**n·K_f·i | follows the simulator (`i_ref = −F/(n·K_f)`); ICD sign to be corrected, or the port inverted, at bring-up |
| D3 | `design_revA.py` note: "PWM on one input, other low = drive/brake (slow decay)". Under the DRV8212P IN/IN truth table (00 coast, 11 brake) that is drive/**coast** | IN1 = 1, IN2 = brake-phase PWM (drive/brake), drive phase centred. VERIFY against the datasheet |
| D4 | ICD §4.1 lists record types 0x04 and 0x05 without payloads; §4.2 `mode` byte codes undefined | proposed layouts and numbering |
| D5 | ICD v1.0 §4.3 φ "0.5° as φ/2" does not fit a u8 | 2° steps; **resolved in ICD v1.2** |
| D6 | R_th coil: YAML v0.4.2 130 K/W (was 60). The design case of `results/thermal/thermal.json` (0.31 W → 85.5 °C coil over a 33 °C hand) implies ~170 K/W | uses the YAML value; the observer's I²R model must be fitted in EXP-B07 |
| D7 | Simulator γ(θ) = K_n·sin²θ/(K_n·sin²θ + k_ax) varies with tilt; the ICD stores a fixed γ in CAL_USER | fixed calibrated γ; suggest storing K_n, k_ax |
| D8 | Optics: ICD "2 kHz burst" vs YAML opt_rate 1 kHz; force 1 kHz. The IMU is now consistent (3.84 kHz in ICD v1.2) | fusion follows the simulator (sample-and-hold at the optical rate) |
| D9 | Simulator band-pass estimator re-initialises on absolute page position: up to 10.6 mm transient at optical re-acquisition, inflating the BPF baseline | local-origin option, default on (9.86 mm → 0.27 mm); replays run with it off to match |
| D10 | Simulator current loop adds R·i_ref feedforward with no sample-to-PWM delay; with the Rev A timing this overshoots 55 % | PI only by default (`cur_r_ff = 0`, 13 % overshoot) |
| D11 | `drive_sense.py` headroom check omits the magnet tempco (K_f −8 % at 85 °C) and the correction force; it also uses r_ext 0.58 Ω vs 0.52 Ω in YAML/simulator | reported (the hold test shows 0.955 peaks at the corner) |
| D12 | `ml/export/tcn_int8.h` (v1 kernel) still takes f_est as a third input channel (`TCN_CIN 3`), against ICD §5 v1.1 | `pen_ml_predict()` hook passes 64 × (dx, dy) only; the adapter needs the retrained no-f_est export |

## 12. Findings and open issues

**Findings** (host model; to be confirmed on the loaded hardware):
- F1: phase margin is 35° (< 40°, REQ-CTRL-002) on the unloaded plant with the simulator's gains. The loaded-plant analysis is pending (EXP-B05). Options are to reduce ω_c or to add phase lead.
- F2: the "~60 Hz bandwidth" is the PID natural frequency. The closed loop is −3 dB at 193 Hz, with a +4.4 dB peak at 80 Hz. The step overshoot is 46 % on feedback only; the firmware reference path applies the slew limit and the reference feedforward.
- F3: at the 3.3 V / 85 °C corner the hold plus correction touches 0.955 duty, briefly above the 0.95 headroom threshold (D11).
- F4: the KF replays of the 2 s scenarios engage authority only since the estimator re-tune (q_j 0.1). Under the earlier tuning, f_est stayed below the gate and g_eff was 0 there. The 4 s / 9 Hz replay was added so that authority coverage does not depend on the tuning.
- F5: the simulator does not reset `kf_init`, `phase_prev` or `nis_f` when the KF re-initialises. This is ported as is, for replay fidelity; the simulator owners should decide.
- F6: the stuck-value Hall detector needs ≥ 1 LSB of noise. A conversion-counter freshness check (TMAG5170 status) would be more robust (VERIFY).
- F7: `sim/pensim/model.py` takes `pos_bw` (60 Hz) and `cur_bw` (2 kHz) from `Controller` defaults, not from the YAML `control.pos_bw` / `control.current_bw`. The values are equal today. `gen_params.py` records both and flags any mismatch.

**Open issues**:
- O1: nothing has run on the nRF5340. **VERIFY** before power-up:
  - `nrf5340_regs.h`: all addresses, offsets and bit fields are from memory;
  - the DPPI chain, gapless PWM looping (`LOOPSDONE → SEQSTART0`) and the EasyDMA fetch timing;
  - SAADC scan timing and the slow-scan reconfiguration;
  - the 128 MHz clock set-up; the vendor `SystemInit` errata are not reproduced;
  - the WDT at 5 ms;
  - the linker memory sizes (no bootloader offset);
  - pin mapping and polarities (INA241 sense polarity);
  - the TMAG5170 SPI frame, CRC4 and register map.
- O2: measure real cycles with DWT CYCCNT and a GPIO toggle on a logic analyser. The QEMU numbers are instruction counts. Also measure the loop delay (target 47.5 µs) and the stage release jitter (≤ 20 µs).
- O3: mode numbering and the 0x04/0x05 payloads are proposed (D4); the ICD should adopt or replace them.
- O4: only the CAL_USER record layout is defined. CAL_HALL, CAL_ACT, CAL_ISNS and CAL_AXIAL use the container but have no field layout. The Hall map is an uncalibrated placeholder (EXP-B04).
- O5: the optical sensor is not selected (EXP-S01). The port reports optics invalid, so no correction can be commanded on hardware yet. The IMU FIFO driver, the USB CDC transport, flash capture and BLE are not written.
- O6: sensor noise floors and delays: Hall noise sets the stuck detector and the residual threshold; the optical delay sets the fusion lag (FUSION_LAG_TICKS = 2).
- O7: thermal observer parameters (R_th, C_th, NTC coupling) and the r_bridge spread (±6.8 °C systematic in resistance thermometry) need EXP-B07.
- O8: ML integration:
  - the export adapter (D12);
  - REQ-SAF-003 mentions "low-confidence" outputs, but ICD §5 defines no confidence rule, so the confidence byte is unused;
  - ML inference cost is not in the bench; the ML workstream reports 0.92–1.48 ms in plain C by QEMU instruction count.
- O9: log format v2 items: nib offset and uncertainty (REQ-CAP-001), and the page-id event.
- O10: γ(θ) handling (D7) and the contact-feedforward option (DEC-011, off) remain design questions for the bench.
