"""ADR-006: population stability index."""

import numpy as np

from scripts.p4_quality import psi


def test_psi_is_near_zero_for_same_distribution_and_large_for_a_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 20_000)
    assert psi(ref, rng.normal(0, 1, 20_000)) < 0.01
    assert psi(ref, rng.normal(1.5, 1, 20_000)) > 0.25          # an "alert"-sized shift
    assert psi(ref, np.full(50, 1.0)) is None                     # too few samples to judge
