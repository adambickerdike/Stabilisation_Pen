"""Simulator v2 (study V, Rev J): a MuJoCo hand-pen-paper simulator generated from Python (MJCF).

What it models (every output is a SIMULATION or a CALCULATION on synthetic writing and tremor; nothing here is a
measurement of hardware or people):

  pen        the Rev H handle (results/revH/layout.json; mass properties from opt/inertial/revh.py) with the fixed
             sleeve and the C-shaped skid ring (contact radius 6.75 mm, DEC-034), the nose on a 2-axis flexure
             gimbal (hinges with bending stiffness), flat voice coils (current, force limit, copper loss, coil
             temperature), the refill on a slide joint with a constant-force spring and a tilt-adaptive front stop;
  plug-ins   parametric devices with one interface (plugins.py): heel drive (driven ball, steered or braked wheel),
             rear end-cap rotor / control-moment gyroscope (spinning body on gimbal joints: gyroscopic effects are
             native), reaction mass, multi-plane nose;
  hand       'h1': H1's hand (HAP-26 hand mass on the arm spring to an imposed path; two-zone grip calibrated to the
             tip-referred HAP-26 impedance with the split r_rot) realised as grip joints at the elastic centre;
             'arm': a forearm-wrist-hand chain (base, pronation-supination, wrist flexion-extension and deviation,
             finger stage) with joint impedance, an inverse-dynamics writer controller tracking the intended path,
             and tremor torques at the wrist and forearm;
  tremor     tremor.py: narrow-band torque (or displacement) generators with frequency and amplitude wander,
             harmonics; ET, PD (rest, re-emergent) and physiological profiles;
  paper      the H1 contact law by default (compliant penalty normal force and LuGre friction at the skid ring's
             lowest point and the ball, numba kernel), or MuJoCo's soft contacts with Coulomb friction (elliptic
             cones) for coarse RL runs and geometry-rich plug-ins;
  sensors    IMU (LSM6DSV16X class through fusion's reading models), nose Hall position, page sensor (optical flow,
             1 kHz, 2 ms), writing force, refill slide;
  checks     verify.py (contact closed forms, convergence, energy, gyroscope, sensors), h1compare.py (against H1),
             validate.py (literature), myo.py (MyoSuite MyoArm impedance);
  interfaces a Gymnasium environment (env.py) with domain randomisation; run_study.py (--quick); report in
             docs/sim_v2.md and results/sim2/.

Evidence labels used throughout: SIM, CALC, LIT (ledger id), MFR (ledger id), ASSUMPTION, PROPOSED DESIGN.
"""
import os as _os

_PKG = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.dirname(_PKG)
# keep numba caches of the read-only packages this one imports (fusion, sim.handpen) inside sim2/build (gitignored)
_os.environ.setdefault("NUMBA_CACHE_DIR", _os.path.join(_PKG, "build", "numba_cache"))
# one core per process (four cores are shared by five studies): single-threaded BLAS.  Multi-threaded OpenBLAS on an
# oversubscribed machine spins its worker threads and slows small dense solves by orders of magnitude.
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    _os.environ.setdefault(_k, "1")

import sys as _sys

if ROOT not in _sys.path:
    _sys.path.insert(0, ROOT)

VERSION = "sim2-0.1"
