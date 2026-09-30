"""Part (c): sensitivity of the platen to page slip, pen tilt, sensing delay and noise, stage bandwidth and travel,
friction convention and pen mass; and of accepted writing to the lift time, sensing noise and the hand.

SIMULATION (model HW1 + the platen stage) with real recorded inputs, TUNING SPLIT ONLY (study E's selection set,
severe class, PD and ET, 20 cases).  Every variant changes one thing from the baseline of part (a): the fine stage
(40 Hz, +-5 mm, 0.59 kg), the camera-class sensor (250 Hz, 6 ms, 15 um) with its tuned predictor (refitted on the
tuning split for every sensor timing or noise and every stage bandwidth, because the predictor must cover that lag),
HW1's writer convention, a rigid sheet, the ordinary 12 g pen.  Two drives per variant where it matters:
  oracle   perfect knowledge of the fixed-page tip tremor (previewed by the stage's group delay): the mechanism alone
  camera   perfect separation with the camera-class sensor and its predictor (P_cam_sep of part a): mechanism + sensing
Measure: study R's tip tremor (sqrt(2) x RMS of the major axis, f0 +- 2 Hz, contact), mapped to words of 10 through
study F's frozen tuning curve (CALCULATION); writer-bootstrap intervals.

Estimator command smoothing: ai2's TCN outputs at 500 Hz; extrapolated over the platen's extra 2.7 ms of lag they
form a 2 ms sawtooth that the fine stage follows with large forces (part a's force budget).  The variant
'e_command_smoothed' runs study E's frozen design twice on the same streams: as in part (a) ('E_chosen_raw', which
reproduces part a's row) and with a causal 4-tick (2 ms) moving average after predicting 0.75 ms further (the average's
delay), which turns the sawtooth into a continuous line ('E_chosen_smooth').

Page slip under the hand ('held' drive: the page held still, to separate the sheet's own creep from the page motion;
note that single-state friction models such as LuGre creep under oscillating loads below breakaway, a known nonphysical
drift, Dupont et al. 2002): the sheet becomes a 3 g body held by a LuGre hold-down (normal force N_hold, mu 0.4) and,
where the hand rests on the paper (no palm rest), loaded by the hand's skin friction (N_hand, mu 0.5), whose reaction
also drags the hand.  Pen tilt: the camera marker sits above the ball, so the pen's rotation reads as motion: the
marker error is kappa x the imposed hand tremor (kappa = marker height / grip distance x the share of the finger
tremor that rotates the pen; ASSUMPTION values 0.05-0.2).
"""
from __future__ import annotations

import dataclasses
import time
from typing import Dict, List, Optional

import numpy as np

from . import common as CM

BASE_CAM = {"cam_hz": 250.0, "cam_latency": 6e-3, "noise": 15e-6}
LATENCIES_MS = (2.0, 4.0, 10.0, 15.0, 25.0)
NOISES_UM = (0.0, 5.0, 30.0, 60.0)
RATES_HZ = (125.0, 500.0)
BANDWIDTHS_HZ = (15.0, 25.0, 80.0)
TRAVELS_MM = (3.0, 4.0, 6.0)
KAPPAS = (0.05, 0.1, 0.2)
SLIPS = {   # name: (N_hold N, N_hand N)
    "hand_on_paper_vacuum": (7.5, 2.0),
    "hand_on_paper_clip_only": (0.5, 2.0),
    "palm_rest_clip_only": (0.5, 0.0),
    "palm_rest_vacuum": (7.5, 0.0),
}
PEN_MASSES_G = (20.0,)
FIRM_HAND = {"K_grip": 1150.0, "k_arm": 2000.0, "b_arm": 20.0}   # part (b)'s firm grip on the palm rest (ASSUMPTION)


def variants(quick: bool) -> List[Dict]:
    """Every variant (name, what changes, which drives)."""
    v = [{"name": "baseline", "drives": ["oracle", "camera"]}]
    if quick:
        return v + [{"name": "latency_15ms", "cam": {"cam_latency": 15e-3}, "drives": ["camera"]}]
    for L in LATENCIES_MS:
        v.append({"name": f"latency_{L:g}ms", "cam": {"cam_latency": L * 1e-3}, "drives": ["camera"]})
    for nz in NOISES_UM:
        v.append({"name": f"noise_{nz:g}um", "cam": {"noise": nz * 1e-6}, "drives": ["camera"]})
    for r in RATES_HZ:
        v.append({"name": f"rate_{r:g}Hz", "cam": {"cam_hz": r}, "drives": ["camera"]})
    for bw in BANDWIDTHS_HZ:
        v.append({"name": f"bandwidth_{bw:g}Hz", "stage": {"servo_hz": bw, "inner_hz": max(250.0, 5.0 * bw)},
                  "drives": ["oracle", "camera"]})
    for tr in TRAVELS_MM:
        v.append({"name": f"travel_{tr:g}mm", "stage": {"q_lim_f": tr * 1e-3, "q_taper_f": 0.1 * tr * 1e-3,
                                                         "q_stop_f": tr * 1.2e-3}, "drives": ["oracle"]})
    for k in KAPPAS:
        v.append({"name": f"tilt_kappa_{k:g}", "kappa": k, "drives": ["camera"]})
    v.append({"name": "friction_intended", "writer": "intended", "drives": ["oracle", "camera"]})
    for name, (nh, nd) in SLIPS.items():         # 'held': the page held still (no command), the sheet's own creep
        v.append({"name": f"slip_{name}", "paper": {"rigid": False, "N_hold": nh, "N_hand": nd},
                  "drives": ["oracle", "camera", "held"]})
    for mg in PEN_MASSES_G:
        v.append({"name": f"pen_{mg:g}g", "pen_mass": mg * 1e-3, "drives": ["oracle", "camera"]})
    v.append({"name": "belt_single_stage", "variant": "belt_single", "drives": ["oracle", "camera"]})
    v.append({"name": "ideal_inner_loop", "stage": {"enc_res": 0.0, "vel_filter_hz": 0.0}, "drives": ["oracle"]})
    v.append({"name": "e_command_smoothed", "drives": ["E_chosen_raw", "E_chosen_smooth"]})
    v.append({"name": "friction_intended_firm_hand", "writer": "intended", "hand": dict(FIRM_HAND),
              "drives": ["oracle", "camera"]})
    return v


def moving_average(d: np.ndarray, n: int = 4) -> np.ndarray:
    """Causal n-tick moving average (delay (n - 1) / 2 ticks); removes a sawtooth of period n ticks."""
    d = np.asarray(d, float)
    c = np.cumsum(np.vstack([np.zeros((1, d.shape[1])), d]), axis=0)
    out = np.empty_like(d)
    k = np.arange(len(d))
    lo = np.maximum(k + 1 - n, 0)
    out[:] = (c[k + 1] - c[lo]) / (k + 1 - lo)[:, None]
    return np.ascontiguousarray(out)


def _stage(var: Dict):
    from . import design as D
    st = D.sim_stage(var.get("variant", "fine_A5"))
    for k, val in (var.get("stage") or {}).items():
        setattr(st, k, val)
    return st


def _cam(var: Dict) -> Dict:
    c = dict(BASE_CAM)
    c.update(var.get("cam") or {})
    return c


def _pred(var: Dict, quick: bool, signals_fn) -> Dict:
    from . import predictor as PRD
    st = _stage(var)
    g = st.group_delay()
    c = _cam(var)
    key = f"free_{c['cam_hz']:g}Hz_{c['cam_latency'] * 1e3:g}ms_{c['noise'] * 1e6:g}um_g{g * 1e3:.2f}"
    return PRD.load_or_fit(key, signals_fn, quick=quick, cam_hz=c["cam_hz"], cam_latency=c["cam_latency"],
                           noise=c["noise"], g=g, with_drift=False)


def run_note(i: int, quick: bool = False) -> List[str]:
    """Every variant on one tuning note (PD and ET, severe), cached per case."""
    from handwriting import params as PR
    from handwriting import plant as PL
    from readable import common as RC
    from . import plant as PP
    from . import predictor as PRD
    from . import tremor as T
    out_dir = CM.cache_dir(quick, "sensitivity")
    kinds = ["PD"] if quick else ["PD", "ET"]
    VV = variants(quick)
    sig_cache: Dict = {}

    def signals():
        if "s" not in sig_cache:
            sig_cache["s"] = PRD.training_signals(quick)
        return sig_cache["s"]
    preds = {v["name"]: _pred(v, quick, signals) for v in VV if "camera" in v["drives"]}
    sig_cache.clear()
    note = None
    done = []
    for kind in kinds:
        p = out_dir / f"tune_n{i}_{kind}_severe.json"
        prev = CM.jload(p) or {"devices": {}}
        todo = [v for v in VV if any(f"{v['name']}|{d}" not in prev["devices"] for d in v["drives"])]
        if not todo:
            done.append(p.name)
            continue
        t1 = time.time()
        if note is None:
            note = RC.tuning_note(i)
        spec = RC.tuning_spec(i, kind, "severe")
        dr = RC.tuning_tremor(note, spec)
        f0 = float(dr.meta["f0"])
        dev = prev["devices"]
        refs: Dict = {}

        def reference(writer: str, pen_mass: float, hand_over: Optional[Dict] = None):
            """(scn with tremor, clean run, fixed-page run with tremor, intended velocity, integrator pen mass, hand)
            for a pen, a writer convention and a hand (a changed pen or hand gets its own adapted hand path)."""
            key = (writer, pen_mass, tuple(sorted((hand_over or {}).items())))
            if key in refs:
                return refs[key]
            pen = dataclasses.replace(PR.ordinary_pen(), mass=pen_mass)
            hand = PR.Hand.from_config(**hand_over) if hand_over else note.hand
            if abs(pen_mass - 0.012) < 1e-9 and not hand_over:
                scn_n, scn_c = note.scenario("none", dr.d), note.scenario("none", None)
            else:
                hp = PL.adapted_path(note.scn0.intended, note.scn0.dt, pen, hand)
                scn_n, scn_c = PL.with_hand_path(note.scn0, hp, dr.d), PL.with_hand_path(note.scn0, hp, None)
            m_int = pen_mass + 1e-6
            vint = np.gradient(np.asarray(scn_c.intended), scn_c.dt, axis=0)
            held = PP.run(scn_n.pref, scn_n.vref, scn_n.down, scn_n.dt, hand=hand, writing=PR.Writing(),
                          pen_mass=m_int, writer=writer, vint=vint, stage=_stage({}),
                          cmd_ext=None)
            clean = PP.run(scn_c.pref, scn_c.vref, scn_c.down, scn_c.dt, hand=hand, writing=PR.Writing(),
                           pen_mass=m_int, writer=writer, vint=vint, stage=_stage({}))
            refs[key] = (scn_n, clean, held, vint, m_int, hand)
            return refs[key]
        base_scn, base_clean, base_held, _, _, _ = reference("hw1", 0.012)
        dev["platen_off|fixed"] = {"tip_tremor_mm": RC.measures(note.written, base_held.as_hw1(), base_scn,
                                                                 note.pens["none"], f0, read=False)["tip_tremor_mm"]}
        for v in todo:
            writer = v.get("writer", "hw1")
            pm = v.get("pen_mass", 0.012)
            scn_n, clean, held, vint, m_int, hand = reference(writer, pm, v.get("hand"))
            if writer != "hw1" or pm != 0.012 or v.get("hand"):
                dev[f"{v['name']}|fixed"] = {"tip_tremor_mm": RC.measures(
                    note.written, held.as_hw1(), scn_n, note.pens["none"], f0, read=False)["tip_tremor_mm"]}
            st = _stage(v)
            g = st.group_delay()
            n_ticks = int(np.ceil(len(scn_n.t) / 20)) + 1
            paper = PP.Paper(**v["paper"]) if v.get("paper") else None
            for drive in v["drives"]:
                k = f"{v['name']}|{drive}"
                if k in dev:
                    continue
                if drive.startswith("E_chosen"):
                    if "e_st" not in refs:
                        from aiprior import core as CO
                        r_n = PL.run(scn_n, note.pens["none"], hand)
                        refs["e_st"] = CO.streams_for(r_n, scn_n, note.pens["none"], note.trk,
                                                      CM.h(spec["id"], "platen-streams") % (2 ** 31))
                        del r_n
                    des = T.designs()["E_chosen"]
                    if drive.endswith("smooth"):
                        cmd = moving_average(T.e_command(des, refs["e_st"], RC.CaseLike(spec, None), g + 0.75e-3), 4)
                    else:
                        cmd = T.e_command(des, refs["e_st"], RC.CaseLike(spec, None), g)
                    pr = PP.run(scn_n.pref, scn_n.vref, scn_n.down, scn_n.dt, hand=hand, writing=PR.Writing(),
                                pen_mass=m_int, writer=writer, vint=vint, stage=st, paper=paper, cmd_ext=cmd)
                elif drive == "held":
                    pr = PP.run(scn_n.pref, scn_n.vref, scn_n.down, scn_n.dt, hand=hand, writing=PR.Writing(),
                                pen_mass=m_int, writer=writer, vint=vint, stage=st, paper=paper, cmd_ext=None)
                elif drive == "oracle":
                    cmd = T._oracle_ticks(held, clean, n_ticks, 5e-4, g)
                    pr = PP.run(scn_n.pref, scn_n.vref, scn_n.down, scn_n.dt, hand=hand, writing=PR.Writing(),
                                pen_mass=m_int, writer=writer, vint=vint, stage=st, paper=paper, cmd_ext=cmd)
                else:
                    c = _cam(v)
                    ctl = PP.Control(mode=1, cam_hz=c["cam_hz"], cam_latency=c["cam_latency"], cam_noise=c["noise"],
                                     kappa=v.get("kappa", 0.0), ar_coef=np.asarray(preds[v["name"]]["coef"]),
                                     horizon=g)
                    pr = PP.run(scn_n.pref, scn_n.vref, scn_n.down, scn_n.dt, hand=hand, writing=PR.Writing(),
                                pen_mass=m_int, writer=writer, vint=vint, stage=st, paper=paper, ctl=ctl, trem=dr.d,
                                tgt_tick=T._clean_ticks(clean, n_ticks, 5e-4),
                                seed=CM.h(spec["id"], "cam", v["name"]) % (2 ** 31))
                m = {"tip_tremor_mm": RC.measures(note.written, pr.as_hw1(), scn_n, note.pens["none"], f0,
                                                  read=False)["tip_tremor_mm"]}
                m.update(T.stage_stats(pr, pr.contact > 0.5))
                if paper is not None:
                    slip = np.linalg.norm(pr.xy("paperx") - pr.page, axis=1) * 1e3
                    m["paper_slip_max_mm"] = float(np.max(slip))
                    m["paper_slip_final_mm"] = float(slip[-1])
                dev[k] = m
                del pr
        CM.jdump(p, {"split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                     "class": "severe", "case_id": spec["id"], "f0": f0, "devices": dev,
                     "_elapsed_s": time.time() - t1})
        CM.log(f"[sensitivity] n{i} {kind}: {len(dev)} runs ({time.time() - t1:.0f} s)")
        done.append(p.name)
    return done


def aggregate(quick: bool) -> Dict:
    d = CM.cache_dir(quick, "sensitivity")
    cases = [c for c in (CM.jload(p) for p in sorted(d.glob("tune_n*_severe.json"))) if c]
    fc = CM.f_curve()
    keys = sorted({k for c in cases for k in c["devices"]})
    out = {"label": "SIMULATION (HW1 + the platen stage), real inputs, TUNING SPLIT, severe class; words via study F's "
                    "frozen curve (CALC); 95 % writer-bootstrap intervals", "variants": variants(quick),
           "n_cases": len(cases), "rows": {}}
    for k in keys:
        pw = CM.per_writer(cases, lambda c: (c["devices"].get(k) or {}).get("tip_tremor_mm"))
        if not pw:
            continue
        row = {"tip_tremor_mm": CM.boot(pw),
               "words_via_curve": CM.boot(CM.per_writer(cases, lambda c: CM.words_via_curve(
                   (c["devices"].get(k) or {}).get("tip_tremor_mm"), fc["p"]) if k in c["devices"] else None))}
        for m in ("at_limit_share", "travel_p99_mm", "force_rms_N", "force_p99_N", "copper_W_per_axis_rms",
                  "paper_slip_max_mm", "paper_slip_final_mm"):
            b = CM.per_writer(cases, lambda c, m=m: (c["devices"].get(k) or {}).get(m))
            if b:
                row[m] = CM.boot(b)
        out["rows"][k] = row
    return out
