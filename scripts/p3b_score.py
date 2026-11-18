"""P3b/P3c step 4: score the arms (ADR-013 §5, ADR-014 §2) on a set of Kansas wells under the original and amended gate.

    python scripts/p3b_score.py --set dev [--m1 M1b] [--workers 8] [--limit N]
    python scripts/p3b_score.py --set test --m1 <frozen variant>     # once, after the variant is frozen (ADR-013)
    python scripts/p3b_score.py --set p3c --m1 M1a                   # once, after ADR-014 is pushed
    python scripts/p3b_score.py --set test --m1 M1a --tag posthoc    # informational rerun; never overwrites a result

dev = the P3 selection (1,915 development files); test = the P3b fresh manifest; p3c = the P3c fresh manifest
(scripts/p3b_select_fresh.py; each SHA-256 is checked against its ADR before anything is read). Arms: C (P3 model T),
M0 (physics rules), M1a, M1b, M3 (ADR-014: M1a whose sandstone calls become the physics rules' limestone or dolomite
where they say so), and M2 (the chosen M1 with priors re-estimated by EM on a systematic 1-in-10 sample of all valid
samples in the scored wells; implementation choice, logged). All arms read logs with the fixed reader (ADR-013 §1).

Original gate: samples with GR, NPHI and RHOB; agreement per well over intervals with ≥ 80% such samples; lift = pooled
inside ÷ pooled rest of the well. Amended gate: the same samples minus |DRHO| > 0.15 g/cc; lift = pooled inside ÷ pooled
within 30 m above and below the interval (interval excluded). Thresholds: 30 wells, median 50%, lift 2, 4 of 6 units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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
from scripts.p3_kansas_transfer import MIN_AGREE, MIN_COVER, MIN_LIFT, MIN_UNITS, MIN_WELLS, ZIPS, acceptable  # noqa: E402
from scripts.p3b_train import m1_matrix  # noqa: E402
from src.features import expected_penalty_decision, transfer_matrix  # noqa: E402
from src.kansas import load_well  # noqa: E402
from src.physics import m0_classify  # noqa: E402
from src.scoring import NAMES  # noqa: E402

MANIFEST_SHA = "19165ba97993699cd3beeb8b2fccf7552069f0352e6c8726c59ec681a14572aa"   # ADR-013 §4
P3C_SHA = "1ced56de9a82d5f98d406e49411c3b70bb2787bb6a74a7c28aa27820de0f8db9"        # ADR-014 §3
SETS = {"dev": ("p3_selection.parquet", None, "ADR-013", "p3b_dev"),
        "test": ("p3b_test_selection.parquet", MANIFEST_SHA, "ADR-013", "p3b_test"),
        "p3c": ("p3c_test_selection.parquet", P3C_SHA, "ADR-014", "p3c_test")}
CONTEXT_M, DRHO_MAX = 30.0, 0.15
ARMS = ["C", "M0", "M1a", "M1b", "M3"]
SAND, CARB = NAMES.index("Sandstone"), [NAMES.index("Limestone"), NAMES.index("Dolomite")]
TMP = DER / "p3b_tmp"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731
_models: dict = {}


def model(name: str) -> xgb.Booster:
    if name not in _models:
        b = xgb.Booster()
        b.load_model(str(DATA / "models" / ("p3_transfer_T.json" if name == "C" else f"p3b_{name}.json")))
        _models[name] = b
    return _models[name]


def counts(cls: np.ndarray, depth: np.ndarray, have_o: np.ndarray, have_a: np.ndarray, u: dict) -> dict:
    inside = (depth >= u["top_m"]) & (depth < u["base_m"])
    ctx = ~inside & (depth >= u["top_m"] - CONTEXT_M) & (depth < u["base_m"] + CONTEXT_M)
    ok = np.isin(cls, list(acceptable(u["rock"])))
    n_in = int(inside.sum())
    return {"samples": n_in, "cover": float(have_o[inside].mean()) if n_in else 0.0,
            "in_n": int((inside & have_o).sum()), "in_acc": int((inside & have_o & ok).sum()),
            "out_n": int((~inside & have_o).sum()), "out_acc": int((~inside & have_o & ok).sum()),
            "in_n_a": int((inside & have_a).sum()), "in_acc_a": int((inside & have_a & ok).sum()),
            "ctx_n_a": int((ctx & have_a).sum()), "ctx_acc_a": int((ctx & have_a & ok).sum())}


def score_file(job: dict) -> dict:
    try:
        w = load_well(str(ZIPS / f"{job['archive']}.zip"), job["entry"])
    except Exception as e:  # noqa: BLE001 - every failure is recorded
        return {"entry": job["entry"], "error": repr(e)[:160], "rows": [], "em": None}
    if w.empty or "GR" not in w:
        return {"entry": job["entry"], "error": "no usable curves", "rows": [], "em": None}
    w["WELL"] = job["kgs_id"]
    w = w.sort_values("DEPTH_MD").reset_index(drop=True)
    have_o = (w.GR.notna() & w.NPHI.notna() & w.RHOB.notna()).to_numpy() if {"NPHI", "RHOB"} <= set(w) else np.zeros(len(w), bool)
    drho_ok = (w.DRHO.abs() <= DRHO_MAX) | w.DRHO.isna() if "DRHO" in w else pd.Series(True, index=w.index)
    have_a = have_o & drho_ok.to_numpy()
    depth = w.DEPTH_MD.to_numpy()
    cls, proba = {}, {}
    cls["C"] = expected_penalty_decision(model("C").predict(xgb.DMatrix(transfer_matrix(w))))
    cls["M0"] = m0_classify(w)
    for v in ("M1a", "M1b"):
        proba[v] = model(v).predict(xgb.DMatrix(m1_matrix(w, v)))
        cls[v] = expected_penalty_decision(proba[v])
    # M3 (ADR-014): the frozen M1a, except where it calls sandstone and the physics rules call limestone or dolomite
    cls["M3"] = np.where((cls["M1a"] == SAND) & np.isin(cls["M0"], CARB), cls["M0"], cls["M1a"])
    np.savez_compressed(TMP / f"{job['kgs_id']}_{Path(job['entry']).stem}.npz", depth=depth, have_o=have_o, have_a=have_a,
                        **{f"p_{v}": proba[v].astype("float16") for v in proba})
    rows = [{"arm": a, "unit": u["unit"], "rock": u["rock"], "gated": u["gated"], "kgs_id": job["kgs_id"],
             **counts(cls[a], depth, have_o, have_a, u)} for a in ARMS for u in job["units"]]
    sub = np.flatnonzero(have_o)[::10]                                     # systematic 1-in-10 sample for EM
    return {"entry": job["entry"], "error": "", "rows": rows, "em": {v: proba[v][sub].astype("float32") for v in proba}}


def em_priors(p: np.ndarray, train: np.ndarray, iters: int = 200, tol: float = 1e-8) -> np.ndarray:
    """Saerens et al. (2002): re-estimate class priors on unlabelled data from calibrated probabilities."""
    pri = train.copy()
    for _ in range(iters):
        q = p * (pri / np.where(train > 0, train, 1))[None, :]
        q /= q.sum(1, keepdims=True)
        new = q.mean(0)
        if np.abs(new - pri).max() < tol:
            return new
        pri = new
    return pri


def summarise(rows: pd.DataFrame) -> dict:
    out = {}
    for arm, ga in rows.groupby("arm", sort=False):
        units = {}
        for unit, g in ga.groupby("unit", sort=False):
            s = g[(g.cover >= MIN_COVER) & (g.in_n > 0)]
            sa = g[(g.cover >= MIN_COVER) & (g.in_n_a > 0)]
            ins, outs = s.in_acc.sum() / max(1, s.in_n.sum()), s.out_acc.sum() / max(1, s.out_n.sum())
            ins_a, ctx_a = sa.in_acc_a.sum() / max(1, sa.in_n_a.sum()), sa.ctx_acc_a.sum() / max(1, sa.ctx_n_a.sum())
            o = {"wells": int(len(s)), "median_agreement": float((s.in_acc / s.in_n).median()) if len(s) else None,
                 "lift": float(ins / outs) if outs > 0 else (float("inf") if ins > 0 else None)}
            a = {"wells": int(len(sa)), "median_agreement": float((sa.in_acc_a / sa.in_n_a).median()) if len(sa) else None,
                 "lift": float(ins_a / ctx_a) if ctx_a > 0 else (float("inf") if ins_a > 0 else None)}
            gated = bool(g.gated.iloc[0])
            for r in (o, a):
                r["passed"] = bool(gated and r["wells"] >= MIN_WELLS and (r["median_agreement"] or 0) >= MIN_AGREE and (r["lift"] or 0) >= MIN_LIFT)
            units[unit] = {"expected_rock": g.rock.iloc[0], "gated": gated, "original": o, "amended": a}
        n_o = sum(u["original"]["passed"] for u in units.values())
        n_a = sum(u["amended"]["passed"] for u in units.values())
        out[arm] = {"units": units, "passed_original": int(n_o), "passed_amended": int(n_a),
                    "gate_original": bool(n_o >= MIN_UNITS), "gate_amended": bool(n_a >= MIN_UNITS)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=list(SETS), required=True)
    ap.add_argument("--m1", choices=["M1a", "M1b"], default="M1b", help="variant used by M2")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default="", help="suffix for an informational rerun, e.g. posthoc")
    a = ap.parse_args()
    t0 = time.time()
    path, sha, design, stem = SETS[a.set]
    sel = pd.read_parquet(DER / path)
    if sha:
        sel = sel.sort_values(["unit", "kgs_id"]).reset_index(drop=True)
        listing = "\n".join(f"{r.unit}\t{r.kgs_id}\t{r.entry}" for r in sel.itertuples())
        assert hashlib.sha256(listing.encode()).hexdigest() == sha, "test set differs from the pre-registered manifest"
    suffix = ("_check" if a.limit else "") + (f"_{a.tag}" if a.tag else "")
    jobs = [{"entry": e, "archive": g.archive.iloc[0], "kgs_id": g.kgs_id.iloc[0],
             "units": g[["unit", "rock", "gated", "top_m", "base_m"]].to_dict("records")} for e, g in sel.groupby("entry", sort=True)]
    if a.limit:
        jobs = jobs[: a.limit]
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    log(f"{a.set}: {len(jobs)} files")
    rows, errors, em = [], [], {"M1a": [], "M1b": []}
    with ProcessPoolExecutor(a.workers) as ex:
        for k, r in enumerate(ex.map(score_file, jobs, chunksize=4), 1):
            rows += r["rows"]
            if r["error"]:
                errors.append({"entry": r["entry"], "error": r["error"]})
            elif r["em"]:
                for v in em:
                    em[v].append(r["em"][v])
            if k % 200 == 0:
                log(f"{k}/{len(jobs)} files, {len(errors)} errors")
    train = np.array(list(json.loads((ROOT / CFG["paths"]["outputs_dir"] / "p3b_models.json").read_text())["training_priors"].values()))
    pri = em_priors(np.concatenate(em[a.m1]), train)
    ratio = pri / np.where(train > 0, train, 1)
    units_by_entry = {j["kgs_id"]: j["units"] for j in jobs}
    for f in sorted(TMP.glob("*.npz")):
        z = np.load(f)
        p = z[f"p_{a.m1}"].astype("float32") * ratio[None, :]
        p /= p.sum(1, keepdims=True)
        c = expected_penalty_decision(p)
        kgs = f.stem.split("_")[0]
        rows += [{"arm": "M2", "unit": u["unit"], "rock": u["rock"], "gated": u["gated"], "kgs_id": kgs,
                  **counts(c, z["depth"], z["have_o"], z["have_a"], u)} for u in units_by_entry[kgs]]
    shutil.rmtree(TMP, ignore_errors=True)
    df = pd.DataFrame(rows)
    df.to_parquet(DER / f"{stem}_rows{suffix}.parquet", index=False)
    res = {"design": design, "set": a.set, "tag": a.tag or None, "check_run": bool(a.limit), "files": len(jobs), "errors": len(errors),
           "error_examples": errors[:10], "m2_uses": a.m1, "m2_priors": {n: round(float(x), 4) for n, x in zip(NAMES, pri)},
           "arms": summarise(df), "seconds": round(time.time() - t0)}
    name = f"{stem}{suffix}.json"
    (ROOT / CFG["paths"]["outputs_dir"] / name).write_text(json.dumps(res, indent=1))
    for arm, r in res["arms"].items():
        log(f"{arm}: original {r['passed_original']}/6, amended {r['passed_amended']}/6")


if __name__ == "__main__":
    main()
