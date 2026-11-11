# ADR-010: Multi-Seed Comparison of the Baseline (P1) and the Chosen Model (B)

**Status:** Accepted — written and pushed before any new seed runs; result: **B is reliably better** (2026-11-11)
**Date:** 2026-11-11
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- P2 passed: B beat P1 by +0.036 on the hidden wells (bar +0.020), each scored with one seed (42).
- P6's diagnostic then showed B's hidden score moves with the random seed alone: seeds 1, 2, 3 and 42 give −0.482, −0.666, −0.501, −0.504 (sd 0.086).
- **Question:** averaged over seeds, does B beat P1 on the hidden wells by a margin larger than the seed noise?

## Decision Drivers

- The seed-42 results and the P2 gate stand as pre-registered; this ADR adds a robustness check, not a new choice.
- Same data, code and settings as ADR-004; only `random_state` changes.
- The answer must be fixed before the runs, including what counts as "B is better".

## Decision (pre-registered)

- **Seeds:** 0–9 (10 seeds) for both P1 and B; every other setting as ADR-004.
- **Scored:** each fit on the open and the hidden wells (reported, not used to choose anything).
- **Measure:** difference B − P1 per seed (same seed for both), its mean and a 95% interval (t-distribution, 9 degrees of freedom).
- **B is reliably better if** the mean hidden-well difference is ≥ +0.020 (the P2 margin) **and** its 95% interval excludes 0.
- **Otherwise:** the page and README say plainly that B's advantage over P1 is not separable from seed noise, while the P2 gate result stays as recorded.
- **Also reported:** each model's mean ± sd on hidden and open wells, the worst seed, and which hidden well drives the spread.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **10 seeds, paired by seed, hidden and open wells** | **Chosen** | Laptop cost about 1.5 hours; the interval half-width is then about 0.04 at sd 0.086 |
| Multi-seed cross-validation | Rejected for now | 5× the cost; CV chose the model, the question here is the hidden-well claim |
| 3 seeds | Rejected | Too few to estimate an interval |
| Average the 10 seeds into one ensemble model | Not now | A different model; would need its own pre-registration |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| Mean difference ≥ 0.02, interval excludes 0 | B's features and decision help beyond noise | Pages keep "B beats P1", now with an interval |
| Interval includes 0 | One seed could not separate them | Pages say so; a seed ensemble as a pre-registered follow-up |
| One hidden well drives most of the spread | The score depends on one unusual well | Report that well; per-well view on the page |

## Empirical results (2026-11-11)

Scores are FORCE penalty scores: 0 is perfect, higher (less negative) is better. Source: `data/outputs/p2c_multi_seed.json`.

| Measure | P1 | B | B − P1 (95% interval) |
|---|---|---|---|
| Hidden wells, mean ± sd over 10 seeds | −0.645 ± 0.112 | −0.511 ± 0.056 | **+0.134 (+0.055 to +0.213)** |
| Open wells, mean ± sd | −0.575 ± 0.007 | −0.523 ± 0.005 | +0.053 (+0.046 to +0.059) |
| Worst seed, hidden wells | −0.743 (seed 3) | −0.666 (seed 2) | |
| Seeds where B wins (hidden; open) | | | 10 of 10; 10 of 10 |

- **Rule met:** mean difference +0.134 ≥ +0.020 and the interval excludes 0, so B is reliably better than P1.
- **One well drives the spread:** across seeds, well 17/4-1's score has sd 0.74 (P1) and 0.39 (B); every other hidden well stays within 0.08.
- **P1's hidden score has two modes:** about −0.51 or about −0.73, depending on 17/4-1. Seed 42 fell in P1's good mode, so P2's +0.036 understated B's lead.
- **Caveat:** with two modes, the t-interval is approximate. Also reported, not pre-registered: B wins all 10 paired seeds (sign test p = 0.002).
- **Pages:** "B beats P1" stays, now with the interval; the seed caveat now names 17/4-1.

## Related Decisions

- ADR-002 (gates, seed-spread note), ADR-004 (P1 and B settings), ADR-008 (seed spread found in P6)
