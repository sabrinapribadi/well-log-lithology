"""Read one Kansas LAS file into FORCE-style curves (ADR-005 §5). Rules fixed before any Kansas data was read.

- Null codes and values ≤ −999 → missing.
- One curve per standard name: the matching curve with the most valid values.
- Units: neutron in percent (median > 1.5) → fraction; density in kg/m³ (median > 100) → g/cm³; sonic in µs/m
  (median > 300) → µs/ft; deep conductivity (mmho/m) → resistivity 1000 / C when no deep resistivity exists.
- Density from density porosity when only DPHI exists: RHOB = 2.71 − 1.71 × DPHI (limestone matrix, fresh fluid).
- Depth in feet → metres; resampled to a 0.1524 m grid by linear interpolation, never bridging gaps over 0.3 m.
"""

from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd

from src.curves import standard_name
from src.las_header import parse_header

FT, STEP_M, MAX_GAP_M = 0.3048, 0.1524, 0.3
WANT = ["GR", "RHOB", "NPHI", "DTC", "RDEP", "RMED", "RSHA", "PEF", "CALI", "BS", "SP", "DRHO", "DPHI", "COND_DEEP"]


def read_entry(zip_path: str, entry: str) -> bytes:
    """LAS bytes for an inventory entry such as '2014/1044753445.zip/1044753445.las' or '2013/1043.las'."""
    outer = zipfile.ZipFile(zip_path)
    if ".zip/" in entry:
        inner_name, las_name = entry.split(".zip/", 1)
        inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_name + ".zip")))
        names = [n for n in inner.namelist() if n.lower().endswith(".las")]
        return inner.read(las_name if las_name in names else names[0])
    return outer.read(entry)


def parse_data(raw: bytes) -> tuple[dict, pd.DataFrame]:
    """Header plus the ~A block as a numeric table (wrapped files are reshaped by curve count)."""
    h = parse_header(raw)
    i = raw.find(b"\n~A")
    body = raw[raw.index(b"\n", i + 1) + 1:] if i >= 0 else b""
    vals = pd.to_numeric(pd.Series(body.split()), errors="coerce").to_numpy(dtype="float64")
    n = len(h["curves"])
    vals = vals[: (len(vals) // n) * n].reshape(-1, n) if n else np.empty((0, 0))
    names = [f"{c['mnemonic']}#{k}" for k, c in enumerate(h["curves"])]
    df = pd.DataFrame(vals, columns=names)
    null = h.get("null")
    if null is not None:
        df = df.mask(np.isclose(df, null))
    return h, df.mask(df <= -999)


def standardise(h: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Depth (m) plus one column per standard curve, with ADR-005 unit rules applied."""
    if df.empty:
        return pd.DataFrame()
    depth = df.iloc[:, 0].to_numpy()
    if not str(h.get("depth_unit") or "FT").upper().startswith("M"):
        depth = depth * FT
    out = pd.DataFrame({"DEPTH_MD": depth})
    best: dict[str, pd.Series] = {}
    for col, c in zip(df.columns[1:], h["curves"][1:]):
        s = standard_name(c["mnemonic"])
        if s in WANT and (s not in best or df[col].notna().sum() > best[s].notna().sum()):
            best[s] = df[col]
    for s, v in best.items():
        out[s] = v.to_numpy()
    med = lambda s: float(np.nanmedian(out[s])) if s in out and out[s].notna().any() else np.nan
    if med("NPHI") > 1.5:
        out["NPHI"] = out["NPHI"] / 100
    if med("DPHI") > 1.5:
        out["DPHI"] = out["DPHI"] / 100
    if med("RHOB") > 100:
        out["RHOB"] = out["RHOB"] / 1000
    if med("DTC") > 300:
        out["DTC"] = out["DTC"] / 3.281
    if "RHOB" not in out and "DPHI" in out:
        out["RHOB"] = 2.71 - 1.71 * out["DPHI"]
    if "RDEP" not in out and "COND_DEEP" in out:
        out["RDEP"] = 1000.0 / out["COND_DEEP"].where(out["COND_DEEP"] > 0)
    return out.drop(columns=[c for c in ("DPHI", "COND_DEEP") if c in out]).dropna(subset=["DEPTH_MD"]).sort_values("DEPTH_MD")


def resample(df: pd.DataFrame) -> pd.DataFrame:
    """Linear interpolation onto a 0.1524 m grid; never across a gap between valid samples wider than 0.3 m."""
    if df.empty:
        return df
    d = df.DEPTH_MD.to_numpy()
    grid = np.arange(np.ceil(d.min() / STEP_M) * STEP_M, d.max() + 1e-9, STEP_M)
    out = {"DEPTH_MD": np.round(grid, 4)}
    for c in df.columns.drop("DEPTH_MD"):
        ok = df[c].notna().to_numpy()
        if ok.sum() < 2:
            out[c] = np.full(len(grid), np.nan)
            continue
        dv, vv = d[ok], df[c].to_numpy()[ok]
        v = np.interp(grid, dv, vv)
        j = np.clip(np.searchsorted(dv, grid), 1, len(dv) - 1)
        on_sample = np.minimum(np.abs(grid - dv[j - 1]), np.abs(dv[j] - grid)) < 1e-6
        wide_gap = (dv[j] - dv[j - 1]) > MAX_GAP_M          # never interpolate across a gap wider than 0.3 m
        v[(wide_gap & ~on_sample) | (grid < dv[0]) | (grid > dv[-1])] = np.nan
        out[c] = v
    return pd.DataFrame(out)


def load_well(zip_path: str, entry: str) -> pd.DataFrame:
    h, df = parse_data(read_entry(zip_path, entry))
    return resample(standardise(h, df))
