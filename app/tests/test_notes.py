"""Note store: immutable content-addressed original, derived layers, provenance, schema."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat

import numpy as np
import pytest

from penapp import logfmt
from penapp.notes import (ImmutableLayerError, ImmutableOriginalError, IntegrityError, NoteStore, OriginalLayer,
                          ValidationError, load_schema, schema_errors, validate)


def _import(store, path):
    data = path.read_bytes()
    return store.import_log(logfmt.read_log(data), source_name=path.name,
                            source_sha256=hashlib.sha256(data).hexdigest())


def test_schema_is_a_valid_draft_2020_12_schema():
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(load_schema())


def test_content_address_is_sha256_of_logged_payloads(store, files):
    data = files["a"].read_bytes()
    # independent extraction: walk the records and concatenate the 0x02 payload bytes
    payloads = b"".join(data[o + 2:e - 2] for o, e, t in logfmt.iter_record_spans(data) if t == 0x02)
    note = _import(store, files["a"])
    assert note["original_sha256"] == hashlib.sha256(payloads).hexdigest()
    orig = store.get_original(note["original_sha256"])
    assert orig.payload == payloads
    assert orig.n_samples == len(payloads) // 20


def test_original_layer_refuses_every_modification(store, files):
    note = _import(store, files["a"])
    orig = store.get_original(note["original_sha256"])
    with pytest.raises(ImmutableOriginalError):
        orig._payload = b""
    with pytest.raises(ImmutableOriginalError):
        orig.anything = 1
    with pytest.raises(ImmutableOriginalError):
        del orig._payload
    with pytest.raises(ValueError):
        orig.samples["x_um"][0] = 123
    with pytest.raises(ValueError):
        orig.samples.flags.writeable = True
    with pytest.raises(ImmutableOriginalError):
        store.update_original(note["original_sha256"], b"")
    with pytest.raises(ImmutableOriginalError):
        store.delete_original(note["original_sha256"])
    with pytest.raises(ImmutableLayerError):
        store.update_layer("x")
    path = store.root / "originals" / f"{orig.sha256}.json"
    assert stat.S_IMODE(os.stat(path).st_mode) & 0o222 == 0          # read-only on disk
    copy_ = orig.samples.copy()                                        # copies are free to change
    copy_["x_um"][0] += 1
    assert OriginalLayer(copy_.tobytes()).sha256 != orig.sha256        # ... and become a *different* original


def test_put_original_is_idempotent_and_never_rewrites(store, files):
    note = _import(store, files["a"])
    path = store.root / "originals" / f"{note['original_sha256']}.json"
    before = (path.read_bytes(), os.stat(path).st_mtime_ns)
    again = _import(store, files["a"])
    assert again["note_id"] == note["note_id"]
    assert (path.read_bytes(), os.stat(path).st_mtime_ns) == before
    assert len(store.list_originals()) == 1 and len(store.list_notes()) == 1


def test_tampered_original_is_detected(store, files):
    note = _import(store, files["a"])
    sha = note["original_sha256"]
    path = store.root / "originals" / f"{sha}.json"
    obj = json.loads(path.read_text())
    obj["samples"][3][2] += 1
    os.chmod(path, 0o644)
    path.write_text(json.dumps(obj))
    fresh = NoteStore(store.root)
    with pytest.raises(IntegrityError):
        fresh.get_original(sha)
    rep = fresh.verify()
    assert not rep["ok"] and any(sha[:12] in p for p in rep["problems"])


def test_tampered_note_manifest_is_detected(store, files):
    note = _import(store, files["a"])
    path = store.root / "notes" / f"{note['note_id']}.json"
    obj = json.loads(path.read_text())
    obj["labels"] = []
    os.chmod(path, 0o644)
    path.write_text(json.dumps(obj))
    with pytest.raises(IntegrityError):
        store.get_note(note["note_id"])


def test_manifest_records_session_events_and_synthetic_label(store, files):
    note = _import(store, files["a"])
    assert note["labels"] == ["synthetic"]
    assert note["session"]["device_id"].isdigit()                    # u64 as a decimal string
    assert {e["name"] for e in note["events"]} >= {"PEN_DOWN", "PEN_UP", "MODE_CHANGE"}
    assert note["annotations"][0]["text"].startswith("SYNTHETIC")
    assert note["source"]["parse"]["bytes_skipped"] == 0
    validate(note, "note")


def _seg(store, nid):
    from penapp.capture import add_segmentation_layer
    return add_segmentation_layer(store, nid)


def test_derived_layer_has_icd_provenance_fields_and_stable_id(store, files):
    note = _import(store, files["a"])
    layer = _seg(store, note["note_id"])
    for k in ("layer_id", "kind", "created_by", "inputs", "created_utc"):
        assert layer[k]
    assert layer["created_by"].startswith("penapp.capture.segment@")
    assert layer["inputs"][0] == {"type": "original", "sha256": note["original_sha256"],
                                  "stroke_ranges": layer["inputs"][0]["stroke_ranges"]}
    again = _seg(store, note["note_id"])                     # identical content -> same id, stored once
    assert again["layer_id"] == layer["layer_id"]
    assert len(list((store.root / "layers").glob("*.json"))) == 1
    validate(layer, "derived_layer")


def test_add_layer_rejects_broken_links_and_provenance(store, files):
    note = _import(store, files["a"])
    nid, sha = note["note_id"], note["original_sha256"]
    ok_span = {"span_id": "l0", "level": "line", "text": "x", "stroke_ranges": [[0, 1]], "bbox_um": [0, 0, 1, 1]}
    base = dict(kind="recognition", note_ids=[nid], created_by="penapp.test@1",
                inputs=[{"type": "original", "sha256": sha}],
                payload={"language": "en", "evidence_status": "test", "spans": [ok_span]})
    store.add_layer(**base)
    bad = copy.deepcopy(base)
    bad["payload"]["spans"][0]["stroke_ranges"] = [[0, 99999]]          # strokes that do not exist
    with pytest.raises(ValidationError):
        store.add_layer(**bad)
    bad = copy.deepcopy(base)
    bad["payload"]["spans"][0]["stroke_ranges"] = []                    # a span without stroke links
    with pytest.raises(ValidationError):
        store.add_layer(**bad)
    with pytest.raises(ValidationError):
        store.add_layer(**{**base, "created_by": "somebody"})           # no algorithm@version
    with pytest.raises(ValidationError):
        store.add_layer(**{**base, "kind": "original"})
    with pytest.raises(ValidationError):
        store.add_layer(**{**base, "inputs": []})
    with pytest.raises(ValidationError):
        store.add_layer(**{**base, "inputs": [{"type": "original", "sha256": "0" * 64}]})
    with pytest.raises(ValidationError):
        store.add_layer(**{**base, "payload": {**base["payload"], "samples": []}})   # schema: no extra fields


def test_ai_summary_requires_citations_at_store_level(loaded):
    store, ids = loaded
    rec = store.list_layers(note_id=ids["a"], kind="recognition")[-1]
    sha = store.get_note(ids["a"])["original_sha256"]
    payload = {"question": "q?", "sentences": [{"text": "uncited claim", "citations": [], "support": 1.0}],
               "sources": [{"source_id": "S1", "note_id": ids["a"], "layer_ids": [rec["layer_id"]], "span_id": "l0",
                            "text": "t", "stroke_ranges": [[0, 1]], "bbox_um": [0, 0, 1, 1], "score": 1.0}],
               "llm": {"model_id": "m", "version": "1", "local": True, "deterministic": True},
               "validation": {}, "disclaimer": "d"}
    with pytest.raises(ValidationError):
        store.add_layer(kind="ai_summary", note_ids=[ids["a"]], created_by="penapp.grounded@0.1.0",
                        inputs=[{"type": "original", "sha256": sha}], payload=payload)


def test_assistant_output_cannot_feed_note_content_layers(loaded):
    from penapp.grounded import GroundedAssistant
    store, ids = loaded
    ans = GroundedAssistant(store).ask("When should I return the library books?")
    sha = store.get_note(ids["a"])["original_sha256"]
    with pytest.raises(ValidationError):
        store.add_layer(kind="recognition", note_ids=[ids["a"]], created_by="penapp.test@1",
                        inputs=[{"type": "original", "sha256": sha}, {"type": "layer", "layer_id": ans.layer_id}],
                        payload={"language": "en", "evidence_status": "x", "spans": []})


def test_user_edit_is_a_new_layer_that_keeps_stroke_links(loaded):
    store, ids = loaded
    rec = store.list_layers(note_id=ids["a"], kind="recognition")[-1]
    rec_file = (store.root / "layers" / f"{rec['layer_id']}.json").read_bytes()
    word = next(s for s in rec["payload"]["spans"] if s["level"] == "word" and s["text"] == "friday")
    edit = store.add_user_edit(ids["a"], {word["span_id"]: "saturday"})
    assert edit["created_by"] == "user" and edit["payload"]["edits"][0]["previous_text"] == "friday"
    assert edit["payload"]["edits"][0]["stroke_ranges"] == word["stroke_ranges"]
    eff = store.effective_text(ids["a"])
    line = next(s for s in eff["spans"] if s["span_id"] == word["parent"])
    assert line["text"] == "return library books by saturday"
    assert eff["user_edit_layer_ids"] == [edit["layer_id"]]
    assert (store.root / "layers" / f"{rec['layer_id']}.json").read_bytes() == rec_file   # recognition untouched
    with pytest.raises(ValidationError):
        store.add_user_edit(ids["a"], {"l9.w9": "nope"})


def test_user_edits_become_stale_after_new_recognition(loaded):
    from penapp import recognize
    store, ids = loaded
    store.add_user_edit(ids["a"], {"l0.w0": "sell"})
    recognize.run_recognizer(store, ids["a"], recognize.NullRecognizer())
    eff = store.effective_text(ids["a"])
    assert eff["recognizer"].startswith("penapp.recognize.null@") and eff["spans"] == []
    assert len(eff["stale_user_edit_layer_ids"]) == 1


def test_export_bundle_validates_and_broken_bundle_fails(loaded):
    store, _ = loaded
    b = store.export_bundle()                     # validated on export (envelope + sampled rows)
    assert {l["kind"] for l in b["layers"]} >= {"segmentation", "recognition"}
    assert len(b["notes"]) == len(b["originals"]) == 2
    # full-schema checks on a reduced copy (per-row jsonschema validation of every sample is slow)
    small = copy.deepcopy({**b, "originals": [{**o, "samples": o["samples"][:50]} for o in b["originals"]]})
    assert not schema_errors(small)
    broken = copy.deepcopy(small)
    del broken["layers"][0]["created_by"]
    assert schema_errors(broken)
    broken = copy.deepcopy(small)
    broken["originals"][0]["samples"][0][4] = -1           # force is u16
    assert schema_errors(broken)


def test_verify_ok_and_purge_requires_confirmation(loaded):
    store, ids = loaded
    assert store.verify()["ok"]
    with pytest.raises(Exception):
        store.purge_note(ids["a"], confirm="yes")
    rep = store.purge_note(ids["a"], confirm=ids["a"])
    assert rep["original_removed"] and rep["layers_removed"]
    assert [n["note_id"] for n in store.list_notes()] == [ids["b"]]
    assert store.verify()["ok"]


def test_original_from_json_rejects_out_of_range_rows(store, files):
    note = _import(store, files["a"])
    obj = store.get_original(note["original_sha256"]).to_json()
    obj["samples"][0][5] = 999
    with pytest.raises(IntegrityError):
        OriginalLayer.from_json(obj)
    assert np.frombuffer(store.get_original(note["original_sha256"]).payload, dtype=logfmt.STROKE_DTYPE).size
