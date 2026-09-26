"""stabpen: shared models for the active stabilisation pen programme.

Modules
-------
params    versioned parameter file access and Monte Carlo sampling
frames    reference frames, pen orientation, paper-plane Jacobian
contact   quasi-static contact reaction, transverse load, pressure modulation
actuator  motor-constant scaling, lever transmission, coil electrical/thermal
signals   synthetic handwriting and disturbance generators
metrics   path error, band power, feature-preservation metrics
provenance run metadata (git revision, parameter digest, seeds)

Every numerical output of these modules is an analytical calculation or a
simulation.  None is a physical measurement.
"""
__all__ = ["params", "frames", "contact", "actuator", "signals", "metrics", "provenance"]
