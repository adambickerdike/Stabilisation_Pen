"""results/realtrack/realtrack.json (with stabpen.provenance), the figures with CSV twins and evidence_rows.csv.

Everything numeric is read from the stage caches (realtrack/build) and R's cache (read-only); evidence labels are
attached per block.  The document docs/real_tracker.md quotes these numbers.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import BUILD_DIR, CACHE_DIR, EVIDENCE_CALC, EVIDENCE_SIM, REPO_ROOT, RESULTS_DIR, __version__
from . import cases as C
from . import tune as TU


def provenance(extra: Optional[Dict] = None) -> Dict:
    from stabpen import provenance as PV
    files = {}
    for rel in ("results/nose2/nose2.json", "results/opt/inertial_tracker_revh.json", "results/sim2j/rules.json",
                "results/ai2/ai2.json", "results/realdata/realdata.json"):
        p = REPO_ROOT / rel
        if p.exists():
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return PV.metadata(EVIDENCE_SIM, seeds={"splits": "study R's tuning/test split of writers, texts and patients; "
                                                      "every choice on the tuning split, the test split run once",
                                            "bootstrap": "R's: 2000 writer resamples, seed 20260929"},
                       extra={"package": f"realtrack-{__version__}", "inputs_sha256_16": files, **(extra or {})})


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def tuning_summary() -> Dict:
    out = {"rules": TU.__doc__, "selection_set": C.__doc__.split("TUNING SET")[1].split("TEST SET")[0].strip(),
           "stage1": {}, "stage2_amplitude_only": {}, "binary_gate": None, "soft_confidence": None, "joint_akf": None}
    for fam in ("akf", "wflc", "bmflc", "bmflc_kf", "epll"):
        s = TU.load_search(f"s1_{fam}")
        if s:
            b = s["best"]
            init = s["history"][0]
            out["stage1"][fam] = {"best_params": b["params"], "J_severe_bb": b["summary"]["severe_bb"],
                                  "severe_ratio": b["summary"]["severe_ratio"],
                                  "severe_PD_ratio": b["summary"].get("severe_PD_ratio"),
                                  "severe_ET_ratio": b["summary"].get("severe_ET_ratio"),
                                  "literature_start": {"params": init["params"], "J": init["summary"]["severe_bb"],
                                                       "severe_ratio": init["summary"]["severe_ratio"]},
                                  "n_evaluations": len(s["history"])}
    for fam in ("akf", "wflc", "epll"):
        s = _load(TU.TUNE_DIR / f"auth_s2_{fam}_amp.json")
        if s:
            b = s["best"]
            out["stage2_amplitude_only"][fam] = {"best_params": b["params"], "summary": b["summary"],
                                                 "passes": TU.passes(b["summary"]), "front": front(s["history"])}
    s = _load(TU.TUNE_DIR / "gate_s2_gate_listen.json")
    if s:
        out["binary_gate"] = {"best_params": s["best"]["params"], "summary": s["best"]["summary"],
                              "passes": TU.passes(s["best"]["summary"]),
                              "R_setting": s["history"][0]["summary"], "G4_like_setting": s["history"][1]["summary"],
                              "front": front(s["history"])}
    s = _load(TU.TUNE_DIR / "auth_s2_listen_conf.json")
    if s:
        out["soft_confidence"] = {"best_params": s["best"]["params"], "summary": s["best"]["summary"],
                                  "passes": TU.passes(s["best"]["summary"]), "front": front(s["history"])}
    s = _load(TU.TUNE_DIR / "joint_akf.json")
    if s:
        out["joint_akf"] = {"best_raw": s["best"]["raw"], "best_auth": s["best"]["auth"], "summary": s["best"]["summary"],
                            "passes": TU.passes(s["best"]["summary"]), "front": front(s["history"])}
    s = _load(TU.TUNE_DIR / "auth_net_main.json")
    if s:
        out["net_authority"] = {"best_params": s["best"]["params"], "summary": s["best"]["summary"],
                                "passes": TU.passes(s["best"]["summary"]), "front": front(s["history"])}
    return out


def front(hist: List[Dict]) -> List[Dict]:
    """The clean-change / severe-ratio Pareto front of a search history (points passing T3 and T4 only)."""
    pts = []
    for h in hist:
        s = h["summary"]
        ok = TU.passes(s)
        if ok["T3"] and ok["T4"]:
            pts.append({"clean_um": s.get("clean_um_mean"), "clean_um_max": s.get("clean_um_max"),
                        "severe_ratio": s.get("severe_ratio"), "severe_bb": s.get("severe_bb")})
    pts.sort(key=lambda p: p["clean_um"])
    out, best = [], np.inf
    for p in pts:
        if p["severe_ratio"] < best - 1e-6:
            best = p["severe_ratio"]
            out.append(p)
    return out


def all_points(hist: List[Dict]) -> List[Dict]:
    return [{"clean_um": h["summary"].get("clean_um_mean"), "severe_ratio": h["summary"].get("severe_ratio"),
             "severe_bb": h["summary"].get("severe_bb")} for h in hist
            if np.isfinite(h["summary"].get("clean_um_mean", np.nan))]


def one_number_table(ag: Dict, new: str = "revJ_new|deltapen") -> List[Dict]:
    rows = []
    for kind, kn in (("PD", "Parkinson's"), ("ET", "Essential tremor"), ("all", "Both, pooled")):
        for cls in ("severe", "moderate", "mild"):
            cd = ag["real"].get(f"{kind}/{cls}")
            if not cd:
                continue

            def w(dev):
                v = cd.get(dev, {}).get("words_of_10")
                return None if not v or not np.isfinite(v.get("mean", np.nan)) else v
            rows.append({"kind": kind, "label": kn, "class": cls, "amp_mm": cd["_amp_mm_mean"],
                         "ceiling": (cd.get("none", {}) or {}).get("clean_words_of_10"),
                         "ordinary": w("none"), "best_causal": w(new), "perfect": w("revJ_oracle"),
                         "rev_j_gated": w("revJ_gated|deltapen"), "g4": w("revJ_g4|deltapen"),
                         "gain": (cd.get(new) or {}).get("words_of_10_gain")})
    return rows


def write(quick: bool = False, log=print) -> Dict:
    from . import delay as DY
    from . import figures as FG
    from . import mcu as MC
    from . import test as T
    od = RESULTS_DIR if not quick else BUILD_DIR / "quick" / "results"
    od.mkdir(parents=True, exist_ok=True)
    fr = T.load_frozen()
    cases = T.run(log=lambda *a: None, quick=quick)
    ag = T.aggregate(cases, fr)
    out = {"stabpen.provenance": provenance({"quick": quick}),
           "evidence": {"sim": EVIDENCE_SIM, "calc": EVIDENCE_CALC},
           "question": "Can a causal tremor estimator, small enough for the pen's microcontroller, make real "
                       "tremor-affected writing more readable while leaving clean real writing alone?",
           "reproduction_of_R": _load(CACHE_DIR / "repro" / "summary.json"),
           "tuning": tuning_summary(), "frozen": {k: fr[k] for k in ("frozen_utc", "chosen_name", "why", "chosen", "g4",
                                                                      "tuning_full_plant")},
           "test": {"cards": ag, "one_number_table": one_number_table(ag),
                    "dec055": {"chosen": T.dec055(ag, "revJ_new|deltapen"), "g4": T.dec055(ag, "revJ_g4|deltapen"),
                               "R_gated": T.dec055(ag, "revJ_gated|deltapen"), "R_tcn": T.dec055(ag, "revJ_tcn|deltapen")},
                    "n_cases": len(cases), "reuse_of_R": "R's pens read from R's cache (bit-identical re-run: repro)"},
           "mcu": MC.table()}
    # extra blocks produced by other stages (if present)
    for k, p in (("delay", BUILD_DIR / "delay.json"), ("separability", BUILD_DIR / "separability.json"),
                 ("learned", BUILD_DIR / "learned.json"), ("sim2", BUILD_DIR / "sim2.json"),
                 ("chosen_mcu", BUILD_DIR / "chosen_mcu.json")):
        v = _load(p)
        if v is not None:
            out[k] = v
    (od / "realtrack.json").write_text(json.dumps(out, indent=1, default=float))
    log(f"[report] {od / 'realtrack.json'}")
    figures(out, od, fr, quick, log)
    from . import evidence as EVD
    EVD.write(od / "evidence_rows.csv", out)
    log(f"[report] {od / 'evidence_rows.csv'}")
    return out


FAMILY_LABEL = {"auth_s2_akf_amp": "AKF + amplitude gate", "auth_s2_wflc_amp": "WFLC + amplitude gate",
                "auth_s2_epll_amp": "EPLL + amplitude gate", "gate_s2_gate_listen": "listening + binary gate",
                "auth_s2_listen_conf": "listening + soft confidence", "joint_akf": "AKF + gate, tuned jointly",
                "auth_net_main": "TCN (real data) + gate", "auth_ai2tcn": "ai2 TCN (synthetic) + gate",
                "gate_s2_glg": "GLG (G4 fallback), retuned"}


def figures(out: Dict, od: Path, fr: Dict, quick: bool, log=print) -> None:
    from . import figures as FG
    from . import test as T
    ag = out["test"]["cards"]
    devs = ["none", "revJ_gated|deltapen", "revJ_g4|deltapen", "revJ_new|deltapen", "revJ_oracle"]
    FG.words_chart(od, ag, devs)
    FG.tremor_chart(od, ag, devs)
    fronts = {}
    for stem, lab in FAMILY_LABEL.items():
        v = _load(TU.TUNE_DIR / f"{stem}.json")
        if v:
            fronts[lab] = all_points(v["history"])
    ch = (fr.get("tuning_full_plant") or {}).get(fr.get("chosen_name")) or {}
    chosen = None
    if ch:
        chosen = {"clean_um": ch["summary"].get("clean_um_mean"), "severe_ratio": ch["summary"].get("severe_ratio")}
    FG.tradeoff_chart(od, fronts, chosen)
    if out.get("separability"):
        FG.separability_chart(od, out["separability"])
    dl = out.get("delay")
    if dl:
        FG.delay_chart(od, dl["servo_lag"], dl["decompose"], dl["horizon"])
    if not quick:
        for pr in T.picture_runs(log=log):
            FG.picture(od, pr)
    log("[report] figures written")
