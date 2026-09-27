"""Shared fixtures.  All data are synthetic and generated into pytest tmp dirs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
for p in (str(APP), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from penapp import logfmt  # noqa: E402
from penapp._util import FixedClock  # noqa: E402

LINES_A = ["buy milk eggs and bread", "return library books by friday", "call the plumber at 9 am"]
LINES_B = ["pen rev a bench test on monday", "check hall sensor offset", "order spare refills"]
TRACE = ROOT / "results" / "sim" / "nominal" / "traces_kf_asr.npz"


@pytest.fixture(scope="session")
def session_a():
    from penapp.synth import synth_text_session
    return synth_text_session(LINES_A, seed=11, session_id=1)


@pytest.fixture(scope="session")
def session_b():
    from penapp.synth import synth_text_session
    return synth_text_session(LINES_B, seed=12, session_id=2, start_unix_ms=1788339600000)


@pytest.fixture(scope="session")
def files(tmp_path_factory, session_a, session_b):
    d = tmp_path_factory.mktemp("samples")
    out = {}
    for name, ses in (("a", session_a), ("b", session_b)):
        ses.write(d / f"{name}.penlog", truth_path=d / f"{name}.truth.json", meta_path=d / f"{name}.meta.json")
        out[name] = d / f"{name}.penlog"
        out[name + "_truth"] = d / f"{name}.truth.json"
    return out


@pytest.fixture
def store(tmp_path):
    from penapp.notes import NoteStore
    return NoteStore(tmp_path / "store", clock=FixedClock("2026-09-01T09:00:00.000Z"))


@pytest.fixture(scope="session")
def loaded_template(tmp_path_factory, files):
    """Store with both text sessions imported (segmentation, ground-truth recognition, index), built once."""
    from penapp.cli import import_log_file
    from penapp.notes import NoteStore
    root = tmp_path_factory.mktemp("template") / "store"
    st = NoteStore(root, clock=FixedClock("2026-09-01T09:00:00.000Z"))
    ids = {k: import_log_file(st, files[k])["note_id"] for k in ("a", "b")}
    return root, ids


@pytest.fixture
def loaded(tmp_path, loaded_template):
    """Private copy of the template store; its clock starts after the template's time stamps."""
    import shutil
    from penapp.notes import NoteStore
    root, ids = loaded_template
    dst = tmp_path / "store"
    shutil.copytree(root, dst)
    return NoteStore(dst, clock=FixedClock("2026-09-02T09:00:00.000Z")), dict(ids)


def parse(data: bytes, **kw):
    return logfmt.read_log(data, **kw)
