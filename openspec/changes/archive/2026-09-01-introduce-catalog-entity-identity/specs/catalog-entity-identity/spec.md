## ADDED Requirements

### Requirement: Single concrete catalog identity
Every catalog record SHALL have exactly one concrete `CatalogEntity` row carrying its global `id`, `kind`, `namespace`, `name`, and common metadata, independent of any kind-specific storage.

#### Scenario: Two entities of different kinds never share an id
- **WHEN** a System and a Component are each created
- **THEN** each is backed by its own `CatalogEntity` row with a distinct `id`, and neither row's `id` depends on how many entities of its own kind exist

#### Scenario: Deleting an entity removes its identity row
- **WHEN** an entity is deleted
- **THEN** its `CatalogEntity` row and its kind-specific details row are both removed, and no other entity's `id` changes as a result

### Requirement: Kind-specific data attaches via owned detail models
Kind-specific fields SHALL be stored in a details model with a `OneToOne` relationship to `CatalogEntity`, never as columns on `CatalogEntity` itself and never in an untyped shared extension field.

#### Scenario: Component-specific fields live off CatalogEntity
- **WHEN** a Component entity is created with `type=service` and `lifecycle=production`
- **THEN** `type` and `lifecycle` are stored on that Component's details row, and `CatalogEntity` itself carries no Component-specific column

### Requirement: Relations reference CatalogEntity directly
A relation between two catalog entities SHALL be stored as a foreign key pair referencing `CatalogEntity.id` on both sides, not as a `(kind, local-id)` pair.

#### Scenario: A relation survives a kind-local id being reused elsewhere
- **WHEN** a relation exists between entity A and entity B
- **THEN** the relation resolves to A and B unambiguously via their `CatalogEntity.id`, with no dependency on any per-kind numbering
