"""P2 follow-up: why candidate C (LightGBM) collapsed. Training wells only; no test well is touched.

    python scripts/p2_lgb_diagnostic.py

Fits LightGBM on 30 training wells and scores the fit on the same wells, with the pre-registered settings and with
XGBoost's leaf safeguard (minimum hessian per leaf 1 instead of LightGBM's default 0.001). Writes
data/outputs/p2_lgb_diagnostic.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DER, LGB  # noqa: E402
from src.features import engineered_matrix, full_proba, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

CONFIGS = {"pre-registered (min_sum_hessian_in_leaf 0.001)": LGB, "min_sum_hessian_in_leaf 1 (as XGBoost min_child_weight)": {**LGB, "min_sum_hessian_in_leaf": 1.0}}


def main() -> None:
    tr = pd.read_parquet(DER / "force_train.parquet").sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    sub = tr[tr.WELL.isin(sorted(tr.WELL.unique())[:30])].reset_index(drop=True)
    X, y = engineered_matrix(sub, strat_codes(tr)), labels(sub)
    out = {"wells": 30, "samples": len(sub), "configs": {}}
    for name, params in CONFIGS.items():
        m = lgb.LGBMClassifier(**params).fit(X, y)
        p = full_proba(m, X).argmax(1)
        out["configs"][name] = {"train_fit_penalty": penalty_score(y, p), "train_fit_accuracy": float((p == y).mean()),
                                "max_abs_raw_score": float(np.abs(m.predict_proba(X, raw_score=True)).max())}
        print(name, out["configs"][name], flush=True)
    (ROOT / CFG["paths"]["outputs_dir"] / "p2_lgb_diagnostic.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
