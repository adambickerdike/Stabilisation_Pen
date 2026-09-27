#!/usr/bin/env python3
"""C5 support: an example bench-file set in the format the pipeline reads (s2r/io.py).

One hidden plant is measured on the virtual bench (EXP-B03 at protocol settings, EXP-B05 with
2 chirps x 3 s to keep the files small), the datasets are written in the s2r-bench-1 layout
under results/s2r/virtual_bench_example/, read back, and identified from the files. The
estimates from the files must equal the in-memory estimates (checked here and in
s2r/tests/test_io.py). EXP-B01/B02 files use the same layout; they are not written here
because a full grid is about 40 MB (the unit test round-trips a reduced set).

Evidence status: SIMULATION (virtual bench data), CALCULATION (identification).
Run: python3 -m s2r.run_c5_example     (about 20 s)
"""
from __future__ import annotations

import os
import shutil

import numpy as np

import s2r  # noqa: F401
from s2r import common, exp_b03, exp_b05, io, twin
from s2r import truth as tr


def main():
    rng = np.random.default_rng(2027)
    t = tr.draw(np.random.default_rng(11), "inside")
    full = twin.nominal_plant()
    full.update(t["values"])
    root = os.path.join(s2r.RESULTS, "virtual_bench_example")
    shutil.rmtree(root, ignore_errors=True)
    ds3 = exp_b03.generate(full, rng)
    e3 = exp_b03.identify(ds3, np.random.default_rng(1))["estimates"]
    ds5 = exp_b05.generate(full, rng, n_chirps=2, T_c=3.0)
    kf = e3["actuator.Kf"]
    e5 = exp_b05.identify(ds5, kf["value"], kf["u"], L_hat=e3["actuator.L"]["value"],
                          R20_hat=e3["actuator.R20"]["value"])["estimates"]
    io.save(ds3, os.path.join(root, "EXP-B03"), "EXP-B03", meta={"coupon": "virtual", "settings": "protocol"})
    io.save(ds5, os.path.join(root, "EXP-B05"), "EXP-B05", meta={"pen": "virtual", "settings": "2 chirps x 3 s"})
    f3 = exp_b03.identify(io.load(os.path.join(root, "EXP-B03")), np.random.default_rng(1))["estimates"]
    f5 = exp_b05.identify(io.load(os.path.join(root, "EXP-B05")), kf["value"], kf["u"],
                          L_hat=e3["actuator.L"]["value"], R20_hat=e3["actuator.R20"]["value"])["estimates"]
    same = {k: bool(np.isclose(e3[k]["value"], f3[k]["value"], rtol=1e-9)) for k in e3}
    same.update({k: bool(np.isclose(e5[k]["value"], f5[k]["value"], rtol=1e-9)) for k in e5})
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(root) for f in fs)
    common.write_result("c5_example", {"directory": os.path.relpath(root, s2r.ROOT), "bytes": size,
                                       "roundtrip_identical": same, "estimates_from_files": {**f3, **f5}},
                        "SIMULATION (virtual bench files) + CALCULATION")
    print("round trip identical:", all(same.values()), f"{size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
