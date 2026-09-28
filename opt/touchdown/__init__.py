"""Touchdown and lift of the pencil: stage feed-forward of the refill slide, tilt-adaptive stop margin and the
inner piezo servo, tuned on the pencil model P1 (Bayesian optimisation, adjoint gradients of a reduced model).

  law        the feed-forward law, its parameters and kinematics (CALC)
  metrics    extra / missing ink against a rigid pen, transition / in-stroke split (SIM post-processing)
  runs       P1 runs on training or test seeds (harness conventions of sim/pencil/run_study.py)
  bo         Gaussian-process Bayesian optimisation and CMA-ES (numpy)
  reduced    differentiable reduced touchdown model (torch) and its adjoint-gradient law fit
  servo      loop margins and the servo study
  run_study  python3 -m opt.touchdown.run_study

Evidence status: CALCULATION and SIMULATION only.  Nothing here is a measurement of hardware or people.
"""
