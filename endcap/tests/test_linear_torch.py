"""The differentiable model reproduces opt/inertial/linear_ext (numpy) and its gradients are exact."""
import math

import numpy as np
import pytest
import torch

from endcap import linear_torch as LT
from opt.inertial import revh as RH
from opt.inertial.linear_ext import LinearExt, x0_trans
from sim.handpen.params import Device


def test_matches_linear_ext_reaction_mass():
    k_c = 0.03 * (2 * math.pi * 5) ** 2
    c_c = 2 * 0.7 * math.sqrt(k_c * 0.03)
    dev = Device(kind="rm", m=0.03, z=0.1525, stroke=(3e-3, 3e-3, 0.0), F_max=(1, 1, 0), k_c=k_c, c_c=c_c, added_fixed=0.01)
    lm = LinearExt(RH.config_B(RH.RevH(), r_rot=0.5, device=dev))
    el = LT.EndcapLinear(0.5)
    tdev = dict(m_fix=0.01, z_fix=0.1525, m_r=0.03, z_r=0.1525, k_c=k_c, c_c=c_c)
    for f in (2.0, 10.0):
        w = 2 * math.pi * f
        x0n = x0_trans(lm, f, A=1e-3)[0:2]
        Xf = lm.solve(w, lm.input_vector("F_t1").astype(complex))[0:2]
        Xt = lm.solve(w, lm.input_vector("tau_t2").astype(complex))[0:2]
        with torch.no_grad():
            x0t, G = el.responses(tdev, f, 1e-3, inputs=("F_t1", "tau_t2"))
        # differences come only from the added fixed mass's own-length inertia (a rod in numpy, a point here)
        assert np.allclose(np.abs(x0t.numpy()), np.abs(x0n), rtol=2e-3, atol=1e-9)
        assert np.allclose(np.abs(G[:, 0].numpy()), np.abs(Xf), rtol=2e-3, atol=1e-9)
        assert np.allclose(np.abs(G[:, 1].numpy()), np.abs(Xt), rtol=2e-3, atol=1e-9)


def test_matches_linear_ext_gyro_exactly():
    lm = LinearExt(RH.config_B(RH.RevH(), r_rot=0.3, device=Device(kind="gyro", H=2e-3, z=0.15)))
    el = LT.EndcapLinear(0.3)
    with torch.no_grad():
        x0t = el.responses(dict(H_gyro=2e-3), 6.0, 1e-3, inputs=())[0]
    assert np.allclose(np.abs(x0t.numpy()), np.abs(x0_trans(lm, 6.0, A=1e-3)[0:2]), rtol=1e-9)


def test_gradient_matches_central_difference():
    el = LT.EndcapLinear(0.5)
    xref = el.x0_nodev(10.0, 1e-3)
    L = torch.tensor([5e-3, 5e-3])

    def ratio(m):
        x0, G = el.responses(dict(m_fix=m, z_fix=0.1525), 10.0, 1e-3)
        return LT.scaled_inverse_ratio(x0, G, L, xref)

    m = torch.tensor(0.02, requires_grad=True)
    r = ratio(m)
    r.backward()
    eps = 1e-6
    with torch.no_grad():
        fd = (ratio(torch.tensor(0.02 + eps)) - ratio(torch.tensor(0.02 - eps))) / (2 * eps)
    assert float(m.grad) == pytest.approx(float(fd), rel=1e-5)
