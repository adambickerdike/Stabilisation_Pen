r"""Quasi-static contact reaction at the ball and the load it places on the stage.

Paper reaction on the ball:  R = N n + f,  f in the page plane.
For kinetic drag  f = -mu N v_hat, with v_hat the ball's sliding direction on
the page written as v_hat = cos(beta) h + sin(beta) t2
(beta = 0: stroke toward the writer's hand, "pull"; beta = pi: "push").

Components in the housing frame (derivation in docs/physics.md, eq. P-7..P-9):
    R.t1 = -N cos(theta) + f_h sin(theta)
    R.t2 = f_t2
    R.a  =  N sin(theta) + f_h cos(theta)
    with f_h = -mu N cos(beta), f_t2 = -mu N sin(beta).

A laterally actuated nib is connected to the housing through (i) the axial
suspension, which can only carry R.a, and (ii) the transverse stage.  For a
massless refill in equilibrium the stage must therefore supply
    F_stage = -R_perp,   |R_perp| = N sqrt((cos th + mu cos(beta) sin th)^2 + (mu sin beta)^2)
This includes the transverse component of the NORMAL reaction, N cos(theta),
which the source report's worked example omitted (correction COR-01).
The axial suspension carries F_a = N (sin th - mu cos(beta) cos th).
"""
from __future__ import annotations

import numpy as np


def reaction_components(N, mu, beta, theta, rho=0.0):
    """Return dict of reaction components (N). Arrays broadcast.

    R_t1, R_t2 : transverse components along t1, t2
    R_x, R_y   : transverse components along housing axes x_H, y_H
    R_a        : axial component (carried by the axial suspension)
    R_perp     : magnitude of the transverse component (carried by the stage)
    """
    N = np.asarray(N, float)
    f_h = -mu * N * np.cos(beta)
    f_t2 = -mu * N * np.sin(beta)
    ct, st = np.cos(theta), np.sin(theta)
    R_t1 = -N * ct + f_h * st
    R_t2 = f_t2
    R_a = N * st + f_h * ct
    # rotate (t1,t2) -> (x_H, y_H): x_H = cos rho t1 + sin rho t2 ...
    R_x = R_t1 * np.cos(rho) + R_t2 * np.sin(rho)
    R_y = -R_t1 * np.sin(rho) + R_t2 * np.cos(rho)
    return {"R_t1": R_t1, "R_t2": R_t2, "R_x": R_x, "R_y": R_y, "R_a": R_a,
            "R_perp": np.hypot(R_t1, R_t2)}


def transverse_load(N, mu, beta, theta):
    """Magnitude of the transverse stage load |R_perp| (N)."""
    return reaction_components(N, mu, beta, theta)["R_perp"]


def transverse_load_bounds(N, mu, theta):
    """Max/min over stroke direction of |R_perp| and the direction-averaged value."""
    betas = np.linspace(0, 2 * np.pi, 361)[:-1]
    vals = np.array([transverse_load(N, mu, b, theta) for b in betas])
    return {"max": vals.max(axis=0), "min": vals.min(axis=0), "mean": vals.mean(axis=0),
            "rms": np.sqrt((vals ** 2).mean(axis=0))}


def report_example_drag(N, mu):
    """The source report's sizing term: lateral drag only (mu N)."""
    return mu * np.asarray(N, float)


def normal_from_axial(F_a, mu, beta, theta):
    """Normal force produced by an axial suspension force F_a (N)."""
    return F_a / (np.sin(theta) - mu * np.cos(beta) * np.cos(theta))


def pressure_modulation(k_eff, q_t1_amp, theta, mu=0.0, beta=np.pi / 2):
    """Amplitude of normal-force modulation caused by the axial accommodation
    s = cot(theta) q_t1 against an effective axial stiffness k_eff (N/m)."""
    s_amp = q_t1_amp / np.tan(theta)
    dFa = k_eff * s_amp
    return dFa / (np.sin(theta) - mu * np.cos(beta) * np.cos(theta))


def series(k1, k2):
    return k1 * k2 / (k1 + k2)
