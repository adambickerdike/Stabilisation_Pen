#!/usr/bin/env bash
# Reproduce the ML pipeline end to end (SIMULATION / synthetic data only).
# Writes only to ml/ (ml/runs is git-ignored), data/ and results/ml/.
# CPU only; torch uses 2 threads; total about 35 min on a 4-core machine
# (training about 12 min of it).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1        # never write byte-code into stabpen/ or sim/
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p ml/runs/logs

# 1. datasets, leakage checks, schema examples (~3 min; runs the simulator for the realism set)
python3 -m ml.datasets --workers 2                               | tee ml/runs/logs/datasets.log
# 2. conventional baselines tuned on validation writers (~7 min + 2 short grid extensions)
python3 -m ml.tune_baselines                                     | tee ml/runs/logs/tune_baselines.log
python3 -m ml.tune_baselines --extend kf bmflc bpf               | tee ml/runs/logs/tune_extend.log
# 3. networks (evaluated in section c: tcn_s; exported: tcn_s_nofest, contract v1.1 without f_est; also tcn_m)
python3 -m ml.train --model tcn_s --epochs 14 --max-minutes 9     | tee ml/runs/logs/train_tcn_s.log
python3 -m ml.train --model tcn_m --epochs 14 --max-minutes 9     | tee ml/runs/logs/train_tcn_m.log
python3 -m ml.train --model tcn_s --no-fest --tag _nofest --epochs 14 --max-minutes 7 | tee ml/runs/logs/train_nofest.log
# 4. int8 post-training quantisation (calibration on training writers, choice on validation):
#    the exported model -> quantization.json; tcn_s (with f_est, evaluated below) -> quantization_tcn_s.json
python3 -m ml.quantize --model tcn_s_nofest                       | tee ml/runs/logs/quantize.log
python3 -m ml.quantize --model tcn_s                              | tee ml/runs/logs/quantize_tcn_s.log
# 5. C export: generated headers, test vectors, host (gcc, clang UBSan) and Cortex-M33 (arm-none-eabi-gcc, QEMU)
#    checks.  tcn_s_nofest (TCN_CIN 2) -> ml/export/ + export_c.json; tcn_s (TCN_CIN 3) is exported out of tree
#    to ml/runs/export_tcn_s/ + export_c_tcn_s.json for comparison
python3 -m ml.export_c --model tcn_s_nofest                       | tee ml/runs/logs/export_c.log
python3 -m ml.export_c --model tcn_s                              | tee ml/runs/logs/export_c_tcn_s.log
# 6. budget (MACs, memory, time, energy)
python3 -m ml.budget --model tcn_s_nofest --alt tcn_s tcn_m       | tee ml/runs/logs/budget.log
# 7. evaluation on the held-out sets, bootstrap CIs, figures
python3 -m ml.evaluate --model tcn_s --alt tcn_m                  | tee ml/runs/logs/evaluate.log
# 8. tests
python3 -m pytest -p no:cacheprovider ml/tests -q
