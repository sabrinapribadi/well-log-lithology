"""P3b step 1: model-free diagnostics of the P3 development intervals (ADR-013 §2). No model is loaded or read here.

    python scripts/p3b_diagnostics.py [--workers 8] [--limit N]

For every (unit, well) the P3 selection scored (the 1,915 development files), re-reads the LAS file with the P3 rules
(src/kansas.py) and records, inside the unit's interval: where density came from (measured RHOB or converted from density
porosity), median logs, the share of samples that read like halite (RHOB < 2.20), anhydrite (RHOB > 2.85), hot shale
(GR > 100 API), washed-out hole (caliper − bit size > 1.5 in) and a doubtful density correction (DRHO > 0.15 g/cc), and
the apparent matrix density RHOmaa from the neutron-density crossplot porosity (limestone units, fresh fluid 1.0 g/cc).
Writes data/outputs/p3b_diagnostics.json (per-unit summary) and WLL_DATA_DIR/derived/p3b_diagnostics.parquet (per well).
These numbers inform the gate amendments in ADR-013 before any model is evaluated on the development set.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p2_model_choice import CFG, DATA, DER  # noqa: E402
from src.curves import standard_name  # noqa: E402
from src.kansas import parse_data, plausible_density, read_entry, resample, standardise  # noqa: E402

ZIPS = DATA / CFG["paths"]["kgs_las_zips"]
HALITE, ANHYDRITE, HOT_GR, WASHOUT_IN, DRHO_MAX = 2.20, 2.85, 100.0, 1.5, 0.15
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def rhomaa(rhob: np.ndarray, nphi: np.ndarray) -> np.ndarray:
    """Apparent matrix density: crossplot porosity from limestone-unit neutron and density porosity, fluid 1.0 g/cc."""
    dphi = (2.71 - rhob) / 1.71
    phi = np.clip((nphi + dphi) / 2, 0.0, 0.45)
    return (rhob - phi * 1.0) / (1 - phi)


def share(mask: np.ndarray, valid: np.ndarray) -> float | None:
    n = int(valid.sum())
    return round(float((mask & valid).sum() / n), 4) if n else None


def med(v: np.ndarray) -> float | None:
    v = v[np.isfinite(v)]
    return round(float(np.median(v)), 4) if len(v) else None


def diagnose_file(job: dict) -> list[dict]:
    try:
        h, raw = parse_data(read_entry(str(ZIPS / f"{job['archive']}.zip"), job["entry"]))
        names = {standard_name(c["mnemonic"], c.get("description")) for c in h["curves"][1:]}
        real_rhob = any(standard_name(c["mnemonic"], c.get("description")) == "RHOB" and plausible_density(raw[col])
                        for col, c in zip(raw.columns[1:], h["curves"][1:]))
        w = resample(standardise(h, raw))
    except Exception as e:  # noqa: BLE001 - a bad file is recorded, not fatal
        return [{**r, "error": f"{type(e).__name__}: {e}"[:200]} for r in job["rows"]]
    out = []
    for r in job["rows"]:
        iv = w[(w.DEPTH_MD >= r["top_m"]) & (w.DEPTH_MD < r["base_m"])]
        col = lambda c: iv[c].to_numpy(dtype=float) if c in iv else np.full(len(iv), np.nan)  # noqa: E731
        rho, nphi, gr, cali, bs, drho = col("RHOB"), col("NPHI"), col("GR"), col("CALI"), col("BS"), col("DRHO")
        vr, vg = np.isfinite(rho), np.isfinite(gr)
        vc = np.isfinite(cali) & np.isfinite(bs)
        rm = rhomaa(rho, nphi)
        out.append({**r, "error": None, "samples": int(len(iv)),
                    "density_source": "RHOB" if real_rhob else ("DPHI" if "DPHI" in names else "none"),
                    "has_pef": bool(np.isfinite(col("PEF")).any()), "has_caliper_and_bit": bool(vc.any()),
                    "has_drho": bool(np.isfinite(drho).any()),
                    "gr": med(gr), "rhob": med(rho), "nphi": med(nphi), "pef": med(col("PEF")), "dtc": med(col("DTC")),
                    "rdep": med(col("RDEP")), "rhomaa": med(rm),
                    "halite_like": share(rho < HALITE, vr), "anhydrite_like": share(rho > ANHYDRITE, vr),
                    "hot_shale": share(gr > HOT_GR, vg), "washout": share((cali - bs) > WASHOUT_IN, vc),
                    "drho_bad": share(np.abs(drho) > DRHO_MAX, np.isfinite(drho))})
    return out


def summarise(d: pd.DataFrame) -> dict:
    ok = d[d.error.isna() & (d.samples > 0)]
    units = {}
    for unit, g in ok.groupby("unit"):
        q = lambda c: g[c].dropna()  # noqa: E731
        units[unit] = {
            "expected_rock": g.rock.iloc[0], "gated": bool(g.gated.iloc[0]), "wells": int(len(g)),
            "density_from_dphi_share": round(float((g.density_source == "DPHI").mean()), 3),
            "pef_share": round(float(g.has_pef.mean()), 3), "caliper_and_bit_share": round(float(g.has_caliper_and_bit.mean()), 3),
            "median": {c: (round(float(q(c).median()), 3) if len(q(c)) else None) for c in ["gr", "rhob", "nphi", "pef", "dtc", "rdep", "rhomaa"]},
            "median_by_density_source": {s: (round(float(x.rhob.dropna().median()), 3) if x.rhob.notna().any() else None)
                                         for s, x in g.groupby("density_source")},
            "share_wells_mostly": {k: round(float((q(k) >= 0.5).mean()), 3) if len(q(k)) else None
                                   for k in ["halite_like", "anhydrite_like", "hot_shale", "washout", "drho_bad"]},
            "median_share": {k: (round(float(q(k).median()), 3) if len(q(k)) else None)
                             for k in ["halite_like", "anhydrite_like", "hot_shale", "washout", "drho_bad"]},
        }
    return {"design": "ADR-013 §2 (model-free; no prediction read)", "rows": int(len(d)), "errors": int(d.error.notna().sum()),
            "thresholds": {"halite_rhob_below": HALITE, "anhydrite_rhob_above": ANHYDRITE, "hot_shale_gr_above": HOT_GR,
                           "washout_in": WASHOUT_IN, "drho_abs_above": DRHO_MAX}, "units": units}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    sel = pd.read_parquet(DER / "p3_selection.parquet")
    jobs = [{"archive": k[0], "entry": k[1], "rows": g[["unit", "rock", "gated", "kgs_id", "top_m", "base_m"]].to_dict("records")}
            for k, g in sel.groupby(["archive", "entry"])]
    if a.limit:
        jobs = jobs[: a.limit]
    log(f"{len(jobs)} files, {len(sel)} unit intervals")
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(diagnose_file, jobs, chunksize=8), 1):
            rows.extend(r)
            if i % 250 == 0:
                log(i, "files")
    d = pd.DataFrame(rows)
    d.to_parquet(DER / "p3b_diagnostics.parquet", index=False)
    out = summarise(d)
    if not a.limit:
        (ROOT / CFG["paths"]["outputs_dir"] / "p3b_diagnostics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
