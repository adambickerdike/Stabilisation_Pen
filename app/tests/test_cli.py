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
