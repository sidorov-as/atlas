## Why

Atlas can already record which Services consume an API Endpoint and which Services publish or subscribe on an API Operation, but only through the REST API with a browser session. MCP clients and the catalog skills can read these links (`get_endpoint_consumers`, `get_operation_consumers`) and cannot write them. A team that has already mapped its code (API client calls, message publish and subscribe sites) onto endpoints and operations has no way to load that graph into the catalog, and `atlas-curator` and `atlas-scout` cannot record a call site they find.

## What Changes

- Add four MCP write tools for Service-to-Endpoint and Service-to-Operation links: link and unlink for endpoints, link and unlink for operations. Each takes a batch of items, so loading a large graph is not one call per link.
- An item names its endpoint or operation either by id or by natural key (`api` + `method` + `path` for an endpoint, `api` + `channel_address` + `direction` for an operation). Exactly one of the two forms per item.
- A batch succeeds partially. Each item gets its own status (`created`, `unchanged`, `not_found`, `ambiguous`, `conflict`, and the unlink equivalents), so a rerun is idempotent and one stale item does not fail the rest.
- Support `dryRun` on every write tool, as the existing authoring tools do.
- Linking an endpoint reports whether Atlas also added the API to the Service's `consumesAPI` (existing behavior of the REST link). Operation links have no such side effect.
- Add a new PAT scope `apis:write`, required by the four tools, declared next to the existing scopes.
- Record an `origin` (`manual` or `yaml`) and a `source` (`ui` or `mcp`) on every Service-Endpoint and Service-Operation link. `origin` defaults to `manual`; `yaml` is reserved for a future manifest declaration, and a `yaml` link cannot be unlinked through MCP or REST. `source` is set by the server from the channel of the call. Both are visible in Django admin only, not in the web UI. Existing links migrate to `origin=manual`, `source=ui`.
- `atlas-curator` gains a reference for these links: check existing links first, preview with `dryRun`, create them after the API and the Services exist, confirm before unlinking. `atlas-scout` plans them as `(service -> endpoint/operation, role)` rows, with the code location kept as text for the reviewer only.
- Update the MCP documentation, the PAT scope table, and the skill tool and scope references.

Out of scope: declaring these links in `catalog-info.yaml` (only the `yaml` origin is reserved), showing `origin` or `source` in the web UI, storing evidence or a client label with a link, and a new scope for reading endpoints and operations (reads stay scope-free).

## Capabilities

### New Capabilities
- `mcp-api-usage-tools`: the four batch link and unlink tools for Service-Endpoint and Service-Operation links, their addressing forms, per-item statuses, `dryRun`, the `consumesAPI` report, and the `apis:write` requirement.

### Modified Capabilities
- `mcp-plugin`: the API tool set gains the usage write tools, present only when `atlas.apis` is installed, and they call the apis plugin only through its published extension points.
- `endpoint-service-dependencies`: a link carries `origin` and `source`; a `yaml` link cannot be removed.
- `operation-service-dependencies`: a link carries `origin` and `source`; a `yaml` link cannot be removed.
- `personal-access-tokens`: `apis:write` is an issuable scope.
- `atlas-curator-skill`: the curator authors Endpoint and Operation links through the new tools.
- `atlas-scout-skill`: the scout includes endpoint and operation links in the plan it hands to the curator.

## Impact

- `plugins/apis/backend/atlas_plugin_apis`: link and unlink logic moves out of the REST views into the plugin's extension points, shared by REST and MCP; both link models get `origin` and `source` and a migration; the admin shows them.
- `plugins/mcp/backend/atlas_plugin_mcp`: new controllers and schemas for the four tools, registered only when `atlas.apis` is installed; the OpenAPI document served to the MCP server grows by four operations.
- `core/backend/server/apps/catalog/models/personal_access_token.py` and the places that list scope choices (admin, `issue_pat`): the `apis:write` scope.
- `mcp/`: the MCP server registers the new operations when present.
- `skills/atlas-curator`, `skills/atlas-scout`, `skills/atlas-flow/references/tools-and-scopes.md`, and `docs-site/docs/features/mcp.md`.
- Existing REST responses for these links are unchanged.
