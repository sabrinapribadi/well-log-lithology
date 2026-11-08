"""P3 step 1: the transfer model T (ADR-005 §1), trained on the 98 FORCE training wells.

    python scripts/p3_transfer_model.py

Candidate B's recipe with inputs restricted to logs Kansas files carry: no depth, position, North Sea stratigraphy or
drilling curves. Scores the open and hidden FORCE wells once (reported, not gated: the cost of dropping those inputs).
Writes data/outputs/p3_transfer_model.json and WLL_DATA_DIR/models/p3_transfer_T.json (the fitted booster).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p1_baseline import PARAMS, report  # noqa: E402
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.features import expected_penalty_decision, full_proba, labels, transfer_matrix  # noqa: E402

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main() -> None:
    t0 = time.time()
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    Xtr = transfer_matrix(tr)
    model = xgb.XGBClassifier(**PARAMS).fit(Xtr, labels(tr))
    log(f"T fitted on {Xtr.shape[1]} inputs in {time.time() - t0:.0f} s")
    res = {"design": "ADR-005 §1", "features": list(Xtr.columns), "params": PARAMS}
    for name, d in (("open_test", ot), ("hidden_test", hd)):
        p = expected_penalty_decision(full_proba(model, transfer_matrix(d)))
        res[name] = report(labels(d), p, d.WELL.to_numpy())
        log(name, round(res[name]["penalty_score"], 4), "accuracy", round(res[name]["accuracy"], 3))
    p2 = json.loads((ROOT / CFG["paths"]["outputs_dir"] / "p2_model_choice.json").read_text())
    res["b_hidden"] = p2["candidates"][p2["chosen"]]["hidden_test"]["penalty_score"]
    res["cost_vs_b_hidden"] = res["hidden_test"]["penalty_score"] - res["b_hidden"]
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p3_transfer_model.json").write_text(json.dumps(res, indent=1))
    (DATA / "models").mkdir(exist_ok=True)
    model.save_model(DATA / "models" / "p3_transfer_T.json")
    log(f"T hidden {res['hidden_test']['penalty_score']:.4f} vs B {res['b_hidden']:.4f} (cost {res['cost_vs_b_hidden']:+.4f})")


if __name__ == "__main__":
    main()
