"""The one test run on study R's TEST split, after the freeze (SIMULATION, model HW1 with real inputs).

Cases: exactly R's (realdata.hw1.plan(quick=False)): the 9 test notes (one per UNIPEN hpb2 test writer), PD and ET
tremor of test patients at the three class representatives (mild 0.098, moderate 0.24, severe 1.72 mm at the tip), and
the 9 notes without tremor.  Each case is rebuilt with R's own code and seeds (realdata.hw1.Writer, make_scen with R's
case keys), so the new designs see exactly the scenario, the nose-held run and the sensor draws (ideal and DeltaPen-
class) that R's pens saw.  R's pens are NOT recomputed: their per-case results are read from R's cache
(realdata/build/cache/hw1/full_v2, read-only), which repro.py showed to be bit-identical to a re-run of R's code.

New rows (every one with the DeltaPen-class page sensor = the headline, and the ideal sensor as a bound):
  revJ_held    Rev J with the nose held (no tracker): the heavier pen's own effect (tip tremor only; not read)
  revJ_g4      sim2j's guarded tracker G4 ported to HW1 (the second baseline)
  revJ_new     the design frozen on the tuning split (results/realtrack/frozen.json)
  revJ_info_*  other finalists, for information (tip tremor; read at the severe class only)
Reading budget (the reader costs about 5 s per line): the chosen design at every class and on the clean notes; G4 and
the information rows at the severe class and on the clean notes; the rest are measured by tip tremor only.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import CACHE_DIR, REPO_ROOT, RESULTS_DIR
from . import estimators as E

TEST_DIR = CACHE_DIR / "test"
R_CACHE = REPO_ROOT / "realdata" / "build" / "cache" / "hw1" / "full_v2"
FROZEN = RESULTS_DIR / "frozen.json"
R_HEADLINE = ["none", "revH_akf|deltapen", "revJ_gated|deltapen", "revJ_tcn|deltapen", "revJ_oracle"]
R_BOUND = ["revH_akf", "revJ_gated", "revJ_tcn"]


def load_frozen() -> Dict:
    if not FROZEN.exists():
        raise RuntimeError("results/realtrack/frozen.json is missing: the test runs only after the freeze (tune.py)")
    return json.loads(FROZEN.read_text())


def new_designs(fr: Dict) -> Dict[str, Dict]:
    out = {"revJ_g4": fr["g4"], "revJ_new": fr["chosen"]}
    for k, d in (fr.get("info") or {}).items():
        out[f"revJ_info_{k}"] = d
    return out


def ocr_plan(fr: Dict) -> Dict[str, set]:
    """Reading budget (one process; the reader costs about 5 s per line): the chosen design everywhere; G4 and the
    information rows marked 'read' (fr['info_read']) at the severe class and on the clean notes; the rest by tip
    tremor only."""
    info = {f"revJ_info_{k}|deltapen" for k in (fr.get("info_read") or [])}
    return {"severe": {"revJ_new|deltapen", "revJ_g4|deltapen"} | info,
            "moderate": {"revJ_new|deltapen"}, "mild": {"revJ_new|deltapen"},
            "clean": {"revJ_new|deltapen", "revJ_g4|deltapen"} | info}


def sensors_of(name: str):
    """The chosen design runs with both page sensors (the ideal one as R's labelled bound); the others with the
    headline DeltaPen-class sensor only (compute budget)."""
    return ("ideal", "deltapen") if name == "revJ_new" else ("deltapen",)


def _run_design(name: str, design: Dict, sJ, wr, f0: float, clean: bool, read: bool, out: Dict, keep: Optional[Dict],
                sensor: str):
    from realdata import hw1 as H
    from handwriting import plant as PL
    from ai2 import delayed as DL
    t0 = time.time()
    fam = design["family"]

    class _Case:                       # what the gated family needs (the Rev H tracker's estimate on the same streams)
        def __init__(self, dh):
            self._dh = dh
            self.spec = {"split": "test"}

        def dh_revh(self, s):
            return self._dh
    d, info = E.estimate(design, sJ.streams, case=_Case(sJ.dh), sensor=sensor, horizon=design.get("horizon"))
    q = -d
    r = PL.run(sJ.scn, sJ.pen, wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
    key = name if sensor == "ideal" else f"{name}|{sensor}"
    m = H.measures(wr, r, sJ.scn, sJ.pen, read, f0)
    if clean:
        m["false_correction_um"] = DL.ink_timeline_error(sJ, r, np.zeros(len(sJ.dh)), sJ.neutral)
    con = np.interp(sJ.streams.tick_t, r.t, r.contact) > 0.5
    if "auth_g" in (info or {}):
        m["auth_mean"] = float(np.mean(info["auth_g"][con])) if con.any() else float("nan")
    if "det_gate" in (info or {}):
        m["gate_open"] = float(np.mean(np.asarray(info["det_gate"]) > 0.5))
    m["est_s"] = time.time() - t0
    out[key] = m
    if keep is not None:
        keep[key] = r


def run_case(wr, tremor, f0: float, amp: float, case_key: str, designs: Dict[str, Dict], read_keys: set,
             keep: bool = False) -> Dict:
    from realdata import hw1 as H
    pm = H.page_model()
    clean = tremor is None
    out: Dict = {}
    runs = {} if keep else None
    base = None
    for sensor in ("ideal", "deltapen"):
        sJ = H.make_scen(wr, "revJ", tremor, f0, amp, 0, H._seed(case_key, "revJ"),
                         page=None if sensor == "ideal" else pm, base=base)
        base = base or sJ
        if sensor == "ideal" and not clean:
            out["revJ_held"] = H.measures(wr, sJ.neutral, sJ.scn, sJ.pen, False, f0)
        for name, dz in designs.items():
            if sensor not in sensors_of(name):
                continue
            k = name if sensor == "ideal" else f"{name}|{sensor}"
            _run_design(name, dz, sJ, wr, f0, clean, k in read_keys, out, runs, sensor)
    if keep:
        out["_runs"] = runs
    return out


def run(log=print, quick: bool = False) -> List[Dict]:
    """Every test case (resumable, one JSON per case); returns the merged cases (R's pens + the new rows)."""
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import ocr as OC
    fr = load_frozen()
    designs = new_designs(fr)
    plan = ocr_plan(fr)
    tdir = TEST_DIR if not quick else CACHE_DIR.parent / "quick" / "test"
    tdir.mkdir(parents=True, exist_ok=True)
    OC.reader_choice(log=log)
    H.ai2_models()
    H.page_model(False, log)
    P = H.plan(False)
    notes = P["real"]["writers"][:1] if quick else P["real"]["writers"]
    classes = ["severe"] if quick else ["severe", "moderate", "mild"]
    merged = []
    for i in notes:
        wr = None
        todo = [("clean", None, None)] + [(cls, kind, cls) for cls in classes for kind in P["real"]["kinds"]]
        for tag, kind, cls in todo:
            name = f"clean_real_w{i}" if kind is None else f"real_w{i}_{kind}_{cls}"
            p = tdir / f"{name}.json"
            if p.exists():
                res = json.loads(p.read_text())
            else:
                t0 = time.time()
                wr = wr or H.real_writer("test", i)
                if kind is None:
                    dev = run_case(wr, None, 0.0, 0.0, f"clean:{i}", designs, plan["clean"])
                    res = {"set": "clean_real", "writer": wr.written.real["writer"], "note": i, "devices": dev}
                else:
                    dr = RL.tremor_for(wr.written, cls, seed=i, kind=kind, split="test",
                                       amp_mm=RL.classes(False)[cls]["representative_mm"])
                    dev = run_case(wr, dr.d, dr.meta["f0"], dr.meta["amp_mm"] * 1e-3, f"real:{i}:{kind}:{cls}",
                                   designs, plan[cls])
                    res = {"set": "real", "writer": wr.written.real["writer"], "note": i, "kind": kind, "class": cls,
                           "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")},
                           "devices": dev}
                res["_elapsed_s"] = time.time() - t0
                p.write_text(json.dumps(res, default=H._jd))
                log(f"[test] {name} in {res['_elapsed_s']:.0f} s: " + H._fmt(res["devices"]))
            merged.append(merge_r(name, res))
    return merged


def merge_r(name: str, mine: Dict) -> Dict:
    """R's cached per-case results (its pens) + the new rows; the case identity is checked."""
    r = json.loads((R_CACHE / f"{name}.json").read_text())
    assert r["writer"] == mine["writer"] and r.get("kind") == mine.get("kind"), name
    if mine.get("tremor"):
        assert r["tremor"]["rid"] == mine["tremor"]["rid"] and abs(r["tremor"]["amp_mm"] - mine["tremor"]["amp_mm"]) < 1e-12
    out = dict(r)
    out["devices"] = dict(r["devices"])
    out["devices"].update({k: v for k, v in mine["devices"].items() if not k.startswith("_")})
    return out


# ------------------------------------------------------------------ aggregation (R's cards, R's bootstrap)
def devices_all(fr: Dict) -> List[str]:
    names = list(new_designs(fr).keys())
    return (R_HEADLINE + R_BOUND + ["revJ_held"] + [f"{n}|deltapen" for n in names] + names)


def aggregate(cases: List[Dict], fr: Dict) -> Dict:
    from realdata import hw1 as H
    devs = devices_all(fr)
    out = {"real": {}, "clean": {}, "devices": devs}
    real = [c for c in cases if c["set"] == "real"]
    clean = [c for c in cases if c["set"] == "clean_real"]
    for kind in sorted({c["kind"] for c in real}) + ["all"]:
        for cls in ("mild", "moderate", "severe"):
            sel = [c for c in real if (kind == "all" or c["kind"] == kind) and c["class"] == cls]
            if sel:
                cd = H.card(sel, devs, clean)
                cd["_amp_mm_mean"] = float(np.mean([c["tremor"]["amp_mm"] for c in sel]))
                cd["_f0_mean"] = float(np.mean([c["tremor"]["f0"] for c in sel]))
                cd["_n_cases"] = len(sel)
                cd["_n_writers"] = len({c["writer"] for c in sel})
                out["real"][f"{kind}/{cls}"] = cd
    cd = {}
    for dev in devs:
        if not any(dev in c["devices"] for c in clean):
            continue
        pw = H._per_writer(clean, dev, "false_correction_um")
        vals = [float(v) for v in pw.values() if np.isfinite(v)]
        cd[dev] = {"words_of_10": H._boot(H._per_writer(clean, dev, "", fn=H._of10)),
                   "false_correction_um": H._boot(pw),
                   "false_correction_um_worst_writer": max(vals) if vals else float("nan")}
    out["clean"]["clean_real"] = cd
    return out


def dec055(ag: Dict, dev: str = "revJ_new|deltapen") -> Dict:
    """DEC-055's line at the severe class (PD and ET pooled): >= +2 words of 10 over the ordinary pen with the 95 %
    writer-bootstrap interval above 0, and <= 25 um of clean-writing change as the mean over the test writers with no
    single writer above 50 um (docs/decisions.md, DEC-055 as now worded)."""
    c = ag["real"].get("all/severe", {}).get(dev)
    fcd = ag["clean"]["clean_real"].get(dev, {})
    fc = fcd.get("false_correction_um", {})
    worst = fcd.get("false_correction_um_worst_writer", float("nan"))
    if not c:
        return {"device": dev, "evaluated": False}
    g = c.get("words_of_10_gain", {})
    ok_words = bool(g.get("mean", -np.inf) >= 2.0 and g.get("lo", -np.inf) > 0.0)
    ok_mean = bool(fc.get("mean", np.inf) <= 25.0)
    ok_worst = bool(np.isfinite(worst) and worst <= 50.0)
    return {"device": dev, "evaluated": True, "words_gain_mean": g.get("mean"), "words_gain_lo": g.get("lo"),
            "words_gain_hi": g.get("hi"), "clean_change_um_mean": fc.get("mean"), "clean_change_um_hi": fc.get("hi"),
            "clean_change_um_worst_writer": worst, "passes_words": ok_words, "passes_clean_mean": ok_mean,
            "passes_clean_worst": ok_worst, "passes_clean": ok_mean and ok_worst,
            "passes": ok_words and ok_mean and ok_worst,
            "rule": "DEC-055: severe class, PD and ET pooled, >= 2 more readable words out of 10 than the ordinary pen "
                    "with the 95 % writer-bootstrap interval above 0, and <= 25 um of clean-writing change as the mean "
                    "over the test writers, with no single writer above 50 um"}


# ------------------------------------------------------------------ the before/after pictures (CC BY cases of R)
R_PIC = REPO_ROOT / "realdata" / "build" / "cache" / "pictures_v2"
PIC_IDS = ("ct_PD_severe", "ct_ET_severe", "ct_PD_moderate", "ct_ET_moderate")


def picture_runs(log=print, ids: Sequence[str] = PIC_IDS) -> List[Dict]:
    """R's committed picture cases (CC BY letters and tremor, test split; realdata/report.picture_cases) with the
    frozen design added on the same writer, tremor, scenario and sensor draws (R's case key 'picture:<id>')."""
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import ocr as OC
    from handwriting import metrics as MT
    fr = load_frozen()
    dz = fr["chosen"]
    out = []
    pdir = TEST_DIR / "pictures"
    pdir.mkdir(parents=True, exist_ok=True)
    for pid in ids:
        p = pdir / f"{pid}.json"
        if p.exists():
            out.append(json.loads(p.read_text()))
            continue
        r = json.loads((R_PIC / f"{pid}.json").read_text())
        pc = r["case"]
        OC.reader_choice(log=log)
        wr_ = RL.writing("test", seed=pc["seed"], source=pc["source"])
        wr = H.Writer(wr_, 900_000 + int(hashlib.sha1(pc["id"].encode()).hexdigest()[:5], 16))
        dr = RL.tremor_for(wr_, pc["class"], seed=pc["seed"], kind=pc["kind"], split="test", amp_mm=pc["amp_mm"])
        assert dr.meta["rid"] == r["tremor"]["rid"]
        res = run_case(wr, dr.d, dr.meta["f0"], pc["amp_mm"] * 1e-3, f"picture:{pc['id']}", {"revJ_new": dz},
                       {"revJ_new|deltapen"}, keep=True)
        runs = res.pop("_runs")
        merged = dict(r)
        merged["devices"] = dict(r["devices"])
        merged["devices"].update({k: v for k, v in res.items() if not k.startswith("_")})
        merged["paths"] = dict(r["paths"])
        merged["paths"]["revJ_new|deltapen"] = MT.decimate_path(runs["revJ_new|deltapen"], hz=50.0).round(3).tolist()
        p.write_text(json.dumps(merged, default=H._jd))
        log(f"[pictures] {pid}: none {r['devices']['none']['words_read']}, new "
            f"{merged['devices']['revJ_new|deltapen'].get('words_read')} of {r['devices']['none']['words_total']}")
        out.append(merged)
    return out
