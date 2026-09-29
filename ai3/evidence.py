"""Proposed ledger rows of study S (results/ai3/evidence_rows.csv), with the exact 23-column header of docs/evidence.csv.

Id ranges given to the study: EML-85..99, PDT-85..89, CON-90..94, HAP-130..134.  Only sources actually opened are
listed; the access level says what was read.  Derived rows (this study's CALC/SIM) are filled from the result caches.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

HEADER = ["id", "topic", "citation", "year", "doi_or_url", "source_type", "evidence_class", "access_level",
          "task_or_setup", "participants_or_bench", "comparator", "key_quantitative_findings", "units_and_conditions",
          "locator", "limitations", "relevance_to_design", "transferability", "transferability_reason",
          "design_implication", "retrieved", "search_query", "stream", "lead_verification"]

RETRIEVED = "2026-09-29"


def _row(**kw) -> List[str]:
    kw.setdefault("retrieved", RETRIEVED)
    kw.setdefault("lead_verification", "")
    return [str(kw.get(h, "")) for h in HEADER]


LIT = [
    _row(id="EML-85", topic="Real misspellings for training and testing a spelling-error model (Birkbeck corpus and Mitton's derived lists)",
         citation="Mitton R. Corpora of misspellings for download: 'birkbeck' (native-speaker section of the Birkbeck spelling error corpus), 'holbrook', 'aspell', 'wikipedia'. Birkbeck, University of London",
         year="2026 (page); corpus 1985-", doi_or_url="https://titan.dcs.bbk.ac.uk/~roger/corpora.html ; full corpus: Oxford Text Archive 0643 (https://ota.bodleian.ox.ac.uk/repository/xmlui/handle/20.500.12024/0643, not reachable from here)",
         source_type="dataset", evidence_class="physical human study (collected misspellings)", access_level="full text (download page and data files)",
         task_or_setup="Misspellings from spelling tests and free writing, mostly handwritten; each target word with its misspellings",
         participants_or_bench="Schoolchildren, university students and adult literacy students (British or American writers)",
         comparator="n/a",
         key_quantitative_findings="birkbeck: 36,133 misspellings of 6,136 words; holbrook: 1,791 misspellings of 1,200 targets (with frequencies); aspell: 531 of 450; wikipedia: 2,455 of 1,922. Includes 'the efforts of young children and extremely poor spellers'; mostly non-words, some real-word errors",
         units_and_conditions="word pairs (target, misspelling)", locator="Download page text; files missp.dat, holbrook-missp.dat, aspell.dat, wikipedia.dat",
         limitations="No licence stated on the download page (OTA terms not checked: the OTA site timed out); lists of pairs without context (except holbrook); not diagnosed dyslexia",
         relevance_to_design="The spelling-error (channel) model of the physical spell checker is learned from these real misspellings (training target words only)",
         transferability="medium", transferability_reason="Real misspellings of native English writers, many poor spellers; not pen-recognised letters",
         design_implication="Train the error model on real misspellings, split by target word; use the error rates as the writer's prior",
         search_query="WebSearch 'Birkbeck spelling error corpus Oxford Text Archive licence'; curl titan.dcs.bbk.ac.uk/~roger/corpora.html and the .dat files",
         stream="EML"),
    _row(id="EML-86", topic="Real misspellings in running text by poor spellers (Holbrook, tagged)",
         citation="Holbrook D. English for the Rejected. Cambridge University Press, 1964; passages tagged with every misspelling and its target by R. Mitton (holbrook-tagged.dat)",
         year="1964", doi_or_url="https://titan.dcs.bbk.ac.uk/~roger/holbrook-tagged.dat", source_type="dataset",
         evidence_class="physical human study (children's writing)", access_level="full text (data file)",
         task_or_setup="Free writing (and some copying) of secondary-school children in their next-to-last school year; misspellings tagged <ERR targ=...>",
         participants_or_bench="19 children (named sections)", comparator="n/a",
         key_quantitative_findings="25,754 tokens, 2,600 tagged errors; parsed here: 22,618 correctly spelled words and 2,577 misspelled word units (10.2 % of words; per child 3-22 %)",
         units_and_conditions="words; error share of words", locator="holbrook-tagged.dat; parsing ai3/data.py, ai3/stage_spell.py",
         limitations="1960s British schoolchildren of low attainment, not diagnosed dyslexia; licence not stated; the passages are copyright CUP (used for evaluation only, not redistributed)",
         relevance_to_design="The only openly downloadable English corpus found with real misspellings IN CONTEXT; used to tune (8 children) and test (11 children) the in-writing detector",
         transferability="medium", transferability_reason="Real misspellings in real sentences; old, British, children; letters known exactly (not recognised)",
         design_implication="Set detection thresholds and the writer's error prior on real in-context errors",
         search_query="curl titan.dcs.bbk.ac.uk/~roger/holbrook-tagged.dat", stream="EML"),
    _row(id="EML-87", topic="How people with dyslexia misspell: error types, real-word errors, first letter",
         citation="Pedler J. Computer Correction of Real-word Spelling Errors in Dyslexic Text. PhD thesis, Birkbeck, University of London, 2007",
         year="2007", doi_or_url="https://www.dcs.bbk.ac.uk/site/assets/files/1025/pedler.pdf", source_type="thesis",
         evidence_class="corpus analysis", access_level="full text",
         task_or_setup="Corpus of dyslexic writing: word-processed homework (unchecked), Holbrook compositions, office documents, essays, typing experiment, bulletin boards; errors marked up",
         participants_or_bench="Several dyslexic writers (the author's daughter, a dyslexic student, online sources); Holbrook's children as 'likely dyslexic today'",
         comparator="Damerau 1964 (80 % single-error misspellings)",
         key_quantitative_findings="Initial samples: 3,134 words, 636 errors (20 % of words), 577 distinct: simple (one letter) 53 %, multi-letter 39 %, word-boundary 8 %; real-word 17 %; first letter correct 95 %. Whole corpus: 21,524 words, 2,654 errors (12 %), real-word 820 (31 %), word-boundary 152",
         units_and_conditions="counts and shares of errors", locator="s1.2.1-1.2.2, Table 1.1 (p 18-21); s3.1.5, Table 3.1 (p 46)",
         limitations="Small, mixed and partly spell-checked sources; not openly released as a dataset",
         relevance_to_design="Realistic error rates for simulated dyslexic writers (12-20 % of words); many errors are multi-letter and 17-31 % are real words, which no letter-level checker can see",
         transferability="high", transferability_reason="English dyslexic writing, the target population",
         design_implication="Use 10-20 % misspelled words as the design range; real-word errors need context (right context arrives one word later)",
         search_query="WebSearch 'Pedler dyslexic real-word spelling error corpus download Birkbeck'", stream="EML"),
    _row(id="EML-88", topic="Noisy-channel spelling correction with generic string-to-string edits",
         citation="Brill E, Moore RC. An improved error model for noisy channel spelling correction. Proc. 38th ACL, 2000, pp 286-293",
         year="2000", doi_or_url="https://aclanthology.org/P00-1037", source_type="conference", evidence_class="numerical evaluation on data",
         access_level="full text", task_or_setup="Error model P(s|w) over partitions into edits alpha->beta with context windows; trie over the dictionary; 10,000 common English misspellings, 80/20 split; 200,000-word dictionary",
         participants_or_bench="n/a (corpus)", comparator="Church & Gale weighted Damerau-Levenshtein (CG)",
         key_quantitative_findings="1-best 87.0 % (single edits) and 89.5 % (CG) -> 93.6 % (window 3-4) without position; 95.0 % with position (52 % relative error reduction vs CG); with a trigram language model 74 % error reduction vs CG",
         units_and_conditions="percentage of misspellings whose correction is ranked first (per type)", locator="s5.1 Tables 1-2; s5.2 Figure 1; Conclusions",
         limitations="Typing and cognitive errors of general users; isolated words (left context only with the language model)",
         relevance_to_design="The channel model used here (segment edits with one letter of context, dictionary trie, left-context language model)",
         transferability="high", transferability_reason="Same algorithmic problem", design_implication="Model multi-letter edits; search the lexicon with a trie",
         search_query="curl aclanthology.org/P00-1037.pdf; pdftotext", stream="EML"),
    _row(id="EML-89", topic="The noisy-channel spelling corrector (confusion matrices, prior x channel)",
         citation="Kernighan MD, Church KW, Gale WA. A spelling correction program based on a noisy channel model. COLING 1990, vol 2, pp 205-210",
         year="1990", doi_or_url="https://aclanthology.org/C90-2036", source_type="conference", evidence_class="numerical evaluation on data",
         access_level="full text", task_or_setup="Candidates within one insertion, deletion, substitution or reversal; P(c) P(t|c) with confusion matrices",
         participants_or_bench="3 judges on 564 triples", comparator="no-prior, no-channel and neither",
         key_quantitative_findings="The top-scoring candidate agreed with the majority of three judges in 87 % of the 329 cases where two judges agreed",
         units_and_conditions="agreement with judges", locator="Section on evaluation (p 3)", limitations="Typos from newswire, one-edit errors only",
         relevance_to_design="The prior x channel decision rule of the checker", transferability="high", transferability_reason="Same problem",
         design_implication="Combine a word prior and a learned channel; rank candidates by posterior",
         search_query="curl aclanthology.org/C90-2036.pdf; pdftotext", stream="EML"),
    _row(id="EML-90", topic="Cache language model (personalisation to recent text)",
         citation="Kuhn R, De Mori R. A cache-based natural language model for speech recognition. IEEE TPAMI 12(6):570-583, 1990",
         year="1990", doi_or_url="10.1109/34.56193", source_type="journal", evidence_class="numerical evaluation on data",
         access_level="bibliographic record only (Crossref); no abstract or text read",
         task_or_setup="A cache component raises the probability of recently used words", participants_or_bench="n/a", comparator="static n-gram",
         key_quantitative_findings="Not read (cited as the origin of the cache idea only)", units_and_conditions="n/a", locator="Crossref record",
         limitations="Only the bibliographic record was opened", relevance_to_design="The personalisation used in task 3 is a decaying unigram cache plus user bigrams",
         transferability="n/a", transferability_reason="Idea only", design_implication="Adapt the predictor to the user's own words",
         search_query="api.crossref.org/works/10.1109/34.56193", stream="EML"),
    _row(id="EML-91", topic="Public-domain journals as stand-ins for a user's own notes (personalisation test text)",
         citation="Project Gutenberg eBooks #1026 (Grossmith, The Diary of a Nobody, 1892), #57393 (Thoreau, Journal 01, 1837-1846), #11579 (Scott, Scott's Last Expedition, Volume I, 1913), #2024 (Jerome, Diary of a Pilgrimage, 1891)",
         year="1891-1913", doi_or_url="https://www.gutenberg.org/ebooks/1026 ; /57393 ; /11579 ; /2024", source_type="dataset (texts)",
         evidence_class="text data", access_level="full text", task_or_setup="Each journal split in halves: the first half is the user's history, the second is predicted word by word",
         participants_or_bench="4 authors (2 tuning, 2 test)", comparator="n/a", key_quantitative_findings="See the derived row EML-94",
         units_and_conditions="words", locator="Project Gutenberg plain-text files", limitations="Old literary diaries, not modern notes; each is one person's recurring vocabulary",
         relevance_to_design="The only openly licensed text found that is one person's own running notes", transferability="low",
         transferability_reason="Style and vocabulary differ from modern notes", design_implication="Measure personalisation on the user's own notes in the app (EXP-S14)",
         search_query="gutenberg.org/ebooks/search/?query=scott's last expedition | diary of a nobody | diary of a pilgrimage | journal henry david thoreau",
         stream="EML"),
    _row(id="EML-92", topic="Openly licensed dyslexic spelling-error data (French) and a review of dyslexic error corpora",
         citation="Bodard J, Jost C, Uzan G et al. Spelling errors made by people with dyslexia. Language Resources and Evaluation 57:293-322, 2023; data: Bodard J. Corpus DYS (NAKALA 10.34847/nkl.ced0370u) and Annotation des erreurs d'orthographe du corpus 'Corpus DYS' (10.34847/nkl.2ebcg834)",
         year="2022-2023", doi_or_url="10.1007/s10579-022-09603-6 ; https://doi.org/10.34847/nkl.ced0370u ; https://doi.org/10.34847/nkl.2ebcg834",
         source_type="journal + dataset", evidence_class="corpus analysis", access_level="dataset pages (NAKALA) opened; the article only through a search-engine summary (the publisher page needed JavaScript)",
         task_or_setup="78 typed texts by French-speaking people with dyslexia (7 by one adolescent, 71 by adults), every spelling error annotated with target, lemma and type",
         participants_or_bench="1 adolescent and adults with dyslexia (numbers not read)", comparator="n/a",
         key_quantitative_findings="Corpus DYS licence CC BY-NC-ND 4.0; annotation file (422 kB CSV) CC BY-NC-SA 4.0. The article reviews six studies (English, Spanish, German, French) (search summary)",
         units_and_conditions="n/a", locator="NAKALA dataset pages", limitations="French, typed; non-commercial licences; not used for the English models here",
         relevance_to_design="The only openly licensed dyslexic spelling-error data found; no openly licensed English dyslexic corpus was found",
         transferability="low", transferability_reason="Other language and orthography", design_implication="An English dyslexic error corpus is a gap: collect one with consent (EXP-S11)",
         search_query="WebSearch 'corpus of spelling errors written by people with dyslexia English dataset download'; curl doi.org/10.34847/...",
         stream="EML"),
    _row(id="HAP-130", topic="Students with learning disabilities using spelling checkers: correction rates and choosing suggestions",
         citation="MacArthur CA, Graham S, Haynes JB, DeLaPaz S. Spelling checkers and students with learning disabilities: performance comparisons and impact on spelling. Journal of Special Education 30(1):35-57, 1996",
         year="1996", doi_or_url="10.1177/002246699603000103", source_type="journal", evidence_class="physical human study",
         access_level="abstract only (Crossref; the ASU record)", task_or_setup="Study 1: 10 spelling checkers on 555 misspellings; Study 2: students correcting their errors with and without a checker",
         participants_or_bench="Study 1: writing of 55 students with LD, grades 5-8; Study 2: 27 students with LD, grades 6-8", comparator="no checker",
         key_quantitative_findings="Corrected 9 % of errors unaided and 37 % with a checker; checkers missed 26 % and 37 % of errors (other real words); the right suggestion offered for about 55 % of identified errors; when offered, students chose it 82 % of the time",
         units_and_conditions="share of spelling errors", locator="Abstract", limitations="Abstract only; word processors, not handwriting; 1990s checkers",
         relevance_to_design="Anchors the writer-response model of the physical cues: choosing a correct suggestion (0.82), fixing unaided (low)",
         transferability="medium", transferability_reason="Same population; typed, not handwritten", design_implication="Show the right word; a cue without a suggestion helps less",
         search_query="WebSearch 'MacArthur Graham Haynes DeLaPaz 1996 spelling checkers'; api.crossref.org/works/10.1177/002246699603000103",
         stream="HAP"),
    _row(id="HAP-131", topic="Vibrotactile detection during active hand movement (movement-related gating)",
         citation="Yildiz MZ, Toker I, Ozkan FB, Guclu B. Effects of passive and active movement on vibrotactile detection thresholds of the Pacinian channel and forward masking. Somatosensory & Motor Research 32(4):262-272, 2015",
         year="2015", doi_or_url="10.3109/08990220.2015.1091771 ; PMID 26443938", source_type="journal", evidence_class="physical human study",
         access_level="abstract only (PubMed)", task_or_setup="250 Hz vibration at the middle fingertip; 2-interval forced choice; hand still, moved passively or actively at 10-20 or 50-60 cm/s",
         participants_or_bench="10 healthy adults", comparator="hand still",
         key_quantitative_findings="Both passive and active movement raised thresholds (gating) at 50-60 cm/s; no significant change at 10-20 cm/s; active movement may gate less",
         units_and_conditions="detection threshold", locator="Abstract", limitations="Abstract only; fingertip shaker, not a pen LRA; speeds far above writing",
         relevance_to_design="Handwriting moves at about 3 cm/s (LIT CON-20), below the slow condition: a clear LRA tick while writing should not be masked by the movement",
         transferability="medium", transferability_reason="Same receptors; different stimulus site and device",
         design_implication="Assume a tick is noticed most of the time (0.9 nominal, 0.75 low); measure it (EXP-S13)",
         search_query="WebSearch 'movement-related gating tactile detection threshold during active finger movement'; eutils efetch PMID 26443938",
         stream="HAP"),
    _row(id="HAP-132", topic="Word prediction for students with severe spelling problems (handwriting vs word prediction)",
         citation="MacArthur CA. Word prediction for students with severe spelling problems. Learning Disability Quarterly 22(3):158-172, 1999",
         year="1999", doi_or_url="10.2307/1511283", source_type="journal", evidence_class="physical human study", access_level="abstract only (Crossref)",
         task_or_setup="Daily journal writing alternating handwriting, word processing and word prediction with speech synthesis; then a task demanding larger vocabulary",
         participants_or_bench="3 students with severe spelling problems", comparator="handwriting, word processing",
         key_quantitative_findings="Journal writing: no legibility difference, only one student spelled more words correctly with prediction; larger-vocabulary task: legibility and spelling improved for 2 of 3; students wrote 2-3 times slower with word prediction than by hand; prediction demanded attention and correct initial letters",
         units_and_conditions="words spelled correctly, legibility, speed", locator="Abstract", limitations="n = 3; abstract only; typed prediction",
         relevance_to_design="Prediction's value for poor spellers is spelling, not speed; it needs correct first letters (so spelling-tolerant completion matters)",
         transferability="medium", transferability_reason="Same population, other medium", design_implication="Offer completions sparingly (confidence threshold); tolerate misspelled starts",
         search_query="WebSearch 'MacArthur 1999 Word prediction for students with severe spelling problems'; api.crossref.org/works/10.2307/1511283",
         stream="HAP"),
    _row(id="HAP-133", topic="A real-word spellchecker for dyslexia and its user study (detection only vs suggestions)",
         citation="Rello L, Ballesteros M, Bigham JP. A spellchecker for dyslexia. ASSETS 2015, pp 39-47",
         year="2015", doi_or_url="10.1145/2700648.2809850 ; https://www.cs.cmu.edu/~jbigham/pubs/pdfs/2015/realcheck.pdf", source_type="conference",
         evidence_class="physical human study", access_level="full text",
         task_or_setup="Real Check (language model + dependency parser + Google n-grams) for Spanish real-word errors; 37 sentences written by people with dyslexia corrected under None / Error detection only / Error suggestions",
         participants_or_bench="34 adults (17 with dyslexia)", comparator="no help; common spellcheckers",
         key_quantitative_findings="17 % (English) and 21 % (Spanish) of dyslexic errors are real-word errors; people with dyslexia: writing accuracy 78.05 % (none) -> 89.83 % (detection only) -> 93.01 % (suggestions); correcting time 11.97 -> 15.44 -> 10.03 s; Pedler's English real-word detection recall 31.1 % / 23.4 %, precision 83.3 % / 77.2 %",
         units_and_conditions="% sentences correct; seconds", locator="Abstract; s1; s2.2; Table 2",
         limitations="Spanish; typed sentences in a correction task, not writing",
         relevance_to_design="Marking WHERE the error is already helps; suggestions help more and save time",
         transferability="medium", transferability_reason="Same population, other language and medium",
         design_implication="A cue on the suspect letter plus the suggestion in the app; real-word errors need context",
         search_query="WebSearch 'Rello Ballesteros Bigham 2015 A Spellchecker for Dyslexia'; curl cs.cmu.edu/~jbigham/pubs/pdfs/2015/realcheck.pdf",
         stream="HAP"),
    _row(id="EML-95", topic="Sensor-pen handwriting recognition datasets (OnHW, Fraunhofer IIS): availability, content and terms",
         citation="Fraunhofer IIS. Online Handwriting Recognition from Sensor-Enhanced Pens (OnHW datasets and publications), project page; README for the sequence-to-sequence and character-based OnHW datasets (Ott et al.)",
         year="2020-2022 (page accessed 2026)", doi_or_url="https://www.iis.fraunhofer.de/de/ff/lv/dataanalytics/anwproj/schreibtrainer/onhw-dataset.html ; https://www2.iis.fraunhofer.de/LV-OnHW/README.pdf",
         source_type="dataset documentation", evidence_class="dataset description", access_level="full text (project page and README; data not downloaded)",
         task_or_setup="STABILO DigiPen (two accelerometers, gyroscope, magnetometer, force) streamed to a tablet; single characters (OnHW-chars), words (OnHW-words500), equations; writer-dependent and writer-independent 5-fold splits",
         participants_or_bench="OnHW-chars: 119 writers, 31,275 upper- and lower-case letters (search summary of the ACM IMWUT 2020 paper; the page says the download is 895 MB)",
         comparator="n/a",
         key_quantitative_findings="Sensor data at 100 Hz; the 'Millis' timestamp is when the data were processed on the connected tablet; 'Only right-handed recordings are released' while files marked _L (left-handed writers) are also listed; writers could choose print or cursive; no licence or terms of use stated on the page or in the README",
         units_and_conditions="IMU and force time series; per-character and per-word labels", locator="Project page sections 'The OnHW-chars Dataset', 'Sensor Data', downloads list; README.pdf",
         limitations="No stated licence: not used here; IMU signals, not page positions, so the task-1 model (pen-path input) cannot use them directly; not tremor or dyslexia data",
         relevance_to_design="Candidate benchmark for the pen's own IMU-based recogniser and for writer-disjoint CER/WER (review R15)",
         transferability="medium", transferability_reason="A real sensor pen on paper, but a different sensor set and no patients",
         design_implication="Ask Fraunhofer IIS for terms before any use; record our own pen's data with a clear licence (EXP-S17)",
         search_query="WebSearch 'OnHW dataset Fraunhofer IIS online handwriting sensor-enhanced pen download licence'; curl of the project page (de) and README.pdf",
         stream="EML"),
    _row(id="EML-96", topic="Calibrating the confidence of a combined model: temperature scaling",
         citation="Guo C, Pleiss G, Sun Y, Weinberger KQ. On Calibration of Modern Neural Networks. ICML 2017 (PMLR 70:1321-1330); arXiv:1706.04599",
         year="2017", doi_or_url="https://arxiv.org/abs/1706.04599", source_type="journal/conference paper", evidence_class="machine-learning methods",
         access_level="abstract", task_or_setup="Post-hoc calibration methods on image and document classifiers",
         participants_or_bench="n/a", comparator="histogram binning, isotonic regression, Platt scaling variants",
         key_quantitative_findings="Modern networks are poorly calibrated; on most data sets temperature scaling, a one-parameter variant of Platt scaling, is 'surprisingly effective'",
         units_and_conditions="expected calibration error, NLL", locator="Abstract",
         limitations="Abstract only; calibration on one distribution does not guarantee it under a shift of writers or devices (review R18)",
         relevance_to_design="The spelling checker's combined P(misspelled) is calibrated by temperature scaling on the tuning children (rule W2) and checked on test children",
         transferability="medium", transferability_reason="General method; our model is a noisy-channel combination, not a deep classifier",
         design_implication="Calibrate after combining the recognition, language and error models; re-check per user and device",
         search_query="arxiv.org/abs/1706.04599", stream="EML"),
]


def derived(res: Dict) -> List[List[str]]:
    """Rows for this study's own CALC/SIM results (only if the corresponding result exists)."""
    out = []
    on, cal = res.get("online"), res.get("online_cal")
    if on:
        t = on["test"]
        c = cal["test"]["clean"]["top1"] if cal else None
        out.append(_row(id="CON-90", topic="Recognising letters while they are written, on real handwriting",
                        citation="This ledger's calculation: ai3 task 1 (streaming GRU on UJI Pen Characters v2; Character Trajectories cross-test)",
                        year="2026", doi_or_url="results/ai3/ai3.json (online)", source_type="derived calculation", evidence_class="calculation",
                        access_level="full text", task_or_setup="34 training, 6 tuning, 20 test writers (UJI); rules O1-O4 fixed before the test",
                        participants_or_bench="none (public recordings of 60 + 1 writers)", comparator="writer-independent vs writer-calibrated",
                        key_quantitative_findings=(f"test top-1 at 50 % / 100 % of the letter: {t['clean']['top1'][4]:.3f} / {t['clean']['top1'][-1]:.3f} (new writers)"
                                                   + (f", {c[4]:.3f} / {c[-1]:.3f} with the writer's calibration letters" if c else "")
                                                   + f"; Character Trajectories {t['chartraj']['top1'][-1]:.3f}; {t['cost']['n_params']} parameters, "
                                                   f"{t['cost']['ms_per_point_this_cpu']:.2f} ms per point on this CPU"),
                        units_and_conditions="top-1 accuracy; ms", locator="ai3.json online", limitations="Isolated letters on a tablet; timing assumed for UJI",
                        relevance_to_design="How early the pen can know which letter is being written", transferability="medium",
                        transferability_reason="Real handwriting, but isolated letters on a tablet", design_implication="Calibrate the recogniser on the user's letters",
                        search_query="n/a (derived)", stream="CON"))
    tr = res.get("trace")
    if tr:
        a = tr["aggregate"].get("dysgraphia", {})
        n, w = a.get("none", {}), a.get("wheel_path+nose", {})
        out.append(_row(id="CON-91", topic="Why close tracing makes letters less readable",
                        citation="This ledger's simulation: ai3 task 4a on the drive study's HW1-D runs (test writers 0-5, seeds 200-203)",
                        year="2026", doi_or_url="results/ai3/ai3.json (trace)", source_type="derived simulation", evidence_class="simulation",
                        access_level="full text", task_or_setup="Per-letter completeness, backtracking and counterfactual readings of the guided ink",
                        participants_or_bench="none (synthetic learners)", comparator="no guidance",
                        key_quantitative_findings=(f"heel wheel + nose: ink {w.get('d_ink_um_mean', float('nan')):.0f} um from the target, letters read by the app's "
                                                   f"order-sensitive reader {w.get('read', float('nan')):.3f} (none {n.get('read', float('nan')):.3f}); by an order-free "
                                                   f"picture reader {w.get('read_static', float('nan')):.3f} (none {n.get('read_static', float('nan')):.3f}); "
                                                   f"{w.get('newly_misread', 0)} letters newly misread by the app's reader, {w.get('newly_misread_both_readers', 0)} of them by both; "
                                                   f"share of the target letter left undrawn {w.get('missing_mean', float('nan')):.3f} (none {n.get('missing_mean', float('nan')):.3f})"),
                        units_and_conditions="shares of letters; um", locator="ai3.json trace", limitations="Synthetic learners, passive hand, the app's template recogniser",
                        relevance_to_design="Shape assist must not collapse ink onto the nearest part of the model letter", transferability="low",
                        transferability_reason="Model-to-model", design_implication="Progress-aligned correspondence, small limits, completeness metric",
                        search_query="n/a (derived)", stream="CON"))
    sh = res.get("shape")
    if sh:
        ag = sh["test"]["aggregate"]
        def f(k, key):
            return ag.get(k, {}).get(key, float("nan"))
        out.append(_row(id="CON-92", topic="Shape assist on real handwriting with the nose (HW1)",
                        citation="This ledger's simulation: ai3 task 4b (UJI test writers' letters in words, HW1 closed loop, independent offline reader)",
                        year="2026", doi_or_url="results/ai3/ai3.json (shape)", source_type="derived simulation", evidence_class="simulation",
                        access_level="full text", task_or_setup="Recognised-letter shape assist toward the writer's own letter; rules A1 fixed on tuning writers",
                        participants_or_bench="none (20 test writers' real letters, simulated hand)", comparator="no assist",
                        key_quantitative_findings=(f"letters read with 1 mm 8 Hz tremor {f('tremor_1mm_8Hz', 'read_none'):.3f} -> {f('tremor_1mm_8Hz', 'read_assist'):.3f}; "
                                                   f"warped {f('warp', 'read_none'):.3f} -> {f('warp', 'read_assist'):.3f}; clean writing moved {f('clean', 'moved_um_mean'):.1f} um"),
                        units_and_conditions="share of letters read by the judge; um", locator="ai3.json shape",
                        limitations="Simulated hand and tremor; one tablet dataset; the judge is a model", relevance_to_design="What shape assist can do",
                        transferability="low", transferability_reason="Simulation", design_implication="See docs/spelling_and_clarity.md",
                        search_query="n/a (derived)", stream="CON"))
    sp = res.get("spell")
    if sp:
        s = sp["test"]["score"]
        out.append(_row(id="EML-93", topic="Detecting a misspelling while the word is written (noisy channel on real misspellings)",
                        citation="This ledger's calculation: ai3 task 2 (channel from Birkbeck training targets; Holbrook tuning/test children)",
                        year="2026", doi_or_url="results/ai3/ai3.json (spell)", source_type="derived calculation", evidence_class="calculation",
                        access_level="full text", task_or_setup="Letter-by-letter posterior of a deviation; thresholds by rules S2-S3 on tuning children",
                        participants_or_bench="none (11 test children's real writing)", comparator="lexicon-only earliest point",
                        key_quantitative_findings=(f"caught {s['detection_rate']:.3f} of {s['errors']} errors, {s['fa_per_100_correct']:.2f} false alarms per 100 correct words; "
                                                   f"flag on the first wrong letter {s['flag_minus_first_wrong_letter']['same_letter']:.2f} of caught errors; right word in the top 3 "
                                                   f"{s['suggestion_top3']:.2f}"),
                        units_and_conditions="shares; per 100 words", locator="ai3.json spell", limitations="Letters known exactly unless stated; 1960s children",
                        relevance_to_design="What a physical spell checker can catch and when", transferability="medium",
                        transferability_reason="Real errors in real text; recognition simplified", design_implication="See docs/spelling_and_clarity.md",
                        search_query="n/a (derived)", stream="EML"))
    pr = res.get("predict")
    if pr:
        out.append(_row(id="EML-94", topic="Personalised word prediction on one person's own running text",
                        citation="This ledger's calculation: ai3 task 3 (cache + user bigram on NG0/NG1x; public-domain journals)",
                        year="2026", doi_or_url="results/ai3/ai3.json (predict)", source_type="derived calculation", evidence_class="calculation",
                        access_level="full text", task_or_setup="Online adaptation on each journal's first half; rules P1-P2 on tuning journals",
                        participants_or_bench="none (2 test journals)", comparator="NG0 and NG1x without personalisation",
                        key_quantitative_findings=pr.get("_summary", "see ai3.json"), units_and_conditions="top-k accuracy; letters saved; ms",
                        locator="ai3.json predict", limitations="Old journals stand in for notes", relevance_to_design="REQ-APP-003",
                        transferability="low", transferability_reason="Text domain", design_implication="See docs/spelling_and_clarity.md",
                        search_query="n/a (derived)", stream="EML"))
    cu = res.get("cues")
    if cu:
        out.append(_row(id="HAP-134", topic="Physical feedback for spelling while writing: tick, pen lift, show-me, heel steer (simulated)",
                        citation="This ledger's simulation: ai3 task 2 cue comparison (Holbrook test children's words; assumed responses anchored in HAP-130, HAP-131, HAP-133)",
                        year="2026", doi_or_url="results/ai3/ai3.json (cues)", source_type="derived simulation", evidence_class="simulation",
                        access_level="full text", task_or_setup="Monte Carlo of writer responses to each cue; rule S4 on tuning children",
                        participants_or_bench="none", comparator="no cue; the app afterwards",
                        key_quantitative_findings=cu.get("_summary", "see ai3.json"), units_and_conditions="per 10 errors; per 100 correct words; % time",
                        locator="ai3.json cues", limitations="Writer responses are ASSUMPTIONS", relevance_to_design="Which cue to build first",
                        transferability="low", transferability_reason="Assumed responses", design_implication="See docs/spelling_and_clarity.md",
                        search_query="n/a (derived)", stream="HAP"))
    wd = res.get("words")
    if wd and wd.get("test_words"):
        tw = wd["test_words"]["normal"]
        b = wd["W1"]["beta_w"]
        g = lambda k: tw.get(k, {})
        out.append(_row(id="EML-97", topic="Word recognition while writing: character and word error rates, writer- and session-disjoint",
                        citation="This ledger's calculation: ai3 words stage (task 1's causal GRU on words written with real UJI letters of 20 held-out writers; NG1x character model)",
                        year="2026", doi_or_url="results/ai3/ai3.json (words)", source_type="derived calculation", evidence_class="simulation",
                        access_level="full text", task_or_setup="Letters separated at pen lifts by the demo's rule; rule W1 (LM weight) on 6 tuning writers",
                        participants_or_bench="none (20 test writers, both sessions)", comparator="with and without the language model; with and without writer calibration from the other session",
                        key_quantitative_findings=(f"CER / WER, new writers, no LM {g('independent|beta=0')['cer']:.3f} / {g('independent|beta=0')['wer']:.3f}; "
                                                   f"with LM (beta {b:g}) {g(f'independent|beta={b:g}')['cer']:.3f} / {g(f'independent|beta={b:g}')['wer']:.3f}; "
                                                   f"calibrated on the other session, with LM {g(f'calibrated|beta={b:g}')['cer']:.3f} / {g(f'calibrated|beta={b:g}')['wer']:.3f}; "
                                                   f"segmentation errors {tw.get('segmentation_error_per_letter', float('nan')):.3f} per letter"),
                        units_and_conditions="character and word error rates", locator="ai3.json words",
                        limitations="Words assembled from isolated letters with assumed spacing (print writing); tablet data; no tremor",
                        relevance_to_design="Review gate G7: raw and corrected CER/WER on held-out people and sessions", transferability="medium",
                        transferability_reason="Real letters of held-out writers; assembled words", design_implication="Calibrate per writer; add CTC for joined-up writing (EXP-S17)",
                        search_query="n/a (derived)", stream="EML"))
    if wd and wd.get("spelling"):
        b2 = (wd["spelling"].get("calibrated") or {})
        blk = (wd.get("spelling_v2") or {}).get("calibrated") or b2
        t = blk.get("test", {})
        rel = blk.get("reliability_test", {})
        t2, r2 = b2.get("test", {}), b2.get("reliability_test", {})
        if t:
            out.append(_row(id="EML-98", topic="Spelling help that keeps recognition errors apart from spelling errors, with calibrated confidence",
                            citation="This ledger's calculation: ai3 words stage (the review's score over the recogniser's 3 best readings; Holbrook test children; UJI test writers' real letters)",
                            year="2026", doi_or_url="results/ai3/ai3.json (words)", source_type="derived calculation", evidence_class="simulation",
                            access_level="full text", task_or_setup="score = lambda_r log P(strokes|x) + log P(w|context) + log P(x|w); temperature scaling; rules W2-W4 on tuning children",
                            participants_or_bench="none (11 test children's real writing; real letters of 20 held-out writers)", comparator="uncalibrated combination; letters known exactly (EML-93)",
                            key_quantitative_findings=(f"calibrated recogniser. As planned (rule W2: 3 best letter strings, temperature scaling): caught "
                                                       f"{t2.get('detection_rate', float('nan')):.3f} at {t2.get('fa_per_100_correct', float('nan')):.2f} false alarms per 100, ECE "
                                                       f"{r2.get('raw', {}).get('ece', float('nan')):.3f} -> {r2.get('calibrated', {}).get('ece', float('nan')):.3f} (failed). "
                                                       f"Post hoc (W5: + lexicon readings, Platt scaling): caught {t['detection_rate']:.3f} of misspellings at {t['fa_per_100_correct']:.2f} false alarms per 100 correct words; "
                                                       f"shown suggestions right {t['suggestion_right_when_shown']:.2f}; misread words put right {t['recognition']['misread_fixed_share']:.2f}, "
                                                       f"right readings changed {t['recognition']['right_reading_changed_share']:.3f}; unusual correct words kept {t['unusual_correct_words']['kept_unflagged_share']:.2f}; "
                                                       f"ECE {rel.get('raw', {}).get('ece', float('nan')):.3f} -> {rel.get('calibrated', {}).get('ece', float('nan')):.3f}; "
                                                       f"auto mode: {t['auto_mode']['errors_fixed_per_100_errors']:.1f} errors fixed per 100, {t['auto_mode']['correct_words_changed_per_100_correct']:.2f} correct words changed per 100"),
                            units_and_conditions="shares; per 100 words; expected calibration error", locator="ai3.json words",
                            limitations="W5 was designed after W2's test result (post hoc); recognition simulated with real letters of other writers than the children; 1960s texts",
                            relevance_to_design="Review section 10: combine recognition, context and error model; abstain when weak", transferability="medium",
                            transferability_reason="Real errors and real letters, combined in simulation", design_implication="See docs/spelling_and_clarity.md",
                            search_query="n/a (derived)", stream="EML"))
    pl = res.get("plan")
    if pl and pl.get("table"):
        T = pl["table"]
        g = lambda k, f: T.get(k, {}).get(f, float("nan"))
        out.append(_row(id="CON-93", topic="Writing an accepted word with a reach-limited nib while the hand advances",
                        citation="This ledger's simulation: ai3 plan stage (completions from held-out sentences, the UJI test writers' own letters at 3 mm x-height; kinematic planner, rule C1)",
                        year="2026", doi_or_url="results/ai3/ai3.json (plan)", source_type="derived simulation", evidence_class="simulation",
                        access_level="full text", task_or_setup="q = r(s) - b(t) kept within the usable reach; letter admission; slow, lift, hand back",
                        participants_or_bench="none", comparator="stage radius 1-6 mm; hand steady, slow, fast, pausing, still",
                        key_quantitative_findings=(f"completed with a steady hand: {g('steady|6|letter_admission', 'completed_share'):.2f} at +-6 mm, "
                                                   f"{g('steady|4|letter_admission', 'completed_share'):.2f} at +-4 mm, {g('steady|3|letter_admission', 'completed_share'):.2f} at +-3 mm, "
                                                   f"{g('steady|1|letter_admission', 'completed_share'):.2f} at +-1 mm; still hand at +-6 mm {g('still|6|letter_admission', 'completed_share'):.2f}; "
                                                   f"half letters left with letter admission {g('pause|6|letter_admission', 'partial_letters_per_100'):.0f} per 100 (pausing hand) vs "
                                                   f"{g('pause|6|pointwise', 'partial_letters_per_100'):.0f} point by point"),
                        units_and_conditions="shares of completions; per 100 completions", locator="ai3.json plan",
                        limitations="Kinematics only; the hand's advance is assumed; tracking error inside a 0.5 mm reserve",
                        relevance_to_design="Review section 10: the workspace, not the prediction, limits physical completion", transferability="low",
                        transferability_reason="Simulation", design_implication="Complete physically only with >= +-4-6 mm reach at a 3 mm x-height and a moving hand; letter admission",
                        search_query="n/a (derived)", stream="CON"))
    return out


def rows(res: Optional[Dict] = None) -> List[List[str]]:
    return list(LIT) + (derived(res) if res else [])


def write(path: Path, res: Optional[Dict] = None) -> int:
    rs = rows(res)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rs:
            w.writerow(r)
    return len(rs)
