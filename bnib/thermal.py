r"""Two-node thermal model of the nib actuator with a governor (CALC; parameters labelled in labels.THERMAL).

Nodes: the coil (heat capacity C_c from its copper and bond, labels) and the grip shell over the actuator (C_s: the shell
section and the stator parts bonded to it).  Coil -> shell through R_cs; shell -> room through R_sa, the fin model of a
PEEK tube heated over the actuator's length (revj1/thermal.py generalised to any diameter), optionally with a graphite
spreader in the wall (Rev J.1).  No heat into the hand is counted (conservative).
    C_c dT_c/dt = P - (T_c - T_s)/R_cs,     C_s dT_s/dt = (T_c - T_s)/R_cs - (T_s - T_room)/R_sa
Governor (PROPOSED DESIGN firmware rule): the controller's current is scaled by g = min(1, g_c, g_s),
    g_c = clip((T_c,max - 10 K - T_c)/10 K, 0, 1)^(1/2),  g_s = clip((T_skin,target - T_s)/1.5 K, 0, 1)^(1/2)
so the copper loss is g^2 P_demand and the nib loses authority (it follows its reference less) before any limit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np

from .labels import MAT, THERMAL, val


def fin_R(D: float, wall: float = 1.0e-3, L_src: float = 8e-3, k_shell: float = None, h: float = None,
          spreader: Optional[Dict] = None) -> float:
    """Surface rise per watt of a tube of outer diameter D heated over L_src (K/W), bare or with a spreader of in-plane
    conductivity k_s, thickness t_s and length L_s embedded in the wall (revj1.thermal generalised; CALC)."""
    k = val(MAT["PEEK_k"]) if k_shell is None else k_shell
    h = val(THERMAL["h_conv"]) if h is None else h
    P = math.pi * D
    Ac = math.pi / 4 * (D ** 2 - (D - 2 * wall) ** 2)
    if spreader is None:
        return 1.0 / (h * P * L_src + 2.0 * math.sqrt(h * P * k * Ac))
    A_s = math.pi * (D - 2 * wall) * spreader["t"]
    m = math.sqrt(h * P / (spreader["k"] * A_s))
    x = m * spreader["L"] / 2
    eff = math.tanh(x) / x
    return 1.0 / (h * P * spreader["L"] * eff + 2.0 * math.sqrt(h * P * k * Ac))


GRAPHITE_30 = {"k": 600.0, "t": 0.1e-3, "L": 30e-3, "label": "MFR AMF-158 (PGS a-b plane 600-800 W/mK), Rev J.1 choice"}


@dataclass
class TwoNode:
    C_c: float = 0.5
    C_s: float = 6.0
    R_cs: float = 15.0
    R_sa: float = 33.0
    T_room: float = 30.0
    T_c_max: float = 120.0
    T_s_target: float = 41.0

    def steady(self, P: float) -> Dict:
        Ts = self.T_room + P * self.R_sa
        Tc = Ts + P * self.R_cs
        return {"T_coil_C": Tc, "T_skin_C": Ts, "P_W": P,
                "P_allow_skin_W": (self.T_s_target - self.T_room) / self.R_sa,
                "P_allow_coil_W": (self.T_c_max - 10.0 - self.T_room) / (self.R_sa + self.R_cs)}

    def simulate(self, P_demand: np.ndarray, dt: float, governor: bool = True, T0: Optional[float] = None) -> Dict:
        """Explicit integration (dt << C_c R_cs); returns temperatures, the delivered power and the authority g."""
        n = len(P_demand)
        Tc = np.empty(n); Ts = np.empty(n); g = np.ones(n); P = np.empty(n)
        tc = ts = self.T_room if T0 is None else T0
        for k in range(n):
            gk = 1.0
            if governor:
                gc = min(max((self.T_c_max - 10.0 - tc) / 10.0, 0.0), 1.0) ** 0.5
                gs = min(max((self.T_s_target - ts) / 1.5, 0.0), 1.0) ** 0.5
                gk = min(1.0, gc, gs)
            p = gk * gk * P_demand[k]
            tc += dt * (p - (tc - ts) / self.R_cs) / self.C_c
            ts += dt * ((tc - ts) / self.R_cs - (ts - self.T_room) / self.R_sa) / self.C_s
            Tc[k], Ts[k], g[k], P[k] = tc, ts, gk, p
        return {"T_coil": Tc, "T_skin": Ts, "g": g, "P": P}


def model_for(D: float, L_src: float, m_cu: float, C_s: float = 6.0, spreader: Optional[Dict] = GRAPHITE_30,
              T_room: float = None, wall: float = 1.0e-3) -> TwoNode:
    """A two-node model for a nib: coil capacity from its copper mass (x1.5 for bond and former, ASSUMPTION), shell
    resistance from the fin model (bare or with the graphite spreader); the shell node's capacity C_s scales with the
    shell's diameter (6 J/K at 24 mm, ASSUMPTION: shell section + stator parts bonded to it)."""
    C_c = max(m_cu * 385.0 * 1.5, 0.05)
    R_sa = fin_R(D, wall=wall, L_src=L_src, spreader=spreader)
    C_s = C_s * (D / 24e-3)
    return TwoNode(C_c=C_c, C_s=C_s, R_cs=val(THERMAL["R_cs"]), R_sa=R_sa,
                   T_room=val(THERMAL["T_room"]) if T_room is None else T_room,
                   T_c_max=val(THERMAL["T_coil_max"]), T_s_target=val(THERMAL["T_skin_target"]))


def review_check() -> Dict:
    """The review's single-node screen (C_th 0.5 J/K, R_th 100 K/W, 25 degC start, 120 degC limit): time to the limit at
    1.628 W and 2.68 W (reproduces 43.8 s and 21.9 s; CALC)."""
    out = {}
    for P in (1.628, 2.68):
        Tinf = 25.0 + P * 100.0
        t = -100.0 * 0.5 * math.log(1 - (120.0 - 25.0) / (Tinf - 25.0))
        out[f"{P:g}W"] = t
    return out


def duty_run(tn: TwoNode, P_contact: float, P_penup: float, minutes: float = 30.0, stroke_s: float = 0.35,
             contact: float = 0.70, dt: float = 0.01, governor: bool = True) -> Dict:
    """A long writing run: the demanded power alternates between the contact and pen-up values with a stroke period
    (CALC on the design's powers); returns the peaks, the final temperatures and the authority statistics."""
    n = int(minutes * 60 / dt)
    t = np.arange(n) * dt
    ph = (t % stroke_s) / stroke_s
    Pd = np.where(ph < contact, P_contact, P_penup)
    r = tn.simulate(Pd, dt, governor)
    k30 = int(30.0 / dt)
    return {"T_coil_peak_C": float(r["T_coil"].max()), "T_skin_peak_C": float(r["T_skin"].max()),
            "T_coil_end_C": float(r["T_coil"][-1]), "T_skin_end_C": float(r["T_skin"][-1]),
            "g_min": float(r["g"].min()), "g_mean_last_min": float(r["g"][-int(60 / dt):].mean()),
            "t_governor_s": float(t[np.argmax(r["g"] < 0.999)]) if (r["g"] < 0.999).any() else None,
            "P_delivered_mean_W": float(r["P"].mean()), "minutes": minutes,
            "T_coil_30s_C": float(r["T_coil"][min(k30, n - 1)]),
            "trace": {"t_s": t[::500].tolist(), "T_coil": r["T_coil"][::500].tolist(), "T_skin": r["T_skin"][::500].tolist(),
                      "g": r["g"][::500].tolist()}}
