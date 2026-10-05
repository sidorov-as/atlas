## ADDED Requirements

### Requirement: Database schemas are searchable
The database schema plugin SHALL register a search source producing one document per schema facet, with the owning resource's name as title and the names of its tables and columns as body.

#### Scenario: Found by table name
- **WHEN** a user searches for the name of a table in a schema
- **THEN** the owning resource's schema appears in results

#### Scenario: Found by column name
- **WHEN** a user searches for the name of a column
- **THEN** the schemas containing it appear in results

### Requirement: A schema hit opens the owning resource's schema view
A schema result SHALL link to the schema view of its owning resource. A match on a table or column SHALL lead to the schema view as a whole.

#### Scenario: Open a schema from search
- **WHEN** the user opens a schema result
- **THEN** the application navigates to the owning resource's schema view

### Requirement: Schemas that failed to parse are still discoverable
A schema whose parse status is failed SHALL still be indexed by the owning resource's name and SHALL NOT break indexing.

#### Scenario: Failed parse
- **WHEN** a schema has failed to parse
- **THEN** it is indexed from its title only and indexing of other documents continues

### Requirement: Schema visibility follows the owning resource
`resolve` SHALL return a schema only when the owning resource is readable by the requesting actor under catalog rules and the facet's own read rules.

#### Scenario: Owning resource not readable
- **WHEN** the actor cannot read the owning resource
- **THEN** its schema is omitted from results

### Requirement: Schema and owner changes reach the index
Saving or deleting a schema facet SHALL record a pending change, and renaming or removing the owning resource SHALL refresh or remove its schema document.

#### Scenario: Schema edited
- **WHEN** a schema's SQL is edited and parsed
- **THEN** a search for a newly added table name finds the schema after the next indexing run

#### Scenario: Owner renamed
- **WHEN** the owning resource is renamed
- **THEN** the schema document's title reflects the new name after the next indexing run
