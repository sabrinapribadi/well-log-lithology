# ADR-004: P1 Baseline and P2 Model Choice

**Status:** Accepted — written and pushed before P1 and P2 run
**Date:** 2026-10-15
**Deciders:** Sabrina Pribadi

---

## Context

ADR-002 sets the gates:

- **P1:** an XGBoost baseline must reach the 2020 finalists' range on the hidden wells (≥ −0.526).
- **P2:** the chosen model must beat P1 by ≥ 0.02 there and also score better on the open test.

This ADR fixes the baseline exactly and names the P2 candidates and how one is chosen, before any of them runs.

## Decision (pre-registered)

### P1 baseline (fixed; no tuning on test wells)

- **Model:** XGBoost multiclass (the winning team's model family), `hist` trees.
  - Settings: 300 rounds, depth 8, learning rate 0.1, row and column subsampling 0.8, seed 42, no class weights.
- **Features (as provided):**
  - logs: CALI, RSHA, RMED, RDEP, RHOB, GR, SGR, NPHI, PEF, DTC, SP, BS, ROP, DTS, DCAL, DRHO, MUDWEIGHT, RMIC, ROPA, RXO;
  - position: DEPTH_MD, X_LOC, Y_LOC, Z_LOC;
  - stratigraphy: GROUP and FORMATION as integer codes, fitted on the training wells (unseen names → missing).
- **Missing values:** left missing (XGBoost learns a direction for them).
- **Decision:** the most probable class.
- **Leakage check (reported):** the same model trained on a random 80% of training samples and scored on the other 20%.

### P2 candidates (all use the same 98 training wells)

| Candidate | What changes from P1 | Why (petrophysics) |
|---|---|---|
| A. Engineered features | Adds: log10 of resistivities; bad-hole flag and size (CALI − BS); per-well gamma-ray percentile; first differences and ±5-sample rolling means of GR, RHOB, NPHI, DTC, PEF within each well | Normalisation, log QC and vertical context, as interpreters use them (ADR-003 E5, E6) |
| B. A + penalty-aware decision | Same model as A; picks the class with the lowest expected penalty, argmin_k Σ_j p_j A[j, k], not the most probable class | The metric charges different costs for different mistakes, so the best decision uses the class probabilities and the matrix (Bayes decision rule) |
| C. LightGBM on A's features + B's decision | A different gradient-boosting library with the same features and decision | Checks whether the gain is the features or the library |

### Selection

- **On training wells only:** 5-fold well-grouped cross-validation (GroupKFold by well); mean penalty score across folds.
- **Choose:** the best candidate by that cross-validated score.
- **Score once** on the open test and the hidden test.
- **Report all three:** each candidate's open-test and hidden-test scores are reported too, as a check. The choice is the cross-validation one, even if another candidate happens to score better on the hidden wells.

### Gate (ADR-002 P2)

The chosen candidate beats P1 by ≥ 0.02 on the hidden test and scores better than P1 on the open test.

## SOTA comparison

| Family | Method | Tested | Cited, not tested (why) |
|---|---|---|---|
| Gradient-boosted trees | XGBoost (competition winner's family), LightGBM | Yes | — |
| Decision rule | Expected-penalty (Bayes) decision on class probabilities | Yes | — |
| Deep sequence models | Semi-supervised contrastive + Transformer (Natural Resources Research 2025) | No (P2) | Needs a GPU-scale training budget; considered after P2 if the gap to the winner stays large |
| Foundation models | Well-log foundation model (WLFM); tabular foundation models | No | Recent preprints; a later comparison on the same blind wells |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| P1 well below −0.526 | Pipeline problem: class mapping, features, missing values | Fix before P2; log a deviation |
| Candidates beat P1 in CV but not on hidden wells | Cross-validation folds differ from the hidden wells (geology, tools) | Keep P1; report |
| B helps only rare classes | The decision rule trades shale accuracy for fewer costly mistakes | Report per-class recall |

## Related Decisions

- ADR-001 (blind wells, metric)
- ADR-002 (gates)
- ADR-003 (petrophysics features)
