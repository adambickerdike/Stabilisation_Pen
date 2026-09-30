"""Rough market-sizing model for study U (users and market).

Writes results/market/market_sizing.csv. Every input row carries a label:

* LITERATURE  - a published figure; `sources` gives the ledger id(s) in results/market/evidence_rows.csv
                (or docs/evidence.csv) and the figure is quoted as published.
* CALCULATION - arithmetic on other rows; `derivation` names the rows used.
* ASSUMPTION  - a planning value with no source; each one is a question for customer discovery.

Ranges are carried as (low, central, high) and multiplied low x low, central x central and high x high.
That gives a deliberately wide envelope, not a probability interval.

Run:  python3 results/market/sizing_model.py
Pure arithmetic; no external data are fetched.
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "market_sizing.csv")

ROWS = []
VAL = {}


def add(row_id, region, option, segment, quantity, low, central, high, unit, label, derivation, sources, note=""):
    VAL[row_id] = (low, central, high)
    ROWS.append({
        "row_id": row_id, "region": region, "product_option": option, "segment": segment,
        "quantity": quantity, "low": low, "central": central, "high": high, "unit": unit,
        "label": label, "derivation": derivation, "sources": sources, "note": note,
    })


def mul(*ids_or_triples):
    lo, ce, hi = 1.0, 1.0, 1.0
    for x in ids_or_triples:
        t = VAL[x] if isinstance(x, str) else x
        lo *= t[0]
        ce *= t[1]
        hi *= t[2]
    return lo, ce, hi


def plus(*ids):
    lo = sum(VAL[i][0] for i in ids)
    ce = sum(VAL[i][1] for i in ids)
    hi = sum(VAL[i][2] for i in ids)
    return lo, ce, hi


def calc(row_id, region, option, segment, quantity, triple, unit, derivation, sources, note=""):
    lo, ce, hi = triple
    add(row_id, region, option, segment, quantity, lo, ce, hi, unit, "CALCULATION", derivation, sources, note)


# ---------------------------------------------------------------- inputs: populations (LITERATURE)
add("IN-POP-UK-ALL", "UK", "all", "input", "Resident population, mid-2024", 69281437, 69281437, 69281437,
    "people", "LITERATURE", "ONS mid-2024 table MYE2 (UK, all ages)", "PDT-118")
add("IN-POP-UK-65", "UK", "all", "input", "Population aged 65+, mid-2024", 13161666, 13161666, 13161666,
    "people", "LITERATURE", "sum of ONS MYE2 single-year ages 65 to 90+", "PDT-118",
    "World Bank WDI gives 13,509,634 for 2024 (UN-based); ONS is used")
add("IN-POP-UK-18", "UK", "all", "input", "Population aged 18+, mid-2024", 55022253, 55022253, 55022253,
    "people", "LITERATURE", "sum of ONS MYE2 single-year ages 18 to 90+", "PDT-118")
add("IN-POP-UK-5to15", "UK", "all", "input", "Population aged 5-15 (school age), mid-2024", 9021968, 9021968,
    9021968, "people", "LITERATURE", "sum of ONS MYE2 single-year ages 5 to 15", "PDT-118")
add("IN-POP-US-65", "US", "all", "input", "Population aged 65+, 2024", 61200000, 61200000, 61200000, "people",
    "LITERATURE", "US Census Bureau Vintage 2024 press release (61.2 million)", "PDT-118")
add("IN-POP-US-K12", "US", "all", "input", "Elementary and secondary enrolment (public 49.4 M + private 6.1 M, fall 2021)",
    55500000, 55500000, 55500000, "pupils", "LITERATURE", "NCES Fast Facts id=65", "HAP-156",
    "private figure is an NCES projection")
add("IN-POP-W-65", "World", "all", "input", "Population aged 65+, 2024", 830519148, 830519148, 830519148, "people",
    "LITERATURE", "World Bank WDI SP.POP.65UP.TO (UN WPP based)", "PDT-118")
w_f, w_m = 4047858202, 4093039322
w_5to14 = (0.0818882345941536 + 0.0817740824912808) * w_f + (0.0858288881577176 + 0.0862307631963267) * w_m
add("IN-POP-W-5to14", "World", "all", "input", "Population aged 5-14, 2024", round(w_5to14), round(w_5to14),
    round(w_5to14), "people", "CALCULATION",
    "WDI 2024: female share aged 5-9 (8.189 %) + 10-14 (8.177 %) x 4,047,858,202 females; male 8.583 % + 8.623 % x 4,093,039,322 males",
    "PDT-118")

# ---------------------------------------------------------------- inputs: prevalence (LITERATURE)
add("IN-PD-UK", "UK", "all", "input", "People with Parkinson's (diagnosed; high adds the estimated undiagnosed)",
    166000, 166000, 187000, "people", "LITERATURE", "Parkinson's UK 2025: 166,000 diagnosed; 21,000 more undiagnosed",
    "PDT-92")
add("IN-PD-US", "US", "all", "input", "People with Parkinson's", 930000, 1100000, 1238000, "people", "LITERATURE",
    "low: Marras 2018 projection for 2020 (age 45+); central: Parkinson's Foundation 2024; high: Marras 2018 projection for 2030 (upper bound)",
    "PDT-93")
add("IN-PD-W", "World", "all", "input", "People with Parkinson's", 8500000, 11770000, 13420000, "people",
    "LITERATURE", "low: WHO fact sheet (2019 estimate); central and high: GBD 2021 via Luo et al. 2025 (11.77 M, UI upper 13.42 M)",
    "PDT-90; PDT-91")
add("IN-ET-P65", "all", "all", "input", "Essential tremor prevalence, age 65+ (pooled)", 0.0414, 0.0579, 0.0805,
    "fraction", "LITERATURE", "Louis & McCreary 2021 meta-analysis: 5.79 % (95 % CI 4.14-8.05 %)", "PDT-94")
add("IN-ET-PALL", "all", "all", "input", "Essential tremor prevalence, all ages (pooled)", 0.0133, 0.0133, 0.0133,
    "fraction", "LITERATURE", "Louis & McCreary 2021: 1.33 % (no CI reported in the extracted text)", "PDT-94",
    "study populations were often adults, so this may overstate an all-ages rate")
add("IN-ET-US-POP", "US", "all", "input", "People with ET (population-based estimate)", 6380000, 7010000, 7630000,
    "people", "LITERATURE", "Louis & Ottman 2014: 7.01 M (6.38-7.63 M), about 2.2 %", "PDT-95")
add("IN-ET-US-DX", "US", "all", "input", "Adults with diagnosed ET (claims-based), 2024", 1100000, 1100000, 1100000,
    "people", "LITERATURE", "Lin et al. 2025: 1.1 M; 0.42 % age-standardised", "PDT-96")
add("IN-ET-DXRATE", "all", "all", "input", "Diagnosed ET as a share of adults (US claims)", 0.0042, 0.0042, 0.0042,
    "fraction", "LITERATURE", "Lin et al. 2025", "PDT-96")
add("IN-ET-SYMPT", "all", "all", "input", "Share of community ET cases who report tremor (not asymptomatic)", 0.507,
    0.507, 0.507, "fraction", "CALCULATION", "1 - 0.493 (36 of 73 community cases asymptomatic, Louis et al. 1998)",
    "PDT-97")

# ---------------------------------------------------------------- inputs: writing affected (LITERATURE / ASSUMPTION)
add("IN-ET-WRITE-ENG", "all", "all", "input", "Share of engaged or diagnosed ET patients whose writing is affected",
    0.505, 0.65, 0.80, "fraction", "LITERATURE range; central ASSUMPTION",
    "low: QUEST writing moderate impairment 50.5 % (Gerbasi 2022 review); high: IETF member survey 80 % (Gupta 2021); central is the midpoint (ASSUMPTION)",
    "PDT-99; PDT-101", "central value is an ASSUMPTION")
calc("IN-ET-WRITE-COMM", "all", "all", "input", "Share of all (population-based) ET cases whose writing is affected",
     mul("IN-ET-SYMPT", "IN-ET-WRITE-ENG"), "fraction", "IN-ET-SYMPT x IN-ET-WRITE-ENG",
     "PDT-97; PDT-99; PDT-101",
     "ASSUMPTION that asymptomatic community cases have no writing problem and symptomatic ones resemble engaged patients")
add("IN-PD-WRITE", "all", "all", "input", "Share of people with Parkinson's whose handwriting is affected", 0.333, 0.50,
    0.632, "fraction", "LITERATURE range; central ASSUMPTION",
    "low: 'impaired dexterity or micrographia' most bothersome in early PD 33.3 % (Fox Insight 2025); high: micrographia by history 63.2 % (Wagle Shukla 2012); central midpoint (ASSUMPTION)",
    "PDT-102; PDT-01", "different definitions; central value is an ASSUMPTION")

# ---------------------------------------------------------------- inputs: behaviour and technology (ASSUMPTION unless stated)
add("IN-WEEKLY", "all", "all", "input",
    "Share of people with writing difficulty who still write by hand at least weekly", 0.40, 0.55, 0.62, "fraction",
    "ASSUMPTION", "high = general 65+ population writing short lists by hand at least weekly (62 %, YouGov May 2025); low and central ASSUMPTION",
    "HAP-158", "the key unknown for go/no-go GNG-1")
add("IN-CLASS-MS", "all", "active_pen", "input",
    "Share of tremor patients in the moderate or severe tip-tremor class", 0.40, 0.45, 0.50, "fraction",
    "CALCULATION", "project data: classes set at the median and 90th percentile of 24 PD tuning patients (50 %); 24 % + 16 % = 40 % on 25 held-out patients (docs/real_data.md)",
    "project record (study R)", "PD spirals only; ET tip data do not exist (ASSUMPTION that ET is similar)")
add("IN-NOW", "all", "active_pen", "input",
    "Share of the serviceable segment with a demonstrated legibility benefit today", 0, 0, 0, "fraction",
    "CALCULATION", "no causal tracker passes DEC-055 on real tremor (docs/claims_register.md; docs/readable_target.md)",
    "project record (studies R, E, F)")
add("IN-EARLY-HW", "all", "active_pen", "input",
    "Share of the serviceable segment buying within 3 years at the needed price", 0.02, 0.05, 0.10, "fraction",
    "ASSUMPTION", "planning value; to be replaced by EXP-U01 (GNG-5) and EXP-U05 (GNG-6)", "")
add("IN-TABLET-ADULT", "all", "tablet_app", "input",
    "Share of affected adults with a stylus-capable tablet or willing to use one", 0.30, 0.45, 0.60, "fraction",
    "ASSUMPTION", "no tablet-ownership figure for this group was found (Pew 2025 reports smartphones: 78 % of 65+)",
    "HAP-160", "GAP")
add("IN-TABLET-CHILD-HI", "UK/US", "tablet_app", "input",
    "Share of children with handwriting difficulty with tablet access at home or school", 0.50, 0.65, 0.80, "fraction",
    "ASSUMPTION", "no source found", "", "GAP")
add("IN-TABLET-CHILD-W", "World", "tablet_app", "input",
    "Share of the world's children with handwriting difficulty with tablet access and a buyer", 0.05, 0.10, 0.20,
    "fraction", "ASSUMPTION", "no source found", "", "GAP; not decision-grade")
add("IN-EARLY-APP", "all", "tablet_app", "input", "Share of serviceable users adopting within 3 years", 0.01, 0.02,
    0.05, "fraction", "ASSUMPTION", "planning value", "")
add("IN-HWD", "all", "tablet_app", "input", "Share of school-aged children with handwriting difficulties", 0.10, 0.20,
    0.30, "fraction", "LITERATURE range; central ASSUMPTION", "Feder & Majnemer 2007: 10-30 %; central midpoint (ASSUMPTION)", "HAP-152")
add("IN-DCD", "all", "therapy_tool", "input", "Share of children with developmental coordination disorder", 0.03,
    0.05, 0.07, "fraction", "LITERATURE", "Li et al. 2024 meta-analysis: 5 % (95 % CI 3-7 %); Blank et al. 2019: 5-6 % most quoted",
    "HAP-151; HAP-150")
add("IN-OT-CHILD", "all", "therapy_tool", "input", "Share of children with DCD receiving OT or school handwriting support",
    0.20, 0.30, 0.50, "fraction", "ASSUMPTION", "no source found", "", "GAP")
add("IN-OT-PD", "all", "therapy_tool", "input",
    "Share of people with PD handwriting problems referred to therapy for handwriting", 0.10, 0.20, 0.30, "fraction",
    "ASSUMPTION", "no source found", "", "GAP")
add("IN-EARLY-THER", "all", "therapy_tool", "input", "Share of the serviceable caseload reached in the first 3 years",
    0.01, 0.03, 0.05, "fraction", "ASSUMPTION", "planning value", "")
add("IN-ET-DX-W", "World", "all", "input", "Diagnosed share of population-based ET, outside the US", 0.05, 0.10, 0.157,
    "fraction", "ASSUMPTION", "high = US ratio 1.1 M / 7.01 M (CALCULATION from PDT-95, PDT-96); low and central ASSUMPTION",
    "PDT-95; PDT-96", "undiagnosed shares of 59.5-100 % are reported in some countries (PDT-94)")
add("IN-ET-DX-UK", "UK", "all", "input", "Diagnosed ET as a share of UK adults", 0.0030, 0.0042, 0.0060, "fraction",
    "ASSUMPTION", "central = US claims rate 0.42 % (PDT-96) transferred to the UK; no UK count was found", "PDT-96",
    "GAP")
add("IN-ACCESS-W", "World", "all", "input",
    "Share of the world's affected people in markets where a product like this could be sold, afforded and supported",
    0.10, 0.20, 0.30, "fraction", "ASSUMPTION", "no source; applied to every World serviceable segment except trials", "",
    "GAP; World serviceable values are not decision-grade")
add("IN-DESK", "all", "desk_surface", "input", "Share of handwriting occasions done seated at a desk or table", 0.75,
    0.83, 0.90, "fraction", "LITERATURE central; range ASSUMPTION",
    "central = 1 - 0.17 (older adults stood for 17 % of handwriting occasions, van Drempt et al. 2011, n = 30); low/high ASSUMPTION",
    "HAP-159", "small sample")
add("IN-CLINIC", "all", "measuring_pen", "input",
    "Share of PD or diagnosed-ET patients in services that would use objective writing measurement", 0.10, 0.20, 0.30,
    "fraction", "ASSUMPTION", "NICE conditionally recommends wearable PD monitors (HTG657) but none measures handwriting",
    "PDT-115", "GAP")
add("IN-TRIALS", "World", "measuring_pen", "input",
    "Open or active industry-sponsored phase 2/3 drug trials (PD 80 + ET 2), ClinicalTrials.gov 2026-09-30", 82, 82,
    82, "trials", "LITERATURE", "registry query (CALCULATION of counts)", "PDT-116")
add("IN-TRIAL-FIT", "World", "measuring_pen", "input", "Share of those trials where a writing or fine-motor endpoint is relevant",
    0.25, 0.35, 0.50, "fraction", "ASSUMPTION", "planning value", "")
add("IN-SITES", "World", "measuring_pen", "input", "Sites per trial", 20, 30, 60, "sites", "ASSUMPTION", "planning value", "")
add("IN-KITS", "World", "measuring_pen", "input", "Measuring kits per site", 1, 2, 2, "kits", "ASSUMPTION", "planning value", "")

# ---------------------------------------------------------------- ET counts
calc("ET-UK-65", "UK", "all", "input", "People with ET aged 65+ (population-based)", mul("IN-POP-UK-65", "IN-ET-P65"),
     "people", "IN-POP-UK-65 x IN-ET-P65", "PDT-118; PDT-94", "ASSUMPTION that the pooled rate applies to the UK")
et_uk_all = 69281437 * 0.0133
add("ET-UK-POP", "UK", "all", "input", "People with ET, all ages (population-based)", VAL["ET-UK-65"][0], et_uk_all,
    VAL["ET-UK-65"][2] + (et_uk_all - VAL["ET-UK-65"][1]), "people", "CALCULATION",
    "low = 65+ only at the lower CI; central = 1.33 % x all ages; high = 65+ upper CI + (central - 65+ central)",
    "PDT-118; PDT-94", "ASSUMPTION that pooled rates apply to the UK")
calc("ET-UK-DX", "UK", "all", "input", "Adults with diagnosed ET", mul("IN-POP-UK-18", "IN-ET-DX-UK"), "people",
     "IN-POP-UK-18 x IN-ET-DX-UK", "PDT-118; PDT-96", "rests on an ASSUMPTION (GAP)")
calc("ET-W-65", "World", "all", "input", "People with ET aged 65+ (population-based)", mul("IN-POP-W-65", "IN-ET-P65"),
     "people", "IN-POP-W-65 x IN-ET-P65", "PDT-118; PDT-94",
     "excludes under-65s; all-ages 1.33 % x 8.14 bn would give 108 M but overstates in young populations")
calc("ET-W-DX", "World", "all", "input", "People with diagnosed ET (65+ only)", mul("ET-W-65", "IN-ET-DX-W"), "people",
     "ET-W-65 x IN-ET-DX-W", "PDT-94; PDT-95; PDT-96", "ASSUMPTION-heavy")

# ---------------------------------------------------------------- writing-affected adults (TOTAL for pen-type options)
for reg, et_pop, pd in (("UK", "ET-UK-POP", "IN-PD-UK"), ("US", "IN-ET-US-POP", "IN-PD-US"), ("World", "ET-W-65", "IN-PD-W")):
    calc(f"WA-{reg}-ET", reg, "all", "input", "People with ET whose writing is affected (population-based)",
         mul(et_pop, "IN-ET-WRITE-COMM"), "people", f"{et_pop} x IN-ET-WRITE-COMM", "see inputs")
    calc(f"WA-{reg}-PD", reg, "all", "input", "People with PD whose handwriting is affected", mul(pd, "IN-PD-WRITE"),
         "people", f"{pd} x IN-PD-WRITE", "see inputs")
    calc(f"WA-{reg}", reg, "all", "input", "Adults with ET or PD whose writing is affected", plus(f"WA-{reg}-ET", f"WA-{reg}-PD"),
         "people", f"WA-{reg}-ET + WA-{reg}-PD", "see inputs", "ignores the small overlap of ET and PD")

# diagnosed / engaged base (reachable through care or charities)
for reg, et_dx, pd in (("UK", "ET-UK-DX", "IN-PD-UK"), ("US", "IN-ET-US-DX", "IN-PD-US"), ("World", "ET-W-DX", "IN-PD-W")):
    calc(f"DX-{reg}-ET", reg, "all", "input", "Diagnosed ET with writing affected", mul(et_dx, "IN-ET-WRITE-ENG"), "people",
         f"{et_dx} x IN-ET-WRITE-ENG", "see inputs")
    calc(f"DX-{reg}", reg, "all", "input", "Diagnosed ET or PD with writing affected", plus(f"DX-{reg}-ET", f"WA-{reg}-PD"),
         "people", f"DX-{reg}-ET + WA-{reg}-PD", "see inputs")

# ---------------------------------------------------------------- option 1: active pen
for reg in ("UK", "US", "World"):
    add(f"AP-{reg}-TOTAL", reg, "active_pen", "total", "Adults with ET or PD whose writing is affected", *VAL[f"WA-{reg}"],
        "people", "CALCULATION", f"= WA-{reg}", "see inputs")
    acc = ("IN-ACCESS-W",) if reg == "World" else ()
    calc(f"AP-{reg}-SERV-COND", reg, "active_pen", "serviceable",
         "Diagnosed, still writing by hand weekly, tremor class moderate or severe (IF a tracker passes DEC-055)",
         mul(f"DX-{reg}", "IN-WEEKLY", "IN-CLASS-MS", *acc), "people",
         f"DX-{reg} x IN-WEEKLY x IN-CLASS-MS" + (" x IN-ACCESS-W" if acc else ""), "see inputs",
         "conditional on a technical result that does not exist yet")
    calc(f"AP-{reg}-SERV-NOW", reg, "active_pen", "serviceable",
         "Same segment with a demonstrated legibility benefit today", mul(f"AP-{reg}-SERV-COND", "IN-NOW"), "people",
         f"AP-{reg}-SERV-COND x IN-NOW", "project record", "zero until DEC-055 passes on real inputs")
    calc(f"AP-{reg}-EARLY", reg, "active_pen", "early_adopter",
         "Buyers in the first 3 years (IF the conditional serviceable segment materialises)",
         mul(f"AP-{reg}-SERV-COND", "IN-EARLY-HW"), "people", f"AP-{reg}-SERV-COND x IN-EARLY-HW", "see inputs")

# ---------------------------------------------------------------- option 2: measuring pen (clinics and trials)
for reg, pd, et_dx in (("UK", "IN-PD-UK", "ET-UK-DX"), ("US", "IN-PD-US", "IN-ET-US-DX"), ("World", "IN-PD-W", "ET-W-DX")):
    calc(f"MP-{reg}-TOTAL", reg, "measuring_pen", "total", "Patients who could have writing measured (PD + diagnosed ET)",
         plus(pd, et_dx), "patients", f"{pd} + {et_dx}", "see inputs")
    acc = ("IN-ACCESS-W",) if reg == "World" else ()
    calc(f"MP-{reg}-SERV", reg, "measuring_pen", "serviceable", "Patients in services that would measure writing objectively",
         mul(f"MP-{reg}-TOTAL", "IN-CLINIC", *acc), "patients",
         f"MP-{reg}-TOTAL x IN-CLINIC" + (" x IN-ACCESS-W" if acc else ""), "see inputs")
calc("MP-World-TRIAL-SERV", "World", "measuring_pen", "serviceable", "Industry phase 2/3 trials with a relevant endpoint",
     mul("IN-TRIALS", "IN-TRIAL-FIT"), "trials", "IN-TRIALS x IN-TRIAL-FIT", "PDT-116")
calc("MP-World-TRIAL-KITS", "World", "measuring_pen", "serviceable", "Measuring kits those trials would need",
     mul("MP-World-TRIAL-SERV", "IN-SITES", "IN-KITS"), "kits", "MP-World-TRIAL-SERV x IN-SITES x IN-KITS", "PDT-116")
add("MP-UK-EARLY", "UK", "measuring_pen", "early_adopter", "Research groups or services running a paid or co-funded pilot",
    2, 4, 8, "organisations", "ASSUMPTION", "planning value; tested by EXP-U03 and GNG-7/GNG-8", "")
add("MP-US-EARLY", "US", "measuring_pen", "early_adopter", "Research groups or services running a paid or co-funded pilot",
    3, 6, 12, "organisations", "ASSUMPTION", "planning value", "")
add("MP-World-EARLY", "World", "measuring_pen", "early_adopter", "Trial sponsors or CROs running a pilot", 1, 2, 3,
    "sponsors", "ASSUMPTION", "planning value; GNG-8", "")

# ---------------------------------------------------------------- option 3: tablet app with stylus
for reg, kids, tab in (("UK", "IN-POP-UK-5to15", "IN-TABLET-CHILD-HI"), ("US", "IN-POP-US-K12", "IN-TABLET-CHILD-HI"),
                       ("World", "IN-POP-W-5to14", "IN-TABLET-CHILD-W")):
    calc(f"TA-{reg}-KIDS-TOTAL", reg, "tablet_app", "total", "School-aged children with handwriting difficulties",
         mul(kids, "IN-HWD"), "children", f"{kids} x IN-HWD", "HAP-152")
    add(f"TA-{reg}-ADULT-TOTAL", reg, "tablet_app", "total", "Adults with ET or PD whose writing is affected",
        *VAL[f"WA-{reg}"], "people", "CALCULATION", f"= WA-{reg}", "see inputs")
    calc(f"TA-{reg}-KIDS-SERV", reg, "tablet_app", "serviceable", "Children with DCD who have tablet access",
         mul(kids, "IN-DCD", tab), "children", f"{kids} x IN-DCD x {tab}", "HAP-151")
    acc = ("IN-ACCESS-W",) if reg == "World" else ()
    calc(f"TA-{reg}-ADULT-SERV", reg, "tablet_app", "serviceable", "Diagnosed adults with writing affected and a tablet",
         mul(f"DX-{reg}", "IN-TABLET-ADULT", *acc), "people",
         f"DX-{reg} x IN-TABLET-ADULT" + (" x IN-ACCESS-W" if acc else ""), "see inputs")
    calc(f"TA-{reg}-EARLY", reg, "tablet_app", "early_adopter", "Users in the first 3 years (children + adults)",
         tuple(a * b for a, b in zip(plus(f"TA-{reg}-KIDS-SERV", f"TA-{reg}-ADULT-SERV"), VAL["IN-EARLY-APP"])),
         "users", f"(TA-{reg}-KIDS-SERV + TA-{reg}-ADULT-SERV) x IN-EARLY-APP", "see inputs")

# ---------------------------------------------------------------- option 4: handwriting-therapy tool (clinician-led)
for reg, kids, pd in (("UK", "IN-POP-UK-5to15", "IN-PD-UK"), ("US", "IN-POP-US-K12", "IN-PD-US"),
                      ("World", "IN-POP-W-5to14", "IN-PD-W")):
    calc(f"TT-{reg}-KIDS-TOTAL", reg, "therapy_tool", "total", "Children with DCD", mul(kids, "IN-DCD"), "children",
         f"{kids} x IN-DCD", "HAP-151")
    add(f"TT-{reg}-PD-TOTAL", reg, "therapy_tool", "total", "People with PD whose handwriting is affected",
        *VAL[f"WA-{reg}-PD"], "people", "CALCULATION", f"= WA-{reg}-PD", "see inputs")
    acc = ("IN-ACCESS-W",) if reg == "World" else ()
    calc(f"TT-{reg}-SERV", reg, "therapy_tool", "serviceable", "Caseload in therapy (children with DCD in OT + PD referred)",
         tuple(a + b for a, b in zip(mul(f"TT-{reg}-KIDS-TOTAL", "IN-OT-CHILD", *acc), mul(f"TT-{reg}-PD-TOTAL", "IN-OT-PD", *acc))),
         "people", f"(TT-{reg}-KIDS-TOTAL x IN-OT-CHILD + TT-{reg}-PD-TOTAL x IN-OT-PD)" + (" x IN-ACCESS-W" if acc else ""),
         "see inputs", "not decision-grade" if reg == "World" else "")
    calc(f"TT-{reg}-EARLY", reg, "therapy_tool", "early_adopter", "Patients reached through early-adopting services",
         mul(f"TT-{reg}-SERV", "IN-EARLY-THER"), "people", f"TT-{reg}-SERV x IN-EARLY-THER", "see inputs")

# ---------------------------------------------------------------- option 5: desk writing surface
for reg in ("UK", "US", "World"):
    add(f"DS-{reg}-TOTAL", reg, "desk_surface", "total", "Adults with ET or PD whose writing is affected", *VAL[f"WA-{reg}"],
        "people", "CALCULATION", f"= WA-{reg}", "see inputs")
    acc = ("IN-ACCESS-W",) if reg == "World" else ()
    calc(f"DS-{reg}-SERV", reg, "desk_surface", "serviceable",
         "Diagnosed, still writing weekly; scaled by the share of writing done at a desk",
         mul(f"DX-{reg}", "IN-WEEKLY", "IN-DESK", *acc), "people",
         f"DX-{reg} x IN-WEEKLY x IN-DESK" + (" x IN-ACCESS-W" if acc else ""), "see inputs",
         "no tremor-class filter: the surface is not limited by the nib's reach (ASSUMPTION; another study evaluates it)")
    calc(f"DS-{reg}-EARLY", reg, "desk_surface", "early_adopter", "Buyers in the first 3 years",
         mul(f"DS-{reg}-SERV", "IN-EARLY-HW"), "people", f"DS-{reg}-SERV x IN-EARLY-HW", "see inputs")


def fmt(x):
    if isinstance(x, float) and x < 1:
        return f"{x:.4g}"
    return f"{round(x):d}" if isinstance(x, (int, float)) else x


with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()), lineterminator="\r\n")
    w.writeheader()
    for r in ROWS:
        r = dict(r)
        for k in ("low", "central", "high"):
            r[k] = fmt(r[k])
        w.writerow(r)

if __name__ == "__main__":
    print(f"wrote {len(ROWS)} rows to {OUT}")
    for r in ROWS:
        if r["segment"] != "input":
            print(f"{r['row_id']:24s} {r['region']:6s} {r['segment']:14s} {fmt(r['low']):>12s} {fmt(r['central']):>12s} {fmt(r['high']):>12s} {r['unit']}")
