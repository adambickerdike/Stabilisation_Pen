"""Guidance law, supervisor and closed-loop simulation checks (SIM)."""
import numpy as np

from board import control as C


def test_projection_on_a_line():
    p = C.Path(np.array([[0.0, 0.0], [10.0, 0.0]]))
    s, q = p.project(np.array([4.0, 1.5]), 3.0)
    assert abs(s - 4.0) < 0.05 and abs(q[1]) < 1e-9


def test_partial_guidance_has_a_deadband_and_points_to_the_path():
    g = C.Guidance(mode="partial", deadband_mm=1.0, k_partial=0.1, b_n=0.0)
    n = np.array([0.0, 1.0])
    t = np.array([1.0, 0.0])
    f_in = g.force(np.array([0.0, 0.5]), 0.5, n, t, np.zeros(2), 0.0)
    f_out = g.force(np.array([0.0, 3.0]), 3.0, n, t, np.zeros(2), 0.0)
    assert np.allclose(f_in, 0.0)
    assert f_out[1] < 0 and abs(f_out[1] + 0.2) < 1e-9


def test_supervisor_caps_slew_limits_and_yields():
    s = C.Supervisor(cap_N=0.4, slew_N_s=8.0, override_mm=4.0, override_s=0.3)
    f = s.step(np.array([2.0, 0.0]), 0.5, True, 1e-3, 0.0)
    assert np.linalg.norm(f) <= 8.0 * 1e-3 + 1e-12
    for k in range(2000):
        f = s.step(np.array([2.0, 0.0]), 0.5, True, 1e-3, k * 1e-3)
    assert abs(np.linalg.norm(f) - 0.4) < 1e-9
    for k in range(1000):
        f = s.step(np.array([2.0, 0.0]), 6.0, True, 1e-3, 2 + k * 1e-3)
    assert np.linalg.norm(f) < 1e-6 and s.events
    assert np.allclose(s.step(np.array([2.0, 0.0]), 0.0, False, 1e-3, 5.0), 0.0)


def test_full_guidance_reduces_tracing_error():
    off = C.scenario_tracing("off", "relaxed")
    full = C.scenario_tracing("full", "relaxed")
    e_off = np.mean([r["metrics"]["ink_to_template_rms_mm"] for r in off])
    e_full = np.mean([r["metrics"]["ink_to_template_rms_mm"] for r in full])
    assert e_full < 0.7 * e_off
    assert max(r["metrics"]["force_max_N"] for r in full) <= 0.4 + 1e-9


def test_guidance_cannot_flip_a_reversal_but_lead_through_can():
    full = C.scenario_reversal("full")
    lead = C.scenario_reversal("lead_through", lead_through=True)
    assert full[1]["metrics"]["bowl_ink_on_correct_side_fraction"] < 0.1
    assert lead[1]["metrics"]["bowl_ink_on_correct_side_fraction"] > 0.8
