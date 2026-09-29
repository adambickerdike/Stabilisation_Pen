r"""P4, the end-cap part: the lightest reaction-mass end-cap that keeps study K's rule R-T1.

Method (SIM with study K's models, read-only: endcap/design.py, endcap/optimise.py, endcap/sim.py; model H1 of
sim/handpen through opt/inertial; synthetic writing and tremor; the Rev H pen and its causal tracker, as study K).

  family     study K's recommended LRM2 design (slug d 11.65 mm, coil 0.676 mm per side, +-4.0 mm stroke) with a
             shorter tungsten slug: L_s 15.0 (study K) ... 5.0 mm.  Mass, force constant, coil force and the flexure
             follow study K's design model (endcap.design.lrm2) unchanged.
  gain       study K's feed-forward gain 0.75 (tuned on seeds 300-303 for the 45 g design) is kept for every member
             (ASSUMPTION: re-tuning per mass is not done here).
  stage 1    TUNING seeds 300-303 only: splits 0.3 / 0.5 / 0.7, 8-12 Hz x 1-2 mm (24 cases per split and member).
  rule J1-M1 (fixed here before any test run): choose the LIGHTEST member whose tuning further reduction is
             >= 12 % at split 0.5 (R-T1's 10 % plus a 2-point allowance for tuning-to-test shrinkage: study K's 45 g
             design fell from 20.2 % on tuning to 18.2 % on test) and >= 6 % at splits 0.3 and 0.7 (R-T1's 5 % + 1 point).
  stage 2    TEST seeds 200-203, study K's full test grid (4-12 Hz x 0.3 / 1 / 2 mm, three splits) for the chosen member
             and the next heavier one (fallback), with R-T1 exactly as study K's report.rule_RT1 applies it; plus the same
             total mass fixed (passive weight), for DEC-038's revisit trigger ("the fixed weight comes within 5 points").
Results are cached in results/revJ1/_cache/ (JSON rows) so python3 -m revj1.run reuses them.

Limits: study K's pen is Rev H (75 g, Rev H nose +-3 mm, Rev H tracker), not Rev J.1; the ratios rank end-cap masses
on that model and are not evidence of benefit (DEC-040's context of use).  Nothing measured.
"""
from __future__ import annotations

import json
import math
import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import CACHE_DIR, REPO_ROOT, ensure_paths

ensure_paths()

STUDY_K_GAIN = 0.75                        # SIM, study K tuning (results/endcap/endcap_study.json -> tuning.chosen.lrm)
L_S_FAMILY_MM = (14.98, 11.0, 9.0, 7.5, 6.0, 5.0)      # 14.98 mm = study K's chosen design exactly
TUNE_SEEDS = (300, 301, 302, 303)
TEST_SEEDS = (200, 201, 202, 203)
TUNE_CONDS = tuple((f, a) for f in (8.0, 10.0, 12.0) for a in (1e-3, 2e-3))
TEST_F = (4.0, 6.0, 8.0, 10.0, 12.0)
TEST_A = (0.3e-3, 1e-3, 2e-3)
SPLITS = (0.3, 0.5, 0.7)
RULE_J1_M1 = {"split_0.5_min": 0.12, "split_0.3_0.7_min": 0.06,
              "text": "lightest member with tuning further reduction (8-12 Hz x 1-2 mm) >= 12 % at split 0.5 and >= 6 % at "
                      "splits 0.3 and 0.7 (R-T1's 10 % / 5 % plus a 2-point / 1-point allowance for tuning-to-test shrinkage)"}


def _studyK_chosen() -> Dict:
    return json.loads((REPO_ROOT / "results" / "endcap" / "_cache" / "stage_optimise.json").read_text())["chosen"]["lrm"]


def member(L_s_mm: float) -> Dict:
    """Study K's LRM2 design with the slug length L_s (CALC, endcap.optimise.summarize on endcap.design.lrm2)."""
    from endcap import optimise as OP
    ref = _studyK_chosen()
    x = dict(ref["x"])
    if abs(L_s_mm * 1e-3 - x["L_s"]) > 0.05e-3:                  # within 0.05 mm: study K's own design, unchanged
        x["L_s"] = L_s_mm * 1e-3
    s = OP.summarize("LRM2", x, ())
    s["L_s_mm"] = x["L_s"] * 1e3
    s["label"] = "CALC (study K design model endcap.design.lrm2, read-only; slug length varied here)"
    return s


def _cache_path(name: str, quick: bool):
    d = CACHE_DIR / ("quick" if quick else "full")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"endcap_{name}.json"


def _load(name: str, quick: bool) -> Optional[Dict]:
    p = _cache_path(name, quick)
    return json.loads(p.read_text()) if p.exists() else None


def _save(name: str, obj: Dict, quick: bool) -> None:
    from stabpen import provenance
    p = _cache_path(name, quick)
    obj = dict(obj)
    obj.setdefault("meta", provenance.metadata("SIMULATION (study K model H1 via endcap/sim.py, read-only; synthetic writing "
                                               "and tremor)", extra={"script": "revj1/endcap_mass.py"}))
    provenance.write_json(str(p), obj)


def _eval(s: Dict, split: float, seed: int, f0: float, a: float, active: bool = True, ev=None):
    from endcap import sim as S
    return ev.case(seed, f0, a, active=active)


def tune_stage(quick: bool = False, log=print, family: Sequence[float] = L_S_FAMILY_MM) -> Dict:
    """Stage 1 (tuning seeds only).  Cached."""
    from endcap import sim as S
    old = _load("tune", quick)
    if old is not None and old.get("family") == list(family):
        return old
    seeds = TUNE_SEEDS[:1] if quick else TUNE_SEEDS
    conds = ((10.0, 1e-3),) if quick else TUNE_CONDS
    splits = (0.5,) if quick else SPLITS
    out = {"family_mm": list(family), "family": list(family), "seeds": list(seeds), "conds": [list(c) for c in conds],
           "splits": list(splits), "gain": STUDY_K_GAIN, "rule": RULE_J1_M1, "members": {}}
    t0 = time.time()
    for L in family:
        s = member(L)
        dev = S.h1_device(s)
        rec = {"design": {k: s[k] for k in ("mass_g", "moving_mass_g", "X", "Km", "F_act", "P_avg_W", "parts_g", "L_s_mm", "x")},
               "label": dev.label, "rows": {}, "further_reduction": {}}
        for rr in splits:
            ev = S.TremorEval(dev, rr, gain=STUDY_K_GAIN, Km=s["Km"])
            rows = [ev.case(seed, f0, a) for seed in seeds for (f0, a) in conds]
            rec["rows"][str(rr)] = rows
            fr = [1.0 - c["nose+dev"] / c["nose"] for c in rows]
            rec["further_reduction"][str(rr)] = {"mean": float(np.mean(fr)), "min": float(np.min(fr)),
                                                 "P_act_W_mean": float(np.mean([c["P_act_W"] for c in rows])),
                                                 "stroke_pk_mm_max": float(np.max([max(c["stroke_pk_mm"]) for c in rows]))}
            log(f"[{time.time() - t0:6.1f}s] end-cap L_s {L:4.1f} mm ({s['mass_g']:.1f} g) split {rr}: further reduction "
                f"{np.mean(fr) * 100:5.1f} %")
        out["members"][f"{L:g}"] = rec
    out["chosen"] = choose(out)
    _save("tune", out, quick)
    return out


def choose(tune: Dict) -> Dict:
    """Rule J1-M1 on the tuning results (see the module docstring)."""
    ok = []
    for k, m in tune["members"].items():
        fr = m["further_reduction"]
        c5 = fr.get("0.5", {}).get("mean", -1)
        c3 = fr.get("0.3", {}).get("mean", 1)
        c7 = fr.get("0.7", {}).get("mean", 1)
        passes = c5 >= RULE_J1_M1["split_0.5_min"] and c3 >= RULE_J1_M1["split_0.3_0.7_min"] and c7 >= RULE_J1_M1["split_0.3_0.7_min"]
        ok.append((m["design"]["mass_g"], k, passes))
    ok.sort()
    passing = [k for (_, k, p) in ok if p]
    if not passing:
        return {"L_s_mm": None, "note": "no member passes on tuning seeds: keep study K's 45 g design"}
    light = passing[0]
    heavier = [k for (mg, k, p) in ok if p and tune["members"][k]["design"]["mass_g"] > tune["members"][light]["design"]["mass_g"]]
    return {"L_s_mm": float(light), "fallback_L_s_mm": float(heavier[0]) if heavier else None,
            "mass_g": tune["members"][light]["design"]["mass_g"], "rule": RULE_J1_M1["text"]}


# Rule J1-M2, written after the tuning stage showed that no member lighter than study K's passes the split-0.3 part of R-T1
# on tuning seeds (4.5 % at 36.3 g, 6.0 % at 45 g) and BEFORE any test run of a lighter member: test the members with
# L_s 9.0, 7.5 and 5.0 mm (31.6, 28.0 and 22.0 g; the ones that can keep the pen with the end-cap near or under 120 g).
# Rev J.1 takes the heaviest tested member that (i) keeps the pen with the end-cap <= 120 g with the Rev J.1 base pen and
# (ii) passes the split-0.5 part of R-T1 (>= 10 %) with no split worse on average; its split-0.3 and 0.7 results are
# reported against R-T1's 5 % as they fall (a shortfall is stated, not tuned away).
RULE_J1_M2 = {"members_mm": [9.0, 7.5, 5.0],
              "text": "heaviest tested member (L_s 9.0 / 7.5 / 5.0 mm) that keeps the pen with the end-cap <= 120 g and passes "
                      "the split-0.5 part of R-T1 (>= 10 %) with no split worse on average on TEST seeds; splits 0.3 and 0.7 "
                      "reported against R-T1's 5 %"}


def test_stage(tune: Dict, quick: bool = False, log=print, members: Optional[Sequence[float]] = None, tag: str = "test") -> Dict:
    """Stage 2 (test seeds): rule J1-M1's choice, or the listed members (rule J1-M2).  Cached per tag."""
    from endcap import report as RP
    from endcap import sim as S
    ch = tune["chosen"]
    keys = list(members) if members is not None else [k for k in (ch.get("L_s_mm"), ch.get("fallback_L_s_mm")) if k is not None]
    old = _load(tag, quick)
    if old is not None and old.get("members_tested") == [float(k) for k in keys]:
        return old
    seeds = TEST_SEEDS[:1] if quick else TEST_SEEDS
    f0s = (10.0,) if quick else TEST_F
    amps = (1e-3,) if quick else TEST_A
    splits = (0.5,) if quick else SPLITS
    out = {"members_tested": [float(k) for k in keys], "seeds": list(seeds), "rows": {}, "verdicts": {}, "summary": {},
           "rule_R_T1": "study K's R-T1 (endcap/run_study.RULES) via endcap/report.rule_RT1; passive weight = the same total "
                        "mass fixed in the end-cap (nose + passive)"}
    t0 = time.time()
    for L in keys:
        s = member(L)
        dev = S.h1_device(s)
        wdev = S.weight_device(s["mass_g"] * 1e-3)
        rows, wrows = [], []
        for rr in splits:
            ev = S.TremorEval(dev, rr, gain=STUDY_K_GAIN, Km=s["Km"])
            ew = S.TremorEval(wdev, rr, gain=1.0)
            for seed in seeds:
                for f0 in f0s:
                    for a in amps:
                        rows.append(ev.case(seed, f0, a, active=True))
                        wrows.append(ew.case(seed, f0, a, active=False))
            log(f"[{time.time() - t0:6.1f}s] test L_s {L:g} mm split {rr}: {len(rows)} rows")
        name = f"lrm_{L:g}"
        out["rows"][name] = rows
        out["rows"][f"weight_{L:g}"] = wrows
        ts = RP.tremor_summary({"rows": {"lrm": rows, "weight_lrm": wrows}})
        P_avg = float(np.mean([c["P_act_W"] for c in rows]))
        out["summary"][name] = ts
        out["verdicts"][name] = RP.rule_RT1(ts, "lrm", s["P_avg_W"])
        out["verdicts"][name]["P_act_W_mean_SIM"] = P_avg
        out["verdicts"][name]["mass_g"] = s["mass_g"]
        _save(tag, out, quick)
    return out


def studyK_reference() -> Dict:
    """Study K's own test verdict for its 45 g design (SIM, results/endcap/endcap_study.json, read-only)."""
    d = json.loads((REPO_ROOT / "results" / "endcap" / "endcap_study.json").read_text())
    return {"verdict": d["recommendation"]["verdicts"]["lrm"], "design_mass_g": d["designs"]["lrm"]["mass_g"],
            "slug_g": d["designs"]["lrm"]["parts_g"]["slug_g"], "label": "SIM (study K, test seeds 200-203)"}


def summary(quick: bool = False, log=print, run_missing: bool = True) -> Dict:
    tune = _load("tune", quick)
    if tune is None and run_missing:
        tune = tune_stage(quick, log)
    if tune is None:
        return {"status": "not run"}
    test = _load("test", quick)
    if test is None and run_missing and tune["chosen"].get("L_s_mm") is not None:
        test = test_stage(tune, quick, log)
    fam = {k: {"mass_g": m["design"]["mass_g"], "slug_g": m["design"]["parts_g"]["slug_g"],
               "moving_mass_g": m["design"]["moving_mass_g"], "Km": m["design"]["Km"], "F_act_N": m["design"]["F_act"],
               "P_avg_W_design": m["design"]["P_avg_W"], "L_s_mm": m["design"]["L_s_mm"],
               "tune_further_reduction": {sp: v["mean"] for sp, v in m["further_reduction"].items()},
               "tune_P_act_W": {sp: v["P_act_W_mean"] for sp, v in m["further_reduction"].items()},
               "tune_stroke_pk_mm_max": {sp: v["stroke_pk_mm_max"] for sp, v in m["further_reduction"].items()}}
           for k, m in tune["members"].items()}
    return {"family": fam, "chosen_by_rule": tune["chosen"], "rule": RULE_J1_M1, "gain": STUDY_K_GAIN,
            "test": {"verdicts": (test or {}).get("verdicts"), "summary": (test or {}).get("summary"),
                     "members_tested": (test or {}).get("members_tested")},
            "studyK_45g": studyK_reference(),
            "label": "SIM (study K's model H1 and tracker cascade, read-only; tuning seeds 300-303 for the choice, test seeds "
                     "200-203 for the verdict; synthetic writing and tremor; Rev H pen)"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stage", default="all", choices=("tune", "test", "test2", "all"))
    a = ap.parse_args()
    t = tune_stage(a.quick)
    print(json.dumps(t["chosen"], indent=1))
    if a.stage in ("test", "all"):
        te = test_stage(t, a.quick)
        print(json.dumps(te["verdicts"], indent=1))
    if a.stage in ("test2", "all"):
        te2 = test_stage(t, a.quick, members=RULE_J1_M2["members_mm"], tag="test_j1m2")
        print(json.dumps(te2["verdicts"], indent=1))
