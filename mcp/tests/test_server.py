"""`build_server` never talks to a real Atlas backend: `httpx2.get`
(the one-off schema fetch) and `FastMCP.from_openapi` (tool generation) are
both monkeypatched, so these tests assert only the two things this module
is actually responsible for getting right — which URL/header the schema
fetch uses, and what `FastMCP.from_openapi` is handed — not `fastmcp`'s or
`httpx2`'s own behavior.
"""

import httpx2
import pytest
from atlas_mcp import server as server_module
from atlas_mcp.config import Config
from atlas_mcp.icons import search_flow_icons


@pytest.fixture
def config():
    return Config(api_url="http://localhost:8000", pat="atlaspat_x")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeFastMCP:
    """Stands in for `FastMCP.from_openapi()`'s return value — real enough
    to record what `build_server` does with it afterwards (`.tool(...)`
    calls), without pulling in `fastmcp`'s own tool-registration machinery.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.registered_tools = []

    def tool(self, fn):
        self.registered_tools.append(fn)
        return fn


def _patch_schema_fetch(monkeypatch, spec):
    monkeypatch.setattr(
        server_module.httpx2, "get", lambda *a, **kw: _FakeResponse(spec)
    )


def _patch_from_openapi(monkeypatch):
    captured = {}

    def fake_from_openapi(cls, *, openapi_spec, client, name, instructions):
        captured["openapi_spec"] = openapi_spec
        captured["client"] = client
        captured["name"] = name
        captured["instructions"] = instructions
        captured["server"] = _FakeFastMCP(
            openapi_spec=openapi_spec, client=client, name=name
        )
        return captured["server"]

    monkeypatch.setattr(
        server_module.FastMCP, "from_openapi", classmethod(fake_from_openapi)
    )
    return captured


def test_build_server_fetches_the_mcp_plugins_own_schema_endpoint_with_bearer_auth(
    monkeypatch, config
):
    captured = {}

    def fake_get(url, *, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return _FakeResponse({"paths": {}})

    monkeypatch.setattr(server_module.httpx2, "get", fake_get)
    monkeypatch.setattr(
        server_module.FastMCP, "from_openapi", classmethod(lambda cls, **kw: object())
    )

    server_module.build_server(config)

    assert captured["url"] == "http://localhost:8000/api/plugins/atlas.mcp/openapi.json"
    assert captured["headers"] == {"Authorization": "Bearer atlaspat_x"}


def test_build_server_passes_the_fetched_spec_and_an_authenticated_client(
    monkeypatch, config
):
    spec = {"paths": {"/api/plugins/atlas.mcp/catalog/search/": {}}}
    _patch_schema_fetch(monkeypatch, spec)
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert captured["openapi_spec"] == spec
    assert captured["name"] == "Atlas"
    client = captured["client"]
    assert isinstance(client, httpx2.AsyncClient)
    assert str(client.base_url) == "http://localhost:8000"
    assert client.headers["authorization"] == "Bearer atlaspat_x"


def test_build_server_passes_instructions_mentioning_atlas(monkeypatch, config):
    _patch_schema_fetch(monkeypatch, {"paths": {}})
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert "Atlas" in captured["instructions"]
    assert "search_catalog" in captured["instructions"]


def test_build_server_instructions_describe_the_authoring_workflow(monkeypatch, config):
    _patch_schema_fetch(monkeypatch, {"paths": {}})
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    for expected in ("describe_kinds", "create_relationship", "dryRun"):
        assert expected in captured["instructions"]


def test_build_server_instructions_mention_validate_flow_only_with_flows(
    monkeypatch, config
):
    _patch_schema_fetch(monkeypatch, {"paths": {"/api/plugins/atlas.mcp/flows/": {}}})
    with_flows = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    _patch_schema_fetch(monkeypatch, {"paths": {}})
    without_flows = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    assert "validate_flow" in with_flows["instructions"]
    assert "validate_flow" not in without_flows["instructions"]


def test_build_server_instructions_mention_flow_tools_only_when_flows_are_present(
    monkeypatch, config
):
    _patch_schema_fetch(monkeypatch, {"paths": {"/api/plugins/atlas.mcp/flows/": {}}})
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert "search_flow_icons" in captured["instructions"]


def test_build_server_instructions_omit_flow_tools_when_flows_are_absent(
    monkeypatch, config
):
    _patch_schema_fetch(
        monkeypatch, {"paths": {"/api/plugins/atlas.mcp/catalog/search/": {}}}
    )
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert "search_flow_icons" not in captured["instructions"]


def test_build_server_instructions_mention_api_tools_only_when_apis_are_present(
    monkeypatch, config
):
    _patch_schema_fetch(
        monkeypatch,
        {"paths": {"/api/plugins/atlas.mcp/endpoints/{id}/consumers/": {}}},
    )
    with_apis = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    _patch_schema_fetch(
        monkeypatch, {"paths": {"/api/plugins/atlas.mcp/catalog/search/": {}}}
    )
    without_apis = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    assert "get_endpoint_consumers" in with_apis["instructions"]
    assert "get_operation_consumers" in with_apis["instructions"]
    assert "get_endpoint_consumers" not in without_apis["instructions"]


def test_build_server_instructions_mention_usage_tools_only_when_present(
    monkeypatch, config
):
    _patch_schema_fetch(
        monkeypatch,
        {
            "paths": {
                "/api/plugins/atlas.mcp/endpoints/{id}/consumers/": {},
                "/api/plugins/atlas.mcp/endpoints/consumers/link/": {},
            }
        },
    )
    with_usage = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    _patch_schema_fetch(
        monkeypatch,
        {"paths": {"/api/plugins/atlas.mcp/endpoints/{id}/consumers/": {}}},
    )
    read_only = _patch_from_openapi(monkeypatch)
    server_module.build_server(config)

    for expected in ("link_endpoint_consumers", "apis:write", "dryRun", "200"):
        assert expected in with_usage["instructions"]
    assert "link_endpoint_consumers" not in read_only["instructions"]
    assert "get_endpoint_consumers" in read_only["instructions"]


def test_build_server_registers_search_flow_icons_only_when_flows_are_present(
    monkeypatch, config
):
    _patch_schema_fetch(monkeypatch, {"paths": {"/api/plugins/atlas.mcp/flows/": {}}})
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert captured["server"].registered_tools == [search_flow_icons]


def test_build_server_does_not_register_search_flow_icons_without_flows(
    monkeypatch, config
):
    _patch_schema_fetch(
        monkeypatch, {"paths": {"/api/plugins/atlas.mcp/catalog/search/": {}}}
    )
    captured = _patch_from_openapi(monkeypatch)

    server_module.build_server(config)

    assert captured["server"].registered_tools == []
