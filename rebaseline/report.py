"""The tables quoted by docs/rebaseline.md (rebaseline/build/doc_tables.md) and the proposed ledger rows
(results/rebaseline/evidence_rows.csv: docs/evidence.csv's 23-column header, CRLF line endings, ids EML-110...).
Every number is read from results/rebaseline/*.json; nothing is recomputed here (CALC formatting only).
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import BUILD_DIR, REPO_ROOT, RESULTS_DIR
from . import common as CM
from . import impact as IM


def _r(name: str) -> Dict:
    return CM.jload(RESULTS_DIR / f"{name}.json") or {}


def f(x, nd=2, pct=False) -> str:
    if x is None:
        return "–"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x != x:
        return "–"
    return f"{100 * x:.{nd}f} %" if pct else f"{x:.{nd}f}"


# ------------------------------------------------------------------ task 2
def sim2j_tables(s: Dict) -> str:
    if not s:
        return "(sim2j_cards.json missing)\n"
    out = []
    cards = ("headline_8_12Hz_1_2mm", "et_moderate", "et_strong", "et_mild", "slow_4hz")
    cols = [("historical (sim2j/build rows)", (s.get("historical") or {}).get("summary") or {})]
    for m in ("legacy_exact", "legacy_flags", "causal"):
        if m in s.get("by_mode", {}):
            cols.append((m, s["by_mode"][m]))
    out.append("| Card | Run | Cases | Words of 10: ordinary -> G4 | Letters of 10 | Error left, mm | Ratio to ordinary "
               "(95 % case / writer bootstrap) | Perfect knowledge ratio | Power, W: ordinary -> G4 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for cid in cards:
        for name, blk in cols:
            c = (blk.get("cards") or {}).get(cid)
            if not c:
                continue
            cb, wb = c.get("ratio_case_boot") or {}, c.get("ratio_writer_boot") or {}
            out.append(f"| {cid} | {name} | {c['n_cases']} | {f(c['words_of_10'][0], 1)} -> {f(c['words_of_10'][1], 1)} | "
                       f"{f(c['letters_of_10'][0], 1)} -> {f(c['letters_of_10'][1], 1)} | {f(c['err_mm'][0])} -> "
                       f"{f(c['err_mm'][1])} | **{f(c['ratio_mean'], 3)}** ({f(cb.get('lo'))}–{f(cb.get('hi'))} / "
                       f"{f(wb.get('lo'))}–{f(wb.get('hi'))}) | {f(c.get('oracle_ratio_mean'), 3)} | "
                       f"{f(c['P_total_W'][0])} -> {f(c['P_total_W'][1])} |")
    out.append("")
    out.append("| Run | Clean writing moved by G4, mean (max), um | Power on clean writing, W | Stale/warm-up servo ticks (max) |")
    out.append("|---|---|---|---|")
    for name, blk in cols:
        cw = blk.get("clean_writing") or {}
        out.append(f"| {name} | {f(cw.get('moved_um_mean'), 1)} ({f(cw.get('moved_um_max'), 1)}) | "
                   f"{f(cw.get('P_total_W_mean'))} | {blk.get('stale_or_warmup_ticks_max', '–')} |")
    out.append("")
    out.append("| Paired comparison (same writer, cell, seed) | Controller | Cases | Ratio difference (writer bootstrap) | "
               "Words of 10 difference | Ink error difference, um | Identical ink |")
    out.append("|---|---|---|---|---|---|---|")
    for name, blk in (s.get("paired") or {}).items():
        for scope in ("headline_cells", "all_cells"):
            for ctl, v in (blk.get(scope) or {}).items():
                rd, wd, ed = v.get("ratio_diff") or {}, v.get("words_of_10_diff") or {}, v.get("ink_err_um_diff") or {}
                out.append(f"| {name} ({scope}) | {ctl} | {v['n']} | {f(rd.get('mean'), 3)} ({f(rd.get('lo'), 3)}–"
                           f"{f(rd.get('hi'), 3)}) | {f(wd.get('mean'), 2)} | {f(ed.get('mean'), 1)} ({f(ed.get('lo'), 1)}–"
                           f"{f(ed.get('hi'), 1)}) | {f(v.get('exactly_equal_ink_share'), 0, pct=True)} |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ task 3
def bnib_tables(s: Dict) -> str:
    if not s:
        return "(bnib_rerun.json missing)\n"
    out = []
    sb = s.get("studyB_published") or {}
    out.append("| Configuration | Writers | ET cell | Ratio G4 (95 % case bootstrap) | Ratio perfect knowledge | Words of 10: "
               "held -> G4 (perfect) | Nib power G4, mW |")
    out.append("|---|---|---|---|---|---|---|")
    for k, v in (sb.get("by_cell") or {}).items():
        out.append(f"| study B B1 as published (80/100 Hz, linear wires, no drag) | 0-3 | {k} | {f(v.get('ratio_mean'), 3)} | "
                   f"{f(v.get('ratio_oracle'), 3)} | {f(10 * v['words_off'], 1)} -> {f(10 * v['words_nib'], 1)} "
                   f"({f(10 * v['words_oracle'], 1)}) | {f(v.get('P_mW'), 1)} |")
    for c, v in (s.get("configs") or {}).items():
        blk = v.get("all_writers") or {}
        for cell, x in (blk.get("cells") or {}).items():
            b = x.get("ratio_G4_boot") or {}
            out.append(f"| {c} | {blk.get('n_writers')} writers | {cell} | **{f(x.get('ratio_G4'), 3)}** ({f(b.get('lo'), 3)}–"
                       f"{f(b.get('hi'), 3)}) | {f(x.get('ratio_oracle'), 3)} | {f(x.get('words_off'), 1)} -> "
                       f"{f(x.get('words_G4'), 1)} ({f(x.get('words_oracle'), 1)}) | {f(x.get('P_nib_mW_G4'), 1)} |")
    out.append("")
    out.append("| Configuration | Writers | Pooled 4 cells: ratio G4 (writer bootstrap) | Perfect knowledge | Words held -> G4 "
               "| Clean writing moved, mean (max), um | Nib power: G4 / held / clean, mW | Battery h (G4) | Power bands (CALC), mW |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for c, v in (s.get("configs") or {}).items():
        for wkey in ("writers_0_3", "all_writers"):
            blk = v.get(wkey) or {}
            p = blk.get("pooled_4_cells") or {}
            if not p:
                continue
            wb = p.get("ratio_G4_writer_boot") or {}
            cl = blk.get("clean") or {}
            pb = v.get("power_bands") or {}
            bands = (f"weak axis {f(pb.get('weaker_axis_mW'), 1)}, disk min {f(pb.get('disk_minimum_mW'), 1)}, derated "
                     f"{f(pb.get('disk_minimum_derated_0p7_mW'), 1)}") if (pb and wkey == "all_writers") else "–"
            out.append(f"| {c} | {wkey.replace('_', ' ')} ({blk.get('n_writers')}) | **{f(p.get('ratio_G4'), 3)}** "
                       f"({f(wb.get('lo'), 3)}–{f(wb.get('hi'), 3)}) | {f(p.get('ratio_oracle'), 3)} | "
                       f"{f(p.get('words_off'), 1)} -> {f(p.get('words_G4'), 1)} | {f(cl.get('moved_um_mean'), 1)} "
                       f"({f(cl.get('moved_um_max'), 1)}) | {f(p.get('P_nib_mW_G4'), 1)} / {f(p.get('P_nib_mW_off'), 1)} / "
                       f"{f(cl.get('P_nib_mW'), 1)} | {f(p.get('battery_h_G4'), 1)} | {bands} |")
    rp = s.get("reproduction_vs_studyB_rows")
    if rp:
        out.append("")
        out.append(f"Reproduction check (B1_studyB_exact against study B's rows): {rp.get('n')} rows, largest ink-error "
                   f"difference {f(rp.get('max_abs_diff_um'), 6)} um.")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ task 4
def reach_tables(s: Dict) -> str:
    ag = (s or {}).get("aggregate")
    if not ag:
        return "(reach_b1.json missing)\n"
    out = ["| Pen (servo, moving mass) | Reach | Command | Tip tremor left, mm (writer bootstrap) | Time at the travel limit "
           "| Words read of 10 | Gain over ordinary pen, read | DEC-055 words line | Gain via the frozen curve |",
           "|---|---|---|---|---|---|---|---|---|"]
    names = {"revJ": "Rev J (80 Hz / 400 Hz, 2.10 g) - study F's pen", "B1k": "B1, Rev K nib (40 / 46 Hz, 3.44 g)",
             "B1c": "B1, 1.5 mm candidate (40 / 46 Hz, 3.67 g)"}
    for k, v in ag["rows"].items():
        pen, reach, cmd = k.split("|")
        t = v.get("tip_tremor_mm") or {}
        wr = v.get("words_read") or {}
        g = v.get("gain_read") or {}
        gc = v.get("gain_via_curve") or {}
        line = v.get("dec055_mechanism_line") or {}
        out.append(f"| {names.get(pen, pen)} | ±{reach} mm | {cmd} | **{f(t.get('mean'))}** ({f(t.get('lo'))}–{f(t.get('hi'))}) "
                   f"| {f((v.get('at_travel_limit') or {}).get('mean'), 0, pct=True)} | {f(wr.get('mean'), 1)} | "
                   f"{f(g.get('mean'), 1)} ({f(g.get('lo'), 1)}–{f(g.get('hi'), 1)}) | "
                   f"{('passes' if line.get('passes') else 'fails') if line else '–'} | {f(gc.get('mean'), 1)} "
                   f"({f(gc.get('lo'), 1)}–{f(gc.get('hi'), 1)}) |")
    pub = s.get("studyF_published") or {}
    out.append("")
    out.append("Study F as published (the Rev J pen with its travel cut): " + "; ".join(
        f"{k}: tip {f(v.get('tip_tremor_mm'))} mm, words read {f(v.get('words_read'), 1)}, gain {f(v.get('gain_read'), 1)}"
        for k, v in pub.items()) + f".  Reproduction of study F's runs here: largest tip-tremor difference "
        f"{f(ag.get('repro_vs_studyF_max_abs_mm'), 6)} mm.")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ task 5
def page_tables(s: Dict) -> str:
    if not s:
        return "(page_v2.json missing)\n"
    out = []
    re_ = s.get("R_and_E") or {}
    if re_:
        out.append("| Class | Device | v1: words of 10 (gain) | v2: words of 10 (gain, 95 % writer interval) | v1: tip tremor mm "
                   "(ratio) | v2: tip tremor mm (ratio) |")
        out.append("|---|---|---|---|---|---|")
        for cls in ("all/severe", "all/moderate", "all/mild"):
            c1 = ((re_.get("v1") or {}).get("cards") or {}).get(cls) or {}
            c2 = ((re_.get("v2") or {}).get("cards") or {}).get(cls) or {}
            for d in ("none", "revH_akf|deltapen", "revJ_gated|deltapen", "revJ_tcn|deltapen", "revJ_g4|deltapen",
                      "revJ_new|deltapen", "revJ_info_net|deltapen", "revJ_info_ungated_akf|deltapen", "revJ_oracle",
                      "revJ_gated", "revJ_new"):
                a, b = c1.get(d) or {}, c2.get(d) or {}
                if not a and not b:
                    continue
                ci = b.get("words_gain_ci") or [None, None]
                out.append(f"| {cls} | {d} | {f(a.get('words_of_10'), 1)} ({f(a.get('words_gain'), 2)}) | "
                           f"{f(b.get('words_of_10'), 1)} ({f(b.get('words_gain'), 2)}; {f(ci[0], 2)} to {f(ci[1], 2)}) | "
                           f"{f(a.get('tip_tremor_mm'))} ({f(a.get('tip_tremor_ratio'), 3)}) | "
                           f"{f(b.get('tip_tremor_mm'))} ({f(b.get('tip_tremor_ratio'), 3)}) |")
        out.append("")
        out.append("| Device | v1: clean writing moved, um (worst writer) | v2: clean writing moved, um (worst writer) | "
                   "v1 words (clean) | v2 words (clean) |")
        out.append("|---|---|---|---|---|")
        for d in ("revH_akf|deltapen", "revJ_gated|deltapen", "revJ_tcn|deltapen", "revJ_g4|deltapen", "revJ_new|deltapen",
                  "revJ_info_net|deltapen", "revJ_info_ungated_akf|deltapen"):
            a = ((re_.get("v1") or {}).get("clean") or {}).get(d) or {}
            b = ((re_.get("v2") or {}).get("clean") or {}).get(d) or {}
            if not a and not b:
                continue
            fa, fb = a.get("false_correction_um") or {}, b.get("false_correction_um") or {}
            out.append(f"| {d} | {f(fa.get('mean'), 1)} ({f(a.get('false_correction_um_worst_writer'), 1)}) | "
                       f"{f(fb.get('mean'), 1)} ({f(b.get('false_correction_um_worst_writer'), 1)}) | "
                       f"{f(a.get('words_of_10'), 1)} | {f(b.get('words_of_10'), 1)} |")
        out.append("")
        for ver in ("v1", "v2"):
            for dev, d in ((re_.get(ver) or {}).get("dec055") or {}).items():
                out.append(f"- DEC-055 line, {ver}, {dev}: words gain {f(d.get('words_gain_mean'), 2)} "
                           f"({f(d.get('words_gain_lo'), 2)} to {f(d.get('words_gain_hi'), 2)}), clean writing "
                           f"{f(d.get('clean_change_um_mean'), 1)} um (worst writer {f(d.get('clean_change_um_worst_writer'), 1)}): "
                           f"{'PASSES' if d.get('passes') else 'fails'}")
        iv = re_.get("ideal_vs_deltapen") or {}
        out.append("")
        out.append("- Ideal page sensor against the DeltaPen-class one, largest card difference: " + "; ".join(
            f"{v}: {f(x.get('max_abs_words_of_10'), 2)} words, {f(x.get('max_abs_tip_tremor_mm'), 3)} mm" for v, x in iv.items()))
        pc = re_.get("page_check_v2") or {}
        out.append(f"- Version-2 window check (median / mean per 10 ms window, um): {f(pc.get('window_error_median_um_mean'), 1)} / "
                   f"{f(pc.get('window_error_mean_um_mean'), 1)} (version 1 on the same cases: median "
                   f"{f(pc.get('v1_window_error_median_um_mean'), 1)}); absolute reference valid "
                   f"{f(pc.get('reference_valid_share_mean'), 0, pct=True)} of the time; dropouts per case {f(pc.get('dropouts_mean'), 1)}")
    g = s.get("F_gap") or {}
    if g:
        out.append("")
        out.append("| Split | Configuration | Page-dependent | v1 tip tremor mm | v2 tip tremor mm | v1 words (curve) | v2 words (curve) |")
        out.append("|---|---|---|---|---|---|---|")
        for split, blk in (g.get("splits") or {}).items():
            for k, v in (blk.get("configs") or {}).items():
                if not v.get("page_dependent") and k not in ("oracle", "held", "pred_ar_imu", "page_ar_trem_ideal"):
                    continue
                out.append(f"| {split} | {k} | {'yes' if v.get('page_dependent') else 'no'} | {f(v.get('tip_tremor_mm_v1'))} | "
                           f"{f(v.get('tip_tremor_mm_v2'))} | {f(v.get('words_via_curve_v1'), 1)} | {f(v.get('words_via_curve_v2'), 1)} |")
            out.append(f"| {split} | (check) page-independent configurations, largest change | | | "
                       f"{f(blk.get('page_independent_max_abs_change_mm'), 6)} mm | | |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ ledger rows
HEADER = ("id,topic,citation,year,doi_or_url,source_type,evidence_class,access_level,task_or_setup,participants_or_bench,"
          "comparator,key_quantitative_findings,units_and_conditions,locator,limitations,relevance_to_design,transferability,"
          "transferability_reason,design_implication,retrieved,search_query,stream,lead_verification")


def evidence_rows(rows: List[Dict]) -> str:
    """CSV text with CRLF line endings and the 23-column header of docs/evidence.csv."""
    head = (REPO_ROOT / "docs" / "evidence.csv").read_bytes().split(b"\r\n", 1)[0].decode()
    cols = head.split(",")
    assert len(cols) == 23
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])
    return buf.getvalue()


def write_evidence(rows: List[Dict]) -> Path:
    p = RESULTS_DIR / "evidence_rows.csv"
    p.write_bytes(evidence_rows(rows).encode("utf-8"))
    return p


def main(argv=None) -> int:
    parts = ["# Tables for docs/rebaseline.md (generated by python3 -m rebaseline.report; SIM/CALC as labelled)\n",
             "## Impact register\n", IM.markdown_table(), "\n\n## Task 2: sim2j cards\n", sim2j_tables(_r("sim2j_cards")),
             "\n## Task 3: balanced nib\n", bnib_tables(_r("bnib_rerun")), "\n## Task 4: reach\n", reach_tables(_r("reach_b1")),
             "\n## Task 5: page model v2\n", page_tables(_r("page_v2"))]
    p = BUILD_DIR / "doc_tables.md"
    p.write_text("\n".join(parts))
    from . import evidence as EV
    write_evidence(EV.rows())
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
