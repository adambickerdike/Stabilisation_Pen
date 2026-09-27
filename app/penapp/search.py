"""SQLite FTS5 index over the recognised text of every note.

The index is a derived, rebuildable cache (``<store>/index.sqlite``); the note
store stays the source of truth.  One FTS row per recognised *line* of a
note's effective text (latest recognition layer + user edits).  Each hit
returns the line and the matched words with their stroke-id ranges and page
bounding boxes (page frame, micrometres), plus the layer ids the text came
from.  Assistant output (``ai_summary``) is never indexed, so generated text
cannot be retrieved later as if it were a note.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from ._util import ids_from_ranges, ranges_from_ids

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lines(
    row_id          INTEGER PRIMARY KEY,
    note_id         TEXT NOT NULL,
    original_sha256 TEXT NOT NULL,
    layer_ids       TEXT NOT NULL,
    span_id         TEXT NOT NULL,
    text            TEXT NOT NULL,
    stroke_ranges   TEXT NOT NULL,
    bbox_um         TEXT NOT NULL,
    words           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS lines_note ON lines(note_id);
CREATE VIRTUAL TABLE IF NOT EXISTS lines_fts USING fts5(text, tokenize = 'porter unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS indexed_notes(note_id TEXT PRIMARY KEY, original_sha256 TEXT NOT NULL,
                                         layer_ids TEXT NOT NULL);
"""
_TOKEN = re.compile(r"\w+", re.UNICODE)
_CTRL = re.compile(r"[\x00-\x1f\x7f]")
_OPEN, _CLOSE = "\x02", "\x03"


@dataclass
class WordHit:
    span_id: str
    text: str
    stroke_ranges: List[List[int]]
    bbox_um: List[float]


@dataclass
class SearchHit:
    note_id: str
    original_sha256: str
    layer_ids: List[str]
    span_id: str
    text: str
    score: float
    stroke_ranges: List[List[int]]
    bbox_um: List[float]
    words: List[WordHit] = field(default_factory=list)

    @property
    def matched_stroke_ranges(self) -> List[List[int]]:
        if not self.words:
            return self.stroke_ranges
        return ranges_from_ids(i for w in self.words for i in ids_from_ranges(w.stroke_ranges))

    def to_json(self) -> dict:
        d = asdict(self)
        d["matched_stroke_ranges"] = self.matched_stroke_ranges
        return d


def build_match_expression(query: str, *, mode: str = "all", prefix: bool = False) -> Optional[str]:
    """Translate free text into a safe FTS5 expression.

    Bare words become quoted terms (so FTS5 operators and punctuation in user
    input are inert); ``"double quoted"`` text becomes a phrase.  Terms are
    joined with AND (``mode="all"``) or OR (``mode="any"``).
    """
    parts = []
    for m in re.finditer(r'"([^"]*)"|(\S+)', query):
        if m.group(1) is not None:
            toks = _TOKEN.findall(m.group(1))
            if toks:
                parts.append('"' + " ".join(toks) + '"')
        else:
            for tok in _TOKEN.findall(m.group(2)):
                parts.append(f'"{tok}"' + ("*" if prefix else ""))
    if not parts:
        return None
    if mode not in ("all", "any"):
        raise ValueError("mode must be 'all' or 'any'")
    return (" AND " if mode == "all" else " OR ").join(parts)


def _marked(highlighted: str):
    """Character ranges of the original text wrapped in highlight markers."""
    out, pos, start = [], 0, None
    for ch in highlighted:
        if ch == _OPEN:
            start = pos
        elif ch == _CLOSE:
            out.append((start, pos))
            start = None
        else:
            pos += 1
    return out


class SearchIndex:
    def __init__(self, path):
        self.path = Path(path)
        self.con = sqlite3.connect(str(self.path))
        self.con.executescript(_SCHEMA)

    @classmethod
    def for_store(cls, store) -> "SearchIndex":
        return cls(store.index_path)

    def close(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -------------------------------------------------------------- writing
    def remove_note(self, note_id: str) -> None:
        with self.con:
            rows = [r[0] for r in self.con.execute("SELECT row_id FROM lines WHERE note_id = ?", (note_id,))]
            self.con.executemany("DELETE FROM lines_fts WHERE rowid = ?", [(r,) for r in rows])
            self.con.execute("DELETE FROM lines WHERE note_id = ?", (note_id,))
            self.con.execute("DELETE FROM indexed_notes WHERE note_id = ?", (note_id,))

    def index_note(self, store, note_id: str) -> int:
        """(Re)index the effective text of one note; returns the number of lines."""
        self.remove_note(note_id)
        eff = store.effective_text(note_id)
        if eff is None:
            return 0
        layer_ids = [eff["recognition_layer_id"]] + eff["user_edit_layer_ids"]
        words_of = {}
        for s in eff["spans"]:
            if s["level"] == "word" and s.get("parent") and not s.get("superseded"):
                words_of.setdefault(s["parent"], []).append(s)
        n = 0
        with self.con:
            for s in eff["spans"]:
                if s["level"] != "line":
                    continue
                words = []
                pieces = []
                pos = 0
                for w in words_of.get(s["span_id"], []):
                    t = _CTRL.sub(" ", w["text"]).strip()
                    if not t:
                        continue
                    if pieces:
                        pos += 1
                    words.append({"span_id": w["span_id"], "text": t, "start": pos, "end": pos + len(t),
                                  "stroke_ranges": w["stroke_ranges"], "bbox_um": w["bbox_um"]})
                    pieces.append(t)
                    pos += len(t)
                text = " ".join(pieces) if words else _CTRL.sub(" ", s["text"]).strip()
                if not text:
                    continue
                cur = self.con.execute(
                    "INSERT INTO lines(note_id, original_sha256, layer_ids, span_id, text, stroke_ranges, bbox_um, words)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (note_id, eff["original_sha256"], json.dumps(layer_ids), s["span_id"], text,
                     json.dumps(s["stroke_ranges"]), json.dumps(s["bbox_um"]), json.dumps(words)))
                self.con.execute("INSERT INTO lines_fts(rowid, text) VALUES (?, ?)", (cur.lastrowid, text))
                n += 1
            self.con.execute("INSERT OR REPLACE INTO indexed_notes VALUES (?,?,?)",
                             (note_id, eff["original_sha256"], json.dumps(layer_ids)))
        return n

    def rebuild(self, store) -> int:
        with self.con:
            self.con.execute("DELETE FROM lines_fts")
            self.con.execute("DELETE FROM lines")
            self.con.execute("DELETE FROM indexed_notes")
        return sum(self.index_note(store, n["note_id"]) for n in store.list_notes())

    def indexed_layer_ids(self, note_id: str) -> Optional[List[str]]:
        r = self.con.execute("SELECT layer_ids FROM indexed_notes WHERE note_id = ?", (note_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def is_stale(self, store, note_id: str) -> bool:
        eff = store.effective_text(note_id)
        want = None if eff is None else [eff["recognition_layer_id"]] + eff["user_edit_layer_ids"]
        return self.indexed_layer_ids(note_id) != want

    # -------------------------------------------------------------- reading
    def search(self, query: str, *, limit: int = 20, mode: str = "all", prefix: bool = False,
               note_ids: Optional[Sequence[str]] = None) -> List[SearchHit]:
        expr = build_match_expression(query, mode=mode, prefix=prefix)
        if expr is None:
            return []
        sql = ("SELECT l.note_id, l.original_sha256, l.layer_ids, l.span_id, l.text, l.stroke_ranges, l.bbox_um,"
               " l.words, bm25(lines_fts) AS rank, highlight(lines_fts, 0, char(2), char(3))"
               " FROM lines_fts JOIN lines l ON l.row_id = lines_fts.rowid WHERE lines_fts MATCH ?")
        args: list = [expr]
        if note_ids:
            sql += " AND l.note_id IN (%s)" % ",".join("?" * len(note_ids))
            args.extend(note_ids)
        sql += " ORDER BY rank, l.note_id, l.span_id LIMIT ?"
        args.append(int(limit))
        hits = []
        for (nid, sha, lids, sid, text, sr, bb, words, rank, hl) in self.con.execute(sql, args):
            marks = _marked(hl)
            matched = [WordHit(w["span_id"], w["text"], w["stroke_ranges"], w["bbox_um"])
                       for w in json.loads(words)
                       if any(a < w["end"] and w["start"] < b for a, b in marks)]
            hits.append(SearchHit(nid, sha, json.loads(lids), sid, text, round(-float(rank), 6),
                                  json.loads(sr), json.loads(bb), matched))
        return hits

    def count_lines(self) -> int:
        return int(self.con.execute("SELECT count(*) FROM lines").fetchone()[0])
