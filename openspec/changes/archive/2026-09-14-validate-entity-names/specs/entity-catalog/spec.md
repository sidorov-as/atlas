## MODIFIED Requirements

### Requirement: Entity envelope
Every entity SHALL have a stable `id`, `apiVersion`, `kind`, `metadata: {name, title, description, documentation, labels, tags, links[]}`, and a kind-specific `spec`. `description` is an optional short summary and `documentation` is an optional Markdown document; both default to empty strings. `id` SHALL be globally stable and comparable across kinds (it identifies the entity's underlying `CatalogEntity` record), independent of `kind`+`name`. `metadata.name` SHALL be stripped of leading/trailing whitespace and SHALL be rejected if the stripped value is empty or contains `/` or `:`; a PATCH that omits `name` SHALL leave the existing name unchanged, but a PATCH that explicitly provides an invalid `name` SHALL be rejected the same as on create.

#### Scenario: Entity created with only required fields
- **WHEN** a System is created with only `metadata.name` and `spec.owner` set
- **THEN** it is stored with the remaining envelope fields, including empty `description` and `documentation`, at their defaults and is retrievable by its `id`

#### Scenario: Entity id is stable and globally unique
- **WHEN** a System and a Component are each created
- **THEN** each has an `id` that is unique across the whole catalog, not merely within its own kind

#### Scenario: Empty or whitespace-only name is rejected
- **WHEN** an entity is created or updated with `metadata.name` set to `""` or `"   "`
- **THEN** the request is rejected and no entity is created or modified

#### Scenario: Name containing a forbidden character is rejected
- **WHEN** an entity is created or updated with `metadata.name` containing `/` or `:`
- **THEN** the request is rejected

#### Scenario: Name is trimmed of surrounding whitespace
- **WHEN** an entity is created with `metadata.name` set to `" checkout "`
- **THEN** the entity is stored with `name` equal to `"checkout"`

#### Scenario: Omitting name on a PATCH leaves it unchanged
- **WHEN** an existing entity is updated via PATCH without a `name` field in the request body
- **THEN** the entity's existing `name` is unchanged
