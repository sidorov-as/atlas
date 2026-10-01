"""`GET /api/plugins/atlas.mcp/openapi.json` (`atlas_plugin_mcp.api.
schema_views.openapi_schema_view`): the HTTP-servable form of this plugin's
own curated OpenAPI document, for the MCP transport process (task 6, no
Django import of its own) to fetch over `httpx` instead of calling
`build_openapi_schema()` in-process.

Gated by the same Atlas Personal Access Token requirement as every other
operation this plugin exposes (`mcp-plugin` spec's "Every MCP API request is
authenticated by an Atlas Personal Access Token") — asserted the same way
`test_catalog_controllers.py` asserts it for `search_catalog`.
"""

import pytest

from atlas_plugin_mcp.api.openapi import build_openapi_schema

pytestmark = pytest.mark.django_db


def test_openapi_schema_endpoint_rejects_a_request_with_no_bearer_token(dmr_client):
    response = dmr_client.get("/api/plugins/atlas.mcp/openapi.json")

    assert response.status_code in (401, 403)


def test_openapi_schema_endpoint_rejects_an_invalid_token(dmr_client):
    response = dmr_client.get(
        "/api/plugins/atlas.mcp/openapi.json",
        HTTP_AUTHORIZATION="Bearer atlaspat_not-a-real-token",
    )

    assert response.status_code in (401, 403)


def test_openapi_schema_endpoint_returns_the_curated_document_for_a_valid_token(
    dmr_client, pat_auth_header
):
    response = dmr_client.get("/api/plugins/atlas.mcp/openapi.json", **pat_auth_header)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    body = response.json()
    assert set(body["paths"]) == set(build_openapi_schema().paths)
    # The schema endpoint itself is not one of the operations it lists (kept
    # out via `external_path(..., openapi=None)` — it has no typed response
    # model of its own for `get_schema()` to describe).
    assert "/api/plugins/atlas.mcp/openapi.json" not in body["paths"]
