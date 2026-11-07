# Well-Log Lithology

**Does a rock-type model trained on North Sea wells hold up on wells it never saw, and does it transfer to Kansas?**

[![ci](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml/badge.svg)](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml)

**Live:** [results page](https://sabrinapribadi.github.io/well-log-lithology/) · [technical walkthrough](https://sabrinapribadi.github.io/well-log-lithology/build.html)

- **Lithology** is the rock type at each depth; petrophysicists pick it by hand from well logs.
- Train on 98 labelled North Sea wells (FORCE 2020); judge on 10 hidden wells the model never saw.
- Next: test transfer to ~28,900 public Kansas LAS files against formation tops.

## Status: phases 0–2 done

| Phase | Gate (set before the work) | Result |
|---|---|---|
| P0 Data foundation | Exact FORCE splits; ≥ 99% of Kansas headers readable | Passed (99.86% of 28,906) |
| P1 Blind-well baseline | XGBoost ≥ −0.526 on hidden wells (the finalists' range) | **Failed** (−0.540) |
| P2 Model choice | Chosen model beats P1 by ≥ 0.02 on hidden wells and on open wells | Passed (−0.504; +0.036) |
| P3 Kansas transfer | Agreement with known unit lithology (ADR first) | Planned |
| P4–P6 | Log quality, API + MCP tools, Databricks job | Planned |
| P7 Pages | Live, browser-tested in three modes | Live for P0–P2 |

## Results

**How to read the score:** the official penalty score is the average cost of a mistake per 0.152 m depth sample. 0 is perfect; near mistakes (chalk for limestone) cost 1.375, far ones up to 4. Labelling everything shale scores −1.308 on the hidden wells.

- **Chosen model: −0.504 on 10 hidden wells.** That would rank 4th of the 13 2020 finalists (winner −0.469).
- **In metres:** 79.4% of the 18,604 m of hidden-well depth is labelled as the interpreter did (baseline 77.7%).
- **The baseline failed by 0.014.** No pipeline fault was found, so the failure stands.
- **Blind wells matter.** The same baseline scores −0.171 on a random split of samples: about 3× better than on unseen wells, because neighbouring depths leak.
- **Features carry the gain.** Context, bad-hole size and per-well gamma ray add +0.031; the penalty-aware decision adds +0.005.
- **Weak spots:** dolomite (22% of its metres found) and chalk (28%) need review; shale (94%) and halite (97%) are reliable.
- **One candidate collapsed.** LightGBM's loose default leaf limit let rare-rock leaves explode (raw scores 1.4M); matched limits fix it on training wells.

Details: [docs/PRD.md](docs/PRD.md), [decision records](docs/adr/README.md), [CHANGELOG.md](CHANGELOG.md).

## Reproduce

```bash
make env                          # shared environment outside OneDrive: ~/.venvs/portfolio (+ ~/.portfolio-node)
cp .env.example .env              # set WLL_DATA_DIR
set -a; . ./.env; set +a
make pipeline                     # P0 → P1 → P2 → page data (about 1.5 hours on an 8 GB laptop)
make lint test build-test hover-test preview evidence
```

| Step | Script | Output (`data/outputs/`) | Decision record |
|---|---|---|---|
| P0 data foundation | `force_ingest.py`, `kgs_inventory.py`, `p0_report.py`, `reference_floors.py` | `p0_foundation.json`, `reference_floors.json` | ADR-001, ADR-003 |
| P1 baseline | `p1_baseline.py` | `p1_baseline.json` | ADR-004 |
| P2 model choice | `p2_model_choice.py`, `p2_lgb_diagnostic.py` | `p2_model_choice.json`, `p2_lgb_diagnostic.json` | ADR-004 |
| Evidence (R2) | `evidence.py` | `references_evidence.json` | all ADRs |
| Pages | `export_page_data.py` | `docs/data/page_data.js` | — |

## Data

| Source | Licence |
|---|---|
| FORCE 2020 well log and lithofacies dataset (Zenodo 4351156) | CC BY 4.0 |
| FORCE 2020 competition repository (splits, penalty matrix, final scores) | Published by the organisers |
| Kansas Geological Survey LAS archive, wells, formation tops | Free use with citation (KGS terms of use) |

Raw data lives outside the repository (`WLL_DATA_DIR`). Code is MIT-licensed.
