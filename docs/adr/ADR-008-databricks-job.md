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

## Related Decisions

- ADR-001 (scale), ADR-002 (P6 gate), ADR-004 (B), ADR-005 (T and reading rules), ADR-006 (PSI bands)
