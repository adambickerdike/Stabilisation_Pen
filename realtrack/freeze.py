"""The freeze: finalists re-run in the FULL HW1 plant on the tuning cases, the choice by tune.py's rules, frozen.json.

Finalists (the best setting of each family that the searches found; tuning split only):
  joint_akf     the AKF with its leakage/capture parameters and the soft amplitude authority tuned together
  gate_listen   ai2's listening estimate with the retuned binary gate (detector band, window, thresholds, hysteresis,
                amplitude gate, fallback)
  listen_conf   ai2's listening estimate with the soft authority: amplitude x the detector's continuous line confidence
  glg           study W's GLG (the lead's request): ai2's gated listening estimate with sim2j's G4 as the fallback, the
                gate retuned like the binary gate (fallback chosen among G4, the Rev H tracker and none)
  net           the TCN trained on real tuning inputs (cross-fitted: each tuning case scored by the fold model that never
                saw its writer or patients), with its own soft amplitude authority if the search found one
Rule (tune.py): pass T2-T4 in the full plant; the lowest J (severe broadband ratio); within 0.02 the cheaper MCU design.
The G4 port (frozen sim2j settings, results/sim2j/rules.json) is the second baseline and is carried into the test as is.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional

import numpy as np

from . import BUILD_DIR, RESULTS_DIR
from . import cases as C
from . import estimators as E
from . import evaluate as EV
from . import servo as SV
from . import tune as TU

FROZEN = RESULTS_DIR / "frozen.json"
FULL_DIR = BUILD_DIR / "freeze"


def _sha(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def finalists() -> Dict[str, Dict]:
    from . import search as SR
    out = {}
    p = TU.TUNE_DIR / "joint_akf.json"
    if p.exists():
        out["joint_akf"] = SR.joint_design("joint_akf")
    p = TU.TUNE_DIR / "gate_s2_gate_listen.json"
    if p.exists():
        b = json.loads(p.read_text())["best"]["params"]
        out["gate_listen"] = {"family": "gatefast", "params": {"gate": b, "D": SR.listening_design()},
                              "name": "gate_listen"}
    p = TU.TUNE_DIR / "gate_s2_glg.json"
    if p.exists():
        b = json.loads(p.read_text())["best"]["params"]
        out["glg"] = {"family": "gatefast", "params": {"gate": b, "D": SR.listening_design()}, "name": "glg"}
    p = TU.TUNE_DIR / "auth_s2_listen_conf.json"
    if p.exists():
        b = json.loads(p.read_text())["best"]["params"]
        d = SR.listening_design()
        d.update({"auth": b, "name": "listen_conf"})
        out["listen_conf"] = d
    p = TU.TUNE_DIR / "auth_net_main.json"
    from .learned import MODEL_DIR
    if (MODEL_DIR / "net_net_main.json").exists():
        d = {"family": "net", "params": {"tag": "net_main", "fold": "auto"}, "name": "net"}
        if p.exists():
            d["auth"] = json.loads(p.read_text())["best"]["params"]
        out["net"] = d
    return out


def full_eval(designs: Dict[str, Dict], log=print) -> Dict[str, Dict]:
    """Every design on every tuning case in the full HW1 closed loop (the cached streams; the scenario rebuilt from its
    spec); tip tremor, broadband residual, false correction as R measures them."""
    from realdata import hw1 as H
    from realdata import library as RL
    from handwriting import plant as PL
    from ai2 import delayed as DL
    FULL_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    t0 = time.time()
    specs = C.tuning_specs()
    by_note: Dict[int, List[Dict]] = {}
    for s in specs:
        by_note.setdefault(s["note"], []).append(s)
    for i, ss in sorted(by_note.items()):
        cache = FULL_DIR / f"note{i}.json"
        prev = json.loads(cache.read_text()) if cache.exists() else []
        have = {(r["design"], r["case"]) for r in prev}
        need = [(nm, s) for s in ss for nm in designs if (nm, s["id"]) not in have]
        if need:
            note = C.tuning_note(i)
            pen = note.pens["revJ"]
            for s in ss:
                todo = [nm for nm in designs if (nm, s["id"]) not in have]
                if not todo:
                    continue
                case = C.load_case(s)
                tremor = None
                if s.get("kind"):
                    tremor = RL.tremor(s["level"] if s["level"] in ("severe", "moderate", "mild") else "severe",
                                       seed=int(s["tseed"]), kind=s["kind"], split="tuning",
                                       t=note.written.intended.t, amp_mm=float(s["amp_mm"]), rid=s["rid"]).d
                scn = note.scenario("revJ", tremor)
                held_bb = SV.broadband_um(case.arrays["t1k"], case.arrays["handle1k"], case.arrays["intended1k"],
                                          case.arrays["contact1k"])
                for nm in todo:
                    q, info = EV.command(designs[nm], case, "deltapen")
                    r = PL.run(scn, pen, note.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
                    m = {"design": nm, "case": s["id"], "level": s["level"], "kind": s.get("kind"), "note": i}
                    if s.get("kind"):
                        f0 = float(case.meta["tremor"]["f0"])
                        tt = H.tip_tremor_mm(r, scn, f0)
                        m["tip_tremor_mm"] = tt
                        m["ratio"] = tt / case.meta["ref"]["none_tip_tremor_mm"]
                        m["ratio_held"] = tt / case.meta["ref"]["held_tip_tremor_mm"]
                        rr = r.rec[::4]
                        k = np.clip(np.round(rr[:, 0] / scn.dt).astype(int), 0, len(scn.t) - 1)
                        bb = SV.broadband_um(rr[:, 0], r.ink[::4], np.asarray(scn.intended)[k], r.contact[::4])
                        m["bb_um"] = bb
                        m["bb_ratio_held"] = bb / held_bb
                    else:
                        ref = note.clean["revJ"]
                        n = min(len(r.t), len(ref.t))
                        mm = (r.contact[:n] > 0.5) & (ref.contact[:n] > 0.5)
                        e = r.ink[:n][mm] - ref.ink[:n][mm]
                        m["clean_change_um"] = float(np.sqrt(np.mean(np.sum(e ** 2, 1))) * 1e6) if mm.any() else float("nan")
                    prev.append(m)
                del case
            cache.write_text(json.dumps(prev, default=float))
            log(f"[freeze] note {i}: {len(need)} full-plant runs ({time.time() - t0:.0f} s)")
            del note
        rows += [r for r in prev if r["design"] in designs]
    return EV.summarize(rows)


def choose(summ: Dict[str, Dict], cost: Dict[str, float]) -> Dict:
    table = {}
    for nm, sm in summ.items():
        table[nm] = {"J": sm.get("severe_bb"), "severe_ratio": sm.get("severe_ratio"), "passes": TU.passes(sm),
                     "summary": sm, "cpu_share": cost.get(nm)}
    passing = [nm for nm, t in table.items() if t["passes"]["all"]]
    if passing:
        best = min(passing, key=lambda n: table[n]["J"])
        close = [n for n in passing if table[n]["J"] <= table[best]["J"] + 0.02]
        chosen = min(close, key=lambda n: (cost.get(n, 1.0), table[n]["J"]))
        why = f"lowest J among the designs that pass T2-T4 ({best}); cheapest within 0.02 of it: {chosen}"
    else:
        cand = [nm for nm, t in table.items() if t["passes"]["T3"]] or list(table)
        chosen = min(cand, key=lambda n: table[n]["summary"].get("clean_um_mean", np.inf))
        why = "no design passes T2-T4: the smallest clean-writing change among those passing T3 (DEC-055 not claimed)"
    return {"table": table, "chosen": chosen, "why": why}


def g4_design() -> Dict:
    return {"family": "g4", "params": {}, "name": "g4",
            "note": "sim2j's guarded tracker G4 as frozen in results/sim2j/rules.json (guard G4_gate_r8, detector r_on 8 / "
                    "r_off 4); horizon + the Rev J servo group delay; detector fed with page samples with the ball on "
                    "the paper"}


def run(log=print, designs: Optional[Dict[str, Dict]] = None, costs: Optional[Dict[str, float]] = None) -> Dict:
    if FROZEN.exists():
        log(f"[freeze] {FROZEN} exists: the choice is frozen (delete it only to re-tune before any test run)")
        return json.loads(FROZEN.read_text())
    from stabpen import provenance as PV
    from . import mcu as MC
    fin = designs or finalists()
    summ = full_eval(fin, log=log)
    t = MC.table()
    cost = {"joint_akf": t["akf"]["cpu_share_128MHz"] + t["authority"]["cpu_share_128MHz"],
            "gate_listen": t["akf"]["cpu_share_128MHz"] + t["detector"]["cpu_share_128MHz"],
            "listen_conf": t["akf"]["cpu_share_128MHz"] + t["detector"]["cpu_share_128MHz"],
            "glg": 2 * t["akf"]["cpu_share_128MHz"] + 2 * t["detector"]["cpu_share_128MHz"],
            "net": 0.07}
    cost.update(costs or {})
    ch = choose(summ, cost)
    chosen = dict(fin[ch["chosen"]])
    info = {k: v for k, v in fin.items() if k != ch["chosen"]}
    models = {}
    from .learned import MODEL_DIR
    for p in sorted(MODEL_DIR.glob("*.pt")) + sorted(MODEL_DIR.glob("fir_*.json")):
        models[p.name] = _sha(p)
    out = {"stabpen.provenance": PV.metadata("SIMULATION (tuning split only; frozen before the test run)",
                                             extra={"package": "realtrack", "script": "realtrack/freeze.py"}),
           "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rules": TU.__doc__, "chosen_name": ch["chosen"], "why": ch["why"], "chosen": chosen, "g4": g4_design(),
           "info": info, "tuning_full_plant": ch["table"], "model_sha256_16": models,
           "search_files": {p.name: _sha(p) for p in sorted(TU.TUNE_DIR.glob("*.json"))}}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FROZEN.write_text(json.dumps(out, indent=1, default=float))
    log(f"[freeze] chosen {ch['chosen']}: {ch['why']}")
    return out
