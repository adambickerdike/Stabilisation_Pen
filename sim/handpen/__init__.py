"""Hand-pen-paper rigid-body model with pen rotation (model H1) and the study of inertial,
gyroscopic, grip and paper-pivot stabilisers for the pencil-class pen.

Modules
-------
params     labelled inputs: pen mass properties from the CAD (+10 % wiring), grip zones,
           HAP-26 hand impedance, paper contact, tremor geometry, device envelopes
grip       two-zone grip (finger pads + thumb-index web) calibrated to the tip-referred
           HAP-26 impedance for a chosen split between translational and rotational
           grip compliance (the split is an ASSUMPTION; swept)
linear     small-angle 3-D linear model (pen 5 DOF, hand mass 3 DOF, device DOF) in the
           frequency domain: tremor transmission, device force/torque transfer functions,
           oracle bounds and the size needed for a 50 % reduction
devices    candidate devices (reaction mass, tuned-mass damper, heavier cap, gyroscope,
           control-moment gyroscope, reaction wheels, grip sleeve, passive grip, paper
           pivot): sizing, power, mass and hand calculations with evidence labels
core       compiled (numba) time-domain integrator: rigid pen with rotation, hand mass,
           two grip zones, skid and nib LuGre contacts, reaction mass with stroke stops,
           scissored-pair CMG with gimbal limits, gyroscopic coupling, kinematic nib stage
model      scenario -> parameters -> run -> named channels; oracle feed-forward by
           iterative learning on the true disturbance
evaluate   ink-error metrics (same definitions as sim/pencil/evaluate.py)
run_study  the study behind results/pencil/inertial.json and inertial_viz.json

Every output is a CALCULATION or a SIMULATION on synthetic signals; nothing here is a
measurement of hardware or people.
"""
import os as _os

# Keep this package's numba cache out of sim/pensim/ (other agents run that simulator).
_os.environ.setdefault("NUMBA_CACHE_DIR", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "build", "numba_cache"))
