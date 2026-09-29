"""Task 3: text prediction v2, personalised to the user's own notes (CALCULATION on public-domain journals).

Base models (reused, read-only code): NG0 (aiguide, Tatoeba CC0) and NG1x (the ai2 NG1 recipe: Tatoeba + Common Voice
CC0).  Personalisation (PROPOSED DESIGN):
  cache       a unigram of the user's own words with exponential decay (half-life in words); Kuhn & De Mori 1990 (LIT)
  user bigram counts of (previous word, word) in the user's notes
  user words  every word the user has written joins the vocabulary (names, jargon)
  P(w | prev) = (1 - lc - lb[prev seen]) P_base(w | prev) + lc P_cache(w) + lb P_userbigram(w | prev)
Offered as: the next word before its first letter, or a completion after 1-2 letters (top-k list); measured online
(the model keeps learning as the user writes, never from the text still to come).
Letters saved (the keystroke-savings measure of word prediction, LIT EML-63): a writer who accepts the intended word as
soon as it is in the top-k list saves (letters + space - letters written - 1 acceptance) / (letters + space).
"""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths

ensure_paths()


def words_of(line: str) -> List[str]:
    return [w for w in line.replace(".", " ").replace(",", " ").replace(":", " ").replace("/", " ").split() if w.strip("'-")]


@dataclass
class Personal:
    """The user's model: a decaying cache, user bigram counts and the user's vocabulary (all causal).  The cache is
    indexed by its words' first one and two letters, so a suggestion never scans the whole history."""
    half_life: float = 1000.0
    cache: Dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    big: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    t: int = 0
    by1: Dict[str, set] = field(default_factory=lambda: defaultdict(set))
    by2: Dict[str, set] = field(default_factory=lambda: defaultdict(set))
    _top: List[str] = field(default_factory=list)

    def update(self, prev: Optional[str], w: str) -> None:
        self.t += 1
        if math.isfinite(self.half_life):
            g = 0.5 ** (1.0 / self.half_life)
            # lazy decay: scale the whole cache every 200 words
            if self.t % 200 == 0:
                f = g ** 200
                for k in list(self.cache):
                    self.cache[k] *= f
                    if self.cache[k] < 1e-4:
                        del self.cache[k]
                        self.by1[k[:1]].discard(k); self.by2[k[:2]].discard(k)
                self.total = sum(self.cache.values())
        if w not in self.cache:
            self.by1[w[:1]].add(w); self.by2[w[:2]].add(w)
        self.cache[w] = self.cache.get(w, 0.0) + 1.0
        self.total += 1.0
        self.big[prev or "<s>"][w] += 1

    def words_with(self, prefix: str):
        """Cache words starting with the prefix (the most frequent 80 for an empty prefix, refreshed every 50 words)."""
        if not prefix:
            if not self._top or self.t - getattr(self, "_top_t", -10**9) >= 50:
                self._top = sorted(self.cache, key=self.cache.get, reverse=True)[:80]
                self._top_t = self.t
            return self._top
        if len(prefix) == 1:
            return self.by1.get(prefix, ())
        return [w for w in self.by2.get(prefix[:2], ()) if w.startswith(prefix)]


class Predictor:
    """Next word / completion with personalisation on top of an aiguide TextPredictor (its WordKN)."""

    def __init__(self, base, lc: float = 0.0, lb: float = 0.0, half_life: float = 1000.0):
        self.base = base
        self.W = base.word
        self.lc, self.lb = lc, lb
        self.P = Personal(half_life=half_life)
        self.user_words: List[str] = []
        self.user_index: Dict[str, int] = {}

    def observe(self, prev: Optional[str], w: str) -> None:
        if self.lc > 0 or self.lb > 0:
            self.P.update(prev, w)
            if w not in self.W.index and w not in self.user_index:
                self.user_index[w] = len(self.user_words)
                self.user_words.append(w)

    def candidates(self, prev: Optional[str], prefix: str, k: int = 3) -> List[str]:
        W = self.W
        ids = W.prefix_range(prefix) if prefix else None
        pb = W.dist(prev)
        pb[0] = 0.0                                          # '</s>' is not a word to write
        if ids is not None:
            sub = pb[ids]
            names = ids
        else:
            sub = pb
            names = None
        lb_eff = self.lb if (prev or "<s>") in self.P.big and self.P.big[prev or "<s>"] else 0.0
        scale = 1.0 - self.lc - lb_eff
        scores: Dict[str, float] = {}
        # base: top candidates only (the personal terms can add any word)
        m = min(len(sub), 60)
        if m:
            top = np.argpartition(-sub, m - 1)[:m] if len(sub) > m else np.arange(len(sub))
            for j in top:
                wid = int(names[j]) if names is not None else int(j)
                scores[W.vocab[wid]] = scale * float(sub[j])
        if self.lc > 0 and self.P.total > 0:
            for w in self.P.words_with(prefix):
                c = self.P.cache.get(w, 0.0)
                base_p = scores.get(w, scale * W.prob(w, prev) if w in W.index else 0.0)
                scores[w] = base_p + self.lc * c / self.P.total
        if lb_eff > 0:
            bc = self.P.big[prev or "<s>"]
            tot = sum(bc.values())
            for w, c in bc.items():
                if w.startswith(prefix):
                    base_p = scores.get(w, scale * W.prob(w, prev) if w in W.index else 0.0)
                    scores[w] = base_p + lb_eff * c / tot
        return [w for w, _ in sorted(scores.items(), key=lambda z: -z[1])[:k]]

    def ranked_with_probs(self, prev: Optional[str], prefix: str, k: int = 3) -> List[Tuple[str, float]]:
        """Top-k with probabilities renormalised over the words starting with the prefix (for offer thresholds)."""
        W = self.W
        ids = W.prefix_range(prefix) if prefix else np.arange(1, len(W.vocab))
        pb = W.dist(prev)
        tot_base = float(pb[ids].sum()) if len(ids) else 0.0
        cands = self.candidates(prev, prefix, k=max(k, 5))
        lb_eff = self.lb if (prev or "<s>") in self.P.big and self.P.big[prev or "<s>"] else 0.0
        scale = 1.0 - self.lc - lb_eff
        if self.lc > 0 and self.P.total > 0:
            pool = self.P.cache if not prefix else self.P.words_with(prefix)
            cache_tot = sum(self.P.cache.get(w, 0.0) for w in pool) / self.P.total
        else:
            cache_tot = 0.0
        bc = self.P.big.get(prev or "<s>", Counter()) if lb_eff > 0 else Counter()
        btot = sum(bc.values())
        big_tot = sum(c for w, c in bc.items() if w.startswith(prefix)) / max(btot, 1) if btot else 0.0
        Z = scale * tot_base + self.lc * cache_tot + lb_eff * big_tot
        out = []
        for w in cands[:k]:
            p = scale * (W.prob(w, prev) if w in W.index else 0.0)
            if self.lc > 0 and self.P.total > 0:
                p += self.lc * self.P.cache.get(w, 0.0) / self.P.total
            if btot:
                p += lb_eff * bc.get(w, 0) / btot
            out.append((w, p / max(Z, 1e-300)))
        return out


def evaluate_stream(pred: Predictor, history: Sequence[str], test: Sequence[str], max_words: int,
                    offer_thresholds: Sequence[float] = (), latency_every: int = 25) -> Dict:
    """Adapt on the history lines, then score every word of the test lines in order (adapting after each word)."""
    prev = None
    for line in history:
        prev = None
        for w in words_of(line):
            pred.observe(prev, w)
            prev = w
    hits = {(j, k): 0 for j in (0, 1, 2) for k in (1, 3)}
    n = 0
    ksr = {1: [0, 0], 3: [0, 0]}                      # saved, total
    lat = []
    offers = {th: {"saved_letters": 0, "offers": 0, "accepted": 0, "total": 0} for th in offer_thresholds}
    for line in test:
        prev = None
        for w in words_of(line):
            if n >= max_words:
                break
            L = len(w)
            cl: Dict[int, List[str]] = {}

            def cands(j):
                if j not in cl:
                    t0 = time.perf_counter()
                    cl[j] = pred.candidates(prev, w[:j], k=3)
                    if n % latency_every == 0:
                        lat.append((time.perf_counter() - t0) * 1e3)
                return cl[j]
            for j in (0, 1, 2):
                if j > L:
                    continue
                c = cands(j)
                for k in (1, 3):
                    hits[(j, k)] += int(w in c[:k])
            # letters saved with a top-k list (accept as soon as the word is listed; acceptance = 1 action)
            typed = {1: None, 3: None}
            for j in range(0, L):
                c = cands(j)
                if typed[3] is None and w in c:
                    typed[3] = j
                if typed[1] is None and c and c[0] == w:
                    typed[1] = j
                if typed[1] is not None:
                    break
            for k in (1, 3):
                tot = L + 1
                ksr[k][1] += tot
                if typed[k] is not None:
                    ksr[k][0] += max(tot - typed[k] - 1, 0)
            for th in offer_thresholds:
                o = offers[th]
                o["total"] += L + 1
                for j in range(0, L):
                    r = pred.ranked_with_probs(prev, w[:j], k=1)
                    if r and r[0][1] >= th:
                        o["offers"] += 1
                        if r[0][0] == w:
                            o["accepted"] += 1
                            o["saved_letters"] += L - j
                            break
            pred.observe(prev, w)
            prev = w
            n += 1
        if n >= max_words:
            break
    out = {"n_words": n}
    for (j, k), v in hits.items():
        out[f"after{j}_top{k}"] = v / max(n, 1)
    out["letters_saved_top1"] = ksr[1][0] / max(ksr[1][1], 1)
    out["letters_saved_top3"] = ksr[3][0] / max(ksr[3][1], 1)
    out["latency_ms_median"] = float(np.median(lat)) if lat else float("nan")
    out["latency_ms_p95"] = float(np.percentile(lat, 95)) if lat else float("nan")
    out["offers"] = {f"{th:g}": o for th, o in offers.items()}
    return out


def time_saved(offer: Dict, t_letter: float, t_autowrite: float, t_accept: float, t_check: float) -> Dict:
    """CALC: seconds per 100 letters saved by 'autowrite completion on request': accepted completions are finished by
    the nose (t_autowrite per letter) instead of the hand (t_letter); every accepted offer costs t_accept, every offer
    read costs t_check.  Returns net seconds saved per 100 letters of text and the share of writing time."""
    total = max(offer["total"], 1)
    saved = offer["saved_letters"] * (t_letter - t_autowrite) - offer["accepted"] * t_accept - offer["offers"] * t_check
    base = total * t_letter
    return {"seconds_saved_per_100_letters": 100.0 * saved / total, "share_of_writing_time": saved / base}
