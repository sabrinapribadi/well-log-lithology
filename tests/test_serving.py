"""ADR-007 contract tests: REST API and MCP tools in template mode (no API key, small fixture store)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIX = Path(__file__).parent / "fixtures" / "store_small.json"
os.environ["WLL_STORE"] = str(FIX)

from src.serving import api  # noqa: E402
from src.serving.notes import NoteService, grade  # noqa: E402
from src.serving.store import Store  # noqa: E402
from src.serving.tools import REGISTRY, Tools  # noqa: E402


@pytest.fixture(scope="module")
def client():
    t = Tools(Store(FIX), NoteService(None))
    api.tools.cache_clear()
    api.app.dependency_overrides = {}
    api.tools = lambda: t   # template mode, fixture store
    return TestClient(api.app)


def test_health_says_kansas_lithology_not_validated(client):
    r = client.get("/health").json()
    assert r["ok"] and r["kansas_lithology_validated"] is False and r["force_wells"] == 2


def test_lithology_for_a_force_well_and_404_otherwise(client):
    r = client.get("/wells/15/9-23/lithology")
    assert r.status_code == 200 and r.json()["intervals"] and r.json()["blind_score"] <= 0
    assert client.get("/wells/NOPE/lithology").status_code == 404


def test_kansas_quality_carries_the_caveat(client):
    kid = next(iter(Store(FIX).kansas))
    r = client.get(f"/kansas/{kid}/quality").json()
    assert r["lithology_validated"] is False and "not validated" in r["caveat"]
    assert client.get("/kansas/0/quality").status_code == 404


def test_unit_agreement_reports_the_failed_test(client):
    r = client.get("/units/Arbuckle").json()
    assert r["expected_rock"] == "Dolomite" and r["passed"] is False


def test_notes_are_grounded_in_template_mode(client):
    for subject in ["15/9-23", next(iter(Store(FIX).kansas))]:
        r = client.get(f"/wells/{subject}/note").json()
        assert r["grounded"] and r["source"] == "template" and r["meter"]["cost_usd"] == 0


def test_mcp_registry_matches_tools():
    t = Tools(Store(FIX), NoteService(None))
    assert all(callable(getattr(t, n)) for n in REGISTRY)
    from src.serving.mcp_server import build_server
    assert build_server(t) is not None


def test_grader_rejects_invented_numbers():
    facts = {"subject_type": "force_well", "well": "15/9-23", "blind_score": -0.395, "doubtful_m": 45}
    assert grade("Blind score -0.40; 45 m doubtful.", facts)["ok"]
    assert not grade("Blind score -0.41; 300 m doubtful.", facts)["ok"]
