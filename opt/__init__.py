"""Optimisation studies of the pencil concept (adjoint / gradient-based and ML methods).

  opt.hardware   stage and component selection (reverse-mode automatic differentiation of the
                 design model, plus a global search over catalogue and buildable parts)
  opt.tracker    tremor-tracker tuning by backpropagation through time (the discrete adjoint of
                 the filter recursion) and learned trackers with an intent-aligned loss
  opt.touchdown  cancelling the touchdown and lift tails with a stage feed-forward, tuned by
                 Bayesian optimisation on the pencil model P1

Evidence status of every result: CALCULATION or SIMULATION.  Nothing here is a measurement.
"""
