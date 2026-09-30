"""Dataset absence and split membership must not silently select another population."""
import pytest
from realdata import library as L


def test_missing_licensed_pool_is_actionable(monkeypatch):
    monkeypatch.setattr(L.WL, "unipen_index", lambda: [])
    monkeypatch.setattr(L.WL, "unipen_writers", lambda *args: [])
    with pytest.raises(FileNotFoundError, match="licensed UNIPEN"):
        L.writing("test")
    with pytest.raises(FileNotFoundError, match="licensed UNIPEN"):
        L.RealWriter("unipen/0").write()


def test_explicit_writer_cannot_cross_split(monkeypatch):
    monkeypatch.setattr(L.WL, "unipen_index", lambda: [])
    monkeypatch.setattr(L.WL, "unipen_writers", lambda *args: ["test_writer"])
    with pytest.raises(ValueError, match="not in split"):
        L.writing("test", writer="tuning_writer")


def test_unknown_source_is_not_brush_fallback():
    with pytest.raises(ValueError, match="Unknown handwriting source"):
        L.writing(source="typo")


def test_a_notes_own_prefixed_writer_id_selects_that_writer(monkeypatch):
    """RealWritten.real['writer'] carries the source prefix ('unipen/...'); passing it back must select the same writer
    (study F's per-writer calibration does this), while a writer from another split is still refused."""
    seen = []
    monkeypatch.setattr(L.WL, "unipen_index", lambda: [])
    monkeypatch.setattr(L.WL, "unipen_writers", lambda *args: ["hpp/hpp2/hpb2-an.dat"])
    monkeypatch.setattr(L.WL, "unipen_note", lambda w, **kw: seen.append(w) or "note")
    assert L.writing("test", writer="unipen/hpp/hpp2/hpb2-an.dat") == "note"
    assert seen == ["hpp/hpp2/hpb2-an.dat"]
    with pytest.raises(ValueError, match="not in split"):
        L.writing("test", writer="unipen/hpp/hpp2/hpb2-zz.dat")
