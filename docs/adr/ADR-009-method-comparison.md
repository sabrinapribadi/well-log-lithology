# ADR-009: P2b Method Comparison — Fair LightGBM, a 1D Convolutional Network, and the Finalists' Methods

**Status:** Accepted — written and pushed before either new candidate ran; results appended
**Date:** 2026-11-08
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- P2 tested only gradient-boosted trees. LightGBM (candidate C) diverged under its default leaf limit, so "XGBoost vs LightGBM" is still open (ADR-004, empirical results).
- No deep model was tested; the published deep approaches were only cited.
- The page compares our score with the 2020 finalists, but not their methods.
- **Question:** does a fairly configured LightGBM, or a deep model reading depth windows, beat candidate B on the same wells?

## Decision Drivers

- Same wells, same metric, same selection rule as P2: choose on training wells only; each new candidate meets the hidden wells once.
- No tuning after seeing any score; settings fixed here.
- The 8 GB laptop: LightGBM and PyTorch run in separate processes (an OpenMP clash crashed a combined process in an earlier portfolio project).

## Decision (pre-registered)

### Candidate C2 — LightGBM, fair

- Candidate C exactly (same features as A, B's expected-penalty decision, same settings), with one change: `min_sum_hessian_in_leaf = 1.0`, matching XGBoost's default `min_child_weight = 1`.
- This is the only change, chosen from the P2 diagnostic on training wells (ADR-004); no other setting is touched.

### Candidate D — 1D convolutional network over depth windows

- **Input:** for each depth sample, a window of 33 samples (± 16, about ± 2.4 m) within the same well, zero-padded at well ends.
- **Channels:** P1's per-sample inputs (20 logs, position, group and formation codes), standardised with training-well statistics; missing values → 0, plus one missing-flag channel per log.
- **Network:** three 1D convolutions (64 filters, kernel 5, batch norm, ReLU), then the centre position and the window average concatenated, then a linear layer to 12 classes.
- **Training:** cross-entropy, no class weights (as P1); Adam, learning rate 0.001, batch 2,048, 6 epochs, seed 42. No early stopping.
- **Decision:** expected penalty (as B).
- **Device:** Apple GPU (MPS) when available, else CPU; recorded.

### Selection and reporting

- **Both candidates:** the same 5-fold well-grouped CV as P2, then fitted on all 98 training wells and scored once on the open and hidden wells.
- **B stays the chosen model** unless a new candidate's CV mean beats B's (−0.670) by ≥ 0.02, the P2 margin. In that case the new candidate becomes the choice, and its hidden-well score is the P2b result.
- **All three** (B, C2, D) are reported side by side, whatever happens.

### Finalists' methods (documentation)

- Each of the 13 finalists' model families, from the organisers' technical retrospective and each team's public code in the organisers' repository. Recorded in ADR-004's SOTA table and on the results page.

## Empirical results (2026-11-08; the decision above is unchanged)

| Candidate | CV mean | Open test | Hidden test | Hidden accuracy |
|---|---|---|---|---|
| **B (XGBoost, chosen)** | **−0.670** | **−0.521** | **−0.504** | 79.4% |
| C2 LightGBM, matched leaf limit | −0.679 | −0.536 | −0.495 | 80.0% |
| D 1D CNN, 33-sample windows (Apple GPU, 55 min) | −0.944 | −0.829 | −0.945 | 64.0% |

- **B stays the chosen model:** neither candidate beats its CV mean by ≥ 0.02.
- **C2:** matching one safeguard took LightGBM from collapse (−1.03) to level with XGBoost. On the 10 hidden wells it scores 0.009 better than B and on the open wells 0.015 worse: a reminder of why selection uses CV, not one set of 10 wells.
- **D:** a small CNN trained for a fixed 6 epochs falls well short of trees with engineered context on 98 wells, as in the 2020 competition (11 of the 12 in-range finalists used tree ensembles).
- **Finalists' methods:** recorded with sources in `configs/force2020_finalists.json` and ADR-004's SOTA table.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **C2 (one documented fix) + D (a standard 1D CNN)** | **Chosen** | Closes the two gaps a reviewer would raise, at laptop cost |
| Tune LightGBM fully | Rejected | Would compare a tuned model with an untuned B |
| Transformer or contrastive pre-training (NRR 2025) | Cited, not tested | GPU-scale budget; D is the cheaper deep baseline |
| LSTM over depth | Not chosen | A CNN is the more cited well-log baseline (Imamverdiyev and Sukhostat 2019); one deep model is enough to answer the question |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| C2 ≈ B | Library does not matter; features and decision do | Report; B stays |
| D well below B | Trees with engineered context beat a small CNN on 98 wells (as in the 2020 competition) | Report |
| D beats B by ≥ 0.02 in CV | Learned depth context adds skill | D becomes the choice; scored once on hidden wells |

## Consequences

- **Positive:** one tested deep model and a fair library comparison, without moving any earlier result.
- **Negative:** one CNN configuration says little about deep models in general; it is a baseline, not a search.

## Related Decisions

- ADR-002 (selection by CV; hidden wells once), ADR-004 (candidates A–C, diagnostic)

## Evidence (OpenAlex, retrieved 2026-11-11; generated by `make evidence`)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| Lithological facies classification using deep convolutional neural network | Journal of Petroleum Science and Engineering | yes | 2018 | 230 | 25.6 | 1D CNN on well logs (candidate D) |
| Lithology identification from well-log curves via neural networks with additional geologic constraint | Geophysics | yes | 2021 | 103 | 17.2 | deep models on log curves with a geologic constraint (context) |

**Other sources (not papers; no citation counts):**

| Document | Issuer | Year | Used for |
|---|---|---|---|
| FORCE 2020 lithology prediction: technical retrospective | Competition organisers (repository PDF) | — | Top-three methods |
| Finalists' code (`lithology_competition/code/<team>/`) | Organisers' repository | 2020–2021 | Model family per finalist |
