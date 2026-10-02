## MODIFIED Requirements

### Requirement: API Endpoint/Operation tools are present only when atlas.apis is installed
`atlas.mcp` SHALL treat `atlas.apis` as an optional, code-level dependency, not a manifest `requires_plugins` entry — the same pattern already used for `atlas.flows`. `search_api_endpoints`, `get_api_endpoint`, `get_endpoint_consumers`, `search_api_operations`, `get_api_operation`, `get_operation_consumers`, `link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, and `unlink_operation_participants` SHALL be part of the MCP API and its OpenAPI document only when `atlas.apis` is also selected by the distribution. Composition SHALL succeed either way, and no Endpoint/Operation-related MCP operation SHALL exist to be called when `atlas.apis` is absent. This dependency is independent of the existing `atlas.flows` one: either, both, or neither MAY be installed alongside `atlas.mcp` in any combination.

#### Scenario: Distribution with both atlas.mcp and atlas.apis exposes the new tools
- **WHEN** a distribution selects both `atlas.mcp` and `atlas.apis`
- **THEN** the MCP OpenAPI document includes `search_api_endpoints`, `get_api_endpoint`, `get_endpoint_consumers`, `search_api_operations`, `get_api_operation`, `get_operation_consumers`, `link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`, and `unlink_operation_participants`

#### Scenario: Distribution without atlas.apis omits the new tools entirely
- **WHEN** a distribution selects `atlas.mcp` but not `atlas.apis`
- **THEN** composition succeeds, and the MCP OpenAPI document contains no Endpoint- or Operation-related operation

#### Scenario: The atlas.apis and atlas.flows dependencies are independent
- **WHEN** a distribution selects `atlas.mcp` and `atlas.apis` but not `atlas.flows`
- **THEN** the MCP OpenAPI document includes the Endpoint/Operation tools and excludes every Flow tool

## ADDED Requirements

### Requirement: MCP usage link writes go through the apis plugin's published extension points
`atlas.mcp` SHALL create, check, and remove Service-Endpoint and Service-Operation links only through functions that `atlas.apis` publishes as extension points, taking the PAT's owning user as the actor. It SHALL NOT import the apis plugin's models or its REST controllers. The REST endpoints and the MCP tools SHALL apply the same link rules because both call the same extension-point functions.

#### Scenario: REST and MCP agree on a duplicate link
- **WHEN** a link already created through the REST API is submitted again through an MCP tool
- **THEN** the MCP item is reported `unchanged`, and the REST API rejects the same duplicate as before

#### Scenario: Link rules change in one place
- **WHEN** a rule for creating a link changes in the apis plugin
- **THEN** both the REST endpoint and the MCP tool apply it without a separate change in `atlas.mcp`
