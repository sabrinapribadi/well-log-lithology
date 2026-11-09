"""P3 follow-up (ADR-005 falsification): are Kansas log values inside each unit like FORCE's values for the same rock?

    python scripts/p3_diagnostic.py

Diagnostic only; the P3 result is unchanged. Reads up to 40 selected wells per unit (first 40 by KGS ID), takes median
log values inside the unit intervals, and compares them with FORCE training medians for the expected rock and for
sandstone. Writes data/outputs/p3_diagnostic.json.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.features import labels  # noqa: E402
from src.kansas import load_well  # noqa: E402
from src.scoring import NAMES  # noqa: E402

ZIPS = DATA / CFG["paths"]["kgs_las_zips"]
CURVES = ["GR", "RHOB", "NPHI", "DTC", "RDEP", "PEF"]


def one(job: dict) -> list[dict]:
    try:
        w = load_well(str(ZIPS / f"{job['archive']}.zip"), job["entry"])
    except Exception:  # noqa: BLE001
        return []
    out = []
    for u in job["units"]:
        s = w[(w.DEPTH_MD >= u["top_m"]) & (w.DEPTH_MD < u["base_m"])]
        out.append({"unit": u["unit"], **{c: float(s[c].median()) if c in s and s[c].notna().any() else np.nan for c in CURVES}})
    return out


def main() -> None:
    sel = pd.read_parquet(DER / "p3_selection.parquet")
    sel = sel.sort_values("kgs_id").groupby("unit").head(40)
    jobs = [{"archive": g.archive.iloc[0], "entry": e, "units": g[["unit", "top_m", "base_m"]].to_dict("records")} for e, g in sel.groupby("entry")]
    rows = []
    with ProcessPoolExecutor(3) as ex:
        for r in ex.map(one, jobs):
            rows += r
    ks = pd.DataFrame(rows).groupby("unit")[CURVES].median()
    ks["has_PEF_share"] = pd.DataFrame(rows).groupby("unit").PEF.apply(lambda s: float(s.notna().mean()))
    tr = pd.read_parquet(DER / "force_train.parquet", columns=CURVES + ["FORCE_2020_LITHOFACIES_LITHOLOGY"])
    tr["rock"] = [NAMES[k] for k in labels(tr)]
    fo = tr.groupby("rock")[CURVES].median()
    res = {"design": "ADR-005 falsification diagnostic", "kansas_unit_medians": ks.round(3).to_dict("index"),
           "force_rock_medians": fo.round(3).to_dict("index")}
    (ROOT / CFG["paths"]["outputs_dir"] / "p3_diagnostic.json").write_text(json.dumps(res, indent=1, default=float))
    print("KANSAS (inside unit)\n", ks.round(2).to_string(), "\n\nFORCE (by rock)\n", fo.round(2).to_string())


if __name__ == "__main__":
    main()
