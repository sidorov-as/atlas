# Atlas MCP transport

A standalone [MCP](https://modelcontextprotocol.io) server that bridges an
MCP client (Claude Desktop, Codex, Qwen, etc.) to a running Atlas backend's
curated `atlas.mcp` API. It speaks the MCP protocol over **stdio** to the
client and calls Atlas's curated HTTP API over `httpx`, authenticated with
an [Atlas Personal Access Token](../docs-site/docs/features/mcp.md).

This directory is **not** an Atlas plugin and is **not**
composer/manifest-aware — it isn't installed by selecting anything in a
distribution's `manifest.yaml`, it has no Django import, and it is built,
run, and released independently of which Atlas distribution it points at.
Composing the `atlas.mcp` plugin into a distribution only makes the HTTP API
this process calls available; see [Features & Integrations →
MCP](../docs-site/docs/features/mcp.md) for that plugin's own tool set, PAT
issuance, and scopes.

## Requirements

- A running Atlas backend with the `atlas.mcp` plugin selected (the default
  distribution includes it).
- An Atlas Personal Access Token for the account you want MCP-triggered
  writes attributed to. Easiest: in the admin UI, open
  `/admin/catalog/personalaccesstoken/` and click **Add personal access
  token** (revoke it there later with the **Revoke selected tokens** action).
  Or from a shell:

  ```shell
  cd core/backend
  uv run python manage.py issue_pat <your-username> \
    --scope catalog:read --scope catalog:write \
    --scope flows:read --scope flows:write
  ```

  Save the printed plaintext — it is shown exactly once.

## Build

```shell
cd mcp
docker build -t atlas-mcp .
```

No image is published anywhere by this repository; running and distributing
a built image for your own deployment is up to you.

## Run without Docker

```shell
cd mcp
uv sync
ATLAS_API_URL=http://localhost:8000 ATLAS_PAT=<your-token> uv run atlas-mcp
```

This starts the stdio server directly — useful for local iteration, but an
MCP client normally launches it itself (see below), not the other way
around.

## Connect an MCP client

Add an entry under `mcpServers` naming a `command`, its `args`, and an `env`
block — the same shape
[`crystaldba/postgres-mcp`](https://github.com/crystaldba/postgres-mcp)
uses for its own Docker-based config. For Claude Desktop, this goes in
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atlas": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "ATLAS_API_URL",
        "-e", "ATLAS_PAT",
        "atlas-mcp"
      ],
      "env": {
        "ATLAS_API_URL": "http://host.docker.internal:8000",
        "ATLAS_PAT": "<your-token>"
      }
    }
  }
}
```

`ATLAS_API_URL` must be reachable from *inside* the container — against a
locally running `make dev-up` stack, `http://host.docker.internal:8000` is
usually correct on macOS/Windows; on Linux, use the host's own address or
run the container with `--network host`. Running without Docker (the `uv
run atlas-mcp` form above), point `command`/`args` at that instead:

```json
{
  "mcpServers": {
    "atlas": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/atlas/mcp", "atlas-mcp"],
      "env": {
        "ATLAS_API_URL": "http://localhost:8000",
        "ATLAS_PAT": "<your-token>"
      }
    }
  }
}
```

### Against a deployed Atlas

For an Atlas deployed at a public address (for example
`atlas.mycompany.com`), set `ATLAS_API_URL` to its base URL — scheme and
host only, no `/api` and no trailing slash. This process appends
`/api/plugins/atlas.mcp/openapi.json` and every other API path itself, and
no `host.docker.internal` is involved:

```json
{
  "mcpServers": {
    "atlas": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "ATLAS_API_URL",
        "-e", "ATLAS_PAT",
        "atlas-mcp"
      ],
      "env": {
        "ATLAS_API_URL": "https://atlas.mycompany.com",
        "ATLAS_PAT": "<your-token>"
      }
    }
  }
}
```

The deployment must route `/api/*` to the backend (the bundled Caddy does
this), select the `atlas.mcp` plugin, and the token must be issued on that
same instance. The `atlas.flows` plugin is needed for the Flow tools.

Restart the client after editing its config so it relaunches the server.

## Verify the connection

Once connected, ask the client something only Atlas's catalog can answer,
for example:

> Using the Atlas tools, search the catalog for a System named
> "user-management" and list its Components.

A working connection calls `search_catalog` (and `get_entity` for each
Component), returning real results from your Atlas instance. If the client
reports no tools available, or every call fails, see
[Troubleshooting](#troubleshooting) below.

## Troubleshooting

- **No tools appear / connection fails immediately**: the client couldn't
  reach `ATLAS_API_URL`, or the container/process exited before completing
  the startup handshake — check the client's own MCP server logs (Claude
  Desktop keeps one per server under its own log directory).
- **Every tool call is rejected with an authorization error**: `ATLAS_PAT`
  is missing, expired, revoked, or belongs to a deactivated account. Issue
  a fresh token (see [Requirements](#requirements)) and update `env`.
- **A write tool (`create_entity`, `update_flow`, etc.) is rejected but
  reads work**: the token's scopes don't cover that write — reissue it with
  the needed `catalog:write`/`flows:write` scope. A `403` distinct from an
  authentication failure means the token itself is valid but under-scoped,
  or the underlying user's own RBAC denies the operation.
- **`describe_kinds`, `list_relationships`, or `validate_flow` is rejected
  with a `403`**: these read tools need the `catalog:read` (first two) or
  `flows:read` scope, unlike `search_catalog`/`get_entity`.
- **A write is rejected with a `400` naming an unknown field**: `create_entity`
  and `update_entity` refuse `spec`/`metadata` keys the kind doesn't accept
  (and `spec.relationships`; use `create_relationship`). Call `describe_kinds`
  for the accepted fields. Add `dryRun` to any authoring write to preview it
  without saving.
- **Flow tools (`list_flows`, etc.) are missing**: the distribution
  `ATLAS_API_URL` points at doesn't have `atlas.flows` selected alongside
  `atlas.mcp` — this process only ever exposes what that distribution's own
  OpenAPI document lists.

## `search_flow_icons`

Unlike every other tool this process exposes, `search_flow_icons` is
answered entirely by this process itself, with no call to Atlas — a Flow
step's `icon` field accepts any `@gravity-ui/icons` component name, a fixed
set that ships with the frontend, not data any particular Atlas instance's
database holds. It's registered whenever Flow tools are (same
`atlas.flows`-installed condition as `list_flows`), backed by a small,
checked-in copy of `@gravity-ui/icons`' own icon list
(`atlas_mcp/_gravity_icons.py`) — the same generated copy
`atlas_plugin_flows` validates a submitted `icon` value against server-side
(`plugins/flows/backend/atlas_plugin_flows/_gravity_icons.py`). Regenerate
both after bumping `@gravity-ui/icons` in `plugins/flows/frontend`'s
`package.json`:

```shell
python scripts/sync_gravity_icons.py
```

## Skills

The [`skills/`](../skills/README.md) directory holds three assistant skills
(`atlas-scout`, `atlas-flow`, `atlas-curator`) that use these tools to fill the
catalog from a codebase and to build flows from a conversation. Install them
together; see [Catalog authoring skills](https://sidorov-as.github.io/atlas/features/mcp-skills/)
for installation, token scopes, and a worked example.

## Tests

```shell
cd mcp
uv sync
uv run pytest
```
