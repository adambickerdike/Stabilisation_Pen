#!/usr/bin/env python3
"""Lumped thermal network: coil -> actuator iron/magnets -> barrel sections ->
ambient and hand, plus PCB and cell, for actuator configuration variants.

Nodes: coil, iron+magnets, barrel_act (actuator bulge), barrel_grip, barrel_rear,
pcb, cell.  Boundaries: ambient (25 C) and hand skin (33 C) through a finger
contact conductance on the grip section.
Evidence status: ANALYTICAL/NUMERICAL CALCULATION with assumed conductances
(listed below with their basis); validate with EXP-B07 thermocouple and IR
measurements on the assembled pen.  Touch limits: 41 C design, 43 C absolute
continuously held (AMF-34, AMF-35; regulatory review required).
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stabpen import plotstyle, provenance  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "thermal")
K_AIR, K_AL, K_EPOXY = 0.026, 167.0, 0.25

NODES = ["coil", "iron", "barrel_act", "barrel_grip", "barrel_rear", "pcb", "cell"]
C = {"coil": 0.44e-3 * 385 + 0.05, "iron": 5.6e-3 * 450, "barrel_act": 4.0e-3 * 900,
     "barrel_grip": 4.5e-3 * 900, "barrel_rear": 5.2e-3 * 900, "pcb": 2.3e-3 * 900, "cell": 8.5e-3 * 1000}


def conductances(coil_type="moving", hand=True):
    area_paddle = math.pi * (4.9e-3 ** 2 - 1.7e-3 ** 2)
    if coil_type == "moving":
        g_cm = K_AIR * 2 * area_paddle / 0.45e-3          # two air gaps (moving coil in air)
    else:
        g_cm = K_EPOXY * area_paddle / 0.1e-3             # coil bonded to iron through 0.1 mm epoxy
    A_wall = math.pi * ((7.5e-3) ** 2 - (6.8e-3) ** 2)
    h_out = 10.0                                            # W/m2K natural convection + radiation (assumed)
    G = {("coil", "iron"): g_cm,
         ("iron", "barrel_act"): 0.2,                       # bonded/press-fit magnet rings (assumed)
         ("barrel_act", "barrel_grip"): K_AL * A_wall / 0.030,
         ("barrel_act", "barrel_rear"): K_AL * A_wall / 0.045,
         ("barrel_rear", "pcb"): 0.02, ("barrel_rear", "cell"): 0.05,
         ("barrel_act", "amb"): h_out * math.pi * 0.016 * 0.025,
         ("barrel_grip", "amb"): h_out * math.pi * 0.015 * 0.030 * (0.5 if hand else 1.0),
         ("barrel_rear", "amb"): h_out * math.pi * 0.015 * 0.085,
         ("coil", "amb_internal"): 0.0}
    if hand:
        G[("barrel_grip", "hand")] = 600.0 * 3.0e-4        # finger contact ~600 W/m2K over ~3 cm2 (assumed)
    return G


def simulate(P_coil, P_pcb=0.06, P_cell=0.01, coil_type="moving", hand=True, T_amb=25.0, T_hand=33.0, t_end=3600.0,
             alpha_cu=0.00393):
    G = conductances(coil_type, hand)
    idx = {n: i for i, n in enumerate(NODES)}

    def rhs(t, T):
        dT = np.zeros(len(NODES))
        # coil copper loss rises with resistance at temperature (constant-force operation)
        q = {"coil": P_coil * (1 + alpha_cu * (T[idx["coil"]] - 25.0)), "pcb": P_pcb, "cell": P_cell}
        for n, Q in q.items():
            dT[idx[n]] += Q
        for (a, b), g in G.items():
            Ta = T[idx[a]]
            if b in idx:
                Tb = T[idx[b]]
                dT[idx[a]] -= g * (Ta - Tb)
                dT[idx[b]] += g * (Ta - Tb)
            elif b == "amb":
                dT[idx[a]] -= g * (Ta - T_amb)
            elif b == "hand":
                dT[idx[a]] -= g * (Ta - T_hand)
        return np.array([dT[i] / C[n] for i, n in enumerate(NODES)])

    sol = solve_ivp(rhs, (0, t_end), np.full(len(NODES), T_amb), max_step=5.0, rtol=1e-6)
    return sol, idx


def main():
    os.makedirs(OUT, exist_ok=True)
    plotstyle.apply()
    import matplotlib.pyplot as plt
    trade = json.load(open(os.path.join(os.path.dirname(OUT), "trade", "config_trade.json")))
    cases = {}
    duty = 0.65
    for c in trade["configs"]:
        if "points" not in c:
            continue
        name = c["config"]
        ctype = "fixed" if "fixed bonded" in name else "moving"
        for pt in ("design", "high"):
            P = c["points"][pt]["P_copper_contact_W"] * duty
            if P > 5:
                cases[f"{name} | {pt}"] = {"P_coil_avg_W": P, "infeasible": True}
                continue
            sol, idx = simulate(P, coil_type=ctype)
            T = sol.y
            cases[f"{name} | {pt}"] = {
                "P_coil_avg_W": P, "coil_type": ctype,
                "T_coil_end_C": float(T[idx["coil"], -1]), "T_grip_end_C": float(T[idx["barrel_grip"], -1]),
                "T_act_surface_end_C": float(T[idx["barrel_act"], -1]),
                "t_to_41C_act_surface_min": float(next((t / 60 for t, v in zip(sol.t, T[idx["barrel_act"]]) if v >= 41.0), float("nan"))),
            }
            if name.startswith("B lever") and pt == "design":
                fig, ax = plt.subplots(figsize=(6.2, 3.4))
                for i, (n, lab) in enumerate((("coil", "coil"), ("barrel_act", "barrel at actuator"), ("barrel_grip", "barrel at grip"))):
                    ax.plot(sol.t / 60, T[idx[n]], color=plotstyle.SERIES[i], label=lab)
                ax.axhline(41, color=plotstyle.MUTED, lw=1.0)
                ax.text(1, 41.5, "41 °C design limit (held surface)", fontsize=8, color=plotstyle.INK2)
                ax.set_xlabel("Writing time (min)")
                ax.set_ylabel("Temperature (°C)")
                ax.set_title("Rev A (moving coil) at the design load, 65% pen-down duty", loc="left")
                ax.legend(loc="center right")
                plotstyle.stamp(fig, "analytical calculation", "lumped network, assumed conductances; not measured")
                fig.tight_layout()
                fig.savefig(os.path.join(OUT, "fig_thermal_revA_design.png"))
                plt.close(fig)
    # steady-state allowable copper loss for 41 C actuator surface (moving and fixed coil)
    allow = {}
    for ctype in ("moving", "fixed"):
        lo, hi = 0.0, 3.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            sol, idx = simulate(mid, coil_type=ctype, t_end=7200.0)
            if sol.y[idx["barrel_act"], -1] > 41.0 or sol.y[idx["coil"], -1] > 120.0:
                hi = mid
            else:
                lo = mid
        allow[ctype] = lo
    meta = provenance.metadata("analytical calculation (lumped thermal network; assumed conductances)",
                               extra={"conductance_basis": "air-gap conduction k=0.026 W/mK; epoxy 0.25 W/mK; Al 167 W/mK; h_out 10 W/m2K; finger contact 600 W/m2K x 3 cm2; hand 33 C"})
    provenance.write_json(os.path.join(OUT, "thermal.json"), {"meta": meta, "cases": cases,
                                                              "allowable_avg_copper_W_for_41C_and_coil120C": allow})
    for k, v in cases.items():
        print(k, {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    print("allowable average copper loss (W):", {k: round(v, 3) for k, v in allow.items()})


if __name__ == "__main__":
    main()
