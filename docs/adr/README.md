# Architecture Decision Records

| ADR | Decision | Status | Summary |
|---|---|---|---|
| [ADR-001](ADR-001-framing-and-evaluation-unit.md) | Framing, evaluation unit and scale | Accepted | Blind wells (official FORCE splits) and the official penalty score; Kansas judged against geology; R15 volumes measured. |
| [ADR-002](ADR-002-validation-and-gates.md) | Validation and gates for every phase | Accepted | Gates P0–P7 fixed before analysis; P1 at competition level (≥ −0.526); P2 +0.02 on hidden wells. |
| [ADR-003](ADR-003-industry-alignment.md) | Industry alignment (R16) | Accepted | Ten petrophysics expectations (classes, blind wells, LAS standard, curve names, QC, normalisation, tops, uncertainty, deliverables, cadence). |
| [ADR-004](ADR-004-baseline-and-model-choice.md) | P1 baseline and P2 model choice | Accepted | XGBoost baseline fixed in advance; three candidates (engineered features, expected-penalty decision, LightGBM) chosen by well-grouped CV; winner scored once on hidden wells. Results: P1 failed (−0.540); P2 passed with B (−0.504, +0.036). |
| [ADR-005](ADR-005-kansas-transfer-test.md) | P3 Kansas transfer test | Accepted | Six named units with expected rock from KGS sources; transferable model T (no position or North Sea stratigraphy); agreement ≥ 50% and lift ≥ 2 in 4 of 6 units; written before any Kansas prediction. |
| [ADR-006](ADR-006-log-quality-and-drift.md) | P4 log quality and drift | Accepted | Per-file coverage, physical ranges, bad hole, model confidence; PSI by archive year (bands 0.10 / 0.25); gate: ≥ 99% of readable files and every year. |
| [ADR-007](ADR-007-api-mcp-copilot.md) | P5 API, MCP tools, grounded copilot | Accepted | One store for API, MCP and notes; grader + template fallback; budgets $0.20 per 1,000 notes, p95 5 s live, 50 ms cached. |
| [ADR-008](ADR-008-databricks-job.md) | P6 Databricks job | Accepted | Parity of B to three decimals, Unity Catalog registry, Spark scoring of the newest archive, PSI drift; yearly schedule paused on Free Edition. |
