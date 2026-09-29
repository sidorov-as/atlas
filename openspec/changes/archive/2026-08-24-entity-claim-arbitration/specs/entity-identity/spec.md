## ADDED Requirements

### Requirement: Namespaced identity
Every entity SHALL be identified by the tuple `(kind, namespace, name)`, with `namespace` defaulting to `default`.

#### Scenario: Entity created without specifying namespace
- **WHEN** an entity is created via the UI, API, or ingestion without an explicit namespace
- **THEN** it is stored with `namespace=default`

### Requirement: Case-insensitive uniqueness
No two entities of the same kind and namespace SHALL share a name differing only in case.

#### Scenario: Case-different name collision rejected
- **WHEN** a Component named `Auth` is created in the `default` namespace and one named `auth` already exists for the same kind and namespace
- **THEN** the creation, or ingestion claim, is rejected as a name collision

### Requirement: Ref parsing
Entity references SHALL be parsed as `[kind:][namespace/]name`, resolving an absent namespace to `default`.

#### Scenario: Ref without namespace resolves to default
- **WHEN** a `catalog-info.yaml` spec field references `resource:user-db`
- **THEN** it resolves to the entity `kind=resource, namespace=default, name=user-db`

#### Scenario: Bare name rejects a slash
- **WHEN** a manifest declares `metadata.name` containing a `/` character
- **THEN** the manifest is rejected as invalid, since namespace is not settable via `name` in v1

### Requirement: Namespace unexposed in v1
No UI control or `catalog-info.yaml` field SHALL allow a user to set a namespace other than `default`.

#### Scenario: No namespace UI control
- **WHEN** a user creates or edits an entity through the web UI
- **THEN** there is no field to set a namespace other than the implicit `default`
