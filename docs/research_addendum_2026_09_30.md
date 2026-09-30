# Research implications for the improved pen

This targeted engineering review supplements the 25-source review dated 29 September 2026. It is not a systematic review or meta-analysis. Searches on 30 September used the problem terms *time-optimal path parameterization reachability*, *jerk-limited arbitrary target states*, *haptic pen skill training*, and the primary papers already identified for typing, Parkinsonian handwriting and writing mode. Primary papers and official documents were used for technical claims. Retrieval scope is stated below; inaccessible full text is not treated as reviewed.

## Geometry needs a clock and a force budget

The new accepted-stroke implementation preserves a geometric path within a declared error tolerance, constructs smooth pieces, and retimes them until conservative bounds pass. It does not claim globally shortest duration. The separation is deliberate: recognition decides a candidate string, acceptance chooses future text, the glyph planner chooses geometry, and the physical planner decides whether and when the mechanism can draw it.

**Reachability-based timing.** Pham and Pham's TOPPRA work computes reachable/controllable sets along a geometric path through small linear programmes. It is a relevant baseline for reducing conservative traversal time after actuator and contact models are calibrated. Its published success on its numerical tests does not certify this nib, and third-order constraints need separate treatment. The present code uses a conservative polynomial-bound search, not an implementation of TOPPRA. [Pham and Pham, author abstract reviewed](https://arxiv.org/abs/1707.07239)

**Jerk-limited transitions.** Berscheid and Kroeger's Ruckig work constructs synchronized state-to-state trajectories subject to velocity, acceleration and jerk limits. Its distinction between kinematic constraints and full dynamic constraints matters here: a jerk-limited move can still exceed a coil's current/voltage or a handwriting path's error tolerance. Ruckig is a useful comparison for pen-up repositioning and interruption recovery. It is not a substitute for the new radial workspace, force, contact and page-reference checks, and it was not added as an untested dependency. [RSS 2021 paper, full text inspected](https://www.roboticsproceedings.org/rss17/p015.pdf)

The scientific advance needed for free writing is different. If a sensor measures `x(t) = voluntary(t) + tremor(t)`, then `voluntary(t) + d(t)` and `tremor(t) - d(t)` give the same motion for arbitrary `d(t)`. Motion and its derivatives alone do not uniquely establish intent. Additional task constraints, a personalized prior or an explicitly accepted target add information. A larger policy cannot repeal that ambiguity. The implementation therefore keeps bounded free-writing assistance distinct from accepted-path execution.

## Immediate assistance and learning are different outcomes

Shire and colleagues tested a robotic intervention in a counterbalanced crossover study of 51 children aged 5-11 with manual-control difficulties. Improvement on the trained robotic task did not generalise to the study's standardized pen-skill tasks. This is evidence against assuming that better assisted tracing automatically produces lasting handwriting improvement. For this pen, report assisted ink quality and retained unassisted skill separately, using an appropriate target population. [Shire et al., PLOS ONE 2016, full article inspected](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0151354)

Nackaerts and colleagues' randomized study of 38 people with early-to-mid-stage Parkinson's disease found a trade-off: amplitude training improved writing size in their earlier analysis, while this analysis found longer stroke duration and worse normalized jerk. A controller optimized only for bigger letters could therefore miss a material cost. Size, speed, fluency, legibility, effort and preference belong in the same evaluation. This does not establish the effect of the present device. [Nackaerts et al., PLOS ONE 2017, primary article text reviewed](https://pmc.ncbi.nlm.nih.gov/articles/PMC5741263/)

A 2025 haptic-handwriting paper was found in the search but its full text could not be retrieved reliably in this run. It is not used to justify a new benefit claim. None of these sources demonstrates a compact autonomous spelling pen or validates a treatment for dyslexia.

## Typing is a comparator the product should welcome

The strongest answer to “why not type?” is to test the actual task. A person who completes it more comfortably with typing or dictation should have that option. The commercial hypothesis is narrower: some people want or need paper-based signing, drawing, annotations or personal handwriting, and an assistive tool may restore enough control to make those tasks worthwhile. The frequency and willingness to pay for those tasks require user research; no pen-use market statistic is invented here.

Natural typing can itself reflect Parkinsonian motor impairment. The neuroQWERTY study examined motor signatures in keyboard timing during home use; it did not establish that a pen is easier than a keyboard. It therefore supports testing both interfaces, not dismissing typing. [Arroyo-Gallego et al., JMIR 2018, primary article text reviewed](https://pmc.ncbi.nlm.nih.gov/articles/PMC5891671/)

Writing-mode effects in developmental dyslexia are also task-specific. Jung and colleagues found that mode affected some outcomes and spelling rules differently; their German-language assessment does not imply that changing the input device resolves the underlying spelling difficulty. A steadier nib and a language-support interface need separate evaluations. [Jung et al., Dyslexia 2021, abstract reviewed](https://pubmed.ncbi.nlm.nih.gov/33615629/)

A defensible product statement is: “We are developing an option for people who value writing or drawing on paper and have difficulty controlling it. It must demonstrate useful task completion, comfort and user choice against an ordinary pen and available digital alternatives.” This is a proposed positioning statement, not evidence of established demand or efficacy.

## What each new result can establish

| Result | What it establishes | What still needs measurement |
|---|---|---|
| Direct magnetic calculation and wire/guide screen | Internal consistency of a proposed mechanical envelope under specified assumptions | Force map, tolerances, friction, lead heating, fatigue and assembly |
| Discrete controller pole and noise calculation | Stability/noise predictions for the modeled sampled loop | Actual transfer function, delay, quantization, nonlinear contact and flexible modes |
| Fresh synthetic controller comparison | Model performance on separately generated scenarios under a frozen protocol | Transfer to measured writing and an identified physical pen |
| UJI glyph admission replay | Which reused recorded geometries fit the assumed workspace/dynamic bounds | Timestamped motor behaviour, legibility and transfer to patients |
| Accepted-command execution replay | Behaviour of the new planner/supervisor in a specified simulated plant | Actual deposited ink, lift transitions, user override and sensing |
| Unit tests and host C checks | The software properties asserted by those tests | Target execution, electronics integration and device effectiveness |

The next decisive comparison uses a named hardware build and blinded deposited-ink scoring. It should compare an ordinary light pen, the same device with assistance disabled, a mass-matched locked mechanism, the proposed controller, typing with available accessibility settings, and dictation where the task permits. Keep outcome analysis at the participant level; many strokes from one person are not many independent people. Measure useful words per minute, reader legibility, omitted/extra strokes, effort, fatigue, setup time, choice and adverse device behaviour. Predefine what improvement is worth the extra bulk and cost. Estimate sample size from pilot variability and a user-relevant effect rather than choosing an impressive-looking count.

For spelling and next-word suggestions, use participant-disjoint text and report recognition errors separately from language-model edits. Measure false edits, accepted suggestions, time to accept, corrected-text accuracy, name/dialect preservation and semantic changes. Calibrate confidence on a separate validation set and permit abstention. The implemented acceptance/provenance layers make those comparisons possible; they do not by themselves establish language-model accuracy or dyslexia benefit.
