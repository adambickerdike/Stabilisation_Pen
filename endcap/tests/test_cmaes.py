import numpy as np

from endcap.cmaes import cmaes


def test_sphere():
    r = cmaes(lambda x: float(np.sum((x - 1.5) ** 2)), np.zeros(5), sigma0=1.0, max_evals=3000, seed=0)
    assert r["f"] < 1e-8
    assert np.allclose(r["x"], 1.5, atol=1e-3)


def test_rosenbrock():
    f = lambda x: float(100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2)
    r = cmaes(f, np.array([-1.0, 1.0]), sigma0=0.5, max_evals=4000, seed=1)
    assert r["f"] < 1e-6


def test_negative_objective_runs_to_the_optimum():
    """A maximisation written as a negative objective must not stop at the first negative value (bug found 2026-09-28)."""
    f = lambda x: float(-(3.0 - np.sum((x - 1.0) ** 2)))
    r = cmaes(f, np.zeros(3), sigma0=1.0, max_evals=1500, seed=2)
    assert r["f"] < -3.0 + 1e-6
    assert r["evals"] >= 1000
