"""Slow checks (run with --runslow): MyoArm linearisation, one H1 comparison case, a quick study stage."""
import numpy as np
import pytest

import sim2  # noqa: F401


@pytest.mark.slow
def test_myoarm_passive_posture_is_stable_and_impedance_positive():
    from sim2 import myo as MY
    m, d, info = MY.build()
    r = MY.impedance(0.0, m, d, info)
    assert r["qacc_residual"] < 1e-6
    assert r["n_unstable"] == 0
    for ax in "xyz":
        assert min(1.0 / np.array(r["dynamic_fit"][ax]["compliance_mag_m_per_N"])) > 0


@pytest.mark.slow
def test_h1_comparison_one_case_within_tolerance():
    from sim2 import h1compare as HC
    out = HC.compare_grid([{"seed": 300, "f0": 8.0, "amp": 1.0e-3}], 0.5, log=None, controllers=("oracle",))
    row = out["rows"][0]
    assert abs(row["unmod_rel"]) < HC.TOL["unmod_rel"]
    assert abs(row["d_oracle"]) < HC.TOL["oracle_abs"]


@pytest.mark.slow
def test_run_study_quick_stage(tmp_path, monkeypatch):
    from sim2 import run_study as RS
    # Test execution must not overwrite the committed historical study cache.
    monkeypatch.setattr(RS, "CACHE", str(tmp_path / "cache"))
    RS.main(["--quick", "--stages", "gyro"])


@pytest.mark.slow
def test_stable_baselines3_smoke():
    """A PPO agent can train on the environment (a few hundred steps; interface check, not a result)."""
    from stable_baselines3 import PPO
    from sim2 import env as E
    env = E.PenEnv(E.EnvConfig(seed=300, episode_s=0.2, settle_s=0.05))
    model = PPO("MlpPolicy", env, n_steps=64, batch_size=32, n_epochs=1, verbose=0, seed=0, device="cpu")
    model.learn(total_timesteps=128)
    obs, _ = env.reset(seed=301)
    a, _ = model.predict(obs, deterministic=True)
    assert a.shape == env.action_space.shape
