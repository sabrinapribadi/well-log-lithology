"""P3b step 3: train M1a and M1b (ADR-013 §5) on the 98 FORCE training wells with model T's settings.

    python scripts/p3b_train.py

M1a = model T's inputs plus physics features (RHOmaa, neutron-density separation, apparent matrix transit time, Umaa, GR
index). M1b = the same without raw RHOB and NPHI levels (RHOB, NPHI, roll_RHOB, roll_NPHI), so "density near quartz" cannot
act as a sandstone shortcut. Their North Sea open and hidden scores are reported, not gated. Training class priors are
saved for M2. Writes WLL_DATA_DIR/models/p3b_M1a.json, p3b_M1b.json and data/outputs/p3b_models.json.
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
from scripts.p1_baseline import PARAMS, report  # noqa: E402
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.features import expected_penalty_decision, full_proba, labels, transfer_matrix  # noqa: E402
from src.physics import physics_features  # noqa: E402
from src.scoring import NAMES  # noqa: E402

DROP_B = ["RHOB", "NPHI", "roll_RHOB", "roll_NPHI"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def m1_matrix(d: pd.DataFrame, variant: str) -> pd.DataFrame:
    d = d.sort_values(["WELL", "DEPTH_MD"])
    X = pd.concat([transfer_matrix(d), physics_features(d)], axis=1)
    return X.drop(columns=DROP_B) if variant == "M1b" else X


def main() -> None:
    t0 = time.time()
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)  # noqa: E731
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    y = labels(tr)
    priors = np.bincount(y, minlength=len(NAMES)) / len(y)
    res = {"design": "ADR-013 §5", "params": PARAMS, "training_priors": {n: float(p) for n, p in zip(NAMES, priors)}, "variants": {}}
    (DATA / "models").mkdir(exist_ok=True)
    for v in ("M1a", "M1b"):
        Xtr = m1_matrix(tr, v)
        model = xgb.XGBClassifier(**PARAMS).fit(Xtr, y)
        r = {"features": list(Xtr.columns)}
        for name, d in (("open_test", ot), ("hidden_test", hd)):
            p = expected_penalty_decision(full_proba(model, m1_matrix(d, v)))
            rep = report(labels(d), p, d.WELL.to_numpy())
            r[name] = {"penalty_score": rep["penalty_score"], "accuracy": rep["accuracy"], "recall": rep.get("recall")}
            log(v, name, round(rep["penalty_score"], 4), "accuracy", round(rep["accuracy"], 3))
        model.save_model(DATA / "models" / f"p3b_{v}.json")
        res["variants"][v] = r
    res["seconds"] = round(time.time() - t0)
    (ROOT / CFG["paths"]["outputs_dir"] / "p3b_models.json").write_text(json.dumps(res, indent=1))
    log("done", res["seconds"], "s")


if __name__ == "__main__":
    main()
