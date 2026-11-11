# Changelog

Newest first. Each entry uses STAR (Situation, Task, Action, Result) so it can be told as a story.

## [0.11.0] — 2026-11-11 — Public API and remote MCP, prompt-injection tests, GenAI traces
**Files:** src/serving/public.py, src/serving/telemetry.py, src/serving/tools.py, src/serving/notes.py, scripts/build_deploy.py, scripts/trace_notes.py, deploy/, tests/test_safety_and_traces.py, data/outputs/traces_*.json*, docs/adr/ADR-011
- **Situation:** P5's tools ran only on a laptop; the portfolio rules now require free hosting, CI/CD and a technology assessment (R19–R21).
- **Task:** A public, read-only API and MCP endpoint that never spends tokens, defended against prompt injection and traced to standard conventions.
- **Action:**
  - Stateless MCP (2026-07-28 spec) beside the REST tools; cached notes served without a key; a checksummed 0.5 MB deploy bundle.
  - Tools accept identifiers only and never echo other input; the model sees store facts only.
  - OpenTelemetry GenAI spans (`execute_tool`, `notes.explain`, `chat`) with tokens and cost.
- **Result:** 20 of 20 injection attempts refused, none echoed; 20 of 20 live calls traced, span cost equal to meter cost ($0.065 per 1,000 notes, p95 4.9 s).
- **Talking point:** The tests caught that the MCP library would have rejected every request on the public host; it now allows only the deployment's own hostnames.

## [0.10.0] — 2026-11-09 — P6 Databricks: parity failed, explained; registry and yearly job passed
**Files:** databricks.yml, scripts/databricks_p6.py, scripts/databricks_prepare_inputs.sh, scripts/p6_drift_reference.py, scripts/p6_seed_spread.py, src/quality.py, data/outputs/p6_*.json, docs/adr/ADR-008
- **Situation:** ADR-008 required Databricks to reproduce model B's hidden-well score to three decimals, register the models, and run a yearly quality and drift job.
- **Task:** Same code as the laptop on serverless compute; Kansas lithology no longer served (amendment 1).
- **Action:**
  - Parity trained B on Databricks: −0.486 vs −0.504. Ruled out versions (pinned rerun), processor family, threads and duplicates; features were bit-identical.
  - Measured B's own seed spread on the laptop: −0.482 to −0.666 (sd 0.086). The build difference acts like a seed change.
  - Registered B and T in Unity Catalog; Spark job measured the 2026 archive's quality and drift.
  - Fixed two bugs on the way: pandas 3 dropped the grouping column; equal-weight down-sampling changed drift bands.
- **Result:** parity **failed**; registry passed; quality matches the laptop to four decimals and drift bands match for all six inputs.
- **Talking point:** When the cloud score differed, I proved the inputs were bit-identical and showed the gap was smaller than the model's own seed noise.

## [0.9.0] — 2026-11-09 — P5 API, MCP tools, grounded copilot: passed
**Files:** src/serving/, scripts/p5_build_store.py, scripts/p5_eval_notes.py, tests/test_serving.py, tests/fixtures/store_small.json, configs/default_config.yaml, data/outputs/p5_notes_eval.json, docs/adr/ADR-007
- **Situation:** P3 failed, so serving Kansas lithology would ship known-poor predictions.
- **Task:** API, MCP tools and LLM notes on validated outputs only, within R13 budgets set from two earlier measurements.
- **Action:** One store for North Sea lithology (model B), Kansas quality (P4) and the transfer result; grader + template fallback reused from GEO-1; prompt v2 writes shares as percentages.
- **Result:** 22 contract tests; 60 live cases 100% grounded; $0.066 per 1,000 notes; p95 2.7–4.7 s live (budget 5 s); 0.04 ms cached: **passed**.
- **Talking point:** The copilot refuses to call a Kansas rock: it explains the well's log quality and why lithology is not validated there.

## [0.8.0] — 2026-11-08 — P4 log quality and drift: passed
**Files:** scripts/p4_quality.py, src/drift.py, tests/test_drift.py, data/outputs/p4_quality.json, docs/adr/ADR-006
- **Situation:** 28,906 Kansas LAS files from 1999–2026; nobody knew which wells a model could read.
- **Task:** Quality measures for ≥ 99% of readable files and drift for every archive year (ADR-006).
- **Action:** Streamed every file once: coverage, physical ranges, hole condition, model confidence; PSI by year vs earlier years and vs FORCE.
- **Result:** 99.92% of files (24,157 wells); gamma ray, neutron and density together cover a median 36% of depth (0% before 2012); neutron drifts in 9 of 17 years; every year alerts against FORCE: **passed**.
- **Talking point:** The quality scan explained the transfer failure: Kansas logs sit outside the North Sea training range in every year.

## [0.7.0] — 2026-11-08 — P3 Kansas transfer: failed; P5–P6 re-scoped
**Files:** docs/adr/ADR-005, scripts/p3_*.py, src/kansas.py, tests/test_kansas.py, data/outputs/p3_*.json, docs/adr/ADR-007, ADR-008
- **Situation:** A North Sea model and 28,906 unlabelled Kansas files; the only labels are geological.
- **Task:** Agreement ≥ 50% and lift ≥ 2 in 4 of 6 named units, designed before any prediction (ADR-005).
- **Action:** Pushed the test first; built a transferable model T (no position or stratigraphy; FORCE cost 0.168); scored 1,915 files; diagnosed the failure on log values.
- **Result:** 0 of 6 units: **failed**. Shales found (Heebner 90%) but lift < 2; carbonates read as sandstone (tighter than any North Sea limestone); evaporite intervals do not read as evaporites. Transfer claim withdrawn; P5–P6 serve validated outputs only.
- **Talking point:** I let geology refute my model, then showed exactly why: old Kansas carbonates look like North Sea sandstone on gamma ray.

## [0.6.0] — 2026-11-08 — P2b method comparison and the finalists' methods
**Files:** docs/adr/ADR-009, scripts/p2b_lightgbm_fair.py, scripts/p2b_cnn.py, configs/force2020_finalists.json, data/outputs/p2b_*.json, docs/adr/ADR-004
- **Situation:** P2 tested only trees, LightGBM had diverged, and no deep model was tested.
- **Task:** A fair LightGBM and a 1D CNN under P2's rules, pre-registered; B kept unless beaten by ≥ 0.02 in CV.
- **Action:** C2 = LightGBM with XGBoost's leaf limit; D = 1D CNN over ±2.4 m windows on the Apple GPU; documented all 13 finalists' methods from the organisers' retrospective and code.
- **Result:** C2 CV −0.679 (level with XGBoost); D CV −0.944 (far behind); B stays. 11 of 12 in-range finalists used tree ensembles; none of the top three used the penalty matrix in training.
- **Talking point:** One matched safeguard took LightGBM from collapse to parity, and a CNN confirmed what the 2020 competition found: trees with context win on 98 wells.

## [0.5.0] — 2026-11-07 — Pages live; share previews
**Files:** docs/index.html, docs/build.html, docs/data/page_data.js, docs/assets/, scripts/export_page_data.py, tests/browser/hover_test.js, tests/browser/preview.js, configs/force2020_finalists.json, Makefile
- **Situation:** P0–P2 results existed only as JSON files and ADR tables.
- **Task:** A results page a hiring team reads in about two minutes (R12) and a walkthrough for technical reviewers (R14), every number traced to a result file (R17), with a LinkedIn preview (R18).
- **Action:** One exporter writes all page numbers; results page in R12 order with a rock-column viewer, a review-budget dial and a finalists chart; walkthrough on the shared phase engine; browser tests in light, dark and phone modes.
- **Result:** Both pages live on GitHub Pages; every chart hoverable and keyboard-focusable.
- **Talking point:** The page shows a petrophysicist what they would actually open: the rock column of a well they never trained on.

## [0.4.0] — 2026-11-07 — P2 model choice: passed
**Files:** scripts/p2_model_choice.py, scripts/p2_lgb_diagnostic.py, src/features.py, tests/test_features.py, data/outputs/p2_model_choice.json, data/outputs/p2_lgb_diagnostic.json, docs/adr/ADR-002, ADR-004
- **Situation:** P1 sat 0.014 below the finalists; ADR-004 had named three candidates before any ran.
- **Task:** Choose by 5-fold well-grouped CV on training wells only; the choice must beat P1 by ≥ 0.02 on the hidden wells and also on the open wells.
- **Action:**
  - Ran A (engineered features), B (A + expected-penalty decision) and C (LightGBM).
  - First run died when the laptop slept; re-run kept awake. A CV fold without basement samples crashed the next run; probabilities are now placed into all 12 classes by label (tested).
  - C collapsed; a training-wells-only diagnostic traced it to LightGBM's loose leaf safeguard (raw scores up to 1.4M).
- **Result:**
  - Chosen B: hidden −0.504 (+0.036 vs P1), open −0.521 (+0.064): **passed**. Would rank 4th of the 13 finalists.
  - Features carry the gain (A +0.031); the decision rule adds +0.005.
  - 79.4% of hidden-well depth labelled as the interpreter did (P1: 77.7%).
- **Talking point:** My pre-named model cleared its bar by 0.036 on unseen wells and would have placed 4th in the 2020 competition; when one candidate collapsed, I found why instead of dropping it.

## [0.3.1] — 2026-11-07 — Rules audit before P2 results
**Files:** docs/adr/ADR-001…004, docs/references.yaml, scripts/evidence.py, scripts/reference_floors.py, pyproject.toml, .github/workflows/ci.yml, Makefile, requirements.txt, CHANGELOG.md
- **Situation:** P1 had run and P2 was running; the documents had not been checked against portfolio rules R1–R17.
- **Task:** Find every rule gap and wrong fact, and fix it before P2's result could colour the fixes.
- **Action:**
  - Facts checked at the source: 13 finalists' code ran (12 within −0.469 to −0.526, one at −0.944); LAS 2.0 dates to 1992 with a July 2009 update, not 2017; Kansas zips are 8.9 GB (8.3 GiB).
  - Reading aids added (R17): "shale everywhere" floors per split and logged metres (`reference_floors.json`).
  - R2: OpenAlex evidence tables in every ADR; ADR-004 gained its rejected options (documentation only).
  - Deviations logged in ADR-002: candidate A builds bad-hole size but no flag; ADR-003 E5 phase corrected.
  - Data: 1,633 Kansas header longitudes missing their minus sign restored to west (tested); 24,165 of 24,166 located wells now map inside Kansas.
  - Engineering: ruff lint in CI; Makefile pipeline targets that were listed but missing.
- **Result:** 13 fixes (incl. this missing P0 entry; a curve count that included depth channels: 373,791 curve entries, not 402,583; and 1,633 Kansas headers whose longitude lacked its minus sign); no pre-registered decision changed; lint and 8 tests pass.
- **Talking point:** I audited the write-up against the rules while the model was still training, so nothing could be bent to fit the result.

## [0.3.0] — 2026-11-07 — P1 baseline: failed by 0.014
**Files:** scripts/p1_baseline.py, src/features.py, tests/test_features.py, data/outputs/p1_baseline.json
- **Situation:** ADR-004 fixed an XGBoost baseline in advance; the gate was the 2020 finalists' range (≥ −0.526 on the hidden wells).
- **Task:** Train once on the 98 training wells, score the open and hidden wells once, measure the random-split leak.
- **Action:** Fitted the pre-registered model (no tuning on test wells). After the miss, checked the pipeline as ADR-002 requires: stratigraphy names, class mapping, null codes. No fault found.
- **Result:**
  - Hidden test −0.540 (gate −0.526): **failed**; open test −0.585; 77.7% of hidden depth samples labelled correctly.
  - The same model on a random 80/20 sample split scores −0.171, about 3× better than on blind wells: the leak ADR-001 warned about.
  - Penalty score: the average cost of a mistake per depth sample; 0 is perfect, "shale everywhere" scores −1.308.
- **Talking point:** My baseline missed competition level by 0.014 and I reported it, then showed a random split would have flattered it threefold.

## [0.2.0] — 2026-10-15 — P0 data foundation: passed
**Files:** scripts/force_ingest.py, scripts/kgs_inventory.py, scripts/p0_report.py, src/las_header.py, src/curves.py, tests/test_las.py, docs/adr/ADR-004
- **Situation:** Two sources: FORCE 2020 (official splits, penalty matrix) and 28,906 Kansas LAS files inside yearly and nested zips.
- **Task:** Reproduce the official splits exactly; read ≥ 99% of Kansas headers (ADR-002 P0).
- **Action:** Ingested the official splits with count checks; parsed every LAS header in parallel without unzipping to disk; built a curve-name dictionary; pre-registered ADR-004 before P1.
- **Result:** Splits exact (98 / 10 / 10 wells); 99.86% of Kansas headers read (41 files lack a curve section); the dictionary recognises 84.1% of 373,791 curve entries (depth channels excluded).
- **Talking point:** Before modelling I proved the data matched the published competition to the last sample.

## [0.1.0] — 2026-10-15 — Design before analysis
**Files:** docs/PRD.md, docs/adr/ADR-001, ADR-002, ADR-003, docs/adr/README.md, configs/default_config.yaml, Makefile, requirements.txt, LICENSE, .github/workflows/ci.yml
- **Situation:** A public archive of ~28,900 Kansas LAS files and 118 labelled North Sea wells; no lithology for Kansas.
- **Task:** Fix the question, the evaluation unit and every phase's gate before touching the data.
- **Action:**
  - ADR-001: blind wells and the official penalty score; Kansas judged against geology.
  - ADR-002: gates P0–P7, with P1 set at the 2020 finalists' range.
  - ADR-003: ten petrophysics expectations with primary sources.
- **Result:** Design pushed before any analysis.
- **Talking point:** I wrote down how every phase would be judged before I opened the data, so no result could move the goalposts.
