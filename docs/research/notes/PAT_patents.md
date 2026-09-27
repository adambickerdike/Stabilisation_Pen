# Patent landscape and claim map: actuated-nib tremor-stabilising pen

Prepared by technical prior-art research support (not a lawyer) for the Stabilisation Pen programme.
Searches and retrievals ran on 2026-09-26 and, for a few items after midnight, 2026-09-27 (UTC).
The companion ledger is `docs/research/ledger/PAT_patents.csv` (25 records, PAT-01 to PAT-25).

> **This is not a legal opinion.** Three questions are separate and each needs a registered patent attorney
> working from certified claim text and official file histories:
>
> 1. **Novelty/patentability** of our own features over the prior art listed here, which includes expired, abandoned and withdrawn documents.
> 2. **Practical differentiation**: engineering choices that make our product technically different from a given disclosure.
> 3. **Freedom to operate (FTO)**: whether making or selling our product in a given country would infringe claims that are in force there.
>
> A document can matter for (1) and not at all for (3), for example a lapsed patent. The reverse also happens: a narrow live claim can matter for (3) while adding little for (1).
> Unless stated otherwise, every legal status below is **as displayed on Google Patents on the date given; not verified in an official register** (USPTO Patent Center, EPO Register, CNIPA, KIPO, NL register).
> "Appears to recite" in the feature map is a technical reading by a non-lawyer. **Every mapping needs professional review.**

---

## 1. Programme features used for the map

| Code | Feature |
|---|---|
| a | 2-axis actuated nib/refill relative to the barrel (electromagnetic or piezo actuators, flexure stage) |
| b | IMU-based tremor estimation |
| c | Optical local motion sensing near the tip |
| d | Stage (nib/refill) position sensing |
| e | Contact (nib) force sensing |
| f | Predictive cancellation |
| g | Guided letter formation / predefined characters or shapes |
| h | Confidence-based authority limiting (limit correction authority when estimates are uncertain) |
| i | Capture of the corrected (actually inked) trajectory for digital notes |
| j | Pivoting refill with a front flexure and rear actuation |

---

## 2. Method, sources and limitations

- **Web search.** The session's shared WebSearch budget ran out after 8 queries from this task (other parallel work had used the rest), and 3 further queries were refused. After that, the **Google Patents query endpoint** (`https://patents.google.com/xhr/query?url=<encoded query>&exp=`) was used through the fetch tool as the patent search engine. Google Patents full-text pages were read through the same tool, which extracts and summarises page content automatically. Claims taken only from that route are marked "automated extraction" in the ledger.
- **Official documents.**
  - USPTO full-page image PDFs (`https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/<number>`) were downloaded and OCR'd with Tesseract 5.3.4. This gave verbatim claims for PAT-01, 04, 05, 09, 10, 12, 13, 22, 23, 24 and 25, plus front pages. Obvious OCR artefacts were corrected by hand, for example "(1)" to "(i)", "1s" to "is" and "mb" to "nib".
  - The same PDFs were used to check the automatically extracted claim 1 of PAT-06, 07, 08, 11, 13, 16, 20 and 21, and the EP B1 text was used for PAT-17. Checks confirmed PAT-06, 07, 08, 11, 17, 20 and 21. For PAT-16 the extraction wrongly listed claim 18 as independent.
  - **Three automated extractions did not match the official claims:** PAT-10 (US 10,078,320 B2), PAT-09 (US 10,369,045 B2) and PAT-13 (US 2025/0162342 A1). The tool appears to have returned pre-grant or other family-member text. All three records were rebuilt from the official documents. Claims still based only on automated extraction (PAT-03, 14, 15, 18 and 19, plus claims other than claim 1 where noted in the ledger) need checking against official texts.
  - The EP A1 publication for PAT-02 and the EP B1 for PAT-17 came from the EPO publication server (text layer). The PAT-02 European search report pages are images and were OCR'd.
- **Registers.**
  - The EPO Register returned HTTP 403 to automated access, so EP statuses are not verified.
  - CNIPA, KIPO, USPTO Patent Center and the NL register were not queried.
- **Machine translation.** Claims of CN and KR documents are Google machine translations, or the researcher's rendering of a displayed Korean claim for PAT-15. They must be checked against the originals.
- **Availability.** Google Patents intermittently returned HTTP 503 (rate limiting). Several planned queries and status checks could not be completed; these are listed in §3.4 and §11.
- **Search methods not available.** DuckDuckGo showed a captcha, Bing ignored search operators, the USPTO PPUBS search API returned 404, and FreePatentsOnline failed on TLS. No commercial database (Derwent, PatBase, Orbit) and no citation-forward searching were available.

---

## 3. Search log (exact queries, dates in UTC)

### 3.1 WebSearch tool

| # | Date | Exact query | Outcome / records taken |
|---|---|---|---|
| W1 | 2026-09-26 | `"handheld tool for leveling uncoordinated motion" patent` | US 9,943,430; US 10,532,465; US 10,219,930 B2; US 8,308,664 B2; US 6,730,049 B2 -> PAT-06, PAT-08 |
| W2 | 2026-09-26 | `Verily Liftware patent "unintentional muscle movements" handheld tool stabilization actuator` | US 10,058,445 B2; US 10,219,930 B2; US 2014/0052275 A1; US 8,308,664 B2; CN 109688924 B; US 9,925,034 B2; US 10,851,867 B2; US 10,758,388 -> PAT-07 |
| W3 | 2026-09-26 | `Shaper Tools Rivers "position-correcting tools" patent` | US 10,078,320 B2; US 10,795,333 B2; US 10,556,356 B2; US 2015/0094836 A1; US 2020/0061767 A1 -> PAT-10 |
| W4 | 2026-09-26 | `Riviere Carnegie Mellon Micron handheld micromanipulator tremor cancellation patent` | Papers only (Micron, New Scale, CMU); no patents |
| W5 | 2026-09-26 | `writing instrument actuator nib tremor patent` | Nothing relevant (US 5,165,814 A vibrating pen; retractable pens) |
| W6 | 2026-09-26 | `stylus tremor compensation actuator patent pen tip displacement` | US 8,308,664 B2; US 7,265,750 B2 (Immersion); US 10,101,824 -> PAT-04 |
| W7 | 2026-09-26 | `pen nib displacement actuator handwriting correction patent` | Retractable e-pens (Silverbrook), CN 104751688 A; not relevant |
| W8 | 2026-09-26 | `haptic guidance pen electromagnetic handwriting training patent` | Academic work only (electromagnetic haptic guidance under a tablet, UIST 2019/2020; KATIB); no patents |
| W9 | 2026-09-26 | `anti-tremor pen patent actuator refill counteract hand tremor Parkinson writing` | **Not executed** (budget exhausted) |
| W10 | 2026-09-26 | `"Riviere" patent "hand-held" instrument tremor "micromanipulator" google patents` | **Not executed** |
| W11 | 2026-09-26 | `handheld tool stabilization tremor actuator patent tip "relative to the handle" inertial sensor` | **Not executed** |

### 3.2 Google Patents query endpoint (decoded query strings)

| # | Date | Query (Google Patents syntax) | Notable hits / records taken |
|---|---|---|---|
| G1 | 2026-09-26 | `q=(tremor) (pen OR stylus OR "writing instrument") (actuator)`, num=50 | US 10,101,824 B2; US 10,369,045 B2; stylus-haptics families |
| G2 | 2026-09-26 | `q=TI=(tremor) (pen OR stylus OR writing OR handwriting OR penmanship)`, num=50 | US 10,101,824 B2; MY 171245 A; tremor-diagnosis pens (CN 115346661 B etc.) |
| G3 | 2026-09-26 | `q=(防抖笔)`, num=50 | Irrelevant (camera stabilisation) |
| G4 | 2026-09-26 | `q=(tremor OR shake OR jitter) (nib OR refill OR "pen tip") (actuator OR motor OR piezoelectric OR "voice coil")`, cpc=B43K, num=50 | US 2025/0162342 A1 (PAT-13); US 2021/0007519 A1 (PAT-20); US 12,122,180 B2 (PAT-21); CN 109263362 A |
| G5 | 2026-09-26 | `inventor=Riviere`, `q=(tremor)`, num=50 | US 10,369,045 B2 (PAT-09) |
| G6 | 2026-09-26 | `q=(tremor) (handheld OR hand-held) (stabiliz* OR cancel*) (actuator) (inertial OR accelerometer OR gyroscope)`, assignee=Lift Labs, num=50 | 0 results |
| G7 | 2026-09-26 | `q=(electromagnet OR magnetic) (pen OR stylus) (guid*) (handwriting OR drawing OR trajectory) (force)`, num=50 | US 7,508,382 B2 (PAT-11); US 9,886,088 B2; JP 6651297 B2 |
| G8 | 2026-09-26 | `assignee=Anoto`, `q=(pen) (camera OR "image sensor") (position-coding OR "position code") (paper)`, num=30, sort=old | US 6,985,643 B1 (PAT-16) |
| G9 | 2026-09-26 | `assignee=Neolab`, `q=(pen)`, num=40 | WO 2020/091323 A1 (PAT-15); US 11,567,590 B2; WO 2020/105880 A1 |
| G10 | 2026-09-26 | `assignee=Nuwa`, `q=(pen)`, num=40 | WO 2024/072219 A1 (PAT-14); NL 2034260 B1 |
| G11 | 2026-09-26 | `assignee=Stabilo`, `q=(handwriting) (sensor OR accelerometer OR inertial)`, num=40 | EP 3143479 B1 (PAT-17); WO 2014/006198 A1 (PAT-18); DE 10 2014 106 838 B4 |
| G12 | 2026-09-26 | `q=(pen OR "writing instrument" OR stylus) (refill OR cartridge OR nib) (pivot*) (flexure OR "flexible hinge" OR gimbal) (actuator OR coil OR piezoelectric) (tremor OR stabiliz* OR guid*)`, num=40 | Nothing relevant (feature j) |
| G13 | 2026-09-26 | `q=(pen OR "writing instrument") (inertial OR IMU OR accelerometer) (handwriting recognition) (paper) (ink)`, num=40 | CN 115050031 A (PAT-19); US 2005/0243656 A1 |
| G14 | 2026-09-26 | `q=(pen OR "writing instrument" OR "writing implement") (nib OR "writing tip" OR refill) (actuator) ("relative to the housing" OR "relative to the barrel" OR "relative to the body") (handwriting) (correct* OR assist* OR guid* OR tremor)`, num=50 | Only US 12,122,180 B2 relevant |
| G15 | 2026-09-26 | `q=("nib manipulator" OR ((pen OR "writing instrument") ("delta robot" OR "parallel mechanism") (nib OR "pen tip")))`, num=40 | EP 4250070 A1; CN 109278447 A (delta calligraphy robot, not handheld) |
| G16 | 2026-09-26 | `q=(震颤 OR 手抖 OR 防抖) (笔芯 OR 笔尖) (电机 OR 驱动器 OR 压电 OR 陀螺仪)`, num=50 | Irrelevant |
| G17 | 2026-09-26 | `q=(tremor OR "hand shake" OR "hand shaking") (pen OR "writing instrument") (gyroscope OR IMU OR "inertial measurement") (motor OR actuator) (compensat* OR suppress* OR counteract*)`, num=50 | US 6,234,045 B1 (Draper, "Active tremor control"; not reviewed) |
| G18 | 2026-09-26 | `q=TI=("anti-shake pen" OR "anti-tremor pen" OR "anti-shaking pen" OR "tremor pen" OR "stabilizing pen" OR "anti-shake writing" OR "anti-tremor")`, num=50 | **CN 121979402 A (PAT-03)**; US 2021/0007519 A1 family; JP H07-64694 A |
| G19 | 2026-09-26 | `assignee=Carnegie Mellon`, `q=(tremor) (handheld OR hand-held)`, num=30 | **HTTP 503, not executed** |
| G20 | 2026-09-26 | `assignee=BIC`, `q=("writing instrument") (actuator OR motor OR haptic) (nib OR tip)`, after=priority:20180101, num=40 | **HTTP 503, not executed** |
| G21 | 2026-09-26 | `q=(tremor) (pen OR writing OR handwriting)`, cpc=A61F4/00, num=40 | **HTTP 503**; superseded by G24 |
| G22 | 2026-09-27 | `q=(actuator OR motor OR piezoelectric) (tremor OR guid* OR correct* OR stabiliz*) (nib OR tip OR refill)`, cpc=B43K29/08, num=50 | US 2025/0006076 A1 (PAT-25); US 2018/0158348 A1 (PAT-22); US 2023/0364936 A1 (BIC, screened out); KR 2021-0025998 A; EP 2004423 B1; EP 2182423 A2 |
| G23 | 2026-09-27 | `q=(tremor) (actuator OR motor OR piezoelectric OR "voice coil")`, cpc=G06F3/03545, num=50 | Stylus haptics (Apple "Pencil haptics" US 11,221,677 B2; TDK); nothing new on nib actuation |
| G24 | 2026-09-27 | `q=(tremor) (pen OR writing OR handwriting OR stylus) (actuator OR motor)`, cpc=A61F4/00, num=50 | **US 11,944,216 B2 (PAT-12)**; US 11,883,342 B2; US 10,758,388 B2; EP 3258829 B1; EP 3846973 A1 |

CPC A61B 5/11 was not queried separately. It mainly covers tremor measurement; see §11.

### 3.3 Direct document retrievals

| Date | Source (exact URL) | Used for |
|---|---|---|
| 2026-09-26 | https://patents.google.com/patent/US12026327B2/en | PAT-01 bibliographic data and status |
| 2026-09-26 | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12026327 (21 pp., OCR) | PAT-01 claims 1-20 and description |
| 2026-09-26 | https://patents.google.com/patent/EP4250070A1/en | PAT-02 displayed status |
| 2026-09-26 | https://data.epo.org/publication-server/rest/v1.0/publication-dates/20230927/patents/EP4250070NWA1/document.pdf (26 pp.) | PAT-02 claims and search report |
| 2026-09-26 | https://register.epo.org/application?number=EP22164386&lng=en&tab=main | **HTTP 403**, status not verified |
| 2026-09-26 | https://patents.google.com/patent/CN121979402A/en (5 reads) | PAT-03 existence, claims 1-10 (machine translation) |
| 2026-09-26 | https://patents.google.com/patent/{US10101824B2, US8308664B2, US9925034B2, US10369045B2, US10078320B2, US9943430B2, US20210007519A1, US12122180B2, US7265750B2, US20250162342A1, US6985643B1, US20200202741A1, WO2024072219A1, WO2020091323A1, CN115050031A, EP3143479B1, WO2014006198A1, CN109263362A, US7508382B2}/en | Bibliographic data, displayed status, claims (automated extraction) |
| 2026-09-26 | image-ppubs downloadPdf/10101824, /11120704, /4211012, /20150148948 (OCR) | Verbatim claims for PAT-04, 05, 24, 23 |
| 2026-09-27 | https://patents.google.com/patent/{US11120704B2, US20150148948A1, US4211012A, US20250006076A1, US20180158348A1}/en | Displayed statuses |
| 2026-09-27 | image-ppubs downloadPdf/20180158348, /20250006076, /20230364936, /11944216, /9943430, /9925034, /8308664, /10078320 (OCR) | Claims for PAT-22, 25, 12; checks for PAT-08, 07, 06; correction of PAT-10; screening of US 2023/0364936 A1 |
| 2026-09-27 | image-ppubs downloadPdf/10369045, /7508382, /20250162342, /6985643, /20210007519, /12122180 (OCR) | Claim checks: corrections of PAT-09, 13 and 16; confirmation of PAT-11, 20 and 21 (claim 1) |
| 2026-09-27 | https://data.epo.org/publication-server/rest/v1.0/publication-dates/20190724/patents/EP3143479NWB1/document.pdf | PAT-17 claim 1 check (EP B1 text) |
| 2026-09-27 | https://patents.google.com/patent/US11944216B2/en | **HTTP 503**, status not displayed |

### 3.4 Blocked or failed access (2026-09-26)

- `https://html.duckduckgo.com/html/?q=tremor+pen+patent+actuator` returned a captcha.
- `https://www.bing.com/search?q=tremor+pen+patent+actuator+site%3Apatents.google.com` returned irrelevant results (operators ignored).
- `POST https://ppubs.uspto.gov/dirsearch-public/users/me/session` returned 404.
- `https://www.freepatentsonline.com/12026327.html` failed with a TLS error.
- Direct curl to patents.google.com was blocked ("Sorry" page).
- Google Patents returned HTTP 503 intermittently during 2026-09-26/27. First attempts at US 2015/0148948 A1, US 4,211,012 A and US 11,120,704 B2 failed; later retries succeeded.

---

## 4. Records (bibliographic data and displayed status)

"GP" means as displayed on Google Patents on the date shown. None of these statuses were verified in an official register.

| ID | Publication | Title | Assignee / applicant | Priority | Published / granted | Family (as displayed or read) | Jur. | Displayed status | Claimed subject matter (one line) |
|---|---|---|---|---|---|---|---|---|---|
| PAT-01 | US 12,026,327 B2 | Writing instrument | BIC Violex Single Member S.A. | 2022-03-25 (EP 22164386.9) | 2024-07-02 | US 2023/0305647 A1; EP 4250070 A1 | US | Active; exp. 2043-03-21 (GP 09-26) | Pen with electronically actuated nib manipulator (XP/YP + ZP), IMU and ECU that scribes predefined characters from segment formation commands; speech/image method; system |
| PAT-02 | EP 4 250 070 A1 | Writing instrument | BIC Violex Single Member S.A. | 2022-03-25 | 2023-09-27 | US 12,026,327 B2 | EP | Withdrawn (GP 09-26; Register 403) | Same as PAT-01 (15 claims) |
| PAT-03 | CN 121979402 A | Smart anti-shake pen and writing method based on vector force guidance | Shaoyang Industrial Vocational and Technical College | 2026-02-24 | 2026-05-05 | none shown | CN | Pending (GP 09-26) | Anti-shake pen: IMU + eccentric-mass counter-moment tremor suppression; orthogonal linear micro-drivers push a refill-sleeve guide ring along preset strokes; nib pressure sensor + nib camera; guided-stroke method |
| PAT-04 | US 10,101,824 B2 | Apparatus, system, and method to stabilize penmanship and reduce tremor | Verily Life Sciences LLC | 2016-07-27 | 2018-10-16 | US 2018/0032159 A1; WO 2018/022356 A1 | US | Active; exp. 2036-10-13 (GP 09-26) | Portable stage whose actuated pen carriage redraws the user's (tremor-filtered) handwriting while measuring and adjusting pen pressure; stylus + filter system; method |
| PAT-05 | US 11,120,704 B2 | Writing implement | Xiamen Zhi Hui Quan Technology Co., Ltd. | 2017-06-22 (CN 201710479177.8) | 2021-09-14 | US 2020/0202741 A1; WO 2018/233532 A1; CN 109118875 A | US | Expired - Fee Related (GP 09-27) | Pen whose guiding element (actuators; inner tube tilted or displaced within outer tube) applies guiding force toward stored copybook characters based on motion sensing; nib pressure sensor; gyroscope |
| PAT-06 | US 8,308,664 B2 | Tremor stabilizing system for handheld devices | Regents of the University of Michigan | 2009-03-03 | 2012-11-13 | US 2010/0228362 A1 | US | Expired - Fee Related (GP 09-26) | Handheld device moving a gripping element on two orthogonal axes with SMA/smart-material actuators to counteract sensed base motion |
| PAT-07 | US 9,925,034 B2 | Stabilizing unintentional muscle movements | Verily Life Sciences LLC (now also Google LLC) | 2011-09-30 | 2018-03-27 | US 2013/0297022 A1; WO 2015/003133 A1 | US | Active; exp. 2031-11-13 (GP 09-26) | Implement moved relative to handheld base by internal actuator, commanded by an external processor using a remote non-contact position sensor |
| PAT-08 | US 9,943,430 B2 | Handheld tool for leveling uncoordinated motion | Verily Life Sciences LLC (now also Google LLC) | 2015-03-25 | 2018-04-17 | US 2017/0100272 A1; same-title US 10,532,465 | US | Active; exp. 2035-03-25 (GP 09-26) | IMU on attachment arm + 2-DOF actuators (one in handle, one outside) + auto-levelling control; dependent claims: actuator position sensors, tremor stabilisation, handle IMU for tremor |
| PAT-09 | US 10,369,045 B2 | Micromanipulation systems and methods | Carnegie Mellon University; Johns Hopkins University | 2014-07-29 | 2019-08-06 | US 2016/0030240 A1 | US | Active; exp. 2036-02-08 (GP 09-26) | Micromanipulator with tool-shaft force sensing (actuation-force compensated) and a vibrator imposing vibration along the sensed force direction; dependent claims add handpiece tremor cancellation |
| PAT-10 | US 10,078,320 B2 | Automatically guided tools | Shaper Tools, Inc. | 2011-05-19 | 2018-09-18 | US 2015/0277421 A1; US 10,788,804 B2; US 10,067,495 B2; US 10,795,333 B2; US 11,467,554 B2; US 11,815,873 B2 | US | Active; exp. 2032-05-21 (GP 09-26) | Hand-advanced rig whose motorised stage keeps the working member on a design path registered to a stored surface map (surface sensor, display screen), correcting as the rig is advanced |
| PAT-11 | US 7,508,382 B2 | Force-feedback stylus and applications to freeform ink | Fuji Xerox (now FUJIFILM Business Innovation) | 2004-04-28 | 2009-03-24 | none shown | US | Expired - Fee Related (GP 09-26) | Stylus with tip electromagnet over a magnetic surface; field varies with location and projected objects for haptic guidance |
| PAT-12 | US 11,944,216 B2 | System and method for stabilizing unintentional muscle movements | Verily Life Sciences LLC | 2011-09-30 (chain) | 2024-04-02 | US 2020/0015610 A1; continuation of US 16/124,898 (US 10,455,963), continuation of US 13/250,000 filed 2011-09-30 (US 10,368,669) | US | **Not displayed (HTTP 503, 09-27)**; front page: terminal disclaimer, 1226 days PTA | Housing with internal mechanism moving an attachment arm relative to it, motion sensor(s), on-board control to stabilise tremor; dependent claims: inertial sensor on arm, magnetic arm-position sensor |
| PAT-13 | US 2025/0162342 A1 | Digital pen with enhanced educational and therapeutic feedback | Neubauer, L. M. (individual) | 2014-05-21 | 2025-05-22 | chain incl. US 2021/0291579 A1 | US | Pending (GP 09-26) | System/method monitoring therapy efficacy: characters recognised in writing captured by a sensor pen are scored against models; performance and efficacy metrics tracked over time |
| PAT-14 | WO 2024/072219 A1 | Handwriting detecting pen | Nuwa Pen B.V. | 2022-09-29 | 2024-04-04 | NL 2034260 B1 | WO | Ceased (international phase) (GP 09-26) | Pen with camera system of at least 90 deg field of view recording the writing surface |
| PAT-15 | WO 2020/091323 A1 | Method for correcting handwriting data of electronic pen and apparatus therefor | NeoLAB Convergence Inc. | 2018-11-02 | 2020-05-07 | national phases not checked | WO | Ceased (GP 09-26) | Laser-speckle imaging of pen-tip motion corrected by sensed pen tilt, transmitted when pen pressure is detected |
| PAT-16 | US 6,985,643 B1 | Device and method for recording hand-written information | Anoto Group AB (now Anoto IP LIC HB) | 1998-04-30 | 2006-01-10 | same-title WO 99/60467 A1 (likely) | US | Expired - Lifetime (GP 09-26) | Recording handwriting by imaging overlapping surface patches and computing relative shifts |
| PAT-17 | EP 3 143 479 B1 | Drift compensation with parallel minimization | STABILO International GmbH | 2014-05-15 (DE 10 2014 106 837) | 2019-07-24 | WO 2015/173401; CN 106462268 B (likely) | EP | Active (GP 09-26) | IMU pen position evaluation with drift compensation by parallel angle-hypothesis minimisation |
| PAT-18 | WO 2014/006198 A1 | Digital writing learning aid | STABILO International GmbH | 2012-07-05 | 2014-01-09 | DE 10 2012 211 752 B4; DE 20 2012 102 492 U1 | WO | Ceased (GP 09-26) | Device comparing input characters with task characters incl. pressure and acceleration criteria |
| PAT-19 | CN 115050031 A | Handwriting feedback | Societe BIC | 2021-03-09 | 2022-09-13 | EP 4057182 A1; US 11,675,495 B2; JP 2022-138131 A | CN | Pending (GP 09-26) | Capture handwriting, compare attributes with predefined text features, modify digital text, give feedback |
| PAT-20 | US 2021/0007519 A1 | Anti-tremor tool, anti-tremor device thereof, and auxiliary holding device | Icaninnotech Co., Ltd. | 2019-03-29 | 2021-01-14 | US 12,089,757 B2; US 2024/0398142 A1; GB 202115585 D0 | US | Granted as US 12,089,757 B2; exp. 2040-03-27 (GP 09-26) | Holder with carrying and support portions for a tool unit (pens mentioned); inertial/elastic tremor damping |
| PAT-21 | US 12,122,180 B2 | Writing system having magnetic writing tool and magnetic support surface therefor | SteadyScrib LLC | 2022-08-03 | 2024-10-22 | US 2024/0042791 A1; WO 2024/030893 A2 | US | Active; exp. 2043-08-01 (GP 09-26) | Pen with magnetic core near the tip plus a magnetic support surface (passive tremor aid) |
| PAT-22 | US 2018/0158348 A1 | Instructive writing instrument | Google LLC | 2016-12-06 (prov.) | 2018-06-07 | none shown | US | Abandoned (GP 09-27) | Visual cues directing the user's pen movement toward a model object, updated from camera-derived pen position |
| PAT-23 | US 2015/0148948 A1 | Mixing machine motion in a handheld marking device | Singh, D.; Isner, M. | 2013-11-23 | 2015-05-28 | none shown | US | Abandoned (GP 09-27) | Handheld marking device combining hand motion with motor-driven positioning of the marking region (presets, text, "stabilization", camera feedback) |
| PAT-24 | US 4,211,012 A | Electric-signal controlled hand-held printer | Bell Telephone Laboratories (now shown as AT&T) | 1978-03-23 | 1980-07-08 | none | US | Expired - Lifetime (GP 09-27) | Hand-held printer: electromagnetically driven marking tip traces a recurrent pattern and is lifted per signals to form characters as the device is swept |
| PAT-25 | US 2025/0006076 A1 | Haptic stylus to guide a user to handwrite letters | International Business Machines Corp. | 2023-06-27 | 2025-01-02 | none shown | US | Pending (GP 09-27) | Haptic stylus generating vibration commands that guide the user to form a selected letter; camera and ML verification |

---

## 5. Task 1: US 12,026,327 B2 "Writing instrument" (BIC)

### 5.1 Bibliographic data

- **Assignee and applicant:** BIC Violex Single Member S.A., Anoixi (GR).
- **Inventors:** Panagiotis Polygerinos; Nikolaos Chrysanthakopoulos.
- **Application:** US 18/187,156, filed 2023-03-21.
- **Priority:** EP 22164386.9, 2022-03-25.
- **Publications:** pre-grant US 2023/0305647 A1 (2023-09-28); grant US 12,026,327 B2 (2024-07-02).
- **Term:** patent term adjustment 0 days.
- **Classification:** CPC G06F 3/03546; B25J 9/0084; B25J 9/1679; B43K 29/08; G10L 15/22.
- **Scope:** 20 claims, 7 drawing sheets. Primary examiner Nicholas J. Lee.
- **Displayed status:** Active, anticipated expiration 2043-03-21 (GP 2026-09-26; not verified in USPTO Patent Center).
- **Family (as displayed):** US 2023/0305647 A1, US 12,026,327 B2 and EP 4250070 A1. No other members are shown on Google Patents; the INPADOC/Espacenet family and any continuations were not checked.
- **References cited on the face (selection; the foreign-document list is partly illegible in OCR):** US 4,211,012 A; US 5,501,535 A; US 5,861,877 A; US 7,627,703 B2; US 10,254,856 B2; US 2015/0148948 A1; US 2020/0202741 A1; CN 204172543 U; CN 104385808 A; CN 109263362 A; CN 110970033; JP 2005-173807; JP 2006-211497 A; KR 2009-0005210 A; the EP search report; NPL Speech Pen (CHI 2006) and Pentelligence (2018).

### 5.2 Independent claims (verbatim)

Transcribed from OCR of the official USPTO image PDF, with obvious OCR artefacts corrected. Verify against a certified copy before relying on the wording.

> **1.** A writing instrument comprising:
> an elongate body portion enabling a user to grip the writing instrument, wherein the elongate body portion comprises a distal end (D) and a proximal end (P), the proximal end and the distal end defining a principal axis (A) of the writing instrument;
> an electronically actuated nib manipulator attached to the proximal end of the elongate body portion, wherein the nib manipulator further comprises an end portion comprising a nib, and the nib manipulator is configured to move the end portion within a spatial domain defined (i) along first (XP) and second (YP) axes of a plane that is substantially orthogonal to the principal axis (A), and (ii) along a third (ZP) axis that is an extension of the principal axis (A);
> an inertial measurement unit configured to measure at least a position of the principal axis (A) relative to a writing surface; and
> an electronic control unit operatively coupled to at least the inertial measurement unit and the nib manipulator;
> wherein the electronic control unit is configured to obtain one or more segment formation commands, and to receive the position of the principal axis (A) from the inertial measurement unit, and wherein the electronic control unit is configured to electronically actuate the nib manipulator so that the end portion moves within the spatial domain to scribe a predefined character defined by the one or more segment formation commands onto the writing surface.

> **15.** A computer-implemented method for generating one or more segment formation commands for causing a writing instrument to scribe a predefined character onto a writing surface, wherein the method comprises:
> obtaining an audio or graphical sample from a user;
> performing speech recognition on the audio sample, or image recognition on the graphical sample to convert the audio or graphical sample to one, or more, character identifiers;
> referencing one, or more, records of a predefined character store corresponding to the one, or more, character identifiers, wherein the predefined character store comprises a plurality of records indexed by one, or more, corresponding character identifiers, wherein each record comprises one or more segment formation commands configured to cause an electronically actuated nib manipulator of the writing instrument to form the predefined character; and
> providing the one or more segment formation commands to the writing instrument.

> **16.** A non-transitory computer program element comprising machine readable instructions which, when executed by a processor, causes the processor to perform the computer-implemented method of claim 15.
>
> **17.** A computer readable medium comprising the computer program element according to claim 16.

> **18.** A system comprising:
> a writing instrument;
> an external processing apparatus; and
> a wireless communications network configured to communicably couple the writing instrument and the external processing apparatus;
> wherein a wireless modem of the writing instrument is configured to transmit an audio sample obtained by a microphone of the writing instrument to the external processing apparatus via the wireless communications network;
> wherein the external processing apparatus is configured to perform speech recognition on the audio sample, thus converting the audio sample to one, or more, character identifiers;
> wherein the external processing apparatus is configured to reference one, or more, records of a predefined character store corresponding to the one, or more, character identifiers, wherein the predefined character store comprises a plurality of records indexed by one, or more, corresponding character identifiers, wherein each record comprises one or more segment formation commands configured to cause an electronically actuated nib manipulator of the writing instrument to form a predefined character; and
> wherein the external processing apparatus is configured to transmit the one or more segment formation commands to the writing instrument.

Claims 16 and 17 are program-element and medium claims that refer to claim 15. Claim 18 is independent, and claim 19 adds the full claim-1 pen to it.

### 5.3 Dependent-claim features

| Claim | Depends on | Added feature |
|---|---|---|
| 2 | 1 | Nib manipulator comprises a robotic mechanism with a plurality of arms that moves the end portion within the spatial domain |
| 3 | 2 | Each arm's proximal end is coupled to the end portion; the distal end of each arm is coupled to a corresponding actuator |
| 4 | 2 | Robotic mechanism is a delta mechanism |
| 5 | 2 | Mechanism prevents rotation of the end portion substantially about the principal axis |
| 6 | 2 | Displacement detector senses the pen's displacement velocity across the surface; the ECU also actuates based on the displacement rate |
| 7 | 6 | Detector at the proximal end of a protrusion from the body: a trackball, a tracking wheel with position encoder, or an optical sensor configured to contact the writing surface |
| 8 | 1 | Contact detector senses nib-surface contact; the ECU begins scribing a predetermined character on receiving the contact signal |
| 9 | 1 | Microphone + audio processing unit + wireless modem; audio pre-processing |
| 10 | 9 | Modem sends audio to an external apparatus and receives segment formation commands in response |
| 11 | 10 | ECU obtains the commands from the modem and scribes the characters defined in the audio sample |
| 12 | 9 | Speech recognition unit + predefined character store (records = segment formation commands + character identifiers); microphone captures a writing instruction |
| 13 | 12 | Speech recognition converts audio to a character identifier; the ECU fetches the commands from the store and scribes |
| 14 | 1 | Ink supply with flexible supply tube to the nib, or a pencil/crayon attachment |
| 19 | 18 | System pen has all claim-1 features (body, XP/YP/ZP nib manipulator, IMU, ECU) |
| 20 | 19 | Modem round-trip of audio and commands; ECU scribes the characters defined in the audio |

### 5.4 Described embodiments

The description never uses the word "tremor"; this was checked by full-text search of the OCR text and of the EP A1 text layer.

- **Purpose.** Automatic transcription of equations and pictorial symbols onto paper by a pen-sized "miniature automatic mechanism", as an aid for students and for partially sighted or disabled users. It is not a tremor device.
- **Form factor.**
  - Body length 50-200 mm (140 mm example); maximum diameter 6-25 mm (15 mm example).
  - Body in polystyrene or polypropylene, with a rubber or foam grip that helps the user resist the manipulator's reaction forces.
  - Ink is fed from a reservoir in the body through a flexible tube routed through the manipulator.
- **Actuators and mechanism.**
  - Nib manipulator 14 is a delta (parallel) robot with three arms 32a-c in carbon fibre or Kevlar. Its joints 19a-e are passive flexures of Kapton film, giving low inertia so the nib can move "at speeds matching, or exceeding, a human writer".
  - Arm actuators 36a-c can be:
    - linear micro-actuators ("smart actuators" with integrated drive and controller) acting through rigid rods, push-pull cables, polymer cords or tensioned wires anchored with epoxy or articulated sockets;
    - three motors winding wire linkages; or
    - piezoelectric strips laminated at the flexible joints.
  - Actuators may give digital or analogue position feedback, or have end-of-limit switches. The ECU may use this feedback in the delta-robot control laws for 3 DOF (XP, YP, ZP).
  - ZP motion is used for pen-down/pen-up (for example placing a dot).
- **Sensors.**
  - An IMU of MEMS accelerometers and gyroscopes (one or more modules) measures roll, pitch, yaw and X/Y/Z displacement of the principal axis.
  - A displacement detector (tracking wheel with encoder on a protrusion that also supports the pen, trackball, or optical/acoustic displacement sensor) synchronises character formation with the user's sweep along the line.
  - A contact detector (microswitch, compressible seat with proximity detector, or sensing actuator resistance "electromagnetic monitoring of an actuator").
  - An electret or MEMS microphone.
- **Control.**
  - A segment formation command is either a 2-D spatial definition of a segment (2-D splines, a mathematical function or a bitmap) or direct actuation signals.
  - The ECU computes a time-dependent geometric transformation between the 2-D segment definition and nib position, using IMU orientation. When the pen axis is tilted (80 to 45 deg to the paper), it adds ZP and differential arm extension so the end portion stays correctly oriented.
- **Character formation.**
  - Characters are decomposed into segments (lines, points, arcs); for example "A" is two angled segments and a horizontal one.
  - Commands come from on-pen or external speech recognition, image recognition of a photo (smartphone camera), text or LaTeX input, and a predefined character store.
  - Communication is by Bluetooth/BLE and other wireless links.

### 5.5 Observations for the programme (technical, not legal)

- Claim 1 combines an XP/YP **and** ZP manipulator, an IMU measuring axis position relative to the surface, and an ECU that scribes a predefined character from commands.
  - Tremor cancellation with no character target does not obviously involve "segment formation commands".
  - The guided-letter mode is closer to the claim.
  - See questions Q1-Q5 in §9.
- The EPO search for the EP twin rated **US 2020/0202741 A1 (PAT-05 family)** and **US 4,211,012 A (PAT-24)** as category **X** against all 15 EP claims. This is the most useful context for the strength of the claim-1 concept, but only an attorney can assess validity.

---

## 6. Task 2: EP 4 250 070 A1

- **Displayed status:** **Withdrawn** (Google Patents, 2026-09-26). The EPO Register (`register.epo.org`) returned HTTP 403, so the status is **not verified**.
- **Bibliographic data:**
  - Application EP 22164386.9, filed 2022-03-25; no earlier priority.
  - Published 2023-09-27 (Bulletin 2023/39).
  - Applicant BIC Violex Single Member S.A.; inventors as PAT-01; representative Peterreins Schley (Munich).
  - All EPC states designated, plus extension states BA and ME and validation states KH, MA, MD and TN.
  - IPC G06F 3/0354, B41J 3/36, B41J 3/44, B41J 3/46, G06F 1/16, B43K 8/22, B43K 29/08. CPC G06F 3/03545, B43K 29/00, B43K 29/08, B43L 13/028.
- **Claims:** 15 as published (full text read from the EPO A1).
  - Claim 1 is word-for-word the same as US claim 1, with reference signs.
  - Claim 2 merges US claims 2-3 (arms; distal ends coupled to actuators). Claim 3 is the delta mechanism; claim 4 anti-rotation (depends on 2 or 3).
  - Claim 5 is the displacement detector; claim 6 the protrusion with trackball, encoder tracking wheel or surface-contacting optical sensor.
  - Claim 7 is the contact detector.
  - Claims 8-10 cover the microphone, modem and speech recognition (claim 10 merges US claims 12-13).
  - Claim 11 is the ink tube or pencil/crayon.
  - Claim 12 is the method, for a pen "according to one of claims 1 to 11".
  - Claim 13 is the system comprising the pen of claim 9. Claims 14 and 15 are the program element and medium.
- **European search report** (Munich, completed 2022-09-01, examiner Oliver Tonet):
  - **X** US 2020/0202741 A1 (Zhong) against claims 1-15.
  - **X** US 4,211,012 A (Alles et al.) against claims 1-15.
  - **A** US 2015/0148948 A1 (Singh et al.).
  - **A** US 5,501,535 A (Hastings et al.).
  - **A** US 5,861,877 A (Kagayama et al.).
  - The category letters were read by OCR of the image page, and the claim ranges for the A documents are partly illegible.
- **Implication (technical).** If the displayed withdrawal is confirmed, BIC holds no granted European patent from this family. The A1 remains prior art from 2023-09-27.

---

## 7. Task 3: CN 121979402 A (verified to exist)

- **Found:** https://patents.google.com/patent/CN121979402A/en (read 2026-09-26). The reported details (published 2026-05-05; "smart anti-shake pen and writing method based on vector force guidance") **match** what is displayed.
- **Bibliographic data:**
  - 基于矢量力引导的智能防抖笔及书写方法 (machine translation: "A smart anti-shake pen and writing method based on vector force guidance").
  - Application CN 202610221299.6, filed and priority 2026-02-24; published 2026-05-05.
  - Applicant Shaoyang Industrial Vocational and Technical College.
  - Inventors Liu Pan, Liu Fei, Li Bing, Lyu Fa, Zhou Yuan, Ouyang Jianfeng, Liu Yuanzhi, Mao Yi, Zhong Meixing and Cao Xuan.
  - Displayed status: **Pending**. No family members shown.
- **Claims** (10, from the Google machine translation, which is garbled in places; for example the pen is rendered "anti-curlicue"):
  - **Claim 1 (device).** A pen shell with a hollow cavity, grip portion and nib portion, and an inner core support.
    - A writing refill assembly (refill + refill sleeve) slidable along the shell's central axis, with the tip passing through the nib opening.
    - A tremor suppression module on the core support that "counteract[s] vibration transmitted to the pen body shell by unconscious vibration of hands ... through generating compensation moment". It comprises an IMU on the core support's base surface monitoring angular velocity and linear acceleration, and "reverse micro vibration assemblies", each "a micro vibration motor and an eccentric mass block fixedly connected to an output shaft of the motor".
    - A vector-force stroke auxiliary driving module, a bidirectional interaction module, and a main controller that coordinates tremor suppression and guidance "based on a control algorithm".
  - **Claim 2:** the core support is moulded integrally with the shell.
  - **Claim 3:** the vector-force module is motion-coupled to the refill sleeve "for applying a controllable physical guidance force to the writing cartridge assembly in a direction in a two-dimensional writing plane according to an external command".
  - **Claim 4:** the interaction module senses nib writing state in real time and communicates wirelessly with an external terminal.
  - **Claim 5:** the controller processes high-frequency IMU data and computes "a compensation moment vector opposite to the current tremble trend in real time through a built-in inverse dynamic model algorithm". It drives the vibration motors "at a specific rotating speed and a specific phase" so the eccentric masses produce a moment opposite to and dynamically matching the hand-tremor moment.
  - **Claim 6 (from 3).** A driver frame on the core support.
    - A linear-driver array of **at least two linear micro-drives with mutually orthogonal drive directions**, defining an X-Y frame perpendicular to the pen axis.
    - A movable guide mechanism connected to the refill sleeve that translates in that plane, with transmission structures between drivers and guide.
    - The controller decomposes a stroke vector command from the external terminal into X and Y components and drives each axis for "preset displacement or thrust". The result is a resultant force applied to the refill "to guide the pen core to move along a preset stroke track".
  - **Claim 7:** the guide is a ring fixed round the refill sleeve, running in a guide rail on the driver frame. It is **restrained to translate only in the 2-D plane**, "so that ... the inclination of the pen core is prevented".
  - **Claim 8:** the linear micro-actuators are **voice coil motors or piezoelectric ceramic actuators**, with push rods hinged to the actuator outputs.
  - **Claim 9 (from 4):**
    - A nib state sensing device: an **axial nib pressure sensor** between the refill tail and the sleeve's bearing surface.
    - A **miniature optical tracking device**: image sensor and wide-angle lens on the inner wall of the nib portion, plus an adjacent illumination source at an inclined angle.
    - A Bluetooth or Wi-Fi unit.
    - The controller or a coprocessor captures high-speed frames and uses "a digital image correlation algorithm or a characteristic point tracking algorithm" to compute the pen's instantaneous motion vector, then the nib trajectory from the pen geometry.
  - **Claim 10 (method):**
    - A: initialise and link to a terminal, which decomposes a target font into an ordered stroke sequence (start point, direction vector, length, recommended speed).
    - B: issue a stroke vector instruction.
    - C1: run a **high-priority** anti-tremor thread. C2: run a **standard-priority** guidance thread applying the guidance force.
    - D: stream the actual trajectory and pressure back.
    - E: the terminal compares them with the target stroke (graphic similarity). On a completion threshold or time limit it moves to the next stroke, until the character is done.
- **Mechanism summary.**
  - Tremor is countered by **eccentric-mass counter-moments on the whole pen body**, not by nib displacement.
  - Guidance is a **2-axis translation of the refill** by orthogonal voice-coil or piezo drivers, constrained against tilt.
  - Sensing is IMU, nib pressure, and a nib-mounted camera with image correlation.
- **Numbers.** IMU sampled at "hundreds of hertz" (description, per translation). No force, stroke, bandwidth or mass values were found in the text read.
- **Caveats.** The claim wording must be checked against the Chinese original. This is an unexamined application whose claims may change. Foreign or PCT filings claiming its priority remain possible until **2027-02-24**. Its prior-art effect against our filings depends on our own filing dates and the jurisdiction (attorney question Q8).

---

## 8. Feature-to-claims map

"Appears to recite" means a claim of the record, read technically, contains a limitation resembling the feature. Claim numbers are given in brackets.
"Related / analogous" means the claim is near the feature but differs in an obvious respect (different object, 1-axis, description only, and so on).
Status tags: [live] means active or pending as displayed; [dead] means expired, withdrawn or abandoned as displayed; [?] means unknown.
**Every row: needs professional review.**

| Feature | Records whose claims appear to recite it | Related / analogous only | Notes |
|---|---|---|---|
| **a** 2-axis actuated nib relative to barrel | PAT-01 [live] (1: XP/YP + ZP; 2-5; 19); PAT-02 [dead] (1-4); PAT-03 [live] (3, 6-8: orthogonal X-Y drivers move refill-sleeve guide ring); PAT-05 [dead] (9-12: inner tube tilted/displaced within outer tube by radial actuators); PAT-23 [dead] (1, 12-13: motor-driven positioning of marking region, pen nozzle) | PAT-12 [?] (1, 13, 18: arm moved relative to housing, not a pen); PAT-06 [dead] (1: two orthogonal SMA axes, gripping element); PAT-07 [live] (1); PAT-08 [live] (1-3: 2 rotational DOF); PAT-10 [live] (1, 19: stage keeps working member on a path as the rig is advanced); PAT-04 [live] (1, 5-6, 15: carriage in a separate stage); PAT-24 [dead] (1-2: 1-axis/circular tip drive); PAT-09 [live] (3, 18: dependent handpiece tremor cancellation) | Closest live pen claims: PAT-01 (needs ZP and character scribing) and PAT-03 (needs eccentric-mass tremor module per claim 1). Broadest live tremor-tool claim: PAT-12. **Needs professional review** |
| **b** IMU-based tremor estimation | PAT-03 [live] (1, 5); PAT-08 [live] (13: handle IMU measures tremor; 9); PAT-12 [?] (9, 16, 20: inertial sensor on the moving arm; 1, 13 tremor stabilisation) | PAT-01 (1: IMU measures axis position vs surface, not tremor); PAT-04 (2, 9, 14, 19-22: tremor filtering of stylus data, sensor unspecified); PAT-05 (18: gyroscope/gravity sensor for pencraft); PAT-06 (1: generic sensor); PAT-15 (1: sensed tilt); PAT-17 (1: IMU drift compensation); PAT-23 (22, 29, 35); PAT-09 (3, 18: tremor cancellation, sensing unspecified) | IMU-based tremor sensing on handheld stabilisers is claimed in the Verily family (PAT-08, PAT-12). **Needs professional review** |
| **c** Optical local motion sensing near the tip | PAT-03 [live] (9: nib camera, image correlation to motion vector to nib trajectory); PAT-01 [live] (7: optical sensor contacting surface on a protrusion); PAT-02 [dead] (6); PAT-15 [dead WO; national phases ?] (1: laser speckle); PAT-16 [dead] (1, 21); PAT-14 [dead WO; NL ?] (1: camera with FOV >= 90 deg); PAT-10 [live] (1, 7-8: surface sensor, e.g. camera, locates the working member on a stored map; 2: map built from images); PAT-23 [dead] (41-42) | PAT-22 [dead] (1: image of writing surface gives pen position); PAT-25 [live] (5, 9: camera page layout and letter capture); PAT-04 (8: optical check of drawn line); PAT-13 (1: generic capture sensor on the pen) | For control (not only capture), PAT-03 cl. 9 and PAT-01 cl. 6-7 are the closest. **Needs professional review** |
| **d** Stage position sensing | PAT-08 [live] (6: position sensors on actuator outputs); PAT-12 [?] (6-7, 14-15, 20: contactless magnetic sensor of arm position relative to housing) | PAT-24 [dead] (3: angular indexing signals); PAT-09 (4: position detection of the micromanipulator); description only: PAT-01 (actuator position feedback), PAT-07 (hall-effect), PAT-09 (magnetic slider sensors), PAT-10 (motor shaft angles) | Our hall/magnetic stage sensing resembles PAT-12 cl. 14-15. **Needs professional review** |
| **e** Contact force sensing | PAT-04 [live] (1, 9, 14: measure and adjust pen pressure); PAT-03 [live] (9: axial nib pressure sensor); PAT-05 [dead] (17: nib pressure/deformation sensor); PAT-09 [live] (1, 17: shaft force sensing with actuation-force compensation, but combined with vibrating the shaft along the force direction) | PAT-01 (8: binary contact detector); PAT-02 (7); PAT-15 (1: pressure gates output); PAT-18 (1: generation pressure criterion); PAT-22 (4-5: tip contact) | PAT-04's "adjusting the pressure applied by the actuator system" is a distinct step. **Needs professional review** |
| **f** Predictive cancellation | None clearly found | PAT-03 (5: inverse-dynamics compensation "opposite to the current tremble trend in real time"; whether predictive is unclear); PAT-04 (19, 22: adaptive, learned user-specific tremor parameters) | Gap in this sample; see Micron literature (not claimed in PAT-09). **Needs professional review** |
| **g** Guided letter formation / predefined characters | PAT-01 [live] (1, 12-13, 15, 18: predefined characters, autonomous scribing); PAT-02 [dead] (1, 10, 12-13); PAT-03 [live] (6, 10: preset stroke track, target font); PAT-25 [live] (1, 5, 8, 11, 16: vibration guidance to a selected letter); PAT-05 [dead] (1-3: guiding force toward copybook characters); PAT-23 [dead] (2, 15, 20, 49); PAT-24 [dead] (1-2: characters from signals); PAT-22 [dead] (1: guidance toward a model object) | PAT-18 (1: comparison with task characters, no actuation); PAT-13 (1, 10: characters scored against models, no guidance); PAT-10 (1, 19: design registered to the surface map defines the path); PAT-11 (1: displayed objects); PAT-04 (1: redraws the user's own characters) | Crowded area. Live claims: PAT-01 (actuated, autonomous), PAT-03 (actuated guidance), PAT-25 (vibrotactile guidance). **Needs professional review** |
| **h** Confidence-based authority limiting | None found | PAT-10 (11: display of the working member's range of movement; description: notification and wait when out of range); PAT-09 (7-8: automatic position holding after detected puncture); PAT-03 (10E: completion threshold, not authority) | Possible novelty opportunity, subject to a professional search including non-patent literature. **Needs professional review** |
| **i** Capture of corrected ink trajectory | PAT-03 [live] (10 D-E: actual guided trajectory and pressure returned and compared); PAT-15 [dead WO] (1: tilt-corrected tip motion transmitted); PAT-04 [live] (9, 14: filtered data drawn; the ink is the corrected trajectory) | PAT-14 (1-3: image and vector capture); PAT-16 (1); PAT-17 (1: drift-corrected position); PAT-13 (1, 10, 20: captured writing to recognition confidence to efficacy metrics); PAT-19 (1: modified digital text); PAT-23 (41); PAT-25 (4, 9) | Logging the post-correction nib path (actuator state + optical flow) is not claimed as such in this sample. **Needs professional review** |
| **j** Pivoting refill, front flexure, rear actuation | None found | PAT-05 (9-12: inner tube inclined or displaced relative to outer tube by actuators; pivot and flexure not specified as read); PAT-01 (2-3: arms with actuators at distal ends; Kapton flexures in description); PAT-24 (1: electromagnetically reciprocated member "pivoted" with spring limit) | Contrast: PAT-03 claim 7 restricts the refill to translation and prevents inclination. **Needs professional review** |

---

## 9. Claim-interpretation questions for a patent attorney

**US 12,026,327 B2 (PAT-01; BIC; active as displayed)**

- **Q1.** Claim 1 requires a nib manipulator "configured to move the end portion within a spatial domain defined (i) along first (XP) and second (YP) axes ... and (ii) along a third (ZP) axis".
  - Does a mechanism with only two actively controlled in-plane axes meet this? Consider Z provided passively by refill spring or compliance, or no Z control at all.
  - Does a pivoting refill whose tip moves on a spherical cap (small coupled Z change) meet it?
- **Q2.** "Obtain one or more segment formation commands" and "scribe a predefined character defined by the one or more segment formation commands".
  - Does user-led, bounded local guidance toward a selected letter template fall within "scribe"? In that mode the user supplies the gross motion and the pen corrects deviations within a few millimetres.
  - Does an on-device target trajectory generated from a font count as "obtaining" commands?
  - Is a pure tremor-cancellation mode (no character target) outside the claim?
- **Q3.** "An inertial measurement unit configured to measure at least a position of the principal axis (A) relative to a writing surface". The description equates position with orientation or pose.
  - Would an IMU used only for tremor or gravity estimation meet this limitation?
  - Would the ECU "receiv[ing] the position of the principal axis" be satisfied by any use of IMU attitude?
- **Q4.** Claims 6-7 (EP claims 5-6).
  - Is a non-contact optical-flow sensor in the nose cone a "displacement detector" on "a protrusion", or an "optical sensor configured to contact the writing surface"?
  - Does using optical flow in the actuation loop meet "actuate the nib manipulator based, additionally, on a displacement rate"?
- **Q5.** Are there pending continuations or divisionals claiming priority from US 18/187,156 or EP 22164386.9?
  - Please confirm in the EPO Register that EP 4250070 A1 is withdrawn, and whether any other national filings exist.
  - The search-report X citations (US 2020/0202741 A1; US 4,211,012 A) matter for any validity view of US claim 1. Is such a view warranted at this stage?

**US 10,101,824 B2 (PAT-04; Verily; active to 2036 as displayed)**

- **Q6.** Could a single handheld pen whose internal refill carriage is moved by actuators be a "portable writing apparatus" with "a writing instrument carriage shaped to removably hold a writing instrument and change between types of the writing instrument"?
- **Q7.** In claim 1, does "receiving input data describing a user's handwritten characters" and moving the carriage so it "recreates a shape of the user's handwritten characters" read on **real-time** correction? There the input is the user's ongoing motion sensed by the same pen.
  - Is a nib force sensor used only for monitoring and gating outside "adjusting the pressure applied by the actuator system"?
  - In method claim 14, is a pen barrel plus refill stage a "mechanical stage [with] a mobile segment and an immobile segment"?

**CN 121979402 A (PAT-03; pending)**

- **Q8.** On the Chinese text: are the reverse micro-vibration assemblies (motor + eccentric mass) and the bidirectional interaction module essential features of claim 1, and therefore of every claim?
  - What prior-art effect does the application have against our filings, given filing 2026-02-24, publication 2026-05-05 and our own priority dates? This applies in CN, and in EP/US if PCT or national equivalents are filed by 2027-02-24.
  - Should we monitor for amendment of claim 1 dropping the eccentric-mass limitation?
- **Q9.** Claim 7 restricts the guide ring to translation "so that ... the inclination of the pen core is prevented".
  - Does this support differentiation of a pivoting refill (feature j)?
  - Conversely, could claims 3 and 6 without claim 7 be read on a tilting refill whose tip moves in X-Y?
  - Is "guidance force ... along a preset stroke track" met by position-controlled bounded correction toward a letter template?

**Verily tremor-stabiliser family (PAT-07, PAT-08, PAT-12)**

- **Q10.** For US 11,944,216 B2 claims 1, 13 and 18, and US 9,943,430 B2 claim 1:
  - Can a pen refill or nib carrier be an "attachment arm ... configured to attach a user assistive device"? Can a refill be a "user-assistive device"?
  - Is a flexure stage driven by voice-coil or piezo actuators a "motion-generating mechanism"?
  - Please confirm the expiry of US 11,944,216 B2 under its terminal disclaimer and 1226-day PTA, and search for live continuations.
- **Q11.** US 9,925,034 B2 claim 1 requires "at least one remote non-contact position sensor external to and not in physical contact with the stabilization unit" and an external processing unit. Is an entirely on-board system outside this claim, and do later family members lack these limitations?

**Other records**

- **Q12.** US 10,078,320 B2 (Shaper): claims 1 and 19 require locating the working member "using a map of the surface retrieved from memory", indicating it "via a display screen of the rig", registering a design to that map, and maintaining alignment "as the rig is advanced".
  - Does a pen with local optical flow (no stored surface map), no display on the pen, and letter templates anchored to the pen's own start point fall outside these claims?
  - Do continuation claims (for example US 11,815,873 B2 and US 11,467,554 B2) omit these limitations or cover hand-held pens?
- **Q13.** US 10,369,045 B2: claims 1 and 17 combine actuation-force compensation of a shaft force signal with vibrating the shaft along the sensed force direction.
  - If our firmware subtracts actuator-induced force from the nib force signal but never vibrates the nib along the force direction, is it outside these claims?
  - Are any continuations pending without the vibration limitation?
- **Q14.** Optical capture families:
  - Did WO 2020/091323 A1 (NeoLAB: speckle + tilt correction + pressure-gated transmission) enter national phases, and would optical flow + IMU tilt correction + force-gated logging fall within them?
  - Same question for WO 2024/072219 A1 (Nuwa): the FOV >= 90 deg limitation against a narrow-FOV flow sensor, and the claims of NL 2034260 B1.
- **Q15.** Pending guidance and feedback claims:
  - US 2025/0006076 A1 (IBM): could "vibration commands ... to guide the haptic stylus held by the user to form the selected letter" be read on nib-displacement guidance or on any vibrotactile cue we add?
  - US 2025/0162342 A1 (Neubauer; 2014 priority chain): if our companion app derives handwriting-quality or therapy-progress metrics from recognition confidence over time, is that within claims 1, 10 or 20? Do other family members (for example US 2021/0291579 A1) claim rule-based or haptic feedback?
- **Q16.** For our own filings: this sample shows no claims reciting (f) predictive tremor cancellation, (h) confidence-based authority limiting, or (j) a front-flexure pivot with rear actuation.
  - The combination (a)+(c)+(e)+(i) in one pen does appear in PAT-03's claims, but with eccentric-mass tremor suppression and a translation-only refill.
  - Apart from the abandoned PAT-23 (claim 29: generic "stabilization" in a motor-driven marking device, with presets and camera feedback in other claims), nib-displacement tremor cancellation combined with guidance and capture was not found claimed in a pen in this sample.
  - Would a professional novelty search, including non-patent literature (Micron, electromagnetic guidance systems), support such claims?
  - Which disclosures here (PAT-01, 03, 05, 23, 24, 25) are the closest prior art for claim drafting?
- **Q17.** Several documents are expired, abandoned or withdrawn as displayed: PAT-02, 05, 06, 11, 16, 22, 23, 24. Please confirm each status in the official registers and advise which remain relevant only as prior art.

---

## 10. Screened, identified but not recorded, or not reviewed

- **Screened out after review:**
  - US 7,265,750 B2 (Immersion, haptic stylus with 1-axis actuator between body and tip; expired - fee related as displayed).
  - CN 109263362 A (Guangdong Genius, camera pen with tip-facing lens; cited on the face of PAT-01).
  - US 2023/0364936 A1 (BIC, audio-to-tactile haptics and heart-rate; not relevant).
  - US 11,567,590 B2 (NeoLAB; title only).
- **Identified, not reviewed; attorney or researcher follow-up suggested:**
  - Verily/Lift Labs family: US 10,455,963 and US 10,368,669 (parents of PAT-12); US 2014/0052275 A1; US 10,219,930 B2 and US 11,883,342 B2 (high-amplitude tremor stabilisation); US 10,058,445 B2 and US 10,758,388 B2 (motion stabilisation); US 10,851,867 B2 (feedback controller); US 10,532,465 (same title as PAT-08); EP 3258829 B1 (tremor measurement through a handheld tool).
  - Shaper Tools continuations: US 10,556,356 B2 (drawing-path embodiment); US 10,788,804 B2; US 10,795,333 B2; US 11,467,554 B2; US 11,815,873 B2.
  - Tremor and handwriting-assistance aids:
    - US 6,234,045 B1 (Draper, "Active tremor control").
    - EP 3846973 A1 (Université Laval, movement assistance for feeding and writing).
    - MY 171245 A (Universiti Teknologi Malaysia, writing means for tremor).
    - JP H07-64694 A (Sharp, "anti-shake pen input system").
    - KR 2021-0025998 A ("Smartpen, helping handwriting").
    - EP 2004423 B1 (Philips, "Expressive pen").
    - EP 2182423 A2 (KIT, "Writing device").
    - CN 108215585 A ("dynamics simulation writing device").
    - WO 2018/229662 A1 (smart pen for pen-holding skill).
  - Remaining EP search-report A documents against PAT-02: US 5,501,535 A and US 5,861,877 A.
  - STABILO: DE 10 2014 106 838 B4 ("drift compensation / optical absolute referencing", which may combine IMU and optics and is relevant to b + c).
  - Stylus haptics: US 11,221,677 B2 (Apple "Pencil haptics"); TDK haptic pen (CN 112424559 B / TW I780346 B).
  - Core CMU Micron tremor-cancellation patents: not found (query G19 blocked).

---

## 11. Gaps and recommended next steps

1. **Verify statuses in official registers.**
   - USPTO Patent Center: maintenance fees, continuity, terminal disclaimers.
   - EPO Register: EP 4250070 A1, EP 3143479 B1.
   - CNIPA: CN 121979402 A, CN 115050031 A, CN 109118875 A.
   - KIPO and WIPO PATENTSCOPE: national phases of WO 2020/091323 A1 and WO 2024/072219 A1.
   - Priority by FTO weight: PAT-12, PAT-04, PAT-01, PAT-03, PAT-25 and PAT-07/08.
2. **Obtain certified or verified texts.**
   - Chinese original and professional translation of CN 121979402 A claims.
   - Korean original of WO 2020/091323 A1 claim 1.
   - Certified copies of the US claims transcribed here by OCR.
3. **Run the searches that were blocked or out of budget.**
   - W9-W11 and G19-G21.
   - CPC A61B 5/11 with actuator terms.
   - CPC B43K 29/00 and B43K 29/004 with "actuator OR motor" and priority after 2018.
   - Forward citations of US 12,026,327 B2, US 10,101,824 B2 and US 11,120,704 B2.
   - Assignee sweeps for BIC 2022-2026, Verily 2019-2026, Shaper 2020-2026, NeoLAB and Nuwa.
   - Chinese-language searches for 防抖笔 / 手抖 书写 辅助 with CNIPA syntax; Japanese searches (手振れ ペン).
4. **Monitor.** CN 121979402 A (PCT or foreign filings by 2027-02-24); US 2025/0006076 A1 (IBM); US 2025/0162342 A1 (Neubauer); and any continuation of PAT-01 or PAT-04.
5. **Engineering records.** Keep dated design records of the choices raised in §9: 2-axis vs ZP actuation, pivot vs translation, guidance representation, force-sensor use and on-board sensing. This will help the attorney with both differentiation and FTO.

*Nothing in this note is a legal opinion. Novelty, practical differentiation and freedom to operate are separate assessments for a qualified patent attorney.*
