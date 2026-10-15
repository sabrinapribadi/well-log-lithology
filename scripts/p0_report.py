"""P0 gate report (ADR-002): FORCE splits (from force_ingest.py) and the Kansas LAS inventory (from kgs_inventory.py).

    python scripts/p0_report.py

Writes data/outputs/p0_foundation.json and data/outputs/kgs_wells_summary.json (small, per-well summary for the map).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.curves import CORE, LITHOLOGY  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
DATA = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser()
OUT = ROOT / CFG["paths"]["outputs_dir"]


def main() -> None:
    force = json.loads((OUT / "p0_force.json").read_text())
    f = pd.read_parquet(DATA / "derived/kgs_files.parquet"); c = pd.read_parquet(DATA / "derived/kgs_curves.parquet")
    c2 = c[c.standard != "DEPTH"]
    per = c2.dropna(subset=["standard"]).groupby("file").standard.apply(set)
    has = lambda need: per.apply(lambda s: set(need) <= s).reindex(f.file).fillna(False).to_numpy()
    f = f.assign(has_gr=has(["GR"]), has_gr_rhob_nphi=has(["GR", "RHOB", "NPHI"]), has_core=has(CORE))
    kgs = {
        "files": int(len(f)), "readable": int(f.ok.sum()), "readable_share": float(f.ok.mean()),
        "wells": int(f.kgs_id.nunique()), "files_direct": int((~f.nested).sum()), "files_in_nested_zips": int(f.nested.sum()),
        "unreadable": f[~f.ok][["archive", "entry", "error"]].to_dict("records"),
        "las_version": f.version.replace({"2.00": "2.0", "1.20": "1.2"}).value_counts().to_dict(),
        "wrapped_files": int((f.wrap == "YES").sum()),
        "null_codes": {str(k): int(v) for k, v in f.null.value_counts().head(6).items()},
        "depth_units": f.depth_unit.replace({"F": "FT", "FEET": "FT"}).value_counts().to_dict(),
        "located_share": float(f.lat.notna().mean()), "location_source": f.lat_source.value_counts().to_dict(),
        "curve_entries": int(len(c2)),
        "curve_entries_recognised_share": float(c2.standard.notna().mean()),
        "curve_entries_lithology_share": float(c2.standard.isin(LITHOLOGY).mean()),
        "standard_curve_counts": c2.standard.value_counts().to_dict(),
        "top_unrecognised": c2[c2.standard.isna()].mnemonic.str.upper().value_counts().head(25).to_dict(),
        "files_with": {"GR": float(f.has_gr.mean()), "GR+RHOB+NPHI": float(f.has_gr_rhob_nphi.mean()), "core (GR, RHOB, NPHI, DTC, RDEP)": float(f.has_core.mean())},
        "archive_counts": f.archive.value_counts().sort_index().to_dict(),
    }
    gate_kgs = kgs["readable_share"] >= 0.99
    res = {"design": "ADR-002 P0", "force": force, "kgs": kgs, "gate_force": force["gate_force"], "gate_kgs": gate_kgs,
           "gate_passed": bool(force["gate_force"] and gate_kgs)}
    (OUT / "p0_foundation.json").write_text(json.dumps(res, indent=1, default=str))
    # per-well summary for the map: one row per KGS well, best file
    w = f[f.ok & f.lat.notna()].sort_values(["kgs_id", "has_core", "has_gr_rhob_nphi"], ascending=[True, False, False]).drop_duplicates("kgs_id")
    rows = [[round(r.lat, 4), round(r.lon, 4), int(r.has_gr) + int(r.has_gr_rhob_nphi) + int(r.has_core), r.archive] for r in w.itertuples()]
    (OUT / "kgs_wells_summary.json").write_text(json.dumps({"columns": ["lat", "lon", "curve_level", "archive"], "rows": rows}, separators=(",", ":")))
    print({"files": kgs["files"], "readable_share": round(kgs["readable_share"], 4), "recognised": round(kgs["curve_entries_recognised_share"], 3),
           "lithology_curves": round(kgs["curve_entries_lithology_share"], 3), "files_with": {k: round(v, 3) for k, v in kgs["files_with"].items()},
           "wells_on_map": len(rows), "gate": res["gate_passed"]})


if __name__ == "__main__":
    main()
