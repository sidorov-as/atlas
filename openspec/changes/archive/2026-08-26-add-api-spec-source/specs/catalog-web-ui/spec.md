## MODIFIED Requirements

### Requirement: Entity detail pages
System, Component, Resource, and API SHALL each have a detail page with an Overview and Relations view; System and Component detail pages SHALL additionally show their C4 Diagram tab and (for System) Components/Resources/APIs/Docs tabs. An API detail page SHALL additionally show a Documentation tab when its `type` has a documentation viewer available.

#### Scenario: System detail shows its tabs
- **WHEN** a user opens a System's detail page
- **THEN** it shows Overview, Components, Resources, APIs, Docs, Relations, and C4 Diagram tabs

#### Scenario: Component detail shows its tabs
- **WHEN** a user opens a Component's detail page
- **THEN** it shows Overview, Relations, and C4 Diagram (component view) tabs, but no Components/Resources/APIs/Docs tabs

#### Scenario: Resource detail shows only Overview and Relations
- **WHEN** a user opens a Resource's detail page
- **THEN** it shows only Overview and Relations tabs, with no C4 Diagram tab

#### Scenario: API detail shows Overview, Relations, and conditionally Documentation
- **WHEN** a user opens an API's detail page
- **THEN** it shows Overview and Relations tabs, with no C4 Diagram tab, and additionally shows a Documentation tab only when the API's `type` is `openapi` or `asyncapi`
