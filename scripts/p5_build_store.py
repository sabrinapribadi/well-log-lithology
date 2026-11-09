"""P5 serving store (ADR-007, amendment 1): validated outputs only.

    python scripts/p5_build_store.py

- FORCE open and hidden wells: model B's lithology column (run-length intervals), doubtful intervals (top probability
  < 0.5), rock shares and blind score.
- Kansas wells: P4 quality (the best-covered file per well); model T's confidence is kept as a drift signal only.
- Kansas units: P3 agreement and lift (the transfer test that failed).
Writes WLL_DATA_DIR/serving/store.json.
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
from src.scoring import NAMES  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
DER, OUT = DATA / CFG["paths"]["derived"], ROOT / CFG["paths"]["outputs_dir"]
STEP = 0.152


def runs(depth: np.ndarray, vals: np.ndarray) -> list[tuple[int, int]]:
    cut = np.flatnonzero(np.diff(vals)) + 1
    return list(zip(np.r_[0, cut], np.r_[cut, len(vals)]))


def main() -> None:
    p2 = json.loads((OUT / "p2_model_choice.json").read_text())
    b = p2["candidates"][p2["chosen"]]
    pr = pd.read_parquet(DER / "p2_predictions.parquet").sort_values(["split", "WELL", "DEPTH_MD"])
    force = {}
    for (split, well), g in pr.groupby(["split", "WELL"]):
        d, p, y, conf = g.DEPTH_MD.to_numpy(), g.p.to_numpy(), g.y.to_numpy(), g.pmax.to_numpy()
        iv = [{"rock": NAMES[int(p[s])], "top_m": round(float(d[s]), 1), "base_m": round(float(d[e - 1]) + STEP, 1),
               "probability": round(float(conf[s:e].mean()), 2)} for s, e in runs(d, p)]
        low = conf < 0.5
        doubt = [{"top_m": round(float(d[s]), 1), "base_m": round(float(d[e - 1]) + STEP, 1)} for s, e in runs(d, low.astype(int)) if low[s]]
        shares = pd.Series([NAMES[int(k)] for k in p]).value_counts(normalize=True).round(3)
        force[well] = {"well": well, "split": "hidden" if split == "hidden_test" else "open", "model": "B (P2 choice, XGBoost)",
                       "top_m": round(float(d.min()), 1), "base_m": round(float(d.max()), 1), "logged_m": round(len(d) * STEP),
                       "blind_score": round(b[split]["per_well"][well], 3), "share_as_interpreted": round(float((p == y).mean()), 3),
                       "rock_shares": shares.head(5).to_dict(), "doubtful_m": round(float(low.sum() * STEP)), "doubtful_intervals": len(doubt),
                       "intervals": iv, "doubtful": doubt[:200]}
    q = pd.read_parquet(DER / "p4_file_quality.parquet")
    q = q[q.ok].sort_values(["kgs_id", "coverage_core3"], ascending=[True, False]).drop_duplicates("kgs_id")
    kansas = {}
    for r in q.itertuples():
        kansas[str(r.kgs_id)] = {"kgs_id": str(r.kgs_id), "archive": r.archive, "logged_samples": int(r.samples),
                                 "curves": [c for c in ("GR", "RHOB", "NPHI", "DTC", "RDEP", "PEF", "CALI") if getattr(r, f"has_{c}")],
                                 "coverage_gr_neutron_density": round(float(r.coverage_core3), 3),
                                 "out_of_range_share": None if pd.isna(r.out_of_range_share) else round(float(r.out_of_range_share), 4),
                                 "bad_hole_share": None if pd.isna(r.bad_hole_share) else round(float(r.bad_hole_share), 3), "bad_hole_basis": r.bad_hole_basis,
                                 "model_t_confidence_median": None if pd.isna(r.t_conf_median) else round(float(r.t_conf_median), 2),
                                 "lithology_validated": False}
    p3 = json.loads((OUT / "p3_kansas_transfer.json").read_text())
    units = {u: {"unit": u, "expected_rock": v["expected_rock"], "gated": v["gated"], "wells_scored": v["wells_scored"],
                 "median_agreement": None if v["median_agreement"] is None else round(v["median_agreement"], 3),
                 "lift": round(v["lift"], 2) if np.isfinite(v["lift"]) else None,
                 "passed": v["passed"], "predicted_mix_inside": {k: round(x, 2) for k, x in v["predicted_mix_inside"].items()}} for u, v in p3["units"].items()}
    store = {"version": 1, "force": force, "kansas": kansas, "units": units,
             "meta": {"p3_gate_passed": p3["gate_passed"], "model_b_hidden_score": round(b["hidden_test"]["penalty_score"], 3)}}
    (DATA / "serving").mkdir(exist_ok=True)
    (DATA / "serving" / "store.json").write_text(json.dumps(store, separators=(",", ":")))
    print(len(force), "FORCE wells;", len(kansas), "Kansas wells;", len(units), "units")


if __name__ == "__main__":
    main()
