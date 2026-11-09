"""Down-sample the P4 drift sample to at most 20,000 rows per archive year (ADR-008 amendment 1), for upload to Databricks.

    python scripts/p6_drift_reference.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DER = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "derived"


def main() -> None:
    d = pd.read_parquet(DER / "p4_drift_sample.parquet")
    r = d.groupby("archive", group_keys=False).apply(lambda g: g.sample(min(len(g), 20_000), random_state=42))
    r.to_parquet(DER / "p6_drift_reference.parquet", index=False)
    print(len(d), "->", len(r), "rows")


if __name__ == "__main__":
    main()
