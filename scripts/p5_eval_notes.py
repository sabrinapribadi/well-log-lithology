"""P5 live evaluation of grounded notes (ADR-007, rule R13).

    python scripts/p5_eval_notes.py          # needs OPENAI_API_KEY in .env

Cases: the 20 FORCE test wells and 40 Kansas wells drawn at random (seed 42). Each case gets a live note (no cache),
graded for grounding and required facts; served notes fall back to the template when a draft fails. Then a second,
cached pass measures cached latency. Writes data/outputs/p5_notes_eval.json and fills the notes cache.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.serving.notes import NoteService, coverage, force_facts, kansas_facts  # noqa: E402
from src.serving.store import Store  # noqa: E402
from src.serving.tools import CFG, writer_from_config  # noqa: E402


def main() -> None:
    w = writer_from_config()
    if w is None:
        sys.exit("OPENAI_API_KEY missing: live evaluation needs it (templates are tested in CI).")
    store = Store()
    cache = Path(os.environ["WLL_DATA_DIR"]) / "serving" / "notes_cache.json"
    svc = NoteService(w, cache)
    kan = sorted(store.kansas); random.Random(42).shuffle(kan)
    cases = [force_facts(v) for v in store.force.values()] + [kansas_facts(store.kansas[k]) for k in kan[:40]]
    rows = []
    for f in cases:
        note, source, g, meter, raw = svc.note(f, use_cache=False)
        rows.append({"subject": f.get("well") or f.get("kgs_id"), "type": f["subject_type"], "source": source, "draft_ok": g["ok"],
                     "served_ok": g["served_ok"], "unknown": g["unknown_numbers"], "coverage": coverage(note, f)["all"],
                     "latency_ms": meter.latency_ms, "cost_usd": meter.cost_usd, "in": meter.input_tokens, "out": meter.output_tokens,
                     "note": note, "raw": raw})
    svc.save()
    cached = []
    for f in cases:
        t0 = time.perf_counter(); svc.note(f); cached.append((time.perf_counter() - t0) * 1000)
    live = [r for r in rows if r["latency_ms"] > 0]
    n = CFG["notes"]
    res = {"design": "ADR-007", "model": w.model, "prices_retrieved": "2026-11-09", "cases": len(rows),
           "live_calls": len(live), "live_draft_pass_rate": float(np.mean([r["draft_ok"] for r in rows])),
           "served_grounded_rate": float(np.mean([r["served_ok"] for r in rows])),
           "required_fact_coverage": float(np.mean([r["coverage"] for r in rows])),
           "served_by_template": int(sum(r["source"] == "template" for r in rows)),
           "cost_per_1000_usd": float(1000 * np.mean([r["cost_usd"] for r in live])) if live else None,
           "p50_ms_live": float(np.percentile([r["latency_ms"] for r in live], 50)) if live else None,
           "p95_ms_live": float(np.percentile([r["latency_ms"] for r in live], 95)) if live else None,
           "p95_ms_cached": float(np.percentile(cached, 95)),
           "budgets": {"cost_per_1000": n["budget_cost_per_1000"], "p95_ms_live": n["budget_p95_ms_live"], "p95_ms_cached": n["budget_p95_ms_cached"]},
           "examples": rows[:3] + rows[20:22], "failures": [r for r in rows if not r["draft_ok"]][:10]}
    res["within_budget"] = bool(res["cost_per_1000_usd"] is not None and res["cost_per_1000_usd"] <= n["budget_cost_per_1000"]
                                and res["p95_ms_live"] <= n["budget_p95_ms_live"] and res["p95_ms_cached"] <= n["budget_p95_ms_cached"])
    res["gate_notes"] = bool(res["served_grounded_rate"] == 1.0 and res["cases"] >= 60 and res["within_budget"])
    (ROOT / CFG["paths"]["outputs_dir"] / "p5_notes_eval.json").write_text(json.dumps(res, indent=1))
    print({k: res[k] for k in ("cases", "live_draft_pass_rate", "served_grounded_rate", "required_fact_coverage", "served_by_template",
                               "cost_per_1000_usd", "p50_ms_live", "p95_ms_live", "p95_ms_cached", "within_budget", "gate_notes")})


if __name__ == "__main__":
    main()
