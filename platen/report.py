"""results/platen/*.json with stabpen.provenance, the figures with CSV twins, the proposed ledger rows, the tables of
docs/platen_concept.md (platen/build/doc_tables.md)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import EVIDENCE_CALC, EVIDENCE_SIM, REPO_ROOT
from . import common as CM


def provenance(quick: bool, status: str) -> Dict:
    from stabpen import provenance as PV
    extra = {"package": "platen", "quick": quick,
             "split": "study R's TUNING split only (study E's selection set); the test split is spent and was not used",
             "inputs_sha256": {
                 "results/readable/frozen.json": CM.sha256_file(CM.F_FROZEN),
                 "results/realtrack/frozen.json": CM.sha256_file(CM.E_FROZEN),
                 "results/improvement/mechanics/grounded_batch.json": CM.sha256_file(CM.GROUNDED_BATCH),
                 "results/improvement/mechanics/grounded_derivative_check.json": CM.sha256_file(CM.GROUNDED_DERIV),
                 "results/improvement/writing/grounded_accepted/manifest.json": CM.sha256_file(CM.SE_MANIFEST)},
             "reused_read_only": ["handwriting/ (model HW1)", "realdata/ (library, measures, reader)",
                                  "realtrack/ (cases, estimators, frozen designs)", "readable/ (common, reach, curve; "
                                  "per-case caches of study F)", "ai3/ (accepted references)", "aiprior/, fusion/, ai2/"],
             "seeds": "per case: sha1 of the case id and the run tag (platen/common.h); bootstrap seed 20260929 (R's)"}
    try:
        import torch
        extra["torch"] = torch.__version__
    except Exception:
        pass
    return PV.metadata(status, seeds="per-case hashed seeds (see split/seeds)", extra=extra)


def example_traces(quick: bool) -> List[Dict]:
    from . import accepted as A
    preds = A.predictors(quick)
    se = A.se_references()
    out = []
    for hk, cfg, title in (("still", "proposed", "still hand, proposed platen"),
                           ("sev_ET", "proposed", "severe ET, proposed platen"),
                           ("still", "relaxed_naive", "still but relaxed hand, tip following")):
        m = A.run_one(se[0], hk, cfg, preds, keep=True)
        tr = m.pop("_trace")
        tr["title"] = f"{title} ({'complete' if m['engineering_complete'] else 'not complete'}; RMS " + \
                      (f"{m['actual_requested_ink_rms_error_mm']:.3f} mm)" if m['actual_requested_ink_rms_error_mm']
                       is not None else "n/a)")
        out.append(tr)
    return out


def comparison(res: Dict) -> Dict:
    """The product-fit comparison (handheld nib, five-bar, platen, typing and dictation) per user need, with the key
    numbers of this study and the earlier ones and their labels."""
    tr = (res.get("tremor") or {}).get("by_class", {}).get("all/severe", {})
    acc = (res.get("accepted") or {}).get("summary", {})
    f = lambda k, m="tip_tremor_mm", nd=2: CM.fmt_ci((tr.get(k) or {}).get(m), nd)            # noqa: E731
    w = lambda k: CM.fmt_ci((tr.get(k) or {}).get("words_read"), 1)                            # noqa: E731
    a = lambda t, c, h: acc.get(f"{t}|{c}|{h}") or {}                                            # noqa: E731

    def comp(t, c, h):
        s = a(t, c, h)
        return f"{s['engineering_complete']}/{s['n']}" if s else "not run"
    five = {r["grip_stiffness_N_m"]: r for r in ((res.get("fivebar") or {}).get("summary") or []) if r.get("feedforward")}
    fb = lambda g: f"{five[g]['engineering_complete']}/{five[g]['words']}" if g in five else "n/a"   # noqa: E731
    return {
        "label": "Comparison built from SIMULATION results (this study, studies F and E, the independent pass) and "
                 "ASSUMPTION or LITERATURE judgements; nothing measured",
        "rows": [
            {"need": "Severe-tremor legibility (free writing, 1.72 mm at the tip)",
             "nib": f"Rev K +-1.0 mm: perfect knowledge {f('F10_oracle')} mm left, {w('F10_oracle')} words of 10 (F); "
                    f"+-1.5 mm candidate: {f('F15_oracle')} mm, {w('F15_oracle')} words; with E's design +-1.5 mm: "
                    f"{f('N15_E_chosen')} mm, {w('N15_E_chosen')} words (SIM, tuning)",
             "fivebar": "Not a tremor canceller: it moves the pen through the hand; 0/20 accepted words against a 200 "
                        "or 500 N/m grip (the independent pass, SIM)",
             "platen": f"Perfect knowledge {f('P_oracle')} mm, {w('P_oracle')} words; perfect separation with the "
                       f"camera {f('P_cam_sep')} mm, {w('P_cam_sep')} words; with E's design {f('P_E_chosen')} mm, "
                       f"{w('P_E_chosen')} words (SIM, tuning): reach solved, separation not",
             "typing_dictation": "Legible by construction (typed or dictated text); keyboards also suffer from tremor "
                                 "and dictation needs clear speech and privacy (ASSUMPTION; no ledger numbers); paper "
                                 "forms, cards and signatures still need ink",
             "ordinary_pen": f"{f('none')} mm left, {w('none')} words of 10 (F's reading, same cases)"},
            {"need": "Signatures (about 20 mm tall, 3.2 s, 88 mm/s: ledger CON-08)",
             "nib": "Reach of +-1.0-1.5 mm limits severe tremor as for notes; no whole-signature authority",
             "fivebar": "Could draw a stored signature within its 60 x 40 mm patch if the hand does not resist; "
                        "grip resistance defeats it (SIM)",
             "platen": "Free signing: as free writing (estimator-limited). By template (the user's stored signature, "
                       "written under the held pen) as accepted writing; legally a machine-made mark (like an autopen) "
                       "unless the user's own motion drives it (ASSUMPTION; a legal question, EXP-PL09)",
             "typing_dictation": "Electronic signatures where accepted; paper forms still need ink"},
            {"need": "Accepted-word completion for dyslexia ('se' and 'library')",
             "nib": "0/20 'se' suffixes pass the whole-text preflight at +-1.06 mm (Rev K) and +-1.5 mm (the independent "
                    "pass's writing audit, SIM): the pen's reach cannot write whole letters",
             "fivebar": f"'se': {fb(0.0)} with no hand resistance, {fb(200.0)} at 200 N/m, {fb(500.0)} at 500 N/m (SIM)",
             "platen": (f"'se': proposed {comp('se', 'proposed', 'still')} (still), {comp('se', 'proposed', 'drift')} "
                        f"(drift); pen in a cradle {comp('se', 'cradle', 'cradle')}; relaxed hand with tip following "
                        f"{comp('se', 'relaxed_naive', 'still')}. 'library': proposed {comp('library', 'proposed', 'still')} "
                        f"(still) (SIM)"),
             "typing_dictation": "Spell checking and word prediction already do this for typed text (LITERATURE: "
                                 "ledger HAP-50, HAP-133, EML-63); a pen plotter writes accepted text on paper without "
                                 "the user's hand (MFR AMF-283)"},
            {"need": "Portability",
             "nib": "Pocketable pen, 24 mm x about 152 mm, battery (PROPOSED)",
             "fivebar": "Desk board about 170 x 165 mm with two motors; mains (PROPOSED)",
             "platen": "Desk appliance: base 380 x 300 mm, paper 66 mm above the desk, palm rest about 100 mm, a "
                       "folding camera post about 200 mm (CAD, PROPOSED); 4-5.5 kg (ASSUMPTION); mains, 6-25 W (CALC "
                       "on ASSUMPTION ranges); loose A5 sheets. A6 variant about 320 x 260 mm, 3-4 kg",
             "typing_dictation": "Phone, tablet or laptop"},
            {"need": "Price (estimate)",
             "nib": "not estimated here", "fivebar": "not estimated here (two Faulhaber 2224 motors, board)",
             "platen": "BOM about USD 900-2,200 at prototype quantities; retail about USD 1,500-3,000 (ASSUMPTION)",
             "typing_dictation": "Free to a few hundred USD (ASSUMPTION)"},
        ],
        "users": [
            "Home: letters, cards, forms and signatures written at a desk by people with severe tremor, if an estimator "
            "reaches the target; accepted-word completion for people with dyslexia who want their own handwriting on "
            "paper (with the pen held firmly or docked)",
            "Clinics: occupational therapy and research on handwriting under controlled tremor cancellation (the platen "
            "can replay perfect knowledge, which a pen cannot reach), assessment of how much tremor matters to a person",
            "Schools: a shared desk station for children with dysgraphia or dyslexia; size, price and supervision "
            "limit it to special-needs rooms",
            "Portability limits: a desk and mains power; loose A5 or A6 sheets only (no bound notebooks, bank counters, "
            "clipboards or envelopes already addressed); a few minutes to register a sheet",
        ],
    }


def write(quick: bool = False) -> Dict:
    from . import accepted as A
    from . import design as D
    from . import evidence as EV
    from . import figures as FG
    from . import sensitivity as S
    from . import tremor as T
    t0 = time.time()
    out = CM.out_dir(quick)
    res = {"summary_label": EVIDENCE_SIM, "design": D.summary(), "tremor": T.aggregate(quick),
           "accepted": A.aggregate(quick), "fivebar": A.fivebar(), "sensitivity": S.aggregate(quick),
           "predictors": {}, "timings": CM.jload(CM.cache_dir(quick) / "timings.json")}
    for p in sorted(CM.cache_dir(quick, "predictors").glob("*.json")):
        d = CM.jload(p)
        res["predictors"][p.stem] = {k: d[k] for k in ("cam_hz", "cam_latency_s", "noise_m", "horizon_s", "order",
                                                         "ridge", "cv_rms_m", "hold_rms_m", "with_drift", "rule")}
    res["comparison"] = comparison(res)
    res["f_curve"] = CM.f_curve()
    res["stabpen.provenance"] = provenance(quick, EVIDENCE_SIM + "; " + EVIDENCE_CALC)
    CM.jdump(out / "platen.json", res)
    des = {"stabpen.provenance": provenance(quick, "PROPOSED DESIGN with CALCULATION, MANUFACTURER, LITERATURE and "
                                                   "ASSUMPTION values (each labelled)"), **D.summary()}
    CM.jdump(out / "design.json", des)
    figs = [FG.fig_tremor(res["tremor"], res["f_curve"], out), FG.fig_reach(res["tremor"], res["sensitivity"],
                                                                           res["f_curve"], out),
            FG.fig_sensing(res["sensitivity"], res["f_curve"], out), FG.fig_accepted(res["accepted"], res["fivebar"], out)]
    try:
        figs.append(FG.fig_accepted_example(example_traces(quick), out))
    except Exception as e:                   # the example is illustration only
        CM.log(f"[report] example traces skipped: {e!r}")
    rows = EV.write(res, out / "evidence_rows.csv")
    from . import proposals as PRP
    PRP.write_csvs(res, out)
    CM.log(f"[report] {out / 'platen.json'}; {len([f for f in figs if f])} figures; {len(rows)} ledger rows "
           f"({time.time() - t0:.0f} s)")
    try:
        from . import doc
        doc.tables(res, quick)
        if doc.TEMPLATE.exists():             # --quick fills a copy under platen/build/quick, never docs/
            doc.fill(res, out=(CM.QUICK / "platen_concept.md") if quick else doc.DOC_PATH)
    except Exception as e:
        CM.log(f"[report] doc skipped: {e!r}")
    return res
