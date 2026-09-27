"""Bench-file format read by the identification pipeline (protocol §0.4: HDF5 preferred, or
CSV with a JSON sidecar).

One directory per experiment and session:

  <dir>/manifest.json           experiment id, format version, evidence status, top-level
                                scalars and the list of record groups
  <dir>/<group>/<nnnn>_<k>.<ext> one array file per record and sample-rate group k:
                                .csv (header "name[unit]") or .npz (compressed, same names);
                                an HDF5 file with one group per record and the same dataset
                                names maps one to one (h5py is not in requirements.txt)
  <dir>/<group>/<nnnn>.json     sidecar: scalar attributes of the record (set points, angles,
                                sample rates), units and the array files it owns

The virtual bench writes this; the rig export should too. Real files carry
evidence_status "measured"; virtual ones "SIMULATION (virtual bench)".
"""
from __future__ import annotations

import json
import os
from typing import Dict

import numpy as np

FORMAT_VERSION = "s2r-bench-1"
UNITS = {"t": "s", "t_s": "s", "t_cap": "s", "F_a": "N", "F_t1": "N", "F_t2": "N", "x_enc": "m", "y_enc": "m",
         "x_cap": "m", "z_laser": "m", "i_A": "A", "v_V": "V", "R_ohm": "ohm", "v_emf_V": "V", "vel_m_s": "m/s",
         "v_m_s": "m/s", "ref_A": "A", "iref_A": "A", "q_hall_m": "m", "F_N": "N", "s_m": "m", "q_m": "m",
         "dir": "-", "cycle": "-"}


def _is_array(v):
    return isinstance(v, np.ndarray) and v.ndim == 1 and v.size > 1 and v.dtype.kind in "fiub"


def _jsonable(v):
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def _write_record(rec: Dict, base: str, fmt: str = "npz"):
    arrays = {k: np.asarray(v) for k, v in rec.items() if _is_array(np.asarray(v)) and not isinstance(v, str)}
    attrs = {k: _jsonable(v) for k, v in rec.items() if k not in arrays and not isinstance(v, dict)}
    subs = {k: v for k, v in rec.items() if isinstance(v, dict)}
    groups: Dict[int, list] = {}
    for k, v in arrays.items():
        groups.setdefault(len(v), []).append(k)
    files = []
    for gi, (n, keys) in enumerate(sorted(groups.items())):
        fn = f"{os.path.basename(base)}_{gi}.{fmt}"
        path = os.path.join(os.path.dirname(base), fn)
        if fmt == "csv":
            hdr = ",".join(f"{k}[{UNITS.get(k, '')}]" for k in keys)
            np.savetxt(path, np.column_stack([arrays[k] for k in keys]), delimiter=",", header=hdr, comments="",
                       fmt="%.10g")
        else:
            np.savez_compressed(path, **{k: arrays[k] for k in keys})
        files.append({"file": fn, "columns": keys, "units": [UNITS.get(k, "") for k in keys], "n": n})
    for sk, sv in subs.items():
        files.append({"sub": sk, "files": _write_record(sv, base + "_" + sk, fmt)})
    with open(base + ".json", "w") as f:
        json.dump({"attrs": attrs, "files": files}, f, indent=1)
    return files


def _read_record(base: str) -> Dict:
    with open(base + ".json") as f:
        side = json.load(f)
    rec = dict(side["attrs"])
    d = os.path.dirname(base)
    for entry in side["files"]:
        if "sub" in entry:
            rec[entry["sub"]] = _read_record(base + "_" + entry["sub"])
            continue
        path = os.path.join(d, entry["file"])
        if path.endswith(".csv"):
            a = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
            for j, k in enumerate(entry["columns"]):
                rec[k] = a[:, j]
        else:
            with np.load(path) as z:
                for k in entry["columns"]:
                    rec[k] = z[k]
    return rec


def save(ds: Dict, directory: str, experiment: str, evidence: str = "SIMULATION (virtual bench)", meta=None,
         fmt: str = "npz"):
    """Write a dataset dict (as produced by exp_*.generate) to directory (fmt 'npz' or 'csv')."""
    os.makedirs(directory, exist_ok=True)
    manifest = {"format": FORMAT_VERSION, "experiment": experiment, "evidence_status": evidence,
                "meta": meta or {}, "scalars": {}, "groups": {}}
    for key, val in ds.items():
        if key.startswith("_"):
            continue            # virtual-bench truth and hidden session errors never leave the generator
        if isinstance(val, dict) and "records" in val:
            gdir = os.path.join(directory, key)
            os.makedirs(gdir, exist_ok=True)
            for i, rec in enumerate(val["records"]):
                _write_record(rec, os.path.join(gdir, f"{i:04d}"), fmt)
            manifest["groups"][key] = {"n_records": len(val["records"]),
                                       "attrs": {k: _jsonable(v) for k, v in val.items() if k != "records"}}
        elif isinstance(val, dict):
            gdir = os.path.join(directory, key)
            os.makedirs(gdir, exist_ok=True)
            _write_record(val, os.path.join(gdir, "0000"), fmt)
            manifest["groups"][key] = {"n_records": 1, "single": True}
        elif isinstance(val, list):
            gdir = os.path.join(directory, key)
            os.makedirs(gdir, exist_ok=True)
            for i, rec in enumerate(val):
                _write_record(rec, os.path.join(gdir, f"{i:04d}"), fmt)
            manifest["groups"][key] = {"n_records": len(val), "list": True}
        else:
            manifest["scalars"][key] = _jsonable(val)
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    return directory


def load(directory: str) -> Dict:
    with open(os.path.join(directory, "manifest.json")) as f:
        man = json.load(f)
    ds = dict(man["scalars"])
    for key, g in man["groups"].items():
        gdir = os.path.join(directory, key)
        recs = [_read_record(os.path.join(gdir, f"{i:04d}")) for i in range(g["n_records"])]
        if g.get("single"):
            ds[key] = recs[0]
        elif g.get("list"):
            ds[key] = recs
        else:
            ds[key] = {"records": recs, **g["attrs"]}
    return ds
