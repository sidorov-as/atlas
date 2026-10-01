"""The MCP API's own OpenAPI document — a separate `OpenAPIConfig`/`OpenAPI`
instance from the SPA-facing API's (`core/backend/server/settings/components/api.py`'s
`DMR_SETTINGS[Settings.openapi_config]`), never merged with it
(`mcp-plugin` spec: "under its own OpenAPI document, distinct from Atlas's
existing SPA-facing API ... SHALL NOT re-expose the SPA-facing API's
endpoints under this document").

This is what an MCP transport process (this change's own `mcp/` directory)
points `FastMCP.from_openapi()` at, matching Flagsmith's own
already-generated-document precedent (design.md Decision 2).

`build_openapi_schema()` calls `urls.build_router()` fresh each time, so the
returned document reflects whether `atlas.flows` is installed *right now* —
see that function's own docstring.
"""

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.openapi import OpenAPI

from .urls import build_router

MCP_OPENAPI_CONFIG = OpenAPIConfig(title="Atlas MCP API", version="0.1.0")


def build_openapi_schema() -> OpenAPI:
    return build_router().get_schema(OpenAPIContext(MCP_OPENAPI_CONFIG))
