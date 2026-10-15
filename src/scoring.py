"""FORCE 2020 penalty score (ADR-001): S = -(1/N) * sum A[true, predicted], with the official 12 x 12 matrix."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
A = np.array(json.loads((ROOT / "configs" / "penalty_matrix.json").read_text())["matrix"])
CODES = {int(k): v for k, v in CFG["lithology_codes"].items()}
NAMES = CFG["lithology_names"]


def to_class(codes) -> np.ndarray:
    """FORCE lithology codes (e.g. 65000) → class index 0–11."""
    return np.vectorize(CODES.get)(np.asarray(codes).astype(int))


def penalty_score(y_true, y_pred) -> float:
    """Official score on class indices: 0 is perfect; more negative is worse (vectorised official formula)."""
    t, p = np.asarray(y_true, dtype=int), np.asarray(y_pred, dtype=int)
    return float(-A[t, p].mean())
