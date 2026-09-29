## ADDED Requirements

### Requirement: Entity envelope
Every entity SHALL have `apiVersion`, `kind`, `metadata: {name, title, description, labels, tags, links[]}`, and a kind-specific `spec`.

#### Scenario: Entity created with only required fields
- **WHEN** a System is created with only `metadata.name` and `spec.owner` set
- **THEN** it is stored with the remaining envelope fields at their defaults and is retrievable by its id

### Requirement: System CRUD
A logged-in user SHALL be able to create, list, retrieve, update, and delete Systems via REST, except that update and delete are blocked for YAML-managed Systems.

#### Scenario: Member of owner Group creates a System
- **WHEN** a logged-in user who is a member of Group *G* submits "Add System" with `owner=G`
- **THEN** the System is created and appears in the Systems list within the same request

#### Scenario: Non-member cannot edit a manual System
- **WHEN** a user who is not a member of a manual System's owning Group attempts to edit it
- **THEN** the request is rejected with 403 and no fields change

#### Scenario: YAML-managed System cannot be edited via API
- **WHEN** a user attempts to PATCH or DELETE a System that was created by ingestion
- **THEN** the request is rejected regardless of the user's Group membership

### Requirement: Component, Resource, and API CRUD
Component, Resource, and API SHALL each support the same CRUD shape as System, with their own kind-specific `spec` fields, and SHALL validate that reference fields (`owner`, `system`, `dependsOn[]`, `providesApis[]`, `consumesApis[]`) point at existing entities.

#### Scenario: Component created with valid references
- **WHEN** a Component is created with `system`, `owner`, `dependsOn`, and `providesApis` all referencing existing entities
- **THEN** the Component is created successfully

#### Scenario: Component creation rejects a dangling reference
- **WHEN** a Component is created with a `dependsOn` entry referencing a Resource that doesn't exist
- **THEN** the request is rejected with a validation error and no Component is created

### Requirement: Group and User are read-only via API
Group and User SHALL be listable and retrievable via REST, but SHALL NOT be creatable, updatable, or deletable through the API.

#### Scenario: Creating a Group via the API is rejected
- **WHEN** a request attempts `POST /api/groups/`
- **THEN** the request is rejected, since Groups are admin/ingestion-managed only

#### Scenario: Creating a User via the API is rejected
- **WHEN** a request attempts `POST /api/users/`
- **THEN** the request is rejected, since Users are admin/ingestion-managed only, the same as Groups

### Requirement: List filtering and search
List endpoints for ingestible kinds SHALL support `?owner=`, `?lifecycle=`, `?type=`, and `?q=` (name/description search).

#### Scenario: Filtering the Systems list by owner
- **WHEN** `GET /api/systems/?owner=group:identity-team` is called
- **THEN** only Systems owned by that Group are returned

#### Scenario: Searching the Systems list by text
- **WHEN** `GET /api/systems/?q=user` is called
- **THEN** only Systems whose name or description contains "user" are returned
