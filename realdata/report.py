"""Figures, results/realdata/realdata.json, samples.json and the proposed ledger rows.

Everything in results/realdata/ is either an aggregate statistic, a fitted parameter, a figure, or a short attributed
excerpt of a CC BY 4.0 recording (the before/after pictures).  Nothing from BRUSH, UNIPEN, PADS or NewHandPD other than
statistics is written there (sources.py, 'redistribute').
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import CACHE_DIR, EVIDENCE_CALC, EVIDENCE_DATA, EVIDENCE_SIM, REPO_ROOT, __version__, ensure_paths
from . import figures as FG
from . import hw1 as H
from . import library as RL
from . import sources as SO
from . import tremorlib as TL
from . import writinglib as WL

ensure_paths()

PIC_DIR = CACHE_DIR / "pictures"
PIC_DEVICES = ["none", "revH_akf", "revJ_gated", "revJ_tcn", "revJ_oracle"]


def provenance(quick: bool, extra: Optional[Dict] = None) -> Dict:
    from stabpen import provenance as PV
    files = {}
    for rel in ("results/nose2/nose2.json", "results/revH/tip_params.json", "results/opt/inertial_tracker_revh.json",
                "results/sim2j/writer_fit.json"):
        p = REPO_ROOT / rel
        if p.exists():
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    md = PV.metadata(EVIDENCE_SIM, seeds={"splits": "writers and recordings split tuning/test before evaluation; "
                                                   "all headline numbers from the test split"},
                     extra={"package": f"realdata-{__version__}", "quick": quick, "inputs_sha256_16": files,
                            "datasets": {k: {"licence": s.licence, "redistribute": s.redistribute} for k, s in SO.SOURCES.items()},
                            **(extra or {})})
    return md


# ================================================================== the before/after picture runs (cached)
def picture_cases(quick: bool) -> List[Dict]:
    """Fixed before any run: the composed sentence of the one CC BY writer (test-split letters), a PD and an ET
    tremor recording of the test split (seed 0) at the moderate and severe class representatives."""
    cl = RL.classes(quick)
    out = []
    for kind in ("PD", "ET"):
        for cls in (("severe",) if quick else ("moderate", "severe")):
            out.append({"id": f"ct_{kind}_{cls}", "source": "chartraj", "kind": kind, "class": cls,
                        "amp_mm": cl[cls]["representative_mm"], "seed": 0})
    out.append({"id": "brush_PD_severe", "source": "brush", "kind": "PD", "class": "severe",
                "amp_mm": cl["severe"]["representative_mm"], "seed": 0, "research_only": True})
    out.append({"id": "brush_ET_severe", "source": "brush", "kind": "ET", "class": "severe",
                "amp_mm": cl["severe"]["representative_mm"], "seed": 0, "research_only": True})
    return out


def picture_run(pc: Dict, log=print) -> Dict:
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    p = PIC_DIR / f"{pc['id']}.json"
    if p.exists():
        return json.loads(p.read_text())
    from handwriting import metrics as MT
    kw = {"with_reader": False} if pc["source"] == "brush" else {}
    wr_ = RL.writing("test", seed=pc["seed"], source=pc["source"], **kw)
    wr = H.Writer(wr_, 900_000 + int(hashlib.sha1(pc["id"].encode()).hexdigest()[:5], 16))
    dr = RL.tremor_for(wr_, pc["class"], seed=pc["seed"], kind=pc["kind"], split="test", amp_mm=pc["amp_mm"])
    res = H.run_case(wr, dr.d, dr.meta["f0"], pc["amp_mm"] * 1e-3, f"picture:{pc['id']}", keep=True)
    runs = res.pop("_runs")
    clean = H.run_case(wr, None, 0.0, 0.0, f"picture-clean:{pc['id']}", devices=["none"], keep=True)
    rc = clean.pop("_runs")["none"]
    out = {"case": pc, "text": wr_.text, "lines": wr_.real.get("lines"), "writer": wr_.real.get("writer"),
           "letter_height_mm": wr_.real.get("letter_height_mm"),
           "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "source", "looped")},
           "devices": {k: v for k, v in res.items() if not k.startswith("_")}, "clean": clean["none"],
           "paths": {k: MT.decimate_path(r, hz=50.0).round(3).tolist() for k, r in runs.items()},
           "clean_path": MT.decimate_path(rc, hz=50.0).round(3).tolist(),
           "intended": MT.intended_path(wr.su.scn0, hz=50.0).round(3).tolist()}
    p.write_text(json.dumps(out, default=H._jd))
    log(f"[pictures] {pc['id']}: " + ", ".join(f"{k} {v['words_read']}/{v['words_total']}" for k, v in out["devices"].items()))
    return out


def _baselines(pr: Dict) -> List[float]:
    """Ruled lines under each line of writing: the intended path's low percentile per line (by y clusters)."""
    P = np.asarray(pr["intended"], float)
    d = P[:, 2] > 0.5
    y = P[d, 1]
    if len(y) == 0:
        return []
    h = float(pr.get("letter_height_mm") or 5.0)
    pitch = WL.LINE_GAP_HEIGHTS * h
    top = y.max()
    out = []
    k = 0
    while True:
        lo, hi = top - (k + 1) * pitch, top - k * pitch
        sel = y[(y > lo) & (y <= hi + 1e-9)]
        if len(sel) == 0:
            if k > 12:
                break
            k += 1
            continue
        out.append(float(np.percentile(sel, 12)))
        k += 1
        if lo < y.min():
            break
    return out


def picture_png(pr: Dict, od: Path) -> Path:
    pc = pr["case"]
    n = pr["devices"]["none"]["words_total"]
    kind_txt = {"PD": "Parkinson's tremor recorded from a patient drawing on a tablet",
                "ET": "essential tremor recorded from a patient's hand"}[pc["kind"]]
    cls_txt = f"{pc['class']} ({pr['tremor']['amp_mm']:.2f} mm at the tip, {pr['tremor']['f0']:.1f} Hz)"
    wn, wj = pr["devices"]["none"]["words_read"], pr["devices"]["revJ_gated"]["words_read"]
    panels = [
        {"title": "What the writer meant (no tremor)", "ink": pr["clean_path"],
         "caption": f"words you can read: {pr['clean']['words_read']} of {n}"},
        {"title": "With tremor, ordinary pen", "ink": pr["paths"]["none"],
         "caption": f"words you can read: {wn} of {n}"},
        {"title": "With the same tremor, Rev J pen (tracker switched on)", "ink": pr["paths"]["revJ_gated"],
         "caption": f"words you can read: {wj} of {n}      (ordinary pen {wn} of {n} -> Rev J {wj} of {n})"},
    ]
    bl = _baselines(pr)
    for p_ in panels:
        p_["baselines_mm"] = bl
    src = ("letters written by one real adult (UCI Character Trajectories, Williams 2008, CC BY 4.0), placed on the "
           "line by the simulation" if pc["source"] == "chartraj" else
           f"real words of BRUSH writer {pr['writer']} (Kotani et al. 2020; non-commercial research use only)")
    trem = (f"tremor: {'UCI Parkinson spiral tablet data (Isenkul et al. 2014, CC BY 4.0)' if pc['kind'] == 'PD' else 'Zenodo ET accelerometry (Pardo-Valencia, Ammann, Foffani 2026, CC BY 4.0)'}, "
            f"recording {pr['tremor']['rid']}, scaled to the {pc['class']} class")
    header = f"{FG.SIM_TAG}.  {kind_txt}, {cls_txt}."
    footer = (f"SIMULATION (model HW1) with real recorded inputs. Writing: {src}. {trem}. Words read by an AI "
              f"handwriting reader (TrOCR) standing in for a person. Rev J: +-6 mm nose with the gated tracker "
              f"(PROPOSED DESIGN, not built).")
    name = f"fig_before_after_{pc['kind'].lower()}_{pc['class']}.png"
    target = (FG.RESEARCH_DIR if pc.get("research_only") else od) / name
    return FG.before_after(target, panels, header, footer, research_only=bool(pc.get("research_only")))


# ================================================================== spectra of the pen accelerometer (NewHandPD)
def pen_spectra(quick: bool) -> Dict:
    p = CACHE_DIR / ("pen_spectra_quick.json" if quick else "pen_spectra.json")
    if p.exists():
        return json.loads(p.read_text())
    from . import calib as CB, dsp as D, loaders as L
    lib = TL.load(quick)
    cal = lib["extra"]["newhandpd_calibration"]
    grid = np.arange(0.5, 20.01, 0.25)
    out = {"grid_Hz": grid.tolist(), "groups": {}, "calibration": cal}
    seen = set()
    for info, a in L.newhandpd_iter(("spiral1",) if not quick else ("spiral1",)):
        if a is None or len(a) < 4000 or info["subject"] in seen:
            continue
        seen.add(info["subject"])
        acc = CB.apply_gravity(a[:, 3:6], cal)
        c = int(0.5 * info["fs"])
        acc = acc[c:len(acc) - c]
        P = D.spectrum_on_grid(acc - D.lowpass(acc, info["fs"], 0.3), info["fs"], grid)
        out["groups"].setdefault(info["group"], []).append(P.tolist())
    p.write_text(json.dumps(out))
    return out


# ================================================================== figures
def figures(quick: bool, od: Path, log=print) -> Dict:
    lib = TL.load(quick)
    made = {}
    # --- tremor library
    ex = []
    for kind, rid_seed in (("PD", 0), ("ET", 0)):
        dr = RL.tremor("moderate", seed=rid_seed, kind=kind, split="test", duration=6.0, dt=1e-3, amp_mm=1.0, quick=quick)
        sy = RL.synthetic_like(dr, seed=0)
        sl = slice(3000, 5000)
        tt = np.arange(2000) / 1000.0
        ex.append({"t": tt, "y": dr.d[sl, 0] * 1e3, "kind": "real", "label": f"real {kind} ({dr.meta['f0']:.1f} Hz)"})
        ex.append({"t": tt, "y": sy.d[sl, 0] * 1e3, "kind": "synthetic", "label": f"model, same f and size"})
    made["tremor"] = str(FG.tremor_figure(od / "fig_tremor_library.png", lib, ex))
    log(f"[figures] {made['tremor']}")
    # --- pen accelerometer spectra
    try:
        ps = pen_spectra(quick)
        grid = np.array(ps["grid_Hz"])
        groups = {("Parkinson's" if g == "PD" else "healthy"): np.array(v) for g, v in ps["groups"].items()}
        made["pen_spectra"] = str(FG.spectra_figure(
            od / "fig_pen_acceleration_spectra.png", grid, groups,
            "Pen acceleration while drawing a spiral (NewHandPD smart pen, first spiral per person)",
            "acceleration PSD ((m/s^2)^2/Hz)",
            "DATA re-analysed (CALC): BiSP pen, sensor at the pen's rear; gravity calibration DERIVED (|a| = 1 g); median "
            "and quartiles over people; grey band 3-12 Hz. No licence stated by the dataset: statistics only."))
    except Exception as e:
        log(f"[figures] pen spectra skipped: {e!r}")
    # --- kinematics
    kp = CACHE_DIR / ("kinematics_quick.json" if quick else "kinematics.json")
    if kp.exists():
        val = json.loads(kp.read_text())
        made["kinematics"] = str(FG.kinematics_figure(od / "fig_writer_kinematics.png", val))
    # --- HW1 charts
    hw = H.run(quick=quick, log=lambda *a: None, sets=())
    ag = H.aggregate(hw["cases"])
    if ag["real"]:
        tab = {}
        for kind, kname in (("PD", "Parkinson's"), ("ET", "Essential tremor")):
            for cls in ("mild", "moderate", "severe"):
                k = f"{kind}/{cls}"
                if k in ag["real"]:
                    amp = ag["real"][k]["_amp_mm_mean"]
                    tab[f"{kname}, {cls} ({amp:.2f} mm)"] = {d: (ag["real"][k][d] or {}).get("words_of_10") for d in H.DEVICES}
        cl = ag["clean"].get("clean_real", {}).get("none") or {}
        made["words"] = str(FG.words_chart(
            od / "fig_words_read.png", tab, H.DEVICES, H.LABELS,
            "Words you can read out of 10: real handwriting with real tremor (simulation)",
            f"SIMULATION (HW1) with real inputs: BRUSH test writers (real words and timing) and real tremor recordings "
            f"of the test split, scaled to the data's severity classes (mm at the tip, peak). Reader: TrOCR (AI "
            f"handwriting reader). Without tremor the same reader reads {cl.get('words_of_10', float('nan')):.1f} of 10."))
    if ag["bridge"]:
        ser_w, ser_e = {}, {}
        names = {"syn_syn": "synthetic writing\n+ synthetic tremor\n(inputs used so far)",
                 "real_syn": "real writing\n+ synthetic tremor", "real_real": "real writing\n+ real tremor"}
        for var in ("syn_syn", "real_syn", "real_real"):
            k = f"{var}/all"
            if k in ag["bridge"]:
                ser_w[names[var]] = {d: (ag["bridge"][k][d] or {}).get("words_of_10") for d in H.DEVICES}
                ser_e[names[var]] = {d: (ag["bridge"][k][d] or {}).get("ink_err_um") for d in H.DEVICES}
        made["bridge_words"] = str(FG.bridge_chart(
            od / "fig_bridge_words.png", ser_w, H.DEVICES, H.LABELS, "words you can read, out of 10",
            "What changes when the inputs become real (tremor 1 mm peak at the tip, every row)",
            "SIMULATION (HW1). Same pens and trackers; only the inputs change. Synthetic: aiguide writers 0-5 and the "
            "stabpen tremor model at the real recordings' frequencies. Real: BRUSH test writers, UCI PD and Zenodo ET "
            "test recordings."))
        made["bridge_ink"] = str(FG.bridge_chart(
            od / "fig_bridge_ink_error.png", ser_e, H.DEVICES, H.LABELS, "ink error (micrometres, RMS)",
            "Ink error when the inputs become real (tremor 1 mm peak at the tip)",
            "SIMULATION (HW1). Ink error = RMS distance of the ink to the intended strokes of its own letter."))
    # --- before/after pictures
    pics = []
    for pc in picture_cases(quick):
        try:
            pr = picture_run(pc, log)
            pics.append(str(picture_png(pr, od)))
        except Exception as e:
            log(f"[figures] picture {pc['id']} failed: {e!r}")
    made["pictures"] = pics
    log(f"[figures] made {len(made)} groups")
    return made


# ================================================================== realdata.json, samples.json
def samples(quick: bool) -> Dict:
    panels = []
    for pc in picture_cases(quick):
        if pc.get("research_only"):
            continue
        p = PIC_DIR / f"{pc['id']}.json"
        if not p.exists():
            continue
        pr = json.loads(p.read_text())
        for dev in PIC_DEVICES:
            if dev not in pr["paths"]:
                continue
            m = pr["devices"][dev]
            panels.append({
                "id": f"{pc['id']}_{dev}", "title": f"{H.LABELS[dev]} - {pc['kind']} tremor, {pc['class']} "
                f"({pr['tremor']['amp_mm']:.2f} mm, {pr['tremor']['f0']:.1f} Hz)",
                "condition": f"real_{pc['kind'].lower()}_{pc['class']}", "device": dev,
                "caption": (f"SIMULATION with real recorded inputs. Letters of one real writer (UCI Character Trajectories, "
                            f"CC BY 4.0) composed into '{pr['text']}'; tremor recording {pr['tremor']['rid']} (CC BY 4.0) "
                            f"scaled to the {pc['class']} class. Words read by an AI handwriting reader."),
                "evidence": "SIM (real inputs)", "intended": pr["intended"], "ink": pr["paths"][dev],
                "metrics": {"ink_err_um": round(m["ink_err_um"], 1), "band_err_um": round(m["band_err_um"], 1),
                            "words_read": m["words_read"], "words_total": m["words_total"],
                            "read_text": m.get("read_text"), "at_travel_limit": m.get("at_travel_limit"),
                            "q_rms_mm": m.get("q_rms_mm")}})
    prov = provenance(quick, {"script": "realdata/report.py", "units": "mm, pen_down flag; 50 Hz; 0.001 mm"})
    return {"meta": prov, "stabpen.provenance": prov, "panels": panels}


def write(quick: bool, od: Path, log=print) -> Dict:
    lib = TL.load(quick)
    kp = CACHE_DIR / ("kinematics_quick.json" if quick else "kinematics.json")
    val = json.loads(kp.read_text()) if kp.exists() else None
    hw = H.run(quick=quick, log=lambda *a: None, sets=())
    ag = H.aggregate(hw["cases"])
    stats = WL.brush_writer_stats()
    wsum = {"brush_writers": len(stats["writers"]),
            "brush_tuning": len(WL.brush_writers("tuning", stats)), "brush_test": len(WL.brush_writers("test", stats)),
            "brush_lowercase_word_recordings": sum(len(s["lowercase_recordings"]) for s in stats["writers"].values()),
            "size_rule": WL.brush_scale.__doc__.strip()}
    from . import kinematics as KI
    out = {"stabpen.provenance": provenance(quick, {"script": "realdata/report.py"}),
           "evidence": {"data": EVIDENCE_DATA, "sim": EVIDENCE_SIM, "calc": EVIDENCE_CALC},
           "datasets": SO.table(), "datasets_not_used": SO.NOT_USED, "files": SO.status(with_hash=False),
           "tremor_library": {"classes": {k: v for k, v in lib["classes"].items() if k != "_subject_amplitudes_mm"},
                              "subject_amplitudes_mm": lib["classes"].get("_subject_amplitudes_mm"),
                              "thresholds": lib["thresholds"], "rules": lib["rules"], "shape_2d": lib["shape_2d"],
                              "duplicates_removed": lib["duplicates"], "summary": TL.summary(lib),
                              "generator_waveforms": sum(1 for x in lib["rows"] if x.get("generator")),
                              "newhandpd_calibration": lib.get("extra", {}).get("newhandpd_calibration")},
           "writing_library": wsum,
           "kinematics": {"table": KI.table(val) if val else None, "literature": KI.LIT},
           "hw1": {"aggregate": ag, "plan": hw["plan"], "n_cases": len(hw["cases"]), "devices": H.LABELS,
                   "ai2_settings": {k: v for k, v in H.ai2_models()["S"].get("gated", {}).items()},
                   "tcn": H.ai2_models().get("tcn_info")},
           "api": RL.__doc__}
    ps = CACHE_DIR / ("pen_spectra_quick.json" if quick else "pen_spectra.json")
    if ps.exists():
        d = json.loads(ps.read_text())
        grid = np.array(d["grid_Hz"])
        out["pen_acceleration_spectra"] = {"grid_Hz": d["grid_Hz"], "units": "(m/s^2)^2/Hz, DERIVED calibration",
                                           "median": {g: np.median(np.array(v), axis=0).tolist() for g, v in d["groups"].items()},
                                           "n": {g: len(v) for g, v in d["groups"].items()}}
    od.mkdir(parents=True, exist_ok=True)
    (od / "realdata.json").write_text(json.dumps(out, indent=1, default=H._jd))
    (od / "samples.json").write_text(json.dumps(samples(quick), default=H._jd))
    from . import evidence as EV
    EV.write(od / "evidence_rows.csv", out)
    log(f"[report] wrote {od}/realdata.json, samples.json, evidence_rows.csv")
    return out
