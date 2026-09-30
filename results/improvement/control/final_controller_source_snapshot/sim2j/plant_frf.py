r"""Linear frequency responses of the Rev J model (CALC on the SIM model), for the controllers' internal models.

endcap_plant(pm): tip displacement (page x, y) per unit coil force on the reaction mass's two slides (t1, t2), from
MuJoCo's linearisation (mjd_transitionFD) about the rest state with the pen lifted (no paper contact), as sim2's
hand.torque_frf does for joint torques.  The controller uses the model at the nominal grip split r_rot 0.5 (it does
not know the writer's split; study K's convention).
"""
from __future__ import annotations

import numpy as np

from . import ROOT  # noqa: F401
from sim2 import hand as HD  # noqa: E402

_CACHE = {}


def endcap_plant(pm, freqs=None):
    freqs = np.arange(2.0, 16.01, 0.25) if freqs is None else np.asarray(freqs, float)
    key = (id(pm.m), len(freqs))
    if key in _CACHE:
        return _CACHE[key]
    from sim2 import builder as B
    Amat, jac, dt, Minv = HD._linearise_lifted(pm)
    nv = pm.m.nv
    nx = Amat.shape[0]
    lam, V = np.linalg.eig(Amat)
    z = np.exp(1j * 2 * np.pi * freqs * dt)
    G = np.zeros((len(freqs), 2, 2), complex)
    for j, jn in enumerate(("rm_0", "rm_1")):
        e = np.zeros(nv)
        e[pm.jnt_dadr(jn)] = 1.0
        Bv = np.zeros(nx)
        Bv[nv:2 * nv] = dt * (Minv @ e)
        w = np.linalg.solve(V, Bv.astype(complex))
        CV = jac[:2] @ V[:nv, :]
        G[:, :, j] = np.einsum("in,fn,n->fi", CV, 1.0 / (z[:, None] - lam[None, :]), w)
    B.reset(pm)
    _CACHE[key] = (freqs, G)
    return freqs, G
