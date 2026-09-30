# Users and market: is there a market, and what should the project do first? (study U)

*Study U, 30 September 2026. Desk research, a sizing model, a competitor table, a customer-discovery pack and a study design. Nothing was built, no one was interviewed and no prices were quoted by suppliers. Every source was opened on 30 September 2026 and is logged as a ledger row (PDT-90…PDT-119 and HAP-150…HAP-166) in [`results/market/evidence_rows.csv`](../results/market/evidence_rows.csv). Every number carries a label (§1).*

## The answer in plain words

**Do people still use pens?** Yes, most people do, including older people.
- In a May 2025 poll of 2,095 adults in Great Britain, 62 % of those aged 65 or over wrote a shopping or to-do list by hand at least a few times a week, and 92 % wrote in a card at least a few times a year (LITERATURE, HAP-158; the sums are a CALCULATION).
- Some documents must still be signed by hand. In England and Wales a lasting power of attorney must be signed on the original document ("They cannot sign copies or use digital signatures"), a will must be signed (or the signature acknowledged) in front of two witnesses, and a postal-vote application needs a photo of a handwritten signature (LITERATURE, PDT-105).
- In the US, 40.7 % of the 584,463 mail ballots rejected in the 2024 general election were rejected for a non-matching or incomplete signature (LITERATURE, PDT-106).
- Exams in England are handwritten by default, and the exam regulator proposes to keep every subject with more than 100,000 entries on paper for now (LITERATURE, HAP-153, HAP-154).

**Isn't typing or voice easier?** Often, yes, and every product must be tested against them.
- For people with clear speech, dictation is about three times faster than a phone keyboard: 153 against 52 words per minute in a laboratory (LITERATURE, HAP-161).
- But tremor affects keyboards too. Among 2,864 members of a tremor charity, 80 % said tremor affected their writing and 54 % said it affected typing or using a mouse (LITERATURE, PDT-99).
- In a classic study of 200 people with Parkinson's, about 9 in 10 had voice problems (LITERATURE, PDT-103; the share is a CALCULATION). A speech recogniser that got 3.4 % of words wrong for typical speakers got 36.3 % wrong for people with Parkinson's (LITERATURE, PDT-104).

**How many people?**
- About 166,000 people in the UK have diagnosed Parkinson's (LITERATURE, PDT-92). Roughly 0.5–1.2 million have essential tremor (CALCULATION from PDT-94 and PDT-118), but in the community half of them do not notice it and most are never treated (LITERATURE, PDT-97).
- Our model puts the number of adults with either condition whose writing is affected at about 390,000 in the UK (195,000–613,000), 2.9 million in the US and 22 million worldwide (CALCULATION, [`market_sizing.csv`](../results/market/market_sizing.csv)).
- About 1 child in 20 has developmental coordination disorder, and 10–30 % of school children have handwriting difficulties (LITERATURE, HAP-151, HAP-152).

**The catch.**
- Cheap alternatives exist. Weighted pens cost about $8 each (CALCULATION from PDT-107), and the SteadyScrib pen and clipboard costs $125 (LITERATURE, PDT-107).
- In spoon studies people rated a simple weighted spoon as highly as an active stabilising spoon, and in essential tremor they preferred it (LITERATURE, ACT-18, ACT-19).
- The active pen would cost $226–501 to make at 1,000 units plus tooling (project estimate, [`revK_design.md`](revK_design.md) §5.4, ASSUMPTION ranges). It would therefore sell for roughly $500–2,000 (CALCULATION, §6.1). That is between a $999 anti-tremor glove and a $5,899 gyroscopic glove (LITERATURE, PDT-108, PDT-109).
- The project's own simulations put the pen's legibility benefit in severe tremor, where no tracker works yet and the nib's reach is too short (project SIM, [`readable_target.md`](readable_target.md)). Today, the number of people for whom the active pen has shown a benefit is zero.
- **So the active pen's market rests on a technical result that does not exist yet, and on beating a weighted pen, typing and dictation at tasks people care about.**

**What to do first.**
1. **Ask before building.** Run the discovery pack now: a survey of at least 200 people with tremor or Parkinson's through charities, about 50 interviews with people, clinicians, parents and teachers, and an honest waitlist page. The answers that mean "go" or "stop" are written down in advance (§7.2).
2. **Measure the alternatives now.** A pilot with no new device (ordinary pen, weighted pen, typing with accessibility settings, dictation) can start once ethics approval is in place (EXP-U06). It shows what people can already do and sizes the later study.
3. **Sell measurement and practice before assistance.** The instrumented, non-actuated pen that the tremor census (EXP-H01) already needs could become a measuring pen for clinics and drug trials, and a tablet app could deliver practice and measurement. Both are cheaper, closer to evidence, and have buyers. 80 industry-sponsored Parkinson's drug trials in phase 2 or 3 are open or active (LITERATURE, PDT-116). NICE conditionally recommends Parkinson's monitoring wearables and lists prices such as £64 per patient-month and £225 per use (LITERATURE, PDT-115).
4. **Keep the active pen as the long-term flagship behind hard gates.** It needs a tracker that passes DEC-055 on real tremor, then a comparison (EXP-U07) in which it beats a weighted pen, typing and dictation on paper-bound tasks.

---

## 1. Scope, method and labels

**Questions.** This study asked:
- whether people still write by hand, and where a handwritten signature is still needed;
- how many people have essential tremor (ET), Parkinson's (PD) or a childhood writing difficulty, and how many of them have trouble writing;
- what they can use instead, what that costs and how well it works;
- which product options could make money, who would pay, and in which order to pursue them;
- how to test all of this with people.

**Labels.** Every number in this document carries one of these labels.

| Label | Meaning |
|---|---|
| LITERATURE, with a ledger id | A figure quoted as published. The ledger row gives the source, the retrieval date, the search query and the limits |
| CALCULATION | Arithmetic on labelled numbers. The sizing model's arithmetic is in [`sizing_model.py`](../results/market/sizing_model.py) |
| ASSUMPTION | A planning value with no source. Each one is a question for customer discovery |
| project SIM / CALC / ASSUMPTION | A number from this repository's own studies, with its original label and document. None is a measurement on people |

Numbers that define a proposed protocol (task lengths, session lengths, group sizes) are design choices. Where a number is a threshold or a planning value, it is labelled ASSUMPTION.

**Method.** Web searches and database queries on 30 September 2026:
- Europe PMC, Crossref and PMC full texts;
- GOV.UK and legislation.gov.uk pages; the eCFR API; the ClinicalTrials.gov API; the World Bank API; the ONS mid-2024 spreadsheet;
- manufacturers' product data.

Primary or official sources were preferred. The ledger's `access_level` column marks abstracts, summaries and secondary accounts. Pages that could not be opened are recorded as such: for example the Ofcom report and the NCSL table returned HTTP 403, and the Liftware and NeuroMotor Pen sites were unavailable. No statistic was taken from a source that was not opened. Gaps are listed in §10.

**Not done here.** No interviews or surveys; no supplier quotations; no regulatory opinion (a regulatory adviser is needed); no edits to shared project files. Proposed rows for the lead are in §12.

## 2. Do people still write by hand?

### 2.1 Everyday writing in Great Britain

YouGov asked 2,095 adults in Great Britain, 11–12 May 2025, "How often, if ever, do you write the following by hand?" (LITERATURE, HAP-158).

| Task | All adults, at least a few times a week | Aged 65+, at least a few times a week | All adults, at least a few times a year | Aged 65+, at least a few times a year | Aged 65+, never |
|---|---|---|---|---|---|
| Short lists (shopping, to-do) | 52 % | 62 % | 84 % | 91 % | 6 % |
| Notes | 48 % | 44 % | 82 % | 82 % | 9 % |
| Forms | 8 % | 3 % | 70 % | 70 % | 8 % |
| Birthday or greetings cards | 3 % | 4 % | 90 % | 92 % | 4 % |
| Letters | 2 % | 1 % | 28 % | 36 % | 33 % |

The cumulative columns are sums of the rounded published categories (CALCULATION, about ±1 point of rounding). The "never" column is published (LITERATURE, HAP-158). Also published: 80 % of people aged 65+ write joined-up, against 46 % of 18–24-year-olds, and 42 % of all adults say their handwriting is not neat (LITERATURE, HAP-158).

### 2.2 What older adults write, how much and how fast

- Thirty healthy adults aged 65+ (mean 75.1 years) wrote a median of 18 words per occasion over three days of digital-pen recording. 85 % of their writing was self-generated text, and they stood for 17 % of writing occasions. The commonest reasons were note taking (23 %) and puzzles (22 %) (LITERATURE, HAP-159).
- Normal handwriting speed falls with age: about 113 letters per minute at 60–69 and 61–67 letters per minute at 90–99 on the Handwriting Speed Test (LITERATURE, HAP-159).
- **Meaning.** The frequent job is short, self-generated text (a list, a note, a crossword), often away from a desk. Speed matters less than getting a few words down readably.

### 2.3 School

- **England.** The national curriculum requires pupils to be taught to "write legibly, fluently and with increasing speed" (LITERATURE, HAP-155). A school's exam policy, quoting the exam boards' rules, states that candidates handwrite unless an exception applies; a word processor may be allowed for, among others, poor handwriting or a physical disability (LITERATURE, HAP-153).
- In 2024/25, 23,625–38,815 students had an approved scribe or speech-recognition arrangement for GCSE, AS or A-level exams (1.7–2.7 % of students assessed), and 18.0–27.7 % had at least one access arrangement (LITERATURE, HAP-153). Word-processor use is not counted in these figures.
- The regulator's December 2025 proposal would not permit on-screen exams for subjects with more than 100,000 entries "at this stage" (LITERATURE, HAP-154).
- **California.** Since 2023, handwriting instruction in grades 1–6 must include "cursive or joined italics" (LITERATURE, HAP-155).
- **Meaning.** School handwriting is a durable, regulated demand. Typing and scribes are the established alternatives that any children's product sits beside.

### 2.4 Where a handwritten signature is still needed

**UK** (LITERATURE, PDT-105)
- **Wills.** A will must be in writing and signed by the testator "or by some other person in his presence and by his direction", before two witnesses present at the same time. Video witnessing was allowed only for wills made between 31 January 2020 and 31 January 2024. The Law Commission recommended on 16 May 2025 that electronic wills be made valid under safeguards; this is not yet law.
- **Lasting powers of attorney.** "Everyone must sign the same original document. They cannot sign copies or use digital signatures."
- **Postal votes.** Applicants upload "a photo of your handwritten signature in black ink on plain white paper". "If you cannot provide a signature or one that always looks the same, you may be able to apply for a postal vote signature waiver."

**US** (LITERATURE, PDT-106)
- **Wills.** The federal electronic-signature law does not apply to laws governing "the creation and execution of wills, codicils, or testamentary trusts", nor to family law and court documents.
- **Mail ballots.** In the 2024 general election, 47,957,093 mail ballots were returned and 584,463 rejected (1.2 %). A non-matching or incomplete signature caused 40.7 % of rejections, a missing voter signature 10 %, and a missing witness signature 5.6 %. That is about 237,900 ballots rejected for signature mismatch (CALCULATION). The report does not say how many were due to tremor or other motor problems (GAP).
- By a search summary of the NCSL table (the page itself returned 403), 32 states check signatures on returned mail ballots (LITERATURE, PDT-106, secondary account).
- Check payments continue to fall in number and value (LITERATURE, PDT-106).

**Meaning.** Signatures are rare but high-stakes, and the system already tests whether a signature "looks the same". Accommodations exist: signing by direction, and waivers. So the need is about independence and dignity as much as legality. How often people with tremor meet these tasks, and how they solve them, is unmeasured (GAP, GNG-2).

### 2.5 Summary: two kinds of handwriting job

| Job | Frequency | Can typing or voice replace it? | Evidence |
|---|---|---|---|
| Short self-generated text: lists, notes, puzzles | weekly for most older adults | often yes (a phone note), but many choose paper | HAP-158, HAP-159 |
| Paper-bound, high-stakes: signatures, paper forms, cards, legal documents | a few times a year | usually no, or only through a waiver or a helper | PDT-105, PDT-106, HAP-158 |

The second job is where a writing aid has no digital substitute. The first is where it competes with a phone.

## 3. Why typing and voice are not universally easy

### 3.1 Tremor affects keyboards and touchscreens

- **Charity survey.** Among 2,864 respondents from the International Essential Tremor Foundation (IETF) database, tremor affected writing (80 %), drinking (68 %), eating (67 %), carrying (67 %), using tools (54 %) and typing or a computer mouse (54 %) (LITERATURE, PDT-99).
- **Small clinic sample.** In 20 people with ET, all reported difficulty "writing a letter, postcard, thank you card, or cheque", 50 % reported difficulty typing on a mobile phone and 45 % using a computer mouse (LITERATURE, PDT-100).
- **Reading these together.** Typing is affected in about half of people with ET, less often than writing. For many people typing will be the better tool, and the product must accept that.

### 3.2 Accessibility settings exist, but their benefit is unmeasured

iPads and iPhones offer Touch Accommodations "if you have difficulties with hand tremors, dexterity, or fine motor control": Hold Duration, Ignore Repeat and Tap Assistance (LITERATURE, HAP-162). No study measuring their effect on typing in tremor was found (GAP). The comparison studies must configure these settings rather than use defaults, and must time the setup.

### 3.3 Voice

- **Voice problems in PD.** In 200 people with Parkinson's, every group in the classification had laryngeal (voice) dysfunction, together 90 % of the sample (LITERATURE, PDT-103; the sum is a CALCULATION). Voice was the leading and earliest deficit in another sample of 200, and it worsens over time (LITERATURE, PDT-103).
- **Speech recognition.** A recogniser with 3.4 % word errors on typical speakers made 36.3 % word errors on the Parkinson's test speech of the Speech Accessibility Project. Fine-tuning on Parkinson's speech reduced this to 23.7 % (LITERATURE, PDT-104).
- **Specialist speech apps.** A subscription app for non-standard speech costs $49.99 a month and says it works best for mild to moderate impairment (LITERATURE, HAP-163). A free research app is not accepting new users (LITERATURE, HAP-163).
- **Clear speech.** For people with clear speech, dictation is far faster than any handwriting: 153 words per minute against 52 on a phone keyboard in a laboratory (LITERATURE, HAP-161), and about 61–113 letters per minute is normal handwriting at older ages (LITERATURE, HAP-159).

### 3.4 Digital access

- **US.** 78 % of Americans aged 65+ own a smartphone and 70 % have home broadband (all adults: 91 % and 78 %) (LITERATURE, HAP-160).
- **UK.** 6 % of adults have no home internet, and two-thirds of them are 75+ (LITERATURE, HAP-160, a secondary account of an Ofcom report).
- Most target users therefore own a phone they could type or dictate on. Tablet ownership in this group was not found (GAP).

### 3.5 What follows

The engineering review's position stands: typing, accessible typing settings and dictation are comparators, and the product is "an option for people who value writing or drawing on paper and have difficulty controlling it" ([engineering report §7](reviews/Stabilisation_Pen_Engineering_Improvement_Report.md)). The evidence adds two things:
- tremor also degrades typing, and Parkinson's often degrades voice, so the alternatives are not free for everyone;
- the one job no digital alternative serves is the paper-bound one, which is rarer.

A pen should not compete on text speed (REQ-MKT-005, proposed).

## 4. How many people?

### 4.1 Parkinson's

| Place | Count | Source |
|---|---|---|
| World | over 8.5 million in 2019 | LITERATURE, PDT-90 (WHO) |
| World | 11.77 million in 2021 (95 % UI 10.44–13.42 million) | LITERATURE, PDT-91 (GBD 2021) |
| US | about 1.1 million (2024 estimate); about 90,000 new diagnoses a year | LITERATURE, PDT-93 |
| UK | about 166,000 diagnosed; about 21,000 more undiagnosed | LITERATURE, PDT-92 |

**Age.**
- In the UK the average age at diagnosis is 69, the average age of people living with Parkinson's is 77, and over 1 in 3 were of working age (under 67) at diagnosis (LITERATURE, PDT-92).
- Worldwide, rates are highest at 85–89 (LITERATURE, PDT-91). Men are affected about 1.5 times as often as women (LITERATURE, PDT-91, PDT-93).

### 4.2 Essential tremor

**Prevalence.**
- Pooled over 42 population studies: 1.33 % at all ages and 5.79 % at age 65+ (95 % CI 4.14–8.05 %). Prevalence rises by 74 % per decade of age, with no difference between sexes (LITERATURE, PDT-94).
- **UK.** 0.76 million aged 65+ (0.54–1.06 million) and 0.92 million at all ages (CALCULATION: pooled rates × ONS mid-2024 population, PDT-118).
- **US.** A population-based estimate of 7.0 million (6.4–7.6 million) (LITERATURE, PDT-95), against 1.1 million adults with a diagnosis in insurance claims (0.42 %) (LITERATURE, PDT-96). So only about one in six appears as diagnosed (15.7 %, CALCULATION; the two estimates differ in year and method).
- **World.** 48 million aged 65+ (34–67 million) (CALCULATION from PDT-94 and PDT-118).

**Most community cases are mild.** In a community sample, 49.3 % of people with ET said they did not have tremor they could not control, and 91.8 % had never been prescribed tremor medication (LITERATURE, PDT-97). Even so, 73 % of community cases reported some disability on a questionnaire (LITERATURE, PDT-98).

**No UK count of diagnosed ET was found (GAP).** The model transfers the US diagnosed rate as an ASSUMPTION: 231,000 (165,000–330,000).

### 4.3 How many have trouble writing

**Essential tremor**

| Group | Share with writing affected | Source |
|---|---|---|
| Charity members (IETF survey) | 80 % | LITERATURE, PDT-99 |
| Quality-of-life studies (QUEST) | 30.1–34.8 % with high impairment in writing; 50.5 % with moderate impairment | LITERATURE, PDT-101 |
| Community cases | about 26–41 % | CALCULATION: 50.7 % symptomatic (PDT-97) × 50.5–80 % |

**Parkinson's**

| Group | Share | Source |
|---|---|---|
| Small handwriting (micrographia) by history, 68 men | 63.2 % | LITERATURE, PDT-01 |
| Micrographia across studies | 9–60 % | LITERATURE, PDT-03 |
| "Impaired dexterity or micrographia" named as most bothersome, 8,536 people within about a year of diagnosis | 33.3 % | LITERATURE, PDT-102 |
| Tremor as the most frequent bothersome motor symptom (same survey) | 55.9 % | LITERATURE, PDT-102 |

Tremor while writing is less common in PD than tremor at rest (LITERATURE, PDT-08, PDT-10). PD writing problems are mainly size, speed and fluency, not tremor (project decision DEC-002).

**Rating-scale writing items.**
- A US Medicare coverage policy admits people with ET to a tremor-stimulator benefit when they score 3 or more on the Bain-Findley ADL item for eating, drinking, self-care or writing, and continues cover after a 1-point improvement (LITERATURE, PDT-113).
- No published distribution of the TETRAS or Bain-Findley writing item in a population or clinic sample was found (GAP). The survey's item S7 is a stand-in until EXP-U07 records the real items.

### 4.4 Children

- **Developmental coordination disorder (DCD).** 5 % of children (95 % CI 3–7 %), 7 % of boys and 4 % of girls, and 2 % in European studies (LITERATURE, HAP-151). Published estimates range from 2 % to 20 %, 5–6 % is most often quoted, and at least 2 % face severe consequences in daily life (LITERATURE, HAP-150). About half of children with DCD have difficulty learning to write (LITERATURE, HAP-49).
- **Handwriting difficulties.** 10–30 % of school-aged children, and they do not resolve without intervention (LITERATURE, HAP-152).
- **Denominators.**
  - UK: 9.02 million aged 5–15 (LITERATURE, PDT-118).
  - US: 55.5 million in elementary and secondary school (LITERATURE, HAP-156), of whom 7.5 million (15 %) receive special-education services (LITERATURE, HAP-156).
  - World: 1.37 billion aged 5–14 (CALCULATION, PDT-118).

### 4.5 The sizing model

[`market_sizing.csv`](../results/market/market_sizing.csv) has 120 rows. Each input row is labelled LITERATURE, CALCULATION or ASSUMPTION, and each derived row names the rows it uses. [`sizing_model.py`](../results/market/sizing_model.py) regenerates the file.

**Definitions.**
- **Total**: everyone with the condition and the problem.
- **Serviceable**: those the option could reach and serve: diagnosed or in care, still writing, able to use the product.
- **Early adopters**: those who would plausibly start within three years (ASSUMPTION rates, to be replaced by discovery results).

Central value (low–high); all values are CALCULATION on the labelled inputs:

| Option | Segment | UK | US | World |
|---|---|---|---|---|
| Active pen | Total: adults with ET or PD whose writing is affected | 387 k (195 k–613 k) | 2.86 M (1.94 M–3.88 M) | 21.7 M (11.6 M–35.6 M) |
| Active pen | Serviceable IF a tracker passes DEC-055 (diagnosed, writing weekly, moderate or severe tip tremor) | 58 k (22 k–119 k) | 313 k (138 k–515 k) | 446 k (59 k–1.57 M) |
| Active pen | **Serviceable with a demonstrated benefit today** | **0** | **0** | **0** |
| Active pen | Early adopters over 3 years (IF) | 2.9 k (444–12 k) | 16 k (2.8 k–52 k) | 22 k (1.2 k–157 k) |
| Measuring pen | Total: patients with PD or diagnosed ET | 397 k (331 k–517 k) | 2.20 M (2.03 M–2.34 M) | 16.6 M (10.2 M–23.9 M) |
| Measuring pen | Serviceable: patients in services that would measure writing | 79 k (33 k–155 k) | 440 k (203 k–701 k) | 663 k (102 k–2.15 M) |
| Measuring pen | Serviceable: industry phase 2/3 trials with a relevant endpoint / kits they need | – | – | 29 trials (20–41) / 1.7 k kits (410–4.9 k) |
| Measuring pen | Early adopters: organisations running a pilot (world: trial sponsors) | 4 (2–8) | 6 (3–12) | 2 (1–3) |
| Tablet app | Total: children with handwriting difficulty | 1.80 M (902 k–2.71 M) | 11.1 M (5.55 M–16.6 M) | 273 M (137 M–410 M) |
| Tablet app | Total: adults with writing affected | 387 k (195 k–613 k) | 2.86 M (1.94 M–3.88 M) | 21.7 M (11.6 M–35.6 M) |
| Tablet app | Serviceable: children with DCD and a tablet | 293 k (135 k–505 k) | 1.80 M (832 k–3.11 M) | 6.83 M (2.05 M–19.1 M) |
| Tablet app | Serviceable: diagnosed adults with a tablet | 105 k (42 k–229 k) | 569 k (260 k–997 k) | 811 k (111 k–3.04 M) |
| Tablet app | Early adopters over 3 years | 8.0 k (1.8 k–37 k) | 47 k (11 k–205 k) | 153 k (22 k–1.11 M) |
| Therapy tool | Total: children with DCD | 451 k (271 k–632 k) | 2.77 M (1.67 M–3.88 M) | 68.3 M (41.0 M–95.7 M) |
| Therapy tool | Total: people with PD whose handwriting is affected | 83 k (55 k–118 k) | 550 k (310 k–782 k) | 5.88 M (2.83 M–8.48 M) |
| Therapy tool | Serviceable: caseload in therapy | 152 k (60 k–351 k) | 942 k (364 k–2.18 M) | 4.34 M (848 k–15.1 M) |
| Therapy tool | Early adopters over 3 years | 4.6 k (597–18 k) | 28 k (3.6 k–109 k) | 130 k (8.5 k–756 k) |
| Desk surface | Total: adults with writing affected | 387 k (195 k–613 k) | 2.86 M (1.94 M–3.88 M) | 21.7 M (11.6 M–35.6 M) |
| Desk surface | Serviceable: diagnosed, writing weekly, share of writing done at a desk | 106 k (42 k–213 k) | 577 k (260 k–928 k) | 823 k (111 k–2.83 M) |
| Desk surface | Early adopters over 3 years | 5.3 k (832–21 k) | 29 k (5.2 k–93 k) | 41 k (2.2 k–283 k) |

**How to read it.**
- Ranges multiply low by low and high by high. They are wide envelopes, not probability intervals.
- The same people appear under several options. Do not add across rows.
- World serviceable values include an ASSUMPTION about which markets can buy and be supported (10–30 %). They are not decision-grade.

**Which inputs matter most.** The serviceable and early-adopter rows move most with four inputs, three of them ASSUMPTIONS:
1. the share of affected people who still write by hand weekly (40–62 %; ASSUMPTION, upper bound from HAP-158);
2. the share of diagnosed ET patients whose writing is affected (50.5–80 %; LITERATURE range, PDT-99, PDT-101);
3. the share in the moderate or severe tip-tremor class (40–50 %; project CALC on data, [`real_data.md`](real_data.md));
4. the adoption rates (1–10 %; ASSUMPTION).

Discovery measures the first and the last (GNG-1, GNG-5, GNG-6).

### 4.6 What the project's own results do to the active pen's market

The active pen helps only if two things hold: the tremor makes writing hard to read, and the pen can remove enough of it. The project's simulations with real recorded tremor (project SIM, HW1 with real inputs, an automatic reader standing in for people) show where those overlap.

| Tip-tremor class (project data) | Share of PD spiral patients | Words read of 10: ordinary pen | Words read with perfect tremor knowledge | Best causal tracker today |
|---|---|---|---|---|
| Mild, 0.03–0.16 mm | below the median; 60 % of 25 held-out patients | 6.8 (same as no tremor) | – | no gain needed |
| Moderate, 0.16–0.51 mm | median to 90th percentile; 24 % of held-out | 5.7 | 6.9 | 5.5 (Rev J tracker) |
| Severe, above 0.51 mm (typically 1.7 mm) | top 10 %; 16 % of held-out | 0.5 | 7.0 | 0.5 |

Sources: [`claims_register.md`](claims_register.md), [`real_data.md`](real_data.md), [`readable_target.md`](readable_target.md).

**The paradox.**
- Where people are within the nib's reach, the benefit is small. At the moderate class, perfect knowledge adds about 1.2 words of 10 (project SIM; the difference 6.9 − 5.7 is a CALCULATION), and the correction claim is limited to tremor within ±0.5 mm (REQ-USR-002).
- Where the benefit is large, at the severe class, today's trackers leave about twice the tremor the target allows (1.12 mm against 0.55 mm; project SIM, DEC-067). And even perfect knowledge with Rev K's ±1 mm nib gains only 1.4 words (project SIM, [`readable_target.md`](readable_target.md) §8).
- People whose tremor stops them using a tablet are missing from these data, so the severe share is a floor (project record).

Hence the model's "serviceable with a demonstrated benefit today = 0", and the conditional row that assumes a future tracker passes DEC-055. Parkinson's writing is mainly a size, speed and fluency problem (DEC-002), which a ±1 mm nib cannot fix. For PD the relevant options are cueing and practice (the therapy tool and the tablet app), not correction.

## 5. Competitors and alternatives

The full table is [`competitors.csv`](../results/market/competitors.csv): 23 rows with price, price date, regulatory status, evidence, weaknesses and ledger ids. Summary:

| Alternative | Price | Evidence of benefit | Main weakness |
|---|---|---|---|
| Weighted pens | $24.99 for 3 (LITERATURE, PDT-107) | PD pilot: more variable letters (PDT-21); no ET writing trial (PDT-111); weighted spoons matched or beat active ones in preference (ACT-18, ACT-19) | Fatigue; may hurt PD fluency |
| Large-grip pen | £8.50 (LITERATURE, PDT-107) | none found | Grip only |
| SteadyScrib pen and magnetic clipboard | $125 (LITERATURE, PDT-107) | none controlled (PDT-26) | Clipboard-bound; mass |
| Lined paper, cues, practice (PD) | low (not sourced) | size gains in small trials (PDT-16, PDT-20, PDT-33) | Needs practice; costs fluency (PDT-17) |
| Steadi-3 Plus damping glove | $999 per hand (LITERATURE, PDT-108) | manufacturer: 84 % vs no device, 70 % vs placebo glove; no peer-reviewed trial found (PDT-108, PDT-111) | Bulk; unverified evidence |
| GyroGlove | $5,899 per hand (LITERATURE, PDT-109) | manufacturer pilot abstract: writing task −48 % vs no device (ACT-25) | Price; not MHRA-registered |
| Liftware Steady (spoon) | $195 (2021) (LITERATURE, PDT-110) | 15-person pilot, 71–76 % tremor reduction; severe tremor could not use it (ACT-16) | Eating only; availability uncertain |
| Cala TAPS wrist stimulator | not found | 263-person open-label study: 68 % of moderate or severe improved to mild or slight on the Bain-Findley ADL scale; 18 % device-related adverse events (PDT-112); Medicare cover (PDT-113) | Prescription; benefit wears off |
| Smart pens | $80–120 (LITERATURE, HAP-163) | capture only (HAP-50) | Do not steady writing |
| Tablet and stylus | from $449 + $79 (LITERATURE, HAP-162) | measures dysgraphia well (HAP-157); no tremor-writing benefit found | Not paper |
| Typing with touch accessibility settings | free with a device (HAP-162) | none found for these settings (GAP) | Tremor affects typing too (PDT-99, PDT-100) |
| Dictation | free with a device (HAP-162) | 153 vs 52 WPM for clear speakers (HAP-161) | 36.3 % word errors on PD speech (PDT-104) |
| NHS-assessed PD wearables | £64 per patient-month (KinesiaU) to £225 per use (PKG); others £224–350 a month or £1,600 a year (LITERATURE, PDT-115) | conditionally recommended by NICE | Do not measure writing |
| NeuroMotor Pen (clinical digital pen) | not found | unverified (HAP-166) | Status unknown |

**What the table says.**
1. **Evidence is thin across the whole category.** A 2024 review found no published trial data for weighted utensils, the Steadi-Two glove, Readi-Steadi or Tremelo, and no reported results for GyroGlove's controlled trial (LITERATURE, PDT-111). Controlled, comparator-based evidence of task benefit would itself be a differentiator.
2. **The price ladder runs from about $8 to $5,899.** An active pen at $500–2,000 would sit in the glove band, where sellers offer 30-day returns (LITERATURE, PDT-108, PDT-109).
3. **The only device with a large study also has payer coverage.** Cala's route runs through prescription, a writing ADL item and US Medicare (PDT-112, PDT-113). That route needs a device that is primarily medical.
4. **Digital alternatives are free to anyone who owns a phone,** and 78 % of Americans aged 65+ do (LITERATURE, HAP-160).

## 6. Business-model options

### 6.1 Rough unit economics

| Option | Unit cost | Price anchors | Implied price or revenue | Label |
|---|---|---|---|---|
| **Active pen (Rev K)** | $226–501 per pen at 1,000 units, plus $28–70 per pen of tooling over 1,000 units ($254–571 in all); $812–1,929 at 100 units | gloves $999 and $5,899; SteadyScrib $125; weighted pen about $8 (PDT-107–109) | $508–1,142 at a 50 % gross margin (direct sale); $907–2,039 retail at a 60 % margin plus a 30 % channel margin | costs: project estimate, [`revK_design.md`](revK_design.md) §5.4 (ASSUMPTION ranges); margins: ASSUMPTION; prices: CALCULATION |
| **Measuring pen** (instrumented, no actuator) | about $106–216 at 1,000 units: Rev K minus its three piezo motors and drivers ($75–180), counter-face head ($30–70) and titanium carrier ($15–35) | NICE: KinesiaU £64 per patient-month; PKG £225 per use; STAT-ON £1,600 a year (PDT-115) | per-use or per-patient-month service near £64–225; per-kit-month plus data services in trials | CALCULATION on project ASSUMPTION ranges; anchors LITERATURE |
| **Tablet app with stylus** | software; hosting and support small (ASSUMPTION); the user needs a tablet from $449 plus a $79 stylus ($528, CALCULATION, HAP-162) | speech app $49.99 a month (HAP-163); KinesiaU £64 a month (PDT-115) | consumer subscription of a few dollars to tens of dollars a month; school or clinic licences | ASSUMPTION, to be tested in EXP-U01, U04, U05 |
| **Therapy tool** (app + passive pen + clinician protocol) | as the app, plus pens at the measuring-pen cost if instrumented | therapist time; no price found (GAP) | per-clinician or per-service licence | ASSUMPTION, to be tested in EXP-U03 |
| **Desk writing surface** | not estimated here (another study) | SteadyScrib clipboard set $125 (PDT-107) | unknown | GAP |

**What the numbers mean.**
- The active pen's cost puts it 60–250 times the price of a weighted pen (CALCULATION: $508–2,039 against about $8).
- The Rev K cost is quoted for a batch of 1,000 units. The model's UK early-adopter estimate is about 2,900 buyers over three years, and only IF a tracker passes (CALCULATION, §4.5): the first batch would take about a year to sell in the UK alone, so the US market matters from the start.
- The measuring pen and the app make most of their money from service and software, so hardware cost matters less.

### 6.2 Who pays

| Payer | Active pen | Measuring pen | Tablet app | Therapy tool | Desk surface |
|---|---|---|---|---|---|
| Individual or family | Main route | – | Yes (subscription) | Some | Main route |
| UK VAT relief | Possible if designed solely for disabled users and sold to an eligible person (PDT-117) | – | Unclear for general software (PDT-117) | – | Possible (PDT-117) |
| Employer (UK Access to Work: "specialist equipment and assistive software") | For working-age users (a third of people with PD are under 67 at diagnosis, PDT-92) | – | Yes | – | Yes |
| NHS or insurer | Unlikely without trial evidence. US Medicare durable equipment must be "primarily and customarily used to serve a medical purpose" and not useful without illness, which a pen is unlikely to meet (PDT-117) | Plausible: NICE sets a precedent for paying for PD monitoring by use or subscription (PDT-115) | Only with therapy evidence and claims | NHS therapy services (price not found, GAP) | Unlikely |
| Schools | – | – | School special-needs budgets (not sourced, GAP) | School OT services | – |
| Pharma and CROs | – | Trial endpoints: 80 industry PD phase 2/3 drug trials and 2 ET trials open or active (PDT-116) | – | – | – |

### 6.3 Regulatory class (planning view; a regulatory adviser must confirm)

| Option | US | EU (MDR) | Notes |
|---|---|---|---|
| Active pen | Class I "daily activity assist device", 510(k)-exempt (21 CFR 890.5050). A 510(k) may still be needed because an actuated nib "operates using a different fundamental scientific technology" (890.9(b)) | Class I under Rule 13 ("all other active devices") if it has no diagnostic or monitoring claim | LITERATURE, PDT-114. The UK (GB) route under UK MDR 2002 was not reviewed (GAP) |
| Measuring pen, used for clinical decisions | Class II "tremor transducer" (21 CFR 882.1950), 510(k) | Class IIa (Rule 11: software informing diagnosis or therapy, or monitoring physiological processes) | LITERATURE, PDT-114. Must stay separate from the consumer pen, which keeps REQ-USR-003 (no diagnostic output) |
| Measuring pen, used only as a trial endpoint | Investigational use; FDA's December 2023 guidance covers digital tools that acquire data in trials of medical products | Clinical-investigation rules | Route to confirm (GAP; PDT-116) |
| Tablet app, no medical claims | Not a device | Not a device | Practice, notes and larger on-screen writing |
| Tablet app or therapy tool, with therapy or measurement claims | Software as a medical device; class depends on claims | Rule 11: class IIa if it informs therapy or diagnosis decisions; otherwise class I | LITERATURE, PDT-114 |
| Desk surface | Class I (890.5050) | Class I (Rule 1 if non-active; Rule 13 if active) | LITERATURE, PDT-114 |

**Advertising.** In the UK, medical claims are allowed only for a device with the applicable conformity marking, and objective claims need evidence, "if relevant consisting of trials conducted on people" (CAP Code 12.1, LITERATURE, PDT-119).

### 6.4 Routes to market

| Option | Route | First customers |
|---|---|---|
| Measuring pen | Research-use kits for academic movement-disorder groups, then trial sponsors and contract research organisations, then NHS services under a per-use or subscription model | PD research groups; trial sponsors (GNG-8) |
| Tablet app | App stores; through occupational therapists, PD nurses and school OTs; charity shops and guides (Parkinson's UK runs a shop and a Tech Guide, PDT-107, PDT-109) | Clinicians who prescribe practice; parents |
| Therapy tool | Clinician-led: NHS and private OT or physiotherapy services; schools | OT services (GNG-7) |
| Desk surface | Direct and charity channels; employer-funded (Access to Work) | Working-age users with desk jobs |
| Active pen | Direct with a trial period and returns; charity channels; employer funding in the UK; VAT relief if eligible; later clinician recommendation | Only after GNG-10 (DEC-055) and EXP-U07 |

### 6.5 Recommended order, with reasons

1. **Customer discovery and the no-device pilot (EXP-U01 to U06), now.** They cost little, need no hardware, and decide whether any paper-based option is worth building. They also fix the comparison study's size.
2. **Measuring pen as a research tool, then for clinics and trials.** It reuses the passive instrumented pen of EXP-H01/R01. It has identified buyers (PDT-115, PDT-116). It needs measurement reliability rather than a new physical capability. It generates the writing data every other option needs. Risks: a separate regulatory route (Class II / IIa) and an existing but unverified competitor (HAP-166).
3. **Tablet app with stylus**, for measurement, practice and larger, clearer writing on screen. Low unit cost and fast iteration. Tablets measure handwriting well (HAP-157), and PD size cueing and practice have supporting evidence (PDT-16, PDT-20, PDT-33). Risks: it is not paper, and typing is a free alternative for notes.
4. **Therapy tool.** The app and passive pen with a clinician protocol, after an unassisted-retention study (EXP-H04 style, REQ-VAL-002). Children's handwriting programmes need practice (HAP-41), and PD amplitude training works with costs (PDT-16, PDT-17).
5. **Desk writing surface.** Decide after the other study reports and after GNG-2 measures the paper-bound desk jobs (forms, cards, signatures). A surface misses the standing sixth of older adults' writing occasions (HAP-159).
6. **Active pen**, the long-term flagship, only after GNG-10 (DEC-055 passed on real inputs), the discovery gates GNG-1 to GNG-5, and EXP-U07. Until then it stays a research instrument, and its measurement subsystems feed options 2–4.

**What would move the active pen earlier.** A tracker that passes DEC-055. A survey showing a large unserved paper job (GNG-2 well above 30 %) with willingness to pay above the cost-implied price (GNG-5). A payer route that accepts writing ADL outcomes.

## 7. Customer-discovery pack

### 7.1 Instruments

| File | Use |
|---|---|
| [`interview_guide_people_with_tremor_or_pd.md`](../results/market/interview_guide_people_with_tremor_or_pd.md) | EXP-U02, 12–16 interviews per diagnosis |
| [`interview_guide_clinicians.md`](../results/market/interview_guide_clinicians.md) | EXP-U03, 12–16 OTs, PD nurses, neurologists, SLTs |
| [`interview_guide_parents_teachers.md`](../results/market/interview_guide_parents_teachers.md) | EXP-U04, adults only |
| [`screening_survey.md`](../results/market/screening_survey.md) | EXP-U01, at least 100 ET and 100 PD; item-to-metric map |
| [`landing_page_test_plan.md`](../results/market/landing_page_test_plan.md) | EXP-U05, honest waitlist pages with price arms |
| [`go_no_go_criteria.csv`](../results/market/go_no_go_criteria.csv) | GNG-1 to GNG-10, fixed in advance |
| [`recruitment_and_ethics.md`](../results/market/recruitment_and_ethics.md) | Routes, approvals, consent, children, data protection |

**Sizes.** Interview numbers follow empirical saturation: 9–17 interviews for homogeneous groups (LITERATURE, HAP-164). With 100 survey answers per group, the widest 95 % interval on a proportion is about ±10 percentage points; with 200, about ±7 (CALCULATION).

### 7.2 Go/no-go criteria (decided now; all thresholds are ASSUMPTIONS)

| Id | Question | Go | No-go |
|---|---|---|---|
| GNG-1 | Share of people with writing affected who still write by hand at least weekly (lists, notes, forms, signatures, cards) | ≥ 50 %, lower 95 % bound ≥ 40 % | < 30 % |
| GNG-2 | Share with a paper-bound task in the last 3 months that they avoided, delegated or had rejected, and that could not be typed or dictated | ≥ 30 % | < 15 % |
| GNG-3 | Among those who tried a weighted or grip pen, share scoring it ≤ 5 of 10 | ≥ 40 % | ≥ 70 % score it ≥ 7 of 10 |
| GNG-4 | Share for whom typing or dictation already covers almost all or most writing | ≤ 50 % | ≥ 70 % |
| GNG-5 | In the serviceable subgroup, share who would "definitely" buy a proven pen at 500 (GBP or USD) | ≥ 20 % | < 10 % at 250 |
| GNG-6 | Confirmed waitlist sign-ups per unique visitor (≥ 400 per arm) | ≥ 10 % in any arm | < 3 % in every arm |
| GNG-7 | Clinicians (of 12–16) who would recommend a proven device / services willing to host a study | ≥ 6 / ≥ 3 | ≤ 2 recommend |
| GNG-8 | Measuring pen: written expressions of interest (of ≥ 10 approached) / co-funded pilots in 6 months | ≥ 3 / ≥ 1 | 0 |
| GNG-9 | Parents and teachers (≥ 100): daily school handwriting / an unmet writing job | ≥ 50 % / ≥ 30 % | < 20 % unmet |
| GNG-10 | DEC-055 on real inputs (severe class, +2 readable words, clean writing ≤ 25 µm) | passes | fails |

**Context for the thresholds.**
- GNG-1: 62 % of GB adults aged 65+ write lists weekly (LITERATURE, HAP-158). People with tremor may write less; that is exactly what is being measured.
- GNG-5: the 500 price is the low end of the cost-implied price (§6.1).

**Decision rules.**
- **Active pen, consumer path:** GNG-1, GNG-2, GNG-3 and GNG-5 pass, GNG-4 does not fail, and GNG-10 passes. Otherwise the pen stays a research flagship.
- **Tablet app:** GNG-1 (adults) or GNG-9 (children), GNG-6 for its page, and GNG-7.
- **Measuring pen:** GNG-8 and GNG-7.
- **Therapy tool:** GNG-7, and GNG-9 for children or clinician demand for PD.
- **Desk surface:** GNG-1, GNG-2 (desk tasks) and GNG-6.
- **A grey result** (between go and no-go) buys a second survey wave or one rewrite of the page. It never buys tooling.

### 7.3 Recruitment

UK routes:
- Parkinson's UK's Take Part Hub and Research Support Network. It asks for "your full ethical approval or support letter" and a participant information sheet, shares studies for free, and needs up to 10 weeks (LITERATURE, PDT-119).
- The National Tremor Foundation.
- NHS PD nurses and OT services. HRA and HCRW Approval applies to research in the NHS in England and Wales where the NHS has a duty of care to participants (LITERATURE, PDT-119).
- Professional and school networks.

US routes:
- The International Essential Tremor Foundation. Its database reached 19,206 people in a 2021 survey (LITERATURE, PDT-99).
- PD foundations and the Fox Insight cohort (8,536 respondents in PDT-102).

Charity members are more engaged than the population, where half of people with ET do not notice their tremor (PDT-97). Report every result by recruitment route. Details: [`recruitment_and_ethics.md`](../results/market/recruitment_and_ethics.md).

### 7.4 Ethics note

- **Approval.** Discovery with patients is research with vulnerable adults and needs ethics approval before charity recruitment. Follow the Market Research Society Code of Conduct 2023 (PDT-119): meet vulnerable participants' needs and never pressure them (rules 23–24); state incentive terms, and do not pay in the project's own products (rules 25–26); never run activities "under the guise of research, which aim to manipulate, mislead or coerce" (rule 4).
- **Children.** No child is interviewed in discovery. Later children's studies need verified responsible-adult permission and the child's own right to decline, including in school (rules 16–22).
- **Signatures.** Never collect real signatures or documents; use a pseudo-signature, as the human-study plan already requires (`validation/human_study_plan.md` §10).
- **No money from patients** before a benefit is shown (DEC-094, proposed).
- **No benefit claims** on any page (CAP Code 12).

## 8. The user comparison study (EXP-U06 and EXP-U07)

### 8.1 Structure

**EXP-U06 is a pilot without any investigational device.**
- Conditions: ordinary pen, weighted pen, typing on a phone or tablet with accessibility settings, and dictation.
- It can run as soon as ethics approval is in place.
- It checks feasibility, qualifies the reading panel, times setups, and estimates the variability that sizes EXP-U07.

**EXP-U07 is the full comparison.** It adds three device states: unpowered, locked with matched mass, and on. It runs only on a build that has passed safety gate G-S (`validation/prototype_stages.md`), after the EXP-H06 pilot shows that the device works as intended. Any severe-class claim also needs GNG-10 (DEC-055).

### 8.2 Tasks

All tasks are short and use everyday content, because older adults write about 18 words per occasion (LITERATURE, HAP-159).

| Task | What the participant does | Main task outcome |
|---|---|---|
| T1 Signature | Signs a practised made-up name (pseudo-signature) three times | Similarity to their own reference pseudo-signature (blinded raters, 1–5); time |
| T2 Form | Completes a standard eight-field form: name, address, date, phone, tick boxes, one short answer | Fields read correctly; share of characters inside the boxes; time |
| T3 Shopping list | Writes ten items shown as pictures | Useful words per minute |
| T4 Sentence copying | Copies a standard sentence | Useful words per minute; letter height; legibility |
| T5 Free writing | Writes for 2 minutes on "your morning" | Useful words per minute; legibility |
| T6 Simple drawing | Copies a simple house outline and draws a spiral | Blinded shape rating (0–4); time |

**Which conditions apply to which task** (✓ = run; – = not applicable):

| Task | Ordinary pen | Weighted pen | Device unpowered | Device locked, matched mass | Device on | Typing, phone or tablet, accessibility settings | Dictation |
|---|---|---|---|---|---|---|---|
| T1 Signature | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (finger or stylus signature on screen) | – |
| T2 Form | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (the same form on screen) | ✓ (into the screen form) |
| T3 List | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| T4 Copying | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| T5 Free writing | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| T6 Drawing | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (stylus on screen) | – |

### 8.3 Conditions

| Condition | Definition |
|---|---|
| Ordinary pen | A light ballpoint of normal diameter (the reference) |
| Weighted pen | A commercially available weighted pen, the same model for everyone (PDT-107) |
| Device unpowered | The pen with its battery removed or disabled: the flat-battery case. Rev K's unpowered nib rests on its stop 1.26 mm off centre (project CALC, [`claims_register.md`](claims_register.md)), so this tests whether the pen is still a usable pen |
| Device locked, matched mass | The same pen with the nib mechanically locked at centre: EXP-H06's OFF condition. It separates the active effect from mass and shape |
| Device on | The pre-specified assistance mode (ASSIST_KF, or GUIDED for guided tasks), as frozen for EXP-H06 |
| Typing with accessibility settings | The participant's own phone or a standard tablet. The researcher configures Touch Accommodations or equivalents and text size from a written checklist, and records the settings used (HAP-162) |
| Dictation | The device's built-in dictation, on the same phone or tablet. Participants may correct by voice or touch |

EXP-H06's powered sham (NEUTRAL) is not repeated in EXP-U07, to limit burden. Blinding of the device states relies on H06's validation.

### 8.4 Outcomes

Definitions follow `validation/human_study_plan.md` §3.6 where one exists.

- **Useful words per minute (new).** Words that match the intended text, divided by task time, from the start cue to the participant's "done", including corrections.
  - For handwriting, a word counts when it matches the target (copy tasks) or the participant's own read-back (self-generated tasks) and at least 2 of 3 blinded naive readers transcribe it correctly.
  - For typed or dictated text, a word counts when it matches after the participant's own corrections.
- **Legibility.** Share of handwritten words transcribed correctly by blinded naive readers (§3.6), using EXP-R03's panel procedure.
- **Errors.** Omissions, substitutions and insertions left in the final text. Recognition errors for dictation are recorded separately.
- **Effort.** NASA-TLX (raw) after each condition (§3.6).
- **Fatigue.** Borg CR10 for hand and arm after each condition and at the end (§3.6).
- **Preference.** A ranking of conditions for each task class at the end, and "Which would you use at home for [task]?"
- **Setup time (new).** From being handed the tool (phone locked, pen switched off) to the first useful word. Includes unlocking, opening an app, switching on dictation, and powering and calibrating the pen.
- **Adverse events.** ISO 14155 definitions and stopping rules (§3.4).
- **Payer-readable secondary outcomes.** The Bain-Findley ADL writing item (or the TETRAS ADL writing item) and MDS-UPDRS 2.7, before and after; QUEST 2.0 at the end (REQ-MKT-007, proposed).

### 8.5 Design, randomisation and blinding

**Sessions.** Two sessions of at most 90 minutes each, with breaks every 15 minutes (participant burden as `validation/human_study_plan.md` §10).
- Session 1: ordinary pen, weighted pen, typing, dictation. This session is the whole of EXP-U06.
- Session 2 (EXP-U07 only): device on, locked, unpowered, and the ordinary pen again as a bridge between sessions.

**Order.** Condition order within each session follows a Williams design for four conditions (four sequences), allocated by computer with concealment (§3.5). Task order within a condition is fixed (T1 to T6).

**Blinding.**
- The device states are blinded to participant and operator as far as possible. The participant's guess is recorded after each period (Bang's index; §3.5).
- Readers and raters are blinded to condition: scans are coded and shown in random order. Typed and dictated outputs are scored automatically against the intended text.

### 8.6 Analysis

**Unit.** Each participant is the unit of analysis. Words and strokes are aggregated to one value per participant, condition and task class before any test. Many strokes from one person are not many people (engineering report §9).

**Primary analysis (EXP-U07).**
- A linear mixed model on log useful words per minute for the text tasks (T3–T5): condition, session, period and task as fixed effects, and participant as a random effect.
- Contrast: device on against locked with matched mass, reported as a geometric-mean ratio with a 95 % CI.
- Analysed separately for ET and for PD (REQ-USR-001).

**Key secondary analyses, in fixed sequence** (the next is tested only if the previous succeeds):
1. device on against the weighted pen;
2. device on against the ordinary pen;
3. unpowered against the ordinary pen (non-inferiority on legibility, margin −5 percentage points, as AC-H06-05).

**Pen against digital alternatives.** Estimated with 95 % CIs for each task, with no superiority test. The pen is not expected to beat dictation on text speed. The question is what each person would choose for each task.

**Strata** (exploratory):
- tip-tremor class (mild, moderate, severe, by the EXP-H01 method; REQ-DATA-004);
- age (under 65 / 65+);
- speech intelligibility (share of words a naive listener transcribes from a short reading).

**Missing data.** Mixed models under missing-at-random, with per-protocol and delta-adjusted sensitivity analyses (§3.7). Pre-registration, and reporting of every result, follow §3.7.

### 8.7 Sample size from the pilot

1. **Pilot.** Run EXP-U06 with 12–16 participants per diagnosis. Pilots estimate the SD imprecisely, and recommended pilot sizes are 15 per arm for medium effects (LITERATURE, HAP-165); a within-participant design needs fewer.
2. **Planning SD.** From the pilot, estimate σ_D: the SD of within-participant differences in log useful words per minute between two pen conditions (ordinary against weighted), as a proxy for pen-to-pen differences. Plan with the upper 80 % confidence limit of σ_D, which multiplies the pilot SD by 1.255 for 12 pilot participants and by 1.206 for 16 (CALCULATION, chi-square).
3. **Effect.** Choose the smallest effect users would value: a 20 % gain in useful words per minute (ratio 1.2) is the proposed default (ASSUMPTION; AC-U07-02). Confirm it in the interviews.
4. **Size.** Compute n for a paired t-test (two-sided α 0.05, power 0.80), add 15 % attrition, then round up to a multiple of four sequences (the table below stops before this rounding).

Worked examples (CALCULATION, exact paired t; pilot n = 12; the pilot SDs are ASSUMPTIONS for illustration):

| Pilot σ_D (log units) | Planning σ_D | n for ratio 1.2 | n for ratio 1.3 | n for ratio 1.5 |
|---|---|---|---|---|
| 0.30 | 0.376 | 36 (43 with attrition) | 19 (23) | 9 (11) |
| 0.40 | 0.502 | 62 (73) | 31 (37) | 15 (18) |
| 0.50 | 0.627 | 95 (112) | 47 (56) | 21 (25) |

These are **per diagnosis group**. The pilot replaces every assumed SD, as `validation/human_study_plan.md` §11 requires for all studies.

### 8.8 Participants

**Inclusion.**
- Adults with clinician-diagnosed ET (2018 consensus) or PD (Hoehn and Yahr 1–3), as in `validation/human_study_plan.md` §3.1.
- Self-reported writing difficulty (survey item S7 ≥ 1).
- Able to write at least a few words.
- Able to use a phone or tablet with instruction (own or provided).
- Dictation: no speech criterion; intelligibility is recorded, because it is part of the question.
- EXP-U07 only: tip tremor measured by the EXP-H01 method.

**Exclusion.** As §3.2: other neurological conditions affecting the writing hand, severe arthritis, recent hand surgery, open skin lesions, and inability to consent. For EXP-U07 add the actuated-device exclusions: active implantable devices, until the magnetic-field assessment permits inclusion.

**Strata.** Diagnosis; tip-tremor class; age; left-handedness (at least 10 % left-handed, ASSUMPTION). Optional: 8–12 age-matched adults without a neurological diagnosis as reference values.

### 8.9 Ethics and safety

- **EXP-U06** is research with patients but not a device investigation: ethics committee approval, plus HRA and HCRW Approval if run in the NHS in England or Wales (PDT-119).
- **EXP-U07** is a clinical investigation of an investigational device: ethics, the device-investigation route (the MHRA in the UK), ISO 14155, gate G-S for the exact build, the independent safety monitor, and the stopping rules of `validation/human_study_plan.md` §3.4 and §10.
- **Data.** Pseudo-signatures only; data minimisation; a data protection impact assessment; large-print materials; travel reimbursement; home visits on request.

### 8.10 Mapping to `validation/human_study_plan.md` (proposed rows; the plan is not edited)

| Existing element | How EXP-U06/U07 uses it |
|---|---|
| §3.1 group definitions; §3.2 inclusion and exclusion | Used as is, with the additions in §8.8 |
| §3.3 consent; §10 pseudo-signature, data protection | Used as is |
| §3.4 safety; gate G-S | Required for EXP-U07's device states |
| §3.5 randomisation and blinding | Williams design in each session; blinded readers; Bang's index for device states |
| §3.6 outcome definitions | Legibility, writing speed, NASA-TLX, Borg CR10, QUEST 2.0 and preference used as is. New: useful words per minute, setup time, signature similarity, in-box share, the task-applicability matrix |
| EXP-H06 (§9) | EXP-U07's "locked" = H06's OFF, and "on" = H06's ON. U07 adds the unpowered, weighted-pen, typing and dictation conditions, and asks a task-level question after H06's pilot shows the device works |
| EXP-H01/R01 (§4, §21) | Tip-tremor class for stratification and EXP-U07 eligibility |
| EXP-R03 (§21) | The blinded reading panel's procedure scores legibility |
| EXP-W01, EXP-J09, EXP-K24 | Mass, balance and grip acceptability should pass before EXP-U07 |
| §11 sample-size rule | EXP-U06 is the pilot that replaces the assumed SDs |

Proposed new rows for the plan's §2 overview table (a new §26 would hold the details):

| ID | Question | Population (n) | Design | Primary outcome | Claim type | Stage / gate |
|---|---|---|---|---|---|---|
| EXP-U01 (§26) | Do people with ET or PD whose writing is affected still write by hand weekly? Which paper jobs are unserved, and what would they pay? | ≥ 100 ET + ≥ 100 PD (UK, US) | Cross-sectional survey via charities; thresholds fixed in advance | GNG-1 to GNG-5 proportions with Wilson 95 % CIs | none (market) | Ethics (non-NHS); before any tooling |
| EXP-U02 (§26) | Which writing jobs matter, what is used instead, and why are aids abandoned? | 12–16 ET + 12–16 PD | Semi-structured interviews to saturation | Coded unserved jobs; adoption barriers | none | Ethics |
| EXP-U03 (§26) | How do clinicians assess and support writing, who pays, and would they use a measuring pen? | 12–16 clinicians | Semi-structured interviews | GNG-7; GNG-8 | none | Ethics; HRA if at NHS sites |
| EXP-U04 (§26) | How much must children with writing difficulties handwrite, and what is unmet? | 12–16 adults interviewed + ≥ 100 surveyed | Interviews and survey, adults only | GNG-9 | none | Ethics |
| EXP-U05 (§26) | Do people ask to be kept informed after an honest description, and does price matter? | ≥ 400 visitors per arm per page | Randomised price arms on waitlist pages | GNG-6 | none | Ethics review of the copy; CAP Code |
| EXP-U06 (§26) | How do people with ET or PD perform six everyday tasks with an ordinary pen, a weighted pen, typing with accessibility settings and dictation? | 12–16 ET + 12–16 PD | Within-subject, Williams order, blinded readers; no investigational device | Feasibility; pilot SD of log useful words per minute | none (feasibility) | Ethics; can start now |
| EXP-U07 (§26) | While active, does the pen give more useful writing than the same pen locked with matched mass, than a weighted pen, and than typing or dictation where they apply? | n from EXP-U06, per group | Within-subject crossover, 2 sessions, 7 conditions; blinded readers and device states | GM ratio of useful words per minute, on / locked | IA | After G-S on the build and the EXP-H06 pilot; severe-class claims also need DEC-055 |
| EXP-U08 (§26) | Is a measuring pen reliable and quick enough for clinics and trials? | 15 ET + 15 PD + 10 controls | Test-retest over 1–2 weeks; blinded clinical ratings | ICC of the primary writing metrics | none (measurement) | Stage A passive instrumented pen (as EXP-H01) |
| EXP-U09 (§26) | Is a tablet or therapist-led practice tool usable, and used, at home or school? | 20 PD with micrographia + 20 children with DCD (with their OT) | Single-arm, 4-week usability and adherence pilot | Adherence; System Usability Scale; drop-out | none (no lasting-improvement claim) | Ethics; child safeguards |

Proposed §11 sample-size rows:

| Study | n | Basis |
|---|---|---|
| EXP-U01 | ≥ 100 per diagnosis | Widest 95 % CI about ±10 points at n = 100 (CALCULATION) |
| EXP-U02–U04 | 12–16 per group | Saturation within 9–17 interviews (HAP-164) |
| EXP-U05 | ≥ 400 visitors per arm | ±3 points at 10 % conversion (CALCULATION) |
| EXP-U06 | 12–16 per diagnosis | Pilot for the SD (HAP-165) |
| EXP-U07 | from EXP-U06; e.g. 37 per diagnosis for ratio 1.3 at a pilot σ_D of 0.40 (40 after rounding to four sequences) | Exact paired t on the upper 80 % limit of the pilot SD, +15 % attrition (§8.7) |
| EXP-U08 | 30 patients + 10 controls | Precision of an ICC near 0.8 (ASSUMPTION; to be computed at protocol stage) |
| EXP-U09 | 20 + 20 | Feasibility (ASSUMPTION) |

## 9. What would change these conclusions

| New result | Consequence |
|---|---|
| GNG-1 below 30 %: people with tremor have largely stopped handwriting | Drop the paper-based consumer options (active pen, desk surface); keep measurement and the app |
| GNG-2 well above 30 %, with specific jobs such as signatures and forms | Design the active pen and desk surface around those jobs (REQ-MKT-005); consider a signature-consistency claim study |
| GNG-3 fails: weighted pens satisfy most people | The active pen must show a large margin over a weighted pen, or stop |
| GNG-5 at 500 well above 20 % | The Rev K cost basis is viable; plan a first batch around 1,000 units, with the US in scope |
| A tracker passes DEC-055 on real inputs | The conditional serviceable segment in §4.5 becomes real; run EXP-U07 |
| GNG-8 passes with a co-funded pilot | Prioritise the measuring pen and its regulatory route |
| A UK count of diagnosed ET is found | Replace the ASSUMPTION IN-ET-DX-UK in the model |

## 10. Open gaps

1. **Handwriting frequency among people with tremor or PD.** Only general-population data were found (HAP-158). This is GNG-1.
2. **Unserved paper jobs and their frequency** in the target group. This is GNG-2.
3. **Item-level distributions of writing items** (TETRAS ADL writing, Bain-Findley writing, MDS-UPDRS 2.7) in population or clinic samples: not found.
4. **UK count of diagnosed ET:** not found. The model transfers the US claims rate (ASSUMPTION).
5. **Tablet ownership** among older adults with tremor: not found. Pew's release covers smartphones only.
6. **The effect of accessibility settings** (Touch Accommodations, filter keys) on typing in tremor: no study found.
7. **Prices not found:** Cala TAPS, Readi-Steadi, Gyenno, keyguards, OT services, the NeuroMotor Pen. Liftware's current price and availability were not verified (manufacturer site unavailable).
8. **Motor causes of mail-ballot signature rejections:** unknown.
9. **Regulatory routes to confirm:** UK (GB) classification under UK MDR 2002; whether a trial-only measuring pen needs its own authorisation; whether an actuated pen needs a US 510(k) under 890.9(b).
10. **Adoption rates, market-access shares and therapy-referral shares** in the model are ASSUMPTIONS.
11. **Stated purchase intent** overstates buying (ASSUMPTION). Only the waitlist test measures behaviour, and only weakly.
12. **Evidence behind the Steadi-3 Plus and GyroGlove claims:** not peer-reviewed as far as found.
13. **Ofcom's 2026 report and the NCSL table** could not be opened (HTTP 403); their figures are second-hand and labelled so.

## 11. Files and how to regenerate

| File | Contents |
|---|---|
| `docs/market_and_users.md` | This document |
| `results/market/market_sizing.csv` | 120 rows: inputs (labelled) and derived totals, serviceable and early-adopter segments per option and region |
| `results/market/sizing_model.py` | Regenerates the CSV: `python3 results/market/sizing_model.py` (arithmetic only, under a second) |
| `results/market/competitors.csv` | 23 alternatives: price, date, regulatory status, evidence, weaknesses, ledger ids |
| `results/market/evidence_rows.csv` | 47 ledger rows (PDT-90…119, HAP-150…166), docs/evidence.csv's 23-column header, CRLF line endings |
| `results/market/go_no_go_criteria.csv` | GNG-1 to GNG-10 |
| `results/market/proposed_requirements.csv` | REQ-MKT-001…010 in docs/requirements.csv's format |
| `results/market/proposed_acceptance_criteria.csv` | AC-U01-01…AC-U09-05 (45 rows) in validation/acceptance_criteria.csv's format |
| `results/market/interview_guide_*.md`, `screening_survey.md`, `landing_page_test_plan.md`, `recruitment_and_ethics.md` | The discovery instruments |

## 12. Proposed rows for the lead

None of these rows has been entered into a shared file; the lead decides and commits.

### 12.1 Decisions (for `docs/decisions.md`)

| ID | Decision | Alternatives considered | Evidence | Status | Revisit trigger |
|---|---|---|---|---|---|
| DEC-090 | **Pursue measurement and practice before the active pen; keep the active pen as the long-term flagship behind hard gates** (proposed; study U, `docs/market_and_users.md` §6.5). Order: (1) customer discovery and the no-device pilot (EXP-U01 to U06) now; (2) a measuring pen for research, clinics and trials, built from the passive instrumented pen EXP-H01/R01 already needs; (3) a tablet app for measurement, practice and clearer on-screen writing; (4) a clinician-led practice tool after an unassisted-retention study; (5) the desk surface after its own study and GNG-2; (6) the active consumer pen only after GNG-10 (DEC-055) passes, GNG-1 to GNG-5 pass and EXP-U07 shows benefit | The active pen first as the consumer product; stop the project; digital products only | For paper: 62 % of GB adults 65+ write lists by hand weekly (HAP-158); signatures on paper persist (PDT-105, PDT-106); writing is affected in 80 % of engaged ET (PDT-99). Against the active pen now: no tracker passes DEC-055; cost-implied price $508–2,039 against $8–125 passive aids (CALCULATION; PDT-107); passive utensils matched active ones in preference (ACT-18, ACT-19). Literature and calculation | proposed | GNG results (EXP-U01 to U05); DEC-055 passing; EXP-U07 |
| DEC-091 | **Adopt the go/no-go criteria GNG-1 to GNG-10 (`results/market/go_no_go_criteria.csv`) before discovery starts; a grey or no-go result never releases tooling or volume funds** | Decide informally after the interviews | Thresholds are ASSUMPTIONS fixed in advance; stated intent overstates buying (ASSUMPTION), so the waitlist test is a behavioural check | proposed | Before EXP-U01 launches; after wave 1 only the sample size may change, not the thresholds |
| DEC-092 | **Typing with configured accessibility settings and dictation are mandatory comparators, with an ordinary pen and a weighted pen, in every benefit study; device studies add the device unpowered and locked with matched mass** (REQ-MKT-001) | ON against OFF/NEUTRAL only (EXP-H06) | Dictation 153 vs 52 WPM for clear speakers (HAP-161) but 36.3 % word errors on PD speech (PDT-104); typing affected in 54 % of ET (PDT-99); passive aids strong in preference (ACT-18, ACT-19); engineering report §7 | proposed | EXP-U06 results |
| DEC-093 | **First customers are researchers, clinicians and trial sponsors (measuring pen, practice tool) in the UK and US, not consumers; any consumer launch waits for EXP-U07** | Direct-to-consumer launch first | 80 industry PD phase 2/3 drug trials open or active (PDT-116); NICE conditionally recommends PD monitors and lists prices from £64 per patient-month to £225 per use (PDT-115); US Medicare unlikely to pay for a pen (PDT-117); consumer price competition from $8 to $5,899 (PDT-107 to PDT-110) | proposed | GNG-7, GNG-8; regulatory advice on trial-only use |
| DEC-094 | **Honest discovery: waitlists only, no deposits or payments from patients or families before a demonstrated benefit; every participant-facing text says "in development, not proven"; all results are reported** (REQ-MKT-009) | Refundable deposits or pre-orders to test willingness to pay | CAP Code 12.1 and 12.6; MRS Code rules 4 and 23–26 (PDT-119); vulnerable users | proposed | Only after EXP-U07 passes and the product has conformity marking |

### 12.2 Requirements (for `docs/requirements.csv`; full rows in `results/market/proposed_requirements.csv`)

| ID | Title | Requirement (short) | Verification |
|---|---|---|---|
| REQ-MKT-001 | Named comparators | Every benefit study compares ordinary pen, weighted pen, typing with accessibility settings and dictation; device studies add unpowered and locked with matched mass | EXP-U06, EXP-U07 |
| REQ-MKT-002 | Discovery before tooling | No tooling or volume commitment for the active pen before GNG-1 to GNG-5 are evaluated | Lead review |
| REQ-MKT-003 | Price justified by willingness to pay | Target retail price ≤ the highest tested price at which ≥ 20 % of the serviceable subgroup would definitely buy, unless a payer route is secured | EXP-U01, EXP-U05 |
| REQ-MKT-004 | Ready in seconds; usable when flat | Median setup ≤ 10 s with no app step; unpowered legibility non-inferior to an ordinary pen (margin −5 points) | EXP-U07 |
| REQ-MKT-005 | Paper-bound jobs, not text speed | Prioritise the unserved paper jobs found in discovery; do not compete with dictation on speed | EXP-U01, U02, U07 |
| REQ-MKT-006 | Measuring pen: reliable, quick, separate | Test-retest ICC ≥ 0.80; \|ρ\| ≥ 0.5 with blinded clinical items; ≤ 10 min; own intended purpose; consumer pen keeps REQ-USR-003 | EXP-U08 |
| REQ-MKT-007 | Payer-readable outcomes | Record Bain-Findley (or TETRAS) ADL writing, MDS-UPDRS 2.7 and QUEST 2.0; confirm licences | EXP-U07 protocol review |
| REQ-MKT-008 | Intended purpose and class per option | Written intended purpose and US and EU/UK classification rationale before any external claim; CAP Code 12 | Regulatory adviser review |
| REQ-MKT-009 | Honest discovery | No money from patients before benefit; "in development, unproven" on all texts; report all results | Ethics review; EXP-U05 audit |
| REQ-MKT-010 | Children | Compare with typing and OT practice; measure unassisted retention; never claim to treat dyslexia; child-research safeguards | EXP-U09; children's protocols |

### 12.3 Experiments EXP-U01…U09 and their criteria (for `validation/acceptance_criteria.csv`; full rows in `results/market/proposed_acceptance_criteria.csv`)

The experiments themselves (question, population, design, primary outcome, gate) are defined in the §8.10 table. Their criteria:

| ID | Req. | Experiment | Metric | Threshold | Direction |
|---|---|---|---|---|---|
| AC-U01-01 | REQ-MKT-002 | EXP-U01 | GNG-1: writing by hand at least weekly, lower 95 % bound, per diagnosis | 40 % | ≥ |
| AC-U01-02 | REQ-MKT-005 | EXP-U01 | GNG-2: unserved paper-bound task in 3 months | 30 % | ≥ |
| AC-U01-03 | REQ-MKT-001 | EXP-U01 | GNG-3: weighted or grip pen scored ≤ 5 of 10 | 40 % | ≥ |
| AC-U01-04 | REQ-MKT-005 | EXP-U01 | GNG-4: typing or dictation already covers most writing | 50 % | ≤ |
| AC-U01-05 | REQ-MKT-003 | EXP-U01 | GNG-5: "definitely buy" at 500, serviceable subgroup | 20 % | ≥ |
| AC-U01-06 | REQ-USR-001 | EXP-U01 | Responses per diagnosis | 100 | ≥ |
| AC-U01-07 | REQ-USR-001 | EXP-U01 | Results per diagnosis, country and route; no pooled claim | conforms | pass/fail |
| AC-U02-01 | REQ-MKT-005 | EXP-U02 | Interviews per group, stopping after 3 with no new job code | 12 | ≥ |
| AC-U02-02 | REQ-MKT-005 | EXP-U02 | Unserved paper jobs each named by ≥ 25 % of a group | 1 | ≥ |
| AC-U02-03 | REQ-MKT-009 | EXP-U02 | Real signatures or documents collected | 0 | = |
| AC-U03-01 | REQ-MKT-006 | EXP-U03 | GNG-7: recommend / host | 6 / 3 | ≥ |
| AC-U03-02 | REQ-MKT-006 | EXP-U03 | GNG-8: expressions of interest / co-funded pilots | 3 / 1 | ≥ |
| AC-U03-03 | REQ-MKT-008 | EXP-U03 | Payer routes documented per option | 2 | ≥ |
| AC-U04-01 | REQ-MKT-010 | EXP-U04 | GNG-9: daily school handwriting / unmet job | 50 % / 30 % | ≥ |
| AC-U04-02 | REQ-MKT-010 | EXP-U04 | Children interviewed | 0 | = |
| AC-U05-01 | REQ-MKT-002 | EXP-U05 | GNG-6: sign-ups per unique visitor in at least one arm | 10 % | ≥ |
| AC-U05-02 | REQ-MKT-009 | EXP-U05 | Payments or deposits from patients | 0 | = |
| AC-U05-03 | REQ-MKT-009 | EXP-U05 | Upheld "misleading" complaints | 0 | = |
| AC-U05-04 | REQ-MKT-003 | EXP-U05 | Sign-up rate at the 500–700 arm relative to no price | 0.5 | ≥ |
| AC-U06-01 | REQ-MKT-001 | EXP-U06 | Task × condition cells completed | 90 % | ≥ |
| AC-U06-02 | – | EXP-U06 | Session length | 90 min | ≤ |
| AC-U06-03 | REQ-MKT-001 | EXP-U06 | Reader agreement on words read (ICC) | 0.80 | ≥ |
| AC-U06-04 | REQ-MKT-001 | EXP-U06 | Pilot σ_D reported with its upper 80 % limit | conforms | pass/fail |
| AC-U06-05 | REQ-MKT-004 | EXP-U06 | Setup time recorded for every condition | conforms | pass/fail |
| AC-U07-01 | REQ-MKT-001 | EXP-U07 | Primary: useful words per minute, on / locked, lower 95 % bound, per group | 1.0 | > |
| AC-U07-02 | REQ-MKT-001 | EXP-U07 | Primary point estimate for "meaningful" | 1.20 | ≥ |
| AC-U07-03 | REQ-MKT-001 | EXP-U07 | On / weighted pen, lower 95 % bound (fixed sequence) | 1.0 | > |
| AC-U07-04 | REQ-MKT-001 | EXP-U07 | Words read correctly, on minus locked | +10 points | ≥ |
| AC-U07-05 | – | EXP-U07 | NASA-TLX, on minus ordinary pen, upper 95 % bound | 10 points | ≤ |
| AC-U07-06 | REQ-MKT-005 | EXP-U07 | Participants choosing the device for ≥ 1 paper-bound task | 50 % | ≥ |
| AC-U07-07 | REQ-MKT-004 | EXP-U07 | Median setup time, device on | 10 s | ≤ |
| AC-U07-08 | REQ-MKT-004 | EXP-U07 | Unpowered minus ordinary pen, words read, lower 95 % bound | −5 points | ≥ |
| AC-U07-09 | – | EXP-U07 | Serious adverse device effects | 0 | = |
| AC-U07-10 | REQ-USR-001 | EXP-U07 | Results per group and tremor class; no pooled claim | conforms | pass/fail |
| AC-U07-11 | REQ-MKT-007 | EXP-U07 | Payer-readable writing items recorded | conforms | pass/fail |
| AC-U08-01 | REQ-MKT-006 | EXP-U08 | Test-retest ICC of each primary metric, per group | 0.80 | ≥ |
| AC-U08-02 | REQ-MKT-006 | EXP-U08 | \|ρ\| with the blinded clinical writing or spiral item | 0.5 | ≥ |
| AC-U08-03 | REQ-MKT-006 | EXP-U08 | Median assessment time | 10 min | ≤ |
| AC-U08-04 | REQ-MKT-006 | EXP-U08 | Median clinician System Usability Scale score | 70 | ≥ |
| AC-U08-05 | REQ-USR-003 | EXP-U08 | Diagnostic output shown to participants | 0 | = |
| AC-U09-01 | REQ-MKT-010 | EXP-U09 | Median share of planned sessions completed | 70 % | ≥ |
| AC-U09-02 | – | EXP-U09 | Median System Usability Scale score | 70 | ≥ |
| AC-U09-03 | – | EXP-U09 | Drop-out over 4 weeks | 20 % | ≤ |
| AC-U09-04 | REQ-VAL-002 | EXP-U09 | No lasting-improvement claim from the pilot | conforms | pass/fail |
| AC-U09-05 | REQ-MKT-010 | EXP-U09 | Materials claiming to treat dyslexia | 0 | = |

All thresholds marked "hypothesis" in the CSV are ASSUMPTIONS fixed in advance. The requirement-type rows follow existing project rules (REQ-USR-001, REQ-USR-003, REQ-VAL-002, ISO 14155).

### 12.4 Evidence rows (for `docs/evidence.csv`)

47 rows in `results/market/evidence_rows.csv`, with the ledger's 23-column header and CRLF line endings:

| Ids | Topics |
|---|---|
| PDT-90…93 | Parkinson's prevalence: world, UK, US |
| PDT-94…98 | ET prevalence, diagnosis and disability |
| PDT-99…102 | Writing affected in ET and PD |
| PDT-103, 104 | Voice and speech recognition in PD |
| PDT-105, 106 | Signature requirements in the UK and US |
| PDT-107…113 | Competitor prices and evidence; Medicare coverage |
| PDT-114 | Regulatory classes |
| PDT-115 | NICE prices for PD monitors |
| PDT-116 | Trial counts and FDA guidance |
| PDT-117 | Who pays |
| PDT-118 | Population denominators |
| PDT-119 | Claims, market-research code and recruitment rules |
| HAP-150…157 | Children, school and tablets |
| HAP-158…163 | Handwriting use, digital access and alternatives |
| HAP-164, 165 | Methods: interview saturation, pilot size |
| HAP-166 | A clinical digital pen competitor |

### 12.5 Human-study plan rows

The §2 overview rows, the §11 sample-size rows and the mapping to the existing sections are in §8.10 above, ready to paste into a new §26 of `validation/human_study_plan.md`.
