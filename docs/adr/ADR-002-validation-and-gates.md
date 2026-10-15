# ADR-002: Validation Strategy and Gates for Every Phase

**Status:** Accepted — written and pushed before any analysis
**Date:** 2026-10-15
**Deciders:** Sabrina Pribadi

---

## Context

Each phase passes or fails a gate written here before its work starts. A failed gate is reported with its number, never hidden. The 10 hidden-test wells are the final judge. Each model named in a pre-registered decision is scored on them once; nothing is tuned on them.

## Gates

| Phase | Question | Gate (pass) | Fail means |
|---|---|---|---|
| P0 | Is the data what we think it is? | **FORCE:** the official splits are reproduced exactly (98 / 10 / 10 wells; 1,170,511 / 136,786 / 122,397 samples), and our scorer matches the official formula. **Kansas:** ≥ 99% of the 28,906 LAS files have a readable header; every file is inventoried (curves, units, null code, depth range, API number, location); failures are listed | Fix ingestion before any modelling |
| P1 | Can a standard model reach competition level on blind wells? | XGBoost (the winning team's model family), trained on the 98 training wells with documented features and no tuning on test wells, scores **≥ −0.526** on the hidden test, i.e. within the 12 finalists' range (−0.469 to −0.526) | The pipeline, not the model, is wrong: features, encoding or class mapping |
| P2 | Does a better-designed model beat the baseline on blind wells? | The model chosen in ADR-004 (written before P2) beats P1 by **≥ 0.02** on the hidden test **and** scores better on the open test. Selection uses only well-grouped cross-validation on the training wells | Keep the P1 model; report the candidates' scores |
| P3 | Does the model transfer to Kansas? | Designed in a pre-registered ADR before any Kansas prediction: agreement with known lithology of named Kansas units (e.g. Hutchinson Salt → halite; Arbuckle → dolomite) in wells with formation tops | Transfer claim withdrawn; North Sea-only model |
| P4 | Can the logs' quality be monitored? | Per-well data-quality and drift measures (curve availability, ranges, bad-hole share) computed for every Kansas well and year | Monitoring not shipped |
| P5 | Can geologists and agents use it? | API and MCP contract tests pass; LLM explanations grounded in tool results; cost and latency within R13 budgets | Tools not shipped |
| P6 | Does it run as a scheduled cloud job? | Databricks reproduces the local P1 or P2 hidden-test score exactly; model registered; drift job runs | Local only |
| P7 | Can readers use the results? | Results page and technical walkthrough live; browser tests pass in three display modes | Pages not published |

## About the thresholds

- **P1 (−0.526):** the weakest score among the 12 finalists whose code ran on the hidden wells, from the organisers' published table. It means "competition level", not "winning".
- **P2 (+0.02):** our own threshold, about a third of the spread between the 1st and 12th finalists (0.057). No published standard sets it. The practice of fixing the smallest worthwhile difference in advance follows Lakens (2017).
- **Kansas (P3):** has no per-sample labels, so its gate is a geological consistency test, designed before predictions are made.

## Validation details

- **Well-grouped cross-validation (P2 selection):** 5 folds of training wells (GroupKFold by well), so no well is in both training and validation.
- **Leakage check (reported in P1):** the P1 model's score on a random 80/20 split of samples vs on blind wells.
- **Class imbalance:** reported per class. Rare classes (basement: 103 training samples) cannot be judged reliably and are flagged as such.

## Deviations from the pre-registered plan

Logged here when found, with evidence.

| Date | Phase | Pre-registered | Found | Changed to | Evidence |
|---|---|---|---|---|---|

## Gate results (updated as phases finish)

| Phase | Result | Where |
|---|---|---|
| P0–P7 | Not yet run | — |

## Related Decisions

- ADR-001 (unit and metric)
- ADR-003 (industry alignment)
- ADR-004 (P2 model choice, written before P2)
