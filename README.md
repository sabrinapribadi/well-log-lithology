# Well-Log Lithology

**Does a lithology model trained on North Sea wells label Kansas wells correctly, and how good is it on wells it never saw?**

- Train on 98 labelled North Sea wells (FORCE 2020); judge on 10 hidden wells with the industry's penalty for geologically "far" mistakes.
- Test transfer to ~28,900 public Kansas LAS files against formation tops and known unit lithology.
- Deliver lithology curves per well (LAS), a well map, and later an API, AI tools and a scheduled cloud job.

**Status:** design pushed (ADR-001–003); P0 next. Details: [docs/PRD.md](docs/PRD.md), [decision records](docs/adr/README.md), [CHANGELOG.md](CHANGELOG.md).

## Data

| Source | Licence |
|---|---|
| FORCE 2020 well log and lithofacies dataset (Zenodo 4351156) | CC BY 4.0 |
| Kansas Geological Survey LAS archive, wells, formation tops | Free use with citation (KGS terms of use) |

Raw data lives outside the repository (`WLL_DATA_DIR`). Code is MIT-licensed.
