"""OpenTelemetry GenAI traces for notes and tools (ADR-011; OpenTelemetry GenAI semantic conventions).

- `chat {model}` span per language-model call: provider, model, max tokens, input / cached input / output tokens.
- `execute_tool {name}` span per MCP or REST tool call.
- Project attributes (prefix `wll.`): cost in US dollars, latency, note source, grader result.
- Optional: without the OpenTelemetry API installed (e.g. the public host) every span is a no-op.

    python scripts/p5_eval_notes.py --trace data/outputs/traces.jsonl    # one JSON span per line
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

try:
    from opentelemetry import trace
except ImportError:            # public bundle ships without OpenTelemetry
    trace = None

_TRACER = trace.get_tracer("well-log-lithology") if trace else None


class _NoSpan:
    def set_attribute(self, *_):
        pass

    def set_attributes(self, *_):
        pass


@contextlib.contextmanager
def span(name: str, **attrs):
    """A span with the given attributes (None values dropped); a no-op without OpenTelemetry."""
    if _TRACER is None:
        yield _NoSpan()
        return
    with _TRACER.start_as_current_span(name) as s:
        s.set_attributes({k: v for k, v in attrs.items() if v is not None})
        yield s


def chat_span(provider: str, model: str, max_tokens: int | None):
    return span(f"chat {model}", **{"gen_ai.operation.name": "chat", "gen_ai.provider.name": provider,
                                    "gen_ai.request.model": model, "gen_ai.request.max_tokens": max_tokens})


def record_usage(s, meter) -> None:
    s.set_attributes({"gen_ai.response.model": meter.model, "gen_ai.usage.input_tokens": meter.input_tokens,
                      "gen_ai.usage.cache_read.input_tokens": meter.cached_input_tokens,
                      "gen_ai.usage.output_tokens": meter.output_tokens,
                      "wll.cost_usd": meter.cost_usd, "wll.latency_ms": meter.latency_ms})


def tool_span(name: str):
    return span(f"execute_tool {name}", **{"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name})


def setup_jsonl(path: Path):
    """Install an SDK tracer provider writing one JSON span per line to `path`. Returns the provider (call shutdown())."""
    global _TRACER
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

    class JsonlExporter(SpanExporter):
        def __init__(self, p: Path):
            self.f = p.open("a")

        def export(self, spans):
            for s in spans:
                self.f.write(json.dumps({"name": s.name, "trace_id": f"{s.context.trace_id:032x}",
                                         "parent": f"{s.parent.span_id:016x}" if s.parent else None,
                                         "duration_ms": round((s.end_time - s.start_time) / 1e6, 3),
                                         "status": s.status.status_code.name, "attributes": dict(s.attributes)}) + "\n")
            self.f.flush()
            return SpanExportResult.SUCCESS

        def shutdown(self):
            self.f.close()

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(JsonlExporter(Path(path))))
    _TRACER = provider.get_tracer("well-log-lithology")
    return provider


def use_provider(provider) -> None:
    """Route spans to a given SDK provider (tests use an in-memory exporter)."""
    global _TRACER
    _TRACER = provider.get_tracer("well-log-lithology")
