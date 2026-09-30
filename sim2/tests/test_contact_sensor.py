"""Servo contact must be acquired causally and compared to its contemporaneous stop."""
from dataclasses import replace
import pytest
from sim2 import builder as B, params as P, sim as S
from sim2.contact_sensor import SlideContact
from sim.pensim import scenarios as SCN


def test_slide_gate_waits_for_availability_and_holds_acquisition_geometry():
    cfg = P.Config(sensors=P.Sensors(slide_noise=0., slide_latency=.001, slide_rate=1000.))
    pm = B.build(cfg)
    s = SlideContact(pm)
    pm.d.qpos[s.jq] = pm.m.jnt_range[s.joint, 0] + .0002
    assert s.read(0) is False
    pm.m.jnt_range[s.joint, 0] += .001
    assert s.read(.0005) is False
    assert s.read(.001) is True
    assert s.read(.002) is False


@pytest.mark.parametrize("source,expected", [("measured", 0.), ("force", 1.)])
def test_generic_run_contact_option_is_not_ignored(source, expected):
    st = S.Stepper(B.build(P.Config()), SCN.static_hold(duration=.01), S.RunOptions(contact_from=source))
    st._update_flag = lambda: True
    st.servo_contact_sensor.read = lambda t: False
    st.step()
    assert st.servo.g_eff == pytest.approx(expected * st.servo.alpha_a)
