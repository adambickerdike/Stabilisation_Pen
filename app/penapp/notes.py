"""Note store (ICD v1.0 section 4.5): immutable original layer + derived layers.

On-disk layout (a local directory of JSON documents; SQLite is used only for
the rebuildable search index, see ``search.py``)::

    <root>/store.json                   format marker
    <root>/originals/<sha256>.json      original layers (write-once, mode 0444)
    <root>/notes/<note_id>.json         note manifests (write-once, mode 0444)
    <root>/layers/<layer_id>.json       derived layers (write-once, mode 0444)

Guarantees
----------
* The original layer is the list of stroke samples exactly as logged.  Its
  address is SHA-256 over the concatenated 20-byte ICD 0x02 payloads in log
  order; it is re-verified on every load (``IntegrityError`` on mismatch).
* Any attempt to modify an original raises: ``OriginalLayer`` refuses
  attribute assignment (``ImmutableOriginalError``), its sample array is a
  read-only view of an immutable ``bytes`` object (numpy raises ``ValueError``
  and refuses to re-enable writing), the store has no update path and its
  ``update_original``/``delete_original`` guards raise, files are created
  exclusively and made read-only.
* Derived layers (``recognition``, ``segmentation``, ``hand_path_estimate``,
  ``user_edit``, ``ai_summary``) are append-only, carry ``layer_id``, ``kind``,
  ``created_by``, ``inputs`` and ``created_utc``, and every span links to the
  stroke ids it came from.  Links are checked against the original on write.
* Every object is validated against ``data/schema/note_store.schema.json``.
* ``purge_note`` (explicit, confirmed deletion of a whole note) exists for the
  user's right to erase their data; it is deletion, not modification.
"""
from __future__ import annotations

import copy
import json
import os
import re
import uuid
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import numpy as np

from . import __version__
from ._util import (REPO_ROOT, canonical_json, ids_from_ranges, ranges_from_ids, sha256_hex,
                    utc_now)
from .logfmt import STROKE_DTYPE, ParsedLog, RecordType

SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "note_store.schema.json"
LAYER_KINDS = ("recognition", "segmentation", "hand_path_estimate", "user_edit", "ai_summary")
COLUMNS = ["t_ms", "stroke_id", "x_um", "y_um", "force_mN", "theta_raw", "phi_raw"]
HASH_SCOPE = ("sha256 over concatenated ICD 1.0 section 4.3 stroke-sample payloads "
              "(20 B, little-endian) in log order")
CREATED_BY_RE = re.compile(r"^(user|[a-z][a-z0-9_.\-]*@[0-9][0-9A-Za-z.\-+]*)$")
IMPORTER_ID = f"penapp.import@{__version__}"


class NoteStoreError(Exception):
    pass


class ImmutableOriginalError(NoteStoreError, PermissionError):
    """Raised on any attempt to modify an original stroke layer."""


class ImmutableLayerError(NoteStoreError, PermissionError):
    """Raised on any attempt to modify a stored derived layer or note manifest."""


class IntegrityError(NoteStoreError):
    """Stored content does not match its content address or digest."""


class ValidationError(NoteStoreError, ValueError):
    """An object violates the schema or a store invariant (links, provenance)."""


# ------------------------------------------------------------------ schema
@lru_cache(maxsize=1)
def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def _validator(defname: Optional[str]):
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:          # pragma: no cover - jsonschema is a test dependency
        return None
    schema = load_schema()
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    target = schema if defname is None else {"$ref": f"{schema['$id']}#/$defs/{defname}"}
    return Draft202012Validator(target, registry=registry)


def schema_errors(obj, defname: Optional[str] = None) -> List[str]:
    """Schema violations of ``obj`` against ``$defs/<defname>`` (root if None)."""
    v = _validator(defname)
    if v is None:                 # pragma: no cover
        return []
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(obj), key=lambda e: list(map(str, e.absolute_path)))]


def validate(obj, defname: Optional[str] = None) -> None:
    errs = schema_errors(obj, defname)
    if errs:
        raise ValidationError(f"{defname or 'bundle'} fails note_store.schema.json: " + "; ".join(errs[:5]))


def schema_available() -> bool:
    return _validator(None) is not None


# ---------------------------------------------------------- original layer
class OriginalLayer:
    """Immutable view of the logged stroke samples of one session."""

    __slots__ = ("_payload", "_sha256", "_samples", "_runs", "_ids")

    def __init__(self, payload: bytes):
        payload = bytes(payload)
        if len(payload) % STROKE_DTYPE.itemsize:
            raise ValidationError(f"payload length {len(payload)} is not a multiple of 20 B")
        samples = np.frombuffer(payload, dtype=STROKE_DTYPE)   # read-only view of immutable bytes
        runs = []
        sid = samples["stroke_id"]
        if len(sid):
            cut = np.flatnonzero(np.diff(sid.astype(np.int64)) != 0) + 1
            starts = np.r_[0, cut]
            stops = np.r_[cut, len(sid)]
            runs = [(int(sid[a]), int(a), int(b)) for a, b in zip(starts, stops)]
        object.__setattr__(self, "_payload", payload)
        object.__setattr__(self, "_sha256", sha256_hex(payload))
        object.__setattr__(self, "_samples", samples)
        object.__setattr__(self, "_runs", tuple(runs))
        object.__setattr__(self, "_ids", frozenset(int(s) for s in np.unique(sid)))

    # immutability ---------------------------------------------------------
    def __setattr__(self, key, value):
        raise ImmutableOriginalError("original stroke layers are immutable; derive a new layer instead")

    def __delattr__(self, key):
        raise ImmutableOriginalError("original stroke layers are immutable")

    def __reduce__(self):
        return (OriginalLayer, (self._payload,))

    # accessors ------------------------------------------------------------
    @property
    def payload(self) -> bytes:
        return self._payload

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def samples(self) -> np.ndarray:
        """Structured read-only array (fields as ``logfmt.STROKE_DTYPE``)."""
        return self._samples

    @property
    def n_samples(self) -> int:
        return int(len(self._samples))

    @property
    def stroke_runs(self):
        """(stroke_id, start, stop) for each contiguous run of equal stroke_id."""
        return self._runs

    @property
    def stroke_ids(self) -> frozenset:
        return self._ids

    def stroke_slices(self) -> Dict[int, List[slice]]:
        out: Dict[int, List[slice]] = defaultdict(list)
        for sid, a, b in self._runs:
            out[sid].append(slice(a, b))
        return dict(out)

    def indices_for(self, stroke_ids: Iterable[int]) -> np.ndarray:
        want = np.fromiter((int(s) for s in stroke_ids), dtype=np.int64)
        return np.flatnonzero(np.isin(self._samples["stroke_id"].astype(np.int64), want))

    def xy_um(self, idx=None) -> np.ndarray:
        s = self._samples if idx is None else self._samples[idx]
        return np.column_stack([s["x_um"], s["y_um"]]).astype(np.int64)

    def bbox_um(self, stroke_ids: Iterable[int]) -> List[int]:
        idx = self.indices_for(stroke_ids)
        if not len(idx):
            raise ValidationError("no samples for the requested stroke ids")
        s = self._samples[idx]
        return [int(s["x_um"].min()), int(s["y_um"].min()), int(s["x_um"].max()), int(s["y_um"].max())]

    def check_ranges(self, ranges: Sequence[Sequence[int]], where: str = "") -> None:
        for a, b in ranges:
            if b < a:
                raise ValidationError(f"{where}: invalid stroke range [{a}, {b}]")
        missing = [i for i in ids_from_ranges(ranges) if i not in self._ids]
        if missing:
            raise ValidationError(f"{where}: stroke ids {missing[:5]} not present in original {self.sha256[:12]}")

    # serialisation --------------------------------------------------------
    def to_json(self) -> dict:
        s = self._samples
        rows = np.column_stack([s[c].astype(np.int64) for c in COLUMNS]).tolist() if len(s) else []
        return {"object": "original_layer", "schema_version": 1, "icd_version": "1.0",
                "sha256": self.sha256, "hash_scope": HASH_SCOPE, "n_samples": self.n_samples,
                "columns": list(COLUMNS), "samples": rows}

    @classmethod
    def from_json(cls, obj: dict, *, expected_sha256: Optional[str] = None) -> "OriginalLayer":
        if obj.get("columns") != COLUMNS:
            raise IntegrityError("original layer columns differ from the ICD order")
        rows = obj.get("samples", [])
        arr = np.zeros(len(rows), dtype=STROKE_DTYPE)
        if rows:
            m = np.asarray(rows, dtype=np.int64)
            if m.ndim != 2 or m.shape[1] != len(COLUMNS):
                raise IntegrityError("original layer rows must have 7 integers")
            for k, c in enumerate(COLUMNS):
                info = np.iinfo(STROKE_DTYPE[c])
                if m[:, k].min() < info.min or m[:, k].max() > info.max:
                    raise IntegrityError(f"column {c} out of range for its ICD type")
                arr[c] = m[:, k]
        layer = cls(arr.tobytes())
        declared = obj.get("sha256")
        if layer.sha256 != declared or (expected_sha256 and layer.sha256 != expected_sha256):
            raise IntegrityError(f"original layer content hash {layer.sha256} does not match its address "
                                 f"{expected_sha256 or declared}")
        if obj.get("n_samples") != layer.n_samples:
            raise IntegrityError("n_samples does not match the sample rows")
        return layer


# ------------------------------------------------------------ JSON writing
def pretty_json(obj, indent: int = 1, _level: int = 0) -> str:
    """Readable JSON with scalar-only lists on one line (rows stay one per line)."""
    pad = " " * (indent * (_level + 1))
    end = " " * (indent * _level)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {pretty_json(v, indent, _level + 1)}"
                 for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + end + "}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(not isinstance(v, (dict, list)) for v in obj):
            return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        return "[\n" + ",\n".join(pad + pretty_json(v, indent, _level + 1) for v in obj) + "\n" + end + "]"
    return json.dumps(obj, ensure_ascii=False, allow_nan=False)


def _write_once(path: Path, data: bytes) -> bool:
    """Create ``path`` atomically and read-only unless it already exists."""
    if path.exists():
        return False
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with open(tmp, "xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o444)
        try:
            os.link(tmp, path)            # atomic; fails if the target exists
        except FileExistsError:
            return False
        except OSError:                   # pragma: no cover - filesystems without hard links
            if path.exists():
                return False
            os.replace(tmp, path)
        return True
    finally:
        if tmp.exists():
            tmp.unlink()


def _digest(obj: dict) -> str:
    body = {k: v for k, v in obj.items() if k != "digest"}
    return sha256_hex(canonical_json(body))


def layer_id_for(kind: str, note_ids, created_by: str, inputs, params, payload) -> str:
    body = {"kind": kind, "note_ids": list(note_ids), "created_by": created_by, "inputs": inputs,
            "params": params, "payload": payload}
    return f"{kind}-{sha256_hex(canonical_json(body))[:16]}"


# ------------------------------------------------------------------ store
class NoteStore:
    FORMAT = "penapp.note_store"
    VERSION = 1

    def __init__(self, root, *, clock: Callable[[], str] = utc_now, create: bool = True):
        self.root = Path(root)
        self.clock = clock
        marker = self.root / "store.json"
        if not marker.exists():
            if not create:
                raise NoteStoreError(f"no note store at {self.root}")
            for d in ("originals", "notes", "layers"):
                (self.root / d).mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"format": self.FORMAT, "version": self.VERSION,
                                          "schema": "data/schema/note_store.schema.json"}, indent=1) + "\n")
        else:
            meta = json.loads(marker.read_text())
            if meta.get("format") != self.FORMAT or meta.get("version") != self.VERSION:
                raise NoteStoreError(f"unsupported store format {meta}")
        self._orig_cache: Dict[str, OriginalLayer] = {}
        self._layer_cache: Optional[Dict[str, dict]] = None

    # paths -----------------------------------------------------------------
    def _orig_path(self, sha: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", sha or ""):
            raise ValidationError(f"not a sha256 address: {sha!r}")
        return self.root / "originals" / f"{sha}.json"

    def _note_path(self, note_id: str) -> Path:
        if not re.fullmatch(r"note-[0-9a-f]{16}", note_id or ""):
            raise ValidationError(f"not a note id: {note_id!r}")
        return self.root / "notes" / f"{note_id}.json"

    def _layer_path(self, layer_id: str) -> Path:
        if not re.fullmatch(r"(%s)-[0-9a-f]{16}" % "|".join(LAYER_KINDS), layer_id or ""):
            raise ValidationError(f"not a layer id: {layer_id!r}")
        return self.root / "layers" / f"{layer_id}.json"

    @property
    def index_path(self) -> Path:
        return self.root / "index.sqlite"

    # originals ---------------------------------------------------------------
    def put_original(self, payload) -> OriginalLayer:
        """Store an original layer (idempotent; never overwrites)."""
        layer = payload if isinstance(payload, OriginalLayer) else OriginalLayer(payload)
        obj = layer.to_json()
        validate(obj, "original_layer")
        path = self._orig_path(layer.sha256)
        if not _write_once(path, pretty_json(obj).encode("utf-8") + b"\n"):
            existing = self.get_original(layer.sha256)       # verifies content
            if existing.payload != layer.payload:           # pragma: no cover - needs a SHA-256 collision
                raise IntegrityError("content address collision")
            return existing
        self._orig_cache[layer.sha256] = layer
        return layer

    def get_original(self, sha: str, *, use_cache: bool = True) -> OriginalLayer:
        if use_cache and sha in self._orig_cache:
            return self._orig_cache[sha]
        path = self._orig_path(sha)
        if not path.exists():
            raise NoteStoreError(f"original {sha} not in store")
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise IntegrityError(f"original {sha[:12]} is not valid JSON: {e}") from e
        layer = OriginalLayer.from_json(obj, expected_sha256=sha)
        self._orig_cache[sha] = layer
        return layer

    def update_original(self, *_a, **_k):
        raise ImmutableOriginalError("original stroke layers cannot be modified (ICD 4.5); add a derived layer")

    def delete_original(self, *_a, **_k):
        raise ImmutableOriginalError("original stroke layers cannot be deleted individually; "
                                     "use purge_note(note_id, confirm=note_id) to erase a whole note")

    def update_layer(self, *_a, **_k):
        raise ImmutableLayerError("derived layers are append-only; add a new layer (e.g. user_edit)")

    def list_originals(self) -> List[str]:
        return sorted(p.stem for p in (self.root / "originals").glob("*.json"))

    # notes -----------------------------------------------------------------
    @staticmethod
    def note_id_for(device_id: int, session_id: int, original_sha: str) -> str:
        return "note-" + sha256_hex(f"{int(device_id)}:{int(session_id)}:{original_sha}".encode())[:16]

    def import_log(self, parsed: ParsedLog, *, source_name: str, source_sha256: str,
                   labels: Sequence[str] = ()) -> dict:
        """Create the original layer and the note manifest for one parsed log."""
        orig = self.put_original(parsed.stroke_payload)
        h = parsed.header
        note_id = self.note_id_for(h.device_id, h.session_id, orig.sha256)
        path = self._note_path(note_id)
        if path.exists():
            return self.get_note(note_id)
        annotations = []
        for off, rec in parsed.raw:
            if rec.rtype != RecordType.ANNOTATION:
                continue
            txt = rec.text
            annotations.append({"offset": off, "text": txt} if txt is not None
                               else {"offset": off, "payload_hex": rec.payload.hex()})
        lab = list(dict.fromkeys(labels))
        if any((a.get("text") or "").startswith("SYNTHETIC") for a in annotations) and "synthetic" not in lab:
            lab.append("synthetic")
        parse = parsed.summary()
        parse["stroke_semantics"] = stroke_semantic_checks(orig)
        manifest = {
            "object": "note", "schema_version": 1, "note_id": note_id, "original_sha256": orig.sha256,
            "session": h.to_json(),
            "source": {"file_name": source_name, "file_sha256": source_sha256, "file_bytes": parsed.n_bytes,
                       "parse": parse},
            "imported_utc": self.clock(), "imported_by": IMPORTER_ID, "labels": lab,
            "events": [{"t_us": int(t), "code": int(ev.code), "name": ev.name, "arg": int(ev.arg)}
                       for _, ev, t in parsed.events],
            "annotations": annotations,
        }
        manifest["digest"] = _digest(manifest)
        validate(manifest, "note")
        if not _write_once(path, pretty_json(manifest).encode("utf-8") + b"\n"):
            return self.get_note(note_id)
        return copy.deepcopy(manifest)

    def get_note(self, note_id: str) -> dict:
        path = self._note_path(note_id)
        if not path.exists():
            raise NoteStoreError(f"note {note_id} not in store")
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("digest") != _digest(obj):
            raise IntegrityError(f"note manifest {note_id} digest mismatch")
        return obj

    def list_notes(self) -> List[dict]:
        return [self.get_note(p.stem) for p in sorted((self.root / "notes").glob("note-*.json"))]

    def original_for_note(self, note_id: str) -> OriginalLayer:
        return self.get_original(self.get_note(note_id)["original_sha256"])

    # derived layers --------------------------------------------------------
    def _load_layers(self) -> Dict[str, dict]:
        if self._layer_cache is None:
            cache = {}
            for p in sorted((self.root / "layers").glob("*.json")):
                cache[p.stem] = self._read_layer(p.stem)
            self._layer_cache = cache
        return self._layer_cache

    def _read_layer(self, layer_id: str) -> dict:
        path = self._layer_path(layer_id)
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("digest") != _digest(obj):
            raise IntegrityError(f"layer {layer_id} digest mismatch")
        if layer_id_for(obj["kind"], obj["note_ids"], obj["created_by"], obj["inputs"], obj["params"],
                        obj["payload"]) != layer_id:
            raise IntegrityError(f"layer {layer_id} content does not match its id")
        return obj

    def get_layer(self, layer_id: str) -> dict:
        layers = self._load_layers()
        if layer_id not in layers:
            raise NoteStoreError(f"layer {layer_id} not in store")
        return copy.deepcopy(layers[layer_id])

    def list_layers(self, note_id: Optional[str] = None, kind: Optional[str] = None) -> List[dict]:
        out = [l for l in self._load_layers().values()
               if (note_id is None or note_id in l["note_ids"]) and (kind is None or l["kind"] == kind)]
        return [copy.deepcopy(l) for l in sorted(out, key=lambda l: (l["created_utc"], l["layer_id"]))]

    def add_layer(self, *, kind: str, note_ids: Sequence[str], created_by: str, inputs: List[dict],
                  payload: dict, params: Optional[dict] = None) -> dict:
        """Validate and append a derived layer; returns the stored object.

        Identical content (same kind, notes, creator, inputs, params, payload)
        maps to the same ``layer_id`` and is stored once.
        """
        if kind not in LAYER_KINDS:
            raise ValidationError(f"unknown layer kind {kind!r}; allowed: {LAYER_KINDS}")
        if not CREATED_BY_RE.match(created_by or ""):
            raise ValidationError(f"created_by {created_by!r} must be '<algorithm>@<version>' or 'user'")
        note_ids = list(dict.fromkeys(note_ids))
        params = dict(params or {})
        inputs = copy.deepcopy(inputs)
        payload = copy.deepcopy(payload)
        # canonical round trip: rejects NaN and non-JSON types early
        json.loads(canonical_json({"inputs": inputs, "payload": payload, "params": params}))
        self._check_links(kind, note_ids, created_by, inputs, payload)
        layer_id = layer_id_for(kind, note_ids, created_by, inputs, params, payload)
        obj = {"object": "derived_layer", "schema_version": 1, "layer_id": layer_id, "kind": kind,
               "note_ids": note_ids, "created_by": created_by, "created_utc": self.clock(),
               "inputs": inputs, "params": params, "payload": payload}
        obj["digest"] = _digest(obj)
        validate(obj, "derived_layer")
        path = self._layer_path(layer_id)
        if _write_once(path, pretty_json(obj).encode("utf-8") + b"\n"):
            if self._layer_cache is not None:
                self._layer_cache[layer_id] = obj
            return copy.deepcopy(obj)
        return self.get_layer(layer_id)

    def _check_links(self, kind, note_ids, created_by, inputs, payload) -> None:
        if not note_ids:
            raise ValidationError("a derived layer must reference at least one note")
        if kind == "user_edit" and created_by != "user":
            raise ValidationError("user_edit layers must have created_by == 'user'")
        if kind == "ai_summary" and created_by == "user":
            raise ValidationError("ai_summary layers are machine generated; created_by must name the algorithm")
        notes = {nid: self.get_note(nid) for nid in note_ids}
        originals = {nid: self.get_original(n["original_sha256"]) for nid, n in notes.items()}
        by_sha = {o.sha256: o for o in originals.values()}
        if not inputs:
            raise ValidationError("a derived layer must list its inputs")
        for ref in inputs:
            t = ref.get("type")
            if t == "original":
                o = by_sha.get(ref.get("sha256"))
                if o is None:
                    raise ValidationError(f"input original {ref.get('sha256')} does not belong to notes {note_ids}")
                if "stroke_ranges" in ref:
                    o.check_ranges(ref["stroke_ranges"], "inputs")
            elif t == "layer":
                src = self.get_layer(ref["layer_id"])
                if not set(src["note_ids"]) <= set(note_ids):
                    raise ValidationError(f"input layer {ref['layer_id']} belongs to other notes")
                if src["kind"] == "ai_summary" and kind != "ai_summary":
                    raise ValidationError("assistant output must not become an input of note content layers")
                if "span_ids" in ref:
                    known = {s["span_id"] for s in src["payload"].get("spans", [])}
                    bad = [s for s in ref["span_ids"] if s not in known]
                    if bad:
                        raise ValidationError(f"input spans {bad[:3]} not in layer {ref['layer_id']}")
            elif t in ("source_file", "external_file"):
                pass
            else:
                raise ValidationError(f"unknown input type {t!r}")
        if kind != "ai_summary" and len(note_ids) != 1:
            raise ValidationError(f"{kind} layers belong to exactly one note")
        single = originals[note_ids[0]]
        if kind in ("recognition", "segmentation"):
            for s in payload.get("spans", []):
                if not s.get("stroke_ranges"):
                    raise ValidationError(f"span {s.get('span_id')} has no stroke links")
                single.check_ranges(s["stroke_ranges"], f"span {s.get('span_id')}")
            ids = [s["span_id"] for s in payload.get("spans", [])]
            if len(ids) != len(set(ids)):
                raise ValidationError("duplicate span ids")
            if kind == "segmentation":
                for st in payload.get("strokes", []):
                    single.check_ranges([[st["stroke_id"], st["stroke_id"]]], "segmentation stroke")
        elif kind == "hand_path_estimate":
            for st in payload.get("strokes", []):
                single.check_ranges([[st["stroke_id"], st["stroke_id"]]], "hand path stroke")
                if not len(st["t_ms"]) == len(st["x_um"]) == len(st["y_um"]):
                    raise ValidationError("hand path arrays differ in length")
        elif kind == "user_edit":
            target = self.get_layer(payload["target_layer"])
            if target["kind"] != "recognition":
                raise ValidationError("user_edit must target a recognition layer")
            if not set(target["note_ids"]) <= set(note_ids):
                raise ValidationError("user_edit target belongs to another note")
            spans = {s["span_id"]: s for s in target["payload"]["spans"]}
            for ed in payload["edits"]:
                s = spans.get(ed["span_id"])
                if s is None:
                    raise ValidationError(f"user_edit span {ed['span_id']} not in target layer")
                if ed["stroke_ranges"] != s["stroke_ranges"]:
                    raise ValidationError("user_edit must keep the stroke links of the edited span")
            if not any(r.get("type") == "layer" and r.get("layer_id") == payload["target_layer"] for r in inputs):
                raise ValidationError("user_edit inputs must include its target layer")
        elif kind == "ai_summary":
            for k, sent in enumerate(payload.get("sentences", [])):
                if not sent.get("citations"):
                    raise ValidationError(f"ai_summary sentence {k} has no citation")
                for c in sent["citations"]:
                    if c["note_id"] not in originals:
                        raise ValidationError(f"citation to note {c['note_id']} not in note_ids")
                    o = originals[c["note_id"]]
                    if c["original_sha256"] != o.sha256:
                        raise ValidationError("citation original does not match the cited note")
                    o.check_ranges(c["stroke_ranges"], "citation")
                    for lid in c["layer_ids"]:
                        lk = self.get_layer(lid)["kind"]
                        if lk not in ("recognition", "user_edit"):
                            raise ValidationError(f"citations must point at note text layers, not {lk}")

    # effective text (recognition + user edits) --------------------------------
    def effective_text(self, note_id: str) -> Optional[dict]:
        """Most recent recognition layer with the user edits that target it."""
        recs = self.list_layers(note_id=note_id, kind="recognition")
        if not recs:
            return None
        rec = recs[-1]
        spans = [dict(s) for s in rec["payload"]["spans"]]
        by_id = {s["span_id"]: s for s in spans}
        edits_all = self.list_layers(note_id=note_id, kind="user_edit")
        applied = [l for l in edits_all if l["payload"]["target_layer"] == rec["layer_id"]]
        stale = [l["layer_id"] for l in edits_all if l["payload"]["target_layer"] != rec["layer_id"]]
        line_edited = set()
        for el in applied:
            for ed in el["payload"]["edits"]:
                s = by_id[ed["span_id"]]
                s["text"] = ed["text"]
                s.setdefault("edited_by", []).append(el["layer_id"])
                if s["level"] == "line":
                    line_edited.add(s["span_id"])
        children = defaultdict(list)
        for s in spans:
            if s["level"] == "word" and s.get("parent"):
                children[s["parent"]].append(s)
        for s in spans:
            if s["level"] != "line":
                continue
            if s["span_id"] in line_edited:
                for w in children[s["span_id"]]:
                    w["superseded"] = True
            elif children[s["span_id"]]:
                s["text"] = " ".join(w["text"] for w in children[s["span_id"]] if w["text"])
                edited = sorted({e for w in children[s["span_id"]] for e in w.get("edited_by", [])})
                if edited:
                    s["edited_by"] = edited
        note = self.get_note(note_id)
        return {"note_id": note_id, "original_sha256": note["original_sha256"],
                "recognition_layer_id": rec["layer_id"], "recognizer": rec["created_by"],
                "user_edit_layer_ids": [l["layer_id"] for l in applied],
                "stale_user_edit_layer_ids": stale, "spans": spans}

    def add_user_edit(self, note_id: str, edits: Dict[str, str], *, target_layer: Optional[str] = None) -> dict:
        """Record user corrections ``{span_id: new_text}`` as a user_edit layer."""
        if target_layer is None:
            eff = self.effective_text(note_id)
            if eff is None:
                raise ValidationError("note has no recognition layer to edit")
            target_layer = eff["recognition_layer_id"]
            current = {s["span_id"]: s for s in eff["spans"]}
        else:
            current = {s["span_id"]: s for s in self.get_layer(target_layer)["payload"]["spans"]}
        items = []
        for sid, text in edits.items():
            if sid not in current:
                raise ValidationError(f"span {sid} not in layer {target_layer}")
            items.append({"span_id": sid, "text": str(text), "previous_text": current[sid]["text"],
                          "stroke_ranges": current[sid]["stroke_ranges"]})
        ranges = ranges_from_ids(i for it in items for i in ids_from_ranges(it["stroke_ranges"]))
        note = self.get_note(note_id)
        return self.add_layer(kind="user_edit", note_ids=[note_id], created_by="user",
                              inputs=[{"type": "layer", "layer_id": target_layer,
                                       "span_ids": [it["span_id"] for it in items]},
                                      {"type": "original", "sha256": note["original_sha256"],
                                       "stroke_ranges": ranges}],
                              payload={"target_layer": target_layer, "edits": items})

    # integrity, export, erasure ----------------------------------------------
    def verify(self) -> dict:
        """Re-verify every object; returns a report (``ok`` is False on any problem)."""
        problems = []
        n_orig = n_notes = n_layers = 0
        for sha in self.list_originals():
            try:
                self.get_original(sha, use_cache=False)
                n_orig += 1
            except NoteStoreError as e:
                problems.append(f"original {sha[:12]}: {e}")
        self._layer_cache = None
        for p in sorted((self.root / "notes").glob("*.json")):
            try:
                note = self.get_note(p.stem)
                validate(note, "note")
                if not self._orig_path(note["original_sha256"]).exists():
                    problems.append(f"note {p.stem}: original missing")
                n_notes += 1
            except NoteStoreError as e:
                problems.append(f"note {p.stem}: {e}")
        for p in sorted((self.root / "layers").glob("*.json")):
            try:
                obj = self._read_layer(p.stem)
                validate(obj, "derived_layer")
                n_layers += 1
            except (NoteStoreError, KeyError) as e:
                problems.append(f"layer {p.stem}: {e}")
        self._layer_cache = None
        return {"ok": not problems, "originals": n_orig, "notes": n_notes, "layers": n_layers,
                "problems": problems}

    def export_bundle(self, note_ids: Optional[Sequence[str]] = None) -> dict:
        notes = [self.get_note(n) for n in note_ids] if note_ids else self.list_notes()
        keep = {n["note_id"] for n in notes}
        shas = sorted({n["original_sha256"] for n in notes})
        layers = [l for l in self.list_layers() if set(l["note_ids"]) <= keep]
        bundle = {"object": "note_store_bundle", "schema_version": 1, "exported_utc": self.clock(),
                  "exported_by": f"penapp.export@{__version__}", "notes": notes,
                  "originals": [self.get_original(s).to_json() for s in shas], "layers": layers}
        validate(bundle, None)
        return bundle

    def purge_note(self, note_id: str, *, confirm: str) -> dict:
        """Erase a note, every derived layer that uses it and (if unshared) its original.

        ``confirm`` must repeat the note id: erasure is explicit and irreversible.
        """
        if confirm != note_id:
            raise NoteStoreError("purge_note requires confirm=<note_id>")
        note = self.get_note(note_id)
        removed_layers = [l["layer_id"] for l in self.list_layers(note_id=note_id)]
        for lid in removed_layers:
            _force_unlink(self._layer_path(lid))
        _force_unlink(self._note_path(note_id))
        sha = note["original_sha256"]
        shared = any(n["original_sha256"] == sha for n in self.list_notes())
        if not shared:
            _force_unlink(self._orig_path(sha))
            self._orig_cache.pop(sha, None)
        self._layer_cache = None
        return {"note_id": note_id, "layers_removed": removed_layers, "original_removed": not shared}


def _force_unlink(path: Path) -> None:
    if path.exists():
        os.chmod(path, 0o644)
        path.unlink()


def stroke_semantic_checks(orig: OriginalLayer) -> dict:
    """Non-fatal plausibility checks of logged stroke samples (reported, never corrected)."""
    s = orig.samples
    if not len(s):
        return {"n_samples": 0}
    sid = s["stroke_id"].astype(np.int64)
    t = s["t_ms"].astype(np.int64)
    same = np.diff(sid) == 0
    return {"n_samples": int(len(s)), "n_strokes": int(len(np.unique(sid))),
            "n_stroke_runs": len(orig.stroke_runs),
            "stroke_id_decreases": int(np.sum(np.diff(sid) < 0)),
            "t_ms_decreases_within_stroke": int(np.sum((np.diff(t) < 0) & same)),
            "theta_out_of_range": int(np.sum(s["theta_raw"] > 180)),
            "phi_out_of_range": int(np.sum(s["phi_raw"] > 179))}
