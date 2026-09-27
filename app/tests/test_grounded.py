"""Source-grounded assistant: citations, refusals, rejection of ungrounded output, storage rules."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from penapp import grounded as g
from penapp.notes import validate
from penapp.search import SearchIndex

Q_LIBRARY = "When should I return the library books?"


class FakeLLM:
    """Scripted model that records every request it receives."""

    def __init__(self, reply, *, local=True, model_id="fake-llm"):
        self.reply = reply
        self.is_local = local
        self.model_id = model_id
        self.version = "test"
        self.deterministic = True
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return self.reply(request) if callable(self.reply) else self.reply


def _snapshot(root: Path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / "originals").glob("*.json"))}


def _n_layers(store):
    return len(list((store.root / "layers").glob("*.json")))


def _assistant(store, llm=None, **kw):
    return g.GroundedAssistant(store, SearchIndex.for_store(store), llm, **kw)


def test_extractive_answer_is_cited_down_to_strokes(loaded, session_a):
    store, ids = loaded
    before = _snapshot(store.root)
    ans = _assistant(store).ask(Q_LIBRARY)
    assert ans.status == "answered"
    assert [s.text for s in ans.sentences] == ["return library books by friday"]
    c = ans.sentences[0].citations[0]
    assert c["note_id"] == ids["a"] and c["span_id"] == "l1"
    truth_ids = {i for w in session_a.truth["lines"][1]["words"] for r in w["stroke_ranges"]
                 for i in range(r[0], r[1] + 1)}
    cited_ids = {i for r in c["stroke_ranges"] for i in range(r[0], r[1] + 1)}
    assert cited_ids == truth_ids
    layer = store.get_layer(ans.layer_id)
    assert layer["kind"] == "ai_summary" and layer["created_by"].startswith("penapp.grounded@")
    assert layer["payload"]["llm"] == {"model_id": "penapp.extractive", "version": layer["payload"]["llm"]["version"],
                                       "local": True, "deterministic": True}
    assert {i["type"] for i in layer["inputs"]} == {"original", "layer"}
    assert "not a medical device" in layer["payload"]["disclaimer"]
    validate(layer, "derived_layer")
    assert _snapshot(store.root) == before                                  # originals never modified


def test_answer_is_deterministic(loaded):
    store, _ = loaded
    a = _assistant(store).ask(Q_LIBRARY)
    b = _assistant(store).ask(Q_LIBRARY)
    assert a.layer_id == b.layer_id and [s.text for s in a.sentences] == [s.text for s in b.sentences]


def test_cross_note_answer_cites_both_notes(loaded):
    store, ids = loaded
    ans = _assistant(store).ask("What should I buy or order?")
    notes = {c["note_id"] for s in ans.sentences for c in s.citations}
    assert notes == {ids["a"], ids["b"]}
    assert set(store.get_layer(ans.layer_id)["note_ids"]) == notes


def test_refuses_without_supporting_notes_and_never_calls_the_model(loaded):
    store, _ = loaded
    llm = FakeLLM("anything [S1]")
    n = _n_layers(store)
    for q in ("What is the wifi password?", "What is it?", "When is the library wifi password due?"):
        res = _assistant(store, llm).ask(q)
        assert res.status == "refused" and res.reason in ("no_supporting_notes", "no_searchable_terms")
    assert llm.requests == [] and _n_layers(store) == n


@pytest.mark.parametrize("reply,why", [
    ("return library books by friday", "uncited"),
    ("return library books by friday [S1]\nThe library also sells coffee.", "uncited"),
    ("Return library books by friday. It is overdue. [S1]", "uncited"),        # two sentences, one citation
    ("return library books by friday [S7]", "unknown sources"),
    ("The plumber comes on sunday [S1]", "unsupported"),
    ("return library books by friday at 10 [S1]", "numbers"),
    ("[S1]", "citation without text"),
    ("", "empty_output"),
])
def test_rejects_ungrounded_model_output_and_stores_nothing(loaded, reply, why):
    store, _ = loaded
    llm = FakeLLM(reply)
    n = _n_layers(store)
    before = _snapshot(store.root)
    res = _assistant(store, llm).ask(Q_LIBRARY)
    assert res.status == "refused" and res.reason == "ungrounded_output" and res.llm_called
    assert any(why in v for v in res.violations), res.violations
    assert len(llm.requests) == 1
    assert _n_layers(store) == n and _snapshot(store.root) == before


def test_accepts_cited_paraphrase_with_markers_after_the_period(loaded):
    store, _ = loaded
    llm = FakeLLM("Return the library books by Friday. [S1]")
    res = _assistant(store, llm).ask(Q_LIBRARY)
    assert res.status == "answered" and res.sentences[0].support == 1.0
    assert store.get_layer(res.layer_id)["payload"]["llm"]["model_id"] == "fake-llm"


def test_model_declining_is_a_refusal(loaded):
    store, _ = loaded
    res = _assistant(store, FakeLLM(g.INSUFFICIENT)).ask(Q_LIBRARY)
    assert res.status == "refused" and res.reason == "llm_declined"


def test_model_sees_only_question_and_excerpt_text(loaded):
    store, _ = loaded
    llm = FakeLLM(lambda r: f"{r.sources[0][1]} [S1]")
    _assistant(store, llm).ask(Q_LIBRARY)
    req = llm.requests[0]
    assert set(vars(req)) == {"question", "sources", "system_prompt", "max_sentences"}
    assert all(isinstance(i, str) and isinstance(t, str) for i, t in req.sources)
    assert "note-" not in repr(req.sources) and "stroke" not in repr(req.sources)


def test_non_local_model_needs_explicit_consent(loaded):
    store, _ = loaded
    remote = FakeLLM("return library books by friday [S1]", local=False, model_id="cloud-x")
    with pytest.raises(g.ConsentRequiredError):
        _assistant(store, remote).ask(Q_LIBRARY)
    assert remote.requests == []
    wrong = g.CloudConsent(True, "other-model", "2026-09-01T00:00:00.000Z")
    with pytest.raises(g.ConsentRequiredError):
        _assistant(store, remote, consent=wrong).ask(Q_LIBRARY)
    ok = g.CloudConsent(True, "cloud-x", "2026-09-01T00:00:00.000Z")
    res = _assistant(store, remote, consent=ok).ask(Q_LIBRARY)
    assert res.status == "answered"
    assert store.get_layer(res.layer_id)["params"]["consent"]["model_id"] == "cloud-x"
    with pytest.raises(NotImplementedError):
        g.RemoteLLMClientSpec().complete(None)


@pytest.mark.parametrize("q", ["Is my tremor getting worse?", "Does my handwriting show signs of Parkinson's?",
                               "Can you diagnose me from my strokes?", "Is my handwriting normal?"])
def test_clinical_questions_are_refused(loaded, q):
    store, _ = loaded
    llm = FakeLLM("x [S1]")
    res = _assistant(store, llm).ask(q)
    assert res.status == "refused" and res.reason == "out_of_scope_clinical" and llm.requests == []


@pytest.mark.parametrize("q", ["When do I take my pills?", "What did I note about the bench test?",
                               "What is on the hall sensor list?"])
def test_ordinary_questions_pass_the_scope_screen(q):
    assert not g.is_clinical_question(q)


def test_split_claims():
    assert g.split_claims("Meet Dr. Lee at 3 pm [S1]") == [("Meet Dr. Lee at 3 pm", ["S1"])]
    assert g.split_claims("A b. [S1][S2]\nC d [S3, S4]") == [("A b.", ["S1", "S2"]), ("C d", ["S3", "S4"])]
    assert g.split_claims("A b. C d [S1]") == [("A b.", []), ("C d", ["S1"])]
    assert g.split_claims("A b [S1] trailing") == [("A b", ["S1"]), ("trailing", [])]
