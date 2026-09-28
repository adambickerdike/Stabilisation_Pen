"""Checks of the proposed ledger rows and of the published study files (when they exist)."""
from __future__ import annotations

import json

import pytest

from handwriting import RESULTS_DIR
from handwriting import evidence as EV

REQUIRED = {"et_tremor": ["none", "pencil_akf", "revH_oracle"], "pd_micrographia": ["pen_none", "cue", "size_assist_1.35"],
            "guided_practice": ["none", "nose_full", "board_full"]}


def test_evidence_rows_header_and_ids():
    assert EV.HEADER == EV.ledger_header()
    rows = EV.LITERATURE + EV.sim_rows({})
    EV.check_ids(rows)
    for r in rows:
        assert set(r) == set(EV.HEADER)
        assert r["citation"] and r["doi_or_url"] and r["key_quantitative_findings"] is not None


def test_written_evidence_csv_matches_header():
    p = RESULTS_DIR / "evidence_rows.csv"
    if not p.exists():
        pytest.skip("run python3 -m handwriting.run_study first")
    import csv
    with open(p, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        assert next(rd) == EV.HEADER
        assert all(len(row) == len(EV.HEADER) for row in rd)


def test_samples_schema_and_size():
    p = RESULTS_DIR / "samples.json"
    if not p.exists():
        pytest.skip("run python3 -m handwriting.run_study first")
    assert p.stat().st_size <= 2_000_000
    d = json.loads(p.read_text())
    assert "meta" in d and d["panels"]
    for pan in d["panels"]:
        for k in ("id", "title", "condition", "device", "caption", "evidence", "intended", "ink", "metrics"):
            assert k in pan, (pan.get("id"), k)
        assert pan["condition"] in ("et_tremor", "pd_micrographia", "guided_practice", "spelling")
        for key in ("intended", "ink"):
            pts = pan[key]
            assert 0 < len(pts) <= 3000
            assert all(len(q) == 3 and q[2] in (0, 1) for q in pts[:50])
    have = {}
    for pan in d["panels"]:
        have.setdefault(pan["condition"], set()).add(pan["device"])
    for cond, devs in REQUIRED.items():
        if cond in have:
            assert set(devs) <= have[cond], (cond, have[cond])
