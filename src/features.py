"""Features and decision rule for P1 and P2 (ADR-004)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.scoring import A, to_class

LABEL = "FORCE_2020_LITHOFACIES_LITHOLOGY"
LOGS = ["CALI", "RSHA", "RMED", "RDEP", "RHOB", "GR", "SGR", "NPHI", "PEF", "DTC", "SP", "BS", "ROP", "DTS", "DCAL", "DRHO",
        "MUDWEIGHT", "RMIC", "ROPA", "RXO"]
POSITION = ["DEPTH_MD", "X_LOC", "Y_LOC", "Z_LOC"]
STRAT = ["GROUP", "FORMATION"]
RESISTIVITY = ["RSHA", "RMED", "RDEP", "RXO", "RMIC"]
CONTEXT = ["GR", "RHOB", "NPHI", "DTC", "PEF"]
HALF_WINDOW = 5


def strat_codes(train: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Integer codes for GROUP and FORMATION, fitted on the training wells only."""
    return {c: {v: i for i, v in enumerate(sorted(train[c].dropna().unique()))} for c in STRAT}


def baseline_matrix(d: pd.DataFrame, codes: dict) -> pd.DataFrame:
    """P1 features: logs as provided, position, stratigraphy codes (unseen names → missing)."""
    X = d[LOGS + POSITION].astype("float32").copy()
    for c in STRAT:
        X[c] = d[c].map(codes[c]).astype("float32")
    return X


def engineered_matrix(d: pd.DataFrame, codes: dict) -> pd.DataFrame:
    """P2 features (candidate A): baseline plus log resistivities, bad-hole size, per-well GR percentile and vertical
    context (first difference and centred rolling mean within each well, ordered by depth)."""
    d = d.sort_values(["WELL", "DEPTH_MD"])
    X = baseline_matrix(d, codes)
    for c in RESISTIVITY:
        X[f"log_{c}"] = np.log10(d[c].clip(lower=1e-3)).astype("float32")
    X["badhole"] = (d["CALI"] - d["BS"]).astype("float32")
    X["gr_pct_well"] = d.groupby("WELL")["GR"].rank(pct=True).astype("float32")
    g = d.groupby("WELL")
    for c in CONTEXT:
        X[f"d_{c}"] = g[c].diff().astype("float32")
        X[f"roll_{c}"] = g[c].transform(lambda s: s.rolling(2 * HALF_WINDOW + 1, center=True, min_periods=1).mean()).astype("float32")
    return X


def labels(d: pd.DataFrame) -> np.ndarray:
    return to_class(d[LABEL].to_numpy())


def full_proba(model, X) -> np.ndarray:
    """Class probabilities in all 12 columns. A training fold can miss a rare class (basement: 103 samples in a few
    wells), so the model returns fewer columns; those classes get probability 0, the others keep their index."""
    proba = model.predict_proba(X)
    out = np.zeros((proba.shape[0], len(A)), dtype=proba.dtype)
    out[:, np.asarray(model.classes_, dtype=int)] = proba
    return out


def expected_penalty_decision(proba: np.ndarray) -> np.ndarray:
    """Candidate B: the class with the lowest expected penalty, argmin_k sum_j p_j A[j, k] (Bayes decision rule)."""
    return np.argmin(proba @ A, axis=1)
