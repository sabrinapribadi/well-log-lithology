"""Down-sample the P4 drift sample to 360,000 rows, uniformly, so years keep their P4 weights (ADR-008), for upload to Databricks.

    python scripts/p6_drift_reference.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DER = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "derived"


def main() -> None:
    d = pd.read_parquet(DER / "p4_drift_sample.parquet")
    # uniform sample, so each year keeps its share of the pooled reference exactly as in P4 (ADR-008 deviation, 2026-11-09)
    r = d.sample(n=min(len(d), 360_000), random_state=42)
    assert "archive" in r and r.archive.nunique() == d.archive.nunique()
    r.to_parquet(DER / "p6_drift_reference.parquet", index=False)
    print(len(d), "->", len(r), "rows")


if __name__ == "__main__":
    main()
