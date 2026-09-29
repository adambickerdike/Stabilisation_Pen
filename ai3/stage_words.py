"""Word-level recognition and recognition-aware spelling (the lead's request of 2026-09-29 after the independent review,
section 10; rules W1-W4 in rules.py, written before these tests ran).

A  Recognition of words, writer-disjoint and session-disjoint, CER and WER, with and without a language model
   Recogniser: task 1's causal streaming GRU (it reads the pen path point by point and never looks ahead), one
   letter at a time.  Letters are separated at pen lifts by the demo's rule: a stroke that overlaps the current
   letter's horizontal extent (0.15 x-height margin) belongs to it, otherwise it starts a new letter.  This suits the
   print handwriting of the target users; joined-up writing needs a CTC recogniser (proposed, EXP-S17).
   Words: held-out CC0 sentences (Tatoeba test; Tatoeba validation for tuning), written with the REAL letters of one
   UJI writer from ONE session, placed left to right with gaps of N(0.25, 0.12) x-height (ASSUMPTION; a 'tight'
   N(0.08, 0.12) spacing as a sensitivity).  A letter used twice in a word reuses the same real sample.
     writer-disjoint   the GRU never saw the test writers (trained on 34 other writers)
     session-disjoint  the writer calibration (rule O4) uses the writer's letters from the OTHER session (UJI's two
                       sessions were non-consecutive: uji2.names)
     no LM             each letter's arg-max;  LM: beam search with the NG1x character model, weight beta_w (rule W1)
B  Recognition-aware spelling (the review's score)
     score(w, x) = lambda_r log P(strokes | x) + log P(w | context) + log P(x | w, writer)
   x runs over the recogniser's 3 best readings of the word, from per-letter posteriors of REAL letters of held-out
   writers (for every letter the Holbrook child wrote, a real sample of that letter by a random held-out UJI writer);
   P(x | w) and P(w | context) are task 2's checker.  Recognition errors (x is not what was written) and spelling
   errors (w is not x) are kept apart.  The combined P(misspelled) is calibrated by temperature scaling on the tuning
   children (Guo et al. 2017); the pen abstains below theta_c and shows a suggestion only when its calibrated
   probability >= p_s (rules W2, W3).  Names (capitalised inside a sentence) are never flagged.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import common as C
from . import data as D
from . import online as O
from . import spell as SP
from . import stage_spell as SS
from .rules import RULES_V2, rules_v2_sha256

GAP = {"normal": (0.25, 0.12), "tight": (0.08, 0.12)}
SEG_MARGIN = 0.15
BETAS_W = (0.0, 0.25, 0.5, 0.75, 1.0)
LAMBDAS_R = (0.5, 0.75, 1.0, 1.5)
THETAS_C = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99)
P_S_GRID = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
NBEST = 3
PRUNE_NATS = 14.0          # readings less likely than the best by more than e^14 are dropped (no effect for lambda_r >= 0.5)


# ============================================================================================ letters and posteriors
def letter_bank(letters, xh, splits=("tune", "test")) -> Dict:
    """(writer, session, char) -> strokes in x-height units; per split, the writers."""
    bank, writers = {}, {s: set() for s in splits}
    for L in letters:
        sp = O.split_of(L.writer)
        if sp not in splits:
            continue
        bank[(L.writer, int(L.rep), L.char)] = [np.asarray(s, float) / xh[L.writer] for s in L.strokes]
        writers[sp].add(L.writer)
    return {"bank": bank, "writers": {k: sorted(v) for k, v in writers.items()}}


class Reader:
    """Per-segment posteriors of the GRU (beta = 0, no language) and of the writer-calibrated fusion (rule O4, the
    other session's letters as templates), cached by segment."""

    def __init__(self, model, bank: Dict, a: float, tau: float):
        self.m, self.bank, self.a, self.tau = model, bank, a, tau
        self.cal: Dict[Tuple[str, int], Dict[int, np.ndarray]] = {}
        for (w, s, c), st in bank.items():
            F, _ = O.encode(st, 1.0)
            self.cal.setdefault((w, s), {})[O.L2I[c]] = F
        self.cache: Dict = {}

    def post(self, strokes: Sequence[np.ndarray], writer: str, session: int, key=None) -> Tuple[np.ndarray, np.ndarray]:
        if key is not None and key in self.cache:
            return self.cache[key]
        F, _ = O.encode(list(strokes), 1.0)
        p = O.posteriors(self.m, [F])[0][-1]
        q = O.fuse(p, O.calib_logscores(F, self.cal.get((writer, 3 - session), {}), self.tau), self.a)
        out = (p, q)
        if key is not None:
            self.cache[key] = out
        return out

    def batch_samples(self, keys: List[Tuple[str, int, str]]) -> None:
        """Fill the cache for whole real samples in one GRU batch."""
        todo = [k for k in keys if ("s",) + k not in self.cache]
        if not todo:
            return
        Fs = [O.encode(self.bank[k], 1.0)[0] for k in todo]
        P = O.posteriors(self.m, Fs)
        for k, F, p in zip(todo, Fs, P):
            q = O.fuse(p[-1], O.calib_logscores(F, self.cal.get((k[0], 3 - k[1]), {}), self.tau), self.a)
            self.cache[("s",) + k] = (p[-1], q)


# ============================================================================================ A: words
def compose(word: str, writer: str, session: int, bank: Dict, rng, gap=(0.25, 0.12)):
    """The word written with the writer's real letters of one session: strokes in time order, each tagged with its
    letter index; None if a letter is missing."""
    strokes, owner = [], []
    cur = 0.0
    for i, c in enumerate(word):
        st = bank.get((writer, session, c))
        if st is None:
            return None
        allp = np.vstack(st)
        x0, x1 = float(allp[:, 0].min()), float(allp[:, 0].max())
        for s in st:
            strokes.append(s - np.array([x0 - cur, 0.0]))
            owner.append(i)
        cur += (x1 - x0) + float(rng.normal(*gap))
    return strokes, owner


def segment(strokes: Sequence[np.ndarray], margin: float = SEG_MARGIN) -> List[List[int]]:
    """The demo's rule: a stroke joins the current letter if it overlaps its horizontal extent (with a margin of
    0.15 x-height; 0.5 for a dot, a stroke shorter than 0.3 x-height, since i and j dots are often set off)."""
    segs: List[List[int]] = []
    lo = hi = None
    for i, s in enumerate(strokes):
        a, b = float(s[:, 0].min()), float(s[:, 0].max())
        mg = 0.5 if (len(s) < 2 or float(np.hypot(*np.diff(s, axis=0).T).sum()) < 0.3) else margin
        if segs and a <= hi + mg and b >= lo - mg:
            segs[-1].append(i)
            lo, hi = min(lo, a), max(hi, b)
        else:
            segs.append([i])
            lo, hi = a, b
    return segs


def edit_distance(a: str, b: str) -> int:
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(b)]


def decode(P: List[np.ndarray], charlm, ctx: str, beta: float, beam: int = 8) -> str:
    """Beam search over the letters of one word: sum of log posteriors + beta x character-model log-probabilities
    (including the space that ends the word).  beta = 0: arg-max per letter."""
    if beta <= 0 or charlm is None:
        return "".join(O.LETTERS[int(np.argmax(p))] for p in P)
    from aiguide import lm
    ids = np.array([lm.SYM.get(c, lm.SPACE_ID) for c in O.LETTERS])
    hyps = [("", 0.0)]
    for p in P:
        lp = np.log(np.maximum(p, 1e-9))
        new = []
        for h, s in hyps:
            q = charlm.dist(ctx + h)
            v = lp + beta * np.log(np.maximum(q[ids], 1e-12))
            for j in np.argsort(-v)[:beam]:
                new.append((h + O.LETTERS[j], s + float(v[j])))
        new.sort(key=lambda t: -t[1])
        hyps = new[:beam]
    best = max(hyps, key=lambda t: t[1] + beta * math.log(max(float(charlm.dist(ctx + t[0])[lm.SPACE_ID]), 1e-12)))
    return best[0]


def sentences_words(sentences: Sequence[str], n_words: int, seed: int) -> List[List[str]]:
    rng = np.random.default_rng(seed)
    out, n = [], 0
    for i in rng.permutation(len(sentences)):
        ws = [w for w in sentences[i].lower().replace("'", " ").split()]
        ws = ["".join(c for c in w if c.isalpha()) for w in ws]
        ws = [w for w in ws if w and all(c in O.LETTERS for c in w)]
        if len(ws) < 3:
            continue
        out.append(ws)
        n += len(ws)
        if n >= n_words:
            break
    return out


def word_eval(reader: Reader, bank: Dict, writers: Sequence[str], sents: List[List[str]], charlm, betas: Sequence[float],
              gap: Tuple[float, float], seed: int, max_sent_per_ws: int) -> Dict:
    """CER/WER for each (calibrated?, beta).  Every writer writes every session's share of the sentences."""
    rng = np.random.default_rng(seed)
    tallies = {(cal, b): [0, 0, 0, 0] for cal in (False, True) for b in betas}   # edits, letters, wrong words, words
    seg_stats = [0, 0]                                                          # letters, segmentation errors
    for w in writers:
        for sess in (1, 2):
            reader.batch_samples([(w, sess, c) for c in O.LETTERS if (w, sess, c) in reader.bank])
            for si in rng.choice(len(sents), size=min(max_sent_per_ws, len(sents)), replace=False):
                words = sents[si]
                ctx = {(cal, b): "" for cal in (False, True) for b in betas}
                for word in words:
                    comp = compose(word, w, sess, reader.bank, rng, gap)
                    if comp is None:
                        continue
                    strokes, owner = comp
                    segs = segment(strokes)
                    good = len(segs) == len(word) and all(len({owner[i] for i in g}) == 1 and
                                                          [owner[i] for i in g][0] == k for k, g in enumerate(segs))
                    seg_stats[0] += len(word); seg_stats[1] += 0 if good else abs(len(segs) - len(word)) or 1
                    P_ind, P_cal = [], []
                    for g in segs:
                        own = {owner[i] for i in g}
                        if len(own) == 1:
                            k = own.pop()
                            n_str = len(reader.bank[(w, sess, word[k])])
                            if len(g) == n_str:
                                p, q = reader.cache[("s", w, sess, word[k])]
                                P_ind.append(p); P_cal.append(q)
                                continue
                        p, q = reader.post([strokes[i] for i in g], w, sess)
                        P_ind.append(p); P_cal.append(q)
                    for cal in (False, True):
                        PP = P_cal if cal else P_ind
                        for b in betas:
                            hyp = decode(PP, charlm, ctx[(cal, b)][-40:], b)
                            T = tallies[(cal, b)]
                            e = edit_distance(hyp, word)
                            T[0] += e; T[1] += len(word); T[2] += int(e > 0); T[3] += 1
                            ctx[(cal, b)] += hyp + " "
    out = {}
    for (cal, b), (e, n, ww, nw) in tallies.items():
        out[f"{'calibrated' if cal else 'independent'}|beta={b:g}"] = {"cer": e / max(n, 1), "wer": ww / max(nw, 1),
                                                                     "letters": n, "words": nw}
    out["segmentation_error_per_letter"] = seg_stats[1] / max(seg_stats[0], 1)
    return out


# ============================================================================================ B: spelling with recognition
def nbest(P: List[np.ndarray], k: int = NBEST) -> List[Tuple[str, float]]:
    hyps = [("", 0.0)]
    for p in P:
        lp = np.log(np.maximum(p, 1e-9))
        top = np.argsort(-lp)[:k]
        hyps = sorted([(h + O.LETTERS[j], s + float(lp[j])) for h, s in hyps for j in top], key=lambda t: -t[1])[:k]
    return hyps


def observe(word: str, pool: Dict[str, List[Tuple[np.ndarray, np.ndarray]]], rng, cal: bool) -> Optional[List[np.ndarray]]:
    """Per-letter posteriors of real samples of the written letters (a random held-out writer per letter)."""
    out = []
    for c in word:
        lst = pool.get(c)
        if not lst:
            return None
        p, q = lst[int(rng.integers(len(lst)))]
        out.append(q if cal else p)
    return out


def spell_tokens(ck, units_list: List[List[Dict]], pool, cal: bool, seed: int, p_oov: float,
                 max_units: int) -> List[Dict]:
    """For every single-token correct/error unit: the N-best readings and the checker's word-end masses per reading."""
    rng = np.random.default_rng(seed)
    toks = []
    for ui, units in enumerate(units_list):
        prev, ctx = None, ""
        for u in units[:max_units]:
            for ti, wtok in enumerate(u["written"]):
                wl = SP.clean_word(wtok)
                if not wl or any(c not in O.LETTERS for c in wl):
                    continue
                P = observe(wl, pool, rng, cal)
                if P is None:
                    continue
                cands = nbest(P)
                cands = [(x, lp) for x, lp in cands if lp >= cands[0][1] - PRUNE_NATS]   # negligible readings dropped
                literal = "".join(O.LETTERS[int(np.argmax(p))] for p in P)
                capital = bool(u["capital"] and ti == 0)
                start_prev = None if (u["sentence_start"] and ti == 0) else prev
                reads = []
                snaps = []                                   # the first reading's checker state after each letter
                for ri, (x, lp) in enumerate(cands):
                    if ri == 0:
                        st = ck.start(start_prev, ctx_text=ctx[-60:], capital=capital)
                        snaps.append((st.typed, len(st.cols), st.logp_char))
                        for c in x:
                            ck.push(st, c)
                            snaps.append((st.typed, len(st.cols), st.logp_char))
                        st0 = st
                    else:                                    # share the columns of the common prefix
                        j = next((i for i, (a, b) in enumerate(zip(x, cands[0][0])) if a != b), len(x))
                        typed, ncol, lpc = snaps[j]
                        st = ck.start(start_prev, ctx_text=ctx[-60:], capital=capital)
                        st.typed, st.cols, st.logp_char = typed, list(st0.cols[:ncol]), lpc
                        for c in x[j:]:
                            ck.push(st, c)
                    e = ck.end(st)
                    err_raw, cor_raw, oov_raw = e["masses"]
                    tot = (err_raw + cor_raw) * (1 - p_oov) + p_oov * oov_raw
                    sug = [(s, float(pw)) for s, pw in e["suggestions"]]
                    reads.append({"x": x, "lp": lp, "err": err_raw * (1 - p_oov), "cor": cor_raw * (1 - p_oov),
                                  "oov": p_oov * oov_raw, "tot": tot, "sug": sug, "in_lex": e["in_lexicon"]})
                if len(u["written"]) == 1 and u["kind"] in ("correct", "error"):
                    toks.append({"child": ui, "kind": u["kind"], "written": wl, "target": u["target"].lower(),
                                 "literal": literal, "capital": capital, "reads": reads,
                                 "in_lexicon_written": wl in ck.t.index})
                prev = literal
                ctx = (ctx + " " + literal)[-80:]
    return toks


def combine(tok: Dict, lam_r: float) -> Dict:
    """The review's score over the N-best readings: posterior of each reading, P(misspelled), intended-word ranking."""
    R = tok["reads"]
    lps = np.array([r["lp"] for r in R]) * lam_r
    tots = np.array([max(r["tot"], 1e-300) for r in R])
    lw = lps + np.log(tots)
    lw -= lw.max()
    J = np.exp(lw); J /= J.sum()
    p_err = float(sum(J[k] * R[k]["err"] / tots[k] for k in range(len(R))))
    cand: Dict[str, float] = {}
    for k, r in enumerate(R):
        cand[r["x"]] = cand.get(r["x"], 0.0) + J[k] * (r["cor"] + r["oov"]) / tots[k]
        for s, pw in r["sug"]:
            cand[s] = cand.get(s, 0.0) + J[k] * pw          # pw: the checker's P(intended = s | reading k)
    best_read = R[int(np.argmax(J))]["x"]
    ranked = sorted(cand.items(), key=lambda t: -t[1])
    sugg = [(w, p) for w, p in ranked if w != best_read][:3]
    if tok["capital"]:
        p_err = 0.0
    return {"p_err": min(max(p_err, 1e-9), 1 - 1e-9), "best_read": best_read, "p_best_read": float(J.max()),
            "sugg": sugg}


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def fit_temperature(p: Sequence[float], y: Sequence[int]) -> float:
    """Temperature scaling of a binary probability (Guo et al. 2017): minimise the NLL of sigmoid(logit(p) / T)."""
    z, y = _logit(p), np.asarray(y, float)
    best = (np.inf, 1.0)
    for T in np.exp(np.linspace(math.log(0.2), math.log(20.0), 121)):
        q = 1 / (1 + np.exp(-z / T))
        nll = -np.mean(y * np.log(np.maximum(q, 1e-12)) + (1 - y) * np.log(np.maximum(1 - q, 1e-12)))
        if nll < best[0]:
            best = (nll, float(T))
    return best[1]


def apply_T(p, T):
    return 1 / (1 + np.exp(-_logit(p) / T))


def ece(p: Sequence[float], y: Sequence[int], bins: int = 15) -> Dict:
    p, y = np.asarray(p, float), np.asarray(y, float)
    e, rows = 0.0, []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        m = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        if m.sum():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
            rows.append({"bin": [lo, hi], "n": int(m.sum()), "mean_p": float(p[m].mean()), "freq": float(y[m].mean())})
    return {"ece": float(e), "bins": rows}


def evaluate(toks: List[Dict], lam_r: float, T: float, theta: float, p_s: float, T_s: float) -> Dict:
    """Detection, false alarms, suggestions, recognition fixes, harmful edits, preservation."""
    n_err = n_cor = det = fa = 0
    s_shown = s_right = s_top3 = 0
    rec_wrong = rec_fixed = rec_broken = rec_right = 0
    oov_cor = oov_kept = 0
    auto_fix = auto_harm = 0
    for t in toks:
        c = combine(t, lam_r)
        pe = float(apply_T(c["p_err"], T))
        is_err = t["kind"] == "error"
        # recognition, kept apart from spelling
        if t["literal"] != t["written"]:
            rec_wrong += 1; rec_fixed += int(c["best_read"] == t["written"])
        else:
            rec_right += 1; rec_broken += int(c["best_read"] != t["written"])
        flagged = pe >= theta and not t["capital"]
        top = c["sugg"][0] if c["sugg"] else None
        p_top = float(apply_T(top[1], T_s)) if top else 0.0
        if is_err:
            n_err += 1
            if flagged:
                det += 1
                if top and p_top >= p_s:
                    s_shown += 1
                    s_right += int(top[0] == t["target"])
                s_top3 += int(t["target"] in [w for w, _ in c["sugg"][:3]])
        else:
            n_cor += 1
            fa += int(flagged)
            if not t["in_lexicon_written"]:
                oov_cor += 1; oov_kept += int(not flagged)
        # opt-in automatic digital correction (rule W4): replace only when both are >= 0.9 (logged, reversible)
        if pe >= 0.9 and top and p_top >= 0.9 and not t["capital"]:
            if is_err and top[0] == t["target"]:
                auto_fix += 1
            elif not is_err:
                auto_harm += 1
    return {"errors": n_err, "correct_words": n_cor, "detection_rate": det / max(n_err, 1),
            "fa_per_100_correct": 100.0 * fa / max(n_cor, 1),
            "suggestion_shown_share_of_detected": s_shown / max(det, 1),
            "suggestion_right_when_shown": s_right / max(s_shown, 1),
            "target_in_top3_of_detected": s_top3 / max(det, 1),
            "recognition": {"words_misread": rec_wrong, "misread_fixed_share": rec_fixed / max(rec_wrong, 1),
                            "words_read_right": rec_right, "right_reading_changed_share": rec_broken / max(rec_right, 1)},
            "unusual_correct_words": {"n": oov_cor, "kept_unflagged_share": oov_kept / max(oov_cor, 1)},
            "auto_mode": {"errors_fixed_per_100_errors": 100.0 * auto_fix / max(n_err, 1),
                          "correct_words_changed_per_100_correct": 100.0 * auto_harm / max(n_cor, 1)}}


def choose_W2(toks: List[Dict]) -> Dict:
    """Rule W2: for each lambda_r, T by NLL, then the lowest theta_c with <= 2 false alarms per 100 correct words; the
    lambda_r with the highest detection wins."""
    tab = {}
    best = None
    y = [int(t["kind"] == "error") for t in toks]
    for lam in LAMBDAS_R:
        pe = [combine(t, lam)["p_err"] for t in toks]
        T = fit_temperature(pe, y)
        th_ok = None
        for th in THETAS_C:
            r = evaluate(toks, lam, T, th, 1.1, 1.0)
            if r["fa_per_100_correct"] <= 2.0:
                th_ok = (th, r)
                break
        if th_ok is None:
            th_ok = (THETAS_C[-1], evaluate(toks, lam, T, THETAS_C[-1], 1.1, 1.0))
        tab[f"{lam:g}"] = {"T": T, "theta_c": th_ok[0], "detection_rate": th_ok[1]["detection_rate"],
                           "fa_per_100_correct": th_ok[1]["fa_per_100_correct"]}
        if th_ok[1]["fa_per_100_correct"] <= 2.0 and (best is None or th_ok[1]["detection_rate"] > best[3]):
            best = (lam, T, th_ok[0], th_ok[1]["detection_rate"])
    if best is None:
        k = min(tab, key=lambda q: tab[q]["fa_per_100_correct"])
        best = (float(k), tab[k]["T"], tab[k]["theta_c"], tab[k]["detection_rate"])
    return {"lambda_r": best[0], "T": best[1], "theta_c": best[2], "table": tab}


def choose_W3(toks: List[Dict], lam: float, T: float, theta: float) -> Dict:
    """Rule W3: the suggestion temperature T_s by NLL of 'the top suggestion is the intended word' over flagged
    errors and false alarms; then the lowest p_s whose shown suggestions are right >= 80 % of the time."""
    ps, ys = [], []
    for t in toks:
        c = combine(t, lam)
        if float(apply_T(c["p_err"], T)) >= theta and c["sugg"]:
            ps.append(c["sugg"][0][1]); ys.append(int(t["kind"] == "error" and c["sugg"][0][0] == t["target"]))
    T_s = fit_temperature(ps, ys) if len(ps) >= 10 else 1.0
    tab = {}
    chosen = None
    for p_s in P_S_GRID:
        r = evaluate(toks, lam, T, theta, p_s, T_s)
        tab[f"{p_s:g}"] = {"shown_share": r["suggestion_shown_share_of_detected"],
                           "right_when_shown": r["suggestion_right_when_shown"]}
        if chosen is None and r["suggestion_right_when_shown"] >= 0.8:
            chosen = p_s
    return {"T_s": T_s, "p_s": chosen if chosen is not None else P_S_GRID[-1], "table": tab, "n_fit": len(ps)}


def reliability(toks: List[Dict], lam: float, T: float) -> Dict:
    y = [int(t["kind"] == "error") for t in toks if not t["capital"]]
    raw = [combine(t, lam)["p_err"] for t in toks if not t["capital"]]
    cal = list(apply_T(raw, T))
    return {"raw": ece(raw, y), "calibrated": ece(cal, y), "n": len(y), "error_share": float(np.mean(y))}


# ============================================================================================ the stage
def run(quick: bool) -> Dict:
    from aiguide import corpus as ACO
    from . import lmx
    from .stage_online import load_model
    t0 = time.time()
    sp_cache = C.load("spell_NG1x", quick)
    cal_cache = C.load("online_cal", quick)
    if sp_cache is None or cal_cache is None:
        raise RuntimeError("words stage needs the spell and calib stages first")
    model, js = load_model(quick)
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    lb = letter_bank(letters, xh)
    a, tau = cal_cache["O4"]["a"], cal_cache["O4"]["tau"]
    reader = Reader(model, lb["bank"], a, tau)
    pred, _ = lmx.ng1x(quick)
    out = {"rules_v2_sha256": rules_v2_sha256(), "rules": {k: RULES_V2[k] for k in RULES_V2},
           "O4": {"a": a, "tau": tau}, "gap_assumption": GAP, "seg_margin_xh": SEG_MARGIN}
    # ---------------- A: words.  Rule W1 on tuning writers (Tatoeba validation), then test writers (Tatoeba test)
    spl = ACO.make_splits()
    n_w = 300 if quick else 2500
    s_val = sentences_words(list(spl.val), n_w, seed=11)
    s_test = sentences_words(list(spl.test), n_w * 2, seed=12)
    tune_w = lb["writers"]["tune"][: 2 if quick else 6]
    test_w = lb["writers"]["test"][: 3 if quick else 20]
    per = 4 if quick else 12
    tw = word_eval(reader, lb["bank"], tune_w, s_val, pred.char, BETAS_W, GAP["normal"], seed=21, max_sent_per_ws=per)
    best_b = min(BETAS_W, key=lambda b: (tw[f"independent|beta={b:g}"]["cer"], b))
    out["W1"] = {"beta_w": best_b, "table": {k: v for k, v in tw.items()}}
    C.log(f"[words] rule W1 -> beta_w {best_b} (tuning CER {tw[f'independent|beta={best_b:g}']['cer']:.3f})")
    res = {}
    for gname in ("normal", "tight"):
        r = word_eval(reader, lb["bank"], test_w, s_test, pred.char, (0.0, best_b), GAP[gname], seed=31,
                      max_sent_per_ws=per)
        res[gname] = r
        C.log(f"[words] test ({gname} spacing): " + ", ".join(f"{k} CER {v['cer']:.3f} WER {v['wer']:.3f}"
                                                              for k, v in r.items() if isinstance(v, dict)))
    out["test_words"] = res
    out["test_writers"] = len(test_w)
    # ---------------- B: spelling with recognition (Holbrook children; UJI tuning writers <-> tuning children)
    passages, _ = D.load_holbrook()
    tune_p = [p for p in passages if SS.child_split(p.child) == "tune"]
    test_p = [p for p in passages if SS.child_split(p.child) == "test"]
    units_tune = [SS.holbrook_units(p) for p in tune_p]
    units_test = [SS.holbrook_units(p) for p in test_p]
    if quick:
        units_tune, units_test = units_tune[:2], units_test[:2]
    max_units = 80 if quick else 300
    pools = {}
    for split in ("tune", "test"):
        keys = [k for k in lb["bank"] if O.split_of(k[0]) == split]
        reader.batch_samples(keys)
        pool: Dict[str, List] = {}
        for k in keys:
            pool.setdefault(k[2], []).append(reader.cache[("s",) + k])
        pools[split] = pool
    # recognition accuracy of the letters in these pools (for the record)
    out["pool_letter_accuracy"] = {s: {"independent": float(np.mean([np.argmax(p) == O.L2I[c] for c, l in pools[s].items()
                                                                       for p, q in l])),
                                       "calibrated": float(np.mean([np.argmax(q) == O.L2I[c] for c, l in pools[s].items()
                                                                    for p, q in l]))} for s in pools}
    ck, _ = SS.build_checker(pred, [pp for pp in _train_pairs()], sp_cache["alpha"])
    p_oov = sp_cache["S2"]["p_oov"]
    ck.p_oov = p_oov
    out["spelling"] = {"p_oov": p_oov, "alpha": sp_cache["alpha"], "max_units_per_child": max_units}
    for cal in (False, True):
        name = "calibrated" if cal else "independent"
        t1 = time.time()
        tk_tune = spell_tokens(ck, units_tune, pools["tune"], cal, seed=41, p_oov=p_oov, max_units=max_units)
        w2 = choose_W2(tk_tune)
        w3 = choose_W3(tk_tune, w2["lambda_r"], w2["T"], w2["theta_c"])
        tk_test = spell_tokens(ck, units_test, pools["test"], cal, seed=42, p_oov=p_oov, max_units=max_units)
        ev = evaluate(tk_test, w2["lambda_r"], w2["T"], w2["theta_c"], w3["p_s"], w3["T_s"])
        rel = reliability(tk_test, w2["lambda_r"], w2["T"])
        out["spelling"][name] = {"W2": w2, "W3": w3, "test": ev, "reliability_test": rel,
                                 "tune": evaluate(tk_tune, w2["lambda_r"], w2["T"], w2["theta_c"], w3["p_s"], w3["T_s"]),
                                 "n_tokens": {"tune": len(tk_tune), "test": len(tk_test)},
                                 "minutes": (time.time() - t1) / 60}
        C.log(f"[words] spelling with {name} recognition: W2 lambda_r {w2['lambda_r']}, T {w2['T']:.2f}, theta_c "
              f"{w2['theta_c']}; W3 p_s {w3['p_s']}; test detection {ev['detection_rate']:.3f}, "
              f"FA/100 {ev['fa_per_100_correct']:.2f}, ECE {rel['raw']['ece']:.3f} -> {rel['calibrated']['ece']:.3f}")
    out["minutes"] = (time.time() - t0) / 60
    C.save("words", out, quick)
    return out


def _train_pairs():
    pairs, _ = D.load_pairs("birkbeck")
    return [(w, s) for w, s in pairs if SS.pair_split(w) == "train"]

