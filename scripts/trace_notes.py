"""Live trace check for grounded notes (ADR-011, rules R13 and R21): OpenTelemetry GenAI spans for the 20 FORCE wells.

    python scripts/trace_notes.py            # needs OPENAI_API_KEY in .env; about 20 calls (≈ $0.002)

Checks that every live call left a `chat` span carrying tokens and cost, nested under its `notes.explain` and
`execute_tool` spans, and that span costs add up to the meters. Writes data/outputs/traces_notes.jsonl and
data/outputs/traces_summary.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.serving import telemetry  # noqa: E402
from src.serving.notes import NoteService  # noqa: E402
from src.serving.store import Store  # noqa: E402
from src.serving.tools import CFG, Tools, writer_from_config  # noqa: E402


def main() -> None:
    w = writer_from_config()
    if w is None:
        sys.exit("OPENAI_API_KEY missing: the live trace check needs it (spans are tested in CI with a fake model).")
    out = ROOT / CFG["paths"]["outputs_dir"]
    path = out / "traces_notes.jsonl"; path.unlink(missing_ok=True)
    provider = telemetry.setup_jsonl(path)
    tools = Tools(Store(), NoteService(w))            # no cache: every note is a live call
    meters = [tools.explain_well(well).meter for well in sorted(tools.store.force)]
    provider.shutdown()
    spans = [json.loads(line) for line in path.read_text().splitlines()]
    chat = [s for s in spans if s["attributes"].get("gen_ai.operation.name") == "chat"]
    live = [m for m in meters if m.provider == "openai"]
    req = ("gen_ai.provider.name", "gen_ai.request.model", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "wll.cost_usd")
    ids = {s["parent"] for s in chat}
    res = {"design": "ADR-011", "model": w.model, "calls": len(meters), "live_calls": len(live), "chat_spans": len(chat),
           "spans_with_required_attributes": sum(all(k in s["attributes"] for k in req) for s in chat),
           "chat_spans_nested": len(ids) == len(chat) and None not in ids,
           "span_cost_usd": round(sum(s["attributes"]["wll.cost_usd"] for s in chat), 8),
           "meter_cost_usd": round(sum(m.cost_usd for m in live), 8),
           "cost_per_1000_usd": round(1000 * float(np.mean([m.cost_usd for m in live])), 4) if live else None,
           "p95_ms_live": round(float(np.percentile([m.latency_ms for m in live], 95)), 1) if live else None,
           "span_names": sorted({s["name"] for s in spans})}
    res["pass"] = bool(live and res["chat_spans"] == res["live_calls"] == res["spans_with_required_attributes"]
                       and res["chat_spans_nested"] and abs(res["span_cost_usd"] - res["meter_cost_usd"]) < 1e-9)
    (out / "traces_summary.json").write_text(json.dumps(res, indent=1))
    print(res)


if __name__ == "__main__":
    main()
