"""Independent linear calculation for the causal Hall servo.

This is a local, unconstrained one-axis model, not a contact stability proof.
It includes zero-order-held commands, exact linear mechanical/coil dynamics,
delayed angle, backward-difference/low-pass velocity, and the implemented PI-D
update order. Saturation, friction, moving stops and hand coupling are omitted.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.linalg import expm


def closed_loop_matrix(inertia, spring, damping, resistance, inductance,
                       inner_hz, cutoff_hz=300.0, sample_hz=10000.0,
                       delay_ticks=1, inertia_ratio=1.0, torque_ratio=1.0):
    if min(inertia, resistance, inductance, inner_hz, cutoff_hz, sample_hz, inertia_ratio, torque_ratio) <= 0:
        raise ValueError("physical values and gains must be positive")
    if delay_ticks < 0 or int(delay_ticks) != delay_ticks:
        raise ValueError("delay must be a nonnegative integer number of samples")
    dt = 1.0 / sample_hz
    physical_I = inertia * inertia_ratio
    electrical_tau = inductance / resistance
    # State: angle, velocity, actual coil torque. Input: demanded coil torque.
    A = np.array([[0., 1., 0.], [-spring/physical_I, -damping/physical_I, 1/physical_I],
                  [0., 0., -1/electrical_tau]])
    B = np.array([0., 0., torque_ratio/electrical_tau])
    aug = np.zeros((4, 4))
    aug[:3, :3], aug[:3, 3] = A, B
    discrete = expm(aug * dt)
    Ad, Bd = discrete[:3, :3], discrete[:3, 3]
    wi = 2 * np.pi * inner_hz
    kp, kd = inertia * wi**2, 2 * .8 * inertia * wi
    ki = kp * 2 * np.pi * 20
    alpha = -np.expm1(-2 * np.pi * cutoff_hz * dt)
    n = 6 + int(delay_ticks)

    def transition(x):
        measured = x[-1] if delay_ticks else x[0]
        integral = x[3] - dt * measured
        velocity = (1-alpha) * x[4] + alpha / dt * (measured-x[5])
        command = -kp*measured - kd*velocity + ki*integral
        out = np.zeros(n)
        out[:3] = Ad @ x[:3] + Bd * command
        out[3:6] = integral, velocity, measured
        if delay_ticks:
            out[6] = x[0]
            out[7:] = x[6:-1]
        return out

    return np.column_stack([transition(e) for e in np.eye(n)])


def pole_summary(**kwargs):
    eig = np.linalg.eigvals(closed_loop_matrix(**kwargs))
    radius = float(np.max(abs(eig)))
    return {"spectral_radius": radius, "stable_local_linear": bool(radius < 1),
            "max_continuous_growth_per_s": float(math.log(max(radius, 1e-30))*kwargs.get("sample_hz", 10000.0))}
