## ADDED Requirements

### Requirement: Catalog entities are searchable
The catalog SHALL register a search source producing one document per active catalog entity with the entity's name as title and its description and documentation as body. The document id SHALL identify the entity and kind.

#### Scenario: Entity found by name
- **WHEN** a user searches for part of an entity's name
- **THEN** the entity appears in results

#### Scenario: Entity found by documentation
- **WHEN** a user searches for a phrase present only in an entity's documentation
- **THEN** the entity appears with a snippet around the phrase

### Requirement: Removed entities are not searchable
Entities in a removed or purged state SHALL NOT appear in results, and changing an entity's state SHALL update the index.

#### Scenario: Entity removed
- **WHEN** an entity is removed
- **THEN** it disappears from results after the next indexing run

#### Scenario: Entity revived
- **WHEN** a removed entity is revived
- **THEN** it reappears in results after the next indexing run

### Requirement: Entity visibility follows existing read rules
The source's `resolve` SHALL apply the catalog's existing entity read rules for the requesting actor.

#### Scenario: Actor lacks read access
- **WHEN** the actor cannot read an entity under existing catalog rules
- **THEN** that entity is omitted from search results

### Requirement: Edits reach the index without a request-time engine call
Creating, updating, removing or reviving an entity SHALL record a pending change and SHALL NOT call the engine during the request.

#### Scenario: Engine down during an edit
- **WHEN** an entity is edited while the engine is unavailable
- **THEN** the edit succeeds and the change is indexed once the engine returns
