"""Magnetics: magpylib force against the analytic dipole, symmetry, monotonic gap law (CALC checks)."""
import math

import numpy as np
import magpylib as magpy

from board import magnetics as M
from board import params as P

MM = 1e-3


def test_getFT_matches_point_dipoles_far_apart():
    # two small cylinders 60 mm apart, laterally offset: dipole formula should agree within 3 %
    J1, J2 = 1.4, 1.3
    d1, h1, d2, h2 = 4.0, 4.0, 3.0, 3.0
    src = magpy.magnet.Cylinder(dimension=(d1 * MM, h1 * MM), polarization=(0, 0, J1), position=(0, 0, 0))
    tgt = magpy.magnet.Cylinder(dimension=(d2 * MM, h2 * MM), polarization=(0, 0, J2), meshing=200,
                                position=(20 * MM, 5 * MM, 60 * MM))
    F, _ = magpy.getFT(src, tgt)
    m1 = J1 * math.pi / 4 * d1 ** 2 * h1 * 1e-9 / P.MU0
    m2 = J2 * math.pi / 4 * d2 ** 2 * h2 * 1e-9 / P.MU0
    Fd = M.dipole_force([0, 0, m1], [0, 0, 0], [0, 0, m2], [20 * MM, 5 * MM, 60 * MM])
    assert np.allclose(F, Fd, rtol=0.03, atol=1e-9)


def test_vertical_pen_magnet_above_axial_head_has_no_lateral_force():
    pen = M.PenMagnet(axis="vertical", height_mm=2.2, mesh=60)
    F = M.force_at_offsets(M.Head(), pen, 3.7, np.zeros((1, 2)))[0]
    assert abs(F[0]) < 1e-3 and abs(F[1]) < 1e-3
    assert F[2] < -0.5          # pulled down toward the head


def test_lateral_capability_falls_with_gap():
    pen = M.PenMagnet(mesh=50)
    offs = M.offset_grid(16.0, 1.0)
    caps = [M.lateral_capability(M.force_at_offsets(M.Head(), pen, g, offs), offs)["lateral_isotropic_N"]
            for g in (2.0, 4.0, 8.0)]
    assert caps[0] > caps[1] > caps[2] > 0


def test_antiphase_coil_pair_gives_no_normal_force_above_midpoint():
    pen = M.PenMagnet(axis="vertical", height_mm=3.0, mesh=40)
    common = dict(r_in_mm=1.0, r_out_mm=4.0, turns_per_layer=4, layers=2, layer_pitch_mm=0.5, z_top_mm=-1.0)
    a = M.Coil(xy_mm=(-5.0, 0.0), sign=+1.0, **common)
    b = M.Coil(xy_mm=(5.0, 0.0), sign=-1.0, **common)
    F = M.coil_force([a, b], pen, np.array([0.0, 0.0, 3.0]), 1.0)
    assert abs(F[2]) < 1e-3 * max(abs(F[0]), 1e-6) + 1e-9
    assert abs(F[0]) > 0
