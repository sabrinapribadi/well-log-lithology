"""P3 step 3: score the selected Kansas wells with model T and test agreement with named units (ADR-005 §3, §6, §7).

    python scripts/p3_kansas_transfer.py [--workers 5] [--limit N]

Reads each selected LAS file once (src/kansas.py rules), predicts lithology with T and the expected-penalty decision,
and measures per unit: agreement (share of interval samples predicted as an acceptable rock; median across wells) and
lift (pooled share inside the intervals ÷ pooled share in the rest of those wells). Writes one LAS 2.0 lithology file
per well to WLL_DATA_DIR/outputs/kansas_las/, data/outputs/p3_kansas_transfer.json and derived/p3_samples.parquet.
`--limit` scores only the first N files (a pipeline check; its numbers are not the P3 result).
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
from src.features import expected_penalty_decision, transfer_matrix  # noqa: E402
from src.kansas import load_well  # noqa: E402
from src.scoring import NAMES, A  # noqa: E402

ZIPS = DATA / CFG["paths"]["kgs_las_zips"]
LAS_OUT = DATA / "outputs" / "kansas_las"
NEAR = 2.0          # ADR-005 §3: acceptable = expected rock or any rock the matrix charges ≤ 2.0 for
MIN_COVER = 0.80    # ADR-005 §4
MIN_WELLS, MIN_AGREE, MIN_LIFT, MIN_UNITS = 30, 0.50, 2.0, 4   # ADR-005 §6
CARBONATE = {"Dolomite", "Limestone", "Chalk"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
_booster = None


def acceptable(rock: str) -> set[int]:
    k = NAMES.index(rock)
    return {j for j in range(len(NAMES)) if A[k][j] <= NEAR}


def write_las(path: Path, well: str, depth_m: np.ndarray, cls: np.ndarray, prob: np.ndarray) -> None:
    from src.scoring import CODES
    code = {v: k for k, v in CODES.items()}
    lines = ["~VERSION INFORMATION", " VERS.   2.0 : CWLS LOG ASCII STANDARD - VERSION 2.0", " WRAP.   NO  : ONE LINE PER DEPTH STEP",
             "~WELL INFORMATION", f" STRT.M  {depth_m[0]:.4f} :", f" STOP.M  {depth_m[-1]:.4f} :", " STEP.M  0.1524 :", " NULL.   -999.25 :",
             f" UWI .   {well} : KGS well ID", " SRVC.   well-log-lithology model T (ADR-005) : predicted, not interpreted",
             "~CURVE INFORMATION", " DEPT.M        : Depth", " LITH.         : Predicted lithology, FORCE 2020 code",
             " LITH_PROB.    : Probability of the most likely class", "~A"]
    body = [f"{d:.4f} {code[int(c)]} {p:.3f}" for d, c, p in zip(depth_m, cls, prob)]
    path.write_text("\n".join(lines + body) + "\n")


def score_file(job: dict) -> dict:
    global _booster
    if _booster is None:
        _booster = xgb.Booster(); _booster.load_model(str(DATA / "models" / "p3_transfer_T.json"))
    try:
        w = load_well(str(ZIPS / f"{job['archive']}.zip"), job["entry"])
    except Exception as e:  # noqa: BLE001 — every failure is recorded
        return {"entry": job["entry"], "error": repr(e)[:160], "units": []}
    if w.empty or "GR" not in w:
        return {"entry": job["entry"], "error": "no usable curves", "units": []}
    w["WELL"] = job["kgs_id"]
    X = transfer_matrix(w)
    proba = _booster.predict(xgb.DMatrix(X))
    cls = expected_penalty_decision(proba)
    w = w.loc[X.index]
    have = w.GR.notna() & w.NPHI.notna() & w.RHOB.notna() if {"NPHI", "RHOB"} <= set(w.columns) else pd.Series(False, index=w.index)
    LAS_OUT.mkdir(parents=True, exist_ok=True)
    write_las(LAS_OUT / f"{job['kgs_id']}.las", job["kgs_id"], w.DEPTH_MD.to_numpy(), cls, proba.max(1))
    out = []
    for u in job["units"]:
        inside = (w.DEPTH_MD >= u["top_m"]) & (w.DEPTH_MD < u["base_m"])
        n_in = int(inside.sum())
        cover = float(have[inside].mean()) if n_in else 0.0
        acc, carb = acceptable(u["rock"]), {NAMES.index(r) for r in CARBONATE}
        ok_in, ok_out = inside & have, ~inside & have
        out.append({"unit": u["unit"], "rock": u["rock"], "gated": u["gated"], "kgs_id": job["kgs_id"], "samples": n_in, "cover": cover,
                    "in_n": int(ok_in.sum()), "in_acc": int(np.isin(cls[ok_in.to_numpy()], list(acc)).sum()),
                    "out_n": int(ok_out.sum()), "out_acc": int(np.isin(cls[ok_out.to_numpy()], list(acc)).sum()),
                    "in_carb": int(np.isin(cls[ok_in.to_numpy()], list(carb)).sum()), "out_carb": int(np.isin(cls[ok_out.to_numpy()], list(carb)).sum()),
                    "pred_mix": {NAMES[int(k)]: int(v) for k, v in zip(*np.unique(cls[ok_in.to_numpy()], return_counts=True))}})
    return {"entry": job["entry"], "error": "", "units": out}


def summarise(rows: pd.DataFrame) -> dict:
    res = {}
    for unit, g in rows.groupby("unit", sort=False):
        s = g[(g.cover >= MIN_COVER) & (g.in_n > 0)]
        agree = (s.in_acc / s.in_n)
        inside, outside = s.in_acc.sum() / max(1, s.in_n.sum()), s.out_acc.sum() / max(1, s.out_n.sum())
        lift = float(inside / outside) if outside > 0 else float("inf")
        mix = pd.DataFrame(list(s.pred_mix)).sum().sort_values(ascending=False) if len(s) else pd.Series(dtype=float)
        r = {"expected_rock": g.rock.iloc[0], "gated": bool(g.gated.iloc[0]), "wells_selected": int(len(g)), "wells_scored": int(len(s)),
             "median_agreement": float(agree.median()) if len(s) else None, "pooled_inside": float(inside), "pooled_outside": float(outside),
             "lift": lift, "predicted_mix_inside": {k: float(v / mix.sum()) for k, v in mix.head(5).items()} if len(mix) else {}}
        if unit == "Arbuckle":
            r["carbonate_family_median_agreement"] = float((s.in_carb / s.in_n).median()) if len(s) else None
        r["passed"] = bool(r["gated"] and r["wells_scored"] >= MIN_WELLS and (r["median_agreement"] or 0) >= MIN_AGREE and lift >= MIN_LIFT)
        res[unit] = r
    return res


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=5); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    t0 = time.time()
    sel = pd.read_parquet(DER / "p3_selection.parquet")
    jobs = [{"entry": e, "archive": g.archive.iloc[0], "kgs_id": g.kgs_id.iloc[0],
             "units": g[["unit", "rock", "gated", "top_m", "base_m"]].to_dict("records")} for e, g in sel.groupby("entry", sort=True)]
    missing = sorted({j["archive"] for j in jobs if not (ZIPS / f"{j['archive']}.zip").exists()})
    if a.limit:
        jobs = jobs[: a.limit]
    log(f"{len(jobs)} files to score; archives not on disk: {missing or 'none'}")
    rows, errors = [], []
    with ProcessPoolExecutor(a.workers) as ex:
        for k, r in enumerate(ex.map(score_file, jobs, chunksize=4), 1):
            rows += r["units"]
            if r["error"]:
                errors.append({"entry": r["entry"], "error": r["error"]})
            if k % 200 == 0:
                log(f"{k}/{len(jobs)} files, {len(errors)} errors")
    df = pd.DataFrame(rows)
    df.drop(columns=["pred_mix"]).to_parquet(DER / ("p3_samples_check.parquet" if a.limit else "p3_samples.parquet"), index=False)
    units = summarise(df)
    gated = [u for u in units.values() if u["gated"]]
    res = {"design": "ADR-005", "check_run": bool(a.limit), "files": len(jobs), "errors": len(errors), "error_examples": errors[:20],
           "units": units, "units_passed": int(sum(u["passed"] for u in gated)), "units_gated": len(gated),
           "seconds": round(time.time() - t0)}
    res["gate_passed"] = bool(res["units_passed"] >= MIN_UNITS)
    name = "p3_kansas_transfer_check.json" if a.limit else "p3_kansas_transfer.json"
    (ROOT / CFG["paths"]["outputs_dir"] / name).write_text(json.dumps(res, indent=1))
    log(f"{res['units_passed']}/{res['units_gated']} units passed → {'PASS' if res['gate_passed'] else 'FAIL'}" + (" (check run, not the result)" if a.limit else ""))


if __name__ == "__main__":
    main()
