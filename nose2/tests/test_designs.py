"""Design models: adjoint gradients against central differences, and basic physics (CALC verification)."""
from __future__ import annotations

import math

import torch

from nose2 import designs as DS
from nose2 import optimise as OP


def test_gradients_match_finite_differences():
    for kind in ("gimbal_sphere", "gimbal_radial"):
        res = OP.grad_check(kind)
        for k, (g, fd) in res.items():
            assert abs(g - fd) <= 1e-4 * max(abs(fd), 1e-3), (kind, k, g, fd)


def test_power_scales_with_force_constant():
    v = {k: torch.tensor(0.5 * (lo + hi), dtype=DS.DT) for k, (lo, hi) in DS.VAR_BOUNDS["gimbal_sphere"].items()}
    duty = DS.Duty()
    o1 = DS.evaluate("gimbal_sphere", v, DS.Parts(grade="N42SH"), duty)
    o2 = DS.evaluate("gimbal_sphere", v, DS.Parts(grade="N52"), duty)
    # same geometry, stronger magnets: Km up by the remanence ratio; copper loss = 2 (F / Km)^2 (two axes) and lower
    # (not by exactly the square: the back iron, and so the moving mass, grows with the flux)
    ratio = DS.MAGNET_GRADES["N52"][0] / DS.MAGNET_GRADES["N42SH"][0]
    assert math.isclose(float(o2["Km_act"] / o1["Km_act"]), ratio, rel_tol=1e-9)
    for o in (o1, o2):
        assert math.isclose(float(o["P_autowrite"]), float(2 * (o["F_aw_rms"] / o["Km_tip"]) ** 2), rel_tol=1e-12)
    assert float(o2["P_autowrite"]) < float(o1["P_autowrite"])


def test_cmaes_on_a_quadratic():
    import numpy as np
    x, f = OP.cmaes(lambda x: float(np.sum((x - 0.3) ** 2)), np.full(4, 0.7), 0.3, iters=80, popsize=10, seed=1)
    assert f < 1e-6 and np.allclose(x, 0.3, atol=1e-3)


def test_screening_numbers():
    s = DS.screening(DS.Duty())
    assert s["galvo_pair"]["mass_g"] == 36.0 and s["ultrasonic_piezo"]["driver_power_W"] == 10.0


def test_pareto_matches_brute_force():
    import numpy as np
    rng = np.random.default_rng(3)
    rows = [{"X_min_mm": rng.uniform(4, 8), "Km_tip": rng.uniform(0.05, 0.3), "mass_added_g": rng.uniform(10, 40),
             "P_autowrite_W": rng.uniform(0.05, 0.3)} for _ in range(400)]
    keys = (("X_min_mm", 1), ("Km_tip", 1), ("mass_added_g", -1), ("P_autowrite_W", -1))
    A = np.array([[r[k] * s for k, s in keys] for r in rows])
    brute = {i for i in range(len(rows)) if not (np.all(A >= A[i], axis=1) & np.any(A > A[i], axis=1)).any()}
    fast = {next(i for i, r in enumerate(rows) if r is f) for f in OP.pareto(rows)}
    assert fast == brute
