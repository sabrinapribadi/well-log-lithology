"""P1: XGBoost baseline on the official FORCE splits (ADR-004, gate in ADR-002).

    python scripts/p1_baseline.py

Fits the pre-registered baseline on the 98 training wells; scores the open test and the hidden test once; reports
accuracy, recall per lithology and per-well scores; and runs the leakage check (random 80/20 split of training samples).
Writes data/outputs/p1_baseline.json and WLL_DATA_DIR/derived/p1_predictions.parquet.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features import baseline_matrix, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score, report  # noqa: E402,F401 — report re-exported for P2 scripts

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
DER = DATA / CFG["paths"]["derived"]
PARAMS = dict(n_estimators=300, max_depth=8, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, tree_method="hist",
              random_state=42, n_jobs=8, objective="multi:softprob")
GATE = -0.526
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)




def main() -> None:
    t0 = time.time()
    tr, ot, hd = (pd.read_parquet(DER / f"force_{k}.parquet") for k in ("train", "open_test", "hidden_test"))
    codes = strat_codes(tr)
    Xtr, ytr = baseline_matrix(tr, codes), labels(tr)
    model = xgb.XGBClassifier(**PARAMS).fit(Xtr, ytr)
    log(f"fitted in {time.time() - t0:.0f} s")
    res = {"design": "ADR-004 P1", "params": PARAMS, "features": list(Xtr.columns), "gate_threshold": GATE}
    preds = []
    for name, d in (("open_test", ot), ("hidden_test", hd)):
        proba = model.predict_proba(baseline_matrix(d, codes)); p = proba.argmax(1); y = labels(d)
        res[name] = report(y, p, d.WELL.to_numpy())
        preds.append(pd.DataFrame({"split": name, "WELL": d.WELL, "DEPTH_MD": d.DEPTH_MD, "y": y, "p": p, "pmax": proba.max(1)}))
        log(name, round(res[name]["penalty_score"], 4), "accuracy", round(res[name]["accuracy"], 3))
    # leakage check: random 80/20 split of training samples (what a random split would claim)
    rng = np.random.default_rng(42); m = rng.random(len(tr)) < 0.8
    leak = xgb.XGBClassifier(**PARAMS).fit(Xtr[m], ytr[m])
    pl = leak.predict_proba(Xtr[~m]).argmax(1)
    res["random_split"] = {"penalty_score": penalty_score(ytr[~m], pl), "accuracy": float((ytr[~m] == pl).mean())}
    log("random split", round(res["random_split"]["penalty_score"], 4))
    res["gate_passed"] = bool(res["hidden_test"]["penalty_score"] >= GATE)
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p1_baseline.json").write_text(json.dumps(res, indent=1))
    pd.concat(preds).to_parquet(DER / "p1_predictions.parquet", index=False)
    log(f"hidden {res['hidden_test']['penalty_score']:.4f} vs gate {GATE} → {'PASS' if res['gate_passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
