"""Run metadata so every result identifies code revision, configuration, seeds and command."""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import subprocess
import sys

from . import params as _params


def git_revision(repo=_params.REPO_ROOT) -> str:
    try:
        rev = subprocess.check_output(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.call(["git", "-C", repo, "diff", "--quiet", "HEAD"],
                                stderr=subprocess.DEVNULL) != 0
        return rev + ("-dirty" if dirty else "")
    except Exception:
        return "no-commit"


def metadata(evidence_status: str, seeds=None, extra=None, p=None) -> dict:
    p = p or _params.load()
    md = {
        "evidence_status": evidence_status,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "git_revision": git_revision(),
        "parameters_version": p.version(),
        "parameters_sha256_16": p.digest(),
        "command": " ".join([os.path.basename(sys.argv[0])] + sys.argv[1:]),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seeds": seeds,
    }
    try:
        import numpy, scipy
        md["numpy"] = numpy.__version__
        md["scipy"] = scipy.__version__
    except Exception:
        pass
    if extra:
        md.update(extra)
    return md


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_default)


def _default(o):
    try:
        import numpy as np
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except Exception:
        pass
    return str(o)
