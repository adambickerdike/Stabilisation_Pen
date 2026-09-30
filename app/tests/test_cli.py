"""Command line: python -m penapp import|render|search|ask|fidelity (+ list, verify, edit)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from penapp.cli import main

from conftest import APP, TRACE


def _run(capsys, *argv):
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_import_search_ask_render_list_verify_edit(tmp_path, files, capsys):
    st = str(tmp_path / "store")
    code, out = _run(capsys, "--store", st, "import", str(files["a"]), str(files["b"]), "--json")
    assert code == 0
    summary = json.loads(out)
    assert [s["recognizer"].split("@")[0] for s in summary] == ["penapp.recognize.groundtruth"] * 2
    nid = summary[0]["note_id"]
    code, out = _run(capsys, "--store", st, "search", "library", "--json")
    hit = json.loads(out)[0]
    assert hit["note_id"] == nid and hit["matched_stroke_ranges"] and hit["words"][0]["bbox_um"]
    code, out = _run(capsys, "--store", st, "ask", "When should I return the library books?")
    assert "return library books by friday" in out and "strokes" in out
    code, out = _run(capsys, "--store", st, "ask", "What is the wifi password?", "--json")
    assert json.loads(out)["reason"] == "no_supporting_notes"
    svg = tmp_path / "n.svg"
    assert _run(capsys, "--store", st, "render", nid, "-o", str(svg), "--overlay", "text", "--force-width")[0] == 0
    ET.parse(svg)
    code, out = _run(capsys, "--store", st, "list")
    assert nid in out and "ai_summary" in out
    code, out = _run(capsys, "--store", st, "edit", nid, "l1.w4", "saturday")
    assert out.strip().startswith("user_edit-")
    code, out = _run(capsys, "--store", st, "search", "saturday", "--json")
    assert json.loads(out)[0]["words"][0]["span_id"] == "l1.w4"
    code, out = _run(capsys, "--store", st, "verify")
    assert code == 0 and json.loads(out)["ok"]


def test_store_is_required(capsys, monkeypatch):
    monkeypatch.delenv("PENAPP_STORE", raising=False)
    with pytest.raises(SystemExit):
        main(["search", "x"])


@pytest.mark.skipif(not TRACE.exists(), reason="simulator traces not present")
def test_fidelity_command(tmp_path, capsys):
    out = tmp_path / "fid.json"
    code, text = _run(capsys, "fidelity", "--traces", str(TRACE), "-o", str(out), "--no-frechet")
    assert code == 0 and out.exists()
    res = json.loads(out.read_text())
    assert "format_point" in res["summary"] and res["interpretation"]


def test_module_entry_point(tmp_path, files):
    env = dict(os.environ, PYTHONPATH=str(APP), PENAPP_STORE=str(tmp_path / "s"))
    r = subprocess.run([sys.executable, "-m", "penapp", "import", str(files["a"])], env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, "-m", "penapp", "search", "plumber"], env=env, capture_output=True,
                       text=True, timeout=60)
    assert r.returncode == 0 and "plumber" in r.stdout


def test_proposal_review_acceptance_keeps_ink_and_reindexes(loaded, tmp_path, capsys):
    from penapp import recognize
    from penapp.notes import NoteStore, ValidationError
    from conftest import LINES_A, LINES_B
    store, ids = loaded
    nid = ids["a"]
    original = store.original_for_note(nid).payload
    base = store.list_layers(note_id=nid, kind="recognition")[-1]
    lines = []
    for line in [s for s in base["payload"]["spans"] if s["level"] == "line"]:
        words = [{"text": "libary" if w["text"] == "library" else w["text"],
                  "stroke_ranges": w["stroke_ranges"]}
                 for w in base["payload"]["spans"] if w.get("parent") == line["span_id"]]
        lines.append({"text": " ".join(w["text"] for w in words), "words": words})
    literal = recognize.run_recognizer(store, nid, recognize.GroundTruthRecognizer({"lines": lines}))
    corpus = tmp_path / "training.txt"
    corpus.write_text("\n".join((LINES_A + LINES_B) * 5 +
                              ["Buy milk & bread!", "Café orders; Friday?", "🖊️ ✨"]))
    proposal = tmp_path / "proposal.json"
    before_layers = len(store.list_layers(note_id=nid))
    code, out = _run(capsys, "--store", str(store.root), "propose-corrections", nid,
                     "--corpus", str(corpus), "--out", str(proposal))
    assert code == 0 and len(store.list_layers(note_id=nid)) == before_layers
    metadata = json.loads(proposal.read_text())["model"]
    assert metadata["corpus_lines"] == len((LINES_A + LINES_B) * 5) + 2
    assert metadata["corpus_sha256"] != metadata["normalized_corpus_sha256"]
    choice = next(c for c in json.loads(out)["choices"] if c["observed"] == "libary")
    assert choice["suggested"] == "library"
    assert store.effective_text(nid)["recognition_layer_id"] == literal["layer_id"]
    with pytest.raises(SystemExit):
        main(["--store", str(store.root), "accept-corrections", str(proposal)])
    capsys.readouterr()
    assert len(store.list_layers(note_id=nid)) == before_layers
    code, out = _run(capsys, "--store", str(store.root), "accept-corrections", str(proposal),
                     "--span-id", choice["span_id"])
    assert code == 0 and json.loads(out)["user_edit_layer"].startswith("user_edit-")
    # CLI commands open their own single-writer NoteStore. Refresh the fixture's
    # read cache before inspecting files persisted by that separate instance.
    store = NoteStore(store.root)
    assert store.get_layer(literal["layer_id"]) == literal
    assert store.original_for_note(nid).payload == original
    code, out = _run(capsys, "--store", str(store.root), "search", "library", "--json")
    assert code == 0 and any(h["note_id"] == nid for h in json.loads(out))
    with pytest.raises(ValidationError, match="stale"):
        main(["--store", str(store.root), "accept-corrections", str(proposal),
              "--span-id", choice["span_id"]])
    assert len(store.list_layers(note_id=nid)) == before_layers + 1


@pytest.mark.parametrize("content", ["\n \n", "🖊️ ✨\n"])
def test_proposal_rejects_empty_local_corpus(tmp_path, content):
    corpus = tmp_path / "empty.txt"
    corpus.write_text(content)
    out = tmp_path / "proposal.json"
    with pytest.raises(SystemExit, match="empty"):
        main(["--store", str(tmp_path / "store"), "propose-corrections", "unused-note",
              "--corpus", str(corpus), "--out", str(out)])
    assert not out.exists()
