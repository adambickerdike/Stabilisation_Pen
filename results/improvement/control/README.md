# Control improvement evidence, 30 September 2026

These artifacts contain software checks, analytic calculations and synthetic physical simulation. They contain no hardware measurements, patient handwriting, reader study or proof of useful physical autocorrect. The full account is in `docs/control_improvement_audit.md`.

The implemented simulation now estimates velocity causally from timestamped noisy Hall measurements, gates contact from delayed measurements, scores required and unwanted ink separately, and uses an 80 Hz inner-loop design selected before final cases. Replacing the old 400 Hz gains under matched causal sensing removes a substantial instability. Learned residual policies were actually trained twice and rejected by their prewritten rules.

| Study | Data status | Result and principal files |
|---|---|---|
| Initial corrected-reward PPO | Three seeds × 16,384 transitions; separate train/tune/test writer IDs; ideal derivative and true-contact inner loop | Selected policy failed fresh test: large-case ratio 1.004476. `rl_integrity_results.json`, `rl_adoption_decision.json`, `research_checkpoints/`, `legacy_source_snapshot/` |
| Causal Hall sensitivity | Frozen initial PPO on its already spent test set, old 400 Hz gains | Fails clean-writing and ink gates. Post-hoc sensitivity only. `hall_sensitivity_results.json`, `causal400_source_snapshot/` |
| Servo design/calibration | Independent linear uncertainty grid then nine nonlinear engineering cases; gain frozen before nonlinear runs | Selects 80 Hz; old causal 400 Hz locally unstable. Bench still had true-contact gating. `servo_design_frozen.json`, `servo_design_results.json` |
| Aborted final comparison | Eleven paired cases inspected before discovery of remaining contact truth in inner servo | Aborted for model defect; no gain retuning; wholly new IDs used after correction. `aborted_hall_only_final/` |
| Final causal controller comparison | 45 fresh paired cases; five synthetic writers; identical Hall/contact sensing and target | 328→103 um mean clean-path error; 8.223→1.596 W mean copper power; five cases have worse error. `causal_controller_results.json`, `causal_controller_comparison.png`, `final_controller_source_snapshot/` |
| Larger causal PPO | Three seeds × 65,536 transitions; final checkpoints only; separate writers | All fail tuning. Best large-case ratio 0.998077 versus required <=0.98. Planned test split unconsumed. `causal_ppo/results.json`, `causal_ppo/checkpoints/`, `causal_ppo/source_snapshot/` |
| Timestep refinement | Three previously inspected cases, 12.5/25/50 us steps; common fine target | Maximum observed coarse/fine path difference 32.518 um; no universal numerical error bound. `timestep_sensitivity.json` |

The final controller intervals contain 112.5 s total scored writing. Required ink lasts 64.7685 s and required lift 47.7315 s. Missing ink decreases from 18.2005 s to 1.4670 s (**28.10%→2.26% of required ink**). Unwanted ink increases from 0.5530 s to 0.7995 s (**1.16%→1.67% of required lift**). Worst new trajectory error is 2.181 mm and maximum modeled winding temperature is 65.68°C after a short interval. The revised controller is a more defensible simulation baseline, not a production or clinical result. Its gains have not been validated for the proposed balanced nib or grounded five-bar.

Both PPO studies together completed 245,760 transitions across six seeds. They use different plants and protocols and must not be pooled as one efficacy experiment. All failed seeds and checkpoints remain available. No learned policy was deployed into firmware.

## Reproduction

Use the pinned Python environment, set `PYTHONNOUSERSITE=1`, and use one numerical thread per process. The executed runtime is Python 3.12 on macOS arm64; the original repository also has historical Linux/Python 3.11 results. Exact library versions are saved in the protocols.

From the repository root:

```sh
PYTHONNOUSERSITE=1 python results/improvement/control/reproduce_frozen_rl.py --mode smoke
PYTHONNOUSERSITE=1 python results/improvement/control/reproduce_causal_ppo.py --mode smoke
```

These export the recorded Git base plus the appropriate verified source overlay into an ignored build directory. They do not replace the working checkout. Each script also supports `--mode prepare`, `--mode evaluate`, `--mode train`, and `--destination NEW_DIRECTORY`. Use a new destination for a fresh full training or evaluation run. Reusing an already populated destination permits the frozen experiment's documented checkpoint/case cache behavior.

Both smoke replays were actually executed: one matched baseline/policy case from each source bundle reproduced all six saved numeric fields exactly on the same host. This verifies those cases, not a complete independent repetition of training. The later bundle contains all 82 source files declared in its executed protocol. Its original 4 kHz recording-rate prose error is preserved in the snapshot; `causal_ppo/protocol_clarification_record_rate.json` records the actual 2 kHz rate, corrected during training before tuning results.

`summary.json` provides a compact machine-readable handover. `figure_metrics.json` records the denominators used by the figure. Original repository results outside `results/improvement/` remain historical and are not silently rewritten to reflect the new model.
