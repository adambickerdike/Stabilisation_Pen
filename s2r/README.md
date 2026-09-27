# s2r: sim-to-real methodology (built and demonstrated in simulation)

**Evidence status: SIMULATION and CALCULATION only.** The "bench" here is virtual: M1 (`sim/pensim`) or small standalone models with hidden true parameters, seen through measurement models of the instruments named in `validation/bench_protocols.md`. Twin experiments show that the identification and calibration method works on data whose structure we control. They do not show that M1 is right about the real pen; only the bench can. Nothing here is a measurement.

Report: [`docs/sim_to_real.md`](../docs/sim_to_real.md). Procedure for the bench: [`validation/sim_to_real.md`](../validation/sim_to_real.md).

## Modules

| Module | Role |
|---|---|
| `instruments.py` | Measurement models (noise, bandwidth, mounted resonance, sampling, latency, jitter, quantisation, session gain/offset/non-linearity, cross-clock sync). Every number is labelled PROTOCOL, CONFIG, DESIGN or ASSUMPTION (`provenance_table()`). |
| `truth.py` | Hidden plants: draws inside the declared ranges of `config/parameters.yaml` or partly outside them; groups by the experiment that measures them; SHA-256 commitment. |
| `twin.py` | Plant/controller separation around M1 (the firmware keeps its nominal constants while the plant changes), and the C2 outcome evaluation (oracle and Kalman ratios, distortion, neutral ink error, static hold power, device distortion). |
| `fastharness.py` | Drop-in for `sim.pensim.harness.eval_case/run_cases` with a memory-mapped scenario cache and a persistent 2-process pool (identical outputs, tested). |
| `exp_b03.py` | EXP-B03 coupon: R20 (4-wire), voltage-step L (scope), blocked force K_f (F/T), back-EMF K_f (LDV), thermal step R_th, C_th. |
| `exp_b05.py` | EXP-B05 on M1 itself as a test build (clamped pen, Hall frozen, current injection): IV-FRF (m_eq, k_tip, ζ), pen-log FRF (loop and Hall delay), static tip stiffness, axial path. |
| `exp_b01b02.py` | EXP-B01/B02 tribometer with M1's contact and LuGre equations (numba): indentation, sliding, velocity steps, sweeps, reciprocation; Stribeck, pre-sliding and paper-stiffness identification; Maxwell-slip friction-memory truth for C3. |
| `pipeline.py` | The calibration pipeline in protocol order (B03 → B05 → B01/B02) and scoring against the revealed truth. |
| `ident.py` | Least squares with Laplace covariance, bootstrap, H1 and instrumental-variable FRF, second-order-plus-delay fit, Ljung-Box, input cross-correlation, band misfit, drift test, GUM combination. |
| `stage_model.py`, `modelform.py` | C3 structural truths (flexure mode, extra delay and jitter, pivot Coulomb friction, backlash) and the residual diagnostics. |
| `piezo.py` | Pencil piezo stage: Bouc-Wen truth, Prandtl-Ishlinskii identification and analytic inverse, feedforward and feedback tracking. |
| `io.py` | Bench-file layout `s2r-bench-1` (manifest + per-record arrays + JSON sidecars), read by the pipeline. |

## Run

```bash
python3 -m pytest s2r/tests -q                 # 22 tests, about 25 s with a warm numba cache (first run compiles into s2r/build/)
bash s2r/run_all.sh                            # full chain, about 30 min on 2 processes; logs in results/s2r/logs/
```

| Script | Output (`results/s2r/`) | Runtime (2 processes, shared machine) |
|---|---|---|
| `python3 -m s2r.run_c1_identify` | `c1_identification.json`, `fig_c1_recovery.png` | about 2-3 min |
| `python3 -m s2r.run_c1_benchtime --only B05`, `--only B01B02`, `--only B03` (merged into one file; `--replot` redraws the figure) | `c1_bench_time.json`, `fig_c1_bench_time.png` | about 10 min in all: B05 1 min, B01/B02 8 min, B03 1 min. The first run (one call) took 36 min: BLAS thread pools oversubscribed the shared cores. `s2r/__init__.py` now pins one thread per process |
| `python3 -m s2r.run_c2_twin --part 1`, `--part 2`, `--merge` | `c2_twin.json`, `fig_c2_gap.png` | about 4 min per part |
| `python3 -m s2r.run_c2_sensitivity` | `c2_sensitivity.json`, `fig_c2_sensitivity.png` | about 3 min |
| `python3 -m s2r.run_c3_modelform` | `c3_modelform.json`, `fig_c3_model_form.png` | about 2-3 min |
| `python3 -m s2r.run_c3_piezo` | `c3_piezo.json`, `fig_c3_piezo.png` | under 1 min |
| `python3 -m s2r.run_c4_domain` | `c4_domain.json`, `fig_c4_domain.png` | about 4-5 min |
| `python3 -m s2r.run_c5_example` | `c5_example.json`, `virtual_bench_example/` (2.9 MB) | under 1 min |

Every script accepts `--quick` for a smoke run. Every JSON carries `stabpen.provenance.metadata()` (git revision, parameter version and digest, seeds, command).

## Rules this package keeps

- It never writes under `sim/`, `stabpen/`, `config/`, `firmware/`, `ml/` or `app/`. The numba cache goes to `s2r/build/numba_cache` (set in `s2r/__init__.py`); scenario caches to `s2r/build/scn_cache` (both git-ignored via `build/`).
- At most 2 worker processes, one BLAS/OpenMP/numba thread each (set in `s2r/__init__.py`).
- Identification code receives datasets only; hidden truths and session errors live under `_hidden` keys that `io.save` never writes.
