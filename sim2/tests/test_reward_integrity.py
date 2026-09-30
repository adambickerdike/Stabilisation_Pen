"""Adversarial checks: missing ink, timestamp alignment and delayed sensing."""
from types import SimpleNamespace

import numpy as np
import pytest

from sim2.reward import InkCost, InkReference, advance_scored


@pytest.mark.parametrize("error", [0.0, 0.3e-3, 3e-3, 30e-3])
def test_losing_contact_never_improves_same_trajectory_cost(error):
    cost = InkCost()
    writing = cost.evaluate([error, 0], [0, 0], True, True)
    missing = cost.evaluate([error, 0], [0, 0], False, True)
    assert missing["cost"] == pytest.approx(writing["cost"] + cost.missing_ink)
    assert missing["tracking_cost"] == writing["tracking_cost"]


def test_unwanted_ink_is_costly_during_reference_lift():
    cost = InkCost()
    assert cost.evaluate([0, 0], [0, 0], True, False)["cost"] == cost.extra_ink
    assert cost.evaluate([0, 0], [0, 0], False, False)["cost"] == 0


def test_reference_interpolates_time_and_never_uses_future_contact():
    ref = InkReference([0, 0.01, 0.02], [[0, 0], [0.001, 0], [0.002, 0]], [False, True, False])
    p, c = ref.at(0.005)
    assert p == pytest.approx([0.0005, 0])
    assert c is False
    assert ref.at(0.015)[1] is True


def test_subdecision_dropout_cannot_hide_at_good_endpoint():
    class Fake:
        def __init__(self):
            self.k, self.n, self.rdec, self.dt, self.n_thr = 0, 4, 1, 0.001, 0.01
            self.pm = SimpleNamespace(ids={"site:ball": 0})
            self.d = SimpleNamespace(site_xpos=np.zeros((1, 3)))
            self.law = SimpleNamespace(summary=lambda: {"Nb": float(self.k % 2 == 0)})
        def advance(self, n):
            self.k += n
    ref = InkReference([0, 1], [[0, 0], [0, 0]], [True, True])
    out = advance_scored(Fake(), 4, ref, InkCost())
    assert out["missing_fraction"] == 0.5
    assert out["cost"] == 4.5
    assert out["samples"] == 4
    assert out["t"] == pytest.approx(0.003)  # last resolved kinematics, not 0.004


def test_page_validity_and_force_slide_follow_acquisition_latency():
    from sim2 import builder as B, params as P
    from sim2.sensors import OnlineSensors
    pm = B.build(P.Config())
    sens = OnlineSensors(pm, 0.001, seed=20, noise_scale=0)
    sens.reset()
    tip = pm.ids["site:tip"]
    pm.d.site_xpos[tip, 2] = 0
    pm.d.qpos[sens.js] = 0.0002
    r0 = sens.read({"Nb": 0.25})
    assert r0["page_valid"][0] == 0
    assert r0["force"][0] == 0
    assert r0["slide"][0] < 0
    pm.d.site_xpos[tip, 2] = 0.01
    r1 = sens.read({"Nb": 0.0})
    assert r1["force"][0] == 0.25
    assert r1["slide"][0] == pytest.approx(0.0002)
    assert r1["page_valid"][0] == 0
    r2 = sens.read({"Nb": 0.0})
    assert r2["page_valid"][0] == 1  # delayed valid sample from t=0
    r3 = sens.read({"Nb": 0.0})
    assert r3["page_valid"][0] == 0  # delayed invalid sample from t=1 ms
    sens.reset()
    assert sens.read({"Nb": 0.0})["page_valid"][0] == 0
