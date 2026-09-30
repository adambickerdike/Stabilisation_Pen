"""Proposed ledger rows of study X (results/rebaseline/evidence_rows.csv; derived from this study's simulations, no new
literature).  The numbers are read from results/rebaseline/*.json when the rows are written, so the rows always match
the results files."""
from __future__ import annotations

from typing import Dict, List, Optional

from . import RESULTS_DIR
from . import common as CM


def _r(name: str) -> Dict:
    return CM.jload(RESULTS_DIR / f"{name}.json") or {}


def _f(x, nd=2) -> str:
    return "n/a" if x is None else f"{float(x):.{nd}f}"


BASE = {"year": "2026", "source_type": "derived calculation", "evidence_class": "numerical simulation",
        "access_level": "full text", "retrieved": "2026-09-30", "search_query": "n/a (derived)", "stream": "EML",
        "lead_verification": "", "transferability": "low",
        "transferability_reason": "Simulation on the stated inputs; not a measurement of a pen or of any person"}


def row_sim2j(s: Dict) -> Optional[Dict]:
    bm = s.get("by_mode") or {}
    c = ((bm.get("causal") or {}).get("cards") or {}).get("headline_8_12Hz_1_2mm")
    l = ((bm.get("legacy_flags") or {}).get("cards") or {}).get("headline_8_12Hz_1_2mm")
    h = (((s.get("historical") or {}).get("summary") or {}).get("cards") or {}).get("headline_8_12Hz_1_2mm")
    if not c:
        return None
    cw = (bm.get("causal") or {}).get("clean_writing") or {}
    cb = c.get("ratio_writer_boot") or {}
    return dict(BASE, id="EML-110",
                topic="Rev J + the guarded tracker G4 in the whole-pen physics simulation, rerun with causal sensing "
                      "(study X, sim2j headline card)",
                citation="This study's simulation (rebaseline/sim2j_cards.py): sim2 / MuJoCo whole Rev J pen, sim2j "
                         "firmware, the frozen G4 tracker, causal Hall velocity, delayed measured contact, 80 Hz inner loop",
                doi_or_url="results/rebaseline/sim2j_cards.json",
                task_or_setup="Essential tremor 8-12 Hz x 1-2 mm on the H1 hand, v2 synthetic test writers 0-5 on their "
                              "first test seed (the historical cases, paired), 'return library' after a 4 s rest; the same "
                              "cases with the legacy optimistic flags on the same code, and with the historical firmware "
                              "contact channel (exact reproduction)",
                participants_or_bench="Simulated (synthetic writers and synthetic tremor)",
                comparator="The same pen with the nose held (ordinary-pen column); perfect knowledge; the historical rows",
                key_quantitative_findings=(
                    f"Ink error with G4 / held nose: causal {_f(c.get('ratio_mean'), 3)} (writer bootstrap "
                    f"{_f(cb.get('lo'), 3)}-{_f(cb.get('hi'), 3)}; {c.get('n_cases')} cases), legacy flags "
                    f"{_f((l or {}).get('ratio_mean'), 3)}, historical {_f((h or {}).get('ratio_mean'), 3)}; words of 10 "
                    f"{_f(c['words_of_10'][0], 1)} -> {_f(c['words_of_10'][1], 1)} (historical "
                    f"{_f((h or {}).get('words_of_10', [None, None])[0], 1)} -> {_f((h or {}).get('words_of_10', [None, None])[1], 1)}); "
                    f"letters {_f(c['letters_of_10'][0], 1)} -> {_f(c['letters_of_10'][1], 1)}; perfect knowledge "
                    f"{_f(c.get('oracle_ratio_mean'), 3)}; clean writing moved {_f(cw.get('moved_um_mean'), 1)} um (max "
                    f"{_f(cw.get('moved_um_max'), 1)}); mean power {_f(c['P_total_W'][0])} -> {_f(c['P_total_W'][1])} W "
                    f"(legacy {_f((l or {}).get('P_total_W', [None, None])[0])} W)"),
                units_and_conditions="Ratio of rms ink error to the clean-ink letters (lower is better); words and letters "
                                     "read by the app's recogniser, of 10; W incl. 0.077 W electronics; SIMULATION",
                locator="docs/rebaseline.md section 3",
                limitations="Synthetic writers and tremor; one seed per writer; the static ball load of the C1S nose still "
                            "dominates power; the nib is Rev J's, not the balanced nib; no measurement",
                relevance_to_design="Whether the explainer's biggest positive result survives realistic sensing",
                design_implication="G4's synthetic-tremor card is reported with causal sensing; legacy numbers become an "
                                   "optimistic bound (DEC-070)")


def row_bnib(s: Dict) -> Optional[Dict]:
    cf = s.get("configs") or {}
    rk = ((cf.get("revK_corrected") or {}).get("all_writers") or {}).get("pooled_4_cells")
    c15 = ((cf.get("cand15_corrected") or {}).get("all_writers") or {}).get("pooled_4_cells")
    if not rk:
        return None
    rkc = ((cf.get("revK_corrected") or {}).get("all_writers") or {}).get("clean") or {}
    return dict(BASE, id="EML-111",
                topic="The balanced nib (Rev K and the 24 mm / 1.5 mm candidate) in sim2 with causal contact, DEC-066's "
                      "40/46 Hz servo and corrected loads (study X; synthetic-input half of EXP-E23)",
                citation="This study's simulation (rebaseline/bnib_rerun.py): study B's sim2 set-up (bnib/sim.py) with "
                         "nonlinear wire force (revk/feasibility.wire_anchor) and 8.07 mN guide rolling drag per step",
                doi_or_url="results/rebaseline/bnib_rerun.json",
                task_or_setup="ET 8 and 12 Hz x 1 and 2 mm, v2 synthetic test writers, G4 tracker, study B's DeltaPen-"
                              "calibrated page sensor; nib held, G4, perfect knowledge; tremor-free writing",
                participants_or_bench="Simulated (synthetic writers and tremor)",
                comparator="Study B's published B1 (80/100 Hz, linear wires, no drag, true-contact gate)",
                key_quantitative_findings=(
                    f"Rev K corrected: ink ratio G4 {_f(rk.get('ratio_G4'), 3)}, perfect knowledge "
                    f"{_f(rk.get('ratio_oracle'), 3)}, words {_f(rk.get('words_off'), 1)} -> {_f(rk.get('words_G4'), 1)} of 10, "
                    f"nib power {_f(rk.get('P_nib_mW_G4'), 1)} mW, clean writing moved {_f(rkc.get('moved_um_mean'), 1)} um. "
                    + (f"1.5 mm candidate: G4 {_f(c15.get('ratio_G4'), 3)}, perfect knowledge {_f(c15.get('ratio_oracle'), 3)}, "
                       f"words {_f(c15.get('words_off'), 1)} -> {_f(c15.get('words_G4'), 1)}, {_f(c15.get('P_nib_mW_G4'), 1)} mW"
                       if c15 else "")),
                units_and_conditions="Ratios of rms ink error to the held nib's; words of 10 (app recogniser); mW copper "
                                     "loss at the x-axis force constant; SIMULATION",
                locator="docs/rebaseline.md section 4",
                limitations="Synthetic inputs; isotropic force constant in sim2 (weaker axis and disk minimum as CALC "
                            "scalings); guide drag coefficient and wire material unmeasured; no carrier structural modes",
                relevance_to_design="The balanced nib's tremor benefit and power under the corrected loads and servo",
                design_implication="See DEC-077 (proposed)")


def row_reach(s: Dict) -> Optional[Dict]:
    ag = (s or {}).get("aggregate") or {}
    rows = ag.get("rows") or {}
    k1, k2 = rows.get("B1k|1.0587|oracle"), rows.get("B1c|1.5|oracle")
    if not k1:
        return None
    g = lambda r, k: ((r or {}).get(k) or {})          # noqa: E731
    return dict(BASE, id="EML-112",
                topic="The reach a balanced nib needs at the severe class, with its own servo bandwidth and moving mass "
                      "(study X; study F's reach check redone)",
                citation="This study's simulation (rebaseline/reach_b1.py): model HW1 with study R's real inputs, study F's "
                         "20 tuning cases, perfect knowledge, B1's 40/46 Hz servo and 3.44 / 3.67 g",
                doi_or_url="results/rebaseline/reach_b1.json",
                task_or_setup="Severe class (1.72 mm at the tip), PD and ET, 10 tuning notes; travel +-1.0, +-1.06, +-1.5 mm",
                participants_or_bench="Simulated (real recorded inputs: UNIPEN hpb2 writers, UCI PD tip tremor, Zenodo ET)",
                comparator="The ordinary pen (study F's reading of the same cases); study F's Rev J nose with its travel cut",
                key_quantitative_findings=(
                    f"+-1.06 mm (Rev K): tip tremor {_f(g(k1, 'tip_tremor_mm').get('mean'))} mm, words gained "
                    f"{_f(g(k1, 'gain_read').get('mean'), 1)} ({_f(g(k1, 'gain_read').get('lo'), 1)} to "
                    f"{_f(g(k1, 'gain_read').get('hi'), 1)}); +-1.5 mm (candidate): tip tremor "
                    f"{_f(g(k2, 'tip_tremor_mm').get('mean'))} mm, words gained {_f(g(k2, 'gain_read').get('mean'), 1)} "
                    f"({_f(g(k2, 'gain_read').get('lo'), 1)} to {_f(g(k2, 'gain_read').get('hi'), 1)})"),
                units_and_conditions="mm peak (sqrt(2) x rms of the major axis, f0 +- 2 Hz); words of 10 read by study R's "
                                     "literal AI reader; SIMULATION",
                locator="docs/rebaseline.md section 5",
                limitations="HW1's idealised inner loop and linear suspension; perfect knowledge (a mechanism bound, not "
                            "a tracker); tuning split only; AI reader stands in for people",
                relevance_to_design="Whether the next nib can meet DEC-055's words line at the severe class at all",
                design_implication="See DEC-078 (proposed)")


def _clean(ver: Dict, dev: str) -> Optional[float]:
    v = ((ver.get("clean") or {}).get(dev) or {}).get("false_correction_um")
    return v.get("mean") if isinstance(v, dict) else v


def row_page(s: Dict) -> Optional[Dict]:
    re_ = (s or {}).get("R_and_E") or {}
    v1, v2 = re_.get("v1") or {}, re_.get("v2") or {}
    if not v2:
        return None
    sev1 = (v1.get("cards") or {}).get("all/severe") or {}
    sev2 = (v2.get("cards") or {}).get("all/severe") or {}
    d1 = (v1.get("dec055") or {}).get("revJ_new|deltapen") or {}
    d2 = (v2.get("dec055") or {}).get("revJ_new|deltapen") or {}
    return dict(BASE, id="EML-113",
                topic="Studies R, E and F's DeltaPen-class page-sensor rows re-analysed with the causal page model v2 "
                      "(study X)",
                citation="This study's simulation (rebaseline/page_v2.py): model HW1 with study R's real inputs, R's case "
                         "keys and seeds, realdata/sensors.py version 2",
                doi_or_url="results/rebaseline/page_v2.json",
                task_or_setup="R's 54 test cases, 9 clean notes and 8 bridge cases; E's frozen designs; F's 38 gap cases",
                participants_or_bench="Simulated (real recorded inputs; the test split already spent: a re-analysis)",
                comparator="The same cases with page model v1 (as published) and the ideal page sensor",
                key_quantitative_findings=(
                    "Severe class tip tremor v1 -> v2: " + "; ".join(
                        f"{k} {_f((sev1.get(k) or {}).get('tip_tremor_mm'))} -> {_f((sev2.get(k) or {}).get('tip_tremor_mm'))} mm"
                        for k in ("revJ_gated|deltapen", "revJ_tcn|deltapen", "revJ_new|deltapen") if sev2.get(k))
                    + f". DEC-055 for E's frozen design: words gain {_f(d1.get('words_gain_mean'))} -> "
                      f"{_f(d2.get('words_gain_mean'))}, passes {d1.get('passes')} -> {d2.get('passes')}. Clean real writing "
                      f"moved by Rev J's gated tracker {_f(_clean(v1, 'revJ_gated|deltapen'), 1)} -> "
                      f"{_f(_clean(v2, 'revJ_gated|deltapen'), 1)} um (worst writer "
                      f"{_f(((v1.get('clean') or {}).get('revJ_gated|deltapen') or {}).get('false_correction_um_worst_writer'), 0)} -> "
                      f"{_f(((v2.get('clean') or {}).get('revJ_gated|deltapen') or {}).get('false_correction_um_worst_writer'), 0)} um)"),
                units_and_conditions="mm peak at the tip; words of 10 (literal AI reader); SIMULATION",
                locator="docs/rebaseline.md section 6",
                limitations="Page model v2 is an ASSUMPTION informed by LIT OPT-02, not a calibrated paper sensor; spent test "
                            "split; composed inputs",
                relevance_to_design="Whether the real-input conclusions depended on the non-causal page model",
                design_implication="See DEC-079 (proposed)")


def row_ladder(s: Dict) -> Optional[Dict]:
    """EML-114: what each correction did to the balanced nib (the attribution ladder, writers 0-1)."""
    cf = (s or {}).get("configs") or {}
    steps = [c for c in ("B1_studyB_now", "B1_dec066", "revK_linear", "revK_corrected", "cand15_corrected") if c in cf]
    if len(steps) < 3:
        return None
    rp = (s or {}).get("reproduction_vs_studyB_rows") or {}
    sb = (((s or {}).get("studyB_rows") or {}).get("writers_0_1") or {}).get("pooled_4_cells") or {}

    def one(c):
        p = ((cf[c].get("studyB_cells_writers_0_1") or {}).get("pooled_4_cells")) or {}
        return (f"{c}: G4 {_f(p.get('ratio_G4'), 3)}, perfect knowledge {_f(p.get('ratio_oracle'), 3)}, words "
                f"{_f(p.get('words_off'), 1)} -> {_f(p.get('words_G4'), 1)}, nib {_f(p.get('P_nib_mW_G4'), 1)} mW")
    return dict(BASE, id="EML-114",
                topic="Which correction moved the balanced nib's simulated card: sensing, servo bandwidth, nib constants, "
                      "loads (study X attribution ladder)",
                citation="This study's simulation (rebaseline/bnib_rerun.py): study B's bnib/sim.py configured one change "
                         "at a time, with a reproduction of study B's own rows first",
                doi_or_url="results/rebaseline/bnib_rerun.json",
                task_or_setup="ET 8 Hz x 1 and 2 mm and 12 Hz x 1 mm (study B's cells), writers 0-1, G4 and perfect knowledge",
                participants_or_bench="Simulated (synthetic writers and tremor)",
                comparator="Study B's rows (bnib/build/sim_rows.json)",
                key_quantitative_findings=(
                    f"Reproduction of study B's rows: {rp.get('n')} rows, largest ink difference "
                    f"{_f(rp.get('max_abs_diff_um'), 4)} um. Study B: G4 {_f(sb.get('ratio_G4'), 3)}, perfect knowledge "
                    f"{_f(sb.get('ratio_oracle'), 3)}, {_f(sb.get('P_nib_mW_G4'), 1)} mW. " + "; ".join(one(c) for c in steps)),
                units_and_conditions="Ratios of rms ink error to the held nib's; words of 10 (app recogniser); mW copper "
                                     "loss at the simulated force constant; SIMULATION",
                locator="docs/rebaseline.md section 4",
                limitations="Two writers, one seed; synthetic inputs; isotropic force constant",
                relevance_to_design="Separates the effect of causal sensing, DEC-066's servo, Rev K's constants and the loads",
                design_implication="See DEC-077 (proposed)")


def row_gap(s: Dict) -> Optional[Dict]:
    """EML-115: study F's gap rows and page sensing check with page model version 2."""
    g = (s or {}).get("F_gap") or {}
    sp = g.get("splits") or {}
    if not sp:
        return None
    te = (sp.get("test") or {}).get("configs") or {}
    tu = (sp.get("tuning") or {}).get("configs") or {}
    pa = lambda d: (d.get("page_ar_trem_deltapen") or {})          # noqa: E731
    sc = (g.get("sensing_check_page") or {})
    v2 = ((sc.get("v2") or {}).get("deltapen") or {})
    v1 = ((sc.get("v1_published") or {}).get("deltapen") or {})
    est = [abs((v.get("tip_tremor_mm_v2") or 0) - (v.get("tip_tremor_mm_v1") or 0))
           for d in (te, tu) for k, v in d.items() if v.get("page_dependent") and not k.startswith("page_ar")]
    return dict(BASE, id="EML-115",
                topic="Study F's gap decomposition and page sensing check with the causal page model v2 (study X)",
                citation="This study's simulation (rebaseline/page_v2.py): readable/gap.py's cases with realdata/sensors.py "
                         "version 2 installed (anchored at the first valid report)",
                doi_or_url="results/rebaseline/page_v2.json",
                task_or_setup="Study F's 20 tuning and 18 test severe cases (PD and ET); the page sensing check on the "
                              "tuning split (tremor alone, cross-fitted)",
                participants_or_bench="Simulated (real recorded inputs)",
                comparator="Study F's published version-1 values; the ideal page sensor",
                key_quantitative_findings=(
                    f"Estimators fed the DeltaPen-class streams change by at most {_f(max(est) if est else None, 3)} mm; "
                    f"page-position predictor on the tremor alone {_f(pa(tu).get('tip_tremor_mm_v1'), 3)} -> "
                    f"{_f(pa(tu).get('tip_tremor_mm_v2'), 3)} mm (tuning), {_f(pa(te).get('tip_tremor_mm_v1'), 3)} -> "
                    f"{_f(pa(te).get('tip_tremor_mm_v2'), 3)} mm (test); sensing check tip tremor "
                    f"{_f(v1.get('tip_tremor_mm'), 3)} -> {_f(v2.get('tip_tremor_mm'), 3)} mm; configurations that do not "
                    f"read the page position unchanged (0.000 mm)"),
                units_and_conditions="mm peak at the tip (R's measure); SIMULATION",
                locator="docs/rebaseline.md section 6",
                limitations="Spent test split; page model v2 is an ASSUMPTION; version 2 needed an anchoring workaround",
                relevance_to_design="Whether the DeltaPen-class sensor can serve as the tremor reference",
                design_implication="See DEC-079 (proposed)")


def row_sim2j_more(s: Dict) -> Optional[Dict]:
    """EML-116: sim2j's other cards under causal sensing (mild, slow, severe, autowrite)."""
    c = ((s or {}).get("by_mode") or {}).get("causal") or {}
    h = (((s or {}).get("historical") or {}).get("summary") or {})
    cc, hc = c.get("cards") or {}, h.get("cards") or {}
    if not cc.get("severe_autowrite") or not cc.get("et_mild"):
        return None
    g = lambda d, k, i=None: (d.get(k) if i is None else (d.get(k) or [None, None])[i])      # noqa: E731
    m, sl, sv, aw, a0 = (cc.get(k) or {} for k in ("et_mild", "slow_4hz", "severe_through", "severe_autowrite",
                                                     "autowrite_no_tremor"))
    hsv, haw = hc.get("severe_through") or {}, hc.get("severe_autowrite") or {}
    return dict(BASE, id="EML-116",
                topic="Rev J's other synthetic cards under causal sensing: mild and slow tremor, writing through severe "
                      "tremor, autowrite (study X)",
                citation="This study's simulation (rebaseline/sim2j_cards.py): sim2 / MuJoCo whole Rev J pen, causal Hall "
                         "velocity, delayed measured contact, 80 Hz inner loop; paired with sim2j's historical rows",
                doi_or_url="results/rebaseline/sim2j_cards.json",
                task_or_setup="ET 0.3 mm at 4/8/12 Hz, 4 Hz x 1-2 mm, 3 mm at 5 and 8 Hz (G4 writing through it; the nose "
                              "writing a known text), v2 synthetic test writers 0-5 on their first test seed",
                participants_or_bench="Simulated (synthetic writers and tremor)",
                comparator="The historical rows of the same cases (legacy sensing)",
                key_quantitative_findings=(
                    f"Mild ratio {_f(m.get('ratio_mean'), 3)} (historical 1.010); slow {_f(sl.get('ratio_mean'), 3)} "
                    f"(1.000); severe words {_f(g(sv, 'words_of_10', 0), 1)} -> {_f(g(sv, 'words_of_10', 1), 1)} of 10 "
                    f"(historical {_f(g(hsv, 'words_of_10', 0), 1)} -> {_f(g(hsv, 'words_of_10', 1), 1)}); autowrite at 3 mm "
                    f"{_f(g(aw, 'words_of_10', 1), 1)} of 10 words (historical {_f(g(haw, 'words_of_10', 1), 1)}), ink to the "
                    f"planned letters {_f((g(aw, 'err_mm', 1) or 0) * 1e3, 0)} um (historical "
                    f"{_f((g(haw, 'err_mm', 1) or 0) * 1e3, 0)} um); no tremor {_f(g(a0, 'words_of_10', 1), 1)} of 10"),
                units_and_conditions="Ink-error ratios to the held nose; words of 10 (app recogniser); SIMULATION",
                locator="docs/rebaseline.md section 3",
                limitations="Synthetic inputs; one seed per writer; the C1S nose is a bench module only (DEC-050); in-pen "
                            "autowrite is superseded (DEC-071)",
                relevance_to_design="Whether the rest of sim2j's cards depended on ideal sensing",
                design_implication="Autowrite's accuracy depends on the nib servo's sensing (cause not split); see DEC-075 "
                                   "(proposed)")


def rows() -> List[Dict]:
    out = []
    for fn, name in ((row_sim2j, "sim2j_cards"), (row_bnib, "bnib_rerun"), (row_reach, "reach_b1"), (row_page, "page_v2"),
                     (row_ladder, "bnib_rerun"), (row_gap, "page_v2"), (row_sim2j_more, "sim2j_cards")):
        r = fn(_r(name))
        if r:
            out.append(r)
    return out
