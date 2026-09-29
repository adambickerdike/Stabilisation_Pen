"""Energy balance, gyroscopic torque, tremor generators, sensors (fast)."""
import numpy as np

import sim2  # noqa: F401
from sim2 import tremor as TR
from sim2 import verify as V


def test_energy_conservative_and_damped():
    for case in ("conservative", "damped", "actuated"):
        r = V.energy_audit(case, T=0.1)
        assert abs(r["residual_rel"]) < 2e-3, (case, r)


def test_gyroscopic_torque_matches_h_cross_omega():
    r = V.gyro_torque(spin_rpms=(20000,), rates=(5.0,))
    assert r["max_rel_error"] < 1e-3


def test_tremor_profiles_and_gate():
    t = np.arange(0, 4.0, 1e-3)
    speed = np.where((t > 1.0) & (t < 3.0), 0.02, 0.0)
    p = TR.profile("PD_rest", f0=5.0)
    out = TR.torques(t, p, {"ps": 1.0, "fe": 0.5}, np.random.default_rng(0), speed=speed)
    g = out["_gate"]
    assert g[(t > 2.0) & (t < 3.0)].mean() < 0.4          # suppressed while writing
    assert g[t > 3.9].mean() > g[(t > 2.5) & (t < 3.0)].mean()   # re-emerging after the pen stops
    et = TR.torques(t, TR.profile("ET", f0=6.0), {"ps": 1.0}, np.random.default_rng(1))
    f = np.fft.rfftfreq(len(t), 1e-3)
    P_ = np.abs(np.fft.rfft(et["ps"])) ** 2
    assert 4.5 < f[np.argmax(P_[1:]) + 1] < 7.5


def test_online_sensor_shapes():
    from sim2 import builder as B, params as P
    from sim2.sensors import OnlineSensors
    pm = B.build(P.Config())
    s = OnlineSensors(pm, 1e-3, seed=0)
    r = s.read({"Ns": 0.8, "Nb": 0.2, "fsx": 0.0, "fsy": 0.0, "fbx": 0.0, "fby": 0.0})
    assert r["acc"].shape == (3,) and r["gyro"].shape == (3,) and r["hall"].shape == (2,)
