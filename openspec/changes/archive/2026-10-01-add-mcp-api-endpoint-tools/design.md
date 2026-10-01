## Context

`atlas.mcp` (`add-mcp-server`) publishes a small, curated tool surface for
catalog entities and Flows, generated from a purpose-built OpenAPI document
(`atlas_plugin_mcp`) that the MCP transport process (`mcp/`) turns into
tools via `FastMCP.from_openapi()`. Flow support is an optional, code-level
dependency: `atlas_plugin_mcp.api.urls.build_router()` includes
`flows/`-prefixed routes only when `django.apps.apps.is_installed
("atlas_plugin_flows")` is true, so a distribution without `atlas.flows`
composes cleanly with no Flow tools and no dead routes.

`atlas.apis` (`extract-apis-plugin`, already merged) owns `Endpoint`
(OpenAPI-shaped) and `Operation` (AsyncAPI-shaped) as child data of the
`api` Entity Kind — not their own registered kind, each reachable only
nested under its owning API (`api-endpoints`/`api-operations` capabilities).
It also owns `ServiceEndpointUsage`/`ServiceOperationUsage`: explicit,
human-asserted "this Service uses this specific Endpoint/Operation" links,
finer-grained than the Component-level `consumesApi` relation
(`endpoint-service-dependencies`/`operation-service-dependencies`
capabilities). All of this already has a full, tested REST surface
(`plugins/apis/backend/atlas_plugin_apis/api/{views,urls}.py`) and a
frontend that renders it (the endpoint/operation detail pages' "Linked
Services" tab). None of it is reachable through `atlas.mcp`: `get_entity`
on an `api` returns only `ApiSpecOut` (type, spec source, sync timestamps),
never its endpoints or operations.

`atlas_plugin_apis.extension_points` already publishes a narrow,
ORM-crossing surface for exactly this kind of cross-plugin read —
`resolve_endpoint()`/`resolve_operation()` (single-id lookup, `None` on a
miss) and their batched counterparts, built for `atlas_plugin_flows`'s
Query/Event step validation. Its own docstring explains why: an ORM-backed
cross-plugin edge "can't be fixed by moving types into a contract package,
since Django ORM querying needs the real model class", so each gets a
narrow function surface instead of the caller importing `ApiEndpoint`/
`ApiOperation` directly.

## Goals / Non-Goals

**Goals:**
- Let an MCP client search Endpoints/Operations (per-API or across every
  API), read one in full detail, and — the specific gap that motivated this
  change — read exactly which Services are linked to it as consumers.
- Reuse `atlas.flows`'s already-proven "optional, code-level dependency"
  pattern for `atlas.apis`, rather than inventing a second mechanism.
- Keep MCP's existing plugin-boundary discipline: no new direct import of
  `atlas_plugin_apis` models from `atlas_plugin_mcp`.
- Enforce the exact same RBAC (`check_endpoint_read_permission` and
  friends) an equivalent REST call would, so an MCP read never returns more
  than the acting user could already see in the web UI.

**Non-Goals:**
- Writing/removing a `ServiceEndpointUsage`/`ServiceOperationUsage` link
  through MCP — linking stays a web UI action; this change is strictly the
  read gap the reported incident surfaced.
- Any new PAT scope. Every existing MCP read tool (`search_catalog`,
  `get_entity`, `list_flows`, `get_flow`) requires a valid PAT but no
  particular scope; these new tools follow that same precedent (see
  Decision 4).
- Changing `atlas_plugin_apis`'s existing REST routes, models, permissions,
  or pagination/search behavior — this only adds a second, MCP-shaped read
  path onto data that already exists.
- A generic "child-resource-of-an-Entity-Kind" abstraction in `atlas.mcp`
  for future plugins with the same shape — one concrete instance (Endpoint/
  Operation) doesn't yet justify generalizing it.

## Decisions

### 1. New MCP controllers call new `atlas_plugin_apis.extension_points` functions, not the ORM directly
Considered:
- **(a) Import `ApiEndpoint`/`ApiOperation`/`ServiceEndpointUsage`/
  `ServiceOperationUsage` directly from `atlas_plugin_mcp`**: least new
  code, but breaks the plugin-boundary discipline this codebase otherwise
  holds everywhere else an ORM-backed cross-plugin read exists (see
  `extension_points.py`'s own stated rationale) — a future change to those
  models' shape would have no single place to check for every consumer.
- **(b) Build a full `EndpointService`/`OperationService` class**, the same
  shape as `EntityService`/`FlowService`: consistent with those precedents,
  but those exist to give a *write* pipeline (authorize → validate →
  transaction → audit) a single owner; this change adds no write path, so a
  full service class is more structure than the problem needs.
- **(c) New, narrow read functions in `atlas_plugin_apis.extension_points`**
  *(chosen)*: `search_endpoints()`, `get_endpoint_consumers()`, and their
  Operation equivalents, each taking the acting user and enforcing the same
  `permissions.py` checks its REST-controller counterpart already does.
  Mirrors `resolve_endpoint()`/`resolve_operation()`'s own precedent in the
  same module exactly, extended from single-id lookup to search/consumers.
  The detail half needs two thin additions too: `resolve_endpoint()`/
  `resolve_operation()` take no actor, so they can't enforce the read
  permission the spec requires, and `atlas_plugin_mcp` may not import
  `atlas_plugin_apis.permissions` itself. `get_endpoint(actor, id)`/
  `get_operation(actor, id)` check the read permission, then delegate to
  the resolver (same `None`-on-a-miss convention) for the new
  `get_api_endpoint`/`get_api_operation` tools.

### 2. One curated search tool per resource, not a reuse of both existing REST shapes
`atlas_plugin_apis` exposes two different REST list shapes today:
per-API (`ApiEndpointListController`, unpaginated, richer filters) and
cross-API (`ApiEndpointSearchController`, paginated, search-only, backing
the Flow step picker). Considered:
- **(a) Expose both as separate MCP tools** (`list_api_endpoints(api_id)`
  and `search_api_endpoints(query)`): mirrors the REST surface exactly, but
  repeats design.md's own Decision 2 mistake it was written to avoid — a
  "chatty, badly-scoped tool list" that just re-exports UI-shaped variety
  rather than curating one.
- **(b) Reuse `EndpointOut`/`OperationOut`/`EndpointSearchResultOut` etc.
  directly** as the MCP response schemas: least new code, but these are
  `atlas_plugin_apis`'s own SPA-facing schemas, not a contract published
  for reuse the way `FlowIn`/`FlowPatch` explicitly were — reusing them
  would let an unrelated SPA-driven schema change silently reshape MCP's
  tool output, the exact coupling `add-mcp-server`'s Decision 2 rejected
  for the standard-catalog per-kind schemas.
- **(c) One `search_api_endpoints(query="", api_id=None, ...)` tool**
  *(chosen)*, with an MCP-owned `EndpointSummaryOut` schema (id, api ref,
  method, path, summary, deprecated, status) — `api_id` folds the per-API
  case in as an optional filter on the same cross-API search, the same
  kind-agnostic-search-with-optional-filters shape `search_catalog` already
  established. `get_api_endpoint` (single id) returns a separate, fuller
  MCP-owned `EndpointOut`-equivalent (adds request/response/security) —
  mirrors the existing summary/detail split `search_catalog`/`get_entity`
  and `list_flows`/`get_flow` already use.

### 3. `get_endpoint_consumers`/`get_operation_consumers` mirror the compact consumers shape, not the paginated/sortable services list
`atlas_plugin_apis` also exposes a richer, paginated, search/sort/
team-filterable services list per endpoint (`EndpointServicesController`)
alongside the compact, unpaginated consumers-graph shape
(`EndpointConsumersController`/`EndpointConsumersOut`). Considered:
- **(a) Mirror the paginated services list**: supports the same search/
  sort/filter the web UI's Linked Services tab does, but nothing in the
  reported gap ("which services use this endpoint") needs pagination or
  sorting — an API typically has a handful of consumers, not enough to
  paginate.
- **(b) Mirror the compact consumers shape** *(chosen)*: a flat list of
  linked Services (ref, name, title, owning team) for a given Endpoint/
  Operation id — exactly answers the question that motivated this change,
  with the simplest possible tool signature (one required id, no query
  params). Operations additionally carry each participant's `role`
  (`publisher`/`subscriber`), mirroring `OperationConsumersOut`'s own
  shape, since direction is exactly what makes an Operation-level answer
  meaningful (unlike an Endpoint, which has none).
- Search/sort/paginated browsing of an endpoint's consumers stays a web UI
  concern; nothing prevents adding it as a later, separate tool if an
  actual need shows up.

### 4. No new PAT scope; every new tool requires a valid PAT, like every existing MCP read tool
Considered:
- **(a) A new `apis:read` scope**: consistent in spirit with the existing
  `catalog:read`/`flows:read` scopes, but those two currently gate nothing
  (`add-mcp-server`'s own Open Questions: "every read tool is open to any
  valid token; reserved for a future read gate") — adding a third
  not-yet-enforced scope compounds an already-acknowledged gap instead of
  closing it.
- **(b) No new scope** *(chosen)*: these tools require a valid PAT (via
  `PATBearerAuth`) and the same RBAC (`check_endpoint_read_permission` and
  friends) the equivalent REST read already enforces, exactly matching how
  `search_catalog`/`get_entity`/`list_flows`/`get_flow` behave today. When
  a real read-scope gate is eventually added for the existing `catalog:
  read`/`flows:read` scopes, extending it to cover these tools is a small
  , uniform follow-up, not a second bespoke mechanism to retrofit.

### 5. `atlas.apis` becomes a second optional, code-level MCP dependency, via the same mechanism as `atlas.flows`
Considered:
- **(a) A manifest `requires_plugins` dependency**: rejected for the exact
  reason `add-mcp-server`'s Decision 5 already rejected it for
  `atlas.flows` — it's mandatory in this composer, so it would make the
  *entire* `atlas.mcp` plugin, including catalog tools that have nothing to
  do with `atlas.apis`, uninstallable in any distribution lacking it.
- **(b) Publish the new tools unconditionally, fail at call time** if
  `atlas.apis` isn't installed: same rejection as Decision 5(b) in
  `add-mcp-server` — an avoidable, late failure for a condition knowable at
  OpenAPI-document-build time.
- **(c) Optional, code-level dependency** *(chosen)*: `atlas_plugin_mcp.
  api.urls.build_router()` gains a second conditional block, `_api_urls()`,
  checking `django_apps.is_installed("atlas_plugin_apis")` exactly the way
  `_flow_urls()` already checks `atlas_plugin_flows` — present in the MCP
  OpenAPI document (and therefore as MCP tools) only when `atlas.apis` is
  actually selected alongside `atlas.mcp`.

## Risks / Trade-offs

- **[Risk]** A sixth/seventh new tool grows the MCP tool list further,
  compounding the "does the model reach for the right tool" discoverability
  problem `add-mcp-server`'s `instructions` field was written to address.
  → **Mitigation:** extend `mcp/atlas_mcp/server.py`'s conditional
  `instructions` block (already gated on Flow-tool presence) with a short,
  similarly-gated paragraph for these tools, so an agent is told when and
  why to reach for `get_endpoint_consumers`/`get_operation_consumers`
  specifically, the same way it's already told about `search_flow_icons`.
- **[Risk]** `atlas.apis` and `atlas.flows` being independent optional
  dependencies means four distinct MCP tool-surface shapes are possible
  (neither, either, or both installed) — more combinations for the OpenAPI
  document test suite to cover than `add-mcp-server` needed.
  → **Mitigation:** mirror `test_openapi_document.py`'s existing pattern
  (`django_apps.is_installed` monkeypatches) per dependency, plus one test
  asserting the two are independent (e.g. `atlas.apis` without
  `atlas.flows` still exposes endpoint/operation tools and vice versa).
- **[Risk]** `get_endpoint()`/`get_operation()` delegate to
  `resolve_endpoint()`/`resolve_operation()`, so for
  `get_api_endpoint`/`get_api_operation` a `removed`-status Endpoint/
  Operation still resolves (that function's own docstring: "status
  filtering is the caller's business, not this lookup's") — an MCP client
  could read a removed Endpoint's detail without realizing it.
  → **Mitigation:** the MCP response schema surfaces `status` explicitly
  (already true of `EndpointOut`/`OperationOut`, carried over as-is), so a
  client can tell; no silent 404-vs-removed ambiguity.

## Migration Plan

1. Add `search_endpoints()`/`get_endpoint()`/`get_endpoint_consumers()` and
   `search_operations()`/`get_operation()`/`get_operation_consumers()` to
   `atlas_plugin_apis.extension_points`, each enforcing the same
   `permissions.py` read checks their REST-controller counterpart does.
2. Add `plugins/mcp/backend/atlas_plugin_mcp/api/endpoint_views.py` (naming
   mirrors `flow_views.py`) with the six new controllers, plus their MCP-
   owned schemas in `api/schemas.py`, calling only `atlas_plugin_apis.
   extension_points` (including `get_endpoint()`/`get_operation()`) — never
   `atlas_plugin_apis`'s models directly.
3. Wire `_api_urls()` into `atlas_plugin_mcp.api.urls.build_router()`,
   conditional on `atlas_plugin_apis` being installed, alongside the
   existing `_flow_urls()`.
4. Extend `mcp/atlas_mcp/server.py`'s conditional `instructions` text for
   the new tools (Risk above).
5. Update `docs-site/docs/features/mcp.md`'s tool-set table and
   enablement/dependency notes.

**Rollback:** removing `atlas.apis` from a distribution that has it (or
never adding it) simply removes these six tools from the MCP OpenAPI
document, the same as removing `atlas.flows` already does for Flow tools —
no data migration, no irreversible step.

## Open Questions

- Whether a future `apis:read` PAT scope (if one is ever added for
  `catalog:read`/`flows:read`) should also gate these tools — deferred
  alongside that existing, already-open question in `add-mcp-server`.
