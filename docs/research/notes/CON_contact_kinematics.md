# CON stream: pen-paper contact mechanics, writing forces and handwriting kinematics

Evidence ledger: `docs/research/ledger/CON_contact_kinematics.csv` (CON-01 to CON-30). Prepared 2026-09-26.

## 1. Search log

All searches ran on 2026-09-26 in the requester's session. The UTC clock passed midnight part-way through, so later entries carry the UTC date 2026-09-27. Ledger rows keep `retrieved = 2026-09-26` as specified.

Tools used:
- **WebSearch** (Anthropic search tool). The session-wide budget, shared with other streams, ran out after the entries marked below.
- **WebFetch** (page fetch with automated extraction). Key numbers were then re-checked with verbatim-quote prompts.
- **curl** downloads of PDFs, followed by pdftotext, or tesseract OCR for scanned patents. Figures were rendered and read visually where values existed only in plots.
- **Scholarly APIs:** NCBI E-utilities, Europe PMC REST, Crossref, Semantic Scholar, OpenAlex, J-STAGE search API and DSpace (UMD DRUM).
- **DuckDuckGo HTML search** via curl. It stopped working after a bot challenge.

Entries tagged [reconstructed] were added from the session transcript because the automatic log missed them. They are placed by date; order within a date is approximate.

| # | Date | Tool | Exact query or URL | Outcome |
|---|---|---|---|---|
| 1 | 2026-09-26 | WebSearch | Wann Nimmo-Smith 1991 "The control of pen pressure in handwriting: a subtle point" axial force |  |
| 2 | 2026-09-26 | WebSearch | Schomaker Plamondon 1990 "relation between pen force and pen-point kinematics in handwriting" |  |
| 3 | 2026-09-26 | WebSearch | Hooke Park Shim 2008 "kinetic pen" forces behind the words digit forces pen-paper normal force |  |
| 4 | 2026-09-26 | WebFetch/curl | https://www.ai.rug.nl/~lambert/papers/pen-pressure.pdf (Schomaker & Plamondon 1990 preprint, full text) | full text read (CON-01, CON-02) |
| 5 | 2026-09-26 | WebSearch | Hermsdörfer Marquardt Schneider Fürholzer Baur 2011 "finger forces and kinematics during handwriting in writer's cramp" grip force N |  |
| 6 | 2026-09-26 | WebSearch | Schwellnus 2013 "Writing forces associated with four pencil grasp patterns in grade 4 children" axial force grip force newtons |  |
| 7 | 2026-09-26 | WebSearch | Ghali 2013 "Variability of grip kinetics during adult signature writing" PLoS One grip force newtons |  |
| 8 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC3642185/ (Ghali 2013 PLoS One) | full text (CON-08) |
| 9 | 2026-09-26 | curl | https://tspace.library.utoronto.ca/bitstream/1807/43948/1/Ghali_Bassma_201311_PhD_thesis.pdf (Ghali 2013 PhD thesis) | full text thesis (CON-08) |
| 10 | 2026-09-26 | curl (NCBI E-utilities efetch) | PMIDs 20580894,18514204,23433277,23658812,17230462 abstracts |  |
| 11 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC3722657/ (Schwellnus 2013 AJOT) | full text (CON-05) |
| 12 | 2026-09-26 | WebSearch | Kushki Schwellnus Ilyas Chau 2011 "Changes in kinetics and kinematics of handwriting during a prolonged writing task" grip force axial force |  |
| 13 | 2026-09-26 | WebSearch | Chau Ji Tam Schwellnus 2006 "A novel instrument for quantifying grip activity during handwriting" Archives of Physical Medicine and Rehabilitation |  |
| 14 | 2026-09-26 | curl (NCBI E-utilities efetch) | PMIDs 21315553,17084133 abstracts | abstracts (CON-06, CON-07) |
| 15 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC9231762/ (Lin et al. 2022 PLOS One pen-grip kinetics children) | full text (CON-04) |
| 16 | 2026-09-26 | curl | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/0167-9457(91)90005-I (Wann 1991 metadata; abstract elided, closed access) |  |
| 17 | 2026-09-26 | WebFetch | https://pure.royalholloway.ac.uk/en/publications/the-control-of-pen-pressure-in-handwriting-a-subtle-point/ (no abstract) |  |
| 18 | 2026-09-26 | WebFetch | https://www.academia.edu/94837428/... (403) | HTTP 403 |
| 19 | 2026-09-26 | WebSearch | "Wann" "Nimmo-Smith" pen pressure children "axial" force newtons "poor handwriting" friction feedback |  |
| 20 | 2026-09-26 | WebSearch | handwriting axial pen force adults mean newtons instrumented pen paper "pen force" study healthy adults "N" |  |
| 21 | 2026-09-26 | WebFetch | https://en.wikipedia.org/wiki/Axial_pen_force |  |
| 22 | 2026-09-26 | curl (NCBI E-utilities esearch) | terms: "axial pen force"; "pen pressure handwriting newton"; "writing pressure parkinson pen"; "handwriting force essential tremor"; "pen tilt handwriting"; "pen grip force handwriting adults" |  |
| 23 | 2026-09-26 | curl (NCBI E-utilities efetch) | PMIDs 9844562,20594605,19406309,19360497,20488445,22643028,40618453,23934582,42490571,24510237 abstracts | abstracts (CON-09, CON-30) |
| 24 | 2026-09-26 | WebSearch | coefficient of friction ballpoint pen on paper measurement writing feel tribology |  |
| 25 | 2026-09-26 | WebSearch | Gerth 2016 handwriting tablet paper friction "Adapting to the surface" Human Movement Science pen pressure |  |
| 26 | 2026-09-26 | WebFetch | https://www.jstage.jst.go.jp/article/trol/12/5/12_257/_article (Isokane 2017 Tribology Online) | metadata; PDF then downloaded |
| 27 | 2026-09-26 | WebFetch | https://www.mdpi.com/2075-4442/10/3/44 (403) | HTTP 403 |
| 28 | 2026-09-26 | curl | https://www.jstage.jst.go.jp/article/trol/12/5/12_257/_pdf (Isokane et al. 2017 full text) | full text (CON-16) |
| 29 | 2026-09-26 | curl | https://www.mdpi.com/2075-4442/10/3/44/pdf (403 blocked) | HTTP 403 |
| 30 | 2026-09-26 | WebSearch | "writing resistance" ballpoint pen paper friction force measured N load angle speed low viscosity oil-based ink |  |
| 31 | 2026-09-26 | WebSearch | 筆記抵抗 ボールペン 摩擦係数 紙 測定 荷重 筆記角度 |  |
| 32 | 2026-09-26 | curl | https://www.jstage.jst.go.jp/article/jsmemdt/2016.16/0/2016.16_A3-2/_pdf/-char/ja (JSME 2016 A3-2 conference, Isokane et al.) |  |
| 33 | 2026-09-26 | WebFetch | https://www.forcegauge.net/solution/force/friction_test/67790 (Imada app note; no numbers) |  |
| 34 | 2026-09-26 | WebSearch | "Direct measurement of friction acting between a ballpoint pen and a paper" |  |
| 35 | 2026-09-26 | WebFetch | https://ieeexplore.ieee.org/document/1491667 (empty) |  |
| 36 | 2026-09-26 | curl | https://api.crossref.org/works?query.bibliographic=Direct+measurement+of+friction+acting+between+a+ballpoint+pen+and+a+paper (no match) |  |
| 37 | 2026-09-26 | curl | Semantic Scholar search API (429 rate limited) | rate limited |
| 38 | 2026-09-26 | WebFetch | https://patents.google.com/patent/US11891491B2/en (Lintec writing-feel sheet patent) | touch-pen/sheet claims (mu 0.11-0.64 at 200 g, 45 deg) - not ledgered |
| 39 | 2026-09-26 | WebFetch | https://patents.google.com/patent/US10671187B2/en (Wacom pen input sheet patent; 2 prompts) | full text (CON-14) |
| 40 | 2026-09-26 | WebSearch | stylus friction coefficient glass screen versus paper measured tribometer handwriting "coefficient of friction" pen tablet study |  |
| 41 | 2026-09-26 | WebSearch | pencil graphite on paper friction coefficient measured writing tribology stick-slip |  |
| 42 | 2026-09-26 | WebFetch | https://www.sciencedirect.com/science/article/pii/0043164896069529 (403) | HTTP 403 |
| 43 | 2026-09-26 | WebFetch | https://arxiv.org/pdf/1803.02307 (RealPen; saved PDF, text extracted) | no numeric friction; gave citation Chigira, Fujii & Valera (SICE 2004) |
| 44 | 2026-09-26 | WebFetch | https://ceramics.org/ceramic-tech-today/accelerating-development-of-paper-like-electronic-screens-researchers-explore-friction-behaviors-of-stylus-tips-on-textured-glass-surfaces/ | secondary news, no numbers; Tribology International 2022 paper not accessed |
| 45 | 2026-09-26 | WebFetch | https://patents.google.com/patent/US10955943B2/en (404) |  |
| 46 | 2026-09-26 | note | WebSearch budget exhausted (200/200 session-wide) at this point; switching to curl-based search APIs (DuckDuckGo HTML, OpenAlex, Crossref, NCBI E-utilities, Europe PMC) |  |
| 47 | 2026-09-26 | DuckDuckGo (curl html) | ISO 12757-1 writing test angle load speed |  |
| 48 | 2026-09-26 | curl | https://cdn.standards.iteh.ai/samples/1129/d31cfcb55e2c4394a2d8c24916bd511a/ISO-12757-1-1998.pdf (ISO 12757-1:1998 preview incl. clause 5.1) | clause 5.1 read (CON-21) |
| 49 | 2026-09-26 | curl | https://cdn.standards.iteh.ai/samples/73283/1b0bbd644c4d451d877b3aeca1354456/ISO-12757-1-2017.pdf (ISO 12757-1:2017 preview, Tables 1-3 rendered and read) | Tables 1-3 read (CON-22) |
| 50 | 2026-09-26 | DuckDuckGo (curl html) | ISO 14145-1 roller ball write test machine point load writing angle speed |  |
| 51 | 2026-09-26 | DuckDuckGo (curl html) | ISO 14145-1 roller ball pens write test machine |  |
| 52 | 2026-09-26 | DuckDuckGo (curl html) | iteh ISO 14145-1 sample pdf |  |
| 53 | 2026-09-26 | curl | https://cdn.standards.iteh.ai/samples/73282/*/ISO-14145-1-2017.pdf (two ISO 14145-1:2017 previews) |  |
| 54 | 2026-09-26 | curl | https://www.ai.rug.nl/~lambert/papers/ (directory listing) |  |
| 55 | 2026-09-26 | curl | https://www.ai.rug.nl/~lambert/papers/thesis-schomaker-1991.pdf | full text (CON-24) |
| 56 | 2026-09-26 | curl | https://www.ai.rug.nl/~lambert/papers/Wrid-1988-Maarse-etal.pdf |  |
| 57 | 2026-09-26 | curl | https://www.ai.rug.nl/~lambert/papers/robmot-schomaker-1988.pdf |  |
| 58 | 2026-09-26 | curl | https://www.ai.rug.nl/~lambert/papers/teulings/teulings-schomaker-bonas-1991.pdf |  |
| 59 | 2026-09-26 | curl+pdftotext | https://www.ai.rug.nl/~lambert/papers/thesis-schomaker-1991.pdf (read pp. ~186-187 and ch.1) | full text (CON-24) |
| 60 | 2026-09-26 | curl | https://public-pages-files-2025.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.01308/pdf (Gerth et al. 2016 Front Psychol full text) | full text (CON-20) |
| 61 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC13395322/ (Toffoli et al. 2026 PLOS Digit Health) | sensorised ink pen reports tilt/force indicators but no numeric values in text - not ledgered |
| 62 | 2026-09-26 | DuckDuckGo (curl html) | pen tilt angle during handwriting altitude degrees distribution participants stylus study |  |
| 63 | 2026-09-26 | DuckDuckGo (curl html) | "altitude" angle pen handwriting mean degrees Wacom writers natural pen tilt |  |
| 64 | 2026-09-26 | curl | https://www3.cs.stonybrook.edu/~xiaojun/pdf/pta.pdf (Xin/Ren/Bi CHI 2012 natural use profiles) | full text (CON-12) |
| 65 | 2026-09-26 | curl | https://openaccess-api.cms-conferences.org/articles/download/978-1-4951-2102-9_54 (AHFE pen holding posture) | read; pitch/roll 24-40 deg, N=8, definitions ambiguous - not ledgered |
| 66 | 2026-09-26 | curl (NCBI E-utilities esearch) | handwriting+AND+parkinson*+AND+(pressure+OR+force)+AND+(newton*+OR+axial) |  |
| 67 | 2026-09-26 | curl (NCBI E-utilities esearch) | (writing+OR+handwriting)+AND+essential+tremor+AND+(pen+force+OR+pen+pressure+OR+axial) |  |
| 68 | 2026-09-26 | curl (NCBI E-utilities esearch) | handwriting+AND+(pen+pressure+OR+axial+force)+AND+(fatigue+OR+prolonged) |  |
| 69 | 2026-09-26 | curl (NCBI E-utilities esearch) | handwriting+AND+speed+AND+(pen+pressure+OR+axial+force)+AND+adults |  |
| 70 | 2026-09-26 | curl (NCBI E-utilities efetch) | PMIDs 34988457,38861795,10680310,16870291,21957916 |  |
| 71 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC8679070/ (Peters et al. 2021 ET; uncalibrated pressure) | full text (CON-11) |
| 72 | 2026-09-26 | DuckDuckGo (curl html) | Parkinson's disease handwriting pen force newtons axial force healthy controls instrumented pen |  |
| 73 | 2026-09-26 | DuckDuckGo (curl html) | Parkinson handwriting "pen pressure" "N" calibrated force transducer micrographia study |  |
| 74 | 2026-09-26 | curl | https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2023.1093690/pdf (smart ink pen spiral PD) | full text (CON-10) |
| 75 | 2026-09-26 | OpenAlex API (curl) | search: Lacquaniti Terzuolo Viviani law relating kinematic figural aspects drawing movements |  |
| 76 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"law relating the kinematic and figural aspects of drawing movements" |  |
| 77 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"speed-curvature power law" AND reappraisal | abstract (CON-27) |
| 78 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"two-thirds power law" AND (handwriting OR drawing) |  |
| 79 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"coordination of arm movements: an experimentally confirmed mathematical model" | abstract (CON-26) |
| 80 | 2026-09-26 | Europe PMC REST search (curl) | AUTH:"Plamondon R" AND (lognormal OR "kinematic theory") |  |
| 81 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"A model of handwriting" AND AUTH:"Edelman S" | abstract (CON-26) |
| 82 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC3867641/ (Plamondon et al. 2013 lognormal handwriter) | full text (CON-28) |
| 83 | 2026-09-26 | curl | https://archive.ics.uci.edu/static/public/175/character+trajectories.zip (UCI Character Trajectories dataset) | dataset downloaded (CON-25) |
| 84 | 2026-09-26 | LOCAL ANALYSIS | chartraj/spec.py, spec2.py on UCI Character Trajectories (single writer, 2858 chars, 200 Hz) | spectral fractions, band-passed displacement, speeds (CON-25); also kin.py for accelerations and stroke intervals |
| 85 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"pen pressure and grip force signal during basic drawing tasks" | abstract (CON-29) |
| 86 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"Does handwriting speed influence pencil grip force" |  |
| 87 | 2026-09-26 | Europe PMC REST search (curl) | TITLE:"Digitized analysis of handwriting and drawing movements in healthy subjects" |  |
| 88 | 2026-09-26 | DuckDuckGo (curl html) | ballpoint pen stroke groove depth paper micrometres profilometry writing pressure indentation forensic |  |
| 89 | 2026-09-26 | DuckDuckGo (curl html) | indentation depth ballpoint pen paper writing force relationship underlay hard surface soft pad study |  |
| 90 | 2026-09-26 | DuckDuckGo (curl html) | ballpoint indentation depth paper writing pressure |  |
| 91 | 2026-09-26 | DuckDuckGo (curl html) | handwriting stroke depth 3D profilometry ballpoint |  |
| 92 | 2026-09-26 | Bing (curl html) | ballpoint pen indentation depth paper writing pressure micrometers | irrelevant results (bot mode); not used |
| 93 | 2026-09-26 | Europe PMC REST search (curl) | (ballpoint OR "ball point" OR "ball-point") AND (indentation OR groove OR depth OR profilometry) AND (writing OR stroke) |  |
| 94 | 2026-09-26 | Crossref API (curl) | writing pressure indentation depth ballpoint paper |  |
| 95 | 2026-09-26 | Crossref API (curl) | stroke depth handwriting three-dimensional profile ballpoint pen pressure |  |
| 96 | 2026-09-26 | Europe PMC REST search (curl) | AUTH:"Furukawa T" AND indentation |  |
| 97 | 2026-09-26 | Europe PMC REST search (curl) | "writing pressure" AND (indentation OR "stroke depth" OR "groove") |  |
| 98 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC13534941/ (Wang 2026 JFS; method unspecified, excluded) | indentation-variation claim with unspecified method - excluded |
| 99 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC8330766/ (Li & Liu 2021; qualitative only) | qualitative only - excluded |
| 100 | 2026-09-26 | WebFetch | https://doi.org/10.4103/jfsm.jfsm_71_21 -> ovid 402 paywall; jfsmonline redirect |  |
| 101 | 2026-09-26 | curl [reconstructed] | https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3722657/fullTextXML | HTTP 500; used WebFetch of PMC page instead |
| 102 | 2026-09-26 | curl [reconstructed] | https://pmc.ncbi.nlm.nih.gov/articles/PMC3722657/ and NCBI BioC API PMC3722657 | reCAPTCHA / HTTP 429 |
| 103 | 2026-09-26 | WebFetch [reconstructed] | https://pubmed.ncbi.nlm.nih.gov/20580894/ ; https://www.sciencedirect.com/science/article/abs/pii/S0167945710000539 | reCAPTCHA / HTTP 403; abstracts taken from NCBI E-utilities instead |
| 104 | 2026-09-26 | curl [reconstructed] | https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10955943 , /5627348 , /12030339 | scanned PDFs; 10955943 OCRed (pages 12-14) and FIG. 3 viewed |
| 105 | 2026-09-26 | OpenAlex API (curl) [reconstructed] | search: law relating kinematic figural aspects drawing movements | daily budget exhausted (no results) |
| 106 | 2026-09-27 (UTC) | OCR (tesseract, 72 dpi) | US 10,955,943 B1 pages 12-14 (Microsoft; stylus-paper COF, FIG. 3) | OCR pages 12-14 (CON-15) |
| 107 | 2026-09-27 (UTC) | Crossref API (curl) | Tribological characteristics of graded pencil cores on paper |  |
| 108 | 2026-09-27 (UTC) | Crossref API (curl) | friction pen paper handwriting feel measurement coefficient ballpoint gel rollerball fountain pen |  |
| 109 | 2026-09-27 (UTC) | Semantic Scholar API (curl) | DOI:10.1016/0043-1648(96)06952-9 |  |
| 110 | 2026-09-27 (UTC) | Semantic Scholar API (curl) | DOI:10.1016/j.matdes.2022.110739 |  |
| 111 | 2026-09-27 (UTC) | Semantic Scholar API (curl) | DOI:10.1016/0167-9457(84)90003-6 |  |
| 112 | 2026-09-27 (UTC) | OSTI API (curl) | title=pencil cores paper |  |
| 113 | 2026-09-27 (UTC) | curl | sciencedirect pdf link for Wann & Nimmo-Smith 1991 (403) |  |
| 114 | 2026-09-27 (UTC) | Semantic Scholar API (curl) | citations+contexts of Wann & Nimmo-Smith 1991 (paperId 2cf79276...) | secondary values via van Drempt 2011 (CON-03) |
| 115 | 2026-09-27 (UTC) | Semantic Scholar API search (curl) | Pressure on point and barrel of a writing instrument |  |
| 116 | 2026-09-27 (UTC) | Semantic Scholar API search (curl) | The relationship between handwriting pressure and legibility of handwriting in children and adolescents |  |
| 117 | 2026-09-27 (UTC) | Semantic Scholar API search (curl) | The problem of pressure in handwriting |  |
| 118 | 2026-09-27 (UTC) | Semantic Scholar API (curl) | citations+contexts of Herrick & Otto 1961 |  |
| 119 | 2026-09-27 (UTC) | Semantic Scholar API search (curl) | handwriting kinetics a search for synergies |  |
| 120 | 2026-09-27 (UTC) | DSpace API (curl) | drum.lib.umd.edu search: handwriting kinetics synergies |  |
| 121 | 2026-09-27 (UTC) | curl | https://api.drum.lib.umd.edu/server/api/core/bitstreams/9c0cdc56-b576-45cd-8a19-becbaeeafe4c/content (Hooke 2008 MSc thesis, UMD DRUM hdl 1903/9002) | full text thesis (CON-17) |
| 122 | 2026-09-27 (UTC) | pdftoppm+visual read | Hooke 2008 thesis Figure 4.2 (pp.42-43) |  |
| 123 | 2026-09-27 (UTC) | WebFetch | https://patents.google.com/patent/US8771410B2/en (Pentel ink patent test conditions) | test conditions (CON-23) |
| 124 | 2026-09-27 (UTC) | WebFetch | https://patents.google.com/patent/US12030339B2/en (BIC passive variable friction pen; claim ranges only) | claim ranges only - not ledgered |
| 125 | 2026-09-27 (UTC) | DuckDuckGo (curl html) | Schmidt D1 mini refill 67 mm weight datasheet |  |
| 126 | 2026-09-27 (UTC) | curl (NCBI E-utilities esearch) | parkinson*+AND+(writing+OR+handwriting)+AND+(%22grip+force%22+OR+%22pen+force%22+OR+%22axial+force%22+OR+%22tip+force%22) |  |
| 127 | 2026-09-27 (UTC) | curl (NCBI E-utilities esearch) | tremor+AND+(writing+OR+handwriting)+AND+(%22grip+force%22+OR+%22pen+force%22+OR+%22tip+force%22) |  |
| 128 | 2026-09-27 (UTC) | curl (NCBI E-utilities efetch) | PMIDs 36349662,27422450 |  |
| 129 | 2026-09-27 (UTC) | J-STAGE search API (curl) | ボールペン 筆記抵抗 |  |
| 130 | 2026-09-27 (UTC) | J-STAGE search API (curl) | ボールペン 摩擦係数 |  |
| 131 | 2026-09-27 (UTC) | J-STAGE search API (curl) | 筆記具 書き味 摩擦 |  |
| 132 | 2026-09-27 (UTC) | J-STAGE search API (curl) | ballpoint pen friction paper |  |
| 133 | 2026-09-27 (UTC) | curl | https://www.jstage.jst.go.jp/article/trol/18/5/18_202/_pdf (Hase 2023 Tribology Online) | education paper, not relevant |
| 134 | 2026-09-27 (UTC) | curl | https://www.jstage.jst.go.jp/article/jsmecs/2026.64/0/2026.64_08C1/_pdf/-char/ja |  |
| 135 | 2026-09-27 (UTC) | curl | https://www.jstage.jst.go.jp/article/jsmemecj/2021/0/2021_S113-22/_pdf/-char/ja |  |
| 136 | 2026-09-27 (UTC) | WebFetch | J-STAGE landing pages jsmecs.2026.64.08C1 and jsmemecj.2021.S113-22 (abstract only, no numbers) |  |
| 137 | 2026-09-27 (UTC) | Europe PMC REST search (curl) | DOI:"10.3390/lubricants10030044" |  |
| 138 | 2026-09-27 (UTC) | curl | https://mdpi-res.com/d_attachment/lubricants/lubricants-10-00044/article_deploy/lubricants-10-00044.pdf (Hase 2022 Lubricants full text) | full text (CON-13) |
| 139 | 2026-09-27 (UTC) | pdftoppm+visual read | Hase 2022 Lubricants Figures 4 and 9 (pp.4,7) |  |
| 140 | 2026-09-27 (UTC) | curl | https://www.jstage.jst.go.jp/article/ningenseikatsukogaku/25/2/25_50/_pdf ; .../26/2/26_56/_pdf | full text (CON-18) |
| 141 | 2026-09-27 (UTC) | Europe PMC REST search (curl) | DOI:"10.1371/journal.pone.0270466" |  |
| 142 | 2026-09-27 (UTC) | WebFetch [verbatim re-check] | https://pmc.ncbi.nlm.nih.gov/articles/PMC3642185/ (Table 1 mean row and speed range) | full text (CON-08) |
| 143 | 2026-09-27 (UTC) | WebFetch [reconstructed] | https://www.semanticscholar.org/paper/The-control-of-pen-pressure-in-handwriting:-A-point-Wann-Nimmo-Smith/2cf792767e477f17f093d8abaa9409b14b47a44e | JS page, no content |
| 144 | 2026-09-27 (UTC) | curl [reconstructed] | https://api.unpaywall.org/v2/10.1016/j.matdes.2022.110739 ; https://www.sciencedirect.com/science/article/pii/S0264127522003616/pdf | OA copy only at ScienceDirect, HTTP 403 (Fritz 2022 fountain-pen ink paper not read) |
| 145 | 2026-09-27 (UTC) | curl [reconstructed] | https://webstore.ansi.org/preview-pages/ISO/preview_ISO+12757-2-1998.pdf | HTTP 403 (ISO 12757-2 not accessed) |
| 146 | 2026-09-27 (UTC) | WebFetch [reconstructed] | https://www.schmidttechnology.de/en/ | no refill datasheets/masses on page |
| 147 | 2026-09-27 (UTC) | WebFetch (verbatim re-checks) [reconstructed] | https://pmc.ncbi.nlm.nih.gov/articles/PMC9231762/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3722657/ ; https://patents.google.com/patent/US10671187B2/en ; https://patents.google.com/patent/US8771410B2/en | verbatim quotes and dates confirmed |
| 148 | 2026-09-27 (UTC) | WebFetch [reconstructed] | https://www.ovid.com/10.4103/jfsm.jfsm_71_21 ; https://www.jfsmonline.com/article.asp?issn=2349-5014;year=2021;volume=7;issue=4;spage=152;epage=158;aulast=Guo | HTTP 402 / redirect; Guo & Li 2021 stroke-indentation study not read |
| 149 | 2026-09-27 (UTC) | curl [reconstructed] | https://archive.ics.uci.edu/dataset/175/character+trajectories | dataset DOI 10.24432/C58G7V |
| 150 | 2026-09-27 (UTC) | WebFetch [reconstructed] | https://www.jstage.jst.go.jp/article/jsmecs/2026.64/0/2026.64_08C1/_article/-char/ja/ ; https://www.jstage.jst.go.jp/article/jsmemecj/2021/0/2021_S113-22/_article/-char/ja/ | abstract/metadata only; 2026 paper subscription-only |

Sources examined but not ledgered, or inaccessible:
- **Wann & Nimmo-Smith 1991** (Hum Mov Sci 10:223-246): paywalled. Values reached only second-hand via CON-03.
- **Herrick & Otto 1961 and Harris & Rarick:** no access. Citing papers describe Herrick & Otto only qualitatively: 60 writers, and high point pressure goes with high grip pressure.
- **Chigira, Fujii & Valera 2004** (SICE, direct pen-paper friction measurement): abstract has no numbers.
- **Blau & Gardner 1996:** abstract not accessible (see CON-19).
- **Fritz 2022** (fountain-pen ink): ScienceDirect returned 403.
- **Guo & Li 2021** (stroke indentation): paywalled.
- **Murata & Gotoh** (AHFE): pen pitch/roll 24-40 deg with N = 8, but the angle definitions are ambiguous.
- **Wang et al. 2026** (J Forensic Sci): reports "indentation depth variation" of 0.15 mm (natural) vs 0.03 mm (robotic) with no measurement method, so it was excluded.
- **Lintec US 11,891,491 B2:** touch-pen friction ranges on screen sheets.
- **BIC US 12,030,339 B2:** claim ranges only.
- **ISO 12757-2 and ISO 14145-1** (rollerball) test clauses: not available in the previews.

## 2. Critical synthesis

Scope: contact loads, tilt, friction and intended-writing kinematics for sizing a ±0.5 mm nib actuator. Ledger IDs in brackets. "Derived" values were calculated by this stream and have no published source.

### 2.1 Best current estimates

| Quantity | Best estimate | Plausible range | Main evidence |
|---|---|---|---|
| Axial pen force, healthy adults, ballpoint on paper | 1.0 N (between-writer SD 0.4 N) | writer means 0.56–2.1 N; within-word SD about 0.2 N | CON-01, CON-03, CON-14 |
| Normal force | about 0.8 × axial force (at 50–60° tilt) | 0.4–2.5 N typical; about 4 N high cases | CON-02, CON-14, CON-18 |
| Pen altitude (tilt to paper) | 55–62° | 95% range 47–77°; within writing ±2.5°, at most 10° | CON-02, CON-12 |
| Azimuth (right-handers) | 132° ± 22° | 89–175° | CON-12 |
| Kinetic friction, ballpoint on paper | μ ≈ 0.15 | 0.09–0.4, with about ±25% ripple along a stroke | CON-13, CON-14, CON-15, CON-17 |
| Grip squeeze on the barrel | 4–7 × tip force | adults 5–20 N in total | CON-04, CON-05, CON-07, CON-08 |
| Pen-tip speed on paper | 30 ± 8 mm/s (phrase) | 20–105 mm/s by task; signatures 38–226 mm/s (tablet); peaks about 2 × mean | CON-20, CON-08, CON-25 |
| Stroke duration | 135 ms | 90–150 ms | CON-24, CON-25 |
| Intended-motion spectrum | velocity flat 1–5 Hz, noise level by about 10 Hz | 90% of velocity energy below 4.9 Hz; 99% below 9.3 Hz | CON-24, CON-25, CON-02 |

Children write with similar force: 0.65–1.23 N on a tablet (CON-05), 0.95 ± 0.29 N on paper (CON-04). Force drifts upward within words (+8 g/s in cursive trials) and across tasks (CON-01, CON-03, CON-06). It also rises with task difficulty (CON-30) and in writer's cramp (CON-09). In Parkinson's disease (PD), force is lower but more variable (CON-10). No calibrated writing-force data were found for essential tremor (ET): the one ET study reports raw tablet units only (CON-11). Speed does not appear to change normal force (CON-29).

**Spectral overlap with tremor (key design finding).**
- A single-writer dataset (CON-25, derived) was re-analysed. The 4–7 Hz band holds about 17% of intended velocity energy and the 8–12 Hz band about 1.5%.
- Band-passed intended displacement is about 7% of letter height at 4–7 Hz and about 1% at 8–12 Hz. For 3–4 mm letters that is about 0.2–0.3 mm RMS at 4–7 Hz, which is comparable to the actuator stroke. At 8–12 Hz it is about 0.03–0.04 mm RMS.
- In healthy older adults drawing spirals, 36% of pen angular-velocity power already lies in 4–7 Hz (CON-10).
- Implication: cancelling at 8–12 Hz (the physiological tremor band) is nearly free for handwriting. Cancelling at 4–7 Hz (the PD tremor band used in CON-10) will remove real stroke content unless it uses a model of the intended motion, such as minimum-jerk or lognormal priors (CON-26, CON-27, CON-28).

### 2.2 Derived load budget (analytical, CON)

For altitude θ, normal force N and friction μN at the nib, the contact force resolves into:
- perpendicular to the pen axis, within the pen's vertical plane: N·cosθ ± μN·sinθ;
- perpendicular to the pen axis, out of that plane: up to μN;
- along the pen axis: N·sinθ ∓ μN·cosθ.

At θ = 55° and μ = 0.15–0.4, an actuator whose axes are perpendicular to the pen axis must react 0.25–0.9 N per newton of normal force. Most of this is geometric (cos θ), not friction. Taking N = 4 N as the design case gives up to about 3.6 N lateral and 4.2 N axial.

Inertia is small by comparison: at 10 Hz and ±0.5 mm, (2π·10)²·0.5 mm ≈ 2 m/s², only about 6 mN for a few-gram nib assembly (refill mass unpublished; weigh it).

Actuator force is therefore set by contact loads and tilt, not by inertia. The housing must also carry 5–20 N of grip squeeze without moving the nib (CON-08). Some writers roll or regrip the pen (CON-08), so the actuator frame must be referenced to pen orientation.

### 2.3 What can be modelled from published data

- Distributions of normal force (right-skewed, mean about 1 N, between-writer CV about 40%) and tilt (Gaussian, 55–62° ± 7.5°).
- Friction as μN with μ in 0.1–0.4, rising with load and paper sinking (μ ∝ δ/SR, CON-14), plus about 25% spatial ripple. At writing speeds, texture on a 1–5 mm scale maps to broadband disturbance of roughly 6–100 Hz (CON-15).
- Intended-motion spectra, peak speeds of about 100–200 mm/s and peak accelerations of about 1 m/s² at normal letter size (scaled from 3.8 m/s² for 14 mm letters).
- Bench reference points from the standards and patents: 1.5 N, 75° ± 5°, 75 mm/s (CON-21); 1.47 N, 70° and 90°, 70 mm/s (CON-23).
- Envelopes of the ISO type D (67 × 2.35 mm) and type G2 refills (CON-22).

### 2.4 What must be measured on our refill and paper

1. Kinetic and breakaway μ versus normal load (0.3–4 N), speed (1–200 mm/s), push versus pull direction, tilt (45–80°) and ink. Use 80 g/m² copy and notebook paper, each over a hard desk, a pad of about 50 sheets and a soft underlay.
2. The small-amplitude, reciprocating regime (±0.02–0.5 mm at 3–15 Hz). This covers pre-sliding stiffness, hysteresis and rolling versus sliding of the ball. No source covers it, yet it decides whether the paper acts as a spring/damper on the nib during cancellation.
3. Paper sinking δ and contact stiffness versus load for our ball and tip radius, on each underlay.
4. The minimum normal force, and the effect of lateral nib velocity, for continuous ink laydown. No source was found.
5. Refill and nib-assembly mass and centre of mass. No source was found.
6. Calibrated axial force, tilt and grip in PD and ET users holding our prototype, including 95th and 99th percentile peaks and drift over 10–30 min.

### 2.5 Conflicting or weak evidence

- **Friction.** Estimates span 0.04 (Dooijes, cited second-hand in CON-02), 0.09–0.17 (CON-13, at 90°), 0.10–0.40 (CON-14) and about 0.30 (CON-15, tip unknown). The spread plausibly reflects ball rolling versus sliding tips, angle, load and paper sinking. CON-13 is also internally inconsistent: its Fig. 4 and Fig. 9 disagree for the special oil ink.
- **Force level.** Estimates are 1.0 N (forearm fixed, CON-01), 1.4–1.5 N (review, CON-03) and 3.6–3.9 N (stylus tracing by one person, CON-18). Instruments, axes and tasks differ.
- **Tilt.** Readings are 50° (paper, 4 subjects, CON-02) and 62° (tablet, 20 subjects, CON-12).
- **Fatigue.** CON-06 reports force rising over 10 min, while CON-05 finds no significant pre/post change.
- **Spectral peak.** Estimates are about 5 Hz for cursive (CON-24), 3.5–4.5 Hz for drawn patterns (CON-02) and 3.0 Hz for large isolated letters (CON-25). Our spectral fractions therefore probably understate the 4–7 Hz content of fast cursive writing.
- **Access gaps.** Wann & Nimmo-Smith 1991, Harris & Rarick, Herrick & Otto 1961 and Teulings & Maarse 1984 could not be read. PD and ET data use uncalibrated units, and no indentation-depth measurements were found.

