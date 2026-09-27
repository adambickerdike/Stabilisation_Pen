#!/usr/bin/env bash
# Reproduce every aiguide result (results/ai/).  Evidence status: SIMULATION / CALCULATION on synthetic data
# and public-domain text.  At most two processes (run_guidance uses two workers).  About 13 min here.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m aiguide.run_text
python3 -m aiguide.run_style
python3 -m aiguide.run_stroke
python3 -m aiguide.run_autocorrect
python3 -m aiguide.run_guidance --workers 2
python3 -m aiguide.run_deploy
python3 -m pytest -q -p no:cacheprovider aiguide/tests app/tests/test_autocorrect.py
