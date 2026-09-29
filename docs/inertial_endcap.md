# Rev J study K: the inertial end-cap (what weight, spin and "pull" at the back of the pen can do)

**Status: calculation and simulation only, 2026-09-28.** Nothing here was built or measured on a pen or a person. Labels:
- **SIM**: an executed simulation (model H1, `sim/handpen`, read-only, extended in `endcap/sim.py`; synthetic writing and tremor);
- **CALC**: a calculation (closed-form laws in `endcap/scaling.py`, the linear hand-pen model in `endcap/linear_torch.py`, design models in `endcap/design.py`);
- **LIT (id)**: published literature, with its ledger id (proposed rows in `results/endcap/evidence_rows.csv`, or `docs/evidence.csv`);
- **MFR (id)**: a manufacturer statement, with its ledger id;
- **ASSUMPTION**: an input nobody has measured (listed in `endcap/params.py`, `LABELS`).

Numbers come from `results/endcap/endcap_study.json` (with its `stabpen.provenance` block) unless a ledger id is given.

<!-- RESULTS-DEPENDENT SECTIONS ARE FILLED BELOW -->
