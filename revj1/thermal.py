r"""P3: skin temperature over the coil plate, and the heat spreader (CALC; fin model of the PEEK shell as in
revj/budgets.py, generalised to any spreader material and thickness).

Limit (opened here).  ECMA-287 Table 5.2 (ledger AMF-35, re-read for this study): parts continuously held, all
materials, 43 degC (continuous holding assumed below 8 h; derived from EN 563, the predecessor of EN ISO 13732-1).
ECMA-287 B.5: the limit assumes a 25 degC room unless the maker states a higher maximum room temperature T_mra; the
check is then T - T_amb <= 43 - T_mra.  IEC 60601-1 (AMF-34): 41 degC needs no justification.  Proposal: one rated
room, 30 degC; one limit, 43 degC absolute (13 K rise), with 41 degC (11 K) as the design target.

Model.  The coil loss P reaches the shell through R_int (15 K/W, ASSUMPTION, Rev J).  The shell is a PEEK tube (k 0.30
W/mK, MFR AMF-24; 1 mm wall; h 10 W/m^2K, ASSUMPTION) with the heat entering over the plate's length; a spreader
sleeve of in-plane conductivity k_s and thickness t_s, length L_s, makes that stretch nearly isothermal (fin efficiency
of the sleeve, heated in the middle), PEEK fins beyond its ends.  No heat into the hand is counted (conservative).
Spreader placement (PROPOSED DESIGN): laminated into a recess of the shell's inner wall, so the bore does not shrink.
A 0.5 mm aluminium sleeve INSIDE the bore (Rev J's proposal) would hit the swinging magnet cap (margin 0.19 mm at the
stop) and the motors (0.12 mm): it only works embedded in the wall.
"""
from __future__ import annotations

import math
from typing import Dict, Sequence

from . import ensure_paths
from . import params as P1

ensure_paths()
from revj import params as PA  # noqa: E402

D_MM = 24.0


def _shell():
    h = PA.THERMAL["h_W_m2K"].value
    k = PA.THERMAL["k_shell_W_mK"].value
    t = PA.THERMAL["shell_wall_mm"].value
    P = math.pi * D_MM * 1e-3
    Ac = math.pi / 4 * ((D_MM * 1e-3) ** 2 - ((D_MM - 2 * t) * 1e-3) ** 2)
    return h, k, t, P, Ac


def R_bare(L_src_mm: float) -> float:
    """Surface rise per watt over a source of length L inside the bare PEEK shell (revj.budgets.fin_resistance)."""
    h, k, t, P, Ac = _shell()
    return 1.0 / (h * P * L_src_mm * 1e-3 + 2.0 * math.sqrt(h * P * k * Ac))


def R_spreader(L_mm: float, t_mm: float, k_s: float) -> float:
    """Surface rise per watt with a spreader sleeve (length L, thickness t, in-plane conductivity k_s) over the source."""
    h, k, tw, P, Ac = _shell()
    A_s = math.pi * (D_MM - 2 * tw) * 1e-3 * t_mm * 1e-3
    m = math.sqrt(h * P / (k_s * A_s))
    x = m * L_mm * 1e-3 / 2
    eff = math.tanh(x) / x
    return 1.0 / (h * P * L_mm * 1e-3 * eff + 2.0 * math.sqrt(h * P * k * Ac))


def spreader_options(P_design_W: float, L_plate_mm: float, lengths: Sequence[float] = (20.0, 30.0, 40.0)) -> Dict:
    """Every material x thickness x length: resistance, surface rise at P, mass (CALC)."""
    R_int = PA.THERMAL["R_int_K_W"].value
    rows = []
    Rb = R_bare(L_plate_mm)
    rows.append({"material": "none", "t_mm": 0.0, "L_mm": 0.0, "R_K_W": Rb, "rise_K": P_design_W * Rb,
                 "coil_rise_K": P_design_W * (Rb + R_int), "mass_g": 0.0})
    for name, s in P1.SPREADERS.items():
        k_s, rho = s["k"].value, s["rho"].value
        for t in s["t_mm"]:
            for L in lengths:
                R = R_spreader(L, t, k_s)
                mass = math.pi * (D_MM - 2.0) * t * L * rho * 1e-3
                rows.append({"material": name, "t_mm": t, "L_mm": L, "R_K_W": R, "rise_K": P_design_W * R,
                             "coil_rise_K": P_design_W * (R + R_int), "mass_g": mass,
                             "k_W_mK": k_s, "label_k": s["k"].label + " " + s["k"].source})
    return {"P_W": P_design_W, "rows": rows, "R_int_K_W": R_int,
            "label": "CALC (fin model; h, R_int ASSUMPTION; k of PEEK MFR AMF-24; spreader k per params.SPREADERS)"}


CHOSEN = {"material": "PGS_graphite", "t_mm": 0.10, "L_mm": 30.0, "z_mm": (80.0, 110.0),
          "placement": "laminated in a 0.1 mm recess of the shell's inner wall (bore unchanged), insulated from the plate by the "
                       "shell's own PEEK (0.9 mm); covers the plate (z 88.8-91.4) and the web (z about 92)",
          "label": "PROPOSED DESIGN"}


def chosen_R() -> float:
    s = P1.SPREADERS[CHOSEN["material"]]
    return R_spreader(CHOSEN["L_mm"], CHOSEN["t_mm"], s["k"].value)


def chosen_mass_g() -> float:
    s = P1.SPREADERS[CHOSEN["material"]]
    return math.pi * (D_MM - 2.0) * CHOSEN["t_mm"] * CHOSEN["L_mm"] * s["rho"].value * 1e-3


def web_table(coil_W: Dict[str, float], factors: Sequence[float] = (1.0, 2.0, 5.0), R_s: float = None) -> Dict:
    """Web surface and coil temperatures per mode and nose-power factor, rated room 30 degC and a 23 degC room (CALC)."""
    R_s = chosen_R() if R_s is None else R_s
    R_int = PA.THERMAL["R_int_K_W"].value
    room = P1.SKIN["rated_room_C"].value
    lim, tgt = P1.SKIN["held_max_C"].value, P1.SKIN["design_target_C"].value
    out = {}
    for k, P in coil_W.items():
        rows = {}
        for f in factors:
            Pf = P * f
            rise = Pf * R_s
            rows[f"x{f:g}"] = {"coil_W": Pf, "web_rise_K": rise, "web_C_room30": room + rise, "web_C_room23": 23.0 + rise,
                               "coil_rise_K": Pf * (R_s + R_int), "passes_43C_at_30C": room + rise <= lim,
                               "passes_41C_at_30C": room + rise <= tgt}
        out[k] = rows
    return {"rows": out, "R_surface_K_W": R_s, "R_int_K_W": R_int, "room_C": room, "limit_C": lim, "target_C": tgt,
            "allowed_coil_W_43C": (lim - room) / R_s, "allowed_coil_W_41C": (tgt - room) / R_s,
            "label": "CALC (fin model with the chosen spreader; no heat into the hand counted)"}


def coil_temperature(P_W: float, room_C: float = 23.0, R_s: float = None) -> float:
    R_s = chosen_R() if R_s is None else R_s
    return room_C + P_W * (R_s + PA.THERMAL["R_int_K_W"].value)


def summary(coil_W_nominal: Dict[str, float], L_plate_mm: float) -> Dict:
    P_design = coil_W_nominal.get("steady_1mm", 0.17)
    return {"limit": P1.table(P1.SKIN), "spreaders": spreader_options(P_design, L_plate_mm), "chosen": dict(CHOSEN),
            "chosen_R_K_W": chosen_R(), "chosen_mass_g": chosen_mass_g(), "bare_R_K_W": R_bare(L_plate_mm),
            "revJ_Al_inside_bore_conflicts": {"cap_rim_margin_mm": 0.19, "motor_bore_margin_mm": 0.12, "sleeve_mm": 0.5,
                                              "note": "Rev J's 0.5 mm Al sleeve inside the bore over z 82-102 overlaps the cap's "
                                                      "swing and the motors (CALC from Rev J's fit checks)"},
            "web": web_table(coil_W_nominal)}
