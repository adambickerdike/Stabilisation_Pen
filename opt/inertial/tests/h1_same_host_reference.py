"""Run the frozen, unmodified H1 source on the current numerical runtime.

An exact output hash is a valid regression check only within a matching numerical
environment. Never overwrite the historical Linux hashes with today's output.
Instead replay the source revision recorded by that historical baseline, using
the identical case definitions, interpreter and libraries as the current code.
No network access or Git working-tree mutation is used.
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

from . import h1_regression_cases as C


def reference():
    import llvmlite
    import numba
    import numpy
    import scipy

    root = Path(C.ROOT)
    historic = json.loads(Path(C.BASELINE).read_text())
    revision = subprocess.check_output(['git', 'rev-parse', '--verify',
                                         historic['git_revision']+'^{commit}'], cwd=root, text=True).strip()
    helper = Path(C.__file__).read_bytes()
    signature = dict(revision=revision, helper_sha256=hashlib.sha256(helper).hexdigest(),
                     python=sys.version, executable=sys.executable, platform=platform.platform(),
                     numpy=numpy.__version__, scipy=scipy.__version__, numba=numba.__version__,
                     llvmlite=llvmlite.__version__)
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    cache = root/'build'/'h1_reference'/digest
    result = cache/'reference.json'
    if result.exists():
        return json.loads(result.read_text())['cases']
    cache.mkdir(parents=True, exist_ok=True)
    source = cache/'source'
    source.mkdir(exist_ok=True)
    paths = ['sim/handpen', 'sim/pensim', 'sim/pencil', 'stabpen', 'config',
             'results/cad/pencil_revPQ_summary.json']
    archive = subprocess.check_output(['git', 'archive', revision, *paths], cwd=root)
    # Explicit path check also supports Python 3.11, whose tar filter support
    # varies by patch release. Only regular files/directories from our Git tree.
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            target = source/member.name
            if not target.resolve().is_relative_to(source.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError('Unexpected archive member: '+member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
    cases = source/'opt/inertial/tests/h1_regression_cases.py'
    cases.parent.mkdir(parents=True, exist_ok=True)
    cases.write_bytes(helper)
    raw = cache/'computed.json'
    script = ('import json; from opt.inertial.tests.h1_regression_cases import compute; '
              'json.dump(compute(),open('+repr(str(raw))+',"w"),sort_keys=True)')
    env = dict(os.environ)
    for key in ('NUMBA_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS'):
        env[key] = '1'
    env['NUMBA_CACHE_DIR'] = str(cache/'numba_cache')
    env.pop('PYTHONPATH', None)
    completed = subprocess.run([sys.executable, '-c', script], cwd=source, env=env,
                               capture_output=True, text=True, timeout=600)
    if completed.returncode:
        raise RuntimeError('Frozen H1 replay failed:\n'+completed.stderr[-4000:])
    data = {'signature': signature, 'archive_sha256': hashlib.sha256(archive).hexdigest(),
            'cases': json.loads(raw.read_text())}
    result.write_text(json.dumps(data, indent=2)+'\n')
    return data['cases']
