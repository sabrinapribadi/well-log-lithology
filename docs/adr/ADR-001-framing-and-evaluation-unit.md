# ADR-001: Framing, Evaluation Unit and Scale

**Status:** Accepted — written and pushed before any analysis
**Date:** 2026-10-15
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- **The task:** a petrophysicist labels each depth of a well with a lithology (rock type) from its logs: gamma ray, density, neutron, sonic, resistivity and others. Done by hand across hundreds of wells, the picks are slow and inconsistent, and mistakes propagate into reservoir models.
- **What the project answers:**
  1. How well does a model label rocks in wells it has never seen (North Sea, FORCE 2020)?
  2. Does a North Sea model transfer to a different basin (Kansas, ~28,900 public LAS files)?

## Decision

### Unit of evaluation: the blind well

- **Rule:** models are judged only on wells they never saw in training.
- **Why:** consecutive depth samples in one well are nearly identical. A random split of samples puts neighbours of every test sample in training and flatters any model. The competition starter notebook shows this: a random forest scores −0.130 on a random sample split, while the best team scored −0.469 on hidden wells.
- **Splits:** the official FORCE 2020 splits.

| Split | Wells | Samples | Use |
|---|---|---|---|
| Train | 98 | 1,170,511 | Training and well-grouped cross-validation |
| Open test ("leaderboard") | 10 | 136,786 | Reported; never used for choices |
| Hidden test (final scoring) | 10 | 122,397 | The gate; each pre-registered model scored once |

### Metric

- **Primary:** the official FORCE penalty score, S = −(1/N) Σ A[true, predicted], with the competition's 12 × 12 penalty matrix A. 0 is perfect; mistakes between similar rocks cost less (limestone vs chalk 1.375) than between unrelated ones (up to 4).
- **Reported, not gated:**
  - accuracy;
  - recall per lithology, which matters most for rare rocks (coal, anhydrite, halite);
  - per-well scores.
- **Published reference** (organisers' repository):
  - the 13 finalists' hidden-test scores were −0.469 (winner) to −0.526, plus one outlier at −0.944;
  - "shale everywhere" scores −1.154 on the starter's split.

### Kansas (transfer)

- **Labels:** none per sample. Transfer is judged against geology:
  - formation tops from the Kansas Geological Survey;
  - known lithology of named Kansas units, e.g. halite in the Hutchinson Salt, dolomite in the Arbuckle Group.
- **Designed in ADR-002 (P3)** before any Kansas prediction is made.

### Scale and platform (R15, measured 2026-10-15)

| Data | Volume | Fits the 8 GB laptop? |
|---|---|---|
| FORCE 2020 | 118 wells, 1.43M samples, ~29 columns | Yes |
| Kansas LAS archive | 28,906 files (8,463 direct + 20,443 in nested zips), 18 yearly zips, 8.3 GB zipped; the 8,463 direct files alone are 13.1 GB of text | Headers yes; all curves as one table, no (≈ 10⁸–10⁹ depth rows) |

- **P0–P2:** run locally with parallel processes: FORCE modelling and a header inventory of every Kansas file.
- **Spark on Databricks** is planned for P6, to standardise and score every Kansas curve (≈ 10⁸+ rows, heterogeneous files) on a schedule with a model registry. The volume and operations justify it there.

## Options considered

| Option | Status | Why |
|---|---|---|
| **Blind wells, official splits, penalty score** | **Chosen** | Matches how a model is used (new wells) and the published benchmark |
| Random split of samples | Rejected as an evaluation; reported once to show the overstatement | Leaks neighbouring depths |
| Accuracy as the headline | Rejected | Ignores that some mistakes are geologically worse; dominated by shale (62% of training samples) |
| Kansas lithology from cuttings descriptions | Not available at scale | KGS cuttings records are sparse and not on a depth grid |

## Consequences

- Scores are comparable with the 2020 competition finalists.
- Kansas results are a geological plausibility test, not an accuracy score. This is stated wherever they appear.

## Related Decisions

- ADR-002 (gates)
- ADR-003 (industry alignment)
