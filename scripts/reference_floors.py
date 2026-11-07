"""Reference points for reading the penalty score (ADR-001): "shale everywhere" per split and logged depth in metres.

    python scripts/reference_floors.py

Writes data/outputs/reference_floors.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features import labels  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DER = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / CFG["paths"]["derived"]
SHALE = 2


def main() -> None:
    out = {}
    for k in ("train", "open_test", "hidden_test"):
        d = pd.read_parquet(DER / f"force_{k}.parquet")
        y = labels(d)
        step = float(d.sort_values(["WELL", "DEPTH_MD"]).groupby("WELL").DEPTH_MD.diff().median())
        out[k] = {"wells": int(d.WELL.nunique()), "samples": len(d), "sample_step_m": round(step, 4),
                  "logged_m": round(len(d) * step), "shale_everywhere": penalty_score(y, np.full_like(y, SHALE)),
                  "shale_share": float((y == SHALE).mean())}
    (ROOT / CFG["paths"]["outputs_dir"] / "reference_floors.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
