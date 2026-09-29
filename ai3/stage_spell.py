"""Stage 'spell' (task 2): the spelling checker on real misspellings in real running text (CALCULATION).

Data (rules S1-S3, fixed before the test):
  channel    Birkbeck pairs whose target word has sha256 bucket >= 20 (training); < 10 tuning; 10-19 test
  Holbrook   real writing of 19 secondary-school children with every misspelling tagged (Holbrook 1964; Pedler 2007 thinks
             many of these poor spellers would be classed as dyslexic today, LIT); children split by sha256 of the name:
             bucket < 40 tuning, else test
  alpha      the checker's prior share of misspelled words = the tuning children's measured rate
Outputs per written word: P(deviation) after every letter, P(the next letter goes wrong) before every letter, P(error)
at the word end (left context) and one word later (right context), ranked suggestions.
"""
from __future__ import annotations

import math
import re
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import ensure_paths
from . import common as C
from . import data as D
from . import spell as SP
from .rules import RULES, rules_sha256

ensure_paths()

THETAS = tuple(np.round(np.r_[np.arange(0.30, 0.90, 0.05), 0.9, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999], 4))
_PUNCT_END = re.compile(r"[.!?]$")


def pair_split(target: str) -> str:
    b = C.stable_hash("ai3-spell:" + target.lower())
    return "tune" if b < 10 else "test" if b < 20 else "train"


def child_split(name: str) -> str:
    return "tune" if C.stable_hash("ai3-holbrook:" + name) < 40 else "test"


def build_checker(pred, pairs_train, alpha: float, min_count: int = 3, rec_sub=None):
    ch = SP.Channel.from_pairs(pairs_train)
    W = pred.word
    words = [w for w, c in zip(W.vocab, W.unigram_count) if c >= min_count and w and all(q in SP.A2I for q in w)]
    trie = SP.Trie(words)
    lex_ids = np.array([W.index.get(w, -1) for w in trie.words])
    ck = SP.Checker(trie, ch, W, pred.char, lex_ids, alpha=alpha, rec_sub=rec_sub)
    return ck, ch


# ------------------------------------------------------------------ Holbrook as word streams
def _clean_token(tok: str) -> Tuple[str, bool]:
    """Strip punctuation around a token; returns (word, ends_sentence)."""
    ends = bool(_PUNCT_END.search(tok))
    w = tok.strip(".,;:!?\"()[]{}*").strip("-")
    return w, ends


def holbrook_units(passage) -> List[Dict]:
    """Units in writing order: a correct word, or a tagged error span (its written tokens and target).  Case-only
    errors and unknown targets are 'skip' units (written, not scored)."""
    units = []
    start = True
    for tk in passage.tokens:
        if tk.target is None:
            w, ends = _clean_token(tk.written)
            if w and re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", w):
                units.append({"kind": "correct", "written": [w], "target": w, "sentence_start": start,
                              "capital": w[0].isupper() and not start})
            if w or ends:
                start = ends if (w or ends) else start
            continue
        wr = [x for x in (_clean_token(q)[0] for q in tk.written.split()) if x]
        tg = tk.target.strip(".,;:!?\"()")
        if not wr or tg == "?" or not re.fullmatch(r"[A-Za-z][A-Za-z' \-]*", tg) or \
                not all(re.fullmatch(r"[A-Za-z'\-]+", x) for x in wr):
            units.append({"kind": "skip", "written": wr, "target": tg, "sentence_start": start, "capital": False})
            start = False
            continue
        kind = "skip" if " ".join(wr).lower() == tg.lower() else "error"
        units.append({"kind": kind, "written": wr, "target": tg, "sentence_start": start,
                      "capital": wr[0][0].isupper() and not start})
        start = False
    return units


def run_units(ck: "SP.Checker", units: List[Dict], noise: Optional[Dict] = None, seed: int = 0) -> List[Dict]:
    """Run the checker over a stream of units, letter by letter.  noise: {'conf': (26,26) row-stochastic confusion}
    replaces each written letter by a recognised one (the checker then sees recognised letters)."""
    rng = np.random.default_rng(seed)
    out = []
    prev_word = None
    ctx = ""
    pending = None                            # (record, state) waiting for its right context
    for u in units:
        rec_u = {"kind": u["kind"], "written": u["written"], "target": u["target"], "tokens": []}
        for ti, w in enumerate(u["written"]):
            wl = SP.clean_word(w)
            if not wl:
                continue
            seen = wl
            if noise is not None:
                seen = "".join(_recognise(c, noise["conf"], rng) for c in wl)
            st = ck.start(None if (u["sentence_start"] and ti == 0) else prev_word, ctx_text=ctx[-60:],
                          capital=u["capital"] and ti == 0)
            traj = [ck.push(st, c, want_next=True) for c in seen]
            e = ck.end(st)
            tok = {"written": wl, "seen": seen, "p_dev": [o["p_dev"] for o in traj],
                   "p_next": [o.get("p_next_dev", 0.0) for o in traj], "p_err_end": e["p_err"],
                   "in_lexicon": e["in_lexicon"], "suggestions": [s for s, _ in e["suggestions"]],
                   "nonword_at": _nonword_at(ck.t, seen)}
            if pending is not None:
                prec, pst = pending
                prec["p_err_late"] = ck.end(pst, next_word=seen)["p_err"]
            pending = (tok, st)
            rec_u["tokens"].append(tok)
            prev_word = seen
            ctx = (ctx + " " + seen)[-80:]
        if u["sentence_start"]:
            pass
        out.append(rec_u)
    if pending is not None:
        pending[0]["p_err_late"] = pending[0]["p_err_end"]
    return out


def _recognise(c: str, conf: np.ndarray, rng) -> str:
    i = SP.A2I.get(c)
    if i is None or i >= 26:
        return c
    return SP.ALPH[int(rng.choice(26, p=conf[i]))]


def _nonword_at(trie, s: str) -> int:
    """First letter (1-based) at which s is no longer the start of any lexicon word; len + 1 if the whole word is a
    lexicon word or a proper prefix (then only the word end or the context can show an error)."""
    n = 0
    for i, c in enumerate(s):
        n = trie.kids[n].get(SP.A2I.get(c, -1), -1)
        if n < 0:
            return i + 1
    return len(s) + 1


# ------------------------------------------------------------------ scoring
def flag_letter(tok: Dict, theta: float, use_end: bool = True) -> Optional[int]:
    """1-based letter at which the word is flagged (len + 1 = at the word end), or None."""
    for k, p in enumerate(tok["p_dev"]):
        if p >= theta:
            return k + 1
    if use_end and tok["p_err_end"] >= theta:
        return len(tok["p_dev"]) + 1
    return None


def score(records: List[List[Dict]], theta: float, use_end: bool = True, late: Optional[float] = None) -> Dict:
    err, cor = [], []
    for recs in records:
        for u in recs:
            if u["kind"] == "error":
                err.append(u)
            elif u["kind"] == "correct":
                cor.append(u)
    fa = 0
    for u in cor:
        t = u["tokens"][0] if u["tokens"] else None
        if t is None:
            continue
        if flag_letter(t, theta, use_end) is not None or (late is not None and t.get("p_err_late", 0) >= late):
            fa += 1
    det, rel, pos, sugg1, sugg3, nsugg = 0, [], [], 0, 0, 0
    kinds = {"nonword": [0, 0], "realword": [0, 0]}
    for u in err:
        wr = " ".join(t["written"] for t in u["tokens"])
        tg = SP.clean_word(u["target"].replace(" ", "")) if " " not in u["target"] else u["target"].lower()
        first_dev = SP.first_deviation(u["target"].lower(), wr)
        offset = 0
        got = None
        for t in u["tokens"]:
            f = flag_letter(t, theta, use_end)
            if f is None and late is not None and t.get("p_err_late", 0) >= late:
                f = len(t["p_dev"]) + 2                  # one word later
            if f is not None:
                got = offset + f
                break
            offset += len(t["written"]) + 1
        nonword = any(not t["in_lexicon"] for t in u["tokens"])
        kinds["nonword" if nonword else "realword"][1] += 1
        if got is not None:
            det += 1
            kinds["nonword" if nonword else "realword"][0] += 1
            rel.append(got - first_dev)
            pos.append(got)
        if len(u["tokens"]) == 1 and " " not in u["target"] and got is not None:
            nsugg += 1
            s = u["tokens"][0]["suggestions"]
            sugg1 += int(bool(s) and s[0] == u["target"].lower())
            sugg3 += int(u["target"].lower() in s[:3])
    n_cor = len(cor)
    rel = np.array(rel)
    return {"theta": theta, "errors": len(err), "detected": det, "detection_rate": det / max(len(err), 1),
            "correct_words": n_cor, "false_alarms": fa, "fa_per_100_correct": 100.0 * fa / max(n_cor, 1),
            "flag_minus_first_wrong_letter": {"same_letter": float(np.mean(rel == 0)) if len(rel) else float("nan"),
                                              "one_later": float(np.mean(rel == 1)) if len(rel) else float("nan"),
                                              "two_or_more_later": float(np.mean(rel >= 2)) if len(rel) else float("nan"),
                                              "before": float(np.mean(rel < 0)) if len(rel) else float("nan"),
                                              "median": float(np.median(rel)) if len(rel) else float("nan")},
            "flag_letter_median": float(np.median(pos)) if pos else float("nan"),
            "nonword": {"n": kinds["nonword"][1], "detected": kinds["nonword"][0]},
            "realword": {"n": kinds["realword"][1], "detected": kinds["realword"][0]},
            "suggestion_top1": sugg1 / max(nsugg, 1), "suggestion_top3": sugg3 / max(nsugg, 1), "n_suggest_scored": nsugg}


def earliest_possible(records: List[List[Dict]]) -> Dict:
    """For every scored error: the first wrong letter, and the first letter at which the written string stops being the
    start of any lexicon word (the earliest a lexicon-only checker could flag)."""
    fd, nw, L = [], [], []
    for recs in records:
        for u in recs:
            if u["kind"] != "error" or len(u["tokens"]) != 1:
                continue
            t = u["tokens"][0]
            fd.append(SP.first_deviation(u["target"].lower(), t["written"]))
            nw.append(t["nonword_at"])
            L.append(len(t["written"]))
    fd, nw, L = map(np.array, (fd, nw, L))
    return {"n": int(len(fd)), "first_wrong_letter_median": float(np.median(fd)),
            "first_wrong_letter_share_of_word_median": float(np.median(fd / np.maximum(L, 1))),
            "error_at_word_end_share": float(np.mean(fd > L)),
            "nonword_point_median": float(np.median(nw)), "never_nonword_share": float(np.mean(nw > L)),
            "nonword_point_minus_first_wrong_median": float(np.median(nw - fd))}


def choose_theta(records, max_fa: float, prefix_only: bool = False) -> Tuple[float, Dict]:
    table = {}
    best = None
    for th in THETAS:
        s = score(records, float(th), use_end=not prefix_only)
        table[f"{th:g}"] = {k: s[k] for k in ("detection_rate", "fa_per_100_correct", "detected", "false_alarms")}
        if s["fa_per_100_correct"] <= max_fa and best is None:
            best = float(th)
    return (best if best is not None else float(THETAS[-1])), table


# ------------------------------------------------------------------ Birkbeck pairs in CC0 sentences
def pairs_in_text(pairs: List[Tuple[str, str]], sentences: List[str], n_words: int, seed: int) -> Tuple[List[Dict], Dict]:
    """Simulated writers: CC0 sentences in which every word that has held-out real misspellings is misspelled with
    probability 0.5 (one of its real misspellings, uniformly); returns units and the resulting word error rate."""
    by_t: Dict[str, List[str]] = {}
    for w, s in pairs:
        if " " in w or " " in s:
            continue
        wl, sl = SP.clean_word(w), SP.clean_word(s)
        if wl and sl and wl != sl and w.islower():
            by_t.setdefault(wl, []).append(sl)
    rng = np.random.default_rng(seed)
    units, n, n_err = [], 0, 0
    order = rng.permutation(len(sentences))
    for i in order:
        ws = [x for x in re.sub(r"[^a-z' ]", " ", sentences[i].lower()).split() if x]
        if not any(w in by_t for w in ws):
            continue
        for j, w in enumerate(ws):
            if w in by_t and rng.random() < 0.5:
                s = by_t[w][int(rng.integers(len(by_t[w])))]
                units.append({"kind": "error", "written": [s], "target": w, "sentence_start": j == 0, "capital": False})
                n_err += 1
            else:
                units.append({"kind": "correct", "written": [w], "target": w, "sentence_start": j == 0, "capital": False})
            n += 1
        if n >= n_words:
            break
    return units, {"words": n, "misspelled": n_err, "word_error_rate": n_err / max(n, 1), "targets_available": len(by_t)}


# ------------------------------------------------------------------ the stage
def run(quick: bool, pred=None, lm_name: str = "NG1x", rec_conf: Optional[Dict[str, np.ndarray]] = None) -> Dict:
    t_all = time.time()
    pairs, pv = D.load_pairs("birkbeck")
    sp = {"train": [], "tune": [], "test": []}
    for w, s in pairs:
        sp[pair_split(w)].append((w, s))
    passages, hv = D.load_holbrook()
    tune_p = [p for p in passages if child_split(p.child) == "tune"]
    test_p = [p for p in passages if child_split(p.child) == "test"]
    units_tune = [holbrook_units(p) for p in tune_p]
    units_test = [holbrook_units(p) for p in test_p]
    if quick:
        units_tune = [u[:150] for u in units_tune[:3]]
        units_test = [u[:150] for u in units_test[:3]]
    # rule S2: alpha = the tuning children's share of misspelled words
    n_e = sum(1 for us in units_tune for u in us if u["kind"] == "error")
    n_c = sum(1 for us in units_tune for u in us if u["kind"] == "correct")
    alpha = n_e / max(n_e + n_c, 1)
    ck, ch = build_checker(pred, sp["train"], alpha)
    C.log(f"[spell] channel: {ch.info['pairs_used']} training pairs, {ch.info['rules']} rules; lexicon {len(ck.t.words)} "
          f"words ({ck.t.n} trie nodes); alpha {alpha:.3f}")
    out = {"data": {"birkbeck": pv, "holbrook": hv}, "lm": lm_name, "alpha": alpha,
           "split": {k: len(v) for k, v in sp.items()},
           "children": {"tune": [p.child for p in tune_p], "test": [p.child for p in test_p]},
           "channel": ch.info, "lexicon_words": len(ck.t.words), "trie_nodes": ck.t.n,
           "rules_sha256": rules_sha256(), "rules": {k: RULES[k] for k in ("S1_channel", "S2_detect", "S3_withhold")}}
    # lexicon coverage of the children's intended words
    tg = [SP.clean_word(u["target"]) for us in units_tune + units_test for u in us if u["kind"] in ("correct", "error")
          and " " not in u["target"]]
    out["lexicon_coverage_of_intended_words"] = float(np.mean([t in ck.t.index for t in tg if t]))
    # ---- tuning children
    t0 = time.time()
    rec_tune = [run_units(ck, us) for us in units_tune]
    n_letters = sum(len(t["written"]) for recs in rec_tune for u in recs for t in u["tokens"])
    out["ms_per_letter"] = (time.time() - t0) * 1e3 / max(n_letters, 1)
    C.log(f"[spell] tuning children done ({time.time() - t0:.0f} s, {out['ms_per_letter']:.1f} ms/letter)")
    theta, tab = choose_theta(rec_tune, 2.0)
    theta_w, tab_w = choose_theta(rec_tune, 0.2, prefix_only=True)
    out["S2"] = {"theta": theta, "table": tab}
    out["S3"] = {"theta_w": theta_w, "table": tab_w}
    out["tune_score"] = score(rec_tune, theta)
    C.log(f"[spell] rule S2 -> theta {theta}; S3 -> theta_w {theta_w}; tuning {out['tune_score']['detection_rate']:.3f} "
          f"detected, {out['tune_score']['fa_per_100_correct']:.2f} FA/100")
    # ---- test children (rules fixed above)
    t0 = time.time()
    rec_test = [run_units(ck, us) for us in units_test]
    C.log(f"[spell] test children done ({time.time() - t0:.0f} s)")
    res = {"theta": theta, "theta_w": theta_w}
    res["score"] = score(rec_test, theta)
    res["score_prefix_only_withhold"] = score(rec_test, theta_w, use_end=False)
    res["score_with_right_context"] = score(rec_test, theta, late=theta)
    res["earliest_possible"] = earliest_possible(rec_test)
    res["curve"] = {f"{th:g}": {k: v for k, v in score(rec_test, float(th)).items() if k in
                                ("detection_rate", "fa_per_100_correct")} for th in THETAS}
    # per child
    res["per_child"] = {}
    for p, recs in zip(test_p, rec_test):
        s = score([recs], theta)
        n_err = s["errors"]; n_cor = s["correct_words"]
        res["per_child"][p.child] = {"error_rate": n_err / max(n_err + n_cor, 1), "detection_rate": s["detection_rate"],
                                     "fa_per_100_correct": s["fa_per_100_correct"], "errors": n_err}
    out["test"] = res
    # examples for the report (short quotations)
    ex = []
    for recs in rec_test:
        for u in recs:
            if u["kind"] == "error" and len(u["tokens"]) == 1 and len(ex) < 400:
                t = u["tokens"][0]
                ex.append({"written": t["written"], "target": u["target"], "flag": flag_letter(t, theta),
                           "first_wrong": SP.first_deviation(u["target"].lower(), t["written"]),
                           "suggestions": t["suggestions"], "p_dev": [round(x, 3) for x in t["p_dev"]],
                           "p_err_end": round(t["p_err_end"], 3)})
    out["examples"] = ex
    # ---- Birkbeck pairs in CC0 text (secondary test): tuning pairs for nothing, test pairs only
    from aiguide import corpus as ACO
    spl = ACO.make_splits()
    units_bb, info_bb = pairs_in_text(sp["test"], list(spl.test), 400 if quick else 3000, seed=5)
    rec_bb = run_units(ck, units_bb)
    out["birkbeck_in_text"] = {"info": info_bb, "score": score([rec_bb], theta),
                               "earliest_possible": earliest_possible([rec_bb])}
    C.log(f"[spell] Birkbeck-in-text: {out['birkbeck_in_text']['score']['detection_rate']:.3f} detected, "
          f"{out['birkbeck_in_text']['score']['fa_per_100_correct']:.2f} FA/100")
    # ---- recognised letters instead of written ones (noise from the task-1 recogniser's real confusions)
    out["with_recognition"] = {}
    for name, conf in (rec_conf or {}).items():
        conf = np.asarray(conf, float)
        conf = (conf + 0.02) / (conf + 0.02).sum(1, keepdims=True)
        rs = np.full((SP.NA, SP.NA), 12.0)
        rs[:26, :26] = -np.log(conf)
        for i in range(26, SP.NA):
            rs[i, i] = 0.0
        ck.rec_sub = rs
        rec_n = [run_units(ck, us, noise={"conf": conf}, seed=17) for us in units_test]
        ck.rec_sub = None
        out["with_recognition"][name] = {"letter_error_rate": float(1 - np.mean(np.diag(conf))),
                                         "score": score(rec_n, theta), "records": _slim(rec_n)}
        C.log(f"[spell] with recognition '{name}': {out['with_recognition'][name]['score']['detection_rate']:.3f} detected, "
              f"{out['with_recognition'][name]['score']['fa_per_100_correct']:.2f} FA/100")
    out["records_test"] = _slim(rec_test)
    out["records_birkbeck"] = _slim([rec_bb])
    out["minutes"] = (time.time() - t_all) / 60
    C.save(f"spell_{lm_name}", out, quick)
    return out


def _slim(records):
    """Per-token trajectories kept for the physical-cue simulation (rounded)."""
    out = []
    for recs in records:
        o = []
        for u in recs:
            o.append({"kind": u["kind"], "target": u["target"],
                      "tokens": [{"written": t["written"], "seen": t.get("seen", t["written"]),
                                  "p_dev": [round(float(x), 4) for x in t["p_dev"]],
                                  "p_next": [round(float(x), 4) for x in t["p_next"]],
                                  "p_err_end": round(float(t["p_err_end"]), 4),
                                  "p_err_late": round(float(t.get("p_err_late", t["p_err_end"])), 4),
                                  "in_lexicon": t["in_lexicon"], "suggestions": t["suggestions"][:3],
                                  "nonword_at": t["nonword_at"]} for t in u["tokens"]]})
        out.append(o)
    return out
