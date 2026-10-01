---
title: MCP
description: Expose a curated, tool-calling-shaped HTTP API for catalog entities and Flows, authenticated by Personal Access Tokens, for MCP clients such as Claude Desktop.
audience: [ operator, plugin-author ]
page-type: feature
plugin-id: atlas.mcp
---

# MCP

`atlas.mcp` lets AI assistants that speak MCP (Model Context Protocol), such
as Claude Desktop, read your Atlas catalog and, with a suitably scoped token,
change it. Ask "what does the booking service depend on?" or "who owns the
payments system?" and the assistant answers from Atlas's own data. It covers
catalog entities, plus Flows and API endpoints/operations when the matching
plugins are installed.

Access uses an Atlas Personal Access Token (PAT) instead of a browser
session. The plugin has no frontend.

Setup takes three steps:

1. [Issue a token](#issuing-a-token) for the account the assistant acts as.
2. Run the separate [MCP transport process](#mcp-transport-process) and give it
   that token.
3. Point your MCP client at it (see [`mcp/README.md`](https://github.com/sidorov-as/atlas/tree/main/mcp)
   for ready-to-paste client configuration).

## Enablement and configuration

Select `atlas.mcp` alongside `atlas.standard-catalog` and run normal
distribution composition; it is included in every first-party distribution
except the render single-container demo (kept out there for the same
free-tier footprint reason as `atlas.c4`'s remote renderer). There is no
plugin-specific configuration or secret.

Flow and API tools depend on other plugins, independently of each other:

- `atlas.flows` adds the Flow tools.
- `atlas.apis` adds the API endpoint/operation tools.

A distribution that omits either one still composes, and the matching tools
are not offered.

## Tool set

| Tool                          | What it does                                                                                        | Scope required  |
|-------------------------------|-----------------------------------------------------------------------------------------------------|-----------------|
| `search_catalog`              | Search entities by free text, kind, owner, tags, or status                                          | none            |
| `get_entity`                  | Read one entity's full detail                                                                       | none            |
| `create_entity`               | Create a System, Component, Resource, or API                                                        | `catalog:write` |
| `update_entity`               | Partially update an entity                                                                          | `catalog:write` |
| `remove_entity`               | Soft-remove an entity                                                                               | `catalog:write` |
| `purge_entity`                | Permanently delete a removed entity                                                                 | `catalog:write` |
| `list_flows`\*                | Search Flows across Systems                                                                         | none            |
| `get_flow`\*                  | Read one Flow's steps and documentation                                                             | none            |
| `create_flow`\*               | Create a Flow                                                                                       | `flows:write`   |
| `update_flow`\*               | Partially update a Flow                                                                             | `flows:write`   |
| `delete_flow`\*               | Delete a Flow                                                                                       | `flows:write`   |
| `search_api_endpoints`\*\*    | Search HTTP endpoints across all APIs, or within one                                                | none            |
| `get_api_endpoint`\*\*        | Read one endpoint: parameters, body, responses, security                                            | none            |
| `get_endpoint_consumers`\*\*  | List the Services linked to an endpoint as consumers                                                | none            |
| `search_api_operations`\*\*   | Search async (AsyncAPI) operations across all APIs, or within one                                   | none            |
| `get_api_operation`\*\*       | Read one operation: channel, direction, messages                                                    | none            |
| `get_operation_consumers`\*\* | List the Services publishing or subscribing on an operation's channel, with their role              | none            |

\* Present only when `atlas.flows` is also selected.

\*\* Present only when `atlas.apis` is also selected. The consumer tools return
only Services explicitly linked to that endpoint or operation, not Services
that consume the owning API as a whole.

Writes are limited to System, Component, Resource, and API. Group and Actor
are read-only through MCP, as they are in the REST API. Deleting takes two
steps, as in the web UI: `remove_entity`, then `purge_entity`. Writes are
audited like web UI changes, with the token's owner as the actor. A tool only
returns or changes what its token's owner could in the web UI.

## Authentication

Every request needs `Authorization: Bearer <token>`. A request with no token,
an unknown token, or a token that is expired, revoked, or belongs to a
deactivated account is rejected. A valid token acts as its owning user, so
Atlas's permissions and audit trail apply as usual.

### Issuing a token

In the admin UI, open **Personal access tokens** (`/admin/catalog/personalaccesstoken/`)
and click **Add personal access token**. Choose the owner, an optional name
(for example the client it is for), the scopes, and an optional expiry in days.
After you submit, the next page shows the token once. Copy it right away:
Atlas stores only a salted hash and a short lookup prefix, so it cannot show
the token again.

From a shell, the equivalent is:

```shell
uv run python manage.py issue_pat <username> \
  --scope catalog:read --scope catalog:write \
  --expires-in-days 90
```

See [Management commands](../reference/management-commands.md) for the full
option list. Accounts marked read-only cannot issue tokens in the admin UI.

### Managing and revoking tokens

The same admin list shows each token's owner, name, prefix, scopes, expiry,
last use, and whether it is revoked. To revoke tokens, select them and run
**Revoke selected tokens**; a revoked token stops working immediately, and the
row is kept for the record. Revoke a token as soon as it may have leaked, and
set an expiry on every token you issue.

### Scopes

A token's scopes can only narrow its owner's own permissions: an operation
is permitted only when both the token's scopes and the owner's permissions
allow it. The available scopes are:

| Scope           | Grants                                                                                         |
|-----------------|------------------------------------------------------------------------------------------------|
| `catalog:read`  | No effect today: every read tool is open to any valid token. Reserved for a future read gate. |
| `catalog:write` | `create_entity`, `update_entity`, `remove_entity`, `purge_entity`                              |
| `flows:read`    | No effect today, same as `catalog:read`                                                        |
| `flows:write`   | `create_flow`, `update_flow`, `delete_flow`                                                    |

A token with no scopes can read but not write, which makes it a safe default
for an assistant that only answers questions. A read-scoped token attempting
a write is rejected whatever its owner's permissions are.

## The MCP OpenAPI document

`atlas.mcp` generates its own OpenAPI document, separate from the SPA-facing
API's and titled "Atlas MCP API". It lists only this plugin's curated
operations, with no SPA-facing routes. It is served at a PAT-authenticated
endpoint:

```shell
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/plugins/atlas.mcp/openapi.json
```

The document reflects the running distribution: Flow paths appear only when
`atlas.flows` is installed, and API endpoint/operation paths only when
`atlas.apis` is. Plugin authors who need the document in-process (tests, or
another in-Django consumer) can call
`atlas_plugin_mcp.api.openapi.build_openapi_schema()` directly.

## MCP transport process

The process that speaks the MCP protocol to clients such as Claude Desktop is
not part of this plugin. It is a separate process that calls the plugin's
HTTP API with your token, and it is built and deployed independently of your
distribution. Composing `atlas.mcp` only makes the HTTP API available for it
to call. It reads the API's OpenAPI document at startup, so restart it after
enabling or disabling `atlas.flows` or `atlas.apis` to refresh its tool list.

Its code, `Dockerfile`, and connection instructions live in [`mcp/`](https://github.com/sidorov-as/atlas/tree/main/mcp)
at the repository root. Its README covers building, running, and connecting
an MCP client.

The process also has one tool of its own, `search_flow_icons`, alongside the
tools in the table above. It answers from a checked-in copy of
`@gravity-ui/icons` component names (the values a Flow step's `icon` field
accepts) without calling Atlas, and is present whenever the Flow tools are.
The transport's README explains how to regenerate that copy.

## Limits and troubleshooting

A write refused because of the owner's permissions, or because the token
lacks the scope, fails with the same kind of authorization error as the REST
API. If a client shows no Flow or API tools, check that `atlas.flows` or
`atlas.apis` is selected alongside `atlas.mcp`, then restart the transport
process. This API is not a replacement for the SPA-facing API: it exposes only
the curated operations above, a much smaller set than the full REST surface.

## Next steps

See [management commands](../reference/management-commands.md) for token
issuance, [permissions](../concepts/permissions.md), [distribution
operations](../operating-atlas/index.md), and the [Plugin API
reference](../plugin-development/reference.md).
