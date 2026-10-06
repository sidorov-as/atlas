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

| Tool                                | What it does                                                                           | Scope required  |
|-------------------------------------|----------------------------------------------------------------------------------------|-----------------|
| `search_catalog`                    | Search entities by free text, kind, owner, tags, or status                             | none            |
| `get_entity`                        | Read one entity's full detail                                                          | none            |
| `describe_kinds`                    | Show the `spec` fields, enum values, and required fields of each writable kind         | `catalog:read`  |
| `create_entity`                     | Create a System, Component, Resource, or API                                           | `catalog:write` |
| `update_entity`                     | Partially update an entity                                                             | `catalog:write` |
| `remove_entity`                     | Soft-remove an entity                                                                  | `catalog:write` |
| `purge_entity`                      | Permanently delete a removed entity                                                    | `catalog:write` |
| `list_relationships`                | List the Architecture Relationships an entity is the source or target of, with origin  | `catalog:read`  |
| `create_relationship`               | Create a manual Architecture Relationship                                              | `catalog:write` |
| `update_relationship`               | Partially update a manual Architecture Relationship                                    | `catalog:write` |
| `delete_relationship`               | Delete a manual Architecture Relationship                                              | `catalog:write` |
| `list_flows`\*                      | Search Flows across Systems                                                            | none            |
| `get_flow`\*                        | Read one Flow's steps and documentation                                                | none            |
| `create_flow`\*                     | Create a Flow                                                                          | `flows:write`   |
| `update_flow`\*                     | Partially update a Flow                                                                | `flows:write`   |
| `delete_flow`\*                     | Delete a Flow                                                                          | `flows:write`   |
| `validate_flow`\*                   | Check a Flow body against every save rule and list all violations, without saving      | `flows:read`    |
| `search_api_endpoints`\*\*          | Search HTTP endpoints across all APIs, or within one                                   | none            |
| `get_api_endpoint`\*\*              | Read one endpoint: parameters, body, responses, security                               | none            |
| `get_endpoint_consumers`\*\*        | List the Services linked to an endpoint as consumers                                   | none            |
| `search_api_operations`\*\*         | Search async (AsyncAPI) operations across all APIs, or within one                      | none            |
| `get_api_operation`\*\*             | Read one operation: channel, direction, messages                                       | none            |
| `get_operation_consumers`\*\*       | List the Services publishing or subscribing on an operation's channel, with their role | none            |
| `link_endpoint_consumers`\*\*       | Link a Service to the endpoints it consumes, in a batch                                | `apis:write`    |
| `unlink_endpoint_consumers`\*\*     | Remove a Service's links to endpoints, in a batch                                      | `apis:write`    |
| `link_operation_participants`\*\*   | Link a Service to operations it publishes or subscribes on, in a batch                 | `apis:write`    |
| `unlink_operation_participants`\*\* | Remove a Service's publisher or subscriber role on operations, in a batch              | `apis:write`    |
| `request_attach`\*\*\*              | Get a one-time upload URL for an API spec or a Resource's database schema               | `apis:write` for a spec, `catalog:write` for a schema |
| `set_resource_schema`\*\*\*\*       | Save a Resource's database schema from SQL text; reports whether it parsed             | `catalog:write` |

\* Present only when `atlas.flows` is also selected.

\*\* Present only when `atlas.apis` is also selected. The consumer tools return
only Services explicitly linked to that endpoint or operation, not Services
that consume the owning API as a whole.

\*\*\* Present only when a plugin registers an upload target (`atlas.apis` for
an API `spec`, `atlas.database-schema` for a Resource `schema`).

\*\*\*\* Present only when `atlas.database-schema` is also selected.

Writes are limited to System, Component, Resource, and API. Group and Actor
are read-only through MCP, as they are in the REST API. Deleting takes two
steps, as in the web UI: `remove_entity`, then `purge_entity`. Writes are
audited like web UI changes, with the token's owner as the actor. A tool only
returns or changes what its token's owner could in the web UI.

### Linking Services to endpoints and operations

The four `apis:write` tools create and remove the same Service links the web
UI shows in the **Linked Services** tabs of an endpoint or operation. Each call
takes one Service (a Component) and up to 200 items, so a whole repository's
call sites go in one call per Service.

An item names its target in one of two ways, never both:

- by id: `endpointId`, or `operationId` with a `role` (`publisher` or
  `subscriber`);
- by natural key: `api` (an API ref), `method`, and `path` for an endpoint, or
  `api`, `channelAddress`, and `direction` plus `role` for an operation.

A call succeeds item by item. The response lists a `status` per item in
request order, with a count per status: `created` or `removed`, `unchanged`
(the link already existed, or was already absent), `not_found`, `ambiguous`
(an operation key matching several operations; the candidate ids are
returned), `conflict`, and `invalid`. A bad item does not stop the others, and
repeating a call is safe. A removed endpoint cannot be linked (`conflict`),
but a link to it can still be removed. Linking an operation to the Service
that owns its API document is also a `conflict`.

`dryRun` previews the statuses and counts without saving anything.

Linking an endpoint also adds its API to the Service's `consumesAPI`, reported
per item as `apiRelationCreated`. Unlinking never removes `consumesAPI`, and
operation links do not touch the Service's relations.

Links created through MCP have origin `manual` and source `mcp`; links made in
the web UI have source `ui`. Both fields are visible in Django admin only, not
in the web UI or the REST API. A link with origin `yaml` is managed by
ingestion and the unlink tools refuse to remove it.

### Uploading large files with `request_attach`

An API spec can run to megabytes, and passing it as `spec_content` sends every
byte through the model's context. When the agent can run shell commands, it
calls `request_attach` instead and gets a one-time URL; it then sends the raw
file with `curl -T file <url>`. The file goes straight to Atlas, and the agent
never holds the token.

The entity must exist first (an API without a spec is valid). The call takes
`entity` as `kind:name`, a `field`, and any `params`:

| Target                | `field`  | `params`                                     | Limit                              |
|-----------------------|----------|----------------------------------------------|------------------------------------|
| `api`                 | `spec`   | none                                         | 20 MiB                             |
| `resource`            | `schema` | `dialect`: `postgresql` (default), `mysql`, `mssql` | `ATLAS_DATABASE_SCHEMA_UPLOAD_MAX_BYTES` (5 MiB by default) |

The upload reply is `{"ok": true, "summary": {...}}`. `ok` means the content
was saved. For an API, `summary` has the spec kind and the number of endpoints
or operations; a document that does not parse, exceeds the parse limits, or
is the wrong kind for the API's type is rejected and the stored spec stays as
it was. For a schema, a body that cannot be parsed is still saved, and
`summary.parse_status` and `parse_error` say so. A rejected upload returns
`{"ok": false, "error": "..."}` and the same URL accepts a corrected file
until it expires.

Small content, or an agent without a shell, uses the inline paths:
`spec_content` on `create_entity`/`update_entity`, and `set_resource_schema`
(`resource`, `dialect`, `sourceSql`, with `dryRun` like other writes).

**Security properties of an upload link:**

- The URL is the only credential. The `PUT` has no `Authorization` header and
  is not an MCP tool.
- The token in the URL has 256 bits of randomness; Atlas stores only its hash
  and returns it once. It is kept out of Atlas's logs.
- A link covers one field of one entity, expires after
  `ATLAS_UPLOAD_TICKET_TTL_SECONDS`, and is consumed only by an upload that is
  accepted. A failed upload leaves it usable until expiry.
- Issuing needs the same rights as a normal write: the token's scope, the
  owner's edit permission, and an entity not managed by `catalog-info.yaml`.
  The permission is checked again at upload time and the write is made as the
  token's owner.
- If the token that issued a link is revoked or expires, or its owner is
  deactivated, the link stops working.
- An unknown, expired, used, or revoked link all answer with the same `404`.
- The body size is capped while it is read, so a missing or false
  `Content-Length` does not bypass the limit.
- The URL starts with the transport's `ATLAS_API_URL`. Run in Docker with a
  container-only host such as `host.docker.internal`, it may not resolve from
  the agent's shell; the agent is told to substitute a reachable host.

### Strict validation

`create_entity` and `update_entity` reject any key in `spec` or `metadata`
that the kind does not accept, with an error naming the key and, when one is
close, the field it probably meant (for example `dependOn` instead of
`dependsOn`). Nothing is created or changed when a request is rejected. Use
`describe_kinds` to read the accepted fields. `relationships` is not a `spec`
field for MCP writes: manage Architecture Relationships with the
relationship tools. Relationships declared in an ingested `catalog-info.yaml`
keep the origin `yaml`; they are managed by ingestion and the relationship
tools refuse to change or delete them.

### Previewing a write with `dryRun`

`create_entity`, `update_entity`, `create_flow`, `update_flow`,
`create_relationship`, `update_relationship`, and `delete_relationship`
accept a `dryRun` flag. (The usage link tools take it too, with the
per-item response described above.) With `dryRun` true the write runs through the real
validation, permission, and reference checks, then is rolled back: nothing is
saved and no audit record is written. The response has `dryRun: true`, the
resulting `result` (with `id` null for a create), a `changes` list of fields
with their current and proposed values, and `warnings`. A dry-run is rejected
with the same error a real write would give, and still needs the write scope.
When an API's `specSource` is `url`, a dry-run does not fetch the URL and
warns that a real write would.

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
  --scope catalog:read --scope catalog:write --scope apis:write \
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

| Scope           | Grants                                                                                                                 |
|-----------------|------------------------------------------------------------------------------------------------------------------------|
| `catalog:read`  | `describe_kinds`, `list_relationships`. Other read tools are open to any valid token.                                  |
| `catalog:write` | `create_entity`, `update_entity`, `remove_entity`, `purge_entity`, the relationship writes, `set_resource_schema`, and `request_attach` for a schema                        |
| `flows:read`    | `validate_flow`. Other read tools are open to any valid token.                                                         |
| `flows:write`   | `create_flow`, `update_flow`, `delete_flow`                                                                            |
| `apis:write`    | `link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, `unlink_operation_participants`, and `request_attach` for an API spec |

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
