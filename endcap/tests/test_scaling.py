"""Closed-form laws against hand calculations (CALC)."""
import math

import pytest

from endcap import params as P
from endcap import scaling as SC


def test_reaction_mass_force_and_corner():
    # 30 g, 3.5 mm, 3 Hz: 0.7 x 0.03 x (2 pi 3)^2 x 0.0035 = 26.1 mN
    assert SC.lrm_force(0.03, 3.5e-3, 3.0, 1.0) == pytest.approx(0.7 * 0.03 * (2 * math.pi * 3) ** 2 * 3.5e-3)
    assert SC.lrm_force(0.03, 3.5e-3, 50.0, 0.5) == pytest.approx(0.5)        # actuator-limited at high f
    fc = SC.lrm_corner(0.03, 4e-3, 0.5)
    assert SC.lrm_force(0.03, 4e-3, fc, 0.5) == pytest.approx(0.5, rel=1e-9)


def test_cmg_torque_impulse_corner():
    H = 1.2e-3
    assert SC.cmg_torque(H, 3.0, 30.0, 1.0) == pytest.approx(2 * H * 2 * math.pi * 3 * 1.0)   # angle-limited
    assert SC.cmg_torque(H, 10.0, 30.0, 1.0) == pytest.approx(2 * H * 30.0)                  # rate-limited
    assert SC.cmg_impulse(H, math.pi / 2, n=2) == pytest.approx(4 * H)
    fc = SC.cmg_corner(30.0, 1.0)
    assert SC.cmg_torque(H, fc, 30.0, 1.0) == pytest.approx(2 * H * 30.0)


def test_com_bound_and_weight_shift():
    assert SC.com_shift_bound(0.03, 4e-3, 0.33) == pytest.approx(0.03 * 8e-3 / 0.36)
    assert SC.weight_shift_torque(0.03, 4e-3, 50.0) == pytest.approx(0.03 * P.G0 * 4e-3 * math.cos(math.radians(50)))


def test_rotor_energy_stress_imbalance():
    m = SC.rotor_mass(16e-3, 4e-3, d_hub=0.0)
    assert m == pytest.approx(18e3 * math.pi / 4 * 0.016 ** 2 * 0.004)
    J = SC.rotor_J(m, 16e-3, d_hub=0.0)
    assert J == pytest.approx(m * 0.008 ** 2 / 2)
    assert SC.stored_energy(J, 20000) == pytest.approx(0.5 * J * (20000 * 2 * math.pi / 60) ** 2)
    s = SC.hoop_stress(30000, 0.008)
    assert s < P.UTS_WHA / 50                   # tungsten rotors are far from bursting at pen scale
    assert SC.imbalance_force(0.012, 30000, 2.5e-3) == pytest.approx(0.012 * 2.5e-3 * 30000 * 2 * math.pi / 60)


def test_gyro_ratio_and_modes():
    assert SC.gyro_stiffening_ratio(3e-3, 8.0, 2.875) == pytest.approx(3e-3 * 2 * math.pi * 8 / 2.875)
    wn, wp = SC.nutation_precession(3e-3, 1e-4, 2.9)
    w0 = math.sqrt(2.9 / 1e-4) / (2 * math.pi)
    assert wp < w0 < wn and wn - wp == pytest.approx(3e-3 / 1e-4 / (2 * math.pi))


def test_propeller_momentum_theory():
    T = SC.prop_thrust(22e-3, 1.0)
    assert SC.prop_power_for(T, 22e-3) == pytest.approx(1.0, rel=1e-9)
    assert SC.prop_thrust(22e-3, 8.0) == pytest.approx(4.0 * T, rel=1e-9)     # T ~ P^(2/3)
