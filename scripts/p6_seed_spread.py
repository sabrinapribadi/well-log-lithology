"""P6 follow-up (ADR-008 falsification): how much does model B's hidden score move with the random seed alone?

    python scripts/p6_seed_spread.py

Same data, code and settings as P2's candidate B; only `random_state` changes (1, 2, 3; the chosen model used 42).
Run on the laptop; the spread is the yardstick for the Databricks parity gap. Writes data/outputs/p6_seed_spread.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p1_baseline import PARAMS  # noqa: E402
from scripts.p2_model_choice import CFG, DER  # noqa: E402
from src.features import engineered_matrix, expected_penalty_decision, full_proba, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score  # noqa: E402


def main() -> None:
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, hd = sort(pd.read_parquet(DER / "force_train.parquet")), sort(pd.read_parquet(DER / "force_hidden_test.parquet"))
    codes = strat_codes(tr); Xtr, Xhd, y, yh = engineered_matrix(tr, codes), engineered_matrix(hd, codes), labels(tr), labels(hd)
    scores = {}
    for seed in (1, 2, 3):
        t = time.time(); m = xgb.XGBClassifier(**{**PARAMS, "random_state": seed}).fit(Xtr, y)
        scores[seed] = penalty_score(yh, expected_penalty_decision(full_proba(m, Xhd)))
        print(f"seed {seed}: hidden {scores[seed]:.4f} ({time.time() - t:.0f} s)", flush=True)
    v = list(scores.values()) + [-0.5040]
    res = {"design": "ADR-008 falsification: seed spread", "hidden_by_seed": scores, "seed_42": -0.5040,
           "min": min(v), "max": max(v), "range": max(v) - min(v), "sd": float(np.std(v, ddof=1)), "databricks_seed_42": -0.4861}
    (ROOT / CFG["paths"]["outputs_dir"] / "p6_seed_spread.json").write_text(json.dumps(res, indent=1))
    print(res)


if __name__ == "__main__":
    main()
