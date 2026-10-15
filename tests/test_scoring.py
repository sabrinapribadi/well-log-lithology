"""ADR-001 metric: our vectorised scorer equals the official loop, and the class mapping covers all 12 codes."""

import numpy as np

from src.scoring import A, CODES, NAMES, penalty_score, to_class


def official_loop(y_true, y_pred):
    S = 0.0
    for i in range(len(y_true)):
        S -= A[int(y_true[i]), int(y_pred[i])]
    return S / len(y_true)


def test_scorer_matches_official_formula():
    rng = np.random.default_rng(0)
    t, p = rng.integers(0, 12, 5000), rng.integers(0, 12, 5000)
    assert abs(penalty_score(t, p) - official_loop(t, p)) < 1e-12
    assert penalty_score(t, t) == 0.0


def test_matrix_and_classes():
    assert A.shape == (12, 12) and np.all(np.diag(A) == 0) and np.allclose(A, A.T)
    assert sorted(CODES.values()) == list(range(12)) and len(NAMES) == 12
    assert list(to_class([65000, 30000, 93000])) == [2, 0, 11]
