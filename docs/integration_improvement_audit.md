# Integration and reproducibility audit

30 September 2026. Base commit `4ad62b6acdcda1fa1102362f32780168297f5bb3`, branch `claude/pensive-shannon-wzm6ls`. Evidence here is code verification, calculation and simulation. No pen, coil, circuit, participant outcome or new sensor measurement was produced.

## What was recovered and preserved

The requested branch was fetched and fast-forwarded from `b1694a3` to `4ad62b6`. The local independent review and README edits were preserved with a stash, then reapplied successfully. The stash remains recoverable. The updated base contains 2,103 tracked files, 683 Python files and 74 Python test modules; the initial collection found 747 tests. The inventory in `results/improvement/verification/repository_inventory.json` records the inspected source tree. These counts describe scope, not a claim that every line or citation received independent review.

The work audited the current Rev K/B1 geometry and force path; predecessor pen, grip, contact, sensor and thermal models; current and trajectory loops; replay and physical learning environments; recognition, corrections and completion planning; and the tests linking these pieces. Historical generated reports and failed experiments are preserved. The detailed mechanical, control and writing audits identify the equations and code actually changed. Existing historical results are not rerun merely by rerunning unit tests.

## Sensor models must not reveal future or unobserved motion

`realdata/sensors.py` previously let a future trajectory alter past simulated sensor errors. Its invalid optical-flow intervals could also disappear from the integrated path when valid sensing resumed. Both faults made a causal controller's input better informed than the proposed hardware.

The default page model is now version 2. Its noise construction uses only present and preceding increments. Independent random streams give identical prefixes for identical input prefixes, even when a later record is extended. Invalid relative increments are never integrated or recovered from true motion. Relative flow may resume after a dropout, but absolute page registration remains invalid until another subsystem supplies a new anchor. Version 1 is an explicitly selected historical model; an old fitted cache cannot masquerade as the new model.

The reproducible check in `realdata/sensor_integrity_study.py` follows a 20 mm/s path with 100 invalid optical reports. Because both ends of an increment must be observed, 101 increments and 2.02 mm of displacement are lost. The old model returns to zero final error; the new model retains the unobserved 2.02 mm and marks the absolute reference invalid. In a future-mutation check, the old model changes earlier readings by up to 284.39 micrometres; the new model changes them by zero. These are deliberately constructed software checks, not sensor accuracy measurements.

![Missing motion and absolute registration](../results/improvement/sensing/dropout_integrity.png)

The metrology code in `rig/pagesense.py` now includes both interpolation brackets and shared window boundaries in validity checks. A trace with no valid windows or no valid two-sample stroke run returns an invalid result with NaN error, rather than a perfect zero score. Aggregators must count and report those invalid cases; dropping them from an accuracy denominator would recreate the bias elsewhere.

DeltaPen's published magnitude-error distribution is useful for setting an approximate scale, but it does not identify a unique two-dimensional error process, temporal spectrum, long-term drift or relocalisation behaviour. Version 2 is still a causal **assumed model**, not a sensor calibrated from vector residual recordings. Absolute position through lift, tilt, roll and arbitrary paper remains a hardware dependency. [DeltaPen, UIST 2022, full paper](https://static.siplab.org/papers/uist2022-deltapen.pdf)

## Numerical state must not silently change unrelated models

Four physics modules changed PyTorch's global default precision to float64 when imported. Later neural layers could therefore be float64 while their inputs and checkpoints were float32. The resulting errors depended on test order and which other studies had been imported.

The physics factories now request float64 explicitly; learned-model factories request float32 explicitly. Complex frequency responses remain complex128, including their imaginary part. Regression tests import the physics modules before constructing a learned model and check that the global default is unchanged. Other tests preserve the complex response and compare differentiation with numerical finite differences.

The CMA-ES implementation in `opt/touchdown/bo.py` had two separate reproducibility issues. Eigenvector signs can differ across numerical libraries without changing an eigensystem, changing a seeded random search. Those signs are now canonical. More substantially, covariance adaptation used unbounded proposal steps even when the evaluated candidate had been clipped to a constraint. It now uses the actual bounded displacement. An adversarial test flips every eigenvector sign and requires the same seeded search; another checks bounded evaluation.

The note schema validator formerly returned no errors if its optional dependency was unavailable. It now raises an actionable validation error, and `jsonschema==4.26.0` is an explicit requirement. The no-dependency case is exercised directly. No application operation should interpret missing validation software as a valid document.

Independent review also found a numerical defect in the newly added generic writing replay: its 0.5 ms explicit velocity update was unstable for the assumed 20 mN `tanh(v / 0.5 mm/s)` friction acting on a 3.44 g mass. The near-zero velocity multiplier is about -4.81; the local stability limit is 0.172 ms. `validation/friction_step_check.py` compares isolated free decay against its analytic solution and demonstrates nonphysical energy growth at the old step. This is a simulator defect, not a paper-friction measurement or controller benefit. The writing audit reports the stable integration repair and corrected replays of the same spent cases, with no gain retuning. The old results are retained as invalid numerical diagnostics. The separately grounded model has a smaller friction slope and received its own full-workspace energy-bound and decay check; stability and timestep accuracy remain distinct checks.

The new CLI connects the explicit proposal/acceptance API to a runnable offline workflow. `propose-corrections` uses an explicitly supplied local corpus and creates a reviewable JSON file without changing a note. `accept-corrections` requires offered span IDs, stores selected edits and refreshes search; stale/tampered proposals fail. The end-to-end check preserves original ink and literal recognition while checking the new search result. The CLI does not download a corpus or command physical pen movement. It uses the existing research ngram scorer rather than claiming a newly validated language model.

## Missing data and calibration identity

The licensed UNIPEN corpus and several ignored model/tuning caches are not in the clone. Their absence is reported explicitly. A missing writer pool no longer produces integer division by zero. An explicitly selected writer must belong to the requested split; a misspelled dataset name no longer falls through to BRUSH.

The personal calibration helper formerly inferred writer identity from a seed stride. It now selects the original writer explicitly while searching for a separate recording. A data-independent test uses a writer-pool size different from the stride and checks both identity and recording disjointness. The integration test requiring licensed UNIPEN data skips with its actual reason; no substitute data is called UNIPEN.

An old clean-handwriting geometry fixture also contained random allograph, scale and baseline changes. That was inconsistent with its assertion about exact clean glyph width. The clean fixture is now deterministic in those quantities. Existing evidence-ledger tests were updated to permit already-merged IDs only when citation and DOI agree; they still reject incompatible overlap.

## Historical output hashes across operating systems

Two regression groups compared bit-for-bit hashes generated under an earlier Linux numerical stack with macOS arm64 output. Such a hash checks exact floating-point execution, not physical equivalence across libm, LLVM and BLAS implementations. Saturated dynamics can amplify a small numerical difference; simply widening a tolerance or overwriting the old fixture would conceal this distinction.

The unchanged historical source is now exported from the Git commit recorded in each baseline and executed with the same interpreter and libraries as the current code. H1 uses `9d309a0`; P1 uses `410a173`. The historical Linux JSON/NPZ fixtures remain unchanged. Each generated reference is cached by source revision, recorder/helper hash and numerical environment, and its source archive hash is recorded. Current versus original source must still match exactly on this host. A full clone containing those historical commits is needed; the test does not fetch or mutate a checkout.

All 23 H1 cases matched every compared field exactly against the original source on this host. Comparing today's replay with the historical Linux RMS values exposed up to about 0.84% difference in a saturated reaction-mass case, while many cases differ only around floating-point rounding. That difference is portability sensitivity, not an engineering improvement. The P1 comparison similarly replays the original source rather than creating a new golden result from modified code.

## Firmware verification and the board revision gap

The host C suite passes **60 cases and 1,120 checks** with address and undefined-behaviour sanitizers. Its report records the actual compiler and architecture. Floating-point contraction is disabled explicitly so a fused multiply-add cannot silently change the sequential float32 operations assumed by the golden-vector test. A previously unused bridge count is now checked against every plant step; the Makefile depends on its own flags so changes trigger recompilation.

This host build is **not** a firmware port or timing measurement for the proposed pen. The available checkout's bare-metal port targets nRF5340 and DRV8212P-era electronics, with an older unbalanced actuator model. Rev K's design text describes nRF54L15, DRV8214 and the balanced nib. Those parts, pin maps, sensing routes, plant constants and lifter interfaces are not interchangeable.

| Interface | Current evidence | Required integration work |
|---|---|---|
| Processor and schedule | Host C functional checks; nRF5340 source port | Select the actual board, compile its port, measure worst-case execution and interrupt timing |
| Bridge and current sensing | Older bridge truth table/current-loop implementation | Verify selected part and decay modes, shunt path, ADC aperture, current calibration and saturation |
| Nib force map | Rev K calculations and new vector-map screens | Measure both directions and cross-coupling over position, temperature and tolerance |
| Position feedback | Existing Hall model plus new causal estimator | Measure noise spectrum, delay, magnetic interference and usable resolution on the chosen assembly |
| Contact and lift | Counterface design calculations; software timing guards | Demonstrate actual ink cutoff, full clearance and lift/lower timing under writing load |
| Page reference | Assumed optical model and new loss-of-anchor behaviour | Implement measured anchoring/relocalisation; carry timestamp, validity and frame epoch through firmware |
| Accepted writing | Python reference generator, constraints and supervisor | Port the command/acceptance lifecycle and measured tracking checks; retain independent local limits |
| Temperature and power | Lumped simulation; earlier budgets | Measure coil, lead, bridge, cell and skin temperatures and total input energy over duty cycle |

The ARM compiler, QEMU target and circuit CAD/simulation tools were unavailable in this environment. No target binary, cycle-time measurement, routed Rev K board, SPICE validation or physical bench result is claimed. The successful host report is kept separate from these open items.

## Reproduction and interpretation

The local Python environment uses Python 3.12.14 on macOS arm64 with the repository's pinned scientific dependencies and the added schema validator. The final default suite passes 871 tests with 20 skips; the four optional slow tests pass separately. This gives 875 distinct passing Python checks and 16 unavailable-artifact checks. The complete logs are `results/improvement/verification/full_suite_delivery.txt` and `slow_suite_delivery.txt`. Artifact-dependent skips are part of that result, not successful reproductions. `validation/check_criteria.py --check` currently finds 609 criteria and 182 named experiments with no requirement lacking a criterion. This checks document coverage; it does not mean 182 experiments have been run.

Use one numerical thread per process when reproducing the recorded studies. The master report and delivery manifest list the exact commands, source hashes and new result paths. Earlier results remain available for comparison, but a study depending on the old page model, ideal velocity feedback, old reward or old trajectory planner must be rerun before it is used as evidence for the modified system.
