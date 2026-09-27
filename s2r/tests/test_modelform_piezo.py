"""C3 building blocks: the standalone stage matches M1's test build without extras, the
diagnostics flag missing physics, and the Prandtl-Ishlinskii inverse is exact. SIMULATION."""
import numpy as np
import pytest

import s2r  # noqa: F401
from s2r import exp_b05, ident, modelform, piezo, twin
from s2r import stage_model as sm


def _fit(r):
    f, H, _, _ = ident.frf_h1([r["i1"]], [r["q1"]], 1.0 / (r["t"][1] - r["t"][0]), 2, 300)
    return ident.fit_second_order(f, H, 1e-3 * np.abs(H), fit_delay=True)["p"]


def test_standalone_stage_matches_m1_test_build():
    plant = twin.nominal_plant()
    t_in, i_c = exp_b05.chirp_current(4.0, 10000.0, exp_b05.nominal_amp_fn(30e-6))
    r_m1, _ = exp_b05.run_chirp(plant, t_in, i_c, seed=1)
    r_sm = sm.run(plant, t_in, i_c, sm.Extras(), np.random.default_rng(0))
    p1, p2 = _fit(r_m1), _fit(r_sm)
    assert p2[1] == pytest.approx(p1[1], rel=2e-3)      # natural frequency
    assert p2[2] == pytest.approx(p1[2], rel=2e-2)      # damping ratio
    assert p2[0] == pytest.approx(p1[0], rel=5e-3)      # mass line n K_f / m


def test_diagnostics_pass_control_and_flag_coulomb():
    plant = twin.nominal_plant()
    ok = modelform.run_stage_case(plant, sm.Extras(), np.random.default_rng(1), levels=(10e-6, 100e-6),
                                  n_chirps=2, T_c=6.0)
    bad = modelform.run_stage_case(plant, sm.Extras(coulomb_N=3e-4), np.random.default_rng(1),
                                   levels=(10e-6, 100e-6), n_chirps=2, T_c=6.0)
    assert not modelform.verdicts(ok)["any"]
    v = modelform.verdicts(bad)
    assert v["any"] and ("zeta" in v["drift_flags"] or v["frf_misfit_band"] is not None)


def test_pi_inverse_is_exact_and_fit_recovers_pi():
    u = 25 * np.sin(np.linspace(0, 30, 6000)) * np.exp(-np.linspace(0, 2, 6000))
    true = piezo.PIModel(1.0e-5, np.array([3.0, 8.0, 15.0]), np.array([2e-6, 1e-6, 5e-7]))
    y = true(u)
    assert np.max(np.abs(true.inverse_call(y) - u)) < 1e-9
    fit = piezo.fit_pi(u, y, n_ops=10)
    assert fit.info["resid_rms"] < 1e-3 * np.ptp(y)


def test_bouc_wen_truth_hysteresis_in_assumed_class():
    w = piezo.hysteresis_width(piezo.PiezoPlant())
    assert 0.10 <= w <= 0.15
