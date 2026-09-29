# Rev J in the physics simulator: closed-loop study, round 2 (DRAFT, runs in progress)

Status: DRAFT written while the test runs are going. Sections marked (pending) wait for their runs.
Every number here is a SIMULATION (sim2, MuJoCo 3.6) or a CALCULATION on synthetic writers and synthetic tremor.
Nothing was built or measured. sim2 ranks concepts (context of use COU-1, docs/sim_v2.md §8.1) until EXP-V01, EXP-V02
and EXP-V04 calibrate it and EXP-V05 validates it. These results are not evidence of benefit to people.

## 1. What was simulated

- **Simulator.** sim2 (MuJoCo 3.6): H1 contact law at the ball and the skid ring, H1 hand (HAP-26 lumped grip and
  arm) and, for a subset, sim2's articulated 'arm' hand. Step 50 µs (sim2 §5.3: 0.66 µm against 12.5 µs; a 25 µs check
  is in §9).
- **Pen.** The lead's Rev J integration, read at run time from `results/revJ/sim_params.json` and
  `results/revJ/layout.json` (CALC on a PROPOSED DESIGN). The version used is recorded in every result file
  (`pen_source`: generation time and SHA-256).

| Part | Value used (label) |
|---|---|
| Handle incl. heel drive | 68.89 g, centre of mass 89.8 mm from the tip, 8.53·10⁻⁵ kg·m² transverse (CALC, matches the lead's budget to 0.1 %) |
| Moving nose (C1S gimbal at 76.48 mm) | 16.6 g without the refill; refill + holder + drum + spring 1.74 g; tip-equivalent mass 1.50 g (CALC; study N's model: 2.10 g) |
| Nose flexure, actuator | 0.0028 N·m/rad; Km 0.656 N/√W at the magnets (image method: an upper bound); 2.47 Ω, 1.5 A, 3.7 V; 80 Hz servo (CALC / ASSUMPTION) |
| Nose travel | 6.57 mm at 50° (soft limit), stop at 7.07 mm (CALC) |
| Refill | 0.15 N spring, −2.19 N/m, 0.01 N friction; front stop follows the nose 0.3 mm beyond contact; pen lift 0.5 mm, 8 ms (ASSUMPTION) |
| Skid ring | contact radius 11.65 mm, open 120° on top (CALC / ASSUMPTION) |
| Heel wheel | 2 mm wheel at 12.0 mm in the ring plane (0.35 mm beyond the ring), 0.55 N preload on 200 N/m, μ 0.6–1.2 drawn per case, bristle tyre 1500 N/m, rolling 0.078, back-drive 0.03 N, 0.603 N peak / 0.369 N continuous, copper loss 4.30 W/N² (CALC from the motor data) |
| End-cap (optional) | 30.39 g slug at 152.7 mm, ±4 mm, 5 Hz flexures, damping ratio 0.05, Km 0.735 N/√W, 1 W peak; fixed parts in the handle (pen 129.4 g) |
| Sensors | IMU at 56.25 mm, 8.42 mm off the axis (LSM6DSV16X model); page sensor 1 kHz, 2 ms, 3 µm, valid to 2 mm lift; nose Hall 5.9 µm rms; refill slide 1 kHz, 2 µm |

- **Writers.** v2 writers (this study, §2) and, for comparison, the v1 writers of the handwriting study.
  Test writers 0–5, test seeds 200–203. Rules fixed first on tuning writers 100–103 and seed 300 (§4).
- **Tremor.** The project's tremor model on the hand path (H1) or as joint torques ('arm' hand). 4–12 Hz, 0.3–2 mm
  peak; severe 3 mm.
- **Start of each ET run.** The pen rests on the paper for 4 s before writing (tremor on). Reason: the tremor-line
  detectors need 2–4 s of signal; a person places the pen before writing (ASSUMPTION). The rest's ink is not scored.

## 2. Findings so far (SIM and CALC, tuning writers only)

- **The C1S nose must hold the refill spring's side load at the ball, and that costs about 1.6 W (CALC).**
  - The refill spring (0.15 N, along the nose) presses the ball on the paper. At 50° tilt the paper pushes back with a
    side component F_c·cot θ = 0.126 N at the ball (CALC).
  - The C1S gimbal is soft (0.0028 N·m/rad), so the coils must hold 9.6 mN·m (CALC). With Km 0.656 N/√W on the 11.5 mm
    magnet arm this is 1.62 W of coil heat while the ball is on the paper (CALC; about 3.9 W at 35°, 0.3 W at 75°).
  - sim2 shows 2.0–2.6 W mean nose coil power while writing (SIM, tuning writer 100). The lead's budget has 0.06 W for
    "writing without tremor" (results/revJ/budgets.json). Rev H's longer arm needed about 0.13 W for the same load (CALC).
- **ai2's gated listening tracker (DEC-042) does not hold in sim2 as built.** Its fallback, the Rev H tracker as built,
  moves tremor-free v2 writing by 51–141 µm (SIM, tuning writers; rule ≤ 25 µm). Its unfiltered listening output also
  carries 15–200 Hz content that the C1S servo cannot follow; with the Rev H tracker's 64 Hz output filter added it
  helps at 1–2 mm (pending numbers).
- **ai2's causal TCN does not transfer to sim2 without retraining** (replay on the pen's own sensor record, tuning
  writer 100): 0.66–0.73 of the device-off ink error at 8–10 Hz, 1 mm, but 1.56× at 0.3 mm and 184 µm false
  correction on tremor-free writing (HW1: 19.3 µm).
- **The v2 writers carry more 8–12 Hz motion than the literature target** (16 % of the velocity energy against
  1.3–1.7 %), which trips ai2's tremor-line detector (threshold 5) on tremor-free writing unless the threshold is raised.

(sections pending: writer model, verification, controllers, RL, outcomes per condition, proposals)
