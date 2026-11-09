"""Page data for docs/index.html and docs/build.html: every number shown on the pages comes from here.

    python scripts/export_page_data.py

Reads data/outputs/*.json, configs/force2020_finalists.json and the prediction parquets in WLL_DATA_DIR/derived;
writes docs/data/page_data.js (window.PAGE = {...}). Works before P2 finishes (P2 fields are then null).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.scoring import NAMES, A  # noqa: E402

CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
OUT = ROOT / CFG["paths"]["outputs_dir"]
DER = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / CFG["paths"]["derived"]
STEP = 0.152  # metres per sample (reference_floors.json)
GRID = 0.25  # degrees, Kansas map cells


def load(name: str) -> dict | None:
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else None


def runs(depth: np.ndarray, cls: np.ndarray) -> list[list]:
    """Run-length intervals [top, base, class] along depth (metres, 1 decimal)."""
    cut = np.flatnonzero(np.diff(cls)) + 1
    starts = np.r_[0, cut]
    ends = np.r_[cut, len(cls)]
    return [[round(float(depth[s]), 1), round(float(depth[e - 1]) + STEP, 1), int(cls[s])] for s, e in zip(starts, ends)]


def confidence_curve(y: np.ndarray, p: np.ndarray, pmax: np.ndarray) -> list[dict]:
    wrong = y != p
    rows = []
    for t in np.round(np.arange(0.30, 0.96, 0.05), 2):
        flag = pmax < t
        kept = ~flag
        rows.append({"threshold": float(t), "flagged_share": float(flag.mean()),
                     "errors_caught": float((wrong & flag).sum() / max(1, wrong.sum())),
                     "kept_accuracy": float((~wrong[kept]).mean()) if kept.any() else None,
                     "flagged_m": round(float(flag.sum() * STEP))})
    return rows


def costly_confusions(y: np.ndarray, p: np.ndarray, top: int = 6) -> list[dict]:
    cost = A[y, p]
    total = cost.sum()
    df = pd.DataFrame({"y": y, "p": p, "c": cost})[y != p].groupby(["y", "p"]).agg(n=("c", "size"), c=("c", "sum")).reset_index()
    df = df.sort_values("c", ascending=False).head(top)
    return [{"true": NAMES[int(r.y)], "predicted": NAMES[int(r.p)], "metres": round(r.n * STEP), "cost_share": float(r.c / total),
             "penalty_each": float(A[int(r.y), int(r.p)])} for r in df.itertuples()]


def main() -> None:
    p0, p1, p2 = load("p0_foundation.json"), load("p1_baseline.json"), load("p2_model_choice.json")
    floors = load("reference_floors.json")
    fin = json.loads((ROOT / "configs" / "force2020_finalists.json").read_text())
    page: dict = {"updated": time.strftime("%Y-%m-%d"), "classes": NAMES, "penalty_matrix": A.tolist(), "floors": floors,
                  "finalists": fin["finalists"], "finalists_source": fin["source"]}

    # P0
    k = p0["kgs"]
    page["p0"] = {"splits": p0["force"]["splits"], "missing_train": p0["force"]["checks"]["curve_missing_share_train"],
                  "kgs": {x: k[x] for x in ("files", "readable", "readable_share", "wells", "files_direct", "files_in_nested_zips",
                                             "wrapped_files", "null_codes", "located_share", "curve_entries", "curve_entries_recognised_share",
                                             "files_with", "archive_counts")},
                  "unreadable": len(k["unreadable"]), "gate_passed": p0["gate_passed"]}
    page["p0"]["kgs"]["las_version"] = {"2.0": k["las_version"].get("2.0", 0), "1.2": k["las_version"].get("1.2", 0),
                                        "3.0": k["las_version"].get("3.0", 0) + k["las_version"].get("3.00", 0)}

    # Kansas map: wells binned to 0.25° cells; level 0 no GR, 1 GR only, 2 GR+RHOB+NPHI, 3 all five core logs
    kw = json.loads((OUT / "kgs_wells_summary.json").read_text())
    w = pd.DataFrame(kw["rows"], columns=kw["columns"])
    w = w[w.lat.between(36.9, 40.1) & w.lon.between(-102.1, -94.5)]
    w["cy"], w["cx"] = np.floor(w.lat / GRID) * GRID, np.floor(w.lon / GRID) * GRID
    g = w.groupby(["cy", "cx"]).curve_level.agg(n="size", triple=lambda s: (s >= 2).mean(), core=lambda s: (s >= 3).mean()).reset_index()
    page["kgs_grid"] = {"cell_deg": GRID, "wells_mapped": int(len(w)),
                        "cells": [[round(r.cy, 2), round(r.cx, 2), int(r.n), round(r.triple, 3), round(r.core, 3)] for r in g.itertuples()],
                        "levels": {int(a): int(b) for a, b in w.curve_level.value_counts().sort_index().items()}}

    # FORCE well map (positions as provided, km relative to the south-west corner)
    pos = []
    for split in ("train", "open_test", "hidden_test"):
        d = pd.read_parquet(DER / f"force_{split}.parquet", columns=["WELL", "X_LOC", "Y_LOC"])
        m = d.groupby("WELL")[["X_LOC", "Y_LOC"]].median().dropna()
        pos += [[wn, split, float(r.X_LOC), float(r.Y_LOC)] for wn, r in m.iterrows()]
    x0, y0 = min(p[2] for p in pos), min(p[3] for p in pos)
    page["wells"] = [{"well": wn, "split": s, "x_km": round((x - x0) / 1000, 1), "y_km": round((y - y0) / 1000, 1)} for wn, s, x, y in pos]

    # P1
    page["p1"] = {s: {"penalty": p1[s]["penalty_score"], "accuracy": p1[s]["accuracy"], "recall": p1[s]["recall"],
                      "support": p1[s]["support"], "per_well": p1[s]["per_well"]} for s in ("open_test", "hidden_test")}
    page["p1"].update({"random_split": p1["random_split"], "gate": p1["gate_threshold"], "gate_passed": p1["gate_passed"]})

    # P2 (null until it has run)
    page["p2"] = None
    if p2:
        c = p2["chosen"]
        page["p2"] = {"chosen": c, "cv_mean": p2["cv_mean"], "cv_folds": p2["cv_folds"], "gain": p2["gain_vs_p1"],
                      "gate_passed": p2["gate_passed"], "margin": p2["margin"],
                      "candidates": {k2: {s: {"penalty": v[s]["penalty_score"], "accuracy": v[s]["accuracy"]} for s in v}
                                     for k2, v in p2["candidates"].items()},
                      "chosen_detail": {s: {"recall": p2["candidates"][c][s]["recall"], "per_well": p2["candidates"][c][s]["per_well"]}
                                        for s in ("open_test", "hidden_test")}}

    # Lithology columns for the 10 hidden wells: truth, P1, and the P2 choice (if run); confidence what-if; costly confusions
    pr1 = pd.read_parquet(DER / "p1_predictions.parquet")
    pr2 = pd.read_parquet(DER / "p2_predictions.parquet") if (DER / "p2_predictions.parquet").exists() and p2 else None
    best = pr2 if pr2 is not None else pr1
    tracks = {}
    for wn, g1 in pr1[pr1.split == "hidden_test"].sort_values(["WELL", "DEPTH_MD"]).groupby("WELL"):
        dep = g1.DEPTH_MD.to_numpy()
        t = {"top": round(float(dep.min()), 1), "base": round(float(dep.max()), 1), "truth": runs(dep, g1.y.to_numpy()), "p1": runs(dep, g1.p.to_numpy())}
        if pr2 is not None:
            g2 = pr2[(pr2.split == "hidden_test") & (pr2.WELL == wn)].sort_values("DEPTH_MD")
            d2 = g2.DEPTH_MD.to_numpy()
            t["p2"] = runs(d2, g2.p.to_numpy())
            t["low_conf"] = [r[:2] for r in runs(d2, (g2.pmax.to_numpy() < 0.5).astype(int)) if r[2] == 1]
        tracks[wn] = t
    page["tracks"] = tracks
    h = best[best.split == "hidden_test"]
    page["confidence"] = {"model": "P2" if pr2 is not None else "P1", "curve": confidence_curve(h.y.to_numpy(), h.p.to_numpy(), h.pmax.to_numpy())}
    page["confusions"] = {"model": page["confidence"]["model"], "rows": costly_confusions(h.y.to_numpy(), h.p.to_numpy())}

    # P2b method comparison (ADR-009)
    c2, cnn = load("p2b_lightgbm_fair.json"), load("p2b_cnn.json")
    page["p2b"] = None if not (c2 and cnn) else {k: {"cv": v["cv_mean"], "open": v["open_test"]["penalty_score"], "hidden": v["hidden_test"]["penalty_score"],
                                                    "accuracy": v["hidden_test"]["accuracy"]} for k, v in (("C2", c2), ("D", cnn))}
    # P3 Kansas transfer (ADR-005) and its diagnostic
    p3, p3t, p3d = load("p3_kansas_transfer.json"), load("p3_transfer_model.json"), load("p3_diagnostic.json")
    if p3:
        page["p3"] = {"gate_passed": p3["gate_passed"], "units_passed": p3["units_passed"], "units_gated": p3["units_gated"], "files": p3["files"],
                      "units": [{"unit": u, **{k: v[k] for k in ("expected_rock", "gated", "wells_scored", "median_agreement", "lift", "passed")},
                                 "lift": (None if v["lift"] is None or not np.isfinite(v["lift"]) else v["lift"]),
                                 "mix": v["predicted_mix_inside"]} for u, v in p3["units"].items()],
                      "t_hidden": p3t["hidden_test"]["penalty_score"], "t_cost": p3t["cost_vs_b_hidden"],
                      "diag": {"kansas_lkc": p3d["kansas_unit_medians"]["Lansing-Kansas City"], "force_limestone": p3d["force_rock_medians"]["Limestone"],
                               "force_sandstone": p3d["force_rock_medians"]["Sandstone"], "kansas_salt": p3d["kansas_unit_medians"]["Hutchinson Salt"],
                               "force_halite": p3d["force_rock_medians"]["Halite"]}}
    # P4 quality and drift (ADR-006)
    p4 = load("p4_quality.json")
    if p4:
        page["p4"] = {k: p4[k] for k in ("files_readable", "files_processed", "processed_share", "wells", "coverage_core3_median", "out_of_range_median",
                                         "bad_hole_median", "t_conf_median", "gate_passed", "bad_hole_basis", "by_year")}
        page["p4"]["drift"] = [{"archive": d["archive"], "input": d["input"], "earlier": d["psi_vs_earlier"], "force": d["psi_vs_force"]} for d in p4["drift"]]
    # P5 serving (ADR-007) and P6 Databricks (ADR-008)
    p5 = load("p5_notes_eval.json")
    if p5:
        page["p5"] = {k: p5[k] for k in ("cases", "live_draft_pass_rate", "served_grounded_rate", "required_fact_coverage", "cost_per_1000_usd",
                                         "p50_ms_live", "p95_ms_live", "p95_ms_cached", "budgets", "gate_notes")}
        page["p5"]["examples"] = [{"subject": e["subject"], "note": e["note"]} for e in (p5["examples"][1], p5["examples"][4])]
    par, reg, aq, dr, ss = load("p6_parity.json"), load("p6_registry.json"), load("p6_archive_quality.json"), load("p6_drift.json"), load("p6_seed_spread.json")
    if par:
        page["p6"] = {"parity": par, "registry": reg, "archive_quality": aq, "drift": dr["rows"] if dr else None, "seed_spread": ss}

    ev = load("references_evidence.json")
    page["evidence_retrieved"] = ev["retrieved"] if ev else None
    (ROOT / "docs" / "data").mkdir(parents=True, exist_ok=True)
    js = "window.PAGE = " + json.dumps(page, separators=(",", ":")) + ";\n"
    (ROOT / "docs" / "data" / "page_data.js").write_text(js)
    print(f"docs/data/page_data.js {len(js) / 1e3:.0f} kB; P2 {'in' if p2 else 'not yet'}")


if __name__ == "__main__":
    main()
