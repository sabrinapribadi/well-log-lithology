"""Streamlit app (R26, app template v2): first screen, navigation, every page and the agent chat, offline on recorded API answers; no key."""
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


def run(page=None, **state):
    at = AppTest.from_file(APP, default_timeout=90)
    if page:
        at.session_state["page"] = page
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


PAGES = ["overview", "explore", "well", "quality", "transfer", "agent"]


def html_text(at) -> str:
    return " ".join(e.proto.body for e in at.get("html"))


def test_first_screen():
    at = run()
    h = D.headline()
    assert [m.value for m in at.metric][:4] == [f"{h['hidden']:.3f}", f"{h['open']:.3f}", "10 of 10 seeds", "0 of 6"]
    assert any("12 hours" in c.value for c in at.caption)
    page = html_text(at)
    for w in ["What", "Why", "Who", "Where", "When it fails", "How"]:          # the 5W1H brief (R22)
        assert f'class="f-w">{w}<' in page, w
    assert [b.key for b in at.sidebar.button] == [f"nav_{k}" for k in PAGES]
    assert [b.key for b in at.button if b.key.startswith("go_")] == [f"go_{k}" for k in PAGES[1:]]


def test_every_page_opens_with_its_business_question():
    for key in PAGES[1:]:
        at = run(key)
        assert "Business question" in html_text(at), key
        assert at.query_params["page"] == [key] or at.query_params["page"] == key


def test_navigation_and_deep_link():
    at = run()
    at.sidebar.button(key="nav_transfer").click().run()
    assert not at.exception and at.session_state["page"] == "transfer"
    at = AppTest.from_file(APP, default_timeout=90)
    at.query_params["page"] = "explore"
    at.run()
    assert not at.exception and at.session_state["page"] == "explore"
    assert any(s.value.startswith("FORCE 2020 North Sea") for s in at.subheader)


def test_well_and_kansas_pages():
    at = run("well")
    assert at.subheader[0].value.startswith("15/9-23: hidden test well, blind score -0.395")
    assert len(at.dataframe[0].value) == 10                                    # the ten thickest doubtful intervals
    at = run("transfer")
    assert at.subheader[0].value.startswith("No Kansas unit passed: 6 gated units")
    assert any(s.value.startswith("The retest (P3b): 3 of 6 on 601 fresh files") for s in at.subheader)   # ADR-013
    assert any(s.value.startswith("The second retest (P3c): 2 of 6 on 589 new fresh files") for s in at.subheader)   # ADR-014
    at = run("quality")
    assert "not validated" in at.warning[0].value
    at = run("explore")
    assert any("Kansas LAS archive" in s.value for s in at.subheader)


def test_replays_recorded_grounded_and_keyless():
    d = json.loads((ROOT / "app" / "replays.json").read_text())
    assert [r["question"] for r in d["runs"]] == AT.QUESTIONS and all(r["grounded"] for r in d["runs"])
    assert "sk-" not in (ROOT / "app" / "replays.json").read_text()


def test_agent_replay_and_live_stub(monkeypatch):
    at = run("agent")
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
    at = run("agent")
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


def test_frame_is_the_shared_copy():
    """The app frame is identical in every portfolio app; change it everywhere at once (checksum of the shared copy)."""
    import hashlib
    assert hashlib.sha256((ROOT / "app" / "frame.py").read_bytes()).hexdigest()[:16] == "385e92329f20405a"
