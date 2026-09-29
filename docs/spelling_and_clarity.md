# Spelling help, text prediction and clearer handwriting (study S)

**Status: DRAFT, results arriving (2026-09-29).** Labels: SIM (simulation), CALC (calculation on recorded data),
LIT + ledger id, MFR, ASSUMPTION, PROPOSED DESIGN. Nothing here was measured on people or on a pen.

## The answer in plain words

(pending: filled when the last stage finishes)

## Details

### T1. Recognising letters while they are written (task 1)

- **Data (CALC on real handwriting).** UJI Pen Characters v2, lower-case letters (CC BY 4.0, CON-48): 60 writers, each
  letter in 2 non-consecutive sessions. 34 writers train, 6 tune, 20 test. The 20 test writers are used only for the
  final numbers.
- **Model.** A causal 2-layer GRU (114,842 parameters) reads the pen path point by point and gives a probability for
  each of the 26 letters after every point. Trained with tremor added (rule O1 chose the tremor variant: it tied with
  the sigma-lognormal variant within 0.5 points and is simpler).
- **Result on new writers (test).** 82 % of letters read at the letter's end (top 3: 94 %); 52 % at half the letter.
  With 1 mm tremor (0.33 x-height): 73 %. With one calibration sample per letter from the writer's other session:
  86 % at the end, 60 % at half.
- **Cost.** 113,568 multiply-accumulates per point; 0.19 ms per point on this container's CPU (7.5 ms for a median
  letter); 112 kB as int8; about 1.8 ms per point on a 128 MHz Cortex-M33 (CALC).
