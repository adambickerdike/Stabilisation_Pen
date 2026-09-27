#!/usr/bin/env bash
# Re-run the complete simulation evidence chain on frozen code (model M1).
# Order matters: tests -> diagnosis -> estimator tuning (tuning seeds) ->
# nominal benchmark and sweeps (test seeds, frozen estimator parameters).
# Do not edit sim/, stabpen/ or config/ while this runs.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pytest sim/tests -q
python3 sim/diag_ff_chatter.py
python3 sim/tune_estimators.py > results/sim/tune_estimators.log 2>&1
python3 sim/diag_ff_options.py > results/sim/diag_ff_options.log 2>&1
python3 sim/run_nominal.py > results/sim/run_nominal.log 2>&1
python3 sim/run_sweeps.py > results/sim/run_sweeps.log 2>&1
python3 sim/mc_sensitivity.py > results/sim/mc_sensitivity.log 2>&1
python3 sim/sweep_design.py > results/sim/sweep_design.log 2>&1
python3 sim/diag_kappa.py > results/sim/diag_kappa.log 2>&1
python3 sim/guided_eval.py > results/sim/guided_eval.log 2>&1
python3 sim/diag_gate.py > results/sim/diag_gate.log 2>&1
echo "run_all complete"
