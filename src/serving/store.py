"""Read-only serving store built by scripts/p5_build_store.py (ADR-007)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def store_path() -> Path:
    if os.environ.get("WLL_STORE"):
        return Path(os.environ["WLL_STORE"])
    return Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "serving" / "store.json"


class Store:
    def __init__(self, path: Path | None = None):
        d = json.loads((path or store_path()).read_text())
        self.force, self.kansas, self.units, self.meta = d["force"], d["kansas"], d["units"], d["meta"]
