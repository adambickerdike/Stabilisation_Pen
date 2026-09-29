r"""One command for the Rev J closed-loop study in sim2 (SIMULATION):

    python3 -m sim2j.run_study --stages et            (one stage; rows are cached in sim2j/build and resumed)
    python3 -m sim2j.run_study --quick --stages et    (a smoke run: one writer, one cell)

Stages (each writes results/sim2j/<stage>.json with stabpen.provenance; rows are cached in sim2j/build/<stage>_rows.json
so a stopped run resumes where it stopped):
  tune        guard and detector rule on the tuning writers 100-103, seed 300 -> results/sim2j/rules.json (freeze)
  et          essential tremor, test writers 0-5, seeds 200-203 (two per writer and cell), 4/8/12 Hz x 0.3/1/2 mm
  writer_cmp  tremor separation on the v1 and the v2 writers (test writers, one seed)
  verify      overlap with round 1: nose2's autowrite (HW1) and the drive study's tracing (HW1-D)
  guided      dysgraphia tracing, PD 'write big' loops, dyslexia lead-through
  autowrite   autowrite of a known text (nose2 planner) with 0 / 1 / 2 / 3 mm tremor, and severe tremor
  rl_train    PPO in the Rev J environment (training writers 1000+ only)
  rl_select   checkpoint selection on the tuning writers and seeds (rule in rules.json)
  rl_test     the selected policy on the test writers and seeds
  dr          the main controllers over the domain randomisation (24 draws)
  arm         the 'arm' hand model subset
  dt          25 us step check of a subset
  power       refill-spring sensitivity of the nose's coil power (static ball load)
  report      figures (+ CSV twins), samples.json, the viewer replay
Every number is labelled SIM or CALC on synthetic writers and tremor: sim2 ranks concepts (COU-1) until EXP-V01/V02/V04
calibrate it and EXP-V05 validates it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from typing import Callable, Dict, List, Optional

import numpy as np

from . import BUILD, RESULTS, ROOT, TEST_SEEDS, TEST_WRITERS, TUNE_SEEDS, TUNE_WRITERS, VERSION

EVIDENCE = ("SIMULATION (sim2, MuJoCo 3.6; synthetic writers and tremor; Rev J PROPOSED DESIGN parameters). sim2 ranks "
            "concepts (context of use COU-1) until EXP-V01/V02/V04 calibrate and EXP-V05 validates it; not evidence of "
            "benefit to people")


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ------------------------------------------------------------------------------------------------ caching
class Rows:
    """Rows cached in sim2j/build/<name>_rows.json, keyed; a stopped stage resumes."""

    def __init__(self, name: str, fresh: bool = False):
        os.makedirs(BUILD, exist_ok=True)
        self.path = os.path.join(BUILD, f"{name}_rows.json")
        self.rows: Dict[str, Dict] = {}
        if not fresh and os.path.exists(self.path):
            try:
                self.rows = json.load(open(self.path))
            except Exception:
                self.rows = {}
        self.t_save = time.time()

    def has(self, key: str) -> bool:
        return key in self.rows

    def get(self, key: str) -> Optional[Dict]:
        return self.rows.get(key)

    def put(self, key: str, row: Dict, force_save: bool = False):
        self.rows[key] = _clean(row)
        if force_save or time.time() - self.t_save > 20.0:
            self.save()

    def save(self):
        tmp = self.path + ".tmp"
        json.dump(self.rows, open(tmp, "w"), default=_default)
        os.replace(tmp, self.path)
        self.t_save = time.time()

    def values(self) -> List[Dict]:
        return list(self.rows.values())


def _default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def _clean(row: Dict) -> Dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def pen_source_meta() -> Dict:
    from . import revj as RJ
    return RJ.lead()["meta"] if RJ.default_source() == "revJ" else {"source": "round1"}


def write_result(name: str, body: Dict, seeds=None, extra: Optional[Dict] = None) -> str:
    from stabpen import provenance as PV
    md = PV.metadata(EVIDENCE, seeds=seeds, extra=dict({"package": VERSION, "stage": name,
                                                         "pen_source": pen_source_meta()}, **(extra or {})))
    out = {"stabpen.provenance": md}
    out.update(body)
    path = os.path.join(RESULTS, f"{name}.json")
    PV.write_json(path, out)
    log(f"[{name}] wrote {os.path.relpath(path, ROOT)}")
    return path


def agg(rows: List[Dict], keys=("ink_err_um", "letters_read", "words_app"), by=("ctl",)) -> Dict:
    """Mean (and n) of each key per group."""
    groups: Dict[str, List[Dict]] = {}
    for r in rows:
        g = "|".join(str(r.get(b)) for b in by)
        groups.setdefault(g, []).append(r)
    out = {}
    for g, rs in groups.items():
        d = {"n": len(rs)}
        for k in keys:
            v = [r.get(k) for r in rs if isinstance(r.get(k), (int, float)) and r.get(k) is not None
                 and not (isinstance(r.get(k), float) and math.isnan(r.get(k)))]
            if v:
                d[k] = float(np.mean(v))
                d[k + "_sd"] = float(np.std(v))
        out[g] = d
    return out


# ------------------------------------------------------------------------------------------------ tune
def stage_tune(quick: bool = False) -> None:
    from . import tuning as TU
    t0 = time.time()
    if os.path.exists(os.path.join(BUILD, "tune_guard.json")) and not quick:
        res = json.load(open(os.path.join(BUILD, "tune_guard.json")))
    else:
        res = TU.tune_guard(writers=TUNE_WRITERS[:1] if quick else TUNE_WRITERS,
                            f0s=(8.0,) if quick else (6.0, 8.0, 10.0),
                            amps=(1e-3,) if quick else (0.3e-3, 1e-3, 2e-3), log=log)
    if quick:
        log(f"[tune] quick: chosen {res['chosen']} {res['summary']}")
        return
    TU.freeze(res, extra={"tuning_rows_file": "sim2j/build/tune_guard_rows.json",
                          "tuning_wall_s": res.get("elapsed_s")})
    log(f"[tune] frozen {res['chosen']} in {time.time() - t0:.0f} s")


# ------------------------------------------------------------------------------------------------ ET
ET_F0 = (4.0, 8.0, 12.0)
ET_AMP = (0.3e-3, 1.0e-3, 2.0e-3)
ET_FULL = ("none", "nose", "nose_wheel", "oracle")        # 12 cases per cell (6 writers x 2 seeds)
ET_HALF = ("nose_wheel_ec",)                              # 6 cases per cell (the first seed of each writer)
ET_NOGUARD_AMP = (1.0e-3,)


def et_seeds(w: int) -> List[int]:
    """Two of the test seeds per writer, rotating (each seed three times per cell)."""
    return [TEST_SEEDS[w % 4], TEST_SEEDS[(w + 2) % 4]]


def stage_et(quick: bool = False, controllers_extra: Optional[Dict] = None, rows_name: str = "et",
             writers=TEST_WRITERS, include_model_based: bool = True, first_seed_only: bool = False) -> Dict:
    """The ET test grid.  controllers_extra: {'rl': policy} adds RL cases."""
    from . import et as ET
    rows = Rows(rows_name)
    pens = ET.PenModels()
    f0s, amps = (ET_F0, ET_AMP) if not quick else ((8.0,), (1.0e-3,))
    ws = writers if not quick else writers[:1]
    t0 = time.time()
    for w in ws:
        setups = {}

        def su_for(pen):
            if pen not in setups:
                setups[pen] = ET.WriterSetup(w, pens, pen=pen, log=log)
            return setups[pen]
        seeds = et_seeds(w) if not (quick or first_seed_only) else et_seeds(w)[:1]
        # tremor-free writing (false correction against the device-off pen with the same seed)
        clean_ctl = (list(ET_FULL[1:3]) + list(ET_HALF) + ["nose_noguard"] if include_model_based else [])
        clean_ctl += list((controllers_extra or {}).keys())
        for si, seed in enumerate(seeds):
            for ctl in clean_ctl:
                key = f"clean|{w}|{seed}|{ctl}"
                if rows.has(key) or (ctl in ET_HALF + ("nose_noguard",) and si > 0):
                    continue
                pen = ET.PEN_OF.get(ctl, "base")
                su = su_for(pen)
                pol = (controllers_extra or {}).get(ctl)
                m = ET.run_case(su, "rl" if pol is not None else ctl, 0.0, 0.0, seed, ref_none=su.clean_ref(seed),
                                policy=pol)
                m.update({"kind": "clean", "ctl": ctl})
                rows.put(key, m)
                log(f"[{rows_name}] w{w} s{seed} clean {ctl}: moved {m['moved_vs_clean_um']:.1f} um, "
                    f"P {m['P_total_W']:.2f} W")
        for f0 in f0s:
            for amp in amps:
                for si, seed in enumerate(seeds):
                    ref = {}
                    for pen in ("base", "endcap"):
                        need = [c for c in (list(ET_FULL) + list(ET_HALF) + ["nose_noguard"] + list((controllers_extra or {}).keys()))
                                if ET.PEN_OF.get(c, "base") == pen]
                        if not need:
                            continue
                        todo = []
                        for ctl in need:
                            if ctl in ("none",) and pen != "base":
                                continue
                            if ctl in ET_FULL and not include_model_based:
                                continue
                            if ctl in ET_HALF and (si > 0 or not include_model_based):
                                continue
                            if ctl == "nose_noguard" and (si > 0 or amp not in ET_NOGUARD_AMP or not include_model_based):
                                continue
                            key = f"{f0:g}|{amp * 1e3:g}|{w}|{seed}|{ctl}"
                            if not rows.has(key):
                                todo.append((ctl, key))
                        if not todo:
                            continue
                        su = su_for(pen)
                        rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
                        r_none = rn.pop("_r")
                        rn.update({"kind": "tremor", "ctl": "none" if pen == "base" else "none_endcap_pen"})
                        k_none = f"{f0:g}|{amp * 1e3:g}|{w}|{seed}|{'none' if pen == 'base' else 'none_endcap_pen'}"
                        rows.put(k_none, rn)
                        for ctl, key in todo:
                            if ctl == "none":
                                continue
                            pol = (controllers_extra or {}).get(ctl)
                            m = ET.run_case(su, "rl" if pol is not None else ctl, f0, amp, seed, ref_none=r_none,
                                            policy=pol)
                            m.update({"kind": "tremor", "ctl": ctl, "none_ink_err_um": rn["ink_err_um"],
                                      "ratio": m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)})
                            rows.put(key, m)
                    done = [r for k, r in rows.rows.items() if k.startswith(f"{f0:g}|{amp * 1e3:g}|{w}|{seed}|")]
                    log(f"[{rows_name}] w{w} s{seed} {f0:g} Hz {amp * 1e3:g} mm: " + ", ".join(
                        f"{r['ctl']} {r['ink_err_um']:.0f}" for r in done) + f"  ({time.time() - t0:.0f} s)")
        rows.save()
    rows.save()
    return summarise_et(rows.values(), rows_name, quick)


def summarise_et(rows: List[Dict], name: str = "et", quick: bool = False) -> Dict:
    tr = [r for r in rows if r.get("kind") == "tremor"]
    cl = [r for r in rows if r.get("kind") == "clean"]
    keys = ("ink_err_um", "ratio", "letters_read", "words_app", "ink_err_intended_um", "device_share", "felt_rms_N",
            "felt_p95_N", "P_total_W", "P_nose_W", "P_wheel_W", "P_endcap_W", "battery_h", "wheel_F_rms_N",
            "wheel_slide_share", "f_est_median", "f_at_bound_share", "guard_events")
    by_cell = agg(tr, keys, by=("f0", "amp_mm", "ctl"))
    by_amp = agg(tr, keys, by=("amp_mm", "ctl"))
    by_ctl = agg(tr, keys, by=("ctl",))
    clean = agg(cl, ("moved_vs_clean_um", "P_total_W", "P_nose_W", "letters_read", "words_app"), by=("ctl",))
    clean_max = {}
    for r in cl:
        clean_max[r["ctl"]] = max(clean_max.get(r["ctl"], 0.0), float(r.get("moved_vs_clean_um") or 0.0))
    body = {"what": "Essential tremor with the Rev J pen (H1 hand, v2 writers, 'return library'), test writers 0-5, "
                    "seeds 200-203 (two per writer and cell), tremor 4/8/12 Hz x 0.3/1/2 mm (stabpen tremor model)",
            "labels": {"ink_err_um": "SIM: rms distance of the in-contact ink to the writer's clean-ink letters "
                                     "(letter-wise nearest point)",
                       "ratio": "SIM: ink error / ink error of the device-off pen in the same case",
                       "letters_read": "SIM: share of letters the app's recogniser reads as the intended letter",
                       "words_app": "SIM: share of words the app reads correctly after its autocorrect",
                       "device_share": "SIM: share of the ink motion that comes from the device (authorship)",
                       "felt_rms_N": "SIM: rms change of the grip force on the hand against the device-off run",
                       "P_total_W": "CALC on SIM: mean electrical power incl. 0.077 W electronics",
                       "moved_vs_clean_um": "SIM: false correction, rms ink moved on tremor-free writing against the "
                                            "device-off pen with the same seed (rule <= 25 um)"},
            "by_cell": by_cell, "by_amp": by_amp, "by_ctl": by_ctl, "clean": clean, "clean_max_um": clean_max,
            "n_rows": len(rows), "quick": quick}
    if not quick:
        write_result(name, body, seeds=list(TEST_SEEDS))
    return body


# ------------------------------------------------------------------------------------------------ writers
def stage_writers(quick: bool = False) -> Dict:
    """Writer model v2 against the literature targets and the v1 writers (CALC on synthetic writing): held-out fitting
    writers 1010-1019 (never used in the fit, which used 1000-1009) and the test writers 0-5, the ET sentence."""
    from . import writers as WV
    from .et import ET_TEXT
    out = {"targets": WV.TARGETS, "fit": json.load(open(os.path.join(RESULTS, "writer_fit.json"))).get("chosen")}
    pops = {"v2_heldout_1010_1019": ("v2", range(1010, 1020 if not quick else 1012)),
            "v2_test_0_5": ("v2", TEST_WRITERS if not quick else TEST_WRITERS[:2]),
            "v1_test_0_5": ("v1", TEST_WRITERS if not quick else TEST_WRITERS[:2]),
            "v1_heldout_1010_1019": ("v1", range(1010, 1020 if not quick else 1012))}
    kin = {}
    for name, (ver, ws) in pops.items():
        written = [WV.writer(w, ver).write(WV.ET_SENTENCE, dt=1e-3, seed=2000 + w) for w in ws]
        k = WV.kinematics(WV.written_items(written))
        k["writers"] = list(ws)
        k["fit_loss"] = WV.fit_loss(k)
        kin[name] = k
        log(f"[writers] {name}: speed {k['speed_mm_s']['mean']:.1f} mm/s, 8-12 Hz share {k['spectrum']['share_8_12']:.3f}, "
            f"f50/f90 {k['spectrum']['f50']:.2f}/{k['spectrum']['f90']:.2f} Hz, stroke {k['stroke_ms']['median']:.0f} ms, "
            f"beta {k['beta']['mean']:.3f}")
    out["kinematics"] = kin
    out["labels"] = {"speed_mm_s": "CALC: mean pen-down speed of the intended path (target LIT CON-20 about 30 mm/s)",
                     "share_8_12": "CALC: share of pen-down velocity energy at 8-12 Hz (target LIT CON-25 1.3-1.7 %)",
                     "beta": "CALC: fitted exponent of v = K kappa^-beta ... reported as the slope of log(v kappa) on "
                             "log(kappa) (2/3 law: LIT CON-27)"}
    if not quick:
        write_result("writers", out)
    return out


# ------------------------------------------------------------------------------------------------ writer comparison
def stage_writer_cmp(quick: bool = False) -> Dict:
    """How tremor separation changes with the writer refit: the same pen, tremor and controllers on the v1 and the v2
    writers (test writers 0-5, the first test seed of each writer, 8 Hz and 12 Hz x 1 mm, and tremor-free writing)."""
    from . import et as ET
    rows = Rows("writer_cmp")
    pens = ET.PenModels()
    ctls = ("nose", "nose_noguard", "nose_gl", "oracle")
    ws = TEST_WRITERS if not quick else TEST_WRITERS[:1]
    for ver in ("v1", "v2"):
        for w in ws:
            seed = et_seeds(w)[0]
            su = None
            for ctl in ctls[:3]:
                key = f"{ver}|clean|{w}|{seed}|{ctl}"
                if rows.has(key):
                    continue
                su = su or ET.WriterSetup(w, pens, version=ver, log=log)
                m = ET.run_case(su, ctl, 0.0, 0.0, seed, ref_none=su.clean_ref(seed))
                m.update({"kind": "clean", "ctl": ctl, "writer_model": ver})
                rows.put(key, m)
            for f0 in (8.0, 12.0):
                amp = 1.0e-3
                keys = [f"{ver}|{f0:g}|{w}|{seed}|{c}" for c in ("none",) + ctls]
                if all(rows.has(k) for k in keys):
                    continue
                su = su or ET.WriterSetup(w, pens, version=ver, log=log)
                rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
                r_none = rn.pop("_r")
                rn.update({"kind": "tremor", "ctl": "none", "writer_model": ver})
                rows.put(keys[0], rn)
                for ctl, key in zip(ctls, keys[1:]):
                    m = ET.run_case(su, ctl, f0, amp, seed, ref_none=r_none)
                    m.update({"kind": "tremor", "ctl": ctl, "writer_model": ver,
                              "ratio": m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)})
                    rows.put(key, m)
                log(f"[writer_cmp] {ver} w{w} {f0:g} Hz: none {rn['ink_err_um']:.0f} um; " + ", ".join(
                    f"{c} {rows.get(k)['ratio']:.3f}" for c, k in zip(ctls, keys[1:])))
            rows.save()
    rows.save()
    R = rows.values()
    keys = ("ink_err_um", "ratio", "letters_read", "words_app", "f_est_median", "f_at_bound_share", "moved_vs_clean_um")
    body = {"what": "the same pen, tremor and controllers on the v1 (aiguide) and v2 (refitted) writers",
            "by_model_ctl_f0": agg([r for r in R if r["kind"] == "tremor"], keys, by=("writer_model", "f0", "ctl")),
            "by_model_ctl": agg([r for r in R if r["kind"] == "tremor"], keys, by=("writer_model", "ctl")),
            "clean": agg([r for r in R if r["kind"] == "clean"], keys, by=("writer_model", "ctl"))}
    if not quick:
        write_result("writer_cmp", body, seeds=list(TEST_SEEDS))
    return body


# ------------------------------------------------------------------------------------------------ verify
def stage_verify(quick: bool = False) -> Dict:
    """Overlap with round 1.  (a) nose2's autowrite (HW1, 2-D) of 'return library books by friday' at 2.5 mm, v1
    writers, test writers 0-5, seed 200, no tremor and 8 Hz x 1 mm, on the C1S pen without the heel drive (study N's
    pen: round-1 assembly) and on the lead's Rev J pen.  (b) the drive study's tracing (HW1-D, task a) with v1
    dysgraphia-like learners, none / wheel steer-only / wheel + nose."""
    from . import revj as RJ
    from . import verify as VF
    from . import guided as GD
    rows = Rows("verify")
    ws = TEST_WRITERS if not quick else TEST_WRITERS[:1]
    pms = {"round1_C1S": RJ.build(RJ.config(heel=False, dt=50e-6, source="round1")),
           "revJ": RJ.build(RJ.config(heel=True, dt=50e-6))}
    for pen, pm in pms.items():
        for w in ws:
            for amp in (0.0, 1.0e-3):
                key = f"aw|{pen}|{w}|{amp * 1e3:g}"
                if rows.has(key):
                    continue
                res = VF.autowrite_case(w, 200, 8.0, amp, pm)
                if isinstance(res, dict):
                    rows.put(key, dict(res, pen=pen, task="autowrite"))
                    continue
                m, r, ac = res
                m.update({"pen": pen, "task": "autowrite"})
                rows.put(key, m)
                log(f"[verify] autowrite {pen} w{w} {amp * 1e3:g} mm: ink {m['ink_err_um']:.0f} um, letters "
                    f"{m['letters_read']:.2f}, words {m['words_app']:.2f}, P_nose {m['P_nose_W']:.2f} W")
    pm = pms["revJ"]
    for w in ws:
        gc = None
        for ctl in ("none", "wheel", "wheel_nose"):
            key = f"tr|{w}|{ctl}"
            if rows.has(key):
                continue
            gc = gc or GD.GuidedCase(w, 200, "dysgraphia", pm, version="v1", log=log)
            m = GD.run_tracing(gc, ctl)
            m.update({"task": "tracing_v1", "pen": "revJ"})
            rows.put(key, m)
            log(f"[verify] tracing v1 w{w} {ctl}: target {m['target_err_um']:.0f} um, letters {m['letters_read']:.2f}, "
                f"words {m['words_app']:.2f}, coverage {m['coverage']:.2f}")
        rows.save()
    rows.save()
    R = rows.values()
    body = {"autowrite": agg([r for r in R if r.get("task") == "autowrite" and r.get("plan_ok", True)],
                             ("ink_err_um", "letters_read", "words_app", "P_nose_W", "P_total_W", "q_max_mm", "at_reach"),
                             by=("pen", "amp_mm")),
            "tracing_v1": agg([r for r in R if r.get("task") == "tracing_v1"],
                              ("target_err_um", "letters_read", "words_app", "coverage", "device_share",
                               "error_letters_read_as_target", "wheel_F_rms_N"), by=("ctl",)),
            "round1": {"nose2_autowrite_revJ_2p5mm": VF.nose2_reference()["table"],
                       "drive_practice": "results/drive/tasks.json practice.rows (task a)"}}
    if not quick:
        write_result("verify", body, seeds=[200])
    return body


# ------------------------------------------------------------------------------------------------ guided tasks
def stage_guided(quick: bool = False) -> Dict:
    """Dysgraphia tracing, PD 'write big' loops and dyslexia lead-through (v2 learners, the lead's Rev J pen)."""
    from . import guided as GD
    from . import revj as RJ
    rows = Rows("guided")
    pm = RJ.build(RJ.config(heel=True, dt=50e-6))
    ws = TEST_WRITERS if not quick else TEST_WRITERS[:1]
    for w in ws:
        gc = None
        for ctl in GD.TRACING_CTL:
            key = f"tracing|{w}|200|{ctl}"
            if rows.has(key):
                continue
            gc = gc or GD.GuidedCase(w, 200, "dysgraphia", pm, log=log)
            m = GD.run_tracing(gc, ctl)
            m.update({"task": "tracing"})
            rows.put(key, m)
            log(f"[guided] tracing w{w} {ctl}: target {m['target_err_um']:.0f} um, letters {m['letters_read']:.2f}, "
                f"words {m['words_app']:.2f}, coverage {m['coverage']:.2f}, P {m['P_total_W']:.2f} W")
        rows.save()
    for seed in (TEST_SEEDS if not quick else TEST_SEEDS[:1]):
        for hand in GD.HANDS:
            lc = None
            for ctl in GD.LOOPS_CTL:
                key = f"loops|{hand}|{seed}|{ctl}"
                if rows.has(key):
                    continue
                lc = lc or GD.LoopsCase(seed, hand)
                m = GD.run_loops(lc, ctl)
                m.update({"task": "loops"})
                rows.put(key, m)
                log(f"[guided] loops {hand} s{seed} {ctl}: height ratio {m['loop_height_ratio']:.2f}, last "
                    f"{m['last_loop_ratio']:.2f}, ink-template {m['ink_to_template_rms_mm']:.2f} mm")
        rows.save()
    for w in ws:
        lc = None
        r0 = None
        for ctl in ("writer_alone", "relaxed_none", "lead", "lead_nose"):
            key = f"lead|{w}|200|{ctl}"
            if rows.has(key) and ctl != "relaxed_none":
                continue
            lc = lc or GD.LeadCase(w, 200, pm, words=GD.LEAD_WORDS, log=log)
            if ctl == "relaxed_none":
                if r0 is None:
                    m = GD.run_lead(lc, ctl, keep=True)
                    r0 = m.pop("_r")
                    if not rows.has(key):
                        rows.put(key, dict(m, task="lead"))
                continue
            m = GD.run_lead(lc, ctl, ref=r0)
            m.update({"task": "lead"})
            rows.put(key, m)
            log(f"[guided] lead w{w} {ctl}: target {m.get('target_err_um', float('nan')):.0f} um, letters "
                f"{m['letters_read']:.2f}, words {m['words_app']:.2f}, coverage {m.get('coverage', float('nan')):.2f}")
        rows.save()
    rows.save()
    R = rows.values()
    body = {"tracing": agg([r for r in R if r["task"] == "tracing"],
                           ("target_err_um", "letters_read", "words_app", "coverage", "error_letters_read_as_target",
                            "device_share", "felt_rms_N", "wheel_F_rms_N", "wheel_slide_share", "P_total_W"), by=("ctl",)),
            "loops": agg([r for r in R if r["task"] == "loops"],
                         ("loop_height_ratio", "last_loop_ratio", "ink_to_template_rms_mm", "device_share", "felt_rms_N",
                          "wheel_F_rms_N", "P_total_W"), by=("hand", "ctl")),
            "lead": agg([r for r in R if r["task"] == "lead"],
                        ("target_err_um", "letters_read", "words_app", "coverage", "device_share", "felt_rms_N",
                         "wheel_F_rms_N", "wheel_slide_share", "P_total_W", "pen_speed_mm_s", "n_strokes_done"),
                        by=("ctl",))}
    if not quick:
        write_result("guided", body, seeds=list(TEST_SEEDS))
    return body


# ------------------------------------------------------------------------------------------------ autowrite / severe
def stage_autowrite(quick: bool = False) -> Dict:
    """Autowrite of a known text (nose2 planner, pen lift) by the Rev J pen, v2 test writers' style at 2.5 mm x-height
    (DEC-039 sizes), 8 Hz tremor of 0 / 1 / 2 / 3 mm, and severe tremor (2 and 3 mm, 5 and 8 Hz) with the writer
    writing through the tremor (none, nose, nose + wheel, oracle) for comparison."""
    from . import et as ET
    from . import revj as RJ
    from . import stepper as ST
    from . import tasks as TK
    from .firmware import FWConfig
    rows = Rows("autowrite")
    pm = RJ.build(RJ.config(heel=True, dt=50e-6))
    ws = TEST_WRITERS if not quick else TEST_WRITERS[:1]
    for w in ws:
        seed = et_seeds(w)[0]
        ac = None
        for amp in (0.0, 1.0e-3, 2.0e-3, 3.0e-3):
            for f0 in ((8.0,) if amp < 2e-3 else (5.0, 8.0)):
                key = f"aw|{w}|{seed}|{f0:g}|{amp * 1e3:g}"
                if rows.has(key):
                    continue
                ac = ac or TK.AutowriteCase(w, h_mm=2.5, version="v2")
                if not ac.ok:
                    rows.put(key, {"w": w, "plan_ok": False, "amp_mm": amp * 1e3, "f0": f0})
                    continue
                scn = ac.scenario(f0, amp, seed)
                fw = FWConfig(nose="autowrite", pen_lift="plan", seed=seed, reach=pm.cfg.geom.travel)
                t0 = time.time()
                r = ST.run(pm, scn, fw, ac.task(), seed=seed)
                m = ac.metrics(r)
                m.update({"w": w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "plan_ok": True, "ctl": "autowrite",
                          "task": "autowrite", "wall_s": time.time() - t0})
                rows.put(key, m)
                log(f"[autowrite] w{w} {f0:g} Hz {amp * 1e3:g} mm: ink {m['ink_err_um']:.0f} um, letters "
                    f"{m['letters_read']:.2f}, words {m['words_app']:.2f}, {m['letters_per_s']:.2f} letters/s, "
                    f"P {m['P_total_W']:.2f} W")
        rows.save()
    pens = ET.PenModels()
    for w in ws:
        seed = et_seeds(w)[0]
        su = None
        for amp in (2.0e-3, 3.0e-3):
            for f0 in (5.0, 8.0):
                keys = {c: f"sev|{w}|{seed}|{f0:g}|{amp * 1e3:g}|{c}" for c in ("none", "nose", "nose_wheel", "oracle")}
                if all(rows.has(k) for k in keys.values()):
                    continue
                su = su or ET.WriterSetup(w, pens, log=log)
                rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
                r_none = rn.pop("_r")
                rows.put(keys["none"], dict(rn, task="severe", ctl="none"))
                for c in ("nose", "nose_wheel", "oracle"):
                    m = ET.run_case(su, c, f0, amp, seed, ref_none=r_none)
                    m.update({"task": "severe", "ctl": c, "ratio": m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)})
                    rows.put(keys[c], m)
                log(f"[severe] w{w} {f0:g} Hz {amp * 1e3:g} mm: none {rn['ink_err_um']:.0f} um, letters "
                    f"{rn['letters_read']:.2f}; " + ", ".join(f"{c} {rows.get(keys[c])['ink_err_um']:.0f} um "
                                                             f"{rows.get(keys[c])['letters_read']:.2f}" for c in ("nose", "nose_wheel", "oracle")))
        rows.save()
    rows.save()
    R = rows.values()
    keys = ("ink_err_um", "letters_read", "words_app", "letters_per_s", "P_total_W", "P_nose_W", "battery_h", "q_max_mm",
            "at_reach", "ratio", "device_share", "felt_rms_N")
    body = {"autowrite": agg([r for r in R if r.get("task") == "autowrite" and r.get("plan_ok")], keys,
                             by=("f0", "amp_mm")),
            "autowrite_plan_fail": sum(1 for r in R if r.get("task") == "autowrite" and not r.get("plan_ok")),
            "severe": agg([r for r in R if r.get("task") == "severe"], keys, by=("f0", "amp_mm", "ctl")),
            "labels": {"ink_err_um": "SIM: autowrite - rms distance of the ink to the planned letters (nose2 metric); "
                                     "severe - to the writer's clean-ink letters",
                       "letters_per_s": "SIM: letters written per second of the text"}}
    if not quick:
        write_result("autowrite", body, seeds=list(TEST_SEEDS))
    return body


# ------------------------------------------------------------------------------------------------ DR population
def stage_dr(quick: bool = False, n: int = 24) -> Dict:
    """The main controllers over sim2's domain randomisation mapped onto Rev J (rl.sample_dr: hand, grip, tremor,
    friction, sensors, tolerances, posture and the lead's Rev J factors); test writers 0-5 in turn, test seeds; no
    re-adaptation per draw (the nominal pen's adapted hand path; the clean reference is re-run on the drawn pen)."""
    from . import et as ET
    from . import rl as RL
    from . import revj as RJ
    rows = Rows("dr")
    rng = np.random.default_rng(4242)
    draws = [RL.sample_dr(rng) for _ in range(n)]
    pens_nom = ET.PenModels()
    ctls = ("none", "nose", "nose_wheel", "oracle")
    for i, p in enumerate(draws[: (2 if quick else n)]):
        w = TEST_WRITERS[i % len(TEST_WRITERS)]
        seed = TEST_SEEDS[i % len(TEST_SEEDS)]
        keys = {c: f"{i}|{c}" for c in ctls + ("clean_nose",)}
        if all(rows.has(k) for k in keys.values()):
            continue
        su_nom = ET.WriterSetup(w, pens_nom, log=log)
        cfg = RL.config_from_dr(p, dt=50e-6)
        pm = RJ.build(cfg)

        class _Pens:
            def get(self, pen="base"):
                return pm
        su = ET.WriterSetup.__new__(ET.WriterSetup)
        su.w, su.version, su.text, su.pen, su.pre_s = w, "v2", ET.ET_TEXT, "base", su_nom.pre_s
        su.pm = pm
        su.case = su_nom.case
        su.adapt_hist = su_nom.adapt_hist
        su.clean_runs = {}
        su.clean = ET.ST.run(pm, su.case.scenario(), ET.controller("none"))
        su.ref_polys = ET.clean_letters(su.case.written, su.clean)
        f0, amp = float(p["f0"]), float(np.clip(p["amp"], 0.3e-3, 2.0e-3))
        rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
        r_none = rn.pop("_r")
        rows.put(keys["none"], dict(rn, draw=i, dr=p, ctl="none"))
        for c in ctls[1:]:
            m = ET.run_case(su, c, f0, amp, seed, ref_none=r_none)
            m.update({"draw": i, "ctl": c, "ratio": m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)})
            rows.put(keys[c], m)
        mc = ET.run_case(su, "nose", 0.0, 0.0, seed, ref_none=su.clean_ref(seed))
        rows.put(keys["clean_nose"], dict(mc, draw=i, ctl="clean_nose"))
        log(f"[dr] draw {i} w{w} {f0:.1f} Hz {amp * 1e3:.2f} mm: none {rn['ink_err_um']:.0f} um; " + ", ".join(
            f"{c} {rows.get(keys[c])['ratio']:.3f}" for c in ctls[1:]) + f"; clean moved {mc['moved_vs_clean_um']:.1f} um")
        rows.save()
    rows.save()
    R = rows.values()
    body = {"n_draws": n, "by_ctl": agg([r for r in R if r["ctl"] in ctls],
                                        ("ink_err_um", "ratio", "letters_read", "words_app", "P_total_W"), by=("ctl",)),
            "clean": agg([r for r in R if r["ctl"] == "clean_nose"], ("moved_vs_clean_um", "P_total_W"), by=("ctl",)),
            "ratio_p90": {c: float(np.percentile([r["ratio"] for r in R if r["ctl"] == c], 90))
                          for c in ctls[1:] if any(r["ctl"] == c for r in R)},
            "draws": [r.get("dr") for r in R if r["ctl"] == "none"]}
    if not quick:
        write_result("dr", body, seeds=list(TEST_SEEDS))
    return body


# ------------------------------------------------------------------------------------------------ step check
def stage_dt(quick: bool = False) -> Dict:
    """25 us against the 50 us test step on a subset (writers 0-1, first seed, 8 Hz x 1 mm and tremor-free)."""
    from . import et as ET
    rows = Rows("dt")
    for dt in (50e-6, 25e-6):
        pens = ET.PenModels(dt=dt)
        for w in (TEST_WRITERS[:2] if not quick else TEST_WRITERS[:1]):
            seed = et_seeds(w)[0]
            keys = {c: f"{dt * 1e6:g}|{w}|{c}" for c in ("none", "nose", "oracle", "clean_nose")}
            if all(rows.has(k) for k in keys.values()):
                continue
            su = ET.WriterSetup(w, pens, log=log)
            rn = ET.run_case(su, "none", 8.0, 1.0e-3, seed, keep=True)
            r_none = rn.pop("_r")
            rows.put(keys["none"], dict(rn, dt_us=dt * 1e6, ctl="none", clean_floor_um=su.clean_floor["ink_to_intended_um"]))
            for c in ("nose", "oracle"):
                m = ET.run_case(su, c, 8.0, 1.0e-3, seed, ref_none=r_none)
                rows.put(keys[c], dict(m, dt_us=dt * 1e6, ctl=c, ratio=m["ink_err_um"] / max(rn["ink_err_um"], 1e-9)))
            mc = ET.run_case(su, "nose", 0.0, 0.0, seed, ref_none=su.clean_ref(seed))
            rows.put(keys["clean_nose"], dict(mc, dt_us=dt * 1e6, ctl="clean_nose"))
            log(f"[dt] {dt * 1e6:g} us w{w}: none {rn['ink_err_um']:.0f}, nose {rows.get(keys['nose'])['ink_err_um']:.0f}, "
                f"oracle {rows.get(keys['oracle'])['ink_err_um']:.0f} um, clean moved {mc['moved_vs_clean_um']:.1f} um")
            rows.save()
    R = rows.values()
    body = {"by_dt_ctl": agg(R, ("ink_err_um", "ratio", "letters_read", "words_app", "moved_vs_clean_um", "P_total_W",
                                 "clean_floor_um"), by=("dt_us", "ctl"))}
    if not quick:
        write_result("dt_check", body, seeds=[et_seeds(w)[0] for w in TEST_WRITERS[:2]])
    return body


# ------------------------------------------------------------------------------------------------ power sensitivity
def stage_power(quick: bool = False) -> Dict:
    """The nose's coil power with the refill spring's transverse ball load (CALC and SIM): F_c 0.075 / 0.15 N and
    Km scale 0.7 / 1.0 (the lead's DR range), writer 0, tremor-free and 8 Hz x 1 mm, nose held and nose tracking."""
    from . import et as ET
    from . import revj as RJ
    rows = Rows("power")
    out_calc = []
    for th in (35.0, 50.0, 75.0):
        for Fc in (0.075, 0.15):
            for kms in (0.7, 1.0):
                cfg = RJ.config(dt=50e-6, theta_deg=th, F_c=Fc, km_scale=kms)
                tau = cfg.geom.z_p * Fc / math.tan(math.radians(th))
                P = (tau / (cfg.nose.Km_act * (cfg.geom.z_a - cfg.geom.z_p))) ** 2
                out_calc.append({"theta_deg": th, "F_c_N": Fc, "km_scale": kms, "torque_mNm": tau * 1e3,
                                 "P_static_W": P, "I_static_A": tau / (cfg.nose.K_f * (cfg.geom.z_a - cfg.geom.z_p)),
                                 "label": "CALC: F_c cot(theta) at the ball held by the coils, z_p F_c cot(theta) / "
                                          "(Km (z_a - z_p)) squared"})
    for Fc in (0.075, 0.15):
        for kms in ((1.0,) if quick else (0.7, 1.0)):
            pens = ET.PenModels(F_c=Fc, km_scale=kms)
            w = 0
            seed = et_seeds(w)[0]
            keys = {c: f"{Fc:g}|{kms:g}|{c}" for c in ("clean_none", "clean_nose", "tremor_none", "tremor_nose")}
            if all(rows.has(k) for k in keys.values()):
                continue
            su = ET.WriterSetup(w, pens, log=log)
            a = ET.run_case(su, "none", 0.0, 0.0, seed)
            b = ET.run_case(su, "nose", 0.0, 0.0, seed, ref_none=su.clean_ref(seed))
            rn = ET.run_case(su, "none", 8.0, 1e-3, seed, keep=True)
            r_none = rn.pop("_r")
            c = ET.run_case(su, "nose", 8.0, 1e-3, seed, ref_none=r_none)
            for k, m in zip(keys.values(), (a, b, rn, c)):
                rows.put(k, dict(m, F_c=Fc, km_scale=kms, case=k.split("|")[-1]))
            log(f"[power] F_c {Fc:g} N, Km x{kms:g}: P_nose held {a['P_nose_W']:.2f} W, tracking {c['P_nose_W']:.2f} W; "
                f"ink {rn['ink_err_um']:.0f} -> {c['ink_err_um']:.0f} um; clean floor {su.clean_floor['ink_to_intended_um']:.0f} um")
            rows.save()
    R = rows.values()
    body = {"calc": out_calc, "sim": agg(R, ("P_nose_W", "P_total_W", "battery_h", "ink_err_um", "letters_read",
                                              "words_app", "moved_vs_clean_um"), by=("F_c", "km_scale", "case"))}
    if not quick:
        write_result("power", body, seeds=[et_seeds(0)[0]])
    return body


# ------------------------------------------------------------------------------------------------ RL
RL_DIR = os.path.join(BUILD, "rl")
RL_STEPS = int(os.environ.get("SIM2J_RL_STEPS", "1000000"))
RL_SEL_CELLS = ((8.0, 0.3e-3), (6.0, 1.0e-3), (8.0, 1.0e-3), (10.0, 1.0e-3), (8.0, 2.0e-3))


def stage_rl_train(quick: bool = False) -> Dict:
    from . import rl as RL
    steps = 5000 if quick else RL_STEPS
    out = os.path.join(BUILD, "rl_quick") if quick else RL_DIR
    t0 = time.time()
    stats = RL.train(steps, out, seed=0, ckpt_every=2500 if quick else 100_000, log=log)
    stats["wall_s_total"] = time.time() - t0
    json.dump(stats, open(os.path.join(out, "train_stats.json"), "w"), indent=1, default=_default)
    log(f"[rl_train] {steps} steps in {stats['wall_s_total'] / 60:.1f} min ({stats})")
    return stats


def _checkpoints(d: str) -> List[str]:
    import glob
    cks = sorted(glob.glob(os.path.join(d, "ppo_revj_*_steps.zip")), key=lambda p: int(p.split("_")[-2]))
    fin = os.path.join(d, "ppo_revj_final.zip")
    if os.path.exists(fin):
        cks.append(fin)
    return cks


def stage_rl_select(quick: bool = False, last_n: int = 4) -> Dict:
    """Checkpoint selection on the tuning writers 100-103 (seed 300 + i for writer 100 + i) with the rule frozen in
    results/sim2j/rules.json (S1 false correction, S2 no worse than the model-based tracker at 0.3 mm, then the lowest
    ink error at 1-2 mm)."""
    from . import et as ET
    from . import rl as RL
    rows = Rows("rl_select")
    cks = _checkpoints(RL_DIR if not quick else os.path.join(BUILD, "rl_quick"))
    cks = cks[-last_n:]
    if not cks:
        log("[rl_select] no checkpoints")
        return {}
    pens = ET.PenModels()
    ws = TUNE_WRITERS if not quick else TUNE_WRITERS[:1]
    for i, w in enumerate(ws):
        seed = TUNE_SEEDS[i % len(TUNE_SEEDS)]
        su = ET.WriterSetup(w, pens, log=log)
        need = [(f0, a) for f0, a in RL_SEL_CELLS]
        # model-based and device-off on the same cases
        for f0, amp in need:
            kb = f"{f0:g}|{amp * 1e3:g}|{w}|{seed}"
            todo = [ck for ck in cks if not rows.has(kb + "|" + os.path.basename(ck))]
            if rows.has(kb + "|nose") and not todo:
                continue
            rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
            r_none = rn.pop("_r")
            rows.put(kb + "|none", dict(rn, ctl="none", kind="tremor"))
            if not rows.has(kb + "|nose"):
                m = ET.run_case(su, "nose", f0, amp, seed, ref_none=r_none)
                rows.put(kb + "|nose", dict(m, ctl="nose", kind="tremor", ratio=m["ink_err_um"] / rn["ink_err_um"]))
            for ck in todo:
                pol = RL.Policy(RL.load(ck))
                m = ET.run_case(su, "rl", f0, amp, seed, ref_none=r_none, policy=pol)
                rows.put(kb + "|" + os.path.basename(ck), dict(m, ctl=os.path.basename(ck), kind="tremor",
                                                               ratio=m["ink_err_um"] / rn["ink_err_um"]))
            log(f"[rl_select] w{w} {f0:g} Hz {amp * 1e3:g} mm: none {rn['ink_err_um']:.0f}, nose "
                f"{rows.get(kb + '|nose')['ink_err_um']:.0f}, " + ", ".join(
                    f"{os.path.basename(ck)[9:-4]} {rows.get(kb + '|' + os.path.basename(ck))['ink_err_um']:.0f}" for ck in cks))
        for ck in cks:
            kc = f"clean|{w}|{seed}|{os.path.basename(ck)}"
            if rows.has(kc):
                continue
            pol = RL.Policy(RL.load(ck))
            m = ET.run_case(su, "rl", 0.0, 0.0, seed, ref_none=su.clean_ref(seed), policy=pol)
            rows.put(kc, dict(m, ctl=os.path.basename(ck), kind="clean"))
            log(f"[rl_select] w{w} clean {os.path.basename(ck)}: moved {m['moved_vs_clean_um']:.1f} um")
        rows.save()
    R = rows.values()
    table = {}
    for ck in cks:
        nm = os.path.basename(ck)
        cl = [r["moved_vs_clean_um"] for r in R if r["ctl"] == nm and r["kind"] == "clean"]
        t03, t12 = [], []
        for r in R:
            if r["ctl"] != nm or r["kind"] != "tremor":
                continue
            kb = f"{r['f0']:g}|{r['amp_mm']:g}|{r['w']}|{r['seed']}"
            mb = rows.get(kb + "|nose")
            if abs(r["amp_mm"] - 0.3) < 1e-6:
                t03.append(r["ink_err_um"] / max(mb["ink_err_um"], 1e-9))
            else:
                t12.append(r["ink_err_um"])
        mb12 = [r["ink_err_um"] for r in R if r["ctl"] == "nose" and r["kind"] == "tremor" and r["amp_mm"] > 0.5]
        table[nm] = {"false_correction_um_mean": float(np.mean(cl)) if cl else None,
                     "false_correction_um_max": float(np.max(cl)) if cl else None,
                     "ratio_to_model_based_0p3": float(np.mean(t03)) if t03 else None,
                     "ink_err_1_2mm_um": float(np.mean(t12)) if t12 else None,
                     "model_based_ink_err_1_2mm_um": float(np.mean(mb12)) if mb12 else None}
        tb = table[nm]
        tb["S1"] = bool(cl) and tb["false_correction_um_mean"] <= 25.0 and tb["false_correction_um_max"] <= 50.0
        tb["S2"] = tb["ratio_to_model_based_0p3"] is not None and tb["ratio_to_model_based_0p3"] <= 1.0
    passing = [k for k, v in table.items() if v["S1"] and v["S2"]]
    chosen = min(passing, key=lambda k: table[k]["ink_err_1_2mm_um"]) if passing else None
    body = {"rule": json.load(open(os.path.join(RESULTS, "rules.json"))).get("rl_selection_rule"),
            "checkpoints": table, "chosen": chosen, "adopted": chosen is not None,
            "cells": [list(c) for c in RL_SEL_CELLS], "writers": list(ws)}
    if not quick:
        write_result("rl_select", body, seeds=list(TUNE_SEEDS))
    log(f"[rl_select] chosen {chosen}")
    return body


def stage_rl_test(quick: bool = False) -> Dict:
    """The selected policy on the test writers and seeds (the ET grid's first seed of each writer: 6 cases per cell)
    and on tremor-free writing, against the model-based tracker's rows of the ET stage."""
    from . import rl as RL
    sel = json.load(open(os.path.join(RESULTS, "rl_select.json")))
    ck = sel.get("chosen")
    if not ck:
        log("[rl_test] no checkpoint passed the selection rule: RL not adopted, nothing to test")
        write_result("rl_test", {"adopted": False, "reason": "no checkpoint passed S1 and S2 on the tuning writers"})
        return {}
    pol = RL.Policy(RL.load(os.path.join(RL_DIR, ck)))
    global ET_FULL, ET_HALF
    body = stage_et(quick=quick, controllers_extra={"rl": pol}, rows_name="et_rl", include_model_based=False,
                    first_seed_only=True)
    return body


def stage_report(quick: bool = False) -> None:
    from . import report as RP
    RP.run_all(log=log, with_runs=not quick)


# ------------------------------------------------------------------------------------------------ main
STAGES: Dict[str, Callable] = {"report": stage_report, "rl_train": stage_rl_train, "rl_select": stage_rl_select, "rl_test": stage_rl_test,
                               "tune": stage_tune, "writers": stage_writers, "writer_cmp": stage_writer_cmp,
                               "verify": stage_verify, "et": stage_et, "guided": stage_guided,
                               "autowrite": stage_autowrite, "dr": stage_dr, "dt": stage_dt, "power": stage_power}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", nargs="+", default=["tune", "et"])
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    for s in a.stages:
        if s not in STAGES:
            log(f"unknown stage {s}; known: {list(STAGES)}")
            return 2
    for s in a.stages:
        t0 = time.time()
        log(f"=== stage {s} ===")
        try:
            STAGES[s](quick=a.quick)
        except Exception:
            traceback.print_exc()
            log(f"stage {s} failed")
            return 1
        log(f"=== stage {s} done in {time.time() - t0:.0f} s ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
