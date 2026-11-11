"""ADR-010: P1 and B retrained with seeds 0–9; hidden and open wells scored for each (robustness, not a choice).

    python scripts/p2c_multi_seed.py

Writes data/outputs/p2c_multi_seed.json (results are saved after every seed, so a stopped run keeps its progress).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p1_baseline import PARAMS  # noqa: E402
from scripts.p2_model_choice import CFG, DER  # noqa: E402
from src.features import baseline_matrix, engineered_matrix, expected_penalty_decision, full_proba, labels, strat_codes  # noqa: E402
from src.scoring import penalty_score  # noqa: E402

OUT = ROOT / CFG["paths"]["outputs_dir"] / "p2c_multi_seed.json"
SEEDS, MARGIN = list(range(10)), 0.02
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def summary(runs: list[dict]) -> dict:
    out = {}
    for split in ("hidden_test", "open_test"):
        d = np.array([r["B"][split]["score"] - r["P1"][split]["score"] for r in runs])
        half = float(stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None
        sc = {m: [r[m][split]["score"] for r in runs] for m in ("P1", "B")}
        sd = lambda v: float(np.std(v, ddof=1)) if len(v) > 1 else None
        out[split] = {"P1_mean": float(np.mean(sc["P1"])), "P1_sd": sd(sc["P1"]), "B_mean": float(np.mean(sc["B"])), "B_sd": sd(sc["B"]),
                      "diff_mean": float(d.mean()), "diff_ci95": None if half is None else [float(d.mean() - half), float(d.mean() + half)], "b_wins": int((d > 0).sum())}
    h = out["hidden_test"]
    out["b_reliably_better"] = bool(h["diff_ci95"] and h["diff_mean"] >= MARGIN and h["diff_ci95"][0] > 0)
    return out


def main() -> None:
    sort = lambda d: d.sort_values(["WELL", "DEPTH_MD"]).reset_index(drop=True)
    tr, ot, hd = (sort(pd.read_parquet(DER / f"force_{k}.parquet")) for k in ("train", "open_test", "hidden_test"))
    codes, y = strat_codes(tr), labels(tr)
    X = {"P1": (baseline_matrix(tr, codes), {s: baseline_matrix(d, codes) for s, d in (("open_test", ot), ("hidden_test", hd))}),
         "B": (engineered_matrix(tr, codes), {s: engineered_matrix(d, codes) for s, d in (("open_test", ot), ("hidden_test", hd))})}
    ys = {"open_test": labels(ot), "hidden_test": labels(hd)}
    wells = {"open_test": ot.WELL.to_numpy(), "hidden_test": hd.WELL.to_numpy()}
    runs = json.loads(OUT.read_text())["runs"] if OUT.exists() else []
    done = {r["seed"] for r in runs}
    for seed in SEEDS:
        if seed in done:
            continue
        r = {"seed": seed}
        for name, (Xtr, Xte) in X.items():
            m = xgb.XGBClassifier(**{**PARAMS, "random_state": seed}).fit(Xtr, y)
            r[name] = {}
            for s in Xte:
                proba = full_proba(m, Xte[s])
                p = proba.argmax(1) if name == "P1" else expected_penalty_decision(proba)   # each model's own decision rule
                per = {w: penalty_score(ys[s][wells[s] == w], p[wells[s] == w]) for w in np.unique(wells[s])}
                r[name][s] = {"score": penalty_score(ys[s], p), "accuracy": float((p == ys[s]).mean()), "per_well": per}
        runs.append(r)
        log(f"seed {seed}: P1 hidden {r['P1']['hidden_test']['score']:.4f}  B hidden {r['B']['hidden_test']['score']:.4f}")
        OUT.write_text(json.dumps({"design": "ADR-010", "seeds_planned": SEEDS, "runs": runs, "summary": summary(runs)}, indent=1))
    s = summary(runs)
    log("hidden: diff mean", round(s["hidden_test"]["diff_mean"], 4), "ci95", s["hidden_test"]["diff_ci95"], "→ B reliably better:", s["b_reliably_better"])


if __name__ == "__main__":
    main()
