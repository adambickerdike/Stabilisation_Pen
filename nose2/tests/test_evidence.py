"""Proposed ledger rows: the exact header of docs/evidence.csv, ids in the study's ranges, no duplicates."""
from __future__ import annotations

import csv
import re

from nose2 import REPO_ROOT
from nose2 import evidence as EV

RANGES = {"AMF": (135, 154), "ACT": (100, 104), "OPT": (50, 54), "PAT": (40, 44)}


def test_header_and_ids():
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="") as f:
        header = next(csv.reader(f))
    assert EV.HEADER == header and len(header) == 23
    rows = EV.rows({})
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    for i in ids:
        m = re.fullmatch(r"([A-Z]+)-(\d+)", i)
        lo, hi = RANGES[m.group(1)]
        assert lo <= int(m.group(2)) <= hi, i
    for r in rows:
        assert set(r) == set(header)
        assert r["doi_or_url"] and r["access_level"]
