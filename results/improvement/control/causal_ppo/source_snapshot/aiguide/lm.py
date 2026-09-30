"""Text prediction: character Kneser-Ney n-gram + word Kneser-Ney model.

CharKN
    Interpolated modified Kneser-Ney (Chen & Goodman 1999) over the glyph
    alphabet plus an end-of-sentence symbol.  n-grams are packed into int64
    codes (6 bits per symbol) and counted with numpy, so training on the
    2.7 M-character training split takes seconds and lookups are vectorised
    (``searchsorted``).  Every sentence is left-padded with EOS symbols, so the
    model learns sentence starts; padding is never a prediction target.
WordKN
    Word bigram modified Kneser-Ney with <s>/</s>, vocabulary = training word
    types.  Gives next-word distributions and prefix completions.
TextPredictor
    Next-character distribution = lambda * CharKN + (1 - lambda) * the
    distribution implied by WordKN completions of the partial word (lexicon
    constraint and word context), then temperature scaling fitted on the
    validation split (the confidence is the calibrated top-1 probability).
    ``predict_ahead`` gives the distribution of the character d positions
    ahead (d = 2 is what the template lead requires, see aiguide/README.md).

Evidence status: CALCULATION on a public-domain corpus (Tatoeba CC0).
"""
from __future__ import annotations

import bisect
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .corpus import EOS, LM_ALPHABET, words_of

BITS = 6
BASE = 1 << BITS
SYM = {c: i for i, c in enumerate(LM_ALPHABET)}
V = len(LM_ALPHABET)
EOS_ID = SYM[EOS]
SPACE_ID = SYM[" "]
assert V <= BASE


def encode(text: str) -> np.ndarray:
    return np.fromiter((SYM[c] for c in text), dtype=np.int64, count=len(text))


def _discounts(counts: np.ndarray) -> np.ndarray:
    """Modified-KN discounts D1, D2, D3+ from count-of-counts (Chen & Goodman)."""
    n = [float(np.sum(counts == k)) for k in (1, 2, 3, 4)]
    if n[0] == 0 or n[1] == 0:
        return np.array([0.5, 1.0, 1.5])
    Y = n[0] / (n[0] + 2 * n[1])
    D1 = 1 - 2 * Y * n[1] / n[0]
    D2 = 2 - 3 * Y * n[2] / n[1] if n[1] else 1.0
    D3 = 3 - 4 * Y * n[3] / n[2] if n[2] else 1.5
    return np.clip(np.array([D1, D2, D3]), 0.05, [1.0, 2.0, 3.0])


@dataclass
class _Order:
    codes: np.ndarray        # sorted n-gram codes
    cnt: np.ndarray          # KN counts (raw at the top order, continuation below)
    ctx: np.ndarray          # sorted context codes
    ctx_tot: np.ndarray
    ctx_gamma_num: np.ndarray    # D1 N1 + D2 N2 + D3 N3+
    D: np.ndarray


class CharKN:
    """Character n-gram language model with interpolated modified Kneser-Ney smoothing."""

    def __init__(self, order: int = 7):
        if not 1 <= order <= 10:
            raise ValueError("order must be 1..10 (6 bits per symbol in an int64)")
        self.order = order
        self.orders: Dict[int, _Order] = {}
        self.n_train_chars = 0

    # ---------------------------------------------------------------- training
    def fit(self, sentences: Sequence[str]) -> "CharKN":
        N = self.order
        pad = EOS * (N - 1)
        seq = "".join(pad + s + EOS for s in sentences)
        x = encode(seq)
        valid = np.ones(len(x), bool)
        pos = 0
        for s in sentences:                 # padding symbols are never targets
            valid[pos:pos + N - 1] = False
            pos += N - 1 + len(s) + 1
        self.n_train_chars = int(valid.sum())
        tgt = np.flatnonzero(valid)
        # codes of the full-order n-grams ending at each valid target
        codes = {}
        for n in range(1, N + 1):
            c = np.zeros(len(tgt), np.int64)
            for k in range(n):
                c = (c << BITS) | x[tgt - (n - 1) + k]
            codes[n] = c
        # top order: raw counts
        raw_u, raw_c = np.unique(codes[N], return_counts=True)
        kn = {N: (raw_u, raw_c.astype(np.float64))}
        # lower orders: continuation counts = number of distinct left extensions
        for n in range(N - 1, 0, -1):
            higher = np.unique(codes[n + 1])                  # distinct (n+1)-grams
            low = higher & ((1 << (BITS * n)) - 1)            # drop the first symbol
            u, c = np.unique(low, return_counts=True)
            kn[n] = (u, c.astype(np.float64))
        for n in range(1, N + 1):
            u, c = kn[n]
            D = _discounts(c)
            ctx = u >> BITS
            cu, first = np.unique(ctx, return_index=True)
            tot = np.add.reduceat(c, first)
            g = (D[0] * np.add.reduceat((c == 1).astype(np.float64), first)
                 + D[1] * np.add.reduceat((c == 2).astype(np.float64), first)
                 + D[2] * np.add.reduceat((c >= 3).astype(np.float64), first))
            self.orders[n] = _Order(u, c, cu, tot, g, D)
        return self

    # --------------------------------------------------------------- inference
    def _ctx_codes(self, ctx_ids: np.ndarray, n: int) -> np.ndarray:
        """Codes of the last n-1 symbols of each context row (rows of length order-1)."""
        c = np.zeros(ctx_ids.shape[0], np.int64)
        L = ctx_ids.shape[1]
        for k in range(L - (n - 1), L):
            c = (c << BITS) | ctx_ids[:, k]
        return c

    def dist_batch(self, ctx_ids: np.ndarray) -> np.ndarray:
        """P(. | context) for each row of ``ctx_ids`` (B, order-1) symbol ids -> (B, V)."""
        B = ctx_ids.shape[0]
        p = np.full((B, V), 1.0 / V)
        wv = np.arange(V, dtype=np.int64)
        for n in range(1, self.order + 1):
            o = self.orders[n]
            h = self._ctx_codes(ctx_ids, n) if n > 1 else np.zeros(B, np.int64)
            ci = np.searchsorted(o.ctx, h)
            ci_c = np.minimum(ci, len(o.ctx) - 1)
            seen = o.ctx[ci_c] == h
            tot = np.where(seen, o.ctx_tot[ci_c], 1.0)
            gam = np.where(seen, o.ctx_gamma_num[ci_c] / tot, 1.0)
            q = (h[:, None] << BITS) | wv[None, :]
            qi = np.searchsorted(o.codes, q.ravel())
            qi_c = np.minimum(qi, len(o.codes) - 1)
            hit = o.codes[qi_c] == q.ravel()
            cnt = np.where(hit, o.cnt[qi_c], 0.0).reshape(B, V)
            Dm = np.where(cnt >= 3, o.D[2], np.where(cnt == 2, o.D[1], np.where(cnt == 1, o.D[0], 0.0)))
            disc = np.maximum(cnt - Dm, 0.0) / tot[:, None]
            newp = disc + gam[:, None] * p
            p = np.where(seen[:, None], newp, p)
        return p / p.sum(axis=1, keepdims=True)

    def context_ids(self, text: str) -> np.ndarray:
        """Symbol ids of the last order-1 characters of ``text`` (EOS-padded sentence start)."""
        L = self.order - 1
        t = (EOS * L + text)[-L:] if L > 0 else ""
        return encode(t)

    def dist(self, text: str) -> np.ndarray:
        if self.order == 1:
            return self.dist_batch(np.zeros((1, 0), np.int64))[0]
        return self.dist_batch(self.context_ids(text)[None, :])[0]

    def contexts_for(self, sentences: Sequence[str]) -> Tuple[np.ndarray, np.ndarray]:
        """(contexts (T, order-1), targets (T,)) for every prediction position of the sentences."""
        L = self.order - 1
        ctxs, tg = [], []
        for s in sentences:
            x = encode(EOS * L + s + EOS)
            idx = np.arange(L, len(x))
            if L:
                ctxs.append(np.stack([x[idx - L + k] for k in range(L)], axis=1))
            tg.append(x[idx])
        C = np.concatenate(ctxs) if L else np.zeros((sum(len(t) for t in tg), 0), np.int64)
        return C, np.concatenate(tg)

    def logprob_sentences(self, sentences: Sequence[str], chunk: int = 40000) -> Tuple[float, int]:
        C, T = self.contexts_for(sentences)
        lp = 0.0
        for a in range(0, len(T), chunk):
            P = self.dist_batch(C[a:a + chunk])
            lp += float(np.sum(np.log(P[np.arange(len(P)), T[a:a + chunk]])))
        return lp, len(T)

    def n_params(self) -> int:
        return int(sum(len(o.codes) for o in self.orders.values()))

    def to_npz(self, path) -> None:
        arrs = {"order": np.array([self.order]), "n_train_chars": np.array([self.n_train_chars])}
        for n, o in self.orders.items():
            for k in ("codes", "cnt", "ctx", "ctx_tot", "ctx_gamma_num", "D"):
                arrs[f"o{n}_{k}"] = getattr(o, k)
        np.savez_compressed(path, **arrs)

    @classmethod
    def from_npz(cls, path) -> "CharKN":
        z = np.load(path)
        m = cls(int(z["order"][0]))
        m.n_train_chars = int(z["n_train_chars"][0])
        for n in range(1, m.order + 1):
            m.orders[n] = _Order(*(z[f"o{n}_{k}"] for k in ("codes", "cnt", "ctx", "ctx_tot", "ctx_gamma_num", "D")))
        return m


# ======================================================================= words
BOS_W, EOS_W = "<s>", "</s>"


class WordKN:
    """Word bigram language model, interpolated modified Kneser-Ney."""

    def __init__(self):
        self.vocab: List[str] = []
        self.index: Dict[str, int] = {}
        self.sorted_vocab: List[str] = []
        self.sorted_ids: np.ndarray = np.zeros(0, np.int64)
        self.p_uni: np.ndarray = np.zeros(0)
        self.big: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        self.big_tot: Dict[int, float] = {}
        self.big_gam: Dict[int, float] = {}
        self.D = np.array([0.5, 1.0, 1.5])
        self.unigram_count: np.ndarray = np.zeros(0)
        self.next_sym: np.ndarray = np.zeros((0, 0), np.int8)   # [k, word id] -> symbol after a k-letter prefix
        self._cache: Dict[Optional[str], np.ndarray] = {}

    def fit(self, sentences: Sequence[str]) -> "WordKN":
        toks = [[BOS_W] + words_of(s) + [EOS_W] for s in sentences]
        uni = Counter(w for t in toks for w in t[1:])
        self.vocab = [EOS_W] + sorted(w for w in uni if w != EOS_W)
        self.index = {w: i for i, w in enumerate(self.vocab)}
        self.index[BOS_W] = -1
        self.unigram_count = np.array([uni[w] for w in self.vocab], np.float64)
        bic = Counter((t[i], t[i + 1]) for t in toks for i in range(len(t) - 1))
        # continuation unigram: distinct left contexts per word
        cont = Counter(w for (_u, w) in bic)
        cu = np.array([cont.get(w, 0) for w in self.vocab], np.float64)
        n_cont = cu.sum()
        D1 = _discounts(cu[cu > 0])
        g1 = (D1[0] * np.sum(cu == 1) + D1[1] * np.sum(cu == 2) + D1[2] * np.sum(cu >= 3)) / n_cont
        dm = np.where(cu >= 3, D1[2], np.where(cu == 2, D1[1], np.where(cu == 1, D1[0], 0.0)))
        self.p_uni = np.maximum(cu - dm, 0) / n_cont + g1 / len(self.vocab)
        self.p_uni /= self.p_uni.sum()
        counts = np.array(list(bic.values()), np.float64)
        self.D = _discounts(counts)
        by_u: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        for (u, w), c in bic.items():
            by_u[self.index[u]].append((self.index[w], float(c)))
        for u, lst in by_u.items():
            ids = np.array([i for i, _ in lst], np.int64)
            cs = np.array([c for _, c in lst], np.float64)
            tot = cs.sum()
            Dm = np.where(cs >= 3, self.D[2], np.where(cs == 2, self.D[1], self.D[0]))
            self.big[u] = (ids, np.maximum(cs - Dm, 0.0) / tot)
            self.big_tot[u] = tot
            self.big_gam[u] = float((self.D[0] * np.sum(cs == 1) + self.D[1] * np.sum(cs == 2)
                                     + self.D[2] * np.sum(cs >= 3)) / tot)
        order = sorted(range(len(self.vocab)), key=lambda i: self.vocab[i])
        self.sorted_vocab = [self.vocab[i] for i in order]
        self.sorted_ids = np.array(order, np.int64)
        self._build_next_sym()
        return self

    def _build_next_sym(self, kmax: int = 24) -> None:
        """Symbol that follows a k-letter prefix of each word (a space once the word is complete)."""
        ns = np.full((kmax + 1, len(self.vocab)), SPACE_ID, np.int8)
        for i, w in enumerate(self.vocab):
            if w == EOS_W:
                ns[:, i] = -1
                ns[0, i] = EOS_ID
                continue
            for k, c in enumerate(w[:kmax + 1]):
                ns[k, i] = SYM.get(c, SPACE_ID)
        self.next_sym = ns

    def dist(self, prev: Optional[str]) -> np.ndarray:
        """P(w | previous word) over the vocabulary (prev None or unknown -> sentence start / unigram)."""
        key = prev if prev is not None else BOS_W
        hit = self._cache.get(key)
        if hit is not None:
            return hit.copy()
        u = self.index.get(key, None)
        if u is None or u not in self.big:
            p = self.p_uni.copy()
        else:
            ids, disc = self.big[u]
            p = self.big_gam[u] * self.p_uni
            p[ids] += disc
        if len(self._cache) > 4096:
            self._cache.clear()
        self._cache[key] = p
        return p.copy()

    def prob(self, w: str, prev: Optional[str]) -> float:
        """P(w | prev) without copying the distribution (uses the per-context cache)."""
        i = self.index.get(w)
        if i is None or i < 0:
            return 0.0
        key = prev if prev is not None else BOS_W
        vec = self._cache.get(key)
        if vec is None:
            self.dist(prev)
            vec = self._cache.get(key)
        return float(vec[i])

    def prefix_range(self, prefix: str) -> np.ndarray:
        """Vocabulary ids of words starting with ``prefix``."""
        lo = bisect.bisect_left(self.sorted_vocab, prefix)
        hi = bisect.bisect_left(self.sorted_vocab, prefix + "\x7f")
        return self.sorted_ids[lo:hi]

    def in_vocab(self, w: str) -> bool:
        return w in self.index and w != BOS_W

    def count(self, w: str) -> float:
        i = self.index.get(w)
        return float(self.unigram_count[i]) if i is not None and i >= 0 else 0.0


# =================================================================== predictor
def _split_context(text: str) -> Tuple[Optional[str], str]:
    """(previous complete word or None at sentence start, current partial word)."""
    if not text:
        return None, ""
    line = text.split(EOS)[-1]
    if line.endswith(" "):
        ws = words_of(line)
        return (ws[-1] if ws else None), ""
    parts = line.split(" ")
    partial = parts[-1]
    prev_ws = words_of(" ".join(parts[:-1]))
    return (prev_ws[-1] if prev_ws else None), partial


@dataclass
class Prediction:
    chars: str                   # top-1 predicted characters
    conf: List[float]            # calibrated confidence per predicted position (joint prefix probability)
    dist: Optional[np.ndarray] = None


@dataclass
class TextPredictor:
    char: CharKN
    word: WordKN
    lam: float = 0.6             # weight of the character model in the next-character mixture
    T: float = 1.0               # temperature (fitted on validation)
    info: Dict = field(default_factory=dict)

    # ---------------------------------------------------------- distributions
    def word_char_dist(self, text: str) -> Optional[np.ndarray]:
        """Next-character distribution implied by WordKN completions of the partial word."""
        prev, partial = _split_context(text)
        if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789'-/" for c in partial):
            return None
        ids = self.word.prefix_range(partial)
        if len(ids) == 0:
            return None
        k = len(partial)
        if k >= self.word.next_sym.shape[0]:
            return None
        pw = self.word.dist(prev)[ids]
        ns = self.word.next_sym[k, ids].astype(np.int64)
        ok = ns >= 0
        if not ok.any():
            return None
        out = np.bincount(ns[ok], weights=pw[ok], minlength=V)
        s = out.sum()
        return out / s if s > 0 else None

    def raw_dist(self, text: str) -> np.ndarray:
        pc = self.char.dist(text)
        pw = self.word_char_dist(text)
        p = pc if pw is None else self.lam * pc + (1 - self.lam) * pw
        return p / p.sum()

    def dist(self, text: str) -> np.ndarray:
        """Calibrated next-character distribution."""
        return _temper(self.raw_dist(text), self.T)

    def next_char(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        p = self.dist(text)
        idx = np.argsort(-p)[:k]
        return [(LM_ALPHABET[i], float(p[i])) for i in idx]

    def predict_ahead(self, text: str, depth: int, beam: int = 8) -> np.ndarray:
        """Distribution of the character ``depth`` positions ahead (marginalised over a beam)."""
        paths = [(text, 1.0)]
        for d in range(depth - 1):
            nxt = []
            for t, w in paths:
                p = self.dist(t)
                for i in np.argsort(-p)[:beam]:
                    nxt.append((t + LM_ALPHABET[i], w * p[i]))
            nxt.sort(key=lambda z: -z[1])
            paths = nxt[:beam]
        out = np.zeros(V)
        tot = sum(w for _, w in paths)
        for t, w in paths:
            out += (w / tot) * self.dist(t)
        return out

    def glyph_ahead(self, text: str, d: int = 1, beam: int = 10, calibrated: bool = True) -> np.ndarray:
        """Distribution of the d-th next *glyph* (spaces are gaps, not glyphs).

        This is the quantity a template needs: the next letter to be written
        (d = 1), or the one after it (d = 2) when the template must be sent
        before the current letter is finished.  Paths are expanded with the
        raw next-character model over a beam; sentence ends are dropped; the
        result is tempered with the depth-specific temperature fitted on the
        validation split (``info['T_glyph']``).
        """
        out = np.zeros(V)
        paths = [(text, 1.0, 0)]
        for _ in range(2 * d + 1):
            nxt = []
            for t, w, g in paths:
                p = self.raw_dist(t)
                if g == d - 1:
                    q = p.copy()
                    q[SPACE_ID] = 0.0
                    q[EOS_ID] = 0.0
                    out += w * q
                    if p[SPACE_ID] > 1e-9 and not t.endswith(" "):
                        nxt.append((t + " ", w * p[SPACE_ID], g))
                else:
                    for i in np.argsort(-p)[:beam]:
                        if i == EOS_ID or (i == SPACE_ID and t.endswith(" ")):
                            continue
                        nxt.append((t + LM_ALPHABET[i], w * p[i], g + (i != SPACE_ID)))
            if not nxt:
                break
            nxt.sort(key=lambda z: -z[1])
            paths = nxt[:beam]
        s = out.sum()
        out = out / s if s > 0 else np.full(V, 1.0 / V)
        if calibrated:
            T = (self.info.get("T_glyph") or {}).get(str(d), self.T)
            out = _temper(out, T)
        return out

    def next_glyphs(self, text: str, d: int = 1, k: int = 3) -> List[Tuple[str, float]]:
        p = self.glyph_ahead(text, d)
        idx = np.argsort(-p)[:k]
        return [(LM_ALPHABET[i], float(p[i])) for i in idx]

    def complete(self, text: str, max_len: int = 12, beam: int = 6) -> Prediction:
        """Most likely continuation to the end of the current word, with the
        joint probability of each prefix of it (confidence per position)."""
        beams = [("", 1.0)]
        done = []
        for _ in range(max_len):
            nxt = []
            for s, w in beams:
                p = self.dist(text + s)
                for i in np.argsort(-p)[:beam]:
                    c = LM_ALPHABET[i]
                    if c in (" ", EOS) or c in ".,:":
                        done.append((s, w * p[i]))
                    else:
                        nxt.append((s + c, w * p[i]))
            if not nxt:
                break
            nxt.sort(key=lambda z: -z[1])
            beams = nxt[:beam]
            if done and max(w for _, w in done) > beams[0][1]:
                break
        cands = done + beams
        # confidence per position = total probability of candidates agreeing with the best string so far
        best = max(done, key=lambda z: z[1])[0] if done else beams[0][0]
        conf = []
        for k in range(1, len(best) + 1):
            conf.append(float(sum(w for s, w in cands if s[:k] == best[:k])))
        return Prediction(best, conf)

    def next_words(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        """Top-k next words (before any letter of the word is written)."""
        prev, partial = _split_context(text if text.endswith(" ") or not text else text + " ")
        p = self.word.dist(prev)
        p[0] = 0.0                                   # </s> is not a word to write
        idx = np.argpartition(-p, k)[:k]
        idx = idx[np.argsort(-p[idx])]
        tot = p.sum()
        return [(self.word.vocab[i], float(p[i] / tot)) for i in idx]

    def complete_word(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        prev, partial = _split_context(text)
        ids = self.word.prefix_range(partial)
        if not len(ids):
            return []
        pw = self.word.dist(prev)[ids]
        o = np.argsort(-pw)[:k]
        tot = pw.sum()
        return [(self.word.vocab[ids[i]], float(pw[i] / tot)) for i in o]


def _temper(p: np.ndarray, T: float) -> np.ndarray:
    if T == 1.0:
        return p
    q = np.power(np.maximum(p, 1e-300), 1.0 / T)
    return q / q.sum(axis=-1, keepdims=True)


# ============================================================ batch evaluation
def positions(sentences: Sequence[str]) -> List[Tuple[str, str]]:
    """(context text, target char) for every character of every sentence (incl. spaces and EOS)."""
    out = []
    for s in sentences:
        full = s + EOS
        for i, c in enumerate(full):
            out.append((s[:i], c))
    return out


def batch_raw_dists(pred: TextPredictor, contexts: Sequence[str], lam: Optional[float] = None):
    """Raw (untempered) mixture distributions for many contexts (vectorised char part)."""
    lam = pred.lam if lam is None else lam
    L = pred.char.order - 1
    C = np.stack([pred.char.context_ids(t) for t in contexts]) if L else np.zeros((len(contexts), 0), np.int64)
    Pc = np.concatenate([pred.char.dist_batch(C[a:a + 40000]) for a in range(0, len(C), 40000)])
    Pw = [pred.word_char_dist(t) for t in contexts]
    out = Pc.copy()
    for i, pw in enumerate(Pw):
        if pw is not None:
            out[i] = lam * Pc[i] + (1 - lam) * pw
    return out / out.sum(axis=1, keepdims=True), Pc, Pw


def fit_temperature(P: np.ndarray, y: np.ndarray, grid=None) -> float:
    grid = np.linspace(0.6, 1.6, 101) if grid is None else grid
    best, bT = 1e18, 1.0
    for T in grid:
        q = _temper(P, T)
        nll = -np.mean(np.log(np.maximum(q[np.arange(len(y)), y], 1e-300)))
        if nll < best:
            best, bT = nll, float(T)
    return bT


def calibration(conf: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> dict:
    """Expected calibration error (equal-width bins), Brier score and the reliability table."""
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    ece = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        m = (conf > a) & (conf <= b) if a > 0 else (conf >= a) & (conf <= b)
        if m.sum() == 0:
            rows.append({"bin": [round(a, 2), round(b, 2)], "n": 0})
            continue
        acc = float(correct[m].mean())
        c = float(conf[m].mean())
        ece += m.mean() * abs(acc - c)
        rows.append({"bin": [round(a, 2), round(b, 2)], "n": int(m.sum()), "mean_conf": c, "accuracy": acc})
    brier = float(np.mean((conf - correct) ** 2))
    return {"ece": float(ece), "brier_top1": brier, "bins": rows}


def build_predictor(splits, order: int = 7, lam: Optional[float] = None, fit_T: bool = True,
                    n_val_positions: int = 60000, seed: int = 0) -> TextPredictor:
    """Train CharKN and WordKN on the training split; choose lambda and T on validation."""
    ch = CharKN(order).fit(splits.train)
    wd = WordKN().fit(splits.train)
    pred = TextPredictor(ch, wd)
    rng = np.random.default_rng(seed)
    pos = positions(splits.val)
    sel = rng.choice(len(pos), size=min(n_val_positions, len(pos)), replace=False)
    ctx = [pos[i][0] for i in sel]
    y = np.array([SYM[pos[i][1]] for i in sel])
    _, Pc, Pw = batch_raw_dists(pred, ctx, lam=1.0)
    lam_grid = [lam] if lam is not None else [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    best = (1e18, 1.0)
    for lm_ in lam_grid:
        P = Pc.copy()
        for i, pw in enumerate(Pw):
            if pw is not None:
                P[i] = lm_ * Pc[i] + (1 - lm_) * pw
        nll = -np.mean(np.log(P[np.arange(len(y)), y]))
        if nll < best[0]:
            best = (nll, lm_)
    pred.lam = best[1]
    P, _, _ = batch_raw_dists(pred, ctx)
    pred.T = fit_temperature(P, y) if fit_T else 1.0
    pred.info = {"order": order, "lambda": pred.lam, "temperature": pred.T, "val_positions": len(y),
                 "val_nll_nats_raw": float(-np.mean(np.log(P[np.arange(len(y)), y]))),
                 "char_ngrams": ch.n_params(), "vocab_words": len(wd.vocab) - 1,
                 "train_chars": ch.n_train_chars}
    return pred


def glyph_positions(sentences: Sequence[str], d: int) -> List[Tuple[str, str]]:
    """(context text, target glyph) for every glyph (non-space character) of every
    sentence, with the context ending d glyphs before the target (the spaces
    after the context glyph are not observed yet)."""
    out = []
    for s in sentences:
        g = [i for i, c in enumerate(s) if c != " "]
        for j, i in enumerate(g):
            if j - d >= 0:
                ctx = s[:g[j - d] + 1]
            elif j - d == -1:
                ctx = ""
            else:
                continue
            out.append((ctx, s[i]))
    return out


def fit_glyph_temperatures(pred: TextPredictor, sentences: Sequence[str], depths=(1, 2), n: int = 6000,
                           seed: int = 1) -> Dict[str, float]:
    """Depth-specific temperatures for ``glyph_ahead`` fitted on validation positions."""
    rng = np.random.default_rng(seed)
    out = {}
    for d in depths:
        pos = glyph_positions(sentences, d)
        sel = rng.choice(len(pos), size=min(n, len(pos)), replace=False)
        P = np.stack([pred.glyph_ahead(pos[i][0], d, calibrated=False) for i in sel])
        y = np.array([SYM[pos[i][1]] for i in sel])
        out[str(d)] = fit_temperature(P, y)
    return out


def cached_predictor(splits=None, order: int = 7, rebuild: bool = False) -> TextPredictor:
    """Build (or load from aiguide/build/) the predictor trained on the corpus training split."""
    import pickle
    from . import BUILD_DIR, __version__
    from .corpus import CORPUS_FILE, make_splits, sha256_file
    key = f"pred_o{order}_{sha256_file(CORPUS_FILE)[:12]}_{__version__}.pkl"
    path = BUILD_DIR / key
    if path.exists() and not rebuild:
        with open(path, "rb") as f:
            return pickle.load(f)
    splits = splits or make_splits()
    pred = build_predictor(splits, order=order)
    pred.info["T_glyph"] = fit_glyph_temperatures(pred, splits.val)
    pred.word._cache.clear()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(pred, f, protocol=pickle.HIGHEST_PROTOCOL)
    return pred
