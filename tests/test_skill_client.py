"""Agent skill client (R24): routes, id quoting, charts and skill files, with the network stubbed out."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "skills/well-log-lithology"
SPEC = importlib.util.spec_from_file_location("wll_client", ROOT / "scripts/wll.py")
wll = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wll)

LITH = {"well": "15/9-23", "split": "hidden", "blind_score": -0.395, "share_as_interpreted": 0.829, "doubtful_m": 45,
        "rock_shares": {"Shale": 0.722, "Limestone": 0.172, "Coal": 0.004},
        "intervals": [{"rock": "Shale", "top_m": 1518.0, "base_m": 2000.0, "probability": 0.9},
                      {"rock": "Limestone", "top_m": 2000.0, "base_m": 2100.0, "probability": 0.45},
                      {"rock": "Coal", "top_m": 2100.0, "base_m": 2101.0, "probability": 0.6}]}
UNIT = {"unit": "Heebner", "expected_rock": "Shale", "gated": True, "wells_scored": 289, "median_agreement": 0.9, "lift": 1.57, "passed": False}


def fake(base, path, timeout=60):
    if path == "/":
        return {"force_wells": ["15/9-23"], "kansas_wells": 24158, "kansas_lithology_validated": False, "results_page": "x"}
    if path.startswith("/wells/") and path.endswith("/lithology"):
        return LITH
    if path.startswith("/units/"):
        return UNIT
    return {"ok": True}


@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(wll, "get", lambda base, path, timeout=60: seen.append(path) or fake(base, path))
    return seen


def test_routes_quote_ids(calls, capsys):
    wll.main(["lithology", "15/9-23"]); wll.main(["quality", "1001184201"]); wll.main(["unit", "Hutchinson Salt"]); wll.main(["note", "15/9-23"])
    assert calls == ["/wells/15%2F9-23/lithology", "/kansas/1001184201/quality", "/units/Hutchinson%20Salt", "/wells/15%2F9-23/note"]
    assert capsys.readouterr().out.count("{") >= 4


def test_about_states_scores_and_kansas_caveat(calls):
    ab = wll.about("x")
    assert ab["hidden_score"] == -0.504 and "0 is perfect" in ab["score_meaning"] and ab["kansas_lithology_validated"] is False
    assert "24,158" in wll.data_line(ab) and "-0.504" in wll.data_line(ab)


def test_charts_offline(calls, tmp_path):
    out = tmp_path / "c.html"
    wll.main(["chart", "column", "15/9-23", "--out", str(out)])
    page = out.read_text()
    assert page.count('class="bar"') == 3 and 'url(#hatch)' in page and "Shale 72%" in page and "Coal &lt;1%" in page
    wll.main(["chart", "units", "--out", str(out)])
    page = out.read_text()
    assert page.count('class="bar"') == len(wll.UNITS) and "50% pass line" in page


def test_skill_files():
    head = (ROOT / "SKILL.md").read_text().split("---")[1]
    assert "name: well-log-lithology" in head and "description:" in head
    cases = [p for p in (ROOT / "evals").iterdir() if p.is_dir()]
    assert len(cases) >= 4 and all((c / "prompt.md").exists() and (c / "case.yaml").exists() and any((c / "graders").glob("*.md")) for c in cases)
    trig = json.loads((ROOT / "trigger-evals.json").read_text())
    assert sum(t["should_trigger"] for t in trig) >= 8 and sum(not t["should_trigger"] for t in trig) >= 8
