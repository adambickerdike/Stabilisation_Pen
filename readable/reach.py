"""Reach check: can a nib with less reach than the Rev J nose deliver the readable target?  (Information for DEC-050
and DEC-060, added to the brief's three questions because a target is only useful if a nib can reach it.)

SIMULATION, model HW1 with real recorded inputs (study R's library), TUNING SPLIT ONLY (study E's selection set: 5
writers x 2 notes, severe class, PD and ET; 20 cases).  The Rev J nose (+-6 mm, PROPOSED DESIGN) is given the usable
travel of Rev K's balanced nib, +-1.5 and +-1.0 mm (DEC-050, DEC-060: q_lim, with the same taper share and the stop
the same share beyond it); its mass, servo, latency, slew and force are unchanged (Rev J's, not B1's).  Each case is
driven with
  - perfect knowledge (study R's oracle command),
  - perfect knowledge scaled to leave the frozen +2-words residual (EXP-E13 type (a), the same per-case rule as the
    test levels: rho = target / the case's nose-held tip tremor),
at +-3 and +-2 mm as well, to see what reach the target needs.  Measures: the tremor left at the tip (study R's
measure), the share of contact time at the travel limit (R's 'at_travel_limit': >= 0.95 q_lim), the nose's RMS
travel in contact, and words out of 10: read (the literal reader) for perfect knowledge at +-1.5 and +-1.0 mm, and
through the frozen tuning curve (CALC) for every run.  Also the size of the perfect-knowledge command itself in
contact (CALC on SIM signals: percentiles of its 2-D magnitude, share of time above 1-3 mm).  The +-6 mm runs repeat
EXP-E13's tuning runs (a check: they must give the same tip tremor).
"""
from __future__ import annotations

import dataclasses
import time
from typing import Dict, List

import numpy as np

from . import common as CM

REACH_MM = (6.0, 3.0, 2.0, 1.5, 1.0)       # 6.0 = the Rev J nose as modelled (results/nose2/nose2.json)
COMMANDS = ("oracle", "a_r2")
READ = {(1.5, "oracle"), (1.0, "oracle")}
KINDS = ("PD", "ET")
MAG_LEVELS_MM = (1.0, 1.5, 2.0, 3.0)


def plan(quick: bool) -> Dict:
    from . import e13
    notes = list(e13.plan(quick)["tuning"]["notes"])
    return {"notes": notes[:1] if quick else notes, "kinds": KINDS[:1] if quick else KINDS,
            "reach_mm": list(REACH_MM), "commands": list(COMMANDS),
            "read": [] if quick else sorted(f"{r:g}|{c}" for r, c in READ)}


def limited_pen(pen, reach_mm: float):
    """The Rev J pen with its usable travel set to reach_mm (taper and stop scaled with it); nothing else changed."""
    if abs(reach_mm * 1e-3 - pen.q_lim) < 1e-6:
        return pen
    k = reach_mm * 1e-3 / pen.q_lim
    return dataclasses.replace(pen, q_lim=pen.q_lim * k, q_taper=pen.q_taper * k, q_stop=pen.q_stop * k,
                               label=f"{pen.label} (travel limited to +-{reach_mm:g} mm)")


def reach_note(i: int, frozen: Dict, quick: bool = False) -> List[str]:
    """One tuning note (both kinds, severe): every reach x command, cached per case."""
    from handwriting import plant as PL
    from realdata import hw1 as H
    from . import residual as RS
    P = plan(quick)
    out_dir = CM.cache_dir(quick) / "reach"
    targets = {"a_r2": float(frozen["e13"]["r_plus2_mm"])}
    done, note = [], None
    for kind in P["kinds"]:
        p = out_dir / f"tune_n{i}_{kind}_severe.json"
        if p.exists():
            done.append(p.name)
            continue
        t1 = time.time()
        note = note or CM.tuning_note(i)
        spec = CM.tuning_spec(i, kind, "severe")
        tc = CM.TuneCase(note, spec)
        held = H.tip_tremor_mm(tc.neutral, tc.scn, tc.f0)
        cmds = {"oracle": (tc.q_oracle, {"remain": 0.0})}
        for key, tg in targets.items():
            rho = float(np.clip(tg / held, 0.02, 1.0))
            cmds[key] = (RS.scaled(tc.q_oracle, rho), {"remain": rho, "target_mm": tg})
        c = np.interp(tc.tick_t, tc.neutral.t, tc.neutral.contact) > 0.5
        mag = np.hypot(tc.q_oracle[c, 0], tc.q_oracle[c, 1]) * 1e3
        qmag = {"p50_mm": float(np.percentile(mag, 50)), "p90_mm": float(np.percentile(mag, 90)),
                "p99_mm": float(np.percentile(mag, 99)), "rms_mm": float(np.sqrt(np.mean(mag ** 2))),
                "share_above": {f"{a:g}": float(np.mean(mag > a)) for a in MAG_LEVELS_MM}}
        dev = {}
        for r_mm in P["reach_mm"]:
            pen = limited_pen(tc.pen, r_mm)
            for key, (q, prm) in cmds.items():
                res = PL.run(tc.scn, pen, note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
                read = f"{r_mm:g}|{key}" in P["read"]
                m = CM.measures(tc.written, res, tc.scn, pen, tc.f0, read=read)
                m["param"] = dict(prm, reach_mm=r_mm)
                dev[f"{r_mm:g}|{key}"] = m
        CM.jdump(p, {"set": "real", "split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                     "class": "severe", "case_id": spec["id"], "tremor": tc.tremor_meta(),
                     "held_tip_tremor_mm": held, "q_oracle_contact": qmag, "devices": dev,
                     "_elapsed_s": time.time() - t1})
        CM.log(f"[reach] n{i} {kind}: " + ", ".join(f"{k} {v['tip_tremor_mm']:.2f}" for k, v in dev.items()))
        done.append(p.name)
    return done


def aggregate(quick: bool, p_curve) -> Dict:
    """Per reach x command: tip tremor, time at the limit, RMS travel, words read and words via the frozen curve, with
    writer-bootstrap 95 % intervals (R's bootstrap); words gained over the ordinary pen from EXP-E13's reading of the
    same case."""
    from . import curve as CV
    P = plan(quick)
    d = CM.cache_dir(quick)
    cases = []
    for i in P["notes"]:
        for kind in P["kinds"]:
            c = CM.jload(d / "reach" / f"tune_n{i}_{kind}_severe.json")
            if c is None:
                continue
            e = CM.jload(d / "e13" / f"tune_n{i}_{kind}_severe.json") or {}
            c["_ordinary_words"] = CM.of10((e.get("devices") or {}).get("none") or {})
            c["_e13"] = {k: (e.get("devices") or {}).get(k, {}).get("tip_tremor_mm")
                         for k in ("E13a_0.00", "E13a_1.00")}
            cases.append(c)
    if not cases:
        return {"n_cases": 0}
    wr = sorted({c["writer"] for c in cases})
    out = {"n_cases": len(cases), "n_writers": len(wr), "label": "SIMULATION (model HW1) with real recorded inputs; "
           "tuning split only; the Rev J nose with its travel limited (Rev J's mass and servo); words via the frozen "
           "tuning curve = CALC", "plan": P, "rows": {}}

    def pw(fn):
        acc: Dict[str, List[float]] = {}
        for c in cases:
            v = fn(c)
            if v is not None and np.isfinite(v):
                acc.setdefault(c["writer"], []).append(float(v))
        return {w: float(np.mean(v)) for w, v in acc.items()}

    for r_mm in P["reach_mm"]:
        for key in P["commands"]:
            dk = f"{r_mm:g}|{key}"
            get = lambda c, m: (c["devices"].get(dk) or {}).get(m)          # noqa: E731
            row = {"reach_mm": r_mm, "command": key}
            for m in ("tip_tremor_mm", "at_travel_limit", "q_rms_mm"):
                b = pw(lambda c, m=m: get(c, m))
                row[m] = CM.boot(b) if b else None
            if p_curve is not None:
                b = pw(lambda c: float(CV.model(get(c, "tip_tremor_mm"), p_curve)) if get(c, "tip_tremor_mm") is not None
                       else None)
                row["words_via_curve"] = CM.boot(b) if b else None
            if dk in P["read"]:
                b = pw(lambda c: CM.of10(c["devices"].get(dk) or {}))
                row["words_read"] = CM.boot(b) if b else None
                g = pw(lambda c: CM.of10(c["devices"].get(dk) or {}) - c["_ordinary_words"])
                row["gain_read"] = CM.boot(g) if g else None
            out["rows"][dk] = row
    # the size of the perfect-knowledge command (what the nib would have to do)
    qm = {}
    for k in ("p50_mm", "p90_mm", "p99_mm", "rms_mm"):
        b = pw(lambda c, k=k: (c.get("q_oracle_contact") or {}).get(k))
        qm[k] = CM.boot(b) if b else None
    for a in MAG_LEVELS_MM:
        b = pw(lambda c, a=a: ((c.get("q_oracle_contact") or {}).get("share_above") or {}).get(f"{a:g}"))
        qm[f"share_above_{a:g}mm"] = CM.boot(b) if b else None
    out["q_oracle_contact"] = qm
    # the RMS travel perfect knowledge asks for, by class (EXP-E13's +-6 mm runs, R's 'q_rms_mm' in contact)
    qr = {}
    for cls in ("severe", "moderate"):
        acc: Dict[str, List[float]] = {}
        for i in P["notes"]:
            for kind in P["kinds"]:
                e = CM.jload(d / "e13" / f"tune_n{i}_{kind}_{cls}.json") or {}
                x = ((e.get("devices") or {}).get("E13a_0.00") or {}).get("q_rms_mm")
                if x is not None:
                    acc.setdefault(e.get("writer"), []).append(float(x))
        b = {w: float(np.mean(v)) for w, v in acc.items()}
        qr[cls] = CM.boot(b) if b else None
    out["oracle_q_rms_mm_by_class"] = qr
    # the check against EXP-E13's own +-6 mm runs (perfect knowledge, and the nose held)
    diffs = [abs(c["devices"]["6|oracle"]["tip_tremor_mm"] - c["_e13"]["E13a_0.00"]) for c in cases
             if c["_e13"].get("E13a_0.00") is not None and "6|oracle" in c["devices"]]
    out["repro_vs_e13_oracle_max_abs_mm"] = float(max(diffs)) if diffs else None
    return out
