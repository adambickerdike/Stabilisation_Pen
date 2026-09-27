"""penapp: reference companion application for the research pen (Rev A).

Faithful stroke capture (ICD v1.0 section 4 binary log), an immutable,
content-addressed original stroke layer with derived layers carrying
provenance, SVG rendering, a recogniser interface, full-text search linked
back to stroke ids, and a source-grounded note assistant.

Evidence status: every dataset this package ships or generates is SYNTHETIC
(glyph-based handwriting or coupled-simulator traces).  Nothing here is a
recording of a person or a bench measurement.

Modules
-------
logfmt      ICD section 4 reader/writer (CRC-16/CCITT-FALSE, resync, time unwrap)
notes       note store: immutable original layer + derived layers + schema validation
capture     segmentation, resampling, capture-fidelity analysis
render      SVG rendering (force-to-width, overlays)
recognize   recogniser interface, null / ground-truth / error-injection, ML Kit adapter spec
search      SQLite FTS5 index, hits linked to stroke ids and page bounding boxes
grounded    source-grounded assistant with cited sentences stored as ai_summary layers
synth       synthetic sessions (glyph polylines timed with stabpen.signals; simulator traces)
cli         ``python -m penapp import|render|search|ask|fidelity``
"""
from __future__ import annotations

__version__ = "0.1.0"
ICD_VERSION = "1.0"
SYNTHETIC_LABEL = "SYNTHETIC DATA - not a recording of a person, not a measurement"

__all__ = ["__version__", "ICD_VERSION", "SYNTHETIC_LABEL"]
