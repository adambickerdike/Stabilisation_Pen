"""Research calculations must not change unrelated neural-network construction."""
import importlib

import numpy as np
import pytest


def test_physics_imports_preserve_ml_precision_and_complex_response():
    torch = pytest.importorskip('torch')
    old = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float32)
        for module in ('drive.design_opt', 'endcap.linear_torch', 'wholepen.lin', 'opt.touchdown.reduced'):
            importlib.reload(importlib.import_module(module))
            assert torch.get_default_dtype() == torch.float32, module
        # The neighbouring neural network still agrees with float32 input data.
        nn = torch.nn.Linear(2, 1)
        assert nn(torch.zeros(1, 2)).dtype == torch.float32
        # The physical model explicitly retains double and complex precision.
        from wholepen import lin
        asm = lin.Assembly(lin.Model())
        assert asm.M.dtype == torch.float64
        response = asm.solve(2*np.pi*6, asm.u_force_hand(np.array([1., 0., 0.])))
        assert response.dtype == torch.complex128
        assert np.any(np.abs(response.imag.numpy()) > 0)
    finally:
        torch.set_default_dtype(old)


def test_cma_eigenvector_sign_cannot_change_seeded_experiment(monkeypatch):
    from opt.touchdown import bo
    objective = lambda x: float(np.sum((x-.6)**2))
    expected = bo.cmaes(objective, [.2,.2,.2], iters=25, seed=1)
    eigh = np.linalg.eigh

    def opposite_basis(matrix):
        values, vectors = eigh(matrix)
        return values, -vectors

    monkeypatch.setattr(np.linalg, 'eigh', opposite_basis)
    observed = bo.cmaes(objective, [.2,.2,.2], iters=25, seed=1)
    np.testing.assert_array_equal(observed[0], expected[0])
    assert observed[1] == expected[1]


def test_cma_bounded_problem_scores_only_feasible_designs():
    from opt.touchdown import bo
    evaluated = []

    def objective(x):
        evaluated.append(x.copy())
        return float(np.sum((x-1.1)**2))

    x, value, history = bo.cmaes(objective, [.02,.02], sigma0=.8, iters=45, seed=41)
    points = np.asarray(evaluated)
    assert np.all((points >= 0) & (points <= 1))
    assert value == objective(x)
    assert np.linalg.norm(x-1) < .02
    assert all(b['best'] <= a['best'] for a,b in zip(history,history[1:]))
