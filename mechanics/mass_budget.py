#!/usr/bin/env python3
"""Mass and centre-of-mass budget with allowances (Rev A and Rev A.1).

Evidence status: CALCULATION from the CAD concept (nominal solids x density,
results/cad/pen_rev*_summary.json) plus explicit allowances for items the CAD
does not model.  Measured masses replace these rows in EXP-M03.

Options evaluated:
  A      Rev A CAD as drawn (10440 cell, 29 mm PCB, aluminium barrel)
  A1     Rev A.1 packaging (pouch cell, 41 mm PCB; DEC-014)
  A1-PR  A1 with a polymer rear barrel (z > 66 mm, glass-filled PC), which the
         2.4 GHz antenna needs anyway (no metal around the chip antenna)
Outputs: mechanics/mass_budget.csv, results/mechanics/mass_budget.json.
Run: python3 mechanics/mass_budget.py   (after mechanics/cad/pen_revA.py [--variant A1])
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402

CAD = os.path.join(ROOT, "results", "cad")
# allowances: (name, mass_g, com_z_mm, basis)
ALLOW = [
    ("adhesives and potting", None, None, "3 % of modelled fixed mass, at its CoM (engineering judgement)"),
    ("flex circuits and coil/battery leads", 0.60, 75.0, "estimate: 3 flexes, 0.05 mm Cu/PI"),
    ("cross-strip gimbal and clamps", 0.12, 12.0, "BeCu strips + PEEK clamp (flexure_calc); CAD still shows wire pivots"),
    ("axial diaphragm and seat", 0.20, 66.0, "spiral-arm diaphragm 0.22 mm BeCu"),
    ("grip sleeve (TPE, 1 mm over 45 mm)", 1.90, 30.0, "elastomer 1.1 g/cm3"),
    ("cap/end plug with USB-C tail board", 1.40, 147.0, "PC plug + tail PCB + receptacle"),
    ("fasteners and pins", 0.30, 60.0, "M1.2 screws / dowels"),
]
CONTINGENCY = 0.10       # on the total, at the total CoM (early concept)
# polymer rear-barrel option: replace the Al barrel beyond z0 by PC-GF30 (1.45 g/cm3)
PR_Z0 = 66.0
RHO_AL, RHO_PC = 2.70e-3, 1.45e-3


def load(tag):
    d = json.load(open(os.path.join(CAD, f"pen_{tag}_summary.json")))
    return d["summary"], d["parts"]


def barrel_rear_fraction(summary):
    """Approximate the rear barrel (z > PR_Z0) as a uniform tube over the grip OD."""
    P = summary["parameters_mm"]
    import math
    ro = P["od_grip"] / 2
    ri = ro - P["wall"]
    L = P["L_total"] - PR_Z0
    V = math.pi * (ro ** 2 - ri ** 2) * L + math.pi * ro ** 2 * 1.0     # tube + 1 mm end wall
    return V, PR_Z0 + L / 2


def budget(tag, polymer_rear=False):
    s, parts = load(tag)
    rows = [{"item": p["part"], "group": p["group"], "source": "CAD", "mass_g": p["mass_g"], "com_z_mm": p["com_z_mm"],
             "basis": f"{p['material']} nominal solid"} for p in parts]
    if polymer_rear:
        V, zc = barrel_rear_fraction(s)
        rows.append({"item": "barrel rear -> PC-GF30 (delta)", "group": "fixed", "source": "option",
                     "mass_g": round(-V * (RHO_AL - RHO_PC), 3), "com_z_mm": round(zc, 1),
                     "basis": f"tube z > {PR_Z0:g} mm, density change Al -> PC-GF30"})
    fixed_m = sum(r["mass_g"] for r in rows if r["group"] == "fixed")
    fixed_c = sum(r["mass_g"] * r["com_z_mm"] for r in rows if r["group"] == "fixed") / fixed_m
    for name, m, z, basis in ALLOW:
        if m is None:
            m, z = 0.03 * fixed_m, fixed_c
        rows.append({"item": name, "group": "allowance", "source": "allowance", "mass_g": round(m, 3),
                     "com_z_mm": round(z, 1), "basis": basis})
    tot = sum(r["mass_g"] for r in rows)
    com = sum(r["mass_g"] * r["com_z_mm"] for r in rows) / tot
    rows.append({"item": f"contingency {CONTINGENCY:.0%}", "group": "allowance", "source": "allowance",
                 "mass_g": round(CONTINGENCY * tot, 3), "com_z_mm": round(com, 1), "basis": "concept-stage margin"})
    tot2 = tot * (1 + CONTINGENCY)
    moving = sum(r["mass_g"] for r in rows if r["group"] == "moving")
    return rows, {"total_g": round(tot2, 2), "com_z_mm": round(com, 1), "moving_g": round(moving, 3),
                  "modelled_g": round(sum(p["mass_g"] for p in parts), 2)}


def main():
    out = {}
    all_rows = []
    for label, tag, pr in (("A", "revA", False), ("A1", "revA1", False), ("A1-PR", "revA1", True)):
        if not os.path.exists(os.path.join(CAD, f"pen_{tag}_summary.json")):
            print("missing", tag); continue
        rows, summ = budget(tag, pr)
        out[label] = summ
        for r in rows:
            all_rows.append({"option": label, **r})
    req = {"REQ": "REQ-FORM-003 mass <= 35 g incl. refill and battery with >= 10 % margin; REQ-FORM-004 CoM <= 70 mm from the tip (provisional)"}
    with open(os.path.join(ROOT, "mechanics", "mass_budget.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader(); w.writerows(all_rows)
    meta = provenance.metadata("calculation (CAD solids x density + allowances)")
    provenance.write_json(os.path.join(ROOT, "results", "mechanics", "mass_budget.json"), {"meta": meta, "options": out, **req})
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
