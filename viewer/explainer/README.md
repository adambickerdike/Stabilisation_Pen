# How the Pen Works: the Rev H explainer page

An interactive page for people with essential tremor, Parkinson's, poor handwriting or dyslexia, and for the people
who help them. It shows how the Rev H pen is built and held, how it changes the ink, how much better the writing gets
in simulation, and which problem each function helps. Every number carries an evidence tag (SIMULATION, CALCULATION,
LITERATURE + ledger id, ASSUMPTION, PROPOSED DESIGN, or ILLUSTRATION for drawn scenes). Nothing on the page has been
measured on a real pen or person.

## Files

| File | What it is |
|---|---|
| `template.html` | The page source: HTML, CSS and JS in one file. Edit this, not `index.html`. |
| `build.py` | Copies or builds `data/*.json` from `results/`, fills the `<!--BUILD:...-->` placeholders, writes `index.html`. |
| `index.html` | Generated page (about 190 kB). It loads `data/*.json` with relative `fetch()` calls. |
| `data/*.json` | Generated data (about 1.3 MB). See below. |
| `smoke_test.js` | Playwright check at 1360 × 900 and 390 × 844, with screenshots of every section and scene. |

## Rebuild

```sh
python3 viewer/explainer/build.py
```

Run it whenever a results file changes. It prints which source each data file came from (final or provisional)
and any warning. The page shows the same list under "Where the data comes from".

## Data files and fallbacks

| Page file | Final source | Fallback |
|---|---|---|
| `data/layout.json` | `results/revH/layout.json` | `results/revH/layout_provisional.json` |
| `data/board.json` | `results/board/layout.json` (+ plain-language numbers and the scene-(e) physics from `results/board/board_params.json` and `results/board/board.json`) | a provisional board defined in `build.py` (every size an ASSUMPTION) |
| `data/samples.json` | `results/handwriting/samples.json`, plus the clean copy and AI-guidance runs of `results/aiprior/samples.json` added to the matching tremor panels (same writer, sentence and tremor) | panels from `results/fusion/viz_fusion.json` and `results/ai/viz_guided.json` (earlier pencil design, labelled) + a drawn illustration of shrinking letters |
| `data/replay.json` | `results/opt/viz_inertial_opt_1mm.json` + `viz_inertial_opt.json` (+ band averages from `results/opt/inertial_opt.json`) | none: scenes (a) and (b) then use the tremor panels of `samples.json`, else an illustration |
| `data/outcomes.json` | `results/handwriting/outcomes.json` (slimmed: tremor bands, Parkinson's and practice averages) | none: the page shows the tip-study numbers instead |
| `data/tip.json` | `results/revH/tip_params.json` | `results/revH/tip_params_provisional.json` |
| `data/manifest.json` | written by `build.py`: source, status and date of each file | |

A final file wins as soon as it exists. When the handwriting study lacks a condition, the provisional panels for
that condition stay on the page, clearly labelled.

### Schemas the build accepts

- **Handwriting samples.** The study's per-run schema (`panels[{id, title, condition, device, caption, evidence,
  intended [[x, y, pen_down]], ink [[...]], metrics}]`) is grouped into one panel per condition and scenario, with
  one variant per device and plain-language metrics for tremor, Parkinson's-like writing, guided practice and
  spelling. A generic schema (panels with `variants`, or `before`/`after` keys; strokes as point lists, `{x, y}`
  arrays or points with `null` separators) is also read.
- **Board layout.** Both the provisional schema (centres in the page frame, `moves`) and the board study's schema
  (boxes by corner and size, `moves_with: carriage`) are drawn.
- **Pen layout.** `components[{id, group, shape (cylinder, cone, tube, box), z0, z1, d0, d1, d_in, size, offset,
  moves_with, optional}]`. The layout frame has x in the tilt plane (away from the paper) and y lateral; the page
  maps it to its own pen frame.

## What each section uses

- **Pen in 3-D:** `layout.json` (optional parts drawn see-through: vibration motor, paper sensor, inertial module
  "in the first prototype", board magnet and keel).
- **How it works:** scenes (a) and (b) replay `replay.json` (the handle's tip, pen axis, nose and rear-module slug);
  (c) and (d) are illustrations; (e) is an illustration sized like the board study's tracing run, with the pull on the
  sleeve magnet capped at 0.4 N.
- **How much better:** `outcomes.json` for the averages, `samples.json` for the strips at real size.
- **What's inside:** `layout.json` (table built at build time) and the technology table.

## Test

```sh
# 1. a test copy with local three.js (the sandbox has no CDN access)
node viewer/explainer/smoke_test.js --prepare DIR --three /path/to/three.min.js --orbit /path/to/OrbitControls.js
# 2. serve it
cd DIR && python3 -m http.server 8791 --bind 127.0.0.1
# 3. run the checks (Playwright installed globally)
NODE_PATH=$(npm root -g) node viewer/explainer/smoke_test.js --url http://127.0.0.1:8791/index.html --shots DIR/shots
```

The test checks: data loaded, no page or console errors, no horizontal scroll, the legend and part picking, "Take
apart", the tip pad, all five scenes drawing ink, the replay and rear-module cases, the board scene (magnet on the
handle, the board's head under it, pull within the limit, ink closer to the letter than the sleeve), the toggles, and
the handwriting strips at real size and ×3. It exits with code 1 if a check fails.

## Page contract

- Title "How the Pen Works"; colour tokens on `:root`, redefined for dark mode under
  `@media (prefers-color-scheme: dark)` (guarded by `:root:not([data-theme="light"])`) and under
  `:root[data-theme="dark"]`.
- three.js r128 from cdnjs and OrbitControls from `cdn.jsdelivr.net/npm/three@0.128.0/...`; fonts from Google Fonts
  only; everything else inline.
- Works at 390 px with 16 px gutters and no horizontal page scroll; wide strips scroll inside their own box.
- The part-group palette was checked with the dataviz palette validator (light and dark). Two adjacent pairs are
  close for some colour-vision types, so every group also has a text label and a legend entry.
