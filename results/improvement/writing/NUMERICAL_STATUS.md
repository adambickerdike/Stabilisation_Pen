# Numerical evidence status

The root-level generic-plant friction studies `accepted_robustness.json`, `robust_observer_development.json`, `robust_observer_holdout.json`, and their earlier assessment are invalid for performance claims. Their 0.5 ms explicit tanh-friction update can create energy. Unmodified bytes and source snapshots are retained in `legacy_unstable_friction/`; root JSON copies now carry a warning and pointer. Original root CSVs/PNGs are legacy diagnostics. The no-drag nominal study is also superseded by the consistent coupled electromechanical update.

Use `numerical_correction_50us/` for current generic-plant results, `numerical_correction_25us/` for the matched timestep check, and `numerical_convergence.json` for their comparison. The same spent protocols, controller gains, seeds and sensor/control schedules were retained. This correction is not a fresh blind test.

Reference-only certificates (`reachable_replay.json`), the ideal kinematic coarse/fine allocation, and grounded-mechanism exports do not use this old integrator. The separate five-bar plant uses its own equations and independent timestep checks; its results are in `../mechanics/`.
