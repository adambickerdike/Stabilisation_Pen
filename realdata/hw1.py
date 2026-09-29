"""The headline comparison on REAL inputs in model HW1 (SIMULATION; handwriting/, aiprior/, ai2/, fusion/ used read-only).

Pens and controllers (the same hand, writing, tremor and sensor draws for every row of one case):
  none         ordinary 12 g pen (ASSUMPTION mass, HW1)
  revH_akf     Rev H (+-3 mm nose, results/revH/tip_params.json) + the AKF tracker re-tuned for Rev H (as built)
  revJ_gated   Rev J nose (+-6 mm, results/nose2/nose2.json 'revJ', DEC-044) + ai2's adopted gated listening tracker
  revJ_tcn     Rev J nose + ai2's causal TCN (the candidate successor; trained on synthetic writers)
  revJ_oracle  Rev J nose with perfect knowledge of the tremor (the limit of the mechanism, not a design)
Page sensor of the trackers (sensors.py): every tracker row is run twice on the same case,
  ideal        fusion default, 1 kHz, 2 ms, 3 um white noise (ASSUMPTION): the labelled BOUND ('revJ_gated')
  deltapen     a DeltaPen-class error model fitted to LIT OPT-02 (pessimistic: all of DeltaPen's measured window
               error is given to the sensor): the HEADLINE sensor ('revJ_gated|deltapen')
The ordinary pen and the perfect-knowledge limit use no sensor.
Conventions as the handwriting / aiprior / ai2 studies: the writer is adapted to each pen (tremor-free ink = intended
letters) and compensates the paper drag; the nose acts while the tip is within 2 mm of the page; the trackers run
causally on the fusion sensor models of the nose-held run; the oracle previews the servo group delay.

Measures (the results card: review 2026-09-29 s13):
  words read        readable words out of 10: the AI reader (ocr.py, TrOCR; literal, greedy, no lexicon) reads each
                    line of the drawn ink; words equal to the intended words (lower case, letters only)
  cer               character error rate of the same reading
  tip tremor        tremor left at the tip: power amplitude (sqrt(2) x RMS of the major axis; the class convention)
                    of ink minus intended in contact, band f0 +- 2 Hz (zero-phase measurement filter), mm (CALC)
  ink error         RMS distance of in-contact ink to the intended strokes of its own stroke (pseudo-letter)
  band error        3-15 Hz RMS of ink minus intended (handwriting.metrics.band_error_um)
  coverage          share of the intended pen-down time with ink (missing strokes lower it)
  nose travel       share of contact time at >= 95 % of the usable travel (handwriting.metrics.travel)
  false correction  tremor-free writing: RMS ink displacement against the nose-held run (ai2 definition): the
                    'clean writing changed' line of the card, with the words read on the tremor-free ink

Input sets (TEST split only; writers, texts and tremor subjects split before any evaluation):
  real        real writing (UNIPEN hpb2 test writers: ballpoint on paper, one note of about 10 words each) + real tremor
              (PD: uci_spiral tip; ET: zenodo_et hand, test subjects) at each data severity class's representative
              amplitude (the median of the class's tuning subjects: tremorlib), both sensors
  clean       the same notes without tremor (the reader's ceiling and the false correction), both sensors
  bridge      at a fixed 1 mm and the real recordings' frequencies, to explain the change from the old results:
                syn_syn    synthetic writers (aiguide test writers 0-3) + synthetic tremor (stabpen TremorSpec), ideal
                real_syn   real writing + synthetic tremor with the real recording's frequency, ideal
                real_real  real writing + real tremor, ideal and deltapen
Uncertainty: 95 % intervals by bootstrap over WRITERS (participant level; 2000 resamples, seed fixed).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import CACHE_DIR, REPO_ROOT, ensure_paths
from . import library as RL
from . import ocr as OC

ensure_paths()
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import tracker as TR  # noqa: E402

BASE_DEVICES = ["none", "revH_akf", "revJ_gated", "revJ_tcn", "revJ_oracle"]
TRACKERS = ["revH_akf", "revJ_gated", "revJ_tcn"]
SENSORS = ("ideal", "deltapen")
HEADLINE_SENSOR = "deltapen"


def dkey(dev: str, sensor: str = "ideal") -> str:
    """Result key of a device on a page sensor ('revJ_gated' = ideal bound, 'revJ_gated|deltapen' = headline)."""
    return dev if (sensor == "ideal" or dev not in TRACKERS) else f"{dev}|{sensor}"


DEVICES = BASE_DEVICES + [dkey(d, "deltapen") for d in TRACKERS]
HEADLINE = ["none", dkey("revH_akf", HEADLINE_SENSOR), dkey("revJ_gated", HEADLINE_SENSOR),
            dkey("revJ_tcn", HEADLINE_SENSOR), "revJ_oracle"]
BOUND = ["revH_akf", "revJ_gated", "revJ_tcn"]
LABELS = {"none": "Ordinary pen", "revH_akf": "Rev H + tracker (as built), ideal page sensor",
          "revJ_gated": "Rev J + gated tracker, ideal page sensor",
          "revJ_tcn": "Rev J + learned tracker (TCN), ideal page sensor",
          "revJ_oracle": "Rev J, perfect knowledge (limit)",
          "revH_akf|deltapen": "Rev H + tracker (as built)", "revJ_gated|deltapen": "Rev J + gated tracker",
          "revJ_tcn|deltapen": "Rev J + learned tracker (TCN)"}
SHORT = {"none": "Ordinary pen", "revH_akf": "Rev H (ideal sensor)", "revJ_gated": "Rev J (ideal sensor)",
         "revJ_tcn": "Rev J + AI (ideal sensor)", "revJ_oracle": "Rev J limit", "revH_akf|deltapen": "Rev H",
         "revJ_gated|deltapen": "Rev J", "revJ_tcn|deltapen": "Rev J + AI"}
HW1_DIR = CACHE_DIR / "hw1"
RUN_TAG = "v2"          # UNIPEN notes, both page sensors, results-card measures


# ------------------------------------------------------------------ pens and the ai2 estimators (read-only)
def revj_pen() -> PR.Pen:
    """The Rev J nose as an HW1 pen: results/nose2/nose2.json -> hw1_designs['revJ'] (CALC, PROPOSED DESIGN)."""
    d = json.loads((REPO_ROOT / "results" / "nose2" / "nose2.json").read_text())["hw1_designs"]["revJ"]
    return PR.Pen(d["key"], d["label"], mass=d["mass"], rigid=False, m_tip=d["m_tip"], k_tip=d["k_tip"], zeta_tip=0.05,
                  q_lim=d["q_lim"], q_taper=0.1 * d["q_lim"], q_stop=d["q_stop"], servo_hz=d["servo_hz"],
                  servo_zeta=d["servo_zeta"], latency=d["latency"], slew=d["slew"], F_peak=d["F_peak"],
                  F_cont=d["F_cont"], skid=True, F_c=d["F_c"], r_imu=d["r_imu"],
                  sources={"file": "results/nose2/nose2.json hw1_designs.revJ", "label": "CALC on a PROPOSED DESIGN (study N)"})


def pens() -> Dict[str, PR.Pen]:
    return {"none": PR.ordinary_pen(), "revH": PR.rev_h(), "revJ": revj_pen()}


_AI2: Dict = {}


def ai2_models(with_tcn: bool = True) -> Dict:
    """ai2's settings fixed on its tuning data (stage d01/d2b), the model-based parameters and the TCN, if present."""
    if _AI2:
        return _AI2
    from ai2 import stage_learn_data as SLD
    from ai2 import stage_test as ST
    S = ST.settings(False)
    mp = SLD.model_params(False)
    tcn = None
    info = {}
    if with_tcn:
        try:
            from ai2 import stage_learn as SL
            tcn, info = SL.load_model("tcn", False)
        except Exception as e:          # the TCN is a git-ignored build product of ai2
            info = {"error": repr(e)}
    _AI2.update({"S": S, "mp": mp, "tcn": tcn, "tcn_info": {k: v for k, v in info.items() if k != "history"}})
    return _AI2


# ------------------------------------------------------------------ duck-typed aiprior writer and scenario
class _SU:
    def __init__(self, written, hand, pens_: Dict[str, PR.Pen]):
        self.written = written
        self.text = written.text
        self.hand = hand
        self.scn0 = PL.scenario_from_written(written, None)
        self.pens = pens_
        self.hp = {k: PL.adapted_path(self.scn0.intended, self.scn0.dt, p, hand) for k, p in pens_.items()}
        self.clean = {k: PL.run(PL.with_hand_path(self.scn0, self.hp[k]), p, hand) for k, p in pens_.items()}

    def scenario(self, key: str, tremor):
        return PL.with_hand_path(self.scn0, self.hp[key], tremor)


class Writer:
    """What aiprior.core.Writer offers, for any Written (real or synthetic)."""

    def __init__(self, written, wid: int):
        from aiprior import core as CO
        self.w = int(wid)
        self.hand = PR.Hand.from_config()
        self.pens = pens()
        self.su = _SU(written, self.hand, self.pens)
        self.written = written
        self.rec = None
        self.trk = CO.tracker()

    @property
    def scn0(self):
        return self.su.scn0


@dataclass
class Scen:
    """aiprior.core.Scenario for pen `key` (Rev H or Rev J)."""
    wr: Writer
    key: str
    f0: float
    amp: float
    seed: int
    scn: PL.Scenario
    neutral: PL.Result
    streams: object
    dh: np.ndarray
    info: Dict
    runs: Dict = field(default_factory=dict)
    extra: Dict = field(default_factory=dict)

    @property
    def pen(self):
        return self.wr.pens[self.key]

    @property
    def Ts(self):
        return self.neutral.info["Ts"]

    @property
    def n_ticks(self):
        return self.neutral.info["n_ticks"]


def make_scen(wr: Writer, key: str, tremor: Optional[np.ndarray], f0: float, amp: float, seed: int, s_seed: int,
              page=None, base: Optional[Scen] = None) -> Scen:
    """The nose-held run, its sensor streams (ideal, or degraded by the page model) and the Rev H tracker estimate.
    base: a Scen of the same case whose nose-held run is reused (only the sensors differ)."""
    from aiprior import core as CO
    from fusion import estimators as ES
    from . import sensors as RS
    pen = wr.pens[key]
    if base is not None:
        scn, neutral = base.scn, base.neutral
    else:
        scn = wr.su.scenario(key, tremor)
        neutral = wr.su.clean[key] if tremor is None else PL.run(scn, pen, wr.hand, ctl=PL.Controls())
    st = CO.streams_for(neutral, scn, pen, wr.trk, s_seed)
    if page is not None:
        st = RS.degrade_page(st, page, s_seed + 17)
    dh, info = ES.akf(st, CO.tracker_params(pen, wr.trk))
    return Scen(wr, key, f0, amp, seed, scn, neutral, st, dh, info)


_PAGE: Dict = {}


def page_model(quick: bool = False, log=print):
    """The DeltaPen-class page model, fitted once on the TUNING writers' clean notes (cached)."""
    from . import sensors as RS
    if "m" in _PAGE:
        return _PAGE["m"]
    m = RS.load_model()
    if m is None:
        from . import writinglib as WL
        ws = WL.unipen_writers("tuning")
        notes = [RL.writing("tuning", seed=i, dt=1e-3) for i in range(2 * len(ws))]
        m = RS.fit_window_error(notes)
        RS.save_model(m)
        log(f"[hw1] page model fitted on {len(notes)} tuning notes: c {m.c * 1e6:.1f} um, sigma {m.sigma:.2f}, "
            f"median {m.fitted['median_um']:.1f} um, mean {m.fitted['mean_um']:.1f} um")
    _PAGE["m"] = m
    return m


# ------------------------------------------------------------------ measures
def path_error_um(written, res, pad: float = 0.002) -> float:
    """RMS nearest-point distance of in-contact ink to its own letter's intended strokes (every stroke of the
    letter, delayed ones included)."""
    from scipy.spatial import cKDTree
    from aiguide.metrics import dense
    t, ink, con = res.t, res.ink, res.contact > 0.5
    it = written.intended
    d_all = []
    for Lt in written.letters:
        if not Lt.strokes:
            continue
        m = np.zeros(len(t), bool)
        for a, b in Lt.strokes:
            m |= (t >= it.t[a] - pad) & (t <= it.t[min(b, len(it.t) - 1)] + pad)
        m &= con
        if m.sum() < 4:
            continue
        polys = [it.xy[a:b:40] if b - a > 80 else it.xy[a:b] for a, b in Lt.strokes]
        tree = cKDTree(dense(polys))
        d, _ = tree.query(ink[m])
        d_all.append(d)
    if not d_all:
        return float("nan")
    d = np.concatenate(d_all)
    return float(np.sqrt(np.mean(d ** 2)) * 1e6)


def tip_tremor_mm(res, scn, f0: float, min_seg_s: float = 0.5) -> float:
    """Tremor left at the tip: power amplitude (sqrt(2) x RMS of the major axis, the class convention) of ink minus
    intended over contact segments of at least 0.5 s, band f0 +- 2 Hz (4th-order zero-phase: a measurement)."""
    from scipy.signal import butter, sosfiltfilt
    if not f0 or f0 <= 0:
        return float("nan")
    k = np.clip(np.round(res.t / scn.dt).astype(int), 0, len(scn.t) - 1)
    fs0 = 1.0 / float(res.t[1] - res.t[0])
    dec = max(1, int(round(fs0 / 1000.0)))
    e = (res.ink - scn.intended[k])[::dec]
    con = (res.contact > 0.5)[::dec]
    fs = fs0 / dec
    sos = butter(4, (max(1.0, f0 - 2.0), f0 + 2.0), btype="band", fs=fs, output="sos")
    idx = np.flatnonzero(con)
    if len(idx) < int(min_seg_s * fs):
        return float("nan")
    parts = []
    for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        if len(r) < int(min_seg_s * fs):
            continue
        eb = sosfiltfilt(sos, e[r], axis=0)
        trim = int(0.1 * fs)
        if len(eb) > 2 * trim + 10:
            parts.append(eb[trim:len(eb) - trim])
    if not parts:
        return float("nan")
    X = np.vstack(parts)
    X = X - X.mean(0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    major = X @ vt[0]
    return float(np.sqrt(2.0) * np.sqrt(np.mean(major ** 2)) * 1e3)


def coverage(written, res) -> float:
    """Share of the intended pen-down time with the tip in contact (missing or cut strokes lower it)."""
    it = written.intended
    k = np.clip(np.round(res.t / written.dt).astype(int), 0, len(it.t) - 1)
    want = it.pen_down[k]
    return float(np.mean(res.contact[want] > 0.5)) if want.any() else float("nan")


def measures(wr: Writer, res, scn, pen, ocr: bool = True, f0: float = 0.0) -> Dict:
    out = {"ink_err_um": path_error_um(wr.written, res), "band_err_um": MT.band_error_um(res, scn),
           "tip_tremor_mm": tip_tremor_mm(res, scn, f0), "coverage": coverage(wr.written, res)}
    tv = MT.travel(res, pen)
    out.update({k: tv.get(k) for k in ("at_travel_limit", "q_rms_mm", "q_max_mm", "F_rms_N") if k in tv})
    if ocr:
        w = OC.words_read(res, wr.written)
        out.update({"words_read": w["words_read"], "words_total": w["words_total"], "words_share": w["share"],
                    "cer": w["cer"], "read_text": " | ".join(l["read"] for l in w["lines"])})
    return out


def _seed(*key) -> int:
    return int(hashlib.sha1(":".join(map(str, key)).encode()).hexdigest()[:7], 16)


# ------------------------------------------------------------------ one case: every pen on the same inputs
OCR_REAL = set(HEADLINE) | {"revJ_gated"}        # read by the AI reader (the others: tip tremor and ink only)
OCR_BRIDGE = {"none", "revJ_gated", "revJ_gated|deltapen", "revJ_oracle"}


def run_case(wr: Writer, tremor: Optional[np.ndarray], f0: float, amp: float, case_key: str, devices=BASE_DEVICES,
             keep: bool = False, ocr: bool = True, sensors: Sequence[str] = SENSORS,
             ocr_devices: Optional[Sequence[str]] = None) -> Dict:
    """Every pen on the same writing and tremor; the trackers once per page sensor (same case, same draws).
    ocr_devices: result keys read by the AI reader (default: the headline pens and Rev J with the ideal sensor)."""
    rd = set(OCR_REAL if ocr_devices is None else ocr_devices)

    def reads(k):
        return bool(ocr) and k in rd
    from ai2 import candidates as CA
    from ai2 import delayed as DL
    M = ai2_models()
    DL.OUT_EVERY = 1
    hand = wr.hand
    out, runs = {}, {}
    t0 = time.time()
    clean = tremor is None
    pm = page_model() if any(s_ != "ideal" for s_ in sensors) else None
    if "none" in devices:
        scn = wr.su.scenario("none", tremor)
        r = PL.run(scn, wr.pens["none"], hand)
        out["none"] = measures(wr, r, scn, wr.pens["none"], reads("none"), f0)
        runs["none"] = r
    if "revH_akf" in devices:
        base = None
        for sensor in sensors:
            sH = make_scen(wr, "revH", tremor, f0, amp, 0, _seed(case_key, "revH"),
                           page=None if sensor == "ideal" else pm, base=base)
            base = base or sH
            r = PL.run(sH.scn, sH.pen, hand, ctl=PL.Controls(qext=np.ascontiguousarray(-sH.dh)))
            k = dkey("revH_akf", sensor)
            out[k] = measures(wr, r, sH.scn, sH.pen, reads(k), f0)
            if clean:
                out[k]["false_correction_um"] = DL.ink_timeline_error(sH, r, np.zeros(len(sH.dh)), sH.neutral)
            runs[k] = r
    if any(d.startswith("revJ") for d in devices):
        base = None
        S = M["S"]
        for si, sensor in enumerate(sensors):
            sJ = make_scen(wr, "revJ", tremor, f0, amp, 0, _seed(case_key, "revJ"),
                           page=None if sensor == "ideal" else pm, base=base)
            base = base or sJ
            tick_t = sJ.streams.tick_t
            cfg = DL.DelayCfg(tremor=S["tremor"], det=S["det"] or {})
            cfg.amp_lo, cfg.amp_hi = S["gated"]["amp_lo"], S["gated"]["amp_hi"]
            est = DL.estimates(sJ, cfg, lags=CA.LAGS_CL)
            zeros = np.zeros(len(tick_t))
            qs = {}
            if "revJ_gated" in devices:
                qs["revJ_gated"] = DL.command(est, zeros, tick_t)
            if "revJ_tcn" in devices and M["tcn"] is not None:
                X, tk, mb = CA.arrays(sJ, M["mp"])
                cm = CA.commands(sJ, est, M["mp"], {"learned": {"tcn": M["tcn"]}}, X, tk, mb)
                qs["revJ_tcn"] = cm["learned_tcn"]
            if "revJ_oracle" in devices and not clean and si == 0:
                qs["revJ_oracle"] = TR.oracle_command(sJ.neutral, wr.su.clean["revJ"], sJ.pen, sJ.n_ticks, sJ.Ts)
            for name, q in qs.items():
                k = dkey(name, sensor)
                r = PL.run(sJ.scn, sJ.pen, hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
                out[k] = measures(wr, r, sJ.scn, sJ.pen, reads(k), f0)
                if clean:
                    out[k]["false_correction_um"] = DL.ink_timeline_error(sJ, r, zeros, sJ.neutral)
                runs[k] = r
            out[f"_gate_open_frac|{sensor}"] = float(np.mean(est["g"] > 0.5))
            if sensor != "ideal":
                from . import sensors as RS
                out[f"_page_check|{sensor}"] = RS.window_error_check(base.streams, sJ.streams)
    out["_elapsed_s"] = time.time() - t0
    if keep:
        out["_runs"] = runs
    return out


# ------------------------------------------------------------------ the input sets
def _cache(path) -> Optional[Dict]:
    return json.loads(path.read_text()) if path.exists() else None


def real_writer(split: str, i: int, quick: bool = False) -> Writer:
    """Note i of the split: writer ws[i % n], lines chosen with seed i (UNIPEN hpb2)."""
    wr = RL.writing(split, seed=i, source="unipen")
    return Writer(wr, 200_000 + i)


def synthetic_writer(w: int) -> Writer:
    from handwriting import writers as HWW
    wr = HWW.writer(w).write(HWW.ET_SENTENCE, dt=HWW.SIM_DT, seed=2000 + w)
    return Writer(wr, w)


def plan(quick: bool) -> Dict:
    """The case list, fixed before any case runs: one note per TEST writer (UNIPEN hpb2), both tremor kinds, the three
    data classes; bridge at 1 mm on the first four test writers and aiguide test writers 0-3."""
    from . import writinglib as WL
    n_test = len(WL.unipen_writers("test"))
    n_real = 2 if quick else n_test
    n_bridge = 2 if quick else min(4, n_test)
    n_syn = 2 if quick else 4
    classes = ["moderate", "severe"] if quick else ["mild", "moderate", "severe"]
    kinds = ["PD", "ET"]
    return {"real": {"writers": list(range(n_real)), "classes": classes, "kinds": kinds, "sensors": list(SENSORS)},
            "bridge": {"writers_real": list(range(n_bridge)), "writers_syn": list(range(n_syn)), "amp_mm": 1.0,
                       "kinds": kinds, "sensors": {"syn_syn": ["ideal"], "real_syn": ["ideal"],
                                                   "real_real": list(SENSORS)}},
            "tag": RUN_TAG}


def run(quick: bool = False, log=print, sets: Sequence[str] = ("real", "bridge", "clean")) -> Dict:
    P = plan(quick)
    base = HW1_DIR / (("quick" if quick else "full") + "_" + RUN_TAG)
    base.mkdir(parents=True, exist_ok=True)
    ai2_models()
    page_model(quick, log)
    rc = OC.reader_choice(log=log)
    P["reader"] = rc["chosen"]
    out = {"plan": P, "cases": [], "reader": {k: rc.get(k) for k in ("chosen", "rule", "reliable")}}
    # --- real writing and real tremor at the data classes, and the tremor-free notes (ceiling, false correction);
    # computed in the order severe, moderate, clean, (bridge), mild so that the most informative cases come first
    wrs: Dict[int, Writer] = {}

    def W_(i):
        if i not in wrs:
            wrs.clear()
            wrs[i] = real_writer("test", i, quick)
        return wrs[i]

    def real_cases(cls):
        for i in P["real"]["writers"]:
            for kind in P["real"]["kinds"]:
                p = base / f"real_w{i}_{kind}_{cls}.json"
                res = _cache(p)
                if res is None and "real" in sets:
                    wr = W_(i)
                    # the class's representative amplitude (median of its tuning subjects), a test-split waveform
                    dr = RL.tremor_for(wr.written, cls, seed=i, kind=kind, split="test",
                                       amp_mm=RL.classes(quick)[cls]["representative_mm"])
                    res = {"set": "real", "writer": wr.written.real["writer"], "note": i, "kind": kind, "class": cls,
                           "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")},
                           "devices": run_case(wr, dr.d, dr.meta["f0"], dr.meta["amp_mm"] * 1e-3, f"real:{i}:{kind}:{cls}")}
                    p.write_text(json.dumps(res, default=_jd))
                    log(f"[hw1] real w{i} {kind} {cls} {dr.meta['amp_mm']:.2f} mm {dr.meta['f0']:.1f} Hz: " + _fmt(res["devices"]))
                if res:
                    out["cases"].append(res)

    def clean_cases():
        for i in P["real"]["writers"]:
            cp = base / f"clean_real_w{i}.json"
            res = _cache(cp)
            if res is None and "clean" in sets:
                wr = W_(i)
                res = {"set": "clean_real", "writer": wr.written.real["writer"], "note": i, "text": wr.written.text,
                       "devices": run_case(wr, None, 0.0, 0.0, f"clean:{i}")}
                cp.write_text(json.dumps(res, default=_jd))
                log(f"[hw1] clean real note {i} ({res['writer']}): " + _fmt(res["devices"]))
            if res:
                out["cases"].append(res)

    for cls in [c for c in ("severe", "moderate") if c in P["real"]["classes"]]:
        real_cases(cls)
    clean_cases()
    # --- bridge at 1 mm (cached cases are always loaded; missing ones are computed only if "bridge" is in sets)
    B = P["bridge"]
    amp = B["amp_mm"]
    comp = "bridge" in sets
    for i in B["writers_real"]:
        wr = None
        for kind in B["kinds"]:
            for variant in ("real_real", "real_syn"):
                p = base / f"bridge_{variant}_w{i}_{kind}.json"
                res = _cache(p)
                if res is None and comp:
                    wr = W_(i)
                    dr = RL.tremor_for(wr.written, "moderate", seed=1000 + i, kind=kind, split="test", amp_mm=amp)
                    if variant == "real_syn":
                        dr = RL.synthetic_like(dr, seed=i)
                    res = {"set": "bridge", "variant": variant, "writer": wr.written.real["writer"], "note": i, "kind": kind,
                           "tremor": {"rid": dr.meta["rid"], "amp_mm": amp, "f0": dr.meta["f0"]},
                           "devices": run_case(wr, dr.d, dr.meta["f0"], amp * 1e-3, f"bridge:{variant}:{i}:{kind}",
                                               sensors=B["sensors"][variant], ocr_devices=OCR_BRIDGE)}
                    p.write_text(json.dumps(res, default=_jd))
                    log(f"[hw1] bridge {variant} w{i} {kind} f0 {dr.meta['f0']:.1f}: " + _fmt(res["devices"]))
                if res:
                    out["cases"].append(res)
    for j, w in enumerate(B["writers_syn"]):
        ws = None
        p0 = base / f"clean_syn_w{w}.json"
        res = _cache(p0)
        if res is None and comp:
            ws = ws or synthetic_writer(w)
            res = {"set": "clean_syn", "writer": f"aiguide/{w}", "text": ws.written.text,
                   "devices": run_case(ws, None, 0.0, 0.0, f"clean_syn:{w}", sensors=("ideal",), ocr_devices=OCR_BRIDGE)}
            p0.write_text(json.dumps(res, default=_jd))
            log(f"[hw1] clean synthetic writer {w}: " + _fmt(res["devices"]))
        if res:
            out["cases"].append(res)
        for kind in B["kinds"]:
            p = base / f"bridge_syn_syn_w{w}_{kind}.json"
            res = _cache(p)
            if res is None and comp:
                ws = ws or synthetic_writer(w)
                # the frequency of a real test recording of this kind (as the other bridge rows), synthetic waveform
                dr = RL.tremor(t=ws.written.intended.t, cls="moderate", seed=1000 + j, kind=kind, split="test", amp_mm=amp)
                dr = RL.synthetic_like(dr, seed=w)
                res = {"set": "bridge", "variant": "syn_syn", "writer": f"aiguide/{w}", "kind": kind,
                       "tremor": {"rid": dr.meta["rid"], "amp_mm": amp, "f0": dr.meta["f0"]},
                       "devices": run_case(ws, dr.d, dr.meta["f0"], amp * 1e-3, f"bridge:syn_syn:{w}:{kind}",
                                           sensors=B["sensors"]["syn_syn"], ocr_devices=OCR_BRIDGE)}
                p.write_text(json.dumps(res, default=_jd))
                log(f"[hw1] bridge syn_syn aiguide {w} {kind} f0 {dr.meta['f0']:.1f}: " + _fmt(res["devices"]))
            if res:
                out["cases"].append(res)
    if "mild" in P["real"]["classes"]:
        real_cases("mild")
    return out


def _fmt(dv: Dict) -> str:
    return ", ".join(f"{k} {v.get('words_read', '-')}/{v.get('words_total', '-')} "
                     f"{v.get('tip_tremor_mm', float('nan')):.2f}mm" for k, v in dv.items()
                     if not k.startswith("_") and isinstance(v, dict))


def _jd(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ------------------------------------------------------------------ aggregation (writer-level bootstrap)
METRICS = ("words_read", "words_total", "words_share", "cer", "tip_tremor_mm", "ink_err_um", "band_err_um",
           "coverage", "at_travel_limit", "false_correction_um", "q_rms_mm")
N_BOOT = 2000


def _boot(per_writer: Dict[str, float], seed: int = 20260929) -> Dict:
    """Mean over writers and its 95 % bootstrap interval (resampling writers)."""
    v = np.array([x for x in per_writer.values() if np.isfinite(x)])
    if len(v) == 0:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n_writers": 0}
    rng = np.random.default_rng(seed)
    bs = v[rng.integers(0, len(v), (N_BOOT, len(v)))].mean(axis=1) if len(v) > 1 else np.full(N_BOOT, v[0])
    return {"mean": float(v.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
            "n_writers": int(len(v))}


def _per_writer(sel: List[Dict], dev: str, metric: str, ref: Optional[str] = None, fn=None) -> Dict[str, float]:
    """Per writer: the mean over its cases of metric (or metric(dev) - metric(ref), or fn(dev, ref))."""
    acc: Dict[str, List[float]] = {}
    for c in sel:
        d = c["devices"].get(dev)
        if d is None:
            continue
        if fn is not None:
            r = c["devices"].get(ref) if ref else None
            x = fn(d, r)
        else:
            x = d.get(metric)
            if x is None:
                continue
            x = float(x)
            if ref is not None:
                r = c["devices"].get(ref)
                if r is None or r.get(metric) is None:
                    continue
                x = x - float(r[metric])
        if x is not None and np.isfinite(x):
            acc.setdefault(c["writer"], []).append(float(x))
    return {w: float(np.mean(v)) for w, v in acc.items()}


def _of10(d, r=None):
    return 10.0 * float(d["words_read"]) / max(float(d["words_total"]), 1.0) if d.get("words_total") else float("nan")


def card(sel: List[Dict], devices: Sequence[str], clean: Optional[List[Dict]] = None) -> Dict:
    """One results card: per device, readable words out of 10, tremor left at the tip (mm; ratio to the ordinary
    pen and its meaning in power), ink error, coverage, travel; with writer-bootstrap 95 % intervals."""
    out = {}
    for dev in devices:
        if not any(dev in c["devices"] for c in sel):
            continue
        e = {"n_cases": sum(1 for c in sel if dev in c["devices"])}
        e["words_of_10"] = _boot(_per_writer(sel, dev, "", fn=_of10))
        if dev != "none":
            e["words_of_10_gain"] = _boot(_per_writer(sel, dev, "", ref="none",
                                                      fn=lambda d, r: _of10(d) - _of10(r) if r else float("nan")))
        for m in ("tip_tremor_mm", "cer", "ink_err_um", "band_err_um", "coverage", "at_travel_limit", "q_rms_mm"):
            e[m] = _boot(_per_writer(sel, dev, m))
        if dev != "none":
            ratio = _per_writer(sel, dev, "", ref="none",
                                fn=lambda d, r: (float(d["tip_tremor_mm"]) / float(r["tip_tremor_mm"]))
                                if (r and np.isfinite(float(d.get("tip_tremor_mm", np.nan))) and
                                    float(r.get("tip_tremor_mm", 0) or 0) > 0) else float("nan"))
            b = _boot(ratio)
            b["power_reduction_pct"] = float(100.0 * (1.0 - b["mean"] ** 2)) if np.isfinite(b["mean"]) else float("nan")
            b["dB"] = float(20.0 * np.log10(b["mean"])) if (np.isfinite(b["mean"]) and b["mean"] > 0) else float("nan")
            b["meaning"] = "amplitude ratio to the ordinary pen; power (squared-signal) ratio = its square"
            e["tip_tremor_ratio"] = b
        if clean:
            e["clean_words_of_10"] = _boot(_per_writer(clean, dev, "", fn=_of10))
            e["false_correction_um"] = _boot(_per_writer(clean, dev, "false_correction_um"))
        out[dev] = e
    return out


def aggregate(cases: List[Dict]) -> Dict:
    """Results cards per set, kind and class, with writer-level bootstrap intervals."""
    out: Dict = {"real": {}, "bridge": {}, "clean": {}, "devices": DEVICES, "headline": HEADLINE, "bound": BOUND}
    real = [c for c in cases if c["set"] == "real"]
    clean = [c for c in cases if c["set"] == "clean_real"]
    for kind in sorted({c["kind"] for c in real}) + ["all"]:
        for cls in ("mild", "moderate", "severe"):
            sel = [c for c in real if (kind == "all" or c["kind"] == kind) and c["class"] == cls]
            if sel:
                cd = card(sel, DEVICES, clean)
                cd["_amp_mm_mean"] = float(np.mean([c["tremor"]["amp_mm"] for c in sel]))
                cd["_f0_mean"] = float(np.mean([c["tremor"]["f0"] for c in sel]))
                cd["_n_cases"] = len(sel)
                cd["_n_writers"] = len({c["writer"] for c in sel})
                out["real"][f"{kind}/{cls}"] = cd
    br = [c for c in cases if c["set"] == "bridge"]
    for var in ("syn_syn", "real_syn", "real_real"):
        for kind in ("PD", "ET", "all"):
            sel = [c for c in br if c["variant"] == var and (kind == "all" or c["kind"] == kind)]
            if sel:
                out["bridge"][f"{var}/{kind}"] = card(sel, DEVICES)
    for s_ in ("clean_real", "clean_syn"):
        sel = [c for c in cases if c["set"] == s_]
        if sel:
            cd = {}
            for dev in DEVICES:
                if not any(dev in c["devices"] for c in sel):
                    continue
                cd[dev] = {"words_of_10": _boot(_per_writer(sel, dev, "", fn=_of10)),
                           "false_correction_um": _boot(_per_writer(sel, dev, "false_correction_um")),
                           "ink_err_um": _boot(_per_writer(sel, dev, "ink_err_um")),
                           "cer": _boot(_per_writer(sel, dev, "cer"))}
            out["clean"][s_] = cd
    return out
