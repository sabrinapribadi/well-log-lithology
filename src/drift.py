"""Drift statistic shared by P4 (laptop) and P6 (Databricks), ADR-006."""

from __future__ import annotations

import numpy as np

BINS = 10

def psi(ref: np.ndarray, new: np.ndarray, bins: int = BINS) -> float | None:
    """Population stability index on quantile bins of the reference (Yurdakul and Naranjo 2020)."""
    ref, new = ref[np.isfinite(ref)], new[np.isfinite(new)]
    if len(ref) < 100 or len(new) < 100:
        return None
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return None
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    n = np.histogram(new, edges)[0] / len(new)
    r, n = np.clip(r, 1e-6, None), np.clip(n, 1e-6, None)
    return float(np.sum((n - r) * np.log(n / r)))
