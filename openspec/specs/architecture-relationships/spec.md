# architecture-relationships Specification

## Purpose

Store authored, directed runtime interactions independently of derived catalog relations and expose them to catalog clients and C4 rendering.

## Requirements

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
The relations API and UI SHALL expose derived Catalog Relations separately from Architecture Relationships. An Architecture Relationship listing for an entity SHALL include every relationship where that entity is the source or target and SHALL retain canonical source, target, direction, origin, target kind, id, and ref navigation. Write authorization and mutation SHALL remain tied to a manually managed source entity.

#### Scenario: Component has both kinds of relationships
- **WHEN** a Component has a derived `consumesAPI` relation and a declared architecture interaction
- **THEN** its Relations tab shows the derived relation in Catalog relations and the declared interaction in Architecture relationships

#### Scenario: Target lists an authored incoming interaction
- **WHEN** `component:customer-portal` declares an Architecture Relationship to `component:api-gateway`
- **THEN** the architecture-relationship listing for `component:api-gateway` includes that canonical directed relationship with `component:customer-portal` as its source

#### Scenario: Target cannot edit a manual incoming interaction
- **WHEN** an authorized user views a manual Architecture Relationship from the target entity's Relations tab
- **THEN** the API and UI do not allow that target entity to update or delete the relationship

### Requirement: Declared relationships override duplicate derived diagram edges
When diagram construction encounters an Architecture Relationship and a derived fallback relation with the same directed visible endpoints, it SHALL render the declared relationship and SHALL not render a duplicate fallback edge.

#### Scenario: Explicit API call replaces generic dependency label
- **WHEN** a Component has a derived dependency and a declared relationship to the same visible target labeled `Makes API calls to`
- **THEN** the diagram shows one edge labeled `Makes API calls to`

### Requirement: Explicit User and Group interactions are represented as C4 People
The system SHALL allow any catalog entity whose kind declares the `architecture.actor.v1` capability (which `group` and `actor` — renamed from `user` in `introduce-catalog-entity-identity` — both declare) as an Architecture Relationship endpoint. A System Context diagram SHALL render an explicitly related capability-declaring entity as a C4 Person, while ownership alone SHALL not render a Person.

#### Scenario: Explicit actor interaction appears as a person
- **WHEN** a catalog entity whose kind declares `architecture.actor.v1` (e.g. an Actor or a Group) has an explicit Architecture Relationship to a System or Component in the selected System's context
- **THEN** the System Context diagram includes that entity as a Person and renders the declared interaction

#### Scenario: A future capability-declaring kind needs no C4 change
- **WHEN** a new Entity Kind is registered declaring `architecture.actor.v1`
- **THEN** its entities render as C4 People when explicitly related, without any change to the C4 plugin's own code

### Requirement: Architecture Relationship listings surface a removed or deprecated endpoint's status
An Architecture Relationship listing entry SHALL include the source and target entities' current `status` (`active`/`removed`) and `deprecated` flag, so a Relations tab or C4 diagram consumer can visibly warn when a declared interaction points at an entity that is no longer active or is going away, rather than presenting it as a healthy edge.

#### Scenario: A relationship to a removed target is listed with its status
- **WHEN** a Component's Architecture Relationship listing includes an interaction whose target is now `removed`
- **THEN** that listing entry includes `status: "removed"` for the target

#### Scenario: A relationship from a removed source is listed with its status
- **WHEN** a `removed` Component's outgoing Architecture Relationship is listed from its target's perspective
- **THEN** that listing entry includes `status: "removed"` for the source

#### Scenario: A relationship to a deprecated target is listed with its flag
- **WHEN** a Component's Architecture Relationship listing includes an interaction whose target is `deprecated`
- **THEN** that listing entry includes `deprecated: true` for the target

### Requirement: Booking demo demonstrates actor architecture interactions
The booking demo seed SHALL create representative Architecture Relationships for synchronous, asynchronous, data-access, manual, and external interactions, including at least one explicit User or Group actor interaction.

#### Scenario: Seeded context shows a person
- **WHEN** an operator seeds the booking demo and opens the relevant System Context diagram
- **THEN** it includes the seeded actor as a Person and its explicit interaction
