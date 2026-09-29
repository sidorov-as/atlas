# entity-catalog Specification

## Purpose
The entity envelope shared by all catalog entities, and CRUD/listing REST endpoints for System, Component, Resource, and API (with read-only listing for Group and User), including reference validation and filtering/search.

## Requirements

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

### Requirement: System CRUD
A logged-in user SHALL be able to create, list, retrieve, and update Systems via REST, except that update and manual remove are blocked for YAML-managed Systems. There SHALL be no REST route or UI affordance to permanently delete a System directly from `active`; `Remove` followed by `Purge` (per the `entity-removal-lifecycle` capability) is the only path to permanently destroying one. Create and update SHALL be served by the core Entity Service using the registered `system` kind handler, not by kind-specific viewset logic. A permitted user SHALL additionally be able to remove and revive a manually-created System, and purge a removed System, per the `entity-removal-lifecycle` capability.

#### Scenario: Member of owner Group creates a System
- **WHEN** a logged-in user who is a member of Group *G* submits "Add System" with `owner=G`
- **THEN** the System is created and appears in the Systems list within the same request

#### Scenario: Non-member cannot edit a manual System
- **WHEN** a user who is not a member of a manual System's owning Group attempts to edit it
- **THEN** the request is rejected with 403 and no fields change

#### Scenario: YAML-managed System cannot be edited via API
- **WHEN** a user attempts to PATCH a System that was created by ingestion
- **THEN** the request is rejected regardless of the user's Group membership

#### Scenario: No REST route exists to directly delete a System
- **WHEN** a client sends `DELETE /api/systems/{id}/`
- **THEN** the request is rejected with 405 Method Not Allowed — there is no delete action on this route; `Remove` then `Purge` is the only way to permanently destroy a System

#### Scenario: YAML-managed System cannot be manually removed via API
- **WHEN** a user attempts to invoke Remove on a System that was created by ingestion
- **THEN** the request is rejected regardless of the user's Group membership; that System can only become `removed` through ingestion reconciliation

#### Scenario: Owner removes and revives a manual System
- **WHEN** a member of a manual System's owning Group invokes Remove, and later Revive
- **THEN** the System's status becomes `removed` and then `active` again, with its id and relations unchanged throughout

### Requirement: Component, Resource, and API CRUD
Component, Resource, and API SHALL each support the same CRUD shape as System — including the same absence of a direct-delete route, the same manual remove/revive/purge behavior, and the same YAML-managed restriction on manual remove — with their own kind-specific `spec` fields, and SHALL validate that reference fields (`owner`, `system`, `dependsOn[]`, `providesApis[]`, `consumesApis[]`) point at existing entities. `providesApis[]`/`consumesApis[]` SHALL be validated generically against `CatalogEntity` records of kind `api`, resolved without Component's owning plugin importing the APIs plugin's models, and SHALL be accepted as empty when no plugin currently provides the `api` kind. Create and update SHALL be served by the core Entity Service using each kind's registered handler.

#### Scenario: Component created with valid references
- **WHEN** a Component is created with `system`, `owner`, `dependsOn`, and `providesApis` all referencing existing entities
- **THEN** the Component is created successfully

#### Scenario: Component creation rejects a dangling reference
- **WHEN** a Component is created with a `dependsOn` entry referencing a Resource that doesn't exist
- **THEN** the request is rejected with a validation error and no Component is created

#### Scenario: providesApis validation does not import the APIs plugin's models
- **WHEN** a Component is created with a `providesApis` entry referencing an existing `api`-kind entity
- **THEN** the reference is validated by checking `CatalogEntity.kind`, not by joining against or importing the APIs plugin's `ApiDetails` model

#### Scenario: A manually-created Resource can be removed, revived, and purged
- **WHEN** a permitted user removes a manually-created Resource with no remaining active references, then purges it
- **THEN** the remove and purge each succeed in sequence, and the purge frees the Resource's name for reuse by a new entity

### Requirement: Group and User are read-only via API
Group and User SHALL be listable and retrievable via REST, but SHALL NOT be creatable, updatable, or deletable through the API.

#### Scenario: Creating a Group via the API is rejected
- **WHEN** a request attempts `POST /api/groups/`
- **THEN** the request is rejected, since Groups are admin/ingestion-managed only

#### Scenario: Creating a User via the API is rejected
- **WHEN** a request attempts `POST /api/users/`
- **THEN** the request is rejected, since Users are admin/ingestion-managed only, the same as Groups

### Requirement: List filtering and search
List endpoints for ingestible kinds SHALL support `?owner=`, `?lifecycle=`, `?type=`, `?tags=` (repeatable; matches an entity carrying **any** of the given tags), `?q=` (name/description/documentation search), `?page=`/`?page_size=` for pagination, and a status filter that excludes `removed` entities by default while allowing any authenticated caller to request them explicitly. Component, Resource, and API lists SHALL additionally support `?system=`. Responses SHALL be a paginated envelope (item count, page count, page size, and the current page's items) rather than a bare array.

#### Scenario: Filtering the Systems list by owner
- **WHEN** `GET /api/systems/?owner=group:identity-team` is called
- **THEN** only Systems owned by that Group are returned

#### Scenario: Searching the Systems list by text
- **WHEN** `GET /api/systems/?q=user` is called
- **THEN** only Systems whose name, description, or documentation contains "user" are returned

#### Scenario: Filtering a list by multiple tags matches any of them
- **WHEN** `GET /api/components/?tags=payments&tags=internal` is called
- **THEN** only Components carrying at least one of `payments` or `internal` in their tags are returned

#### Scenario: Listing entities returns a paginated envelope
- **WHEN** `GET /api/components/?page=2&page_size=10` is called
- **THEN** the response contains at most 10 Components for page 2, along with the total item count and page metadata

#### Scenario: Listing entities belonging to a System
- **WHEN** `GET /api/components/?system=system:payments` is called
- **THEN** only Components belonging to that System are returned

#### Scenario: Default list excludes removed entities
- **WHEN** `GET /api/components/` is called with no status filter
- **THEN** only `active` Components are returned

#### Scenario: Any authenticated caller can request removed entities
- **WHEN** any authenticated user, regardless of Group membership, calls the list endpoint with the removed-inclusive status filter
- **THEN** `removed` entities are included in the response

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

### Requirement: System document links have a paginated read API
The catalog API SHALL expose `GET /api/systems/{id}/docs/` to authenticated
readers. The endpoint SHALL return that System's metadata links in the standard
paginated envelope and SHALL support `q`, `page`, and `page_size` query
parameters. `q` SHALL match title or description case-insensitively, and the
response order SHALL retain the System's declared link order after filtering.

#### Scenario: Search filters System document links
- **WHEN** a reader requests a System's document links with `q=dashboard`
- **THEN** the response contains only links whose title or description matches
  `dashboard` case-insensitively

#### Scenario: Document links are paginated
- **WHEN** a System has more document links than the requested `page_size`
- **THEN** the response contains the requested page and the total item count
  and page metadata

#### Scenario: Document-link API is read-only
- **WHEN** a client sends a non-GET request to a System's document-links URL
- **THEN** the request is rejected and no System metadata changes

#### Scenario: Manual Docs management uses the System PATCH API
- **WHEN** an authorized owner adds, edits, or removes a document link in the
  System Docs tab
- **THEN** the client updates the complete `metadata.links` list through the
  existing System PATCH route, while the document-links URL remains read-only

#### Scenario: Missing System has no document-link listing
- **WHEN** a reader requests document links for a nonexistent System id
- **THEN** the API returns the same not-found result as System retrieval
