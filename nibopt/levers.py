r"""Which lever matters most: one-at-a-time changes around a candidate (CALCULATION).

Each lever is applied alone to the candidate and the typical-duty copper loss (duty A, mean 35-75 deg), the severe
duty at 35 deg, the skin and the worst-case screen are re-evaluated with the brief's force-constant convention (weakest
point x the derating).  The levers are inputs the design, the firmware or a measurement can move:
  the magnet model's derating (EXP-B23 / EXP-K22 measure K_m), the face trimmed to cancel the moving mass's weight in
  contact (a schedule change), the moving mass (+-1 g), the ink force F_n (gate G1, EXP-B20), the refill's slide
  friction (REQ-BNIB-016), the guide's rolling resistance and preload, study K's face residual, the contact share, the
  copper fill, and the force-constant convention itself.
"""
from __future__ import annotations

import contextlib
from dataclasses import replace
from typing import Dict

from . import duty as DU
from . import evaluate as E
from . import magnet as M
from . import params as P
from .design import Design
from .params import V, val


@contextlib.contextmanager
def override(table: Dict, key: str, value):
    old = table[key]
    table[key] = V(value, old.unit, old.label, old.source + " [lever study override]")
    DU.contact_terms.cache_clear()
    DU.contact_B.cache_clear()
    try:
        yield
    finally:
        table[key] = old
        DU.contact_terms.cache_clear()
        DU.contact_B.cache_clear()


def _metrics(d: Design, fm=None) -> Dict:
    ev = E.evaluate(d, fine=False, full=False, fm=fm)
    return {"typical_W": ev["dutyA"]["worst07"]["mean"], "severe35_W": ev["severe"]["worst07"]["P35_W"],
            "skin_C": ev["severe"]["worst07"]["skin"]["max_shell_C"], "screen_W": ev["screen"]["worst07"]}


def study(d: Design) -> Dict:
    fm = E.force_map(d, fine=False)
    base = _metrics(d, fm)
    rows = []

    def add(name, what, m, label="CALCULATION"):
        rows.append({"lever": name, "what": what, **m,
                     "d_typical_pct": 100 * (m["typical_W"] / base["typical_W"] - 1),
                     "d_screen_pct": 100 * (m["screen_W"] / base["screen_W"] - 1), "label": label})
    for der in (0.85, 1.0):
        with override(P.KM, "derating", der):
            add(f"magnet derating {der:g}", f"K_m derated by {der:g} instead of 0.7 (EXP-K22 measures it)", _metrics(d, fm))
    add("face trimmed for the weight", "the face schedule also cancels the moving mass's weight in contact (study B's "
        "comp_weight; a firmware change, it costs float travel)", _metrics(replace(d, weight_trim=True), fm))
    for dm in (-1.0, +1.0):
        add(f"moving mass {dm:+g} g", "all else equal", _metrics(replace(d, m_move_override_g=d.m_move_g() + dm), fm))
    for f in (0.5, 1.5):
        with override(P.LOADS, "F_n_N", val(P.LOADS["F_n_N"]) * f):
            add(f"ink force x {f:g}", f"F_n {val(P.LOADS['F_n_N']):.3f} N (gate G1, EXP-B20, sets it)", _metrics(d, fm))
    with override(P.LOADS, "slide_friction_N", 0.005):
        add("refill slide friction 5 mN", "rolling guide stations under the couple (study B took 10 mN)", _metrics(d, fm))
    with override(P.MECH, "mu_roll", 0.002):
        from . import suspension as SU
        SU._guide.cache_clear()
        add("guide rolling resistance x 2", "mu_roll 0.002 (EXP-K20 measures it)", _metrics(d, fm))
    from . import suspension as SU
    SU._guide.cache_clear()
    add("guide preload 4 N", "study K's 4 N per race", _metrics(replace(d, preload_N=4.0), fm))
    kr = DU.k_residual()
    DU.k_residual.cache_clear()
    orig = DU.k_residual

    def doubled():
        r = dict(orig())
        for k in ("mean_N", "p95_N", "rms_N"):
            r[k] *= 2
        return r
    DU.k_residual = doubled
    try:
        add("face residual x 2", "study K's face-parallelism residual doubled (EXP-B22 / EXP-B28)", _metrics(d, fm))
    finally:
        DU.k_residual = orig
    with override(P.LOADS, "contact_share", 0.9):
        add("contact share 0.9", "the ball on the paper 90 % of the writing time (study B took 70 %)", _metrics(d, fm))
    for kf in (0.45, 0.65):
        if abs(kf - d.coil.k_fill) > 1e-6:
            d2 = replace(d, coil=replace(d.coil, k_fill=kf))
            add(f"copper fill {kf:g}", "etched flex (0.45) or bonded rectangular wire (0.65) (ASSUMPTION)",
                _metrics(d2, E.force_map(d2, fine=False)))
    ev = E.evaluate(d, fine=False, full=True, fm=fm)
    rows.append({"lever": "force-constant convention: centre x 1.0", "what": "study K's optimistic convention",
                 "typical_W": ev["dutyA"]["centre10"]["mean"], "severe35_W": ev["severe"]["centre10"]["P35_W"],
                 "skin_C": ev["severe"]["centre10"]["skin"]["max_shell_C"], "screen_W": ev["screen"]["centre10"],
                 "d_typical_pct": 100 * (ev["dutyA"]["centre10"]["mean"] / base["typical_W"] - 1),
                 "d_screen_pct": 100 * (ev["screen"]["centre10"] / base["screen_W"] - 1), "label": "CALCULATION"})
    ranked = sorted(rows, key=lambda r: -abs(r["d_typical_pct"]))
    return {"design": d.name, "base": base, "rows": rows, "ranked_by_typical": [r["lever"] for r in ranked],
            "items_base_W": ev["dutyA"]["worst07"]["mean_items_W"],
            "label": "CALCULATION (one-at-a-time; weakest point x derating unless stated)"}
