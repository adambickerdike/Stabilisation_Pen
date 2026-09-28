"""Task 4: guided practice (copying or dictation of a text the app knows) and spelling help (SIMULATION, model HW1).

Learners (writer-error model, ASSUMPTION magnitudes; writers.ErrorProfile):
  dysgraphia  poor letter formation (extra smooth deformation of 60 % of letters), size (15 %) and baseline (0.12
              x-height) irregularity
  dyslexia    normal letter formation; b/d and p/q reversals (35 % each), one wrong letter ('deep' -> 'deap')
The target is the copybook glyph of the correct letter in the learner's own size and slant, anchored at the learner's
first touchdown of that letter (the pen knows only relative position; rule T2 of docs/ai_guidance.md 7.3).

Guidance (Rev H; no tremor in this study):
  none           nose held at centre
  cue            vibration on a detected error only (the ink is not changed; detection statistics reported)
  nose_partial   the nose pulls toward the template, gain 0.5, within +-3 mm, capture 2 mm, dropped after 60 ms beyond 2.5 mm
  nose_full      the same with gain 1.0
  nose_nogate    gain 1.0 with no capture gate and no drop rule: what "the pen writes for you" would look like
  board_partial  the guidance board (final board file; its magnet sits on the fixed front sleeve, so it pushes the
                 handle and hand, not the nose) with the board study's partial law: no force inside a 1 mm band,
                 0.10 N/mm beyond it
  board_full     the board study's full law: 0.20 N/mm with no band plus a 0.1 N pull along the template while the pen
                 moves forward; both with 2 N s/m, cap 0.4 N, slew 8 N/s and the yield rule (4 mm for 0.3 s)
Every guidance law searches only the template stroke that matches the writer's current stroke (stroke counting at
touchdown), chosen on the same tuning writers against the nearest-point search of the M1/P1 guided core.
The hand is passive to guidance (the HAP-26 impedance; no voluntary following or resisting): an upper bound for
following, since a real learner can resist.  Authorship: device share of the ink motion against the same hand
without guidance (metrics.authorship).
"""
from __future__ import annotations

import math
import time
from typing import Dict, List

import numpy as np

from . import ensure_paths
from . import metrics as MT
from . import params as PR
from . import plant as PL
from . import writers as W

ensure_paths()
from aiguide.glyphs import GLYPH_SET  # noqa: E402
from aiguide.template import LetterTemplate, build_track  # noqa: E402

CONDITIONS = ["none", "cue", "nose_partial", "nose_full", "nose_nogate", "board_partial", "board_full"]
LABELS = {"none": "No guidance", "cue": "Vibration cue on error only", "nose_partial": "Nose guidance, partial (0.5)",
          "nose_full": "Nose guidance, full", "nose_nogate": "Nose guidance without the capture gate (the pen writes)",
          "board_partial": "Guidance board, partial (1 mm band, 0.10 N/mm)", "board_full": "Guidance board, full (0.20 N/mm + 0.1 N lead)"}
PROFILES = ("dysgraphia", "dyslexia")
VIZ = {"writer": 0, "seed": 200}
FLAG_FRAC = 0.30        # cue: a letter is flagged if misread, or if its ink is > 0.30 x-height (RMS) from the target
STROKE_MATCH = True     # guidance searches only the template stroke that matches the writer's current stroke (chosen on
                        # tuning writers 100-102, seeds 300-301: lower target error than nearest-point search at equal or
                        # better recognition; see docs/handwriting_outcomes.md section 5)


def learner(w: int, seed: int, profile: str, text: str = W.PRACTICE_SENTENCE):
    prof = W.dysgraphia_profile() if profile == "dysgraphia" else W.dyslexia_profile()
    if profile == "dyslexia":
        s = text.replace(" ", "")
        k = s.find("deep")
        prof.wrong_letters = {k + 2: "a"} if k >= 0 else {}
    plan = W.error_plan(text, prof, 10_000 * w + seed)
    wtr = W.writer(w)
    wr = wtr.write(text, dt=W.SIM_DT, seed=6000 + w, size_factors=plan["size"], glyph_override=plan["override"],
                   extra_warp=plan["warp"], baseline_offsets=plan["baseline"], err_seed=8000 + 10 * w + seed)
    targets = [c for c in text if c != " "]
    return wr, plan, targets, prof


def target_letters(wr, targets: List[str]) -> List[LetterTemplate]:
    """Copybook glyphs of the correct letters in the learner's size, width and slant, anchored at the first touchdown."""
    st = wr.style
    shear = math.tan(math.radians(st.slant_deg))
    out = []
    for k, (L, ch) in enumerate(zip(wr.letters, targets)):
        h = st.x_height_mm * 1e-3
        strokes = [np.column_stack([h * (st.width * g[:, 0] + g[:, 1] * shear), h * g[:, 1]]) for g in GLYPH_SET[ch]]
        t = LetterTemplate(ch, strokes, 1.0, "copybook", k)
        out.append(t.translate(L.polylines[0][0] - strokes[0][0]))
    return out


def run_condition(su: Dict, cond: str, hand: PR.Hand, pen: PR.Pen, brd: PR.Board) -> PL.Result:
    scn = su["scn"]
    trk = su["track"]
    ctl = PL.Controls()
    if cond.startswith("nose"):
        g = 0.5 if cond == "nose_partial" else 1.0
        ctl = PL.Controls(tmpl=trk.xy, tmpl_down=trk.pen_down.astype(float), g_guide=g, stroke_match=STROKE_MATCH)
        if cond == "nose_nogate":
            ctl.capture = 10e-3
            ctl.drop_d = 1.0
    elif cond.startswith("board"):
        ctl = PL.Controls(board=brd, board_mode="partial" if cond == "board_partial" else "full",
                          board_tmpl=trk.xy, board_tmpl_down=trk.pen_down.astype(float), stroke_match=STROKE_MATCH)
    return PL.run(scn, pen, hand, ctl=ctl, seed=su["seed"])


def setup(w: int, seed: int, profile: str, hand: PR.Hand, pen: PR.Pen) -> Dict:
    wr, plan, targets, prof = learner(w, seed, profile)
    scn0 = PL.scenario_from_written(wr, None, meta={"writer": w})
    hp = PL.adapted_path(scn0.intended, scn0.dt, pen, hand)
    scn = PL.with_hand_path(scn0, hp, None)
    tl = target_letters(wr, targets)
    st = wr.style
    trk = build_track(tl, speed=st.speed_mm_s * 1e-3, air_speed=st.air_speed_mm_s * 1e-3, dt=1.0 / pen.tick_hz)
    return {"w": w, "seed": 20_000 + 100 * w + seed, "wr": wr, "plan": plan, "targets": targets, "scn": scn, "track": trk,
            "tl": tl, "rec": MT.recognizer_for(wr), "profile": profile, "pen": pen}


def evaluate(su: Dict, r: PL.Result, r_none: PL.Result) -> Dict:
    wr = su["wr"]
    rows = MT.letter_rows(wr, r, su["rec"], targets=su["targets"], target_polys=[t.strokes for t in su["tl"]])
    s = MT.summary(rows)
    wd = MT.words(rows, W.PRACTICE_SENTENCE)
    kinds = su["plan"]["kind"]
    ok_err = [rw.get("recognised_ok", False) for rw, k in zip(rows, kinds) if k != "ok"]
    out = {"target_err_um": s.get("path_rms_um"), "target_p95_um": s.get("path_p95_um"), "dtw_um": s.get("dtw_mean_um"),
           "letters_read_ok": s.get("recognition_accuracy"), "words_read_ok_letters": wd["word_accuracy_letters"],
           "words_app": wd.get("word_accuracy_app"), "recognised": " ".join(wd["recognised"]),
           "app_words": " ".join(wd.get("corrected", [])),
           "error_letters_read_as_target": float(np.mean(ok_err)) if ok_err else None,
           "n_error_letters": int(sum(1 for k in kinds if k != "ok"))}
    out.update(MT.authorship(r, r_none))
    out["at_force_limit"] = MT.travel(r, su["pen"])["at_force_limit"]
    Fb = np.hypot(r["FBx"], r["FBy"])
    out["board_F_rms_N"] = float(np.sqrt(np.mean(Fb[r.contact > 0.5] ** 2)))
    q = np.hypot(r["qx"], r["qy"])
    out["nose_q_rms_mm"] = float(np.sqrt(np.mean(q[r.contact > 0.5] ** 2)) * 1e3)
    out["_rows"] = rows
    return out


def cue_detection(su: Dict, rows_none: List[Dict]) -> Dict:
    """The cue fires on a letter the app misreads against the target, or whose ink is far from the target."""
    h = su["wr"].style.x_height_mm * 1e3
    kinds = su["plan"]["kind"]
    flagged = [(not rw.get("recognised_ok", False)) or (rw.get("path_rms_um", 0.0) > FLAG_FRAC * h) for rw in rows_none]
    err = [k != "ok" for k in kinds]
    tp = sum(1 for f, e in zip(flagged, err) if f and e)
    fp = sum(1 for f, e in zip(flagged, err) if f and not e)
    by_kind = {}
    for kd in ("malformed", "reversal", "wrong_letter"):
        idx = [i for i, k in enumerate(kinds) if k == kd]
        if idx:
            by_kind[kd] = float(np.mean([flagged[i] for i in idx]))
    return {"flag_rate_on_errors": tp / max(sum(err), 1), "flag_rate_on_correct": fp / max(len(err) - sum(err), 1),
            "n_errors": int(sum(err)), "n_letters": len(err), "by_kind": by_kind}


def spelling(su: Dict, rows_none: List[Dict]) -> Dict:
    """App-side spelling help: compare the recognised words with the known target text (copying/dictation), and the
    lexicon correction for free writing.  The ink is never changed."""
    wd = MT.words(rows_none, W.PRACTICE_SENTENCE)
    tgt = wd["target"]
    rec = wd["recognised"]
    flagged = [i for i, (a, b) in enumerate(zip(rec, tgt)) if a != b]
    written = []
    k = 0
    for word in W.PRACTICE_SENTENCE.split(" "):
        written.append("".join(su["wr"].letters[k + j].char for j in range(len(word))))
        k += len(word)
    return {"written_letters": " ".join(written), "recognised": " ".join(rec), "target": " ".join(tgt),
            "flagged_words_known_target": [tgt[i] for i in flagged],
            "app_corrected_free_writing": " ".join(wd.get("corrected", [])),
            "free_writing_word_accuracy": wd.get("word_accuracy_app")}


def writer_job(job: Dict) -> Dict:
    t0 = time.time()
    hand = PR.Hand.from_config()
    pen = PR.rev_h()
    brd = PR.board()
    rows, viz = [], {}
    for profile in job.get("profiles", PROFILES):
        for seed in job["seeds"]:
            su = setup(job["writer"], seed, profile, hand, pen)
            res = {}
            r_none = run_condition(su, "none", hand, pen, brd)
            ev_none = evaluate(su, r_none, r_none)
            keep = job.get("viz") and seed == VIZ["seed"]
            for cond in job.get("conds", CONDITIONS):
                if cond in ("none", "cue"):
                    ev = dict(ev_none)
                    r = r_none
                else:
                    r = run_condition(su, cond, hand, pen, brd)
                    ev = evaluate(su, r, r_none)
                lrows = ev.pop("_rows")
                if cond == "cue":
                    ev.update(cue_detection(su, lrows))
                res[cond] = ev
                if keep:
                    viz.setdefault(profile, {})[cond] = MT.decimate_path(r, hz=250.0).tolist()
            sp = spelling(su, evaluate(su, r_none, r_none)["_rows"]) if profile == "dyslexia" else None
            if keep:
                viz[profile]["target"] = [[p.tolist() for p in t.strokes] for t in su["tl"]]
                viz[profile]["intended"] = MT.intended_path(su["scn"], hz=250.0).tolist()
                viz[profile]["kinds"] = su["plan"]["kind"]
                viz[profile]["x_height_mm"] = su["wr"].style.x_height_mm
            rows.append({"writer": job["writer"], "seed": seed, "profile": profile, "conds": res, "spelling": sp,
                         "kinds": su["plan"]["kind"]})
    return {"writer": job["writer"], "rows": rows, "viz": viz, "elapsed_s": time.time() - t0,
            "board": {k: v for k, v in vars(brd).items()}}


def aggregate(outs: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    keys = ["target_err_um", "target_p95_um", "dtw_um", "letters_read_ok", "words_read_ok_letters", "words_app",
            "error_letters_read_as_target", "device_share", "device_disp_rms_mm", "device_disp_max_mm", "board_F_rms_N",
            "nose_q_rms_mm", "at_force_limit", "flag_rate_on_errors", "flag_rate_on_correct"]
    out = {}
    for prof in PROFILES:
        sel = [r for r in rows if r["profile"] == prof]
        if not sel:
            continue
        out[prof] = {}
        for c in CONDITIONS:
            vals = [r["conds"][c] for r in sel if c in r["conds"]]
            if not vals:
                continue
            out[prof][c] = {k: float(np.mean([v[k] for v in vals if v.get(k) is not None])) for k in keys
                            if any(v.get(k) is not None for v in vals)}
            out[prof][c]["n"] = len(vals)
        kinds = [k for r in sel for k in r["kinds"]]
        out[prof]["error_mix"] = {k: kinds.count(k) for k in set(kinds)}
    sp = [r["spelling"] for r in rows if r.get("spelling")]
    if sp:
        out["spelling_examples"] = sp[:6]
        out["spelling_flagged_share"] = float(np.mean([len(s["flagged_words_known_target"]) > 0 for s in sp]))
    return out
