"""Ledger rows, BOM, proposed experiments and criteria: structure and honesty rules."""
import csv
import os
import re

from rig import ROOT, bom, experiments, ledger


def test_ledger_header_matches_evidence_csv():
    with open(os.path.join(ROOT, "docs", "evidence.csv"), newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == ledger.COLUMNS
    assert len(header) == 23


def test_ledger_ids_in_assigned_ranges_and_unique():
    ok = {**{f"AMF-{i}": 1 for i in range(220, 240)}, **{f"OPT-{i}": 1 for i in range(85, 95)},
          **{f"CON-{i}": 1 for i in range(100, 105)}, **{f"HAP-{i}": 1 for i in range(140, 145)}}
    ids = [r["id"] for r in ledger.ROWS]
    assert len(ids) == len(set(ids))
    assert all(i in ok for i in ids), [i for i in ids if i not in ok]
    for r in ledger.ROWS:
        assert r["citation"] and r["doi_or_url"] and r["locator"] and r["retrieved"], r["id"]


def test_ledger_ids_not_already_in_evidence_csv():
    """The study's ids are new: either absent from docs/evidence.csv, or present only because the lead merged these
    very rows (same citation and source)."""
    with open(os.path.join(ROOT, "docs", "evidence.csv"), newline="", encoding="utf-8") as f:
        existing = {row["id"]: row for row in csv.DictReader(f)}
    for r in ledger.ROWS:
        if r["id"] in existing:
            assert existing[r["id"]]["citation"] == r["citation"], r["id"]
            assert existing[r["id"]]["doi_or_url"] == r["doi_or_url"], r["id"]


def test_bom_prices_only_where_seen():
    for r in bom.ROWS:
        if r["unit_price"] != bom.NS:
            assert r["price_seen_on"] and r["source"] and r["currency"], r["part"]
            float(r["unit_price"].replace(",", ""))
        else:
            assert not r["price_seen_on"], r["part"]


def test_experiments_and_criteria_consistent():
    ids = [e["id"] for e in experiments.EXPERIMENTS]
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"EXP-T\d\d", i) for i in ids)
    crit = [c["id"] for c in experiments.CRITERIA]
    assert len(crit) == len(set(crit))
    for c in experiments.CRITERIA:
        assert c["experiment_id"] in ids, c["id"]
    for m in experiments.MERGE_MAP:
        targets = re.findall(r"EXP-T\d\d", " ".join(str(v) for v in m.values()))
        assert all(t in ids for t in targets), m


def test_merged_experiments_exist_in_validation():
    text = ""
    for p in ("validation/bench_protocols.md", "validation/README.md", "docs/revJ1_design.md", "docs/revJ_design.md", "docs/revJ_simulation.md",
              "validation/human_study_plan.md", "validation/sim_to_real.md"):
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as f:
                text += f.read()
    missing = [m["existing"] for m in experiments.MERGE_MAP if m["existing"] not in text]
    assert not missing, missing
