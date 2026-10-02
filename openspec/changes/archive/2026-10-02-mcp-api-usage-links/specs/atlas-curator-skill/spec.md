## MODIFIED Requirements

### Requirement: Curator writes in dependency order and never duplicates
`atlas-curator` SHALL create entities in this order: Systems, then Resources and APIs, then Components, then references between entities, then Architecture Relationships, then Endpoint and Operation links. Before each create it SHALL search the catalog by kind and name, and an entity that already exists SHALL be updated or left unchanged, never created again.

#### Scenario: Components are created after their system
- **WHEN** a plan contains a system and its components
- **THEN** the system exists before any component that references it is created

#### Scenario: Re-run is idempotent
- **WHEN** the same approved plan is applied a second time
- **THEN** no duplicate entities are created and unchanged entities are reported as unchanged

#### Scenario: Links are created after the API has been parsed
- **WHEN** a plan contains a new API with a specification and a Service that calls one of its endpoints
- **THEN** the curator attaches the specification and confirms the endpoints exist before it creates the link

## ADDED Requirements

### Requirement: Curator authors Endpoint and Operation links through the usage link tools
`atlas-curator` SHALL record that a Service calls an Endpoint, or publishes or subscribes on an Operation, with the usage link tools, never through an entity's `spec` or an Architecture Relationship. It SHALL identify each target by natural key when it has the API, method and path (or channel and direction) and by id when it has already looked the id up. Before linking, it SHALL check the existing consumers or participants with `get_endpoint_consumers` or `get_operation_consumers` and leave an existing link as unchanged. It SHALL send links as batches, grouped by Service. It SHALL read every per-item status and report `not_found`, `ambiguous`, and `conflict` items to the user, and SHALL NOT retry them with a guessed identifier. If the usage link tools are not available, it SHALL say the links cannot be recorded and ask whether to continue without them.

#### Scenario: Call site recorded as an endpoint link
- **WHEN** the plan says `component:booking-web` calls `GET /bookings/{id}` of `api:booking`
- **THEN** the curator links the Service to that Endpoint with `link_endpoint_consumers` using the API, method and path

#### Scenario: Publisher and subscriber recorded with a role
- **WHEN** the plan says a Service publishes to a channel declared by an AsyncAPI document
- **THEN** the curator links it with `link_operation_participants` and the role `publisher`

#### Scenario: Existing link is not duplicated
- **WHEN** the Service is already a consumer of the Endpoint
- **THEN** the curator reports the link as unchanged

#### Scenario: Unresolved target is reported, not guessed
- **WHEN** an item comes back `not_found` or `ambiguous`
- **THEN** the curator lists it with the reason and does not link a different endpoint in its place

#### Scenario: Missing tools
- **WHEN** the usage link tools are not available
- **THEN** the curator tells the user the links cannot be recorded and asks whether to continue with entities and relationships only

### Requirement: Curator confirms before removing usage links
`atlas-curator` SHALL call an unlink tool only when the user explicitly asked to remove specific links, only after showing the links that would be removed from a dry-run and receiving confirmation, and SHALL NOT attempt to remove a link reported as managed by ingestion.

#### Scenario: Removal is previewed first
- **WHEN** the user asks to remove a Service's links to an API's endpoints
- **THEN** the curator runs the unlink with `dryRun`, shows the links that would be removed, and waits for confirmation before the real call

#### Scenario: Removal not requested
- **WHEN** a plan merely omits a link that exists in the catalog
- **THEN** the curator leaves the link and may mention it, but does not remove it
