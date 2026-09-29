"""Gymnasium environment and plug-ins (fast smoke tests)."""
import numpy as np
import pytest

import sim2  # noqa: F401
from sim2 import builder as B
from sim2 import env as E
from sim2 import params as P
from sim2 import plugins as PL
from sim2 import sim as S
from sim2 import verify as V


def test_env_reset_step():
    env = E.PenEnv(E.EnvConfig(seed=300, episode_s=0.3, settle_s=0.1))
    obs, info = env.reset(seed=300)
    assert obs.shape == env.observation_space.shape
    for _ in range(20):
        obs, r, term, trunc, inf = env.step(np.zeros(env.n_act))
        assert np.all(np.isfinite(obs)) and np.isfinite(r)


def test_dr_ranges_are_ordered():
    for k, (lo, hi, kind, src) in E.DR.items():
        assert lo < hi and kind in ("log", "lin") and src
    p = E.sample_dr(np.random.default_rng(0))
    for k, v in p.items():
        lo, hi = E.DR[k][:2]
        assert lo - 1e-12 <= v <= hi + 1e-12


@pytest.mark.parametrize("plugin", [PL.ReactionMass(), PL.EndCapRotor(mode="cmg"), PL.EndCapRotor(mode="gyro"),
                                    PL.HeelDrive(kind="ball"), PL.HeelDrive(kind="wheel"), PL.MultiPlaneNose()])
def test_plugins_build_and_run(plugin):
    pm = B.build(P.h1_check_config(0.5).replace(plugins=[plugin]))
    nc = len(plugin.commands())
    r = S.run(pm, V._still(T=0.05), S.RunOptions(plugin_cmd=lambda t, pm_: [np.zeros(nc)]))
    assert np.all(np.isfinite(r.rec))


def test_env_action_space_grows_with_plugins():
    env = E.PenEnv(E.EnvConfig(base=P.Config(plugins=[PL.ReactionMass()]), seed=301, episode_s=0.2, settle_s=0.05))
    assert env.n_act == 2 + len(PL.ReactionMass().commands())


def test_gymnasium_env_checker():
    import warnings
    from gymnasium.utils.env_checker import check_env
    env = E.PenEnv(E.EnvConfig(seed=300, episode_s=0.3, settle_s=0.1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        check_env(env, skip_render_check=True)
