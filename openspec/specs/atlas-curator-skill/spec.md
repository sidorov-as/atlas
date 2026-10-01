# atlas-curator-skill Specification

## Purpose

The `atlas-curator` skill: the only skill that writes catalog entities and relationships through the MCP server (TBD: refine).

## Requirements

### Requirement: Curator is the only skill that writes entities
`atlas-curator` SHALL create and update catalog entities (Systems, Components, Resources, APIs) and their relationships on behalf of the user or of another skill's approved plan. It SHALL write only kinds the MCP server accepts and SHALL tell the user when asked for a kind it cannot write, such as a Group.

#### Scenario: Unsupported kind is declined
- **WHEN** the user asks the curator to create a Group
- **THEN** it explains that groups are managed in Atlas itself and creates nothing

### Requirement: Curator learns the kinds from the server when it can
When the kind-introspection tool is available, `atlas-curator` SHALL use it as the source of truth for fields, enum values, and limits; otherwise it SHALL use its bundled reference and say that the reference may be out of date. It SHALL send only fields the kind defines.

#### Scenario: Introspection available
- **WHEN** the server offers kind introspection
- **THEN** the curator takes enum values and required fields from it rather than from its bundled reference

#### Scenario: Introspection missing
- **WHEN** the server does not offer kind introspection
- **THEN** the curator uses its bundled reference and tells the user

### Requirement: Curator writes in dependency order and never duplicates
`atlas-curator` SHALL create entities in this order: Systems, then Resources and APIs, then Components, then references between entities, then Architecture Relationships. Before each create it SHALL search the catalog by kind and name, and an entity that already exists SHALL be updated or left unchanged, never created again.

#### Scenario: Components are created after their system
- **WHEN** a plan contains a system and its components
- **THEN** the system exists before any component that references it is created

#### Scenario: Re-run is idempotent
- **WHEN** the same approved plan is applied a second time
- **THEN** no duplicate entities are created and unchanged entities are reported as unchanged

### Requirement: Curator never overwrites list fields blindly
Before changing a list-valued field such as `dependsOn`, `providesApis`, or `consumesApis`, `atlas-curator` SHALL read the entity and send the merged list, so existing values are kept unless the user asked to remove them.

#### Scenario: Existing dependency is kept
- **WHEN** a component already depends on one resource and the plan adds a second
- **THEN** the saved list contains both

### Requirement: Curator takes owners from existing groups
`atlas-curator` SHALL list existing groups through the MCP server and ask the user which group owns each system, offering to apply one choice across the batch. When the intended group does not exist, it SHALL stop and tell the user to create it in Atlas, and SHALL NOT assign a different group.

#### Scenario: Owner chosen from existing groups
- **WHEN** the curator needs an owner
- **THEN** it offers the existing groups and uses the user's choice

#### Scenario: Missing group blocks the write
- **WHEN** the user names a group that does not exist
- **THEN** the curator tells the user to create it first and writes nothing for that owner

### Requirement: Curator attaches API specifications and verifies the result
For an API with an OpenAPI or AsyncAPI document available, `atlas-curator` SHALL attach it inline (warning when it exceeds the size limit) or by public HTTPS URL when the user supplies one, then SHALL read the API back, report any spec-resolution or sync failure, and confirm that endpoints or operations were created. For an API without a document it SHALL create the API without a spec and tell the user endpoints appear once a spec is attached. For gRPC and GraphQL it SHALL tell the user the spec is stored but not parsed into endpoints.

#### Scenario: Spec attached and verified
- **WHEN** an OpenAPI file is attached to a new API
- **THEN** the curator reports the number of endpoints found, or the failure flag if parsing failed

#### Scenario: Oversized spec
- **WHEN** a spec document exceeds the size limit
- **THEN** the curator warns the user and does not send it inline

#### Scenario: No spec available
- **WHEN** no spec document exists for an API
- **THEN** the API is created without a spec and the user is told how endpoints will appear

### Requirement: Curator authors relationships through the relationship tools
`atlas-curator` SHALL create Architecture Relationships with the relationship tools, giving each a label, a technology when known, and an interaction kind, after checking the existing relationships so it does not duplicate one. It SHALL NOT place relationships in an entity's `spec`, and SHALL NOT change a relationship whose origin is YAML, reporting it as managed by ingestion.

#### Scenario: Relationship created with a label
- **WHEN** the plan says one component calls another over HTTP
- **THEN** the curator creates a relationship with a label, the technology, and a synchronous interaction kind

#### Scenario: Existing relationship is not duplicated
- **WHEN** an equivalent relationship already exists
- **THEN** the curator leaves it and reports it as unchanged

#### Scenario: Ingested relationship is left alone
- **WHEN** a relationship has origin `yaml`
- **THEN** the curator does not modify it and tells the user it is managed by ingestion

### Requirement: Curator shows a confirmed summary and reports exact outcomes
Before writing, `atlas-curator` SHALL show a summary of each entity and relationship to be created or changed, built from the server's dry-run when available, and SHALL wait for confirmation. During and after the write it SHALL keep a ledger of what it created or changed, and on any failure it SHALL report precisely what was written and what remains, so the plan can be re-applied safely.

#### Scenario: Summary comes from dry-run
- **WHEN** the server supports dry-run
- **THEN** the summary is built from dry-run responses and the user confirms it before any real write

#### Scenario: Partial failure is reported
- **WHEN** a write fails after some entities were created
- **THEN** the curator lists the entities already written and those still pending, and stops
