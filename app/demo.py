#!/usr/bin/env python3
"""End-to-end demo of the companion-app reference implementation.

EVERYTHING HERE IS SYNTHETIC: glyph handwriting of known text and a
coupled-simulator trace.  No person, no device, no network.

Steps
  1. synthesise two text sessions and one simulator session; write ICD v1.0
     binary logs (+ ground truth / metadata) to data/samples/
  2. write the ICD example vector (data/samples/icd_v1_example.*)
  3. corruption test: flip/insert/delete bytes, parse with resync, check that
     every recovered record is genuine
  4. import into a note store (results/app/demo_store/, fixed synthetic clock)
  5. segmentation vs ground truth; recognition (ground-truth passthrough for
     text, null for the simulator session); hand-path layer from research frames
  6. SVG renders to results/app/
  7. full-text search with stroke-id/box links
  8. grounded questions: answers with citations, refusals
  9. injected recognition errors + user edits (derived layers only)
 10. CER stress test of search and assistant (temporary store)
 11. integrity verification and tamper detection
 12. capture-fidelity analysis (results/app/capture_fidelity.json)
 13. results/app/demo_report.json

Run: python3 app/demo.py [--skip-fidelity]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent
for p in (str(APP), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

from penapp import __version__, capture, logfmt, recognize, render, vectors  # noqa: E402
from penapp._util import (FixedClock, environment_info, file_sha256, format_ranges, git_revision,  # noqa: E402
                          rel_to_repo, write_json)
from penapp.cli import import_log_file  # noqa: E402
from penapp.grounded import GroundedAssistant  # noqa: E402
from penapp.notes import IntegrityError, NoteStore  # noqa: E402
from penapp.search import SearchIndex  # noqa: E402
from penapp.synth import synth_sim_session, synth_text_session  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
OUT = ROOT / "results" / "app"
TRACE = ROOT / "results" / "sim" / "nominal" / "traces_kf_asr.npz"
SESSIONS = {
    "demo_text_errands": dict(lines=["buy milk eggs and bread", "return library books by friday",
                                     "call the plumber at 9 am"], seed=11, session_id=1,
                              start_unix_ms=1788253200000),
    "demo_text_project": dict(lines=["pen rev a bench test on monday", "check hall sensor offset",
                                     "order spare refills"], seed=12, session_id=2,
                              start_unix_ms=1788339600000),
}
QUESTIONS = [
    "When should I return the library books?",
    "What do I need to check on the hall sensor?",
    "What should I buy or order?",
    "What is the wifi password?",
    "Is my handwriting getting worse?",
]
SEARCHES = [("library", {}), ('"hall sensor"', {}), ("refill", {}), ("plumber 9", {}), ("mon", {"prefix": True})]


def step(msg):
    print(f"[demo] {msg}", flush=True)


def corruption_test(data: bytes, seed: int = 5) -> dict:
    """Corrupt a copy of a log and check that resynchronisation recovers only genuine records."""
    rng = np.random.default_rng(seed)
    clean = logfmt.read_log(data, strict=True)
    genuine = {(logfmt.record_type_of(r), bytes(r.encode())) for _, r in clean.records}
    x = bytearray(data)
    flips = sorted(rng.choice(np.arange(logfmt.HEADER_SIZE, len(x)), size=25, replace=False).tolist())
    for o in flips:
        x[o] ^= 1 << int(rng.integers(8))
    cut = int(len(x) * 0.4)
    del x[cut:cut + 3]
    ins = int(len(x) * 0.7)
    x[ins:ins] = bytes(rng.integers(0, 256, 17, dtype=np.uint8))
    p = logfmt.read_log(bytes(x))
    recovered = [(logfmt.record_type_of(r), bytes(r.encode())) for _, r in p.records]
    false_records = sum(1 for r in recovered if r not in genuine)
    return {"operations": {"bit_flips": len(flips), "bytes_deleted": 3, "bytes_inserted": 17},
            "records_clean": len(clean.records), "records_recovered": len(recovered),
            "records_lost": len(clean.records) - len(recovered), "false_records_accepted": false_records,
            "stroke_samples_clean": int(len(clean.strokes)), "stroke_samples_recovered": int(len(p.strokes)),
            "issues_by_kind": p.summary()["issues_by_kind"], "bytes_skipped": p.bytes_skipped}


def segmentation_vs_truth(store, note_id, truth) -> dict:
    seg = store.list_layers(note_id=note_id, kind="segmentation")[-1]
    got = [s["stroke_ranges"] for s in seg["payload"]["spans"] if s["level"] == "word"]
    want = [w["stroke_ranges"] for l in truth["lines"] for w in l["words"]]
    lines_got = sum(s["level"] == "line" for s in seg["payload"]["spans"])
    return {"words_truth": len(want), "words_segmented": len(got),
            "words_exact_stroke_match": sum(w in got for w in want),
            "lines_truth": len(truth["lines"]), "lines_segmented": lines_got,
            "flagged_strokes": sum(bool(s["flags"]) for s in seg["payload"]["strokes"])}


def hit_json(h) -> dict:
    return {"note_id": h.note_id, "line_span": h.span_id, "text": h.text, "score": h.score,
            "layer_ids": h.layer_ids, "line_stroke_ranges": h.stroke_ranges, "line_bbox_um": h.bbox_um,
            "matched_words": [{"text": w.text, "span_id": w.span_id, "stroke_ranges": w.stroke_ranges,
                               "bbox_um": w.bbox_um} for w in h.words]}


def answer_json(res) -> dict:
    if res.status == "refused":
        return {"status": "refused", "reason": res.reason, "message": res.message,
                "violations": res.violations, "llm_called": res.llm_called}
    return {"status": "answered", "ai_summary_layer_id": res.layer_id, "model": res.model_id,
            "sentences": [{"text": s.text, "support": s.support,
                           "citations": [{"source": c["source_id"], "note_id": c["note_id"], "span_id": c["span_id"],
                                          "layer_ids": c["layer_ids"], "stroke_ranges": c["stroke_ranges"],
                                          "bbox_um": c["bbox_um"]} for c in s.citations]}
                          for s in res.sentences]}


def user_edit_demo(store, idx, note_id, truth) -> dict:
    """Injected recognition errors on one note, then user corrections as a user_edit layer."""
    base = recognize.GroundTruthRecognizer.from_file(SAMPLES / "demo_text_project.truth.json")
    noisy = recognize.run_recognizer(store, note_id, recognize.ErrorInjectingRecognizer(base, cer=0.15, seed=4))
    idx.index_note(store, note_id)
    eff = store.effective_text(note_id)
    truth_words = {f"l{li}.w{wi}": w["text"] for li, l in enumerate(truth["lines"]) for wi, w in enumerate(l["words"])}
    wrong = {s["span_id"]: s["text"] for s in eff["spans"] if s["level"] == "word"
             and s["text"] != truth_words[s["span_id"]]}
    probe = next((truth_words[k] for k in sorted(wrong) if len(truth_words[k]) >= 3), None)
    before = [hit_json(h) for h in idx.search(probe)] if probe else []
    edit = store.add_user_edit(note_id, {k: truth_words[k] for k in sorted(wrong)}) if wrong else None
    idx.index_note(store, note_id)
    after = [hit_json(h) for h in idx.search(probe)] if probe else []
    return {"recognition_layer": noisy["layer_id"], "recognizer": noisy["created_by"],
            "achieved_cer": noisy["params"]["achieved_cer_vs_base"],
            "misrecognised_words": {k: {"recognised": v, "truth": truth_words[k]} for k, v in sorted(wrong.items())},
            "user_edit_layer": edit["layer_id"] if edit else None,
            "probe_query": probe, "hits_before_edit": len(before), "hits_after_edit": len(after),
            "hit_after_edit": after[0] if after else None,
            "original_unchanged": store.get_original(eff["original_sha256"], use_cache=False).sha256
            == eff["original_sha256"]}


def cer_stress(logs, truths, cers=(0.0, 0.05, 0.1, 0.2, 0.3), seeds=range(5)) -> dict:
    """Search recall and assistant behaviour vs injected CER (temporary store, nothing kept)."""
    rows = []
    with tempfile.TemporaryDirectory() as d:
        store = NoteStore(d, clock=FixedClock("2026-09-01T12:00:00.000Z"))
        nids = [import_log_file(store, lg, recognizer="null")["note_id"] for lg in logs]
        idx = SearchIndex.for_store(store)
        qs = [("When should I return the library books?", nids[0], "l1"),
              ("What do I need to check on the hall sensor?", nids[1], "l1")]
        for c in cers:
            for sd in seeds:
                achieved = []
                for nid, tp in zip(nids, truths):
                    base = recognize.GroundTruthRecognizer.from_file(tp)
                    lay = recognize.run_recognizer(store, nid, recognize.ErrorInjectingRecognizer(base, c, seed=sd))
                    achieved.append(lay["params"]["achieved_cer_vs_base"])
                    idx.index_note(store, nid)
                found = total = 0
                for nid, tp in zip(nids, truths):
                    tr = json.loads(Path(tp).read_text())
                    for l in tr["lines"]:
                        for w in l["words"]:
                            if len(w["text"]) < 3:
                                continue
                            total += 1
                            hits = idx.search(w["text"], note_ids=[nid])
                            found += any(any(x.stroke_ranges == w["stroke_ranges"] for x in h.words) for h in hits)
                asst = GroundedAssistant(store, idx)
                answered = correct = 0
                for q, nid, line in qs:
                    r = asst.ask(q, store_result=False)
                    if r.status == "answered":
                        answered += 1
                        correct += any(cc["note_id"] == nid and cc["span_id"] == line
                                       for s in r.sentences for cc in s.citations)
                rows.append({"target_cer": c, "seed": sd, "achieved_cer": round(float(np.mean(achieved)), 4),
                             "word_search_recall": found / total,
                             "questions_answered": answered, "questions_citing_correct_line": correct})
        idx.close()
    summ = []
    for c in cers:
        sub = [r for r in rows if r["target_cer"] == c]
        summ.append({"target_cer": c, "n_seeds": len(sub),
                     "achieved_cer_mean": round(float(np.mean([r["achieved_cer"] for r in sub])), 3),
                     "word_search_recall_mean": round(float(np.mean([r["word_search_recall"] for r in sub])), 3),
                     "word_search_recall_min": round(float(np.min([r["word_search_recall"] for r in sub])), 3),
                     "answered_of_2_mean": round(float(np.mean([r["questions_answered"] for r in sub])), 2),
                     "correct_citation_of_2_mean": round(float(np.mean([r["questions_citing_correct_line"]
                                                                         for r in sub])), 2)})
    return {"evidence_status": "SYNTHETIC stress test: ground-truth transcripts with injected character errors",
            "method": "per (CER, seed): recognition layer from ErrorInjectingRecognizer over the ground truth; "
                      "word recall = fraction of truth words (>= 3 chars) whose search hits link to exactly the "
                      "word's stroke ids; two answerable questions asked without storing answers",
            "summary": summ, "runs": rows}


def tamper_test(store_root: Path, sha: str) -> dict:
    with tempfile.TemporaryDirectory() as d:
        dst = Path(d) / "store"
        shutil.copytree(store_root, dst)
        f = dst / "originals" / f"{sha}.json"
        f.chmod(0o644)
        obj = json.loads(f.read_text())
        obj["samples"][10][2] += 1                      # move one sample by 1 um
        f.write_text(json.dumps(obj))
        st = NoteStore(dst)
        try:
            st.get_original(sha)
            detected = False
        except IntegrityError:
            detected = True
        rep = st.verify()
    return {"modification": "x of sample 10 of one original changed by +1 um in a copy of the store",
            "detected_on_load": detected, "verify_ok_after_tamper": rep["ok"], "verify_problems": rep["problems"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-fidelity", action="store_true", help="reuse results/app/capture_fidelity.json")
    args = ap.parse_args(argv)
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    report = {"meta": {
        "evidence_status": "SYNTHETIC DEMO - synthetic handwriting and simulator traces; no human data, "
                           "no measurements, no network calls",
        "generated_by": f"app/demo.py (penapp {__version__})", "git_revision": git_revision(),
        "environment": environment_info(),
        "clock": "note-store created_utc/imported_utc values come from a fixed synthetic clock "
                 "(2026-09-01T09:00:00Z + 1 ms per call) so the store is reproducible"}}

    step("1-2 synthesising sessions and the ICD example vector")
    files = {}
    truths = {}
    for name, kw in SESSIONS.items():
        ses = synth_text_session(kw["lines"], seed=kw["seed"], session_id=kw["session_id"],
                                 start_unix_ms=kw["start_unix_ms"])
        files[name] = ses.write(SAMPLES / f"{name}.penlog", truth_path=SAMPLES / f"{name}.truth.json",
                                meta_path=SAMPLES / f"{name}.meta.json")
        truths[name] = ses.truth
    sim = synth_sim_session(TRACE)
    files["demo_sim_kf_asr"] = sim.write(SAMPLES / "demo_sim_kf_asr.penlog", meta_path=SAMPLES / "demo_sim_kf_asr.meta.json")
    vec = vectors.example_log()
    (SAMPLES / "icd_v1_example.penlog").write_bytes(vec)
    write_json(SAMPLES / "icd_v1_example.json", vectors.describe())
    files["icd_v1_example"] = {"log": rel_to_repo(SAMPLES / "icd_v1_example.penlog"),
                               "log_sha256": file_sha256(SAMPLES / "icd_v1_example.penlog"),
                               "expectation": rel_to_repo(SAMPLES / "icd_v1_example.json")}
    report["sample_files"] = files

    step("3 corruption / resynchronisation test")
    report["corruption_test"] = corruption_test((SAMPLES / "demo_text_errands.penlog").read_bytes())

    step("4-5 import, segmentation, recognition, hand-path layer")
    store_root = OUT / "demo_store"
    if store_root.exists():
        shutil.rmtree(store_root)
    store = NoteStore(store_root, clock=FixedClock("2026-09-01T09:00:00.000Z"))
    imports = {}
    for name in list(SESSIONS) + ["demo_sim_kf_asr"]:
        imports[name] = import_log_file(store, SAMPLES / f"{name}.penlog")
    report["imports"] = imports
    nid = {k: v["note_id"] for k, v in imports.items()}
    report["segmentation_vs_truth"] = {k: segmentation_vs_truth(store, nid[k], truths[k]) for k in SESSIONS}
    sim_note = store.get_note(nid["demo_sim_kf_asr"])
    seg_sim = store.list_layers(note_id=nid["demo_sim_kf_asr"], kind="segmentation")[-1]
    report["simulator_session"] = {
        "note_id": nid["demo_sim_kf_asr"],
        "strokes": [{"stroke_id": s["stroke_id"], "n": s["n"], "duration_ms": s["t1_ms"] - s["t0_ms"],
                     "flags": s["flags"]} for s in seg_sim["payload"]["strokes"]],
        "events": len(sim_note["events"]),
        "hand_path_layer": imports["demo_sim_kf_asr"]["layers"]["hand_path_estimate"]}
    hp = store.get_layer(imports["demo_sim_kf_asr"]["layers"]["hand_path_estimate"])
    orig_sim = store.get_original(sim_note["original_sha256"])
    dev = []
    for st in hp["payload"]["strokes"]:
        sl = orig_sim.stroke_slices()[st["stroke_id"]][0]
        ink = orig_sim.xy_um(sl).astype(float)
        dev.append(np.hypot(ink[:, 0] - np.asarray(st["x_um"]), ink[:, 1] - np.asarray(st["y_um"])))
    dev = np.concatenate(dev)
    report["simulator_session"]["ink_minus_hand_path_um"] = {
        "rms": round(float(np.sqrt(np.mean(dev ** 2))), 1), "max": round(float(dev.max()), 1),
        "meaning": "distance between deposited ink (original layer) and the housing path (hand-path estimate) "
                   "at the stroke samples: the stage correction in this simulated run (Kalman, assertive)"}

    step("6 SVG renders")
    renders = {}
    e_id = nid["demo_text_errands"]
    renders["errands_force_width"] = render.save_svg(OUT / "demo_errands_force_width.svg", render.render_note(
        store, e_id, force_width=True, title="Synthetic note: errands (line width from force)"))
    renders["errands_recognition_overlay"] = render.save_svg(OUT / "demo_errands_text_overlay.svg", render.render_note(
        store, e_id, overlay="text", title="Synthetic note: errands + recognised text (ground-truth passthrough)"))
    renders["simulator_hand_path_overlay"] = render.save_svg(OUT / "demo_sim_hand_path_overlay.svg", render.render_note(
        store, nid["demo_sim_kf_asr"], overlay="hand_path_estimate", width_mm=0.12,
        title="Simulator session (kf_asr, 9 Hz 0.3 mm tremor): ink vs hand-path estimate"))

    step("7 search")
    idx = SearchIndex.for_store(store)
    report["search"] = [{"query": q, "options": o, "hits": [hit_json(h) for h in idx.search(q, **o)]}
                        for q, o in SEARCHES]

    step("8 grounded questions")
    asst = GroundedAssistant(store, idx)
    answers = []
    first_answer = None
    for q in QUESTIONS:
        res = asst.ask(q)
        answers.append({"question": q, **answer_json(res)})
        if res.status == "answered" and first_answer is None:
            first_answer = res
    report["ask"] = answers
    if first_answer is not None:
        cited = [r for s in first_answer.sentences for c in s.citations for r in c["stroke_ranges"]]
        cap = [f"Q: {first_answer.question}"] + [
            f"A: {s.text}  [{', '.join(c['source_id'] + ' strokes ' + format_ranges(c['stroke_ranges']) for c in s.citations)}]"
            for s in first_answer.sentences] + [f"stored as {first_answer.layer_id}; extractive local model"]
        renders["answer_highlight"] = render.save_svg(OUT / "demo_answer_highlight.svg", render.render_note(
            store, e_id, highlight_ranges=cited, caption=cap, title="Grounded answer: cited strokes highlighted"))

    step("9 injected recognition errors and user edits")
    report["user_edit_demo"] = user_edit_demo(store, idx, nid["demo_text_project"], truths["demo_text_project"])
    renders["project_user_edit_overlay"] = render.save_svg(OUT / "demo_project_user_edit_overlay.svg", render.render_note(
        store, nid["demo_text_project"], overlay="text",
        title=f"Synthetic note: injected recognition errors (target CER 0.15, achieved "
              f"{report['user_edit_demo']['achieved_cer']:.3f}) corrected by user_edit (orange)"))
    report["ask_after_edit"] = {"question": QUESTIONS[1], **answer_json(asst.ask(QUESTIONS[1], store_result=False))}
    report["renders"] = {k: rel_to_repo(v) for k, v in renders.items()}

    step("10 CER stress test")
    report["cer_stress_test"] = cer_stress([SAMPLES / f"{n}.penlog" for n in SESSIONS],
                                           [SAMPLES / f"{n}.truth.json" for n in SESSIONS])

    step("11 integrity")
    idx.close()
    ver = store.verify()
    bundle = store.export_bundle()
    report["integrity"] = {
        "verify": ver,
        "export_bundle_valid": True,
        "bundle_counts": {k: len(bundle[k]) for k in ("notes", "originals", "layers")},
        "layers_by_kind": {k: len(store.list_layers(kind=k)) for k in
                           ("segmentation", "recognition", "hand_path_estimate", "user_edit", "ai_summary")},
        "originals_match_logs": all(
            store.get_original(imports[k]["original_sha256"], use_cache=False).payload
            == logfmt.read_log(SAMPLES / f"{k}.penlog").stroke_payload for k in imports),
        "tamper_test": tamper_test(store_root, imports["demo_text_errands"]["original_sha256"])}

    fid_path = OUT / "capture_fidelity.json"
    if args.skip_fidelity and fid_path.exists():
        step("12 capture fidelity: reusing existing results/app/capture_fidelity.json")
        fid = json.loads(fid_path.read_text())
    else:
        step("12 capture-fidelity analysis on simulator traces (about a minute)")
        traces = sorted((ROOT / "results" / "sim" / "nominal").glob("traces_*.npz"))
        fid = capture.run_fidelity(traces, fid_path)
    report["capture_fidelity"] = {"file": rel_to_repo(fid_path), "inputs": fid["meta"]["inputs"],
                                  "headline_format_point": fid["summary"]["format_point"],
                                  "with_endpoint_samples": fid["summary"]["format_point_endpoints"],
                                  "quantisation_only": fid["summary"]["quantisation_only"],
                                  "interpretation": fid["interpretation"]}
    report["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    write_json(OUT / "demo_report.json", report)
    step(f"done in {report['meta']['elapsed_s']} s -> {rel_to_repo(OUT / 'demo_report.json')}")
    for a in answers:
        print(f"  Q: {a['question']}\n     -> {a['status']}: "
              + ("; ".join(s['text'] for s in a.get('sentences', [])) or a.get("reason", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
