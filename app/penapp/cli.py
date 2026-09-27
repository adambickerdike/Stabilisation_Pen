"""Command line: ``python -m penapp <command>`` (run with ``app/`` on PYTHONPATH).

Commands
--------
import    parse ICD logs (CRC-checked), store the original layer, derive
          segmentation / hand-path layers, recognise, index
render    SVG of a note, optionally with a derived-layer overlay
search    full-text search; hits carry stroke-id ranges and page boxes
ask       source-grounded question answering over the notes (local, extractive)
fidelity  capture-fidelity analysis of the 200 Hz / 1 um stroke format
list, verify, edit   list notes, re-verify every content address, record a user edit

The store directory comes from ``--store`` or the ``PENAPP_STORE`` variable.
No command makes network calls.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import List, Optional

from . import __version__
from ._util import REPO_ROOT, format_ranges, sha256_hex


def _store(args):
    from .notes import NoteStore
    if not args.store:
        raise SystemExit("error: give --store DIR or set PENAPP_STORE")
    return NoteStore(args.store)


def _mm(b) -> str:
    return f"({b[0] / 1000:.2f}, {b[1] / 1000:.2f})-({b[2] / 1000:.2f}, {b[3] / 1000:.2f}) mm"


def import_log_file(store, path, *, truth: Optional[str] = None, recognizer: str = "auto",
                    labels=(), strict: bool = False) -> dict:
    """Full import pipeline for one log file; returns a summary dict."""
    from . import capture, logfmt, recognize
    from .search import SearchIndex
    data = Path(path).read_bytes()
    parsed = logfmt.read_log(data, strict=strict)
    sha = sha256_hex(data)
    note = store.import_log(parsed, source_name=Path(path).name, source_sha256=sha, labels=labels)
    nid = note["note_id"]
    seg = capture.add_segmentation_layer(store, nid)
    hand = capture.add_hand_path_layer(store, nid, parsed, sha)
    if truth is None and recognizer in ("auto", "groundtruth"):
        cand = Path(path).with_suffix(".truth.json")
        truth = str(cand) if cand.exists() else None
    if recognizer == "groundtruth" and truth is None:
        raise SystemExit("error: --recognizer groundtruth needs --truth FILE")
    rec_impl = recognize.GroundTruthRecognizer.from_file(truth) if truth else recognize.NullRecognizer()
    rec = recognize.run_recognizer(store, nid, rec_impl)
    with SearchIndex.for_store(store) as idx:
        n_lines = idx.index_note(store, nid)
    return {"note_id": nid, "original_sha256": note["original_sha256"], "labels": note["labels"],
            "parse": {k: parsed.summary()[k] for k in ("records", "bytes_skipped", "issues_by_kind", "data_loss")},
            "layers": {"segmentation": seg["layer_id"], "hand_path_estimate": hand["layer_id"] if hand else None,
                       "recognition": rec["layer_id"]},
            "recognizer": rec["created_by"], "indexed_lines": n_lines}


def cmd_import(args) -> int:
    store = _store(args)
    out = []
    for p in args.log:
        out.append(import_log_file(store, p, truth=args.truth, recognizer=args.recognizer, labels=args.label,
                                   strict=args.strict))
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        for s in out:
            print(f"{s['note_id']}  original {s['original_sha256'][:16]}  labels {s['labels']}")
            print(f"  records {s['parse']['records']}  bytes skipped {s['parse']['bytes_skipped']}  "
                  f"issues {s['parse']['issues_by_kind']}")
            print(f"  layers {s['layers']}  recogniser {s['recognizer']}  indexed lines {s['indexed_lines']}")
    return 0


def cmd_render(args) -> int:
    from .render import render_note, save_svg
    store = _store(args)
    svg = render_note(store, args.note_id, overlay=args.overlay, force_width=args.force_width)
    save_svg(args.out, svg)
    print(args.out)
    return 0


def cmd_search(args) -> int:
    from .search import SearchIndex
    store = _store(args)
    with SearchIndex.for_store(store) as idx:
        hits = idx.search(args.query, mode="any" if args.any else "all", prefix=args.prefix, limit=args.limit)
    if args.json:
        print(json.dumps([h.to_json() for h in hits], indent=1))
        return 0
    if not hits:
        print("no hits")
    for h in hits:
        print(f"{h.note_id} {h.span_id}  score {h.score:.3f}  \"{h.text}\"")
        print(f"  line strokes {format_ranges(h.stroke_ranges)}  box {_mm(h.bbox_um)}  layers {h.layer_ids}")
        for w in h.words:
            print(f"  match \"{w.text}\" strokes {format_ranges(w.stroke_ranges)}  box {_mm(w.bbox_um)}")
    return 0


def cmd_ask(args) -> int:
    from .grounded import GroundedAssistant
    from .search import SearchIndex
    store = _store(args)
    with SearchIndex.for_store(store) as idx:
        res = GroundedAssistant(store, idx).ask(args.question, store_result=not args.no_store)
    if args.json:
        print(json.dumps(res.to_json(), indent=1))
        return 0
    if res.status == "refused":
        print(f"REFUSED ({res.reason}): {res.message}")
        for v in res.violations:
            print(f"  - {v}")
        return 0
    print(f"Answer (model {res.model_id}; stored as layer {res.layer_id or '-'}):")
    for s in res.sentences:
        cites = "; ".join(f"{c['source_id']} {c['note_id']} {c['span_id']} strokes {format_ranges(c['stroke_ranges'])}"
                          for c in s.citations)
        print(f"  {s.text}   [{cites}]")
    from .grounded import DISCLAIMER
    print(DISCLAIMER)
    return 0


def cmd_fidelity(args) -> int:
    from .capture import run_fidelity
    traces = args.traces or sorted(glob.glob(str(REPO_ROOT / "results" / "sim" / "nominal" / "traces_*.npz")))
    if not traces:
        raise SystemExit("error: no simulator traces found")
    res = run_fidelity(traces, args.out, densify_um=args.densify_um, frechet=not args.no_frechet)
    for line in res["interpretation"]:
        print("-", line)
    print(args.out)
    return 0


def cmd_list(args) -> int:
    store = _store(args)
    for n in store.list_notes():
        kinds = {}
        for l in store.list_layers(note_id=n["note_id"]):
            kinds[l["kind"]] = kinds.get(l["kind"], 0) + 1
        print(f"{n['note_id']}  session {n['session']['session_id']}  samples "
              f"{n['source']['parse']['stroke_semantics'].get('n_samples', 0)}  labels {n['labels']}  layers {kinds}")
    return 0


def cmd_verify(args) -> int:
    rep = _store(args).verify()
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


def cmd_edit(args) -> int:
    from .search import SearchIndex
    store = _store(args)
    layer = store.add_user_edit(args.note_id, {args.span_id: args.text})
    with SearchIndex.for_store(store) as idx:
        idx.index_note(store, args.note_id)
    print(layer["layer_id"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="penapp", description=f"research-pen companion app v{__version__} "
                                 "(reference implementation; synthetic data only)")
    ap.add_argument("--store", default=os.environ.get("PENAPP_STORE"), help="note store directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import", help="import ICD v1.0 binary logs")
    p.add_argument("log", nargs="+")
    p.add_argument("--truth", help="ground-truth transcript JSON of a SYNTHETIC session")
    p.add_argument("--recognizer", choices=["auto", "null", "groundtruth"], default="auto",
                   help="auto: ground-truth passthrough if <log>.truth.json exists, else null")
    p.add_argument("--label", action="append", default=[])
    p.add_argument("--strict", action="store_true", help="fail on any CRC/framing anomaly")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("render", help="render a note to SVG")
    p.add_argument("note_id")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--overlay", help="text | recognition | segmentation | hand_path_estimate | <layer id>")
    p.add_argument("--force-width", action="store_true", help="line width from force")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("search", help="full-text search over recognised text")
    p.add_argument("query")
    p.add_argument("--any", action="store_true", help="match any term (default: all)")
    p.add_argument("--prefix", action="store_true", help="prefix-match terms")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_search)
    p = sub.add_parser("ask", help="source-grounded answer with citations")
    p.add_argument("question")
    p.add_argument("--no-store", action="store_true", help="do not store the answer as an ai_summary layer")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_ask)
    p = sub.add_parser("fidelity", help="capture-fidelity analysis on simulator traces")
    p.add_argument("--traces", nargs="*")
    p.add_argument("-o", "--out", default=str(REPO_ROOT / "results" / "app" / "capture_fidelity.json"))
    p.add_argument("--densify-um", type=float, default=2.0)
    p.add_argument("--no-frechet", action="store_true")
    p.set_defaults(fn=cmd_fidelity)
    p = sub.add_parser("list", help="list notes")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("verify", help="re-verify content addresses and digests")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("edit", help="record a user correction of a recognised span")
    p.add_argument("note_id")
    p.add_argument("span_id")
    p.add_argument("text")
    p.set_defaults(fn=cmd_edit)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)
