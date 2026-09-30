"""Study K: the Rev K integrated layout.  Run:  python3 -m revk.run [--quick]

Writes results/revK/ (or the git-ignored revk/build/quick/ with --quick): revK.json (every number, with the stabpen.provenance block),
layout.json (the Rev J layout schema), budgets.json, sim_params.json, evidence_rows.csv and the figures (PNG + CSV).
The CAD (mechanics/cad/revK_pen.py) reads results/revK/layout.json.  One process, one BLAS thread; caches in revk/build/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import EVIDENCE_CALC, clean, ensure_paths, out_dir, write_json

ensure_paths()


def log(msg: str, t0: float):
    print(f"[{time.time() - t0:7.1f} s] {msg}", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="coarse grids, written to revk/build/quick/ (git-ignored)")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    q = a.quick
    t0 = time.time()
    from . import budgets as BU, counterface as CF, evidence as EV, figures as FG, frontend as F, layout as LY, nib as N
    from . import params as PR, simparams as SP, tolerance as TL
    out = out_dir(q)
    times = {}
    # front end
    t = time.time()
    fc = F.front_close(heel=False, quick=q)
    fc_h = F.front_close(heel=True, quick=q)
    hand = F.hand(fc["R_s_mm"])
    vis = F.visibility(fc["R_s_mm"], quick=q)
    times["front_end_s"] = time.time() - t
    log(f"front end: R_s {fc['R_s_mm']} mm (heel variant {fc_h['R_s_mm']} / wheel {fc_h['R_d_mm']} mm)", t0)
    # counter-face head
    t = time.time()
    hd = CF.design(fc["R_s_mm"], quick=q)
    stack = CF.face_stack(n=4000 if q else 20000)
    refill = CF.refill_change(hd)
    times["head_s"] = time.time() - t
    log(f"head: L_O {hd['L_O_mm']} mm, x_h {hd['x_h_mm']} mm, plate {hd['face']['length_mm']:.1f} x {hd['face']['width_mm']:.1f} mm", t0)
    # nib
    t = time.time()
    coil = N.buildable_coil(quick=q)
    base = LY.base_components(fc, hd, coil)
    ns = N.summary(fc["R_s_mm"], base, quick=q)
    times["nib_s"] = time.time() - t
    log(f"nib: Km x {ns['Km_tip_revK']['x']:.3f}, servo allowed {ns['modes']['by_restraint']['revK_ball_guide']['servo_bw_max_worst_Hz']:.1f} Hz", t0)
    # layout, tolerance, budgets
    t = time.time()
    lay = LY.build(fc, fc_h, hd, coil, ns, stack, hand)
    fcc = {x["id"]: x for x in lay["fit_checks"]}
    sens = TL.sensing(ns["hall"]["gradient_mT_per_mm"]["min_norm"], ns["hall"]["coil_crosstalk_um_per_A"],
                      ns["hall"]["earth_offset_um"], n=4000 if q else 20000)
    mech = TL.mechanics(PR.val(PR.B1["stop_mm"]), PR.val(PR.B1["travel_G4_mm"]),
                        {"ring_bore": 0.0, "optics_block": fcc["F2"]["margin"], "coil_vs_bore": fcc["N1"]["margin"],
                         "plate_hole_vs_carrier": max(fcc["N4"]["margin"], 0.0)}, n=4000 if q else 20000)
    bud = BU.summary(lay, ns, hd)
    sp = SP.build(lay, ns, hd, fc, fc_h, bud)
    times["layout_budgets_s"] = time.time() - t
    log(f"layout: {lay['length']:.1f} mm, {bud['mass']['base']['mass_g']:.1f} g; checks {lay['fit_summary']}", t0)
    # files
    ex = {"command": "python3 -m revk.run" + (" --quick" if q else ""), "times_s": times}
    lay_out = dict(lay)
    lay_out["pivot_z"] = SP.Z_P_VIRTUAL * 1e3
    lay_out["pivot_note"] = "virtual pivot (mm) for sim2j's gimbal model: B1 is a translation nib (revk/simparams.py)"
    files = [write_json(out / "layout.json", lay_out, "PROPOSED DESIGN; CALC (fit checks)", q, ex)]
    files.append(write_json(out / "budgets.json", {"budgets": bud}, EVIDENCE_CALC, q, ex))
    files.append(write_json(out / "sim_params.json", sp, "CALCULATION from the Rev K layout; values labelled", q, ex))
    files.append(EV.write(out / "evidence_rows.csv"))
    hd_small = dict(hd)
    revk = {
        "summary": {
            "length_mm": lay["length"], "mass_g": bud["mass"]["base"]["mass_g"],
            "mass_with_heel_g": bud["mass"]["with_heel_module"]["mass_g"],
            "balance_point_mm": bud["mass"]["balance_point_mm"], "handle_od_mm": lay["handle_od"],
            "front_d_mm": 2 * fc["R_s_mm"], "hours": {k: r["hours"] for k, r in bud["power"]["rows"].items()},
            "hours_heel_variant": {k: r["hours"] for k, r in bud["power_heel_variant"]["rows"].items()},
            "skin_worst_C": bud["heat"]["worst_shell_C"], "web_C_steady_1mm": bud["heat"]["rows"]["steady_1mm"]["web_C"],
            "modes_vs_rule": ns["modes"]["by_restraint"], "cost_usd": bud["cost"]["unit_cost_usd"],
            "cost_heel_usd": bud["cost_heel_variant"]["unit_cost_usd"], "fit_summary": lay["fit_summary"],
            "label": "CALCULATION on a PROPOSED DESIGN (nothing built or measured)"},
        "front_end": {k: v for k, v in fc.items() if k != "history"},
        "front_end_heel_variant": {k: v for k, v in fc_h.items() if k != "history"},
        "hand": hand, "visibility": vis,
        "counter_face_head": hd_small, "face_parallelism_stack": stack, "refill_change": refill,
        "nib": ns, "tolerance": {"sensing": sens, "mechanics": mech, "inputs": TL.tables()},
        "fit_checks": lay["fit_checks"], "fit_summary": lay["fit_summary"], "budgets": bud,
        "sim_params_file": "results/revK/sim_params.json", "evidence_rows_file": "results/revK/evidence_rows.csv",
        "inputs": PR.all_tables(),
    }
    if not a.no_figures:
        t = time.time()
        files += FG.all_figures(lay, bud, hd, out)
        times["figures_s"] = time.time() - t
    times["total_s"] = time.time() - t0
    revk["files"] = files
    files.insert(0, write_json(out / "revK.json", revk, EVIDENCE_CALC, q, ex))
    log(f"wrote {len(files)} files to {out}", t0)
    for f in files:
        print("  ", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
