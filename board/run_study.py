"""One command for the guidance-board study: ``python3 -m board.run_study``.

Writes results/board/: board.json (everything, with provenance), board_params.json
(interface for the handwriting-outcomes study), layout.json (3-D explainer),
evidence_rows.csv (proposed ledger rows), fig_*.png with CSV twins; then runs
mechanics/cad/guidance_board.py (STEP + drawing) unless --no-cad.

Evidence status: CALC and SIM only; nothing built or measured.
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time

import board  # noqa: F401  (sets thread limits before numpy)
import numpy as np

from stabpen import provenance
from . import RESULTS, REPO_ROOT
from . import params as P
from . import magnetics as M
from . import hand as H
from . import stage as ST
from . import sensing as SE
from . import control as C
from . import architectures as A
from . import bom as B
from . import layout as L
from . import figures as FG

GAPS = [0.5, 1.0, 1.5, 2.0, 2.2, 2.5, 2.7, 3.0, 3.7, 4.0, 5.0]
ZLIFT_GAPS = [6.0, 8.0, 11.0, 15.7, 20.0]


def _log(msg, t0):
    print(f"[{time.time() - t0:6.1f} s] {msg}", flush=True)


def constrained_capability(F, offs, fz_lo, fz_hi, n_dir=36):
    th = np.radians(np.arange(0, 360, 360 / n_dir))
    best = []
    for a in th:
        e = np.array([math.cos(a), math.sin(a)])
        par = F[:, 0] * e[0] + F[:, 1] * e[1]
        perp = np.abs(-F[:, 0] * e[1] + F[:, 1] * e[0])
        ok = (perp <= 0.05 * np.maximum(par, 1e-12) + 0.01) & (F[:, 2] >= fz_lo) & (F[:, 2] <= fz_hi)
        v = np.where(ok, par, -np.inf)
        best.append(float(v.max()))
    return {"isotropic_N": min(best), "best_N": max(best), "normal_band_N": [fz_lo, fz_hi]}


def workspace_map(gap_mm, pen, travel_design, travel_page, paper, step=(10.0, 11.0)):
    """Isotropic lateral force available at each pen (ball) position on the page."""
    offs = M.offset_grid(16.0, 1.0)
    head = M.Head()
    F_hi = M.force_at_offsets(head, pen, gap_mm, offs)
    F_lo = M.force_at_offsets(head, pen, gap_mm - 0.2, offs)
    x0, y0, w, h = paper
    xs = np.arange(x0, x0 + w + 1e-9, step[0])
    ys = np.arange(y0, y0 + h + 1e-9, step[1])
    X, Y = np.meshgrid(xs, ys)
    az = math.radians(pen.az_deg)
    lever = pen.behind_mm * np.array([math.cos(az), math.sin(az)])
    out = {}
    for name, trav in (("design", travel_design), ("no_margin", travel_page)):
        Fm = np.full(X.shape, np.nan)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                pb = np.array([X[i, j], Y[i, j]])
                pm = pb + lever
                # glass sag at the pen under a 10 N hand load at the pen (supported on the walls)
                wsag = float(ST.plate_deflection(pm[0] - 3.0, pm[1] - 3.0, (pb[0] - 3.0, pb[1] - 3.0), 10.0, 294.0, 357.0,
                                                 P.STACK["glass_mm"].value, n_terms=15))
                a = min(max(wsag / 0.2, 0.0), 1.0)
                F = F_hi * (1 - a) + F_lo * a
                hp = pm + offs
                ok = ((hp[:, 0] >= trav["x"][0]) & (hp[:, 0] <= trav["x"][1]) &
                      (hp[:, 1] >= trav["y"][0]) & (hp[:, 1] <= trav["y"][1]))
                if ok.sum() < 5:
                    Fm[i, j] = 0.0
                    continue
                Fm[i, j] = max(0.0, M.lateral_capability(F[ok], offs[ok], n_dir=24)["lateral_isotropic_N"])
        out[name] = Fm
    return X, Y, out


def _in_guided(X, Y):
    gx, gy, gw, gh = L.G["guided"]
    return (X >= gx - 1e-9) & (X <= gx + gw + 1e-9) & (Y >= gy - 1e-9) & (Y <= gy + gh + 1e-9)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-cad", action="store_true")
    ap.add_argument("--quick", action="store_true", help="fewer gaps and simulation cases (tests)")
    a = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(RESULTS, exist_ok=True)
    meta = provenance.metadata("CALCULATION + SIMULATION (magpylib 5.2 magnetostatics, linear dynamics, plate theory, "
                               "closed-loop guidance simulation on synthetic paths with the HAP-26 hand model); "
                               "PROPOSED DESIGN; nothing built or measured",
                               seeds={"tracing": 0, "sensing_mc": 1},
                               extra={"magpylib": M.magpy.__version__, "script": "board/run_study.py",
                                      "doc": "docs/guidance_board.md"})
    gaps = [1.0, 2.7, 3.7] if a.quick else GAPS
    zgaps = [8.0, 15.7] if a.quick else ZLIFT_GAPS
    design_gap = P.design_gap_mm()
    pen = M.PenMagnet()
    # ------------------------------------------------------------------ magnetics
    _log("force vs gap (recommended pair)", t0)
    rows = M.force_vs_gap(gaps)
    zrows = M.force_vs_gap(zgaps)
    diam = M.diametric_force_vs_gap(gaps)
    _log("tilt sensitivity and variants", t0)
    tilt = []
    for alt in ([50.0] if a.quick else [35.0, 50.0, 75.0]):
        pn = M.PenMagnet(alt_deg=alt)
        offs = M.offset_grid(16.0, 1.0)
        cap = M.lateral_capability(M.force_at_offsets(M.Head(), pn, design_gap, offs), offs)
        tilt.append({"alt_deg": alt, "lateral_isotropic_N": cap["lateral_isotropic_N"],
                     "lateral_best_direction_N": cap["lateral_best_direction_N"],
                     "normal_at_zero_lateral_N": cap["normal_at_zero_lateral_N"],
                     "zero_lateral_offset_mm": cap["zero_lateral_offset_mm"]})
    offs24 = M.offset_grid(24.0, 1.0)
    F24 = M.force_at_offsets(M.Head(), pen, design_gap, offs24)
    constrained = {"abs_Fz_le_0.3N": constrained_capability(F24, offs24, -0.3, 0.3),
                   "Fz_in_-0.8_to_0.05N": constrained_capability(F24, offs24, -0.8, 0.05),
                   "unconstrained": M.lateral_capability(F24, offs24)["lateral_isotropic_N"],
                   "gap_mm": design_gap, "label": "CALC: the controller may choose any head offset within +/-24 mm"}
    pen_vertical = M.PenMagnet(axis="vertical", height_mm=P.PEN["pen_magnet_h_mm"].value / 2 + 0.6)
    offs = M.offset_grid(16.0, 1.0)
    cap_v = M.lateral_capability(M.force_at_offsets(M.Head(), pen_vertical, design_gap, offs), offs)
    variants = {"pen_magnet_vertical_axis": {"height_mm": pen_vertical.height_mm,
                                             "lateral_isotropic_N": cap_v["lateral_isotropic_N"],
                                             "normal_at_zero_lateral_N": cap_v["normal_at_zero_lateral_N"],
                                             "note": "more force, but the fit can no longer see the pen azimuth (needed to place the ball)"}}
    _log("coil options", t0)
    coil_pcb = M.pcb_array_km(0.8)
    coil_pcb_design = M.pcb_array_km(design_gap)
    cross = M.em_cross_head_km(design_gap)
    # cuts for the figure
    ox = np.arange(-20.0, 20.01, 0.5)
    cut_x = (ox, M.force_at_offsets(M.Head(), pen, design_gap, np.stack([ox, np.zeros_like(ox)], 1)))
    cut_y = (ox, M.force_at_offsets(M.Head(), pen, design_gap, np.stack([np.zeros_like(ox), ox], 1)))
    # ------------------------------------------------------------------ hand
    _log("hand model", t0)
    defl = H.deflection_table()
    nudge = H.nudge_vs_steer(0.3)
    needed = H.forces_needed()
    fric = {"off": H.friction_deadband(0.25), "guiding": H.friction_deadband(1.0)}
    freqs = np.linspace(0.1, 10.0, 100)
    curves = {c.name: np.abs(H.compliance(c, freqs)) * 0.1 * 1e3 for c in H.cases()}
    # ------------------------------------------------------------------ stage
    _log("stage", t0)
    stage = ST.summary()
    # ------------------------------------------------------------------ sensing
    _log("sensing Monte Carlo", t0)
    sens = SE.localise_mc(n_draws=12 if a.quick else 40)
    sens_fast = SE.localise_mc(n_draws=12 if a.quick else 30, avg=1, seed=2)
    options = SE.options_table()
    # ------------------------------------------------------------------ control simulation
    _log("guidance simulation", t0)
    sim = {"tracing": [], "write_big": [], "reversal": [], "robustness": []}
    modes = ["off", "partial", "full"]
    hands = ["relaxed"] if a.quick else ["relaxed", "lightly_resisting", "hand_held_still"]
    examples = {}
    for mode in modes:
        for hc in hands:
            res = C.scenario_tracing(mode, hc)
            sim["tracing"].append({"mode": mode, "hand": hc, "nose": "locked",
                                   "ink_rms_mm": float(np.mean([r["metrics"]["ink_to_template_rms_mm"] for r in res])),
                                   "intended_rms_mm": float(np.mean([r["metrics"]["intended_to_template_rms_mm"] for r in res])),
                                   "force_rms_N": float(np.mean([r["metrics"]["force_rms_N"] for r in res])),
                                   "force_max_N": float(np.max([r["metrics"]["force_max_N"] for r in res]))})
            if hc == "relaxed":
                examples[("tracing", mode)] = res
        res = C.scenario_tracing(mode, "relaxed", nose="assist")
        sim["tracing"].append({"mode": mode, "hand": "relaxed", "nose": "assist",
                               "ink_rms_mm": float(np.mean([r["metrics"]["ink_to_template_rms_mm"] for r in res])),
                               "intended_rms_mm": float(np.mean([r["metrics"]["intended_to_template_rms_mm"] for r in res])),
                               "force_rms_N": float(np.mean([r["metrics"]["force_rms_N"] for r in res])),
                               "force_max_N": float(np.max([r["metrics"]["force_max_N"] for r in res]))})
    for mode in modes:
        for hc in (["relaxed"] if a.quick else ["relaxed", "lightly_resisting"]):
            r = C.scenario_write_big(mode, hc)
            sim["write_big"].append({"mode": mode, "hand": hc, **{k: v for k, v in r["metrics"].items()}})
            if hc == "relaxed":
                examples[("write_big", mode)] = r
    for mode, lt in (("off", False), ("partial", False), ("full", False), ("lead_through", True)):
        out = C.scenario_reversal(mode, lead_through=lt)
        sim["reversal"].append({"mode": mode, "stem_rms_mm": out[0]["metrics"]["ink_to_template_rms_mm"],
                                "bowl_rms_mm": out[1]["metrics"]["ink_to_template_rms_mm"],
                                "bowl_on_correct_side_fraction": out[1]["metrics"]["bowl_ink_on_correct_side_fraction"],
                                "force_max_N": out[1]["metrics"]["force_max_N"],
                                "yield_events": out[1]["metrics"]["yield_events"] if mode != "off" else 0,
                                "duration_s": out[1]["metrics"]["duration_s"]})
        examples[("reversal", mode)] = out
    if not a.quick:
        for label, kw in (("force gain -30 %", dict(force_gain_error=-0.3)),
                          ("stage twice as slow (lag 12.7 ms, delay 5 ms)", dict(stage_tau_s=2 / (2 * math.pi * 25.0), stage_delay_s=5e-3))):
            rng = np.random.default_rng(0)
            vals = []
            for stroke in C.tracing_word(8.0, 20.0, 150.0):
                tp = C.Path(stroke)
                intended = C.smooth_deviation(tp, 1.5, rng)
                r = C.simulate_stroke(tp, intended, C.Guidance(mode="full"), C.SimConfig(**kw))
                vals.append(r["metrics"]["ink_to_template_rms_mm"])
            sim["robustness"].append({"case": label, "mode": "full", "hand": "relaxed", "ink_rms_mm": float(np.mean(vals))})
    # ------------------------------------------------------------------ architectures
    _log("architecture table", t0)
    panto_a5 = A.pantograph_study()
    panto_a4 = A.pantograph_study(paper=P.A4_MM, L1=0.22, L2=0.30, d=0.08, y_off=0.08)
    arch = A.comparison(rows, diam, coil_pcb, cross, stage, sens, panto_a5, panto_a4)
    # ------------------------------------------------------------------ workspace map
    _log("workspace force map", t0)
    trav = L.travel()
    gx0, gy0, gw, gh = L.G["guided"]
    lev = P.PEN["pen_magnet_behind_ball_mm"].value
    no_margin = {"x": [gx0, gx0 + gw], "y": [gy0 - lev, gy0 + gh - lev]}   # head can only reach the magnet's own path
    X, Y, maps = workspace_map(design_gap, pen, trav, no_margin, L.G["paper"],
                               step=(21.0, 27.0) if a.quick else (10.0, 11.0))
    # ------------------------------------------------------------------ figures
    _log("figures", t0)
    a5_gap = round(P.STACK["paper_mm"].value + P.STACK["glass_mm_A5"].value + P.STACK["clearance_mm"].value, 2)
    figs = [FG.force_vs_gap(RESULTS, rows, diam, zrows, design_gaps=(("A4", design_gap), ("A5", a5_gap)),
                            zlift=(design_gap, design_gap + P.HEAD["zlift_travel_mm"].value)),
            FG.force_vs_position(RESULTS, X, Y, maps["design"], maps["no_margin"], L.G["paper"], trav,
                                 guided=L.G["guided"], gap_mm=design_gap),
            FG.force_cuts(RESULTS, cut_x, cut_y, gap_mm=design_gap),
            FG.hand_deflection(RESULTS, freqs, curves)]
    tr_off, tr_full = examples[("tracing", "off")], examples[("tracing", "full")]
    wb_off, wb_full = examples[("write_big", "off")], examples[("write_big", "full")]
    rv_full, rv_lead = examples[("reversal", "full")], examples[("reversal", "lead_through")]
    panels = [
        ("Tracing (8 mm letters)", [("template", "template", r["template"]) for r in tr_off] +
         [("writer's own path", "intended", r["intended"]) for r in tr_off] +
         [("ink, no guidance", "ink_off", r["ink"]) for r in tr_off] +
         [("ink, full guidance", "ink_guided", r["ink"]) for r in tr_full]),
        ("PD 'write big' loops (10 mm target)", [("template", "template", wb_off["template"]),
                                               ("writer's own path", "intended", wb_off["intended"]),
                                               ("ink, no guidance", "ink_off", wb_off["ink"]),
                                               ("ink, full guidance", "ink_guided", wb_full["ink"])]),
        ("Reversal: 'd' asked, 'b' intended", [("template 'd'", "template", r["template"]) for r in rv_full] +
         [("writer's own 'b'", "intended", r["intended"]) for r in rv_full] +
         [("ink, full guidance", "ink_guided", r["ink"]) for r in rv_full] +
         [("ink, lead-through (hand relaxed)", "ink_lead", r["ink"]) for r in rv_lead]),
    ]
    figs.append(FG.guidance_examples(RESULTS, panels))
    # ------------------------------------------------------------------ BOM, ledger rows, layout
    n_rows = B.write_evidence_rows(os.path.join(RESULTS, "evidence_rows.csv"))
    lay = L.layout_json(provenance.metadata("PROPOSED DESIGN (dimensioned concept; catalogue parts as envelopes; nothing built)",
                                            extra={"script": "board/layout.py", "doc": "docs/guidance_board.md"}))
    provenance.write_json(os.path.join(RESULTS, "layout.json"), lay)
    # ------------------------------------------------------------------ interface file
    g = {round(r["gap_mm"], 2): r for r in rows + zrows}
    d = g[round(design_gap, 2)]
    params = {
        "meta": meta,
        "status": "CALC + SIM + ASSUMPTION; supersedes board_params_provisional.json; every value is a hypothesis until EXP-G01...G05 (docs/guidance_board.md section 8)",
        "leading_option": "i-a: XY CoreXY stage under 3 mm glass carrying a permanent-magnet head (K&J D88-N52) on a Z-lift; pen add-on K&J D42-N52 in a keel under the Rev H fixed front sleeve",
        "changes_from_provisional": ["pen magnet moved from the nose to the fixed front sleeve (the nose actuator carries only 0.21 N continuously)",
                                     "pen magnet D42-N52 (0.75 g) instead of a 5 x 2.5 x 3 ring: much stronger coupling",
                                     "A4 glass 3 mm (design gap 3.7 mm) instead of 2 mm: hand loads up to ~70 N before the glass touches the head"],
        "pen_magnet": L.pen_magnet_info(),
        "design_gap_mm": {"A4": design_gap, "A5": round(P.STACK["paper_mm"].value + P.STACK["glass_mm_A5"].value + P.STACK["clearance_mm"].value, 2)},
        "max_lateral_force_N": {"at_design_gap_isotropic": d["lateral_isotropic_N"], "at_design_gap_best_direction": d["lateral_best_direction_N"],
                                "A5_gap_2p7mm_isotropic": g[2.7]["lateral_isotropic_N"], "label": "CALC magpylib (physical limit with the head fully raised)"},
        "software_force_cap_N": P.CONTROL["force_cap_N"].value,
        "continuous_lateral_force_N": {"value": P.CONTROL["force_cap_N"].value, "note": "permanent magnet: no thermal limit; the cap is a safety choice"},
        "guidance_level_by_zlift": [{"gap_mm": r["gap_mm"], "lateral_isotropic_N": r["lateral_isotropic_N"],
                                     "normal_pull_at_zero_lateral_N": -r["normal_at_zero_lateral_N"]} for r in rows + zrows if r["gap_mm"] >= design_gap - 1e-9],
        "normal_pull_N": {"operating": "about 2.2-2.5 x the lateral capability set by the Z-lift (e.g. ~1.0 N while a 0.4 N capability is selected); ~0.25 N with the head retracted",
                          "at_design_gap_fully_raised": -d["normal_at_zero_lateral_N"],
                          "bounded_normal_option": constrained, "label": "CALC"},
        "offset_to_force_slope_N_per_mm": {"at_design_gap": d["slope_at_zero_N_per_mm"],
                                           "at_0.4N_capability": g[8.0]["slope_at_zero_N_per_mm"] if 8.0 in g else None},
        "force_bandwidth_Hz": {"value": round(stage["position_bandwidth_Hz"], 1), "first_belt_mode_Hz": round(min(stage["mode_x_Hz"], stage["mode_y_Hz"]), 1),
                               "label": "CALC (belt stiffness ASSUMPTION)"},
        "latency_ms": stage["latency"],
        "position_sensing": {"method": "8 x TMAG5170A2 Hall ring on the carriage + stage steps", "rate_Hz": 1000,
                             "ball_noise_rms_mm": sens["summary"]["ball_noise_rms_mm_median"],
                             "ball_error_total_rms_mm_max": sens["summary"]["ball_total_rms_mm_max"],
                             "stage_position_error_mm": [0.1, 0.2], "label": "CALC Monte Carlo (AMF-95 noise) + ASSUMPTION stage error"},
        "workspace_mm": {"A4": list(P.A4_MM), "A5": list(P.A5_MM), "carriage_travel": trav, "board_outer_mm": list(L.G["board"])},
        "force_vs_gap_table": [{"gap_mm": r["gap_mm"], "lateral_isotropic_N": r["lateral_isotropic_N"],
                                "lateral_best_direction_N": r["lateral_best_direction_N"],
                                "normal_pull_at_zero_lateral_N": -r["normal_at_zero_lateral_N"],
                                "slope_at_zero_N_per_mm": r["slope_at_zero_N_per_mm"]} for r in rows],
        "suggested_simulation_model": {
            "force": "F_board = cap(F_cmd, 0.40 N) -> dead time 1.5 ms -> first-order lag 6.4 ms (25 Hz); gain error +/-10 % (ASSUMPTION)",
            "acts_on": "the pen handle (front-sleeve keel), 16.5 mm behind the ball; not on the nose",
            "normal_pull": "constant ~1.0 N while guiding (capability ~0.4 N), 0.25 N when off; adds skid friction mu 0.15",
            "sensing": "ball position noise ~0.2 mm RMS at 1 kHz, bias up to 0.4 mm",
            "hand": "HAP-26 two-stage (k1 575, b1 1.3, M 0.21, k2 170, b2 11)"},
        "sim_headlines": {"tracing_full_vs_off_ink_rms_mm": [next(r["ink_rms_mm"] for r in sim["tracing"] if r["mode"] == "off" and r["hand"] == "relaxed" and r["nose"] == "locked"),
                                                            next(r["ink_rms_mm"] for r in sim["tracing"] if r["mode"] == "full" and r["hand"] == "relaxed" and r["nose"] == "locked")],
                          "label": "SIM"},
    }
    provenance.write_json(os.path.join(RESULTS, "board_params.json"), params)
    # ------------------------------------------------------------------ everything
    out = {"meta": meta, "params": P.all_tables(),
           "magnetics": {"force_vs_gap": rows, "zlift_levels": zrows, "diametric_variant": diam, "tilt": tilt,
                         "constrained": constrained, "variants": variants, "pcb_array": [coil_pcb, coil_pcb_design],
                         "em_cross_head_air_core": cross,
                         "langerak_em_km_N_per_sqrtW": {"value": 0.488 / math.sqrt(11.0), "label": "CALC from LIT HAP-16"}},
           "hand": {"cases": H.as_dicts(), "deflection_per_0p1N": defl, "nudge_vs_steer_0p3N": nudge,
                    "forces_needed": needed, "friction": fric},
           "stage": stage, "sensing": {"monte_carlo_8x_avg": sens, "monte_carlo_no_avg": sens_fast, "options": options},
           "simulation": sim, "architectures": arch,
           "pantograph": {"A5": panto_a5, "A4": panto_a4},
           "bom": B.BOM, "custom_parts": B.CUSTOM, "evidence_rows": n_rows,
           "workspace": {"travel": trav, "paper": L.G["paper"], "guided_area": L.G["guided"],
                         "min_isotropic_N_on_guided_area_design": float(np.nanmin(np.where(_in_guided(X, Y), maps["design"], np.nan))),
                         "min_isotropic_N_on_guided_area_no_margin_travel": float(np.nanmin(np.where(_in_guided(X, Y), maps["no_margin"], np.nan))),
                         "min_isotropic_N_on_page_design": float(np.nanmin(maps["design"])),
                         "min_isotropic_N_on_page_no_margin_travel": float(np.nanmin(maps["no_margin"])),
                         "median_isotropic_N_design": float(np.nanmedian(maps["design"]))},
           "figures": [os.path.relpath(p, REPO_ROOT) for p in figs]}
    provenance.write_json(os.path.join(RESULTS, "board.json"), out)
    _log("results written", t0)
    if not a.no_cad:
        _log("CAD", t0)
        cad = os.path.join(REPO_ROOT, "mechanics", "cad", "guidance_board.py")
        r = subprocess.run([sys.executable, cad], cwd=REPO_ROOT)
        if r.returncode != 0:
            print("CAD script failed", file=sys.stderr)
            return r.returncode
    _log("done", t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
