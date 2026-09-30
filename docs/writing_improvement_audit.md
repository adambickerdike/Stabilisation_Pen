# Accepted handwriting and spelling: executable improvement audit

30 September 2026. This audit adds executable accepted-text planning, continuous reference bounds, a contact/reference supervisor, matched plant replays, and a proposed grounded coarse/fine reference interface. It does **not** establish a handwriting, Parkinson's or dyslexia treatment benefit. Existing permanent ink cannot be changed by moving a pen later.

The central design conclusion is that a small correction stage and a machine that writes ordinary accepted letters have different workspace needs. A compact stage can correct a bounded part of a stroke. Whole letters and words need adequate relative travel, deliberate body repositioning, or an externally reacted writing mechanism. Learning cannot remove that geometric requirement. Internal moving mass cannot supply sustained displacement against the hand at DC.

All new evidence is in `results/improvement/writing/`; historic `results/ai3/` is preserved. Current generic-plant results are under `numerical_correction_50us/`. Earlier explicit-friction results are labelled invalid/superseded and preserved unmodified in `legacy_unstable_friction/`; see `NUMERICAL_STATUS.md`. The source hashes in each new JSON identify the exact implementation used. Results in this document distinguish a public recorded glyph, assumed text acceptance, a mathematical reference, a generic simulated plant, and the separate proposed mechanics. None is labelled a measured pen result.

## 1. Concrete gaps in the original implementation

`ai3/complete_plan.py` limits progress along a polyline, then selects a quantized waypoint. Its scalar path-speed limit is not a limit on actual stage velocity, acceleration or jerk after the moving body is subtracted. Pen-up movement is not subject to the same original admission test. The constant-velocity prediction used to ask whether a whole letter fits also lacks an explicit tube for future body-prediction error. Consequently, the historic 95% completion at ±6 mm is a kinematic simulation result, not evidence that a loaded actuator can make that motion. The new runner measures the old command trace on exactly the same glyphs and body assumptions as the new reference generator.

`WritingPlan` previously accepted an empty gate dictionary because `all({}.values())` is true. A plan could hold letters unrelated to the explicitly accepted suffix. Array mutation could alter an ostensibly fixed plan. Letter state transitions did not fully enforce accepted order. These are executable interface faults, not model-accuracy issues. `ai3/layers.py` now requires explicit reach/tracking gates, matches the plan text to the accepted suffix or separate rewrite, returns detached path copies, binds each trajectory to a content digest and plan ID, and refuses invalid transitions. The append-only ink digest now covers index and time metadata as well as points.

The application had a separate semantic problem: `autocorrect_note(write=True)` appends a recognition layer, and the latest recognition becomes the effective digital text. A correction can therefore look like a new literal reading. Historical evaluation remains reproducible, but the new interactive API is explicit:

1. `propose_autocorrect(store, note_id, ...)` makes no stored change. It uses current text, including the writer's edits, and excludes edited spans from proposals.
2. `accept_autocorrect(store, proposal, accepted_span_ids=...)` requires a nonempty explicit choice. It binds the proposal to the current note snapshot, rejects stale/tampered proposals, and records accepted changes as `user_edit`, preserving the original recognition and ink.

A runnable command-line path now wraps this API:

```sh
PYTHONPATH=app python -m penapp --store STORE propose-corrections NOTE --corpus local_sentences.txt --out new_proposal.json
PYTHONPATH=app python -m penapp --store STORE accept-corrections new_proposal.json --span-id offered_id
```

Repeat `--span-id` for each chosen proposal. The command uses a supplied local corpus, records its hash and does not download one implicitly. Proposal output cannot overwrite an existing file. Known words are protected by default. Unsupported alphabet tokens remain literal; the current ASCII model cannot rewrite them by transliteration. Acceptance appends a user edit and rebuilds the search index. This is a tested API/CLI, not a claim that every existing application screen has been migrated. `NoteStore` remains a single-writer store; this work does not add cross-process transactions.

## 2. From accepted text to bounded future ink

`ai3/accepted_completion.py` accepts an arbitrary explicit writer revision and glyph bank. A completion must preserve the deposited prefix. For example, accepted `becau` → `because` produces only `se`. A spelling revision such as `libary` → `library` produces a **separately placed rewrite**, never a fictional erasure of the old word. Missing or unreachable glyphs reject the whole proposed text before execution. The demonstration acceptances are synthetic integration inputs; no recognizer was credited with making them.

For each accepted letter, the body origin is proposed at the whole-glyph bounding-box centre. The old and new matched replay both receive that advantageous placement. Per-letter body repositioning is an explicit requirement. It is not hidden in a freehand motion predictor and is not supplied by an internal reaction mass.

`ai3/reachable.py` builds a quintic spline with zero velocity and acceleration at each ink-stroke endpoint. Each spline span is represented as a degree-five Bézier polynomial. The geometry deviation from the original recorded polyline has a convex-hull upper bound evaluated on intervals containing every original polyline knot. The generator refines spatial knots until this sufficient error bound is at most 75 µm. It then searches a fixed set of duration scales for an admissible path. It does not silently shrink a letter or draw only its reachable fragments.

This is a conservative search over retimed polynomial references. It is not a claim of time-optimality and does not implement TOPPRA or Ruckig. Reachability-based path parameterization and third-order online trajectory generation provide appropriate future comparison methods: [Pham and Pham, *A New Approach to Time-Optimal Path Parameterization based on Reachability Analysis*](https://arxiv.org/abs/1707.07239), and [Berscheid and Kröger, *Jerk-limited Real-time Trajectory Generation with Arbitrary Target States*](https://arxiv.org/abs/2105.04830). Their published performance cannot be transferred to this pen or this implementation.

For fixed 50° tilt, zero roll, and page x along the tilt plane, the coordinate map is

\[
q=M(r-b),\qquad M=\operatorname{diag}(\sin 50^\circ,1).
\]

The stage limit is the mechanical **radial** norm `||q||`, not independent x/y clipping. A radial stage therefore has an elliptical page workspace under this local map. This matches the coordinate convention of `revk.feasibility.page_to_nib_matrix`. Runtime observations must include measured tilt, roll and tilt-plane azimuth. A missing or changed pose rejects execution. Numerical equality within 10⁻⁶ degrees is explicitly a fixed-fixture assumption; it does not claim IMU accuracy. A freehand implementation still needs a certificate covering measured orientation uncertainty and angular dynamics.

For body prediction over one letter,

\[
e_b(t)=e_0+e_vt+\tfrac12e_at^2.
\]

The default assumptions are 25 µm initial error, 0.10 mm/s velocity error and 0.20 mm/s² acceleration error. These are demanding engineering inputs, not measured human behavior. The reach certificate includes this tube, 150 µm tracking reserve and emergency stopping travel. Longer duration reduces reference acceleration but increases the body-error tube; unlimited slowing is not a universal fix.

Every ink, lift, air and lowering span is checked continuously using Bézier convex-hull bounds. The nominal reference limits are 30 mm/s, 2 m/s² and 300 m/s³. The simplified planar force/electrical screen computes

\[
F=m\ddot q+c\dot q+kq+F_0,\quad I_i=F_i/K_i,
\quad V_i=RI_i+L\dot I_i+K_i\dot q_i.
\]

Bounds include load and load-slew uncertainty, prediction velocity/acceleration uncertainty, and the corresponding uncertain back-EMF. The scalar current observation means the maximum absolute value across both axes. Nominal coil/lead energy is integrated from the polynomial current; it is not a wire-temperature prediction.

The braking reserve starts with the positive acceleration bound, includes motion during reaction delay, ramps acceleration down at the jerk limit, holds deceleration when required, and ramps back to zero acceleration. This replaces the optimistic `v*delay + v²/(2a)` expression. Separate current/voltage bounds screen this assumed stopping profile. The result remains conditional on a servo actually supplying that profile. Motor-command clipping alone is not a plant safety proof, especially with saturation, unknown contact force or attitude change.

`StageModel` is explicitly a **generic planar translation model**. Some scalar values originated in Rev K, but it omits the actual mechanism's spatial force matrix, nonlinear suspension leads, virtual-work inertia mapping, lead thermal dynamics and normal-contact dynamics. A larger hypothetical radius in this model is not a supported larger Rev K build. The concrete mechanics postcheck is separate.

## 3. Execution and fault semantics

`CompletionExecutor` accepts only a path whose digest matches an immutable accepted plan and whose certificate still matches its contents. It emits time-indexed page position and analytic stage velocity/acceleration; it does not jump to the nearest waypoint. Feedforward is legitimate here because a future path has been explicitly accepted, not because future freehand intention is known.

The supervisor checks fresh page/body/tip observations, contact, current, temperature, fixed attitude, actual workspace, body-prediction error and reference tracking. Loss of an absolute page anchor, a changed page epoch, a stale observation, missed deadline or excessive error hands control back, requests braking and requests lift. Resumed relative optical counts do not recover the lost absolute reference. A failed plan cannot resume itself after apparently good readings return.

The default 20 ms lift/lower is a **fast-contact research assumption**, not Rev K counterface performance. The sensitivity matrix also uses 200 ms in both directions, motivated by the much slower counterface calculations. Neither setting is a measured bidirectional contact response. A 4 ms phase margin is added to each lowering/lifting dwell for the sampled supervisor. Replays retain actual contact during lift latency, including after a fault, so any resulting simulated ink remains in the record. No instantaneous lift or fictional latch is introduced.

`completion_replay.py` contains a transparent lumped plant: planar inertia, damping and stiffness; R-L current dynamics; back-EMF; current/voltage limits; delayed binary contact; and a PD servo. It compares feedback-only motion with analytic accepted-path velocity/acceleration feedforward on the same references. Acceleration commands and their vector slew are bounded. Reports also expose **actual** acceleration and jerk, which can exceed command bounds under plant mismatch.

The robustness cases alter mass/stiffness/damping by ±30%, weaken the force constant by 30%, add delayed/noisy position sensing and causal filtered velocity estimation, add lateral drag, combine these errors, and use slower contact. In noisy/delayed cases both the servo and the supervisor receive the delayed position. Neither receives hidden true velocity. The ideal baseline is labelled as such. The encoder model still assumes exact body/page registration and a rigid pose; it is not a measured sensor model.

## 4. Dataset and validation boundary

The recorded shapes are [UJI Pen Characters v2](https://archive.ics.uci.edu/dataset/177/uji+pen+characters+version+2), DOI `10.24432/C5FG8S`, CC BY 4.0. The dataset has 60 writers and two sessions, with a published 40/20 writer split. It records isolated character x/y coordinates, not timing, pressure or motion between strokes. Therefore the 3 mm x-height, timing, contact, composition into words and actuator behavior in this work are explicitly assumed. The citation in `ai3/data.py` has been corrected.

The 520-glyph capacity study uses all 26 lowercase letters from session 2 of the 20 published test writers. Writer scale is estimated only from that writer's session 1. Accepted-text integration uses their session-1 calibration glyph banks. The test-writer identities have already been used by prior repository development and this engineering work, so these are **replays and sensitivity analyses, not a newly untouched blind test**. Writer bootstrap intervals quantify variation across these 20 writers; they do not establish a population effect for Parkinson's or dyslexia.

Every matched baseline uses the same shape, scale, body origin and radius. The legacy metric is differentiated from its actual quantized command samples. The new reference's bounds are continuous sufficient bounds; the generic plant trajectory is separately simulated. A planned reference, an actually contacting simulated trajectory and a recognized character score are different endpoints.

## 5. Results

The completed 520-glyph comparison includes positive initial acceleration and jerk-limited braking reserves. All of the historic planner's completed commands fail the sampled 30 mm/s / 2 m/s² screen. The new counts are **admitted mathematical references**, not measured ink or complete-word success.

| Mechanical radius | Legacy geometric completion | New reference admitted | New admitted share, writer-bootstrap 95% interval | Median admitted glyph duration |
|---|---:|---:|---|---:|
| 1.0587 mm | 0/520 | 0/520 | 0.0% (0.0–0.0%) | — |
| 1.5 mm | 0/520 | 5/520 | 1.0% (0.2–1.9%) | 0.704 s |
| 2 mm | 17/520 | 60/520 | 11.5% (8.8–14.4%) | 0.868 s |
| 3 mm | 262/520 | 248/520 | 47.7% (41.5–53.5%) | 1.156 s |
| 6 mm | 517/520 | 495/520 | 95.2% (91.9–97.9%) | 1.585 s |

The 1.0587 mm radius is the historic conservative Rev K radial travel. The 1.5 mm radius is evaluated as a new mechanical candidate elsewhere; 2/3/6 mm in this table are hypothetical reference envelopes. These counts cannot support a compact ordinary-letter autowriting claim. The 2 mm result exceeds the old geometric planner partly because the new controller uses the physical page ellipse and continuous retiming; this is a matched-input system comparison, not an isolated algorithm-only ablation. At 3 and 6 mm, the admitted matched letters take approximately 3.57 and 3.76 times the legacy duration respectively.

The text integration uses twenty session-1 glyph banks and assumed explicit acceptance. Its baseline has exact state sensing and the nominal planar plant, 40 Hz feedback with damping ratio 0.85, 20 ms contact transitions, and assumed pen-up body repositioning. The corrected coupled integration is used throughout this table. Completion counts below are out of all twenty writers; RMS is conditional on complete texts, so it must not be used alone to compare policies.

| Accepted future text | Radius | Whole-text preflight | Feedback-only completed | Accepted-path feedforward completed | Feedforward median letter RMS, completed texts |
|---|---:|---:|---:|---:|---:|
| se suffix | 1.0587 mm | 0/20 | 0/20 | 0/20 | — |
| se suffix | 1.5 mm | 0/20 | 0/20 | 0/20 | — |
| se suffix | 2 mm | 2/20 | 0/20 | 2/20 | 10.3 µm |
| se suffix | 3 mm | 18/20 | 2/20 | 16/20 | 11.8 µm |
| se suffix | 6 mm | 20/20 | 3/20 | 18/20 | 12.8 µm |
| library separate rewrite | 6 mm | 16/20 | 2/20 | 11/20 | 7.9 µm |

### Corrected robustness and causal feedback

The first sensitivity matrix and subsequent observer development exposed a numerical defect during independent review: the former explicit 0.5 ms friction update was unstable near zero velocity. For radial drag `F_d tanh(||v||/v_s) v/||v||`, the small-velocity drag slope is `F_d/v_s`. At 20 mN, `v_s = 0.5 mm/s` and 3.44 g, the scalar explicit multiplier is approximately **−4.83**. A passive drag can then create kinetic energy. Earlier friction-case success and failure counts are not used as controller evidence; their exact original outputs and source are archived, not quietly discarded.

`ai3/planar_integrator.py` now jointly integrates the R-L coils, reciprocal back-EMF/force exchange, spring/mass/damping and radial friction using implicit midpoint. Internal steps are at most 50 µs; the original 0.5 ms servo/observer clock and 2 ms sensing/reference-supervisor clock remain unchanged. Voltage and contact are held per outer tick. The ideal current-limiter branch is solved inside the mechanical equation, then its required effective voltage is checked against the actual supply. Internal midpoint current integrates copper loss. A rail-infeasible limiter is rejected rather than supplying imaginary force.

Without applied voltage/bias, and with nonnegative dissipative terms, the midpoint energy balance cannot add stored mechanical/electrical energy. An independent agent checked 500 unclipped and 500 current-limited randomized states: energy/work residual was at most **1.24 × 10⁻¹⁹ J**, and mechanical impulse residual **4.62 × 10⁻¹⁸ N·s**. Analytic isolated friction decay follows

\[
v(t)=v_s\operatorname{asinh}\!\left(\sinh(v_0/v_s)e^{-F_dt/(mv_s)}\right).
\]

The recorded independent decay refinement agrees at second order. These checks establish numerical consistency for the stated equations, not that tanh friction describes a particular refill or paper. See `results/improvement/verification/writer_integrator_independent.json`.

The new feedback stack is `ai3/robust_completion.py`. For each axis it estimates position, velocity and a disturbance-acceleration state from timestamped position and ideal measured mean coil current. The nominal dynamics are

\[
\dot q=v,\qquad
\dot v=-kq/m-cv/m+K_iI/m-F_{0i}/m+d,\qquad
\dot d=w_d.
\]

The estimator corrects the historical state at a measurement's known acquisition timestamp and propagates already applied measured currents forward. It does not receive true load, true velocity or perturbed mass/force constants. The replay currently supports a fixed known delay aligned to the simulation clock; it is not a general asynchronous sensor fusion implementation. Assumed encoder noise is 10 µm and disturbance random-walk scale is 2 m/s²/√s. Two aligned large innovations can temporarily increase the load-state covariance. Force compensation is capped at 60 mN per axis. Independent recovery feedback is capped at a **40 mN vector** and **10 N/s vector slew**. Its bandwidth is bounded by the available force at the 150 µm tracking threshold, by 8% of the sensing/reference update rate and by a 40 Hz ceiling.

These are a complete observer/recovery stack comparison, not an isolated proof of the disturbance-state component. A fixed 10 mN nominal contact prior was tried during development and rejected; the frozen selected controller uses **zero contact prior**. Earlier process-noise, prior and recovery-slew experiments are preserved as development diagnostics. Position-noise/velocity-filter tradeoffs require explicit stability analysis; [Sariyildiz and Ohnishi, *Stability and Robustness of Disturbance Observer based Motion Control Systems*](https://arxiv.org/abs/1912.05046) explains why ideal velocity assumptions can conceal bandwidth/robustness limits. This implementation does not inherit that paper's stability guarantees.

All following generic-plant results use the corrected integration. The development replay is already used engineering data. Every row is the same hypothetical 3 mm stage and the same accepted `se` suffix; both policies use the selected stack's bandwidth and damping. The scenario names retain historical “20 Hz” tags in JSON, but the corrected gain-matched comparison uses the frozen common design. Counts require whole-plan completion **and true simulated position within the 150 µm stage tube**, independently of the observer's estimate.

| Development condition | Preflight admitted / 20 | Gain-matched path feedforward | Observer/recovery stack |
|---|---:|---:|---:|
| Nominal plant | 18 | 17 | 18 |
| Mass/stiffness/damping +30% | 18 | 17 | 18 |
| Mass/stiffness/damping −30% | 18 | 15 | 18 |
| Force constant −30% | 18 | 0 | 18 |
| Position delay 2 ms / noise 5 µm | 18 | 0 | 18 |
| Position delay 4 ms / noise 10 µm | 18 | 0 | 14 |
| Lateral drag 20 mN | 18 | 0 | 7 |
| Combined perturbations | 18 | 0 | 0 |
| Contact lower/lift 200 ms | 16 | 15 | 16 |

The noisy-delay and drag rows each have one additional supervisor “done” that fails the retrospective true-position check. Those two cases are correctly excluded. This exposes a remaining safety problem: estimated tracking alone is not an error bound.

Before its first evaluation, a second protocol fixed 60 mixed cases: three independently drawn combinations per writer, mass/stiffness/damping 0.7–1.3 times nominal, force constant 0.65–1.1, delay 1–4 ms, position noise 2–10 µm, drag 0–25 mN and 200 ms contact transitions. Its seeds, cases, gains and decisions were frozen. Correcting the numerical integrator then reran **the same already-spent cases**, with no controller retuning. It is simulator sensitivity, not a fresh human or blind model validation. Protocol/output reuse refuses changed or overwritten completed records.

Of all 60 scenarios, **48 pass preflight**. Gain-matched path feedforward completes **0/48** admitted texts. The observer/recovery stack completes **11/48** within the actual position tube, or **11/60 = 18.3%** of all scenarios. The descriptive writer-cluster bootstrap interval is 8.3–28.3%; it describes these simulation cases, not clinical effectiveness. Completed letters have median RMS **35.52 µm**. However, median required-ink contact coverage across all admitted cases is only **28.9%**, and the other 37 admitted cases abort for tracking error. Full-plan denominators include letters never started. Median ink persistence after an abort is **200 ms**, and median contact outside requested ink phases is **4 ms**. These are different quantities: post-abort wrong ink can occur during what was originally a requested phase.

Critically, **none of the 11 position completions passes both actual motion-rate limits**. Their internal acceleration peaks are 5.65–13.59 m/s² against the provisional 2 m/s² reference bound. Their internal constant-contact finite-difference jerk peaks are about 15,566–31,937 m/s³ against 300 m/s³. Instantaneous binary contact additionally creates an acceleration discontinuity, reported separately; it cannot be described as finite bounded jerk. Command/reference limits therefore do not establish plant smoothness or safe recovery.

Halving internal time steps from 50 to 25 µs preserves every completion/refusal decision and executed-letter count across all 96 admitted policy/case pairs. Maximum letter RMS change is **0.01165 µm**, peak acceleration change **0.078%**, peak current change **0.053%**, and copper-energy change **0.752%**. One refusal shifts by one 2 ms supervisor tick. Finite-difference peak jerk changes up to **8.5%**, so its exact magnitude remains resolution dependent; the large rate-limit failure is unchanged. Detailed comparison is in `numerical_convergence.json`.

These results support useful causal position-feedback engineering, but reject deployment of this generic stack as reliable physical autocorrection. Remaining work includes a measured force/contact model, a continuous contact transition, uncertainty-bounded state estimation and a recovery controller whose actual mechanical motion respects validated device limits. More tuning on these cases would remain development, not new validation.

The ideal coarse/fine split admits 506/520 glyphs (97.3%) at 0 or 50 N/m external stiffness, 196/520 (37.7%) at 200 N/m, and none at 500 N/m under its declared 0.4 N force cap. At zero stiffness the median admitted duration is 1.617 s. This is a useful **conditional architecture calculation**; it cannot be attributed to a person's unknown grip or to the concrete five-bar without that separate dynamics check.

## 6. A concrete route to ordinary accepted writing

`ai3/coarse_fine.py` makes a conditional allocation between 4 mm of page-plane coarse motion and a 1.5 mm radial nib, with a fixed split β = 4/5.5. It bounds the separate reference motions and an explicitly ideal carriage load. This is an architecture calculation, not a miniaturized collar design. Its 0.2 mm reserves are geometric/tracking assumptions; the ideal carriage screen is not an emergency-stop validation.

For absolute tip position `r`, coarse displacement `b_c` and fine coordinates `q_f`,

\[
b_c=\beta(r-r_0),\qquad q_f=(1-\beta)M(r-r_0).
\]

Fine inertial load uses **absolute** nib acceleration, not only relative-stage acceleration. For `A=M⁻¹`, the generalized fine force is `Aᵀ m r̈`; moving the body does not remove the nib's inertia. The exporter provides position and analytic velocity/acceleration for both stages, plus absolute tip acceleration, so the full mechanics model need not differentiate quantized samples.

The refined nib package is about 24 mm OD in the mechanics proposal. The old collar assumed a 12 mm inner pen, so combining those drawings without repackaging would be invalid. The mechanically developed writing option is instead a **grounded five-bar laboratory demonstrator**, described in `wholepen/grounded.py` and `wholepen/grounded_replay.py`. It supplies sustained reaction force through a desk-mounted base, with link Jacobians, reflected inertia, motor current/voltage, and the fine-stage spatial force map evaluated separately. That mechanism is distinct from a sleek handheld pen.

`export_grounded_completion.py` exports all 20 accepted `se` suffixes as complete two-letter references. Each contains 200 ms lowering/lifting phases and an explicit 500 ms minimum-jerk pen-up coarse/fine transfer between letters. The common page origin is retained, and the full word occupies the actual coarse working patch rather than silently resetting the body in the middle of a word. The 100 mm radius used internally to construct these references is merely a reference-generation envelope; the actual coarse/fine mechanism must pass its own postcheck. See `grounded_accepted/manifest.json` and the separate mechanics results for the subsequent actuator and coupled-plant checks.

The final coupled-mechanism replay in `results/improvement/mechanics/grounded_batch.json` completes all 20 suffixes with accepted-path feedforward plus feedback and no resisting grip spring; median actual requested-ink RMS is **0.03975 mm**, with 100% required-ink coverage, peak coarse force **0.29250 N**, and peak fine current **0.11384 A**. Feedback alone completes none. The fixed gains are 9 Hz coarse / 25 Hz fine from a separate pole screen. This uses the proposed spatial fine-stage map and coupled five-bar inertia, motor/current limits and delayed sensing; it is a materially stronger mechanism simulation than the generic planar example.

A separate derivative audit of those saved grounded traces finds **0/20** also meets both the provisional 2 m/s² actual-tip acceleration and 300 m/s³ sampled-jerk comparisons. Peak combined-tip acceleration is **3.696 m/s²** and sampled jerk **8,064 m/s³**; requested-ink jerk is also high, about **7,958 m/s³**. The derivative reconstruction was cross-checked against saved forces. The grounded simulation does not switch its guide-drag law at ink contact and does not model impact; ideal current-loop and noise-driven force changes can still produce high sampled jerk. Thus 20/20 is a position/contact result, not a complete physical motion-limit pass. See `results/improvement/mechanics/grounded_derivative_check.json`.

The same mechanism with start-neutral 200 or 500 N/m resisting grip springs completes **none** of the twenty suffixes. Median required-ink coverage is 28.16% / 26.24%, and median actual error is 0.968 / 0.944 mm. All twenty have some ink, so these error denominators are twenty, not only successful cases. A 200 ms lift leaves partial wrong ink after refusal: the clean-abort quality target remains unmet. These results support a **cooperative, grounded demonstrator**, not automatic writing against an arbitrary human grip, and not a small handheld product. The mechanical assumptions and remaining bench gates are detailed in `docs/mechanics_improvement_audit.md`.

## 7. What the existing AI evidence does and does not establish

The repository already reports several limitations honestly in `docs/spelling_and_clarity.md`. They matter more than a larger language model:

* The isolated-letter recognizer reaches about 82% final-letter accuracy on the UJI split and approximately 40% on the other capture dataset. This is a substantial acquisition/domain mismatch. It does not establish robust continuous pen recognition or reliable inference of the writer's intended letter under severe tremor.
* The approximately 20% word error rate uses words assembled from recorded isolated letters with assumed spacing and segmentation. It is not an evaluation on continuous natural writing captured by this physical pen. Every recognizer improvement must be tested on actual sensor trajectories and actual completed-word segmentation.
* Planned spelling rule W2 failed at about 1–3% detected misspellings. The subsequent W5 dictionary-aware candidate design reports about 34% detection at 1.7 false alarms per 100 correct words. The documentation labels this post-hoc work on a previously seen test set. It is evidence for an engineering hypothesis, not an independent validation. Confidence calibration cannot recover a correct word that has already been removed from the candidate lattice.
* Confusing recognition alternatives with spelling errors produces false cues. A calibrated alternative such as “perhaps the pen misread this” must remain distinct from “perhaps the writer intended a different word.” The new app proposal/accept API preserves this distinction in provenance but does not retrain or independently validate the scorer.
* The reported 52–56% top-three completion after one letter comes from a person's running text corpus. It does not measure motor benefit, dyslexia support or user acceptance. Familiar corpus continuation can be easy while rare names, out-of-vocabulary words and text-entry errors remain difficult. Those should retain an explicit keep-as-written path.
* The reported “3.4 of 10 misspellings fixed” depends on simulated user responses to cues. UJI glyphs and Holbrook spelling errors do not supply evidence that a person with dyslexia will perceive, accept or benefit from a moving pen. There is no new efficacy claim here.

The next AI evaluation should freeze recognizer, candidate generation, calibration and thresholds before collecting a separate cohort/session. It should report top-k **candidate recall before calibration**, calibration/risk-coverage curves, corrected and newly corrupted words, protected-name behavior, false cues per 100 correct words, response time, and physically completed accepted text. Recognition-only, oracle-letter spelling, full recognition-plus-spelling, and explicitly accepted physical execution must remain separate arms. No threshold should be promoted because it performed well on this replay.

## 8. Reproduction and acceptance gates

Run from the repository root with the installed scientific environment. Use new output directories when rerunning the frozen numerical studies; an identical numerical reproduction is not another independent validation:

```sh
OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q ai3/tests app/tests/test_autocorrect.py -k 'not corpus'
python -m ai3.run_reachable
python -m ai3.run_completion_replay --out results/improvement/writing/numerical_reproduction
python -m ai3.run_numerical_completion --phase development --out results/improvement/writing/numerical_reproduction
python -m ai3.run_numerical_completion --phase holdout --out results/improvement/writing/numerical_reproduction
python -m ai3.assess_robust_writing --out results/improvement/writing/numerical_reproduction
python -m ai3.plot_writing_audit --out results/improvement/writing/numerical_reproduction
python -m validation.writer_integrator_review
python -m ai3.coarse_fine
python -m ai3.export_grounded_completion
python -m ai3.accepted_completion --accepted-text because --written-prefix becau --writer tst_UJI_W12 --radius-mm 3 --out results/improvement/writing/numerical_reproduction/accepted_example_3mm --simulate
```

The latest dedicated `ai3/tests` run passes **71 tests**, including nine new integrator checks. The parent audit reports the updated app and full-repository suites separately; a local-corpus-only app workflow requires no external corpus download. Tests independently check minimum-jerk line motion, continuous bounds against dense derivatives, geometry against polyline distance, uncertain back-EMF, jerk-aware stopping distance by numerical integration, radial rather than square reach, air motion, consent/text matching, tamper resistance, contact/reference/attitude faults, causal delayed sensing and the full coarse/fine kinematic decomposition. The observer tests include future-mutation/prefix invariance, independent forced plants with wrong mass and force constants, covariance positivity, physical recovery-force/slew limits, and full-plan ink denominators. These are software checks. The broader integration suite is reported separately by the root audit.

The necessary hardware gates are measured stroke/current/temperature authority across the actual travel; actual stage position noise and delay; normal-contact and lift/lower response in both directions; orientation uncertainty; paper/refill friction; loaded frequency response and flexible modes; and a repeatable emergency stop with retained ink accounting. Then blinded human reading and matched user tasks can establish whether improved tracking makes writing more legible or useful. None of these gates is replaced by the current calculation or a favorable recognizer score.
