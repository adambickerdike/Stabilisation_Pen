"""Pencil-class pen (Rev P0): shared design model and coupled time-domain simulator.

Modules
-------
design    parameters (config/pencil.yaml over config/parameters.yaml), CAD-derived
          masses, piezo bender and stage reduction, contact loads behind a skid,
          nib-protrusion geometry, decoupling-leaf mechanics
layout    index layout of the packed parameter vector and recorded channels
core      compiled (numba) integrator: hand, housing with skid contact, spring-loaded
          nib with LuGre friction, two-axis piezo stage with driver and hysteresis,
          sensors, estimators (neutral / oracle / Kalman / guided), piezo servo
model     scenario -> parameter vector -> run -> named channels
evaluate  ink-error metrics (same definitions as sim/pensim/evaluate.py)
run_study the study behind results/pencil/sim_metrics.json and viz_trace.json

Every output is a CALCULATION or a SIMULATION on synthetic signals; nothing
here is a measurement of hardware or people.
"""
import os as _os

# Keep every numba cache this package triggers (including M1 runs for the cross-check)
# out of sim/pensim/: other agents run that simulator concurrently.  build/ is git-ignored.
_os.environ.setdefault("NUMBA_CACHE_DIR", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "build", "numba_cache"))
