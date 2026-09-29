r"""Study W, one command: python3 -m wholepen.run_study [--quick] [--stages s1 s2 ...]

Stages (in order; each writes results/wholepen/<stage>.json with stabpen.provenance; the simulation stages keep one
row per case in wholepen/build/rows/<stage>.jsonl and resume from it, so a killed run continues where it stopped):
  targets    task 1: tremor classes at the pen tip (LIT, REAL DATA)                                        seconds
  realdata   UCI spirals and NewHandPD pen signals (needs the data files; see realdata.py)                  ~1 min
  grip       task 2: the grip model and its sensitivity                                                    seconds
  calc       the review's questions by calculation (calc.py) and the sizing of every candidate (designs.py) ~1 min
  optimise   CMA-ES + exact gradients over the gyroscope tail (optimise.py) and the CALC sweeps           ~3 min
  verify     simulator checks for each new device (verify.py)                                              ~5 min
  tune       tuning writers 100 (and 101), seed 300: the collar's gain, the gyroscope's law, the gate      ~15 min
  freeze     the rules (results/wholepen/rules.json) before any test run
  test       test writers 0-1 (5 words each: 10 words), seeds 200/201; tremor classes x designs          ~80 min
  grips      the collar and the gyroscope tail against the same mass locked at grip 0.5 / 1 / 2 x         ~20 min
  arm        a subset on sim2's articulated arm                                                            ~10 min
  summary    the one-number table, results cards, ratios explained                                          seconds
  figures    figures with CSV twins; explain: animation.json and layout_parts.json; evidence rows          ~1 min
--quick: one writer, the moderate classes and fewer designs (a smoke test, minutes; results under quick_*.json).
Evidence status: SIMULATION on synthetic writers with synthetic or recorded tremor, and CALCULATION.  Nothing measured.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from dataclasses import asdict, replace
from typing import Dict, List, Optional

import numpy as np

from . import BUILD, RESULTS, ROOT, provenance, write_json  # noqa: F401
from . import cases as CS
from . import control as C
from . import designs as DS

LOG = os.path.join(BUILD, "logs", "run_study.log")


def log(msg: str):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


class Rows:
    """One JSON line per simulated case, keyed; resumable."""

    def __init__(self, name: str):
        self.path = os.path.join(BUILD, "rows", name + ".jsonl")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.d: Dict[str, Dict] = {}
        if os.path.exists(self.path):
            for ln in open(self.path):
                try:
                    r = json.loads(ln)
                    self.d[r["key"]] = r
                except Exception:
                    pass

    def has(self, k):
        return k in self.d

    def get(self, k):
        return self.d.get(k)

    def put(self, k, row: Dict):
        row = dict(row, key=k)
        self.d[k] = row
        with open(self.path, "a") as f:
            f.write(json.dumps(row, default=_jd) + "\n")

    def values(self):
        return list(self.d.values())


def _jd(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ------------------------------------------------------------------------------------------------ pens and designs
def gt100_kwargs() -> Dict:
    d = DS.cmg_design(100, mode="turret")
    return dict(mode="turret", z=0.145 + d["length_mm"] * 0.5e-3, r_o=d["rotor_r_o_mm"] * 1e-3, r_i=d["rotor_r_i_mm"] * 1e-3,
                thick=d["rotor_t_mm"] * 1e-3, rpm=25000.0, fixed_mass=d["fixed_g"] * 1e-3, tau_g_max=0.045)


def pens() -> Dict[str, CS.PenVariant]:
    return {"base": CS.PenVariant("base"),
            "collar": CS.PenVariant("collar", collar=dict(z_p=0.050)),
            "gt100": CS.PenVariant("gt100", gt=gt100_kwargs())}


def pen_variant(name: str, grip: float = 1.0) -> CS.PenVariant:
    pv = pens()[name]
    if grip != 1.0:
        pv = replace(pv, name=f"{pv.name}_g{grip:g}", grip_scale=grip)
    return pv


# design -> (pen, firmware, device-law overrides, nose reach override, oracle split (nose share))
def designs(rules: Dict) -> Dict[str, tuple]:
    cg = rules.get("collar_gain", 0.75)
    claw = rules.get("collar_law", "ff")
    law = rules.get("cmg_law", "damp")
    gm = rules.get("gate_margin_mm", 0.3) * 1e-3
    return {
        "none": ("base", "none", {}, None, None),
        "nose": ("base", "nose", {}, None, None),
        "nose_gate": ("base", "nose", {"gate": True, "gate_margin": gm}, None, None),
        "collar_locked": ("collar", "none", {}, None, None),
        "collar_nose": ("collar", "nose", {"collar": claw, "collar_gain": cg}, None, None),
        "collar_fine": ("collar", "nose", {"collar": claw, "collar_gain": cg}, 1.0e-3, None),
        "gt_locked": ("gt100", "none", {}, None, None),
        "gt_locked_nose": ("gt100", "nose", {}, None, None),
        "gt_nose": ("gt100", "nose", {"cmg": law}, None, None),
        "nose_oracle": ("base", "oracle", {}, None, None),
        "collar_oracle": ("collar", "none", {"collar": "oracle"}, None, None),
        "collar_nose_oracle": ("collar", "oracle", {"collar": "oracle"}, None, 0.5),
        "gt_oracle": ("gt100", "none", {"cmg": "oracle"}, None, None),
    }


REF_OF_PEN = {"base": "none", "collar": "collar_locked", "gt100": "gt_locked"}

LABELS = {
    "none": "Rev J pen, nothing moving (no help)",
    "nose": "Rev J moving nose (+-6.57 mm), as built",
    "nose_gate": "Rev J nose + write only when in reach",
    "collar_locked": "collar pen, collar locked, nose held",
    "collar_nose": "whole-pen collar + Rev J nose",
    "collar_fine": "whole-pen collar + small fine nib (+-1 mm)",
    "gt_locked": "gyro tail 100 g, locked, nose held",
    "gt_locked_nose": "gyro tail 100 g locked + Rev J nose (same mass, no gyro action)",
    "gt_nose": "gyro tail 100 g active + Rev J nose",
    "nose_oracle": "Rev J nose, perfect tremor knowledge (limit)",
    "collar_oracle": "collar alone, perfect tremor knowledge (limit)",
    "collar_nose_oracle": "collar + Rev J nose, perfect tremor knowledge (limit)",
    "gt_oracle": "gyro tail alone, perfect tremor knowledge (limit)",
}

CLASSES = [
    ("ET_mild", "ET", 6.0, 1e-3), ("ET_moderate", "ET", 6.0, 3e-3), ("ET_severe", "ET", 6.0, 8e-3),
    ("ET_moderate_9Hz", "ET", 9.0, 3e-3),
    ("PD_mild", "PD_action", 5.0, 1e-3), ("PD_moderate", "PD_action", 5.0, 3e-3), ("PD_severe", "PD_action", 5.0, 8e-3),
    ("PD_reemergent_severe", "PD_reemergent", 5.0, 8e-3), ("PD_recorded_moderate", "PD_recorded", 5.37, 3e-3),
]
CLASS_LABEL = {
    "ET_mild": "ET mild (1 mm, 6 Hz)", "ET_moderate": "ET moderate (3 mm, 6 Hz)", "ET_severe": "ET severe (8 mm, 6 Hz)",
    "ET_moderate_9Hz": "ET moderate, fast (3 mm, 9 Hz)", "PD_mild": "PD action mild (1 mm, 5 Hz)",
    "PD_moderate": "PD action moderate (3 mm, 5 Hz)", "PD_severe": "PD action severe (8 mm, 5 Hz)",
    "PD_reemergent_severe": "PD re-emergent severe (8 mm, 5 Hz, in pauses)",
    "PD_recorded_moderate": "PD recorded patient waveform (3 mm, 5.4 Hz)",
}
KEEP = ("ink_err_um", "letters_read", "words_app", "tip_tremor_mm", "handle_tremor_mm", "coverage", "missing_stroke_rate",
        "missing_strokes", "n_strokes", "ink_lost_mm", "autowrite_extra_s", "completion_time_ratio", "task_time_s",
        "P_nose_W", "P_devices_W", "P_total_W", "P_collar_W", "P_cmg_spin_W", "P_cmg_gimbal_W", "P_gate_W",
        "detector_open_share", "pivot_peak_rad", "gimbal_peak_rad", "gimbal_tq_p95_mNm", "felt_rms_N", "felt_p95_N",
        "moved_vs_clean_um", "f_est_median", "wall_s", "mu", "seed", "w", "f0", "amp_mm", "kind", "fw", "pen", "hand_model")


class Bench:
    """Set-ups per (writer, pen, grip, hand model), built lazily and cached on disk by cases.Setup."""

    def __init__(self, text: str = CS.TEXT):
        self.text = text
        self.su = {}
        self.refs = {}

    def setup(self, w: int, pen: str, grip: float = 1.0, hand_model: str = "h1"):
        k = (w, pen, grip, hand_model)
        if k not in self.su:
            pv = pen_variant(pen, grip)
            pm = pv.build(hand_model=hand_model)
            self.su[k] = CS.Setup(w, pv, pm, text=self.text, log=log, hand_model=hand_model)
        return self.su[k]


def run_design(bench: Bench, rows: Rows, rules: Dict, w: int, seed: int, cls: tuple, dname: str, grip: float = 1.0,
               hand_model: str = "h1", key_prefix: str = "") -> Dict:
    """One (writer, class, design) case; the pen's device-off run is made first (every oracle and every 'felt change'
    needs it) and kept in memory for the writer's other designs."""
    cname, kind, f0, amp = cls
    pen, fw, over, reach, split = designs(rules)[dname]
    key = f"{key_prefix}{hand_model}|g{grip:g}|w{w}|s{seed}|{cname}|{dname}"
    if rows.has(key):
        return rows.get(key)
    su = bench.setup(w, pen, grip, hand_model)
    rk = (w, seed, cname, pen, grip, hand_model)
    ref = bench.refs.get(rk)
    ref_name = REF_OF_PEN[pen]
    is_oracle = fw == "oracle" or any(v == "oracle" for v in over.values())
    if ref is None and amp > 0 and (is_oracle or dname == ref_name):
        rpen, rfw, rover, _, _ = designs(rules)[ref_name]
        m0 = CS.run_case(su, rfw, C.WPConfig(**rover), kind, f0, amp, seed, keep=True)
        ref = m0.pop("_r")
        bench.refs[rk] = ref
        k0 = f"{key_prefix}{hand_model}|g{grip:g}|w{w}|s{seed}|{cname}|{ref_name}"
        if hand_model == "h1" and grip == 1.0 and not key_prefix and (w, cname) in TRACE_CASES:
            save_trace(k0, ref, su)
        if not rows.has(k0):
            rows.put(k0, _row(m0, cname, ref_name, grip))
        if dname == ref_name:
            return rows.get(k0)
    wp = C.WPConfig(**over)
    trace = (hand_model == "h1" and grip == 1.0 and not key_prefix and (w, cname) in TRACE_CASES)
    m = CS.run_case(su, fw, wp, kind, f0, amp, seed, ref_none=ref, nose_reach=reach, oracle_split=split, keep=trace)
    if trace:
        save_trace(key, m.pop("_r"), su, full=(cname, dname) in ANIM_CASES)
    row = _row(m, cname, dname, grip)
    rows.put(key, row)
    log(f"[{rows.path.split('/')[-1][:-6]}] {hand_model} g{grip:g} w{w} {cname} {dname}: tip {row.get('tip_tremor_mm', float('nan')):.2f} mm, "
        f"ink {row.get('ink_err_um', float('nan')):.0f} um, words {row.get('words_app', float('nan')):.2f}, "
        f"cover {row.get('coverage', float('nan')):.2f}, {row.get('wall_s', 0):.0f} s")
    return row


TRACE_CASES = {(0, "ET_moderate"), (0, "ET_severe"), (0, "PD_severe"), (0, "PD_moderate"), (1, "ET_severe"),
               (0, "PD_recorded_moderate")}
ANIM_CASES = {("PD_severe", "collar_nose"), ("ET_severe", "collar_nose")}


def save_trace(key: str, r, su, full: bool = False):
    """The ink (x, y, contact) at 250 Hz and the writer's intended letters, for the before/after pictures; with full,
    the channels the explainer's animation needs (SIMULATION record)."""
    d = os.path.join(BUILD, "traces")
    os.makedirs(d, exist_ok=True)
    t = r["t"]
    k = max(1, int(round(0.004 / float(t[1] - t[0]))))
    ink = r.ink()
    out = {"t": t[::k], "ink": ink[::k, :2], "contact": r["contact"][::k]}
    it = su.case.written.intended
    kk = max(1, int(round(0.004 / float(it.t[1] - it.t[0]))))
    out.update(it_t=it.t[::kk], it_xy=it.xy[::kk], it_down=it.pen_down[::kk])
    if full:
        for ch in ("tipx", "tipy", "tipz", "ballx", "bally", "ballz", "ax", "ay", "az", "handx", "handy", "handz", "q1", "q2",
                   "w_piv1", "w_piv2", "w_col_u1", "w_col_u2", "Nb", "Ns"):
            if ch in r.idx:
                out["ch_" + ch] = r[ch][::k]
    fn = os.path.join(d, key.replace("|", "_") + ".npz")
    np.savez_compressed(fn, **out)
    return fn


def _row(m: Dict, cname: str, dname: str, grip: float) -> Dict:
    r = {k: m[k] for k in KEEP if k in m}
    r.update({"class": cname, "design": dname, "grip": grip})
    return r


# ------------------------------------------------------------------------------------------------ stages
def stage_targets(quick=False):
    from . import targets as T
    rd = None
    p = os.path.join(RESULTS, "realdata.json")
    if os.path.exists(p):
        try:
            rd = json.load(open(p)).get("summary")
        except Exception:
            rd = None
    body = T.classes(rd)
    body["stabpen.provenance"] = provenance("LITERATURE + REAL DATA + CALC (class values ASSUMPTION)")
    write_json("targets.json", body)
    return body


def stage_realdata(quick=False):
    from . import realdata as RD
    body = {"stabpen.provenance": provenance("REAL DATA (UCI spirals, NewHandPD pen signals) + CALC")}
    for name, fn in (("uci", RD.uci), ("newhandpd", RD.newhandpd)):
        try:
            body[name] = fn()
        except Exception as e:                                   # the data are outside the repository
            body[name] = {"error": f"{type(e).__name__}: {e}", "how_to_get": RD.__doc__}
    try:
        body["summary"] = {"uci_pd_tremor_peak_mm_max": body["uci"].get("pd_peak_mm_max"),
                           "newhandpd_share_with_line": body["newhandpd"].get("share_with_line"),
                           "newhandpd_lines": body["newhandpd"].get("lines_summary")}
    except Exception:
        pass
    write_json("realdata.json", body)
    return body


def stage_grip(quick=False):
    from . import grip as G
    body = G.summary()
    body["stabpen.provenance"] = provenance("CALCULATION on LIT and ASSUMPTION")
    write_json("grip.json", body)
    return body


def stage_calc(quick=False):
    from . import calc as K
    body = K.run_all()
    body["designs"] = {
        "cmg": {str(m): DS.cmg_design(m, mode="turret") for m in (40, 60, 80, 100)},
        "cmg_pairs": {str(m): DS.cmg_design(m, mode="pairs") for m in (60, 100)},
        "tmd": DS.tmd_design(), "collar_v1": DS.collar_design(0.050, 4e-3), "paper": DS.paper_design(),
        "gating": DS.gating_design(), "authority": DS.authority()}
    body["stabpen.provenance"] = provenance("CALCULATION (linear model lin.py; designs.py) on PROPOSED DESIGN inputs")
    write_json("calc.json", body)
    return body


def stage_optimise(quick=False):
    from . import optimise as OP
    body = {"combo_100g": OP.optimise_combo(100.0, evals=60 if quick else 240),
            "sweep_cmg": OP.sweep_cmg(), "sweep_tmd": OP.sweep_tmd(), "sweep_force_omni": OP.sweep_force("omni"),
            "sweep_force_sled": OP.sweep_force("sled")}
    body["stabpen.provenance"] = provenance("CALCULATION (linear model; CMA-ES endcap/cmaes.py; torch gradients)")
    write_json("optimise.json", body)
    return body


def stage_verify(quick=False):
    from . import verify as V
    body = V.run_all(quick=quick)
    body["stabpen.provenance"] = provenance("SIMULATION checked against CALCULATION (closed forms, conservation)")
    write_json("verification.json", body)
    return body


def rules_path():
    return os.path.join(RESULTS, "rules.json")


def load_rules() -> Dict:
    try:
        return json.load(open(rules_path()))["rules"]
    except Exception:
        return {}


def stage_tune(quick=False):
    """Tuning writer 100 (and 101 unless quick), seed 300: the collar's gain (0.75 / 1.0), the gyroscope's causal law
    (damp / afc / ff, against the locked tail with the nose), the gate's margin (0.3 / 1.0 mm)."""
    rows = Rows("tune")
    bench = Bench()
    ws = (100,)
    seed = 300
    et3 = ("ET_moderate", "ET", 6.0, 3e-3)
    pd8 = ("PD_severe", "PD_action", 5.0, 8e-3)
    et8 = ("ET_severe", "ET", 6.0, 8e-3)
    for w in ws:
        for cls in (et3, pd8):
            for tag, rl in (("ff0.75", {"collar_law": "ff", "collar_gain": 0.75}), ("ff1", {"collar_law": "ff", "collar_gain": 1.0}),
                            ("afc", {"collar_law": "afc"})):
                run_design(bench, rows, rl, w, seed, cls, "collar_nose", key_prefix=f"cl_{tag}|")
            run_design(bench, rows, {}, w, seed, cls, "collar_oracle")
            run_design(bench, rows, {}, w, seed, cls, "nose")
        for law in ("damp", "afc", "ff"):
            run_design(bench, rows, {"cmg_law": law}, w, seed, et3, "gt_nose", key_prefix=f"cmg_{law}|")
        run_design(bench, rows, {}, w, seed, et3, "gt_locked_nose")
        run_design(bench, rows, {}, w, seed, et3, "gt_oracle")
        run_design(bench, rows, {}, w, seed, et3, "nose")
        for gmm in (0.3, 1.0):
            run_design(bench, rows, {"gate_margin_mm": gmm}, w, seed, et8, "nose_gate", key_prefix=f"gm{gmm}|")
        run_design(bench, rows, {}, w, seed, et8, "nose")
        if quick:
            break
    R = rows.values()
    body = {"rows": R, "stabpen.provenance": provenance("SIMULATION (tuning writers and seed only)", seeds=[seed])}
    write_json("tuning.json" if not quick else "quick_tuning.json", body)
    return body


def _mean(R, key, **flt):
    v = [r[key] for r in R if all(r.get(k) == x for k, x in flt.items()) and isinstance(r.get(key), (int, float))
         and math.isfinite(r[key])]
    return float(np.mean(v)) if v else float("nan")


def stage_freeze(quick=False):
    """Rules from the tuning rows only (written with a timestamp before any test row exists)."""
    rows = Rows("tune").values()
    by = lambda pref, cls, d: [r for r in rows if r["key"].startswith(pref) and r["class"] == cls and r["design"] == d]
    # the collar's law and gain: lower mean ink error over ET 3 mm and PD 8 mm
    cg = {}
    for tag in ("ff0.75", "ff1", "afc"):
        v = [r["ink_err_um"] for cls in ("ET_moderate", "PD_severe") for r in by(f"cl_{tag}|", cls, "collar_nose")]
        cg[tag] = float(np.mean(v)) if v else float("inf")
    best = min(cg, key=cg.get)
    collar_law = "afc" if best == "afc" else "ff"
    collar_gain = {"ff0.75": 0.75, "ff1": 1.0, "afc": 0.75}[best]
    # the gyroscope's law: lowest ink tremor among the causal laws (the gate against the locked tail is reported, not
    # used to pick)
    cl = {}
    for law in ("damp", "afc", "ff"):
        v = [r["tip_tremor_mm"] for r in by(f"cmg_{law}|", "ET_moderate", "gt_nose")]
        cl[law] = float(np.mean(v)) if v else float("inf")
    cmg_law = min(cl, key=cl.get)
    # the gate's margin: the larger margin only if it keeps >= 90 % coverage and lowers the ink error
    gmr = {}
    for gmm in (0.3, 1.0):
        rr = by(f"gm{gmm}|", "ET_severe", "nose_gate")
        gmr[gmm] = (float(np.mean([r["ink_err_um"] for r in rr])) if rr else float("inf"),
                    float(np.mean([r["coverage"] for r in rr])) if rr else 0.0)
    gate_margin = 0.3
    if gmr[1.0][1] >= 0.9 * gmr[0.3][1] and gmr[1.0][0] < gmr[0.3][0]:
        gate_margin = 1.0
    body = {"rules": {"collar_law": collar_law, "collar_gain": collar_gain, "cmg_law": cmg_law, "gate_margin_mm": gate_margin,
                      "page_sensor": "measured (sim2j deltapen_walk: OPT-02 per-window statistics, errors add up)",
                      "tracker": "sim2j frozen (results/sim2j/rules.json)"},
            "evidence": {"collar_law_ink_um": cg, "cmg_law_tip_mm": cl, "gate_margin": {str(k): v for k, v in gmr.items()}},
            "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "chosen on the tuning writers 100-101 and seed 300 only, before any test run",
            "stabpen.provenance": provenance("SIMULATION (tuning set) -> frozen rules", seeds=[300])}
    if not quick:
        write_json("rules.json", body)
    log(f"[freeze] {body['rules']}")
    return body


def stage_test(quick=False):
    rules = load_rules()
    rows = Rows("test" if not quick else "quick_test")
    bench = Bench()
    ws = ((0, 200), (1, 201)) if not quick else ((0, 200),)
    cls_all = CLASSES if not quick else [c for c in CLASSES if c[0] in ("ET_moderate", "PD_severe")]
    full = ("ET_moderate", "ET_severe", "PD_moderate", "PD_severe", "PD_reemergent_severe", "PD_recorded_moderate")
    plan = {c[0]: (["none", "nose", "collar_nose", "collar_nose_oracle"] if c[0] in full else ["none", "nose", "collar_nose"])
            for c in cls_all}
    for c in ("ET_moderate", "ET_severe", "PD_severe", "PD_reemergent_severe"):
        plan.get(c, []).append("nose_gate")
    for c in ("ET_moderate", "ET_severe", "PD_moderate", "PD_severe"):
        plan.get(c, []).append("collar_fine")
    for c in ("ET_moderate", "ET_severe", "PD_severe"):
        plan.get(c, []).append("nose_oracle")
    for c in ("ET_moderate", "PD_severe"):
        plan.get(c, []).extend(["gt_locked_nose", "gt_nose"])
    if quick:
        plan = {c[0]: ["none", "nose", "collar_nose", "collar_nose_oracle"] for c in cls_all}
    for w, seed in ws:
        for cls in cls_all:
            for dn in plan[cls[0]]:
                try:
                    run_design(bench, rows, rules, w, seed, cls, dn)
                except Exception as e:
                    log(f"[test] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
        # tremor-free writing: the false correction ('clean writing changed')
        for dn in ("nose", "collar_nose", "collar_fine"):
            key = f"h1|g1|w{w}|s{seed}|clean|{dn}"
            if rows.has(key):
                continue
            pen, fw, over, reach, _ = designs(rules)[dn]
            su = bench.setup(w, pen)
            m = CS.run_case(su, fw, C.WPConfig(**over), "ET", 6.0, 0.0, seed, nose_reach=reach)
            rows.put(key, _row(m, "clean", dn, 1.0))
            log(f"[test] w{w} clean {dn}: moved {m.get('moved_vs_clean_um', float('nan')):.0f} um")
    body = {"rows": rows.values(), "rules": rules,
            "stabpen.provenance": provenance("SIMULATION (test writers and seeds; rules frozen before)",
                                             seeds=[s for _, s in ws])}
    write_json("test.json" if not quick else "quick_test.json", body)
    return body


def stage_grips(quick=False):
    """The review's decisive questions in the simulator: the collar and the gyroscope tail against the same mass
    locked, at grip stiffness 0.5 / 1 / 2 x (tuning writer 100, seed 300: not the test set)."""
    rules = load_rules()
    rows = Rows("grips")
    bench = Bench()
    w, seed = 100, 300
    cls = ("ET_moderate", "ET", 6.0, 3e-3)
    grips = (0.5, 2.0) if not quick else (0.5,)
    for g in grips:
        for dn in ("collar_locked", "collar_nose", "collar_oracle", "gt_locked_nose", "gt_nose"):
            try:
                run_design(bench, rows, rules, w, seed, cls, dn, grip=g)
            except Exception as e:
                log(f"[grips] FAILED g{g} {dn}: {e}")
    body = {"rows": rows.values(), "stabpen.provenance": provenance("SIMULATION (tuning writer 100, seed 300)", seeds=[seed])}
    write_json("grips.json", body)
    return body


def stage_arm(quick=False):
    rules = load_rules()
    rows = Rows("arm")
    bench = Bench()
    w, seed = 0, 200
    for cls in (("ET_moderate", "ET", 6.0, 3e-3),):
        for dn in ("none", "nose", "collar_locked", "collar_nose", "collar_oracle"):
            try:
                run_design(bench, rows, rules, w, seed, cls, dn, hand_model="arm")
            except Exception as e:
                log(f"[arm] FAILED {cls[0]} {dn}: {e}")
        if quick:
            break
    body = {"rows": rows.values(), "stabpen.provenance": provenance("SIMULATION (articulated arm, test writer 0)", seeds=[seed])}
    write_json("arm.json", body)
    return body


def stage_summary(quick=False):
    from . import summary as SM
    body = SM.build()
    body["stabpen.provenance"] = provenance("SIMULATION + CALCULATION (aggregates of test.json, grips.json, arm.json, calc.json)")
    write_json("summary.json", body)
    return body


def stage_figures(quick=False):
    from . import figures as F
    from . import explain as X
    from . import evidence as E
    out = {"figures": F.all_figures(), "explain": X.write_all(), "evidence": E.write_rows()}
    return out


STAGES = ["targets", "realdata", "grip", "calc", "optimise", "verify", "tune", "freeze", "test", "grips", "arm",
          "summary", "figures"]
FN = {s: globals()["stage_" + s] for s in STAGES}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", nargs="*", default=None)
    a = ap.parse_args(argv)
    stages = a.stages or (["targets", "grip", "calc", "tune", "freeze", "test", "summary", "figures"] if a.quick else STAGES)
    for s in stages:
        t0 = time.time()
        log(f"== stage {s}")
        FN[s](quick=a.quick)
        log(f"== stage {s} done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
