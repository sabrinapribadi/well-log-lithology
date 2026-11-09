# ADR-004: P1 Baseline and P2 Model Choice

**Status:** Accepted — written and pushed before P1 and P2 ran; results appended
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
| Gradient-boosted trees, fair LightGBM | LightGBM with XGBoost's leaf safeguard (ADR-009, C2) | Yes (P2b) | CV −0.679, hidden −0.495: level with XGBoost |
| Deep, convolutional | 1D CNN over depth windows (Imamverdiyev and Sukhostat 2019; ADR-009, D) | Yes (P2b) | CV −0.944, hidden −0.945: far behind trees |
| Deep sequence models | Semi-supervised contrastive + Transformer (Natural Resources Research 2025) | No | Needs a GPU-scale training budget; a small CNN already trails trees by 0.27 in CV |
| Foundation models | Well-log foundation model (WLFM); tabular foundation models | No | Recent preprints; a later comparison on the same blind wells |

### What the 2020 finalists used (organisers' technical retrospective; each team's code in the organisers' repository)

| Final rank | Team | Hidden score | Method |
|---|---|---|---|
| 1 | Olawale Ibrahim | −0.469 | XGBoost; 10-fold stratified CV; rare curves dropped; window and gradient features; no imputation |
| 2 | GIR Team | −0.479 | XGBoost; physics-guided imputation of missing curves; gradient and polynomial features |
| 3 | Lab.ICA-Team | −0.495 | Random forest; 5-fold CV; normalised GR and RHOB, gradients, formation; median fill |
| 4 | H3G | −0.505 | CatBoost and XGBoost; iterative imputation |
| 5 | ISPL Team | −0.508 | XGBoost |
| 6 | Jiampiers C. | −0.509 | scikit-learn model (family not stated in the published code) |
| 7 | José Bermúdez | −0.509 | Random forest |
| 8 | Bohdan Pavlyshenko | −0.517 | LightGBM with a logistic-regression stack |
| 9 | Jeremy Zhao | −0.517 | XGBoost and random forest; iterative imputation |
| 10 | Campbell Hutcheson | −0.522 | XGBoost |
| 11 | David P. | −0.526 | LightGBM |
| 12 | SoftServe Team | −0.526 | Ensemble of LightGBM models; LightGBM imputation |
| 13 | Dapo Awolayo | −0.944 | LightGBM |

- None of the top three used the penalty matrix in training (retrospective). Candidate B uses it in the decision step (+0.005).

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| P1 well below −0.526 | Pipeline problem: class mapping, features, missing values | Fix before P2; log a deviation |
| Candidates beat P1 in CV but not on hidden wells | Cross-validation folds differ from the hidden wells (geology, tools) | Keep P1; report |
| B helps only rare classes | The decision rule trades shale accuracy for fewer costly mistakes | Report per-class recall |

## Options considered and rejected (R2)

Documentation added 2026-11-07, after P1 and before P2 results; the pre-registered decision above is unchanged.

| Option | Status | Why |
|---|---|---|
| **XGBoost / LightGBM on well logs** | **Chosen** (P1, A–C) | The competition winner's family; handles missing logs natively; trains on 1.17M samples on an 8 GB laptop |
| Random forest (the starter notebook's model) | Rejected | Its published score comes from a random sample split (−0.130), which leaks neighbouring depths (ADR-001) |
| Class weights for rare rocks | Rejected | The penalty matrix already prices each mistake; reweighting shifts the probabilities that candidate B's decision rule uses |
| Deep sequence models (contrastive + Transformer, NRR 2025) | Cited, not tested in P2 | Needs a GPU-scale training budget; revisited if the gap to the winner stays large |
| Foundation models (WLFM; tabular foundation models) | Cited, not tested in P2 | Recent preprints; a 2026 preprint questions tabular foundation models off independent, identically distributed data, which blind wells are not |

## Evidence (OpenAlex, retrieved 2026-11-07; generated by `make evidence`)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| XGBoost | ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD) | yes | 2016 | 61,163 | 5,560.3 | P1 baseline and candidates A, B |
| LightGBM: A Highly Efficient Gradient Boosting Decision Tree | NeurIPS 2017 (OpenAlex primary copy is a mirror) | yes | 2017 | 10,513 | 1,051.3 | candidate C |
| Enhanced Lithology Classification Using an Interpretable SHAP Model Integrating Semi-Supervised Contrastive Learning and Transformer with Well Logging Data | Natural Resources Research | yes | 2025 | 33 | 16.5 | cited alternative (semi-supervised contrastive + Transformer) |
| WLFM: A Well-Logs Foundation Model for Multi-Task and Cross-Well Geological Interpretation | arXiv 2509.18152 | no (preprint) | 2025 | 5 | 2.5 | cited alternative (well-log foundation model) |
| Beyond IID: How General Are Tabular Foundation Models, Really? | arXiv 2606.30410 | no (preprint) | 2026 | 25 | 25.0 | cited alternative (tabular foundation models off IID data) |

Citation counts are evidence, never a gate.

## Empirical results (appended after each phase; the decision above is unchanged)

### P1 (2026-11-07): failed

| Split | Penalty score | Accuracy |
|---|---|---|
| Open test | −0.585 | 77.5% |
| Hidden test | −0.540 (gate ≥ −0.526) | 77.7% |
| Random 80/20 split of training samples (leak check) | −0.171 | 93.6% |

Falsification row 1 applied: pipeline checked (stratigraphy names, class mapping, null codes); no fault found, so the failure stands (ADR-002 deviations).

### P2 (2026-11-07): passed

| Candidate | CV mean (5 well groups) | Open test | Hidden test |
|---|---|---|---|
| A. Engineered features | −0.671 | −0.524 | −0.509 |
| **B. A + expected-penalty decision (chosen)** | **−0.670** | **−0.521** | **−0.504** |
| C. LightGBM + A's features + B's decision | −1.231 | −1.139 | −1.028 |

- **Gate:** B beats P1 by +0.036 on the hidden test (bar +0.020) and by +0.064 on the open test: passed.
- **Where the gain comes from:** features, mostly. A alone gains +0.031 on the hidden test; B's decision rule adds +0.005. A and B differ by only 0.001 in CV, so the choice between them is close.
- **Benchmark:** −0.504 would rank 4th of the 13 finalists (3rd −0.495, 4th −0.505).
- **Candidate C collapsed.** Falsification check: LightGBM's default leaf safeguard (`min_sum_hessian_in_leaf` 0.001) let leaves with a few rare-rock samples take huge values: maximum raw score 1.4M. With XGBoost's safeguard (1.0) the same fit is near-perfect on its training wells (raw scores ≤ 34). C therefore says nothing about LightGBM itself; a matched comparison would be a new candidate, pre-registered before scoring. Evidence: `data/outputs/p2_lgb_diagnostic.json` (training wells only).
- **Rare rocks:** B's recall on the hidden wells: shale 94%, halite 97%, sandstone 78%; dolomite 22% and chalk 28% remain weak.

## Related Decisions

- ADR-001 (blind wells, metric)
- ADR-002 (gates)
- ADR-003 (petrophysics features)
