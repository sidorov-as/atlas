## MODIFIED Requirements

### Requirement: Entity envelope
Every entity SHALL have a stable `id`, `apiVersion`, `kind`, `metadata: {name, title, description, documentation, labels, tags, links[]}`, and a kind-specific `spec`. `description` is an optional short summary and `documentation` is an optional Markdown document; both default to empty strings and are each bounded to a fixed maximum length. `labels` (a map) and `tags`/`links` (lists) are each bounded to a fixed maximum number of entries. `id` SHALL be globally stable and comparable across kinds (it identifies the entity's underlying `CatalogEntity` record), independent of `kind`+`name`. `metadata.name` SHALL be stripped of leading/trailing whitespace and SHALL be rejected if the stripped value is empty or contains `/` or `:`; a PATCH that omits `name` SHALL leave the existing name unchanged, but a PATCH that explicitly provides an invalid `name` SHALL be rejected the same as on create.

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

#### Scenario: Oversized description or documentation is rejected
- **WHEN** an entity is created or updated with `metadata.description` or `metadata.documentation` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and no entity is created or modified

#### Scenario: Too many labels, tags, or links is rejected
- **WHEN** an entity is created or updated with more `metadata.labels` entries, `metadata.tags` entries, or `metadata.links` entries than the declared maximum
- **THEN** the request is rejected with a validation error and no entity is created or modified

### Requirement: Metadata links include resource descriptions
Every catalog entity's `metadata.links[]` item SHALL expose `url`, `title`,
`description`, and `type`. `url` SHALL be non-empty; `title`, `description`,
and `type` SHALL default to empty strings so existing manifests and API clients
that omit them remain valid. Each of `url`, `title`, `description`, and `type`
SHALL be bounded to a fixed maximum length.

#### Scenario: Existing link remains valid without a description
- **WHEN** an entity is created or ingested with a link containing only `url`,
  `title`, and `type`
- **THEN** it is accepted and retrieved with an empty `description`

#### Scenario: Oversized link field is rejected
- **WHEN** an entity is created or updated with a `metadata.links[]` item whose
  `url`, `title`, `description`, or `type` exceeds its declared maximum length
- **THEN** the request is rejected with a validation error and no entity is
  created or modified
