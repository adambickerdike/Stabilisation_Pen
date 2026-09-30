"""Fixed text used by the studies.  All of it is SYNTHETIC note text (written
for tests and demos), not text from any person's notes.

APP_NOTE_LINES   the note lines of app/demo.py and app/tests/conftest.py
EXTRA_NOTE_LINES further note-like lines composed for this study (out of the corpus domain)
RARE_LINES       lines with proper nouns and rare words for the autocorrect study
GUIDE_SENTENCE   the sentence the synthetic writer writes in the closed-loop study
CALIB_SENTENCE   a different sentence by the same writer, used to estimate the style before the study sentence
"""
from __future__ import annotations

APP_NOTE_LINES = [
    "buy milk eggs and bread", "return library books by friday", "call the plumber at 9 am",
    "pen rev a bench test on monday", "check hall sensor offset", "order spare refills",
]

EXTRA_NOTE_LINES = [
    "pick up the prescription on tuesday", "water the plants and feed the cat", "send the report to the team",
    "book a table for four at seven", "take the car to the garage", "pay the gas bill before the end of the month",
    "ask about the new bus times", "bring a coat it will rain", "clean the kitchen and take out the bins",
    "phone the bank about my card", "buy stamps and post the letters", "meet the neighbours for tea on sunday",
]

# proper nouns and rare words (names, foods, places, brands) - deliberately outside the training vocabulary
RARE_LINES = [
    "email dr okafor about the scan", "meet zoltan at the kowalski deli", "buy quinoa tahini and sumac",
    "call priya about the invoice", "renew the passport for siobhan", "drive to llandudno on saturday",
    "order the ikea shelf for anneliese", "ask mr nakamura for the key", "pick up kombucha and kimchi",
    "text bartholomew the new address",
]

GUIDE_SENTENCE = "return library books by friday"
CALIB_SENTENCE = "the quick brown fox jumps over the lazy dog"
