# Rev J.1: fixing the Rev J budgets and loads (round 3) — DRAFT, work in progress

**Status: draft, 2026-09-29. Sections are being filled as calculations finish. Numbers below are labelled; nothing is measured.**

## Findings so far (draft notes, to be rewritten)

### P1 gimbal axial load
- Study N's cross-strip pivot (301 FH, 50 um x 2.55 mm x 3.8 mm, +-45 deg, crossing at mid-length) buckles at 16.3-16.5 N of
  axial compression in a non-linear beam model of the whole pivot (CALC, revj1/gimbal.py; converged to 1 % with 16-48
  elements). The image-method pull is 16.5 N (upper bound). Safety factor about 1.0, not the 1.24 of the per-strip Euler
  estimate.
- Strips in tension (the Rev J proposal) have two problems (CALC, beam model):
  - crossing at mid-length: the pull makes the pivot unstable (-14 mN m/rad at 16.5 N against +2.8 unloaded);
  - crossing near one end (lambda 0.04-0.08) keeps the stiffness positive and flat, but a strip under tension bends in a
    short boundary layer at its clamp: peak strain about theta x sqrt(3 sigma_axial / E), 0.0036 at the usable angle and
    16.5 N; Goodman safety factor 0.7-1.2 even with 10 mm wide strips. Fails fatigue.
- Thicker strips in compression work: 75 um x 2.55 x 3.8 mm buckles at 55-56 N (3.4 x the upper-bound pull), stiffness
  9.4 mN m/rad unloaded, 22.8 at 16.5 N; strain 0.00133 at the usable angle; Goodman SF 2.0 at 16.5 N (fully reversed full
  travel). 100 um x 5 mm: 76 N, SF 2.3.
- Thrust pivot: the refill holder passes the gimbal's centre, so no on-axis pivot; sliding friction mu F r gives tens of mN at
  the ball (dead band tens of um): rejected.

### P4 end-cap (SIM, study K's model H1, read-only)
- Tuning seeds, split 0.5, 8-12 Hz x 1-2 mm: further reduction 20.2 / 19.4 / 18.6 / 17.7 / 16.3 / 15.2 % for end-caps of
  45.0 / 36.3 / 31.6 / 28.0 / 24.4 / 22.0 g (slug 28.8 ... 9.6 g). Split 0.3: 6.0 ... 3.1 %.
- Test seeds: 45 g reproduces study K exactly (8.0 / 18.2 / 19.5 %); 31.6 g: 5.6 / 16.8 / 18.3 % (passes R-T1).

### P6 motor detent
- Faulhaber 0620 B housing is aluminium, black anodized (MFR, datasheet edition 2026-07-28): no shielding from the housing.
