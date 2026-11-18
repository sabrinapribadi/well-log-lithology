# ADR-013: P3b Kansas Transfer Retest (pre-registered)

**Status:** Proposed — pre-registered 2026-11-18; written and pushed before any P3b model is evaluated on Kansas data and before any test file is opened. Results are appended below the line, never edited above it.
**Date:** 2026-11-18
**Deciders:** Sabrina Pribadi
**Amends:** nothing in ADR-005. P3's result (0 of 6 units, transfer claim withdrawn) stands as reported.

---

## Context and Problem Statement

- P3 (ADR-005) failed: 0 of 6 gated Kansas units passed. The North Sea model called tight Kansas carbonates sandstone, called shale nearly everywhere (high agreement, lift under 2), and found no halite or anhydrite.
- A literature and data review (rule R2; evidence table below) found:
  - No open, labelled carbonate or evaporite well-log set that fixes the training gap; FORCE 2020 stays the only training data.
  - No published study that trains a lithology model on FORCE 2020 and tests it on another basin. Domain-adaptation gains (6–10 points) come from cross-well tests inside one basin.
  - Basin-independent mineral physics: apparent matrix density (RHOmaa) separates quartz (2.65 g/cc), calcite (2.71) and dolomite (2.87) whatever the porosity, where raw density does not.
- **Question:** with the reader fixed and physics-based features, does a model trained only on the North Sea recognise the named Kansas units on wells it has never seen?

## 1. Erratum found before P3b: density correction read as density

Model-free diagnostics (`scripts/p3b_diagnostics.py`) found that in about 10% of P3 wells per unit the "density" fed to the model had a median near 0.05 g/cc.

- **Cause:** the curve dictionary mapped the mnemonic `RHOC` to bulk density. In KGS files RHOC is usually the *density correction* (10,709 of 11,513 RHOC curves are described as a correction); 1,055 files carry RHOC as their only "density". When a file had both, the reader kept whichever had more values.
- **Fix (now):** a density mnemonic described as a correction maps to DRHO; a density candidate whose median is outside 1.2–3.3 g/cc is ignored (`src/curves.py`, `src/kansas.py`, test `test_density_correction_is_never_read_as_density`).
- **Effect on the development intervals:** wells reading implausibly light (median density under 2.20 g/cc) fell from 14–45 per unit to 1–5, except the Stone Corral (45; see §2).
- **Scope:** P3 is not re-scored as P3; its result stands. Every P3b arm, including the P3 model as control, is scored with the fixed reader. The P4 log-quality counts (ADR-006) and the served Kansas quality may overstate density coverage by up to 1,055 files; they are recounted in a separate follow-up, reported as an erratum to ADR-006.

## 2. Model-free diagnostics of the development intervals (fixed reader)

Medians over the P3 wells (`data/outputs/p3b_diagnostics.json`). RHOmaa uses the neutron-density crossplot porosity (limestone units, fluid 1.0 g/cc).

| Unit (expected rock) | Wells | RHOB | RHOmaa | Reads like the expected rock? |
|---|---|---|---|---|
| Arbuckle (dolomite) | 300 | 2.61 | 2.80 | Yes: RHOmaa near dolomite; raw density near quartz explains the P3 "sandstone" |
| Lansing-Kansas City (limestone) | 298 | 2.61 | 2.72 | Yes: calcite |
| Mississippian (limestone; not gated) | 300 | 2.56 | 2.72 | Mostly calcite |
| Cherokee (shale) | 299 | 2.58 | 2.76 | Mixed: 32% of samples above 100 API |
| Heebner (shale) | 298 | 2.40 | 2.74 | Yes: 80% of samples above 100 API |
| Stone Corral (anhydrite) | 300 | 2.63 | 2.81 | Partly: 27% of samples above 2.85 g/cc; 77 wells have no density over the interval |
| Hutchinson Salt (halite) | 299 | 2.71 | 2.84 | **No:** 1.7% of samples read like halite; 101 wells have no density over the interval |

The Hutchinson Salt logs do not show salt (halite reads 2.04 g/cc). No classifier can call halite from them; the unit stays gated and is expected to fail.

## 3. The gate: original, and one amended version written now

- **Original gate (ADR-005 §6), reported unchanged:** a unit passes with at least 30 wells scored, median agreement at least 50% and lift at least 2; 4 of 6 gated units needed.
- **Amended gate (primary for P3b),** fixed now from geology and the diagnostics above, before any model is evaluated:
  1. **Sample quality:** a sample counts only with GR, neutron and a plausible density; samples with |DRHO| > 0.15 g/cc are dropped (doubtful density correction).
  2. **Lift against the neighbours, not the whole well:** lift = share of acceptable calls inside the interval ÷ the same share within 30 m above and 30 m below it in the same well. Reason: the Kansas column above and below is itself shale- and limestone-rich, so lift against the whole well caps a perfect shale or limestone classifier under 2 (research report §3). The threshold stays 2.
  3. **Unchanged:** units, expected rocks, intervals and caps, acceptable rocks (penalty ≤ 2.0), 30 wells, 50% median agreement, 4 of 6 units.
- **Hutchinson Salt:** only 10 fresh eligible wells exist (300 of 317 were used in P3), so it cannot reach 30 wells and does not pass under either gate. The rule is not changed for it.

## 4. Development set and one-shot test set

- **Development set:** the 1,915 P3 files (1,914 wells). Used for diagnostics, for the M1 variant choice (§5) and for checks; any number of runs.
- **Test set:** fresh wells never scored in P3, from headers and tops only (`scripts/p3b_select_fresh.py`): same eligibility as P3 with the corrected mapping, development wells excluded by KGS ID, up to 100 wells per unit, seed 2026.
  - 601 files, 610 unit intervals: Stone Corral, Arbuckle, Heebner, Lansing-Kansas City, Cherokee and Mississippian 100 each; Hutchinson Salt 10; Precambrian 0.
  - **Manifest SHA-256:** `19165ba97993699cd3beeb8b2fccf7552069f0352e6c8726c59ec681a14572aa` (`data/outputs/p3b_test_manifest.json`).
  - Scored once, by every arm, under both gates. No test result changes any arm, threshold or rule.

## 5. Arms (all trained on FORCE 2020 only; no Kansas label is used for training)

- **C — control:** P3's model T, unchanged, scored with the fixed reader. Separates what the reader fix and the amended gate do from what the new methods do.
- **M0 — physics reference, no training.** Per sample, in this order:
  1. Coal if RHOB < 1.90 g/cc.
  2. Halite if RHOB < 2.20 and NPHI < 0.05 (halite 2.04 g/cc, NPHI about −0.03).
  3. Anhydrite if RHOB > 2.92 and NPHI < 0.05 (anhydrite 2.98; above zero-porosity dolomite 2.87).
  4. Shale if the GR index (GR scaled between the well's 5th and 95th percentiles) is above 0.5.
  5. Otherwise by RHOmaa: Sandstone under 2.68, Limestone from 2.68 to under 2.79, Dolomite from 2.79 (midpoints of quartz 2.65, calcite 2.71, dolomite 2.87).
- **M1 — physics-feature XGBoost:** model T's recipe (ADR-005 §1) plus RHOmaa, neutron-density separation (NPHI − density porosity, limestone units), apparent matrix transit time (sonic, fluid 189 µs/ft), the apparent volumetric photoelectric factor where PEF exists, and the GR index. Two variants; the development set picks one by gated units passed under the amended gate (ties: M1b), then it is frozen:
  - M1a keeps raw RHOB and NPHI;
  - M1b drops raw RHOB and NPHI levels (they enter only through the physics features), so the model cannot use "density near 2.65" as a sandstone shortcut.
- **M2 — M1 plus label-shift correction:** class priors re-estimated on the pooled, unlabelled test samples by EM (Saerens et al. 2002), probabilities rescaled by new ÷ training priors, then the expected-penalty decision. Targets "shale everywhere" and the North Sea class mix.
- **Primary result:** M1 under the amended gate. The other arms and the original gate are reported beside it.

## 6. Decision rules

- **P3b passes** if the primary arm passes at least 4 gated units under the amended gate on the test set.
- If the control C also passes under the amended gate, the reader fix and gate change explain the result, and the report says so before any method claim.
- **If P3b passes:** Kansas lithology is described as "validated for the passing units after the P3b retest (ADR-013)", with the P3 failure kept beside it; the API, app and skill keep the not-validated caveat for the units that failed.
- **If P3b fails:** the transfer claim stays withdrawn; the per-unit results and the physics diagnosis are reported as a second, sharper negative result.

## 7. What would change this decision

- An open, core-labelled Kansas lithology set (for example a downloadable description of the Wellington KGS 1-32 core) would replace formation tops as truth for the units it covers.
- A published FORCE-to-other-basin lithology result would set a reference for the size of the drop.

## Evidence

### ADR-013 — evidence (OpenAlex, retrieved 2026-11-18)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| FORCE 2020 Well well log and lithofacies dataset for machine learning competition | Zenodo (dataset, CC BY 4.0) | n/a (dataset) | 2020 | 23 | 3.3 | data, official splits and penalty matrix |
| WLFM: A Well-Logs Foundation Model for Multi-Task and Cross-Well Geological Interpretation | arXiv 2509.18152 | no (preprint) | 2025 | 10 | 5.0 | cited alternative (well-log foundation model) |
| Facies classification using machine learning | The Leading Edge | yes | 2016 | 280 | 25.5 | Kansas Council Grove facies data (SEG 2016 contest; licence says treat as proprietary) |
| Distributed collaborative prediction: Results of the machine learning contest | The Leading Edge | yes | 2017 | 77 | 7.7 | SEG 2016 contest results (blind-well F1 range on Kansas core facies) |
| Comparison of four approaches to a rock facies classification problem | Computers & Geosciences | yes | 2007 | 239 | 11.9 | Kansas facies classification; realistic accuracy ceiling |
| Application of Machine Learning in Rock Facies Classification with Physics-Motivated Feature Augmentation | arXiv 1808.09856 | no (preprint) | 2018 | 20 | 2.2 | physics-motivated features, about +5% F1 within one Kansas field |
| Improved well-log classification using semisupervised label propagation and self-training, with comparisons to popular supervised algorithms | Geophysics | yes | 2019 | 33 | 4.1 | semi-supervised self-training on Kansas logs (cross-well) |
| Improved well log classification using semisupervised Gaussian mixture models and a new hyper-parameter selection strategy | Computers & Geosciences | yes | 2020 | 32 | 4.6 | semi-supervised Gaussian mixtures vs XGBoost (cross-well) |
| Unsupervised domain adaptation using maximum mean discrepancy optimization for lithology identification | Geophysics | yes | 2020 | 40 | 5.7 | MMD domain adaptation for lithology, about +10% (cross-well, one basin) |
| Well Logging Based Lithology Identification Model Establishment Under Data Drift: A Transfer Learning Method | Sensors | yes | 2020 | 81 | 11.6 | transfer learning under data drift, 3 classes (cross-well) |
| Cross-Well Lithology Identification Based on Wavelet Transform and Adversarial Learning | Energies | yes | 2023 | 23 | 5.8 | adversarial alignment and wavelet features (cross-well) |
| Cross-well lithology identification based on adversarial spectral kernel matching domain adaptation | Computational Geosciences | yes | 2026 | 0 | 0.0 | cross-well adversarial domain adaptation (no numbers read) |
| Accurate predictions on small data with a tabular foundation model | Nature | yes | 2025 | 2,226 | 1,113.0 | tabular foundation model (no lithology use found; not pre-registered) |
| Lithology Identification from Well Logs via Meta-Information Tensors and Quality-Aware Weighting | Big Data and Cognitive Computing | yes | 2026 | 3 | 3.0 | within-FORCE weighted-F1 gains; same-well leakage warning |
| Robust lithology identification from imperfect well logs using a quality-aware and geological-risk-constrained deep learning framework | Energy Geoscience | yes | 2026 | 0 | 0.0 | within-FORCE quality-aware model (split unverified) |
| Lithology Classification Based on Well Log Data: A Benchmark for Machine Learning Models | Mathematical Geosciences | yes | 2026 | 11 | 11.0 | Kansas Arbuckle lithology benchmark (paywalled; numbers not read) |
| Well Log Normalization: Methods and Guidelines | Petrophysics (SPWLA) 45(3), no DOI in OpenAlex | yes | 2004 | 69 | 3.0 | type-well normalisation practice |
| MID Plot: a new lithology technique. [Matrix identification plot] | The Log Analyst 17(6), no DOI in OpenAlex | yes | 1976 | 53 | 1.0 | matrix identification plot (apparent matrix density and transit time) |
| Basic well log analysis | American Association of Petroleum Geologists eBooks | yes | 2004 | 916 | 39.8 | mineral endpoint values (chartbook) |
| Well Logging for Earth Scientists | Springer eBooks | yes | 2007 | 1,622 | 81.1 | mineral endpoint values and log physics |
| GLOBAL, A NEW APPROACH TO COMPUTER-PROCESSED LOG INTERPRETATION | SPE Annual Technical Conference and Exhibition | yes | 1980 | 125 | 2.7 | multimineral log inversion (GLOBAL), basis of the M0 reference |
| CT and Scanning Data of the KGS Wellington 1-32 CarbonSAFE Core | OSTI OAI (U.S. Department of Energy Office of Scientific and Technical Information) | n/a (dataset) | 2022 | 0 | 0.0 | Wellington KGS 1-32 core CT and scanning data (Kansas core truth candidate) |
| Computed Tomography Scanning and Geophysical Measurements of the Wellington 1-32 Core | OSTI technical report (US DOE, NETL) | no (preprint) | 2022 | 0 | 0.0 | Wellington 1-32 core measurements report |
| Using sedimentology to address the marine or continental origin of the Permian Hutchinson Salt Member of Kansas | Sedimentology | yes | 2019 | 17 | 2.1 | Hutchinson Salt core lithologies (halite with shale and anhydrite) |
| Adjusting the Outputs of a Classifier to New a Priori Probabilities: A Simple Procedure | Neural Computation | yes | 2002 | 653 | 26.1 | prior re-estimation under label shift (arm M2) |
| Detecting and Correcting for Label Shift with Black Box Predictors | arXiv 1802.03916 | no (preprint) | 2018 | 609 | 67.7 | black-box label-shift estimation (arm M2) |

Grey literature and pages used (not in OpenAlex, so not in `docs/references.yaml`):
- FORCE 2020 organisers: [geological summary](https://www.sodir.no/globalassets/2-force/2020/seminars/contest-machine-learning/blog-post-litho-facies-competition-geological-summary.pdf) and [technical retrospective](https://www.sodir.no/4ace9a/globalassets/2-force/2020/seminars/contest-machine-learning/technical_retrospective_force-2020-lithofacies-competition.pdf).
- Kansas Geological Survey: [Geological Log Analysis](https://www.kgs.ku.edu/Publications/Bulletins/LA/index.html) (mineral endpoints, RHOmaa and Umaa, [evaporites](https://www.kgs.ku.edu/Publications/Bulletins/LA/07_evaporites.html)); [Bulletin 226](https://www.kgs.ku.edu/Publications/Bulletins/226/Doveton/index.html); [Bulletin 214, salt](https://www.kgs.ku.edu/Publications/Bulletins/214/03_salt.html); Bulletin 189 ([Permian](https://www.kgs.ku.edu/Publications/Bulletins/189/08_perm.html), [Pennsylvanian](https://www.kgs.ku.edu/Publications/Bulletins/189/07_penn.html), [Cambro-Ordovician](https://www.kgs.ku.edu/Publications/Bulletins/189/04_paleoz.html), [Mississippian](https://www.kgs.ku.edu/Publications/Bulletins/189/06_miss.html)); [Bulletin 137](https://www.kgs.ku.edu/Publications/Bulletins/137/Jewett/); [Watney, core studies](https://www.kgs.ku.edu/Publications/Bulletins/Sub6/Watney/index.html); [OFR 1980-16](https://www.kgs.ku.edu/Publications/OFR/1980/KGSOFR1980-16.pdf); [OFR 2003-66](https://www.kgs.ku.edu/PRS/publication/2003/ofr2003-66/lithology.html); [formation tops](https://www.kgs.ku.edu/Magellan/Tops/index.html).
- SEG 2016 contest data ([github.com/seg/2016-ml-contest](https://github.com/seg/2016-ml-contest)): licence says "treat as proprietary"; not used.
- Density quality thresholds: [Crain's Petrophysical Handbook, density tools](https://spec2000.net/logging-tool-profiles/tool-profiles-density-and-photo-electric-effect-logs.htm).
- FORCE-to-Taranaki log reconstruction, arXiv [2611.19625](https://arxiv.org/abs/2611.19625) (not yet indexed in OpenAlex).
- Excluded as training data: [NORA lithology dataset](https://huggingface.co/datasets/NoraResearchLab/Lithology-Training-Dataset) (rule-derived labels, licence "other").

---

## Results

*Appended after the one-shot test. Nothing above this line changes.*
