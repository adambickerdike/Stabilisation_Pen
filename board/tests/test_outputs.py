"""Interface files: layout schema, ledger-row header and id ranges, sensing sanity (CALC)."""
import csv
import json
import os

import numpy as np

from board import RESULTS, REPO_ROOT
from board import bom as B
from board import layout as L
from board import sensing as SE

GROUPS = {"structure", "actuator", "sensor", "electronics", "power", "mechanism", "magnet"}
SHAPES = {"box", "cylinder", "tube", "cone"}


def test_layout_components_follow_the_schema():
    lay = L.layout_json({"evidence_status": "test"})
    assert lay["units"] == "mm" and "board frame" in lay["axis"]
    assert set(lay["carriage_travel"]) == {"x", "y"} and "pen_magnet" in lay
    ids = set()
    for c in lay["components"]:
        for k in ("id", "label", "group", "shape", "moves_with", "function", "part", "ledger"):
            assert k in c, (c["id"], k)
        assert c["group"] in GROUPS and c["shape"] in SHAPES and c["moves_with"] in ("carriage", "board")
        assert ("x0" in c and "size" in c) or ("center" in c and "d" in c and "h" in c)
        assert c["id"] not in ids
        ids.add(c["id"])
    tr = lay["carriage_travel"]
    assert 0 < tr["x"][0] < tr["x"][1] < L.G["board"][0] and 0 < tr["y"][0] < tr["y"][1] < L.G["glass_y"]


def test_evidence_rows_header_and_ids():
    with open(os.path.join(REPO_ROOT, "docs", "evidence.csv"), newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == B.HEADER and len(header) == 23
    allowed = {f"AMF-{i}" for i in range(90, 100)} | {f"HAP-{i}" for i in range(51, 56)} | {f"PAT-{i}" for i in range(26, 31)}
    rows = B.evidence_rows()
    assert rows and all(r["id"] in allowed for r in rows)
    assert all(set(r) == set(header) for r in rows)
    assert len({r["id"] for r in rows}) == len(rows)


def test_hall_ring_localises_without_noise_and_fits_range():
    r = SE.localise_mc(offsets_mm=((5.0, 3.0),), n_draws=3, seed=0)
    assert r["head_field_at_ring_mT"]["fits_range"]
    assert r["rows"][0]["dipole_model_bias"]["magnet_xy_mm"] < 0.5


def test_results_files_exist_after_a_run():
    need = ["board.json", "board_params.json", "layout.json", "evidence_rows.csv", "fig_force_vs_gap.png",
            "fig_force_vs_gap.csv", "fig_force_vs_position.png", "fig_force_vs_position.csv"]
    missing = [n for n in need if not os.path.exists(os.path.join(RESULTS, n))]
    if missing:
        import pytest
        pytest.skip(f"run python3 -m board.run_study first (missing {missing})")
    with open(os.path.join(RESULTS, "board_params.json"), encoding="utf-8") as f:
        p = json.load(f)
    assert p["meta"]["evidence_status"].startswith("CALCULATION")
    assert p["software_force_cap_N"] <= p["max_lateral_force_N"]["at_design_gap_isotropic"]
