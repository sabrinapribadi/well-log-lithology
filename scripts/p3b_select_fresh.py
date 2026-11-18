"""P3b step 2: the one-shot test set (ADR-013 §4): fresh Kansas wells, never scored in P3, from headers and tops only.

    python scripts/p3b_select_fresh.py                  # P3b (ADR-013): excludes the P3 wells; seed 2026
    python scripts/p3b_select_fresh.py --design p3c     # P3c (ADR-014): also excludes the P3b test wells; seed 2027

Same units, intervals and eligibility as P3 (scripts/p3_select_wells.py, ADR-005 §2 and §4), with two differences fixed in
ADR-013 before any test file is opened: (1) the corrected curve mapping (a density mnemonic described as a correction is
not density), and (2) every well already scored in P3 (the development set) is excluded by KGS well ID. Up to 100 wells
per unit, drawn at random with seed 2026. No LAS data and no prediction is read here.
Writes WLL_DATA_DIR/derived/<design>_test_selection.parquet and data/outputs/<design>_test_manifest.json (counts and a
SHA-256 of the sorted unit, well and file list, recorded in the ADR before scoring).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DER  # noqa: E402
from scripts.p3_select_wells import FT, TOPS, UNITS  # noqa: E402
from src.curves import CORE, standard_name  # noqa: E402

MAX_WELLS = 100
DESIGNS = {"p3b": {"seed": 2026, "adr": "ADR-013 §4", "exclude": []},
           "p3c": {"seed": 2027, "adr": "ADR-014 §3", "exclude": ["p3b_test_selection.parquet"]}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", choices=list(DESIGNS), default="p3b")
    design = ap.parse_args().design
    cfg = DESIGNS[design]
    dev = set(pd.read_parquet(DER / "p3_selection.parquet").kgs_id)
    used = set(dev)
    for p in cfg["exclude"]:
        used |= set(pd.read_parquet(DER / p).kgs_id)
    tops = pd.read_csv(zipfile.ZipFile(TOPS).open("ks_tops.txt"), dtype=str, usecols=["KID", "FORMATION", "TOP"])
    tops["top_m"] = pd.to_numeric(tops.TOP, errors="coerce") * FT
    tops = tops.dropna(subset=["top_m"])
    tops["name"] = tops.FORMATION.str.lower().str.strip()
    f = pd.read_parquet(DER / "kgs_files.parquet")
    c = pd.read_parquet(DER / "kgs_curves.parquet")
    c["standard"] = [standard_name(m, d) for m, d in zip(c.mnemonic.astype(str), c.description.fillna(""))]   # corrected mapping
    std = c.dropna(subset=["standard"]).groupby(["archive", "file"]).standard.apply(set)
    f = f[f.ok & f.kgs_id.notna() & ~f.kgs_id.isin(used)].copy()
    f["std"] = [std.get((a, n), set()) for a, n in zip(f.archive, f.file)]
    f = f[f["std"].apply(lambda s: {"GR", "NPHI"} <= s and bool({"RHOB", "DPHI"} & s))]
    unit_m = f.depth_unit.str.upper().str.startswith("M")
    f["strt_m"] = np.where(unit_m, f.strt, f.strt * FT)
    f["stop_m"] = np.where(unit_m, f.stop, f.stop * FT)
    f["n_core"] = f["std"].apply(lambda s: len(set(CORE) & (s | ({"RHOB"} if "DPHI" in s else set()))))
    rng = np.random.default_rng(cfg["seed"])
    rows, summary = [], {}
    for unit, (pat, rock, cap, gated) in UNITS.items():
        u = tops[tops.name.str.contains(pat, regex=True)].groupby("KID").top_m.median()
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
        summary[unit] = {"expected_rock": rock, "gated": gated, "fresh_eligible_wells": int(len(el)), "selected": int(len(pick)),
                         "median_interval_m": round(float((pick.base_m - pick.top_m).median()), 1) if len(pick) else None}
        print(unit, summary[unit], flush=True)
    sel = pd.concat(rows, ignore_index=True).sort_values(["unit", "kgs_id"]).reset_index(drop=True)
    assert not set(sel.kgs_id) & used, "an already-scored well leaked into the test set"
    sel.to_parquet(DER / f"{design}_test_selection.parquet", index=False)
    listing = "\n".join(f"{r.unit}\t{r.kgs_id}\t{r.entry}" for r in sel.itertuples())
    out = {"design": cfg["adr"], "seed": cfg["seed"], "max_wells_per_unit": MAX_WELLS, "development_wells_excluded": len(dev),
           "units": summary, "files": int(sel.entry.nunique()), "rows": int(len(sel)),
           "sha256": hashlib.sha256(listing.encode()).hexdigest()}
    if design != "p3b":
        out["earlier_test_wells_excluded"] = len(used - dev)
    (ROOT / CFG["paths"]["outputs_dir"] / f"{design}_test_manifest.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "units"}))


if __name__ == "__main__":
    main()
