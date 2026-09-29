# Response to the independent review of 29 September 2026

**Review:** "Stabilisation Pen: independent research and engineering review", 29 September 2026. The PDF is in this folder. The user commissioned it outside this repository, on commit `b1694a3`. Its calculation scripts, Markdown source and 25-source register are in the user's local package; this repository holds only the PDF.

**Status of this response:** lead engineering response, 2026-09-29. Nothing here is measured. Labels as elsewhere: SIM, CALC, LIT (ledger id), MFR, ASSUMPTION, PROPOSED DESIGN.

## 1. The answer in plain words

**The review is right about the most important thing.** The moving nose of Rev J (the "C1S" nose) wastes most of its power just holding the ball still against the paper.
- **Why.** The refill spring pushes the ball onto the paper along the pen. Because the pen is tilted, the paper pushes back partly sideways.
- **The C1S nose makes it worse.** Its magnets sit on a short 11.5 mm arm, while the ball is 76.5 mm from the pivot, so the coils must push 6.7 times harder than the sideways force at the ball.
- **The cost.** That is 1.6 W at a 50° pen angle and 4.7 W at 35° (CALC). The earlier budget assumed 0.09–0.38 W.
- **What it breaks.**
  - The coils would overheat within about a minute of writing (CALC).
  - The battery would last about an hour.
  - Every Rev J and Rev J.1 battery and heat claim is therefore **suspended**.

Two independent routes found this before the review arrived:
- the whole-pen physics simulation (`docs/revJ_simulation.md` §8.1, SIM);
- the lead's own check of the review's formula (CALC; the numbers reproduce exactly: 4.717 / 1.628 / 0.166 W at 35 / 50 / 75°).

**What changes now:**
1. **A load-balanced nib comes first.** The next design round (study B, `docs/balanced_nib.md`) removes this static load mechanically before choosing another actuator.
2. **The pen body is moved by a motorised collar.** The fingers hold a collar and motors swing the pen inside it; study W already includes this.
3. **The moving tail weight stays an optional experiment.** It is judged against the same weight locked in place, not against nothing.
4. **Measurement comes before more synthetic optimisation.** Study M specifies the bench rigs for the review's gates G1–G5.
5. **Language help is a separate layer.** The chain is: stroke record → recognition → suggestion → the writer accepts → optional physical writing (study S, with a prototype the user can try).
6. **The heel wheel is retracted by default** until its controller is redesigned. With it on, clean writing moved 0.42 mm in the physics simulation (SIM).

## 2. Finding by finding

| # | Review finding | Our check | Verdict | Action |
|---|---|---|---|---|
| 1 | The static nib load F_c·cot θ, multiplied by the lever L_t/L_a, dominates coil power: 4.72 / 1.63 / 0.17 W at 35 / 50 / 75° | Reproduced exactly (CALC). The physics simulation found about 1.1 W of it in a writing run (SIM, `docs/revJ_simulation.md` §8.1). Study N's duty model left it out | **Confirmed** | Battery and heat claims of DEC-044 and DEC-045 suspended. DEC-036 reopened. Study B: balanced load path |
| 2 | Levers: halving F_c quarters the loss; a 34 mm arm gives 0.19 W at 50°; balancing 90 % leaves 0.016 W; a 30 % lower Km doubles the heat | Reproduced (CALC: 0.407 W at 0.075 N; 0.186 W at 34 mm). The simulation also found that halving F_c let the tracker remove more tremor (SIM, one writer) | Confirmed | Study B compares all four levers, plus tilt-scheduled bias, contact-driven cam bias and low-force refills |
| 3 | A fixed preload tuned at one angle will not balance 35–75°; roll, pen lift and refill change also change the balance | Agreed: the load goes as cot θ, which varies 5.3 × over 35–75° | Confirmed | Study B must balance over the full range or schedule the bias by tilt without holding power |
| 4 | An internal mass gives F = m(2πf)²X: 0.118 N at 5 Hz for 30 g over ±4 mm; 0.5 N at 1 Hz needs ±422 mm | Same physics as `docs/revJ_plan.md` §3 and `docs/inertial_endcap.md` | Confirmed | No change. The tail stays optional and is compared with an equal locked mass |
| 5 | Packaging a 30 g tungsten slug with ±4 mm travel in a 16 mm barrel needs about 55 mm | Plausible (CALC geometry). The 24 mm pen makes it shorter (Rev J.1: 17.3 g slug, 21 mm end-cap) | Agreed | Study B and W report packaging per grip size |
| 6 | A gyroscope needs real numbers. A 20 g, 6 mm-radius rotor at 30 000 rpm gives h = 1.13 mN·m·s and stores 1.78 J. The round 4 example h = 5 mN·m·s needs a 25 mm rotor and 7.85 J | Agreed. The round 4 plan's example is large for a pen | Agreed | Study W sizes gyroscopes with containment and stored energy |
| 7 | Tremor cannot be separated from writing by frequency alone. Primary writing tremor at 4.1–7.3 Hz overlaps normal writing oscillations at 4.0–7.7 Hz (Bain et al. 1995, abstract) | Consistent with our studies: the gate, the listening tracker and the TCN all show false-correction risk | Agreed | Confidence-gated authority stays (DEC-042). Add the source to the ledger once opened |
| 8 | Page tracking at 1 kHz, 2 ms and 3 µm is not established. DeltaPen measured 68.3 µm mean error per 10 ms window (median 23.6 µm) on a Wacom surface | Agreed. Our 3 µm was an ASSUMPTION | Confirmed | Report results with a measured-error sensor model; the ideal sensor only as a labelled bound (studies B, R, W). Page sensing becomes a build gate |
| 9 | The heel wheel distorted clean writing by 420–427 µm; retracted by default is the credible baseline | Same numbers in `docs/revJ_simulation.md` §8.2 (SIM) | Confirmed | Wheel retracted by default; its controller must be redesigned before it is on during free writing |
| 10 | The replayed TCN moved clean writing by 131–155 µm: learned control does not transfer automatically | Same (SIM, domain shift) | Confirmed | TCN stays in shadow mode (DEC-042); retrain before any use |
| 11 | Rev J.1's thicker strips are a calculation only: recompute stability, stiffness, fatigue, actuator demand and tolerances together; 43.2 million cycles in 3 years at 8 Hz | Agreed. Study B's balanced load path changes the gimbal loads anyway | Agreed | Study B; EXP-J11 coupon tests |
| 12 | Later results were not promoted to the top-level summary | True: the README and concept doc still carried Rev J battery claims | Confirmed | Corrected today. A single claims register (`docs/claims_register.md`) lists every headline claim with its status |
| 13 | Compactness was traded away (24 mm, 87 g). Study targets: 12–16 mm, 25–40 g for the core | Note: the user chose a bigger grip in DEC-029 | **Open: user's choice** | Study B reports both the 24 mm pen and a 12–16 mm core as Pareto fronts, not a weighted score. The user decides |
| 14 | Control: nested loops; an independent supervisor on contact, travel, force, voltage and temperature; modes kept apart; pure-delay limit 2 × sin(π f τ) | Agreed. It matches the firmware's safety state machine, which predates Rev J | Agreed | Mode split in the supervisor (manual, stabilise, trace, accepted-text completion, digital correction) is proposed in the next firmware round |
| 15 | Spelling: three outputs (immutable stroke record, revisable transcript, accepted physical plan); noisy-channel score; completions at pauses; permanent ink cannot be corrected by moving the nib | Agreed | Agreed | Sent to study S, with a runnable prototype |
| 16 | Data: four separate datasets; participant and session splits; synthetic before/after pictures carry a prominent simulation label | Agreed | Agreed | Studies R and S; figure labels |
| 17 | Outcomes: one results card per population and mode; readable words out of 10, useful words per minute, tremor left at the tip, clean writing changed; say what a ratio means; report coverage and missing strokes with "ink only when correct" policies | Agreed; matches the user's request for clarity | Agreed | Explainer and every study doc; "write when in reach" (study W) must report coverage and missing strokes |
| 18 | The integrated report's §8.1 prose says 3.9 W and 0.3 W at 35° and 75°; its table says 4.7 and 0.17 W | Checked: cot²θ scaling gives 4.7 and 0.17 W | Confirmed | The simulation study is asked to fix the prose |

## 3. Development order (adopted, provisional)

1. **Balanced two-axis nib** (study B). It must show low holding power over 35–75°, enough loaded travel, accurate sensing and stable contact.
2. **Motorised collar around a moving inner pen** (study W, option d). It must show controllability across grip strengths, web clearance and comfort.
3. **Detachable moving-mass tail**, only if it beats the same mass locked (≥ 10 % incremental, the review's gate G5).
4. **Lightweight pen with a grounded writing surface**, for sustained guidance and accepted-word completion (the desk board, DEC-031, re-evaluated).
5. **Language help** (study S) in parallel, as a separate, reviewable layer.

## 4. The review's gates and where they live

| Gate | Review | Our experiments (existing or to specify in study M) |
|---|---|---|
| G1 contact and ink | Axial and normal force apart; friction; ink continuity; ≥ 3 refills, 6 papers, 35/50/75° | EXP-B01/B02 (Rev A friction rig), EXP-Q02 (ink laydown), EXP-J17 (the nib's static side load and holding power); study M runs them on rig R9 (`docs/measurement_rig.md`) |
| G2 actuator coupon | 2-D force/current/displacement, Km, attraction, interference, loaded modes at temperature | EXP-N01, EXP-J01, EXP-J14 |
| G3 one-axis loaded nib | Independent position ground truth; 1–30 Hz disturbances, 0.25–2 mm | EXP-I05 (Rev H nose bench); study M specifies it for the balanced nib |
| G4 complete two-axis nib | Sharp turns, repeated contacts, full roll and tilt, optical dropout, long thermal run | EXP-N02…N06, EXP-J13; study M |
| G5 collar and tail | Same tasks: no module, equal mass locked, unpowered, active; several grip strengths | EXP-K02, EXP-J16, EXP-I01; study W and M |
| G6 grounded guidance | Retracted, free, constrained wheel and external pad | EXP-D04…D08, EXP-G01…G07 |
| G7 recognition and suggestions | Held-out people and sessions; CER/WER; harmful edits | EXP-L06, EXP-A03; study S |
| G8 user study | Randomised crossover; blinded ink transcription; task completion | Human study plan §§12–20; the review's sample-size note (about 32 per comparison at d = 0.5) is a planning figure |

## 5. What this does not change

- Nothing in the review, or in this response, is a measurement.
- The physics limits of inertia, the need for page-relative sensing and the difficulty of telling intent from tremor were already in the programme. The review sharpens them.
- The user's requests stand: whole-pen shifting against large tremor (study W), realistic data (study R), clearer results (explainer, claims register) and spelling help (study S).
