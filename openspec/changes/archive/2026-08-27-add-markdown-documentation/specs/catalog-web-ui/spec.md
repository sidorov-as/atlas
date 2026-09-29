## MODIFIED Requirements

### Requirement: Entity detail pages
System, Component, Resource, and API SHALL each have a detail page with an Overview and Relations view; System and Component detail pages SHALL additionally show their C4 Diagram tab and (for System) Components/Resources/APIs/Docs tabs. Overview SHALL render the entity's Markdown `documentation`, while its short `description` remains in the page header. An API with stored specification content SHALL additionally show a `Specification` tab containing the specification download action before its viewer or fallback state; an OpenAPI or AsyncAPI API SHALL render the matching viewer below that action, and a gRPC or GraphQL API SHALL show an unsupported-viewer message below it.

#### Scenario: System detail shows its tabs
- **WHEN** a user opens a System's detail page
- **THEN** it shows Overview, Components, Resources, APIs, Docs, Relations, and C4 Diagram tabs

#### Scenario: Component detail shows its tabs
- **WHEN** a user opens a Component's detail page
- **THEN** it shows Overview, Relations, and C4 Diagram (component view) tabs, but no Components/Resources/APIs/Docs tabs

#### Scenario: Resource detail shows only Overview and Relations
- **WHEN** a user opens a Resource's detail page
- **THEN** it shows only Overview and Relations tabs, with no C4 Diagram tab

#### Scenario: API detail shows Overview, Relations, and Specification for stored content
- **WHEN** a user opens an API with stored specification content
- **THEN** it shows Overview, Relations, and a Specification tab, with no C4 Diagram tab

#### Scenario: API Specification places download before viewer
- **WHEN** a user opens the Specification tab of an OpenAPI or AsyncAPI API with stored specification content
- **THEN** the download action appears before the matching specification viewer

#### Scenario: Unsupported API viewer preserves specification download
- **WHEN** a user opens the Specification tab of a gRPC or GraphQL API with stored specification content
- **THEN** the tab shows the download action and an explicit message that no embedded viewer is available

### Requirement: Add/Edit forms for manual entities only
A manual entity's detail page SHALL show Add/Edit affordances; a YAML-managed entity's detail page SHALL show a read-only banner naming the backing repository instead. The add/edit forms for manual System, Component, Resource, and API entities SHALL include a Markdown Documentation editor after their standard and kind-specific fields.

#### Scenario: YAML-managed entity shows a banner, not an Edit button
- **WHEN** a user opens the detail page of an entity ingested from `org/repo`
- **THEN** the page shows "managed by `catalog-info.yaml` in `org/repo`" instead of an Edit button

#### Scenario: Manual entity form places Documentation after its fields
- **WHEN** a user opens the create or edit form for a manual API
- **THEN** the Documentation editor follows its Name, Title, Description, Tags, Type, Owner, System, and specification-source fields
