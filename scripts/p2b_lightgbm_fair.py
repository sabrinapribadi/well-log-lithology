"""P2b candidate C2 (ADR-009): candidate C with LightGBM's leaf limit matched to XGBoost (min_sum_hessian_in_leaf = 1).

    python scripts/p2b_lightgbm_fair.py

Same 5-fold well-grouped CV as P2, then fitted on all 98 training wells and scored once on the open and hidden wells.
Writes data/outputs/p2b_lightgbm_fair.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p1_baseline import report  # noqa: E402
from scripts.p2_model_choice import CFG, DER, LGB  # noqa: E402
from src.features import engineered_matrix, expected_penalty_decision, full_proba, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

C2 = {**LGB, "min_sum_hessian_in_leaf": 1.0}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main() -> None:
    t0 = time.time()
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    codes = strat_codes(tr)
    X, y, g = engineered_matrix(tr, codes), labels(tr), tr.WELL.to_numpy()
    cv = []
    for fold, (a, b) in enumerate(GroupKFold(n_splits=5).split(X, y, g)):
        m = lgb.LGBMClassifier(**C2).fit(X.iloc[a], y[a])
        cv.append(penalty_score(y[b], expected_penalty_decision(full_proba(m, X.iloc[b]))))
        log(f"fold {fold + 1}/5 {cv[-1]:.4f}")
    m = lgb.LGBMClassifier(**C2).fit(X, y)
    res = {"design": "ADR-009 C2", "params": C2, "cv_folds": cv, "cv_mean": float(np.mean(cv))}
    for name, d in (("open_test", ot), ("hidden_test", hd)):
        res[name] = report(labels(d), expected_penalty_decision(full_proba(m, engineered_matrix(d, codes))), d.WELL.to_numpy())
        log(name, round(res[name]["penalty_score"], 4))
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p2b_lightgbm_fair.json").write_text(json.dumps(res, indent=1))
    log(f"C2 CV {res['cv_mean']:.4f}; hidden {res['hidden_test']['penalty_score']:.4f}")


if __name__ == "__main__":
    main()
