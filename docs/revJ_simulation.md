# Rev J in the physics simulator: closed-loop study, round 2 (DRAFT, runs in progress)

Status: DRAFT written while the test runs are going. Numbers marked (pending) are not yet computed.
Every number here is a SIMULATION (sim2, MuJoCo 3.6) or a CALCULATION on synthetic writers and synthetic tremor.
Nothing was built or measured. sim2 ranks concepts (context of use COU-1, docs/sim_v2.md §8.1) until EXP-V01, EXP-V02
and EXP-V04 calibrate it and EXP-V05 validates it. These results are not evidence of benefit to people.

## Findings so far (SIM and CALC, tuning writers only)

- **The C1S nose must hold the refill spring's side load at the ball, and that costs about 1.6 W (CALC).**
  - The refill spring (0.15 N, along the nose) presses the ball on the paper. At 50° tilt the paper pushes back with a
    side component F_c·cot θ = 0.126 N at the ball (CALC).
  - The C1S gimbal is soft (0.0028 N·m/rad), so the coils must hold 9.6 mN·m (CALC). With Km 0.656 N/√W on the 11.5 mm
    magnet arm this is 1.62 W of coil heat while the ball is on the paper (CALC; 3.9 W at 35°, 0.3 W at 75°).
  - sim2 shows 2.0–2.6 W mean nose coil power while writing (SIM, tuning writer 100). The lead's budget has 0.06 W for
    "writing without tremor" (results/revJ/budgets.json). Rev H's longer arm needed about 0.13 W for the same load (CALC).
- **ai2's gated listening tracker (DEC-042) does not hold in sim2 as built.** (details pending)
- **The v2 writers carry more 8–12 Hz motion than real writing** (pending numbers), which trips the tremor-line
  detector on tremor-free writing unless its threshold is raised.

(sections pending: writer model, Rev J assembly, verification, controllers, RL, outcomes per condition, proposals)
