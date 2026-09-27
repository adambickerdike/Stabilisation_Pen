# AMF: miniature actuators, drivers, flexure materials, magnets, small cells and touch-temperature limits

Stream: AMF (actuators, drivers, flexures, magnets, cells, touch temperature)
Ledger: `docs/research/ledger/AMF_actuators_materials.csv` (AMF-01 to AMF-40)
Evidence retrieved: 2026-09-26 for all ledger sources. A few re-reads for verification ran on 2026-09-27 and are listed in section 1.3.

Method notes
- Datasheet PDFs were downloaded with `curl` and converted to text locally (pdfplumber). Image-only drawings (Moticont) and graphs (TI DRV2700 Fig. 8-2, IEC 60601-1 Tables 23/24) were rendered to PNG and read visually. Web pages were read through WebFetch or as raw HTML.
- The shared session WebSearch budget (200 calls) ran out at query W24. After that, sources were reached only by direct URLs on manufacturer, publisher or standards domains, by site-internal navigation (sitemaps, product listings), and by record lookups by identifier (Europe PMC by DOI, Crossref by DOI or PII). No general search engine was used to work around the budget.
- Blocked sources were not bypassed: Cloudflare 403, captchas, the web.archive.org egress block and Akamai 403s are all logged below.
- In the ledger, "MY CALC" marks my own arithmetic. Km = Kf/sqrt(R), and holding power P = (F/Km)^2 per axis.

## 1. Search log

### 1.1 WebSearch queries (exact strings, all 2026-09-26)

| # | Query | Outcome |
|---|---|---|
| W1 | `smallest voice coil actuator datasheet force constant N/A resistance diameter 10 mm BEI Kimco LA05` | BEI LA05-05-000A press release (snippet) -> AMF-05 |
| W2 | `Sensata LA05-05-000A voice coil actuator datasheet` | Sensata PDF and product pages all HTTP 403 |
| W3 | `"LAH04-10-000A" datasheet continuous stall force resistance force constant` | distributor snippets; Sensata drawing 403 -> AMF-05 |
| W4 | `"LA05-05-000A" actuator constant stroke force ozf BEI Kimco tiny` | press-release summary (2.5 ozf, 1.02 mm, 1.04 N/sqrt(W)) -> AMF-05 |
| W5 | `SupT Motion miniature voice coil actuator VCAR 10 mm diameter force constant resistance datasheet` | no SupT datasheet; linearmotiontips article naming H2W minis -> AMF-04 |
| W6 | `H2W Technologies NCC01-04-001-1X datasheet force constant resistance` | H2W product pages -> AMF-04 |
| W7 | `Akribis AVM voice coil motor smallest diameter 12 mm force constant motor constant datasheet` | Agito-Akribis AVM catalogue PDF -> AMF-03 |
| W8 | `Dongwoon DW9784 OIS driver Hall sensor datasheet output current` | HMI pages DW9784 and DW9786 -> AMF-08 |
| W9 | `ROHM OIS driver IC BU24 Hall amplifier VCM driver output current datasheet` | BU24025MWV (Mouser link, HTTP 503) -> AMF-10 |
| W10 | `rohm.com BU24025MWV datasheet pdf OIS controller` | ROHM OIS white paper (rohm.com 403; pdf4pro mirror) -> AMF-10 |
| W11 | `onsemi LC898 OIS controller datasheet Hall amplifier VCM driver 2-axis gyro` | onsemi.com 403 (Akamai); onsemi.cn LC898121XA Rev 4 -> AMF-09 |
| W12 | `OIS voice coil actuator smartphone camera stroke ±100 µm coil resistance ohm force mN Hall sensor paper IEEE Transactions on Magnetics` | paywalled papers only; no numbers |
| W13 | `mdpi optical image stabilization voice coil motor actuator stroke coil resistance current Hall feedback smartphone camera module design` | no open numeric source |
| W14 | `Asahi Kasei Microdevices OIS driver IC VCM Hall AK73 datasheet output current` | no public AKM OIS driver datasheet found |
| W15 | `"OIS" actuator "stroke" "±" "µm" "coil resistance" VCM camera module specification` | Apple US10187573B2 (up to 200 um) -> AMF-07 |
| W16 | `OIS VCM motor specification "OIS stroke" "resistance" Ω "Hall" X Y lens shift camera actuator manufacturer` | patents and CML SMA pages; no OIS VCM datasheet |
| W17 | `PI PICMA bender PL112 PL122 PL127 PL140 datasheet blocking force displacement capacitance` | PI datasheet 31.07.2020 -> AMF-11 (search snippet values differed from the datasheet; the datasheet was used) |
| W18 | `Thorlabs piezoelectric bimorph bender PB4NB2S blocking force displacement capacitance voltage specifications` | Thorlabs pages are JS-rendered; summary only -> AMF-12 |
| W19 | `Thorlabs PB4NB2W "blocking force" "capacitance" bender 150 V ±450 µm` | page titles only -> AMF-12 |
| W20 | `piezo.com bending actuator Q220-A4-203YB blocked force free deflection capacitance datasheet` | Q220-A4BR-1305YB and -2513YB pages -> AMF-13 |
| W21 | `Cedrat CTEC APA50XS APA60S APA120S amplified piezoelectric actuator stroke blocked force stiffness capacitance datasheet` | Cedrat product pages -> datasheets -> AMF-14 |
| W22 | `New Scale Technologies SQUIGGLE SQL-RV-1.8 micro motor stall force speed holding force unpowered datasheet` | Tech bulletins Rev G and Rev H -> AMF-15 |
| W23 | `Materion Alloy 25 C17200 strip datasheet fatigue strength 10^8 cycles modulus yield strength TH04 HT` | Not executed: WebSearch budget exhausted |

### 1.2 Direct retrievals (WebFetch or curl, 2026-09-26)

- VCM: moticont.com/lvcm-010-013-01.htm (brief URL) and the drawing PDFs linked from moticont.com/voice-coil-motor.htm (AMF-01, AMF-02). The powersystemsdesign.com LAH04 article (AMF-05). The motioncontroltips.com and linearmotiontips.com miniature-VCA articles (leads only). psdl.engin.umich.edu publications -> J18.pdf and T2.pdf (AMF-06, AMF-26).
  - Blocked: automation.com (403); octopart, rs-online, globalspec (403); web.archive.org (egress policy); azcus.digikey.com (DNS failure).
- OIS: hmisemi.com/dw9784 and /dw9786 (AMF-08); onsemi.cn LC898121XA (AMF-09); pdf4pro ROHM mirror (AMF-10); nmbtc.com blog (no data); Google Patents WO2014008012A1 (no numbers) and US10187573B2 (AMF-07).
  - Crossref DOI or PII lookups for 10.1016/j.sna.2020.112014 and 10.1007/s00542-017-3454-1 returned no abstracts.
  - Blocked: st.com OIS white paper (HTTP 503 / empty reply); rohm.com (403); ScienceDirect and ResearchGate (403); Springer (login redirect).
- Piezo: pi-usa.us PL112-PL140 datasheet (AMF-11); piezo.com pages, verified in raw HTML (AMF-13); cedrat-technologies.com APA50XS, APA60S-1 and APA120S datasheets (AMF-14); mmech.com APA table (not used; datasheets preferred); newscaletech.com SQL-RV bulletins (AMF-15); ti.com DRV2700 and DRV2667 (AMF-16, AMF-17).
  - Blocked: thorlabs.com (JS app); thorlabschina.cn (connection reset); govolition.com and meetoptics.com (403 or empty).
- Materials: materion.com literature listing -> Alloy 25 strip, plate, rod, tube and wire PDFs; only the strip sheet is used (AMF-18). alloys.copper.org/alloy/C17200 (AMF-19). makeitfrom.com Ti-6Al-4V, 17-7PH (CH900/RH950/TH1050) and 301 pages (AMF-20). azom.com ArticleID=1547 (AMF-21). en.wikipedia.org Nickel_titanium (AMF-22). Europe PMC REST `query=DOI:"10.1016/j.jmbbm.2007.08.001"` (AMF-23). victrex.com 450G TDS (AMF-24). dupont.com/products/kapton-hn.html -> qnityelectronics.com EI-10142 (AMF-25).
  - Not accessible: clevelandcliffs.com (no 17-7PH bulletin found); aksteel.com (502); ulbrich.com (403); asm.matweb.com (connection reset/503); timet.com (404); fwmetals.com (no data); Confluent and Johnson Matthey Nitinol pages (404); PubMed (captcha).
- Magnets and wire: vacuumschmelze.com -> VACODYM grade table (AMF-27); kjmagnetics.com/specs.asp (AMF-28); nvlpubs.nist.gov NBS Handbook 100 (AMF-29); en.wikipedia.org Insulation_system (AMF-30).
  - Not accessible: arnoldmagnetic.com ("coming soon" site); product.tdk.com (403).
- Cells: eemb.com categories 33, 34 and 36 -> product-18 (LIR10440) and product-34 (LIR1255) with spec PDFs (AMF-31, AMF-32); grepow.com sitemap -> ultra-narrow and button pages (AMF-33).
  - Blocked: varta-ag.com (Link11 captcha, both curl and WebFetch); panasonic industrial/energy (403). EEMB lists no 10180, 10280 or 10440-LiFePO4 cells; its smallest LiFePO4 is LIP14500.
- Touch temperature: ecma-international.org ECMA-287 2nd ed. (AMF-35); archive.org gov.in.is.13450.1.2008 (IEC 60601-1:2005 identical adoption), OCR text plus page render (AMF-34).
  - Not accessible: webstore.iec.ch previews (JS shell only); standards.nasa.gov (404). Wikipedia IEC 60601 and IEC 62368-1 pages had no limit values.
  - IEC 62368-1 Table 38 text was not accessed.
- Drivers and current sense: ti.com/lit/ds/symlink for DRV8212, DRV8214, DRV8234, DRV8837, INA240, INA241A, INA296A and INA181 (AMF-36 to AMF-40).

### 1.3 Verification re-reads (2026-09-27, UTC, after midnight)

- The H2W NCC01-04-001-1X and NCM01-04-001-2IB raw HTML tables were re-read and matched the WebFetch extraction.
- The Google Patents US10187573B2 raw text was re-read to confirm the "up to 200 microns" and "<50% of maximum output current" passages.
- The final URL of the VAC VACODYM page was checked.

## 2. Critical synthesis

### 2.1 Actuator candidates (all per axis; * = my calculation)

| Candidate (ledger) | Envelope | Stroke | Force | Km (N/sqrt(W)) / hold power at 0.3 N and 1.6 N | Drive | Fragility / notes |
|---|---|---|---|---|---|---|
| Moticont LVCM-010-013-01 (AMF-01) | Ø9.5 x 12.7 mm | 6.4 mm | 0.28 N cont / 0.88 N 10% | 0.21* / 2.0 W, 58 W* | ~2-10 V | robust; too weak even with a lever |
| Moticont LVCM-013-013-03 (AMF-02) | Ø12.7 x 12.7 mm | 3.2 mm | 1.42 / 4.48 N | 0.83* / 0.13 W, 3.7 W*; with 3:1 lever 0.015 W, 0.41 W* | <3 V | robust; best verified Km in the bore |
| Akribis AVM 12-6.4 (AMF-03) | Ø12.7 x 12.7 mm | 6.4 mm | 0.91 / 3.53 N | 0.54 / 0.31 W, 8.9 W*; 25.6 K/W* | 3.2 V at 1.6 N* | robust; the only published thermal constant |
| H2W NCC01 / NCM01 (AMF-04) | Ø10.2-11.1 mm | 2.5-3.2 mm | 0.27-0.45 / 0.80-1.34 N | 0.34-0.36 / 0.67-0.80 W, 19-23 W* | 5-8 V at 1.6 N* | NCM has a sliding bearing |
| BEI LA05-05-000A (AMF-05) | 12.7 x 12.7 mm | 1.02 mm | 0.69 N (type unstated) | 1.04 claimed (unverified) / 0.08 W, 2.4 W* | ? | frameless; verify |
| PI PL127.10 / PL140.10 (AMF-11) | 31 x 9.6 / 45 x 11 mm | ±450 / ±1000 µm | ±1.1 / ±0.5 N blocked | ~0 W hold; ±77-78 µm reachable at 1.6 N with an ideal lever* | 0-60 V | brittle ceramic |
| Cedrat APA50XS (AMF-14) | 5 x 13 x 9 mm | 66 µm | 16 N blocked | ~0 W; 41 µm at 1.6 N* | -20 to 150 V | APA60S/120S do not fit a 13 mm bore* |
| New Scale SQL-RV-3.4-15 (AMF-15) | 4.75 x 4.5 x 11.2 mm | 15 mm | 3 N stall | 0 mW off-power hold; 5 W moving | 6 V | >7 mm/s; >300k-cycle life; OEM-only |

No in-bore actuator gives ±0.5 mm against 1.6 N at zero holding power.

- **Piezo** holds at zero power but lacks work. The in-bore maximum per-direction Fb x df is about 0.5 mN·m, against the 3.2 mN·m or more needed (4 x 1.6 N x 0.5 mm)*.
- **SQUIGGLE** holds but is too slow. ±0.5 mm at 8 Hz needs 25 mm/s*, and 300k cycles lasts about 10 h at 8 Hz*.
- **VCMs** have the force but pay continuously in heat.

The workable architecture is an LVCM-013-013-03-class VCM driven through a flexure lever of about 3:1. That gives a nib Km of about 2.5 N/sqrt(W): 15 mW at 0.3 N and about 0.41 W at 1.6 N*. The lever multiplies the reflected moving mass by 9 (about 49 g)*, which still needs only about 0.1 N at 10 Hz and 0.5 mm*.

Hot operation cuts Km by about 17% at +60 K (copper α20 = 0.00393/K plus Br at about -0.12 %/K)* (AMF-27, AMF-29). If zero-power holding is mandatory, it must come from a separate lock or a passive load path, not from these piezo parts. OIS-class VCMs (≤200 µm stroke, AMF-07) are unsuitable.

### 2.2 Flexure material

The recommended material is **C17200 (Alloy 25) TH04 strip**. It is non-magnetic, has E 127-131 GPa, a typical yield of 1241 MPa, and a typical fatigue strength of 310 MPa at 1e8 cycles (AMF-18, AMF-19).

Provisional allowables:
- alternating bending stress: 150 MPa or less (fatigue strength / 2);
- peak stress: yield/4, about 310 MPa, or less (the SF 4 on yield in AMF-06).

Sizing follows AMF-26: for a fixed-guided beam, L ≥ sqrt(3·T·δ/α). With T = 0.1 mm this gives L ≥ 11.3 mm*. Form the part before ageing, and control beryllium dust.

- **Ti-6Al-4V** is the non-magnetic alternative. Its fatigue/E ratio is about 2x higher*, but that value is low-provenance (AMF-20, AMF-21).
- **17-7PH and full-hard 301:** avoid near the magnets. My judgement is that both are ferromagnetic, and their data here are low-provenance.
- **Nitinol:** avoid. Fatigue is strain-based and the modulus depends on phase (AMF-22, AMF-23).
- **PEEK:** avoid for preloaded flexures (no creep or fatigue data, AMF-24).
- **Kapton:** use for the flex leads only (AMF-25).

### 2.3 Cell shortlist

1. **EEMB LIR10440** (AMF-31): 10.3 x 44.5 mm, 320 mAh, 1C (0.32 A) continuous, ≤80 mΩ, 1.18 Wh*, bare cell. It fits a 10.5-11 mm bore, but the 1C ceiling means the lever and high-Km design is mandatory.
2. **Grepow GRP5811047 / GRP6711060 narrow pouch** (AMF-33): 200-300 mAh, 20-30C claimed, 11 mm wide, 12.4-12.8 mm diagonal*. It needs a bore of 13 mm or more, a PCM and swelling allowance, and a proper datasheet.
3. **Coin cells** (LIR1255: 65 mAh, 1C; GRP1254: ≤96 mAh, ≤3C) are unsuitable for actuation (AMF-32, AMF-33).

Varta CoinPower and Panasonic pin cells could not be verified (sites blocked). No named-manufacturer datasheet was found for 10180, 10280 or 10440 LiFePO4 cells. Treat hobby-brand claims as unverified.

### 2.4 Provisional touch-temperature limit

Use **43 °C absolute** for any continuously held surface, with a **design target of ≤41 °C**. The sources are:
- IEC 60601-1:2005 Table 24: contact of 10 min or more, all materials, 43 °C; above 41 °C the temperature must be disclosed (AMF-34);
- ECMA-287 Table 5.2: continuously held, 43 °C (AMF-35).

Metal parts touched for 1 min or more that are not continuously held may reach 48 °C (Table 23). At 25 °C ambient this leaves a surface rise of 16-18 K or less; at 35 °C ambient it leaves only 6-8 K.

IEC 62368-1 Table 38 was not accessed and must be confirmed. IEC 62471 (photobiological safety) is not relevant.

### 2.5 Drivers and current sense

- **Per axis:** a DRV8212 (1.65-11 V, 280 mΩ, PWM up to 100 kHz, 2 x 2 mm) with an inline shunt and an INA241A (1.1 MHz, PWM rejection up to 125 kHz, SOT-23-8) or INA240 (400 kHz, 93 dB AC CMRR at 50 kHz), so that force control has signed coil current (AMF-36, AMF-38, AMF-39).
- **Compact alternative:** DRV8214. Its IPROPI error of ±5% and its current regulation are acceptable only inside a Hall or encoder position loop (AMF-37).
- **Reject:**
  - DRV8234, because VM must be at least 4.5 V;
  - INA181 for coil current (low-side monitoring only);
  - linear OIS drivers: from 1S, driver loss is far above coil loss*, the current limit is 200-300 mA, and the documentation is NDA-gated (AMF-07 to AMF-09).
- For piezo, if used at all: DRV2700 with the boost at 30-55 V (Iq 5-9 mA) (AMF-16).

### 2.6 What must be measured

1. **Nib load in real writing:** the transverse load spectrum (mean, RMS, peak, and direction relative to pen roll). This decides whether 1.6 N is a continuous or a rare design case.
2. **Actuator:** Km versus position and current for the chosen VCM plus lever, measured cold and with the coil at 60-80 °C. Also magnet-induced negative stiffness.
3. **Thermal:** coil-to-grip thermal resistance in the barrel, and the surface temperature map versus dissipation with a hand, at 25 °C and 35 °C ambient.
4. **Cell:** voltage sag, capacity and cell temperature under the real current profile (1-3C) for the 10440 and pouch candidates.
5. **Flexure:** fatigue coupons of C17200 TH04 at 150 MPa to 1e7-1e8 cycles, plus stiffness and parasitic motion.
6. **Electronics:** current-sense accuracy, PWM acoustic and EMI noise, and driver losses.
7. **Unverified leads:** BEI LA05-05-000A Km, Thorlabs bender specs, OIS IC access, and IEC 62368-1 Table 38.
