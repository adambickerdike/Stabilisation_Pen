"""Report plumbing: the add-on decision rule, the evidence-row header and the figure CSV twins (code verification only)."""
import csv
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from opt.inertial import evidence as EVD  # noqa: E402
from opt.inertial import figures as FG  # noqa: E402
from opt.inertial import report as RP  # noqa: E402


def _sa(gain_min, gain_mean, P=0.03, m=19.8, fixed=8.0):
    def g(v, vm):
        return {"mean": vm, "seed_min": v, "seed_max": vm + 0.05, "frac_conditions_worse": 0.0}
    split = {"band_8_12Hz_1_2mm": {"gain_nose+ff": g(gain_min, gain_mean), "gain_nose+ff_cal": g(gain_min, gain_mean),
                                   "gain_nose+weight": g(0.05, 0.08)},
             "all_translational": {"ff_P_cu_W_max": P}}
    return {"rm": {"label": "test", "m_g": m, "added_fixed_g": fixed}, "by_split": {str(r): split for r in (0.3, 0.5, 0.7)}}


def test_addon_decision_rule():
    assert RP.addon_decision(_sa(0.12, 0.18))["include"]
    assert not RP.addon_decision(_sa(0.05, 0.18))["include"]           # not measurable on every seed
    assert not RP.addon_decision(_sa(0.12, 0.18, m=25.0))["include"]   # 33 g > 30 g guide
    assert not RP.addon_decision(_sa(0.12, 0.18, P=0.6))["include"]    # > 0.5 W guide


def test_evidence_header_matches_ledger():
    with open(os.path.join(ROOT, "docs", "evidence.csv")) as f:
        header = next(csv.reader(f))
    assert header == EVD.HEADER
    ids = [r["id"] for r in EVD.static_rows()]
    assert len(ids) == len(set(ids))
    for i in ids:
        pre, num = i.split("-")
        n = int(num)
        assert (pre == "ACT" and 61 <= n <= 70) or (pre == "AMF" and 73 <= n <= 89) or (pre == "HAP" and 36 <= n <= 40) or \
               (pre == "OPT" and 48 <= n <= 49)


def test_figure_has_csv_twin(tmp_path, monkeypatch):
    monkeypatch.setattr(FG, "OUT", str(tmp_path))
    FG.lines_panels("fig_test", "t", {"p": {"a": ([1, 2], [0.5, 0.4]), "b": ([1, 2], [0.7, 0.6])}}, "x", "y")
    assert (tmp_path / "fig_test.png").exists()
    rows = list(csv.reader(open(tmp_path / "fig_test.csv")))
    assert rows[0] == ["panel", "series", "x", "y"] and len(rows) == 5
