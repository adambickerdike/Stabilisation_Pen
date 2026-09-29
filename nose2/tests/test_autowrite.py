"""Autowrite smoke test: a two-letter word through HW1 with a +-6 mm nose (SIMULATION verification, not validation)."""
from __future__ import annotations

import math

from nose2 import autowrite as AW


def test_two_letters_no_tremor():
    d = AW.NoseDesign("t", "test nose", mass=0.09, m_tip=3.5e-3, k_tip=10.0, q_lim=6e-3, q_stop=6.5e-3, F_peak=1.0, Km_tip=0.2)
    c = AW.build(100, 300, 2.5, 8.0, 0.0, d, AW.AWSettings(), text="ab")
    assert c.plan.ok
    m = AW.run(c, 1, passes=3)
    assert m["plan_ok"] and math.isfinite(m["ink_err_um"])
    assert m["ink_err_um"] < 150.0                              # the ink follows the letters
    assert m["at_travel_limit"] <= 0.01
    assert m["P_coil_W"] < 1.0
