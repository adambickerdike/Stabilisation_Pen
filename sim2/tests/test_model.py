"""Model construction, parameters and the grip equivalence with H1 (fast)."""
import json
import math

import mujoco
import numpy as np
import pytest

import sim2  # noqa: F401
from sim2 import builder as B
from sim2 import hand as HD
from sim2 import params as P


def test_config_serialises_and_labels():
    cfg = P.Config()
    json.dumps(cfg.to_dict())
    assert cfg.contact.model == "h1"
    tab = P.labels_table()
    assert len(tab) > 10


def test_build_default_and_masses():
    pm = B.build(P.Config())
    assert pm.m.nq > 10
    # Rev H masses (opt/inertial/revh.py via results/revH/layout.json): handle ~67 g, nose ~7 g, refill ~0.9 g
    assert abs(pm.info["handle"]["m"] - 0.0671) < 0.002
    assert abs(pm.info["nose"]["m"] - 0.00696) < 0.0005
    assert abs(pm.info["nose_I_pivot"] - 6.0e-6) < 0.3e-6


def test_grip_equivalence_with_h1_static():
    """At 0.2 Hz the pen-tip compliance (pen lifted, nose rigid) equals H1's lumped HAP-26-structure hand."""
    pm = B.build(P.h1_check_config(0.5).replace(nose_on=False))
    f = np.array([0.2])
    H = HD.tip_frf(pm, f)
    C = HD.hap26_compliance(f)
    for d in "xyz":
        assert abs(abs(H[d][0]) / abs(C[0]) - 1.0) < 0.01, d


def test_front_stop_and_refill_range():
    pm = B.build(P.Config())
    j = pm.ids["jnt:refill_s"]
    lo, hi = pm.m.jnt_range[j]
    assert lo < 0 < hi


@pytest.mark.parametrize("hand_model", ["h1", "arm"])
def test_both_hand_models_step(hand_model):
    from sim2 import sim as S
    from sim.pensim import scenarios as SCN
    pm = B.build(P.Config(hand_model=hand_model))
    r = S.run(pm, SCN.static_hold(duration=0.15))
    assert np.all(np.isfinite(r.rec))
    assert r["Nb"][-1] > 0.0


def test_from_identified_maps_s2r_names():
    vals = {"actuator.Kf": 0.8, "actuator.R20": 4.0, "stage.k_tip": 20.0, "writing.mu_eff": 0.2, "hand.grip_stiffness": 700.0,
            "sensing.opt_delay": 3e-3, "unknown.name": 1.0}
    cfg = P.from_identified(vals)
    assert abs(cfg.nose.K_f - 0.8) < 1e-9 and cfg.nose.R == 4.0
    assert abs(cfg.nose.k_r - 20.0 * cfg.geom.z_p ** 2) < 1e-12
    assert cfg.contact.mu_ball == 0.2 and cfg.hand.k_nib == 700.0 and cfg.sensors.page_latency == 3e-3
    assert "unknown.name" in cfg.label
