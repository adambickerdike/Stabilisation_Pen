# Claims register: every headline claim and its current status

**Updated 2026-09-29 by the lead.** This is the one place to check before quoting a number. Nothing in this programme has been built or measured. Every claim below is a calculation (CALC), a simulation (SIM), literature (LIT) or an assumption (ASSUMPTION).

**Status words**

| Status | Meaning |
|---|---|
| CURRENT | The latest calculation or simulation stands. It is not evidence of benefit to real people |
| SUSPENDED | A known error affects it. Do not quote it until the named study redoes it |
| SUPERSEDED | A later number replaces it (given) |
| UNPROVEN | It rests on an assumption that nobody has measured |

**The big correction (2026-09-29).** The moving nose's coils must hold the ball against a static sideways push from the paper. The refill spring presses the ball along the tilted pen, and the paper pushes back partly sideways. Study N's duty model left this out.
- **Rev J (C1S nose, 11.5 mm magnet arm):** 4.7 / 1.6 / 0.17 W at 35 / 50 / 75° pen angle (CALC; confirmed by the physics simulation, SIM).
- **Rev H (34 mm arm):** 0.36 / 0.13 / 0.01 W with its image-method magnet strength, or about six times that if the lower estimate holds (CALC).
- Every battery and heat claim below that includes the nose is **SUSPENDED** until the balanced-nib study (study B) redoes it. See `docs/reviews/2026-09-29_review_response.md`.

## Tremor

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| With perfect knowledge of the tremor, the moving nose removes most of the ink error | Rev H: 87–99 % up to 2 mm | SIM (H1) | CURRENT, as a mechanism limit only | `docs/opt_inertial.md` | Measured actuator force and bandwidth (EXP-I05, gates G3/G4) |
| Essential tremor 1–2 mm at 6–10 Hz with the gated listening tracker | Ink error 830 → 430 µm; words read 31 → 74 % | SIM (HW1, synthetic writers, Rev H nose model) | CURRENT, synthetic writers only | `docs/ai_control_v2.md` | Real recordings (study R now; EXP-H01, EXP-L01/L02) |
| The same at 6 Hz, where Rev H's tracker did nothing | 822 → 540 µm | SIM | CURRENT, synthetic only | `docs/ai_control_v2.md` | As above |
| The learned TCN estimator | 278 µm and 81 % of words in HW1; moved clean writing 131–155 µm in the physics simulator | SIM | Shadow mode only: it does not transfer (domain shift) | `docs/ai_control_v2.md`; `docs/revJ_simulation.md` §8.2 | Retraining; real recordings (EXP-L04) |
| Telling tremor from writing by frequency alone | Not reliable: writing tremor 4.1–7.3 Hz overlaps normal writing 4.0–7.7 Hz | LIT (Bain et al. 1995, abstract, via the review) | CURRENT | review §1, R04 | – |
| The tail weight (end-cap) on top of the nose | Rev J.1, 29.6 g: a further 5.6 / 16.8 / 18.3 % at grip splits 0.3 / 0.5 / 0.7. The same mass locked in place gives 12.6 / 11.1 / 6.7 % | SIM (H1, Rev H pen) | CURRENT; optional, and must beat a locked weight | `docs/revJ1_design.md` §6.1 | Grip split (EXP-I01); equal-mass test (EXP-J16, gate G5) |
| First end-cap design, 43 g | 8 / 18 / 20 % | SIM | SUPERSEDED by the 29.6 g end-cap | `docs/inertial_endcap.md` | – |
| Inertia cannot move letters: at writing speeds (below about 5 Hz) the best 45 g end-cap moves the ink at most 0.21 mm | 0.21 mm (end-cap), 1.06 mm (gyroscope) | CALC, SIM | CURRENT (physics) | `docs/inertial_endcap.md`; review §5 | – |
| Tremor bigger than the nose's reach, and whole-pen shifting | – | – | Being studied | study W (`docs/whole_pen_shift.md`, running) | – |

## Writing help

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| Autowrite: the nose writes a known text while the hand sweeps | 99.2 % of letters and 100 % of words read up to 1 mm tremor; 98 % of words at 2 mm | SIM (HW1) | CURRENT as a mechanism result. SUSPENDED as a hardware claim: the static load makes the C1S nose overheat in under a minute | `docs/nose_v2.md`; `docs/revJ_simulation.md` §8.1 | The balanced nib (study B) |
| Parkinson's "write big" loops with the heel wheel steering | Loop height 0.99 of the target (0.78 with nothing) | SIM (HW1-D) | CURRENT (synthetic) | `docs/grounded_drive.md` | Heel bench and people (EXP-D04, D08) |
| Tracing with the heel wheel and nose | Ink 582 → 76 µm from the template, but letters read FELL from 92 % to 79 % | SIM | CURRENT: closer is not more legible | `docs/grounded_drive.md` | Study S's shape assist |
| Leading a relaxed hand with the driven wheel | Letter bowl within 0.3 mm in 93 % of runs (3 % with nothing) | SIM | CURRENT (synthetic) | `docs/grounded_drive.md` | EXP-D08, D11 |
| The heel wheel during free writing | Moved clean writing 0.42 mm | SIM (sim2) | CURRENT: the wheel stays retracted by default | `docs/revJ_simulation.md` §8.2 | A redesigned controller |
| A writer set on a letter is never turned into another | 0 % | SIM | CURRENT | `docs/grounded_drive.md`; `docs/handwriting_outcomes.md` | People (EXP-D08) |
| The app's digital clean copy at 1–2 mm tremor | 97 % of words readable (the paper keeps the real ink) | SIM | CURRENT (synthetic) | `docs/ai_severe_tremor.md` | Blinded readers (EXP-A03) |
| Spelling help, prediction, shape assist | – | – | Being studied | study S (`docs/spelling_and_clarity.md`, running) | – |

## Hardware

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| The nose's reach at the ball | Rev J C1S: ±6.0 mm guaranteed over 35–75°. Rev H: ±2.75 mm | CALC | CURRENT as geometry. The C1S design is REOPENED (DEC-036) | `docs/nose_v2.md` | Study B |
| Nose coil power | Rev J: 64–376 mW in the budget | CALC | **SUSPENDED**: the static load adds 0.17–4.7 W | `docs/revJ_design.md` §6.3 | Study B |
| Battery life | Rev J 6.1–7.3 h; Rev J.1 8.5–9.7 h at 1 mm tremor; Rev H 27 h | CALC | **SUSPENDED** (static load) | DEC-044, DEC-045, DEC-032 | Study B, then EXP-J12 |
| Skin temperature at the grip | Rev J.1 35.9 °C in a 30 °C room | CALC | **SUSPENDED** (static load) | DEC-045 | Study B, then EXP-J13 |
| Mass and length | Rev J.1 84.3 g / 143.9 mm; 112.7 g / 161.9 mm with the end-cap | CALC | CURRENT for Rev J.1; the nib may change | `docs/revJ1_design.md` | Study B (a 12–16 mm, 25–40 g core is also being studied) |
| Gimbal strength | 75 µm strips buckle at 55 N against a 12–22 N magnet pull | CALC | CURRENT; the balanced nib may change the loads | `docs/revJ1_design.md` §3 | EXP-J11 |
| Heel-wheel push on the hand | 0.3–0.6 N | CALC on ASSUMED tyre friction | UNPROVEN | `docs/grounded_drive.md` | Tyre friction (EXP-D01) |
| Page sensor accuracy | 3 µm, 2 ms, 1 kHz on paper | ASSUMPTION | **UNPROVEN**: a research pen (DeltaPen, UIST 2022) measured 68.3 µm mean error per 10 ms window, median 23.6 µm, on a tablet surface | review §7, R14 | Page-sensing rig (study M), EXP-J10 |
| Nose magnet strength Km | Rev H 0.47 N/√W (image method gives 0.19); C1S 0.656 N/√W (upper bound) | CALC | UNPROVEN, contested (DEC-041) | `docs/nose_v2.md` | Coupons (EXP-N01, gate G2) |

## Simulation

| Claim | Value | Evidence | Status | Source | What changes it |
|---|---|---|---|---|---|
| The physics simulator matches the earlier hand–pen model | Uncorrected ink error within 3.1 % in 56 of 56 cases; perfect-knowledge ratio within ±0.03 in 52; tracker ratio within ±0.05 in 50 | SIM against SIM | CURRENT as verification. It is NOT validation against hardware | `docs/sim_v2.md` | Bench identification (EXP-V01/V02/V04), validation (EXP-V05) |
| The synthetic writers | Half adult speed; about ten times the measured 8–12 Hz content | SIM against LIT | Known flaw; real recorded data are being brought in | `docs/sim_v2.md`; study R | Study R; EXP-H01 |
