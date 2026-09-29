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
             writers=TEST_WRITERS, include_model_based: bool = True) -> Dict:
    """The ET test grid.  controllers_extra: {'rl': policy} adds RL cases (all 12 per cell)."""
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
        seeds = et_seeds(w) if not quick else et_seeds(w)[:1]
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


# ------------------------------------------------------------------------------------------------ main
STAGES: Dict[str, Callable] = {"tune": stage_tune, "et": stage_et}


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
