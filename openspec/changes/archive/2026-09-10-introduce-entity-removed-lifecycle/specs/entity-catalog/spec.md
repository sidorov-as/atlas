## MODIFIED Requirements

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
