"""Study K of Rev J: the inertial, gyroscopic and pseudo-force end-cap at the rear of the pen.

Question: what is the best inertial, gyroscopic or pseudo-force system in a rear end-cap (up to 26 mm across, about
45 mm long, at most 45 g, 1 W peak, 0.3 W average), and what can it honestly do to
  (1) steady the pen against tremor (4-12 Hz),
  (2) steer or shift the pen at writing frequencies (1-5 Hz) by letter-scale amounts,
  (3) guide the hand by feel?

Modules
-------
params        labelled inputs (envelope, materials, catalogue motors, literature data with ledger ids)
scaling       closed-form scaling laws for every device class (reaction mass, tuned mass, reaction wheel, control-moment
              gyroscope in several arrangements, passive gyroscope, propeller, asymmetric-vibration cue, weight shift)
design        parametric end-cap designs inside the envelope: mass, fit, capacity, power, spin-up, stored energy, noise
linear_torch  differentiable (PyTorch) small-angle hand-pen model of the Rev H pen with an end-cap device
optimise      gradient (autograd) and CMA-ES design optimisation of each device class; Pareto fronts
cmaes         a small, tested CMA-ES implementation (no external package)
sim           time-domain runs in model H1 (sim/handpen, read-only) through opt/inertial (read-only): tremor on top of
              the Rev H nose, letter-scale steering, gyroscopic stiffening, the pseudo-force cue's ink side effect
cue           what the literature supports for pseudo-force and torque cues (a perceptual model, not a force)
report        results/endcap/endcap_study.json, figures with CSV twins, headline numbers
evidence      literature and manufacturer rows + result rows in the ledger's 23-column format
layout        the recommended end-cap as parts in the Rev H layout schema (results/endcap/layout_parts.json)
run_study     all stages and the rules fixed before the test runs (python3 -m endcap.run_study [--quick])
Doc: docs/inertial_endcap.md.  CAD: mechanics/cad/endcap.py.

Evidence labels: SIM (executed simulation), CALC (calculation), LIT (ledger id), MFR (ledger id), ASSUMPTION.
Nothing here was built or measured.
"""
