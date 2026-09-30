"""Regressions for live contact timing and deterministic physical RL episodes."""
import numpy as np
import pytest


def test_contact_available_only_after_declared_delay():
    from sim2 import builder as B, params as P
    from sim2j.sensing import OnlineSensors
    pm = B.build(P.Config())
    sens = OnlineSensors(pm, Ts=0.0005, seed=2, noise_scale=0)
    sens.reset()
    lo = pm.m.jnt_range[sens.j_refill, 0]
    pm.d.qpos[sens.js] = lo + 0.0002
    r0 = sens.read(0)
    assert r0["contact"] is False
    assert r0["contact_sample"][:2] == (0, 0.001)
    # A moving front stop after acquisition must not alter the queued reading.
    pm.m.jnt_range[sens.j_refill, 0] += 0.001
    r1 = sens.read(0.0005)
    assert "contact_sample" not in r1
    assert r1["contact"] is False
    r2 = sens.read(0.001)
    assert r2["contact"] is True
    assert r2["contact_t"] == 0
    sens.read(0.0015)
    assert sens.read(0.002)["contact"] is False
    sens.reset()
    assert sens.read(0)["contact"] is False


@pytest.mark.parametrize("p_free", [0.0, 1.0])
def test_seeded_reset_reproducible_and_free_probability_honoured(p_free):
    from sim2j.rl import RevJTremorEnv
    env = RevJTremorEnv(writers=[25001], episode_s=0.10, settle_s=0.10, p_free=p_free,
                       fixed_params={"theta": 50.0}, heel=False)
    a, ia = env.reset(seed=601)
    a1, r1, _, _, m1 = env.step(np.zeros(3))
    b, ib = env.reset(seed=601)
    b1, r2, _, _, m2 = env.step(np.zeros(3))
    assert ia["free"] is bool(p_free)
    assert ib == ia
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(a1, b1)
    assert r1 == r2
    assert m1["cost"] == m2["cost"]
    assert m1["samples"] == 8
    with pytest.raises(ValueError):
        env.step([0, np.nan, 0])


def test_clean_target_is_common_across_servo_candidates():
    from sim2j.rl import RevJTremorEnv
    references = []
    for hz in (80, 400):
        env = RevJTremorEnv(writers=[25002], episode_s=.08, settle_s=.08, p_free=0, heel=False,
                           fixed_params={"inner_hz": hz, "f0": 7.3}, reference_mode="ideal_clean")
        env.reset(seed=211)
        references.append(env.ref_ink.copy())
        assert env.f0 == 7.3
        assert env._shared["ref"].cfg.nose.velocity_source == "legacy_true"
        assert env._shared["ref"].cfg.nose.hall_noise == 0
    np.testing.assert_array_equal(*references)


@pytest.mark.parametrize("source,expected_authority", [("measured", 0.0), ("legacy_force", 1.0)])
def test_inner_servo_contact_gate_uses_firmware_measurement(source, expected_authority):
    from dataclasses import replace
    from sim2j import revj as RJ, stepper as ST
    from sim2j.firmware import FWConfig
    from sim.pensim import scenarios as SCN

    cfg = RJ.config(heel=False)
    cfg = cfg.replace(nose=replace(cfg.nose, contact_source=source))
    st = ST.RevJStepper(RJ.build(cfg), SCN.static_hold(duration=.01), FWConfig(), record=False)
    st._update_flag = lambda: True  # privileged physical contact disagrees with delayed reading
    st.fw.contact = False
    st.fw.tick = lambda t: np.zeros(2)
    st.step()
    assert st.servo.g_eff == expected_authority * st.servo.alpha_a
