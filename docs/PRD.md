PRODUCT REQUIREMENT DOCUMENT (PRD)
Project: Well-Log Lithology — Does a North Sea Model Transfer to Kansas?
Version: 0.1 (design: framing, gates and industry alignment, before any analysis)
Author: Sabrina Pribadi
Date: October 15, 2026
Status: Active — design pushed; P0 next


1. EXECUTIVE SUMMARY

Problem: Petrophysicists label the rock type (lithology) at every depth of every well from its logs.
Done by hand across hundreds of wells, the picks are slow and inconsistent, and errors propagate
into reservoir and geological models. Public archives hold tens of thousands of wells that nobody
has the time to interpret.

Solution: A lithology model trained on 98 labelled North Sea wells (FORCE 2020), judged on wells it
never saw with the industry's own penalty for geologically "far" mistakes, then tested for transfer
to Kansas, where ~28,900 public LAS files have no lithology labels but do have formation tops.
Delivered as lithology curves per well, a well map, an API and AI tools, refreshed as new wells
arrive.

Value Proposition: Turn an archive of unread logs into first-pass lithology for every well, with
the uncertainty and the transfer limits stated.

Success Metrics (pre-registered — see ADR-002):
- P0: FORCE splits reproduced exactly; ≥ 99% of Kansas LAS headers readable and inventoried
- P1: XGBoost baseline within the 2020 finalists' range on hidden wells (penalty score ≥ −0.526)
- P2: chosen model beats P1 by ≥ 0.02 on hidden wells and also on the open test
- P3: Kansas predictions agree with known lithology of named units (designed before predicting)
- P4: per-well log-quality and drift measures for every Kansas well
- P5: API and MCP contracts and grounded LLM explanations pass in CI, within cost and latency budgets
- P6: Databricks reproduces the local score exactly; model registered; scheduled drift job
- P7: two live pages, browser-tested


2. PROJECT CONTEXT AND BACKGROUND

Portfolio project OG-2 (roles: Oil & Gas + MLOps). Skills shown:
1. Data engineering on heterogeneous files: ~28,900 LAS files with inconsistent mnemonics, units and null codes
2. Machine learning on well logs with blind-well evaluation and a domain penalty metric
3. Domain transfer: a model trained in one basin, tested in another against geological control
4. MLOps: quality monitoring across wells, model registry, scheduled scoring on Databricks
5. GenAI: a geologist copilot over typed tools, grounded and budgeted


3. SCOPE

In scope: FORCE 2020 (118 wells, Norwegian North Sea); Kansas Geological Survey LAS archive
(1999–2026), well list and formation tops; 12 FORCE lithology classes.

Out of scope: core or cuttings descriptions as labels; seismic; reservoir properties (porosity,
saturation); any operator's private data.


4. USER PERSONAS AND STORIES

| Persona | Need | Today |
|---|---|---|
| Petrophysicist | First-pass lithology for many wells, with doubtful intervals flagged | Manual picks well by well |
| Exploration geologist | Lithology consistent with formation tops across a region | Inconsistent picks between interpreters |
| Data manager | Clean, standardised curves from a messy LAS archive | Mnemonics and units differ per file |
| AI assistant | Typed tools: predict_lithology(well), explain(interval) | None |

User stories:
- As a petrophysicist, I load a LAS file and get a lithology curve with probabilities, as LAS.
- As a geologist, I see where the model agrees with formation tops and where it does not.
- As a data manager, I see which wells have which curves and how good they are.


5. FUNCTIONAL REQUIREMENTS

Module A: Data foundation — FORCE splits, Kansas LAS inventory, curve dictionary — ADR-001, ADR-003 (P0)
Module B: Blind-well baseline — ADR-002 (P1)
Module C: Model choice — ADR-004 (P2, written before P2)
Module D: Kansas transfer — P3 (ADR to be written before predicting)
Module E: Log quality and drift — P4
Module F: API, MCP tools, grounded explanations — P5
Module G: Databricks job, registry, drift — P6


6. NON-FUNCTIONAL REQUIREMENTS

- Reproducible: input fingerprints; one shared environment (`make env`)
- Runs on an 8 GB laptop for P0–P2; Spark on Databricks for the full Kansas curve set (P6)
- Public data only, licences checked at the source (CC BY 4.0; KGS terms of use)
- Pages readable in about two minutes; every number explained (R17)


7. DATA STRATEGY

| Source | Licence | Use |
|---|---|---|
| FORCE 2020 well log and lithofacies dataset (Zenodo 4351156) | CC BY 4.0 | Training and blind-well testing |
| FORCE 2020 competition repository (splits, penalty matrix, scoring code, results) | Published by the organisers | Exact splits, metric, benchmark |
| NPD lithostratigraphy (with FORCE 2020) | Norwegian licence for open government data | Geological context |
| Kansas Geological Survey LAS archive, well list, formation tops | Free use with citation (KGS terms) | Transfer test, inventory, monitoring |

Raw data lives in `WLL_DATA_DIR` (OneDrive `github_project/data/well-log-lithology`), never in the repository.


8. TECHNICAL ARCHITECTURE

1. Sources → `scripts/` ingestion (FORCE CSVs; Kansas LAS read inside the yearly and nested zips)
2. Local models (XGBoost, LightGBM) with well-grouped validation (P1–P2)
3. Outputs as small JSON files → two static pages on GitHub Pages
4. Later: Databricks job (Spark LAS standardisation, registry, drift), API and MCP tools


9. IMPLEMENTATION PLAN

| Phase | Goal | Gate (ADR-002) |
|---|---|---|
| P0 | Data foundation | Exact FORCE splits; ≥ 99% Kansas headers readable |
| P1 | Blind-well baseline | Penalty score ≥ −0.526 on hidden wells |
| P2 | Model choice | +0.02 on hidden wells and better on the open test |
| P3 | Kansas transfer | Agreement with known unit lithology (pre-registered) |
| P4 | Log quality and drift | Measures for every Kansas well |
| P5 | API, MCP, geologist copilot | Contracts, grounding, R13 budgets |
| P6 | Databricks job | Exact score reproduced; registry; drift |
| P7 | Pages | Live and browser-tested |


10. TESTING

| Layer | What |
|---|---|
| Unit | Penalty scorer, LAS header parser, class mapping |
| Data | Split counts, curve dictionary coverage |
| Model | Blind-well scores against the pre-set gates |
| Browser | Both pages in three display modes |


11. RISKS AND MITIGATIONS

| Risk | Mitigation |
|---|---|
| Random splits overstate accuracy | Blind wells only; the overstatement is measured and shown |
| Rare classes (basement, halite, anhydrite) have few samples | Recall per class reported; rare classes flagged as unreliable |
| North Sea rocks and tools differ from Kansas | Transfer judged against Kansas geology, not assumed; claim withdrawn if it fails |
| Kansas files are heterogeneous (mud logs, partial curves) | Inventory first; only wells with the required curves are scored |


12. SUCCESS CRITERIA

- Every phase judged against a gate fixed before its work; misses reported with the number
- A petrophysicist can download a lithology curve per well with its uncertainty
- The transfer to Kansas is either supported by geology or withdrawn


13. KEY INSIGHTS

To be filled as phases finish.


14. APPENDIX — References

- Bormann, P., Aursand, P., Dilib, F., Manral, S., Dischington, P. (2020). FORCE 2020 Well well log and lithofacies dataset for machine learning competition. Zenodo, doi:10.5281/zenodo.4351156
- Chen, T., Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. KDD
- Ke, G. et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. NeurIPS
- Canadian Well Logging Society. LAS Version 2.0: A Digital Standard for Logs
- Zeller, D. E., ed. (1968). The stratigraphic succession in Kansas. Kansas Geological Survey Bulletin 189
- Lakens, D. (2017). Equivalence tests. Social Psychological and Personality Science 8
