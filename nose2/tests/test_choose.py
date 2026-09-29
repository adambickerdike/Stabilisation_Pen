"""The selection rule on synthetic rows (CALC verification of choose.py)."""
from __future__ import annotations

from nose2 import choose as CH


def _row(kind, bore, x, P, m, feas=True):
    return {"kind": kind, "bore": bore, "x_min_req_mm": x, "mu_m": 4.0, "feasible": feas, "P_autowrite_W": P, "mass_added_g": m,
            "Km_tip": 0.1, "m_eff_tip_g": 3.0}


def test_rule_lowest_J_then_flat_parts():
    best = [_row("gimbal_sphere", "22", 6.0, 0.10, 15.0), _row("gimbal_radial", "22", 6.0, 0.12, 16.0),
            _row("gimbal_sphere", "24", 6.0, 0.05, 17.0)]
    c = CH.choose(best, 6.0)
    assert c["handle_od"] == 24.0 and c["design"]["kind"] == "gimbal_sphere"      # lowest J; the flat one is 51 % worse
    best[2]["P_autowrite_W"] = 0.12
    c = CH.choose(best, 6.0)
    assert c["handle_od"] == 22.0 and c["design"]["kind"] == "gimbal_radial"      # flat design within 25 % of the best
    alt = CH.alternatives(best, 6.0)
    assert alt["no_flat_preference"]["kind"] == "gimbal_sphere" and alt["smallest_handle_first"]["handle_od"] == 22.0


def test_rule_falls_back_to_larger_handle_and_lower_travel():
    best = [_row("gimbal_sphere", "22", 6.0, 0.10, 15.0, feas=False), _row("gimbal_sphere", "24", 6.0, 0.05, 15.0)]
    assert CH.choose(best, 6.0)["handle_od"] == 24.0
    best = [_row("gimbal_sphere", "24", 5.0, 0.05, 15.0)]
    c = CH.choose(best, 6.0)
    assert c["x_chosen_mm"] == 5.0 and c["shortfall_mm"] == 1.0


def test_required_travel():
    rows = [{"x_height_mm": 2.5, "speed_factor": 1.0, "reach_mm": 3.3}, {"x_height_mm": 2.5, "speed_factor": 1.0, "reach_mm": 4.1}]
    r = CH.required_travel(rows)
    assert r["x_req_mm"] == 6.0 and abs(r["need_mm"] - 5.1) < 1e-9


def test_coarse_fine_is_reported_not_chosen():
    best = [_row("coarse_fine", "24", 6.0, 0.02, 15.0), _row("gimbal_sphere", "24", 6.0, 0.10, 15.0)]
    assert CH.choose(best, 6.0)["design"]["kind"] == "gimbal_sphere"
