# Round 4: shift the whole pen, use real data, show results clearly, spell-check on paper (plan)

**Status: plan, 2026-09-29.** Nothing here is measured. Labels as elsewhere: SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, PROPOSED DESIGN.

## 1. What the user asked (2026-09-29)

In the user's words:
- "not just the nib being moveable, but physically the pen to shift due to inertial ways of shifting the pen, because Parkinson's also does quite large hand tremors"
- "we need much better mechanics"; "physical pen shifting when pivoted in hand grip to be changed and made better also"
- "the writing improvement isn't good enough"
- "the simulations are not realistic and therefore the results that I see I can't understand ... what the results are, how much better they are etc isn't clear, there is too much data presented in an unclear way"
- "it's not clear to me how either work"
- "as well as the AI algorithms, optimisation, handwriting making clearer and text predictor / physical spell checker"

## 2. Where Rev J stands (SIM and CALC; `docs/revJ_concept.md`)

- **Tip.** The whole inner pen (refill, carrier and arm) swings on a gimbal 76.5 mm behind the ball, inside the shell you hold. The ball moves ±6 mm. It cancels tremor up to about 2 mm, and it can write a known text by itself while the hand sweeps along the line.
- **Heel.** A 2 mm wheel under the front ring grips the paper and pushes the hand with 0.3–0.6 N (friction ASSUMED). It steers by default and leads only in a mode the writer turns on.
- **Tail.** A 30 g tungsten weight in a detachable end-cap adds 8–20 % tremor reduction. It cannot move letters.
- **Limits.**
  - Tremor bigger than the ±6 mm reach cannot be cancelled.
  - The synthetic writers are unrealistic.
  - Results were shown in too many tables.
  - The battery, the pull on the gimbal and heat are open (study Rev J.1 is fixing them).

## 3. Physics for shifting the whole pen (CALC, lead; the studies refine it)

**Where the ink ends up.** The ink lands where the hand is, plus how the pen sits in the hand, plus where the tip sits on the pen. Tremor moves the hand. A pen can fight it in three ways:
- move the tip on the pen (the Rev J nose);
- change how the pen sits in the hand (pivot or shift the pen in the grip);
- push the hand itself.

**Pushing the hand needs something to push against.**
- **The paper**, through friction at a wheel or brake (Rev J heel).
  - At 5 Hz a hand behaves mostly like a mass of a few hundred grams. There, 0.5 N moves the tip about 1–2 mm (CALC, ASSUMPTION: 0.3–0.5 kg effective mass).
  - More normal load on the gripping element gives more force. The side of the hand normally rests on the paper while writing; a rest or sled could carry some of that weight onto a braked or driven element (to design).
- **A mass inside the pen.** Its force is F = m(2πf)²X. At 5 Hz, a 40 g mass over ±5 mm gives about 0.2 N. That is useful against tremor and useless for slow letter shapes.
- **A spinning rotor on a gimbal (control-moment gyroscope).** It gives a torque of h × gimbal rate. The gimbal rate grows with the tremor frequency, so torque is cheapest exactly where tremor lives.
  - Example: h = 5 mN·m·s with a ±1 rad gimbal swing at 5 Hz gives about 0.16 N·m. That is comparable with the torques that shake a wrist (CALC; sim2's arm model uses 32–188 mN·m for 1 mm of ET or PD tremor at the tip).
  - This is the principle of gyroscopic tremor gloves (to be found and cited).

**Pivoting the pen in the grip.** A mass or rotor at the tail can swing the pen strongly only if the pen is free to pivot in the fingers.
- In a normal grip the fingers clamp the pen, so the tail device must move the whole hand, and the effect is small (study K).
- If the fingers hold a collar and the pen swings in a gimbal inside it, a tail device only has to turn the pen's own inertia. The tip then moves opposite to the tail.
- **Conflicts to solve:**
  - the pen's tail normally rests on the web between thumb and index finger;
  - the tip drags on the paper;
  - the writing force must still be carried.

**Reach.** Moderate to severe tremor can move the hand by 1–3 cm peak to peak (rating scales; to be cited). No pen reach cancels that. A system therefore has to:
- cut the tremor itself (paper and gyroscope forces);
- cancel the rest within the nose's reach;
- lay ink only when the ball can be placed correctly ("write when in reach", using the pen lift and the autowrite planner).

## 4. Studies

| Study | Package, doc, results | Question | Ledger ids | Experiment ids |
|---|---|---|---|---|
| W: whole-pen shifting for large tremor | `wholepen/`, `docs/whole_pen_shift.md`, `results/wholepen/` | The strongest way to physically shift and pivot the whole pen against PD and ET tremor of 1–10 mm: gyroscopes, tuned masses, pivot grips, paper-grounded force, ink gating, combinations | ACT-120…139, AMF-180…199, HAP-115…129, PDT-63…74, CON-75…79, PAT-50…54, OPT-70…74 | EXP-W10… |
| R: real recorded data | `realdata/`, `docs/real_data.md`, `results/realdata/` | Real handwriting and real PD/ET tremor recordings as inputs; how the results change; before/after images that look like real writing | CON-80…89, PDT-75…84, EML-80…84 | EXP-R01… |
| S: spelling, prediction and clearer handwriting | `ai3/`, `docs/spelling_and_clarity.md`, `results/ai3/` | A physical spell checker, text prediction and shape assist that make writing clearer, on real handwriting and real spelling errors | EML-85…99, PDT-85…89, CON-90…94, HAP-130…134 | EXP-S01… |
| Done: whole-pen closed loop in sim2 | `sim2j/`, `docs/revJ_simulation.md` | Rev J in the physics simulator (DEC-046…049) | – | EXP-J17, J18, V07 |
| B: balanced two-axis nib (after the independent review) | `bnib/`, `docs/balanced_nib.md`, `results/bnib/` | Carry the static side load mechanically (DEC-046); a 24 mm pen and a 12–16 mm core | as assigned at launch | as assigned at launch |
| Done: M, measurement rigs (after the independent review) | `rig/`, `docs/measurement_rig.md`, `results/rig/` | Bench rigs for gates G1–G5 and page sensing (DEC-058, DEC-059) | AMF-220…238, OPT-85…92, CON-100…101, HAP-140…141 | EXP-T01…T17 |
| Running: Rev J.1 fixes | `revj1/`, `docs/revJ1_design.md` | Gimbal load, battery, heat, mass, ink visibility | ACT-105…119, AMF-155…179, OPT-60…69, CON-70…74, HAP-110…114, PDT-59…62, PAT-45…49 | EXP-J10… |
| Running: the 3-D explainer | `viewer/explainer/` | A clear, simple page: how each part moves, how much better | – | – |

## 5. Rules for every study (as `docs/revJ_plan.md` §5, plus clarity)

- **Evidence.** Label every number. Never invent a result or a citation. Cite only sources actually opened, and say "abstract only" when that is all you read. Give the URL or DOI.
- **Ledger rows** go to `results/<study>/evidence_rows.csv` with the exact 23-column header of `docs/evidence.csv`, using the study's id range.
- **Files.** Write only in the study's own package, doc and results folder. Everything else is read-only.
- **Data discipline.** Tune on tuning writers and seeds; fix the rules before touching the test seeds.
- **Provenance.** Result JSON carries `stabpen.provenance`. Provide `--quick`. Keep tests under a minute.
- **Compute.** Four CPU cores are shared by up to six studies: one process each.
- **No commits.** The lead commits.
- **Clarity (new).** Every study doc starts with:
  - "The answer in plain words";
  - a results table with ONE number per condition that anyone understands (for example "words you can read, out of 10", or "tremor at the tip, mm");
  - before/after pictures of writing that look like real writing.
  Detailed tables come after.

## 6. Common tremor severity classes (ASSUMPTION until studies W and R refine them)

Peak tremor amplitude at the pen tip, measured without any device:
- mild: 0.3–1 mm;
- moderate: 2–4 mm;
- severe: 5–10 mm.

Frequencies:
- essential tremor 5–10 Hz;
- Parkinson's action tremor 5–8 Hz;
- Parkinson's rest or re-emergent tremor 4–6 Hz.
