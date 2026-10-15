# Architecture Decision Records

| ADR | Decision | Status | Summary |
|---|---|---|---|
| [ADR-001](ADR-001-framing-and-evaluation-unit.md) | Framing, evaluation unit and scale | Accepted | Blind wells (official FORCE splits) and the official penalty score; Kansas judged against geology; R15 volumes measured. |
| [ADR-002](ADR-002-validation-and-gates.md) | Validation and gates for every phase | Accepted | Gates P0–P7 fixed before analysis; P1 at competition level (≥ −0.526); P2 +0.02 on hidden wells. |
| [ADR-003](ADR-003-industry-alignment.md) | Industry alignment (R16) | Accepted | Ten petrophysics expectations (classes, blind wells, LAS standard, curve names, QC, normalisation, tops, uncertainty, deliverables, cadence). |
| [ADR-004](ADR-004-baseline-and-model-choice.md) | P1 baseline and P2 model choice | Accepted | XGBoost baseline fixed in advance; three candidates (engineered features, expected-penalty decision, LightGBM) chosen by well-grouped CV; winner scored once on hidden wells. |
