# Firmware baseline: stabilisation pen, research prototype Rev A

**Status: proposed design.**
- Host-tested: x86-64 with ASan and UBSan, against golden vectors from the simulator.
- Compiled and linked for the nRF5340 application core. It has **not run on hardware**.
- Executed as unit tests on QEMU `mps2-an505`, a Cortex-M33 emulator that is not cycle-accurate.

Nothing in this directory is a hardware measurement. Every number below carries its evidence label: *host test*, *QEMU execution*, *build artefact* or *proposed*. Register-level code that could not be checked against the nRF5340 or TMAG5170 documentation is marked `VERIFY`.

Contract documents:
- `docs/icd.md` v1.3 (the ML guard implements the §5 guard rules 1–4 of v1.1, rule 5 and the output expiry of contract v1.2);
- `config/parameters.yaml` v0.4.4;
- `results/sim/estimator_selection.json`;
- `results/electronics/drive_sense.json` v0.4.4 and `electronics/calcs/drive_sense.py` (sense chain, PWM, hold current, headroom);
- `electronics/gen/design_revA.py` (pin plan and fault logic);
- `results/thermal/thermal.json` (two-node thermal model).

## 1. Directory map

| Path | Content |
|---|---|
| `include/`, `core/` | Portable control core, C11. No dynamic allocation; float32 only in control code. Builds with `-Wall -Wextra -Werror -Wdouble-promotion -Wconversion -Wsign-conversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wcast-align -Wformat=2 -Wvla`. |
| `include/params_gen.h`, `.json` | 212 constants generated from the YAML, the simulator, the estimator selection and drive_sense by `tools/gen_params.py`. Do not edit. |
| `include/hal.h` | Hardware interface. The control core never touches registers. |
| `port/host/` | Host HAL, including a behavioural model of the Rev A over-current latch and the ACT_EN AND gate. |
| `port/nrf5340/` | Application-core port: start-up, linker script, register definitions, PWM→DPPI→SAADC scheduler, GPIO/WDT/time-base HAL (including the coil-former NTC on AIN3), sensor front ends and log ring. **Compile-tested only; VERIFY throughout.** |
| `port/qemu_an505/` | Start-up and linker script for running the unit tests under semihosting on QEMU `mps2-an505`, plus the instruction-count bench (`bench_an505.c`). |
| `tests/` | Test runner and 60 cases. Also contains `plant.c`, a switched-bridge coil and stage plant at PWM-clock resolution, and `vec.c`, the golden-vector reader. |
| `tests/vectors/` | Golden vectors (`PENVEC01` float32 files with JSON sidecars). Also `golden_log_v1.bin` and `golden_log_v1.json`. |
| `tools/` | Scripts: `gen_params.py`, `gen_vectors.py`, `check_inputs.py` (freshness), `pen_log.py` (independent ICD §4 decoder and encoder), `size_report.py`, `run_qemu.py`. |
| `../results/firmware/` | `test_report.txt` (host), `size_report.txt` (ARM), `qemu_report.txt` (QEMU). |

## 2. Architecture

```
 port (nRF5340)                 core/app.c (application layer)            core modules
 ─────────────────              ───────────────────────────────           ─────────────────────────────
 SAADC END IRQ (40 kHz) ──────► pen_app_current_isr()  ─────────────────► current_loop.c (PI, bridge map)
 EGU0 IRQ (2 kHz)        ─┐                                               hall.c, fusion.c
 sensors_read() ──────────┴───► pen_app_stage_tick()  ──┬───────────────► safety.c, thermal.c (two-node)
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
4. compliance-aware inverse Jacobian, with γ(θ) = r_n·sin²θ / (r_n·sin²θ + 1) evaluated at every update from the CAL_USER ratio r_n = K_n/k_ax (ICD §1 v1.3; the simulator's formula);
5. `lam_hat` (κ_s = 1);
6. radial tanh taper;
7. slew limit;
8. PID servo with reference, acceleration and contact feedforwards (contact feedforward gain 0, DEC-011);
9. `i_ref = −F/(n·K_f)`.

The replay tests prove the port against the numba simulator (section 7). Firmware-only additions are opt-in or documented:
- the estimator local origin (D9);
- the current-loop feedforward default (D10);
- the authority cap from the state machine and the thermal derating;
- the ML cross-fade and confidence scaling.

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
| Slow channels (VBAT, coil-former NTC) | every 20th stage tick (100 Hz) | the stage task enables 2 more channels for one scan (MAXCNT 6); the ISR stores them and restores MAXCNT 4. The ≈ 10 µs longer scan needs VERIFY with a logic analyser. |

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
6. at 100 Hz: battery, coil-former NTC, two-node thermal estimator and derating;
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
| Stage tick, steady assist | 11535 | 13112 | 64000 cycles per 500 µs (brief); 32000 = the ≤ 250 µs compute of ICD §2 | 20.5 % / 41.0 % |
| Stage tick, all ticks (incl. pen-down/up, events, 100 Hz ticks) | 9744 | 13112 | same | 20.5 % / 41.0 % |

Breakdown of one steady tick:
- 11385 instructions in total: Kalman estimator (both axes) 6866; research frame (pack + CRC + ring copy) 1627, of which the table CRC over the 52-byte payload is 425; everything else (Hall, fusion, safety, state machine, servo, Jacobian with γ(θ), limiter, ML window and guard, capture) about 2892

CRC history:
- the bitwise CRC-16 cost ≈ 3600 instructions per research frame;
- `crc16.c` is now table-driven (512 B of flash).

Mean load in assist is about 31 % of the 128 MHz core at CPI 1 (20 ISR calls + one stage tick per 500 µs). This is a lower bound. The ML inference itself is not included: no model is linked, and ICD §5 allows ≤ 1 ms per 4 ms.

The unit tests on QEMU ran 60 cases (1120 checks) on the Cortex-M33 code: FPv5-SP, newlib libm. 60 passed and 0 failed (0 failed checks), with the host tolerances. The run took 24 min of host time, because the test plant is soft double.

## 4. Module map to the ICD

| Module | ICD / requirement | Simulator reference | Tests |
|---|---|---|---|
| `current_loop.c` | §2 current loop (40 kHz, centre + edge sampling, ≤ 47.5 µs); §1 current sign | `core.py` current loop; `drive_sense.py` (PI design, D13) | `test_current.c`, `test_closed_loop.c` |
| `servo.c` | §1 signs; §2 stage loop; DEC-011 | `core.py` position servo | replays, `test_closed_loop.c` |
| `estimator_kf.c` | §1 d̂; §2 | `core._kf_step`, mode 3 | `test_kf.c` (step, sequences, replays) |
| `estimator_bpf.c`, `guided.c` | §1 d̂ | mode 2, mode 6 | `test_kf.c` |
| `jacobian.c` | §1 J and γ(θ) (v1.3) | `core.py` Ji00..Ji11; `model.py` γ formula; `stabpen/frames.py` | `test_filters.c` (frames vectors), `test_calib.c` (γ(θ), J_t1) |
| `limiter.c` | REQ-CTRL-004 (taper, slew) | `core.py` taper and slew | `test_filters.c` |
| `control.c` | §2 stage-loop order | `simulate()` control tick | replays |
| `fusion.c` | §1 p_H; §2 optics 1 kHz, IMU 3.84 kHz | `core.py` fusion | `test_sensing.c` |
| `hall.c` | §3 CAL_HALL (default map is an **uncalibrated placeholder**) | none | `test_sensing.c` |
| `thermal.c` | §6 bit 2; two-node model (YAML 0.4.4, `thermal.json`) | `core.py` one-node coil model (different, see D6) | `test_thermal.c` |
| `safety.c` | §6 fault bits 0–8; REQ-SAF-001/002 | failure cases F1–F7 | `test_safety.c`, `test_system.c` |
| `state_machine.c` | §6 modes, codes and policies; REQ-SAF-004; REQ-PWR-003 | none | `test_sm.c`, `test_system.c` |
| `ml_guard.c` | §5 v1.2 (rules 1–5, expiry); REQ-SAF-003 | none | `test_ml.c` |
| `log_format.c`, `crc16.c` | §4.1–4.4 (0x04/0x05 per v1.3) | none | `test_log.c`, `tools/pen_log.py` |
| `calib.c` | §3 container and CAL_USER v2 (v1 read with conversion); REQ-CTRL-007 (f0 calibration and f_gate rule) | none | `test_calib.c` |
| `app.c` | §2 order; §4 capture layer; §6 actuator policies | failure cases F1–F7 | `test_system.c` |
| `port/nrf5340/*` | §2 scheduler; Rev A pin plan (`design_revA.py sheet_mcu`) | none | compile and link only |

## 5. Parameters

`tools/gen_params.py` (run with `make params`) reads four sources:
- `config/parameters.yaml` through `stabpen.params`;
- `sim/pensim/model.py` `build_params()` and `Controller` (balanced and assertive profiles). Since model.py for YAML 0.4.3, `Controller.f_stage/pos_bw/cur_bw` default to `None` and resolve from the YAML inside `build_params()`. `gen_params.py` resolves them the same way and refuses to generate if the packed gains (Ts, Kp, Kp_i) were not built from those values;
- `results/sim/estimator_selection.json`;
- `results/electronics/drive_sense.json`, the output of `electronics/calcs/drive_sense.py`: sense chain, PWM, duty limit, design hold current and design coil temperature.

It writes `include/params_gen.h` (212 `#define`s, each with its source and status) and `params_gen.json`. The output is deterministic: no timestamps; the digests of every input are recorded. `tools/check_inputs.py` compares those digests with the current files. `make test` records the result in the report and **fails if the generated header or any vector is stale**. The upstream files changed several times during this work, so check this before trusting a report.

Current inputs:

| Input | Version / digest |
|---|---|
| YAML | 0.4.4 [a9d3d0016461d690] |
| estimator selection | [eace6b899bb37c3a]: balanced KF q_j 0.1, q_t 1e-8, w0 7 Hz, f_gate 7.5 Hz (the same values as the assertive profile) |
| `model.py` | [d8e582e84966892f] |
| `core.py` | [7b86d3e72d535bce] |
| `drive_sense.json` | [7fcbd6c40ee3b4af] |
| `docs/icd.md` | [7c379c5d77455a2f] (recorded; the ICD is not an input to the values) |

Notable values:

| Parameter | Value |
|---|---|
| K_f20 | 0.717 N/A |
| R20 | 6 Ω |
| L | 175 µH |
| r_bridge + r_shunt | 0.42 + 0.10 Ω |
| i_max / i_trip | 0.60 / 0.80 A |
| Kp_i / Ki_i | 2.20 V/A / 81.9 kV/(A·s) (ω_c = 2π·2 kHz, R at 20 °C; D13) |
| m_eq | 13.69 g (simulator geometry; YAML documents 13.7 g) |
| k_tip | 80 N/m |
| Kp / Kd / Ki | 1866 N/m / 7.23 N·s/m / 1.41e5 N/(m·s) |
| q_lim | 0.55 mm |
| slew | 0.08 m/s |
| horizon | 1.33 ms |
| r_n (default CAL_USER) | 0.4 = K_n/k_ax = 800/2000; γ(50°) = 0.190 |
| Thermal: coil → structure | R 145 K/W (`actuator.Rth_coil_amb`, key name historical), C 0.25 J/K |
| Thermal: structure → ambient | R 12.5 K/W, C 14.9 J/K; reference T_amb (25 °C) + 5.9 K with no coil loss |
| Thermal: time constants | 35.5 s and 190 s (coupled network); total 157.5 K/W |
| Design coil temperature | 96.6 °C (drive_sense v0.4.4, used by the hold-corner test) |
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
| Flash | 32.3 kB (3.1 % of 1 MB) |
| RAM | 29.4 kB (5.6 % of 512 kB), including the 16 kB stack and the 8 kB log ring |
| Control core | 20.7 kB text |
| libm | 7.5 kB |

## 7. Verification status

Evidence labels: **H** = host test (float32 code on x86-64), **Q** = QEMU execution (Cortex-M33 code, emulator), **B** = build artefact, **P** = proposed / not verified. All host cases also run on QEMU (section 3 and `qemu_report.txt`). The numbers are the host values; the QEMU run passes the same checks, with target values printed in its log (for example KF replay i_ref 22 µA vs 15 µA on the host).

| Item (brief / requirement) | Method | Status | Result |
|---|---|---|---|
| CRC-16/CCITT-FALSE | KAT "123456789", 64 vectors vs `binascii.crc_hqx`, 448 single-bit corruptions | H, Q | 0x29B1; 0 mismatches; 448/448 detected |
| Log round-trip | header and all record types packed and unpacked; unit conversions; corruption | H, Q | pass |
| Golden log | `golden_log_v1.bin` (491 B) + `golden_log_v1.json` (CAL_USER v2 snapshot, ML model hash 0xa57d81f6); the firmware writer reproduces the file byte for byte, and the independent Python decoder re-encodes it byte-identically | H, Q (C side) | pass |
| Log fixes (1)–(5) from the project lead | 64-bit t_ms, wrap-count arg, 2° φ, pen-down/up boundary samples, page-origin p_H | H, Q | all done (section 8); documented in ICD v1.3 |
| Jacobian vs `stabpen/frames.py` | 240 poses, γ = 1 closed form and 0 ≤ γ ≤ 1 numeric construction | H, Q | max error J 2.4e-7, J⁻¹ 2.1e-7 |
| γ(θ) and J_t1 vs the simulator formula (D7) | 35°, 50°, 75° through `ctrl_tick`; replays check γ(θ_scenario) = the simulator's `gamma_acc` | H, Q | \|Δγ\| ≤ 1.5e-8, relative ΔJ_t1 ≤ 4.1e-8; γ(50°) = 0.19011 |
| CAL_USER v2 and v1 conversion | round-trip (flash record and log payload); v1 records with γ 0.05–0.8; out-of-range γ | H, Q | bit-exact round-trip; v1 γ recovered within 3e-8 after r_n = γ/((1−γ)·sin²50°); γ outside 0.0116–0.854 clamped and flagged |
| Biquads vs scipy | 60 Hz feedforward filter, BP1, BP2 (`sosfilt`) | H, Q | 3.9e-6 / 3.3e-5 / 3.9e-5 |
| Limiter and slew properties | 4000 radii, 2000 random slews | H, Q | \|q\| ≤ q_lim + 4 ulp (0.5 nm); step ≤ 40 µm per tick |
| KF step vs `core._kf_step` | 114 realistic states, covariance-normalised | H, Q | dx/σ 2.6e-5, dP 9.4e-6 |
| KF sequences (balanced, assertive) | 6000 ticks, 8→10 Hz, dropout | H, Q | d̂ 9.0e-9 m, relative ω 1.4e-6; float32 P stays SPD |
| Replay of `core.simulate()` (Kalman) | inputs reconstructed from the numba closed-loop run, 2 s | H, Q | d̂ 4.7e-9 m, f 4.8e-5 Hz, g 5.5e-6, q_r 3.4e-9 m, i_ref 15 µA; authority on in 92 % of ticks |
| Replay, Kalman 4 s / 9 Hz | same, long run | H, Q | d̂ 1.8e-8 m, q_r 5.8e-9 m, i_ref 31 µA; authority on in 96 % |
| Replay, band-pass | same | H, Q | d̂ 1.7e-7 m, q_r 1.9e-7 m, i_ref 2.1 mA. Float32 DF2T on page position; tolerance 1 µm / 5 mA; standalone BPF 1.0e-7 m |
| Replay, contact feedforward (gain 1) | same | H, Q | q_r 6.0e-9 m, i_ref 19 µA |
| Current loop | switched-bridge plant, 0→0.30 A step, 3.7 V | H, Q | rise 125 µs, overshoot 13.2 %, error −0.53 mA; simulator R·i_ref form 54.7 % (D10) |
| Voltage clamp and anti-windup | 3.0 V, 85 °C, 0.6 A request | H, Q | duty 0.970, 0.361 A; recovers to 0.20 A ±5 mA in 400 µs |
| ISNS offset calibration at pen-up | +8 / −5 mA injected | H, Q | estimated 8.06 / −5.04 mA |
| Servo + current loop closed loop ("~60 Hz") | C plant: stage, coil, bridge, ADC, delayed Hall | H, Q | 50 µm step: rise 1.5 ms, overshoot 45.8 %, 2 % settling 23 ms; −3 dB at 193 Hz, peak +4.4 dB at 80 Hz. "60 Hz" is the PID natural frequency |
| Loop margins (REQ-CTRL-002) | force injection, unloaded plant | H, Q | crossover 98 Hz, **PM 35.3° (< 40°, not met; open)**, GM 10.9 dB |
| No voltage saturation at the design hold current | 0.76 N hold (0.335 A) + 0.3 mm 8 Hz correction | H, Q | 3.7 V / 25 °C: max duty 0.66. 3.3 V, coil 96.6 °C, magnets 36.1 °C (drive_sense v0.4.4 corner): DC 0.868, peaks 0.930; no clamp, below the 0.95 headroom threshold |
| Two-node thermal estimator (D6) | constant loss and constant current (copper tempco) vs closed form; 0.30 W step response; NTC preference; derating | H, Q | steady state within 0.001 K of the closed form; time constants 35.5 s / 190.1 s from the response = network eigenvalues (R·C products 36.25 s / 186.25 s); NTC preferred when valid; derate thresholds unchanged |
| Hall frozen detection < 5 ms | unit test + system test on the plant | H, Q | 4.0 ms; no false trip in 10 s. Open-loop hold drifts 33 µm in 200 ms (release would move 600 µm) |
| Fault detections | residual, range, headroom, optical, battery | H, Q | headroom 50.5 ms; optical 300.5 ms; battery 230 ms (LPF 50 ms + debounce 200 ms) |
| Over-current latch clear | host latch model (PRE/CLR/Q, AND gate) | H, Q | clears only with ACT_EN_REQ low; FAILED after 3 retries |
| State-machine table, every fault | 18 transitions; 9 fault bits × (in contact, pen-up, timeout, self-check) | H, Q | as ICD §6 (policy per bit in section 10) |
| System fault sequences (a)–(e) | app + plant + host HAL | H, Q | pass. Watchdog kicked only while the ISR runs |
| ML guard (§5 v1.2) | injected good, bad, NaN, saturated (flag and int16 full-scale value), stale and low-confidence predictors | H, Q | rules 1–3; bad predictor → fallback 38.5 ms, Kalman fully in use 20 ms later; re-admission ≥ 1 s; expiry at t_acq + 8 ms (8.5 ms at tick granularity); rule 5: byte 255 at the defaults leaves the share unchanged, byte 0 removes it within 20 ms, c_full 0.4 with byte 51 halves it within 10 ms, c_min 0.3 rejects byte 51 |
| Calibration records and f0 | 328 corruptions; Goertzel bank; gate rule | H, Q | 328/328 rejected; peak error < 0.001 Hz |
| Fusion, attitude | vs double transcription of the simulator scheme | H, Q | 1.1e-9 m; θ, ρ, φ exact |
| Capture layer | 501.5 ms stroke across a hardware counter wrap | H, Q | 102 samples incl. pen-down and pen-up; t_ms monotonic |
| ARM build | `make arm` | B | links; sizes above |
| Target timing | QEMU icount bench | Q (instructions) | section 3; cycles **not measured** |
| Register code, DPPI chain, SAADC timing, TMAG5170 frames | none possible without hardware | P | VERIFY (section 12) |

## 8. Log format notes (ICD §4)

- Encoding is explicitly little-endian (no struct overlay). Every record is `type | len | payload | CRC-16` over type..payload. The header CRC covers the first 34 B.
- Research frame: 52 B at 2 kHz; with framing this is 56 B, 112 kB/s. p_H is an i32 in 0.1 µm. `INT32_MIN` is reserved for "undefined" (before the first pen-down). `sat_i32` clamps to `INT32_MIN + 1`.
- The project lead's fixes are **all done**, within the v1 layout (format_version stays 1). ICD v1.3 §4.2, §4.3 and §4.6 now document them as implemented:
  1. stroke `t_ms` comes from a 64-bit session time base (`penlog_clock_t`), so it no longer wraps every 71.6 min;
  2. event 0x0009 arg is the cumulative wrap count;
  3. φ is a u8 in 2° steps (0–358°) and θ is in 0.5° steps;
  4. a stroke sample is emitted at the exact pen-down tick (phase reset) and at the pen-up boundary (the last in-contact tick, unless already on the 200 Hz grid);
  5. research p_H is relative to the session page origin (the ink position at the first pen-down), the same origin as stroke x/y.
- 0x04 calibration snapshot (ICD §4.1 v1.3): `rec_type u8 | cal_version u16 | payload`, where the payload is exactly the flash container's payload (no magic, length or CRC). The application logs it together with event 0x0004 when a CAL_USER record is applied. The golden log carries a CAL_USER v2 snapshot. `pen_log.py` decodes v1 (γ) and v2 (r_n) payloads, and also the earlier container-in-record form.
- 0x05 annotation: `t_us u32 | UTF-8 text` (≤ 251 B).
- Still open for format version 2 (ICD §4.6): nib offset and uncertainty in the stroke sample, and per-page origins at event 0x000A. The codes 0x000A and 0x000B are defined and decoded, but Rev A never emits them.

## 9. ML guard (ICD §5 contract v1.2)

`ml_guard.c` implements:
1. NaN/Inf or output saturation rejects that inference. Saturation means the kernel's int16 d̂ (0.1 µm) at full scale, ±3.2767 mm: the kernel's status bit (`TCN_ST_OUTPUT_SAT`) or |d̂| ≥ 3276.65 µm in the value. int8 activation saturation is not observable and not used;
2. |d̂| is clipped to q_lim;
3. d̂ is slew-limited at 50 mm/s, over acquisition-time intervals;
4. a-posteriori check: the prediction made h = 6 ms earlier is compared with the realised disturbance (fused p_H band-passed 3–15 Hz, 2nd-order Butterworth). If the 200 ms running RMS error exceeds the running RMS of the realised disturbance, the guard falls back to the Kalman estimate for ≥ 1 s and logs event 0x0006 with a reason bit;
5. confidence (v1.2): with ĉ = confidence byte / 255, the ML share of the correction is scaled by c = min(1, ĉ/c_full), slewed so that a new value is reached within 20 ms. ĉ below c_min is a rejected inference (reason bit 0x40). c_min and c_full (0–1) come with the model card (`ml_guard_set_confidence_cal()`); the defaults are 0 and 1. An uncalibrated model reports 255 (`TCN_CONFIDENCE_UNCALIBRATED`), so the rule has no effect; a byte of 0 removes all ML authority. The share is the weight of the ML estimate in its blend with the Kalman estimate: w = cross-fade × c.

The v1 rule "|d̂ − d̂_KF| > 150 µm" is **not** present.

Other behaviour:
- **Expiry**: an output expires at t_acq_newest + 8 ms (REQ-SAF-003, REQ-ML-002).
- Every fallback and re-admission is a 20 ms cross-fade.
- More than 5 trips in 10 s set fault bit 8.

Input and hook:
- The window holds 64 × (dx, dy) µm increments, oldest first, stamped at acquisition (tick time − IMU delay). There is no f_est input.
- `pen_ml_predict(dp_um, &out)` returns d̂ in float µm (the kernel's int16 0.1 µm output), the NaN/Inf and saturation status and the confidence byte. The weak default reports that no model is linked.
- The exported model is `tcn_s_nofest` (`ml/export/tcn_model.h`: TCN_CIN 2, hash low32 0xa57d81f6, 448 B scratch). Its adapter calls `tcn_predict()` with `f_est_hz = 0.0f` (ignored), maps `TCN_ST_INPUT_NAN` / `TCN_ST_OUTPUT_SAT` to the status flags and reports confidence 255. The adapter and the link of `ml/export` into the image are ML-integration work, not in this baseline.

## 10. State machine (ICD §6)

`OFF → STANDBY → NEUTRAL_HOLD → {ASSIST_KF, ASSIST_ML, GUIDED, TRAINING_FADE}`. Any state goes to `SAFE_PASSIVE` on a fault. `SAFE_PASSIVE → STANDBY` only after pen-up and a successful self-check. Arming needs the battery to be OK and the pen not to be charging. Mode permissions come from CAL_USER (bit0 ASSIST_KF, bit1 ASSIST_ML, bit2 GUIDED, bit3 TRAINING_FADE). Disarm and off take effect at pen-up, with the 30 ms ramp.

| Fault bit | Class | In contact | After pen-up (or the 5 s timeout) |
|---|---|---|---|
| 0 over-current, 5 watchdog, 7 charging | VMOT removed by hardware | coast immediately | latch clear sequence (bit 0) and self-check |
| 1 Hall frozen / implausible | hard | hold the mean of the 8 ms of current references before the stuck run, open loop | ramp 30 ms → off (pen-up from optical lift) |
| 2 thermal, 3 battery, 4 optical, 6 headroom, 8 ML | soft | fade authority, closed-loop neutral hold | ramp 30 ms → off |

Mode codes (research frame `mode` byte, event 0x0001 arg): OFF 0, STANDBY 1, NEUTRAL_HOLD 2, ASSIST_KF 3, ASSIST_ML 4, GUIDED 5, TRAINING_FADE 6, SAFE_PASSIVE 7 (adopted by ICD v1.3 §6).

## 11. Discrepancies (simulator ↔ ICD ↔ circuit) and their status

| # | Discrepancy | Status |
|---|---|---|
| D1 | ICD §1 printed J with diag(1/J_t1, 1), the inverse of the simulator's and frames.py's diag(J_t1, 1) | **resolved upstream**: ICD v1.3 §1. The firmware always followed the simulator (verified to 2e-7) |
| D2 | ICD §1 tip force +n·K_f·i vs the simulator's −n·K_f·i | **resolved upstream**: ICD v1.3 §1 (positive current = +x_H force on the paddle; tip-equivalent −n·K_f·i) |
| D3 | `design_revA.py` note described "PWM on one input, other low" as drive/brake; under the DRV8212P IN/IN truth table that is drive/coast | **resolved upstream**: `design_revA.py` note corrected (one input high, the other with inverted duty = drive/brake, slow decay); matches the firmware mapping. The truth table itself stays VERIFY |
| D4 | 0x04/0x05 payloads and the mode codes were undefined | **resolved upstream**: ICD v1.3 §4.1 and §6. The firmware now logs 0x04 as rec_type, cal_version and the container payload only |
| D5 | φ encoding "0.5° as φ/2" did not fit a u8 | **resolved upstream**: ICD v1.2/v1.3 (2° steps) |
| D6 | Coil thermal resistance: one-node 60 → 130 K/W vs the thermal network | **resolved in firmware + upstream**: YAML 0.4.3 two-node values, `thermal.c` two-node estimator. The C_coil mismatch (thermal network 0.219 J/K vs YAML 0.25 J/K) is resolved in YAML 0.4.4: `analysis/thermal.py` takes the coil node from `actuator.Cth_coil`. The simulator keeps a one-node model against ambient, which is valid for runs much shorter than 3 min |
| D7 | Simulator γ(θ) varies with tilt; the ICD stored a fixed γ | **resolved in firmware + upstream**: ICD v1.3 CAL_USER v2 stores r_n; `control.c` evaluates γ(θ) at every Jacobian update; v1 records are converted |
| D8 | Optics "2 kHz burst" (ICD) vs 1 kHz (YAML, simulator) | **resolved upstream**: ICD v1.3 §2 (1 kHz; 2 kHz if the selected sensor allows) |
| D9 | Simulator band-pass estimator re-initialises on absolute page position: up to 10.6 mm transient at optical re-acquisition | **open (simulator)**, recorded in `docs/sim_report.md`. Firmware: local-origin option, default on (9.86 mm → 0.27 mm); replays run with it off to match |
| D10 | Simulator current loop adds R·i_ref feedforward with no sample-to-PWM delay; with the Rev A timing this overshoots 55 % | **open (simulator)**, recorded in `docs/sim_report.md`. Firmware: PI only by default (`cur_r_ff = 0`, 13 % overshoot) |
| D11 | `drive_sense.py` headroom check omitted the magnet tempco and the correction force | **resolved upstream**: drive_sense v0.4.3 (per-point coil and magnet temperatures, Br tempco, correction force). Its r_ext 0.58 Ω includes 0.06 Ω of wiring; the firmware models the shared load switch separately in V_M. The host hold test now uses the same corner |
| D12 | `ml/export/tcn_int8.h` (v1 kernel) took f_est as a third input channel | **resolved upstream**: re-exported as `tcn_s_nofest` (TCN_CIN 2, hash 0xa57d81f6); `f_est_hz` is ignored and callers pass 0.0f. The firmware hook has no f_est |
| D13 (new) | Current-loop PI: drive_sense v0.4.3 designs Kp 2.57 V/A, Ki 114.7 kV/(A·s) (2.34 kHz crossover at 50° PM, pole cancelled at the hot-coil resistance); the simulator and firmware use Kp 2.20, Ki 81.9 k (YAML `current_bw` 2 kHz, R at 20 °C) | **resolved upstream** (YAML 0.4.4): `drive_sense.py` now evaluates the implemented loop (2 kHz, zero on the cold pole: Kp 2.20 V/A, Ki 81.9 kV/(A·s), 55.8° phase margin) and reports 2.34 kHz as the 50° limit. Scheduling Ki with the thermal estimate R(T) remains a cheap option if bench tests show a slow integral tail when hot |
| D14 (new) | `core.py` applies the magnet Br tempco at the **coil** temperature; drive_sense v0.4.3 uses the magnet (structure) temperature, which is far cooler (36 °C vs 97 °C at the design corner) | **resolved upstream** (YAML 0.4.4): `core.py` applies the Br tempco at the magnet temperature, which is ambient over the simulator's short runs; `actuator.alpha_B` moved to the parameter file. The simulation chain was re-run. The host hold test follows drive_sense |

## 12. Findings and open issues

**Findings** (host model; to be confirmed on the loaded hardware):
- F1: phase margin is 35.3° (< 40°, **REQ-CTRL-002 open**) on the unloaded plant with the simulator's gains. The loaded-plant analysis is pending (EXP-B05). Options are to reduce ω_c or to add phase lead.
- F2: the "~60 Hz bandwidth" is the PID natural frequency. The closed loop is −3 dB at 193 Hz, with a +4.4 dB peak at 80 Hz. The step overshoot is 46 % on feedback only; the firmware reference path applies the slew limit and the reference feedforward.
- F3: at the drive_sense v0.4.4 hot corner (3.3 V, coil 96.6 °C, magnets 36.1 °C; unchanged in v0.4.4), the design hold plus a 0.3 mm 8 Hz correction peaks at 0.930 duty, below the 0.95 threshold. The earlier 0.955 came from the pessimistic coil-temperature Br tempco (D14). drive_sense reports that the 6 Ω winding binds at 3.3 V in 0.5 % of the thermal envelope.
- F4: authority coverage: the 2 s KF replays engage authority since the estimator re-tune (q_j 0.1). The 4 s / 9 Hz replay makes coverage independent of the tuning.
- F5: the simulator does not reset `kf_init`, `phase_prev` or `nis_f` when the KF re-initialises. This is ported as is, for replay fidelity.
- F6: the stuck-value Hall detector needs ≥ 1 LSB of noise. A conversion-counter freshness check (TMAG5170 status) would be more robust (VERIFY).
- F7: float32 at 100 Hz loses per-step thermal increments near equilibrium (up to 0.05 K); the estimator uses compensated summation, and the closed-form tests now agree within 0.001 K.

**Open issues**:
- O1: nothing has run on the nRF5340. **VERIFY** before power-up:
  - `nrf5340_regs.h`: all addresses, offsets and bit fields are from memory;
  - the DPPI chain, gapless PWM looping (`LOOPSDONE → SEQSTART0`) and the EasyDMA fetch timing;
  - SAADC scan timing, the slow-scan reconfiguration and the ratiometric NTC scaling;
  - the 128 MHz clock set-up; the vendor `SystemInit` errata are not reproduced;
  - the WDT at 5 ms;
  - the linker memory sizes (no bootloader offset);
  - pin mapping and polarities (INA241 sense polarity);
  - the TMAG5170 SPI frame, CRC4 and register map.
- O2: measure real cycles with DWT CYCCNT and a GPIO toggle on a logic analyser. The QEMU numbers are instruction counts. Also measure the loop delay (target 47.5 µs) and the stage release jitter (≤ 20 µs).
- O3: REQ-CTRL-002 (F1).
- O4: only the CAL_USER record layout is defined. CAL_HALL, CAL_ACT, CAL_ISNS and CAL_AXIAL use the container but have no field layout. The Hall map is an uncalibrated placeholder (EXP-B04).
- O5: the optical sensor is not selected (EXP-S01). The port reports optics invalid, so no correction can be commanded on hardware yet. The IMU FIFO driver, the USB CDC transport, flash capture and BLE are not written.
- O6: sensor noise floors and delays: Hall noise sets the stuck detector and the residual threshold; the optical delay sets the fusion lag (FUSION_LAG_TICKS = 2).
- O7: thermal: EXP-B07 must confirm R/C values, the NTC-to-winding gradient (the estimator prefers the coil-former NTC and does not model its lag), and the r_bridge spread (±6.8 °C systematic in resistance thermometry, used only without the NTC). T_amb is the config value (25 °C); without a valid NTC a hotter room makes the open-loop model optimistic by the difference.
- O8: ML integration:
  - the adapter from `pen_ml_predict()` to `tcn_predict()` and linking `ml/export` into the nRF5340 image (7.3 kB weights, 448 B scratch);
  - ML inference cost is not in the bench; the ML workstream reports 0.92–1.48 ms in plain C by QEMU instruction count;
  - the model card must supply c_min and c_full once a confidence is calibrated (EXP-E01); until then the adapter reports 255.
- O9: log format v2 items: nib offset and uncertainty (REQ-CAP-001), and per-page origins.
- O10: v1 CAL_USER records with γ outside 0.0116–0.854 (r_n outside 0.02–10) are clamped on conversion and flagged (`from_v1_clamped`); γ = 1 (rigid page) has no finite r_n.
