"""Figures, results/realdata/realdata.json, samples.json and the proposed ledger rows.

Everything in results/realdata/ is either an aggregate statistic, a fitted parameter, a figure, or a short attributed
excerpt of a CC BY 4.0 recording (the before/after pictures).  Nothing from BRUSH, UNIPEN, PADS or NewHandPD other than
statistics is written there (sources.py, 'redistribute'); pictures of UNIPEN writing go to
realdata/build/figures_research_only/ (git-ignored).
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

PIC_DIR = CACHE_DIR / "pictures_v2"
REV_J = H.dkey("revJ_gated", H.HEADLINE_SENSOR)          # the Rev J row of the pictures (headline page sensor)
PIC_DEVICES = ["none", H.dkey("revH_akf", H.HEADLINE_SENSOR), REV_J, H.dkey("revJ_tcn", H.HEADLINE_SENSOR),
               "revJ_oracle", "revJ_gated"]
KIND_NAME = {"PD": "Parkinson's", "ET": "Essential tremor", "all": "Both kinds"}


def provenance(quick: bool, extra: Optional[Dict] = None) -> Dict:
    from stabpen import provenance as PV
    files = {}
    for rel in ("results/nose2/nose2.json", "results/revH/tip_params.json", "results/opt/inertial_tracker_revh.json",
                "results/sim2j/writer_fit.json"):
        p = REPO_ROOT / rel
        if p.exists():
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    md = PV.metadata(EVIDENCE_SIM, seeds={"splits": "subjects, writers and texts split tuning/test before evaluation; "
                                                   "all headline numbers from the test split",
                                          "bootstrap": "2000 writer resamples, seed 20260929"},
                     extra={"package": f"realdata-{__version__}", "quick": quick, "inputs_sha256_16": files,
                            "datasets": {k: {"licence": s.licence, "redistribute": s.redistribute} for k, s in SO.SOURCES.items()},
                            **(extra or {})})
    return md


# ================================================================== the before/after picture runs (cached)
def picture_cases(quick: bool) -> List[Dict]:
    """Fixed before any run: the composed sentence of the one CC BY writer (test-split letters) with a PD and an ET
    tremor recording of the test split at the severe and moderate class representatives (committed); the same for a
    UNIPEN test writer's note (research use only: not committed)."""
    cl = RL.classes(quick)
    out = []
    for cls in (("severe",) if quick else ("severe", "moderate")):
        for kind in ("PD", "ET"):
            out.append({"id": f"ct_{kind}_{cls}", "source": "chartraj", "kind": kind, "class": cls,
                        "amp_mm": cl[cls]["representative_mm"], "seed": 0})
    for kind in (("PD",) if quick else ("PD", "ET")):
        out.append({"id": f"unipen_{kind}_severe", "source": "unipen", "kind": kind, "class": "severe",
                    "amp_mm": cl["severe"]["representative_mm"], "seed": 0, "research_only": True})
    if quick:
        out = [o for o in out if o["kind"] == "PD"]
    return out


def picture_run(pc: Dict, log=print) -> Dict:
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    p = PIC_DIR / f"{pc['id']}.json"
    if p.exists():
        return json.loads(p.read_text())
    from handwriting import metrics as MT
    from . import ocr as OC
    OC.reader_choice(log=log)
    wr_ = RL.writing("test", seed=pc["seed"], source=pc["source"])
    wr = H.Writer(wr_, 900_000 + int(hashlib.sha1(pc["id"].encode()).hexdigest()[:5], 16))
    dr = RL.tremor_for(wr_, pc["class"], seed=pc["seed"], kind=pc["kind"], split="test", amp_mm=pc["amp_mm"])
    res = H.run_case(wr, dr.d, dr.meta["f0"], pc["amp_mm"] * 1e-3, f"picture:{pc['id']}", keep=True,
                     ocr_devices=set(PIC_DEVICES))
    runs = res.pop("_runs")
    clean = H.run_case(wr, None, 0.0, 0.0, f"picture-clean:{pc['id']}", devices=["none"], keep=True, sensors=("ideal",))
    rc = clean.pop("_runs")["none"]
    it = wr_.intended
    spans = wr_.real.get("line_spans") or []
    base = []
    for a, b in spans:
        m = (it.t >= a) & (it.t <= b) & it.pen_down
        if m.any():
            base.append(float(np.percentile(it.xy[m, 1], 12) * 1e3))
    out = {"case": pc, "page_model_version": H.page_model().version, "text": wr_.text, "lines": wr_.real.get("lines"),
           "writer": wr_.real.get("writer"),
           "letter_height_mm": wr_.real.get("letter_height_mm"), "baselines_mm": base,
           "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "source", "looped")},
           "devices": {k: v for k, v in res.items() if not k.startswith("_")}, "clean": clean["none"],
           "paths": {k: MT.decimate_path(r, hz=50.0).round(3).tolist() for k, r in runs.items()},
           "clean_path": MT.decimate_path(rc, hz=50.0).round(3).tolist(),
           "intended": MT.intended_path(wr.su.scn0, hz=50.0).round(3).tolist()}
    p.write_text(json.dumps(out, default=H._jd))
    log(f"[pictures] {pc['id']}: " + ", ".join(f"{k} {v.get('words_read')}/{v.get('words_total')}"
                                              for k, v in out["devices"].items()))
    return out


def picture_png(pr: Dict, od: Path) -> Path:
    pc = pr["case"]
    n = pr["devices"]["none"]["words_total"]
    kind_txt = {"PD": "Parkinson's tremor recorded from a patient drawing on a tablet",
                "ET": "Essential tremor recorded from a patient's hand"}[pc["kind"]]
    cls_txt = f"{pc['class']} class ({pr['tremor']['amp_mm']:.2f} mm at the tip, {pr['tremor']['f0']:.1f} Hz)"
    dn, dj = pr["devices"]["none"], pr["devices"][REV_J]
    wn, wj = dn["words_read"], dj["words_read"]
    panels = [
        {"title": "What the writer meant (the same note without tremor, ordinary pen)", "ink": pr["clean_path"],
         "caption": f"words you can read: {pr['clean']['words_read']} of {n}"},
        {"title": "With tremor, ordinary pen", "ink": pr["paths"]["none"],
         "caption": f"words you can read: {wn} of {n}"},
        {"title": "With the same tremor, Rev J pen (tracker on, realistic page sensor)", "ink": pr["paths"][REV_J],
         "caption": f"words you can read: {wj} of {n}"},
    ]
    for p_ in panels:
        p_["baselines_mm"] = pr.get("baselines_mm") or []
    src = ("letters written by one real adult (UCI Character Trajectories, Williams 2008, CC BY 4.0), placed on the "
           "line by the simulation" if pc["source"] == "chartraj" else
           "real words of a UNIPEN hpb2 test writer (HP Labs 1992, ballpoint on paper; UNIPEN research use only)")
    trem = (f"tremor: {'UCI Parkinson spiral tablet data (Isenkul et al. 2014, CC BY 4.0)' if pc['kind'] == 'PD' else 'Zenodo ET accelerometry (Pardo-Valencia, Ammann, Foffani 2026, CC BY 4.0)'}, "
            f"recording {pr['tremor']['rid']}, scaled to the {pc['class']} class")
    tl_n, tl_j = dn.get("tip_tremor_mm", float("nan")), dj.get("tip_tremor_mm", float("nan"))
    header = f"SIMULATION, not a measurement of a person.  {kind_txt}, {cls_txt}."
    footer = (f"SIMULATION (model HW1) with real recorded inputs; the same writer, text and tremor in every panel; one "
              f"fixed scale (mm on the page, 10 mm bar). Writing: {src}. {trem}. Tremor left at the tip (peak, f0 +- 2 "
              f"Hz): ordinary pen {tl_n:.2f} mm, Rev J {tl_j:.2f} mm. Words read by an AI handwriting reader (TrOCR, "
              f"literal) standing in for a person. Rev J: +-6 mm nose with ai2's gated tracker and a DeltaPen-class page "
              f"sensor (PROPOSED DESIGN, not built). Not an observed improvement of any user.")
    name = f"fig_before_after_{pc['source']}_{pc['kind'].lower()}_{pc['class']}.png"
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
    for info, a in L.newhandpd_iter(("spiral1",)):
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


# ================================================================== results cards from the HW1 aggregate
def _ci(e: Optional[Dict]) -> Dict:
    return e if isinstance(e, dict) and "mean" in e else {"mean": float("nan"), "lo": float("nan"), "hi": float("nan")}


def cards(ag: Dict) -> List[Dict]:
    """One card per population and class (headline sensor), in plain numbers, for the doc and realdata.json."""
    out = []
    for key, cd in ag.get("real", {}).items():
        kind, cls = key.split("/")
        row = {"population": KIND_NAME.get(kind, kind), "kind": kind, "class": cls,
               "tremor_in_mm": cd.get("_amp_mm_mean"), "f0_Hz": cd.get("_f0_mean"), "n_writers": cd.get("_n_writers"),
               "n_cases": cd.get("_n_cases"), "pens": {}}
        for dev in H.HEADLINE + H.BOUND:
            e = cd.get(dev)
            if not e:
                continue
            row["pens"][dev] = {
                "label": H.LABELS[dev], "words_of_10": _ci(e.get("words_of_10")),
                "words_gain_vs_ordinary": _ci(e.get("words_of_10_gain")),
                "tip_tremor_mm": _ci(e.get("tip_tremor_mm")), "tip_tremor_ratio": _ci(e.get("tip_tremor_ratio")),
                "power_reduction_pct": (e.get("tip_tremor_ratio") or {}).get("power_reduction_pct"),
                "clean_words_of_10": _ci(e.get("clean_words_of_10")),
                "false_correction_um": _ci(e.get("false_correction_um")), "coverage": _ci(e.get("coverage")),
                "cer": _ci(e.get("cer")), "at_travel_limit": _ci(e.get("at_travel_limit"))}
        out.append(row)
    return out


# ================================================================== figures
def figures(quick: bool, od: Path, log=print) -> Dict:
    lib = TL.load(quick)
    made = {}
    # --- tremor library
    ex = []
    for kind in ("PD", "ET"):
        dr = RL.tremor("moderate", seed=0, kind=kind, split="test", duration=6.0, dt=1e-3, amp_mm=1.0, quick=quick)
        sy = RL.synthetic_like(dr, seed=0)
        sl = slice(3000, 5000)
        tt = np.arange(2000) / 1000.0
        ex.append({"t": tt, "y": dr.d[sl, 0] * 1e3, "kind": "real", "label": f"real {kind} ({dr.meta['f0']:.1f} Hz)"})
        ex.append({"t": tt, "y": sy.d[sl, 0] * 1e3, "kind": "synthetic", "label": "model, same f and size"})
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
            "DATA re-analysed (CALC): BiSP pen at 1000 samples/s (file headers), sensor at the pen's rear; gravity "
            "calibration DERIVED (|a| = 1 g); median and quartiles over people; grey band 3-12 Hz. No licence stated by "
            "the dataset: statistics only."))
    except Exception as e:
        log(f"[figures] pen spectra skipped: {e!r}")
    # --- kinematics and the UNIPEN survey
    kp = CACHE_DIR / ("kinematics_quick.json" if quick else "kinematics.json")
    if kp.exists():
        val = json.loads(kp.read_text())
        made["kinematics"] = str(FG.kinematics_figure(od / "fig_writer_kinematics.png", val))
        sv = val.get("unipen_survey")
        if isinstance(sv, dict) and sv.get("rows"):
            extra = []
            b = val["sets"].get("real_brush")
            if b and "spectrum" in b:
                extra.append({"x": 100 * b["spectrum"]["share_8_12"], "y": b["speed_mm_s"]["mean"],
                              "label": "BRUSH (stylus on screens; size derived)"})
            made["survey"] = str(FG.survey_figure(od / "fig_unipen_setups.png", sv, extra))
    # --- HW1 charts
    hw = H.run(quick=quick, log=lambda *a: None, sets=())
    ag = H.aggregate(hw["cases"])
    if ag["real"]:
        groups, groups_t = [], []
        for kind in ("PD", "ET"):
            for cls in ("severe", "moderate", "mild"):
                k = f"{kind}/{cls}"
                if k not in ag["real"]:
                    continue
                cd = ag["real"][k]
                lab = f"{KIND_NAME[kind]}, {cls} ({cd['_amp_mm_mean']:.2f} mm)"
                clean = (cd.get("none") or {}).get("clean_words_of_10")
                groups.append({"label": lab, "clean": clean,
                               "dev": {d: (cd.get(d) or {}).get("words_of_10") for d in H.HEADLINE},
                               "bound": {H.dkey(b, H.HEADLINE_SENSOR): ((cd.get(b) or {}).get("words_of_10") or {}).get("mean")
                                         for b in H.BOUND}})
                groups_t.append({"label": lab, "dev": {d: (cd.get(d) or {}).get("tip_tremor_ratio")
                                                       for d in H.HEADLINE if d != "none"}})
        note = ("SIMULATION (model HW1) with real inputs: UNIPEN hpb2 test writers (real words written with a ballpoint "
                "on paper, real timing; one note of about 10 words each) and real tremor recordings of test subjects "
                "(PD: pen tip on a tablet; ET: hand), at each data class's representative size (peak at the tip). "
                "Trackers use a DeltaPen-class page sensor (pessimistic); open circles: the same pen with the ideal "
                "sensor, where read. Reader: TrOCR base, literal. Intervals: 95 % bootstrap over writers.")
        made["words"] = str(FG.words_ci_chart(od / "fig_words_read.png", groups, H.HEADLINE, H.SHORT,
                                              "Words you can read out of 10: real handwriting with real tremor (simulation)",
                                              note))
        made["tremor_left"] = str(FG.tremor_left_chart(
            od / "fig_tremor_left.png", groups_t, [d for d in H.HEADLINE if d != "none"], H.SHORT,
            "Tremor left at the pen tip, compared with an ordinary pen (simulation)",
            "SIMULATION (HW1), same cases as fig_words_read. Tremor at the tip = peak (sqrt(2) x RMS of the major axis) of "
            "ink minus intended in contact, band f0 +- 2 Hz, the class convention. An amplitude of 50 % is 75 % less "
            "power (-6 dB). Intervals: 95 % bootstrap over writers."))
    if ag["bridge"]:
        ser_w, ser_t = {}, {}
        names = {"syn_syn": "synthetic writing\n+ synthetic tremor\n(inputs used so far)",
                 "real_syn": "real writing\n+ synthetic tremor", "real_real": "real writing\n+ real tremor",
                 "real_real_dp": "real inputs\n+ DeltaPen-class\npage sensor"}
        base_devs = ["none", "revH_akf", "revJ_gated", "revJ_tcn", "revJ_oracle"]
        for var in ("syn_syn", "real_syn", "real_real", "real_real_dp"):
            k = f"{'real_real' if var == 'real_real_dp' else var}/all"
            if k not in ag["bridge"]:
                continue
            cd = ag["bridge"][k]
            sel = {d: (H.dkey(d, "deltapen") if var == "real_real_dp" else d) for d in base_devs}
            ser_w[names[var]] = {d: ((cd.get(sel[d]) or {}).get("words_of_10") or {}).get("mean") for d in base_devs}
            ser_t[names[var]] = {d: ((cd.get(sel[d]) or {}).get("tip_tremor_mm") or {}).get("mean") for d in base_devs}
        labels = {d: H.SHORT[H.dkey(d, "deltapen")] for d in base_devs}
        for d in list(ser_w.values()):
            for k_ in list(d):
                if d[k_] is not None and not np.isfinite(d[k_]):
                    d[k_] = None
        made["bridge_words"] = str(FG.bridge_chart(
            od / "fig_bridge_words.png", ser_w, base_devs, labels, "words you can read, out of 10",
            "What changes when the inputs become real (tremor 1 mm peak at the tip, every column)",
            "SIMULATION (HW1). Same pens and trackers; the inputs change from left to right, then the page sensor. "
            "Synthetic: aiguide writers 0-3 and the stabpen tremor model at the real recordings' frequencies. Real: UNIPEN "
            "hpb2 test writers, UCI PD and Zenodo ET test recordings. Words read for the ordinary pen, Rev J and the limit."))
        made["bridge_tip"] = str(FG.bridge_chart(
            od / "fig_bridge_tremor_left.png", ser_t, base_devs, labels, "tremor left at the tip (mm, peak)",
            "Tremor left at the pen tip when the inputs become real (1 mm peak at the tip going in)",
            "SIMULATION (HW1). Tip tremor = peak (sqrt(2) x RMS of the major axis) of ink minus intended, f0 +- 2 Hz.",
            nd=2))
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
                "id": f"{pc['id']}_{dev.replace('|', '_')}", "title": f"{H.LABELS[dev]} - {pc['kind']} tremor, "
                f"{pc['class']} ({pr['tremor']['amp_mm']:.2f} mm, {pr['tremor']['f0']:.1f} Hz)",
                "condition": f"real_{pc['kind'].lower()}_{pc['class']}", "device": dev,
                "caption": (f"SIMULATION with real recorded inputs, not a measurement of a person. Letters of one real "
                            f"writer (UCI Character Trajectories, CC BY 4.0) composed into '{pr['text']}'; tremor "
                            f"recording {pr['tremor']['rid']} (CC BY 4.0) scaled to the {pc['class']} class. Words read "
                            f"by an AI handwriting reader (literal)."),
                "evidence": "SIM (real inputs)", "intended": pr["intended"], "ink": pr["paths"][dev],
                "metrics": {"ink_err_um": round(m["ink_err_um"], 1), "band_err_um": round(m["band_err_um"], 1),
                            "tip_tremor_mm": round(m.get("tip_tremor_mm", float("nan")), 3),
                            "words_read": m.get("words_read"), "words_total": m.get("words_total"), "cer": m.get("cer"),
                            "read_text": m.get("read_text"), "at_travel_limit": m.get("at_travel_limit"),
                            "q_rms_mm": m.get("q_rms_mm"), "coverage": m.get("coverage")}})
    prov = provenance(quick, {"script": "realdata/report.py", "units": "mm, pen_down flag; 50 Hz; 0.001 mm"})
    return {"meta": prov, "stabpen.provenance": prov, "panels": panels}


def tremor_table(lib: Dict, path: Path) -> Path:
    """Per-recording tremor parameters of the CC BY 4.0 sources only (UCI spirals, Zenodo ET): fitted parameters with
    attribution; PADS (CC BY-NC-SA) and NewHandPD (no licence) stay as statistics in realdata.json."""
    cols = ["rid", "source", "subject", "group", "condition", "split", "duration_s", "f0", "line_ratio", "detected",
            "amp_tip_mm", "subject_amp_tip_mm", "class", "env_cv", "f_sd", "harmonic_excess", "ellipticity",
            "orientation_deg", "background_share", "generator"]
    rows = []
    for x in lib["rows"]:
        if x["source"] not in ("uci_spiral", "zenodo_et"):
            continue
        rows.append([x.get(c, "") if not isinstance(x.get(c), float) else round(x[c], 5) for c in cols])
    FG.write_csv(path, cols, rows, [
        "DATA re-analysed by study R (CALC): per-recording tremor parameters (dsp.tremor_params; Welch 4 s; background-"
        "corrected major-axis peak amplitude in mm at the pen tip for uci_spiral; zenodo_et amplitude is uncalibrated and "
        "omitted)",
        "uci_spiral: Isenkul ME, Sakar BE, Kursun O (2014), UCI Machine Learning Repository, doi 10.24432/C5Q01S, CC BY 4.0",
        "zenodo_et: Pardo-Valencia J, Ammann C, Foffani G (2026), Zenodo, doi 10.5281/zenodo.19130599, CC BY 4.0",
        "split: subject-level tuning/test; class: severity class of the subject (tuning-fitted boundaries)"])
    return path


def _page_checks(cases: List[Dict]) -> Dict:
    """The simulated DeltaPen-class window errors over all cases (a check of the construction against OPT-02)."""
    med, mean = [], []
    for c in cases:
        v = c["devices"].get("_page_check|deltapen")
        if isinstance(v, dict) and v.get("n"):
            med.append(v["median_um"])
            mean.append(v["mean_um"])
    return {"n_cases": len(med), "median_um_median": float(np.median(med)) if med else None,
            "mean_um_median": float(np.median(mean)) if mean else None,
            "target": {"median_um": 23.6, "mean_um": 68.3, "ledger": "OPT-02"}}


def _gate_open(cases: List[Dict]) -> Dict:
    """Share of time the ai2 gate is open, per set, kind and class (ideal and DeltaPen-class sensors)."""
    acc: Dict[str, List[float]] = {}
    for c in cases:
        key = c["set"] + "/" + (c.get("variant") or "") + "/" + (c.get("kind") or "") + "/" + (c.get("class") or "")
        for s_ in ("ideal", "deltapen"):
            v = c["devices"].get(f"_gate_open_frac|{s_}")
            if v is not None:
                acc.setdefault(key + "|" + s_, []).append(float(v))
    return {k: {"mean": float(np.mean(v)), "n": len(v)} for k, v in sorted(acc.items())}


def write(quick: bool, od: Path, log=print) -> Dict:
    from . import kinematics as KI
    from . import ocr as OC
    from . import sensors as RS
    lib = TL.load(quick)
    kp = CACHE_DIR / ("kinematics_quick.json" if quick else "kinematics.json")
    val = json.loads(kp.read_text()) if kp.exists() else None
    hw = H.run(quick=quick, log=lambda *a: None, sets=())
    ag = H.aggregate(hw["cases"])
    idx = WL.unipen_index()
    stats = WL.brush_writer_stats()
    wsum = {"headline_source": "unipen " + ", ".join(idx["setups"]), "rule": idx["rule"], "split": idx["split_note"],
            "unipen_writers": len(idx["writers"]), "unipen_tuning": len(WL.unipen_writers("tuning", idx)),
            "unipen_test": len(WL.unipen_writers("test", idx)), "unipen_texts": idx["n_texts"],
            "unipen_lines": sum(len(v["segments"]) for v in idx["writers"].values()),
            "brush_writers": len(stats["writers"]),
            "brush_lowercase_word_recordings": sum(len(s["lowercase_recordings"]) for s in stats["writers"].values()),
            "brush_status": "diagnostic only (timing artefact at 8-12 Hz)",
            "composition": WL.__doc__.split("Composition")[1].split("Outputs are")[0].strip()}
    pm = RS.load_model()
    rc = OC.reader_choice(log=log)
    reader = {k: rc.get(k) for k in ("chosen", "rule", "reliable")}
    for m in OC.READERS:
        reader[m] = {kk: (rc.get(m) or {}).get(kk) for kk in ("share", "ok", "total")}
    gen = {f"{s}/{sp}": sum(1 for x in lib["rows"] if x.get("generator") and x["source"] == s and x["split"] == sp)
           for s in ("uci_spiral", "zenodo_et") for sp in ("tuning", "test")}
    out = {"stabpen.provenance": provenance(quick, {"script": "realdata/report.py"}),
           "evidence": {"data": EVIDENCE_DATA, "sim": EVIDENCE_SIM, "calc": EVIDENCE_CALC},
           "datasets": SO.table(), "datasets_not_used": SO.NOT_USED, "files": SO.status(with_hash=False),
           "tremor_library": {"classes": {k: v for k, v in lib["classes"].items() if k != "_subject_amplitudes_mm"},
                              "subject_amplitudes_mm_tuning": lib["classes"].get("_subject_amplitudes_mm"),
                              "thresholds": lib["thresholds"], "rules": lib["rules"], "shape_2d": lib["shape_2d"],
                              "duplicates_removed": lib["duplicates"], "summary": TL.summary(lib),
                              "generator_waveforms": gen,
                              "newhandpd_calibration": lib.get("extra", {}).get("newhandpd_calibration")},
           "writing_library": wsum,
           "kinematics": {"table": KI.table(val) if val else None, "literature": KI.LIT,
                          "unipen_survey": (val or {}).get("unipen_survey")},
           "page_sensor_model": {"model": (pm.__dict__ if pm else None), "doc": RS.__doc__},
           "reader": reader,
           "hw1": {"cards": cards(ag), "aggregate": ag, "plan": hw["plan"], "n_cases": len(hw["cases"]),
                   "devices": H.LABELS, "headline": H.HEADLINE, "bound": H.BOUND,
                   "ai2_settings": {k: v for k, v in H.ai2_models()["S"].get("gated", {}).items()},
                   "tcn": H.ai2_models().get("tcn_info"),
                   "page_check": _page_checks(hw["cases"]), "gate_open": _gate_open(hw["cases"])},
           "api": RL.__doc__}
    ps = CACHE_DIR / ("pen_spectra_quick.json" if quick else "pen_spectra.json")
    if ps.exists():
        d = json.loads(ps.read_text())
        out["pen_acceleration_spectra"] = {"grid_Hz": d["grid_Hz"], "units": "(m/s^2)^2/Hz, DERIVED calibration",
                                           "median": {g: np.median(np.array(v), axis=0).tolist() for g, v in d["groups"].items()},
                                           "n": {g: len(v) for g, v in d["groups"].items()}}
    od.mkdir(parents=True, exist_ok=True)
    (od / "realdata.json").write_text(json.dumps(out, indent=1, default=H._jd))
    (od / "samples.json").write_text(json.dumps(samples(quick), default=H._jd))
    from . import evidence as EV
    EV.write(od / "evidence_rows.csv", out)
    tremor_table(lib, od / "tremor_library.csv")
    from . import BUILD_DIR
    tp = BUILD_DIR / ("doc_tables_quick.md" if quick else "doc_tables.md")
    tp.write_text(doc_tables(out))
    log(f"[report] wrote {od}/realdata.json, samples.json, evidence_rows.csv; tables in {tp}")
    return out


# ================================================================== markdown tables for docs/real_data.md
def doc_tables(out: Dict) -> str:
    """The plain-words table, the results cards and the bridge table in Markdown (pasted into docs/real_data.md)."""
    hw = out["hw1"]
    ag = hw["aggregate"]
    L = []

    def m(e, nd=1):
        return "n/a" if not e or not np.isfinite(e.get("mean", np.nan)) else f"{e['mean']:.{nd}f}"

    def ci(e, nd=1):
        return "n/a" if not e or not np.isfinite(e.get("mean", np.nan)) else f"{e['mean']:.{nd}f} ({e['lo']:.{nd}f}-{e['hi']:.{nd}f})"
    heads = ["none", H.dkey("revH_akf", "deltapen"), H.dkey("revJ_gated", "deltapen"), H.dkey("revJ_tcn", "deltapen"),
             "revJ_oracle"]
    L.append("| Tremor (size at the pen tip) | No tremor (same notes) | " + " | ".join(H.SHORT[d] for d in heads) + " |")
    L.append("|---|---|" + "---|" * len(heads))
    for kind in ("PD", "ET"):
        for cls in ("severe", "moderate", "mild"):
            cd = ag["real"].get(f"{kind}/{cls}")
            if not cd:
                continue
            clean = (cd.get("none") or {}).get("clean_words_of_10")
            L.append(f"| {KIND_NAME[kind]}, {cls} ({cd['_amp_mm_mean']:.2f} mm) | {m(clean)} | " +
                     " | ".join(m((cd.get(d) or {}).get("words_of_10")) for d in heads) + " |")
    L.append("")
    L.append("### Results cards")
    for kind in ("PD", "ET"):
        for cls in ("severe", "moderate", "mild"):
            cd = ag["real"].get(f"{kind}/{cls}")
            if not cd:
                continue
            L.append("")
            L.append(f"**{ {'PD': 'Parkinson' + chr(39) + 's tremor', 'ET': 'Essential tremor'}[kind]}, {cls} class: {cd['_amp_mm_mean']:.2f} mm peak at the tip, about "
                     f"{cd['_f0_mean']:.1f} Hz** ({cd['_n_writers']} test writers, {cd['_n_cases']} notes; 95 % intervals over writers)")
            L.append("")
            L.append("| | " + " | ".join(H.SHORT[d] for d in heads) + " |")
            L.append("|---|" + "---|" * len(heads))
            L.append("| Readable words out of 10 | " + " | ".join(ci((cd.get(d) or {}).get("words_of_10")) for d in heads) + " |")
            L.append("| Tremor left at the tip, mm (peak, f0 +- 2 Hz) | " +
                     " | ".join(ci((cd.get(d) or {}).get("tip_tremor_mm"), 2) for d in heads) + " |")

            def ratio(d):
                e = (cd.get(d) or {}).get("tip_tremor_ratio")
                if d == "none" or not e or not np.isfinite(e.get("mean", np.nan)):
                    return "1 (reference)" if d == "none" else "n/a"
                return f"{e['mean']:.2f} (power {100 * (e['mean'] ** 2 - 1):+.0f} %)"
            L.append("| ... as a share of the ordinary pen's (amplitude) | " + " | ".join(ratio(d) for d in heads) + " |")
            L.append("| Clean writing moved, um (tremor-free notes) | " +
                     " | ".join(("0 (reference)" if d == "none" else ci((cd.get(d) or {}).get("false_correction_um"), 0))
                                for d in heads) + " |")
            L.append("| Readable words without tremor | " + " | ".join(m((cd.get(d) or {}).get("clean_words_of_10")) for d in heads) + " |")
            L.append("| With the ideal page sensor instead: words / tremor left | " + " | ".join(
                ("-" if d in ("none", "revJ_oracle") else
                 f"{m((cd.get(d.split('|')[0]) or {}).get('words_of_10'))} / {m((cd.get(d.split('|')[0]) or {}).get('tip_tremor_mm'), 2)} mm")
                for d in heads) + " |")
    if ag.get("bridge"):
        L.append("")
        L.append("### Bridge (1 mm peak at the tip, both kinds pooled)")
        L.append("")
        base = ["none", "revH_akf", "revJ_gated", "revJ_tcn", "revJ_oracle"]
        L.append("| Inputs | " + " | ".join(H.SHORT[H.dkey(d, 'deltapen')] for d in base) + " |")
        L.append("|---|" + "---|" * len(base))
        for var, name in (("syn_syn", "synthetic writing + synthetic tremor (as before)"), ("real_syn", "real writing + synthetic tremor"),
                          ("real_real", "real writing + real tremor"), ("real_real_dp", "... + DeltaPen-class page sensor")):
            cd = ag["bridge"].get(f"{'real_real' if var == 'real_real_dp' else var}/all")
            if not cd:
                continue
            cells = []
            for d in base:
                k = H.dkey(d, "deltapen") if var == "real_real_dp" else d
                e = cd.get(k) or {}
                cells.append(f"{m(e.get('words_of_10'))} words; {m(e.get('tip_tremor_mm'), 2)} mm")
            L.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(L)
