# ADR-012: Agent Skill for Lithology Answers (R24)

**Status:** Accepted
**Date:** 2026-11-17
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- The public API and MCP (ADR-011) serve four tools, but an agent does not know when to use them or how to read their numbers.
- Easy misreadings:
  1. The blind score is a penalty: 0 is perfect and more negative is worse; it is per 0.152 m sample on wells never seen.
  2. `hidden` wells are the final judge; `open` wells are a second check.
  3. A Kansas quality answer is not a lithology answer: Kansas lithology is not validated (ADR-005 failed).
  4. A Kansas unit passes only with 30+ wells, median agreement ≥ 50% and lift ≥ 2; high agreement alone (Heebner, 90%) is not a pass.
- **Question:** how can any agent answer lithology questions correctly, with proof?

## Decision

- `skills/well-log-lithology/`: `SKILL.md` (trigger description, workflow, reading rules, answer structure, limits), `scripts/wll.py` (standard library, Python 3.8+, one retry, ids URL-quoted, 404 as data), `scripts/charts.py` (a strip log with conventional lithology colours, a probability track and doubtful intervals hatched; Kansas unit bars against the 50% pass line), `references/charts.md`.
- `evals/`: four tasks in the `claude plugin eval` layout (a FORCE well's column, a Kansas well's quality, two Kansas units, an unserved well) with 15 graders; `trigger-evals.json` with 10 should-trigger and 10 near-miss prompts.
- CI: `tests/test_skill_client.py` (offline), a Python 3.8 syntax check of `skills/`, and `scripts/skill_live_check.py` after every deploy.

## Empirical Results (2026-11-17, iteration 1)

- **20 of 20** checks pass, verified by script against the live API (`grade.py` reads every figure from the API, not from the answer).
- Found while writing (R23): two claims of mine were not in any tool result and were corrected before grading. The doubtful beds at 2,800–2,900 m in 15/9-23 are mainly marl (not sandstone). The Hutchinson Salt miss is explained in ADR-005 by logs that do not read as salt (median density 2.60 vs about 2.03 for halite), not by missing training data.
- One format miss in the first run (a two-sentence headline) was fixed.
- Runs were done by the session that wrote the skill, so there is no independent no-skill baseline yet; `claude plugin eval` gives one.

## Consequences

- **Positive:** an agent answers with the score's meaning, the review targets and the Kansas caveat; the live check fails if a grader fact changes.
- **Negative:** the skill serves only the 20 FORCE test wells; Kansas answers stay at log quality until a transfer passes.
