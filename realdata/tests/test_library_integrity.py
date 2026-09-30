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
