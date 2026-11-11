"""Public, read-only deployment of the lithology API and MCP server (rules R19, R20; ADR-011).

    uvicorn src.serving.public:app --port 8000     # locally; CD deploys the same app to a free host

- REST: the read-only tools of src/serving/api.py (no LAS upload: the model file stays off the free host).
- MCP: the same four tools over Streamable HTTP at /mcp, stateless (MCP 2026-07-28), so it runs on serverless hosts.
- Notes: cached or template only. No API key is deployed, so public traffic can never spend tokens (R13, R20).
"""

from __future__ import annotations

import contextlib
import os

from fastapi import FastAPI, HTTPException
from mcp.server.transport_security import TransportSecuritySettings

from src.serving.contracts import Lithology, Note, NotFound, Quality, UnitAgreement
from src.serving.mcp_server import build_server
from src.serving.notes import NoteService
from src.serving.store import Store, store_path
from src.serving.tools import CFG, Tools

# writer=None: never calls a model; serves notes cached for the configured model, else the template
TOOLS = Tools(Store(), NoteService(None, store_path().with_name("notes_cache.json"), cache_model=CFG["notes"]["model"]))


def allowed_hosts() -> list[str]:
    """DNS-rebinding protection stays on: only localhost and this deployment's own hostnames reach /mcp.
    Vercel sets VERCEL_URL (this deployment) and VERCEL_PROJECT_PRODUCTION_URL; WLL_ALLOWED_HOSTS adds more (comma-separated;
    the Databricks App sets it in app.yaml, because Databricks Apps expose no URL variable)."""
    hosts = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]
    for v in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        if os.environ.get(v):
            hosts.append(os.environ[v])
    hosts += [h.strip() for h in os.environ.get("WLL_ALLOWED_HOSTS", "").split(",") if h.strip()]
    return hosts


SECURITY = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts(),
                                     allowed_origins=[f"{s}://{h.removesuffix(':*')}" + (":*" if h.endswith(":*") else "")
                                                      for h in allowed_hosts() for s in ("http", "https")])
MCP = build_server(TOOLS).streamable_http_app(stateless_http=True, json_response=True, streamable_http_path="/", transport_security=SECURITY)


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    async with MCP.router.lifespan_context(MCP):      # the MCP session manager's task group
        yield


app = FastAPI(title="Well-Log Lithology API", version="1", lifespan=lifespan,
              description="North Sea lithology from a blind-tested model (FORCE 2020), Kansas log quality, and the Kansas "
                          "transfer test result. Read-only; notes are cached or templated. MCP endpoint: /mcp.")
app.mount("/mcp", MCP)


def _or_404(r):
    if isinstance(r, NotFound):
        raise HTTPException(status_code=404, detail=r.message)
    return r


@app.get("/")
def root() -> dict:
    return {"name": "well-log-lithology", "docs": "/docs", "mcp": "/mcp", "force_wells": sorted(TOOLS.store.force),
            "kansas_wells": len(TOOLS.store.kansas), "kansas_lithology_validated": False,
            "results_page": "https://sabrinapribadi.github.io/well-log-lithology/"}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "notes": "cached or template (no LLM calls on this host)"}


@app.get("/wells/{well:path}/lithology", response_model=Lithology)
def lithology(well: str):
    return _or_404(TOOLS.predict_lithology(well))


@app.get("/kansas/{kgs_id}/quality", response_model=Quality)
def quality(kgs_id: str):
    return _or_404(TOOLS.well_quality(kgs_id))


@app.get("/units/{unit}", response_model=UnitAgreement)
def unit(unit: str):
    return _or_404(TOOLS.unit_agreement(unit))


@app.get("/wells/{well:path}/note", response_model=Note)
def note(well: str):
    return _or_404(TOOLS.explain_well(well))
