"""Task 5: the DeltaPen-class page-sensor rows of studies R, E and F re-analysed with the causal page model version 2
(SIMULATION, model HW1 with REAL recorded inputs; realdata/sensors.py degrade_page version 2; nothing measured).

Version 1 (used by R, E and F) let a window's future endpoint set its error and restored displacement lost in a dropout
from the true motion.  Version 2 draws each window's error from the preceding window only (independent seeded
streams), never recovers unobserved motion, and marks the absolute reference invalid after a loss.  Its amplitude fit
to LIT OPT-02 is the same moment match (c, sigma), refitted here IN MEMORY on the same tuning notes (never saved over
realdata/build/cache/page_model.json).

The test split is spent: these are re-analyses of already-inspected cases, not new tests.
  R  study R's test cases (9 notes x PD/ET x severe/moderate/mild, the 9 clean notes, the 8 real_real bridge cases at
     1 mm): its three trackers on the DeltaPen-class sensor ('revH_akf|deltapen', 'revJ_gated|deltapen',
     'revJ_tcn|deltapen') rerun with version 2, R's case keys and seeds, R's reading budget; the ordinary pen, perfect
     knowledge and the ideal-sensor bound are R's cached rows (they use no DeltaPen-class page sensor).
  E  study E's frozen test designs on the same cases and streams: 'revJ_new|deltapen' (the frozen design), 'revJ_g4|
     deltapen' (G4 in HW1) and the information rows, E's reading budget; DEC-055's line recomputed.
  F  study F's gap decomposition on its 20 tuning and 18 test severe cases: every configuration of readable.gap.run_case
     recomputed with version 2 installed (the DeltaPen-class ones change; the others must not: a built-in check); no
     reading (tip tremor, words via the frozen curve).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, REPO_ROOT
from . import common as CM

R_CACHE = REPO_ROOT / "realdata" / "build" / "cache" / "hw1" / "full_v2"      # read-only
E_CACHE = REPO_ROOT / "realtrack" / "build" / "cache" / "test"                # read-only
F_CACHE = REPO_ROOT / "readable" / "build" / "cache"                           # read-only
OUT = BUILD_DIR / "page_v2"
R_TRACKERS = ("revH_akf", "revJ_gated", "revJ_tcn")
SOURCES = ("realdata/sensors.py", "realdata/hw1.py", "realdata/library.py", "realdata/ocr.py", "realtrack/test.py",
           "realtrack/estimators.py", "realtrack/cases.py", "readable/gap.py", "readable/common.py", "ai2/delayed.py",
           "ai2/candidates.py", "fusion/sensors.py", "fusion/estimators.py", "handwriting/plant.py",
           "results/realtrack/frozen.json", "results/readable/frozen.json", "rebaseline/page_v2.py",
           "rebaseline/common.py")
_STATE: Dict = {}
# the version-1 fit used by studies R, E and F (realdata/build/cache/page_model.json as it stood before the pass; the
# file has since been overwritten by a version-2 refit elsewhere): recorded here from this study's first read of it
V1_PUBLISHED_FIT = {"c": 2.048007929735164e-05, "sigma": 1.3544049799035518, "n_windows": 31757,
                    "median_um": 23.6, "mean_um": 68.3}


# ------------------------------------------------------------------ the page model
ANCHOR_NOTE = ("rebaseline runtime workaround (patch proposal 6): realdata.sensors.degrade_page version 2 raises when "
               "the first page sample is invalid, and every real note starts with the pen lifted; here the sensor "
               "anchors at its first valid report (the version-2 model runs unchanged from there; the earlier samples "
               "are reported invalid, their availability monotone, their absolute reference invalid)")


def anchored(orig):
    """Wrap version 2 of degrade_page so that a stream whose first page sample is invalid is anchored at its first valid
    sample instead of raising.  From the anchor on, the output is exactly orig() applied to the suffix (same seed, same
    substreams); version 1 and streams that start valid pass straight through."""
    import dataclasses as _dc

    def degrade_page(st, model, seed):
        if getattr(model, "version", None) != 2:
            return orig(st, model, seed)
        P = np.asarray(st.pos, float)
        ok = np.asarray(st.pos_ok, bool)
        if P.ndim != 2 or len(ok) != len(P) or len(ok) == 0:
            return orig(st, model, seed)
        ok = ok & np.all(np.isfinite(P), axis=1)
        if ok[0] or not ok.any():
            return orig(st, model, seed)
        k = int(np.flatnonzero(ok)[0])
        if len(ok) - k < 2:
            return orig(st, model, seed)
        t = np.asarray(st.pos_t, float)
        sub = _dc.replace(st, pos_t=t[k:], pos_av=np.asarray(st.pos_av, float)[k:], pos=P[k:],
                          pos_ok=np.asarray(st.pos_ok, float)[k:], meta=dict(st.meta))
        out = orig(sub, model, seed)
        lead_av = t[:k] + float(model.latency_s)
        av = np.concatenate([np.minimum(lead_av, float(out.pos_av[0])), np.asarray(out.pos_av, float)])
        pos = np.concatenate([np.repeat(np.asarray(out.pos, float)[:1], k, axis=0), np.asarray(out.pos, float)])
        pok = np.concatenate([np.zeros(k), np.asarray(out.pos_ok, float)])
        meta = dict(out.meta)
        rv = meta.get("page_reference_valid")
        if rv is not None:
            meta["page_reference_valid"] = [False] * k + list(rv)
        meta.update(page_anchor_index=k, page_anchor_t=float(t[k]), page_anchor_note=ANCHOR_NOTE)
        return _dc.replace(out, pos_t=t, pos_av=av, pos=np.ascontiguousarray(pos), pos_ok=pok, meta=meta)

    degrade_page._rebaseline_anchored = True
    degrade_page.__wrapped__ = orig
    return degrade_page


def install_v2(log=CM.log) -> Dict:
    """Fit version 2 on the tuning writers' clean notes (as realdata.hw1.page_model does) and install it in realdata.hw1
    for this process only; compare its fit with the cached version-1 fit (read-only)."""
    if "model" in _STATE:
        return _STATE["info"]
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import sensors as RS
    from realdata import writinglib as WL
    ws = WL.unipen_writers("tuning")
    notes = [RL.writing("tuning", seed=i, dt=1e-3) for i in range(2 * len(ws))]
    m = RS.fit_window_error(notes, RS.PageModel())
    assert m.version == 2
    H._PAGE["m"] = m
    if not getattr(RS.degrade_page, "_rebaseline_anchored", False):
        RS.degrade_page = anchored(RS.degrade_page)
    v1 = RS.load_model(allow_legacy=True)
    info = {"v2": {k: v for k, v in asdict(m).items() if k != "labels"},
            "v1_cached": {k: v for k, v in asdict(v1).items() if k != "labels"} if v1 else None,
            "fit_identical_c_sigma": bool(v1 is not None and abs(v1.c - m.c) < 1e-15 and abs(v1.sigma - m.sigma) < 1e-12),
            "v1_fit_as_published": V1_PUBLISHED_FIT,
            "c_change_vs_v1_published": m.c / V1_PUBLISHED_FIT["c"] - 1.0,
            "anchoring": ANCHOR_NOTE,
            "note": ("version 2 as the current code defines it: the causal construction AND the pass's corrected window "
                     "definition in the moment fit (a 10 ms window now spans 10 sample intervals, not 9), which moves "
                     "the fitted amplitude c; the cached file realdata/build/cache/page_model.json may already hold a "
                     "version-2 refit written by another run (it is only read here)")}
    _STATE.update({"model": m, "info": info})
    log(f"[page_v2] model v2 fitted: c {m.c * 1e6:.2f} um, sigma {m.sigma:.3f} (v1 cache: "
        f"{(v1.c * 1e6) if v1 else float('nan'):.2f} um, {v1.sigma if v1 else float('nan'):.3f})")
    return info


# ------------------------------------------------------------------ R + E on one case
def r_name(i: int, kind: Optional[str], cls: Optional[str], bridge: bool = False) -> str:
    if bridge:
        return f"bridge_real_real_w{i}_{kind}"
    return f"clean_real_w{i}" if kind is None else f"real_w{i}_{kind}_{cls}"


def _reading(fr: Dict, cls: Optional[str], bridge: bool) -> Dict[str, set]:
    from realdata import hw1 as H
    from realtrack import test as T
    trk = {f"{t}|deltapen" for t in R_TRACKERS}
    if bridge:
        r = set(H.OCR_BRIDGE) & trk
        e = set()
    elif cls is None:
        r = set(H.OCR_REAL) & trk
        e = set(T.ocr_plan(fr)["clean"])
    else:
        r = set(H.OCR_BY_CLASS.get(cls, H.OCR_REAL)) & trk
        e = set(T.ocr_plan(fr)[cls])
    return {"r": r, "e": e}


def run_case_v2(wr, i: int, kind: Optional[str], cls: Optional[str], fr: Dict, bridge: bool = False,
                quick: bool = False) -> Dict:
    """R's trackers and E's designs on version-2 DeltaPen-class streams of one R test case (R's keys and seeds)."""
    from ai2 import candidates as CA
    from ai2 import delayed as DL
    from aiprior import core as CO
    from handwriting import plant as PL
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import sensors as RS
    from realtrack import test as T
    t0 = time.time()
    pm = _STATE["model"]
    DL.OUT_EVERY = 1
    M = H.ai2_models()
    if kind is None:
        tremor, f0, amp, key, tmeta = None, 0.0, 0.0, f"clean:{i}", {}
    elif bridge:
        dr = RL.tremor_for(wr.written, "moderate", seed=1000 + i, kind=kind, split="test", amp_mm=1.0)
        tremor, f0, amp, key = dr.d, float(dr.meta["f0"]), 1.0e-3, f"bridge:real_real:{i}:{kind}"
        tmeta = {"rid": dr.meta["rid"], "amp_mm": 1.0, "f0": f0}
    else:
        dr = RL.tremor_for(wr.written, cls, seed=i, kind=kind, split="test",
                           amp_mm=RL.classes(False)[cls]["representative_mm"])
        tremor, f0, amp, key = dr.d, float(dr.meta["f0"]), dr.meta["amp_mm"] * 1e-3, f"real:{i}:{kind}:{cls}"
        tmeta = {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")}
    clean = tremor is None
    rd = _reading(fr, cls, bridge)
    if quick:
        rd = {"r": set(), "e": set()}
    out: Dict = {}
    # Rev H + its tracker (as built), version-2 streams
    sH = H.make_scen(wr, "revH", tremor, f0, amp, 0, H._seed(key, "revH"), page=pm)
    r = PL.run(sH.scn, sH.pen, wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(-sH.dh)))
    k = "revH_akf|deltapen"
    out[k] = H.measures(wr, r, sH.scn, sH.pen, k in rd["r"], f0)
    if clean:
        out[k]["false_correction_um"] = DL.ink_timeline_error(sH, r, np.zeros(len(sH.dh)), sH.neutral)
    del r, sH
    # Rev J: ai2's gated tracker and TCN (R), then E's frozen designs on the same streams
    sJ = H.make_scen(wr, "revJ", tremor, f0, amp, 0, H._seed(key, "revJ"), page=pm)
    S = M["S"]
    tick_t = sJ.streams.tick_t
    cfg = DL.DelayCfg(tremor=S["tremor"], det=S["det"] or {})
    cfg.amp_lo, cfg.amp_hi = S["gated"]["amp_lo"], S["gated"]["amp_hi"]
    est = DL.estimates(sJ, cfg, lags=CA.LAGS_CL)
    zeros = np.zeros(len(tick_t))
    qs = {"revJ_gated": DL.command(est, zeros, tick_t)}
    if M["tcn"] is not None:
        X, tk, mb = CA.arrays(sJ, M["mp"])
        cm = CA.commands(sJ, est, M["mp"], {"learned": {"tcn": M["tcn"]}}, X, tk, mb)
        qs["revJ_tcn"] = cm["learned_tcn"]
    for name, q in qs.items():
        k = f"{name}|deltapen"
        r = PL.run(sJ.scn, sJ.pen, wr.hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
        out[k] = H.measures(wr, r, sJ.scn, sJ.pen, k in rd["r"], f0)
        if clean:
            out[k]["false_correction_um"] = DL.ink_timeline_error(sJ, r, zeros, sJ.neutral)
        del r
    out["_gate_open_frac|deltapen"] = float(np.mean(est["g"] > 0.5))
    if not bridge:
        for name, dz in T.new_designs(fr).items():
            k = f"{name}|deltapen"
            T._run_design(name, dz, sJ, wr, f0, clean, k in rd["e"], out, None, "deltapen")
    # the page-model check against the ideal streams of the same case (the same IMU and seeds)
    st_i = CO.streams_for(sJ.neutral, sJ.scn, sJ.pen, wr.trk, H._seed(key, "revJ"))
    out["_page_check|deltapen_v2"] = RS.window_error_check(st_i, sJ.streams)
    out["_page_v2_meta"] = _v2_meta(sJ.streams)
    out["_elapsed_s"] = time.time() - t0
    return {"set": "bridge" if bridge else ("clean_real" if clean else "real"), "variant": "real_real" if bridge else None,
            "writer": wr.written.real["writer"], "note": i, "kind": kind, "class": cls, "tremor": tmeta,
            "devices": out}


def plan(quick: bool = False) -> List[tuple]:
    """(note, kind, class, bridge) in R's order: per note, clean, the three classes x PD/ET, then the bridge."""
    notes = range(1) if quick else range(9)
    out = []
    for i in notes:
        out.append((i, None, None, False))
        for cls in (("severe",) if quick else ("severe", "moderate", "mild")):
            for kind in ("PD", "ET"):
                out.append((i, kind, cls, False))
        if i < 4 and not quick:
            for kind in ("PD", "ET"):
                out.append((i, kind, None, True))
    return out


def run_re(notes: Optional[Sequence[int]] = None, quick: bool = False, log=CM.log) -> Dict:
    from realdata import hw1 as H
    from realdata import ocr as OC
    from realtrack import test as T
    install_v2(log)
    if not quick:
        OC.reader_choice(log=log)
    H.ai2_models()
    fr = T.load_frozen()
    d = OUT / ("quick" if quick else "cases")
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    wr, wr_i = None, None
    for (i, kind, cls, bridge) in plan(quick):
        if notes is not None and i not in notes:
            continue
        p = d / f"{r_name(i, kind, cls, bridge)}.json"
        if p.exists():
            continue
        if wr_i != i:
            wr, wr_i = H.real_writer("test", i), i
        res = run_case_v2(wr, i, kind, cls, fr, bridge, quick)
        CM.jdump(p, res, indent=None)
        dv = res["devices"]
        log(f"[page_v2] {p.stem}: " + ", ".join(
            f"{k} {v.get('tip_tremor_mm', float('nan')):.2f} mm" + (f" {v['words_read']}/{v['words_total']}" if v.get("words_total") else "")
            for k, v in dv.items() if isinstance(v, dict) and "tip_tremor_mm" in v)
            + f" [{dv['_elapsed_s']:.0f} s]")
    return {"wall_s": time.time() - t0}


_META_KEYS = ("page_model", "page_model_version", "page_dropouts", "page_lost_intervals", "page_lost_displacement_m",
              "page_anchor_index", "page_anchor_t")


def _v2_meta(st) -> Dict:
    meta = (getattr(st, "meta", None) or {}) if st is not None else {}
    out = {k: meta.get(k) for k in _META_KEYS}
    rv = meta.get("page_reference_valid")
    out["reference_valid_share"] = float(np.mean(rv)) if rv else None
    ok = np.asarray(getattr(st, "pos_ok", []), float) if st is not None else np.zeros(0)
    out["pos_valid_share"] = float(np.mean(ok > 0.5)) if len(ok) else None
    return out


# ------------------------------------------------------------------ F's gap decomposition with version 2
def run_gap(splits=("tuning", "test"), quick: bool = False, log=CM.log) -> Dict:
    from realdata import hw1 as H
    from readable import common as RC
    from readable import gap as G
    install_v2(log)
    ar = CM.jload(F_CACHE / "gap" / "predictor.json")
    if ar is None:
        raise RuntimeError("study F's AR predictor cache (readable/build/cache/gap/predictor.json) is missing")
    d = OUT / ("quick_gap" if quick else "gap")
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    from readable import e13
    if "tuning" in splits:
        for i in (list(e13.plan(quick)["tuning"]["notes"])[:1] if quick else e13.plan(False)["tuning"]["notes"]):
            note = None
            for kind in (("PD",) if quick else ("PD", "ET")):
                p = d / f"tune_n{i}_{kind}_severe.json"
                if p.exists():
                    continue
                t1 = time.time()
                note = note or RC.tuning_note(i)
                spec = RC.tuning_spec(i, kind, "severe")
                tc = RC.TuneCase(note, spec, streams=True)
                res = G.run_case(tc, spec, str(spec["fold"]), ar)
                res.update({"split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                            "_page_v2_meta": _v2_meta(tc.streams_d), "_elapsed_s": time.time() - t1})
                CM.jdump(p, res, indent=None)
                log(f"[page_v2 gap] tune n{i} {kind} ({time.time() - t1:.0f} s)")
    if "test" in splits:
        for i in (range(1) if quick else range(9)):
            wr = None
            for kind in (("PD",) if quick else ("PD", "ET")):
                p = d / f"test_w{i}_{kind}_severe.json"
                if p.exists():
                    continue
                t1 = time.time()
                wr = wr or H.real_writer("test", i)
                tc = RC.TestCase(wr, i, kind, "severe")
                res = G.run_case(tc, {"split": "test"}, None, ar, read_keys=())
                res.update({"split": "test", "writer": wr.written.real["writer"], "note": i, "kind": kind,
                            "_page_v2_meta": _v2_meta(tc.streams_d), "_elapsed_s": time.time() - t1})
                CM.jdump(p, res, indent=None)
                log(f"[page_v2 gap] test w{i} {kind} ({time.time() - t1:.0f} s)")
    return {"wall_s": time.time() - t0}


def run_sensing(quick: bool = False, log=CM.log) -> Dict:
    """Study F's page sensing check (readable.gap.sensing_check('page'): a linear predictor on the page position of the
    tremor alone, ideal and DeltaPen-class sensors, tuning split, cross-fitted) with version 2 installed."""
    from readable import gap as G
    from readable import stages as SG
    install_v2(log)
    p = OUT / ("quick_sensing_page.json" if quick else "sensing_page.json")
    if p.exists():
        return CM.jload(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    ar = CM.jload(F_CACHE / "gap" / "predictor.json")
    if ar is None:
        raise RuntimeError("study F's AR predictor cache (readable/build/cache/gap/predictor.json) is missing")
    SG.load_predictor = lambda q: ar          # always study F's fitted predictor (read-only), also in a quick run
    out = G.sensing_check("page", quick=quick, log=log)
    CM.jdump(p, out, indent=None)
    return out


# ------------------------------------------------------------------ aggregation
def _load_dir(d: Path) -> Dict[str, Dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(Path(d).glob("*.json"))}


def merged_cases(v2: Dict[str, Dict]) -> Dict[str, List[Dict]]:
    """R-format case lists for the cards: 'v1' = R's cached cases (+ E's cached rows) exactly as published; 'v2' = the
    same with every DeltaPen-class tracker/design row replaced by its version-2 rerun."""
    out = {"v1": [], "v2": [], "identity_mismatch": []}
    for name, mine in sorted(v2.items()):
        r = CM.jload(R_CACHE / f"{name}.json")
        if r is None:
            continue
        same = r.get("writer") == mine.get("writer") and r.get("kind") == mine.get("kind")
        if mine.get("tremor"):
            rt = r.get("tremor") or {}
            same = same and rt.get("rid") == mine["tremor"].get("rid") and abs(
                float(rt.get("amp_mm", 0)) - float(mine["tremor"].get("amp_mm", 0))) < 1e-9
        if not same:                                # never pair a rerun with a different case
            out["identity_mismatch"].append(name)
            continue
        e = CM.jload(E_CACHE / f"{name}.json") or {"devices": {}}
        v1 = dict(r)
        v1["devices"] = dict(r["devices"])
        v1["devices"].update({k: v for k, v in e["devices"].items() if not k.startswith("_")})
        new = dict(v1)
        new["devices"] = dict(v1["devices"])
        for k, v in mine["devices"].items():
            if not k.startswith("_"):
                if k not in new["devices"]:
                    continue                           # only rows that existed in the published cases
                new["devices"][k] = v
        out["v1"].append(v1)
        out["v2"].append(new)
    return out


def summarise_re(v2_dir: Path = OUT / "cases") -> Dict:
    from realdata import hw1 as H
    from realtrack import test as T
    v2 = _load_dir(v2_dir)
    if not v2:
        return {}
    mc = merged_cases(v2)
    fr = T.load_frozen()
    out = {"n_cases_rerun": len(v2), "cases_rerun": sorted(v2), "identity_mismatch": mc["identity_mismatch"]}
    devs_r = ["none", "revH_akf|deltapen", "revJ_gated|deltapen", "revJ_tcn|deltapen", "revJ_oracle", "revH_akf",
              "revJ_gated", "revJ_tcn"]
    for ver in ("v1", "v2"):
        cases = mc[ver]
        agR = H.aggregate([c for c in cases if c["set"] in ("real", "clean_real", "bridge")])
        agE = T.aggregate([c for c in cases if c["set"] in ("real", "clean_real")], fr)
        keep = {}
        for cls in ("all/severe", "all/moderate", "all/mild", "PD/severe", "ET/severe"):
            cd = agR["real"].get(cls) or {}
            keep[cls] = {d: _card_short(cd.get(d)) for d in devs_r + ["revJ_new|deltapen", "revJ_g4|deltapen",
                                                                       "revJ_info_net|deltapen", "revJ_info_ungated_akf|deltapen",
                                                                       "revJ_new", "revJ_held"]
                         if (agE["real"].get(cls) or {}).get(d) or cd.get(d)}
            for d in ("revJ_new|deltapen", "revJ_g4|deltapen", "revJ_info_net|deltapen", "revJ_info_ungated_akf|deltapen",
                      "revJ_new", "revJ_held", "revJ_info_glg|deltapen", "revJ_info_listen_conf|deltapen"):
                v = (agE["real"].get(cls) or {}).get(d)
                if v:
                    keep[cls][d] = _card_short(v)
        clean = {}
        for d, v in ((agE["clean"].get("clean_real") or {}).items()):
            clean[d] = {"words_of_10": (v.get("words_of_10") or {}).get("mean"),
                        "false_correction_um": v.get("false_correction_um"),
                        "false_correction_um_worst_writer": v.get("false_correction_um_worst_writer")}
        bridge = {d: _card_short(v) for d, v in (agR["bridge"].get("real_real/all") or {}).items()}
        out[ver] = {"cards": keep, "clean": clean, "bridge_real_real_1mm": bridge,
                    "dec055": {d: T.dec055(agE, d) for d in ("revJ_new|deltapen", "revJ_g4|deltapen")}}
    # ideal against DeltaPen-class, per version (study R's 'changes by at most 0.1 word and 0.01 mm')
    comp = {}
    for ver in ("v1", "v2"):
        mx_w, mx_t = 0.0, 0.0
        for cls in ("all/severe", "all/moderate", "all/mild"):
            c = out[ver]["cards"][cls]
            for t in R_TRACKERS:
                a, b = c.get(t), c.get(f"{t}|deltapen")
                if not a or not b:
                    continue
                if a.get("words_of_10") is not None and b.get("words_of_10") is not None:
                    mx_w = max(mx_w, abs(a["words_of_10"] - b["words_of_10"]))
                if a.get("tip_tremor_mm") is not None and b.get("tip_tremor_mm") is not None:
                    mx_t = max(mx_t, abs(a["tip_tremor_mm"] - b["tip_tremor_mm"]))
        comp[ver] = {"max_abs_words_of_10": mx_w, "max_abs_tip_tremor_mm": mx_t}
    out["ideal_vs_deltapen"] = comp
    pc = [c["devices"].get("_page_check|deltapen_v2") for c in v2.values() if c["devices"].get("_page_check|deltapen_v2")]
    out["page_check_v2"] = {"window_error_median_um_mean": CM.mean_or_none(p.get("median_um") for p in pc),
                            "window_error_mean_um_mean": CM.mean_or_none(p.get("mean_um") for p in pc),
                            "reference_valid_share_mean": CM.mean_or_none(
                                (c["devices"].get("_page_v2_meta") or {}).get("reference_valid_share") for c in v2.values()),
                            "dropouts_mean": CM.mean_or_none((c["devices"].get("_page_v2_meta") or {}).get("page_dropouts")
                                                             for c in v2.values()),
                            "v1_window_error_median_um_mean": CM.mean_or_none(
                                ((CM.jload(R_CACHE / f"{n}.json") or {}).get("devices", {}).get("_page_check|deltapen") or {}).get("median_um")
                                for n in v2),
                            "target_LIT_OPT02": {"median_um": 23.6, "mean_um": 68.3}}
    out["paired_tip_tremor"] = _paired(mc)
    return out


def _card_short(v: Optional[Dict]) -> Optional[Dict]:
    if not v:
        return None
    g = lambda k: (v.get(k) or {}).get("mean") if isinstance(v.get(k), dict) else v.get(k)   # noqa: E731
    out = {"words_of_10": g("words_of_10"), "words_gain": g("words_of_10_gain"), "tip_tremor_mm": g("tip_tremor_mm"),
           "tip_tremor_ratio": g("tip_tremor_ratio"), "n_cases": v.get("n_cases")}
    wg = v.get("words_of_10_gain")
    if isinstance(wg, dict):
        out["words_gain_ci"] = [wg.get("lo"), wg.get("hi")]
    tr = v.get("tip_tremor_ratio")
    if isinstance(tr, dict):
        out["tip_tremor_ratio_ci"] = [tr.get("lo"), tr.get("hi")]
    if isinstance(v.get("false_correction_um"), dict):
        out["false_correction_um"] = v["false_correction_um"].get("mean")
    return out


def _paired(mc: Dict[str, List[Dict]]) -> Dict:
    """Per device: mean over rerun cases of (v2 - v1) tip tremor (mm) and words (of 10), severe class."""
    out = {}
    for a, b in zip(mc["v1"], mc["v2"]):
        if a.get("set") != "real":
            continue
        for k, v in b["devices"].items():
            if not k.endswith("|deltapen") or not isinstance(v, dict):
                continue
            u = a["devices"].get(k) or {}
            e = out.setdefault(f"{a.get('class')}|{k}", {"d_tip": [], "d_words": []})
            if v.get("tip_tremor_mm") is not None and u.get("tip_tremor_mm") is not None:
                e["d_tip"].append(v["tip_tremor_mm"] - u["tip_tremor_mm"])
            if v.get("words_total") and u.get("words_total"):
                e["d_words"].append(10 * (v["words_read"] / v["words_total"] - u["words_read"] / u["words_total"]))
    return {k: {"n": len(v["d_tip"]), "tip_tremor_mm_diff_mean": CM.mean_or_none(v["d_tip"]),
                "tip_tremor_mm_diff_maxabs": max((abs(x) for x in v["d_tip"]), default=None),
                "words_of_10_diff_mean": CM.mean_or_none(v["d_words"]), "n_read": len(v["d_words"])}
            for k, v in sorted(out.items())}


def summarise_gap(d: Path = OUT / "gap") -> Dict:
    from readable import curve as CV
    fr = CM.jload(REPO_ROOT / "results" / "readable" / "frozen.json") or {}
    p_curve = fr.get("e13", {}).get("fit", {}).get("p")
    new = _load_dir(d)
    if not new:
        return {}
    out = {"n_cases": len(new), "splits": {}}
    for split, pre in (("tuning", "tune_"), ("test", "test_")):
        cases = {k: v for k, v in new.items() if k.startswith(pre)}
        if not cases:
            continue
        keys = sorted({k for c in cases.values() for k in c["configs"]})
        tab, unchanged_max = {}, 0.0
        for k in keys:
            acc_v1, acc_v2 = {}, {}
            for name, c in cases.items():
                old = CM.jload(F_CACHE / "gap" / f"{name}.json") or {}
                a = ((old.get("configs") or {}).get(k) or {}).get("tip_tremor_mm")
                b = (c["configs"].get(k) or {}).get("tip_tremor_mm")
                if a is not None:
                    acc_v1.setdefault(c["writer"], []).append(a)
                if b is not None:
                    acc_v2.setdefault(c["writer"], []).append(b)
                if a is not None and b is not None and not _page_dependent(k):
                    unchanged_max = max(unchanged_max, abs(a - b))
            m1 = CM.mean_or_none(np.mean(v) for v in acc_v1.values())
            m2 = CM.mean_or_none(np.mean(v) for v in acc_v2.values())
            tab[k] = {"tip_tremor_mm_v1": m1, "tip_tremor_mm_v2": m2,
                      "words_via_curve_v1": float(CV.model(m1, p_curve)) if (m1 is not None and p_curve) else None,
                      "words_via_curve_v2": float(CV.model(m2, p_curve)) if (m2 is not None and p_curve) else None,
                      "page_dependent": _page_dependent(k), "n_writers": len(acc_v2)}
        out["splits"][split] = {"n_cases": len(cases), "configs": tab,
                                "page_independent_max_abs_change_mm": unchanged_max}
    pub = ((CM.jload(REPO_ROOT / "results" / "readable" / "readable.json") or {}).get("gap") or {})
    out["published_v1"] = {sp: {k: (v.get("tip_tremor_mm") or {}) for k, v in ((pub.get(sp) or {}).get("configs") or {}).items()}
                           for sp in ("tuning", "test")}
    sc_v2 = CM.jload(OUT / "sensing_page.json")
    sc_v1 = (pub.get("sensing_check") or {}).get("page") or {}
    out["sensing_check_page"] = {
        ver: {v: {"signal_residual_mm": x.get("signal_residual_mm"), "tip_tremor_mm": x.get("tip_tremor_mm"), "n": x.get("n")}
              for v, x in ((sc or {}).get("variants") or {}).items()}
        for ver, sc in (("v1_published", sc_v1), ("v2", sc_v2)) if sc}
    return out


def _page_dependent(k: str) -> bool:
    """Configurations that read the DeltaPen-class page position (study F's naming).  The real-data network ('net_*',
    realtrack/netmodel.features) reads the IMU and the contact channel only, so the page model cannot move it."""
    if k in ("oracle", "held") or k.startswith("pred_") or k.startswith("fir_") or k.endswith("idealpage"):
        return False
    if k.startswith("net_"):
        return False
    if k == "page_ar_trem_ideal":
        return False
    return True


def summarise(write: bool = True) -> Dict:
    install_info = _STATE.get("info")
    body = {"what": "DeltaPen-class page-sensor rows of studies R, E and F re-analysed with the causal version 2",
            "evidence": ("SIMULATION (model HW1 with real recorded inputs; page model realdata/sensors.py version 2, an "
                         "ASSUMPTION informed by LIT OPT-02); re-analysis of the spent test split, not a new test"),
            "page_model": install_info, "R_and_E": summarise_re(), "F_gap": summarise_gap()}
    if write:
        CM.write_result("page_v2", body, body["evidence"], inputs=SOURCES,
                        seeds="R's case keys (realdata.hw1._seed) and E's; version 2 draws from SeedSequence(seed + 17)",
                        parameters={"plan": [list(p) for p in plan(False)], "trackers": list(R_TRACKERS)})
    return body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--re", action="store_true", help="R and E cases")
    ap.add_argument("--notes", default="", help="comma list of test notes (R/E)")
    ap.add_argument("--gap", action="store_true", help="F's gap cases")
    ap.add_argument("--sensing", action="store_true", help="F's page sensing check")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args(argv)
    if a.re:
        run_re([int(x) for x in a.notes.split(",") if x.strip()] or None, a.quick)
    if a.gap:
        run_gap(quick=a.quick)
    if a.sensing:
        run_sensing(quick=a.quick)
    if a.summarise:
        install_v2()
        s = summarise(write=not a.quick)
        print(json.dumps({k: (v if k != "R_and_E" else {kk: vv for kk, vv in (v or {}).items() if kk in ("ideal_vs_deltapen", "page_check_v2")})
                          for k, v in s.items() if k in ("R_and_E",)}, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
