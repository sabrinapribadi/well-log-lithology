# Changelog

Newest first. Each entry uses STAR (Situation, Task, Action, Result) so it can be told as a story.


## [0.21.0] — 2026-11-19 — P3c result: failed, 2 of 6 Kansas units (ADR-014); no further rules on formation tops
**Files:** docs/adr/ADR-014-p3c-combined-arm-retest.md, docs/adr/README.md, data/outputs/p3c_test.json, data/outputs/p3b_dev_posthoc.json, data/outputs/p3b_test_posthoc.json, docs/index.html, docs/build.html, docs/brief.yaml, docs/data/page_data.js, docs/PRD.md, README.md, scripts/export_page_data.py, app/streamlit_app.py, tests/test_streamlit_app.py, tests/browser/build_test.js, src/serving/contracts.py, skills/well-log-lithology/SKILL.md, skills/well-log-lithology/scripts/wll.py
- **Situation:** P3c was pre-registered (commit c88b270) with the combined arm M3, a new fresh set of 589 files and a written forecast of 3 or 4 units.
- **Task:** Score M3 once on the new wells and report the result as it falls, including a run that was interrupted.
- **Action:** Informational M3 runs on the two sets already seen (development 2 of 6, P3b test 3 of 6; every other arm reproduced its committed numbers). The first one-shot attempt stopped after 170 of 589 files with no score written; it was logged and rerun as the ADR allows (589 files, 0 read errors, manifest hash checked).
- **Result:** P3c failed: M3 passed 2 of 6 (Heebner, Stone Corral), exactly the control's 2. P3b's Cherokee pass (50.2%) did not replicate (47%, lift 1.83); Arbuckle reached 28% because the model's carbonate errors are not all "sandstone"; Lansing-Kansas City failed on lift (1.40) as forecast. Only the training-free physics rules pass the Arbuckle on both fresh sets (61%, 51%). Per ADR-014, no more rules are tried on Kansas formation tops; the next step needs core-based labels. Results page, walkthrough (10th phase), app, API caveat, skill, brief, README and PRD updated.
- **Talking point:** "Three pre-registered Kansas tests, three honest failures; the third showed that an attractive post-hoc fix adds nothing on new wells, and named what would: real labels."

## [0.20.0] — 2026-11-18 — P3c pre-registered: combined physics + model arm on new fresh wells (ADR-014)
**Files:** docs/adr/ADR-014-p3c-combined-arm-retest.md (new), docs/adr/README.md, scripts/p3b_select_fresh.py, scripts/p3b_score.py, data/outputs/p3c_test_manifest.json, docs/references.yaml, data/outputs/references_evidence.json, README.md
- **Situation:** P3b failed at 3 of 6 units, but its arms failed in different places: the physics rules recognise the carbonates, the physics-feature model the shale and anhydrite. Combining them was thought of only after the P3b test set was seen.
- **Task:** Test the combination fairly, on wells no earlier test had used, with the rule and the pass bar fixed first.
- **Action:** Arm M3 written as one line with no free parameter (M1a, except where it says sandstone and the physics rules say limestone or dolomite). New fresh set: 589 files, seed 2027, excluding all 2,515 wells scored in P3 and P3b, SHA-256 recorded and checked by the scorer. The selection script's P3b output was checked to stay byte-identical. Expectations per unit written down before scoring; two new sources verified on OpenAlex.
- **Result:** Pre-registration pushed before any M3 score exists. Hutchinson Salt has no wells left, so M3 needs 4 of the other 5 gated units; the ADR expects 3 or 4, with the Lansing-Kansas City likely failing on lift.
- **Talking point:** "An idea born from looking at test results gets a new test set, and its expected outcome is written down before the run."

## [0.19.0] — 2026-11-18 — Reader erratum carried through: Kansas log quality recounted (ADR-006); P3b on the results page, app, API and skill
**Files:** docs/adr/ADR-006-log-quality-and-drift.md, docs/adr/README.md, data/outputs/p0_foundation.json, data/outputs/p4_quality.json, data/outputs/kgs_wells_summary.json, deploy/serving_snapshot.tar.gz, deploy/serving_snapshot.sha256, docs/index.html, docs/build.html, docs/brief.yaml, docs/data/page_data.js, docs/PRD.md, README.md, scripts/export_page_data.py, app/streamlit_app.py, tests/test_streamlit_app.py, tests/browser/build_test.js, src/serving/contracts.py, skills/well-log-lithology/SKILL.md, skills/well-log-lithology/scripts/wll.py
- **Situation:** The P3b reader fix (a density correction, `RHOC`, read as density) also touched the archive-wide inventory and log-quality figures published since P0 and P4, and P3b's result was only in its ADR.
- **Task:** Recount every figure the fix could move, publish the corrections next to the originals, and show P3b wherever the Kansas result appears, keeping "not validated".
- **Action:** Reran the inventory, the P0 report and P4 on all 28,906 files (2 h 06 min); wrote an erratum to ADR-006 with a before/after table; rebuilt the serving store, deploy snapshot and page data; checked that the P3b test set rebuilt from the new inventory has the same SHA-256. Added P3b to the results page (a line and a collapsed per-method table), the walkthrough (a phase entry), the app's Kansas page, the API caveat, the agent skill, the brief, README and PRD.
- **Result:** Hole condition is now knowable for 46.6% of files (was 9.4%), and where knowable the median bad-hole share is 12.8% (was 5.5%). Files with gamma ray, density and neutron: 54.6% (was 58.3%); mapped wells holding gamma ray plus density or neutron: 59% (was 63%). Density drift alerts against FORCE: 16 of 18 years (was 17). Coverage (36%), wells (24,157), the map (24,166 wells) and the P0 and P4 gates are unchanged. 60 Python tests, 390 walkthrough and 121 results-page checks pass; the results page stays at 7.2 screens.
- **Talking point:** "When a bug turned up mid-project, we recounted every number it touched and published the corrections next to the originals."

## [0.18.0] — 2026-11-18 — P3b result: failed, 3 of 6 Kansas units (ADR-013)
**Files:** docs/adr/ADR-013-p3b-kansas-retest.md, docs/adr/README.md, README.md, data/outputs/p3b_test.json
- **Situation:** P3b was pre-registered (commit c609433) and its M1 variant frozen on the development set (commit 6a1bff8) before the fresh test set was opened.
- **Task:** Score every arm once on the 601 fresh files and report the result as it falls.
- **Action:** Manifest hash checked before reading; five arms scored under the original and the amended gate; 0 read errors.
- **Result:** Primary arm (physics-feature XGBoost, amended gate) passed 3 of 6 units (Heebner, Cherokee, Stone Corral); 4 were needed, so the transfer claim stays withdrawn. The control already passes 2 with the reader fix and amended gate. Training-free physics rules reach 61–71% agreement in the Arbuckle and Lansing-Kansas City where every North Sea-trained arm stays at 0–2%, and pass 3 units themselves. No arm reaches 4; combining arms after the test is not done.
- **Talking point:** "A pre-registered retest moved Kansas from 0 to 3 of 6 units and showed exactly why the rest fail: North Sea training cannot recognise tight carbonates, while basin-independent physics can."

## [0.17.0] — 2026-11-18 — P3b pre-registered: reader erratum, diagnostics, amended gate, fresh test set (ADR-013)
**Files:** docs/adr/ADR-013-p3b-kansas-retest.md (new), src/curves.py, src/kansas.py, scripts/p3b_diagnostics.py (new), scripts/p3b_select_fresh.py (new), scripts/kgs_inventory.py, tests/test_kansas.py, docs/references.yaml, data/outputs/p3b_diagnostics.json, data/outputs/p3b_test_manifest.json, data/outputs/references_evidence.json
- **Situation:** P3 failed (0 of 6 Kansas units). A literature and data review found no open labelled Kansas or carbonate set and no published FORCE-to-other-basin lithology study, but basin-independent mineral physics that targets the documented failure.
- **Task:** Pre-register a fair retest before any new model touches Kansas data, without moving the goalposts.
- **Action:** Verified all 24 identifiers in the review against OpenAlex or arXiv (one unindexed preprint moved to the ADR's grey-literature list) and added 25 sources to `references.yaml`. Model-free diagnostics of the 1,915 development files found a reader bug: `RHOC`, usually the density correction in KGS files, was read as bulk density (about 10% of P3 wells per unit); fixed with a description rule and a physical-plausibility check, with a regression test. ADR-013 fixes an amended gate (sample quality; lift against 30 m of neighbours) next to the original, four arms (control, physics rules, physics-feature XGBoost, plus label-shift correction), the primary result, and a fresh one-shot test set of 601 files (SHA-256 recorded).
- **Result:** Pre-registration pushed before any P3b model was evaluated. The Hutchinson Salt logs do not read as salt and only 10 fresh wells exist, so it is expected to fail; P3b needs 4 of the other 5 gated units. P3's result stands as reported.
- **Talking point:** "Before retesting, we fixed the test: a model-free check found the reader feeding a density correction as density in one well in ten."

## [0.16.0] — 2026-11-18 — App template v2: sidebar pages, Explore the data, a business question per page
**Files:** app/streamlit_app.py, app/frame.py (new, shared), tests/test_streamlit_app.py, README.md
- **Situation:** The user wanted every Streamlit app to combine the older dashboards' structure (sidebar pages: a real use case, EDA, an AI assistant; a business question on every view) with the newer apps' 5W1H brief and KPI first screen.
- **Task:** Rebuild this app on one shared template (R26 item 8) and check every page against the data before release.
- **Action:** Six pages (Overview, Explore the data, Review a well, Check a Kansas log, Kansas transfer test, AI Assistant) on the shared `frame.py`; a new EDA page from committed results (FORCE rock mix and missing logs, Kansas coverage by archive year, the wells map with filters); each page's answer computed from the data (e.g. where to review first in a well, which bars the closest Kansas unit missed).
- **Result:** 8 app tests pass (every page, navigation, deep links, frame checksum). Checking the pages fixed a rock legend overlapping the next column and a 'core logs' count that included the caliper.
- **Talking point:** "Every portfolio app now reads the same way: what it is for, the data, the use case, then an assistant; and every page answers a business question from the data."

## [0.15.1] — 2026-11-18 — App live on Streamlit; Databricks app start retried in CD
**Files:** docs/brief.yaml, README.md, docs/index.html, docs/build.html, .github/workflows/ci.yml
- **Situation:** The companion app was deployed on Streamlit Community Cloud, unlinked; the Databricks CD job failed twice on 2026-11-17 at app start ("Cannot create Databricks App, please try again later") while every other job passed.
- **Task:** Link the live app; keep a passing platform hiccup from failing the pipeline.
- **Action:** App link in the brief and README; started the stopped app by hand and re-ran the job (passed, so the error was transient on the Databricks side, not the bundle); the start step now retries twice, a minute apart.
- **Result:** Live app linked from every brief; CI fully green again.

## [0.15.0] — 2026-11-18 — Streamlit companion app with the agent chat (R26)
**Files:** app/streamlit_app.py, app/wl_data.py, app/agent_tools.py, app/agent.py and app/chat.py (shared with the other portfolio apps), app/replays.json, app/requirements.txt, .streamlit/config.toml, scripts/record_agent_replays.py, tests/test_streamlit_app.py, tests/fixtures/app_api.json (all new), .github/workflows/ci.yml, README.md
- **Situation:** The results page is static and LinkedIn previews a Streamlit app; the project had no interactive surface and no way to show its tools working with a model.
- **Task:** Build the R26 app: brief and results first, only what a static page cannot do, no keys, tested in CI.
- **Action:** Four lazy tabs (a well's strip log and review list, the Kansas transfer by unit, the Kansas archive on a map with a quality lookup, the agent chat); the agent's tools give it a summary and the thickest doubtful intervals, and the pass rule, so every number it states is checkable; 8 answers recorded on the public API.
- **Result:** 8 of 8 recorded answers pass the number check; about $0.21 per 1,000 questions. Found on the way: the shared chat engine dropped a tool call's arguments when the tool failed (fixed in all five apps), and the agent printed fractions instead of percentages (instructions fixed).
- **Talking point:** "A geologist can open any blind well, see the thickest doubtful intervals first, and ask the agent why Kansas is not validated."

## [0.14.0] — 2026-11-17 — Agent skill for lithology answers (R24)
**Files:** skills/well-log-lithology/ (new), tests/test_skill_client.py (new), scripts/skill_live_check.py (new), .github/workflows/ci.yml, docs/adr/ADR-012-agent-skill.md (new), docs/adr/README.md, docs/brief.yaml, scripts/brief.py, README.md, docs/index.html, docs/build.html
- **Situation:** The API and MCP were live, but an agent could misread the blind score (a penalty, 0 is perfect), mix open and hidden wells, or answer Kansas questions with an unvalidated rock column.
- **Task:** Ship an evaluated agent skill under R24, with the portfolio's answer structure.
- **Action:** Reading rules, a strip-log chart and Kansas unit bars, four eval tasks with 15 graders, 20 trigger prompts; offline client test, Python 3.8 syntax check and a live check after every deploy.
- **Result:** 20 of 20 checks pass against the live API; two claims corrected while writing (R23).
- **Talking point:** "The skill shows a geologist where to look first on a blind well, and refuses to give a Kansas rock column the model has not earned."

## [0.13.0] — 2026-11-11 — Hiring-team brief (R22), rules audit fixes, Databricks App
**Files:** docs/brief.yaml, scripts/brief.py, README.md, docs/index.html, docs/build.html, docs/PRD.md, docs/adr/README.md, docs/adr/ADR-011, scripts/build_deploy.py, databricks.yml, .github/workflows/ci.yml, tests/browser/*.js
- **Situation:** A rules audit found gaps: browser tests not in CI, Pages publishing without a gate, no free-tier notes, an unbumped PRD, no ADR dependency tree, long paragraphs; hiring teams had no one-glance summary.
- **Task:** Fix every gap and put a 5W1H brief first on the README and both pages, with no repeated content.
- **Action:** One brief source written into all three by script and checked in CI; removed the lede, intro bullets, status chips and repeated figures; browser tests now run in CI and fail on errors; Pages deploy only after tests; the API and MCP also run as a Databricks App from the bundle.
- **Result:** CI green with unit, browser and brief checks; 351 build-page and all hover checks pass; Databricks App answers REST and MCP behind workspace login.
- **Talking point:** "A hiring manager gets what, why, who, where, when it fails and how in six lines, each skill linked to its proof."

## [0.12.0] — 2026-11-11 — Multi-seed comparison: B reliably beats the baseline (ADR-010)
**Files:** scripts/p2c_multi_seed.py, data/outputs/p2c_multi_seed.json, scripts/export_page_data.py, docs/data/page_data.js, docs/index.html, docs/build.html, docs/adr/ADR-010, ADR-002, docs/PRD.md, README.md
- **Situation:** P2's +0.036 over the baseline came from one seed, and P6 showed seed noise up to 0.18.
- **Task:** Settle whether B beats P1 beyond seed noise, with the rule fixed before the runs (ADR-010).
- **Action:** Retrained P1 and B on seeds 0–9 with identical settings; paired the hidden-well scores by seed; traced the spread to single wells.
- **Result:** B wins all 10 seeds: +0.134 on average (95% interval +0.055 to +0.213), so the rule is met. Well 17/4-1 drives the spread; seed 42 was a good draw for P1, so P2 understated B's lead.
- **Talking point:** "One seed said the gain was within noise; ten paired seeds showed it was four times larger, and named the one well causing the noise."

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
