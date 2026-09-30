"""Part (a): tremor on real recorded inputs, cancelled by moving the page (SIMULATION, model HW1 + the platen stage).

PLAN (fixed here before any platen case ran; TUNING SPLIT ONLY, because study R's test split is spent):
  Cases   study E's selection set, exactly as studies E and F built it (realtrack.cases, readable.common): tuning
          notes 0-9 of study R's tuning split (5 tuning writers x 2 notes, tuning texts), PD and ET recordings of tuning
          patients of the note's fold, at the severe class (1.72 mm at the tip, DEC-055's condition; words read) and the
          moderate class (0.24 mm; tip tremor only), and the 10 notes without tremor (clean-writing change).
  Pen     the ordinary 12 g pen of HW1 (rigid), held by HW1's hand; the page moves under it (platen/plant.py, the
          'hw1' writer convention of every earlier study, so the pen itself is exactly HW1's ordinary pen).
  Stage   the proposed fine stage (design.sim_stage('fine_A5'): 0.59 kg moving, +-5 mm, 40 Hz follower, 250 Hz inner
          loop on 0.25 um encoders, 20 N cap); the coarse stage holds still in free writing.
  Rows    platen off           the ordinary pen on a fixed page (the platen held: identical ink; study F's reading of
                               the same case is reused and its tip tremor reproduced)
          P_oracle             perfect knowledge: the page follows the true tip tremor of the fixed-page run
                               (d = tip(tremor) - tip(no tremor)), previewed by the stage's group delay (R's oracle
                               convention)
          P_a_r2               perfect knowledge scaled to leave study F's frozen +2-words residual (0.65 mm; F's rule
                               rho = target / the case's fixed-page tip tremor): does the platen keep an estimator's
                               result? (tip tremor only)
          P_E_chosen           study E's frozen design (ai2's causal TCN + soft size gate) on the ordinary pen's own
                               sensor streams (IMU + E's ideal page-position stream: the platen's absolute tip sensor)
          P_E_net              study E's real-data TCN + soft gate (information row of E), same streams
          P_cam_sep            perfect separation with real sensing: the camera-class tip sensor (250 Hz, 6 ms, 15 um)
                               and the tuned AR predictor, told the clean tip path (the sensing limit, no estimator)
          N{6,15,10}_E_*       the handheld nib: the Rev J nose at its full +-6 mm and with its usable travel cut to
                               +-1.5 and +-1.0 mm (study F's limited_pen), driven by the same two E designs on E's own
                               cached Rev J streams (ideal page sensor): the estimator on the nib at F's reach
          F rows               study F's perfect-knowledge runs of the same cases at +-6, +-3, +-2, +-1.5, +-1.0 mm
                               (readable/build/cache/reach and e13; read at +-6, +-1.5, +-1.0 mm)
  Read    by study R's literal reader (its chosen OCR instrument): P_oracle, P_E_chosen, P_E_net, P_cam_sep, N15_E_chosen,
          N10_E_chosen at the severe class; every other row by tip tremor and study F's frozen curve (CALC).
  Measures study R's (realdata.hw1.measures): words of 10, tip tremor (sqrt(2) x RMS of the major axis of ink -
          intended in contact, f0 +- 2 Hz), ink error, coverage; E's broadband residual; the stage's travel, force,
          time at the travel limit and copper power; clean-writing change (RMS over contact of the ink against the
          fixed-page ink, ai2's definition).  Writer bootstrap (R's): 2000 resamples of writers.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np

from . import common as CM

PLATEN_ROWS = ("P_oracle", "P_a_r2", "P_E_chosen", "P_E_net", "P_cam_sep")
NIB_ROWS = ("N6_E_chosen", "N15_E_chosen", "N10_E_chosen", "N6_E_net", "N15_E_net", "N10_E_net")
READ_ROWS = {"P_oracle", "P_E_chosen", "P_E_net", "P_cam_sep", "N15_E_chosen", "N10_E_chosen"}
F_ROWS = {"F6_oracle": ("e13", "E13a_0.00"), "F3_oracle": ("reach", "3|oracle"), "F2_oracle": ("reach", "2|oracle"),
          "F15_oracle": ("reach", "1.5|oracle"), "F10_oracle": ("reach", "1|oracle"),
          "F6_a_r2": ("reach", "6|a_r2"), "F15_a_r2": ("reach", "1.5|a_r2"), "F10_a_r2": ("reach", "1|a_r2"),
          "none_F": ("e13", "none")}
NIB_REACH = {"N6": 6.0, "N15": 1.5, "N10": 1.0}
CAMERA = {"cam_hz": 250.0, "cam_latency": 6e-3, "noise": 15e-6}
STAGE_VARIANT = "fine_A5"
LABELS = {
    "none": "Platen off: ordinary pen on a fixed page",
    "P_oracle": "Platen +-5 mm, perfect knowledge",
    "P_a_r2": "Platen +-5 mm, perfect knowledge scaled to F's +2 residual",
    "P_E_chosen": "Platen +-5 mm, study E's frozen design (ai2 TCN + gate)",
    "P_E_net": "Platen +-5 mm, study E's real-data TCN + gate (info)",
    "P_cam_sep": "Platen +-5 mm, perfect separation, camera sensing (250 Hz, 6 ms, 15 um)",
    "N6_E_chosen": "Nib (Rev J nose) +-6 mm, E's frozen design", "N15_E_chosen": "Nib +-1.5 mm, E's frozen design",
    "N10_E_chosen": "Nib +-1.0 mm, E's frozen design", "N6_E_net": "Nib +-6 mm, E's real-data TCN",
    "N15_E_net": "Nib +-1.5 mm, E's real-data TCN", "N10_E_net": "Nib +-1.0 mm, E's real-data TCN",
    "F6_oracle": "Nib (Rev J nose) +-6 mm, perfect knowledge (study F)",
    "F3_oracle": "Nib +-3 mm, perfect knowledge (study F)", "F2_oracle": "Nib +-2 mm, perfect knowledge (study F)",
    "F15_oracle": "Nib +-1.5 mm, perfect knowledge (study F)", "F10_oracle": "Nib +-1.0 mm, perfect knowledge (study F)",
    "F6_a_r2": "Nib +-6 mm, perfect knowledge scaled to the +2 residual (study F)",
    "F15_a_r2": "Nib +-1.5 mm, scaled to the +2 residual (study F)",
    "F10_a_r2": "Nib +-1.0 mm, scaled to the +2 residual (study F)",
}


def plan(quick: bool) -> Dict:
    return {"notes": [0] if quick else list(range(10)), "kinds": ["PD"] if quick else ["PD", "ET"],
            "classes": ["severe"] if quick else ["severe", "moderate"], "clean": not quick,
            "read": sorted(READ_ROWS) if not quick else ["P_oracle"], "stage": STAGE_VARIANT, "camera": CAMERA,
            "platen_rows": list(PLATEN_ROWS), "nib_rows": [] if quick else list(NIB_ROWS),
            "split": "tuning (study R's tuning split, study E's selection set); the test split is spent"}


def designs() -> Dict[str, Dict]:
    fr = CM.jload(CM.E_FROZEN)
    return {"E_chosen": fr["chosen"], "E_net": fr["info"]["net"]}


def predictor(quick: bool) -> Dict:
    """The camera predictor for free writing (tremor only), fitted on the tuning split (predictor.py)."""
    from . import design as D
    from . import predictor as PRD
    g = D.sim_stage(STAGE_VARIANT).group_delay()
    key = f"free_{CAMERA['cam_hz']:g}Hz_{CAMERA['cam_latency'] * 1e3:g}ms_{CAMERA['noise'] * 1e6:g}um_g{g * 1e3:.2f}"
    return PRD.load_or_fit(key, lambda: PRD.training_signals(quick), quick=quick, cam_hz=CAMERA["cam_hz"],
                           cam_latency=CAMERA["cam_latency"], noise=CAMERA["noise"], g=g, with_drift=False)


def stage_stats(pr, con: np.ndarray) -> Dict:
    """Travel, force, limit and power of the fine stage over contact (CALC on SIM signals)."""
    from . import design as D
    rel = np.hypot(pr["fx"], pr["fy"]) * 1e3
    F = np.hypot(pr["Ffx"], pr["Ffy"])
    Fx = np.sqrt(np.mean(pr["Ffx"] ** 2)); Fy = np.sqrt(np.mean(pr["Ffy"] ** 2))
    lim = pr.info["stage"]["q_lim_f"] * 1e3
    m = con if con.any() else np.ones_like(con, bool)
    return {"travel_p50_mm": float(np.percentile(rel[m], 50)), "travel_p99_mm": float(np.percentile(rel[m], 99)),
            "travel_max_mm": float(rel.max()), "at_limit_share": float(np.mean(rel[m] >= 0.95 * lim)),
            "force_rms_N": float(np.sqrt(np.mean(F ** 2))), "force_p99_N": float(np.percentile(F, 99)),
            "force_max_N": float(F.max()), "sat_share": float(np.mean(pr["satf"] > 0.5)),
            "stop_share": float(np.mean(pr["stop"] > 0.5)),
            "copper_W_per_axis_rms": float((D.vca_power(Fx) + D.vca_power(Fy)) / 2.0)}


def _oracle_ticks(r, rc, n_ticks: int, Ts: float, g: float) -> np.ndarray:
    n = min(len(r.t), len(rc.t))
    d = r.ink[:n] - rc.ink[:n]
    tt = np.arange(n_ticks) * Ts + g
    return np.column_stack([np.interp(tt, r.t[:n], d[:, 0]), np.interp(tt, r.t[:n], d[:, 1])])


def _clean_ticks(rc, n_ticks: int, Ts: float) -> np.ndarray:
    tt = np.arange(n_ticks) * Ts
    return np.column_stack([np.interp(tt, rc.t, rc.ink[:, 0]), np.interp(tt, rc.t, rc.ink[:, 1])])


def _platen(note, scn, dt, stage, **kw):
    from handwriting import params as PR
    from . import plant as PP
    return PP.run(scn.pref, scn.vref, scn.down, dt, hand=note.hand, writing=PR.Writing(), pen_mass=CM.PEN_MASS_HW1,
                  stage=stage, **kw)


def extrapolate(d: np.ndarray, shift_s: float, Ts: float = 5e-4, span_ticks: int = 4) -> np.ndarray:
    """Causal linear extrapolation of a per-tick estimate by shift_s, from its change over the last span_ticks."""
    d = np.asarray(d, float)
    if abs(shift_s) < 1e-9:
        return np.ascontiguousarray(d)
    prev = np.vstack([np.repeat(d[:1], span_ticks, axis=0), d[:-span_ticks]])
    return np.ascontiguousarray(d + (shift_s / (span_ticks * Ts)) * (d - prev))


def e_command(design: Dict, st, caselike, g: float) -> np.ndarray:
    """Study E's design on the pen's streams, predicted to the platen's command lag g.  E's estimators predict to
    the Rev J servo's group delay (3.39 ms); ai2's TCN takes the extra horizon through its own causal shift (E's
    delay-study mechanism); the real-data TCN, which has a fixed horizon, is extrapolated causally by the difference."""
    from realtrack import estimators as E
    d_hat, _ = E.estimate(design, st, case=caselike, sensor="ideal", horizon=g)
    if design["family"] == "net":
        d_hat = extrapolate(d_hat, g - E.servo_delay())
    return np.ascontiguousarray(d_hat)


def false_correction_um(res_ink, held_ink, contact) -> float:
    """ai2's definition: RMS over contact of the ink against the fixed-page (held) ink, um."""
    n = min(len(res_ink), len(held_ink), len(contact))
    m = contact[:n] > 0.5
    if not m.any():
        return float("nan")
    e = res_ink[:n][m] - held_ink[:n][m]
    return float(np.sqrt(np.mean(np.sum(e ** 2, axis=1))) * 1e6)


def run_note(i: int, quick: bool = False) -> List[str]:
    """One tuning note: both kinds at each class (every row), then the clean note (clean-writing change)."""
    from handwriting import plant as PL
    from aiprior import core as CO
    from readable import common as RC
    from readable import reach as FR
    from realtrack import cases as C
    from realtrack import estimators as E
    from . import design as D
    from . import plant as PP
    P = plan(quick)
    out_dir = CM.cache_dir(quick, "tremor")
    stage = D.sim_stage(STAGE_VARIANT)
    g = stage.group_delay()
    des = designs()
    pred = predictor(quick)
    note = None
    rc = None
    done = []
    todo = [(kind, cls) for cls in P["classes"] for kind in P["kinds"]
            if not (out_dir / f"tune_n{i}_{kind}_{cls}.json").exists()]
    for kind, cls in todo:
        t1 = time.time()
        if note is None:
            note = RC.tuning_note(i)
            rc = PL.run(note.scenario("none", None), note.pens["none"], note.hand)
        spec = RC.tuning_spec(i, kind, cls)
        dr = RC.tuning_tremor(note, spec)
        f0 = float(dr.meta["f0"])
        scn_n = note.scenario("none", dr.d)
        r_n = PL.run(scn_n, note.pens["none"], note.hand)                     # platen off (= page held)
        Ts = 5e-4
        n_ticks = int(np.ceil(len(scn_n.t) / 20)) + 1
        read_sev = cls == "severe"
        dev: Dict[str, Dict] = {}
        dev["none"] = RC.measures(note.written, r_n, scn_n, note.pens["none"], f0, read=False)
        held_tip = dev["none"]["tip_tremor_mm"]
        # the page commands
        cmds = {"P_oracle": ("ext", _oracle_ticks(r_n, rc, n_ticks, Ts, g), {})}
        rho = float(np.clip(CM.f_curve()["r_plus2_mm"] / held_tip, 0.02, 1.0))
        cmds["P_a_r2"] = ("ext", (1.0 - rho) * cmds["P_oracle"][1], {"remain": rho})
        s_seed = CM.h(spec["id"], "platen-streams") % (2 ** 31)
        st = CO.streams_for(r_n, scn_n, note.pens["none"], note.trk, s_seed)       # the pen's IMU + ideal position
        caselike = RC.CaseLike(spec, None)
        for dk, key in (("E_chosen", "P_E_chosen"), ("E_net", "P_E_net")):
            cmds[key] = ("ext", e_command(des[dk], st, caselike, g), {"design": dk, "horizon_s": g})
        cmds["P_cam_sep"] = ("cam", None, {"camera": CAMERA, "predictor_order": pred["order"]})
        for key, (kindc, cmd, prm) in cmds.items():
            if key not in P["platen_rows"]:
                continue
            if kindc == "ext":
                pr = _platen(note, scn_n, scn_n.dt, stage, cmd_ext=cmd)
            else:
                ctl = PP.Control(mode=1, cam_hz=CAMERA["cam_hz"], cam_latency=CAMERA["cam_latency"],
                                 cam_noise=CAMERA["noise"], ar_coef=np.asarray(pred["coef"]), horizon=g)
                pr = _platen(note, scn_n, scn_n.dt, stage, ctl=ctl, trem=dr.d, tgt_tick=_clean_ticks(rc, n_ticks, Ts),
                             seed=CM.h(spec["id"], "cam") % (2 ** 31))
            res = pr.as_hw1()
            m = RC.measures(note.written, res, scn_n, note.pens["none"], f0,
                            read=(read_sev and key in P["read"]))
            m.update(stage_stats(pr, pr.contact > 0.5))
            m["param"] = prm
            dev[key] = m
            del pr, res
        # the nib (Rev J nose, E's own cached streams) at +-6 / +-1.5 / +-1.0 mm with the same E designs
        if P["nib_rows"]:
            tc = RC.TuneCase(note, spec)
            ecase = C.load_case(spec)
            st_j = ecase.streams("ideal")
            for dk in ("E_chosen", "E_net"):
                d_hat, _ = E.estimate(des[dk], st_j, case=RC.CaseLike(spec, ecase.dh_revh("ideal")), sensor="ideal")
                q = -np.ascontiguousarray(d_hat)
                for tag, reach in NIB_REACH.items():
                    key = f"{tag}_{dk}"
                    if key not in P["nib_rows"]:
                        continue
                    pen = FR.limited_pen(tc.pen, reach)
                    res = PL.run(tc.scn, pen, note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
                    m = RC.measures(note.written, res, tc.scn, pen, f0, read=(read_sev and key in P["read"]))
                    m["param"] = {"reach_mm": reach, "design": dk}
                    dev[key] = m
                    del res
            del tc, ecase, st_j
        CM.jdump(out_dir / f"tune_n{i}_{kind}_{cls}.json",
                 {"set": "real", "split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                  "class": cls, "case_id": spec["id"], "tremor": {k: dr.meta[k] for k in
                                                                 ("rid", "amp_mm", "f0", "subject", "source", "kind")},
                  "held_tip_tremor_mm": held_tip, "stage_group_delay_s": g, "devices": dev,
                  "_elapsed_s": time.time() - t1})
        CM.log(f"[tremor] n{i} {kind} {cls}: " + ", ".join(
            f"{k} {v['tip_tremor_mm']:.2f}" + (f"/{v['words_read']}w" if 'words_read' in v else "")
            for k, v in dev.items()) + f" ({time.time() - t1:.0f} s)")
        done.append(f"tune_n{i}_{kind}_{cls}")
    # clean note: what the estimators on the platen do to writing without tremor
    pc = out_dir / f"tune_n{i}_clean.json"
    if P["clean"] and not pc.exists():
        t1 = time.time()
        if note is None:
            note = RC.tuning_note(i)
            rc = PL.run(note.scenario("none", None), note.pens["none"], note.hand)
        spec = RC.tuning_spec(i, None, "clean")
        scn_c = note.scenario("none", None)
        held = _platen(note, scn_c, scn_c.dt, stage)                         # page held (no command)
        s_seed = CM.h(spec["id"], "platen-streams") % (2 ** 31)
        st = CO.streams_for(rc, scn_c, note.pens["none"], note.trk, s_seed)
        dev = {}
        for dk, key in (("E_chosen", "P_E_chosen"), ("E_net", "P_E_net")):
            pr = _platen(note, scn_c, scn_c.dt, stage, cmd_ext=e_command(des[dk], st, RC.CaseLike(spec, None), g))
            dev[key] = {"false_correction_um": false_correction_um(pr.ink, held.ink, pr.contact),
                        "page_rms_um": float(np.sqrt(np.mean(np.sum(pr.page ** 2, axis=1))) * 1e6)}
        # the nib (Rev J, +-6 mm) with the same designs on E's cached clean streams, for comparison
        if P["nib_rows"]:
            tc_note = note
            ecase = C.load_case(spec)
            st_j = ecase.streams("ideal")
            neutral = tc_note.clean["revJ"]
            scn_j = tc_note.scenario("revJ", None)
            for dk in ("E_chosen", "E_net"):
                d_hat, _ = E.estimate(des[dk], st_j, case=RC.CaseLike(spec, ecase.dh_revh("ideal")), sensor="ideal")
                res = PL.run(scn_j, tc_note.pens["revJ"], tc_note.hand,
                             ctl=PL.Controls(qext=np.ascontiguousarray(-d_hat)))
                dev[f"N6_{dk}"] = {"false_correction_um": false_correction_um(res.ink, neutral.ink, res.contact)}
        CM.jdump(pc, {"set": "clean", "split": "tuning", "writer": note.written.real["writer"], "note": i,
                      "case_id": spec["id"], "devices": dev, "_elapsed_s": time.time() - t1})
        CM.log(f"[tremor] n{i} clean: " + ", ".join(f"{k} {v['false_correction_um']:.1f} um" for k, v in dev.items()))
        done.append(f"tune_n{i}_clean")
    return done


# ------------------------------------------------------------------ aggregation
def load(quick: bool) -> List[Dict]:
    d = CM.cache_dir(quick, "tremor")
    out = []
    P = plan(quick)
    for i in P["notes"]:
        for cls in P["classes"]:
            for kind in P["kinds"]:
                c = CM.jload(d / f"tune_n{i}_{kind}_{cls}.json")
                if c is None:
                    continue
                # study F's rows of the same case (read-only caches)
                for key, (sub, fk) in F_ROWS.items():
                    fc = CM.jload(CM.F_CACHE / sub / f"tune_n{i}_{kind}_{cls}.json")
                    if fc and fk in (fc.get("devices") or {}):
                        c["devices"][key] = fc["devices"][fk]
                out.append(c)
    return out


def load_clean(quick: bool) -> List[Dict]:
    d = CM.cache_dir(quick, "tremor")
    return [c for c in (CM.jload(d / f"tune_n{i}_clean.json") for i in plan(quick)["notes"]) if c]


def aggregate(quick: bool) -> Dict:
    cases = load(quick)
    clean = load_clean(quick)
    fc = CM.f_curve()
    rows = ["none"] + list(PLATEN_ROWS) + list(NIB_ROWS) + [k for k in F_ROWS if k != "none_F"]
    out = {"label": "SIMULATION (model HW1 + the platen stage) with real recorded inputs, TUNING SPLIT (study E's "
                    "selection set); words read by study R's literal reader where read, else via study F's frozen "
                    "curve (CALC); 95 % writer-bootstrap intervals", "plan": plan(quick), "labels": LABELS,
           "n_cases": len(cases), "by_class": {}}
    for cls in ("severe", "moderate"):
        for kind in ("all", "PD", "ET"):
            sel = [c for c in cases if c["class"] == cls and (kind == "all" or c["kind"] == kind)]
            if not sel:
                continue
            tab = {}
            for dev in rows:
                if not any(dev in c["devices"] for c in sel):
                    continue
                e = {"n_cases": sum(1 for c in sel if dev in c["devices"])}
                e["tip_tremor_mm"] = CM.boot(CM.per_writer(sel, lambda c: (c["devices"].get(dev) or {}).get("tip_tremor_mm")))
                e["ratio_to_ordinary"] = CM.boot(CM.per_writer(sel, lambda c: (
                    (c["devices"].get(dev) or {}).get("tip_tremor_mm", np.nan) / c["devices"]["none"]["tip_tremor_mm"])
                    if dev in c["devices"] else None))
                e["words_via_curve"] = CM.boot(CM.per_writer(sel, lambda c: CM.words_via_curve(
                    (c["devices"].get(dev) or {}).get("tip_tremor_mm"), fc["p"]) if dev in c["devices"] else None))
                wr = CM.per_writer(sel, lambda c: CM.of10(c["devices"].get(dev)) if (
                    (c["devices"].get(dev) or {}).get("words_total")) else None)
                if dev == "none":
                    wr = CM.per_writer(sel, lambda c: CM.of10(c["devices"].get("none_F")) if c["devices"].get("none_F") else None)
                if wr:
                    e["words_read"] = CM.boot(wr)
                    e["gain_read"] = CM.boot(CM.per_writer(sel, lambda c: (
                        CM.of10(c["devices"].get(dev) if dev != "none" else c["devices"].get("none_F"))
                        - CM.of10(c["devices"].get("none_F"))) if (c["devices"].get("none_F") and (
                            dev == "none" or (c["devices"].get(dev) or {}).get("words_total"))) else None))
                for m in ("at_limit_share", "travel_p99_mm", "force_rms_N", "force_p99_N", "copper_W_per_axis_rms",
                          "bb_um", "coverage", "at_travel_limit"):
                    b = CM.per_writer(sel, lambda c, m=m: (c["devices"].get(dev) or {}).get(m))
                    if b:
                        e[m] = CM.boot(b)
                tab[dev] = e
            out["by_class"][f"{kind}/{cls}"] = tab
    # clean-writing change on the tuning notes without tremor
    cl = {}
    for dev in ("P_E_chosen", "P_E_net", "N6_E_chosen", "N6_E_net"):
        vals = {c["writer"]: [] for c in clean}
        for c in clean:
            v = (c["devices"].get(dev) or {}).get("false_correction_um")
            if v is not None:
                vals[c["writer"]].append(v)
        pw = {w: float(np.mean(v)) for w, v in vals.items() if v}
        if pw:
            allv = [v for c in clean for v in [(c["devices"].get(dev) or {}).get("false_correction_um")] if v is not None]
            cl[dev] = {"mean_over_writers": CM.boot(pw), "worst_note_um": float(np.max(allv)),
                       "notes_over_50um": int(np.sum(np.array(allv) > 50.0)), "n_notes": len(allv)}
    out["clean"] = cl
    # reproduction check: the platen-off tip tremor against study F's ordinary pen on the same case
    diffs = [abs(c["devices"]["none"]["tip_tremor_mm"] - c["devices"]["none_F"]["tip_tremor_mm"])
             for c in cases if c["devices"].get("none_F")]
    out["repro_ordinary_vs_F_max_abs_mm"] = float(max(diffs)) if diffs else None
    return out


BANDS_HZ = ((0.0, 3.0), (3.0, 12.0), (12.0, 40.0), (40.0, 100.0), (100.0, 250.0), (250.0, 1000.0))


def command_bands(quick: bool = False) -> Dict:
    """Diagnostic (CALC on SIM signals): band RMS of the page commands of one severe case (note 0, ET; PD with
    --quick): perfect knowledge, study E's frozen design predicted to the platen's lag (part a's command), and the same
    design at its own horizon (the Rev J servo's).  Explains the fine stage's effort with E's commands."""
    from scipy.signal import welch
    from aiprior import core as CO
    from handwriting import plant as PL
    from readable import common as RC
    from realtrack import estimators as E
    from . import design as D
    i, kind = 0, ("PD" if quick else "ET")
    note = RC.tuning_note(i)
    spec = RC.tuning_spec(i, kind, "severe")
    dr = RC.tuning_tremor(note, spec)
    scn_n = note.scenario("none", dr.d)
    r_n = PL.run(scn_n, note.pens["none"], note.hand)
    rc = PL.run(note.scenario("none", None), note.pens["none"], note.hand)
    g = D.sim_stage(STAGE_VARIANT).group_delay()
    n_ticks = int(np.ceil(len(scn_n.t) / 20)) + 1
    st = CO.streams_for(r_n, scn_n, note.pens["none"], note.trk, CM.h(spec["id"], "platen-streams") % (2 ** 31))
    des = designs()["E_chosen"]
    own, _ = E.estimate(des, st, case=RC.CaseLike(spec, None), sensor="ideal", horizon=E.servo_delay())
    cmds = {"perfect_knowledge": _oracle_ticks(r_n, rc, n_ticks, 5e-4, g),
            "E_chosen_platen_horizon": e_command(des, st, RC.CaseLike(spec, None), g),
            "E_chosen_own_horizon": np.asarray(own)}
    out = {"label": "CALC (Welch spectra) on SIM command signals; one case", "case": spec["id"],
           "bands_hz": [list(b) for b in BANDS_HZ], "rms_mm": {}}
    for name, d in cmds.items():
        d = np.asarray(d, float)[: n_ticks - 10]
        f, P = welch(d, fs=2000.0, nperseg=4096, axis=0)
        Pt, df = P.sum(axis=1), float(f[1] - f[0])
        out["rms_mm"][name] = {f"{lo:g}-{hi:g}": float(np.sqrt(Pt[(f >= lo) & (f < hi)].sum() * df) * 1e3)
                               for lo, hi in BANDS_HZ}
        out["rms_mm"][name]["total"] = float(np.sqrt(np.mean(np.sum(d ** 2, axis=1))) * 1e3)
        hi = [k for k in out["rms_mm"][name] if k not in ("total", "0-3", "3-12")]
        out["rms_mm"][name]["above_12"] = float(np.sqrt(sum(out["rms_mm"][name][k] ** 2 for k in hi)))
    return out
