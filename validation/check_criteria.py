#!/usr/bin/env python3
"""Check validation/acceptance_criteria.csv and refresh the criteria tables in
validation/bench_protocols.md and validation/human_study_plan.md.

The CSV is the source of truth. The tables between the markers
<!-- AC-TABLE:EXP-xxx:BEGIN --> and <!-- AC-TABLE:EXP-xxx:END --> are generated
from it, so edit the CSV and re-run:

    python3 validation/check_criteria.py            # check, then rewrite the tables
    python3 validation/check_criteria.py --check    # check only (exit 1 on any problem)
    python3 validation/check_criteria.py --selftest # test the checker's own rules

Ids: an experiment is EXP- plus one or two capital letters and two digits
(EXP-B25, EXP-BB01); its criteria are AC-<same letters and digits>-<two digits>
(AC-B25-01, AC-BB01-01).

Checks: unique ids; id prefix matches the experiment; requirement ids exist in
docs/requirements.csv; status in {requirement, derived, hypothesis}; status
'requirement' has a requirement id; direction vocabulary; the threshold does not
repeat the leading operator given in 'direction'; no empty fields; every
experiment with criteria has a table and every table has criteria; coverage of
requirements. Reads docs/ only; writes only the two markdown files above.
Every run first runs the self-test on made-up rows and stops if it fails.
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
EXP_ID = re.compile(r"EXP-([A-Z]{1,2}\d\d)")
AC_ID = re.compile(r"AC-([A-Z]{1,2}\d\d)-\d\d")
MARK = re.compile(r"(<!-- AC-TABLE:(EXP-[A-Z]{1,2}\d\d):BEGIN -->)(.*?)(<!-- AC-TABLE:\2:END -->)", re.S)


def load():
    with open(CSV, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != COLS:
            sys.exit(f"unexpected columns: {rd.fieldnames}")
        return list(rd)


def id_matches(ac_id, exp_id):
    """True when both ids are well formed and the criterion's prefix is the experiment's."""
    a, e = AC_ID.fullmatch(ac_id), EXP_ID.fullmatch(exp_id)
    return bool(a and e and a.group(1) == e.group(1))


def check(rows):
    reqs = {r["id"] for r in csv.DictReader(open(os.path.join(ROOT, "docs", "requirements.csv"),
                                                 newline="", encoding="utf-8"))}
    errs, seen = [], set()
    for r in rows:
        i = r["id"]
        if i in seen:
            errs.append(f"duplicate id {i}")
        seen.add(i)
        if not id_matches(i, r["experiment_id"]):
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


def selftest():
    """Run the checks on made-up rows. Returns a list of failures (empty when all pass)."""
    def row(i, e, **kw):
        r = dict(id=i, requirement_id="", experiment_id=e, metric="m", threshold="1", direction="<=",
                 basis="b", status="hypothesis", decision_gated="g")
        r.update(kw)
        return r

    def errs_of(*rows):
        return check(list(rows))[0]

    fails = []
    good = [("AC-B25-01", "EXP-B25"), ("AC-BB01-01", "EXP-BB01"), ("AC-NB12-03", "EXP-NB12")]
    bad = [("AC-BB01-01", "EXP-BB02"), ("AC-BB01-01", "EXP-B01"), ("AC-B01-01", "EXP-BB01"),
           ("AC-BBB01-01", "EXP-BBB01"), ("AC-bb01-01", "EXP-bb01"), ("AC-B1-01", "EXP-B1"),
           ("AC-B25-1", "EXP-B25"), ("AC-B25-01", "EXP-B25X"), ("AC-B25-01X", "EXP-B25"),
           ("AC-B251-01", "EXP-B251"), ("AC-25-01", "EXP-25")]
    for i, e in good:
        if errs_of(row(i, e)):
            fails.append(f"rejected a good pair {i} / {e}")
    for i, e in bad:
        if not any("does not match" in x for x in errs_of(row(i, e))):
            fails.append(f"accepted a bad pair {i} / {e}")
    # The other rules stay as strict as before.
    strict = {
        "duplicate id": [row("AC-BB01-01", "EXP-BB01"), row("AC-BB01-01", "EXP-BB01")],
        "not in docs/requirements.csv": [row("AC-BB01-01", "EXP-BB01", requirement_id="REQ-NONE-999")],
        "status 'x'": [row("AC-BB01-01", "EXP-BB01", status="x")],
        "needs a requirement_id": [row("AC-BB01-01", "EXP-BB01", status="requirement")],
        "direction 'about'": [row("AC-BB01-01", "EXP-BB01", direction="about")],
        "starts with an operator": [row("AC-BB01-01", "EXP-BB01", threshold="<= 1")],
        "empty basis": [row("AC-BB01-01", "EXP-BB01", basis=" ")],
    }
    for want, rows in strict.items():
        if not any(want in x for x in errs_of(*rows)):
            fails.append(f"missed '{want}'")
    for text, exp in [("<!-- AC-TABLE:EXP-B25:BEGIN -->\nx\n<!-- AC-TABLE:EXP-B25:END -->", "EXP-B25"),
                      ("<!-- AC-TABLE:EXP-BB01:BEGIN -->\nx\n<!-- AC-TABLE:EXP-BB01:END -->", "EXP-BB01"),
                      ("<!-- AC-TABLE:EXP-BBB01:BEGIN -->\nx\n<!-- AC-TABLE:EXP-BBB01:END -->", None),
                      ("<!-- AC-TABLE:EXP-BB01:BEGIN -->\nx\n<!-- AC-TABLE:EXP-BB02:END -->", None)]:
        got = [m.group(2) for m in MARK.finditer(text)]
        if got != ([exp] if exp else []):
            fails.append(f"table markers: expected {exp}, found {got}")
    return fails


def main():
    fails = selftest()
    if fails:
        print("self-test failed:\n" + "\n".join(fails))
        sys.exit(1)
    if "--selftest" in sys.argv:
        print("self-test passed")
        return
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
