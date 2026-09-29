## MODIFIED Requirements

### Requirement: Entity envelope
Every entity SHALL have a stable `id`, `apiVersion`, `kind`, `metadata: {name, title, description, documentation, labels, tags, links[]}`, and a kind-specific `spec`. `description` is an optional short summary and `documentation` is an optional Markdown document; both default to empty strings. `id` SHALL be globally stable and comparable across kinds (it identifies the entity's underlying `CatalogEntity` record), independent of `kind`+`name`.

#### Scenario: Entity created with only required fields
- **WHEN** a System is created with only `metadata.name` and `spec.owner` set
- **THEN** it is stored with the remaining envelope fields, including empty `description` and `documentation`, at their defaults and is retrievable by its `id`

#### Scenario: Entity id is stable and globally unique
- **WHEN** a System and a Component are each created
- **THEN** each has an `id` that is unique across the whole catalog, not merely within its own kind
