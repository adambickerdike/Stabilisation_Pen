# Screening survey (EXP-U01): handwriting, alternatives and willingness to pay

**Purpose.** Measure, in people with essential tremor (ET) or Parkinson's (PD), how often they still write by hand, which paper tasks they cannot replace, how well current aids and digital alternatives work, and what they would pay. It also screens volunteers for interviews (guide A) and for the comparison studies (EXP-U06/U07).

**Target sample.** At least 100 people with ET and 100 with PD (CALCULATION: with 100 answers the widest 95 % confidence interval on a proportion is about ±10 percentage points; with 200 about ±7). Recruit in the UK through Parkinson's UK and the National Tremor Foundation, and in the US through the International Essential Tremor Foundation and PD charities (see `recruitment_and_ethics.md`).

**Length.** 8–10 minutes. Online, on paper (large print, freepost envelope) and by phone with a researcher reading the questions. A family member may fill it in with the person.

**Scales.** The frequency scale matches the YouGov May 2025 survey (HAP-158) so the answers can be compared with the general population. Items are written for this study; no copyrighted rating scale is reproduced. Check licensing before adding any validated scale.

**Pre-registration.** The go/no-go thresholds in `go_no_go_criteria.csv` and the analysis below are fixed before the survey opens.

---

## Consent and eligibility

- **S0. Consent.** Information sheet shown first; tick box: "I have read the information and agree to take part." Separate optional ticks: (a) contact me about an interview; (b) contact me about future studies; (c) add me to the product waitlist. Each is optional and independent.
- **S1. Are you 18 or older?** Yes / No (No ends the survey politely).
- **S2. Age group:** 18–44 / 45–64 / 65–74 / 75–84 / 85+.
- **S3. Country:** UK / US / other (state).
- **S4. Which of these has a doctor told you that you have?** Essential tremor / Parkinson's / both / another tremor (state) / none or not sure.
- **S5. How many years since that diagnosis?** under 2 / 2–5 / 6–10 / over 10.
- **S6. Which hand do you write with?** Right / left / either. **Which hand is more affected?** Right / left / both equally / neither.

## Writing now

- **S7. How much does your condition affect your handwriting?** 0 not at all / 1 a little / 2 moderately / 3 a lot / 4 I can no longer write.
- **S8. In the last 4 weeks, how often did you write each of these by hand?** (every day / a few times a week / a few times a month / less often / never)
  - a. short lists (shopping, to-do)
  - b. notes or reminders
  - c. forms on paper
  - d. your signature on paper
  - e. cards or letters
  - f. cheques
  - g. puzzles (crosswords, sudoku)
  - h. drawing, colouring or art
  - i. writing for work or study
- **S9. For each task you do, how hard is it now?** no difficulty / some / a lot / I cannot do it.
- **S10. In the last 3 months, did you avoid writing, ask someone else to write, or have to redo something because of your writing?** Tick all that apply and the task:
  - avoided a task (which?) / someone else wrote for me (which?) / someone else signed for me (which?) / a signature or form was questioned or rejected (which?) / none.
- **S11. For the task in S10 that mattered most: could it have been typed, dictated or done online instead?** Yes, and that would have been fine / Yes, but I would rather write it / No, it had to be on paper or signed by hand / Not sure.

## Aids and alternatives

- **S12. Which of these have you tried for writing?** Weighted or heavy pen / thick or shaped grip / a pen with a clipboard or board / glove or wrist weight / stabilising gadget (state) / none. **For each tried: how satisfied (0–10)? Do you still use it?**
- **S13. Typing:** How often do you type on a phone, tablet or computer? (daily / weekly / less / never.) How hard is it (none / some / a lot / cannot)? Have you changed any touch or keyboard settings to help? (yes / no / did not know that was possible.)
- **S14. Voice:** Have you used speech-to-text (dictation) to write? (yes, often / yes, sometimes / tried and stopped / never.) How well does it understand you (0–10)?
- **S15. For your everyday writing, how much could typing or voice replace handwriting for you?** (almost all / most / about half / little / none.)
- **S16. Which devices do you have?** Smartphone / tablet / a stylus or tablet pen / computer / none.

## Product interest and price (read the caveat aloud or show it)

"The next questions ask about ideas that are being studied. None is available, and none has been shown to help anyone yet."

- **S17. Which ideas would you consider?** (tick any) A pen that steadies itself / a tablet app with a stylus for practice and larger, clearer writing on screen / a practice kit with a therapist / a desk writing surface / none.
- **S18. Price (randomised arm).** Each respondent sees one price for the pen idea, allocated at random from four arms: **150 / 250 / 500 / 800** (GBP in the UK, USD in the US).
  "If a pen existed that was proven to make your everyday handwriting clearly easier to read, how likely would you be to buy it at [PRICE]?" Definitely / Probably / Not sure / Probably not / Definitely not.
- **S19. What is the most you would pay for such a pen?** (open number; optional)
- **S20. Who would pay?** Me / my family / NHS or insurer / my employer / a charity / not sure.

## Close

- **S21. Would you be willing to try writing aids and typing or dictation in a 60–90 minute research session?** Yes / Maybe / No. (Feeds EXP-U06 recruitment.)
- Thank you and helpline details (Parkinson's UK, tremor charities).

---

## How the answers become the go/no-go metrics

| Metric | Items | Definition (fixed in advance) |
|---|---|---|
| GNG-1 still writing by hand weekly | S7, S8 | Among respondents with S7 ≥ 1, the share with "every day" or "a few times a week" for at least one of S8 a–e |
| GNG-2 unserved paper job | S10, S11 | Share with at least one avoided, delegated or rejected paper task in S10 **and** S11 = "No, it had to be on paper or signed by hand" |
| GNG-3 passive aids insufficient | S12 | Among those who tried a weighted or grip pen, the share scoring it ≤ 5 of 10 |
| GNG-4 digital alternatives sufficient | S13–S15 | Share answering "almost all" or "most" in S15 **and** typing or dictation difficulty "none" or "some" |
| GNG-5 willingness to pay | S7, S8, S18 | In the serviceable subgroup (S7 ≥ 2 and weekly writing per GNG-1), the share answering "Definitely" at the 500 arm; the no-go check uses the 250 arm |

**Analysis.** Proportions with Wilson 95 % intervals, per diagnosis (ET, PD) and per country; no pooled claim across ET and PD (REQ-USR-001). Missing answers are reported, not imputed. Stated purchase intent overstates real buying (ASSUMPTION), so GNG-5 is read together with the waitlist test (EXP-U05, GNG-6).

**Data protection.** Health data are special-category personal data: collect only what is listed; keep contact details apart from answers; delete contact details 12 months after the study unless the person opted in to future contact (ASSUMPTION of a retention period; set by the sponsor's data protection officer).
