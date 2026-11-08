# ADR-005: P3 Kansas Transfer Test

**Status:** Accepted — written and pushed before any Kansas prediction
**Date:** 2026-11-08
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- P2 chose candidate B: −0.504 on the 10 hidden North Sea wells (ADR-004).
- Kansas has 28,906 LAS files and no per-sample lithology labels. Its only labels are geological: formation tops picked by geologists, and the published lithology of named units.
- **Question:** do predictions agree with the known rock of named Kansas units, far more often than elsewhere in the same wells?

## Decision Drivers

- No Kansas prediction is made before this ADR is pushed (ADR-002, P3).
- Each unit's expected rock comes from a primary source, not from looking at predictions.
- A trivial model (e.g. "shale everywhere") must not pass.
- Kansas wells must be chosen without looking at predictions.

## Decision (pre-registered)

### 1. The transfer model "T"

- Candidate B's recipe (ADR-004): XGBoost with the same settings, engineered features and expected-penalty decision.
- **Inputs restricted to what Kansas logs carry:** GR, RHOB, NPHI, DTC, RDEP, RMED, RSHA, PEF, CALI, BS, SP, DRHO, plus B's engineered features built from them.
- **Dropped:** depth, X/Y/Z position, North Sea group and formation names, and drilling curves (ROP, ROPA, mud weight, DCAL, RMIC, RXO, SGR, DTS). None exists or means the same in Kansas.
- Trained once on the 98 FORCE training wells. Its hidden-well score is **reported, not gated**: it measures what dropping North Sea-only inputs costs.

### 2. Kansas units and expected rock

| Unit (KGS tops name) | Expected rock | Interval scored | Primary source |
|---|---|---|---|
| Hutchinson Salt Member | Halite | Top to next deeper top, ≤ 170 m | KGS Bulletin 214; KGS Bulletin 237 (net salt up to 170 m, with ~20% shale and anhydrite interbeds) |
| Stone Corral Formation ("Cimarron anhydrite") | Anhydrite | Top to next deeper top, ≤ 14 m | KGS Oil and Gas Investigations 11 (subsurface mostly anhydrite, 25–45 ft) |
| Arbuckle Group | Dolomite | Top to next deeper top, ≤ 30 m | KGS Subsurface Geology Series 2 (mostly dolomite, almost no shale) |
| Heebner Shale Member | Shale | First 1.5 m below the top (a thin marker) | KGS Bulletin "LA", gamma-ray chapter (black, radioactive shale) |
| Lansing Group / Lansing–Kansas City / Kansas City Group | Limestone | Top to next deeper top, ≤ 120 m | KGS Bulletin 51 (principally limestone, with shale) |
| Cherokee Group | Shale | Top to next deeper top, ≤ 150 m | KGS Open-File Report 2022-2 transects; older KGS usage "Cherokee shale" |

- **Reported, not gated:** Mississippian (mixed limestone, dolomite and chert) and Precambrian basement (too few FORCE basement samples: 103).
- Tops names are matched case-insensitively on the unit name; "Granite Wash" is not basement.
- Depths: KGS tops and LAS depths are in feet below the log reference; converted to metres (× 0.3048).

### 3. What counts as "right"

- **Acceptable rock:** the expected rock, or any rock the official FORCE penalty matrix charges ≤ 2.0 for. That is: limestone accepts chalk and marl; shale accepts marl; halite, anhydrite and dolomite accept only themselves.
- **Also reported (not gated):** the carbonate family for the Arbuckle (dolomite, limestone or chalk), because FORCE trains dolomite on 0.14% of samples.

### 4. Wells

- **Eligible:** a readable LAS file whose header has GR, a neutron log, and a density or density-porosity log (17,757 files, 15,973 wells), and a KGS top for the unit.
- **Sample:** up to 300 eligible wells per unit, drawn at random (seed 42) from all archive years. If a well has several files, the one covering the unit interval with the most core logs is used.
- **Coverage:** an interval counts only if GR, neutron and density are present on ≥ 80% of its samples.

### 5. Kansas log preparation (fixed before reading any data)

- Null codes and values ≤ −999 → missing.
- Resampled to a 0.1524 m (0.5 ft) grid by linear interpolation, matching FORCE's 0.152 m spacing so the ±5-sample context means the same depth.
- One curve per standard name: the matching curve with the most valid values.
- **Units:** neutron in percent (median > 1.5) → fraction; density in kg/m³ (median > 100) → g/cm³; sonic in µs/m (median > 300) → µs/ft; deep conductivity (mmho/m) → resistivity 1000 / C when no resistivity is present.
- **Density from density porosity** when only DPHI exists: RHOB = 2.71 − 1.71 × DPHI (limestone matrix 2.71 g/cm³, fresh fluid 1.0 g/cm³; KGS logs are commonly recorded on a limestone matrix).
- **Not corrected (stated risk):** neutron matrix differences between FORCE and Kansas tools.

### 6. Measures and gate

- **Agreement (per well):** share of scored samples in the unit interval predicted as an acceptable rock. Unit agreement = median across wells.
- **Lift (per unit):** pooled share of acceptable rock inside the unit intervals ÷ pooled share of the same rocks in the rest of those wells' logged depth. Lift guards against a model that predicts one rock everywhere.
- **Unit passes:** ≥ 30 wells scored, median agreement ≥ 50%, and lift ≥ 2.
- **P3 passes:** at least 4 of the 6 gated units pass.
- The 50%, 2× and 4-of-6 thresholds are our own choice. No published standard sets them; fixing them before the data follows Lakens (2017).

### 7. Deliverable

- Lithology and probability curves per scored well, written as LAS 2.0 (curves `LITH` code, `LITH_PROB`). Outputs stay outside the repository; three example wells are committed under `docs/data/las/`.

## Considered Options

| Option | Status | Why |
|---|---|---|
| **Named units + lift vs the rest of the well** | **Chosen** | Uses the only Kansas labels that exist; lift stops a one-rock model from passing |
| Retrain on Kansas pseudo-labels from tops | Rejected | Circular: tops would be both labels and test |
| Domain adaptation (feature alignment between basins) | Cited, not tested in P3 | First measure transfer as is; adaptation is the remedy if P3 fails |
| Cuttings descriptions as labels | Rejected | Sparse and not on a depth grid (ADR-001) |
| Score every Kansas well | Deferred to P6 | 10⁸+ depth rows; Databricks is planned for that (R15) |

## Falsification

| Result | Diagnosis | Next action |
|---|---|---|
| Evaporites pass, carbonates and shales fail | Log responses of salt and anhydrite are distinctive; carbonate and clastic responses depend on tools and matrix | Report; neutron-matrix correction as a pre-registered follow-up |
| High agreement but lift < 2 | Model predicts one rock almost everywhere | Transfer claim withdrawn for that unit |
| Fewer than 30 scorable wells for a unit | Logs or tops missing | Unit reported, not gated |
| T scores far below B on the FORCE hidden wells | North Sea position and stratigraphy carried much of B's skill | Report the cost; Kansas results judged with it |

## Consequences

- **Positive:** a transfer claim that geology can refute, decided before any prediction.
- **Negative:** tops are picked by many geologists over decades; some will be wrong, which lowers agreement for every model equally.

## Related Decisions

- ADR-001 (Kansas judged against geology), ADR-002 (P3 gate), ADR-003 (E7 geological control), ADR-004 (candidate B)

## Evidence

| Document | Issuer | Year | Used for |
|---|---|---|---|
| Bulletin 214 (salt in Kansas) | Kansas Geological Survey | 1978 | Hutchinson Salt lithology |
| Bulletin 237, geophysical atlas (Hutchinson Salt) | Kansas Geological Survey | — | Salt thickness cap |
| Oil and Gas Investigations 11 | Kansas Geological Survey | — | Stone Corral anhydrite, thickness |
| Subsurface Geology Series 2 (Cole) | Kansas Geological Survey | 1975 | Arbuckle dolomite |
| Bulletin "LA" (log analysis), gamma-ray chapter | Kansas Geological Survey | — | Heebner black shale |
| Bulletin 51 | Kansas Geological Survey | — | Lansing and Kansas City limestone |
| Open-File Report 2022-2 (Oborny and Hasiuk) | Kansas Geological Survey | 2022 | Cherokee Group |
| Formation tops database (`ks_tops`, 2,135,525 tops, retrieved 2026-11-08) | Kansas Geological Survey | 2026 | Unit intervals |
