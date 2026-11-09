# Well-Log Lithology

**Does a rock-type model trained on North Sea wells hold up on wells it never saw, and does it transfer to Kansas?**

[![ci](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml/badge.svg)](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml)

**Live:** [results page](https://sabrinapribadi.github.io/well-log-lithology/) · [technical walkthrough](https://sabrinapribadi.github.io/well-log-lithology/build.html)

- **Lithology** is the rock type at each depth; petrophysicists pick it by hand from well logs.
- Train on 98 labelled North Sea wells (FORCE 2020); judge on 10 hidden wells the model never saw.
- Tested transfer to 28,906 public Kansas LAS files against formation tops: it failed, so this is a North Sea-only model.

## Status: phases 0–7 done

| Phase | Gate (set before the work) | Result |
|---|---|---|
| P0 Data foundation | Exact FORCE splits; ≥ 99% of Kansas headers readable | Passed (99.86% of 28,906) |
| P1 Blind-well baseline | XGBoost ≥ −0.526 on hidden wells (the finalists' range) | **Failed** (−0.540) |
| P2 Model choice | Chosen model beats P1 by ≥ 0.02 on hidden wells and on open wells | Passed (−0.504; +0.036) |
| P2b Method comparison | A new candidate replaces B only if ≥ 0.02 better in CV | B stays (fair LightGBM level; 1D CNN far behind) |
| P3 Kansas transfer | ≥ 50% agreement and lift ≥ 2 in 4 of 6 named units | **Failed** (0 of 6); transfer withdrawn |
| P4 Log quality and drift | Measures for ≥ 99% of Kansas files, drift every year | Passed (99.92%) |
| P5 API, MCP tools, copilot | Contract tests; grounded notes; cost and latency budgets | Passed (100% grounded, $0.066 per 1,000) |
| P6 Databricks job | Hidden score reproduced to 3 decimals; registry; drift job | **Failed** on parity (−0.486 vs −0.504); registry and job passed |
| P7 Pages | Live, browser-tested in three modes | Passed |

## Results

**How to read the score:** the official penalty score is the average cost of a mistake per 0.152 m depth sample. 0 is perfect; near mistakes (chalk for limestone) cost 1.375, far ones up to 4. Labelling everything shale scores −1.308 on the hidden wells.

- **Chosen model: −0.504 on 10 hidden wells.** That would rank 4th of the 13 2020 finalists (winner −0.469).
- **In metres:** 79.4% of the 18,604 m of hidden-well depth is labelled as the interpreter did (baseline 77.7%).
- **The baseline failed by 0.014.** No pipeline fault was found, so the failure stands.
- **Blind wells matter.** The same baseline scores −0.171 on a random split of samples: about 3× better than on unseen wells, because neighbouring depths leak.
- **Features carry the gain.** Context, bad-hole size and per-well gamma ray add +0.031; the penalty-aware decision adds +0.005.
- **Weak spots:** dolomite (22% of its metres found) and chalk (28%) need review; shale (94%) and halite (97%) are reliable.
- **One candidate collapsed, then recovered.** LightGBM's loose default leaf limit let rare-rock leaves explode; with XGBoost's limit it is level with XGBoost (CV −0.679).
- **A deep baseline trails.** A 1D CNN over ±2.4 m depth windows scores −0.944 in CV; 11 of 12 in-range 2020 finalists also used tree ensembles.
- **Seed noise is large.** Retraining with other seeds moves the hidden score from −0.482 to −0.666; P2's +0.036 sits within that noise.
- **Kansas transfer failed (0 of 6 units).** Old Kansas carbonates are tighter than any North Sea limestone and read as sandstone; evaporite intervals do not read as evaporites.
- **Kansas data quality:** gamma ray, neutron and density together cover a median 36% of each file's depth; logs sit outside the North Sea range in every year.
- **Copilot:** API and MCP tools serve validated outputs only; notes 100% grounded at $0.066 per 1,000.
- **Databricks:** quality and drift match the laptop exactly; retraining B differs like a seed change (features bit-identical).

Details: [docs/PRD.md](docs/PRD.md), [decision records](docs/adr/README.md), [CHANGELOG.md](CHANGELOG.md).

## Reproduce

```bash
make env                          # shared environment outside OneDrive: ~/.venvs/portfolio (+ ~/.portfolio-node)
cp .env.example .env              # set WLL_DATA_DIR
set -a; . ./.env; set +a
make pipeline                     # P0 → P1 → P2 → page data (about 1.5 hours on an 8 GB laptop); P3–P6 scripts in the table below
uvicorn src.serving.api:app --port 8000   # API; python -m src.serving.mcp_server for MCP (needs scripts/p5_build_store.py first)
make lint test build-test hover-test preview evidence
```

| Step | Script | Output (`data/outputs/`) | Decision record |
|---|---|---|---|
| P0 data foundation | `force_ingest.py`, `kgs_inventory.py`, `p0_report.py`, `reference_floors.py` | `p0_foundation.json`, `reference_floors.json` | ADR-001, ADR-003 |
| P1 baseline | `p1_baseline.py` | `p1_baseline.json` | ADR-004 |
| P2 model choice | `p2_model_choice.py`, `p2_lgb_diagnostic.py` | `p2_model_choice.json`, `p2_lgb_diagnostic.json` | ADR-004 |
| P2b comparison | `p2b_lightgbm_fair.py`, `p2b_cnn.py` | `p2b_lightgbm_fair.json`, `p2b_cnn.json` | ADR-009 |
| P3 Kansas transfer | `p3_transfer_model.py`, `p3_select_wells.py`, `p3_kansas_transfer.py`, `p3_diagnostic.py` | `p3_*.json` | ADR-005 |
| P4 quality and drift | `p4_quality.py` | `p4_quality.json` | ADR-006 |
| P5 serving | `p5_build_store.py`, `p5_eval_notes.py`, `src/serving/` | `p5_notes_eval.json` | ADR-007 |
| P6 Databricks | `databricks_p6.py`, `databricks.yml`, `p6_seed_spread.py` | `p6_*.json` | ADR-008 |
| Evidence (R2) | `evidence.py` | `references_evidence.json` | all ADRs |
| Pages | `export_page_data.py` | `docs/data/page_data.js` | — |

## Data

| Source | Licence |
|---|---|
| FORCE 2020 well log and lithofacies dataset (Zenodo 4351156) | CC BY 4.0 |
| FORCE 2020 competition repository (splits, penalty matrix, final scores) | Published by the organisers |
| Kansas Geological Survey LAS archive, wells, formation tops | Free use with citation (KGS terms of use) |

Raw data lives outside the repository (`WLL_DATA_DIR`). Code is MIT-licensed.
