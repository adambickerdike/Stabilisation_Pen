"""Recogniser interface, metrics, error injection and the ML Kit adapter mapping."""
from __future__ import annotations

import numpy as np
import pytest

from penapp import logfmt, recognize
from penapp.notes import OriginalLayer, validate


def test_edit_distance_metrics():
    assert recognize.levenshtein("kitten", "sitting") == 3
    assert recognize.cer("abcd", "abcd") == 0.0
    assert recognize.cer("abcd", "abxd") == 0.25
    assert recognize.wer("buy milk now", "buy silk now") == pytest.approx(1 / 3)
    ev = recognize.evaluate_lines(["ab cd", "ef"], ["ab cx", "ef", "extra"])
    assert ev["char_edits"] == 1 + 5 and ev["ref_chars"] == 7 and ev["n_lines"] == 3


def test_protocol_conformance():
    for r in (recognize.NullRecognizer(), recognize.GroundTruthRecognizer({"lines": []}),
              recognize.MLKitDigitalInkAdapter()):
        assert isinstance(r, recognize.Recognizer)


def test_null_recogniser_layer(loaded):
    store, ids = loaded
    layer = recognize.run_recognizer(store, ids["a"], recognize.NullRecognizer())
    assert layer["payload"]["spans"] == [] and layer["created_by"].startswith("penapp.recognize.null@")
    validate(layer, "derived_layer")


def test_ground_truth_passthrough_links_words_to_strokes(loaded, session_a):
    store, ids = loaded
    rec = store.list_layers(note_id=ids["a"], kind="recognition")[-1]
    orig = store.original_for_note(ids["a"])
    words = [s for s in rec["payload"]["spans"] if s["level"] == "word"]
    truth = [w for l in session_a.truth["lines"] for w in l["words"]]
    assert [w["text"] for w in words] == [w["text"] for w in truth]
    assert [w["stroke_ranges"] for w in words] == [w["stroke_ranges"] for w in truth]
    w = words[4]
    idx = orig.indices_for(range(w["stroke_ranges"][0][0], w["stroke_ranges"][0][1] + 1))
    s = orig.samples[idx]
    assert w["bbox_um"] == [s["x_um"].min(), s["y_um"].min(), s["x_um"].max(), s["y_um"].max()]
    assert any(i["type"] == "external_file" for i in rec["inputs"])     # the transcript file is provenance
    assert "GROUND-TRUTH PASSTHROUGH" in rec["payload"]["evidence_status"]


def test_ground_truth_drops_strokes_lost_to_corruption(session_a):
    p = logfmt.read_log(session_a.encode())
    keep = p.strokes[p.strokes["stroke_id"] != 0]            # stroke 0 ('b' stem) lost
    res = recognize.GroundTruthRecognizer(session_a.truth).recognize(OriginalLayer(keep.tobytes()))
    first = next(s for s in res.spans if s["level"] == "word")
    assert first["stroke_ranges"][0][0] == 1 and first["text"] == "buy"


def test_error_injection_is_deterministic_and_hits_target_cer(session_a):
    orig = OriginalLayer(logfmt.read_log(session_a.encode()).stroke_payload)
    base = recognize.GroundTruthRecognizer(session_a.truth)
    same = recognize.ErrorInjectingRecognizer(base, 0.0).recognize(orig)
    assert [s["text"] for s in same.spans] == [s["text"] for s in base.recognize(orig).spans]
    a = recognize.ErrorInjectingRecognizer(base, 0.2, seed=5).recognize(orig)
    b = recognize.ErrorInjectingRecognizer(base, 0.2, seed=5).recognize(orig)
    assert [s["text"] for s in a.spans] == [s["text"] for s in b.spans]
    cers = [recognize.ErrorInjectingRecognizer(base, 0.2, seed=k).recognize(orig).params["achieved_cer_vs_base"]
            for k in range(30)]
    assert 0.12 < float(np.mean(cers)) < 0.28
    assert all(s["stroke_ranges"] for s in a.spans)                    # links survive corruption


def test_mlkit_adapter_mapping_and_guards(session_a):
    orig = OriginalLayer(logfmt.read_log(session_a.encode()).stroke_payload)
    ink = recognize.MLKitDigitalInkAdapter.to_ink(orig, [0, 1], start_unix_ms=1_000_000)
    assert [s["stroke_id"] for s in ink["strokes"]] == [0, 1]
    s0 = orig.samples[orig.stroke_runs[0][1]]
    p0 = ink["strokes"][0]["points"][0]
    assert p0 == {"x": s0["x_um"] / 1000.0, "y": -s0["y_um"] / 1000.0, "t": 1_000_000 + int(s0["t_ms"])}
    ts = [p["t"] for p in ink["strokes"][0]["points"]]
    assert ts == sorted(ts)
    assert recognize.MLKitDigitalInkAdapter.writing_area([0, 0, 5000, 2000]) == {"width": 5.0, "height": 2.0}
    with pytest.raises(PermissionError):
        recognize.MLKitDigitalInkAdapter().recognize(orig)
    with pytest.raises(NotImplementedError):
        recognize.MLKitDigitalInkAdapter(user_consented_to_vendor_metrics=True).recognize(orig)
