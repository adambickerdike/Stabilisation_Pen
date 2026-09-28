"""Task 2: essential tremor, before and after (SIMULATION, model HW1).

aiguide test writers 0-5 write "return library books by friday" with hand tremor at 4, 6, 8, 10 Hz and 0.3, 1.0,
2.0 mm peak (stabpen.signals.TremorSpec; tremor seeds 200-203).  The same writer, writing and tremor go through:

  none            ordinary pen, 12 g (ASSUMPTION)
  weighted        the same pen + 60 g (ASSUMPTION; comparators ACT-18/19, PDT-21/22, ACT-32)
  pencil_akf      pencil Rev P0: +-0.3 mm nib stage, the shipped AKF tracker (IMU + page sensor, fusion models)
  pencil_oracle   the same stage with perfect knowledge of the tremor (limit)
  revH_off        Rev H with the nose held at centre (a 75 g pen)
  revH_akf        Rev H nose (+-3 mm, results/revH/tip_params.json) with the shipped AKF (tuned on the pencil)
  revH_akf_revh   Rev H nose with the AKF re-tuned for Rev H by the mechanism study (training seeds only), if present
  revH_oracle     Rev H nose with perfect knowledge of the tremor (limit)

The writer is adapted to each pen (plant.adapted_path: tremor-free ink = intended letters) and compensates the paper
drag (ASSUMPTION; the P1 open-loop convention is a sensitivity case).  Tip authority is on while the pen is within 2 mm
of the paper (hover gating, T7 of docs/ai_guidance.md 7.3); contact gating (the P1 convention) is a sensitivity case.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

import numpy as np

from . import TEST_SEEDS, TEST_WRITERS, ensure_paths
from . import metrics as MT
from . import params as PR
from . import plant as PL
from . import tracker as TR
from . import writers as W

ensure_paths()

F0S = (4.0, 6.0, 8.0, 10.0)
AMPS = (0.3e-3, 1.0e-3, 2.0e-3)
DEVICES = ["none", "weighted", "pencil_akf", "pencil_oracle", "revH_off", "revH_akf", "revH_akf_revh", "revH_oracle"]
LABELS = {"none": "No device (ordinary pen)", "weighted": "Weighted pen (+60 g)",
          "pencil_akf": "Pencil Rev P0 + tracker", "pencil_oracle": "Pencil Rev P0, perfect knowledge (limit)",
          "revH_off": "Rev H, nose off (75 g pen)", "revH_akf": "Rev H + tracker as shipped (tuned on the pencil)",
          "revH_akf_revh": "Rev H + tracker re-tuned for Rev H", "revH_oracle": "Rev H, perfect knowledge (limit)"}
VIZ = {"writer": 0, "seed": 200, "cases": [(6.0, 1.0e-3), (10.0, 1.0e-3), (8.0, 2.0e-3)]}


def sensor_seed(w: int, seed: int, f0: float, amp: float, tag: int) -> int:
    return 60_000_000 + 100_000 * w + 1000 * (seed % 1000) + 10 * int(round(f0)) + int(round(amp * 1e4)) + 7 * tag


class WriterSetup:
    """Writing, recogniser and per-pen adapted hand paths and tremor-free runs of one writer (cached)."""

    def __init__(self, w: int, hand: PR.Hand, pens: Dict[str, PR.Pen], text: str = W.ET_SENTENCE, ctl_kw=None):
        self.w = w
        self.hand = hand
        self.written = W.writer(w).write(text, dt=W.SIM_DT, seed=2000 + w)
        self.scn0 = PL.scenario_from_written(self.written, None, meta={"writer": w})
        self.rec = MT.recognizer_for(self.written)
        self.text = text
        self.pens = pens
        self.ctl_kw = dict(ctl_kw or {})
        self.hp: Dict[str, np.ndarray] = {}
        self.clean: Dict[str, PL.Result] = {}
        for key, pen in pens.items():
            self.hp[key] = PL.adapted_path(self.scn0.intended, self.scn0.dt, pen, hand)
            self.clean[key] = PL.run(PL.with_hand_path(self.scn0, self.hp[key]), pen, hand, ctl=PL.Controls(**self.ctl_kw))

    def scenario(self, key: str, tremor: Optional[np.ndarray]):
        return PL.with_hand_path(self.scn0, self.hp[key], tremor)


def case_metrics(su: WriterSetup, res: PL.Result, scn: PL.Scenario, pen: PR.Pen, neutral: Optional[PL.Result] = None) -> Dict:
    rows = MT.letter_rows(su.written, res, su.rec)
    s = MT.summary(rows)
    wd = MT.words(rows, su.text)
    out = {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"), "dtw_um": s.get("dtw_mean_um"),
           "recognition": s.get("recognition_accuracy"), "word_acc_letters": wd["word_accuracy_letters"],
           "word_acc_app": wd.get("word_accuracy_app"), "recognised_words": " ".join(wd["recognised"]),
           "app_words": " ".join(wd.get("corrected", [])), "band_err_um": MT.band_error_um(res, scn),
           "aligned_err_um": MT.aligned_error_um(res, scn)}
    out.update(MT.travel(res, pen))
    if neutral is not None:
        n = min(len(res.t), len(neutral.t))
        out["handle_departure_um"] = float(np.sqrt(np.mean(np.sum((res.handle[:n] - neutral.handle[:n]) ** 2, axis=1))) * 1e6)
    return out


def run_devices(su: WriterSetup, f0: float, amp: float, seed: int, trackers: Dict, keep: bool = False,
                devices=DEVICES) -> Dict:
    """All devices on one (writer, f0, amp, seed) scenario."""
    w = su.w
    d = W.tremor_path(su.scn0.t, f0, amp, seed, w)
    out, keepers = {}, {}
    hand = su.hand
    ck = su.ctl_kw
    for key in ("none", "weighted"):
        if key not in devices:
            continue
        pen = su.pens[key]
        scn = su.scenario(key, d)
        r = PL.run(scn, pen, hand, ctl=PL.Controls(**ck))
        out[key] = case_metrics(su, r, scn, pen)
        keepers[key] = (r, scn)
    for pk, prefix in (("pencil", "pencil"), ("revH", "revH")):
        if not any(dv.startswith(prefix) for dv in devices):
            continue
        pen = su.pens[pk]
        scn = su.scenario(pk, d)
        rn = PL.run(scn, pen, hand, ctl=PL.Controls(**ck))
        if prefix == "revH" and "revH_off" in devices:
            out["revH_off"] = case_metrics(su, rn, scn, pen)
            keepers["revH_off"] = (rn, scn)
        Ts, nt = rn.info["Ts"], rn.info["n_ticks"]
        if prefix + "_oracle" in devices:
            qo = TR.oracle_command(rn, su.clean[pk], pen, nt, Ts)
            ro = PL.run(scn, pen, hand, ctl=PL.Controls(qext=qo, **ck))
            out[prefix + "_oracle"] = case_metrics(su, ro, scn, pen, rn)
            keepers[prefix + "_oracle"] = (ro, scn)
        tlist = [("_akf", trackers["ship"])]
        if prefix == "revH" and trackers.get("revh") is not None:
            tlist.append(("_akf_revh", trackers["revh"]))
        for sfx, tr in tlist:
            dk = prefix + sfx
            if dk not in devices:
                continue
            dh, inf = TR.akf_estimate(rn, scn, pen, tr, sensor_seed(w, seed, f0, amp, len(dk)))
            ra = PL.run(scn, pen, hand, ctl=PL.Controls(qext=-dh, **ck))
            out[dk] = case_metrics(su, ra, scn, pen, rn)
            out[dk]["tracker_f_est_hz"] = inf["f_est_median_hz"]
            keepers[dk] = (ra, scn)
    # ratios against the ordinary pen on the same scenario
    if "none" in out:
        for k, v in out.items():
            v["ink_err_ratio"] = v["ink_err_um"] / max(out["none"]["ink_err_um"], 1e-9)
            v["band_err_ratio"] = v["band_err_um"] / max(out["none"]["band_err_um"], 1e-9)
    res = {"writer": w, "f0": f0, "amp_mm": amp * 1e3, "seed": seed, "devices": out}
    if keep:
        res["_keep"] = keepers
    return res


def distortion(su: WriterSetup, trackers: Dict) -> Dict:
    """Tremor-free writing with each tracker switched on: the tracker's false correction (distortion)."""
    out = {}
    for pk, prefix in (("pencil", "pencil"), ("revH", "revH")):
        pen = su.pens[pk]
        scn = su.scenario(pk, None)
        rc = su.clean[pk]
        base = case_metrics(su, rc, scn, pen)
        out[prefix + "_clean"] = base
        tlist = [("_akf", trackers["ship"])]
        if prefix == "revH" and trackers.get("revh") is not None:
            tlist.append(("_akf_revh", trackers["revh"]))
        for sfx, tr in tlist:
            dh, _ = TR.akf_estimate(rc, scn, pen, tr, sensor_seed(su.w, 0, 0.0, 0.0, 50 + len(sfx)))
            ra = PL.run(scn, pen, su.hand, ctl=PL.Controls(qext=-dh, **su.ctl_kw))
            m = case_metrics(su, ra, scn, pen, rc)
            n = min(len(ra.t), len(rc.t))
            c = (ra.contact[:n] > 0.5)
            m["distortion_um"] = float(np.sqrt(np.mean(np.sum((ra.ink[:n] - rc.ink[:n])[c] ** 2, axis=1))) * 1e6)
            out[prefix + sfx] = m
    for key in ("none", "weighted"):
        scn = su.scenario(key, None)
        out[key + "_clean"] = case_metrics(su, su.clean[key], scn, su.pens[key])
    return out


def pens_default(revh: Optional[PR.Pen] = None) -> Dict[str, PR.Pen]:
    return {"none": PR.ordinary_pen(), "weighted": PR.weighted_pen(), "pencil": PR.pencil_p0(),
            "revH": revh or PR.rev_h()}


def trackers_default() -> Dict:
    return {"ship": PR.akf_ship(), "revh": PR.akf_revh()}


def writer_job(job: Dict) -> Dict:
    """One writer: every (f0, amp, seed) in the job, the tremor-free distortion check, and kept paths for figures."""
    t0 = time.time()
    hand = PR.Hand.from_config(**job.get("hand", {}))
    pens = pens_default(job.get("revh_pen"))
    trk = trackers_default()
    su = WriterSetup(job["writer"], hand, pens, ctl_kw=job.get("ctl", {}))
    rows = []
    viz = {}
    for seed in job["seeds"]:
        for f0 in job["f0s"]:
            for amp in job["amps"]:
                keep = job.get("viz") and seed == VIZ["seed"] and (f0, amp) in VIZ["cases"]
                r = run_devices(su, f0, amp, seed, trk, keep=keep, devices=job.get("devices", DEVICES))
                if keep:
                    viz[f"{f0:g}Hz_{amp * 1e3:g}mm"] = export_paths(su, r.pop("_keep"))
                rows.append(r)
    dist = distortion(su, trk) if job.get("distortion", True) else None
    out = {"writer": job["writer"], "rows": rows, "distortion": dist, "elapsed_s": time.time() - t0,
           "style": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in vars(su.written.style).items()},
           "x_height_mm": su.written.style.x_height_mm}
    if viz:
        out["viz"] = viz
        out["viz"]["intended"] = MT.intended_path(su.scn0, hz=250.0).tolist()
        out["viz"]["x_height_mm"] = su.written.style.x_height_mm
    return out


def export_paths(su: WriterSetup, keepers: Dict) -> Dict:
    """Ink paths of the kept devices (250 Hz for the figures; samples.json decimates further)."""
    return {k: MT.decimate_path(r, hz=250.0).tolist() for k, (r, scn) in keepers.items()}


# ------------------------------------------------------------------ aggregation
def aggregate(outs: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    keys = ["ink_err_um", "ink_p95_um", "band_err_um", "recognition", "word_acc_letters", "word_acc_app", "dtw_um",
            "at_travel_limit", "at_force_limit", "ink_err_ratio", "band_err_ratio", "handle_departure_um", "F_rms_N",
            "q_rms_mm"]
    by = {}
    for dv in DEVICES:
        cells = {}
        for f0 in sorted({r["f0"] for r in rows}):
            for amp in sorted({r["amp_mm"] for r in rows}):
                sel = [r["devices"][dv] for r in rows if r["f0"] == f0 and r["amp_mm"] == amp and dv in r["devices"]]
                if not sel:
                    continue
                cell = {}
                for k in keys:
                    vals = [s[k] for s in sel if s.get(k) is not None]
                    if vals:
                        cell[k] = float(np.mean(vals))
                        cell[k + "_sd"] = float(np.std(vals))
                cell["n"] = len(sel)
                cells[f"{f0:g}Hz_{amp:g}mm"] = cell
        if cells:
            by[dv] = cells
    # per amplitude, averaged over frequencies; and over everything
    per_amp = {}
    for dv, cells in by.items():
        per_amp[dv] = {}
        for amp in sorted({r["amp_mm"] for r in rows}):
            cs = [c for k, c in cells.items() if k.endswith(f"_{amp:g}mm")]
            per_amp[dv][f"{amp:g}mm"] = {k: float(np.mean([c[k] for c in cs if k in c])) for k in keys if any(k in c for c in cs)}
    dist = {}
    for o in outs:
        if o.get("distortion"):
            for k, v in o["distortion"].items():
                dist.setdefault(k, []).append(v)
    dist_agg = {k: {m: float(np.mean([x[m] for x in v if x.get(m) is not None])) for m in
                    ("ink_err_um", "recognition", "word_acc_app", "distortion_um") if any(x.get(m) is not None for x in v)}
                for k, v in dist.items()}
    return {"by_condition": by, "by_amplitude": per_amp, "tremor_free": dist_agg,
            "n_scenarios": len(rows), "writers": sorted({o["writer"] for o in outs})}
