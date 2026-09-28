# Environment

All results in `results/` were produced on Linux x86_64 (Ubuntu 24.04 container) with the versions below. Every result JSON records its own git revision, parameter-file version and digest, seeds, command and library versions (`stabpen/provenance.py`).

| Tool | Version | Used for | Install |
|---|---|---|---|
| Python | 3.11.15 | everything in `stabpen/`, `sim/`, `analysis/`, `mechanics/`, `ml/`, `app/`, `aiguide/`, `s2r/`, `fusion/`, `opt/`, `viewer/` | `python3.11 -m pip install -r requirements.txt` |
| KiCad | 8.0.9 (symbol/footprint libraries 20231120) | schematic generation, ERC, netlist, BOM and PDF export (`electronics/`) | KiCad 8 PPA (`ppa:kicad/kicad-8.0-releases`) |
| ngspice | 42 | drive-stage transient (`electronics/spice/`) | `apt install ngspice` |
| GCC | 13.3.0 | host firmware tests (`firmware/`) | `apt install build-essential` |
| arm-none-eabi-gcc | 13.2.1 (13.2.rel1) | Cortex-M33 build and size report (`firmware/`, `ml/export/`) | `apt install gcc-arm-none-eabi` |
| QEMU | 8.2.2 | running firmware unit tests on an emulated Cortex-M33 (mps2-an505); not cycle-accurate | `apt install qemu-system-arm` |

**Unavailable here**, and so not produced:

- PCB layout and fabrication outputs (blocked by the packaging decision DEC-014).
- FEM magnetics beyond magpylib's analytic magnet models.
- Any hardware or human measurement.

**Quick checks**:

```bash
python3 -m pytest sim/tests -q                       # simulator verification (12 tests)
bash sim/run_all.sh                                  # full simulation evidence chain (10-25 min on 4 cores)
python3 electronics/gen/design_revA.py && (cd electronics/kicad && kicad-cli sch erc pen_research.kicad_sch)
```
