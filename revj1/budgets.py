r"""Rev J.1 budgets: mass, centre of mass and inertia, length, power and battery per mode (with the nose-coil
sensitivity x1 / x2 / x5), heat at the web.  CALC on the PROPOSED DESIGN of revj1.layout; the mass-property code is
revj.budgets (read-only); nothing measured.
"""
from __future__ import annotations

import json
import math
from typing import Dict

from . import REPO_ROOT, ensure_paths
from . import gimbal as GB
from . import params as P1
from . import power as PW
from . import thermal as TH

ensure_paths()
from revj import budgets as RBU  # noqa: E402
from revj import params as RPA  # noqa: E402


def revJ_reference() -> Dict:
    """Rev J's budgets (results/revJ/budgets.json, read-only) for the comparison columns."""
    b = json.loads((REPO_ROOT / "results" / "revJ" / "budgets.json").read_text())["budgets"]
    return {"mass_base_g": b["mass"]["base"]["mass_g"], "mass_with_endcap_g": b["mass"]["with_endcap"]["mass_g"],
            "com_base_mm": b["mass"]["base"]["com_mm"][2], "com_with_endcap_mm": b["mass"]["with_endcap"]["com_mm"][2],
            "length_base_mm": b["length"]["base_mm"], "length_with_endcap_mm": b["length"]["with_endcap_mm"],
            "hours": {k: v["hours"] for k, v in b["power"]["modes"].items()},
            "hours_with_endcap": {k: v["hours_with_endcap"] for k, v in b["power"]["modes"].items()},
            "total_W": {k: v["total_W"] for k, v in b["power"]["modes"].items()},
            "label": "CALC (Rev J, results/revJ/budgets.json)"}


def gimbal_stiffness(F_pull: float = GB.F_PULL_IMAGES) -> Dict:
    s = GB.Strip(t=P1.GIMBAL["t_um"].value * 1e-6, b=P1.GIMBAL["b_mm"].value * 1e-3, L=P1.GIMBAL["L_mm"].value * 1e-3,
                 alpha_deg=P1.GIMBAL["alpha_deg"].value, lam=P1.GIMBAL["crossing"].value)
    cp = GB.CrossPivot(s, 16)
    k_F = cp.stiffness(-F_pull)                    # the pull compresses the strips (study N's arrangement)
    k_0 = cp.stiffness(0.0)
    zp = RPA.nose_design()["z_p"] * 1e-3
    return {"k_pull_Nm_rad": k_F, "k_unloaded_Nm_rad": k_0, "k_tip_N_m": k_F / zp ** 2, "k_tip_unloaded_N_m": k_0 / zp ** 2,
            "F_pull_N": F_pull, "label": "CALC (revj1.gimbal co-rotational beam model, 75 um strips, compression)"}


def coil_temperatures(rows_fn, n_iter: int = 3) -> Dict:
    """Fixed point: coil loss depends on the copper's temperature, which depends on the loss (CALC)."""
    T = {}
    rows = rows_fn(T)
    for _ in range(n_iter):
        T = {k: TH.coil_temperature(r["nose_coil_W"], 23.0) for k, r in rows.items()}
        rows = rows_fn(T)
    return T, rows


def summary(geo: Dict, travel_factor: float, endcap_sim_W: float, endcap_design_W: float) -> Dict:
    mb = RBU.mass_budget(geo)
    F_g = mb["nose"]["gravity_hold"]["50"]["torque_mNm"] / geo["pivot_z"]          # N at the tip (Rev J.1 nose)
    gs = gimbal_stiffness()
    k_tip = gs["k_tip_N_m"]
    ec = (endcap_sim_W, endcap_design_W)
    cells = PW.cells()
    E = {"LIR14500": cells["LIR14500"]["E_usable_Wh"], "ICR14650": cells["ICR14650"]["E_usable_Wh"]}
    power = {}
    for f in P1.NOSE_POWER_FACTORS.value:
        for page in ("PMW3610_class", "PMW3360_gated", "PMW3360_1kHz"):
            if page != "PMW3610_class" and f != 1.0:
                continue
            T, rows = coil_temperatures(lambda T: PW.modes(k_tip, travel_factor, F_g, T, page_choice=page, endcap_W=ec, factor=f))
            key = f"x{f:g}_{page}"
            power[key] = {"factor": f, "page": page, "coil_T_C": T, "rows": rows,
                          "hours": {cn: PW.hours(rows, e) for cn, e in E.items()}}
    nominal = power["x1_PMW3610_class"]
    coil_nom = {k: r["nose_coil_W"] for k, r in nominal["rows"].items()}
    ht = TH.summary(coil_nom, geo_plate_len(geo))
    ht["web_by_factor"] = {}
    for f in P1.NOSE_POWER_FACTORS.value:
        rows = power[f"x{f:g}_PMW3610_class"]["rows"]
        ht["web_by_factor"][f"x{f:g}"] = TH.web_table({k: r["nose_coil_W"] for k, r in rows.items()}, factors=(1.0,))
    L = {"base_mm": geo["length"], "with_endcap_mm": geo["length_with_endcap"], "limit_mm": RPA.ENVELOPE["length_mm"].value,
         "with_ICR14650_base_mm": geo["length"] + cells["ICR14650"]["extra_length_mm"],
         "with_ICR14650_endcap_mm": geo["length_with_endcap"] + cells["ICR14650"]["extra_length_mm"], "label": "CALC (layout)"}
    return {"mass": mb, "length": L, "gimbal": gs, "F_grav_tip_N": F_g, "electronics": PW.electronics(),
            "page_options": PW.page_options(), "page_needs": PW.NEEDS, "cells": cells, "power": power, "energy_Wh": E,
            "endcap_W": list(ec), "heat": ht, "targets": PW.targets_proposal(), "revJ": revJ_reference(),
            "travel_factor": travel_factor,
            "labels": {"mass": "CALC (revj.budgets.mass_budget on the Rev J.1 layout; +10 % wiring on the base pen, ASSUMPTION)",
                       "power": "CALC (revj1.power; nose coils from study N's duty model and SIM autowrite values, x factor)",
                       "endcap": "SIM (study K model H1, test seeds, the Rev J.1 member; drivers included) .. CALC (design model)"}}


def geo_plate_len(geo: Dict) -> float:
    c = next(x for x in geo["components"] if x["id"] == "coil_plate")
    return c["z1"] - c["z0"]
