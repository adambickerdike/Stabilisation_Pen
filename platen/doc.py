"""docs/platen_concept.md from platen/doc_template.md and results/platen/platen.json:

  python3 -m platen.doc            the generated tables only (platen/build/doc_tables.md)
  python3 -m platen.doc --fill     fills the template's {{...}} fields and writes docs/platen_concept.md

Fields: {{tab:<name>}} a generated table; {{t:<class>:<row>:<metric>[:ci]}} a part (a) value (class 'all/severe',
'PD/severe', ...); {{s:<variant|drive>:<metric>[:ci]}} a part (c) value; {{a:<text|config|hand>:<field>[:<digits>]}}
a part (b) value ('complete' gives k/n); {{as:<variant|hand>:<field>}} a part (b) sensitivity value;
{{fb:<grip N/m>}} the five-bar's feedforward result k/n; {{n:<key>}} a value of proposals.numbers; {{d:<dotted
path>[:<digits>]}} a design value.  So the prose quotes the results file and no number is typed by hand."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import DOC_PATH, PKG_DIR
from . import common as CM


def _ci(b: Optional[Dict], nd: int = 2, scale: float = 1.0) -> str:
    return CM.fmt_ci(b, nd, scale)


def _t(header: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


TREMOR_ROWS = ["none", "F10_oracle", "F15_oracle", "F2_oracle", "F3_oracle", "F6_oracle", "P_oracle", "P_cam_sep",
               "F10_a_r2", "F15_a_r2", "F6_a_r2", "P_a_r2", "N10_E_chosen", "N15_E_chosen", "N6_E_chosen",
               "P_E_chosen", "N10_E_net", "N15_E_net", "N6_E_net", "P_E_net"]


def tremor_table(res: Dict, tag: str) -> str:
    tab = res["tremor"]["by_class"].get(tag) or {}
    labels = res["tremor"]["labels"]
    rows = []
    for k in TREMOR_ROWS:
        e = tab.get(k)
        if not e:
            continue
        rows.append([labels.get(k, k), _ci(e.get("tip_tremor_mm")), _ci(e.get("ratio_to_ordinary")),
                     _ci(e.get("words_read"), 1) if e.get("words_read") else "not read",
                     _ci(e.get("gain_read"), 1) if e.get("gain_read") else "-",
                     _ci(e.get("words_via_curve"), 1), _ci(e.get("at_limit_share"), 3) if e.get("at_limit_share") else
                     (_ci(e.get("at_travel_limit"), 3) if e.get("at_travel_limit") else "-"), e.get("n_cases")])
    return _t(["Pen", "Tremor left at the tip, mm", "x ordinary pen (amplitude)", "Words read of 10",
               "Gain read over the ordinary pen", "Words via F's curve (CALC)", "Share of contact at the travel limit",
               "Cases"], rows)


def stage_table(res: Dict) -> str:
    tab = res["tremor"]["by_class"].get("all/severe") or {}
    rows = []
    for k in ("P_oracle", "P_cam_sep", "P_E_chosen", "P_E_net"):
        e = tab.get(k) or {}
        if not e:
            continue
        rows.append([res["tremor"]["labels"].get(k, k), _ci(e.get("travel_p99_mm")), _ci(e.get("force_rms_N")),
                     _ci(e.get("force_p99_N")), _ci(e.get("copper_W_per_axis_rms"), 3)])
    return _t(["Platen row (severe)", "Fine travel p99, mm", "Fine force RMS, N", "Fine force p99, N",
               "Copper loss per axis, W (CALC)"], rows)


def clean_table(res: Dict) -> str:
    cl = res["tremor"].get("clean") or {}
    lab = {"P_E_chosen": "Platen, E's frozen design", "P_E_net": "Platen, E's real-data TCN",
           "N6_E_chosen": "Rev J nose +-6 mm, E's frozen design", "N6_E_net": "Rev J nose +-6 mm, E's real-data TCN"}
    rows = [[lab[k], _ci(v["mean_over_writers"], 1), f"{v['worst_note_um']:.1f}", f"{v['notes_over_50um']} of {v['n_notes']}"]
            for k, v in cl.items()]
    return _t(["Design", "Clean writing moved, um (mean over writers)", "Worst note, um", "Notes over 50 um"], rows)


SENS_LABEL = {"baseline": "baseline (40 Hz, +-5 mm, camera 250 Hz / 6 ms / 15 um)"}


def sens_table(res: Dict) -> str:
    rows = res["sensitivity"].get("rows") or {}
    names = []
    for k in rows:
        n = k.split("|")[0]
        if n not in names and n != "e_command_smoothed":
            names.append(n)
    out = []
    for n in names:
        o = rows.get(f"{n}|oracle")
        c = rows.get(f"{n}|camera")
        f = rows.get(f"{n}|fixed")
        slip = (c or o or {}).get("paper_slip_max_mm")
        force = " / ".join(_ci((x or {}).get("force_rms_N"), 2).split(" (")[0] if x else "-" for x in (o, c))
        out.append([SENS_LABEL.get(n, n.replace("_", " ")), _ci((f or {}).get("tip_tremor_mm")) if f else "-",
                    _ci((o or {}).get("tip_tremor_mm")) if o else "-", _ci((o or {}).get("words_via_curve"), 1) if o else "-",
                    _ci((c or {}).get("tip_tremor_mm")) if c else "-", _ci((c or {}).get("words_via_curve"), 1) if c else "-",
                    force, _ci(slip, 3) if slip else "-"])
    return _t(["Variant", "Fixed page (own reference), mm", "Perfect knowledge: tip, mm", "words via curve",
               "Camera + predictor: tip, mm", "words via curve", "Fine force RMS, N (perfect knowledge / camera)",
               "Paper slip max, mm"], out)


def ecmd_table(res: Dict) -> str:
    """Study E's frozen design on the platen: the command as in part (a) and smoothed (part c)."""
    rows = res["sensitivity"].get("rows") or {}
    out = []
    for k, lab in (("e_command_smoothed|E_chosen_raw", "as in part (a): 500 Hz outputs extrapolated 2.7 ms"),
                   ("e_command_smoothed|E_chosen_smooth", "smoothed: 0.75 ms more prediction, 2 ms moving average")):
        e = rows.get(k)
        if not e:
            continue
        out.append([lab, _ci(e.get("tip_tremor_mm")), _ci(e.get("words_via_curve"), 1), _ci(e.get("force_rms_N")),
                    _ci(e.get("force_p99_N")), _ci(e.get("copper_W_per_axis_rms"), 2)])
    return _t(["E's frozen design on the platen", "Tip tremor, mm", "Words via F's curve (CALC)", "Fine force RMS, N",
               "Fine force p99, N", "Copper loss per axis, W (CALC)"], out)


HANDS = ["still", "drift", "mod_PD", "mod_ET", "sev_PD", "sev_ET"]
CFGS = ["proposed", "firm_ideal", "relaxed_ink_loop", "relaxed_naive"]


def accepted_table(res: Dict, text: str) -> str:
    summ = res["accepted"]["summary"]
    rows = []
    for cfg in CFGS + ["cradle"]:
        for hk in (["cradle"] if cfg == "cradle" else HANDS):
            s = summ.get(f"{text}|{cfg}|{hk}")
            if not s:
                continue
            rows.append([cfg, hk, f"{s['engineering_complete']}/{s['n']}", s["refused"], f"{s['median_coverage']:.3f}",
                         f"{s['median_rms_mm']:.3f}", f"{s['median_air_ink_mm']:.3f}",
                         f"{s['median_extra_ink_spread_mm']:.3f}", f"{s['ink_max_acc_m_s2']:.1f} / {s['ink_max_jerk_m_s3']:.0f}",
                         f"{s['ink_lp30_max_acc_m_s2']:.2f} / {s['ink_lp30_max_jerk_m_s3']:.0f}",
                         f"{s['ink_passes_both']} / {s['ink_lp30_passes_both']}",
                         f"{s['page_max_acc_m_s2']:.1f} / {s['page_max_jerk_m_s3']:.0f}",
                         f"{s['fine_travel_max_mm']:.2f}", f"{s['coarse_force_max_N']:.2f}"])
    return _t(["Configuration", "Hand", "Complete", "Refused", "Median coverage", "Median RMS, mm",
               "Median air ink, mm", "Median extra-ink spread, mm", "Ink max acc / jerk (0.5 ms), m/s2 / m/s3",
               "Ink max acc / jerk (30 Hz), m/s2 / m/s3", "Words passing 2 m/s2 and 300 m/s3 (0.5 ms / 30 Hz)",
               "Page max acc / jerk (0.5 ms)", "Fine travel max, mm", "Coarse force max, N"], rows)


def accepted_sens_table(res: Dict) -> str:
    sens = res["accepted"].get("sensitivity") or {}
    rows = []
    for k, s in sens.items():
        name, hk = k.split("|")
        rows.append([name.replace("_", " "), hk, f"{s['engineering_complete']}/{s['n']}", s["refused"],
                     f"{s['median_coverage']:.3f}", f"{s['median_rms_mm']:.3f}"])
    return _t(["Variant ('se', proposed unless stated)", "Hand", "Complete", "Refused", "Median coverage",
               "Median RMS, mm"], rows)


def fivebar_table(res: Dict) -> str:
    fb = (res.get("fivebar") or {}).get("summary") or []
    rows = [[("feedforward + feedback" if r["feedforward"] else "feedback only"), f"{r['grip_stiffness_N_m']:.0f}",
             f"{r['engineering_complete']}/{r['words']}", r["refused"], f"{r['median_ink_coverage'] * 100:.2f} %",
             f"{r['median_actual_ink_error_mm']:.4f}"] for r in fb]
    return _t(["Five-bar controller", "Grip spring, N/m", "Complete", "Refused", "Median coverage", "Median RMS, mm"], rows)


def design_tables(res: Dict) -> str:
    d = res["design"]
    out = ["**Sensing options** (delays and noise; labels in each cell)\n",
           _t(["Option", "Measures", "Delay, ms", "Noise", "For", "Against", "Label"],
              [[s["option"], s["measures"], s["delay_ms"], s["noise"], s["pros"], s["cons"], s["label"]]
               for s in d["sensing_options"]])]
    b = d["bom"]
    out.append("\n**Bill of materials, prototype quantities** (ASSUMPTION ranges; sums CALC)\n")
    out.append(_t(["Item", "Qty", "USD low", "USD high", "Note"],
                  [[i["item"], i["qty"], i["usd_low"], i["usd_high"], i["note"]] for i in b["items"]] +
                  [["**Total**", "", b["bom_usd_low"], b["bom_usd_high"], ""]]))
    p = d["power"]
    out.append("\n**Power** (CALC on ASSUMPTION ranges)\n")
    out.append(_t(["Consumer", "W low", "W high", "Label"],
                  [[i["consumer"], i["W_low"], i["W_high"], i["label"]] for i in p["items"]] +
                  [["**Total**", f"{p['total_W'][0]:.1f}", f"{p['total_W'][1]:.1f}", ""]]))
    m5 = d["masses"]["A5"]
    out.append("\n**Moving masses** (CALC; part masses ASSUMPTION except the voice coils, MANUFACTURER)\n")
    out.append(_t(["Stage", "A5, kg", "A6, kg"],
                  [["fine Y (plate, Z-drop, carriages, coil)", f"{m5['fine_y_kg']:.3f}", f"{d['masses']['A6']['fine_y_kg']:.3f}"],
                   ["fine X (+ Y stage and its coil body)", f"{m5['fine_x_kg']:.3f}", f"{d['masses']['A6']['fine_x_kg']:.3f}"],
                   ["coarse (fine stage + its stator + carriage)", f"{m5['coarse_moving_kg']:.3f}",
                    f"{d['masses']['A6']['coarse_moving_kg']:.3f}"]]))
    return "\n".join(out)


def comparison_table(res: Dict) -> str:
    c = res["comparison"]
    return _t(["User need", "Handheld nib (Rev K +-1.0 / +-1.5 mm)", "Grounded five-bar", "Moving-paper platen",
               "Typing and dictation"],
              [[r["need"], r["nib"], r["fivebar"], r["platen"], r["typing_dictation"]] for r in c["rows"]])


def tables(res: Dict, quick: bool = False) -> Path:
    parts = ["# Generated tables (platen/doc.py from results/platen/platen.json)\n",
             "## Part (a), severe class, PD and ET pooled\n", tremor_table(res, "all/severe"),
             "\n## Part (a), severe, Parkinson's\n", tremor_table(res, "PD/severe"),
             "\n## Part (a), severe, essential tremor\n", tremor_table(res, "ET/severe"),
             "\n## Part (a), moderate class\n", tremor_table(res, "all/moderate"),
             "\n## Stage effort (severe)\n", stage_table(res),
             "\n## Clean writing moved\n", clean_table(res),
             "\n## Part (c) sensitivity\n", sens_table(res),
             "\n## Part (b) 'se'\n", accepted_table(res, "se"),
             "\n## Part (b) 'library'\n", accepted_table(res, "library"),
             "\n## Part (b) sensitivity\n", accepted_sens_table(res),
             "\n## Five-bar (published)\n", fivebar_table(res),
             "\n## Design\n", design_tables(res),
             "\n## Comparison\n", comparison_table(res)]
    from . import proposals as PRP
    parts += ["\n## Proposed rows\n", PRP.markdown(res)]
    p = (CM.QUICK if quick else CM.BUILD_DIR) / "doc_tables.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(parts))
    CM.log(f"[doc] {p}")
    return p


# ------------------------------------------------------------------ the template
TEMPLATE = PKG_DIR / "doc_template.md"
NDIG = {"tip_tremor_mm": 2, "ratio_to_ordinary": 2, "words_read": 1, "words_via_curve": 1, "gain_read": 1,
        "travel_p99_mm": 2, "force_rms_N": 2, "force_p99_N": 2, "copper_W_per_axis_rms": 3, "at_limit_share": 3,
        "paper_slip_max_mm": 3, "bb_um": 0, "median_coverage": 3, "median_rms_mm": 3, "max_rms_mm": 3,
        "median_air_ink_mm": 3, "median_extra_ink_spread_mm": 2, "max_extra_ink_spread_mm": 2,
        "ink_max_acc_m_s2": 1, "ink_max_jerk_m_s3": 0, "ink_lp30_max_acc_m_s2": 2, "ink_lp30_max_jerk_m_s3": 0,
        "page_max_acc_m_s2": 1, "page_max_jerk_m_s3": 0, "page_lp30_max_acc_m_s2": 2, "page_lp30_max_jerk_m_s3": 0,
        "ink_median_peak_acc_m_s2": 2, "ink_median_peak_jerk_m_s3": 0, "fine_travel_max_mm": 2,
        "coarse_travel_max_mm": 1, "fine_force_max_N": 1, "coarse_force_max_N": 1, "ball_drag_max_N": 2}


def _b(b: Optional[Dict], nd: int, ci: bool) -> str:
    if not b or b.get("mean") is None or not np.isfinite(b.get("mean", np.nan)):
        return "n/a"
    return CM.fmt_ci(b, nd) if ci else f"{b['mean']:.{nd}f}"


def _tables() -> Dict:
    return {"tremor_severe": lambda r: tremor_table(r, "all/severe"), "tremor_pd": lambda r: tremor_table(r, "PD/severe"),
            "tremor_et": lambda r: tremor_table(r, "ET/severe"), "tremor_moderate": lambda r: tremor_table(r, "all/moderate"),
            "stage": stage_table, "clean": clean_table, "sens": sens_table, "ecmd": ecmd_table,
            "acc_se": lambda r: accepted_table(r, "se"), "acc_library": lambda r: accepted_table(r, "library"),
            "acc_sens": accepted_sens_table, "fivebar": fivebar_table, "design": design_tables,
            "comparison": comparison_table, "proposed": _proposed, "ledger": _ledger, "timings": _timings}


def _timings(res: Dict) -> str:
    full = (res.get("timings") or {}).get("stages") or {}
    quick = (CM.jload(CM.QUICK / "cache" / "timings.json") or {}).get("stages") or {}
    rows = []
    for st in ("tremor", "accepted", "sensitivity", "report"):
        f, q = full.get(st), quick.get(st)
        rows.append([st, f"{f / 60:.1f} min" if f is not None else "-", f"{q / 60:.1f} min" if q is not None else "-"])
    tf = sum(v for v in full.values() if v is not None)
    tq = sum(v for v in quick.values() if v is not None)
    rows.append(["**total**", f"{tf / 60:.1f} min" if full else "-", f"{tq / 60:.1f} min" if quick else "-"])
    return _t(["Stage", "Full run", "--quick"], rows)


def _proposed(res: Dict) -> str:
    from . import proposals as PRP
    return PRP.markdown(res)


def _ledger(res: Dict) -> str:
    from . import evidence as EV
    rows = sorted(EV.derived_rows(res) + EV.source_rows(), key=EV._key)
    return _t(["id", "Topic", "Source", "Evidence class"],
              [[r["id"], r["topic"], r["doi_or_url"], r["evidence_class"]] for r in rows])


def resolve(res: Dict, key: str) -> str:
    parts = key.strip().split(":")
    kind = parts[0]
    if kind == "fb":                                  # {{fb:<grip N/m>}}: the number is the grip, not a format
        five = {r["grip_stiffness_N_m"]: r for r in ((res.get("fivebar") or {}).get("summary") or [])
                if r.get("feedforward")}
        r = five.get(float(parts[1]))
        return f"{r['engineering_complete']}/{r['words']}" if r else "n/a"
    ci = parts[-1] == "ci"
    digits = int(parts[-1]) if parts[-1].isdigit() else None
    if ci or digits is not None:
        parts = parts[:-1]
    if kind == "tab":
        return _tables()[parts[1]](res).rstrip("\n")
    if kind == "t":
        cls, row, m = parts[1], parts[2], parts[3]
        b = (((res["tremor"]["by_class"].get(cls) or {}).get(row)) or {}).get(m)
        return _b(b, digits if digits is not None else NDIG.get(m, 2), ci)
    if kind == "s":
        b = ((res["sensitivity"].get("rows") or {}).get(parts[1]) or {}).get(parts[2])
        return _b(b, digits if digits is not None else NDIG.get(parts[2], 2), ci)
    if kind in ("a", "as"):
        src = (res["accepted"].get("summary" if kind == "a" else "sensitivity") or {}).get(parts[1])
        if not src:
            return "not run"
        f = parts[2]
        if f == "complete":
            return f"{src['engineering_complete']}/{src['n']}"
        v = src[f]
        if isinstance(v, float):
            return f"{v:.{digits if digits is not None else NDIG.get(f, 2)}f}"
        return str(v)
    if kind == "n":
        from . import proposals as PRP
        return PRP.numbers(res)[parts[1]]
    if kind == "d":
        v = res["design"]
        for k in parts[1].split("."):
            v = v[int(k)] if isinstance(v, list) else v[k]
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        if isinstance(v, float):
            return f"{v:.{digits if digits is not None else 2}f}"
        return str(v)
    if kind == "r":                                   # a plain value of the results file by dotted path
        v = res
        for k in parts[1].split("."):
            v = v[int(k)] if isinstance(v, list) else v[k]
        if isinstance(v, float):
            return f"{v:.{digits if digits is not None else 2}f}"
        return str(v)
    raise KeyError(key)


def fill(res: Dict, template: Path = TEMPLATE, out: Path = DOC_PATH) -> Path:
    text = template.read_text()
    missing: List[str] = []

    def rep(m):
        try:
            return resolve(res, m.group(1))
        except Exception as e:                        # a missing value is reported, never invented
            missing.append(f"{m.group(1)}: {e!r}")
            return f"[missing: {m.group(1)}]"
    filled = re.sub(r"\{\{([^{}]+)\}\}", rep, text)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(filled)
    CM.log(f"[doc] {out} ({len(filled.splitlines())} lines; {len(missing)} missing fields)")
    for m in missing:
        CM.log(f"[doc]   missing {m}")
    return out


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    res = CM.jload(CM.out_dir(quick) / "platen.json")
    tables(res, quick)
    if "--fill" in sys.argv:
        fill(res, out=(CM.QUICK / "platen_concept.md") if quick else DOC_PATH)
