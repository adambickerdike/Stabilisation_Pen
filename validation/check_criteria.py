#!/usr/bin/env python3
"""Check validation/acceptance_criteria.csv and refresh the criteria tables in
validation/bench_protocols.md and validation/human_study_plan.md.

The CSV is the source of truth. The tables between the markers
<!-- AC-TABLE:EXP-xxx:BEGIN --> and <!-- AC-TABLE:EXP-xxx:END --> are generated
from it, so edit the CSV and re-run:

    python3 validation/check_criteria.py            # check, then rewrite the tables
    python3 validation/check_criteria.py --check    # check only (exit 1 on any problem)

Checks: unique ids; id prefix matches the experiment; requirement ids exist in
docs/requirements.csv; status in {requirement, derived, hypothesis}; status
'requirement' has a requirement id; direction vocabulary; the threshold does not
repeat the leading operator given in 'direction'; no empty fields; every
experiment with criteria has a table and every table has criteria; coverage of
requirements. Reads docs/ only; writes only the two markdown files above.
"""
from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(HERE, "acceptance_criteria.csv")
MDS = ("bench_protocols.md", "human_study_plan.md")
COLS = ["id", "requirement_id", "experiment_id", "metric", "threshold", "direction",
        "basis", "status", "decision_gated"]
DIRS = {"<=", ">=", "<", ">", "=", "within", "pass/fail"}
STATUS = {"hypothesis", "derived", "requirement"}
SYM = {"<=": "≤ ", ">=": "≥ ", "<": "< ", ">": "> ", "=": "= ", "within": "within ", "pass/fail": ""}
MARK = re.compile(r"(<!-- AC-TABLE:(EXP-[A-Z]\d\d):BEGIN -->)(.*?)(<!-- AC-TABLE:\2:END -->)", re.S)


def load():
    with open(CSV, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != COLS:
            sys.exit(f"unexpected columns: {rd.fieldnames}")
        return list(rd)


def check(rows):
    reqs = {r["id"] for r in csv.DictReader(open(os.path.join(ROOT, "docs", "requirements.csv"),
                                                 newline="", encoding="utf-8"))}
    errs, seen = [], set()
    for r in rows:
        i = r["id"]
        if i in seen:
            errs.append(f"duplicate id {i}")
        seen.add(i)
        if not re.fullmatch(r"AC-[A-Z]\d\d-\d\d", i) or i[3:6] != r["experiment_id"][4:7]:
            errs.append(f"{i}: id does not match experiment {r['experiment_id']}")
        if r["requirement_id"] and r["requirement_id"] not in reqs:
            errs.append(f"{i}: {r['requirement_id']} not in docs/requirements.csv")
        if r["status"] not in STATUS:
            errs.append(f"{i}: status {r['status']!r}")
        if r["status"] == "requirement" and not r["requirement_id"]:
            errs.append(f"{i}: status 'requirement' needs a requirement_id")
        if r["direction"] not in DIRS:
            errs.append(f"{i}: direction {r['direction']!r}")
        if r["direction"] != "pass/fail" and re.match(r"(<=|>=|<|>|=|≤|≥|within\b)", r["threshold"].strip()):
            errs.append(f"{i}: threshold starts with an operator; the leading operator belongs in 'direction'")
        for c in COLS:
            if c != "requirement_id" and not r[c].strip():
                errs.append(f"{i}: empty {c}")
    covered = {r["requirement_id"] for r in rows if r["requirement_id"]}
    return errs, sorted(reqs - covered)


def pretty(s: str) -> str:
    s = s.replace("+/-", "±").replace("deg C", "°C").replace("sqrt(W)", "√W").replace("R^2", "R²")
    s = re.sub(r"(\d)\s?um\b", r"\1 µm", s)
    s = re.sub(r"(\d)\s?uH\b", r"\1 µH", s)
    s = re.sub(r"(\d)\s?us\b", r"\1 µs", s)
    s = re.sub(r"(\d)\s?deg\b", r"\1°", s)
    s = s.replace("theta", "θ").replace("gamma", "γ").replace("mu_k", "μ_k").replace("|R_perp|", "|R⊥|")
    s = s.replace("<=", "≤").replace(">=", "≥")
    return s.replace("|", "\\|")


def table(exp, rows):
    sel = [r for r in rows if r["experiment_id"] == exp]
    out = ["| ID | Req. | Metric | Threshold | Status | Basis | Gates |", "|---|---|---|---|---|---|---|"]
    for r in sel:
        out.append("| " + " | ".join([r["id"], r["requirement_id"] or "—", pretty(r["metric"]),
                                       pretty(SYM[r["direction"]] + r["threshold"]).strip(), r["status"],
                                       pretty(r["basis"]), pretty(r["decision_gated"])]) + " |")
    out += ["", f"Source of truth: [`acceptance_criteria.csv`](acceptance_criteria.csv) ({len(sel)} rows for {exp})."]
    return "\n".join(out)


def main():
    rows = load()
    errs, uncovered = check(rows)
    exps = {r["experiment_id"] for r in rows}
    tabled = set()
    texts = {}
    for md in MDS:
        txt = open(os.path.join(HERE, md), encoding="utf-8").read()
        texts[md] = txt
        tabled |= {m.group(2) for m in MARK.finditer(txt)}
    errs += [f"no table for {e}" for e in sorted(exps - tabled)]
    errs += [f"table without criteria: {e}" for e in sorted(tabled - exps)]
    c = Counter(r["status"] for r in rows)
    print(f"{len(rows)} criteria, {len(exps)} experiments; status {dict(c)}; "
          f"requirements without criteria: {uncovered or 'none'}")
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    if "--check" in sys.argv:
        return
    for md, txt in texts.items():
        new = MARK.sub(lambda m: m.group(1) + "\n" + table(m.group(2), rows) + "\n" + m.group(4), txt)
        if new != txt:
            open(os.path.join(HERE, md), "w", encoding="utf-8").write(new)
            print(f"updated {md}")


if __name__ == "__main__":
    main()
