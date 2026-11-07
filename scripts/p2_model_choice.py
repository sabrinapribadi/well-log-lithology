"""P2: choose between the pre-registered candidates by well-grouped CV, then score the choice once (ADR-004).

    python scripts/p2_model_choice.py

Candidates: A (XGBoost + engineered features), B (A + expected-penalty decision), C (LightGBM + A's features + B's
decision). Selection: 5-fold GroupKFold by well on the 98 training wells, mean penalty score. The chosen candidate is
then fitted on all training wells and scored on the open and hidden tests; the others are scored too, as a check.
Gate (ADR-002 P2): chosen beats P1 by >= 0.02 on the hidden test and scores better on the open test.
Writes data/outputs/p2_model_choice.json and WLL_DATA_DIR/derived/p2_predictions.parquet.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
import yaml
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p1_baseline import PARAMS, report  # noqa: E402
from src.features import engineered_matrix, expected_penalty_decision, full_proba, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
DER = DATA / CFG["paths"]["derived"]
LGB = dict(n_estimators=300, max_depth=8, num_leaves=127, learning_rate=0.1, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
           random_state=42, n_jobs=8, objective="multiclass", verbose=-1)
MARGIN = 0.02
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def fit(kind: str, X, y):
    return (xgb.XGBClassifier(**PARAMS) if kind == "xgb" else lgb.LGBMClassifier(**LGB)).fit(X, y)


def decide(proba: np.ndarray, rule: str) -> np.ndarray:
    return expected_penalty_decision(proba) if rule == "penalty" else proba.argmax(1)


CANDIDATES = {"A": ("xgb", "argmax"), "B": ("xgb", "penalty"), "C": ("lgb", "penalty")}


def main() -> None:
    t0 = time.time()
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    codes = strat_codes(tr)
    Xtr, ytr, gtr = engineered_matrix(tr, codes), labels(tr), tr.WELL.to_numpy()
    assert (Xtr.index == tr.index).all()
    # well-grouped CV: A and B share the same XGBoost fits; C uses LightGBM
    cv = {k: [] for k in CANDIDATES}
    for fold, (a, b) in enumerate(GroupKFold(n_splits=5).split(Xtr, ytr, gtr)):
        for lib in ("xgb", "lgb"):
            proba = full_proba(fit(lib, Xtr.iloc[a], ytr[a]), Xtr.iloc[b])
            for k, (kind, rule) in CANDIDATES.items():
                if kind == lib:
                    cv[k].append(penalty_score(ytr[b], decide(proba, rule)))
        log(f"fold {fold + 1}/5", {k: round(v[-1], 4) for k, v in cv.items()})
    cv_mean = {k: float(np.mean(v)) for k, v in cv.items()}
    chosen = max(cv_mean, key=cv_mean.get)
    log("CV means", {k: round(v, 4) for k, v in cv_mean.items()}, "→ chosen", chosen)
    # score every candidate on the open and hidden tests (the gate uses the chosen one only)
    p1 = json.loads((ROOT / CFG["paths"]["outputs_dir"] / "p1_baseline.json").read_text())
    res = {"design": "ADR-004 P2", "cv_folds": cv, "cv_mean": cv_mean, "chosen": chosen, "candidates": {}, "margin": MARGIN,
           "p1": {k: p1[k]["penalty_score"] for k in ("open_test", "hidden_test")}}
    preds = []
    for lib in ("xgb", "lgb"):
        m = fit(lib, Xtr, ytr)
        for name, d in (("open_test", ot), ("hidden_test", hd)):
            proba = full_proba(m, engineered_matrix(d, codes)); y = labels(d)
            for k, (kind, rule) in CANDIDATES.items():
                if kind != lib:
                    continue
                p = decide(proba, rule)
                res["candidates"].setdefault(k, {})[name] = report(y, p, d.WELL.to_numpy())
                if k == chosen:
                    preds.append(pd.DataFrame({"split": name, "WELL": d.WELL, "DEPTH_MD": d.DEPTH_MD, "y": y, "p": p, "pmax": proba.max(1)}))
        log(lib, "scored")
    c = res["candidates"][chosen]
    gain_hidden = c["hidden_test"]["penalty_score"] - res["p1"]["hidden_test"]
    gain_open = c["open_test"]["penalty_score"] - res["p1"]["open_test"]
    res["gain_vs_p1"] = {"hidden_test": gain_hidden, "open_test": gain_open}
    res["gate_passed"] = bool(gain_hidden >= MARGIN and gain_open > 0)
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p2_model_choice.json").write_text(json.dumps(res, indent=1))
    pd.concat(preds).to_parquet(DER / "p2_predictions.parquet", index=False)
    log(f"chosen {chosen}: hidden {c['hidden_test']['penalty_score']:.4f} (P1 {res['p1']['hidden_test']:.4f}, gain {gain_hidden:+.4f}); "
        f"open {c['open_test']['penalty_score']:.4f} (gain {gain_open:+.4f}) → {'PASS' if res['gate_passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
