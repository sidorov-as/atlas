## Why

`atlas.mcp`'s curated tool surface covers catalog entities and Flows, but an
API entity's individual Endpoints and Operations — and, critically, which
Services are explicitly linked as their consumers (`ServiceEndpointUsage`/
`ServiceOperationUsage`) — are invisible to it. `get_entity` on an `api`
returns only its metadata and spec-source info, never its endpoint/operation
list. This was discovered when an MCP client, asked which services consume
a specific endpoint, had no tool to answer precisely: it had to guess from
the coarser Component-level `consumesApi` relation and then told the user
Atlas doesn't track usage at that granularity at all — which is false. The
data already exists, fully modeled and already served by the existing
SPA-facing API (`atlas_plugin_apis`'s per-API and cross-API endpoint/
operation listing, detail, and linked-services/consumers routes); it's
simply never been wired into the MCP surface.

## What Changes

- Add six new read-only MCP tools, present only when `atlas.apis` is
  installed alongside `atlas.mcp` (a new optional, code-level dependency,
  mirroring the existing `atlas.flows` one):
  - `search_api_endpoints` — cross-API, optionally API-scoped, paginated
    Endpoint search.
  - `get_api_endpoint` — one Endpoint's full detail (method, path, request/
    response shapes, security, deprecation, status).
  - `get_endpoint_consumers` — the Services explicitly linked to one
    Endpoint via `ServiceEndpointUsage`.
  - `search_api_operations` / `get_api_operation` / `get_operation_consumers`
    — the same three, for AsyncAPI Operations and `ServiceOperationUsage`.
- No write tools for these links in this change (linking/unlinking a Service
  stays a web UI action); this closes the *read* gap the incident above
  surfaced.
- Add a small, read-only data-access surface to `atlas_plugin_apis.
  extension_points` (search + consumers lookups) for the new MCP
  controllers to call, rather than importing `atlas_plugin_apis`'s models
  directly — the same plugin-boundary discipline `resolve_endpoint()`/
  `resolve_operation()` already establish in that module for Flow's own
  cross-plugin reads.

## Capabilities

### New Capabilities

(none — this extends the tool surface `add-mcp-server` establishes, see
below)

### Modified Capabilities

- `mcp-plugin`: gains a second optional plugin dependency (`atlas.apis`,
  alongside the existing `atlas.flows` one) and six new curated read
  operations, following the exact same "present only when the owning
  plugin is installed" rule the existing Flow-tools requirement already
  states. No existing requirement's behavior changes — see `design.md` for
  why this lands as new, additive requirements rather than an edit to the
  existing tool-surface enumeration.

## Impact

- **Sequencing**: this change extends the `mcp-plugin` capability that
  `add-mcp-server` introduces. It assumes that change has already landed
  (its `atlas_plugin_mcp` plugin, PAT auth, and curated-OpenAPI-document
  machinery all exist) — apply/archive it after `add-mcp-server`.
- **Backend**: new controllers in `plugins/mcp/backend/atlas_plugin_mcp/
  api/` (new `endpoint_views.py`/schemas, wired into `urls.py`'s
  `build_router()` the same conditional way `_flow_urls()` already is,
  keyed on `atlas.apis` instead of `atlas.flows`), and new read-only
  functions in `plugins/apis/backend/atlas_plugin_apis/extension_points.py`.
- **MCP transport**: none — `mcp/atlas_mcp/server.py` already generates
  every tool from the curated OpenAPI document; no code there changes, the
  new tools simply appear once the backend exposes them, the same way Flow
  tools already do.
- **Docs**: `docs-site/docs/features/mcp.md`'s tool-set table gains six
  rows; `mcp/README.md` unaffected (no new transport-level behavior).
- No changes to `atlas_plugin_apis`'s existing REST routes, models, or
  permissions — this change only adds a second, MCP-shaped read path onto
  data that already exists and is already served.
