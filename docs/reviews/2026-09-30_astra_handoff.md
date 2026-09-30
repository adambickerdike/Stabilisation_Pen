# Astra engineering pass: cloud handoff

This commit publishes the engineering work based directly on `4ad62b6acdcda1fa1102362f32780168297f5bb3` on `claude/pensive-shannon-wzm6ls`. Source changes, proposed STEP assemblies, corrected and failed studies, six RL checkpoints, exact-source snapshots and test logs are included. No new physical or participant measurements were obtained.

The report's references to an uncommitted local clone and no push describe its original delivery snapshot. This publication supplies that work in Git. The original PDF is unchanged; the copied Markdown has only its figure paths adjusted for this directory.

- [21-page PDF report](Stabilisation_Pen_Engineering_Improvement_Report.pdf)
- [Report readable on GitHub](Stabilisation_Pen_Engineering_Improvement_Report.md)
- [Mechanical equations, candidate assumptions and reproduction commands](../mechanics_improvement_audit.md)
- [Control and both RL experiments](../control_improvement_audit.md)
- [Accepted writing, observer and numerical correction](../writing_improvement_audit.md)
- [Integration and portability audit](../integration_improvement_audit.md)
- [Additional primary-source research](../research_addendum_2026_09_30.md)

## Reproduce the verification

The delivery runs used Python 3.12.14 on macOS arm64 with the pinned `requirements.txt`; the original upstream studies used a different runtime. Use a full clone containing the historical commits: H1/P1 regressions export their original source and compare it with current source on the same host. They preserve the original Linux fixtures rather than replacing them with Mac output.

```sh
python -m pip install -r requirements.txt
export MPLCONFIGDIR=build/improvement_mpl
export NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONNOUSERSITE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q -ra
python -m pytest -q -ra --runslow sim2/tests/test_slow.py
python validation/check_criteria.py --check
```

Recorded results: 871 default-suite passes with 20 skips, followed by four passing optional slow tests, for **875 distinct passes and 16 unavailable-artifact checks**. The missing licensed data, tremor libraries, models and generated artifacts are not silently supplied or counted as passes. Logs and JUnit reports are in [`results/improvement/verification/`](../../results/improvement/verification/); the host C suite separately passed 60 cases and 1,120 checks. Only publication documentation and report copies were changed for this handoff; the numerical implementation is the verified delivery version.

## Locate the friction correction

The specific energy-creation defect was in the **new generic accepted-writing replay**, with a 0.5 ms explicit update of the assumed 20 mN smoothed friction on a 3.44 g mass. Its repair is [`ai3/planar_integrator.py`](../../ai3/planar_integrator.py); the independent isolated diagnostic is [`validation/friction_step_check.py`](../../validation/friction_step_check.py).

The authoritative [numerical-status note](../../results/improvement/writing/NUMERICAL_STATUS.md) identifies the invalid studies and preserved originals. Use `numerical_correction_50us/`, `numerical_correction_25us/` and `numerical_convergence.json` for the corrected same-case evidence. Reference-only certificates do not use that integrator. The separate grounded model has its own friction and derivative checks. This finding by itself does not establish that the old whole-pen, balanced-nib, Rev K servo or readable-target integrators share the same defect; their dependency and numerical checks remain separate. Other causal-sensing and controller corrections in this pass also need consideration when reproducing upstream studies.

## Compare the actuator and motion results consistently

The 20 mm candidate actually resizes its magnets and winding; it is not the original Rev K coil inside a smaller barrel. Its reported 0.139 W is a worst sampled periodic-duty value at the declared 20 mN residual-load condition, with motion, support forces, spatial force variation and field derating. Compare matched geometry, displacement, load waveform, force-map location and derating before interpreting the difference as magnet strength alone. Detailed inputs and recovered B1 calibration are in the mechanics audit, `bnib/data/`, and `results/improvement/mechanics/`.

The grounded 20/20 result passes its ink/tracking criterion only: none of those traces also passes the selected actual acceleration/jerk comparisons, and either tested resisting grip defeats completion. Similarly, the corrected generic observer completes 11/48 admitted mixed cases by the position criterion but none with the rate comparisons also satisfied. Preserve these qualifications when folding the findings into the next design and claims register.
