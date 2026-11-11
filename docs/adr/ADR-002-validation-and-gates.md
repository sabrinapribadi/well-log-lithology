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
| P3 | Does the model transfer to Kansas? | Designed in ADR-005 (pushed before any Kansas prediction): agreement with known lithology of named Kansas units (e.g. Hutchinson Salt → halite; Arbuckle → dolomite) in wells with formation tops | Transfer claim withdrawn; North Sea-only model |
| P4 | Can the logs' quality be monitored? | (ADR-006) Per-well data-quality and drift measures (curve availability, ranges, bad-hole share) computed for every Kansas well and year | Monitoring not shipped |
| P5 | Can geologists and agents use it? | (ADR-007) API and MCP contract tests pass; LLM explanations grounded in tool results; cost and latency within R13 budgets | Tools not shipped |
| P6 | Does it run as a scheduled cloud job? | (ADR-008) Databricks reproduces the local P1 or P2 hidden-test score exactly; model registered; drift job runs | Local only |
| P7 | Can readers use the results? | Results page and technical walkthrough live; browser tests pass in three display modes | Pages not published |

## About the thresholds

- **P1 (−0.526):** the 12th of the 13 finalists whose code ran on the hidden wells (the 13th, −0.944, is an outlier), from the organisers' published table. It means "competition level", not "winning".
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
| 2026-11-07 | P0 | Every file's location recorded | 1,633 Kansas headers give longitude without its minus sign (e.g. 99.0 for 99.0° W), placing 1,588 wells in Asia | Values between 94° and 103° flipped to west (`src/las_header.fix_west_longitude`, tested); count stored as `longitude_sign_fixed`. Gate unaffected; 24,165 of 24,166 located wells now inside Kansas | `data/outputs/p0_foundation.json` |
| 2026-11-07 | P2 | Model wrappers return probabilities for all 12 classes | CV fold 3 had no basement samples (103 in all training, in few wells); the model returned 11 columns and the penalty decision crashed | `src/features.full_proba` places probabilities by class label, unseen classes 0 (tested); folds 1–2 scored identically before and after | `tests/test_features.py` |
| 2026-11-07 | P1 | Fail means "the pipeline, not the model, is wrong" | P1 missed by 0.014. Checked: GROUP names all seen in training; 0.04% of hidden FORMATION names unseen; all 12 classes mapped; no −999 null codes in any log (values below −999 are Z_LOC, true vertical depth below sea level, legitimate) | Nothing changed; P1 stays failed; P2 runs against it as planned | Audit commands in CHANGELOG 0.3.0 |
| 2026-11-07 | P2 | ADR-004 candidate A: "bad-hole flag **and** size (CALI − BS)" | Code builds the size only; no flag | Not changed before P2 results; logged. For tree models a flag (size above a threshold) adds nothing a split on size cannot learn | `src/features.py` `engineered_matrix` |
| 2026-11-07 | Design | ADR-003 E5 says bad-hole features arrive in P1 | ADR-004 puts them in P2 (candidate A); P1 uses logs as provided | ADR-003 E5 phase corrected to P2 | ADR-004 |

## Seed spread: how to read the hidden-well scores (2026-11-09)

- Retraining B with seeds 1, 2, 3 (and 42) gives −0.482, −0.666, −0.501, −0.504 on the hidden wells: sd 0.086 (`data/outputs/p6_seed_spread.json`).
- P2's gain over P1 (+0.036) is smaller than one seed's sd. P2's gate result stands as pre-registered, but one seed cannot separate B from P1 with confidence; a multi-seed comparison would be a new pre-registered decision.
- **Multi-seed result (ADR-010, 2026-11-11):** over seeds 0–9, B beats P1 on every seed; mean +0.134 on the hidden wells (95% interval +0.055 to +0.213). Most of the spread comes from one hidden well, 17/4-1.

## Gate results (updated as phases finish)

| Phase | Result | Where |
|---|---|---|
| P0 | **Passed.** FORCE splits exact (98 / 10 / 10 wells; 1,170,511 / 136,786 / 122,397 samples); scorer equals the official loop. Kansas: 28,865 of 28,906 headers readable (99.86%); 41 files have no curve section, listed | `data/outputs/p0_foundation.json` |
| P1 | **Failed.** Hidden test −0.540 vs gate −0.526 (open test −0.585). Random 80/20 split of samples scores −0.171: the leak a random split hides | `data/outputs/p1_baseline.json` |
| P2 | **Passed.** Chosen by CV: B (engineered features + expected-penalty decision). Hidden test −0.504 (+0.036 vs P1; bar +0.020); open test −0.521 (+0.064). −0.504 would rank 4th of the 13 finalists | `data/outputs/p2_model_choice.json` |
| P3 | **Failed.** 0 of 6 Kansas units passed (ADR-005). Shales recognised (Heebner 90% agreement) but lift < 2; carbonates predicted as sandstone (tighter than any North Sea limestone); evaporite intervals do not read as evaporites. Transfer claim withdrawn | `data/outputs/p3_kansas_transfer.json`, `p3_diagnostic.json` |
| P4 | **Passed.** Quality measured for 99.92% of readable Kansas files (24,157 wells); drift for every year. Kansas logs alert against FORCE on density, neutron, sonic and resistivity in every year | `data/outputs/p4_quality.json` |
| P5 | **Passed.** API, MCP tools and notes on validated outputs only (ADR-007 amendment 1); 60 live cases 100% grounded; $0.066 per 1,000 notes; p95 2.7–4.7 s live (budget 5 s), 0.04 ms cached | `data/outputs/p5_notes_eval.json` |
| P6 | **Failed on parity** (Databricks −0.486 vs laptop −0.504; features bit-identical; the XGBoost build acts like a seed change, and the laptop's own seed spread is 0.18). Registry and the yearly quality and drift job passed, matching the laptop | `data/outputs/p6_*.json` |
| P7 | **Passed.** Results page (6.7 screens collapsed) and walkthrough live for P0–P6; browser tests 121/121 and 348/348 in light, dark and phone modes | `docs/index.html`, `docs/build.html`, `tests/browser/` |

## Evidence (OpenAlex, retrieved 2026-11-07; generated by `make evidence`)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| Equivalence Tests | Social Psychological and Personality Science | yes | 2017 | 2,617 | 261.7 | practice of a pre-set smallest worthwhile difference (the +0.02 margin is our own choice) |

Citation counts are evidence, never a gate.

## Related Decisions

- ADR-001 (unit and metric)
- ADR-003 (industry alignment)
- ADR-004 (P2 model choice, written before P2)
