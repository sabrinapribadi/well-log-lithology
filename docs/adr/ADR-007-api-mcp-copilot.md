# ADR-007: P5 Lithology API, MCP Tools and a Grounded Geologist Copilot

**Status:** Accepted — written and pushed before P5 is built
**Date:** 2026-11-08
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- A petrophysicist wants a well's lithology column, its doubtful intervals and its log quality, without running code.
- An AI assistant (copilot) should answer the same questions through typed tools, never by inventing numbers.
- **ADR-002 gate (P5):** API and MCP contract tests pass; LLM explanations grounded in tool results; cost and latency within R13 budgets.

## Decision Drivers

- One serving store feeds the API, the MCP tools and the notes, so every answer comes from the same numbers.
- Budgets are set from two earlier measurements with the same provider and model (portfolio projects GEO-1 and CHN-1), not hoped for.
- No key, no outage, no invented number: a deterministic template note is always available.

## Decision (pre-registered)

### 1. Serving store (built from P2–P4 outputs; no model at request time except `/predict`)

- Per scored Kansas well: lithology intervals (run-length), top-class probability, low-confidence intervals, P4 quality row, P3 unit agreement where the well has a top.
- Per FORCE hidden well: chosen model B's column and blind score.

### 2. API (FastAPI) and MCP tools (same functions)

| Endpoint / tool | Returns |
|---|---|
| `GET /wells/{id}/lithology` · `predict_lithology(well_id)` | Intervals with rock, top and base (m), probability; share of each rock |
| `GET /wells/{id}/quality` · `well_quality(well_id)` | P4 measures and flags |
| `GET /units/{unit}` · `unit_agreement(unit)` | P3 agreement and lift for a named Kansas unit |
| `POST /predict` (LAS upload, ≤ 20 MB) | Model T's lithology curve as LAS 2.0 |
| `GET /wells/{id}/note` · `explain_well(well_id)` | A short note on the column, its doubtful intervals and quality |

- Contract tests: schema, status codes, unknown well → 404, LAS round trip.

### 3. Notes (the copilot's explanations)

- **Facts only from the store:** the prompt holds the well's facts as a list; the note may only restate them.
- **Grader (reused from GEO-1):** every number in a note must match a fact to two significant figures, sign-aware; names must appear in the facts. A note that fails is replaced by the template.
- **Provider:** OpenAI behind one config line; model `gpt-6-luna`, no reasoning effort, ≤ 200 output tokens. Prices read from the vendor's official pricing page at build time, dated in config.

### 4. Budgets (R13)

| Budget | Value | Basis |
|---|---|---|
| Cost per 1,000 live notes | ≤ $0.20 | GEO-1 measured $0.064, CHN-1 $0.05 |
| p95 latency, live note | ≤ 5,000 ms | GEO-1 measured 4,166 ms, CHN-1 3,600 ms; a 3,000 ms budget failed twice |
| p95 latency, cached note or API read | ≤ 50 ms | Store lookups |
| Cost levers | Notes precomputed and cached for every scored well; template fallback; smallest model that passes | R13 |

### 5. Gate

- Contract tests pass in CI (template mode, no key needed).
- ≥ 60 live evaluation cases: **served** notes 100% grounded; live drafts' pass rate reported.
- Measured cost and p95 latency within the budgets above.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **Typed tools + grounded notes with template fallback** | **Chosen** | Same pattern passed grounding in two earlier projects |
| Free-text chat over raw LAS files | Rejected | Numbers cannot be traced; costly |
| Multi-agent copilot (quality agent + interpretation agent) | Deferred | Typed tools answer the current questions; a second agent adds cost and failure modes without a question that needs it |
| Fine-tuned LLM | Rejected | No labelled explanation data; grounding is the real risk |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| Live drafts often fail the grader | Prompt or facts unclear | Fix prompt; served notes stay grounded via the template |
| p95 above 5 s | Provider latency | Report; serve cached notes (as GEO-1) |
| Cost above budget | Prompt too long | Shorten facts; cache |

## Consequences

- **Positive:** answers are traceable to the same store the pages use.
- **Negative:** notes are only as good as P3–P4; they explain the model, they do not interpret the rock independently.

## Related Decisions

- ADR-002 (P5 gate), ADR-005 (Kansas predictions), ADR-006 (quality measures)
