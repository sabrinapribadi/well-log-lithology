# Well-Log Lithology

<!-- brief:start -->

## For hiring teams: the project in 5W1H

1. **What:** A rock-type (lithology) model for well logs, served as a results page, an API, MCP tools and grounded notes.
2. **Why:** Petrophysicists pick lithology by hand at every 0.152 m of every well; a checked first pass shows where to look first.
3. **Who:** Users: petrophysicists and geologists reviewing new wells.
   - Data: FORCE 2020 North Sea, 118 wells with interpreted rock types (CC BY 4.0), plus 28,906 public Kansas LAS files.
4. **Where:** [Results page](https://sabrinapribadi.github.io/well-log-lithology/) and [technical walkthrough](https://sabrinapribadi.github.io/well-log-lithology/build.html) on GitHub Pages; [live API and MCP](https://well-log-lithology.vercel.app/docs) on Vercel; yearly job, registry and app on Databricks.
5. **When it fails:** 8 phases, each with a pass bar set before the work; 3 failed and are reported (baseline, Kansas transfer, cloud parity).
   - No live A/B test: there are no live users. Changes face 10 blind wells, grouped cross-validation and a 10-seed paired test.
6. **How:** XGBoost with engineered features and a penalty-aware decision, chosen over LightGBM and a 1D CNN by cross-validation.
   - Score: the official FORCE penalty, 0 is perfect: −0.504 on 10 unseen wells (4th of 13 2020 finalists); beats the baseline on 10 of 10 seeds.

**Skills applied** (each linked to the file or decision that shows it):

- **Data engineering:** LAS parsing, unit standardisation and quality checks for 28,906 files — [src/kansas.py](src/kansas.py), [ADR-006](docs/adr/ADR-006-log-quality-and-drift.md)
- **Machine learning:** XGBoost, LightGBM and a PyTorch 1D CNN under one comparison — [ADR-004](docs/adr/ADR-004-baseline-and-model-choice.md), [ADR-009](docs/adr/ADR-009-method-comparison.md)
- **Statistics and evaluation:** blind wells, grouped CV, cost matrix, paired-seed interval, PSI drift — [ADR-002](docs/adr/ADR-002-validation-and-gates.md), [ADR-010](docs/adr/ADR-010-multi-seed-comparison.md)
- **MLOps and CI/CD:** GitHub Actions with browser tests, gated Pages, signed build provenance, CD to Vercel — [ci.yml](.github/workflows/ci.yml)
- **Cloud and platform:** Databricks bundle, Spark job, Unity Catalog registry, Databricks App — [ADR-008](docs/adr/ADR-008-databricks-job.md), [databricks.yml](databricks.yml)
- **GenAI and agents:** grounded notes with a grader, MCP tools, OpenTelemetry traces, prompt-injection tests — [ADR-007](docs/adr/ADR-007-api-mcp-copilot.md), [ADR-011](docs/adr/ADR-011-public-api-and-technology-assessment.md)
- **Domain:** petrophysics (LAS standard, formation tops, lithology classes, Kansas geology) — [ADR-003](docs/adr/ADR-003-industry-alignment.md), [ADR-005](docs/adr/ADR-005-kansas-transfer-test.md)

<!-- brief:end -->

[![ci](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml/badge.svg)](https://github.com/sabrinapribadi/well-log-lithology/actions/workflows/ci.yml)

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

## Try it: live API and MCP

| Surface | Address | What it serves |
|---|---|---|
| REST API with interactive docs | [well-log-lithology.vercel.app/docs](https://well-log-lithology.vercel.app/docs) | Lithology for the 20 test wells, Kansas log quality, the transfer result, notes |
| MCP endpoint (stateless, spec 2026-07-28) | `https://well-log-lithology.vercel.app/mcp` | The same four tools for AI assistants |
| Databricks App (platform demo) | `og2-lithology-api-…databricksapps.com` | The same app inside Databricks Free Edition |

- Read-only: notes are cached or templated; no LLM key on any host; LAS upload and prediction run locally.
- Connect an assistant: `claude mcp add --transport http lithology https://well-log-lithology.vercel.app/mcp`.
- The Databricks App needs a workspace login; Free Edition stops apps after 24 hours (`databricks bundle run og2_api` restarts it).

**Free-tier limits (R20; Vercel Hobby, read 2026-11-11):**
- Free and non-commercial; each call gets up to 2 GB, 1 vCPU and 300 s.
- A monthly allotment; Hobby has no billing, so Vercel pauses the project instead of charging.
- After idle time the first call wakes the app: about 1–3 s (measured 2026-11-11).
- **Fallback:** the [results page](https://sabrinapribadi.github.io/well-log-lithology/) is static and carries every number, even if the API is paused.

## Results

**How to read the score:** the official penalty score is the average cost of a mistake per 0.152 m depth sample. 0 is perfect; near mistakes (chalk for limestone) cost 1.375, far ones up to 4. Labelling everything shale scores −1.308 on the hidden wells.

- **The 2020 field:** the winner scored −0.469; the finalists in range ran −0.469 to −0.526.
- **In metres:** 79.4% of the 18,604 m of hidden-well depth is labelled as the interpreter did (baseline 77.7%).
- **Baseline miss (P1):** no pipeline fault was found, so the failure stands.
- **Blind wells matter.** The same baseline scores −0.171 on a random split of samples: about 3× better than on unseen wells, because neighbouring depths leak.
- **Features carry the gain.** Context, bad-hole size and per-well gamma ray add +0.031; the penalty-aware decision adds +0.005.
- **Weak spots:** dolomite (22% of its metres found) and chalk (28%) need review; shale (94%) and halite (97%) are reliable.
- **One candidate collapsed, then recovered.** LightGBM's loose default leaf limit let rare-rock leaves explode; with XGBoost's limit it is level with XGBoost (CV −0.679).
- **A deep baseline trails.** A 1D CNN over ±2.4 m depth windows scores −0.944 in CV; 11 of 12 in-range 2020 finalists also used tree ensembles.
- **Seed check (ADR-010):** B's lead is +0.134 on average; the 95% interval, +0.055 to +0.213, would hold the true gain 19 times in 20 and stays above 0.
- **One hidden well drives the seed noise.** Well 17/4-1 swings by up to 0.74 between seeds; the other nine stay within 0.08.
- **Why Kansas failed (0 of 6 units):** old Kansas carbonates are tighter than any North Sea limestone and read as sandstone; evaporite intervals do not read as evaporites.
- **Kansas data quality:** gamma ray, neutron and density together cover a median 36% of each file's depth; logs sit outside the North Sea range in every year.
- **Databricks:** quality and drift match the laptop exactly; retraining B moves the score like a seed change (features bit-identical).

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
