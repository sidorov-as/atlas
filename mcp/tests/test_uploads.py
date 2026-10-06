"""The hand-written `request_attach` tool: URL composition, the result shape,
error mapping, and that it replaces (not duplicates) the generated tool."""

import asyncio
import json

import httpx2
import pytest
from atlas_mcp import server as server_module
from atlas_mcp.config import Config
from atlas_mcp.uploads import ATTACH_PATH, make_request_attach
from fastmcp import Client
from fastmcp.exceptions import ToolError

_ISSUED = {
    "entity": "api:booking",
    "field": "spec",
    "uploadPath": "/api/uploads/tok-123",
    "expiresAt": "2030-01-01T00:00:00Z",
    "maxBytes": 20971520,
}


@pytest.fixture
def config():
    return Config(api_url="https://atlas.example.com", pat="atlaspat_x")


def _client(handler):
    return httpx2.AsyncClient(
        base_url="https://atlas.example.com", transport=httpx2.MockTransport(handler)
    )


def test_result_has_a_full_url_expiry_limit_and_a_curl_command(config):
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["url"] = str(request.url)
        return httpx2.Response(200, json=_ISSUED)

    tool = make_request_attach(_client(handler), config)

    result = asyncio.run(tool("api:booking", "spec"))

    assert seen["url"] == f"https://atlas.example.com{ATTACH_PATH}"
    assert seen["body"] == {"entity": "api:booking", "field": "spec", "params": {}}
    assert result["uploadUrl"] == "https://atlas.example.com/api/uploads/tok-123"
    assert result["expiresAt"] == "2030-01-01T00:00:00Z"
    assert result["maxBytes"] == 20971520
    assert result["exampleCommand"] == (
        "curl --fail-with-body -T <file> https://atlas.example.com/api/uploads/tok-123"
    )
    assert "host" in result["note"]


def test_params_are_forwarded(config):
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json=_ISSUED)

    asyncio.run(
        make_request_attach(_client(handler), config)(
            "resource:db", "schema", {"dialect": "mysql"}
        )
    )

    assert seen["body"]["params"] == {"dialect": "mysql"}


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            httpx2.Response(403, json={"detail": [{"msg": "scope missing"}]}),
            "scope missing",
        ),
        (
            httpx2.Response(400, json={"detail": [{"msg": "no target 'x'"}]}),
            "no target",
        ),
        (httpx2.Response(502, text="bad gateway"), "bad gateway"),
    ],
)
def test_errors_become_tool_errors_with_the_reason(config, response, expected):
    tool = make_request_attach(_client(lambda request: response), config)

    with pytest.raises(ToolError, match=expected):
        asyncio.run(tool("api:booking", "spec"))


def _spec(*paths):
    operation = {
        "operationId": "request_attach",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"entity": {"type": "string"}},
                    }
                }
            }
        },
        "responses": {"200": {"description": "ok"}},
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            path: {"post": {**operation, "operationId": op_id}} for path, op_id in paths
        },
    }


def _tools(monkeypatch, config, spec):
    monkeypatch.setattr(
        server_module.httpx2,
        "get",
        lambda *a, **kw: type(
            "R", (), {"raise_for_status": lambda s: None, "json": lambda s: spec}
        )(),
    )
    server = server_module.build_server(config)

    async def listing():
        async with Client(server) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    return asyncio.run(listing())


def test_exactly_one_request_attach_tool_is_listed_when_the_target_exists(
    monkeypatch, config
):
    tools = _tools(
        monkeypatch,
        config,
        _spec(
            (ATTACH_PATH, "request_attach"),
            ("/api/plugins/atlas.mcp/catalog/", "create_entity"),
        ),
    )

    assert set(tools) == {"request_attach", "create_entity"}
    assert "one-time upload URL" in tools["request_attach"].description
    assert "SAVED" in tools["request_attach"].description


def test_no_request_attach_tool_without_the_operation(monkeypatch, config):
    tools = _tools(
        monkeypatch, config, _spec(("/api/plugins/atlas.mcp/catalog/", "create_entity"))
    )

    assert set(tools) == {"create_entity"}
