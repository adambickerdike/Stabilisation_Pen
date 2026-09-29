# How the Pen Works: the Rev J explainer page

An interactive page for people with essential tremor, Parkinson's, poor handwriting or dyslexia, and for the people
who help them. It explains how the Rev J pen moves the ink and how much the writing may improve. Every number carries
an evidence label (SIMULATION with its model, CALCULATION, LITERATURE + ledger id, ASSUMPTION, PROPOSED DESIGN, or
ILLUSTRATION for drawings). Nothing on the page has been measured on a real pen or person.

## What the page shows

The page opens with a **simple view**. Everything else sits in a closed **Details** section.

1. **Three parts that move.** One sentence each: what moves, what pushes it, what it does to the ink.
   - The inner pen at the tip (with a note: being redesigned, see Known problems).
   - The heel wheel under the front ring (retracted by default; lowered only when the writer turns guidance on).
   - The tail weight in the end-cap: Rev J.1's lighter end-cap (29.6 g, a 17.3 g weight, a further 6–18 %), optional
     until it beats the same weight locked in place. The first design's 8–20 % appears only in Details.
2. **See it move.** A 2-D cut-away of the pen, drawn to scale from the layout, with four animations and numbered,
   labelled arrows:
   - *Hand shake* (the handle and hand shake, the whole inner pen swings the other way about its pivot, the ball stays
     on the line);
   - *Writes for you* (autowrite, replayed from simulation data, with the ink seen from above);
   - *Heel wheel* (the paper pushes the whole pen; seen from above, the wheel steers along practice loops);
   - *Tail weight* (the weight is pushed against the shake).
   The shake is drawn 3× bigger and 12× slower, and the page says so. The idealised drawing is followed by one honest
   line: in the simulations the pen removed about half the wobble, not all of it.
3. **The pen in 3-D.** Colours show what moves by default (inner pen, pivot, coils, heel drive, tail weight, handle,
   fixed parts); "Part groups" switches to the component groups. "Hand shake" animates the handle and hand while the
   inner pen keeps the ball still. Take apart, see inside, end-cap on or off, the tip pad and four cameras remain.
4. **How much better?** One row per condition. Each row has a without/with picture pair, drawn from simulated writing
   where the study saved it. Otherwise it has an illustration or the text the reading program read. Each row has ONE
   number (for example "words read correctly 31 % → 74 %") with its evidence label. The source file shows on hover
   and under the number. There are no micrometre tables in the simple view. The autowrite row says it is suspended as a hardware claim (the current inner
   pen would overheat), with a link to Known problems.
5. **How sure are we?** One line: simulation only, not tested on a prototype or with people.
6. **Known problems (being fixed).** Four plain lines, each with its evidence label:
   - (a) holding the ball on the paper costs the inner pen's coils 1.6 W at 50° and 4.7 W at 35° (CALCULATION, the
     independent review's formula; SIMULATION, sim2 found the same load in a writing run); the coils would overheat
     within about a minute, so every Rev J battery and heat figure is suspended while a balanced nib is designed;
   - (b) the heel wheel moved clean writing by about 0.4 mm in the physics simulation, so it stays retracted unless
     the writer turns guidance on (SIMULATION; the mean of the range in `docs/revJ_simulation.md` §8.2, which the
     label shows);
   - (c) the page sensor was assumed accurate to 3 µm; DeltaPen (2022) measured about 24–68 µm (ASSUMPTION;
     LITERATURE OPT-02);
   - (d) all writers and shakes so far are made up; study R brings in real recordings.
   Beside them, **the side-load figure** (one SVG, two panels): (1) at the ball, magnified: the refill spring along
   the pen, the paper's push straight up, and its part along the pen (it balances the spring) and across it (the
   sideways push), to one force scale; (2) the inner pen as a lever, drawn flat and to scale: the sideways push on the
   76.5 mm ball arm against the magnets' 0.84 N on the 11.5 mm arm. The caption gives the lever equation and the cost.
7. **Details** (closed blocks):
   - the physics;
   - the parts, one by one (component table, budgets, technologies); every battery-hours and heat figure is marked
     "suspended (see known problems)" and links to the panel;
   - the five modes;
   - all results with every number (table, what the AI does and does not do, strips at real size);
   - six simulation replays in 3-D, built only when their block is opened;
   - holding a pen;
   - who it helps;
   - limits and first tests (integration problems, how far to trust the simulations);
   - what changed from Rev H;
   - where the numbers come from.

In the design documents and some tables the inner pen is called the "nose" or "moving nose"; the Details section
says so.

## Files

| File | What it is |
|---|---|
| `template.html` | The page source: HTML, CSS and JS in one file. Edit this, not `index.html`. |
| `build.py` | Builds `data/*.json` from `results/`, fills the `<!--BUILD:...-->` placeholders and `[[fact]]` tokens, writes `index.html`. |
| `index.html` | Generated page (about 380 kB, of which about 100 kB are the "How much better?" pictures). It loads `data/*.json` with relative `fetch()` calls. |
| `data/*.json` | Generated data (about 670 kB). See below. |
| `smoke_test.js` | Playwright check at 1360 × 900 and 390 × 844, with screenshots. |

## Rebuild

```sh
python3 viewer/explainer/build.py
```

Run it whenever a results file changes. It prints which source each data file came from (final or provisional) and
any warning. The page lists the same under Details → "Where the numbers come from".

## Changing a mechanism or a result (studies W, R, S and later)

The simple view is data-driven, so a new study can replace a mechanism or a result without redesign:

- **Mechanism sentences:** `MECHANISMS` in `build.py`. Each entry has a key, colour token, name, one sentence (with
  `{tokens}` from `fact_tokens()`, all read from results files), short uses and evidence labels with the source on
  hover.
- **"How much better?" rows:** `simple_rows()` in `build.py`. Each row has:
  - the condition and which mechanism helps;
  - a picture spec: a panel and two variant keys of `data/samples.json` with an x-window in mm, or the loops
    illustration drawn from two numbers;
  - ONE number read from `data/pen.json`, and its evidence label and source.
  To show a new study's result, add its facts in `build_facts()` and its strips in `build_samples()`, then point a
  row at them. For example, real recorded handwriting from study R becomes a new samples panel and a new picture
  spec.
- **The cut-away** draws every component of the layout. Colour and motion come from the layout's `moves_with`
  (`nose`: swings with the inner pen; `drive`: heel wheel; `inertial_mass`: tail weight) and `group` fields, so a
  new `results/revJ/layout.json` redraws itself. The animations' sizes and speeds are in `CUTCFG` in
  `template.html`. The autowrite replay uses the `autowrite_example` panel of `samples.json`.
- **The 3-D "what moves" colours** use `MOVECATS` in `template.html` (the same `moves_with` and `group` rules).
- **Known problems:** `KNOWN_PROBLEMS` in `build.py`, one entry per line (a bold lead, one or two short sentences with
  `{tokens}`, evidence labels with their sources). The numbers come from `facts_sideload()` (the refill spring, Km,
  coil resistance and thermal model from `results/revJ/sim_params.json`; the two arms from the layout, to 0.1 mm as
  the design documents quote them; checked against the review's 4.717 / 1.628 / 0.166 W, with a build warning above
  2 %) and `facts_known()` (the heel wheel's range and mean from `docs/revJ_simulation.md` §8.2, the simulated 1.1 W
  from §8.1, the coil limit and time from its summary, the page sensor's assumed noise from `sim_params.json`,
  DeltaPen from `docs/evidence.csv` OPT-02). The figure is `sideload_svg()`. When the balanced nib (study B)
  replaces the C1S nose, drop or rewrite line (a) and the figure, and remove the "suspended" marks in `template.html`
  (search for `class="susp"`).

## Data files and fallbacks

| Page file | Source | Fallback |
|---|---|---|
| `data/layout.json` | `results/revJ/layout.json` | `results/revH/layout.json` (the page says it is Rev H) |
| `data/pen.json` | facts with labels and sources: `results/revJ/{budgets,revJ}.json`, `results/ai2/ai2.json`, `results/nose2/nose2.json`, `results/drive/` (tasks, practice, loops, traction), `results/endcap/` (the first end-cap: study, ceiling, steer), `results/revJ1/{endcap,budgets,revJ1}.json` (Rev J.1's lighter end-cap), `results/revJ/sim_params.json` with the layout (the side load; the page sensor's assumed accuracy), `docs/revJ_simulation.md` §8 and `docs/evidence.csv` OPT-02 (known problems), and `results/sim2j/et.json` when it exists and is complete | a block that cannot be read is left out, with a build warning, and its rows disappear |
| `data/samples.json` | strips: `results/ai2/samples.json` (tremor, trackers, clean copy), `results/nose2/fig_nose2_autowrite_example.csv` (autowrite), `results/drive/tasks.json` `paths_first_case` (lead-through), `results/sim2j/samples.json` when it exists | panels from a missing source are left out |
| `data/replay.json` | `results/sim2j/viz_sim2j.json` when it exists (scenes a and b then replay the whole-pen simulation) | not written; scenes a and b replay the ai2 strips |
| `data/manifest.json` | written by `build.py`: source, status and date of each file | |

`build.py` deletes the Rev H page files that Rev J no longer uses (`board.json`, `tip.json`, `outcomes.json`), and
deletes `replay.json` when there is no whole-pen replay.

### The whole-pen simulation (sim2j)

When `results/sim2j/` has results, a rebuild adds them automatically:

- `et.json` gives a results-table row and a "How much better?" row ("The whole pen together").
- `samples.json` (handwriting samples schema) gives strips and the picture pair of that row.
- `viz_sim2j.json` gives the replay for scenes a and b.

Until then, Details → "Where the numbers come from" lists it as pending. A partial `et.json` (a non-empty
`unfinished` list, or `quick: true`) is not shown: the study is still running and its intermediate numbers are not
quoted. On 29 September 2026 at 17:23 UTC `et.json` listed writers 4 and 5 as unfinished, so the page shows no
whole-pen results yet; the build prints a warning and the pending line says why. The study's report
(`docs/revJ_simulation.md`) is revised while it runs: the known-problems numbers read from it (§8.1, §8.2) follow it on
each rebuild.

## What could not be shown, and why

- **Tracing:** the drive study saved no writing paths, so its row shows what the reading program read for one writer.
- **Parkinson's loops:** only numbers were saved, so the loops are an ILLUSTRATION. It is drawn from the tallest and
  the last loop of each case, and the page says so.
- **End-cap study** (the first design and Rev J.1's lighter end-cap): numbers only, so its row has no picture.
- **Side-load figure:** panel 1 is magnified and schematic (the forces are to one scale, the pen tip is not); panel 2
  is to scale. It shows the static load at 50° only; the 35° and 75° values are in the text.
- **Whole-pen simulation:** not shown while `results/sim2j/et.json` is partial (see above).
- **Autowrite:** the target letters are not stored at full resolution, so the strips show ink and the hand's path.
- **Cut-away:** the "Hand shake" drawing is idealised (the ball stays exactly on the line); the page gives the
  simulated effect beside it.

## Test

```sh
# 1. a test copy with local three.js (the sandbox has no CDN access)
node viewer/explainer/smoke_test.js --prepare DIR --three /path/to/three.min.js --orbit /path/to/OrbitControls.js
# 2. serve it
cd DIR && python3 -m http.server 8791 --bind 127.0.0.1
# 3. run the checks (Playwright installed globally)
NODE_PATH=$(npm root -g) node viewer/explainer/smoke_test.js --url http://127.0.0.1:8791/index.html --shots DIR/shots
```

The test runs at both sizes and exits with code 1 if a check fails. It checks:

- no page or console errors, and no horizontal scroll;
- the three mechanism sentences and their labels;
- no micrometre numbers above Details, except the page-sensor line of Known problems;
- the cut-away:
  - the handle moves while the ball stays within 0.05 mm, the inner pen turns, the tail weight moves the other way;
  - the autowrite data and the wheel steering;
  - labels, arrows, the view from above, play, pause and the scrubber;
- the 3-D colours, legend, picking, pins, hand shake, take apart, X-ray, end-cap, tip pad and cameras;
- one number and one label per "How much better?" row, with picture pairs where the data exist, and the tracing row
  showing the fall in letters read;
- "How sure are we?";
- "Known problems (being fixed)": in the simple view, right after "How sure are we?", four lines with their labels and
  numbers (1.6 W at 50°, 4.7 W at 35°, about 7 times; 0.4 mm; 3 µm against 24–68 µm; made-up data); the side-load
  figure's arrows (spring, paper, sideways part, magnets), the two arms, the lever equation and every label inside
  the drawing, at least 300 px wide;
- every battery-hours and temperature figure outside that panel sits in a block marked "suspended (see known
  problems)" that links to it;
- the tail weight: Rev J.1 in the mechanism sentence, the "How much better?" row and the 3-D tail pin; the first
  design's 8–20 % only in Details (results table: Rev J.1 and the first design, marked superseded);
- every Details block closed at first, then opened:
  - the physics chart, the component table and the corrected limits text;
  - the results table (tracing with the fall in letters read) and the strips at ×1 and ×3;
  - the six scenes, built on opening.

With software WebGL on a busy machine a run takes several minutes.

## Page contract

- Title "How the Pen Works".
- Colour tokens on `:root`, redefined for dark mode under `@media (prefers-color-scheme: dark)` (guarded by
  `:root:not([data-theme="light"])`) and under `:root[data-theme="dark"]`. The body background comes from a token.
- Scripts only from cdnjs (three.js r128) and `cdn.jsdelivr.net/npm` (OrbitControls). Fonts only from Google Fonts.
  Everything else is inline.
- Works at 390 px with 16 px gutters and no horizontal page scroll. Wide strips and charts scroll inside their own
  box.
- Respects `prefers-reduced-motion`: the cut-away starts paused on a telling frame (the scrubber steps through it),
  scenes do not autoplay, and smooth scrolling is off.
- The part-group palette was checked with the dataviz palette validator (light and dark). Every colour also has a
  text label.
