# ADR-006: P4 Log Quality and Drift Across the Kansas Archive

**Status:** Accepted — written and pushed before P4 ran; results appended; erratum 2026-11-18 (curve reader, see ADR-013)
**Date:** 2026-11-08
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- Kansas logs span 1999–2026, many companies and tools. A model is only as good as the curves it reads.
- A data manager needs to know, per well: which curves exist, whether their values are physically plausible, and whether the hole was in good condition.
- A model owner needs to know whether each new yearly archive looks like the data the model was judged on.
- **ADR-002 gate (P4):** per-well data-quality and drift measures computed for every Kansas well and year.

## Decision Drivers

- Measures must be cheap enough to run on every file, every year (the industry's cadence: KGS adds a yearly archive).
- Thresholds come from physics or published practice, fixed here.
- Streaming per file: no all-curves table on the 8 GB laptop (R15; the full table is P6's job).

## Decision (pre-registered)

### 1. Per-file quality measures (every readable LAS file)

| Measure | Definition | Why |
|---|---|---|
| Curve availability | Which of GR, RHOB (or DPHI), NPHI, DTC, RDEP, PEF, CALI exist in the header | What the model can read |
| Data coverage | Share of logged depth where GR, neutron and density are all valid | A curve in the header can still be empty |
| Out-of-range share | Share of valid samples outside physical ranges: GR 0–300 API, RHOB 1.0–3.2 g/cm³, NPHI −0.15–1.0, DTC 40–240 µs/ft, RDEP 0.01–100,000 Ω·m | Spikes, unit errors, tool failures |
| Bad-hole share | Share of samples with \|DRHO\| > 0.15 g/cm³ where DRHO exists; else caliper exceeding bit size by > 1 in where both exist; else "unknown" | Density reads the mud, not the rock, in washed-out hole |
| Model confidence | Median top-class probability of model T over covered depth | Low confidence flags wells to review |

- Files are read with the ADR-005 §5 rules; units fixed the same way.
- **Per well:** the file with the most core logs represents the well.

### 2. Drift by archive year

- **Inputs tracked:** GR, RHOB, NPHI, DTC, RDEP (log10), and model T's top-class probability.
- **Statistic:** population stability index (PSI) of each archive year against all earlier years pooled, on 10 quantile bins of the reference.
- **Bands:** < 0.10 stable, 0.10–0.25 watch, > 0.25 alert (the common practice examined by Yurdakul and Naranjo 2020).
- **Also reported:** PSI of each Kansas year against the FORCE training wells, a measure of how far Kansas sits from what the model learned.
- **Sampling:** at most 2,000 depth samples per file enter the drift sample (random, seed 42), so long wells do not dominate.

### 3. Gate

- **Passes if:** quality measures are computed for ≥ 99% of readable Kansas files (failures listed with reasons), and drift is computed for every archive year.
- **Not a gate:** how many wells are poor or how many years drift. Those are findings.

### 4. Deliverables

- `data/outputs/p4_quality.json` (summary), a per-well quality table (`derived/p4_well_quality.parquet`, outside the repository), drift tables per year, and a quality map on the results page.

## Empirical results (2026-11-08)

**P4 passed:** 28,841 of 28,865 readable files measured (99.92%; 24 have no data rows); 24,157 wells; drift computed for all 18 archives (1999 has no earlier year).

- **Coverage:** gamma ray, neutron and density together cover a median 36% of each file's depth; 0% in the 1999–2011 archives, 83–99% in most archives since 2015.
- **Values:** a median 0.1% of samples fall outside physical ranges.
- **Hole condition:** knowable for 9.4% of files only (DRHO in 2,644, caliper and bit size in 78); median bad-hole share there 5.5%.
- **Model T's confidence:** median 0.77, steady across years (0.75–0.82).
- **Drift vs earlier years:** neutron alerts (PSI > 0.25) in 9 of 17 comparable years, largest in 2020–2021 (0.58), consistent with changing tools; gamma ray and sonic stable in 15–16 of 17.
- **Drift vs FORCE:** density alerts in 17 of 18 years; neutron, sonic, resistivity and T's confidence in all 18. Kansas logs sit far from what the model learned, consistent with P3's failure.

## Erratum (2026-11-18): density correction read as density

- **Bug:** in Halliburton CDL files the mnemonic `RHOC` is the density correction, not bulk density. The reader mapped it to `RHOB`, so 10,709 correction curves counted as density and could not count as `DRHO`. Found while preparing ADR-013.
- **Fix:** a density mnemonic whose description says it is a correction maps to `DRHO`; a density curve whose median is outside 1.2–3.3 g/cc is not used as density (`src/curves.py`, `src/kansas.py`, tested). P0 and P4 were rerun on the whole archive with the same code otherwise; old outputs kept outside the repository.
- **What changed:**

| Measure | Before | After |
|---|---|---|
| Curves read as density / as density correction | 28,063 / 2,647 | 17,352 / 13,358 |
| Files with gamma ray, density and neutron (P0) | 58.3% | 54.6% |
| Files with all five core logs (P0) | 18.2% | 17.5% |
| Mapped wells holding gamma ray plus density or neutron | 63% | 59% |
| Hole condition knowable | 9.4% of files (DRHO 2,644, caliper 78) | 46.6% (DRHO 13,351, caliper 78) |
| Median bad-hole share where knowable | 5.5% | 12.8% |
| Model T's median confidence | 0.77 (0.75–0.82 by year) | 0.78 (0.76–0.83) |
| Density drift vs FORCE: alert years | 17 of 18 | 16 of 18 |
| Density drift vs earlier year: watch / alert | 7 / 1 | 3 / 1 |

- **What did not change:** files measured (28,841, 99.92%), wells (24,157), wells on the map (24,166), median coverage (36%), coverage by year, neutron, sonic and resistivity drift, and the gate (passed). The P3b test selection rebuilt from the new inventory has the same SHA-256 (19165ba9…).
- **Reading:** hole condition is now measurable for almost half the archive, and where it is measurable it is worse than first reported. The P3 result (ADR-005) is unaffected in direction; ADR-013 reran Kansas scoring with the fixed reader.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **Physical ranges + DRHO/caliper bad hole + PSI by year** | **Chosen** | Standard log QC; PSI is simple, comparable across inputs and years |
| Kolmogorov–Smirnov test per year | Rejected as the headline | With millions of samples every difference is "significant"; PSI measures size |
| Learned anomaly detector (autoencoder) | Not now | Harder to explain to a data manager; revisit if simple measures miss problems |
| Read only a sample of files | Rejected | The gate says every well |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| < 99% of files processed | Reader fails on some LAS variants | Fix and rerun; list remaining failures |
| Most years alert against FORCE | Kansas tools and rocks differ from the North Sea | Expected; supports reading P3 with caution |
| Model confidence falls by year | Newer logs differ from what T saw | Flag for retraining once Kansas labels exist |

## Consequences

- **Positive:** every Kansas well gets a quality row, so P3 and later scoring can exclude poor wells transparently.
- **Negative:** physical ranges are coarse; a plausible but wrong value passes.

## Related Decisions

- ADR-002 (P4 gate), ADR-003 (E5 log QC, E10 cadence), ADR-005 (reading rules)

## Evidence (OpenAlex, retrieved 2026-11-11; generated by `make evidence`)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| Statistical properties of the population stability index | The Journal of Risk Model Validation | yes | 2020 | 57 | 8.1 | population stability index (drift bands) |
