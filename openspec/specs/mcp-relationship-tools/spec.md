# mcp-relationship-tools Specification

## Purpose

MCP tools for listing and managing manual Architecture Relationships (TBD: refine).

## Requirements

### Requirement: Relationship tools manage manual Architecture Relationships
The MCP API SHALL publish `list_relationships`, `create_relationship`, `update_relationship`, and `delete_relationship` operations, each performed through the published Architecture Relationship service. `create_relationship` SHALL accept a source ref, a target ref, a non-empty label, an optional technology, an interaction kind of `synchronous`, `asynchronous`, `data-access`, or `manual`, and tags, and SHALL always record the relationship with origin `manual`.

#### Scenario: Creating a manual relationship
- **WHEN** an authorized client calls `create_relationship` from `component:customer-portal` to `component:api-gateway` with label `Makes API calls to`, technology `REST/HTTPS`, and interaction kind `synchronous`
- **THEN** a directed manual Architecture Relationship is persisted with those values and returned with its id

#### Scenario: Updating a manual relationship
- **WHEN** an authorized client calls `update_relationship` with only a new label
- **THEN** the label changes and every omitted field is left untouched

#### Scenario: Deleting a manual relationship
- **WHEN** an authorized client calls `delete_relationship` for a manual relationship
- **THEN** the relationship no longer appears in either endpoint's listing

### Requirement: Relationship listing returns incoming and outgoing relationships with origin
`list_relationships` SHALL take an entity ref and return every Architecture Relationship where that entity is the source or the target, each with its id, source, target, label, technology, interaction kind, tags, and origin.

#### Scenario: Listing shows both directions
- **WHEN** a client lists relationships for an entity that is the source of one relationship and the target of another
- **THEN** both are returned and each states its source, target, and origin

#### Scenario: Listing shows YAML-origin relationships
- **WHEN** an entity has a relationship declared by an ingested manifest
- **THEN** it appears in the listing with origin `yaml`

### Requirement: YAML-origin relationships are read-only through MCP
`update_relationship` and `delete_relationship` SHALL reject any relationship whose origin is `yaml`, and the rejection SHALL state that the relationship is managed by ingestion.

#### Scenario: Updating a YAML-origin relationship is rejected
- **WHEN** a client calls `update_relationship` for a relationship with origin `yaml`
- **THEN** the request is rejected and the relationship is unchanged

#### Scenario: Deleting a YAML-origin relationship is rejected
- **WHEN** a client calls `delete_relationship` for a relationship with origin `yaml`
- **THEN** the request is rejected and the relationship is unchanged

### Requirement: Relationship sources are limited to manually writable entity kinds and require write permission
A relationship's source SHALL be a System, Component, Resource, or API, and the acting user SHALL hold write permission on the source entity. A relationship whose source is an entity managed by ingestion SHALL not be mutated through MCP. A relationship's target MAY be any catalog entity that resolves.

#### Scenario: Source of a non-writable kind is rejected
- **WHEN** a client calls `create_relationship` with a Group as the source
- **THEN** the request is rejected and nothing is created

#### Scenario: Missing write permission on the source is rejected
- **WHEN** the acting user lacks write permission on the source entity
- **THEN** the request is rejected the same way the REST endpoint rejects it

#### Scenario: Unresolvable target is rejected
- **WHEN** a client calls `create_relationship` with a target ref that does not resolve to a catalog entity
- **THEN** the request is rejected with an error naming the target and nothing is created

### Requirement: Relationship tools require catalog PAT scopes
`list_relationships` SHALL require the `catalog:read` scope, and `create_relationship`, `update_relationship`, and `delete_relationship` SHALL require the `catalog:write` scope.

#### Scenario: Read-only token cannot write a relationship
- **WHEN** a request authenticated by a PAT scoped only to `catalog:read` calls `create_relationship`
- **THEN** the request is rejected regardless of the underlying user's own permissions
