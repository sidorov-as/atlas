## ADDED Requirements

### Requirement: MCP integration is an optional plugin-provided feature
MCP tool-calling support SHALL be provided entirely by the `atlas.mcp` plugin; a distribution MAY omit it. The MCP wire-protocol transport that speaks to external MCP clients (e.g. a FastMCP process) is a separate, independently deployed consumer of this plugin's HTTP API and is not itself part of this plugin or of composer/manifest composition.

#### Scenario: Distribution without atlas.mcp composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.mcp`
- **THEN** composition succeeds, and no MCP-facing routes or OpenAPI document are present

### Requirement: The MCP API exposes a curated tool surface, not the existing internal API
`atlas.mcp` SHALL publish its own, purpose-built set of operations (`search_catalog`, `get_entity`, catalog create/update/delete, and — when available per the optional Flow dependency below — `list_flows`, `get_flow`, `create_flow`, `update_flow`, `delete_flow`) under its own OpenAPI document, distinct from Atlas's existing SPA-facing API. It SHALL NOT re-expose the SPA-facing API's endpoints under this document.

#### Scenario: MCP OpenAPI document lists only the curated operations
- **WHEN** the MCP plugin's OpenAPI document is generated
- **THEN** it contains only the curated catalog and (if available) Flow operations, and no route from the existing SPA-facing API

### Requirement: The MCP OpenAPI document is available over HTTP, PAT-authenticated
`atlas.mcp` SHALL serve its own OpenAPI document at an HTTP endpoint under this plugin's own prefix, gated by the same Atlas Personal Access Token requirement as every other operation it exposes — so a consumer with no Django import of its own (the MCP transport process) can fetch the current tool surface without calling any Atlas Python function directly.

#### Scenario: The OpenAPI document endpoint requires a valid PAT
- **WHEN** a request for the MCP OpenAPI document endpoint carries no Bearer token, or a token that fails validation
- **THEN** the request is rejected the same way any other MCP API request would be

#### Scenario: A valid PAT retrieves the current document
- **WHEN** a request for the MCP OpenAPI document endpoint carries a valid Bearer PAT
- **THEN** the response is the same document `atlas_plugin_mcp.api.openapi.build_openapi_schema()` returns for the distribution's current plugin selection

### Requirement: Catalog operations route through EntityService
Every catalog read or write exposed by the MCP API SHALL be performed through `EntityService`, never through direct ORM access, so authorization, validation, transaction handling, and audit recording are identical to the existing web UI/REST catalog paths.

#### Scenario: Creating a catalog entity via MCP produces the same audit trail as the web UI
- **WHEN** a catalog entity is created through the MCP API's create operation
- **THEN** the resulting `CatalogEntity` and its audit record are indistinguishable in shape from one created through the existing REST API, other than the recorded actor

#### Scenario: A write rejected by RBAC through the web UI is also rejected through MCP
- **WHEN** the authenticated actor lacks the permission a catalog write would require
- **THEN** the MCP API rejects the request the same way `EntityService` would for any other caller

### Requirement: Flow tools are present only when atlas.flows is installed
`atlas.mcp` SHALL treat `atlas.flows` as an optional, code-level dependency, not a manifest `requires_plugins` entry: `list_flows`, `get_flow`, `create_flow`, `update_flow`, and `delete_flow` SHALL be part of the MCP API and its OpenAPI document only when `atlas.flows` is also selected by the distribution. Composition SHALL succeed either way, and no Flow-related MCP operation SHALL exist to be called when `atlas.flows` is absent.

#### Scenario: Distribution with both plugins exposes Flow operations
- **WHEN** a distribution selects both `atlas.mcp` and `atlas.flows`
- **THEN** the MCP OpenAPI document includes `list_flows`, `get_flow`, `create_flow`, `update_flow`, and `delete_flow`

#### Scenario: Distribution without atlas.flows omits Flow operations entirely
- **WHEN** a distribution selects `atlas.mcp` but not `atlas.flows`
- **THEN** composition succeeds, and the MCP OpenAPI document contains no Flow-related operation

#### Scenario: Flow writes route through FlowService
- **WHEN** `create_flow`, `update_flow`, or `delete_flow` is called through the MCP API
- **THEN** the operation is performed through the published `FlowService` contract, applying the same authorization and validation as the existing Flow REST controllers

### Requirement: Every MCP API request is authenticated by an Atlas Personal Access Token
`atlas.mcp` SHALL require a valid Atlas Personal Access Token, presented as a Bearer credential, on every request; it SHALL resolve a valid token to its owning Django user and pass that user as `actor` into `EntityService`/`FlowService`. A request with no token, an invalid token, or a token that validation rejects (see the `personal-access-tokens` capability) SHALL be denied.

#### Scenario: Valid PAT resolves to the correct actor
- **WHEN** a request carries a valid Bearer PAT
- **THEN** the operation it triggers is attributed, in the resulting audit record, to the Django user that PAT belongs to

#### Scenario: Missing or invalid token is rejected
- **WHEN** a request carries no Bearer token, or a token that fails validation
- **THEN** the MCP API rejects the request without invoking `EntityService`/`FlowService`

### Requirement: PAT scopes narrow the MCP API's effective permissions
A request authenticated by a PAT SHALL be denied if the operation falls outside that token's granted scopes, even when the underlying user's own RBAC would otherwise allow it.

#### Scenario: Read-only-scoped PAT cannot perform a write operation
- **WHEN** a request authenticated by a PAT scoped only to read operations attempts a catalog or Flow write
- **THEN** the request is rejected, regardless of the underlying user's own write permissions
