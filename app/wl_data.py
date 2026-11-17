"""Data access for the Streamlit companion app (R26): the public API and committed results only; no keys, no model."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "outputs"
REPO = "https://github.com/sabrinapribadi/well-log-lithology"
PAGES = "https://sabrinapribadi.github.io/well-log-lithology/"
API = os.environ.get("WLL_API_BASE", "https://well-log-lithology.vercel.app")
UNITS = ["Heebner", "Stone Corral", "Lansing-Kansas City", "Cherokee", "Mississippian", "Arbuckle", "Precambrian", "Hutchinson Salt"]
ROCK = {"Sandstone": "#e8c547", "Sandstone/Shale": "#c2ad6e", "Shale": "#6f8f72", "Marl": "#9fc4a5", "Dolomite": "#a77fb8",
        "Limestone": "#4f9bd9", "Chalk": "#cfe0ea", "Halite": "#e59ab8", "Anhydrite": "#c48ad8", "Tuff": "#d9774f", "Coal": "#8c8c8c",
        "Basement": "#a8432f"}                      # conventional lithology colours; coal lightened to read on a dark page
LEVELS = {0: "no gamma ray", 1: "gamma ray only", 2: "gamma ray, density, neutron", 3: "all five core logs"}


class ApiError(RuntimeError):
    pass


def get(path: str, timeout: float = 45) -> dict:
    url = API.rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "well-log-lithology-streamlit/1.0", "Accept": "application/json"})
    last: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"not_found": True, **json.loads(e.read().decode(errors="replace") or "{}")}
            last = e
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise ApiError(f"{type(last).__name__}: {last}")


def q(x: str) -> str:
    return urllib.parse.quote(str(x), safe="")


def headline() -> dict:
    """Scores from the committed results (ADR-004, ADR-010)."""
    m = json.loads((OUT / "p2_model_choice.json").read_text())["candidates"]["B"]
    s = json.loads((OUT / "p2c_multi_seed.json").read_text())["summary"]["hidden_test"]
    return {"hidden": m["hidden_test"]["penalty_score"], "open": m["open_test"]["penalty_score"], "seed_wins": s["b_wins"],
            "seed_gain": s["diff_mean"], "seed_ci": s["diff_ci95"]}


def kansas_wells() -> list[dict]:
    d = json.loads((OUT / "kgs_wells_summary.json").read_text())
    return [dict(zip(d["columns"], r)) for r in d["rows"]]


def brief() -> list[tuple[str, list[str]]]:
    b = yaml.safe_load((ROOT / "docs/brief.yaml").read_text())
    fix = lambda t: re.sub(r"\]\((?!https?://)([^)]+)\)", lambda m: f"]({REPO}/blob/main/{m.group(1)})", t)  # noqa: E731
    return [(i["w"], [fix(str(x)) for x in i["lines"]]) for i in b["brief"]]


def md_html(text: str) -> str:
    import html as _h
    t = _h.escape(text, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank">\1</a>', t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
