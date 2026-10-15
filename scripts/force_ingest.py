"""P0: FORCE 2020 splits exactly as the organisers published them (ADR-001, ADR-002 P0).

    python scripts/force_ingest.py

Train (train.zip), open test (leaderboard features + target) and hidden test (with labels). Checks the pre-registered
counts (98 / 10 / 10 wells; 1,170,511 / 136,786 / 122,397 samples), that no well is in two splits, that every label
maps to one of the 12 classes, and writes WLL_DATA_DIR/derived/force_{train,open_test,hidden_test}.parquet.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.scoring import CODES  # noqa: E402

import yaml  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
OFF = DATA / CFG["paths"]["force_official"]
EXPECT = {"train": (98, 1_170_511), "open_test": (10, 136_786), "hidden_test": (10, 122_397)}
LABEL = "FORCE_2020_LITHOFACIES_LITHOLOGY"


def load() -> dict[str, pd.DataFrame]:
    z = zipfile.ZipFile(OFF / "train.zip")
    train = pd.read_csv(z.open("train.csv"), sep=";")
    feat = pd.read_csv(OFF / "leaderboard_test_features.csv", sep=";")
    tgt = pd.read_csv(OFF / "leaderboard_test_target.csv", sep=";")
    open_test = feat.merge(tgt, on=["WELL", "DEPTH_MD"], how="left", validate="one_to_one")
    hidden = pd.read_csv(OFF / "hidden_test.csv", sep=";")
    return {"train": train, "open_test": open_test, "hidden_test": hidden}


def main() -> None:
    d = load(); out = DATA / CFG["paths"]["derived"]; out.mkdir(parents=True, exist_ok=True)
    res = {"splits": {}, "checks": {}}
    wells = {k: set(v.WELL) for k, v in d.items()}
    for k, v in d.items():
        n_w, n = v.WELL.nunique(), len(v)
        res["splits"][k] = {"wells": n_w, "samples": n, "expected": {"wells": EXPECT[k][0], "samples": EXPECT[k][1]},
                            "matches": (n_w, n) == EXPECT[k], "labelled": float(v[LABEL].notna().mean()),
                            "classes_present": int(v[LABEL].nunique()), "columns": int(v.shape[1])}
        v.to_parquet(out / f"force_{k}.parquet", index=False)
    res["checks"]["no_well_in_two_splits"] = not (wells["train"] & wells["open_test"] or wells["train"] & wells["hidden_test"] or wells["open_test"] & wells["hidden_test"])
    res["checks"]["all_labels_mapped"] = all(set(v[LABEL].dropna().astype(int)) <= set(CODES) for v in d.values())
    res["checks"]["curve_missing_share_train"] = {c: round(float(d["train"][c].isna().mean()), 3) for c in
                                                  ["GR", "RHOB", "NPHI", "DTC", "RDEP", "RMED", "PEF", "CALI", "BS", "DRHO", "SP", "DTS", "RSHA"]}
    res["class_counts_train"] = {int(k): int(v) for k, v in d["train"][LABEL].value_counts().items()}
    res["wells"] = {k: sorted(v) for k, v in wells.items() if k != "train"}
    res["gate_force"] = all(s["matches"] for s in res["splits"].values()) and res["checks"]["no_well_in_two_splits"] and res["checks"]["all_labels_mapped"]
    (ROOT / CFG["paths"]["outputs_dir"]).mkdir(parents=True, exist_ok=True)
    (ROOT / CFG["paths"]["outputs_dir"] / "p0_force.json").write_text(json.dumps(res, indent=1))
    print({k: (s["wells"], s["samples"], s["matches"]) for k, s in res["splits"].items()}, res["checks"]["no_well_in_two_splits"], res["checks"]["all_labels_mapped"], "gate", res["gate_force"])


if __name__ == "__main__":
    main()
