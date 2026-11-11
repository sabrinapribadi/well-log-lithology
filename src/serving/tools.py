"""Lithology copilot tools (ADR-007, amendment 1): one registry for the REST API and the MCP server.

Validated outputs only: North Sea lithology from model B; Kansas data quality from P4; the failed Kansas transfer test.
"""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path

import yaml

from src.serving.contracts import Lithology, Note, NotFound, Quality, UnitAgreement
from src.serving.notes import NoteService, OpenAIWriter, force_facts, kansas_facts
from src.serving.store import Store
from src.serving.telemetry import tool_span

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "configs" / "default_config.yaml").read_text())
REGISTRY = ["predict_lithology", "well_quality", "unit_agreement", "explain_well"]
MAX_ID = 40                                         # longest FORCE name, KGS ID or unit is 19 characters
SAFE_ID = re.compile(r"[A-Za-z0-9 /._-]{1,%d}" % MAX_ID)


def shown(x: str) -> str:
    """Echo an input in a reply only if it looks like an identifier; anything else (e.g. instructions) is never repeated
    back to the calling assistant (prompt-injection defence, ADR-011)."""
    return f"'{x}'" if SAFE_ID.fullmatch(str(x)) else "the given input (not an identifier)"


def traced(f):
    """One `execute_tool {name}` span per call; inputs longer than an identifier are refused before any lookup."""
    @functools.wraps(f)
    def call(self, *args, **kw):
        (arg,) = (*args, *kw.values())                 # each tool takes one identifier, by position or by name
        with tool_span(f.__name__) as sp:
            if not isinstance(arg, str) or len(arg) > MAX_ID:
                sp.set_attribute("wll.refused", True)
                return NotFound(message=f"Not an identifier: inputs are at most {MAX_ID} characters (a well name, KGS ID or unit).")
            r = f(self, arg)
            sp.set_attribute("wll.found", not isinstance(r, NotFound))
            return r
    return call


def writer_from_config() -> OpenAIWriter | None:
    n = CFG["notes"]
    if n["provider"] != "openai" or not os.environ.get("OPENAI_API_KEY"):
        return None
    return OpenAIWriter(model=n["model"], price_in=n["price_input_per_m"], price_cached_in=n["price_cached_input_per_m"],
                        price_out=n["price_output_per_m"], max_output_tokens=n["max_output_tokens"], reasoning_effort=n["reasoning_effort"],
                        timeout=n["timeout_s"])


class Tools:
    def __init__(self, store: Store | None = None, notes: NoteService | None = None):
        self.store = store or Store()
        if notes is None:
            cache = Path(os.environ.get("WLL_DATA_DIR", "~/data/well-log-lithology")).expanduser() / "serving" / "notes_cache.json"
            notes = NoteService(writer_from_config(), cache if cache.parent.exists() else None)
        self.notes = notes

    @traced
    def predict_lithology(self, well: str) -> Lithology | NotFound:
        """Lithology column predicted by model B for a FORCE North Sea test well (e.g. '15/9-23'): intervals with rock,
        top and base in metres and probability; rock shares; doubtful intervals; the well's blind score (0 is perfect)."""
        w = self.store.force.get(well)
        if w is None:
            return NotFound(message=f"No FORCE test well {shown(well)}. Lithology is served for the 20 open and hidden FORCE wells; Kansas lithology is not validated.")
        return Lithology(**{k: w[k] for k in Lithology.model_fields if k in w})

    @traced
    def well_quality(self, kgs_id: str) -> Quality | NotFound:
        """Log quality of a Kansas well by KGS ID (e.g. '1001184201'): curves present, coverage of gamma ray, neutron and
        density, share of values outside physical ranges, hole condition. Kansas lithology is not validated."""
        k = self.store.kansas.get(str(kgs_id))
        if k is None:
            return NotFound(message=f"No Kansas well with KGS ID {shown(kgs_id)} in the LAS archive inventory.")
        return Quality(**{f: k[f] for f in Quality.model_fields if f in k})

    @traced
    def unit_agreement(self, unit: str) -> UnitAgreement | NotFound:
        """Result of the Kansas transfer test for a named unit (e.g. 'Hutchinson Salt', 'Arbuckle', 'Heebner'): share of
        the unit predicted as its known rock, lift versus the rest of the well, and whether it passed."""
        u = next((v for k, v in self.store.units.items() if k.lower() == unit.lower()), None)
        if u is None:
            return NotFound(message=f"Unknown unit {shown(unit)}. Units: {', '.join(self.store.units)}.")
        return UnitAgreement(**u)

    @traced
    def explain_well(self, well_or_kgs_id: str) -> Note | NotFound:
        """A short grounded note: for a FORCE test well, its column, blind score and doubtful metres; for a Kansas well,
        its log quality and why its lithology is not validated. Every number comes from the store."""
        if well_or_kgs_id in self.store.force:
            facts = force_facts(self.store.force[well_or_kgs_id])
        elif str(well_or_kgs_id) in self.store.kansas:
            facts = kansas_facts(self.store.kansas[str(well_or_kgs_id)])
        else:
            return NotFound(message=f"{shown(well_or_kgs_id)} is neither a FORCE test well nor a Kansas KGS ID.")
        note, source, g, meter, _ = self.notes.note(facts)
        return Note(subject=str(well_or_kgs_id), note=note, source=source, grounded=g["served_ok"], meter=meter)
