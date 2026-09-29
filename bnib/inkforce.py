r"""The minimum reliable ink force: what the sources opened in this study say, and what gate G1 must measure.

The nib is designed for a refill spring of 0.15 N along the pen (REQ-RVJ-N05 proposed, ASSUMPTION).  Every writing load
this study found in a standard or a manufacturer's test is higher, and none of them is a MINIMUM: they are test loads
chosen to make a line reliably on a machine.  No source opened here states the lowest normal force at which a
ballpoint, gel, rollerball or fineliner line stays continuous.  That number is therefore a measurement (gate G1,
EXP-B20), not a literature value, and the design must not depend on it: the counter-face balance scales with the actual
force (balance.CounterFace), so a G1 result of 0.7 N instead of 0.15 N changes the nib's residual power, not its
architecture (sensitivity below, CALC).

Sources (opened; ledger ids from docs/evidence.csv or this study's proposed rows in results/bnib/evidence_rows.csv):
"""
from __future__ import annotations

import math
from typing import Dict, List

from .labels import V

GF = 9.80665e-3          # N per gram-force

SOURCES: List[Dict] = [
    {"id": "CON-21", "tip": "ballpoint (oil)", "what": "ISO 12757-1:1998 machine write test", "load_N": 1.5, "tol_N": 0.1,
     "angle_deg": 75.0, "speed": "4.5 m/min", "kind": "standard test load (not a minimum)", "access": "full text (preview)",
     "note": "point load 1.5 +- 0.1 N, writing angle 75 +- 5 deg"},
    {"id": "AMF-60", "tip": "gel", "what": "ISO 27668-1:2017 (preview): write test machine definition (ISO 12756 3.1.7)",
     "load_N": (0.1, 5.0), "angle_deg": (60.0, 90.0), "speed": "1-10 m/min",
     "kind": "machine adjustment range (not a test load, not a minimum)", "access": "preview pages",
     "note": "'point load: vertical component of force applied to a writing tip during line generation' (clause 3.7.3.7): "
             "the ISO loads are NORMAL forces"},
    {"id": "CON-95", "tip": "rollerball", "what": "ISO 14145-1:2017 (preview): tip classes, refill types A-D",
     "load_N": None, "kind": "no load in the preview pages (the test clause is outside the preview)",
     "access": "preview pages", "note": "tip classes EF < 0.55, F 0.55-0.75, M 0.75-1.00, B >= 1.00 mm"},
    {"id": "CON-96", "tip": "gel / water-based (Pentel)", "what": "US 11,697,743 B2 spiral machine writing test",
     "load_N": 100 * GF, "angle_deg": 70.0, "speed": "7 cm/s", "kind": "manufacturer test load (not a minimum)",
     "access": "full text", "note": "'spiral machine written test (writing speed: 7 cm/sec, writing angle: 70 deg, writing load: "
                                   "100 gf)'"},
    {"id": "CON-97", "tip": "oil ballpoint, 0.5 mm ball (Pilot)", "what": "US 11,993,099 B2 start-of-writing and running tests",
     "load_N": 70 * GF, "angle_deg": 70.0, "speed": "4 m/min", "kind": "manufacturer test load (the lowest found; not a minimum)",
     "access": "full text", "note": "start-of-writing test at 70 gf, 70 deg, 4 m/min; running tests at 100 gf; ink consumption "
                                   "at 200 g; the ball's own spring presses 5-10 gf (the ball seal, not the writing load)"},
    {"id": "CON-23", "tip": "oil ballpoint 0.7 mm (Pentel)", "what": "US 8,771,410 B2 writing-resistance tests",
     "load_N": 150 * GF, "angle_deg": (70.0, 90.0), "kind": "manufacturer test load", "access": "full text",
     "note": "ledger row CON-23"},
    {"id": "CON-98", "tip": "plotter pens (fibre-tip, drafting, roller-ball)", "what": "HP 7550A/B plotter specification: "
     "carousel force defaults", "load_N": None, "kind": "relative force levels (paper fibre-tip 2, drafting 1, roller-ball 6; "
     "the level-to-gram table was not in the opened documents)", "access": "full text (spec sheet)",
     "note": "machine pens are driven with a set force; a roller-ball pen is given the highest level"},
    {"id": "CON-99", "tip": "ballpoint / rollerball", "what": "Lee, Murad, Nikolov 2023 Colloids Interfaces 7:29",
     "load_N": None, "kind": "mechanism (ink film, ball rotation, wetting); the ball's downward pressure named as a factor "
     "of writing quality; no force threshold", "access": "full text", "note": ""},
    {"id": "CON-01", "tip": "any (human)", "what": "healthy adults' axial pen force while writing", "load_N": (0.56, 2.08),
     "kind": "human writing force (context: what hands apply, far above the refill spring)", "access": "ledger",
     "note": "mean 1.01 N"},
]

MIN_FORCE = {
    "ballpoint_oil": V(None, "N", "UNKNOWN", "no minimum found; lowest manufacturer test load 0.69 N normal at 70 deg (CON-97)"),
    "gel": V(None, "N", "UNKNOWN", "no minimum found; manufacturer test load 0.98 N at 70 deg (CON-96); ISO machines 0.1-5 N (AMF-60)"),
    "rollerball": V(None, "N", "UNKNOWN", "no minimum found; ISO 14145-1 preview gives no load (CON-95)"),
    "fineliner_capillary": V(None, "N", "UNKNOWN", "no source opened in this study; capillary tips need no ball rotation"),
    "design_value": V(0.15, "N", "ASSUMPTION", "REQ-RVJ-N05 proposed (along the pen); 0.196 N normal at 50 deg"),
}


def g1_protocol() -> Dict:
    """Gate G1 (EXP-B20): the minimum reliable ink force per tip type (PROPOSED protocol; equipment in study M's rig)."""
    return {
        "id": "EXP-B20", "gate": "G1",
        "question": "the lowest normal force at which each tip type writes a continuous line on six papers, across the "
                    "writing angles 35-75 deg and speeds 5-60 mm/s",
        "tips": ["D1 oil ballpoint 0.7 mm (the design refill)", "D1 low-viscosity oil ballpoint", "gel 0.5 mm",
                 "rollerball 0.5 mm", "fineliner / capillary 0.4 mm"],
        "rig": "a dead-weight or voice-coil force-controlled carriage (study M's rig) holding the refill at the set angle, "
               "on a motorised XY table; load cell under the paper (0.5 mN resolution); force steps 0.05-1.5 N",
        "papers": "six: 80 g/m2 copy, 90 g/m2 smooth, recycled, school exercise paper, ISO 12757 test paper, a notebook on "
                  "a soft underlay",
        "measure": "line continuity (skip length and gap count from a 1200 dpi scan), ink laydown (optical density), "
                   "friction coefficient (tangential / normal: the friction map, EXP-B21), start-of-writing after 30 s",
        "decision": "minimum reliable force = the lowest force with gap share < 1 % over the 5-60 mm/s x 35-75 deg grid "
                    "for >= 95 % of refills (n >= 10 refills per type); it sets F_s in config/nib.yaml",
        "why_it_does_not_block_the_nib": "the counter-face scales with the actual force: the design point moves along the "
                                         "sensitivity curve (below), not off it",
    }


def sensitivity(forces=(0.05, 0.10, 0.15, 0.30, 0.50, 0.69, 1.00)) -> Dict:
    """Mean continuous power of the default candidates vs the refill force (CALC): the counter-face nib and the same nib
    without balance, 24 mm pen, duty A, mean over 35/50/60/75 deg."""
    from . import candidates as CD
    out = {}
    for key in ("c_counterface", "f_translation"):
        rows = []
        for F in forces:
            d = CD.make(key, CD.pen24())
            d.F_s = F
            if hasattr(d.balance, "F_s_nom"):
                d.balance.F_s_nom = F
            r = CD.evaluate(d, detail=False, fast=True)
            rows.append({"F_s_N": F, "P_cont_W": r["P_cont_W"], "P_35deg_W": r["P_mean_W_by_theta"][35.0],
                         "travel_under_load_mm": r["travel_under_load_mm"]})
        out[key] = rows
    out["label"] = "CALC (candidates.evaluate, Km upper bound, duty A)"
    return out


def summary() -> Dict:
    return {"sources": SOURCES, "minimum_force": {k: v.d() for k, v in MIN_FORCE.items()}, "g1": g1_protocol(),
            "finding": "No source opened states a minimum ink force for any tip type. The lowest manufacturer test load "
                       "found is 70 gf (0.69 N) at 70 deg (Pilot, US 11,993,099 B2); ISO 12757-1 tests ballpoints at 1.5 N "
                       "(normal) at 75 deg; ISO 27668-1 write-test machines cover 0.1-5 N. The design's 0.15 N spring is "
                       "4.6x below the lowest test load found: it is unverified until gate G1 (EXP-B20)."}
