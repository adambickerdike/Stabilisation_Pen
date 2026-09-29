"""Stage 'cues' (task 2): compare the physical feedback options (SIMULATION with ASSUMED writer responses).

Uses the checker's letter-by-letter outputs on the Holbrook children (stage 'spell'), the recogniser's commit timing
(stage 'online'/'calib') and the nose's reach (CALC on real UJI letters at a 3 mm x-height).  Rule S4 picks the
recommended cue on the TUNING children; the test children are scored once.
"""
from __future__ import annotations

import time
from typing import Dict, List

import numpy as np

from . import ensure_paths
from . import common as C
from . import cues as CU
from . import data as D
from . import online as O
from .rules import RULES, rules_sha256

ensure_paths()

PLAN_REACH_MM = 5.5          # the Rev J nose's autowrite plan reach (SIM nose_v2: 6 mm guaranteed minus 0.5 mm margin)
THETA_B = (0.02, 0.03, 0.05, 0.08, 0.12)


def reach_share(letters, xh) -> Dict:
    """CALC: share of (previous, next) letter pairs of the test writers whose next letter lies entirely within the plan
    reach of a hand held still at the previous letter's last point (3 mm x-height, 0.35 x-height gap)."""
    by: Dict[str, List] = {}
    for L in letters:
        if O.split_of(L.writer) == "test":
            by.setdefault(L.writer, []).append(L)
    rng = np.random.default_rng(3)
    ok, dists = [], []
    for w, Ls in by.items():
        f = O.XH_MM / xh[w]
        for _ in range(60):
            a, b = Ls[int(rng.integers(len(Ls)))], Ls[int(rng.integers(len(Ls)))]
            A = [np.asarray(s) * f for s in a.strokes]; B = [np.asarray(s) * f for s in b.strokes]
            end = A[-1][-1]
            ax = np.vstack(A)[:, 0].max()
            Bp = np.vstack(B)
            Bp = Bp + np.array([ax + 0.35 * O.XH_MM - Bp[:, 0].min(), 0.0])
            d = float(np.max(np.hypot(Bp[:, 0] - end[0], Bp[:, 1] - end[1])))
            dists.append(d); ok.append(d <= PLAN_REACH_MM)
    return {"share_within_reach": float(np.mean(ok)), "max_distance_mm_median": float(np.median(dists)),
            "max_distance_mm_p90": float(np.percentile(dists, 90)), "n_pairs": len(ok), "plan_reach_mm": PLAN_REACH_MM}


def warnings_fa(records, theta_b) -> float:
    n = fa = 0
    for recs in records:
        for u in recs:
            if u["kind"] != "correct" or not u["tokens"]:
                continue
            n += 1
            fa += int(CU.warn_at(u["tokens"][0], theta_b) is not None)
    return 100.0 * fa / max(n, 1)


def run(quick: bool) -> Dict:
    t0 = time.time()
    sp = C.load("spell_NG1x", quick)
    if sp is None:
        raise RuntimeError("stage 'spell' must run first")
    on = C.load("online", quick) or {}
    cal = C.load("online_cal", quick) or {}
    com = (cal.get("test") or {}).get("commit") or (on.get("test") or {}).get("commit") or {}
    commit = {"p_before_end": float(com.get("committed_before_end_share", 0.5)),
              "frac_median": float(com.get("median_fraction_at_commit", 0.7) or 0.7)}
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    reach = reach_share(letters, xh)
    theta, theta_w = sp["test"]["theta"], sp["test"]["theta_w"]
    # rule S5 on the tuning children
    s5 = {f"{tb:g}": warnings_fa(sp["records_tune"], tb) for tb in THETA_B}
    ok = [tb for tb in THETA_B if s5[f"{tb:g}"] <= 5.0]
    theta_b = min(ok) if ok else max(THETA_B)
    # rule S4 on the tuning children
    tune = CU.run_all(sp["records_tune"], theta, theta_w, theta_b, commit, reach["share_within_reach"], seed=1,
                      n_rep=5 if quick else 20)
    def admissible(r, nominal_only=False):
        return (r["false_interventions_per_100_correct"] <= 2.0 and r["extra_time_pct"] <= 25.0
                and (r["cue"] != "show_me" or True))
    physical = [c for c in CU.CUES if c not in ("none", "app_after", "show_me")]
    cand = [c for c in physical if admissible(tune["nominal"][c])]
    rec = max(cand, key=lambda c: tune["nominal"][c]["fixed_on_paper_per_10_errors"]) if cand else None
    fragile = bool(rec) and not admissible(tune["low"][rec]) or (
        bool(rec) and any(tune["low"][c]["fixed_on_paper_per_10_errors"] > tune["low"][rec]["fixed_on_paper_per_10_errors"]
                          for c in cand if c != rec))
    out = {"commit": commit, "reach": reach, "theta": theta, "theta_w": theta_w, "S5": {"table": s5, "theta_b": theta_b},
           "S4": {"tuning": tune, "admissible": cand, "recommended": rec, "fragile": fragile},
           "rules_sha256": rules_sha256(), "rules": {k: RULES[k] for k in ("S4_policy", "S5_warn")}}
    C.log(f"[cues] rule S5 -> theta_b {theta_b}; rule S4 -> recommended '{rec}' (fragile: {fragile})")
    test = CU.run_all(sp["records_test"], theta, theta_w, theta_b, commit, reach["share_within_reach"], seed=2,
                      n_rep=5 if quick else 20)
    out["test"] = test
    # with recognised letters (the checker saw the recogniser's letters): nominal responses
    out["test_with_recognition"] = {}
    for name, blk in (sp.get("with_recognition") or {}).items():
        out["test_with_recognition"][name] = {c: CU.simulate(blk["records"], c, theta, theta_w, theta_b, CU.Response(),
                                                             commit, reach["share_within_reach"], seed=3,
                                                             n_rep=5 if quick else 10) for c in CU.CUES}
    out["minutes"] = (time.time() - t0) / 60
    C.save("cues", out, quick)
    for c in CU.CUES:
        r = test["nominal"][c]
        C.log(f"[cues] test {c}: fixed on paper {r['fixed_on_paper_per_10_errors']:.2f}/10, FA {r['false_interventions_per_100_correct']:.2f}/100, "
              f"time +{r['extra_time_pct']:.1f} %")
    return out
