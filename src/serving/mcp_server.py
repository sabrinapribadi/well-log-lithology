"""MCP server exposing the lithology tools to AI assistants (ADR-007). Same registry as the REST API.

    python -m src.serving.mcp_server          # stdio transport
"""

from __future__ import annotations

import inspect

from mcp.server.mcpserver import MCPServer

from src.serving.tools import REGISTRY, Tools

INSTRUCTIONS = ("Tools for well-log lithology: the predicted rock column of a FORCE 2020 North Sea test well from a blind-tested "
                "model, the log quality of a Kansas well from the Kansas Geological Survey archive, the result of the Kansas "
                "transfer test for a named unit, and a grounded note on one well. Kansas lithology is not validated: the transfer "
                "test failed, so never present a Kansas rock prediction as reliable.")


def build_server(tools: Tools | None = None) -> MCPServer:
    t = tools or Tools()
    srv = MCPServer(name="well-log-lithology", instructions=INSTRUCTIONS, version="1")
    for name in REGISTRY:
        fn = getattr(t, name)

        def make(f):
            def call(**kw):
                return f(**kw).model_dump()
            call.__name__, call.__doc__, call.__signature__ = f.__name__, inspect.getdoc(f), inspect.signature(f)
            return call
        srv.tool(name=name, description=inspect.getdoc(fn))(make(fn))
    return srv


if __name__ == "__main__":
    build_server().run("stdio")
