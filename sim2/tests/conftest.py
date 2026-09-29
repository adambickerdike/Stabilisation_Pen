"""pytest configuration for sim2: fast tests by default; `--runslow` also runs the tests marked slow."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False, help="run the slow sim2 tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: slow sim2 test (MyoSuite, H1 comparison, study stages)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip = pytest.mark.skip(reason="slow: use --runslow")
    for it in items:
        if "slow" in it.keywords:
            it.add_marker(skip)
