"""Response contracts shared by the REST API and the MCP tools (ADR-007)."""

from __future__ import annotations

from pydantic import BaseModel


class Meter(BaseModel):
    provider: str
    model: str
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    cached: bool = False


class NotFound(BaseModel):
    not_found: bool = True
    message: str


class Interval(BaseModel):
    rock: str
    top_m: float
    base_m: float
    probability: float


class Lithology(BaseModel):
    well: str
    split: str
    model: str
    blind_score: float
    share_as_interpreted: float
    rock_shares: dict[str, float]
    doubtful_m: int
    doubtful_intervals: int
    intervals: list[Interval]
    meaning: str = "Blind score: average penalty per 0.152 m sample on a well the model never saw; 0 is perfect."


class Quality(BaseModel):
    kgs_id: str
    archive: str
    curves: list[str]
    coverage_gr_neutron_density: float
    out_of_range_share: float | None
    bad_hole_share: float | None
    bad_hole_basis: str
    model_t_confidence_median: float | None
    lithology_validated: bool = False
    caveat: str = "Kansas lithology is not validated: the transfer test failed (ADR-005). Confidence is a drift signal only."


class UnitAgreement(BaseModel):
    unit: str
    expected_rock: str
    gated: bool
    wells_scored: int
    median_agreement: float | None
    lift: float | None
    passed: bool
    predicted_mix_inside: dict[str, float]


class Note(BaseModel):
    subject: str
    note: str
    source: str
    grounded: bool
    meter: Meter
