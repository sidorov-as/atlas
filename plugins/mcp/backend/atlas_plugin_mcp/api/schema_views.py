"""The `openapi_schema` endpoint: serves this plugin's own curated OpenAPI
document (`atlas_plugin_mcp.api.openapi.build_openapi_schema`) as JSON.

The MCP transport process (this change's own `mcp/` directory, task 6) holds
no Django import at all (design.md Decision 1: "the MCP transport process
holds no Django import ... calls a new, curated Atlas HTTP API over
`httpx`") — it can't call `build_openapi_schema()` in-process, so this
document needs an HTTP-servable route of its own, the same way `mcp-plugin`
spec's curated operations do. `dmr.openapi.views.json.OpenAPIJsonView` is
this framework's own ready-made renderer for an already-built `OpenAPI`
instance; nothing in this codebase had wired it to a URL before this
endpoint (the existing SPA-facing API's `OpenAPIConfig` has no HTTP-served
document either — see this plugin's docs page for that distinction).

Requires a valid Atlas Personal Access Token, like every other operation
this plugin exposes (`mcp-plugin` spec's "Every MCP API request is
authenticated by an Atlas Personal Access Token") — no particular scope:
reading this plugin's own schema is metadata about the API, not a catalog or
Flow read/write for `require_scope` to gate.

A plain function-based view rather than an `AtlasController`: the payload is
an already-serialized `OpenAPI` object with its own `.convert()`/JSON
encoding (`dmr.openapi.dump.json_dump`), not a typed response model this
plugin's other controllers declare for `PydanticSerializer` to build a
schema entry from — routing it through `AtlasController` would just
re-encode what `OpenAPIJsonView` already renders. It is still reached only
via `PATBearerAuth`, applied here directly rather than through a
`Controller`'s `auth` tuple (which only `dmr.controller.Controller`
subclasses invoke).
"""

from http import HTTPStatus

from atlas_plugin_api.pat import get_pat_validator
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from dmr.errors import ErrorType, format_error
from dmr.openapi.views.json import OpenAPIJsonView

_BEARER_PREFIX = "Bearer "


def _unauthorized() -> HttpResponse:
    return JsonResponse(
        format_error(
            "This endpoint requires a Personal Access Token",
            error_type=ErrorType.security,
        ),
        status=HTTPStatus.UNAUTHORIZED,
    )


def openapi_schema_view(request: HttpRequest) -> HttpResponseBase:
    """`GET /api/plugins/atlas.mcp/openapi.json` — the MCP transport's own
    entry point for discovering this plugin's curated tool surface.
    """
    header = request.headers.get("Authorization", "")
    raw_token = (
        header.removeprefix(_BEARER_PREFIX).strip()
        if header.startswith(_BEARER_PREFIX)
        else ""
    )
    if not raw_token or get_pat_validator()(raw_token) is None:
        return _unauthorized()

    # Local import: `.openapi` imports `build_router` from `.urls`, and
    # `.urls` imports this module to register the route below — importing
    # `.openapi` at this module's top level would be circular.
    from .openapi import build_openapi_schema

    return OpenAPIJsonView.as_view(schema=build_openapi_schema())(request)
