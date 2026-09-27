"""Source-grounded note assistant.

Pipeline: scope screen -> retrieval over the note store (SQLite FTS5, BM25 +
query-term coverage) -> ``LLMClient`` -> output validation -> storage of the
answer as a new ``ai_summary`` derived layer.  Enforced properties (tested in
app/tests/test_grounded.py):

1. Refusal when no note supports the question; the language model is then
   not called at all.
2. Every generated sentence must carry citations ``[S#]`` to retrieved
   sources; citations must name sources that were actually provided; each
   sentence's content words (and every number) must be found in the cited
   sources.  Any violation rejects the *whole* answer and nothing is stored.
3. Citations resolve to note ids, derived-layer span ids and stroke-id ranges
   (+ page boxes) so every claim can be traced to ink.
4. Answers are stored only as ``ai_summary`` layers with provenance (model id,
   version, locality, retrieval parameters, sources shown); originals and
   other layers are never modified; ``ai_summary`` text is never indexed or
   retrieved as a source.
5. Only recognised *text* is sent to the model, never stroke kinematics; a
   non-local model requires explicit, recorded user consent before any data
   leaves the device.
6. The assistant is not a medical device: questions asking for clinical or
   health inferences (e.g. about tremor or handwriting) are refused.

The default ``ExtractiveLLM`` is deterministic, local and makes no network
call; it quotes the best-supported note lines verbatim.  The lexical support
test is a necessary-not-sufficient faithfulness check (see README: evaluation
with AIS / ALCE-style citation precision and recall).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

from . import __version__
from ._util import ids_from_ranges, ranges_from_ids
from .notes import NoteStore
from .search import SearchIndex

ASSISTANT_ID = f"penapp.grounded@{__version__}"
DISCLAIMER = ("Generated only from your recognised notes; each sentence cites the note strokes it comes from. "
              "Not medical advice: this assistant is not a medical device and makes no inference about health "
              "or handwriting.")
INSUFFICIENT = "INSUFFICIENT_SOURCES"
SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered note excerpts provided. Write at most {n} short sentences, "
    "one per line. End every sentence with the citation markers of the excerpts that support it, e.g. [S1] "
    "or [S1][S3]. Do not add facts, numbers or names that are not in the cited excerpts. If the excerpts do "
    f"not answer the question, reply exactly {INSUFFICIENT}. Never comment on the writer's health, tremor or "
    "handwriting. The excerpts are machine-recognised handwriting and may contain recognition errors.")

STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on
once only or other our ours ourselves out over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very was we were what when where which
while who whom why will with would you your yours yourself yourselves note notes wrote write written did say said
tell told remind me please need needs anything something thing things
""".split())
_WORD = re.compile(r"\w+", re.UNICODE)
_CITE_GROUP = re.compile(r"(?:\s*\[\s*S\d+(?:\s*[,;]\s*S\d+)*\s*\])+")
_CITE_ID = re.compile(r"S\d+")
_BOUNDARY = re.compile(r"([.!?])\s+(?=[A-Z0-9\"'(])")
_ABBREV = frozenset({"dr", "mr", "mrs", "ms", "st", "vs", "etc", "no", "approx", "e.g", "i.e", "fig", "p"})

CLINICAL_PATTERNS = [
    re.compile(r"\b(diagnos\w*|prognos\w*|parkinson\w*|dementia|alzheimer\w*|disease|disorder|symptom\w*|"
               r"clinical\w*|medical advice|essential tremor|micrographia)\b", re.I),
    re.compile(r"\b(my|the writer'?s?|his|her|their)\s+(handwriting|writing|tremor|hand|strokes?|pen control)\b"
               r".*\b(worse|better|improv\w*|deteriorat\w*|sign\w*|indicat\w*|mean\w*|normal|severe|severity|"
               r"progress\w*|decline\w*|healthy|abnormal)\b", re.I),
    re.compile(r"\b(is|am|are)\s+(i|my|the writer)\b.*\b(tremor|ill|sick|healthy)\b", re.I),
]


def _norm(tok: str) -> str:
    t = tok.lower()
    if t.endswith("'s"):
        t = t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss") and not t.isdigit():
        t = t[:-1]
    return t


def content_terms(text: str) -> List[str]:
    """Lower-cased, lightly normalised content words (stopwords removed)."""
    out = []
    for tok in _WORD.findall(text):
        t = tok.lower()
        if t in STOPWORDS or (len(t) < 2 and not t.isdigit()):
            continue
        out.append(_norm(t))
    return out


def numeric_terms(text: str) -> List[str]:
    return [t.lower() for t in _WORD.findall(text) if any(c.isdigit() for c in t)]


def is_clinical_question(question: str) -> bool:
    return any(p.search(question) for p in CLINICAL_PATTERNS)


# ------------------------------------------------------------------ types
@dataclass(frozen=True)
class Passage:
    source_id: str
    note_id: str
    original_sha256: str
    layer_ids: Tuple[str, ...]
    span_id: str
    text: str
    stroke_ranges: Tuple[Tuple[int, int], ...]
    bbox_um: Tuple[float, ...]
    score: float
    coverage: float

    def citation(self) -> dict:
        return {"source_id": self.source_id, "note_id": self.note_id, "original_sha256": self.original_sha256,
                "layer_ids": list(self.layer_ids), "span_id": self.span_id,
                "stroke_ranges": [list(r) for r in self.stroke_ranges], "bbox_um": list(self.bbox_um)}


@dataclass(frozen=True)
class LLMRequest:
    """Everything a model sees: the question and numbered excerpt texts (no ink, no ids of the device)."""
    question: str
    sources: Tuple[Tuple[str, str], ...]
    system_prompt: str
    max_sentences: int


@runtime_checkable
class LLMClient(Protocol):
    model_id: str
    version: str
    is_local: bool
    deterministic: bool

    def complete(self, request: LLMRequest) -> str:
        """Return the answer text: sentences ending with [S#] markers, or INSUFFICIENT_SOURCES."""


class ExtractiveLLM:
    """Deterministic local default: quote the note lines that best match the question."""
    model_id = "penapp.extractive"
    version = __version__
    is_local = True
    deterministic = True

    def __init__(self, max_sentences: int = 3):
        self.max_sentences = max_sentences

    def complete(self, request: LLMRequest) -> str:
        q = set(content_terms(request.question))
        scored = []
        for rank, (sid, text) in enumerate(request.sources):
            overlap = len(q & set(content_terms(text)))
            if overlap:
                scored.append((-overlap, rank, sid, text.strip()))
        if not scored:
            return INSUFFICIENT
        scored.sort()
        best = scored[0][0]
        chosen = [s for s in scored if s[0] == best][:min(self.max_sentences, request.max_sentences)]
        return "\n".join(f"{text} [{sid}]" for _, _, sid, text in chosen)


class RemoteLLMClientSpec:
    """Placeholder showing how a cloud model plugs in. Never called in tests or the demo.

    A real implementation would send ``LLMRequest`` (question + excerpt texts
    only) to a provider after ``CloudConsent`` has been granted, then return
    the text for validation.  This stub makes no network call.
    """
    model_id = "remote-llm-spec"
    version = "0"
    is_local = False
    deterministic = False

    def complete(self, request: LLMRequest) -> str:
        raise NotImplementedError("remote models are not wired in this reference implementation")


@dataclass(frozen=True)
class CloudConsent:
    """Explicit, recorded user consent to send note text to a named non-local model."""
    granted: bool
    model_id: str
    granted_utc: str
    scope: str = "recognised note text excerpts only; no ink, no identifiers"


class ConsentRequiredError(PermissionError):
    pass


@dataclass
class AnswerSentence:
    text: str
    citations: List[dict]
    support: float


@dataclass
class Answer:
    question: str
    sentences: List[AnswerSentence]
    sources: List[Passage]
    layer_id: str
    model_id: str
    status: str = "answered"

    def to_json(self) -> dict:
        return {"status": self.status, "question": self.question, "layer_id": self.layer_id,
                "model_id": self.model_id, "sentences": [asdict(s) for s in self.sentences],
                "sources": [asdict(p) for p in self.sources]}


@dataclass
class Refusal:
    question: str
    reason: str
    message: str
    violations: List[str] = field(default_factory=list)
    llm_called: bool = False
    status: str = "refused"

    def to_json(self) -> dict:
        return asdict(self)


# -------------------------------------------------------------- validation
def split_claims(text: str) -> List[Tuple[str, List[str]]]:
    """Split model output into (sentence, cited ids) pairs.

    A citation group closes a claim; text after the last group, or any sentence
    boundary / line break inside a claim, yields sentences without citations.
    """
    out: List[Tuple[str, List[str]]] = []
    pos = 0

    def pieces(chunk: str) -> List[str]:
        parts: List[str] = []
        for line in chunk.split("\n"):
            start = 0
            for m in _BOUNDARY.finditer(line):
                prev = line[start:m.start()].split()
                if prev and prev[-1].lower().rstrip(".") in _ABBREV:
                    continue
                parts.append(line[start:m.end(1)])
                start = m.end()
            parts.append(line[start:])
        return [p.strip() for p in parts if p.strip(" \t.,;:!?-")]

    for m in _CITE_GROUP.finditer(text):
        ps = pieces(text[pos:m.start()])
        ids = _CITE_ID.findall(m.group(0))
        if not ps:
            if out:                          # markers after a period: attach to the previous sentence
                out[-1] = (out[-1][0], out[-1][1] + ids)
            else:
                out.append(("", ids))
        else:
            out.extend((p, []) for p in ps[:-1])
            out.append((ps[-1], ids))
        pos = m.end()
    out.extend((p, []) for p in pieces(text[pos:]))
    return out


def validate_answer(text: str, passages: Sequence[Passage], *, min_support: float = 0.75,
                    max_sentences: int = 5) -> Tuple[List[AnswerSentence], List[str]]:
    by_id = {p.source_id: p for p in passages}
    claims = split_claims(text)
    violations: List[str] = []
    sentences: List[AnswerSentence] = []
    if not claims:
        return [], ["empty_output"]
    if len(claims) > max_sentences:
        violations.append(f"too_many_sentences: {len(claims)} > {max_sentences}")
    for k, (sent, ids) in enumerate(claims):
        if not sent:
            violations.append(f"sentence {k}: citation without text")
            continue
        if not ids:
            violations.append(f"sentence {k}: uncited sentence {sent!r}")
            continue
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            violations.append(f"sentence {k}: cites unknown sources {unknown}")
            continue
        cited = [by_id[i] for i in dict.fromkeys(ids)]
        src_terms = set(t for p in cited for t in content_terms(p.text))
        terms = content_terms(sent)
        support = (sum(t in src_terms for t in terms) / len(terms)) if terms else 0.0
        if not terms:
            violations.append(f"sentence {k}: no content words")
        elif support < min_support:
            violations.append(f"sentence {k}: unsupported by cited sources (support {support:.2f} < {min_support})")
        src_nums = set(n for p in cited for n in numeric_terms(p.text))
        bad_nums = [n for n in numeric_terms(sent) if n not in src_nums]
        if bad_nums:
            violations.append(f"sentence {k}: numbers {bad_nums} not in cited sources")
        sentences.append(AnswerSentence(sent, [p.citation() for p in cited], round(support, 4)))
    return sentences, violations


# --------------------------------------------------------------- assistant
class GroundedAssistant:
    def __init__(self, store: NoteStore, index: Optional[SearchIndex] = None, llm: Optional[LLMClient] = None, *,
                 top_k: int = 5, min_coverage: float = 0.5, min_support: float = 0.75, max_sentences: int = 3,
                 consent: Optional[CloudConsent] = None):
        self.store = store
        self.index = index or SearchIndex.for_store(store)
        self.llm = llm or ExtractiveLLM(max_sentences=max_sentences)
        self.top_k = top_k
        self.min_coverage = min_coverage
        self.min_support = min_support
        self.max_sentences = max_sentences
        self.consent = consent

    def retrieve(self, question: str, *, note_ids: Optional[Sequence[str]] = None) -> List[Passage]:
        q_terms = list(dict.fromkeys(content_terms(question)))
        if not q_terms:
            return []
        hits = self.index.search(" ".join(q_terms), mode="any", limit=self.top_k * 4, note_ids=note_ids)
        cands = []
        for rank, h in enumerate(hits):
            terms = set(content_terms(h.text))
            cov = sum(t in terms for t in q_terms) / len(q_terms)
            if cov >= self.min_coverage:
                cands.append((-cov, rank, h, cov))
        cands.sort(key=lambda c: (c[0], c[1]))
        out = []
        for k, (_, _, h, cov) in enumerate(cands[: self.top_k]):
            out.append(Passage(f"S{k + 1}", h.note_id, h.original_sha256, tuple(h.layer_ids), h.span_id, h.text,
                               tuple(tuple(r) for r in h.stroke_ranges), tuple(h.bbox_um), h.score, round(cov, 4)))
        return out

    def _check_consent(self) -> None:
        if getattr(self.llm, "is_local", False):
            return
        c = self.consent
        if c is None or not c.granted or c.model_id != self.llm.model_id:
            raise ConsentRequiredError(f"model {self.llm.model_id!r} is not local: explicit user consent is required "
                                       "before any note text leaves the device")

    def ask(self, question: str, *, note_ids: Optional[Sequence[str]] = None, store_result: bool = True):
        question = question.strip()
        if is_clinical_question(question):
            return Refusal(question, "out_of_scope_clinical",
                           "I can only look things up in your notes. I am not a medical device and do not assess "
                           "health, tremor or handwriting.")
        if not content_terms(question):
            return Refusal(question, "no_searchable_terms", "The question has no searchable words.")
        passages = self.retrieve(question, note_ids=note_ids)
        if not passages:
            return Refusal(question, "no_supporting_notes", "No supporting notes were found for this question.")
        self._check_consent()
        req = LLMRequest(question=question, sources=tuple((p.source_id, p.text) for p in passages),
                         system_prompt=SYSTEM_PROMPT.format(n=self.max_sentences), max_sentences=self.max_sentences)
        text = self.llm.complete(req)
        if text.strip() == INSUFFICIENT:
            return Refusal(question, "llm_declined", "The retrieved notes do not answer the question.",
                           llm_called=True)
        sentences, violations = validate_answer(text, passages, min_support=self.min_support,
                                                max_sentences=self.max_sentences)
        if violations:
            return Refusal(question, "ungrounded_output",
                           "The generated answer was rejected because it was not fully supported by cited notes.",
                           violations=violations, llm_called=True)
        layer_id = ""
        if store_result:
            layer_id = self._store(question, sentences, passages, text)["layer_id"]
        return Answer(question, sentences, passages, layer_id, self.llm.model_id)

    def _store(self, question: str, sentences: List[AnswerSentence], passages: List[Passage], raw: str) -> dict:
        note_ids = list(dict.fromkeys(p.note_id for p in passages))
        inputs: List[dict] = []
        for nid in note_ids:
            ps = [p for p in passages if p.note_id == nid]
            ids = [i for p in ps for i in ids_from_ranges(p.stroke_ranges)]
            inputs.append({"type": "original", "sha256": ps[0].original_sha256, "stroke_ranges": ranges_from_ids(ids)})
        layer_spans: Dict[str, List[str]] = {}
        for p in passages:
            for lid in p.layer_ids:
                layer_spans.setdefault(lid, [])
                if lid.startswith("recognition-") and p.span_id not in layer_spans[lid]:
                    layer_spans[lid].append(p.span_id)
        for lid, spans in layer_spans.items():
            inputs.append({"type": "layer", "layer_id": lid, **({"span_ids": spans} if spans else {})})
        payload = {
            "question": question,
            "sentences": [asdict(s) for s in sentences],
            "sources": [{"source_id": p.source_id, "note_id": p.note_id, "layer_ids": list(p.layer_ids),
                         "span_id": p.span_id, "text": p.text, "stroke_ranges": [list(r) for r in p.stroke_ranges],
                         "bbox_um": list(p.bbox_um), "score": p.score} for p in passages],
            "llm": {"model_id": self.llm.model_id, "version": str(self.llm.version),
                    "local": bool(self.llm.is_local), "deterministic": bool(self.llm.deterministic)},
            "validation": {"all_sentences_cited": True, "min_support": self.min_support,
                           "numbers_checked": True, "raw_output_chars": len(raw)},
            "disclaimer": DISCLAIMER,
        }
        params = {"retrieval": {"method": "sqlite-fts5 bm25 (porter, unicode61) + query-term coverage",
                                "top_k": self.top_k, "min_coverage": self.min_coverage},
                  "max_sentences": self.max_sentences,
                  "consent": None if self.consent is None else asdict(self.consent)}
        return self.store.add_layer(kind="ai_summary", note_ids=note_ids, created_by=ASSISTANT_ID,
                                    inputs=inputs, payload=payload, params=params)
