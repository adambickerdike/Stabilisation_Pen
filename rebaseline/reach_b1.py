"""Task 4: study F's reach check with the balanced nib's dynamics (SIMULATION, model HW1 of handwriting/ with study R's
REAL recorded inputs: UNIPEN hpb2 writing, UCI PD tip tremor, Zenodo ET hand tremor; TUNING SPLIT ONLY; perfect
knowledge of the tremor; nothing measured).

readable/reach.py cut the Rev J nose's travel to +-1.0 / +-1.5 mm but kept Rev J's servo (80 Hz follower, 400 Hz
idealised inner loop) and its 2.10 g tip-equivalent mass.  Here the same 20 cases (study E's selection set: 10 tuning
notes x PD and ET, severe class 1.72 mm at the tip) run with the balanced nib's servo and moving mass:
  pen 'B1k'  Rev K's nib: 40 Hz position follower, 46 Hz inner loop (DEC-066), 3.44 g moving mass, 1.56 N/m linear
             wires, F_peak = Km sqrt(2.5 ohm) x 1.5 A with Km 0.3335 N/sqrt(W)
  pen 'B1c'  the 24 mm / 1.5 mm candidate: the same servo, 3.67 g, 1.53 N/m, Km 0.2729 N/sqrt(W)
  pen 'revJ' study F's pen (the reproduction check: its tip tremor must equal study F's cached runs)
Everything else is the Rev J pen of study F (handle mass 83.5 g, latency 0.6 ms, slew 0.6 m/s, skid ring, refill
force): HW1 cannot represent the wires' hardening or the guide's rolling drag (its suspension is linear and its
idealised inner loop feeds it forward); those loads are in task 3 (sim2).  For each pen the writer's adapted path, the
tremor-free run and the nose-held run are its own, and perfect knowledge previews ITS servo group delay (0.6 ms + 2 zeta
/ (2 pi 40 Hz) = 6.2 ms for B1, 3.4 ms for Rev J).  Travel limits as readable.reach.limited_pen (taper 10 % of the
usable radius, stop scaled).  Commands: perfect knowledge ('oracle') and perfect knowledge scaled to leave the frozen
+2-words residual ('a_r2', study F's rule).  Words: read by study R's literal reader for B1k at +-1.06 mm and B1c at
+-1.5 mm (perfect knowledge), and through the frozen tuning curve (CALC) for every run; the ordinary pen's words of
the same case come from study F's E13 reading (readable/build/cache/e13, read-only).
DEC-055's line: +2 readable words out of 10 over the ordinary pen at the severe class (with the 95 % writer-bootstrap
interval above 0) - applied here to perfect knowledge, i.e. as a necessary condition on the mechanism, not a tracker.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, REPO_ROOT
from . import common as CM

F_CACHE = REPO_ROOT / "readable" / "build" / "cache"                # study F's caches (read-only)
FROZEN_F = REPO_ROOT / "results" / "readable" / "frozen.json"
KINDS = ("PD", "ET")
INNER_HZ_B1 = 46.0
SERVO_HZ_B1 = 40.0
NIBS = {"B1k": {"m_tip": 3.439830737727785e-3, "k_tip": 1.5617, "Km": 0.33354573489671424,
                "label": "Rev K's nib (results/revK/revK.json m_move_g, Km_tip_revK x; revk/servo_sim.py k)"},
        "B1c": {"m_tip": 3.6699750000000002e-3, "k_tip": 1.5302, "Km": 0.2728601029645367,
                "label": "the 24 mm / 1.5 mm candidate (results/improvement/mechanics/mechanics_study.json)"}}
RUNS = (("revJ", 1.0, ("oracle",)), ("revJ", 1.5, ("oracle",)),                      # reproduction of study F
        ("B1k", 1.0, ("oracle", "a_r2")), ("B1k", 1.0587, ("oracle", "a_r2")), ("B1k", 1.5, ("oracle",)),
        ("B1c", 1.5, ("oracle", "a_r2")))
READ = {("B1k", 1.0587, "oracle"), ("B1c", 1.5, "oracle")}
SOURCES = ("readable/reach.py", "readable/common.py", "readable/curve.py", "readable/residual.py", "realtrack/cases.py",
           "realdata/hw1.py", "realdata/library.py", "realdata/ocr.py", "handwriting/plant.py", "handwriting/params.py",
           "handwriting/tracker.py", "results/nose2/nose2.json", "results/readable/frozen.json",
           "rebaseline/reach_b1.py", "rebaseline/common.py")


def b1_pen(revj, nib: str):
    """The Rev J HW1 pen with the balanced nib's servo bandwidth and moving mass (all else unchanged)."""
    p = NIBS[nib]
    K_f = p["Km"] * math.sqrt(2.5)
    return dataclasses.replace(revj, key=f"b1_{nib}", label=f"Rev J HW1 pen with the {nib} nib's servo and mass",
                               m_tip=p["m_tip"], k_tip=p["k_tip"], servo_hz=SERVO_HZ_B1, F_peak=K_f * 1.5,
                               F_cont=K_f * 1.5 / math.sqrt(2.0))


def limited(pen, reach_mm: float):
    from readable.reach import limited_pen
    return limited_pen(pen, reach_mm)


def inner_hz_of(key: str) -> Optional[float]:
    return None if key == "revJ" else INNER_HZ_B1


class Note:
    """realtrack.cases.Note for a given pen set: the adapted hand path and the tremor-free (nose-held) run per pen."""

    def __init__(self, written, pens: Dict):
        from handwriting import params as PR
        from handwriting import plant as PL
        from aiprior import core as CO
        self.written = written
        self.hand = PR.Hand.from_config()
        self.pens = pens
        self.scn0 = PL.scenario_from_written(written, None)
        self.hp = {k: PL.adapted_path(self.scn0.intended, self.scn0.dt, p, self.hand) for k, p in pens.items()}
        self.clean = {k: PL.run(PL.with_hand_path(self.scn0, self.hp[k]), p, self.hand,
                                **({} if inner_hz_of(k) is None else {"inner_hz": inner_hz_of(k)}))
                      for k, p in pens.items() if k != "none"}
        self.trk = CO.tracker()

    def scenario(self, key: str, tremor):
        from handwriting import plant as PL
        return PL.with_hand_path(self.scn0, self.hp[key], tremor)


def pens():
    from realdata import hw1 as H
    base = H.pens()
    out = {"none": base["none"], "revJ": base["revJ"]}
    for nib in NIBS:
        out[nib] = b1_pen(base["revJ"], nib)
    return out


def plan(quick: bool = False) -> Dict:
    from readable import e13
    notes = list(e13.plan(quick)["tuning"]["notes"])
    return {"notes": notes[:1] if quick else notes, "kinds": KINDS[:1] if quick else KINDS}


def f_cached(i: int, kind: str) -> Dict:
    return CM.jload(F_CACHE / "reach" / f"tune_n{i}_{kind}_severe.json") or {}


def e13_ordinary_words(i: int, kind: str) -> Optional[float]:
    from readable import common as RC
    e = CM.jload(F_CACHE / "e13" / f"tune_n{i}_{kind}_severe.json") or {}
    d = (e.get("devices") or {}).get("none")
    return RC.of10(d) if d else None


def run_note(i: int, frozen: Dict, rows: CM.Rows, quick: bool = False, log=CM.log) -> None:
    from handwriting import params as PR
    from handwriting import plant as PL
    from handwriting import tracker as TR
    from realdata import hw1 as H
    from readable import common as RC
    from readable import residual as RS
    from realdata import library as RL
    P = plan(quick)
    todo = [k for k in P["kinds"] if not rows.has(f"n{i}|{k}")]
    if not todo:
        return
    wr = RL.writing("tuning", seed=i, source="unipen")
    note = Note(wr, pens())
    target = float(frozen["e13"]["r_plus2_mm"])
    for kind in todo:
        t0 = time.time()
        spec = RC.tuning_spec(i, kind, "severe")
        dr = RC.tuning_tremor(note, spec)
        f0 = float(dr.meta["f0"])
        dev, held, qmag = {}, {}, {}
        cache = {}
        for key, r_mm, cmds in RUNS:
            if key not in cache:
                pen = note.pens[key]
                kw = {} if inner_hz_of(key) is None else {"inner_hz": inner_hz_of(key)}
                scn = note.scenario(key, dr.d)
                neutral = PL.run(scn, pen, note.hand, ctl=PL.Controls(), **kw)
                Ts, n_ticks = float(neutral.info["Ts"]), int(neutral.info["n_ticks"])
                q = TR.oracle_command(neutral, note.clean[key], pen, n_ticks, Ts)
                h = H.tip_tremor_mm(neutral, scn, f0)
                tick_t = np.arange(n_ticks) * Ts
                c = np.interp(tick_t, neutral.t, neutral.contact) > 0.5
                mag = np.hypot(q[c, 0], q[c, 1]) * 1e3
                qmag[key] = {"p50_mm": float(np.percentile(mag, 50)), "p90_mm": float(np.percentile(mag, 90)),
                             "share_above_1mm": float(np.mean(mag > 1.0)), "share_above_1p5mm": float(np.mean(mag > 1.5)),
                             "preview_ms": 1e3 * PR.servo_group_delay(pen)}
                held[key] = h
                cache[key] = (scn, q, kw, h)
            scn, q, kw, h = cache[key]
            pen_l = limited(note.pens[key], r_mm)
            for cmd in cmds:
                if cmd == "oracle":
                    qq, prm = q, {"remain": 0.0}
                else:
                    rho = float(np.clip(target / h, 0.02, 1.0))
                    qq, prm = RS.scaled(q, rho), {"remain": rho, "target_mm": target}
                res = PL.run(scn, pen_l, note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(qq)), **kw)
                read = (key, r_mm, cmd) in READ and not quick
                m = RC.measures(wr, res, scn, pen_l, f0, read=read)
                m["param"] = dict(prm, reach_mm=r_mm, pen=key)
                dev[f"{key}|{r_mm:g}|{cmd}"] = m
        from readable import curve as CV
        p_curve = frozen["e13"]["fit"]["p"]
        for k, m in dev.items():
            m["words_via_curve"] = float(CV.model(m["tip_tremor_mm"], p_curve))
        fc = f_cached(i, kind)
        repro = {}
        for key_f, key_me in (("1|oracle", "revJ|1|oracle"), ("1.5|oracle", "revJ|1.5|oracle")):
            a = ((fc.get("devices") or {}).get(key_f) or {}).get("tip_tremor_mm")
            b = dev[key_me]["tip_tremor_mm"]
            repro[key_f] = {"studyF_mm": a, "here_mm": b, "abs_diff_mm": None if a is None else abs(a - b)}
        row = {"note": i, "kind": kind, "writer": wr.real["writer"], "case_id": spec["id"],
               "tremor": {k: dr.meta.get(k) for k in ("rid", "amp_mm", "f0", "subject", "looped")},
               "held_tip_tremor_mm": held, "q_oracle_contact": qmag, "devices": dev,
               "ordinary_words_of_10": e13_ordinary_words(i, kind), "repro_vs_studyF": repro,
               "wall_s": time.time() - t0}
        rows.put(f"n{i}|{kind}", row, save=True)
        log(f"[reach_b1] n{i} {kind}: " + ", ".join(f"{k} {v['tip_tremor_mm']:.2f}" + (
            f" ({v.get('words_read')}/{v.get('words_total')})" if v.get("words_read") is not None else "")
            for k, v in dev.items()) + f"; repro max diff {max((r['abs_diff_mm'] or 0) for r in repro.values()):.2e} mm"
            f" [{row['wall_s']:.0f} s]")


def run(quick: bool = False, log=CM.log) -> Dict:
    from readable import common as RC
    RC.reader_ready(log)
    frozen = CM.jload(FROZEN_F)
    rows = CM.Rows("reach_b1", quick=quick)
    t0 = time.time()
    for i in plan(quick)["notes"]:
        run_note(int(i), frozen, rows, quick, log)
    return {"wall_s": time.time() - t0, "n": len(rows.rows)}


# ------------------------------------------------------------------ aggregation (writer bootstrap, R's convention)
def aggregate(rows: List[Dict]) -> Dict:
    from realdata import hw1 as H
    out = {"n_cases": len(rows), "n_writers": len({r["writer"] for r in rows}), "rows": {}}

    def pw(fn):
        acc: Dict[str, List[float]] = {}
        for r in rows:
            v = fn(r)
            if v is not None and np.isfinite(v):
                acc.setdefault(r["writer"], []).append(float(v))
        return {w: float(np.mean(v)) for w, v in acc.items()}
    keys = sorted({k for r in rows for k in r["devices"]})
    for dk in keys:
        get = lambda r, m: ((r["devices"].get(dk) or {}).get(m))           # noqa: E731
        row = {}
        for m in ("tip_tremor_mm", "at_travel_limit", "q_rms_mm", "words_via_curve", "bb_um"):
            b = pw(lambda r, m=m: get(r, m))
            row[m] = H._boot(b) if b else None
        if any(get(r, "words_read") is not None for r in rows):
            from readable import common as RC
            row["words_read"] = H._boot(pw(lambda r: RC.of10(r["devices"][dk]) if r["devices"][dk].get("words_total") else None))
            row["gain_read"] = H._boot(pw(lambda r: (RC.of10(r["devices"][dk]) - r["ordinary_words_of_10"])
                                          if (r["devices"][dk].get("words_total") and r.get("ordinary_words_of_10") is not None) else None))
            g = row["gain_read"]
            row["dec055_mechanism_line"] = {"gain_mean": g.get("mean"), "gain_lo": g.get("lo"),
                                            "passes": bool(g.get("mean") is not None and g["mean"] >= 2.0 and g["lo"] > 0.0),
                                            "rule": "+2 words of 10 over the ordinary pen, 95 % writer-bootstrap interval "
                                                    "above 0 (DEC-055's words line applied to perfect knowledge)"}
        row["gain_via_curve"] = H._boot(pw(lambda r: (get(r, "words_via_curve") - r["ordinary_words_of_10"])
                                           if (get(r, "words_via_curve") is not None and r.get("ordinary_words_of_10") is not None) else None))
        out["rows"][dk] = row
    rep = [x["abs_diff_mm"] for r in rows for x in r["repro_vs_studyF"].values() if x.get("abs_diff_mm") is not None]
    out["repro_vs_studyF_max_abs_mm"] = max(rep) if rep else None
    out["ordinary_words_of_10"] = H._boot(pw(lambda r: r.get("ordinary_words_of_10")))
    out["held_tip_tremor_mm"] = {k: H._boot(pw(lambda r, k=k: (r["held_tip_tremor_mm"] or {}).get(k))) for k in
                                 ("revJ", "B1k", "B1c")}
    out["q_oracle_share_above_1p5mm"] = {k: H._boot(pw(lambda r, k=k: (r["q_oracle_contact"].get(k) or {}).get("share_above_1p5mm")))
                                         for k in ("revJ", "B1k", "B1c")}
    return out


def studyF_published() -> Dict:
    r = (CM.jload(REPO_ROOT / "results" / "readable" / "readable.json") or {}).get("reach") or {}
    return {k: {kk: (vv.get("mean") if isinstance(vv, dict) else vv) for kk, vv in v.items()}
            for k, v in (r.get("rows") or {}).items() if k in ("1|oracle", "1.5|oracle", "1|a_r2", "1.5|a_r2")}


def summarise(quick: bool = False, write: bool = True) -> Dict:
    rows = [r for r in CM.Rows("reach_b1", quick=quick).rows.values()]
    body = {"what": "study F's perfect-knowledge reach check with the balanced nib's servo (40/46 Hz) and moving mass",
            "evidence": ("SIMULATION (model HW1 with real recorded inputs, tuning split only, perfect knowledge; the "
                         "nib constants are CALC / PROPOSED DESIGN); words read by study R's literal AI reader; words "
                         "via the frozen E13 tuning curve are CALC"),
            "nibs": NIBS, "servo": {"position_hz": SERVO_HZ_B1, "inner_hz": INNER_HZ_B1, "rule": "DEC-066"},
            "studyF_published": studyF_published(), "aggregate": aggregate(rows) if rows else None,
            "wall_s_total": float(sum(r.get("wall_s") or 0 for r in rows))}
    if write and not quick:
        CM.write_result("reach_b1", body, body["evidence"], inputs=SOURCES,
                        seeds="study E's tuning specs (realtrack.cases.tuning_specs: tseed per case)",
                        parameters={"runs": [list(r) for r in RUNS], "read": sorted(map(list, READ)), "nibs": NIBS,
                                    "kinds": list(KINDS)})
    return body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args(argv)
    if a.run:
        run(a.quick)
    if a.summarise:
        s = summarise(a.quick)
        ag = s.get("aggregate") or {}
        print(json.dumps({k: {m: (v.get(m) or {}).get("mean") for m in ("tip_tremor_mm", "words_read", "gain_read",
                                                                        "gain_via_curve")}
                          for k, v in (ag.get("rows") or {}).items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
