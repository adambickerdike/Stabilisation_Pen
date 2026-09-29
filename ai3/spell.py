"""Task 2: a spelling checker that works WHILE a word is being written (noisy channel; CALCULATION on real misspellings).

Model
  prior     word bigram Kneser-Ney (aiguide.lm.WordKN) of the larger CC0 model (Tatoeba + Common Voice, the ai2 'NG1'
            recipe); out-of-vocabulary words (names) get p_oov x the character model's spelling probability
  writer    with probability 1 - alpha the word is spelled right; with probability alpha it goes through the channel
  channel   learned from REAL misspellings (Birkbeck corpus, training target words only): Brill & Moore style
            segment rules alpha -> beta (|alpha|, |beta| <= 3, with one character of context), plus context-free
            single-letter substitution, insertion, deletion and match probabilities, all conditional on the word being
            misspelled; Viterbi over partitions
  search    the whole lexicon at once: a trie in arrays, one dynamic-programming column per written letter
            (vectorised over the trie by depth), so the cost per letter does not depend on how many words are close
Outputs per written letter (prefix p of the current word)
  P(deviation | p, context) = P(the letters so far are not the start of the intended word's spelling), i.e. 'the word
  is going wrong'; the most likely intended words; the probability that the NEXT letter goes wrong (for a warning
  before the letter).  At the word end: P(the finished word is not the intended word) and ranked suggestions.
"""
from __future__ import annotations

import bisect
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths

ensure_paths()

ALPH = "abcdefghijklmnopqrstuvwxyz'-"
A2I = {c: i for i, c in enumerate(ALPH)}
NA = len(ALPH)
BOS = NA                    # index of the start marker in insertion/substitution tables
MAXLEN = 3                  # longest segment of a rule
INF = 1e9


def clean_word(w: str) -> str:
    return "".join(c for c in w.lower() if c in A2I)


# ============================================================================================ alignment
def align(w: str, s: str) -> List[Tuple[str, str, str]]:
    """Damerau-Levenshtein alignment of target w and written s: list of (op, a, b) with op in M, S, D, I, T."""
    n, m = len(w), len(s)
    D = np.zeros((n + 1, m + 1), int)
    D[:, 0] = np.arange(n + 1); D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = 0 if w[i - 1] == s[j - 1] else 1
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + c)
            if i > 1 and j > 1 and w[i - 1] == s[j - 2] and w[i - 2] == s[j - 1] and w[i - 1] != w[i - 2]:
                D[i, j] = min(D[i, j], D[i - 2, j - 2] + 1)
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and w[i - 1] == s[j - 1] and D[i, j] == D[i - 1, j - 1]:
            ops.append(("M", w[i - 1], s[j - 1])); i -= 1; j -= 1
        elif (i > 1 and j > 1 and w[i - 1] == s[j - 2] and w[i - 2] == s[j - 1] and w[i - 1] != w[i - 2]
              and D[i, j] == D[i - 2, j - 2] + 1):
            ops.append(("T", w[i - 2:i], s[j - 2:j])); i -= 2; j -= 2
        elif i > 0 and j > 0 and D[i, j] == D[i - 1, j - 1] + 1:
            ops.append(("S", w[i - 1], s[j - 1])); i -= 1; j -= 1
        elif i > 0 and D[i, j] == D[i - 1, j] + 1:
            ops.append(("D", w[i - 1], "")); i -= 1
        else:
            ops.append(("I", "", s[j - 1])); j -= 1
    return ops[::-1]


def first_deviation(w: str, s: str) -> int:
    """1-based index of the first written letter that is not the next letter of the intended spelling; len(s) + 1
    when the written word is a proper prefix of the target (the error shows only at the word's end)."""
    for i, c in enumerate(s):
        if i >= len(w) or c != w[i]:
            return i + 1
    return len(s) + 1


# ============================================================================================ channel
@dataclass
class Channel:
    sub: np.ndarray            # (NA, NA) cost of intended c written as x (diagonal: match cost)
    dele: np.ndarray           # (NA,) cost of intended c not written
    ins: np.ndarray            # (NA + 1, NA) cost of x written after intended c (row BOS: at the start)
    rules: Dict[str, List[Tuple[str, float, bool, bool]]]   # beta -> [(alpha, cost, at_start, at_end)] multi-letter rules
    match_cost: np.ndarray     # (NA,)
    info: Dict = field(default_factory=dict)

    @classmethod
    def from_pairs(cls, pairs: Sequence[Tuple[str, str]], min_rule: int = 3) -> "Channel":
        sub = np.zeros((NA, NA)); dele = np.zeros(NA); ins = np.zeros((NA + 1, NA)); trans = Counter()
        rule_n: Counter = Counter()
        n_alpha: Counter = Counter()
        n_char = np.zeros(NA)
        edits_char = np.zeros(NA)
        used = 0
        for w, s in pairs:
            w, s = clean_word(w), clean_word(s)
            if not w or not s or w == s or len(w) > 20 or len(s) > 24:
                continue
            used += 1
            ww = "^" + w + "$"
            for L in range(1, MAXLEN + 1):
                for i in range(len(ww) - L + 1):
                    n_alpha[ww[i:i + L]] += 1
            for c in w:
                n_char[A2I[c]] += 1
            ops = align(w, s)
            # single-letter statistics
            prev = BOS
            for op, a, b in ops:
                if op == "S":
                    sub[A2I[a], A2I[b]] += 1; edits_char[A2I[a]] += 1
                elif op == "D":
                    dele[A2I[a]] += 1; edits_char[A2I[a]] += 1
                elif op == "I":
                    ins[prev, A2I[b]] += 1
                elif op == "T":
                    trans[a] += 1; edits_char[A2I[a[0]]] += 1; edits_char[A2I[a[1]]] += 1
                if op in ("M", "S", "T"):
                    prev = A2I[a[-1]]
                elif op == "D":
                    prev = A2I[a]
            # segment rules: maximal edit regions with 0/1 letter of context on each side
            k = 0
            pos_w = 0
            while k < len(ops):
                if ops[k][0] == "M":
                    pos_w += 1; k += 1
                    continue
                k0, w0 = k, pos_w
                a0, b0 = "", ""
                while k < len(ops) and ops[k][0] != "M":
                    a0 += ops[k][1]; b0 += ops[k][2]
                    pos_w += len(ops[k][1]); k += 1
                Lc = w[w0 - 1] if w0 > 0 else "^"
                Rc = w[pos_w] if pos_w < len(w) else "$"
                for al, be in ((a0, b0), (Lc + a0, (Lc if Lc != "^" else "") + b0),
                               (a0 + Rc, b0 + (Rc if Rc != "$" else "")),
                               (Lc + a0 + Rc, (Lc if Lc != "^" else "") + b0 + (Rc if Rc != "$" else ""))):
                    if 1 <= len(al) <= MAXLEN and len(be) <= MAXLEN and al.strip("^$"):
                        rule_n[(al, be)] += 1
        # costs
        m_p = np.clip(1.0 - edits_char / np.maximum(n_char, 1), 0.5, 0.999)
        match_cost = -np.log(m_p)
        subc = np.zeros((NA, NA))
        for c in range(NA):
            tot = max(n_char[c], 1.0)
            pr = (sub[c] + 0.05) / (tot + 0.05 * NA)
            subc[c] = -np.log(pr)
            subc[c, c] = match_cost[c]
        delc = -np.log((dele + 0.05) / (np.maximum(n_char, 1) + 0.05))
        tot_prev = np.r_[n_char, float(used)]
        insc = -np.log((ins + 0.02) / (tot_prev[:, None] + 0.02 * NA))
        rules: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        n_rules = 0
        for (al, be), cnt in rule_n.items():
            if cnt < min_rule:
                continue
            if len(al.strip("^$")) <= 1 and len(be) <= 1 and "^" not in al and "$" not in al:
                continue                                    # single letters: the context-free tables above
            den = n_alpha.get(al, 0)
            if den <= 0:
                continue
            p = min(cnt / den, 0.9)
            al2 = al.replace("^", "").replace("$", "")
            if not al2 or len(be) == 0 and len(al2) == 1:
                continue
            rules[be].append((al2, float(-math.log(p)), al.startswith("^"), al.endswith("$")))
            n_rules += 1
        for a, cnt in trans.items():
            den = n_alpha.get(a, 0)
            if den > 0 and cnt >= 1:
                rules[a[::-1]].append((a, float(-math.log(min(cnt / den, 0.9))), False, False))
                n_rules += 1
        info = {"pairs_used": used, "rules": n_rules, "match_prob_mean": float(np.mean(m_p[:26])),
                "top_substitutions": sorted(((ALPH[i] + ">" + ALPH[j], int(sub[i, j])) for i in range(26) for j in range(26)
                                             if i != j and sub[i, j] > 0), key=lambda z: -z[1])[:15],
                "top_rules": sorted(((f"{a}>{b}", c) for (a, b), c in rule_n.items() if len(a.strip("^$")) > 1 or len(b) > 1),
                                    key=lambda z: -z[1])[:25]}
        return cls(subc, delc, insc, dict(rules), match_cost, info)

    def word_cost(self, w: str, s: str) -> float:
        """Viterbi cost of writing s when w was intended (full words; for tests and suggestions)."""
        w, s = clean_word(w), clean_word(s)
        n, m = len(w), len(s)
        D = np.full((n + 1, m + 1), INF)
        D[0, 0] = 0.0
        for i in range(0, n + 1):
            for j in range(0, m + 1):
                if i == 0 and j == 0:
                    continue
                best = INF
                if i > 0 and j > 0:
                    best = min(best, D[i - 1, j - 1] + self.sub[A2I[w[i - 1]], A2I[s[j - 1]]])
                if i > 0:
                    best = min(best, D[i - 1, j] + self.dele[A2I[w[i - 1]]])
                if j > 0:
                    prev = A2I[w[i - 1]] if i > 0 else BOS
                    best = min(best, D[i, j - 1] + self.ins[prev, A2I[s[j - 1]]])
                for b in range(0, min(MAXLEN, j) + 1):
                    be = s[j - b:j]
                    for al, c, at_start, at_end in self.rules.get(be, ()):
                        a = len(al)
                        if a <= i and w[i - a:i] == al and (not at_start or i - a == 0) and (not at_end or i == n):
                            best = min(best, D[i - a, j - b] + c)
                D[i, j] = min(D[i, j], best)
        return float(D[n, m])


# ============================================================================================ lexicon trie
class Trie:
    """The lexicon as arrays: node parent, letter, depth; per-node lexicographic word range; words' terminal nodes."""

    def __init__(self, words: Sequence[str]):
        words = sorted(set(w for w in words if w and all(c in A2I for c in w) and len(w) <= 20))
        self.words = words
        self.index = {w: i for i, w in enumerate(words)}
        par, ch, dep = [0], [BOS], [0]
        lo, hi = [0], [len(words)]
        term = np.zeros(len(words), np.int64)
        kids: List[Dict[int, int]] = [dict()]
        for wi, w in enumerate(words):
            n = 0
            for c in w:
                ci = A2I[c]
                nxt = kids[n].get(ci)
                if nxt is None:
                    nxt = len(par)
                    kids[n][ci] = nxt
                    kids.append(dict())
                    par.append(n); ch.append(ci); dep.append(dep[n] + 1)
                    lo.append(wi); hi.append(wi + 1)
                else:
                    hi[nxt] = wi + 1
                n = nxt
            term[wi] = n
        self.parent = np.array(par, np.int64)
        self.char = np.array(ch, np.int64)
        self.depth = np.array(dep, np.int64)
        self.lo = np.array(lo, np.int64); self.hi = np.array(hi, np.int64)
        self.term = term
        self.kids = kids
        self.max_depth = int(self.depth.max())
        self.by_depth = [np.flatnonzero(self.depth == d) for d in range(self.max_depth + 1)]
        self.n = len(par)
        # ancestors at distance 1..3 and node suffix strings (for multi-letter rules)
        self.anc = [np.arange(self.n)]
        for _ in range(MAXLEN):
            self.anc.append(self.parent[self.anc[-1]])
        self._suffix_nodes: Dict[str, np.ndarray] = {}
        suf = [""] * self.n
        for d in range(1, self.max_depth + 1):
            for nd in self.by_depth[d]:
                suf[nd] = (suf[self.parent[nd]] + ALPH[self.char[nd]])[-MAXLEN:]
        self.suffix = suf
        buckets: Dict[str, List[int]] = defaultdict(list)
        for nd in range(1, self.n):
            s = suf[nd]
            for L in range(1, min(MAXLEN, len(s)) + 1):
                if self.depth[nd] >= L:
                    buckets[s[-L:]].append(nd)
        self._suffix_nodes = {k: np.array(v, np.int64) for k, v in buckets.items()}
        self.is_term = np.zeros(self.n, bool); self.is_term[term] = True

    def node_of(self, p: str) -> int:
        n = 0
        for c in p:
            n = self.kids[n].get(A2I.get(c, -1), -1)
            if n < 0:
                return -1
        return n

    def prefix_range(self, p: str) -> Tuple[int, int]:
        n = self.node_of(p)
        return (int(self.lo[n]), int(self.hi[n])) if n >= 0 else (0, 0)


class RuleIndex:
    """Multi-letter rules bound to the trie: beta -> [(alen, nodes, anc, cost)]."""

    def __init__(self, trie: Trie, ch: Channel):
        self.by_beta: Dict[str, List[Tuple[int, np.ndarray, np.ndarray, float]]] = {}
        for be, lst in ch.rules.items():
            out = []
            for al, cost, at_start, at_end in lst:
                nodes = trie._suffix_nodes.get(al)
                if nodes is None or not len(nodes):
                    continue
                if at_start:
                    nodes = nodes[trie.depth[nodes] == len(al)]
                if at_end:
                    nodes = nodes[trie.is_term[nodes]]
                if not len(nodes):
                    continue
                out.append((len(al), nodes, trie.anc[len(al)][nodes], cost))
            if out:
                self.by_beta[be] = out


def bigram_prob(W, prev: Optional[str], w: str) -> float:
    """P(w | prev) from aiguide's WordKN without building the whole distribution (O(successors of prev))."""
    wi = W.index.get(w)
    if wi is None or wi < 0:
        return 0.0
    u = W.index.get(prev if prev is not None else "<s>", None)
    if u is None or u not in W.big:
        return float(W.p_uni[wi])
    ids, disc = W.big[u]
    return float(W.big_gam[u] * W.p_uni[wi] + disc[ids == wi].sum())


# ============================================================================================ the checker
@dataclass
class WordState:
    prev: Optional[str]
    ctx_text: str
    typed: str = ""
    cols: List[np.ndarray] = field(default_factory=list)
    rec_col: Optional[np.ndarray] = None
    p_lex: Optional[np.ndarray] = None
    logp_char: float = 0.0
    capital: bool = False
    history: List[Dict] = field(default_factory=list)


class Checker:
    def __init__(self, trie: Trie, channel: Channel, word_lm, char_lm, lex_ids: np.ndarray, alpha: float = 0.12,
                 p_oov: float = 0.03, p_oov_name: float = 0.5, rec_sub: Optional[np.ndarray] = None,
                 skip_capital: bool = False):
        self.skip_capital = skip_capital  # never flag a capitalised word inside a sentence (a name)
        self.t = trie
        self.ch = channel
        self.rules = RuleIndex(trie, channel)
        self.wlm = word_lm
        self.clm = char_lm
        self.lex_ids = lex_ids            # WordKN id of each lexicon word (-1 if absent)
        self.alpha = alpha
        self.p_oov = p_oov
        self.p_oov_name = p_oov_name
        self.rec_sub = rec_sub            # (NA, NA) recognition confusion costs (None: letters known exactly)
        self._ctx_cache: Dict[Optional[str], np.ndarray] = {}
        d0 = np.full(trie.n, INF); d0[0] = 0.0
        for d in range(1, trie.max_depth + 1):
            nd = trie.by_depth[d]
            d0[nd] = d0[trie.parent[nd]] + channel.dele[trie.char[nd]]
        self.col0 = d0

    # ---------------------------------------------------------------- context
    def lex_prior(self, prev: Optional[str]) -> np.ndarray:
        key = prev
        v = self._ctx_cache.get(key)
        if v is None:
            p = self.wlm.dist(prev)
            v = np.where(self.lex_ids >= 0, p[np.maximum(self.lex_ids, 0)], 0.0)
            v = v / max(v.sum(), 1e-300)
            if len(self._ctx_cache) > 2000:
                self._ctx_cache.clear()
            self._ctx_cache[key] = v
        return v

    def start(self, prev: Optional[str], ctx_text: str = "", capital: bool = False) -> WordState:
        st = WordState(prev=prev, ctx_text=ctx_text, capital=capital)
        st.cols = [self.col0]
        st.p_lex = self.lex_prior(prev)
        if self.rec_sub is not None:
            st.rec_col = np.full(self.t.n, INF); st.rec_col[0] = 0.0
        return st

    # ---------------------------------------------------------------- one written letter
    def _column(self, st: WordState, x: int) -> np.ndarray:
        t, ch = self.t, self.ch
        Dp = st.cols[-1]
        Dk = np.full(t.n, INF)
        Dk[0] = Dp[0] + ch.ins[BOS, x]
        for d in range(1, t.max_depth + 1):
            nd = t.by_depth[d]
            par = t.parent[nd]
            c = t.char[nd]
            v = Dp[par] + ch.sub[c, x]
            np.minimum(v, Dp[nd] + ch.ins[c, x], out=v)
            np.minimum(v, Dk[par] + ch.dele[c], out=v)
            Dk[nd] = v
        k = len(st.typed)
        for b in range(1, min(MAXLEN, k) + 1):
            be = st.typed[k - b:k]
            for alen, nodes, anc, cost in self.rules.by_beta.get(be, ()):
                src = st.cols[k - b]
                Dk[nodes] = np.minimum(Dk[nodes], src[anc] + cost)
        for d in range(1, t.max_depth + 1):          # deletions after a multi-letter rule
            nd = t.by_depth[d]
            Dk[nd] = np.minimum(Dk[nd], Dk[t.parent[nd]] + ch.dele[t.char[nd]])
        return Dk

    def _best_on_path(self, Dk: np.ndarray) -> np.ndarray:
        t = self.t
        B = Dk.copy()
        for d in range(1, t.max_depth + 1):
            nd = t.by_depth[d]
            B[nd] = np.minimum(B[nd], B[t.parent[nd]])
        return B

    def _char_logp(self, text: str, c: str) -> float:
        from aiguide import lm
        p = self.clm.dist(text)
        return float(np.log(max(p[lm.SYM.get(c, lm.SPACE_ID)], 1e-12)))

    def push(self, st: WordState, c: str, want_next: bool = False) -> Dict:
        """Add one written (or recognised) letter; returns P(deviation) and the leading intended words."""
        c = c.lower()
        x = A2I.get(c)
        if x is None:
            return {"p_dev": float("nan")}
        st.typed += c
        k = len(st.typed)
        Dk = self._column(st, x)
        st.cols.append(Dk)
        st.logp_char += self._char_logp(st.ctx_text + st.typed[:-1], c)
        t = self.t
        B = self._best_on_path(Dk)
        best_w = B[t.term]
        P = st.p_lex
        a = self.alpha
        lo, hi = t.prefix_range(st.typed)
        Mp = float(sum(self.ch.match_cost[A2I[q]] for q in st.typed))
        if self.rec_sub is not None:
            # correct spelling, letters possibly misrecognised: substitutions only, at depth k
            rc = np.full(t.n, INF)
            nd = t.by_depth[k] if k <= t.max_depth else np.zeros(0, np.int64)
            rc[nd] = st.rec_col[t.parent[nd]] + self.rec_sub[t.char[nd], x]
            st.rec_col = rc
            Brc = self._best_on_path(rc)
            rec_w = Brc[t.term]
            wmask = np.ones(len(P), bool); wmask[lo:hi] = False
            nodev = float(np.sum(P * np.exp(-rec_w)) * (1 - a))
            nodev += float(np.sum(P[lo:hi]) * a * math.exp(-Mp))
            dev_terms = P * np.exp(-best_w) * a
            dev_terms[lo:hi] = 0.0
        else:
            nodev = float(np.sum(P[lo:hi]) * ((1 - a) + a * math.exp(-Mp)))
            dev_terms = P * np.exp(-best_w) * a
            dev_terms[lo:hi] = 0.0
        dev = float(dev_terms.sum())
        poov = self.p_oov_name if st.capital else self.p_oov
        oov_raw = (1 - a) * math.exp(st.logp_char)
        # masses without the out-of-vocabulary prior, so the prior can be re-weighted afterwards (rule S2)
        masses = (dev, nodev, oov_raw)
        oov = poov * oov_raw
        # lexicon mass is (1 - poov) of the prior
        dev *= (1 - poov); nodev *= (1 - poov)
        tot = dev + nodev + oov
        out = {"k": k, "p_dev": dev / max(tot, 1e-300), "in_lexicon_prefix": hi > lo, "masses": masses}
        if st.capital and self.skip_capital:
            out["p_dev"] = 0.0                       # a capitalised word inside a sentence is taken as a name
        top = np.argsort(-dev_terms)[:3]
        out["intended_top"] = [(t.words[i], float(dev_terms[i] / max(tot, 1e-300))) for i in top if dev_terms[i] > 0]
        # spelling-tolerant completion: the most likely intended words, whether or not the letters so far are right
        allw = dev_terms.copy()
        if hi > lo:
            allw[lo:hi] = P[lo:hi] * ((1 - a) + a * math.exp(-Mp))
        top = np.argpartition(-allw, 3)[:3] if len(allw) > 3 else np.arange(len(allw))
        top = top[np.argsort(-allw[top])]
        out["complete_top"] = [t.words[i] for i in top if allw[i] > 0]
        if want_next:
            out["p_next_dev"] = self.next_letter_risk(st, lo, hi, nodev, tot)
        st.history.append(out)
        return out

    def next_letter_risk(self, st: WordState, lo: int, hi: int, nodev: float, tot: float) -> float:
        """P(the next letter deviates | no deviation so far): over intended words that continue the prefix, the
        misspelled branch's chance of an edit at the next position (1 - match probability of the next letter),
        weighted by the posterior that the word is in the misspelled branch."""
        if hi <= lo:
            return 0.0
        t = self.t
        n = t.node_of(st.typed)
        P = st.p_lex
        cs = np.r_[0.0, np.cumsum(P)]
        mass = cs[hi] - cs[lo]
        if mass <= 0:
            return 0.0
        a = self.alpha
        Mp = float(sum(self.ch.match_cost[A2I[q]] for q in st.typed))
        post_mis = a * math.exp(-Mp) / ((1 - a) + a * math.exp(-Mp))
        risk = 0.0
        for ci, child in t.kids[n].items():
            m = cs[t.hi[child]] - cs[t.lo[child]]
            risk += m * (1.0 - math.exp(-self.ch.match_cost[ci]))
        return float(post_mis * risk / mass)

    # ---------------------------------------------------------------- word end
    def end(self, st: WordState, next_word: Optional[str] = None) -> Dict:
        """The finished word: P(it is not the intended word) and ranked suggestions."""
        t = self.t
        s = st.typed
        if not s:
            return {"p_err": 0.0, "suggestions": []}
        Dk = st.cols[-1]
        F = Dk[t.term]
        P = st.p_lex.copy()
        a = self.alpha
        p_next_oov = 1.0
        if next_word is not None:
            # right context (one word later): P(next | w) for the 20 best candidates and the written word itself
            nxt = clean_word(next_word)
            sc = P * np.exp(-F)
            ids = np.argpartition(-sc, 20)[:20] if len(sc) > 20 else np.arange(len(sc))
            f = np.array([bigram_prob(self.wlm, t.words[i], nxt) for i in ids])
            scale = np.zeros_like(P); scale[ids] = f
            wi = t.index.get(s)
            if wi is not None:
                scale[wi] = bigram_prob(self.wlm, s, nxt)
            P = P * scale
            ni = self.wlm.index.get(nxt)
            p_next_oov = float(self.wlm.p_uni[ni]) if ni is not None and ni >= 0 else 1e-5   # P(next | a name)
        err_terms = P * np.exp(-F) * a
        wi = t.index.get(s)
        Ms = float(sum(self.ch.match_cost[A2I[q]] for q in s))
        cor = 0.0
        if wi is not None:
            cor = P[wi] * ((1 - a) + a * math.exp(-Ms))
            err_terms[wi] = 0.0
        poov = self.p_oov_name if st.capital else self.p_oov
        err_raw, cor_raw = float(err_terms.sum()), cor
        err = err_raw * (1 - poov)
        cor *= (1 - poov)
        end_lp = self._char_logp(st.ctx_text + s, " ")
        oov_raw = (1 - a) * math.exp(st.logp_char + end_lp) * p_next_oov
        oov = poov * oov_raw
        tot = err + cor + oov
        top = np.argsort(-err_terms)[:3]
        p_err = err / max(tot, 1e-300)
        if st.capital and self.skip_capital:
            p_err = 0.0
        return {"p_err": p_err, "in_lexicon": wi is not None, "masses": (err_raw, cor_raw, oov_raw),
                "suggestions": [(t.words[i], float(err_terms[i] * (1 - poov) / max(tot, 1e-300))) for i in top if err_terms[i] > 0]}
