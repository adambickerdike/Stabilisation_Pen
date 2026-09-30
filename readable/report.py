"""results/readable/readable.json (with stabpen.provenance), the figures and the generated doc tables.

Every number is read from the stage caches (readable/build), R's cache and E's cache (read-only), with its evidence label.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from . import BUILD_DIR, EVIDENCE_CALC, EVIDENCE_SIM, REPO_ROOT, __version__
from . import common as CM

INPUT_FILES = (
    "results/realtrack/frozen.json", "results/realtrack/realtrack.json", "results/realdata/realdata.json",
    "results/nose2/nose2.json", "results/opt/inertial_tracker_revh.json", "results/sim2j/rules.json",
    "realtrack/build/models/net_net_main.pt", "realtrack/build/models/net_net_main_f0.pt",
    "realtrack/build/models/net_net_main_f1.pt", "realtrack/build/models/net_net_main_f2.pt",
    "realtrack/build/models/net_net_main_f3.pt", "realtrack/build/models/net_net_main_f4.pt",
    "ai2/build/models/tcn.pt", "realdata/build/cache/reader_choice.json", "realdata/build/cache/page_model.json",
    "realdata/build/cache/tremorlib.json", "realdata/build/cache/tremor_waveforms.npz",
    "realdata/build/cache/unipen_index.json",
)
_SHA: Dict[str, Optional[str]] = {}


def reader_weights() -> Optional[Path]:
    d = REPO_ROOT / "realdata" / "build" / "hf" / "hub" / "models--microsoft--trocr-base-handwritten" / "snapshots"
    for p in sorted(d.glob("*/*")):
        if p.suffix in (".safetensors", ".bin") and "model" in p.name:
            return p
    return None


def inputs_sha256() -> Dict[str, Optional[str]]:
    if not _SHA:
        for rel in INPUT_FILES:
            _SHA[rel] = CM.sha256_file(REPO_ROOT / rel)
        w = reader_weights()
        if w is not None:
            _SHA[str(w.relative_to(REPO_ROOT))] = CM.sha256_file(w)
    return dict(_SHA)


def provenance(quick: bool, status: str = EVIDENCE_SIM, extra: Optional[Dict] = None) -> Dict:
    from stabpen import provenance as PV
    from . import e11, e13, gap
    seeds = {"splits": "study R's tuning/test split of writers, texts and patients (realdata.writinglib, tremorlib); "
                       "study E's tuning selection set and folds (realtrack.cases); every choice on the tuning split, "
                       "the test split run once after frozen.json",
             "cards_bootstrap": f"R's: {CM.N_BOOT} writer resamples, seed {CM.BOOT_SEED}",
             "curve_bootstrap": "2000 writer resamples, seed 20260930 (curve.py)",
             "sensor_seeds": "R's case keys (test) and E's case ids (tuning), realdata.hw1._seed / realtrack.cases._h",
             "noise_seeds": "sha1 of (case id, 'noise', level) (e13.py)",
             "calibration_notes": "the first note with seed i + K k (K = writers in the split) sharing no line with the "
                                  "scored note (e11.py)"}
    params = {"e13": e13.plan(quick), "e11": {"p": list(e11.P_Q), "kappa": list(e11.KAPPA), "modes": list(e11.MODES),
                                               "clean_note_max_um": e11.CLEAN_NOTE_MAX_UM,
                                               "clean_mean_um": e11.CLEAN_MEAN_UM},
              "gap": {"delta_s": gap.DELTA_S, "dtau_ms": list(gap.DTAU_GRID_MS), "order": list(gap.ORDER_GRID),
                      "ridge": gap.RIDGE, "fit_levels": list(gap.FIT_LEVELS)}}
    try:
        import torch
        tv = torch.__version__
    except Exception:
        tv = None
    md = PV.metadata(status, seeds=seeds,
                     extra={"package": f"readable-{__version__}", "inputs_sha256": inputs_sha256(),
                            "parameters": params, "quick": quick, "torch": tv,
                            "command_line": "python3 -m readable.run" + (" --quick" if quick else ""),
                            **(extra or {})})
    return md


def answers(e13a: Dict, e11a: Dict, gapa: Dict) -> Dict:
    """The key numbers of the three answers (each with its label)."""
    out = {}
    tf = (e13a.get("tuning") or {}).get("fits", {}).get("pooled")
    tsf = ((e13a.get("test") or {}).get("fits") or {}).get("pooled")
    if tf:
        out["e13"] = {"label": "SIMULATION (HW1, real inputs) + CALCULATION (curve fit)",
                      "tuning": {k: tf.get(k) for k in ("r_plus2_mm", "r_80_mm", "r_within1_mm", "w_ord_severe",
                                                        "w_clean")},
                      "tuning_ci95": {k: (tf.get("ci95") or {}).get(k) for k in ("r_plus2_mm", "r_80_mm", "r_within1_mm")},
                      "tuning_fit": tf["fit"].get("params")}
        if tsf:
            out["e13"]["test"] = {k: tsf.get(k) for k in ("r_plus2_mm", "r_80_mm", "r_within1_mm", "w_ord_severe",
                                                          "w_clean")}
            out["e13"]["test_ci95"] = {k: (tsf.get("ci95") or {}).get(k) for k in ("r_plus2_mm", "r_80_mm",
                                                                                  "r_within1_mm")}
            out["e13"]["test_fit"] = tsf["fit"].get("params")
            out["e13"]["gain_at_r_plus2_test"] = (e13a.get("test") or {}).get("gain_at_r_plus2")
    if e11a.get("test"):
        s = e11a["test"]["summary"]
        out["e11"] = {"label": e11a["label"], "by_design": {k: {
            "clean_um_mean": (v.get("clean_um") or {}).get("mean"), "clean_um_worst_writer": v.get("clean_um_worst_writer"),
            "worst_writer": v.get("worst_writer"), "writers_over_50um": v.get("writers_over_50um"),
            "severe_words_gain": v.get("severe_words_gain"), "severe_ratio_to_ordinary": v.get("severe_ratio_to_ordinary"),
            "dec055": v.get("dec055")} for k, v in s.items()}}
    ch = {}
    for split in ("tuning", "test"):
        g = gapa.get(split)
        if g:
            ch[split] = {k: [{kk: st.get(kk) for kk in ("step", "config", "tip_tremor_mm", "words_via_curve",
                                                         "words_read", "signal_residual_mm")} for st in v["steps"]]
                         for k, v in g["chains"].items()}
    if ch:
        out["gap"] = {"label": "SIMULATION (HW1, real inputs); words via the frozen E13 tuning curve (CALCULATION)",
                      "chains": ch}
    return out


def write(quick: bool, log=CM.log) -> Dict:
    from . import e11, e13, gap
    from . import stages as SG
    t0 = time.time()
    fr = CM.jload(SG.frozen_path(quick))
    e13a = e13.aggregate(quick, fr)
    e11a = e11.aggregate(quick, fr)
    p_curve = (fr or {}).get("e13", {}).get("fit", {}).get("p")
    ar = CM.jload(SG.predictor_path(quick))
    gapa = gap.aggregate(quick, p_curve, ar)
    timings = CM.jload(CM.cache_dir(quick) / "timings.json") or {}
    out = {"stabpen.provenance": provenance(quick),
           "evidence": {"sim": EVIDENCE_SIM, "calc": EVIDENCE_CALC,
                        "labels": "SIMULATION, CALCULATION, ASSUMPTION, PROPOSED DESIGN, LITERATURE (ledger id); "
                                  "nothing here is a MEASUREMENT"},
           "questions": {
               "e13": "EXP-E13: how much tremor may be left at the tip for words to be readable?",
               "e11": "EXP-E11: does calibrating the estimator's authority gate on the user's own clean writing keep every "
                      "writer under 50 um? (REQ-CTRL-016)",
               "gap": "Where is the gap between the best causal estimator and perfect knowledge: prediction or "
                      "separation?"},
           "answers": answers(e13a, e11a, gapa),
           "e13": e13a, "e11": e11a, "gap": gapa, "frozen": fr, "compute": timings,
           "generated_in_s": None}
    out["generated_in_s"] = time.time() - t0
    d = SG.results_dir(quick)
    CM.jdump(d / "readable.json", out)
    log(f"[report] {d / 'readable.json'} ({(d / 'readable.json').stat().st_size / 1e6:.2f} MB) in {out['generated_in_s']:.0f} s")
    return out
