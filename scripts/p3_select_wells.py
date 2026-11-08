"""P3 step 2: choose the Kansas wells and unit intervals to score (ADR-005 §2, §4), from headers and tops only.

    python scripts/p3_select_wells.py

No prediction is read or made here. For each unit: wells with a KGS top for it and an eligible LAS file (GR, a neutron
log, and a density or density-porosity log in the header) whose depth range covers the interval; up to 300 wells drawn
at random (seed 42). Interval = top to the next deeper top in the same well, capped per ADR-005; the Heebner uses the
first 1.5 m. Several picks of the same top in one well: the median depth is used (implementation choice, logged).
Writes WLL_DATA_DIR/derived/p3_selection.parquet and data/outputs/p3_selection.json.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.curves import CORE  # noqa: E402

FT = 0.3048
TOPS = DATA / "kgs" / "fresh" / "ks_tops.zip"
# unit -> (tops-name pattern, expected rock, cap in metres, gated)
UNITS = {
    "Hutchinson Salt": (r"hutchinson salt", "Halite", 170.0, True),
    "Stone Corral": (r"stone corral|cimarron anhydrite", "Anhydrite", 14.0, True),
    "Arbuckle": (r"^arbuckle", "Dolomite", 30.0, True),
    "Heebner": (r"heebner", "Shale", 1.5, True),
    "Lansing-Kansas City": (r"^lansing|^kansas city", "Limestone", 120.0, True),
    "Cherokee": (r"^cherokee", "Shale", 150.0, True),
    "Mississippian": (r"^mississippian", "Limestone", 30.0, False),
    "Precambrian": (r"precambrian|^granite$", "Basement", 30.0, False),
}
MAX_WELLS = 300


def main() -> None:
    tops = pd.read_csv(zipfile.ZipFile(TOPS).open("ks_tops.txt"), dtype=str, usecols=["KID", "FORMATION", "TOP"])
    tops["top_m"] = pd.to_numeric(tops.TOP, errors="coerce") * FT
    tops = tops.dropna(subset=["top_m"])
    tops["name"] = tops.FORMATION.str.lower().str.strip()
    f = pd.read_parquet(DER / "kgs_files.parquet")
    c = pd.read_parquet(DER / "kgs_curves.parquet")
    std = c.dropna(subset=["standard"]).groupby(["archive", "file"]).standard.apply(set)
    f = f[f.ok & f.kgs_id.notna()].copy()
    f["std"] = [std.get((a, n), set()) for a, n in zip(f.archive, f.file)]
    f = f[f["std"].apply(lambda s: {"GR", "NPHI"} <= s and bool({"RHOB", "DPHI"} & s))]
    unit_m = f.depth_unit.str.upper().str.startswith("M")
    f["strt_m"] = np.where(unit_m, f.strt, f.strt * FT)
    f["stop_m"] = np.where(unit_m, f.stop, f.stop * FT)
    f["n_core"] = f["std"].apply(lambda s: len(set(CORE) & (s | ({"RHOB"} if "DPHI" in s else set()))))
    rng = np.random.default_rng(42)
    rows, summary = [], {}
    for unit, (pat, rock, cap, gated) in UNITS.items():
        u = tops[tops.name.str.contains(pat, regex=True)].groupby("KID").top_m.median()
        # next deeper top of any name in the same well
        cand = tops[tops.KID.isin(u.index)][["KID", "top_m"]]
        nxt = cand.merge(u.rename("utop"), left_on="KID", right_index=True)
        nxt = nxt[nxt.top_m > nxt.utop + 0.05].groupby("KID").top_m.min()
        base = pd.concat([u + cap, nxt.reindex(u.index)], axis=1).min(axis=1) if unit != "Heebner" else u + cap
        iv = pd.DataFrame({"top_m": u, "base_m": base})
        el = f.merge(iv, left_on="kgs_id", right_index=True)
        el = el[(el.strt_m <= el.top_m) & (el.stop_m >= el.base_m - 0.5)]
        el = el.sort_values(["kgs_id", "n_core", "size"], ascending=[True, False, False]).drop_duplicates("kgs_id")
        pick = el if len(el) <= MAX_WELLS else el.loc[rng.choice(el.index.to_numpy(), MAX_WELLS, replace=False)]
        rows.append(pick.assign(unit=unit, rock=rock, gated=gated)[["unit", "rock", "gated", "kgs_id", "archive", "entry", "file", "top_m", "base_m"]])
        summary[unit] = {"expected_rock": rock, "gated": gated, "wells_with_top": int(len(u)), "eligible_wells": int(len(el)),
                         "selected": int(len(pick)), "median_interval_m": round(float((pick.base_m - pick.top_m).median()), 1) if len(pick) else None}
        print(unit, summary[unit], flush=True)
    sel = pd.concat(rows, ignore_index=True)
    sel.to_parquet(DER / "p3_selection.parquet", index=False)
    out = {"design": "ADR-005 §4", "units": summary, "files_to_read": int(sel.entry.nunique()),
           "archives": sel.drop_duplicates("entry").archive.value_counts().sort_index().to_dict()}
    (ROOT / CFG["paths"]["outputs_dir"] / "p3_selection.json").write_text(json.dumps(out, indent=1))
    print(out["files_to_read"], "files;", out["archives"])


if __name__ == "__main__":
    main()
