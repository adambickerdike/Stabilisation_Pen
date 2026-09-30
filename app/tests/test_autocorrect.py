"""Digital autocorrect: noisy channel, candidates, derived layer with stroke links, re-rendering.

All sessions are synthetic; the small language model below is trained on the
fixture sentences plus filler text, so these tests need no corpus and no network.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace

import numpy as np
import pytest

from conftest import LINES_A, LINES_B
from penapp import autocorrect as AC
from penapp import recognize
from penapp._util import ids_from_ranges
from penapp.notes import validate

FILLER = ["the milk and the bread are in the kitchen", "call the bank at nine", "books and more books",
          "return the books by monday", "buy eggs milk and bread", "the plumber called on friday",
          "check the offset of the sensor", "order the parts and the spare pens", "the test bench is ready"]


@pytest.fixture(scope="module")
def toy_model():
    from aiguide import lm
    sents = (LINES_A + LINES_B + FILLER) * 3
    return AC.NgramWordModel(lm.WordKN().fit(sents), lm.CharKN(4).fit(sents), min_count=1)


def test_channel_prefers_fewer_edits_and_scales_with_cer():
    assert AC.channel_logp("milk", "milk", 0.1) > AC.channel_logp("milk", "silk", 0.1) > AC.channel_logp("milk", "sick", 0.1)
    assert AC.channel_logp("mlk", "milk", 0.05) < AC.channel_logp("mlk", "milk", 0.15)     # deletions likelier at high CER
    assert AC.channel_logp("milk", "milk", 0.05) == pytest.approx(4 * math.log(0.95))


def test_delete_index_finds_words_within_two_edits():
    idx = AC.DeleteIndex(["library", "books", "friday", "fridge"])
    assert set(idx.lookup("librray")) == {"library"}
    assert "friday" in idx.lookup("frday") and "fridge" in idx.lookup("fridae")
    assert idx.lookup("xyzzy") == []
    assert AC.edit_distance("kitten", "sitting") == 3


def test_corrector_fixes_non_words_keeps_known_words(toy_model):
    ac = AC.Autocorrector(toy_model, cer=0.1, threshold=0.9)
    out = ac.correct_tokens(["buy", "mlik", "eggs", "and", "bread"])
    assert [c.chosen for c in out] == ["buy", "milk", "eggs", "and", "bread"]
    assert out[1].changed and out[1].posterior >= 0.9 and not out[0].changed
    keep = AC.Autocorrector(toy_model, cer=0.1, threshold=1.01).correct_tokens(["buy", "mlik"])
    assert not any(c.changed for c in keep)                                   # threshold above 1: never change


def test_punctuation_is_kept_and_digits_untouched(toy_model):
    out = AC.Autocorrector(toy_model, cer=0.1).correct_tokens(["return", "librray", "books,", "9", "am."])
    assert out[1].chosen == "library" and out[2].chosen == "books," and out[3].chosen == "9"


def test_out_of_vocabulary_names_can_survive(toy_model):
    """A correctly recognised name far from every lexicon word is not 'corrected'."""
    out = AC.Autocorrector(toy_model, cer=0.05, threshold=0.9).correct_tokens(["call", "zoltan", "at", "nine"])
    assert out[1].chosen == "zoltan"


def test_outside_model_alphabet_is_preserved_without_losing_context(toy_model):
    tokens = ["François", "wrote", "東京", "buy", "mlik", "eggs", "and", "bread", "🖊️"]
    out = AC.Autocorrector(toy_model, cer=.1, threshold=.9).correct_tokens(tokens)
    assert [out[i].chosen for i in [0, 2, 8]] == [tokens[i] for i in [0, 2, 8]]
    assert not any(out[i].changed for i in [0, 2, 8])
    assert out[4].chosen == "milk"


def test_personal_dictionary_enables_fixing_names(toy_model):
    m = AC.NgramWordModel(toy_model.word, toy_model.char, min_count=1)
    ac = AC.Autocorrector(m, cer=0.1, threshold=0.9)
    assert ac.correct_tokens(["call", "zoltn"])[1].chosen == "zoltn"
    m.add_personal(["zoltan"])
    assert ac.correct_tokens(["call", "zoltn"])[1].chosen == "zoltan"


def _noisy(store, nid, cer=0.12, seed=3):
    truth_layer = [l for l in store.list_layers(note_id=nid, kind="recognition")][-1]
    base = recognize.GroundTruthRecognizer({"lines": [
        {"text": s["text"], "words": [{"text": w["text"], "stroke_ranges": w["stroke_ranges"]}
                                      for w in truth_layer["payload"]["spans"] if w.get("parent") == s["span_id"]]}
        for s in truth_layer["payload"]["spans"] if s["level"] == "line"]})
    return recognize.run_recognizer(store, nid, recognize.ErrorInjectingRecognizer(base, cer, seed=seed))


def test_autocorrect_layer_keeps_links_and_never_touches_the_original(loaded, toy_model):
    store, ids = loaded
    nid = ids["a"]
    orig_before = store.original_for_note(nid).payload
    noisy = _noisy(store, nid)
    res = AC.autocorrect_note(store, nid, AC.Autocorrector(toy_model, cer=0.12, threshold=0.9))
    lay = res.layer
    validate(lay, "derived_layer")
    assert lay["kind"] == "recognition" and lay["created_by"].startswith("penapp.autocorrect@")
    assert res.base_layer_id == noisy["layer_id"]
    base_spans = {s["span_id"]: s for s in noisy["payload"]["spans"]}
    for s in lay["payload"]["spans"]:                     # every span cites exactly the strokes it corrects
        assert s["stroke_ranges"] == base_spans[s["span_id"]]["stroke_ranges"]
        assert s["bbox_um"] == base_spans[s["span_id"]]["bbox_um"]
    for c in lay["params"]["changes"]:
        assert base_spans[c["span_id"]]["text"] == c["from"] and c["from"] != c["to"]
    assert any(i["type"] == "layer" and i["layer_id"] == noisy["layer_id"] for i in lay["inputs"])
    assert store.original_for_note(nid).payload == orig_before
    assert store.get_layer(noisy["layer_id"]) == noisy                        # the base layer is untouched
    assert store.effective_text(nid)["recognition_layer_id"] == lay["layer_id"]
    assert store.verify()["ok"]
    ref = " ".join(LINES_A)
    hyp_before = " ".join(s["text"] for s in noisy["payload"]["spans"] if s["level"] == "line")
    hyp_after = " ".join(s["text"] for s in lay["payload"]["spans"] if s["level"] == "line")
    assert recognize.wer(ref, hyp_after) <= recognize.wer(ref, hyp_before)


def test_autocorrect_is_idempotent_on_its_base_and_can_stay_in_memory(loaded, toy_model):
    store, ids = loaded
    nid = ids["b"]
    _noisy(store, nid, seed=5)
    n_layers = len(store.list_layers(note_id=nid))
    ac = AC.Autocorrector(toy_model, cer=0.12)
    r1 = AC.autocorrect_note(store, nid, ac, write=False)
    assert r1.layer is None and len(store.list_layers(note_id=nid)) == n_layers
    a = AC.autocorrect_note(store, nid, ac)
    b = AC.autocorrect_note(store, nid, ac)                  # corrects the same base again: same content, same id
    assert a.layer["layer_id"] == b.layer["layer_id"]


def test_rerender_in_writer_style(loaded, toy_model, tmp_path):
    store, ids = loaded
    nid = ids["a"]
    _noisy(store, nid, cer=0.15, seed=8)
    res = AC.autocorrect_note(store, nid, AC.Autocorrector(toy_model, cer=0.15, threshold=0.5), write=False)
    assert res.changes, "the seeded errors should produce at least one change"
    rr = AC.rerender_words(store, nid, res)
    assert rr["fitted_words"] >= 3 and 1.5e3 < rr["style"]["x_height_um"] < 4e3
    for w in rr["words"]:
        change = next(c for c in res.changes if c["span_id"] == w["span_id"])
        assert w["stroke_ranges"] == change["stroke_ranges"] and w["polylines_um"]
    out = AC.rerender_svg(store, nid, rr, tmp_path / "rr.svg")
    svg = out.read_text()
    assert svg.count("data-span-id=") == len(rr["words"]) and "SYNTHETIC DATA" in svg


def test_corpus_model_end_to_end():
    """The Tatoeba-CC0 model (cached predictor or a fresh 5-gram) corrects a note-like line."""
    m = AC.NgramWordModel.from_corpus()
    assert "CC0" in m.source["licence"]
    out = AC.Autocorrector(m, cer=0.1).correct_tokens(["buy", "mlilk", "eggs", "and", "bread"])
    assert out[1].chosen == "milk"


def test_interactive_correction_is_proposal_then_explicit_user_edit(loaded, toy_model):
    store, ids = loaded
    nid = ids["a"]
    noisy = _noisy(store, nid, cer=.15, seed=8)
    before = store.effective_text(nid)
    count = len(store.list_layers(note_id=nid))
    proposal = AC.propose_autocorrect(store, nid, AC.Autocorrector(toy_model, cer=.15, threshold=.5))
    assert proposal.choices
    assert len(store.list_layers(note_id=nid)) == count and store.effective_text(nid) == before
    chosen = proposal.choices[0]
    edit = AC.accept_autocorrect(store, proposal, accepted_span_ids=[chosen.span_id])
    assert edit["kind"] == "user_edit" and edit["created_by"] == "user"
    assert store.effective_text(nid)["recognition_layer_id"] == noisy["layer_id"]
    assert store.get_layer(noisy["layer_id"]) == noisy
    assert len(edit["payload"]["edits"]) == 1
    with pytest.raises(AC.ValidationError, match="stale"):
        AC.accept_autocorrect(store, proposal, accepted_span_ids=[chosen.span_id])


def test_interactive_correction_protects_user_edits_and_rejects_tampering(loaded, toy_model):
    store, ids = loaded
    nid = ids["a"]
    _noisy(store, nid, cer=.15, seed=8)
    corrector = AC.Autocorrector(toy_model, cer=.15, threshold=.5)
    proposal = AC.propose_autocorrect(store, nid, corrector)
    chosen = proposal.choices[0]
    with pytest.raises(AC.ValidationError, match="select"):
        AC.accept_autocorrect(store, proposal, accepted_span_ids=[])
    bad = replace(proposal, choices=(replace(chosen, suggested="unoffered"),))
    with pytest.raises(AC.ValidationError, match="changed"):
        AC.accept_autocorrect(store, bad, accepted_span_ids=[chosen.span_id])
    store.add_user_edit(nid, {chosen.span_id: chosen.observed})   # intentional spelling/name as written
    fresh = AC.propose_autocorrect(store, nid, corrector)
    assert chosen.span_id not in {c.span_id for c in fresh.choices}
