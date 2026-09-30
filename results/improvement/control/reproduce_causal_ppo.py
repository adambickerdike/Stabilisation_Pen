"""Reproduce the frozen 196,608-transition causal PPO screen in a source bundle.

No current checkout or original results are modified. ``prepare`` verifies the
82 declared source files, ``smoke`` reruns one existing matched pair, ``evaluate``
reuses the saved checkpoints but recalculates all tuning cases, and ``train``
starts again. The frozen script's original 4 kHz prose typo remains untouched;
protocol_clarification_record_rate.json records the executed 2 kHz trace rate.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = HERE / "causal_ppo"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT / "sim2j/build/frozen_causal_ppo_reproduction")
    parser.add_argument("--mode", choices=["prepare", "smoke", "evaluate", "train"], default="prepare")
    args = parser.parse_args()
    protocol = json.loads((ORIGINAL / "protocol.json").read_text())
    target = args.destination.resolve()
    base = protocol["head"]
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current != base:
        raise RuntimeError("Use the recorded base checkout so the frozen runner's Git metadata remains accurate")
    marker = target / "frozen_source_manifest.json"
    for rel, expected in protocol["source_sha256"].items():
        if digest(ORIGINAL / "source_snapshot" / rel) != expected:
            raise RuntimeError(f"Archived source changed: {rel}")
    if not target.exists():
        target.mkdir(parents=True)
        archive = subprocess.check_output(["git", "archive", base], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as package:
            package.extractall(target, filter="data")
        for rel in protocol["source_sha256"]:
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ORIGINAL / "source_snapshot" / rel, dest)
        marker.write_text(json.dumps({"base": base, "source_sha256": protocol["source_sha256"]}, indent=2) + "\n")
    elif not marker.exists():
        raise RuntimeError("Existing destination is not this script's source bundle; refusing overwrite")
    manifest = json.loads(marker.read_text())
    if manifest != {"base": base, "source_sha256": protocol["source_sha256"]}:
        raise RuntimeError("Source-bundle manifest differs from the executed experiment")
    for rel, expected in protocol["source_sha256"].items():
        if digest(target / rel) != expected:
            raise RuntimeError(f"Prepared source differs: {rel}")
    print(f"Verified {len(protocol['source_sha256'])} executed sources at {target}", flush=True)
    if args.mode == "prepare":
        return
    git_dir = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=ROOT, text=True).strip()
    env = dict(os.environ, PYTHONNOUSERSITE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMBA_NUM_THREADS="1", GIT_DIR=git_dir, GIT_WORK_TREE=str(target),
               MPLCONFIGDIR=str(target / "sim2j/build/mpl"))
    if args.mode == "smoke":
        code = '''
import json, pathlib, sys
from sim2j.causal_ppo_study import evaluate_job
original = pathlib.Path(sys.argv[1])
data = json.loads((original / 'tuning_seed_1.json').read_text())
policy_expected = next(r for r in data['rows'] if r['class'] == 'large')
case = {k: policy_expected[k] for k in ('writer', 'seed', 'f0', 'amp', 'class')}
key = f"{case['writer']}_{case['seed']}_{case['class']}"
base_expected = json.loads((original / 'cases/zero' / (key+'.json')).read_text())
reports = []
for name, checkpoint, expected in [('smoke_zero', None, base_expected),
        ('smoke_seed_1', str(original / 'checkpoints/seed_1.zip'), policy_expected)]:
    row = evaluate_job((case, name, checkpoint))
    delta = {k: abs(row[k]-expected[k]) for k in ['rms_um', 'cost', 'missing_fraction',
             'extra_fraction', 'coil_power_W', 'coil_temperature_C']}
    assert row['reference_sha256'] == expected['reference_sha256']
    assert max(delta.values()) <= 1e-8, delta
    reports.append({'policy': name, 'absolute_difference': delta})
pathlib.Path('frozen_causal_smoke_result.json').write_text(json.dumps(reports,indent=2)+'\\n')
print(json.dumps(reports,indent=2))
'''
        subprocess.run([sys.executable, "-c", code, str(ORIGINAL)], cwd=target, env=env, check=True)
    else:
        output = target / "results/improvement/control/causal_ppo"
        # Evaluation copies only frozen training artifacts, never case metrics or
        # traces, so the comparison is physically recalculated.
        if args.mode == "evaluate":
            (output / "checkpoints").mkdir(parents=True, exist_ok=True)
            shutil.copy2(ORIGINAL / "protocol.json", output / "protocol.json")
            for seed in protocol["seeds"]:
                shutil.copy2(ORIGINAL / f"checkpoints/seed_{seed}.zip", output / f"checkpoints/seed_{seed}.zip")
                shutil.copy2(ORIGINAL / f"training_seed_{seed}.json", output / f"training_seed_{seed}.json")
        subprocess.run([sys.executable, "-m", "sim2j.causal_ppo_study"], cwd=target, env=env, check=True)


if __name__ == "__main__":
    main()
