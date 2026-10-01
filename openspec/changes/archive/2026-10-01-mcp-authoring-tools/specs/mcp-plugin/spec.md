## ADDED Requirements

### Requirement: Entity write operations reject unknown fields instead of ignoring them
`create_entity` and `update_entity` SHALL reject, with a 400 error, any key in `spec` or `metadata` that is not a field the target kind accepts through MCP. The error SHALL name each unknown key and SHALL suggest the closest valid field when one is similar. A `relationships` key in `spec` SHALL be rejected with a message that directs the caller to the relationship tools. A rejected request SHALL create or modify nothing.

#### Scenario: Misspelled spec field is rejected
- **WHEN** a client calls `update_entity` with `spec` containing `dependOn` instead of `dependsOn`
- **THEN** the request is rejected with an error naming `dependOn` and suggesting `dependsOn`, and the entity is unchanged

#### Scenario: Unknown spec field is rejected on create
- **WHEN** a client calls `create_entity` with a `spec` key the kind does not define
- **THEN** the request is rejected, and no entity is created

#### Scenario: Relationships in spec are rejected with a pointer
- **WHEN** a client calls `create_entity` or `update_entity` with `relationships` in `spec`
- **THEN** the request is rejected with an error stating that relationships are managed through the relationship tools, and nothing is persisted

#### Scenario: Unknown metadata field is rejected
- **WHEN** a client calls `create_entity` with an unknown key in `metadata`
- **THEN** the request is rejected and nothing is created

#### Scenario: Ingestion is unaffected
- **WHEN** an ingested manifest declares `spec.relationships`
- **THEN** ingestion continues to reconcile them as YAML-origin Architecture Relationships exactly as before

## MODIFIED Requirements

### Requirement: The MCP API exposes a curated tool surface, not the existing internal API
`atlas.mcp` SHALL publish its own, purpose-built set of operations (`search_catalog`, `get_entity`, `describe_kinds`, catalog create/update/delete, `list_relationships`, `create_relationship`, `update_relationship`, `delete_relationship`, and — when available per the optional Flow dependency below — `list_flows`, `get_flow`, `create_flow`, `update_flow`, `delete_flow`, `validate_flow`) under its own OpenAPI document, distinct from Atlas's existing SPA-facing API. It SHALL NOT re-expose the SPA-facing API's endpoints under this document.

#### Scenario: MCP OpenAPI document lists only the curated operations
- **WHEN** the MCP plugin's OpenAPI document is generated
- **THEN** it contains only the curated catalog, relationship, and (if available) Flow operations, and no route from the existing SPA-facing API

### Requirement: Catalog operations route through EntityService
Every catalog read or write exposed by the MCP API SHALL be performed through `EntityService`, and every Architecture Relationship read or write through the published Architecture Relationship service, never through direct ORM access, so authorization, validation, transaction handling, and audit recording are identical to the existing web UI/REST catalog paths.

#### Scenario: Creating a catalog entity via MCP produces the same audit trail as the web UI
- **WHEN** a catalog entity is created through the MCP API's create operation
- **THEN** the resulting `CatalogEntity` and its audit record are indistinguishable in shape from one created through the existing REST API, other than the recorded actor

#### Scenario: A write rejected by RBAC through the web UI is also rejected through MCP
- **WHEN** the authenticated actor lacks the permission a catalog write would require
- **THEN** the MCP API rejects the request the same way `EntityService` would for any other caller

#### Scenario: A relationship write follows the REST rules
- **WHEN** a relationship is created or changed through the MCP API
- **THEN** the same origin and source-permission rules apply as for the REST endpoints, because both call the same service
