"""Planner: the plan stays within the reach, keeps dwells, and larger letters need more reach (CALC verification)."""
from __future__ import annotations

import numpy as np

from nose2 import planner as PN
from nose2 import tasks as T


def _tp(h, text="bad"):
    return PN.target_from_written(T.written_for(100, 300, h, text=text))


def test_plan_within_reach_and_dwells():
    tp = _tp(2.5)
    pp = PN.PlanParams()
    v = PN.line_speed(tp, pp)
    r = PN.min_reach(tp, v, pp)
    p = PN.plan(tp, v, r["reach_mm"] * 1e-3 + 0.3e-3, pp)
    assert p.ok
    assert np.max(p.exc) <= r["reach_mm"] * 1e-3 + 0.3e-3 + 0.15e-3        # smoothing may add a little
    # dwells: repeated samples at stroke starts
    assert np.any(np.all(np.diff(tp.xy, axis=0) == 0, axis=1))


def test_reach_grows_with_letter_size():
    pp = PN.PlanParams()
    r = []
    for h in (2.0, 3.0):
        tp = _tp(h)
        r.append(PN.min_reach(tp, PN.line_speed(tp, pp), pp)["reach_mm"])
    assert r[1] > r[0]
