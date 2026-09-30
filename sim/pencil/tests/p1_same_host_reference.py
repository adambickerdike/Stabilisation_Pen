"""Replay the frozen pre-touchdown simulator, preserving the historical Linux fixture.

The old source, not current source, creates this host-specific reference. Cache
identity includes its Git commit, exact recorder and numerical environment.
Full Git history is required; no network fetch or checkout mutation occurs.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tarfile


def reference():
    import llvmlite
    import numba
    import numpy as np
    import scipy

    root = Path(__file__).resolve().parents[3]
    fixture = Path(__file__).parent / "data/p1_default_baseline"
    historical = json.loads(fixture.with_suffix(".json").read_text())
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", historical["git_revision"] + "^{commit}"],
        cwd=root, text=True).strip()
    recorder = (Path(__file__).parent / "data/record_p1_default_baseline.py").read_bytes()
    signature = dict(revision=revision, recorder_sha256=hashlib.sha256(recorder).hexdigest(),
                     driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     python=sys.version, executable=sys.executable, platform=platform.platform(),
                     numpy=np.__version__, scipy=scipy.__version__, numba=numba.__version__,
                     llvmlite=llvmlite.__version__)
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    cache = root / "build/p1_reference" / digest
    result = cache / "reference"
    if result.with_suffix(".json").exists() and result.with_suffix(".npz").exists():
        return json.loads(result.with_suffix(".json").read_text()), np.load(result.with_suffix(".npz"))
    source = cache / "source"
    source.mkdir(parents=True, exist_ok=True)
    paths = ["sim/pencil", "sim/pensim", "sim/handpen", "stabpen", "config",
             "results/cad/pencil_revPQ_summary.json", "results/cad/pencil_revPL_summary.json",
             "results/sim/estimator_selection.json"]
    archive = subprocess.check_output(["git", "archive", revision, *paths], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            target = source / member.name
            if not target.resolve().is_relative_to(source.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError("Unexpected archive member: " + member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
    script = source / "sim/pencil/tests/data/record_p1_default_baseline.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    # Import by path after explicitly installing the frozen source root. main()
    # only asks git for metadata; it never mutates the repository or fixtures.
    script.write_bytes(recorder)
    code = ("import sys,runpy; sys.path.insert(0," + repr(str(source)) + "); "
            "runpy.run_path(" + repr(str(script)) + ")[\"main\"](" + repr(str(result)) + ")")
    env = dict(os.environ)
    for name in ("NUMBA_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env[name] = "1"
    env["NUMBA_CACHE_DIR"] = str(cache / "numba_cache")
    env.pop("PYTHONPATH", None)
    done = subprocess.run([sys.executable, "-c", code], cwd=source, env=env,
                          capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise RuntimeError("Frozen P1 replay failed:\n" + done.stderr[-4000:])
    meta = json.loads(result.with_suffix(".json").read_text())
    # Recorder's git query walks to the active repository; explicitly replace
    # that descriptive field with the source revision we actually exported.
    meta["git_revision"] = revision
    meta["source_signature"] = signature
    meta["archive_sha256"] = hashlib.sha256(archive).hexdigest()
    result.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta, np.load(result.with_suffix(".npz"))
