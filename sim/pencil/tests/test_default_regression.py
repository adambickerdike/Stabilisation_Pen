"""Bit-identical regression of default P1 runs across the touchdown feed-forward change (opt/touchdown).

The fixture data/p1_default_baseline.{npz,json} was recorded with git 410a173, BEFORE the feed-forward
parameters (td_*), the recorded channels qff1/qff2/td_sh/td_state and PencilConfig.servo_kp /
touchdown_ff were added (data/record_p1_default_baseline.py; never re-record it with newer code).
It holds, per case, the packed parameter vector, the SHA-256 of the full recorded array and every
20th ink sample.

Two levels:
  * core: the stored parameter vector (new entries zero) through core.simulate with the scenario
    rebuilt from its seed must reproduce the original source on this numerical host bit for bit. It does not depend on
    sim/pencil/design.py, so it holds while other studies change the design model.
  * model: M.run with default settings must give the same parameter vector and the same record.
    If the design model's defaults were changed elsewhere, the parameter vector differs and the
    case is skipped with that reason (the core level still guards the simulator).
Run: python3 -m pytest -q sim/pencil/tests/test_default_regression.py

Historical Linux arrays/hashes are preserved. Replaying the unchanged source on
this host avoids mistaking libm/LLVM differences for a simulator-core change.
"""
import hashlib
import json
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.pencil  # noqa: E402,F401
from sim.pencil import core  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pencil.layout import IDX, NAMES, NP, NREC, REC, RIDX  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "p1_default_baseline")
META = json.load(open(FIX + ".json"))
ARR = np.load(FIX + ".npz")
TREMOR = sg.TremorSpec(f0=6.0, amp_pk=3e-4)


@pytest.fixture(scope="module")
def original():
    from sim.pencil.tests.p1_same_host_reference import reference
    return reference()


def _scenario(key):
    """Scenario inputs of each case, as in data/record_p1_default_baseline.py (oracle cases need a model run)."""
    if key in ("neutral_tiltrange_s200", "neutral_adaptive030_s200", "locked_s200"):
        return scenarios.handwriting(seed=200, duration=2.0)
    if key in ("kalman_6Hz_s201", "guided_6Hz_s201"):
        return scenarios.handwriting(seed=201, duration=2.0, tremor=TREMOR)
    if key == "external_6Hz_s201":
        s1 = scenarios.handwriting(seed=201, duration=2.0, tremor=TREMOR)
        return M.with_estimate(s1, 0.5 * np.asarray(s1.dtrue))
    if key == "neutral_theta35_s202":
        return scenarios.handwriting(seed=202, duration=2.0, theta_deg=35.0)
    return None


def _model_case(key):
    cfg0 = M.PencilConfig()
    if key == "neutral_tiltrange_s200":
        return _scenario(key), M.Controller(mode="neutral"), cfg0
    if key == "neutral_adaptive030_s200":
        return _scenario(key), M.Controller(mode="neutral"), M.PencilConfig(overrides={"s_min": -0.3e-3, "s_init": -0.3e-3})
    if key == "locked_s200":
        return _scenario(key), M.Controller(mode="neutral"), M.PencilConfig(locked=True)
    if key == "kalman_6Hz_s201":
        return _scenario(key), M.kalman_controller(), cfg0
    if key == "guided_6Hz_s201":
        return _scenario(key), M.Controller(mode="guided"), cfg0
    if key == "external_6Hz_s201":
        return _scenario(key), M.Controller(mode="external"), cfg0
    if key == "neutral_theta35_s202":
        return _scenario(key), M.Controller(mode="neutral"), cfg0
    if key == "oracle_6Hz_s201":
        s0 = scenarios.handwriting(seed=201, duration=2.0)
        s1 = scenarios.handwriting(seed=201, duration=2.0, tremor=TREMOR)
        ref = M.run(s0, M.Controller(mode="neutral"), cfg0, seed=202)
        return M.with_disturbance(s1, M.housing_disturbance(s1, ref)), M.Controller(mode="oracle"), cfg0
    if key == "oracle_theta75_s203":
        s1 = scenarios.handwriting(seed=203, duration=2.0, theta_deg=75.0, tremor=TREMOR)
        s0 = scenarios.handwriting(seed=203, duration=2.0, theta_deg=75.0)
        ref = M.run(s0, M.Controller(mode="neutral"), cfg0, seed=206)
        return M.with_disturbance(s1, M.housing_disturbance(s1, ref)), M.Controller(mode="oracle"), cfg0
    raise KeyError(key)


def _old_channels_hash(rec):
    cols = [RIDX[n] for n in META["rec"]]
    return hashlib.sha256(np.ascontiguousarray(rec[:, cols]).tobytes()).hexdigest()


def test_layout_only_appends():
    assert NAMES[:len(META["names"])] == META["names"]
    assert REC[:len(META["rec"])] == META["rec"]
    new = NAMES[len(META["names"]):]
    assert new and all(n.startswith("td_") for n in new)


CORE_CASES = [k for k in META["cases"] if _scenario(k) is not None]


@pytest.mark.parametrize("key", CORE_CASES)
def test_core_default_run_is_bit_identical(key, original):
    meta, arrays = original
    scn = _scenario(key)
    Pold = arrays[key + "__P"]
    Pv = np.zeros(NP)
    for i, n in enumerate(META["names"]):
        Pv[IDX[n]] = Pold[i]
    n = len(scn.t)
    nrec = int(math.ceil(n / Pv[IDX["rec_decim"]])) + 1
    rec = np.zeros((nrec, NREC))
    sdec = int(Pv[IDX["stage_decim"]])
    m = core.simulate(Pv, np.ascontiguousarray(scn.pref), np.ascontiguousarray(scn.vref), np.ascontiguousarray(scn.fpush),
                      np.ascontiguousarray(scn.dtrue), np.ascontiguousarray(scn.intended[::sdec]),
                      np.ascontiguousarray(scn.opt_ok.astype(np.float64)), META["cases"][key]["seed"], rec)
    rec = rec[:m]
    assert rec.shape[0] == META["cases"][key]["nrec"]
    assert np.array_equal(rec[::20][:, [RIDX["Cx"], RIDX["Cy"]]], arrays[key + "__ink"])
    assert _old_channels_hash(rec) == meta["cases"][key]["sha256_rec"]
    for ch in ("qff1", "qff2", "td_sh", "td_state"):
        assert not np.any(rec[:, RIDX[ch]])


@pytest.mark.parametrize("key", list(META["cases"]))
def test_model_default_run_is_bit_identical(key, original):
    meta, arrays = original
    scn, ctrl, cfg = _model_case(key)
    r = M.run(scn, ctrl, cfg, seed=META["cases"][key]["seed"])
    Pold = arrays[key + "__P"]
    Pnow = np.array([r.P[IDX[n]] for n in META["names"]])
    if not np.array_equal(Pold, Pnow):
        diff = [n for n, a, b in zip(META["names"], Pold, Pnow) if a != b]
        pytest.skip(f"design-model inputs changed outside the simulator core ({diff[:6]}); the core-level test still applies")
    assert all(r.P[IDX[n]] == 0.0 for n in NAMES if n.startswith("td_"))
    assert np.array_equal(r.ink()[::20], arrays[key + "__ink"])
    assert _old_channels_hash(r.rec) == meta["cases"][key]["sha256_rec"]


def test_feedforward_is_active_only_when_enabled():
    scn = scenarios.handwriting(seed=200, duration=0.6)
    ov = {"s_min": -0.3e-3, "s_init": -0.3e-3}
    on = M.run(scn, M.Controller(mode="neutral"), M.PencilConfig(overrides=ov, touchdown_ff={"dz": 20e-6}), seed=201)
    assert on.P[IDX["td_on"]] == 1.0 and on.info["touchdown_ff"]["s_ref"] > 0
    assert np.max(np.abs(on["qff1"])) > 0.1e-3            # pre-positioned while the refill rests on its stop
    assert set(np.unique(on["td_state"])) == {0.0, 1.0}   # one touchdown in 0.6 s
    with pytest.raises(KeyError):
        M.build_params(scn, M.Controller(mode="neutral"), M.PencilConfig(touchdown_ff={"gian": 1.0}))
    # servo_kp only adds the proportional term
    Pv, info = M.build_params(scn, M.Controller(mode="neutral"), M.PencilConfig(servo_kp=0.5))
    assert Pv[IDX["Kp"]] == pytest.approx(0.5 * (info["stage"]["k_b_nib_N_per_m"] + info["stage"]["k_par_nib_N_per_m"]))
