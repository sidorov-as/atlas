## ADDED Requirements

### Requirement: API Endpoint/Operation tools are present only when atlas.apis is installed
`atlas.mcp` SHALL treat `atlas.apis` as an optional, code-level dependency, not a manifest `requires_plugins` entry — the same pattern already used for `atlas.flows`. `search_api_endpoints`, `get_api_endpoint`, `get_endpoint_consumers`, `search_api_operations`, `get_api_operation`, and `get_operation_consumers` SHALL be part of the MCP API and its OpenAPI document only when `atlas.apis` is also selected by the distribution. Composition SHALL succeed either way, and no Endpoint/Operation-related MCP operation SHALL exist to be called when `atlas.apis` is absent. This dependency is independent of the existing `atlas.flows` one: either, both, or neither MAY be installed alongside `atlas.mcp` in any combination.

#### Scenario: Distribution with both atlas.mcp and atlas.apis exposes the new tools
- **WHEN** a distribution selects both `atlas.mcp` and `atlas.apis`
- **THEN** the MCP OpenAPI document includes `search_api_endpoints`, `get_api_endpoint`, `get_endpoint_consumers`, `search_api_operations`, `get_api_operation`, and `get_operation_consumers`

#### Scenario: Distribution without atlas.apis omits the new tools entirely
- **WHEN** a distribution selects `atlas.mcp` but not `atlas.apis`
- **THEN** composition succeeds, and the MCP OpenAPI document contains no Endpoint- or Operation-related operation

#### Scenario: The atlas.apis and atlas.flows dependencies are independent
- **WHEN** a distribution selects `atlas.mcp` and `atlas.apis` but not `atlas.flows`
- **THEN** the MCP OpenAPI document includes the Endpoint/Operation tools and excludes every Flow tool

### Requirement: Endpoint and Operation tools expose a curated search-then-detail shape
`atlas.mcp` SHALL expose Endpoint and Operation search as a single tool each (`search_api_endpoints`, `search_api_operations`), matching by free-text query and optionally scoped to one API by id, returning a paginated list of summaries. It SHALL expose a separate detail tool for each (`get_api_endpoint`, `get_api_operation`) returning one Endpoint's or Operation's full documented shape (method/path or channel/direction, summary, description, deprecation, status, and — for an Endpoint — its request parameters/body and responses). Neither search nor detail tool SHALL re-expose the SPA-facing API's own response schemas directly; each uses its own MCP-scoped read shape.

#### Scenario: Searching endpoints across every API
- **WHEN** `search_api_endpoints` is called with a free-text query and no `api_id`
- **THEN** it returns matching active Endpoints from every API, each summary identifying its owning API

#### Scenario: Searching endpoints scoped to one API
- **WHEN** `search_api_endpoints` is called with an `api_id`
- **THEN** only that API's Endpoints are searched

#### Scenario: Reading one endpoint's full detail
- **WHEN** `get_api_endpoint` is called with a valid Endpoint id
- **THEN** the response includes that Endpoint's request parameters/body and responses, not just its summary fields

### Requirement: Endpoint/Operation consumer tools expose the explicit Service link, not the coarser API-level relation
`get_endpoint_consumers` SHALL return exactly the Services linked to the given Endpoint via an explicit `ServiceEndpointUsage` record; `get_operation_consumers` SHALL return exactly the Services linked to the given Operation via an explicit `ServiceOperationUsage` record, each tagged with its `publisher`/`subscriber` role. Neither tool SHALL derive its answer from the coarser, Component-level API-wide consumption relation — a Service consuming the owning API as a whole, with no explicit link to the specific Endpoint or Operation, SHALL NOT appear in either tool's result.

#### Scenario: Only explicitly linked services appear as endpoint consumers
- **WHEN** `get_endpoint_consumers` is called for an Endpoint that some Service consumes at the whole-API level but has no `ServiceEndpointUsage` link to
- **THEN** that Service does not appear in the result

#### Scenario: Operation consumers carry their role
- **WHEN** `get_operation_consumers` is called for an Operation with both a publisher and a subscriber linked
- **THEN** the result distinguishes which linked Service holds which role

### Requirement: Endpoint/Operation tools enforce the same read permissions as their REST equivalents
Every Endpoint/Operation MCP tool SHALL enforce the same RBAC read permission its equivalent REST endpoint already enforces (Endpoint/Operation read permission for search and detail; Endpoint/Operation dependency-read permission for consumer lookups), evaluated against the PAT's owning Django user. No new PAT scope SHALL be required beyond a valid token, matching every other existing MCP read tool.

#### Scenario: A user without dependency-read permission is denied through MCP the same way they would be through the REST API
- **WHEN** a PAT belonging to a user who lacks Endpoint-dependency-read permission calls `get_endpoint_consumers`
- **THEN** the request is rejected the same way the equivalent REST call would be for that user

#### Scenario: A valid PAT with no particular scope can call every new read tool
- **WHEN** a request to any of the six new tools carries a valid Bearer PAT with no scopes granted
- **THEN** the request is not rejected for lacking a scope
