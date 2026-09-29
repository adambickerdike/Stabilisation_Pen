"""The calculations in rig.run_all use the stage the CAD describes; the CAD fit checks pass.
Skipped until python3 -m rig.run_all --cad (or the mechanics/cad/rig_*.py scripts) has written the summaries."""
import json
import os

import pytest

from rig import RESULTS, run_all

CAD = os.path.join(RESULTS, "cad")


def _load(name):
    p = os.path.join(CAD, f"{name}_summary.json")
    if not os.path.exists(p):
        pytest.skip(f"{p} not written yet")
    with open(p) as f:
        return json.load(f)["summary"]


def test_stage_constants_match_cad():
    s = _load("rig_nib")
    for pen, o in s["by_pen"].items():
        c = o["calc"]
        assert abs(c["stage_k_N_per_m"] - run_all.STAGE_K) / run_all.STAGE_K < 0.02
        assert abs(c["moving_mass"]["stage_without_pen_g"] / 1e3 - run_all.STAGE_M) / run_all.STAGE_M < 0.10


@pytest.mark.parametrize("name", ["rig_contact", "rig_nib", "rig_grip", "rig_pagesense", "rig_coupon", "rig_recpen"])
def test_cad_fit_checks_pass(name):
    s = _load(name)
    txt = json.dumps(s)
    if name == "rig_contact":
        assert s["interference_with_bed"] == []
        assert all(not r["hits_on_arc_frame"] for r in s["clearance_by_theta"])
    elif name == "rig_nib":
        for o in s["by_pen"].values():
            assert o["interference_with_bed"] == []
            assert all(not r["self_interference"] for r in o["clearance_by_theta"])
    elif name == "rig_grip":
        for r in s["checks"]:
            assert r["interference_with_bed"] == [] and r["mount_vs_pen"] == []
    elif name == "rig_pagesense":
        assert s["mode_A_sled"]["interference_with_bed"] == [] and s["mode_B_nose"]["interference_with_bed"] == []
    elif name == "rig_coupon":
        assert s["interference_at_rest"] == []
    elif name == "rig_recpen":
        for o in s["by_pen"].values():
            assert o["checks"]["cell_fits"] and o["checks"]["refill_free_0p3mm"] and not o["checks"]["parts_outside_shell"]
            assert o["mass"]["target_reachable"]
    assert "overlap_mm3" not in txt or name in ("rig_contact", "rig_nib", "rig_grip")
