"""ADR-004: the expected-penalty decision and the engineered features (no leakage across wells, order preserved)."""

import numpy as np
import pandas as pd

from src.features import LOGS, POSITION, engineered_matrix, expected_penalty_decision, strat_codes
from src.scoring import A


def test_certain_predictions_are_unchanged():
    proba = np.eye(12)
    assert list(expected_penalty_decision(proba)) == list(range(12))


def test_decision_can_differ_from_most_probable():
    # 40% coal (10), 30% tuff (9), 30% sandstone (0): coal is most probable, but tuff is "near" both others
    p = np.zeros((1, 12)); p[0, 10], p[0, 9], p[0, 0] = 0.40, 0.30, 0.30
    cost = p @ A
    assert p.argmax() == 10 and expected_penalty_decision(p)[0] == int(cost.argmin()) == 9


def _well(name, n, gr):
    d = pd.DataFrame({c: np.nan for c in LOGS + POSITION}, index=range(n))
    d["DEPTH_MD"] = np.arange(n, dtype=float); d["GR"] = gr; d["WELL"] = name; d["GROUP"] = "G"; d["FORMATION"] = "F"
    return d


def test_context_features_stay_within_each_well():
    d = pd.concat([_well("W1", 20, 10.0), _well("W2", 20, 100.0)], ignore_index=True)
    X = engineered_matrix(d, strat_codes(d))
    w1 = X.loc[d.WELL == "W1"]
    assert np.allclose(w1["roll_GR"], 10.0) and (w1["d_GR"].fillna(0) == 0).all()   # never mixes in W2's 100s
    assert list(X.index) == list(d.sort_values(["WELL", "DEPTH_MD"]).index)


def test_missing_class_gets_zero_probability_and_keeps_indices():
    from src.features import full_proba

    class Stub:  # a fold that never saw basement (11) or dolomite (4)
        classes_ = np.array([c for c in range(12) if c not in (4, 11)])
        def predict_proba(self, X):
            p = np.zeros((1, 10)); p[0, list(self.classes_).index(10)] = 1.0; return p
    out = full_proba(Stub(), None)
    assert out.shape == (1, 12) and out[0, 10] == 1.0 and out[0, 4] == out[0, 11] == 0
    assert expected_penalty_decision(out)[0] == 10


def test_transfer_matrix_has_no_position_or_stratigraphy_and_tolerates_missing_logs():
    from src.features import transfer_matrix
    d = pd.DataFrame({"WELL": ["K1"] * 5 + ["K2"] * 5, "DEPTH_MD": list(range(5)) * 2, "GR": [10.0] * 5 + [100.0] * 5})
    X = transfer_matrix(d)   # a Kansas-like file with only gamma ray
    assert not {"DEPTH_MD", "X_LOC", "Y_LOC", "Z_LOC", "GROUP", "FORMATION", "ROP", "MUDWEIGHT"} & set(X.columns)
    assert X["RHOB"].isna().all() and np.allclose(X.loc[d.WELL == "K1", "roll_GR"], 10.0)
