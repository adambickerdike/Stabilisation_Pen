"""Export base Git source plus the exact executed PPO overlay, without checkout mutation.

Run with the pinned workspace Python. Default only prepares a source bundle.
--mode smoke verifies one matched baseline/policy case against saved numbers.
--mode evaluate reruns all tuning/test cases from the three saved checkpoints.
--mode train repeats the complete 49,152-transition training/evaluation run.

The source bundle contains no .git directory; GIT_DIR is read only by the frozen
runner's rev-parse metadata call. Source hashing and the 400Hz RevJ constructor
are verified before execution. No historical output files are overwritten.
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=ROOT / "sim2j/build/frozen_rl_reproduction")
    parser.add_argument("--mode", choices=["prepare", "smoke", "evaluate", "train"], default="prepare")
    args = parser.parse_args()
    target = args.destination.resolve()
    original = json.loads((HERE / "rl_protocol.json").read_text())
    base = original["head"]
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current != base:
        raise RuntimeError("Use a checkout of the recorded base commit for reproducible Git metadata")
    marker = target / "frozen_source_manifest.json"
    if not target.exists():
        target.mkdir(parents=True)
        archive = subprocess.check_output(["git", "archive", base], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as package:
            package.extractall(target, filter="data")
        overlay = HERE / "legacy_source_snapshot"
        source_hashes = {}
        for source in sorted(overlay.rglob("*.py")):
            relative = source.relative_to(overlay)
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            source_hashes[str(relative)] = digest(source)
        marker.write_text(json.dumps({"base": base, "overlay_sha256": source_hashes}, indent=2) + "\n")
    elif not marker.exists():
        raise RuntimeError("Destination exists and is not this script's source bundle; refusing overwrite")
    manifest = json.loads(marker.read_text())
    if manifest["base"] != base:
        raise RuntimeError("Source bundle base differs")
    for name, expected in manifest["overlay_sha256"].items():
        if digest(target / name) != expected:
            raise RuntimeError(f"Frozen overlay changed: {name}")
    for name, expected in original["hashes"].items():
        if digest(target / name) != expected:
            raise RuntimeError(f"Original protocol source hash differs: {name}")
    print(f"Verified base {base}, {len(manifest['overlay_sha256'])} overlay sources at {target}", flush=True)
    if args.mode == "prepare":
        return
    git_dir = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=ROOT, text=True).strip()
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               NUMBA_NUM_THREADS="1", GIT_DIR=git_dir, GIT_WORK_TREE=str(target),
               MPLCONFIGDIR=str(target / "sim2j/build/mpl"))
    if args.mode == "smoke":
        smoke = '''
import hashlib, json, pathlib
import numpy as np
from stable_baselines3 import PPO
from sim2j.rl_integrity_study import evaluate_case
source = pathlib.Path(__import__('sys').argv[1])
test = json.loads((source/'rl_test.json').read_text())
case = {k: test['baseline'][0][k] for k in ('writer','seed','f0','amp','class')}
model = PPO.load(source/'research_checkpoints/seed_0.zip',device='cpu')
report = []
for key, policy in [('baseline',None),('selected',model)]:
    row = evaluate_case(case,policy)
    expected = test[key][0]
    error = {k: abs(row[k]-expected[k]) for k in ['rms_um','cost','missing_fraction','extra_fraction','coil_power_W','coil_temperature_C']}
    if max(error.values()) > 1e-8:
        raise AssertionError(error)
    report.append({'policy':key,'metrics':row,'absolute_difference':error})
pathlib.Path('frozen_smoke_result.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report,indent=2))
'''
        subprocess.run([sys.executable, "-c", smoke, str(HERE)], cwd=target, env=env, check=True)
    else:
        if args.mode == "evaluate":
            output = target / "results/improvement/control"
            build = target / "sim2j/build/rl_integrity"
            output.mkdir(parents=True, exist_ok=True)
            build.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / "rl_protocol.json", output / "rl_protocol.json")
            for seed in original["seeds"]:
                shutil.copy2(HERE / f"research_checkpoints/seed_{seed}.zip", build / f"seed_{seed}.zip")
                shutil.copy2(HERE / f"training_seed_{seed}.json", output / f"training_seed_{seed}.json")
        subprocess.run([sys.executable, "-m", "sim2j.rl_integrity_study", "--steps",
                        str(original["requested_steps_per_seed"]), "--seeds",
                        *map(str, original["seeds"])], cwd=target, env=env, check=True)


if __name__ == "__main__":
    main()
