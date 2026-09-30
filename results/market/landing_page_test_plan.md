# Waitlist and landing-page test plan (EXP-U05)

**Question.** When people with tremor or Parkinson's, parents, and clinicians see an honest description of each product idea, how many ask to be kept informed, and does an expected price change that? This is a behavioural check on the stated interest in the survey (EXP-U01), because stated purchase intent overstates real buying (ASSUMPTION).

**What it is not.** It is not a sale, a pre-order or a claim of benefit. Nothing is available and nothing has been shown to help anyone.

---

## 1. Rules the pages must follow

| Rule | Source |
|---|---|
| No claim that any idea reduces tremor, improves writing or treats a condition. Objective claims need evidence, and medical claims are allowed only for a device with the applicable conformity marking | CAP Code 12.1, 12.6 (PDT-119) |
| Every page carries the status box: "In development. Not available. Not yet shown to help anyone. We are asking who would want it." | project rule; DEC-094 (proposed) |
| No money, deposit or card details from patients or families | DEC-094 (proposed) |
| The page is transparent about who runs it and why; no activity "under the guise of research" that aims to mislead | MRS Code 2023 rule 4 (PDT-119) |
| Email only for the waitlist, double opt-in, a privacy notice, and a stated retention period | UK GDPR (ASSUMPTION: 12-month retention; set by the data protection officer) |
| Charity channels only with the charity's written permission | charity policies (PDT-119) |

## 2. Concepts and audiences

| Page | Idea | Audience | Main button |
|---|---|---|---|
| A | A pen that steadies itself (active pen) | adults with ET or PD, families | Join the waitlist |
| B | A tablet app with a stylus: practice, larger and clearer writing on screen, progress tracking | adults with ET or PD; parents of children with handwriting difficulty | Join the waitlist |
| C | A therapist-led practice kit | occupational therapists, PD nurses, school OTs | Register interest as a clinician |
| D | A measuring pen for clinics and trials | neurologists, trial sponsors, contract research organisations, academic groups | Request a briefing |
| E | A desk writing surface (only if the other study reaches a design) | adults with ET or PD | Join the waitlist |

Each page has the same layout: a plain headline; one paragraph on what it is; who it is for; the status box; "What we do not know yet" (effectiveness, price, size, availability date); the button; and an optional three-question micro-survey ("What would you use it for?", "What do you use now?", "Would you like to take part in research?").

## 3. Price arms (pages A, B and E only)

Visitors are allocated at random by visit to one of three arms:

| Arm | Wording shown |
|---|---|
| 1 | "Expected price: about 250-350 (estimate; may change)" |
| 2 | "Expected price: about 500-700 (estimate; may change)" |
| 3 | no price shown |

GBP for UK visitors and USD for US visitors (by the visitor's choice of country, not by tracking). For page B the price is per year. Arm 1 sits below the price that the Rev K cost estimate implies; arm 2 sits at the low end of that implied price (CALCULATION in `docs/market_and_users.md` §6.1).

## 4. Channels

1. Charity newsletters and social posts (Parkinson's UK, National Tremor Foundation, International Essential Tremor Foundation, PD and dyspraxia charities) with written permission.
2. Moderated online communities, with the moderator's permission.
3. Paid search and social adverts with neutral wording. Check each platform's health-advertising policy before launch (not reviewed here).
4. Clinician and trial channels for pages C and D: professional newsletters, conference contacts.

Tag each link with its channel so conversion can be reported per channel.

## 5. Sample size and duration

- At least **400 unique visitors per concept per arm** (CALCULATION: at a 10 % conversion, the 95 % interval is about ±3 percentage points; at 3 %, about ±1.7).
- Run 4–6 weeks, or until the targets are met.
- Pages C and D are judged on counts of qualified contacts, not rates (see GNG-7 and GNG-8).

## 6. Measures

| Measure | Definition |
|---|---|
| Unique visitors | after bot filtering |
| Sign-up rate | confirmed (double opt-in) sign-ups ÷ unique visitors |
| Micro-survey completion | completions ÷ sign-ups |
| Price effect | sign-up rate difference between arms, with a 95 % interval |
| Qualified clinician or sponsor contacts | contacts who state a role and a use case (pages C and D) |
| Complaints | any complaint that the page misleads |

## 7. Decision thresholds (fixed in advance; see `go_no_go_criteria.csv`)

- **GNG-6 go:** confirmed sign-ups ≥ 10 % of unique visitors for a consumer page (any arm), with at least 400 visitors in that arm.
- **GNG-6 no-go:** below 3 % in every arm of a page.
- Between 3 % and 10 %: grey zone. Revise the concept wording once and rerun; do not commit build funds on a grey result.
- **Price:** if arm 2 converts at less than half of arm 3, treat the Rev K price band as a barrier (feeds DEC-091 and REQ-MKT-003).

## 8. Analysis and reporting

- Wilson 95 % intervals for each rate; arm differences with 95 % intervals. All pages and all arms are reported, including failures.
- Results are read together with the survey (GNG-1 to GNG-5) and the interviews.
- A short decision memo goes to the lead with the numbers and the go, grey or no-go call for each concept.

## 9. Stop and review rules

- Any complaint that a page misleads: take the page down within 48 hours and review the wording.
- If a charity partner objects to any wording: pause that channel.
- Waitlist members are told the outcome, and are removed on request or at the end of the retention period.
