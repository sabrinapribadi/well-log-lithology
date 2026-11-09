# ADR-008: P6 Scheduled Databricks Job — Parity, Registry, Yearly Scoring and Drift

**Status:** Accepted — written and pushed before P6 is built
**Date:** 2026-11-08
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- KGS publishes a new yearly LAS archive. Scoring it, checking drift and keeping model versions is an operations job, not a laptop task.
- Scoring every Kansas curve means ≈ 10⁸ depth rows across 28,906 heterogeneous files (ADR-001, R15).
- **ADR-002 gate (P6):** Databricks reproduces the local P1 or P2 hidden-test score exactly; model registered; drift job runs.

## Decision Drivers

- Same code paths as the laptop (`src/`), so parity tests the platform, not a rewrite.
- Free Edition limits: serverless compute only, quotas; the schedule is defined but paused, runs on demand.
- No workspace URL or token in the repository; the CLI profile supplies them.

## Decision (pre-registered)

### Job `og2_p6` (Databricks Asset Bundle, serverless)

| Task | What | Output |
|---|---|---|
| `parity_b` | Train candidate B on the FORCE training wells (uploaded Parquet), score the 10 hidden wells | Score vs local −0.504 |
| `register` | Log B and T with MLflow; register in Unity Catalog with alias `champion` | `workspace.og2.lithology_b`, `workspace.og2.lithology_t` |
| `score_archive` | Parse every LAS file of the newest archive in parallel with Spark (one task per file, ADR-005 §5 rules), score with T | Delta table `workspace.og2.kansas_lithology` (well, depth, rock, probability) and a per-well summary |
| `monitor_drift` | PSI of the new archive's inputs and T's confidence vs earlier years (P4 reference sample, ADR-006 bands) | Delta table `workspace.og2.drift_psi` |

- **Archive in scope:** 2026 (and 2025 as the comparison year), uploaded to a Unity Catalog volume. The full archive stays the documented scale-up path.
- **Schedule:** yearly (after KGS's annual archive), defined and paused on Free Edition.

### "Exactly" made operational

- Parity passes when Databricks' hidden-well score equals the local −0.504 **to the reported three decimals**, and the share of identical predictions is reported.
- XGBoost's results can differ in the last float digits across processor types; three decimals is the precision every page and ADR reports. This clarifies ADR-002's "exactly"; it does not loosen any reported number.

### Gate

- Parity as above; both models registered with alias `champion`; `monitor_drift` finishes and writes its table.

### Scale (R15)

- Archives in scope: 2026 (374 files) and 2025 (2,715 files), ≈ 10⁷ depth rows together; all 18 archives ≈ 10⁸. Parsing thousands of independent files and scoring them on a schedule is what Spark and Databricks add here; the laptop handles P0–P4 by streaming one file at a time.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **Serverless job on Free Edition, newest archive, paused yearly schedule** | **Chosen** | Shows the operating cadence end to end within free quotas |
| Upload and score all 18 archives | Deferred | 8.9 GB upload and quota; same code scales out |
| Cron on the laptop | Rejected | No registry, no audit trail, not how operations run |
| Databricks downloads from KGS itself | Rejected for now | KGS served ≈ 50 KB/s on 2026-11-08; an upload is faster and repeatable |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| Score differs at the third decimal | Library versions or nondeterminism (as CHN-1's first Databricks run) | Pin versions; check row order and ties; rerun |
| Spark parse fails on files the laptop reads | Environment differences (encodings, zip libraries) | Fix and test with the failing files |
| Drift alerts on every input | 2026 archive genuinely differs (tools, companies) | Report; feeds the retraining case |

## Consequences

- **Positive:** a registry-backed, scheduled job that scores new Kansas wells and watches drift, as an operator would run it.
- **Negative:** Free Edition quotas cap scale; only one archive is scored on the platform.

## Amendment 1 (2026-11-09, after P3 failed, before P6 runs): the yearly job reports quality and drift, not lithology

- **Why:** P3 withdrew the Kansas transfer claim (ADR-005).
- **`parity_b` and `register`:** unchanged.
- **`score_archive` → `quality_archive`:** parse every LAS file of the newest archive in parallel with Spark and compute ADR-006's per-file quality measures (and T's confidence, labelled as a drift signal only). Output table `workspace.og2.kansas_quality`.
- **`monitor_drift`:** unchanged in method; its reference is a down-sampled P4 drift sample (≤ 20,000 rows per year), uploaded once.
- **Gate:** unchanged (parity to three decimals; models registered; drift task runs).

## Empirical results (2026-11-09)

**P6 failed on parity; registry and the yearly job passed.**

| Check | Target | Result |
|---|---|---|
| B's hidden score on Databricks vs laptop | equal to 3 decimals | **−0.486 vs −0.504: failed**; 94.4% of predictions identical |
| Models registered | B and T, alias `champion` | `workspace.og2.lithology_b` v1, `workspace.og2.lithology_t` v1: passed |
| Yearly quality job (2026 archive, Spark) | runs | 374 of 374 files; coverage 0.9871, out-of-range 0.0009, T confidence 0.777, equal to the laptop's P4 to four decimals: passed |
| Drift job | runs | PSI vs earlier years in the same band as the laptop for all 6 inputs (neutron 0.313 alert; density 0.125 watch): passed |

### Why parity failed (falsification diagnostic)

- **Ruled out:** library versions (rerun pinned to the laptop's pandas 3.0.6, numpy 2.5.4, pyarrow 26.0.0, xgboost 3.4.1: same −0.486); processor family (both ARM); thread count (laptop with 4 threads: −0.5040); duplicate rows (none).
- **Features are bit-identical:** all 122,397 × 43 hidden-well features match the laptop's.
- **The remaining difference is the XGBoost build** (Linux vs macOS wheel). Floating-point sums can differ in the last digits, changing near-tied splits; over 300 trees this behaves like a different random seed.
- **Seed spread on the laptop alone:** seeds 1, 2, 3 and 42 give −0.482, −0.666, −0.501, −0.504 (range 0.18, sd 0.086). The Databricks gap (0.018) is smaller than an ordinary seed change.
- **Consequence:** exact cross-platform parity is not achievable for this model as trained. Parity of inference (scoring a model trained once) and of the deterministic steps (quality, drift) does hold.

### Deviations

- **Drift reference (2026-11-09):** amendment 1 capped the reference at 20,000 rows per year, which weights every year equally and gave different bands from P4 (neutron "watch" instead of "alert"). Changed to a uniform 360,000-row sample, so years keep their P4 weights; bands then match P4 for all inputs.
- **Environment:** the parity task runs in an environment pinned to the laptop's library versions (`parity`), the registry task in the MLflow environment (`ml`).

## Related Decisions

- ADR-001 (scale), ADR-002 (P6 gate), ADR-004 (B), ADR-005 (T and reading rules), ADR-006 (PSI bands)
