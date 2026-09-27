"""Corpus handling and language-model tests (CALCULATION checks; no network)."""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pytest

from aiguide import corpus, lm


def test_normalize_maps_to_glyph_alphabet():
    s = corpus.normalize("Hello, World!  Ça va?  Tom's 3% plan — done")
    assert s == "hello, world. ca va. tom's 3 percent plan - done"
    assert all(c in corpus.ALPHABET for c in s)


def test_splits_deterministic_disjoint_and_sized():
    a = corpus.make_splits()
    b = corpus.make_splits()
    assert a.train == b.train and a.test == b.test
    tr, va, te = set(a.train), set(a.val), set(a.test)
    assert not (tr & va) and not (tr & te) and not (va & te)
    n = len(tr) + len(va) + len(te)
    assert 0.08 < len(te) / n < 0.12 and 0.08 < len(va) / n < 0.12


def test_corpus_provenance_matches_snapshot():
    p = corpus.provenance()
    assert p["snapshot_matches_recorded_sha256"]
    assert "CC0" in p["licence"] and p["url"].startswith("https://")


# ------------------------------------------------------------ brute-force KN reference
def _reference_kn(sentences, N):
    """Independent dictionary implementation of interpolated modified Kneser-Ney with EOS padding."""
    E = corpus.EOS
    grams = defaultdict(Counter)                  # order -> Counter(ngram string)
    for s in sentences:
        seq = E * (N - 1) + s + E
        for t in range(N - 1, len(seq)):
            for n in range(1, N + 1):
                grams[n][seq[t - n + 1:t + 1]] += 1
    counts = {N: dict(grams[N])}
    for n in range(N - 1, 0, -1):
        cont = Counter()
        for g in grams[n + 1]:
            cont[g[1:]] += 1
        counts[n] = dict(cont)

    def disc(cs):
        c = np.array(list(cs.values()), float)
        n1, n2, n3, n4 = (float(np.sum(c == k)) for k in (1, 2, 3, 4))
        if n1 == 0 or n2 == 0:                      # same documented fallback as lm._discounts
            return np.array([0.5, 1.0, 1.5])
        Y = n1 / (n1 + 2 * n2)
        D = np.array([1 - 2 * Y * n2 / n1, 2 - 3 * Y * n3 / n2 if n2 else 1.0, 3 - 4 * Y * n4 / n3 if n3 else 1.5])
        return np.clip(D, 0.05, [1.0, 2.0, 3.0])

    D = {n: disc(counts[n]) for n in counts}

    def prob(ctx, w):
        p = 1.0 / lm.V
        for n in range(1, N + 1):
            h = ctx[len(ctx) - (n - 1):] if n > 1 else ""
            cs = {g[-1]: c for g, c in counts[n].items() if g[:-1] == h}
            if not cs:
                continue
            tot = sum(cs.values())
            d = D[n]
            dm = lambda c: d[2] if c >= 3 else d[1] if c == 2 else d[0]
            gam = sum(dm(c) for c in cs.values()) / tot
            p = max(cs.get(w, 0) - (dm(cs[w]) if w in cs else 0), 0) / tot + gam * p
        return p
    return prob


def test_charkn_matches_bruteforce_reference():
    sents = ["abca", "abcb", "bca", "cab", "aab", "abc abc", "ca ab"]
    N = 3
    m = lm.CharKN(N).fit(sents)
    ref = _reference_kn(sents, N)
    for ctx in ["", "a", "ab", "bc", "zz", "c a"]:
        p = m.dist(ctx)
        full = (corpus.EOS * (N - 1) + ctx)[-(N - 1):]
        q = np.array([ref(full, w) for w in corpus.LM_ALPHABET])
        assert abs(p.sum() - 1) < 1e-12
        assert np.allclose(p, q / q.sum(), atol=1e-12), ctx


def test_wordkn_distributions_and_prefix_range():
    sents = ["the cat sat", "the cat ran", "a dog sat", "the dog"]
    w = lm.WordKN().fit(sents)
    for prev in (None, "the", "unknownword"):
        assert abs(w.dist(prev).sum() - 1) < 1e-12
    ids = w.prefix_range("ca")
    assert sorted(w.vocab[i] for i in ids) == ["cat"]
    assert w.dist("the")[w.index["cat"]] > w.dist("the")[w.index["sat"]]


def test_glyph_ahead_skips_spaces_and_sums_to_one():
    sents = ["ab cd"] * 30 + ["ab ce"] * 10
    pred = lm.TextPredictor(lm.CharKN(4).fit(sents), lm.WordKN().fit(sents), lam=0.5)
    p1 = pred.glyph_ahead("a", 1)
    p2 = pred.glyph_ahead("a", 2)
    p3 = pred.glyph_ahead("a", 3)
    for p in (p1, p2, p3):
        assert abs(p.sum() - 1) < 1e-9
        assert p[lm.SPACE_ID] == 0 and p[lm.EOS_ID] == 0
    assert lm.LM_ALPHABET[int(np.argmax(p1))] == "b"
    assert lm.LM_ALPHABET[int(np.argmax(p2))] == "c"
    assert lm.LM_ALPHABET[int(np.argmax(p3))] == "d"


def test_glyph_positions_depth_semantics():
    pos = lm.glyph_positions(["ab cd"], 2)
    assert pos == [("", "b"), ("a", "c"), ("ab", "d")]


def test_calibration_of_calibrated_scores_is_small():
    rng = np.random.default_rng(0)
    conf = rng.uniform(0, 1, 200_000)
    correct = rng.uniform(0, 1, conf.size) < conf
    assert lm.calibration(conf, correct.astype(float))["ece"] < 0.01


def test_temperature_fit_detects_overconfidence():
    rng = np.random.default_rng(1)
    n, k = 20_000, 5
    logits = rng.normal(0, 1, (n, k))
    true_p = np.exp(logits) / np.exp(logits).sum(1, keepdims=True)
    y = np.array([rng.choice(k, p=q) for q in true_p])
    over = np.exp(2 * logits) / np.exp(2 * logits).sum(1, keepdims=True)     # sharpened = over-confident
    T = lm.fit_temperature(over, y, grid=np.linspace(0.5, 3.0, 51))
    assert 1.6 < T < 2.4
