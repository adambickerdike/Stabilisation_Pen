# HAP stream: guidance, shared control, learning and pen-grip impedance

Ledger: `docs/research/ledger/HAP_guidance_impedance.csv` (30 rows, HAP-01 to HAP-30). All sources retrieved 2026-09-26.

## 1. Search log

**Method notes**

- WebSearch results were used only to locate sources. Every number in the ledger comes from the full text or the abstract, as flagged in the `access_level` column.
- Some PDFs came back from WebFetch as binary. Their text was extracted locally with pypdf.
- One scanned PDF (Tan et al. 1994) had no text layer and was read from page images.
- Abstracts and open-access full text were pulled from the Europe PMC REST API (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=...` and `.../{PMCID}/fullTextXML`). The OA full text (and the PMC HTML page for HAP-04) was used to re-verify statistics for HAP-03, HAP-04, HAP-09, HAP-10 and HAP-30.
- The Semantic Scholar and OpenAlex APIs were rate-limited.
- The session's shared web-search quota ran out near the end, so two planned queries were not executed. They are logged below.

**Query log** (every exact query or URL, in order)

| # | Date | Tool | Exact query / URL (outcome) |
|---|---|---|---|
| 1 | 2026-09-26 | WebSearch | Langerak 2019 CHI dynamic drawing guidance electromagnetic haptic feedback |
| 2 | 2026-09-26 | WebSearch | Rivers Moyer Durand 2012 position-correcting tools 2D digital fabrication |
| 3 | 2026-09-26 | WebSearch | Bluteau Coquillart Payan Gentaz 2008 PLoS ONE haptic guidance handwriting learning |
| 4 | 2026-09-26 | WebFetch | https://arxiv.org/pdf/1906.11753 (PDF; text extracted locally with pypdf) |
| 5 | 2026-09-26 | WebFetch | https://hackaday.com/wp-content/uploads/2012/08/position-correcting-tools-for-2d-digital-fabrication.pdf (PDF; text extracted locally) |
| 6 | 2026-09-26 | WebFetch | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0001775 |
| 7 | 2026-09-26 | WebSearch | Sigrist Rauter Riener Wolf 2013 augmented visual auditory haptic multimodal feedback motor learning review Psychonomic Bulletin |
| 8 | 2026-09-26 | WebSearch | Marchal-Crespo Reinkensmeyer 2009 review of control strategies for robotic movement training after neurologic injury |
| 9 | 2026-09-26 | WebSearch | Milot 2010 comparison of error-amplification and haptic-guidance training techniques timing-based motor task Experimental Brain Research |
| 10 | 2026-09-26 | WebFetch | https://link.springer.com/article/10.3758/s13423-012-0333-8 (redirected to login; not retrieved) |
| 11 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC2710333/ |
| 12 | 2026-09-26 | WebFetch | https://escholarship.org/uc/item/3bw664gw (no content) |
| 13 | 2026-09-26 | WebFetch | https://escholarship.org/content/qt3bw664gw/qt3bw664gw.pdf (PDF; text extracted locally) |
| 14 | 2026-09-26 | WebFetch | https://pubmed.ncbi.nlm.nih.gov/19787345/ (reCAPTCHA; not retrieved) |
| 15 | 2026-09-26 | WebFetch | https://www.zora.uzh.ch/entities/publication/e5c339ed-5f99-4e3a-9676-5ed560b7cdce (access denied) |
| 16 | 2026-09-26 | WebSearch | Salmoni Schmidt Walter 1984 knowledge of results and motor learning review critical reappraisal guidance hypothesis Psychological Bulletin |
| 17 | 2026-09-26 | WebSearch | Heuer Lüttgen 2015 robot assistance of motor learning a neuro-cognitive perspective Neuroscience Biobehavioral Reviews |
| 18 | 2026-09-26 | WebSearch | Lüttgen Heuer 2012 robotic guidance benefits the learning of dynamic but not of spatial movement characteristics |
| 19 | 2026-09-26 | WebSearch | Heuer Lüttgen motor learning with fading and growing haptic guidance Experimental Brain Research 2014 |
| 20 | 2026-09-26 | Europe PMC REST API | EXT_ID:24736860 / 22836521 / 6399752 / 19787345 / 24276313 AND SRC:MED (abstracts) |
| 21 | 2026-09-26 | Europe PMC REST API | TITLE:"Robot assistance of motor learning" AND AUTH:"Heuer" |
| 22 | 2026-09-26 | Europe PMC REST API | EXT_ID:23132605 AND SRC:MED |
| 23 | 2026-09-26 | Europe PMC REST API | TITLE:"effectiveness of robotic training depends on motor task characteristics" |
| 24 | 2026-09-26 | Europe PMC REST API | TITLE:"haptic guidance" AND TITLE:"handwriting" |
| 25 | 2026-09-26 | WebSearch | Palluel-Germain 2007 visuo-haptic device Telemaque increases kindergarten children's handwriting acquisition |
| 26 | 2026-09-26 | WebSearch | Teranishi Korres Park Eid 2018 combining full and partial haptic guidance improves handwriting skills development |
| 27 | 2026-09-26 | Europe PMC REST API | EXT_ID:29994720 / 31247561 / 33769937 AND SRC:MED (abstracts) |
| 28 | 2026-09-26 | WebFetch | https://hal.science/hal-00769415/document (access denied by bot filter) |
| 29 | 2026-09-26 | WebSearch | Teo Burdet Lim 2002 "robotic teacher of Chinese handwriting" haptic interface |
| 30 | 2026-09-26 | WebSearch | Henmi Yoshikawa 1998 virtual lesson and its application to virtual calligraphy system ICRA |
| 31 | 2026-09-26 | Semantic Scholar API | "A robotic teacher of Chinese handwriting"; "Virtual lesson and its application to virtual calligraphy system" (HTTP 429, no data) |
| 32 | 2026-09-26 | OpenAlex API | title.search: robotic teacher of chinese handwriting (rate-limited, no data) |
| 33 | 2026-09-26 | WebFetch | https://ieeexplore.ieee.org/document/677278/ (no content returned) |
| 34 | 2026-09-26 | WebFetch | https://www.scitepress.org/papers/2010/27789/27789.pdf (PDF; text extracted locally) |
| 35 | 2026-09-26 | WebSearch | "A robotic teacher of Chinese handwriting" Teo Burdet Lim pdf 6-DOF haptic interface guidance mode assistance levels |
| 36 | 2026-09-26 | WebSearch | Kim Collins Bulmer Sharma Mayrose Haptics Assisted Training (HAT) system for children's handwriting World Haptics 2013 |
| 37 | 2026-09-26 | WebFetch | https://www.frontiersin.org/articles/10.3389/fpsyg.2016.02010/full (two passes) |
| 38 | 2026-09-26 | WebFetch | https://files.ait.ethz.ch/projects/magpen/magpen.pdf (PDF; text extracted locally) |
| 39 | 2026-09-26 | WebSearch | dePENd Yamaoka Kakehi UIST 2013 augmented handwriting system using ferromagnetism of a ballpoint pen |
| 40 | 2026-09-26 | WebSearch | Zoran Paradiso FreeD freehand digital sculpting tool CHI 2013 handheld milling spindle retract speed |
| 41 | 2026-09-26 | WebFetch | https://futurecrafts.kmd.keio.ac.jp/depend/ |
| 42 | 2026-09-26 | WebFetch | https://resenv.media.mit.edu/pubs/papers/2013-ZORAN_CHI_FREED.pdf (PDF; text extracted locally) |
| 43 | 2026-09-26 | WebFetch | https://dl.acm.org/doi/10.1145/2501988.2502017 (HTTP 403) |
| 44 | 2026-09-26 | WebSearch | Yamaoka Kakehi dePENd neodymium magnet XY plotter ballpoint pen tip guidance user evaluation free-hand drawing accuracy |
| 45 | 2026-09-26 | WebFetch | https://aimlab-haptics.com/katib |
| 46 | 2026-09-26 | WebSearch | Park Korres Moonesinghe Eid 2019 full partial disturbance haptic guidance handwriting children Phantom Omni stiffness threshold partial guidance deviation |
| 47 | 2026-09-26 | WebFetch | https://aimlab-haptics.com/s/Contactless-Kinesthetic-Feedback-to-Support-Handwriting-Using-Magnetic-Force.pdf (PDF; text extracted locally) |
| 48 | 2026-09-26 | WebSearch | Rosenberg 1993 virtual fixtures perceptual tools for telerobotic manipulation peg insertion performance improvement |
| 49 | 2026-09-26 | WebSearch | Abbott Marayong Okamura haptic virtual fixtures for robot-assisted manipulation guidance virtual fixture admittance ratio pdf |
| 50 | 2026-09-26 | WebSearch | Abbink Mulder Boer 2012 haptic shared control smoothly shifting control authority Cognition Technology Work |
| 51 | 2026-09-26 | WebFetch | http://robots.stanford.edu/isrr-papers/draft/abbott-final.pdf (PDF; text extracted locally) |
| 52 | 2026-09-26 | WebFetch | https://link.springer.com/content/pdf/10.1007/s10111-011-0192-5.pdf (redirected to login; not retrieved) |
| 53 | 2026-09-26 | Europe PMC REST API | TITLE:"Speed-accuracy characteristics of human-machine cooperative manipulation"; TITLE:"Sharing control with haptics" |
| 54 | 2026-09-26 | WebSearch | Abbink Carlson Mulder de Winter 2018 "A topology of shared control systems" finding common ground in diversity IEEE Transactions Human-Machine Systems |
| 55 | 2026-09-26 | WebSearch | Dragan Srinivasa 2013 policy-blending formalism for shared control arbitration confidence prediction International Journal of Robotics Research |
| 56 | 2026-09-26 | WebSearch | Li Okamura 2003 recognition of operator motions for real-time assistance using virtual fixtures hidden Markov models curve following |
| 57 | 2026-09-26 | WebFetch | https://discovery.ucl.ac.uk/10041044/1/Abbink%20et%20al%20-%20Shared%20Control%20Review%20R2.pdf (PDF; text extracted locally) |
| 58 | 2026-09-26 | WebFetch | https://publications.ri.cmu.edu/a-policy-blending-formalism-for-shared-control |
| 59 | 2026-09-26 | WebFetch | https://publications.ri.cmu.edu/storage/publications/pub_files/2013/5/assistive_teleop_IJRR.pdf (PDF; text extracted locally) |
| 60 | 2026-09-26 | Europe PMC REST API | TITLE:"mechanical impedance at the human finger tip"; TITLE:"Human-arm-and-hand-dynamic model"; TITLE:"Mechanical behavior of the fingertip in the range of frequencies and displacements relevant to touch" |
| 61 | 2026-09-26 | WebSearch | Hajian Howe 1997 "Identification of the mechanical impedance at the human finger tip" pdf biorobotics harvard |
| 62 | 2026-09-26 | WebSearch | Kuchenbecker Park Niemeyer 2003 characterizing the human wrist for improved haptic interaction stylus grip stiffness damping mass values |
| 63 | 2026-09-26 | WebSearch | Fu Oliver 2005 direct measurement of index finger mechanical impedance at low force World Haptics |
| 64 | 2026-09-26 | WebSearch | "Engineering Haptic Devices" open access 2023 chapter "The User's Role in Haptic System Design" mechanical impedance index finger grasp model parameters |
| 65 | 2026-09-26 | WebFetch | https://www.semanticscholar.org/paper/Characterizing-the-Human-Wrist-for-Improved-Haptic-Kuchenbecker-Park/53a699763fef1fffaf0776aca32898936abbecc3 (no content) |
| 66 | 2026-09-26 | WebFetch | https://link.springer.com/chapter/10.1007/978-3-031-04536-3_3 (redirect to login); curl retry blocked by JS challenge |
| 67 | 2026-09-26 | WebSearch | "Hajian and Howe" fingertip effective mass damping stiffness values "N/m" "Ns/m" extension 2-20 N |
| 68 | 2026-09-26 | WebSearch | Kuchenbecker "Characterizing the human wrist for improved haptic interaction" pdf grip force wrist stiffness natural frequency |
| 69 | 2026-09-26 | curl | http://bdml.stanford.edu/twiki/pub/RisePrivate/HapticsDraftPublications/kjkthesis-oneside.pdf (Kuchenbecker PhD thesis 2006; text extracted locally) |
| 70 | 2026-09-26 | WebSearch | Fu Cavusoglu human arm and hand dynamic model stylus Phantom Premium grip force 1-3 N identified mass damping stiffness parameters pdf |
| 71 | 2026-09-26 | WebSearch | Wiertlewski Hayward 2012 fingertip impedance tangential spring damper values N/m N s/m 100 Hz high mobility probe |
| 72 | 2026-09-26 | curl | http://engr.case.edu/cavusoglu_cenk/papers/TSMC2012.pdf (author PDF; text extracted locally) |
| 73 | 2026-09-26 | WebSearch | Israr Choi Tan 2006 detection threshold and mechanical impedance of the hand in a pen-hold posture |
| 74 | 2026-09-26 | WebSearch | McMahan Kuchenbecker stylus hand model five parameter mass spring damper 10-200 Hz dedicated actuator tool contact identification |
| 75 | 2026-09-26 | curl | https://engineering.purdue.edu/~hongtan/pubs/ (publication list) and https://engineering.purdue.edu/~hongtan/pubs/PDFfiles/C70_IsrarChoiTan_IROS2006.pdf (text extracted locally) |
| 76 | 2026-09-26 | Europe PMC REST API | TITLE:"Four channels mediate the mechanical aspects of touch"; TITLE:"Detection of vibration transmitted through an object grasped in the hand" |
| 77 | 2026-09-26 | WebSearch | Bolanowski Gescheider Verrillo Checkosky 1988 threshold 0.4 Hz 3 Hz thenar eminence "dB re 1 µm" NP III channel absolute threshold value |
| 78 | 2026-09-26 | WebSearch | Morioka Griffin thresholds for perception of hand-transmitted vibration dependence on contact area and contact location frequency 8 to 1000 Hz acceleration thresholds |
| 79 | 2026-09-26 | curl/WebFetch | https://eprints.soton.ac.uk/28546/1/14554_Morioka_Griffin_2005_Thresholds_for_hand_vibration_contact_area_and_location.pdf (HTML stub / HTTP 403; not retrieved) |
| 80 | 2026-09-26 | Europe PMC REST API | EXT_ID:16503581 AND SRC:MED; AUTH:"Morioka M" AND AUTH:"Griffin MJ" AND TITLE:"hand-transmitted vibration" |
| 81 | 2026-09-26 | curl | https://engineering.purdue.edu/~hongtan/pubs/PDFfiles/C15_Tan_ASME1994.pdf (scanned; page images read visually) |
| 82 | 2026-09-26 | Europe PMC REST API | TITLE:"Basic and supplementary sensory feedback in handwriting"; TITLE:"Functions of vision in the control of handwriting"; TITLE:"production of letter strokes in handwriting benefit from vision"; TITLE:"role of vision in the temporal and spatial control of handwriting" |
| 83 | 2026-09-26 | WebFetch | https://pmc.ncbi.nlm.nih.gov/articles/PMC4335466/ |
| 84 | 2026-09-26 | Europe PMC REST API | (TITLE:"delayed visual feedback" OR TITLE:"visual feedback delay") AND (TITLE:handwriting OR TITLE:writing OR TITLE:drawing) (no hits) |
| 85 | 2026-09-26 | WebSearch | delayed visual feedback handwriting experiment letter repetition errors delay ms writing performance (NOT EXECUTED: session web-search budget exhausted) |
| 86 | 2026-09-26 | WebSearch | Ng Annett Dietz Gupta Bischof 2014 "In the blink of an eye" latency perception stylus interaction inking threshold ms (NOT EXECUTED: session web-search budget exhausted) |
| 87 | 2026-09-26 | Europe PMC REST API | fullTextUrlList check for PMIDs 23132605, 26192105, 24276313, 29994720, 9083857, 3209773, 10200190, 8475770, 15573549, 23156623 |
| 88 | 2026-09-26 | curl | https://journals.sagepub.com/doi/pdf/10.1518/hfes.46.3.518.50400 (Cloudflare challenge; not retrieved) |
| 89 | 2026-09-26 | Europe PMC REST API | TITLE:"Can robots help the learning of skilled actions"; TITLE:"Evaluation of robotic training forces that either enhance or reduce error in chronic hemiparetic stroke survivors" |
| 90 | 2026-09-26 | WebFetch + curl | https://pmc.ncbi.nlm.nih.gov/articles/PMC2905644/ |
| 91 | 2026-09-26 | Europe PMC REST API | TITLE:"Effects of physical guidance and knowledge of results on motor learning" (found via ref. 30 of PMC2905644) |
| 92 | 2026-09-26 | curl | http://www.ism.univ-amu.fr/wiertlewski/pub/ (HTTP 503; not retrieved) |
| 93 | 2026-09-26 | WebFetch | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0001775 (second pass, verbatim parameters) |
| 94 | 2026-09-26 | Europe PMC REST API | DOI:"10.3389/fpsyg.2016.02010"; DOI:"10.1371/journal.pone.0001775" |
| 95 | 2026-09-26 | Europe PMC REST API | fullTextXML for PMC5183591, PMC2258003, PMC2710333, PMC2905644 (not available), PMC4335466 (used to verify numbers) |

**Retrieved but not ledgered.** These sources were left out to keep the ledger at 30 rows or because their content could not be verified. They are not used in the synthesis unless a ledger row cites them.

- Marchal-Crespo L, Rappo N, Riener R (2017), Exp Brain Res 235:3799-3816, abstract. With 30 participants, error amplification gave better learning than haptic guidance in both a continuous tracking game and a discrete reaching game. It also reduced interest/enjoyment and perceived competence. This is consistent with HAP-08 and HAP-09.
- Lüttgen J, Heuer H (2012), Exp Brain Res 222:1-9, abstract. After haptic demonstration, dynamic accuracy was better; after visual demonstration, spatial accuracy was better. This is consistent with HAP-05.
- Brisben AJ, Hsiao SS, Johnson KO (1999), J Neurophysiol 81:1548-1558, abstract. Folded into HAP-27 as a comparator.
- Bolanowski SJ et al. (1988), JASA 84:1680-1694, abstract. Four channels operate from at least 0.4 Hz to above 500 Hz. The numeric threshold levels were taken only as secondary citations in HAP-27 and HAP-28.
- Morioka M, Griffin MJ (2005), Somatosens Mot Res 22:281-297, abstract. Covers thresholds from 8 to 500 Hz: NP I thresholds below 31.5 Hz decrease from proximal to distal regions of the hand, while Pacinian thresholds at 125 Hz do not depend on location. The full text was blocked (HTTP 403).
- Wiertlewski M, Hayward V (2012), J Biomech 45:1869-1874, abstract. The fingertip behaves elastically from DC to about 100 Hz and viscously above that. Numeric values appeared only in a search-engine summary, were not verified, and were not used.
- Kim Y et al. (2013) HAT, WHC 2013 pp. 559-564; Fu C-Y & Oliver M (2005), WHC 2005; McMahan W & Kuchenbecker KJ (2009). Only search snippets were seen, with no results accessed. They are not ledgered and are listed as gaps.
- Mulder M, Abbink DA, Boer ER (2012), Hum Factors 54:786-798, abstract. Folded into HAP-22.

## 2. Critical synthesis

### 2.1 What the evidence supports

- The nib is ungrounded. It cannot push the hand; it can only move the ink relative to the hand, as Rivers' position-correcting tool does (HAP-18), and create small reaction forces. Its learning effect should be judged against outcome-guidance evidence, which is consistently cautionary: guidance that removes error improves assisted performance but can reduce unassisted retention (HAP-01, HAP-02, HAP-04, HAP-06). In the closest analogue, curve tracing with an error-minimising channel (0.8 mm deadband, 0.3 N/mm), the assisted group was the least accurate once assistance was removed, including 1 day later (HAP-09).
- The benefits fall on dynamics and fluency, not on shape. Force-profile guidance reduced velocity peaks and raised speed, but no mode improved shape (HAP-10). Children gained fluency with Telemaque (HAP-11). A review classifies spatial features as impeded by guidance (HAP-05).
- Who benefits depends on skill and on letter complexity. Guidance helped low-skill learners and error amplification helped skilled ones (HAP-08). In children, disturbance guidance worked best for complex letters and full guidance for simple ones (HAP-14). Partial-then-full guidance ranked best in HAP-13. These handwriting studies were available only as abstracts, which do not say whether tests were unassisted or delayed.
- No drawing-guidance device has measured learning. MagPen cut shape errors to 50–62 % of unguided values while guiding but did not test learning (HAP-16), and KATIB measured assisted copying only (HAP-15).

### 2.2 Design rules for assistance that supports learning

1. **Two modes, two success metrics.** Assist mode (tremor and precision) may correct continuously. Learn mode is judged only on unassisted, delayed retention and on transfer to untrained letters (HAP-02, HAP-06, HAP-12).
2. **Split the correction by frequency.** Voluntary force control reaches about 7 Hz, with an upper bound of 20–30 Hz, and users actively cancel induced motion below about 8 Hz (HAP-28, HAP-25). Cancel content above that band, and leave slow error (drift, shape, size) visible so the writer's own loop corrects it. One inference still needs testing: full-band correction may hide slow drift until the ±0.5 mm headroom saturates.
3. **Deadband and continuous gain.** Leave natural variability uncorrected (HAP-03, HAP-09). Use a correction gain from 0 to 1 rather than on/off (HAP-21), because strong guidance helps on the path but costs time and error when the user means to deviate.
4. **Fade by performance and keep assist-off strokes.** Use these mechanisms:
   - an error-driven gain with forgetting, P_i = f·P_(i−1) + g·e_i with f < 1 (HAP-03);
   - a faded correction frequency (HAP-02);
   - a demonstrate → assisted → unassisted sequence of repetitions (HAP-07);
   - about 20 % catch strokes with assistance off (HAP-08).
5. **Adapt the mode to skill and letter complexity.** For proficient users, consider revealing errors, or augmenting them visually by moving the ink away from the path (HAP-08, HAP-14, HAP-04). Visual error augmentation through the nib is untested and remains a hypothesis.
6. **Tie authority to confidence.** Assistance that is confident but wrong is the costliest case: aggressive assistance with a wrong prediction performed worst (HAP-23). At junctions, loop closures and stroke starts, use a timid profile that never fully takes over. Track progress with a time-free variable rather than a timed setpoint (HAP-16, HAP-17). Release the fixture when intent to leave the path is recognised (e.g., the HMM approach in HAP-21).
7. **Behave predictably out of range.** Rivers holds or stops at the edge of its range, prefers walking along the path over shortcuts, and then re-acquires the path (HAP-18). FreeD withdraws rather than fights (HAP-19). The pen should saturate smoothly, hand authority back and optionally give a cue. It should never create sustained conflict, since users dislike resisting forces that act against their intent (HAP-22).
8. **Deliver error information after the stroke.** In learn mode, use audio or vibration rather than concurrent visual changes, which disrupt fluency (HAP-30).

### 2.3 Hand-impedance ranges for simulation

The model from HAP-26 connects barrel –(k1 ∥ b1, grasp)– hand/arm mass M –(k2 ∥ b2, arm)– ground, with in-plane axes X (left–right) and Z (fore–aft).

| Parameter | Baseline | Sweep | Source |
|---|---|---|---|
| Grasp stiffness k1 | 380 (X) – 770 (Z) N/m | 230–1040 N/m | HAP-26 Tables II–III |
| Grasp damping b1 | 0.8–1.8 N·s/m | ~0–4.6 N·s/m | HAP-26 |
| Effective mass M | 0.20–0.22 kg | 0.02–0.57 kg | HAP-26 |
| Arm stiffness k2 | 79–272 N/m | 63–533 N/m | HAP-26 |
| Arm damping b2 | 4.6–18 N·s/m | 3.7–27.6 N·s/m | HAP-26 |
| Small-signal pen-hold impedance, <40 Hz (axial) | ≈13–16 N·s/m | — | HAP-27 (converted from dB) |
| Check with another grasp (joystick) | k 40 N/m, b 23 N·s/m, handle 0.014 kg | — | HAP-25 |

Add an active user loop below about 5–8 Hz (HAP-25, HAP-28), and schedule k and b with grip force (HAP-24, HAP-25); in HAP-26 the effect of grip between 1 and 3 N was small. The model was fitted over 0.6–30 Hz and fits best below 20 Hz; above that range, use HAP-27.

Illustrative estimate (this note's derivation, not a measurement): each 0.1 N of in-plane reaction on the barrel deflects it by about 0.13–0.26 mm quasi-statically against k1 = 380–770 N/m, which is about 5–10× the pen-hold detection threshold at 10 Hz (26 µm; HAP-27). Actuator reactions will therefore be felt. Shape them as smooth, low-bandwidth events, or use them deliberately as cues.

### 2.4 What does not transfer to a ±0.5 mm nib

- **Kinesthetic demonstration.** Every guidance study used grounded devices that move the hand (Phantom, magnets under a tablet, Steady-Hand robot, rehabilitation robots). Benefits attributed to feeling the correct dynamics (HAP-05, HAP-10, HAP-11) have no mechanism in an ungrounded pen.
- **Correction range.** Without guidance, shape errors were 3.8–5.1 mm (HAP-16). With a display, manual error stayed within 3.2 mm, which is why Rivers sized its range at ±6.35 mm (HAP-18). Magnet playback error was under 3 mm (HAP-15). A ±0.5 mm range cannot fix a novice's letter shapes. It can polish sub-millimetre error around a reference that is re-anchored to the writer's own stroke.
- **Gains and force levels.** Values of 0.3–0.6 N/mm and 0.43–0.49 N at the tip were chosen to move hands, not to size a nib actuator.
- **Posture in the impedance studies.** HAP-26 used an unsupported arm, and HAP-27 used a supported forearm with axial excitation. A hand resting on paper has not been characterised.
- **Time-indexed playback.** The playback systems in HAP-12 and HAP-17 cannot work with free-paced writing.

### 2.5 Decisive experiments

1. **Retention trial**, first with adult novices on an unfamiliar script and then with children. Compare no assistance, full correction, faded assist-as-needed with 20 % catch strokes, and visual error augmentation. Test unassisted immediately, at 24 h and at 1 week, with transfer to untrained and mirror-image letters. Measure shape error (DTW or Hausdorff), velocity peaks, pen lifts and legibility.
2. **Drift and headroom.** Compare full-band with band-split correction. Log the hand–ink offset and the time spent at saturation, and ask whether writers notice the correction or feel a loss of agency.
3. **Impedance in the writing posture.** Inject in-plane forces at 1–100 Hz at the barrel (with the prototype actuator or a shaker) while the hand rests on paper, and measure grip force. Fit the HAP-26 model.
4. **Perception and comfort.** Measure detection thresholds and annoyance ratings for in-plane barrel reactions at 1–50 Hz during writing.
5. **Branch ambiguity.** Compare timid and aggressive authority at letter junctions using the HAP-23 protocol. Measure the rate of wrong branches, completion time and preference.
