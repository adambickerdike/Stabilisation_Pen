# PDT - Handwriting impairments in PD and ET, and handwriting interventions

- **Stream:** PDT (evidence ledger, compact actively-stabilised pen programme)
- **Date of all retrieval:** 2026-09-26
- **Ledger:** `docs/research/ledger/PDT_pd_et_handwriting.csv` (30 rows, PDT-01 to PDT-30)
- **Amplitude conventions:**
  - "p-p" means peak-to-peak.
  - "peak" means half of p-p for a sinusoid.
  - The +/-0.5 mm-per-axis nib stroke can fully cancel at most 1 mm p-p along one axis, or about 1.4 mm p-p along a diagonal, assuming ideal phase and bandwidth.
- **Scope:** No clinical or diagnostic claims are made or implied. The pen is not a diagnostic device.

## 1. Search log

### 1.1 Queries and retrievals

- **Tools:** WebSearch, WebFetch, Europe PMC REST API, Crossref REST API and Semantic Scholar Graph API (the APIs via curl), plus direct downloads inspected locally with pdftotext or Python.
- **Search budget:** 30 WebSearch queries ran. The 31st was refused because the session's shared WebSearch budget was exhausted. Remaining retrieval used the APIs and direct fetches, all listed below.
- **Blocked sources:**
  - PubMed pages returned a reCAPTCHA, so abstracts came from Europe PMC.
  - ScienceDirect, MDPI and CADTH returned HTTP 403.

| # | Date | Tool | Exact query or URL | Outcome / ledger use |
|---|---|---|---|---|
| 1 | 2026-09-26 | WebSearch | `Wagle Shukla 2012 BMJ Open micrographia and related deficits in Parkinson's disease cross-sectional study` | PDT-01 |
| 2 | 2026-09-26 | WebSearch | `Elble 2006 Brain tremor amplitude is logarithmically related to 4- and 5-point tremor rating scales` | PDT-11; surfaced Elble 2018 (screened) |
| 3 | 2026-09-26 | WebSearch | `Nackaerts 2016 Movement Disorders relearning of writing skills Parkinson's disease intensive amplitude training` | PDT-16; surfaced PDT-18 |
| 4 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC3383984/ | PDT-01 (full text) |
| 5 | 2026-09-26 | WebFetch | https://academic.oup.com/brain/article/129/10/2660/290348 (abstract only; paywalled) | PDT-11 (paywalled; abstract only) |
| 6 | 2026-09-26 | WebFetch | https://tremorjournal.org/articles/10.5334/tohm.455 | Elble 2018 (screened) |
| 7 | 2026-09-26 | WebSearch | `Elble Ellenbogen digitizing tablet Fahn-Tolosa-Marin ratings Archimedes spirals comparable minimum detectable change essential tremor` | PDT-12 |
| 8 | 2026-09-26 | WebSearch | `TETRAS Essential Tremor Rating Assessment Scale spiral handwriting item amplitude anchors cm Elble reliability` | PDT-14; surfaced Ondo 2021 (screened) |
| 9 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5618112/ | PDT-12 |
| 10 | 2026-09-26 | WebFetch | https://storage.googleapis.com/jnl-up-j-tohm-files/journals/1/articles/344/submission/proof/344-1-1126-1-10-20200514.pdf (PDF text extracted locally with pdftotext) | PDT-12 (full text) |
| 11 | 2026-09-26 | WebFetch | https://www.semanticscholar.org/paper/Tremor-amplitude-is-logarithmically-related-to-4-Elble-Pullman/4814fa2d17978eaf5c41d54e9574a0bf4d8d6ad9 (no content) | no content returned |
| 12 | 2026-09-26 | WebFetch | https://pubmed.ncbi.nlm.nih.gov/16891320/ (blocked by reCAPTCHA) | blocked (reCAPTCHA) |
| 13 | 2026-09-26 | Europe PMC REST API | EXT_ID:16891320 AND SRC:MED | PDT-11 abstract |
| 14 | 2026-09-26 | Europe PMC REST API | DOI:"10.1002/mds.26565" | PDT-16 abstract |
| 15 | 2026-09-26 | Europe PMC REST API | DOI:"10.1371/journal.pone.0190223" | PDT-17 abstract |
| 16 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5741263/ | PDT-17 (full text) |
| 17 | 2026-09-26 | WebSearch | `Nackaerts "intensive amplitude training" micrographia SOS-test daily life writing transfer results lirias` | context for PDT-16 |
| 18 | 2026-09-26 | WebSearch | `Oliveira Gurd Nixon Marshall Passingham 1997 micrographia Parkinson's disease effect of providing external cues` | PDT-19; surfaced Bryant 2010 (screened) |
| 19 | 2026-09-26 | Europe PMC REST API | EXT_ID:9343118 AND SRC:MED ; EXT_ID:20554637 AND SRC:MED ; EXT_ID:22734114 AND SRC:MED | PDT-19, Bryant 2010, PDT-01 |
| 20 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC2169751/ (abstract only; scanned PDF not retrievable) | PDT-19 (abstract only) |
| 21 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5384257/ | Bryant 2010 (screened) |
| 22 | 2026-09-26 | Europe PMC REST API | DOI:"10.1177/1545968315601361" ; TITLE:"undershoot target size in handwriting" ; TITLE:"Auditory instructional cues benefit unimanual and bimanual drawing" | PDT-18; Van Gemmert 2003 and Ringenbach 2011 (screened) |
| 23 | 2026-09-26 | WebSearch | `systematic review handwriting interventions Parkinson's disease micrographia cueing training 2022 OR 2023 OR 2024 OR 2025` | PDT-20, PDT-21; Gardoni 2023, Collins 2024, Vorasoot 2020 (screened) |
| 24 | 2026-09-26 | WebSearch | `Thomas Lenka Pal 2017 handwriting analysis in Parkinson's disease current status and future directions micrographia prevalence` | PDT-03 |
| 25 | 2026-09-26 | Europe PMC REST API | DOI:"10.1016/j.jht.2023.08.004" ; EXT_ID:36964814 AND SRC:MED ; EXT_ID:37249793 AND SRC:MED ; DOI:"10.1002/mdc3.12552" | PDT-21, PDT-03; Gardoni 2023, Collins 2024 (screened) |
| 26 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC6174397/ | PDT-03, PDT-02 |
| 27 | 2026-09-26 | Europe PMC REST API | TITLE:"Micrographia in Parkinson" AND PUB_YEAR:1972 ; AUTH:"McLennan JE" AND TITLE:micrographia | PDT-02 (no abstract indexed) |
| 28 | 2026-09-26 | WebSearch | `McLennan 1972 micrographia Parkinson's disease "95 patients" OR "15%" OR "5%" prevalence Schwab` | PDT-02 (secondary only) |
| 29 | 2026-09-26 | WebSearch | `Letanneux 2014 "From micrographia to Parkinson's disease dysgraphia" consistent progressive micrographia prevalence` | surfaced PDT-05 and PDT-06; Letanneux 2014 not accessible |
| 30 | 2026-09-26 | WebFetch | https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2019.00403/full | PDT-05 |
| 31 | 2026-09-26 | WebFetch | https://d-nb.info/1265368090/34 (PDF text extracted locally with pdftotext; Eklund et al. 2022 J Neural Transm) | PDT-06 (full text) |
| 32 | 2026-09-26 | Europe PMC REST API | TITLE:"Micrographia on free writing versus copying tasks" ; TITLE:"Kinematic analysis of dopaminergic effects on skilled handwriting" | PDT-04; Tucha 2006 (screened) |
| 33 | 2026-09-26 | WebSearch | `action tremor Parkinson's disease prevalence kinetic postural re-emergent tremor frequency Hz cohort study` | PDT-08 |
| 34 | 2026-09-26 | WebSearch | `Parkinson's disease spiral drawing digitizing tablet tremor amplitude frequency kinetic tremor compared essential tremor` | Lin 2018 (screened) |
| 35 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC7757606/ | PDT-08 |
| 36 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5845296/ | Lin 2018 (screened) |
| 37 | 2026-09-26 | WebSearch | `"handwriting" tremor Parkinson's disease tablet spectral analysis tremor frequency amplitude during writing mm` | PDT-10 |
| 38 | 2026-09-26 | WebSearch | `Jankovic re-emergent tremor Parkinson's disease latency frequency prevalence 1999 JNNP` | PDT-09 |
| 39 | 2026-09-26 | WebFetch | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0097614 | PDT-10 |
| 40 | 2026-09-26 | WebFetch | https://tremorjournal.org/articles/10.5334/tohm.520 | single case report (screened) |
| 41 | 2026-09-26 | Europe PMC REST API | TITLE:"spectral features of kinetic tremor" ; TITLE:"Re-emergent tremor of Parkinson" AND AUTH:"Jankovic J" ; kinetic tremor handwriting spectral Parkinson digitized motor scales ; "re-emergent tremor" Jankovic 1999 | no relevant hits |
| 42 | 2026-09-26 | WebFetch | https://scholars.houstonmethodist.org/en/publications/re-emergent-tremor-of-parkinsons-disease/ | PDT-09 |
| 43 | 2026-09-26 | Europe PMC REST API | DOI:"10.1002/mds.870110113" ; DOI:"10.1002/mds.23808" ; DOI:"10.1016/0165-0270(90)90140-B" | PDT-13; Haubenberger 2011, Elble 1990 (screened) |
| 44 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4117681/ | Haubenberger 2011 (screened) |
| 45 | 2026-09-26 | WebSearch | `Louis Ford Pullman Baron 1998 "How normal is normal" mild tremor multiethnic cohort normal subjects Archimedes spiral` | Louis 1998 normal subjects (screened) |
| 46 | 2026-09-26 | Europe PMC REST API | TITLE:"How normal is" AND TITLE:"mild tremor" ; EXT_ID:21442657 AND SRC:MED ; EXT_ID:30954661 AND SRC:MED ; DOI:"10.1002/mds.870130508" | Louis 1998/2011/2019, community ET (screened) |
| 47 | 2026-09-26 | WebFetch | https://tremorjournal.org/articles/10.5334/tohm.665 | PDT-14 (spiral/handwriting anchor wording) |
| 48 | 2026-09-26 | WebSearch | `Elble 2016 "The Essential Tremor Rating Assessment Scale" Journal of Neurology and Neuromedicine TETRAS performance items spiral handwriting amplitude` | PDT-14 context |
| 49 | 2026-09-26 | WebSearch | `physiological tremor hand displacement amplitude micrometers RMS 8-12 Hz surgeons Riviere hand-held instrument tremor characteristics` | PDT-15; Riviere 1998 (screened) |
| 50 | 2026-09-26 | Europe PMC REST API | EXT_ID:1248981 AND SRC:MED ; TITLE:"Characteristics of physiologic tremor in young and elderly adults" ; TITLE:"Comparison of Baseline Tremor Under Various Microsurgical Conditions" | PDT-15; Elble 2003, Wells 2013 (screened) |
| 51 | 2026-09-26 | WebFetch | https://publications.ri.cmu.edu/storage/publications/pub_files/pub3/riviere_cameron_1998_1/riviere_cameron_1998_1.pdf (PDF text extracted locally) | Riviere 1998 (screened) |
| 52 | 2026-09-26 | Europe PMC REST API | DOI:"10.1038/s41598-025-14196-5" | PDT-25 |
| 53 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC12325923/ | PDT-25 (full text) |
| 54 | 2026-09-26 | WebSearch | `SteadyScrib pen tremor evidence study` | PDT-26 |
| 55 | 2026-09-26 | WebSearch | `Sabari 2019 adapted feeding utensils Parkinson's related or essential tremor Liftware weighted spoon American Journal of Occupational Therapy` | PDT-24 |
| 56 | 2026-09-26 | WebSearch | `Pathak 2014 noninvasive handheld assistive device accommodate essential tremor pilot study Liftware Movement Disorders` | PDT-23 |
| 57 | 2026-09-26 | Europe PMC REST API | DOI:"10.1002/mds.25796" ; DOI:"10.5014/ajot.2019.030759" ; PMCID:PMC7313572 ; PMCID:PMC7452531 | PDT-23, PDT-24; Ryden 2020, Zajki-Zechmeister 2020 (screened) |
| 58 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4156033/ | PDT-23 (full text) |
| 59 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC7313572/ | Ryden 2020 (screened) |
| 60 | 2026-09-26 | WebFetch | https://www.cda-amc.ca/sites/default/files/pdf/EH0030_liftware_self_stabilizing_eating_utensils_for_individuals_with_hand_tremor-e.pdf (HTTP 403) | HTTP 403 |
| 61 | 2026-09-26 | WebSearch | `Liftware Steady Parkinson's disease tremor study patients spoon evaluation results rest tremor` | no additional Liftware-in-PD trial found |
| 62 | 2026-09-26 | WebSearch | `weighted utensils essential tremor study tremor amplitude reduction inertial loading randomized` | Meshack 2002, Ma 2009 (screened) |
| 63 | 2026-09-26 | Europe PMC REST API | EXT_ID:12194619 AND SRC:MED ; TITLE:"effect of eating utensil weight on functional arm movement" ; TITLE:"inertial loading on wrist postural tremor in essential tremor" | PDT-22; Meshack 2002, Ma 2009 (screened) |
| 64 | 2026-09-26 | WebSearch | `weighted pen essential tremor handwriting study grip diameter built-up pen tremor writing` | commercial pages only; no study found |
| 65 | 2026-09-26 | WebSearch | `pen grip diameter handwriting older adults Parkinson's disease grip force writing performance study` | surfaced PDT-27 and Zaman 2018 |
| 66 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5333892/ | PDT-27 (full text) |
| 67 | 2026-09-26 | WebFetch | https://www.neurores.org/index.php/neurores/article/view/493/472 | Zaman 2018 (screened) |
| 68 | 2026-09-26 | WebSearch | `PaHaW Parkinson's disease handwriting database Drotar license request Wacom Intuos sampling rate pressure azimuth altitude` | PDT-28 |
| 69 | 2026-09-26 | WebSearch | `NewHandPD HandPD dataset Pereira smart pen BiSP signals spirals meanders UNESP download` | PDT-29 |
| 70 | 2026-09-26 | WebFetch | https://wwwp.fc.unesp.br/~papa/pub/datasets/Handpd/ | PDT-29 |
| 71 | 2026-09-26 | WebFetch | https://arxiv.org/abs/2411.03044 | PDT-28 (no access terms in abstract) |
| 72 | 2026-09-26 | WebSearch | `PaHaW database bdalab license agreement download "PaHaW" Brno` | PDT-28 |
| 73 | 2026-09-26 | WebSearch | `UCI "Parkinson Disease Spiral Drawings Using Digitized Graphics Tablet" dataset Isenkul license` | PDT-30 |
| 74 | 2026-09-26 | WebFetch | https://archive.ics.uci.edu/dataset/395/parkinson+disease+spiral+drawings+using+digitized+graphics+tablet | PDT-30 |
| 75 | 2026-09-26 | WebFetch | https://bdalab.utko.fekt.vut.cz/ | PDT-28 (access terms, 150 Hz) |
| 76 | 2026-09-26 | WebFetch | http://archive.ics.uci.edu/ml/datasets/Parkinson+Disease+Spiral+Drawings+Using+Digitized+Graphics+Tablet | PDT-30 |
| 77 | 2026-09-26 | curl download + local inspection | https://archive.ics.uci.edu/static/public/395/parkinson+disease+spiral+drawings+using+digitized+graphics+tablet.zip (readme + timestamp/coordinate inspection) | PDT-30 (file inspection) |
| 78 | 2026-09-26 | WebSearch | `TETRAS minimal clinically important difference performance subscale essential tremor anchor-based patient global impression` | Ondo 2026 MCID (screened) |
| 79 | 2026-09-26 | WebSearch (NOT EXECUTED: session web-search budget exhausted) | `NewHandPD smart pen BiSP sampling rate channels microphone finger grip axial pressure tilt acceleration Pereira SIBGRAPI 2016 convolutional handwritten dynamics` | not executed (budget) |
| 80 | 2026-09-26 | Europe PMC REST API | DOI:"10.1002/mdc3.70807" ; TITLE:"Essential tremor frequency decreases with time" ; TITLE:"Handwritten dynamics assessment through convolutional neural networks" | Ondo 2026, Elble 2000, Pereira 2018 (screened) |
| 81 | 2026-09-26 | curl + local inspection | https://wwwp.fc.unesp.br/~papa/pub/datasets/Handpd/ (page text) ; https://wwwp.fc.unesp.br/~papa/pub/datasets/Handpd/NewPatients/PatientSignal.zip (372 files: header Samplerate, Pen, column count) | PDT-29 (file inspection) |
| 82 | 2026-09-26 | curl + pdftotext | http://sibgrapi.sid.inpe.br/col/sid.inpe.br/sibgrapi/2016/07.08.22.47/doc/opf-sibgrapi16.pdf (BiSP channel list) | PDT-29 (channel list) |
| 83 | 2026-09-26 | Europe PMC REST API | (handwriting) AND (kinetic tremor) AND (Parkinson) AND (spectral) AND PUB_YEAR:[2021 TO 2024] | no relevant hits |
| 84 | 2026-09-26 | WebFetch | https://www.sciencedirect.com/science/article/abs/pii/S0966636222005148 (HTTP 403) | HTTP 403 |
| 85 | 2026-09-26 | Europe PMC REST API | TITLE:"Using Portable Transducers to Measure Tremor Severity" ; TITLE:"Reliability of a new scale for essential tremor" | Elble & McNames 2016 (screened); PDT-14 |
| 86 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4872171/ | Elble & McNames 2016 (screened) |
| 87 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4157921/ | PDT-14 (full text) |
| 88 | 2026-09-26 | WebFetch | https://doi.org/10.3390/disabilities5040093 -> https://www.mdpi.com/2673-7272/5/4/93 (HTTP 403) | HTTP 403 |
| 89 | 2026-09-26 | Europe PMC REST API | TITLE:"Effects of handwriting exercise on functional outcome in Parkinson disease" ; (handwriting exercise) AND (Parkinson) AND (randomized) AND JOURNAL:"J Clin Neurosci" ; DOI:"10.3390/disabilities5040093" ; TITLE:"Exaggerated Spatial Cueing" | Vorasoot 2020 (screened) |
| 90 | 2026-09-26 | Crossref REST API | https://api.crossref.org/works/10.3390/disabilities5040093 | PDT-20 abstract |
| 91 | 2026-09-26 | Europe PMC REST API | TITLE:"Consensus Statement on the classification of tremors" | PDT-07 |
| 92 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC6530552/ | PDT-07 (full text) |
| 93 | 2026-09-26 | WebFetch | https://steadyscrib.com/products/the-steadyscrib-parkinsons-pen-set | PDT-26 |
| 94 | 2026-09-26 | WebFetch | https://news.northwestern.edu/stories/2023/03/students-design-pen-for-parkinsons-patients | PDT-26 |
| 95 | 2026-09-26 | WebFetch | https://www.sciencedirect.com/science/article/abs/pii/0022510X72900020 (HTTP 403) | HTTP 403 |
| 96 | 2026-09-26 | Semantic Scholar Graph API + Crossref REST API | DOI 10.1016/0022-510X(72)90002-0 (abstract elided by publisher) | PDT-02 (abstract elided) |
| 97 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC6174397/ (second pass: verbatim quotes) | PDT-02, PDT-03 (verbatim) |
| 98 | 2026-09-26 | WebFetch | https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2019.00403/full (second pass: verbatim quotes) | PDT-05 (verbatim) |
| 99 | 2026-09-26 | WebFetch | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0097614 (second pass: verbatim quotes) | PDT-10 (verbatim) |
| 100 | 2026-09-26 | Crossref REST API | https://api.crossref.org/works/10.5014/ajot.2019.030759 ; https://api.crossref.org/works/10.1016/j.jht.2023.08.004 | PDT-24, PDT-21 |
| 101 | 2026-09-26 | Europe PMC REST API | DOI:"10.3389/fneur.2019.00403" ; EXT_ID:33384882 AND SRC:MED ; DOI:"10.1136/jnnp.67.5.646" ; PMCID:PMC5333892 ; EXT_ID:26874552 AND SRC:MED ; TITLE:"A new computer vision-based approach to aid the diagnosis of Parkinson" ; DOI:"10.1371/journal.pone.0097614" ; DOI:"10.7916/D89S20H7" ; AUTH:"Papa JP" AND Parkinson AND PUB_YEAR:2016 (citation verification) | citation checks (multiple rows) |
| 102 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC1736624/ (Jankovic 1999 abstract verbatim) | PDT-09 (verbatim) |
| 103 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4156033/ (second pass: TRS change-score definition, Table 2) | PDT-23 (verbatim) |
| 104 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC7757606/ (second pass: action-tremor definition verbatim) | PDT-08 (verbatim) |
| 105 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC5741263/ (second pass: normalized-jerk formula and tablet specification verbatim) | PDT-17 (verbatim) |
| 106 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC12325923/ (second pass: sampling-rate and dataset sentences verbatim) | PDT-25 (verbatim) |

### 1.2 Retrieved and screened but not ledgered (30-row cap)

These are listed so the evidence is not lost. Access level is shown in brackets.

- Tucha et al. 2006, J Neural Transm, doi:10.1007/s00702-005-0346-9 [abstract]. 27 PD vs 27 controls, on usual medication and after withdrawal. Off medication, handwriting kinematics were markedly disturbed. Medication improved them but did not normalise them.
- Louis, Ford, Wendt, Cameron 1998, Mov Disord, doi:10.1002/mds.870130508 [abstract]. 73 community ET cases: 49.3% asymptomatic, 91.8% never prescribed tremor medication, mean total tremor score 17.8/36, kinetic tremor worse than postural in 98.6%.
- Louis et al. 2019, J Neurol Sci, doi:10.1016/j.jns.2019.03.019 [abstract]. 1158 normal adults aged 40-98: 98.9% had a spiral score >0, but only 1.8-8.5% had a rating of 1.5 or more (19.6% in left-hand spirals of men aged 70+).
- Louis, Ford, Pullman, Baron 1998, Arch Neurol, doi:10.1001/archneur.55.2.222 [abstract]. 96% of 103 normal subjects had mild, clinically detectable tremor.
- Elble 2003, Clin Neurophysiol, doi:10.1016/s1388-2457(03)00006-3 [abstract]. About 8% of young and elderly controls have an EMG-acceleration pattern indistinguishable from mild ET.
- Elble 2000, Neurology, doi:10.1212/wnl.55.10.1547 [abstract]. 44 ET patients (mean age 68): tremor frequency 5.79 +/- 1.32 Hz, falling 0.06-0.08 Hz per year (frequency = -0.061 x age + 9.94).
- Elble & McNames 2016, Tremor Other Hyperkinet Mov, doi:10.7916/d8dr2vcc [full text]. Tablets resolve 0.005 mm but are accurate only to +/-0.25 mm, sample at >=100 Hz, and cannot measure physiological tremor. Physiological hand acceleration is 3-33 cm/s^2 (half peak-to-peak, 14 cm from the wrist); this ledger derives ~0.005-0.13 mm half peak-to-peak displacement at 8-12 Hz.
- Elble 2018, Tremor Other Hyperkinet Mov, doi:10.5334/tohm.455 [full text]. log T = alpha x R + beta, with alpha ~0.4-0.6 and beta ~-1 to -3. With alpha = 0.5, a 1-point rating fall is ~68% less amplitude.
- Ondo, Wagle Shukla, Ondo 2021, Tremor Other Hyperkinet Mov, doi:10.5334/tohm.665 [full text]. 94 spirals and 64 handwriting samples rated by 21 raters. Agreement was good for spirals and poor for handwriting. Anchor wording is quoted in PDT-14.
- Ondo et al. 2026, Mov Disord Clin Pract, doi:10.1002/mdc3.70807 [abstract]. Anchor-based MCIDs for TETRAS ADL composites: mADL -6.2 and mADL11 -4.1 (patient-anchored). No handwriting-specific MCID was found.
- Van Gemmert, Adler, Stelmach 2003, JNNP, doi:10.1136/jnnp.74.11.1502 [abstract]. 13 PD vs 13 controls. Stroke size and duration were modulated independently up to 1.5 cm, with progressive undershooting above 1.5 cm.
- Bryant et al. 2010, Clin Rehabil, doi:10.1177/0269215510371420 [full text]. 11 men with PD practised with 10 mm parallel or grid lines. Three-word length rose from 17.83 to 23.36 cm (parallel) and 22.65 cm (grid). Immediate effect only.
- Collins et al. 2024, Ir J Med Sci, doi:10.1007/s11845-023-03404-8 [abstract]. 48 community PwP, 6-week remote programme. SOS-PD improved: overall quality p=0.001, legibility p=0.009, letter size p=0.012, fluency p=0.001. Pre/post design, no control group.
- Vorasoot et al. 2020, J Clin Neurosci, doi:10.1016/j.jocn.2019.08.119 [abstract]. RCT, n=46, 4-week practice book. Handwriting-test time fell 16.16% vs rising 3.63% in controls (p<0.001).
- Zaman & Stegemöller 2018, J Neurol Res 8(3) [full text]. 22 PD and 11 controls. Lined paper (1 or 2 cm) did not normalise letter height when writing large and/or fast; writing fast at 2 cm reduced height by 1.07 +/- 1.52 mm.
- Ringenbach et al. 2011, Hum Mov Sci, doi:10.1016/j.humov.2010.08.018 [abstract]. In line drawing (15 PD), auditory and verbal cues reduced timing and amplitude variability more than visual cues.
- Gardoni et al. 2023, Neurol Sci, doi:10.1007/s10072-023-06752-6 [abstract]. Scoping review of 8 studies, mostly at high risk of bias. Handwriting-specific training improved amplitude; non-specific training improved speed.
- Meshack & Norman 2002, Clin Rehabil, doi:10.1191/0269215502cr521oa [abstract]. Randomised repeated-measures study, 16 PD. A 248 g spoon or a 470 g wrist cuff, compared with a 108 g spoon, did not change postural tremor amplitude or frequency.
- Ma et al. 2009, Clin Rehabil, doi:10.1177/0269215509342334 [abstract]. 18 PD and 18 controls; 35 vs 85 vs 135 g spoons. The light spoon gave fewer movement units and higher peak velocity.
- Ryden et al. 2020, Ann Indian Acad Neurol, doi:10.4103/aian.aian_251_19 [full text]. 10 PD (8 analysed) used a stabilising spoon, on vs off. Less rice was transferred with the device on in the 60-s task (p=0.0138), and the authors made no recommendation for PD.
- Riviere, Rader, Thakor 1998, IEEE Trans Biomed Eng 45(7):839 [full text]. Bench cantilever with piezo tip actuation, driven by recorded physiological tremor: RMS tip motion in the 6-16 Hz band fell by 67% (25 tests).
- Haubenberger et al. 2011, Mov Disord, doi:10.1002/mds.23808 [author manuscript]. 200 Hz tablet; log tablet measure vs Bain-Findley 0-10 rating slope 0.2436 (space).
- Lin et al. 2018, BMC Neurol (PMC5845296) [full text]. 12 ET + 12 PD on a 50 Hz Cintiq. Spiral indices correlated with a visual rating (R up to 0.973). No mm amplitudes.
- Zajki-Zechmeister et al. 2020, Heliyon, doi:10.1016/j.heliyon.2020.e04702 [abstract]. A pen-shaped inertial sensor correlated with MDS-UPDRS (r=0.638-0.779) and TETRAS (r=0.597-0.704).
- Not accessible: Letanneux et al. 2014, Mov Disord, doi:10.1002/mds.25990 (paywalled). A search-engine summary claimed prevalence '30-60%... about 70%'; this was not verified and is not used.

## 2. Critical synthesis

### 2.1 Scale check

- A +/-0.5 mm-per-axis nib fully cancels only tremor of 1 mm p-p or less per axis.
- Above that the nib clips. The best-case reduction is 1 mm divided by A_pp per axis: 50% at 2 mm, 25% at 4 mm, 10% at 10 mm (analytical derivation, this note).
- Every writing impairment below is judged against this ceiling.

### 2.2 What a +/-0.5 mm local correction could address, and for whom

**Essential tremor (ET).** Only one source gives a per-patient displacement distribution: PDT-12 (18 drug-free ET trial volunteers, tablet spirals, averaged over both hands and two spiral sizes).
- Geometric mean tremor is 2.0 mm p-p.
- A log-normal fit gives about 18% of patients at 0.5 mm p-p or less, 32% at 1 mm or less, 50% at 2 mm or less and 68% at 4 mm or less. The spread (sigma_log10 about 0.65) is derived here from the published geometric and arithmetic means.
- The same paper's regression is log10 T[cm] = 0.6 x FTM - 1.27. It implies an FTM spiral rating of 1 ("slight") is already about 2.1 mm p-p, and a rating of 0.5 about 1.1 mm.
- Full cancellation is therefore available only for tremor at or below the threshold of clinical visibility.

For handwriting, one rating point equals about 2.6-2.8x amplitude (PDT-11), so a 50% reduction is worth about 0.7 rating points. The tablet minimum detectable change is 51% (PDT-12), and a clipped correction can exceed that only when tremor is about 2 mm p-p or less on one axis. Writing tremor correlates weakly with postural tremor (r<0.6; PDT-13), so spiral and posture numbers are only proxies.

**Best estimate of the addressable fraction in ET.** For trial-type ET measured off medication:
- About 30% (plausible range 15-50%, set by n=18 and the log-normal assumption) have tremor fully within +/-0.5 mm (1 mm p-p or less).
- About 50% could get at least a 50% reduction (2 mm p-p or less).
- The rest get less than 50%, which is at or below measurement noise.

The same fractions expressed as peak amplitude: about 18% have 0.25 mm peak or less, 32% have 0.5 mm or less, 50% have 1 mm or less and 68% have 2 mm or less. The estimates below 0.5 mm p-p extrapolate beneath the tablets' +/-0.25 mm accuracy and should not be relied on. Community ET is milder and mostly untreated (Louis 1998, screened). That would raise the in-range fraction, but among people with little writing disability.

**Parkinson's disease (PD).**
- In PD, rest tremor "almost always diminishes" during goal-directed movement (PDT-07).
- Kinetic tremor of any grade is seen in about 51-52% of PD patients on clinical items (PDT-08).
- Re-emergent tremor appears after about 9 s of holding, at about 5.5 Hz (PDT-09).
- In a small OFF-state study, only the 3 of 10 patients with rest tremor showed 4.4-8 Hz peaks while writing (PDT-10).
- No retrieved study reports PD writing-tremor displacement in mm, so the addressable PD fraction cannot be estimated.

Plausible PD targets are tremor-dominant users during pen-down pauses, hovering and slow strokes. That subgroup also has less micrographia (PDT-03).

**Non-clinical users.** Physiological tremor is about 30 um RMS (about 85 um p-p) at 8-12 Hz (PDT-15, PDT-07). That is well inside the stroke but below tablet accuracy and normally invisible. Normal adults' spirals are almost always rated "mild" (screened). Cancelling physiological tremor is easy but probably imperceptible. Tremor enhanced by fatigue or anxiety is the only non-clinical case likely to matter, and its size during writing is unquantified.

### 2.3 What requires cueing or practice instead

Micrographia is a failure of scaling across a sequence of strokes, not local noise:
- About 50% of clinic PD patients by test and 63% by history (PDT-01).
- 1-44% depending on free vs copied writing (PDT-04).
- 66% progressive in the OFF state, with stroke length falling from 18.97 to 14.61 mm over about 20 letters (PDT-05).
- Early-PD letters 4.3 vs 5.0 mm, 14% smaller (PDT-06).

Medication restores letter size inconsistently (about 50%; PDT-03), and size is unrelated to dose or levodopa use (PDT-01, PDT-06). A nib that enlarges strokes by up to 0.5 mm would have to infer the intended size and write for the user. That is an unsupported hypothesis and could undermine relearning.

Practice and cues are what the evidence supports:
- Intensive amplitude training (30 min/day, 5 days/week, 6 weeks) gave 7-17% size gains, retained at 6 weeks with transfer (PDT-16). The cost was longer strokes and higher normalized jerk (PDT-17).
- Visual target lines help at 1.0 cm but shrink writing at 0.6 cm (PDT-18).
- Verbal "big" cues and dot cues enlarge writing by slowing it (PDT-19).
- Daily diary practice on 10 mm lines gave large within-group amplitude gains (d about 0.8-1.1). Diverging lines added little (PDT-20).
- Rhythmic auditory cues shortened letter cycles (0.807 to 0.70 s) and reduced extensor EMG, in only 8 patients (PDT-21).

Outcomes must track fluency and speed as well as size. The SOS-test minimum detectable change is 2.2 points (PDT-27).

### 2.4 Mass, grip and friction

- The only pen-specific study is a PD pilot: a weighted pen increased spatial variability (0.187 to 0.482) and temporal variability (PDT-21).
- Inertial loading reduces ET postural tremor (PDT-22), but with loads of 5-25% of maximum strength, far heavier than any pen.
- In PD, weighted utensils did not change tremor, and lighter spoons moved more smoothly (screened).
- Users rated a passive weighted spoon about as highly as Liftware (PDT-24).
- SteadyScrib's claims for weight, magnets and grip have no published data (PDT-26).
- No retrieved study tests grip diameter or writing-surface friction in PD or ET.

Keep the pen's mass and inertia close to a normal pen unless testing shows otherwise.

### 2.5 Separating PD, ET and non-clinical users

The three groups need different functions:
- ET users need tremor handling; their writing size is normal (PDT-06).
- PD users mainly need size and fluency cueing; tremor affects a minority.
- Non-clinical users need neither.

The pen cannot tell the groups apart reliably, and must not try. Frequency bands overlap (pathological 4-8 Hz, physiological 8-12 Hz; PDT-07). Micrographia separates PD from ET poorly (56.8% sensitivity, 78.6% specificity; PDT-06). The pen should offer modes the user chooses and adapt to the measured signal, never inferring or displaying a diagnosis. Studies should stratify by clinician diagnosis and by measured writing-tremor amplitude.

### 2.6 What the literature does not establish

1. The distribution of nib-level tremor displacement in natural handwriting for ET, PD or older adults. Only spirals (n=18) and acceleration spectra exist.
2. Intercepts linking TETRAS handwriting ratings to millimetres. The handwriting item also has poor rater agreement (PDT-14).
3. Whether reducing tremor by 1 mm p-p or less changes legibility, speed, fatigue or satisfaction.
4. PD writing-tremor prevalence and amplitude by subtype and medication state.
5. Whether active correction interferes with motor learning or the user's sense of control.
6. Effects of pen mass, grip diameter and friction on ET writing.
7. Any human evidence for a tremor-cancelling pen. Tironi 2025 is simulation and bench work only (PDT-25). Liftware evidence concerns spoons, and severe tremor was excluded (PDT-23).

### 2.7 Decisive measurements

1. **Writing-tremor distribution.** Measure nib displacement (p-p and RMS per axis, 3-12 Hz) during sentence copying, free writing, spirals and dot-holding.
   - Groups: clinic and community ET; tremor-dominant and akinetic-rigid PD, ON and OFF medication; age-matched controls.
   - Instrumentation: at least 200 Hz and 0.05 mm accuracy, e.g. motion capture or a calibrated high-accuracy tablet (standard tablets are only +/-0.25 mm).
   - Report the fraction of each group at or below 0.25, 0.5, 1, 2 and 4 mm p-p.
2. **Rating-to-mm calibration** for TETRAS handwriting and spiral items.
3. **Separability** of voluntary stroke content from tremor in the spectrum, per user.
4. **Perceptual threshold:** blinded legibility ratings of samples with 25%, 50% and 100% of tremor synthetically removed.
5. **Device on/off crossover** with blinded outcomes (SOS score, TETRAS handwriting, nib mm, jerk), including effects on learning in cueing modes.
