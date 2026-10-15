# ADR-003: Industry Alignment — How Petrophysicists Work (R16)

**Status:** Accepted — written and pushed before any analysis
**Date:** 2026-10-15
**Deciders:** Sabrina Pribadi

---

## Context

The project must look like petrophysics work, not a generic classifier. These are the expectations it meets, each with a primary source and the phase that delivers it.

## Expectations

| # | What practitioners expect | How this project meets it | Phase | Source |
|---|---|---|---|---|
| E1 | **Lithology classes and the cost of mistakes**: confusing chalk with limestone matters less than shale with sandstone | The 12 FORCE classes and the official penalty matrix are the metric | P1 | FORCE 2020 competition (Bormann et al. 2020) |
| E2 | **Blind-well testing**: a model is trusted on wells it never saw | Official hidden wells; well-grouped cross-validation | P1–P2 | FORCE 2020 final scoring |
| E3 | **LAS files read as the standard defines them**: sections, units, null codes, wrapped lines | Parser follows LAS 2.0; every file's version, null code, depth unit and step recorded | P0 | CWLS LAS 2.0 standard (declared in each file's header; cwls.org unreachable when checked 2026-10-15) |
| E4 | **Curve names standardised**: one rock property, many mnemonics (`GR`, `G/R`, `GRGC`…) | A curve dictionary maps raw mnemonics and units to standard curves; unmapped curves listed | P0 → P3 | KGS LAS archive (observed), FORCE curve set |
| E5 | **Log quality control**: bad hole (caliper far above bit size), density correction (DRHO), spikes | Bad-hole flags from CALI − BS and DRHO; reported per well | P1 (features), P4 (monitoring) | FORCE curves BS, CALI, DRHO provided for this purpose |
| E6 | **Per-well normalisation**: gamma-ray scales differ between tools and wells | Per-well scaled features tested as a candidate | P2 | Standard practice; tested, not assumed |
| E7 | **Geological control**: picks honour formation tops and known unit lithology | NPD lithostratigraphy (North Sea); KGS formation tops and unit descriptions for the Kansas transfer test | P1, P3 | NPD (Norwegian Offshore Directorate) FactPages; KGS tops database; Zeller (1968) KGS Bulletin 189 |
| E8 | **Uncertainty**: a planner needs to know when a pick is doubtful | Class probabilities per depth; low-confidence intervals flagged | P2–P3 | — |
| E9 | **Deliverables in the domain's formats**: lithology as a LAS curve per well, composite plots, a well map | Predicted lithology and probability curves written as LAS 2.0; well map with per-well scores | P3, P7 | LAS 2.0 |
| E10 | **Cadence**: new wells arrive continuously (KGS adds yearly archives) | Scheduled scoring of new LAS files with drift checks | P6 | KGS archive structure (yearly zips 1999–2026) |

## Terminology (used on the pages, defined on first use)

- **lithology**, **log** (curve), **well**, **blind well**, **penalty score**
- **mnemonic** (curve short name), **bad hole**
- **formation top**, **lithostratigraphy**

## Differences from the earlier portfolio projects (R16)

| | GEO-1 (network planning) | OG-2 (petrophysics) |
|---|---|---|
| Unit | 0.74 km² hexagon | Well and depth sample |
| Decision | Where to build sites | What rock is at each depth |
| Validation | Spatial blocks, pre-trends | Blind wells, official penalty |
| Deliverable | Site lists (CSV, KML) | Lithology curves (LAS), well map |

**Reused, not copied:** gates written first, ADRs, CI, the two pages and the browser tests.

## Evidence

| Document | Issuer | Year | Used for |
|---|---|---|---|
| FORCE 2020 well log and lithofacies dataset (doi:10.5281/zenodo.4351156), CC BY 4.0 | FORCE / Bormann, Aursand, Dilib, Manral, Dischington | 2020 | Data, splits, penalty (E1, E2) |
| FORCE 2020 competition repository: results and scoring code | Competition organisers | 2020–2022 | Published finalist scores, scorer (E1, E2) |
| LAS Version 2.0: a digital standard for logs | Canadian Well Logging Society | 1992, updated 2017 | File format (E3, E9) |
| The stratigraphic succession in Kansas, Bulletin 189 (Zeller, ed.) | Kansas Geological Survey | 1968 | Unit lithology for the transfer test (E7) |
| LAS archive, formation tops and well databases | Kansas Geological Survey | 1999–2026 | Kansas data (E4, E7, E10) |
| FactPages: wellbores and lithostratigraphy | Norwegian Offshore Directorate (formerly NPD) | current | North Sea stratigraphy (E7) |

## Related Decisions

- ADR-001 (framing)
- ADR-002 (gates)
