"""Versioned parameter access for all models.

Parameters live in config/parameters.yaml. Each leaf is a mapping with value,
unit, min, max, dist, status, source and note.  This module returns plain
floats (SI units as declared in the file) and can draw Monte Carlo samples
within the declared ranges.  Ranges are exploratory unless their status says
otherwise; they are never tuned to make a controller succeed.
"""
from __future__ import annotations

import copy
import hashlib
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import numpy as np
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(REPO_ROOT, "config", "parameters.yaml")

LEAF_KEYS = {"value", "unit"}


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and LEAF_KEYS.issubset(node.keys())


@dataclass
class Params:
    """Nested parameter store with dotted-key access."""

    tree: Dict[str, Any]
    path: str = DEFAULT_PATH

    # ------------------------------------------------------------------ access
    def leaf(self, key: str) -> Dict[str, Any]:
        node: Any = self.tree
        for part in key.split("."):
            node = node[part]
        if not _is_leaf(node):
            raise KeyError(f"{key} is not a parameter leaf")
        return node

    def __getitem__(self, key: str) -> Any:
        return self.leaf(key)["value"]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def rng_range(self, key: str):
        lf = self.leaf(key)
        return lf.get("min", lf["value"]), lf.get("max", lf["value"])

    def keys(self) -> Iterable[str]:
        def walk(node, prefix):
            for k, v in node.items():
                if k == "meta":
                    continue
                full = f"{prefix}.{k}" if prefix else k
                if _is_leaf(v):
                    yield full
                elif isinstance(v, dict):
                    yield from walk(v, full)
        return list(walk(self.tree, ""))

    # ---------------------------------------------------------------- mutation
    def with_overrides(self, overrides: Optional[Dict[str, Any]] = None) -> "Params":
        new = Params(copy.deepcopy(self.tree), self.path)
        for k, v in (overrides or {}).items():
            new.leaf(k)["value"] = v
        return new

    def sample(self, keys: Iterable[str], rng: np.random.Generator) -> Dict[str, float]:
        """Draw one Monte Carlo sample for the given keys using declared ranges."""
        out = {}
        for k in keys:
            lf = self.leaf(k)
            lo, hi, dist = lf.get("min"), lf.get("max"), lf.get("dist", "fixed")
            v = lf["value"]
            if dist == "fixed" or lo is None or hi is None or lo == hi:
                out[k] = v
            elif dist == "uniform":
                out[k] = float(rng.uniform(lo, hi))
            elif dist == "loguniform":
                if lo <= 0:
                    raise ValueError(f"loguniform needs positive bounds for {k}")
                out[k] = float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
            elif dist == "normal_clip":
                sd = (hi - lo) / 4.0
                out[k] = float(np.clip(rng.normal(v, sd), lo, hi))
            else:
                raise ValueError(f"unknown dist {dist} for {k}")
        return out

    # ------------------------------------------------------------ provenance
    def version(self) -> str:
        return str(self.tree.get("meta", {}).get("version", "unknown"))

    def digest(self) -> str:
        with open(self.path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]


def _coerce(node):
    """Convert numeric-looking strings (e.g. YAML 1.1 '5.0e4') to float."""
    if isinstance(node, dict):
        return {k: _coerce(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_coerce(v) for v in node]
    if isinstance(node, str):
        try:
            return float(node) if any(c.isdigit() for c in node) and node.strip().replace("e", "").replace("E", "").replace(".", "").replace("-", "").replace("+", "").isdigit() else node
        except ValueError:
            return node
    return node


def load(path: str = DEFAULT_PATH) -> Params:
    with open(path, "r", encoding="utf-8") as f:
        tree = _coerce(yaml.safe_load(f))
    return Params(tree, path)


def status_table(p: Params):
    """Rows (key, value, unit, status, source) for reporting evidence status."""
    rows = []
    for k in p.keys():
        lf = p.leaf(k)
        rows.append((k, lf["value"], lf.get("unit", ""), lf.get("status", ""), lf.get("source", "")))
    return rows
