# Claims register: every headline claim and its current status

**Updated 2026-09-29 by the lead** (after the whole-pen physics study, sim2j). This is the one place to check before quoting a number. Nothing in this programme has been built or measured. Every claim below is a calculation (CALC), a simulation (SIM), literature (LIT) or an assumption (ASSUMPTION).

**Status words**

| Status | Meaning |
|---|---|
| CURRENT | The latest calculation or simulation stands. It is not evidence of benefit to real people |
| SUSPENDED | A known error affects it. Do not quote it until the named study redoes it |
| SUPERSEDED | A later number replaces it (given) |
| CONTESTED | A later, more detailed simulation disagrees; quote both or neither |
| UNPROVEN | It rests on an assumption that nobody has measured |

**Which simulation to trust most.** The physics simulator sim2 with the Rev J pen (study sim2j, `docs/revJ_simulation.md`) models the pen's contact, stick-slip, masses and sensors in 3-D. The earlier hand–pen models (H1, HW1, HW1-D) are simpler. Where they disagree, sim2j is the better guide, but it still uses synthetic writers and synthetic tremor, and it ranks designs only until bench tests calibrate it (EXP-V01, V02, V04) and EXP-V05 validates it.

**The big correction (2026-09-29).** The moving nose's coils must hold the ball against a static sideways push from the paper. The refill spring presses the ball along the tilted pen, and the paper pushes back partly sideways. Study N's duty model left this out.
- **Rev J (C1S nose, 11.5 mm magnet arm):** 4.7 / 1.6 / 0.17 W at 35 / 50 / 75° pen angle (CALC; the independent review's figure, reproduced exactly).
- **In the physics simulation** the nose drew 2.25 W in tremor-free writing: about 1.1 W for this static load, 0.74 W for the servo reacting to its unfiltered position sensor (mostly a model artefact), and 0.4 W for friction and holding (SIM, `docs/revJ_simulation.md` §8.1).
- **Rev H (34 mm arm):** 0.36 / 0.13 / 0.01 W with its image-method magnet strength, or about six times that if the lower estimate holds (CALC).
- **Decision DEC-046:** the static load must be carried mechanically (≤ 0.1 W of coil heat), not by coil current. Study B chooses how. Every battery and heat claim below that includes the nose is **SUSPENDED** until then. See `docs/reviews/2026-09-29_review_response.md`.

## Tremor

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| With perfect knowledge of the tremor, the moving nose removes most of the ink error | Rev H: 87–99 % up to 2 mm (H1). Rev J in the physics simulator: leaves 0.10–0.20 of the ordinary pen's error at 8–12 Hz, 0.07–0.12 at 4 Hz | SIM | CURRENT, as a mechanism limit only | `docs/opt_inertial.md`; `docs/revJ_simulation.md` §6.1 | Measured actuator force and bandwidth (EXP-I05, gates G3/G4) |
| **Rev J, essential tremor 1–2 mm at 8–12 Hz, with the guarded tracker G4** | Ink error 0.63 of the ordinary pen (95 % bootstrap 0.59–0.68): 0.41 → 0.28 mm rms at 1 mm, 0.96 → 0.55 mm at 2 mm. Words read 69 → 100 %, letters 75 → 92 % | SIM (sim2j; 4 test writers, 16 cases; synthetic writers and tremor) | CURRENT, synthetic only (DEC-047) | `docs/revJ_simulation.md` §6.1 | Test writers 4–5 (to run); study R's recorded tremor; EXP-L01/L02 |
| Rev J, mild tremor (0.3 mm) | No gain and no harm: 1.02 of the ordinary pen's error | SIM (sim2j) | CURRENT | as above | as above |
| Rev J, slow tremor (4 Hz, 1–2 mm) | Nothing: 1.00. The detector listens from 4.5 Hz up, because 4 Hz overlaps writing's own rhythm | SIM (sim2j) | CURRENT: an open gap in estimation, not in the mechanism | as above | A better estimator (RL or learned, trained in sim2 and on real recordings) |
| Rev J, tremor-free writing | Moved 0 mm by the nose with G4 (5 writers) | SIM (sim2j) | CURRENT | `docs/revJ_simulation.md` §8.2 | EXP-L01 on real writing |
| Essential tremor 1–2 mm at 6–10 Hz with the gated listening tracker | Ink error 830 → 430 µm; words read 31 → 74 % | SIM (HW1, Rev H nose model) | **CONTESTED**: in the physics simulator this tracker moved tremor-free writing 59 µm (rule 25 µm) and raised the 0.3 mm error to 1.14 ×; G4 replaces it there (DEC-047) | `docs/ai_control_v2.md`; `docs/revJ_simulation.md` §6.1 | Real recordings (study R; EXP-L01/L02) |
| The same at 6 Hz, where Rev H's tracker did nothing | 822 → 540 µm | SIM (HW1) | CONTESTED, as above | `docs/ai_control_v2.md` | As above |
| The learned TCN estimator | 278 µm and 81 % of words in HW1. In the physics simulator it moved tremor-free writing 150 µm (up to 206 µm) and raised the 0.3 mm error to 1.26–1.38 × | SIM | Shadow mode only: it does not transfer (domain shift) | `docs/ai_control_v2.md`; `docs/revJ_simulation.md` §6.1, §8.2 | Retraining on sim2 streams and real recordings (EXP-L04) |
| Telling tremor from writing by frequency alone | Not reliable: writing tremor 4.1–7.3 Hz overlaps normal writing 4.0–7.7 Hz | LIT (Bain et al. 1995, abstract, via the review) | CURRENT | review §1, R04 | – |
| The tail weight (end-cap) on top of the nose | H1, Rev J.1, 29.6 g: a further 5.6 / 16.8 / 18.3 % at grip splits 0.3 / 0.5 / 0.7 (the same mass locked in place: 12.6 / 11.1 / 6.7 %). In the physics simulator with the Rev J pen: **no gain** (0.67 of the ordinary pen's error with it, 0.65 without) and fewer letters read | SIM (H1, Rev H pen); SIM (sim2j) | **CONTESTED**; optional, and must beat a locked weight | `docs/revJ1_design.md` §6.1; `docs/revJ_simulation.md` §6.1 | Grip split (EXP-I01); equal-mass test (EXP-J16, gate G5) |
| First end-cap design, 43 g | 8 / 18 / 20 % | SIM | SUPERSEDED by the 29.6 g end-cap | `docs/inertial_endcap.md` | – |
| Inertia cannot move letters: at writing speeds (below about 5 Hz) the best 45 g end-cap moves the ink at most 0.21 mm | 0.21 mm (end-cap), 1.06 mm (gyroscope) | CALC, SIM | CURRENT (physics) | `docs/inertial_endcap.md`; review §5 | – |
| **Rev J, severe tremor (3 mm at 5 and 8 Hz), writing through it** | Words read 4 → 38 %; ink error 1.47 → 1.15 mm rms | SIM (sim2j; 6 writers × 2 frequencies) | CURRENT, synthetic only | `docs/revJ_simulation.md` §6.2 | Study W (whole-pen shifting); study R |
| Tremor bigger than the nose's reach, and whole-pen shifting | The nose runs out of travel at about 3 mm (it used 6.55 of 6.57 mm in autowrite) | SIM (sim2j) | Being studied | study W (`docs/whole_pen_shift.md`, running) | – |

## Writing help

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| Autowrite: the nose writes a known text while the hand sweeps | HW1: 99.2 % of letters and 100 % of words up to 1 mm tremor; 98 % of words at 2 mm. **Physics simulator: 88 % of words at 3 mm tremor (4 % with the ordinary pen); 100 % with no tremor** | SIM (HW1; sim2j, 6 writers × 2 frequencies) | CURRENT as a mechanism result (DEC-049). SUSPENDED as a hardware claim: the C1S nose overheats in under a minute | `docs/nose_v2.md`; `docs/revJ_simulation.md` §6.2, §8.1 | The balanced nib (study B); page-sensor drift (EXP-J10) |
| Autowrite with a realistic page sensor | With DeltaPen-like errors that do not add up: 2–4 × the ink error, still readable. With errors that add up over a word: letters drift 1.5–3 mm apart, 7 of 10 words read. The error model used is harsher than DeltaPen's measurement (54.7 µm median and 117 µm mean per window, against 23.6 and 68.3 µm; study M), so these results are conservative | SIM (sim2j, writers 0–1; study M's check) | CURRENT; the page sensor's accumulated drift decides it (DEC-059) | `docs/revJ_simulation.md` §6.7 | EXP-J10 (REQ-RVJ-C05) |
| Parkinson's "write big" loops (five 10 mm loops) | Physics simulator: only the **driven** heel wheel keeps the last loop big: 6.6 → 8.6 mm with a relaxed hand, 7.4 mm with a lightly resisting one (felt 0.25–0.31 N rms). Steering alone enlarged the early loops but not the last. HW1-D had steering reach 0.99 of the target (0.78 with nothing) | SIM (sim2j, 2 cases per hand); SIM (HW1-D) | CURRENT for the driven wheel (synthetic); the HW1-D steering claim is **CONTESTED** | `docs/revJ_simulation.md` §6.3; `docs/grounded_drive.md` | Heel bench and people (EXP-D04, D08) |
| Tracing and guided copying (dysgraphia-like writers) | Physics simulator: the nose pulling half-way toward the copybook letter brings the ink 0.83 → 0.64 mm from it with words read unchanged (9.7 of 10). Stronger guidance (nose and wheel): 0.27 mm, but words read fall to 6.3 of 10. HW1-D: 582 → 76 µm, letters read 92 → 79 % | SIM (sim2j, 6 writers); SIM (HW1-D) | CURRENT: closer is not more legible; gentle guidance is the setting to prefer | `docs/revJ_simulation.md` §6.4; `docs/grounded_drive.md` | Study S's shape assist; people (EXP-D08) |
| Leading a relaxed hand with the driven wheel (lead-through) | HW1-D: letter bowl within 0.3 mm in 93 % of runs (3 % with nothing). Physics simulator, dyslexia lead-through: words read 5.8 → 6.7 of 10, letters distorted and slow (8 mm/s); autowrite of the same text reads 10 of 10 | SIM (HW1-D); SIM (sim2j, 4 writers) | CURRENT (synthetic); lead-through helps little, autowrite is the better tool | `docs/grounded_drive.md`; `docs/revJ_simulation.md` §6.5 | EXP-D08, D11 |
| The heel wheel during free writing | Moved tremor-free writing 0.40 mm (up to 0.50 mm) and doubled the error at 0.3 mm tremor; it helped only at 8 Hz × 2 mm (0.54 against the nose's 0.59; equal at 12 Hz) and at 4 Hz × 2 mm (0.73, where the nose does nothing) | SIM (sim2j) | CURRENT: the wheel stays retracted by default (DEC-048) | `docs/revJ_simulation.md` §6.1, §8.2 | A redesigned controller (REQ-RVJ-C02); EXP-J18 (writers adapting to it) |
| A writer set on a letter is never turned into another | 0 % | SIM | CURRENT | `docs/grounded_drive.md`; `docs/handwriting_outcomes.md` | People (EXP-D08) |
| The app's digital clean copy at 1–2 mm tremor | 97 % of words readable (the paper keeps the real ink) | SIM | CURRENT (synthetic) | `docs/ai_severe_tremor.md` | Blinded readers (EXP-A03) |
| Spelling help, prediction, shape assist | – | – | Being studied | study S (`docs/spelling_and_clarity.md`, running) | – |

## Hardware

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| The nose's reach at the ball | Rev J C1S: ±6.0 mm guaranteed over 35–75°. Rev H: ±2.75 mm | CALC | CURRENT as geometry. The C1S design is REOPENED (DEC-036, DEC-046) | `docs/nose_v2.md` | Study B |
| Nose coil power | Rev J budget: 64–376 mW. Physics simulator: 2.25 W in tremor-free writing, about 2.3 W in every mode | CALC; SIM (sim2j) | **SUSPENDED**: the static load adds 0.17–4.7 W (DEC-046) | `docs/revJ_design.md` §6.3; `docs/revJ_simulation.md` §8.1 | Study B; EXP-J17 |
| Battery life | Rev J 6.1–7.3 h; Rev J.1 8.5–9.7 h at 1 mm tremor; Rev H 27 h. At the simulated 2.3 W the 2.22 Wh cell lasts about 1 h | CALC | **SUSPENDED** (static load) | DEC-044, DEC-045, DEC-032; `docs/revJ_simulation.md` §8.1 | Study B, then EXP-J12 |
| Skin and coil temperature | Rev J.1: skin 35.9 °C in a 30 °C room. At the simulated 2.68 W on the paper the coil would pass its 120 °C limit after about 22 s of continuous writing | CALC (coil 100 K/W, 0.5 J/K ASSUMED) | **SUSPENDED** (static load) | DEC-045; `docs/revJ_simulation.md` §8.1 | Study B, then EXP-J13, EXP-J17 |
| Mass and length | Rev J.1 84.3 g / 143.9 mm; 112.7 g / 161.9 mm with the end-cap | CALC | CURRENT for Rev J.1; the nib may change | `docs/revJ1_design.md` | Study B (a 12–16 mm, 25–40 g core is also being studied) |
| Gimbal strength | 75 µm strips buckle at 55 N against a 12–22 N magnet pull | CALC | CURRENT; the balanced nib may change the loads | `docs/revJ1_design.md` §3 | EXP-J11 |
| Heel-wheel push on the hand | 0.3–0.6 N | CALC on ASSUMED tyre friction | UNPROVEN | `docs/grounded_drive.md` | Tyre friction (EXP-D01) |
| Page sensor accuracy | 3 µm, 2 ms, 1 kHz on paper | ASSUMPTION | **UNPROVEN**: a research pen (DeltaPen, UIST 2022) measured 68.3 µm mean and 23.6 µm median error per 10 ms window, on a tablet surface. Its metric is the error of the translation length, which is smaller than the vector error our protocol first wrote down (DEC-059) | review §7, R14; `docs/measurement_rig.md` §3 | Page-sensor rig R10 (EXP-T04, T05), EXP-J10 |
| Nose magnet strength Km | Rev H 0.47 N/√W (image method gives 0.19); C1S 0.656 N/√W (upper bound). At 0.7 × the C1S nose sags under the static load (4.2 W; 62 % of letters read in tremor-free writing, SIM) | CALC; SIM | UNPROVEN, contested (DEC-041) | `docs/nose_v2.md`; `docs/revJ_simulation.md` §8.1 | Coupons (EXP-N01, gate G2) |

## Simulation

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| The physics simulator matches the earlier hand–pen model | Uncorrected ink error within 3.1 % in 56 of 56 cases; perfect-knowledge ratio within ±0.03 in 52; tracker ratio within ±0.05 in 50 | SIM against SIM | CURRENT as verification. It is NOT validation against hardware | `docs/sim_v2.md` | Bench identification (EXP-V01/V02/V04), validation (EXP-V05) |
| The synthetic writers | v2 (refitted): speed 27–31 mm/s and the speed–curvature slope 0.80 now match the literature; the 8–12 Hz share of velocity energy is still 10–12 % against 1.3–1.7 %, and the letters look like crude print | SIM against LIT | Known flaw; real recorded data are being brought in. On v2 writers the listening estimators lost more than G4, so the v1 results flattered them | `docs/sim_v2.md`; `docs/revJ_simulation.md` §3; study R | Study R; EXP-V07; EXP-H01 |
| RL for the nose in the physics simulator | Not trained yet (the environment runs; the full run needs about 2.4 CPU hours). The gap it could close: 0.63 → 0.16 of the ordinary pen's error, and the 4 Hz tremor | SIM (smoke run only) | No result | `docs/revJ_simulation.md` §7 | EXP-L05 |
