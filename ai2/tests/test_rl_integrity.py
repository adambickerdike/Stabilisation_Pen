"""Replay windows are time limits; features respect their public observation space."""
import numpy as np
import pytest

from ai2 import rl_env as RE
from ai2.tests.test_ai2 import _episode


@pytest.mark.parametrize("cls", [RE.GateEnv, RE.ResidualEnv])
def test_replay_window_truncates_and_keeps_finite_valid_final_observation(cls):
    ep = _episode(T=127)
    ep["amp"][:] = 0.1
    ep["ratio"][:] = 1000
    env = cls(RE.ReplayBackend([ep]))
    obs, _ = env.reset(options={"full": True})
    assert env.observation_space.contains(obs)
    term = trunc = False
    n = 0
    while not (term or trunc):
        obs, _, term, trunc, _ = env.step(np.zeros(env.action_space.shape))
        assert env.observation_space.contains(obs)
        n += 1
        assert n < 130
    assert term is False and trunc is True
    with pytest.raises(RuntimeError):
        env.step(np.zeros(env.action_space.shape))


def test_arbiter_applies_policy_to_final_partial_window():
    ep = _episode(T=127)
    w = RE.policy_weights(lambda obs: np.array([0.75]), ep)
    assert np.all(w[:RE.DECIM] == 0)
    assert np.all(w[RE.DECIM:] == 0.75)


def test_replay_data_not_silently_dropped():
    with pytest.raises(ValueError):
        RE.ReplayBackend([])
    with pytest.raises(ValueError):
        RE.ReplayBackend([_episode(), {"X": np.zeros((10, 7))}])


def test_learned_factories_ignore_unrelated_float64_default():
    import torch
    from ai2 import learned
    from realtrack.netmodel import make_tcn
    original = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        models = [learned.make_tcn(7, 2, ch=8, dil=(1, 2)),
                  learned.make_transformer(7, 2, d=8, heads=2, layers=1, ff=16),
                  make_tcn(ch=8, dil=(1, 2))]
        for model, n_in in zip(models, [7, 7, 3]):
            assert next(model.parameters()).dtype == torch.float32
            out = model(torch.zeros((1, 32, n_in), dtype=torch.float32))
            assert out.dtype == torch.float32 and torch.isfinite(out).all()
    finally:
        torch.set_default_dtype(original)
