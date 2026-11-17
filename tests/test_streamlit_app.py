"""Streamlit app (R26): first screen, every tab and the agent chat, offline on recorded API answers; no key."""
import io
import json
import sys
import types
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
pytest.importorskip("streamlit")
import agent as A  # noqa: E402
import agent_tools as AT  # noqa: E402
import wl_data as D  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "app" / "streamlit_app.py")
FIX = json.loads((ROOT / "tests" / "fixtures" / "app_api.json").read_text())


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake(req, timeout=None):
        key = req.full_url.split(D.API.rstrip("/"), 1)[1]
        if key not in FIX:
            raise urllib.error.URLError(f"not recorded: {key}")
        return _Resp(json.dumps(FIX[key]).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.setattr(D, "time", types.SimpleNamespace(sleep=lambda s: None))


def run(view=None, **state):
    at = AppTest.from_file(APP, default_timeout=90)
    if view:
        at.session_state["view"] = view
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def test_first_screen_and_well_column():
    at = run()
    h = D.headline()
    assert [m.value for m in at.metric][:4] == [f"{h['hidden']:.3f}", f"{h['open']:.3f}", "10 of 10 seeds", "0 of 6"]
    assert any("12 hours" in c.value for c in at.caption)
    assert at.subheader[0].value.startswith("15/9-23: hidden test well, blind score -0.395")


def test_kansas_tabs():
    at = run("Kansas transfer test")
    assert at.subheader[0].value.startswith("No Kansas unit passed: 6 gated units")
    at = run("Kansas log quality")
    assert at.subheader[0].value.startswith("24,166 Kansas LAS files") and "not validated" in at.warning[0].value


def test_replays_recorded_grounded_and_keyless():
    d = json.loads((ROOT / "app" / "replays.json").read_text())
    assert [r["question"] for r in d["runs"]] == AT.QUESTIONS and all(r["grounded"] for r in d["runs"])
    assert "sk-" not in (ROOT / "app" / "replays.json").read_text()


def test_agent_replay_and_live_stub(monkeypatch):
    at = run("Ask the agent")
    assert at.radio(key="chat_mode").value.startswith("Replay")
    at.selectbox(key="replay_pick").set_value(AT.QUESTIONS[0]).run()
    first = json.loads((ROOT / "app" / "replays.json").read_text())["runs"][0]["answer"]
    assert not at.exception and any(first[:40] in m.value for m in at.markdown)
    key = "sk" + "-" + "test-viewerkey-123456"                         # fake, built at runtime
    seen = {}

    def fake(q, client, tools, system, model, prices, **kw):
        seen["key"] = client.api_key
        return {"question": q, "answer": "Live answer.", "tool_calls": [], "tool_results": [], "steps": 1, "grounded": True,
                "ungrounded_numbers": [], "model": model, "tokens": {"input": 1, "cached_input": 0, "output": 1}, "cost_usd": 0.0, "latency_ms": 1.0}
    monkeypatch.setattr(A, "run", fake)
    at = run("Ask the agent")
    at.radio(key="chat_mode").set_value("Live: use your own OpenAI key").run()
    at.text_input(key="byo_key").input(key).run()
    at.chat_input(key="live_input").set_value("Anything").run()
    assert seen["key"] == key and any("Live answer." in m.value for m in at.markdown)
    assert key not in " ".join(m.value for m in at.markdown)


def test_app_agent_tools_match_registry():
    import inspect
    tools_mod = pytest.importorskip("src.serving.tools")
    assert [s["name"] for s in AT.SCHEMAS] == list(tools_mod.REGISTRY)
    for s in AT.SCHEMAS:
        params = [p for p in inspect.signature(getattr(tools_mod.Tools, s["name"])).parameters if p != "self"]
        assert sorted(s["parameters"]["properties"]) == sorted(params), s["name"]
