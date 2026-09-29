r"""Study W, one command: python3 -m wholepen.run_study [--quick] [--stages s1 s2 ...]

Stages (in order; each writes results/wholepen/<stage>.json with stabpen.provenance; the simulation stages keep one
row per case in wholepen/build/rows/<stage>.jsonl and resume from it, so a killed run continues where it stopped):
  targets    task 1: tremor classes at the pen tip (LIT, REAL DATA)                                        seconds
  realdata   UCI spirals and NewHandPD pen signals (needs the data files; see realdata.py)                  ~1 min
  grip       task 2: the grip model and its sensitivity                                                    seconds
  calc       the review's questions by calculation (calc.py) and the sizing of every candidate (designs.py) ~1 min
  optimise   CMA-ES + exact gradients over the gyroscope tail (optimise.py) and the CALC sweeps           ~3 min
  verify     simulator checks for each new device (verify.py)                                              ~5 min
  tune       tuning writer 100, seed 300: the tracker, the collar's gain, the gyroscope's law, the gate  ~40 min
  freeze     the rules (results/wholepen/rules.json) before any test run
  test       test writers 0-1 (5 words each: 10 words), seeds 200/201; tremor classes x designs          ~80 min
  grips      the collar and the gyroscope tail against the same mass locked at grip 0.5 and 2 x (tuning
             writer 100, ET 3 mm; grip 1 x from the tune stage)                                             ~20 min
  arm        a subset on sim2's articulated arm                                                            ~10 min
  limits     the collar against the same pen with the collar locked and the nose working, and the nose's own
             perfect-knowledge limit, on the test writers (comparators; rows added to the test rows)        ~15 min
  light      the collar with a light (24 g) inner pen, the review's design point, on the test writers        ~20 min
  light2     the light collar with a +-1 mm nib: its law re-tuned on tuning writer 100 (rules_light.json), then
             the test writers                                                                               ~10 min
  real       study R's real tremor classes (recorded PD tremor, test split) at 0.24 and 1.72 mm, test
             writers 0-1                                                                                    ~15 min
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
            # the review's design point: a light inner pen (the Rev J nose and refill in a 6 g barrel: 24 g, centre of
            # mass 63 mm from the tip) instead of the whole 87 g Rev J pen; servo damping scaled to its inertia
            "collar_light": CS.PenVariant("collar_light", collar=dict(z_p=0.050, inner_m=0.006, inner_zcm=0.035, inner_J=3e-6,
                                                                     C_s=0.015)),
            "gt100": CS.PenVariant("gt100", gt=gt100_kwargs())}


def pen_variant(name: str, grip: float = 1.0) -> CS.PenVariant:
    pv = pens()[name]
    if grip != 1.0:
        pv = replace(pv, name=f"{pv.name}_g{grip:g}", grip_scale=grip)
    return pv


# design -> (pen, firmware, device-law overrides, nose reach override, oracle split (nose share))
def designs(rules: Dict) -> Dict[str, tuple]:
    cg = rules.get("collar_gain", 1.0)
    claw = rules.get("collar_law", "ff")
    law = rules.get("cmg_law", "damp")
    gm = rules.get("gate_margin_mm", 0.3) * 1e-3
    tr = rules.get("tracker_fw", "nose")          # 'nose' (sim2j's frozen guarded tracker) | 'nose_gl' (ai2's gated listening)
    cmax = rules.get("collar_share_max", 1.0)
    cfrac = rules.get("collar_frac", 0.9)
    return {
        "none": ("base", "none", {}, None, None),
        "nose": ("base", tr, {}, None, None),
        "nose_gate": ("base", tr, {"gate": True, "gate_margin": gm}, None, None),
        "collar_locked": ("collar", "none", {}, None, None),
        "collar_locked_nose": ("collar", tr, {}, None, None),
        "collar_nose": ("collar", tr, {"collar": claw, "collar_gain": cg, "alloc_reach": 5.0e-3, "alloc_share_max": cmax,
                                       "collar_frac": cfrac}, None, None),
        "collar_fine": ("collar", tr, {"collar": claw, "collar_gain": cg, "alloc_reach": 0.8e-3, "alloc_share_max": cmax,
                                       "collar_frac": cfrac}, 1.0e-3, None),
        "light_locked": ("collar_light", "none", {}, None, None),
        "light_locked_nose": ("collar_light", tr, {}, None, None),
        "light_nose": ("collar_light", tr, {"collar": claw, "collar_gain": cg, "alloc_reach": 5.0e-3, "alloc_share_max": cmax,
                                            "collar_frac": cfrac}, None, None),
        "light_fine": ("collar_light", tr, {"collar": claw, "collar_gain": cg, "alloc_reach": 0.8e-3, "alloc_share_max": cmax,
                                            "collar_frac": cfrac}, 1.0e-3, None),
        "light_nose_oracle": ("collar_light", "oracle", {"collar": "oracle"}, None, 0.5),
        # the compact design's law re-tuned for a +-1 mm nib on tuning writer 100 (rules_light.json, frozen before its
        # test runs): the main rules cap the collar at gain 0.5 and share 0.6, chosen for the collar with Rev J's nose
        "light_fine_t": ("collar_light", tr, {"collar": claw, "collar_gain": rules.get("lf_gain", cg), "alloc_reach": 0.8e-3,
                                              "alloc_share_max": rules.get("lf_share_max", cmax),
                                              "collar_frac": rules.get("lf_frac", cfrac)}, 1.0e-3, None),
        "gt_locked": ("gt100", "none", {}, None, None),
        "gt_locked_nose": ("gt100", tr, {}, None, None),
        "gt_nose": ("gt100", tr, {"cmg": law}, None, None),
        "nose_oracle": ("base", "oracle", {}, None, None),
        "collar_oracle": ("collar", "none", {"collar": "oracle"}, None, None),
        "collar_nose_oracle": ("collar", "oracle", {"collar": "oracle"}, None, 0.5),
        "gt_oracle": ("gt100", "none", {"cmg": "oracle"}, None, None),
    }


REF_OF_PEN = {"base": "none", "collar": "collar_locked", "collar_light": "light_locked", "gt100": "gt_locked"}

LABELS = {
    "none": "Rev J pen, nothing moving (no help)",
    "nose": "Rev J moving nose (±6.57 mm), as built",
    "nose_gate": "Rev J nose + write only when in reach",
    "collar_locked": "collar pen, collar locked, nose held",
    "collar_locked_nose": "collar pen, collar locked + Rev J nose (same mass, no collar action)",
    "collar_nose": "whole-pen collar + Rev J nose",
    "collar_fine": "whole-pen collar + small fine nib (±1 mm)",
    "light_locked": "light collar pen (24 g inner pen), collar locked, nose held",
    "light_locked_nose": "light collar pen, collar locked + Rev J nose (same mass, no collar action)",
    "light_nose": "light collar pen: collar + Rev J nose",
    "light_fine": "light collar pen: collar + small fine nib (±1 mm)",
    "light_nose_oracle": "light collar pen: collar + Rev J nose, perfect tremor knowledge (limit)",
    "light_fine_t": "light collar pen: collar + small fine nib (±1 mm), law re-tuned for the fine nib",
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
CLASSES_REAL = [("REAL_PD_moderate", "REAL_PD", 6.0, 0.24e-3), ("REAL_PD_severe", "REAL_PD", 6.0, 1.72e-3)]
CLASS_LABEL.update({"REAL_PD_moderate": "Real PD, moderate class (0.24 mm, study R)",
                    "REAL_PD_severe": "Real PD, severe class (1.72 mm, study R)"})
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
        u, n = body["uci"], body["newhandpd"]
        ab = n.get("above_rows", [])
        body["summary"] = {
            "uci_pd_tremor_peak_mm_median": u["parkinson"]["amp_pk_mm_median"],
            "uci_pd_tremor_peak_mm_max": u["parkinson"]["amp_pk_mm_max"],
            "uci_control_peak_mm_max": u["control"]["amp_pk_mm_max"],
            "uci_pd_share_above_control_p95": u.get("pd_share_above"),
            "newhandpd_patients_with_line": n.get("patients_above"),
            "newhandpd_patients": n.get("patients", {}).get("n_persons"),
            "newhandpd_share_with_line": n.get("patients_share_above"),
            "newhandpd_line_f_Hz": [round(r["f_Hz"], 2) for r in ab],
            "newhandpd_line_disp_pk_mm_at_sensor": [round(r["disp_pk_mm_at_sensor"], 2) for r in ab],
            "label": "REAL DATA, CALC (see uci.label and newhandpd.label for the assumptions)"}
    except Exception as e:
        body["summary"] = {"error": f"{type(e).__name__}: {e}"}
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
    body = {"collar_design": OP.optimise_collar(evals=40 if quick else 80),
            "combo_100g": OP.optimise_combo(100.0, evals=40 if quick else 120),
            "sweep_cmg": OP.sweep_cmg(masses=(60, 100)), "sweep_tmd": OP.sweep_tmd(f_tunes=(5.0, 6.0), zetas=(0.08,)),
            "sweep_force_omni": OP.sweep_force("omni"), "sweep_force_sled": OP.sweep_force("sled")}
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


TRACKERS = ("nose", "nose_gl", "nose_glg")       # sim2j's guarded (G4); ai2's gated listening (fallback: Rev H as built);
                                                 # gated listening with the guarded fallback
DESIGN_TRACKER = "nose_glg"
COLLAR_VARIANTS = {"g0.75_f0.9": {"collar_gain": 0.75, "collar_share_max": 1.0, "collar_frac": 0.9},
                   "g0.5_f0.65": {"collar_gain": 0.5, "collar_share_max": 1.0, "collar_frac": 0.65},
                   "g0.5_s0.6_f0.65": {"collar_gain": 0.5, "collar_share_max": 0.6, "collar_frac": 0.65}}


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
            for trk in TRACKERS:
                run_design(bench, rows, {"tracker_fw": trk}, w, seed, cls, "nose", key_prefix=f"tr_{trk}|")
            # the collar's gain, share cap and reference cap, with the gated listening tracker whose fallback is the
            # guarded tracker (DEC-042's listening estimate, DEC-047's guard)
            for tag, rl in COLLAR_VARIANTS.items():
                run_design(bench, rows, dict(rl, tracker_fw=DESIGN_TRACKER), w, seed, cls, "collar_nose", key_prefix=f"cpg_{tag}|")
            run_design(bench, rows, {}, w, seed, cls, "collar_oracle")
        # tremor-free writing with each tracker: the false correction (the review: tremor and writing overlap)
        for trk in TRACKERS:
            key = f"tr_{trk}|h1|g1|w{w}|s{seed}|clean|nose"
            if not rows.has(key):
                su = bench.setup(w, "base")
                m = CS.run_case(su, trk, C.WPConfig(), "ET", 6.0, 0.0, seed)
                rows.put(key, _row(m, "clean", "nose", 1.0))
                log(f"[tune] clean {trk}: moved {m.get('moved_vs_clean_um', float('nan')):.0f} um")
        T = {"tracker_fw": DESIGN_TRACKER}
        for law in ("damp", "afc", "ff"):
            run_design(bench, rows, dict(T, cmg_law=law), w, seed, et3, "gt_nose", key_prefix=f"cmgg_{law}|")
        run_design(bench, rows, T, w, seed, et3, "gt_locked_nose", key_prefix="g|")
        run_design(bench, rows, {}, w, seed, et3, "gt_oracle")
        for gmm in (0.3, 1.0):
            run_design(bench, rows, dict(T, gate_margin_mm=gmm), w, seed, et8, "nose_gate", key_prefix=f"gmg{gmm}|")
        run_design(bench, rows, T, w, seed, et8, "nose", key_prefix="g|")
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
    # the tracker: lower mean ink error of the nose over ET 3 mm and PD 8 mm, unless its false correction on
    # tremor-free writing exceeds sim2j's 25 um rule by more than the other's
    trk = {}
    for tr_ in TRACKERS:
        v = [r["ink_err_um"] for cls in ("ET_moderate", "PD_severe") for r in by(f"tr_{tr_}|", cls, "nose")]
        clean = [r.get("moved_vs_clean_um", float("nan")) for r in rows if r["key"].startswith(f"tr_{tr_}|") and r["class"] == "clean"]
        trk[tr_] = {"ink_um": float(np.mean(v)) if v else float("inf"), "clean_moved_um": float(np.mean(clean)) if clean else float("nan")}
    ok = [k for k in trk if trk[k]["clean_moved_um"] <= 25.0]      # sim2j's false-correction rule (25 um)
    tracker_fw = min(ok or list(trk), key=lambda k: trk[k]["ink_um"])
    # the collar's settings: the lowest mean ink error over ET 3 mm and PD 8 mm (gated listening tracker); kept in the
    # test when it beats the nose alone on those cases (reported either way)
    cv = {}
    for tag in COLLAR_VARIANTS:
        v = [r["ink_err_um"] for cls in ("ET_moderate", "PD_severe") for r in by(f"cpg_{tag}|", cls, "collar_nose")]
        cv[tag] = float(np.mean(v)) if v else float("inf")
    best = min(cv, key=cv.get)
    nose_ink = float(np.mean([r["ink_err_um"] for cls in ("ET_moderate", "PD_severe") for r in by(f"tr_{tracker_fw}|", cls, "nose")] or [float("inf")]))
    cc = {"nose": nose_ink, "collar_nose": cv[best]}
    cg = {"tracker": trk, "collar_variants_ink_um": cv, "collar_vs_nose_ink_um": cc}
    collar_law = "ff"
    collar_gain = COLLAR_VARIANTS[best]["collar_gain"]
    collar_share_max = COLLAR_VARIANTS[best]["collar_share_max"]
    collar_frac = COLLAR_VARIANTS[best]["collar_frac"]
    # the gyroscope's law: lowest ink tremor among the causal laws (the gate against the locked tail is reported, not
    # used to pick)
    cl = {}
    for law in ("damp", "afc", "ff"):
        v = [r["tip_tremor_mm"] for r in by(f"cmgg_{law}|", "ET_moderate", "gt_nose")]
        cl[law] = float(np.mean(v)) if v else float("inf")
    cmg_law = min(cl, key=cl.get)
    # the gate's margin: the larger margin only if it keeps >= 90 % coverage and lowers the ink error
    gmr = {}
    for gmm in (0.3, 1.0):
        rr = by(f"gmg{gmm}|", "ET_severe", "nose_gate")
        gmr[gmm] = (float(np.mean([r["ink_err_um"] for r in rr])) if rr else float("inf"),
                    float(np.mean([r["coverage"] for r in rr])) if rr else 0.0)
    gate_margin = 0.3
    if gmr[1.0][1] >= 0.9 * gmr[0.3][1] and gmr[1.0][0] < gmr[0.3][0]:
        gate_margin = 1.0
    body = {"rules": {"tracker_fw": tracker_fw, "collar_law": collar_law, "collar_gain": collar_gain, "collar_alloc": "overflow",
                      "collar_share_max": collar_share_max, "collar_frac": collar_frac,
                      "collar_helps_on_tuning": cc["collar_nose"] < cc["nose"], "cmg_law": cmg_law, "gate_margin_mm": gate_margin,
                      "page_sensor": "measured (sim2j deltapen_walk: OPT-02 per-window statistics, errors add up)",
                      "tracker_note": "nose = sim2j's frozen guarded tracker (G4); nose_gl = ai2's gated listening (fallback Rev H as built); nose_glg = gated listening with the guarded fallback; chosen by ink error among those whose tremor-free writing moved <= 25 um"},
            "evidence": {"tracker_and_collar": cg, "cmg_law_tip_mm": cl, "gate_margin": {str(k): v for k, v in gmr.items()}},
            "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "chosen on tuning writer 100 and seed 300 only, before any test run",
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
    # compute budget (four shared cores): the collar and the oracles on the moderate and severe classes; the mild
    # and 9 Hz classes with the pen alone; the gate, the fine nib, the nose's own limit and the gyro tail on writer 0
    full = ("ET_moderate", "ET_severe", "PD_moderate", "PD_severe", "PD_reemergent_severe", "PD_recorded_moderate")
    plan0 = {c[0]: (["none", "nose", "collar_nose", "collar_nose_oracle"] if c[0] in full else ["none", "nose"]) for c in cls_all}
    extra0 = {"ET_severe": ["nose_gate"], "PD_severe": ["nose_gate", "collar_fine", "nose_oracle"],
              "ET_moderate": ["gt_locked_nose", "gt_nose"]}
    if quick:
        plan0 = {c[0]: ["none", "nose", "collar_nose", "collar_nose_oracle"] for c in cls_all}
        extra0 = {}
    import gc
    for w, seed in ws:
        for cls in cls_all:
            ds = list(plan0[cls[0]]) + (extra0.get(cls[0], []) if w == ws[0][0] else [])
            for dn in ds:
                try:
                    run_design(bench, rows, rules, w, seed, cls, dn)
                except Exception as e:
                    log(f"[test] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
            bench.refs.clear()                       # memory: the device-off records are only needed within a class
            gc.collect()
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
        bench.su.clear()                             # memory: one writer's set-ups at a time
        bench.refs.clear()
        gc.collect()
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
    grips = (0.5, 1.0, 2.0) if not quick else (0.5,)
    for g in grips:
        # grip 1 x: the other designs come from the tune stage's frozen rows (summary.tune_frozen_grip1); the collar's
        # same-mass comparator (collar locked, nose working) is run here at every grip
        dns = ("collar_locked_nose",) if g == 1.0 else ("collar_locked", "collar_locked_nose", "collar_nose", "gt_locked_nose", "gt_nose")
        for dn in dns:
            try:
                run_design(bench, rows, rules, w, seed, cls, dn, grip=g)
            except Exception as e:
                log(f"[grips] FAILED g{g} {dn}: {e}")
        bench.su.clear()
        bench.refs.clear()
    body = {"rows": rows.values(), "stabpen.provenance": provenance("SIMULATION (tuning writer 100, seed 300)", seeds=[seed])}
    write_json("grips.json", body)
    return body


def stage_arm(quick=False):
    rules = load_rules()
    rows = Rows("arm")
    bench = Bench()
    w, seed = 0, 200
    for cls in (("ET_moderate", "ET", 6.0, 3e-3),):
        for dn in ("none", "nose", "collar_nose"):
            try:
                run_design(bench, rows, rules, w, seed, cls, dn, hand_model="arm")
            except Exception as e:
                log(f"[arm] FAILED {cls[0]} {dn}: {e}")
        if quick:
            break
    body = {"rows": rows.values(), "stabpen.provenance": provenance("SIMULATION (articulated arm, test writer 0)", seeds=[seed])}
    write_json("arm.json", body)
    return body


def stage_real(quick=False):
    """The headline at study R's real tremor classes (the lead's request): recorded PD tremor at the pen tip (UCI spirals,
    test split) scaled to study R's representative moderate (0.24 mm) and severe (1.72 mm) amplitudes, test writers 0-1."""
    rules = load_rules()
    rows = Rows("real")
    bench = Bench()
    import gc
    ws = ((0, 200), (1, 201)) if not quick else ((0, 200),)
    for w, seed in ws:
        for cls in CLASSES_REAL:
            dns = ["none", "nose", "collar_nose", "collar_nose_oracle"] + (["collar_locked_nose"] if cls[0] == "REAL_PD_severe" else [])
            for dn in dns:
                try:
                    run_design(bench, rows, rules, w, seed, cls, dn)
                except Exception as e:
                    log(f"[real] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
            bench.refs.clear()
            gc.collect()
        bench.su.clear()
    body = {"rows": rows.values(), "classes": {c[0]: {"amp_mm": c[3] * 1e3, "kind": c[1]} for c in CLASSES_REAL},
            "stabpen.provenance": provenance("SIMULATION with REAL recorded tremor (study R's library, test split)",
                                             seeds=[s for _, s in ws])}
    write_json("real.json", body)
    return body


def stage_limits(quick=False):
    """What the collar adds on its own (the review's gate: the same pen with the collar locked and the nose working)
    and the nose's own limit with perfect knowledge, on the test writers with the frozen rules (comparators added after
    the main test campaign; no rule changed).  Rows go to the test rows."""
    rules = load_rules()
    rows = Rows("test")
    bench = Bench()
    import gc
    ws = ((0, 200), (1, 201)) if not quick else ((0, 200),)
    cls_l = [c for c in CLASSES if c[0] in ("ET_moderate", "PD_moderate", "ET_severe", "PD_severe", "PD_reemergent_severe")]
    for w, seed in ws:
        for cls in cls_l:
            for dn in ("collar_locked_nose", "nose_oracle"):
                try:
                    run_design(bench, rows, rules, w, seed, cls, dn)
                except Exception as e:
                    log(f"[limits] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
            bench.refs.clear()
            gc.collect()
        bench.su.clear()
        gc.collect()
    body = {"rows": rows.values(), "rules": rules,
            "stabpen.provenance": provenance("SIMULATION (test writers and seeds; rules frozen before)", seeds=[s for _, s in ws])}
    write_json("test.json", body)
    return body


def stage_light(quick=False):
    """The review's design point in the simulator: the collar with a light inner pen (24 g) instead of the 87 g Rev J
    pen, on the test writers with the frozen rules (added after the main campaign; no rule changed): the collar locked,
    locked with the nose working (the same-mass comparator), the collar with the Rev J nose, and the collar with a
    +-1 mm fine nib (the compact design).  Rows go to wholepen/build/rows/light.jsonl."""
    rules = load_rules()
    rows = Rows("light")
    bench = Bench()
    import gc
    ws = ((0, 200), (1, 201)) if not quick else ((0, 200),)
    cls_l = [c for c in CLASSES if c[0] in ("ET_moderate", "PD_severe")]
    for w, seed in ws:
        for cls in cls_l:
            for dn in ("light_locked", "light_locked_nose", "light_nose", "light_fine", "light_nose_oracle"):
                try:
                    run_design(bench, rows, rules, w, seed, cls, dn)
                except Exception as e:
                    log(f"[light] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
            bench.refs.clear()
            gc.collect()
        bench.su.clear()
        gc.collect()
    body = {"rows": rows.values(), "pen": asdict(pens()["collar_light"]) if hasattr(pens()["collar_light"], "__dataclass_fields__") else None,
            "stabpen.provenance": provenance("SIMULATION (test writers and seeds; rules frozen before)", seeds=[s for _, s in ws])}
    write_json("light.json", body)
    return body


LIGHT_FINE_VARIANTS = {"g1.0_s1.0_f0.9": {"lf_gain": 1.0, "lf_share_max": 1.0, "lf_frac": 0.9},
                       "g0.75_s1.0_f0.9": {"lf_gain": 0.75, "lf_share_max": 1.0, "lf_frac": 0.9}}


def stage_light2(quick=False):
    """The compact design's law (collar + +-1 mm nib, light inner pen) re-tuned on tuning writer 100, seed 300, ET 3 mm
    (the main rules were chosen for the collar with Rev J's nose and cap the collar at gain 0.5, share 0.6), frozen in
    results/wholepen/rules_light.json, then run on the test writers (ET 3 mm, PD 8 mm)."""
    rules = load_rules()
    bench = Bench()
    import gc
    tr_rows = Rows("light_tune")
    cls_t = next(c for c in CLASSES if c[0] == "ET_moderate")
    res = {}
    for tag, lf in LIGHT_FINE_VARIANTS.items():
        rl = dict(rules, **lf)
        r = run_design(bench, tr_rows, rl, 100, 300, cls_t, "light_fine_t", key_prefix=f"lf_{tag}|")
        res[tag] = {"ink_um": r.get("ink_err_um"), "tip_mm": r.get("tip_tremor_mm"), "coverage": r.get("coverage"),
                    "pivot_peak_rad": r.get("pivot_peak_rad")}
    ok = {k: v for k, v in res.items() if (v.get("coverage") or 0) >= 0.9 * max((x.get("coverage") or 0) for x in res.values())}
    best = min(ok, key=lambda k: ok[k]["ink_um"] if ok[k]["ink_um"] is not None else float("inf"))
    body = {"rules": LIGHT_FINE_VARIANTS[best], "chosen": best, "evidence": res,
            "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "chosen on tuning writer 100, seed 300, ET 3 mm only, by ink error among variants keeping >= 90 % of the "
                    "best coverage, before the test runs of light_fine_t",
            "stabpen.provenance": provenance("SIMULATION (tuning writer) -> frozen rule for the light collar with a fine nib", seeds=[300])}
    write_json("rules_light.json", body)
    log(f"[light2] frozen {best}: {res}")
    bench.su.clear()
    gc.collect()
    rows = Rows("light")
    rl = dict(rules, **LIGHT_FINE_VARIANTS[best])
    ws = ((0, 200), (1, 201)) if not quick else ((0, 200),)
    for w, seed in ws:
        for cls in [c for c in CLASSES if c[0] in ("ET_moderate", "PD_severe")]:
            for dn in ("light_locked", "light_fine_t"):
                try:
                    run_design(bench, rows, rl, w, seed, cls, dn)
                except Exception as e:
                    log(f"[light2] FAILED w{w} {cls[0]} {dn}: {e}\n{traceback.format_exc()}")
            bench.refs.clear()
            gc.collect()
        bench.su.clear()
        gc.collect()
    body = {"rows": rows.values(), "rules_light": LIGHT_FINE_VARIANTS[best],
            "stabpen.provenance": provenance("SIMULATION (test writers and seeds; rules frozen before)", seeds=[s for _, s in ws])}
    write_json("light.json", body)
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


STAGES = ["targets", "realdata", "grip", "calc", "optimise", "verify", "tune", "freeze", "test", "limits", "light", "light2",
          "real", "grips", "arm", "summary", "figures"]
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
