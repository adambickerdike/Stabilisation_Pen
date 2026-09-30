"""The extension of sim/handpen by opt/inertial (grip sleeve, actuated pivot, in-loop controller hook) must leave every
default output unchanged, bit for bit within one numerical runtime. The original source revision is replayed
on this host; historical Linux hashes remain unchanged. Evidence status: code verification only."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from opt.inertial.tests import h1_regression_cases as C  # noqa: E402


@pytest.fixture(scope="module")
def now():
    return C.compute()


@pytest.fixture(scope="module")
def original():
    from opt.inertial.tests.h1_same_host_reference import reference
    return reference()


def test_baseline_was_recorded_on_unmodified_tree():
    d = json.load(open(C.BASELINE))
    assert d["sim_handpen_modified_at_recording"] is False
    assert len(d["cases"]) >= 20


@pytest.mark.parametrize("name", list(json.load(open(C.BASELINE))["cases"]))
def test_default_outputs_bit_for_bit(now, original, name):
    base = original[name]
    got = now[name]
    for key in ("rec_sha256", "u_sha256", "frf_sha256", "shape", "hist"):
        if key in base:
            assert got[key] == base[key], f"{name}: {key} changed"
    if "appended_all_zero" in got:
        assert got["appended_all_zero"], f"{name}: an appended (extension) channel is non-zero in a default run"
