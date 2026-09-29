"""The headline comparison on REAL inputs in model HW1 (SIMULATION; handwriting/, aiprior/ and ai2/ used read-only).

Pens and controllers (the same hand, writing, tremor and sensor noise for every row of one case):
  none         ordinary 12 g pen (ASSUMPTION mass, HW1)
  revH_akf     Rev H (+-3 mm nose, results/revH/tip_params.json) + the AKF tracker re-tuned for Rev H (as built)
  revJ_gated   Rev J nose (+-6 mm, results/nose2/nose2.json 'revJ', DEC-044) + ai2's adopted gated listening tracker
  revJ_tcn     Rev J nose + ai2's causal TCN (the candidate successor; trained on synthetic writers)
  revJ_oracle  Rev J nose with perfect knowledge of the tremor (the limit of the mechanism, not a design)
Conventions as the handwriting / aiprior / ai2 studies: the writer is adapted to each pen (tremor-free ink = intended
letters) and compensates the paper drag; the nose acts while the tip is within 2 mm of the page; the trackers run
causally on the fusion sensor models of the nose-held run; the oracle previews the servo group delay.

Measures (one number per case for the plain-words table: words read):
  words read      the AI reader (ocr.py, TrOCR) reads the drawn ink line by line; words equal to the intended words
  ink error       RMS distance of in-contact ink to the intended strokes of its own letter (nearest point; delayed
                  strokes such as t-bars counted with their letter) (CALC)
  tremor band     3-15 Hz part of ink minus intended (handwriting.metrics.band_error_um)
  nose travel     share of contact time at >= 95 % of the usable travel (handwriting.metrics.travel)
  false correction  tremor-free writing: RMS ink displacement against the nose-held run (ai2 definition)

Input sets (all test split; writers and recordings split before any evaluation):
  real        real writing (BRUSH test writers, notes of about 10 words) + real tremor (PD: uci_spiral; ET: zenodo_et)
              at the data severity classes (tremorlib)
  bridge      at a fixed 1 mm peak and the real recordings' frequencies, to explain the change:
                syn_syn    synthetic writers (aiguide test writers 0-5) + synthetic tremor (stabpen TremorSpec)
                real_syn   real writing + synthetic tremor with the real recording's frequency
                real_real  real writing + real tremor
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

DEVICES = ["none", "revH_akf", "revJ_gated", "revJ_tcn", "revJ_oracle"]
LABELS = {"none": "Ordinary pen", "revH_akf": "Rev H + tracker (as built)", "revJ_gated": "Rev J + gated tracker",
          "revJ_tcn": "Rev J + learned tracker (TCN)", "revJ_oracle": "Rev J, perfect knowledge (limit)"}
SHORT = {"none": "Ordinary pen", "revH_akf": "Rev H", "revJ_gated": "Rev J", "revJ_tcn": "Rev J + AI",
         "revJ_oracle": "Rev J limit"}
HW1_DIR = CACHE_DIR / "hw1"


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


def make_scen(wr: Writer, key: str, tremor: Optional[np.ndarray], f0: float, amp: float, seed: int, s_seed: int) -> Scen:
    from aiprior import core as CO
    from fusion import estimators as ES
    pen = wr.pens[key]
    scn = wr.su.scenario(key, tremor)
    neutral = wr.su.clean[key] if tremor is None else PL.run(scn, pen, wr.hand, ctl=PL.Controls())
    st = CO.streams_for(neutral, scn, pen, wr.trk, s_seed)
    dh, info = ES.akf(st, CO.tracker_params(pen, wr.trk))
    return Scen(wr, key, f0, amp, seed, scn, neutral, st, dh, info)


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


def measures(wr: Writer, res, scn, pen, ocr: bool = True) -> Dict:
    out = {"ink_err_um": path_error_um(wr.written, res), "band_err_um": MT.band_error_um(res, scn)}
    tv = MT.travel(res, pen)
    out.update({k: tv.get(k) for k in ("at_travel_limit", "q_rms_mm", "q_max_mm", "F_rms_N") if k in tv})
    if ocr:
        w = OC.words_read(res, wr.written)
        out.update({"words_read": w["words_read"], "words_total": w["words_total"], "words_share": w["share"],
                    "read_text": " | ".join(l["read"] for l in w["lines"])})
    return out


def _seed(*key) -> int:
    return int(hashlib.sha1(":".join(map(str, key)).encode()).hexdigest()[:7], 16)


# ------------------------------------------------------------------ one case: every pen on the same inputs
def run_case(wr: Writer, tremor: Optional[np.ndarray], f0: float, amp: float, case_key: str, devices=DEVICES,
             keep: bool = False, ocr: bool = True) -> Dict:
    from ai2 import candidates as CA
    from ai2 import delayed as DL
    M = ai2_models()
    DL.OUT_EVERY = 1
    hand = wr.hand
    out, runs = {}, {}
    t0 = time.time()
    clean = tremor is None
    # ordinary pen
    if "none" in devices:
        scn = wr.su.scenario("none", tremor)
        r = PL.run(scn, wr.pens["none"], hand)
        out["none"] = measures(wr, r, scn, wr.pens["none"], ocr)
        runs["none"] = r
    # Rev H + tracker (as built)
    if "revH_akf" in devices:
        sH = make_scen(wr, "revH", tremor, f0, amp, 0, _seed(case_key, "revH"))
        r = PL.run(sH.scn, sH.pen, hand, ctl=PL.Controls(qext=np.ascontiguousarray(-sH.dh)))
        out["revH_akf"] = measures(wr, r, sH.scn, sH.pen, ocr)
        if clean:
            out["revH_akf"]["false_correction_um"] = DL.ink_timeline_error(sH, r, np.zeros(len(sH.dh)), sH.neutral)
        runs["revH_akf"] = r
    # Rev J: gated tracker, TCN, oracle
    if any(d.startswith("revJ") for d in devices):
        sJ = make_scen(wr, "revJ", tremor, f0, amp, 0, _seed(case_key, "revJ"))
        tick_t = sJ.streams.tick_t
        S = M["S"]
        cfg = DL.DelayCfg(tremor=S["tremor"], det=S["det"] or {})
        cfg.amp_lo, cfg.amp_hi = S["gated"]["amp_lo"], S["gated"]["amp_hi"]
        est = DL.estimates(sJ, cfg, lags=CA.LAGS_CL)
        zeros = np.zeros(len(tick_t))
        qs = {"revJ_gated": DL.command(est, zeros, tick_t)}
        if "revJ_tcn" in devices and M["tcn"] is not None:
            X, tk, mb = CA.arrays(sJ, M["mp"])
            cm = CA.commands(sJ, est, M["mp"], {"learned": {"tcn": M["tcn"]}}, X, tk, mb)
            qs["revJ_tcn"] = cm["learned_tcn"]
        if "revJ_oracle" in devices and not clean:
            qs["revJ_oracle"] = TR.oracle_command(sJ.neutral, wr.su.clean["revJ"], sJ.pen, sJ.n_ticks, sJ.Ts)
        for name, q in qs.items():
            if name not in devices:
                continue
            r = PL.run(sJ.scn, sJ.pen, hand, ctl=PL.Controls(qext=np.ascontiguousarray(q)))
            out[name] = measures(wr, r, sJ.scn, sJ.pen, ocr)
            if clean:
                out[name]["false_correction_um"] = DL.ink_timeline_error(sJ, r, zeros, sJ.neutral)
            runs[name] = r
        out["_gate_open_frac"] = float(np.mean(est["g"] > 0.5))
    out["_elapsed_s"] = time.time() - t0
    if keep:
        out["_runs"] = runs
    return out


# ------------------------------------------------------------------ the input sets
def _cache(path) -> Optional[Dict]:
    return json.loads(path.read_text()) if path.exists() else None


def real_writer(split: str, i: int, quick: bool) -> Writer:
    wr = RL.writing(split, seed=i, with_reader=False)
    return Writer(wr, 100_000 + int(wr.real["writer"].split("/")[1]))


def synthetic_writer(w: int) -> Writer:
    from handwriting import writers as HWW
    wr = HWW.writer(w).write(HWW.ET_SENTENCE, dt=HWW.SIM_DT, seed=2000 + w)
    return Writer(wr, w)


def plan(quick: bool) -> Dict:
    """The case list, fixed before any case runs (writers by index in the test split; tremor seeds)."""
    n_real = 2 if quick else 12
    n_syn = 2 if quick else 6
    classes = ["moderate", "severe"] if quick else ["mild", "moderate", "severe"]
    kinds = ["PD", "ET"]
    return {"real": {"writers": list(range(n_real)), "classes": classes, "kinds": kinds},
            "bridge": {"writers_real": list(range(n_real)), "writers_syn": list(range(n_syn)), "amp_mm": 1.0,
                       "kinds": kinds}}


def run(quick: bool = False, log=print, sets: Sequence[str] = ("real", "bridge", "clean")) -> Dict:
    P = plan(quick)
    base = HW1_DIR / ("quick" if quick else "full")
    base.mkdir(parents=True, exist_ok=True)
    ai2_models()
    out = {"plan": P, "cases": []}
    # --- real writing, real tremor at the data classes, plus the tremor-free ceiling and false correction
    for i in P["real"]["writers"]:
        wr = None
        cp = base / f"clean_real_w{i}.json"
        res = _cache(cp)
        if res is None and "clean" in sets:
            wr = wr or real_writer("test", i, quick)
            res = {"set": "clean_real", "writer": wr.written.real["writer"], "text": wr.written.text,
                   "devices": run_case(wr, None, 0.0, 0.0, f"clean:{i}")}
            cp.write_text(json.dumps(res, default=_jd))
            log(f"[hw1] clean real writer {i} ({res['writer']}): " + _fmt(res["devices"]))
        if res:
            out["cases"].append(res)
        for kind in P["real"]["kinds"]:
            for cls in P["real"]["classes"]:
                p = base / f"real_w{i}_{kind}_{cls}.json"
                res = _cache(p)
                if res is None and "real" in sets:
                    wr = wr or real_writer("test", i, quick)
                    dr = RL.tremor_for(wr.written, cls, seed=i, kind=kind, split="test")
                    res = {"set": "real", "writer": wr.written.real["writer"], "kind": kind, "class": cls,
                           "tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "looped")},
                           "devices": run_case(wr, dr.d, dr.meta["f0"], dr.meta["amp_mm"] * 1e-3, f"real:{i}:{kind}:{cls}")}
                    p.write_text(json.dumps(res, default=_jd))
                    log(f"[hw1] real w{i} {kind} {cls} {dr.meta['amp_mm']:.2f} mm {dr.meta['f0']:.1f} Hz: " + _fmt(res["devices"]))
                if res:
                    out["cases"].append(res)
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
                    wr = wr or real_writer("test", i, quick)
                    dr = RL.tremor_for(wr.written, "moderate", seed=1000 + i, kind=kind, split="test", amp_mm=amp)
                    if variant == "real_syn":
                        dr = RL.synthetic_like(dr, seed=i)
                    res = {"set": "bridge", "variant": variant, "writer": wr.written.real["writer"], "kind": kind,
                           "tremor": {"rid": dr.meta["rid"], "amp_mm": amp, "f0": dr.meta["f0"]},
                           "devices": run_case(wr, dr.d, dr.meta["f0"], amp * 1e-3, f"bridge:{variant}:{i}:{kind}")}
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
                   "devices": run_case(ws, None, 0.0, 0.0, f"clean_syn:{w}")}
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
                       "devices": run_case(ws, dr.d, dr.meta["f0"], amp * 1e-3, f"bridge:syn_syn:{w}:{kind}")}
                p.write_text(json.dumps(res, default=_jd))
                log(f"[hw1] bridge syn_syn aiguide {w} {kind} f0 {dr.meta['f0']:.1f}: " + _fmt(res["devices"]))
            if res:
                out["cases"].append(res)
    return out


def _fmt(dv: Dict) -> str:
    return ", ".join(f"{k} {v.get('words_read', '-')}/{v.get('words_total', '-')} {v['ink_err_um']:.0f}um"
                     for k, v in dv.items() if not k.startswith("_") and isinstance(v, dict))


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


# ------------------------------------------------------------------ aggregation
def aggregate(cases: List[Dict]) -> Dict:
    """Means per set, kind, class and device: words read (count, share), ink error, band error, travel limit."""
    def agg(sel, dev):
        v = [c["devices"][dev] for c in sel if dev in c["devices"]]
        if not v:
            return None
        e = {"n": len(v)}
        for k in ("words_read", "words_total", "words_share", "ink_err_um", "band_err_um", "at_travel_limit",
                  "false_correction_um", "q_rms_mm"):
            x = [float(a[k]) for a in v if a.get(k) is not None and np.isfinite(float(a[k]))]
            if x:
                e[k] = float(np.mean(x))
                e[k + "_sd"] = float(np.std(x))
        if "words_share" in e:
            e["words_of_10"] = 10.0 * e["words_share"]
        return e
    out: Dict = {"real": {}, "bridge": {}, "clean": {}}
    real = [c for c in cases if c["set"] == "real"]
    for kind in sorted({c["kind"] for c in real}):
        for cls in ("mild", "moderate", "severe"):
            sel = [c for c in real if c["kind"] == kind and c["class"] == cls]
            if sel:
                out["real"][f"{kind}/{cls}"] = {d: agg(sel, d) for d in DEVICES}
                out["real"][f"{kind}/{cls}"]["_amp_mm_mean"] = float(np.mean([c["tremor"]["amp_mm"] for c in sel]))
                out["real"][f"{kind}/{cls}"]["_f0_mean"] = float(np.mean([c["tremor"]["f0"] for c in sel]))
    for cls in ("mild", "moderate", "severe"):
        sel = [c for c in real if c["class"] == cls]
        if sel:
            out["real"][f"all/{cls}"] = {d: agg(sel, d) for d in DEVICES}
    br = [c for c in cases if c["set"] == "bridge"]
    for var in ("syn_syn", "real_syn", "real_real"):
        for kind in ("PD", "ET", "all"):
            sel = [c for c in br if c["variant"] == var and (kind == "all" or c["kind"] == kind)]
            if sel:
                out["bridge"][f"{var}/{kind}"] = {d: agg(sel, d) for d in DEVICES}
    for s in ("clean_real", "clean_syn"):
        sel = [c for c in cases if c["set"] == s]
        if sel:
            out["clean"][s] = {d: agg(sel, d) for d in DEVICES}
    return out
