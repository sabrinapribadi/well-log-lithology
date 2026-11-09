"""Per-file log quality and drift sample (ADR-006), shared by P4 (laptop) and P6 (Databricks). No LightGBM import."""

from __future__ import annotations

import numpy as np
import xgboost as xgb

from src.features import transfer_matrix
from src.kansas import parse_data, read_entry, resample, standardise

RANGES = {"GR": (0, 300), "RHOB": (1.0, 3.2), "NPHI": (-0.15, 1.0), "DTC": (40, 240), "RDEP": (0.01, 100_000)}
DRIFT = ["GR", "RHOB", "NPHI", "DTC", "RDEP", "T_CONF"]
PER_FILE = 2000


def file_quality(zip_path: str, entry: str, kgs_id, archive: str, booster: xgb.Booster) -> dict:
    try:
        raw = read_entry(zip_path, entry)
    except Exception as e:  # noqa: BLE001 — every failure is recorded
        return {"row": {"archive": archive, "entry": entry, "kgs_id": kgs_id, "ok": False, "error": repr(e)[:160]}, "sample": None}
    return las_quality(raw, entry, kgs_id, archive, booster)


def las_quality(raw: bytes, entry: str, kgs_id, archive: str, booster: xgb.Booster) -> dict:
    """ADR-006 measures for one LAS file given as bytes (archive entry or an upload)."""
    row = {"archive": archive, "entry": entry, "kgs_id": kgs_id, "ok": False, "error": ""}
    try:
        h, df = parse_data(raw)
        raw = standardise(h, df)
        w = resample(raw)
    except Exception as e:  # noqa: BLE001 — every failure is recorded
        row["error"] = repr(e)[:160]
        return {"row": row, "sample": None}
    if w.empty:
        row["error"] = "no data rows"
        return {"row": row, "sample": None}
    row["ok"] = True
    row["samples"] = len(w)
    for c in ["GR", "RHOB", "NPHI", "DTC", "RDEP", "PEF", "CALI"]:
        row[f"has_{c}"] = bool(c in w and w[c].notna().any())
    core = [c for c in ("GR", "NPHI", "RHOB") if c in w]
    row["coverage_core3"] = float(w[core].notna().all(axis=1).mean()) if len(core) == 3 else 0.0
    vals, out = 0, 0
    for c, (lo, hi) in RANGES.items():
        if c in w:
            v = w[c].dropna()
            vals += len(v); out += int(((v < lo) | (v > hi)).sum())
    row["out_of_range_share"] = out / vals if vals else None
    if "DRHO" in w and w["DRHO"].notna().any():
        d = w["DRHO"].dropna(); row["bad_hole_share"], row["bad_hole_basis"] = float((d.abs() > 0.15).mean()), "DRHO"
    elif {"CALI", "BS"} <= set(w) and (w["CALI"] - w["BS"]).notna().any():
        d = (w["CALI"] - w["BS"]).dropna(); row["bad_hole_share"], row["bad_hole_basis"] = float((d > 1.0).mean()), "caliper"
    else:
        row["bad_hole_share"], row["bad_hole_basis"] = None, "unknown"
    w["WELL"] = kgs_id
    X = transfer_matrix(w)
    conf = booster.predict(xgb.DMatrix(X)).max(1)
    covered = w.loc[X.index, core].notna().all(axis=1).to_numpy() if len(core) == 3 else np.zeros(len(X), bool)
    row["t_conf_median"] = float(np.median(conf[covered])) if covered.any() else None
    s = w.loc[X.index].assign(T_CONF=conf)
    s["RDEP"] = np.log10(s["RDEP"].clip(lower=1e-3)) if "RDEP" in s else np.nan
    s = s[[c for c in DRIFT if c in s]]
    if len(s) > PER_FILE:
        s = s.iloc[np.sort(np.random.default_rng(42).choice(len(s), PER_FILE, replace=False))]
    return {"row": row, "sample": s.assign(archive=archive).astype({c: "float32" for c in s.columns})}
