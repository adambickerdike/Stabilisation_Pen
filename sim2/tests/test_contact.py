"""Contact law: compiled kernel against the Python reference, ring geometry, LuGre and native closed forms (fast)."""
import math

import mujoco
import numpy as np

import sim2  # noqa: F401
from sim2 import builder as B
from sim2 import contact as CT
from sim2 import params as P
from sim2 import verify as V


def test_ring_point_is_h1_skid_point_at_nominal_pose():
    pm = B.build(P.Config())
    B.reset(pm)
    mujoco.mj_forward(pm.m, pm.d)
    law = CT.ContactLaw(pm)
    p = law._ring_point()
    s = pm.d.site_xpos[pm.ids["site:skid_pt"]]
    assert np.linalg.norm(p - s) < 1e-7
    law.forces(1.0)
    assert np.linalg.norm(law.kout[0, 3:6] - s) < 1e-7


def test_kernel_matches_python_reference():
    from sim2 import sim as S
    from sim.pensim import scenarios as SCN
    pm = B.build(P.Config())
    st = S.Stepper(pm, SCN.static_hold(duration=0.1))
    st.advance(2000)
    m, d = pm.m, pm.d
    mujoco.mj_forward(m, d)
    law_a = CT.ContactLaw(pm)
    law_b = CT.ContactLaw(pm)
    # same bristle state
    law_a.forces(1.0)
    fa = d.xfrc_applied.copy()
    law_b.forces_py(1.0)
    fb = d.xfrc_applied.copy()
    assert np.allclose(fa, fb, atol=1e-9, rtol=1e-7)


def test_lugre_closed_forms():
    r = V.lugre_tests()
    ps = r["presliding_stiffness_N_per_m"]
    assert abs(ps["measured"] / ps["closed_form"] - 1.0) < 0.02
    assert abs(r["sliding_20mm_s"]["F_N"] - r["sliding_20mm_s"]["mu_k_N"]) < 1e-6
    ss = r["stick_slip"]
    assert abs(ss["F_max_N"] / ss["mu_s_N"] - 1.0) < 0.03


def test_native_contact_closed_forms():
    r = V.native_block_tests()
    k = r["static_stiffness_N_per_m"]
    assert abs(k["measured"] / k["closed_form"] - 1.0) < 0.05
    c = r["creep"]
    assert abs(c["v_creep_m_s"] / c["closed_form_m_s"] - 1.0) < 0.05
    assert abs(r["sliding_mu_elliptic"] - 0.12) < 0.005
