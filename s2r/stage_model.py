"""Standalone stage + current-loop model for EXP-B05 with physics M1 does not have (C3).

Same equations, rates and step order as M1's stage path in the B05 test build
(core.py: 2 kHz tick sets i_ref; 40 kHz PI current loop with R feed-forward and
back-EMF; symplectic-Euler stage at 25 us with the force from the previous step's
current; Hall read from a delay line), so with every extra switched off it
reproduces the M1 test-build FRF (s2r/tests/test_stage_model.py). Extras, each a
structural difference from M1:

  * flexure mode: the tip (where the LDV looks) is a second mass m2 = r_m m_eq on a
    spring to the lever, so a mode at f2 appears above the stage resonance and the
    measured tip is not the lever coordinate the Hall sees;
  * extra loop delay: i_ref reaches the current loop tau_x later (PWM/SPI chain);
  * release jitter: each 2 kHz tick is released with Gaussian jitter sigma_j
    (config control.exec_jitter is 20 us, assumed; M1 has none);
  * pivot Coulomb friction F_c (stick-slip in the gimbal or lead wires);
  * backlash: a dead band +-b in the actuator-to-lever linkage.

Evidence status: SIMULATION.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np
from numba import njit

from stabpen import params as sp_params

_P = sp_params.load()
DT = 25e-6


@dataclass
class Extras:
    f2_hz: float = 0.0          # flexure mode (0 = rigid tip)
    zeta2: float = 0.02
    mass_ratio2: float = 0.3
    tau_extra: float = 0.0      # s
    jitter_rms: float = 0.0     # s
    coulomb_N: float = 0.0      # tip-equivalent Coulomb friction at the pivot
    backlash_m: float = 0.0     # half-width of the dead band (tip-equivalent)


@njit(cache=True)
def _run(iref_ticks, t_tick, dt, n, m1, k1, c1, m2, k2, c2, nKf, R, L, Rhat, Kpi, Kii, Vbus, emf_on,
         Fc, bl, hd, rec):
    """rec columns: 0 q_lever, 1 q_tip, 2 current, 3 i_ref applied, 4 hall (delayed lever)."""
    q = 0.0; qd = 0.0; x2 = 0.0; x2d = 0.0
    cur = 0.0; vint = 0.0; ir = 0.0
    j = 0
    nt = len(t_tick)
    qbuf = np.zeros(8192)
    for k in range(n):
        t = k * dt
        # tick release (possibly jittered / delayed): apply the newest command whose release time has passed
        while j < nt and t_tick[j] <= t + 1e-12:
            ir = iref_ticks[j]
            j += 1
        # current loop (every step, 40 kHz): PI with R feed-forward, saturating
        e = ir - cur
        vcmd = Rhat * ir + Kpi * e + Kii * vint
        V = min(max(vcmd, -Vbus), Vbus)
        if V == vcmd:
            vint += e * dt
        # mechanics with the previous step's current
        F = -nKf * cur
        fr = 0.0
        if Fc > 0.0:
            fr = -Fc * math.tanh(qd / 1e-5)
        if m2 > 0.0:
            qdd = (F - k1 * q - c1 * qd - k2 * (q - x2) - c2 * (qd - x2d) + fr) / m1
            x2dd = (k2 * (q - x2) + c2 * (qd - x2d)) / m2
            x2d += x2dd * dt
            x2 += x2d * dt
        else:
            qdd = (F - k1 * q - c1 * qd + fr) / m1
        qd += qdd * dt
        q += qd * dt
        if m2 <= 0.0:
            x2 = q
        # electrical
        emf = -nKf * qd if emf_on else 0.0
        ex = math.exp(-dt * R / L)
        cur = cur * ex + (V - emf) / R * (1.0 - ex)
        qbuf[k % 8192] = q
        rec[k, 0] = q
        rec[k, 1] = x2
        rec[k, 2] = cur
        rec[k, 3] = ir
        rec[k, 4] = qbuf[(k - hd) % 8192] if k >= hd else 0.0
    return rec


@njit(cache=True)
def _run_backlash(iref_ticks, t_tick, dt, n, m1, k1, c1, ma, nKf, R, L, Rhat, Kpi, Kii, Vbus, kl, bl, hd, rec):
    """Backlash variant: actuator paddle (tip-equivalent mass ma) drives the lever through a
    stiff link kl with a dead band +-bl."""
    q = 0.0; qd = 0.0; xa = 0.0; xad = 0.0
    cur = 0.0; vint = 0.0; ir = 0.0
    j = 0
    nt = len(t_tick)
    qbuf = np.zeros(8192)
    for k in range(n):
        t = k * dt
        while j < nt and t_tick[j] <= t + 1e-12:
            ir = iref_ticks[j]
            j += 1
        e = ir - cur
        vcmd = Rhat * ir + Kpi * e + Kii * vint
        V = min(max(vcmd, -Vbus), Vbus)
        if V == vcmd:
            vint += e * dt
        F = -nKf * cur
        gap = xa - q
        fl = 0.0
        if gap > bl:
            fl = kl * (gap - bl)
        elif gap < -bl:
            fl = kl * (gap + bl)
        xadd = (F - fl) / ma
        qdd = (fl - k1 * q - c1 * qd) / m1
        xad += xadd * dt
        xa += xad * dt
        qd += qdd * dt
        q += qd * dt
        emf = -nKf * xad
        ex = math.exp(-dt * R / L)
        cur = cur * ex + (V - emf) / R * (1.0 - ex)
        qbuf[k % 8192] = q
        rec[k, 0] = q
        rec[k, 1] = q
        rec[k, 2] = cur
        rec[k, 3] = ir
        rec[k, 4] = qbuf[(k - hd) % 8192] if k >= hd else 0.0
    return rec


class Result:
    """Minimal stand-in for sim.pensim.model.Result with the channels exp_b05 reads."""

    def __init__(self, t, rec):
        self._c = {"t": t, "q_lever": rec[:, 0], "q1": rec[:, 1], "i1": rec[:, 2], "iref1": rec[:, 3],
                   "hall_raw": rec[:, 4]}

    def __getitem__(self, k):
        return self._c[k]


def run(plant: Dict, i_design_t, i_design, ex: Extras, rng, T_amb=25.0, seed_jitter=None):
    """Drive the test build with the designed current (as the M1 B05 run does)."""
    n_lev = float(_P["stage.L2"] / _P["stage.L1"])
    Kf20 = plant["actuator.Kf"]
    Kf_T = Kf20 * (1 + float(_P["actuator.alpha_B"]) * (T_amb - 20.0))
    R20 = plant["actuator.R20"]
    R = R20 * (1 + float(_P["actuator.alpha_cu"]) * (T_amb - 20.0)) + _P["electrical.r_bridge"] + _P["electrical.r_shunt"]
    L = plant["actuator.L"]
    wci = 2 * math.pi * _P["control.current_bw"]
    Kpi = _P["actuator.L"] * wci                       # firmware uses nominal L and R (as the shim)
    Rhat_c = _P["actuator.R20"] + _P["electrical.r_bridge"] + _P["electrical.r_shunt"]
    Kii = Rhat_c * wci
    Rhat = R20 + _P["electrical.r_bridge"] + _P["electrical.r_shunt"]   # M1 feeds forward the true R20
    m = plant["stage.m_eq"]
    k = plant["stage.k_tip"]
    c = 2 * plant["stage.zeta_open"] * math.sqrt(k * m)
    n = int(round(i_design_t[-1] / DT)) + 1
    sdec = int(round(1.0 / (_P["control.f_stage"] * DT)))
    k_tick = np.arange(0, n, sdec)
    t_nom = k_tick * DT
    iref = np.interp(t_nom, i_design_t, i_design)
    t_rel = t_nom + ex.tau_extra
    if ex.jitter_rms > 0:
        t_rel = t_rel + ex.jitter_rms * np.abs(rng.standard_normal(len(t_rel)))
    # M1 convention: the command computed at tick k is used by the current loop in step k
    t_rel = t_rel - 1e-12
    hd = int(round(plant.get("sensing.hall_delay", _P["sensing.hall_delay"]) / DT))
    rec = np.zeros((n, 5))
    if ex.backlash_m > 0:
        ma = 0.1 * m
        kl = ma * (2 * math.pi * 1500.0) ** 2          # stiff link: 1.5 kHz paddle-on-link mode
        _run_backlash(iref, t_rel, DT, n, m - ma, k, c, ma, n_lev * Kf_T, R, L, Rhat, Kpi, Kii,
                      _P["electrical.v_bat_nom"], kl, ex.backlash_m, hd, rec)
    else:
        if ex.f2_hz > 0:
            m2 = ex.mass_ratio2 * m
            m1 = m - m2
            mu = m1 * m2 / m
            k2 = mu * (2 * math.pi * ex.f2_hz) ** 2
            c2 = 2 * ex.zeta2 * math.sqrt(k2 * mu)
        else:
            m1, m2, k2, c2 = m, 0.0, 0.0, 0.0
        _run(iref, t_rel, DT, n, m1, k, c, m2, k2, c2, n_lev * Kf_T, R, L, Rhat, Kpi, Kii,
             _P["electrical.v_bat_nom"], True, ex.coulomb_N, 0.0, hd, rec)
    t = np.arange(n) * DT
    # the log holds the command as computed at each tick (what the firmware writes), not the
    # delayed or jittered instant at which it reached the current loop
    idx = np.clip(np.searchsorted(t_nom, t, side="right") - 1, 0, len(iref) - 1)
    rec[:, 3] = iref[idx]
    return Result(t, rec)
