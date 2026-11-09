"""P4: log quality per Kansas file and drift by archive year (ADR-006).

    python scripts/p4_quality.py [--workers 5]

Streams every readable LAS file once (ADR-005 §5 reading rules): curve availability, data coverage, out-of-range share,
bad-hole share, and model T's median confidence; keeps up to 2,000 random depth samples per file (seed 42) for drift.
Drift: PSI of each archive year against all earlier years pooled, and against the FORCE training wells, on 10 quantile
bins of the reference. Writes derived/p4_file_quality.parquet, derived/p4_drift_sample.parquet,
data/outputs/p4_quality.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.drift import psi  # noqa: E402
from src.features import transfer_matrix  # noqa: E402
from src.kansas import parse_data, read_entry, resample, standardise  # noqa: E402

ZIPS = DATA / CFG["paths"]["kgs_las_zips"]
RANGES = {"GR": (0, 300), "RHOB": (1.0, 3.2), "NPHI": (-0.15, 1.0), "DTC": (40, 240), "RDEP": (0.01, 100_000)}
DRIFT = ["GR", "RHOB", "NPHI", "DTC", "RDEP", "T_CONF"]
PER_FILE, BINS, WATCH, ALERT = 2000, 10, 0.10, 0.25
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
_booster = None




def one_file(job: dict) -> dict:
    global _booster
    if _booster is None:
        _booster = xgb.Booster(); _booster.load_model(str(DATA / "models" / "p3_transfer_T.json"))
    row = {"archive": job["archive"], "entry": job["entry"], "kgs_id": job["kgs_id"], "ok": False, "error": ""}
    try:
        h, df = parse_data(read_entry(str(ZIPS / f"{job['archive']}.zip"), job["entry"]))
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
    w["WELL"] = job["kgs_id"]
    X = transfer_matrix(w)
    conf = _booster.predict(xgb.DMatrix(X)).max(1)
    covered = w.loc[X.index, core].notna().all(axis=1).to_numpy() if len(core) == 3 else np.zeros(len(X), bool)
    row["t_conf_median"] = float(np.median(conf[covered])) if covered.any() else None
    s = w.loc[X.index].assign(T_CONF=conf)
    s["RDEP"] = np.log10(s["RDEP"].clip(lower=1e-3)) if "RDEP" in s else np.nan
    s = s[[c for c in DRIFT if c in s]]
    if len(s) > PER_FILE:
        s = s.iloc[np.sort(np.random.default_rng(42).choice(len(s), PER_FILE, replace=False))]
    return {"row": row, "sample": s.assign(archive=job["archive"]).astype({c: "float32" for c in s.columns})}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=5); a = ap.parse_args()
    t0 = time.time()
    f = pd.read_parquet(DER / "kgs_files.parquet")
    jobs = f[f.ok][["archive", "entry", "kgs_id"]].to_dict("records")
    log(f"{len(jobs):,} readable files")
    rows, samples = [], []
    with ProcessPoolExecutor(a.workers) as ex:
        for k, r in enumerate(ex.map(one_file, jobs, chunksize=8), 1):
            rows.append(r["row"])
            if r["sample"] is not None:
                samples.append(r["sample"])
            if k % 2000 == 0:
                log(f"{k:,}/{len(jobs):,} files, {sum(not x['ok'] for x in rows):,} failed")
    q = pd.DataFrame(rows); q.to_parquet(DER / "p4_file_quality.parquet", index=False)
    ds = pd.concat(samples, ignore_index=True); ds.to_parquet(DER / "p4_drift_sample.parquet", index=False)
    # FORCE reference: up to 2,000 samples per training well, same inputs (T confidence from the same model)
    tr = pd.read_parquet(DER / "force_train.parquet").sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    Xf = transfer_matrix(tr)
    bst = xgb.Booster(); bst.load_model(str(DATA / "models" / "p3_transfer_T.json"))
    fr = tr.loc[Xf.index, ["WELL", "GR", "RHOB", "NPHI", "DTC", "RDEP"]].assign(T_CONF=bst.predict(xgb.DMatrix(Xf)).max(1))
    fr["RDEP"] = np.log10(fr["RDEP"].clip(lower=1e-3))
    fr = fr.groupby("WELL", group_keys=False).apply(lambda g: g.sample(min(len(g), PER_FILE), random_state=42))
    years = sorted(ds.archive.unique())
    drift = []
    for i, y in enumerate(years):
        new = ds[ds.archive == y]
        for c in DRIFT:
            prior = psi(ds[ds.archive.isin(years[:i])][c].to_numpy(), new[c].to_numpy()) if i else None
            drift.append({"archive": y, "input": c, "psi_vs_earlier": prior, "psi_vs_force": psi(fr[c].to_numpy(), new[c].to_numpy())})
    dr = pd.DataFrame(drift)
    ok = q[q.ok]
    band = lambda v: None if v is None or not np.isfinite(v) else ("alert" if v > ALERT else "watch" if v > WATCH else "stable")
    res = {"design": "ADR-006", "files_readable": len(jobs), "files_processed": int(len(ok)), "processed_share": len(ok) / len(jobs),
           "failures": q[~q.ok].error.value_counts().head(10).to_dict(), "wells": int(ok.kgs_id.nunique()),
           "coverage_core3_median": float(ok.coverage_core3.median()), "out_of_range_median": float(ok.out_of_range_share.median()),
           "bad_hole_basis": ok.bad_hole_basis.value_counts().to_dict(),
           "bad_hole_median": float(ok.bad_hole_share.dropna().median()) if ok.bad_hole_share.notna().any() else None,
           "t_conf_median": float(ok.t_conf_median.dropna().median()),
           "by_year": ok.groupby("archive").agg(files=("entry", "size"), coverage=("coverage_core3", "median"), out_of_range=("out_of_range_share", "median"),
                                                t_conf=("t_conf_median", "median")).round(4).reset_index().to_dict("records"),
           "drift": [{**r, "band_vs_earlier": band(r["psi_vs_earlier"]), "band_vs_force": band(r["psi_vs_force"])} for r in dr.to_dict("records")],
           "years": years, "seconds": round(time.time() - t0)}
    has = lambda y, col: dr[dr.archive == y][col].notna().any()
    res["drift_every_year"] = bool(all(has(y, "psi_vs_force") for y in years) and all(has(y, "psi_vs_earlier") for y in years[1:]))
    res["gate_passed"] = bool(res["processed_share"] >= 0.99 and res["drift_every_year"])
    (ROOT / CFG["paths"]["outputs_dir"] / "p4_quality.json").write_text(json.dumps(res, indent=1, default=float))
    log(f"processed {res['processed_share']:.2%}; drift every year {res['drift_every_year']} → {'PASS' if res['gate_passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
