"""Estimator causality, held samples, freshness and frequency-domain agreement."""
import math
import numpy as np
import pytest

from sim2.hall_velocity import HallVelocity


def test_held_sample_never_creates_extra_velocity_updates():
    est = HallVelocity(300)
    est.observe(0, 0)
    est.observe(0.001, 0.002)
    before = est.read(0.0011, 0.002)
    assert est.observe(0.001, 999) is False
    assert est.read(0.0012, 0.002).value == before.value
    assert est.n_updates == 2
    assert est.read(0.0031, 0.002).valid is False
    assert est.read(0.0009, 0.002).valid is False


def test_estimator_uses_acquisition_interval_not_delivery_interval():
    est = HallVelocity(1e6)
    est.observe(0.1, 0.2)
    est.observe(0.102, 0.206)
    assert est.read(0.110, 0.02).value == pytest.approx(3.0)
    with pytest.raises(ValueError):
        est.observe(0.101, 0.203)


def test_sinusoidal_response_matches_backward_difference_and_lowpass():
    fs, f, fc = 10000.0, 10.0, 300.0
    t = np.arange(10000) / fs
    est = HallVelocity(fc)
    out = []
    for ti in t:
        est.observe(ti, math.sin(2 * math.pi * f * ti))
        out.append(est.read(ti, 1e-3).value)
    z = np.exp(1j * 2 * np.pi * f / fs)
    a = -np.expm1(-2 * np.pi * fc / fs)
    H = fs * (1 - 1/z) * a / (1 - (1-a)/z)
    expected = np.imag(H * np.exp(2j * np.pi * f * t))
    np.testing.assert_allclose(np.asarray(out)[2000:], expected[2000:], atol=1e-10)


def test_future_perturbation_cannot_change_past_velocity():
    a, b = HallVelocity(), HallVelocity()
    for k in range(100):
        x = math.sin(k * 0.05)
        a.observe(k * 1e-3, x)
        b.observe(k * 1e-3, x if k < 70 else x + 10)
        if k < 70:
            assert a.read(k * 1e-3, 0.002) == b.read(k * 1e-3, 0.002)


def test_noise_variance_matches_independent_filter_impulse_energy():
    fs, fc, sigma = 10000.0, 300.0, 5e-6 / 0.07648
    rng = np.random.default_rng(411)
    est = HallVelocity(fc)
    samples = rng.normal(0, sigma, 60000)
    out = []
    for k, x in enumerate(samples):
        est.observe(k / fs, x)
        out.append(est.read(k / fs, 0.001).value)
    alpha = -np.expm1(-2 * np.pi * fc / fs)
    # Sum of squared impulse coefficients of D(z)*LP(z).
    variance = 2 * alpha**2 * sigma**2 * fs**2 / (2-alpha)
    assert np.var(out[1000:]) == pytest.approx(variance, rel=0.04)


def test_servo_feedback_has_no_true_velocity_or_early_hall_read():
    from dataclasses import replace
    from sim2 import builder as B, params as P
    from sim2.sim import NoseServo

    cfg = P.Config(nose=P.Nose(hall_noise=0.0, hall_delay=150e-6))
    pm = B.build(cfg)
    servo = NoseServo(pm)
    dt = 1 / cfg.nose.servo_rate
    servo.servo_tick(dt, 0)
    assert not servo.hall_feedback_valid
    assert servo.Icmd == [0.0, 0.0]
    for k in range(1, 6):
        pm.d.qvel[servo.va] = [100.0 + k, -50.0 - k]
        servo.servo_tick(dt, 0)
        assert servo.feedback_velocity == [0.0, 0.0]
    assert servo.hall_feedback_valid
    assert servo.hall_estimators[0].t == pytest.approx(0.0003)
    old_angle = servo.hall_angles[0]
    pm.d.qpos[servo.qa[0]] = 0.001
    servo.servo_tick(dt, 0)
    assert servo.hall_angles[0] == old_angle  # new sample is not available yet
    servo.servo_tick(dt, 0)
    assert servo.hall_angles[0] == old_angle
    servo.servo_tick(dt, 0)
    assert servo.hall_angles[0] == pytest.approx(0.001)

    legacy = NoseServo(B.build(cfg.replace(nose=replace(cfg.nose, velocity_source="legacy_true"))))
    legacy.pm.d.qvel[legacy.va] = [7.0, -3.0]
    legacy.servo_tick(dt, 0)
    assert legacy.feedback_velocity == [7.0, -3.0]


def test_servo_stale_feedback_clears_current_and_holds_integrator():
    from sim2 import builder as B, params as P
    from sim2.sim import NoseServo

    cfg = P.Config(nose=P.Nose(hall_noise=0.0, hall_delay=0.0, hall_max_age=0.0005))
    servo = NoseServo(B.build(cfg))
    dt = 1 / cfg.nose.servo_rate
    for _ in range(3):
        servo.servo_tick(dt, 0)
    assert servo.hall_feedback_valid
    servo.hall_next_acquisition = 1000  # simulate loss of new Hall acquisitions
    for _ in range(6):
        servo.servo_tick(dt, 0)
    before = list(servo.ei)
    servo.servo_tick(dt, 0)
    assert not servo.hall_feedback_valid
    assert servo.Icmd == [0.0, 0.0]
    assert servo.ei == before


def test_causal_servo_design_includes_sample_delay_and_coil_lag():
    from sim2.servo_design import closed_loop_matrix
    from sim2j import revj as RJ
    pm = RJ.build(RJ.config(heel=False))
    kwargs = dict(inertia=pm.info["nose_I_pivot"], spring=pm.cfg.nose.k_r,
                  damping=pm.info["nose_c_flex"], resistance=pm.cfg.nose.R, inductance=pm.cfg.nose.L_ind)
    old = closed_loop_matrix(**kwargs, inner_hz=400)
    repaired = closed_loop_matrix(**kwargs, inner_hz=80)
    assert np.max(np.abs(np.linalg.eigvals(old))) > 1.05
    assert np.max(np.abs(np.linalg.eigvals(repaired))) < 0.99
    # Physically worse delay and uncertain inertia/force gain are evaluated
    # with the same designed gains, not recalibrated ideal parameters.
    stressed = closed_loop_matrix(**kwargs, inner_hz=80, delay_ticks=4, inertia_ratio=.7, torque_ratio=1.3)
    assert np.max(np.abs(np.linalg.eigvals(stressed))) < .998
