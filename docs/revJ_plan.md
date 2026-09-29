# Rev J: a pen that moves itself, not only its tip (plan)

**Status: plan, 2026-09-28.** Nothing here is measured. Labels as elsewhere: SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION.

## 1. What the user asked for

- Much stronger physical effect on the writing: move and tilt the whole pen, not only the ink tip.
- More advanced tip manipulation: more electromagnets, pivots at several points along the pen.
- A clever inertial system, for example at the end of the pen, that shifts the pen: smoothing Parkinson's writing, helping predictively.
- A pen that "can literally somewhat write for you" while you hold it.
- Better algorithms and AI: smoothing, next-word prediction, adaptation, RL.
- More realistic, physics-based simulations with proper sim-to-real practice.
- Iterate the design, physics, simulation and AI together, for as long as needed.

## 2. Where Rev H stands (SIM, CALC; `docs/revH_concept.md`)

- The nose moves the tip ±3 mm; with perfect knowledge of the shake it removes 87–99 % of the ink error.
- With today's tracker it removes 22–50 % at 8–10 Hz and nothing at 4–6 Hz. Telling shake from writing in real time is the limit.
- The rear inertial module adds 6–17 %. AI letter prediction added 0–1 % (`docs/ai_severe_tremor.md`).
- The app's clean copy (look-ahead, after writing) reads 97 % of words at 1–2 mm of shake.
- The desk board can pull the pen along whole letters (0.4 N cap), but it is a separate device.

## 3. Physics that frames Rev J (CALC, first cut; each study refines it)

**A handheld pen can push the hand in only three ways.**

1. **Against an inertial mass inside the pen (ungrounded).** A mass m moved over a stroke X at frequency f gives at most F = m (2πf)² X.
   - 20 g over ±3 mm: 2.4 mN at 1 Hz, 21 mN at 3 Hz, 0.24 N at 10 Hz.
   - Writing lives below about 5 Hz (LIT CON-24), so a reaction mass can fight tremor but cannot move a letter.
   - A gyroscope (control-moment gyroscope) gives a torque h·ω for as long as its gimbal can turn. A Ø16 × 5 mm tungsten rotor at 20 000 rpm stores h ≈ 1.3 mN·m·s. At 10 rad/s of gimbal rate that is about 13 mN·m, for about 0.1 s per radian of gimbal travel. That is letter-stroke timescale, but small.
   - Asymmetric vibration can make people *feel* a pull in one direction without a net force (a perceptual effect). It guides by suggestion, not by force.
2. **Against the hand itself.** The nose (Rev H) reacts against the handle, so it moves the tip relative to the hand but does not move the hand.
3. **Against the paper (grounded through friction).** The pen always touches the paper while writing, with about 1 N of writing force (LIT CON-01).
   - A driven or steered rolling element at the skid can push sideways with up to μ·N: about 0.3–0.8 N for μ 0.3–0.8 (ASSUMPTION, to measure).
   - That is as strong as the desk board's cap (0.4 N) and 10–100 times what an inertial mass gives at writing frequencies.
   - A relaxed hand gives way about 0.35 mm per 0.1 N (CALC from LIT HAP-26, `docs/guidance_board.md`), so 0.5 N moves it about 1.7 mm.
   - A steered wheel (the "cobot" principle: steer, don't push; LIT PAT-27) can channel the writer's own motion along a path with almost no power, and it cannot push on its own.

**The strongest self-contained lever is therefore the paper, used as ground through the skid.** The nose adds fine, fast correction, and inertia adds tremor damping and perceptual cues.

**"Writing for you" inside the nose's reach.** With ±5–8 mm of tip travel, the nose could draw letters of 3–4 mm height on its own while the hand only sweeps along the line. Prior art: position-correcting handheld tools, and an actuated-nib pen that scribes predefined characters (LIT PAT-01).

**Delayed ink (algorithm idea).** The nose can let the ink trail the hand by a fixed delay: at 30 mm/s, 150 ms is 4.5 mm, within a ±5–6 mm nose. The pen could then clean each stroke with 150 ms of look-ahead, like the app's clean copy but on paper. Whether writers accept ink that trails the hand is a human question.

## 4. Studies, round 1 (parallel)

| Study | Package, doc, results | Question | Ledger ids | Experiment ids |
|---|---|---|---|---|
| D: paper-grounded drive | `drive/`, `docs/grounded_drive.md`, `results/drive/` | Driven ball, omni-wheels, steered or braked wheels, controllable friction at the heel: force, power, size, safety; guided writing | HAP-60…79, AMF-100…119, CON-36…45, PAT-30…34 | EXP-D01… |
| K: inertial end-cap | `endcap/`, `docs/inertial_endcap.md`, `results/endcap/` | Best inertial, gyroscopic and pseudo-force system at the rear: what it can steady, steer and cue | ACT-81…99, AMF-120…134, HAP-80…89, PAT-35…39, PDT-39…42 | EXP-K01… |
| N: nose v2 | `nose2/`, `docs/nose_v2.md`, `results/nose2/`, `mechanics/cad/nose2.py` | Multi-pivot, multi-coil tip manipulation with ±5–8 mm; autowrite within reach | AMF-135…154, ACT-100…104, OPT-50…54, PAT-40…44 | EXP-N01… |
| L: AI and control v2 | `ai2/`, `docs/ai_control_v2.md`, `results/ai2/` | Tremor–intent separation, delayed ink, prediction, handwriting synthesis, shared control, RL | EML-44…69, PDT-43…52, CON-46…52, HAP-90…94 | EXP-L01… |
| V: simulator v2 | `sim2/`, `docs/sim_v2.md`, `results/sim2/` | MuJoCo hand–pen–paper physics, muscle-based checks (MyoSuite), sensors, domain randomisation, validation and sim-to-real plan | CON-53…69, HAP-95…109, PDT-53…59, OPT-55…59, EML-70…74 | EXP-V01… |

## 5. Rules for every study

- **Evidence.** Label every number (SIM, CALC, LIT + ledger id, MFR + ledger id, ASSUMPTION). Never invent a result or a citation. Cite only sources actually opened; say "abstract only" when only the abstract was read. Give the URL or DOI.
- **Ledger rows.** Write proposed rows to `results/<study>/evidence_rows.csv` with the exact 23-column header of `docs/evidence.csv`, using the study's id range.
- **Files.** Write only in the study's own package, doc and results folder (and its CAD script if listed). Every other package is read-only. Do not edit `docs/evidence.csv`, `docs/decisions.md`, `docs/requirements.csv`, `validation/`, `README.md`, `CHECKPOINT.md` or `viewer/`: propose changes in the doc instead.
- **Data discipline.** Tune on tuning seeds or writers; fix the rules before touching test seeds; report test results only in the final tables.
- **Provenance.** Write result JSON with `stabpen.provenance`. Provide `--quick`. Keep tests fast (`pytest`, under a minute).
- **Compute.** Four CPU cores are shared by five studies: use one process for long runs (two briefly), and keep each study's total compute to a few hours.
- **No commits.** The lead commits snapshots.
- **Hand-back.** Main results table, files, proposed decisions, requirements and experiments, open issues.

## 6. Envelope for Rev J (ASSUMPTION, lead; studies may argue for changes)

- Handle Ø ≤ 24 mm where held; the rear end-cap may reach Ø 26 mm. Length ≤ 175 mm.
- Mass ≤ 120 g with every module. Battery ≥ 8 h of writing with assistance on.
- Force on the hand from any grounded drive: software cap to be set from the literature (the board uses 0.4 N); the pen always yields to a writer who resists.
- "Writes for you" only in an explicit mode the user turns on; assistance modes never start a stroke on their own.
- Safety: stored rotor energy, magnets near implants, heat on the skin, pinch points.

## 7. After round 1

The lead integrates the studies into a Rev J architecture, with decisions, requirements, validation and the 3-D explainer. Round 2 then ports the chosen devices into simulator v2, trains and compares controllers (model-based, shared control, RL with domain randomisation), evaluates outcomes per condition, and optimises the design with the new models.
