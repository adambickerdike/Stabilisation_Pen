"""Hand impedance and stage checks (CALC)."""
import math

import numpy as np

from board import hand as H
from board import stage as ST
from board import params as P


def _case(name):
    return next(c for c in H.cases() if c.name == name)


def test_static_compliance_is_springs_in_series():
    c = _case("relaxed")
    h0 = abs(H.compliance(c, [1e-5])[0])
    assert math.isclose(h0, 1 / c.k1 + 1 / c.k2, rel_tol=1e-4)
    c2 = _case("hand_held_still")
    assert math.isclose(abs(H.compliance(c2, [1e-5])[0]), 1 / c2.k1, rel_tol=1e-3)


def test_force_for_correction_inverts_compliance():
    c = _case("lightly_resisting")
    f = H.force_for_correction(2.0, 3.0, c)
    assert math.isclose(f * abs(H.compliance(c, [3.0])[0]) * 1e3, 2.0, rel_tol=1e-9)


def test_step_response_settles_to_static_deflection():
    c = _case("relaxed")
    r = H.step_response(c, 0.3, t_end=2.0)
    assert math.isclose(r["final_mm"], 0.3 * (1 / c.k1 + 1 / c.k2) * 1e3, rel_tol=0.02)


def test_stepper_torque_falls_with_speed_and_stage_modes_positive():
    t = [ST.torque_at_speed(v) for v in (0, 200, 400, 600)]
    assert t[0] >= t[1] >= t[2] >= t[3] >= 0
    assert ST.belt_mode_hz("y") > 20 and ST.belt_mode_hz("x") > ST.belt_mode_hz("y")


def test_plate_centre_deflection_matches_square_plate_table():
    # simply supported square plate, central point load: w = 0.01160 P a^2 / D (Timoshenko)
    a, t, P_N = 300.0, 3.0, 10.0
    w = float(ST.plate_deflection(a / 2, a / 2, (a / 2, a / 2), P_N, a, a, t, n_terms=61))
    w_ref = 0.01160 * P_N * (a * 1e-3) ** 2 / ST.plate_D(t) * 1e3
    assert math.isclose(w, w_ref, rel_tol=0.03)


def test_design_gap_is_stack_sum():
    s = P.STACK
    assert math.isclose(P.design_gap_mm(), s["paper_mm"].value + s["glass_mm"].value + s["clearance_mm"].value)
