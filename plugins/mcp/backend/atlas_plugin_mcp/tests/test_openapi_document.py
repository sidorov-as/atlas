"""`mcp-plugin` spec: "Flow tools are present only when atlas.flows is
installed" — asserted directly against the MCP API's own OpenAPI document
(tasks.md 3.5).

`atlas_plugin_mcp.api.urls.build_router()`/`api.openapi.build_openapi_schema()`
both check `django.apps.apps.is_installed("atlas_plugin_flows")` at call
time (module docstring), so flipping that answer with a monkeypatch — not a
module reload — is enough to observe both distribution shapes in one test
module, same as `atlas_plugin_flows.tests.test_flow_query_event_steps`'s own
`django_apps.is_installed` patches for its optional link to `atlas.apis`.
"""

from atlas_plugin_mcp.api.openapi import build_openapi_schema


def _paths(schema):
    return set(schema.paths or {})


def test_mcp_openapi_document_includes_flow_paths_when_flows_is_installed():
    """This test suite's own environment has `atlas_plugin_flows` installed
    (`pytest.ini`'s `testpaths` runs the whole workspace together), so no
    patch is needed for the "present" half of the scenario."""
    paths = _paths(build_openapi_schema())

    assert any("/flows/" in path for path in paths)
    assert any(path.rstrip("/").endswith("flows/{id}".rstrip("/")) for path in paths)


def test_mcp_openapi_document_only_lists_curated_catalog_and_flow_operations():
    """`mcp-plugin` spec: "SHALL NOT re-expose the SPA-facing API's
    endpoints under this document" — every path this document lists lives
    under this plugin's own `/api/plugins/atlas.mcp/` prefix."""
    paths = _paths(build_openapi_schema())

    assert paths
    assert all(path.startswith("/api/plugins/atlas.mcp/") for path in paths)


def test_mcp_openapi_document_omits_flow_paths_when_flows_is_not_installed(
    monkeypatch,
):
    monkeypatch.setattr(
        "atlas_plugin_mcp.api.urls.django_apps.is_installed", lambda _name: False
    )

    paths = _paths(build_openapi_schema())

    assert paths
    assert not any("flow" in path.lower() for path in paths)
    # The catalog tools stay present regardless — only Flow support is
    # conditional on `atlas.flows`.
    assert any("/catalog/" in path for path in paths)


def test_mcp_openapi_document_uses_short_explicit_operation_ids():
    """Every operation names an explicit, tool-shaped `operationId` (e.g.
    `list_flows`) instead of `dmr`'s auto-generated fallback — method plus
    controller class name plus the full URL path, e.g.
    `getFlowlistcontrollerApiPluginsAtlasMcpFlows` — which is what
    `FastMCP.from_openapi()` (`mcp/atlas_mcp/server.py`) would otherwise turn
    into the tool name a client sees.
    """
    schema = build_openapi_schema()

    expected = {
        ("/api/plugins/atlas.mcp/catalog/search/", "get"): "search_catalog",
        ("/api/plugins/atlas.mcp/catalog/", "post"): "create_entity",
        ("/api/plugins/atlas.mcp/catalog/{id}/", "get"): "get_entity",
        ("/api/plugins/atlas.mcp/catalog/{id}/", "patch"): "update_entity",
        ("/api/plugins/atlas.mcp/catalog/{id}/remove/", "post"): "remove_entity",
        ("/api/plugins/atlas.mcp/catalog/{id}/purge/", "post"): "purge_entity",
        ("/api/plugins/atlas.mcp/flows/", "get"): "list_flows",
        ("/api/plugins/atlas.mcp/flows/", "post"): "create_flow",
        ("/api/plugins/atlas.mcp/flows/{id}/", "get"): "get_flow",
        ("/api/plugins/atlas.mcp/flows/{id}/", "patch"): "update_flow",
        ("/api/plugins/atlas.mcp/flows/{id}/", "delete"): "delete_flow",
        ("/api/plugins/atlas.mcp/endpoints/search/", "get"): "search_api_endpoints",
        ("/api/plugins/atlas.mcp/endpoints/{id}/", "get"): "get_api_endpoint",
        ("/api/plugins/atlas.mcp/endpoints/{id}/consumers/", "get"): (
            "get_endpoint_consumers"
        ),
        ("/api/plugins/atlas.mcp/operations/search/", "get"): "search_api_operations",
        ("/api/plugins/atlas.mcp/operations/{id}/", "get"): "get_api_operation",
        ("/api/plugins/atlas.mcp/operations/{id}/consumers/", "get"): (
            "get_operation_consumers"
        ),
    }

    actual = {}
    for path, item in (schema.paths or {}).items():
        for method in ("get", "post", "patch", "delete"):
            operation = getattr(item, method, None)
            if operation is not None:
                actual[(path, method)] = operation.operation_id

    assert actual == expected


_API_OPERATION_IDS = {
    "search_api_endpoints",
    "get_api_endpoint",
    "get_endpoint_consumers",
    "search_api_operations",
    "get_api_operation",
    "get_operation_consumers",
}


def _operation_ids(schema):
    return {
        operation.operation_id
        for item in (schema.paths or {}).values()
        for method in ("get", "post", "patch", "delete")
        if (operation := getattr(item, method, None)) is not None
    }


def _only_installed(monkeypatch, *installed):
    monkeypatch.setattr(
        "atlas_plugin_mcp.api.urls.django_apps.is_installed",
        lambda name: name in installed,
    )


def test_mcp_openapi_document_includes_all_api_tools_when_apis_is_installed():
    assert _API_OPERATION_IDS <= _operation_ids(build_openapi_schema())


def test_mcp_openapi_document_omits_every_api_tool_when_apis_is_not_installed(
    monkeypatch,
):
    _only_installed(monkeypatch, "atlas_plugin_flows")

    ids = _operation_ids(build_openapi_schema())

    assert not ids & _API_OPERATION_IDS
    assert not any(
        "endpoint" in path or "operations" in path
        for path in _paths(build_openapi_schema())
    )


def test_apis_and_flows_dependencies_are_independent(monkeypatch):
    _only_installed(monkeypatch, "atlas_plugin_apis")
    ids = _operation_ids(build_openapi_schema())
    assert _API_OPERATION_IDS <= ids
    assert not {"list_flows", "get_flow"} & ids

    _only_installed(monkeypatch, "atlas_plugin_flows")
    ids = _operation_ids(build_openapi_schema())
    assert {"list_flows", "get_flow"} <= ids
    assert not ids & _API_OPERATION_IDS
