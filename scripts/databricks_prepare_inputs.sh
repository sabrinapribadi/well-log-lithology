#!/usr/bin/env bash
# Upload P6 inputs to the Unity Catalog volume workspace.og2.inputs (ADR-008). Needs WLL_DATA_DIR and the CLI profile.
#   bash scripts/databricks_prepare_inputs.sh [force|archives|drift|all]
set -euo pipefail
P=${DATABRICKS_PROFILE:-portfolio}; V=dbfs:/Volumes/workspace/og2/inputs; D=${WLL_DATA_DIR:?set WLL_DATA_DIR}
what=${1:-all}
databricks schemas create og2 workspace -p "$P" 2>/dev/null || true
databricks volumes create workspace og2 inputs MANAGED -p "$P" 2>/dev/null || true
databricks volumes create workspace og2 outputs MANAGED -p "$P" 2>/dev/null || true
if [[ $what == force || $what == all ]]; then
  for f in force_train force_hidden_test p2_predictions; do databricks fs cp --overwrite "$D/derived/$f.parquet" "$V/$f.parquet" -p "$P"; done
  databricks fs cp --overwrite "$D/models/p3_transfer_T.json" "$V/p3_transfer_T.json" -p "$P"
fi
if [[ $what == archives || $what == all ]]; then
  databricks fs cp --overwrite "$D/kgs/las_zips/2026.zip" "$V/2026.zip" -p "$P"
fi
if [[ $what == drift || $what == all ]]; then
  "${PY:-python}" scripts/p6_drift_reference.py   # ≤ 20,000 rows per year from the P4 drift sample
  databricks fs cp --overwrite "$D/derived/p6_drift_reference.parquet" "$V/p6_drift_reference.parquet" -p "$P"
fi
