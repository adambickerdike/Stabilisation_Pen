# Sim-to-real: calibration pipeline, bench time and prediction gap (twin experiments)

**Evidence status: SIMULATION and CALCULATION only.** No hardware exists and nothing here is a measurement. The "bench" is virtual: M1 (`sim/pensim`) or small standalone models with hidden true parameters, seen through measurement models of the instruments `validation/bench_protocols.md` names. Instrument numbers are copied from the protocols (PROTOCOL), the parameter file (CONFIG) or the design (DESIGN), or chosen inside the protocol's instrument class (ASSUMPTION); `s2r/instruments.py` labels each one.

**What twin experiments can and cannot show.** They show that the identification recovers parameters and states honest uncertainty, what an accuracy costs in bench time, how well a calibrated simulator predicts a plant whose structure it shares, and which residual tests catch which kinds of missing physics. They cannot show that M1's structure is right about the pen, or that its EXP-B09 predictions will hold. Every "gap" below is between two simulations; only the bench can close the question.

Code and run times: [`s2r/README.md`](../s2r/README.md). Bench procedure, data formats, gap thresholds and the HIL plan: [`validation/sim_to_real.md`](../validation/sim_to_real.md). Results: `results/s2r/*.json` (with provenance) and `fig_*.png` (stamped SIMULATION).

## 1. Answers in brief

SUMMARY_PLACEHOLDER

## 2. The virtual bench

**Hidden plants** (`s2r/truth.py`). 26 M1 keys in five groups: EXP-B03 actuator (K_f, R20, L, R_th, C_th); EXP-B05 stage (k_tip, ζ, m_eq, Hall delay, k_ax, F_pre); EXP-B01/B02 contact (μ_k, μ_s/μ_k, v_s, k_p, x_pre); hand (six EXP-B06 keys); sensors (optical noise and delay, Hall noise, IMU delay; EXP-S01/B04). The last two groups are part of the truth but are not identified here. C1/C2 use 15 plants: 10 drawn with the declared distributions inside the declared ranges, 5 with about 40 % of their keys pushed 15–50 % of the range beyond a bound (for example K_f 0.40 N/A, k_tip 29 N/m, ζ 0.5, paper 8×10⁵ N/m, optical noise 28 µm). `x_pre` has no declared range; 3–30 µm is an ASSUMPTION. The batch is committed by SHA-256 before identification (`c1_identification.json`, `truth_commitment_sha256`); the identification code sees only recorded datasets.

**Instruments** (`s2r/instruments.py`; the full table with origins is `provenance_table()`):

| Instrument | Model | Origin |
|---|---|---|
| 6-axis F/T (R1, R4) | 5 kHz; 5 mN step; 2 mN RMS; per-axis gain error U(±2 %) per session; 500 Hz mount | PROTOCOL (rate, resolution, ±2 %, ≥ 500 Hz); ASSUMPTION (noise) |
| Goniometer | session angle error U(±0.1°) | PROTOCOL bound; ASSUMPTION distribution |
| Stage encoder, capacitive probe, laser triangulation | 0.1 µm; 5 nm at 10 kHz; 0.1 µm with ±1 µm non-linearity over 1 mm | PROTOCOL; ASSUMPTION (noise) |
| Current source, 4-wire ohmmeter, DMM | ±0.1 %; ±0.02 % at 20.0 ± 0.5 °C; ±0.1 % | PROTOCOL (source, bath band, DMM); ASSUMPTION (ohmmeter) |
| Scope and current probe (R7) | 10 MS/s, 12 bit, ±1 % | PROTOCOL (probe ±1 %, bandwidth); ASSUMPTION (rate, 12 bit) |
| Thermocouples | ±0.5 °C offset | PROTOCOL |
| LDV and rig DAQ (EXP-B05) | 0.1 µm/s; ±1 % scale; 10 kS/s with a shared 4.5 kHz anti-alias | PROTOCOL (resolution); ASSUMPTION (scale, rate) |
| Force probe, tip metrology, axial load cell | 1 mN; 0.5 µm; ±5 mN | PROTOCOL classes; ASSUMPTION (noise) |
| Pen Hall (research frame) | 1 µm RMS, 0.1 µm step, 2 kHz, hidden delay | CONFIG, DESIGN |
| Pen log vs rig DAQ | clock offset U(±50 µs) | PROTOCOL §0.4 |

Session systematics (gains, offsets, angle, sync) are drawn once per session and do not average down with repeats.

**Plant/controller separation** (`s2r/twin.py`). M1 packs one parameter vector, and `model.build_params` hands overridden plant values to the controller too: the servo feedforward uses the true m_eq, k_tip and c_tip, the current reference divides by the true n·K_f, the current-loop PI is built from the true L and R20, γ from the true K_n and k_ax, the horizon from the true IMU delay. Real firmware keeps the constants it was generated with. The shim rebuilds the controller-side entries from a separate "firmware knowledge" set and passes them as layout-name overrides, which `build_params` applies last; no file under `sim/` changes. At nominal it reproduces M1 exactly (tip trajectories within 1e-17 m; `grid.csv` ratios reproduced: Kalman 1.023/0.781 and oracle 0.162/0.203 at 6/9 Hz, 0.3 mm, 12 test seeds). What it cannot separate (R feed-forward in the current loop, the slide estimate s_hat, the contact threshold) is small in these runs; the reference feedforward is matched by one scale factor over 3–15 Hz (residual 0.7–2.3 % of K_p over the 15 plants).

**Experiments, as the protocols prescribe** (deviations in `validation/sim_to_real.md` §2):

- *EXP-B03*: 4-wire R20; voltage steps on the blocked coil (16 averaged scope records); blocked force at the protocol currents {±0.1, ±0.3, ±0.6} A with 2 s holds; back-EMF at 10/20/50 Hz, ±0.5 mm; a 0.2 A thermal step read by coil resistance.
- *EXP-B05* on M1 itself as the protocol's "test build": pen clamped (1e7 N/m fixture), lifted, stage sensor frozen so the position loop is open, current injected through the servo; 10 chirps of 10 s over 1–500 Hz after a pilot chirp; ±0.03 N static test in 8 directions × 3 cycles; axial 0 → 2 N → 0, 3 cycles.
- *EXP-B01/B02* on a numba tribometer that uses M1's contact and LuGre equations with the R1 rig dynamics (vertical slide with dead weight or force axis, holder mount, platen with velocity ripple): indentation 0 → 4 → 0 N at 0.2 N/s plus a hard-flat compliance check; 20 mm strokes after a 1 s dwell at N ∈ {0.2 … 4} N; velocity steps at the 10 protocol speeds × ±t1, ±t2 × N {0.5, 1, 2} × θ {45, 60}°; slow triangular sweeps 5 µm–1 mm; 32 held-out reciprocation records at 3–15 Hz.

C1_PLACEHOLDER

C2_PLACEHOLDER

C3_PLACEHOLDER

C4_PLACEHOLDER

LIMITS_PLACEHOLDER

CHANGES_PLACEHOLDER

FILES_PLACEHOLDER
