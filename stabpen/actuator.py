r"""Actuator scaling, lever transmission and coil electro-thermal relations.

Motor constant of a Lorentz (voice-coil type) actuator
    K_F = N B l_a                 force constant (N/A)
    R   = rho_cu N l_t / A_w      coil resistance
    K_m = K_F / sqrt(R) = B (l_a / l_t) sqrt(lambda V_cu / rho_cu)      (N/sqrt(W))
with B the mean flux density crossing the active conductors, l_a the active
(force-producing) length per turn, l_t the mean turn length, lambda the copper
fill factor and V_cu = A_c l_t the winding volume.  K_m is independent of wire
gauge; gauge only trades voltage against current.  Holding a force F costs
P = (F / K_m)^2 of copper loss regardless of gauge.

Lever (front pivot, actuator behind the pivot): n = L2 / L1.
    F_act = F_tip / n,   x_act = n x_tip,   m_reflected = m_act n^2
    P_hold = (F_tip / (n K_m))^2
"""
from __future__ import annotations

import numpy as np

RHO_CU_20 = 1.72e-8      # ohm m, annealed copper at 20 C (IEC 60028)
ALPHA_CU = 0.00393       # 1/K
ALPHA_BR_NDFEB = -0.0012 # 1/K typical reversible tempco of Br for NdFeB (grade dependent)


def motor_constant(B, la_over_lt, V_cu, fill=0.6, rho=RHO_CU_20):
    """K_m in N/sqrt(W) from geometry (SI inputs)."""
    return B * la_over_lt * np.sqrt(fill * V_cu / rho)


def coil_from_geometry(B, l_active_per_turn, l_turn, A_winding, wire_d, fill=0.6, rho=RHO_CU_20):
    """Wind a coil of given winding cross-section with round wire of copper
    diameter wire_d.  Returns turns, K_F, R, K_m (all SI)."""
    A_w = np.pi * wire_d ** 2 / 4.0
    N = np.floor(fill * A_winding / A_w)
    KF = N * B * l_active_per_turn
    R = rho * N * l_turn / A_w
    return {"N": N, "KF": KF, "R": R, "Km": KF / np.sqrt(R)}


def hold_power(F, Km):
    """Copper loss (W) to hold force F (N) with motor constant Km."""
    return (np.asarray(F, float) / Km) ** 2


def lever(F_tip, x_tip, n):
    return {"F_act": np.asarray(F_tip, float) / n, "x_act": np.asarray(x_tip, float) * n}


def resistance(R20, T_c, alpha=ALPHA_CU):
    return R20 * (1.0 + alpha * (T_c - 20.0))


def steady_temperature_const_force(F, KF20, R20, Rth, T_amb, alpha_cu=ALPHA_CU,
                                   alpha_B=ALPHA_BR_NDFEB, iters=200):
    """Steady coil temperature holding constant force, including the rise of
    copper resistance and the fall of magnet flux with temperature.
    Returns (T, P, I, runaway_flag)."""
    T = T_amb
    for _ in range(iters):
        KF = KF20 * (1.0 + alpha_B * (T - 20.0))
        if KF <= 0:
            return np.inf, np.inf, np.inf, True
        I = F / KF
        P = I ** 2 * resistance(R20, T, alpha_cu)
        T_new = T_amb + Rth * P
        if T_new > 400:
            return T_new, P, I, True
        if abs(T_new - T) < 1e-6:
            return T_new, P, I, False
        T = 0.5 * T + 0.5 * T_new
    return T, P, I, False


def coil_voltage_headroom(I, R, L, f, KF, v_act, r_bridge=0.6, r_shunt=0.2):
    """Peak voltage required for sinusoidal current amplitude I at frequency f
    with actuator velocity amplitude v_act (in phase assumptions: worst case
    magnitude sum).  Returns required volts."""
    w = 2 * np.pi * f
    z = np.hypot(R + r_bridge + r_shunt, w * L)
    return I * z + KF * v_act


def electrical_time_constant(R, L):
    return L / R
