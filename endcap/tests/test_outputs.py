"""Evidence rows and the explainer layout follow the project schemas."""
import csv
import json
import os

from endcap import evidence as EV
from endcap import layout as LY
from endcap import params as P

ROOT = P.ROOT
RANGES = {"ACT": (81, 99), "AMF": (120, 134), "HAP": (80, 89), "PAT": (35, 39), "PDT": (39, 42)}


def test_evidence_header_and_ids(tmp_path):
    hdr = next(csv.reader(open(os.path.join(ROOT, "docs", "evidence.csv"))))
    assert EV.HEADER == hdr and len(hdr) == 23
    rows = EV.write(str(tmp_path / "rows.csv"), {"headline": {}})
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    existing = {r["id"] for r in csv.DictReader(open(os.path.join(ROOT, "docs", "evidence.csv")))}
    for i in ids:
        pre, num = i.split("-")
        lo, hi = RANGES[pre]
        assert lo <= int(num) <= hi and i not in existing
    lit = [r for r in rows if r["search_query"] != "n/a (derived)"]
    assert len(lit) >= 25
    for r in lit:
        assert r["access_level"] and r["doi_or_url"] and r["citation"]


def test_layout_schema():
    d = {"class": "LRM2", "x": {"d_s": 0.0117, "L_s": 0.0147, "t_c": 0.00066}, "X": 0.0039, "moving_mass_g": 30.2,
         "parts_g": {"slug_g": 28.5, "magnets_g": 1.7, "copper_g": 3.0, "frame_g": 5.9, "shell_g": 4.6, "electronics_g": 1.5}}
    parts = LY.lrm_parts(d)
    for c in parts:
        assert c["group"] == "endcap" and c["shape"] in ("cylinder", "cone", "tube", "box")
        assert c["moves_with"] in ("handle", "rotor", "gimbal", "inertial_mass")
        assert 129.9 <= c["z0"] < c["z1"] <= 175.01
        for k in ("id", "label", "function", "part", "ledger", "mass_g"):
            assert k in c
        if c["shape"] in ("cylinder", "tube"):
            assert c["d0"] <= 26.0 + 1e-9


def test_layout_schema_cmg():
    d = {"class": "DG1", "choice": ["DG1", "INT"], "x": {"D": 0.0158, "t": 0.0064, "n": 28000.0, "delta": 1.01},
         "parts_g": {"rotors_g": 22.0, "spin_motors_g": 2.0, "bearings_g": 1.4, "frames_g": 1.5, "gimbal_drives_g": 6.6, "shell_g": 4.6,
                     "electronics_g": 1.8}}
    parts = LY.cmg_parts(d)
    kinds = {c["moves_with"] for c in parts}
    assert {"rotor", "gimbal", "handle"} <= kinds
    for c in parts:
        assert c["group"] == "endcap" and c["shape"] in ("cylinder", "cone", "tube", "box")
        assert 129.9 <= c["z0"] < c["z1"] <= 175.01
        if c["shape"] in ("cylinder", "tube"):
            assert c["d0"] <= 26.0 + 1e-9
    assert abs(sum(c["mass_g"] for c in parts) - sum(d["parts_g"].values())) < 0.05
