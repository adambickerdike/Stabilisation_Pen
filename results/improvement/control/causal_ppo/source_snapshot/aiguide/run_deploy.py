#!/usr/bin/env python3
"""B4 deployment: lead time, latency budget, template bandwidth, model sizes, 0x06 example.

Evidence status: CALCULATION.  Writing timing comes from synthetic writers
(aiguide/writer.py); latencies of the local predictor and template synthesis
are wall-clock times of this Python implementation on this machine (not a
phone); BLE, recogniser and large-model latencies are allocations, not
measurements.

Lead-time question: a letter's template must be on the pen before the nib
touches down for that letter (the pen anchors it at the touchdown).  If the
template for letter k is predicted from the text up to letter k-d, it is
available at  t_evidence(k-d) + L, where L is the end-to-end latency, and
t_evidence is either the last lift of letter k-d (optimistic) or the first
touchdown of letter k-d+1 (conservative: only then is letter k-d known to be
finished; a 't' crossbar or an 'i' dot may still follow).

Outputs results/ai/deployment.json and fig_lead_time.png.
Run: python3 -m aiguide.run_deploy  (about 10 s)
"""
from __future__ import annotations

import io
import os
import pickle
import time

import numpy as np

from . import BUILD_DIR, EVIDENCE_CALC, RESULTS_DIR, adapter, corpus, lm
from . import icd_template as IT
from . import stroke_predict as sp
from .run_style import EVAL_LINES, observe
from .sentences import CALIB_SENTENCE, GUIDE_SENTENCE
from .style import StyleEstimator
from .template import anchor_to, build_track, letter_template
from .writer import SyntheticWriter, sample_style
from stabpen import params as sp_params
from stabpen import plotstyle, provenance

LATENCIES = (0.05, 0.10, 0.15, 0.20, 0.30, 0.45, 0.60)
DEPTHS = (1, 2, 3)


def letter_times(wr):
    """(first touchdown, last lift) of every letter from the pen-down flags."""
    t, pdn = wr.intended.t, wr.intended.pen_down
    out = []
    for L in wr.letters:
        idx = np.flatnonzero(pdn[L.span[0]:L.span[1]]) + L.span[0]
        out.append((float(t[idx[0]]), float(t[idx[-1]])))
    return out


def lead_time_table(n_writers=24):
    rows = {f"d{d}_{mode}": {str(L): [] for L in LATENCIES} for d in DEPTHS for mode in ("optimistic", "conservative")}
    durations, gaps = [], []
    for w in range(n_writers):
        st = sample_style(np.random.default_rng(w))
        wtr = SyntheticWriter(st, seed=w)
        for i, s in enumerate(EVAL_LINES):
            wr = wtr.write(s, dt=1e-3, seed=2000 + 10 * w + i)
            lt = letter_times(wr)
            durations += [b - a for a, b in lt]
            gaps += [lt[k][0] - lt[k - 1][1] for k in range(1, len(lt))]
            for k in range(len(lt)):
                for d in DEPTHS:
                    if k - d < 0:
                        continue
                    t_opt = lt[k - d][1]
                    # conservative: letter k-d is known finished only when letter k-d+1 touches down;
                    # for d = 1 that is the touchdown of letter k itself, i.e. always too late
                    t_con = lt[k - d + 1][0]
                    for L in LATENCIES:
                        rows[f"d{d}_optimistic"][str(L)].append(lt[k][0] - t_opt >= L)
                        rows[f"d{d}_conservative"][str(L)].append(lt[k][0] - t_con >= L)
    table = {k: {L: float(np.mean(v)) for L, v in d.items()} for k, d in rows.items()}
    return table, {"letter_duration_s": {"median": float(np.median(durations)), "p10": float(np.percentile(durations, 10)),
                                         "p90": float(np.percentile(durations, 90))},
                   "pen_up_gap_s": {"median": float(np.median(gaps)), "p10": float(np.percentile(gaps, 10)),
                                    "p90": float(np.percentile(gaps, 90))}}


def measured_latencies(pred):
    sp_ = corpus.make_splits()
    ctx = [c for c, _ in lm.glyph_positions(sp_.test[:60], 2)][:200]
    t_pred = adapter.time_predictor(pred, ctx, d=2)
    t_pred1 = adapter.time_predictor(pred, ctx, d=1)
    st = sample_style(np.random.default_rng(0))
    wtr = SyntheticWriter(st, seed=0)
    cal = wtr.write(CALIB_SENTENCE, dt=1e-3, seed=1)
    obs, _ = observe(cal, 3e-4, 6.0, np.random.default_rng(0))
    est = StyleEstimator()
    t_upd = []
    for L, (strokes, times, _d) in zip(cal.letters, obs):
        t0 = time.perf_counter()
        est.update(L.char, strokes, t_strokes=times)
        t_upd.append(time.perf_counter() - t0)
    e = est.estimate()
    t_syn = []
    for c in "abcdefghijklmnopqrstuvwxyz":
        t0 = time.perf_counter()
        t = anchor_to(letter_template(c, e, 0, 0, estimator=est, mode="exemplar"), (0.0, 0.0))
        build_track([t], speed=e.speed, air_speed=e.air_speed)
        t_syn.append(time.perf_counter() - t0)
    return {"predictor_glyph_depth2": t_pred, "predictor_glyph_depth1": t_pred1,
            "style_update_per_letter_ms": {"median": float(np.median(t_upd) * 1e3), "p95": float(np.percentile(t_upd, 95) * 1e3)},
            "template_synthesis_per_letter_ms": {"median": float(np.median(t_syn) * 1e3), "p95": float(np.percentile(t_syn, 95) * 1e3)},
            "machine": "this container, CPython + numpy, single thread; a phone will differ"}, est


def bandwidth_study(est, n_writers=6):
    rows = []
    for w in range(n_writers):
        st = sample_style(np.random.default_rng(w))
        wr = SyntheticWriter(st, seed=w).write(GUIDE_SENTENCE, dt=1e-3, seed=2000 + w)
        e = est.estimate()
        letters = [(anchor_to(letter_template(L.char, e, 0, 0, estimator=est, mode="exemplar"), L.polylines[0][0]).strokes, 0.8)
                   for L in wr.letters]
        rows.append(IT.bandwidth(letters, writing_time_s=float(wr.intended.t[-1])))
    keys = [k for k, v in rows[0].items() if isinstance(v, float)]
    return {k: float(np.mean([r[k] for r in rows])) for k in keys} | {"note": rows[0]["note"],
                                                                     "resend_factor": rows[0]["resend_factor"]}


def model_sizes(pred):
    buf = io.BytesIO()
    pred.char.to_npz(buf)
    pred.word._cache.clear()                        # the per-context probability cache is not part of the model
    wbuf = pickle.dumps(pred.word, protocol=pickle.HIGHEST_PROTOCOL)
    mlp = sp.MLPPredictor()
    return {"char_kn7_npz_bytes": len(buf.getvalue()), "char_kn7_ngrams": pred.char.n_params(),
            "word_kn2_pickle_bytes": len(wbuf), "word_vocab": len(pred.word.vocab) - 1,
            "stroke_mlp_params": mlp.n_params(), "stroke_mlp_int8_bytes": mlp.n_params(), "stroke_mlp_macs": mlp.macs()}


def example_record():
    from .glyphs import GLYPH_SET
    h = 2.6e-3
    strokes = [np.column_stack([h * s[:, 0], h * s[:, 1]]) for s in GLYPH_SET["t"]]
    recs = IT.encode_letter(strokes, seg_id=42, glyph="t", confidence=0.86, t_from_ms=61_250, t_to_ms=62_400,
                            speed_mm_s=28)
    return {"letter": "t", "records": len(recs), "framed_bytes": [len(r.framed()) for r in recs],
            "first_record_hex": recs[0].framed().hex(), "header_fields": list(IT.HDR.format)}


def figure(table, path, lead):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for i, d in enumerate(DEPTHS):
        c = plotstyle.SERIES[i]
        xs = list(LATENCIES)
        ax.plot(xs, [table[f"d{d}_optimistic"][str(L)] for L in xs], color=c, label=f"depth {d}: letter done at its last lift")
        ax.plot(xs, [table[f"d{d}_optimistic"][str(L)] for L in xs], **plotstyle.marker_kw(c))
        ax.plot(xs, [table[f"d{d}_conservative"][str(L)] for L in xs], color=c, lw=1.2, ls="--",
                label=f"depth {d}: done at the next touchdown")
    ax.axvline(lead, color=plotstyle.STATUS["critical"], lw=1, ls=":")
    ax.text(lead + 0.005, 0.03, "template_lead\n(config/pencil.yaml)", fontsize=7, color=plotstyle.INK2)
    ax.set_xlabel("end-to-end latency from evidence to template on the pen (s)")
    ax.set_ylabel("letters whose template arrives before touchdown")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "CALCULATION", "synthetic writers' timing, 24 writers x 4 lines")
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    t0 = time.time()
    pencil = sp_params.load(os.path.join(sp_params.REPO_ROOT, "config", "pencil.yaml"))
    lead = float(pencil["ai.template_lead"])
    c_full = float(pencil["ai.confidence_full"])
    pred = lm.cached_predictor()
    table, timing = lead_time_table()
    lat, est = measured_latencies(pred)
    bw = bandwidth_study(est)
    budget = adapter.LatencyBudget(template_lead=lead)
    res = {"meta": provenance.metadata(EVIDENCE_CALC, seeds={"writers": "0-23", "instances": "2000+10w+i"},
                                       extra={"pencil_params": pencil.version()}),
           "inputs": {"template_lead_s": lead, "confidence_full": c_full, "travel_nib_m": float(pencil["stage.travel_nib"])},
           "writing_timing": timing, "template_on_time_fraction": table, "latencies_measured": lat,
           "latency_budget_allocations": {k: getattr(budget, k) for k in budget.__dataclass_fields__} |
                                         {"total": budget.total(), "margin": budget.margin()},
           "bandwidth": bw, "model_sizes": model_sizes(pred), "stroke_mcu_budget": sp.mac_budget(3, 24, 21, sp.MLPPredictor().macs()),
           "icd_0x06_example": example_record(),
           "llm_adapter_specs": {s.model_id: {"locality": s.locality, "p95_latency_budget_s": s.p95_latency_budget_s,
                                              "requires_consent": s.requires_consent, "use": s.notes.get("use")}
                                 for s in (adapter.PHONE_LLM_SPEC, adapter.CLOUD_LLM_SPEC)},
           "runtime_s": 0.0}
    res["runtime_s"] = round(time.time() - t0, 1)
    provenance.write_json(str(RESULTS_DIR / "deployment.json"), res)
    figure(table, RESULTS_DIR / "fig_lead_time.png", lead)
    for k in ("d1_optimistic", "d2_optimistic", "d2_conservative", "d3_conservative"):
        print(k, {L: round(v, 2) for L, v in table[k].items()})
    print(timing, lat, bw, sep="\n")
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
