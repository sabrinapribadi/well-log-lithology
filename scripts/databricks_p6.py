"""P6 Databricks job tasks (ADR-008). Run by the bundle (databricks.yml), one task per call:

    databricks_p6.py --task parity_b|register|quality_archive|monitor_drift

Uses the same src/ code as the laptop. Inputs are uploaded to the Unity Catalog volume workspace.og2.inputs
(scripts/databricks_prepare_inputs.sh); results go to workspace.og2.* tables and the outputs volume.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _repo_root() -> Path:  # Databricks runs job scripts through exec(), without __file__
    for c in (globals().get("__file__"), sys.argv[0] if sys.argv else None, os.path.join(os.getcwd(), "_")):
        if c and (Path(c).resolve().parents[1] / "src" / "features.py").exists():
            return Path(c).resolve().parents[1]
    raise RuntimeError("repo root not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402

from scripts.p1_baseline import PARAMS  # noqa: E402
from src.features import engineered_matrix, expected_penalty_decision, full_proba, labels, strat_codes, transfer_matrix  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

CAT, SCHEMA = "workspace", "og2"
IN, OUT = Path(f"/Volumes/{CAT}/{SCHEMA}/inputs"), Path(f"/Volumes/{CAT}/{SCHEMA}/outputs")
LOCAL_B_HIDDEN = -0.5040   # data/outputs/p2_model_choice.json, rounded as reported
NEW = "2026"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def _spark():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


def _save(name: str, res: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(res, indent=1, default=float))
    _spark().createDataFrame([(json.dumps(res, default=float), time.strftime("%Y-%m-%d %H:%M:%S"))], "result string, at string") \
        .write.mode("append").saveAsTable(f"{CAT}.{SCHEMA}.{name}")


def parity_b() -> None:
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, hd = sort(pd.read_parquet(IN / "force_train.parquet")), sort(pd.read_parquet(IN / "force_hidden_test.parquet"))
    codes = strat_codes(tr)
    t0 = time.time()
    model = xgb.XGBClassifier(**PARAMS).fit(engineered_matrix(tr, codes), labels(tr))
    log(f"B fitted in {time.time() - t0:.0f} s")
    Xhd = engineered_matrix(hd, codes)
    OUT.mkdir(parents=True, exist_ok=True)
    Xhd.reset_index(drop=True).to_parquet(OUT / "parity_features_hidden.parquet")      # compared value by value with the laptop's
    p = expected_penalty_decision(full_proba(model, Xhd))
    score = penalty_score(labels(hd), p)
    loc = pd.read_parquet(IN / "p2_predictions.parquet").query("split == 'hidden_test'")[["WELL", "DEPTH_MD", "p"]]
    m = hd[["WELL", "DEPTH_MD"]].assign(p_db=p).merge(loc, on=["WELL", "DEPTH_MD"], how="inner")
    OUT.mkdir(parents=True, exist_ok=True)
    model.save_model(str(OUT / "lithology_b.json"))
    res = {"design": "ADR-008 parity_b", "hidden_score_databricks": score, "hidden_score_local": LOCAL_B_HIDDEN,
           "equal_to_3_decimals": round(score, 3) == round(LOCAL_B_HIDDEN, 3), "identical_predictions_share": float((m.p_db == m.p).mean()),
           "rows_compared": len(m), "xgboost": xgb.__version__, "pandas": pd.__version__, "numpy": np.__version__, "machine": __import__("platform").machine()}
    _save("parity", res)
    log(res)


def register() -> None:
    import mlflow
    from mlflow.models import infer_signature
    mlflow.set_registry_uri("databricks-uc")
    user = _spark().sql("SELECT current_user()").first()[0]
    mlflow.set_experiment(f"/Users/{user}/og2-p6")
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, hd = sort(pd.read_parquet(IN / "force_train.parquet")), sort(pd.read_parquet(IN / "force_hidden_test.parquet"))
    out = {}
    for name, path, X in (("lithology_b", OUT / "lithology_b.json", engineered_matrix(hd, strat_codes(tr))),
                          ("lithology_t", IN / "p3_transfer_T.json", transfer_matrix(hd))):
        clf = xgb.XGBClassifier(); clf.load_model(str(path))
        sample = X.head(200)
        with mlflow.start_run(run_name=f"og2-p6-{name}"):
            info = mlflow.xgboost.log_model(clf, name="model", input_example=sample,
                                            signature=infer_signature(sample, clf.predict_proba(sample)))
            full = f"{CAT}.{SCHEMA}.{name}"
            v = mlflow.register_model(info.model_uri, full).version
            mlflow.MlflowClient().set_registered_model_alias(full, "champion", v)
        out[name] = {"registered": full, "version": int(v), "alias": "champion", "inputs": X.shape[1]}
        log(name, out[name])
    _save("registry", {"design": "ADR-008 register", **out})


def quality_archive() -> None:
    """ADR-008 amendment 1: every LAS file of the newest archive, parsed in parallel with Spark; ADR-006 quality measures
    and a drift sample per file (T's confidence is a drift signal only, not a lithology prediction)."""
    import zipfile
    spark = _spark()
    names = zipfile.ZipFile(IN / f"{NEW}.zip").namelist()
    entries = [n if n.lower().endswith(".las") else f"{n}/{Path(n).stem}.las" for n in names if n.lower().endswith((".las", ".zip"))]
    log(f"{len(entries):,} files in the {NEW} archive")
    root, zpath, tpath = str(ROOT), str(IN / f"{NEW}.zip"), str(IN / "p3_transfer_T.json")
    qcols = ["entry", "ok", "error", "samples", "coverage_core3", "out_of_range_share", "bad_hole_share", "bad_hole_basis", "t_conf_median"]
    schema = ("kind string, entry string, ok boolean, error string, samples double, coverage_core3 double, out_of_range_share double, "
              "bad_hole_share double, bad_hole_basis string, t_conf_median double, GR double, RHOB double, NPHI double, DTC double, RDEP double, T_CONF double")
    cols = [c.split()[0] for c in schema.split(", ")]

    def run(batches):
        import sys as _s
        if root not in _s.path:
            _s.path.insert(0, root)
        import xgboost as _x

        from src.quality import file_quality
        bst = _x.Booster(); bst.load_model(tpath)
        for pdf in batches:
            out = []
            for e in pdf.entry:
                r = file_quality(zpath, e, Path(e).stem, NEW, bst)
                out.append(pd.DataFrame([{**{k: r["row"].get(k) for k in qcols}, "kind": "file"}]))
                if r["sample"] is not None:
                    out.append(r["sample"].drop(columns=["archive"]).assign(kind="sample", entry=e))
            yield pd.concat(out, ignore_index=True).reindex(columns=cols) if out else pd.DataFrame(columns=cols)

    res = spark.createDataFrame(pd.DataFrame({"entry": entries})).repartition(32).mapInPandas(run, schema)
    res.write.mode("overwrite").saveAsTable(f"{CAT}.{SCHEMA}.kansas_quality_raw")
    t = spark.table(f"{CAT}.{SCHEMA}.kansas_quality_raw")
    files = t.where("kind = 'file'").drop(*["GR", "RHOB", "NPHI", "DTC", "RDEP", "T_CONF"])
    files.write.mode("overwrite").saveAsTable(f"{CAT}.{SCHEMA}.kansas_quality")
    f = files.toPandas()
    ok = f[f.ok == True]  # noqa: E712
    _save("archive_quality", {"design": "ADR-008 amendment 1, quality_archive", "archive": NEW, "files": len(f), "processed": int(len(ok)),
                              "processed_share": len(ok) / max(1, len(f)), "coverage_core3_median": float(ok.coverage_core3.median()),
                              "out_of_range_median": float(ok.out_of_range_share.median()), "t_conf_median": float(ok.t_conf_median.dropna().median())})


def monitor_drift() -> None:
    """PSI of the new archive's inputs and T's confidence vs earlier years (down-sampled P4 reference, ADR-006 bands)."""
    from src.drift import psi
    spark = _spark()
    ref = pd.read_parquet(IN / "p6_drift_reference.parquet")
    ref = ref[ref.archive < NEW]
    new = spark.table(f"{CAT}.{SCHEMA}.kansas_quality_raw").where("kind = 'sample'").toPandas()
    rows = []
    for c in ["GR", "RHOB", "NPHI", "DTC", "RDEP", "T_CONF"]:
        v = psi(ref[c].to_numpy(dtype=float), new[c].to_numpy(dtype=float))
        band = None if v is None else ("alert" if v > 0.25 else "watch" if v > 0.10 else "stable")
        rows.append({"archive": NEW, "input": c, "psi_vs_earlier": v, "band": band})
    spark.createDataFrame(pd.DataFrame(rows)).write.mode("overwrite").saveAsTable(f"{CAT}.{SCHEMA}.drift_psi")
    _save("drift", {"design": "ADR-008 monitor_drift", "reference_rows": len(ref), "new_rows": len(new), "rows": rows})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--task", required=True)
    {"parity_b": parity_b, "register": register, "quality_archive": quality_archive, "monitor_drift": monitor_drift}[ap.parse_args().task]()
