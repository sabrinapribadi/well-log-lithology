# ADR-011: Public API, Remote MCP and Technology Assessment (R19–R21)

**Status:** Accepted
**Date:** 2026-11-11
**Deciders:** Sabrina Pribadi

---

## Context and Problem Statement

- P5 built a lithology API, MCP tools and grounded notes, but only locally.
- Portfolio rules now require CI/CD (R19), zero hosting cost (R20) and an evidence-based technology assessment (R21).
- **Question:** how do hiring teams and AI assistants reach the tools publicly, for $0, using current standards?

## Decision Drivers

- Free tiers only; no API key on any public host (public traffic must never spend tokens).
- The same code paths as P5 (`src/serving`), tested before deploy.
- Current standards: MCP specification 2026-07-28 (stateless core, Streamable HTTP).

## Decision

### 1. Public deployment

- **App:** `src/serving/public.py`: the read-only REST tools plus the same four tools as a remote MCP endpoint at `/mcp`, stateless with JSON responses (MCP 2026-07-28; Python SDK 2.3.0).
- **Notes:** cached LLM notes when present, otherwise the template. No model is called and no key is deployed.
- **Not public:** LAS upload and prediction (the model file stays off the free host; it runs locally).
- **Bundle:** `scripts/build_deploy.py` assembles serving code, config, the serving snapshot (0.5 MB, SHA-256 in `deploy/`) and four dependencies (FastAPI, MCP, pydantic, PyYAML). Tested in a clean environment.
- **Host:** Vercel Hobby (free, non-commercial; FastAPI supported natively). The results page stays the static fallback (R20).

### 2. CD (R19)

- On push to `main` after CI passes: build the bundle, sign its build provenance (GitHub artifact attestations), deploy, then smoke-test `/health` and an MCP `tools/list` on the live URL.

### 3. Databricks App (platform demonstration)

- The same app as a Databricks App in Free Edition (up to 3 apps, 24 hours per run), deployed by the existing bundle. Databricks Apps require a workspace login, so this shows platform deployment; the public URL stays on Vercel.

### 4. Technology assessment (portfolio plan §10)

| Technology | Rating | Where in OG-2 |
|---|---|---|
| CI/CD + build provenance | Adopt | All workflows (§2) |
| Remote MCP, 2026-07-28 spec | Adopt | `/mcp` on the public app |
| Prompt-injection tests on tools | Adopt | Tools take IDs only; tests check that instructions inside inputs are ignored and never echoed as actions |
| OpenTelemetry GenAI traces | Adopt | Every note generation emits `chat` spans with tokens, latency and cost |
| Databricks Apps | Adopt (platform demo) | §3 |
| Multi-agent over A2A | Trial | Only with a pre-registered question that needs two agents; separate ADR |
| Domain-specific or small models | Hold | No labelled explanation data |

## Considered Options

| Option | Status | Why |
|---|---|---|
| **Vercel Hobby + static fallback** | **Chosen** | Free, FastAPI-native, deploys from CI |
| Render | Rejected | Paid instances bill while idle (portfolio R20) |
| Databricks Apps as the public URL | Rejected | Requires workspace login; 24-hour runs |
| Google Cloud Run | Not chosen | Free allowance, but a billing account (card) is required |
| Live LLM notes on the public host | Rejected | Public traffic could spend tokens |

## Consequences

- **Positive:** hiring teams and AI assistants can call real tools; cost stays $0.
- **Negative:** cold starts on a free host; notes for wells outside the cache are templates.

## Related Decisions

- ADR-007 (API, MCP, notes; amendment 1), ADR-008 (Databricks job)

## Evidence

| Source | Issuer | Used for |
|---|---|---|
| The 2026-07-28 Specification (MCP blog) | Model Context Protocol | Stateless core, Streamable HTTP |
| Deploy a FastAPI app on Vercel (docs, updated 2026-08-27) | Vercel | Hosting |
| Free Edition limitations (docs) | Databricks | Apps limits |
| Artifact attestations (docs) | GitHub | Build provenance, free for public repositories |
| Top Strategic Technology Trends for 2026 (press release, 20 Oct 2025) | Gartner | Multi-agent systems, AI security platforms, digital provenance |
