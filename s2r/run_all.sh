#!/usr/bin/env bash
# Sim-to-real evidence chain (SIMULATION + CALCULATION; twin experiments, not measurements).
# At most 2 worker processes at any time. Order matters: C1 identification feeds C2.
# Logs: results/s2r/logs/*.log. Total about 45-60 min on a shared 4-core machine.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
LOG=results/s2r/logs
mkdir -p "$LOG"
python3 -m s2r.run_c1_identify            > "$LOG/c1_identify.log" 2>&1
python3 -m s2r.run_c2_twin --part 1       > "$LOG/c2_twin_part1.log" 2>&1
python3 -m s2r.run_c2_twin --part 2       > "$LOG/c2_twin_part2.log" 2>&1
python3 -m s2r.run_c2_twin --merge        > "$LOG/c2_twin_merge.log" 2>&1
python3 -m s2r.run_c2_sensitivity         > "$LOG/c2_sensitivity.log" 2>&1
python3 -m s2r.run_c3_modelform           > "$LOG/c3_modelform.log" 2>&1
python3 -m s2r.run_c3_piezo               > "$LOG/c3_piezo.log" 2>&1
python3 -m s2r.run_c4_domain              > "$LOG/c4_domain.log" 2>&1
python3 -m s2r.run_c1_benchtime           > "$LOG/c1_benchtime.log" 2>&1
python3 -m s2r.run_c5_example             > "$LOG/c5_example.log" 2>&1
echo "s2r chain complete"
