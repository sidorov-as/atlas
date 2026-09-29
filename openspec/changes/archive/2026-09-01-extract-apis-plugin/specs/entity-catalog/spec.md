## MODIFIED Requirements

### Requirement: Component, Resource, and API CRUD
Component, Resource, and API SHALL each support the same CRUD shape as System, with their own kind-specific `spec` fields, and SHALL validate that reference fields (`owner`, `system`, `dependsOn[]`, `providesApis[]`, `consumesApis[]`) point at existing entities. `providesApis[]`/`consumesApis[]` SHALL be validated generically against `CatalogEntity` records of kind `api`, resolved without Component's owning plugin importing the APIs plugin's models, and SHALL be accepted as empty when no plugin currently provides the `api` kind.

#### Scenario: Component created with valid references
- **WHEN** a Component is created with `system`, `owner`, `dependsOn`, and `providesApis` all referencing existing entities
- **THEN** the Component is created successfully

#### Scenario: Component creation rejects a dangling reference
- **WHEN** a Component is created with a `dependsOn` entry referencing a Resource that doesn't exist
- **THEN** the request is rejected with a validation error and no Component is created

#### Scenario: providesApis validation does not import the APIs plugin's models
- **WHEN** a Component is created with a `providesApis` entry referencing an existing `api`-kind entity
- **THEN** the reference is validated by checking `CatalogEntity.kind`, not by joining against or importing the APIs plugin's `ApiDetails` model
