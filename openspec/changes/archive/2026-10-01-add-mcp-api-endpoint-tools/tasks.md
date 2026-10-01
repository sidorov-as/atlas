## 1. atlas.apis: read-only extension points

- [x] 1.1 Add `search_endpoints(actor, query="", api_id=None, page=1, page_size=20)` to `atlas_plugin_apis.extension_points`: cross-API by default, scoped to one API when `api_id` is given, `status="active"` only — mirrors `ApiEndpointSearchController`'s query shape; enforces `check_endpoint_read_permission(actor)` internally
- [x] 1.2 Add `get_endpoint_consumers(actor, endpoint_id)` to `atlas_plugin_apis.extension_points`: the Services linked via `ServiceEndpointUsage` for one Endpoint, `None` for an unresolvable id (mirrors `resolve_endpoint()`'s own not-found convention); enforces `check_endpoint_dependency_read_permission(actor)` internally
- [x] 1.3 Add `search_operations(actor, query="", api_id=None, page=1, page_size=20)` to `atlas_plugin_apis.extension_points` — mirrors 1.1 for `ApiOperation`/`ApiOperationSearchController`; enforces `check_operation_read_permission(actor)`
- [x] 1.4 Add `get_operation_consumers(actor, operation_id)` to `atlas_plugin_apis.extension_points`: linked Services with their `publisher`/`subscriber` role, mirroring `OperationConsumersController`'s channel-participant aggregation; enforces `check_operation_dependency_read_permission(actor)`
- [x] 1.5 Add tests for all four: permission-denied rejection, `api_id`-scoped vs. cross-API search, empty-consumers case, and that a Component-level `consumesApi`-only Service (no explicit `ServiceEndpointUsage`/`ServiceOperationUsage`) does not appear in a consumers result

## 2. atlas.mcp: new controllers and schemas

- [x] 2.1 Add MCP-owned read schemas to `plugins/mcp/backend/atlas_plugin_mcp/api/schemas.py`: `EndpointSummaryOut`, `EndpointOut` (request/responses/security included), `EndpointConsumersOut`, and the three Operation equivalents — new vocabulary, not a reuse of `atlas_plugin_apis.api.schemas`
- [x] 2.2 Add `plugins/mcp/backend/atlas_plugin_mcp/api/endpoint_views.py` with `EndpointSearchController` (`search_api_endpoints`), `EndpointDetailController` (`get_api_endpoint`, via `atlas_plugin_apis.extension_points.get_endpoint()`, a permission-checked wrapper over `resolve_endpoint()`), and `EndpointConsumersController` (`get_endpoint_consumers`)
- [x] 2.3 Add the three Operation-equivalent controllers to the same module (`search_api_operations`, `get_api_operation` via `get_operation()`, a permission-checked wrapper over `resolve_operation()`, `get_operation_consumers`)
- [x] 2.4 Set explicit `operation_id`/`summary`/`description` on every new controller method via `@modify(...)`, matching the short tool names above exactly — do not repeat the auto-generated-`operationId` gap `add-mcp-api-endpoint-tools`'s own predecessor bug fix addressed for the existing tools
- [x] 2.5 Add `_api_urls()` to `atlas_plugin_mcp.api.urls`, conditional on `django_apps.is_installed("atlas_plugin_apis")`, wired into `build_router()` alongside the existing `_flow_urls()`

## 3. Tests

- [x] 3.1 Add a test asserting the MCP OpenAPI document includes all six new operations when `atlas.apis` is installed, and omits every one when it isn't
- [x] 3.2 Add a test asserting the `atlas.apis` and `atlas.flows` MCP dependencies are independent (each present/absent regardless of the other)
- [x] 3.3 Add a test asserting every new operation's `operationId` is the short, explicit name (`search_api_endpoints`, etc.), not `dmr`'s auto-generated fallback
- [x] 3.4 Add tests asserting `get_endpoint_consumers`/`get_operation_consumers` return exactly the `ServiceEndpointUsage`/`ServiceOperationUsage`-linked Services, excluding a Service that only consumes the owning API at the whole-API level
- [x] 3.5 Add a test asserting a PAT with no scopes can call every new tool (no scope currently required, matching existing MCP read tools)
- [x] 3.6 Add a test asserting a user lacking the relevant `atlas_plugin_apis` read/dependency-read permission is rejected through MCP the same way the equivalent REST call would reject them

## 4. MCP transport and documentation

- [x] 4.1 Extend `mcp/atlas_mcp/server.py`'s conditional `instructions` text with a short, similarly-gated paragraph covering the new tools (present only when the fetched OpenAPI document lists them), telling an agent to reach for `get_endpoint_consumers`/`get_operation_consumers` specifically for a "which services use this endpoint/operation" question instead of falling back to the coarser Component-level relation
- [x] 4.2 Add/update `mcp/tests/test_server.py` coverage for the new conditional instructions text
- [x] 4.3 Update `docs-site/docs/features/mcp.md`'s tool-set table with the six new rows and a short note on the new `atlas.apis` optional dependency, mirroring the existing `atlas.flows` note
- [x] 4.4 Verify end-to-end against a real backend-generated OpenAPI document (as for the `operation_id` fix) that `FastMCP.from_openapi()` produces clean tool names and non-empty descriptions for all six new tools
