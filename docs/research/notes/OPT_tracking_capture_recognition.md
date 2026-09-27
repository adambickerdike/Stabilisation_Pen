# OPT stream: optical tracking, capture pens and recognition (search log and synthesis)

- **Stream:** OPT (pen-tip motion sensing, capture pens, handwriting recognition, datasets, grounded-summary evaluation)
- **Ledger:** `docs/research/ledger/OPT_tracking_capture_recognition.csv` (35 rows, OPT-01 to OPT-35)
- **Research date:** 2026-09-26 (all ledger rows carry `retrieved = 2026-09-26`)

## 0. Method notes

- **Tools.** WebSearch finds candidate sources; WebFetch reads pages. `curl` + `pypdf` fetched PDFs, and PDFs saved by WebFetch were also text-extracted locally. Every number in the ledger comes from a document read in full, unless its row says `secondary account`.
- **Search budget.** The WebSearch budget is shared across this session's parallel agents (200 calls), and it ran out after 40 searches by this stream. The last two planned searches were not run (see the log). Remaining sources were reached by direct URL (arXiv IDs, dataset pages).
- **Blocked or unavailable sources:**
  - PixArt product pages (HTTP 403);
  - ACM DL full text for TipTrack and OptiBasePen (403);
  - Kickstarter (403) and X (402);
  - Livescribe developer PDF and press release (504);
  - IAM-OnDB site: HTTP 503, and curl reported an expired TLS certificate. TLS verification was not bypassed;
  - CASIA site (503 / connection reset);
  - web.archive.org (not fetchable by the tool);
  - NeoLAB getting-started guide (bot wall).
- **Evidence-class convention** (the allowed list has no category for software benchmarks or data-provider statements):
  - studies that collected data from people, or had people rate outputs: `physical human study`;
  - algorithm evaluations on pre-existing recorded datasets: `physical bench experiment`;
  - vendor and dataset-provider statements (specifications, licences): `manufacturer statement`;
  - derived numbers are labelled "derived" in the ledger text.
- **Nominal vs measured.** Datasheet or vendor resolution (cpi/dpi) is labelled NOMINAL. Accuracy figures come only from experiments (DeltaPen, Flashpen, recognition papers) and are labelled MEASURED where relevant.

## 1. Search log (every query and fetch, in execution order)

All entries are dated 2026-09-26. "WebSearch" rows give the exact query string. "WebFetch" and "curl" rows give the exact URL fetched.

| # | Date | Tool | Exact query or URL | Outcome |
|---|------|------|--------------------|---------|
| 1 | 2026-09-26 | WebFetch | `https://static.siplab.org/papers/uist2022-deltapen.pdf` | DeltaPen full text (PDF saved and text-extracted locally with pypdf) |
| 2 | 2026-09-26 | WebSearch | `PixArt P3040 lens-less optical sensor pen mouse datasheet` | no P3040 datasheet found |
| 3 | 2026-09-26 | WebSearch | `PixArt PAA5100JE near-field optical flow sensor datasheet working distance 15mm 35mm` | datasheet on RobotShop CDN |
| 4 | 2026-09-26 | WebSearch | `PMW3901 datasheet frame rate 121 fps working range 80mm SPI` | Pimoroni/DigiKey breakout pages |
| 5 | 2026-09-26 | WebFetch | `https://cdn.robotshop.com/media/p/pim/rb-pim-107/pdf/paa5100je-near-optical-flow-spi-breakout-datasheet.pdf` | PAA5100JE datasheet v1.00 (25 Jul 2018); an earlier curl of the same URL returned an HTML page |
| 6 | 2026-09-26 | WebFetch | `https://www.pixart.com/products-comparison/7/Optical_Mouse_Sensor` | HTTP 403 |
| 7 | 2026-09-26 | WebSearch | `site:pixart.com PMW3901MB-TXQT optical flow` | PixArt product page snippet |
| 8 | 2026-09-26 | WebSearch | `PixArt PAW3395 datasheet 26000 CPI 650 IPS 50G frame rate lift off distance` | secondary pages; LCSC/JLCPCB listings |
| 9 | 2026-09-26 | WebSearch | `PMW3360 datasheet 12000 CPI 250 IPS 50g frame rate 12000 fps lift-off distance LM19-LSI lens` | EPS Global datasheet link |
| 10 | 2026-09-26 | WebFetch | `https://www.epsglobal.com/Media-Library/EPSGlobal/Products/files/pixart/PMW3360DM-T2QU.pdf?ext=.pdf` | PMW3360 datasheet v1.30 (6 Apr 2016) |
| 11 | 2026-09-26 | WebFetch | `https://www.pixart.com/products-detail/44/PMW3901MB-TXQT` | HTTP 403 |
| 12 | 2026-09-26 | WebSearch | `PMW3389DM-T3QU datasheet 16000 cpi epsglobal pdf` | datasheet v1.01 (3 Jan 2019) via gzhls.at mirror |
| 13 | 2026-09-26 | WebSearch | `PMW3901MB-TXQT datasheet pdf "80 mm" frame rate "121" fps PixArt version` | mirrors (GitHub, LCSC, CODICO, datasheet4u) |
| 14 | 2026-09-26 | WebFetch | `https://www.lcsc.com/datasheet/C43496881.pdf` | no content returned |
| 15 | 2026-09-26 | WebFetch | `https://gzhls.at/blob/ldb/a/0/f/6/3971c1b0ff98ce53e924c6ce3ffb16905172.pdf` | PMW3389 datasheet v1.01 |
| 16 | 2026-09-26 | curl | `https://raw.githubusercontent.com/tstellanova/pmw3901-ehal/main/PixArt-PMW3901MB-TXQT-datasheet.pdf` | PMW3901MB datasheet v1.00 (20 Mar 2017) |
| 17 | 2026-09-26 | WebFetch | `https://www.codico.com/media/productattach/p/m/pmw3901mb-txqt_-_productbrief_2451186_7.pdf` | PMW3901MB datasheet v1.10 (20 Jun 2017) |
| 18 | 2026-09-26 | WebFetch | `https://datasheet4u.com/pdf-down/P/M/W/PMW3901MB-TXQT-PixArt.pdf` | HTTP 403 |
| 19 | 2026-09-26 | WebFetch | `https://shop.pimoroni.com/products/pmw3901-optical-flow-sensor-breakout` | Pimoroni listing: 121 FPS, 80 mm to infinity |
| 20 | 2026-09-26 | WebSearch | `PAW3395DM-T6QU datasheet pdf lcsc "Version" lift cut-off frame rate` | LCSC datasheet link |
| 21 | 2026-09-26 | WebSearch | `Flashpen Romat Fender Meier Holz 2021 optical flow sensor pen virtual reality PMW3360 latency` | Flashpen PDF; TipTrack; OptiBasePen |
| 22 | 2026-09-26 | WebFetch | `https://static.siplab.org/papers/vr2021-flashpen.pdf` | Flashpen full text (IEEE VR 2021) |
| 23 | 2026-09-26 | WebFetch | `https://dl.acm.org/doi/fullHtml/10.1145/3623509.3633366` | HTTP 403 (TipTrack) |
| 24 | 2026-09-26 | WebSearch | `TipTrack IR-emitting pen tip optical pen tracking arbitrary surfaces latency accuracy TEI 2024` | Regensburg epub PDF |
| 25 | 2026-09-26 | WebSearch | `OptiBasePen UIST 2024 relative base motion close-range pen position optical flow sensor accuracy` | ACM fullHtml (403) |
| 26 | 2026-09-26 | WebFetch | `https://siplab.org/projects/OptiBasePen` | HTTP 404 |
| 27 | 2026-09-26 | WebSearch | `"OptiBasePen" pdf authors mouse sensor PMW infrared image sensors` | search snippet only: PAJ7025R3 up to 200 Hz |
| 28 | 2026-09-26 | curl | `https://static.siplab.org/papers/uist2024-optibasepen.pdf` | HTTP 404 |
| 29 | 2026-09-26 | WebFetch | `https://www.hackster.io/news/you-ll-be-drawn-to-this-digital-pen-e7ede06c7369` | HTTP 403 |
| 30 | 2026-09-26 | WebSearch | `Anoto dot pattern 0.3 mm grid 6x6 dots position camera frames per second pen specification` | py-microdots; Wikipedia; patents |
| 31 | 2026-09-26 | WebSearch | `Anoto digital pen camera 75 images per second resolution accuracy dot pattern license paper` | patents; DigiWrite; Wikipedia |
| 32 | 2026-09-26 | WebFetch | `https://github.com/cheind/py-microdots` | MIT-licensed Anoto codec; 0.3 mm grid, 6x6 window |
| 33 | 2026-09-26 | WebSearch | `Anoto patent position-coding pattern "0.3 mm" raster marks displaced 6x6 Pettersson Ericson US6663008` | Google Patents US6663008B1, US6548768B1 |
| 34 | 2026-09-26 | WebSearch | `Anoto digital pen accuracy spatial resolution sampling rate study handwriting kinematics validation` | no direct Anoto accuracy validation found |
| 35 | 2026-09-26 | WebFetch | `https://patents.google.com/patent/US6663008` | 300 um raster, 50 um displacement |
| 36 | 2026-09-26 | WebFetch | `https://patents.google.com/patent/US6548768B1/en` | ~100 images/s, 300 um raster |
| 37 | 2026-09-26 | WebSearch | `Anoto pattern license print own dot paper developer SDK 2025 Anoto Group` | Anoto Support pattern-licence articles |
| 38 | 2026-09-26 | WebSearch | `Livescribe smartpen infrared camera frames per second specifications Dot paper Anoto licensed` | reviews; Livescribe dev PDF |
| 39 | 2026-09-26 | WebFetch | `https://support.anoto.com/article/414-pattern-licenses` | pages/books/shelves; subscription; updated 12 Nov 2020 |
| 40 | 2026-09-26 | WebFetch | `https://www.livescribe.com/en-us/media/pdf/dev/Livescribe_Platform_Introduction.pdf` | HTTP 504 (also via curl) |
| 41 | 2026-09-26 | WebFetch | `https://livescribe.helpscoutdocs.com/article/715-60000-livescribe-dot-paper` | DPS description; updated 11 Dec 2020 |
| 42 | 2026-09-26 | WebFetch | `https://en.wikipedia.org/wiki/Livescribe` | Anoto licence; 600 dpi print; acquisition 2015 |
| 43 | 2026-09-26 | WebSearch | `Livescribe Pulse smartpen "72" frames per second infrared camera specification` | reviews (secondary) state 72 fps |
| 44 | 2026-09-26 | WebSearch | `Anoto pen "75 Hz" OR "75 frames" OR "100 frames" camera sampling rate digital pen research paper` | Anoto Support pen comparison |
| 45 | 2026-09-26 | WebFetch | `https://support.anoto.com/article/1626-digital-pen-comparison` | AP-701: 75 FPS, 18 g, 157.5 x 16.85 mm; updated 28 Sep 2022 |
| 46 | 2026-09-26 | WebFetch | `https://www.livescribe.com/en-us/press/releases/release_080128.html` | HTTP 504 |
| 47 | 2026-09-26 | WebFetch | `https://www.neolab.net/en/technology` | Ncode: 2 mm x 2 mm code area; 377.9 billion A4 sheets; sub-mm claim |
| 48 | 2026-09-26 | WebSearch | `Neo smartpen M1+ specifications camera frames per second pressure levels Ncode printing 600 dpi laser printer carbon` | shop pages; no fps |
| 49 | 2026-09-26 | WebSearch | `NeoSmartpen GitHub SDK license Ncode print own notebook "Ncode" developer terms` | Ncode SDK repos |
| 50 | 2026-09-26 | WebFetch | `https://github.com/NeoSmartpen/Ncode-SDK2.0/blob/master/readme.md` | commercial licence USD 7,000/yr; test key |
| 51 | 2026-09-26 | WebFetch | `https://shop.neosmartpen.com/products/neo-smartpen-m1-plus` | M1+ 149.6 x 10.9 mm, 22 g, BT 4.2, USD 129 |
| 52 | 2026-09-26 | WebSearch | `Ncode coordinate unit "2.371" mm OR "56/600" Neo smartpen dot code unit conversion` | Ncode guide (manuals.plus; blocked) |
| 53 | 2026-09-26 | WebSearch | `Neo smartpen N2 camera "120" fps OR "frames per second" sensor specification Ncode dot` | ALSO distributor PDF |
| 54 | 2026-09-26 | WebFetch | `https://www.also.com/pub/assets/f4a919f5-2f8e-4b90-9db5-e702ab755985.pdf` | NeoLAB N2 brochure (c) 2015: 120 PPS / 1100 DPI; 256 pressure steps |
| 55 | 2026-09-26 | WebFetch | `https://usermanual.wiki/Pdf/NcodeE284A220Service20Development20Getting20Started20Guide20v101.1352217076/help` | redirect -> manuals.plus HTTP 403 |
| 56 | 2026-09-26 | curl | `https://usermanual.wiki/Pdf/NcodeE284A220Service20Development20Getting20Started20Guide20v101.1352217076.pdf` | bot-verification page, no PDF |
| 57 | 2026-09-26 | curl | `https://api.github.com/repos/NeoSmartpen/Documentations/contents` | refused: GitHub API access not enabled for this session |
| 58 | 2026-09-26 | WebFetch | `https://github.com/NeoSmartpen/WEB-SDK2.0` | GPL-3.0-only |
| 59 | 2026-09-26 | WebFetch | `https://nuwapen.com` | landing page; no specs |
| 60 | 2026-09-26 | WebFetch | `https://nuwapen.com/products/nuwa-pen` | 143 x 10.75 mm; ~28 g; triple camera 1.63 mm image diagonal; "any paper"; USD 299 pre-order |
| 61 | 2026-09-26 | WebSearch | `Nuwa Pen shipping delivery 2026 backers update` | TechCrunch 2023; Kickstarter update 27; founder X post |
| 62 | 2026-09-26 | WebSearch | `Nuwa Pen three cameras ordinary paper how it works review hands-on accuracy` | press coverage (secondary) |
| 63 | 2026-09-26 | WebFetch | `https://support.nuwapen.com/articles/8534195-when-will-my-nuwa-pen-ship` | no concrete timeline |
| 64 | 2026-09-26 | WebFetch | `https://techcrunch.com/2023/05/19/nuwa-pen/` | prototype limitations (19 May 2023) |
| 65 | 2026-09-26 | WebFetch | `https://x.com/marctuinier/status/1946946912160038931` | HTTP 402 (text known only from search snippet; post ID decodes to 2025-07-20 UTC) |
| 66 | 2026-09-26 | WebFetch | `https://www.kickstarter.com/projects/nuwa/nuwa-pen-ai-powered-ballpoint-pen/posts/4218845` | HTTP 403 |
| 67 | 2026-09-26 | WebSearch | `Nuwa Pen "run out of funds" OR "ran out of funds" 2025 shipped 100 pens` | founder X post snippet; PR Newswire 21 Feb 2025 |
| 68 | 2026-09-26 | WebFetch | `https://www.prnewswire.com/news-releases/nuwa-launches-crowdbuilding-project-empowering-customers-to-help-shape-the-development-of-nuwa-pen-302382449.html` | "shipping the first 6000 units" (21 Feb 2025) |
| 69 | 2026-09-26 | WebFetch | `https://nuwapen.com/en-us/pages/faqs` | HTTP 404 |
| 70 | 2026-09-26 | WebSearch | `Moleskine Smart Pen 3 Pen+ Ellipse NeoLAB Ncode paper specifications camera frame rate` | Moleskine user guide PDF |
| 71 | 2026-09-26 | WebSearch | `Rocketbook app scan handwriting recognition OCR "Rocketbook Beacons" how it works official` | Rocketbook help centre, blog |
| 72 | 2026-09-26 | WebFetch | `https://rocketbookhelp.zendesk.com/hc/en-us/articles/360006723533-Handwriting-Recognition-OCR` | HTTP 403 |
| 73 | 2026-09-26 | WebFetch | `https://www.moleskine.com/on/demandware.static/-/Sites-masterCatalog_Moleskine/default/dwfcac3d66/pdf/Pen+%20Ellipse_User%20Guide%20A4_web.pdf` | NWP-F70 (c)2018 NeoLAB; -20..+40 deg recognition angle |
| 74 | 2026-09-26 | WebFetch | `https://getrocketbook.com/blogs/news/rocketbook-app-and-ocr` | OCR features announced 5 Nov 2018; no engine/accuracy |
| 75 | 2026-09-26 | WebSearch | `OnHW dataset Ott IMU-enhanced ballpoint pens STABILO DigiPen online handwriting recognition IMWUT 2020 accuracy` | IMWUT 2020 author PDF |
| 76 | 2026-09-26 | WebSearch | `Ott "Benchmarking online sequence-to-sequence and character-based handwriting recognition from IMU-enhanced pens" IJDAR CER WER` | arXiv 2202.07036 |
| 77 | 2026-09-26 | curl | `https://arxiv.org/pdf/2202.07036` | IJDAR 2022 accepted version, full text |
| 78 | 2026-09-26 | curl | `http://download.cmutschler.de/publications/2020/IMWUT2020.pdf` | IMWUT 2020 author version, full text |
| 79 | 2026-09-26 | WebFetch | `https://www.iis.fraunhofer.de/de/ff/lv/dataanalytics/anwproj/schreibtrainer/onhw-dataset.html` | download links; no licence stated |
| 80 | 2026-09-26 | WebFetch | `https://www.iis.fraunhofer.de/en/ff/lv/dataanalytics/anwproj/schreibtrainer/onhw-dataset.html` | HTTP 404 |
| 81 | 2026-09-26 | WebSearch | `Wehbi Hamann Barth Eskofier Kämpf "Towards an IMU-based Pen Online Handwriting Recognizer" ICDAR 2021 character error rate` | arXiv 2105.12434 |
| 82 | 2026-09-26 | WebSearch | `IMU pen trajectory reconstruction drift double integration position error handwriting inertial pen zero velocity update` | Sensors 2022 (PMC9318904); IEEE TIE 2010 |
| 83 | 2026-09-26 | curl | `https://arxiv.org/pdf/2105.12434` | Wehbi et al. ICDAR 2021 full text |
| 84 | 2026-09-26 | WebFetch | `https://pmc.ncbi.nlm.nih.gov/articles/PMC9318904/` | Wehbi et al. Sensors 2022 full text |
| 85 | 2026-09-26 | WebSearch | `LSM6DSL datasheet "zero-g level offset accuracy" mg "zero-rate level" dps st.com` | ST datasheet |
| 86 | 2026-09-26 | curl | `https://download.mikroe.com/documents/datasheets/LSM6DSL.pdf (st.com download failed: HTTP/2 stream error)` | LSM6DSL DocID028475 Rev 6 (May 2017) |
| 87 | 2026-09-26 | WebFetch | `https://developers.google.com/ml-kit/vision/digital-ink-recognition` | overview; 300+ languages; offline; last updated 2024-07-10 UTC |
| 88 | 2026-09-26 | WebFetch | `https://developers.google.com/ml-kit/vision/digital-ink-recognition/android` | ~20 MB per language model; API 23+; last updated 2026-09-24 UTC |
| 89 | 2026-09-26 | WebFetch | `https://developers.google.com/ml-kit/terms` | on-device; metrics sent; last updated 2025-05-14 |
| 90 | 2026-09-26 | WebSearch | `MyScript iink SDK licensing pricing developer free tier math diagram recognition 2026` | MyScript pages; Medium pricing post |
| 91 | 2026-09-26 | WebFetch | `https://developer.myscript.com/docs/interactive-ink` | JS-rendered; no content |
| 92 | 2026-09-26 | WebFetch | `https://developer.myscript.com/pricing` | JS-rendered; no content |
| 93 | 2026-09-26 | WebFetch | `https://www.myscript.com/sdk/` | text/math/diagram/music; 70+ languages claim |
| 94 | 2026-09-26 | WebSearch | `MyScript iink SDK 4.3 release notes January 2026 on-device languages math diagram` | MyScript blog 4.3 and 4.5 |
| 95 | 2026-09-26 | WebFetch | `https://www.myscript.com/blog/multilingual-text-recognition-arrives-in-iink-sdk-4-3/` | 6 Jan 2026; ~18 MB multilingual Latin resource; 20% fewer errors (internal) |
| 96 | 2026-09-26 | WebFetch | `https://www.myscript.com/blog/myscript-iink-sdk-4-5-adds-text-to-handwriting-for-latin-script-languages/` | 1 Jul 2026; iink 4.5 |
| 97 | 2026-09-26 | WebSearch | `developer.myscript.com iink SDK "certificate" evaluation "commercial" license native SDK production contact sales` | licence PDF V.8 |
| 98 | 2026-09-26 | WebFetch | `https://medium.com/@myscriptdeveloper/new-pricing-on-myscript-developer-79c22f44e17a` | HTTP 403 |
| 99 | 2026-09-26 | curl | `https://developer.myscript.com/legal-docs/License-terms-of-use-and-sale.pdf` | MyScript terms V.8 (effective 4 Aug 2025) |
| 100 | 2026-09-26 | curl | `https://developer.apple.com/tutorials/data/documentation/pencilkit.json` | PencilKit abstract/platforms (iOS 13+) |
| 101 | 2026-09-26 | curl | `https://developer.apple.com/tutorials/data/documentation/uikit/uiscribbleinteraction.json` | Scribble on text-input views (iOS 14+) |
| 102 | 2026-09-26 | WebSearch | `Azure Cognitive Services Ink Recognizer retired date preview retirement announcement` | MS Learn archive; azure-deprecation issue #66 |
| 103 | 2026-09-26 | WebSearch | `Windows.UI.Input.Inking.Analysis InkAnalyzer handwriting recognition shapes documentation learn.microsoft.com recognize Windows Ink` | MS Learn |
| 104 | 2026-09-26 | WebFetch | `https://learn.microsoft.com/en-us/windows/apps/design/input/convert-ink-to-text` | InkAnalyzer/InkRecognizerContainer; ms.date 2020-09-24; updated_at 2026-03-04 |
| 105 | 2026-09-26 | WebFetch | `https://learn.microsoft.com/en-us/previous-versions/azure/cognitive-services/Ink-Recognizer/` | preview ended 26 Aug 2020; retired 31 Jan 2021 |
| 106 | 2026-09-26 | curl | `https://arxiv.org/pdf/1902.10525` | Carbune et al. (IJDAR 2020) arXiv version full text |
| 107 | 2026-09-26 | WebSearch | `"Representing Online Handwriting for Recognition in Large Vision-Language Models" IAM-OnDB CER Fadeeva 2024` | NOT RUN: session WebSearch budget (200) exhausted |
| 108 | 2026-09-26 | WebSearch | `InkSight derendering handwriting offline to digital ink Google 2024 arXiv TMLR evaluation` | NOT RUN: session WebSearch budget exhausted; switched to direct arXiv/dataset URLs |
| 109 | 2026-09-26 | curl | `https://arxiv.org/pdf/2402.05804` | InkSight (TMLR 06/2025) full text |
| 110 | 2026-09-26 | curl | `https://arxiv.org/pdf/2402.15307` | Fadeeva et al. 2024 (VLM online HWR) full text |
| 111 | 2026-09-26 | curl | `https://arxiv.org/pdf/2404.10690` | MathWriting full text (CC BY-NC-SA 4.0) |
| 112 | 2026-09-26 | WebFetch | `https://fki.tic.heia-fr.ch/databases/iam-on-line-handwriting-database` | HTTP 503 (twice); curl: TLS certificate expired (not bypassed) |
| 113 | 2026-09-26 | WebFetch | `https://ait.ethz.ch/deepwriting` | CC BY-NC-SA 4.0 + conditions; IAM-OnDB registration required |
| 114 | 2026-09-26 | WebFetch | `https://web.archive.org/web/2025/https://fki.tic.heia-fr.ch/databases/iam-on-line-handwriting-database` | tool cannot fetch web.archive.org |
| 115 | 2026-09-26 | WebFetch | `https://fki.tic.heia-fr.ch/databases` | HTTP 503 |
| 116 | 2026-09-26 | WebFetch | `https://github.com/brownvc/decoupled-style-descriptors` | BRUSH: 27,649 samples, 170 writers; non-commercial research only |
| 117 | 2026-09-26 | WebFetch | `http://www.nlpr.ia.ac.cn/databases/handwriting/Home.html` | HTTP 503; curl to nlpr.ia.ac.cn (Home, Online_database, Application_form) connection reset / 503 |
| 118 | 2026-09-26 | curl | `https://arxiv.org/pdf/2112.12870` | AIS (Rashkin et al.) arXiv v2 (2 Aug 2022) full text |
| 119 | 2026-09-26 | curl | `https://arxiv.org/pdf/2305.14251` | FActScore (Min et al.) arXiv v2 (11 Oct 2023) full text |
| 120 | 2026-09-26 | curl | `https://arxiv.org/pdf/2309.15217` | RAGAS (Es et al.) full text |
| 121 | 2026-09-26 | curl | `https://arxiv.org/pdf/2305.14627` | ALCE (Gao et al.) arXiv v2 (31 Oct 2023) full text |
| 122 | 2026-09-26 | curl | `https://arxiv.org/pdf/2304.09848` | Liu, Zhang, Liang 2023 verifiability full text |
| 123 | 2026-09-26 | curl/WebFetch | `https://lcsc.com/datasheet/lcsc_datasheet_2504101957_PixArt-PAW3395DM-T6QU_C41346211.pdf` | JS viewer; no datasheet text |
| 124 | 2026-09-26 | WebFetch | `https://www.lcsc.com/product-detail/C41346211.html` | PAW3395DM-T6QU listed; out of stock; price tiers look implausible (not used) |
| 125 | 2026-09-26 | WebFetch | `https://www.epsglobal.com/products/semiconductors/sensing-and-haptics/optical-navigation/pmw3389dm-t3qu` | quote-based; sample/reference kits listed |
| 126 | 2026-09-26 | WebFetch | `https://www.tindie.com/products/citizenjoe/paw3395-motion-sensor/` | breakout USD 32; OOS since 18 Oct 2024; datasheet needs PixArt NDA |
| 127 | 2026-09-26 | WebFetch | `https://www.tindie.com/products/jkicklighter/pmw3360-motion-sensor/` | PMW3360 breakout retired; SROM upload required |
| 128 | 2026-09-26 | WebFetch | `https://github.com/google-research/inksight` | code Apache 2.0; Small-p weights + dataset on Hugging Face (weights licence not stated on README) |
| 129 | 2026-09-26 | WebFetch | `https://www.cs.rit.edu/~crohme2019/` | CROHME 2019 overview |
| 130 | 2026-09-26 | WebFetch | `https://www.cs.rit.edu/~crohme2019/dataANDtools.html` | data composition; CC BY-NC-ND stated for GTDB document images only |
| 131 | 2026-09-26 | WebFetch | `https://github.com/brownvc/decoupled-style-descriptors` | second fetch: authors/venue confirmed (Kotani, Tellex, Tompkin; ECCV 2020, pp. 764-780) |

## 2. Critical synthesis

### 2.1 Bottom line

Stabilisation and capture need different sensing. Stabilisation needs short-horizon, low-latency motion of the pen relative to the paper, and published pen-tip optical flow does this well: DeltaPen reports 1 kHz per sensor and 0.068 mm mean absolute error per 10 ms window (OPT-01, OPT-02). Capture needs page coordinates held over minutes. Relative flow drifts (DeltaPen idle drift is about 2.6 mm/min, OPT-02), and inertial dead reckoning fails beyond about 0.1 s (OPT-19). Every capture pen with verified specifications reads pre-printed pattern paper (Anoto at 75 FPS, Ncode at 120 samples/s; OPT-08, OPT-10). The one "any paper" camera pen, Nuwa, has no published method or accuracy and an uncertain commercial status (OPT-13).

### 2.2 Recommended sensing path

**(i) Bench rig**
- Ground truth: paper on a motorised XY stage, or a Wacom tablet under paper as DeltaPen used (OPT-02). The pen sits in a jig with controlled tilt, azimuth and height.
- Sensor channels:
  - a PMW3360/3389 breakout at fixed Z = 2.4 mm as the 8–12 kHz reference (OPT-03, OPT-04);
  - a PAA5100JE at 15–35 mm to test a barrel mount (OPT-05);
  - an IMU;
  - P3040-class lens-less sensors as soon as PixArt supplies them (OPT-06).
- Latency path: log the stage encoder (or a photodiode edge), the sensor output, the MCU and the actuator command on one clock.
- Absolute capture: include Anoto and Ncode paper with their pens, because no vendor publishes positioning accuracy (OPT-07, OPT-08, OPT-10).

**(ii) Research pen**
- Replicate DeltaPen: two lens-less flow sensors at the tip, an IMU with the gyroscope actually used (DeltaPen did not use it), a tip-force sensor, and a USB tether first (OPT-01).
- Measure what DeltaPen left unreported: the sensor baseline, end-to-end latency and usable tilt range.
- Keep the actuated nib out of the sensors' field of view, and test whether nib motion and fresh ink corrupt the flow signal.
- For capture studies, write on Ncode or Anoto paper so that absolute reference strokes exist.
- Fallback if lens-less parts cannot be obtained: a PMW33xx sensor with custom short-Z optics, as in Flashpen. Flashpen needed a flat contact tip and cameras for yaw, which do not fit a ballpoint (OPT-03).

**(iii) Product**
- Stabilisation: lens-less optical flow at ≥1 kHz fused with the IMU. Relative motion is enough for this.
- Capture, phase 1: licensed pattern paper (Ncode or Anoto) read by a tip camera at ≥75 Hz. This is proven, but it brings recurring costs (the Ncode printing SDK is listed at USD 7,000/yr; Anoto patterns are sold as subscriptions) and ties users to proprietary paper (OPT-08, OPT-11).
- Capture, phase 2 ("ordinary paper"): optical-flow trajectories re-anchored per line or page, for example from an occasional page photo (OPT-14, OPT-27). Treat this as a research risk, not a launch feature, until bench data show recognition error close to that on tablet ink.
- Cameras need a tilt envelope of at least −20° to +40° from vertical (OPT-12). For comparison, commercial capture pens are 10.75–16.85 mm across and weigh 18–28 g (OPT-08, OPT-11, OPT-13).

### 2.3 Recognition and dataset licensing constraints (commercial product)

- **Default recogniser: Google ML Kit Digital Ink.** It is free, runs on-device and offline, covers 300+ languages and takes x/y/t strokes (OPT-20). Caveats:
  - Google publishes no accuracy figures for it.
  - Performance metrics are sent to Google, and the app must tell users so.
  - Use falls under the Google APIs Terms of Service, and reverse engineering is prohibited.
- **Other platforms.** The Apple documentation reviewed shows no public recogniser for arbitrary ink (OPT-23). Windows InkAnalyzer only helps Windows clients, and Azure Ink Recognizer was retired on 31 Jan 2021 (OPT-24).
- **Math and diagrams: MyScript iink** (OPT-21). Its developer terms grant no distribution right: 25 runtimes for internal evaluation only, online certificate activation, and MyScript may read free-trial cloud results (OPT-22). Negotiate before committing, and never route real notes through the trial.
- **Research recognisers show the ceiling from clean ink.** Carbune et al. report 2.5–4.0% CER on IAM-OnDB, and a VLM reaches 4.39% CER on DeepWriting against 14.16% for image-only OCR, so stroke timing matters (OPT-25, OPT-26).
- **IMU-only recognition is a fallback at best**: 17–18% word CER, and writer-independent CER up to 35% (OPT-16, OPT-17).
- **Datasets.** Every public online dataset checked is either non-commercial or has unverified terms (OPT-15, OPT-28–OPT-31):
  - DeepWriting: CC BY-NC-SA 4.0, plus IAM-OnDB registration;
  - MathWriting: CC BY-NC-SA 4.0;
  - BRUSH: non-commercial research only;
  - OnHW: no licence stated;
  - IAM-OnDB, CASIA and CROHME: terms unverified.

  These datasets are fine for benchmarking. Shipped models must come from a vendor or be trained on licensed or self-collected data, with consent that covers training.

### 2.4 Evaluating source-grounded summaries of noisy notes

- **Separate the error chain.** Measure (1) recognition CER/WER against a human transcript, (2) summary faithfulness to the recognised text, and (3) correctness against the human transcript. A summary can be faithful to misrecognised text and still be wrong.
- **Gold standard.** Use AIS two-stage human judgement per sentence and report Krippendorff's α. AIS reports α = 0.69 on news summaries (OPT-32).
- **Automated metrics:**
  - per-sentence citations to note spans (page, line, stroke IDs), scored for citation recall and precision by an NLI judge. ALCE's judge agrees with humans at κ = 0.70 for recall and 0.53 for precision (OPT-35);
  - FActScore-style atomic-fact precision against both the recognised text and the human transcript (OPT-33);
  - RAGAS faithfulness as a CI regression metric (OPT-34).

  Revalidate every automatic judge on our own noisy notes before trusting it.
- **Stress tests.** Inject recognition errors by CER band and plot faithfulness against CER. Low-confidence words should be flagged or shown as ink, not silently paraphrased.
- **Reference point.** In an audit of generative search engines, only 51.5% of sentences were fully supported by their citations (OPT-35).

### 2.5 What must be measured (no published data found)

1. Flow accuracy on plain, recycled, glossy and printed/lined paper, including fresh ink, as a function of tilt, height, speed and yaw.
2. End-to-end latency from paper motion to actuator command.
3. Yaw noise as a function of sensor baseline, and drift per minute on paper.
4. Interference from the moving nib and from ink.
5. Absolute accuracy of Anoto and Ncode pens.
6. Writer-independent CER from ML Kit and MyScript on our pen's strokes, relative-only versus pattern-anchored.
7. Summary citation recall and precision as a function of CER.
8. Power per sensing channel.

### 2.6 Open gaps

- The P3040 datasheet (probably under NDA).
- Licence texts for IAM-OnDB, CASIA and CROHME: the IAM-OnDB and CASIA sites were unreachable, and the CROHME page states no licence for the handwriting data.
- The OptiBasePen full text (UIST 2024), which is not in the ledger. Search snippets only mention a base-mounted mouse sensor plus two PAJ7025R3 IR sensors at up to 200 Hz, tracking an LED pen tip over roughly 6 × 6 cm.
- Nuwa Pen shipping status and accuracy.
- Livescribe camera rate, where the 72 fps figure is unverified.
- ML Kit accuracy on pen-on-paper ink.
