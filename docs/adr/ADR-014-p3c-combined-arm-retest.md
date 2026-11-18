# ADR-014: P3c Combined-Arm Kansas Retest (pre-registered)

**Status:** Accepted — pre-registered 2026-11-18, before arm M3 was scored on any Kansas well and before the P3c test set was opened. Results will be appended below the line.
**Date:** 2026-11-18
**Deciders:** Sabrina Pribadi
**Amends:** nothing in ADR-005 or ADR-013. P3 (0 of 6 units) and P3b (3 of 6) stand as reported.

---

## Context and Problem Statement

- P3b (ADR-013) failed: the primary arm M1a (XGBoost with physics features) passed 3 of 6 Kansas units (Stone Corral, Cherokee, Heebner); 4 were needed.
- The arms failed in different places. The training-free physics rules (M0) recognise the carbonates (Arbuckle 61%, Lansing-Kansas City 71% median agreement) where every North Sea-trained arm calls them sandstone (0–2%). M1a passes the shale and anhydrite units where M0 does not reach Stone Corral (20%).
- A combined arm is therefore an obvious next idea, but it was **thought of after the P3b test set was seen**. ADR-013 said combining arms after the test would not be done on that set. A rule chosen after looking at a test set has to be judged on data it never touched (Dwork et al. 2015), so P3c uses new wells.
- Question: does a fixed combination of the two existing arms pass 4 of 6 gated Kansas units on fresh wells?

## 1. Arm M3 (no new training, no free parameter)

- **Rule:** take the frozen M1a call (`models/p3b_M1a.json`, unchanged since commit 6a1bff8). Where M1a calls **sandstone** and the physics rules M0 (`src/physics.py`, unchanged since ADR-013) call **limestone or dolomite**, use the M0 call. Everywhere else, including samples where M0 has no call, keep M1a.
- **Why this rule:** it targets the documented failure only (tight Kansas carbonates read as North Sea sandstone, ADR-005 and ADR-013 §2) and leaves M1a's shale, anhydrite and other calls untouched. It mixes a physics prior with a learned model in the simplest auditable way (von Rueden et al. 2021).
- **Code:** `scripts/p3b_score.py`, one line, committed with this ADR before any M3 score exists.

## 2. Gate (unchanged from ADR-013 §3)

- **Primary:** the amended gate. Samples need GR, neutron and a plausible density, minus |DRHO| > 0.15 g/cc; lift is against the 30 m above and below the interval; a unit passes with at least 30 wells scored, median agreement at least 50% and lift at least 2; **4 of 6 gated units** are needed.
- **Also reported:** the original gate (ADR-005 §6).
- Units, expected rocks, intervals and caps, acceptable rocks (penalty ≤ 2.0) and the 80% coverage rule are all unchanged.

## 3. One-shot test set (fresh wells)

- Same eligibility and intervals as P3 and P3b, with the corrected curve reader. Every well already scored, in P3 (1,914 wells) or in the P3b test (601), is excluded by KGS well ID. Up to 100 wells per unit are drawn at random with **seed 2027**; no LAS data is read for the selection.
- `python scripts/p3b_select_fresh.py --design p3c` → **589 files, 600 unit rows**; SHA-256 of the sorted unit, well and file list: **`1ced56de9a82d5f98d406e49411c3b70bb2787bb6a74a7c28aa27820de0f8db9`** (`data/outputs/p3c_test_manifest.json`). The scorer refuses to read a set with any other hash.

| Unit | Expected rock | Gated | Fresh eligible wells | Selected |
|---|---|---|---|---|
| Hutchinson Salt | Halite | yes | 0 | 0 |
| Stone Corral | Anhydrite | yes | 221 | 100 |
| Arbuckle | Dolomite | yes | 1,067 | 100 |
| Heebner | Shale | yes | 7,141 | 100 |
| Lansing-Kansas City | Limestone | yes | 7,257 | 100 |
| Cherokee | Shale | yes | 3,487 | 100 |
| Mississippian | Limestone | no | 2,710 | 100 |
| Precambrian | Basement | no | 0 | 0 |

- **Hutchinson Salt has no wells left, so it fails by rule.** M3 therefore needs 4 of the other 5 gated units. The rule is not changed for it.

## 4. Arms reported beside M3

- C (P3 model T, fixed reader), M0, M1a, M1b and M2 (M1a with re-estimated priors, as in the P3b test), so a pass can be traced to its parts.
- If the control C also passes 4 units, the reader fix and gate explain the result, and the report says so before any method claim.

## 5. What is run, and in what order

1. This ADR, the M3 line, the selection mode and the manifest are committed and pushed.
2. **Informational only:** M3 on the P3 development set and the P3b test set (`--tag posthoc`, separate output files). These sets have already been seen, so the numbers cannot change anything here; they are reported as post-hoc.
3. **One shot:** `python scripts/p3b_score.py --set p3c --m1 M1a`. It is rerun only if it crashes before writing results, and any rerun is logged.

## 6. Decision rules

- **P3c passes** if M3 passes at least 4 gated units under the amended gate on the P3c set.
- **If P3c passes:** Kansas lithology is described as "validated for the passing units after the P3c retest (ADR-014)", with the P3 and P3b failures kept beside it. The API, app and skill keep the not-validated caveat for every unit that failed, including Hutchinson Salt.
- **If P3c fails:** no further arm combinations are tried on Kansas formation tops. The next step needs core-based labels (ADR-013 §7), not another rule.

## 7. Expectations, written before scoring

From the component arms on the P3b test (amended gate):

| Unit | M0 (agreement, lift) | M1a (agreement, lift) | Expected for M3 |
|---|---|---|---|
| Heebner | 90%, 2.57 | 80%, 2.85 | pass (M3 keeps M1a's shale calls) |
| Arbuckle | 61%, 2.70 | 0%, 9.3 | likely pass (M3 takes M0's dolomite calls) |
| Cherokee | 55%, 2.12 | 50.2%, 2.12 | marginal (M1a sat exactly on the 50% bar) |
| Stone Corral | 20%, 260 | 58%, 148 | fragile (M1a was 48% on the development set) |
| Lansing-Kansas City | 71%, 1.35 | 2%, 1.73 | likely fail on lift: the 30 m around it is also limestone |

- **Realistic outcome:** 3 or 4 units. A pass needs Heebner, Arbuckle, Cherokee and Stone Corral to hold together.
- **Known risk:** M3 also turns sandstone calls into carbonate in the neighbouring 30 m, which can lower lift where carbonates sit on carbonates.

## 8. What would change this decision

- An open, core-labelled Kansas lithology set would replace formation tops as the truth for the units it covers.
- A fresh-well count below 30 for any gated unit other than Hutchinson Salt would mean no well can show a pass; the manifest shows 100 in each.

## Evidence

### ADR-014 — evidence (OpenAlex, retrieved 2026-11-18)

| Reference | Venue | Peer-reviewed | Year | Citations | Per year | Used for |
|---|---|---|---|---|---|---|
| Application of Machine Learning in Rock Facies Classification with Physics-Motivated Feature Augmentation | arXiv 1808.09856 | no (preprint) | 2018 | 20 | 2.2 | physics-motivated features, about +5% F1 within one Kansas field |
| Basic well log analysis | American Association of Petroleum Geologists eBooks | yes | 2004 | 916 | 39.8 | mineral endpoint values (chartbook) |
| Well Logging for Earth Scientists | Springer eBooks | yes | 2007 | 1,622 | 81.1 | mineral endpoint values and log physics |
| GLOBAL, A NEW APPROACH TO COMPUTER-PROCESSED LOG INTERPRETATION | SPE Annual Technical Conference and Exhibition | yes | 1980 | 125 | 2.7 | multimineral log inversion (GLOBAL), basis of the M0 reference |
| The reusable holdout: Preserving validity in adaptive data analysis | Science | yes | 2015 | 506 | 42.2 | a rule chosen after seeing a test set needs a fresh holdout (reason for P3c's new wells) |
| Informed Machine Learning - A Taxonomy and Survey of Integrating Prior Knowledge into Learning Systems | IEEE Transactions on Knowledge and Data Engineering | yes | 2021 | 1,173 | 195.5 | integrating prior knowledge with learned models (physics rules plus XGBoost, arm M3) |

## Related Decisions

- ADR-005 (P3 transfer test and gate), ADR-013 (P3b: reader erratum, amended gate, arms M0–M2), ADR-006 (log quality, erratum)

---

## Results

Pending: appended after the one-shot run in §5.
