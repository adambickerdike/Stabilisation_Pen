"""Stage 'shape' (task 4b): shape assist and the app's clean copy on real handwriting in HW1 (SIMULATION).

Tuning (rule A1): UJI tuning writers, the fast servo approximation of the nose; test: UJI test writers, HW1 closed loop
(the command enters HW1 as an external nose command computed causally from the page sensor of the nose-held run; the
hand path is imposed, so the handle barely depends on the nose).
Conditions (writer's hand): clean; dysgraphia-like warp 0.14 x-height (ASSUMPTION, the handwriting study's model);
tremor 0.3 mm and 1 mm at 8 Hz, 1 mm at 6 Hz (the project's tremor model).
"""
from __future__ import annotations

import json
import math
import pickle
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import BUILD_DIR, ensure_paths
from . import common as C
from . import data as D
from . import online as O
from . import shape as SH
from .rules import RULES, rules_sha256

ensure_paths()

CONDS = {"clean": {"warp": 0.0, "f0": 0.0, "amp": 0.0},
         "warp": {"warp": 0.14, "f0": 0.0, "amp": 0.0},
         "tremor_0.3mm_8Hz": {"warp": 0.0, "f0": 8.0, "amp": 0.3e-3},
         "tremor_1mm_8Hz": {"warp": 0.0, "f0": 8.0, "amp": 1.0e-3},
         "tremor_1mm_6Hz": {"warp": 0.0, "f0": 6.0, "amp": 1.0e-3}}
GRID = {"c_min": (0.6, 0.8, 0.9), "g": (0.25, 0.5, 0.75), "q_max_mm": (0.15, 0.3, 0.5), "d0_xh": (0.05, 0.1, 0.2)}
# REAL recorded tremor from study R's library (realdata.library.tremor: PD pen-tip tremor from UCI spirals, ET hand
# tremor from Zenodo, both CC BY 4.0), scaled to 1 mm peak; used only if the library is available when the stage runs
REAL_CONDS = {"real_PD_tremor_1mm": {"warp": 0.0, "real": "PD", "amp": 1.0e-3},
              "real_ET_tremor_1mm": {"warp": 0.0, "real": "ET", "amp": 1.0e-3}}


def real_tremor(kind: str, t: np.ndarray, amp: float, seed: int, split: str):
    try:
        from realdata import library as RL
        dr = RL.tremor("moderate", seed=seed, kind=kind, split=split, t=t, amp_mm=amp * 1e3)
        return dr.d, dr.meta
    except Exception as e:                           # the library is built by study R; skip if it is not ready
        return None, {"error": repr(e)}


def active_conds(split: str) -> Dict[str, Dict]:
    conds = dict(CONDS)
    t = np.arange(0.0, 3.0, 25e-6)
    for name, cc in REAL_CONDS.items():
        d, meta = real_tremor(cc["real"], t, cc["amp"], 0, "test" if split == "test" else "tuning")
        if d is not None:
            conds[name] = cc
    return conds


_WORDS: List[str] = []


def pick_words(n: int, seed: int) -> List[str]:
    """Common CC0 words of 3-6 letters (aiguide's Tatoeba vocabulary, count >= 30)."""
    if not _WORDS:
        from aiguide import lm
        W = lm.cached_predictor().word
        _WORDS.extend(w for w, c in zip(W.vocab, W.unigram_count) if 3 <= len(w) <= 6 and w.isalpha() and w.islower()
                      and c >= 30)
    cand = _WORDS
    rng = np.random.default_rng(seed)
    return [cand[i] for i in rng.choice(len(cand), size=n, replace=False)]


def writer_cases(letters, xh, dt, split: str, n_words: int, seed: int, pen, hand):
    """Yields the word cases one by one (each scenario is about 14 MB at the plant's 40 kHz step: never hold them all)."""
    conds = active_conds(split)
    by: Dict[str, Dict[Tuple[str, int], object]] = {}
    for L in letters:
        if O.split_of(L.writer) == split:
            by.setdefault(L.writer, {})[(L.char, L.rep)] = L
    for wi, w in enumerate(sorted(by)):
        words = pick_words(n_words, seed + 97 * wi)
        rng = np.random.default_rng(seed + wi)
        for word in words:
            reps = [int(rng.integers(1, 3)) for _ in word]
            try:
                ls = [by[w][(c, r)].strokes for c, r in zip(word, reps)]
                tp = [by[w][(c, 3 - r)].strokes for c, r in zip(word, reps)]
            except KeyError:
                continue
            f = O.XH_MM / xh[w] * 1e-3
            tpl_by_class = {}
            for ci, c in enumerate(O.LETTERS):
                for r in (1, 2):
                    if (c, r) in by[w]:
                        tpl_by_class.setdefault(ci, {})[r] = [np.asarray(s, float) * f for s in by[w][(c, r)].strokes]
            for cname, cc in conds.items():
                case = SH.build_word(ls, tp, xh[w], dt, word, w, warp_amp=cc["warp"],
                                     warp_seed=C.stable_hash(f"{w}:{word}", 1 << 30))
                if "real" in cc:
                    from handwriting import plant as PL
                    d, meta = real_tremor(cc["real"], case.scn.t, cc["amp"], C.stable_hash(f"r{w}:{word}", 1 << 20),
                                          "test" if split == "test" else "tuning")
                    if d is None:
                        continue
                    hp = PL.adapted_path(case.scn.intended, case.scn.dt, pen, hand)
                    scn = PL.with_hand_path(case.scn, hp, d)
                else:
                    scn = SH.with_tremor(case, cc["f0"], cc["amp"], C.stable_hash(f"t{w}:{word}", 1 << 20), pen, hand)
                case.scn = scn
                # the calibration sample the controller may use for any recognised class: the writer's other repetition
                # of the SAME class as the written letter where the class is right; for another class, repetition 1
                case.meta = {"reps": reps, "cond": cname,
                             "tpl_by_class": {ci: (d.get(1) or d.get(2)) for ci, d in tpl_by_class.items()}}
                yield {"writer": w, "word": word, "cond": cname, "case": case}


def judge_word(judge, strokes_per_letter, word) -> List[bool]:
    ok_idx = [i for i, s in enumerate(strokes_per_letter) if s]
    P = SH.judge_probs(judge, [strokes_per_letter[i] for i in ok_idx], xh=SH.XH_M)
    res = [False] * len(word)
    for j, i in enumerate(ok_idx):
        res[i] = bool(int(P[j].argmax()) == O.L2I[word[i]])
    return res


def evaluate_config(items, sigs, judge, cfg, tick_hz, base_read) -> Dict:
    """Servo-approximation evaluation of one assist setting on precomputed nose-held runs."""
    gain_read, n_let, harm, n_read_base = 0, 0, 0, 0
    moved_clean, share = [], []
    per_cond = {}
    for it, sg, br in zip(items, sigs, base_read):
        case = it["case"]; r0 = it["res0"]
        dev = sg["dev"][cfg["c_min"]]
        q = SH.command(dev, cfg["g"], cfg["q_max_mm"] * 1e-3, cfg["d0_xh"] * SH.XH_M, tick_hz)
        qa = SH.servo_response(q, tick_hz)
        tq = np.arange(len(qa)) / tick_hz
        qi = np.column_stack([np.interp(r0.t, tq, qa[:, 0]), np.interp(r0.t, tq, qa[:, 1])])
        ink = r0.ink + qi
        L = SH.letters_ink(r0.t, ink, r0.contact, case.windows)
        rd = judge_word(judge, L, case.word)
        c = it["cond"]
        pc = per_cond.setdefault(c, [0, 0, 0])
        pc[0] += sum(rd); pc[1] += len(rd); pc[2] += sum(br)
        n_let += len(rd)
        gain_read += sum(rd) - sum(br)
        harm += sum(1 for a, b in zip(br, rd) if a and not b)
        n_read_base += sum(br)
        m = r0.contact > 0.5
        if c == "clean":
            moved_clean.append(float(np.sqrt(np.mean(np.sum(qi[m] ** 2, 1)))) * 1e6)
        dq = np.diff(qi[m], axis=0); dh = np.diff(r0.ink[m], axis=0)
        Lq = float(np.sum(np.hypot(dq[:, 0], dq[:, 1]))); Lh = float(np.sum(np.hypot(dh[:, 0], dh[:, 1])))
        share.append(Lq / max(Lq + Lh, 1e-12))
    return {"cfg": cfg, "letters": n_let, "read_gain_per_100_letters": 100.0 * gain_read / max(n_let, 1),
            "net_harm_share": harm / max(n_read_base, 1), "clean_moved_um_rms": float(np.mean(moved_clean)) if moved_clean else 0.0,
            "clean_moved_um_worst_word": float(np.max(moved_clean)) if moved_clean else 0.0,
            "device_share_mean": float(np.mean(share)),
            "read_by_cond": {k: {"assist": v[0] / max(v[1], 1), "none": v[2] / max(v[1], 1), "n": v[1]} for k, v in per_cond.items()}}


def clean_copy_eval(items, judge, rec, cal: Dict, conf_min: float = 0.9) -> Dict:
    """The app's digital clean copy on the nose-held ink (aiprior's zero-phase Wiener smoother, read-only), and clean
    copy v2: letters the recogniser (with the writer's calibration letters, rule O4) is sure of (>= conf_min) are
    re-drawn from the writer's own calibration sample and MARKED synthetic.  Readability by the independent judge."""
    import torch
    from aiprior import cleancopy as CC
    return _cc_finish(_cc_counts(items, judge, rec, cal, conf_min))


def _cc_counts(items, judge, rec, cal: Dict, conf_min: float = 0.9, out: Optional[Dict] = None) -> Dict:
    import torch
    from aiprior import cleancopy as CC
    a, tau = float(cal.get("a", 0.5)), float(cal.get("tau", 0.1))
    out = {} if out is None else out
    for it in items:
        case = it["case"]; r0 = it["res0"]
        c = it["cond"]
        o = out.setdefault(c, {"letters": 0, "words": 0, "raw_l": 0, "cc_l": 0, "v2_l": 0, "raw_w": 0, "cc_w": 0,
                               "v2_w": 0, "synthetic_letters": 0, "synthetic_wrong": 0, "applied": 0})
        down = r0.contact > 0.5
        try:
            ink_c, info = CC.wiener_clean(r0.t, r0.ink, down)
        except Exception:
            ink_c, info = r0.ink, {"applied": False}
        o["applied"] += int(bool(info.get("applied")))
        L0 = SH.letters_ink(r0.t, r0.ink, r0.contact, case.windows)
        L1 = SH.letters_ink(r0.t, ink_c, r0.contact, case.windows)
        raw = judge_word(judge, L0, case.word)
        cc = judge_word(judge, L1, case.word)
        L2 = []
        for k, S in enumerate(L1):
            if not S:
                L2.append(S); continue
            F, _ = O.encode([s - S[0][0] for s in S], SH.XH_M)
            if len(F) < 2:
                L2.append(S); continue
            with torch.no_grad():
                lo, _ = rec(torch.from_numpy(F[None]))
                p = torch.softmax(lo[0, -1], -1).numpy()
            cal_set = {}
            for ci, tpl in case.meta["tpl_by_class"].items():
                if tpl:
                    cal_set[ci] = O.encode([np.asarray(s) - np.asarray(tpl[0][0]) for s in tpl], SH.XH_M)[0]
            wc = O.L2I[case.word[k]]
            tk = case.templates[k]
            cal_set[wc] = O.encode([np.asarray(s) - np.asarray(tk[0][0]) for s in tk], SH.XH_M)[0]
            q = O.fuse(p, O.calib_logscores(F, cal_set, tau), a)
            ci = int(np.argmax(q))
            if q[ci] >= conf_min:
                tpl = tk if ci == wc else case.meta["tpl_by_class"].get(ci)
                if tpl:
                    P = np.vstack(S); T = np.vstack(tpl)
                    off = 0.5 * (P.min(0) + P.max(0)) - 0.5 * (T.min(0) + T.max(0))
                    L2.append([np.asarray(s) + off for s in tpl])
                    o["synthetic_letters"] += 1
                    o["synthetic_wrong"] += int(ci != wc)
                    continue
            L2.append(S)
        v2 = judge_word(judge, L2, case.word)
        n = len(case.word)
        o["letters"] += n; o["words"] += 1
        o["raw_l"] += sum(raw); o["cc_l"] += sum(cc); o["v2_l"] += sum(v2)
        o["raw_w"] += int(all(raw)); o["cc_w"] += int(all(cc)); o["v2_w"] += int(all(v2))
    return out


def _cc_finish(out: Dict) -> Dict:
    res = {}
    for c, o in out.items():
        res[c] = {"letters_read_raw": o["raw_l"] / max(o["letters"], 1), "letters_read_cleancopy": o["cc_l"] / max(o["letters"], 1),
                  "letters_read_cleancopy_v2": o["v2_l"] / max(o["letters"], 1),
                  "words_read_raw": o["raw_w"] / max(o["words"], 1), "words_read_cleancopy": o["cc_w"] / max(o["words"], 1),
                  "words_read_cleancopy_v2": o["v2_w"] / max(o["words"], 1),
                  "synthetic_share": o["synthetic_letters"] / max(o["letters"], 1),
                  "synthetic_wrong_letters": o["synthetic_wrong"], "cleancopy_applied_share": o["applied"] / max(o["words"], 1),
                  "n_words": o["words"]}
    return res


def run(quick: bool, judge_minutes: float = None) -> Dict:
    import torch
    from handwriting import params as PR, plant as PL
    from .stage_online import load_model
    t_all = time.time()
    judge_minutes = judge_minutes or (0.5 if quick else 6.0)
    letters, prov = D.load_uji()
    xh = O.writer_xheights(letters)
    dt = O.sample_dt(letters, xh)
    train = O.build_items(letters, xh, "train")
    tune_items = O.build_items(letters, xh, "tune")
    test_items = O.build_items(letters, xh, "test")
    # attach sigma-lognormal fits (from the online stage) for the judge's augmentation
    p = C.cache_dir(quick) / "sl_fits.pkl"
    fits = pickle.loads(p.read_bytes()) if p.exists() else {}
    for it in train:
        it["sl"] = fits.get(it["key"])
    # ---- the judge (independent offline reader)
    mdir = BUILD_DIR / "models"; mdir.mkdir(parents=True, exist_ok=True)
    jp = mdir / f"judge{'_quick' if quick else ''}.pt"
    if jp.exists():
        judge = SH.make_judge(); judge.load_state_dict(torch.load(jp)); judge.eval()
        jinfo = json.loads(jp.with_suffix(".json").read_text())
    else:
        judge, jinfo = SH.train_judge(train, tune_items, judge_minutes, dt, log=C.log)
        torch.save(judge.state_dict(), jp)
        jp.with_suffix(".json").write_text(json.dumps(jinfo))
    jinfo["acc_tune_clean"] = SH.judge_accuracy(judge, tune_items)
    jinfo["acc_test_clean"] = SH.judge_accuracy(judge, test_items)
    C.log(f"[shape] judge: tune {jinfo['acc_tune_clean']:.3f}, test {jinfo['acc_test_clean']:.3f}")
    rec, rec_info = load_model(quick)
    pen = PR.rev_h(); hand = PR.Hand.from_config()
    out = {"judge": jinfo, "dt_ms": dt * 1e3, "rules_sha256": rules_sha256(),
           "rules": {k: RULES[k] for k in ("A1_shape", "A2_cleancopy")}, "conds": CONDS}
    # ---- tuning writers: nose-held runs and controller signals
    c_mins = GRID["c_min"]

    import itertools

    def one(it):
        case = it["case"]
        r0 = PL.run(case.scn, pen, hand, seed=C.stable_hash(case.writer + case.word, 1 << 20))
        it["res0"] = r0
        sg = SH.controller_signals(r0, case, rec, pen.tick_hz, c_mins, templates_by_class=case.meta["tpl_by_class"],
                                   seed=C.stable_hash("ps" + case.writer + case.word, 1 << 20))
        L = SH.letters_ink(r0.t, r0.ink, r0.contact, case.windows)
        return sg, judge_word(judge, L, case.word)

    def stream(split, n_words, seed):
        g = writer_cases(letters, xh, dt, split, n_words, seed, pen, hand)
        return itertools.islice(g, 5 * len(CONDS)) if quick else g

    def prepare(split, n_words, seed):
        """Tuning words: nose-held runs and controller signals; the 40 kHz scenario is dropped after its run."""
        its, sigs, base = [], [], []
        t0 = time.time()
        for it in stream(split, n_words, seed):
            sg, br = one(it)
            it["case"].scn = None
            its.append(it); sigs.append(sg); base.append(br)
        C.log(f"[shape] {split}: {len(its)} word runs prepared ({time.time() - t0:.0f} s)")
        return its, sigs, base

    tune, tsig, tbase = prepare("tune", 3 if quick else 8, 31)
    grid = [{"c_min": a, "g": b, "q_max_mm": c, "d0_xh": d} for a in GRID["c_min"] for b in GRID["g"]
            for c in GRID["q_max_mm"] for d in GRID["d0_xh"]]
    if quick:
        grid = grid[::9]
    tab = [evaluate_config(tune, tsig, judge, cfg, pen.tick_hz, tbase) for cfg in grid]
    ok = [r for r in tab if r["clean_moved_um_rms"] <= 25.0 and r["net_harm_share"] <= 0.005 and r["device_share_mean"] <= 0.25]
    best = max(ok, key=lambda r: r["read_gain_per_100_letters"]) if ok else None
    out["A1"] = {"table": tab, "chosen": best["cfg"] if best else None, "met": bool(ok)}
    C.log(f"[shape] rule A1 -> {out['A1']['chosen']} ({len(ok)} of {len(tab)} settings meet the constraints)")
    cfg = best["cfg"] if best else {"c_min": 0.9, "g": 0.25, "q_max_mm": 0.15, "d0_xh": 0.2}
    # ---- rule A2: the app's clean copy v2 on the tuning writers
    cal = (C.load("online_cal", quick) or {}).get("O4", {})
    cc_tune = clean_copy_eval(tune, judge, rec, cal)
    trem = [c for c in cc_tune if c.startswith("tremor")]
    gain_w = float(np.mean([cc_tune[c]["words_read_cleancopy_v2"] - cc_tune[c]["words_read_cleancopy"] for c in trem])) if trem else 0.0
    out["A2"] = {"tuning": cc_tune, "words_gain_v2": gain_w, "adopted": bool(gain_w >= 0.02)}
    C.log(f"[shape] rule A2: clean copy v2 words gain {gain_w:+.3f} on tuning writers -> adopted {out['A2']['adopted']}")
    import gc                                         # the tuning runs are no longer needed: free them (memory limit)
    del tune, tsig, tbase, tab
    gc.collect()
    # ---- test writers: HW1 closed loop
    rows = []
    samples = {}
    trace_rows = []
    cc_counts: Dict = {}
    t0 = time.time()
    n_test = 0
    for it in stream("test", 3 if quick else 10, 57):           # one word at a time (memory)
        sg, br = one(it)
        n_test += 1
        case = it["case"]; r0 = it["res0"]
        q = SH.command(sg["dev"][cfg["c_min"]], cfg["g"], cfg["q_max_mm"] * 1e-3, cfg["d0_xh"] * SH.XH_M, pen.tick_hz)
        r1 = PL.run(case.scn, pen, hand, ctl=PL.Controls(qext=q), seed=C.stable_hash(case.writer + case.word, 1 << 20))
        L1 = SH.letters_ink(r1.t, r1.ink, r1.contact, case.windows)
        rd = judge_word(judge, L1, case.word)
        n = min(len(r0.t), len(r1.t))
        m = (r0.contact[:n] > 0.5) & (r1.contact[:n] > 0.5)
        dq = r1.ink[:n] - r0.ink[:n]
        moved = float(np.sqrt(np.mean(np.sum(dq[m] ** 2, 1)))) * 1e6
        d1 = np.diff(dq[m], axis=0); d0 = np.diff(r0.ink[:n][m], axis=0)
        Lq = float(np.sum(np.hypot(d1[:, 0], d1[:, 1]))); Lh = float(np.sum(np.hypot(d0[:, 0], d0[:, 1])))
        k = np.clip(np.round(r0.t[:n] / case.scn.dt).astype(int), 0, len(case.scn.t) - 1)
        e0 = r0.ink[:n] - case.scn.intended[k]; e1 = r1.ink[:n] - case.scn.intended[k]
        row = {"writer": case.writer, "word": case.word, "cond": it["cond"], "read_none": br, "read_assist": rd,
               "moved_um": moved, "device_share": Lq / max(Lq + Lh, 1e-12),
               "ink_err_none_um": float(np.sqrt(np.mean(np.sum(e0[m] ** 2, 1)))) * 1e6,
               "ink_err_assist_um": float(np.sqrt(np.mean(np.sum(e1[m] ** 2, 1)))) * 1e6,
               "nose_max_mm": float(np.max(np.hypot(r1["qx"], r1["qy"]))) * 1e3,
               "committed": sum(1 for x in sg["commit"][cfg["c_min"]] if x >= 0),
               "recognised_right": sum(1 for x, c in zip(sg["letter"][cfg["c_min"]], case.word) if x == O.L2I[c])}
        rows.append(row)
        key = (it["cond"], case.writer)
        if case.word and len(samples) < 60 and key not in samples:
            samples[key] = {"word": case.word, "writer": case.writer, "cond": it["cond"],
                            "intended": [[np.round(s * 1e3, 3).tolist() for s in let] for let in case.written],
                            "none": [[np.round(s * 1e3, 3).tolist() for s in let] for let in SH.letters_ink(r0.t, r0.ink, r0.contact, case.windows)],
                            "assist": [[np.round(s * 1e3, 3).tolist() for s in let] for let in L1],
                            "read_none": br, "read_assist": rd}
        # close tracing on the warped words (nearest-point full guidance toward the same templates), for task 4a
        if it["cond"] == "warp":
            tr = trace_track(case, pen)
            r2 = PL.run(case.scn, pen, hand, ctl=PL.Controls(tmpl=tr[0], tmpl_down=tr[1], g_guide=1.0, stroke_match=True,
                                                            capture=10e-3, drop_d=1.0),
                        seed=C.stable_hash(case.writer + case.word, 1 << 20))
            L2 = SH.letters_ink(r2.t, r2.ink, r2.contact, case.windows)
            trace_rows.append({"writer": case.writer, "word": case.word, "read_none": br,
                               "read_trace": judge_word(judge, L2, case.word)})
        _cc_counts([it], judge, rec, cal, out=cc_counts)          # the app's clean copy on the same word
        del it, case, r0, r1
    C.log(f"[shape] test: {n_test} word runs ({time.time() - t0:.0f} s)")
    agg = {}
    for c in list(CONDS) + list(REAL_CONDS):
        sel = [r for r in rows if r["cond"] == c]
        if not sel:
            continue
        nn = sum(len(r["read_none"]) for r in sel)
        agg[c] = {"letters": nn, "read_none": sum(sum(r["read_none"]) for r in sel) / nn,
                  "read_assist": sum(sum(r["read_assist"]) for r in sel) / nn,
                  "words_all_letters_read_none": float(np.mean([all(r["read_none"]) for r in sel])),
                  "words_all_letters_read_assist": float(np.mean([all(r["read_assist"]) for r in sel])),
                  "moved_um_mean": float(np.mean([r["moved_um"] for r in sel])),
                  "moved_um_worst_word": float(np.max([r["moved_um"] for r in sel])),
                  "device_share_mean": float(np.mean([r["device_share"] for r in sel])),
                  "ink_err_none_um": float(np.mean([r["ink_err_none_um"] for r in sel])),
                  "ink_err_assist_um": float(np.mean([r["ink_err_assist_um"] for r in sel])),
                  "nose_max_mm_p95": float(np.percentile([r["nose_max_mm"] for r in sel], 95)),
                  "harm_letters": sum(1 for r in sel for a, b in zip(r["read_none"], r["read_assist"]) if a and not b),
                  "helped_letters": sum(1 for r in sel for a, b in zip(r["read_none"], r["read_assist"]) if b and not a)}
    if trace_rows:
        nn = sum(len(r["read_none"]) for r in trace_rows)
        agg["warp_close_tracing"] = {"letters": nn, "read_none": sum(sum(r["read_none"]) for r in trace_rows) / nn,
                                     "read_trace": sum(sum(r["read_trace"]) for r in trace_rows) / nn}
    out["test"] = {"cfg": cfg, "aggregate": agg, "rows": rows, "n_writers": len({r["writer"] for r in rows})}
    out["test"]["clean_copy"] = _cc_finish(cc_counts)
    C.log(f"[shape] clean copy (test): {json.dumps(out['test']['clean_copy'])}")
    out["samples"] = list(samples.values())
    out["minutes"] = (time.time() - t_all) / 60
    C.save("shape", out, quick)
    C.log(f"[shape] test: {json.dumps({k: (round(v['read_none'], 3), round(v.get('read_assist', v.get('read_trace', 0)), 3)) for k, v in agg.items()})}")
    return out


def trace_track(case, pen):
    """Template track for HW1's guide mode (nearest point of the matching stroke): the writer's other sample of each
    letter placed at the written letter's first touchdown, strokes at the tick rate with pen-up gaps."""
    pts, down = [], []
    for S, T in zip(case.written, case.templates):
        o = S[0][0] - T[0][0]
        for s in T:
            s = np.asarray(s, float) + o
            seg = np.hypot(*np.diff(s, axis=0).T) if len(s) > 1 else np.zeros(0)
            L = float(seg.sum())
            n = max(2, int(L / 20e-6))
            u = np.linspace(0, 1, n); cs = np.r_[0.0, np.cumsum(seg)] / max(L, 1e-12)
            pts.append(np.column_stack([np.interp(u, cs, s[:, 0]), np.interp(u, cs, s[:, 1])])); down.append(np.ones(n))
            pts.append(s[-1:].repeat(2, 0)); down.append(np.zeros(2))
    return np.ascontiguousarray(np.vstack(pts)), np.ascontiguousarray(np.concatenate(down))
