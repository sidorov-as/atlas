## ADDED Requirements

### Requirement: Declared architecture relationships are first-class directed records
The system SHALL store Architecture Relationships separately from derived catalog `Relation` records. An Architecture Relationship SHALL identify a source and target catalog entity, a non-empty label, optional technology, an interaction kind of `synchronous`, `asynchronous`, `data-access`, or `manual`, tags, and an origin of `manual` or `yaml`.

#### Scenario: Manual relationship retains C4 interaction metadata
- **WHEN** an authorized user creates an Architecture Relationship from `component:customer-portal` to `component:api-gateway` with label `Makes API calls to` and technology `REST/HTTPS`
- **THEN** the relationship is persisted as a directed manual relationship with those values available to the API and diagram generator

#### Scenario: Derived relations remain independent
- **WHEN** a Component's `dependsOn` field is changed and derived catalog relations are recomputed
- **THEN** no Architecture Relationship is deleted, regenerated, or otherwise modified

### Requirement: Architecture relationships are managed according to entity origin
The system SHALL allow authorized users to create, update, and delete manual Architecture Relationships from manually managed source entities. YAML-origin Architecture Relationships SHALL be read-only through the API and web UI.

#### Scenario: Owner edits a manual outgoing relationship
- **WHEN** a user permitted to write a manual source Component updates its relationship label
- **THEN** the updated label is returned from that Component's architecture-relationship listing

#### Scenario: YAML-declared relationship cannot be edited manually
- **WHEN** a user attempts to update or delete an Architecture Relationship whose origin is `yaml`
- **THEN** the system rejects the request and preserves the declared relationship

### Requirement: Relations views distinguish catalog structure from architecture interactions
The relations API and UI SHALL expose derived Catalog Relations separately from Architecture Relationships, while retaining target kind, id, and ref navigation for both categories.

#### Scenario: Component has both kinds of relationships
- **WHEN** a Component has a derived `consumesAPI` relation and a declared architecture interaction
- **THEN** its Relations tab shows the derived relation in Catalog relations and the declared interaction in Architecture relationships

### Requirement: Declared relationships override duplicate derived diagram edges
When diagram construction encounters an Architecture Relationship and a derived fallback relation with the same directed visible endpoints, it SHALL render the declared relationship and SHALL not render a duplicate fallback edge.

#### Scenario: Explicit API call replaces generic dependency label
- **WHEN** a Component has a derived dependency and a declared relationship to the same visible target labeled `Makes API calls to`
- **THEN** the diagram shows one edge labeled `Makes API calls to`
