# Active stabilisation pen: engineering programme

A pen that actively moves its ink tip, and steadies its own body, to counter unwanted hand motion, supports people with Parkinson's-related writing difficulty, assists everyday handwriting and drawing, and captures notes with source-grounded AI assistance.

This repository holds the research and development package: the audit of the source report, evidence, requirements, physics, simulation, mechanics, electronics, firmware, ML, app, validation plans and decisions.

**Evidence status.** Everything here is **calculation, simulation, literature or proposed design**. Nothing has been built, and there are **no physical or human measurements**. Every figure carries a stamp saying what it is, and every result file records its code revision, parameter version, seeds and command.

## Start here

| If you want… | Read |
|---|---|
| **On your computer:** open `START_HERE.html` for one-click links to the claims register, the explainer, the spelling prototype and the latest studies | `START_HERE.html` |
| **The current design, Rev J:** a pen that acts at the tip (a ±6 mm moving nose), the heel (a wheel that uses the paper as ground) and the tail (a detachable reaction-mass end-cap); what each can do, whether it can write for you, what to test first | [`docs/revJ_concept.md`](docs/revJ_concept.md); plan [`docs/revJ_plan.md`](docs/revJ_plan.md); integrated design [`docs/revJ_design.md`](docs/revJ_design.md); the 3-D explainer [`viewer/explainer/`](viewer/explainer/build.py) |
| The Rev J studies | tip [`docs/nose_v2.md`](docs/nose_v2.md), heel [`docs/grounded_drive.md`](docs/grounded_drive.md), tail [`docs/inertial_endcap.md`](docs/inertial_endcap.md), algorithms and AI [`docs/ai_control_v2.md`](docs/ai_control_v2.md), physics simulator [`docs/sim_v2.md`](docs/sim_v2.md) |
| The previous design, Rev H (bigger grip, ±3 mm nose): what is inside, how much it helps each condition | [`docs/revH_concept.md`](docs/revH_concept.md) |
| The recommended route: what to build, where custom hardware and our own data are unavoidable, what evidence each benefit needs | [`docs/recommendation.md`](docs/recommendation.md) |
| The slim pencil variant (Ø8.9 × 166 mm): exact forces, mechanisms with existing parts, what to make, AI guidance and autocorrect, sim-to-real, 3D replay | [`docs/pencil_concept.md`](docs/pencil_concept.md), [`viewer/`](viewer/build.py) |
| The verdict on the source report | [`docs/audit.md`](docs/audit.md), [`docs/corrections.csv`](docs/corrections.csv) |
| **Which numbers still stand:** every headline claim with its status (current, suspended, unproven) | [`docs/claims_register.md`](docs/claims_register.md) |
| The independent review of 29 September 2026 and our response to each finding | [`docs/reviews/`](docs/reviews/2026-09-29_review_response.md) |
| Current state, blockers and next actions | [`CHECKPOINT.md`](CHECKPOINT.md) |
| The system and its budgets | [`docs/architecture.md`](docs/architecture.md), [`docs/icd.md`](docs/icd.md) |
| Why things are the way they are | [`docs/decisions.md`](docs/decisions.md) (DEC-001…044) |
| What the simulations say | [`docs/sim_report.md`](docs/sim_report.md) |
| What may be claimed for each feature | [`docs/features.md`](docs/features.md) |
| The riskiest open questions | [`docs/research_questions.md`](docs/research_questions.md) |
| How to proceed | [`docs/plan.md`](docs/plan.md), [`validation/`](validation/README.md) |

## Key conclusions so far

> **Correction, 29 September 2026.** The moving nose's coils must hold the ball against a static sideways push from the paper. The refill spring presses the ball along the tilted pen, and the paper pushes back partly sideways. This was left out of the power budgets.
>
> - **Rev J (C1S nose):** it costs 4.7 / 1.6 / 0.17 W at 35 / 50 / 75° pen angle (CALC; confirmed by the physics simulation and by an independent review). The coils would overheat within about a minute.
> - **Rev H (longer arm):** 0.13 W at 50° or more (CALC).
> - **What is suspended:** every battery and heat claim for Rev H, Rev J and Rev J.1. A load-balanced nib is being designed (study B).
>
> **Fix designed, 30 September 2026 (study B, DEC-050; CALC and SIM, nothing built).** A balanced nib, B1, carries the load mechanically. The refill slides ±1 mm on four thin wires, and its spring pushes the refill's rear end through a small face kept parallel to the paper, so the spring's push and the paper's push cancel at any angle. Holding heat is at most 1.6 mW (limit 100 mW), continuous power 7.6 mW, about 38 h per charge (CALC). The cost is reach: ±1.06 mm instead of ±6 mm, so the pen can no longer write whole words for the user (autowrite); that stays a bench research mode. The next prototype, **Rev K**, is the Rev J body with this nib, the heel wheel retracted and no tail.
>
> Check [`docs/claims_register.md`](docs/claims_register.md) before quoting any number.

1. **The transverse load is dominated by N·cos θ, not friction** (COR-01). Holding power (F/(n·K_m))² therefore rules out direct drive at the tip (about 12 W). A front-pivot lever with a rear annular actuator brings it to about 0.5 W in contact at the design point. That is **above the 0.412 W a moving coil can dissipate continuously** (within it on average at 65 % pen-down). Skid and bias-actuator variants remain the product path (DEC-003, DEC-008; route in `docs/recommendation.md`).
2. **Intent separation, not mechanics or latency, limits free-writing assistance.**
   - In simulation, the mechanism could remove 70–80 % of tremor-induced ink error (oracle bound 0.22–0.32).
   - The causal estimators tested give no benefit below ~9 Hz on synthetic handwriting.
   - Guided (template) tasks work in simulation: circle 443 → 163 µm, spiral 382 → 112 µm.
   - Whether real handwriting is more separable is the decisive open question (EXP-H01 → E01).
3. **Parkinson's writing difficulty is mainly micrographia.** A ±0.5 mm stage cannot enlarge letters. PD support means cueing, feedback and practice, measured for lasting unassisted benefit, not immediate correction (DEC-002).
4. **Design errors found and fixed in this package** (calculation and simulation):
   - Nib-bounce instability from a measured-force contact feedforward (DEC-011).
   - Voltage-limited 11 Ω coil, rewound to 6 Ω (DEC-012). A later, fuller headroom check found 6 Ω still binds at 3.3 V in the hot, high-force corner (0.5 % of the thermal envelope) and 4 Ω does not; open until EXP-B03 winds both.
   - A thermal model left at the old 0.45 mm air gap: the moving-coil allowable is 0.412 W, not 0.455 W (v0.4.3).
   - Interface errors found by the firmware review: the ICD printed the inverse Jacobian and the wrong actuator-force sign (fixed in ICD v1.3; the simulator and firmware were right). Tilt-dependent γ is now computed from a stored stiffness ratio.
   - An axial suspension layout that closes the actuator gap: the refill now slides in the carrier (DEC-007 rev.).
   - A nose that touched the paper at every writing angle: the refill point now protrudes 5 mm (DEC-018).
   - Inertia understated by a point-mass approximation: 13.7 g, above the 12 g requirement.
   - The research circuit does not fit the 29 mm board in the CAD envelope. The package plan and a 41 mm board fit at 0.65 density (DEC-014, open).
5. **A pencil-sized version is possible only if the writing force bypasses the nib** (`docs/pencil_concept.md`, DEC-019 to DEC-022).
   - A nose skid carries the user's force and a light spring sets the nib force. The stage then holds 0.17 N instead of 0.76 N.
   - Four custom 2.6 mm piezo plates fit the 7.9 mm bore. They give ±277 µm of stroke under load at zero static power, in 12.2 g of CAD before wiring. A voice coil that fits would need 2.4 W.
   - The stroke margin is thin (±162 µm at −20 % tolerance). Tremor estimation is the same open problem as in Rev A. Re-optimising the stage with real parts (P0.2: custom plates, thicker leaves, charge-recovery drive) gives 212 µm in the worst corner instead of none and 2.7 h of assist instead of 0.5 h (`docs/opt_hardware.md`, DEC-030).
   - **The user has since chosen a bigger grip (DEC-029): the primary concept is now Rev H, where the whole front of the pen tilts to move the tip about ±3 mm. The pencil is the slim variant.**
   - The skid causes touchdown and lift tails: about 1.1 mm of extra ink per stroke. A tilt-adaptive front stop cuts this to 0.33 mm. A stage feed-forward in firmware, tuned by adjoint gradients and Bayesian search, then brings the ink at the transitions to 0.005–0.008 mm per stroke; bounce is its open risk (`docs/opt_touchdown.md`, DEC-026).
   - Paper capture needs a ≥ 120 Hz page sensor that does not yet exist at this size.
   - AI helps as a digital autocorrect (word errors 32 % → 10 %). Physical guidance toward AI-predicted letters does not help free writing: a correct prediction is already about 300 µm off, beyond break-even. Guidance toward known templates does help.
   - Weights, gyroscopes or a motorised grip inside the 20 g pencil leave 0.85–0.97 of the ink error with perfect knowledge, against 0.18–0.43 for the nib stage (`docs/inertial_stabilisation.md`). At the user's direction the bigger-grip pen has active inertial control of its body (item 7, DEC-033).
   - The accelerometer now drives the tremor tracker directly, with gyroscope compensation. It leaves 0.78 of the tremor-band error on average, against 0.85 before, and 0.58–0.71 at 8–12 Hz once calibrated per writer. Separating tremor from writing is still the limit (`docs/sensor_fusion_ai.md`, DEC-025). Re-optimising its settings with exact adjoint gradients gives 0.86 instead of 0.91 for the default set, and 0.67 instead of 0.79 at 8–12 Hz; learned trackers were not better at equal false correction (`docs/opt_tracker.md`, DEC-028).
6. **The simulator can be calibrated from the planned bench work, and the twin experiments say how well** (`docs/sim_to_real.md`, DEC-023).
   - On 15 blind simulated plants the protocol experiments recover every model parameter to ≤ 1.6 % in about 1.5 h of bench time per build.
   - The calibrated twin then predicts the oracle ratio within ±0.1 for 14 of 15 plants, against 4–5 uncalibrated.
   - The same work found that the frozen tremor estimator degrades on randomised plants (median ratio 0.88 at 9 Hz), and that the existing Monte Carlo lets the controller see true plant values.

7. **Rev H, the bigger-grip pen, was the primary design until Rev J (item 8)** (DEC-029, DEC-032, DEC-033; `docs/revH_concept.md`). All simulation and calculation.
   - Ø22 × 170 mm, 75 g, or 103 g with the inertial module. The fingers hold a fixed sleeve whose front ring rests on the paper and carries the writing force. The whole front of the pen (the nose, holding the refill) tilts on a flexure gimbal, driven by two pairs of flat voice coils, so the ink tip moves up to ±3 mm: ten times the pencil's stage. About 0.08 W, about 27 h of writing.
   - A rear inertial module (19.8 g tungsten slug moved ±2.75 mm on two axes) pushes the whole pen against the shake. On top of the nose it adds 6–17 % further reduction depending on the grip. It is fitted in the first prototype; the product keeps it if the grip measurement (EXP-I01) and the bench test (EXP-I06) confirm ≥ 10 %. A plain weight made the ink worse in 38–42 % of 8–12 Hz cases and is not used.
   - With perfect knowledge of the tremor the nose removes 87–99 % of the ink error up to 2 mm, and the app reads 98–100 % of words. With today's accelerometer tracker: 22–50 % at 8–10 Hz (words read at 10 Hz, 1 mm: 54 → 87 %), and nothing at 4–6 Hz. **The tracker, not the mechanism, is the limit** (`docs/opt_inertial.md`, `docs/handwriting_outcomes.md`).
   - Parkinson's shrinking letters: a "write bigger" vibration cue kept letters at 5.2 mm instead of 4.2 mm, if people respond as small studies suggest. Poor handwriting: guidance brings the ink 24–61 % closer to the target letters while it is on (partial nose guidance 35 %, reading slightly better; full guidance reads worse); lasting benefit needs a human study (EXP-W04). Dyslexia: guidance never turned a wrong letter into the right one; the help is the app's spelling check, read-back and clean copy.
   - An optional desk board moves a permanent magnet under the paper to pull the pen along whole letters (0.4 N cap; `docs/guidance_board.md`, DEC-031).
   - AI letter prediction does not close the tracker's gap at 1–2 mm tremor: a correct predicted letter is 0.5–0.9 mm off because it is placed where the shaking tip lands; as a tracker input it closed 0 %, as nose guidance 1 %. The app's digital clean copy makes 97 % of words readable at 1–2 mm, against 30–59 % in the ink (`docs/ai_severe_tremor.md`, DEC-035).

8. **Rev J acts at the tip, the heel and the tail; it is now the primary design** (DEC-036…049; `docs/revJ_concept.md`). The user asked for far more physical effect, inertial movement of the whole pen, and a pen that can partly write for you. All calculation and simulation.
   - **The whole pen in the physics simulator (round 2, `docs/revJ_simulation.md`, DEC-046…049; SIM on synthetic writers and synthetic tremor, 6 test writers).** Readable words out of 10, ordinary pen → Rev J: essential tremor 2 mm at 8–12 Hz 5.4 → 10 (1 mm: 10 → 10; the ink error falls to 0.63 of the ordinary pen's); mild 0.3 mm: no change, no harm; **slow 4 Hz tremor: nothing** (the pen cannot yet tell it from writing; perfect knowledge would remove 90 %); severe 3 mm: 0.4 → 3.8 writing through it, 0.4 → 8.8 when the pen writes a text the writer chose (autowrite). Parkinson's practice loops: only the driven heel wheel keeps the last loop big (6.6 → 8.6 mm of 10). Dysgraphia: a half-way nose brings the ink 23 % closer to the copybook letters with no loss of readability. Dyslexia lead-through helps little (5.8 → 6.7); autowrite of the right spelling reads 10 of 10. Tremor-free writing: moved 0 mm by the nose, 0.41 mm by the heel wheel, so **the wheel is retracted by default** (DEC-048). The chosen tracker is the guarded tracker G4 (DEC-047). **Power:** the nose drew about 2.3 W in every mode, mostly to hold the ball against the static side load: writing time per charge is suspended until the load is carried mechanically (DEC-046, study B). RL was not trained yet.
   - **Real recorded data (study R, `docs/real_data.md`, DEC-054, DEC-055; SIM with real recorded inputs).** With real handwriting (UNIPEN: 14 adults with a ballpoint on paper), real Parkinson's tremor recorded at the pen tip, real essential tremor recorded at the hand, and a realistic page sensor, on held-out writers, texts and patients: real tip tremor is smaller than assumed (severe typically 1.7 mm, not 5–10 mm) and about twice as irregular as the model. **No tracker built so far makes the writing more readable on real tremor:** at the severe size, 0.5 of 10 words with an ordinary pen, 0.4 with Rev J's gated tracker, 0.2 with the learned TCN, and 7.0 with perfect knowledge of the tremor (6.8 without tremor). The ±6 mm nose has the reach; estimating real tremor in time is the missing piece. So the synthetic-tremor gains above are not claims about real tremor until a tracker passes on real inputs (DEC-055).
   - **Tracking real tremor (study E, `docs/real_tracker.md`, DEC-060, DEC-061; SIM with real recorded inputs).** Every kind of causal tracker was tried on study R's real inputs (filters, oscillator trackers, the pen's Kalman tracker with new gates, study W's candidate, small networks), tuned on the tuning writers only, frozen, and tested once on 9 held-out writers. **None passes DEC-055 yet.** The winner took about a third off the severe tip tremor (0.69 ×), but about 1 mm was left and words read stayed at 0.5 of 10; and it moved one writer's clean writing 0.49 mm, because that writer's large, fast letters looked like tremor to it. The reasons: handwriting moves in the same 4–8 Hz rhythm as tremor, real tremor wanders, and taking off a third of 1.7 mm is not enough. The delay is not the cause. A small network trained on real recordings looked better afterwards (0.60 ×, clean writing moved 2.5 µm) but must be tested again on new data (EXP-E10). Meanwhile the safe default tracker (G4) stays, help for severe tremor comes from the app (clean copy, spelling, completion), and the next nib stays at ±1 mm.
   - **Spelling help, prediction and clearer writing (study S, `docs/spelling_and_clarity.md`, DEC-056, DEC-057; CALC and SIM on real letters and real misspellings).** A separate language layer with three outputs (the ink, the transcript, and the pen's writing plan). Letters are read while they are written (82 % by the end of each letter for unseen writers). The spell checker catches 63 % of real children's misspellings when the letters are known (34 % when the pen reads them itself) at about 2 false alarms per 100 words; a tick at the next pause gets 3 of 10 misspellings fixed on paper (writer responses assumed). Word completion puts the word in the top 3 after one letter 52–56 % of the time. The shape assist does not make letters clearer (41.4 → 41.9 %), so it is not adopted; nearest-point close tracing is retired because it left parts of letters undrawn. The pen writes only text the writer accepted, and needs about ±4–6 mm of reach for a whole word. A prototype page to try it is in `ai3/demo/index.html`.
   - **Shifting the whole pen (study W, `docs/whole_pen_shift.md`, DEC-051…053; CALC and SIM).** At the user's request the study designed the strongest compact way to physically shift the whole pen: a collar you hold, with the inner pen swinging on a hinge 50 mm behind the tip, driven by a flat coil in the collar's back wall (±4 mm at the tip, 21.7 mm across, 40.1 g, only 0.055 W to hold at 50°). Weights, gyroscopes and pushing on the paper cannot do this job in a pen. **In simulation the collar did not beat Rev J's moving nose**, which already reaches ±6.57 mm (−5 % to +5 % against the same pen with the collar locked; the gate is 10 %), so the moving nose stays the part that shifts the ink, the collar is a bench experiment, and inertial tails are rejected for the product (DEC-051). What would make writing much better is knowing the tremor: at 3 mm, perfect knowledge leaves 0.14–0.24 mm and every word readable, against 1.1–1.4 mm with today's estimate (DEC-052).
   - **The balanced nib (study B, `docs/balanced_nib.md`, DEC-050; CALC and SIM).** Eleven ways to carry the paper's static sideways push were designed and optimised for the 24 mm pen and a 12–16 mm core. The winner, B1, is a two-axis translation nib on four titanium wires with flat moving coils (no magnetic pull) and a contact-driven counter-face that cancels the push at every tilt and roll (residual 5.3 mN, 6 % of the load). It holds with at most 1.6 mW and runs on 7.6 mW (Rev J's nose: 1.6 W at 50°); in the physics simulator it removes as much tremor as Rev J's nose up to 1 mm (words read 6.4 → 8.1 of 10, 8.9 with perfect knowledge) and never moved clean writing. Its reach is ±1.06 mm (a ±1.5 mm option doubles its small power). The biggest unknown is the lowest ink force a ballpoint writes with, which sets the power (8 mW at 0.15 N, 184 mW at 0.69 N). A slim core works only with piezo benders (±0.56 mm).
   - **Physics first.** A handheld pen can push the hand only against a mass inside it, against the hand itself, or against the paper. A moving mass gives F = m(2πf)²X, which is tiny at handwriting frequencies (below about 5 Hz): the best 45 g end-cap moves the ink at most 0.21 mm and a gyroscope 1.06 mm, against the 2 mm needed (SIM). The paper, used as ground through a small wheel at the heel, gives 0.3–0.6 N on the hand (CALC on an assumed tyre friction, to measure in EXP-D01).
   - **Tip (nose v2, DEC-036).** The refill tilts on a gimbal 76.5 mm behind the ball, driven by a 2 × 2 magnet checkerboard across a spherical gap: ±6.0 mm of ball travel guaranteed over 35–75° of tilt (Rev H ±2.75 mm), in a Ø24 handle. A pen lift (electro-permanent brake and latch) separates strokes. **Autowrite** (a mode the user turns on) writes a known text in the writer's style while the hand sweeps along the line: 99.2 % of letters and 100 % of words read with up to 1 mm of tremor, 98 % at 2 mm; 2.5 mm letters at 3.7 letters/s (SIM).
   - **Heel (paper-grounded drive, DEC-037, DEC-048).** A 2 mm wheel in the skid ring; the first studies steered it by default (the cobot principle: it keeps the hand on the letter's path and cannot move the pen by itself); it is now retracted by default (above). In the simpler HW1-D model, Parkinson's "write big" loops reached 0.99 of the target height with steering alone (0.78 with nothing; contested by the physics simulation, where only the driven wheel kept the last loop big); tracing error 582 → 76 µm with the nose, although letters read fell from 92 % to 79 % (closer to the template is not more legible); lead-through drew a letter bowl within 0.3 mm in 93 % of runs. A writer who resists always wins: a letter the writer is set on was never turned into another (0 %).
   - **Tail (reaction-mass end-cap, DEC-038, DEC-045).** A tungsten slug moved ±4 mm on 5 Hz flexures in a detachable end-cap: in the simpler H1 model a further 5.6 / 16.8 / 18.3 % tremor reduction on top of the nose at grip splits 0.3 / 0.5 / 0.7 with Rev J.1's 29.6 g end-cap (8 / 18 / 20 % with the first 43 g design), and cues in pauses; **in the physics simulation, no gain** (0.67 of the ordinary pen's error with it, 0.65 without), and study W's tails never robustly beat the same mass locked, so **inertial tails are rejected for the product** (DEC-051). It cannot steer letters.
   - **Algorithms and AI (DEC-042, DEC-043, DEC-047).** In the simpler HW1 model a tremor-line detector switching on a listening (fixed-lag Kalman) tracker gave, for essential tremor 1–2 mm at 6–10 Hz, ink error 830 → 430 µm (Rev H's tracker 627) and words read 31 → 74 %, including 6 Hz where Rev H did nothing; in the physics simulation this tracker moved tremor-free writing by 59 µm (rule 25 µm), so the guarded tracker G4 replaces it there. A causal TCN reaches 278 µm but stays in shadow mode until real recordings. Delayed ink and next-letter steering did not help, and RL driving the nose read more words but moved clean writing too much; RL is used offline to design shared control. The app gains word completion and labelled style synthesis.
   - **Simulator v2 (DEC-040).** MuJoCo physics of the hand, pen, moving nose, refill and paper, with the heel wheel and end-cap as plug-ins, domain randomisation and a Gymnasium environment. On the earlier hand–pen model's 56 test cases it reproduces the uncorrected ink error within 3.1 % in every case, the perfect-knowledge ratio within ±0.03 in 52 and the tracker's ratio within ±0.05 in 50 (the misses are the Rev H tracker's frequency lock, not the plant); it converges and conserves energy; it also showed that the synthetic writers write at half adult speed with about ten times the measured 8–12 Hz motion, which makes tremor separation look harder than it probably is (refit on recordings, EXP-V03). Until bench identification, it ranks designs only (ASME V&V 40 context COU-1).
   - **Integration and Rev J.1 fixes (DEC-044, DEC-045; CALC).** Rev J.1 is Ø24 × 143.9 mm and 84.3 g, or 161.9 mm and 112.7 g with its lighter end-cap (target 120 g). It fixes what the first layout found: 75 µm gimbal strips carry the 12–22 N magnet pull (buckling 55 N); a low-power page sensor and datasheet-counted electronics give 8.5–9.7 h at 1 mm tremor; a 0.1 mm graphite sheet keeps the skin at 35.9 °C in a 30 °C room; a clear window shows the ink near the ball in 47 % of tilt × eye cases (was 22 %). All battery and heat numbers rest on the nose-coil power model, which left out the static side load; they are suspended (the physics simulation measured about 2.3 W).
   - **Round 4 (running, `docs/round4_plan.md`).** At the user's direction: shifting and pivoting the whole pen against large Parkinson's and essential tremor (gyroscopic tail, tuned mass, pivot grip, paper-grounded force, ink only when in reach); real recorded handwriting and tremor as simulation inputs; a physical spell checker, better word prediction and shape assist; results shown as one understandable number per condition.
   - **Measurement rigs (study M, `docs/measurement_rig.md`, DEC-058, DEC-059; PROPOSED DESIGN, CALC, synthetic checks).** Six bench rigs on one data-acquisition box and a converted 3-D printer, in the order the independent review asks: R9 contact and ink (gate G1: the lowest refill force that writes, the axial and paper-normal forces measured apart, and the static side load; it also runs EXP-J17), R10 page sensing on paper against DeltaPen, R11 recording pen and tablet protocol (real tremor and writing forces), R12 actuator coupons (G2), R13 loaded nib (G3, G4) and R14 grip simulant (G5: a moving collar or tail against the same mass locked). No rig exists yet; the firmware is written but not compiled for the board.
   - Rev H corrections found on the way (DEC-041): the nose actuator's force constant is 0.19 N/√W by an image-method model, not 0.47; the refill's front stop must follow the nose; the ink-force spring needs a fatigue rating.

**Where the simulations are, and what the optimisation studies found:** [`docs/optimisation.md`](docs/optimisation.md). The 3D replay page is `viewer/index.html` (`python3 viewer/build.py --variant Q`); the Rev J explainer is `viewer/explainer/index.html` (`python3 viewer/explainer/build.py`).

## Completion table

States: **drafted** (text or design, not run) · **executable** (code runs, results depend on unverified inputs) · **executed** (run here; outputs in `results/`) · **hardware pending** · **measured** (none yet).

| Brief area | Deliverable | State | Evidence |
|---|---|---|---|
| 1 Research | Audit and recalculation of the report (37/37 numbers reproduce; 28 corrections) | executed | `analysis/audit_recalc.py` → `results/audit/` |
| 1 Research | Evidence ledger (692 sources, 8 streams) and synthesis | drafted | `docs/evidence.csv`, `docs/research_synthesis.md` |
| 1 Research | Ranked research questions with decisive experiments | drafted | `docs/research_questions.md` |
| 2 Mechanics | Parametric CAD (Rev A, Rev A.1) with interference checks, STEP, drawings | executed | `mechanics/cad/`, `results/cad/` |
| 2 Mechanics | Flexures, tolerance stacks (S1–S6), mass/CoM budget, configuration trade | executed | `mechanics/`, `results/mechanics/`, `results/trade/` |
| 2 Mechanics | Stage-A loaded bench rig (dimensioned concept CAD) | executed (design) · hardware pending | `mechanics/cad/bench_rig.py`, `results/cad/drawing_bench_rig.png` |
| 3 Electronics | KiCad 8 schematic: 11 sheets, regenerated deterministically; ERC 0 errors; netlist cross-check pass; PDF; BOM with VERIFY/SELECT | executed | `electronics/kicad/`, `electronics/bom_revA.csv` |
| 3 Electronics | Drive/sense calculations, including the supply-headroom assessment of the winding (6 Ω binds at 3.3 V in the hot, high-force corner; 4 Ω does not); ngspice drive stage incl. fault; placement study | executed | `electronics/calcs/`, `electronics/spice/`, `results/electronics/` |
| 3 Electronics | PCB layout and fabrication outputs | **not started** (blocked by DEC-014) | `electronics/README.md` E-1 |
| 4 Simulation | Coupled pen–hand–paper model M1: 12 verification tests; tuning/test split; grid, Monte Carlo, sensitivity, failures, design sweeps, frequency-gate diagnostic | executed | `sim/`, `results/sim/`, `docs/sim_report.md` |
| 4 Simulation | EM field models; thermal network with a two-node reduction for the firmware governor | executed | `analysis/`, `results/em/`, `results/thermal/` |
| 4 Simulation | Validation plan per model | drafted | `docs/physics.md` (table), `validation/` |
| 5 ML | Synthetic data pipeline with writer-disjoint splits; six conventional baselines tuned on validation; causal TCN; int8 quantisation (no loss); C export bit-exact with the Python reference, also on emulated Cortex-M33; MCU budget (exported model without f_est: 16.2 k MAC, 7.3 kB weights, 0.58 kB RAM); model and dataset cards; 22 tests | executed (synthetic only) · real data pending (EXP-H01) | `ml/README.md`, `results/ml/` |
| 6 Firmware | C control core: 40 kHz current loop, 2 kHz stage task, Kalman and band-pass estimators, guided mode, Jacobian with tilt-dependent γ, two-node thermal governor, safety state machine, ML guard (ICD §5 v1.2), calibration records, ICD log writer. Parameters generated from the YAML with a freshness check; golden vectors and replays from the simulator; 60 test cases (1120 checks) pass on host (ASan/UBSan) and on emulated Cortex-M33; nRF5340 image builds (32.3 kB flash). Register-level drivers are stubs marked VERIFY | executed (host, emulator, build) · hardware pending | `firmware/README.md`, `results/firmware/` |
| 6 Product | ICD log reader/writer with CRC and resync (parses the firmware's golden log with zero issues); immutable content-addressed note store with provenance-carrying derived layers; segmentation; SVG rendering; recogniser interface (on-device adapter specified); FTS5 search with stroke citations; grounded assistant that refuses unsupported, uncited or clinical answers; capture-fidelity analysis; digital autocorrect as a derived layer; 147 tests | executed (synthetic data) · real recogniser pending | `app/README.md`, `results/app/` |
| 7 Validation | 173 experiments with criteria (130 bench/offline, 43 human) with procedures, equipment, uncertainty and decision rules, including the Rev J and Rev J.1 studies (EXP-D, K, N, L, V, J); 581 acceptance criteria (232 requirement, 82 derived, 267 hypothesis; checker passes) against 172 requirements; prototype stages A–D with gates; human study plan separating immediate assistance from lasting improvement; review of 33 document inconsistencies, now resolved or recorded | drafted · hardware and participants pending | `validation/README.md` |
| Pencil | Pencil-class concept: CAD (Q and L layouts, fit checks, STEP, drawings), mechanism study (forces, 12 mechanisms, drive power, drop), pencil model P1 (skid, spring-loaded refill, piezo stage; exact match with M1 when locked), page-sensor rate study, touchdown tails | executed (design, calculation, simulation) · hardware pending | `docs/pencil_concept.md`, `docs/pencil_mechanisms.md`, `mechanics/cad/pencil_revP.py`, `sim/pencil/`, `results/pencil/` |
| Pencil | AI prediction and guidance (text predictor, style templates, stroke continuation, closed loop on P1 and M1, deployment and ICD proposal) and app autocorrect | executed (synthetic data) · people pending (EXP-A02/A03) | `docs/ai_guidance.md`, `aiguide/`, `results/ai/` |
| Pencil | Inertial and pivot stabilisation study: hand-pen model H1 with pen tilt in a two-zone grip; weights, gyroscopes, CMGs, reaction wheels, grip sleeve, passive pivots | executed (simulation, calculation) · grip measurement pending (EXP-I01) | `docs/inertial_stabilisation.md`, `sim/handpen/`, `results/pencil/inertial*.json` |
| Pencil | Sensing and AI estimation: IMU parts and lever arm, acceleration-domain Kalman, WFLC/BMFLC, learned GRU, template prior, 20 s personal calibration, closed loop on P1 | executed (simulation) · real data pending (EXP-H01/E01) | `docs/sensor_fusion_ai.md`, `fusion/`, `results/fusion/` |
| Pencil | Slim pencil hardware optimisation (P0.2): differentiable design model (exact against design.py and the CAD), adjoint gradients, Bayesian optimisation and CMA-ES over real and supplier-standard parts, finalists ranked in P1, BOM, CAD with STEP | executed (calculation, simulation) · custom plates to quote (EXP-Q04) | `docs/opt_hardware.md`, `opt/hardware/`, `results/opt/hardware.json` |
| Pencil | Tracker optimisation: differentiable accelerometer Kalman filter (PyTorch, and a hand-written numba adjoint), tuning of all 23 settings by backpropagation through time, Pareto front against false correction, learned trackers on the tremor band, per-writer gradient tuning; recorded-data pipeline | executed (simulation) · real writing pending (EXP-E01) | `docs/opt_tracker.md`, `opt/tracker/`, `results/opt/tracker.json` |
| Pencil | Touchdown and lift optimisation: stage feed-forward, stop margin and servo retune; adjoint gradients of a differentiable reduced model (torch), ParEGO Bayesian optimisation and CMA-ES on P1; faster slide-sensor option | executed (simulation) · bench pending (EXP-Q08) | `docs/opt_touchdown.md`, `opt/touchdown/`, `results/opt/` |
| Pencil | 3D replay page of the simulated pencil with generated tables | executed | `viewer/` (`python3 viewer/build.py`) |
| Rev H | Bigger-grip pen: tip design A against B, adjoint design of the nose actuator, ParEGO tracker for ±3 mm, rear inertial module, gyroscope and passive-weight options, neural reaction-mass controller, envelope tiers, CAD with STEP (with and without the module), BOM, power; H1 extended with regression tests | executed (calculation, simulation) · grip and bench pending (EXP-I01, I05, I06) | `docs/opt_inertial.md`, `opt/inertial/`, `mechanics/cad/revH_pen.py`, `results/opt/inertial_opt.json`, `results/revH/` |
| Rev H | Handwriting outcomes per condition (essential tremor, Parkinson's micrographia, poor handwriting, dyslexia) in model HW1, cross-checked against P1; scorer for real recordings | executed (simulation) · people pending (EXP-W01…W05) | `docs/handwriting_outcomes.md`, `handwriting/`, `results/handwriting/` |
| Rev H | Guidance board: architecture comparison, magnet force maps, stage, Hall sensing, guidance control, CAD, BOM | executed (calculation, simulation) · hardware pending (EXP-G01…G07) | `docs/guidance_board.md`, `board/`, `mechanics/cad/guidance_board.py`, `results/board/` |
| Rev H | 3-D explainer: components, how it moves, before/after writing, evidence level of every number; smoke test | executed | `viewer/explainer/` (`python3 viewer/explainer/build.py`) |
| Rev H | AI help for severe tremor: letter prediction as a tracker prior and as nose guidance, a severe-tremor tracker setting, the app's digital clean copy; safety (wrong letters, agency, false correction); rules fixed on tuning writers | executed (simulation) · recordings pending (EXP-W02, EXP-A03) | `docs/ai_severe_tremor.md`, `aiprior/`, `results/aiprior/` |
| 4 Simulation | Sim-to-real: virtual bench with instrument models, blind identification of 15 plants in protocol order, bench-time study, calibrated-twin prediction gap, model-form diagnostics, piezo hysteresis identification, domain randomisation, hardware-in-the-loop specification; 22 tests | executed (twin experiments) · bench pending | `docs/sim_to_real.md`, `validation/sim_to_real.md`, `s2r/`, `results/s2r/` |
| Rev J | Plan and plain-words concept: what acts at the tip, heel and tail, results per condition, modes, whether it can write for you, what to test first | drafted | `docs/revJ_plan.md`, `docs/revJ_concept.md` |
| Rev J | Study D, paper-grounded heel drive: traction over the writer population, tyre mechanics, driven ball, omni-wheels, steered and braked wheels, controllable friction; differentiable design optimisation; guided, lead-through and resisting-writer runs; force cap and lateral release; CAD | executed (calculation, simulation) · friction and bench pending (EXP-D01…D07) | `docs/grounded_drive.md`, `drive/`, `results/drive/`, `mechanics/cad/heel_drive.py` |
| Rev J | Study K, inertial end-cap: force ceilings, CMA-ES and autograd design of reaction masses, gyroscopes (CMG), reaction wheels and pseudo-force cues; tremor on top of the nose; letter steering; CAD | executed (calculation, simulation) · grip pending (EXP-I01, K08) | `docs/inertial_endcap.md`, `endcap/`, `results/endcap/`, `mechanics/cad/endcap.py` |
| Rev J | Study N, nose v2: magnet-array field models (magpylib), CMA-ES and adjoint optimisation over multi-pivot and multi-coil candidates, front-end closure at ±3–8 mm, pen lift, autowrite planner and test grid; CAD | executed (calculation, simulation) · coupons pending (EXP-N01) | `docs/nose_v2.md`, `nose2/`, `results/nose2/`, `mechanics/cad/nose2.py` |
| Rev J | Study L, AI and control v2: tremor-line gate, gated listening tracker, learned estimators (TCN, transformer, hybrid), delayed ink, RL (PPO, SAC) in Gymnasium, next-letter and next-word prediction, sigma-lognormal style synthesis, shared-control arbitration | executed (synthetic data) · recordings pending (EXP-H01, EXP-L01…L08) | `docs/ai_control_v2.md`, `ai2/`, `results/ai2/` |
| Rev J | Study V, simulator v2: MuJoCo 3.6 hand–pen–paper model with the H1 contact law, reproduction of H1, time-step convergence, energy balance, gyroscope check, MyoSuite impedance, literature validation, Gymnasium environment with domain randomisation, plug-ins; ASME V&V 40 contexts of use | executed · bench identification pending (EXP-V01…V06) | `docs/sim_v2.md`, `sim2/`, `results/sim2/` |
| Rev J | Integrated design: front end, placement along the pen, refill and pen lift, mass, power, heat and cost budgets, magnetics, 38 fit checks, simulator parameters, CAD with STEP | executed (calculation) · hardware pending | `docs/revJ_design.md`, `revj/`, `results/revJ/`, `mechanics/cad/revJ_pen.py` |
| Round 4 | Study B, the balanced nib (after the independent review): eleven load-balancing mechanisms designed for the 24 mm pen and a 12–16 mm core, magnetics, flexures, fatigue, thermal and ink-force models, multi-objective optimisation, closed-loop simulation in sim2, CAD of the recommended nib B1, interface file `config/nib.yaml` | executed (calculation, simulation) · bench pending | `docs/balanced_nib.md`, `bnib/`, `results/bnib/`, `mechanics/cad/bnib.py` |
| Round 4 | Study W, shifting the whole pen against large tremor: tremor targets, grip pivoting, collar, tuned masses, gyroscopes, paper-grounded force and write-when-in-reach designed and optimised; closed-loop simulation against the same pen locked at three grips; real tremor sizes; CAD of the reference collar | executed (calculation, simulation) · bench pending | `docs/whole_pen_shift.md`, `wholepen/`, `results/wholepen/`, `mechanics/cad/wholepen.py` |
| Round 4 | Study S, spelling help, prediction and clearer writing: causal streaming letter recogniser, recognition-aware spell checker from real misspellings, physical cues, personal word completion, why close tracing lowers legibility, shape assist, accepted-word writing planner, three separated outputs; a self-contained prototype page | executed (calculation, simulation) · people pending | `docs/spelling_and_clarity.md`, `ai3/`, `results/ai3/` |
| Round 4 | Study E, tremor tracking on real data: filters, WFLC/BMFLC, oscillator trackers and EPLL, Kalman trackers with new gates, study W's GLG, networks trained on real and synthetic writing; delay analysis; pre-registered choice frozen on tuning writers and tested once on held-out writers; MCU cost | executed (simulation with real recorded inputs) · none passes DEC-055 | `docs/real_tracker.md`, `realtrack/`, `results/realtrack/` |
| Round 4 | Study R, real recorded data: real handwriting (UNIPEN hpb2, chosen by a kinematics rule), real Parkinson's and essential tremor, severity classes at the pen tip, a measured-error page sensor, a literal handwriting reader (TrOCR); held-out writers, texts and patients; the bridge from synthetic to real inputs; licences respected (only statistics of restricted data committed) | executed (simulation with real recorded inputs) | `docs/real_data.md`, `realdata/`, `results/realdata/` |
| Rev J | Study M, measurement rigs for the review's gates G1–G5 and page sensing: six rigs (R9–R14) on one 24-bit DAQ and a converted CoreXY printer; CAD with STEP files, drawings and fit checks; DAQ firmware (written, not compiled for the board); USB logger, unit conversion, clock sync, calibration, uncertainty budgets and every analysis, tested on synthetic data (49 self-test checks, 25 tests); offline tablet recorder; bill of materials; 17 experiments (EXP-T01…T17) | executed (design, calculation, synthetic checks) · hardware pending | `docs/measurement_rig.md`, `rig/`, `results/rig/`, `mechanics/cad/rig_*.py` |
| Rev J | Whole-pen closed loop in simulator v2: nose, heel wheel and end-cap together; trackers compared on tuning writers and frozen before the test; results cards per condition; power split; page-sensor error; writer model v2 | executed (simulation) · ET test writers 4–5, the second seed and RL training still to run | `docs/revJ_simulation.md`, `sim2j/`, `results/sim2j/` |
| — | Engineering recommendation: route, conflicting targets with limiting calculations, custom hardware, AI data needs, evidence per benefit | drafted | `docs/recommendation.md` |
| — | Interfaces, decisions, plan with effort ranges (100–174 pw) and quotation list, environment lock | drafted | `docs/icd.md`, `docs/decisions.md`, `docs/plan.md`, `ENVIRONMENT.md`, `requirements.txt` |

## Reproduce

Environment: [`ENVIRONMENT.md`](ENVIRONMENT.md) (Python 3.11 with `requirements.txt`; KiCad 8.0.9; ngspice 42; arm-none-eabi-gcc 13.2; QEMU 8.2).

```bash
python3 -m pip install -r requirements.txt
python3 analysis/audit_recalc.py                    # report recalculation
python3 -m pytest sim/tests -q                      # simulator verification
bash sim/run_all.sh                                 # simulation evidence chain (10-25 min)
python3 mechanics/cad/pen_revA.py --variant A1      # CAD, mass, interference
python3 mechanics/tolerance_analysis.py && python3 mechanics/mass_budget.py
python3 electronics/gen/design_revA.py              # schematic; then kicad-cli ERC/netlist (electronics/README.md)
python3 electronics/calcs/drive_sense.py
(cd electronics/spice && ngspice -b drive_stage.cir && python3 plot_drive_stage.py)
```

Pencil concept:

```bash
python3 mechanics/cad/pencil_revP.py --variant Q      # pencil CAD, fit checks, mass (also --variant L)
python3 analysis/pencil_mechanisms.py                 # forces, mechanisms, power (about 90 s)
python3 -m sim.pencil.run_study                       # pencil model P1 (about 95 s); tests: python3 -m pytest sim/pencil/tests -q
python3 -m sim.pencil.diag_touchdown_tails            # touchdown tails and the tilt-adaptive stop
bash aiguide/run_all.sh                               # AI prediction, guidance and autocorrect (about 15 min)
bash s2r/run_all.sh                                   # sim-to-real twin experiments (about 30 min on 2 processes)
python3 -m sim.handpen.run_study                      # weights, gyroscopes and pivots (about 5 min); tests: python3 -m pytest sim/handpen/tests -q
python3 -m fusion.run_study --workers 2               # accelerometer tracker and AI estimation (tests: python3 -m pytest fusion/tests -q)
python3 -m fusion.viz                                 # 3D replay of the tracker
python3 -m opt.hardware.run_study                     # slim pencil hardware optimisation (P0.2); tests: python3 -m pytest opt/hardware/tests -q
python3 -m opt.tracker.run_study                      # tracker tuned by adjoint and learned trackers (3-4 h on 2 cores); tests: python3 -m pytest opt/tracker/tests -q
python3 -m opt.touchdown.run_study                    # touchdown feed-forward and servo optimisation (about 1.5 h on 2 processes; --quick smoke run); tests: python3 -m pytest opt/touchdown/tests -q
python3 viewer/build.py                               # 3D replay page from the results
```

Rev H (bigger grip):

```bash
python3 -m opt.inertial.run_study                     # nose, tracker, inertial module (about 35 min; --quick about 2 min); tests: python3 -m pytest -q opt/inertial/tests
python3 mechanics/cad/revH_pen.py [--addon]           # Rev H CAD, fit checks, STEP (--addon: with the inertial module)
python3 -m handwriting.run_study                      # before/after writing per condition (--quick smoke run); tests: python3 -m pytest -q handwriting/tests
python3 -m board.run_study                            # guidance board (about 2-3 min); tests: python3 -m pytest -q board/tests
python3 -m aiprior.run_study                          # AI help for severe tremor (about 20 min; --quick about 5 min); tests: python3 -m pytest -q aiprior/tests
python3 -m opt.inertial.front_end --sens              # Rev H front-end closure and its sensitivity check (about 1 min)
python3 mechanics/cad/guidance_board.py               # board CAD and drawing
python3 viewer/explainer/build.py                     # 3-D explainer page from the results
```

Rev J (tip, heel and tail):

```bash
python3 -m drive.run_study                            # heel drive (about 50 min; --quick about 5 min); tests: python3 -m pytest -q drive/tests
python3 -m endcap.run_study                           # end-cap (about 75 min; --quick about 2.5 min); tests: python3 -m pytest -q endcap/tests
python3 nose2/run_study.py                            # nose v2 and autowrite (about 2-3 h; --quick about 1.5 min); tests: python3 -m pytest -q nose2/tests
python3 -m ai2.run_study --workers 1                  # AI and control v2 (about 4 h; --quick about 40 min); tests: python3 -m pytest -q ai2/tests
python3 -m sim2.run_study                             # simulator v2 (about 3 h; --quick); tests: python3 -m pytest -q sim2/tests
python3 -m revj.run                                   # integrated layout, budgets, simulator parameters (about 25 s); tests: python3 -m pytest -q revj/tests
python3 -m bnib.run_study                             # the balanced nib (a few hours in stages; --quick); tests: python3 -m pytest -q bnib/tests
python3 -m wholepen.run_study                         # shifting the whole pen (a few hours in stages; see docs/whole_pen_shift.md §9); tests: python3 -m pytest -q wholepen/tests
python3 -m ai3.run_study                              # spelling, prediction and clarity (several hours; --quick about 8 min); tests: python3 -m pytest -q ai3/tests
python3 -m realtrack.run                              # tremor tracking on real inputs (about 5 CPU h; --quick); tests: python3 -m pytest -q realtrack/tests
python3 -m realdata.run                               # real recorded inputs (downloads the open datasets; about 2.5 h; --quick about 15 min); tests: python3 -m pytest -q realdata/tests
python3 -m sim2j.run_study                            # whole Rev J pen in simulator v2 (several CPU hours; one writer per process: SIM2J_WRITERS=4 ... --stages et); tests: python3 -m pytest -q sim2j/tests
python3 mechanics/cad/revJ_pen.py [--no-endcap]       # Rev J CAD, STEP and drawing
```

Firmware, ML and app have their own build and test commands in their READMEs.

## Repository map

`config/parameters.yaml` holds every parameter with unit, range, status and source (v0.4.4); `config/pencil.yaml` overlays it for the pencil concept (P0.1.2). The directories:

| Directory | Contents |
|---|---|
| `stabpen/` | Shared physics |
| `analysis/` | Audit, EM, thermal, trade |
| `sim/` | Coupled simulator (M1 in `sim/pensim/`, pencil model P1 in `sim/pencil/`) |
| `mechanics/` | CAD, flexures, tolerances, mass |
| `electronics/` | Schematic, calculations, SPICE, BOM |
| `firmware/` | Embedded control core |
| `ml/`, `data/` | Learned predictor pipeline, schemas |
| `app/` | Companion software |
| `aiguide/` | AI prediction, templates and guidance studies (pencil concept) |
| `fusion/` | Sensor models and tremor trackers |
| `opt/` | Optimisation studies: touchdown, tracker, slim hardware, Rev H inertial and front end |
| `handwriting/` | Handwriting outcomes model HW1 and the recording scorer |
| `aiprior/` | AI help for severe tremor: tracker prior, guidance, clean copy |
| `board/` | Guidance board study |
| `drive/` | Rev J heel drive (paper-grounded wheel) study |
| `endcap/` | Rev J inertial end-cap study |
| `nose2/` | Rev J nose v2 and autowrite study |
| `ai2/` | Rev J AI and control v2: trackers, learned estimators, RL, text prediction, style synthesis, shared control |
| `sim2/` | Simulator v2 (MuJoCo) with plug-ins and a Gymnasium environment |
| `revj/` | Rev J integration: layout, budgets, magnetics, simulator parameters |
| `sim2j/` | Rev J whole-pen closed loop in simulator v2 (round 2) |
| `bnib/` | The balanced nib (study B): load-balancing mechanisms, optimisation, simulation, the B1 design |
| `wholepen/` | Shifting the whole pen (study W): collar, tails, paper force, write-when-in-reach, closed-loop simulation |
| `ai3/` | Spelling help, prediction and clarity (study S), with the prototype page `ai3/demo/index.html` |
| `realtrack/` | Tremor tracking on real data (study E): estimators, gates, learned networks, the frozen test |
| `realdata/` | Real recorded data library (study R): handwriting and tremor sets, severity classes, page-sensor error model, reader, HW1 runs on real inputs |
| `rig/` | Measurement rigs (study M): DAQ frame protocol, logger, analyses, self-test, Teensy firmware, tablet recorder |
| `s2r/` | Sim-to-real: virtual bench, identification, calibrated twin |
| `viewer/` | 3D replay page; `viewer/explainer/` the 3-D explainer (Rev J) |
| `validation/` | Experiments and studies |
| `docs/` | Everything written |
| `results/` | Generated outputs with provenance |
