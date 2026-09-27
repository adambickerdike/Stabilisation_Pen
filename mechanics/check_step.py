#!/usr/bin/env python3
"""Re-import every exported STEP file with CadQuery/OpenCASCADE and record solid
counts, validity and volume (a parse check, not a physical check).
Output results/cad/step_import_check.json.  Run: python3 mechanics/check_step.py"""
import glob
import json
import os
import sys

import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stabpen import provenance  # noqa: E402


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "cad", "*.step"))):
        try:
            shp = cq.importers.importStep(f).val()
            solids = shp.Solids()
            rows.append({"file": os.path.basename(f), "ok": True, "n_solids": len(solids),
                         "all_valid": all(s.isValid() for s in solids), "volume_mm3": round(sum(s.Volume() for s in solids), 2)})
        except Exception as e:  # noqa: BLE001
            rows.append({"file": os.path.basename(f), "ok": False, "error": repr(e)[:200]})
    meta = provenance.metadata("tool check (STEP re-import with OpenCASCADE)", extra={"cadquery": cq.__version__})
    provenance.write_json(os.path.join(ROOT, "results", "cad", "step_import_check.json"), {"meta": meta, "files": rows})
    for r in rows:
        print(r)
    return 0 if all(r["ok"] and r.get("all_valid") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
