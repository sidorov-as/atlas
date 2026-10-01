# mcp-kind-introspection Specification

## Purpose

Lets MCP clients discover the spec shapes of the catalog kinds writable through MCP (TBD: refine).

## Requirements

### Requirement: describe_kinds reports the writable kinds' spec shapes
The MCP API SHALL publish a `describe_kinds` operation that returns, for each kind writable through MCP and currently registered, the kind id, the field schema of its create `spec`, and the field schema of its patch `spec`, including field names, types, enum values, required fields, and length limits. The schemas SHALL be derived from the registered kind handlers' own schemas so they cannot drift from what the write operations accept.

#### Scenario: Component enums are reported
- **WHEN** a client calls `describe_kinds`
- **THEN** the Component entry lists its `type` values (`service`, `website`, `library`, `worker`) and `lifecycle` values (`experimental`, `production`, `deprecated`) and marks `owner` and `system` required

#### Scenario: API spec fields are reported
- **WHEN** `atlas.apis` is installed and a client calls `describe_kinds`
- **THEN** the API entry lists its `type` values, its `specSource` values (`none`, `inline`, `url`), and the maximum `specContent` length

#### Scenario: Create schema omits relationships
- **WHEN** a client reads any kind's create schema from `describe_kinds`
- **THEN** it does not list a `relationships` field, because relationships are authored through the relationship tools

### Requirement: describe_kinds reflects the installed plugin selection
`describe_kinds` SHALL list only kinds that are both MCP-writable and registered in the running distribution, and SHALL accept an optional kind filter that restricts the result to one kind.

#### Scenario: Kind from an absent plugin is not listed
- **WHEN** the distribution does not select `atlas.apis`
- **THEN** `describe_kinds` does not list the API kind

#### Scenario: Filtering to one kind
- **WHEN** a client calls `describe_kinds` with a kind filter
- **THEN** only that kind's entry is returned, and an unknown or non-writable kind is rejected with a clear error

### Requirement: describe_kinds requires read access
`describe_kinds` SHALL require a valid PAT with the `catalog:read` scope.

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request to `describe_kinds` carries no valid Bearer PAT
- **THEN** it is rejected without returning any schema
