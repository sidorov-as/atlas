"""The hand-written `request_attach` tool.

Atlas's `request_attach` operation returns a *relative* upload path: the Atlas
server has no public base-URL setting, and this process is the one that knows
`ATLAS_API_URL`. This wrapper calls the operation, then turns its result into
what an agent can act on: a complete URL, the expiry and size limit, and an
example `curl` command. The generated tool of the same name is excluded from
`FastMCP.from_openapi()` (`server.build_server`), so only this one is listed.
"""

import shlex
from typing import Any

import httpx2
from fastmcp.exceptions import ToolError

from .config import Config

ATTACH_PATH = "/api/plugins/atlas.mcp/uploads/"

_DESCRIPTION = """\
Get a one-time upload URL to send a large file straight into one field of an \
existing entity, without passing its text through this conversation. Use it \
when you can run shell commands and the content is large or already a file; \
for small content, or when you cannot run commands, pass it inline instead \
(`spec_content` on create_entity/update_entity for an API spec, \
set_resource_schema for a database schema).

`entity` is `kind:name` (create the entity first, without the spec). `field` \
is the field to fill: `spec` of an `api` (OpenAPI/AsyncAPI document), `schema` \
of a `resource` (SQL DDL; pass `params` {"dialect": "postgresql"|"mysql"|\
"mssql"}, default postgresql). Then upload the raw file with PUT to the \
returned `uploadUrl`, using `exampleCommand`.

The URL is a secret: valid for a few minutes, good for one successful upload, \
and not to be repeated to the user or written to files. The upload response \
is {"ok": true, "summary": ...} on success, where `ok` means the content was \
SAVED; for a schema, `summary.parse_status`/`parse_error` say separately \
whether it parsed. A rejected upload returns {"ok": false, "error": ...}: fix \
the file and PUT again to the same URL until it expires. If the URL's host \
is not reachable from your shell (for example host.docker.internal when the \
Atlas MCP server runs in a container), replace the host and keep the path. \
Needs the PAT scope that governs the target (`apis:write` for an API spec, \
`catalog:write` for a schema)."""


def _error_message(response: httpx2.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, list) and detail:
        return "; ".join(str(item.get("msg", item)) for item in detail)
    return str(detail or body)


def upload_url(config: Config, upload_path: str) -> str:
    return f"{config.api_url}{upload_path}"


def example_command(url: str) -> str:
    return f"curl --fail-with-body -T <file> {shlex.quote(url)}"


def make_request_attach(client: httpx2.AsyncClient, config: Config):
    async def request_attach(
        entity: str, field: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = await client.post(
            ATTACH_PATH,
            json={"entity": entity, "field": field, "params": params or {}},
        )
        if response.status_code != 200:
            raise ToolError(_error_message(response))
        issued = response.json()
        url = upload_url(config, issued["uploadPath"])
        return {
            "entity": issued["entity"],
            "field": issued["field"],
            "uploadUrl": url,
            "expiresAt": issued["expiresAt"],
            "maxBytes": issued["maxBytes"],
            "exampleCommand": example_command(url),
            "note": (
                "Replace <file> with the path of the file. Keep this URL "
                "secret. If its host is unreachable from your shell, "
                "substitute a reachable host and keep the path."
            ),
        }

    request_attach.__doc__ = _DESCRIPTION
    return request_attach
