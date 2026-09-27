"""SQLite FTS5 index: hits linked to stroke ids and page boxes, safe queries, edits, erasure."""
from __future__ import annotations

import pytest

from penapp.search import SearchIndex, build_match_expression


@pytest.fixture
def idx(loaded):
    store, _ = loaded
    with SearchIndex.for_store(store) as i:
        yield i


def test_hit_links_word_to_strokes_and_box(loaded, idx, session_a):
    store, ids = loaded
    hits = idx.search("library")
    assert len(hits) == 1
    h = hits[0]
    assert h.note_id == ids["a"] and h.text == "return library books by friday"
    truth = next(w for l in session_a.truth["lines"] for w in l["words"] if w["text"] == "library")
    assert [w.text for w in h.words] == ["library"]
    assert h.words[0].stroke_ranges == truth["stroke_ranges"]
    orig = store.original_for_note(ids["a"])
    a, b = truth["stroke_ranges"][0]
    assert h.words[0].bbox_um == orig.bbox_um(range(a, b + 1))
    assert h.matched_stroke_ranges == truth["stroke_ranges"]
    assert h.layer_ids and h.layer_ids[0].startswith("recognition-")


def test_phrase_and_boolean_modes(idx):
    assert [h.text for h in idx.search('"hall sensor"')] == ["check hall sensor offset"]
    assert idx.search('"sensor hall"') == []
    assert idx.search("plumber friday") == []                      # AND across different lines
    assert len(idx.search("plumber friday", mode="any")) == 2
    assert [w.text for w in idx.search("refill")[0].words] == ["refills"]   # porter stemming
    assert idx.search("mon")[:1] == [] and idx.search("mon", prefix=True)[0].words[0].text == "monday"


def test_case_and_diacritics_insensitive(idx):
    assert idx.search("LIBRARY")[0].words[0].text == "library"
    assert idx.search("líbráry")[0].words[0].text == "library"


@pytest.mark.parametrize("q", ['"', "NEAR(", "a OR", "*", "()", "library AND", "-", "µm", "'; DROP TABLE lines;--"])
def test_hostile_queries_are_inert(idx, q):
    idx.search(q)                                                   # must not raise
    assert idx.count_lines() == 6


def test_match_expression_quotes_everything():
    assert build_match_expression('buy "hall sensor" NEAR(') == '"buy" AND "hall sensor" AND "NEAR"'
    assert build_match_expression("  ") is None


def test_user_edit_reindex_and_staleness(loaded, idx):
    store, ids = loaded
    rec = store.list_layers(note_id=ids["a"], kind="recognition")[-1]
    span = next(s for s in rec["payload"]["spans"] if s.get("text") == "plumber")
    edit = store.add_user_edit(ids["a"], {span["span_id"]: "electrician"})
    assert idx.is_stale(store, ids["a"])
    idx.index_note(store, ids["a"])
    h = idx.search("electrician")[0]
    assert h.words[0].stroke_ranges == span["stroke_ranges"]       # corrected text still points at the ink
    assert h.layer_ids == [rec["layer_id"], edit["layer_id"]]
    assert idx.search("plumber") == [] and not idx.is_stale(store, ids["a"])


def test_assistant_output_is_not_indexed(loaded, idx):
    from penapp.grounded import GroundedAssistant
    store, _ = loaded
    n = idx.count_lines()
    ans = GroundedAssistant(store, idx).ask("When should I return the library books?")
    assert ans.status == "answered"
    idx.rebuild(store)
    assert idx.count_lines() == n
    assert all(all(l.startswith(("recognition-", "user_edit-")) for l in h.layer_ids)
               for h in idx.search("library books", mode="any"))


def test_purge_and_remove_note(loaded, idx):
    store, ids = loaded
    store.purge_note(ids["a"], confirm=ids["a"])
    idx.remove_note(ids["a"])
    assert idx.search("library") == [] and idx.search("hall")
