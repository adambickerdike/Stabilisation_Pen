#!/usr/bin/env python3
"""Bill of materials for the Rev A research electronics, from the design spec.

Status column: SELECT = parameter-class placeholder, no part chosen;
VERIFY = part chosen, datasheet or reference-design check outstanding;
GENERIC = passive specified by value/package/tolerance (any qualified vendor).
No prices or stock data: availability must be checked at ordering time.
Run: python3 electronics/gen/make_bom.py  -> electronics/bom_revA.csv
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from design_revA import build  # noqa: E402
from placement_study import board_of  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "bom_revA.csv")


def status(p):
    v = p.fields.get("Verify", "")
    if "SELECT" in v or "SELECT" in p.value:
        return "SELECT"
    if p.lib_id in ("Device:R", "Device:C", "Device:L", "Device:FerriteBead") and not p.fields.get("MPN"):
        return "GENERIC+VERIFY" if v else "GENERIC"
    return "VERIFY" if v or not p.fields.get("MPN") else "OK"


def main():
    groups = {}
    for sh in build():
        for p in sh.parts:
            key = (p.lib_id, p.value, p.footprint, p.fields.get("MPN", ""), p.dnp)
            g = groups.setdefault(key, {"refs": [], "parts": []})
            g["refs"].append(p.ref)
            g["parts"].append(p)
    rows = []
    for (lib, val, fp, mpn, dnp), g in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        p0 = g["parts"][0]
        notes = sorted({p.fields.get("Verify", "") for p in g["parts"]} - {""})
        rows.append({
            "Refs": " ".join(sorted(g["refs"], key=lambda r: (r.rstrip("0123456789"), int("0" + r[len(r.rstrip("0123456789")):])))),
            "Qty": len(g["refs"]), "Value": val, "Symbol": lib, "Footprint": fp,
            "Manufacturer": p0.fields.get("Manufacturer", ""), "MPN": mpn,
            "Tolerance": p0.fields.get("Tolerance", ""), "Voltage": p0.fields.get("Voltage", ""),
            "DNP": "DNP" if dnp else "", "Board": ";".join(sorted({board_of(r) for r in g["refs"]})),
            "Status": status(p0), "Notes": " | ".join(notes)})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n = sum(r["Qty"] for r in rows)
    by = {}
    for r in rows:
        by[r["Status"]] = by.get(r["Status"], 0) + 1
    print(f"wrote {OUT}: {len(rows)} lines, {n} placements; status lines {by}")


if __name__ == "__main__":
    main()
