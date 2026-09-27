"""Digital autocorrect of recognised note text, stored as a derived layer.

Pipeline
--------
recognition layer (any recogniser, e.g. ``ErrorInjectingRecognizer`` in tests)
  -> noisy-channel correction per line:
       candidates  every lexicon word within 2 edits (SymSpell-style delete index)
                   plus the observed word itself (kept even when out of vocabulary);
       prior       word bigram Kneser-Ney model (``aiguide.lm.WordKN``); an
                   out-of-vocabulary word gets p_oov x its character-model spelling
                   probability (``aiguide.lm.CharKN``), so names are not impossible;
       channel     weighted edit distance matching the recogniser's error process
                   (substitution 0.6 CER, deletion 0.2 CER, insertion 0.2 CER);
       decision    forward-backward posterior per word; the observed word is
                   replaced only if another word's posterior exceeds ``threshold``
                   (conservative: over-correction of rare words and names is the
                   main failure mode, see the evaluation in results/ai/autocorrect.json);
  -> a new ``recognition`` layer, ``created_by = penapp.autocorrect@<version>``,
     whose spans keep exactly the stroke links of the spans they correct and carry
     the posterior as ``confidence``; ``params.changes`` lists every change with
     the text before and after; the base layer and the original ink are untouched;
  -> optional re-rendering of the corrected words in the writer's own style
     (``rerender_words``), a derived drawing only (never written into the store).

The note-store schema has no dedicated correction layer kind; the proposal in
docs/ai_guidance.md adds ``text_correction`` so that suggestions do not become
the effective text by default.  Until then the layer is written only when the
caller asks for it (``write=True``), and it becomes the effective text
(most recent recognition layer) like any re-run recogniser.

Evidence status: the language model is trained on public-domain text
(Tatoeba English sentences, CC0 1.0); every evaluation here uses SYNTHETIC
sessions with injected recognition errors.  Nothing is a recognition result on
real ink.
"""
from __future__ import annotations

import math
from collections import defaultdict
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

from . import __version__
from ._util import ensure_stabpen_importable, ids_from_ranges, ranges_from_ids
from .notes import NoteStore, ValidationError

AUTOCORRECT_ID = "penapp.autocorrect"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
_STRIP = ".,:-/"


# ------------------------------------------------------------------ channel
@lru_cache(maxsize=200_000)
def channel_logp(obs: str, cand: str, cer: float, alphabet: int = 26) -> float:
    """log P(obs | cand) under the recogniser's edit process (best alignment, Viterbi approximation)."""
    cer = min(max(cer, 1e-4), 0.5)
    m_ok = math.log(1.0 - cer)
    sub = math.log(0.6 * cer / alphabet)
    dele = math.log(0.2 * cer)
    ins = math.log(0.2 * cer / alphabet)
    m = len(obs)
    prev = [j * ins for j in range(m + 1)]                 # row i = 0: only insertions
    for i in range(1, len(cand) + 1):
        ci = cand[i - 1]
        cur = [prev[0] + dele]
        for j in range(1, m + 1):
            best = prev[j - 1] + (m_ok if ci == obs[j - 1] else sub)
            d = prev[j] + dele                             # a candidate letter was deleted
            if d > best:
                best = d
            a = cur[j - 1] + ins                           # a letter was inserted
            if a > best:
                best = a
            cur.append(best)
        prev = cur
    return prev[m]


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class DeleteIndex:
    """SymSpell-style index: every lexicon word under all its deletions up to ``max_edits``."""

    def __init__(self, words: Iterable[str], max_edits: int = 2):
        self.max_edits = max_edits
        self.index: Dict[str, Set[str]] = defaultdict(set)
        for w in words:
            self.add(w)

    @staticmethod
    def _deletes(w: str, k: int) -> Set[str]:
        out = {w}
        frontier = {w}
        for _ in range(k):
            nxt = set()
            for s in frontier:
                for i in range(len(s)):
                    nxt.add(s[:i] + s[i + 1:])
            out |= nxt
            frontier = nxt
        return out

    def add(self, w: str) -> None:
        for d in self._deletes(w, self.max_edits):
            self.index[d].add(w)

    def lookup(self, w: str) -> List[str]:
        cands: Set[str] = set()
        for d in self._deletes(w, self.max_edits):
            cands |= self.index.get(d, set())
        return [c for c in cands if edit_distance(c, w) <= self.max_edits]


# ------------------------------------------------------------------ word model
@dataclass
class NgramWordModel:
    """Adapter from ``aiguide.lm`` (WordKN + CharKN) to what the corrector needs."""
    word: object
    char: object
    p_oov: float = 0.046                     # held-out OOV token rate of the corpus (results/ai/text_predictor.json)
    min_count: int = 2                       # correction lexicon: words seen at least this often
    personal: Set[str] = field(default_factory=set)
    p_personal: float = 1e-4
    source: Dict = field(default_factory=dict)

    def __post_init__(self):
        lex = [w for w in self.word.vocab if w.isalpha() and self.word.count(w) >= self.min_count]
        self.lexicon = set(lex)
        self.index = DeleteIndex(lex)
        for w in self.personal:
            self.index.add(w)
        self._spell_cache: Dict[str, float] = {}

    @classmethod
    def from_corpus(cls, *, order: int = 5, personal: Iterable[str] = (), **kw) -> "NgramWordModel":
        """Train on the Tatoeba CC0 training split (aiguide/data), about 6 s, or reuse the cached predictor."""
        ensure_stabpen_importable()
        import sys
        from ._util import REPO_ROOT
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from aiguide import BUILD_DIR, corpus, lm
        cached = sorted(BUILD_DIR.glob("pred_o7_*.pkl"))
        if cached:
            pred = lm.cached_predictor()
            word, char = pred.word, pred.char
        else:
            sp = corpus.make_splits()
            word, char = lm.WordKN().fit(sp.train), lm.CharKN(order).fit(sp.train)
        src = corpus.provenance()
        return cls(word, char, personal=set(personal), source={k: src[k] for k in ("name", "url", "licence", "sha256_used")}, **kw)

    def add_personal(self, words: Iterable[str]) -> None:
        for w in words:
            w = w.lower()
            if w not in self.personal:
                self.personal.add(w)
                self.index.add(w)

    def known(self, w: str) -> bool:
        return w in self.lexicon or w in self.personal

    def spell_logp(self, w: str) -> float:
        """log P(letters of w, then a word end | word start) under the character model."""
        if w in self._spell_cache:
            return self._spell_cache[w]
        from aiguide.lm import SYM, SPACE_ID
        ctx = "the "
        lp = 0.0
        for c in w:
            p = self.char.dist(ctx)
            lp += math.log(max(p[SYM[c]], 1e-12)) if c in SYM else math.log(1e-6)
            ctx += c
        p = self.char.dist(ctx)
        lp += math.log(max(p[SPACE_ID] + p[SYM["."]] + p[SYM[","]] + p[SYM["\n"]], 1e-12))
        self._spell_cache[w] = lp
        return lp

    def logprior(self, w: str, prev: Optional[str]) -> float:
        if w in self.personal and w not in self.lexicon:
            return math.log(self.p_personal)
        if w in self.lexicon:
            p = self.word.prob(w, prev if (prev is None or self.word.in_vocab(prev)) else "\x00")
            return math.log(1.0 - self.p_oov) + math.log(max(p, 1e-15))
        return math.log(self.p_oov) + self.spell_logp(w)

    def candidates(self, obs: str) -> List[str]:
        return self.index.lookup(obs)


# ------------------------------------------------------------------ corrector
@dataclass
class Correction:
    index: int
    observed: str
    chosen: str
    posterior: float                 # posterior of the chosen (output) word
    posterior_observed: float
    alternatives: List[Tuple[str, float]]

    @property
    def changed(self) -> bool:
        return self.chosen != self.observed


def _split_token(tok: str) -> Tuple[str, str, str]:
    core = tok.strip(_STRIP)
    if not core:
        return tok, "", ""
    a = tok.find(core)
    return tok[:a], core, tok[a + len(core):]


@dataclass
class Autocorrector:
    model: NgramWordModel
    cer: float = 0.08                # expected recogniser CER (sets the channel)
    threshold: float = 0.9           # posterior needed to replace the observed word
    max_candidates: int = 25
    min_len: int = 2                 # never touch one-letter tokens
    change_known_words: bool = True  # False: only non-words are corrected (no real-word correction)

    def _cands(self, obs: str) -> List[str]:
        c = set(self.model.candidates(obs)) if len(obs) >= self.min_len else set()
        if not self.change_known_words and self.model.known(obs):
            c = set()
        c.add(obs)
        if len(c) > self.max_candidates:
            ranked = sorted(c, key=lambda w: -(channel_logp(obs, w, self.cer) + self.model.logprior(w, None)))
            c = set(ranked[:self.max_candidates]) | {obs}
        return sorted(c)

    def correct_tokens(self, tokens: Sequence[str]) -> List[Correction]:
        """Posterior decoding over a line (forward-backward on a bigram lattice)."""
        parts = [_split_token(t.lower()) for t in tokens]
        cores = [p[1] for p in parts]
        active = [bool(c) and c.isalpha() for c in cores]
        lat: List[List[str]] = [self._cands(c) if a else [c] for c, a in zip(cores, active)]
        emis = [np.array([channel_logp(c, w, self.cer) if a else 0.0 for w in L]) for c, a, L in zip(cores, active, lat)]
        n = len(lat)
        if n == 0:
            return []
        fw: List[np.ndarray] = []
        for i in range(n):
            if i == 0:
                prior = np.array([self.model.logprior(w, None) for w in lat[0]])
                fw.append(emis[0] + prior)
                continue
            T = np.array([[self.model.logprior(w, u) for w in lat[i]] for u in lat[i - 1]])   # (prev, cur)
            fw.append(emis[i] + _lse(fw[i - 1][:, None] + T, axis=0))
        bw: List[np.ndarray] = [np.zeros(len(lat[-1]))]
        for i in range(n - 1, 0, -1):
            T = np.array([[self.model.logprior(w, u) for w in lat[i]] for u in lat[i - 1]])
            bw.insert(0, _lse(T + (emis[i] + bw[0])[None, :], axis=1))
        out = []
        for i in range(n):
            lp = fw[i] + bw[i]
            post = np.exp(lp - _lse(lp, axis=0))
            L = lat[i]
            j_obs = L.index(cores[i])
            order = np.argsort(-post)
            best = int(order[0])
            chosen = cores[i]
            if active[i] and best != j_obs and post[best] >= self.threshold:
                chosen = L[best]
            pch = float(post[L.index(chosen)])
            pre, _, suf = parts[i]
            out.append(Correction(i, tokens[i], pre + chosen + suf if chosen != cores[i] else tokens[i], pch,
                                  float(post[j_obs]), [(L[k], float(post[k])) for k in order[:3]]))
        return out


def _lse(a: np.ndarray, axis: int) -> np.ndarray:
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return np.squeeze(m, axis=axis) + np.log(np.sum(np.exp(a - m), axis=axis))


# ------------------------------------------------------------------ note layer
def _base_layer(store: NoteStore, note_id: str, layer_id: Optional[str]) -> dict:
    if layer_id:
        return store.get_layer(layer_id)
    recs = [l for l in store.list_layers(note_id=note_id, kind="recognition")
            if not l["created_by"].startswith(AUTOCORRECT_ID + "@")]
    if not recs:
        raise ValidationError("note has no recognition layer to correct")
    return recs[-1]


@dataclass
class AutocorrectResult:
    spans: List[dict]
    changes: List[dict]
    base_layer_id: str
    layer: Optional[dict] = None


def autocorrect_note(store: NoteStore, note_id: str, corrector: Autocorrector, *,
                     recognition_layer_id: Optional[str] = None, write: bool = True) -> AutocorrectResult:
    """Correct a note's recognised text; optionally store it as a derived recognition layer."""
    base = _base_layer(store, note_id, recognition_layer_id)
    spans = [dict(s) for s in base["payload"]["spans"]]
    words_by_line: Dict[str, List[dict]] = defaultdict(list)
    for s in spans:
        if s["level"] == "word" and s.get("parent"):
            words_by_line[s["parent"]].append(s)
    changes = []
    for line in [s for s in spans if s["level"] == "line"]:
        ws = words_by_line.get(line["span_id"], [])
        if not ws:
            continue
        corr = corrector.correct_tokens([w["text"] for w in ws])
        for w, c in zip(ws, corr):
            w["confidence"] = round(min(1.0, max(0.0, c.posterior)), 6)
            if c.changed:
                changes.append({"span_id": w["span_id"], "from": w["text"], "to": c.chosen,
                                "posterior": round(c.posterior, 6), "posterior_observed": round(c.posterior_observed, 6),
                                "stroke_ranges": w["stroke_ranges"]})
                w["text"] = c.chosen
        line["text"] = " ".join(w["text"] for w in ws)
        line["confidence"] = None
    res = AutocorrectResult(spans, changes, base["layer_id"])
    if not write:
        return res
    note = store.get_note(note_id)
    used = sorted({i for s in spans for i in ids_from_ranges(s["stroke_ranges"])})
    inputs = [{"type": "layer", "layer_id": base["layer_id"],
               "span_ids": [s["span_id"] for s in spans if s["level"] == "word"]},
              {"type": "original", "sha256": note["original_sha256"], "stroke_ranges": ranges_from_ids(used)}]
    src = corrector.model.source or {}
    if src.get("sha256_used"):
        inputs.append({"type": "external_file", "sha256": src["sha256_used"],
                       "role": "language-model training corpus (" + src.get("licence", "") + ")", "name": src.get("url", "")})
    params = {"base_layer": base["layer_id"], "base_created_by": base["created_by"],
              "model": {"kind": "word bigram Kneser-Ney + character n-gram spelling prior, noisy channel",
                        "corpus": src, "p_oov": corrector.model.p_oov, "lexicon_min_count": corrector.model.min_count,
                        "personal_words": len(corrector.model.personal)},
              "decision": {"threshold": corrector.threshold, "cer_assumed": corrector.cer,
                           "change_known_words": corrector.change_known_words, "max_edits": corrector.model.index.max_edits},
              "changes": changes}
    payload = {"language": base["payload"].get("language") or "en",
               "evidence_status": "AUTOCORRECT (n-gram noisy channel, derived text; ink untouched) over: "
                                  + base["payload"].get("evidence_status", ""),
               "spans": spans}
    res.layer = store.add_layer(kind="recognition", note_ids=[note_id], created_by=f"{AUTOCORRECT_ID}@{__version__}",
                                inputs=inputs, payload=payload, params=params)
    return res


# ------------------------------------------------------------------ re-rendering
def rerender_words(store: NoteStore, note_id: str, result: AutocorrectResult, *, only_changed: bool = True) -> dict:
    """Synthesise corrected words in the writer's own style (derived drawing; the ink is never modified).

    The style (size, width, slant, exemplars) is fitted on the note's own ink for
    words whose text was not changed and whose stroke count matches the glyph
    font; each corrected word is drawn from the left edge of the original word's
    box on the fitted baseline.  Returns polylines in um with the source stroke
    ranges, ready for an SVG overlay (``rerender_svg``) or a future ``rerender``
    layer kind (proposal in docs/ai_guidance.md).
    """
    ensure_stabpen_importable()
    import sys
    from ._util import REPO_ROOT
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from aiguide.glyphs import GLYPH_SET
    from aiguide.style import StyleEstimator
    from aiguide.template import letter_template
    orig = store.original_for_note(note_id)
    s = orig.samples
    by_sid = {sid: (a, b) for sid, a, b in orig.stroke_runs}
    changed = {c["span_id"] for c in result.changes}
    est = StyleEstimator()
    fitted_words = 0
    word_base: Dict[str, Tuple[float, float]] = {}
    for w in [x for x in result.spans if x["level"] == "word"]:
        if w["span_id"] in changed or not w["text"].isalpha():
            continue
        ids = ids_from_ranges(w["stroke_ranges"])
        need = [len(GLYPH_SET[c]) for c in w["text"] if c in GLYPH_SET]
        if sum(need) != len(ids):
            continue
        k = 0
        for ch, nk in zip(w["text"], need):
            strokes, times = [], []
            for sid in ids[k:k + nk]:
                a, b = by_sid[sid]
                if b - a >= 2:
                    strokes.append(np.column_stack([s["x_um"][a:b], s["y_um"][a:b]]).astype(float) * 1e-6)
                    times.append(s["t_ms"][a:b].astype(float) * 1e-3)
            k += nk
            if strokes:
                f = est.update(ch, strokes, t_strokes=times)
                word_base.setdefault(w["span_id"], (f.x0, f.y0))
        fitted_words += 1
    out = {"fitted_words": fitted_words, "words": []}
    if not est.fits:
        return out
    e = est.estimate()
    from aiguide.glyphs import width as glyph_width
    for c in result.changes if only_changed else []:
        w = next(x for x in result.spans if x["span_id"] == c["span_id"])
        # the word's own baseline: its box bottom lifted by the lowest glyph point of the corrected text
        lows = [float(min(np.vstack(GLYPH_SET[ch])[:, 1])) for ch in c["to"] if ch in GLYPH_SET]
        x0 = w["bbox_um"][0] * 1e-6
        y0 = w["bbox_um"][1] * 1e-6 - e.size * (min(lows) if lows else 0.0)
        polys = []
        for ch in c["to"]:
            if ch not in GLYPH_SET:
                x0 += e.size * 0.5
                continue
            t = letter_template(ch, e, x0, y0, estimator=est, mode="exemplar")
            polys += [(p * 1e6).round(1).tolist() for p in t.strokes]
            x0 += e.a * glyph_width(ch) + e.letter_gap * e.size
        out["words"].append({"span_id": c["span_id"], "text": c["to"], "replaces": c["from"],
                             "stroke_ranges": c["stroke_ranges"], "polylines_um": polys})
    out["style"] = {"x_height_um": e.h * 1e6, "width": e.width, "slant_deg": math.degrees(e.slant),
                    "letters_fitted": e.n_letters}
    return out


def rerender_svg(store: NoteStore, note_id: str, rr: dict, path, *, offset_um: float = 0.0) -> Path:
    """Original ink (grey) with the re-rendered corrected words (blue) drawn over their words (``offset_um`` shifts them)."""
    from xml.sax.saxutils import quoteattr
    orig = store.original_for_note(note_id)
    s = orig.samples
    xs, ys = s["x_um"].astype(float), s["y_um"].astype(float)
    pad = 4000.0
    x0, x1 = xs.min() - pad, xs.max() + pad
    y0, y1 = ys.min() - pad - abs(offset_um), ys.max() + pad
    W, H = (x1 - x0) / 1000.0, (y1 - y0) / 1000.0
    def pt(x, y):
        return f"{(x - x0) / 1000:.3f},{(y1 - y) / 1000:.3f}"
    el = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" viewBox="0 0 {W:.3f} {H:.3f}">',
          f'<rect width="{W:.3f}" height="{H:.3f}" fill="#fcfcfb"/>',
          '<text x="1" y="2.5" font-size="1.8" fill="#d03b3b">SYNTHETIC DATA - original ink (grey) is untouched; '
          'blue = corrected words re-rendered in the writer\'s style (derived)</text>']
    for sid, a, b in orig.stroke_runs:
        el.append(f'<polyline data-stroke-id="{sid}" fill="none" stroke="#b9b7b0" stroke-width="0.3" '
                  f'points="{" ".join(pt(xs[k], ys[k]) for k in range(a, b))}"/>')
    for w in rr.get("words", []):
        el.append(f'<g data-span-id={quoteattr(w["span_id"])} data-stroke-ranges={quoteattr(str(w["stroke_ranges"]))} '
                  f'data-replaces={quoteattr(w["replaces"])}>')
        for p in w["polylines_um"]:
            el.append(f'<polyline fill="none" stroke="#2a78d6" stroke-width="0.3" '
                      f'points="{" ".join(pt(q[0], q[1] + offset_um) for q in p)}"/>')
        el.append("</g>")
    el.append("</svg>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(el) + "\n", encoding="utf-8")
    return path
