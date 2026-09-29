## MODIFIED Requirements

### Requirement: System CRUD
A logged-in user SHALL be able to create, list, retrieve, update, and delete Systems via REST, except that update and delete are blocked for YAML-managed Systems. Create, update, and delete SHALL be served by the core Entity Service using the registered `system` kind handler, not by kind-specific viewset logic.

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
Component, Resource, and API SHALL each support the same CRUD shape as System, with their own kind-specific `spec` fields, and SHALL validate that reference fields (`owner`, `system`, `dependsOn[]`, `providesApis[]`, `consumesApis[]`) point at existing entities. Create, update, and delete SHALL be served by the core Entity Service using each kind's registered handler.

#### Scenario: Component created with valid references
- **WHEN** a Component is created with `system`, `owner`, `dependsOn`, and `providesApis` all referencing existing entities
- **THEN** the Component is created successfully

#### Scenario: Component creation rejects a dangling reference
- **WHEN** a Component is created with a `dependsOn` entry referencing a Resource that doesn't exist
- **THEN** the request is rejected with a validation error and no Component is created
