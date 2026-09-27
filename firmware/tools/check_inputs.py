#!/usr/bin/env python3
"""Check that the generated parameters and golden vectors were produced from
the CURRENT sources of truth (config/parameters.yaml, estimator selection,
drive_sense.json, sim/pensim/model.py and core.py).

Other teams edit those files; a stale params_gen.h or stale vectors would make
the firmware or its tests silently disagree with the simulator. Exit status 1
if anything is stale; `make params vectors` regenerates.
Run: python3 firmware/tools/check_inputs.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)
ROOT = os.path.dirname(FW)
SRC = {
    "yaml_sha16": os.path.join(ROOT, "config", "parameters.yaml"),
    "estimator_selection_sha16": os.path.join(ROOT, "results", "sim", "estimator_selection.json"),
    "drive_sense_sha16": os.path.join(ROOT, "results", "electronics", "drive_sense.json"),
    "model_py_sha16": os.path.join(ROOT, "sim", "pensim", "model.py"),
    "core_py_sha16": os.path.join(ROOT, "sim", "pensim", "core.py"),
    "design_revA_sha16": os.path.join(ROOT, "electronics", "gen", "design_revA.py"),
    "icd_sha16": os.path.join(ROOT, "docs", "icd.md"),
}


def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def main():
    cur = {k: sha16(v) for k, v in SRC.items()}
    stale = []
    pj = os.path.join(FW, "include", "params_gen.json")
    meta = json.load(open(pj))["meta"]
    for k, v in cur.items():
        if k in meta and meta[k] != v:
            stale.append(f"include/params_gen.h: {k} {meta[k]} != current {v} ({os.path.relpath(SRC[k], ROOT)})")
    for side in sorted(glob.glob(os.path.join(FW, "tests", "vectors", "*.vec.json"))):
        m = json.load(open(side))
        for k in ("yaml_sha16", "estimator_selection_sha16", "core_py_sha16", "model_py_sha16"):
            if k in m and m[k] != cur[k]:
                stale.append(f"tests/vectors/{os.path.basename(side)}: {k} {m[k]} != current {cur[k]}")
    print(f"input check: yaml {meta.get('yaml_version')} [{cur['yaml_sha16']}], estimator_selection [{cur['estimator_selection_sha16']}], "
          f"model.py [{cur['model_py_sha16']}], core.py [{cur['core_py_sha16']}]")
    if stale:
        print("STALE generated files (run: make -C firmware params vectors):")
        for s in stale:
            print("  " + s)
        return 1
    print("params_gen.h and all golden vectors match the current sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
