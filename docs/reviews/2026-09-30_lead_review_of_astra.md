# Lead review of the independent engineering pass (commit e09a15f)

30 September 2026. The pass is described in [its report](Stabilisation_Pen_Engineering_Improvement_Report.md) and [handoff](2026-09-30_astra_handoff.md). This note records what the lead checked, the one defect found, and the decisions taken.

## Verification on a second platform

The full default suite was rerun on Linux x86_64 (Python 3.11.15, numpy 2.4.6, scipy 1.17.1, torch 2.14.0+cpu), with one numerical thread per process. The pass itself was verified on macOS arm64 with Python 3.12.14.

| | The pass (macOS) | This rerun (Linux) |
|---|---|---|
| Tests collected | 891 (871 passed, 20 skipped) | 891 |
| Passed | 871, and 4 slow tests separately | 886 |
| Failed | 0 | 1, fixed below |
| Skipped | 20 (16 need licensed data, models or build artefacts; 4 slow) | 4 (the slow tests) |

The licensed handwriting data and the model caches are installed on this machine. So all 16 checks the pass had to skip ran here: 15 passed and 1 failed.

**The failure was a real defect in the pass, unreachable without the licensed data.** `realdata/library.py` gained a check that an explicitly chosen writer belongs to the requested split. That is a good check. But a note's own writer id, `RealWritten.real["writer"]`, carries the source prefix (`unipen/hpp/hpp2/hpb2-an.dat`), while the split lists bare ids (`hpp/hpp2/hpb2-an.dat`).

Study F's per-writer calibration (`readable/e11.py`, also revised in the pass) passes the note's own id back, so every calibration note was refused. The fix strips the source prefix before the check, so the check still refuses writers from other splits. A data-free regression test covers both behaviours (`realdata/tests/test_library_integrity.py`). With the fix, the affected tests pass: 23 of 23 in `realdata/tests/test_library_integrity.py` and `readable/tests`.

**A portability note.** The pass's reproduction recipe sets `PYTHONNOUSERSITE=1`. On machines whose scientific packages live in the user site, as here, that hides them: collection then fails with `ModuleNotFoundError`. Leave it unset on such machines.

## Decisions

The lead's decisions on the pass are DEC-070 to DEC-074 in [the decision log](../decisions.md):
- **DEC-070:** causal sensing is the default. Earlier closed-loop results computed with ideal sensing are suspended as device evidence until rerun.
- **DEC-071:** the fine nib does local corrections. Whole words need a grounded stage or a moving page.
- **DEC-072:** two nib candidates go forward to the bench.
- **DEC-073:** no learned policy drives the nib.
- **DEC-074:** a correction is proposed, then explicitly accepted by the writer.

The [claims register](../claims_register.md) marks the affected rows. The explainer (version 12) labels its whole-pen simulation rows as upper bounds.

## Round 5: developing the pass further

Five studies run in parallel. Each writes only to its own folders, and the lead integrates the results.

| Study | Question | Outputs |
|---|---|---|
| X: re-baseline | Which headline results survive realistic sensing, the corrected loads and page model v2? Reruns of sim2j's cards (causal and legacy on the same code), the balanced nib in sim2 (Rev K and the 1.5 mm candidate), study F's reach check with the nib's servo, and the page-sensor rows of R, E and F | `rebaseline/`, `results/rebaseline/`, `docs/rebaseline.md` |
| N: nib optimisation | Rev K against the pass's candidates under matched loads and duties. Then a multi-objective search over reach, body diameter, magnets, winding, wires, anchor, guide type and moving mass. Can ±1.5 mm fit the heat limit at realistic load, and what would ±2 mm need? | `nibopt/`, `results/nibopt/`, `docs/nib_optimisation.md`, `mechanics/cad/nibopt.py` |
| P: active writing surface | A moving-paper platen for severe tremor (reach) and for writing accepted words without pushing the hand. Simulated on real recorded tremor and the pass's accepted references | `platen/`, `results/platen/`, `docs/platen_concept.md` |
| U: users and market | Sourced market sizing, competitors, customer-discovery pack with go/no-go numbers, the pen, typing and dictation comparison study, business-model order | `docs/market_and_users.md`, `results/market/` |
| H: first bench build | Order-ready build list per gate: parts, prices, fabrication, assembly, safety, test-to-decision map, budget and schedule | `docs/bench_build_plan.md`, `results/benchbuild/` |

## Lead checks on the round-5 results

- **Study N.** Study K's 17 mW and the pass's 0.081 W for similar nibs were reconciled line by line (`docs/nib_optimisation.md` §2). The difference is mostly convention and duty: which force constant is used, and a typical duty against a worst-case screen. The physics adds only 17 → 20 mW. The claims register now states every nib figure under one convention (DEC-080).
- **Study P, friction integration.** The pass found that its new accepted-writing replay could create energy: an explicit 0.5 ms update of smoothed friction on a 3.44 g mass. Study P's plant is not that code. It uses HW1's LuGre law with the exact exponential bristle step at HW1's 25 µs, and with the page held still it reproduces HW1's ordinary pen to 1e-17 m (`platen/tests`). So this check does not suspend its results. They remain simulation on the tuning split.
- **Study P, a shared cache.** Study P refitted the git-ignored `realdata/build/cache/page_model.json` to page model v2, the current code's default. The lead kept v2; the v1 values remain in `results/realdata/realdata.json`. Anyone rerunning study R's page-sensor rows should expect v2 values (study X reports the difference).
- **Test fixes.** Study P's evidence-row test refused rows that the lead had already merged into the ledger. Its check now matches studies K and F: a new id, or a row merged verbatim.

## Study X and the six code fixes (DEC-075…079)

**Checks on study X.** The lead read the headline numbers back from `results/rebaseline/sim2j_cards.json`:
- the causal headline card: 0.612 of the ordinary pen's ink error (cases 0.585–0.644, writers 0.596–0.627);
- words 7.5 → 10 of 10, and tremor-free writing moved 0 µm;
- perfect knowledge 0.169, and 1.54 W;
- autowrite at 3 mm: 6.8 of 10 words;
- the 1 mm and 2 mm cell means (0.43 → 0.28 mm and 0.94 → 0.53 mm).

All match the study's text. Every rerun first reproduced the historical result. This takes the historical firmware contact channel, which the pass had replaced without a switch: sim2j to 0.4 µm, study B exactly. So each change can be attributed to the correction and not to a drift in the code. DEC-075…079 are accepted. DEC-077 is accepted for the correction benefit and the mechanism limit only: its SIM power figures carry no gravity load, so the nib's power, heat and battery claims stay with DEC-080's matched CALC model.

**The six fixes (DEC-076)** were applied by a separate lead pass to the owning packages. Study X's runtime workarounds stay in place, and a new test file, `rebaseline/tests/test_patch_agreement.py`, checks each workaround against the patched code.

1. **The historical contact channel.** `sim2/params.py` Sensors and `sim2j/sensing.py` gain `firmware_contact = "delayed" | "legacy_immediate"` (default "delayed"). With the legacy flags plus `legacy_immediate`, writer 0, seed 200, 8 Hz × 1 mm reproduces study X's historical row bit for bit: ordinary pen 440.606 µm, G4 377.055 µm. The legacy flags alone give 316.56 µm.
2. **The sim2j writer-setup cache key** now includes the velocity source, the contact source, the inner loop and the contact channel. Existing setup caches are orphaned and re-learned on the next run, at about 55 s per writer.
3. **`bnib/sim.py` and `wholepen/stepper.py`** now pass the firmware's delayed contact to the servo's gate, as sim2j does. No pinned value moved: B1 has no bias current.
4. **The version-2 page-model fit** is saved as `page_model_v2.json` beside the version-1 file. On this machine the version-1 cache, overwritten earlier by study P's run, was restored from study X's record: c 20.48 µm, σ 1.354, 31,757 windows. It agrees with `results/realdata/realdata.json`. This supersedes the lead's earlier "keep v2" note above: both versions are now kept.
5. **Case caches** (studies R, E and F) record the page-model version, and aggregation refuses a mix. Existing caches read as version 1.
6. **`degrade_page` version 2** anchors at the first valid report instead of raising. Records that start valid are unchanged bit for bit. Every recorded note starts with the pen lifted, so without this fix studies R, E and F could not run on current code.

Tests: the full default suite passed <!--SUITE--> on Linux after the fixes; before them it passed 942, with 5 skipped.
