# Changelog

Newest first. Each entry uses STAR (Situation, Task, Action, Result) so it can be told as a story.

## [0.1.0] — 2026-10-15 — Design before analysis
**Files:** docs/PRD.md, docs/adr/ADR-001, ADR-002, ADR-003, docs/adr/README.md, configs/default_config.yaml, Makefile, requirements.txt, LICENSE, .github/workflows/ci.yml
- **Situation:** A public archive of ~28,900 Kansas LAS files and 118 labelled North Sea wells; no lithology for Kansas.
- **Task:** Fix the question, the evaluation unit and every phase's gate before touching the data.
- **Action:**
  - ADR-001: blind wells and the official penalty score; Kansas judged against geology.
  - ADR-002: gates P0–P7, with P1 set at the 2020 finalists' range.
  - ADR-003: ten petrophysics expectations with primary sources.
- **Result:** Design pushed before any analysis.
