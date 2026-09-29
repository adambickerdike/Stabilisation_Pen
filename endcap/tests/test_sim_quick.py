"""Feed-forward sign and one short H1 steering check (uses the numba cache of sim/handpen)."""
import math

import numpy as np

from endcap import sim as S
from sim.handpen.params import Device


def test_torque_feedforward_cancels_in_the_linear_model():
    dev = Device(kind="cmg", H=1.5e-3, delta_max=1.0, rate_max=30.0, axes=(1, 1), added_fixed=0.03, z=0.1525)
    f, G = S.torque_plant(dev, 0.5)
    i = int(np.argmin(abs(f - 10.0)))
    Ts = 5e-4
    t = np.arange(4000) * Ts
    e = np.column_stack([1e-4 * np.sin(2 * np.pi * 10 * t), 0.5e-4 * np.cos(2 * np.pi * 10 * t)])
    u = S.ff_torque(e, np.full(len(t), 10.0), dev, margin=10.0, plant=(f, G))
    # phasor of u at 10 Hz should satisfy G u = -e
    k = slice(2000, 4000)
    ph = np.exp(-2j * np.pi * 10 * t[k])
    U = 2 * np.mean(u[k] * ph[:, None], axis=0)
    E = 2 * np.mean(e[k] * ph[:, None], axis=0)
    assert np.allclose(G[i] @ U, -E, rtol=0.05, atol=2e-6)


def test_cmg_moves_the_tip_more_than_a_mass_at_3Hz():
    cmg = Device(kind="cmg", H=1.4e-3, delta_max=1.1, rate_max=30.0, axes=(1, 1), added_fixed=0.045, z=0.1525)
    k_c = 0.03 * (2 * math.pi * 5) ** 2
    lrm = Device(kind="rm", m=0.03, z=0.1525, stroke=(4e-3, 4e-3, 0.0), F_max=(0.5, 0.5, 0.0), k_c=k_c,
                 c_c=2 * 0.7 * math.sqrt(k_c * 0.03), added_fixed=0.015)
    a = S.steer_case(cmg, 0.5, 3.0, scenario="hold", dur=1.0)["tip_peak_mm"]
    b = S.steer_case(lrm, 0.5, 3.0, scenario="hold", dur=1.0)["tip_peak_mm"]
    assert a > 5 * b


def test_rm_feedforward_matches_revh_when_the_cap_is_loose():
    """endcap.sim.ff_force equals opt/inertial/addon.ff_phasor when neither cap binds, and its cap is the flexure-aware one."""
    import numpy as np
    from sim.handpen.params import Device
    from opt.inertial import addon as AD
    from opt.inertial import revh as RH
    from endcap import sim as S
    m, fc = 0.027, 5.0
    k = m * (2 * np.pi * fc) ** 2
    dev = Device(kind="rm", m=m, z=0.1525, stroke=(4e-3, 4e-3, 0.0), F_max=(0.55, 0.55, 0.0), k_c=k, c_c=1.4 * np.sqrt(k * m), Km=0.8)
    d = RH.RevH()
    n = 400
    t = np.arange(n) * 5e-4
    e = 1e-6 * np.column_stack([np.sin(2 * np.pi * 10 * t), np.cos(2 * np.pi * 10 * t)])     # tiny: no cap binds
    f = np.full(n, 10.0)
    a = AD.ff_phasor(e, f, d, dev)
    b = S.ff_force(e, f, d, dev)
    assert np.allclose(a, b)
    # at 1 Hz the flexure-aware cap is about 25x the old stroke cap (spring-dominated)
    cap_new = S.rm_coil_cap(dev, 1.0, 1.0)
    cap_old = m * (2 * np.pi) ** 2 * 4e-3
    assert 20 < cap_new / cap_old < 30
